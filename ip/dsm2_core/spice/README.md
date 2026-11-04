# dsm2_core netlists for ngspice, oscillator variant (quantizer2 preset fix)

Read-only snapshot for the DSA1 start-up and supply-bounce bench, 2026-11-01. It replaces the previous snapshot. The only circuit change is in `quantizer2_top`: its output latch preset is now logical, so the latch no longer fights the preset devices while `di_ena` or `di_rst_b` is low. Ports, pin order and layout outline are unchanged.

| file | content |
| --- | --- |
| `dsm2_core_sch.spice` | schematic, subckt `dsm2_core` with every child subckt (standard cells come from the PDK) |
| `dsm2_core_pex3.spice` | extracted, subckt `dsm2_core_pex`, Magic full RC (mode 3, flat), from `dsm2_core.gds` md5 00624787128efe33ca6ddf5273170e56, MoM caps of `sc_int2`, `vcm_gen` and `quantizer2_top` at the model value |
| `header.spice` | corner libraries, OSDI loads, options, and the notes on options |
| `smoke_sch.spice`, `smoke_pex3.spice` | 5-clock smoke benches, also a minimal example instance |
| `MD5SUMS` | checksums of the files above |

## Ports

Both subckts have the same port order:

`vi vcm di_clk di_ena di_rst_b di_trim[3] di_trim[2] di_trim[1] di_trim[0] di_dith_en di_dith_amp[1] di_dith_amp[0] di_vcm_ext di_btest_en di_qout_en do_q do_q_b do_q_dec ibias_test vdd vss di_osc_en di_clk_sel do_clk_osc do_osc_oe`

- Oscillator pins: `di_osc_en` and `di_clk_sel` take 1.2 V highs like the other register inputs. `di_clk_sel` high selects the internal oscillator instead of `di_clk`. `do_clk_osc` is the oscillator clock and `do_osc_oe` the pad output enable, both at 1.5 V levels. The smoke benches keep the oscillator off and load `do_clk_osc` with 80 fF and `do_osc_oe` with 15 fF.

- 1.5 V domain: `vdd` (VDDA, 1.5 V), `di_clk` (1.024 MHz, 1.5 V levels), the outputs `do_q`, `do_q_b` and `do_q_dec` (1.5 V levels), and the analog pins `vi`, `vcm` (vdd/2) and `ibias_test`.
- 1.2 V levels: `di_ena`, `di_rst_b`, `di_trim[3:0]`, `di_dith_en`, `di_dith_amp[1:0]`, `di_vcm_ext`, `di_btest_en` and `di_qout_en` take 1.2 V highs from the register file. `dsm2_io` shifts them to 1.5 V inside.
- Bench levels: trim code 4 (`di_trim` = 0100) gives 200 nA. `di_qout_en` high enables `do_q` / `do_q_b`. With `di_vcm_ext` low, `vcm_gen` drives `vcm`. The benches hold the `ibias_test` pad at 0.5 V and load `do_q` / `do_q_b` with 80 fF and `do_q_dec` with 15 fF.

Minimal instance (see `smoke_*.spice`):

```
.include header.spice
.include dsm2_core_sch.spice
x1 vi vcm di_clk di_ena di_rst_b di_trim[3] di_trim[2] di_trim[1] di_trim[0] di_dith_en di_dith_amp[1] di_dith_amp[0] di_vcm_ext
+ di_btest_en di_qout_en do_q do_q_b do_q_dec ibias_test vdd 0 di_osc_en di_clk_sel do_clk_osc do_osc_oe dsm2_core
```

For the extracted view, include `dsm2_core_pex3.spice` and use `dsm2_core_pex`.

## Options and speed

