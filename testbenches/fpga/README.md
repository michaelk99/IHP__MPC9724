<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# Two-board FPGA bring-up

The master board stands in for the rest of the ADC and for the lab host: it owns `clk_fs` and `data_in`, as the chip's surroundings will, drives the SPI slave of the DUT board, and reports every transaction and conversion over its UART. Everything here is simulated and built. **Nothing has run on hardware yet.**

The DUT board is [macros/dsa1_dig/fpga](../../macros/dsa1_dig/fpga/README.md), a ULX3S carrying `dsa1_dig_top`. The master is a second ULX3S, built from this folder.

## Wiring

```
   MASTER board (this folder)             DUT board (macros/dsa1_dig/fpga)
   --------------------------             --------------------------------
   dsa1_ic_bus_master  --- sclk  ------>  sclk
                       --- mosi  ------>  mosi
                       <-- miso  -------  miso
                       --- ss    ------>  ss
   bitstream source    --- data_in ---->  data_in_pin
   fs_gen              --- clk_fs  ---->  clk_fs_pin (DUT SW1 on)
                       <-- adc_conv ----  adc_conv_pin
   sequencer           --- rst_n   ---->  rst_n_pin
                       --- GND  --------  GND
   UART to the host (FTDI)
```

Both `ulx3s.lpf` files use the same J1 positions, so the jumpers go straight across. Ground has to be connected too.

| Signal | J1 | Site | Master | DUT |
|---|---|---|---|---|
| `data_in` | gp[0] | B11 | out | in |
| `sclk` | gn[0] | C11 | out | in |
| `mosi` | gp[1] | A10 | out | in |
| `ss` | gn[1] | A11 | out | in, pull-up |
| `adc_conv` | gp[2] | A9 | in | out |
| `clk_fs` | gn[2] | B10 | out | in, pull-down |
| `rst_n` | gp[3] | B9 | out | in, pull-up |
| `miso` | gn[3] | C10 | in | out |
| GND | GND | | | |

The master's UART goes out on `ftdi_rxd` (L4), the board's own USB port.

## Switches and LEDs

Master: SW1 to SW4 are the program number, read at reset. LEDs: `led[0]` adc_conv, `led[1]` halted, `led[2]` capturing, `led[3]` loopback, `led[7:4]` the program number.

DUT: SW1 on takes `clk_fs` from the master, read at reset. Off, the DUT makes its own 65536 Hz. The DUT LEDs show `adc_conv` and `o_tst_ctrl[6:0]`, as before.

## Programs

| Program | What it does | What it proves | PLAN.md 1c step |
|---|---|---|---|
| 0 | loopback: mosi fed to miso inside the master, ss held high | the master, the sequencer and the UART, with no DUT | 2 |
| 1 | reset, every writable register inverted, read back and restored, then the startup sequence | the SPI write and read path, reset values, write returns the old value | 3 |
| 2 | step + | on-chip stimulus through the filter, against `models/stimulus.py` | 1 and 4 |
| 3 | impulse | same | 1 and 4 |
| 4 | half scale | same, the third point of the gain linearity | 1 and 4 |
| 5 | step - | same, the negative rail | 1 and 4 |
| 6 | PRBS23 | same, the noise bandwidth | 1 and 4 |
| 7 | the modulator record from BRAM, captured forever | the real bitstream bit-exact against `models/decimator_model.py`, and the DUT on the master's clock | 5 |

The source is [seq/programs.seq](seq/programs.seq), with the startup sequence of `startup.md` step for step in [seq/startup.seq](seq/startup.seq). [seq/seqasm.py](seq/seqasm.py) assembles it and refuses a `TEST_CTRL_0` value that drops the `0x0500` base, sets bit 9, puts `11` in bits 7:6, selects the undocumented core test page `11`, or selects more than one integrator, and a program that switches the core test mux from one node to another without going through neutral.

## Bring-up

Build and load both boards:

```sh
make -C testbenches/fpga build-master load-master
make -C macros/dsa1_dig build-fpga
make -C macros/dsa1_dig/fpga load_bitstream
```

Then, on the host, open the master's port and press the master's reset button, because a program runs once from reset:

```sh
python3 models/bench_capture.py --port /dev/ttyUSB0 --records 60 --save p2.bin --stream testbenches/fpga/build/stream.mem
```

Every step must end in `OK: every check passes`. Expect the first failure to be pin assignment or SPI polarity, which programs 0 and 1 separate from the filter.

