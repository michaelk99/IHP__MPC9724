# ihp-sg13cmos5l Trimmable Bias Output (bias_trim)

A PMOS current-mirror output with a binary trim, made to hang on the gate net `vz` of the `bias_gm` core mirror. Every current unit is the core PMOS unit (LV 0.5u/5u, 8.33 nA at the core operating point) with a series switch of the same device, one switch element of 2 unit devices per group. The trim bits go straight to the switch gates, there is no logic in the cell. **Schematic, testbenches and layout, no CACE datasheet yet.** Every number below is a sanity check from the benches of this folder, not a characterisation. The `code` sweep and the Monte Carlo of the whole cell wait for the unit pick of the `bias_gm` task.

It is its own macro because copies are planned for an optional on-chip oscillator and for a measurement pin, each on the same `vz`.

## Ports

| Port | Direction | Meaning |
| --- | --- | --- |
| `vdd`, `vss` | inout | supply and ground |
| `vz` | in | gate of the core PMOS mirror of `bias_gm`, sets the unit current |
| `di_trim_b[3:0]` | in | active low trim bits, a low bit closes the switches of its group, code 4 is `di_trim_b` = 1011 |
| `iout` | inout, sourcing | output current |

Port order in the netlist is `vdd vss vz di_trim_b[3] di_trim_b[2] di_trim_b[1] di_trim_b[0] iout`. There is no `di_ena` pin. The units are switched off by the `vz` clamp of `bias_gm`.
Symbol: references on the top edge (`vdd`, `vz`, `di_trim_b[3:0]`), `vss` at the bottom, `iout` on the right, five current sources with one switch each in the body.

## Circuit

Schematic: `schematic/xschem/bias_trim.sch`, one band of five columns. The groups are 16 fixed units and 16, 8, 4, 2 units for bit 3 to bit 0, so 46 units, output = 8.33 nA x (16 + 2 x code) at the core operating point, code 4 gives 200 nA.

| Group | Devices | Sizes |
| --- | --- | --- |
| Units, LV PMOS, gate `vz`, source `vdd` | `MPF` (fixed), `MP3` to `MP0` (m = group size) | 0.5u/5u, the core unit |
| Switches, LV PMOS, drain side | `MSF`, `MS3` to `MS0`, m = 2 in every group, between the unit drains `vdf`, `vd3` to `vd0` and `iout` | 0.5u/5u, the unit device |
| Dummy | `MPD` (every terminal on `vdd`) | 0.5u/5u, m=40, set by the layout |

The switch gates of group k are `di_trim_b[k]`, the fixed switches are tied to `vss`. Sizes follow the user's grid (L from minimum, 0.5u, 1u, 5u, 10u, W in multiples of 0.5u), no HV device, 11 MOSFET symbols and no logic.

## Decisions

- **Unit.** The core PMOS unit, 0.5u/5u (same W/L as 0.7u/7u, 2.5 um2 against 4.9 um2), so the output is a plain current mirror on `vz`. The output unit carries 8.33 nA against 25 nA per core unit, so the core mirror has 24 legs per side (see the `bias_gm` task). At 0.7u/7u a 3x length stack tracked the core worse than the identical unit (0.990 to 1.009 against 0.999 to 1.001) and loaded `vz` more.
- **Switch on the drain side.** The unit sources stay on `vdd` and the unit gate voltage is `vz` whatever the code, so the switch adds no source degeneration to the 8.33 nA units.
- **One switch element of 2 unit devices per group** (user, for the lower area), every element at least 2 units, the switch device is the unit device, LV. The first version had one switch per unit (m = group size), the comparison is below.
- **No decoding logic and no buffers** (user: the trim bits are static, dedicated buffers are a luxury). With a NOR2 per bit, a shared inverter and `di_ena` in the cell the start-up SOA failed by 0.1 to 0.3 V, see below. Without them it passes the 1.6 V limit.

## Sizing

`scripts/sizing/size_bias_trim.ipynb` derives the groups, the unit and the switch element from the spec with the gm/ID tables and compares them with the schematic. It was written after the schematic and reproduces it. Its switch drop on the 16-unit groups is 22 mV at a pin of 0.8 V and 246 mV at 0.35 V, which moves the unit current by 0.27 % (model).

## Testbenches

