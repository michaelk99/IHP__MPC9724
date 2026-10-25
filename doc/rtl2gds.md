<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
Description: how RTL becomes GDS in this repository, and what is not obvious about it
-->

# RTL to GDS

How this chip is built, in the order it is built, and the parts that are not
obvious from a log. The template's own `README.md` covers the generic flow;
this covers what is specific here.

Everything runs inside IIC-OSIC-TOOLS. Nothing in this repository is built
outside the container.

## The shape of the thing

```
macros/decimator/rtl/*.sv ──┬─> macros/decimator  ── final/ ──> (not on the die)
                            │
macros/dsa1_dig/rtl/*.vhd ──┴─> macros/dsa1_dig   ── final/ ──> rtl/*_core.sv
                                                                      │
                                                                      v
                                                            flow/librelane ──> layout/*.gds.gz
```

One macro reaches the die: `dsa1_dig_top`. The `decimator` macro is the same
filter hardened alone, kept so its area, timing and leakage can be quoted for
the block by itself. The chip consumes only `macros/dsa1_dig/final/`.

## The cell library is not in this repository

EZ130 8T is a prerelease and does not ship here, nor do the thick-oxide
decoupling cells. Both are read in place from outside:

| Variable | Default | What it holds |
|---|---|---|
| `EZ130_DIR` | `~/projects/OpenBLAU/ip/ez130_8t_v1p1` | tech LEF, cell LEF, GDS, CDL, Verilog models, three liberties |
| `DECAPHV_DIR` | `~/projects/OpenBLAU/ip/ez130_8t_decap_hv` | `DECAPHV8/16/32` views and liberties |

`make check-ez130` fails loudly when either is wrong, and every `librelane`
target depends on it.

LibreLane resolves `dir::` against the design directory, so a path outside the
repository cannot be written in a checked-in config at all. Two generators
produce fragments with absolute paths into `runs/` instead, and both go on the
command line **in this order**:

```sh
librelane $(EZ130_SCL) $(DECAP_FRAG) flow/librelane/config.yaml ...
```

- `EZ130_SCL` comes from the library's own `scripts/librelane_scl.py`.
- `DECAP_FRAG` comes from `macros/scripts/decaphv_frag.py`.

The order matters and is not cosmetic. The SCL fragment sets `LIB` to EZ130's
three corners; the decap fragment rewrites `LIB` with both liberties per
corner, because a later file **replaces** that key rather than merging into
it. The design config comes last so its own keys win.

**`STD_CELL_LIBRARY` is deliberately not set to `ez130_8t`.** Every step
re-reads the PDK config under that name and dies on a name the CMOS5L PDK does
not have. The consequence is that a `librelane` invocation without the SCL
fragment silently hardens on `sg13cmos5l_stdcell` instead, which is why the
Makefile never invokes it without one.

## Two things the flow needs before synthesis

**The clock-gate pre-pass.** yosys `clockgate` skips any flop whose
synchronous reset overrides its enable, which is every register in this
design. LibreLane runs `clockgate` inside its synthesis step with no hook
before it, so `make rtl-gen` does the work first: `techmap` rewrites the
synchronous reset into logic, `opt_merge` shares the resulting enable across a
group, and `clockgate` puts a `CGX3` in front of each group of three or more.
LibreLane then synthesises `rtl_gen/*_cg.v`, not the RTL.

**GHDL, for `dsa1_dig` only.** LibreLane reads one language per run and that
macro's top is VHDL, so `rtl-gen` is two steps there: `ghdl synth` emits
Verilog with `decimator_top` left unbound, then the pre-pass clock-gates that
together with the decimator SystemVerilog.

## Order of operations

```sh
# per macro
make rtl-gen                 # pre-pass (and ghdl synth for dsa1_dig)
make build-top               # harden, collect views, reports, netlists, render
make sim-gl                  # gate level must equal RTL, sample for sample
make model-gate              # decimator only, both must equal the bit-true model
make check-netlist           # no cell that is wrong in silicon got in
macros/scripts/fill_macro.sh # metal fill, see below

# chip
make build-top               # pad ring, macro placement, PDN, route, logo and fill
make magic-drc CELL=sg13cmos5l_dsa1_dig_top_logo_fill
make klayout-drc-regular
make bondplan
```

`build-top` at chip level deliberately runs `librelane-nodrc`, because IHP's
`metal1_pin_offgrid` rule trips on the pad ring. Chip DRC is therefore a
separate step on the filled GDS, and **density and antenna are only checked by
the `regular` KLayout deck** — a green `precheck` says nothing about density.

## A hard macro has to carry its own metal fill

This is the least obvious part of the flow and it cost a day.

The chip-level fill step cannot place anything inside a hard macro. A macro
that leaves LibreLane sparse in some layer is therefore a permanent density
hole, and no amount of fill around it can compensate.

