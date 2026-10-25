<!--
SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
Description: Thick-oxide decap cells for the EZ130 8T row
-->

# Thick-oxide decap cells for EZ130 8T

`DECAPHV8`, `DECAPHV16` and `DECAPHV32` are the same width as EZ130's
`DECAP8/16/32` and hold one `sg13_hv_pmos` each: gate on VSS, source, drain
and well on VDD. They exist for leakage. EZ130's decaps are thin oxide and
tunnel through the whole gate; the HV model carries no tunnelling term at all
(`iginvlw = 0`).

**They can be placed anywhere an EZ130 cell can, and nothing beside them has to
know.** That is the design constraint, and it is proven by DRC against every
cell in the library, not argued (§4). It costs capacitance: the insets that make
a cell safe next to anything leave it 13 to 29 % of the LV cell's C.

Image `hpretl/iic-osic-tools:latest` = `96bdc869118a`, KLayout 0.30.11, PDK
`ihp-sg13cmos5l`, 2026-09-14.

## 1. Result

C is the series capacitance across the rail at 1 MHz, leakage the DC supply
current x VDD, both ngspice on PSP (`make char`). The LV rows reproduce EZ130's
own `cell_leakage_power` to every printed digit, which is the check on the deck.

| cell | area | PMOS W x L | C tt | C ss | C ff | leakage tt / ff |
|---|---:|---|---:|---:|---:|---:|
| `DECAP8` | 11.29 um2 | | 49.82 fF | 47.32 | 52.02 | 1.256 / 4.808 nW |
| `DECAPHV8` | 11.29 um2 | 1.66 x 0.82 um | **6.27 fF** | 5.89 | 6.64 | ~0 |
| `DECAP16` | 22.58 um2 | | 128.89 fF | 122.45 | 134.52 | 3.18 / 11.98 nW |
| `DECAPHV16` | 22.58 um2 | 1.66 x 4.18 um | **30.52 fF** | 28.62 | 32.36 | ~0 |
| `DECAP32` | 45.16 um2 | | 270.50 fF | 256.97 | 282.30 | 6.664 / 25.09 nW |
| `DECAPHV32` | 45.16 um2 | 1.66 x 10.90 um | **79.03 fF** | 74.10 | 83.80 | ~0 |

The HV leakage prints as 1e-10 to 1e-9 nW: solver residue, not an estimate.
Per um2 of gate the HV cells come out at 4.4 to 4.6 fF, which is the HV PMOS
oxide (4.62 fF/um2 at tt, §1 of the removed 9T study,
`git show 71ca7e9f:macros/decap_hv/doc/decap_hv_study.md`), so the
rest of the gap to the LV cell is area the insets take (§2).

## 2. Geometry: every inset is a neighbour's, and derived

"Any neighbour" is measured. `decap_hv_gen.py` reads all 216 single-height EZ130
cells and takes the closest any of them brings Activ to its own edge,
**0.105 um**, and the frame EZ130 draws (NWell and pSD from y 1.46 / 1.47, the
0.16 um rail half-width). Each inset is then the larger of what a foreign cell
needs and what a mirrored copy of this cell needs, with the values read from
`sg13cmos5l_tech_default.json`:

| edge | inset | binding term |
|---|---:|---|
| ThickGateOx, all four sides | 0.43 | TGO.e 0.86 / 2, so two HV windows never come closer than 0.86 (TGO.b against foreign Activ only wants 0.165) |
| NWell tongue under the device | 0.31 | NW.b 0.62 / 2 against a mirrored copy (NW.d to foreign N+ Activ only wants 0.205) |
| Activ, sides and bottom | 0.93 | tongue + NW.c1 0.62 (TGO + TGO.a only wants 0.70) |
| channel top | 2.59 | window top - TGO.c 0.34 |
| pSD tongue | 0.53 bottom, 0.75 sides | the loosest box that still meets pSD.i1 0.40 over the gate and pSD.c 0.18 over Activ |

```
  y 3.36  ================ VDD rail ================   NWell/pSD band: EZ130's own frame
  y 2.93  +------------- ThickGateOx -------------+
  y 2.59  |  | S |======== gate (VSS) ========| D | |   Activ 0.93 .. W-0.93
  y 1.46  |  |   |                              |   | |   <- EZ130's well edge; the tongue
  y 0.93  |  +---+------------------------------+---+ |      carries NWell down to 0.31
  y 0.63  |        [ gate contacts on poly ]          |
  y 0.43  +-------------------------------------------+
  y 0.00  ================ VSS rail ================
        x 0.43                                  W-0.43
```

