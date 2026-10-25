#!/bin/bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Negative controls: a broken copy of the layout or the CDL per check, each of
# which has to fail. Nothing here touches gds/, lef/ or cdl/.
#
#   bash layout/mutants.sh <scratch dir>
set -u
C=sg13cmos5l_ip__clamp_vddvss
M=${1:-/tmp/${C}_mutants}
cd "$(dirname "$0")/.."
rm -rf "$M" && mkdir -p "$M"
missed=0

gen() {     # a broken layout, from the generator's variant
	mkdir -p "$M/$1"
	(cd layout && klayout -n sg13cmos5l -zz -r clamp_gen.py -rd variant="$1" -rd out="$M/$1/$C.gds") \
		> "$M/$1/gen.log" 2>&1 || { echo "gen $1 failed"; cat "$M/$1/gen.log"; exit 1; }
}

cdl() {     # a broken CDL, from a sed edit that must change something
	mkdir -p "$M/$1"
	sed -e "$2" "cdl/$C.cdl" > "$M/$1/$C.cdl"
	cmp -s "cdl/$C.cdl" "$M/$1/$C.cdl" && { echo "cdl $1: the edit changed nothing"; exit 1; }
}

run() {     # name, pass|fail, target, make arguments
	local name=$1 want=$2 target=$3
	shift 3
	local log="$M/$name/$target.log"
	if make --no-print-directory "$target" OUT="$M/$name/out" "$@" > "$log" 2>&1; then got=pass; else got=fail; fi
	local why
	why=$(grep -m1 -E "^FAIL|FAIL:|Outcome|tb_clamp: FAIL|COUNT: [1-9]" "$log" | sed 's/^.*| Outcome *| //; s/ *|$//')
	if [ "$got" = "$want" ]; then
		echo "ok      $name: make $target: $got, as it should. $why"
	else
		echo "MISSED  $name: make $target: $got, want $want. $log"
		missed=$((missed + 1))
	fi
}

gen m2_spacing
run m2_spacing fail drc GDS="$M/m2_spacing/$C.gds"
run m2_spacing fail magic-drc GDS="$M/m2_spacing/$C.gds"

gen low_activ
run low_activ fail drc-abut GDS="$M/low_activ/$C.gds" ROWS=abut

gen drop_inv_nmos
run drop_inv_nmos fail lvs GDS="$M/drop_inv_nmos/$C.gds"
cdl clamp_1512 's/^Mclamp vdd clamp_g vss vss sg13_hv_nmos w=2268u l=0.6u ng=252/Mclamp vdd clamp_g vss vss sg13_hv_nmos w=1512u l=0.6u ng=168/'
run clamp_1512 fail lvs CDL="$M/clamp_1512/$C.cdl"

for v in vdd_vss_short open_stripe no_island_holes iovss_gap; do
	gen $v
	run $v fail probe GDS="$M/$v/$C.gds"
done
# what LVS makes of the two opens: it passes them, which is why the probe exists
run open_stripe pass lvs GDS="$M/open_stripe/$C.gds"
run iovss_gap pass lvs GDS="$M/iovss_gap/$C.gds"

cdl inv_in_vdd 's/^\(Minv[np] clamp_g\) clamp_rc/\1 vdd/'
run inv_in_vdd fail sim-clamp CDL="$M/inv_in_vdd/$C.cdl"
cdl cap_x10 's/^Mcap vss clamp_rc vss vss sg13_hv_nmos w=126u l=9.5u ng=14/Mcap vss clamp_rc vss vss sg13_hv_nmos w=1260u l=9.5u ng=140/'
run cap_x10 fail sim-clamp CDL="$M/cap_x10/$C.cdl"

echo "mutants: $missed missed"
exit $((missed > 0))
