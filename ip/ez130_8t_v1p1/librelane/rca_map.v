// SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Description: Map $add / $sub onto EZ130's FAX1 and HAX2 ripple-carry cells
//
// abc's standard-cell mapper only ever uses SINGLE-OUTPUT cells, so FAX1 and
// HAX2, which each carry CO and S, can never be reached from the liberty. Left
// alone, the adders come out of abc as majority plus xor: measured on
// dco_switch_cap_decoder, 9 MIN3X1 + 6 MIN3X2 and 64 XOR2X1/XNOR2X*.
//
// Of LibreLane's three adder hooks only SYNTH_RCA_MAP runs early enough to
// bite. SYNTH_FA_MAP is applied AFTER librelane_synth, that is after abc, and
// the generic techmap inside that call has already turned $alu into $fa into
// gates by then, so it matches nothing. SYNTH_RCA_MAP and SYNTH_CSA_MAP are
// applied to the $add / $sub operators before any of it. Read off
// librelane/scripts/pyosys/synthesize.py lines 377-381 against 421-424 in
// image 96bdc869118a.
//
// The cells are known here because LibreLane adds CELL_VERILOG_MODELS as
// blackboxes before it reads the design.

(* techmap_celltype = "$add" *)
module _ez130_rca_add (A, B, Y);
    parameter A_SIGNED = 0;
    parameter B_SIGNED = 0;
    parameter A_WIDTH  = 1;
    parameter B_WIDTH  = 1;
    parameter Y_WIDTH  = 1;

    input  [A_WIDTH-1:0] A;
    input  [B_WIDTH-1:0] B;
    output [Y_WIDTH-1:0] Y;

    // A one-bit add has no carry to ripple; leave it to the generic mapping
    // rather than spending a cell and a dangling CO on it.
    wire _TECHMAP_FAIL_ = Y_WIDTH < 2;

    wire [Y_WIDTH-1:0] a, b;
    wire [Y_WIDTH-1:0] carry;

    \$pos #(.A_SIGNED(A_SIGNED), .A_WIDTH(A_WIDTH), .Y_WIDTH(Y_WIDTH))
        a_ext (.A(A), .Y(a));
    \$pos #(.A_SIGNED(B_SIGNED), .A_WIDTH(B_WIDTH), .Y_WIDTH(Y_WIDTH))
        b_ext (.A(B), .Y(b));

    // bit 0 has no carry in, so it is a half adder
    HAX2 bit0 (.A(a[0]), .B(b[0]), .S(Y[0]), .CO(carry[0]));

    genvar i;
    generate
        for (i = 1; i < Y_WIDTH; i = i + 1) begin : chain
            FAX1 fa (.A(a[i]), .B(b[i]), .CI(carry[i - 1]),
                     .S(Y[i]), .CO(carry[i]));
        end
    endgenerate
endmodule

(* techmap_celltype = "$sub" *)
module _ez130_rca_sub (A, B, Y);
    parameter A_SIGNED = 0;
    parameter B_SIGNED = 0;
    parameter A_WIDTH  = 1;
    parameter B_WIDTH  = 1;
    parameter Y_WIDTH  = 1;

    input  [A_WIDTH-1:0] A;
    input  [B_WIDTH-1:0] B;
    output [Y_WIDTH-1:0] Y;

    wire _TECHMAP_FAIL_ = Y_WIDTH < 2;

    wire [Y_WIDTH-1:0] a, b;
    wire [Y_WIDTH-1:0] carry;

    \$pos #(.A_SIGNED(A_SIGNED), .A_WIDTH(A_WIDTH), .Y_WIDTH(Y_WIDTH))
        a_ext (.A(A), .Y(a));
    \$pos #(.A_SIGNED(B_SIGNED), .A_WIDTH(B_WIDTH), .Y_WIDTH(Y_WIDTH))
        b_ext (.A(B), .Y(b));

    // a - b = a + ~b + 1, so bit 0 is a full adder with its carry in tied high
    // and there is no half adder in a subtractor.
    wire [Y_WIDTH-1:0] bn = ~b;

    FAX1 bit0 (.A(a[0]), .B(bn[0]), .CI(1'b1), .S(Y[0]), .CO(carry[0]));

    genvar i;
    generate
        for (i = 1; i < Y_WIDTH; i = i + 1) begin : chain
            FAX1 fa (.A(a[i]), .B(bn[i]), .CI(carry[i - 1]),
                     .S(Y[i]), .CO(carry[i]));
        end
    endgenerate
endmodule