1. **DUT alone on on-chip stimulus.** Programs 2 to 6 with DUT SW1 off, so the DUT runs on its own clock. Wire only `sclk`, `mosi`, `ss`, `miso`, `adc_conv`, `rst_n` and GND, no `clk_fs` and no `data_in`. The checker prints `step+: N words match the model at offset k`, and likewise `impulse`, `steady`, `step-`, `prbs23`.
2. **Master alone.** Program 0, no DUT needed. `8 of 8 SPI transactions checked`.
3. **Register access.** Program 1, all wires. `72 of 72 SPI transactions checked`. Watch `o_tst_ctrl[6:0]` on the DUT LEDs follow the `0x0545` and `0x052A` writes. Against a chip with analog, the SG13G2 DSADC1, program 1 needs the analog owner's OK first: it writes the inverse of every bias, trim and clock register while the blocks are enabled. On the CMOS5L die nothing reads those bits.
4. **On-chip stimulus from the master's sequencer.** Programs 2 to 6, all wires, DUT SW1 on.
5. **Real bitstream.** Program 7, all wires, DUT SW1 on. `stream: N words match the model, lag 3, index steps 128`. The lag must be 3, as in simulation. Steps other than 128 mean the DUT is not on the master's clock.
6. **The silicon hosts against the DUT board.** They and their PC tools are kept with the evaluation setup in the IIC svn, `r_tapeouts/2024_DSADC/TO_IHPSG13G2/eval/dsa1`, see its `README.txt`. They run programs 1 to 6 of this folder and have to pass the same checks. Programs 0 and 7 stay ULX3S only. The DUT for this step can also be an Arty A7-35T with the XIAO ESP32-S3 on a Pmod adapter, or, as the fallback, a Lattice ECP5 Versa wired to the adapter's probe header, see [the Arty section](../../macros/dsa1_dig/fpga/README.md#arty-a7-35t) and [the Versa section](../../macros/dsa1_dig/fpga/README.md#ecp5-versa), which have the wiring and the bench checklist.

## Protocol

The program and record formats, the UART framing, and what the chip requires of any host are in [doc/host_protocol.md](../../doc/host_protocol.md).

## Simulation

```sh
make -C testbenches/fpga sim-unit            # seven unit benches: the Arty, Versa and versa_duo builds, and the bus switch of both duo builds, which needs the legacy RTL from JKU_PHD_DIR
make -C testbenches/fpga sim PROGRAM=2       # both boards on one program, then the checker
make -C testbenches/fpga sim-all             # the unit benches, all eight programs, and sim-slip
```

`sim` compiles both board tops with Icarus, wires them pin for pin with oscillators 50 ppm apart, logs the UART bytes, and runs `models/bench_capture.py` on the log, the same checker that reads the real port. `sim-slip` runs program 7 with the DUT on its own oscillator, 2000 ppm off, and passes only if the checker fails on the stream index: a DUT that is not on the master's `clk_fs` has to be caught.

Measured on 2026-09-23, container `2026.08`:

| Program | Checker | Wall time |
|---|---|---|
| 0 | 8 of 8 SPI transactions checked | 6 s |
| 1 | 72 of 72 SPI transactions checked, writes return the old value | 25 s |
| 2 | step+: 46 words match the model at offset 2, settled at 1048232 | 153 s |
| 3 | impulse: 46 words match the model at offset 2, settled at 0 | 153 s |
| 4 | steady: 46 words match the model at offset 2, settled at 524116 | 138 s |
| 5 | step-: 46 words match the model at offset 2, settled at -1048232 | 150 s |
| 6 | prbs23: 46 words match the model at offset 2, settled at 101477 | 148 s |
| 7 | stream: 48 words match the model, lag 3, index steps 128 | 181 s |
| slip | stream index steps [127, 128], caught | 127 s |

## Build

Master board, ULX3S ECP5-85F, yosys and nextpnr-ecp5, 2026-09-23: 467 flip-flops, 710 LUT4, 9 DP16KD (the 16 kB stream window and the ROM, all nine with their contents), board clock closing at 81.8 MHz against 25 MHz.

## Where the master comes from

`dsa1_ic_bus_master.vhd` is the master the chip was designed against. It is read in place from `$(JKU_PHD_DIR)/circuit-level/hdl/DSADC1/SPI/src/`, `JKU_PHD_DIR` defaulting to `../jku-phd`, and never copied: it carries no license here. `gen.mk` turns it into Verilog with `ghdl synth` into `build/`, which git ignores. `sclk_permanent_active` is tied high because the slave takes a new ADC word only on sclk edges.

The modulator record is read in place too, `STIM_FILE`, and `models/stream_window.py` cuts the 131072-bit window into `build/stream.mem`, starting one second in.
