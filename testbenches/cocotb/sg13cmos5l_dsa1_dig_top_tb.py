# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Chip-level testbench for sg13cmos5l_dsa1_dig_top.

The die carries one macro, the DSADC1 digital back end: a 128x decimation
filter, an SPI slave and a configuration register file. dsm2, the analog modulator, sits in a
VDDA segment of the pad ring.

Pad map, from rtl/sg13cmos5l_dsa1_dig_core.sv:

  input_PAD[0]     data_in, the 1-bit modulator bitstream, synchronized on chip
  input_PAD[1]     sclk
  input_PAD[2]     mosi
  input_PAD[3]     ss, active low
  output_PAD[0]    miso
  output_PAD[1]    adc_conv, one clk cycle wide at the 512 Hz output rate, gated by ADC_CONV_EN
  analog_PAD[2:0]  vi, vcm, ibias_test
  dsm_clk_PAD      dsm2 clock, the inverted clk when DEC_SRC is used
  do_q_PAD         dsm2 bit, high only with DSM_QOUT_EN
  do_q_b_PAD       its complement
  no test pads, VDDA is a supply

SPI frame of dsa1_ic_bus_slave, 23 falling sclk edges with ss low: 5 address
bits MSB first (bit 4 set means read), 1 load cycle, 16 data bits MSB first,
1 store cycle. mosi is sampled on the falling edge, miso driven on the rising.

