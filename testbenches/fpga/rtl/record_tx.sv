// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// One record is 63 bits sent as nine bytes of 7 payload bits, most significant
// first. Only the first byte has bit 7 set, so a host that joins the stream
// late finds the next frame start without any escaping.

`timescale 1ns / 1ps

module record_tx #(
    parameter int CLK_HZ = 25_000_000,
    parameter int BAUD   = 115_200
)(
    input  wire        clk,
    input  wire        rst_b,
    input  wire [62:0] payload,
    input  wire        valid,        // taken when ready
    output logic       ready,
    output logic       tx
);
    logic [62:0] buf_q;
    logic [3:0]  left;               // bytes still to send
    logic        u_ready;

    assign ready = (left == 4'd0);

    always_ff @(posedge clk) begin
        if (!rst_b) begin
            buf_q <= '0;
            left  <= '0;
        end else if (left == 4'd0) begin
            if (valid) begin
                buf_q <= payload;
                left  <= 4'd9;
            end
        end else if (u_ready) begin
            buf_q <= {buf_q[55:0], 7'b0};
            left  <= left - 4'd1;
        end
    end

    uart_tx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) u_uart (
        .clk  (clk),
        .rst_b(rst_b),
        .data ({left == 4'd9, buf_q[62:56]}),
        .valid(left != 4'd0),
        .ready(u_ready),
        .tx   (tx)
    );
endmodule
