#!/bin/bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# The supply start-up bench in both supply orders, the ground bounce case and the two power cases, then the checks.
# Run inside IIC-OSIC-TOOLS at the repo root with the AGENTS.md environment set: testbenches/startup/run_startup.sh
# STARTUP_ORDERS, STARTUP_BUILD, STARTUP_TREE and STARTUP_NO_CHECK are for run_power_v111.sh, which writes the power_v111.json the report compares when present.
set -euo pipefail
: "${PDK:?}" "${PDK_ROOT:?}" "${EZ130_DIR:?}"
B=${STARTUP_BUILD:-testbenches/startup/build}
TREE_ARGS=${STARTUP_TREE:+--tree $STARTUP_TREE}
RUN_ORDERS=${STARTUP_ORDERS:-io_first,core_first,bounce,power_dsa1,power_dsm}

python3 testbenches/startup/gen_startup.py --out $B --orders $RUN_ORDERS $TREE_ARGS
python3 macros/counter/scripts/spi2xspice.py $B/cells.lib -io_time=500p -time=50p -idelay=5p -odelay=50p \
    -cload=250f $B/core.spice $B/core.xspice > $B/spi2xspice.log 2>&1
# CGX3 is the one cell spi2xspice.py cannot model, --patch-xspice adds it
if grep "No output for" $B/spi2xspice.log | grep -v -w CGX3; then
    echo "FAIL: spi2xspice.py could not model the cells above"; exit 1
fi
python3 testbenches/startup/gen_startup.py --out $B --patch-xspice
cp "$PDK_ROOT/$PDK/libs.tech/ngspice/.spiceinit" $B/
sed -E 's/\btt *= *[0-9.Ee+-]+/tt=0/g' "$PDK_ROOT/$PDK/libs.tech/ngspice/models/diodes.lib" > $B/diodes_bench.lib

# Solver settings, tried in order until one runs through: 1 fF on every node, then a looser reltol,
# then 1 TOhm from every node to ground too, then the trapezoidal method, which passed the outputs'
# common flip at VDD 0.78 V with IOVDD first once the clamp cell was in. A larger shunt did worse.
RECIPES=("method=gear cshunt=1e-15" "method=gear cshunt=1e-15 reltol=3e-3"
         "method=gear cshunt=1e-15 reltol=3e-3 rshunt=1e12" "method=trap cshunt=1e-15")
# ngspice's simulated time, from the progress it prints
sim_time() { tail -c 200 "$1" 2>/dev/null | grep -o -E '[0-9.]+e-[0-9]+' | tail -1 || true; }
run_order() {
    local k=0
    for r in "${RECIPES[@]}"; do
        k=$((k + 1))
        sed -e "s/method=gear cshunt=@CSHUNT@/$r/" $B/tb_$1.in > $B/tb_$1.spice
        (cd $B && exec ngspice -b tb_$1.spice > ngspice_$1_$k.log 2>&1) & local pid=$!
        # a solver can also creep without aborting: no progress for 15 minutes ends the attempt
        local last="" still=0
        while kill -0 $pid 2>/dev/null; do
            sleep 60
            local now; now=$(sim_time $B/ngspice_$1_$k.log)
            if [ -n "$now" ] && [ "$now" = "$last" ]; then still=$((still + 1)); else still=0; fi
            last=$now
            if [ $still -ge 15 ]; then kill $pid; echo "stalled at $now s" >> $B/ngspice_$1_$k.log; fi
        done
        wait $pid || true
        cp $B/ngspice_$1_$k.log $B/ngspice_$1.log
        if grep -q "ngspice-[0-9]* done" $B/ngspice_$1.log && ! grep -q -E "Timestep too small|stalled at" $B/ngspice_$1.log; then
            echo "$r" > $B/solver_$1.txt
            return 0
        fi
    done
    echo "FAIL: $1 stalls with every recipe, see $B/ngspice_$1_*.log"; return 1
}
pids=()
for o in ${RUN_ORDERS//,/ }; do
    run_order $o & pids+=($!)
done
ok=0
for p in "${pids[@]}"; do wait $p || ok=1; done
[ $ok = 0 ] || exit 1
[ -z "${STARTUP_NO_CHECK:-}" ] || exit 0
files=(); for o in ${RUN_ORDERS//,/ }; do files+=($B/startup_$o.txt); done
v111=(); [ ! -f verification/startup/power_v111.json ] || v111=(--v111 verification/startup/power_v111.json)
python3 testbenches/startup/startup_check.py "${files[@]}" --orders $RUN_ORDERS "${v111[@]}" --out verification/startup
