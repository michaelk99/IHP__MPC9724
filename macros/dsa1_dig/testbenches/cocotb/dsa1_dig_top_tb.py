# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Macro-level testbench for dsa1_dig_top: the SPI register file, the ports it drives, adc_conv and the decimator.

Runs on the RTL (the ghdl-synthesized VHDL plus the decimator SystemVerilog) and, with GL=1, on the hardened netlist in FINAL_DIR.
The eight stimulus patterns are checked by `make sim-gl` and `make model-gate`, not here.

SPI frame of dsa1_ic_bus_slave, 23 falling sclk edges with ss low: 5 address bits MSB first (bit 4 set means read), 1 load cycle, 16 data bits MSB first, 1 store cycle.
clk runs at 50 ns and sclk at 20 ns as in dsa1_dig_top_tb.v. sclk must be the faster one, the register file captures an ADC word only on sclk edges.
"""

import os
import sys
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, Timer
from cocotb_tools.runner import get_runner

_HERE = Path(__file__).resolve().parent
_MACRO = _HERE.parents[1]
_REPO = _HERE.parents[3]
sys.path.insert(0, str(_REPO / "models"))
import regmap  # noqa: E402
from decimator_model import DecimatorModel  # noqa: E402

sim = os.getenv("SIM", "icarus")
# GL=1 selects the gate-level netlist, anything else stays in RTL mode.
gl = os.getenv("GL", "0").strip().lower() in ("1", "true", "yes", "on")
ez130_dir = Path(os.getenv("EZ130_DIR", str(_REPO / "ip/ez130_8t_v1p1"))).expanduser()
final_dir = Path(os.getenv("FINAL_DIR", str(_MACRO / "final")))

hdl_toplevel = "dsa1_dig_top"

CLK_PERIOD_NS = 50
SCLK_PERIOD_NS = 20
OUT_PERIOD = 128          # clk cycles per output word
FULL_SCALE = 1 << 20      # a constant 1 on data_in
READ_LAG = 0              # model words ahead of the SPI read, see test_data_in_decimates_bit_exact

A = regmap.ADDR
R = regmap.RESET
ADC_HIGH, ADC_LOW = A["ADC_DATA_CH0_HIGH"], A["ADC_DATA_CH0_LOW"]
CHIP_ID, TEST_CTRL_0 = A["CHIP_ID"], A["TEST_CTRL_0"]
# TEST_CTRL_0 is never written here: bit 9 and 11 in bits 7:6 are forbidden, see models/regmap.py
WRITABLE = ["BIAS_CFG_0", "BIAS_CFG_1", "BIAS_CFG_2", "BLOCK_CTRL_0", "TRIM_CFG_0", "CLK_CFG_0",
            "UWB_TX_CFG_0", "UWB_TX_CFG_1", "AUX_CTRL_0", "TEST_CTRL_1", "SPARE_14"]


def ports(regs):
    """The output ports for register values {addr: value}, as dsa1_ic_bus_slave maps them."""
    r = {name: regs[A[name]] for name in A}
    return {
        "o_bias_cfg": (r["BIAS_CFG_1"] << 19) | (r["BIAS_CFG_0"] << 3) | (r["BIAS_CFG_2"] & 0x7),
        "o_rst_ctrl_b": r["BLOCK_CTRL_0"] >> 14,
        "o_en_ctrl": r["BLOCK_CTRL_0"] & 0x7FF,
        "o_lf_cfg": r["TRIM_CFG_0"],
        "o_clk_cfg": (((r["BLOCK_CTRL_0"] >> 11) & 0x7) << 16) | r["CLK_CFG_0"],
        "o_tst_ctrl": r["TEST_CTRL_0"],
        "o_uwb_tx_cfg": ((r["UWB_TX_CFG_1"] & 0x7FFF) << 15) | (r["UWB_TX_CFG_0"] & 0x7FFF),
        "o_aux_ctrl": r["AUX_CTRL_0"],
    }


def check_ports(dut, regs):
    for name, want in ports(regs).items():
        got = int(getattr(dut, name).value)
        assert got == want, f"{name} is {got:#x}, the registers give {want:#x}"


async def sclk_run(dut):
    """Free-running sclk, a quarter period off, so no sclk edge lands on a rising clk edge."""
    await Timer(SCLK_PERIOD_NS / 4, "ns")
    while True:
        dut.sclk.value = 1
        await Timer(SCLK_PERIOD_NS / 2, "ns")
        dut.sclk.value = 0
        await Timer(SCLK_PERIOD_NS / 2, "ns")


async def spi(dut, addr, wdata=0):
    """One frame. Returns the 16 bits shifted out on miso."""
    frame = ((addr & 0x1F) << 18) | ((wdata & 0xFFFF) << 1)
    rdata = 0
    await FallingEdge(dut.sclk)
    await Timer(1, "ns")
    dut.ss.value = 0
    dut.mosi.value = (frame >> 22) & 1
    for k in range(22, -1, -1):
        await FallingEdge(dut.sclk)
        if 1 <= k <= 16:
            rdata = ((rdata << 1) | int(dut.miso.value)) & 0xFFFF
        await Timer(1, "ns")
        dut.mosi.value = (frame >> (k - 1)) & 1 if k > 0 else 0
    await FallingEdge(dut.sclk)
    await Timer(1, "ns")
    dut.ss.value = 1
    return rdata


async def reg_read(dut, addr):
    return await spi(dut, 0x10 | addr)


async def reg_write(dut, addr, value):
    await spi(dut, addr, value)


async def read_adc_word(dut):
    """The 22-bit word, signed. HIGH first, its read freezes LOW."""
    hi = await reg_read(dut, ADC_HIGH)
    lo = await reg_read(dut, ADC_LOW)
    w = ((hi & 0x3F) << 16) | lo
    return w - (1 << 22) if w & (1 << 21) else w


async def wait_conversion(dut):
    """The next adc_conv pulse, then time for the flag synchronizer."""
    await RisingEdge(dut.adc_conv)
    await Timer(4 * SCLK_PERIOD_NS, "ns")


async def bringup(dut):
    dut.rst_b.value = 0
    dut.ss.value = 1
    dut.mosi.value = 0
    dut.sclk.value = 0
    dut.data_in.value = 0
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, "ns").start())
    cocotb.start_soon(sclk_run(dut))
    # The decimator reset is synchronous, so hold it over several clk edges.
    await ClockCycles(dut.clk, 10)
    dut.rst_b.value = 1
    await ClockCycles(dut.clk, 2)


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def test_reset_values_and_ports(dut):
    """Every register but the ADC words reads its regmap reset value, and the ports carry it."""
    await bringup(dut)
    for name, addr in A.items():
        if addr in (ADC_HIGH, ADC_LOW):
            continue
        got = await reg_read(dut, addr)
        assert got == R[addr], f"{name} reads {got:#06x} after reset, regmap says {R[addr]:#06x}"
    check_ports(dut, R)


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def test_write_read_and_ports(dut):
    """Each writable register takes its inverted reset value, reads it back and drives it onto its port bits."""
    await bringup(dut)
    regs = dict(R)
    for name in WRITABLE:
        addr = A[name]
        regs[addr] = ~R[addr] & 0xFFFF
        await reg_write(dut, addr, regs[addr])
        got = await reg_read(dut, addr)
        assert got == regs[addr], f"{name}: wrote {regs[addr]:#06x}, read {got:#06x}"
        check_ports(dut, regs)
    for value in (~R[CHIP_ID] & 0xFFFF, 0):
        await reg_write(dut, CHIP_ID, value)
        got = await reg_read(dut, CHIP_ID)
        assert got == R[CHIP_ID], f"CHIP_ID took a write of {value:#06x}, reads {got:#06x}"


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def test_adc_conv_cadence(dut):
    """adc_conv is one clk wide, once every 128 clk."""
    await bringup(dut)
    rises, width, high, n = [], 0, 0, 0
    for _ in range(OUT_PERIOD * 6):
        await RisingEdge(dut.clk)
        await Timer(1, "ns")
        v = int(dut.adc_conv.value)
        if v and not high:
            rises.append(n)
        width = max(width, high + 1) if v else width
        high = high + 1 if v else 0
        n += 1
    gaps = {b - a for a, b in zip(rises, rises[1:])}
    assert len(rises) >= 5 and gaps == {OUT_PERIOD}, f"adc_conv rises at {rises}"
    assert width == 1, f"adc_conv stays high for {width} clk"


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def test_dec_en_holds_the_decimator(dut):
    """BLOCK_CTRL_1 bit 0 low holds the decimator in reset, so adc_conv stops. Set again, it comes back."""
    await bringup(dut)
    addr = A["BLOCK_CTRL_1"]
    await reg_write(dut, addr, R[addr] & ~1)
    await ClockCycles(dut.clk, 6)      # the enable crosses a 3-flop synchronizer
    for _ in range(OUT_PERIOD * 3):
        await RisingEdge(dut.clk)
        assert int(dut.adc_conv.value) == 0, "adc_conv fired with the decimator disabled"
    await reg_write(dut, addr, R[addr])
    await wait_conversion(dut)


def prbs15(n):
    lfsr, out = 1, []
    for _ in range(n):
        out.append(lfsr & 1)
        lfsr = ((lfsr << 1) | (((lfsr >> 14) ^ (lfsr >> 13)) & 1)) & 0x7FFF
    return out


async def drive_bits(dut, bits):
    for b in bits:
        await RisingEdge(dut.clk)
        await Timer(1, "ns")
        dut.data_in.value = b


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def test_data_in_decimates_bit_exact(dut):
    """A PRBS15 on data_in, read over SPI, must match the bit-true model word for word.

    The decimator leaves reset on the edge that takes bits[0], so the model starts in phase. Word k read over SPI is model word k + READ_LAG.
    """
    await bringup(dut)
    bits = prbs15(OUT_PERIOD * 100)
    cocotb.start_soon(drive_bits(dut, bits))
    words = []
    for _ in range(70):
        await wait_conversion(dut)
        words.append(await read_adc_word(dut))
    m = DecimatorModel().run(bits)
    lags = [lg for lg in range(-40, len(m) - 69) if m[40 + lg:70 + lg] == words[40:70]]
    assert lags == [READ_LAG], f"words 40 to 69 match the model at lags {lags}, expected [{READ_LAG}]"


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def test_full_scale(dut):
    """data_in held at 1 settles on +full scale, held at 0 on -full scale."""
    await bringup(dut)
    for level, want in ((1, FULL_SCALE), (0, -FULL_SCALE)):
        dut.data_in.value = level
        for _ in range(40):
            await wait_conversion(dut)
        got = await read_adc_word(dut)
        assert abs(got - want) < FULL_SCALE // 50, f"data_in {level} reads {got}, expected about {want}"


def dsa1_dig_top_runner():
    sources = []
    if gl:
        # EZ130 cell models plus empty stubs for its LEF-only cells, which the netlist needs to elaborate.
        sources.append(ez130_dir / "verilog" / "ez130_8t.v")
        sources.append(_MACRO / "../scripts/ez130_phys_stubs.v")
        # Unpowered netlist, so USE_POWER_PINS stays undefined.
        sources.append(final_dir / "nl" / f"{hdl_toplevel}.nl.v")
    else:
        # The ghdl output of `make rtl-gen`, then the decimator RTL in the order of DEC_SRCS.
        sources.append(_MACRO / "rtl_gen" / f"{hdl_toplevel}.v")
        for name in ("ce_generator", "cic_n6_d32", "sinc2_chain", "comp_fir", "decimator_core", "decimator_top"):
            sources.append(_MACRO / "../decimator/rtl" / f"{name}.sv")

    build_args = []
    if sim == "icarus":
        # -gno-specify: zero delay, ignore the cell timing.
        build_args = ["-DSIM", "-gno-specify"]
    if sim == "verilator":
        build_args = ["--timing", "--trace", "--trace-fst", "--trace-structs"]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel=hdl_toplevel,
        defines={},
        always=True,
        includes=[_MACRO / "rtl"],
        build_args=build_args,
        waves=True,
        timescale=("1ns", "1fs"),
    )
    runner.test(hdl_toplevel=hdl_toplevel, test_module="dsa1_dig_top_tb", plusargs=[], waves=True)


if __name__ == "__main__":
    dsa1_dig_top_runner()
