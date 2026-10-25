# Top-Level LVS

`top_lvs.sh` is the tapeout gate: the chip extracted from its GDS by Magic and compared by netgen, with the macro and every standard cell compared device by device.

```
verification/lvs/top_lvs.sh                  inside IIC-OSIC-TOOLS, at the repo root, the AGENTS.md environment set
klayout -b -r verification/lvs/fill_isolation.py
```

## Why a second LVS

LibreLane's own LVS (`verification/reports/lvs.netgen.rpt`) runs with `MAGIC_EXT_USE_GDS` false. Magic then builds the chip from the DEF with every cell as a LEF abstract, so the macro is compared by its pins only and no standard cell by its transistors, and netgen runs with `-blackbox`. That check compares the router's connectivity, not the GDS that goes to the foundry.

## What top_lvs.sh compares

- **Layout**: `layout/sg13cmos5l_dsa1_dig_top.gds.gz`, read by Magic in GDS mode (`top_lvs_extract.tcl`). It runs in about 3 minutes and netgen in about 6.
- **Reference**: the chip's and the macro's powered Verilog netlists (`netlist/pnl/`, `macros/dsa1_dig/final/pnl/`) over the EZ130 CDL, the pinned image's IO SPICE `libs.ref/sg13cmos5l_io/spice/sg13cmos5l_io.spice`, the PDK the IO cell GDS comes from (the repo's snapshot `ip/sg13cmos5l_io_custom` is another PDK version, its LevelDown and clamp diodes differ, it feeds the flow's LEF and Verilog only), the clamp cell's and the cut cell's CDL, and `ip/dsm2_core/verilog/dsm2_core.v` (`top_lvs.tcl`). VDDA is its own net there, as in the layout.
- **Adjustments**, each for a fact of the inputs, not of the design. Each is in the script that makes it, with its reason:
  - The macro's GDS brings its own copy of every EZ130 cell, which the GDS merge renames `AND2X1$1`, so each `name$N` is equated with `name` (`top_lvs_setup.tcl`).
  - Magic writes each transistor and diode as a subcircuit call with positional pins, while the CDL uses M and D cards with named pins. netgen pads two such classes with proxy pins it cannot pair, so the CDL copies use X calls, as OpenBLAU's `cdl2spice.py` does (`top_lvs.sh`). The diodes' area and perimeter, which only the CDL gives, are not compared, because Magic expresses the same as w and l.
  - The EZ130 CDL gives every cell `VNW` and `VPW` pins, which the powered Verilog never connects. `verilog_tie_wells.py` ties them per instance to VDD and VSS. The layout's cells keep their wells as ports of their own, and each cell then matches its CDL with only those two pins renamed. A well region the taps do not reach would show up as a net that never meets VDD.
  - FILLER cells hold no device. Magic writes no instance of them, while the reference keeps each as a black box, because the EZ130 CDL has no FILLER subcircuit, so netgen ignores them.
  - The PDK's IO cells are black boxes compared by their pins, as in LibreLane's LVS: Magic extracts them from the GDS whatever `LEFview` says, and their clamps then disagree with the IO SPICE, the trigger resistor shorted for a missing PolyRes marker, which is the PDK's, not this design's. `top_lvs.sh` empties every cell the IO SPICE defines.
  - The two `cut_vdd` cells have no device and are compared by their pins, as is the dsm2 box, which stays a box until its layout arrives (`top_lvs_extract.tcl` keeps both abstract). The reference keeps their `vss` pin, which they label themselves. Filler200 keeps its `vss` pin only when the extraction gives it one.
  - The bondpad and the logos hold no device and are ignored. The bondpad's GDS carries no label, so Magic gives it no port, and its overlap with the IO cell's pad joins nothing. That overlap is geometry, which DRC and the bond plan check.
  - VSS, IOVSS and the IO cells' core ground `vss` all tap the one substrate, which Magic extracts as one implicit node. The reference joins IOVSS into VSS and drops the IO cells' `vss` pin, except on `Filler200`, whose rail reaches a label. A metal short between VSS and IOVSS is then invisible here, and LibreLane's LVS, which keeps them apart and passes, covers it.
- **Negative controls**: `top_lvs_mutants.sh` edits the reference copy and requires the compare to fail, then runs the clean compare again. The mutants are in `mutate_reference.py`: VDDA joined to VDD, the inverted input `AB` and the input `B` of the first AND3BX1 in the macro swapped (counts stay equal under that swap, so only the graph compare can catch it), the `iovdd` pin of a cut cell moved to VDD, and two of dsm2's inputs swapped.

## Why the unfilled GDS is enough

`top_lvs.sh` reads the delivery GDS minus its fill. `fill_isolation.py` shows on the delivery GDS itself that the fill (datatype 22) joins no two drawn shapes of a layer, touches no via, and crosses no drawn active or poly. A Metal4 fill tile that touches one drawn net only lengthens it. The fill's poly sits on fill active by design, a floating dummy. A mutant with one die-wide Metal3 fill rectangle and one fill poly across drawn active fails it. The record is `fill_isolation.txt`.

The geometric link between the files is an XOR, `macro in delivery GDS = macros/dsa1_dig/final/gds`, `layout/sg13cmos5l_dsa1_dig_top.gds.gz = the chip run's final GDS`, and `filled = unfilled + fill on x/22 + one boundary shape on 189/0`, recorded in `doc/signoff.md`.

## Files

| file | tracked | what |
|---|---|---|
| `top_lvs.sh`, `top_lvs_extract.tcl`, `top_lvs.tcl`, `top_lvs_setup.tcl`, `verilog_tie_wells.py`, `verilog_drop_pin.py`, `fill_isolation.py` | yes | the check |
| `top_lvs_mutants.sh`, `mutate_reference.py` | yes | the negative controls |
| `fill_isolation.txt` | yes | the fill record |
| `sg13cmos5l_dsa1_dig_top.gds.lvs/lvs.rpt`, `input.md5` | yes | the netgen report and the md5 of the GDS it read |
| `sg13cmos5l_dsa1_dig_top.gds.lvs/` everything else | no | the extraction, the reference copies and the netgen log |
