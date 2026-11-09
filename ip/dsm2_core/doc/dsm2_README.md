# ihp-sg13cmos5l Delta-Sigma Modulator Core (dsm2)

The first-order delta-sigma modulator of the new core: the integrator `sc_int2`, the quantizer with dither, the bias generator, the clock generator, the `vcm` generator and the secondary ESD protection of the analog pins in one cell, `dsm2_core`. It goes on the DSA1 die of the IHP open MPW CMOS5L run of 2026-11-09.

**Status (wave 4, 2026-10-29):** schematic, layout with KLayout DRC clean at macro level, Magic DRC with known markers inside child cells only, both LVS matching, a full RC PEX view, and the collaterals in `final/`: GDS, LEF (the frozen one), CDL and a blackbox Verilog. An op check at five corners ran on the extracted view. The wave 4 schematic gives 77.5 dB SNDR at -6 dBFS with dither off (sim, one run), with dither on (`di_dith_amp` 0) 70.3 dB, the extracted SNDR is open (see "Supply Current and SNDR, Wave 4").

`macros/dsm` (`dsm_top`, with `sc_int`, the old quantizer wiring and ideal clock and bias sources) stays untouched as the course reference.
`dsm2_core` differs from it in four ways: the OTA of the integrator is `ota_fcasc2`, the two phases come from `clk_noverlap` inside the block, the 200 nA bias comes from `bias_gm` inside the block, and `vcm` is made by `vcm_gen` inside the block.
The phases and `ibias_200n` are internal nets, so the block needs one clock, an enable and a reset.

**Oscillator variant (this branch, `dsm2-osc`).** DSA1 tapes out this view, the baseline of `master` is its fallback. It adds `dsm2_osc` (`macros/dsm2_osc`), a current-starved ring oscillator on the `bias_gm` test current, which can replace `di_clk`, and four ports. GDS md5 00624787128efe33ca6ddf5273170e56, both LVS matching in `registry.iic.jku.at:5000/iic-osic-tools:next` (2026-10-31, 1477 devices and 696 nets), delivered to DSA1 on 2026-11-02 with the fixed `quantizer2_top`.

The floorplan is `layout/dsm2_core_fp.py` (`make fp`). It places the blocks, the guard ring and the pins without routing and writes `layout/dsm2_core_fp.gds` and the frozen LEF `layout/dsm2_core_frozen.lef`: 150.5 x 178 um, pins on Metal3, OBS on Metal1 to Metal4, agreed with DSA1 (md5 8bcb6e6e743c9e9838114043a02f984a). On this branch `final/lef/dsm2_core.lef` is `layout/dsm2_core_osc.lef` (md5 042ec97848217f9a30e94a391885b839), the frozen LEF plus the four oscillator pins.

The sections "Testbench" and "Results" describe the version before wave 4 (no `dsm2_io`, no dither, `quantizer_top` clocked by `di_phi1`). They stay as the record of that version.

## Ports

Wave 4 (DSA1 die): the static controls come from the 1.2 V register file of DSA1 and enter through `dsm2_io`, the bit stream leaves gated, and a copy goes to the DSA1 decimator.

| Port | Direction | Layout edge | Meaning |
| --- | --- | --- | --- |
| `vi` | in | east | single-ended input, referred to `vcm` |
| `vcm` | inout | east | common-mode reference `vdd/2` from `vcm_gen`, driven from outside with `di_vcm_ext` high |
| `ibias_test` | inout | east | test copy of the 200 nA bias (pad), on while `di_btest_en` is high and `di_osc_en` is low |
| `vdd`, `vss` | inout | east | VDDA and ground, also the DAC levels |
| `di_clk` | in | south | sampling clock, 1.024 MHz, 1.5 V levels |
| `do_q`, `do_q_b` | out | south | bit stream and its complement for the pads, held low while `di_qout_en` is low |
| `di_ena` | in | west | enable of bias, OTA, clock and quantizer, low holds both phases low, slew limited in `dsm2_io` |
| `di_rst_b` | in | west | active-low reset of the quantizer, presets the latch |
| `di_trim[3:0]` | in | west | bias trim word, active high, code 4 (`0100`) gives 200 nA |
| `di_btest_en` | in | west | bias test copy onto `ibias_test` |
| `di_dith_en`, `di_dith_amp[1:0]` | in | west | dither on, and its amplitude (00 100 %, 01 67 %, 10 133 %, 11 33 %) |
| `di_qout_en` | in | west | enables `do_q` / `do_q_b` |
| `di_vcm_ext` | in | west | high stops the `vcm_gen` pump |
| `do_q_dec` | out | west, south end | ungated bit copy for the DSA1 decimator |
| `di_osc_en` | in | west | variant: runs the ring oscillator on the test current, which then no longer reaches `ibias_test` |
| `di_clk_sel` | in | west | variant: high clocks the modulator from the oscillator instead of `di_clk` |
| `do_clk_osc` | out | south | variant: oscillator clock for the pad, low while `di_osc_en` is low |
| `do_osc_oe` | out | south | variant: `di_clk_sel` at 1.5 V levels, output enable of the bidirectional clock pad |

`vi`, `vcm` and `ibias_test` reach the core through `dsm2_io_esd` (one IHP `sg13cmos5l_SecondaryProtection` per pin, see `macros/dsm2_io`), the core side of each is the net `vi_esd`, `vcm_esd` and `ibias_test_esd`.
The `di_` controls on the west edge take 1.2 V highs. Pin order in the netlist is `vi vcm di_clk di_ena di_rst_b di_trim[3:0] di_dith_en di_dith_amp[1:0] di_vcm_ext di_btest_en di_qout_en do_q do_q_b do_q_dec ibias_test vdd vss`, on the variant followed by `di_osc_en di_clk_sel do_clk_osc do_osc_oe`. Symbol pin sides: supplies, `vcm` and the enables and reset on top, `vss` bottom, inputs left, outputs and `ibias_test` right.

Pins of the frozen LEF, all Metal3 (core coordinates in um):

| Pin | Direction | Edge | x | y |
| --- | --- | --- | --- | --- |
| `vi` | input | east | 149.5 to 150.5 | 2.855 to 3.145 |
| `vcm` | inout | east | 149.5 to 150.5 | 8.355 to 8.645 |
| `ibias_test` | inout | east | 149.5 to 150.5 | 13.855 to 14.145 |
| `vdd` | inout | east | 148.5 to 150.5 | 36 to 46 |
| `vss` | inout | east | 148.5 to 150.5 | 50 to 60 |
| `di_clk` | input | south | 97.125 to 97.415 | 0 to 1 |
| `do_q` | output | south | 99.815 to 100.105 | 0 to 1 |
| `do_q_b` | output | south | 102.505 to 102.795 | 0 to 1 |
| `do_q_dec` | output | west | 0 to 3 | 2.855 to 3.145 |
| `di_vcm_ext` | input | west | 0 to 3 | 90.165 to 90.455 |
| `di_qout_en` | input | west | 0 to 3 | 92.855 to 93.145 |
| `di_rst_b` | input | west | 0 to 3 | 95.545 to 95.835 |
| `di_dith_en` | input | west | 0 to 3 | 98.235 to 98.525 |
| `di_dith_amp[1]` | input | west | 0 to 3 | 100.925 to 101.215 |
| `di_dith_amp[0]` | input | west | 0 to 3 | 103.615 to 103.905 |
| `di_btest_en` | input | west | 0 to 3 | 106.305 to 106.595 |
| `di_trim[3]` | input | west | 0 to 3 | 108.995 to 109.285 |
| `di_trim[2]` | input | west | 0 to 3 | 111.685 to 111.975 |
| `di_trim[1]` | input | west | 0 to 3 | 114.375 to 114.665 |
| `di_trim[0]` | input | west | 0 to 3 | 117.065 to 117.355 |
| `di_ena` | input | west | 0 to 3 | 119.755 to 120.045 |
| `di_osc_en` (variant) | input | west | 0 to 3 | 122.445 to 122.735 |
| `di_clk_sel` (variant) | input | west | 0 to 3 | 125.135 to 125.425 |
| `do_osc_oe` (variant) | output | south | 91.745 to 92.035 | 0 to 1 |
| `do_clk_osc` (variant) | output | south | 94.435 to 94.725 | 0 to 1 |

