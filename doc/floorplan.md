<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# Chip Floorplan

Die and core geometry, the three hard macros and where they sit, and the power
distribution network with the measurements that justify it.

Related: [pinout.md](pinout.md) for the pad table, [rtl2gds.md](rtl2gds.md) for
how the layout is produced.

## Die and core geometry

| | value |
|---|---|
| Die | 1300 x 1300 um |
| Core | `[345, 345, 945, 955]`, 600 x 610 um |
| Padframe margin | 345 um west and south, 355 um east, 345 um north |
| Package | QFN24, 4 x 4 mm, 0.5 mm pitch, packaged by IHP, bond plan in [packaging/result.md](../packaging/result.md) |
| Routing stack | Metal1 to Metal4 plus TopMetal1 |

CMOS5L has no Metal5 and no TopMetal2, so `RT_MAX_LAYER` is Metal4 in every macro and TopMetal1 is left for the top-level power grid.

The core ends at dsm2's halo, x 945. A core strip east of the halo got Metal4 stripes whose via stacks put Metal3 pads across the corridor of the analog wires, so the core is 10 um narrower in x than the pad ring would allow.

```
              N: rst_n clk sclk mosi ss miso
        +--------------------------------+
   IOVDD| . . . VDD decap rows . .+-----+ |
   IOVDD| +---------------------+ |decap| |
   IOVSS| |                     | |vdda | |clamp
     VDD| |      dsa1_dig       | |     | |VDDA
   clamp| |                     | +-----+ |ibias_test
     VSS| |                     | +-----+ |vcm
        | +---------------------+ |dsm2 | |vi
        | . . . VDD decap rows . .+-----+ |
        +--------------------------------+
     S: data_in adc_conv VSS dsm_clk do_q do_q_b
```

The pad ring has 660 um between the corner cells on every side. `PAD_SPACING_MULTIPLE` 2 puts every gap on the 1 um site grid: west 20 um gaps and 20 um ends, north 24 and 30, east 30 and 30, south 20 and 25. The west side carries five pads and the clamp cell, 5 x 80 + 120 um. The north IOVDD cell has no bond wire.

## The three hard macros

| | `dsa1_dig_top` | `dsm2_core` | `decap_vdda` |
|---|---|---|---|
| Size | 409.08 x 514.08 um, 69 % utilization | 150.5 x 178 um, dsm2's oscillator variant | 150.36 x 349.44 um, DECAPHV only |
| Instance | `i_sg13cmos5l_dsa1_dig_core.dsa1_dig` | `dsm2` | `vdda_decap` |
| Placement | `[355, 393.12]`, orientation N | `[784.5, 375]`, orientation N, south-east corner of the core | `[784.5, 593]`, orientation N, 20 um above dsm2's halo |
| Supply | VDD | VDDA | VDDA |
| Views | `macros/dsa1_dig/final/{gds,lef,nl,pnl,spef,lib}` | `ip/dsm2_core/{gds,lef,cdl,verilog}` | `macros/decap_vdda/final/{gds,lef,pnl,lib,vh}` |

`dsa1_dig_top` sits at the west edge of the core, 10 um in so its halo stays off the west VDD core ring. The chip rows start at y 346.08, pitch 3.36 um, 181 rows. The macro's lower edge is on row 14 (y 393.12), so its 10 um halo blocks rows 11 to 13, and its upper edge at y 907.2 puts the halo end at 917.2, which blocks rows 167 to 169. Rows 0 to 10 below and 170 to 180 above stay free: two VDD decap strips, 11 rows each, x 345.24 to 774.48 (rows 0 to 4 run to x 945 under dsm2's halo). Its east edge is at x 764.08, the halo ends at 774.08, 0.42 um short of dsm2's.

`dsm2_core` is dsm2's oscillator variant of 2026-11-02 (25 pins). Around it the chip top keeps a 10 um halo, so x 774.5 to 945 and y 365 to 563. No PDN strap crosses it on any layer, TopMetal1 is blocked over the box, and fill stays out.

