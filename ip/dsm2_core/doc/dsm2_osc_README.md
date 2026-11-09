# ihp-sg13cmos5l On-Chip Clock of dsm2_core (dsm2_osc)

A current-starved ring oscillator that can replace the external `di_clk` of `dsm2_core`, fed by the `ibias_test` current of the `bias_gm` test bank. **Schematic, layout with both LVS matching, an extracted view, ngspice benches and a VACASK phase noise bench, no CACE datasheet.** It is part of `dsm2_core` on the oscillator variant (branch `dsm2-osc`), which DSA1 tapes out. Every number below is a sanity check from one run per condition, not a characterisation.

It sits in the `ibias_test` path between `bias_gm` and `dsm2_io_esd`. With `di_osc_en` low the current goes to the pad as today. With it high the current goes into the ring and the pad path is open.

## Ports

| Port | Direction | Meaning |
| --- | --- | --- |
| `vdd`, `vss` | inout | VDDA 1.5 V and ground |
| `di_osc_en` | in | oscillator on (high), 1.2 V static, through its own `dsm2_io_rx` |
| `di_clk_sel` | in | high selects the oscillator as modulator clock, low the external clock, 1.2 V static, through its own `dsm2_io_rx` |
| `d_btest_en` | in | 1.5 V, from `dsm2_io` |
| `ibias_in` | in | sourcing current from `bias_gm` `ibias_test`, 16 + 2 x code units of 8.33 nA |
| `di_clk_ext` | in | external clock from `dsm2_io_clk` |
| `d_btest_or` | out | `d_btest_en` OR `d_osc_en`, to `bias_gm` `di_btest_en`, because the bank only sources while that input is high |
| `ibias_pad` | out | to the `dsm2_io_esd` core node `ibias_test_esd` |
| `do_clk_mod` | out | modulator clock for `clk_noverlap` and the quantizer clock |
| `do_clk_osc` | out | the oscillator clock for a pad driver, low while `di_osc_en` is low |
| `do_osc_oe` | out | `di_clk_sel` at 1.5 V levels (the `XI1` output that also drives the mux select), output enable of the bidirectional clock pad, high = oscillator clock selected |

Both selects are static settings, change them with `di_ena` low. Switching `di_clk_sel` with the clock running can cut a runt pulse into `do_clk_mod`, the shortest pulse after the toggle is in the last column of the clock table (3 ns at ff 1.55 V 125 C code 15, 260 ns at tt code 4). With `di_osc_en` low and `di_clk_sel` high `do_clk_mod` stays low.
Switch `di_osc_en` and `di_clk_sel` only with `di_ena` low and `di_rst_b` low. Runts down to 3 ns can reach `do_clk_mod`, and `clk_noverlap` is not checked against them.

## Circuit

Schematic `schematic/xschem/dsm2_osc.sch`, one flat sheet. Unit finger is W 0.5u L 0.5u, set by the packing of the layout.

| Block | Devices | What |
| --- | --- | --- |
| Receivers | `XRX0`, `XRX1` (`dsm2_io_rx` of `macros/dsm2_io`), `XI0`, `XI1` (`inv_1`) | the two 1.2 V selects to 1.5 V levels and both polarities |
| Bank enable | `XOR` (`or2_1`) | `d_btest_or` |
| Pad path | `MSP`, LV PMOS W 1u L 0.5u m2, gate `d_osc_en` | passes `ibias_in` to `ibias_pad` while `di_osc_en` is low, same idea as `MBS` of `bias_gm` |
| Ring branch | `MSN`, HV NMOS W 1u L 0.45u, gate `d_osc_en` | opens the current into `vg` while `di_osc_en` is high |
| Mirrors | `MD` (diode on `vg`, W 0.5u L 0.5u m2), `M2` (m1), `MPD` (PMOS diode on `vbp`, m1), `MGD` (pulls `vg` low while off), `MPK` (pulls `vbp` high while off) | each tail carries about half of `ibias_in`, `vbp` is the PMOS copy of the same current |
| Ring | 5 x (`XTP`, `XP`, `XN`, `XTN`) and `XC1` to `XC5` | starved inverters, tails `XTP` / `XTN` (unit finger, m1) on `vbp` / `vg`, inverters W 1u L 0.13u, node caps are NMOS gates W 0.5u L 0.5u |
| Clamps | `XK1`, `XK3`, `XK5` (NMOS), `XK2`, `XK4` (PMOS), W 0.5u L 0.13u | hold the ring at 0 1 0 1 0 while `di_osc_en` is low, so no node floats mid-rail |
| Restorer | `XSP1` to `XSP3`, `XSN1` to `XSN3` (unit finger) | 6T Schmitt trigger on `n5`, so the slow ring edges draw no crowbar current in the logic |
| Divide and select | `XR3` (`inv_1`), `XFF` (`dfrbp_1`, reset `d_osc_en`), `XMUX` (`mux2_1`), `XBM` (`buf_2`) | divide by 2 for 50 % duty, 2:1 clock mux, buffer |
| Pad driver | `XA` (`and2_1`), `XO1` (`inv_1`), `XO2` (`inv_2`) | as the `do_q` drivers of `quantizer2` |
| Dummies | `XDN1`, `XDN2` (all terminals `vss`), `XDP1`, `XDP2` (all terminals `vdd`) | unit fingers, one at each end of each tail strip |

