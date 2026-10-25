<!--
SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
Description: What the EZ130 8T library needed to move from SG13G2 to SG13CMOS5L
-->

# EZ130 8T on SG13CMOS5L

ETH Zurich released EZ130 8T v1.1 against **SG13G2**. This copy is retargeted
to **SG13CMOS5L**. Only `lef/ez130_tech.lef` changed, plus a copy of each cell's
boundary onto 189/4 in the GDS (below); no device or pin was touched.

Image `hpretl/iic-osic-tools:latest` = `96bdc869118a`, PDK `ihp-sg13cmos5l`,
checked 2026-09-08.

## The stack delta is four things, and it is the PDK's own

Diffing the two PDK tech LEFs (`sg13g2_stdcell/lef/sg13g2_tech.lef` against
`sg13cmos5l_stdcell/lef/sg13cmos5l_tech.lef`) leaves nothing to interpret. Every
`LAYER` block the two share is byte-identical except one line. The whole
difference is:

| | SG13G2 | SG13CMOS5L |
|-----|----------|----------|
| routing layers | Metal1-Metal5, TopMetal1, TopMetal2 | **Metal1-Metal4, TopMetal1** |
| cut layers above `Cont` | Via1-Via4, TopVia1, TopVia2 | **Via1-Via3, TopVia1** |
| `TopVia1` lands on | Metal5 | **Metal4** |
| `TopMetal1` direction | VERTICAL | **HORIZONTAL** |

Metal1 to Metal4, Via1 to Via3, `Cont`, `TopVia1` and every TopMetal1 number
other than the direction (pitch, width, spacing, RC, density, antenna) are the
same on both. So this is a stack truncation plus one direction flip, not a
re-characterization.

## What was applied to `ez130_tech.lef`

1. Dropped `LAYER Metal5`, `Via4`, `TopMetal2`, `TopVia2`.
2. Dropped the 74 `Via4_*` fixed vias, `TopVia2EWNS`, `ViaRULE via4Array` and
   `ViaRULE viagen67`.
3. `TopVia1EWNS`: lower layer `Metal5` to `Metal4`. The enclosures were already
   the PDK's (0.31 on the metal, 0.75 on TopMetal1), so only the layer name moved.
4. `ViaRULE viagen56` renamed `viaTop1Array` and re-pointed `Metal5` to `Metal4`.
   **Its enclosures changed too, and that is a fix rather than a rename.** It
   carried `ENCLOSURE 0 0` on the lower metal, which `TV1.c` = 0.1 does not
   allow (`sg13cmos5l_tech_default.json`). It now carries the PDK's own
   `viaTop1Array` values, Metal4 0.1 and TopMetal1 0.42, which are exactly
   `TV1.c` and `TV1.d`. The new name is the PDK's, so a PDN config written
   against either tech LEF finds the rule; the old one said "5 to 6" in a file
   with no Metal5.
5. `TopMetal1` direction VERTICAL to HORIZONTAL.
6. `TopMetal1` `OFFSET` 0.0 to **1.68**. The offset is measured on the
   perpendicular axis, so flipping the direction restates it rather than
   preserving it: 0.0 put half of the first wire below y = 0. 1.68 is half the
   3.36 um pitch EZ130 chose, which centres one TopMetal1 track on each
   standard-cell row. The PDK uses the same half-pitch convention on this layer
   (`OFFSET 1.64` against `PITCH 3.28`).

Result, read back through OpenROAD (`read_lef` on both files): 15 layers,
225 vias, 4 generate rules, 220 cells, 1 site, no warning. The layer list is
identical to the PDK's `sg13cmos5l_tech.lef`, and the via stack is continuous:

```
Metal1->Metal2  76 fixed + via1Array
Metal2->Metal3  74 fixed + via2Array
Metal3->Metal4  74 fixed + via3Array
Metal4->TopMetal1  1 fixed + viaTop1Array
```

**EZ130's own track plan was left alone.** The uniform 0.42 um pitch, the
0.21 um Metal2/Metal4 offsets and the 3.36 um TopMetal1 pitch are the 8-track
row geometry, not the metal stack; the PDK's 0.48/0.42 pitches belong to its own
0.48 x 3.78 site. The one exception is the TopMetal1 offset above, which the
direction flip forced.

## What needed no change, and why that is worth knowing

