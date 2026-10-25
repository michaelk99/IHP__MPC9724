# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# netgen setup for top_lvs.tcl: the PDK's, plus one rule. The macro's GDS brings its own copy of
# every EZ130 cell, and the GDS merge renames the copy AND2X1$1, so each name$N equals name.
source $::env(PDK_ROOT)/$::env(PDK)/libs.tech/netgen/$::env(PDK)_setup.tcl
foreach cell [cells list -all -circuit1] {
    if {[regexp {^(.+)\$[0-9]+$} $cell -> base] && [lsearch [cells list -all -circuit2] $base] >= 0} {
        equate classes "-circuit1 $cell" "-circuit2 $base"
        puts "equate $cell with $base"
    }
}
# FILLER cells hold no device, so magic writes no instance of them, while the reference keeps each
# as a black box, the EZ130 CDL having no FILLER subcircuit
foreach circuit {1 2} {
    foreach cell [cells list -all -circuit$circuit] {
        # FILLER cells hold no device, nor does the metal and active fill of the delivery GDS
        if {[regexp {^FILLER[0-9]+(\$[0-9]+)?$|_FILL_CELL(\$[0-9]+)?$} $cell]} {
            ignore class "-circuit$circuit $cell"
        }
    }
}
# The CDL gives each antenna diode its area and perimeter, Magic its w and l, which carry the same.
foreach dev {dantenna dpantenna} {
    if {[lsearch [cells list -all -circuit2] $dev] >= 0} {
        property "-circuit2 $dev" delete a p
    }
}
# The bondpad and the logos hold no device. The bondpad's GDS carries no label, so Magic gives it no
# port and its overlap with the IO cell's pad joins nothing, while the reference connects its pad pin.
# The overlap is geometry, which DRC and the bond plan check. The ESD clamp cell holds devices and
# is compared, the VDD cut cell is compared by its pins.
foreach circuit {1 2} {
    foreach cell [cells list -all -circuit$circuit] {
        if {[regexp {^sg13cmos5l_ip__} $cell] && ![string match sg13cmos5l_ip__clamp_vddvss* $cell] && ![string match sg13cmos5l_ip__cut_vdd* $cell]} {
            ignore class "-circuit$circuit $cell"
        }
    }
}
