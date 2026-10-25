# Chip Pinout

This document lists every bondpad of the chip together with the top-level `sg13cmos5l_dsa1_dig_top` port it is attached to and the role it plays inside the core. The padframe layout is **8 pads per side, 32 bondpads total**. The west side also holds `clamp_vddvss`, a 120 um vdd-to-vss ESD clamp cell without a bondpad between the VSS and the VDD pad (`ip/sg13cmos5l_ip__clamp_vddvss`), so its pads sit at 100 um pitch, the other sides at 114 um.

Order convention:
- `PAD_WEST` / `PAD_EAST`: **bottom → top**
- `PAD_NORTH` / `PAD_SOUTH`: **left → right**

Same convention as the four `PAD_*` lists in [config.yaml](../flow/librelane/config.yaml).

Related documents:
- Floorplan: [floorplan.md](floorplan.md)
- Specifications: [specifications.md](specifications.md)
- Package pin assignment and bond report: [packaging/result.md](../packaging/result.md)

In the QFN32, VSS and IOVSS are bonded only through the cavity: both pads downbond to the paddle and leads 5 and 7 bond to it, so leads 5 and 7 and the exposed pad are one ground. The board ties the exposed pad to ground, and pins 19 and 20, the bidir spares, too: they are never driven and their input buffers would float.


## What the chip needs

The die carries one macro, `dsa1_dig_top`: the 128x decimation filter, the SPI slave and the configuration register file of the DSADC1 delta-sigma ADC. Eight signals reach the outside world.

| Signal     | Direction | Rate                | Role                                                        |
| ---------- | --------- | ------------------- | ----------------------------------------------------------- |
| `clk`      | in        | 65536 Hz            | modulator sample clock, the decimator's `clk_fs`             |
| `rst_n`    | in        | static              | asynchronous, active low                                     |
| `data_in`  | in        | 65536 Hz            | the 1-bit modulator bitstream into the decimator             |
| `sclk`     | in        | 200 kHz             | SPI clock, a second and asynchronous clock domain            |
| `mosi`     | in        | 200 kHz             | SPI master out, slave in                                     |
| `ss`       | in        | static per transfer | SPI slave select, active low                                 |
| `miso`     | out       | 200 kHz             | SPI master in, slave out                                     |
| `adc_conv` | out       | 512 Hz              | conversion finished, one `clk` cycle wide, about 15.3 us     |

The decimated 22-bit word never leaves the die in parallel. It is read over SPI from `ADC_DATA_CH0_HIGH` and `ADC_DATA_CH0_LOW`, and the slave latches the low word at the high-word read so a two-word pair is coherent.

`miso` is driven push-pull and forced low while `ss` is high. There is no output enable, so the chip must not share a bus with another slave.

The 145 configuration register output bits stay inside the die. Carrying the register file is deliberate: its area is what makes this block comparable against the older `dsa1_dig_top`. The one exception is `o_tst_ctrl[15:0]`, brought out on 16 spare pads so the SPI write path can be checked in silicon.


## Top-level ports

Defined in [sg13cmos5l_dsa1_dig_top.sv](../rtl/sg13cmos5l_dsa1_dig_top.sv):

| Top-level port     | Direction | Width                 | Role                                          |
| ------------------ | --------- | --------------------- | --------------------------------------------- |
| `IOVDD`            | inout     | 1                     | I/O supply (3.3 V), under `USE_POWER_PINS`    |
| `IOVSS`            | inout     | 1                     | I/O ground, under `USE_POWER_PINS`            |
| `VDD`              | inout     | 1                     | Core supply (1.2 V), under `USE_POWER_PINS`   |
| `VSS`              | inout     | 1                     | Core ground, under `USE_POWER_PINS`           |
| `clk_PAD`          | inout     | 1                     | modulator sample clock, 65536 Hz              |
| `rst_n_PAD`        | inout     | 1                     | active-low reset                              |
| `input_PAD[3:0]`   | inout     | `NUM_INPUT_PADS=4`    | `data_in`, `sclk`, `mosi`, `ss`               |
| `output_PAD[17:0]` | inout     | `NUM_OUTPUT_PADS=18`  | `miso`, `adc_conv`, `o_tst_ctrl[15:0]`        |
| `bidir_PAD[1:0]`   | inout     | `NUM_BIDIR_PADS=2`    | spare, driven low and never enabled           |
| `analog_PAD[1:0]`  | inout     | `NUM_ANALOG_PADS=2`   | spare, unconnected in the core                |

