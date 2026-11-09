# Switched-Capacitor Common-Mode Reference

A 2:1 switched-capacitor divider that makes `vcm = vdd/2` for `sc_int2` and `dsm2_core` out of the clock phases `clk_noverlap` already makes. **Schematic, testbenches and layout (DRC and both LVS clean), no CACE datasheet yet.** Every number below is a sanity check from one or a few runs of the benches, not a characterisation.

## Ports

| Port | Direction | Meaning |
| --- | --- | --- |
| `di_phi1_b` | in | complement of phase 1 (`do_phi1_b` of `clk_noverlap`), low during phase 1 |
| `di_phi2` | in | phase 2 (`do_phi2` of `clk_noverlap`), high during phase 2 |
| `vcm` | inout | output, `vdd/2` |
| `vdd`, `vss` | inout | supply |

Port order in the netlist is `di_phi1_b di_phi2 vdd vss vcm`.
`do_phi1` and `do_phi2_b` are not used. Every switch is a single device, so each needs one gate polarity only.
`vcm` stays a chip pin. The pump's output resistance is about 1 MOhm, so an external source overrides it and the pin shows the pump's level otherwise.

## How It Works

Two flying capacitors `CF1` and `CF2` (4 `cap_cmomf` units each) sit between `vcf_t` and `vcf_b`. A reservoir `CR` holds `vcm`.

| phase | `vcf_t` | `vcf_b` | switches on |
| --- | --- | --- | --- |
| 1 (`di_phi1_b` low) | `vdd` through `MS1` | `vcm` through `MS2` | `MS1`, `MS2` |
| 2 (`di_phi2` high) | `vcm` through `MS3` | `vss` through `MS4` | `MS3`, `MS4` |

In phase 1 the flying capacitor is in series with the reservoir between `vdd` and `vss`, in phase 2 it is in parallel with it. Steady state is `vcm = vdd/2` whatever the capacitor values, and the output resistance is 1 / (4 fs C) with C the sum of `CF1` and `CF2` (8 units of 31.77 fF, 254 fF, 0.96 MOhm at fs = 1.024 MHz, by the model).
With `di_ena` low `clk_noverlap` holds both phases low, so every pump switch is off and the pump stops. `vcm` does not hold then, see Hold.

## Design Decisions

- **Single-device switches.** `vcf_t` only swings between `vcm` and `vdd`, and `vcf_b` between `vss` and `vcm`. `MS2` (between `vcf_b` and `vcm`) is therefore a PMOS and `MS3` (between `vcf_t` and `vcm`) an NMOS, and each sits at negative Vgs while its far terminal is at the rail. The first version used `sw_tgate` there. Its NMOS leaks with Vgs = 0 and 0.78 V across it, and a DC op at ff 1.55 V 125 C (scratch deck, 1 run per state) drew 62 nA out of `vcm` in phase 2, against 1.3 nA with the single devices. At 1 MOhm output resistance that is 60 mV against 1 mV.
- **Thick-oxide rail switches.** `MS1` and `MS4` connect to the rails and are thick-oxide for the leakage (the same DC op).
- **Plate orientation.** The flying caps are `cap_cmomf` on Metal3..Metal4. Its model is plate to plate only, with no substrate node, so the `cap_cmomi` shunt of the first version (4.2 fF per unit on MINUS, -13.9 mV with all eight units one way and +22.1 mV the other) is gone from the simulation. The real plates still have capacitance to their surroundings. A plate capacitance on `vcf_b` takes `Cp vcm` out of `vcm` every cycle and one on `vcf_t` gives `Cp (vdd - vcm)` back, so only the difference between the two nets counts, about 0.54 mV per fF (inference from the `cap_cmomi` sweep). A Magic extraction of the placed array (2.5D, not EM) gives 1.49 fF on each plate of an isolated unit, but in the array the plate on the south face (PLUS, since the layout mirrors only in x) sees 9.93 fF summed over the 8 units against 8.05 fF for MINUS, because the bottom row faces the ring and the top row the channel. `CF1` has PLUS on `vcf_t` and `CF2` on `vcf_b`, four units each, so that difference lands on both nets alike. LVS does not check orientation, the generator does. EM values of the unit and of these plate capacitances are not known yet.
- **Reservoir.** An LV NMOS gate leaks 0.27 nA per um2 at 0.775 V (ff, 125 C, model, DC op) and has 12 fF per um2. A thick-oxide NMOS with gate on `vcm` and drain, source and bulk on `vss` has no gate current (1e-18 A) and 3.8 fF per um2 at 0.75 V (3.4 at ss -40 C, 4.1 at ff 125 C, 5 corner DC and AC ops). The thick-oxide PMOS on `vdd` loses 44 % at ss -40 C, so the reservoir is the NMOS. `CR` is 7 devices of 10u/10u, 700 um2 of gate, 2.7 pF at tt (inference from the 3.8 fF per um2). The seventh device fills the layout row, see Layout.
- **Phases.** `di_phi1_b` leads `do_phi1` by 0.2 to 0.6 ns, which leaves 0.1 to 0.4 ns of the 0.4 to 0.9 ns non-overlap between phase 2 falling and `di_phi1_b` falling (inference from the `clk_noverlap` table). The pump draws 0.08 uA at tt on top of the 0.94 uA of `clk_noverlap` and the load (supply current of the standalone bench with and without the pump, 1 run each), so no shoot-through shows.