All in `testbenches/xschem/`, netlisted by xschem and run with ngspice. Each prints `BT <name> <value>` lines. The reference is an ideal one: 24 core units diode-connected on a 200 nA ideal source, so `vz` is what the core mirror makes, plus a clamp PMOS (0.5u/5u, gate `di_ena` of the bench) from `vz` to `vdd` like `MCL1` of `bias_gm`. The output is held by `VLO` at 0.6 V, the typical level of the OTA bias pin. `code`, `ena` and `vout` are `.param` values, `di_trim_b[k]` is VDD times (1 - bit k of code).

| Testbench | What it runs |
| --- | --- |
| `bias_trim_tb_code` | operating point, output current, ratio to the ideal, summed current of the open trim switches |
| `bias_trim_tb_rout` | `VLO` swept 0.25 to 0.9 V, current span and output resistance over 0.35 to 0.8 V |
| `bias_trim_tb_mc` | mismatch Monte Carlo of the whole cell, 200 runs |
| `bias_trim_tb_pair` | mismatch Monte Carlo of mu reference units against mu output units with mu switches, `mu` 1 and 2 |
| `bias_trim_tb_startup` | VDD ramp, then `di_ena` low for 1 us, 10 us and 100 us (clamp and reference current of the bench, the reference follows `di_ena` through 5 us like the core restart), `di_trim_b` ramping with VDD, the OTA bias stack (`ota_fcasc2_nbiascasc` and its enable) as load, `save all` for the SOA check |

`scripts/sweep.py` (`make sim-sweep`) reruns these netlists with the corner, temperature, supply and `.param` lines replaced and writes `testbenches/xschem/simulations/sweep/summary.md`. Sets: `code`, `rout`, `off`, `mc`, `pair`, `soa`. `scripts/soa_variants.py` holds netlist patches for SOA experiments (`BT_SOA_VARIANT=<name>`).

## Results

One switch element of 2 unit devices per group ("m=2", the cell as drawn) against one switch per unit ("per unit", m = group size, earlier version of this cell, results in `testbenches/xschem/simulations/sweep_persw/`). Runs: `code` 400 each, `vd` 2, `off` 8, `rout` 45, `soa` 30, 0 failed or unmeasured.

| | per unit | m=2 |
| --- | --- | --- |
| Switch devices, gate area | 46 (115 um2) | 10 (25 um2) |
| Cell gate area without dummies (units 115 um2) | 230 um2 | 140 um2 |
| Code sweep, 25 cases x 16 codes, output over ideal | 1.0074 to 1.0586 (code 0), 1.0074 to 1.0232 (code 15) | 1.0071 to 1.0258 (code 0), 1.0072 to 1.0172 (code 15) |
| Monotonic over code 0 to 15 | 25 of 25 | 25 of 25 |
| Step to the next code (ideal 12.5 % at code 0, 4.5 % at code 15) | 4.46 to 12.50 % | 4.48 to 12.51 % |
| Group error, fixed (16 units) | 0.74 to 5.86 % | 0.70 to 2.58 % |
| Group error, bit 0 / 1 / 2 / 3 (2 / 4 / 8 / 16 units) | 0.20 to 1.48 % for all four | 0.20 to 1.48 / 0.74 to 1.35 / 0.73 to 1.38 / 0.71 to 1.41 % |
| Group drain `vd` at ss, -40 C, 1.45 V, `iout` 0.8 V, code 15 (fixed / bit 3 / 2 / 1 / 0) | 0.8022 V for all | 0.8170 / 0.8170 / 0.8086 / 0.8044 / 0.8022 V |
| Unit V_SD there | 0.648 V for all | 0.633 / 0.633 / 0.641 / 0.646 / 0.648 V |
| Leakage ff/125 C, `di_ena` low, code 4 / 15 | 9.80 nA / 13.66 nA | 6.74 nA / 11.49 nA |
| Leakage ff/125 C, `di_ena` high, code 0, 30 units behind open switches | 3.18 nA (106 pA per unit) | 0.86 nA (28.5 pA per unit) |
| `rout` current span over 0.35 to 0.8 V at 24 units, ff/125 C | 2.87 % | 0.88 % |
| `rout` smallest average r_out, code 0 / 4 / 15 | 0.10 / 0.07 / 0.04 GOhm | 0.38 / 0.25 / 0.12 GOhm |
| Start-up SOA, 30 runs, switch peak Vds / oxide | 1.495 V / 1.550 V, 0 of 30 over | **1.694 V / 1.687 V, 12 of 30 above Vds 1.6 V, 10 of 30 above oxide 1.65 V** |
| Start-up SOA, unit peak Vds | 1.312 V | 1.318 V |
| Lowest `iout` in the start-up bench | 0 V | -0.137 V |

