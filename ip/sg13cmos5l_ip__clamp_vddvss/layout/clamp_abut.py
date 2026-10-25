# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# From OpenBLAU 8f25e634, ip/sg13cmos5l_ip__rfpad_70x70
# Description: abutment test, the clamp cell between the chip's VSS and VDD pads
#
#   klayout -b -r clamp_abut.py -rd out=<dir> [-rd gds=<clamp gds>]
#
# Writes six rows into <dir>: IOPadVss, the clamp, IOPadVdd, abutted, with a
# Filler2000 and with a Filler4000 on each side (the chip's 20 um gaps on the
# west side), each with the two IO pads' bondpads at LibreLane's offset
# (5, -70). Each row comes with a reference row that has 120 um of IO fillers
# in the slot instead, which is what the ring has without the cell. The DRC of
# both rows is compared by drc_report.py.
#
# Here: a conductor that reaches a seam must continue across it with the same
# y profile, and the cell may break nothing the reference row does not.

import os
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))
from gdswrite import write_gds     # noqa: E402

CELL = "sg13cmos5l_ip__clamp_vddvss"
REPO = os.path.join(HERE, "..", "..", "..")
IO_GDS = os.path.join(os.environ["PDK_ROOT"], os.environ["PDK"],
                      "libs.ref", "sg13cmos5l_io", "gds", "sg13cmos5l_io.gds")
BOND_GDS = os.path.join(REPO, "ip", "sg13cmos5l_ip__bondpad_70x70", "final", "gds",
                        "sg13cmos5l_ip__bondpad_70x70.gds")
BOND = "sg13cmos5l_ip__bondpad_70x70"
BOND_OFFSET = (5.0, -70.0)   # PAD_BONDPAD_OFFSETS of the PDK's LibreLane config
W = 120.0
SLOT_FILL = ("sg13cmos5l_Filler10000", "sg13cmos5l_Filler10000", "sg13cmos5l_Filler4000")
SIDES = {"abut": None, "f2000": "sg13cmos5l_Filler2000", "f4000": "sg13cmos5l_Filler4000"}
# the ring bands must carry across. Metal1 and Metal2 are reported only: the
# IO cells run Metal1 tap strips to their edges, the clamp keeps 1 um inside.
LAY = {"Metal3": (30, 0), "Metal4": (50, 0), "TopMetal1": (126, 0)}
INFO = {"Metal1": (8, 0), "Metal2": (10, 0)}


def build(ly, name, side, ours):
    """One row, left to right. Returns the top cell and its seams."""
    top = ly.create_cell(name)
    width = {c.name: c.bbox_per_layer(ly.layer(189, 4)).width() * ly.dbu
             for c in ly.each_cell() if c.name.startswith("sg13cmos5l_")}
    width[CELL] = W
    row = ["sg13cmos5l_IOPadVss"]
    row += [side] if side else []
    row += [CELL] if ours else list(SLOT_FILL)
    row += [side] if side else []
    row += ["sg13cmos5l_IOPadVdd"]
    x, seams = 0.0, []
    for cell in row:
        top.insert(pya.DCellInstArray(ly.cell(cell).cell_index(), pya.DTrans(x, 0.0)))
        if cell.startswith("sg13cmos5l_IOPad"):
            top.insert(pya.DCellInstArray(ly.cell(BOND).cell_index(),
                                          pya.DTrans(x + BOND_OFFSET[0], BOND_OFFSET[1])))
        x += width[cell]
        seams.append(x)
    return top, seams[:-1]


def width_of(ly, name):
    return ly.cell(name).bbox_per_layer(ly.layer(189, 4)).width() * ly.dbu


def profile(merged, x0, x1, dbu):
    col = (merged & pya.Region(pya.DBox(x0, 0, x1, 180).to_itype(dbu))).merged()
    return sorted((round(p.bbox().bottom * dbu, 3), round(p.bbox().top * dbu, 3))
                  for p in col.each())


def seams_check(ly, top, seams, layers=LAY):
    """Conductors that stop at a seam or change their y profile across it."""
    bad = set()
    for layer, (l, d) in layers.items():
        merged = pya.Region(top.begin_shapes_rec(ly.layer(l, d))).merged()
        for x in seams:
            if profile(merged, x - 0.5, x, ly.dbu) != profile(merged, x, x + 0.5, ly.dbu):
                left = set(profile(merged, x - 0.5, x, ly.dbu))
                right = set(profile(merged, x, x + 0.5, ly.dbu))
                for iv in sorted(left ^ right):
                    bad.add("%s/seam x %g/%s/%.3f..%.3f" % (
                        layer, x, "left only" if iv in left else "right only", iv[0], iv[1]))
    return bad


def main():
    out = globals().get("out")
    gds = globals().get("gds") or os.path.join(HERE, "..", "gds", CELL + ".gds")
    os.makedirs(out, exist_ok=True)
    rc = 0
    rows = []
    for name, side in SIDES.items():
        res = {}
        for ours in (True, False):
            ly = pya.Layout()
            ly.read(IO_GDS)
            ly.read(BOND_GDS)
            ly.read(gds)
            tag = "clamp_row_%s%s" % (name, "" if ours else "_ref")
            top, seams = build(ly, tag, side, ours)
            for ci in [c.cell_index() for c in ly.top_cells()]:
                if ci != top.cell_index():
                    ly.prune_cell(ci, -1)
            path = os.path.join(out, tag + ".gds")
            write_gds(ly, path)
            res[ours] = seams_check(ly, top, seams)
            if ours:
                x0 = 80.0 + (width_of(ly, side) if side else 0.0)
                rows.append("%s %g %g" % (tag, x0, x0 + W))
            res[(ours, "info")] = seams_check(ly, top, seams, INFO)
            # the seams of the two rows sit at the same x, so the sets compare
            print("%s: %d seams at %s, %d breaks" % (tag, len(seams),
                  ", ".join("%g" % s for s in seams), len(res[ours])))
        extra = res[True] - res[False]
        for b in sorted(res[False]):
            print("    library: " + b)
        for b in sorted(extra):
            print("    OURS:    " + b)
        info = res[(True, "info")] - res[(False, "info")]
        print("    Metal1/Metal2 conductors that end at a seam of the clamp row only: %d"
              % len(info))
        if extra:
            rc = 1
    with open(os.path.join(out, "rows.txt"), "w") as fh:
        fh.write("\n".join(rows) + "\n")
    print("clamp_abut: %s" % ("FAIL, the cell breaks a conductor the fillers carry" if rc
                              else "ok, no seam break the filler row does not have"))
    return rc


if __name__ == "__main__":
    try:
        r = main()
    except BaseException:
        import traceback
        traceback.print_exc()
        r = 1
    sys.exit(r)
