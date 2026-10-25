<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# AGENTS.md

Guidance for a coding agent working in this repository.

## What this is

The tapeout repo for the DSADC1 digital back end on IHP SG13CMOS5L: a 1.6 mm QFN32 die carrying one macro, `dsa1_dig_top`, which is the 128x decimation filter, the SPI slave and the configuration register file. Built from the `iic-jku/ihp-sg13cmos5l-ams-chip-template`, whose history this repo adopted outright, so `git remote template` can still compute a sync range.

**The RTL development repo is `../jku-phd`.** It is the source of truth for the VHDL and the decimator SystemVerilog. This repo owns a frozen copy under `macros/*/rtl/`. Change the RTL there, prove it there, then mirror. The two copies differ only by SPDX headers and the `dsa1_dig_top_v2` to `dsa1_dig_top` entity rename.

Write prose in the house style of `../jku-phd/CLAUDE.local.md`: no em-dashes, no semicolons outside code, no hard wrapping, short comments, plain colleague tone.

## Running anything

Every target runs inside the IIC-OSIC-TOOLS container. `/home/koefinger/projects` is mounted at `/foss/designs`, so this repo is `/foss/designs/sg13cmos5l_dsa1_dig`.

```sh
docker exec iic-osic-tools_xserver_uid_1000 bash -lc '
  cd /foss/designs/sg13cmos5l_dsa1_dig
  export PDK=ihp-sg13cmos5l PDKPATH=/foss/pdks/ihp-sg13cmos5l PDK_ROOT=/foss/pdks
  export STD_CELL_LIBRARY=sg13cmos5l_stdcell SCL=sg13cmos5l_stdcell
  export EZ130_DIR=/foss/designs/OpenBLAU/ip/ez130_8t_v1p1
  export DECAPHV_DIR=/foss/designs/OpenBLAU/ip/ez130_8t_decap_hv
  make <target>'
```

**All five exports matter.** A parse-time guard in each `Makefile` catches a wrong `PDK`, but `STD_CELL_LIBRARY` is only set by `sak-pdk` in an interactive shell, and without it LibreLane dies looking for `sg13g2_stdcell/config.tcl` under the CMOS5L PDK. `EZ130_DIR` and `DECAPHV_DIR` point outside the repo on purpose: EZ130 8T is a prerelease and must not ship here.

A full macro or chip harden is 30 to 60 minutes. Run it in the background.

## The gates, and what each one proves

| target | proves |
|---|---|
| `make -C macros/<m> sim-gl` | the hardened netlist is the RTL |
| `make -C macros/<m> model-gate` | the RTL is the design, against `models/` |
| `make -C macros/dsa1_dig sim-cdc` | the ready flag and the stimulus bits cross between clk and sclk at every phase, sclk 1.05 to 12.7 times clk, and a 0.8 control run is caught |
| `make -C macros/<m> check-netlist` | no cell that is wrong in silicon got in |
| `make -C macros/dsa1_dig lec`, `lec-fail` | the hardened netlist is the RTL for every input sequence, and the check can fail |
| `make -C macros/dsa1_dig regmap-check` | every file made from `regmap.yaml` is current |
| `make klayout-drc-regular`, `magic-drc` | geometry |
| netgen LVS, in the flow | layout against the synthesized netlist |
| `make sim-rtl-cocotb`, `sim-gl-cocotb` | pad mapping and the bitstream synchronizer |

`sim-gl` and `model-gate` are not interchangeable. The first compares two things that share a source and would agree if both were wrong. `models/` is the independent description. See `../jku-phd/SKILLS/bit-true-model-gate/`.

## Traps that have already cost time

