# Chip Pinout

This document lists every bondpad of the chip together with the top-level `sg13cmos5l_dsa1_dig_top` port it is attached to and the role it plays inside the core. The die carries 21 bondpads on four sides, 20 of them bonded. Besides them the ring holds two `clamp_vddvss` cells (120 um, vdd-to-vss ESD clamp, no bondpad, `ip/sg13cmos5l_ip__clamp_vddvss`) and two `cut_vdd` cells (10 um, no bondpad, `ip/sg13cmos5l_ip__cut_vdd`) that cut the vdd band of the pad ring.

Package: QFN24, 4 x 4 mm, 0.5 mm pitch, packaged by IHP. Lead table, bond wires and gaps are in [packaging/result.md](../packaging/result.md).

Order convention:
- `PAD_WEST` / `PAD_EAST`: **bottom → top**
- `PAD_NORTH` / `PAD_SOUTH`: **left → right**

Same convention as the four `PAD_*` lists in [config.yaml](../flow/librelane/config.yaml).

Related documents:
- Floorplan: [floorplan.md](floorplan.md)
- Specifications: [specifications.md](specifications.md)
- Integration spec: [dsm2_integration.md](dsm2_integration.md)

VSS (two pads) and IOVSS are bonded only through the cavity: the pads downbond to the paddle and leads 3, 5 and 9 bond to it, so leads 3, 5 and 9 and the exposed pad are one ground. The board ties the exposed pad to ground. Leads 1, 6, 13 and 18 are not connected.


## What the chip needs

The die carries two blocks. `dsa1_dig_top` is the 128x decimation filter, the SPI slave and the configuration register file of the DSADC1 delta-sigma ADC. `dsm2_core` is a first-order discrete-time delta-sigma modulator on its own 1.5 V supply VDDA. Fourteen signals reach the outside world.

| Signal       | Direction | Rate                | Role                                                        |
| ------------ | --------- | ------------------- | ----------------------------------------------------------- |
| `clk`        | in        | 65536 Hz            | modulator sample clock, the decimator's `clk_fs`            |
| `rst_n`      | in        | static              | asynchronous, active low                                    |
| `data_in`    | in        | 65536 Hz            | the 1-bit modulator bitstream into the decimator            |
| `sclk`       | in        | 200 kHz             | SPI clock, a second and asynchronous clock domain           |
| `mosi`       | in        | 200 kHz             | SPI master out, slave in                                    |
| `ss`         | in        | static per transfer | SPI slave select, active low                                |
| `miso`       | out       | 200 kHz             | SPI master in, slave out                                    |
| `adc_conv`   | out       | 512 Hz              | conversion finished, one `clk` cycle wide, about 15.3 us    |
| `dsm_clk`    | inout     | 1.024 MHz           | dsm2 sample clock in, or dsm2's oscillator out with `di_clk_sel` |
| `do_q`       | out       | 1.024 MHz           | dsm2 bit stream, 4 mA driver, on from reset, `DSM_QOUT_EN` 1 holds it low |
| `do_q_b`     | out       | 1.024 MHz           | complement of `do_q`                                        |
| `vi`         | in        | analog              | dsm2 input, single ended, full scale 0.75 V around VDDA/2   |
| `vcm`        | inout     | analog              | VDDA/2 from dsm2, an input with `DSM_VCM_EXT`               |
| `ibias_test` | out       | analog              | dsm2 bias current copy, for `DSM_BTEST_EN`                  |

The decimated 22-bit word never leaves the die in parallel. It is read over SPI from `ADC_DATA_CH0_HIGH` and `ADC_DATA_CH0_LOW`, and the slave latches the low word at the high-word read so a two-word pair is coherent.

`miso` is driven push-pull and forced low while `ss` is high. There is no output enable, so the chip must not share a bus with another slave.

The 145 configuration register output bits stay inside the die, except the 16 that control dsm2, the decimator input mux and the `adc_conv` gate. The 16 test pads `o_tst_ctrl[15:0]` of v1.1.1 are gone, `TEST_CTRL_0` stays readable over SPI.


## Board notes