The core supply is **1.2 V**, not the template's 1.5 V: the EZ130 8T cells the macro is hardened on are characterised at 1.08, 1.20 and 1.32 V and have no 1.5 V liberty. The I/O ring stays 3.3 V.

The bit-to-role mapping is fixed inside [sg13cmos5l_dsa1_dig_core.sv](../rtl/sg13cmos5l_dsa1_dig_core.sv):

| Port bit           | Source or destination signal                       |
| ------------------ | -------------------------------------------------- |
| `input_PAD[0]`     | `data_in`, through a three-flop synchronizer        |
| `input_PAD[1]`     | `sclk`                                              |
| `input_PAD[2]`     | `mosi`                                              |
| `input_PAD[3]`     | `ss`                                                |
| `output_PAD[0]`    | `miso`                                              |
| `output_PAD[1]`    | `adc_conv`                                          |
| `output_PAD[17:2]` | `o_tst_ctrl[15:0]`                                  |

`data_in` arrives with no timing relationship to `clk`, so the core synchronizes it with three flops before the macro sees it. That costs three `clk` cycles, about 46 us, which shifts any sample-for-sample comparison against the MATLAB reference by three input samples.


## Pad-count overview

| Category           | Count  | Pads                                            |
| ------------------ | ------ | ----------------------------------------------- |
| Clock              | 1      | `clk_PAD`                                       |
| Reset (active low) | 1      | `rst_n_PAD`                                     |
| Digital inputs     | 4      | `data_in`, `sclk`, `mosi`, `ss`                 |
| Digital outputs    | 18     | `miso`, `adc_conv`, 16 x `o_tst_ctrl`           |
| Digital bidir      | 2      | spare                                           |
| Analog             | 2      | spare                                           |
| I/O supply         | 1      | `IOVDD`                                         |
| I/O ground         | 1      | `IOVSS`                                         |
| Core supply        | 1      | `VDD`                                           |
| Core ground        | 1      | `VSS`                                           |
| **Total**          | **32** |                                                 |


## Location overview

| Side  | Pad count | Function                                                      |
| ----- | --------- | ------------------------------------------------------------- |
| West  | 8         | `miso`, the four supplies, `data_in`, `rst_n`, `clk`          |
| North | 8         | `sclk`, `mosi`, `ss`, `adc_conv`, `o_tst_ctrl[3:0]`           |
| South | 8         | `o_tst_ctrl[11:4]`                                            |
| East  | 8         | 2 analog spares, 2 bidir spares, `o_tst_ctrl[15:12]`          |


## West (bottom → top)

| # | Top-level port   | Pad-cell instance           | Type    | Direction | Domain | Role                                       |
| - | ---------------- | --------------------------- | ------- | --------- | ------ | ------------------------------------------ |
| 1 | `output_PAD[0]`  | `g_outputs[0].output_pad`   | digital | out       | 1.2 V  | `miso`                                     |
| 2 | `VSS`            | `g_vss_pads[0].vss_pad`     | power   | inout     | gnd    | core ground                                |
| 3 | `VDD`            | `g_vdd_pads[0].vdd_pad`     | power   | inout     | 1.2 V  | core supply                                |
| 4 | `IOVSS`          | `g_iovss_pads[0].iovss_pad` | power   | inout     | gnd    | I/O ground                                 |
| 5 | `IOVDD`          | `g_iovdd_pads[0].iovdd_pad` | power   | inout     | 3.3 V  | I/O supply                                 |
| 6 | `input_PAD[0]`   | `g_inputs[0].input_pad`     | digital | in        | 1.2 V  | `data_in`, the modulator bitstream         |
| 7 | `rst_n_PAD`      | `rst_n_pad`                 | digital | in        | 1.2 V  | asynchronous, active-low reset             |
| 8 | `clk_PAD`        | `clk_pad`                   | digital | in        | 1.2 V  | modulator sample clock, 65536 Hz           |


## North (left → right)

