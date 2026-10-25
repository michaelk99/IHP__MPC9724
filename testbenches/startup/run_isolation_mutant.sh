#!/bin/bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Negative control of the VDD isolation check: the vdd pins of the two do_q pads moved to VDD in a copy of the chip netlist must make it fail.
# Needs the build of a run_startup.sh run for its power_dsa1 data, runs power_dsm on the mutant (about 25 minutes alone) and requires the checker to exit 1 with DIFFERENT in its report.
# Run inside IIC-OSIC-TOOLS at the repo root with the AGENTS.md environment set: testbenches/startup/run_isolation_mutant.sh
set -euo pipefail
good=testbenches/startup/build
M=$good/mut
test -f $good/startup_power_dsa1.txt || { echo "FAIL: no $good/startup_power_dsa1.txt, run run_startup.sh first"; exit 1; }
rm -rf $M
mkdir -p $M/tree/netlist/pnl
python3 - "$M/tree" <<'PY'
import os, re, sys
tree = sys.argv[1]
for f in ("macros/dsa1_dig/final/pnl/dsa1_dig_top.pnl.v", "packaging/result.md", "ip/sg13cmos5l_ip__clamp_vddvss", "ip/sg13cmos5l_ip__cut_vdd"):
    dst = os.path.join(tree, f)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    os.symlink(os.path.relpath(f, os.path.dirname(dst)), dst)       # relative, the container sees another root
n = 0
def move(m):
    global n
    n += 1
    return m.group(0).replace(".vdd(VDDA)", ".vdd(VDD)")
text = re.sub(r"sg13cmos5l_IOPadOut4mA do_q(_b)?_pad \(.*?\);", move, open("netlist/pnl/sg13cmos5l_dsa1_dig_top.pnl.v").read(), flags=re.S)
assert n == 2, f"{n} do_q pads moved"
open(os.path.join(tree, "netlist/pnl/sg13cmos5l_dsa1_dig_top.pnl.v"), "w").write(text)
PY
STARTUP_TREE=$PWD/$M/tree STARTUP_BUILD=$M STARTUP_ORDERS=power_dsm STARTUP_NO_CHECK=1 testbenches/startup/run_startup.sh
if python3 testbenches/startup/startup_check.py $good/startup_power_dsa1.txt $M/startup_power_dsm.txt --orders power_dsa1,power_dsm --out $M/out > $M/check.log; then
    echo "FAIL: the isolation check passed with the do_q pads on VDD"; exit 1
fi
grep -q "DIFFERENT" $M/out/startup_report.md || { echo "FAIL: the checker failed for another reason, see $M/check.log"; exit 1; }
grep "VDD current with dsm2 off" $M/out/startup_report.md
echo "ok: the isolation check fails with the do_q pads on VDD"