The ring runs at twice the clock. The tails use both polarities so the rising and falling edges are equally slow and the Schmitt trigger sees a rail-to-rail swing. A ring starved on the NMOS side only swings 0.86 to 1.5 V (sim, 12 us run), the Schmitt never toggles and the clock sticks, so that variant is not usable with this restorer.

Frequency spread comes from the unit mirrors: with L 0.5u the tails carry more than the diode copy because of the drain voltage dependence, and the frequency was set with the caps and `MD` m2, not with a matched ratio.

## Sizing

`scripts/sizing/size_dsm2_osc.ipynb` estimates the tail currents, node capacitances and frequency from the gm/ID tables and compares them with the schematic. It was written after the schematic. The model puts code 4 at 715 kHz (sim 823 kHz) and asks for an `MD` multiplier of 1.4 to 1.6 for 1.024 MHz, which no whole multiplier on the grid gives. The cell stays as drawn and reaches 1.024 MHz with a higher trim code.

## Benches

`testbenches/xschem/dsm2_osc_tb_tran.sch` (frequency, duty, start-up, current, mux toggle) and `dsm2_osc_tb_pad.sch` (pad path, `.op` sweeps). Both use an ideal current source for `ibias_in` with the bank's code to current relation, 200 fF on `ibias_in`, 100 fF on `do_clk_mod` and 80 fF on `do_clk_osc`.
`pvt.py` and `pad.py` rerun the netlists of the benches at the conditions below.
The transient needs a maximum step of 0.5 ns and `abstol` 1e-13. At a 2 ns step the standard-cell flip-flop produced false toggles on the falling clock edge, and with `abstol` 1e-15 ngspice aborted on the receiver output.
Any bench with the oscillator running, dsm2_core included, needs `reltol` 1e-4. At the ngspice default of 1e-3 the flip-flop jumps to its other state about 1 ns before a real clock edge, with its clock input still at 0 V, which shows as low phases of about 1.3 ns. VACASK at 1e-3 shows no such jumps (sim).

### Clock

Transient of `dsm2_osc_tb_tran`, 40 us, `di_osc_en` rises at 1 us, `di_clk_ext` runs at 1.024 MHz with `di_clk_sel` low until 24 us and the oscillator is selected after that. Frequency and duty of `do_clk_mod` after the toggle (sim), start-up is the time from `di_osc_en` rising to the first edge after which every period is within 5 % of the steady one, `I off` is the supply current of the cell with `di_osc_en` low (it includes the receiver and leakage, the bank current is subtracted), `I running` the supply current with the ring running, also without the bank current of 8.33 nA x (16 + 2 x code). 27 runs, none failed to measure. Target 1.024 MHz at code 4, tt, 1.5 V, 27 C.

