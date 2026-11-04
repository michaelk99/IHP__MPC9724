# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Write a GDS copy for IHP's Open-Silicon-MPW: top cell renamed, saved with IHP's KLayout options.
# The internal flow keeps its cell name, only the copy is renamed.
#
# klayout -b -r ihp_gds.py -rd gds_in=<file> -rd gds_out=<file> -rd new=<cellname>
# KLayout keeps a zero-area polygon on read and write, so scan_gds.py checks the written file (release_ihp.sh).

import pya


def write_ihp(ly, path):
    # IHP's save dialog: GDS2, dbu 0.001, no PCell and library context, zero-length paths turned into boundaries
    o = pya.SaveLayoutOptions()
    o.format = "GDS2"
    o.dbu = 0.001
    o.write_context_info = False
    o.gds2_no_zero_length_paths = True
    o.gds2_libname = "LIB"
    o.gds2_max_cellname_length = 32000
    o.gds2_max_vertex_count = 8000
    ly.write(path, o)


ly = pya.Layout()
ly.read(gds_in)
tops = ly.top_cells()
if len(tops) != 1:
    raise RuntimeError("expected one top cell in %s, found %d" % (gds_in, len(tops)))
tops[0].name = new
write_ihp(ly, gds_out)
back = pya.Layout()
back.read(gds_out)
names = [c.name for c in back.top_cells()]
print("[INFO] %s: top cells %s, dbu %g" % (gds_out, names, back.dbu))
if names != [new]:
    raise RuntimeError("top cells %s, want only %s" % (names, new))
