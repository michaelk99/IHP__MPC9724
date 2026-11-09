# dsm2_core Verilog-A model check

`../dsm2_core.va` is a functional model of `dsm2_core` in Verilog-A for OpenVAF and ngspice (OSDI). Its module name is `dsm2_core` and its 25 scalar ports, all electrical, are in the order of the CDL `.subckt` (`../../cdl/dsm2_core.cdl`), with `di_trim_3` to `di_trim_0` for `di_trim[3:0]` and `di_dith_amp_1`, `di_dith_amp_0` for `di_dith_amp[1:0]`. An ngspice instance line is therefore the pin list of the CDL `.subckt` line, with `N<name>` in front and the model name after it. This folder holds its ngspice bench and the check against the Python loop of `../dsm_system.py`. Model and simulation only, nothing here was measured.

## What the model covers

| Part | Model | Source |
| --- | --- | --- |
| Loop | On each rising edge of the loop clock: `q = (y + d >= 0)`, then `y <= (1 - leak) y + a1 (vi - vcm) - a1 (vdac - vcm)` with `vdac` = `vdd` for q = 1 and `vss` for q = 0. `y` is `vo_p - vo_n`, clipped at +-`ysat` | `dsm_system.py` `run_loop`, a1 = 2 - 2/H_inf = 1/3 at H_inf 1.2 (`../README.md` Setup) |
| Leak | `leak` 2.73e-4 per clock, the Magic mode 3 fit of the final layout. Its schematic fit is 2.91e-4, `dsm_system.py` uses 8.51e-4 (A0 61.4 dB) | `sc_int2_README.md` leak bench, `dsm_system.py` |
| `ysat` | 1.41 V, the saturated vod in reset | `dsm2_README.md` line 156 |
| Dither | 17-bit XNOR Fibonacci LFSR, taps 17 and 14, three bits per clock from the all-zero state, cleared while `di_dith_en` is low. `d = A (2c - 7)/7` in V of `vo_p - vo_n`. `A` per `di_dith_amp` 00, 01, 10, 11: 76.5, 50.1, 104.4, 23.3 mV (tt sim) | `quantizer2_README.md`, `dither_deadzone.py` |
| `di_ena` low | loop clock stopped, latch preset, `vcm` not driven, bias and oscillator off. `y` and the LFSR hold their values (model choice, the circuit state after a disable is not characterised) | `dsm2_README.md` lines 29 and 147, `bias_gm_README.md` line 56 |
| `di_rst_b` low | latch preset, so q = 0 and the DAC feeds `vss`. The integrator keeps running and saturates | `dsm2_README.md` line 156, `quantizer2_README.md` line 26 |
| Outputs | `do_q` = q and `di_qout_en`, `do_q_b` = not q and `di_qout_en`, `do_q_dec` = q ungated. All low in preset except `do_q_b`, which is high when `di_qout_en` is high. First-order edge, 10 to 90 % in `tr_out` (0.5 ns, a model value) | `quantizer2_README.md` line 26, `dsm2_README.md` lines 28 and 36 |
| `vcm` | `vdd/2` through `r_vcm` 1 MOhm onto the reservoir `c_res` 2.7 pF while `di_ena` is high and `di_vcm_ext` low. Otherwise 1 GOhm to `vss`, so an undriven `vcm` goes to 0 V | `vcm_gen_README.md` lines 16 and 47 |
| `ibias_test` | sources `i_unit (16 + 2 code)`, 8.33 nA units, 199.92 nA at code 4, while `di_ena` and `di_btest_en` are high and `di_osc_en` is low. The cut-off within 0.3 V of `vdd` is a model bound, not a circuit value | `bias_trim_README.md` line 21, `bias_gm_README.md` line 56 (`di_ena` low turns both banks off), `dsm2_osc_README.md` line 5 |
| Oscillator | runs while `di_ena` and `di_osc_en` are high. `osc_scale` (0.7824) times the schematic tt 565.9, 822.9 and 1479.1 kHz at `di_trim` 0, 4 and 15, so 442.8, 643.8 and 1157.2 kHz. 643.8 kHz is the extracted tt value at code 4, the same scale at the other codes and the line between the three codes are interpolation. `do_clk_osc` is low while `di_osc_en` is low. `di_clk_sel` high clocks the loop from it, `do_osc_oe` follows `di_clk_sel` | `dsm2_osc_README.md` lines 20, 21, 65 to 67 and 252, `dsm2_README.md` line 378 |
| Inputs | digital pins switch at `V(vdd, vss)/2`, so the 1.2 V controls work. `vi` draws no current | |