| corner | vsup (V) | T (C) | code | f of do_clk_mod (kHz) | duty (%) | period jitter (%) | start-up (us) | I off (nA) | I running (uA) | mux min pulse (ns) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tt | 1.5 | 27 | 0 | 565.9 | 50.0 | 0.00 | 0.13 | 48.9 | 4.79 | 168 |
| tt | 1.5 | 27 | 4 | 822.9 | 50.0 | 0.00 | 0.10 | 48.9 | 5.08 | 260 |
| tt | 1.5 | 27 | 15 | 1479.1 | 50.0 | 0.00 | 0.07 | 48.9 | 5.73 | 128 |
| ss | 1.5 | 27 | 0 | 576.2 | 50.0 | 0.00 | 0.17 | 38.7 | 3.89 | 75 |
| ss | 1.5 | 27 | 4 | 837.3 | 50.0 | 0.00 | 0.13 | 38.7 | 4.09 | 75 |
| ss | 1.5 | 27 | 15 | 1507.5 | 50.0 | 0.00 | 0.08 | 38.7 | 4.73 | 332 |
| ff | 1.5 | 27 | 0 | 551.1 | 50.0 | 0.00 | 0.09 | 78.1 | 6.28 | 488 |
| ff | 1.5 | 27 | 4 | 802.6 | 50.0 | 0.00 | 0.08 | 78.1 | 6.41 | 74 |
| ff | 1.5 | 27 | 15 | 1443.5 | 50.0 | 0.00 | 0.06 | 78.1 | 7.08 | 74 |
| sf | 1.5 | 27 | 0 | 567.6 | 50.0 | 0.00 | 0.16 | 49.8 | 4.73 | 132 |
| sf | 1.5 | 27 | 4 | 825.5 | 50.0 | 0.00 | 0.13 | 49.8 | 4.99 | 214 |
| sf | 1.5 | 27 | 15 | 1483.5 | 50.0 | 0.00 | 0.08 | 49.8 | 5.71 | 75 |
| fs | 1.5 | 27 | 0 | 564.8 | 50.0 | 0.00 | 0.10 | 51.3 | 4.90 | 176 |
| fs | 1.5 | 27 | 4 | 821.2 | 50.0 | 0.00 | 0.08 | 51.3 | 5.21 | 283 |
| fs | 1.5 | 27 | 15 | 1475.9 | 50.0 | 0.00 | 0.06 | 51.3 | 5.87 | 162 |
| ss | 1.45 | -40 | 0 | 570.8 | 50.0 | 0.00 | 0.22 | 34.4 | 3.58 | 75 |
| ss | 1.45 | -40 | 4 | 832.8 | 50.0 | 0.00 | 0.16 | 34.4 | 3.90 | 75 |
| ss | 1.45 | -40 | 15 | 1516.9 | 50.0 | 0.00 | 0.09 | 34.4 | 4.45 | 240 |
| ff | 1.55 | 125 | 0 | 502.6 | 50.0 | 0.00 | 0.06 | 472.7 | 6.83 | 488 |
| ff | 1.55 | 125 | 4 | 733.0 | 50.0 | 0.00 | 0.05 | 472.7 | 6.91 | 282 |
| ff | 1.55 | 125 | 15 | 1327.6 | 50.0 | 0.00 | 0.04 | 472.7 | 7.56 | 3 |
| tt | 1.45 | 27 | 0 | 577.2 | 50.0 | 0.00 | 0.12 | 45.0 | 4.41 | 75 |
| tt | 1.45 | 27 | 4 | 839.6 | 50.0 | 0.00 | 0.10 | 45.0 | 4.68 | 75 |
| tt | 1.45 | 27 | 15 | 1510.6 | 50.0 | 0.00 | 0.07 | 45.0 | 5.22 | 308 |
| tt | 1.55 | 27 | 0 | 555.2 | 50.0 | 0.00 | 0.14 | 53.1 | 5.46 | 488 |
| tt | 1.55 | 27 | 4 | 807.3 | 50.0 | 0.00 | 0.11 | 53.1 | 5.66 | 19 |
| tt | 1.55 | 27 | 15 | 1449.6 | 50.0 | 0.00 | 0.07 | 53.1 | 6.32 | 75 |

Code 4 is -19.6 % from the target at tt and spreads from 733 to 840 kHz over all conditions (-28 % to -18 %). The frequency follows the bank current (565.9, 822.9 and 1479 kHz at codes 0, 4, 15, tt) and hardly the corner, as it should for a current-starved ring. Duty is 50.0 % everywhere because the flip-flop divides.

The sheet is tuned with `MD` m2 and the 0.5u node caps, not with a matched mirror ratio, so a 20 % miss at tt is accepted for a trimmed test clock.

### Supply sensitivity at tt, 27 C, code 4

Same bench, tt 27 C code 4 (sim): 839.6 kHz at 1.45 V, 822.9 kHz at 1.50 V, 807.3 kHz at 1.55 V, so -2.0 % and -1.9 % per +50 mV, about -39 %/V. This is with both tails starved, the one-sided variant was not simulated further because it does not restore. The cell current rises from 4.68 to 5.66 uA over the same range.

### Pad path

Operating points of `dsm2_osc_tb_pad`, ideal current source, codes 0, 4 and 15 (the 16 + 2 x code units of 8.33 nA each), `ibias_pad` forced to 0.3, 0.5 and 0.8 V. The error column is `ibias_pad` over `ibias_in` with `di_osc_en` low, the last column the current the cell sources into the pad with `di_osc_en` high. 63 points, none failed. Corners tt, ss, ff, sf, fs at 1.5 V 27 C plus ss 1.45 V -40 C and ff 1.55 V 125 C.

