<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# sg13cmos5l_ip__cut_vdd

A 10 x 180 um IO ring cell that carries iovss, iovdd and vss and has no vdd band. Two of them bound the segment of the pad ring where the vdd band is VDDA for the dsm2 pads.

## Why

The ring's vdd band runs unbroken through every IO cell. A cut cell on each end of a segment separates the VDD band outside from the VDDA band inside, 10 um of nothing between the two.

## Cell

The cell is the PDK's `sg13cmos5l_Filler2000` with the vdd band deleted, so every other band, label and tap abuts as the filler does. `layout/cut_gen.py` copies the filler from the IO GDS, and the vdd band y ranges come from the IO LEF through the clamp cell's `rails.py`:

| layer | vdd band (um) | taken out |
|---|---|---|
| Metal3 | 160..178 | the band, its pin shape and label |
| Metal4 | 140..155.8 | the band, its pin shape and label |
| TopMetal1 | none in the filler | nothing |
| Metal1, Cont, Activ, NWell | the two n-taps at y 148.5 and 167 | every shape inside the Metal3 and Metal4 ranges |

The taps go because they only tie the filler's wells to vdd. The wells run 0.62 um into the neighbours and would join VDD to VDDA. One Metal1 strip (y 115.62..140.17) and one Activ strip stay: they are the vss and iovss tap and cross y 140 by 0.17 um.

The LEF is the filler's with the `vdd` pin removed, as text, `CLASS PAD SPACER` on `sg13cmos5l_ioSite`. The liberty has the three `pg_pin`s and no timing. The CDL is an empty subckt with `vss iovdd iovss`. The blackbox is in `verilog/`.

## Checks

| target | what | result |
|---|---|---|
| `make drc` | KLayout regular deck, the cell alone | 6 markers, all global density rules: AFil.g1, GFil.g, M1.k, M2.j, M3.k, M4.k |
| `make magic-drc` | Magic, `drc(full)` | 0 |
| `make drc-abut` | the cell between IOPadIn and IOPadOut4mA and between IOPadVss and IOPadIn with bondpads, abutted, with a Filler2000 and a Filler4000 each side, against the same rows with a Filler2000 in the slot | no new DRC marker in any of the 6 rows. The only seam breaks are the vdd bands on Metal3 and Metal4, which end at the two cell edges, 10 um apart |
| `make lvs` | KLayout LVS against the CDL | passes, and compares nothing. A cell without devices extracts to an empty netlist, so it needs `--disable_tap_extraction --ignore_top_ports_mismatch` |
| `make probe` | iovss, iovdd and vss bands whole from x 0 to 10 (17), no vdd band shape or label, labels are iovss, iovdd, vss | ok |
| `make probe-filler` | the probe on the PDK's Filler2000 | fails on (b) and (c), as it should |
| `make mutants` | a cell with a 2 um Metal3 strip left in the vdd band | the probe fails on (b) |

LVS cannot see the ports of this cell, so the probe checks the bands and the labels.

## VDDA clamp

`clamp_vdda` is a second instance of the signed-off `sg13cmos5l_ip__clamp_vddvss` on the segment's band, no new cell. Its bench at 1.5 V (`make -C ../sg13cmos5l_ip__clamp_vddvss sim-clamp SIM_ARGS="--vdd 1.5"`, typical models):

| vdd | -40 C | 27 C | 125 C |
|---|---|---|---|
| 1.50 V | 0.127 pA | 28.7 pA | 21.3 nA |
| 1.65 V | 0.133 pA | 29.7 pA | 21.9 nA |

At 1.2 V the same bench gives 20.1 nA at 125 C. The 10 ns edge 0 to 1.5 V takes the gate past 1.35 V in 9.95 ns with a 0.168 A peak. The 1 us and 100 us ramps lift the gate to 0.188 V and 0.082 V, 2.9 uA and 28 nA. The 2 kV HBM result does not depend on vdd, the rail is unpowered.