The clock ratio is what matters, not the absolute rate, so the simulation runs
clk at 50 ns and sclk at 20 ns as the Verilog benches do. sclk must be the
faster of the two: the register file captures a new ADC word only on sclk edges
while the synchronized ready flag is high.
"""

import os
import re
import sys
import types
import logging
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge, ClockCycles
from cocotb_tools.runner import get_results, get_runner

sim      = os.getenv("SIM", "icarus")
pdk_root = os.getenv("PDK_ROOT", Path("~/.ciel").expanduser())
pdk      = os.getenv("PDK", "ihp-sg13cmos5l")
scl      = os.getenv("SCL", "sg13cmos5l_stdcell")
# GL=1 selects the gate-level netlist; anything else stays in RTL mode.
gl       = os.getenv("GL", "0").strip().lower() in ("1", "true", "yes", "on")

hdl_toplevel = "sg13cmos5l_dsa1_dig_top"

CLK_PERIOD_NS  = 50.0
SCLK_PERIOD_NS = 20.0

# Register map, generated from macros/dsa1_dig/regmap.yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "models"))
import regmap  # noqa: E402
from decimator_model import DecimatorModel  # noqa: E402

A = regmap.ADDR
ADC_DATA_HIGH, ADC_DATA_LOW = A["ADC_DATA_CH0_HIGH"], A["ADC_DATA_CH0_LOW"]
BIAS_CFG_0, BIAS_CFG_1, BIAS_CFG_2 = A["BIAS_CFG_0"], A["BIAS_CFG_1"], A["BIAS_CFG_2"]
BLOCK_CTRL_0, BLOCK_CTRL_1 = A["BLOCK_CTRL_0"], A["BLOCK_CTRL_1"]
TRIM_CFG_0, CLK_CFG_0, TEST_CTRL_0 = A["TRIM_CFG_0"], A["CLK_CFG_0"], A["TEST_CTRL_0"]
UWB_TX_CFG_0, UWB_TX_CFG_1 = A["UWB_TX_CFG_0"], A["UWB_TX_CFG_1"]
AUX_CTRL_0, TEST_CTRL_1, CHIP_ID = A["AUX_CTRL_0"], A["TEST_CTRL_1"], A["CHIP_ID"]
CHIP_ID_VALUE = regmap.RESET[CHIP_ID]  # this die, read only. The DSA1 die reads 0x0000 there.

# TEST_CTRL_0 fields. The reset, 0x0500, keeps FLAG_SYNC_EN and PAD_Q_EN set, which every
# write to this register has to preserve. Bit 9 belongs to the analog top and is never written.
_T = {f["name"]: f for f in regmap.REGS["TEST_CTRL_0"]["fields"]}
TST_BASE      = regmap.RESET[TEST_CTRL_0]
TST_STIM_EN   = 1 << _T["STIM_EN"]["lsb"]
TST_STIM_TRIG = 1 << _T["STIM_TRIG"]["lsb"]   # rising edge arms, the pattern fires at valid_strobe
TST_STIM_PAT  = _T["STIM_PAT"]["lsb"]
TST_STIM_OPT  = 1 << _T["STIM_OPT"]["lsb"]    # repeat for the event patterns, variant for the steady one
PAT_STEP_P, PAT_IMPULSE, PAT_STEADY, PAT_STEP_N = (
    _T["STIM_PAT"]["enum"][k] for k in ("STEP_P", "IMPULSE", "STEADY", "STEP_N"))

def stim(pat, opt=False, trig=False):
    """The TEST_CTRL_0 value for one pattern, armed or fired."""
    v = TST_BASE | TST_STIM_EN | (pat << TST_STIM_PAT)
    if opt:
        v |= TST_STIM_OPT
    if trig:
        v |= TST_STIM_TRIG
    return v

# What a constant 1 on data_in decimates to. decimator_top maps it to +1, which
# is 2**20 at the 22-bit output.
FULL_SCALE = 1 << 20


# ----------------------------------------------------------------------
# Pad access
# ----------------------------------------------------------------------

class Pads:
    """Shadow of input_PAD, so single bits can be driven on a vector port."""

    def __init__(self, dut):
        self.dut = dut
        self.val = 0b1000          # ss idle high, everything else low
        self.flush()

    def flush(self):
        self.dut.input_PAD.value = self.val

    def set(self, bit, level):
        if level:
            self.val |= (1 << bit)
        else:
            self.val &= ~(1 << bit)
        self.flush()

    # named lines
    def data_in(self, v):  self.set(0, v)
    def sclk(self, v):     self.set(1, v)
    def mosi(self, v):     self.set(2, v)
    def ss(self, v):       self.set(3, v)


# Read bits out of output_PAD by masking the integer value. Positional
# indexing of the handle picks the wrong end of the vector, which shows up as
# every SPI read returning zero while writes still work.
def miso(dut):
    return (int(dut.output_PAD.value) >> 0) & 1


def adc_conv(dut):
    return (int(dut.output_PAD.value) >> 1) & 1


async def enable_power(dut):
    """Drive supplies for gate-level simulation (USE_POWER_PINS)."""
    for name in ("VDD", "IOVDD", "VDDA"):
        if hasattr(dut, name):
            getattr(dut, name).value = 1
    for name in ("VSS", "IOVSS"):
        if hasattr(dut, name):
            getattr(dut, name).value = 0


# ----------------------------------------------------------------------
# SPI, driven bit by bit on the pad shadow
# ----------------------------------------------------------------------

async def sclk_run(dut, pads):
    """Free-running sclk. The register file needs it even between frames."""
    half = SCLK_PERIOD_NS / 2
    # A quarter period of offset so sclk and clk edges never coincide.
    await Timer(SCLK_PERIOD_NS / 4, units="ns")
    while True:
        pads.sclk(1)
        await Timer(half, units="ns")
        pads.sclk(0)
        await Timer(half, units="ns")


async def sclk_falling(dut, pads):
    """Wait for the next falling edge of the sclk we generate ourselves."""
    while True:
        await Timer(1, units="ns")
        if (pads.val >> 1) & 1:
            break
    while True:
        await Timer(1, units="ns")
        if not ((pads.val >> 1) & 1):
            return


async def spi(dut, pads, addr, wdata):
    """One transaction. Returns the 16 bits shifted out on miso."""
    frame = ((addr & 0x1F) << 18) | ((wdata & 0xFFFF) << 1)
    rdata = 0
    await sclk_falling(dut, pads)
    await Timer(1, units="ns")
    pads.ss(0)
    pads.mosi((frame >> 22) & 1)
    for k in range(22, -1, -1):
        await sclk_falling(dut, pads)
        if 1 <= k <= 16:
            rdata = ((rdata << 1) | miso(dut)) & 0xFFFF
        await Timer(1, units="ns")
        pads.mosi((frame >> (k - 1)) & 1 if k > 0 else 0)
    await sclk_falling(dut, pads)
    await Timer(1, units="ns")
    pads.ss(1)
    pads.mosi(0)
    return rdata


async def reg_read(dut, pads, addr):
    return await spi(dut, pads, 0x10 | addr, 0x0000)


async def reg_write(dut, pads, addr, value):
    await spi(dut, pads, addr, value)


async def read_adc_word(dut, pads):
    """The coherent 22-bit pair, signed. HIGH first: the slave freezes LOW on it."""
    hi = await reg_read(dut, pads, ADC_DATA_HIGH)
    lo = await reg_read(dut, pads, ADC_DATA_LOW)
    w = ((hi & 0x3F) << 16) | lo
    return w - (1 << 22) if w & (1 << 21) else w


# ----------------------------------------------------------------------
# Bring-up
# ----------------------------------------------------------------------

async def bringup(dut):
    """Power, clocks, reset. Returns the pad shadow."""
    await enable_power(dut)
    pads = Pads(dut)
    dut.rst_n_PAD.value = 0
    cocotb.start_soon(Clock(dut.clk_PAD, CLK_PERIOD_NS, units="ns").start())
    cocotb.start_soon(sclk_run(dut, pads))
    # The decimator reset is synchronous, so hold it over several clk edges.
    await ClockCycles(dut.clk_PAD, 10)
    dut.rst_n_PAD.value = 1
    await ClockCycles(dut.clk_PAD, 2)
    return pads


async def wait_conversion(dut):
    """One rising edge of adc_conv, then let the flag synchronizer settle."""
    while adc_conv(dut) == 1:
        await RisingEdge(dut.clk_PAD)
    while adc_conv(dut) == 0:
        await RisingEdge(dut.clk_PAD)
    await Timer(4 * SCLK_PERIOD_NS, units="ns")


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

@cocotb.test()
async def test_register_read_invert_write_read(dut):
    """Read every writable register, write it back inverted, read it again.

    TEST_CTRL_0 is deliberately excluded. Its bits 7:6 are the bias test mux
    and the code 11 is documented as a hazard that must never be written, so a
    blanket invert would put a forbidden pattern in a test that could later be
    pointed at silicon. It gets its own targeted coverage in the step test.

    The two ADC data registers are read only and are checked as such, and so is
    CHIP_ID.
    """
    log = logging.getLogger("riwr")
    pads = await bringup(dut)

    writable = [
        (BIAS_CFG_0,   "BIAS_CFG_0"),
        (BIAS_CFG_1,   "BIAS_CFG_1"),
        (BIAS_CFG_2,   "BIAS_CFG_2"),
        (BLOCK_CTRL_0, "BLOCK_CTRL_0"),
        (BLOCK_CTRL_1, "BLOCK_CTRL_1"),
        (TRIM_CFG_0,   "TRIM_CFG_0"),
        (CLK_CFG_0,    "CLK_CFG_0"),
        (UWB_TX_CFG_0, "UWB_TX_CFG_0"),
        (UWB_TX_CFG_1, "UWB_TX_CFG_1"),
        (AUX_CTRL_0,   "AUX_CTRL_0"),
        (TEST_CTRL_1,  "TEST_CTRL_1"),
        (14,           "SCRATCH_14"),
    ]

    originals = {}
    for addr, name in writable:
        before = await reg_read(dut, pads, addr)
        originals[addr] = before
        inverted = (~before) & 0xFFFF
        await reg_write(dut, pads, addr, inverted)
        after = await reg_read(dut, pads, addr)
        log.info("%-13s %04X -> %04X, read back %04X", name, before, inverted, after)
        assert after == inverted, (
            f"{name} (addr {addr}): wrote {inverted:04X}, read back {after:04X}"
        )

    # Restore, and prove the restore took as well.
    for addr, name in writable:
        await reg_write(dut, pads, addr, originals[addr])
        back = await reg_read(dut, pads, addr)
        assert back == originals[addr], (
            f"{name} (addr {addr}): restore wrote {originals[addr]:04X}, read {back:04X}"
        )

    # CHIP_ID holds its value through a write of its inverse
    for value in (~CHIP_ID_VALUE & 0xFFFF, 0x0000):
        await reg_write(dut, pads, CHIP_ID, value)
        chip_id = await reg_read(dut, pads, CHIP_ID)
        assert chip_id == CHIP_ID_VALUE, (
            f"CHIP_ID (addr {CHIP_ID}): wrote {value:04X}, read {chip_id:04X}, not {CHIP_ID_VALUE:04X}"
        )

    # The ADC data registers are not write protected: dsa1_ic_bus_slave writes
    # dataReg(addr) for any address whose read bit is clear, so address 0
    # accepts a write like any other. It only looks read only because the next
    # conversion overwrites it.
    await reg_write(dut, pads, ADC_DATA_HIGH, 0xFFFF)
    assert await reg_read(dut, pads, ADC_DATA_HIGH) == 0xFFFF, (
        "ADC_DATA_HIGH did not accept a write, which contradicts the slave RTL"
    )

    for _ in range(2):
        await wait_conversion(dut)
    hi = await reg_read(dut, pads, ADC_DATA_HIGH)
    assert hi & 0xFFC0 == 0, (
        f"ADC_DATA_HIGH still shows {hi:04X} after a conversion, so the capture "
        "path did not overwrite the value written over SPI"
    )

    # Address 1 is different. Reading it returns adc_low_freeze_reg, which the
    # slave latches when HIGH is read, so that a HIGH/LOW pair belongs to one
    # conversion. Reading LOW twice without an intervening HIGH read must give
    # the same word even if a conversion lands in between.
    lo1 = await reg_read(dut, pads, ADC_DATA_LOW)
    for _ in range(2):
        await wait_conversion(dut)
    lo2 = await reg_read(dut, pads, ADC_DATA_LOW)
    assert lo1 == lo2, (
        f"ADC_DATA_LOW moved {lo1:04X} -> {lo2:04X} without a HIGH read, so the "
        "coherent block data update is not holding it"
    )
    log.info("ADC data: HIGH is writable and overwritten by capture, "
             "LOW is frozen on the HIGH read (%04X held across two conversions)", lo1)

    log.info("read/invert/write/read passed on %d registers", len(writable))


async def run_pattern(dut, pads, pat, opt=False, settle=20, n=40):
    """Arm, let the idle settle to zero, fire, then collect n output words."""
    await reg_write(dut, pads, TEST_CTRL_0, stim(pat, opt))
    for _ in range(settle):
        await wait_conversion(dut)
    idle = await read_adc_word(dut, pads)
    await reg_write(dut, pads, TEST_CTRL_0, stim(pat, opt, trig=True))
    words = []
    for _ in range(n):
        await wait_conversion(dut)
        words.append(await read_adc_word(dut, pads))
    await reg_write(dut, pads, TEST_CTRL_0, TST_BASE)
    return idle, words


@cocotb.test()
async def test_step_response(dut):
    """Step +: the idle decimates to zero, then the output walks to full scale.

    The idle pattern is an alternating bitstream at clk/2, which the filter
    rejects, so the output settles to zero. The step then holds the stream at 1
    and the output walks to +full scale, overshooting on the way because the
    droop compensator has a gain of about 4.4 at the band edge.
    """
    log = logging.getLogger("step")
    pads = await bringup(dut)
    idle, words = await run_pattern(dut, pads, PAT_STEP_P)

    log.info("idle output after settling: %d", idle)
    log.info("step first 6: %s", words[:6])
    log.info("step peak %d, final %d", max(words, key=abs), words[-1])

    assert abs(idle) < FULL_SCALE // 100, (
        f"the alternating idle should decimate to about zero, got {idle}"
    )
    assert words[0] < FULL_SCALE // 10, f"step starts too high: {words[0]}"
    assert abs(words[-1] - FULL_SCALE) < FULL_SCALE // 50, (
        f"step should settle near {FULL_SCALE}, got {words[-1]}"
    )
    assert max(words) > words[-1], "expected the compensator overshoot"


@cocotb.test()
async def test_step_response_negative(dut):
    """Step -: the mirror of step +, and the only thing that reaches DATA_MIN.

    The core saturates at DATA_MIN on a different path from DATA_MAX, so the
    negative rail is not covered by the positive step.
    """
    log = logging.getLogger("step_n")
    pads = await bringup(dut)
    _, words = await run_pattern(dut, pads, PAT_STEP_N)

    log.info("step- peak %d, final %d", max(words, key=abs), words[-1])
    assert words[0] > -FULL_SCALE // 10, f"step- starts too low: {words[0]}"
    assert abs(words[-1] + FULL_SCALE) < FULL_SCALE // 50, (
        f"step- should settle near {-FULL_SCALE}, got {words[-1]}"
    )
    assert min(words) < words[-1], "expected the compensator undershoot"


@cocotb.test()
async def test_impulse_response(dut):
    """On-chip impulse stimulus: one broken sample on the alternating idle."""
    log = logging.getLogger("impulse")
    pads = await bringup(dut)
    _, words = await run_pattern(dut, pads, PAT_IMPULSE)

    peak = max(words, key=abs)
    log.info("impulse peak %d, final %d", peak, words[-1])

    assert abs(peak) > 1000, f"impulse response too small to be real: peak {peak}"
    assert abs(peak) < FULL_SCALE // 4, f"impulse response implausibly large: {peak}"
    assert abs(words[-1]) < abs(peak) // 4, "impulse should decay back towards zero"


@cocotb.test()
async def test_half_scale_linearity(dut):
    """The period-4 + + + - pattern has mean +1/2, so the output is half scale.

    With the two rails this is a three-point gain-linearity check, and it is
    the only one of the three that does not sit against a saturation limit.
    """
    log = logging.getLogger("half")
    pads = await bringup(dut)
    _, words = await run_pattern(dut, pads, PAT_STEADY)

    log.info("half scale settles at %d, expected about %d", words[-1], FULL_SCALE // 2)
    assert abs(words[-1] - FULL_SCALE // 2) < FULL_SCALE // 50, (
        f"half scale should settle near {FULL_SCALE // 2}, got {words[-1]}"
    )


@cocotb.test()
async def test_prbs_noise(dut):
    """PRBS23 in, so the output is the filter's noise bandwidth, not a signal.

    The same polynomial and seed as decimator_top_tb.v, so models/stimulus.py
    predicts the sequence exactly rather than only its statistics.
    """
    log = logging.getLogger("prbs")
    pads = await bringup(dut)
    _, words = await run_pattern(dut, pads, PAT_STEADY, opt=True)

    peak = max(words, key=abs)
    log.info("prbs peak %d, final %d", peak, words[-1])

    assert peak != 0, "a white input should not decimate to exactly zero"
    assert abs(peak) < FULL_SCALE, f"prbs output should stay in range, got {peak}"
    assert any(w < 0 for w in words) and any(w > 0 for w in words), (
        "a zero-mean white input should give an output of both signs"
    )


B1 = {f["name"]: f for f in regmap.REGS["BIAS_CFG_1"]["fields"]}
DSM_EN      = 1 << B1["DSM_EN"]["lsb"]
DSM_RST_B   = 1 << B1["DSM_RST_B"]["lsb"]
DEC_SRC     = 1 << B1["DEC_SRC"]["lsb"]
DSM_QOUT_EN = 1 << B1["DSM_QOUT_EN"]["lsb"]
ADC_CONV_EN = 1 << B1["ADC_CONV_EN"]["lsb"]


def pad_bit(dut, name):
    v = getattr(dut, name).value
    return None if not v.is_resolvable else int(v)


async def dsm_clock(dut):
    """dsm_clk is the inverted clk, as DEC_SRC needs on the board."""
    while True:
        await RisingEdge(dut.clk_PAD)
        dut.dsm_clk_PAD.value = 0
        await FallingEdge(dut.clk_PAD)
        dut.dsm_clk_PAD.value = 1


def prbs15(n):
    lfsr, out = 1, []
    for _ in range(n):
        out.append(lfsr & 1)
        lfsr = ((lfsr << 1) | (((lfsr >> 14) ^ (lfsr >> 13)) & 1)) & 0x7FFF
    return out


def core_cell(dut, name):
    """A cell of the core, with the pins A, B and Y as signal handles.

    The chip netlist is flat, and a simulator cannot descend into a cell whose escaped name holds dots,
    so the gate-level flavour reads the nets on its pins out of the netlist and returns those.
    """
    if not gl:
        return getattr(dut.i_sg13cmos5l_dsa1_dig_core, name)
    text = (Path(__file__).resolve().parent.parent.parent / f"netlist/nl/{hdl_toplevel}.nl.v").read_text()
    m = re.search(r"^\s*\w+\s+\\i_sg13cmos5l_dsa1_dig_core\.%s\s+\((.*?)\);" % re.escape(name), text, flags=re.S | re.M)
    assert m, f"no cell {name} in the netlist"
    pins = {pin: net.strip().lstrip("\\") for pin, net in re.findall(r"\.(\w+)\(([^()]*)\)", m.group(1))}
    # A name with dots and brackets does not resolve by lookup, only by listing the children.
    children = {c._name: c for c in dut}
    return types.SimpleNamespace(**{pin: children[net] for pin, net in pins.items()})


@cocotb.test()
async def test_dsm_quiet_with_dec_src_low(dut):
    """After reset the do_q pads are low. With dsm2 running and DEC_SRC low the gate output stays 0."""
    pads = await bringup(dut)
    cocotb.start_soon(dsm_clock(dut))
    gate = core_cell(dut, "u_dec_src_gate")
    for _ in range(20):
        await RisingEdge(dut.clk_PAD)
        assert pad_bit(dut, "do_q_PAD") == 0 and pad_bit(dut, "do_q_b_PAD") == 0
        assert int(gate.Y.value) == 0
    await reg_write(dut, pads, A["BIAS_CFG_1"], ADC_CONV_EN | DSM_EN | DSM_RST_B)
    seen = set()
    for _ in range(64):
        await RisingEdge(dut.clk_PAD)
        seen.add(pad_bit(dut, "do_q_PAD"))
        assert int(gate.Y.value) == 0
        v = dut.dsm2.do_q_dec.value
        if v.is_resolvable:
            seen.add(("dec", int(v)))
    assert ("dec", 0) in seen and ("dec", 1) in seen, "dsm2's do_q_dec must toggle while the gate holds 0"
    assert seen - {("dec", 0), ("dec", 1)} == {0}, "the pads must stay quiet with DSM_QOUT_EN low"


@cocotb.test()
async def test_qout_en_switches_the_pads(dut):
    """DSM_QOUT_EN: the pads follow the stream, and stop again when it is cleared."""
    pads = await bringup(dut)
    cocotb.start_soon(dsm_clock(dut))
    await reg_write(dut, pads, A["BIAS_CFG_1"], ADC_CONV_EN | DSM_EN | DSM_RST_B | DSM_QOUT_EN)
    seen = set()
    for _ in range(64):
        await RisingEdge(dut.clk_PAD)
        q, qb = pad_bit(dut, "do_q_PAD"), pad_bit(dut, "do_q_b_PAD")
        assert q is not None and qb == 1 - q
        seen.add(q)
    assert seen == {0, 1}
    await reg_write(dut, pads, A["BIAS_CFG_1"], ADC_CONV_EN | DSM_EN | DSM_RST_B)
    for _ in range(20):
        await RisingEdge(dut.clk_PAD)
        assert pad_bit(dut, "do_q_PAD") == 0 and pad_bit(dut, "do_q_b_PAD") == 0


@cocotb.test()
async def test_bias_cfg_reaches_dsm2(dut):
    """One field at a time: only its own control moves, so a swap between fields shows."""
    pads = await bringup(dut)
    dec_gate = core_cell(dut, "u_dec_src_gate")
    conv_gate = core_cell(dut, "u_adc_conv_gate")

    def cfg0_pins():
        d = dut.dsm2
        return (int(d.di_trim.value) | int(d.di_dith_en.value) << 4 | int(d.di_dith_amp.value) << 5)

    cfg1_names = ("DSM_EN", "DSM_RST_B", "DSM_BTEST_EN", "DSM_VCM_EXT", "DSM_QOUT_EN", "DEC_SRC", "ADC_CONV_EN")

    def cfg1_pins():
        d = dut.dsm2
        got = {"DSM_EN": d.di_ena, "DSM_RST_B": d.di_rst_b, "DSM_BTEST_EN": d.di_btest_en,
               "DSM_VCM_EXT": d.di_vcm_ext, "DSM_QOUT_EN": d.di_qout_en,
               "DEC_SRC": dec_gate.B, "ADC_CONV_EN": conv_gate.B}
        return {n: int(got[n].value) for n in cfg1_names}

    # BIAS_CFG_0: DSM_TRIM, DSM_DITH_EN and DSM_DITH_AMP are bits 0 to 6, the pins carry the same order
    lsb0 = min(f["lsb"] for f in regmap.REGS["BIAS_CFG_0"]["fields"] if f["name"] == "DSM_TRIM")
    for k in range(lsb0, lsb0 + 7):
        await reg_write(dut, pads, A["BIAS_CFG_0"], 1 << k)
        await reg_write(dut, pads, A["BIAS_CFG_1"], ADC_CONV_EN)
        await ClockCycles(dut.clk_PAD, 2)
        assert cfg0_pins() == 1 << k, f"BIAS_CFG_0 bit {k} gives dsm2 pins {cfg0_pins():07b}"
        assert cfg1_pins() == {n: int(n == "ADC_CONV_EN") for n in cfg1_names}

    await reg_write(dut, pads, A["BIAS_CFG_0"], 0)
    for name in cfg1_names:
        await reg_write(dut, pads, A["BIAS_CFG_1"], 1 << B1[name]["lsb"])
        await ClockCycles(dut.clk_PAD, 2)
        assert cfg1_pins() == {n: int(n == name) for n in cfg1_names}, f"{name} moved {cfg1_pins()}"
        assert cfg0_pins() == 0
    await reg_write(dut, pads, A["BIAS_CFG_1"], ADC_CONV_EN)


@cocotb.test()
async def test_dec_src_decimates_dsm2_bit_exact(dut):
    """DEC_SRC high, pads quiet: the decimator reads do_q_dec, word for word what the model gives."""
    pads = await bringup(dut)
    cocotb.start_soon(dsm_clock(dut))
    await reg_write(dut, pads, A["BIAS_CFG_1"], ADC_CONV_EN | DSM_EN | DSM_RST_B | DEC_SRC)
    words = []
    for _ in range(70):
        await wait_conversion(dut)
        words.append(await read_adc_word(dut, pads))
        assert pad_bit(dut, "do_q_PAD") == 0, "the pads must stay quiet with DSM_QOUT_EN low"
    # The stream starts at an unknown decimation phase p, and the filter forgets its history after about
    # 32 words, so words 40 to 69 must appear in the model for one p and one lag.
    bits = prbs15(128 * 100)
    hit = any(m[lg:lg + 30] == words[40:70]
              for p in range(128) for m in [DecimatorModel().run([0] * p + bits)]
              for lg in range(len(m) - 30))
    assert hit, f"no phase and lag reproduce the chip words {words[40:44]}"
    await reg_write(dut, pads, A["BIAS_CFG_1"], ADC_CONV_EN)


@cocotb.test()
async def test_adc_conv_en_holds_the_pad(dut):
    """ADC_CONV_EN low holds adc_conv low, high brings the strobe back."""
    pads = await bringup(dut)
    await reg_write(dut, pads, A["BIAS_CFG_1"], 0)
    for _ in range(3 * 128):
        await RisingEdge(dut.clk_PAD)
        assert adc_conv(dut) == 0
    await reg_write(dut, pads, A["BIAS_CFG_1"], ADC_CONV_EN)
    await wait_conversion(dut)


@cocotb.test()
async def test_dsa1_profile_then_reset_value_restores_data_in(dut):
    """The DSA1 bias resets here set DEC_SRC with dsm2 off and clear ADC_CONV_EN: the decimator reads
    dsm2's do_q_dec, which is low while dsm2 is off. Writing the reset value back brings data_in and the strobe back."""
    pads = await bringup(dut)
    pads.data_in(1)
    await reg_write(dut, pads, A["BIAS_CFG_0"], 0x90EA)
    await reg_write(dut, pads, A["BIAS_CFG_1"], 0xD02C)
    await ClockCycles(dut.clk_PAD, 40 * 128)      # no strobe on the pad now
    low = await read_adc_word(dut, pads)
    assert abs(low + FULL_SCALE) < FULL_SCALE // 50, f"DEC_SRC with dsm2 off (do_q_dec low) should read -full scale, got {low}"
    await reg_write(dut, pads, A["BIAS_CFG_1"], regmap.RESET[A["BIAS_CFG_1"]])
    for _ in range(40):
        await wait_conversion(dut)
    high = await read_adc_word(dut, pads)
    assert abs(high - FULL_SCALE) < FULL_SCALE // 50, f"data_in held at 1 should read +full scale, got {high}"


