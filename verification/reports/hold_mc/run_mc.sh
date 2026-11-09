#!/bin/bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Hold MC of the worst hold path, one ngspice process per seed. Runs inside the pinned image.
#   run_mc.sh <workdir> <corner> <temp> <vdd> <first_seed> <n> <jobs>
# Appends one RESULT line per seed to <workdir>/results_<corner>_<temp>.txt.
set -euo pipefail
# The image's .spiceinit loads the OSDI models from $PDK.
[ "${PDK:-}" = ihp-sg13cmos5l ] || { echo "run_mc.sh: PDK must be ihp-sg13cmos5l" >&2; exit 1; }
here=$(cd "$(dirname "$0")" && pwd)
w=$(cd "$1" && pwd) corner=$2 temp=$3 vdd=$4 s0=$5 n=$6 jobs=$7
[ -f "$w/path.spice" ] || python3 "$here/gen_bench.py" "$w/path.spice"
tag=${corner}_${temp}
sed "s|@CORNER@|$corner|; s|@TEMP@|$temp|; s|@VDD@|$vdd|; s|@PATH@|$w/path.spice|" "$here/bench.cir" > "$w/bench_$tag.cir"
read -r vh vlo vhi < <(python3 -c "v=$vdd; print(v/2, v*0.2, v*0.8)")
export w tag vdd vh vlo vhi here
one() {
    sp=$w/run_${tag}_$1.sp log=$w/run_${tag}_$1.log
    sed "s|@SEED@|$1|g; s|@BENCH@|$w/bench_$tag.cir|; s|@VH@|$vh|g; s|@VLO@|$vlo|g; s|@VHI@|$vhi|g; s|@VDD@|$vdd|g" "$here/hold.ctl" > "$sp"
    ngspice -b "$sp" > "$log" 2>&1 || true
    # A full result has 12 fields, else the log stays for a look.
    if grep "^RESULT $1 " "$log" | awk 'NF == 12 {f = 1} END {exit !f}'; then
        grep "^RESULT $1 " "$log" >> "$w/results_$tag.txt"; rm -f "$sp" "$log"
    fi
}
export -f one
seq "$s0" $((s0 + n - 1)) | xargs -P "$jobs" -I{} bash -c 'one {}'
