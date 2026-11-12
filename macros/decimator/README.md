<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# decimator_top

The 128x decimation filter of the DSADC1 back end, hardened on its own.

**This macro is not on the die.** The chip instantiates `../dsa1_dig`, which holds the same filter plus the SPI slave and the register file. This build gives the filter's own area, timing and leakage, and simulates the RTL without the SPI wrapper.

| | |
|---|---|
| Top cell | `decimator_top` |
| Standard cells | EZ130 8T, read from `EZ130_DIR` |
| Decoupling | `DECAPHV8/16/32` only, from `DECAPHV_DIR` |
| Die | 487.20 um square |
| Clock | `clk_fs` 65536 Hz |

## The filter

```
65536 Hz --CIC(N=6, D=32)--> 2048 --sinc2^9--> 1024 --sinc2^16--> 512 --comp--> 512 Hz
```

One bit in, 22 bits out at `fs`/128. The compensator is a 9-tap symmetric FIR, folded and time multiplexed onto a single shift-add engine. Why the CIC is order 6 and the chain has no half-band: [rtl/README.md](rtl/README.md).

`rtl/` is a frozen copy from the private RTL repository (`circuit-level/hdl/DSADC1/DEC/decimator_v5/src`), one module per file. The `dsa1_dig` macro reads these same files.

## Building it

```sh
make rtl-gen        # the yosys clock-gate pre-pass
make librelane      # harden
make build-top      # harden, collect views and reports, render
make sim-gl         # the gate-level netlist must equal the RTL, sample for sample
make model-gate     # and both must equal the bit-true model in ../../models
make check-netlist  # no cell that is wrong in silicon reached the netlist
```

`sim-gl` shows the netlist equals the RTL, which it would even if both were wrong, since they share a source. `model-gate` is the correctness check: it reproduces the Verilog testbench stimulus in Python, runs `models/decimator_model.py` on it and requires all 500 samples to match. `make sim-rtl-cocotb` and `make sim-gl-cocotb` compare against the same model at every `valid_strobe`.

`EZ130_DIR` and `DECAPHV_DIR` default to `ip/ez130_8t_v1p1` and `ip/ez130_8t_decap_hv`.

## Results

LibreLane run of 2026-09-22, container `2026.08`, EZ130 8T, thick-oxide decoupling. Every signoff check is zero: router DRC, Magic DRC, KLayout DRC, netgen LVS, antenna nets and antenna pins.

| | CMOS5L | SG13G2, for reference |
|---|---|---|
| Functional cells | 120807 um2 | 120337 um2 |
| of which flops | 1487 | 1487 |
| Die | 487.20 um square | 487.20 um square |
| Setup worst slack | +491.03 ns | +491.4 ns |
| Hold worst slack | +0.035 ns | +0.071 ns |
| Max-slew, slow corner | 51 | 27 |
| Decoupling | 3465 DECAPHV | |
| Metal fill | M1/M2/M3/M4 at 29.6 / 24.3 / 19.5 / 58.6 % | |
| Power at typical, `make power-vcd` | 2.213 uW | 2.33 uW |
| `sim-gl` | 500 samples identical to RTL | |
| `model-gate` | 500 of 500 match the bit-true model, RTL and gate level | |
| cocotb | 4 of 4 pass, RTL and gate level | |

Losing Metal5 and TopMetal2 costs 0.4 % of cell area. The slew count roughly doubles because one fewer routing layer makes nets longer.

The router needed two passes: antenna diode insertion pushed it back up from zero, and it reached zero again. No cell padding was required, unlike `dsa1_dig`.

## Open

- `DIE_AREA` is still the SG13G2 number. From the run's metrics the core is 219628 um2 against 120807 um2 of functional cells, so utilisation is **55.0 %** and filler is 98821 um2. `dsa1_dig_top` sits at 68.9 % on the same flow, run of 2026-10-31. At a 65 % target this block would fit a die of roughly 445 um square instead of 487.20.

  Not acted on: re-hardening discards the metal fill and reopens `sim-gl`, `model-gate` and the DRC and LVS runs, for a macro that is not on this chip. Do it when the block is placed on a die where the area matters.
