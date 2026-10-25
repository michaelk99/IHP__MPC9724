<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# Plan

What is left between here and handing this chip to a foundry, and in what order.

## Where it stands

The chip is functionally complete and signed off as the digital-only fallback, v1.1.0, on branch `tapeout/v1.1.0`. The record is [doc/signoff.md](doc/signoff.md), the release in [release/v.1.1.0](release/v.1.1.0).

| | |
|---|---|
| Die, package | 1.6 mm square, QFN32, 32 pads, bond plan generated |
| Macro | 137733 um2, 1846 flops, +44.27 ns setup, +0.074 ns hold |
| Power, leakage | 3.061 uW typical, 1.171 uW transistor level against 1.208 from STA |
| DRC | chip at the 78 known non-defects, Magic clean, density all in range |
| LVS | netgen, circuits match uniquely, macro and chip from the DEF, and the chip from its GDS with the macro and every standard cell device by device (`verification/lvs/top_lvs.sh`) |
| Function | `lec` 1325 of 1325 partitions, `sim-gl` 1343 identical, `model-gate` 8 of 8 stimulus modes both levels, `sim-cdc` every word right from sclk 1.05 to 12.7 times clk, chip cocotb 7 of 7 |
| FPGA | both back ends on the Arty A7 booted from flash, 15 of 15 and 6 of 6 bench tests on 2026-10-02 |
| Start-up | IO cells as transistors, core as XSPICE, both supply orders: VDD must come first (`testbenches/startup/`) |
| EM, precheck | current density ratio 0.312 of 0.5 at most, IHP precheck 0 markers |

Settled, and not to be reopened without new information:

- **Transistor-level LVS against a drawn schematic is not achievable on this PDK.** A full run reports `layout=277536 schematic=5`. netgen against the synthesized netlist is the real check and it passes. See [testbenches/README.md](testbenches/README.md).
- **The die is core-limited, not pad-limited**, so cutting pins does not shrink it. The analysis is in [doc/floorplan.md](doc/floorplan.md).
- **The decimator macro's `DIE_AREA` is oversized** at 55 % utilisation, and it is not on the chip, so it does not matter.

## 1. FPGA bring-up, two boards

**Status, 2026-09-23:** built and simulated. The master board (second ULX3S) and the DUT board run together in Icarus, and all eight programs pass `models/bench_capture.py`: the loopback, 78 of 78 register transactions, the five on-chip stimulus patterns against `models/stimulus.py`, and program 7, whose 48 words match `models/decimator_model.py` bit for bit at lag 3. A DUT on its own clock is caught. Nothing has run on hardware. Steps 1 to 5 of 1c are now a procedure in [testbenches/fpga/README.md](testbenches/fpga/README.md), and the rest of this section is the design record.

The highest-value item: the only thing that would exercise this design outside a simulator, and almost everything it needs already exists.

**Two boards, not one board and a host adapter.** The second board runs the real SPI master, so the interface is proved at pin level with real timing rather than bit-banged by a script. That is much closer to the bench scenario the chip will actually meet.

```
   MASTER board                          DUT board
   ------------                          ---------
   dsa1_ic_bus_master  --- sclk  ------>  sclk
                       --- mosi  ------>  mosi
                       <-- miso  -------  miso
                       --- ss    ------>  ss
   bitstream source    --- data_in ---->  data_in_pin
   clock generator     --- clk_fs  ---->  clk_board / clk_fs
                       <-- adc_conv ----  adc_conv_pin
   UART to host
```

### 1a. The master board

**Use `../jku-phd/circuit-level/hdl/DSADC1/SPI/src/dsa1_ic_bus_master.vhd`.** It is the master this chip was designed against, it already faces the chip's pins, and the startup sequence in `../jku-phd/circuit-level/hdl/DSADC1/DIG_TOP/sim/startup.md` is written for it. Do not write a new one.

Its interface, for reference:

| | |
|---|---|
| generics | `RESET_ACTIVE='0'`, `DATA_MSB=15`, `ADDR_MSB=4`, `DUMMY_NR=1`, `HALF_CLK_PERIOD_INDEX` |
| to the DUT | `sclk`, `mosi`, `miso`, `ss` |
| command | `addr_to_be_sent`, `data_to_be_sent`, `start_comm` |
| result | `data_received`, `data_received_strobe`, `transmit_flag` |
| system | `clk`, `rst` (active low by default) |

Three things to get right:

