<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# sg13cmos5l_ip__clamp_vddvss

An RC-triggered ESD supply clamp from core vdd to core vss, drawn as a 120 x 180 um IO ring cell without a bondpad, for the west side of the DSA1 pad ring between the VSS and the VDD pad.

## Why

IHP's IO library has no vdd-to-vss clamp: `IOPadVdd` clamps vdd to iovss. The chip's HBM check (`doc/esd_hbm.md`) puts 8.4 V across the 1.2 V core rail for a 2 kV zap VDD + vs VSS. The ESD bench with this clamp at its size (`scripts/esd/hbm.py --clamp vss_w2 --clamp-x 1.5`) brings it to 3.45 to 3.62 V.

## Circuit

IHP's `IOPadVdd` clamp with its source on vss and the NMOS three times IHP's block. All devices are thick oxide (`sg13_hv_*`).

| device | size | nets |
|---|---|---|
| `Rtrig1..25` | rppd, 25 x (1 x 20 um) in series, 129.3 kOhm | vdd to `clamp_rc` |
| `Mcap` | hv_nmos 126 / 9.5 um, 14 fingers | gate `clamp_rc`, rest vss |
| `Minvn`, `Minvp` | hv_nmos 108 / 0.5, hv_pmos 350 / 0.5 | `clamp_rc` to `clamp_g` |
| `Mclamp` | hv_nmos 2268 / 0.6, 3 blocks of 2 x 42 fingers of 9 um | vdd to vss, gate `clamp_g` |

IHP's inverter is kept. On a 10 ns vdd edge from 0 to 1.2 V the gate passes 1.08 V at 9.8 ns with 756 um of clamp, 10.7 ns with 1512 um and 11.6 ns with 2268 um, 1.6 ns after vdd arrives. A 1.5x inverter gives 11.9 ns.

## Layout

y 0 is the outer edge of the IO row, as in the IO library. The four ring bands run straight across as in the PDK's IO fillers, read from the `sg13cmos5l_Filler2000` LEF by `layout/rails.py`:

| net | Metal3 | Metal4 | TopMetal1 |
|---|---|---|---|
| iovss | 7..32.5, 34.5..60, 126..134 | same | same |
| iovdd | 66..91.5, 93.5..119 | same | same |
| vss | 140..158 | 162.2..178 | none |
| vdd | 160..178 | 140..155.8 | none |

Each iovss and iovdd band is stitched over its three layers (13000 to 13250 Via3 and 4089 TopVia1 per wide band, 4000 and 1128 on iovss 126..134).

The clamp sits under the bands on FEOL, Metal1 and Metal2 only:

| y (um) | x (um) | what |
|---|---|---|
| 62.9..129.6 | 3.9..27.4, 52.6..76.1, 92.6..116.1 | the three clamp blocks, IHP's finger (L 0.6, source 0.64, drain 1.18), each in a p+ ring on vss |
| 67.1..114.7 | 28.5..51.1 | `Rtrig`, two tiers |
| 11.3..55.5 | 4.8..50.8 | `Mcap`, two blocks |
| 11.3..57.7 | 94.9..114.2 | the inverter under block C, NMOS under PMOS in its own well |
| 11.3..158 | 1..4.8, 115.2..119 | vss lanes on Metal1 and Metal2 |

Each block carries eight 1.6 um Metal2 stripes that run straight up. The vss stripes end in the vss Metal3 band, the vdd stripes pass under it into the vdd Metal3 band and reach the vdd Metal4 band through Metal3 islands cut out of the vss band (140..148, 0.6 um clear), so the two vdd bands are one conductor in this cell. The two vss bands are not tied here, as in the fillers. Metal2 strips under the vss and vdd Metal3 bands collect the stripes.

| via | count |
|---|---|
| Via1, clamp drains to vdd stripes | 756 (63 per stripe) |
| Via1, clamp sources to vss stripes | 792 (66 per stripe) |
| Via2 and Via3, vdd islands | 612 each (51 per island) |
| Via2, vss strip and stripes to the vss Metal3 band | 5846 |
| Via2, vdd strip to the vdd Metal3 band | 9102 |

Per stripe these are OpenBLAU's counts. `clamp_gen.py` fails below 200 on any of them.

Activ starts at y 11.3, 11.3 um from the neighbours' bondpads (`Pad.d1R`, 11.2). Metal1 and Metal2 stay 1 um inside the cell edges, because the IO cells run theirs to within 0.21 um of their own. The substrate tie is the clamp's p+ rings on vss, 640.8 um^2. There is no iovss tap and no `sub!` label: an iovss tap would tie iovss to vss through the substrate inside this cell, and LVS would read them as one net.

