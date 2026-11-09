# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# One STA run: one PVT corner and one SPEF set. Mirrors LibreLane's OpenROAD.STAPostPNR (read libs, netlists, SDC, SPEF).
# Inputs come from the environment, see run_sta.sh.
define_corners $::env(CORNER)
foreach l [split $::env(LIBS) " "] { read_liberty -corner $::env(CORNER) $l }
foreach n [split $::env(MACRO_NLS) " "] { if {$n ne ""} { read_verilog $n } }
read_verilog $::env(TOP_NL)
link_design $::env(DESIGN_NAME)
set ::env(IO_PCT) 0.2
read_sdc $::env(SDC)
if { ![catch {exec grep -q set_propagated_clock $::env(SDC)}] } {
} else {
    set_propagated_clock [all_clocks]
}
read_spef -corner $::env(CORNER) $::env(SPEF)
if { $::env(MACRO_SPEF) ne "" } { read_spef -corner $::env(CORNER) -path $::env(MACRO_INST) $::env(MACRO_SPEF) }
set_cmd_units -time ns -capacitance pF -current mA -voltage V -resistance kOhm -distance um
set sta_report_default_digits 4
report_check_types -max_slew -max_capacitance -max_fanout -violators > $::env(OUT)/checks.rpt
set o [open $::env(OUT)/summary.txt w]
puts $o "setup_ws [worst_slack -max]"
puts $o "hold_ws [worst_slack -min]"
puts $o "setup_tns [total_negative_slack -max]"
puts $o "hold_tns [total_negative_slack -min]"
puts $o "max_slew_violations [sta::max_slew_violation_count]"
puts $o "max_cap_violations [sta::max_capacitance_violation_count]"
puts $o "max_fanout_violations [sta::max_fanout_violation_count]"
close $o
report_checks -path_delay max -group_path_count 1 -fields {slew cap fanout} -format full_clock_expanded > $::env(OUT)/worst_setup.rpt
report_checks -path_delay min -group_path_count 1 -fields {slew cap fanout} -format full_clock_expanded > $::env(OUT)/worst_hold.rpt
check_setup -verbose -unconstrained_endpoints -multiple_clock -no_clock -no_input_delay -loops -generated_clocks > $::env(OUT)/check_setup.rpt
report_parasitic_annotation -report_unannotated > $::env(OUT)/annotation.rpt
exit
