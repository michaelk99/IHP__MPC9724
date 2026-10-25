// SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Description: yosys latch techmap onto EZ130 8T

module \$_DLATCH_P_ (input E, input D, output Q);
  LATQX1 _TECHMAP_DLATCH_P (.D(D), .Q(Q), .CK(E));
endmodule

module \$_DLATCH_N_ (input E, input D, output Q);
  LATNQX1 _TECHMAP_DLATCH_N (.D(D), .Q(Q), .CK(E));
endmodule

module \$_DLATCH_PN0_ (input E, input R, input D, output Q);
  LATRX1 _TECHMAP_DLATCH_PN0 (.D(D), .Q(Q), .QB(), .CK(E), .RB(R));
endmodule

module \$_DLATCH_NN0_ (input E, input R, input D, output Q);
  LATNRX1 _TECHMAP_DLATCH_NN0 (.D(D), .Q(Q), .QB(), .CK(E), .RB(R));
endmodule
