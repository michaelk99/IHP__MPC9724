# Switched-Capacitor Common-Mode Feedback with MoM Capacitors

The common-mode feedback of `sc_int2`, the same network as `macros/cmfb_sc` with the four ideal capacitors replaced by `cap_cmomf` devices, since SG13CMOS5L has no MIM capacitor. `cmfb_sc` stays as it is for `sc_int` and the course modulator. **Schematic only, no layout cell, no testbenches and no CACE datasheet yet.** It is exercised through `sc_int2` (`macros/sc_int2`), whose layout places its devices.

The switches are `sw_tgate_cmfb2` from `macros/sw_tgate_cmfb2` (L = 1u on the sizing grid, with strip-end guards) and the clock inverters `inv_lv` from `macros/sw_tgate`. `cmfb_sc` keeps `sw_tgate_cmfb`. The switches move the refresh capacitor of about 43 fF (4 units of 10.66 fF), so their off leakage matters far more than their on resistance.

## Ports

| Port | Direction | Meaning |
| --- | --- | --- |
| `vo_p`, `vo_n` | inout | the OTA outputs, sensed |
| `vfb` | out | correction voltage, drives the OTA `vfb` input |
| `vbias` | in | the reference the correction settles to, normally the OTA `vbn` |
| `vcm` | in | target output common mode |
| `di_phi1`, `di_phi2` | in | the two non-overlapping clock phases (`vphi1`, `vphi2` in `cmfb_sc`) |
| `vdd`, `vss` | inout | inverter supply and switch control reference |

The symbol has no parameters. The capacitor values come from the unit counts below.

## Capacitors

| | device, Metal1 to Metal4 | C model | C estimated real | before in `cmfb_sc` |
| --- | --- | --- | --- | --- |
| sense `C1` (`vo_p` to `vfb`), `C3` (`vo_n` to `vfb`) | 3 `cap_cmomf` units each, `w` 3.0u, `l` 11.39u | 131.9 fF | 96.0 fF | 100 fF |
| refresh `C2`, `C4` | 4 `cap_cmomf` units each, `w` 3.0u, `l` 4.105u | 63.40 fF | 42.64 fF | 10 fF |

The sense unit is the unit of the `sc_int2` integrator capacitors, sized for 32 fF real. The `cap_cmomf` model (1.287 fF/um2 x l x w) reads high against a field solve, so the real values are estimated as in `macros/sc_int2` (README, Capacitors): the M2..M4 dead-rim fit scaled by the Palace solve of the M1..M4 shapes (EM over the fit 0.938 for the unit, 0.932 for the refresh shape, EM sim). **Simulations use the model value, about 1.37 x the estimate for the sense units and 1.49 x for the refresh cap.** The units are vector instances (`C1[2:0]`, `C2[3:0]`), one device each. `m=4` on one instance would simulate the same, but the PDK's KLayout LVS reader takes `m` of a capacitor line only for MIM caps, so LVS saw one unit.

Sense over refresh is 2.25 by the estimate and 2.08 by the model, against 10 in `cmfb_sc`. The refresh caps are 4 units since 2026-10-20 (1 unit before, ratio 9.00). The refresh unit is a separate shape, so the ratio is not exact by construction, and the CMFB does not need it to be.

`cap_cmomf` has no substrate node. The `cap_cmomi` devices this replaced hung their substrate shunt off MINUS, which is why the sense caps had MINUS on `vfb`. The schematic keeps PLUS on `vo_p`, `vo_n` and `vsw_cm_p`, `vsw_cm_n`, but nothing depends on it now, and the real plate to substrate capacitance comes from the extracted view of `sc_int2`.

## How It Works

Two continuous sense capacitors run from each output to `vfb`, so `vfb` follows the average of `vo_p` and `vo_n`. Two smaller refresh capacitors are charged to `vcm - vbias` during `di_phi2` and then placed between the outputs and `vfb` during `di_phi1`, which pulls the common mode towards `vcm` a little each cycle, about 1 / (1 + 2.25) of the error per cycle by the estimated values, 31 percent against 9.1 percent at ratio 10. The differential signal cancels in the sense pair, so the loop acts only on the common mode.

## Sizing

`scripts/sizing/size_cmfb_sc2.ipynb` derives the capacitor units, the switch size and the clock inverter check from the spec with the gm/ID tables of the course and compares them with the schematic. It was written after the schematic. It reproduces the refresh cap of 4 units (3 units for the common mode to settle to 1 % in 20 cycles, 4 for 15) and the k of 0.31 per cycle, and shows that Ron (5.6 kOhm worst case) and the inverter delay (123 ps) leave a margin of hundreds of time constants. The main disagreements: the 1u/3u switch is 2 times wider than Ron needs, the sense caps reach `vfb` through a divider of 0.57 because the OTA sinks put about 148 fF on it, and the cycle count and the leakage limit are assumptions of the notebook because neither README states one. There is no standalone simulation of the common-mode loop to compare with.

## Where This Comes From

A renamed copy of `macros/cmfb_sc` (`make macro FROM=cmfb_sc NAME=cmfb_sc2`), which came from `sg13g2_pipeadc_3b/xschem/cmfb_sc.sch`.

## What Is Missing

- Layout, testbenches and a CACE datasheet.
- A check of the CMFB loop gain and settling on its own. `sc_int2` runs it inside the integrator.