## Sizing

| Device | Cell | Size | Role |
| --- | --- | --- | --- |
| `MS1` | `sg13_hv_pmos` | 4u/0.45u | `vdd` to `vcf_t` |
| `MS2` | `sg13_lv_pmos` | 4u/0.5u | `vcf_b` to `vcm` |
| `MS3` | `sg13_lv_nmos` | 4u/0.5u | `vcf_t` to `vcm` |
| `MS4` | `sg13_hv_nmos` | 2u/0.45u | `vcf_b` to `vss` |
| `CF1[3:0]`, `CF2[3:0]` | `cap_cmomf` | 4.2u/12.4u, Metal3..Metal4, 31.77 fF each | flying, 254 fF in all |
| `CR` | `sg13_hv_nmos` | 10u/10u, m = 7 | reservoir, 2.7 pF |
| `MDEC` | `sg13_hv_nmos` | 4u/10u, m = 2 | `vdd` decoupling in the two layout corners, gate on `vdd`, about 0.3 pF (inference) |

`MS2` and `MS3` have equal gate area so their charge injection into `vcm` is of the same size and opposite sign. Their on resistance (a few kOhm up to about 25 kOhm at ss -40 C, inference) times the 0.25 pF of the flying capacitor is far below the 488 ns phase.
The reservoir sets the ripple of `vcm` at the sampling instant. Each time the DAC level of `sc_int2` changes, the two C1 right plates (63.56 fF each) pull a charge of up to 95 fC out of or into `vcm` at the start of phase 1, which is 38 mV on 2.5 pF. The flying capacitor has little say in it, the reservoir does. The same bench at tt with other sizes, run with the first version's `cap_cmomi` flying caps and loads (31.78 fF per unit, hpretl 2026.08, 1 run each, random DAC, end of phase 1, mV, the m = 7 row from the rerun after the change, the others from the m = 6 sweep):

| CF1 + CF2 units | CR devices (10u/10u) | CR (pF) | mean | peak to peak | mean at end of phase 2 | `vcm` peak to peak, whole cycle |
| --- | --- | --- | --- | --- | --- | --- |
| 8 | 6 | 2.3 | +4.1 | 58.9 | +12.6 | 72.3 |
| 8 | 7 (used) | 2.7 | +3.7 | 50.8 | +11.1 | 63.1 |
| 8 | 12 | 4.6 | +2.6 | 29.1 | +7.2 | 37.8 |
| 8 | 25 | 9.5 | +1.8 | 12.8 | +4.1 | 17.6 |
| 16 | 12 | 4.6 | +0.9 | 31.0 | +8.3 | 40.9 |
| 16 | 25 | 9.5 | +0.9 | 14.1 | +4.5 | 19.9 |
| 32 | 25 | 9.5 | -0.7 | 15.2 | +5.5 | 22.9 |
| 32 | 50 | 19 | -0.1 | 7.1 | +3.1 | 11.4 |

The ripple goes with 1 / CR (about 350 mV divided by the number of `CR` devices) and not with the flying capacitor. It is common mode on both C1 right plates, so it cancels in the differential charge up to the C1 mismatch, see Closed Loop for what the modulator does with it. A thick-oxide NMOS costs 0.26 um2 of gate per fF before its contacts and rings, a `cap_cmomf` unit on Metal3..Metal4 1.64 um2 per fF by the model.