**The rule is a window, not a block.** `M<n>Fil.h` wants at least 25 % metal
plus filler over any 800 x 800 um area of the chip, and `M<n>Fil.k` at most
75 %. A 497 um macro is 38.6 % of one window, so the die around it carries the
rest and a macro below 25 % on its own is not in violation. What a macro cannot
do is drag a whole window under. Measured here: `dsa1_dig_top` came out at
**5.38 % Metal4** over its 497 um square and the die-centre window failed
`M4Fil.h` at 19.5 %. The area outside the macro would have had to reach 37.4 %
to carry the shortfall, and tightening the chip's fill to the rule minimum
bought only 2.75 points.

`macros/scripts/fill_macro.sh` fixes it at the source, and needs two tricks:

- **The PDK filler fills `EdgeSeal.holes`**, the area enclosed by the seal ring
  on layer `39/0`. A macro has none, so the filler runs, prints "Filling M1"
  through "Filling M4", and places nothing. The first attempt produced a
  byte-identical GDS. `seal_ring.py` wraps the macro in a temporary ring whose
  hole is its own bounding box and strips it again afterwards.
- **The fill region is inset 2 um from the macro edge.** Fill flush with the
  boundary lands inside the filler-to-metal spacing of chip routing running
  alongside, which the macro-level filler cannot see: 104 `M3Fil.c` and 13
  `M2Fil.c` edge pairs, gaps of 0.28 um, all at the macro edge.

TopMetal1 is deliberately left unfilled in a macro: the chip runs its
TopMetal1 power stripes across the block.

Result: Metal4 5.38 % to 52.35 %. Run `macros/scripts/report_density.py` on any
macro GDS to check a block before it goes on a die. It prints what the rest of
a window would have to carry, which is the number that decides the case.

### The verdict, from the chip's own density run

`make klayout-drc-regular` runs the PDK's density deck and writes a separate
log, `verification/drc/<top>.klayout.drc/*_density.log`. It is the only place
the densities are actually stated, and it reports **zero** `M<n>Fil.h` and
`M<n>Fil.k` window violations on the filled chip. Global, drawn metal only,
against `M<n>.j` and `M<n>.k`:

| Layer | Chip | Limits |
|---|---|---|
| Activ | 45.88 % | 35 to 55 |
| GatPoly | 19.91 % | min 15 |
| Metal1 | 53.87 % | 35 to 60 |
| Metal2 | 49.02 % | 35 to 60 |
| Metal3 | 52.68 % | 35 to 60 |
| Metal4 | 57.18 % | 35 to 60 |
| TopMetal1 | 47.19 % | 25 to 70 |
| LBE | 0.00 % | max 20 |

**The Metal4 fill distance is coupled to the chip logo, which is not obvious.**
The template's generic top-metal logo also wrote a `50/23` nofill rectangle
around itself, 800 x 540 um, which is 17 % of the die and kept the chip filler
out of Metal4 there. Switching the logo off removed that keep-out, the filler
moved in, and global Metal4 went from 57.15 % to 61.94 %, over the 60 %
maximum of `M4.k`. `FILL_DIST_M4` in `scripts/add_logo_fill.sh` went from 0.75
to 1.25 um to put it back at 57.18 %. Re-run the density deck after any change
to the logo, the fill distances or the floorplan: it is the only check that
sees this, and the main DRC report does not.

Metal2 and Metal3 inside the macro are 18.46 % and 16.57 %. The die around it
carries 52.3 % and 56.5 %, against the 29.1 % and 30.3 % the window arithmetic
asks for, so the margin is wide. Metal4 is the layer that was ever close.

Both macros are filled. `decimator_top` went from 27.4 / 11.3 / 8.6 / 4.4 % to
29.6 / 24.3 / 19.5 / 58.6 % on Metal1 to Metal4, and DRCs clean afterwards.

**Check the fill with DRC, and name the file after the top cell.** The macro
DRC level catches the boundary spacing the macro-level filler cannot see. One
trap in `sak-drc.sh`: it passes `topcell` derived from the **file name**, so a
GDS called `dec_filled.gds` holding cell `decimator_top` fails with a KLayout
traceback and "did not generate any result database", which reads like a deck
problem and is not one.

**A fresh LibreLane build resets this.** The fill lives in the GDS, so it has
to be reapplied after every re-harden, before the chip is rebuilt.

## Decoupling is thick-oxide only

EZ130's own thin-oxide `DECAP*` was 83.6 % of this block's leakage, measured at
transistor level. They are banned, in three places, because `DECAP_CELLS`
alone only steers the decap insertion step and leaves the cells legal for
anything else to place:

| Where | Effect |
|---|---|
| `DECAP_CELLS` | insertion uses `DECAPHV32/16/8` |
| `EXTRA_EXCLUDED_CELLS` | `DECAP4/8/16/32` out of synthesis and placement |
| `BANNED_CELLS` | `make check-netlist` fails the build if one appears |

Worth 7.136 uW to 1.157 uW at tt on `dsa1_dig`.

