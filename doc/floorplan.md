<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# Chip Floorplan

Die and core geometry, the one hard macro and where it sits, and the power
distribution network with the measurements that justify it.

Related: [pinout.md](pinout.md) for the pad table, [rtl2gds.md](rtl2gds.md) for
how the layout is produced.

## Die and core geometry

| | value |
|---|---|
| Die | 1600 x 1600 um |
| Core | `[365, 365, 1235, 1235]`, 870 um square |
| Padframe margin | 365 um per side |
| Package | QFN-32, `OP_QFN32_A4_FIT` |
| Routing stack | Metal1 to Metal4 plus TopMetal1 |

CMOS5L has no Metal5 and no TopMetal2, so `RT_MAX_LAYER` is Metal4 in every
macro and TopMetal1 is left for the top-level power grid.

The die size is inherited from the template and was not re-derived. It is not
tight: the core holds one 497 um macro and 871 um2 of standard cells.

## The one hard macro

| | |
|---|---|
| Cell | `dsa1_dig_top` |
| Size | 497.28 um square |
| Instance | `i_sg13cmos5l_dsa1_dig_core.dsa1_dig` |
| Placement | `[365 + 186, 365 + 186]`, orientation N |
| Views | `macros/dsa1_dig/final/{gds,lef,nl,pnl,spef,lib}` |

Roughly centred in the core. The placement is a round number rather than a
derived one, and it should be revisited if the macro die is ever re-sized.

Everything else in the core is 3 flops and about 871 um2 of glue: the
three-stage synchronizer on the bitstream input. The chip does nothing else.

The template's two counters, two inverters and the SRAM are gone from the die.
Their macros remain in `macros/` as the archetypes they are.

## Power distribution

Resolved from the flow, not from the config comments:

| | layer | width | pitch |
|---|---|---|---|
| Core ring | Metal4 and TopMetal1 | 15 um | 5 um spacing, connected to the pads |
| Vertical straps | Metal4 | 1 um | 50 um |
| Horizontal straps | TopMetal1 | 2 um | 50 um |
| Standard-cell rails | Metal1 | 0.44 um | row pitch |

The macro is covered by the default `-macro` grid. Its own ring must leave one
top-level PDN layer free: the top level is Metal4 vertical and TopMetal1
horizontal, so a macro ring occupying both would make pdngen cut every stripe
at the macro and leave the ring unfed. That failure does not surface until IR
analysis reports `PSM-0069`.

### Measured IR drop

Corner `nom_typ_1p20V_25C`, from the chip run:

| net | average | worst | of supply |
|---|---|---|---|
| VDD | 0.594 mV | 1.16 mV | 0.10 % |
| VSS | 0.537 mV | 0.971 mV | 0.08 % |

Inside the macro, worst-case VSS drop is 35 uV, 0.00 %.

**These are pessimistic.** OpenROAD computes them from the flow's own power
estimate, which reports 1.68 mW for a block whose measured static current is
about 1.2 uW at tt and whose clock is 65 kHz. The real drop is far smaller
than 0.1 %. Read these as a bound, not a measurement.

## On-die decoupling, and what the thick-oxide swap costs

The die decouples with `DECAPHV8/16/32` only. EZ130's thin-oxide `DECAP*` is
banned, because it was 83.6 % of the block's leakage.

That choice is not free. A thick oxide stores far less charge for the same
area, and the counts per size are identical between the two builds, so the
comparison is exact:

| cell | count | C thin-oxide | C thick-oxide |
|---|---:|---:|---:|
| 8 | 1711 | 49.82 fF | 6.27 fF |
| 16 | 527 | 128.89 fF | 30.52 fF |
| 32 | 106 | 270.50 fF | 79.03 fF |
| **total** | **2344** | **181.8 pF** | **35.2 pF** |

**On-die decoupling falls 5.2x, from about 182 pF to about 35 pF.** A further
3654 `DECAP4` cells in the thin-oxide build became plain `FILLER4`, since there
is no `DECAPHV4`, so the real loss is larger than the table shows. `DECAP4` was
never characterised and that part is unquantified.

Per-cell capacitances are from the characterisation in
`ez130_8t_decap_hv/doc/decap_hv.md`, tt corner.

### Does the swap cost meaningful supply impedance?

Two separate questions, and they have different answers.

**Series resistance: no.** Each cell is a single device contacted from both
ends, so its corner falls as 1/L². From the same study:

| cell | channel L | corner | share of the 35.2 pF |
|---|---:|---:|---:|
| `DECAPHV8` | 0.82 um | ~10 GHz | 10.7 pF |
| `DECAPHV16` | 4.18 um | ~0.4 GHz | 16.1 pF |
| `DECAPHV32` | 10.90 um | ~60 MHz | 8.4 pF |

So about 27 pF of the 35 pF is still effective above 400 MHz, and only the
8.4 pF in the largest cells rolls off at 60 MHz. This chip clocks at 65536 Hz
with a 200 kHz SPI, four orders of magnitude below the worst of those corners.
The series resistance of the thick-oxide cells is irrelevant here. It would
matter in a GHz design, which is exactly the caveat that study records.

**Total capacitance: it is a real reduction, and it is not analysed.** Losing
147 pF of on-die decoupling is significant in principle. What this chip has
going for it is that the current it has to smooth is tiny: 1825 flops on a
65 kHz clock, static current about 1.2 uW at tt. Nothing here resembles the
switching transient a fast digital block presents.

What is **not** done, and should be before tapeout:

- No transient simulation of the supply with the real decoupling. The prior
  study in jku-phd characterises the cells, not this die's network.
