# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# netgen side of top_lvs.sh. The reference is the chip's and the macro's powered netlists, every cell's
# wells connected (verilog_tie_wells.py), over the EZ130 CDL with its transistors as Magic writes
# them (top_lvs.sh), with the IO cells from the PDK. -blackbox keeps only cells empty in the layout, the
# abstract IO cells, bondpad and logos, as black boxes. The macro and every standard cell compare
# device by device.

set top $::env(LVS_TOP)
set cell $::env(LVS_CELL)
set circuit1 [readnet spice $::env(LVS_OUT)/$top.boxed.spice]
set circuit2 [readnet verilog /dev/null]
readnet spice $::env(LVS_OUT)/ez130_8t.cdl $circuit2
readnet spice $::env(LVS_OUT)/ez130_8t_decap_hv.cdl $circuit2
readnet spice $::env(LVS_OUT)/sg13cmos5l_io.spi $circuit2
readnet spice $::env(LVS_OUT)/sg13cmos5l_ip__clamp_vddvss.cdl $circuit2
readnet spice $::env(LVS_OUT)/sg13cmos5l_ip__cut_vdd.cdl $circuit2
# dsm2 is an abstract box until its layout arrives, compared by its pins
readnet verilog ip/dsm2_core/verilog/dsm2_core.v $circuit2
readnet verilog $::env(LVS_OUT)/dsa1_dig_top.pnl.v $circuit2
readnet verilog $::env(LVS_OUT)/$top.pnl.v $circuit2
lvs "$circuit1 $cell" "$circuit2 $top" verification/lvs/top_lvs_setup.tcl \
    $::env(LVS_OUT)/lvs.rpt -blackbox -json
