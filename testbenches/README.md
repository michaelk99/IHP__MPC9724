<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
Description: what the chip-level testbenches cover, and what they do not
-->

# Chip-level testbenches

What is verified at the top level, how to run it, and what is still unproven.

Macro-level verification lives with the macros: each one runs one Verilog
testbench on its RTL and on its hardened netlist and requires the two output
files to be identical (`make -C macros/<m> sim-gl`). The decimator goes one
step further and checks both against the bit-true model in `models/`
(`make -C macros/decimator model-gate`), which is the difference between the
two agreeing and the two being right. This directory is about the chip: the
padframe, the pad mapping, and the one macro wired into it.

| Bench | Kind | State |
|---|---|---|
| `cocotb/sg13cmos5l_dsa1_dig_top_tb.py` | functional, Icarus | 8 tests, 7 pass and the PSD one is opt-in |
| `xschem/sg13cmos5l_dsa1_dig_top_tb_tran.sch` | analog transient, ngspice | **stimulus still the template's**, DUT symbol now correct |
| `fpga/` | two FPGA boards, Icarus | 8 programs pass the checker, nothing on hardware, see [fpga/README.md](fpga/README.md) |

## The cocotb bench

```sh
make sim-rtl-cocotb          # chip RTL, macro as a hard block
make sim-gl-cocotb           # chip gate-level netlist
make sim-view-cocotb         # waveforms, WAVEFORM_VIEWER=gtkwave|surfer
```

It needs `EZ130_DIR`, because the macro is read as a hardened netlist and its
cell models live outside this repository. The runner raises a clear error
rather than failing obscurely when the variable is wrong.

### What each test covers

| Test | What it proves |
|---|---|
| `test_register_read_invert_write_read` | all 13 writable registers read back what was written, then restore. Plus the two ADC data registers, see below |
| `test_tst_ctrl_reaches_the_pads` | `o_tst_ctrl[15:0]` written over SPI appears on `output_PAD[17:2]` |
| `test_step_response` | the on-chip step stimulus drives the filter to +full scale through the padframe |
| `test_step_response_negative` | the mirror, and the only thing that drives the core to `DATA_MIN` |
| `test_impulse_response` | the on-chip impulse stimulus, on a zero background |
| `test_half_scale_linearity` | the period-4 pattern of mean +1/2 settles at half scale, so the gain is linear across three points |
| `test_prbs_noise` | PRBS23 in, so the output is the filter's noise bandwidth |
| `test_psd` | opt-in with `PSD=1`, the real modulator bitstream through the whole chain, passing |

Together the first four are the only simulation of the **pad mapping** and the
**bitstream synchronizer**. Before they existed both were verified by reading
the netlist, which is not verification.

### Two register-file properties worth knowing

Both were found by writing this bench, and both matter for bring-up software:

- **The ADC data registers are not write protected.** `dsa1_ic_bus_slave`
  writes `dataReg(addr)` for any address whose read bit is clear, so address 0
  accepts a write like any other. It only looks read only because the next
  conversion overwrites it. The test asserts exactly that: the write lands, a
  conversion clears it, and the top 10 bits of the HIGH word are hardwired
  zero.
- **`ADC_DATA_LOW` does not read back address 1.** It returns
  `adc_low_freeze_reg`, latched when HIGH is read, so a HIGH/LOW pair always
  belongs to one conversion. The test reads LOW twice across two conversions
  with no HIGH read in between and requires the word to hold. **Always read
  HIGH first.**

### What the register test deliberately skips

`TEST_CTRL_0` is left out of the blanket invert. Its bits 7:6 are the bias
test mux and the code `11` is documented in the startup notes as a hazard that
must never be written. Inverting the whole register would put a forbidden
pattern into a test that could later be pointed at silicon. The register gets
targeted coverage in the stimulus tests instead.

### The PSD test

```sh
PSD=1 make sim-rtl-cocotb                  # 1024 output words, the default
PSD=1 PSD_SAMPLES=8192 make sim-rtl-cocotb # the MATLAB resolution, hours
```

It reads the CIFF4 modulator record the HDL benches use, 81 MB, in place from
`STIM_FILE` rather than copying it here. Conventions come from that bench:
`fs` 65536 Hz, a 42 Hz tone at -4 dBFS, 4194304 samples, which is 64 s and
hence the 1/64 Hz resolution the MATLAB PSD uses.

1024 is the default because **42 Hz is coherent in any multiple of 256** at the
512 Hz output rate: a 1024-sample window holds exactly 84 cycles, so the tone
lands on a bin whatever the start offset. That is also why discarding output
samples while the filter fills costs nothing.

It asserts the tone lands in the expected bin, its level, in-band SNDR, and
stopband rejection.

