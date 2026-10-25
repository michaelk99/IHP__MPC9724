#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""DC supply current of each IO cell type, and the static current the IO cells of a chip should draw.

    python3 testbenches/startup/cell_leakage.py [--v111 verification/startup/power_v111.json]    inside the image, after run_startup.sh

Each cell sits alone on its supplies, one ngspice .op per pad and input level (an analog pad at 0 or half the rail), in the bench's models and the image PDK's IO SPICE.
Outputs and supply pads idle low, input, bidirectional and analog pads take the mean of the two levels.
The prediction sums these over the cell counts of this chip's netlist and, with --v111, of the tag's, per supply.
What the bench measures above it is the switching of the two toggling inputs.
It writes verification/startup/cell_leakage.md.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "../.."))
B = os.path.join(HERE, "build")
IO = os.path.join(os.environ["PDK_ROOT"], os.environ["PDK"], "libs.ref/sg13cmos5l_io/spice/sg13cmos5l_io.spice")
CHIP_PNL = os.path.join(ROOT, "netlist/pnl/sg13cmos5l_dsa1_dig_top.pnl.v")
# the cells whose pad or input toggles or is driven in the DSA1 state are run low and high and averaged, the others idle low
TWO_LEVELS = {"sg13cmos5l_IOPadIn", "sg13cmos5l_IOPadInOut30mA", "sg13cmos5l_IOPadAnalog"}
RAIL_V = {"VDD": 1.2, "VDDA": 1.5}
DECK = """* one IO cell, written by cell_leakage.py
.lib cornerMOSlv.lib mos_tt
.lib cornerMOShv.lib mos_tt
.lib cornerRES.lib res_typ
.include diodes_bench.lib
.include sg13g2_esd.lib
.include {io}
.include clamp.spice
.global sub!
Vsub sub! 0 0
VIOVDD iovdd 0 3.3
VIOVSS iovss 0 0
VVSS vss 0 0
VVDD vdd 0 {v}
X1 {conns} {cell}
{extra}
.options method=gear
.op
.control
run
print i(VIOVDD) i(VVDD)
quit
.endc
.end
"""


def pins(cell):
    for fn in (IO, os.path.join(B, "clamp.spice")):
        for ln in open(fn):
            m = re.match(r"\s*\.subckt\s+%s\s+(.*)" % cell, ln, re.I)
            if m:
                return m.group(1).split()
    raise SystemExit(f"no .subckt {cell}")


def run(cell, rail, high):
    v = RAIL_V[rail]
    conns, extra = [], []
    for p in pins(cell):
        conns.append({"c2p_en": "en"}.get(p, p))
        if p == "pad":
            extra.append(f"Vpad pad 0 {(v / 2 if cell.endswith('Analog') else 3.3) if high else 0}")
            if "Out" in cell and "InOut" not in cell:
                extra[-1] = "Rpad pad 0 1Meg"
        elif p == "padres":
            extra.append("Rpr padres 0 1Meg")
        elif p == "c2p":
            extra.append(f"Vc2p c2p 0 {v if high else 0}")
        elif p == "c2p_en":
            extra.append("Ven en 0 0")
        elif p == "p2c":
            extra.append("Cp2c p2c 0 1f")
    open(os.path.join(B, "leak.cir"), "w").write(DECK.format(io=IO, v=v, conns=" ".join(conns), cell=cell, extra="\n".join(extra)))
    out = subprocess.run(["ngspice", "-b", "leak.cir"], cwd=B, capture_output=True, text=True)
    text = out.stdout + out.stderr
    a, b = re.search(r"i\(viovdd\) = (\S+)", text), re.search(r"i\(vvdd\) = (\S+)", text)
    if not (a and b):
        raise SystemExit(f"{cell}: no .op result\n{text[-800:]}")
    return -float(a.group(1)), -float(b.group(1))


def counts(pnl):
    """{(cell, rail of its vdd pin): n} of a chip netlist."""
    text = open(pnl).read()
    n = {}
    for m in re.finditer(r"^ (sg13cmos5l_(?:IOPad\w+|ip__clamp_vddvss)) \S+\s+\((.*?)\);", text, flags=re.M | re.S):
        v = re.search(r"\.vdd\((\w+)\)", m.group(2))
        key = (m.group(1), v.group(1) if v else "VDD")
        n[key] = n.get(key, 0) + 1
    return n


def predict(table, n):
    """{supply: nA} from the per-cell table, a clamp's vdd pin is the rail it clamps."""
    tot = {"IOVDD": 0.0, "VDD": 0.0, "VDDA": 0.0}
    for (cell, rail), k in n.items():
        lo, hi = table[(cell, rail)]
        i = tuple((x + y) / 2 for x, y in zip(lo, hi))
        tot["IOVDD"] += k * i[0]
        tot[rail] += k * i[1]
    return tot


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--v111", help="power_v111.json, for the tag's cell counts")
    ap.add_argument("--out", default=os.path.join(ROOT, "verification/startup/cell_leakage.md"))
    a = ap.parse_args()
    sets = [("this chip", counts(CHIP_PNL))]
    if a.v111:
        old = json.load(open(a.v111))
        sets.append((old["tag"], {(c, "VDD"): k for c, k in old["inventory"].items()}))
    table, lines = {}, ["# DC supply current of the IO cells", "", "| cell | rail | pad and input | IOVDD (nA) | rail (nA) |", "|---|---|---|---|---|"]
    for cell, rail in sorted({key for _, n in sets for key in n}):
        lo = tuple(x * 1e9 for x in run(cell, rail, False))
        both = cell in TWO_LEVELS
        hi = tuple(x * 1e9 for x in run(cell, rail, True)) if both else lo
        table[(cell, rail)] = (lo, hi)
        lines.append(f"| {cell} | {rail} | {'low' if both else 'idle'} | {lo[0]:.3f} | {lo[1]:.3f} |")
        if both:
            lines.append(f"| {cell} | {rail} | high | {hi[0]:.3f} | {hi[1]:.3f} |")
    lines += ["", "Predicted static current in the DSA1 state, from the cell counts:", ""]
    for name, n in sets:
        p = predict(table, n)
        lines.append(f"- {name}: IOVDD {p['IOVDD']:.2f} nA, VDD {p['VDD']:.2f} nA" + (f", VDDA {p['VDDA']:.2f} nA" if p["VDDA"] else ""))
    open(a.out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
