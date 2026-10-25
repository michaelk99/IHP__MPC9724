# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: abutment test, the cut cell between two IO pads
#
#   klayout -b -r cut_abut.py -rd out=<dir> [-rd gds=<cut gds>]
#
# Writes rows into <dir>: IOPadIn, cut, IOPadOut4mA and IOPadVss, cut, IOPadIn,
# abutted, with a Filler2000 and with a Filler4000 on each side, each pad with
# its bondpad at LibreLane's offset. Each row comes with a reference row that has
# a Filler2000 in the slot, which is what the ring has without the cell. The DRC
# of both is compared by clamp's drc_report.py.
#
# Here: every conductor the filler carries across the seams of the cell must
# carry across too, except the vdd band on Metal3 and Metal4, which has to end
# exactly at the cell's two edges, 10 um apart.

import os
import re
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "sg13cmos5l_ip__clamp_vddvss", "layout"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))
import clamp_abut as ca                  # noqa: E402
import rails as rails_mod                # noqa: E402
from gdswrite import write_gds           # noqa: E402

CELL = "sg13cmos5l_ip__cut_vdd"
FILLER = rails_mod.FILLER
ROWS = {"inout": ("sg13cmos5l_IOPadIn", "sg13cmos5l_IOPadOut4mA"),
        "vssin": ("sg13cmos5l_IOPadVss", "sg13cmos5l_IOPadIn")}


def build(ly, name, pads, side, ours):
    top = ly.create_cell(name)
    row = [pads[0]] + ([side] if side else []) + [CELL if ours else FILLER] \
        + ([side] if side else []) + [pads[1]]
    x, seams, cut_x = 0.0, [], None
    for i, cell in enumerate(row):
        if i == len(row) // 2:
            cut_x = x
        top.insert(pya.DCellInstArray(ly.cell(cell).cell_index(), pya.DTrans(x, 0.0)))
        if cell.startswith("sg13cmos5l_IOPad"):
            top.insert(pya.DCellInstArray(ly.cell(ca.BOND).cell_index(),
                                          pya.DTrans(x + ca.BOND_OFFSET[0], ca.BOND_OFFSET[1])))
        x += ca.width_of(ly, cell)
        seams.append(x)
    return top, seams[:-1], cut_x


def vdd_gap(ly, top, x0, x1):
    """Problems with the vdd band: it has to end at x0 and restart at x1."""
    bad = []
    per = {}
    for layer, y0, y1 in rails_mod.rails()["vdd"]:
        per.setdefault(layer, []).append((y0, y1))
    for layer, rngs in per.items():
        l, d = ca.LAY[layer]
        reg = pya.Region(top.begin_shapes_rec(ly.layer(l, d))).merged()
        for y0, y1 in rngs:
            def box(a, b):
                return pya.Region(pya.DBox(a, y0, b, y1).to_itype(ly.dbu))
            if not (reg & box(x0, x1)).is_empty():
                bad.append("%s %g..%g has metal inside the cell" % (layer, y0, y1))
            for a, b in ((x0 - 0.5, x0), (x1, x1 + 0.5)):
                if not (box(a, b) - reg).is_empty():
                    bad.append("%s %g..%g is not solid at x %g..%g" % (layer, y0, y1, a, b))
    return bad, per


def main():
    out = globals().get("out")
    gds = globals().get("gds") or os.path.join(HERE, "..", "gds", CELL + ".gds")
    os.makedirs(out, exist_ok=True)
    rc = 0
    rows = []
    for rname, pads in ROWS.items():
        for sname, side in ca.SIDES.items():
            res = {}
            for ours in (True, False):
                ly = pya.Layout()
                ly.read(ca.IO_GDS)
                ly.read(ca.BOND_GDS)
                ly.read(gds)
                tag = "cut_%s_%s%s" % (rname, sname, "" if ours else "_ref")
                top, seams, x0 = build(ly, tag, pads, side, ours)
                for ci in [c.cell_index() for c in ly.top_cells()]:
                    if ci != top.cell_index():
                        ly.prune_cell(ci, -1)
                write_gds(ly, os.path.join(out, tag + ".gds"))
                res[ours] = ca.seams_check(ly, top, seams)
                if ours:
                    x1 = x0 + ca.width_of(ly, CELL)
                    rows.append("%s %g %g" % (tag, x0, x1))
                    gap, per = vdd_gap(ly, top, x0, x1)
                    print("%s: cell x %g..%g, %d breaks" % (tag, x0, x1, len(res[ours])))
            extra = res[True] - res[False]
            # the breaks the vdd band must have: its layers, at the cell's two edges
            want = set()
            for layer, rngs in per.items():
                for xs, which in ((x0, "left only"), (x1, "right only")):
                    want.add((layer, "seam x %g" % xs, which))
            seen = set()
            for b in sorted(extra):
                m = re.match(r"(\w+)/(seam x \S+)/(left only|right only)/([\d.]+)\.\.([\d.]+)$", b)
                ok = False
                if m and (m.group(1), m.group(2), m.group(3)) in want:
                    lo, hi = float(m.group(4)), float(m.group(5))
                    ok = any(a - 1e-3 <= lo and hi <= bb + 1e-3
                             for a, bb in per[m.group(1)])
                    seen.add((m.group(1), m.group(2), m.group(3)))
                print("    %s %s" % ("vdd band end:" if ok else "OURS:        ", b))
                if not ok:
                    rc = 1
            for w in sorted(want - seen):
                print("    OURS:         no vdd band end at %s" % (w,))
                rc = 1
            for b in gap:
                print("    OURS:         " + b)
                rc = 1
    with open(os.path.join(out, "rows.txt"), "w") as fh:
        fh.write("\n".join(rows) + "\n")
    print("cut_abut: %s" % ("FAIL, the cell breaks more than the vdd band" if rc
                            else "ok, only the vdd band ends, at the cell edges"))
    return rc


if __name__ == "__main__":
    try:
        r = main()
    except BaseException:
        import traceback
        traceback.print_exc()
        r = 1
    sys.exit(r)
