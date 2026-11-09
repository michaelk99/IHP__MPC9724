# dsm2_core Measurement Plan for the DSA1 Die

Every lab number gets a simulated or modelled value to compare against, written down before tapeout (2026-11-09). All predictions are sanity checks from single runs or from the system model, not characterisation, and the lab numbers are checks of the models in the same sense. Nothing in a prediction column is a spec.

Prediction tags: (sim, schematic), (sim, extracted), (model) for `macros/dsm/scripts/dsm_system.py` and `macros/quantizer2/scripts/dither_deadzone.py`, (inference) for a reading of those results without its own run. "Pending, due <date>" means the run is still going and the cell gets filled then. Conditions are tt, 1.5 V, 27 C unless stated. Nothing in the silicon will sit exactly at tt, the correlation rules in section 5 say how far it may move.

## 1. Setup

| Item | What the bench provides |
| --- | --- |
| VDDA | one supply for the `vdd` pad of `dsm2_core`, 1.5 V, current measured by an SMU or a DMM in series. Own segment of the pad ring, nothing else of DSA1 sits on it. The `ibias_test` current also flows through it |
| Board rules | VDDA on and up no later than IOVDD and VDD, so `di_ena` reaches the core as an edge at full VDDA. With VDDA off keep `vi`, `vcm` and `ibias_test` below 0.3 V (the ESD diodes and the `MBS` drain diode would feed `vdd`). `ibias_test` held at 0.3 to 0.8 V by an SMU or through at most 1.5 Mohm to ground at all times while VDDA is up, 10 Mohm saturates the copy |
| Clock | `di_clk`, 1.024 MHz from a generator with a 10 MHz reference input that also locks the tone source. The pad level is set by IOVDD and the core sees it at 1.5 V. Frequency and duty cycle adjustable for section 2 rows C25 and C26 |
| Controls | the 12 control bits, written over SPI by the host. Reset defaults in the table below, the names on the DSA1 side are in the mapping table |
| Bit stream | `do_q` and `do_q_b` pads (4 mA drivers, pad load 80 fF in the sims) into a logic analyzer, at least 2^20 clocks per record. `do_q_dec` goes to the DSA1 decimator, with the decimator source select set to the core, the decimated words are readable over SPI as a cross-check (the clock then has to come from one source with `di_clk` inverted) |
| `vi` | low-noise source around `vcm`, DC from an SMU, tone from a source whose in-band noise is below 10 uVrms (an RC filter after the generator, checked with the pad shorted to `vcm`). Full scale is 0.75 V around `vcm`, -6 dBFS is 0.375 V peak |
| `vcm` | read by an electrometer or buffer with at least 10 Gohm input. A scope probe (10 Mohm) against the 1 Mohm output resistance of the pump reads 9 % low. Driven by a 0.75 V source with `di_vcm_ext` high |
| `ibias_test` | SMU at 0.5 V, reading the current. A 1 Mohm resistor to ground is the fallback (nA read as mV) |
| Environment | 27 C ambient. A hot plate point is optional, the predictions below are at 27 C |

Reset defaults of the 12 control bits:

| Bit | Reset | Meaning |
| --- | --- | --- |
| `di_ena` | 1 | core on from reset (DSA1 chip-level inverter) |
| `di_rst_b` | 0 | quantizer in reset, released by a DSA1 timer 9 clocks (137 us) after the chip `rst_n` |
| `di_trim[3:0]` | 0100 | bias 200 nA |
| `di_dith_en` | 0 | dither off |
| `di_dith_amp[1:0]` | 01 | 67 % when the dither is turned on |
| `di_btest_en` | 0 | `ibias_test` off |
| `di_vcm_ext` | 0 | internal `vcm` |
| `di_qout_en` | 1 | `do_q` and `do_q_b` drive the pads from reset (DSA1 chip-level inverter) |

Names on the DSA1 side (registers `BIAS_CFG_0` and `BIAS_CFG_1`, from its register map, this is the only place they appear here):

| Core pin | `di_ena` | `di_rst_b` | `di_trim` | `di_dith_en` | `di_dith_amp` | `di_btest_en` | `di_vcm_ext` | `di_qout_en` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DSA1 field | `DSM_EN` | `DSM_RST_B` | `DSM_TRIM` | `DSM_DITH_EN` | `DSM_DITH_AMP` | `DSM_BTEST_EN` | `DSM_VCM_EXT` | `DSM_QOUT_EN` |