## Hierarchy

| Instance | Cell | Macro | Role |
| --- | --- | --- | --- |
| `xio` | `dsm2_io` | `macros/dsm2_io` | the twelve 1.2 V receivers, `di_ena` slew limiter, `di_trim` inverted to `d_trim_b` |
| `xioclk` | `dsm2_io_clk` | `macros/dsm2_io` | clock buffer at the south edge |
| `xclk` | `clk_noverlap` | `macros/clk_noverlap` | `d_phi1`, `d_phi2` and the quantizer clock `d_qclk` |
| `xvcmg` | `dsm2_io_vcmg` | `macros/dsm2_io` | gates the `vcm_gen` phases off while `di_vcm_ext` is high |
| `xvcm` | `vcm_gen` | `macros/vcm_gen` | 2:1 switched-capacitor divider, drives `vcm` |
| `xbias` | `bias_gm` | `macros/bias_gm` | `ibias_200n` for the OTA, test copy on `ibias_bank` |
| `xosc` | `dsm2_osc` | `macros/dsm2_osc` | variant: ring oscillator on `ibias_bank`, passes the bank to `ibias_test_esd` while off, clock mux |
| `xsc` | `sc_int2` | `macros/sc_int2` | integrator with `ota_fcasc2`, DAC steered by `d_qi` and `d_qi_b` |
| `xq` | `quantizer2_top` | `macros/quantizer2` | StrongARM latch, SR latch, dither injection, pad drivers, `do_q_dec` |
| `xlfsr` | `quantizer2_lfsr` | `macros/quantizer2` | 17-bit LFSR dither code and the amplitude select |
| `xesd` | `dsm2_io_esd` | `macros/dsm2_io` | secondary ESD protection of `vi`, `vcm` and `ibias_test` |
| `XMDN`, `XMDP` | `sg13_lv_nmos`, `sg13_lv_pmos` | PDK | the devices of the 128 `sg13cmos5l_decap_8` cells of the layout fill, m=128 each |

The sub-macros keep their own layouts, Makefiles and benches.
`schematic/xschem/xschemrc` and the testbench `xschemrc` put the schematic folders of these macros and of the cells they instantiate on the library path.

## Wiring

- `dsm2_io` turns the west inputs into `d_ena`, `d_rst_b`, `d_trim_b[3:0]`, `d_dith_en`, `d_dith_amp[1:0]`, `d_btest_en`, `d_qout_en`, `d_vcm_ext` and `d_vcm_ext_b` at 1.5 V levels. `d_ena` goes to `xclk`, `xsc`, `xbias` and the quantizer `di_en`.
- `di_clk` goes through `dsm2_io_clk` (`d_clk`) to `di_clk_ext` of `dsm2_osc`, whose mux output `d_clk_mod` (the oscillator with `di_clk_sel` high, `d_clk` otherwise) clocks `clk_noverlap`. `do_phi1` and `do_phi2` drive `d_phi1` and `d_phi2`, the `di_phi1` and `di_phi2` pins of `sc_int2`. `do_qclk` (`d_qclk`) clocks `quantizer2_top` and `quantizer2_lfsr`: it rises just after phase 2 falls, so the quantizer decides in the 4.3 ns gap before phase 1 (fix A, 2026-10-25).
- `do_phi1_b` and `do_phi2` go through `dsm2_io_vcmg` to `vcm_gen` (`d_vcm_phi1_b`, `d_vcm_phi2`). `d_phi2_b` is unused.
- `vo_p` and `vo_n` of `sc_int2` go to `vi_p` and `vi_n` of `quantizer2_top`. Its internal bits `do_qi` / `do_qi_b` (`d_qi`, `d_qi_b`) drive `di_q` / `di_q_b` of `sc_int2`, same polarity as the `do_q` / `do_q_b` of the old quantizer. `do_q`, `do_q_b` and `do_q_dec` are the ports.
- `quantizer2_lfsr` gives `d_dith[2:0]`, `d_amp_s[3:0]` and `d_amp_s_b[3:0]` to the quantizer.
- `ibias_200n` runs from `bias_gm` to `sc_int2`. The test copy leaves `bias_gm` on `ibias_bank` into `ibias_in` of `dsm2_osc`, which passes it to `ibias_test_esd` while `di_osc_en` is low and into the ring while it is high.
- `dsm2_osc` ORs `d_btest_en` with its `d_osc_en` into `d_btest_or`, the `di_btest_en` of `bias_gm`, because the bank only sources while that input is high.
- `dsm2_io_esd` sits between the ports `vi`, `vcm`, `ibias_test` and the core nets `vi_esd` (to `sc_int2`), `vcm_esd` (`vcm_gen` and `sc_int2`) and `ibias_test_esd` (`dsm2_osc` `ibias_pad`).

## Supply Current and SNDR, Wave 4

Sanity checks from single runs (sim), not characterisation.

Supply current of the schematic, ngspice on a laptop, `dsm2_core_tb_psd` stimulus at -6 dBFS, pad drivers into 80 fF, `ibias_test` held at 0.5 V. Average of the supply current over 300 clocks (tt, both off and both on) or 150 clocks (the others) after 30 to 50 clocks of settling, and its highest average over any 100 ns and any 10 ns window (windows stepped by 0.05 ns on the piecewise linear current). These runs carry the earlier dither ladder (1.4 uA):

| corner, supply, temperature | dither, btest | average (uA) | 100 ns peak (uA) | 10 ns peak (uA) |
| --- | --- | --- | --- | --- |
| tt 1.5 V 27 C | off, off | 10.69 | 37.5 | 320 |
| tt 1.5 V 27 C | off, on | 10.98 | 37.5 | 318 |
| tt 1.5 V 27 C | on, off | 11.51 | 41.6 | 360 |
| tt 1.5 V 27 C | on, on | 11.65 | 42.1 | 363 |
| ss 1.5 V 27 C | off, off / on, on | 10.11 / 11.03 | 34.0 / 38.6 | 287 / 331 |
| ff 1.5 V 27 C | off, off / on, on | 11.98 / 13.04 | 41.4 / 47.1 | 348 / 402 |
| sf 1.5 V 27 C | off, off / on, on | 10.78 / 11.72 | 36.9 / 42.1 | 312 / 362 |
| fs 1.5 V 27 C | off, off / on, on | 10.83 / 11.83 | 36.9 / 42.1 | 313 / 363 |
| ff 1.55 V 125 C | on, on | 21.25 | 60.2 | 465 |
| ss 1.45 V -40 C | off, off | 9.00 | 30.8 | 262 |

