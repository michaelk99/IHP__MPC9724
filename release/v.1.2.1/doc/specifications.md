<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# Chip Specifications

The DSADC1 digital back end on IHP SG13CMOS5L: a 128x decimation filter, an SPI slave and the configuration register file, next to the `dsm2_core` delta-sigma modulator on its own 1.5 V supply. QFN24, 4 x 4 mm, 0.5 mm pitch, packaged by IHP.

Related: [pinout.md](pinout.md), [floorplan.md](floorplan.md),
[rtl2gds.md](rtl2gds.md), [../testbenches/README.md](../testbenches/README.md).

## Overview

| | |
|---|---|
| Technology | IHP SG13CMOS5L, Metal1 to Metal4 plus TopMetal1 |
| Standard cells | ETH Zurich EZ130 8T, 220 cells, 3.36 um row |
| Core supply | **1.2 V** |
| dsm2 supply | VDDA, **1.5 V** (1.45 to 1.55 V) |
| I/O supply | 3.3 V |
| Die | 1300 x 1300 um |
| Package | QFN24, 4 x 4 mm, 0.5 mm pitch, packaged by IHP, see [../packaging/result.md](../packaging/result.md) |
| Clocks | `clk` 65536 Hz, `sclk` 200 kHz, asynchronous, and `dsm_clk` 1.024 MHz for dsm2 |
| Output rate | 512 Hz, 22-bit words over SPI |

**The core runs at 1.2 V, not the template's 1.5 V.** EZ130 is characterised
at 1.08, 1.20 and 1.32 V and has no 1.5 V liberty, so the corner list is three
entries rather than six:

```
nom_fast_1p32V_m40C   nom_typ_1p20V_25C   nom_slow_1p08V_125C
```

`nom_typ_1p20V_25C` is the default corner. Anything in the repository that
iterates corners, such as `copy-reports`, is driven from `STA_CORNERS` rather
than a hardcoded list, because three of the template's six do not exist here.

## On-die content

| Block | Kind | Notes |
|---|---|---|
| `dsa1_dig_top` | hard macro, 409.08 x 514.08 um | the DSA1 back end, 33.61 pF of DECAPHV on VDD inside |
| `dsm2_core` | hard macro, 150.5 x 178 um | first-order DT delta-sigma modulator, dsm2's oscillator variant of 2026-11-02 |
| `decap_vdda` | hard macro, 150.36 x 349.44 um | 67.61 pF of DECAPHV on VDDA, north of dsm2 |
| VDD decap strips | DECAPHV in the chip rows, 11 rows below and 11 above `dsa1_dig` | 48.60 pF, so VDD has 82.21 pF in all |
| bitstream synchronizer | 3 flops and a mux at chip level | `DEC_SRC` picks the `data_in` pad or dsm2's `do_q_dec` |
| glue gates | two EZ130 `AND2X1` | `do_q_dec` with `DEC_SRC`, `adc_conv` with `ADC_CONV_EN` |
| `sg13cmos5l_ip__clamp_vddvss` | two ESD clamp cells | one on VDD, one on VDDA |
| `sg13cmos5l_ip__cut_vdd` | two ring cells | cut the pad ring's vdd band, the stretch between them is VDDA |
| `sg13cmos5l_ip__jku`, `..._jku_names`, `sg13cmos5l_ip__helm`, `sg13cmos5l_ip__title` | logos, chip art and title, Metal4 | |

The template's counters, inverters and SRAM are not on this die. The standard cells are EZ130 8T v1.1 (ETH Zurich, Apache-2.0), in `ip/ez130_8t_v1p1` and `ip/ez130_8t_decap_hv`.

## dsm2_core

`dsm2_core` is a test and side project on the die. DSA1 stays the main project: the back end runs exactly as in v1.1.1 whether dsm2 runs or not, VDD carries the DSA1 filter alone, and nothing that switches with dsm2 sits on VDD. The design is in [dsm2_integration.md](dsm2_integration.md).

