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
// CIC, N = 6, D = 32
// ----------------------------------------------------------------------------
// Integrators run at clk_fs and are allowed to wrap: modulo anything above the
// chain gain the comb output is still exact (Hogenauer), and an arithmetic
// error only causes a finite transient. CIC_W = N*log2(D) + 2 = 32.
// ============================================================================
module cic_n6_d32 #(
    parameter int DATA_W = 32
)(
    input  logic                     clk_fs,
    input  logic                     rst_b,
    input  logic                     ce_comb,
    input  logic signed [DATA_W-1:0] data_in,
    output logic signed [DATA_W-1:0] data_out
);
    localparam int N = 6;

    logic signed [DATA_W-1:0] int_reg [0:N-1];
    logic signed [DATA_W-1:0] comb_d  [0:N-1];   // one delay per comb, no pipeline
    logic signed [DATA_W-1:0] comb_q  [0:N-1];   // combinational

    always_ff @(posedge clk_fs) begin
        if (!rst_b) begin
            int_reg[0] <= '0; int_reg[1] <= '0; int_reg[2] <= '0;
            int_reg[3] <= '0; int_reg[4] <= '0; int_reg[5] <= '0;
        end else begin
            int_reg[0] <= int_reg[0] + data_in;
            int_reg[1] <= int_reg[1] + int_reg[0];
            int_reg[2] <= int_reg[2] + int_reg[1];
            int_reg[3] <= int_reg[3] + int_reg[2];
            int_reg[4] <= int_reg[4] + int_reg[3];
            int_reg[5] <= int_reg[5] + int_reg[4];
        end
    end

    // The combs are combinational through the chain, so each stage needs only its
    // own delay register. v4 pipelines them as well, which costs N registers of
    // DATA_W and buys nothing at 2048 Hz.
    always_comb begin
        comb_q[0] = int_reg[N-1] - comb_d[0];
        comb_q[1] = comb_q[0]    - comb_d[1];
        comb_q[2] = comb_q[1]    - comb_d[2];
        comb_q[3] = comb_q[2]    - comb_d[3];
        comb_q[4] = comb_q[3]    - comb_d[4];
        comb_q[5] = comb_q[4]    - comb_d[5];
    end

    always_ff @(posedge clk_fs) begin
        if (!rst_b) begin
            for (int i = 0; i < N; i++) comb_d[i] <= '0;
        end else if (ce_comb) begin
            comb_d[0] <= int_reg[N-1];
            comb_d[1] <= comb_q[0];
            comb_d[2] <= comb_q[1];
            comb_d[3] <= comb_q[2];
            comb_d[4] <= comb_q[3];
            comb_d[5] <= comb_q[4];
        end
    end

    logic signed [DATA_W-1:0] out_reg;
    always_ff @(posedge clk_fs) begin
        if (!rst_b)        out_reg <= '0;
        else if (ce_comb)  out_reg <= comb_q[N-1];
    end

    assign data_out = out_reg;
endmodule
