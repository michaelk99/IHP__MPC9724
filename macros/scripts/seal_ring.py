# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Add or strip a temporary EdgeSeal ring (39/0) around a macro's top cell.
#
# The PDK metal filler fills EdgeSeal.holes, that is, the area enclosed by the
# seal ring. A hardened macro has no seal ring, so the region is empty and the
# filler silently places nothing. Wrapping the macro in a ring whose hole is
# its own bounding box makes the filler treat the macro interior as fillable.
# The ring is removed again afterwards: it is scaffolding, not layout.
#
# klayout -b -rd gds=<in> -rd out=<out> -rd mode=<add|strip> -r seal_ring.py

import pya

SEAL = (39, 0)
MARGIN = 2.0          # ring thickness, um
# Fill is kept this far inside the macro edge. The macro-level filler knows
# nothing about the chip routing that will run alongside the block, and fill
# placed flush with the boundary lands within the filler-to-metal spacing of
# it: measured as 104 M3Fil.c and 13 M2Fil.c edge pairs at the macro edge,
# gaps of 0.28 um. Costs about 1.6 % of the fillable area.
KEEPOUT = 2.0         # um

ly = pya.Layout()
ly.read(gds)
top = ly.top_cell()
li = ly.layer(SEAL[0], SEAL[1])

if mode == "add":
    b = top.dbbox()
    outer = pya.DBox(b.left - MARGIN, b.bottom - MARGIN,
                     b.right + MARGIN, b.top + MARGIN)
    inner = pya.DBox(b.left + KEEPOUT, b.bottom + KEEPOUT,
                     b.right - KEEPOUT, b.top - KEEPOUT)
    ring = pya.Region(pya.Box.from_dbox(outer * (1.0 / ly.dbu))) - \
           pya.Region(pya.Box.from_dbox(inner * (1.0 / ly.dbu)))
    top.shapes(li).insert(ring)
    print("[INFO] seal ring added, fill region %.2f x %.2f um (%.1f um keep-out at the edge)"
          % (inner.width(), inner.height(), KEEPOUT))
elif mode == "strip":
    n = top.shapes(li).size()
    top.shapes(li).clear()
    # The filler may have copied it into subcells; clear everywhere.
    for c in ly.each_cell():
        c.shapes(li).clear()
    print("[INFO] seal ring removed (%d shapes in the top cell)" % n)
else:
    raise RuntimeError("mode must be add or strip")

ly.write(out)