| | |
|---|---|
| Supply | VDDA 1.5 V (1.45 to 1.55 V), always on. VSS is shared. VDDA is also the DAC reference |
| Clock | `di_clk` from the `dsm_clk` pad, fs 1.024 MHz, OSR 512, 1 kHz band. Or its own oscillator (`di_osc_en`, about 0.65 MHz extracted and 0.8 MHz schematic at trim 4), selected by `di_clk_sel`, which also makes dsm2 drive the `dsm_clk` pad |
| Inputs | `vi` single ended, full scale +-0.75 V around VDDA/2. `vcm` is VDDA/2 from dsm2's `vcm_gen`, an input with `DSM_VCM_EXT`. Control inputs static, from `BIAS_CFG_0` and `BIAS_CFG_1` |
| Outputs | `do_q`, `do_q_b` at 1.5 V to their pads in the VDDA segment, which drive at IOVDD, on from reset, held low by `DSM_QOUT_EN` 1. `do_clk_osc` and `do_osc_oe` at 1.5 V to the inout `dsm_clk` pad. `do_q_dec`, the same bit ungated, into one gate in the core. `ibias_test`, a current copy of the bias, to its pad |
| Bias | `DSM_TRIM` code c gives 8.33 nA x (16 + 2 c), reset code 4 is 200 nA. Change it only with dsm2 off, `DSM_EN` 1 |
| Start-up | From reset, with no SPI write: dsm2 is on while `rst_n` is low and leaves reset 9 to 10 `clk` periods (137 to 153 us) after `rst_n` rises, dsm2 needs 130 us. After an SPI restart, `DSM_EN` 0, wait 130 us, then `DSM_RST_B` 0. Discard about 40 decimator words after the reset release: the integrator needs about 17 clocks to leave saturation, and the filter holds about 32 words |
| Size | 150.5 x 178 um on the die |
| VDDA current | dsm2's design values for the oscillator variant at ff 1.55 V 125 C: 32 uA average, 220 uA over 100 ns, 600 uA over 10 ns. Its simulation of the variant at that corner: 29.0 uA running, 215.3 uA over 100 ns and 546.4 uA over 10 ns at the first clock after `di_ena` |

| State | VDD | IOVDD | VDDA | `dsm_clk` |
|---|---|---|---|---|
| DSA1 | on | on | 1.5 V | low or running, dsm2 off (`DSM_EN` 1), its pads static (`DSM_QOUT_EN` 1) |
| dsm2, the reset state | on | on | 1.5 V | 1.024 MHz, dsm2 on and its pads driving from reset. `DEC_SRC` for the decimator |
| dsm2 on its oscillator | on | on | 1.5 V | driven by dsm2: the board lets go, `DSM_EN` and `DSM_RST_B` written 1, then `di_osc_en` and `di_clk_sel` (`BIAS_CFG_0` bits 7 and 8), then `DSM_EN` 0, 130 us, `DSM_RST_B` 0 |

The registers that reach dsm2 are `BIAS_CFG_0` (`DSM_TRIM`, `DSM_DITH_EN`, `DSM_DITH_AMP`, and bits 7 and 8 of `DSM_SPARE` as `di_osc_en` and `di_clk_sel`) and `BIAS_CFG_1` (`DSM_EN`, `DSM_RST_B`, `DEC_SRC`, `DSM_BTEST_EN`, `DSM_VCM_EXT`, `DSM_QOUT_EN`, `ADC_CONV_EN`), see [regmap.md](regmap.md). `DSM_EN`, `DSM_RST_B` and `DSM_QOUT_EN` are inverted at chip level: 0, their reset value, means on, released and driving. After reset dsm2 is on, its reset is released by a 9 `clk` period counter, its pads follow the bit stream, its oscillator is off, `dsm_clk` is an input and the decimator reads the `data_in` pad. `DSM_DITH_EN` stays off, dsm2's dither LFSR can stick otherwise.

With `DEC_SRC` set the decimator reads `do_q_dec` through the gate. The decimator samples on `clk`, dsm2 changes `do_q_dec` on the rising `dsm_clk`, so this path needs `clk` to be the inverted `dsm_clk` from one source. Each bit is then read about 488 ns from either edge. It gives 8 kHz words and suits DC and spot reads over SPI. The full-rate stream is the `do_q` pad.

## Signal chain

```
data_in --> 3FF sync --> CIC(N=6, D=32) --> sinc2^9 --> sinc2^16 --> comp9 --> SPI
65536 Hz                 2048 Hz            1024 Hz     512 Hz       512 Hz
```

The decimated 22-bit word never leaves the die in parallel. It is read over
SPI from `ADC_DATA_CH0_HIGH` and `ADC_DATA_CH0_LOW`, and the slave freezes the
low word when the high word is read so a pair is coherent. `adc_conv` strobes
for one `clk` cycle at 512 Hz to say a word is ready.

Filter design detail is in
[../macros/decimator/rtl/README.md](../macros/decimator/rtl/README.md).

### Bitstream input

`data_in` arrives from a pad with no timing relationship to `clk` and passes a
three-flop synchronizer in `sg13cmos5l_dsa1_dig_core`. That costs three `clk`
cycles, about 46 us, so a sample-for-sample comparison against the reference
model is shifted by three input samples.

### Configuration registers

Sixteen 16-bit registers over a 5-bit address, the top address bit selecting
read. 145 output bits drive nothing on this die: the register file is here so the taped area is comparable against the older `dsa1_dig_top`. The exceptions are the `DSM_*`, `DEC_SRC` and `ADC_CONV_EN` fields of `BIAS_CFG_0` and `BIAS_CFG_1`, which control dsm2. The 16 test pads of v1.1.1 are gone, and `TEST_CTRL_0` stays readable over SPI.

