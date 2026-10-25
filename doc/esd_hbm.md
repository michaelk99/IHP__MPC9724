<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
Description: HBM ESD simulation of the pad ring on its extracted metal
-->

# HBM ESD of the pad ring

**With the vdd-to-vss clamp cell (v1.1.1) every 1.2 V node stays under the indicative 4.5 V at 2 kV HBM, at every diode on-resistance: the core rail peaks at 3.58 V (VDD + vs VSS), 3.44 V with VSS and IOVSS joined in the package.** Without it (v1.1.0) the same zap put 8.4 V across the core rail. Every pin has a discharge path. The HV side is unchanged by the clamp: under 10 V up to a diode RON of 1 Ohm, 10.0 V at RON 2 and up to 11.2 V at RON 4. 292 zaps (JS-001 pin combinations, both polarities) on the extracted pad ring of the delivery layout, transistor-level pad cells and clamp, at four values of the one unknown, the diode on-resistance RON, 0.5 to 4 ohm.

| | RON 0.5 | RON 1 | RON 2 | RON 4 |
|---|---|---|---|---|
| die only: pad max / min V | 11.3 / -9.5 | 11.5 / -9.8 | 12.1 / -10.4 | 13.3 / -11.7 |
| die only: core rail, worst V (`vdd_w3` + vs vss) | **3.58** | **3.58** | **3.58** | **3.58** |
| die only: worst HV V | -9.79 | -9.72 | 10.04 | 11.23 |
| VSS = IOVSS: pad max / min V | 10.8 / -9.5 | 11.1 / -9.8 | 11.7 / -10.4 | 12.9 / -11.6 |
| VSS = IOVSS: core rail, worst V (a signal pin - vs vdd) | **3.44** | **3.44** | **3.44** | **3.44** |
| VSS = IOVSS: worst HV V | -9.41 | 9.33 | 9.92 | 11.09 |
| zaps with a 1.2 V node over 4.5 V, die / VSS = IOVSS | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| v1.1.0, no clamp: core rail, worst V, die / VSS = IOVSS | 8.39 / 7.32 | 8.43 / 7.34 | 8.48 / 7.35 | 8.53 / 7.33 |
| ideal ring (die only, RON 1): pad max / min, core rail V | | 10.8 / -9.7, 3.10 | | |
| static check: pairings with a path, die / VSS = IOVSS | 292 / 230 | 292 / 230 | 292 / 230 | 292 / 230 |

1. **The clamp carries the core rail.** `sg13cmos5l_ip__clamp_vddvss` sits between the VSS and the VDD pad (`ip/sg13cmos5l_ip__clamp_vddvss`), three times IHP's `IOPadVdd` clamp NMOS with its source on vss. VDD + vs VSS now goes through it alone, 3.58 V at the VSS pad, and every pin zapped negative against VDD, which went through the IOPadVdd clamp and the `IOPadVss` diode at 7.2 V before, reads 3.41 to 3.56 V. It does not depend on RON: no diode is in the path.
2. **The clamp's metal is extracted, not estimated.** Each of its 24 Metal2 stripes is a port of the ring network, so its in-cell metal and the bands it reaches are in the R network. The bench estimate before it was drawn (0.4 ohm a side, `hbm.py --clamp vss_w2 --clamp-x 1.5`) gave 3.59 V, the extracted layout 3.58 V.
3. **The package short now adds little.** With VSS and IOVSS on the paddle the worst core-rail quantity is 3.44 V, in a signal pin - vs vdd.
4. **HV is at the limit, not over it, up to RON 1**, as before: a pad diode plus the iovdd clamp, on positive signal zaps against VDD. 10.04 V at RON 2 (5 zaps), 10.6 to 11.2 V at RON 4. It follows RON, so a TLP number for `DCPDiode` decides it.
5. **The ring metal costs about 0.5 V on the rail and 0.7 V on the pads.** With every rail one node, VDD + vs VSS gives 3.10 V (3.58 extracted) and the pads 10.8 / -9.7 V (11.5 / -9.8).

## How to run it

Everything runs in `hpretl/iic-osic-tools:2026.09` (kpex 0.4.4, KLayout 0.30.12, ngspice-47, PDK c271a7e), not in the 2026.08 sign-off image: 2026.08 has kpex 0.3.15, which the extraction wrapper does not support, and its IO netlist `sg13cmos5l_io.spi` carries no substrate ties. The run directory `verification/esd/run/` is git-ignored. The summaries land in `verification/esd/`.