@cocotb.test(skip=os.getenv("PSD", "0").strip().lower() not in ("1", "true", "yes", "on"))
async def test_psd(dut):
    """Long run: feed the real modulator bitstream and check the decimated spectrum.

    Opt in with PSD=1. PSD_SAMPLES sets the number of output words, default
    1024.

    The stimulus is the CIFF4 record the HDL benches use, written by the MATLAB
    flow in jku-phd (system-level/matlab/tb_CIFF4_MOD_DEC.m and friends). It is
    81 MB, so it is read in place from STIM_FILE rather than copied here. Its
    conventions, from that bench: fs = 65536 Hz, a 42 Hz tone at -4 dBFS,
    4194304 samples, which is 64 s and hence the 1/64 Hz resolution the MATLAB
    PSD uses.

    Coherence is why 1024 is the default and why any multiple of 256 works: at
    the 512 Hz output rate a 1024-sample window holds exactly 84 cycles of
    42 Hz, so the tone lands on a bin whatever the start offset. The full
    record would be 32768 output words, which is the MATLAB resolution and
    takes hours here.
    """
    import math

    try:
        import numpy as np
    except ImportError:
        raise cocotb.result.SimFailure("numpy is required for the PSD test")

    log = logging.getLogger("psd")

    default_stim = Path.home() / (
        "projects/jku-phd/circuit-level/hdl/DSADC1/DEC/decimator_v5/sim/stim_dac_sine_dec.txt"
    )
    stim_file = Path(os.getenv("STIM_FILE", str(default_stim)))
    if not stim_file.is_file():
        raise cocotb.result.SimFailure(
            f"modulator bitstream not found at {stim_file}. "
            "Set STIM_FILE to stim_dac_sine_dec.txt in the jku-phd checkout."
        )

    FS_IN, DEC, F_IN, FB = 65536.0, 128, 42.0, 128.0
    n_out = int(os.getenv("PSD_SAMPLES", "1024"))
    n_settle = 40
    n_in = (n_out + n_settle + 2) * DEC

    # Only the leading part of the record is needed, so read it lazily.
    bits = []
    with stim_file.open() as fh:
        fh.readline()                      # header, "tvec Var2"
        for line in fh:
            parts = line.split()
            if len(parts) != 2:
                continue
            bits.append(1 if int(parts[1]) == 1 else 0)
            if len(bits) >= n_in:
                break
    assert len(bits) >= n_in, f"{stim_file} holds {len(bits)} samples, need {n_in}"
    log.info("read %d bits from %s", len(bits), stim_file)

    pads = await bringup(dut)

    async def feed():
        for b in bits:
            await RisingEdge(dut.clk_PAD)
            pads.data_in(b)
        while True:
            await RisingEdge(dut.clk_PAD)

    cocotb.start_soon(feed())

    # Let the filter fill before collecting. The window stays coherent whatever
    # the start offset, so discarding output samples here costs nothing.
    for _ in range(n_settle):
        await wait_conversion(dut)

    words = []
    for _ in range(n_out):
        await wait_conversion(dut)
        words.append(await read_adc_word(dut, pads))

    x = np.asarray(words, dtype=float) / FULL_SCALE
    x -= x.mean()
    X = np.fft.rfft(x)                     # no window: the tone is coherent
    psd = np.abs(X) ** 2
    fs_out = FS_IN / DEC
    freqs = np.fft.rfftfreq(len(x), d=1.0 / fs_out)

    k_expect = round(F_IN * len(x) / fs_out)
    k_tone = int(np.argmax(psd))
    log.info("tone bin %d (%.3f Hz), expected bin %d (%.3f Hz)",
             k_tone, freqs[k_tone], k_expect, F_IN)
    assert k_tone == k_expect, (
        f"tone landed in bin {k_tone} ({freqs[k_tone]:.3f} Hz), expected {k_expect}"
    )

    # Tone amplitude, referred to a full-scale sine's amplitude, which is the
    # convention the MATLAB bench and the report use. sqrt(2*psd)/N is the RMS,
    # so the extra sqrt(2) is what makes this -4 and not -7.
    tone_amp = math.sqrt(2.0 * psd[k_tone]) * math.sqrt(2.0) / len(x)
    tone_dbfs = 20 * math.log10(tone_amp) if tone_amp > 0 else -999
    log.info("tone level %.2f dBFS, amplitude referred to the 22-bit full scale", tone_dbfs)

    band = freqs <= FB
    sig = psd[max(k_tone - 1, 0):k_tone + 2].sum()
    noise = psd[band].sum() - sig
    sndr = 10 * math.log10(sig / noise) if noise > 0 else 999
    log.info("in-band SNDR %.1f dB over %d output samples", sndr, n_out)

    assert -5.0 < tone_dbfs < -3.0, f"tone came out at {tone_dbfs:.1f} dBFS, expected near -4"
    assert sndr > 100.0, f"in-band SNDR only {sndr:.1f} dB"

    # The stopband is everything above the passband edge. Nyquist of the 512 Hz
    # output is 256 Hz, so this band is FB to 2*FB and there is nothing beyond
    # it: asking for bins above 2*FB gives an empty array, not a lenient check.
    stopband = freqs > FB
    assert stopband.any(), "no bins above the passband edge, check PSD_SAMPLES"
    rejection = 10 * math.log10(psd[k_tone] / psd[stopband].max())
    log.info("largest bin above %.0f Hz is %.1f dB below the tone", FB, rejection)
    assert rejection > 80.0, f"out-of-band rejection only {rejection:.1f} dB"


