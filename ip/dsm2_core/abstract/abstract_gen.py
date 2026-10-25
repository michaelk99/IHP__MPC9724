# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Placeholder abstract of dsm2_core: outline, Metal3 pins and OBS only.
#
#   klayout -n sg13cmos5l -zz -r abstract_gen.py
#
# The real GDS and LEF from the dsm2 design replace both outputs.

import os
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))
from gdswrite import write_gds       # noqa: E402

CELL = "dsm2_core"
W, H = 155.0, 185.0
GDS = os.path.join(HERE, "..", "gds", CELL + ".gds")
LEF = os.path.join(HERE, "..", "lef", CELL + ".lef")
PIN_LEN, PIN_DEPTH = 2.0, 1.0     # along and across the edge
SUPPLY_DEPTH = 2.0                # supply stubs, 10 um tall, for the chip top's straps

EAST = ["vi", "vcm", "ibias_test"]
SOUTH = ["do_q_b", "do_q", "di_clk"]
WEST = ["do_q_dec", "di_qout_en", "di_btest_en", "di_vcm_ext", "di_dith_amp[1]", "di_dith_amp[0]",
        "di_dith_en", "di_trim[3]", "di_trim[2]", "di_trim[1]", "di_trim[0]", "di_rst_b", "di_ena"]
SOUTH_X = {"do_q_b": 110.0, "do_q": 105.0, "di_clk": 100.0}   # 45, 50, 55 um from the east edge
USE = {"vdd": "POWER", "vss": "GROUND"}
OBS_LAYERS = ["Metal1", "Metal2", "Metal3", "Metal4"]
LAYERS = {"Metal1": (8, 0), "Metal2": (10, 0), "Metal3": (30, 0), "Metal4": (50, 0),
          "prBoundary": (189, 4), "Metal3.pin": (30, 2), "Metal3.text": (30, 25)}


def pins():
    """name -> list of (x0, y0, x1, y1) on Metal3."""
    p = {}
    for i, n in enumerate(EAST):
        c = 10.0 * (i + 1)
        p[n] = [(W - PIN_DEPTH, c - PIN_LEN / 2, W, c + PIN_LEN / 2)]
    for n in SOUTH:
        c = SOUTH_X[n]
        p[n] = [(c - PIN_LEN / 2, 0.0, c + PIN_LEN / 2, PIN_DEPTH)]
    for i, n in enumerate(WEST):
        c = 10.0 * (i + 1)
        p[n] = [(0.0, c - PIN_LEN / 2, PIN_DEPTH, c + PIN_LEN / 2)]
    p["vdd"] = [(W - SUPPLY_DEPTH, 36.0, W, 46.0)]
    p["vss"] = [(W - SUPPLY_DEPTH, 50.0, W, 60.0)]
    return p


def build():
    ly = pya.Layout(True)
    ly.dbu = 0.001
    top = ly.cell(ly.add_cell(CELL))
    lay = lambda n: ly.layer(*LAYERS[n])   # noqa: E731
    top.shapes(lay("prBoundary")).insert(pya.DBox(0, 0, W, H))
    allp = pins()
    for n, rects in allp.items():
        for r in rects:
            top.shapes(lay("Metal3")).insert(pya.DBox(*r))
            top.shapes(lay("Metal3.pin")).insert(pya.DBox(*r))
        x0, y0, x1, y1 = rects[0]
        top.shapes(lay("Metal3.text")).insert(
            pya.DText(n, pya.DTrans(pya.DVector((x0 + x1) / 2, (y0 + y1) / 2))))
    return ly, allp


def write_lef(path, allp):
    # REUSE-IgnoreStart
    out = ["# SPDX-FileCopyrightText: 2026 Michael Koefinger",
           "# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1",
    # REUSE-IgnoreEnd
           "# Placeholder, written by abstract/abstract_gen.py, do not edit.",
           "", "VERSION 5.7 ;", "BUSBITCHARS \"[]\" ;", "DIVIDERCHAR \"/\" ;", "",
           "MACRO %s" % CELL, "    CLASS BLOCK ;", "    ORIGIN 0.000 0.000 ;",
           "    FOREIGN %s 0.000 0.000 ;" % CELL, "    SIZE %.3f BY %.3f ;" % (W, H),
           "    SYMMETRY X Y R90 ;"]
    for n, rects in allp.items():
        d = "OUTPUT" if n.startswith("do_") else "INPUT" if n.startswith("di_") else "INOUT"
        out += ["  PIN %s" % n, "    DIRECTION %s ;" % d]
        out.append("    USE %s ;" % USE.get(n, "SIGNAL"))
        for r in rects:
            out += ["    PORT", "      LAYER Metal3 ;", "        RECT %.3f %.3f %.3f %.3f ;" % r, "    END"]
        out.append("  END %s" % n)
    # OBS: everything but the pin shapes on Metal3, the whole outline on the other layers
    reg = pya.Region(pya.DBox(0, 0, W, H).to_itype(0.001))
    pin_reg = pya.Region()
    for rects in allp.values():
        for r in rects:
            pin_reg.insert(pya.DBox(*r).to_itype(0.001))
    out.append("  OBS")
    for layer in OBS_LAYERS:
        out.append("    LAYER %s ;" % layer)
        body = (reg - pin_reg) if layer == "Metal3" else reg
        for t in sorted((t.bbox() for t in body.decompose_trapezoids_to_region().each()),
                        key=lambda b: (b.bottom, b.left)):
            out.append("      RECT %.3f %.3f %.3f %.3f ;" % (t.left * 0.001, t.bottom * 0.001,
                                                         t.right * 0.001, t.top * 0.001))
    out += ["  END", "END %s" % CELL, "", "END LIBRARY", ""]
    with open(path, "w") as fh:
        fh.write("\n".join(out))


def check(allp):
    """Pins inside the outline and clear of corners, every pin touching the outline, spacing between nets."""
    items = [(n, r) for n, rs in allp.items() for r in rs]
    for n, (x0, y0, x1, y1) in items:
        if min(x0, W - x1) < 0 or min(y0, H - y1) < 0:
            raise AssertionError("%s outside the outline" % n)
        if (min(x0, W - x1) < 1.0 and min(y0, H - y1) < 1.0):
            raise AssertionError("%s within 1 um of a corner" % n)
    for n, rs in allp.items():
        if not any(min(x0, W - x1, y0, H - y1) == 0 for x0, y0, x1, y1 in rs):
            raise AssertionError("%s has no Metal3 shape touching the outline" % n)
    sp = 0.3
    for i, (na, a) in enumerate(items):
        for nb, b in items[i + 1:]:
            if na == nb:
                continue
            dx = max(a[0] - b[2], b[0] - a[2], 0)
            dy = max(a[1] - b[3], b[1] - a[3], 0)
            if (dx * dx + dy * dy) ** 0.5 < sp:
                raise AssertionError("%s and %s closer than %g um" % (na, nb, sp))


def main():
    ly, allp = build()
    check(allp)
    write_gds(ly, GDS)
    write_lef(LEF, allp)
    print("wrote %s and %s, %d pins" % (GDS, LEF, len(allp)))


if __name__ == "__main__":
    try:
        main()
    except BaseException as e:      # klayout -r exits 0 on a raised string
        if isinstance(e, SystemExit) and not e.code:
            raise
        import traceback
        traceback.print_exc()
        sys.exit(1)
