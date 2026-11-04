# sg13cmos5l_dsa1_dig_top v1.2.0

The DSA1 chip for the IHP CMOS5L MPW run of 2026-11-09, 1.3 x 1.3 mm in a QFN24: the digital back end `dsa1_dig` and dsm2, the first-order delta-sigma modulator in its oscillator variant of 2026-11-02, from branch `dsm2/decap-rows` of this repository. The last commit that changes this folder is the release.

It differs from v1.1.1 by the analog modulator on the die, its own VDDA supply segment, `dsa1_dig` re-hardened at 409.08 x 514.08 um, decoupling on both rails (VDD 82.69 pF, VDDA 67.61 pF in `decap_vdda`), and the move to the QFN24.

| | |
|---|---|
| `gds/MPC9724.gds.gz` | the delivery GDS, top cell `MPC9724`, md5 in the `.md5` next to it. `scripts/release_ihp.sh` made it from `layout/sg13cmos5l_dsa1_dig_top_logo_fill.gds.gz` (md5 `872f29b28253c9d28f666a7a5c80b096`, the signed-off layout) by renaming the top cell only: XOR 0 on all 59 layers, IHP's precheck deck 0 markers in 73 rule categories. `ReleaseNote.md` and `doc/` are the IHP part |
| `netlist/` | the powered Verilog, the extracted SPICE and the CDL of the chip |
| `img/` | renders of the die and the bond plan |
| `packaging/` | the bond plan GDS and its report |

Pinout and the board rules are in [doc/pinout.md](../../doc/pinout.md), the host side in [doc/host_protocol.md](../../doc/host_protocol.md), the bond report in [packaging/result.md](../../packaging/result.md). Every check, its result and the known items are in the sign-off record, [doc/signoff.md](../../doc/signoff.md), section "dsm2 oscillator variant integrated, 2026-11-02".

Board rules that matter on first power-up: supplies up before `vi` is driven, no DC load on `vcm`, the host lets go of `dsm_clk` before it sets `di_clk_sel` (`BIAS_CFG_0` bit 8), and the first decimator word after `DSM_RST_B` rises is discarded.