Two properties bring-up software must know, both found in simulation:

- The ADC data registers are **not** write protected. Address 0 accepts a
  write like any other and is simply overwritten by the next conversion.
- `ADC_DATA_LOW` returns the freeze register, not address 1. **Always read
  HIGH first.**

The full map is in [regmap.md](regmap.md).

### Stimulus test mode

`TEST_CTRL_0` bits 11, 12 and 13 drive an on-chip pattern generator, so the
step and impulse response can be measured without feeding in a precise
external bitstream. Enable, let the output settle to zero on the alternating
idle, then trigger. Detail in
[../macros/dsa1_dig/README.md](../macros/dsa1_dig/README.md).

## Power

### Static

Measured at transistor level with `macros/scripts/leakage_sim.py`, corner tt,
on the hardened netlist. The die decouples with thick-oxide cells only, and
that is what the number buys:

| | thin-oxide decap | thick-oxide decap |
|---|---:|---:|
| decap cells | 5998 | 2344 |
| decap leakage | 5967 nW | ~0 nW |
| decap share of the block | 83.6 % | 0.0 % |
| **block total at tt** | **7.136 uW** | **1.157 uW** |

**A 6.2x reduction, and the decoupling stops being the dominant term.**

Three caveats, none of which the headline number shows:

- **The `~0 nW` is a floor, not a measurement.** IHP sets `iginvlw = 0` for
  both 3.3 V devices, so a thick-oxide gate carries no tunnelling term in the
  model at all and ngspice returns solver residue. The physics is right, and
  the 7.136 uW thin-oxide figure **is** a measurement.
- **The total is reproducible since 2026-09-22.** It was not: one `op`
  analysis covered every input vector of a cell, so a single non-converging
  vector dropped the whole cell and the answer was always low. Per-vector
  retry, homotopy options and a liberty fallback fixed it, and two consecutive
  runs are now byte identical. Before the fix it gave 1.089, 1.129 and
  1.157 uW on successive runs of the same netlist. The residual gaps are
  reported rather than hidden: XNOR3X1 averages 2 of its 8 input vectors and
  XNOR2X1 3 of its 4, and ANTENNA2 has no ngspice device model at all, so its
  liberty value is used.
- **Fill cells are excluded**, 17792 instances with no CDL. They are not
  decaps but they are not zero either.

The cost of the swap is on-die decoupling: about 182 pF down to about 35 pF.
See [floorplan.md](floorplan.md) for that analysis and for why the series
resistance of the thick-oxide cells does not matter at this clock.

### Dynamic

The flow's own `power__total` reports 1.68 mW at chip level, which is
meaningless: it is computed with no activity annotation for a design clocked at
65 kHz. `make power-vcd` gives the real figure, annotating per-pin switching
densities from a gate-level VCD at the true 65.536 kHz clock over a whole
number of conversions.

`dsa1_dig_top`, over 401 clock cycles of settled activity, in uW:

| Corner | Internal | Switching | Leakage | Total |
|---|---|---|---|---|
| `nom_typ_1p20V_25C` | 1.170 | 0.733 | 1.171 | **3.075** |
| `nom_fast_1p32V_m40C` | 1.471 | 0.910 | 2.228 | 4.608 |
| `nom_slow_1p08V_125C` | 0.925 | 0.580 | 5.898 | 7.403 |

This is the macro re-hardened for the 1.3 mm die, 0.45 % above the 3.061 uW of v1.1.1 at typical. The decimator alone is 2.213 uW at typical (0.776 / 0.435 / 1.003), so the register file, the SPI slave, the stimulus generator and the extra clock tree cost about 0.86 uW.

Leakage is the largest single term at typical and it dominates at the slow corner. The static figure above for the v1.1.1 macro, 1.157 uW, was not rerun on the re-hardened netlist.

The start-up bench measures the IO cells and clamps in the DSA1 state (VDD, IOVDD and VDDA on, dsm2 off, `dsm_clk` low): VDD 12.65 nA, IOVDD 28.54 nA, VDDA 2.19 nA. With dsm2 running and its pads switching, VDD stays at 12.65 nA (difference -1 pA, resolution 13 pA), so dsm2 costs VDD nothing. The same bench on the v1.1.1 layout gives VDD 21.45 nA and IOVDD 37.54 nA. The difference is the pad population: 2 push-pull 30 mA outputs against 18 on v1.1.1, and no bidirectional pads. Details in [../verification/startup/startup_report.md](../verification/startup/startup_report.md).

## Verification status

Chip run `RUN_2026-10-23_07-00-13`, benches of Tasks 8a and 8b. The sign-off record for the release is [signoff.md](signoff.md).

