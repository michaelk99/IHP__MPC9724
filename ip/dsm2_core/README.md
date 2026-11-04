# dsm2_core

Views of the dsm2 first-order DT delta-sigma modulator, 150.5 x 178 um. GDS, LEF and CDL are dsm2's own, copied byte for byte and never edited here.

These are dsm2's oscillator variant views of 2026-11-02, the views that tape out. They carry the quantizer2 latch preset fix and four oscillator pins. The baseline views of the same day stay outside the repo as the fallback. The views of 6dd2926 (2026-10-29) are in git history.

| File | md5 | Source |
| --- | --- | --- |
| `gds/dsm2_core.gds` | `00624787128efe33ca6ddf5273170e56` | dsm2 delivery 2026-11-02, `dsm2_core_variant`, top cell `dsm2_core` |
| `lef/dsm2_core.lef` | `042ec97848217f9a30e94a391885b839` | same delivery, the variant LEF agreed on 2026-10-31 |
| `cdl/dsm2_core.cdl` | `5df9700351cb3b2c1804480eb62dfc12` | same delivery, the LVS netlist without the xschem path comments, 48 subckts |
| `spice/` | `MD5SUMS` there | same delivery, its ngspice bundle: schematic `dsm2_core`, extracted `dsm2_core_pex` (Magic full RC of this GDS), header, smoke benches, see `spice/README.md` |

dsm2's own LVS of these views, read at intake, kept with the delivery outside the repo (`lvs/`):

- `klayout_lvs.log`: KLayout 0.30.12, "Netlists match", 0 errors.
- `netgen_lvs.out`: Magic and Netgen, "Circuits match uniquely", 1477 devices and 696 nets on both sides. The 2753 property errors are all `mm_ok` on schematic devices, a model flag the extraction does not carry.

Both logs are dated 2026-10-31 02:25 and name `layout/dsm2_core.gds` without an md5. The chip's top LVS compares this GDS device by device against this CDL (`verification/lvs/`).

| File | What it is |
| --- | --- |
| `verilog/dsm2_core.v` | Blackbox with 21 ports, 25 pin bits: the 17 agreed ports and the four oscillator ports appended. dsm2's `dsm2_core.vh` has the same names and widths, its baseline part in another order, the four oscillator ports appended after `ibias_test` as here after `do_q_dec` |
| `verilog/dsm2_core_model.v` | Bench-only model: PRBS15 (`x^15 + x^14 + 1`, seed 1) on `di_clk`, not the circuit |
| `abstract/check_pins.py` | LEF pins against the blackbox ports |

Pins, from the LEF: all Metal3.
East edge from the bottom: `vi` at 3.0 um, `vcm` 8.5, `ibias_test` 14.0, `vdd` 36 to 46, `vss` 50 to 60.
South edge: `di_clk`, `do_q` and `do_q_b` centred at x 97.27, 99.96 and 102.65 um.
West edge: the controls at 2.69 um pitch, `di_osc_en` at y 122.445 and `di_clk_sel` at 125.135 (1.2 V inputs).
South edge, oscillator: `do_osc_oe` at x 91.745 and `do_clk_osc` at 94.435 (1.5 V outputs).
OBS covers Metal1 and Metal2 over the outline, Metal3 around the pins and Metal4.

The GDS has no fill and no nofill markers. The chip keeps metal fill out of the box and its 10 um halo, and Activ and GatPoly fill out of the outline (`scripts/add_logo_fill.sh`). It carries `sg13cmos5l_SecondaryProtection` under the PDK name, identical to the PDK IO library's copy (XOR 0 on every layer). The repo's `ip/sg13cmos5l_io_custom` GDS lacks the 3 PolyRes 128/0 marker shapes in that cell, as it did for 6dd2926.
