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
// Clock enables
// ----------------------------------------------------------------------------
// ce_cic  : CIC comb and the sinc2^9 sections, 2048 Hz
// ce_s1   : sinc2^9 output and the sinc2^16 sections, 1024 Hz. The model keeps
//           the odd-indexed samples of each stage, which is cnt[5:0] == 32 here.
// ce_s2   : sinc2^16 output and the compensator, 512 Hz, odd index again.
// ============================================================================
module ce_generator (
    input  logic clk_fs,
    input  logic rst_b,
    output logic ce_cic,
    output logic ce_s1,
    output logic ce_s2
);
    logic [6:0] cnt;

    always_ff @(posedge clk_fs) begin
        if (!rst_b) cnt <= 7'd0;
        else        cnt <= cnt + 7'd1;
    end

    assign ce_cic = (cnt[4:0] == 5'd0);
    assign ce_s1  = (cnt[5:0] == 6'd32);
    assign ce_s2  = (cnt[6:0] == 7'd96);
endmodule
