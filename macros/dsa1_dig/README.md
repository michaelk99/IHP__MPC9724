<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# dsa1_dig_top

The DSADC1 digital back end, and the only digital macro on this die, next to `dsm2_core` and `decap_vdda`: the 128x decimation filter, an SPI slave and the configuration register file. One bitstream goes in and 22-bit words come out over SPI at 512 Hz.

| | |
|---|---|
| Top cell | `dsa1_dig_top` |
| Standard cells | EZ130 8T, read from `EZ130_DIR` |
| Decoupling | `DECAPHV8/16/32` only, from `DECAPHV_DIR` |
| Die | 409.08 x 514.08 um |
| Clocks | `clk` 65536 Hz, `sclk` 200 kHz, asynchronous |

## Where the RTL comes from

`rtl/` is a frozen copy from the private RTL repository (`circuit-level/hdl/DSADC1`), with the VHDL entity renamed from `dsa1_dig_top_v2` to `dsa1_dig_top`. The decimator is not copied: both macros read the same six SystemVerilog files from `../decimator/rtl`.

`make rtl-gen` is two steps because LibreLane reads one language per run: `ghdl synth` turns the VHDL into Verilog with `decimator_top` left unbound, then a yosys pre-pass clock-gates it together with the decimator RTL. The pre-pass is needed because yosys `clockgate` skips a flop whose synchronous reset overrides its enable, which is every register here.

## The register file stays, on purpose

Of the 145 configuration output bits the chip reads only 16 of `o_bias_cfg`, for dsm2, the decimator input mux and the `adc_conv` gate. The rest keep the taped area comparable against the older `dsa1_dig_top`. The eight scalar ports reach the pad ring, `data_in` through the core's synchronizer and `adc_conv` through its gate. They are eight of the fourteen die signals in the root README, the other six are dsm2's.

Bring-up software has to know two register-file properties, detailed in [testbenches/README.md](../../testbenches/README.md): the ADC data registers are not write protected (address 0 accepts a write until the next conversion overwrites it), and `ADC_DATA_LOW` returns `adc_low_freeze_reg`, latched when HIGH is read, not what was written to address 1. Always read HIGH first.

## Stimulus test mode

`TEST_CTRL_0` carries an on-chip stimulus generator, so the filter response can be measured in silicon without a precise external bitstream.

| bit | name | meaning |
|---|---|---|
| 11 | `STIM_EN` | select the internal pattern, an alternating idle |
| 12 | `STIM_TRIG` | rising edge arms, write low then high to re-arm |
| 14:13 | `STIM_PAT` | the pattern, below |
| 15 | `STIM_OPT` | repeat for the event patterns, variant for the steady one |

| `STIM_PAT` | pattern | `OPT` = 0 | `OPT` = 1 |
|---|---|---|---|
| `00` | step + | hold, once | repeat, 32 idle / 32 held |
| `01` | impulse | one broken sample | repeat every 64 output samples |
| `10` | steady | half scale, mean +1/2 | PRBS23 |
| `11` | step - | hold, once | repeat, as step + |

Bit 9 is the analog top's and is never written from here. Bits 10 and 8 are `FLAG_SYNC_EN` and `PAD_Q_EN`, both reset 1, so every write to this register has to keep the `0x0500` base.

Enable and trigger are separate because the decimator holds about 32 output samples of history, which would bury an event fired on the enable edge. Set bit 11, wait for the output to settle to zero on the idle pattern, then set bit 12.

**The trigger only arms.** The pattern starts at the next `valid_strobe`, so every shot begins on the same phase of the 128-cycle decimation window. Otherwise the impulse response shifts run to run and its polarity is a coin toss.

The idle pattern alternates at `clk`/2, which the filter rejects completely, so the output sits at zero with no DC pedestal. That makes a step and an impulse well defined on a one-bit input.

Measured on RTL at the 512 Hz output rate, and reproduced sample for sample by `models/stimulus.py`:

| pattern | settles at | peak |
|---|---|---|
| step + | 1048232 | 1128189, the compensator overshoot |
| step - | -1048232 | -1127982 |
| half scale | 524116, exactly half of the step | 563999 |
| impulse | 0 | -11246 |
| PRBS23 | wanders about zero | order 1e5 |

The three dc points show the gain linear to the LSB across the range. A settled step's ripple is the sinc chain's per-section truncation noise, and PRBS23 measures the filter's noise bandwidth from a white one-bit input.

`make model-gate` checks all five against the model, plus the repeat modes of step +, impulse and step -, eight modes in all.

## Building it

```sh
make rtl-gen        # ghdl synth, then the yosys clock-gate pre-pass
make librelane      # harden
make build-top      # harden, collect views and reports, render
make sim-gl         # the gate-level netlist must equal the RTL, sample for sample
make check-netlist  # no cell that is wrong in silicon reached the netlist
```

