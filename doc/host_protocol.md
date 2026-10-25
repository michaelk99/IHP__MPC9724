<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# Bench host protocol

How a bench host drives this chip and reports back: the programs, the records, and what the chip requires of any host. The ULX3S master board of the two-board FPGA bring-up implements it, see [testbenches/fpga/README.md](../testbenches/fpga/README.md). [testbenches/fpga/seq/seqasm.py](../testbenches/fpga/seq/seqasm.py) writes the programs and [models/bench_capture.py](../models/bench_capture.py) checks the records, so the check that passes in simulation is the check that runs on the bench.

The silicon hosts and their PC tools are kept with the evaluation setup in the IIC svn, `r_tapeouts/2024_DSADC/TO_IHPSG13G2/eval/dsa1`. They run the same programs and turn their answers into the same records for `bench_capture.check()`.

## What the chip requires of any host

- **sclk must run whenever conversions are read**, between transactions too, at least twice clk_fs, 131 kHz, about 200 kHz as designed. The register file is clocked by sclk alone and loads a new ADC word only on sclk rising edges while its synchronized ready flag is high, and `valid_strobe` is high for one clk_fs period, 15.26 us. Twice clk_fs puts two sclk edges into every flag, so the 3-flop synchronizer resolves before the load. A host that clocks only during a transaction misses the flag and every read returns a stale word. `make -C macros/dsa1_dig sim-cdc` shows the capture at every phase down to 1.05 times, where no flop goes metastable, and a run at 0.8 times losing words. An idle host may stop it: raise ss before sclk stops, so no frame is cut, and after sclk starts again wait for one conversion before reading ADC_DATA, which until then holds the word from before the stop, or a torn one if a flag was in the synchronizer when sclk stopped. On the ULX3S master this is `sclk_permanent_active`. A microcontroller's SPI peripheral usually stops the clock between transactions and cannot be used as it is.
- One transaction is 23 sclk periods with ss low: the read flag and 4 address bits, one dummy bit, 16 data bits, one dummy bit, most significant bit first. The slave samples mosi on the falling edge and drives miso on the rising edge. **A write shifts out the register's old value**, confirmed in the two-board simulation against all 78 transactions of program 1.
- On each adc_conv rising edge, read HIGH (address 0), then LOW (address 1), no earlier than a few sclk periods after the edge. LOW is frozen by the HIGH read, so the pair belongs to one conversion.
- If the host sources the bitstream: clk_fs at 65536 Hz, and data_in changing away from the clk_fs rising edge. Bit-true results do not care about the exact rate, a spectrum's frequency axis does.
- 3.3 V I/O, as the chip's pad ring.
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

| program | name | runs on |
|---|---|---|
| 0 | loopback | ULX3S master |
| 1 | registers: reset values, every writable register inverted, read back and restored, then the startup sequence | every host |
| 2 to 6 | on-chip stimulus: step +, impulse, half scale, step -, PRBS23 | every host |
| 7 | bitstream: the modulator record from BRAM, captured forever | ULX3S master. The ESP32 host plays the whole record from flash instead, with its own `P` command. |

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

## Safety

`seqasm.py` refuses to assemble a forbidden TEST_CTRL_0 value, and a program that switches the core test mux between two nodes without going through neutral. Every host tool checks the static rules again on its side.

Program 1 writes the inverse of every bias, trim and clock register while the blocks are enabled. Against a chip with analog, the SG13G2 DSADC1, it needs the analog owner's OK first. On the CMOS5L die nothing reads those bits.
