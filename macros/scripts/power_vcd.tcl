# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Power of a hardened macro from a gate-level VCD, for one corner, with OpenSTA.
#
#   sta -no_splash -exit power_vcd.tcl
#
# Inputs from the environment:
#   TOP      top module
#   NETLIST  final/nl/<top>.nl.v (no power pins)
#   SPEF     final/spef/nom/<top>.nom.spef
#   LIBS     liberty files of the corner, space separated
#   SDC      the macro SDC (clock definitions, loads, drives)
#   CLOCKS   real clock periods for the power run, "<port> <period_ns> ...", replacing the SDC periods
#   ACT      set_power_activity file written by vcd_activity_sta.py from the gate-level VCD
#   CLOCK_PERIOD  value the macro SDC reads from the environment, as LibreLane sets it
#
# Not read_vcd: OpenSTA looks its signals up with findPin, and after place and route the design is flat, so only the
# top-level ports are pins. It annotated 153 of 9898 signals here and propagated everything else from them.
# vcd_activity_sta.py counts the transitions itself and writes set_power_activity -density for each driving pin.

foreach lib $::env(LIBS) {
    read_liberty $lib
}
read_verilog $::env(NETLIST)
link_design $::env(TOP)
read_sdc $::env(SDC)

foreach {port period} $::env(CLOCKS) {
    create_clock -name $port -period $period [get_ports $port]
}
set_propagated_clock [all_clocks]
read_spef $::env(SPEF)
source $::env(ACT)

report_power -digits 6
