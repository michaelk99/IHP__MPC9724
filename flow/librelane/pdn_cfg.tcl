# SPDX-FileCopyrightText: 2020-2022 Efabless Corporation, 2025 LibreLane Contributors
# SPDX-License-Identifier: Apache-2.0
#
# Copyright 2025 LibreLane Contributors
#
# Adapted from OpenLane
#
# Copyright 2020-2022 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/set_global_connections.tcl
set_global_connections

set secondary []
foreach vdd $::env(VDD_NETS) gnd $::env(GND_NETS) {
    if { $vdd != $::env(VDD_NET)} {
        lappend secondary $vdd

        set db_net [[ord::get_db_block] findNet $vdd]
        if {$db_net == "NULL"} {
            set net [odb::dbNet_create [ord::get_db_block] $vdd]
            $net setSpecial
            $net setSigType "POWER"
        }
    }

    if { $gnd != $::env(GND_NET)} {
        lappend secondary $gnd

        set db_net [[ord::get_db_block] findNet $gnd]
        if {$db_net == "NULL"} {
            set net [odb::dbNet_create [ord::get_db_block] $gnd]
            $net setSpecial
            $net setSigType "GROUND"
        }
    }
}

set_voltage_domain -name CORE -power $::env(VDD_NET) -ground $::env(GND_NET) \
    -secondary_power $secondary



if { $::env(PDN_MULTILAYER) == 1 } {

    set arg_list [list]
    if { $::env(PDN_ENABLE_PINS) } {
        lappend arg_list -pins "$::env(PDN_VERTICAL_LAYER) $::env(PDN_HORIZONTAL_LAYER)"
    }

    define_pdn_grid \
        -name stdcell_grid \
        -starts_with POWER \
        -voltage_domain CORE \
        {*}$arg_list

    set arg_list [list]
    append_if_equals arg_list PDN_EXTEND_TO "core_ring" -extend_to_core_ring
    append_if_equals arg_list PDN_EXTEND_TO "boundary" -extend_to_boundary

    add_pdn_stripe \
        -grid stdcell_grid \
        -layer $::env(PDN_VERTICAL_LAYER) \
        -width $::env(PDN_VWIDTH) \
        -pitch $::env(PDN_VPITCH) \
        -offset $::env(PDN_VOFFSET) \
        -spacing $::env(PDN_VSPACING) \
        -starts_with POWER \
        {*}$arg_list

    add_pdn_stripe \
        -grid stdcell_grid \
        -layer $::env(PDN_HORIZONTAL_LAYER) \
        -width $::env(PDN_HWIDTH) \
        -pitch $::env(PDN_HPITCH) \
        -offset $::env(PDN_HOFFSET) \
        -spacing $::env(PDN_HSPACING) \
        -starts_with POWER \
        {*}$arg_list

    add_pdn_connect \
        -grid stdcell_grid \
        -layers "$::env(PDN_VERTICAL_LAYER) $::env(PDN_HORIZONTAL_LAYER)"
} else {

    set arg_list [list]
    if { $::env(PDN_ENABLE_PINS) } {
        lappend arg_list -pins "$::env(PDN_VERTICAL_LAYER)"
    }

    define_pdn_grid \
        -name stdcell_grid \
        -starts_with POWER \
        -voltage_domain CORE \
        {*}$arg_list

    set arg_list [list]
    append_if_equals arg_list PDN_EXTEND_TO "core_ring" -extend_to_core_ring
    append_if_equals arg_list PDN_EXTEND_TO "boundary" -extend_to_boundary

    add_pdn_stripe \
        -grid stdcell_grid \
        -layer $::env(PDN_VERTICAL_LAYER) \
        -width $::env(PDN_VWIDTH) \
        -pitch $::env(PDN_VPITCH) \
        -offset $::env(PDN_VOFFSET) \
        -spacing $::env(PDN_VSPACING) \
        -starts_with POWER \
        {*}$arg_list
}

# Adds the standard cell rails if enabled.
if { $::env(PDN_ENABLE_RAILS) == 1 } {
    add_pdn_stripe \
        -grid stdcell_grid \
        -layer $::env(PDN_RAIL_LAYER) \
        -width $::env(PDN_RAIL_WIDTH) \
        -followpins

    add_pdn_connect \
        -grid stdcell_grid \
        -layers "$::env(PDN_RAIL_LAYER) $::env(PDN_VERTICAL_LAYER)"
}