- **The cells are Metal1-only.** `lef/ez130_8t.lef` names `Metal1` 2341 times
  and no other routing layer, and the GDS draws only Activ, GatPoly, Cont,
  NWell, pSD, Metal1 (8/0, 8/2, 8/25) plus label and boundary layers. There is
  no Via1 and no Metal2 anywhere in the library. The PDK's own
  `sg13cmos5l_stdcell` uses both. So the cell abstracts and the GDS carry no
  stack dependence at all, and a stack change cannot invalidate a cell.
- **The `.lib` files carry zero routing content** (`grep -c` for
  metal/layer/routing returns 0 on all three) and their corners are already this
  chip's family: tt 1.20 V/25 C, ss 1.08 V/125 C, ff 1.32 V/-40 C. See the
  *Supply* section of the repo `CLAUDE.md`.
- **The CDL calls `sg13_lv_nmos` / `sg13_lv_pmos`**, the same device subcircuits
  SG13CMOS5L uses.
- The Verilog views and the cell list have no technology content.

## Three things this library does not share with `sg13cmos5l_stdcell`

None of them is caused by the stack move (they are the same under SG13G2). They
decide whether the two libraries can sit in one design.

- **The site name collides.** Both call it `CoreSite`, EZ130 at
  0.42 x 3.36 um and the PDK at 0.48 x 3.78 um. Loading both LEFs into one
  OpenROAD database gives one `CoreSite`, silently. Mixing the two libraries in
  a single design needs the EZ130 site renamed first.
- **The cell boundary is on 235/4, not `prBoundary.boundary` 189/4.** Layer 235
  is in neither PDK's layer properties. Every cell carries exactly one 235/4
  shape, so the boundary is there; it is just somewhere the repo's own tooling
  does not look. Anything in `scripts/` that reads 189/4 to get a cell width
  (see *Full-custom layout* in `CLAUDE.md`) reads this library as having no
  boundary, and the drawn bbox is not a substitute.
  `scripts/add_prboundary.py` copies 235/4 onto 189/4 and has to be re-run on
  every vendor drop; `--check` says whether it is due.
- **8T against the PDK's 9T.** 3.36 um rows do not abut 3.78 um rows, so this is
  a whole-block choice, not a per-cell one.

## Three defects of the August drop, fixed in the September 2026 drop

`scripts/sclqa` (see `doc/sclqa.md`) found 45 findings in 33 cells of the first
v1.1 drop. The September 2026 drop fixes all of them and reports 0
(`doc/sclqa_report.md`):

- **`CGTSX1/1P5/2/3`: the enable was inverted IN SILICON**, `ECK = CK AND NOT(E
  OR SE)` against the Verilog's `CK AND (E OR SE)`. Only these four cells'
  GDS changed.
- **`DFFRQ2X*`/`DFFRQ4X*`: the Verilog read the undeclared bundle name `D`**, so
  every `Q` of every bank simulated as `x`. They read `D0..D3` now.
- **The CDL disagreed with the GDS in 25 cells** on the order of series
  transistors. 14 failed KLayout outright and 11 matched only under a pin
  permutation, which broke parents with no cell to blame. The vendor's Calibre
  runs `LVS RECOGNIZE GATES ALL`, which hides exactly this. All 25 match
  pin-for-pin now, so the shipped `cdl/ez130_8t.cdl` is the LVS netlist and
  the locally repaired copy is gone.

The criterion that found the third one stays: **a cell is sound when its GDS is
isomorphic to its CDL with the pins held fixed by name**, never when a comparer
accepts it. The liberty was characterised from the layout, so the CDL fix moved
no timing; only the `CGTSX*` tables changed.

## EZ130 8T against `sg13cmos5l_stdcell`

Measured 2026-09-08 from both CDL netlists (`ez130_8t.cdl`,
`sg13cmos5l_stdcell.cdl`, fingers at L = 130 nm only) and both GDS files
(GatPoly AND Activ for the channels, boundary 235/4 and 189/4 for the widths).
The GDS channel heights and the CDL widths agree, so either source can be used.

### Grid: the device grid is the same, the placement grid is not

| | EZ130 8T | `sg13cmos5l_stdcell` |
|-----|----------|----------|
| `CoreSite` | **0.42 x 3.36** | **0.48 x 3.78** |
| routing tracks per row | 8 at 0.42 | 9 at 0.42 |
| tech LEF Metal1/Metal3 pitch | 0.42 / 0.42 | 0.48 / 0.42 |
| Metal2/Metal4 offset | 0.21 | 0.0 |
| **contacted gate pitch** | **0.51** | **0.51** |
| drawn L | 0.130 | 0.130 |
| manufacturing grid | 0.005 | 0.005 |