**It passes.** 13 minutes at the 1024-word default, RTL, on 2026-09-23. The
bit-true model in `models/` predicts the same window analytically in about two
seconds: tone in bin 84 at -4.02 dBFS, in-band SNDR 126.3 dB, and the largest
stopband bin 135.5 dB below the tone. The chip must agree, since the chain is
bit-true end to end and the synchronizer only shifts the bitstream by three
input samples.

Two bugs came out of running it, both of which had made it useless:

- **`freqs > 2 * FB` selects nothing.** Nyquist of the 512 Hz output is 256 Hz
  and `2 * FB` is 256 Hz, so the rejection check took `.max()` of an empty
  array and raised `ValueError` rather than failing an assertion. The stopband
  at this output rate is FB to 2*FB, which is what it now uses.
- **The tone level was RMS referred while the assertion talked about -4 dBFS.**
  A full-scale sine is -3.01 dBFS in RMS terms, so the test measured -7.03 and
  compared it against a threshold meant for amplitude. It now reports
  amplitude, the convention the MATLAB bench and the report use, and brackets
  it instead of using a one-sided threshold that -7 also satisfied.

## Traps already hit in this bench

- **Reading a pad bit by indexing the handle positionally picks the wrong end
  of the vector.** It presented as every SPI read returning zero while writes
  still worked, which looks like a broken read path rather than a broken
  testbench. The helpers mask the integer value instead.
- **The macro is read as a hard block in both flavours**, because its RTL is
  VHDL and Icarus cannot read it. The macro's own RTL-against-netlist equality
  is proved by `make -C macros/dsa1_dig sim-gl`, not here.
- `sclk` must be faster than `clk`: the register file captures a new ADC word
  only on `sclk` edges while the synchronized ready flag is high.

## What the top-level schematic is, and what LVS it does not do

`schematic/xschem/sg13cmos5l_dsa1_dig_top.sch` described the template's counters
and inverters until 2026-09-23. It is now generated by `make schematic` from the
`PAD_*` lists in `flow/librelane/config.yaml` and the port map in
`rtl/sg13cmos5l_dsa1_dig_core.sv`, so it cannot drift from them again. It holds
the 32 pads, the three-flop bitstream synchronizer and the `dsa1_dig_top` macro,
and its 32 ports match the synthesized netlist exactly.

**It is not the sign-off LVS reference, and on this PDK it cannot be.** The
measurement that settles it, from a full `make klayout-lvs` run:

```
Devices to compare: layout=277536 schematic=5
```

The layout extracts 277536 transistor-level devices. A schematic that
instantiates pad cells and one hard macro offers five subcircuit calls and no
definitions, so there is nothing to compare. Making that comparison work would
mean putting the whole design into the CDL as transistors, assembled from the
EZ130 library, the IO cells and the macro's gate-level netlist. That is not a
schematic, it is the netlist, and comparing the layout against the netlist is
exactly what netgen already does inside the flow:

```
Final result: Circuits match uniquely.
```

`verification/reports/lvs.netgen.rpt`, including the pad pin list. Two smaller
facts point the same way: the template's own tutorial calls top-level LVS "under
construction" on `ihp-sg13cmos5l`, and the PDK ships no Xschem symbol for
`sg13cmos5l_dfrbpq_1`, the flop synthesis actually used for the synchronizer, so
the drawn sheet substitutes the `dfrbp_1` variant with `Q_N` left open.

So the drawn schematic's job here is the transient testbench and the
documentation, not sign-off. `make klayout-lvs` and `make magic-lvs` are left in
place and still fail; do not read that as a defect in the layout.

## The Xschem transient bench is still stale

`testbenches/xschem/sg13cmos5l_dsa1_dig_top_tb_tran.sch` and
`plot_simulations/plot_sg13cmos5l_dsa1_dig_top.py` still drive the template's
counters. The DUT symbol underneath them is correct now, so the bench needs its
stimulus rewritten rather than a rebuild from scratch. `make sim-gl-xschem` and
`sim-all` are not meaningful until that is done.

## Summary of what is and is not verified

| | |
|---|---|
| Pad mapping, SPI register file, stimulus path | cocotb, 7 tests, RTL and gate level |
| Dynamic power at the real clock | `make power-vcd`, 3.061 uW typical |
| Macro RTL against its hardened netlist | `sim-gl`, 527 observations |
| Filter against the bit-true model | `models/`, 500 samples for the decimator and all 5 stimulus patterns for the digital top, RTL and gate level |
| Decimated spectrum through the chip | `PSD=1`, 1024 words, passes |
| Chip against the synthesized netlist | netgen, circuits match uniquely, also from the GDS with every cell device by device (`verification/lvs/top_lvs.sh`) |
| Chip against a drawn schematic at transistor level | not possible on this PDK, see above |
| Supply start-up transient on the bench scenario | [startup/](startup/README.md), both orders, VDD must come first |