`scripts/sizing/size_vcm_gen.ipynb` derives the sizes from the spec (output resistance, ripple, Ron against the phase) and compares them with the schematic. It was written after the schematic and is a model estimate at tt 300 K, not a result. It reproduces `1 / (4 fs C)` of the 254 fF flying capacitor (0.96 MOhm, confirmed by the exact two-phase recursion to 1 %), the Ron of 9.3 kohm in phase 1 and 2.7 kohm in phase 2 against 240 kohm allowed, the equal gate area of `MS2` and `MS3`, and a ripple of 36 mV for one plate against the 50.8 mV simulated. The main disagreements: `CR` is sized for the bench C1 of 63.56 fF, the `sc_int2` schematic now carries 87.95 fF, which gives 50 mV for one plate with the same `CR`. The recursion gives a sensitivity of `vcm` to the virtual grounds of 0.12 per volt against 0.27 in the sweeps and 16 start-up clocks against 12. The 5 mV error and 50 mV ripple limits are assumptions of the notebook.

## Testbenches

All in `testbenches/xschem`, `make sim-xschem TB=<bench>`, then `scripts/pvt.py <tran|start|step|hold>` inside the tools container reruns the netlist at the conditions and prints the table. The load is the C1 part of `sc_int2`: two `cap_cmomf` units per side (4.2u/12.405u, 31.78 fF each by the model, the value the `cap_cmomi` units of `sc_int2` had in hpretl 2026.08, since the new `sc_int2` unit is not final yet), right plate to `vcm` through `sw_tgate` in phase 1 and to an ideal virtual ground `vg` = `vdd/2` in phase 2, left plate to `vi` (`vdd/2` + 0.3 V) and a DAC level through `sw_tgate` in the other phase. The DAC level is a pseudo-random sequence of 0 and 1.5 V that changes 3 ns after each `di_clk` edge. The phases come from `clk_noverlap`. The `cmfb_sc2` load (10 fF refresh capacitors at `vcm` in phase 2) is not in them, the closed loop has it.
`e1` is `vcm` minus `vdd/2` 0.3 ns before the falling edge of `di_phi1` (where `sc_int2` samples), `e2` the same at `di_phi2` (where `cmfb_sc2` samples).

| Bench | What it does | Runs per pvt call |
| --- | --- | --- |
| `vcm_gen_tb_tran` | 40 clocks from `vcm` = `vdd/2`, statistics over the last 24 | 5 (tt 1.5 V 27 C, ss 1.45 V 125 C, ff 1.55 V 125 C, ff 1.55 V -40 C, ss 1.45 V -40 C) |
| `vcm_gen_tb_start` | from `vcm` = 0 V, `di_ena` rises at 2.2 clocks, constant DAC | 2 |
| `vcm_gen_tb_step` | `vdd` +50 mV in 1 ns at 12.25 clocks, constant DAC | 2 |
| `vcm_gen_tb_hold` | 20 clocks, then `di_ena` low for 200 us, constant DAC | 2 |

Capacitors use the typical corner (`cap_typ`) in all runs.

### Results

Standalone, random DAC, mV against `vdd/2`, 1 run per row, 0 measurements failed (`nfail` and `nextra` 0 in all runs), `registry.iic.jku.at:5000/iic-osic-tools:next` (a pre-release of IIC-OSIC-TOOLS 2026.10), `CR` m = 7:

| corner | vdd (V) | T (C) | `e1` mean | `e1` min / max | `e1` p-p | `e2` mean | `e2` p-p | mean `vcm` - `vdd/2` | `vcm` p-p | supply (uA) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tt | 1.5 | 27 | +4.7 | -18.2 / +32.7 | 50.9 | +7.1 | 41.0 | -0.2 | 62.4 | 1.00 |
| ss | 1.45 | 125 | +6.7 | -17.5 / +36.2 | 53.7 | +8.0 | 43.2 | +1.6 | 65.5 | 0.94 |
| ff | 1.55 | 125 | +8.2 | -12.8 / +34.0 | 46.9 | +10.0 | 39.3 | +1.9 | 61.9 | 1.61 |
| ff | 1.55 | -40 | +4.3 | -17.6 / +30.1 | 47.7 | +8.4 | 39.3 | -0.0 | 60.7 | 1.14 |
| ss | 1.45 | -40 | +5.0 | -21.1 / +36.1 | 57.3 | +7.9 | 45.7 | +0.6 | 68.8 | 0.84 |

