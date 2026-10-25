<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
Description: design spec for integrating the dsm2_core delta-sigma modulator on the DSA1 back end
-->

# Integrating dsm2_core on the DSA1 back end (spec)

Status: design agreed on 2026-10-19, not implemented. Branch `dsm2/integration`, from `tapeout/v1.1.1`, which stays the signed-off fallback. Target release v1.2.0.

## Goal and priorities

The die gets a second, analog block: `dsm2_core`, a first-order discrete-time delta-sigma modulator at 1.5 V (`sg13cmos5l_batmon`, `macros/dsm2`). It is a test and side project. DSA1 stays the main project, so:

- the digital back end must run exactly as in v1.1.1 with dsm2 unused, unpowered and unclocked
- dsm2 must cost DSA1 no power in that state
- VDD carries the DSA1 filter alone, so its power can be measured in isolation: no dsm2 circuit, no dsm pad and nothing that switches with dsm2 sits on VDD
- the die shrinks to 1.3 x 1.3 mm in a QFN24, which holds every signal of DSA1 and dsm2

## dsm2_core as seen from the chip

| | |
|---|---|
| Supply | VDDA 1.5 V (1.45 to 1.55 V), verified only there. VSSA is the chip VSS. VDDA is also the DAC reference |
| Clock | `di_clk`, fs 1.024 MHz, OSR 512, 1 kHz band. `do_q` changes 2.63 to 4.26 ns after the rising edge with the thick-oxide clock receiver (ff -40 C to ss 125 C), 2.0 to 5.0 ns with margin. Each output has its own inv_1 and inv_2 driver |
| Size | dsm2 estimates 147 x 180 um with its guard ring (2026-10-22, the second trim bank for `ibias_test`), planned as 155 x 185 um. On the 1.3 mm die at most about 165 um wide and 300 um tall |
| Layers | nothing above Metal4 |
| Inputs | all static except `di_clk`, driven at 1.2 V into one thick-oxide inverter each inside dsm2, so the block runs on full 1.5 V levels inside |
| Outputs | `do_q`, `do_q_b` at 1.5 V into their pads in the VDDA segment, gated by `di_qout_en`. `do_q_dec`, the same bit ungated, into one 1.2 V gate in the core, inside the 1.65 V oxide limit |
| Analog | `vi` (in, single ended, full scale +-0.75 V around vdd/2), `vcm` (vdd/2 from `vcm_gen`, an input with `di_vcm_ext`), `ibias_test` (current out), `vdd`, `vss` |

Control inputs, from the dsm2 design after its wave 4 rebuild:

| Input | Width | Active, reset | Function |
|---|---|---|---|
| `di_ena` | 1 | high, 0 | the whole core: bias with start-up, OTA, `clk_noverlap`, quantizer, `vcm_gen`. Off draws leakage only. A slew limiter inside dsm2 makes the 30 ns edge the OTA's enable switches need, so the pin takes a fast edge |
| `di_rst_b` | 1 | low, 0 | integrator and quantizer latch in reset |
| `di_trim` | 4 | code, `0100` | bias trim, 8.33 nA x (16 + 2 x code): code 0 133 nA, code 4 200 nA, code 15 383 nA. Change only with `di_ena` low |
| `di_dith_en` | 1 | high, 0 | quantizer dither: an LFSR on `di_clk` flips a small auxiliary input pair in the quantizer |
| `di_dith_amp` | 2 | `01` | dither amplitude |
| `di_btest_en` | 1 | high, 0 | `ibias_test`: a second trim bank that follows the trim code 1:1 with `ibias_200n`, through a series NMOS to the pad (2026-10-22). At a 0.4 V pad: code 0 129 nA, code 4 194 nA, code 15 371 nA at tt 27 C, 113 to 449 nA over all corners and -40 to 125 C. The ratio to `ibias_200n` is 0.9998 to 1.0046 over corners, sigma 1.39 % in mismatch at code 4 (post-layout tt 192.5 against 192.45 nA). Measure with an SMU at 0 to 0.8 V (under 1.4 % change), or a resistor to ground of at most 1.5 Mohm (1 Mohm reads nA as mV). A 10 Mohm load saturates the copy and gives no reading. Off, the pad leaks at most 1.3 nA (ff 125 C). Set it before a measurement: its edge pulls `ibias_200n` by up to 37 % for up to 99 us |
| `di_vcm_ext` | 1 | high, 0 | `vcm_gen` off, the `vcm` pad becomes an input and sets vcm |
| `di_qout_en` | 1 | high, 0 | `do_q` and `do_q_b` follow the quantizer, low holds both static low. `do_q_dec` is not gated, its own buffer off the quantizer latch, same 2.6 to 4.3 ns after `di_clk`. With `di_ena` low the latch preset holds `do_q` and `do_q_dec` low and `do_q_b` high (agreed with dsm2 on 2026-10-21) |