| corner | vsup (V) | T (C) | code | vpad (V) | ibias_pad / ibias_in - 1, di_osc_en low (%) | ibias_in, di_osc_en low (V) | leakage into the pad, di_osc_en high (pA) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tt | 1.5 | 27 | 0 | 0.3 | -0.001 | 0.477 | 2.1 |
| tt | 1.5 | 27 | 0 | 0.5 | -0.001 | 0.515 | 1.2 |
| tt | 1.5 | 27 | 0 | 0.8 | -0.012 | 0.801 | 0.6 |
| tt | 1.5 | 27 | 4 | 0.3 | -0.001 | 0.490 | 2.1 |
| tt | 1.5 | 27 | 4 | 0.5 | -0.001 | 0.521 | 1.2 |
| tt | 1.5 | 27 | 4 | 0.8 | -0.008 | 0.802 | 0.6 |
| tt | 1.5 | 27 | 15 | 0.3 | -0.000 | 0.513 | 2.1 |
| tt | 1.5 | 27 | 15 | 0.5 | -0.001 | 0.535 | 1.2 |
| tt | 1.5 | 27 | 15 | 0.8 | -0.004 | 0.803 | 0.6 |
| ss | 1.5 | 27 | 0 | 0.3 | +0.000 | 0.520 | 0.7 |
| ss | 1.5 | 27 | 0 | 0.5 | +0.000 | 0.534 | 0.4 |
| ss | 1.5 | 27 | 0 | 0.8 | -0.004 | 0.801 | 0.2 |
| ss | 1.5 | 27 | 4 | 0.3 | +0.000 | 0.533 | 0.7 |
| ss | 1.5 | 27 | 4 | 0.5 | +0.000 | 0.544 | 0.4 |
| ss | 1.5 | 27 | 4 | 0.8 | -0.002 | 0.802 | 0.2 |
| ss | 1.5 | 27 | 15 | 0.3 | +0.000 | 0.556 | 0.7 |
| ss | 1.5 | 27 | 15 | 0.5 | +0.000 | 0.563 | 0.4 |
| ss | 1.5 | 27 | 15 | 0.8 | -0.001 | 0.804 | 0.2 |
| ff | 1.5 | 27 | 0 | 0.3 | -0.002 | 0.432 | 6.6 |
| ff | 1.5 | 27 | 0 | 0.5 | -0.005 | 0.507 | 4.3 |
| ff | 1.5 | 27 | 0 | 0.8 | -0.038 | 0.801 | 2.2 |
| ff | 1.5 | 27 | 4 | 0.3 | -0.001 | 0.445 | 6.6 |
| ff | 1.5 | 27 | 4 | 0.5 | -0.004 | 0.510 | 4.3 |
| ff | 1.5 | 27 | 4 | 0.8 | -0.025 | 0.801 | 2.2 |
| ff | 1.5 | 27 | 15 | 0.3 | -0.001 | 0.467 | 6.6 |
| ff | 1.5 | 27 | 15 | 0.5 | -0.002 | 0.519 | 4.3 |
| ff | 1.5 | 27 | 15 | 0.8 | -0.013 | 0.803 | 2.2 |
| sf | 1.5 | 27 | 0 | 0.3 | -0.001 | 0.454 | 3.7 |
| sf | 1.5 | 27 | 0 | 0.5 | -0.002 | 0.510 | 2.3 |
| sf | 1.5 | 27 | 0 | 0.8 | -0.021 | 0.801 | 1.2 |
| sf | 1.5 | 27 | 4 | 0.3 | -0.001 | 0.467 | 3.7 |
| sf | 1.5 | 27 | 4 | 0.5 | -0.002 | 0.514 | 2.3 |
| sf | 1.5 | 27 | 4 | 0.8 | -0.014 | 0.802 | 1.2 |
| sf | 1.5 | 27 | 15 | 0.3 | -0.001 | 0.490 | 3.7 |
| sf | 1.5 | 27 | 15 | 0.5 | -0.001 | 0.525 | 2.3 |
| sf | 1.5 | 27 | 15 | 0.8 | -0.007 | 0.803 | 1.2 |
| fs | 1.5 | 27 | 0 | 0.3 | +0.000 | 0.499 | 1.2 |
| fs | 1.5 | 27 | 0 | 0.5 | -0.001 | 0.523 | 0.7 |
| fs | 1.5 | 27 | 0 | 0.8 | -0.007 | 0.801 | 0.3 |
| fs | 1.5 | 27 | 4 | 0.3 | -0.001 | 0.512 | 1.2 |
| fs | 1.5 | 27 | 4 | 0.5 | -0.001 | 0.531 | 0.7 |
| fs | 1.5 | 27 | 4 | 0.8 | -0.004 | 0.802 | 0.3 |
| fs | 1.5 | 27 | 15 | 0.3 | +0.000 | 0.534 | 1.2 |
| fs | 1.5 | 27 | 15 | 0.5 | -0.000 | 0.547 | 0.7 |
| fs | 1.5 | 27 | 15 | 0.8 | -0.002 | 0.804 | 0.3 |
| ss | 1.45 | -40 | 0 | 0.3 | +0.000 | 0.551 | 0.3 |
| ss | 1.45 | -40 | 0 | 0.5 | +0.000 | 0.554 | 0.2 |
| ss | 1.45 | -40 | 0 | 0.8 | -0.002 | 0.801 | 0.1 |
| ss | 1.45 | -40 | 4 | 0.3 | +0.000 | 0.561 | 0.3 |
| ss | 1.45 | -40 | 4 | 0.5 | +0.000 | 0.565 | 0.2 |
| ss | 1.45 | -40 | 4 | 0.8 | -0.002 | 0.802 | 0.1 |
| ss | 1.45 | -40 | 15 | 0.3 | +0.000 | 0.579 | 0.3 |
| ss | 1.45 | -40 | 15 | 0.5 | +0.000 | 0.583 | 0.2 |
| ss | 1.45 | -40 | 15 | 0.8 | -0.001 | 0.803 | 0.1 |
| ff | 1.55 | 125 | 0 | 0.3 | +0.345 | 0.374 | 290.0 |
| ff | 1.55 | 125 | 0 | 0.5 | +0.284 | 0.505 | 238.2 |
| ff | 1.55 | 125 | 0 | 0.8 | +0.134 | 0.801 | 170.7 |
| ff | 1.55 | 125 | 4 | 0.3 | +0.228 | 0.389 | 290.0 |
| ff | 1.55 | 125 | 4 | 0.5 | +0.189 | 0.507 | 238.2 |
| ff | 1.55 | 125 | 4 | 0.8 | +0.090 | 0.802 | 170.7 |
| ff | 1.55 | 125 | 15 | 0.3 | +0.117 | 0.416 | 290.0 |
| ff | 1.55 | 125 | 15 | 0.5 | +0.098 | 0.514 | 238.2 |
| ff | 1.55 | 125 | 15 | 0.8 | +0.046 | 0.803 | 170.7 |

