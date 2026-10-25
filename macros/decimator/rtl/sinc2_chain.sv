// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Michael Koefinger
// 2026-09-16
// ============================================================================
// CIC(N=6, D=32) + sinc2^9 + sinc2^16 + compensator FIR (v5)
// ----------------------------------------------------------------------------
// One module per file. decimator_top.sv is the top, decimator_core.sv wires the
// chain, the rest are the stages. The design note is in decimator_top.sv.
// SystemVerilog-2012, no default_nettype (ModelSim friendly), Genus safe: no
// dynamic index on the left-hand side of any state write.
// ============================================================================

`timescale 1ns / 1ps

// ============================================================================
// sinc2^M section chain
// ----------------------------------------------------------------------------
// M cascaded (1 + z^-1) sections at the input rate, each rounding one bit so
// the word stays at W. Rounding per section costs about 0.3 dB of in-band noise
// against rounding M bits once, and saves M bits of width inside the stage.
// The decimate-by-2 is the consumer sampling the output on every second ce.
// ============================================================================
module sinc2_chain #(
    parameter int W = 26,
    parameter int M = 9
)(
    input  logic                clk_fs,
    input  logic                rst_b,
    input  logic                ce,
    input  logic signed [W-1:0] data_in,
    output logic signed [W-1:0] data_out
);
    logic signed [W-1:0] sect  [0:M-1];   // previous input of each section
    logic signed [W-1:0] chain [0:M];     // chain[0] = input, chain[M] = output

    assign chain[0] = data_in;

    genvar g;
    generate
        for (g = 0; g < M; g++) begin : gen_sect
            // y = (x[n] + x[n-1] + 1) >>> 1, one bit of growth rounded away
            wire signed [W:0] sum = {chain[g][W-1], chain[g]} + {sect[g][W-1], sect[g]} + 1;
            assign chain[g+1] = sum[W:1];

            always_ff @(posedge clk_fs) begin
                if (!rst_b)   sect[g] <= '0;
                else if (ce)  sect[g] <= chain[g];
            end
        end
    endgenerate

    assign data_out = chain[M];
endmodule
