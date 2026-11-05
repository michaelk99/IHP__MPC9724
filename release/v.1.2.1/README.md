# sg13cmos5l_dsa1_dig_top v1.2.1

The DSA1 chip for the IHP CMOS5L MPW run of 2026-11-09, 1.3 x 1.3 mm in a QFN24: the digital back end `dsa1_dig` and dsm2, the first-order delta-sigma modulator in its oscillator variant of 2026-11-02, from branch `dsm2/integration` of this repository. The last commit that changes this folder is the release.

It differs from v1.2.0 in the chip glue only: dsm2 runs from power-up with no SPI write. After `rst_n` it is enabled, leaves reset 9 to 10 `clk` periods (137 to 153 us) later, and `do_q` and `do_q_b` follow its bit stream, so it can be probed even if the SPI fails. `DSM_EN`, `DSM_RST_B` and `DSM_QOUT_EN` keep their names and reset 0 and are inverted at chip level, so writing 1 turns each off. `dsa1_dig`, dsm2, `decap_vdda` and the floorplan are those of v1.2.0. The new cells cost 6 `DECAPHV32`, VDD has 82.21 pF.

| | |
|---|---|
| `gds/MPC9724.gds.gz` | the delivery GDS, top cell `MPC9724`, md5 in the `.md5` next to it. `scripts/release_ihp.sh` made it from `layout/sg13cmos5l_dsa1_dig_top_logo_fill.gds.gz` (md5 `fb4d07f6471df30a646b7ba8c4a1c9b0`, the signed-off layout) by renaming the top cell only: XOR 0 on all 59 layers, IHP's precheck deck 0 markers in 73 rule categories. `ReleaseNote.md` and `doc/` are the IHP part |
| `netlist/` | the powered Verilog, the extracted SPICE and the CDL of the chip |
| `img/` | renders of the die and the bond plan |
| `packaging/` | the bond plan GDS and its report |

Pinout and the board rules are in [doc/pinout.md](../../doc/pinout.md), the host side and the bring-up order in [doc/host_protocol.md](../../doc/host_protocol.md), the bond report in [packaging/result.md](../../packaging/result.md). Every check, its result and the known items are in the sign-off record, [doc/signoff.md](../../doc/signoff.md), section "dsm2 on by default, 2026-11-04".

Board rules that matter on first power-up: a pull-down on `rst_n`, held low until the supplies are up, VDDA no later than VDD and both before IOVDD, supplies up before `vi` is driven, no DC load on `vcm`, `dsm_clk` pulled low through a resistor and driven through a series resistor, the host lets go of `dsm_clk` before it sets `di_clk_sel` (`BIAS_CFG_0` bit 8), and about 40 decimator words are discarded after dsm2 leaves reset. Program 1 of the bench host stops at its `CHIP_ID` check on this die, program 8 replaces it.
