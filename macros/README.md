# Macros

Every folder here is one macro built in this repository, with its own `Makefile` and `README.md`. `dsa1_dig` and `decap_vdda` are on the die, `decimator` is the filter hardened alone for its numbers. The top-level [`Makefile`](../Makefile) builds all but `decap_vdda` with `make build-<macro>` and cleans them with `make clean-all`. `decap_vdda` is rebuilt by hand, see [its README](decap_vdda/README.md).

Blocks delivered as finished views, such as dsm2, live in [`ip/`](../ip/), for example [`ip/dsm2_core/`](../ip/dsm2_core/).

The `Makefile` in this folder only starts a new macro as a renamed copy of an existing one.


## Directory Structure

```text
📁 macros/
├─ 📁 decap_vdda/             decoupling block for the 1.5 V VDDA supply, north of dsm2
├─ 📁 decimator/              the 128x decimation filter hardened on its own, not on the die
├─ 📁 dsa1_dig/               the DSADC1 digital back end: decimation filter, SPI slave, register file
├─ 📁 scripts/                helpers shared by the macros and the chip Makefile
│  └─ rename_gds_cells.py     renames the cells inside a GDS, used by make macro
├─ Makefile
└─ README.md
```


## Makefile Targets

### Show Available Targets

```sh
make help
```


### PDK Guard

`make macro` needs the `ihp-sg13cmos5l` PDK, only `help` is exempt. The Makefile checks `$PDK` at parse time, as every macro and IP Makefile does:

```sh
$ make macro FROM=decimator NAME=fifo
Makefile:18: *** PDK is "ihp-sg13g2", but the macros need "ihp-sg13cmos5l". Run `sak-pdk ihp-sg13cmos5l` in this shell and retry, or pass REQUIRED_PDK= to skip this check.  Stop.
```

Switch with `sak-pdk ihp-sg13cmos5l`, or pass `REQUIRED_PDK=` to skip the check.


### Start a New Macro from an Existing One

```sh
make macro FROM=<macro> NAME=<name>
```

`FROM` is the macro to copy. `NAME` is a lowercase letter followed by lowercase letters, digits or underscores, so it works as a file name, GDS cell name and Verilog module name.

The target refuses to run when `NAME` exists. Otherwise it:

1. Copies every file of `FROM` that git knows about, tracked or untracked but not ignored, so LibreLane runs, `sim_build/`, `__pycache__/` and other ignored outputs stay behind. Outside a git checkout it copies the whole folder.
2. Runs `make clean` in the copy, which removes the committed build outputs (`final/`, `netlist/`, `render/img/`, the reports).
3. Renames every file and folder whose name carries `FROM`.
4. Replaces `FROM` in every text file in its three spellings, for example `decimator`, `Decimator` and `DECIMATOR`. That covers `TOP` in the `Makefile` and every `fpga/<board>/Makefile`, `DESIGN_NAME` in `flow/librelane/config.yaml`, the symbol instances and `.include` lines in the Xschem testbenches, the file names in the plot scripts, and the module names in the RTL.
5. Renames the cells inside every GDS in `layout/` with [`scripts/rename_gds_cells.py`](scripts/rename_gds_cells.py), because the DRC, LVS and PEX targets pass the file name as the cell name. It handles libraries before the layouts that use them and relinks every library reference of a `.klay.gds` to the renamed cell of the renamed library. It runs without the PDK, so the PCells stay frozen as saved. An XOR of every layer against the source, with the library maps resolved, is empty.
6. Lists what still carries the old name. Markdown files and notebooks are left alone on purpose, since they describe the copied design.

`make all` in the copy passes as in the source, since only names changed, so commit the copy before the real work starts.

```sh
cd macros
make macro FROM=decimator NAME=fifo
```

> [!NOTE]
> Runs in the IIC-OSIC-TOOLS container: it needs GNU `find`, `grep`, `sed` and `xargs`, and `klayout` for the GDS step.


### Register the Macro at the Chip Top-Level

There is no central macro list. Add a new macro in these places, relative to the repository root:

1. `Makefile`: a `build-<NAME>` target, its line in `build-macros`, and a `clean` line in `clean-all`.
2. `rtl/sg13cmos5l_dsa1_dig_core.sv`: instantiate the macro.
3. `flow/librelane/config.yaml`: a `MACROS` entry with the view paths (`dir::../../macros/<NAME>/final/...`) and the instance placement. An analog macro's placement snaps to the routing grid, see [doc/floorplan.md](../doc/floorplan.md).
4. `flow/librelane/pdn_cfg.tcl`: a `define_pdn_grid -macro` block when the macro's power pins are not on the layers of the default grid, see the `dsa1_dig` block.
5. `schematic/xschem/xschemrc`: a `source` line for the macro's `xschemrc`, else its symbols do not resolve at the chip top-level.
6. `schematic/xschem/sg13cmos5l_dsa1_dig_top.sch`: place the macro's symbol.
7. `testbenches/cocotb/sg13cmos5l_dsa1_dig_top_tb.py`: the `sources` list names the netlist or RTL and the stub of every macro.
8. The documentation: [doc/floorplan.md](../doc/floorplan.md), [doc/specifications.md](../doc/specifications.md), [doc/pinout.md](../doc/pinout.md) when pins change, and the top-level `README.md`.

`.gitignore` and `REUSE.toml` need no line, their `macros/*/` patterns cover every macro. Add the macro to git before `reuse lint`, otherwise the lint lists the build outputs of the untracked folder.