# ----------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------

def sg13cmos5l_dsa1_dig_top_runner():
    proj_path = Path(__file__).resolve().parent
    root_path = proj_path.parent.parent

    sources  = []
    defines  = {}
    includes = [root_path / "rtl"]

    # The one macro on this die is hardened on EZ130, which is a prerelease and
    # does not ship in this repo. Its cell models are read from EZ130_DIR, the
    # same variable the macro Makefiles use.
    ez130_dir = os.environ.get("EZ130_DIR", str(Path.home() / "projects/OpenBLAU/ip/ez130_8t_v1p1"))
    ez130_models = Path(ez130_dir) / "verilog" / "ez130_8t.v"
    if not ez130_models.is_file():
        raise FileNotFoundError(
            f"EZ130 models not found at {ez130_models}. Set EZ130_DIR to the ez130_8t_v1p1 checkout."
        )

    if gl:
        sources.append(Path(pdk_root) / pdk / "libs.ref" / scl / "verilog" / f"{scl}.v")
        sources.append(Path(pdk_root) / pdk / "libs.ref" / scl / "verilog" / "sg13cmos5l_udp.v")
        sources.append(root_path / f"netlist/nl/{hdl_toplevel}.nl.v")
    else:
        sources.append(root_path / "rtl/sg13cmos5l_dsa1_dig_top.sv")
        sources.append(root_path / "rtl/sg13cmos5l_dsa1_dig_core.sv")

    # dsa1_dig_top is a hard macro either way: its RTL is VHDL, which Icarus
    # cannot read, so both flavours take its hardened netlist plus the EZ130
    # models and the empty stubs for the library's LEF-only cells. The macro's
    # own RTL-against-netlist equality is proved by
    # make -C macros/dsa1_dig sim-gl.
    sources.append(ez130_models)
    sources.append(root_path / "macros/scripts/ez130_phys_stubs.v")
    sources.append(root_path / "macros/dsa1_dig/final/nl/dsa1_dig_top.nl.v")

    sources += [
        root_path / "ip/dsm2_core/verilog/dsm2_core_model.v",
        root_path / "ip/sg13cmos5l_ip__cut_vdd/verilog/sg13cmos5l_ip__cut_vdd.v",
        root_path / "ip/sg13cmos5l_ip__bondpad_70x70/final/vh/sg13cmos5l_ip__bondpad_70x70.vh",
        root_path / "ip/sg13cmos5l_io_custom/verilog/sg13cmos5l_io.v",
        root_path / "ip/sg13cmos5l_ip__clamp_vddvss/verilog/sg13cmos5l_ip__clamp_vddvss.v",
        root_path / "ip/sg13cmos5l_ip__jku/final/vh/sg13cmos5l_ip__jku.vh",
        root_path / "ip/sg13cmos5l_ip__jku_names/final/vh/sg13cmos5l_ip__jku_names.vh",
    ]

    build_args = []

    if sim == "icarus":
        # -gno-specify: skip specify blocks; the cell Verilog uses `ifnone`
        # with edge-sensitive paths, which iverilog cannot parse.
        build_args = ["-DSIM", "-gno-specify"]

    if sim == "verilator":
        build_args = ["--timing", "--trace", "--trace-fst", "--trace-structs"]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel=hdl_toplevel,
        defines=defines,
        always=True,
        includes=includes,
        build_args=build_args,
        waves=True,
        timescale=("1ns", "1fs")
    )

    results = runner.test(
        hdl_toplevel=hdl_toplevel,
        test_module="sg13cmos5l_dsa1_dig_top_tb",
        plusargs=[],
        waves=True,
    )
    # runner.test() returns normally when a test fails, so make would pass
    num_tests, num_failed = get_results(results)
    if num_failed:
        sys.exit(f"{num_failed} of {num_tests} cocotb tests failed")


if __name__ == "__main__":
    sg13cmos5l_dsa1_dig_top_runner()