Against the `cap_cmomi` version (hpretl 2026.08, tt: `e1` mean +3.7, p-p 50.8, `e2` mean +11.1) the ripple is the same, `e1` is 0.9 to 1.5 mV higher and `e2` 3.8 to 4.1 mV lower. The `cap_cmomi` version gave 68.6 mV `e1` p-p in `:next`: that image's `cap_cmomi` model gives 42.98 fF for the 3.56u/10.92u load unit against 31.78 fF in 2026.08 (ngspice AC, 1 run each), and 68.6 / 50.8 = 1.350 is the ratio of the two values, 1.352 (inference). The `cap_cmomf` model is the same in both images.

The supply current is the whole bench (`clk_noverlap` and the loads on its phases, 0.94 uA at tt without the pump).
- The mean error is +4.3 to +8.2 mV at the sampling instant of `sc_int2`, 0.6 to 1.1 % of the 0.75 V full scale, as a DAC offset. It is positive because of the injection of `MS2` and `MS3` and grows 3.5 mV from tt to ff 125 C (the DC op shows about 1 nA of leakage there, 1 mV at 1 MOhm, the rest is not separated out). A width of 4u on `MS2` and 3u on `MS3` gives +3.1 mV, 2u and 4u gives +6.9 mV (tt, 1 run each, with 6 reservoir devices and `cap_cmomi`).
- The 48 to 57 mV peak to peak is the data-dependent charge of the C1 right plates on a node of about 2.9 pF (inference: 2.7 pF of reservoir plus the rest of `vcm`), see Sizing.
- `e2` is 1.3 to 4.1 mV above `e1` in the mean, against 6.6 to 8.9 mV with `cap_cmomi`, whose shunt charge went into `vcm` at the start of phase 2 and out of it at the start of phase 1.

Start-up, from `vcm` = 0 V, 1 run per row, constant DAC, `:next`, 0 measurements failed:

| corner | vdd (V) | T (C) | first sample after `di_ena` (mV) | clocks to within 1 mV of the end value | time (us) | end value (mV) |
| --- | --- | --- | --- | --- | --- | --- |
| tt | 1.5 | 27 | -273 | 12 | 12.0 | +6.1 |
| ss | 1.45 | 125 | -243 | 11 | 11.0 | +7.9 |

Supply step of +50 mV, 1 run per row, constant DAC, the load's `vg` and `vi` stay fixed, `:next`, 0 measurements failed:

| corner | before the step (mV) | first sample after (mV) | second sample (mV) | time to within 1 mV of the end value (us) | end value (mV) |
| --- | --- | --- | --- | --- | --- |
| tt | +6.2 | -13.6 | -8.5 | 6.1 | -1.2 |
| ss 1.45 V 125 C | +7.9 | -11.0 | -5.9 | 6.1 | +2.0 |

The end value moves from +6.1 mV in the start-up bench to -1.2 mV here because `vg` stays at 0.75 V while `vdd/2` becomes 0.775 V, and C1 at 1.024 MHz is a 7.7 MOhm load to `vg` from each side.

Hold, `di_ena` low, 1 run per row, constant DAC, `:next`, 0 measurements failed:

| corner | vdd (V) | T (C) | drift in 50 us (mV) | drift in 200 us (mV) |
| --- | --- | --- | --- | --- |
| tt | 1.5 | 27 | +0.6 | +2.3 |
| ff | 1.55 | 125 | +32.6 | +112.2 |

`vcm` does not hold with the pump stopped. Leakage of about 1.5 nA at ff 125 C moves the 2.7 pF by 0.56 V per ms. From 0 V the pump needs 11 to 12 clocks (Start-up), from a drifted level it needs no more (inference).

## Closed Loop

These runs used `cap_cmomi` flying caps and `CR` m = 6 (hpretl 2026.08) and were not repeated after either change.

`dsm2_core` with `vcm_gen` instead of the ideal `vcm` source, tt 1.5 V 27 C, no noise, no mismatch. It is the first 1280 clocks of `macros/dsm2/testbenches/xschem/dsm2_core_tb_tran.sch` (the two DC steps, `VBRK` kept, the sine part cut), run on a scratch copy of `dsm2_core` with `vcm_gen` added, `vcm` as an inout pin and `.ic v(vcm)` = 0.75 V (the `dsm2` schematic is untouched). The phases of `clk_noverlap` drive the pump, so `sc_int2`, `cmfb_sc2` and the quantizer load `vcm` as in the chip. One run each, 1280 clocks, 0 measurements failed. The ideal run reproduces the bit means of `macros/dsm2` to four digits.

