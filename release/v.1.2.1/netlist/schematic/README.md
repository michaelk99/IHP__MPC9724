# Schematic

There is no schematic netlist of the chip in this release. The chip top is not drawn as transistors.

`schematic/xschem/sg13cmos5l_dsa1_dig_top.sch` in the repository is a drawing of the pad ring and the blocks, generated from the pad plan. It is not an LVS input. An earlier file here, `MPC9724_klayout.cdl`, came from the template's export of that drawing, was stale and has been removed.

The netlists that the layout was compared against are in [../lvs_reference/](../lvs_reference/README.md), with the list of what is transformed and why.
