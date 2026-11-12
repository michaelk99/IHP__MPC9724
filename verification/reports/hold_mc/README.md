<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->
# Hold Monte Carlo of the worst hold path, 2026-11-07

STA at max RC, the worst of the four R and C combinations in `../sta_rc_corners/`, puts the chip's worst hold slack at +0.0516 ns, fast corner (1.32 V, -40 C), with no OCV derate, only `set_clock_uncertainty -hold 0.05`. This bench states that margin in sigma of local transistor mismatch. Read only, the layout and the GDS are untouched.

## Result

Hold slack in ps without the 50 ps clock uncertainty, `results.txt`:

| set | runs | nominal | mean | sigma | min | sigmas to 0 | sigmas to 50 ps |
|---|---|---|---|---|---|---|---|
| `mos_ff_mismatch`, 1.32 V, -40 C | 500 | 98.3 | 98.3 | 5.30 | 85.6 | 18.6 | 9.1 |
| `mos_tt_mismatch`, 1.20 V, 27 C | 200 | 149.9 | 149.5 | 9.25 | 130.8 | 16.2 | 10.8 |

"Sigmas to 0" counts the 50 ps uncertainty as margin, "sigmas to 50 ps" keeps it reserved, where the STA slack would reach zero. Both are mean over sigma. With 500 runs sigma is known to about 3 % (18.0 to 19.2 and 8.8 to 9.4 at one standard error), and the runs say nothing about a tail beyond the Gaussian shape. No run failed functionally, every hold search ended inside its window, and the slack has no visible tail (skewness 0.08 and 0.04, worst run 2.4 sigma under the mean in 500).

Sigma split at ff in ps: skew 3.52, launch CK to Q 2.72, hold requirement 2.63. Their root sum of squares is 5.17 against the measured 5.30, so the three are nearly independent. Skew is the largest part since the two leaf buffers carry their own mismatch.

The tt set is a comparison only, on the ff bench as is (ff liberty pin caps, the 32 ps clock ramp of the ff report).

## The path

From `verification/reports/sta_rc_corners/chip/nom_fast_1p32V_m40C/max/worst_hold.rpt`, path group clk, inside `dsa1_dig`: launch `_20056_` (DFFRQX1) Q straight into D of `_20057_` (DFFRQX1). The clock splits after `clkbuf_1_0__f_clk_regs` (CRPR 17.7 ps). Launch leaf `clkbuf_leaf_17_clk_regs`, capture leaf `clkbuf_leaf_16_clk_regs`.

## Bench