| run | bit mean at +0.3 V (clocks 200 to 640) | against 0.400 | bit mean at -0.3 V (840 to 1280) | against -0.400 | supply (uA) |
| --- | --- | --- | --- | --- | --- |
| ideal `vcm` | 0.4181 | +0.0181 | -0.3911 | +0.0089 | 6.80 |
| `vcm_gen`, `vi` referred to an ideal 0.75 V | 0.4271 | +0.0271 | -0.3866 | +0.0134 | 6.88 |

- The pump moves the bit means by +0.0090 at +0.3 V and +0.0045 at -0.3 V, 0.9 and 0.45 % of the full scale of 0.75 V. The supply goes up by 0.08 uA, the pump's own share in the standalone bench was the same.
- `vcm` at the sampling instants of the second run, in the two windows: 3.1 and 3.9 mV below 0.75 V at the end of phase 1 (`sc_int2`), 46 and 44 mV peak to peak, and 11.5 and 10.5 mV above it at the end of phase 2 (`cmfb_sc2`), 36 and 34 mV peak to peak. The standalone bench gave +4.1 mV and 59 mV, so the loop load pulls it 7 mV lower, which is the virtual grounds of `sc_int2` sitting about 25 mV below `vcm` against the pump's 1 MOhm (inference from the sensitivity below).
- The load of `sc_int2` is 133 nA per volt between its virtual grounds and `vcm` (2 C1 fs). The standalone bench with `vg` 0.2 V above `vdd/2` moves the mean of `vcm` at the end of phase 1 from +4.1 to +57.6 mV (8 flying units, 6 reservoir devices), from +2.6 to +53.7 mV (8 units, 12 devices) and from +0.9 to +31.5 mV (16 units, 12 devices), 1 run each. So the flying capacitor sets this sensitivity, 0.27 for 8 units and 0.15 for 16, and the reservoir does not.
- A third run with `vi` referred to the pump's own `vcm` node gave bit means of 0.4544 and -0.3411 against 0.4262 and -0.3548 expected (+0.0282 and +0.0137, so +0.0101 and +0.0048 against the same figures of the ideal run) and moved `vcm` by +11 and +25 mV with 108 mV peak to peak. That is a property of the bench: the input source returns the charge of the C1 left plates through the `vcm` node. A real input source has a stiff return, so this run is not used.
- `vod` stays within -0.513 and +0.518 V in the pump run, against -0.514 and +0.603 V with the ideal source. The ideal run's maximum is the response to the input step at clock 640.
- One run per row at one condition, without noise and mismatch. The 0.45 and 0.9 % shifts are a sanity check against the ideal source, not a measured offset of the chip.

## Layout

`layout/vcm_gen_gen.py` (`make layout`) draws the 78.83 x 24.00 um box that `dsm2_core` reserves at its bottom, with one vertical axis at x 39.415. Bottom to top:

| y (um) | what |
| --- | --- |
| 0.10 to 12.70 | `CR`: one strip of 7 HV NMOS 10/10 with an `MDR` finger (HV NMOS 10/0.45, every terminal on `vss`) at each end, all S/D columns on `vss` and shared, inside a psub ring (x 1.245 to 77.585). The gate strap under the row carries the `vcm` bus (Metal1, y 1.19), as far from the top edge and the switching nets as the box allows. The S/D columns run up into the ring's top band. |
| 12.97 to 21.6, corners | one `MDEC` per corner (HV NMOS 4/10, gate strap above on `vdd`, S/D columns down onto the ring), a tap bar, then the switches turned on their side. Left `MS2` and `MS1` in one NWell, right `MS3`, `MS4` and `MDS` (HV NMOS 1.5/0.45, every terminal on `vss`) at the mirrored x. `MDS` fills the 2 um that `MS4` (2u) leaves against `MS1` (4u). Gate pads of the switches face each other and the phase comes down between them. |
| 12.90 to 21.55, centre | `CF1` and `CF2`, 2 x 4 `cap_cmomf` units (Metal3..Metal4, Metal1 and Metal2 empty under them), checkerboard, both centroids on the axis. Unit ends from the left, on the full-height Metal3 edges of the units: `vcf_t`, `vcf_b`, `vcf_t`, `vcf_b`, `vcf_t`, 0.25 um between facing edges. Each edge runs on through the row gap and up into the channel as one 0.355 um Metal3 strip, the two strips of a column are tied at the row centres, and each strip ends in its own two-cut stack on the track of its net (four per net). Nothing merges into a wide shape next to the PCell's 0.21 um finger gaps. |
| 12.295 to 22.155 | the cap guard, 0.25 um outside the array on all four sides, on each layer as wide as the face of a neighbouring unit (sides Metal3 0.355 and Metal4 0.20, below and above Metal3 0.20 and Metal4 0.355). Every piece is on the plate net its face is not, so it only adds flying capacitance: the sides face the two outer edges (`vcf_t`) and are `vcf_b`, each one more riser up to a `vcf_b` tap. Below and above, per column `vcf_b`, `vcf_t`, `vcf_t`, `vcf_b`: the outer runs join the sides, the middle run hangs on the axis risers (extended down to the bottom run), and above the array each Metal3 piece joins the riser of its own net. The bottom runs lie over the ring's top band. |
| 21.55 to 23.79 | channel: `vcf_b` (Metal2), `vcf_t` (Metal4), `di_phi1_b` (Metal2) from its pin to the left drop, and a `vdd` Metal4 track that joins the two `vdd` stripes and screens the channel from the `dsm2_core` pin tracks above. |

