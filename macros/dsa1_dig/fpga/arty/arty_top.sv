// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Arty A7 top: the DUT harness on the board's 100 MHz oscillator, its LEDs
// showing AUX_CTRL_0[7:0], all eight under the host's control.

`timescale 1ns / 1ps

module arty_top (
    input  wire       clk_board,
    input  wire       rst_n_btn,
    input  wire       rst_n_pin,
    input  wire       ext_fs_sw,
    input  wire       clk_fs_pin,
    input  wire       data_in_pin,
    input  wire       sclk_pin,
    input  wire       mosi_pin,
    input  wire       ss_pin,
    output wire       miso_pin,
    output wire       adc_conv_pin,
    output wire [7:0] led
);
    dsa1_dig_fpga_top #(.CLK_HZ(100_000_000), .LED_AUX(1'b1)) u_dut (.*);
endmodule
