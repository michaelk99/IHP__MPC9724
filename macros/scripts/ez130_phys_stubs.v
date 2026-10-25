// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Empty models for the EZ130 cells that ship LEF-only, so a gate-level netlist elaborates.
// The fillers and the well tap have no logic function and no Verilog view in the library.
// DECAP* are not here: the library's own ez130_8t.v declares them.

module FILLER1 (); endmodule
module FILLER2 (); endmodule
module FILLER4 (); endmodule
module FILLER8 (); endmodule
module FILLER16 (); endmodule
module WELLTAP (); endmodule

// Thick-oxide decoupling from ../../ip/ez130_8t_decap_hv. Physical-only like the
// fillers: LEF, GDS and CDL but no Verilog, so a gate-level run needs these.
module DECAPHV8 (); endmodule
module DECAPHV16 (); endmodule
module DECAPHV32 (); endmodule
