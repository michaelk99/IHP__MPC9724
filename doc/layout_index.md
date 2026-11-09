# Layout index for IHP's `MPC9724-main/` structure

IHP's template expects the design sources under `MPC9724-main/` and the proposals in `doc/ihp-structure-proposals/`. This repository keeps the layout of the AMS chip template it grew from, with the sources at the root. This is a documented layout exception, nothing is duplicated. The table maps each expected item to our path.

| expected | here |
|---|---|
| `dependencies/` | `ip/` (EZ130 cells, `dsm2_core`, the clamp, cut and bondpad cells, the IO snapshot), versions in `doc/info.json`, `verification/signoff_env_v1.2.1.txt` and `verification/signoff_env.txt` |
| `doc/` (Datasheet, Specification, TRL, `info.json`) | `doc/Datasheet.md` (links and key numbers), `doc/specifications.md`, `doc/TRL-Mixed-Signal-IP.md`, `doc/info.json`, and `doc/signoff.md` for the records |
| `MPC9724-main/layout/` (GDS) | `layout/` (unfilled and filled chip GDS), `macros/dsa1_dig/final/gds/` and `ip/dsm2_core/gds/` |
| `MPC9724-main/layout/lef/`, `def/` | `macros/dsa1_dig/final/lef/`, `ip/dsm2_core/lef/`, the chip DEF is not tracked, `make build-top` writes it to `flow/final/def/` |
| `MPC9724-main/model/` | `models/` (bit-true decimator model), `ip/dsm2_core/verilog/` (black box and bench model), `ip/dsm2_core/spice/` (dsm2 schematic and extracted netlists) |
| `MPC9724-main/netlist/` | `netlist/` (powered Verilog, SPICE), `macros/dsa1_dig/final/nl/` and `pnl/`, `release/v.1.2.1/netlist/` (with the LVS reference in `lvs_reference/`) |
| `MPC9724-main/schematic/xschem/` | `schematic/xschem/` (the chip top drawing, generated, not an LVS input), `ip/dsm2_core/schematic/` (the dsm2 block schematics, 11 sheets) |
| `MPC9724-main/testbenches/` | `testbenches/` (cocotb, FPGA master, start-up bench), `macros/*/testbenches/`, `ip/dsm2_core/spice/smoke_*.spice` |
| `MPC9724-main/verification/drc/`, `lvs/` | `verification/drc/`, `verification/lvs/`, `verification/submission/` (checks on the release file itself), `verification/reports/` (STA, antenna, IR drop), `verification/esd/`, `verification/em/` |
| `MPC9724-main/README.md` | the root `README.md` |
| `measurements/` | none yet, the chip is not back from the fab |
| `release/v.1.2.1/` | `release/v.1.2.1/` (`gds/`, `netlist/`, `doc/`, `img/`, `packaging/`, `README.md`, `ReleaseNote.md`) |
