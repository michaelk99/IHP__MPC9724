#!/bin/bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Negative controls of top_lvs.sh: each edit of the reference must give netgen's mismatch verdict, then the clean compare runs again so the tracked report is the passing one.
# A mutant counts as detected only when top_lvs.sh exits 1 and a fresh lvs.rpt has netgen's "Netlists do not match." and a failing final result. A crash or a stale report fails.
# The final result can be "Top level cell failed pin matching." when netgen's symmetry breaking after the mismatch also swaps two top pins, as dsm2_pins does since v1.2.1.
# Needs the extraction of a clean top_lvs.sh run. Run inside IIC-OSIC-TOOLS at the repo root with the AGENTS.md environment set: verification/lvs/top_lvs_mutants.sh
set -uo pipefail
out=verification/lvs/sg13cmos5l_dsa1_dig_top.gds.lvs
ok=0
for m in vdda_to_vdd and3bx1_swap cut_pin dsm2_pins dsm2_device decap_vdd; do
    rm -f $out/lvs.rpt
    LVS_MUTANT=$m verification/lvs/top_lvs.sh --netgen-only > $out/mutant_$m.log 2>&1
    rc=$?
    if [ $rc = 1 ] && [ -f $out/lvs.rpt ] && grep -q '^Netlists do not match\.$' $out/lvs.rpt \
            && grep -qE '^Final result: (Netlists do not match|Top level cell failed pin matching)\.$' $out/lvs.rpt; then
        echo "ok: mutant $m detected: $(grep -m1 '^Final result' $out/lvs.rpt)"
    else
        echo "FAIL: mutant $m not detected, exit $rc, see $out/mutant_$m.log"; tail -3 $out/mutant_$m.log; ok=1
    fi
done
rm -f $out/lvs.rpt
verification/lvs/top_lvs.sh --netgen-only || ok=1
exit $ok