# Adds the core ring if enabled.
if { $::env(PDN_CORE_RING) == 1 } {
    if { $::env(PDN_MULTILAYER) == 1 } {
        set arg_list [list]
        append_if_flag arg_list PDN_CORE_RING_ALLOW_OUT_OF_DIE -allow_out_of_die
        append_if_flag arg_list PDN_CORE_RING_CONNECT_TO_PADS -connect_to_pads
        append_if_equals arg_list PDN_EXTEND_TO "boundary" -extend_to_boundary

        set pdn_core_vertical_layer $::env(PDN_VERTICAL_LAYER)
        set pdn_core_horizontal_layer $::env(PDN_HORIZONTAL_LAYER)

        if { [info exists ::env(PDN_CORE_VERTICAL_LAYER)] } {
            set pdn_core_vertical_layer $::env(PDN_CORE_VERTICAL_LAYER)
        }

        if { [info exists ::env(PDN_CORE_HORIZONTAL_LAYER)] } {
            set pdn_core_horizontal_layer $::env(PDN_CORE_HORIZONTAL_LAYER)
        }

        add_pdn_ring \
            -grid stdcell_grid \
            -layers "$pdn_core_vertical_layer $pdn_core_horizontal_layer" \
            -widths "$::env(PDN_CORE_RING_VWIDTH) $::env(PDN_CORE_RING_HWIDTH)" \
            -spacings "$::env(PDN_CORE_RING_VSPACING) $::env(PDN_CORE_RING_HSPACING)" \
            -core_offset "$::env(PDN_CORE_RING_VOFFSET) $::env(PDN_CORE_RING_HOFFSET)" \
            {*}$arg_list

        if { [info exists ::env(PDN_CORE_VERTICAL_LAYER)] } {
            add_pdn_connect \
                -grid stdcell_grid \
                -layers "$::env(PDN_CORE_VERTICAL_LAYER) $::env(PDN_HORIZONTAL_LAYER)"
        }

        if { [info exists ::env(PDN_CORE_HORIZONTAL_LAYER)] } {
            add_pdn_connect \
                -grid stdcell_grid \
                -layers "$::env(PDN_CORE_HORIZONTAL_LAYER) $::env(PDN_VERTICAL_LAYER)"
        }

        if { [info exists ::env(PDN_CORE_VERTICAL_LAYER)] && [info exists ::env(PDN_CORE_HORIZONTAL_LAYER)] } {
            add_pdn_connect \
                -grid stdcell_grid \
                -layers "$::env(PDN_CORE_VERTICAL_LAYER) $::env(PDN_CORE_HORIZONTAL_LAYER)"
        }

    } else {
        throw APPLICATION "PDN_CORE_RING cannot be used when PDN_MULTILAYER is set to false."
    }
}

# Only dsa1_dig gets a macro grid. dsm2 is fed by the straps below, and the default grid would try to reach its Metal3 pins through the abstract's full Metal4 obstruction (PDN-0006).
define_pdn_grid \
    -macro \
    -instances {i_sg13cmos5l_dsa1_dig_core.dsa1_dig} \
    -name macro \
    -starts_with POWER \
    -halo "$::env(PDN_HORIZONTAL_HALO) $::env(PDN_VERTICAL_HALO)"

add_pdn_connect \
    -grid macro \
    -layers "$::env(PDN_VERTICAL_LAYER) $::env(PDN_HORIZONTAL_LAYER)"

# VDDA: the pad ring's segment between the two cut_vdd cells, and dsm2's supply. Not VDD anywhere.
if {[[ord::get_db_block] findNet VDDA] == "NULL"} {
    set net [odb::dbNet_create [ord::get_db_block] VDDA]
    $net setSpecial
    $net setSigType "POWER"
}
add_global_connection -net VDDA -inst_pattern {^(dsm_clk_pad|do_q_pad|do_q_b_pad|vi_pad|vcm_pad|ib_pad|vdda_pad|clamp_vdda)$} -pin_pattern {^vdd$} -power
add_global_connection -net VDDA -inst_pattern {^dsm2$} -pin_pattern {^vdd$} -power
add_global_connection -net VSS  -inst_pattern {^dsm2$} -pin_pattern {^vss$} -ground
global_connect -verbose

