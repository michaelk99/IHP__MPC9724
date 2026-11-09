<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# Bench host protocol

How a bench host drives this chip and reports back: the programs, the records, and what the chip requires of any host. The ULX3S master board of the two-board FPGA bring-up implements it, see [testbenches/fpga/README.md](../testbenches/fpga/README.md). [testbenches/fpga/seq/seqasm.py](../testbenches/fpga/seq/seqasm.py) writes the programs and [models/bench_capture.py](../models/bench_capture.py) checks the records, so the check that passes in simulation is the check that runs on the bench.

The silicon hosts and their PC tools are kept with the evaluation setup, outside this repo. They run the same programs and turn their answers into the same records for `bench_capture.check()`.

## What the chip requires of any host

- **sclk must run whenever conversions are read**, between transactions too, at least twice clk_fs, 131 kHz, about 200 kHz as designed. The register file is clocked by sclk alone and loads a new ADC word only on sclk rising edges while its synchronized ready flag is high, and `valid_strobe` is high for one clk_fs period, 15.26 us. Twice clk_fs puts two sclk edges into every flag, so the 3-flop synchronizer resolves before the load. A host that clocks only during a transaction misses the flag and every read returns a stale word. `make -C macros/dsa1_dig sim-cdc` shows the capture at every phase down to 1.05 times, where no flop goes metastable, and a run at 0.8 times losing words. An idle host may stop it: raise ss before sclk stops, so no frame is cut, and after sclk starts again wait for one conversion before reading ADC_DATA, which until then holds the word from before the stop, or a torn one if a flag was in the synchronizer when sclk stopped. On the ULX3S master this is `sclk_permanent_active`. A microcontroller's SPI peripheral usually stops the clock between transactions and cannot be used as it is.
- One transaction is 23 sclk periods with ss low: the read flag and 4 address bits, one dummy bit, 16 data bits, one dummy bit, most significant bit first. The slave samples mosi on the falling edge and drives miso on the rising edge. **A write shifts out the register's old value**, confirmed in the two-board simulation against all 78 transactions of program 1.
- On each adc_conv rising edge, read HIGH (address 0), then LOW (address 1), no earlier than a few sclk periods after the edge. LOW is frozen by the HIGH read, so the pair belongs to one conversion.
- If the host sources the bitstream: clk_fs at 65536 Hz, and data_in changing away from the clk_fs rising edge. Bit-true results do not care about the exact rate, a spectrum's frequency axis does.
- 3.3 V I/O, as the chip's pad ring.
- **`rst_n`** is held low until all supplies are up, and the board pulls it low while the host configures. There is no power-on reset. The decimator's reset is synchronous, so `clk` runs while `rst_n` is low, for several periods. With `DEC_SRC` on the oscillator the host first switches `clk` back to its own source, since the forwarded clock stops when `rst_n` clears bits 7 and 8.
- **dsm2 is on from reset.** `DSM_EN`, `DSM_RST_B` and `DSM_QOUT_EN` in `BIAS_CFG_1` are inverted at chip level: 0, the reset value, means dsm2 on, out of reset and its pads driving, 1 means off, held in reset and the pads low. With no SPI write dsm2 is enabled while `rst_n` is low and leaves reset 9 to 10 `clk` periods (137 to 153 us at 65536 Hz) after `rst_n` rises. Writing `DSM_RST_B` 1 holds it in reset at any time. After an SPI restart the host writes `DSM_EN` 0, waits at least 130 us, then writes `DSM_RST_B` 0, never both in one write.
- **dsm2's oscillator.** `dsm_clk` is an inout pad. The ring runs only with dsm2 on, its current comes from the bank that also feeds `ibias_test`, which then reads 0. Order: write `BIAS_CFG_1` with `DSM_EN` and `DSM_RST_B` 1 (dsm2 off and in reset), stop driving `dsm_clk` (high impedance), set `BIAS_CFG_0` bits 7 (`di_osc_en`) and 8 (`di_clk_sel`) in one write, then write `DSM_EN` 0, wait at least 200 us (dsm2 needs 130 us, the ring starts 20 to 131 us after `DSM_EN`), then `DSM_RST_B` 0. Bits 7 and 8 set with dsm2 off also avoid the bias kick of the oscillator bank, up to 37 % for up to 99 us. Change the trim or bits 7 and 8 only with dsm2 off. Bit 8 turns on dsm2's 4 mA driver whether bit 7 is set or not, and without bit 7 it drives the pad low, so bit 8 is set only with bit 7. The host drives `dsm_clk` again only after bit 8 is cleared. The ring runs at about 0.58 to 0.67 MHz at trim code 4 on the extracted view over corners. For 1.024 MHz, raise the trim with dsm2 off, from code 8 up until `dsm_clk` reads 1.024 MHz, about code 10 to 12. The trim moves dsm2's bias with it, 300 to 333 nA at codes 10 to 12. Code 15 reaches at least 1.05 MHz in every corner. The decimator keeps its clock from the `clk` pad, so with `DEC_SRC` the host forwards the inverted `dsm_clk` it now reads to `clk`.
- **Discard about 40 decimator words** after dsm2 leaves reset, after a `DEC_SRC` change and after a change of the `clk` source. While dsm2 is in reset its quantizer holds its output and the integrator saturates, it needs about 17 clocks to recover (dsm2 simulation at `vi` = +0.3 V, longer closer to full scale). The decimator holds about 32 words of history, so each of these events stays in the output for that long, 4 ms at 8 kHz.
- **TEST_CTRL_0** (address 9): every write keeps the `0x0500` base and bit 9 at 0, and never puts `11` in bits 7:6, which shorts the bias nodes. The core test mux, bits 5:0, never selects page `11`, which is undocumented, and on the INT page (bits 5:4 `01`) at most one of bits 3:0, or two integrator outputs are shorted. Between two selected nodes it goes through neutral, page `00` or the INT page with none selected, as `startup.md` requires.

