// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// dsm2_core: 1.5 V first-order DT delta-sigma modulator, a hard macro. Pin list agreed with the dsm2 design.
`timescale 1ns/10ps
`celldefine
(* blackbox *)
module dsm2_core (vdd, vss, vi, vcm, ibias_test, di_clk, di_ena, di_rst_b, di_trim, di_dith_en,
                  di_dith_amp, di_vcm_ext, di_btest_en, di_qout_en, do_q, do_q_b, do_q_dec);
	inout vdd;
	inout vss;
	inout vi;
	inout vcm;
	inout ibias_test;
	input di_clk;
	input di_ena;
	input di_rst_b;
	input [3:0] di_trim;
	input di_dith_en;
	input [1:0] di_dith_amp;
	input di_vcm_ext;
	input di_btest_en;
	input di_qout_en;
	output do_q;
	output do_q_b;
	output do_q_dec;
endmodule
`endcelldefine
