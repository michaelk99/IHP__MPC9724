<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
Description: what the chip-level testbenches cover, and what they do not
-->

# Chip-level testbenches

What is verified at the top level, how to run it, and what is still unproven.

Macro-level verification lives with the macros: each runs one Verilog testbench on its RTL and on its hardened netlist and requires identical output files (`make -C macros/<m> sim-gl`). The decimator also checks both against the bit-true model in `models/` (`make -C macros/decimator model-gate`), which shows they are right, not only that they agree. This directory covers the chip: the padframe, the pad mapping, and the `dsa1_dig_top` macro and `dsm2_core` wired into it.

| Bench | Kind | State |
|---|---|---|
| `cocotb/sg13cmos5l_dsa1_dig_top_tb.py` | functional, Icarus | 14 tests, 13 pass at RTL and gate level and the PSD one is opt-in |
| `xschem/sg13cmos5l_dsa1_dig_top_tb_tran.sch` | analog transient, ngspice | **stimulus still the template's**, DUT symbol now correct |
| `fpga/` | two FPGA boards, Icarus | 9 programs pass the checker in simulation, the DUT build ran on hardware with the ESP32 host, see [fpga/README.md](fpga/README.md) |

## The cocotb bench

```sh
make sim-rtl-cocotb          # chip RTL, macro as a hard block
make sim-gl-cocotb           # chip gate-level netlist
make sim-view-cocotb         # waveforms, WAVEFORM_VIEWER=gtkwave|surfer
```

It needs `EZ130_DIR`, because the macro is read as a hardened netlist whose cell models live outside this repository. The runner raises a clear error when the variable is wrong.

### What each test covers

| Test | What it proves |
|---|---|
| `test_register_read_invert_write_read` | all 13 writable registers read back what was written, then restore. Plus the two ADC data registers, see below |
| `test_step_response` | the on-chip step stimulus drives the filter to +full scale through the padframe |
| `test_step_response_negative` | the mirror, and the only thing that drives the core to `DATA_MIN` |
| `test_impulse_response` | the on-chip impulse stimulus, on a zero background |
| `test_half_scale_linearity` | the period-4 pattern of mean +1/2 settles at half scale, so the gain is linear across three points |
| `test_prbs_noise` | PRBS23 in, so the output is the filter's noise bandwidth |
| `test_dsm2_on_after_reset` | with no SPI write dsm2 is enabled and drives its pads, `di_rst_b` rises 9 to 10 `clk` periods after `rst_n` |
| `test_writing_one_turns_dsm2_off` | `DSM_EN`, `DSM_RST_B` and `DSM_QOUT_EN` written 1 turn each function off, 0 brings it back |
| `test_bias_cfg_reaches_dsm2` | every dsm2 field of `BIAS_CFG_0` and `BIAS_CFG_1` reaches its own pin and no other, bits 7 and 8 of `BIAS_CFG_0` the oscillator pins, bit 9 nothing |
| `test_oscillator_drives_dsm_clk` | after reset `dsm_clk` is an input that dsm2's `di_clk` follows. Once the board lets go and bits 7 and 8 are set, dsm2 alone drives the pad from the model's 0.8 MHz oscillator, and the pad lets go when bit 8 is cleared |
| `test_dec_src_decimates_dsm2_bit_exact` | with `DEC_SRC` high the decimator reads `do_q_dec`, word for word the model's |
| `test_adc_conv_en_holds_the_pad` | `ADC_CONV_EN` low holds `adc_conv` low, high brings the strobe back |
| `test_dsa1_profile_then_reset_value_restores_data_in` | the DSA1 die's bias values select dsm2's bit and stop the strobe, the reset value brings `data_in` and the strobe back |
| `test_psd` | opt-in with `PSD=1`, the real modulator bitstream through the whole chain, passing |


### Two register-file properties worth knowing

Both matter for bring-up software:

- **The ADC data registers are not write protected.** `dsa1_ic_bus_slave` writes `dataReg(addr)` for any address whose read bit is clear, so address 0 accepts a write like any other until the next conversion overwrites it. The test asserts that the write lands, a conversion clears it, and the top 10 bits of the HIGH word are hardwired zero.
- **`ADC_DATA_LOW` does not read back address 1.** It returns `adc_low_freeze_reg`, latched when HIGH is read, so a HIGH/LOW pair always belongs to one conversion. The test reads LOW twice across two conversions with no HIGH read in between and requires the word to hold. **Always read HIGH first.**

### What the register test deliberately skips

`TEST_CTRL_0` is left out of the blanket invert. Its bits 7:6 are the bias test mux, and the startup notes document code `11` as a hazard that must never be written, so a test that could later be pointed at silicon must not write it. The stimulus tests cover the register instead.

### The PSD test

```sh
PSD=1 make sim-rtl-cocotb                  # 1024 output words, the default
PSD=1 PSD_SAMPLES=8192 make sim-rtl-cocotb # the MATLAB resolution, hours
```