Not modelled: noise (kT/C, OTA, flicker, phase noise), comparator offset and metastability, OTA settling, kickback, the `vi` sampling charge of C1, the `vcm_gen` ripple and its +4 to +8 mV offset, supply current, the `di_btest_en` kick on `ibias_200n`, oscillator start-up, supply and corner dependence, and runts from switching `di_clk_sel`. The disabled `vcm` floats at 0.47 to 0.51 V in the circuit. The reset recovery is shorter than in the circuit: 10 clocks of `do_q` = 1 at +0.3 V against 16 to 17 in `dsm2_README.md` line 156, because the model integrator clips at `ysat` and recovers linearly. `sc_int2_README.md` line 104 gives the mechanism of the missing clocks, the virtual grounds drift by C1/(C1+C2) = 1/7 of the gap per cycle while the OTA sits at its limit, which a behavioural model there turns into 15 clocks.

How it works: OpenVAF has no event controls and keeps no variable from one time point to the next, so every state sits on an internal node. Each state has a master node that tracks its next value while the loop clock is low and a slave node that copies the master while it is high, both with 1 ns time constants, held on 1 nF otherwise. The two windows must not overlap at the clock edge. The 17 LFSR bits are 34 such nodes. The oscillator phase is a node that integrates the frequency.

## Commands

From the repo root:

```
scripts/in_image.sh 'python3 ip/dsm2_core/model/va_check/run_va_check.py --out runs/trl1/va --jobs 6'
```

It compiles the model (`openvaf ip/dsm2_core/model/dsm2_core.va`), writes one copy of `tb_dsm2_core_va.spice` per case with its `.param` values under `--out`, runs `ngspice -b`, compares, writes `summary.txt` and exits 1 if any check fails. Every bit comparison below must be equal in full, and every control result must sit within the stated tolerance of its expected value. `--quick` runs short records to try the flow. The bench alone runs with `dsm2_core.osdi` in the working directory: `ngspice -b tb_dsm2_core_va.spice`. It uses `.options method=gear reltol=1e-3 trtol=20` for speed. The full run took 34 min wall time with 6 jobs on a shared 12-core host and ended in PASS. The two 16424-clock sine runs dominate.

The bench drives the controls at 1.2 V, `vi` from an ideal `vdd/2` reference as in the `dsm2_README.md` bench, `di_clk` at 1.024 MHz with 1 ns edges, rising through `vdd/2` at (k + 0.5)/fs, and reads the bit of clock k at (k + 0.75)/fs as `psd_bitstream.py` does. `di_ena` and `di_rst_b` are high before the first edge, so model clock 0 is Python sample 0. The bench sets `leak` on the `.model` line to the `dsm_system.py` value 10^(-61.4/20), so both sides run the same loop. The Python reference is `dsm_system.run_loop1` with the same a1 and leak, no noise, and for dither on the codes of the LFSR rule copied from `dither_deadzone.py` with A = 76.5 mV (`di_dith_amp` 00).

## Results, 2026-11-09

What the bit equality proves: both sides run the same difference equation with the same a1, leak, A and LFSR rule, typed in by the author of this check. Equality shows that the node emulation of the `.va`, its clock windows, sample instant, LFSR wiring and dither scaling reproduce `dsm_system.run_loop1`. It says nothing about the circuit values a1, leak, DAC levels, dither amplitude or reset behaviour. The one link to the circuit is the LFSR: its codes come from the `dither_deadzone.py` rule, which `quantizer2_README.md` matched to the circuit for 200 clocks.

LFSR reference: the code sequence repeats after 131071 clocks and gives codes 0 to 6 16384 times each per period and code 7 16383 times.

(a) DC on `vi`, 2048 clocks from clock 0, ones density of `do_q`:

| vi - vref | ideal 0.5 + vi/1.5 | model, dither off | Python, dither off | bits equal | model, dither on | Python, dither on | bits equal |
| --- | --- | --- | --- | --- | --- | --- | --- |
| +0.3 V | 0.70000 | 0.69971 | 0.69971 | 2048 of 2048 | 0.69971 | 0.69971 | 2048 of 2048 |
| 0 V | 0.50000 | 0.50000 | 0.50000 | 2048 of 2048 | 0.50000 | 0.50000 | 2048 of 2048 |
| -0.3 V | 0.30000 | 0.30029 | 0.30029 | 2048 of 2048 | 0.30029 | 0.30029 | 2048 of 2048 |
| +0.6 V | 0.90000 | 0.89941 | 0.89941 | 2048 of 2048 | 0.89941 | 0.89941 | 2048 of 2048 |

The offset from the ideal density is the start from y = 0 and the leak, the same in both models.

(b) Sine of 687.5 Hz at -6 dBFS (0.3759 V), 16424 clocks, SNR over the 16384 points after 32 settle clocks (`psd_bitstream.py` spectrum and band split, 62.5 Hz bins):

| Case | model SNR | Python SNR | bits equal |
| --- | --- | --- | --- |
| dither off, `vi` held per clock | 74.30 dB | 74.30 dB | 16424 of 16424 |
| dither on, `vi` held per clock | 72.10 dB | 72.10 dB | 16424 of 16424 |
| dither off, continuous sine | 74.30 dB | 74.30 dB | 16424 of 16424 |

`psd_bitstream.py` run on the ngspice raw files gives the same 74.30 and 72.10 dB. `dsm_system.py --fres 62.5 --noiseless --settle 32` gives 74.27 dB on the same record, its own band split keeps the stream mean and the DC skirt bins in. The held `vi` is a PWL staircase that steps while the master holds, so the sample does not depend on the sampling instant. With the continuous sine the model samples about 1 ns before the clock edge, and the run script shifts the sine phase by that so the Python samples are the same.

(c) Controls, `vi` at +0.3 V, short runs, at the model defaults apart from `leak`:

| Case | Result | Expected, tolerance, source |
| --- | --- | --- |
| `di_osc_en` and `di_clk_sel` high, `di_trim` 0, 4, 15 | `do_clk_osc` 442.8, 643.8, 1157.2 kHz, `do_osc_oe` 1.500 V, `do_q` time average 0.702, 0.700, 0.700 from 20 to 196 us | 0.7824 times 565.9, 822.9, 1479.1 kHz within 0.1 %, 1.5 V within 1 mV, 0.7 within 0.01 (`dsm2_osc_README.md` lines 21, 65 to 67, 252) |
| `di_rst_b` released after 20 clocks | `do_q` 0 V in reset, then 10 ones, 80 of 80 bits equal the model loop with q held at 0 and the clip | 0 V (`dsm2_README.md` line 156), bits exact |
| `di_qout_en` low | `do_q` and `do_q_b` 0 V, `do_q_dec` 64 of 64 bits equal Python | below 1 mV, bits exact (`dsm2_README.md` lines 28 and 36) |
| `di_ena` low, `di_qout_en` high | `do_q` and `do_q_dec` 0 V, `do_q_b` 1.5 V, `vcm` 0 V, undriven | within 1 mV (`quantizer2_README.md` line 26, `vcm_gen_README.md` line 28) |
| `di_btest_en` high, code 4 | 199.92 nA out of `ibias_test` into 0.5 V, 0.00 nA with `di_osc_en` high too | 8.33 nA (16 + 8) within 0.1 %, 0 (`bias_trim_README.md` line 21, `dsm2_osc_README.md` line 5) |
| `di_vcm_ext` high | `vcm` 0 V, undriven. 0.750000 V with `di_vcm_ext` low | within 1 mV and 10 uV (`dsm2_README.md` line 24, `vcm_gen_README.md` line 16) |

Tools: image `registry.iic.jku.at:5000/iic-osic-tools@sha256:65771d5c6be66df4f8a7522421355b53964ce643dc4cc612b605f645063b1af4` (`IMAGE_AMD64` of `scripts/image.env`), OpenVAF-Reloaded `osdi_0.5_20260820-23-gfbd1d4a-dirty`, ngspice-47, Python numpy 2.5.3.
