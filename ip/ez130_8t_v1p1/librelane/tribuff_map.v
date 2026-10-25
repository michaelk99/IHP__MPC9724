// SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Description: yosys tristate-buffer techmap onto EZ130 8T
//
// TBUFX1's enable is active high (the PDK's ebufn_2 is active low), so this
// map needs no inverter on E.

module \$_TBUF_ (input A, input E, output Y);
  TBUFX1 _TECHMAP_TBUF_ (.A(A), .Y(Y), .E(E));
endmodule