| # | Top-level port   | Pad-cell instance          | Type    | Direction | Role                              |
| - | ---------------- | -------------------------- | ------- | --------- | --------------------------------- |
| 1 | `input_PAD[1]`   | `g_inputs[1].input_pad`    | digital | in        | `sclk`, 200 kHz                   |
| 2 | `input_PAD[2]`   | `g_inputs[2].input_pad`    | digital | in        | `mosi`                            |
| 3 | `input_PAD[3]`   | `g_inputs[3].input_pad`    | digital | in        | `ss`, active low                  |
| 4 | `output_PAD[1]`  | `g_outputs[1].output_pad`  | digital | out       | `adc_conv`, 512 Hz strobe         |
| 5 | `output_PAD[2]`  | `g_outputs[2].output_pad`  | digital | out       | `o_tst_ctrl[0]`                   |
| 6 | `output_PAD[3]`  | `g_outputs[3].output_pad`  | digital | out       | `o_tst_ctrl[1]`                   |
| 7 | `output_PAD[4]`  | `g_outputs[4].output_pad`  | digital | out       | `o_tst_ctrl[2]`                   |
| 8 | `output_PAD[5]`  | `g_outputs[5].output_pad`  | digital | out       | `o_tst_ctrl[3]`                   |


## South (left → right)

| # | Top-level port   | Pad-cell instance          | Type    | Direction | Role                                        |
| - | ---------------- | -------------------------- | ------- | --------- | ------------------------------------------- |
| 1 | `output_PAD[6]`  | `g_outputs[6].output_pad`  | digital | out       | `o_tst_ctrl[4]`                             |
| 2 | `output_PAD[7]`  | `g_outputs[7].output_pad`  | digital | out       | `o_tst_ctrl[5]`                             |
| 3 | `output_PAD[8]`  | `g_outputs[8].output_pad`  | digital | out       | `o_tst_ctrl[6]`                             |
| 4 | `output_PAD[9]`  | `g_outputs[9].output_pad`  | digital | out       | `o_tst_ctrl[7]`                             |
| 5 | `output_PAD[10]` | `g_outputs[10].output_pad` | digital | out       | `o_tst_ctrl[8]`                             |
| 6 | `output_PAD[11]` | `g_outputs[11].output_pad` | digital | out       | `o_tst_ctrl[9]`                             |
| 7 | `output_PAD[12]` | `g_outputs[12].output_pad` | digital | out       | `o_tst_ctrl[10]`, the flag-sync select bit  |
| 8 | `output_PAD[13]` | `g_outputs[13].output_pad` | digital | out       | `o_tst_ctrl[11]`                            |


## East (bottom → top)

| # | Top-level port   | Pad-cell instance          | Type    | Direction | Role                        |
| - | ---------------- | -------------------------- | ------- | --------- | --------------------------- |
| 1 | `analog_PAD[0]`  | `g_analogs[0].analog_pad`  | analog  | inout     | spare                       |
| 2 | `analog_PAD[1]`  | `g_analogs[1].analog_pad`  | analog  | inout     | spare                       |
| 3 | `bidir_PAD[0]`   | `g_bidirs[0].bidir_pad`    | digital | bidir     | spare, output enable tied 0 |
| 4 | `bidir_PAD[1]`   | `g_bidirs[1].bidir_pad`    | digital | bidir     | spare, output enable tied 0 |
| 5 | `output_PAD[14]` | `g_outputs[14].output_pad` | digital | out       | `o_tst_ctrl[12]`            |
| 6 | `output_PAD[15]` | `g_outputs[15].output_pad` | digital | out       | `o_tst_ctrl[13]`            |
| 7 | `output_PAD[16]` | `g_outputs[16].output_pad` | digital | out       | `o_tst_ctrl[14]`            |
| 8 | `output_PAD[17]` | `g_outputs[17].output_pad` | digital | out       | `o_tst_ctrl[15]`            |


## Register map reached over SPI

Five address bits are shifted in, the most significant being read when set and write when clear, then 16 data bits. `mosi` is sampled on the falling `sclk` edge and `miso` is driven on the rising edge.

Every register, its fields and resets, and which die uses which bit are in [regmap.md](regmap.md), generated from `macros/dsa1_dig/regmap.yaml`.

Inside the die only `BLOCK_CTRL_1` bit 0, which gates the decimator's reset, and `TEST_CTRL_0` bits 15 to 10, the stimulus and the flag synchronizer, are read. Everything else is a pass-through to a port this chip leaves unconnected, except `TEST_CTRL_0`, which reaches the pads.
