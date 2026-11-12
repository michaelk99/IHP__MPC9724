# Top-Level LVS

`top_lvs.sh` is the tapeout gate: the chip extracted from its GDS by Magic and compared by netgen, with the macro and every standard cell compared device by device.

```
verification/lvs/top_lvs.sh                  inside IIC-OSIC-TOOLS, at the repo root, the environment of doc/running.md set
klayout -b -r verification/lvs/fill_isolation.py
```

## Why a second LVS

LibreLane's own LVS (`verification/reports/lvs.netgen.rpt`) runs with `MAGIC_EXT_USE_GDS` false: Magic builds the chip from the DEF with every cell as a LEF abstract and netgen runs with `-blackbox`, so the macro is compared by its pins only and no standard cell by its transistors. That checks the router's connectivity, not the GDS that goes to the foundry.

## What top_lvs.sh compares

- **Layout**: `layout/sg13cmos5l_dsa1_dig_top.gds.gz`, read by Magic in GDS mode (`top_lvs_extract.tcl`). It runs in about 3 minutes and netgen in about 6.
- **Reference**: the chip's and the macro's powered Verilog (`netlist/pnl/`, `macros/dsa1_dig/final/pnl/`) over the EZ130 CDL, the pinned image's IO SPICE `libs.ref/sg13cmos5l_io/spice/sg13cmos5l_io.spice` (the PDK the IO cell GDS comes from, the repo's snapshot `ip/sg13cmos5l_io_custom` is another PDK version with different LevelDown and clamp diodes and feeds only the flow's LEF and Verilog), the clamp and cut cell CDL, and dsm2's `ip/dsm2_core/cdl/dsm2_core.cdl` (`top_lvs.tcl`). VDDA is its own net there, as in the layout.
- **Adjustments**, each for a fact of the inputs, not of the design, and each explained in the script that makes it:
  - The macro's GDS brings its own copy of every EZ130 cell, which the GDS merge renames `AND2X1$1`, so each `name$N` is equated with `name` (`top_lvs_setup.tcl`).
  - Magic writes each transistor and diode as a subcircuit call with positional pins, the CDL uses M and D cards with named pins, and netgen pads the two classes with proxy pins it cannot pair. So the CDL copies use X calls, as OpenBLAU's `cdl2spice.py` does (`top_lvs.sh`). Diode area and perimeter are not compared, since only the CDL gives them and Magic expresses the same as w and l.
  - The EZ130 CDL gives every cell `VNW` and `VPW` pins that the powered Verilog never connects. `verilog_tie_wells.py` ties them per instance to VDD and VSS. The layout's cells keep their wells as their own ports, so each cell matches its CDL with only those two pins renamed. A well region the taps do not reach would show up as a net that never meets VDD.
  - FILLER cells hold no device. Magic writes no instance of them, the reference keeps each as a black box (the EZ130 CDL has no FILLER subcircuit), and netgen ignores them.
  - The PDK's IO cells are black boxes compared by their pins, as in LibreLane's LVS. Magic extracts them from the GDS whatever `LEFview` says, and their clamps then disagree with the IO SPICE (the trigger resistor shorted for a missing PolyRes marker, the PDK's issue, not this design's). `top_lvs.sh` empties every cell the IO SPICE copy defines.
  - The two `cut_vdd` cells have no device and are compared by their pins (`top_lvs_extract.tcl` keeps them abstract). The reference keeps their `vss` pin, which they label themselves. Filler200 keeps its `vss` pin only when the extraction gives it one.
  - dsm2 is compared device by device. `cdl_magic.py` writes its CDL the way Magic writes devices and drops what Magic does not extract: the 106 `cap_cmomf` MOM capacitors (metal fingers only, covered by dsm2's own KLayout LVS) and the `ptap1` substrate tie in `sg13cmos5l_SecondaryProtection`, whose two nodes are one in the layout. A subckt the reference already has is dropped from dsm2's copy when identical. Only an IO cell's may differ, then dsm2's stays and the IO SPICE copy loses it: `sg13cmos5l_SecondaryProtection`, where dsm2 has a fifth pin `sub` and the IO SPICE the global `sub!`. dsm2's CDL is read before the IO SPICE, so the black-boxed IO cells' calls of that cell only warn.
  - The bondpad and the logos hold no device and are ignored. The bondpad's GDS carries no label, so Magic gives it no port and its overlap with the IO cell's pad joins nothing. DRC and the bond plan check that overlap.
  - VSS, IOVSS and the IO cells' core ground `vss` all tap the one substrate, which Magic extracts as one implicit node. The reference joins IOVSS into VSS and drops the IO cells' `vss` pin, except on `Filler200`, whose rail reaches a label. A metal short between VSS and IOVSS is then invisible here, and LibreLane's LVS, which keeps them apart and passes, covers it.
- **Negative controls**: `top_lvs_mutants.sh` edits the reference copy and requires the compare to fail, then runs the clean compare again. The mutants are in `mutate_reference.py`: VDDA joined to VDD, the inverted input `AB` and the input `B` of the first AND3BX1 in the macro swapped (counts stay equal under that swap, so only the graph compare can catch it), the `iovdd` pin of a cut cell moved to VDD, two of dsm2's inputs swapped, and drain and gate of a transistor inside dsm2 swapped.

## Why the unfilled GDS is enough

`top_lvs.sh` reads the delivery GDS minus its fill. `fill_isolation.py` shows on the delivery GDS that the fill (datatype 22) joins no two drawn shapes of a layer, touches no via and crosses no drawn active or poly. A Metal4 fill tile that touches one drawn net only lengthens it. The nofill markers (datatype 23) do not count as drawn. Fill poly sits on fill active by design, a floating dummy. A mutant with one die-wide Metal3 fill rectangle and one fill poly across drawn active fails it. Record: `fill_isolation.txt`.

The geometric link between the files is an XOR, `macro in delivery GDS = macros/dsa1_dig/final/gds`, `layout/sg13cmos5l_dsa1_dig_top.gds.gz = the chip run's final GDS`, and `filled = unfilled + fill on x/22 + one boundary shape on 189/0`, recorded in `doc/signoff.md`.

## Files

| file | tracked | what |
|---|---|---|
| `top_lvs.sh`, `top_lvs_extract.tcl`, `top_lvs.tcl`, `top_lvs_setup.tcl`, `verilog_tie_wells.py`, `verilog_drop_pin.py`, `cdl_magic.py`, `fill_isolation.py` | yes | the check |
| `top_lvs_mutants.sh`, `mutate_reference.py` | yes | the negative controls |
| `fill_isolation.txt` | yes | the fill record |
| `sg13cmos5l_dsa1_dig_top.gds.lvs/lvs.rpt`, `input.md5` | yes | the netgen report and the md5 of the GDS it read |
| `sg13cmos5l_dsa1_dig_top.gds.lvs/` everything else | no | the extraction, the reference copies and the netgen log |