**The gate pitch is 0.51 um in both**, verified on every multi-finger cell
(`INVX4`, `INVX8`, `NAND2X1`, `NAND3X1` against `inv_2`, `inv_4`, `inv_8`,
`nand2_1`, `nand3_1`). So the two libraries draw devices on the same pitch and
differ only in the placement site and row height. Neither site is commensurate
with 0.51, in either library; the gates float inside the cell.

Site counts come out the same for the small cells, so the area saving is exactly
the site product: `0.42/0.48 x 3.36/3.78` = **0.778**, a 22 percent smaller cell
for the same function.

| cell | EZ130 | | `sg13cmos5l` | |
|-----|----------|----------|----------|----------|
| inverter, lowest drive | `INVX1` | 3 sites, 1.26 um | `inv_1` | 3 sites, 1.44 um |
| nand2, lowest drive | `NAND2X1` | 4 sites, 1.68 um | `nand2_1` | 4 sites, 1.92 um |
| nand3, lowest drive | `NAND3X1` | 5 sites, 2.10 um | `nand3_1` | 5 sites, 2.40 um |

### Finger width: a width ladder against a fixed finger

| | EZ130 8T | `sg13cmos5l_stdcell` |
|-----|----------|----------|
| NMOS finger widths in use | 12 distinct, 0.25 to 0.88 um | 10 distinct, 0.30 to 0.88 um |
| PMOS finger widths in use | 11 distinct, 0.48 to 1.32 um | 10 distinct, 0.30 to 1.155 um |
| most common NMOS | **0.300 um**, 68 % of fingers | **0.740 um**, 60 % |
| most common PMOS | **0.480 um**, 67 % | **1.120 um**, 51 % |
| minimum inverter | `INVX1` 0.30 / 0.48 | `inv_1` 0.74 / 1.12 |
| P/N width ratio | 1.60 at X1, 1.53 above | 1.514 |
| widest N + P in one cell | 0.86 + 1.32 = **2.18 um**, 65 % of the row | 0.88 + 1.155 = **1.95 um**, 52 % |

**The two libraries scale drive differently, and that is the substantive
difference.** `sg13cmos5l_stdcell` holds the finger at 0.74 / 1.12 um and adds
fingers: `inv_1/2/4/8` are `ng = 1/2/4/8` of the same device. EZ130 climbs a
width ladder first, 0.30/0.48 at X1, 0.64/0.98 at X2, 0.86/1.32 at X3, and only
then multiplies (`INVX4` is `m = 2` of the X2 device). Consequences:

- **EZ130's X1 tier has no counterpart in the PDK library.** At 0.30 / 0.48 um
  it is 2.5x narrower than `inv_1`, which is already a mid-strength device. For
  a block that is area- and leakage-bound rather than speed-bound this is the
  whole reason to reach for EZ130.
- **EZ130's X2 tier, 0.64 / 0.98 um, is still below `inv_1`.** Anything sized
  against `sg13cmos5l` drive numbers will be optimistic here; re-synthesize
  rather than translate a cell mapping.
- **EZ130's row overhead is tighter.** It fits 2.18 um of channel into a 3.36 um
  row where the PDK fits 1.95 um into 3.78 um, so the 8T row is not simply the
  9T row with a track removed.

## LibreLane collateral, and a trial hardening

**The library is read in place and never installed into the PDK.** LibreLane
looks for an SCL's `config.tcl` only under `$PDK_ROOT/$PDK/libs.tech/librelane`,
and resolves `dir::` against the design's directory, not against the file that
says it. So `librelane/config.yaml` holds every setting where EZ130 differs from
`sg13cmos5l_stdcell` (views, liberties, tracks, taps, role cells), and
`scripts/librelane_scl.py` writes a copy with absolute paths to
`<design dir>/runs/.ez130_8t.yaml` for the command line:

```bash
cd macros/<name>/flow/librelane
librelane $(python3 ../../../../ip/ez130_8t_v1p1/scripts/librelane_scl.py) config.yaml
```

The fragment has to come FIRST, and the design config must NOT set
`STD_CELL_LIBRARY: ez130_8t`: every step re-reads the PDK config under that name
(`Config.with_increment`) and dies on one the PDK lacks, after the whole config
has loaded clean. So the name stays the PDK default and the fragment overrides
every view it implies, which also means a design config run alone loads the PDK
library without a word. Every macro's `make flow` does this. Verified
2026-09-14: all eight EZ130 configs resolve to the same values as the former
install, path for path, `STD_CELL_LIBRARY` itself aside.