```bash
R=verification/esd/run
python3 scripts/esd/models.py --selftest; python3 scripts/esd/pex.py --selftest
python3 scripts/esd/check.py --selftest; python3 scripts/esd/hbm.py --selftest   # tester against JS-001
ESD_NJOBS=6 python3 scripts/esd/pex.py $R all          # clip, kpex, Kron reduction (55 min, 15 GB)
python3 scripts/esd/models.py $R/sim                     # IO netlist with high-current diodes
python3 scripts/esd/check.py $R --ron 1 [--pkg-gnd]      # static path check (seconds)
python3 scripts/esd/check.py $R --without iovdd_w5       # must fail: exits 1
python3 scripts/esd/check.py $R --without clamp          # the clamp cell left out
for r in 0.5 1 2 4; do
  python3 scripts/esd/hbm.py $R --ron $r --jobs 6 [--pkg-gnd]
  python3 scripts/esd/report.py $R --ron $r [--pkg-gnd] --json verification/esd/esd_hbm_r$r[_pkg].json
done
python3 scripts/esd/hbm.py $R --ron 1 --ideal-ring --jobs 6    # the no-metal reference
python3 scripts/esd/report.py $R --tables [--pkg-gnd]           # the tables below
```

The scripts are ported from OpenBLAU (`scripts/esd/`, `scripts/spicerun.py`, commit 8f25e634). Its RF pad, the RF pad's clamp, the RF driver and VMON are gone, and the core model is DSA1's own.

## What is simulated

**The pad ring and core ring as extracted metal.** `scripts/esd/ring_clip.py` flattens the unfilled GDS `layout/sg13cmos5l_dsa1_dig_top.gds.gz` (md5 `3c136e848ce67988e27ee3f9d3403f09`, v1.1.1) outside the core box (x, y in [364.5, 1235.0]), Metal1 to TopMetal1 with every via, and keeps the metal of the nets that carry ESD current, found by one `LayoutToNetlist` run probed at the ports. Fill is isolated metal and is left out.

| port | where | what attaches |
|---|---|---|
| `<rail>_<slot>` | every rail band of a pad cell, at the cell's centre line | that pad cell's rail pin |
| `pad_<slot>` | the bond pad plate, at the chip's own pad label | the tester |
| `padc_<slot>` | the pad cell's pad strip | the pad cell's pad pin |
| `<rail>ring_<k>` | the core ring, 8 points per rail | core decap, core well, the core cells behind the pads |
| `clv_clamp`, `cls_clamp` | every Metal2 stripe of the clamp cell, vdd and vss, at the fingers' centroid | the clamp, `esd_clamp_vddvss_cell` in `models.py` |
| `<rail>_clamp` | the clamp cell's rail bands | nothing, ring metal |

Slots are numbered per side in their order, IO pad cells only, so the clamp cell takes no slot number. Slots are named after the signal (`miso`, `adcconv`, `tst0` to `tst15` for `o_tst_ctrl`, `datain`, `sclk`, `mosi`, `ss`, `rstn`, `clk`, `ana0`, `ana1`, `bidir0`, `bidir1`) or after the supply and its place (`vss_w2`, `vdd_w3`, `iovss_w4`, `iovdd_w5`). The core ring is Metal4 on W and E and TopMetal1 on S and N, vdd the inner ring on every side, and it is one net with the pad ring's vdd and vss bands. The clip asserts that no two nets share metal, that every pad slot and the clamp cell have a port on all four rails, and that every clamp stripe port sits on its rail's metal. No rail splits into islands.

kpex 2.5D extracts the clip R-only through `scripts/esd/kpex_cmos5l.py --wires --mode R`, and `scripts/esd/pex.py` reduces it onto the 214 port nodes (723 labels, repeated names joined) by Kron reduction, exact at DC: 927,331 resistors to 948 branches. The reduced network is `verification/esd/esd_ring_rport.spice`.

