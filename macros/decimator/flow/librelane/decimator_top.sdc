# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Timing constraints for decimator_top on EZ130, used for both implementation and signoff.
# Translated from the Genus constraints of dsa1_dig_top:
#   svn r_tapeouts/2024_DSADC/TO_IHPSG13G2/cad_libs/TO_DSA1_DIGITAL/DIG_TOP/syn_genus/scripts_ihpsg13/constraints.sdc
# Only the clk domain applies here. Deviations from that file are listed in ../../README.md.

# Clock: 1000 ns as in Genus. The real modulator clock is 65.536 kHz.
create_clock -name clk_fs -period $::env(CLOCK_PERIOD) -waveform [list 0 [expr {$::env(CLOCK_PERIOD) / 2.0}]] [get_ports clk_fs]
# 0.3 ns as in Genus, but as a setup guard band only. Applied to hold as well it costs 0.3 ns of delay on every short
# path, which on this slow clock filled the netlist with hold buffers (12234 of them, 69355 um2, measured 2026-09-11).
set_clock_uncertainty -setup 0.3 [get_clocks clk_fs]
set_clock_uncertainty -hold 0.05 [get_clocks clk_fs]
# Acts only before CTS. Propagated clocks replace it afterwards.
set_clock_transition 0.2 [get_clocks clk_fs]

# Design-rule limits. EZ130's liberty has no default max capacitance and a 5.33 ns default max transition, so these are the real bounds.
set_max_transition 1.0 [current_design]
set_max_capacitance 0.3 [current_design]
set_max_fanout 16 [current_design]

# Drive and load. DFFRQX3 is the EZ130 flop that stands in for Genus' DFRSQJIX2 driver.
set_drive 0 [get_ports clk_fs]
set_driving_cell -lib_cell DFFRQX3 -pin Q [get_ports {rst_b data_in}]
# Digital output pad buffer input (4 fF) with 8x margin, as in Genus.
set_load 0.032 [all_outputs]

# data_in is sampled on the falling clk edge inside the comparator and captured on the rising edge here, a half-cycle path.
# Sampler clock-to-Q from the Genus analysis: 0.40 ns max (slow corner, 32 fF), 0.10 ns min (fast corner).
set_input_delay -clock clk_fs -clock_fall -max 0.40 [get_ports data_in]
set_input_delay -clock clk_fs -clock_fall -min 0.10 [get_ports data_in]

# rst_b is timed, not a false path as in Genus. The decimator uses it as a synchronous reset, driven by a clk-domain register (dec_en_s3) in dsa1_dig_top.
set_input_delay -clock clk_fs -max 0.5 [get_ports rst_b]
set_input_delay -clock clk_fs -min 0.10 [get_ports rst_b]

# valid_strobe becomes adc_conv, data_out is held data for the SPI register file. Both launch in the clk domain.
set_output_delay -clock clk_fs -max 0.5 [all_outputs]
set_output_delay -clock clk_fs -min 0.0 [all_outputs]
