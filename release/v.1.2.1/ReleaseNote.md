# MPC9724 v.1.2.1

IHP SG13CMOS5L multi project die, 1300 x 1300 um: the DSA1 digital back end (128x decimation filter, SPI slave, register file) and the dsm2_core delta-sigma modulator on its own VDDA segment.

| | |
|---|---|
| GDS | `gds/MPC9724.gds.gz`, top cell `MPC9724` |
| md5 of the GDS | `7cf6da0e6ea7b6c2c473bff6e6093cd7` |
| Process, PDK | SG13CMOS5L, `5eddf3e96c4b1a42bffe90dd58daa6089a77fc23` |
| Package | QFN24, 4 x 4 mm, 0.5 mm pitch, packaged by IHP |
| Saved with | IHP's KLayout options: GDS2, dbu 0.001, no PCell and library context, zero-length paths eliminated |
| Zero-area check | no zero-area polygon, no degenerate path, and no zero-width path (`scripts/scan_gds.py`, the last is stricter than IHP's check) |
| Netlists | the top is defined once as `MPC9724` in every view under `netlist/` except `lvs_reference/`. That reference keeps the design's top name `sg13cmos5l_dsa1_dig_top`, and the LVS maps the layout cell `MPC9724` onto it. Subcells keep their names |

The GDS is a copy of the project layout with the top cell renamed from `sg13cmos5l_dsa1_dig_top_logo_fill`, nothing else changed: XOR 0 on all 59 layers, and the same 295 cells, 2951 texts and per cell the same elements (`verification/submission/gds_compare.txt`). The source layout is the one recorded in doc/signoff.md (md5 fb4d07f6471df30a646b7ba8c4a1c9b0). Checks and known items are in `doc/signoff.md`. Metadata is in `doc/info.json`, maturity in `doc/TRL-Mixed-Signal-IP.md`.