In the oscillator variant (section 7), `di_osc_en` and `di_clk_sel` are two bits of `DSM_SPARE` (`BIAS_CFG_0[9:7]`), the bit order is DSA1's. `do_clk_osc` drives the bidirectional `dsm_clk` pad with `do_osc_oe` as its output enable.

`di_dith_amp` codes: 00 is 100 % (76.5 mV peak of the integrator output at tt), 01 is 67 %, 10 is 133 %, 11 is 33 %.

With the DSA1 reset defaults the modulator runs from power-up with no SPI write: `di_ena` reaches the core as an edge at full VDDA (board rule VDDA up no later than VDD) and the timer releases `di_rst_b` 137 us later. Start-up sequence after any SPI change: set trim, dither and the test bits with `di_ena` low, raise `di_ena`, wait 130 us (slowest corner of the bias start-up), release `di_rst_b` at least 2 clocks later. The integrator saturates during reset and needs about 17 clocks after the release to recover (sim, vi = +0.3 V), so discard the first decimator output. Trim changes only with `di_ena` low. `di_btest_en` is a static setting, its edge kicks `ibias_200n` by up to 37 % and it settles within 99 us, so wait 1 ms after any change. `di_qout_en` is set before the record starts.

## 2. Configurations

Every configuration starts from the baseline and changes only the listed items. `vi` is `vcm` plus 0.3 V for the current readings (as the extracted op check), a tone or a DC sweep for the stream readings.

| Id | Change from baseline | Purpose |
| --- | --- | --- |
| C0 | baseline: dither off, btest off, trim 4, internal `vcm`, `di_clk` 1.024 MHz, `di_qout_en` 1 | first and last (drift check) |
| C1 to C4 | dither on, `di_dith_amp` 00, 01, 10, 11 | dither cost, amplitude, dead zone |
| C5 | btest on at trim 4, SMU 0.5 V | supply delta, test copy |
| C6 to C21 | btest on, trim code 0 to 15 (`di_ena` low while changing) | bias current against code, SNDR against bias |
| C22 | `di_vcm_ext` high, 0.75 V on `vcm` | offset of the internal `vcm`, pump off |
| C23 | `di_vcm_ext` high, 0.70 V on `vcm` | shows that the pin sets the common mode |
| C24 | `di_qout_en` low | pad outputs static, `do_q_dec` only |
| C25 | `di_ena` low | power down |
| C26 | `di_clk` 0.256, 0.512, 2.048 MHz at 50 % duty | frequency steps |
| C27 | `di_clk` 1.024 MHz at 30 %, 40 %, 60 %, 70 % duty | clock edge margin |
| C28 | supply 1.45 and 1.55 V (optional) | supply sensitivity |

## 3. Measurements and predictions

### 3.1 VDDA current (average)

Measured with `vi` at `vcm` plus 0.3 V, pad drivers loaded by the board. The schematic window-peak values are not measurable on the bench and stay in the `dsm2` README.

| Config | Prediction | Tag, source | Status |
| --- | --- | --- | --- |
| C0 | 12.24 uA schematic, 13.59 uA extracted | (sim, schematic) and (sim, extracted), op check table of `macros/dsm2/README.md`, 40 clocks, DC +0.3 V | done |
| C0, tone at -6 dBFS | 10.69 uA | (sim, schematic), supply current table of `macros/dsm2/README.md`, 300 clocks, earlier dither ladder, before `dsm2_io_esd` | done, differs from the row above by 1.55 uA, open (3.8) |
| C1 to C4 | 12.77 uA at amplitude 00 (schematic) | (sim, schematic), same section, 150 clocks, one run. The ladder runs while `di_en` is high, so the other codes should read the same (inference) | dither off with the present ladder: open (3.8) |
| C5 | baseline plus 0.29 uA | (sim, schematic), 10.98 against 10.69 uA, earlier ladder, pad at 0.5 V | done |
| C6 to C21 | baseline plus the change of `ibias_test` | (inference), the copy current flows through VDDA | no number |
| C24 | baseline minus the pad driver charge | (inference) | no number, not simulated |
| C25 | below the baseline by almost all of it. Parts: 1.2 to 3.4 nA of the 12 receivers (tt, inputs low and at 1.08 V) | (sim, schematic), `macros/dsm2_io/README.md`. The rest of the core off is not simulated | open, no core-level run (3.8) |
| C26 | rises with the clock frequency | (inference) | no number |
| Corner window | 9.0 uA (ss 1.45 V -40 C) to 21.25 uA (ff 1.55 V 125 C) | (sim, schematic), same table | done |

