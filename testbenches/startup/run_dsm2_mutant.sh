#!/bin/bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Negative control of the dsm2 checks: dsm2's vdd moved from VDDA to VDD in a copy of the chip netlist must make core_first fail.
# Runs core_first with dsm2's schematic on the mutant (as long as core_first itself) and requires the checker to exit 1 on the VDD current line.
# Run inside IIC-OSIC-TOOLS at the repo root with the AGENTS.md environment set: testbenches/startup/run_dsm2_mutant.sh
set -euo pipefail
M=${STARTUP_MUT:-testbenches/startup/build_dsm2_mut}
rm -rf $M
mkdir -p $M/tree/netlist/pnl
python3 - "$M/tree" <<'PY'
import os, re, sys
tree = sys.argv[1]
for f in ("macros/dsa1_dig/final/pnl/dsa1_dig_top.pnl.v", "packaging/result.md", "ip/sg13cmos5l_ip__clamp_vddvss", "ip/sg13cmos5l_ip__cut_vdd", "ip/dsm2_core/spice"):
    dst = os.path.join(tree, f)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    os.symlink(os.path.relpath(f, os.path.dirname(dst)), dst)       # relative, the container sees another root
text, n = re.subn(r"(dsm2_core dsm2 \(.*?)\.vdd\(VDDA\)", r"\1.vdd(VDD)", open("netlist/pnl/sg13cmos5l_dsa1_dig_top.pnl.v").read(), flags=re.S)
assert n == 1, f"{n} dsm2 vdd pins moved"
open(os.path.join(tree, "netlist/pnl/sg13cmos5l_dsa1_dig_top.pnl.v"), "w").write(text)
PY
STARTUP_TREE=$PWD/$M/tree STARTUP_BUILD=$M STARTUP_ORDERS=core_first STARTUP_DSM2=sch STARTUP_NO_CHECK=1 testbenches/startup/run_startup.sh
grep -q "Vdsm2_vdd VDD dsm2_VDD 0" $M/chip.spice || { echo "FAIL: dsm2 is not on VDD in the mutant's chip.spice"; exit 1; }
if python3 testbenches/startup/startup_check.py $M/startup_core_first.txt --orders core_first --dsm2 sch --out $M/out > $M/check.log; then
    echo "FAIL: the dsm2 checks passed with dsm2's vdd on VDD"; exit 1
fi
grep -E "^- VDD current .*FAIL" $M/out/startup_report.md || { echo "FAIL: the checker failed for another reason, see $M/check.log"; exit 1; }
echo "ok: the dsm2 checks fail with dsm2's vdd on VDD"
