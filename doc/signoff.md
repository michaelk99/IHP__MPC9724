# Sign-off record, v1.1.1

The digital-only DSA1 back end, `sg13cmos5l_dsa1_dig_top`, as the fallback tapeout should the analog macros not be ready. Branch `tapeout/v1.1.1`, signed off on 2026-10-09. It is v1.1.0 (`tapeout/v1.1.0`, signed off 2026-10-06) with one change to the layout: a vdd-to-vss ESD clamp cell, `ip/sg13cmos5l_ip__clamp_vddvss`, between the VSS and the VDD pad, because the IHP IO library has none and the HBM check put 8.4 V across the core rail without it. The macro is the same hardened one, and the register map comes from one YAML (`macros/dsa1_dig/regmap.yaml`), which every later revision keeps.

The tools and their versions are in [verification/signoff_env.txt](../verification/signoff_env.txt).

## What is delivered

| file | md5 | from |
|---|---|---|
| `layout/sg13cmos5l_dsa1_dig_top_logo_fill.gds.gz`, the delivery GDS | `f61eb35a093f9cad83ac9d3ad3fcbdb6` | chip build d218814, logo and fill added |
| `layout/sg13cmos5l_dsa1_dig_top.gds.gz`, the same without fill | `3c136e848ce67988e27ee3f9d3403f09` | chip run `RUN_2026-10-08_01-11-22` |
| `macros/dsa1_dig/final/gds/dsa1_dig_top.gds`, the macro | `b00066a56d0018cfd18d7acab568597b` | macro run `RUN_2026-09-30_13-54-33`, 9031d16 |

The delivery GDS keeps its design name until IHP assigns the project name. Then `scripts/submission.sh <name>` copies it to that name, requires this md5, and runs IHP's precheck deck and the LVS on that file.

## Provenance

The checks below ran on the files above, not on a rebuild. Their geometry ties them together (KLayout XOR, every layer):

| compared | layers | differ |
|---|---|---|
| macro cell inside the delivery GDS against the macro's final GDS | all | 0 |
| unfilled layout against the chip run's final GDS | all | 0 |
| delivery GDS against the unfilled layout | all | 8: fill on 1/22, 5/22, 8/22, 10/22, 30/22, 50/22, 126/22, and one boundary shape on 189/0 |

The macro being identical keeps its LEC verdict and its own checks valid.

## Checks

