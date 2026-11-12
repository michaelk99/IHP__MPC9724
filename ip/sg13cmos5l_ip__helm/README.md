# sg13cmos5l_ip__helm

Chip art: a knight's helmet, 100 x 100 um on `Metal4` with `NoMetFiller`, in the lower-right die corner of the IHP SG13CMOS5L chip. `script/make_helm_png.py` turns the photo `logo/helm_source.jpg` into the 1-bit `logo/helm.png` (400 x 400 px, black is metal), and `make all` draws it at 0.25 um per pixel.

## Files

- `Makefile`: the build.
- `logo/helm_source.jpg`: the source photo, `logo/helm.png`: the 1-bit image, `logo/README.md`: copyright of the pictures.
- `script/make_helm_png.py`: photo to 1-bit image.
- `script/img2lay.py`: PNG to GDS.
- `final/gds/`, `final/lef/`, `final/lib/`, `final/vh/`: the generated GDS, LEF, Liberty stub and Verilog blackbox stub.
- `verification/drc/`: the DRC reports.

## Usage

`make` prints the targets. `make all` cleans, generates the logo GDS, LEF, Liberty and Verilog stubs and runs DRC.

### PDK Guard

Every target except `help` and `clean` needs the `ihp-sg13cmos5l` PDK, but the container starts with `ihp-sg13g2`. `img2lay.py` resolves `LAYER` through the active PDK's layer properties and `sak-drc.sh` uses its rule deck, so the Makefile compares `$PDK` against `REQUIRED_PDK` at parse time, before any target runs:

```bash
$ make all
Makefile:21: *** PDK is "ihp-sg13g2", but this IP needs "ihp-sg13cmos5l". Run `sak-pdk ihp-sg13cmos5l` in this shell and retry, or pass REQUIRED_PDK= to skip this check.  Stop.
```

Switch with `sak-pdk ihp-sg13cmos5l`, pass `REQUIRED_PDK=` to skip the check, or `REQUIRED_PDK=<pdk>` to require a different PDK.

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
| `PIXEL_SIZE`  | `0.25`   | Pixel size in µm (must be ≥ 0.21 µm, the Metal4 minimum space, single pixels and single-pixel gaps are drawn as is) |
| `LAYER`       | `Metal4` | Metal layer the logo is drawn on, one of `Metal1`..`Metal4` or `TopMetal1`            |

`LAYER` sets both the GDS artwork (`img2lay.py` resolves it through the PDK's KLayout layer properties, `Metal4` is `50/0`) and the LEF `OBS`, so the two agree. The image is scaled to `BLOCK_SIZE`, so the GDS boundary and the LEF `SIZE` agree too.

```sh
make all LAYER=TopMetal1
```

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

Both flows run `sak-drc.sh` on the GDS in `final/gds/` and write per-cell run folders: `verification/drc/<CELL>.magic.drc/` and `verification/drc/<CELL>.klayout.drc/` (`.lyrdb`). KLayout runs at `DRC_LEVEL` `precheck`, `macro` (default) or `regular`.

```sh
make klayout-drc
make klayout-drc CELL=sg13cmos5l_ip__helm
make klayout-drc DRC_LEVEL=regular
make magic-drc
make magic-drc CELL=sg13cmos5l_ip__helm
```