- **`HALF_CLK_PERIOD_INDEX` is derived from the board clock**, not copied. 250 gives 200 kHz from 100 MHz. On a 25 MHz ULX3S it is 62, giving 201.6 kHz. Any value is fine as long as sclk stays well above the 65536 Hz sample clock, because the register file only captures a new ADC word on sclk edges while the synchronized ready flag is high.
- **Hold `sclk_permanent_active` high.** Same reason. A master that only clocks during a transaction will read stale ADC words.
- Yosys does not read VHDL, so the master goes through `ghdl synth` exactly as `dsa1_dig_top` does on the DUT side. Reuse the `rtl_gen` pattern from `macros/dsa1_dig/Makefile`.

Around the master, the board needs:

- **A sequencer.** A ROM of (address, data) pairs plus a small state machine driving `start_comm`. First the bring-up writes from `startup.md`, then the stimulus arm and fire values. Keeping it a ROM rather than hand-coded states means the same table can be diffed against the documented sequence.
- **A bitstream source** for `data_in`. A window of the modulator record in BRAM is enough and makes the result bit-true comparable: 1024 output samples is 131072 input bits, 16 kB, against 3.7 Mbit of BRAM on an ECP5-85F. The full 4.19 M-sample record does not fit and is not needed, because 42 Hz is coherent in any multiple of 256 at the 512 Hz output rate.
- **A capture path.** Read HIGH then LOW on every `adc_conv` and ship the pair to a host over UART. 512 words per second at 3 bytes is 12.3 kbit/s, so 115200 baud is ample. A minimal 8N1 transmitter is about 50 lines.

### 1b. Who owns the clock

**The master board should generate `clk_fs` and drive it to the DUT**, with `data_in` alongside it. That is the chip's real situation: the clock and the bitstream both arrive from outside, and the master board is standing in for the rest of the ADC.

This is a change to the DUT harness, which currently makes its own 65536 Hz from the board oscillator with a phase accumulator. Add a mode where `clk_fs` comes from a pin instead. Keep the accumulator path, it is what lets the DUT board run standalone for the on-chip stimulus patterns, which need no external bitstream at all.

### 1c. Order of bring-up

Go in this order. Each step needs only the ones before it.

1. **DUT board alone, on-chip stimulus.** No bitstream source, no clock wire, nothing from the master. Drive `TEST_CTRL_0` from any host adapter, arm, wait about 20 conversions, fire, read HIGH then LOW. `models/stimulus.py` predicts all five patterns exactly, so this is a bit-true check on the first day.
2. **Master board alone, loopback.** Prove the master, the sequencer and the UART against a stub that echoes a known pattern, before either board depends on the other.
3. **Both boards, register access.** Write `o_tst_ctrl` and read it back. `o_tst_ctrl[6:0]` is on the DUT board's LEDs, so the write path is visible before any read is trusted.
4. **Both boards, on-chip stimulus** driven by the master's sequencer, compared against `models/stimulus.py`.
5. **Both boards, real bitstream** from BRAM, compared against `models/decimator_model.py`.

Expect the first failure to be pin assignment or SPI polarity, not the filter. Step 3 exists to separate those from everything else.

### 1d. Where it lives

The DUT harness stays in `macros/dsa1_dig/fpga/`. The master is a bench, not part of the design, so it belongs in `testbenches/fpga/`, together with the wiring diagram, the pin map for both boards and the bring-up procedure. The host-side capture script goes next to the models it compares against.

## 2. Tapeout deliverables

Nothing here is hard, and all of it is easy to get wrong at the last minute.

Done for v1.1.0 on 2026-10-06 and for v1.1.1, which adds a vdd-to-vss ESD clamp cell, on 2026-10-09, see [doc/signoff.md](doc/signoff.md). Instead of a clean rebuild, every check ran on the exact delivery GDS, and XORs tie it to the hardened macro and the chip run, which keeps the LEC verdict valid. On submission day `scripts/submission.sh <IHP project name>` copies the GDS to its new name, requires the signed-off md5 and one top cell, and runs IHP's precheck deck and the GDS-level LVS on that file.

Open items from the audit of 2026-10-06 at 31ecf8c. Each row's own document is authoritative.

Before submission:
- **Cell names over 32 characters**, 16, the top cell `sg13cmos5l_dsa1_dig_top_logo_fill` (33) and the clamp cell's via cells among them, the rest via cells. The GDSII format allows 32, most tools read more, and what IHP's intake accepts is not known. Ask IHP, or rename the top cell (`scripts/rename_top_cell.py`), which changes the md5 and means the checks again.
- **STA at nominal RC only.** `flow/librelane/config.yaml` lists only `nom_*` SPEF, so the three corners are PVT at nominal parasitics, and the hold slack of +0.074 ns at the fast corner has no min RC case. Run min and max RC, or accept it in the sign-off record.
- Tag the release commit and push the branch.
- **The macro's 327 Magic DRC items** (164 overlap, 163 `M4.d`) in the chip-level run, which IHP's KLayout decks do not report and LibreLane's Magic DRC of the macro alone does not either (`macros/dsa1_dig/verification/drc.magic.rpt`, 0).

