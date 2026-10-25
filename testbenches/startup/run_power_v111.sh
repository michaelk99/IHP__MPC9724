#!/bin/bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# The DSA1 state (power_dsa1) on the chip of an older tag, for the report's comparison. The worktree stays
# untouched, everything is written under testbenches/startup/build/v111 and verification/startup/power_v111.json.
# Run inside IIC-OSIC-TOOLS at the repo root with the AGENTS.md environment set:
#   testbenches/startup/run_power_v111.sh <worktree of the tag> <tag>
set -euo pipefail
tree=$(realpath "$1"); tag=$2
B=testbenches/startup/build/v111
mkdir -p $B
STARTUP_TREE=$tree STARTUP_BUILD=$B STARTUP_ORDERS=power_dsa1 STARTUP_NO_CHECK=1 testbenches/startup/run_startup.sh
python3 testbenches/startup/startup_check.py $B/startup_power_dsa1.txt --export-power "$tree" "$tag" verification/startup/power_v111.json
cat verification/startup/power_v111.json
