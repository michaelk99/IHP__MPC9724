// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Unit test: the DUT harness runs from clk_fs_pin when SW1 is on at reset, from
// its own accumulator when it is off, and stops while rst_n_pin is low. A host
// with no hand on the switch asks for clk_fs_pin by writing TEST_CTRL_1[0] = 1,
// and for the board clock again with 0, each taking effect at the next reset and
// surviving the DUT resets after it, until the board button.

`timescale 1ns / 1ps

module dut_extclk_tb;
    logic clk = 1'b0;
    always #20 clk = ~clk;                  // 25 MHz board oscillator
    logic ext_clk = 1'b0;
    always #5000 ext_clk = ~ext_clk;        // 100 kHz, so it cannot pass for 65536 Hz

    logic rst_n_pin = 1'b0;
    logic rst_n_btn = 1'b1;
    logic ext_sw = 1'b1;
    logic sclk = 1'b0;
    always #1250 sclk = ~sclk;              // 400 kHz, running all the time as the hosts do
    logic ss = 1'b1, mosi = 1'b0;
    wire  miso, conv;
    wire [7:0] led;

    dsa1_dig_fpga_top u_dut (
        .clk_board(clk), .rst_n_btn(rst_n_btn), .rst_n_pin(rst_n_pin), .ext_fs_sw(ext_sw),
        .clk_fs_pin(ext_clk), .data_in_pin(1'b0), .sclk_pin(sclk), .mosi_pin(mosi),
        .ss_pin(ss), .miso_pin(miso), .adc_conv_pin(conv), .led(led));

    // One transaction: read flag and 4 address bits, a dummy, 16 data bits, a dummy.
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

    // the conversion period after a reset of the pin, as a host's P or I gives
    task automatic period_after_reset(output realtime p);
        realtime a, b;
        rst_n_pin = 1'b0;
        #200_000 rst_n_pin = 1'b1;
        @(posedge conv) a = $realtime;
        @(posedge conv) b = $realtime;
        p = b - a;
    endtask

    function automatic bit is_ext(realtime p);
        return p == 1_280_000;
    endfunction
    function automatic bit is_own(realtime p);
        return p > 1_953_045 && p < 1_953_205;
    endfunction

    logic [15:0] old;
    realtime     p;

    integer   edges = 0;
    realtime  t0, t1;
    always @(posedge conv) edges = edges + 1;

    initial begin
        #200_000 rst_n_pin = 1'b1;
        @(posedge conv) t0 = $realtime;
        @(posedge conv) t1 = $realtime;
        if (t1 - t0 != 1_280_000)           // 128 periods of 10 us
            $fatal(1, "FAIL: external clock, conversion period %0t ns, want 1280000", t1 - t0);

        ext_sw = 1'b0;
        rst_n_pin = 1'b0;
        #200_000 rst_n_pin = 1'b1;
        @(posedge conv) t0 = $realtime;
        @(posedge conv) t1 = $realtime;
        if (t1 - t0 < 1_953_045 || t1 - t0 > 1_953_205)   // 128 / 65536 Hz, within two board clocks
            $fatal(1, "FAIL: own clock, conversion period %0t ns, want 1953125", t1 - t0);

        rst_n_pin = 1'b0;
        #5000 edges = 0;
        #3_000_000;
        if (edges != 0)
            $fatal(1, "FAIL: %0d conversions while rst_n_pin was low", edges);

        // switch off: TEST_CTRL_1[0] asks for the pin's clock from the next reset on
        rst_n_pin = 1'b1;
        #200_000 spi(5'b0_1101, 16'h0001, old);
        if (old !== 16'h0000)
            $fatal(1, "FAIL: TEST_CTRL_1 read 0x%04h before the write, want the reset value 0x0000", old);
        period_after_reset(p);
        if (!is_ext(p))
            $fatal(1, "FAIL: TEST_CTRL_1[0] then a reset, conversion period %0.1f ns, want the pin's 1280000", p);
        // the reset returned the DUT's TEST_CTRL_1 to 0, the harness keeps its copy through the next one
        period_after_reset(p);
        if (!is_ext(p))
            $fatal(1, "FAIL: a second reset dropped the request, conversion period %0.1f ns", p);
        // AUX_CTRL_0 is the LEDs' and asks for nothing
        spi(5'b0_1100, 16'hFF02, old);
        period_after_reset(p);
        if (!is_ext(p))
            $fatal(1, "FAIL: AUX_CTRL_0 = 0xFF02 moved clk_fs, conversion period %0.1f ns", p);

        // TEST_CTRL_1[0] = 0 asks for the board clock again
        spi(5'b0_1101, 16'h0000, old);
        period_after_reset(p);
        if (!is_own(p))
            $fatal(1, "FAIL: TEST_CTRL_1 = 0 then a reset, conversion period %0.1f ns, want 1953125", p);

        // the board button clears a request
        spi(5'b0_1101, 16'h0001, old);
        rst_n_btn = 1'b0;
        #200_000 rst_n_btn = 1'b1;
        @(posedge conv) t0 = $realtime;
        @(posedge conv) t1 = $realtime;
        if (!is_own(t1 - t0))
            $fatal(1, "FAIL: the button left the pin's clock selected, conversion period %0.1f ns", t1 - t0);

        $display("PASS: dut_extclk_tb, external clock, own clock, reset pin, and the TEST_CTRL_1 request");
        $finish;
    end
endmodule
