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
- **Hold slack +0.074 ns at the fast corner rests on the EZ130 timing libraries, a prerelease.**
- **VDD must come up no later than IOVDD.** With IOVDD first, the IO cells' level shifters drive all 18 outputs high from IOVDD 0.58 V until VDD reaches 0.78 V, TEST_CTRL_0 bits 7:6 included, and flip together in a 21 ns, 381 mA spike on IOVDD. With VDD first no output goes high before the reset value. The eval PCB has to sequence the supplies.
- **No power-on reset.** Until the first `rst_n` low, TEST_CTRL_0 and the 16 test pads it drives are undefined, and bits 7:6 = 11 shorts the analog die's bias nodes. The host must hold `rst_n` low until both supplies are up.
- **Metal4 density at 57.40 %**, under 3 points from its maximum, if anything is ever added.
- **The ESD verdict is indicative.** IHP gives no transient limits and the simulation models no snapback. The 4.5 V and 10 V limits rank the pins, and HV crosses 10 V only for a diode on-resistance of 2 Ohm and above, which a TLP measurement of the IO diodes would settle.
- **VSS and IOVSS are one ground.** Every IO cell ties both to the substrate, which is why Magic extracts them as one node, and the package joins them on the paddle (`packaging/config.yaml`, `EPAD_NETS`). On the board the exposed pad is ground.
- **The GDS-level LVS joins VSS and IOVSS**, which share the substrate and which Magic extracts as one node. A metal short between them is visible only to LibreLane's DEF-level LVS, which keeps them apart and passes. The PDK's IO cells are compared by their pins, as in LibreLane's LVS.