Worst case is ff 1.55 V 125 C, code 0, pad 0.3 V: +0.35 % error and 290 pA into the pad. At tt the error is below 0.02 % for codes 4 and 15 and 0.012 % at most for code 0. `MSN` is an HV device because an LV `MSN` (W 0.5u L 1u) leaked 9 % of the code 0 current into the ring branch at ff 125 C. `MSP` at W 1u m2 holds with the pad at 0.3 V and code 15.

## Highest usable clock

The `sc_int2` README gives no maximum clock. Its OTA settles with a time constant of 16.2 ns (the 9.8 MHz noise bandwidth entry), and `clk_noverlap` leaves 3.8 to 4.9 ns between the phases. At 1.024 MHz one phase is 488 ns, 30 time constants. Asking for 10 time constants per phase plus the 5 ns gap gives about 2.9 MHz (inference, not simulated). Code 15 at the fastest corner runs at 1.52 MHz (ss 1.45 V -40 C, sim), so it stays below that, with a factor of about 1.9 left. A settling sweep of `sc_int2` against the clock is still to do.

## Open issues

- The bench capacitors `CIN` (200 fF), `CMOD` and `COSC` of the bench are placeholders. The real bank, pad and ESD capacitance on `ibias_in` sets the start-up time, a 1 pF there adds a few microseconds.
- The mux toggle can cut runt pulses into `do_clk_mod` (down to 3 ns). Accepted for static selects changed with `di_ena` low, `clk_noverlap` has not been run against such a runt.
- Cell current with `di_osc_en` low reaches 473 nA at ff 1.55 V 125 C (leakage of the receivers and clamps), 49 nA at tt.
- All numbers are single-run sanity checks, no Monte Carlo. The extracted view runs about 21 % slower than the schematic (see Verification). The frequency needs a trim in the lab.
- Inside `dsm2_core` with the real `bias_gm` bank (schematic, tt, reltol 1e-4) the clock runs at 806.3 kHz with no runts, the shortest phase 620.1 ns, and the cell adds 4.15 uA. The CACE datasheet is not done. `make sim-xschem TB=dsm2_osc_tb_pad` runs. The `pex-mixed` call was taken out of that target because the script was not copied, `sim-cace` still calls it.
- The one-sided (NMOS-only) starving that was asked for to save area does not restore with a Schmitt trigger, see Circuit.