# dsa1_dig's own ring sits on Metal2 and Metal3 and the top-level TopMetal1 stripes feed it through Metal4. A ring on both top-level layers would make pdngen cut every stripe at the macro and leave the ring unfed (PSM-0069 in the IR analysis).

# ---------------------------------------------------------------------------
# The analog wires of dsm2, drawn on Metal3 after pdngen and checked before the flow goes on.
# vi, vcm and ibias_test run from the pad's padres pin to the dsm2 pin, 2 um wide, vi with a VSS track on each side.
# The VDDA strap runs from the segment's vdd band of vdda_pad to dsm2's vdd stub, the VSS strap from dsm2's vss stub to the east VSS core ring.
# All of it is Metal3 below the Metal4 core ring, so the ring does not join the segment.
# Coordinates come from the placed pads, dsm2 and the core ring in the database. All lengths below are in um.
# ---------------------------------------------------------------------------

# Metal3 spacing table of the tech LEF (width, parallel run length), checked against the layer's own minimum.
proc m3_space {wa wb prl} {
    set w [expr {max($wa, $wb)}]
    if {$w >= 10.0} {
        if {$prl >= 10.0} { return 0.60 }
        if {$prl >= 1.0} { return 0.24 }
        return 0.21
    }
    if {$w >= 0.39 && $prl >= 1.0} { return 0.24 }
    return 0.21
}

proc rect_gap_prl {a b} {
    lassign $a ax1 ay1 ax2 ay2
    lassign $b bx1 by1 bx2 by2
    set dx [expr {max($bx1 - $ax2, $ax1 - $bx2, 0.0)}]
    set dy [expr {max($by1 - $ay2, $ay1 - $by2, 0.0)}]
    set px [expr {min($ax2, $bx2) - max($ax1, $bx1)}]
    set py [expr {min($ay2, $by2) - max($ay1, $by1)}]
    set prl 0.0
    if {$dx > 0 && $py > 0} { set prl $py }
    if {$dy > 0 && $px > 0} { set prl $px }
    return [list [expr {hypot($dx, $dy)}] $prl]
}

proc rect_width {r} {
    lassign $r x1 y1 x2 y2
    return [expr {min($x2 - $x1, $y2 - $y1)}]
}

proc fail_analog {msg} {
    puts stderr "\[ERROR\] analog wires: $msg"
    error "analog wires: $msg"
}

# The Metal3 geometry of an instance pin as {x1 y1 x2 y2} in um.
proc pin_rects {inst pin layer} {
    set block [ord::get_db_block]
    set dbu [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])}]
    set i [$block findInst $inst]
    if {$i == "NULL"} { fail_analog "no instance $inst" }
    set it [$i findITerm $pin]
    if {$it == "NULL"} { fail_analog "no pin $inst/$pin" }
    set out {}
    foreach g [$it getGeometries] {
        lassign $g l r
        if {[$l getName] eq $layer} {
            lappend out [list [expr {[$r xMin] / $dbu}] [expr {[$r yMin] / $dbu}] [expr {[$r xMax] / $dbu}] [expr {[$r yMax] / $dbu}]]
        }
    }
    if {[llength $out] == 0} { fail_analog "$inst/$pin has no $layer shape" }
    return $out
}

proc one_pin_rect {inst pin layer} {
    set r [pin_rects $inst $pin $layer]
    if {[llength $r] != 1} { fail_analog "$inst/$pin has [llength $r] $layer shapes, expected 1" }
    return [lindex $r 0]
}

# The wires of the net on a layer as {x1 y1 x2 y2} in um. A via counts on both of its layers.
proc net_shapes {net layer} {
    set dbu [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])}]
    set out {}
    foreach sw [$net getSWires] {
        foreach b [$sw getWires] {
            if {[$b isVia]} {
                set v [$b getTechVia]
                if {$v == "NULL"} { set v [$b getBlockVia] }
                if {[$v getBottomLayer] eq "NULL" || ([[$v getBottomLayer] getName] ne $layer && [[$v getTopLayer] getName] ne $layer)} continue
            } elseif {[[$b getTechLayer] getName] ne $layer} continue
            lappend out [list [expr {[$b xMin] / $dbu}] [expr {[$b yMin] / $dbu}] [expr {[$b xMax] / $dbu}] [expr {[$b yMax] / $dbu}]]
        }
    }
    return $out
}

