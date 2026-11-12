# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Metal1 around the two Magic M1.e markers in dsm2's OTA: merged shapes, owning cells, gaps under 0.22 um.
# Usage: python3 probe.py release/v.1.2.1/gds/MPC9724.gds.gz
import sys
import klayout.db as db

ly = db.Layout()
ly.read(sys.argv[1])
top = ly.top_cell()
um = lambda v: int(round(v / ly.dbu))
m1 = ly.layer(8, 0)
box = db.Box(um(805), um(525), um(875), um(535))
print("top", top.name)
r = db.Region(top.begin_shapes_rec_touching(m1, box)).merged() & db.Region(box)
for p in r.each():
    b = p.bbox()
    print("M1 %.3f %.3f %.3f %.3f" % (b.left * ly.dbu, b.bottom * ly.dbu, b.right * ly.dbu, b.top * ly.dbu))
it = top.begin_shapes_rec_touching(m1, db.Box(um(840), um(528.7), um(841), um(530.6)))
seen = set()
while not it.at_end():
    path = "/".join(ly.cell(e.inst().cell_index).name for e in it.path())
    b = it.shape().bbox().transformed(it.trans())
    k = (path, b.bottom)
    if k not in seen:
        seen.add(k)
        print("shape in %s: %.3f %.3f %.3f %.3f" % (path, b.left * ly.dbu, b.bottom * ly.dbu, b.right * ly.dbu, b.top * ly.dbu))
    it.next()
for e in r.space_check(um(0.22)).each():
    print("gap < 0.22:", e)
