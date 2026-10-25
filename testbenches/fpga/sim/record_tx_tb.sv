// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Unit test: two records back to back come out as 18 UART bytes, 8N1 at
// 115200, with bit 7 set only on the first byte of each record.

`timescale 1ns / 1ps

module record_tx_tb;
    localparam real BIT_NS = 1.0e9 / 115200.0;

    logic clk = 1'b0;
    always #20 clk = ~clk;
    logic        rst_b = 1'b0;
    logic [62:0] payload = '0;
    logic        valid = 1'b0;
    wire         ready, tx;

    record_tx u_rec (.clk(clk), .rst_b(rst_b), .payload(payload), .valid(valid),
                     .ready(ready), .tx(tx));

    logic [62:0] sent [0:1];
    logic [7:0]  got  [0:17];
    logic [7:0]  b, want;
    integer      n = 0;

    // Receiver, sampling mid-bit.
    initial forever begin
        @(negedge tx);
        #(BIT_NS * 1.5);
        for (int i = 0; i < 8; i++) begin
            b[i] = tx;
            #(BIT_NS);
        end
        if (tx !== 1'b1) $fatal(1, "FAIL: no stop bit after byte %0d", n);
        got[n] = b;
        n = n + 1;
    end

    initial begin
        sent[0] = 63'h2A5A_A5A5_0F0F_F0F0;
        sent[1] = {3'd1, 60'h123_4567_89AB_CDEF};
        #200 rst_b = 1'b1;
        for (int r = 0; r < 2; r++) begin
            @(posedge clk);
            while (!ready) @(posedge clk);
            payload <= sent[r];
            valid   <= 1'b1;
            @(posedge clk);
            valid   <= 1'b0;
        end
        wait (n == 18);
        for (int r = 0; r < 2; r++)
            for (int i = 0; i < 9; i++) begin
                want = {i == 0, sent[r][62 - 7*i -: 7]};
                if (got[9*r + i] !== want)
                    $fatal(1, "FAIL: record %0d byte %0d is %02x, want %02x", r, i, got[9*r + i], want);
            end
        $display("PASS: record_tx_tb, 2 records, 18 bytes");
        $finish;
    end
endmodule
