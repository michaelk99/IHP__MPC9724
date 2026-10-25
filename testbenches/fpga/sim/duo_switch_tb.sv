// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Unit test: the eval board's two digital back ends in one harness, this chip's
// (decimator v5, 512 Hz) and the DSA1 die's (legacy, decimator v4, 256 Hz),
// behind one SPI bus. Writing TEST_CTRL_1[1] = 1 switches the bus to the legacy
// slave and 0 back, at the next rising edge of ss, never inside a frame. The
// harness decodes the write from the bus, whichever slave takes it. AUX_CTRL_0
// only drives the LEDs, and CHIP_ID tells the two dies apart. The choice survives
// the DUT reset and the board button returns to this chip's slave.

`timescale 1ns / 1ps

module duo_switch_tb;
    logic clk = 1'b0;
    always #20 clk = ~clk;                  // 25 MHz board oscillator
    logic sclk = 1'b0;
    always #1250 sclk = ~sclk;              // 400 kHz, running all the time as the hosts do

    logic rst_n_pin = 1'b0, rst_n_btn = 1'b1;
    logic ss = 1'b1, mosi = 1'b0;
    wire  miso, conv;
    wire [7:0] led;

    dsa1_dig_fpga_top #(.DUO(1'b1), .LED_AUX(1'b1)) u_dut (
        .clk_board(clk), .rst_n_btn(rst_n_btn), .rst_n_pin(rst_n_pin), .ext_fs_sw(1'b0),
        .clk_fs_pin(1'b0), .data_in_pin(1'b0), .sclk_pin(sclk), .mosi_pin(mosi),
        .ss_pin(ss), .miso_pin(miso), .adc_conv_pin(conv), .led(led));

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
        repeat (4) @(negedge sclk);         // the gap between frames
    endtask

    task automatic period(output realtime p);
        realtime a, b;
        @(posedge conv) a = $realtime;
        @(posedge conv) b = $realtime;
        p = b - a;
    endtask

    // 128 or 256 periods of 65536 Hz, within two board clocks of fs_gen's accumulator
    function automatic bit is_v5(realtime p);
        return p > 1_953_045 && p < 1_953_205;
    endfunction
    function automatic bit is_v4(realtime p);
        return p > 3_906_170 && p < 3_906_330;
    endfunction

    // the bus never moves while ss is low
    always @(u_dut.sel_legacy)
        if (ss === 1'b0 && $realtime > 0)
            $fatal(1, "FAIL: the bus switched inside a frame at %0.1f ns", $realtime);

    logic [15:0] r;
    realtime     p;

    initial begin
        #200_000 rst_n_pin = 1'b1;
        period(p);
        if (!is_v5(p)) $fatal(1, "FAIL: after reset the bus is not on this chip's slave, conversion period %0.1f ns", p);
        spi(5'b1_1111, 16'h0000, r);
        if (r !== 16'h0001) $fatal(1, "FAIL: this chip's CHIP_ID reads 0x%04h, want 0x0001", r);

        // AUX_CTRL_0 drives the LEDs, all eight, and switches nothing, the old code 0xFF04 included
        spi(5'b0_1100, 16'hFF04, r);
        period(p);
        if (!is_v5(p)) $fatal(1, "FAIL: AUX_CTRL_0 = 0xFF04 moved the bus, period %0.1f ns", p);
        if (led !== 8'h04) $fatal(1, "FAIL: LEDs 0x%02h, want AUX_CTRL_0[7:0] = 0x04", led);
        // a read of TEST_CTRL_1 writes nothing, whatever mosi carries
        spi(5'b1_1101, 16'hFFFF, r);
        period(p);
        if (!is_v5(p)) $fatal(1, "FAIL: a read of TEST_CTRL_1 moved the bus, period %0.1f ns", p);

        spi(5'b0_1101, 16'h0002, r);        // TEST_CTRL_1[1]: to the legacy slave
        spi(5'b1_1111, 16'h0000, r);
        if (r !== 16'h0000) $fatal(1, "FAIL: the DSA1 back end's CHIP_ID reads 0x%04h, want 0x0000", r);
        period(p);
        if (!is_v4(p)) $fatal(1, "FAIL: adc_conv is not the legacy decimator's 256 Hz, period %0.1f ns", p);
        if (led !== 8'h00) $fatal(1, "FAIL: LEDs 0x%02h, want the legacy AUX_CTRL_0[7:0] = 0x00", led);

        // the reset returns both TEST_CTRL_1 to 0 and the harness keeps the choice, also
        // once frames run again, which is when a lost choice would show
        rst_n_pin = 1'b0;
        #200_000 rst_n_pin = 1'b1;
        spi(5'b1_1110, 16'h0000, r);
        spi(5'b1_1110, 16'h0000, r);
        period(p);
        if (!is_v4(p)) $fatal(1, "FAIL: a DUT reset dropped the legacy choice, period %0.1f ns", p);

        spi(5'b0_1101, 16'h0000, r);        // written to the legacy slave: back
        spi(5'b1_1111, 16'h0000, r);
        if (r !== 16'h0001) $fatal(1, "FAIL: back on this chip's slave CHIP_ID reads 0x%04h, want 0x0001", r);
        period(p);
        if (!is_v5(p)) $fatal(1, "FAIL: back on this chip's slave, conversion period %0.1f ns", p);

        // the board button returns to this chip's slave
        spi(5'b0_1101, 16'h0002, r);
        rst_n_btn = 1'b0;
        #200_000 rst_n_btn = 1'b1;
        period(p);
        if (!is_v5(p)) $fatal(1, "FAIL: the button left the legacy slave selected, period %0.1f ns", p);

        $display("PASS: duo_switch_tb, one bus to both digital back ends, switched between frames through TEST_CTRL_1");
        $finish;
    end
endmodule