proc add_box {swire layer r} {
    set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
    lassign $r x1 y1 x2 y2
    odb::dbSBox_create $swire $layer [expr {int(round($x1 * $dbu))}] [expr {int(round($y1 * $dbu))}] [expr {int(round($x2 * $dbu))}] [expr {int(round($y2 * $dbu))}] STRIPE
}

# A Via3 array between Metal3 and Metal4 over the overlap of a Metal3 rect and a Metal4 rect, both of the same net.
# The 2-cut via is the one pdngen uses, so the array passes the same electromigration rating as the rest of the grid.
proc via3_array {swire m3 m4} {
    set tech [ord::get_db_tech]
    set dbu [$tech getDbUnitsPerMicron]
    set via [$tech findVia Via3_DV2E_so]
    # The via's metal pads, relative to its centre.
    set ex1 1e9; set ey1 1e9; set ex2 -1e9; set ey2 -1e9
    foreach b [$via getBoxes] {
        if {[[$b getTechLayer] getName] ni {Metal3 Metal4}} continue
        set ex1 [expr {min($ex1, [$b xMin] / double($dbu))}]; set ey1 [expr {min($ey1, [$b yMin] / double($dbu))}]
        set ex2 [expr {max($ex2, [$b xMax] / double($dbu))}]; set ey2 [expr {max($ey2, [$b yMax] / double($dbu))}]
    }
    lassign $m3 ax1 ay1 ax2 ay2
    lassign $m4 bx1 by1 bx2 by2
    # Keep the pads 0.2 um inside the overlap, and 0.4 um between the pads of neighbours.
    set x1 [expr {max($ax1, $bx1) + 0.2 - $ex1}]
    set x2 [expr {min($ax2, $bx2) - 0.2 - $ex2}]
    set y1 [expr {max($ay1, $by1) + 0.2 - $ey1}]
    set y2 [expr {min($ay2, $by2) - 0.2 - $ey2}]
    if {$x2 < $x1 || $y2 < $y1} { fail_analog "no room for a Via3 array in $m3 over $m4" }
    set px [expr {$ex2 - $ex1 + 0.4}]
    set py [expr {$ey2 - $ey1 + 0.4}]
    set n 0
    for {set x $x1} {$x <= $x2 + 1e-6} {set x [expr {$x + $px}]} {
        for {set y $y1} {$y <= $y2 + 1e-6} {set y [expr {$y + $py}]} {
            odb::dbSBox_create $swire $via [expr {int(round($x * $dbu))}] [expr {int(round($y * $dbu))}] STRIPE
            incr n
        }
    }
    return $n
}