- The array is not a matched one (the DC value of `vcm` needs no capacitor matching), so it has a guard instead of a ring of dummy units. A guard on `vss` puts capacitance to ground on the plates and moves `vcm`: Magic full RC, tran set, same flow and host, mean of `vcm` against the layout before the guard (sanity checks):

| guard | `vcf_t` / `vcf_b` to rails and phases (fF, mode 2) | mean of `vcm`, tt | all five corners |
| --- | --- | --- | --- |
| none (layout before) | 15.1 / 12.4 | +1.85 mV | |
| all `vss` | 30.2 / 22.3 | +5.35 mV | |
| `vss` below and above, `vcf_b` sides | 26.9 / 23.6 | +2.80 mV | +0.8 to +1.1 mV |
| on the plate nets (built) | 15.8 / 14.2 | +1.25 mV | -0.58 to -0.62 mV (mode 2: -0.58 to -0.62 mV) |

`pex_caps.py` drops the guard-to-plate coupling with the rest of the `vcf_t`/`vcf_b` coupling (228.7 fF in all).
- `vcm` runs in shielded lanes along both side edges, a Metal1 conductor between a Metal1 `vss` track and the ring's side band (0.235 um from the conductor, M1.e asks 0.22 for the 0.32 band) under a Metal2 `vss` roof, the form of the `dsm2_core` lane that continues it above the box. Above the ring the band runs on as the inner track. Left: from the bus to `MS2` and up to the pin. Right: from the bus to `MS3`, `vss` above that. It leaves the ring on a Metal2 jumper over the band.
- The cap orientation is a generator check, since LVS treats both plates alike: unmirrored a unit has PLUS on its west edge (and its south face), `CF1` PLUS on `vcf_t` and `CF2` PLUS on `vcf_b`. The KLayout extraction agrees: four units with `vcf_t` on the first terminal and four with `vcf_b`.
- Pins as the `dsm2_core` box wants them: `vcm` Metal1 x 0.72 to 1.01, `di_phi1_b` Metal3 x 30.38 to 30.67, `di_phi2` Metal3 x 70.945 to 71.235, all on the top edge, and the Metal3 stripes `vss` (x 5.64 to 6.34, 72.49 to 73.19) and `vdd` (x 6.64 to 7.34, 71.49 to 72.19) full height, their bottom ends the chip supply pins. Metal2 and Metal4 stay 0.21 um inside the top edge.
- The MOS PCells are flattened and the cap is one static cell, `cap_cmomf_vcm_gen`, because `dsm2_core` copies `sc_int2` in as well, whose PCell cells have the same names and other parameters.
- The build stops on shorts and spacing between recorded nets, opens and floating metal (one metal cluster per net, seven nets), the cap orientation, the device count against the schematic, the shared CR and `MDR` columns, the mirror XOR on the device layers and Metal1 outside the two switch corners and the right lane slot, the mirror of both guard nets on Metal3 and Metal4, lone vias, labels outside pins, off-grid vertices, shapes outside the outline and an empty area over 8 % (2.8 %). `CHECK_CONTROL=1` adds a short and a floating piece and the build fails on both. `PLACE_ONLY=1` writes devices, wells, rings and the cap guard only.
- Left empty on purpose: above `MS2` (3.6 x 2.7 um) and above `MS3` (2.1 x 2.7 um) at the top edge. Filling them would take about 1.8 um more device height per corner.

Verification, all in `registry.iic.jku.at:5000/iic-osic-tools:next` (image bb525d654d8d):

