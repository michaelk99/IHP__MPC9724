# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Chip timing constraints, used for implementation and signoff.
# STA_MACRO_PRIORITIZE_NL reads the macro's gate netlist, so this file times the macro's inside too. It carries the
# intent of macros/dsa1_dig/flow/librelane/dsa1_dig_top.sdc, which the macro is signed off with, translated to the pads.

current_design $::env(DESIGN_NAME)
set_units -time ns

# Clocks at the pad outputs, as the macro sees them. clk: the modulator clock, 65.536 kHz with data_in, 1.024 MHz with DEC_SRC, constrained at 950 ns.
# sclk: SPI clock on input_PAD[1], constrained at 10 MHz (real 200 kHz).
create_clock -name clk  -period 950.0 -waveform {0.0 475.0} [get_pins clk_pad/p2c]
create_clock -name sclk -period 100.0  -waveform {0.0 50.0}  [get_pins {g_inputs\[1\].input_pad/p2c}]

# As in the macro: 0.3 ns of setup guard band, 0.05 ns for hold, and no derate.
set_clock_uncertainty -setup 0.3 [get_clocks {clk sclk}]
set_clock_uncertainty -hold 0.05 [get_clocks {clk sclk}]
set_clock_transition $::env(CLOCK_TRANSITION_CONSTRAINT) [get_clocks {clk sclk}]

# clk and sclk are independent host-driven clocks. Crossings go through 3-FF synchronizers or carry held data.
set_clock_groups -asynchronous -group [get_clocks clk] -group [get_clocks sclk]

set_max_fanout $::env(MAX_FANOUT_CONSTRAINT) [current_design]
set_load [expr $::env(OUTPUT_CAP_LOAD) / 1000.0] [all_outputs]

# Asynchronous reset, as rst_b in the macro
set_false_path -from [get_ports rst_n_PAD]
# data_in has no known phase at the pad. It enters the core's 3-FF synchronizer, so its first flop is not a timed path.
set_false_path -from [get_ports {input_PAD[0]}]

# SPI inputs and outputs in the sclk domain
set_input_delay  -clock sclk -max 0.5 [get_ports {input_PAD[2] input_PAD[3]}]
set_input_delay  -clock sclk -min 0.0 [get_ports {input_PAD[2] input_PAD[3]}]
set sclk_outputs [get_ports {output_PAD[0]}]
set_output_delay -clock sclk -max 0.5 $sclk_outputs
set_output_delay -clock sclk -min 0.0 $sclk_outputs
# adc_conv is the clk-domain data-ready event
set_output_delay -clock clk -max 0.5 [get_ports {output_PAD[1]}]
set_output_delay -clock clk -min 0.0 [get_ports {output_PAD[1]}]

# dsm2 runs on its own clock pin and has no timed path to anything of the core: its controls are static
# registers, do_q_dec reaches the core only through the synchronizer, and its pads are observed off chip.
set_false_path -from [get_ports {dsm_clk_PAD}]
set_false_path -to   [get_ports {do_q_PAD do_q_b_PAD}]
set_false_path -to   [get_pins {dsm2/*}]
set_false_path -from [get_pins {dsm2/do_q dsm2/do_q_b dsm2/do_q_dec}]
set_false_path -through [get_ports {analog_PAD[*]}]

if { [info exists ::env(OPENLANE_SDC_IDEAL_CLOCKS)] && $::env(OPENLANE_SDC_IDEAL_CLOCKS) } {
    unset_propagated_clock [all_clocks]
} else {
    set_propagated_clock [all_clocks]
}
