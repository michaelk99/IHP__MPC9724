// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// dsm2_core for the chip cocotb bench only. Not the circuit: a PRBS15 bit stream on di_clk.
// do_q_dec is low while disabled, as dsm2's latch preset gives. The oscillator variant's clock runs at 0.8 MHz.
`timescale 1ns/10ps
module dsm2_core (vdd, vss, vi, vcm, ibias_test, di_clk, di_ena, di_rst_b, di_trim, di_dith_en,
                  di_dith_amp, di_vcm_ext, di_btest_en, di_qout_en, do_q, do_q_b, do_q_dec,
                  di_osc_en, di_clk_sel, do_clk_osc, do_osc_oe);
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
	input di_osc_en;
	input di_clk_sel;
	output do_clk_osc;
	output do_osc_oe;

	// di_clk_sel picks the oscillator as the modulator clock and enables the dsm_clk pad driver.
	// The ring runs only with di_ena: its current comes from a bias bank that is off without it.
	reg osc = 1'b0;
	always begin
		#625;
		osc = (di_osc_en && di_ena) ? ~osc : 1'b0;
	end
	assign do_clk_osc = osc;
	assign do_osc_oe  = di_clk_sel;
	wire mclk = di_clk_sel ? osc : di_clk;

	reg [14:0] lfsr = 15'd1;
	reg q = 1'b0;
	always @(posedge mclk) begin
		if (!di_rst_b) begin
			lfsr <= 15'd1;
			q <= #3 1'b0;
		end else begin
			q <= #3 lfsr[0];
			lfsr <= {lfsr[13:0], lfsr[14] ^ lfsr[13]};
		end
	end
	assign do_q_dec = di_ena ? q : 1'b0;
	assign do_q     = di_qout_en & di_ena & q;
	// do_q_b is high while di_ena is low, as dsm2's latch preset gives
	assign do_q_b   = di_qout_en & (di_ena ? ~q : 1'b1);
endmodule