Checks of the reduction on the v1.1.0 ring, two-port resistance, full network against reduced: `pad_iovdd_w5` to `iovdd_tst9` 0.30034 / 0.30035 ohm, `pad_vdd_w3` to `vddring_6` 1.41276 / 1.41276, `pad_vss_w2` to `vss_tst15` 1.56805 / 1.56805, `pad_iovss_w4` to `iovss_ana0` 0.30818 / 0.30818. Against a hand estimate: IOVDD from W5 to S6 (`tst9`) runs 1283 um on Metal3, Metal4 and TopMetal1 (two 25.5 um bands each, 88 / 88 / 18 mohm/sq from kpex's tech) and 80 um without TopMetal1 through `IOPadVdd`, 0.390 ohm, in parallel with 3177 um the long way round, 0.796 ohm: 0.262 ohm. With about 0.035 ohm from the bond pad's centre to the band (127 um of 65 um TopMetal1) that is 0.297 against 0.300 extracted.

**Every pad cell at transistor level**, from the PDK's `sg13cmos5l_io.spice` in 2026.09, which carries the substrate (`sub!`) and its ptap ties. The chip was built with the 2026.08 PDK, whose `.spi` describes the same ESD devices (checked: `Clamp_N43N43D4R` 756.8 um of `sg13_hv_nmos` at L 0.6 um, `Clamp_N15N15D` 66 um, `Clamp_P15N15D` 199.8 um, `DCNDiode` and `DCPDiode` 2 x 35 um^2, the secondary protection's rppd and diodes, the trigger inverter, all equal) but no substrate. The IO GDS differs between the two images (md5), the LEF does not. The IO library clamps vdd to iovss in `IOPadVdd` and iovdd to iovss in `IOPadIOVdd`, and no cell clamps vdd to vss: a vdd-to-vss discharge has to stack the vdd clamp and the `IOPadVss` diode from iovss into vss. DSA1 has one `IOPadVdd` and one `IOPadIOVdd`.

**The clamp cell** at transistor level from its schematic devices: `sg13_hv_nmos` 2268/0.6 um, the 126/9.5 um MOS capacitor, IHP's inverter (108/0.5 and 350/0.5 um), the 129.3 kOhm rppd trigger, between `clv_clamp` and `cls_clamp`.

**The core**, DSA1's own:

| part | value | source |
|---|---|---|
| core-rail decap | 749.9 pF in three banks, split over the 8 core-ring points: `DECAPHV32` 7530 cells x 79.01 fF = 594.95 pF, `DECAPHV16` 3938 x 30.52 fF = 120.19 pF, `DECAPHV8` 5541 x 6.272 fF = 34.75 pF | cell counts from `netlist/pnl/sg13cmos5l_dsa1_dig_top.pnl.v` (7399, 3434, 3916) plus `macros/dsa1_dig/final/pnl/dsa1_dig_top.pnl.v` (131, 504, 1625). C per cell: the `$DECAPHV_DIR/cdl/ez130_8t_decap_hv.cdl` device (one `sg13_hv_pmos`, W 1.66 um, L 0.82 / 4.18 / 10.9 um, gate on VSS) in ngspice, AC at 1 MHz biased at 1.2 V, tt. It moves under 4 % up to 5 V. The liberty has no capacitance. |
| decap series R | per bank 1 / (2 pi f_c C): 4.459, 3.311 and 0.458 ohm, plus 0.5 ohm for the whole bank (assumption) | f_c is the decap library's own channel-corner estimate, 60 MHz, 0.4 GHz and 10 GHz (`$DECAPHV_DIR/doc/decap_hv.md`) |
| core n-well junction | a high-current diode vss to vdd of 20000 um^2, split over the 8 points | assumption, as in OpenBLAU: a bound, not measured |
| output pads (18) | the macro's `BUFX3` that drives `c2p`, input at its vss (unpowered core), on the nearest core-ring point | `macros/dsa1_dig/final/pnl`: every `miso`, `adc_conv` and `o_tst_ctrl` output is a `BUFX3`. Devices from `$EZ130_DIR/cdl/ez130_8t.cdl`. |
| bidir spares (2) | `TIELO` on `c2p` and on `c2p_en`, nearest core-ring point. `p2c` is open in the core, given 50 fF. | `netlist/pnl` |
| inputs (6) | 50 fF from `p2c` to the nearest core-ring vss point: a core gate | assumption, as in OpenBLAU |
| analog spares (2) | `padres` is open in the core, 50 fF to the slot's iovss | `netlist/pnl` |

**The tester**: 100 pF, 1.5 kohm, 5 uH, 1 pF at the pin. Into a short at 2 kV it gives 1.247 A peak, 7.86 ns rise and 154.0 ns decay, inside JS-001 (`hbm.py --selftest` asserts it). The reference pins sit at 0 V through 1 mohm, every other pin floats.

