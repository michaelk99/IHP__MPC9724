# ihp-sg13cmos5l Quantizer with Dither (quantizer2)

The clocked quantizer of `dsm2_core`: the StrongARM latch comparator and NOR SR latch of `macros/quantizer`, plus a switchable 8-level dither against the idle tones of the first-order loop, pad drivers for the bit stream and a copy for the decimator. `macros/quantizer` stays as it is for the course modulator `macros/dsm`. **Schematic, benches and layout done (routed, DRC and both LVS clean), no PEX benches, no CACE datasheet.**

## Ports

`quantizer2_top`:

| Port | Direction | Meaning |
| --- | --- | --- |
| `vi_p`, `vi_n` | in | differential input, the integrator outputs |
| `di_clk` | in | quantizer clock, decision on the rising edge |
| `di_en` | in | enable, gates the comparator clock, presets the latch and powers the dither ladder |
| `di_rst_b` | in | active-low reset, presets the latch |
| `di_dith_en` | in | dither on (high) or off (low, the comparator is then today's quantizer) |
| `di_amp_s[3:0]`, `di_amp_s_b[3:0]` | in | one-hot dither amplitude select from `quantizer2_lfsr`: s[0] 100 %, s[1] 67 %, s[2] 133 %, s[3] 33 % |
| `di_dith[2:0]` | in | the three dither bits from `quantizer2_lfsr` |
| `di_qout_en` | in | pad drivers on (high). Low holds `do_q` and `do_q_b` low |
| `do_qi`, `do_qi_b` | out | latch outputs, NRZ, to the `sc_int2` DAC select |
| `do_q`, `do_q_b` | out | pad drivers (and2 with `di_qout_en`, inv_1, inv_2), for the IOPadOut4mA inputs |
| `do_q_dec` | out | ungated copy (inv_1, inv_2) for the decimator, with a dummy of the same load on `do_qi_b` |
| `vdd`, `vss` | inout | supply |

`quantizer2_lfsr`: `di_clk`, `di_dith_en` (reset while low), `di_dith_amp[1:0]` (00 100 %, 01 67 %, 10 133 %, 11 33 %), `do_dith[2:0]`, `do_amp_s[3:0]`, `do_amp_s_b[3:0]`, `vdd`, `vss`. Its 11 outputs go to the `quantizer2_top` inputs of the same names.

The preset sits in the last buffer stage of the latch inputs. While `di_en` or `di_rst_b` is low, `XGATE_P` (nand2_2 of `d_p_2` and `d_preset_b`) holds `d_p_b` high and `XGATE_N` (nor2_2 of `d_n_2` and `d_preset`) holds `d_n_b` low. The NOR latch then holds `do_qi` and `do_q_dec` low and `do_qi_b` high whatever the comparator decides, and `do_q` is low and `do_q_b` high when `di_qout_en` is high. No device fights another. The earlier preset pulled the latch outputs with thick-oxide devices against the nor2_2 drivers and lost: with the latch holding `do_qi` high it drew about 195 uA, and during reset with the clock running the outputs followed the comparator.

Preset sanity checks on the schematic, not characterisation. The transient runs disabled, then enabled in reset with the clock running and the input alternating +-50 mV every clock, releases reset in the low window, runs, resets again and releases during an evaluation, runs and disables again:

| | tt 27 C 1.5 V | ss -40 C 1.45 V | ff 125 C 1.55 V |
| --- | --- | --- | --- |
| disabled, latch started either way | 46 nA | 4.4 nA | 3.1 uA |
| same, Magic PEX (mode 1) | 46 nA | 5.0 nA | 3.1 uA |
| earlier preset, latch started with `do_qi` high | 195 uA | 159 uA | 223 uA |
| supply in reset with the clock running | 4.2 uA | 3.2 uA | 8.0 uA |
| output transitions in reset (10.75 clocks) | 0 | 0 | 0 |
| decisions after both releases | 16 of 16 right | 16 of 16 right | 16 of 16 right |

The release during an evaluation writes the held decision with one clean edge. The gate in front of the latch costs up to 26 ps on the rising `do_qi` edge (nor2_2, two PMOS in series), the falling edge (nand2_2) comes 0 to 18 ps earlier. At 10 mV and 1 mV the rising edge now trails the falling one by 55 to 80 ps instead of 39 to 57 ps, against a half period of 488 ns. Clock to `do_qi` at mid rail, overdrive counted from the bisected trip point, earlier preset and new one in the same run, change in brackets:

| overdrive | tt rising | tt falling | ss -40 C 1.45 V rising | ss falling | ff 125 C 1.55 V rising | ff falling |
| --- | --- | --- | --- | --- | --- | --- |
| 10 mV | 0.859 ns (+22 ps) | 0.792 ns (+2 ps) | 0.967 ns (+21 ps) | 0.887 ns (-2 ps) | 0.855 ns (+12 ps) | 0.800 ns (-3 ps) |
| 1 mV | 0.983 ns (+26 ps) | 0.911 ns (0 ps) | 1.114 ns (+17 ps) | 1.038 ns (-3 ps) | 1.000 ns (+13 ps) | 0.935 ns (-12 ps) |
| 1 uV | 1.639 ns (+12 ps) | 1.065 ns (-10 ps) | 1.731 ns (0 ps) | 1.299 ns (-12 ps) | 1.705 ns (+2 ps) | 1.157 ns (-18 ps) |

## Hierarchy

| Cell | What it is |
| --- | --- |
| `quantizer2_top` | SR latch, enable and reset path, pad drivers, `do_q_dec` |
| `quantizer2_sal` | the StrongARM, input and tail fingers 4.0u, plus the three dither pairs and their row dummies |
| `quantizer2_dith` | the dither network: rhigh ladder, amplitude mux, gate switches, flying caps, plate switches, phase logic |
| `quantizer2_lfsr` | 17 bit LFSR and the amplitude decoder, its own cell because it sits in the `dsm2_core` west column |

`macros/inv_en` provides the thick-oxide inverters of the enable path.

## Dither

Three auxiliary pairs (1.5u, 3u and 6u, L 0.5u, weights 1 : 2 : 4) sit in parallel with the input pair. Each aux gate is held at its own main input plus or minus delta by a flying capacitor (`cap_cmomf`, 40.1 fF units of w 7.6u x l 4.1u, 7 per side plus one dummy unit with both plates on the plate node). The schematic splits the units by layout orientation: the KLayout LVS deck reads an x-mirrored `cap_cmomf` with its plates swapped, so the mirrored units (left columns 0 to 2, right column 3) carry the gate net on the other terminal. The model is plate to plate only, so the circuit is the same. While `di_clk` is high (after a delay of about 7 ns) the gates sit on the ladder taps and the cap plates on the ladder centre. About 7 ns after `di_clk` falls the gates float and the plates move to `vi_p` / `vi_n`, so the next decision sees `vi + delta` on each aux gate. Delta comes from an rhigh ladder across `vdd` (RTOP and RBOT 80.4 um, eight 4.08 um taps, 2.6 uA at tt 27 C and 3.3 uA at ff 125 C 1.55 V while `di_en` is high, sim), so the amplitude follows the full scale. Each bit adds plus or minus A/7 times its weight, so the 8 codes give A (2c - 7) / 7.

The phase delay matters. The precharge lifts vtail by about 0.8 V within 1 ns of the falling clock, and a floating aux gate follows through its Cgs. With a 1 ns delay the amplitude came out 40 % high, with the gates floating on purpose through the jump it got worse. The gates are therefore held on the ladder through the jump. What remains is a gate common mode 44 mV above the input common mode, the same within 2 mV at three corners and for alternating codes, and the ladder ratio absorbs it.

Amplitude, code 7, bisection on the schematic (ladder at half the earlier resistance, inner units 4.08 um), vcm at vdd/2. Sanity checks, not characterisation. At tt one of the 11 trials hit `Timestep too small` and was flagged, the other corners measured every trial:

| | tt 27 C | ss 27 C | ff 27 C | sf 27 C | fs 27 C | ss -40 C 1.45 V | ff 125 C 1.55 V |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A (mV) | 76.5 | 75.9 | 78.0 | 76.7 | 77.8 | 70.0 | 82.5 |
| code 3 level (mV) | 11.0 | 10.8 | 11.0 | 10.8 | 11.2 | 10.1 | 11.8 |

All seven are inside the 67 to 85 mV window of the system model. At tt the amplitude selects give 65.5 % (s[1]), 136.5 % (s[2]) and 30.5 % (s[3]) of s[0]. Halving the ladder at the same length ratio (3.83 um taps) gave about 5 % less amplitude, so the taps went to 4.08 um.

LFSR: 17 bit XNOR Fibonacci register, taps 17 and 14, three new bits per clock by a leap-forward update. Its code sequence repeats after 131071 clocks, and all 8 codes appear equally often. A 16 bit register would repeat after 21845 clocks, because 3 divides 65535. 200 clocks from reset match the python model at tt, ss 125 C and ff -40 C.

## Dither off against the quantizer, and the outputs

Real clock period, 1 mV overdrive, sanity checks:

| | tt 27 C | ss 125 C | ff -40 C |
| --- | --- | --- | --- |
| clock to latch, `quantizer` | 0.865 ns | 1.218 ns | 0.653 ns |
| clock to latch, `quantizer2` dither off | 0.885 ns | 1.242 ns | 0.669 ns |
| clock to `do_q` pad (80 fF) | 1.053 ns | 1.459 ns | 0.800 ns |
| clock to `do_q_dec` (and2_1 plus 15 fF) | 0.947 ns | 1.321 ns | 0.718 ns |
| input charge per pin, `quantizer` / off / dither on | 43.0 / 45.9 / 75.3 fC | 41.6 / 44.4 / 73.2 fC | 46.2 / 49.3 / 80.1 fC |

These timings were taken with the earlier preset, the gate in front of the latch adds up to 26 ps to the rising `do_qi` edge (see Ports). With the dither off the offset is 0 within the bench resolution at seven corners. The latch is 16 to 24 ps slower and the kickback 7 % larger: the wider input fingers, and the latch now also drives the gating and2 and the `do_q_dec` inverter. With the dither on the differential kickback is 9 to 11 fC per decision. ngspice has no device noise, so noise was not compared. With the dither off the aux pairs only add junction capacitance.

## Sizing

`scripts/sizing/size_quantizer2.ipynb` derives the comparator timing (integration, regeneration time constant, decision time, metastability window), the input noise, the dither ladder, the amplitude, the flying capacitors and the RC and Ron timing of the dither network from the spec with the gm/ID tables of the course, then compares them with the schematics. It was written after the schematic. It reproduces the aux width for 75 mV (10.5 um), the 1 : 2 : 4 weights, the ladder current (2.63 uA against 2.6 uA), the amplitude selects (75.2 mV at `s[0]` with ideal coupling against 76.5 mV simulated), the 7.1 ns phase delay, the kickback ratio (1.66 against 1.64) and a regeneration tau of 74 ps against 95 ps. The main disagreements: the input pair (16u) and tail (32u) are 8 times wider than speed and noise need and are set by offset, which the Monte Carlo has to settle. With the lookup gate capacitance the model amplitude is 85.2 mV, 11 % above the simulation. The decision time, the pad path and the preset gates come out 0.24 to 0.38 ns, 2.4 times and 2.5 times short of the simulation. It also finds that the dither plates act as a switched-capacitor resistor of 22 MOhm (45 nS) per side on the integrator outputs, as large as the OTA output conductance, which is open for the dither-loss investigation.

## Testbenches

`quantizer2_tb_offset`, `quantizer2_tb_convtime` and `quantizer2_tb_noise` are the benches of `macros/quantizer` (see its README for how they work and what they cannot say), rewired to `quantizer2_top` with the dither off and `do_qi` / `do_qi_b` as the measured outputs. The dither benches (bisection per code and corner, the real-period timing, gating and preset run, the LFSR check) are scratch scripts so far.

## Layout

`layout/quantizer2_gen.py` (`make layout` routes, `PLACE_ONLY=1` stops at the placement). 68.35 x 42.13 um, the `sc_int2` width with one shared axis at x 34.175. Bands D and F are mirror images about the axis in their devices. In the routing the per-side exceptions (MPLAD and its net1, MCDLY, the RDLY ends, di_clk, the west select pins) are drawn on one side only. Bottom to top:

- band D, 0 to 14.45 um: the ladder as two stripe blocks on the axis (0.70 um stripe pitch, 0.2 um more below and above the two RL rows, whose mid-row heads would otherwise sit too close to the neighbouring SalBlock), the plate switches, at both outer ends the gate switches, pull-downs and amplitude mux, MCDLY / MCDLYD and MPLAD / MPLADD. The top 3 um is an empty strip where the four plate nets and the five Metal3-lane gate nets cross the axis, each on a fixed slot (Metal2 or Metal3) next to it.
- band F, 14.75 to 31.27 um: the StrongARM with its aux row and the flying caps, 2 x 4 units a side. A channel of 13 lanes between the caps and the StrongARM carries the dither nets from band S down to band D, four more lanes run in the cap gaps. Each net comes down only on the side of the cell that drives it, the lane on the other side is cut at the band D top and tied to vss at the row 1 rail.
- a 2.9 um channel: the eight Metal4-lane gate nets cross the axis here on drawn Metal4 tracks.
- band S, 34.17 to 42.13 um: two standard-cell rows (latch, buffers, pad drivers, phase logic, gate decode) and the thick-oxide cells at both ends, the two `inv_en` on the left, two HV dummy cells on the right.

Routing: pass 1 routes the left half of bands D and F (negotiated congestion router on a 0.255 um grid, Metal2 to Metal4) and mirrors it, pass 2a joins the halves and the west select pins in band D, pass 2b routes band S and the channel. The generator then merges each net, stretches pieces under the minimum metal area, drops duplicate via cuts and checks spacing, mirror symmetry and the outline. Pass 1 does not converge from scratch in `:next` (`d_c0[1]` and `d_c1[2]` stay unresolved), so its result is the tracked `layout/quantizer2_pass1.json`, loaded by default (`PASS1_REROUTE=1` routes it again).

Pins, held at these places by the generator because the `dsm2_core` floorplan and the DSA1 LEF depend on them: `di_clk` bottom, Metal3, x 33.175. `do_qi` / `do_qi_b` top, Metal3, x 32.645 / 35.705. `do_q` / `do_q_b` east edge, Metal3, y 33.420 / 32.910. `vi_p` west edge and `vi_n` east edge, Metal3, y 1.015. West edge, Metal2: `di_amp_s[3:0]` y 5.605, 5.095, 4.585, 0.250, `di_amp_s_b[3:0]` y 7.645, 7.135, 6.625, 6.115, `di_dith[2:0]` y 34.950, 40.305, 39.540, `di_dith_en` 40.815, `di_en` 38.265, `di_qout_en` 37.755, `di_rst_b` 41.580, `do_q_dec` 38.775. `vss` the Metal1 bottom rail, `vdd` the Metal1 row rail.

Verification, all in `registry.iic.jku.at:5000/iic-osic-tools:next` (dd952ba01866), last run 2026-10-31 on the logical preset: `make klayout-drc DRC_LEVEL=regular` only the chip-level density rules (AFil.g, GFil.g, M1.j to M4.j, TM1.c). `make klayout-drc` (macro level) 0. In the `dsm2_core` floorplan (`make fp` in `macros/dsm2`) regular DRC also showed only density rules, Sal.d included (checked on the earlier ratioed-preset layout). `make magic-drc` 0. `make klayout-lvs` match. `make magic-lvs` match uniquely with `cap_cmomf` ignored (Magic does not extract it, see `scripts/netgen_setup.tcl`), plus the `mm_ok` property notes on the MOS devices.

`layout/quantizer2_lfsr_gen.py` places and routes the LFSR, its output buffers and the amplitude decoder in three columns of standard cells turned by 90 degrees, 11.73 x 85.76 um, vss on the west edge, no Metal3 inside so a Metal3 track can pass over it. klayout-lvs match, magic-lvs OK, Magic DRC 0, KLayout regular DRC only density.

## What Is Missing

- PEX and the benches on the extracted views.
- The amplitude corners rerun on the schematic with the cap units split by orientation (the circuit is unchanged).
- The full `dsm2_core` loop SNDR runs with `quantizer2`, after the quantizer clock edge is chosen (the present qclk costs 8 to 11 dB).
- A CACE datasheet.