- Use `header.spice` as is. At -40 C add `.options gmin=1e-10 reltol=1e-3 trtol=7`. Without it, extracted runs at -40 C stopped on "Timestep too small" in the `dparea` part of the core-side `dpantenna` of the `ibias_test` ESD cell.
- The start of an extracted transient is fragile at that same diode. A smoke bench with `vi` driven by one 0 V source from `vref` stalled at 5.6e-14 s on "Timestep too small". The same bench with `vi` as two series 0 V sources (`VI2 vi vi_dc 0`, `VI1 vi_dc vref 0`) runs, with the same operating point. If your bench stalls there, first change the node ordering around `vi` / `ibias_test` (an extra series 0 V source).
- Clock timing at ff 1.55 V -40 C needs the tighter options. `reltol=5e-3 trtol=10` gave a false 0.40 ns phase gap there (3.33 ns with the tighter options).
- At `reltol` 1e-3 and looser, ngspice can flip an idle `sg13cmos5l_dfrbp_1` latch between two time points. Use `reltol=1e-4` where flop states matter.
- The dsm2 loop benches add breakpoint sources every 0.25 ns from 1 to 4 ns after both clock edges, so the quantizer decision is never stepped over. Use them for any loop result that matters.
- Smoke results (5 clocks, tt 1.5 V 27 C, average over clocks 2 to 5 just after the reset release): schematic 13.1 uA, `vcm` 0.744 V, 305 s. Extracted 14.5 uA, `vcm` 0.734 V, 995 s with the operating point included. Both exit 0, oscillator off. These show start-up behaviour, not the steady `vcm` and supply current, which depend on the first decisions after reset.

## Start-up

Sanity checks of one schematic run each (ngspice, `reltol=1e-4`), `di_ena` stepped up at full supply, `di_rst_b` released 60 us later (140 us at ss). The rows without `quantizer2_top` come from runs with the previous `quantizer2` version, whose other blocks are unchanged.

| corner | `ibias_200n` within 1 % after `di_ena` | inrush without `quantizer2_top`, 100 ns / 10 ns peak | charge in the first 10 us | running current after reset | disabled |
| --- | --- | --- | --- | --- | --- |
| tt 1.5 V 27 C | 40.9 us | 64 / 240 uA | 40.8 pC | 12.0 to 12.6 uA | 0.65 uA |
| ff 1.55 V 125 C | 29.2 us | 137 / 365 uA (above 80 uA for 0.1 us, from `clk_noverlap`) | 124 pC | 22.8 to 23.7 uA | 8.3 uA |
| ss 1.45 V -40 C | 71.2 us | 32 / 151 uA | 32 pC | 9.8 to 10.3 uA | 0.2 uA |

- `quantizer2_top` with the preset fix: at tt 38 uA over 100 ns and 177 uA over 10 ns at enable, 33 pC in the first 10 us, 2.7 to 4.2 uA during reset, 3.9 uA running. At ff 1.55 V 125 C 82 uA over 100 ns and 201 uA over 10 ns.
- While `di_rst_b` is low the quantizer output is held, so the integrator runs into saturation (`vo_p - vo_n` about 1.4 V). After `di_rst_b` rises it takes about 17 clocks at `vi` = +0.3 V before the bit stream follows the input, longer for inputs closer to full scale.
- Oscillator variant, tt, oscillator enabled 1 us and selected 2 us after `di_ena`: 99 uA over 100 ns (above 80 uA for 0.08 us right after `di_ena`), 389 uA over 10 ns, 53 pC in the first 10 us, 16.0 uA running of which the oscillator draws 4.9 uA. The oscillator runs at 806 kHz at trim code 4 (schematic).
- Oscillator variant, ff 1.55 V 125 C, same sequence: 215 uA over 100 ns (`clk_noverlap` 110 uA, `quantizer2_top` 82 uA in that window, above 80 uA for 0.12 us in all), 546 uA over 10 ns (`clk_noverlap` 301 uA, `quantizer2_top` 188 uA), 254 pC in the first 10 us, 29.0 uA running, 8.5 uA while disabled. Both peaks sit at the first clock edge after `di_ena`, before the oscillator is enabled.