`decap_vdda` is an empty module filled with DECAPHV, its VDD pin on VDDA. Its halo is x 774.5 to 944.86, y 583 to 952.44, and PDN and routing obstructions cover that on every metal, so no VDD strap reaches its Metal4 or Metal3 ports. The 20 um between the two halos is left for dsm2 to grow in height. Its rows are pruned (`FP_PRUNE_THRESHOLD` 200 um), since no strap can reach them there.

Everything else in the core is the glue logic: the three-flop synchronizer on the bitstream, the `DEC_SRC` mux, and two `AND2X1` gates, one for `do_q_dec` and one for `adc_conv`. With the channel east of `dsa1_dig` gone they sit in the VDD strips: the gates and the mux in row 10 (y 379.68, x 475 to 728), the synchronizer in rows 170 and 171. dsm2's analog nets, its VDDA strap and the two straps of `decap_vdda` are drawn after the power grid as special nets, on Metal3 under the core ring.

The template's two counters, two inverters and the SRAM are gone from the die. Their macros remain in `macros/` as the archetypes they are.

## Power distribution

Resolved from the flow, not from the config comments:

| | layer | width | pitch |
|---|---|---|---|
| Core ring | Metal4 and TopMetal1 | 5 um | 5 um spacing, VDD and VSS, connected to the pads |
| Vertical straps | Metal4 | 1 um | 50 um |
| Horizontal straps | TopMetal1 | 2 um | 50 um |
| Standard-cell rails | Metal1 | 0.44 um | row pitch |

The macro is covered by the macro grid, restricted to `dsa1_dig`. Its own ring must leave one top-level PDN layer free: the top level is Metal4 vertical and TopMetal1 horizontal, so a macro ring occupying both would make pdngen cut every stripe at the macro and leave the ring unfed. That failure does not surface until IR analysis reports `PSM-0069`.

The core ring is VDD and VSS only. VDDA is the vdd band of the pad ring between the two `cut_vdd` cells, and it reaches dsm2 through a 10 um Metal3 strap from the VDDA pad's band. `decap_vdda` takes it through its own 10 um Metal3 strap at y 913.36 to 923.36, straight east from its VDD pin into the band of the IO filler at y 910 to 930, below `cut_vdd_e` at y 940. Its VSS strap at y 927.36 to 937.36 ends on the east VSS core ring. The straps, the three analog wires and dsm2's VSS strap are special nets drawn by `flow/librelane/pdn_cfg.tcl`, with checks for spacing, pin entry and VDD isolation.

### Measured IR drop

Corner `nom_typ_1p20V_25C`, from the chip run of 2026-11-01 (`verification/reports/irdrop.rpt`):

| net | average | worst | of supply |
|---|---|---|---|
| VDD | 2.25 uV | 4.93 uV | 0.00 % |
| VSS | 170 uV | 418 uV | 0.03 % |

These come from the flow's own power estimate and bound the real drop. **VDDA has no IR-drop analysis.** The EM check rates it at 1 mA. dsm2's design values for the oscillator variant at its worst corner (ff 1.55 V 125 C) are 32 uA average, 220 uA over 100 ns and 600 uA over 10 ns, so the bound covers even the 10 ns peak.

## On-die decoupling

The die decouples with `DECAPHV8/16/32` only, on both rails. EZ130's thin-oxide `DECAP*` is banned, because it was 83.6 % of the block's leakage in the v1.1.0 build.

| rail | where | `DECAPHV8` | `DECAPHV16` | `DECAPHV32` | C |
|---|---|---:|---:|---:|---:|
| VDD | chip rows (`netlist/pnl`) | 339 | 200 | 511 | 48.60 pF |
| VDD | `dsa1_dig` (`macros/dsa1_dig/final/pnl`) | 1578 | 575 | 78 | 33.61 pF |
| **VDD** | | **1917** | **775** | **589** | **82.21 pF** |
| **VDDA** | `decap_vdda` (`macros/decap_vdda/final/pnl`) | 339 | 323 | 704 | **67.61 pF** |

Per cell 6.272, 30.52 and 79.01 fF, from the characterisation in `ez130_8t_decap_hv/doc/decap_hv.md`, tt corner, which agree with the ngspice AC run in [esd_hbm.md](esd_hbm.md). Before the 2026-10-31 rework the die had 145.2 pF, all on VDD. dsm2's own decoupling is inside its macro and not counted here.