## Equivalence against the RTL

`make -C macros/dsa1_dig lec` proves the hardened netlist equal to the RTL with EQY, for every input sequence and not only the simulated ones.
Gold is ghdl's Verilog of the VHDL from before the clock-gate pre-pass, plus the decimator sources, read through yosys-slang. So the proof also covers the pre-pass, and a misparse by the yosys frontend synthesis used.
ghdl is on both sides, so the meaning of the VHDL stays `model-gate`'s to check.
The verdict and the netlist's sha256 go to `verification/lec_verdict.json`.
On 2026-10-01: 1325 of 1325 partitions proved, 2.4 h on 12 cores.
`make lec-fail`, gate output 3000 inverted (`_12607_`, an XNOR3X1 in the sinc2 chain), failed 23 partitions the clean run had proved.
EQY runs one solver per core and peaked at about 10 GB, so do not run it beside other heavy jobs.

`macros/scripts/lec.py` is vendored from iic-jku/OpenBLAU at 690a7c71. These changes were each forced by a failure on this macro:

- EQY ends a `/regex/` pattern at any slash, escaped or not, and yosys leaves source paths in net names. The slash is written as `\x2f`.
- `--gold` takes gold from the given files instead of the config's, here ghdl's output from before the pre-pass.
- A gate flop named after a gold net that gold does not register is no match point. Synthesis named a re-encoded FSM's one-hot bits after ghdl's decode wires (`n296 = state == 2'b01`), and matched by name they gave 9 false FAILs.
- slang reads gold with `--no-implicit-memories`, and `--array-maps` maps each gate flop `arr[i][j]` of an ascending unpacked array to gold `arr[(N-1-i)*W+j]`. Without it 1273 decimator flops had no match. An element's top bit that synthesis merged into the bit below it, two copies of the sign, maps onto that flop (`u_s1.sect[0][26]` and `[1][26]`).
- Gold's multi-bit flops are split to single bits. Synthesis dropped `cic_out[4:0]`, which the rounding add cannot carry out of, and as part of one 32-bit gold cell they had merged every reader of `cic_out` into one partition PDR did not finish.

LibreLane runs yosys 0.68's `arith_tree`, which miscompiles a narrow adder link into a wider sum (YosysHQ/yosys#6130, fixed in 0.69).
`equiv_opt -assert -async2sync arith_tree` on this macro's RTL proves the pass changed nothing here, 10539 of 10539, and the same recipe fails on the bug's three-line reproduction.

## Verdicts, and how to read them

| Check | Clean looks like |
|---|---|
| Router | `route__drc_errors` 0 in `final/metrics.json` |
| Magic DRC | `COUNT: 0` in the `.rpt` |
| KLayout DRC | item count over the `.lyrdb`, **not** the exit code |
| Netgen LVS | `Final result: Circuits match uniquely.` |
| `sim-gl` | the two output files are byte identical |
| `model-gate` | 500 of 500 samples match `models/decimator_model.py` |
| `lec` | `PASS` in `verification/lec_verdict.json`, every partition proved, and `lec-fail` failing |

The chip's regular KLayout deck reports **78 items that are not defects**: 40
`Pad.d1R` and 38 `Pad.fR_TM1`, recommended bondpad rules. Until the core rows
moved to EZ130, 2 `NW.d` items sat on the PDK's thin-oxide decap and filler
cells next to the macro's top corners. `klayout-drc-regular` returns non-zero whenever any item exists, so
its exit code is not the verdict.

Two numbers that are **not** verdicts:

- **`power__total`** from the flow is meaningless at 65 kHz. Real power needs
  `make power-vcd`, which annotates per-pin activity from a gate-level VCD.
- **Synthesis area** moves about 1 % on statement order alone, because the
  pre-pass emits its netlist in source order and ABC maps that differently.
  Splitting a file into one module per file, leaving every module body byte
  identical, moved it 1455 um2. Use `sim-gl` to prove a change, not the area.

## Traps that have already been hit here

- A stale instance name in `PDN_MACRO_CONNECTIONS` is caught at **Floorplan
  Init**, step 12 of 81, not at config load.
- `copy-reports` iterates corners. EZ130 has three, the template names six, and
  the target dies halfway through with a bare `cp: cannot stat`.
- `GPL_CELL_PADDING` and `DPL_CELL_PADDING` are **totals**. Both scripts halve
  them with Tcl integer arithmetic, so 1 silently becomes 0 per side.
- `scripts/fill_pdk_patched/` is a cache the fill step builds and deletes. A
  killed run leaves it behind and the next one dies on a file it just wrote.
  Delete the directory and rerun.
- Killing a `docker run` client does not stop the container. Orphans keep
  holding memory until they are removed.
- OpenSTA refuses a liberty that declares no thresholds, even one with no
  timing arc. The decap liberty has none; `decaphv_frag.py` injects them into a
  copy rather than editing the source, and skips the patch when the source
  already has them.
