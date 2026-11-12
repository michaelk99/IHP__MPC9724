# sg13cmos5l_ip__bondpad_70x70

A 70 µm × 70 µm square bondpad for the IHP SG13CMOS5L 130 nm CMOS process, generated using the KLayout PCell engine and the `SG13_dev` library.

## Directory Structure

<details>
<summary>Show Directory Structure</summary>

```text
📁 sg13cmos5l_ip__bondpad_70x70/
├─ Makefile                             # Build automation
├─ 📁 script/
│  └─ bondpad.py                        # KLayout PCell-based bondpad generator
├─ 📁 final/
│  ├─ 📁 gds/
│  │  └─ sg13cmos5l_ip__bondpad_70x70.gds   # Generated GDSII layout
│  ├─ 📁 lef/
│  │  └─ sg13cmos5l_ip__bondpad_70x70.lef   # LEF macro for place-and-route
│  └─ 📁 vh/
│     └─ sg13cmos5l_ip__bondpad_70x70.vh    # Verilog blackbox stub
└─ 📁 verification/
   └─ 📁 drc/                           # DRC reports
```

</details>


## Usage

`make` (same as `make help`) prints all targets.

```bash
make help
```

Build everything (clean, generate bondpad, generate Verilog, run DRC):

```bash
make all
```

### PDK Guard

Every target except `help` and `clean` needs the `ihp-sg13cmos5l` PDK, because the `bondpad` target asks `$PDK_ROOT/$PDK` for the `sg13cmos5l` KLayout technology by name and `sak-drc.sh` uses the rule deck of `$PDK`. The container starts with `ihp-sg13g2`, so the Makefile checks `$PDK` against `REQUIRED_PDK` at parse time:

```bash
$ make all
Makefile:21: *** PDK is "ihp-sg13g2", but this IP needs "ihp-sg13cmos5l". Run `sak-pdk ihp-sg13cmos5l` in this shell and retry, or pass REQUIRED_PDK= to skip this check.  Stop.
```

Switch the PDK with `sak-pdk ihp-sg13cmos5l`, pass `REQUIRED_PDK=` to skip the check, or `REQUIRED_PDK=<pdk>` to require a different PDK.


### Individual Targets

| Target        | Description                                                                                                          |
| ------------- | -------------------------------------------------------------------------------------------------------------------- |
| `bondpad`     | Generate GDS and LEF via `bondpad.py` (usage: `make bondpad [DIAMETER=<um>] [SHAPE=<square\|octagon\|circle>] [BOTTOM_METAL=<1-4>]`) |
| `verilog`     | Generate Verilog blackbox stub (`inout pad`)                                                                         |
| `klayout-drc` | Run KLayout DRC using `sak-drc.sh` (usage: `make klayout-drc [CELL=<cellname>] [DRC_LEVEL=<precheck\|macro\|regular>]`) |
| `magic-drc`   | Run Magic DRC using `sak-drc.sh` (usage: `make magic-drc [CELL=<cellname>]`)                                         |
| `open`        | Browse this folder with `sak-open.py` and open each file in its tool                                |
| `clean`       | Remove all generated output directories                                                                              |

### Parameters

| Variable       | Default  | Description                                                                                |
| -------------- | -------- | ------------------------------------------------------------------------------------------ |
| `DIAMETER`     | `70.0`   | Bondpad diameter/side length in µm                                                         |
| `SHAPE`        | `square` | Bondpad shape (`square`/`octagon`/`circle`)                                                |
| `BOTTOM_METAL` | `3`      | Lowest metal in the pad stack (`1`=Metal1 .. `4`=Metal4). Top is fixed to TopMetal1. |

Example: generate an octagonal 70 µm bondpad starting at Metal2:

```bash
make bondpad DIAMETER=70.0 SHAPE=octagon BOTTOM_METAL=2
```

> **Note:** The SG13_dev `bondpad` PCell takes its bottom metal as the string choice `'1'..'4'` and fixes its top metal to TopMetal1. `bondpad.py` maps the integer `BOTTOM_METAL` to that choice and writes the matching `OBS` range into the LEF.


## Bondpad Generator Script

`script/bondpad.py` runs in KLayout batch mode. It:

1. Instantiates the `bondpad` PCell from the `SG13_dev` library
2. Flattens the PCell into a static layout
3. Exports the layout as GDSII
4. Generates a matching LEF file (with `pad` pin on Metal2–TopMetal1 and metal obstruction layers)

The pad stack covers `Metal3` through `TopMetal1` by default (`BOTTOM_METAL=3` in the Makefile, also the PCell's own default, `script/bondpad.py` run on its own defaults to 1).


## Design Rule Check (DRC)

Runs `sak-drc.sh` on `final/gds/`. Reports go to `verification/drc/<CELL>.klayout.drc/` (`.lyrdb`) and `verification/drc/<CELL>.magic.drc/`. `DRC_LEVEL` (`precheck`, `macro` [default], or `regular`) applies to KLayout only.

```sh
make klayout-drc
make klayout-drc CELL=sg13cmos5l_ip__bondpad_70x70
make klayout-drc DRC_LEVEL=regular
make magic-drc
make magic-drc CELL=sg13cmos5l_ip__bondpad_70x70
```
