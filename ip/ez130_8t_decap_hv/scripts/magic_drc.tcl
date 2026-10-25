# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: Magic DRC on every cell of the library GDS, one MAGIC line each
#
# magic -dnull -noconsole -rcfile $PDK_ROOT/$PDK/libs.tech/magic/<pdk>.magicrc magic_drc.tcl
# Run from scripts/. The Makefile requires one MAGIC line per cell and a total
# of 0; Magic itself exits 0 whatever it finds.

gds read ../gds/ez130_8t_decap_hv.gds
foreach c {DECAPHV8 DECAPHV16 DECAPHV32} {
    load $c
    select top cell
    drc check
    drc catchup
    puts "MAGIC $c [drc list count total]"
    foreach {why boxes} [drc listall why] { puts "  $why" }
}
quit -noprompt
