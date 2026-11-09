# Powered Verilog

`MPC9724.pnl.v` is the hardened netlist of the chip with its power pins, top module `MPC9724`. The IO cells, the macros and `dsm2_core` are instances of cells that this file does not define, as in the SPICE next to it. It is not a transistor-level netlist.

The copy of this file that the LVS used, with the wells tied, VSS and IOVSS joined and the IO cells' `vss` pin dropped, is in [../lvs_reference/](../lvs_reference/README.md).
