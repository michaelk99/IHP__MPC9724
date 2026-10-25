# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Per-layer metal density of a macro GDS, over the top cell bounding box.
#
# This is a proxy, not a rule. The rule that bites a hard macro is M<n>Fil.h,
# a minimum of 25 % metal plus filler over any 800 x 800 um window of the CHIP,
# and its companion M<n>Fil.k at 75 % maximum. A macro smaller than the window
# is only part of one, so the surrounding die carries some of it and a macro
# below 25 % on its own can still pass. What a macro cannot do is be so sparse
# that it drags a whole window under, which is what happened here at 5.4 %
# Metal4 before the fill. Use this to see how much a block is contributing;
# use the chip's density DRC log for the verdict.
#
# The chip-level rules on drawn metal only, which filler does not count towards,
# are M<n>.j and M<n>.k: 35 % to 60 % on Metal1 to Metal4, 25 % to 70 % on
# TopMetal1. They are reported in the density log as a global percentage.
#
# klayout -b -rd gds=<file> -r report_density.py

import pya

# Drawn metal plus the filler datatype the PDK filler writes (22). M*Fil.h and
# M*Fil.k count both, so a report on datatype 0 alone understates a filled macro.
LAYERS = [
    ("Metal1",     8),
    ("Metal2",    10),
    ("Metal3",    30),
    ("Metal4",    50),
    ("TopMetal1", 126),
]

WINDOW = 800.0   # um, the M*Fil.h / M*Fil.k window side
FIL_MIN = 25.0   # M*Fil.h
FIL_MAX = 75.0   # M*Fil.k

ly = pya.Layout()
ly.read(gds)
top = ly.top_cell()
bbox = top.dbbox()
area = bbox.width() * bbox.height()
share = min(1.0, area / (WINDOW * WINDOW))

print("cell   : %s" % top.name)
print("bbox   : %.2f x %.2f um, %.1f um2" % (bbox.width(), bbox.height(), area))
print("window : %.0f x %.0f um, this block is %.1f %% of one" % (WINDOW, WINDOW, 100.0 * share))
for name, num in LAYERS:
    r = pya.Region()
    for dt in (0, 22):
        r += pya.Region(top.begin_shapes_rec(ly.layer(num, dt)))
    r.merge()
    a = r.area() * (ly.dbu ** 2)
    pct = 100.0 * a / area
    # What the rest of a window would have to carry for that window to reach the
    # minimum, if this block sat entirely inside one.
    if share >= 1.0:
        note = "   <- below M*Fil.h on its own" if pct < FIL_MIN else ""
    else:
        need = (FIL_MIN - pct * share) / (1.0 - share)
        note = "   needs %.1f %% around it" % need if need > 0 else ""
    if pct > FIL_MAX:
        note = "   <- above the M*Fil.k maximum of %.0f %%" % FIL_MAX
    print("%-10s %12.1f um2   %6.2f %%%s" % (name, a, pct, note))

print("")
print("TopMetal1 is left unfilled in a macro on purpose, the chip runs its")
print("TopMetal1 power stripes across the block.")