S and D are one contact column each, 0.34 um of Activ (Cnt.c + Cnt.a + Cnt.f),
strapped on Metal1 to the VDD rail. The gate poly runs down under the device to
a contact row, strapped on Metal1 to the VSS rail. The cell is Metal1 only, and
all of its Metal1 is pin.

**No DigiBnd.** It would relax NW.c1 to 0.31 and buy 0.23 um of W, but Magic's
deck knows only the 0.62 rule, so a DigiBnd cell passes KLayout and fails Magic.

**A single device, as asked, and that sets the RC corner.** The channel is
contacted from both ends only, so its corner falls with 1/L2. Scaled from the
R_ch measured for this device in §2 of that study
(7.0 GHz at L = 1 um, ss, which also fits its 1.7 and 3 um points within 5 %):

| cell | L | f_c, estimate |
|---|---:|---:|
| `DECAPHV8` | 0.82 um | ~10 GHz |
| `DECAPHV16` | 4.18 um | ~0.4 GHz |
| `DECAPHV32` | 10.90 um | ~60 MHz |

`DECAPHV32` decouples the 16 or 40 MHz reference domain and not the DCO rate.
Fingers would move the corner up for the area of one contact column each. Do not
read this off an AC sweep: PSP runs quasi-static and reports the full C at any
frequency.

## 3. One assumption: every row's VDD rail is one net

Two DECAPHV cells mirrored across a VSS rail put their wells 0.62 apart, which
NW.b allows. **The flow deck's NW.b1 asks 1.8 um between wells on DIFFERENT
nets**, and it takes the nets from connectivity up to TopMetal1
(`nwell_drw.nets`). In a powered floorplan the PDN makes every VDD rail one net,
so the rule does not apply; this chip is a single 1.2 V rail. The harness ties
its rails with a Metal2 strap for exactly this reason, and without the strap it
reports 39 NW.b1 markers, all HV over HV. Magic has NW.b only.

A design with separate VDD domains in adjacent rows would need the tongue inset
at 0.90 instead, for W 1.07 um, 36 % less C.

## 4. Verification

| what | how | result |
|---|---|---|
| each cell alone, both PDK KLayout decks | `make drc` | only LU.a, which is the tapless library's: untouched `DECAP4` alone reports LU.a and LU.b |
| each cell alone, Magic | `make drc-magic` | 0, 0, 0 |
| every neighbour | `make drc-row` | 0 markers for each size |
| CDL against GDS pin-for-pin, LEF against GDS, Verilog against liberty | `make qa` (`scripts/sclqa`) | 0 findings |

**The neighbour harness** (`scripts/rowtest.py`) puts every single-height EZ130
cell, in both x orientations, left and right of the DUT, and the whole library
again in the mirrored rows above and below with each cell's edge on a DUT edge.
A second block abuts the DUT to itself, offsets mirrored copies by 0, 1, 3 and 5
sites above and below, and places the other two HV sizes beside it. WELLTAPs
keep LU quiet, and the rows are asserted gap-free on the boundary layer that
landed. The same harness around EZ130's own `DECAP8` and `DECAP32` reports 0,
so a marker in it is the DUT's.

**Every check was made to fail first:**

| control | expected | got |
|---|---|---|
| CDL with `sg13_lv_pmos` | LVS fails | 3 of 3 cells |
| CDL with W 1.20 | LVS fails | 3 of 3 cells |
| `DECAPHV8` with the NWell tongue deleted, in Magic | NW.c1 | NW.c1, NW.f1 |
| the harness with its VDD strap removed | NW.b1 | 39 NW.b1 |
| the harness around `DECAPHV8` with ThickGateOx 0.10 um wider | TGO.e | 46 TGO.e |

## 5. Using them

A second library next to EZ130, not a change to it:

```yaml
DECAP_CELLS: [DECAPHV32, DECAPHV16, DECAPHV8]
EXTRA_LEFS: [dir::<to repo>/ip/ez130_8t_decap_hv/lef/ez130_8t_decap_hv.lef]
EXTRA_GDS:  [dir::<to repo>/ip/ez130_8t_decap_hv/gds/ez130_8t_decap_hv.gds]
EXTRA_LIBS: [dir::<to repo>/ip/ez130_8t_decap_hv/lib/ez130_8t_decap_hv_tt_1p20v_25c.lib]
```

`DECAP*` in EZ130's `CELL_PAD_EXCLUDE` already matches the names. There is no
4-site cell: gaps narrower than 8 sites take `FILLER*`. Not yet run through a
LibreLane hardening; `doc/TODO.md` P17 is where that is tracked.
