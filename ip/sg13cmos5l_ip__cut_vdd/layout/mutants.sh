#!/bin/bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Negative controls: a 2 um Metal3 or Metal4 strip left in the vdd band, and an NWell that
# straddles a vdd range edge. The probe has to fail on (b) for each. Nothing here touches gds/ or lef/.
#
#   bash layout/mutants.sh <scratch dir>
set -u
C=sg13cmos5l_ip__cut_vdd
M=${1:-/tmp/${C}_mutants}
cd "$(dirname "$0")/.."
rm -rf "$M" && mkdir -p "$M"
missed=0

for v in m3_strip m4_strip nwell_straddle; do
	(cd layout && klayout -n sg13cmos5l -zz -r cut_gen.py -rd variant=$v -rd out="$M/$v.gds") \
		> "$M/gen_$v.log" 2>&1 || { echo "gen $v failed"; cat "$M/gen_$v.log"; exit 1; }
	if make --no-print-directory probe GDS="$M/$v.gds" > "$M/probe_$v.log" 2>&1; then
		echo "MISSED  $v: make probe passed. $M/probe_$v.log"
		missed=$((missed + 1))
	else
		echo "ok      $v: make probe failed, as it should. $(grep -m1 '^FAIL (b)' "$M/probe_$v.log")"
	fi
done

echo "mutants: $missed missed"
exit $((missed > 0))
