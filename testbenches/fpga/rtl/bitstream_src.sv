// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// ============================================================================
// A window of the modulator record in BRAM, played one bit per clk_fs and
// looped. 131072 bits is 1024 output words, and 42 Hz is coherent in any
// multiple of 256 at 512 Hz, so the loop needs no windowing.
//
// Until started it plays the idle alternation, which decimates to zero.
// start only arms: the window begins one fall later, so the synchronous BRAM
// read always has a whole clk_fs period to fetch byte 0.
// ============================================================================

`timescale 1ns / 1ps

module bitstream_src #(
    parameter     MEM_FILE = "stream.mem",
    parameter int N_BITS   = 131072          // a power of two
)(
    input  wire                        clk,
    input  wire                        rst_b,
    input  wire                        fall,
    input  wire                        start,
    output logic                       data_in,
    output logic [$clog2(N_BITS)-1:0]  index    // the bit now on data_in
);
    localparam int AW = $clog2(N_BITS);

    logic [7:0] mem [0:N_BITS/8-1];
    initial $readmemh(MEM_FILE, mem);

    logic [AW-1:0] next;
    logic [7:0]    byte_q;
    logic          run, pending;

    always_ff @(posedge clk) byte_q <= mem[next[AW-1:3]];

    always_ff @(posedge clk) begin
        if (!rst_b) begin
            run     <= 1'b0;
            pending <= 1'b0;
            next    <= '0;
            index   <= '0;
            data_in <= 1'b0;
        end else if (start) begin
            run     <= 1'b0;
            pending <= 1'b1;
        end else if (fall) begin
            if (run) begin
                data_in <= byte_q[next[2:0]];
                index   <= next;
                next    <= next + 1'b1;
            end else begin
                data_in <= ~data_in;
                if (pending) begin
                    run     <= 1'b1;
                    pending <= 1'b0;
                    next    <= '0;
                end
            end
        end
    end
endmodule
