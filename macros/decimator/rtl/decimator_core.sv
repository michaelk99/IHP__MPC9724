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
// Decimator core
// ============================================================================
module decimator_core #(
    parameter int DATA_W  = 22,
    parameter int CIC_W   = 32,   // N*log2(D) + 2, integrators wrap in this
    parameter int W       = 27,   // datapath, see the note on headroom below
    parameter int ALIGN_W = 6,    // CIC gain 2^30 down to 2^(20+F)
    parameter int RND_W   = 4     // F, fraction bits below the output LSB
)(
    input  logic                     clk_fs,
    input  logic                     rst_b,
    input  logic signed [DATA_W-1:0] data_in,
    output logic signed [DATA_W-1:0] data_out,
    output logic                     valid_strobe
);
    // Headroom: W = 27 gives FINAL_W = W - RND_W = 23, one bit above DATA_W, so
    // the output saturate actually clamps. At W = 26 they were equal and an
    // overshoot wrapped instead, which matters because the compensator's gain at
    // the band edge is 4.4. A full-scale dc input puts 2^24 here, so W = 27
    // leaves two bits over that.
    logic ce_cic, ce_s1, ce_s2;

    ce_generator u_ce (
        .clk_fs(clk_fs), .rst_b(rst_b),
        .ce_cic(ce_cic), .ce_s1(ce_s1), .ce_s2(ce_s2)
    );

    // +-1 into the CIC, from the sign bit only, as in v4
    logic signed [CIC_W-1:0] cic_in;
    assign cic_in = {{(CIC_W-1){data_in[DATA_W-1]}}, 1'b1};

    logic signed [CIC_W-1:0] cic_out;
    cic_n6_d32 #(.DATA_W(CIC_W)) u_cic (
        .clk_fs(clk_fs), .rst_b(rst_b), .ce_comb(ce_cic),
        .data_in(cic_in), .data_out(cic_out)
    );

    // align the CIC gain to the datapath scale, rounding
    wire signed [CIC_W-1:0] cic_rnd = cic_out + (1 <<< (ALIGN_W - 1));
    /* verilator lint_off UNUSEDSIGNAL */
    wire signed [CIC_W-1:0] cic_sh  = cic_rnd >>> ALIGN_W;
    /* verilator lint_on UNUSEDSIGNAL */
    wire signed [W-1:0]     s1_in   = cic_sh[W-1:0];

    // sinc2^9 at 2048 Hz, its output taken every second event
    wire signed [W-1:0] s1_out;
    sinc2_chain #(.W(W), .M(9)) u_s1 (
        .clk_fs(clk_fs), .rst_b(rst_b), .ce(ce_cic),
        .data_in(s1_in), .data_out(s1_out)
    );

    logic signed [W-1:0] s2_in;
    always_ff @(posedge clk_fs) begin
        if (!rst_b)      s2_in <= '0;
        else if (ce_s1)  s2_in <= s1_out;
    end

    // sinc2^16 at 1024 Hz, its output taken every second event
    wire signed [W-1:0] s2_out;
    sinc2_chain #(.W(W), .M(16)) u_s2 (
        .clk_fs(clk_fs), .rst_b(rst_b), .ce(ce_s1),
        .data_in(s2_in), .data_out(s2_out)
    );

    logic signed [W-1:0] comp_in;
    always_ff @(posedge clk_fs) begin
        if (!rst_b)      comp_in <= '0;
        else if (ce_s2)  comp_in <= s2_out;
    end

    wire signed [W-1:0] comp_out;
    comp_fir #(.W(W)) u_comp (
        .clk_fs(clk_fs), .rst_b(rst_b), .ce(ce_s2),
        .data_in(comp_in), .data_out(comp_out)
    );

    // final round and saturate
    localparam int FINAL_W = W - RND_W;
    wire signed [W-1:0]       out_rnd  = comp_out + (1 <<< (RND_W - 1));
    /* verilator lint_off UNUSEDSIGNAL */
    wire signed [FINAL_W-1:0] out_trnc = out_rnd[W-1 -: FINAL_W];
    /* verilator lint_on UNUSEDSIGNAL */
    localparam signed [FINAL_W-1:0] DATA_MAX =  (1 <<< (DATA_W-1)) - 1;
    localparam signed [FINAL_W-1:0] DATA_MIN = -(1 <<< (DATA_W-1));

    logic signed [DATA_W-1:0] out_sat;
    always_comb begin
        if      (out_trnc > DATA_MAX) out_sat = DATA_MAX[DATA_W-1:0];
        else if (out_trnc < DATA_MIN) out_sat = DATA_MIN[DATA_W-1:0];
        else                          out_sat = out_trnc[DATA_W-1:0];
    end

    logic signed [DATA_W-1:0] out_reg;
    logic                     vs_r;
    always_ff @(posedge clk_fs) begin
        if (!rst_b) begin
            out_reg <= '0;
            vs_r    <= 1'b0;
        end else begin
            vs_r <= ce_s2;
            if (ce_s2) out_reg <= out_sat;
        end
    end

    assign data_out     = out_reg;
    assign valid_strobe = vs_r;
endmodule
