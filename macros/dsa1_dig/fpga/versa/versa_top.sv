// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Lattice ECP5 Versa top: the DUT harness on the board's 100 MHz clock, its LEDs
// showing AUX_CTRL_0[7:0]. They light on a low output, and its DIP switches read 0 when ON.

`timescale 1ns / 1ps

module versa_top (
    input  wire       clk_board,
    input  wire       rst_n_btn,
    input  wire       rst_n_pin,
    input  wire       ext_fs_sw_n,
    input  wire       clk_fs_pin,
    input  wire       data_in_pin,
    input  wire       sclk_pin,
    input  wire       mosi_pin,
    input  wire       ss_pin,
    output wire       miso_pin,
    output wire       adc_conv_pin,
    output wire [7:0] led_n
);
    wire [7:0] led;

    dsa1_dig_fpga_top #(.CLK_HZ(100_000_000), .LED_AUX(1'b1)) u_dut (
        .clk_board, .rst_n_btn, .rst_n_pin,
        .ext_fs_sw(~ext_fs_sw_n),
        .clk_fs_pin, .data_in_pin, .sclk_pin, .mosi_pin, .ss_pin,
        .miso_pin, .adc_conv_pin, .led);

    assign led_n = ~led;
endmodule
