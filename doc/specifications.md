<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# Chip Specifications

The DSADC1 digital back end on IHP SG13CMOS5L: a 128x decimation filter, an
SPI slave and the configuration register file, in a QFN-32.

Related: [pinout.md](pinout.md), [floorplan.md](floorplan.md),
[rtl2gds.md](rtl2gds.md), [../testbenches/README.md](../testbenches/README.md).

## Overview

| | |
|---|---|
| Technology | IHP SG13CMOS5L, Metal1 to Metal4 plus TopMetal1 |
| Standard cells | ETH Zurich EZ130 8T, 220 cells, 3.36 um row |
| Core supply | **1.2 V** |
| I/O supply | 3.3 V |
| Die | 1600 x 1600 um |
| Package | QFN-32 |
| Clocks | `clk` 65536 Hz, `sclk` 200 kHz, asynchronous |
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
| `dsa1_dig_top` | hard macro, 497.28 um square | the whole design |
| bitstream synchronizer | 3 flops at chip level | the only logic outside the macro |
| `sg13cmos5l_ip__jku`, `..._jku_names` | logos, TopMetal1 | |

The template's counters, inverters and SRAM are not on this die.

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
read. 145 output bits drive nothing on this die: the register file is here so
the taped area is comparable against the older `dsa1_dig_top`. The exception
is `o_tst_ctrl[15:0]`, bonded out on 16 spare pads so the write path can be
checked in silicon.

Two properties bring-up software must know, both found in simulation:

- The ADC data registers are **not** write protected. Address 0 accepts a
  write like any other and is simply overwritten by the next conversion.
- `ADC_DATA_LOW` returns the freeze register, not address 1. **Always read
  HIGH first.**

The full map is in [pinout.md](pinout.md).

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
| `nom_typ_1p20V_25C` | 1.178 | 0.676 | 1.208 | **3.061** |
| `nom_fast_1p32V_m40C` | 1.480 | 0.841 | 2.299 | 4.619 |
| `nom_slow_1p08V_125C` | 0.932 | 0.533 | 6.105 | 7.570 |

The decimator alone is 2.213 uW at typical (0.776 / 0.435 / 1.003), so the
register file, the SPI slave, the stimulus generator and the extra clock tree cost about 0.85 uW, and
most of that is clock: the decimator spends 17.6 % of its power on the clock
tree and the digital top 29.5 %.

Leakage is the largest single term at typical and it dominates at the slow
corner. The static timing figure of 1.208 uW agrees with the transistor-level
measurement of 1.171 uW from `leakage_sim.py` to 3 %, which is the only
independent check of either number.

## Verification status

| | |
|---|---|
| Router DRC, Magic DRC | 0 router, Magic 9710 items in library cells, seal ring and macro, see [signoff.md](signoff.md) |
| KLayout regular DRC | 69 items, all library level, see below |
| Netgen LVS | `Circuits match uniquely`, from the DEF, and from the GDS with the macro, every standard cell and the ESD clamp cell device by device |
| Antenna | 0 nets, 0 pins |
| Setup / hold worst slack | +44.26 ns / +0.074 ns, the macro's inside included |
| Chip cocotb | 7 of 8 pass, the 8th opt-in with PSD=1 |
| Macro RTL vs netlist | identical, 527 observations, and EQY 1325 of 1325 partitions |
| Bond plan | 34 wires, VSS and IOVSS through the cavity, 60 um minimum gap, 5.8 deg max skew |
| HBM ESD, 2 kV | every 1.2 V node under 4.5 V with the vdd-to-vss clamp cell, the core rail at 3.58 V, see [esd_hbm.md](esd_hbm.md) |
| Current density | worst ratio 0.312 of 0.5, chip and macro |
| Supply start-up | VDD first required, see [testbenches/startup](../testbenches/startup/README.md) |

The 69 KLayout items are 31 `Pad.d1R` and 38 `Pad.fR_TM1`, recommended bondpad
rules. Until the core rows moved to EZ130, 2 `NW.d` items sat on the PDK's
thin-oxide decap and filler cells next to the macro's top corners.

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
- **Supply network simulation with the package.** The start-up bench ramps the
  supplies through 0.5 Ohm with the IO cells as transistors. Its bounce case adds
  the package and switches 11 output pads together, but its core draws no current
  and carries no on-die decoupling, so the core supply network is not simulated.