| check | on | result | record |
|---|---|---|---|
| IHP MPW precheck, minimum DRC | delivery GDS | 0 markers in 28 tables | `verification/drc/precheck/` |
| IHP's own precheck deck, `run_drc.py --precheck_drc` | a renamed copy of the delivery GDS, top cell named, `scripts/submission.sh` dry run 2026-10-09 | 0 markers in 73 rule categories, density in range | rerun on submission day into `verification/submission/` |
| Shape scan | delivery GDS | 0 degenerate, prBoundary 1600 x 1600 um, 16 cell names over 32 characters | `make gds-scan` |
| KLayout regular DRC | delivery GDS | 69, all `Pad.d1R` (31) and `Pad.fR_TM1` (38), the recommended bondpad rules of the library bondpad, every one on a bondpad or in the bondpad cell. 33 of 33 rule tables completed. The clamp cell alone and abutted between IOPadVss and IOPadVdd adds no marker (`ip/sg13cmos5l_ip__clamp_vddvss`) | `verification/drc/sg13cmos5l_dsa1_dig_top_logo_fill.klayout.drc/verdict.txt` |
| Density | delivery GDS | all in range, Metal4 57.40 % of 60 % the closest | same verdict |
| Magic DRC, `drc(full)` | delivery GDS and unfilled | 9098 and 9710 items in 7 rules, none in the clamp cell, the same rules and nearly the same counts as v1.1.0's layout (9754), see below | `verification/drc/*.magic.drc/` |
| Fill isolation | delivery GDS | the fill joins no two drawn shapes, touches no via, crosses no drawn active or poly, and a mutant fails | `verification/lvs/fill_isolation.txt` |
| Top LVS from the GDS, the macro, every standard cell and the clamp cell device by device, IO cells by pins | unfilled GDS | `Circuits match uniquely`, no property error. A reference with two gate inputs swapped fails, and one with the clamp at 1512 instead of 2268 um fails on its property error | `verification/lvs/sg13cmos5l_dsa1_dig_top.gds.lvs/lvs.rpt`, method in `verification/lvs/README.md` |
| The same top LVS on the delivery GDS itself, the wrapper with the chip flattened into it next to its fill | the renamed copy of the dry run | `Circuits match uniquely`, the fill cells ignored as FILLER is | rerun on submission day |
| LibreLane LVS, from the DEF, cells and macro by pins | chip run | `Circuits match uniquely` | `verification/reports/lvs.netgen.rpt` |
| Macro netlist against RTL, EQY | `final/nl` | 1325 of 1325 partitions, a mutant fails | `macros/dsa1_dig/verification/lec_verdict.json` |
| STA, 3 corners | chip | setup +44.26 ns, hold +0.074 ns (fast corner) | `verification/reports/stapostpnr_summary.rpt` |
| Antenna | chip | 0 nets, 0 pins | `verification/reports/antenna_summary.rpt` |
| Banned cells | chip netlist | none | `make check-netlist` |
| Current density | final DEF of the chip run and of the macro run above | worst ratio 0.312 of 0.5, VDD through a 2-cut Via1 at 0.25 mA, the STA's vectorless 0.236 mA at the fast corner rounded up and about 80 times the typical draw (`EM_CURRENTS` in the Makefile) | `verification/em/em_table.md`, `macros/dsa1_dig/verification/em_table.md` |
| Supply start-up, both orders | IO cells and the clamp cell as transistors, core as XSPICE | VDD first: all reads right, bits 7:6 never high together, no current above 10 mA for longer than 1 ns. IOVDD first: see below | `verification/startup/startup_report.md`, `testbenches/startup/` |
| Ground bounce | the same, VDD first, with the package: bond wires from `packaging/result.md`, VSS and IOVSS on the paddle | TEST_CTRL_0 0x0500 to 0xFDAF and back, 11 of the 16 test pads switching together through the one IOVDD and one IOVSS pad: reads and pad levels right, no core input glitch. On the die IOVDD to IOVSS moves up to 0.43 V for about 3 ns, IOVSS 0.27 V against the board, quiet pins up to 0.33 V, static core inputs up to 76 mV. The core draws no current in this bench | `verification/startup/bounce.png`, same report |
| HBM ESD, 2 kV, JS-001 pin matrix both polarities | the extracted pad ring with the clamp cell, IO cells and clamp as transistors, the core's 750 pF decap | every pairing has a discharge path (292 die only, 230 with VSS and IOVSS one pin), a check without the IOPadIOVdd cell fails. No 1.2 V node over the indicative 4.5 V at any diode RON: the core rail peaks at 3.58 V (VDD + vs VSS), 3.44 V with the package short, where v1.1.0 had 8.4 and 7.3 V. HV under 10 V up to RON 1, 10.04 V at RON 2, up to 11.2 V at RON 4 | [doc/esd_hbm.md](esd_hbm.md), `verification/esd/` |
| Bond plan | delivery GDS in QFN32 | 34 wires: 30 pad to lead, 1289 to 1701 um, VSS and IOVSS through the cavity (2 pad downbonds, leads 5 and 7 to the paddle), 60 um minimum gap, 5.8 deg maximum skew, no crossing. The west pads sit at 100 um pitch with the clamp cell between VSS and VDD | `packaging/result.md` |
| Clamp cell | `ip/sg13cmos5l_ip__clamp_vddvss` alone | KLayout and Magic DRC clean, LVS against its CDL, a connectivity probe of every stripe and band, and a clamp bench: 26.9 pA at 27 C and 20.1 nA at 125 C, on 1.6 ns after a 10 ns vdd edge, gate at 0.08 V on the board's 100 us ramp. Every check fails on a broken input | `ip/sg13cmos5l_ip__clamp_vddvss/README.md` |

Simulation and hardware, on the same macro: `sim-gl` 1343 identical, `model-gate` 8 of 8 stimulus modes at RTL and gate level, `sim-cdc` every word right from sclk 1.05 to 12.7 times clk (at 9031d16). Chip cocotb 7 of 7 at RTL and gate level on the v1.1.1 netlist, the PSD test opt-in. On the Arty A7, both back ends behind one bus, booted from flash: 15 of 15 bench tests on this chip's and 6 of 6 on the DSA1 die's, 2026-10-02, kept in the IIC svn at r1936 (`eval/dsa1/signoff/`).

## Known and accepted