`EZ130_DIR` and `DECAPHV_DIR` default to `ip/ez130_8t_v1p1` and `ip/ez130_8t_decap_hv`. `check-ez130` fails loudly if either is wrong.

## FPGA evaluation

`make build-fpga` puts the **top level** on an FPGA, ULX3S by default, read out over the chip's own SPI slave. Synthesis and place-and-route pass on 2026-09-23, 1903 flops against 1862 in the macro hardened that day (the current macro has 1846), about 2 % of an ECP5-85F, `clk_fs` closing at 28.54 MHz against the 65.536 kHz it needs. The ULX3S build has no hardware run on record. The Arty A7-35T and ECP5 Versa builds ran on hardware on 2026-09-29 and 2026-10-01, and the Arty passed 15 of 15 bench tests on 2026-10-02 ([doc/signoff.md](../../doc/signoff.md)). See [fpga/README.md](fpga/README.md).

## Results

LibreLane run of 2026-10-31 (`RUN_2026-10-31_16-16-30`), the image of `scripts/image.env`, EZ130 8T, thick-oxide decoupling. The outline is 409.08 x 514.08 um at 69 % utilization, as wide as the gap to dsm2's halo allows, so the chip has room for VDD decap strips above and below it. Every signoff check is zero: router DRC, Magic DRC, KLayout DRC, netgen LVS, antenna nets and antenna pins.

| | |
|---|---|
| Functional cells | 134.0k um2 |
| of which flops | 1846 |
| Clock gates | 26 CGX3 |
| Decoupling | 2231 DECAPHV, 33.6 pF |
| Setup worst slack | +43.64 ns, slow corner |
| Hold worst slack | +0.044 ns, fast corner |
| Max-slew, slow corner | 193 |
| Power at typical, `make power-vcd` | 2.979 uW |
| `sim-gl` | 1343 samples identical to RTL |
| `model-gate` | all 8 stimulus patterns match the model, RTL and gate level |
| `sim-cdc` | 24 sweeps, 0 of 48 words stale in each |
| `sim-rtl-cocotb`, `sim-gl-cocotb` | 6 of 6 on 2026-11-13, gate level on this netlist: reset values, write and read back with the port mapping, `adc_conv` cadence, decimator enable, `data_in` bit-exact against the model, full scale |
| `lec` | open: EQY timed out at 10800 s with 946 of 1325 partitions proved and 0 failed, under a load of about 25 on 12 threads. Its work dir passed 5 GB, so it was not rerun |

Detailed placement runs without cell padding (`DPL_CELL_PADDING` 1, which is 0 per side). With padding the 404.88 x 504 um try failed legalization, without it the router reached 0.

Setup slack is +44 ns against the decimator's +491 ns because this path is in the `sclk` domain, constrained at 100 ns while `clk` sits at 1000 ns. Expected, not a warning.

### Leakage

Transistor level, `../scripts/leakage_sim.py --corner tt`, on the hardened netlist. Banning EZ130's thin-oxide `DECAP*` was worth 6.2x on the 497 um macro of 2026-09-30:

| | thin-oxide | thick-oxide |
|---|---|---|
| decap cells | 5998 | 2344 |
| decap leakage | 5967 nW | ~0 nW |
| share of the block | 83.6 % | 0.0 % |
| block total | 7.136 uW | 1.157 uW |

The 409.08 x 514.08 um macro measures 1.136 uW with 2231 DECAPHV, against 1.137 uW with 1035 for the 370.02 x 588 um one. The 1.171 uW in the root README is the liberty leakage of `make power-vcd` at typical (`verification/power_vcd_nom_typ_1p20V_25C.rpt`), not this transistor-level number.

`~0 nW` is a floor, not a number: IHP sets `iginvlw = 0` for both 3.3 V devices, so the model has no gate tunnelling term for thick oxide and the solver returns residue. The physics is right and the 7.136 uW is a real measurement.

The total moves 1.089 to 1.157 uW between runs because a few cells hit a non-deterministic ngspice failure and drop out (XOR3X1, CGX3 and ANTENNA2 fall back to the liberty value). It under-counts when that happens.

## Open

- The macro GDS in `final/gds` carries no metal fill: Metal1 to Metal4 sit at 28.53, 16.80, 13.46 and 5.96 % over its 409.08 x 514.08 um, which is 32.9 % of an 800 um window. `macros/scripts/fill_macro.sh` takes them to 30.49, 19.33, 15.45 and 47.97 %. `M<n>Fil.h` is a 25 % minimum over the window, so the die around the macro must carry the rest. Recheck the chip's density log after the floorplan change.
