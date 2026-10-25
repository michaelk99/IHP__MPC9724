# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Check a decimator_top_out.txt against the bit-true model.

make sim-gl proves the hardened netlist equals the RTL. It cannot prove either
one is right, because both come from the same source. This reproduces the
stimulus of testbenches/verilog/decimator_top_tb.v in Python, runs the model on
it and requires every one of the 500 output samples to match, which turns that
equality into a correctness check.

    python3 models/gate_decimator_out.py macros/decimator/sims/rtl/decimator_top_out.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decimator_model import DecimatorModel  # noqa: E402

# Must track decimator_top_tb.v
N_STEP = 100      # output samples of step response
N_PRBS = 400      # output samples of pseudo-random input
STEP_EDGE = 64    # clk_fs edges after reset release before data_in goes to +1


class _Prbs23:
    """x^23 + x^18 + 1, seeded at 1, as the testbench runs it.

    The testbench advances the register on the edge and reads bit 0 one
    nanosecond later, so the bit the DUT consumes at the next edge is the
    feedback term of the advance just taken.
    """

    def __init__(self, seed: int = 1):
        self.state = seed

    def next_bit(self) -> int:
        fb = ((self.state >> 22) & 1) ^ ((self.state >> 17) & 1)
        self.state = ((self.state << 1) | fb) & 0x7FFFFF
        return fb


def reference() -> list:
    """The 500 output samples the testbench must produce."""
    model = DecimatorModel()
    out = []

    # Reset releases with data_in at -1, then a step to +1 STEP_EDGE edges later.
    bit, edge = 0, 0
    while len(out) < N_STEP:
        edge += 1
        y = model.step(bit)
        if y is not None:
            out.append(y)
        if edge == STEP_EDGE:
            bit = 1

    # The testbench leaves its wait on the negedge after the N_STEP'th sample, so
    # the first edge of the PRBS loop still carries the step value.
    y = model.step(1)
    if y is not None:
        out.append(y)

    prbs = _Prbs23()
    while len(out) < N_STEP + N_PRBS:
        y = model.step(prbs.next_bit())
        if y is not None:
            out.append(y)
    return out


def main(argv) -> int:
    if len(argv) != 2:
        print("usage: gate_decimator_out.py <decimator_top_out.txt>")
        return 2

    got = [int(line) for line in Path(argv[1]).read_text().split() if line.strip()]
    want = reference()

    if len(got) != len(want):
        print(f"FAIL: {argv[1]} has {len(got)} samples, model has {len(want)}")
        return 1

    bad = [i for i, (a, b) in enumerate(zip(want, got)) if a != b]
    if bad:
        print(f"FAIL: {len(bad)} of {len(want)} samples differ, first at {bad[:3]}")
        for i in bad[:3]:
            print(f"  sample {i}: model {want[i]}, sim {got[i]}")
        return 1

    print(f"OK: {len(want)} samples match the bit-true model ({argv[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
