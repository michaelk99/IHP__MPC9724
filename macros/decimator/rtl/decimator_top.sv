// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Michael Koefinger
// 2026-09-16
// ============================================================================
// CIC(N=6, D=32) + sinc2^9 + sinc2^16 + compensator FIR (v5)
// ----------------------------------------------------------------------------
// v4 decimates by 256 to 256 Hz while the band is 128 Hz, so its band edge sits
// at f_dec/2 and its worst alias is -6.3 dB. Protecting 128 Hz needs an output
// above 2*fb, and once the rate is free the alias is set by the CIC alone: the
// image at fs/D - fb folds to fb at the CIC output rate, so every half-band
// sits at 0.0 dB there. This chain therefore has no half-band at all. See
// SKILLS/dsm-decimation-architecture and system-level/matlab/dec_v5_*.
//
//   65536 Hz --CIC/32--> 2048 --sinc2^9--> 1024 --sinc2^16--> 512 --comp--> 512
//
// Measured on the modulator bitstream: alias -141.1 dB at the binding image
// (simulated, matches the analysis to 0.0 dB), in-band noise -130.4 dBFS
// against v4's -128.0, passband deviation 0.047 dB, tone level as v4.
//
// Word widths come from the bit-true model's measured node peaks, not from a
// growth bound: the datapath carries F = 4 fraction bits below the output LSB
// and each sinc section rounds one bit, which keeps every word at W = 26.
//
// Same pinout as v4 so dsa1_dig_top swaps versions by choosing a file set.
// SystemVerilog-2012, no default_nettype (ModelSim friendly), Genus safe: no
// dynamic index on the left-hand side of any state write.
// ============================================================================

`timescale 1ns / 1ps

// ============================================================================
// Top wrapper, pinout identical to v4
// ============================================================================
// data_out is two's complement but declared unsigned: OpenROAD's Verilog reader
// rejects `signed` on a top-level port.
module decimator_top (
    input  wire        clk_fs,
    input  wire        rst_b,
    input  wire        data_in,
    output wire [21:0] data_out,
    output wire        valid_strobe
);
    localparam int DATA_W = 22;
    wire signed [DATA_W-1:0] data_in_wide = {{(2){~data_in}}, {(DATA_W-2){data_in}}};

    decimator_core #(
        .DATA_W (DATA_W),
        .CIC_W  (32),
        .W      (27),
        .ALIGN_W(6),
        .RND_W  (4)
    ) u_dec (
        .clk_fs      (clk_fs),
        .rst_b       (rst_b),
        .data_in     (data_in_wide),
        .data_out    (data_out),
        .valid_strobe(valid_strobe)
    );
endmodule
