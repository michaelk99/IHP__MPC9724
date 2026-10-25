<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
Description: the SystemVerilog sources of the DSADC1 decimation filter
-->

# Decimator RTL

The 128x decimation filter of the DSADC1 delta-sigma ADC. One bit in at
65536 Hz, one 22-bit word out at 512 Hz.

```
65536 Hz --CIC(N=6, D=32)--> 2048 --sinc2^9--> 1024 --sinc2^16--> 512 --comp9--> 512 Hz
```

These files are a frozen copy from the jku-phd development repo
(`circuit-level/hdl/DSADC1/DEC/decimator_v5/src`), one module per file. Both
macros in this repository read them: `macros/decimator` hardens the filter
alone, and `macros/dsa1_dig` reads the same six files rather than keeping a
second copy.

## Files

Listed in the order the Makefiles and the yosys pre-pass read them. The order
is fixed, not globbed: the pre-pass emits its netlist in source order and ABC
maps that order differently, which moves the mapped area by about 1 % with no
design change at all.

| File | Module | What it is |
|---|---|---|
| `ce_generator.sv` | `ce_generator` | one free-running 7-bit counter on `clk_fs` producing the three clock enables |
| `cic_n6_d32.sv` | `cic_n6_d32` | 6 integrators at the input rate, decimate by 32, 6 comb sections at the reduced rate |
| `sinc2_chain.sv` | `sinc2_chain` | M cascaded `1 + z^-1` sections, parameterised, used twice |
| `comp_fir.sv` | `comp_fir` | the 9-tap droop compensator, folded and time multiplexed onto one shift-add engine |
| `decimator_core.sv` | `decimator_core` | wires the chain together, does the scaling, rounding and output saturate |
| `decimator_top.sv` | `decimator_top` | the wrapper LibreLane hardens, and the design note |

## Word widths

| Parameter | Value | Why |
|---|---|---|
| `DATA_W` | 22 | output word |
| `CIC_W` | 32 | `N*log2(D) + 2`, the integrators are allowed to wrap inside this |
| `W` | 27 | datapath through the sinc chains and the compensator |
| `ALIGN_W` | 6 | shifts the CIC gain of `2^30` down to `2^(20+F)` |
| `RND_W` | 4 | `F`, fraction bits carried below the output LSB |

The widths come from the bit-true model's measured node peaks, not from a
growth bound. Each sinc section rounds one bit, which keeps every word at `W`.

**`W` is 27 and not 26 for a specific reason.** `FINAL_W = W - RND_W` is 23,
one bit above `DATA_W`, so the output saturate actually clamps. At `W` = 26 the
two were equal, the saturate was a no-op and an overshoot wrapped instead,
which matters because the compensator's gain at the band edge is about 4.4. The
extra bit costs roughly 5300 um2 of synthesised cells.

## Why the CIC is order 6, and why there is no half-band

The order is set by aliasing, not by quantisation noise. The image at
`fs/D - fb` folds onto `fb` at the CIC output rate, and every stage after the
first decimation has unity gain there, so alias rejection is the first stage's
job alone. Rejection improves by about 22.6 dB per CIC order at D = 32 and then
flattens at N = 6, where the `sinc2` stages take over.

That is also why this chain carries no half-band filter. A half-band's stopband
sits where the CIC has already put a null, so it would buy nothing here.

The predecessor decimated by 256 to 256 Hz with a 128 Hz band, which put the
band edge at `f_dec/2` and left a worst in-band alias of -6.3 dB. This chain
stops at 512 Hz, twice the Nyquist rate of the band, and measures -140.9 dB.

## Things that look wrong and are not

- **The CIC integrators wrap.** Modulo anything above the chain gain the comb
  output is still exact, which is Hogenauer's result. An arithmetic error only
  causes a finite transient.
- **The comb sections are combinational through the chain.** Each stage needs
  only its own delay register. Pipelining them costs `N` registers of `DATA_W`
  and buys nothing at 2048 Hz.
- **The compensator is idle most of the time.** It runs at 512 Hz with 128
  clocks per sample and needs 35 of them. Five parallel CSD multipliers were
  replaced by one shift-add engine walking five taps of six terms each, in the
  same order, with the same rounding. The arithmetic is identical, which is why
  the bit-true model did not change.
- **`data_out` is two's complement but declared unsigned.** OpenROAD's Verilog
  reader rejects `signed` on a top-level port.

## House rules for editing these files

- **No `` `default_nettype none ``.** It breaks ModelSim and `input logic`
  parsing, and that rule predates this repository.
- **Every file carries its own `` `timescale ``**, since compile order is no
  longer fixed by a single file.
- **No dynamic index on the left-hand side of a state write.** Genus prunes
  registers whose dataflow to an output passes through one, and no
  `dont_touch` prevents it.
- Every file must pass
  `verilator --lint-only -sv -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM`, and the set
  must elaborate under `iverilog -g2012`.
- **The proof of any change is `make sim-gl`, not the area.** The gate-level
  output has to equal the RTL sample for sample. Synthesis area in this flow
  moves about 1 % on statement order alone, so it cannot resolve a small
  change.

## Verification

`make sim-gl` in either macro runs one testbench on the RTL and on the
hardened netlist and requires the two output files to be identical: 500
samples for `decimator`, 284 observations for `dsa1_dig`. The testbench uses
no hierarchical reference, which is what lets the same file run against a flat
netlist.

The filter itself is checked against the bit-true MATLAB model in jku-phd,
where the RTL is bit exact over 32767 samples.
