<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# STA at min and max RC, 2026-11-07

Static timing of the signed-off chip and of the `dsa1_dig` macro at the three PVT corners, each with min, nominal and max parasitics, and on 2026-11-08 with R and C scaled apart. Read only, the layout and the GDS are untouched. No slack is negative.

The PDK ships one OpenRCX rules file, `libs.tech/librelane/IHP_rcx_patterns.rules`, which is the nominal one. It has no min or max rules. So min and max here are the signed-off nominal SPEF with every wire R and C scaled by 0.8 and 1.2 (`scale_spef.py`), and `r08c12` and `r12c08` are R 0.8 with C 1.2 and R 1.2 with C 0.8. That brackets a global wire spread, it is not a foundry RC corner. One factor applies to the whole SPEF, so the launch and capture clock branches always move together. No run here bounds a split between the two branches, which is what makes hold worse on silicon. The hold Monte Carlo in `../hold_mc/` covers the device side of that split, not wire variation.

Nominal reproduces hold and the violation counts of the signed-off chip run exactly. The macro alone at nominal equals the macro's own signed-off `macros/dsa1_dig/verification/stapostpnr_summary.rpt` (run `RUN_2026-10-31_16-16-30`, d74afa2) to all 4 printed digits: setup 47.3646, 45.9506, 43.6389 ns, hold 0.0443, 0.1120, 0.2056 ns, 2 max-cap items at the fast corner, 193 max-slew items at the slow corner. The chip setup slacks are 0.013 to 0.023 ns lower than the recorded 47.355, 45.934 and 43.608 ns. The cause is in the clock network: this run leaves 24 drivers partially annotated (`annotation.rpt`) against 6 in the signed-off step, among them the `sclk` pad's output net, which it loads with 8.5 fF instead of 69.3 fF. On the worst setup path (`_18506_` to `_18280_`, the same path as signed off) the launch clock then arrives 49 ps and the capture clock 72 ps earlier than in the signed-off `max.rpt`, which is the 23 ps. The scaled runs carry the same gap.

## Result

Worst slack in ns over all paths, uniform scaling first. The max-cap, max-slew and max-fanout columns are violation counts of the STA, not of a gate. The chip has 190 max-fanout items at every corner, the same 190 as in the signed-off `checks.rpt`, all inside the macro.

| design | corner | RC | setup | hold | max cap | max slew | max fanout |
|---|---|---|---|---|---|---|---|
| chip | fast 1.32 V -40 C | min | 47.628 | 0.0591 | 0 | 0 | 190 |
| chip | fast 1.32 V -40 C | nom | 47.342 | 0.0551 | 2 | 0 | 190 |
| chip | fast 1.32 V -40 C | max | 47.064 | 0.0516 | 4 | 0 | 190 |
| chip | typ 1.20 V 25 C | min | 46.382 | 0.1178 | 0 | 0 | 190 |
| chip | typ 1.20 V 25 C | nom | 45.918 | 0.1120 | 0 | 0 | 190 |
| chip | typ 1.20 V 25 C | max | 45.469 | 0.1068 | 2 | 0 | 190 |
| chip | slow 1.08 V 125 C | min | 44.343 | 0.2125 | 0 | 3 | 190 |
| chip | slow 1.08 V 125 C | nom | 43.585 | 0.2056 | 0 | 3 | 190 |
| chip | slow 1.08 V 125 C | max | 42.838 | 0.1971 | 2 | 3 | 190 |
| macro | fast 1.32 V -40 C | min | 47.648 | 0.0254 | 0 | 0 | 2 |
| macro | fast 1.32 V -40 C | nom | 47.365 | 0.0443 | 2 | 0 | 2 |
| macro | fast 1.32 V -40 C | max | 47.091 | 0.0516 | 4 | 0 | 2 |
| macro | typ 1.20 V 25 C | min | 46.412 | 0.1037 | 0 | 0 | 2 |
| macro | typ 1.20 V 25 C | nom | 45.951 | 0.1120 | 0 | 0 | 2 |
| macro | typ 1.20 V 25 C | max | 45.506 | 0.1068 | 2 | 34 | 2 |
| macro | slow 1.08 V 125 C | min | 44.393 | 0.2125 | 0 | 84 | 2 |
| macro | slow 1.08 V 125 C | nom | 43.639 | 0.2056 | 0 | 193 | 2 |
| macro | slow 1.08 V 125 C | max | 42.895 | 0.1971 | 2 | 285 | 2 |


R and C apart, 2026-11-08:

| design | corner | RC | setup | hold | max cap | max slew | max fanout |
|---|---|---|---|---|---|---|---|
| chip | fast 1.32 V -40 C | R 0.8 C 1.2 | 47.072 | 0.0526 | 4 | 0 | 190 |
| chip | fast 1.32 V -40 C | R 1.2 C 0.8 | 47.621 | 0.0581 | 0 | 0 | 190 |
| chip | typ 1.20 V 25 C | R 0.8 C 1.2 | 45.476 | 0.1077 | 2 | 0 | 190 |
| chip | typ 1.20 V 25 C | R 1.2 C 0.8 | 46.375 | 0.1168 | 0 | 0 | 190 |
| chip | slow 1.08 V 125 C | R 0.8 C 1.2 | 42.846 | 0.1980 | 2 | 3 | 190 |
| chip | slow 1.08 V 125 C | R 1.2 C 0.8 | 44.336 | 0.2116 | 0 | 3 | 190 |
| macro | fast 1.32 V -40 C | R 0.8 C 1.2 | 47.095 | 0.0526 | 4 | 0 | 2 |
| macro | fast 1.32 V -40 C | R 1.2 C 0.8 | 47.644 | 0.0171 | 0 | 0 | 2 |
| macro | typ 1.20 V 25 C | R 0.8 C 1.2 | 45.509 | 0.1077 | 2 | 34 | 2 |
| macro | typ 1.20 V 25 C | R 1.2 C 0.8 | 46.408 | 0.0954 | 0 | 0 | 2 |
| macro | slow 1.08 V 125 C | R 0.8 C 1.2 | 42.899 | 0.1980 | 2 | 283 | 2 |
| macro | slow 1.08 V 125 C | R 1.2 C 0.8 | 44.390 | 0.2100 | 0 | 84 | 2 |

