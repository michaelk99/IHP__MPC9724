# ihp-sg13cmos5l Bias Generator (bias_gm)

Constant-current reference that sources 200 nA into the NMOS bias diode of `ota_fcasc2`, from VDD = 1.5 V (1.45 to 1.55 V).
The core is a mixed-threshold NMOS pair on the Pavan supply-rejection loop (Fig. 10(b) of R. Pavan, TCAS-II 69(5), 2022): `M2` is an LV diode on the resistor `R1`, `M1` is an HV device with the same gate `vx`.
The resistor voltage is V_R = dVth(HV - LV) + n U_T ln K, 422 mV at tt against 71 mV of the constant-gm core it replaces (review of 2026-10-16, V_R of at least 100 mV at every PVT point).
The output is the trimmable mirror `bias_trim` (its own macro) on the gate net `vz` of the core PMOS mirror, with no cascode.
The core legs run at 200 nA with 24 units each, so one unit of 0.5u/5u carries 8.33 nA, and the output is 24 units at code 4, 200 nA.
The numbers below read the core current from the PMOS leg `M4` and the output from `ibias_200n` at code 4.

| Pin | Direction | Level | Meaning |
| --- | --- | --- | --- |
| `vdd`, `vss` | inout | 1.45 to 1.55 V | supply and ground |
| `di_ena` | in | VDD logic, active high | low: every bias gate goes to its off rail and the output is off |
| `di_trim_b[3:0]` | in | VDD logic, active low | output code of `bias_trim`, code 4 is 1011, must ramp with `vdd` at power-up |
| `ibias_200n` | out, sourcing | 200 nA | NMOS bias diode of `ota_fcasc2` |
| `di_btest_en` | in | VDD logic, active high, reset 0, static | high: the test bank sources into `ibias_test`. A static setting: its edge kicks `ibias_200n` (up to -37 %), settled within 99 us |
| `ibias_test` | out, sourcing | equal to `ibias_200n`, 16 + 2 x code units, pad held at 0 to 0.8 V | test output for the lab, a second `bias_trim` on the same code |

## Circuit

Schematic: `schematic/xschem/bias_gm.sch`, one instance of `bias_trim` (`xtrim`, see `../bias_trim/README.md`) and the devices below.
The two start-up diodes are 13 series devices each, drawn as `MSA[12:0]` and `MSB[12:0]`.

| Group | Devices | Sizes |
| --- | --- | --- |
| PMOS mirror, LV | `M3` (copy leg into `vy`), `M4` (leg into the diode `M2`), both m=24, `M5` (diode, m=12), dummies `MPD` m=26 on vdd | 0.5u/5u per unit, 8.33 nA |
| HV device | `M1` (drain `vy`) | 4 x 0.5u/10u |
| LV diode | `M2` on `R1` (K = 1) | 4 x 0.5u/10u |
| Sense copy | `M6`, HV, gate `vy`, drain `vz` | 2 x 0.5u/10u |
| Compensation | `CC`, HV NMOS, drain, source and bulk on vss, gate through `RZ` to `vy` | 10u/10u, m=20, 2000 um2 (16 before the test bank), `RZ` rhigh 0.5u/43.9u, 130 kOhm at tt |
| Core resistor | `R1` rhigh at the 0.5 um minimum width, dummy stripes `RD1` to `RD4` with both ends on vss | 0.5u/735u, 2.17 MOhm at tt 27 C |
| Start-up | diodes `MSA`, `MSB` (LV PMOS, gate on the bottom node of each), dummies `MSD`, `MSDS`, sink `MSN` (HV, 2 units of the `M1` unit, gate `vx`), injector `MINJ` (HV NMOS, 2 x 4u/0.5u) | 0.5u/10u per series device |
| Enable | inverter `MPI`, `MNI`, clamps `MCL1` (`vz`, LV PMOS), `MCL3` (`vx`), `MCL4` (`vy`) HV, `MCL6` (`vs`) LV | see schematic |
| Pin cap | `MCI`, HV NMOS, gate on `ibias_200n`, drain, source and bulk on vss | 0.5u/10u, m=4 |
| Output | `xtrim` (`bias_trim`): fixed 16 units plus switched groups of 2, 4, 8, 16 of the same unit on `vz` | 16 + 2 x code units conduct |
| Test bank | `xtrim2` (`bias_trim`, same `vz` and `di_trim_b`, output `vbt`), switch `MBS` (LV PMOS, `vbt` to `ibias_test`, gate `d_btest_b`), inverter `MPBI` 0.5u/0.5u, `MNBI` 0.5u/5u from `di_btest_en` | `MBS` 0.5u/5u m=6 |

The dummies with every terminal on one net (`MPD`, `MSD`, `MSDS`, `MNDJ`, `MNDL`, `MNDS`, `MNDT`, `RD1` to `RD4`, and `MPD` of `bias_trim`) are declared in the LVS netlist like every other device. `MNDR` (drain and source on vnr, gate and bulk on vss) is an ordinary device that is off. The 2026.08 image deletes such a device from the layout netlist, so there KLayout LVS fails on them. A pre-release build of IIC-OSIC-TOOLS 2026.10 and Netgen keep them.
The dummy counts and sizes (`MPD`, `MSD`, `MSDS`, `MNDJ`, `MNDL`, `MNDR`, `MNDS`, `MNDT`, `RD1` to `RD4` with both ends on vss) are set by the layout, see Layout.

How it works and why it is built this way:

