# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Rename the top cell of a GDS and write it out again.
#
# add_logo_fill.sh normally gets the renamed cell for free, as a side effect of
# meerkat merging the logo in. With the logo switched off there is nothing to
# merge, but the fill step and every downstream DRC target still expect the
# top cell to be <design>_logo_fill, so do just the rename.
#
# klayout -b -r rename_top_cell.py -rd gds_in=<file> -rd gds_out=<file> -rd new=<cellname>

import pya

ly = pya.Layout()
ly.read(gds_in)

tops = ly.top_cells()
if len(tops) != 1:
    raise RuntimeError("expected one top cell in %s, found %d" % (gds_in, len(tops)))

tops[0].name = new
ly.write(gds_out)
print("[INFO] %s: top cell renamed to %s" % (gds_out, new))
