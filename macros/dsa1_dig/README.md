<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# dsa1_dig_top

The DSADC1 digital back end, and the only macro on this die. It holds the 128x
decimation filter, an SPI slave and the configuration register file.

One bitstream goes in and 22-bit words come out over SPI at 512 Hz.

| | |
|---|---|
| Top cell | `dsa1_dig_top` |
| Standard cells | EZ130 8T, read from `EZ130_DIR` |
| Decoupling | `DECAPHV8/16/32` only, from `DECAPHV_DIR` |
| Die | 497.28 um square |
| Clocks | `clk` 65536 Hz, `sclk` 200 kHz, asynchronous |

## Where the RTL comes from

`rtl/` is a frozen copy from the jku-phd development repo
(`circuit-level/hdl/DSADC1`), with the VHDL entity renamed from
`dsa1_dig_top_v2` to `dsa1_dig_top`. The decimator is not copied: both macros
read the same six SystemVerilog files from `../decimator/rtl`.

LibreLane reads one language per run, so `make rtl-gen` is two steps. `ghdl
synth` turns the VHDL into Verilog with `decimator_top` left unbound, then the
yosys pre-pass clock-gates that together with the decimator RTL. The pre-pass
exists because yosys `clockgate` skips a flop whose synchronous reset overrides
its enable, which is every register here.

## The register file stays, on purpose

Nothing on this chip reads the 145 configuration output bits. They are here so
the taped area is comparable against the older `dsa1_dig_top`. Only the eight
scalar pins reach the padframe, plus `o_tst_ctrl[15:0]`, which is bonded out so
the SPI write path can be checked on the die.

Two properties of the register file that bring-up software has to know, both
found by writing the chip-level testbench:

- **The ADC data registers are not write protected.** `dsa1_ic_bus_slave` writes
  `dataReg(addr)` for any address whose read bit is clear, so address 0 accepts
  a write like any other. It only looks read only because the next conversion
  overwrites it.
- **`ADC_DATA_LOW` does not read back what was written to address 1.** It returns
  `adc_low_freeze_reg`, latched when HIGH is read, so a HIGH/LOW pair always
  belongs to one conversion. Always read HIGH first.

## Stimulus test mode

`TEST_CTRL_0` carries an on-chip stimulus generator, so the filter response can
be measured in silicon without feeding in a precise external bitstream.

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

Bit 9 is the analog top's and is never written from here. Bits 10 and 8 are
`FLAG_SYNC_EN` and `PAD_Q_EN`, both reset 1, so every write to this register
has to keep the `0x0500` base.

Enable and trigger are separate, and that is not optional. The decimator holds
about 32 output samples of history, so firing on the enable edge buries the
event under whatever the filter was full of. The sequence is: set bit 11, wait
for the output to settle to zero on the idle pattern, then set bit 12.

**The trigger only arms.** The pattern starts at the next `valid_strobe`, so
every shot begins on the same phase of the 128-cycle decimation window. Without
that the SPI-written trigger lands anywhere in the window, the impulse response
shifts run to run and its polarity is a coin toss.

The idle pattern is an alternating bitstream at `clk`/2, which the filter
rejects completely, so the output sits at zero with no DC pedestal to subtract.
That is what makes a step and an impulse well defined on a one-bit input: a +-1
stream cannot be zero, but an alternation decimates to zero.

Measured on RTL at the 512 Hz output rate, and reproduced sample for sample by
`models/stimulus.py`:

| pattern | settles at | peak |
|---|---|---|
| step + | 1048232 | 1128189, the compensator overshoot |
| step - | -1048232 | -1127982 |
| half scale | 524116, exactly half of the step | 563999 |
| impulse | 0 | -11246 |
| PRBS23 | wanders about zero | order 1e5 |

The three dc points are -1048232, +524116 and +1048232, so the gain is linear
to the LSB across the range. A settled step is a constant in the ideal, so its
ripple is the sinc chain's per-section truncation noise, measured for free, and
PRBS23 measures the filter's noise bandwidth from a white one-bit input.

`make model-gate` checks all five against the model.

## Building it

```sh
make rtl-gen        # ghdl synth, then the yosys clock-gate pre-pass
make librelane      # harden
make build-top      # harden, collect views and reports, render
make sim-gl         # the gate-level netlist must equal the RTL, sample for sample
make check-netlist  # no cell that is wrong in silicon reached the netlist
```

`EZ130_DIR` and `DECAPHV_DIR` point at checkouts outside this repo and default
to `~/projects/OpenBLAU/ip/...`. `check-ez130` fails loudly if either is wrong.
EZ130 is a prerelease and deliberately does not ship here.

## FPGA evaluation

`make build-fpga` puts the **top level** on an FPGA, ULX3S by default. The SPI
slave is the readout, so a host reads the decimated word over the chip's own
interface. Synthesis and place-and-route pass, 1903 flops against 1862 in the
hardened macro, about 2 % of an ECP5-85F, `clk_fs` closing at 28.54 MHz against
the 65.536 kHz it needs. Nothing has run on hardware yet. See
[fpga/README.md](fpga/README.md).

## Results

LibreLane run of 2026-09-30, container `2026.08`, EZ130 8T, thick-oxide
decoupling. Every signoff check is zero: router DRC, Magic DRC, KLayout DRC,
netgen LVS, antenna nets and antenna pins.

| | |
|---|---|
| Functional cells | 137733 um2 |
| of which flops | 1846 |
| Clock gates | 26 CGX3 |
| Decoupling | 2260 DECAPHV |
| Setup worst slack | +44.27 ns |
| Hold worst slack | +0.074 ns |
| Max-slew, slow corner | 145 |
| Power at typical, `make power-vcd` | 3.061 uW |
| `sim-gl` | 527 observations identical to RTL |
| `model-gate` | all 5 stimulus patterns match the model, RTL and gate level |
| `lec` | EQY, netlist equal to the RTL, 1325 of 1325 partitions |

Setup margin is +44 ns against the decimator's +491 ns because this is the
`sclk` domain, constrained at 100 ns while `clk` sits at 1000 ns. That is the
expected number, not a warning.

### Leakage

Transistor level, `../scripts/leakage_sim.py --corner tt`, on the hardened
netlist. Banning EZ130's thin-oxide `DECAP*` is worth 6.2x:

| | thin-oxide | thick-oxide |
|---|---|---|
| decap cells | 5998 | 2344 |
| decap leakage | 5967 nW | ~0 nW |
| share of the block | 83.6 % | 0.0 % |
| block total | 7.136 uW | 1.157 uW |

Read the `~0 nW` correctly: IHP sets `iginvlw = 0` for both 3.3 V devices, so a
thick-oxide gate carries no tunnelling term in the model at all and the solver
returns residue. The physics is right and the 7.136 uW is a real measurement,
but this is a floor rather than a number.

The total also moves 1.089 to 1.157 uW between runs, because a few cells hit a
non-deterministic ngspice failure and drop out. It under-counts when that
happens.

## Open

- Metal2 and Metal3 sit at 18.46 % and 16.57 % inside the macro. That is not a
  violation, `M<n>Fil.h` is a 25 % minimum over an 800 x 800 um window and this
  block is 38.6 % of one, and the chip's density run reports no window failures.
  The die around the macro carries 52.3 % and 56.5 % against the 29.1 % and
  30.3 % the arithmetic needs. A floorplan that put a second sparse block in the
  same window would break it, so recheck the density log after any move.