- **The chip cocotb bench reads the macro as a hard block.** The macro's RTL is VHDL and Icarus cannot read it, so both the RTL and GL flavours compile the macro's *gate-level netlist*. After any macro RTL change, chip-level tests exercise the previous netlist until the macro is re-hardened. Failures then look like a broken design.
- **The FPGA master board reads `dsa1_ic_bus_master.vhd` from `JKU_PHD_DIR`.** Never copy it or commit its ghdl output, it carries no license here. Both stay in `testbenches/fpga/build/`.
- **`sim-gl` compares two files.** Update the Verilog testbench before rebuilding the netlist, or the check passes against a stale reference.
- **Metal fill lives in the GDS**, so every re-harden destroys it. Re-run `macros/scripts/fill_macro.sh` before rebuilding the chip.
- **Density has its own report.** The merged `*_full.lyrdb` never mentions `M<n>.j`, `M<n>.k` or `M<n>Fil.h`. Read `verification/drc/*/*_density.log`. Global Metal4 runs with under three points of headroom under the 60 % maximum, and the chip DRC is expected to show **exactly 78 items**: 40 `Pad.d1R`, 38 `Pad.fR_TM1`.
- **`sak-drc.sh` takes the top cell name from the file name.** A wrongly named GDS fails with a KLayout traceback that reads like a deck problem.
- **Chip STA times the macro's inside.** `STA_MACRO_PRIORITIZE_NL` reads the macro's gate netlist, so `flow/librelane/sg13cmos5l_dsa1_dig_top.sdc` carries the macro's own clocks: `clk` at 1000 ns, `sclk` at 100 ns, asynchronous to each other. While the core rows were PDK cells, no loaded liberty knew the macro's EZ130 cells, and the chip's clean timing covered only the pads. Check `check_setup` in the STA report: 0 unclocked register pins.
- **KLayout 0.30.11 can segfault in the multithreaded regular deck.** `drc_verdict.py` then reports a table that stopped early. Rerun it, the crash is not the layout.
- **Top-level LVS against the drawn schematic is not a gate here.** `layout=277536 schematic=5`. netgen against the synthesized netlist is the real check and it passes. See `testbenches/README.md`.

## Layout of the repo

- `macros/dsa1_dig/` the one macro on the die. `macros/decimator/` the same filter standalone, for area and power numbers, **not** on the chip. `macros/counter/`, `macros/inverter/` are the template's archetypes for `make macro`.
- `models/` the bit-true decimator model, the stimulus patterns and the two gate scripts.
- `rtl/` the chip core and padframe, SystemVerilog, hardened on the PDK cells. EZ130 reaches the chip only inside the macro.
- `schematic/xschem/sg13cmos5l_dsa1_dig_top.sch` is **generated** by `make schematic` from the pad plan. Do not hand edit it.
- `doc/` specifications, pinout, floorplan, rtl2gds. `doc/rtl2gds.md` explains how to read each sign-off verdict. `doc/host_protocol.md` is the bench host protocol.
- `testbenches/fpga/` the master board of the two-board FPGA bring-up and its simulation against the DUT board. The silicon hosts and their GUI live in the IIC svn, `r_tapeouts/2024_DSADC/TO_IHPSG13G2/eval/dsa1`, never here.

## Register map note

The register map is `macros/dsa1_dig/regmap.yaml`, the only place it is written. `make -C macros/dsa1_dig regmap` writes `rtl/dsa1_regs.vhd` and `.vh`, `sw/dsa1_regs.h`, `models/regmap_defs.py` and `doc/regmap.md` from it. Never edit those by hand: `regmap-check` fails on a stale one, and CI runs it. The SPI frame is not in the YAML, it is the taped-out DSA1 die's and every host's.

`TEST_CTRL_0` at address 9, reset `0x0500`. Bits 15:11 are the decimator stimulus generator, 10 is the ADC flag sync and 8 is PAD_Q, both reset 1, so **every write to this register has to keep the `0x0500` base**. Bit 9 belongs to the analog top and must not be written from here. The bit-7:6 code `11` is a documented hazard that shorts bias nodes; never write it.

`TEST_CTRL_1` at 13 is plain storage on the die, the FPGA harness decodes writes to it from the bus: bit 0 takes `clk_fs` from the pin, bit 1 the duo bus to the DSA1 back end. `CHIP_ID` at 15 is read only, `0x0001` for this chip. The DSA1 die has plain storage there that resets to `0x0000`, so never write 15 on either die. Program 1 leaves both alone.
