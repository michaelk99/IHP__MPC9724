# LVS reference of MPC9724

The netlists the top LVS compared the layout against. They replace the CDL that was in `../schematic/`, which was a stale file of the template. The top LVS is a layout against these netlists, not against a drawn schematic.

Built on 2026-11-07 by `verification/lvs/top_lvs.sh` of this repository on the release GDS, and kept here from that run. The result of the run is in `verification/submission/lvs.rpt`: `Circuits match uniquely`, no property error. The inputs of every file and the image are in `verification/submission/README.md`.

```sh
LVS_CELL=MPC9724 LVS_OUT=<dir> verification/lvs/top_lvs.sh release/v.1.2.1/gds/MPC9724.gds.gz
```

The script extracts the layout with Magic (`verification/lvs/top_lvs_extract.tcl`), writes the files below into `<dir>` and compares with netgen (`verification/lvs/top_lvs.tcl`). The layout cell `MPC9724` is compared with the reference cell `sg13cmos5l_dsa1_dig_top`. So the reference keeps the design's top name `sg13cmos5l_dsa1_dig_top` and is not a view of the chip under the release top name `MPC9724`.

## Files

| file | md5 | what it is |
|---|---|---|
| `sg13cmos5l_dsa1_dig_top.pnl.v` | `5e386704c52ed5c8616ee232ac496a5c` | the chip's powered Verilog, transformed as below |
| `dsa1_dig_top.pnl.v` | `0189db3afc82f43a5f8bb53d6ea8d4c9` | the macro's powered Verilog, wells tied |
| `decap_vdda.pnl.v` | `37409f109ce5473ef0dd47668242b1c8` | the VDDA decap macro's powered Verilog, wells tied |
| `ez130_8t.cdl` | `c1c5caacd48ce00e7d9bae677cd0e968` | EZ130 standard cells, `M` and `D` cards renamed `X` |
| `ez130_8t_decap_hv.cdl` | `51154aec7ca503c92e1fe77c88bee24c` | the thick-oxide decap cells, same renaming |
| `sg13cmos5l_ip__clamp_vddvss.cdl` | `4dd55daa5ca1b87a35909eac204af53c` | the VDD to VSS clamp cell, device by device |
| `sg13cmos5l_ip__cut_vdd.cdl` | `d5bcaca0ee952ad21e22aa60323e6f70` | the VDD cut cell, compared by its pins |
| `dsm2_core.spice` | `0ab5472f917dfd5bf71a88a6f67270af` | dsm2's CDL as `verification/lvs/cdl_magic.py` writes it |
| `dsm2_different.txt` | `c951101c9839d3dab21caaa5b49384b7` | the subckt of dsm2 that differs from the reference cell of the same name |
| `sg13cmos5l_dsa1_dig_top.boxed.spice.gz` | `f00bfd7604b4619f4cc8d20d4b20da01`, `6f70dfe2704b7d4f6f40e3c00ebeb4f3` unzipped | the layout side: Magic's extraction of `MPC9724` with the IO cells, bondpad and logos emptied to black boxes |

The IO cells' SPICE is not copied. It is the PDK's `libs.ref/sg13cmos5l_io/spice/sg13cmos5l_io.spice` (md5 `c0c109bf7f688aad0f50c815f5869374`) in `ihp-sg13cmos5l` commit `5eddf3e96c4b1a42bffe90dd58daa6089a77fc23`, with the `vss` pin dropped from every cell but `Filler200` by the `awk` line of the script.

## What the script changes before comparing

- VSS and IOVSS are one net. Both tap the one substrate, which Magic extracts as one node, so the reference joins them. A metal short between them is invisible here. The DEF-level LibreLane LVS keeps them apart and passes (`verification/reports/lvs.netgen.rpt`).
- The IO cells' `vss` pin is dropped from the IO SPICE and from their instances in the chip Verilog, because Magic never makes it a port. Not dropped from `Filler200` when the extraction has the pin, the clamp cell or the cut cell.
- The IO cells, the bondpad and the logos are black boxes, compared by their pins as LibreLane's LVS does. Magic extracts the IO cells from the GDS and their clamps then disagree with the IO SPICE, which is the PDK's, not this design's.
- Wells are tied in the three Verilog files (`verilog_tie_wells.py`).
- `M` and `D` cards of the EZ130 CDLs become `X` calls, as Magic writes devices. The clamp cell's CDL also turns its `rppd` trigger into an `X` call with the substrate as third pin.
- 106 `cap_cmomf` and one `ptap1` are dropped from dsm2, because Magic does not extract them. dsm2's own KLayout LVS extracts the capacitors and ends "Netlists match" (`ip/dsm2_core/lvs/klayout_lvs.log`).
- A subckt that dsm2's CDL shares with the reference is dropped from dsm2's copy when it is the same. `sg13cmos5l_SecondaryProtection` differs, so dsm2's copy is kept and the IO SPICE copy loses it.
- 8 cells match "with port errors" in `verification/submission/lvs.rpt`, and netgen alters their pin lists to match before it compares the parents, so the top compare is unaffected. `top_lvs.sh` gates on the final line and on property errors only. `sg13cmos5l_SecondaryProtection`: the reference pin `minus` has no layout pin, it is left open once the `ptap1` that joined it to the substrate is dropped. `DECAPHV8`, `DECAPHV16`, `DECAPHV32`: the reference pin `VPW` has no layout node, the cells have no device in a p-well. `INVX4`, `INVX8`, `INVX14`: `VNW` and `VPW` against Magic's well node `w_n41_292#` and `sub`, the well renaming of `verification/lvs/README.md`. `sg13cmos5l_ip__clamp_vddvss`: four layout nodes, `m4_0_32440#`, `m5_0_25200#`, `m5_0_6900#` and `m5_0_18700#`, have no reference pin. They are clamp metal that connects to no device, so no device compare depends on them.
