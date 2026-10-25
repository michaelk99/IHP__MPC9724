// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// 8N1 UART transmitter. tx is a flop output, so it cannot glitch.

`timescale 1ns / 1ps

module uart_tx #(
    parameter int CLK_HZ = 25_000_000,
    parameter int BAUD   = 115_200
)(
    input  wire       clk,
    input  wire       rst_b,
    input  wire [7:0] data,
    input  wire       valid,        // taken when ready
    output logic      ready,
    output logic      tx
);
    localparam int DIV = (CLK_HZ + BAUD / 2) / BAUD;

    logic [$clog2(DIV)-1:0] div_cnt;
    logic [3:0]             bit_cnt;     // bits still on the line, 0 when idle
    logic [9:0]             shreg;       // stop, data LSB first, start

    assign ready = (bit_cnt == 4'd0);
    assign tx    = shreg[0];

    always_ff @(posedge clk) begin
        if (!rst_b) begin
            shreg   <= '1;
            bit_cnt <= '0;
            div_cnt <= '0;
        end else if (bit_cnt == 4'd0) begin
            if (valid) begin
                shreg   <= {1'b1, data, 1'b0};
                bit_cnt <= 4'd10;
                div_cnt <= '0;
            end
        end else if (div_cnt == DIV - 1) begin
            div_cnt <= '0;
            shreg   <= {1'b1, shreg[9:1]};
            bit_cnt <= bit_cnt - 4'd1;
        end else begin
            div_cnt <= div_cnt + 1'b1;
        end
    end
endmodule