| | |
|---|---|
| Router DRC, Magic DRC | 0 router. Magic 4978 items at the top, only rule families v1.1.1 already had, none new |
| KLayout regular DRC | 37 items, `Pad.d1R` 4 and `Pad.fR_TM1` 33, all on the bondpads. Against 35 before the second IOVDD cell: it adds 4 `Pad.fR_TM1`, and its 20 um west gaps are one `Filler4000` each, so the small fillers that met the pad cell corner are gone, which removes 2 `Pad.d1R` and the 12 Magic `LU.d` items. Magic gains 201 `Slt.c` and 54 `CntB.h1` from the new cell |
| Top LVS from the GDS | `Circuits match uniquely`: the macro, every standard cell and both clamp copies device by device, the cut cells and dsm2 by pins, VDDA its own net. A reference with VDDA joined to VDD fails, and so do three more mutants |
| Antenna | the flow's antenna checker clear |
| Setup / hold worst slack | +44.07 ns / +0.0695 ns, the macro's inside included |
| Chip cocotb | 12 pass, 1 skipped (`test_psd`, opt-in with PSD=1), RTL and gate level |
| Macro RTL vs netlist | `sim-gl` identical (1343 samples), `model-gate` 8 of 8, `sim-cdc` clean, LEC 1323 of 1323 partitions |
| Bond plan | in [../packaging/result.md](../packaging/result.md) |
| HBM ESD, 2 kV | model result at RON 1 and 4 on the tape-out layout: 1.2 V nodes (3.87 V), the VDDA rail (4.38 V), dsm2's analog pins behind its protection (4.41 V) and HV (8.84 V) inside the indicative limits, see [esd_hbm.md](esd_hbm.md) |
| Current density | worst ratio 0.312 of 0.5, VDDA rated at 1 mA, above dsm2's 600 uA over 10 ns |
| Supply start-up | VDD and VDDA no later than IOVDD, see [testbenches/startup](../testbenches/startup/README.md) |

### Known limits

- Signal and supply wires run inside dsm2's 10 um halo to reach its pins. The keep-out check bounds the box metal and the halo fill only.
- VDDA has no IR-drop analysis. The EM check rates VDDA at 1 mA, dsm2's design values for the oscillator variant are 32 uA average, 220 uA over 100 ns and 600 uA over 10 ns.
- The `miso` and `adc_conv` pads are 20 to 24 ps over max slew at the slow corner. At the 950 ns clock this has no timing effect.
- With IOVDD before VDDA, `do_q` and `do_q_b` sit at 3.3 V from 28 to 202 us and IOVDD sees a 53 mA, 34 ns peak. The board rule (VDD and VDDA no later than IOVDD) avoids it.
- The v1.1.1 start-up currents in uA were an artifact of a sample mean over 1 ns edges. The bench now uses a time mean, and the currents are nA.
- `dsm2_core` is a box in the ESD model: its supply nodes and the protection of its analog pins, not its internal nodes.
- HBM, dsm2 analog pins: behind dsm2's own `sg13cmos5l_SecondaryProtection`, `vi`, `vcm` and `ibias_test` reach 4.41 V at worst (`ibias_test`, `iovdd_w4` - vs vdda, RON 4, 4.35 V at RON 1), 0.09 V under the indicative 4.5 V. The margin is the VDDA rail plus one diode drop and shrinks with the diodes' on-resistance.
- HBM, HV: under the indicative 10 V with the second `IOPadIOVdd` cell, which has a bondpad and no wire (item 5 of [esd_hbm.md](esd_hbm.md)). Worst 8.68 V at RON 1 (`pad_iovdd@vdda_e4`) and 8.84 V at RON 4 (`pad_iovss@doqb`), no zap over 10 V. With the one cell of the first layout it was 30 zaps at RON 0.5 and 1 and 96 at RON 4, worst 11.55 V. RON 0.5 and 2 and the package short were not rerun on this layout.

### Not done

- **Transistor-level top LVS against a drawn schematic.** Settled, and not by
  drawing one. A full `klayout-lvs` run reports `layout=277536 schematic=5`:
  the layout extracts 277536 devices and a sheet of pad cells plus one hard
  macro offers five subcircuit calls with no definitions. Making it compare
  would mean assembling the whole design as transistors in the CDL, which is
  the netlist, and netgen already compares the layout against that with
  `Circuits match uniquely`. The schematic is now correct and generated, but
  its job is the transient testbench and the documentation. See
  [testbenches/README.md](../testbenches/README.md).
- **Supply network simulation with the package.** The start-up bench ramps the supplies through 0.5 Ohm with the IO cells as transistors. Its bounce case adds the package and switches `do_q`, `do_q_b`, `miso` and `adc_conv`, but its core draws no current and carries no on-die decoupling, so the core supply network is not simulated.