For the chip, uniform max RC stays the worst of the four for both setup (slow corner, 42.838 ns) and hold (fast corner, 0.0516 ns). The macro alone has its worst hold at R 1.2 C 0.8, +0.0171 ns at the fast corner, on the input `ss` to `_18259_` in the sclk group, against the input delay the macro SDC assumes. In the chip that port comes from its pad, and the chip's sclk group stays at +0.0690 ns at the same corner and RC. The macro's register to register worst hold path, `_20056_` to `_20057_`, gives the chip's values at every RC (0.0516 ns at max RC). The design is capacitance dominated: C 1.2 with R 0.8 comes within 0.01 ns of max RC, R 1.2 with C 0.8 within 0.01 ns of min RC.

Worst hold path at the fast corner and min RC, chip: clk group, register `i_sg13cmos5l_dsa1_dig_core.dsa1_dig/_20056_` to `_20057_` inside the macro, slack +0.0591 ns. It is the worst path at max RC too (+0.0516 ns). The sclk group is worst at +0.0697 ns, input hold against `sclk` at +0.34 ns. The full path is in `chip/nom_fast_1p32V_m40C/min/worst_hold.rpt`.

The chip's max-cap items are the two SPI register flops `_18515_` and `_18516_` of `dsa1_dig` that the audit table already accepts. Max RC and R 0.8 C 1.2 at the fast corner add two more flops of `dsa1_dig`, `_18510_` and `_18513_`, at 100.8 and 100.5 fF against the 95 fF limit (`chip/nom_fast_1p32V_m40C/max/checks.rpt`). The chip's 3 max-slew items at the slow corner are the same at every RC. The macro alone counts 193 slew items at the slow corner at nominal as signed off, 84 at min RC and 285 at max RC, and 34 at the typical corner with C 1.2.

## Command

The pinned sign-off image of `scripts/image.env` (PDK 5eddf3e), one throwaway container through `scripts/in_image.sh`, scratch under the gitignored `runs/`:

```sh
scripts/in_image.sh 'export WORK=/foss/designs/sg13cmos5l_dsa1_dig/runs/sta
  H=verification/reports/sta_rc_corners
  for d in macro chip; do $H/run_sta.sh $d all all
    for c in nom_fast_1p32V_m40C nom_typ_1p20V_25C nom_slow_1p08V_125C; do $H/run_sta.sh $d $c r08c12; $H/run_sta.sh $d $c r12c08; done; done'
```

`run_sta.sh` scales the SPEFs into `$WORK`, then runs `sta -no_splash -exit sta_corner.tcl` once per corner and RC. The Tcl mirrors LibreLane's OpenROAD.STAPostPNR step: same liberty files, netlists, SDC and parasitics, the macro SPEF read at `i_sg13cmos5l_dsa1_dig_core.dsa1_dig`. Per run, `summary.txt`, `worst_hold.rpt` and `worst_setup.rpt` (the worst path of each path group), `checks.rpt` (max slew, cap and fanout violators), `annotation.rpt` and `check_setup.rpt` are kept under `<design>/<corner>/<rc>/`. The chip's uniform runs were first made on 2026-11-07 and rerun on 2026-11-08 with identical `summary.txt`, `worst_hold.rpt` and `check_setup.rpt`. The macro-alone runs were all redone on 2026-11-08 from the taped-out views.

## Inputs

| input | md5 |
|---|---|
| chip final DEF, `flow/librelane/runs/RUN_2026-11-04_15-49-13/final/def/sg13cmos5l_dsa1_dig_top.def` | `578f9c05b6b4797ffa00186523e25e99` |
| chip top netlist, step `51-openroad-fillinsertion` | `04f51fb545387285fd0cbedf61927fdf` |
| chip top SPEF, step `53-openroad-rcx/nom` | `65c0d59b0db46a984bcbeac27fca2a16` |
| macro netlist, the taped-out view the chip and the macro alone read, `macros/dsa1_dig/final/nl/dsa1_dig_top.nl.v` | `a7f6aad12c17011d5578c11d362c99d2` |
| macro SPEF, read by the chip and the macro alone, `macros/dsa1_dig/final/spef/nom/dsa1_dig_top.nom.spef` | `a6ebe0ee2edf5bf41cf25b48686df452` |
| chip SDC, `flow/librelane/sg13cmos5l_dsa1_dig_top.sdc` | `1f6dfa54c5b0695c0bf2d60b4c8a2125` |
| macro signed-off STA summary, `macros/dsa1_dig/verification/stapostpnr_summary.rpt` | `239d83766371f91f212798abb12917e5` |
| macro SDC, `macros/dsa1_dig/flow/librelane/dsa1_dig_top.sdc` | `5c44a8a71f67acffb11901d9482fb7a2` |

The chip and the macro alone both read the taped-out macro views in `macros/dsa1_dig/final/`, the 409.08 x 514.08 um harden of `RUN_2026-10-31_16-16-30` (d74afa2), whose run folder is not kept. Until 2026-11-08 the macro alone was timed on `RUN_2026-09-30_13-54-33`, an earlier 497.28 um square harden that is not in the chip, and its rows here are replaced.
