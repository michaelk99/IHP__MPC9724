// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Techmap for clockgate_pre.ys: synchronous reset into logic, enable kept.
// $sdffe (reset overrides enable): EN = en | rst, so the gate opens for the reset. $sdffce (reset only while enabled): EN = en.
// yosys dffunmap -srst-only drops the enable of a $sdffe as well, which leaves nothing to gate.

module \$sdffe (CLK, SRST, EN, D, Q);
    parameter WIDTH = 0;
    parameter CLK_POLARITY = 1'b1;
    parameter EN_POLARITY = 1'b1;
    parameter SRST_POLARITY = 1'b1;
    parameter SRST_VALUE = 0;
    input CLK, SRST, EN;
    input [WIDTH-1:0] D;
    output [WIDTH-1:0] Q;
    wire rst = SRST_POLARITY ? SRST : ~SRST;
    wire en = EN_POLARITY ? EN : ~EN;
    \$dffe #(.WIDTH(WIDTH), .CLK_POLARITY(CLK_POLARITY), .EN_POLARITY(1'b1)) _TECHMAP_REPLACE_ (
        .CLK(CLK), .EN(en | rst), .D(rst ? SRST_VALUE[WIDTH-1:0] : D), .Q(Q));
endmodule

module \$sdffce (CLK, SRST, EN, D, Q);
    parameter WIDTH = 0;
    parameter CLK_POLARITY = 1'b1;
    parameter EN_POLARITY = 1'b1;
    parameter SRST_POLARITY = 1'b1;
    parameter SRST_VALUE = 0;
    input CLK, SRST, EN;
    input [WIDTH-1:0] D;
    output [WIDTH-1:0] Q;
    wire rst = SRST_POLARITY ? SRST : ~SRST;
    wire en = EN_POLARITY ? EN : ~EN;
    \$dffe #(.WIDTH(WIDTH), .CLK_POLARITY(CLK_POLARITY), .EN_POLARITY(1'b1)) _TECHMAP_REPLACE_ (
        .CLK(CLK), .EN(en), .D(rst ? SRST_VALUE[WIDTH-1:0] : D), .Q(Q));
endmodule