### Does the thick oxide cost meaningful supply impedance?

**Series resistance: no.** Each cell is a single device contacted from both ends, so its corner falls as 1/L². From the same study:

| cell | channel L | corner | share |
|---|---:|---:|---:|
| `DECAPHV8` | 0.82 um | ~10 GHz | 12.0 pF VDD, 2.1 pF VDDA |
| `DECAPHV16` | 4.18 um | ~0.4 GHz | 23.7 pF VDD, 9.9 pF VDDA |
| `DECAPHV32` | 10.90 um | ~60 MHz | 47.0 pF VDD, 55.6 pF VDDA |

This chip clocks at 65536 Hz with a 200 kHz SPI, three to four orders of magnitude below the lowest corner. It would matter in a GHz design, which is the caveat that study records.

What is **not** done:

- No transient simulation of the VDD network with the real decoupling. The core draws microwatts and the start-up bench's core is XSPICE, so it has no on-die decoupling.
- No estimate of the package and bond-wire inductance against the on-die network.
- No measurement of the peak switching current of the decimator.

The bounce case of [testbenches/startup](../testbenches/startup/README.md) has the package in it, with bond wires from the bond report. It runs `dsm_clk` at 1.024 MHz with `do_q` and `do_q_b` switching, and `miso` and `adc_conv` switching through an SPI read. The rails on the die move by IOVDD-IOVSS 49 mV droop and 47 mV overshoot, VDD-VSS 17 and 27 mV, VDDA-VSS 15 and 25 mV, and `vi` by 6.0 mV peak to peak. No core input glitches. Its core draws no current, so the three points above still stand for VDD.

## Logos

Four blocks on Metal4, one in each die corner outside the IO ring, from
`ip/sg13cmos5l_ip__jku` (the JKU mark, upper left), `ip/sg13cmos5l_ip__jku_names` (the
author block, M. KOEFINGER, upper right), `ip/sg13cmos5l_ip__helm` (a knight's helmet, lower right) and `ip/sg13cmos5l_ip__title` (IHP__MPC9724, 2026, DSA1_DIG and BATMON on four lines, lower left). All are 100 um square hard macros with the
geometry drawn from a PNG by `img2lay.py`, so changing one is a matter of
replacing the image and running `make all` in that IP folder.
`ip/sg13cmos5l_ip__jku_names/script/make_names_png.py` renders the name block, `ip/sg13cmos5l_ip__helm/script/make_helm_png.py` the helmet from a photo, `ip/sg13cmos5l_ip__title/script/make_title_png.py` the title block.

The template's generic "AMS CHIP" logo, which `scripts/add_logo_fill.sh` used to
write across TopMetal1, is switched off. `CHIP_LOGO=1` puts it back.

## How the die got to 1.3 mm

The v1.1.1 die was 1.6 mm and core-limited, not pad-limited: the pad ring costs 2 x 180 um whatever the pin count, and the core held one 497 um macro with slack. Dropping the 16 test pads and the 4 spares does not shrink the die by itself. The 1.3 mm die in a QFN24 comes from three changes made together: the pads spread over all four sides, `dsa1_dig` re-hardened at a smaller outline (370 x 588 um at 66 % utilization, since 2026-10-31 409 x 514 um at 69 %), and the core ring at 5 um instead of 15 um. The reasoning is in [dsm2_integration.md](dsm2_integration.md).

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
- **A macro power pin named `VDD` on another rail** needs a `PDN_MACRO_CONNECTIONS` entry, as `decap_vdda` has. Otherwise the standard-cell rule (any instance, pin `VDD`) ties it to VDD at floorplan and `Odb.SetPowerConnections` stops.
- **A pocket of rows no strap reaches** fails the power grid check (PSM-0069). `FP_PRUNE_THRESHOLD` drops rows under 200 um, which covers the one between dsm2's and `decap_vdda`'s halos.
- `PAD_SPACING_MULTIPLE` is hand-derived for the cells of each side, including the 120 um clamp cells and the 10 um cut cells. Redo the arithmetic in the config comment if the die or the pad count changes.
