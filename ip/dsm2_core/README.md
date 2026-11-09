# dsm2_core

Views of the dsm2 first-order DT delta-sigma modulator, 150.5 x 178 um. GDS, LEF and CDL are dsm2's own, copied byte for byte and never edited here.

These are dsm2's oscillator variant views of 2026-11-02, the views that tape out. They carry the quantizer2 latch preset fix and four oscillator pins. The baseline views of the same day stay outside the repo as the fallback. The views of 6dd2926 (2026-10-29) are in git history.

| File | md5 | Source |
| --- | --- | --- |
| `gds/dsm2_core.gds` | `00624787128efe33ca6ddf5273170e56` | dsm2 delivery 2026-11-02, `dsm2_core_variant`, top cell `dsm2_core` |
| `lef/dsm2_core.lef` | `042ec97848217f9a30e94a391885b839` | same delivery, the variant LEF agreed on 2026-10-31 |
| `cdl/dsm2_core.cdl` | `5df9700351cb3b2c1804480eb62dfc12` | same delivery, the LVS netlist without the xschem path comments, 48 subckts |
| `spice/` | `MD5SUMS` there | same delivery, its ngspice bundle: schematic `dsm2_core`, extracted `dsm2_core_pex` (Magic full RC of this GDS), header, smoke benches, see `spice/README.md` |

## LVS record

dsm2's own LVS of the variant GDS (md5 `00624787128efe33ca6ddf5273170e56`, `lvs/gds_md5.txt`), run 2026-10-31 (the designer names iic-osic-tools:next, image dd952ba01866, the logs do not record it), kept in `lvs/`:

- `lvs/klayout_lvs.log`: KLayout LVS, extracts `cap_cmomf` and ends "Netlists match". It covers the 106 MOM capacitors that the chip's Magic LVS drops from the dsm2 comparison, because Magic does not extract them.
- `lvs/netgen_lvs.out`: Magic and Netgen, "Circuits match uniquely", 1477 devices and 696 nets on both sides. The 2753 property errors are all `mm_ok` on schematic devices, a model flag the extraction does not carry.

The chip's top LVS compares this GDS device by device against `cdl/dsm2_core.cdl` (`verification/lvs/`).

## Sizing and schematics

`schematic/` holds the xschem schematics of `bias_gm`, `bias_trim`, `dsm2_osc`, `sw_tgate`, `sw_tgate_cmfb2`, `sc_int2`, `cmfb_sc2`, `vcm_gen`, `quantizer2_top` and its `quantizer2_sal` and `quantizer2_dith` that the sizing notebooks read. `sizing/` holds the nine gm/ID notebooks and the OTA script, see `sizing/README.md`. All nine notebooks were rerun in this tree. They are tt derivations from SG13G2 tables, not evidence over PVT.

`model/` holds dsm2's Python behavioural models of the modulator (system level with integrator leak and noise, bit stream PSD, dither dead zone), see `model/README.md`. On 2026-11-09 the references to the designer's system-level notebook, which is not in this repo, were replaced by the setup they stood for. Only comment, docstring, help, print and prose text changed, no logic or number: `model/dither_deadzone.py`, `model/dsm_system.py`, `model/psd_bitstream.py`, `sizing/size_ota_fcasc2.py`, `sizing/size_sc_int2.ipynb`, `sizing/size_sw_tgate.ipynb`, `sizing/size_sw_tgate_cmfb2.ipynb`, `doc/ota_fcasc2_README.md`, `doc/sc_int2_README.md`, `doc/dsm2_README.md`. The setup is in `model/README.md`.

## Docs from the dsm2 design tree

Delivered with the views and not edited apart from the 2026-11-09 wording change above, in `doc/`: `dsm2_README.md` (the modulator), `dsm2_osc_README.md` (the oscillator variant, its frequencies are schematic values, the extracted view gives 583 to 671 kHz at code 4 and 1053 to 1195 kHz at code 15 over corners, per the designer's 2026-11-07 runs), `quantizer2_README.md`, `sc_int2_README.md`, `cmfb_sc2_README.md`, `vcm_gen_README.md`, `ota_fcasc2_README.md`, `bias_gm_README.md`, `bias_trim_README.md` and `measurement_plan.md` (the predicted value for each lab number, written before the tape-out. This is the 2026-11-09 version, in which the designer reworded only the row "SNDR at -6 dBFS, O2" after the tape-out: the about 49 dB with the on-chip clock holds for tone tests, DC readings do not see it). Some links inside them point into the dsm2 design tree and do not resolve here.

On the die, [doc/pinout.md](../../doc/pinout.md) and [doc/host_protocol.md](../../doc/host_protocol.md) govern where they differ from `measurement_plan.md`:

- `ibias_test`: the plan says "through at most 1.5 Mohm to ground" and offers 1 Mohm as a fallback. 200 nA across 1 Mohm is 0.2 V, below the 0.3 V floor of the oscillator variant. The safe rule is an SMU at 0.3 to 0.8 V, or 1.5 to 4 MOhm to ground, never 10 MOhm.
- Power-up: the plan lists an "SPI write of the defaults". Since v1.2.1 dsm2 is on from reset and needs no write.
- Reset release: the plan says 9 clocks (137 us). The chip's counter releases `di_rst_b` 9 to 10 `clk` periods after `rst_n`, 137 to 153 us at 65536 Hz.

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
