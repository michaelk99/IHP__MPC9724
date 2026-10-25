# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Extract the chip from its GDS for top_lvs.sh. LibreLane's own extraction reads the DEF with every cell as a LEF abstract, so it never sees the macro's or a standard cell's geometry.
# The LEFview loop below asks Magic to keep the IO cells, the bondpad and the logos abstract, which it does not do in GDS mode, so top_lvs.sh empties them before netgen.

drc off
crashbackups disable
locking disable

gds rescale false
gds readonly true
gds read $::env(LVS_GDS)

# the CDL's port order for every extracted standard cell
readspice $::env(EZ130_DIR)/cdl/ez130_8t.cdl
readspice $::env(DECAPHV_DIR)/cdl/ez130_8t_decap_hv.cdl

# the VDD cut cell and the dsm2 box are kept abstract by the same loop, so they are compared by their pins
foreach cell [cellname list allcells] {
    if {([regexp {^sg13cmos5l_(IOPad|Filler[0-9]|Corner|ip__)} $cell] || $cell eq "dsm2_core") && $cell ne "sg13cmos5l_ip__clamp_vddvss"} {
        load $cell
        property LEFview true
        puts "abstract: $cell"
    }
}

load $::env(LVS_CELL) -dereference
cd $::env(LVS_OUT)

extract do local
extract no capacitance
extract no coupling
extract no resistance
extract no adjust
extract unique notopports
extract

ext2spice lvs
ext2spice -o $::env(LVS_TOP).spice
quit -noprompt
