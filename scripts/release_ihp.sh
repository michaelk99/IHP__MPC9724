#!/bin/bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# The IHP Open-Silicon-MPW part of a release: gds/, doc/ and ReleaseNote.md in OUT, next to what `make release` copied.
# Run inside IIC-OSIC-TOOLS at the repo root, with the AGENTS.md environment set:
#   OUT=release/v.1.2.0 scripts/release_ihp.sh
#   scripts/release_ihp.sh --self-test
# The internal flow keeps its cell name, only the copy in OUT/gds is renamed to NAME.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
name=${NAME:-MPC9724}
src=${SRC:-layout/sg13cmos5l_dsa1_dig_top_logo_fill.gds.gz}
top=sg13cmos5l_dsa1_dig_top

# the top must be defined once per netlist and only under the project name
check_netlists() {
    local f n defs=0 ok=0
    while IFS= read -r f; do
        n=$(grep -c -i -E "^[[:space:]]*(\.subckt|module)[[:space:]]+$top([[:space:]]|\(|$)" "$f" || true)
        [ "$n" = 0 ] || { echo "FAIL: $f still defines $top"; ok=1; }
        n=$(grep -c -i -E "^[[:space:]]*(\.subckt|module)[[:space:]]+$name([[:space:]]|\(|$)" "$f" || true)
        [ "$n" -le 1 ] || { echo "FAIL: $f defines $name $n times"; ok=1; }
        defs=$((defs + n))
    done < <(find "$1" -type f \( -name '*.v' -o -name '*.spice' -o -name '*.cdl' -o -name '*.sp' \))
    [ "$defs" -ge 1 ] || { echo "FAIL: no netlist under $1 defines $name"; ok=1; }
    return $ok
}

# a flat boundary must fail the check, and a clean layout must pass it
if [ "${1:-}" = "--self-test" ]; then
    t=$(mktemp -d)
    trap 'rm -rf "$t"' EXIT
    python3 - "$t" <<'PY'
import sys, pya
ly = pya.Layout(); ly.dbu = 0.001
top = ly.create_cell("tiny_top")
top.shapes(ly.layer(8, 0)).insert(pya.Polygon(pya.Box(0, 0, 1000, 1000)))
top.shapes(ly.layer(189, 0)).insert(pya.Polygon(pya.Box(0, 0, 5000, 5000)))
ly.write(sys.argv[1] + "/clean.gds")
d = open(sys.argv[1] + "/clean.gds", "rb").read()
# 1000 dbu is the only coordinate 1000, zeroing it flattens the square
m = d.replace((1000).to_bytes(4, "big"), bytes(4))
assert m != d
open(sys.argv[1] + "/flat.gds", "wb").write(m)
PY
    for f in clean flat; do
        klayout -b -r "$here/ihp_gds.py" -rd gds_in="$t/$f.gds" -rd gds_out="$t/$f.ihp.gds" -rd new="$name" > /dev/null
    done
    python3 "$here/scan_gds.py" "$t/clean.ihp.gds" > /dev/null || { echo "FAIL: the clean layout fails the zero-area check"; exit 1; }
    if python3 "$here/scan_gds.py" "$t/flat.ihp.gds" > "$t/flat.txt"; then
        echo "FAIL: the zero-area check passes a layout with a flat polygon"; exit 1
    fi
    grep FAIL "$t/flat.txt" | head -2
    mkdir -p "$t/nl"
    printf '.subckt %s a b\n.ends %s\n' "$name" "$name" > "$t/nl/ok.cdl"
    check_netlists "$t/nl" > /dev/null || { echo "FAIL: a netlist with one top is refused"; exit 1; }
    printf '.subckt %s a b\n.ends\n' "$top" > "$t/nl/old.cdl"
    ! check_netlists "$t/nl" > /dev/null || { echo "FAIL: a netlist still defining $top passes"; exit 1; }
    printf 'module %s (a);\nendmodule\nmodule %s (a);\nendmodule\n' "$name" "$name" > "$t/nl/old.cdl"
    ! check_netlists "$t/nl" > /dev/null || { echo "FAIL: a netlist defining $name twice passes"; exit 1; }
    echo "PASS: self-test, the flat polygon is caught after the IHP save, the netlist check refuses the old top and a double definition"
    exit 0
fi

: "${OUT:?usage: OUT=release/v.<version> scripts/release_ihp.sh}"
version=$(basename "$OUT")
gds=$OUT/gds/$name.gds.gz
mkdir -p "$OUT/gds" "$OUT/doc"
cd "$(dirname "$here")"

# the checks on the written file, not on the source: zero-area polygons, degenerate paths, one top cell
klayout -b -r scripts/ihp_gds.py -rd gds_in="$src" -rd gds_out="$gds" -rd new="$name"
python3 scripts/scan_gds.py "$gds" > "$OUT/doc/$name.scan.txt" || { cat "$OUT/doc/$name.scan.txt"; rm -f "$gds"; echo "FAIL: zero-area check on $gds, file removed"; exit 1; }
tops=$(sed -n 's/^cells: [0-9]*, top: \(.*\), dbu.*/\1/p' "$OUT/doc/$name.scan.txt")
[ "$tops" = "$name" ] || { rm -f "$gds"; echo "FAIL: top cells '$tops', want only $name, file removed"; exit 1; }
echo "PASS: zero-area check on $gds, top cell $tops, 0 degenerate shapes"

# every view names the project: rename the top's definition and the files, subcells stay
for f in $(find "$OUT/netlist" -type f \( -name '*.v' -o -name '*.spice' -o -name '*.cdl' -o -name '*.sp' \)); do
    sed -i -E "s/^([[:space:]]*(\.subckt|\.ends|module)[[:space:]]+)$top([[:space:]]|\(|$)/\1$name\3/I" "$f"
    case $(basename "$f") in "$top"*) mv "$f" "$(dirname "$f")/$name${f##*/$top}" ;; esac
done
check_netlists "$OUT/netlist" || { rm -f "$gds"; exit 1; }
echo "PASS: release netlists define $name once and no $top"

cp doc/TRL-Mixed-Signal-IP.md doc/specifications.md doc/pinout.md doc/signoff.md "$OUT/doc/"
md5=$(md5sum "$gds" | cut -d' ' -f1)
srcmd5=$(md5sum "$src" | cut -d' ' -f1)
srccell=$(python3 scripts/scan_gds.py "$src" | sed -n 's/^cells: [0-9]*, top: \(.*\), dbu.*/\1/p')
if grep -q "$srcmd5" doc/signoff.md; then signoff="The source layout is the one recorded in doc/signoff.md (md5 $srcmd5)."
else signoff="The source layout (md5 $srcmd5) is not recorded as signed off in doc/signoff.md."; fi
sed -e "s/@NAME@/$name/g" -e "s/@VERSION@/$version/g" -e "s/@MD5@/$md5/g" -e "s/@SRCCELL@/$srccell/g" -e "s|@SIGNOFF@|$signoff|" scripts/release_note.template.md > "$OUT/ReleaseNote.md"
echo "$gds md5 $md5"