### 3.2 `ibias_test` against trim code (C5 to C21)

Pad at 0.5 V. Prediction is 193.71 nA times 16 plus 2 times the code, divided by 24 (core mirror of 24 units, trim of 16 plus 2 per code), (sim, schematic), `macros/bias_gm/README.md` (op at code 4, trim sweep 0.999 to 1.012 of the unit count at every code). The extracted view reads 192.53 nA at code 4 (-0.6 %).

| Code | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nA | 129.1 | 145.3 | 161.4 | 177.6 | 193.7 | 209.9 | 226.0 | 242.1 |

| Code | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nA | 258.3 | 274.4 | 290.6 | 306.7 | 322.9 | 339.0 | 355.1 | 371.3 |

Status: done (sim). The pad voltage dependence over 0 to 0.8 V is under 1.4 %, the test copy over `ibias_200n` is 0.9998 to 1.0046 over corners with 1.39 % mismatch sigma at code 4. The README quotes 191.35 nA for `bias_gm_tb_op` in one place and 193.71 nA in the PEX table, the plan uses 193.71 nA.

### 3.3 `vcm` voltage (pin mean, C0 and C22 to C23)

| Config | Prediction | Tag, source | Status |
| --- | --- | --- | --- |
| C0 | 0.753 V schematic, 0.756 V extracted | (sim, schematic) and (sim, extracted), op check table of `macros/dsm2/README.md`. `vdd/2` is 0.750 V | done |
| C0, error at the sampling instant | -1.4 to -2.3 mV (earlier version), +4.3 to +8.2 mV in the `vcm_gen` bench | (sim, schematic), `macros/dsm2/README.md` and `macros/vcm_gen/README.md`, different read instants | done |
| C0, ripple at the sampling instant | 45 to 79 mV peak to peak | (sim, schematic), same sources, not visible on the pin mean | done |
| C22 | source current under 0.33 nA with the pump off | (sim, schematic), `macros/dsm2_io/README.md`, -0.6 to 327 pA | done |
| C23 | source current 45 to 51 nA at +50 mV with the pump running, pad leakage of the ESD cell 63 pA at 27 C | (sim, schematic), same | done |

### 3.4 SNDR at -6 dBFS and in-band floor (C0 to C4, C6 to C21, C22, C26, C27)

| Config | Prediction | Tag, source | Status |
| --- | --- | --- | --- |
| C0, C1 | schematic SNDR and floor, dither off and on, full record | (sim, schematic) | pending, due 2026-11-02 |
| C0 | extracted SNDR | (inference) = schematic SNDR minus the shaped-floor difference, extracted against schematic. The extracted runs are 1536 clocks (512 settling plus a 1024-clock window), so they give no in-band SNDR, only the floor over 8 to 128 kHz in dBFS per 1 kHz bin. A single run carries about 3 dB of floor scatter, a smaller difference is not significant | pending, due 2026-11-08. The results go into the dsm2 README when the runs end. The view is the schematic core with `sc_int2` and `quantizer2_top` extracted, the full extraction does not finish by then |
| C1 | extracted SNDR, dither on | (inference), same method, dither off against on on the mixed view | pending, due 2026-11-08 |
| C0 | ceiling 76.9 dB (floor -81.1 dBFS) | (model), `dsm_system.py --fres 1 --a0-db 71.3 --noiseless`, no device noise, leak of the `sc_int2` schematic | done |
| C1 to C4 | 73.1 dB (00), 74.8 dB (01), 71.9 dB (10), 77.0 dB (11) | (model), same with `--qdither-v 76.5e-3, 50.1e-3, 104.4e-3, 23.3e-3 --qdither-kind lfsr8`, quantization only | done |
| C0 and C1 at -20 dBFS | 68.4 dB and 59.8 dB | (model), same, `--ampl-dbfs -20` | done |
| C0, C1 earlier deck | 83.5 dB (dither off, 1 run) and 72.4 dB (dither on, 4 seeds, 67.7 to 80.4) at -6 dBFS | (sim, schematic), "In-band SNDR" of `macros/dsm2/README.md`, previous quantizer deck, 13 uVrms input dither | superseded by the wave 4 runs |
| C6 to C21 | SNDR against bias | no prediction. Direction: lower code, more settling error (inference) | no number |
| C22 | equal to C0 within 1 dB | (inference), only the pump is off | no number |
| C26 | quantization-only ceiling 56.8, 65.0, 76.9, 84.5 dB at 0.256, 0.512, 1.024, 2.048 MHz (dither on: 55.0, 64.2, 73.1, 82.8 dB), band 1 kHz, OSR fs/2000 | (model), same script with `--fs` and `--osr`. No circuit run at another clock | done for the model only |
| C27 | no prediction. The phase gap of 3.3 to 7.4 ns comes from the inverter chain of `clk_noverlap` and does not follow the duty (inference) | | no number |