Start-up: `di_ena` high, wait 130 us (slowest corner of the bias start-up), then release `di_rst_b`, at least 2 clocks after `di_ena`.

## Pads and package

The die shrinks from 1.6 x 1.6 mm in a QFN32 to 1.3 x 1.3 mm in a QFN24 (5 x 5 mm body, 3428 um between the lead tips), 1.69 mm2, 34 % less area. The 16 test pads `o_tst_ctrl[15:0]` and the four spares go, `TEST_CTRL_0` stays readable over SPI. Three changes make 1.3 mm possible: the pads spread over all four sides, `dsa1_dig` runs at 75 % utilization instead of 60 %, and the core ring is 5 um wide instead of 15 um.

Leads: 14 signals (8 for DSA1, 6 for dsm2) and VDD, IOVDD, VDDA on 17 of 24 leads. VSS (two pads) and IOVSS downbond to the paddle, leads 3, 5 and 9 bond to the paddle as ground leads. Leads 1, 6, 13, 18 are NC, so 13 and 18 keep the other wires off the analog leads.

| Lead | Pad | Cell | Side |
|---|---|---|---|
| 1 | NC | | W |
| 2 | IOVDD | `IOPadIOVdd` | W |
| 3 | ground lead, to the paddle (IOVSS pad downbonded) | `IOPadIOVss` | W |
| 4 | VDD | `IOPadVdd` | W |
| | VDD clamp | `sg13cmos5l_ip__clamp_vddvss`, 120 um, no bondpad | W |
| 5 | ground lead, to the paddle (VSS pad downbonded) | `IOPadVss` | W |
| 6 | NC | | W |
| 7 | `data_in` | `IOPadIn` | S |
| 8 | `adc_conv` | `IOPadOut30mA` | S |
| 9 | ground lead, to the paddle (second VSS pad downbonded) | `IOPadVss` | S |
| | vdd band cut | `sg13cmos5l_ip__cut_vdd`, 10 um, no bondpad | S |
| 10 | `dsm_clk` | `IOPadIn` | S |
| 11 | `do_q` | `IOPadOut4mA` | S |
| 12 | `do_q_b` | `IOPadOut4mA` | S |
| 13 | NC | | E |
| 14 | `vi` | `IOPadAnalog`, `padres` pin to the macro | E |
| 15 | `vcm` | `IOPadAnalog`, `padres` | E |
| 16 | `ibias_test` | `IOPadAnalog`, `padres` | E |
| 17 | VDDA | `IOPadVdd`, its vdd band is the segment's | E |
| | VDDA clamp | `sg13cmos5l_ip__clamp_vddvss`, a second copy, on the segment's band | E |
| | vdd band cut | `sg13cmos5l_ip__cut_vdd`, 10 um, no bondpad | E |
| 18 | NC | | E |
| 19 | `miso` | `IOPadOut30mA` | N |
| 20 | `ss` | `IOPadIn` | N |
| 21 | `mosi` | `IOPadIn` | N |
| 22 | `sclk` | `IOPadIn` | N |
| 23 | `clk` | `IOPadIn` | N |
| 24 | `rst_n` | `IOPadIn` | N |

Die pads per side, in the flow's ring order (west and east bottom to top, north and south left to right), 660 um between the corner cells:

| Side | Cells | Gaps |
|---|---|---|
| W | VSS, clamp_vddvss, VDD, IOVSS, IOVDD | 36 um, ends 38 um |
| N | `rst_n`, `clk`, `sclk`, `mosi`, `ss`, `miso` | 24 um, ends 30 um |
| E | `vi`, `vcm`, `ibias_test`, VDDA, clamp_vddvss, cut_vdd | 30 um, ends 30 um |
| S | `data_in`, `adc_conv`, VSS, cut_vdd, `dsm_clk`, `do_q`, `do_q_b` | 20 um, ends 25 um |

- West holds only supplies, east only dsm2's analog pads, VDDA and its clamp. `dsm_clk`, `do_q` and `do_q_b` sit on the south side under dsm2, so their routes never cross the analog nets.
- The two cut cells bound the VDDA segment, which runs from `dsm_clk` on the south side round the south-east corner to the VDDA clamp on the east side. Every dsm pad is inside it, every DSA1 pad outside.
- With `PAD_SPACING_MULTIPLE` 2 every gap lands on the 1 um site grid.
- The draft bond plan ran through `packaging/scripts/run_bondplan.py` on a synthetic die with these pads (2026-10-21): 23 wires, length 1394 to 1788 um, minimum wire gap 64.9 um (`do_q` to `do_q_b`), maximum lead skew 5.5 deg, no crossing, no guard warning on leads 14 to 17. The paddle was taken as 3200 um, which still has to be checked against the EUROPRACTICE QFN24 drawing.
- `do_q` and `do_q_b` sit side by side so their currents largely cancel. The 4 mA drivers keep their bounce low.
- The second VSS pad gives dsm2's ground a short path to the paddle and the ESD network a second path.
- Every lead number changes from v1.1.1. The board has to follow this table. `dsm_clk` is tied low when dsm2 is not used.

IOVDD stays a pin. Its voltage is free within what the IO cells allow (characterized at 3.0 to 3.6 V, `IOPadIn` switches down to 1.5 V at TT and 1.6 V at SS in simulation), but the hosts' IO level has to match it. That is a board decision and changes nothing on the die.

## Floorplan

```
              N: rst_n clk sclk mosi ss miso
        +--------------------------------+
   IOVDD| +-----------+                  |
   IOVSS| |           |                  |clamp
     VDD| | dsa1_dig  |                  |VDDA
   clamp| | 355 x 570 |        +-------+ |ibias_test
     VSS| |           |        | dsm2  | |vcm
        | +-----------+        +-------+ |vi
        +--------------------------------+
     S: data_in adc_conv VSS dsm_clk do_q do_q_b
```

- Die 1300 x 1300 um, core 345 to 955 um (610 x 610 um). The pad ring is as today, the core ring between it and the core is 5 um per net instead of 15 um. The core draws microwatts, so IR and EM are checked again but not expected to bind.
- `dsa1_dig` is re-hardened at about 355 x 570 um as the west column, 75 % utilization (137.7k um2 of cells, 60 % today, with 23 router DRC errors in its first iteration, so there is routing headroom). The exact size snaps to the row and site grid. If it does not route at 75 %, 70 % gives about 370 x 590 um and the die stays 1.3 mm with less room for dsm2. `pin_order.cfg`: `rst_b`, `clk` and the SPI pins north, `data_in` and `adc_conv` south, `o_bias_cfg[34:0]` east in the south part, toward dsm2. The macro ring keeps one top-level PDN layer free, as now.
- `dsm2_core` sits in the south-east of the core. Its east edge carries `vi`, `vcm`, the `ibias_test` output and VDDA, toward the east pads. Its south edge carries `do_q_b`, `do_q`, `di_clk` (east to west), about 45 to 55 um from its east edge where its two internal columns meet, toward the south pads. The south-east corner stays free for dsm2's internal `vi` route and bias stripes (agreed with dsm2 on 2026-10-21, exact x after its rebuild). Its west edge carries `di_ena`, `di_rst_b`, `di_trim[3:0]`, `di_dith_en`, `di_dith_amp[1:0]`, `di_vcm_ext`, `di_btest_en`, `di_qout_en`, and `do_q_dec` at its south end toward the decimator. The psub guard ring on VSS is inside the macro.
- Around dsm2 the chip top places a 10 um placement halo, keeps the power grid off it on every layer, blocks TopMetal1 over it, and keeps fill out.
- `dsa1_dig` came out at 370.02 x 588 um (66 % utilization): the 75 % outline failed placement (DPL-0036, the cell padding took the core over 90 %). It sits 5 um from the core's west edge.
- Room for dsm2 east of the macro: from about x 750 (macro edge at 720 plus a 30 um channel for `o_bias_cfg` and the glue cells) to 955, minus its halo and 20 um at the core edge. So dsm2 can be at most about 165 um wide and about 300 um tall. dsm2's estimate, 147 x 180 um, fits the planned 155 x 185 um box.