`scripts/check_scl_config.py` vets every cell name and every pin in the SCL
config, both exclude lists and all three techmaps against the LEF macros and the
liberty pin lists. It proves nothing is a typo; it does not claim the exclude
set is the right set.

### What the exclude lists hold, and what they deliberately do not

**Only clock gates and scan cells are excluded, and nothing else.** Verified by
census rather than by eye: of the 220 macros, exactly seven carry an `E`/`CK`/
`ECK` triple (`CGX1/2/3`, `CGTSX1/1P5/2/3`) and exactly one carries `SD`+`SE`
(`DFFMRQX2`). `synth_exclude.cells` is those eight, no more and no less;
`pnr_exclude.cells` is the four scan clock gates plus the scan flop. Listing an
ICG in `synth_exclude.cells` does not stop the yosys `clockgate` pass inserting
it, which is the same arrangement the PDK library uses for `lgcp_1`.

### Only one clock gate is reachable, and it is chosen once

`SYNTH_CLOCKGATE_POSEDGE_ICG` is an `Optional[str]`. LibreLane splits it with
`rsplit("/", maxsplit=4)` into one `(cell, ce, clk, gclk)` and hands yosys
`clockgate -pos <cell> <ce>:<clk>:<gclk>`, so **synthesis inserts exactly one
ICG type and there is no list form**.

The obvious hope is that the resizer then sizes them, which is why `CGX1/2/3`
were taken out of `pnr_exclude.cells`. **It does not.** Measured 2026-09-08 by
inserting the weakest gate and giving the resizer every freedom: 6 `CGX1` after
synthesis, 6 `CGX1` in the final netlist, and the block misses 2.8 ns by
43.2 ps with 9 violations where `CGX3` closes at +32.2 ps with none. OpenROAD
treats an ICG as clock-network furniture, not as a resizable gate.

So the `pnr_exclude.cells` entry for `CGX*` is inert either way, and it is left
out because nothing should block them artificially. What actually decides the
clock gate is the one name in `SYNTH_CLOCKGATE_POSEDGE_ICG`, it is a real
timing choice worth 75 ps on this block, and it has to be picked on
`max_capacitance` against the PDK library like every other role cell.

**The multi-bit flops `DFFRQ2X*` and `DFFRQ4X*` are in neither list.** They were
excluded from 2026-09-10 to 2026-09-14 for their broken Verilog view, fixed in
the September 2026 drop (see above).

An earlier revision excluded them for a *wrong* reason, which is worth keeping
apart. That came from reading the PDK's
`sg13cmos5l_dfrbp_2` as a two-bit cell. It is not: it is drive 2 of a
dual-*output* flop. EZ130's `DFFRQ2X1 (Q0, Q1, D0, D1, RB, CK)` and
`DFFRQ4X1 (Q0..Q3, D0..D3, RB, CK)` are genuine flop banks sharing one clock
and one reset, a capability `sg13cmos5l_stdcell` does not have at all, so
excluding them for that reason foreclosed the one thing worth trying.

Making them available changes nothing today, and it is worth knowing why rather
than concluding the cells are useless. Removing them from both lists gives a
**bit-identical run**: same 146 `DFFRQX3` and 6 `CGX3`, same 11876.7 um2, same
+32.2 ps, same wirelength, same 0/0 DRC. Nothing in this toolchain infers a
flop bank: yosys has no pass matching mbff, bank or multibit, OpenROAD in
`96bdc869118a` exposes no `*mbff*` or `*bank*` command, and LibreLane has no
config variable for it. Reaching them would need an explicit techmap beside
`latch_map.v` and friends, driven by something that groups registers by clock
and reset. Until then the cells sit unused but reachable, which is the right
state for them.

### Two things had to be right before the numbers meant anything

**EZ130 needs well taps and `sg13cmos5l_stdcell` does not.** This is the one
place the two libraries differ structurally rather than in sizing.
`sg13cmos5l_inv_1` has four Activ polygons, the two channels plus a full-width
tie strip on each rail; `INVX1` has two, the channels alone. That is why the
PDK config says there are no welltie cells and sets `FP_TAPCELL_DIST 0`, and
why EZ130 ships a `WELLTAP`. Hardening with taps off gives **13588 Magic and
170 KLayout markers, every one of them `LU.a` or `LU.b`**, the 20 um latch-up
rules, while routing, antenna and timing all come back clean. `WELLTAP_CELL`
plus `FP_TAPCELL_DIST 20` places 85 taps and takes both counts to 0.