proc draw_analog {} {
    set block [ord::get_db_block]
    set tech [ord::get_db_tech]
    set m3 [$tech findLayer Metal3]
    if {abs([$m3 getSpacing] / 1000.0 - 0.21) > 1e-9} { fail_analog "Metal3 minimum spacing is not 0.21 um, m3_space is stale" }
    set dsm2 [$block findInst dsm2]
    if {$dsm2 == "NULL"} { fail_analog "no dsm2 instance" }

    # Widths: signals and the VSS tracks 2 um, the straps 10 um. d is the centre distance of a VSS track to vi.
    set w 2.0
    set g 2.0
    set smin 0.24
    set d [expr {$w / 2 + $smin + $g / 2}]
    set ws 10.0

    # The east VSS core ring on Metal4: the tallest VSS Metal4 shape east of dsm2.
    set vss [$block findNet VSS]
    set vdd [$block findNet VDD]
    set vdda [$block findNet VDDA]
    set dsm2_xmax [expr {[[$dsm2 getBBox] xMax] / 1000.0}]
    set ring ""
    foreach r [net_shapes $vss Metal4] {
        lassign $r x1 y1 x2 y2
        if {$x1 > $dsm2_xmax && ($y2 - $y1) > 500.0 && ($ring eq "" || $x1 > [lindex $ring 0])} { set ring $r }
    }
    if {$ring eq ""} { fail_analog "no east VSS core ring on Metal4" }
    lassign $ring ring_x1 ring_y1 ring_x2 ring_y2

    # Pins: padres of the three analog pads, the dsm2 pins, the vdd band of vdda_pad.
    set sigs {}
    foreach {pad pin} {vi_pad vi vcm_pad vcm ib_pad ibias_test} {
        set pr [one_pin_rect $pad padres Metal3]
        set dr [one_pin_rect dsm2 $pin Metal3]
        set n1 [[[$block findInst $pad] findITerm padres] getNet]
        set n2 [[$dsm2 findITerm $pin] getNet]
        if {$n1 eq "NULL" || $n1 != $n2} { fail_analog "$pad/padres and dsm2/$pin are not on one net" }
        lappend sigs [list $n1 $pr $dr]
    }
    # vdda_pad has its vdd pin twice on Metal3, the band at the core edge and a stub at the bond pad side. Take the one nearest to the core.
    set band ""
    foreach r [pin_rects vdda_pad vdd Metal3] {
        if {$band eq "" || [lindex $r 0] < [lindex $band 0]} { set band $r }
    }
    set dvdd [one_pin_rect dsm2 vdd Metal3]
    set dvss [one_pin_rect dsm2 vss Metal3]
    # The pad cells' east pins sit at their core edge x. The wires end there.
    set pad_edge [lindex [lindex [lindex $sigs 0] 1] 0]

    # Columns from dsm2 eastwards, all under the Metal4 core ring: the VSS strap, the VDDA strap, ibias_test, vcm and the vi group.
    set gap_ws 1.0
    set gap_s 0.5
    set vss_c1 [expr {$dsm2_xmax + 1.0}]
    set vss_c2 [expr {$vss_c1 + $ws}]
    set vdda_c1 [expr {$vss_c2 + $gap_ws}]
    set vdda_c2 [expr {$vdda_c1 + $ws}]
    set ib_c1 [expr {$vdda_c2 + $gap_ws}]
    set vcm_c1 [expr {$ib_c1 + $w + $gap_s}]
    set vi_gw_c1 [expr {$vcm_c1 + $w + $gap_s}]
    set vi_c1 [expr {$vi_gw_c1 + $g + $smin}]
    set vi_ge_c2 [expr {$vi_c1 + $w + $smin + $g}]
    if {$vi_ge_c2 >= $pad_edge - 1.0} { fail_analog "the columns reach x $vi_ge_c2, the pads start at $pad_edge" }
    set cols [dict create ibias_test $ib_c1 vcm $vcm_c1 vi $vi_c1]

    set drawn {}
    set vi_guard_runs {}
    foreach s $sigs {
        lassign $s net pr dr
        set name [$net getName]
        set cxc [expr {[dict get $cols $name] + $w / 2}]
        set yp [expr {([lindex $pr 1] + [lindex $pr 3]) / 2}]
        set yd [expr {([lindex $dr 1] + [lindex $dr 3]) / 2}]
        set xp [lindex $pr 2]
        set xd [lindex $dr 0]
        set h [expr {$w / 2}]
        lappend drawn [list $net [list [expr {$cxc - $h}] [expr {$yd - $h}] [expr {$cxc + $h}] [expr {$yp + $h}]]]
        lappend drawn [list $net [list [expr {$cxc - $h}] [expr {$yp - $h}] $xp [expr {$yp + $h}]]]
        lappend drawn [list $net [list $xd [expr {$yd - $h}] [expr {$cxc + $h}] [expr {$yd + $h}]]]
        if {$name eq "vi"} {
            # The VSS tracks on both sides, the offset curves of the Z at distance d. Their lower runs cross the VSS ring, where the Via3 arrays go.
            set k [expr {$g / 2}]
            set xg_end [expr {$pad_edge - 1.0}]
            set xg_pin [expr {$dsm2_xmax + 1.0}]
            foreach sgn {1 -1} {
                set cxg [expr {$cxc - $sgn * $d}]
                set yu [expr {$yp + $sgn * $d}]
                set yl [expr {$yd + $sgn * $d}]
                lappend drawn [list $vss [list [expr {$cxg - $k}] [expr {min($yl, $yu) - $k}] [expr {$cxg + $k}] [expr {max($yl, $yu) + $k}]]]
                set run [list [expr {$cxg - $k}] [expr {$yu - $k}] $xg_end [expr {$yu + $k}]]
                lappend drawn [list $vss $run]
                set run [list $xg_pin [expr {$yl - $k}] [expr {$cxg + $k}] [expr {$yl + $k}]]
                lappend drawn [list $vss $run]
                lappend vi_guard_runs $run
            }
        }
    }

    # VDDA: pin stub of dsm2, up the column to the band, then east into the band.
    set yb [expr {[lindex $band 1] + 5.0}]
    set xb [expr {[lindex $band 0] + 8.0}]
    lappend drawn [list $vdda [list [lindex $dvdd 0] [lindex $dvdd 1] $vdda_c2 [lindex $dvdd 3]]]
    lappend drawn [list $vdda [list $vdda_c1 [lindex $dvdd 1] $vdda_c2 [expr {$yb + $ws}]]]
    lappend drawn [list $vdda [list $vdda_c1 $yb $xb [expr {$yb + $ws}]]]

    # VSS: pin stub of dsm2, up its column to above the VDDA strap, then east to the ring.
    # The VDDA column cuts the way east on Metal3, so the VSS strap goes round its north end.
    set yv [expr {$yb + $ws + 5.0}]
    set xv [expr {$ring_x2 + 0.5}]
    lappend drawn [list $vss [list [lindex $dvss 0] [lindex $dvss 1] $vss_c2 [lindex $dvss 3]]]
    lappend drawn [list $vss [list $vss_c1 [lindex $dvss 1] $vss_c2 [expr {$yv + $ws}]]]
    lappend drawn [list $vss [list $vss_c1 $yv $xv [expr {$yv + $ws}]]]
    set vss_run [list $vss_c1 $yv $xv [expr {$yv + $ws}]]

    # Shapes into the database, one new special wire per net and the vias where a track meets the VSS ring.
    set swires [dict create]
    foreach e $drawn {
        lassign $e net r
        set nm [$net getName]
        if {![dict exists $swires $nm]} {
            dict set swires $nm [odb::dbSWire_create $net ROUTED]
            $net setSpecial
        }
        add_box [dict get $swires $nm] $m3 $r
    }
    set nvia 0
    foreach run [concat $vi_guard_runs [list $vss_run]] {
        incr nvia [via3_array [dict get $swires VSS] $run $ring]
    }
    puts "\[INFO\] analog wires: [llength $drawn] Metal3 boxes and $nvia Via3 cuts drawn"

    check_analog $drawn $sigs $band $dvdd $dvss
}