- Transistor level in ngspice: the common buffer `clkbuf_1_0__f_clk_regs`, both leaf buffers (BUFX12), launch and capture flop (DFFRQX1). Cells from `ip/ez130_8t_v1p1/cdl/ez130_8t.cdl` through the library's `scripts/cdl2spice.py`, every device `sg13_lv_nmos` or `sg13_lv_pmos` with `mm_ok=1` added (`gen_bench.py`).
- Wires: the four nets of the path (common net, both leaf nets, launch Q) from the macro SPEF the chip STA reads, `macros/dsa1_dig/final/spef/nom/dsa1_dig_top.nom.spef`, as RC networks with R and C scaled by 1.2 like the max RC STA. Coupling caps are grounded. The 28 load pins outside the bench are their ff liberty pin caps.
- Clock: a 32 ps PWL ramp (20 to 80 %, the report's slew at the common buffer input) into the common buffer, so the common node carries a real buffer edge. Its mismatch is common to both branches.
- Corner `mos_ff_mismatch`, 1.32 V, -40 C. The bench has no resistor or capacitor devices, so no RES or CAP corner applies.
- Mismatch is on through `mm_ok=1` on every device line (the subckt default is 0). Seeds give different delays, and a seed reproduces bit for bit, also across hosts.

## Method

Per seed one ngspice process (`hold.ctl`):

1. Path run: launch D is 1 at clock edge 1 and 0 at edge 2, so launch Q falls at edge 2 as in the report. At edge 2 it measures at 50 % of supply the skew (capture CK minus launch CK), launch CK to Q at the capture D pin, and arrival at D minus capture CK, and checks that the capture flop held 0 before and took 1 after.
2. Hold search in the same loaded circuit, so the same mismatch sample: launch Q is cut off capture D, and an ideal ramp with the measured launch Q slew drives D, falling at capture CK plus tau. The capture flop is reset before the edge with D at 1, so a pass is Q at 1 after the edge. Bisection on tau, 11 halvings of -40 to 90 ps, 0.06 ps step. The hold requirement is the smallest passing tau, the pass or fail point, not a CK to Q push-out criterion.
3. Slack = arrival at D minus capture CK minus hold requirement, without the 50 ps uncertainty.

`summarize.py` turns the RESULT lines into `results.txt`.

## Sanity against STA

Nominal run, `mos_ff` without mismatch, against the max RC report. Times in ps, each branch from the common node `clkbuf_1_0__f_clk_regs/Y`.

| quantity | STA | spice | spice minus STA |
|---|---|---|---|
| launch branch, common node to launch CK | 113.2 | 123.6 | +10.4 |
| capture branch, common node to capture CK | 140.7 | 143.2 | +2.5 |
| skew | 27.5 | 19.6 | -7.9 |
| launch CK to Q at capture D | 151.9 | 141.9 | -10.0 |
| arrival at D minus capture CK | 124.4 | 122.3 | -2.1 |
| hold requirement | 22.8 | 23.9 | +1.1 |
| slack without the 50 ps uncertainty | 101.6 | 98.3 | -3.3 |

The slack lands 3.3 ps under STA. The parts move by up to 10 ps and partly cancel:

- Launch branch +10.4 ps: STA times the launch side early, with the minimum CK pin cap of the liberty range (1.20 against 1.69 fF on 12 flops of the leaf net, 5.9 fF less on 31 fF) and the early slew at the common node (89 against 98 ps late). The bench has one edge, 102 ps at the common driver, and 1.69 fF on every load pin.
- CK to Q -10 ps: the cells are the schematic CDL, the liberty was characterised from the extracted layout.
- Hold requirement +1.1 ps: the bench takes the pass or fail point, the liberty its own characterisation criterion, and the cells differ as above.

Launch Q slew at D is 17.3 ps (STA 19.7).

## Command

Images of `scripts/image.env`. These runs used the ARM64 compute host in `IMAGE_ARM64` (PDK `ihp-sg13cmos5l` a49358c, model cards identical to the 5eddf3e of `IMAGE_AMD64`, OSDI models compiled for aarch64, ngspice-47 in both), 6 parallel ngspice. The nominal run and seeds 5 and 6 gave the same digits on the laptop (`IMAGE_AMD64`).

```sh
H=verification/reports/hold_mc
python3 $H/gen_bench.py $H/runs/ff/path.spice     # also done by run_mc.sh when missing
scripts/in_image.sh "$H/run_mc.sh $H/runs/ff mos_ff -40 1.32 1 1 1 && $H/run_mc.sh $H/runs/ff mos_ff_mismatch -40 1.32 1 500 6"
scripts/in_image.sh "$H/run_mc.sh $H/runs/tt mos_tt 27 1.2 1 1 1 && $H/run_mc.sh $H/runs/tt mos_tt_mismatch 27 1.2 1 200 6"
python3 $H/summarize.py ff $H/runs/ff/results_mos_ff_-40.txt $H/runs/ff/results_mos_ff_mismatch_-40.txt \
  tt $H/runs/tt/results_mos_tt_27.txt $H/runs/tt/results_mos_tt_mismatch_27.txt > $H/results.txt
```

`run_mc.sh` needs `PDK=ihp-sg13cmos5l`, which `in_image.sh` sets, since the image's `.spiceinit` loads the OSDI models from it. One sample takes about 20 s on one core of the ARM64 compute host, about 50 s on the loaded laptop.

## Limitation

- Local mismatch around the fixed ff corner only. The PDK has no combined global plus local Monte Carlo for MOS (`doc/ihp-sg13cmos5l-Open-PDK/sg13cmos5l_ngspice_mc_mm_guide.md`, section 7), so global spread is covered by the corner and local by this run, not both in one draw.
- The cell netlists are the schematic CDL without layout parasitics, so cell delays here are some ps faster than the liberty, which was characterised from the layout.
- Wire RC is OpenRCX nominal scaled by 1.2, not a foundry RC corner.
- Mismatch sigmas are IHP's SG13G2 values that the SG13CMOS5L model set inherits.