**Group errors above 1 % occur in both variants.** The error is the current of a group over its ideal n x 200 nA / 24. Largest values: fixed group 2.58 % (m=2) against 5.86 % (per unit), the bit groups up to 1.48 %. Part of it is the same in both, the diode reference sits at V_SD 0.33 V against 0.6 V at the output, the rest is the leakage of the drain junctions at ff/125 C and the supply and temperature spread. The m=2 version has the smaller spread (fixed group 1.87 % against 5.11 % peak to peak). What the m=2 switch adds is the drain voltage rise of the large groups: 15 mV on the 16-unit groups (0.817 V against 0.802 V), which lowers the unit V_SD by 2.3 % and moves the unit current by about 0.2 to 0.4 %, much less than the 75 mV expected from n U_T ln 8 for a gate at 0 V.

**Start-up SOA, m=2:** fails the robust limits by 0.04 V for about 10 ns in 10 to 12 of 30 runs (switch `MS3` and its twins, Vgs 0.00 V, off, at the `di_ena` fall in the fs/125 C and ff/125 C corners). Mechanism: the OTA bias pin dips below vss at that edge (-0.137 V against 0 V with the per-unit switches) while the open switches have their gate at `vdd`, so Vgd and Vds are `vdd` plus the dip, 1.687 V against 1.65 V. The dip gets shallower as the switch element gets wider (extra runs at the fs/125 C and ff/125 C corners, 10 us ramp, 4 runs each, not the full set): m=4 gives -0.088 V, Vds 1.652 V, oxide 1.651 V and is still over in 2 of 4 runs, m=8 gives no dip, Vds 1.558 V, 0 of 4 over. Why a narrower switch lets the pin dip deeper was not isolated (inference: less switch and drain-junction capacitance and conductance on the pin). The units stay at 1.32 V. The fallback limit of 2.0 V Vds is met, the oxide limit of 1.65 V is not.

**Area, m=2:** units 115 um2, switches 25 um2, dummies `MPD` m=40 100 um2, 240 um2 for the cell, no drivers. On `vz` 46 units 115 um2 here plus 60 units 150 um2 in the core mirror, 265 um2, against 137 um2 on `vz` at HEAD and 446 um2 in the first version. Each further copy adds 46 gates (115 um2) to `vz`.

## Pin capacitor (rounds 6 and 7)

The OTA's series enable switch `MNSW5` leaves its channel charge on the high-impedance bias pin at the `di_ena` edge, the pin dips below vss (-0.137 V with the m=2 switches) and the open switches see 1.69 V (oxide 1.687 V, 10 of 30 start-up runs over 1.65 V). A capacitor on `iout` fixes it. The cap does not live in this cell, `bias_gm` places it next to the instance. `MPD` is a plain dummy again. Scratch netlists of the start-up bench (OTA bias stack as load), 1 ngspice process, image `hpretl/iic-osic-tools:2026.08`, `BT_VARIANT=<name>` in `scripts/sweep.py`:

| | no cap | `MPD` gate on `iout` (to vdd, round 6) | HV NMOS 0.5u/10u m=2 to vss | HV NMOS m=4 to vss | LV NMOS 0.5u/10u m=2 to vss |
| --- | --- | --- | --- | --- | --- |
| Lowest `iout`, 30 runs | -0.137 V | 0.000 V | 0.000 V | 0.000 V | 0.000 V |
| Switch peak Vds, 30 runs | 1.694 V | 1.500 V | 1.547 V | 1.525 V | 1.525 V |
| Switch peak oxide | 1.687 V | 1.550 V | 1.550 V | 1.550 V | 1.550 V |
| Runs over Vds 1.6 V / oxide 1.65 V | 12 / 10 of 30 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Unit peak Vds | 1.318 V | 1.307 V | 1.318 V | 1.318 V | 1.307 V |
| Cap device peak oxide | | 1.486 V (`MPD`) | | | 1.115 V |
| Ripple vdd to `iout` at 100 kHz, tt/27, ff/125, ss/-40 | 0.019, 0.022, 0.029 | 0.041 at tt/27 | 0.018, 0.022, 0.029 | 0.018, 0.022, 0.029 | 0.018, 0.022, 0.029 |
| Ripple at 1 MHz | 0.097, 0.101, 0.089 | 0.213, 0.245, 0.195 | 0.092, 0.096, 0.084 | 0.087, 0.091, 0.079 | 0.079, 0.080, 0.074 |
| Ripple at 10 MHz | 0.153, 0.163, 0.150 | 0.326 at tt/27 | 0.136, 0.143, 0.132 | 0.122, 0.127, 0.117 | 0.104, 0.099, 0.104 |
| Gate leakage into `iout`, ff/125 C / tt/27 C | | +0.61 nA / +0.15 nA | none | none | -1.17 nA / -0.15 nA |
| Code sweep tt/27 C, output over ideal at codes 0 / 4 / 15 | 1.0090 / 1.0090 / 1.0090 | 1.0099 / 1.0096 / 1.0093 | 1.0090 / 1.0090 / 1.0090 | 1.0090 / 1.0090 / 1.0090 | 1.0079 / 1.0083 / 1.0086 |
| Cap gate area | | 5 um2 (dummy) | 10 um2 | 20 um2 | 10 um2 |

