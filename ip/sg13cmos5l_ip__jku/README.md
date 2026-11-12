# sg13cmos5l_ip__jku

A logo IP block for [Johannes Kepler University Linz](https://www.jku.at/), rendered as a GDSII layout on a configurable metal layer (default `Metal4`) with `NoMetFiller` for the IHP SG13CMOS5L 130 nm CMOS process.

## Directory Structure

<details>
<summary>Show Directory Structure</summary>

```text
📁 sg13cmos5l_ip__jku/
├─ Makefile                   # Build automation
├─ 📁 logo/
│  └─ jku_logo.png            # Source PNG image
├─ 📁 script/
│  └─ img2lay.py              # PNG-to-GDS converter
├─ 📁 final/
│  ├─ 📁 gds/
│  │  └─ sg13cmos5l_ip__jku.gds   # Generated GDSII layout
│  ├─ 📁 lef/
│  │  └─ sg13cmos5l_ip__jku.lef   # LEF macro for place-and-route
│  ├─ 📁 lib/
│  │  └─ sg13cmos5l_ip__jku.lib   # Liberty timing stub
│  └─ 📁 vh/
│     └─ sg13cmos5l_ip__jku.vh    # Verilog blackbox stub
└─ 📁 verification/
   └─ 📁 drc/                 # DRC reports
```

</details>


## Usage

`make` (same as `make help`) prints all targets.

```bash
make help
```

Build everything (clean, generate logo GDS, LEF, Liberty, Verilog stub, run DRC):

```bash
make all
```

### PDK Guard

Every target except `help` and `clean` needs the `ihp-sg13cmos5l` PDK, because `img2lay.py` resolves `LAYER` through the active PDK's layer properties and `sak-drc.sh` uses its rule deck. The container starts with `ihp-sg13g2`, so the Makefile checks `$PDK` against `REQUIRED_PDK` at parse time:

```bash
$ make all
Makefile:21: *** PDK is "ihp-sg13g2", but this IP needs "ihp-sg13cmos5l". Run `sak-pdk ihp-sg13cmos5l` in this shell and retry, or pass REQUIRED_PDK= to skip this check.  Stop.
```

Switch the PDK with `sak-pdk ihp-sg13cmos5l`, pass `REQUIRED_PDK=` to skip the check, or `REQUIRED_PDK=<pdk>` to require a different PDK.


### Individual Targets

| Target        | Description                                              |
|---------------|----------------------------------------------------------|
| `logo`        | Convert PNG to GDSII using `img2lay.py`                  |
| `lef`         | Generate LEF macro (CLASS BLOCK, OBS on `$(LAYER)`) |
| `lib`         | Generate Liberty timing stub (empty cell)                |
| `verilog`     | Generate Verilog blackbox stub (no ports)                |
| `klayout-drc` | Run KLayout DRC using `sak-drc.sh` (usage: `make klayout-drc [CELL=<cellname>] [DRC_LEVEL=<precheck\|macro\|regular>]`) |
| `magic-drc`   | Run Magic DRC using `sak-drc.sh` (usage: `make magic-drc [CELL=<cellname>]`)                                         |
| `open`        | Browse this folder with `sak-open.py` and open each file in its tool      |
| `clean`       | Remove all generated output directories                  |

### Parameters

| Variable      | Default  | Description                                                                           |
|---------------|----------|---------------------------------------------------------------------------------------|
| `BLOCK_SIZE`  | `100`    | Block edge in µm, the image is scaled to it                                           |
| `PIXEL_SIZE`  | `0.50`   | Pixel size in µm (must be ≥ 0.21 µm, the Metal4 minimum space, single pixels and single-pixel gaps are drawn as is) |
| `LAYER`       | `Metal4` | Metal layer the logo is drawn on, one of `Metal1`..`Metal4` or `TopMetal1`            |

`LAYER` sets both the GDS artwork (`logo`, resolved through the PDK's KLayout layer properties, `Metal4` is `50/0`) and the LEF `OBS` (`lef`).

```sh
make all LAYER=TopMetal1
```

The image is scaled to `BLOCK_SIZE`, so the GDS boundary and the LEF `SIZE` agree.


## Logo Generator Script

`script/img2lay.py` converts a PNG image into a GDSII layout:

- Each horizontal run of dark pixels becomes a rectangle on the layer selected via `LAYER` (default `Metal4`, resolved to `50/0`)
- Boundary layers `prBoundary` (189/0) and `NoMetFiller` (160/0) mark the block outline
- Layers are given as `<layer>/<datatype>` or as a drawing-layer name of the active PDK, read from `$PDK_ROOT/$PDK/libs.tech/klayout/tech/<pdk>.lyp`
- `--invert` inverts the image (dark ↔ light)
- `--merge` merges the rectangles into polygons to reduce the polygon count
- `--pixel-size` sets the physical size of each pixel in µm
- `--block-size` scales the image to the given block edge in µm and draws the boundary layers at that size
- `--scale` downscales the image by a plain factor instead


## Design Rule Check (DRC)

Runs `sak-drc.sh` on `final/gds/`. Reports go to `verification/drc/<CELL>.klayout.drc/` (`.lyrdb`) and `verification/drc/<CELL>.magic.drc/`. `DRC_LEVEL` (`precheck`, `macro` [default], or `regular`) applies to KLayout only.

```sh
make klayout-drc
make klayout-drc CELL=sg13cmos5l_ip__jku
make klayout-drc DRC_LEVEL=regular
make magic-drc
make magic-drc CELL=sg13cmos5l_ip__jku
```
