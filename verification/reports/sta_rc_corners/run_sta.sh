#!/bin/bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# STA of the chip and of the dsa1_dig macro at three PVT corners and min, nom, max RC.
# Runs inside the pinned image, repo mounted at /foss/designs/sg13cmos5l_dsa1_dig, scratch at $WORK (default /work).
#   run_sta.sh <chip|macro> <corner|all> <min|nom|max|r08c12|r12c08|all>
# min and max are the nominal SPEF with R and C scaled by 0.8 and 1.2, the PDK has no min or max RCX rules.
# r08c12 and r12c08 scale R and C apart. all is min, nom, max.
set -euo pipefail
R=/foss/designs/sg13cmos5l_dsa1_dig
H=$R/verification/reports/sta_rc_corners
CR=$R/flow/librelane/runs/RUN_2026-11-04_15-49-13
MF=$R/macros/dsa1_dig/final    # the taped-out macro views, also what the chip reads
target=$1 corners=$2 rcs=$3
[ "$corners" = all ] && corners="nom_fast_1p32V_m40C nom_slow_1p08V_125C nom_typ_1p20V_25C"
[ "$rcs" = all ] && rcs="min nom max"
declare -A tag=([nom_fast_1p32V_m40C]=ff_1p32v_m40c [nom_slow_1p08V_125C]=ss_1p08v_125c [nom_typ_1p20V_25C]=tt_1p20v_25c)
declare -A iolib=([nom_fast_1p32V_m40C]=sg13cmos5l_io_fast_1p32V_3p6V_m40C [nom_slow_1p08V_125C]=sg13cmos5l_io_slow_1p08V_3p0V_125C [nom_typ_1p20V_25C]=sg13cmos5l_io_typ_1p2V_3p3V_25C)
export CLOCK_TRANSITION_CONSTRAINT=0.15 MAX_FANOUT_CONSTRAINT=10 OUTPUT_CAP_LOAD=6.0 IO_DELAY_CONSTRAINT=20.0
for c in $corners; do
  t=${tag[$c]}
  for rc in $rcs; do
    case $rc in min) rf=0.8 cf=0.8;; nom) rf=1 cf=1;; max) rf=1.2 cf=1.2;; r08c12) rf=0.8 cf=1.2;; r12c08) rf=1.2 cf=0.8;; esac
    out=${WORK:-/work}/$target/$c/$rc; mkdir -p "$out"; export OUT=$out CORNER=$c
    sp() { python3 $H/scale_spef.py "$1" "$2" $rf $cf; }
    if [ $target = chip ]; then
      sp $CR/53-openroad-rcx/nom/sg13cmos5l_dsa1_dig_top.nom.spef $out/top.spef
      sp $MF/spef/nom/dsa1_dig_top.nom.spef $out/macro.spef
      export DESIGN_NAME=sg13cmos5l_dsa1_dig_top SDC=$R/flow/librelane/sg13cmos5l_dsa1_dig_top.sdc
      export MACRO_NLS=$MF/nl/dsa1_dig_top.nl.v TOP_NL=$CR/51-openroad-fillinsertion/sg13cmos5l_dsa1_dig_top.nl.v
      export SPEF=$out/top.spef MACRO_SPEF=$out/macro.spef MACRO_INST=i_sg13cmos5l_dsa1_dig_core.dsa1_dig
      export LIBS="$R/ip/ez130_8t_v1p1/lib/ez130_8t_$t.lib $R/flow/librelane/runs/.decaphv_lib/ez130_8t_decap_hv_$t.lib $R/ip/sg13cmos5l_io_custom/lib/${iolib[$c]}.lib $R/ip/sg13cmos5l_ip__clamp_vddvss/lib/sg13cmos5l_ip__clamp_vddvss.lib $R/ip/sg13cmos5l_ip__cut_vdd/lib/sg13cmos5l_ip__cut_vdd.lib $R/macros/decap_vdda/final/lib/$c/decap_vdda__$c.lib $R/ip/sg13cmos5l_ip__jku/final/lib/sg13cmos5l_ip__jku.lib $R/ip/sg13cmos5l_ip__jku_names/final/lib/sg13cmos5l_ip__jku_names.lib $R/ip/sg13cmos5l_ip__helm/final/lib/sg13cmos5l_ip__helm.lib $R/ip/sg13cmos5l_ip__title/final/lib/sg13cmos5l_ip__title.lib"
    else
      sp $MF/spef/nom/dsa1_dig_top.nom.spef $out/top.spef
      export DESIGN_NAME=dsa1_dig_top SDC=$R/macros/dsa1_dig/flow/librelane/dsa1_dig_top.sdc MACRO_NLS="" TOP_NL=$MF/nl/dsa1_dig_top.nl.v
      export SPEF=$out/top.spef MACRO_SPEF="" MACRO_INST=""
      export LIBS="$R/ip/ez130_8t_v1p1/lib/ez130_8t_$t.lib $R/macros/dsa1_dig/flow/librelane/runs/.decaphv_lib/ez130_8t_decap_hv_$t.lib"
    fi
    echo "== $target $c $rc"
    sta -no_splash -exit ${TCL:-$H/sta_corner.tcl} > $out/sta.log 2>&1 || echo "sta exit $?"
    rm -f $out/*.spef
    cat $out/summary.txt | tr '\n' ' '; echo
  done
done
