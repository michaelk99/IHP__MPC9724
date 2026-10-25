# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Arty A7-35T pins for arty_top. nextpnr-xilinx needs a pin and an IOSTANDARD
# on every port. Pins from the Digilent Arty-A7-35-Master.xdc, Rev. D.

# 100 MHz oscillator
set_property -dict {PACKAGE_PIN E3 IOSTANDARD LVCMOS33} [get_ports clk_board]
# on the net behind the input buffer: nextpnr-xilinx does not carry a
# constraint on the port through the IBUF and times it at its 12 MHz default
create_clock -period 10.000 [get_nets u_dut.clk_board]

# Red RESET button, active low
set_property -dict {PACKAGE_PIN C2 IOSTANDARD LVCMOS33} [get_ports rst_n_btn]

# SW0, read at reset: on takes clk_fs from Pmod JD pin 10
set_property -dict {PACKAGE_PIN A8 IOSTANDARD LVCMOS33 PULLTYPE PULLDOWN} [get_ports ext_fs_sw]

# Pmod JD, 200 Ohm series resistors on the board, standard Pmod SPI Type 2A order.
# Inputs are pulled so the DUT sits idle with nothing plugged in: ss and rst_n
# inactive high, the rest low.
set_property -dict {PACKAGE_PIN D4 IOSTANDARD LVCMOS33 PULLTYPE PULLUP}   [get_ports ss_pin]
set_property -dict {PACKAGE_PIN D3 IOSTANDARD LVCMOS33 PULLTYPE PULLDOWN} [get_ports mosi_pin]
set_property -dict {PACKAGE_PIN F4 IOSTANDARD LVCMOS33 DRIVE 4}           [get_ports miso_pin]
set_property -dict {PACKAGE_PIN F3 IOSTANDARD LVCMOS33 PULLTYPE PULLDOWN} [get_ports sclk_pin]
set_property -dict {PACKAGE_PIN E2 IOSTANDARD LVCMOS33 DRIVE 4}           [get_ports adc_conv_pin]
set_property -dict {PACKAGE_PIN D2 IOSTANDARD LVCMOS33 PULLTYPE PULLUP}   [get_ports rst_n_pin]
set_property -dict {PACKAGE_PIN H2 IOSTANDARD LVCMOS33 PULLTYPE PULLDOWN} [get_ports data_in_pin]
set_property -dict {PACKAGE_PIN G2 IOSTANDARD LVCMOS33 PULLTYPE PULLDOWN} [get_ports clk_fs_pin]

# led = AUX_CTRL_0[7:0] (arty_top sets LED_AUX): LD4..LD7 show bits 3:0, the
# green channels of RGB LD0..LD3 show bits 7:4
set_property -dict {PACKAGE_PIN H5 IOSTANDARD LVCMOS33} [get_ports {led[0]}]
set_property -dict {PACKAGE_PIN J5 IOSTANDARD LVCMOS33} [get_ports {led[1]}]
set_property -dict {PACKAGE_PIN T9 IOSTANDARD LVCMOS33} [get_ports {led[2]}]
set_property -dict {PACKAGE_PIN T10 IOSTANDARD LVCMOS33} [get_ports {led[3]}]
set_property -dict {PACKAGE_PIN F6 IOSTANDARD LVCMOS33} [get_ports {led[4]}]
set_property -dict {PACKAGE_PIN J4 IOSTANDARD LVCMOS33} [get_ports {led[5]}]
set_property -dict {PACKAGE_PIN J2 IOSTANDARD LVCMOS33} [get_ports {led[6]}]
set_property -dict {PACKAGE_PIN H6 IOSTANDARD LVCMOS33} [get_ports {led[7]}]
