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
// Compensator, 9 taps, symmetric, folded, time multiplexed
// ----------------------------------------------------------------------------
// The taps are symmetric, so pairs are pre-added and one product serves both:
// five products per output sample. Those five used to be five CSD multipliers
// standing side by side, which is the densest arithmetic in the block, and they
// are idle almost all the time: the compensator runs at 512 Hz with 128 clocks
// per sample and needs 35 of them.
//
// So one shift-add engine walks the five taps, six CSD terms each, exactly the
// arithmetic the parallel version did and in the same order: terms accumulated
// at the tap's own scale, rounded once per product, products summed. Nothing
// about the result changes, which is why the bit-true model does not change
// either and the equality gate still has to pass.
//
// Term table, from dec_design_comp.m (see section 4):
//   b0 = 28997/2^18   +2^15 -2^12 +2^8 +2^6 +2^2 +2^0
//   b1 = -6243/2^13   -2^13 +2^11 -2^7 +2^5 -2^2 +2^0
//   b2 =  44815/2^14  +2^15 +2^13 +2^12 -2^8 +2^4 -2^0
//   b3 =  -1639/2^8   -2^11 +2^9 -2^7 +2^5 -2^3 +2^0
//   b4 =   2467/2^8   +2^11 +2^9 -2^6 -2^5 +2^2 -2^0
// ============================================================================
module comp_fir #(
    parameter int W = 27
)(
    input  logic                clk_fs,
    input  logic                rst_b,
    input  logic                ce,
    input  logic signed [W-1:0] data_in,
    output logic signed [W-1:0] data_out
);
    localparam int WP    = W + 1;        // the pre-adder grows by one
    localparam int ACC_W = WP + 17;      // the largest term is x <<< 15, plus guard

    logic signed [W-1:0] d [0:7];

    always_ff @(posedge clk_fs) begin
        if (!rst_b) begin
            for (int i = 0; i < 8; i++) d[i] <= '0;
        end else if (ce) begin
            d[0] <= data_in;
            d[1] <= d[0]; d[2] <= d[1]; d[3] <= d[2];
            d[4] <= d[3]; d[5] <= d[4]; d[6] <= d[5]; d[7] <= d[6];
        end
    end

    // The five folded operands, combinational. data_in and d hold still between
    // ce events, so there is nothing to register, and taking them combinationally
    // is what keeps the tap alignment identical to the parallel version: x[n] is
    // data_in, x[n-1-i] is d[i].
    wire signed [WP-1:0] s [0:4];
    assign s[0] = {data_in[W-1], data_in} + {d[7][W-1], d[7]};
    assign s[1] = {d[0][W-1],    d[0]}    + {d[6][W-1], d[6]};
    assign s[2] = {d[1][W-1],    d[1]}    + {d[5][W-1], d[5]};
    assign s[3] = {d[2][W-1],    d[2]}    + {d[4][W-1], d[4]};
    assign s[4] = {d[3][W-1],    d[3]};

    // 5 taps x 6 terms, then one finalise cycle per tap: 35 of the 128 clocks
    localparam int NTERM = 6;
    logic [5:0] step;
    logic       busy;
    wire [2:0]  tap  = step[5:3];        // step = {tap, term}, 8 slots per tap
    wire [2:0]  term = step[2:0];
    wire        last = (term == 3'd6);  // finalise slot

    always_ff @(posedge clk_fs) begin
        if (!rst_b) begin
            step <= 6'd0;
            busy <= 1'b0;
        end else if (ce) begin
            step <= 6'd0;
            busy <= 1'b1;
        end else if (busy) begin
            if (step == 6'd38) busy <= 1'b0;
            else if (term == 3'd6) step <= {tap + 3'd1, 3'd0};
            else                    step <= step + 6'd1;
        end
    end

    // shift and sign of the current term, and the tap's own scale
    logic [3:0] sh_term;
    logic       neg;
    logic [4:0] sh_tap;
    always_comb begin
        sh_term = 4'd0; neg = 1'b0;
        case (tap)
            3'd0: begin sh_tap = 5'd18;
                case (term)
                    3'd0: begin sh_term = 4'd15; neg = 1'b0; end
                    3'd1: begin sh_term = 4'd12; neg = 1'b1; end
                    3'd2: begin sh_term = 4'd8;  neg = 1'b0; end
                    3'd3: begin sh_term = 4'd6;  neg = 1'b0; end
                    3'd4: begin sh_term = 4'd2;  neg = 1'b0; end
                    default: begin sh_term = 4'd0; neg = 1'b0; end
                endcase end
            3'd1: begin sh_tap = 5'd13;
                case (term)
                    3'd0: begin sh_term = 4'd13; neg = 1'b1; end
                    3'd1: begin sh_term = 4'd11; neg = 1'b0; end
                    3'd2: begin sh_term = 4'd7;  neg = 1'b1; end
                    3'd3: begin sh_term = 4'd5;  neg = 1'b0; end
                    3'd4: begin sh_term = 4'd2;  neg = 1'b1; end
                    default: begin sh_term = 4'd0; neg = 1'b0; end
                endcase end
            3'd2: begin sh_tap = 5'd14;
                case (term)
                    3'd0: begin sh_term = 4'd15; neg = 1'b0; end
                    3'd1: begin sh_term = 4'd13; neg = 1'b0; end
                    3'd2: begin sh_term = 4'd12; neg = 1'b0; end
                    3'd3: begin sh_term = 4'd8;  neg = 1'b1; end
                    3'd4: begin sh_term = 4'd4;  neg = 1'b0; end
                    default: begin sh_term = 4'd0; neg = 1'b1; end
                endcase end
            3'd3: begin sh_tap = 5'd8;
                case (term)
                    3'd0: begin sh_term = 4'd11; neg = 1'b1; end
                    3'd1: begin sh_term = 4'd9;  neg = 1'b0; end
                    3'd2: begin sh_term = 4'd7;  neg = 1'b1; end
                    3'd3: begin sh_term = 4'd5;  neg = 1'b0; end
                    3'd4: begin sh_term = 4'd3;  neg = 1'b1; end
                    default: begin sh_term = 4'd0; neg = 1'b0; end
                endcase end
            default: begin sh_tap = 5'd8;
                case (term)
                    3'd0: begin sh_term = 4'd11; neg = 1'b0; end
                    3'd1: begin sh_term = 4'd9;  neg = 1'b0; end
                    3'd2: begin sh_term = 4'd6;  neg = 1'b1; end
                    3'd3: begin sh_term = 4'd5;  neg = 1'b1; end
                    3'd4: begin sh_term = 4'd2;  neg = 1'b0; end
                    default: begin sh_term = 4'd0; neg = 1'b1; end
                endcase end
        endcase
    end

    // one shifter, one accumulator
    wire signed [WP-1:0]    op    = s[tap[2:0]];
    wire signed [ACC_W-1:0] opx   = {{(ACC_W-WP){op[WP-1]}}, op};
    wire signed [ACC_W-1:0] shft  = opx <<< sh_term;
    wire signed [ACC_W-1:0] addend = neg ? -shft : shft;

    logic signed [ACC_W-1:0] acc;
    logic signed [WP-1:0]    out_acc;

    // round at the tap's own scale, exactly as the parallel multipliers did
    wire signed [ACC_W-1:0] rnd = acc + (1 <<< (sh_tap - 1));
    /* verilator lint_off UNUSEDSIGNAL */
    wire signed [ACC_W-1:0] prd = rnd >>> sh_tap;
    /* verilator lint_on UNUSEDSIGNAL */

    always_ff @(posedge clk_fs) begin
        if (!rst_b) begin
            acc     <= '0;
            out_acc <= '0;
        end else if (ce) begin
            acc     <= '0;
            out_acc <= '0;
        end else if (busy) begin
            if (last) begin
                out_acc <= out_acc + prd[WP-1:0];
                acc     <= '0;
            end else begin
                acc <= acc + addend;
            end
        end
    end

    // Held between passes, so the consumer sees a stable word. Latched with the
    // last product included, not before it.
    logic signed [WP-1:0] result;
    always_ff @(posedge clk_fs) begin
        if (!rst_b)                     result <= '0;
        else if (busy && step == 6'd38) result <= out_acc + prd[WP-1:0];
    end

    assign data_out = result[W-1:0];
endmodule