- **Core.** `M2` is an LV NMOS diode with `R1` in its source, so `vx` = V_GS2 + I R1. `M1` is an HV NMOS with the same gate and no resistor, and `M3` and `M4` push the same current into both. At the operating point the two currents are equal, so I R1 = V_GS1 - V_GS2, the threshold difference of the two oxides plus n U_T ln K of the size ratio. The resistor has to sit in the diode leg: with it in the other leg, the loop below has positive feedback and the op converges to a runaway state (found by simulation, 19.6 uA in the leg).
- **Loop.** `M6` is an HV copy of `M1` at the same current density (50 nA per unit) and drives the PMOS diode `M5`, whose gate `vz` sets `M3`, `M4` and the output units. It holds the drain of `M1` (`vy`) at the gate voltage `vx`, so `M3` and `M4` see the same V_SD whatever VDD does. `vy` - `vx` is -4.0 to -0.9 mV over the 135 PVT runs, and the current changes by at most 0.07 % over 1.45 to 1.55 V (the phase 1 core without the loop: 3.7 to 6.8 %/V).
- **K = 1.** `M1` and `M2` have the same total W/L, 4 units each, and `M6` is 2 units, each at least 2 units.
- **The unit is 0.5u/10u at W/L 0.2 in total.** The loop gain is gm4 R / nU_T times the gain of `M1`, and V_R of 422 mV puts gm4 R at about 13 (the old core: 2). A stronger inversion level of the HV and LV devices (W/L 0.2 instead of 0.8, I/Is about 4) cuts gm1 and the gate area on `vx`, which moves the `vx` pole out (a pole of R1 + 1/gm2 into the gates of `M1`, `M2`, `MSN`). Same `CC` of 14 units: phase margin -17 deg with 8 x 0.5u/5u, +13 deg with this unit. The HV and LV units have the same W and L, so `M1` and `M2` do not need an extra ratio.
- **Branch current 100 nA.** `M5` is 12 units, so with `M6` at the density of `M1` the branch carries 100 nA nominal, 67 to 158 nA over PVT. At the old W/L of 0.8 and `CC` of 14 units, branches of 100, 50 and 25 nA gave -13, -17 and -42 deg (the `vz` pole is gm5 over the gates of 91 units), so the branch is kept at 100 nA. A smaller branch would save 0.15 uW per 100 nA.
- **CC with a series resistor, 16 units, 1600 um2, 20 units with the test bank.** The 46 gates of `xtrim2` on `vz` took the post-layout minimum at 7 corners from 43.9 to 38.7 deg, 20 units bring it to 46.9 deg (see Verification status). `CC` on `vy` is the dominant pole (about 1 kHz), the `vx` pole (about 150 kHz) and the `vz` pole (about 250 kHz) are next. A plain `CC` needs 42 units, 4200 um2, for 49 deg (the unity-gain frequency is about 13 gm1 / (2 pi CC) at the V_R of this core, so `CC` scales with V_R). `RZ` of 130 kOhm in series puts a zero at 1/(2 pi RZ C), about 210 kHz for 5.8 pF, near the `vx` pole, and 16 units give 47.4 deg over the 135 PVT runs, 14 units 43.6 deg, 15 units 45.7 deg (RZ 43.9u) (the optimum of RZ is flat from 0.1 to 0.17 MOhm). An LV NMOS cap of 5 units would be 3x denser but leaks 38 nA into `vy` at ff/125 C (core current -5.5 %), so `CC` is HV. A Miller cap from `vy` to `vz` or from `vx` to `vy`, and a cap from `vz` to vdd, oscillated in a closed-loop transient at every size tried (ideal caps, 1 to 100 pF). `CC` is HV and on vss for the reason of the Pavan core: an LV NMOS cap leaks gate current into `vy`.
- **PMOS unit 0.5u/5u.** With the loop in place the 0.5u/10u unit gives the same supply slope and needed 56 units of plain `CC` for 43 deg against 42 units for 49 deg, and its restart is 15 to 20 % slower, see the table.
- **Process.** The 5 correlated MOS corners move the current by +-2 % only. The rhigh corners move it by -22 % (wcs) and +31 % (bcs), the HV and LV libraries are independent so a skew combination moves it by -22 % and +21 %, and global Monte Carlo is 11 % sigma. The trim has to absorb that.
- **Start-up.** Two diode-connected LV PMOS stacks (`MSA`, `MSB`) pull the sense node `vs` up while the core is off, and the HV injector `MINJ` (gate `vs`) then pulls `vz` down, which turns on `M3`, `M4` and `M5`. Once the core runs, `MSN` (gate `vx`) holds `vs` at 9 to 39 mV and the stack carries 14 to 38 nA. Without the injector the core does not start at all in the 12 control runs. The stack is always connected, a switch isolates its chain nodes and ngspice then swings them by volts.
- **HV injector.** The LV injector leaks 17 nA at ff/125 C into `vz`, the HV one 0.4 nA, and `vy` - `vx` is -26 mV with the LV one and -4 mV with the HV one at the worst corner. The HV one restarts slower: after a `di_ena` toggle at most 171 to 204 us at ss/-40 C for 4u/0.5u, 2u/1u and 1u/1u against 77 us for the LV one (0.5u/10u). The size does not set the time, the gate drive from the stack does. 4u/0.5u x 2 is the fastest tried. The output current of the core is the same to 0.04 % with either, because the loop absorbs the leakage.
- **Clamps.** `di_ena` low clamps `vz` to vdd and `vx`, `vy` and `vs` to vss. The clamps on `vx` and `vy` are HV because an LV NMOS leaks nA at ff/125 C on nodes that carry 100 nA.
- **Output.** `bias_trim` takes `vz` and sources its units straight from the core mirror, no cascode. The output is 0.998 to 1.046 of the core current over PVT (1.000 at tt 27 C).
- **Pin cap `MCI`.** The enable switch `MNSW5` of the OTA bias stack dumps charge on `ibias_200n` when `di_ena` falls. Without a cap the pin dips to -0.137 V and the trim switches see 1.69 V. `MCI` is an HV NMOS gate cap to vss on the pin, so it does not raise the vdd-to-pin ripple, and it leaks nothing (BT's scratch test: pin stays at 0 V, SOA 0 of 30, ripple 0.09 at 1 MHz).
- **Test bank.** `xtrim2` is a second `bias_trim` for the analog test pad of DSA1, so `ibias_test` follows the trim code like `ibias_200n`: test over `ibias_200n` 0.9998 to 1.0046 over 5 corners, 3 temperatures, codes 0, 4 and 15 with the pad at 0.4 V, mismatch sigma 1.39 % at code 4 (200 runs, tt). `bias_trim` has no enable, `di_ena` low turns both banks off through the `vz` clamp. `MBS` is 6 unit devices, the current density of the `bias_trim` switches at code 15. Off, it leaks at most 1.3 nA into a 0 V pad (ff/125 C). An LV NMOS switch with its gate at 0 V leaks 8.6 to 57 nA there and an HV NMOS does not pass 0.8 V on the pad at ss/-40 C, so the switch is a PMOS with an inverter. The 46 more gates on `vz` cost 4.3 to 8.2 deg of loop phase margin with `CC` of 16 units (minimum 46.4 deg at ff/-40 C on the schematic, 38.7 deg on the PEX view), so `CC` went to 20 units: minimum 54.0 deg on the schematic and 46.9 deg on the PEX view at 7 corners. Into an open pad (PDK pad cell) `ibias_test` rises to vdd with the bank in triode, and neither `ibias_200n` (0 ppm) nor the loop (0.1 deg) moves. A `di_btest_en` edge kicks `ibias_200n` by up to -37 % (open pad, ss/-40 C) and it settles within 99 us, so `di_btest_en` is a static setting. With `di_btest_en` low the pad sees only the reverse diode of the `MBS` drain in the n-well. With VDD off, keep the pad below 0.3 V like `vi` and `vcm` of dsm2_core, else that diode feeds vdd.
- **Device lengths.** The PDK symbols accept L up to 10 um, so long devices are series stacks.

## Sizing

`scripts/sizing/size_bias_gm.ipynb` derives the unit counts, V_R, R1 and CC from the spec with the gm/ID tables of the course and compares them with the schematic. It was written after the schematic and reproduces every drawn count. Its estimates of the poles (`vy` 0.14 kHz, `vx` 333 kHz) and of gm4 R (10.9) differ from the figures in Circuit, the simulated phase margin is what counts.

## Layout

`layout/bias_gm_gen.py` writes `layout/bias_gm.gds` with KLayout (`make layout`), no hand-drawn geometry. bias_gm is the right-hand column of dsm2_core floorplan option 1, upright, beside the signal column: 47.580 x 160.910 um (7656.1 um2, 47.580 x 129.350 um before the test bank). `bias_trim` is a GDS child (`../bias_trim/layout/bias_trim.gds`) placed twice, `xtrim` upright and `xtrim2` mirrored about x below it, everything else is flat. `PLACE_ONLY=1` writes the placement without routing, `LABELS=1` adds internal net labels for PEX probes (scratch only, with `OUT=`), `TRIM_GDS=` reads another bias_trim GDS, `CHECK_CONTROL=1` proves a failing check stops the target.

- Every array is rows of multi-finger strips, one PCell with `ng` per strip, so neighbouring fingers share a diffusion. Two fingers share one only where the schematic gives them one node: the vdd or vss source between unit pairs, the drain inside a pair, the internal node of a series stack, a dummy on its own rail. HV and LV fingers never share one.
- A dummy finger at both ends of every strip and a dummy strip below and above every matched array. The start-up strips end on chain nodes and carry no end dummies (not matched). CC ends in a 10u/1u finger and has 1u/10u dummy strips.
- One vertical symmetry axis through every block.
- Bottom to top:
  - `MBS` strip, eight LV PMOS 0.5/5 fingers `D S S S S S S D`: `vbt` on the outer columns and columns 1, 3, 5, 7, `ibias_test` on 2, 4 (axis) and 6, `MBSD` at both ends. A ring band below closes the nwell ring around it and `xtrim2`, its contacts on the 0.36 um lattice of the mirrored cell.
  - `xtrim2`, the bias_trim cell mirrored about x, its open ring side down, one pitch above the MBS strip. Its outline abuts the one of `xtrim`, ring band to ring band, and the bottom vdd and vss pins of `xtrim` touch its mirrored ones there.
  - `xtrim`, 12 strips of eight LV PMOS 0.5/5 fingers, see the bias_trim README.
  - Core mirror, 10 strips `D X X Y Y X X D` on the top dummy strip of bias_trim (shared by both arrays). X is a pair on each side, Y the pair on the axis, each pair shares its drain. Row types a = M3 / M5, b = M4 / M5, c = M3 / M4, d = M4 / M3 in the order `a d b d a b c a c b`, which puts M3, M4 and M5 on one centroid in x and y (searched over all row orders, equal second moment for M3 and M4). Then a dummy strip, `MCL1` at its left end. One nwell ring closes around bias_trim, the core and the start-up rows.
  - Start-up, 7 rows of two 0.5/10 strips of two fingers: `MSA` a serpentine on the left, `MSB` its mirror, joined across the axis in the top row, `MSD` and `MSDS` at the chain ends in the bottom row. The 1.6 um axis gap holds `MPI` in the bottom row and an n-tap from row 1 into the ring top band (LU.a for the core and the start-up).
  - psub band.
  - NMOS, 8 strips of four 0.5/10 fingers: an LV dummy strip, `M2` (LV), `M1`, `M6`, `MSN`, `M1` (HV), `M2`, an LV dummy strip. `M1` and `M2` share one centroid, `M6` and `MSN` are `M1` units in the rows between. The HV strips end in `MNDJ` (left) and `MCI` (right, next to the ibias_200n lane), the `M2` strips in `MNDR` on vnr (gate on vss, off). Side columns: `MNI`, `MCL3` (both turned by 90 degrees), `MINJ` on the left, `MCL6`, `MCL4`, `MINJ` on the right. The clamp sources sit on the vss source tracks of rows 0 and 2.
  - R1, 23 rows of horizontal rhigh stripes in two halves: a dummy row, 21 rows of R1 (42 x 17.5 um, chained in Metal1 up the left half from the left outer head and down the right half), a dummy row, a 2.75 um dummy stripe (`RD3`) in line at the outer end of every row.
  - RZ, 4 rows: a dummy row, two rows of RZ (4 x 10.975 um), a dummy row, a 9.28 um dummy stripe (`RD4`) in line at the outer end of every row.
  - psub band.
  - CC, 5 strips of four HV NMOS 10/10 fingers, two below and three above a psub band (a gate strap in each gap between strips of a group), an `MNDS` (10u/1u) at both strip ends, an `MNDT` strip (four 1u/10u fingers) below and above.
- Latch-up: the axis n-tap of the start-up rows (LU.a), psub bands under CC and between its row pairs (LU.b).
- Routing: per strip row three Metal2 tracks (sources at y + 0.25, drains at y + 0.75, gates at y - 0.25), each a run of one net between landings of other nets. Metal3 lanes per net, Metal4 for the joins, the side-column jogs and the pins. Dummies are tied locally in Metal1. The R1 and RZ heads are joined in Metal1, the dummy heads on vss. Every via has two cuts.
- Metal3 lanes (axis frame): vss +-20.0 (bottom to top), vdd +-19.0 (the left one on to the vdd pin), ibias_200n 17.5, vz +-14.0 (the right one on to the NMOS block), vx +-12.0 and -1.5, vy +-10.76 and 1.5, vs 3.0, vz 0 (core axis column), d_en_b -4.5, vt1 -7.5, di_ena -16.5, vnr -17.8, net1 11.955 (RZ to the CC gate tracks), d_btest_b 5.5 (MBS gates on to the MPBI and MNBI drains), di_btest_en 16.5 (top pin to the MNBI and MPBI gates), vbt 0 (iout of `xtrim2` into the MBS strip), the four trim bit joins 15.25 to 17.5 (from the right-edge lines of `xtrim` down to the mirrored lines of `xtrim2`).
- Test bank: `MPBI` is the right end finger of the core dummy strip (the mirror of `MCL1`), `MNBI` the two inner fingers of the bottom LV dummy strip of the NMOS block. vz reaches `xtrim2` on a Metal4 line at x -14 from its bottom vz pin to the top vz pin of `xtrim`. The vss pins of both cells meet at the abutment and take vss on a Metal4 line from the right vss lane. vdd enters `xtrim2` from the bottom supply lines on the vdd lanes +-19. ibias_test leaves the MBS strip on Metal4 at y 2.53 to the right edge, with vss lines 0.70 um above and below.
- ibias_200n leaves the bias_trim pin on Metal4 at the bottom of the core and runs up its own lane to the left-edge pin on Metal4 between the two vss pin lines, which run on over the lane as its shield. The vss lane stands outside it. The MCI gates land on it in the HV rows. di_ena stays on the left half. d_en_b reaches the side columns on two Metal4 jogs at the bottom of the NMOS block, and the HV clamp gates join it on Metal3 inside the side columns, so no d_en_b runs beside the vx and vy jogs of the HV clamp drains. A 1.4 um vss Metal2 strip lies under the di_ena lane over R1, RZ and CC, open at the CC gate tracks.
- Rings: nwell ring on vdd, psub ring and bands on vss, unlabelled (tap extraction on), tied to vdd and vss but never a supply path.
- Pins (outline frame, x from the left edge, axis at 23.79):
  - Left edge, Metal4: `vss` (1.0 um) at y 159.56, `ibias_200n` (0.29 um) at y 158.56, `vss` (1.0 um) at y 157.56, `di_ena` at y 156.56, `vdd` (1.0 um) at y 155.56. ibias_200n has vss on both sides.
  - Top edge, Metal3: `di_btest_en` (0.29 um) at x 40.29.
  - Bottom edge, Metal3 stripes 2 um wide: `vss` at x 7.79 and 39.79, `vdd` at x 12.79 and 34.79.
  - Right edge, Metal4: `ibias_test` (0.29 um) at y 2.53, `di_trim_b[3]` y 23.20, `[2]` y 24.20, `[1]` y 25.20, `[0]` y 26.20.
- Generator checks:
  - every finger's two columns carry the source and drain nets of its device
  - mirror XOR of Activ, GatPoly, Cont, pSD, NWell and ThickGateOx (and EXTBlock, PolyRes) zero with an empty allow-list, Metal1 in the check before routing only (the routing is net-dependent)
  - units per device counted in fingers and stripes against the schematic, LV Activ against TGO.b
  - shorts and spacing per net (euclidean), opens per net, lone vias, labels inside pins, pins on the outline, off-grid vertices, nothing outside the outline
  - empty area 2.0 % of the outline (Activ, GatPoly, PolyRes, Cont, Metal1 to Metal4 grown by 0.25 um, taps as empty), build limit 8 %
  - same-net gaps under the metal spacing are closed in the build (0.149 um2)

Checks in `registry.iic.jku.at:5000/iic-osic-tools:next` (image bb525d654d8d):
- KLayout DRC (rerun with the test bank): macro level 0, `DRC_LEVEL=regular` (antenna included) only the chip-level density rules (`M1.j` to `M4.j`, `TM1.c`).
- Magic DRC: 0 (rerun with the test bank).
- KLayout LVS (deep, taps on): match (rerun with the test bank, 2026-10-22).
- Magic LVS: match (rerun with the test bank). Its only property messages are `mm_ok`, the schematic-only Monte Carlo flag, as in every macro of this repo.
- Both extracted netlists reduce the strips to the schematic devices (checked on the layout before the test bank, not rerun): with the MOSFETs combined in parallel by model, L, gate, bulk and source/drain pair, the multiset of (model, L, W) equals the schematic's for KLayout and for Magic, every finger counted. The KLayout extraction folds R1 into one 0.5u/735u and RZ into one 0.5u/43.9u device.

The dummies with every terminal on one net are kept by both LVS flows in this image.

PEX against the schematic (sanity check, not a characterisation), on the layout before the test bank (`xtrim2`, `MBS`), not rerun. `make magic-pex EXT_MODE=3` (full RC with the hierarchy-off rerun, every net pair scaled to the mode 2 run of the same layout by `macros/scripts/pex_rc_caps.py`, MINDELAY 0) in `registry.iic.jku.at:5000/iic-osic-tools:next` (image bb525d654d8d, Magic 8.3.684), on a copy of the GDS written with `LABELS=1` for the internal net names (XOR against `layout/bias_gm.gds` 0 um2 on all 29 layers). Between nets 755.1 fF after the scaling (raw mode 3 1284.2 fF, the previous layout 837.7 fF), 1406 resistors. `scripts/pex_mixed.py` ties the 108 capacitor-only nodes (the rhigh bodies) to ground by 1 TOhm. The benches ran on an arm64 server in the same tag (image 0ad78d950901, ngspice-47 on both hosts, `bias_gm_tb_op` at tt gives 193.714 nA, 420.674 mV V_R on both). The schematic is the reference in the same runs. `bias_gm_tb_op` has its device-current probes dropped, the loop is broken by moving the gates of the two `M6` devices onto their own net behind the AC source. Runs per view: 6 op, 6 rout, 1 noise, 6 + 135 loop, 60 start-up ramps. Failed to measure: one start-up ramp of the schematic (`su_10u_fs_typ_m40_1.55_en1`, no convergence with either aid), 0 of the PEX view. 7 start-up runs of each view needed a convergence aid.

The schematic loop numbers are 0.3 to 0.4 deg below those of the previous README (57.5 against 57.9 deg at tt), the dummies of this layout are in the schematic too (`MNDR` on vnr). The previous layout's column is its pair-scaled mode 3 view (commit 1af74d9).

| quantity | schematic | this layout | previous layout |
| --- | --- | --- | --- |
| ibias_200n tt 27 C 1.5 V (nA) | 193.71 | 192.45 (-0.65 %) | 192.51 (-0.62 %) |
| ss -40 C 1.45 V | 172.64 | 171.52 (-0.65 %) | 171.57 (-0.62 %) |
| ss 125 C 1.45 V | 234.16 | 232.60 (-0.67 %) | 232.68 (-0.64 %) |
| ff -40 C 1.45 V | 168.81 | 167.72 (-0.65 %) | 167.77 (-0.62 %) |
| ff 125 C 1.45 V | 229.61 | 228.10 (-0.66 %) | 228.16 (-0.63 %) |
| ff 125 C 1.55 V | 229.64 | 228.13 (-0.66 %) | 228.20 (-0.63 %) |
| V_R tt (mV) / vy - vx (mV) / own power (uW) | 420.7 / -1.76 / 0.760 | 420.4 / -1.77 / 0.755 | 420.4 / -1.77 / 0.756 |
| rout worst span over 0.35 to 0.8 V (ff 125 C 1.45 V, %) | 0.832 | 0.836 | 0.836 |
| rout smallest incremental / average r_out (ff 125 C 1.45 V, GOhm) | 0.14 / 0.23 | 0.14 / 0.23 | 0.14 / 0.23 |
| noise tt 1 Hz / 1 kHz / 100 kHz / 1 MHz (pA/rtHz) | 24.5 / 0.933 / 0.559 / 0.273 | 24.4 / 0.929 / 0.589 / 0.242 | 24.4 / 0.929 / 0.590 / 0.229 |
| loop tt, phase margin (deg) / unity-gain (kHz) | 57.5 / 240 | 48.2 / 200 | 47.8 / 198 |
| loop 135 PVT, phase margin (deg) | 46.9 to 65.4 | 40.9 to 56.3 | 40.7 to 55.8 |
| loop 135 PVT, unity-gain (kHz) / gain margin (dB) | 150 to 325 / at least 10.1 | 131 to 265 / at least 9.7 | 130 to 262 |
| start-up, worst settling to 1 %, event 0 / events 1 to 4 (us) | 52.5 / 67.4 | 34.5 / 79.5 | 35.5 / 81.7 |
| start-up, lowest / highest final ibias_200n (nA) | 168.8 / 234.2 | 167.7 / 232.7 | 167.7 / 232.7 |
| start-up SOA, LV Vds / LV oxide peak (V), runs over 1.6 / 1.65 V | 1.575 / 1.592, 0 | 1.567 / 1.583, 0 | 1.569 / 1.585, 0 |
| start-up SOA, HV Vds / HV oxide peak (V), runs over 3.3 V | 1.579 / 1.597, 0 | 1.573 / 1.598, 0 | 1.572 / 1.602, 0 |

The op change is the same at every corner, so it is device geometry: R1 is 42 stripes, 41 more head contact pairs than the single 735 um stripe of the schematic (the previous layout, 40 stripes, gave -0.62 %, inference). The phase margin loss to the schematic is -10.3 to -5.9 deg over the 135 conditions, mean -8.7 deg, against -11.2 to -6.4 deg, mean -9.4 deg, on the previous layout. The SOA rows cover bias_gm and bias_trim together, the worst LV device is `M3` (drain `vy`, gate `vz`), whose drain overshoots VDD at the `di_ena` edge.

Wiring capacitance per net from the labelled C-coupled extraction (mode 2, fF, every capacitor on the net summed): vz 217.8, net1 195.9, vx 50.6, vs 35.2, ibias_200n 32.3, vy 28.7, vnr 15.4. The previous layout's labelled mode 2 extraction (before its ibias_200n rerouting) had vz 238.3, vx 60.8, vs 43.8, vy 34.4. The 20 fF less on `vz` and 10 fF less on `vx` show as 0.7 deg more phase margin against the schematic on average (sim). The previous README's capacitor-removal runs (all `vz` caps +4.1 deg, all `vx` caps +6.8 deg at tt) would predict about 1.5 deg, so another part of the wiring takes some of it back (inference, not separated).

A first routing of this layout took the d_en_b join of the two HV clamp gates on Metal4 across the NMOS block beside the vx and vy jogs: d_en_b to vy 1.59 fF, and the start-up SOA rose to 1.597 V LV Vds (limit 1.6 V, 0 runs over) and 1.613 V LV oxide on `M3`, from `vy` kicked above VDD at the `di_ena` edge. The join on Metal3 inside the side columns brought it back to the table (d_en_b to vy 0.13 fF).

Coupling of ibias_200n (same extraction, fF): vss 19.43, vdd 2.50, net1 1.77, vz 1.66, di_trim_b[1] 1.34, di_trim_b[3] 0.94, vs 0.54, vnr 0.24, di_trim_b[0] 0.21, vy 0.19, di_trim_b[2] 0.09, d_en_b 0.06, di_ena 0, total 32.31. The trim bits are static. Other couplings of the digital nets: d_en_b to vs 1.50, vx 0.74, vt1 0.57, vy 0.13, di_ena to net1 1.23, vx 0.87, vt1 0.73, vnr 0.42. All of these nodes are clamped while di_ena is low, so d_en_b only moves at the enable edges (inference).

Magic's full-RC extraction books the coupling of every net with a resistor network a second time as capacitance to the substrate (raw mode 3 1284.2 fF against 755.1 fF in mode 2 here), which `make magic-pex EXT_MODE=3` corrects. On the unlabelled repo GDS some net pairs come back as capacitors on bare nodes, as before. The joint check with `ota_fcasc2` was not rerun on this layout. `bias_gm_tb_mc` was not run on the PEX view, the extracted devices carry no `mm_ok=1` and one `m=24` schematic device is one mismatch sample where the layout has 24.

## Verification status

PEX of the layout with the test bank and `CC` of 20 units (2026-10-22): `make magic-pex EXT_MODE=3` (pair-scaled to mode 2, MINDELAY 0) on a `LABELS=1` copy of the GDS (XOR against `layout/bias_gm.gds` 0 um2 on 26 layers) in `registry.iic.jku.at:5000/iic-osic-tools:next` (image bb525d654d8d), mixed view by `make pex-mixed`. 650 net pairs scaled, between nets 993.9 fF (raw mode 3 1793.6 fF, 755.1 fF before the test bank). Bench `bias_gm_tb_btest`, code 4, loop broken at the gates of `M6` as in `g5.py`, bank off (`di_btest_en` low) and on (SMU at 0.5 V). Sanity checks, not characterisation.

| corner | schematic off / on | PEX off / on | PEX - schematic (off) | PEX, CC 16 with the bank | PEX before the bank (CC 16) |
| --- | --- | --- | --- | --- | --- |
| tt 27 C 1.5 V | 60.3 / 61.0 | 51.3 / 51.8 | -9.0 | 41.8 | 48.2 |
| ss 125 C 1.45 V | 64.6 / 65.4 | 55.9 / 56.5 | -8.7 | 46.5 | 53.8 |
| ss -40 C 1.45 V | 55.4 / 55.8 | 47.8 / 48.2 | -7.6 | 39.3 | 44.8 |
| ff -40 C 1.55 V | 54.0 / 54.3 | 46.9 / 47.2 | -7.1 | 38.7 | 43.9 |
| ff 125 C 1.55 V | 64.9 / 65.8 | 56.3 / 56.9 | -8.6 | 46.9 | 54.2 |
| sf 27 C 1.5 V | 60.2 / 60.9 | 51.1 / 51.7 | -9.1 | 41.6 | 48.0 |
| fs 27 C 1.5 V | 60.4 / 61.1 | 51.4 / 51.9 | -9.0 | 41.9 | 48.3 |

Phase margin in deg. Minimum on the PEX view 46.9 deg (ff -40 C, bank off), 3.0 deg above the layout before the test bank. Unity-gain frequency on the PEX view 111 to 198 kHz (bank off). Op at tt 27 C 1.5 V: ibias_200n 192.45 nA on the PEX view (193.71 nA schematic, -0.65 %), test current 192.53 nA (bank on), 8.9 pA into the pad with the bank off.

Start-up on the schematic with `CC` of 20 units (10 us VDD ramp, di_ena following VDD, then di_ena off for 1 us, settling of ibias_200n to 1 %, bank off / on into the SMU, us): tt 27 C 28.4 / 27.5 after the ramp and 38.1 / 38.1 after the toggle, ss -40 C 75.6 / 74.0 and 131.1 / 131.1, ff 125 C 20.1 / 20.0 and 27.3 / 27.4, ss 125 C 26.9 / 26.8 and 37.8 / 37.8, ff -40 C 31.6 / 30.4 and 44.8 / 44.3. Against 16 units (bank on) that is 2.7 to 11.7 us more after the ramp and 1.8 to 4.5 us after the toggle. Final ibias_200n unchanged, the test current equals ibias_200n within 0.8 nA.

## Testbenches

The benches, `scripts/g5.py`, the CACE templates and the joint bench of `macros/ota_fcasc2` drive `di_trim_b` active low (VDD x (1 - bit), code 4 is 1011), probe the HV injector `xminj` and `xm1` as the core current, and were rerun on this core in phase 3.

All in `testbenches/xschem/`, netlisted by xschem and run with ngspice. Each prints `G5 <name> <value>` lines. The trim word is the `.param code` of every bench (default 4, 200 nA) and drives `di_trim_b[3:0]` through four sources in the model block, in `bias_gm_tb_startup` through behavioural sources that follow `v(vdd)`, so the bits ramp with the supply. The load of `ibias_200n` is the real bias diode stack of `ota_fcasc2`, the cells `ota_fcasc2_nbiascasc` and `ota_fcasc2_ena` from `macros/ota_fcasc2` (their outputs held at 0.75 V), behind a 0 V meter source. The `xschemrc` files of the benches and of the CACE templates add that folder to the symbol path. The joint bench with the whole OTA is `ota_fcasc2_top_tb_biasgm` in `macros/ota_fcasc2`. At tt, 27 C, 1.5 V `bias_gm_tb_op` gives 191.35 nA at 0.605 V on `ibias_200n`, and VACASK gives the same in the `sc_int2` noise bench.

| Testbench | What it runs |
| --- | --- |
| `bias_gm_tb_op` | operating point from the zero-current state (`.nodeset` with `vx`, `vy`, `vs` at 0 and `vz` at VDD), output and core current, V_R across R1, vy - vx, diode voltage, power, injector and stack current |
| `bias_gm_tb_rout` | output held by a source swept 0.25 to 0.9 V, current span and output resistance over 0.35 to 0.8 V, the range of the OTA bias pin |
| `bias_gm_tb_startup` | VDD ramp, then `di_ena` off for 1 us, 10 us, 100 us and 1 ms, settling to 1 % after each event, residual output current and bias_gm supply current (meter `VDB`) while off, `save all` for the SOA check |
| `bias_gm_tb_noise` | output current noise |
| `bias_gm_tb_mc` | mismatch Monte Carlo, 200 runs |
| `bias_gm_tb_btest` | the op bench with the test pad: `VBT` drives `di_btest_en` (`.param btest`), 5 pF on the pin and 587 Ohm to the SMU `VPAD` (`.param vpad`), `RBRD` the 1 MOhm of the board (`.param rbrd`, 1T while `VPAD` is there), then `VPAD` swept 0 to 0.8 V |

`scripts/g5.py` (`--code N` sets the trim word, the `code` set sweeps 0 to 15) reruns these netlists over PVT (5 MOS corners, 3 rhigh corners, -40/27/125 C, 1.45/1.5/1.55 V), runs `macros/scripts/soa_check.py` on the ramps at 1.55 V, and writes `testbenches/xschem/simulations/g5/summary.md`. Three of its sets edit the `bias_gm_tb_op` netlist instead of having a bench of their own:

- `loop`: a series AC source between `vy` and the gate of `M6` inside the DUT, T = -v(vy)/v(g6), 135 corners. The gate of `M6` is the only load on that side, a few fF against `CC`, so voltage injection gives the loop gain directly.
- `vstep`: VDD steps 1.45 to 1.50 V and back with 1 us edges, the trim word follows the supply (a static high leaves the off switches of `bias_trim` 50 mV on and adds 1.4 nA at ff/125 C, see Results).
- `sens`: temperature curve -40 to 125 C and supply slope at tt.
- `btest`: pad sweeps of `bias_gm_tb_btest` at codes 0, 4 and 15 with the bank on and at code 4 off (5 corners, 3 temperatures, 1.45 and 1.55 V), a mismatch Monte Carlo of test over `ibias_200n` (tt, codes 4 and 15, 200 runs), the loop gain at 7 corners (tt 27, ss and ff at -40 and 125, sf and fs at 27 C) with the bank removed, off, into the SMU and into 1 MOhm, and the start-up bench up to the 1 us `di_ena` toggle with the pad model added to its netlist. The other benches tie `di_btest_en` and `ibias_test` to ground.
- `bopen`: the same benches with the pad open, modelled by the PDK `sg13cmos5l_IOPadAnalog` (secondary 587 Ohm, diodes and clamps to iovdd 3.3 V and ground) and 5 pF on the bond pad: `ibias_200n` against the SMU case at codes 4 and 15, where `ibias_test` settles, loop gain, a `di_btest_en` toggle in transient, start-up.

The Monte Carlo set also runs with only `M1` and `M2` mismatched (`mm_ok=1` on those two, 0 everywhere else) and with only the bias_gm and bias_trim devices mismatched.

The CACE datasheet `verification/cace/bias_gm.yaml` has `op_params` (current window 144 to 288 nA, injector current at most 20 % of the `M5` current, V_R reported), `power_params` and `rout_params` (no limits).

```
make sim-xschem TB=bias_gm_tb_op    # one testbench at tt, 27 C
make sim-cace                       # CACE, three parameter sets, 3 parallel runs
make sim-g5                         # gate G5 with 3 parallel runs
make sim-g5 G5_ARGS=--quick         # typical rhigh only, two ramps, 30 Monte Carlo runs
```

xschem used to exit with 10 on this schematic although it wrote the netlist. The cause was `ibias_200n`: an `iopin` on the sheet against `dir=out` in `bias_gm.sym` ("iopin <--> out"). The symbol now says `inout` and netlisting exits 0. `sim-xschem` and `pex-mixed` still check for the netlist file instead of the exit code.

## Results

Final core: loop with `CC` of 16 units (20 since the test bank, see Verification status) and `RZ`, HV injector 4u/0.5u x 2, pin cap `MCI`, K = 1, PMOS unit 0.5u/5u, trim at code 4 (`di_trim_b` 1011). Image `hpretl/iic-osic-tools:2026.08`, `scripts/g5.py` and `macros/ota_fcasc2/scripts/sweep_biasgm.py` with one ngspice process. Bench and Monte Carlo numbers are sanity checks of the schematic with the `ota_fcasc2` bias stack as load, not characterisation results. R1 is 0.5u/735u, 3.0 % longer than the 713.5u that centred the core at 200 nA, so that the worst joint power clears 10 uW. The core sits 3.3 % low at tt/27 C (193.6 nA), which is what the trim is for. Sets that are DC only (rout, mc) ran with R1 at 713.5u and before `MCI` was drawn, start-up and noise with 713.5u, op, sens, vstep, loop, code and the joint check with 735u and `MCI`. Failed or unmeasured: 0 of 135 op, 135 rout, 135 loop, 30 vstep, 240 code, 3 noise, 135 joint PVT, 0 of 7 sequencing runs, 1 of 190 start-up runs (ss/bcs/-40 C, 10 us ramp, ngspice did not converge with `rshunt` or a 300 ns step), 19 start-up runs needed an aid.

| Row | Final core | Pavan core (git HEAD) |
| --- | --- | --- |
| Output at tt, 27 C, 1.5 V | 193.71 nA (core 193.56 nA), 200.26 nA with R1 at 713.5u | 197.0 nA |
| Output over 135 PVT runs | 0.659x to 1.539x of 200 nA, 30 outside 0.72x to 1.44x (R1 713.5u: 0.681x to 1.592x) | 0.660x to 1.546x, 30 outside |
| typical rhigh only | 0.844x to 1.171x | 0.801x to 1.264x |
| I(125 C)/I(-40 C), tt | 1.358 (171.3 to 232.6 nA) | 1.553 |
| V_R at tt 27 C, over PVT | 421 mV, 384 to 447 mV | 71 mV, 55 to 96 mV |
| dI/dVDD at -40 / 27 / 125 C, tt, output | -0.163 / -0.129 / +0.163 %/V (R1 713.5u run: +0.011 / +0.135 / +0.578, bias_trim was changed by BT in between) | +0.08 / +0.07 / +0.18 |
| Worst change over 1.45 to 1.55 V, output | 0.030 % (0.254 % at R1 713.5u) | 0.034 % |
| `vy` - `vx` over PVT | -4.0 to -0.9 mV | -9.8 to +1.2 mV |
| 50 mV VDD step in 1 us, output | at most 1.65 %, within 1 % after 1.1 us, DC change -0.012 to +0.015 % | 1.80 %, 1.1 us |
| Output over 0.35 to 0.8 V | span at most 1.61 %, incremental r_out at least 0.1 GOhm (ff/125 C) | span 0.64 %, 0.2 GOhm |
| Loop, 135 runs | PM 47.2 to 65.7 deg, unity gain 150 to 327 kHz, GM at least 10.0 dB, T(0) 55.4 to 64.0 dB, one crossing everywhere | PM 48.4 to 56.8 deg, 131 to 175 kHz, 11.3 dB |
| Mismatch sigma of the output, 200 runs | 1.60 % (core pair only 0.47 %, bias_gm and bias_trim only 1.76 %, sample noise about 8 %), bias pin 5.0 mV | 3.40 % (pair only 2.62 %) |
| Noise at 1 Hz / 1 kHz / 100 kHz / 1 MHz, tt 27 C | 25.2 pA / 0.96 pA / 0.56 pA / 280 fA per rtHz, 27.8 pA at 1 Hz at 125 C | 36.2 pA / 1.37 pA / n/a / 339 fA |
| Power at tt 27 C 1.5 V, from VDD / in `bias_gm`, over PVT from VDD | 1.051 / 0.760 uW, 0.699 to 1.713 uW | 1.072 / 0.776 uW, 0.70 to 1.87 uW |
| Trim code sweep 0 to 15 (240 runs) | output / (core (16 + 2 code) / 24) 0.999 to 1.012 at every code, 0.667x at code 0, 1.906x to 1.915x at code 15, monotonic in 15 of 15 cases | 0.998 to 1.003 |
| Start-up, settling to 1 % | after a ramp (10 us) at most 107 us, 100 us ramp 16.5 us, 1 and 10 ms ramps 0, after a `di_ena` event at most 127 us, `di_ena` 50 us after the ramp 177 us from the ramp (127 us after `di_ena`) | 17.8 us ramp, 60.6 us event, 104.3 us late |
| Start-up, stuck runs / control without the injector | 0 of 189 / the first ramp starts in 1 of 12, the others never start | 0 / 11 of 12 start without |
| Supply current while `di_ena` low, output current | 15.5 to 88.5 nA, at most 5.9 nA | 15.6 to 163 nA, 0.98 nA |
| Joint check with `ota_fcasc2`, worst tau (limit 30.5 ns) | 26.63 ns (ff/wcs/125 C/1.45 V) | 22.87 ns |
| Joint check, dcgain (limit 51.73 dB), swing (0.98 V), err_d (0.32 %) | 52.87 dB, 1.073 V, 0.303 % | 53.63 dB, 1.071 V, 0.281 % |
| **Joint check, power OTA + reference (limit 10 uW)** | **9.757 uW** (ss/bcs/125 C/1.55 V, reference 308 nA), 0 of 135 over, 2.4 % margin (R1 713.5u: 10.091 uW, 2 over) | 9.809 uW |

Reading the table:

1. **The supply rejection is back.** The core current changes by 0.07 % over the supply window (the leg, phase 2 data), the output by 0.03 % at the worst corner with R1 at 735u (0.25 % in the 713.5u run, which had a +0.58 %/V output slope at 125 C that the 735u run does not show, `bias_trim` was changed by BT between the two, cause not separated).
2. **Output resistance is worse than the Pavan core's** at ff/bcs/125 C, 0.1 GOhm and a 1.6 % span over the OTA pin range, from the leakage of the hot off-groups and the uncascoded units (inference, same mechanism as in the Pavan numbers with the new trim cell).
3. **Process spread,** from the phase 2 Monte Carlo of the same DC core (global MOS and rhigh draws, 200 runs per set, tt 27 C): local 0.66 % sigma, global MOS 7.9 %, global rhigh 7.5 %, both 10.8 %, global + local 11.3 % sigma with 0.678x to 1.367x of the core. Correlated corners move the current by +-2 %, rhigh corners by -22 % and +31 %, the LV/HV skew by -22 % and +21 %. Trim coverage with the fixed 16 + 2 x code units at 27 C, 1.5 V, R1 at 735u: 210 global + local Monte Carlo samples reach a residual of rms 2.4 %, max 4.7 %, using codes 2 to 12 and none at code 0 or 15, and the 75-point LV x HV x rhigh skew grid reaches rms 2.3 %, max 5.6 %, using codes 0 to 12, with 3 at code 0 (1 of them has a core above 300 nA, outside the reach) and none at code 15. Code 4, the default, is 2.4 % below the target on the Monte Carlo mean and 0.6 % on the skew grid mean.
4. **The 50 mV step offset of phase 2 was a bench artefact.** After a +50 mV step the output of `bias_gm_tb_op` settled 2.6 % above its DC value at ff/wcs/125 C (0.75 % with `MCI`). The core is not involved: at the end of the transient `vz`, `vx` and the currents of `M1` to `M5` equal the operating-point values within 0.002 mV and 0.001 %. The extra 1.38 nA is in the three off groups of `bias_trim` (their mirror units go from 0.21 to 0.66 nA each), because the trim sources of the bench stayed at the old logic high (1.45 V) while VDD rose to 1.50 V, so the off switches had Vsg = 50 mV. With the trim word following the supply the offset is 0.00 nA (184.414 nA in the operating point and at the end of the transient). `g5.py` now drives the trim word from `v(vdd)` in the step set. The only core node that differs is `vy`, by 0.29 mV, a balance at a high-impedance node that does not move any current.
5. **Joint check.** Every CACE limit passes with R1 at 735u: power 9.757 uW at ss/bcs/125 C/1.55 V (the reference delivers 308 nA), 0 of 135 runs over 10 uW, 2.4 % margin. The tightest other limits are tau 26.63 ns against 30.5 ns (ff/wcs/125 C/1.45 V), err_d 0.303 % against 0.32 % and dcgain 52.87 dB against 51.73 dB. With R1 at 713.5u the power was 10.091 uW and two runs (ss/bcs/125 C/1.55 V and sf/bcs/125 C/1.55 V) were over.
6. **Enable sequencing** (VDD ramp 100 us with `di_ena` low, `di_ena` rises at 200 us, an input step every 5 us):

| case | reference off (nA) | final reference (nA) | tau <= 30.5 ns from (us) | tau within 5 % of final from (us) | final tau (ns) |
| --- | --- | --- | --- | --- | --- |
| tt typ 27 C 1.5 V | 0.067 | 191.7 | 20 | 35 | 16.22 |
| ss typ -40 C 1.45 V | 0.001 | 174.7 | 120 | 130 | 14.18 |
| ss bcs -40 C 1.45 V | 0.001 | 224.7 | 120 | 130 | 11.13 |
| ss wcs 125 C 1.45 V | 1.044 | 183.6 | 35 | 40 | 23.04 |
| ff wcs 125 C 1.45 V | 5.640 | 180.9 | 30 | 30 | 26.31 |
| ff bcs -40 C 1.55 V | 0.011 | 223.9 | 15 | 35 | 11.30 |
| sf wcs 125 C 1.45 V | 1.969 | 183.2 | 30 | 30 | 23.28 |

   The valid tau comes at most 120 us after `di_ena` at the cold ss corners, against 55 us for the Pavan core in all 7 cases. The reference is within 5 % of its final value up to 265 us after `di_ena` at ss/bcs/-40 C (the 400 us window).

Temperature slope after the output trim (R1 735u, VDD 1.5 V). For every sample the code 16 + 2c that brings the output closest to 200 nA at 27 C is picked, the output at -40 C and 125 C is taken with that code (output at code 4 of the same sample times (16 + 2c) / 24, which neglects the 0.1 to 1.2 % code dependence of the output to core ratio). The 210 Monte Carlo samples are drawn once and run at the three temperatures on the same draws, the grid is 25 LV x HV corner pairs x 3 rhigh corners.

| Quantity | Monte Carlo (210) | Skew grid (75) |
| --- | --- | --- |
| I(125 C)/I(-40 C) | 1.342 to 1.407, mean 1.378, sigma 0.0128 (0.93 %) | 1.344 to 1.407, mean 1.379, sigma 0.0147 (1.07 %) |
| I(-40 C) / 200 nA | 0.841 to 0.925, sigma 2.1 % | 0.838 to 0.930, sigma 2.1 % |
| I(27 C) / 200 nA | 0.953 to 1.047 | 0.949 to 1.056 |
| I(125 C) / 200 nA | 1.161 to 1.279, sigma 3.0 % | 1.157 to 1.292, sigma 3.1 % |
| I(125 C)/I(-40 C) against V_R at 27 C | +0.26 per V, correlation +0.70, residual sigma 0.0091 (V_R sigma 34 mV) | +0.29 per V, correlation +0.88, residual sigma 0.0069 (V_R sigma 44 mV) |

The ratio spread is small because the current follows V_R / R1 and the rhigh and V_R temperature slopes are nearly the same in every sample. What is left of the ratio is a scatter that follows V_R at 27 C (a larger V_R means a steeper rise, about +0.26 % of the ratio per 10 mV), so the spread of I(-40 C) and I(125 C) around 200 nA, 2 % and 3 %, is mostly the 27 C trim residual (rms 2.4 %) carried to the temperature ends and not the slope. A K trim on `M1` (n U_T ln K, about +25 mV from K = 1 to 2) would move the ratio by about +0.0065, half of one sigma of its spread, and add a trim bit that has to be calibrated at two temperatures, so it is not worth it for the temperature slope (inference from the fit). It would only be of interest as a way to move the mean slope, which the OTA wants steeper at the hot end if anything.

SOA of the `bias_gm` devices, 60 ramps at VDD 1.55 V, reference limits LV 1.6 V (model-card VDS_MAX) and HV 3.3 V, `bias_trim` devices not counted (task BT). Peak per pair over all runs, device, and its Vgs at the peak:

| Class | Vgs | Vds | Vgd | Vgb |
| --- | --- | --- | --- | --- |
| LV | 1.553 V `MCL6` (Vgs 1.55 V) | 1.575 V `M3` (Vgs 0.37 V) | 1.592 V `M3` (Vgs 0.37 V, ff/27 C) | 1.573 V `MSB[12]` (Vgs 0.86 V) |
| HV | 1.553 V `MCL3` (Vgs 1.55 V) | 1.579 V `MINJ` (Vgs 0.60 V) | 1.597 V `MINJ` (Vgs 0.63 V, sf/27 C) | 1.553 V `MCL3` (Vgs 1.55 V) |

No LV device is over 1.6 V (0 of 60 ramps), the largest is the Vgd of `M3`, 1.592 V, where the gate `vz` is held while its drain `vy` overshoots VDD at the `di_ena` edge. The phase 1 peak of 1.602 V was the LV injector `MINJ` (Vgd). That is gone with the HV injector.

## Open issues

- **Start-up with R1 at 735u**: the Results table holds the 713.5u run. The 60 ramps were rerun with 735u on the schematic and on the PEX view of the layout (see Layout): 0 runs over the SOA limits, one schematic ramp without convergence.
- **Enable sequencing is slower than the Pavan core's:** valid tau from at most 120 us after `di_ena` at the cold ss corners (55 us before), start-up settling at most 127 us after a `di_ena` event (61 us before). The HV injector and the large `M5` branch set it, the LV injector restarts in 77 us in phase 2 at the cost of 17 nA of leakage into `vz` at ff/125 C.
- **Output resistance** 0.1 GOhm at ff/bcs/125 C and 1.6 % span over the OTA pin range, worse than the Pavan core.
- `macros/dsm2/layout/dsm2_core_gen.py` has to place the new outline (47.580 x 160.910 um, 31.56 um taller than 47.580 x 129.350 um) and wire the new pins `di_btest_en` (top) and `ibias_test` (right edge, y 2.53). `dsm2_core.sch` has to connect them (dsm2_core task).
- The post-layout phase margin was rerun at 7 corners only (46.9 deg minimum with `CC` of 20 units), the 135-condition sweep and the start-up SOA on the PEX view were not. Before the test bank the 135-condition minimum was 3.0 deg below the 7-corner one. The PEX section below is the layout before the test bank.
- Each further copy of `bias_trim` on `vz` adds gates to `vz` and lowers the phase margin.
- LVS of the all-one-net dummy groups only works in a pre-release build of IIC-OSIC-TOOLS 2026.10. The 2026.08 image deletes them from the layout netlist before the comparison.
- **Post-layout phase margin** is 40.9 to 56.3 deg over the 135 conditions on the corrected full RC view, against 46.9 to 65.4 deg for the schematic (mean loss 8.7 deg, the previous layout 9.4 deg). The loss is wiring capacitance, mostly on `vz` (218 fF) and `vx` (51 fF), see Layout. The loop was not tuned for it. Start-up and SOA do not move.
- Magic's full-RC extraction adds the coupling capacitance of the nets with a resistor network a second time to their substrate capacitance, `make magic-pex EXT_MODE=3` scales every net pair back to mode 2, see Layout. On the previous layout Magic's mode 2 gave one MOSFET the Metal1 area of a whole net as junction, invisible in these benches.
- Magic PEX leaves one capacitor-only node per rhigh stripe (108), `scripts/pex_mixed.py` ties each to ground by 1 TOhm. The resistor wiring of the stripes is not checked.
- GDS timestamps make rebuilds byte-different, so a rebuild without a change still shows in git.