## Registers

`BIAS_CFG_0` and `BIAS_CFG_1` hold DSA1's OTA, CCRO, comparator and buffer bias fields, which do nothing on this die. On this die they carry dsm2, as `only: cmos5l` fields, and the DSA1 fields become `only: dsa1`.

| Register | Bits | Field | Reset | To |
|---|---|---|---|---|
| `BIAS_CFG_0` | 3:0 | `DSM_TRIM` | `0100` | `di_trim` |
| | 4 | `DSM_DITH_EN` | 0 | `di_dith_en` |
| | 6:5 | `DSM_DITH_AMP` | `01` | `di_dith_amp` |
| | 9:7 | `DSM_SPARE` | 0 | register only, no dsm2 pins |
| | 15:10 | TBD | 0 | |
| `BIAS_CFG_1` | 0 | `DSM_EN` | 0 | `di_ena` |
| | 1 | `DSM_RST_B` | 0 | `di_rst_b` |
| | 2 | `DEC_SRC` | 0 | decimator input, 0 the `data_in` pad, 1 `do_q` |
| | 3 | `DSM_BTEST_EN` | 0 | `di_btest_en` |
| | 4 | `DSM_VCM_EXT` | 0 | `di_vcm_ext` |
| | 5 | `DSM_QOUT_EN` | 0 | `di_qout_en`, the `do_q` and `do_q_b` pads |
| | 6 | `ADC_CONV_EN` | 1 | the `adc_conv` pad, 0 holds it low |
| | 15:7 | TBD | 0 | |

- Both registers already leave the macro on `o_bias_cfg[34:3]`. The macro gets no new port, only this die's resets.
- `macros/scripts/regmap_gen.py` today rejects two fields on one bit (`regmap_gen.py:124`). It is changed to allow an overlap between fields that are `only` on different dies, and to keep rejecting every other overlap.
- After reset dsm2 is off and in reset, its pads are static, and the decimator reads the `data_in` pad, as in v1.1.1.
- Every host that writes a DSA1 bias profile has to check `CHIP_ID` first, or it writes dsm2's trim and enables on this die. `doc/regmap.md` says so.
- The svn side (EasyConfig, the ESP32 host) changes only when the user says so.

## Glue logic in the chip top

In `rtl/sg13cmos5l_dsa1_dig_core.sv`, beside the existing `data_in` synchronizer, all on VDD:

- `do_q_dec` passes one EZ130 `AND2X1` with `DEC_SRC` (a NAND2 and an inverter inside), instantiated by hand and kept by `dont_touch`. With `DEC_SRC` low its NMOS stack is cut, so neither a running dsm2 nor an unpowered one makes anything in VDD switch or draw crossover current.
- `DEC_SRC` selects that gated bit or the `data_in` pad in front of the three-flop synchronizer. The decimator samples on `clk`, dsm2 changes `do_q_dec` on the rising `dsm_clk`, so this path works only with `clk` the inverted `dsm_clk` from one source. Then the decimator reads each bit about 488 ns from either edge, gives 8 kHz words with the passband edge at 2 kHz, and suits DC and spot reads over SPI. The full-rate stream is the `do_q` pad.
- `adc_conv` passes an `AND2X1` with `ADC_CONV_EN` before its pad, so a power measurement can hold that pad still too.
- `do_q` and `do_q_b` do not enter the core. They run from dsm2 straight to their pads in the VDDA segment.
- `o_bias_cfg` goes straight to dsm2's inputs. These lines are static, so VDD supplies only their leakage.

