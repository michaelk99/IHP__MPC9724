// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1

// No signal ports, the flow fills the rows with DECAPHV cells.
// Yosys stops on an empty module, and global routing stops on a design with no net.
// A kept tie cell driving a kept inverter with a floating output gives it one net.
module decap_vdda;
    wire hi;
    (* keep *) TIEHI u_tie (.Y(hi));
    (* keep *) INVX1 u_inv (.A(hi), .Y());
endmodule