The LEF is `CLASS PAD SPACER` on `sg13cmos5l_ioSite` (1 um, so 120 um is legal), as the fillers, with one port per band rectangle and the fillers' OBS. The liberty carries the cell and its four `pg_pin`s and no timing. yosys, OpenSTA and OpenROAD read them.

## Checks

| target | what | result |
|---|---|---|
| `make drc` | KLayout regular deck, the cell alone | 5 markers, all global density rules of the deck's density table: AFil.g, GFil.g, M1.j, M3.k, M4.k (cell Metal3 80 %, Metal4 79 %, from the IO bands) |
| `make magic-drc` | Magic, `drc(full)`, hierarchical | 0 |
| `make drc-abut` | the cell between IOPadVss and IOPadVdd with their bondpads at (5, -70), abutted, with a Filler2000 and with a Filler4000 each side, against the same rows with 120 um of fillers in the slot | no seam break on Metal3, Metal4 or TopMetal1 the filler rows do not have, no new DRC marker |
| `make lvs` | KLayout LVS against `cdl/`, series resistors kept apart | match: 4 MOS and 25 rppd |
| `make probe` | each of the 24 stripes on its own band, 6 distinct nets, 19 bands solid edge to edge | ok |
| `make sim-clamp` | `sim/tb_clamp.py`, the CDL in ngspice, typical models | ok |
| `make mutants` | each check above on a broken layout or CDL | every one fails, see below |

LVS cannot see iovss and iovdd (no device) or a stripe cut off its band (the fingers join it to the others), and passes both. The probe catches them.

`make magic-drc` runs `sak-drc.sh` without `-f "*"`. With `gds flatglob *` Magic flattens the top cell itself away and checks an empty cell: it reports 0 on a 0.1 um Metal2 gap in this cell and on a cell of two rectangles 0.1 um apart.

The negative controls (`layout/mutants.sh`, outputs in a scratch directory, never in the views):

| broken input | check | result |
|---|---|---|
| Metal2 tab 0.1 um from a vss stripe | `drc`, `magic-drc` | M2.b, Magic 2 errors |
| Activ at y 1..3, 9.6 um from the neighbour's pad opening | `drc-abut` | 2 Pad.d1R more than the filler row |
| inverter NMOS gates removed | `lvs` | mismatch |
| CDL clamp 1512 um | `lvs` | mismatch |
| Metal2 bar from a vdd to a vss stripe | `probe` | vdd and vss one net |
| one vdd stripe of block B cut above the fingers | `probe` (LVS passes) | stripe does not reach its bands |
| vss Metal3 band drawn over the vdd islands | `probe` | vdd and vss one net |
| 1 um gap in iovss Metal3 band 34.5..60 | `probe` (LVS passes) | band has a gap |
| CDL inverter input on vdd | `sim-clamp` | gate never on |
| CDL capacitor 10x | `sim-clamp` | a 1 us ramp turns it on, 1.2 V, 72 mA |

## Clamp bench

Leakage vdd to vss, DC:

| vdd | -40 C | 27 C | 125 C |
|---|---|---|---|
| 1.20 V | 0.11 pA | 26.9 pA | 20.1 nA |
| 1.32 V | 0.12 pA | 27.6 pA | 20.6 nA |

vdd from 0 to 1.2 V, 27 C:

| ramp | gate peak | clamp current peak | gate over 1.08 V | gate back under 0.6 V |
|---|---|---|---|---|
| 10 ns | 1.200 V | 72 mA | 11.6 ns | 0.26 us |
| 1 us | 0.174 V | 2.4 uA | never | |
| 100 us | 0.080 V | 22 nA | never | |

A 2 kV HBM current (1.33 A, 10 ns rise, 150 ns decay) into an unpowered vdd peaks at 3.87 V with ideal metal (7.72 V with IHP's 756 um, 5.01 V with 1512 um). The bench fails if a 10 ns edge leaves the gate under 1.08 V for more than 20 ns, or if a 1 us or 100 us ramp lifts it over 0.3 V or the clamp current over 10 uA.

## Files

- `layout/clamp_gen.py` the generator, writes `gds/` and `lef/`. `layout/clamp.py` the devices, `layout/rails.py` the band positions.
- `layout/clamp_probe.py`, `layout/clamp_abut.py`, `layout/drc_report.py`, `layout/mutants.sh` the checks.
- `cdl/` the LVS reference, `verilog/` the blackbox, `lib/` the liberty, `sim/tb_clamp.py` the bench.

The generator, the clamp drawing, the rail reader, the probe and the abutment test are ported from OpenBLAU 8f25e634, `ip/sg13cmos5l_ip__rfpad_70x70`.