proc check_analog {drawn sigs band dvdd dvss} {
    set block [ord::get_db_block]
    set dbu [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])}]
    set eps 1e-6

    # The window around everything drawn.
    set wx1 1e9; set wy1 1e9; set wx2 -1e9; set wy2 -1e9
    foreach e $drawn {
        lassign [lindex $e 1] x1 y1 x2 y2
        set wx1 [expr {min($wx1, $x1)}]; set wy1 [expr {min($wy1, $y1)}]
        set wx2 [expr {max($wx2, $x2)}]; set wy2 [expr {max($wy2, $y2)}]
    }
    set win [list [expr {$wx1 - 2}] [expr {$wy1 - 2}] [expr {$wx2 + 2}] [expr {$wy2 + 2}]]

    # Foreign shapes on Metal3: every special wire and every instance pin in the window, with the net name.
    set shapes {}
    foreach net [$block getNets] {
        foreach r [net_shapes $net Metal3] {
            lassign [rect_gap_prl $r $win] gap prl
            if {$gap <= $eps} { lappend shapes [list [$net getName] $r "wire of [$net getName]"] }
        }
    }
    set cells {}
    foreach inst [$block getInsts] {
        set bb [$inst getBBox]
        set ib [list [expr {[$bb xMin] / $dbu}] [expr {[$bb yMin] / $dbu}] [expr {[$bb xMax] / $dbu}] [expr {[$bb yMax] / $dbu}]]
        lassign [rect_gap_prl $ib $win] gap prl
        if {$gap > $eps} continue
        set iname [$inst getName]
        set pins {}
        foreach it [$inst getITerms] {
            set net [$it getNet]
            set nn [expr {$net eq "NULL" ? "" : [$net getName]}]
            foreach gm [$it getGeometries] {
                lassign $gm l r
                if {[$l getName] ne "Metal3"} continue
                set pr [list [expr {[$r xMin] / $dbu}] [expr {[$r yMin] / $dbu}] [expr {[$r xMax] / $dbu}] [expr {[$r yMax] / $dbu}]]
                lappend pins [list $nn $pr]
                lappend shapes [list $nn $pr "pin $iname/[[$it getMTerm] getName]"]
            }
        }
        if {[string match sg13cmos5l_* [[$inst getMaster] getName]]} { lappend cells [list $iname $ib $pins] }
    }

    set errs {}
    foreach e $drawn {
        lassign $e net r
        set nn [$net getName]
        set wa [rect_width $r]
        foreach sh $shapes {
            lassign $sh n2 r2 what
            if {$n2 eq $nn} continue
            lassign [rect_gap_prl $r $r2] gap prl
            set need [m3_space $wa [rect_width $r2] $prl]
            if {$gap < $need - $eps} { lappend errs "$nn $r is [format %.3f $gap] um from $what $r2, needs $need" }
        }
        # A drawn rect may enter a pad cell only where it lands on a pin of its own net.
        foreach c $cells {
            lassign $c iname ib pins
            lassign [rect_gap_prl $r $ib] gap prl
            if {$gap > $eps} continue
            set lands 0
            foreach p $pins {
                lassign $p pn pr
                lassign [rect_gap_prl $r $pr] g2 p2
                if {$pn eq $nn && $g2 <= $eps} { set lands 1 }
            }
            if {!$lands} { lappend errs "$nn $r enters $iname without landing on a pin of $nn" }
        }
    }

    # Each pin the wires are meant to join is covered by a drawn rect of its net.
    set want {}
    foreach s $sigs {
        lassign $s net pr dr
        lappend want [list [$net getName] $pr] [list [$net getName] $dr]
    }
    lappend want [list VDDA $band] [list VDDA $dvdd] [list VSS $dvss]
    foreach w $want {
        lassign $w nn pin
        set hit 0
        foreach e $drawn {
            lassign $e net r
            lassign [rect_gap_prl $r $pin] gap prl
            if {[$net getName] eq $nn && $gap <= $eps} { set hit 1 }
        }
        if {!$hit} { lappend errs "no drawn $nn shape reaches the pin at $pin" }
    }

    # VDD isolation: the VDDA strap touches no VDD shape, and no VDD shape touches a vdd pin of a cell on VDDA.
    set vdd [$block findNet VDD]
    foreach e $drawn {
        lassign $e net r
        if {[$net getName] ne "VDDA"} continue
        foreach v [net_shapes $vdd Metal3] {
            lassign [rect_gap_prl $r $v] gap prl
            if {$gap <= $eps} { lappend errs "VDDA strap $r touches VDD $v" }
        }
    }
    set nseg 0
    foreach inst [$block getInsts] {
        set it [$inst findITerm vdd]
        if {$it == "NULL" || [$it getNet] eq "NULL" || [[$it getNet] getName] ne "VDDA"} continue
        incr nseg
        foreach gm [$it getGeometries] {
            lassign $gm l r
            set ln [$l getName]
            set pr [list [expr {[$r xMin] / $dbu}] [expr {[$r yMin] / $dbu}] [expr {[$r xMax] / $dbu}] [expr {[$r yMax] / $dbu}]]
            foreach v [net_shapes $vdd $ln] {
                lassign [rect_gap_prl $pr $v] gap prl
                if {$gap <= $eps} { lappend errs "VDD $ln $v touches the vdd pin of [$inst getName] at $pr" }
            }
        }
    }
    puts "\[INFO\] analog wires: $nseg cells and macros with a vdd pin on VDDA checked against VDD"

    if {[llength $errs] > 0} {
        foreach e $errs { puts stderr "\[ERROR\] analog wires: $e" }
        fail_analog "[llength $errs] checks failed"
    }
    puts "\[INFO\] analog wires: spacing, pin landing and VDD isolation checks passed"
}

# Draw after pdngen has placed the rings and stripes.
rename pdngen pdngen_stock
proc pdngen {args} {
    pdngen_stock {*}$args
    draw_analog
}