## Programs

A program is a list of 32-bit words: op [31:28], addr [20:16], data [15:0]. A ROM image is 256 words. Words 0 to 15 are the start of programs 0 to 15, one per setting of the ULX3S master's DIP switches, and word 16 is a HALT that every unused number points at. The source is [testbenches/fpga/seq/programs.seq](../testbenches/fpga/seq/programs.seq).

| op | name | fields | the host |
|---|---|---|---|
| 0 | HALT | | sends END and stops |
| 1 | SPI | addr: read flag in bit 4, register in 3:0. data | runs one transaction, sends SPI with the word that came back |
| 2 | WAITC | data: n | waits for n adc_conv edges that arrive after the op starts |
| 3 | STREAM | | starts the bitstream at bit 0 one clk_fs period later, sends STREAM |
| 4 | CAPT | data: n, 0 is forever | on each of the next n adc_conv edges reads HIGH then LOW, sends ADC |
| 5 | LOOPBACK | data bit 0 | loops mosi to miso inside the host and holds ss high, sends LOOPBACK |
| 6 | RESET | | holds rst_n low, waits as long, sends RESET |
| 7 | REQUIRE | data: n | goes on if the last SPI transaction returned n, else sends END and stops |

| program | name | runs on |
|---|---|---|
| 0 | loopback | ULX3S master |
| 1 | registers: reset values, every writable register inverted, read back and restored, then the startup sequence | the DSA1 die only. It reads `CHIP_ID` and stops unless it is 0x0000 |
| 2 to 6 | on-chip stimulus: step +, impulse, half scale, step -, PRBS23 | every host |
| 7 | bitstream: the modulator record from BRAM, captured forever | ULX3S master. The ESP32 host plays the whole record from flash instead, with its own `P` command. |
| 8 | registers on this die: program 1 with `BIAS_CFG_0` and `BIAS_CFG_1` only read | this die only. It stops unless `CHIP_ID` is 0x0001 |

## The ULX3S master over UART

115200 8N1. A record is 63 bits, sent as nine bytes of 7 payload bits, most significant first. Only the first byte has bit 7 set, so a reader that joins late finds the next record without escaping.

| kind [62:60] | name | fields |
|---|---|---|
| 0 | SPI | addr [59:55], sent [54:39], received [38:23], pc [22:15] |
| 1 | ADC | HIGH [59:44], LOW [43:28], conversion [27:17], stream index [16:0] |
| 2 | START | program [59:56], 0xD5A1 [55:40] |
| 3 | RESET | pc [22:15] |
| 4 | LOOPBACK | pc [22:15], value [0] |
| 5 | STREAM | pc [22:15] |
| 7 | END | pc [22:15] |

conversion counts every adc_conv edge the host saw, modulo 2048, so a missed one shows as a gap. stream index is the bit of the window on data_in when the edge was seen, which lets the PC line the words up against the bit-true model.

## Bring-up order for the first chip

`BIAS_CFG_1` values below: `ADC_CONV_EN` 0x40, `DSM_QOUT_EN` 0x20, `DSM_VCM_EXT` 0x10, `DSM_BTEST_EN` 0x08, `DEC_SRC` 0x04, `DSM_RST_B` 0x02, `DSM_EN` 0x01. The reset value 0x0040 is dsm2 running with its pads, 0x0063 is dsm2 off, in reset and its pads low.