- **dsm2 runs from power-up.** With no SPI write dsm2 is enabled, leaves reset 9 to 10 `clk` periods (137 to 153 us) after `rst_n` rises, and `do_q` and `do_q_b` follow its bit stream as soon as `dsm_clk` runs. If the SPI fails, dsm2 can still be probed on these pads. Writing 1 to `DSM_EN`, `DSM_RST_B` or `DSM_QOUT_EN` turns each off, for current measurements.
- **Supply order.** VDDA comes up no later than VDD, and both no later than IOVDD. `di_ena` comes from VDD logic and is high from reset, so with VDDA first or together it reaches dsm2 at full VDDA, the start-up dsm2 simulated. VDDA is always on, dsm2 is switched off by writing `DSM_EN` 1, not by removing VDDA. With IOVDD before VDDA the IO cells of the VDDA segment drive their outputs high: `do_q` and `do_q_b` sit at 3.3 V from 28 to 202 us and IOVDD sees a 53 mA, 34 ns peak in the start-up bench ([testbenches/startup](../testbenches/startup/README.md)).
- **`rst_n`** has a pull-down on the board, and the host holds it low until all supplies are up. There is no power-on reset: until the first `rst_n` low the registers are undefined, and a random bit 8 of `BIAS_CFG_0` turns on dsm2's `dsm_clk` driver. The reset of the decimator is synchronous, so `rst_n` also needs a running `clk`.
- **`dsm_clk`** is an input after reset. The board pulls it low through 10 to 100 kOhm, never ties it, and the host drives it through a series resistor of a few hundred Ohm. With `BIAS_CFG_0` bit 8 (`di_clk_sel`) set, dsm2 drives it from its oscillator (bit 7, `di_osc_en`, 0.58 to 0.67 MHz at trim code 4 and 1.05 to 1.20 MHz at code 15, simulated on dsm2's extracted view over corners) through the 4 mA driver at IOVDD levels, 3.3 V. Bit 8 alone drives it low, so it is set only with bit 7. The ring runs only with dsm2 on. The host stops driving `dsm_clk` before it sets bit 8, and drives it again only after bit 8 is cleared.
- **`vi` and `vcm`** stay within 0 V to VDDA. While VDDA ramps they must be at 0 V or open, at most 0.1 V: at 0.75 V `vi` draws 55 uA and back-powers dsm2 to 0.46 V (dsm2 simulation). Nothing on the die limits this, the `padres` diodes go to IOVDD.
- **No DC load on `vcm`.** dsm2's vcm comes from a switched-capacitor pump with about 0.96 MOhm output resistance, so 1 MOhm to ground pulls it from 0.75 V to about 0.38 V (start-up bench 0.40 V, dsm2's estimate). Read it with a buffer or electrometer of at least 10 GOhm: a 10 MOhm probe reads about 9 % low, a 1 MOhm DMM about 50 % low. To load it, set `DSM_VCM_EXT` and drive 0.75 V from outside. `vcm` exists only with dsm2 on and `dsm_clk` running, the pump runs on the modulator clock. Otherwise it floats at 0.47 to 0.51 V.
- **Supplies before `vi`.** Driving `vi` before IOVDD is up back-powers IOVDD through the vi pad, 1.44 mA from a 50 Ohm source in the start-up bench. A slow IOVDD ramp also lets dsm2 draw current, because the `dsm_clk` pad's output into dsm2 sits mid-rail during the ramp and dsm2's LV clock buffer conducts: up to 52 uA while disabled, and with dsm2 on by default in the VDD-first order 154 uA over 100 ns post-layout and 167 uA in the schematic, above 100 uA for 0.1 to 0.3 us and above 30 uA for 2 to 12 us (start-up bench). That stops once IOVDD passes about 1.26 V. It is harmless, and bringing IOVDD up together with VDDA avoids it.
- **`ibias_test`** is read with a source-measure unit at 0.3 to 0.8 V, or across 1.5 to 4 MOhm to ground, so that 200 nA gives 0.3 to 0.8 V. dsm2 gives 0.3 V as the floor of the oscillator variant, its pass switch needs that headroom. Never 10 MOhm, which saturates the copy and gives no reading. Switch `DSM_BTEST_EN` on before a measurement, its edge pulls the bias by up to 37 % for up to 99 us. With the oscillator on (`di_osc_en`) the copy reads 0, the oscillator takes its bank.
- **Ground.** The board ties the exposed pad to ground. Leads 3, 5 and 9 are bonded to it inside the package.
- **Every lead number changes from v1.1.1.** The board follows the table below.


## Lead table

