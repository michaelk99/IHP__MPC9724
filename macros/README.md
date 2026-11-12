# Macros

Every folder here is one macro with its own `Makefile` and `README.md`. Five macros: `dsa1_dig` and `decap_vdda` are on the die, `decimator` is the filter hardened alone for its numbers, `counter` and `inverter` are the two template archetypes a new block starts from. The top-level [`Makefile`](../Makefile) builds all but `decap_vdda` with `make build-<macro>` and cleans them with `make clean-all`. `decap_vdda` is rebuilt by hand, see [its README](decap_vdda/README.md). The archetypes:

| Macro | Kind | Source of truth | Flow |
| --- | --- | --- | --- |
| [`counter/`](counter/) | digital | SystemVerilog in `rtl/` | Verilator lint, Icarus Verilog and cocotb simulation, LibreLane hardening with DRC and LVS inside the run, XSPICE model for the mixed-signal Xschem simulation, FPGA emulation on three boards |
| [`inverter/`](inverter/) | analog | Xschem schematic and hand-drawn GDS in `layout/` | Four Xschem testbenches, KLayout and Magic DRC and LVS, Magic PEX, LEF, Liberty and Verilog stub export by Magic, CACE characterization |

The `Makefile` in this folder only starts a new macro as a renamed copy of an existing one.


## Directory Structure

```text
📁 macros/
├─ 📁 counter/                template archetype, digital: a counter with LibreLane and FPGA flows
├─ 📁 decap_vdda/             decoupling block for the 1.5 V VDDA supply, north of dsm2
├─ 📁 decimator/              the 128x decimation filter hardened on its own, not on the die
├─ 📁 dsa1_dig/               the DSADC1 digital back end: decimation filter, SPI slave, register file
├─ 📁 inverter/               template archetype, analog: an inverter with Xschem, DRC, LVS and PEX flows
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
$ make macro FROM=inverter NAME=amplifier
Makefile:18: *** PDK is "ihp-sg13g2", but the macros need "ihp-sg13cmos5l". Run `sak-pdk ihp-sg13cmos5l` in this shell and retry, or pass REQUIRED_PDK= to skip this check.  Stop.
```

Switch with `sak-pdk ihp-sg13cmos5l`, or pass `REQUIRED_PDK=` to skip the check.


### Start a New Macro from an Existing One

```sh
make macro FROM=<macro> NAME=<name>
```

`FROM` is the macro to copy: `inverter` for an analog block, `counter` for a digital one, or any other macro here. `NAME` is a lowercase letter followed by lowercase letters, digits or underscores, so it works as a file name, GDS cell name and Verilog module name. The top cell follows the copied macro: `NAME=amp` gives the cells `amp` and `amp_top` from the inverter, `NAME=fifo` the module `fifo_top` from the counter.

The target refuses to run when `NAME` exists. Otherwise it:

1. Copies every file of `FROM` that git knows about, tracked or untracked but not ignored, so LibreLane runs, `sim_build/`, `__pycache__/` and other ignored outputs stay behind. Outside a git checkout it copies the whole folder.
2. Runs `make clean` in the copy, which removes the committed build outputs (`final/`, `netlist/`, `render/img/`, the reports).
3. Renames every file and folder whose name carries `FROM`.
4. Replaces `FROM` in every text file in its three spellings `inverter`, `Inverter` and `INVERTER`. That covers `TOP` in the `Makefile` and every `fpga/<board>/Makefile`, `DESIGN_NAME` and `VERILOG_FILES` in `flow/librelane/config.yaml`, the symbol instances and `.include` lines in the Xschem testbenches, `name:`, `template:` and `script:` in the CACE yaml, the file names in the plot scripts, module names and include guards in the RTL, and `lib_name` and `lib_path` in the `.klib` library map.
5. Renames the cells inside every GDS in `layout/` with [`scripts/rename_gds_cells.py`](scripts/rename_gds_cells.py), because the DRC, LVS and PEX targets pass the file name as the cell name. It handles libraries before the layouts that use them and relinks every library reference of a `.klay.gds` to the renamed cell of the renamed library. It runs without the PDK, so the PCells stay frozen as saved. An XOR of every layer against the source, with the library maps resolved, is empty.
6. Lists what still carries the old name. Markdown files and notebooks are left alone on purpose, since they describe the copied design.

`make all` in the copy passes as in the source, since only names changed, so commit the copy before the real work starts.

```sh
cd macros
make macro FROM=inverter NAME=amp
make macro FROM=counter NAME=fifo
```

> [!NOTE]
> Runs in the IIC-OSIC-TOOLS container: it needs GNU `find`, `grep`, `sed` and `xargs`, and `klayout` for the GDS step.