### 3.5 DC transfer, dead zone, stream mean

The stream mean is `2 mean(do_q) - 1` over a record. Expected mean is `(vi - vcm) / 0.75 V` times the gain plus the offset. Dead zone is the span of `vi` around zero over which the mean moves by less than 0.03 mV of input.

| Config | Quantity | Prediction | Tag, source | Status |
| --- | --- | --- | --- | --- |
| C0 | mean at +0.3 V and -0.3 V | 0.4226 and -0.3912 (schematic), 0.4180 and -0.3822 (extracted), expected without offset 0.400 | (sim, schematic) and (sim, extracted), 2048-clock runs of "Schematic against the full RC PEX view", means over 440 clocks resolve 0.0045 | done |
| C0 | offset, gain | offset +0.016 to +0.020 over five corners, both views (about 12 to 15 mV at the input), gain 1.00 within 0.01 | (sim, schematic) and (sim, extracted), same table | done |
| C22 | offset with known `vcm` | the same offset less the `vcm` error of 3.3 | (inference) | no number |
| C0 | dead zone width, dither off | 0.12 mV (leak 2.72e-4 per cycle, schematic) and 0.14 mV (3.41e-4, extracted) | (model), `dither_deadzone.py`, fine sweep, 0.1 mVrms input noise | done |
| C1 to C4 | dead zone width, dither on, code 00, 01, 10, 11 | schematic leak (71.3 dB): 0.05, 0.08, 0.03, 0.11 mV. Extracted leak (69.3 dB): 0.06, 0.10, 0.03, 0.13 mV | (model), `dither_deadzone.py` run on 2026-10-30, fine sweep, 0.01 mV steps, tt amplitudes 76.5, 50.1, 104.4 and 23.3 mV | done |

### 3.6 Idle tone near zero input

Highest in-band bin (3 to 256 of a 2^18 record, 3.9 Hz bins, periodic Hann, mean removed) in dBFS, `vi` at `vcm` plus the listed offset. Leak 71.3 dB, dither amplitude 00 for "on", from a scratch script that reuses the loop of `dither_deadzone.py`.

| Offset (mV) | off, no noise | on, no noise | off, 0.1 mVrms | on, 0.1 mVrms |
| --- | --- | --- | --- | --- |
| 0 | below -300 (exact 0101 pattern) | -90.6 | below -200 | -91.0 |
| 0.25 | -64.3 | -71.9 | | |
| 0.5 | -58.0 | -67.3 | -66.6 | -74.9 |
| 1.0 | -120.8 | -88.8 | -84.6 | -88.0 |
| 2.0 | -105.8 | -90.3 | | |

(model). The spur sits at the pattern frequency, fs times the mean divided by 2, so it is in band below about 1.5 mV of offset. Dither on lowers it by 7 to 9 dB at 0.25 and 0.5 mV and raises the floor above 1 mV. Real noise of the chip is larger than the model's, so the silicon spur should be at or below the "0.1 mVrms" column (inference).

### 3.7 Dither amplitude

Out-of-band floor lift of the stream against dither off, power averaged over 10 to 50 kHz, tone at -6 dBFS, (model, `dsm_system.py`, 1 Hz bins, noiseless):

| Code | 11 (33 %) | 01 (67 %) | 00 (100 %) | 10 (133 %) |
| --- | --- | --- | --- | --- |
| 10 to 50 kHz | +0.8 dB | +2.2 dB | +3.7 dB | +5.2 dB |
| 50 to 200 kHz | +0.5 dB | +1.7 dB | +3.2 dB | +4.6 dB |
| 200 to 500 kHz | 0.0 dB | 0.0 dB | 0.0 dB | -0.1 dB |