All variants: monotonic, group errors 0.85 to 0.91 % at tt/27 C (LV cap: fixed group 0.79 %, `MPD` to vdd: 0.99 %), step 4.54 to 12.5 %. The cap to vss divides the vdd coupling down (0.10 to 0.08 to 0.07 at 1 MHz, against 0.21 to 0.25 with `MPD` to vdd), the HV thick-oxide cap adds no gate leakage and no code shift, the LV cap sinks 1.17 nA at ff/125 C (0.57 % of the output). Recommendation: HV 0.5u/10u m=4 (Vds margin 0.075 V to 1.6 V, lowest ripple of the zero-leakage options), m=2 if the 10 um2 matter (margin 0.053 V). The effect of the cap on the dip depends on the size of the pin capacitance with the layout, the numbers above are for the schematic.

## Step response of the output after a +50 mV VDD step (task HC)

HC saw the output stay 2.6 % high (194.4 against 189.6 nA) for 1 ms after a +50 mV step of VDD at ff/wcs/125 C while the core nodes were back at their operating point, and guessed the floating drains of the open groups. **Not reproduced.** Bench `step` (ideal reference diode and 200 nA, code 4, ff/125 C, VDD 1.45 V to 1.50 V at 101 us and back at 1201 us, trim bits and clamp gate following VDD): the output moves by +0.14 % (204.33 to 204.61 nA) within 5 us and is back at 204.33 nA within 5 us after the step down. With the OTA bias stack as load and the reference switched by `di_ena` (`step2`, ff/125 C): 205.62, 205.96 (+0.17 %), 205.96 after 500 us, 205.61 after the step down, 205.62 after 500 us. tt/27 C: +0.07 %. The drains of the open groups follow `vdd` within 0.5 mV (1.4495 V to 1.4995 V and back, bits 0 and 3), the closed groups sit at the pin voltage plus 18 to 23 mV (0.6176 V and 0.6227 V against 0.6 V), `vz` follows the 50 mV of the ideal diode. There is no memory in `bias_trim`, so the tail HC sees is not the open groups. At ff/125 C a unit current changes by about 2.3 % per mV on `vz` (n U_T about 43 mV), so 2.6 % corresponds to about 1.1 mV of residual error on `vz` or on a core node that HC's check would not resolve (inference, not measured here). No fix proposed.

## History of the start-up SOA

Earlier versions of the cell had a NOR2 gate per trim bit and a shared inverter with `di_ena` as a pin, so a switch was on whenever `di_ena` was low. Those versions failed the 1.6 V Vds limit in 28 of 30 runs (peak 1.906 V) by two mechanisms: the switch gate edge kicks the floating unit drain through the gate-drain coupling (+0.36 V at turn-off, -0.36 V for about 1 ns at turn-on, 1.906 V on `MP0`, 1.764 V on `MP1`), and the series node of the NOR floats above `vdd` (1.745 to 1.766 V on `MPB2` for 3.5 us). Experiments on those versions: the PSP NQS switch `swnqs` has no effect on the transient in this ngspice build (identical results with it on, checked with a modified model library that was verified to be read, and in a three-device toy bench), `rfmode=1` changes the parasitics but not the picture, a 0.5u/5u NOR is worse (4.65 V), minimum-L and swapped NOR stacks were not needed any more. With the trim bits wired straight to the switch gates the gate edges are static, and the only kicks left are the `vz` edges onto the unit drains, which stay below 1.5 V.