Board before power: pull-down on `rst_n`. Pull-down of 10 to 100 kOhm on `dsm_clk`, the host's `dsm_clk` pin through a series resistor of a few hundred Ohm. `vi` from a source at 0 V. `vcm` open or on a buffer of at least 10 GOhm. `ibias_test` on an SMU at 0.4 V. Ammeters in VDD, VDDA and IOVDD. Optional jumper `do_q` to `data_in`, a second path to decimate dsm2. Program 1 stops at its `CHIP_ID` check on this die, program 8 is its replacement.

1. Power up with `rst_n` held low and `dsm_clk` released: VDDA 1.5 V no later than VDD 1.2 V, then IOVDD 3.3 V. Watch `dsm_clk`, `do_q` and `do_q_b` on a scope through the ramp, no start-up run covers the inout pad in the wrong order. dsm2 is enabled from the first `rst_n` low, unclocked and in reset, about 26 uA on VDDA at tt. Record the static rail currents.
2. dsm2 without SPI: `vi` to VDDA/2 now that the supplies are up, `dsm_clk` at 1.024 MHz from the host, `clk` at 65536 Hz and a continuous `sclk`. Release `rst_n` after several `clk` periods. About 140 to 150 us later `do_q` and `do_q_b` toggle, complementary, about 50 % ones. `vcm` about 0.75 V, VDDA about 12.7 uA at tt. This step needs no SPI and is the fallback if the SPI fails.
3. SPI: read `CHIP_ID` (0x0001) and every register against this die's resets: `BIAS_CFG_0` 0x0024, `BIAS_CFG_1` 0x0040, `TEST_CTRL_0` 0x0500, `BLOCK_CTRL_1` 0x00FF. Program 8 does this and the inversion of every register that does not reach dsm2.
4. Digital alone: stimulus programs 2 to 6 with the 0x0500 base kept, then `data_in` from the host (program 7), discarding about 40 words. Then `BIAS_CFG_1` 0x0023 (dsm2 off, pads low, `adc_conv` still) for the VDD power state. Every wait on `adc_conv` gets a timeout.
5. dsm2 bias: `BIAS_CFG_1` 0x0063, then 0x006B (`DSM_BTEST_EN` while dsm2 is off, so the edge costs nothing), then 0x006A (dsm2 on, still in reset). After 230 us read `ibias_test`, about 194 nA at code 4 and tt. Back to 0x0063.
6. dsm2 on the external clock after an SPI restart: from 0x0063 write 0x0062, wait at least 130 us, then 0x0040. The VDDA current of dsm2 is the delta between 0x0063 and 0x0060 reached this way, with `dsm_clk` running, about 0.47 uA off and 12.7 uA running at tt. Sweep DC `vi`, capture `do_q` for the spectrum. Optional: `DSM_VCM_EXT` with 0.75 V from outside, dither on, trim sweep with dsm2 off at each step and the restart above.
7. Decimator on dsm2: `clk` as the inverted `dsm_clk` from the same host source, `BIAS_CFG_1` 0x0044 (`DEC_SRC`). Discard about 40 words, compare the SPI words with `do_q` captured at the same time and decimated by `models/decimator_model.py`. Then 0x0040 and `clk` back to 65536 Hz, and discard about 40 words again.
8. Oscillator: `BIAS_CFG_1` 0x0063. The host releases `dsm_clk`. `BIAS_CFG_0` 0x01A4 (bits 7 and 8 with trim 4). `BIAS_CFG_1` 0x0062, wait 200 us, then 0x0040. Count `dsm_clk`, expect 0.58 to 0.67 MHz at trim 4. `ibias_test` reads 0 now. Capture `do_q` against `dsm_clk`. For `DEC_SRC`, forward the inverted `dsm_clk` to `clk`, 0x0044, and discard about 40 words.
9. Leave the oscillator: switch `clk` to the host's own source, `BIAS_CFG_1` 0x0063, `BIAS_CFG_0` 0x0024, then the host drives `dsm_clk` again and restarts dsm2 as in step 6. Before any `rst_n`, `clk` must be on the host's own source.

## Safety

`seqasm.py` refuses to assemble a forbidden TEST_CTRL_0 value, and a program that switches the core test mux between two nodes without going through neutral. It also follows `BIAS_CFG_0` and `BIAS_CFG_1` from reset and refuses bit 8 without bit 7, a change of the trim or bits 7 and 8 while dsm2 is on, and a write that switches dsm2 on and releases its reset at once. A `require` for another `CHIP_ID` lifts these dsm2 rules for the rest of the program. Every host tool checks the static rules again on its side.

Program 1 writes the inverse of every bias, trim and clock register while the blocks are enabled. Against a chip with analog, the SG13G2 DSADC1, it needs the analog owner's OK first. On this die `BIAS_CFG_0` and `BIAS_CFG_1` drive dsm2, and program 1's values would turn on the `dsm_clk` driver against the host and restart dsm2 without its 130 us, so program 1 stops at its `CHIP_ID` check here and program 8 takes its place.