Integrator swing grows with the dither, +23 mV (11) to +104 mV (10) peak against 375 mV, which is not observable (model).

### 3.8 Open points of the predictions

- Baseline current: 10.69 uA (tone, 300 clocks) against 12.24 uA (+0.3 V DC, 40 clocks) for the same tt schematic with dither and btest off. The decks differ in the stimulus, the length, the dither ladder (the first predates it) and `dsm2_io_esd`. Which of these makes the 1.55 uA is not established, no run isolates it. The correlation rule in section 5 covers both values.
- `bias_gm` at code 4: the README quotes 191.35 nA in the bench description and 193.71 nA in the PEX table (193.714 nA from `bias_gm_tb_op` on both hosts). The plan uses 193.71 nA, the 1.2 % gap is inside the 3 % limit of section 5 and its cause is open.
- Dither off with the present ladder (2.58 uA) is not simulated. C1 to C4 are compared against the 12.77 uA run, C0 against the two values above.
- Power down (C25) has no core-level simulation. Only the receiver leakage and the `vcm` drift are simulated, so the first lab reading has no full prediction.
- The wave 4 SNDR table of `macros/dsm2/README.md` has no "previous version" note, the rows of 3.4 that come from it carry the note here.

## 4. Procedures

- **Power-up.** `vi`, `vcm` and `ibias_test` at 0.5 V or below, VDDA up, IOVDD up, SPI write of the defaults, then the start-up sequence of section 1. Record the supply current 1 ms after reset release as the reading.
- **PSD record.** `vi` is a tone at -6 dBFS (0.375 V peak), coherent: bin 749 of 2^20 is 731.4 Hz, with the generator and the clock on one 10 MHz reference. Capture 2^20 clocks (1.02 s, 0.98 Hz bins) after 1 ms of settling, sample on the clock edge, never on analyzer time points. Subtract the mean, apply a periodic Hann window (never the symmetric one), exclude 5 bins at the tone and 2 at DC, sum bins up to 1 kHz. Take 4 records on tone bins 749, 751, 757 and 761, report each and the power average. A first-order loop is chaotic, one record scatters by several dB. The minimum record for a band of 1 kHz is 16384 clocks, which gives only 16 bins and is not enough for a number.
- **DC sweep.** `vi - vcm` of 0, plus and minus 0.1, 0.25, 0.5, 1, 2, 5, 50, 150, 300, 600 mV and the fine sweep plus and minus 1.5 mV in 0.02 mV steps. Record 2^18 clocks per point after 2 ms of settling. Read `vcm` before and after each point and use the mean as the reference. Source resolution under 0.01 mV. Dead zone from the fine sweep with the 0.03 mV rule, and once with `di_vcm_ext` high (C22).
- **Idle tones.** Records of 2^18 clocks at the offsets of 3.6, same window as the PSD record, report the highest bin below 1 kHz.
- **Current.** Average over 1 s after 1 ms of settling, `vi` at `vcm` plus 0.3 V. For the clock steps read at each frequency and fit the slope against frequency.
- **`ibias_test`.** Current over 1 s at each code with the pad at 0.5 V. At code 4 also at 0.3 V and 0.8 V.
- **`vcm`.** Electrometer, 10 s mean. Source current for C22 and C23 by the SMU, 10 s mean.
- **Power-down.** `di_ena` low, reading after 10 ms, then restore and compare the baseline.
- **Order.** C0 first, then C1 to C4, C5, C6 to C21 (every code is a `di_ena` toggle), C22, C23, C24, C25, C26, C27, C28 if done, and C0 again at the end. The second C0 is compared with the first: current within 2 %, `vcm` within 2 mV, stream mean at the baseline points within 0.005, SNDR of the 4-record average within 3 dB. A larger change is drift and the series is repeated.

## 5. Correlation rule

The limits are the plan author's choice from the spreads named in the reason column, none is a sourced spec or a design limit.