## Layout

`layout/bias_trim_gen.py` writes `layout/bias_trim.gds` with KLayout (`make layout`), no hand-drawn geometry, one flat cell, 45.350 x 18.490 um (838.5 um2, the previous layout 48.770 x 21.490 um). It is placed as a GDS child at the bottom of `bias_gm`, which imports its strip geometry, column x, lanes and ring helper. `PLACE_ONLY=1` writes the placement without routing, `CHECK_CONTROL=1` proves a failing check stops the target.

- 12 strips of eight LV PMOS 0.5/5 fingers at 1.50 um pitch, one PCell with `ng = 8` per strip, so neighbouring fingers share a diffusion: a dummy strip, 10 rows, a dummy strip, an `MPD` finger at both ends of every strip (40 dummies). The top dummy strip is shared with the core mirror of bias_gm, so the nwell ring is open at the top and bias_gm closes it around both arrays. The ring is as wide as the start-up rows of bias_gm.
- Every row is mirror symmetric about the axis column, nets included. Two fingers share a diffusion only where the schematic gives them one node: vdd between unit pairs, the group drain inside a pair and between a unit and its switch, iout or a group drain between two switches.
  - Pair rows `D U U V V U U D`: a pair of group U on each side, a pair of group V on the axis.
  - Switch rows `D UF SF S3 S3 SF UF D` and `D U2 S2 S1 S1 S2 U2 D`: each outer switch shares its group drain with a unit, the inner pair shares the drain of its group on the axis, inner and outer switches share iout.
  - B0 row `D D U0 S0 S0 U0 D D`, iout on the axis.
- Rows from the bottom: dummy, B3/B3, F/F, B2/B1, switch row F and 3, B0, switch row 2 and 1, F/B3, B3/B1, B3/dummy, F/B2, dummy (outer pairs / axis pair). The order was searched over all row orders: F, B3, B2 and B1 have their centroid exactly on the array centre, B0 (one row) half a row (0.75 um) below it.
- Routing: three Metal2 tracks per row (vdd at y + 0.25, drains at y + 0.75, gates at y - 0.25), each a run of one net between landings of other nets. The iout pair of the switch rows and the vd0 pair of the B0 row join on the vdd track, which is free there. Metal3 lanes join the rows of a net (axis frame): vdd +-19.0, vz +-14.0, vd2 +-12.0, vdf +-10.76, vd3 +-9.5, di_trim_b[2] +-8.6, vss +-7.25, vd1 1.5, iout 0, di_trim_b[3] -1.5, di_trim_b[0] -3.0, di_trim_b[1] -4.5. vd2 of the axis column climbs to Metal4 and joins both vd2 lanes, the two vss lanes join on Metal4 under the bit lines, the trim bits leave on Metal4 at 1 um pitch to the right edge. Every vdd track ties the nwell ring at both sides (the bulk, not a supply path). Dummy gates are tied to a vdd column in Metal1. Every via has two cuts.
- Pins (cell frame, x from the left edge, axis at 22.675):
  - Top edge, Metal3: `vz` at x 8.675 and 36.675, `vdd` at x 3.675 and 41.675, `iout` at x 22.675.
  - Bottom edge, Metal3: `vdd` at x 3.675 and 41.675, `vss` at x 15.425 and 29.925.
  - Right edge, Metal4: `di_trim_b[3]` y 1.24, `[2]` y 2.24, `[1]` y 3.24, `[0]` y 4.24.
- Generator checks: every finger's source, drain and gate nets against the schematic, every row mirror symmetric, mirror XOR of Activ, GatPoly, Cont, pSD and NWell zero (Metal1 before routing only), units per device counted in fingers, shorts and spacing per net (euclidean), opens per net, lone vias, labels inside pins, pins on the outline, off-grid vertices, nothing outside the outline.

Checks in `registry.iic.jku.at:5000/iic-osic-tools:next` (image bb525d654d8d):
- KLayout DRC: macro level 0, `DRC_LEVEL=regular` (antenna included) only the chip-level density rules and `AFil.g`.
- Magic DRC: 0.
- KLayout LVS (deep): match.
- Magic LVS: match, its only property messages are `mm_ok`.
- Both extracted netlists reduce the strips to the schematic devices: with the MOSFETs combined in parallel by model, L, gate, bulk and source/drain pair, the multiset of (model, L, W) equals the schematic's for KLayout and for Magic.