| check | result |
| --- | --- |
| `make klayout-drc DRC_LEVEL=macro` | 0 markers |
| `make klayout-drc DRC_LEVEL=regular` | only the whole-outline density rules M1.j to M4.j and TM1.c, as every block before fill, no antenna or latch-up marker |
| `make magic-drc` | 0 |
| `make klayout-lvs` | netlists match (deep mode). The two dummies on `vss` are extracted (one 21.5u HV NMOS on `vss`, the parallel sum of `MDR` and `MDS`). Without `MDS` in the schematic it fails. |
| `make magic-lvs` | circuits match uniquely (`cap_cmomf` ignored, Magic does not extract it, see `scripts/netgen_setup.tcl`), 7 device classes each side. Netgen also lists `mm_ok` property errors on the MOS devices, a schematic-only parameter, and no value mismatch. Note: the target's verdict accepts "match uniquely with property errors", and without `MDS` in the schematic Netgen reports the 7.2 % W difference only as a property error, so the `circuit1:` lines of `verification/lvs/vcm_gen.magic.lvs/vcm_gen.lvs.out` have to be empty too. |
| `layout/mom_check.py` on the LVS database and the GDS | 2 cap pairs (m = 4 each), w and l match, Metal3 and Metal4 inside the markers as the schematic says. It fails on a CDL with w 4.3u (which KLayout LVS still matches) and on a schematic with mmin 1. |