| Quantity | Agrees if | Reason |
| --- | --- | --- |
| VDDA current, C0 | within -10 % to +20 % of the extracted value | corner spread at 27 C is -5 % to +12 % in the sims, the extracted view reads 10 % above the schematic |
| Current deltas (dither, btest) | within 0.5 uA of the schematic delta | single sims, the baseline cancels |
| `ibias_test` ratio between codes | each code within 3 % of the 16 plus 2 code scaling to code 4 | bank mismatch 1.39 % sigma, trim 0.999 to 1.012 |
| `ibias_test` absolute at code 4 | 0.75 to 1.35 times 193.7 nA, and the shift reported | rhigh corners move the core by -22 % and +31 %, the trim is there for it |
| `vcm` | within 10 mV of 0.750 V | sims 3 to 6 mV over the views, flying cap plate capacitance unknown at 0.54 mV per fF |
| SNDR and floor | within 3 dB of the extracted prediction, using the 4-record average | records of the same loop scatter by up to 13 dB, the average narrows it |
| Dead zone | both widths under 0.5 mV and dither on not wider than off | model 0.03 to 0.14 mV, real noise and bench resolution hide the rest |
| Idle tone | silicon spur at or below the model's noisy column plus 6 dB | model is noiseless or has 0.1 mVrms only, bin scatter |
| Stream mean | gain 1.00 within 0.01, offset 0.016 within 0.012 | corner and view spread is 0.005, source and `vcm` errors add the rest |
| Dither floor lift | the four lifts rise in the order 33, 67, 100, 133 % and each is within 1.5 dB of the model | the floor between 10 and 50 kHz is dominated by shaped quantization noise |
| Frequency steps | SNDR rises by 7 to 10 dB per doubling up to the frequency where it collapses, the collapse frequency is reported | the model ceiling gives 8.2 to 9.0 dB per doubling and nothing models the settling limit |

## 6. Test mode coverage

Rating: yes means the quantity is fully observable with the pins above, partly means an inference or a mix of effects. Closing options in order: (a) procedure or board only, (b) DSA1 chip-level glue or the 3 spare register bits of DSA1, which drive nothing today, (c) a change inside `dsm2_core`. `dsm2_core` is frozen at 6dd2926 and integrated, so (c) is a flagged recommendation and never a plan item.

| Measurement | Controls and pins | Observable | Missing and cheapest closure |
| --- | --- | --- | --- |
| VDDA current | `vdd`, C0 to C28 | partly | Total only, no split between bias, clock tree, quantizer, dither ladder and pad drivers. (a) Differences between configurations (dither, btest, qout, frequency slope) give the split. (c) Separate supply pins per block, risk: floorplan and ESD, not recommended |
| `ibias_test` against trim | `ibias_test`, `di_btest_en`, trim | partly | The copy is a second bank with 1.39 % mismatch to the bank that feeds the OTA, and the pad sits at 0.5 V against the OTA pin at 0.6 V. The real `ibias_200n` is inferred. (a) SNDR against trim code, supply delta against `ibias_test`, and a pad sweep 0.3 to 0.8 V. (c) Not recommended, the copy is the intended access |
| `vcm`, internal | `vcm` pad, `di_vcm_ext` low | partly | The pin shows the mean, the integrator sees the value at its sampling instant, and a meter loads a 1 Mohm node. (a) 10 Gohm meter, then compare the stream mean offset between C0 and C22 (known `vcm`) to get the error the loop sees. Pump ripple is not visible |
| SNDR, floor | `do_q`, `vi`, clock | partly | Integrator, switches, quantizer, `vcm`, clock jitter and the source add into one number. Quantizer errors are shaped away, so the floor mostly belongs to the integrator and the input. (a) Input shorted to `vcm` for the noise floor alone, SNDR against trim and frequency for settling, dither on and off. (c) A buffered tap of the integrator output would separate them, risk: leakage and kickback on a node that sets the dead zone |
| DC transfer, dead zone | `do_q` mean or decimated words, `vi` | yes | Offset is the sum of the `vcm` error, charge injection and the quantizer. (a) C22 against C0 separates the `vcm` part. The dead zone is below the source resolution when dither is on |
| Stream mean | same | yes | As above |
| Idle tone | `do_q`, `vi` | yes | The real noise level of the source limits the lowest spur, (a) a battery-fed divider as input |
| Dither amplitude | `di_dith_amp`, `do_q` | partly | Not observable directly. (a) Floor lift in 10 to 50 kHz, the table of 3.7, and the dead zone ordering. The lift hides under real noise if the floor is above the model. (c) A pad for the dither bits or a step response, not recommended |
| Clock non-overlap margin | `di_clk` duty and frequency, `do_q` | partly | The gap of 3.3 to 7.4 ns is made inside by the inverter chain, an external duty or frequency scan moves the phase widths and not the gap. The scan finds where settling fails, not the gap. (a) Scan duty 30 to 70 % and frequency to 2.048 MHz, read `do_q` delay from `di_clk` on the logic analyzer (2.6 to 4.3 ns in the sims) and the SNDR collapse. (b) A DSA1 delay element on `di_clk` could shift the edges, not asked for. (c) Phase tap pads, risk: coupling into the sampling clocks |
| Start-up | `di_ena`, `ibias_test` with btest on, `do_q` | yes | Bias start-up of 20 to 131 us shows on `ibias_test` through the 1 Mohm fallback on a scope, the first bits after reset on `do_q`. (a) Only. `vcm` start-up of 11 to 12 clocks is not visible |
| Power-down | `di_ena` low, `vdd`, `vcm` | partly | Leakage reads on VDDA, `do_q` holds low and `do_q_b` high (sim). `vcm` drifts, +2.3 mV in 200 us at tt (sim), seen only through a meter. (a) Sequence of readings in time |

