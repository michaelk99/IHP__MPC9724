// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// sg13cmos5l_ip__clamp_vddvss: RC-triggered vdd-to-vss ESD clamp, an IO ring cell without a bondpad
`timescale 1ns/10ps
`celldefine
(* blackbox *)
module sg13cmos5l_ip__clamp_vddvss (vdd, vss, iovdd, iovss);
	inout vdd;
	inout vss;
	inout iovdd;
	inout iovss;
endmodule
`endcelldefine