With the current dither ladder (2.58 uA), tt 1.5 V 27 C with dither on and btest off reads 12.77 uA average, 42.9 uA over 100 ns and 362 uA over 10 ns (one run, 150 clocks), 1.26 uA more on average than the earlier ladder.

Between the clock edges the current stays below 6 uA. The edges carry the switched-capacitor charge, the pad drivers and the clock tree. These runs predate `dsm2_io_esd`, which adds no DC path in normal operation.

Op check of the extracted view against the schematic (2026-10-29, ngspice, laptop, sanity checks of one run each). `dsm2_core_tb_tran` stimulus (DC +0.3 V on `vi`), 40 clocks, values over clocks 20 to 40. The extracted view is `netlist/pex/dsm2_core_magic_pex_3.spice`. Each cell is extracted / schematic. Current is the average of the supply current and its highest average over 100 ns and over 10 ns. `ibias_200n` is the node voltage, CM is the mean of `vo_p` and `vo_n`. The phase columns give the rise of `d_qclk` and of `d_phi1` after the fall of `d_phi2` (50 % crossings, median of the 20 clocks).

| corner, supply, temperature | current (uA): average, 100 ns, 10 ns | `ibias_200n` (V) | `vcm` (V) | CM (V) | `vo_p - vo_n` min / max (V) | `d_qclk` after `d_phi2` fall (ns) | `d_phi1` after `d_phi2` fall (ns) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tt 1.5 V 27 C | 13.59, 45.5, 381 / 12.24, 38.2, 313 | 0.606 / 0.607 | 0.756 / 0.753 | 0.757 / 0.752 | -0.394, +0.457 / -0.418, +0.533 | 0.32 / 0.29 | 5.31 / 4.44 |
| ss 1.45 V 125 C | 14.23, 44.7, 359 / 13.25, 36.7, 285 | 0.628 / 0.629 | 0.733 / 0.732 | 0.727 / 0.727 | -0.383, +0.472 / -0.413, +0.480 | 0.52 / 0.39 | 7.35 / 6.14 |
| ss 1.45 V -40 C | 11.27, 38.2, 323 / 10.10, 31.8, 263 | 0.777 / 0.776 | 0.728 / 0.730 | 0.725 / 0.735 | -0.357, +0.448 / -0.451, +0.515 | 0.46 / 0.34 | 5.56 / 4.62 |
| ff 1.55 V -40 C | 14.43, 50.9, 416 / 13.06, 43.6, 354 | 0.563 / 0.563 | 0.775 / 0.774 | 0.755 / 0.756 | -0.389, +0.493 / -0.456, +0.560 | 0.28 / 0.22 | 3.95 / 3.33 |
| ff 1.55 V 125 C | 24.79, 65.6, 488 / 23.43, 58.9, 429 | 0.406 / 0.407 | 0.778 / 0.781 | 0.757 / 0.770 | -0.399, +0.498 / -0.460, +0.546 | 0.31 / 0.08 | 5.37 / 4.50 |

- The extracted view draws 1.0 to 1.4 uA more than the schematic at every corner, and 6 to 7 uA more over 100 ns. The bias node, `vcm` and the output common mode agree within a few mV, except the CM at ff 125 C (13 mV) and ss -40 C (10 mV).
- The quantizer clock rises 0.2 to 0.5 ns after the phase 2 fall in both views. Phase 1 follows 3.3 to 7.4 ns after that fall, about 1 ns later on the extracted view. At ff 1.55 V -40 C the gap is 3.33 ns on the schematic (3.24 ns on the `clk_noverlap` bench alone) and 3.95 ns extracted. What it has to cover is the quantizer decision: `do_q` (the pad copy, behind the gate and two inverters, so later than the latch itself) reaches 90 % of its swing 1.00 to 1.32 ns after the phase 2 fall on the schematic and 1.23 to 1.69 ns extracted (the 12 of 20 clocks where it changes, down to 1.4 mV of `vo_p - vo_n`). That leaves at least 1.97 ns (schematic) and 2.23 ns (extracted) before phase 1 rises.
- At ff 1.55 V -40 C the two views give the same `do_q` bits in 18 of the 20 clocks 20 to 39. The 2 that differ are a swapped pair, as expected from two runs of a chaotic first-order loop.
- At -40 C the extracted runs stopped on "Timestep too small" in the `dparea` part of the core-side `dpantenna` of `dsm2_io_esd` on `ibias_test` (ss at 0.49 us, ff at 4.9 us). `gmin=1e-10` alone did not get past it. `gmin=1e-10 reltol=1e-3 trtol=7` did, so both -40 C rows use those options, and the ff -40 C schematic row too.
- With the bench's loose `reltol=5e-3 trtol=10`, the ff 1.55 V -40 C schematic run put phase 1 only 0.40 ns after the phase 2 fall. With the tighter options the same deck gives 3.33 ns, which matches the `clk_noverlap` bench. So the default tolerances of the dsm2 benches are not reliable for phase timing at that corner.

Start-up (2026-10-30, ngspice, sanity checks of one run each):