Notes. The decimator path (decimator source select) carries the same bits at 1/128 of the rate, so it adds no observability and is only a cross-check on the capture. The three spare register bits have no wire to the macro, so using them is a DSA1 netlist change and not a procedure. No row needs a change inside `dsm2_core` for the plan to run, the (c) entries are only what would sharpen the separation of integrator from quantizer.

## 7. On-chip clock (variant dsm2-osc, taped out on DSA1)

This section applies only to the die variant with `dsm2_osc` in `dsm2_core`. Source: `macros/dsm2_osc/README.md` and its task report, schematic only (27 clock runs, 63 pad points, none failed), one run per condition, ideal current source in place of the real `bias_gm` bank, 200 fF on `ibias_in`, 80 fF on `do_clk_osc`. Extracted numbers come from the layout task (OL): pending, due 2026-11-01. All values are (sim, schematic) sanity checks unless tagged otherwise.

| Id | `di_osc_en` | `di_clk_sel` | Modulator clock | Purpose |
| --- | --- | --- | --- | --- |
| O0 | 0 | 0 | `di_clk` | baseline, the ring is off and `ibias_test` goes to the pad as in sections 1 to 6 |
| O1 | 1 | 0 | `di_clk` | ring runs, modulator still on the external clock: ring current and pad leakage without a clock change |
| O2 | 1 | 1 | ring divided by 2 | modulator on the chip clock |

Trim code 0, 4 and 15 in each, `di_btest_en` as the config needs (the bank is forced on while `di_osc_en` is high). The pad of `do_clk_osc` shows the clock while `di_osc_en` is high. Its assignment to a DSA1 pad is not checked here. With O2 the clock pad is an output (`do_osc_oe`, inference from the README), so the generator on `di_clk` is disconnected or high-Z first.

Rule: switch `di_osc_en` and `di_clk_sel` only with `di_ena` low and `di_rst_b` low. The ring needs `di_ena` high, because `bias_gm` starves its test bank while `di_ena` is low. `di_clk_sel` sets the pad to output whatever `di_osc_en` is, so never set `di_clk_sel` high with `di_osc_en` low: the pad would then drive low against the generator. Raising `di_osc_en` enables the bank like a `di_btest_en` edge. The mux can cut runts down to 3 ns into `do_clk_mod` (ff 1.55 V 125 C code 15, 260 ns at tt code 4) and `clk_noverlap` is not checked against them.

