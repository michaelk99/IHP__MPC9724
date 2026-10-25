// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Unit test: the ECP5 Versa build of the DUT harness converts at 512 Hz from
// the board's 100 MHz clock, shows AUX_CTRL_0[7:0] on its active-low LEDs, and
// takes clk_fs from the pin when DIP switch SW3-1 is ON, which reads 0.
// With +define+DUO it tests versa_duo_top instead, which also switches its bus to
// the DSA1 die's back end through TEST_CTRL_1, where CHIP_ID reads 0x0000.

`timescale 1ns / 1ps
`include "../../../macros/dsa1_dig/rtl/dsa1_regs.vh"  // generated from macros/dsa1_dig/regmap.yaml

module versa_top_tb;
    logic clk = 1'b0;
    always #5 clk = ~clk;                   // 100 MHz Versa oscillator
    logic ext_clk = 1'b0;
    always #5000 ext_clk = ~ext_clk;        // 100 kHz, so it cannot pass for 65536 Hz
    logic sclk = 1'b0;
    always #1250 sclk = ~sclk;              // 400 kHz, as the ESP32 host runs it

    logic rst_btn = 1'b0;
    logic sw_n    = 1'b1;                   // SW3-1 OFF
    logic ss = 1'b1, mosi = 1'b0;
    wire  miso, conv;
    wire [7:0] led_n;

`ifdef DUO
    versa_duo_top u_dut (
`else
    versa_top u_dut (
`endif
        .clk_board(clk), .rst_n_btn(rst_btn), .rst_n_pin(1'b1), .ext_fs_sw_n(sw_n),
        .clk_fs_pin(ext_clk), .data_in_pin(1'b0), .sclk_pin(sclk), .mosi_pin(mosi),
        .ss_pin(ss), .miso_pin(miso), .adc_conv_pin(conv), .led_n(led_n));

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
    logic [15:0] rd;

    initial begin
        #200_000 rst_btn = 1'b1;
        @(posedge conv) t0 = $realtime;
        @(posedge conv) t1 = $realtime;
        if (t1 - t0 < 1_953_105 || t1 - t0 > 1_953_145)   // 128 / 65536 Hz, within two board clocks
            $fatal(1, "FAIL: own clock, conversion period %0.1f ns, want 1953125", t1 - t0);

        if (led_n !== 8'hFF)
            $fatal(1, "FAIL: LEDs 0x%02h after reset, want ~AUX_CTRL_0[7:0] = 0xFF", led_n);
        spi({1'b0, `DSA1_AUX_CTRL_0_ADDR}, 16'hFFA5, rd);
        if (rd !== `DSA1_AUX_CTRL_0_RESET)
            $fatal(1, "FAIL: the AUX_CTRL_0 write returned 0x%04h, want the reset value", rd);
        if (led_n !== 8'h5A)
            $fatal(1, "FAIL: LEDs 0x%02h after writing AUX_CTRL_0 = 0xFFA5, want 0x5A, active low", led_n);

        spi({1'b1, `DSA1_CHIP_ID_ADDR}, 16'h0000, rd);
        if (rd !== `DSA1_CHIP_ID_RESET)
            $fatal(1, "FAIL: CHIP_ID reads 0x%04h, want this chip's", rd);
`ifdef DUO
        // the switch moves on the rising ss after the write, the next frame reaches the DSA1 back end
        spi({1'b0, `DSA1_TEST_CTRL_1_ADDR}, 16'h0001 << `DSA1_TEST_CTRL_1_BUS_DSA1_LSB, rd);
        spi({1'b1, `DSA1_CHIP_ID_ADDR}, 16'h0000, rd);
        if (rd !== 16'h0000)
            $fatal(1, "FAIL: after TEST_CTRL_1 BUS_DSA1, CHIP_ID reads 0x%04h, want the DSA1 die's 0x0000", rd);
`endif

        sw_n = 1'b0;                        // SW3-1 ON, read at reset
        rst_btn = 1'b0;
        #200_000 rst_btn = 1'b1;
        @(posedge conv) t0 = $realtime;
        @(posedge conv) t1 = $realtime;
        if (t1 - t0 != 1_280_000)           // 128 periods of 10 us
            $fatal(1, "FAIL: switch ON, conversion period %0.1f ns, want 1280000", t1 - t0);

`ifdef DUO
        $display("PASS: versa_top_tb DUO, 100 MHz clock, LEDs show AUX_CTRL_0, switch, bus to the DSA1 back end");
`else
        $display("PASS: versa_top_tb, 100 MHz clock, LEDs show AUX_CTRL_0 active low, switch");
`endif
        $finish;
    end
endmodule
