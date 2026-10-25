<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# FPGA evaluation of the digital back end

The **top level** goes on the FPGA, not the decimator alone. That is the whole point: `dsa1_dig_top` carries the SPI slave, so a host reads the decimated word out of `ADC_DATA_CH0_HIGH` and `ADC_DATA_CH0_LOW` exactly as it will from the chip. The filter and the bring-up software are exercised by the same run, over the same interface, and the FPGA needs no readout of its own.

```sh
make -C macros/dsa1_dig synth-fpga    # yosys only, resource report
make -C macros/dsa1_dig pnr-fpga      # place and route, timing
make -C macros/dsa1_dig build-fpga    # through to a bitstream
make -C macros/dsa1_dig/fpga load_bitstream   # or flash_bitstream, see the board Makefile
```

`BOARD` selects the board and defaults to `ulx3s`. Three are set up, the ULX3S (ECP5-85F, yosys and nextpnr-ecp5), the Arty A7-35T (Artix-7, the openXC7 flow in Docker, see [below](#arty-a7-35t)) and the Lattice ECP5 Versa kit (ECP5-45F, yosys and nextpnr-ecp5, see [below](#ecp5-versa)). `dsa1_dig_top` is around 1900 flops and a 27-bit datapath, which is comfortable on either. The template's iCE40 boards were dropped from this macro rather than left as untested stubs, and an iCE40HX1K (1280 logic cells) cannot hold it.

## What is measured so far

Yosys and nextpnr-ecp5 on the ULX3S, 2026-09-23, after the external clock and reset of the two-board bring-up. Synthesis and place-and-route both complete. **Nothing has been run on hardware yet.**

| | |
|---|---|
| Flip-flops | 1903, against 1865 before the stimulus field was extended |
| LUT4 | 868 |
| Carry cells (`CCU2C`) | 744 |
| `PFUMX` / `L6MUX21` | 53 / 3 |
| Share of an ECP5-85F | about 2 % of 83640 LUTs |
| `clk_fs` closure | 28.54 MHz, against the 65.536 kHz it needs |
| `sclk` closure | 84.12 MHz, against 200 kHz |
| Board clock | 241.96 MHz, against 25 MHz |

The flop count is the number worth watching: it tracks the ASIC side, the difference being the harness, which says the same design is being evaluated and not a variant synthesis optimised differently. The +38 over the previous 1865 accounts for itself exactly: 23 for the PRBS23 LFSR, 6 for the repeat counter, 2 for the half-scale counter, one each for armed, fired and the two extra config synchronizer stages of the extended stimulus field, and one for the `ext_fs` select of the external clock.

Timing has no meaning as a chip result, the margins are three orders of magnitude. It matters only as evidence the design is not accidentally combinational somewhere.

## What the harness adds, and why

`rtl/dsa1_dig_fpga_top.sv` adds only what a board needs and what the chip gets from its padframe and core:

- **a 65536 Hz clock**, either from the board oscillator through `fs_gen.sv` or, with SW1 on at reset, from the master board's `clk_fs_pin`. A host with no hand on the switch asks for the pin's clock by writing TEST_CTRL_1 (register 13) bit 0 = 1, and for the board clock again with 0. Either takes effect at the next reset. The harness takes the write off the bus itself, framed as the slave frames it, so it needs no port on the die and works whichever back end is selected. A DUT reset returns the dies' TEST_CTRL_1 to 0, so the harness keeps its own copy, through every reset of `rst_n_pin`, until the board's reset button. `sim-dut-extclk` checks all of it. The second is the chip's real situation: clock and bitstream both arrive from outside. `fs_gen` is a phase accumulator, so that any board frequency works and the average rate is exact to the accumulator width instead of to an integer divider. 25 MHz does not divide by 65536 evenly, so a plain counter would be 0.06 % off and the comparison against a bit-true reference would drift. The master board uses the same `fs_gen`.
- **a reset synchronizer** on the push button, ANDed with `rst_n_pin` from the master board, which is pulled up so the board still runs alone.
- **the three-flop synchronizer on `data_in`** that `sg13cmos5l_dsa1_dig_core` puts in front of the macro. Without it the FPGA would see a different design from the silicon, by three input samples.

Everything else is wired straight out: the four SPI lines, `adc_conv`, and `o_tst_ctrl[6:0]` on the LEDs.

**`rtl_gen/dsa1_dig_top.v` is the source, not `_cg.v`.** Yosys does not read VHDL, so the FPGA flow starts from the same `ghdl synth` output the ASIC flow does. The clock-gated variant carries EZ130 `CGX3` instances, which mean nothing to an FPGA, and yosys infers its own clock enables anyway.

## Running the evaluation

A second ULX3S, the master board of [testbenches/fpga](../../../testbenches/fpga/README.md), drives this one: it owns `clk_fs` and `data_in`, runs the chip's own SPI master, and reports over UART to `models/bench_capture.py`. The wiring, the programs, the bring-up steps and the simulated results are there. The on-chip stimulus programs also run with this board on its own clock, with no `clk_fs` or `data_in` wired.

**Read HIGH before LOW.** The slave latches the low word when the high word is read, so a pair belongs to one conversion. See [testbenches/README.md](../../../testbenches/README.md).

## Pin map

`ulx3s/ulx3s.lpf`, ULX3S v2.0. The SPI lines sit on the J1 header for a host adapter. `ss_pin` is pulled up so the slave is deselected when nothing drives it.

| Signal | Site | Note |
|---|---|---|
| `clk_board` | G2 | 25 MHz oscillator |
| `rst_n_btn` | D6 | BTN_PWRn, already active low |
| `data_in_pin` | B11 | modulator bitstream |
| `sclk_pin` / `mosi_pin` / `ss_pin` / `miso_pin` | C11 / A10 / A11 / C10 | SPI |
| `adc_conv_pin` | A9 | 512 Hz conversion strobe |
| `clk_fs_pin` | B10 | 65536 Hz from the master board, used when SW1 is on at reset |
| `rst_n_pin` | B9 | reset from the master board, pulled up |
| `ext_fs_sw` | E8 | SW1, on takes `clk_fs` from the pin |
| `led[7:0]` | B2 C2 C1 D2 D1 E2 E1 H3 | `adc_conv` then `o_tst_ctrl[6:0]` |

## Arty A7-35T

`BOARD=arty`, built with the open [openXC7](https://github.com/openXC7) flow: yosys `synth_xilinx`, nextpnr-xilinx, prjxray `fasm2frames` and `xc7frames2bit`, all in the `regymm/openxc7` image. The targets start that image with docker, so **run them on the host, not in the IIC-OSIC-TOOLS container**. Only `rtl_gen/dsa1_dig_top.v` needs the container, for ghdl, once after a VHDL change.

```sh
# once after a VHDL change, in the container
make -C macros/dsa1_dig rtl_gen/dsa1_dig_top.v
# on the host
make -C macros/dsa1_dig/fpga BOARD=arty gen_bitstream   # the first run also builds the chip database, about a minute
make -C macros/dsa1_dig/fpga BOARD=arty load_bitstream  # SRAM, needs openFPGALoader on the host
make -C macros/dsa1_dig/fpga BOARD=arty flash_bitstream # the Quad-SPI flash, kept through a power cycle
```

SRAM is lost at every power cycle, and the DUT then answers every SPI read with 0x0000. `flash_bitstream` writes the board's S25FL128S (2026-10-01, `arty_duo`, 0x0 to 0x220000) and the design runs again right after. The Arty boots from the flash only with its own mode jumper JP1 installed, not to be confused with JP1 on the XIAO adapter.

The chip database is cached in `~/.cache/openxc7`, outside the repository. `arty/arty_top.sv` sets the harness's board clock to 100 MHz, and `make -C testbenches/fpga sim-arty-top` checks that it converts at 512 Hz, not at the 2048 Hz the 25 MHz default would give. nextpnr-xilinx does not model speed grades, so the part is `xc7a35tcsg324-1`, the same die as the board's `-1L`.

Measured 2026-09-29, `regymm/openxc7` with yosys 0.62:

| | |
|---|---|
| Flip-flops | 1971, the 1904 before the AUX_CTRL_0 requests plus their code matcher: the register synchronized in 16 bits, a second sample, the last settled value, and the requests |
| Slice LUTs | 3716 LUT sites of 65200 |
| `CARRY4` | 379 |
| IO | 9 in, 10 out |
| Board clock | 201.57 MHz, against 100 MHz |
| `clk_fs` closure | 31.47 MHz, against 65.536 kHz |
| `sclk` closure | 243.90 MHz, against 400 kHz |

The ULX3S and Versa numbers below and above predate the requests and have not been rebuilt, expect about 60 flops more.

nextpnr-xilinx times only `create_clock -period`, and only on the net behind the input buffer, so `arty.xdc` constrains `u_dut.clk_board`. Its numbers are a sanity check, not sign-off. Every port needs a pin and an IOSTANDARD, there is no unconstrained IO.

### Pins and the host adapter

The DUT signals sit on Pmod JD, which has 200 Ohm series resistors on the board, in the standard Pmod SPI Type 2A order. The XIAO ESP32-S3 host plugs into it on a small adapter board.

| Pmod JD | Signal | FPGA pin | Pull | XIAO pin |
|---|---|---|---|---|
| 1 | `ss_pin` | D4 | up | D3, GPIO4 |
| 2 | `mosi_pin` | D3 | down | D1, GPIO2 |
| 3 | `miso_pin` | F4 | | D4, GPIO5 |
| 4 | `sclk_pin` | F3 | down | D0, GPIO1 |
| 5, 11 | GND | | | GND |
| 6 | 3V3 | | | to XIAO 3V3 through jumper JP1, and to the two pull-ups |
| 7 | `adc_conv_pin` | E2 | | D5, GPIO6 |
| 8 | `rst_n_pin` | D2 | up | D8, GPIO7 |
| 9 | `data_in_pin` | H2 | down | D9, GPIO8, spare |
| 10 | `clk_fs_pin` | G2 | down | D10, GPIO9, spare |
| 12 | 3V3 | | | not connected |

The rest of the board: `clk_board` E3 (100 MHz), `rst_n_btn` C2 (the red RESET button), `ext_fs_sw` SW0 (A8, on takes `clk_fs` from JD pin 10), `led[3:0]` on LD4 to LD7 and `led[7:4]` on the green channel of RGB LD0 to LD3. On the Arty the LEDs show `AUX_CTRL_0[7:0]` (register 12, reset 0xFF00, so all off), all eight under the host's control, `arty_top.sv` sets the harness's `LED_AUX`. AUX_CTRL_0 drives nothing on the chip and nothing in the harness, so a host can write it freely to see the SPI write path, with none of `TEST_CTRL_0`'s rules. `sim-arty-top` writes 0xFFA5 over SPI and checks the LEDs.

The adapter carries two 10 kOhm pull-ups from `ss` and `rst_n` to Pmod pin 6, so both stay inactive before the FPGA is configured and while the XIAO boots, and a 1x10 probe header: GND, ss, mosi, miso, sclk, adc_conv, rst_n, data_in, clk_fs, GND. XIAO D2 (a strapping pin) and D6, D7 (UART0, where the boot ROM prints) stay unconnected.

**JP1 is open whenever the XIAO's USB-C is plugged in**, which is flashing, the monitor and normal bench work, so the XIAO's regulator and the Arty's 3V3 never back-feed each other. Close it only for a standalone run, and then power the Arty from its barrel jack: on USB alone its budget is about 500 mA, and the ESP32-S3's WiFi transmit peaks of about 350 mA on top of the FPGA would brown it out. With JP1 closed there is no serial monitor, the XIAO's address comes from the hotspot's DHCP leases.

### Bench with the ESP32 host and EasyConfig

The host firmware, EasyConfig and `bench_udp.py` are kept with the evaluation setup in the IIC svn, `r_tapeouts/2024_DSADC/TO_IHPSG13G2/eval/dsa1`, see its `README.txt`. SW0 off, so the DUT runs on its own clock and the on-chip stimulus replaces the bitstream. For the ESP32 host's `P`, which plays a modulator record into `data_in` with its own `clk_fs`, either SW0 goes on or `bench_record.py --harness-clk` asks through TEST_CTRL_1.

1. Before the first plug-in: continuity check of the adapter, no short between Pmod 6 and GND, JP1 open. Plug it into JD with the Arty off.
2. Hotspot up on the PC's WiFi, 2.4 GHz, and UDP 57345 open in the firewall. Load the bitstream.
3. Flash the XIAO over USB-C and read its address from the monitor, `EasyConfig host at <ip>:57345`.
4. On the probe header: `sclk` runs all the time at 400 kHz, `adc_conv` pulses at 512 Hz, `ss` is high between transactions, and `rst_n` stays high while the XIAO's reset button is pressed.
5. `sh EasyConfig/udp_all.sh <ip>` runs programs 1 to 6. Each must end in `OK: every check passes`: program 1 with 72 of 72 SPI transactions checked, programs 2 to 6 with step+ settled at 1048232, impulse at 0, half scale at 524116, step- at -1048232, and PRBS23 on the model.
6. Program 1 must fail with `miso` forced low, a probe-header wire from miso to GND, and pass again without it.
7. EasyConfig: reset values read back as in `regs_cmos5l.csv`, each stimulus pattern in repeat mode streamed to CSV, and a `TEST_CTRL_0` value with `11` in bits 7:6 shown as blocked.

**Nothing has run on hardware yet.**

## Arty A7-35T with both back ends of the eval board

A later eval board is to carry two dies on two SPI buses, one port each on the host: this chip, and the DSA1 die, whose own digital back end is decimator v4 with the same SPI slave. `arty_duo` puts both back ends into one Arty, behind the one Pmod bus the XIAO host has pins for, so a host can be tested against either slave, and the two decimators against each other on the same bitstream.

- **The legacy back end is the one in silicon**, jku-phd at `LEGACY_REV` = `c353a7e`, checked equal to the RTL delivered for the 2024_DSADC tape-out. `legacy.mk` reads it from `JKU_PHD_DIR` at that commit, never copies it into this repo, and ghdl converts it into `legacy/build/`, which git ignores. Both designs call their top `dsa1_dig_top` and their decimator `decimator_top`, so `scripts/prefix_modules.py` prefixes every legacy module with `legacy_`. ghdl needs the container: `make -C macros/dsa1_dig/fpga/arty_duo legacy-rtl` there once, then build on the host as for the Arty.
- **The bus switch**, `DUO=1` in `dsa1_dig_fpga_top.sv`. sclk and mosi reach both back ends, since each needs a running sclk for its ADC flag synchronizer. ss reaches only the selected one, and miso and adc_conv come from it. Both share the reset, `clk_fs` and `data_in`, as on the board, where DSA1's modulator feeds both decimators.
- **Selecting.** Write TEST_CTRL_1 (register 13) bit 1 = 1 for the legacy back end and 0 for this chip's, keeping bit 0 for the clock. The harness decodes the write from the bus, whichever back end takes it. The switch waits for the next rising edge of ss, so neither slave ever sees part of a frame. The choice survives every DUT reset, `P`'s included, and the board button returns to this chip's. The LEDs show the selected back end's AUX_CTRL_0[7:0], and CHIP_ID (register 15) tells the two apart: 0x0001 this chip, read only, 0x0000 the DSA1 die, whose address 15 is plain storage. `sim-duo-switch` checks it, including that AUX_CTRL_0 and a read of 13 do not switch and that a DUT reset keeps the choice once frames run again. EasyConfig's `--duo` writes the same from its Die menu.
- **Measured 2026-09-29**, through the ESP32 host: this chip's back end passes programs 1 to 6, the legacy one program 1 with 78 of 78 transactions (72 since program 1 leaves 13 and 15 alone) (programs 2 to 6 need the stimulus field it does not have), converting at 256 Hz. The jku-phd modulator sine played into both, at 64 kHz: 32768 v5 words and 16384 v4 words bit-true against their models, SNR 126.8 dB and 125.1 dB in 125 Hz. The v4 model is jku-phd's `system-level/python/dec_v4_bit_true.py`, which `models/stream_psd.py` finds through `JKU_PHD_DIR`.

| | arty_duo |
|---|---|
| Flip-flops | 4849 |
| Slice LUTs | 6479 LUT sites of 65200 |
| Board clock | 126.52 MHz, against 100 MHz |
| `clk_fs` closure | 32.09 MHz |
| `sclk` closure | 182.28 MHz |

## ECP5 Versa

`BOARD=versa` and `BOARD=versa_duo`, the Lattice ECP5 Versa Development Kit with an LFE5UM-45F-7BG381I, in the Arty's two builds: this chip's back end alone, and both back ends of the eval board behind one bus, switched through TEST_CTRL_1 as on [`arty_duo`](#arty-a7-35t-with-both-back-ends-of-the-eval-board). yosys, nextpnr-ecp5 and ecppack run in the IIC-OSIC-TOOLS container, only loading runs on the host.

```sh
# in the container
make -C macros/dsa1_dig rtl_gen/dsa1_dig_top.v
make -C macros/dsa1_dig/fpga/versa_duo legacy-rtl            # once, for versa_duo
make -C macros/dsa1_dig/fpga BOARD=versa_duo gen_bitstream   # or BOARD=versa
# on the host
make -C macros/dsa1_dig/fpga BOARD=versa_duo load_bitstream  # openFPGALoader -c ft2232, SRAM
```

The part is the non-5G 45F in speed grade 7, so nextpnr runs with `--um-45k --speed 7`. `versa/versa_top.sv` and `versa_duo/versa_duo_top.sv` set the harness's board clock to 100 MHz, show AUX_CTRL_0[7:0] on the LEDs, which light on a low output, and read DIP switch SW3-1 inverted, because it reads 0 when ON. `make -C testbenches/fpga sim-versa-top` checks all three, `sim-versa-duo-top` the same on `versa_duo_top` plus the switch to the DSA1 back end, where CHIP_ID reads 0x0000.

Built 2026-10-01:

| | versa | versa_duo |
|---|---|---|
| Flip-flops | 1921 | 4730 |
| Logic cells (`TRELLIS_COMB`) | 2624 of 43848 | 5395 of 43848 |
| IO | 19, the 100 MHz clock on the LVDS pair P3/P4 | 19 |
| Global clocks (`DCCA`) | 3 | 3 |
| Board clock | 243.49 MHz, against 100 MHz | 178.86 MHz |
| `clk_fs` closure | 32.06 MHz, against 65.536 kHz | 32.23 MHz |
| `sclk` closure | 95.02 MHz, against 400 kHz | 93.44 MHz |

**JTAG.** The FT2232H's channel A is the JTAG port, and openFPGALoader has no Versa profile, so the board Makefiles use `-c ft2232`. The factory setting of jumper J50 also puts the on-board ispCLOCK (IDCODE 0x00191043) in the chain, which openFPGALoader does not know. The Makefiles declare it with `--misc-device 0x00191043,8,ispclock`, which worked with J50 in its factory setting on 2026-10-01 and also works with J50 set to the FPGA alone (1-2 and 3-5 closed, 4-6 open). The FPGA is index 0, IDCODE 0x01112043.

### Pins and the host wiring

The DUT uses the even row of expansion header X3 (EXPCON1), pins 4 to 18, by the board's `EXPCON_IO` net names, balls from Table 8.7 of the Lattice user guide FPGA-EB-02021. X3 sits on banks 0 and 1, which the board runs at 3.3 V, and every DUT pin is LVCMOS33, the ESP32's levels. Check the header's silkscreen, X3 and X4 are easy to swap.

| X3 pin | Net | Signal | Ball | Pull | Adapter J2 |
|---|---|---|---|---|---|
| 4 | `EXPCON_IO29` | `clk_fs_pin` | B19 | down | 9 |
| 6 | `EXPCON_IO31` | `data_in_pin` | B9 | down | 8 |
| 8 | `EXPCON_IO33` | `rst_n_pin` | D6 | up | 7 |
| 10 | `EXPCON_IO35` | `adc_conv_pin` | D7 | | 6 |
| 12 | `EXPCON_IO37` | `ss_pin` | B6 | up | 2 |
| 14 | `EXPCON_IO39` | `mosi_pin` | D9 | down | 3 |
| 16 | `EXPCON_IO41` | `miso_pin` | C8 | | 4 |
| 18 | `EXPCON_IO43` | `sclk_pin` | E8 | down | 5 |
| 22, or any even pin 22 to 40 | GND | | | | 1 or 10 |

`sclk` is on a plain IO, not a PCLK pin. It reaches its global clock buffer through the fabric, which closes at 93 MHz and is far above the host's 400 kHz to 5 MHz.

**Never wire X3 pins 3 and 23 (2.5 V), 21 (5VIN) or 29 (the clock chip's OSC output).** Pin 1 is GND too, but it sits next to the 2.5 V on pin 3, so use pin 22.

The rest of the board: `clk_board` on P3 (LVDS, 100 MHz), `rst_n_btn` on T1 (the SW1 reset button), `ext_fs_sw_n` on H2 (SW3 position 1, ON at reset takes `clk_fs` from X3 pin 4), and `led_n[7:0]` on E16 D17 D18 E18 F17 F18 E17 F16, LEDs D25, D24, D22, D21, D26, D27, D28 and D29 for AUX_CTRL_0[0] to [7]. AUX_CTRL_0 resets to 0xFF00, so they are dark until a host writes it.

On the Versa the adapter's Pmod pin 6 net goes nowhere, so its jumper JP1 may be closed while the XIAO runs on USB: R1 and R2 then pull ss and rst_n up from the XIAO's own 3V3, and no second supply is involved.

The bench is the Arty's, [above](#bench-with-the-esp32-host-and-easyconfig), with the wires to X3 instead of the Pmod, SW3-1 OFF instead of SW0 off, and the scope on the X3 pins.

**On hardware, 2026-10-01**, `versa_duo` with the XIAO host on X3: programs 1 to 6 pass, 72 of 72 register transactions and every stimulus pattern bit-true on the model. A TEST_CTRL_1 write switches the bus to the DSA1 back end, where CHIP_ID reads 0x0000, and back to 0x0001, and AUX_CTRL_0 shows on the LEDs.