| Quantity | Config | Code 0 | Code 4 | Code 15 | Source and status |
| --- | --- | --- | --- | --- | --- |
| Frequency at `do_clk_osc` (kHz), tt 1.5 V 27 C | O1, O2 | 565.9 | 822.9 | 1479.1 | clock table, `do_clk_mod` after the select. Equal at `do_clk_osc` is an inference. Extracted (2026-11-07): 443.3, 643.8, 1154.8 |
| Frequency over all 9 conditions (kHz) | O1, O2 | 502.6 to 577.2 | 733.0 to 839.6 | 1327.6 to 1516.9 | same table, corners at 1.5 V 27 C, ss 1.45 V -40 C, ff 1.55 V 125 C and supply 1.45 and 1.55 V |
| Frequency per bank current (kHz per nA) | O1, O2 | 4.25 | 4.12 | 3.86 | same table divided by 8.33 nA times (16 + 2 code), tt |
| Duty (%) | O1, O2 | 50.0 | 50.0 | 50.0 | flip-flop divides, all 27 runs. Extracted: pending, due 2026-11-01 |
| Supply, cell running minus cell off (uA) | O1, O2 | 4.74 | 5.03 | 5.68 | I running 4.79, 5.08, 5.73 uA less I off 48.9 nA, tt, bank current excluded. Extracted: pending, due 2026-11-01 |
| VDDA delta from O0 with bank current added (uA) | O1 | 4.87 | 5.23 | 6.06 | the row above plus 8.33 nA times (16 + 2 code) (inference, the bank is ideal in the sim). O2 adds the change of the modulator current with the clock, no number |
| `ibias_test` pad error, `di_osc_en` low, pad 0.5 V (%) | O0 | -0.001 | -0.001 | -0.001 | `ibias_pad` over `ibias_in` minus 1, tt. Worst case ff 1.55 V 125 C +0.28, +0.19, +0.10 |
| `ibias_test` leakage into the pad, `di_osc_en` high, pad 0.5 V | O1, O2 | 1.2 pA | 1.2 pA | 1.2 pA | tt. 2.1 pA at 0.3 V, 0.6 pA at 0.8 V. Worst case ff 1.55 V 125 C 238 pA at 0.5 V. Extracted: pending, due 2026-11-01 |
| SNDR at -6 dBFS | O2 | | | | Tone tests only: (inference) a tone SNDR reads about 49 dB (48.0 to 49.7 dB) for the 687.5 Hz tone, whatever the amplitude, because the free-running clock's close-in phase noise (flicker FM, dominant up to about 100 kHz offset) smears the tone into the neighbouring in-band bins. This is a time-base effect of indexing the samples by a wandering clock, not noise added in the analog path, and it does not affect DC readings, which see no input slope. Short-term period jitter is negligible: 4.6 ns on the 687.5 Hz, -6 dBFS tone is about 7.5 uV peak, about 94 dB below the tone. The 49 dB is rough, because the phase-noise fit is extrapolated below 4 kHz, the fitted phase wander exceeds 1 rad below about 600 Hz, and no oscillator-clocked dsm2_core spectrum exists. It is for the schematic code-4 clock of 822.9 kHz. At the lab's 1.024 MHz (code 10 to 12) the (fin / fclk)^2 scaling alone gives about 51 dB, with the phase noise at the higher bias not rerun. It is the clock phase noise (transient noise, tt code 4, phase-difference estimator, flicker fit below 4 kHz, ideal bias) scaled by (fin / fclk)^2 and integrated over 125 Hz to 1 kHz offset. A lower tone frequency lowers it by 20 dB per decade. The model ceiling for the external clock is in 3.4 (65.0 dB at 0.512 MHz, 76.9 dB at 1.024 MHz). No run at 0.82 MHz |

Note. The trim code moves the oscillator and the modulator bias together, so the settling margin tracks the clock. On the schematic the frequency at code 4 is 733 to 840 kHz over the corners, not 1.024 MHz (tt 822.9 kHz, -19.6 %). The lab can raise the code to reach 1.024 MHz at a proportional bias current. On the extracted view (2026-11-07, 27 runs: tt, ss and ff at 1.45 and 1.55 V, -40 and 125 C, codes 0, 4, 15, sim) code 4 runs at 583 to 671 kHz and code 15 at 1053 to 1195 kHz, so 1.024 MHz needs a code of about 10 to 12. Start the sweep at code 8 and step up until `do_clk_osc` reads 1.024 MHz. Every run started within 0.38 us of `di_osc_en`, with no runts and a duty of 49.93 to 49.95 %. The frequency falls by about 39 % per volt of supply (839.6, 822.9 and 807.3 kHz at 1.45, 1.50 and 1.55 V, code 4). The highest usable clock is about 2.9 MHz by a settling estimate in the oscillator README (inference, no run), code 15 stays below it.

Procedure. Take O0 first, then O1 and O2 at each code (toggle with `di_ena` and `di_rst_b` low, wait 1 ms after the release), read the frequency with a counter on 10 s gates and the duty on a scope, the supply current as in section 4, and `ibias_test` with the SMU on its lowest range. End with O0 again as a drift check. Agreement (limits chosen by the plan author, not sourced): frequency per measured `ibias_test` current within 10 % of the table above (the bank current moves the frequency, rhigh corners move the bank by -22 % and +31 %), duty 50 +/- 2 %, supply delta within 1 uA, pad leakage below 1 nA at 27 C.
