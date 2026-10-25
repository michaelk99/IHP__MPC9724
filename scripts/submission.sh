#!/bin/bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# The delivery GDS under its IHP project name, and the submission checks on that exact file.
# Run inside IIC-OSIC-TOOLS at the repo root, with the AGENTS.md environment set:
#   scripts/submission.sh <IHP project name>
# The GDS and its md5 go to OUT (release/v.1.1.1/gds), the precheck and the scan to REC
# (verification/submission), the LVS to LVS_OUT (top_lvs.sh's own). A dry run points all three elsewhere.
# The file is renamed, the top cell keeps its design name. A copy keeps every byte, so the md5 must be
# the signed-off one, and the checks then name the top cell, which no longer matches the file name.
set -euo pipefail
: "${PDK:?}" "${PDKPATH:?}" "${EZ130_DIR:?}" "${DECAPHV_DIR:?}"
name=${1:?usage: scripts/submission.sh <IHP project name>}
out=${OUT:-release/v.1.1.1/gds}
rec=${REC:-verification/submission}
src=layout/sg13cmos5l_dsa1_dig_top_logo_fill.gds.gz
top=sg13cmos5l_dsa1_dig_top_logo_fill      # the chip with logo and fill
signed=f61eb35a093f9cad83ac9d3ad3fcbdb6    # doc/signoff.md, v1.1.1
gds=$out/$name.gds.gz

mkdir -p "$out" "$rec"
cp "$src" "$gds"
md5=$(md5sum "$gds" | cut -d' ' -f1)
[ "$md5" = "$signed" ] || { echo "FAIL: $gds has md5 $md5, the signed-off GDS $signed"; exit 1; }
(cd "$out" && md5sum "$name.gds.gz" > "$name.gds.gz.md5")
echo "renamed: $gds, md5 $md5, the signed-off file"

# one top cell, the one the checks below name
tops=$(python3 scripts/scan_gds.py "$gds" | sed -n 's/^cells: [0-9]*, top: \(.*\), dbu.*/\1/p')
[ "$tops" = "$top" ] || { echo "FAIL: top cells '$tops', want only $top"; exit 1; }
python3 scripts/scan_gds.py "$gds" > "$rec/scan.txt"

# IHP's own precheck deck, not the template's minimum level
pre=$rec/precheck
rm -rf "$pre"
python3 "$PDKPATH/libs.tech/klayout/tech/drc/run_drc.py" --path="$gds" --topcell="$top" --run_dir="$pre" \
    --precheck_drc --no_offgrid --no_angle --disable_extra_rules --no_recommended > "$rec/precheck.log" 2>&1 || true
# this deck writes one main log, not the regular run's per-table logs that drc_verdict.py reads
rules=$(cat "$pre"/*.lyrdb | grep -c "<name>" || true)
items=$(cat "$pre"/*.lyrdb | grep -c "<item>" || true)
if grep -q "KLayout DRC Check Passed" "$pre"/drc_run_*.log && grep -q "tables 'main' completed" "$pre"/*_main.log \
        && grep -q "Completed running Density checks" "$pre"/drc_run_*.log && ! grep -q -i exception "$pre"/*.log \
        && [ "$items" = 0 ]; then
    echo "PASS: IHP precheck deck on $gds, top cell $top, $rules rule categories, 0 markers" | tee "$rec/precheck_verdict.txt"
else
    echo "FAIL: IHP precheck deck, $items markers, see $rec/precheck.log" | tee "$rec/precheck_verdict.txt"; exit 1
fi

# the LVS gate on this file, the wrapper with the chip flattened into it next to its fill
LVS_CELL=$top verification/lvs/top_lvs.sh "$gds"
echo "PASS: $gds, precheck and LVS clean, md5 in $gds.md5"
