<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
Description: HBM ESD simulation of the pad ring on its extracted metal
-->

# HBM ESD of the pad ring

**On the tape-out layout, with dsm2's oscillator variant, the 1.2 V nodes, the VDDA rail and dsm2's analog pin nodes behind its own input protection stay under the indicative 4.5 V at 2 kV HBM, and the HV side stays under its 10 V.** Every one of the 188 pairings has a path. 188 zaps (JS-001 pin combinations, both polarities) on the extracted pad ring of the delivery layout, transistor-level pad cells, both clamp copies and dsm2's `sg13cmos5l_SecondaryProtection` on each analog pin, at a diode on-resistance RON of 1 and 4 ohm. The ring has a second `IOPadIOVdd` cell on the west side, without a bond wire, so the iovdd-to-iovss clamp exists twice (Task 8c). Numbers below are from the run of 2026-11-01 in the pinned `:next` image (chip run `RUN_2026-11-01_09-59-06`). Against the 6dd2926 layout the core decap is 82.69 pF instead of about 145 pF, `decap_vdda` adds 67.61 pF on VDDA at its own straps (`vddadcp`, `vssdcp`), and `dsm_clk` is an `IOPadInOut4mA` whose `c2p` and `c2p_en` each get a `BUFX3` on dsm2's nodes. The 6dd2926 column is the run of 2026-10-30. RON 0.5 and 2, the package short, the ideal ring and the VDDA clamp mutant were not rerun, see [Not rerun](#not-rerun).

| | 6dd2926, RON 1 / RON 4 | RON 1 | RON 4 |
|---|---|---|---|
| die only: pad max / min V | 10.7 / -7.8, 12.6 / -9.8 | 10.4 / -7.8 | 12.2 / -9.8 |
| die only: 1.2 V nodes, worst V (`vdd_vss@miso`, `vdd_w2` + vs vdda) | 3.88, 3.87 | **3.87** | **3.87** |
| die only: VDDA rail (segment pads), worst V (`vdda_vss@dsmclk`, `vdda_e4` + vs vss) | 4.40, 4.40 | **4.38** | **4.38** |
| die only: VDDA to VSS at dsm2's pins `vddadsm` / `vssdsm`, worst V (`vdda_e4` + vs vss) | 3.64, 3.64 | 3.63 | 3.63 |
| die only: VDDA to VSS at `decap_vdda`'s straps, worst V (`vdda_e4` + vs vss) | not in the model | 3.37 | 3.37 |
| die only: dsm2 analog pin behind its protection, `in_<pin>`, worst V (`core_in@ibiastest`, `iovdd_w4` - vs vdda) | 4.36, 4.41 | **4.35** | **4.41** |
| die only: dsm2 analog pin itself, `padres`, worst V, not gated (`core_padres@vcm`, `vcm` + vs vdda) | -5.78, -6.80 | -5.60 | -6.59 |
| die only: worst HV V | -8.93, -8.98 (`pad_iovdd@vdda_e4`, `ibiastest` + vs vdda) | **-8.68** (same node and zap) | **8.84** (`pad_iovss@doqb`, `doqb` + vs vdda) |
| die only: zaps with an HV node over 10 V | 0, 0 | 0 | 0 |
| zaps with a 1.2 V node, the VDDA rail or an `in_<pin>` node over 4.5 V | 0, 0 | 0 | 0 |
| zaps with `padres` over 4.5 V, not gated | 12, 19 | 12 | 19 |
| static check: pairings with a path | 188, 188 | 188 | 188 |

1. **Which nodes the 1.5 V figure is taken at.** `dsm2_core` is outside the clipped ring, so its inside is not in the model except its input protection. The figures are taken at its pin nodes: `vddadsm` and `vssdsm`, the points where dsm2's VDDA strap and VSS strap leave the clipped annulus (3.63 V worst, `dsm_vdda_vss`), at the core side of the `dsm_clk`, `do_q` and `do_q_b` pad cells against those two nodes (a `BUFX3` stands in for dsm2's output drivers and 50 fF for its input), and at the three analog pins behind dsm2's protection, `in_vi`, `in_vcm` and `in_ibiastest`, against them. The VDDA rail along the segment's pad cells, which is the metal the segment's IO cells see, is 4.38 V at worst, 0.12 V under the limit. `decap_vdda` sits at its own strap ports, `vddadcp` and `vssdcp`, as the core banks are built (C in series with its channel R per cell type). dsm2's own decap and well junction are not in the model.
2. **dsm2's protection keeps its analog pins under the limit, with 0.09 V of margin at RON 4.** Each of `vi`, `vcm` and `ibias_test` reaches dsm2 through its own `sg13cmos5l_SecondaryProtection` (`esd_dsm2_secprot` in `scripts/esd/models.py`, from dsm2's CDL): 586.9 ohm of rppd into `in_<pin>`, a 3.187 um^2 p+ diode from `in_<pin>` to `vddadsm` and a 1.984 um^2 n+ diode from `vssdsm` to it. The worst is 4.35 V at RON 1 and 4.41 V at RON 4, `in_ibiastest` against `vddadsm` in `iovdd_w4` - vs vdda, with `vi` and `vcm` 4.27 and 4.38 V in their own zaps against VDDA. It is the VDDA-to-VSS rail plus one diode drop, set by the ring and the VDDA clamp, not by the cell. The diodes are small, so their series resistance is 17.6 x RON (dn) and 11.0 x RON (dp), which is why RON moves this node more than the rails. Without the protection (8c column) `padres` reached -9.73 and -9.93 V in 45 zaps. `padres` itself, dsm2's pin ahead of the 586.9 ohm, still reaches -5.60 V and -6.59 V (`vcm` + vs vdda), in 12 and 19 zaps over 4.5 V. Only the two rppd heads, dsm2's and the `IOPadAnalog` cell's, sit on that node, no gate (dsm2's CDL connects `vi`, `vcm` and `ibias_test` to its protection cells only), so it is reported and not gated. `models.py` stops if dsm2's CDL no longer draws these three devices with these sizes.
3. **The VDDA clamp copy is needed.** On the v8b layout (not rerun) with the second clamp left out (`hbm.py --no-clamp clamp_vdda`, the 60 zaps that touch VDDA at RON 1, `report.py --fail-over` exits 1 on it and 0 on the run with the clamp, dsm2's pin nodes aside) the VDDA rail reaches 8.69 V (`vdda_vss@dsmclk`, `vdda_e4` + vs vss, 4.41 V with it) and `dsm_vdda_vss` 8.56 V (`vdd_w2` - vs vdda, 3.61 V with it, both in `verification/esd/esd_hbm_r1_no_clamp_vdda.json`), 19 of the 60 zaps over 4.5 V against none with it. The static check cannot see it: it still finds a path for all 188 pairings, and prices VDDA + vs VSS at 10.25 V against 9.65 V. Five VDD-referenced zaps of that run are still rising at the end of the window (1.4 to 3.1 V on floating nodes), their VDDA rail reads 0.61 V.
4. **The VDDA pad's return to VSS is long.** The nearest VSS pad of the VDDA segment is the one on the south side, past `dsm_clk`, `do_q` and `do_q_b`, so the VDDA clamp's current returns along the segment's vss band: 4.0 ohm of ring metal in the static path against 2.0 ohm for the VDD clamp. That is why the VDDA rail peaks at 4.38 V, close to the limit, in `vdda_e4` + vs vss.
5. **HV is under its indicative limit with the second `IOPadIOVdd` cell.** The IO library holds an iovdd-to-iovss clamp only in `IOPadIOVdd`, and the die had one. In a signal pin zapped against VDD or VDDA the whole current crossed that clamp (7.9 V) and then the supply cell's clamp NMOS backwards, so `pad_iovdd` reached 11.54 V (`ibiastest` + vs vdda) and 10.15 V against VDD at RON 1, with 30 zaps over 10 V at RON 0.5 and 1 and 96 at RON 4. The die now has `g_iovdd_pads[1]` on the west side, on the same IOVDD net, with a bondpad and no wire (`UNBONDED_PADS` in `packaging/config.yaml`), so the package and the lead table are unchanged. Worst HV is -9.02 V at RON 1 and -9.04 V at RON 4 (`pad_iovdd@vdda_e4`, `ibiastest` + vs vdda), no zap over 10 V at either. The pad max falls from 13.2 to 10.7 V and the pad min from -10.3 to -7.9 V at RON 1. The 10 V is still indicative, a TLP number for `DCPDiode` would turn it into a verdict. The unbonded cell is not a tester pin: `hbm.UNBONDED` keeps it out of the reference pins, and the IOVDD group is zapped at `iovdd_w4`, the bonded one. An earlier run that tied it to the reference gave the same figures to the digit shown.
6. **The 1.2 V nodes.** VDD + vs VSS through the VDD clamp reads 3.69 V (`vdd_vss@vss_s3`, 3.74 V in v8b, 3.16 V on the v8b ideal ring, v1.1.1 had 3.58 V). The worst 1.2 V quantity of the die, 3.87 V at `vdd_vss@miso`, is `vdd_w2` + vs vdda: the current goes through the VDD clamp, the ring and the VDDA clamp.
7. **The package short changes little.** On the v8b layout (not rerun) with VSS and IOVSS on the paddle the 1.2 V worst was 3.88 V and the VDDA rail 3.99 V. Its downbonds are still modelled as 0.5 nH and 0.05 ohm (500 um), the wires of the bond plan are shorter, see [packaging/result.md](../packaging/result.md).

## How to run it

Everything runs in the pinned `:next` image (`scripts/image.env`, kpex 0.6.3, ngspice-47) through `scripts/in_image.sh`, not in the 2026.08 sign-off image of v1.1.1. The IO netlist is the image's `libs.ref/sg13cmos5l_io/spice/sg13cmos5l_io.spice`, which carries the substrate ties. `EZ130_DIR` and `DECAPHV_DIR` can point at `ip/ez130_8t_v1p1` and `ip/ez130_8t_decap_hv`. The run directory is git-ignored, the summaries land in `verification/esd/`.

```bash
R=runs/gaps/esd
python3 scripts/esd/models.py --selftest; python3 scripts/esd/pex.py --selftest
python3 scripts/esd/check.py --selftest; python3 scripts/esd/hbm.py --selftest   # tester against JS-001
python3 scripts/esd/report.py --selftest
ESD_NJOBS=6 python3 scripts/esd/pex.py $R all          # clip, kpex, Kron reduction (20 min)
python3 scripts/esd/models.py $R/sim                     # IO netlist with high-current diodes
python3 scripts/esd/check.py $R --ron 1 [--pkg-gnd]      # static path check (seconds)
python3 scripts/esd/check.py $R --without iovdd_w4 --without iovdd_w5   # must fail: exits 1 (one cell alone still leaves a path)
python3 scripts/esd/check.py $R --without clamp_vdda     # still a path, the price moves
for r in 1 4; do
  python3 scripts/esd/hbm.py $R --ron $r --jobs 6 --drop-raw [--pkg-gnd]
  python3 scripts/esd/report.py $R --ron $r [--pkg-gnd] --json verification/esd/esd_hbm_r$r[_pkg].json
done
python3 scripts/esd/hbm.py $R --ron 1 --ideal-ring --jobs 6    # the no-metal reference
# the mutant: the 60 zaps that touch VDDA, without the VDDA clamp copy
python3 scripts/esd/hbm.py $R --ron 1 --no-clamp clamp_vdda --zap <zap:ref:pol> ...
python3 scripts/esd/report.py $R --ron 1 --no-clamp clamp_vdda --fail-over   # exits 1, the run with the clamp exits 0
python3 scripts/esd/report.py $R --tables [--pkg-gnd]           # the tables
```

`hbm.py` exits 1 when a zap is still rising past half its window. On the tape-out layout four are, at RON 1 and at RON 4, the four below, by 0.11 to 0.14 V. The table is from the 8c run, where `vdda_e4` + vs vss was a fourth at RON 1:

| zap | past half the window at 80 ns | at 3 us (RON 1) |
|---|---|---|
| `iovss_w3` - vs vdda (known, documented since v8b) | 0.11 V | still 0.10 V, `vdda_p2c@dsmclk` 1.36 V to 1.81 V, no limit near |
| `vdd_w2` - vs vdda | 0.14 V | still 0.16 V, `p2c_core@dsmclk` 2.20 V to 3.35 V, under 4.5 V and still rising. v8b read 3.23 V there at 80 ns |
| `vdd_w2` - vs vss | 0.13 V | settled, `core_c2p@miso` -0.53 V to -0.72 V |
| `vdda_e4` + vs vss (RON 1 only) | 0.10 V | settled, the VDDA rail stays 4.40 V and `dsm_vdda_vss` 3.64 V |

All of them are floating nodes of dsm2's `dsm_clk` input and the `miso` and `adc_conv` outputs relaxing slowly. The sweep's exit code 1 is these zaps. The JSON files hold the 80 ns runs. The 3 us reruns are the 8c ones, `vdd_w2` - vs vdda was not rerun at 3 us with dsm2 6dd2926.

The scripts are ported from OpenBLAU (`scripts/esd/`, `scripts/spicerun.py`, commit 8f25e634). Its RF pad, the RF pad's clamp, the RF driver and VMON are gone, and the core model is DSA1's own plus dsm2 as a box with its input protection.

## What is simulated

**The pad ring and core ring as extracted metal.** `scripts/esd/ring_clip.py` flattens the unfilled GDS `layout/sg13cmos5l_dsa1_dig_top.gds.gz` (md5 `129144a4deca71f4bd9e865f45551408`, 1300 um die, dsm2 6dd2926) outside the core box (x, y in [344.5, 955.5]), Metal1 to TopMetal1 with every via, and keeps the metal of the nets that carry ESD current, found by one `LayoutToNetlist` run probed at the ports. It reads every slot of all four sides. Fill is isolated metal and is left out. The vdd band of the pad cells between the two `cut_vdd` cells is its own rail, `vdda`: those cells carry `vdda` for `vdd` in every port name. The clip asserts the cut, that no two nets share metal, and that VDD and VDDA are separate nets.

| port | where | what attaches |
|---|---|---|
| `<rail>_<slot>` | every rail band of a pad cell, at the cell's centre line | that pad cell's rail pin |
| `pad_<slot>` | the bond pad plate, at the chip's own pad label | the tester |
| `padc_<slot>` | the pad cell's pad strip | the pad cell's pad pin |
| `<rail>ring_<k>` | the core ring, 8 points per rail | core decap, core well, the core cells behind the pads |
| `clv_clamp`, `cls_clamp`, `clv_clamp_vdda`, `cls_clamp_vdda` | every Metal2 stripe of the clamp cells, vdd and vss, at the fingers' centroid | the clamps, `esd_clamp_vddvss_cell` in `models.py`, one per copy |
| `vddadsm`, `vssdsm` | where dsm2's VDDA strap (Metal3, x 952, y 550) and VSS strap (x 955, y 705) leave the clip | the pins of the dsm2 box |
| `<rail>_clamp`, `<rail>_clamp_vdda` | the clamp cells' rail bands | nothing, ring metal |

Slots are numbered per side in their order, IO pad cells only, so the clamp cells take no slot number. Slots are named after the signal (`miso`, `adcconv`, `datain`, `sclk`, `mosi`, `ss`, `rstn`, `clk`, `vi`, `vcm`, `ibiastest`, `dsmclk`, `doq`, `doqb`) or after the supply and its place (`vss_w1`, `vdd_w2`, `iovss_w3`, `iovdd_w4`, `iovdd_w5`, `vss_s3`, `vdda_e4`). `iovdd_w5` is the cell without a wire. The core ring is Metal4 on W and E and TopMetal1 on S and N, 5 um wide, vdd the inner ring on every side, one net with the pad ring's vdd and vss bands, and VDDA is not on it. The clip asserts that every pad slot and the clamp cells have a port on all four rails and that every clamp stripe port sits on its rail's metal. No rail splits into islands.

kpex 2.5D (kpex 0.6.3 of the `:next` image) extracts the clip R-only through `scripts/esd/kpex_cmos5l.py --wires --mode R`, and `scripts/esd/pex.py` reduces it onto the 156 port nodes (529 labels, repeated names joined) by Kron reduction, exact at DC: 747,120 resistors to 523 branches. The reduced network is `verification/esd/esd_ring_rport.spice`. The extraction and reduction take 20 to 30 min.

The reduction was checked on the v1.1.0 ring (two-port resistances of the full network against the reduced one agreed to 5 digits) and is not re-checked on this ring.

**Every pad cell at transistor level**, from the pinned image's `libs.ref/sg13cmos5l_io/spice/sg13cmos5l_io.spice`, which carries the substrate (`sub!`) and its ptap ties. This is the PDK version the layout's IO cells are from (the repo's snapshot under `ip/sg13cmos5l_io_custom` is another one, see `testbenches/startup/README.md`). The IO library clamps vdd to iovss in `IOPadVdd` and iovdd to iovss in `IOPadIOVdd`, and no cell clamps vdd to vss: a vdd-to-vss discharge has to stack the vdd clamp and the `IOPadVss` diode from iovss into vss, or go through the `clamp_vddvss` cell. The VDDA segment's cells have their vdd pin on `vdda`.

**The clamp cell** at transistor level from its schematic devices: `sg13_hv_nmos` 2268/0.6 um, the 126/9.5 um MOS capacitor, IHP's inverter (108/0.5 and 350/0.5 um), the 129.3 kOhm rppd trigger, between `clv_clamp` and `cls_clamp`, and a second copy between `clv_clamp_vdda` and `cls_clamp_vdda` on the segment. `hbm.py --no-clamp clamp_vdda` leaves the second one out.

**The core**, DSA1's own, and dsm2 as a box with its input protection:

| part | value | source |
|---|---|---|
| core-rail decap | 143.1 pF in three banks, split over the 8 core-ring points: `DECAPHV32` 1378 cells x 79.01 fF = 108.88 pF, `DECAPHV16` 792 x 30.52 fF = 24.17 pF, `DECAPHV8` 1600 x 6.272 fF = 10.04 pF | cell counts from `netlist/pnl/sg13cmos5l_dsa1_dig_top.pnl.v` (1369, 607, 759) plus `macros/dsa1_dig/final/pnl/dsa1_dig_top.pnl.v` (9, 185, 841). C per cell: the `$DECAPHV_DIR/cdl/ez130_8t_decap_hv.cdl` device (one `sg13_hv_pmos`, W 1.66 um, L 0.82 / 4.18 / 10.9 um, gate on VSS) in ngspice, AC at 1 MHz biased at 1.2 V, tt. It moves under 4 % up to 5 V. The liberty has no capacitance. |
| decap series R | per bank 1 / (2 pi f_c C): 4.459, 3.311 and 0.458 ohm per cell class, plus 0.5 ohm for the whole bank (assumption) | f_c is the decap library's own channel-corner estimate, 60 MHz, 0.4 GHz and 10 GHz (`$DECAPHV_DIR/doc/decap_hv.md`) |
| core n-well junction | a high-current diode vss to vdd of 20000 um^2, split over the 8 points | assumption, as in OpenBLAU: a bound, not measured |
| output pads (2 on VDD) | the macro's `BUFX3` that drives `c2p` (`AND2X1` for `adc_conv`), input at its vss (unpowered core), on the nearest core-ring point | `netlist/pnl`, `macros/dsa1_dig/final/pnl`. Devices from `$EZ130_DIR/cdl/ez130_8t.cdl` |
| dsm2 outputs (`do_q`, `do_q_b`) | a `BUFX3` on `c2p`, input at `vssdsm`, supplies `vddadsm` and `vssdsm`: a stand-in for dsm2's output drivers | assumption, dsm2 is a box |
| inputs (4 on VDD, `dsm_clk` on the segment) | 50 fF from `p2c` to the nearest core-ring vss point, `dsm_clk` to `vssdsm` | assumption, as in OpenBLAU |
| dsm2 analog pins (`vi`, `vcm`, `ibias_test`) | `padres` goes through dsm2's `sg13cmos5l_SecondaryProtection`, `esd_dsm2_secprot`: the PDK rppd (w 1 um, l 2 um, body on `vssdsm`, 586.9 ohm at DC) to `in_<pin>`, `esd_dp` 0.64 x 4.98 um from `in_<pin>` to `vddadsm`, `esd_dn` 3.1 x 0.64 um from `vssdsm` to `in_<pin>`, and 50 fF from `in_<pin>` to `vssdsm` for dsm2's input. No dsm2 decap, no well junction | `ip/dsm2_core/cdl/dsm2_core.cdl` lines 424 to 430 (dsm2 6dd2926), the 50 fF and the rest an assumption. Item 2 of the results |

**The tester**: 100 pF, 1.5 kohm, 5 uH, 1 pF at the pin. Into a short at 2 kV it gives 1.247 A peak, 7.86 ns rise and 154.0 ns decay, inside JS-001 (`hbm.py --selftest` asserts it). The reference pins sit at 0 V through 1 mohm, every other pin floats.

**High-current diodes.** The PDK's `dantenna`/`dpantenna` cards are fitted for reverse bias and read kilovolts at an ampere, so `models.py` swaps each for a level-1 diode with the PDK's saturation current, ideality, junction C and breakdown per area, and `rs = RON` per 35 um^2, scaled by area. RON is unknown for this process and is swept: 0.5, 1, 2, 4 ohm. The RC-triggered rail clamps stay PSP: they conduct as a MOSFET, which PSP models. Snapback, avalanche and oxide breakdown are not modelled, so nothing fails by itself here and the limits are indicative.

| class | quantity | indicative limit |
|---|---|---|
| LV, 1.2 V devices | core-ring vdd - vss (`core_vdd_vss_k`), every VDD slot's vdd - vss (`vdd_vss@slot`), `c2p`, `p2c` against the slot's vdd and vss (the pad cell's level shifter gates and LevelDown output) and against the core-ring point their core cell sits on (`*_core@`, `core_*@`) | 4.5 V |
| 1.5 V, the VDDA domain | the same quantities on the segment's slots (`vdda_vss@slot`, `vdda_iovss@slot`), `dsm_vdda_vss` between dsm2's two pin nodes, the segment's `c2p` and `p2c` against `vddadsm` and `vssdsm` (`core_*@`), and the analog pins behind dsm2's protection, `in_<pin>`, against them (`in_core@`, `core_in@`) | 4.5 V, the same thin oxide, not scaled |
| dsm2's analog pin itself | `padres` against `vddadsm` and `vssdsm` (`padres_core@`, `core_padres@`): only the two rppd heads sit on it | reported, not gated |
| HV, 3.3 V devices | iovdd - iovss, pad against either IO rail, the secondary-protected input node and `padres` against either IO rail, vdd and vdda - iovss (the vdd clamps) | 10 V |

On a supply slot the pad strip is that supply, so `pad_iovdd@vdd_w3` is vdd - iovdd at the VDD pad.

**The matrix**, JS-001 pin combinations, both polarities. Die only: 14 signal pins against each of the 5 supply groups (VDD, VDDA, VSS, IOVDD, IOVSS: 140), the supply groups against each other (20), each signal pin against all other signal pins tied (28): 188. That includes `vi`, `vcm`, `ibias_test`, `dsm_clk`, `do_q`, `do_q_b` and the VDDA pad against every supply. The IOVDD group is zapped at `iovdd_w4`, the bonded cell, and `iovdd_w5` is never a tester pin. Every zap runs 80 ns with `.options cshunt=1e-16 rshunt=1e9 method=gear`, `uic`, one thread per ngspice, 4 to 6 in parallel.

**VSS = IOVSS in the package (`--pkg-gnd`).** `packaging/config.yaml` puts VSS and IOVSS in `EPAD_NETS`: the pads downbond to the paddle and leads 3, 5 and 9 bond to it. JS-001 then sees one pin group `gnd`, zapped or referenced at the package node, which each of the three pads reaches through its own downbond, modelled as 0.5 nH and 0.05 ohm (500 um of 25 um gold, the v1.1.1 value). The matrix drops to 152 zaps (4 groups). A `gnd` zap is listed under `iovss_w3`.


## Results, die only

| | RON 1 | RON 4 |
|---|---|---|
| zaps run / of | 188 / 188 | 188 / 188 |
| retried: 0.02 ns step / trap / cshunt | 0 / 0 / 0 | 0 / 0 / 0 |
| still rising past half the window | 3 | 3 |
| pad, max / min V | 10.7 / -7.8 | 12.6 / -9.8 |
| worst 1.2 V V | 3.88 | 3.87 |
| worst 1.2 V V: node, zap | `vdd_vss@miso`, `vdd_w2` + vs vdda | same |
| VDDA rail, worst V | 4.40 | 4.40 |
| VDDA rail: node, zap | `vdda_vss@dsmclk`, `vdda_e4` + vs vss | same |
| worst 1.5 V node V | 4.40 (the VDDA rail) | 4.41 (`core_in@ibiastest`) |
| dsm2 analog pin behind its protection, worst V | 4.36 | 4.41 |
| dsm2 analog pin behind its protection: node, zap | `core_in@ibiastest`, `iovdd_w4` - vs vdda | same |
| zaps with an `in_<pin>` node over 4.5 V | 0 | 0 |
| dsm2 analog pin itself, `padres`, worst V, not gated | -5.78 | -6.80 |
| `padres`: node, zap | `core_padres@vcm`, `vcm` + vs vdda | same |
| zaps with `padres` over 4.5 V | 12 | 19 |
| worst HV V | -8.93 | -8.98 |
| worst HV V: node, zap | `pad_iovdd@vdda_e4`, `ibiastest` + vs vdda | same |
| zaps with an HV node over 10 V | 0 | 0 |
| `report.py --fail-over` | exits 0 | exits 0 |

`python3 scripts/esd/report.py runs/gaps/esd --tables` prints the per-pin table and every quantity over its limit. `verification/esd/esd_hbm_r1.json` and `esd_hbm_r4.json` are these runs, `esd_ring_rport.spice` their ring.

## Not rerun

The second IOVDD cell was added late (Task 8c), and the sweep that goes with it is RON 1 and 4, die only. These were not rerun and their files in `verification/esd/` are the v8b ones, on the layout with one `IOPadIOVdd` cell: RON 0.5 and 2 (`esd_hbm_r0.5.json`, `esd_hbm_r2.json`), VSS = IOVSS in the package (`*_pkg.json`, 152 pairings, 1.2 V worst 3.88 V and VDDA rail 3.99 V at RON 1), the ideal ring (`esd_hbm_r1_ideal.json`), the VDDA clamp mutant (`esd_hbm_r1_no_clamp_vdda.json`, VDDA rail 8.69 V without the copy), and the static check at the other RON. The start-up and bounce benches are not affected by a cell without a wire, but they are rerun with the real dsm2 views in Task 10 together with these.

## Static path check

`scripts/esd/check.py` flattens the same netlists into a graph of forward diodes, rail clamps, substrate ties and the extracted metal, and prices each pairing's cheapest path at the HBM peak current, 1.33 A: 0.7 V plus RON per diode, a clamp's V0 + R*I, metal I*R. It follows one path, so it reads higher than the transient where current shares pads. The rail clamp is calibrated from two zaps on `IOPadIOVdd` alone: V = 2.48 V + 4.16 ohm * I, and the clamp cell is priced as three of them in parallel.

| | RON 0.5 | RON 1 | RON 2 | RON 4 |
|---|---|---|---|---|
| die only: pairings with a path | 188 of 188 | 188 of 188 | 188 of 188 | 188 of 188 |
| die only: worst path V (`vi` + vs vdda at RON 0.5, `adcconv` + vs vdda above) | 13.11 | 15.04 (`vcm` + vs vdd) | 19.21 | 27.45 |
| VSS = IOVSS: pairings with a path | 152 of 152 | 152 of 152 | 152 of 152 | 152 of 152 |

RON 1 and 4 are on the tape-out layout (15.04 V and 27.45 V, the same as with dsm2 6dd2926, 8c had 15.04 and 27.50 V on the abstract, v8b 15.07 V at RON 1), RON 0.5 and 2 and the package short are v8b. dsm2's protection adds no path here: the check does not route through a resistor over 100 ohm.

At RON 1, VDD + vs VSS prices 6.72 V through the VDD clamp (6.96 V in v8b), VDDA + vs VSS 9.65 V through the VDDA clamp and the long vss band.

**It can fail.** Without both `IOPadIOVdd` cells' devices (`--without iovdd_w4 --without iovdd_w5`) 86 of 188 pairings have no path and it exits 1. Without `iovdd_w4` alone it still finds all 188, through the other cell. Without the VDDA clamp copy (`--without clamp_vdda`) every pairing still has a path and VDDA + vs VSS goes from 9.65 V to 10.25 V: like the VDD clamp in v1.1.1, the cell lowers the voltage and adds no path. The transient run without it fails (item 3 above). Results in `verification/esd/check_r*.json`.

## Numerics and runtime

Each deck runs 80 ns. A deck that stops on "Timestep too small" retries with a 0.02 ns step, then `method=trap`, then 1 fF and 3 fF `cshunt` (`hbm.RETRY`), and records the rung. None of the 376 decks of this sweep or of the 8c sweep, the 1,548 of the v8b sweep or the 60 of its mutant run aborted, none needed `cshunt`.

Four zaps at RON 1 and three at RON 4 are still rising past half the window, see How to run it. The 80 ns peaks of every other zap are not rerun.

Runtime, 2026-10-30 on the laptop, 4 ngspice in parallel next to another session's simulations: 30 min for the extraction and reduction, 50 min at RON 1 and 58 min at RON 4. On 2026-10-27 with 6 in parallel it was 20 min each. On 2026-10-26, with another session's simulations running, the v8b sweep took 3 h 52 min.

## Open

- **dsm2's inside beyond its input protection.** Its decap, well junction and the gates behind `in_<pin>` are not in the model, `in_<pin>` has 50 fF. dsm2's input protection is in since 2026-10-30, from its 6dd2926 CDL.
- **RON and the limits need a source.** A TLP curve of `DCNDiode` and `DCPDiode` and IHP's transient oxide and snapback numbers for the LV, HV and 1.5 V devices would turn the bands into a verdict. 4.5 V and 10 V are indicative.
- **Assumptions to check:** the core n-well junction (20000 um^2), the decap banks' series R, the 50 fF input loads and the stand-in for dsm2's output drivers. The core sits at 8 points on the core ring, the core grid between them is not modelled.
- **Not modelled:** substrate resistance between pads (one `sub!` node), the corner and filler cells' substrate ties, the routes from pads to the core, CDM, and metal current density at 1.3 A.
