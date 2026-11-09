# Switched-Capacitor Integrator with ota_fcasc2

The first integrator of the delta-sigma modulator: the shared-capacitor SC network of Figure 7.11, the folded cascode OTA and the switched-capacitor common-mode feedback, wired into one block. Schematic and layout, see [Layout](#layout).

`sc_int2` is `sc_int` with the OTA swapped and the capacitors made real. The OTA instance `xamp1` is `ota_fcasc2_top` instead of `ota_fcasc_fd_top`, which has the same ten pins in the same places, so position, pins and wiring are untouched. The ideal `capa` capacitors are `cap_cmomf` units and `cmfb_sc` is replaced by its copy `cmfb_sc2`, see [Capacitors](#capacitors). `sc_int` keeps `ota_fcasc_fd_top`, `cmfb_sc` and its ideal capacitors because the course modulator `macros/dsm` uses it. Everything else is a renamed copy: switches, clocks and the testbenches.

## Ports

| Port | Direction | Meaning |
| --- | --- | --- |
| `vi` | in | single-ended input, referred to `vdd/2` |
| `vo_p`, `vo_n` | out | integrator outputs |
| `di_q`, `di_q_b` | in | the quantizer decision and its complement, which steer the DAC |
| `di_phi1`, `di_phi2` | in | the two non-overlapping clock phases, generated outside this block, inverted inside by `inv_lv` into `d_phi1_b`, `d_phi2_b` |
| `vcm` | in | common-mode reference for the right plates and for the CMFB |
| `ibias_200n`, `di_ena` | in | OTA bias current and enable |
| `vdd`, `vss` | inout | supply, and the DAC levels |

Net names follow the designer's etiquette (`v` voltage, `i` current, `d` digital, `di_`/`do_` on block pins, `_b` complement). Inside, the C1 plates are `vc1l_p`, `vc1r_p`, `vc1l_n`, `vc1r_n` and the DAC switch middle nodes `vh_p`, `vl_p`, `vh_n`, `vl_n`. `sc_int` keeps the course names (`v`, `v_b`, `vphi1`, `vphi2`). The symbol has no parameters. The capacitor values come from the unit counts in [Capacitors](#capacitors), `a1 = 2*C1/C2 = 1/3` as in the system-level loop.

## Capacitors

SG13CMOS5L has no MIM capacitor, so every capacitor is a `cap_cmomf` (metal fringe MoM, PDK PCell and Verilog-A model) on Metal1 to Metal4. The model is a pure area law, C = 1.287 fF/um2 x l x w on this stack, with no substrate node, and it reads high against a field solve. The units are therefore sized for the capacitance the silicon is expected to have, and the schematic carries the model value.

The design unit is 32 fF (ci = 2 units = 64 fF, cf = 12 units = 384 fF, a1 = 2 C1/C2 = 1/3). Estimate of the real C: the M2..M4 dead-rim fit 0.861 fF/um2 x (l - 0.43)(w - 0.43), taken as a ratio to its own model, scaled by the Palace electrostatic solve of the M1..M4 shapes: EM over the fit is 0.938 for the unit shape and 0.932 for the refresh shape (EM sim, a 2.0 x 12.42 unit gave 21.4 fF against 31.97 fF by the model, a 2.0 x 4.14 refresh cap 6.57 fF against 10.66 fF). Per plate the solve gives 1.62 / 1.68 fF to the substrate on the isolated 2.0 x 12.42 unit (EM sim).

| capacitor | w x l | per side | C model, per device | C estimated real, per device |
| --- | --- | --- | --- | --- |
| unit: `C1P`, `C1N` (2), `C2P`, `C2N` (12), `cmfb_sc2` sense (3) | 3.0u x 11.39u | | 43.98 fF | 32.0 fF |
| `cmfb_sc2` refresh `C2`, `C4` | 3.0u x 4.105u | 4 | 15.85 fF | 10.66 fF |

C1 over C2 is exactly 1/6 by unit count whatever the unit is worth. Sense over refresh is 2.25 by the estimate (2.08 by the model), because the refresh unit loses more of its area to the rim. **Schematic simulations use the model value, about 1.37 x the estimated real C for the unit and 1.49 x for the refresh cap.** The PEX view uses the model value too (see [Layout](#layout)). The final shapes go back to the EM solve, which confirms or resizes them, and the unit size is one constant pair in `layout/sc_int2_gen.py` (`CAP_W`, `U_L`) plus the schematic w and l. The units are vector instances (`C2P[11:0]`), one device each.

Where the `cap_cmomi` units this replaced relied on their substrate shunt (the model hung 4.2 fF per unit off MINUS), nothing in the schematic replaces it now. The shunt put 50.5 fF per side on the OTA outputs and was the measured cause of the leak rising to 1.7 times the gain prediction. The real plate to substrate capacitance is in the PEX view, from the extraction. `cap_cmomf`'s 1 pS DC anchor sits across its plates instead of from each plate to the substrate, 12 pS across C2 per side, at most 3e-5 leak per cycle by hand (inference).

The dummy ring and decoupling of the layout are in the schematic as real devices on one block of the sheet, between `vdd` (PLUS) and `vss` (MINUS):

| instance | w x l | count | C each, model |
| --- | --- | --- | --- |
| `CDUM_STRIP[7:0]`, ring rows | 3.0u x 11.39u | 8 | 43.98 fF |
| `CDUM_DCOL[17:0]`, dummy column and ring corners | 3.0u x 5.6u | 18 | 21.62 fF |
| `xcmfb1.CDUM_COL[13:0]` (in `cmfb_sc2`), outer column and one in each refresh row | 3.0u x 2u | 14 | 7.72 fF |

Together 849 fF between the rails (model). They touch no signal node and the bench supplies are ideal sources, so they change only the simulation time.

The effective values for the benches are the `ci` and `cf` vars of the VACASK decks (87.954 fF, 527.724 fF, model) and `.param cu` of the leak bench. They are not circuit parameters, the servo and sampler blocks and `post.py` read them.

## Structure

Per Figure 7.11 the two branches swap roles every phase, which is what performs the single-ended to differential conversion:

| | upper `C1P` left plate | lower `C1N` left plate |
| --- | --- | --- |
| phase 1 | `vi` | DAC |
| phase 2 | DAC | `vi` |

The right plates sit at `vcm` during phase 1 and at the OTA virtual grounds during phase 2, so both capacitors deliver their charge in phase 2.

The DAC drives both left plates to the **same** rail, `vdd` when `di_q` is high and `vss` when `di_q_b` is high. That is not a common-mode signal, because at any instant one branch is sampling the input while the other delivers the DAC charge. Each DAC connection is a series pair of switches, one gated by the phase and one by the decision, which forms the AND without needing logic gates.

`C2P` and `C2N` are cross-connected, `C2P` from `vvg_n` to `vo_p` and `C2N` from `vvg_p` to `vo_n`, which is the polarity the OTA testbench `ota_fcasc2_top_tb_tran.sch` uses and is what makes the feedback negative.

The common-mode loop is closed here: `xcmfb1` senses `vo_p` and `vo_n`, takes the OTA's own `vbn` as its reference, and drives `vfb` back into the OTA.

## Differences from sc_int

| | `sc_int` | `sc_int2` |
| --- | --- | --- |
| OTA | `ota_fcasc_fd_top`, tail 800 nA, hand-drawn layout | `ota_fcasc2_top`, unit-device sizing from the 200 nA bias, `A0` 58.8 dB (sim, see `macros/ota_fcasc2`) |
| library path | `../ota_fcasc_fd` | `../ota_fcasc2` |
| leak per cycle, leak bench | 4.70e-5 | 3.50e-4 (sim, 3.22e-4 with MPR at 0.5/13 before 7c33e1e, ideal capacitors 2.10e-4) |
| capacitors | `capa` 64 fF and 384 fF, ideal | `cap_cmomf` units, 2 and 12 of 32 fF estimated real (43.98 fF model), see above |
| CMFB | `cmfb_sc`, `capa` 100 fF and 10 fF | `cmfb_sc2`, `cap_cmomf`, 96.0 fF and 10.66 fF estimated real (131.9 fF and 15.85 fF model) |

`ibias_200n`, `di_ena`, `vdd`, `vss` and the common-mode loop through `vfb` and `vbn` are the same. The Makefile of `sc_int2` also differs from the copy it started from: `sim-all` runs the step and leak benches, the CACE targets are gone because there is no datasheet, and `sim-xschem` defaults to `sc_int2_tb_step` and tolerates the exit code 10 that xschem returns on the step and leak benches although the netlist is complete. `scripts/check_pex_ports.py` skips instance parameters on the `.subckt` line, which the former `cmfb_sc cap=100f div=10` instance tripped as dangling ports.

## Neighbouring Macros

This macro instantiates cells from other macros, added to the library path in `schematic/xschem/xschemrc` and `testbenches/xschem/xschemrc`:

- `../ota_fcasc2` for `ota_fcasc2_top`
- `../cmfb_sc2` for `cmfb_sc2`
- `../sw_tgate` and `../sw_tgate_cmfb2` for the switches
- `../clk_noverlap_ideal` for the clock generator of the benches

## What Is Missing

- A clock generator. `di_phi1` and `di_phi2` are inputs and must be non-overlapping.
- A CACE datasheet.
- Why the PDK transmission gates show 3.1 times the kT/C1 variance of ideal switches in transient noise, see `doc/noise-budget.md`. A pnoise on one sampling switch or an ngspice or Spectre cross-check would tell whether pnoise_idsw understates the switch term or VACASK overstates it.
- The 150 nA OTA bias that `doc/noise-budget.md` proposes needs a `bias_gm` change and a settling sweep with `bias_gm`.
- `macros/dsm/scripts/dsm_system.py` still takes kT/C as 2kT/(OSR C1) and the old closed-loop OTA numbers as defaults, unlike `noise_budget.py`. Changing it moves the dsm results, so it is left for a separate pass.

## Switch Sizing

`sw_tgate` and `inv_lv` come from `macros/sw_tgate`, which also holds `sw_tgate_cmfb`, used by `cmfb_sc`. `cmfb_sc2` uses `sw_tgate_cmfb2` from `macros/sw_tgate_cmfb2`. Here the switch is an NMOS 2u/1u and a PMOS 4u/1u in parallel, each flanked by half-width dummies with drain and source shorted onto one terminal and gates driven by the opposite phase. The two clock phases are inverted once by `inv_lv` rather than inside every switch, so the switches see no per-instance skew.

The channel length is 1 um on purpose, not for matching. The off device sits on the floating virtual ground, so its subthreshold leakage is the integrator leak, and the modulator needs that leak-limited gain above 50 dB. Minimum length is far too leaky. Pulling the other way, a longer wider channel injects more charge, so the length is a compromise and the dummies carry the rest.

Thick-oxide devices are not an option here: their threshold near 0.7 V leaves the gate barely conducting at the 0.75 V common mode on a 1.5 V supply.

## Sizing

`scripts/sizing/size_sc_int2.ipynb` derives the sizes from the spec (kT/C, the coefficient, the phases and the OTA numbers of `ota_fcasc2/scripts/sizing/size_ota_fcasc2.py`) and compares them with the schematic. It was written after the schematic and is a model estimate at tt 300 K, not a result. It reproduces C1 and C2 as 2 and 12 units of 32 fF (ratio 1/6, a1 = 1/3), a state swing of 0.98 V peak to peak against the 1.6 V of the OTA, an OTA tau of 22.9 ns with the model capacitors against 30.5 ns allowed, a switch Ron of 4 kohm worst case (under 1 ns of tau) and a finite-gain leak of 2.9e-4 per cycle against the 3.5e-4 simulated. The main disagreements: kT/C asks for 0.1 fF, so the 64 fF of C1 come from the 10 fF rule, leakage and droop. The schematic carries the model unit of 43.98 fF, 1.37 times the 32 fF assumed. The tables give no channel leak for the off `sw_tgate` at any length (1e-12 per cycle at L = 1 um by extrapolation), unlike the length argument under Switch Sizing. The reset recovery of 16 to 17 clocks comes out as 15 in a behavioural model: while the OTA sits at its limit the virtual grounds drift with C1/(C1+C2) = 1/7 of the gap per cycle, and afterwards the state falls by a1 (1 - u) Vref per clock. The OTA slew rate is not the limit.

## Layout

`layout/sc_int2_gen.py` writes `layout/sc_int2.gds` (`make layout`), 68.35 x 85.49 um = 5843 um2. The width is the dsm2_core row width, the height follows the cap rows, the CMFB cap column and the OTA (24.44 um tall). One vertical symmetry axis through the OTA's own axis, and every p net is the mirror image of its n net. Bottom to top:

- Input and DAC switches: one row of ten `sw_tgate` (layout in `macros/sw_tgate`), P side left, N side right as mirror images. The 6.15 um gap at the axis holds the pin risers and the clock transitions. The row ends keep their active end fingers: a guarded `sw_tgate` is 8.80 um wide against 6.04, and the row already fills the half width. Each switch has its mirror twin in the same surroundings.
- Capacitor array: `cap_cmomf` units in four columns P N | P N and seven rows with C1 in the middle row. Every P cap has its PLUS plate (`vvg_n`, `vc1r_p`) on the east face, every N cap on the west face (`vvg_p`, `vc1r_n`), so the right half is the mirror image of the left with p and n swapped. Each half's C1 and C2 share one centroid in x and y. C2P and C2N sit one column pitch apart in x (13.7 um), which moves the gain of the two halves under a gradient and not the ratio within a half (inference). The virtual grounds and C1 right plates face the two gaps between a P and an N column. Each output has one trunk in an outer gap and one in the centre gap, the same for each C1 left plate, so `vo_p` and `vo_n`, `vc1l_p` and `vc1l_n` have the same wiring with no dummy line. A ring of dummies (vdd to vss, they act as decoupling) closes the array: unit-size dummies in the ring rows, a 5.6 um dummy column each side.
- Channel between the array and band B: Metal4 tracks, from the bottom `vo`, `vsw_vbias`, `vcm`, `vsw_cm` (the four that pass under the CMFB cap columns), where the outputs swap sides `vss` and the two output links instead of `vcm` and `vsw_cm`, then `vss`, `vvg_n`, `vc1r_p`, `vc1r_n`, `vvg_p`, `vss`, a stack that is its own mirror image with p and n swapped.
- Band B: an inner block of two rows (TRV and TRC at the outer ends, the clock inverters `inv_lv` at the axis), the CMFB switches (`sw_tgate_cmfb2`, with its end guards) in a column each side, and the CMFB caps in the outer column each side under the OTA output ends: a refresh row at the bottom (refresh unit, 0.93 um lane, refresh unit, 2 um dummy), 3 sense units, a refresh row on top (2 um dummy, refresh unit, lane, refresh unit, flipped so `vsw_cm` is on the north face), and a 2 um dummy column on the outer side past the `vo` lane. The four refresh units of a side face their lanes with `vsw_vbias`. One pSD spans each inner row, as the inverter's own pSD starts 0.22 um inside its edge.
- `ota_fcasc2_top` as a GDS child, unchanged, with a 2.2 um channel under it for `vfb`, `vo`, `vvg`, `vbn` and the vdd and vss lines.

`cmfb_sc2` has no layout cell. Its devices sit in the switch band and the inverter rows, and the LVS deck's `align` step flattens the schematic's `cmfb_sc2` into `sc_int2`.

How a `cap_cmomf` is fed, read back from the PCell and asserted in the generator for every cap cell: unmirrored, PLUS owns the west and south edges and MINUS the east and north edges on every metal, Metal1 and Metal3 carry vertical fingers and Metal2 and Metal4 horizontal ones. At mid height the west face is one plate and the east face the other on Metal3 (full-height edge fingers) and Metal4 (0.20 um edge bars). Each cap is reached by a 0.29 um Metal4 stub at mid height from a Metal3 lane, which keeps every merged comb under the 0.39 um wide-metal width (a wider landing makes the PCell's own 0.21 um gaps a Mn.e error). Caps of one net above each other are also joined on Metal3 across the row gap, where the full-height edge fingers meet. Dummies reach a rail through a south or north face (the ring rows, the refresh rows, the outer column) or a face stub to the column vss lane or to the outer column, and nothing else enters a cap footprint (checked).

Routing: Metal1 and Metal2 inside the leaf cells (pins on Metal2), Metal3 vertical, Metal4 horizontal.
- Clocks: `di_phi1`, `d_phi1_b`, `d_phi2_b`, `di_phi2` cross the array on Metal1 in the centre gap, between two vss Metal1 lines under a vss Metal2 roof, from the band C axis gap to under band B. The trunks over them (`vo_n`, `vc1l_n` | `vc1l_p`, `vo_p`) see the roof. Over band C every clock track, `di_q`, `di_q_b` and `vi` runs the full width, `vc1l` and the DAC node tracks are cut at the axis (p left, n right), so both halves see the same tracks. In band B the clocks rise at +-0.87 um (`di_phi1`, `di_phi2`, through the inverter inputs) and +-2.74 um (the inverted clocks), every track that crosses the GB gaps spans both of them.
- The two pairs that change sides cross once each, as a mirror pair: `vo` over the array (each output's Metal3 passes under the other's Metal4 link once, the links between two vss tracks and away from `vsw_vbias`), `vc1l` under the array.
- `vvg_n` and `vvg_p` rise in the GB gaps on Metal2 under a vss Metal3 strap, so the band B tracks cross them shielded, and enter the switches' m strips on Metal2. They reach the OTA inputs on Metal3 at +-2.07 um, `vi_n` from below the OTA's vd buses and `vi_p` from above them, the `vvg_n` lane carried on dead to the same height. `vc1r` rises beside them on Metal3 and enters TRV and TRC on Metal2.
- `vfb` leaves the sense units on the GB2 lanes, which no band B track crosses, and enters XS6 on Metal2.
- CMFB refresh nodes: the bottom refresh units drop `vsw_cm` from their south faces and `vsw_vbias` from their lane to the channel tracks. The top units join `vsw_cm` on Metal3 over the column and reach the `vsw_cm` lane of the switch column with a stub from the inner unit, and their `vsw_vbias` lane runs on Metal2 over the column (y YB1 + 0.36) to the `vsw_vbias` lane of the switch column. The vdd line under the OTA moved up to YB1 + 1.62 for that link. `vcm` comes in on the left pin, climbs the GB2 inner lanes and crosses band B on one track to TRC, BRC, XS4 and XS10. `vbn` and its dead mirror run over the right column too, so both outputs see it alike.
- Pins: `vi`, `di_phi1`, `di_phi2`, `di_q`, `di_q_b`, `vss` on Metal3 at the bottom edge (x unchanged), `vcm` on Metal3 at the left edge (y 40.35, unchanged), `vo_p` and `vo_n` on Metal4 at the left and right edges at y 69.315 (the OTA output height), `vdd` (x 34.175), `ibias_200n` (x 63.925, Metal4) and `di_ena` (x 25.005, Metal3) at the top edge. A psub ring (vss, unlabelled) surrounds the macro. No supply runs through it.

The generator stops on: what the floorplan assumes of the `cap_cmomf` PCell (two combs per metal, none wide, finger direction, one plate per face at mid height, PLUS on the west face), shorts and spacing between its recorded nets, routing inside a cap footprint, the whole-macro mirror XOR on Activ, GatPoly, Cont, pSD, NWell and Metal1 (zero apart from the OTA's own listed residue), every cap against both schematics (count, w, l, device, metal stack), the leaf cells and the OTA differing from their own GDS, lone vias, labels outside their pin, off-grid vertices, shapes outside the outline and an empty area over 8 % (4.4 %, outline minus Activ, GatPoly, Cont and Metal1 to Metal4 grown by 0.25 um, with the taps' Activ and Cont as empty). Same-net gaps under the metal spacing are filled before the checks. `CHECK_CONTROL=1 make layout` proves that a failing check stops the target. `PLACE_ONLY=1` writes the placement (`render/img/sc_int2_place_white.png`).

Verification, all in `registry.iic.jku.at:5000/iic-osic-tools:next` (bb525d654d8d): `make klayout-drc` 0 at macro level, regular level only the chip-level density rules (AFil.g, M1.j to M4.j, TM1.c). `make magic-drc` 2, both M1.e inside `ota_fcasc2_top` (OTA frame x 2.56 to 61.27 at y 8.13 and 9.87), which the OTA GDS shows on its own too. `make klayout-lvs` matches (deep, tap extraction on). `make magic-lvs` matches uniquely, property errors only `mm_ok`, no value mismatch: Magic extracts no `cap_cmomf`, so the target reruns Netgen with `scripts/netgen_setup.tcl`, which drops them on the schematic side. The deck compares no size of a MoM device, so `layout/mom_check.py` compares w, l and m of every paired `cap_cmomf` and the metal stack of each schematic instance after LVS: 11 device pairs, 0 size and 0 stack mismatches.

PEX flow in this folder: `make magic-pex` (C-coupled, `EXT_MODE=2` is the default here), `make klayout-pex-25d` (kpex 2.5D) and `make pex-mixed` (the Magic view for `sim-xschem PEX=1`). Neither extractor's plate-to-plate value of a MoM comb is trusted, so all of them extract `netlist/pex/pad/sc_int2.gds` (`make pex-gds`), a copy with every `cap_cmomf` flattened to plain metal without its marker and pins, each edge labelled with its net. `scripts/pex_caps.py` then drops the extracted coupling between the two nets of each cap, adds the 82 caps back as `cap_cmomf` devices at the model value and ties each node that only touches capacitors to `vss` by 1 TOhm (two here). What the extraction keeps is the wiring and every plate's capacitance to everything else, the plate to substrate included. The dropped couplings also hold any wiring between the same two nets, the OTA's own `vvg` to `vo` coupling among them. `scripts/pex_gds.py` writes the copy from the cap list of the layout generator (`CAPS_JSON`, rebuilt when the generator or the GDS is newer), and stops if a cap in the layout is not in the list. The extracted `sc_int2_pex` has 385 devices besides the caps and the port order of the symbol.

Full RC: `make magic-pex EXT_MODE=3` (default extresist settings) gives the nets a resistor network, 3381 resistors in this run and a different count every run, most of them on `vss` (2266) and `vdd` (324). Magic books the whole coupling of each of these nets a second time as capacitance to `vss` (magic#557). So `make magic-pex EXT_MODE=3` also extracts the pad layout in mode 2 (`netlist/pex/sc_int2_magic_raw_2.spice`, reused while it is newer than the pad layout), and `../scripts/pex_rc_caps.py` scales every capacitor between two nets of the full-RC netlist to the total of its net pair there (413 pairs, largest deviation afterwards 0.05 aF), and mode 3 differs from mode 2 by its resistors and its junction areas.

Magic's plate-to-plate values, which the flow drops (C only, sim): 62.44 fF for the two C1 units of a side, 409.2 fF for the twelve C2 units (including the OTA's coupling between the same nets), 103.4 / 103.5 fF for the three sense units of each side, 42.3 / 42.3 fF for the four refresh units of each side. The model says 43.98 and 15.85 fF per unit, the EM-scaled estimate 32.0 and 10.66 fF.

Extracted capacitance per net, Magic mode 3 with the pair correction, wiring and plates to everything but the other plate of their own caps (sim, one extraction):

| net | total | of it to vss and substrate |
| --- | --- | --- |
| `vo_p` / `vo_n` | 85.1 / 85.2 fF | 31.8 / 31.8 fF |
| `vvg_n` / `vvg_p` | 61.4 / 62.0 fF | 32.3 / 32.0 fF |
| `vc1r_p` / `vc1r_n` | 35.0 / 35.2 fF | 4.5 / 4.4 fF |
| `vc1l_p` / `vc1l_n` | 30.3 / 30.5 fF | 4.8 / 4.8 fF |
| `vfb` | 45.6 fF | 19.3 fF |

2.5 fF between the two virtual grounds, 2.1 fF between the outputs. Per neighbour net, with the p / n neighbours compared against their mirror partner (`vo_p` to `vc1l_p` against `vo_n` to `vc1l_n`), the pairs differ by at most: `vo` 0.18 fF (to an OTA Metal2 line under the `vo_p` pin track that Magic extracts with no device), `vc1r` 0.27 fF (to the opposite virtual ground), `vvg` 0.37 fF to `vss` and 0.53 fF to the OTA's `vcn`, both inside the OTA (its own `vi_n` / `vi_p` asymmetry). `vc1l`, `vh` and `vl` differ by up to 0.50 fF to `di_phi1` and `di_phi2` taken one at a time, and by under 0.03 fF to the two summed: the p side's DAC switches close on phase 2 and its input switch on phase 1, the n side's the other way round, and each switch cell couples its own pins to its own gates (0.3 to 0.4 fF per pin and gate in a standalone `sw_tgate` extraction). The clocks reach `vo` with 0.39 / 0.40 fF (`di_phi1`) and 0.02 / 0.02 fF (`di_phi2`). The refresh rows put each output on its own `vsw_cm` with 2.18 fF and on `vsw_vbias` with 6.14 fF, and `vfb` on `vsw_vbias` with 6.91 fF (the edges of the sense units facing the refresh rows), equal on both sides. `vsw_vbias` is shorted to `vfb` on phase 1.

High-impedance nets: `vcm` sees 5.8 fF of phases and phase complements, `vfb` 2.1 fF, `ibias_200n` none. Most of the `vcm` share is the switch cells whose m pin it is (TRC, BRC on phase 1, XS4, XS10 on phase 2, 0.4 fF per pin and gate in the standalone cell), its track crosses the `di_phi1` and `d_phi1_b` lanes once each.

Known limit of the mode 2 view: `ext2spice` with hierarchy off books the Metal1 area and perimeter of a whole net as the source or drain junction of one MOSFET on it. On the pad layout Metal1 includes the cap combs, so mode 2 carries 1766 um2 of junction where mode 3 has 175 um2 (mode 3 writes each terminal's own diffusion). On the earlier layout this defect, not the extracted plate and wiring capacitance, was most of the gap between the mode 2 view and the schematic. The flow does not correct it, because mode 2 output stays as Magic writes it. Mode 3 is the view to use for the leak.

Benches on this layout (sim, tt 27 C 1.5 V, one run each, `:next` bb525d654d8d on x86, sanity checks, 0 measurements missing), schematic against the Magic mode 3 view, with the 4-unit refresh caps: step bench -251.269 / -250.441 mV at 4 cycles, -249.664 / -249.122 mV at 22 cycles, output common mode 0.7428 / 0.7412 V. Leak bench 2.913e-4 / 2.730e-4 per cycle, 1.45 / 1.34 times the gain prediction, OTA gain in place 58.35 / 58.25 dB, integrator gain 70.7 / 71.3 dB. With 1-unit refresh caps the same benches gave a step of -251.325 / -250.489 mV, a common mode of 0.7235 / 0.7187 V and a leak of 2.676e-4 / 2.469e-4.

Schematic step bench over corners (sim, one run each, MOS corner cards only, clock, data and enable levels at the supply):

| corner | refresh | 4 cycles after | 22 cycles after | output common mode |
| --- | --- | --- | --- | --- |
| tt, 27 C, 1.5 V | 4 units | -251.269 mV | -249.664 mV | 0.7428 V |
| ss, -40 C, 1.45 V | 4 units / 1 unit | -242.486 / -242.546 mV | -241.391 / -241.754 mV | 0.7213 / 0.7116 V |
| ff, 125 C, 1.55 V | 4 units / 1 unit | -257.552 / -257.560 mV | -253.637 / -254.024 mV | 0.7470 / 0.6630 V |
| ff, 27 C, 1.5 V | 4 units / 1 unit | -251.288 / -251.422 mV | -249.426 / -250.273 mV | 0.7302 / 0.6695 V |

The 4 units move the step response by at most 0.13 mV at 4 cycles. The output common mode at ff 27 C comes from 80.5 mV under vcm to 19.8 mV under it. The tables in [Verification Status](#verification-status) are from the earlier layout and switch. A first routing that crossed `vsw_vbias` over the axis next to the clock bends under band B (2.3 fF of phases on it) put the PEX output common mode at 0.6634 V, 60 mV under the schematic, so the CMFB refresh node stays away from the clocks.

Open points of the layout: the vss share of the two virtual grounds differs by 0.37 fF, inside the OTA. Current density was checked by hand only (OTA about 7.3 uA, far below the Metal1 and via limits). The parent `dsm2_core` still places the 76.575 um tall version.

## Verification Status

Every number below is from one run at tt, 27 C, 1.5 V, the stock `mos_tt` cards. The two final layout columns are the layout of [Layout](#layout) with the 4-unit CMFB refresh caps, the other columns earlier layouts and schematics. They are sanity checks of the bench and the swap, not a characterisation of the integrator, and there was no Monte Carlo or corner run.

The step and leak benches were rerun with the `cap_cmomf` capacitors on the schematic and on the Magic PEX view, all in `registry.iic.jku.at:5000/iic-osic-tools:next` (bb525d654d8d). The schematic carries the model value of the caps (43.98 fF units), the PEX view the same caps plus the extracted wiring and plate capacitance. The `cap_cmomi` columns are the committed earlier numbers: their unit was 31.78 fF in the hpretl 2026.08 image, where most of them were taken, and 42.98 fF in `:next`, because that model changed between the images (`cap_cmomf` is the same in both). On 2026-10-18 both benches ran again on the schematic, Magic mode 2 and Magic mode 3 (full RC, see [Layout](#layout)), after aa0f519 had changed the OTA schematic, in `:next` on an aarch64 host (`0ad78d950901`, ngspice-47 of 2026-10-15), with the extraction on x86 (`bb525d654d8d`). Build check: the leak bench netlist that gave 2.723196e-4 on x86 gives 2.723217e-4 there. The current schematic gives 2.718e-4. The tables carry these runs. The `pss` deck, the `pnoise_idsw` deck, the validation ladder, the transient noise decks, the corner table and `doc/noise-budget.md` were not rerun with `cap_cmomf`.

### Step bench

`make sim-xschem TB=sc_int2_tb_step` runs the impulse response check of Schreier section 7.5 with the real transmission gates. Two integrators run side by side with DAC sequences differing in one cycle, and half their output difference is the response to a unit impulse. The baseline alternates every cycle, because with `a1 = 1/3` a constant sequence ramps the output by 0.25 V per cycle and saturates the OTA in four. The real switches drift both integrators by about 5 mV per cycle, which put vod near 1 V by the impulse and made the response droop 1.37e-3 per cycle, four times the leak, and move by 5 mV with the solver tolerance. The bench therefore has the PI servo of the leak bench on the mean state of the two integrators, which cancels in their difference.

| | `cap_cmomf`, schematic (sim) | `cap_cmomf`, Magic mode 2 (sim) | `cap_cmomf`, Magic mode 3 (sim) | `cap_cmomi`, schematic, 2026.08 (sim) | expected | final layout, schematic (sim) | final layout, Magic mode 3 (sim) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| before the impulse | 1.79 nV | 37.3 nV | 26.4 nV | -0.47 uV | 0 | 4.33 nV | -86.4 nV |
| 4 cycles after | -251.327 mV | -249.442 mV | -250.178 mV | -251.557 mV | -249.6 mV | -251.269 mV | -250.441 mV |
| 22 cycles after | -250.029 mV | -247.166 mV | -248.646 mV | -250.083 mV | -248.0 mV | -249.664 mV | -249.122 mV |
| droop per cycle | 2.87e-4 | 5.07e-4 | 3.40e-4 | | | 3.55e-4 | 2.93e-4 |
| output common mode, cm_end | 0.7350 V | 0.7423 V | 0.7391 V | 0.7325 V | | 0.7428 V | 0.7412 V |

On the schematic the droop is 2.87e-4 per cycle, within 6 % of the leak bench, and the first reading is 0.7 % high, where the gain error predicts 0.15 % low. The same excess showed with every capacitor model so far (`cap_cmomi` +0.6 %, ideal caps +0.33 %, `sc_int` +0.94 %), and its cause is open. The mode 2 view reads 0.75 % lower than the schematic at 4 cycles, the mode 3 view 0.46 %. Mode 3 against mode 2 is +0.30 % at 4 cycles, a droop of 3.40e-4 against 5.07e-4 per cycle and 3.2 mV less output common mode. The mode 2 view with the junction areas of mode 3 gives -250.268 / -248.675 mV and 0.7392 V, so the junction defect of mode 2 (see [Layout](#layout)) accounts for all of it, the resistors for 0.04 % at 4 cycles. Mode 3 without the pair scaling of `pex_caps.py` reads -241.882 / -238.099 mV and 0.7447 V, 3.8 % below the schematic, from the 565 fF of double-counted capacitance on each output. With the C1 row not flipped in y, the C1 right plate faced the output plate of the next C2 row (8.6 fF, Magic), and the PEX view read 2.5 % low (-245.044 / -242.888 mV, one run). The layout therefore flips that row.

### Leak bench

`make sim-xschem TB=sc_int2_tb_leak` (29 min with the 64 `cap_cmomf` devices, 81 min with 36 `cap_cmomi`, 23 min with ideal capacitors) preloads the two integrators to +0.1 V and -0.1 V after the CMFB has settled, holds both at `vi = vcm` with a DAC that alternates every cycle, and fits the decay of half their output difference over 200 cycles. Drift, injection and offset common to both cancel in it.

| | `cap_cmomf`, schematic (sim) | `cap_cmomf`, Magic mode 2 (sim) | `cap_cmomf`, Magic mode 3 (sim) | `cap_cmomi`, schematic (sim) | ideal caps (sim) | `sc_int` (sim) | final layout, schematic (sim) | final layout, Magic mode 3 (sim) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OTA gain in place | 58.29 dB | 57.68 dB | 58.28 dB | 58.27 dB | 58.75 dB | | 58.35 dB | 58.25 dB |
| leak per cycle, fitted | 2.72e-4 | 5.03e-4 | 3.41e-4 | 3.50e-4 | 2.10e-4 | 4.70e-5 | 2.91e-4 | 2.73e-4 |
| leak predicted from the gain, `(C1/C2)/A` | 2.03e-4 | 2.18e-4 | 2.03e-4 | 2.03e-4 | 1.93e-4 | | 2.01e-4 | 2.04e-4 |
| fitted over predicted | 1.34 | 2.31 | 1.68 | 1.72 | 1.09 | | 1.45 | 1.34 |
| integrator gain `1/leak` | 71.3 dB | 66.0 dB | 69.3 dB | 69.1 dB | 73.5 dB | | 70.7 dB | 71.3 dB |

The gain in place tracks the 58.8 dB the OTA bench reports for `ota_fcasc2`. With the ideal capacitors the leak followed from it within 9 %. With `cap_cmomi` it was 1.7 times higher, and scratch runs with local copies of that model assigned the rise to its substrate shunt on the C2 units (50 fF more load or 50 fF more on the virtual ground slows the OTA by 26 % in tau, and with the DAC stepping every cycle the settling residue at the end of the transfer reads as leak, inference). `cap_cmomf` has no shunt, and on the schematic the leak sits 1.34 times above the gain prediction, with C2 and the CMFB caps 1.38 times larger than with `cap_cmomi` at 2026.08 values. Its 1 pS anchors across the plates are worth at most 3e-5 per cycle (hand estimate above). The mode 2 view leaks 1.85 times as much as the schematic, 2.31 times its own gain prediction, with the OTA gain in place 0.6 dB down. The mode 3 view leaks 1.25 times the schematic at the schematic's OTA gain. The difference between the two views is the junction defect of mode 2 ([Layout](#layout)), which puts the Metal1 area and perimeter of each virtual ground and output, cap combs included, on one junction: the mode 2 view with the junction areas of mode 3 leaks 3.47e-4 at 58.29 dB, within 2 % of mode 3. An earlier version of this README read the mode 2 excess as slower settling from the plate capacitance (inference), which the run does not support. What is left between mode 3 and the schematic, 1.25 times, comes with the 81 to 84 fF on each output and 60 fF on each virtual ground of extracted wiring and plate capacitance (table in [Layout](#layout)), which the `cap_cmomi` shunt runs showed reads as leak through slower settling (inference, not separated out on this view). Mode 3 without the pair scaling of `pex_caps.py` leaks 8.75e-4 at an OTA gain of 48.5 dB, the double-counted 565 fF per output. The integrator gain stays above the 50 dB the modulator needs, 71.3 dB on the schematic, 69.3 dB on mode 3 and 66.0 dB on mode 2.

### Periodic steady state

Not rerun with `cap_cmomf`, the numbers below are with `cap_cmomi` or ideal capacitors.

`make sim-vacask DECKS=pss` in the IIC-OSIC-TOOLS image `next` (VACASK 87e4a83) takes 745 s for the PSS and the two check transients (540 s with ideal capacitors). The servo holds `v(vi) - v(vcm)` at -10.03 mV, the output common mode sits at 0.797 V and the held `vod` at -0.1231 and +0.1230 V. A transient started from the PSS state lands 83 uV (reltol 1e-3) and 100 uV (reltol 1e-5) from the PSS in the first cycle and then drifts by +53 and -26 uV per cycle over 20 cycles. With ideal capacitors: -10.65 mV, 0.804 V, -0.1230 / +0.1232 V, first cycle 18 and 17 uV, drift -21 and -125 uV per cycle. For `sc_int` the same deck gave -10.11 mV, 0.774 V and -0.1223 / +0.1219 V. One run, pss only. These numbers predate 7c33e1e and the dummy caps. The current schematic gives -10.25 mV, 0.784 V and +-0.123 V (1 run).

### Run counts

| bench | runs | measurements that did not come back |
| --- | --- | --- |
| `sc_int2_tb_step` | `cap_cmomf`, 2026-10-18: 1 per view (schematic, Magic mode 2, Magic mode 3), plus 1 each on mode 3 with the caps on the nearest node, mode 3 without the pair scaling, mode 3 with an earlier correction rule and mode 2 with the junction areas of mode 3. Before: 1 per view (schematic, Magic PEX), 1 on the Magic view of the unflipped C1 row, and 1 per view with `cap_cmomi` (schematic, Magic, KLayout) | 0 |
| `sc_int2_tb_leak` | `cap_cmomf`, 2026-10-18: the same seven views as the step bench, 1 each, plus the build check. Before: 1 per view (schematic, Magic PEX) and 1 per view with `cap_cmomi` | 0 |
| `sc_int2_tb_periodic`, pss | 1 per view with `cap_cmomi` (schematic, Magic, KLayout), not rerun | 0 |
| pac, pnoise, sampled | 0 | not run |
| `sc_int2_tb_periodic`, pnoise_idsw | 1 from the launcher with the `cap_cmomi` capacitors (the ladder below and the scratch runs used the ideal ones) | 0 |
| `sc_int2_tb_periodic`, pnoise_idsw with `bias=gm` | 1 (scratch) | 0 |
| `sc_int2_tb_periodic`, tn_vcm and tn_step | 6 seeds of 16384 cycles each, through the same netlist.py, not from the launcher | 0 |
| `sc_int2_tb_periodic`, pnoise_idsw over operating points | 45 (all corners, temperatures, supplies), 9 of them twice | 0 |
| `sc_int2_tb_periodic`, pnoise_idsw_step | 1 per truncharm 150, 200, 225 | 0, truncharm 250 and 300 crash |
| `sc_int2_tb_periodic`, pnoise_idsw_r40, sampled_idsw, `ota=pex`, half-size capacitors (the former `ci=32f cf=192f`, ideal), 150 nA | 1 each, all with ideal capacitors | 0 |

## pac and pnoise

`pac`, `pnoise` and the sampled deck run in the decks but do not converge on `sc_int` or `sc_int2`. On `sc_int2` with the PDK switches (2026-10-12, aarch64, VACASK fb8cc20, one run per point) pac at 1 Hz reaches 0.065, 0.085 and 0.25 of the transient gain at truncharm 50, 75 and 90 with the DAC alternating, and 0.63, 0.49 and 0.53 with the DAC at vcm, where pnoise reads 52.0, 52.7 and 51.6 uVrms (stable, but on an unconverged pac, against 27.54 with ideal switches). From truncharm 100 up every point stops (segfault, KLU analysis failure, internal error), see `doc/vacask-issues.md` item 3. The cut Fourier series of an off transmission gate keeps 3 to 5 % of its on-conductance at truncharm 50 and still 0.05 to 0.4 % at 400. Where that lands on the OTA inputs it leaks the integrator, and where it lands on the OTA outputs or on OTA devices that go into triode while slewing, it collapses the OTA gain. The `sc_int` runs at truncharm 50, 75 and 100 disagreed by up to a factor of 5 in gain and a factor of 10 in noise, and converging would take truncharm 400 to 1000, beyond 100 GB of memory. Gain and leak come from the step and leak benches. Noise comes from `pnoise` with ideal noisy switches, see [Noise with Ideal Noisy Switches](#noise-with-ideal-noisy-switches). `post.py` reads the noise budget of `macros/dsm/scripts/noise_budget.py --ota ota_fcasc2` for the `pnoise` and `sampled` decks.

## Periodic Benches in VACASK

`testbenches/xschem/sc_int2_tb_periodic.sch` holds `sc_int2` with its clocks, DAC, bias and supply, a servo on the input and an ideal sampler on the output. Its launchers, one per deck and one to replot, run the decks in `testbenches/vacask/` on it, and so does the command line, both through `testbenches/vacask/run.sh`:

```sh
sak-pdk ihp-sg13cmos5l
make sim-vacask                                   # pss only, or DECKS="pss pac pnoise sampled", or testbenches/vacask/run.sh <decks>
```

It needs a VACASK with `pac` and `pnoise` (IIC-OSIC-TOOLS image `next`, VACASK 7eeb9d2 or later) and stops with that message on the 2026.09 image. Each deck runs in `testbenches/vacask/runs/<deck>/` with the netlist, the transcript, the raw files, `result.json` and plots, and `runs/summary.md` collects them. `run.sh --plot` redraws from existing runs.

| deck | what it does |
|---|---|
| `sc_int2_tb_pss.sim` | periodic steady state over two clock cycles, then two transients started from it, at reltol 1e-3 and 1e-5, as the check |
| `sc_int2_tb_pac.sim` | transfer from `vi` to `vod` by `pac`, truncharm 50, 75 and 100, fitted to `G z^-1 / (1 - p z^-1)` for the gain error and the leak `1 - p` |
| `sc_int2_tb_pnoise.sim` | output noise by `pnoise`, referred to `vi` through the power gain from `VIN`, split into switches, OTA, CMFB and clock inverters, truncharm 50, 75 and 100 |
| `sc_int2_tb_sampled.sim` | the same on the held output of the sampler, which tracks `vod` at the end of phase 2, as the quantizer sees it |
| `sc_int2_tb_pnoise_idsw.sim` | `pnoise` with ideal noisy switches, see [Noise with Ideal Noisy Switches](#noise-with-ideal-noisy-switches) |
| `sc_int2_tb_pnoise_idsw_r40.sim` | the same with Ron x 40, the reference of the transient-noise decks |
| `sc_int2_tb_pnoise_idsw_step.sim` | `pnoise_idsw` at the two-clock period with the DAC alternating to the rails, truncharm 150, 5.4 GB and about 1 h |
| `sc_int2_tb_sampled_idsw.sim` | `pnoise` on the held output of the ideal track-and-hold, the noise per sample the next stage sees |
| `sc_int2_tb_tn_vcm.sim`, `sc_int2_tb_tn_step.sim` | transient noise with ideal noisy switches, DAC at vcm or stepping, see [Transient Noise with DAC Steps](#transient-noise-with-dac-steps) |

What the bench does differently from the transient benches, and why:

- **Two clock cycles per period.** The DAC alternates every cycle, so `vi = vcm` gives a bounded, periodic state, the trick `sc_int2_tb_leak` uses.
- **A servo holds the state.** The real switches drift the integrator by several mV per cycle, the servo cancels that with about -10 mV at `vi`. It is a PI loop with a third-order low pass, built from controlled sources and ideal capacitors so it adds no noise. It also pulls the slowest mode to 0.993 per period (a run with 1 ns edges), which shooting needs: without it the integrator mode sat at 1.0007, within the transient's numerical error of 1, and the Newton steps ended in NaN. The decks read the transfer as `v(vod) / v(vi)` and the noise as `onoise / gain`, so the servo drops out of both.
- **Clock edges of 40 ns and 200 ns between the phases** (`tedge`, `tgap` in each deck), against 1 ns and 10 ns in the transient benches. `pac` and `pnoise` truncate the Fourier series of every Jacobian at `truncharm`, and a switch is only off in that series once enough harmonics cancel its on conductance. With 1 ns edges the integrator gain at 1 Hz came out 0.023 at truncharm 10 and 3.3 at truncharm 40, against about 7000 for the real circuit, and truncharm 100 took more than 1.5 h for three points. With 40 ns edges it was 0.2 at 25 and 77 at 50. The inverters inside sc_int2 and cmfb_sc rebuild the inverted clocks with 4 ns edges, so `tedge` slows only the NMOS gates.
- **The period starts in the middle of the gap after phase 2**, where no source moves. With an edge on the period boundary the branch currents of the sources never met the shooting tolerance.
- **`abstol=1e-8`.** The sources' branch currents carry about 1e-10 A of solver noise at the period boundary, which the default 1e-12 never lets shooting converge on.

The PSP103 cards are copied next to each deck with `swign=0` (`MODEL=noign`, the default). With the cards as shipped (`MODEL=stock`) `pnoise` gave 2.9 MVrms input referred at truncharm 75, all of it the induced gate noise `igig` of the switch devices, whose source PSP103 scales with 1/mig and mig falls toward 1e-40 when a switch turns off. `MODEL=pspfix` loads the patched model of `macros/dsm/testbenches/vacask/trannoise_report`. At truncharm 25 the three changed the `pac` gain by at most 6 %, so the induced-gate node is not what limits the truncation.

## Noise with Ideal Noisy Switches

`testbenches/vacask/sc_int2_tb_pnoise_idsw.sim` gets the integrator's input-referred noise from `pnoise` with the real `ota_fcasc2_top`, the real `cmfb_sc` topology, the ideal 200 nA bias and ideal switches that carry the thermal noise of their own conductance. It runs from the launcher "PNOISE ideal noisy switches" on `sc_int2_tb_periodic.sch` or as `make sim-vacask DECKS=pnoise_idsw` (21 to 45 min depending on the host load, 2.2 GB peak).

### Method

- **Why ideal switches.** `pac` and `pnoise` cut the Fourier series of every Jacobian at `truncharm`, and the cut series of a PDK transmission gate never turns off (section above). `sw_noisy.va` is a conductance stepping from 1e-12 S to 1/Ron along `tanh((v(g) - 0.75 V) / 0.1 V)`, with `white_noise(4kT g)` of the actual conductance. On 200 ns clock edges the step takes about 13 ns, whose Fourier series is gone by truncharm 100 at a one-clock period, and the off conductance floor is 6e-7 of the on value.
- **Ron** is the PDK switch's on-resistance at 0.75 V with the gate at 1.5 V (VACASK op, tt, 27 C): 2562 Ohm for `sw_tgate`, 17170 Ohm for `sw_tgate_cmfb`. Over 0 to 1.5 V they span 1.3k to 4.0k and 10.5k to 19.8k.
- **The variant is made in the netlist step.** A deck line `// netlist variant: idsw ...` makes `netlist.py` swap the bodies of `sw_tgate` and `sw_tgate_cmfb` for one `sw_noisy` each, drop the four clock inverters (they drove only the PMOS halves), and retime the DAC and sampler sources. The drawn schematics are untouched. Options: `opamp=ideal` (noiseless VCVS, gain 1e4), `cmfb=ideal` (the two sensing caps and a noiseless pull of `vfb` toward `vbn + vocm - vcm`), `vref` (DAC levels around vcm), `dac=static`, `rscale`, `swnoise=0` (switches without noise), `bias=gm` (the `bias_gm` schematic with its `bias_trim` at trim code 4 instead of the ideal 200 nA, netlisted from `macros/bias_gm`, from the command line only), `ota=pex` (the Magic PEX of `ota_fcasc2` from its `netlist/pex`, translated to VACASK), `sw=pdk` (keeps the PDK transmission gates, for transient noise with the other options). `CORNER`, `TEMP`, `VDD` and `IBIAS` in the environment of `run.sh` set the operating point.
- **DAC levels at vcm, period one clock.** With the DAC alternating the period is two clocks, and even the ideal opamp did not converge there by truncharm 150 (ladder below). With `vref=0 dac=static` the DAC switches still connect one DAC path per phase as in operation, but no DAC charge moves, the OTA does not slew, and the PSS is quiet within 0.3 mV. What that leaves out: the OTA's bias modulation by the DAC steps (its flicker sources are taken at the quiescent point) and any noise that depends on the signal.

### Validation ladder

Input referred, 1 Hz to 1 kHz. One run per entry, tt, 27 C, `noign` cards. Sanity checks of the bench, not characterisation.

| rung | variant | period, DAC | truncharm | in band | split |
|---|---|---|---|---|---|
| a | ideal opamp, ideal CMFB | 2 clocks, alternating to the rails | 50 / 100 / 150 | 10.6 / 12.2 / 15.7 uVrms | switches only, 336 / 386 / 498 nV/sqrt(Hz) against 355.6 |
| a | ideal opamp, ideal CMFB | 2 clocks, alternating to the rails, DAC edges 200 ns | 50 / 100 / 150 | 13.10 / 12.69 / not integrated (2 points) | switches only, 414.6 / 401.6 / 361.3 nV/sqrt(Hz) against 355.6 |
| a | ideal opamp, ideal CMFB | 1 clock, vcm | 25 / 50 / 100 / 150 | 10.50 / 14.41 / 11.25 / 11.25 uVrms | 356.0 nV/sqrt(Hz) at 100 and 150 against 355.6 |
| b | real OTA, ideal CMFB | 1 clock, vcm | 50 / 100 | 30.43 / 28.64 uVrms | OTA 27.05 / 26.55, switches 13.79 / 10.61 |
| c | real OTA, `cmfb_sc` with ideal switches, ideal capacitors | 1 clock, vcm | 50 / 100 / 150 | 30.43 / 28.64 / 28.64 uVrms | OTA 26.55, switches 10.61, CMFB 0.004 at 100 and 150 |

Rung a converges at the one-clock period, to 0.1 % of the analytic floor at truncharm 100 and 150. At two clocks it drifts away with 10 ns DAC edges, and with DAC edges as slow as the clock edges (`tdedge=200n`, centred on the period boundary) it approaches the floor from above, 1.6 % off at 150. The real OTA at two clocks converges by truncharm 200, see [Transient Noise with DAC Steps](#transient-noise-with-dac-steps). Rung c agrees to four digits between truncharm 100 and 150 in the total and in every group, so the deck runs 50 and 100. b and c agree to 0.01 %, the CMFB adds nothing visible. The PSS of c is quiet within 0.3 mV, and with the PSP103 cards as shipped (`MODEL=stock`) rung c gives 30.42 against 30.43 uVrms at truncharm 50: once the switches are ideal, the induced gate noise that read megavolts before is 3.2 uVrms of the OTA's own devices, moved over from their channel thermal noise, and the total does not change.

An ideal VCVS on `vfb` as the ideal CMFB made the output common mode ring by 0.25 V in phase 1, because a source on `vfb` takes the sensing caps out of the common-mode loop. The ideal CMFB in `netlist.py` keeps the caps and pulls `vfb` slowly instead. The noise came out the same either way.

The analytic switch noise of this shared-capacitor structure is kT/C1 per sample at the input, not 2kT/C1: each capacitor takes kT/C1 per phase, but both capacitors carry the input, so the signal gain is 2 C1/C2 against C1/C2 per capacitor. Over the band that is sqrt(kT / (C1 OSR)) = 11.24 uVrms, a 355.6 nV/sqrt(Hz) white floor.

The model alone, in an RC sampler with a noiseless track-and-hold, gives 0.37, 0.82, 0.9998 and 0.9999 of kT/C at truncharm 10, 25, 50 and 100 (one-clock period).

Cross-check by VACASK transient noise (SDE, 3 seeds, 1994 cycles each, ideal opamp, Ron x 40 so that 200 MHz of noise bandwidth covers the RC): the per-cycle increment of the held output gives 1.019, 1.017 and 1.062 of a1^2 kT/C1, each +-0.032, against 1.002 from `pnoise`.

### Result

`runs/pnoise_idsw` from the launcher, VACASK 87e4a83, truncharm 100, 1 Hz to 1 kHz input referred (sim):

| contribution, uVrms | `cap_cmomi` (not rerun with `cap_cmomf`) | ideal caps |
|---|---|---|
| OTA flicker | 25.66 | 25.67 |
| switches, thermal | 9.06 | 10.61 |
| OTA channel thermal | 6.16 | 6.63 |
| OTA gate current shot | 0.26 | 0.35 |
| CMFB switches | 0.004 | 0.004 |
| total | 28.00 | 28.64 |

With `MPR` of `ota_fcasc2` at 0.5/10 (commit 7c33e1e) the total is 27.54 uVrms, OTA 25.96 and switches 9.06, one run each on two hosts (VACASK 87e4a83 x86 and fb8cc20 aarch64, identical to five digits).

At truncharm 50 the total is 29.06 uVrms (the ideal-capacitor run gave 30.43). The switch term fell by 15 percent, the OTA thermal term by 7 percent and the flicker did not move. Reading (inference, not separated out): the shunt on the left plates of C1 adds 8.4 fF to the node the sampling switches charge, which takes charge noise kT C1^2 / (C1 + shunt) and explains about half of it, and the shunt on the OTA outputs slows the OTA, which lowers its thermal term. The total moved by 2.2 percent, 0.64 uVrms.

The OTA flicker splits evenly over the PMOS loads `XMP4`/`XMP5`, the input pair `XMP1`/`XMP2` and the NMOS sinks `XMN1`/`XMN2`, 10.2 to 10.7 uVrms per device. The total is 28.0 uVrms against the 288.7 uVrms budget, 20.3 dB below it, with the DAC levels at vcm.

The switch term is 10.61 uVrms with the real OTA against 11.25 with the ideal opamp. Reading (inference): during phase 2 the virtual ground is not a short at the switch noise bandwidth, so the charge noise of the transfer phase sees C1 in series with the capacitance on the virtual ground, about 0.8 of kT/C1 instead of 1.

Per sample (model from the sim): the OTA thermal term is 150 uV per sample at the input, so 300 uV differential on the virtual ground when phase 2 opens. The OTA's open-loop white floor of 96.6 nV/sqrt(Hz) over a noise bandwidth of pi/2 times 9.8 MHz (tau 16.2 ns) gives 379 uV, the right size. `sc_int2_tb_sampled_idsw.sim` gives 340 uVrms per sample on the held output, see [Noise over Operating Points, at the Quantizer and in the Budget](#noise-over-operating-points-at-the-quantizer-and-in-the-budget).

### Bias from bias_gm

`bias=gm` in the variant line replaces the noiseless 200 nA source by the `bias_gm` schematic, enabled with the OTA. Rung c with it, truncharm 50 and 100, one run (sim): 30.46 and 28.67 uVrms in band against 30.43 and 28.64 with the ideal source. The whole `bias_gm` contributes 1.07 nVrms, 1.4e-9 of the total power, flat at 0.034 nV/sqrt(Hz) from 1 Hz to 1 kHz, which reads as the numerical floor of the cancellation rather than its flicker. It reaches the OTA only as common mode: the tail, the folding sinks through the CMFB's `vbn` reference and the cascode gates are shared by both halves. It delivers 191.3 nA in VACASK (the README of `bias_gm` gives 191.4 nA in ngspice), which moves the OTA term by 0.03 uVrms. 4.4 GB peak, 53 min at truncharm 100.

### Which referral holds

Charge balance over one cycle: a differential OTA input noise vn reaches `vod` with C1/C2, the input with 2 C1/C2, so vn refers to the input with 1/2. The switch noise refers as kT/C1 per sample, not 2kT/C1.

| how | OTA term in band |
|---|---|
| half the open-loop input noise `vn_d` of `ota_fcasc2_top_tb_noise` | 51.26 / 2 = 25.63 uVrms |
| pnoise, OTA flicker and thermal | 26.55 uVrms (25.67 flicker) |

`macros/dsm/scripts/noise_budget.py` uses this referral (`--ota ota_fcasc2`): 29.21 uVrms total (kT/C 11.24, OTA 25.63, folded thermal 8.38) against 28.64 uVrms from pnoise. Its earlier maps, the closed-loop bench number 1:1 (923 uVrms with the bench's noisy feedback resistors, 416.5 without) or divided by the noise gain (C1+C2+Cgg)/C1, were 16x and 2x too high on the OTA term.

### Limits

- Ron is one value per switch size, taken at 0.75 V. Its signal dependence and the switches' nonlinearity are absent, so is charge injection and clock feedthrough.
- DAC levels at vcm: no DAC step, no slewing, flicker of the OTA at its quiescent bias. The DAC steps are in the next section.
- No mismatch. Corners and the OTA PEX view are in [Noise over Operating Points, at the Quantizer and in the Budget](#noise-over-operating-points-at-the-quantizer-and-in-the-budget) and `doc/noise-budget.md`.
- The OTA term is flicker, so its value carries the PSP103 flicker parameters as they are.

## Transient Noise with DAC Steps

`pnoise` covers the DAC at vcm only. With the DAC stepping every cycle the OTA slews, and the in-band noise comes from VACASK transient noise on the same ideal-switch variant instead: `sc_int2_tb_tn_step.sim`, with `sc_int2_tb_tn_vcm.sim` as the check against `pnoise`. Both run from the launchers "TRANNOISE ..." on `sc_int2_tb_periodic.sch` or as `make sim-vacask DECKS=tn_step` (about 5.5 h and 90 MB per deck).

### Method

- **Same bench, same variant.** Real `ota_fcasc2_top`, `cmfb_sc` with ideal switches, ideal 200 nA, the clock and DAC edges of `pnoise_idsw` (200 ns), DAC alternating to the rails in `tn_step` as in `sc_int2_tb_step`. Ron x 40 (`rscale=40`) puts the switch RC near 20 ns, so 200 MHz of noise bandwidth covers it. kT/C does not depend on Ron, the OTA thermal term does a little: `pnoise` at Ron x 40 gives 28.39 uVrms (OTA thermal 5.25) against 28.64 (6.63) at Ron x 1, so they compare with `sc_int2_tb_pnoise_idsw_r40.sim` (Ron x 40, 28.39 uVrms, one run). `post.py` takes `runs/pnoise_idsw_r40` as the reference when it exists and `runs/pnoise_idsw` (Ron x 1, white floor 7 % higher in power) otherwise.
- **Noisy minus noiseless.** A PSS solve, then a noiseless transient `tn0` and two noisy ones (`tn1`, `tn2`, seeds 1 and 2), all started from the PSS state, 16384 cycles each. The noiseless run takes the same 1.25 ns maximum step. A noiseless run at half that step gives the same held output to 0.05 uV, and a noisy run at `noisescale=0.1` scaled back lands on the same white floor within the scatter of its 2048 cycles, so the difference is noise and not numerical error.
- **Input referred per cycle.** `post.py` samples `vod` at 0.45 ts of each cycle (in phase 1, where it holds) and forms `e[n] = (vod[n+1] - vod[n]) / a1 - (vi - vcm)`, which takes the servo out. An offset and the alternating DAC pattern are regressed out. Welch PSD (Hann, 4096 per segment), averaged over the seeds, compared with `pnoise` over the same bins. The sequences are kept in `tn_e.npz`.
- **sde settings.** `noisemode="sde"`, `tran_noiselte=1e6`, `noign` cards, `noisefmin=10` so that the flicker Lorentzians reach below the band, `oversample=2`. With an ideal opamp the same deck gives 1.16 (oversample 2) and 1.05 (oversample 6) of kT/C1 per sample, 2048 cycles each, +-0.03.
- **What the sequence also holds.** The OTA's instantaneous output noise at the sampling instant (about 0.58 mV rms, both decks) does not integrate, so it enters `e[n]` differenced and rises as f^2 above about 8 kHz. That band does not compare with `pnoise`, the band below does.

### Result

Input referred power over `pnoise` at Ron x 40, 6 seeds of 16363 cycles per deck (seeds 1 and 2 on VACASK 87e4a83, 3 to 6 on fb8cc20), mean and its standard error from the seed spread (sim):

| band | `tn_vcm` | `tn_step` | step over vcm |
|---|---|---|---|
| 125 to 875 Hz, flicker dominated | 0.86 +- 0.09 | 1.00 +- 0.06 | 1.16 +- 0.14 |
| 875 to 9875 Hz, white dominated | 1.00 +- 0.06 | 1.12 +- 0.07 | 1.13 +- 0.09 |
| fit A/f + W + B f^2, 100 Hz to 30 kHz: W | 0.92 +- 0.05 | 1.07 +- 0.06 | 1.17 +- 0.09 |
| in band 1 Hz to 1 kHz from that fit | 27.4 uVrms | 27.4 uVrms | |

- The sde flicker generator reproduces `pnoise` in the overlap band on this circuit. The lowest bins (125 to 375 Hz) read low in both decks, 0.69 and 0.66, by 2.5 and 3 standard errors, so the slowest Lorentzians of the generator may be short. The seed-to-seed spread is about twice what the Welch statistics of one record predict, so the table uses the spread.
- DAC stepping against vcm: 1.13 +- 0.09 in the white band and 1.16 +- 0.14 in the flicker band, 1.4 and 1.1 standard errors from 1.
- `pnoise` at the two-clock period settles the question (`sc_int2_tb_pnoise_idsw_step.sim`, the real OTA with the DAC alternating to the rails and 200 ns DAC edges centred on the period boundary, 1 run per truncharm): 28.84, 28.78 and 28.79 uVrms at truncharm 150, 200 and 225 (5.4, 9.3 and 11.8 GB, 66 min, 2.5 h and 3.4 h), OTA flicker 25.69, OTA thermal 6.63, switches 10.66 at 200. Against the vcm deck on the same frequency points the input ASD is within 0.3 % below 1 kHz and 0.7 % higher at 10 kHz, so the DAC steps change the in-band noise by less than 0.5 %. The transient-noise ratios agree with that within 1.4 standard errors. The rung with the ideal opamp converges the same way, 414.6, 401.6 and 361.3 nV/sqrt(Hz) at 50, 100 and 150 against 355.6, and truncharm 250 and 300 stop with a segmentation fault after 7.3 and 10.5 GB on VACASK fb8cc20, also with `pss_minpts=4000`.
- Why it does not move (inference, with two checks): the OTA settles linearly back to its quiescent point before the end of each transfer, so the charge it leaves on C2 is set by its noise at that bias, not by what it did while slewing. With the switches noiseless (`swnoise=0`, 4096 cycles, 1 seed each) the OTA alone gives 1.08 +- 0.16 (vcm) and 0.82 +- 0.12 (step) of the `pnoise` OTA term from 0.5 to 9.5 kHz. With an ideal opamp the switches give 1.06 kT/C1 per sample with the DAC stepping against 1.16 at vcm.

### Limits

- Ideal switches as in `pnoise_idsw`: no charge injection, no Ron(V). With the PDK transmission gates and an ideal opamp, transient noise gives about 3.1 times the kT/C1 variance per sample of the ideal switches at the same settings (2.5 to 20 GHz noise bandwidth, mechanism open), which would raise the switch term by 1.75 in rms, see `doc/noise-budget.md`.
- tt, 27 C, schematic. 16 ms records reach down to about 125 Hz, the band below comes from the `pnoise` shape.

## Noise over Operating Points, at the Quantizer and in the Budget

`CORNER`, `TEMP` and `VDD` set the operating point of any deck (`CORNER=ss TEMP=125 VDD=1.45 make sim-vacask DECKS=pnoise_idsw`), the run lands in `runs/<deck>_<corner>_<temp>C_<vdd>V`. `post.py` writes a Spectre-style `<analysis>.noise_summary.txt` (`macros/scripts/noise_summary.py`, groups OTA `x1.xamp1.`, switches `x1.XS_`, CMFB `x1.xcmfb1.`, `bias_gm` `xbias.`) next to every pnoise raw, and `make noise-summary` rewrites them for every run directory.

`pnoise_idsw`, truncharm 100, all 45 points of 5 corners, -40/27/125 C and 1.45/1.5/1.55 V, one run each, input referred over 1 Hz to 1 kHz in uVrms at 1.5 V (sim):

| corner | -40 C | 27 C | 125 C |
| --- | --- | --- | --- |
| tt | 24.33 | 28.64 | 34.10 |
| ss | 25.11 | 29.58 | 35.21 |
| ff | 23.53 | 27.70 | 33.05 |
| sf | 24.09 | 28.35 | 33.74 |
| fs | 24.56 | 28.92 | 34.48 |

The supply moves every point by 0.3 to 0.4 %. Temperature sets the spread, the OTA flicker grows by 20 % from 27 to 125 C. The worst point, ss, 125 C, 1.45 V, 35.34 uVrms (OTA flicker 32.06, OTA thermal 8.19, switches 12.13), is 18.2 dB below the 288.7 uVrms budget.

`sc_int2_tb_sampled_idsw.sim` (one run, tt): the held output carries 340 uVrms differential per sample, against kT/(beta C_Ltot) = 234 uVrms with beta 0.785 and C_Ltot 192.6 fF (CMFB caps as the load), so the OTA's noise factor is about 2.1 in power. The transient-noise decks read about 580 uVrms in phase 1. That noise enters the loop like quantization error and lands in band at about 0.3 uVrms.

The system budget, the capacitor and OTA current options and the recommendation for the layout are in `doc/noise-budget.md`.