## Clocks

- `clk` still drives the decimator only. With `DEC_SRC` it runs at 1.024 MHz (976.6 ns), faster than the 1000 ns the SDCs constrain today, so the chip and the macro SDC constrain `clk` at 950 ns.
- `dsm_clk` goes from its `IOPadIn` to `di_clk` and nowhere else. No SDC clock, `RSZ_DONT_TOUCH_RX` keeps the resizer off it.

## VDDA, the segment and the analog nets

- The pad ring's vdd band is cut twice, by `sg13cmos5l_ip__cut_vdd`: a 10 um ring cell with the iovss, iovdd and vss bands of an IO filler and no vdd band on any layer. Between the two cuts the vdd band is VDDA. The iovss, iovdd and vss bands stay continuous.
- VDDA enters through a library `IOPadVdd`, whose own clamp ties it to iovss, and a second, unchanged `clamp_vddvss` next to it ties it to vss. Without that second clamp a zap against VSS would go through IOVDD and its clamp, the detour that put 8.4 V on VDD before `clamp_vddvss`.
- Every IO cell in the segment (`dsm_clk`, `do_q`, `do_q_b`, `vi`, `vcm`, `ibias_test`) runs its core side on VDDA. Their switching current goes to VDDA and IOVDD, never to VDD.
- dsm2's `vdd` takes VDDA from the segment's band: a strap drawn as a special net in the pdngen wrapper in `PDN_CFG`, from the band's Metal3 at the core edge of the VDDA pad, wide on Metal3, under the core ring (Metal4 and TopMetal1), to dsm2's `vdd` pin.
- The core ring is VDD only. `PDN_CORE_RING_CONNECT_TO_PADS` must not reach the segment's vdd pins, which are on net VDDA in the netlist. The first build checks this in the DEF.
- `vi`, `vcm` and the `ibias_test` net are drawn from their pads' `padres` pins the same way, `vi` between VSS tracks.
- dsm2, the segment's pads and these nets live in the chip top module, not in the core, so each net keeps its top-level name in the netlist. Only the digital controls and `do_q_dec` cross into the core.
- `RSZ_DONT_TOUCH_RX` covers these nets and `dsm_clk`, the SDC false-paths the analog ports. Synthesis names an inout net after its deepest port, so the regex is checked against the netlist, and the netlist is checked for antenna diodes on these nets, which `dont_touch` does not prevent.
- VDDA is a net of its own in LVS, not tied to VDD through the substrate, so a VDDA to VDD short shows in the GDS-level LVS.

## Power states

| State | VDD | IOVDD | VDDA | `dsm_clk` | Expected |
|---|---|---|---|---|---|
| DSA1 | on | on | 1.5 V | low or running | dsm2 off (`DSM_EN` 0), its pads static (`DSM_QOUT_EN` 0), VDD carries the filter alone |
| DSA1 measured | on | on | 1.5 V | any | as DSA1, and `ADC_CONV_EN` 0 holds the `adc_conv` pad still. VDD and IOVDD carry only the filter's switching |
| dsm2 | on | on | 1.5 V | 1.024 MHz | after `DSM_EN`, 130 us, `DSM_RST_B`, then `DSM_QOUT_EN` for the pads or `DEC_SRC` for the decimator, or both |