**High-current diodes.** The PDK's `dantenna`/`dpantenna` cards are fitted for reverse bias and read kilovolts at an ampere, so `models.py` swaps each for a level-1 diode with the PDK's saturation current, ideality, junction C and breakdown per area, and `rs = RON` per 35 um^2, scaled by area. RON is unknown for this process and is swept: 0.5, 1, 2, 4 ohm. The RC-triggered rail clamps stay PSP: they conduct as a MOSFET, which PSP models. Snapback, avalanche and oxide breakdown are not modelled, so nothing fails by itself here and the limits are indicative.

| class | quantity | indicative limit |
|---|---|---|
| LV, 1.2 V devices | core-ring vdd - vss (`core_vdd_vss_k`), every slot's vdd - vss (`vdd_vss@slot`), `c2p`, `c2p_en`, `p2c` against the slot's vdd and vss (the pad cell's level shifter gates and LevelDown output) and against the core-ring point their core cell sits on (`*_core@`, `core_*@`) | 4.5 V |
| HV, 3.3 V devices | iovdd - iovss, pad against either IO rail, the secondary-protected input node and `padres` against either IO rail, vdd - iovss (the vdd clamp) | 10 V |

On a supply slot the pad strip is that supply, so `pad_iovdd@vdd_w3` is vdd - iovdd at the VDD pad.

**The matrix**, JS-001 pin combinations, both polarities. Die only: 28 signal pins against each of the 4 supply groups (224), the supply groups against each other (12), each signal pin against all other signal pins tied (56): 292. Every zap runs 80 ns with `.options cshunt=1e-16 rshunt=1e9 method=gear`, `uic`, one thread per ngspice, 6 in parallel.

**VSS = IOVSS in the package (`--pkg-gnd`).** `packaging/config.yaml` puts VSS and IOVSS in `EPAD_NETS`: both pads downbond to the paddle and leads 5 and 7 bond to it. JS-001 then sees one pin group `gnd`, zapped or referenced at the package node, which each of the two pads reaches through its own downbond, modelled as 0.5 nH and 0.05 ohm (500 um of 25 um gold, `packaging/result.md`). The matrix drops to 230 zaps. A `gnd` zap is listed under `iovss_w4`.

## Results, die only

| | RON 0.5 | RON 1 | RON 2 | RON 4 |
|---|---|---|---|---|
| zaps run / of | 292 / 292 | 292 / 292 | 292 / 292 | 292 / 292 |
| retried: 0.02 ns step / trap / cshunt | 33 / 10 / 2 | 36 / 9 / 1 | 37 / 6 / 0 | 44 / 7 / 0 |
| still rising past half the window | 30 | 30 | 30 | 30 |
| pad, max / min V | 11.3 / -9.5 | 11.5 / -9.8 | 12.1 / -10.4 | 13.3 / -11.7 |
| worst LV V | 3.58 | 3.58 | 3.58 | 3.58 |
| worst LV V: node, zap | `vdd_vss@vss_w2`, `vdd_w3` + vs vss | `vdd_vss@vss_w2`, `vdd_w3` + vs vss | `vdd_vss@vss_w2`, `vdd_w3` + vs vss | `vdd_vss@vss_w2`, `vdd_w3` + vs vss |
| worst HV V | -9.79 | -9.72 | 10.04 | 11.23 |
| worst HV V: node, zap | `pad_iovdd@vdd_w3`, `tst0` + vs vdd | `pad_iovdd@vdd_w3`, `miso` + vs vdd | `pad_iovss@ana0`, `ana0` + vs vdd | `pad_iovss@ss`, `ss` + vs vdd |
| zaps with an LV node over 4.5 V | 0 | 0 | 0 | 0 |

The worst LV quantity of every signal pin is 3.4 V, in its zap negative against VDD. `python3 scripts/esd/report.py verification/esd/run --tables` prints the per-pin table.

## Results, VSS = IOVSS in the package

| | RON 0.5 | RON 1 | RON 2 | RON 4 |
|---|---|---|---|---|
| zaps run / of | 230 / 230 | 230 / 230 | 230 / 230 | 230 / 230 |
| retried: 0.02 ns step / trap / cshunt | 35 / 7 / 1 | 33 / 4 / 0 | 40 / 2 / 1 | 54 / 1 / 0 |
| still rising past half the window | 0 | 0 | 0 | 0 |
| pad, max / min V | 10.8 / -9.5 | 11.1 / -9.8 | 11.7 / -10.4 | 12.9 / -11.6 |
| worst LV V | 3.44 | 3.44 | 3.44 | 3.44 |
| worst LV V: node, zap | `vdd_vss@tst1`, `bidir1` - vs vdd | `vdd_vss@tst1`, `bidir1` - vs vdd | `vdd_vss@tst1`, `bidir1` - vs vdd | `vdd_vss@tst1`, `ana1` - vs vdd |
| worst HV V | -9.41 | 9.33 | 9.92 | 11.09 |
| worst HV V: node, zap | `pad_iovdd@vdd_w3`, `rstn` + vs vdd | `pad_iovss@ana1`, `ana1` + vs vdd | `pad_iovss@ana1`, `ana1` + vs vdd | `pad_iovss@ss`, `ss` + vs vdd |
| zaps with an LV node over 4.5 V | 0 | 0 | 0 | 0 |

## Static path check

`scripts/esd/check.py` flattens the same netlists into a graph of forward diodes, rail clamps, substrate ties and the extracted metal, and prices each pairing's cheapest path at the HBM peak current, 1.33 A: 0.7 V plus RON per diode, a clamp's V0 + R*I, metal I*R. It follows one path, so it reads higher than the transient where current shares pads.

Rail clamp, calibrated from two zaps on `IOPadIOVdd` alone: V = 2.48 V + 4.16 ohm * I. The clamp cell is priced as three of them in parallel, V = 2.48 V + 1.39 ohm * I.

| | RON 0.5 | RON 1 | RON 2 | RON 4 |
|---|---|---|---|---|
| die only: pairings with a path | 292 of 292 | 292 of 292 | 292 of 292 | 292 of 292 |
| die only: worst path V (`tst12` + vs vdd) | 13.27 | 15.34 | 18.12 | 21.83 |
| die only: VDD + vs VSS, V (the clamp cell alone) | 6.76 | 6.76 | 6.76 | 6.76 |
| VSS = IOVSS: pairings with a path | 230 of 230 | 230 of 230 | 230 of 230 | 230 of 230 |
| VSS = IOVSS: worst path V (`tst12` + vs vdd) | 13.27 | 15.34 | 16.56 | 18.93 |

Without the clamp cell (`--without clamp`) VDD + vs VSS goes back to one IOPadVdd clamp and one diode, 10.21 V at RON 1, and every pairing still has a path: the cell lowers the voltage, it adds no path that was missing.

**It can fail, and does where it should.** Without the `IOPadIOVdd` cell's devices (`--without iovdd_w5`) 171 of 292 pairings have no path, and it exits 1. Results in `verification/esd/check_r*.json`.

## Numerics and runtime

Each deck runs 80 ns. A deck that stops on "Timestep too small" retries with a 0.02 ns step, then `method=trap`, then 1 fF and 3 fF `cshunt` (`hbm.RETRY`), and records the rung. Priced on `miso` - vs io at RON 1, which converges as is: the finer step moves its extremes by 4 mV, trap by 2 mV, 1 fF by 0.116 V, and 3 fF aborts, so the cshunt rungs come last. None of the 2128 decks aborted, 5 needed 1 fF.

30 zaps per die-only run flag a quantity still rising past half the window, all with VDD as the reference: floating IO rails and core-side nodes relaxing after the zap. On v1.1.0 two such zaps rerun to 300 ns moved no extreme by more than 0.18 V.

Runtime, 2026-10-08 in the 2026.09 image at 6 ngspice in parallel: the extraction and reduction about 1.2 h, then 1.7 to 2.6 h per RON die only and with the short, 20.3 h for the whole sweep with the ideal ring.

## Open

- **RON and the limits need a source.** A TLP curve of `DCNDiode` and `DCPDiode` and IHP's transient oxide and snapback numbers for the LV and HV devices would turn the bands into a verdict. 4.5 V and 10 V are indicative.
- **Assumptions to check:** the core n-well junction (20000 um^2), the decap banks' series R, and the 50 fF input loads. The core sits at 8 points on the core ring, the core grid between them is not modelled.
- **Not modelled:** substrate resistance between pads (one `sub!` node), the corner and filler cells' substrate ties, the routes from pads to the core, CDM, and metal current density at 1.3 A.