- Supply ramp from 0.9 V to 1.5 V (vref along, vdd/2), schematic, tt 27 C, with `di_ena`, `di_rst_b` and every control low throughout and `di_clk` starting after the ramp. Over a 1 us ramp the supply current averages 5.74 uA with a 6.1 uA peak, which is C dV/dt of about 9.5 pF. Over a 100 us ramp it averages 0.32 uA (0.62 uA peak). Afterwards, with the clock running and `di_ena` low, the block draws 0.60 uA (2.8 uA over 10 ns, 193 uA raw spike at the first clock edge), so `bias_gm` stays off. `do_q`, `do_q_b` and `do_q_dec` stay at 0 V and the phases stay low. `vcm` is not driven while `di_ena` is low and floats at 0.47 to 0.51 V.
- Ramps below 0.9 V are not simulated. ngspice (both views, both option sets, also with `maxord=2`) and VACASK (extracted view) stall between 0.16 V and 1.19 V of supply, with steps down to about 1 fs. All nodes saved into the stall show that nothing toggles there, so the stall is numerical.
- Enable step at full supply (the DSA1 sequence: VDDA up, `di_ena` low until the register is written), tt 1.5 V 27 C, `di_ena` at 5 us, `di_rst_b` 60 us later, schematic (reltol 1e-4, a 0 V source in each child's vdd pin) and extracted (reltol 1e-3):
  - `ibias_200n` is within 1 % of its final 0.607 V 40.9 us (schematic) and 48.7 us (extracted) after `di_ena`. `vcm` is 0.726 to 0.731 V at `di_rst_b` and 0.734 to 0.761 V per clock after it. The first 20 bits after `di_rst_b` agree in 19 of 20 between the views, with no saturation run. Running current after reset is 12.0 to 12.6 uA (schematic) and 13 to 14 uA (extracted).
  - Without `quantizer2_top`, the enable inrush stays below 80 uA averaged over 100 ns: 64 uA peak, 240 uA over 10 ns, 40.8 pC in the first 10 us, mostly `clk_noverlap` (23 pC) and `sc_int2` (7 pC).
  - ff 1.55 V 125 C, schematic, same sequence: `ibias_200n` within 1 % of its final 0.407 V 29.2 us after `di_ena`, `vcm` 0.753 V at `di_rst_b` and 0.762 to 0.787 V per clock after it, running current 22.8 to 23.7 uA, 8.3 uA while disabled. Without `quantizer2_top` the enable inrush peaks at 137 uA over 100 ns and 365 uA over 10 ns, above 80 uA for 0.1 us right after `di_ena`, from `clk_noverlap` (109 uA over 100 ns). The first 10 us draw 124 pC (`clk_noverlap` 46 pC, `sc_int2` 25 pC).
  - ss 1.45 V -40 C, schematic, `di_rst_b` 140 us after `di_ena`: `ibias_200n` within 1 % of its final 0.776 V 71.2 us after `di_ena`, `vcm` 0.730 V at `di_rst_b` and 0.710 to 0.739 V per clock after it, running current 9.8 to 10.3 uA, 0.2 uA while disabled. Without `quantizer2_top` the enable inrush peaks at 32 uA over 100 ns and 151 uA over 10 ns, 32 pC in the first 10 us.
  - The runs above used the old `quantizer2_top`, whose ratioed preset fought the output latch (about 195 uA whenever the latch held `do_qi` = 1 under preset, `do_q` toggling during reset). The fixed `quantizer2_top` gates the latch inputs with the preset instead (see its README), so the outputs stay static in reset and the fight is gone.
  - With the fixed `quantizer2_top`, the variant with the oscillator on: tt 1.5 V 27 C peaks at 99 uA over 100 ns and 389 uA over 10 ns, 52.6 pC in the first 10 us, 16.0 uA running, 0.65 uA disabled. ff 1.55 V 125 C peaks at 215 uA over 100 ns and 546 uA over 10 ns, 254 pC, 29.0 uA running, 8.5 uA disabled. Both peaks sit at the first clock edge after `di_ena`, from `clk_noverlap` and `quantizer2_top`, before the oscillator starts.
  - Reset recovery: in reset the quantizer holds `do_q` at 0 and `sc_int2` is not reset, so the integrator saturates (vod 1.41 V). After `di_rst_b` the loop needs 16 to 17 clocks of `do_q` = 1 to recover (tt and ff, vi = +0.3 V), longer as vi approaches positive full scale. Discard the first decimator output after reset release.

SNDR provenance:

- Wave 4 schematic, dither off, -6 dBFS, tt 1.5 V 27 C (VACASK, 16904 clocks, one run, sim): SNDR 77.5 dB in five bins, floor fit over 10 to 200 kHz 75.4 dB at 19.4 dB per decade, worst in-band bin -84.8 dBFS at 875 Hz, stream mean +0.0161. That netlist has the `quantizer2` before the preset fix, which acts only in reset and disable, so the running loop is the same.
- Same bench with dither on, `di_dith_amp` 0, `di_dith_en` rising at 4 us (one run, sim): SNDR 70.3 dB in five bins, floor fit 72.2 dB at 19.7 dB per decade, worst in-band bin -76.1 dBFS at 1 kHz, stream mean +0.0160. The 7.2 dB against dither off is not a circuit loss. The LFSR restarts from the same state when `di_dith_en` rises, so every run evaluates the same 16384-clock window of the code sequence, and this window has its strongest bins at 1.0 and 1.06 kHz (+6.5 and +5.2 dB above the mean). An ideal first-order loop fed with the same vi and that window gives 70.3 dB, and 119 other LFSR offsets give 75.6 +- 2.4 dB (minimum 70.8 dB), against 74.9 +- 1.3 dB without dither. A per-clock fit of the integrator step in both runs shows no added leak with dither on (+1e-5 against -4.25e-4 per clock off). A single run over 16 in-band bins scatters by about 2 dB, so quote dither-on SNDR as the mean over several LFSR windows. The floor fit rises 2.2 dB with ideal dither, 3.2 dB in the circuit.
- Clocking evidence: the quantizer clock fix A (`do_qclk` rises just after the phase 2 fall) read 81.68 and 80.08 dB at -6 dBFS (two seeds, ngspice, a schematic loop of the previous core with the quantizer on that clock), against 81.34 and 82.79 dB with the quantizer on `di_phi1`.
- The same record with dither on (seed 1) is still running on 2026-11-05.
- The extracted SNDR is open. A full record on the extracted view takes about 690 h on the laptop in VACASK (146 s per clock, mode 3), so it runs after the delivery on a faster machine.

A 300-clock closed-loop transient of the extracted view at -6 dBFS (VACASK, full mode 3), compared with the schematic on integrator swing, stream mean and settling, was stopped at about 130 of 300 clocks to free the host before the delivery and is deferred.

## Testbench

Previous version, see the note at the top.


`testbenches/xschem/dsm2_core_tb_tran.sch`, `make sim-xschem` (tt, 1.5 V, 27 C, no noise, no mismatch).
`di_clk` is 1.024 MHz with 1 ns edges and `di_ena` is high. `di_rst_b` is released after 2 clocks, `bias_gm` starts from zero current.
`vcm` has no source any more, it is made by `vcm_gen` inside the block and only observed. `vi` is referred to `vref`, an ideal `vdd/2` source (as the closed-loop run of `macros/vcm_gen` did). A `vi` referred to the `vcm` node would return the charge of the C1 left plates through the pump (see its README). `vi` is `vref` plus 0.3 V for 640 clocks, then -0.3 V for 640 clocks, then a 4 kHz sine of 0.375 V for 768 clocks, 2048 clocks in all.
Full scale is `vdd/2` = 0.75 V, the DAC levels are `vdd` and `vss` around `vcm`, and `dsm_tb_psd` of the course reference uses the same value (a 0.375 V tone is -5.95 dBFS there).
The control block prints the mean of `do_q` as a bit (`2 mean/vdd - 1`) against `(vi - vcm)/vfs`, over the last 440 clocks of each DC step and over 24 windows of 32 clocks of the sine, and the swing of `vo_p`, `vo_n` and their difference. It also prints the mean and the peak to peak of `vcm` minus `vdd/2`, read 10 ns before each falling edge of `di_phi1` (where `sc_int2` samples, the raw has a 10 ns grid) for clocks 200 to 640, 840 to 1280 and 200 to 2045.

`VBRK1` to `VBRK3` in series with `RBRK` are pulse sources on their own net `nbrk`, connected to nothing else. They only put solver breakpoints every 0.25 ns from 1.05 to 3.80 ns after every `di_clk` edge, so no timestep is longer than 0.35 ns while the quantizer decides, at every corner below.
The quantizer clock is `di_phi1` from `clk_noverlap`, which rises 1 to 2 ns after the `di_clk` edge, past the last breakpoint of `VCLK` at 1 ns. From 2^-10 s on (clock 1000) ngspice-47 often lands its clock-edge point a hair before the breakpoint and then skips the step cut that follows a breakpoint, so the step across the decision grows to 0.5 to 3 ns. The latch then resolves to the wrong side, at up to 0.37 V of input. The run without `VBRK` gave 138 such decisions and a swing of -0.96 / +0.95 V.
Do not remove `VBRK`, and do not count on the default tolerance instead: with it the same bench aborted at clock 473 on "Timestep too small" in the AND gate of `clk_noverlap` (1 run, DC -0.3 V).

The window comes from the `di_clk` to `di_phi1` delay of `clk_noverlap` (50 % of `di_clk` to 50 % of `di_phi1`, rising edge, its own bench in a scratch copy, 1 run per corner). The breakpoints count from the start of the 1 ns `di_clk` edge, so add 0.5 ns to read the delay on that axis.

| corner, supply, temperature | delay | `di_phi1` 50 % after the edge starts | `di_phi1` 10 % to 90 % after the edge starts |
| --- | --- | --- | --- |
| tt 1.5 V 27 C | 1.15 ns | 1.65 ns | 1.32 to 2.21 ns |
| ss 1.45 V 125 C | 1.57 ns | 2.07 ns | 1.63 to 2.82 ns |
| ss 1.45 V -40 C | 1.36 ns | 1.86 ns | 1.49 to 2.48 ns |
| ff 1.55 V -40 C | 0.86 ns | 1.36 ns | 1.13 to 1.77 ns |
| ff 1.55 V 125 C | 1.02 ns | 1.52 ns | 1.25 to 2.00 ns |

The slowest is ss 1.45 V 125 C, 2.07 ns, so the window ends at 2.07 + 1 = 3.07 ns and the breakpoint train runs to 3.80 ns, one window for all corners. It starts at 1.05 ns, where the `VCLK` breakpoint at 1 ns ends. The old window (1.05 to 1.8 ns, 4 breakpoints per clock) ended before `di_phi1` reached 50 % in ss at 125 C. The new one has 12 breakpoints per clock. The extra run time was not measured on its own, the host load differed between runs.
The first try used one `PWL` source with `r=0`. It put a breakpoint at every `di_clk` edge itself and the ss 1.45 V 125 C run aborted at clock 1034 with "Timestep too small" in `clk_noverlap` (the PWL repeat point and `VCLK` land within a few ulp of each other, inference). Three series `PULSE` sources have no point at the edge and all five corners ran through.

`testbenches/xschem/pvt.py` runs the five corners from the netlist of `make sim-xschem` (stop that after the netlist, it also starts the tt run) and counts the wrong decisions.

## Results

Previous version, see the note at the top.


The first table, the corner table and the supply current section are from the bench before `vcm_gen` joined the block (ideal `vcm` source, `vi` referred to it). The subsections "With `vcm_gen` inside the block" (tt only) and "Schematic against the full RC PEX view" (five corners, both views) are the current bench.

Sanity checks from one transient run of the bench per condition (2048 clocks, no noise, no mismatch), not characterisation. No measurement failed in the five runs, one earlier ss run aborted (see above, replaced by the rerun). Each run took 2 to 7 hours on a host with a load of about 25.
The bench runs with `reltol=5e-3 trtol=10`, about 3 times faster than the ngspice defaults with gear.

The reference is `macros/dsm` (`dsm_top`, ideal clocks with 10 ns non-overlap and ideal 200 nA source) with the same input and the same options, one run of 2048 clocks (65 min), tt only. Bit mean is `2 mean(do_q)/vdd - 1`.

| | `dsm2_core` tt 1.5 V 27 C | `dsm_top` tt | expected |
| --- | --- | --- | --- |
| DC +0.3 V, bit mean over clocks 200 to 640 | 0.4181 | 0.4225 | 0.400 |
| DC -0.3 V, bit mean over clocks 840 to 1280 | -0.3911 | -0.3866 | -0.400 |
| sine, 24 windows of 32 clocks, gain of window mean against input | 0.994 | 1.015 | 1 |
| sine, rms and max error of the window mean | 0.029 / 0.061 | 0.032 / 0.063 | about 1/32 |
| `vo_p` min / max | 0.424 / 1.223 V | 0.416 / 1.172 V | |
| difference `vo_p - vo_n` min / max | -0.524 / +0.603 V | -0.530 / +0.544 V | |
| clocks of 1847 deciding against the sign of `vo_p - vo_n` 20 ns before the edge, and the largest such input | 7, 0.002 V | 43, 0.054 V | |
| supply current mean | 6.8 uA | 4.0 uA (without bias_gm) | |

The mean follows `(vi - vcm)/0.75` in both, so the feedback is negative. The reference stream carries the +0.02 offset its README mentions.
The +0.603 V maximum of the difference is at clock 640.5, half a clock after the input steps from +0.3 to -0.3 V. At the clock edges the difference stays within 0.37 V.

### With `vcm_gen` inside the block

The bench above, rerun after `vcm_gen` joined the block (the ideal `vcm` source is gone, `vi` is referred to the ideal `vref` = `vdd/2`). One tt 1.5 V 27 C run of 2048 clocks in a scratch copy of the netlist, `hpretl/iic-osic-tools:2026.08`, the same options. A sanity check, not characterisation, 0 measurements failed (1846 `vcm` samples, 24 sine windows). The DC operating point needed true gmin stepping (dynamic gmin stepping failed), the transient was not affected.

| | with `vcm_gen` | ideal `vcm` (table above) | `vcm_gen` pump run of `macros/vcm_gen` (first 1280 clocks) |
| --- | --- | --- | --- |
| DC +0.3 V, bit mean | 0.4271 | 0.4181 | 0.4271 |
| DC -0.3 V, bit mean | -0.3866 | -0.3911 | -0.3866 |
| sine, gain, rms error of the window mean | 1.007, 0.032 | 0.994, 0.029 | |
| `vo_p - vo_n` min / max | -0.519 / +0.533 V | -0.524 / +0.603 V | -0.513 / +0.518 V |
| supply current mean | 6.93 uA | 6.84 uA | 6.88 uA |
| `vcm` minus `vdd/2`, mean / p-p, clocks 200 to 640 | -1.4 mV / 45.7 mV | | |
| `vcm` minus `vdd/2`, mean / p-p, clocks 840 to 1280 | -2.3 mV / 44.2 mV | | |
| `vcm` minus `vdd/2`, mean / p-p, clocks 200 to 2045 | -1.9 mV / 60.5 mV | | |

The bit means agree with the pump run of `macros/vcm_gen` to four digits, so the cell in the block behaves as the scratch copy did. They sit 0.009 and 0.0045 above the ideal source, 1.2 % and 0.6 % of the full scale at the expected 0.400. `vcm` is read 10 ns before each falling edge of `di_phi1` on the 10 ns grid of the raw, and the mean is 1.4 to 2.3 mV below `vdd/2`. The `vcm_gen` README quotes 3.1 and 3.9 mV below for the same windows, read 0.3 ns before the edge. The sine part reaches 60.5 mV peak to peak, 14 mV more than the DC windows, the cause was not looked at.

### Corners

One run per row with the window above, `res_typ` and `cap_typ`, supply and temperature as listed (`vcm` and full scale follow the supply, expected bit mean 0.4138 at 1.45 V, 0.3871 at 1.55 V).
Wrong decisions are `do_q` 0.45 clock after the edge against the sign of `vo_p - vo_n` 20 ns before it, clocks 200 to 999 and 1000 to 2046, count of any sign and the largest input among them. None was above 20 mV.

| corner, supply, temperature | DC +0.3 V / -0.3 V bit mean | sine gain, rms err | `vo_p - vo_n` min / max | wrong, clocks 200-999 / 1000-2046 | largest wrong input | supply current | failed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tt 1.5 V 27 C | 0.418 / -0.391 | 0.994, 0.029 | -0.524 / +0.603 V | 3 / 4 | 2.2 mV | 6.84 uA | 0 |
| ss 1.45 V 125 C | 0.436 / -0.400 | 0.991, 0.027 | -0.546 / +0.503 V | 5 / 5 | 2.6 mV | 7.99 uA | 0 |
| ss 1.45 V -40 C | 0.432 / -0.409 | 1.011, 0.029 | -0.510 / +0.510 V | 3 / 6 | 2.3 mV | 5.66 uA | 0 |
| ff 1.55 V -40 C | 0.404 / -0.377 | 1.011, 0.028 | -0.540 / +0.545 V | 2 / 4 | 1.5 mV | 6.58 uA | 0 |
| ff 1.55 V 125 C | 0.418 / -0.373 | 1.026, 0.042 | -0.529 / +0.541 V | 7 / 4 | 4.0 mV | 10.98 uA | 0 |

The largest step inside 1 to 3.6 ns after the edge, clocks 1000 on, is 0.35 ns in every run. The ff 125 C row has the largest rms error, 0.042 against 0.027 to 0.029 of the others, with a bit mean 0.031 above the expected value at +0.3 V. It is a single run and the cause was not looked at.

### Supply current

The tt run read 6.8 uA, the earlier run of the older netlist 9.2 uA. The two netlists differ only by the 14 decaps in `clk_noverlap` (capacitors, no DC current), the `VBRK` source and the pin names of `inv_en`. A tt rerun with the decaps removed (scratch copy of the deck) read 6.79 uA against 6.84 uA with them, so the decaps account for 0.06 uA. The remaining 2.4 uA belong to the timestep fault of the old run (swing of +-0.95 V, wrong decisions), this is inference from the netlist diff and the two runs, a run with the old netlist and `VBRK` was not made.

### Schematic against the full RC PEX view

One 2048-clock run per corner and view, 10 runs, `registry.iic.jku.at:5000/iic-osic-tools:next` on an aarch64 host (image 0ad78d950901, ngspice-47). Sanity checks, not characterisation. All 10 runs finished, 0 measurements failed. Before them a 128-clock schematic run gave the same 127 bits and `vo_p - vo_n` within 0.08 mV on that host and on a laptop with the same image tag (bb525d654d8d).

The PEX view is `netlist/pex/dsm2_core_magic_pex_3.spice` from `make magic-pex EXT_MODE=3`, a flat Magic full RC extraction of the whole cell, hierarchy off, so the coupling between the blocks and the top routing is in it.

- The MoM caps of `sc_int2` and `vcm_gen` get the pad treatment of those macros: `make pex-gds` (`scripts/pex_gds.py`, then the child's `pex_gds.py`) extracts them as plain metal, `scripts/pex_caps.py` drops the coupling between the two nets of each cap and adds the 72 caps back at the model value.
- Mode 3 books the coupling of every net with resistors a second time as capacitance to vss (`vo_p` 620 fF to vss against 53 fF in mode 2, `di_phi1` 74 against 16 fF). `macros/scripts/pex_rc_caps.py` keeps the resistors and scales each net pair to a mode 2 run of the same layout.
- 1004 devices, equal per model in count and total W to the Magic LVS netlist, plus the 72 caps, 9102 resistors (95 % on vdd and vss), 6182 nodes. 97 capacitor-only nodes are tied to vss by 1 TOhm, the same ones the child views tie.

Decks come from `testbenches/xschem/pvt.py --chgtol 1e-18 --options rshunt=1e12 [--view pex]`. The PEX deck differs from the schematic deck only in the DUT line and its include. `rshunt` puts 1 pS from every node to ground. Both views carry it because without it the PEX operating point did not converge. It moves the start-up state, so the schematic rows are not the runs of the tables above repeated.

Columns as in the corner table, plus `vcm` minus `vdd/2` (mean and peak to peak, clocks 200 to 2045) and the run time.

| corner, supply, temperature, view | DC +0.3 V / -0.3 V bit mean | sine gain, rms err | `vo_p` min / max | `vo_p - vo_n` min / max | wrong, clocks 200-999 / 1000-2046 (above 20 mV) | largest wrong input | supply current | `vcm` error mean / p-p | run time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tt 1.5 V 27 C, schematic | 0.4226 / -0.3912 | 1.012, 0.031 | 0.403 / 1.347 V | -0.552 / +0.555 V | 6 / 5 (0) | 4.2 mV | 6.99 uA | -2.0 / 78.6 mV | 41 min |
| tt 1.5 V 27 C, PEX | 0.4180 / -0.3822 | 0.998, 0.032 | 0.439 / 1.184 V | -0.530 / +0.588 V | 18 / 34 (9) | 23.7 mV | 7.71 uA | +1.7 / 66.2 mV | 238 min |
| ss 1.45 V 125 C, schematic | 0.4317 / -0.4003 | 1.018, 0.033 | 0.397 / 1.290 V | -0.529 / +0.533 V | 5 / 6 (0) | 3.1 mV | 7.67 uA | +4.3 / 80.1 mV | 38 min |
| ss 1.45 V 125 C, PEX | 0.4316 / -0.4004 | 1.011, 0.034 | 0.442 / 1.155 V | -0.506 / +0.487 V | 15 / 32 (2) | 21.7 mV | 8.35 uA | +7.3 / 73.2 mV | 222 min |
| ss 1.45 V -40 C, schematic | 0.4271 / -0.4093 | 1.010, 0.033 | 0.437 / 1.269 V | -0.537 / +0.540 V | 4 / 2 (0) | 1.9 mV | 6.04 uA | +2.0 / 87.6 mV | 44 min |
| ss 1.45 V -40 C, PEX | 0.4316 / -0.4004 | 0.991, 0.027 | 0.451 / 1.137 V | -0.519 / +0.487 V | 23 / 39 (13) | 31.4 mV | 6.71 uA | +3.9 / 78.3 mV | 256 min |
| ff 1.55 V -40 C, schematic | 0.4090 / -0.3774 | 1.005, 0.033 | 0.391 / 1.361 V | -0.572 / +0.579 V | 6 / 4 (0) | 3.5 mV | 6.96 uA | -4.1 / 78.6 mV | 39 min |
| ff 1.55 V -40 C, PEX | 0.4089 / -0.3684 | 1.003, 0.037 | 0.417 / 1.181 V | -0.550 / +0.523 V | 22 / 37 (14) | 30.3 mV | 7.73 uA | -1.0 / 72.6 mV | 237 min |
| ff 1.55 V 125 C, schematic | 0.4089 / -0.3684 | 1.013, 0.039 | 0.366 / 1.399 V | -0.626 / +0.578 V | 8 / 16 (0) | 4.1 mV | 10.81 uA | +1.1 / 72.7 mV | 39 min |
| ff 1.55 V 125 C, PEX | 0.4089 / -0.3685 | 1.009, 0.036 | 0.391 / 1.166 V | -0.539 / +0.525 V | 17 / 31 (0) | 19.4 mV | 11.59 uA | +0.2 / 70.0 mV | 213 min |

- The bit means of the two views agree within 0.009 (tt, -0.3 V) and the sine gain within 0.02 at every corner, so the loop on the extracted view converts as the schematic does. A mean over 440 clocks moves in steps of 0.0045.
- The bit streams themselves are not comparable: they part within the first 4 clocks and 44 to 70 % of the bits from clock 200 on are equal, which is what two runs of a chaotic first-order loop give. Means over 32-clock windows differ by 0.032 to 0.037 rms between the views.
- The extracted view decides against the sign of `vo_p - vo_n` 2 to 10 times as often as the schematic (47 to 62 against 6 to 24 per run), at up to 31 mV. Almost all of them are bit 1 at a negative difference. The count does not change between 20 ns and 2 ns before the edge, so the difference has settled. A single threshold of -17 to -26 mV still leaves 34 to 45 of them, so this is not only an offset. Cause not traced.
- The extracted view draws 0.7 to 0.8 uA more supply current (charging the wiring capacitance of the clocks and phases, inference). `ibias_200n` sits within 1 mV of the schematic in every corner (the node voltage, the current is not probed).
- The maximum of `vo_p` is 0.13 to 0.23 V lower on the extracted view at every corner with a similar differential swing. It is a common mode spike of both outputs 1.5 to 3 ns after the fall of `di_phi1`, 146 to 195 mV on the extracted view against 286 to 357 mV on the schematic. At the clock-sampled instant the levels of the two views agree within 10 to 25 mV. Traced on 2026-10-19 from the existing raws (sim): only the extracted `sc_int2` reproduces it, it stays when the wrong decisions are removed, and only removing all extracted capacitors of `sc_int2` restores the schematic spike.
- The PEX runs took 5.5 to 6 times as long and up to 62 GB of memory (0.25 GB for the schematic).
- No SNDR: the sine is 4 kHz, outside the 1 kHz band, and 768 clocks long.

### In-band SNDR

Sanity checks of the schematic and of one extracted child, not a characterisation. tt 1.5 V 27 C, one coherent tone at 687.5 Hz (bin 11 of 16384, 62.5 Hz bins), Hann window, mean removed, band 0 to 1 kHz, 5-bin tone lobe and 3-bin DC skirt left out, `fs` 1.024 MHz, one dither of 13 uVrms in band (288.68 uVrms white per clock at `vi`, seeded, below the shaped floor and not the system-level budget dither). Amplitude is in dBFS of `vdd/2`. Seeds are averaged as power per bin before the SNDR.

Bench `testbenches/xschem/dsm2_core_tb_psd.sch`, runner and evaluation `testbenches/xschem/psd.py`. The netlist comes from `make sim-xschem TB=dsm2_core_tb_psd` (stop it after the netlist, a run takes 8 to 15 h), then for example `psd.py --run=-6,1,1,2,3,4 --chgtol 1e-18 --options rshunt=1e12 --outdir DIR` runs four seeds, `--post` evaluates the raws, `--swap sc_int2=<extracted netlist> --qclk` swaps the integrator for its extracted view with the quantizer clock on `di_clk`. A run that aborted late is evaluated on a window that ends at the abort (not before clock 200).

| amplitude | view | runs | SNDR |
| --- | --- | --- | --- |
| -1 dBFS | schematic | 1 | 78.1 dB |
| -3 dBFS | schematic | 1 | 76.8 dB |
| -6 dBFS | schematic | 4 | 72.4 dB (per run 67.7 to 80.4) |
| -6 dBFS, no dither | schematic | 1 | 83.5 dB |
| -20 dBFS | schematic | 4 | 58.2 dB |
| -40 dBFS | schematic | 1 | 45.4 dB |
| -60 dBFS | schematic | 1 | 30.4 dB |
| -6 dBFS | `sc_int2` extracted (earlier layout), `qclk` | 4 | 69.3 dB |
| -20 dBFS | `sc_int2` extracted (earlier layout), `qclk` | 4 | 52.4 dB |
| -6 dBFS | `sc_int2` extracted (final layout), `qclk` | 4 | 70.8 dB (per run 70.4 to 71.9) |
| -20 dBFS | `sc_int2` extracted (final layout), `qclk` | 4 | 57.7 dB (per run 56.1 to 60.6) |

- The floor fit over 10 to 200 kHz gives 19 dB per decade at -6 dBFS and an SQNR of 74.4 dB, against 78.0 dB ideal for a first-order loop at this amplitude.
- The -6 dBFS runs scatter by 13 dB, because two of them used a deck without breakpoints at the falling clock edge, whose steps add error (inference). The two runs of the final deck read 78.8 and 80.4 dB.
- `reltol` 1e-3 instead of 5e-3 moves the same seed by 0.8 dB, so the solver tolerance does not limit the SNDR.
- The extracted `sc_int2` costs about 6 dB at -20 dBFS (4 seeds, sd 0.4 dB). Its in-band floor below 500 Hz is flat at -80 to -88 dBFS per bin where the schematic falls to -100 dBFS. That was the extraction before the rework of `sc_int2`. The final extraction recovers most of it: 57.7 dB at -20 dBFS against 58.2 dB on the schematic. Against the same seeds of the final schematic deck it is 2.9 dB lower at -20 dBFS (seed 1) and 8.4 to 8.5 dB lower at -6 dBFS (seeds 1 and 3), with the in-band floor below 500 Hz near -85 dBFS per bin. The final swaps also take the schematic parts from a later netlist (bias values changed), so part of the gap may not be `sc_int2` (inference).
- The bench carries `VBRK0` to `VBRK7` (breakpoints after both clock edges), without them a 16.5 ms run aborts with "Timestep too small" in `clk_noverlap`. `savecurrents` is off because it grows the memory of an extracted run by 7 MB per clock.

## Layout

`layout/dsm2_core_gen.py` writes `layout/dsm2_core.gds` with KLayout (`make layout`). It imports the floorplan of `layout/dsm2_core_fp.py` (blocks, ring, pins), adds `dsm2_io_esd`, the routing and the decap fill, and stops on its own checks. Outline 150.5 x 178 um (26789 um2), the PR boundary on layer 189 in the top cell. Nothing above Metal4.

`layout/reference/dsm2_core_4941474.gds` is a frozen copy of the first complete layout of the previous version. `make layout` never writes it.

Placement (lower left to upper right, um):

| Block | x | y |
| --- | --- | --- |
| `vcm_gen` | 15.48 to 94.31 | 2 to 26 |
| `dsm2_io_vcmg` | 41.48 to 89.08 | 26.4 to 31 |
| `clk_noverlap` | 20.72 to 89.07 | 31.4 to 39.4 |
| `quantizer2_top` | 20.72 to 89.07 | 39.7 to 81.83 |
| `sc_int2` | 20.72 to 89.07 | 85.33 to 170.82 |
| `bias_gm` | 98.42 to 146 | 15.09 to 176 |
| `dsm2_io` | 2 to 13.98 | 88.2 to 165.13 |
| `quantizer2_lfsr` | 2 to 13.95 | 2 to 87.76 |
| `dsm2_io_clk` | 94.6 to 98.44 | 2.6 to 7.1 |
| `dsm2_io_esd` | 122 to 146 | 2 to 15 |
| `dsm2_osc` (variant) | 98.44 to 122.0 | 2.0 to 15.09 |

The signal column (`clk_noverlap`, `quantizer2_top`, `sc_int2`) is centred on x = 54.895. A psub guard ring runs at 0.84 um inside the outline.

Routing:

- Side channels left and right of the signal column carry Metal4 lanes, mirrored about the axis: the phase, `vo_p` / `vo_n` between vss lanes, vdd, and on the left `vcm_esd` from `vcm_gen` up to the `sc_int2` pin. Metal3 supply buses in the top channel over `sc_int2` close them.
- `vi` leaves the `sc_int2` bottom pin on Metal2, runs down a gap lane between `vcm_gen` and `bias_gm` with a vss lane each side, and east on Metal2 under the decap row below `bias_gm` to a Metal2 lane just west of `dsm2_io_esd`. `vcm_esd` takes the same way from `vcm_gen` on the next gap lane. Both enter the cell's west pins on Metal3 between its vss guard pins, which the routing joins to the vss lanes.
- `ibias_200n` runs on Metal4 from `bias_gm` to the `sc_int2` top pin between vss tracks. The `bias_gm` test output runs down the east lane, west on Metal3 below `dsm2_io_esd` and up into its pin.
- The ESD cell's vss and vdd Metal4 bars get Metal4 stubs at their bottom ends, joined along the bottom band to the east vdd / vss straps. The pad side of the cell runs on Metal3 to the east pins.
- The static controls, the LFSR buses, `d_qclk` to the LFSR and `do_q_dec` are grid-routed (A* on a 0.25 um grid, Metal2 to Metal4), each net closed against notches and its pads grown to the minimum area.
- `do_q` and `do_q_b` leave the quantizer on Metal2 and drop down gap lanes to the south pins.

Decap fill: 128 `sg13cmos5l_decap_8` cells (about 35 fF each, 4.5 pF in all, sim) in rows along both side channels, the gap, above `dsm2_io`, under `bias_gm` and in the top channel. They are flattened into the top cell, so the schematic carries their devices as `XMDN` and `XMDP` with m=128. About 10 % of the outline stays without metal of a block or the fill, accepted for DSA1.

Fill: DSA1 puts nofill over this macro plus a 10 um halo (Metal1 to TopMetal1) and over its outline (Activ, GatPoly). The macro draws no fill and no nofill markers.

The generator stops on routing nets closer than the spacing, routing too close to block metal of another net, a net the router cannot finish, a pad that cannot reach the minimum area, a decap count that differs from the schematic, off-grid vertices and shapes outside the outline. `CHECK_CONTROL=1 make layout` proves a failing check stops the target.

Checks in `registry.iic.jku.at:5000/iic-osic-tools:next` (image dd952ba01866), 2026-10-29:

- KLayout DRC is 0 at macro level. At regular level only the chip-level density rules fire (AFil.g, M1.j to M4.j, TM1.c).
- Magic DRC: M1.e inside `sc_int2` (its `ota_fcasc2_top`, core y 153.755 and 155.535), present in `sc_int2` alone, and 12 CntB.h1 inside the IHP `sg13cmos5l_SecondaryProtection` of `dsm2_io_esd`, waived in `macros/dsm2_io`.
- `make klayout-lvs` (deep) matches. `make magic-lvs` matches with `cap_cmomf` ignored (`scripts/netgen_setup.tcl`), property errors only for the schematic-only `mm_ok` property (2530, on MOS, `rhigh` and `rppd`), no value differs. The logs of the delivered GDS are in `final/lvs/`.
- `scripts/check_lef.py` (run by `make lef`): the layout agrees with the frozen LEF (outline, every pin rect on pin metal with its label, no metal outside the OBS except at its pin). It warns about 8 small supply pads in the 1 um pin windows of the west edge, each at least 0.25 um from its pin: 7 of `dsm2_io` (x 2.625 to 2.915) and one vss pad at x 2.03 to 2.41, y 3.56 to 3.94 near `do_q_dec`.

PEX (`make magic-pex`, mode 3 by default):

- `scripts/pex_gds.py` flattens `sc_int2`, `vcm_gen` and `quantizer2_top` one level and writes the pad layout with their MoM caps as plain labelled metal. `scripts/pex_caps.py` drops the coupling between the two plates of each cap and adds the caps back at the model value.
- `quantizer2_top` draws its flying caps flat (marker and metal, no cap cell). `scripts/pex_flat_caps.py` reads their plate nets from the KLayout LVS of `dsm2_core` (so `make klayout-lvs` has to run first) and labels the plates. 104 caps in all: 82 of `sc_int2`, 8 of `vcm_gen`, 14 of `quantizer2_top` (its 2 dummies, both plates on one net, are left out).
- Mode 3: 20789 resistors, 7063 capacitors, 2885 devices and caps. Mode 2: 192 resistors (the 1 TOhm ties of capacitor-only nodes), 5364 capacitors.

## Integration Requirements

- **Controls at 1.2 V.** The `di_` pins on the west edge are 1.2 V register outputs of DSA1. `dsm2_io` level-shifts them to 1.5 V and slew-limits `di_ena` inside the block. `di_clk` takes 1.5 V levels.
- **Loads.** The benches drive `do_q` / `do_q_b` into 80 fF (the pad inputs) and `do_q_dec` into 15 fF.
- **Fill.** No fill inside the macro and its 10 um halo (DSA1 nofill, see Layout).
- **Oscillator (variant).** The ring needs `di_ena` high, because `bias_gm` starves its test bank while `di_ena` is low. Switch `di_osc_en` and `di_clk_sel` only with `di_ena` and `di_rst_b` low, and set `di_clk_sel` high only with `di_osc_en` high, or the pad drives low against the board clock. Benches load `do_clk_osc` with 80 fF and `do_osc_oe` with 15 fF and need ngspice `reltol` 1e-4 (false `dfrbp_1` toggles at 1e-3). The clock runs at about 0.65 MHz at code 4 on the extracted view, so the lab sets it with `di_trim`.

## What Is Missing

- A full-record SNDR of the wave 4 schematic with dither on (running) and of the extracted view (after the delivery, on a faster machine).
- The VACASK operating point of the wave 4 schematic. It fails at t = 0 (NaN, Newton stalls in the `bias_gm` test bank and the `clk_noverlap` delay chain). `testbenches/vacask/netlist.py` with `DSM2_STARTUP=1` ramps the supplies and steps three controls instead, which gets it started. The full mode 3 extraction finds its operating point without that.
- The previous version's open points (the extra wrong decisions and the common mode spike of the extracted `sc_int2`, see Results) were not rechecked on wave 4.
- A CACE datasheet, noise and mismatch runs.

## Nice to Have

Optional additions, none designed yet. Each one stays switchable, so the core runs unchanged with all of them off.

- **On-chip clock from a current-controlled ring oscillator.** Current-starved inverter stages biased by another copy from the bias core, so the frequency follows the reference and its trim. Power is the point: at 1.024 MHz the stage switching charge is tens of nA, but each starved stage needs a restoring buffer (or a Schmitt trigger at the output) so slow edges do not draw crowbar current. A clock mux in front of `clk_noverlap` chooses between the oscillator and the external `di_clk`, its select bit comes from the SPI registers outside this repo, external by default. Open: the frequency spread over PVT against what the modulator tolerates, and a separate frequency trim or a divider.
