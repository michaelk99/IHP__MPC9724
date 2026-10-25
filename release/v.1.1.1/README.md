# sg13cmos5l_dsa1_dig_top v1.1.1

The digital-only DSA1 back end on SG13CMOS5L, the fallback tapeout, from branch `tapeout/v1.1.1` of this repository. The last commit that changes this folder is the release.

It differs from v1.1.0 by one layout change: a vdd-to-vss ESD clamp cell between the VSS and the VDD pad, which takes the core rail from 8.4 to 3.6 V in a 2 kV HBM zap ([doc/esd_hbm.md](../../doc/esd_hbm.md)). The macro is the same.

| | |
|---|---|
| `gds/sg13cmos5l_dsa1_dig_top_logo_fill.gds.gz` | the delivery GDS, top cell `sg13cmos5l_dsa1_dig_top_logo_fill`, md5 in the `.md5` next to it. It keeps the design name until IHP assigns the project name, then `scripts/submission.sh <name>` copies it to that name next to it, with its md5, and runs IHP's precheck deck and the LVS on that file |
| `netlist/` | the powered Verilog, the extracted SPICE and the CDL of the chip |
| `img/` | renders of the die and the bond plan in the QFN32 |
| `packaging/` | the bond plan GDS and its report, VSS and IOVSS bonded through the cavity |

Die 1.6 x 1.6 mm, 32 pads, all bonded, pinout in [doc/pinout.md](../../doc/pinout.md), bond report in [packaging/result.md](../../packaging/result.md). Every check, its result and the known items are in the sign-off record, [doc/signoff.md](../../doc/signoff.md).

The board must bring VDD (1.2 V) up no later than IOVDD (3.3 V), and hold `rst_n` low until both are up: until then the 16 test outputs, TEST_CTRL_0, are undefined, and its bits 7:6 high together short the analog die's bias nodes.

VSS and IOVSS are bonded through the package cavity, so the exposed pad is ground and the board ties it there. Pins 19 and 20, the bidir spares, are never driven and their input buffers float with them, so the board ties them to ground. Pins 17 and 18, the analog spares, connect straight to their pads.