## Layout

`layout/dsm2_osc_gen.py` (`make layout`) writes `layout/dsm2_osc.gds`, 23.56 x 13.09 um, the slot under `bias_gm` in `dsm2_core` (core x 98.44 to 122.0, y 2.0 to 15.09). `PLACE_ONLY=1` writes the placement only, `CHECK_CONTROL=1 make layout` proves a failing check stops the target. `make drc`, `make lvs` and `make pex` run the checks below. The `dsm2_io_rx` instances are read from `macros/dsm2_io/layout/dsm2_io_rx.gds`, the standard cells from the PDK library, nothing of either is redrawn.

### Floorplan

| Part | Where (cell um) | What |
| --- | --- | --- |
| row A | x 1.10 to 22.70, y 0.40 to 4.18 | std row, vss rail on the south edge: `buf_2` (XBM), `mux2_1` (XMUX), `dfrbp_1` (XFF, mirrored so Q sits next to the mux) |
| rx | x 0.67 to 6.05, y 5.10 to 11.78 | XRX0 (mirrored) and XRX1: both gate pads face the middle and take their inputs straight from the north pins |
| row B | x 6.86 to 19.34, y 4.18 to 7.96 | std row flipped onto row A's vdd rail: XI0, XI1, XA, XO1, XO2, XBO (the or2_1), XR3 |
| corner | x 19.34 to 23.25, y 4.2 to 8.0 | MSP (two 1u fingers in row B's well), MGD, MSN (HV, turned by 90 degrees so its TGO window fits between the MSP well and RA) |
| band | x 6.72 to 22.77, y 8.44 to 12.67 | the four rows below |
| rails | y 0.40 (vss), 12.88 to 13.09 (vdd) | Metal1, they are the supply pins |

The analog band, south to north. Every unit is one W 0.5u L 0.5u finger.

| Row | y | West to east |
| --- | --- | --- |
| RA (NMOS, sources down onto row B's vss rail) | 8.44 to 8.94 | DN1, C1 / XTN1, XTN2 / C2, C3 / XTN3, XTN4 / C4, M2 / XTN5, MD (two fingers), C5, DN2 |
| RB (NMOS) | 9.72 to 10.22 | stage switches XN1 to XN5, two 0.5u fingers each, with XK1, XK3, XK5 chained on their west side, then the Schmitt NMOS |
| RC (PMOS) | 10.89 to 11.39 | stage switches XP1 to XP5 with XK2, XK4 on their east side, then the Schmitt PMOS |
| RD (PMOS, sources up onto the vdd rail) | 12.17 to 12.67 | DP1, XTP1, XTP2 / n+ tie / XTP3, XTP4 / n+ tie / XTP5 / MPD, MPK, DP2 |

Stage i of the ring is one column: its NMOS tail in RA, its switches centred on the same x in RB and RC, their gates joined across the well gap and contacted there, its PMOS tail in RD. The tails reach the switches through Metal1 risers in the pad bands. The stages run 1 to 5 west to east, in ring order, with the dummies at both ends of the tail rows (DN1, DN2 in RA, DP1, DP2 in RD). n1 to n4 each hop one stage east. n5 runs back to stage 1 and on to the Schmitt trigger east of stage 5, so it is several stage pitches longer than the other nodes and carries more wire capacitance.

### Pins

All Metal3 stubs except the supplies (cell um):

| Pin | Edge | Position |
| --- | --- | --- |
| `do_clk_mod`, `di_clk_ext`, `d_btest_en` | west | y 2.0, 3.0, 7.6 (x 0 to 1) |
| `di_osc_en`, `di_clk_sel` | north | x 2.16, 4.56 |
| `d_btest_or`, `ibias_in` | north | x 16.50, 21.60 |
| `ibias_pad` | east | y 12.25, x 22.96 to 23.56, abuts the `dsm2_io_esd` `ibias_test` pin |
| `do_osc_oe`, `do_clk_osc` | south | x 0.60, 1.10 (y 0 to 1), west of the core's `do_q` pin |
| `vss` | south | Metal1 rail y 0.18 to 0.62, x 0.20 to 23.36 |
| `vdd` | north | Metal1 rail y 12.88 to 13.09, x 0.20 to 23.36 |

### Metal use

Metal4 is free over the whole cell, so `dsm2_core` can cross it with vi, vcm and their guards on Metal4. Metal3 keeps 1 um from every edge except the pin stubs. Inside, the grid router (`macros/quantizer2/layout/grid_router.py`) uses Metal1 in the band, Metal2 and Metal3. The ring nodes could not be kept off Metal3: the router only converged with every net allowed there. `make layout` prints the Metal3 area per net. The largest are d_osc_en (5.1 um2), d_osc_en_b, d_btest_or, ibias_in and n5. The ring nodes n1, n2, n4, n5 and r1 cross the band on short Metal3 jumpers, n3 does not.

### Verification

All in `registry.iic.jku.at:5000/iic-osic-tools:next` (image dd952ba01866, KLayout 0.30.12, Magic 8.3.685, Netgen 1.5.324), 2026-10-30.

| Check | Command | Result |
| --- | --- | --- |
| KLayout DRC, macro level | `make drc` | clean |
| KLayout DRC, regular level | `make drc` | only the chip-level density rules (AFil.g, GFil.g, M1.j to M4.j, TM1.c), and `layout/drc_regular_check.py` fails on anything else |
| Magic DRC | `make drc` | clean |
| KLayout LVS | `make lvs` | netlists match |
| Magic + Netgen LVS | `make lvs` | circuits match uniquely, 121 devices, 67 nets. Netgen lists only the xschem `mm_ok` tag as property differences. |
| PEX | `make pex` | `netlist/pex/dsm2_osc_magic_pex_3.spice` |

Post-layout tran (sanity check, one run per condition): O's `dsm2_osc_tb_tran` with the schematic and with the extracted view swapped in, code 4, 1.5 V, 27 C. 

| Corner | f do_clk_mod schematic (kHz) | f do_clk_mod PEX (kHz) | Shift | Duty schematic / PEX (%) | Start-up schematic / PEX (us) |
| --- | --- | --- | --- | --- | --- |
| tt | 822.9 | 648.7 | -21.2 % | 50.00 / 49.96 | 0.10 / 0.19 |
| ss | 837.3 | 652.2 | -22.1 % | 50.00 / 49.95 | 0.13 / 0.23 |
| ff | 802.6 | 638.2 | -20.5 % | 50.00 / 49.96 | 0.08 / 0.16 |

The table is from the layout before the second via cuts. After them, tt gives 643.8 kHz (-21.8 %), duty 49.94 %, start-up 0.19 us.

PEX benches of this cell need `.options rshunt` (1e12 here). The PDK `fill_1` cell carries floating poly, which Magic extracts as a node with capacitors only, and the operating point fails without a path to ground. The extracted ring runs about 21 % slower than the schematic, from the wiring capacitance on the ring nodes (inference), so code 4 lands near 650 kHz instead of the schematic's 823 kHz.

Known deviations from the house rules:
- 22 vias stay single cuts, counted per net: vg 6, vbp 4, d_osc_en 3, one each on n1 to n5, r1, net1, do_clk_mod, do_osc_oe. Next to each, a second cut would break a metal or cut spacing. `make layout` added a second cut beside every other one (72 of 94), ring nodes and supplies first.
- The node wires are not equal in length (n5 is the long one, see the floorplan).

## Phase noise

VACASK bench `testbenches/xschem/dsm2_osc_tb_pnoise.sch`: the sources and loads of `dsm2_osc_tb_tran`, `di_osc_en` and `di_clk_sel` held high, `di_clk_ext` held low, so the cell runs free, and an ideal noiseless current source on `ibias_in` (code 4, 200 nA). Every number below is a sanity check of the schematic at tt 1.5 V 27 C code 4 (sim), not a characterisation, and no run failed.
The launchers Simulate PSS and pnoise, Simulate transient noise and Plot call `testbenches/vacask/run.sh`, the same entry point as the command line:

```sh
sak-pdk ihp-sg13cmos5l                      # in IIC-OSIC-TOOLS
cd testbenches/vacask
./run.sh tnoise --seeds 3,4 --tstop 1e-3    # transient noise of the whole cell, about 3 h per 1 ms record on a loaded host
./run.sh pnoise --truncharm 50              # oscillator PSS and pnoise of the ring, about 15 min
./run.sh post                               # runs/summary.md and runs/pnoise.png
```

`netlist.py` netlists the sheet for spectre and adds `dsm2_osc_ring`, the cell without the divider and the output gates (the flip-flop clock input stays as load), for the periodic analyses at the ring period. `pnoise.py` writes and runs the decks with `swign=0` model cards, `post.py` evaluates. Options: `--corner`, `--temp`, `--vdd`, `--code`, `--seeds`, `--tstop`, `--noisefmax`, `--truncharm`, and for the evaluation `--nseg` (Welch segments per record, default 4) and `--demean`.

The result comes from transient noise (sde, `tran_noiselte=1e6`, `noisefmax` 1 GHz, `noisefmin` one over the record, 0.5 ns maximum step): the rising edges of `do_clk_osc` give the period jitter directly and the excess phase at each edge. L(f) comes from the Welch PSD of the period-to-period phase difference, S_phi = S_dphi / (4 sin^2(pi f / f0)), up to half the clock frequency: the phase itself is a random walk, and windowing it biases the lowest bins. The oscillator PSS works (823.05 kHz at `do_clk_osc`, the ngspice transient gives 822.9 kHz), but pnoise does not hold the phase mode of this ring: its L(f) never shows the 1/f^2 skirt and rises by 17 dB and then 4 dB from truncharm 25 to 50 to 100, 18 dB below the transient noise at 100 kHz at truncharm 100 (35 min, 2.4 GB), so pnoise stays in the bench as documentation only.

| quantity | value |
| --- | --- |
| clock frequency with noise, 2 seeds of 1 ms | 821.6 kHz (noiseless 823.2 kHz) |
| period jitter, 1 clock | 4.58 +- 0.08 ns rms (1624 periods, flicker from 1 kHz) |
| jitter accumulated over 16 clocks | 49 +- 3.5 ns rms |
| L at 4 to 8 kHz, 8 to 16 kHz, 32 to 64 kHz, 64 to 128 kHz, 256 to 411 kHz (Welch, 4 segments per record) | -52.3, -62.8, -80.0, -89.3, -100.9 dBc/Hz |
| fit L = a/f^2 + b/f^3 (model) | a = 4.29 Hz, b = 3.16e5 Hz^2, white and flicker FM equal at 74 kHz |
| L from the fit at 1 kHz, 10 kHz, 100 kHz (model) | -34.9, -64.4, -91.3 dBc/Hz |
| absolute jitter from the fit, 1 kHz to 411 kHz (model) | 110 ns rms, 97 to 119 ns with 2 to 8 Welch segments |

The skirt is flicker FM up to about 100 kHz offset: the ring tails are single 0.5u/0.5u fingers at about 100 nA, whose drain noise is 94 % flicker at 10 kHz (sim, noise analysis of one such device). The period jitter grows with the flicker included, 3.96 ns with flicker from 5 kHz (200 us records) and 4.58 ns from 1 kHz, the fit gives 5.0 ns down to 1 Hz. Below about 600 Hz the fitted phase wander exceeds 1 rad, so L(f) there is not a small-angle quantity and the jitter numbers with their limits are the useful form. Checks: the noiseless run on the same time grid gives 0.12 ns period jitter, `noisefmax` 3 GHz gives 3.63 +- 0.21 ns against 3.61 and 4.28 ns for two 1 GHz seeds of the same length, and the Schmitt output over two ring periods gives the same jitter as `do_clk_osc` (4.60 ns), so the divider and the output gates add nothing visible.
Welch segment length: from 32 kHz up the bands move by 0.5 dB or less between 2, 4 and 8 segments per record, 16 to 32 kHz by 1.8 dB and 8 to 16 kHz by 2.9 dB, the lowest one or two bins of each estimate reading high. The fit coefficients move by about 20 % with it (b 2.5e5 to 3.7e5 Hz^2). All seeds start from the same kicked state, but `post.py --demean` (across-seed mean subtracted, scaled by N / (N - 1)) shows no common drift: the bands move by -0.7 to +1.7 dB and the lowest ones not downwards, so it stays off, with two seeds it would also halve the averaging.
One seed of 200 us each (flicker from 5 kHz, compare with 3.96 ns at tt): ss 4.04 +- 0.23 ns and ff 4.08 +- 0.23 ns period jitter at code 4, code 15 at tt 2.11 +- 0.09 ns at 1483 kHz, about the same fraction of the period as code 4.

### Supply current split

VACASK transient at tt 1.5 V 27 C code 4, a 0 V source in the `vdd` connection of every device and standard cell, averaged over 12 clock periods (sim). The cell takes 5.07 uA, of which the Schmitt trigger takes 4.15 uA (`XSN3` 2.71 uA, `XSP1` 1.43 uA), the ring tails 0.28 uA, `MPD` 0.19 uA, the output and divider cells 0.45 uA (`XBM` 0.14, `XO2` 0.10, `XFF` 0.10, `XR3` 0.06, `XMUX`, `XA`, `XO1` 0.04 together), the receivers and static gates below 1 nA. The Schmitt current is crowbar during the slow ring edges: `n5` rises in 148 ns and falls in 200 ns (10 to 90 %), and `XSN3` peaks at 50 uA and stays above 2 uA for about 200 ns per clock period. The charge per edge grows with the edge time as the frequency falls, which is why the running current hardly depends on the code.