- **69 KLayout items**, the recommended bondpad rules on the library bondpad, all on the bondpads. `Pad.fR_TM1` once per pad and four times on the VDD and IOVDD pads, `Pad.d1R` on 25 pads, three times on the first pad of three sides, and once inside the bondpad cell.
- **Magic DRC items, all in library cells, the seal ring and the macro, and on v1.1.0's layout too.** Until 2026-10-08 the Makefile ran Magic with `gds flatglob *`, which made it check an empty cell and report `COUNT: 0` on any layout, so v1.1.0's Magic rows meant nothing. Run properly, the unfilled layout gives 5946 `Slt.c` on TopMetal1 (Magic's Metal5) in the IO cells' wide bands and the seal ring, 3096 subcell-abutment items and 148 `CntB.h1` and 12 `LU.d` in the IO cells, 58 `Seal.a` on the seal ring, and 164 overlap and 163 `M4.d` items inside the macro. None of them is in the clamp cell. IHP's KLayout decks report none of these on the same layout. LibreLane's Magic DRC of the macro alone reports 0, so the macro's 327 come from the chip-level view, and stay open.
- **18 max-slew items at the slow corner**, all on the output pads' bond side, 1.22 ns against 1.20 ns, from the SDC's assumed board load. The signals run at 512 Hz to 200 kHz.
- **156 max-fanout items**, inside the macro, against the chip SDC's limit of 10. The macro was hardened under its own, and no max-cap item comes with them.
- **145 max-slew items in the macro at the slow corner**, against its own SDC's 1.0 ns, worst 1.33 ns (9031d16, `macros/dsa1_dig/verification/stapostpnr_summary.rpt`). The chip SDC sets no limit, so the chip STA does not list them. EZ130's default limit is 5.33 ns, and setup holds with +44 ns.
- **Hold slack +0.074 ns at the fast corner rests on the EZ130 timing libraries.**
- **VDD must come up no later than IOVDD.** With IOVDD first, the IO cells' level shifters drive all 18 outputs high from IOVDD 0.58 V until VDD reaches 0.78 V, TEST_CTRL_0 bits 7:6 included, and flip together in a 21 ns, 381 mA spike on IOVDD. With VDD first no output goes high before the reset value. The eval PCB has to sequence the supplies.
- **No power-on reset.** Until the first `rst_n` low, TEST_CTRL_0 and the 16 test pads it drives are undefined, and bits 7:6 = 11 shorts the analog die's bias nodes. The host must hold `rst_n` low until both supplies are up.
- **Metal4 density at 57.40 %**, under 3 points from its maximum, if anything is ever added.
- **The ESD verdict is indicative.** IHP gives no transient limits and the simulation models no snapback. The 4.5 V and 10 V limits rank the pins, and HV crosses 10 V only for a diode on-resistance of 2 Ohm and above, which a TLP measurement of the IO diodes would settle.
- **VSS and IOVSS are one ground.** Every IO cell ties both to the substrate, which is why Magic extracts them as one node, and the package joins them on the paddle (`packaging/config.yaml`, `EPAD_NETS`). On the board the exposed pad is ground.
- **The GDS-level LVS joins VSS and IOVSS**, which share the substrate and which Magic extracts as one node. A metal short between them is visible only to LibreLane's DEF-level LVS, which keeps them apart and passes. The PDK's IO cells are compared by their pins, as in LibreLane's LVS.

## dsm2 6dd2926 integrated, 2026-10-29

dsm2's views from sg13cmos5l_batmon commit `6dd2926` (GDS md5 `6c7b7e559773e05e0ecf48338f57368d`, CDL `0f4d17b13e38c7a06f55973658880158`, LEF unchanged), which dsm2 confirmed as the GDS of its 2026-11-01 delivery. The rows above stay the v1.1.1 record until the v1.2.0 release. The numbers below are on chip run `RUN_2026-10-29_15-12-41`, delivery GDS md5 `b61196cdbfad4560e4fb28025be1e0d1`.

| check | result |
|---|---|
| Banned cells, analog nets, VDD isolation, keep-out | none, PASS, PASS, PASS. Mutants of the last two fail. `make check-keepout` checks metal in the outline, metal fill in the halo and Activ and GatPoly fill in the outline, a mutant with one Activ fill tile in the outline fails |
| Macro in the chip GDS against `macros/dsa1_dig/final/gds` | XOR 0 |
| dsm2 cell in the chip GDS and in the delivery GDS against `ip/dsm2_core/gds/dsm2_core.gds` | XOR 0 |
| IHP MPW precheck | 0 markers in 28 tables, shape scan PASS |
| KLayout regular DRC with antenna and latch-up | 37, `Pad.d1R` 4 and `Pad.fR_TM1` 33 = `DRC_EXPECT`, 33 of 33 tables, none inside the dsm2 box |
| Density | Activ 45.55 %, GatPoly 17.91 %, Metal1 51.29, Metal2 46.82, Metal3 50.94, Metal4 53.51, TopMetal1 46.21 %, no Activ or GatPoly fill inside the dsm2 outline. Worst 800 um Activ window (AFil.g2, at least 25 %) 43.05 % on the deck's 400 um grid and 37.71 % at (220, 220) on a 10 um sliding step, from `scripts/density_window.py` on the delivery GDS, which computes both as the deck takes the layers and the chip area |
| Magic DRC | 5237 unfilled, 5472 filled: the helmet build's 5223 and 5458 plus dsm2's 14 known items (12 `CntB.h1` in `sg13cmos5l_SecondaryProtection`, 2 `M1.e` in the OTA), nothing else in the box |
| Fill isolation | PASS |
| Top LVS, dsm2 device by device | `Circuits match uniquely`, no property error, 5 of 5 mutants fail |
| LibreLane LVS, STA, antenna | match, setup +44.07 ns and hold +0.0695 ns unchanged, 0 antenna |
| Current density | worst ratio 0.312 of 0.5. VDDA is rated at 1 mA against dsm2's design values of 28 uA average, 80 uA over 100 ns and 600 uA over 10 ns (its extracted view, dither off: 24.79 uA average) |
| Bond plan | unchanged |
| Chip cocotb | RTL 1 of 1, GL 12 of 12 (test_psd skipped) |
| HBM ESD, all 188 zaps at RON 1 and 4, dsm2's `sg13cmos5l_SecondaryProtection` on each analog pin in the model | no 1.2 V node, VDDA rail node or dsm2 pin node behind its protection over the indicative 4.5 V. Worst at RON 1 / 4: 1.2 V 3.88 / 3.87 V (`vdd_w2` + vs vdda), VDDA rail 4.40 / 4.40 V, dsm2 pin 4.36 / 4.41 V (`in_ibiastest`, `iovdd_w4` - vs vdda), HV -8.93 / -8.98 V, every pairing has a static path. dsm2's pin ahead of its 586.9 ohm reaches -5.78 / -6.80 V, not gated, only the rppd heads sit there. `report.py --fail-over` exits 0, [doc/esd_hbm.md](esd_hbm.md), `verification/esd/` |
| Start-up and bounce, dsm2's schematic at tt | `io_first`, `core_first` and `bounce` PASS, dsm2 as transistors (`STARTUP_DSM2=sch`), started as specified: di_ena at DSM_EN, di_rst_b and di_qout_en 130.00 us later. Reads right, the board order's do_q pads under 0.006 V until DSM_QOUT_EN, no supply above 10 mA for longer than 51 ns (IOVDD first, the known 53 mA level-shifter spike). dsm2's own VDDA current 0.47 uA disabled, 12.6 to 12.7 uA running (28 uA), enable inrush 67.7 uA over 100 ns and 214 uA over 10 ns, 37.0 pC in 10 us, running peaks 40 uA over 100 ns and 323 uA over 10 ns (140 uA over 100 ns from the dsm2 peer, 2026-10-31, schematic ff 125 C, quantizer fight excluded, 600 uA over 10 ns). dsm2 6dd2926's known latch fight occurred in every run, about 2 us at 206 uA (230 uA over 100 ns) when dsm_clk starts in reset, not judged. Modulator 50.0 to 51.6 % ones with vi at half VDDA, do_q_b and do_q_dec right in every period. VDD moves by 2 nA when dsm2 starts, and the mutant with dsm2's vdd on VDD fails there (+9.9 uA). Bounce, supplies up from the start: IOVDD-IOVSS 57 mV droop, die VSS 6 mV, no core input glitch. Found: in the board order vi driven before IOVDD back-powers IOVDD through the vi pad, 1.44 mA from a 50 Ohm source at half VDDA, and dsm2 draws up to 52 uA over 1 us disabled while IOVDD ramps and the dsm_clk pad's output crosses mid-rail. The bench's 1 MOhm on the vcm pad holds vcm at 0.40 V (0.25 to 0.50 V) against dsm2's 0.73 V unloaded. Extracted view on `core_first`: still running at 715 us of 760 after 42 h. Wall times 1094, 1086, 1142 min. `verification/startup/dsm2_sch/`, `verification/startup/dsm2_mutant/`, method in [testbenches/startup/README.md](../testbenches/startup/README.md) |

## dsm2 oscillator variant integrated, 2026-11-02

The tape-out candidate: dsm2's oscillator variant of 2026-11-02 (GDS md5 `00624787128efe33ca6ddf5273170e56`, LEF `042ec97848217f9a30e94a391885b839`, CDL `5df9700351cb3b2c1804480eb62dfc12`), `dsa1_dig` re-hardened at 409.08 x 514.08 um (LEC 1325 of 1325, 78ec6de), `decap_vdda` (67.61 pF on VDDA) north of dsm2, and VDD decap strips in the 11 rows below and 11 above `dsa1_dig`. `dsm_clk` is an `IOPadInOut4mA` driven by dsm2's oscillator when `BIAS_CFG_0` bit 8 is set. Chip run `RUN_2026-11-01_09-59-06`, unfilled GDS md5 `cda22ef8189fefab1b856ab6a3f5d4b9`, delivery GDS md5 `872f29b28253c9d28f666a7a5c80b096`. Every command ran through `scripts/in_image.sh` at the repo root. The rows above stay the v1.1.1 record until the release.

| check | command | result | evidence |
|---|---|---|---|
| Banned cells | `make check-netlist` | none | |
| Analog and 1.5 V nets | `python3 scripts/check_analog_nets.py netlist/nl/sg13cmos5l_dsa1_dig_top.nl.v flow/librelane/analog_nets.txt --rx flow/librelane/config.yaml` | PASS, `do_clk_osc` and `do_osc_oe` touch only dsm2 and the `dsm_clk` pad, no 1.2 V cell | `flow/librelane/analog_nets.txt` |
| VDD isolation | `python3 scripts/check_vdd_isolation.py <final def>`, and the drawing checks in `flow/librelane/pdn_cfg.tcl` | PASS, 28 vdd pins on VDDA (segment pads and fillers, dsm2, `decap_vdda`). No VDD shape touches `decap_vdda` on any layer. Its VDDA strap lands in the band of the IO filler at y 910 to 930, below `cut_vdd_e` at y 940 | `scripts/test_check_vdd_isolation.py` has a mutant with `decap_vdda` on VDD |
| Free rows | final DEF | rows 0 to 10 (y 346.08 to 379.68) and 170 to 180 (y 917.28 to 950.88), 22 rows, x 345.24 to 774.48 (rows 0 to 4 to x 945). The pocket between dsm2's and `decap_vdda`'s halos is pruned. Glue gates and mux in row 10 at x 475 to 728, the synchronizer in rows 170 and 171, all off dsm2's halo | |
| Macros in the chip GDS against their own GDS | `runs/final/xor.py` on the unfilled and the delivery GDS | `dsa1_dig_top`, `dsm2_core`, `decap_vdda`: XOR 0 on every layer, labels equal, in both | |
| IHP MPW precheck | `make mpw-precheck` | 0 markers in 28 tables, shape scan 0 degenerate, PASS | `verification/drc/precheck/` |
| KLayout regular DRC with antenna and latch-up | `make klayout-drc-regular` | 37, `Pad.d1R` 4 and `Pad.fR_TM1` 33 = `DRC_EXPECT`, 33 of 33 tables | `verification/drc/sg13cmos5l_dsa1_dig_top_logo_fill.klayout.drc/verdict.txt` |
| Density | same verdict, `python3 scripts/density_window.py` | Activ 45.58 % (35 to 55), GatPoly 17.55 % (at least 15), Metal1 51.72, Metal2 46.44, Metal3 51.03, Metal4 54.17 (35 to 60), TopMetal1 47.16 % (25 to 70). Worst 800 um Activ window 42.78 % on the deck's grid, 38.21 % on a 10 um step (at least 25). The `dsa1_dig` GDS stays unfilled | |
| Magic DRC | `make magic-drc`, `make magic-drc CELL=sg13cmos5l_dsa1_dig_top_logo_fill` | 5353 unfilled, 5588 filled. Against 6dd2926 (5237, 5472) the 116 more sit in the `dsm_clk` pad cell, now `IOPadInOut4mA`: 112 subcell-abutment and 4 overlap items, the same 112 each `IOPadOut4mA` carries. Inside dsm2 only its 14 known items (12 `CntB.h1`, 2 `M1.e`), none in `dsa1_dig` or `decap_vdda` | `verification/drc/*.magic.drc/` |
| Fill isolation | `klayout -b -r verification/lvs/fill_isolation.py` | PASS | `verification/lvs/fill_isolation.txt` |
| Keep-out | `make check-keepout` | PASS on the three checks | |
| Top LVS, dsm2 and `decap_vdda` device by device | `verification/lvs/top_lvs.sh`, `verification/lvs/top_lvs_mutants.sh` | `Circuits match uniquely`, no property error, the variant CDL (106 `cap_cmomf` and 1 `ptap1` dropped as before) and `decap_vdda`'s powered netlist in the reference. 6 of 6 mutants fail, the new `decap_vdd` among them | `verification/lvs/sg13cmos5l_dsa1_dig_top.gds.lvs/lvs.rpt` |
| LibreLane LVS, STA, antenna, IR drop | `make build-top` (copy-reports) | match uniquely. Setup +43.61 ns (slow), hold +0.055 ns (fast), 0 violations, 2 max cap (fast) and 3 max slew (slow). Antenna 0. IR typ: VDD 4.93 uV, VSS 418 uV worst | `verification/reports/` |
| Current density | `make em-probe` | worst ratio 0.312 of 0.5 (VDD Via1). VDDA rated at 1 mA against the variant's design values of 32 uA average, 220 uA over 100 ns and 600 uA over 10 ns | `verification/em/em_table.md` |
| Bond plan | `make bondplan` | unchanged but its date | `packaging/result.md` |
| Chip cocotb | `make sim-rtl-cocotb`, `make sim-gl-cocotb` | 13 of 13 at RTL and gate level, `test_psd` skipped. New `test_oscillator_drives_dsm_clk`, `test_bias_cfg_reaches_dsm2` covers bits 7 to 9 | `testbenches/cocotb/` |
| HBM ESD, all 188 zaps at RON 1 and 4 | `pex.py runs/final/esd all`, `models.py`, `check.py --ron 1/4`, `hbm.py --ron 1/4 --jobs 3 --drop-raw`, `report.py --fail-over` | VDD decap 82.69 pF in the core banks, `decap_vdda`'s 67.61 pF at its own strap ports, the `dsm_clk` pad's `c2p` and `c2p_en` each on a `BUFX3`. No 1.2 V node, VDDA rail node or dsm2 pin node behind its protection over the indicative 4.5 V. Worst at RON 1 / 4: 1.2 V 3.87 / 3.87 V (`vdd_w2` + vs vdda), VDDA rail 4.38 / 4.38 V (`vdda_e4` + vs vss), dsm2 pin 4.35 / 4.41 V (`in_ibiastest`, `iovdd_w4` - vs vdda), against 4.36 / 4.41 V on 6dd2926. HV -8.68 / 8.84 V. Every pairing has a static path. The same 4 zaps as before still relax past half the window (exit 1), `report.py --fail-over` exits 0 | [doc/esd_hbm.md](esd_hbm.md), `verification/esd/` |
| Start-up and bounce with the variant | | skipped, user decision 2026-11-02. The chip-level start-up passes with dsm2 6dd2926 as transistors (section above). dsm2 simulated the variant's own start-up at tt, ff 125 C and ss -40 C | dsm2 peer, 2026-11-01 |
| Release and submission dry run | `make release VERSION=1.2.0`, `OUT=runs/subdry/gds REC=runs/subdry/rec LVS_OUT=runs/subdry/lvs scripts/submission.sh MPC9724` | `release/v.1.2.0`, GDS md5 `872f29b28253c9d28f666a7a5c80b096`. On the renamed copy: IHP precheck deck 0 markers in 73 rule categories, top LVS device by device PASS. Rerun on submission day into the release folder | `release/v.1.2.0/gds/*.md5` |
| IHP delivery copy | `OUT=release/v.1.2.0 scripts/release_ihp.sh`, a KLayout XOR of all layers against the source, IHP's precheck deck on the copy | `gds/MPC9724.gds.gz`, md5 `76a2eec3f01e6683685c9e5533fa3d0b`, top `MPC9724`, 0 degenerate shapes, netlists define `MPC9724` once. XOR 0 on 59 layers against `872f29b2`. Precheck 0 markers in 73 rule categories | `release/v.1.2.0/ReleaseNote.md` |
