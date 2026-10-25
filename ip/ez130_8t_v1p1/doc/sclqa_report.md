<!--
SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# Standard-cell library QA: `ez130_8t_v1p1`

2026-09-14 08:19, 220 cells, 5 checks over 10 workers in 377 s.
Tools: KLayout 0.30.11, PDK ihp-sg13cmos5l.

**No failures.**

## Views

| view | file |
|-----|----------|
| gds | `ez130_8t_v1p1/gds/ez130_8t.gds` |
| cdl | `ez130_8t_v1p1/cdl/ez130_8t.cdl` |
| lef | `ez130_8t_v1p1/lef/ez130_8t.lef` |
| lib | `ez130_8t_v1p1/lib/ez130_8t_tt_1p20v_25c.lib` |
| verilog | `ez130_8t_v1p1/verilog/ez130_8t.v` |

| view | cells |
|-----|----------|
| cdl | 215 |
| lef | 220 |
| lib | 214 |
| verilog | 214 |

Cells not in every view:

- only in lef: `FILLER1`, `FILLER16`, `FILLER2`, `FILLER4`, `FILLER8`
- missing from lib: `WELLTAP`
- missing from verilog: `WELLTAP`

## What was checked

| check | what it compares | cells | fail | other |
|-----|----------|----------|----------|----------|
| **CDL against GDS** | every cell's own GDS extracted and compared to its `.SUBCKT` as a graph, source and drain interchangeable, parallel fingers merged, **with the pins held fixed by name** | 220 | 0 | 5 skip |
| **GDS against the DRC deck** | the PDK deck on each cell alone, plus the metal width and spacing rules that deck does not carry; anything that survives is re-run with the cell abutted with itself, because a blanket layer's minimum area is a property of the row | 220 | 0 | 220 waived |
| **LEF against GDS** | every LEF PORT rectangle against drawn metal of that layer, pin names against the GDS labels, SIZE against the drawn boundary and against the site, and no metal leaving the boundary sideways | 220 | 0 | - |
| **CDL against Verilog** | the transistor netlist evaluated at switch level against the library's own Verilog: every input vector for a combinational cell, a clocked stimulus for a sequential one | 220 | 0 | 2 skip |
| **Verilog against liberty** | the Verilog against the liberty `function`, `ff`/`latch` group or `statetable`, the same way | 220 | 0 | - |

Every check that ran came back clean.
## Waived, skipped and noted

- **220 cells report only context rules**, waived because a cell alone cannot satisfy them: `AFil.g` `AFil.g1` `GFil.g` `LU.a` `LU.b` `M1.j` `M2.j` `M3.j` `M4.j` `TM1.c`. Density and fill need a die; latch-up needs the row's well taps, which a tapless library puts in a separate cell.
- **a diode-connected device has no switch-level value** (skip, 2 cells): `TIEHI`, `TIELO`
- **no netlist in the CDL** (skip, 5 cells): `FILLER1`, `FILLER16`, `FILLER2`, `FILLER4`, `FILLER8`


## The September 2026 drop against the August one

Hand-written, not generated. Image `hpretl/iic-osic-tools:latest`
(`96bdc869118a`), the same `scripts/sclqa` for every row.

**The zero is not vacuous.** The same checks on the August drop still fail:

| check | August drop | this drop |
|-----|----------|----------|
| CDL against GDS, run on this GDS with the August CDL | **25** | 0 |
| CDL against Verilog | **12** | 0 |
| Verilog against liberty | **8** | 0 |

What the drop changed:

| view | change |
|-----|----------|
| GDS | geometry of `CGTSX1/1P5/2/3` only (GatPoly, Cont, Metal1): the enable-inversion fix. XOR of all 220 cells against the August GDS, 189/4 included |
| LEF | one PORT rectangle per `CGTSX*` shortened |
| CDL | the 25 cells whose series order disagreed with the GDS, now pin-for-pin |
| Verilog | `DFFRQ2X*`/`DFFRQ4X*` read `D0..D3` instead of the undeclared bundle `D` |
| liberty | `CGTSX*` tables move 1 to 2 % mean, 21 % max; every other cell 0.14 % max |

Adopted with it: `scripts/add_prboundary.py` re-run (the drop has 235/4 only),
the SG13CMOS5L `lef/ez130_tech.lef` kept, the local repair CDL and its scripts
removed, and the `DFFRQ2X*`/`DFFRQ4X*` exclusion lifted.