After submission, or for the next revision:
- The IO liberty, LEF and Verilog are the template's snapshot in `ip/sg13cmos5l_io_custom` (liberty rev 0.0.1, 2024), and nothing compares them with the PDK. The 18 pad slew items rest on them.
- The chip-level glue (3 DFFRQX3, 1 INVX1, 17 BUFX12, 4 TIELO) has no formal check of its own, only gate-level cocotb and both LVS runs.
- `make regression` runs the template's inverter and counter, not this chip.
- `flow/librelane/config.yaml` lines 41 and 44 keep the template's TODOs on fill, which `scripts/add_logo_fill.sh` does.
- Stale numbers in the docs: decap count and on-die decoupling (`doc/floorplan.md`, `doc/specifications.md`, `macros/dsa1_dig/README.md` say 2344 cells and 35 pF, the macro has 2260 and the core rows 14749 more), leakage 1.157 against 1.171 uW, sim-gl 527 against 1343 observations, `power__total` 1.68 against 1.12 mW, "nothing has run on hardware" in the macro and FPGA READMEs, the synchronizer cell in `testbenches/README.md`, EZ130 only inside the macro in `AGENTS.md`, and the doc indexes in `README.md` and `doc/README.md`, which miss `signoff.md`, `regmap.md` and the release. Several docs are hard-wrapped.

## 3. The Xschem transient bench

The last thing in the repo that still describes the template. The DUT symbol underneath it is correct now, so this is a stimulus rewrite, not a rebuild: `testbenches/xschem/sg13cmos5l_dsa1_dig_top_tb_tran.sch` and `plot_simulations/plot_sg13cmos5l_dsa1_dig_top.py` still drive counters.

The supply start-up transient it was meant for is done in a small dedicated bench instead, [testbenches/startup](testbenches/startup/README.md), so this bench only documents. It found that the board must bring VDD up no later than IOVDD.

## 4. Only if area becomes a goal

[doc/floorplan.md](doc/floorplan.md) has the analysis: about 1.12 mm die in a QFN24, roughly half the area, taken out of the 365 um padframe margin and the loose core rather than the pin list. Two things to check first, neither done: whether the IO power ring and the pad-to-core routing fit a narrower channel, and what the reduced on-die decoupling does to the numbers in the decoupling section of that document.

Do not start this speculatively. It invalidates the bond plan, the pinout and every layout number in the documentation.

## 5. Hosts on silicon

Decided on 2026-09-23. Before silicon, the ULX3S master of section 1 drives the DUT FPGA board. On silicon, two hosts must both work: the existing Arty A7-35 over Ethernet and an ESP32-S3 over WiFi on the eval PCB. They, their GUI and their PC tools are kept with the evaluation setup in the IIC svn, `r_tapeouts/2024_DSADC/TO_IHPSG13G2/eval/dsa1`, and run the programs of [testbenches/fpga](testbenches/fpga/README.md) through the same checks. The chip's requirements of any host are in [doc/host_protocol.md](doc/host_protocol.md), the continuous sclk first.

The ESP32 host passes against the DUT FPGA board on the Arty A7 and the Versa ([macros/dsa1_dig/fpga/README.md](macros/dsa1_dig/fpga/README.md), [doc/signoff.md](doc/signoff.md)). Open: the Arty over Ethernet, whose state the repo does not record, and the ULX3S master of section 1, which has not run on hardware.

## Standing traps

All of these have cost time once already. They are also in [AGENTS.md](AGENTS.md).

- The chip cocotb bench reads the macro as a **hard block**, so after any macro RTL change it silently tests the previous netlist until the macro is re-hardened.
- Metal fill lives in the GDS and every re-harden destroys it.
- Density has its own log. The merged DRC report never mentions it, and global Metal4 has under three points of headroom under the 60 % maximum.
- `sim-gl` compares two files, so the testbench has to be updated before the netlist is rebuilt.
- Chip STA reads the macro's gate netlist, so the chip SDC must carry the macro's clocks, or the macro's inside is timed at the wrong period or not at all.
- Five environment variables, not two, or LibreLane hardens against the wrong library or refuses to start.