It reads the CIFF4 modulator record of the HDL benches, 81 MB, in place from `STIM_FILE`. Conventions from that bench: `fs` 65536 Hz, a 42 Hz tone at -4 dBFS, 4194304 samples, which is 64 s and the 1/64 Hz resolution of the MATLAB PSD.

1024 is the default because **42 Hz is coherent in any multiple of 256** at the 512 Hz output rate: 1024 samples hold exactly 84 cycles, so the tone lands on a bin whatever the start offset, and discarding samples while the filter fills costs nothing.

It asserts the tone's bin, its level, in-band SNDR, and stopband rejection. The stopband at this output rate is FB to 2*FB (2*FB is Nyquist), and the level is amplitude referred, as in the MATLAB bench and the report, and bracketed on both sides.

**It passes.** 13 minutes at the 1024-word default, RTL, on 2026-09-23. The bit-true model in `models/` predicts the same window in about two seconds: tone in bin 84 at -4.02 dBFS, in-band SNDR 126.3 dB, and the largest stopband bin 135.5 dB below the tone. The chip must agree, since the chain is bit-true end to end and the synchronizer only shifts the bitstream by three input samples.

## Traps already hit in this bench

- **Indexing a pad vector handle positionally picks the wrong end.** It showed as every SPI read returning zero while writes worked. The helpers mask the integer value instead.
- **The macro is read as a hard block in both flavours**, because its RTL is VHDL and Icarus cannot read it. Its RTL-against-netlist equality is proved by `make -C macros/dsa1_dig sim-gl`, not here.
- `sclk` must be faster than `clk`: the register file captures a new ADC word only on `sclk` edges while the synchronized ready flag is high.

## What the top-level schematic is, and what LVS it does not do

`schematic/xschem/sg13cmos5l_dsa1_dig_top.sch` is generated by `make schematic` from the `PAD_*` lists in `flow/librelane/config.yaml` and the port map in `rtl/sg13cmos5l_dsa1_dig_core.sv`, so it cannot drift from them. It holds the 20 pads with the two clamp copies and the two cut cells, the `DEC_SRC` mux and the three-flop bitstream synchronizer, the two glue gates, the `dsa1_dig_top` macro and `dsm2_core`, and its 13 ports match the synthesized netlist. VDD and VDDA are separate nets, the segment's pads are on VDDA.

**It is not the sign-off LVS reference, and on this PDK it cannot be.** From a full `make klayout-lvs` run:

```
Devices to compare: layout=277536 schematic=5
```

The layout extracts 277536 transistor-level devices. A schematic of pad cells and one hard macro offers five subcircuit calls and no definitions, so there is nothing to compare. Making it compare would mean the whole design as transistors in the CDL, from the EZ130 library, the IO cells and the macro's gate-level netlist. That is the netlist, and netgen already compares the layout against it inside the flow:

```
Final result: Circuits match uniquely.
```

`verification/reports/lvs.netgen.rpt`, including the pad pin list. The template's own tutorial also calls top-level LVS "under construction" on `ihp-sg13cmos5l`, and the PDK ships no Xschem symbol for `sg13cmos5l_dfrbpq_1`, the flop synthesis used for the synchronizer, so the drawn sheet substitutes `dfrbp_1` with `Q_N` left open.

The drawn schematic serves the transient testbench and the documentation, not sign-off. `make klayout-lvs` and `make magic-lvs` stay in place and still fail, which is not a layout defect.

## The Xschem transient bench is still stale

`testbenches/xschem/sg13cmos5l_dsa1_dig_top_tb_tran.sch` and `plot_simulations/plot_sg13cmos5l_dsa1_dig_top.py` still drive the template's counters. The DUT symbol underneath is correct, so only the stimulus needs rewriting. `make sim-gl-xschem` and `sim-all` are not meaningful until then.

## Summary of what is and is not verified

| | |
|---|---|
| Pad mapping, SPI register file, stimulus path | cocotb, 13 tests, RTL and gate level |
| Dynamic power at the real clock | `make power-vcd`, 2.979 uW typical |
| Macro RTL against its hardened netlist | `sim-gl`, 1343 observations |
| Filter against the bit-true model | `models/`, 500 samples for the decimator and all 8 stimulus modes for the digital top, RTL and gate level |
| Decimated spectrum through the chip | `PSD=1`, 1024 words, passes |
| Chip against the synthesized netlist | netgen, circuits match uniquely, also from the GDS with every cell device by device (`verification/lvs/top_lvs.sh`) |
| Chip against a drawn schematic at transistor level | not possible on this PDK, see above |
| Supply start-up transient on the bench scenario | [startup/](startup/README.md), `core_first`, `io_first` and `vdda_last` pass, VDDA no later than VDD and both no later than IOVDD on the board |
