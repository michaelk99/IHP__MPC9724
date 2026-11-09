# Schematic Netlists

Schematic netlists of `sg13cmos5l_dsa1_dig_top` for LVS, exported from Xschem.

They are written by `make klayout-lvs-netlist` (CDL, `sg13cmos5l_dsa1_dig_top_klayout.cdl`) and by `make magic-lvs-netlist` (SPICE, `sg13cmos5l_dsa1_dig_top_magic.spice`). Both targets also run as the first step of `make klayout-lvs` and `make magic-lvs`.

No netlist is kept here. The Xschem top is a drawing and not the chip's LVS reference. That reference is built by `verification/lvs/top_lvs.sh` from the powered netlists and the cell CDLs, see `verification/lvs/README.md` and `release/v.1.2.1/netlist/lvs_reference/`. An old CDL of the digital-only chip was removed from here on 2026-11-07, since `make release` copies this folder into the release.
