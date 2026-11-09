#!/bin/bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Read-only check of the delivery GDS release/v.1.2.1/gds/MPC9724.gds.gz: md5, one top cell, IHP precheck, top LVS.
# It never writes into release/. Results go to the dry-run directory (default runs/submission_check).
# Run inside IIC-OSIC-TOOLS at the repo root with the environment of doc/running.md set:
#   scripts/submission.sh [dry-run dir]
set -euo pipefail
: "${PDK:?}" "${PDKPATH:?}" "${EZ130_DIR:?}" "${DECAPHV_DIR:?}"
gds=release/v.1.2.1/gds/MPC9724.gds.gz
top=MPC9724
signed=7cf6da0e6ea7b6c2c473bff6e6093cd7    # doc/signoff.md, v1.2.1
rec=$(realpath -m "${1:-runs/submission_check}")
mkdir -p "$rec"

md5=$(md5sum "$gds" | cut -d' ' -f1)
[ "$md5" = "$signed" ] || { echo "FAIL: $gds has md5 $md5, the delivered file $signed"; exit 1; }
echo "md5 $md5, the delivered file"

# one top cell, scan.txt first so a failing scan leaves its output and a FAIL line
python3 scripts/scan_gds.py "$gds" > "$rec/scan.txt" || { echo "FAIL: scan_gds.py on $gds, see $rec/scan.txt"; exit 1; }
tops=$(sed -n 's/^cells: [0-9]*, top: \(.*\), dbu.*/\1/p' "$rec/scan.txt")
[ "$tops" = "$top" ] || { echo "FAIL: top cells '$tops', want only $top"; exit 1; }

# IHP's own precheck deck
pre=$rec/precheck
rm -rf "$pre"
python3 "$PDKPATH/libs.tech/klayout/tech/drc/run_drc.py" --path="$gds" --topcell="$top" --run_dir="$pre" \
    --precheck_drc --no_offgrid --no_angle --disable_extra_rules --no_recommended > "$rec/precheck.log" 2>&1 || true
# this deck writes one main log, not the regular run's per-table logs that drc_verdict.py reads
rules=$(cat "$pre"/*.lyrdb | grep -c "<category>" || true)    # <name> also counts the cell
items=$(cat "$pre"/*.lyrdb | grep -c "<item>" || true)
if grep -q "KLayout DRC Check Passed" "$pre"/drc_run_*.log && grep -q "tables 'main' completed" "$pre"/*_main.log \
        && grep -q "Completed running Density checks" "$pre"/drc_run_*.log && ! grep -q -i exception "$pre"/*.log \
        && [ "$items" = 0 ]; then
    echo "PASS: IHP precheck deck on $gds, top cell $top, $rules rule categories, 0 markers" | tee "$rec/precheck_verdict.txt"
else
    echo "FAIL: IHP precheck deck, $items markers, see $rec/precheck.log" | tee "$rec/precheck_verdict.txt"; exit 1
fi

# top LVS on this file. The reference keeps the design top name, the script maps it to the layout cell MPC9724.
LVS_CELL=$top LVS_OUT=$rec/lvs verification/lvs/top_lvs.sh "$gds"
echo "PASS: $gds, md5, precheck and LVS clean, results in $rec"