- VDDA is always on, and comes up no later than IOVDD, like VDD. v1.1.1's start-up bench showed that IO cells whose core supply is down while IOVDD is up drive their outputs high and flip together in a 21 ns, 381 mA spike on IOVDD when the core supply arrives. The segment's IO cells run on VDDA, so VDDA at 0 V with IOVDD up is that state. dsm2 is switched off with `DSM_EN`, not by removing VDDA.
- `vi` and `vcm` stay within 0 V to VDDA. With VDDA down during sequencing they must be at 0 V or high-Z, at most 0.1 V: at 0.75 V `vi` draws 55 uA and back-powers dsm2 to 0.46 V (dsm2 sim). The `padres` diodes go to IOVDD, so nothing on the die limits this. It goes into the board notes.
- dsm2's inputs have one thick-oxide inverter each, so 1.2 V highs from the registers give full 1.5 V levels inside (a plain LV gate leaked and mistrimmed, dsm2 sim on `:next`). The receivers are sized for VDD 1.08 V against VDDA 1.55 V. Each draws from VDDA while its input is high: 7 nA at tt, 1.13 uA with a 1.08 V high at ff 125 C, 29 nA with a 1.32 V high. After reset only `di_trim[2]` is high, so the DSA1 state costs VDDA up to about 1.1 uA at that corner, 7 nA at tt, and VDD nothing but leakage.
- VDD off with VDDA on: all inputs are 0, `di_ena` is low, dsm2 stays off and draws 134 nA at tt 27 C, 2.65 uA at ff 125 C (sim, not fully settled).
- The decimator path samples `do_q_dec` on the inverted edge, about 488 ns after it changes, so the 5 ns do not matter there.

## Tools

The DSM die is signed off in `registry.iic.jku.at:5000/iic-osic-tools:next`, the image of dsm2's sign-off. 2026.08 is not a valid LVS reference for dsm2: its LVS drops devices whose terminals all sit on one net (dummies, tied-off fingers) from the layout netlist and still reports a match, and dsm2 has many of those.

| | |
|---|---|
| amd64 (laptop) | image id `sha256:bb525d654d8d7fa4abf2ff4f16443af8a3c3acedf5fded023ce3515200b29f8e`, repo digest `sha256:65771d5c6be66df4f8a7522421355b53964ce643dc4cc612b605f645063b1af4`, built 2026-10-08 |
| arm64 (`gigaarm`) | image id `sha256:0ad78d950901...`, repo digest `sha256:2629177ffdeb631b4536cfb4cab5671b65eb2214bcea26d181bb7a878145f88b` |
| PDK | ihp-sg13cmos5l `5eddf3e96c4b1a42bffe90dd58daa6089a77fc23`, from the image |
| Tools | Magic 8.3.684, KLayout 0.30.12, ngspice-47 |

- `:next` moves, so jobs pin the digest, and `signoff_env.txt` records it.
- The registry needs the JKU VPN. `gigaarm` already has the arm64 build, the laptop the amd64 one. They are two builds, so one DRC and one LVS run on both before results from the two hosts are mixed.
- The ESD bench ran on 2026.09 for v1.1.1, and moves to `:next` too, so every row of `doc/signoff.md` comes from one image.
- The v1.1.1 LVS on 2026.08 is not hit by that bug: neither `clamp_vddvss`'s CDL nor the PDK stdcell CDL has a device with all terminals on one net, and the IO cells are black boxes in `top_lvs.sh`.

## Verification

Every row of `doc/signoff.md` is earned again on the delivery GDS. New or changed checks, each shown to fail on a mutant:

