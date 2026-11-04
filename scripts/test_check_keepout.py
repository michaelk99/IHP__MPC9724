#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Tests of check_keepout on a toy layout."""

import importlib.util
import tempfile
from pathlib import Path

import klayout.db as db

_spec = importlib.util.spec_from_file_location("ck", Path(__file__).resolve().parent / "check_keepout.py")
ck = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ck)

BOX = [100.0, 100.0, 200.0, 200.0]


def make(path, extra=None):
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell("top")
    macro = ly.create_cell("dsm2_core")
    um = 1000
    # the macro fills the box on Metal1 to Metal4
    for num in (8, 10, 30, 50):
        macro.shapes(ly.layer(num, 0)).insert(db.Box(0, 0, 100 * um, 100 * um))
    top.insert(db.CellInstArray(macro.cell_index(), db.Trans(100 * um, 100 * um)))
    # a wire that runs 50 um into the box and metal outside it
    top.shapes(ly.layer(30, 0)).insert(db.Box(150 * um, 149 * um, 201 * um, 151 * um))
    top.shapes(ly.layer(10, 0)).insert(db.Box(300 * um, 300 * um, 310 * um, 310 * um))
    if extra:
        num, dt, box = extra
        top.shapes(ly.layer(num, dt)).insert(db.Box(*[int(v * um) for v in box]))
    ly.write(str(path))


def main():
    with tempfile.TemporaryDirectory() as d:
        gds = Path(d) / "t.gds"
        make(gds)
        # the wire reaches deep into the box
        f = ck.check(str(gds), BOX)
        assert len(f) == 1 and f[0].startswith("Metal3 30/0"), f
        # a wire that stays in the edge band passes
        ly = db.Layout()
        ly.read(str(gds))
        top = ly.top_cell()
        top.shapes(ly.layer(30, 0)).clear()
        top.shapes(ly.layer(30, 0)).insert(db.Box(199 * 1000, 149 * 1000, 215 * 1000, 151 * 1000))
        ly.write(str(gds))
        assert ck.check(str(gds), BOX) == []
        # a Metal2 rectangle inside the box fails
        make(gds, (10, 0, [140, 140, 150, 150]))
        ly = db.Layout()
        ly.read(str(gds))
        top = ly.top_cell()
        top.shapes(ly.layer(30, 0)).clear()
        ly.write(str(gds))
        f = ck.check(str(gds), BOX)
        assert len(f) == 1 and f[0].startswith("Metal2 10/0"), f
        # so does a filler shape
        make(gds, (50, 22, [120, 120, 125, 125]))
        ly = db.Layout()
        ly.read(str(gds))
        top = ly.top_cell()
        top.shapes(ly.layer(30, 0)).clear()
        ly.write(str(gds))
        f = ck.check(str(gds), BOX)
        assert len(f) == 1 and f[0].startswith("Metal4 50/22"), f
        # the nofill marker over the whole box is not a shape of the circuit
        make(gds, (50, 23, [100, 100, 200, 200]))
        ly = db.Layout()
        ly.read(str(gds))
        ly.top_cell().shapes(ly.layer(30, 0)).clear()
        ly.write(str(gds))
        assert ck.check(str(gds), BOX) == []
        # Activ filler inside the box fails the feol check, the macro's own Activ does not
        make(gds, (1, 22, [150, 150, 152, 152]))
        ly = db.Layout()
        ly.read(str(gds))
        top = ly.top_cell()
        top.shapes(ly.layer(30, 0)).clear()
        macro = ly.cell("dsm2_core")
        macro.shapes(ly.layer(1, 0)).insert(db.Box(0, 0, 100 * 1000, 100 * 1000))
        top.shapes(ly.layer(1, 23)).insert(db.Box(100 * 1000, 100 * 1000, 200 * 1000, 200 * 1000))
        ly.write(str(gds))
        assert ck.check(str(gds), BOX) == []
        f = ck.check(str(gds), BOX, edge=0, datatypes=(22,), layers=ck.FEOL)
        assert len(f) == 1 and f[0].startswith("Activ 1/22"), f
        # GatPoly filler too, and filler that only abuts the box passes
        make(gds, (5, 22, [190, 110, 200, 112]))
        ly = db.Layout()
        ly.read(str(gds))
        ly.top_cell().shapes(ly.layer(1, 22)).insert(db.Box(200 * 1000, 100 * 1000, 202 * 1000, 102 * 1000))
        ly.write(str(gds))
        f = ck.check(str(gds), BOX, edge=0, datatypes=(22,), layers=ck.FEOL)
        assert len(f) == 1 and f[0].startswith("GatPoly 5/22"), f
        # the named boxes come from the fill script
        script = Path(d) / "fill.sh"
        script.write_text('DSM2_KEEPOUT="1,2,3,4"\n# DSM2_OUTLINE="9,9,9,9"\nDSM2_OUTLINE="5,6,7.5,8"\n')
        assert ck.named_box("halo", script) == [1, 2, 3, 4]
        assert ck.named_box("outline", script) == [5, 6, 7.5, 8]
        o, h = ck.named_box("outline"), ck.named_box("halo")
        assert h[0] < o[0] and h[1] < o[1] and o[2] < h[2] and o[3] < h[3], (o, h)
        # a missing macro cell is an error, not a pass
        assert ck.check(str(gds), BOX, cell="nope") == ["no cell nope in %s" % gds]
    print("test_check_keepout: OK")


if __name__ == "__main__":
    main()
