// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Unit test: the Arty A7 build of the DUT harness, on its 100 MHz oscillator,
// converts at 512 Hz. With the harness's 25 MHz default it would run 4x fast.
// Its LEDs show AUX_CTRL_0[7:0], written over SPI.

`timescale 1ns / 1ps

module arty_top_tb;
    logic clk = 1'b0;
    always #5 clk = ~clk;                   // 100 MHz Arty oscillator

    logic sclk = 1'b0;
    always #1250 sclk = ~sclk;              // 400 kHz, running all the time as the ESP32 host does

    logic rst_btn = 1'b0;
    logic ss = 1'b1, mosi = 1'b0;
    wire  miso, conv;
    wire [7:0] led;

    arty_top u_dut (
        .clk_board(clk), .rst_n_btn(rst_btn), .rst_n_pin(1'b1), .ext_fs_sw(1'b0),
        .clk_fs_pin(1'b0), .data_in_pin(1'b0), .sclk_pin(sclk), .mosi_pin(mosi),
        .ss_pin(ss), .miso_pin(miso), .adc_conv_pin(conv), .led(led));

    // One SPI transaction: read flag and 4 address bits, a dummy, 16 data bits,
    // a dummy. Returns the 16 bits shifted out on miso, the old value on a write.
    task automatic spi(input [4:0] addr, input [15:0] wdata, output [15:0] rdata);
        logic [22:0] frame;
        frame = {addr, 1'b0, wdata, 1'b0};
        rdata = 16'h0;
        @(negedge sclk);
        #1 ss = 1'b0;
        mosi = frame[22];
        for (int k = 22; k >= 0; k--) begin
            @(negedge sclk);
            if (k >= 1 && k <= 16) rdata = {rdata[14:0], miso};
            #1 mosi = (k > 0) ? frame[k-1] : 1'b0;
        end
        @(negedge sclk);
        #1 ss = 1'b1;
        mosi = 1'b0;
    endtask

    realtime t0, t1;
    logic [15:0] old;

    initial begin
        #200_000 rst_btn = 1'b1;
        @(posedge conv) t0 = $realtime;
        @(posedge conv) t1 = $realtime;
        if (t1 - t0 < 1_953_105 || t1 - t0 > 1_953_145)   // 128 / 65536 Hz, within two board clocks
            $fatal(1, "FAIL: conversion period %0.1f ns, want 1953125", t1 - t0);
        if (led !== 8'h00)
            $fatal(1, "FAIL: LEDs 0x%02h after reset, want AUX_CTRL_0[7:0] = 0x00", led);
        spi(5'b0_1100, 16'hFFA5, old);      // write AUX_CTRL_0
        if (old !== 16'hFF00)
            $fatal(1, "FAIL: the write returned 0x%04h, want the reset value 0xFF00", old);
        #1000;
        if (led !== 8'hA5)
            $fatal(1, "FAIL: LEDs 0x%02h after writing AUX_CTRL_0 = 0xFFA5, want 0xA5", led);
        $display("PASS: arty_top_tb, 100 MHz board clock converts at 512 Hz, LEDs show AUX_CTRL_0[7:0]");
        $finish;
    end
endmodule
