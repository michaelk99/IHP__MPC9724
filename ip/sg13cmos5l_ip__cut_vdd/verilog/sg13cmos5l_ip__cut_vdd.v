// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// sg13cmos5l_ip__cut_vdd: vdd band cut: an IO ring cell that carries iovss, iovdd and vss but no vdd band
`timescale 1ns/10ps
`celldefine
(* blackbox *)
module sg13cmos5l_ip__cut_vdd (vss, iovdd, iovss);
	inout vss;
	inout iovdd;
	inout iovss;
endmodule
`endcelldefine
