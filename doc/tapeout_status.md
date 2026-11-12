# MPC9724 tapeout status, 2026-11-12

Status of the delivered chip v1.2.1 (`release/v.1.2.1/gds/MPC9724.gds.gz`, md5 `7cf6da0e6ea7b6c2c473bff6e6093cd7`, frozen) after a check of every Magic DRC verdict for the flatten-flag defect. The full sign-off record is [signoff.md](signoff.md), the evidence of this check is in `verification/drc/magic_recheck_2026-11-12/`.

## Verdict

No finding needs a GDS change on our side, unless IHP's own DRC rejects the two `M1.e` items below. Every Magic DRC count in the sign-off of v1.2.1 is a real one, the flatten flag affected none of them. It voided only side claims, rechecked below. One rule, `M1.e`, is violated twice in dsm2's OTA, both times between two shapes of the same net, so a bridge there would be harmless (Finding 1).

## The flatten-flag defect

`sak-drc.sh -m -f "*"` writes `gds flatglob *` before Magic reads the GDS. Magic then flattens every cell whose name matches, the top cell included, into the cells that instantiate it. Nothing instantiates the top cell, so Magic checks an empty cell and reports `COUNT: 0` on any layout. Any pattern that matches the top cell's name does this, a pattern that matches only subcells is safe. IIC-OSIC-TOOLS PR #402 makes `sak-drc.sh` refuse such a pattern.

## Every Magic DRC verdict of v1.2.1

| layout | how Magic ran | result | flag |
|---|---|---|---|
| chip, unfilled and filled (source of the delivery GDS) | `make magic-drc`, `sak-drc.sh -d -m`, 2026-11-04 | 5353 and 5588 items. The Tcl script has no `flatglob`, the log flattens no cell | not used |
| `dsa1_dig` macro | LibreLane's Magic DRC, `MAGIC_GDS_FLATGLOB` unset in the macro config | 0. The chip-level run also finds no item in `dsa1_dig` | not used |
| `dsm2_core` as delivered (md5 `00624787128efe33ca6ddf5273170e56`) | its designer's `magic-drc` target, without the flag since the macro was created on 2026-10-14 | 2 `M1.e` in the OTA and 12 `CntB.h1` in IHP's `sg13cmos5l_SecondaryProtection`, the latter waived by the designer (`ip/dsm2_core/doc/dsm2_README.md`). The designer's standalone rerun of 2026-11-12 on a newer image: 2 `M1.e` without the flag, 0 with it, no `CntB.h1` (not traced), KLayout at `macro` level clean | not used |
| `ota_fcasc2_top` inside dsm2, its own README | the block's Makefile passed the flag | "Magic DRC is clean" rested on the flag. Corrected in the designer's tree on 2026-11-12. This repo's delivered copy, `ip/dsm2_core/doc/ota_fcasc2_README.md`, keeps the old sentence until the next dsm2 delivery | used, claim void |
| `sg13cmos5l_ip__clamp_vddvss`, `sg13cmos5l_ip__cut_vdd` | `sak-drc.sh -d -m` | clean | not used |
| `sg13cmos5l_ip__helm`, `__jku`, `__jku_names`, `__title`, `__bondpad_70x70` | their Makefiles still pass `-f "*"` | rerun without the flag on 2026-11-12: 0 each, the Tcl scripts have no `flatglob` and the logs flatten no cell | used, now rechecked |
| v1.1.0 layout | the old chip Makefile with `gds flatglob *` | `COUNT: 0` meant nothing, already recorded in [signoff.md](signoff.md), "Known and accepted" | used, void |

## Finding 1: two M1.e items in dsm2's OTA, both same-net

- **Where.** `dsm2_core/sc_int2/ota_fcasc2_top`, both 58.7 um long, chip x 810.04 to 868.75 um.
- **What.** Two 0.32 um wide Metal1 straps of `ota_fcasc2_top`, each 0.18 um from a 0.16 um line of a bias block. Upper pair: strap y 529.995 to 530.315 um, `ota_fcasc2_pbiascasc_blk` line from 530.495 um. Lower pair: strap y 528.975 to 529.295 um, `ota_fcasc2_nbiascasc_blk` line up to 528.795 um. `M1.e` asks 0.22 um when one line is wider than 0.30 um and the parallel run exceeds 1.0 um. Measured with KLayout on the delivery GDS (`probe.py`, `probe.txt`).
- **Nets.** Traced through metal and vias in the delivered `dsm2_core.gds` (`trace.py`, `trace.txt`): the lower strap and its line are both `vss`, the upper strap and its line are both `vdd`, at x 5, 30 and 60 um of the OTA.
- **Risk.** The gap is at the plain Metal1 minimum, 0.18 um (`M1.b`), and 0.04 um under the wide-line rule. A bridge would join two shapes of one supply net and change nothing in the circuit.
- **Why the IHP checks pass.** The precheck deck has no `M1.e`. The regular deck runs it and reports nothing here, its shielded separation misses these pairs (IHP-GmbH/IHP-Open-PDK#1222). Magic flags them.
- **Record.** [signoff.md](signoff.md) accepted the Magic totals 5353 and 5588 in the audit table with a reason ("library cells, the seal ring and the macro") that did not cover the items inside dsm2. That row now names them.

## Other open items

- **Five IP Makefiles** (`helm`, `jku`, `jku_names`, `title`, `bondpad_70x70`) still pass `-f "*"`. Drop the flag so a later run checks the cell.
- **Power at typical.** The taped macro's `power_vcd_nom_typ_1p20V_25C.rpt` gives 2.979 uW, [specifications.md](specifications.md) and the root README give 3.075 uW from the 9031d16 harden. Text only.
- **[signoff.md](signoff.md).** "for longer than 1 ns" in the v1.1.1 checks reads as a limit but is a measured duration, and `sim-gl` 1343 is tied to 9031d16 although it is from the 2026-10-31 harden. Text only.
- **TRL 4** stays open on the modulator-level mismatch Monte Carlo ([TRL-Mixed-Signal-IP.md](TRL-Mixed-Signal-IP.md)).