- No estimate of the package and bond-wire inductance in series with the pads,
  which on a QFN-32 is likely to dominate the on-die network anyway.
- No measurement of the peak switching current, so there is no number to
  divide into 35 pF.

Since 2026-10-06 the bounce case of [testbenches/startup](../testbenches/startup/README.md) has the package in it, bond wires from the bond report, and switches 11 output pads together: the IO rail on the die moves 0.43 V and no core input glitches. Its core draws no current, so the three points above still stand for VDD.

The honest position: the thick-oxide swap buys a 6.2x leakage reduction and
costs 5.2x of on-die decoupling, and on a 65 kHz block that trade looks clearly
right, but the supply network itself has not been simulated.

## Logos

Two blocks on Metal4, placed at the die corners inside the pad ring, from
`ip/sg13cmos5l_ip__jku` (the JKU mark) and `ip/sg13cmos5l_ip__jku_names` (the
author block, M. KOEFINGER). Both are 100 um square hard macros with the
geometry drawn from a PNG by `img2lay.py`, so changing either is a matter of
replacing the image and running `make all` in that IP folder.
`ip/sg13cmos5l_ip__jku_names/script/make_names_png.py` renders the name block.

The template's generic "AMS CHIP" logo, which `scripts/add_logo_fill.sh` used to
write across TopMetal1, is switched off. `CHIP_LOGO=1` puts it back.

## Could the die and the package be smaller

Asked in 2026-09, answered from the cell geometry rather than by trying it.

**The die is core-limited, not pad-limited, so cutting pins does not shrink it.**

| | |
|---|---|
| IO cell (`sg13cmos5l_IOPadIn`, `IOPadOut30mA`) | 80 x 180 um |
| Corner cell | 180 x 180 um |
| Bondpad | 70 x 70 um |
| Padframe margin now | 365 um per side |
| of which IO cell height | 180 um |
| leftover channel and IO power ring | 185 um per side |
| Macro | 497.28 um square |
| Core now | 870 um square, so the macro is 57 % of the core edge |

Two floors set the die. The pad ring costs 2 x 180 um whatever the pin count.
The core has to hold a 497.28 um macro plus a clearance for the chip PDN
straps and the pad-to-core routing. At a 70 um clearance the core is about
637 um and the die about 637 + 2 x 240 = **1.12 mm**, against 1.60 mm today.
That is 49 % of the area, and none of it comes from removing pins: the saving
is the 185 um of padframe slack and the loose core.

**How many pads still fit at 1.12 mm.** Between the corner cells there would be
1120 - 360 = 760 um a side, which at the 114 um pitch of the current bond plan
is 6 pads a side, 24 in total. So a smaller die still carries well over the
number of signals this chip has.

### What the pins are actually for

| Group | Pads | Needed |
|---|---|---|
| `clk`, `rst_n` | 2 | yes |
| `data_in`, `sclk`, `mosi`, `ss` | 4 | yes |
| `miso`, `adc_conv` | 2 | yes |
| VDD, VSS, IOVDD, IOVSS | 4 | yes |
| `o_tst_ctrl[15:0]` | 16 | no, silicon observability of the SPI write path |
| spare bidir and analog | 4 | no |

Twelve pads carry the chip. The other twenty are debug and spares, and while the
die is core-limited they are close to free: they occupy pad-ring perimeter that
exists anyway.

### Package

`packaging/README.md` lists QFN16, QFN24, QFN32, QFN48 and QFN56 in the
EUROPRACTICE library. Three usable points:

| Option | Pads | Die | Comment |
|---|---|---|---|
| QFN32, today | 32 | 1.60 mm | all 16 debug bits, 4 spares |
| QFN24 | 24 | about 1.12 mm | 12 signal, 8 of the 16 debug bits, 4 spare |
| QFN16 | 16 | about 1.12 mm | 12 signal, 4 debug or spare |

The die is the same in the last two rows, because it is the macro and the pad
ring depth that set it, not the pin count. QFN16 buys a cheaper package, not a
smaller chip.

**Recommendation if this is re-floorplanned.** Take the area out of the
padframe margin and the core, not out of the pin list: 365 um to about 240 um a
side and the core down to roughly 640 um gives a 1.12 mm die at about half the
area, in a QFN24 that still keeps half of `o_tst_ctrl` bonded out. Dropping to
12 pins and a QFN16 on its own changes nothing about the silicon.

Two things to check before committing to it, neither done here: the IO power
ring and the pad-to-core routing have to fit the narrower channel, and the
reduced on-die decoupling has to be re-evaluated against the numbers in the
decoupling section above.

## Constraints when editing the floorplan

- **Die geometry lives in four places** kept in step by hand: `DIE_AREA` and
  `CORE_AREA` in `flow/librelane/config.yaml`, the `DIE_*`/`CORE_*` variables
  in `scripts/add_logo_fill.sh`, this file, and `specifications.md`.
- **A macro instance is pinned with `MACROS.<name>.instances`**, not
  `MANUAL_GLOBAL_PLACEMENTS`, which is advisory and runs after `GeneratePDN`
  so pdngen builds no grid over the macro.
- **A hard macro must carry its own metal fill.** Chip fill cannot reach inside
  it, so a sparse macro is a permanent density hole. See
  [rtl2gds.md](rtl2gds.md).
- `PAD_SPACING_MULTIPLE` is hand-derived for 8 pads per side, and for the west side's 8 pads plus the 120 um clamp cell. Redo the
  arithmetic in the config comment if the die or the pad count changes.