PEX: `make magic-pex` (C-coupled, `EXT_MODE=2`, the default, hierarchy off) and `make magic-pex EXT_MODE=3` (full RC, the default extresist settings, `MINDELAY` 0). Neither Magic nor kpex is trusted on the capacitance of a MoM comb, an EM solve is the reference, so `scripts/pex_gds.py` turns every `cap_cmomf` into plain metal with labelled edges and `scripts/pex_caps.py` drops the extracted coupling between `vcf_t` and `vcf_b` (228.7 fF, Magic's plate-to-plate value plus the wire coupling between the two nets and the guard, against 254.2 fF by the model) and adds the caps back as `cap_cmomf` devices at the model value. The extraction is used for the wiring and for the plates' capacitance to everything else, nothing more.
Per net in the mode 2 extraction (fF): `vcf_t` 17.0 (`vss` 8.1, `vdd` 7.3, `vcm` 1.1, phases 0.4), `vcf_b` 15.3 (`vss` 12.3, `vcm` 1.2, `vdd` 0.9, `di_phi1_b` 0.9, `di_phi2` 0.1). `vcm`: `vss` 97.5, `vdd` 1.3, `vcf_t` 1.1, `vcf_b` 1.2, `di_phi1_b` 0.08, `di_phi2` 0.08.

Full RC: `vcf_b` (5 resistors, 2.5 to 12.1 Ohm), `vcf_t` (7, 2.7 to 18.9 Ohm), `vcm` (4, 1.3 to 21.6 Ohm), `vdd` (8) and `vss` (624, the count changes from run to run) get resistor networks at `THRESHOLD` 10000 mOhm. Magic books the whole coupling of a net with a resistor network a second time as capacitance to `vss` (magic#557): `vcf_t` to `vss` comes out 245.7 fF and `vcf_b` to `vss` 244.0 fF instead of 8.1 and 12.3 fF, mostly the plate-to-plate value. Uncorrected, that moved `vcm` by about -100 mV on the old layout. So `make magic-pex EXT_MODE=3` also extracts the pad layout in mode 2 (`netlist/pex/vcm_gen_magic_raw_2.spice`, reused while it is newer than the pad layout), and `../scripts/pex_rc_caps.py` scales every capacitor between two nets of the full-RC netlist to the total of its net pair there (it stops on a missing or older reference). Afterwards all 20 net pairs equal mode 2 (largest deviation 0.04 aF) and the view differs from mode 2 by its resistors and its junction areas (`as` plus `ad` 31.4 against 137.5 um2, mode 2 books the Metal1 of a whole net on one device as in `sc_int2`). The caps sit on the bare net node.

Benches on three views, schematic / Magic mode 2 / Magic mode 3, mV against `vdd/2`, 1 run per point, 0 measurements failed (`nfail` and `nextra` 0 in all 33 runs), all in `registry.iic.jku.at:5000/iic-osic-tools:next` (bb525d654d8d) on one x86 host, sanity checks and not a characterisation.

`vcm_gen_tb_tran`, random DAC:

| corner | vdd (V) | T (C) | `e1` mean | `e1` p-p | `e2` mean | `e2` p-p | supply (uA) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tt | 1.5 | 27 | +4.73 / +3.93 / +4.29 | 50.9 / 49.1 / 49.2 | +7.10 / +10.68 / +10.37 | 41.0 / 39.5 / 39.5 | 1.002 / 1.030 / 1.030 |
| ss | 1.45 | 125 | +6.70 / +5.68 / +5.59 | 53.7 / 51.8 / 51.8 | +7.95 / +11.45 / +11.22 | 43.2 / 41.6 / 41.6 | 0.937 / 0.962 / 0.962 |
| ff | 1.55 | 125 | +8.16 / +7.22 / +7.69 | 46.9 / 46.2 / 46.0 | +9.98 / +13.47 / +13.10 | 39.3 / 38.0 / 37.9 | 1.608 / 1.634 / 1.633 |
| ff | 1.55 | -40 | +4.30 / +3.73 / +5.55 | 47.7 / 44.2 / 45.8 | +8.36 / +11.83 / +11.52 | 39.3 / 38.0 / 38.0 | 1.141 / 1.167 / 1.166 |
| ss | 1.45 | -40 | +4.97 / +3.92 / +4.13 | 57.3 / 55.2 / 55.1 | +7.85 / +11.20 / +10.96 | 45.7 / 43.8 / 43.8 | 0.843 / 0.868 / 0.868 |

Start-up, step and hold, same three views:

| bench | corner | first sample after `di_ena` | clocks to 1 mV | end value |
| --- | --- | --- | --- | --- |
| start | tt 1.5 V 27 C | -273.4 / -300.7 / -300.0 | 12 / 12 / 12 | +6.05 / +5.30 / +5.63 |
| start | ss 1.45 V 125 C | -242.9 / -257.7 / -257.5 | 11 / 11 / 11 | +7.88 / +6.60 / +6.50 |

| bench | corner | before the step | first sample after | second sample | time to 1 mV (us) | end value |
| --- | --- | --- | --- | --- | --- | --- |
| step | tt 1.5 V 27 C | +6.18 / +5.24 / +5.75 | -13.58 / -14.68 / -14.07 | -8.45 / -9.51 / -9.00 | 6.1 / 5.1 / 6.1 | -1.24 / -1.90 / -1.43 |
| step | ss 1.45 V 125 C | +7.86 / +6.60 / +6.46 | -11.01 / -12.47 / -12.49 | -5.92 / -7.22 / -7.35 | 6.1 / 6.1 / 6.1 | +1.98 / +0.99 / +0.93 |

| bench | corner | drift in 50 us | drift in 200 us |
| --- | --- | --- | --- |
| hold | tt 1.5 V 27 C | +0.58 / +0.53 / +0.53 | +2.33 / +2.20 / +2.21 |
| hold | ff 1.55 V 125 C | +32.6 / +31.7 / +31.7 | +112.2 / +109.7 / +109.8 |

The wiring and plate capacitances move the `e2` mean by +3.1 to +3.6 mV and the `e1` mean, where `sc_int2` samples, by -1.1 to +1.3 mV against the schematic. Start-up begins 15 to 27 mV lower on the extracted views, the same 12 and 11 clocks to settle. Against the layout before the guard, same flow and host, see the guard table in Layout. Mode 3 against mode 2: within 0.52 mV in every mean except `e1` at ff 1.55 V -40 C, see What Is Missing.

## What Is Missing

- Mode 3 against mode 2, `e1` mean at ff 1.55 V -40 C: +1.82 mV (+5.55 against +3.73) with `MINDELAY` 0, the same +1.82 mV on the layout before the guard, against +0.18 mV with `MINDELAY` 1 (the earlier runs on the old layout, aarch64 host). At tt the difference is +0.35 mV on both layouts. One run per point, cause not found.
- The export targets (LEF, Liberty, Verilog) and the closed loop with the extracted view.
- A CACE datasheet.
- EM values of the `cap_cmomf` unit and of the plate capacitances in the array (a separate task). Until then the device caps are the model value and the plate parasitics Magic's.
- Capacitor corners and mismatch (the `cap_cmomf` model has none), and noise.
- The closed loop with the `cap_cmomf` flying caps.
- The bench loads at the final `sc_int2` C1 unit.
- The pump with the extracted `sc_int2`. The load of the benches is the C1 part and the closed loop uses the schematic views.
- A `cmfb_sc2` load in the standalone benches.
