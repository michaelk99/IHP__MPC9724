<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# Bit-true models

Reference models the RTL is gated against. The model is the specification here, not a check written after the fact: the decimator chain was designed and its alias and noise measured in a model first, so the RTL is correct only if it reproduces the model sample for sample.

## decimator_model.py

Bit-true, cycle-accurate model of the decimator macro: CIC(N=6, D=32), sinc2^9, sinc2^16 and the folded 9-tap compensator. One `step()` per `clk_fs` rising edge, mirroring `macros/decimator/rtl/decimator_core.sv`, so a testbench compares at the same edge with no lag search.

```python
from decimator_model import DecimatorModel

m = DecimatorModel()
for bit in bits:                 # 1 is +1 into the CIC, 0 is -1
    y = m.step(bit)              # the output word when valid_strobe is high, else None
```

`m.run(bits)` feeds a whole stream and returns one word per strobe.

Pure Python, no dependencies. The host has neither numpy nor cocotb, and a gate that only runs inside the container is a gate that does not get run.

### What it reproduces

| Stage | Detail the model carries |
|---|---|
| CIC integrators | wrap in 32 bit at `clk_fs`, exact by Hogenauer |
| CIC combs | combinational through the chain, one delay each, clocked at `ce_cic` |
| Align | round and shift by `ALIGN_W = 6`, wrapping in 32 bit first |
| sinc2 sections | `(x[n] + x[n-1] + 1) >> 1`, one rounding per section, word flat at 27 bit |
| Decimation phase | each stage keeps the sample its `ce` selects, which is what a spectrum cannot see and a sample comparison can |
| Compensator | the same five folded taps, six CSD terms each, on one shift-add engine, 35 of 128 cycles, rounded per tap at that tap's own scale |
| Output | round 4 fraction bits, saturate to 22 bit |

The compensator taps are not designed at run time. `COMP_TAPS` is the CSD term table copied from `comp_fir.sv`, so the model and the RTL agree by construction on the coefficients and only the arithmetic is being compared. `comp_tap_value(t)` reconstructs the rational for a check against a filter design.

### Gate against a simulated RTL run

```
python3 models/decimator_model.py <stimulus.txt> <rtl_output.txt>
```

Stimulus is the MATLAB bitstream export, one `time value` pair per line with value +-1. The RTL output is what `make -C macros/decimator sim-rtl-out` writes. A lag search absorbs the testbench's reset race, which is a constant offset, but not a decimation phase error, which is what the search would fail on.

Measured against the 4194304-sample DSM stimulus: 0 of 32768 output samples differ, at lag 0. About 65 s.

## stream_psd.py

Spectra and bit-true checks of a long F stream, which `bench_record.py` in the svn EasyConfig folder records from an EasyConfig host. Needs numpy and matplotlib.

```
python3 models/stream_psd.py prbs.npz --out plots/
python3 models/stream_psd.py dsm.npz --seq $JKU_PHD_DIR/circuit-level/hdl/DSADC1/DIG_TOP/sim/stim_dac_sine_dec.txt --out plots/
python3 models/stream_psd.py --self-test
```

| record | bit-true against | spectrum |
|---|---|---|
| `prbs`, the on-chip PRBS23 | `stimulus.predict()` from the fire | Welch PSD against what the chain makes of white +-1 input, the sum of `abs(chain_response)**2` over the images the decimation folds |
| `dsm`, a modulator sequence the host played into `data_in` | `decimator_model` on the same sequence, the few clk_fs edges the reset release adds or eats found by a short probe | Hann periodogram, tone, SNR, SINAD, THD and ENOB in the 128 Hz band |

A record of the DSA1 die's back end (`bench_record.py --die legacy` on a duo harness, `arty_duo` or `versa_duo`) is checked against decimator v4 instead, at 256x, with the bit-true model jku-phd keeps next to the v4 RTL, `system-level/python/dec_v4_bit_true.py`, found through `JKU_PHD_DIR`. It is not in this repo, like the legacy RTL itself.

Both checks place each word by its conversion count, so a conversion lost in transport is skipped and reported as lost, not read as a shift of every word after it. The `dsm` periodogram takes the longest run without a count gap, from 1 s in, and an empty or too short record stops with a message.

Levels are dBFS against `FULL`, so a full-scale sine is 0 dBFS. The tone metrics come from `psd_param.py` with a 7-term Blackman-Harris window, and the plot draws the output word's rounding floor next to the measured one. Log-averaging is for the plot only, every number comes off the raw bins. Model words are cached in the output folder.

## psd_param.py

`calc_psd_param()` is jku-phd's `SKY130_CT-DSM/system-level/matlab/utility/calcPSDParam.m` ported, same inputs and outputs, equal to MATLAB R2024b to 1e-9 on a reference record in the self-test. `psd_param()` keeps its conventions and corrects what a review of it found:

| | calcPSDParam.m | psd_param() |
|---|---|---|
| window | `hann(N)`, which MATLAB makes symmetric, period N-1 | periodic Hann or 7-term Blackman-Harris |
| a coherent tone | leaks a skirt at about 1/N of the tone into the noise, -94 dBc two bins out at N = 16384 | occupies its main lobe only |
| the DSA1 record above | SNR 91.7 dB | SNR 126.8 dB, the output word's floor |
| signal level | `spwr`, the main-lobe sum, 1.76 dB high for Hann | divided by the window's noise bandwidth |
| DC | not removed, bins 0 to 10 skipped | mean removed, the window's skirt skipped |
| harmonics | HD2 and HD3 where they fall unaliased | HD2 to HDk folded at fs/2, THD |
| the tone | given, assumed on a bin, signal +-1 bin | found, its offset from the bin measured, signal bins widened and a warning when off |
| inputs | `fres` given though it is fs/N, `y` must be a row or `w'.*y` becomes N x N | from the record |

The leakage search in the original sets `nb_leak`, which nothing reads after its temporary fix, so it is not ported. `python3 models/psd_param.py --self-test`.

Measured on the Arty through the ESP32 host, 2026-09-29:

- 32509 PRBS23 words, 0 differ from the model, the in-band PSD 0.08 dB below the chain's prediction, the variance 0.04 dB below.
- The 4194304-bit jku-phd modulator sine played into `data_in` at 64 kHz: 32768 words, 0 differ from the model at lead-in 0, tone 41.02 Hz at -4.02 dBFS, SNR 126.8 dB, SNDR 126.3 dB, THD -136.0 dB, ENOB 20.7 bit in 125 Hz. That SNR is the 22-bit output word: its rounding alone gives 127.2 dB for this tone, 131.2 dB for a full-scale one. The same chain with 3 more output bits reads 136.4 dB, its internal rounding, and the modulator's bit stream itself 144.5 dB.

## stimulus.py

The on-chip stimulus of `TEST_CTRL_0` bits 15:11, four patterns, each once or repeating every 64 conversions, as a bit generator that mirrors `p_stim` in `macros/dsa1_dig/rtl/dsa1_dig_top.vhd`. With `decimator_model.py` it predicts what the chip produces for each pattern, which turns an FPGA or silicon measurement into a sample-for-sample gate.

```python
from stimulus import predict, PAT_STEP_P, PAT_STEADY
predict(PAT_STEP_P)             # step +, 40 words from the fire
predict(PAT_STEADY, opt=True)   # PRBS23
```

The prediction is well defined even though the SPI write lands at an arbitrary moment, because the trigger only arms and the pattern fires at the next `valid_strobe`. Before that the stream is the idle alternation, which the filter rejects, so the filter is in the same settled state at every `valid_strobe` and the response does not depend on which one it was.

**`TOG_PHASE` is not cosmetic.** The idle toggle runs from `rst_b` but the decimator's clock-enable counter runs from `dec_rst_b`, which the three-flop `dec_en` synchronizer releases three clocks later. Three is odd, so the toggle is inverted relative to the decimation window. It sets the impulse polarity and the exact step overshoot, and it was measured against the RTL rather than assumed: with the wrong phase the step and step- peaks come out mirrored and the impulse sign flips.

## gate_dsa1_dig_out.py

Runs all eight stimulus modes through the model and compares them against what `make -C macros/dsa1_dig sim-rtl-out` and `sim-gl-out` logged.

```
make -C macros/dsa1_dig model-gate
```

Measured on the 2026-09-23 RTL: 38 of 38 words match for every pattern, PRBS23 included.

## gate_decimator_out.py

The same check without a stimulus file. It reproduces the stimulus of `macros/decimator/testbenches/verilog/decimator_top_tb.v` in Python, 64 idle edges, a step to +1, then PRBS23 seeded at 1, and compares all 500 output samples.

```
make -C macros/decimator model-gate
```

`make sim-gl` only says the hardened netlist and the RTL agree, and they would agree even if both were wrong, because they share a source. This says both are right. Measured on the 2026-09-22 run: 500 of 500 match at RTL and at gate level.

The constants at the top of the script track the testbench. If `N_STEP`, `N_PRBS` or the 64-edge delay change there, change them here or the gate fails for the wrong reason.

### Self-test

```
python3 models/decimator_model.py --self-test
```

Checks that `COMP_TAPS` still reconstructs the five tap values and that a held +-1 settles on the output the tap sum implies. No simulator, no cell library, about a second, so `.github/workflows/model-check.yml` runs it on every push. The nightly regression cannot build this chip's macros at all, since EZ130 lives outside the repository, so this is the only CI job that checks anything about the design rather than the toolchain.

### Where it is used

`macros/decimator/testbenches/cocotb/decimator_top_tb.py` drives the model beside the DUT in both RTL and gate-level mode. `test_dc_gain` is the one absolute check in that file, a held +1 settling on 2^20 times the compensator dc gain: everything else asks whether the RTL equals the model, which cannot catch a scaling error the two would share.

### Origin

Ported from `dec_sinc_bit_true.m` in the development repository, which is vectorised per stage and needs MATLAB. This version is per clock instead, which is slower but is what lets cocotb use it directly.
