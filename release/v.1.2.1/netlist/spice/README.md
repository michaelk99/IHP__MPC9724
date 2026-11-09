# SPICE

`MPC9724.spice` is the netlist of the chip top `MPC9724`, written from an extraction of the chip with every cell abstract (its first line names `sg13cmos5l_dsa1_dig_top.ext`). It holds black-box subcircuits only: the IO cells, the standard cells, the fill and decap cells, `dsa1_dig_top`, `decap_vdda` and `dsm2_core`, each as a `.subckt` with its pins and no devices. It is not a transistor-level netlist.

The device-by-device comparison is in [../lvs_reference/](../lvs_reference/README.md).