| Lead | Pad | Port | Side |
| ---- | --- | ---- | ---- |
| 1 | not connected | | W |
| 2 | IOVDD | `IOVDD` | W |
| 3 | ground lead, paddle (IOVSS pad downbonded) | `IOVSS` | W |
| 4 | VDD | `VDD` | W |
| 5 | ground lead, paddle (VSS pad downbonded) | `VSS` | W |
| 6 | not connected | | W |
| 7 | `data_in` | `input_PAD[0]` | S |
| 8 | `adc_conv` | `output_PAD[1]` | S |
| 9 | ground lead, paddle (second VSS pad downbonded) | `VSS` | S |
| 10 | `dsm_clk` | `dsm_clk_PAD` | S |
| 11 | `do_q` | `do_q_PAD` | S |
| 12 | `do_q_b` | `do_q_b_PAD` | S |
| 13 | not connected | | E |
| 14 | `vi` | `analog_PAD[0]` | E |
| 15 | `vcm` | `analog_PAD[1]` | E |
| 16 | `ibias_test` | `analog_PAD[2]` | E |
| 17 | VDDA | `VDDA` | E |
| 18 | not connected | | E |
| 19 | `miso` | `output_PAD[0]` | N |
| 20 | `ss` | `input_PAD[3]` | N |
| 21 | `mosi` | `input_PAD[2]` | N |
| 22 | `sclk` | `input_PAD[1]` | N |
| 23 | `clk` | `clk_PAD` | N |
| 24 | `rst_n` | `rst_n_PAD` | N |


## Top-level ports

Defined in [sg13cmos5l_dsa1_dig_top.sv](../rtl/sg13cmos5l_dsa1_dig_top.sv):

| Top-level port     | Direction | Width                 | Role                                          |
| ------------------ | --------- | --------------------- | --------------------------------------------- |
| `IOVDD`            | inout     | 1                     | I/O supply (3.3 V), under `USE_POWER_PINS`    |
| `IOVSS`            | inout     | 1                     | I/O ground, under `USE_POWER_PINS`            |
| `VDD`              | inout     | 1                     | Core supply (1.2 V), under `USE_POWER_PINS`   |
| `VSS`              | inout     | 1                     | Core ground, under `USE_POWER_PINS`           |
| `VDDA`             | inout     | 1                     | dsm2 supply (1.5 V), under `USE_POWER_PINS`   |
| `clk_PAD`          | inout     | 1                     | modulator sample clock, 65536 Hz              |
| `rst_n_PAD`        | inout     | 1                     | active-low reset                              |
| `input_PAD[3:0]`   | inout     | `NUM_INPUT_PADS=4`    | `data_in`, `sclk`, `mosi`, `ss`               |
| `output_PAD[1:0]`  | inout     | `NUM_OUTPUT_PADS=2`   | `miso`, `adc_conv`                            |
| `analog_PAD[2:0]`  | inout     | `NUM_ANALOG_PADS=3`   | `vi`, `vcm`, `ibias_test`                     |
| `dsm_clk_PAD`      | inout     | 1                     | dsm2 sample clock, or its oscillator out      |
| `do_q_PAD`         | inout     | 1                     | dsm2 bit stream                               |
| `do_q_b_PAD`       | inout     | 1                     | complement of the dsm2 bit stream             |

The DSA1 core supply is **1.2 V**, not the template's 1.5 V: the EZ130 8T cells the macro is hardened on are characterised at 1.08, 1.20 and 1.32 V and have no 1.5 V liberty. The I/O ring stays 3.3 V. dsm2 and the IO cells of its segment run from VDDA at 1.5 V (1.45 to 1.55 V). VSS is shared.

The bit-to-role mapping is fixed inside [sg13cmos5l_dsa1_dig_core.sv](../rtl/sg13cmos5l_dsa1_dig_core.sv) and the chip top:

| Port bit           | Source or destination signal                       |
| ------------------ | -------------------------------------------------- |
| `input_PAD[0]`     | `data_in`, through the `DEC_SRC` mux and a three-flop synchronizer |
| `input_PAD[1]`     | `sclk`                                              |
| `input_PAD[2]`     | `mosi`                                              |
| `input_PAD[3]`     | `ss`                                                |
| `output_PAD[0]`    | `miso`                                              |
| `output_PAD[1]`    | `adc_conv`, through a gate with `ADC_CONV_EN`       |
| `analog_PAD[0]`    | `vi`, dsm2's input, through the pad's `padres`      |
| `analog_PAD[1]`    | `vcm`                                               |
| `analog_PAD[2]`    | `ibias_test`                                        |
| `dsm_clk_PAD`      | `di_clk` of dsm2 from `p2c`, nowhere else. `c2p` is dsm2's `do_clk_osc`, `c2p_en` its `do_osc_oe` |
| `do_q_PAD`, `do_q_b_PAD` | `do_q`, `do_q_b` of dsm2, they do not enter the core |

`data_in` arrives with no timing relationship to `clk`, so the core synchronizes it with three flops before the macro sees it. That costs three `clk` cycles, about 46 us, which shifts any sample-for-sample comparison against the bit-true model by three input samples. With `DEC_SRC` set the synchronizer takes dsm2's `do_q_dec`, gated by `DEC_SRC`, instead of the pad.


## Pad-count overview

| Category           | Count  | Pads                                            |
| ------------------ | ------ | ----------------------------------------------- |
| Clock              | 1      | `clk_PAD`                                       |
| Reset (active low) | 1      | `rst_n_PAD`                                     |
| Digital inputs     | 4      | `data_in`, `sclk`, `mosi`, `ss`                 |
| Digital outputs    | 2      | `miso`, `adc_conv`                              |
| dsm2 digital       | 3      | `dsm_clk`, `do_q`, `do_q_b`                     |
| dsm2 analog        | 3      | `vi`, `vcm`, `ibias_test`                       |
| I/O supply         | 2      | `IOVDD`, the second one without a wire          |
| I/O ground         | 1      | `IOVSS`                                         |
| Core supply        | 1      | `VDD`                                           |
| Core ground        | 2      | `VSS`                                           |
| dsm2 supply        | 1      | `VDDA`                                          |
| **Total bondpads** | **21** | 17 to a lead, 3 downbonded to the paddle, 1 unbonded |

Ring cells without a bondpad: two `clamp_vddvss`, two `cut_vdd`. The second IOVDD cell has a bondpad but no wire.


## Location overview

| Side  | Bondpads | Function                                                        |
| ----- | -------- | --------------------------------------------------------------- |
| West  | 5        | the five DSA1 supply pads (two IOVDD), and the VDD clamp        |
| North | 6        | `rst_n`, `clk`, `sclk`, `mosi`, `ss`, `miso`                    |
| East  | 4        | `vi`, `vcm`, `ibias_test`, VDDA, then the VDDA clamp and a cut  |
| South | 6        | `data_in`, `adc_conv`, VSS, a cut, `dsm_clk`, `do_q`, `do_q_b`  |

The vdd band of the pad ring is cut twice. Between `cut_vdd_s` on the south side and `cut_vdd_e` on the east side it is VDDA. Every dsm2 pad is inside that segment and every DSA1 pad outside it.


## West (bottom → top)

| # | Top-level port   | Pad-cell instance           | Type    | Direction | Domain | Role                                       |
| - | ---------------- | --------------------------- | ------- | --------- | ------ | ------------------------------------------ |
| 1 | `VSS`            | `g_vss_pads[0].vss_pad`     | power   | inout     | gnd    | core ground, downbonded to the paddle      |
| 2 |                  | `clamp_vddvss`              | clamp   |           | 1.2 V  | VDD-to-VSS ESD clamp, no bondpad           |
| 3 | `VDD`            | `g_vdd_pads[0].vdd_pad`     | power   | inout     | 1.2 V  | core supply                                |
| 4 | `IOVSS`          | `g_iovss_pads[0].iovss_pad` | power   | inout     | gnd    | I/O ground, downbonded to the paddle       |
| 5 | `IOVDD`          | `g_iovdd_pads[0].iovdd_pad` | power   | inout     | 3.3 V  | I/O supply, lead 2                         |
| 6 | `IOVDD`          | `g_iovdd_pads[1].iovdd_pad` | power   | inout     | 3.3 V  | second I/O supply pad, not bonded          |

The IHP IO library has an iovdd-to-iovss clamp only in `IOPadIOVdd`. One cell put the whole HBM current of a signal pin zapped against VDD or VDDA through one clamp, so the second cell is there for its clamp. It is on the same IOVDD net and has no wire, the package and the lead table stay as they are (`UNBONDED_PADS` in `packaging/config.yaml`, [esd_hbm.md](esd_hbm.md)).