PEX of this layout: see PEX below.

## PEX

Post-layout check of the cell (sanity check, not a characterisation). `make magic-pex EXT_MODE=3` of the strip layout in `registry.iic.jku.at:5000/iic-osic-tools:next` (image bb525d654d8d): full RC with the hierarchy-off rerun, every net pair scaled to the mode 2 run of the same layout (`macros/scripts/pex_rc_caps.py`), MINDELAY 0. `make pex-mixed` swaps the view into the benches and ties the capacitor-only node to vss through 1 TOhm. The benches `bias_trim_tb_code` (25 cases x 16 codes) and `bias_trim_tb_rout` (45 runs) were run through `scripts/sweep.py` on the laptop in the same image (ngspice-47) with `x1` on `bias_trim_pex`, the schematic as the reference in the same runs. 890 runs (445 per view), 0 failed to measure. The group-drain probes (`vdf` to `vd0`) and the switch-current probes of the code bench read device paths and nets that the PEX view does not have, so they are dropped.

| quantity | schematic | PEX |
| --- | --- | --- |
| output over ideal at code 0 / 4 / 15, min to max over the 25 cases | 1.0071 to 1.0258 / 1.0071 to 1.0214 / 1.0072 to 1.0172 | 1.0070 to 1.0257 / 1.0071 to 1.0214 / 1.0071 to 1.0172 |
| output at code 0 / 4 / 15 (nA) | 134.3 to 136.8 / 201.4 to 204.3 / 386.1 to 389.9 | same |
| monotonic over code 0 to 15, step to the next code | 25 of 25 cases, 4.48 to 12.51 % | same |
| group error, fixed / bit 0 / 1 / 2 / 3 (%) | 0.70 to 2.58 / 0.20 to 1.48 / 0.74 to 1.35 / 0.73 to 1.38 / 0.71 to 1.41 | same, bit 3 from 0.70 |
| `rout` current span over 0.35 to 0.8 V, worst case at code 0 / 4 / 15 (%) | 0.844 / 0.879 / 0.930 (ff 125 C) | same |
| `rout` smallest average r_out at code 0 / 4 / 15 (GOhm) | 0.38 / 0.25 / 0.12 | same |

Over the 400 code runs the largest difference of the output current to the schematic is 1.9e-5 relative (the previous layout 7.4e-6), over the 45 `rout` runs the span differs by at most 2.5e-4 and the smallest incremental r_out by 1.8e-3 relative. The schematic numbers equal those of the previous layout's runs. The benches are DC, so only the layout's device geometry and the wiring resistance can show in them, the wiring capacitance does not. The start-up SOA with the extracted wiring is in the `bias_gm` README, where the cell is part of the layout.

`bias_trim_tb_mc` was not run on the PEX view. The extracted devices carry no `mm_ok=1`, which the schematic sets on every device to switch its mismatch on (not tried on a PEX view), and one `m=24` schematic device is one mismatch sample where the layout has 24. `bias_trim_tb_pair` instantiates no `bias_trim` (it holds the reference, output and switch devices of one pair directly), so the layout does not enter it.

Checks of the RC view before trusting it. All 96 PMOS fingers of the schematic are in the extraction (48.0 um of total W at L = 5 um in both), the 8 ports are connected. Mode 3 has 330 resistors, 281 of them on `vdd` (2.2 kOhm summed), 33 on `vz`, 8 on `iout`, the rest on the trim bits and `vss`. Raw mode 3 holds 386.9 fF between nets against 147.4 fF in mode 2, the difference is Magic's `extresist` double count of the coupling of nets with a resistor network as substrate capacitance (here 101.9 fF on the substrate node alone), which the pair scaling removes.

## Open issues

- The group-level Monte Carlo is not rerun, it waits for the unit pick of the `bias_gm` task.
- Start-up SOA of the m=2 switch failed by 0.04 V for 10 ns without a pin capacitor, see Results. With `MCI` on the pin in `bias_gm` no start-up run is over the limits, on the schematic and on the PEX view (see the `bias_gm` README).
- Leakage with `di_ena` low is 6.7 nA at ff/125 C at code 4. The open groups' drains float then. In `bias_gm` the output pin is the OTA bias pin and the OTA is off.
- The pin capacitor (HV NMOS to vss, see above) lives in `bias_gm` and is wired there.