### What Is Left to Do

The new macro still implements the copied design under its new name.

#### From the Inverter (Analog)

1. Replace the design: the schematics and symbols in `schematic/xschem/`, the layout sources `layout/<NAME>.gds` and `layout/<NAME>_top.klay.gds`, and the export `layout/<NAME>_top.gds`, see [Layout Sources and the Exported Tapeout GDS](inverter/README.md#layout-sources-and-the-exported-tapeout-gds). Keep the box on the `prBoundary` layer (`189/0`) around the top cell and resize it with the macro, `make check-boundary` verifies it.
2. Rewrite the testbenches in `testbenches/xschem/` and the plot scripts in `testbenches/xschem/plot_simulations/` for the new pins and measurements. `make symbol-pex` rebuilds `<CELL>_pex.sym` from the cell symbol, so only the cell symbol needs drawing.
3. Adapt the CACE datasheet `verification/cace/<NAME>.yaml` with its template and script, or delete the CACE folder together with the `sim-cace` line of `sim-all`.
4. Adapt or delete the sizing notebook `scripts/sizing/sizing_<NAME>.ipynb` and its figures.
5. Rewrite `README.md` and `render/blender/README.md`.

#### From the Counter (Digital)

1. Replace the RTL in `rtl/` and adjust `MODULES_SYNTH` and `MODULES_SIM` in the `Makefile` when you add or drop files. `rtl/constants.sv` keeps its name, its macros were renamed with the rest.
2. When the ports change, delete both symbols in `schematic/xschem/` instead of editing them, since `make symbol-check` rejects every pin that no longer matches a port. Harden once, scaffold the symbol from the hardened ports, arrange it, then run the full flow:

    ```sh
    make librelane        # harden the new design
    make copy-netlist     # brings netlist/pnl/<TOP>.pnl.v into the tree
    make symbol-gl        # scaffold schematic/xschem/<TOP>.sym from its ports
    xschem schematic/xschem/<TOP>.sym   # rename pins to house style, arrange, draw the body
    make all
    ```

    `make all` stops at `generate-xspice` when no symbol exists. Wire the Xschem testbench to the finished symbol afterwards, since it connects to the pins by coordinate. See [Build the Xschem Symbol](counter/README.md#build-the-xschem-symbol).
3. Update `CLOCK_PORT` and `DIE_AREA` in `flow/librelane/config.yaml`, the pin placement in `flow/librelane/pin_order.cfg`, and the constraints in `impl.sdc` and `signoff.sdc`.
4. Rewrite the testbenches in `testbenches/verilog/`, `testbenches/cocotb/` and `testbenches/xschem/`, and the plot script in `testbenches/xschem/plot_simulations/`.
5. Update `DUT_SRCS` in `fpga/dut.mk` and the pin constraint file in each `fpga/<board>/` you need. Delete the other board folders, the dispatcher takes its board list from the folders present. See [fpga/README.md](counter/fpga/README.md).
6. Rewrite `README.md`, `fpga/README.md` and `render/blender/README.md`.


### Register the Macro at the Chip Top-Level

There is no central macro list. Add a new macro in these places, relative to the repository root:

1. `Makefile`: a `build-<NAME>` target, its line in `build-macros`, and a `clean` line in `clean-all`.
2. `rtl/sg13cmos5l_dsa1_dig_core.sv`: instantiate the macro.
3. `flow/librelane/config.yaml`: a `MACROS` entry with the view paths (`dir::../../macros/<NAME>/final/...`) and the instance placement. An analog macro's placement snaps to the routing grid, see [doc/floorplan.md](../doc/floorplan.md).
4. `flow/librelane/pdn_cfg.tcl`: a `define_pdn_grid -macro` block when the macro's power pins are not on the layers of the default grid, see the `inverter_top` blocks at the end of the file.
5. `schematic/xschem/xschemrc`: a `source` line for the macro's `xschemrc`, else its symbols do not resolve at the chip top-level.
6. `schematic/xschem/sg13cmos5l_dsa1_dig_top.sch`: place the macro's symbol.
7. `testbenches/cocotb/sg13cmos5l_dsa1_dig_top_tb.py`: the `sources` list names the netlist or RTL and the stub of every macro.
8. The documentation: [doc/floorplan.md](../doc/floorplan.md), [doc/specifications.md](../doc/specifications.md), [doc/pinout.md](../doc/pinout.md) when pins change, and the top-level `README.md`.

`.gitignore` and `REUSE.toml` need no line, their `macros/*/` patterns cover every macro. Add the macro to git before `reuse lint`, otherwise the lint lists the build outputs of the untracked folder.
