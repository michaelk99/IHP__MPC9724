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
| Top LVS on this file | `LVS_CELL=MPC9724 LVS_OUT=<dir> verification/lvs/top_lvs.sh release/v.1.2.1/gds/MPC9724.gds.gz` | `Circuits match uniquely`, no property error, the script's PASS line. The script, unchanged, takes the cell from `LVS_CELL` | not kept | `lvs_verdict.txt`, `lvs.rpt` |
| XOR against the source | `klayout -b -r verification/submission/xor.py -rd A=layout/sg13cmos5l_dsa1_dig_top_logo_fill.gds.gz -rd B=release/v.1.2.1/gds/MPC9724.gds.gz -rd OUT=<txt>` | the two top cells mapped to each other, 0 differing polygons on all 59 layers | not kept | `xor.txt` (per layer), `xor.py` |
| Element compare against the source | `python3 verification/submission/gds_compare.py layout/sg13cmos5l_dsa1_dig_top_logo_fill.gds.gz release/v.1.2.1/gds/MPC9724.gds.gz sg13cmos5l_dsa1_dig_top_logo_fill MPC9724` | 295 structures and 2951 texts in each, the same cell names, and per cell the same elements (boundaries, paths, references, texts with layers, coordinates and strings) once the top name is mapped. Only the element order inside a cell differs | | `gds_compare.txt`, `gds_compare.py` |

The XOR compares polygons only. The element compare covers texts, cell names and references too, so together they show the release file is the source with the top cell renamed and nothing else changed.

`precheck_verdict.txt` and `lvs_verdict.txt` are one-line summaries written by hand from `precheck.lyrdb`, `precheck_run.log` and `lvs.rpt`, not lines the tools printed.

`precheck_main.redacted.log` and `precheck_density.redacted.log` are the deck's two logs with the local run directory in line 5 replaced by `<run_dir>`, nothing else changed.

The lyrdb has 72 `<category>` tags and 0 `<item>`. The earlier record's 73 counted `<name>` tags, which include the one `<cell><name>`, so it is the same 72. `scripts/submission.sh` now counts `<category>`.

`xor.py` was changed after the run (one top cell per file asserted, each file read once), and its rerun on 2026-11-08 gives the same `xor.txt`.

The reference the LVS compared against is kept in `release/v.1.2.1/netlist/lvs_reference/`, from this same run. The Magic extraction dumps, the netgen log (17 MB) and the run directories are not kept.

## Rerun in the official 2026.10 image, 2026-11-09

The pinned `IMAGE_AMD64` digest above no longer pulls from the JKU registry: `docker manifest inspect --insecure registry.iic.jku.at:5000/iic-osic-tools@sha256:65771d5c6be66df4f8a7522421355b53964ce643dc4cc612b605f645063b1af4` answered `no such manifest` on 2026-11-09, while the same call on the `IMAGE_ARM64` digest returned its index. So the same checks ran again in the public Docker Hub image `hpretl/iic-osic-tools:2026.10`, index digest `sha256:306585de35d198e70ea58950f77147c86f56c698726a19afea9f1c83009557be`, its arm64 manifest `sha256:4091b82d77a63e61ff29f4f6de9fd5f00935ae5163c3144d373f6443f7af01c1` (image id `sha256:cb3f3ec87e17d550c7112c880e053b06c8c4e53a8466992a6006426498c54820`), PDK `ihp-sg13cmos5l` `a49358cc0b20635fcb53c0940505e3563763fc7a`, KLayout 0.30.12, Magic 8.3.685, Netgen 1.5.324. Only the arm64 image ran, not the index's amd64 manifest `sha256:9201d2ebe74a406cf6af850ca2c646ac0462f3b2cea94cd98cb6580d8ceef800`. It ran on the ARM64 compute host at commit `bd6439d` with the commands of the table above and the environment of `scripts/in_image.sh`, one throwaway container per check, 6 CPUs (`--cpus 6`, the container saw 128 cores). Files are in `official_2026.10/`.

| check | result against the first run | wall |
|---|---|---|
| IHP precheck deck | `precheck.lyrdb` byte-identical, 0 markers in 72 rule categories, "KLayout DRC Check Passed". This PDK names the mode `--minimum_drc` and accepts `--precheck_drc` with a deprecation warning | 152 s |
| Top LVS | `lvs.rpt` byte-identical (md5 `c3d04b55d23005771108e9a7be81ddd7`), `Circuits match uniquely`, the script's PASS line in `lvs_run.txt` | 320 s |
| XOR against the source | `xor.txt` byte-identical, 0 on all 59 layers | 41 s |
| Element compare | `gds_compare.txt` byte-identical | 15 s, container start to end |

`image.txt` holds the image id, digests, creation date, commit and the md5s of the two GDS files, `signoff_env.txt` the tool versions, `precheck_run.txt`, `lvs_run.txt` and `xor_run.txt` the logs with times, and `steps.txt` the start and end of each container. Its `rc` field is the exit code of `date`, not of the container, so the result files are the evidence. Log paths are container paths.
