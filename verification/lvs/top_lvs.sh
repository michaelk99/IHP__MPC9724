#!/bin/bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# GDS-level LVS of the chip with the macro and every standard cell extracted, the tapeout gate.
# Run inside IIC-OSIC-TOOLS at the repo root, with the AGENTS.md environment set:
#   verification/lvs/top_lvs.sh [layout/sg13cmos5l_dsa1_dig_top.gds.gz]
#   verification/lvs/top_lvs.sh --netgen-only        compare the last extraction again
# It reads the unfilled GDS, the delivery GDS minus its fill. fill_isolation.py shows the fill
# touches no drawn shape, so the fill cannot change what this compares.
set -euo pipefail
: "${PDK:?}" "${PDK_ROOT:?}" "${EZ130_DIR:?}" "${DECAPHV_DIR:?}"

export LVS_TOP=sg13cmos5l_dsa1_dig_top
# the layout cell to extract: the delivery GDS has the chip flattened into its logo and fill wrapper
export LVS_CELL=${LVS_CELL:-$LVS_TOP}
export LVS_OUT=${LVS_OUT:-$PWD/verification/lvs/$LVS_TOP.gds.lvs}
export LVS_GDS=$LVS_OUT/$LVS_TOP.gds
if [ "${1:-}" != --netgen-only ]; then
    src=${1:-layout/$LVS_TOP.gds.gz}
    rm -rf "$LVS_OUT"
    mkdir -p "$LVS_OUT"
    gunzip -c "$src" > "$LVS_GDS"
    md5sum "$src" > "$LVS_OUT/input.md5"
    magic -dnull -noconsole -rcfile "$PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc" \
        verification/lvs/top_lvs_extract.tcl > "$LVS_OUT/extract.log" 2>&1
    rm -f "$LVS_GDS"
fi
# Magic writes each transistor and diode as a subcircuit call with positional pins, the CDL as an M
# or D card with named ones, and netgen pads two such classes with proxy pins it cannot pair. The
# copies call them the way Magic does, M and D to X, as OpenBLAU's cdl2spice.py does for M.
cdls=("$EZ130_DIR/cdl/ez130_8t.cdl" "$DECAPHV_DIR/cdl/ez130_8t_decap_hv.cdl")
for c in "${cdls[@]}"; do
    sed -E 's/^([MmDd][^ ]* )/X\1/' "$c" > "$LVS_OUT/$(basename "$c")"
done
# The IO cells' SPICE is the pinned image's PDK, the one the layout's IO cell GDS comes from. The repo's snapshot ip/sg13cmos5l_io_custom has other LevelDown and clamp diode devices.
io=$PDK_ROOT/$PDK/libs.ref/sg13cmos5l_io/spice/sg13cmos5l_io.spice
# the ESD clamp cell, compared device by device: its rppd trigger as Magic writes it, an X call
# with the substrate as third pin
sed -E 's/^([Mm][^ ]* )/X\1/; s/^R([^ ]+) ([^ ]+) ([^ ]+) [^ ]+ \$SUB=([^ ]+) \$\[([a-z]+)\] (.*) b=0$/XR\1 \2 \3 \4 \5 \6/' \
    ip/sg13cmos5l_ip__clamp_vddvss/cdl/sg13cmos5l_ip__clamp_vddvss.cdl > "$LVS_OUT/sg13cmos5l_ip__clamp_vddvss.cdl"