## North (left → right)

| # | Top-level port   | Pad-cell instance          | Type    | Direction | Role                              |
| - | ---------------- | -------------------------- | ------- | --------- | --------------------------------- |
| 1 | `rst_n_PAD`      | `rst_n_pad`                | digital | in        | asynchronous, active-low reset    |
| 2 | `clk_PAD`        | `clk_pad`                  | digital | in        | modulator sample clock, 65536 Hz  |
| 3 | `input_PAD[1]`   | `g_inputs[1].input_pad`    | digital | in        | `sclk`, 200 kHz                   |
| 4 | `input_PAD[2]`   | `g_inputs[2].input_pad`    | digital | in        | `mosi`                            |
| 5 | `input_PAD[3]`   | `g_inputs[3].input_pad`    | digital | in        | `ss`, active low                  |
| 6 | `output_PAD[0]`  | `g_outputs[0].output_pad`  | digital | out       | `miso`                            |


## South (left → right)

| # | Top-level port   | Pad-cell instance          | Type    | Direction | Domain | Role                                  |
| - | ---------------- | -------------------------- | ------- | --------- | ------ | ------------------------------------- |
| 1 | `input_PAD[0]`   | `g_inputs[0].input_pad`    | digital | in        | 1.2 V  | `data_in`, the modulator bitstream    |
| 2 | `output_PAD[1]`  | `g_outputs[1].output_pad`  | digital | out       | 1.2 V  | `adc_conv`, 512 Hz strobe             |
| 3 | `VSS`            | `g_vss_pads[1].vss_pad`    | power   | inout     | gnd    | second core ground, downbonded        |
| 4 |                  | `cut_vdd_s`                | cut     |           |        | vdd band cut, VDDA segment starts     |
| 5 | `dsm_clk_PAD`    | `dsm_clk_pad`              | digital | inout     | 1.5 V  | `dsm_clk`, 1.024 MHz in, oscillator out, 4 mA |
| 6 | `do_q_PAD`       | `do_q_pad`                 | digital | out       | 1.5 V  | `do_q`, 4 mA driver                   |
| 7 | `do_q_b_PAD`     | `do_q_b_pad`               | digital | out       | 1.5 V  | `do_q_b`, 4 mA driver                 |


## East (bottom → top)

| # | Top-level port   | Pad-cell instance          | Type    | Direction | Domain | Role                                  |
| - | ---------------- | -------------------------- | ------- | --------- | ------ | ------------------------------------- |
| 1 | `analog_PAD[0]`  | `vi_pad`                   | analog  | inout     | 1.5 V  | `vi`                                  |
| 2 | `analog_PAD[1]`  | `vcm_pad`                  | analog  | inout     | 1.5 V  | `vcm`                                 |
| 3 | `analog_PAD[2]`  | `ib_pad`                   | analog  | inout     | 1.5 V  | `ibias_test`                          |
| 4 | `VDDA`           | `vdda_pad`                 | power   | inout     | 1.5 V  | dsm2 supply, its vdd band is the segment's |
| 5 |                  | `clamp_vdda`               | clamp   |           | 1.5 V  | VDDA-to-VSS ESD clamp, a second `clamp_vddvss` |
| 6 |                  | `cut_vdd_e`                | cut     |           |        | vdd band cut, VDDA segment ends       |


## Register map reached over SPI

Five address bits are shifted in, the most significant being read when set and write when clear, then 16 data bits. `mosi` is sampled on the falling `sclk` edge and `miso` is driven on the rising edge.

Every register, its fields and resets, and which die uses which bit are in [regmap.md](regmap.md), generated from `macros/dsa1_dig/regmap.yaml`.

Inside the die only `BLOCK_CTRL_1` bit 0, which gates the decimator's reset, `TEST_CTRL_0` bits 15 to 10, the stimulus and the flag synchronizer, and the `DSM_*`, `DEC_SRC` and `ADC_CONV_EN` fields of `BIAS_CFG_0` and `BIAS_CFG_1` are read. Those reach dsm2, the decimator input mux and the `adc_conv` gate. Everything else is a pass-through to a port this chip leaves unconnected. Every host that writes a DSA1 bias profile checks `CHIP_ID` first, or it writes dsm2's trim and enables on this die.
