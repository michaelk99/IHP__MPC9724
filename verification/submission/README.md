# Submission record of the exact release file

Checks on `release/v.1.2.1/gds/MPC9724.gds.gz` itself, the file IHP received, run on 2026-11-07 after IHP's audit (issue 81 of the Open-Silicon-MPW repo). Nothing here changes a GDS.

## Inputs

| file | md5 |
|---|---|
| `release/v.1.2.1/gds/MPC9724.gds.gz`, top cell `MPC9724` | `7cf6da0e6ea7b6c2c473bff6e6093cd7` |
| `layout/sg13cmos5l_dsa1_dig_top_logo_fill.gds.gz`, the source, top cell `sg13cmos5l_dsa1_dig_top_logo_fill` | `fb4d07f6471df30a646b7ba8c4a1c9b0` |
| `netlist/pnl/sg13cmos5l_dsa1_dig_top.pnl.v` | `5090e0487a732bfe1e83c381e33201f0` |
| `macros/dsa1_dig/final/pnl/dsa1_dig_top.pnl.v` | `a10dfe3c68cabcd28b69c51fd3d1e2e1` |
| `macros/decap_vdda/final/pnl/decap_vdda.pnl.v` | `8b3399d63e224eac0a1e160794ec8e4c` |
| `ip/ez130_8t_v1p1/cdl/ez130_8t.cdl` | `8c219c9a076dd731a599651ba3cc377a` |
| `ip/ez130_8t_decap_hv/cdl/ez130_8t_decap_hv.cdl` | `a750ceb264c8bac2e76377586d7e7126` |
| `ip/dsm2_core/cdl/dsm2_core.cdl` | `5df9700351cb3b2c1804480eb62dfc12` |
| `ip/sg13cmos5l_ip__clamp_vddvss/cdl/sg13cmos5l_ip__clamp_vddvss.cdl` | `14371a38079a0b59e1042cf0884dd188` |
| `ip/sg13cmos5l_ip__cut_vdd/cdl/sg13cmos5l_ip__cut_vdd.cdl` | `d5bcaca0ee952ad21e22aa60323e6f70` |
| `verification/lvs/top_lvs.sh` | `1e946654213277e45a4585d451dba194` |
| `verification/lvs/top_lvs_extract.tcl` | `7c333c5ab4a2019c34f1b27c6683590c` |
| `verification/lvs/top_lvs.tcl` | `c0f96f6dfa6b63947e6df5bc308d569c` |
| `verification/lvs/top_lvs_setup.tcl` | `106f6b8761f2a8fdc34a40c33a80f883` |
| `verification/lvs/cdl_magic.py` | `f9a9b51dfea8e0ec820d527d250de41b` |
| `verification/lvs/verilog_tie_wells.py` | `a5f45a63d1af0bad32041d5a517c9116` |
| `verification/lvs/verilog_drop_pin.py` | `bec150138c970840643c6bed81901129` |
| PDK `libs.ref/sg13cmos5l_io/spice/sg13cmos5l_io.spice`, from the image | `c0c109bf7f688aad0f50c815f5869374` |

## Image

The pinned sign-off image of `scripts/image.env`, `registry.iic.jku.at:5000/iic-osic-tools@sha256:65771d5c6be66df4f8a7522421355b53964ce643dc4cc612b605f645063b1af4`, PDK `ihp-sg13cmos5l` `5eddf3e96c4b1a42bffe90dd58daa6089a77fc23`, KLayout 0.30.12 (`precheck_run.log`), Magic 8.3.684 (`verification/signoff_env_v1.2.1.txt`). Every command ran in a throwaway container with the environment of `doc/running.md`, repo mounted at `/foss/designs`.

## Results

| check | command | result | wall | files |
|---|---|---|---|---|
| IHP precheck deck | `python3 $PDKPATH/libs.tech/klayout/tech/drc/run_drc.py --path=release/v.1.2.1/gds/MPC9724.gds.gz --topcell=MPC9724 --run_dir=<dir> --precheck_drc --no_offgrid --no_angle --disable_extra_rules --no_recommended` | 0 markers in 72 rule categories of the lyrdb, "KLayout DRC Check Passed". The density run is in range | 3 min 31 s (211.15 s in `precheck_run.log`) | `precheck_verdict.txt`, `precheck.lyrdb`, `precheck_main.redacted.log`, `precheck_density.redacted.log`, `precheck_run.log` |
| Top LVS on this file | `LVS_CELL=MPC9724 LVS_OUT=<dir> verification/lvs/top_lvs.sh release/v.1.2.1/gds/MPC9724.gds.gz` | `Circuits match uniquely`, no property error, the script's PASS line. The script takes the cell from `LVS_CELL` as it is, so the script is unchanged | not kept | `lvs_verdict.txt`, `lvs.rpt` |
| XOR against the source | `klayout -b -r verification/submission/xor.py -rd A=layout/sg13cmos5l_dsa1_dig_top_logo_fill.gds.gz -rd B=release/v.1.2.1/gds/MPC9724.gds.gz -rd OUT=<txt>` | the two top cells mapped to each other, 0 differing polygons on all 59 layers | not kept | `xor.txt` (per layer), `xor.py` |

| Element compare against the source | `python3 verification/submission/gds_compare.py layout/sg13cmos5l_dsa1_dig_top_logo_fill.gds.gz release/v.1.2.1/gds/MPC9724.gds.gz sg13cmos5l_dsa1_dig_top_logo_fill MPC9724` | 295 structures and 2951 texts in each, the same cell names, and per cell the same elements (boundaries, paths, references, texts with their layers, coordinates and strings) once the top name is mapped. Only the element order inside a cell differs | | `gds_compare.txt`, `gds_compare.py` |

The XOR compares polygons only. The element compare covers texts, cell names and references too, so together they show the release file is the source with the top cell renamed and nothing else changed.

`precheck_verdict.txt` and `lvs_verdict.txt` are one-line summaries written by hand from `precheck.lyrdb`, `precheck_run.log` and `lvs.rpt`, not lines the tools printed.

`precheck_main.redacted.log` and `precheck_density.redacted.log` are the deck's two logs with the run directory in line 5 replaced by `<run_dir>`, nothing else changed. The originals named a local work path and stay out of the tree.

The lyrdb has 72 `<category>` tags and 0 `<item>`. The earlier record's 73 counted `<name>` tags, which include the one `<cell><name>`, so it is the same 72. `scripts/submission.sh` now counts `<category>`.

`xor.py` was changed after the run: it asserts one top cell per file and reads each file once. The rerun on 2026-11-08 gives the same `xor.txt`.

The reference the LVS compared against is kept in `release/v.1.2.1/netlist/lvs_reference/`, from this same run. The Magic extraction dumps and the netgen log (17 MB) are not kept. The run directories were deleted.
