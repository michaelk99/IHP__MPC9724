// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Unit test: idle alternation, a fall in the cycle right after start, the
// window played bit by bit, and the wrap.

`timescale 1ns / 1ps

module bitstream_src_tb;
    logic clk = 1'b0;
    always #20 clk = ~clk;
    logic rst_b = 1'b0, fall = 1'b0, start = 1'b0;
    wire       data_in;
    wire [5:0] index;

    bitstream_src #(.MEM_FILE("sim/stream_test.mem"), .N_BITS(64)) u_src (
        .clk(clk), .rst_b(rst_b), .fall(fall), .start(start), .data_in(data_in), .index(index));

    task automatic do_fall;
        @(posedge clk) fall <= 1'b1;
        @(posedge clk) fall <= 1'b0;
        repeat (8) @(posedge clk);
    endtask

    logic prev;
    int   p;
    initial begin
        repeat (4) @(posedge clk);
        rst_b <= 1'b1;
        do_fall;
        prev = data_in;
        do_fall;
        if (data_in === prev) $fatal(1, "FAIL: no idle alternation before start");
        prev = data_in;

        // start, then a fall in the very next cycle
        @(posedge clk) start <= 1'b1;
        @(posedge clk) begin start <= 1'b0; fall <= 1'b1; end
        @(posedge clk) fall <= 1'b0;
        repeat (8) @(posedge clk);
        if (data_in !== ~prev) $fatal(1, "FAIL: the fall right after start did not toggle");

        for (p = 0; p < 70; p++) begin
            do_fall;
            if (index !== 6'(p % 64) || data_in !== ((p % 64) % 9 == 0))
                $fatal(1, "FAIL: step %0d, index %0d data %b", p, index, data_in);
        end
        $display("PASS: bitstream_src_tb, 70 bits, wrap and start hazard");
        $finish;
    end
endmodule
