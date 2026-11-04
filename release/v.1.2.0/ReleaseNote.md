# MPC9724 v.1.2.0

IHP SG13CMOS5L multi project die, 1300 x 1300 um: the DSA1 digital back end (128x decimation filter, SPI slave, register file) and the dsm2_core delta-sigma modulator on its own VDDA segment.

| | |
|---|---|
| GDS | `gds/MPC9724.gds.gz`, top cell `MPC9724` |
| md5 of the GDS | `76a2eec3f01e6683685c9e5533fa3d0b` |
| Process, PDK | SG13CMOS5L, `5eddf3e96c4b1a42bffe90dd58daa6089a77fc23` |
| Package | QFN24, 4 x 4 mm, 0.5 mm pitch, packaged by IHP |
| Saved with | IHP's KLayout options: GDS2, dbu 0.001, no PCell and library context, zero-length paths eliminated |
| Zero-area check | no zero-area polygon, no degenerate path, and no zero-width path (`scripts/scan_gds.py`, the last is stricter than IHP's check) |
| Netlists | the top is defined once as `MPC9724` in every file under `netlist/`, subcells keep their names |

The GDS is a copy of the project layout with the top cell renamed from `sg13cmos5l_dsa1_dig_top_logo_fill`, nothing else changed. The source layout is the one recorded in doc/signoff.md (md5 872f29b28253c9d28f666a7a5c80b096). Checks and known items are in `doc/signoff.md`. Metadata is in `doc/info.json`, maturity in `doc/TRL-Mixed-Signal-IP.md`.
