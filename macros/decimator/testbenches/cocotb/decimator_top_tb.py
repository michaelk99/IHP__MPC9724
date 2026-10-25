# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Gate the decimator macro against the bit-true model in models/decimator_model.py.

Runs on the RTL and, with GL=1, on the hardened netlist. No hierarchical
references, the netlist is flat. The model is the specification: the RTL is
correct only if it reproduces it sample for sample, so every test here compares
against the model rather than against a hand-written expectation.
"""

import os
import random
import sys
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer
from cocotb_tools.runner import get_runner

_REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO / "models"))
from decimator_model import DATA_W, DecimatorModel, comp_tap_value  # noqa: E402

sim = os.getenv("SIM", "icarus")
# GL=1 selects the gate-level netlist; anything else (unset, "0", "") stays in RTL mode.
gl = os.getenv("GL", "0").strip().lower() in ("1", "true", "yes", "on")
ez130_dir = Path(os.getenv("EZ130_DIR", "~/projects/OpenBLAU/ip/ez130_8t_v1p1")).expanduser()

hdl_toplevel = "decimator_top"

CLK_PERIOD_NS = 1000  # only the ratio matters, the macro is constrained at 1 us
OUT_PERIOD = 128      # clk_fs cycles per output sample, from ce_generator.sv


def _signed(raw: int, width: int = DATA_W) -> int:
    return raw - (1 << width) if raw & (1 << (width - 1)) else raw


async def start_up(dut):
    """Clock, then release the synchronous reset with data_in held at -1."""
    cocotb.start_soon(Clock(dut.clk_fs, CLK_PERIOD_NS, "ns").start())
    dut.rst_b.value = 0
    dut.data_in.value = 0
    await ClockCycles(dut.clk_fs, 5)


async def feed(dut, model, bits):
    """Drive the bitstream and collect (model, dut) pairs at every valid_strobe.

    rst_b is released together with the first bit, so the first counted edge is
    the model's first step() and the two stay in phase with no lag search.
    """
    pairs = []
    dut.rst_b.value = 1
    for b in bits:
        dut.data_in.value = b
        await RisingEdge(dut.clk_fs)
        await Timer(1, "ns")  # let the outputs settle past the edge
        expect = model.step(b)
        if int(dut.valid_strobe.value):
            got = _signed(int(dut.data_out.value))
            pairs.append((expect, got))
    return pairs


@cocotb.test()
async def test_reset_clears_output(dut):
    """data_out and valid_strobe must be zero while rst_b is low."""
    await start_up(dut)
    assert int(dut.data_out.value) == 0, f"data_out not zero in reset ({int(dut.data_out.value)})"
    assert int(dut.valid_strobe.value) == 0, "valid_strobe asserted in reset"


@cocotb.test()
async def test_valid_strobe_cadence(dut):
    """valid_strobe must fire once every 128 clk_fs cycles."""
    await start_up(dut)
    model = DecimatorModel()
    marks = []

    dut.rst_b.value = 1
    for i in range(OUT_PERIOD * 6):
        dut.data_in.value = i & 1
        await RisingEdge(dut.clk_fs)
        await Timer(1, "ns")
        model.step(i & 1)
        if int(dut.valid_strobe.value):
            marks.append(i)

    assert len(marks) >= 5, f"only {len(marks)} strobes in {OUT_PERIOD * 6} cycles"
    gaps = {b - a for a, b in zip(marks, marks[1:])}
    assert gaps == {OUT_PERIOD}, f"strobe spacing {sorted(gaps)}, expected {OUT_PERIOD}"


@cocotb.test()
async def test_dc_gain(dut):
    """A held +1 input must settle on 2^20 times the compensator dc gain.

    This is the one absolute check in the file. Everything else asks whether the
    RTL equals the model, which cannot catch a scaling error they would share.
    """
    await start_up(dut)
    model = DecimatorModel()
    pairs = await feed(dut, model, [1] * (OUT_PERIOD * 70))

    dc = sum(comp_tap_value(t) for t in range(4)) * 2 + comp_tap_value(4)
    want = round((1 << 20) * dc)
    settled = pairs[-1][1]
    assert settled == want, f"dc output {settled}, expected {want}"
    assert pairs[-1][0] == want, f"model dc output {pairs[-1][0]}, expected {want}"


@cocotb.test()
async def test_matches_bit_true_model(dut):
    """A pseudorandom bitstream must match the model at every output sample."""
    await start_up(dut)
    rng = random.Random(20260922)
    bits = [rng.getrandbits(1) for _ in range(OUT_PERIOD * 80)]

    model = DecimatorModel()
    pairs = await feed(dut, model, bits)

    assert len(pairs) >= 78, f"only {len(pairs)} output samples"
    bad = [(i, e, g) for i, (e, g) in enumerate(pairs) if e != g]
    assert not bad, f"{len(bad)} of {len(pairs)} samples differ, first three {bad[:3]}"
    cocotb.log.info("%d output samples match the bit-true model", len(pairs))


def decimator_top_runner():
    proj_path = Path(__file__).resolve().parent
    rtl = proj_path / "../../rtl"

    sources = []
    includes = [rtl]

    if gl:
        # EZ130 cell models plus empty stubs for its LEF-only cells (FILLER*,
        # WELLTAP), which the netlist needs in order to elaborate. The macro is
        # hardened on EZ130, not on the PDK standard cells.
        sources.append(ez130_dir / "verilog" / "ez130_8t.v")
        sources.append(proj_path / "../../../scripts/ez130_phys_stubs.v")
        # Unpowered netlist: USE_POWER_PINS must NOT be defined at all
        # (passing USE_POWER_PINS=False would still define the macro).
        sources.append(proj_path / f"../../final/nl/{hdl_toplevel}.nl.v")
    else:
        # Listed, not globbed, so the order is the same every run.
        for name in ("ce_generator", "cic_n6_d32", "sinc2_chain", "comp_fir",
                     "decimator_core", "decimator_top"):
            sources.append(rtl / f"{name}.sv")

    build_args = []
    if sim == "icarus":
        # -gno-specify: skip specify blocks, which iverilog cannot parse here.
        build_args = ["-DSIM", "-gno-specify"]
    if sim == "verilator":
        build_args = ["--timing", "--trace", "--trace-fst", "--trace-structs"]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel=hdl_toplevel,
        defines={},
        always=True,
        includes=includes,
        build_args=build_args,
        waves=True,
        timescale=("1ns", "1fs"),
    )
    runner.test(
        hdl_toplevel=hdl_toplevel,
        test_module="decimator_top_tb",
        plusargs=[],
        waves=True,
    )


if __name__ == "__main__":
    decimator_top_runner()
