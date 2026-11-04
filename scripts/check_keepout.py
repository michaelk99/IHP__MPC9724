#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Fail if anything but the macro itself has metal, or Activ or GatPoly, inside a keep-out box.

    check_keepout.py <gds> <box> [--cell dsm2_core] [--edge 2.0] [--datatypes 0,22] [--layers metal|feol]

All instances of the macro cell are dropped, then every shape of the chosen datatypes on the chosen layers inside the box fails. The nofill markers (datatype 23) are not shapes of the circuit.
The wires that end on a macro pin may reach --edge um into the box, so the part of the box within --edge of its boundary is not checked.
The box is llx,lly,urx,ury in um, or `outline` or `halo` for DSM2_OUTLINE or DSM2_KEEPOUT in add_logo_fill.sh.
"""

import argparse
import re
import sys
from pathlib import Path

import klayout.db as db

# GDS layer numbers, and the datatypes of drawn shapes and of filler. Datatype 23 is the nofill marker that keeps the filler out.
METALS = {"Metal1": 8, "Metal2": 10, "Metal3": 30, "Metal4": 50, "TopMetal1": 126}
FEOL = {"Activ": 1, "GatPoly": 5}
LAYERS = {"metal": METALS, "feol": FEOL}
DATATYPES = (0, 22)
FILL_SCRIPT = Path(__file__).resolve().parent / "add_logo_fill.sh"
BOX_NAMES = {"outline": "DSM2_OUTLINE", "halo": "DSM2_KEEPOUT"}


def named_box(name, script=FILL_SCRIPT):
    """The box the fill script keeps free, so the check and the fill share one copy."""
    var = BOX_NAMES[name]
    m = re.search(r'^%s="([^"]+)"' % var, Path(script).read_text(), re.M)
    if not m:
        raise SystemExit("no %s in %s" % (var, script))
    return [float(v) for v in m.group(1).split(",")]


def check(gds, box, cell="dsm2_core", edge=2.0, datatypes=DATATYPES, layers=METALS):
    """Return a list of failure messages, empty on PASS."""
    layout = db.Layout()
    layout.read(gds)
    top = layout.top_cell()
    dbu = layout.dbu
    llx, lly, urx, ury = box
    inner = db.Box(round((llx + edge) / dbu), round((lly + edge) / dbu), round((urx - edge) / dbu), round((ury - edge) / dbu))
    if inner.empty():
        return ["the box is smaller than twice the edge band"]
    victims = [c.cell_index() for c in layout.each_cell() if c.name == cell]
    if not victims:
        return ["no cell %s in %s" % (cell, gds)]
    for c in layout.each_cell():
        for inst in list(c.each_inst()):
            if inst.cell_index in victims:
                inst.delete()
    fails = []
    for name, num in layers.items():
        for dt in datatypes:
            idx = layout.find_layer(num, dt)
            if idx is None:
                continue
            region = db.Region(top.begin_shapes_rec(idx)) & db.Region(inner)
            for poly in region.each():
                b = poly.bbox()
                fails.append("%s %d/%d shape inside the box: %.3f,%.3f,%.3f,%.3f" % (name, num, dt, b.left * dbu, b.bottom * dbu, b.right * dbu, b.top * dbu))
    return fails


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("gds")
    ap.add_argument("box", help="llx,lly,urx,ury in um, or outline or halo")
    ap.add_argument("--cell", default="dsm2_core")
    ap.add_argument("--edge", type=float, default=2.0)
    ap.add_argument("--datatypes", default="0,22", help="GDS datatypes to check, 0 drawn and 22 filler")
    ap.add_argument("--layers", choices=sorted(LAYERS), default="metal", help="metal: Metal1 to TopMetal1, feol: Activ and GatPoly")
    args = ap.parse_args()
    box = named_box(args.box) if args.box in BOX_NAMES else [float(v) for v in args.box.split(",")]
    fails = check(args.gds, box, args.cell, args.edge, tuple(int(v) for v in args.datatypes.split(",")), LAYERS[args.layers])
    for f in fails[:50]:
        print("FAIL: " + f)
    if len(fails) > 50:
        print("FAIL: ... and %d more" % (len(fails) - 50))
    print("check_keepout: " + ("FAIL" if fails else "PASS"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