| Check | Pass |
|---|---|
| Register generator | an overlap between `only` fields of different dies passes, any other overlap fails |
| Registers | each die reads back its own resets, both die views of `BIAS_CFG_0/1` in the generated files |
| Chip cocotb, RTL and GL | with dsm2 running and `DEC_SRC` low the `DEC_SRC` gate stays 0 while `do_q_dec` toggles. With `DEC_SRC` high, a `do_q_dec` stream decimates bit-exactly against `models/decimator_model.py`. `ADC_CONV_EN` low holds the `adc_conv` pad low |
| Netlist | no buffer and no antenna diode on `vi`, `vcm`, `ibias_test`, VDDA, `dsm_clk`, `do_q`, `do_q_b`. No cell on VDD has an input from dsm2 except the `DEC_SRC` gate |
| VDD isolation | the DEF-level and the GDS-level LVS have VDD and VDDA apart, and no IO cell of the segment has its vdd pin on VDD. In the start-up bench, the VDD current with dsm2 running, its pads switching and `DEC_SRC` low equals the one with dsm2 off, within the bench's resolution |
| Layout | no chip-top shape over dsm2 except at its pins |
| Cut cell | DRC alone and abutted between two IO cells, a connectivity probe that finds iovss, iovdd and vss continuous and no vdd metal on any layer, each failing on a mutant with one vdd strip drawn. The second `clamp_vddvss` is the signed-off cell, its bench rerun at 1.5 V |
| Top LVS | dsm2 and both clamp copies device by device, VDDA a separate net. A reference with VDDA joined to VDD fails |
| HBM ESD | every pairing with VDDA, `vi`, `vcm`, `ibias_test`, `dsm_clk`, `do_q`, `do_q_b` has a path. Without the segment's `clamp_vddvss` the check fails. Peak voltages on the 1.2 V and the 1.5 V nodes reported |
| Supply start-up | the board order (VDD and VDDA no later than IOVDD) clean, and IOVDD before VDDA run once to show the segment's output spike the board rule avoids |
| Bounce | `do_q` and `do_q_b` at 1.024 MHz with `miso` and `adc_conv` switching, the swing on `vi` and VDDA reported |
| Core ring | IR drop and current density of the 5 um core ring from the final DEF (`em-probe`), against the limits used for v1.1.1 |
| DSA1 power | in the DSA1 state, the static VDD and IOVDD current of the start-up bench (IO cells and clamps as transistors, core as XSPICE) is within that of v1.1.1 on the same bench, run on both layouts, or the difference is named. The macro's gate-level power at 65.536 kHz is within v1.1.1's |
| dsm2 inputs | in dsm2's own bench at the two VDD and VDDA extremes: no extra VDDA current, the bias at code 4 within its trim step, the `di_ena` edge at the pin of the OTA at least 30 ns |
| Macro | LEC, `sim-gl`, `model-gate`, `sim-cdc`, STA, Magic DRC after the re-harden at 75 % utilization |
| Bond plan | `make bondplan` in the QFN24 on the delivery GDS: the lead table above, minimum gap at least 60 um, no crossing, no other wire within 60 um of leads 14 to 17 |

## Order of work

Each step is committed on its own.

| # | Step | Needs |
|---|---|---|
| 1 | Register generator change and its test, `regmap.yaml`, regenerate, register tests | |
| 2 | Chip RTL: east pads, glue, dsm2 blackbox, clamp instance, cocotb | 1 |
| 3 | `cut_vdd` with its checks and mutants, the second `clamp_vddvss` placed | |
| 4 | Re-harden `dsa1_dig` as the west column, the macro checks | 1 |
| 5 | Chip top with a dsm2 abstract (LEF on the agreed edges, blackbox model, outline-only GDS named as a placeholder): `PAD_EAST`, placement, halo, obstructions, the pdngen wrapper, `RSZ_DONT_TOUCH_RX`, SDC, `make build-top`, bond plan | 2, 3, 4, dsm2 pin edges |
| 6 | Benches: ESD, start-up, bounce, top LVS scripts, schematic generator | 5 |
| 7 | The real dsm2 GDS and LEF in, rebuild, full sign-off | dsm2 GDS |
| 8 | Release v1.2.0, `doc/signoff.md`, the md5 in `scripts/submission.sh` | 7 |

Effort: about 6 to 8 working days. Registers, RTL and cocotb 1 day, the cut cell 0.5, the re-harden 1 to 1.5, the chip top with VDDA and the drawn nets 1.5 to 2 (the main risk), the benches 1, the sign-off 1 day of attention. Steps 1 to 6 do not wait for dsm2.

Compute: the heavy jobs (macro re-harden, chip builds, the ESD matrix, the start-up benches) run on the 128-core compute host `gigaarm` in a scratch checkout, with `-e PDK=ihp-sg13cmos5l`, where the ESD matrix takes minutes instead of the 20 h it took on the laptop. That needs the JKU VPN. Results come back to the laptop as files, the run directories stay there. Without the VPN the jobs run on the laptop, one at a time, and the sign-off needs about 1.5 days of compute.

## Open

- From dsm2: the pin positions and the exact outline (after the `sc_int2` rework, this week), the GDS and LEF (end of the week of 2026-10-19 at the earliest).
- Disk: the laptop is at 97 %. Runs on `gigaarm` keep their run directories there. Old run directories on the laptop are cleared, after review, before any heavy job runs locally.
