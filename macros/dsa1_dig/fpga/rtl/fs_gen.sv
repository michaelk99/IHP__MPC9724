// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// ============================================================================
// 65536 Hz from any board clock. The accumulator carries out at 2 * FS_HZ on
// average and a toggle flop halves that, so clk_fs has a 50 % duty cycle and
// an exact average rate. 25 MHz does not divide by 65536, so a plain counter
// would be 0.06 % off and a bit-true comparison would drift.
//
// fall is high for one clk cycle, the first one with clk_fs low. The master
// changes data_in there, half a period away from the DUT's sampling edge.
// ============================================================================

`timescale 1ns / 1ps

module fs_gen #(
    parameter int CLK_HZ = 25_000_000,
    parameter int FS_HZ  = 65_536,
    parameter int ACC_W  = 32
)(
    input  wire  clk,
    input  wire  rst_b,          // synchronous, active low
    output logic clk_fs,
    output logic fall
);
    localparam longint unsigned INC =
        (longint'(FS_HZ) * 2 * (longint'(1) << ACC_W)) / longint'(CLK_HZ);

    logic [ACC_W-1:0] acc;
    logic             carry;
    always_ff @(posedge clk) begin
        if (!rst_b) {carry, acc} <= '0;
        else        {carry, acc} <= {1'b0, acc} + INC[ACC_W:0];
    end

    always_ff @(posedge clk) begin
        if (!rst_b) begin
            clk_fs <= 1'b0;
            fall   <= 1'b0;
        end else begin
            fall <= carry & clk_fs;
            if (carry) clk_fs <= ~clk_fs;
        end
    end
endmodule