# the VDD cut cell has no device, so it is compared by its pins
cp ip/sg13cmos5l_ip__cut_vdd/cdl/sg13cmos5l_ip__cut_vdd.cdl "$LVS_OUT/"
python3 verification/lvs/verilog_tie_wells.py "${cdls[@]}" macros/dsa1_dig/final/pnl/dsa1_dig_top.pnl.v "$LVS_OUT/dsa1_dig_top.pnl.v"
python3 verification/lvs/verilog_tie_wells.py "${cdls[@]}" netlist/pnl/$LVS_TOP.pnl.v "$LVS_OUT/$LVS_TOP.pnl.v"
# VSS and IOVSS both tap the one substrate, which Magic extracts as one node, so the reference joins
# them too. A metal short between them is then invisible here, and LibreLane's LVS, which keeps them
# apart, covers it.
sed -i -E '/^\s*IOVSS,\s*$/d; /^\s*inout IOVSS;\s*$/d; s/\(IOVSS\)/(VSS)/g' "$LVS_OUT/$LVS_TOP.pnl.v"
# The same substrate holds the IO cells' core ground, vss, which Magic never makes a port of theirs, so the reference drops that pin from the IO cells and their instances.
# Not from Filler200 when the extraction gives it that pin, nor from the clamp cell, whose vss is its devices' own, nor from the cut cell, whose vss pin is its own label.
f200=sg13cmos5l_Filler200
grep -q '^\.subckt sg13cmos5l_Filler200 .*\bvss\b' "$LVS_OUT/$LVS_TOP.spice" || f200=none
python3 verification/lvs/verilog_drop_pin.py "^sg13cmos5l_(?!$f200\$|ip__clamp_vddvss\$|ip__cut_vdd\$)" vss "$LVS_OUT/$LVS_TOP.pnl.v" "$LVS_OUT/$LVS_TOP.pnl.v"
awk -v keep="$f200" 'tolower($1) == ".subckt" && $2 != keep { l = $1 " " $2; for (i = 3; i <= NF; i++) if ($i != "vss") l = l " " $i; print l; next } 1' \
    "$io" > "$LVS_OUT/sg13cmos5l_io.spi"
# The PDK's IO cells, the bondpad and the logos as black boxes, compared by their pins as LibreLane's LVS does: Magic extracts the IO cells from the GDS whatever LEFview says, and their clamps then disagree with the IO SPICE, the trigger resistor shorted for a missing PolyRes marker, which is the PDK's, not this design's. Every cell the IO SPICE defines is emptied.
awk -v names="$(awk 'tolower($1) == ".subckt" {print $2}' "$io" | tr '\n' ' ')" '
    BEGIN { n = split(names, a, " "); for (i = 1; i <= n; i++) box[a[i]] = 1 }
    tolower($1) == ".subckt" && ($2 in box || ($2 ~ /^sg13cmos5l_ip__/ && $2 != "sg13cmos5l_ip__clamp_vddvss")) { print; skip = 1; next }
    tolower($1) == ".ends" && skip { print; skip = 0; next }
    !skip' "$LVS_OUT/$LVS_TOP.spice" > "$LVS_OUT/$LVS_TOP.boxed.spice"
# negative controls: LVS_MUTANT=<name> verification/lvs/top_lvs.sh --netgen-only edits the reference, see top_lvs_mutants.sh
case "${LVS_MUTANT:-}" in
    "") ;;
    vdda_to_vdd) python3 verification/lvs/mutate_reference.py vdda_to_vdd "$LVS_OUT/$LVS_TOP.pnl.v" ;;
    and3bx1_swap) python3 verification/lvs/mutate_reference.py and3bx1_swap "$LVS_OUT/dsa1_dig_top.pnl.v" ;;
    cut_pin|dsm2_pins) python3 verification/lvs/mutate_reference.py "$LVS_MUTANT" "$LVS_OUT/$LVS_TOP.pnl.v" ;;
    *) echo "unknown LVS_MUTANT ${LVS_MUTANT}"; exit 2 ;;
esac
netgen -batch source verification/lvs/top_lvs.tcl > "$LVS_OUT/netgen.log" 2>&1

grep -q '^Final result: Circuits match uniquely\.$' "$LVS_OUT/lvs.rpt" || {
    echo "FAIL: top LVS, see $LVS_OUT/lvs.rpt"; tail -5 "$LVS_OUT/lvs.rpt"; exit 1; }
# a device of the wrong size is a property error inside its cell, while the final line still matches
if grep -q 'property errors' "$LVS_OUT/lvs.rpt"; then
    echo "FAIL: top LVS property errors, see $LVS_OUT/lvs.rpt"; grep -A2 'property errors' "$LVS_OUT/lvs.rpt" | head; exit 1
fi
echo "PASS: top LVS from the GDS, the macro and every standard cell device by device"