**The drive digit is not comparable across libraries.** The repo already knows
the number in a cell name is drive strength and not width; across libraries it
is not even the same drive. Matched on `max_capacitance` at the slow corner the
two ladders are offset by exactly 3x:

| `sg13cmos5l` | pF | EZ130 | pF | area, PDK vs EZ130 (um2) |
|-----|---|-----|---|-----|
| `buf_1` | 0.3 | `BUFX3` | 0.315 | 7.26 / 5.64 |
| `buf_2` | 0.6 | `BUFX6` | 0.63 | 9.07 / 7.06 |
| `buf_4` | 1.2 | `BUFX12` | 1.26 | 14.52 / 11.29 |
| `buf_8` | 2.4 | `BUFX24` | 2.52 | 23.59 / 22.58 |
| `buf_16` | 4.8 | `BUFX48` | 5.04 | 45.36 / 42.34 |
| `lgcp_1` | 0.3 | `CGX3` | 0.315 | 27.22 / 21.17 |

Taking `BUFX8` for `buf_8` handed CTS a 3x weaker buffer set and a 3x weaker
clock gate. The result was not a slower logic path, it was a slower **clock**:
insertion delay to the worst endpoint reached 1.115 ns with 329 ps of it inside
`CGX1` alone, the worst setup path became a clock path, and the block missed
2.8 ns by 61.8 ps with 15 violations. Re-matched on capacitance it closes with
+32.2 ps and none. Both rows are in the table below, because the wrong one is
the easy mistake.

### PPA, `dco_switch_cap_decoder` at 2.8 ns

Same RTL, SDC, `SYNTH_STRATEGY`, utilization, resizer margins and STA hook;
`config_ez130.yaml` differs from `config.yaml` in four keys only. Image
`96bdc869118a`, 2026-09-08. Both netlists carry 146 flops and 6 clock gates.

| | `sg13cmos5l_stdcell` | `ez130_8t` | | (name-matched, wrong) |
|-----|----------|----------|----------|----------|
| logic cell area, excl. fill | 18768.2 um2 | **11238.8** | **-40.1 %** | 11125.9 |
| of which well taps | 0 | 359.9 (85 cells) | | 359.9 |
| die | 152.4 x 171.1 | **120.7 x 137.5** | **-36.4 %** | 120.7 x 137.5 |
| placed instances | 1585 | 1324 | -16.5 % | 1402 |
| route wirelength | 17902 um | 16396 | -8.4 % | 15310 |
| setup WNS, slow | +189.7 ps | **+32.2 ps** | -157.5 ps | -61.8 ps |
| setup violations, slow | 0 | **0** | | 15 |
| hold WNS, fast | +72.1 ps | +107.9 ps | +35.8 ps | +107.5 ps |
| internal power | 2658.7 uW | 1453.3 | -45.3 % | 707.8 |
| switching power | 508.9 uW | 375.9 | -26.1 % | 225.9 |
| **leakage** | **463.9 nW** | **325.9 nW** | **-29.7 %** | 339.3 |
| total power | 3168.1 uW | **1829.5** | **-42.3 %** | 934.0 |
| Magic / KLayout DRC | 0 / 0 | **0 / 0** | | 0 / 0 |
| antenna violations | 0 | 0 | | 0 |

**EZ130 buys about 40 percent of the area and 42 percent of the power for 157 ps
of setup margin.** Four things bound how far that reads:

- **It is iso-constraint, not iso-performance.** Both close 2.8 ns; neither was
  pushed to its own limit. The baseline still has 190 ps in hand, EZ130 has 32.
- **This block's own config documents +/-80 ps of run-to-run placement noise**
  on the marginal DSM adder path, so the 157 ps is a single-run number of the
  same order as the noise, not a characterized delta. A frequency sweep on the
  name-matched config was non-monotonic (-61.8 / -158.4 / -57.1 ps at
  2.8 / 2.9 / 3.0 ns) for exactly that reason, and because `SYNTH_STRATEGY:
  DELAY 4` makes yosys period-independent here: the synthesis netlist is
  byte-identical across all three periods.
- **Power is OpenSTA with the RTL VCD through `read_vcd`**, which on a flat
  post-layout netlist annotates only top-level pins and propagates from there
  (see *Power* in `CLAUDE.md`). Same method on both sides, so the ratio is
  worth more than the absolute.
- **8T against 9T is a whole-block choice.** 3.36 um rows do not abut 3.78 um
  rows, and the `CoreSite` name collides, so the two libraries cannot share a
  placement region.
