<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# decap_vdda

Decoupling block for the 1.5 V VDDA supply, north of dsm2. It has no logic and no signal ports. LibreLane fills every row with the thick-oxide `DECAPHV32/16/8` cells, nothing else is allowed as decap on this die.

## Numbers

| | |
|---|---|
| Outline | 150.36 x 349.44 um, the 150.5 x 352 um slot rounded down to the 0.42 x 3.36 um site grid |
| Rows | 94, core x 2.52 to 147.84 um, y 3.36 to 319.2 um |
| `DECAPHV8` | 339 cells, 2.126 pF |
| `DECAPHV16` | 323 cells, 9.858 pF |
| `DECAPHV32` | 704 cells, 55.623 pF |
| Decoupling | 67.61 pF with 6.272, 30.52 and 79.01 fF per cell (`doc/floorplan.md`), 1.29 fF per um2 of outline |
| Other cells | 336 `WELLTAP`, 478 `FILLER1/2/4`, one `TIEHI` and one `INVX1` |
| Leakage | 0.038 nW at tt 1.20 V 25 C, 0.079 nW at ff 1.32 V -40 C, 0.123 nW at ss 1.08 V 125 C |

The leakage is the liberty value summed by OpenSTA. No liberty exists at 1.5 V, so ff at 1.32 V is the closest voltage and tt at 25 C the closest temperature. Nearly all of it is the tie cell and the inverter. The decap cells add about 1e-6 nW, which the characterisation reports as solver residue (`ip/ez130_8t_decap_hv/doc/decap_hv.md`).

## Power pins

The chip ties `VDD` to the VDDA net with `add_global_connection`, as for dsm2, and `VSS` to ground. Each has one 10 um Metal3 strap that runs the full width, so the east end is the pin the chip strap reaches. TopMetal1 is free over the macro.

| Pin | Layer | Rect x | Rect y |
|---|---|---|---|
| `VDD` | Metal3 | 0 to 150.36 | 320.36 to 330.36 |
| `VSS` | Metal3 | 0 to 150.36 | 334.36 to 344.36 |

The same straps also reach the west edge. The LEF lists the Metal4 stripe ends above and below the core as pin shapes of the same nets. The rows are fed by Metal1 rails and Metal4 stripes (2 um wide, 30 um pitch).

## Why the cells are there

- Yosys stops with "No top module found" on an empty module and global routing stops on a design with no net. `rtl/decap_vdda.sv` therefore holds one kept `TIEHI` that drives one kept `INVX1` with a floating output.
- `Checker.DisconnectedPins` is off in the config for that inverter output.
- RCX writes an empty `*PORTS` section for a design with no ports and OpenSTA rejects it. `make librelane` stops after RCX, deletes the line and resumes at `STAPostPNR`.
- The Metal3 straps sit above the core, so `flow/librelane/pdn_cfg.tcl` lets them leave it. A strap over rows blocks the Metal1 to Metal4 vias of those rows. With the core top at 319.2 um the strap starts at 320.36 um.

## Checks

Flow run, 4 min 24 s wall time with two LibreLane calls.

| Check | Result |
|---|---|
| Router DRC | 0 |
| KLayout DRC in the flow | 0 |
| Magic DRC in the flow | 0 |
| LVS | clean |
| Antenna | 0 violating nets and pins |
| Magic DRC of the filled GDS | 0 |
| KLayout regular DRC of the filled GDS | 2 markers, `M1.j` and `TM1.c` |

`M1.j` and `TM1.c` are the global density rules (35 % Metal1, 25 % TopMetal1) read over the macro alone. They are chip-level rules, and TopMetal1 stays empty on purpose. Every other rule of the regular deck is 0, including the `M<n>Fil` rules.

Metal fill from `macros/scripts/fill_macro.sh` takes Metal1 to Metal4 from 23.13, 0.48, 6.07 and 13.30 % to 27.44, 46.79, 35.89 and 55.74 %. LVS and the antenna check ran before the fill, both DRC decks ran again after it.

## Rebuild

```
make librelane
make fill
make copy-final
```

Run them in a LibreLane container, for example `scripts/in_image.sh 'make -C macros/decap_vdda librelane'`.
