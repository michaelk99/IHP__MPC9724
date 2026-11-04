# @NAME@ @VERSION@

IHP SG13CMOS5L multi project die, 1300 x 1300 um: the DSA1 digital back end (128x decimation filter, SPI slave, register file) and the dsm2_core delta-sigma modulator on its own VDDA segment.

| | |
|---|---|
| GDS | `gds/@NAME@.gds.gz`, top cell `@NAME@` |
| md5 of the GDS | `@MD5@` |
| Process, PDK | SG13CMOS5L, `5eddf3e96c4b1a42bffe90dd58daa6089a77fc23` |
| Package | QFN24, 4 x 4 mm, 0.5 mm pitch, packaged by IHP |
| Saved with | IHP's KLayout options: GDS2, dbu 0.001, no PCell and library context, zero-length paths eliminated |
| Zero-area check | no zero-area polygon, no degenerate path, and no zero-width path (`scripts/scan_gds.py`, the last is stricter than IHP's check) |
| Netlists | the top is defined once as `@NAME@` in every file under `netlist/`, subcells keep their names |

The GDS is a copy of the project layout with the top cell renamed from `@SRCCELL@`, nothing else changed. @SIGNOFF@ Checks and known items are in `doc/signoff.md`. Metadata is in `doc/info.json`, maturity in `doc/TRL-Mixed-Signal-IP.md`.
