#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Add metal fill inside a hardened macro's GDS, so the block meets the PDK's
# minimum local density on its own.
#
# Why this exists: a macro is a hard block, and the chip-level fill step cannot
# place anything inside its footprint. dsa1_dig_top came out of LibreLane at
# 5.4 % Metal4 over a 497 um square, against the 25 % minimum of M4Fil.h, and no
# amount of fill around it can make the window pass. Measured: the chip-level
# M4 fill at its tightest legal spacing still left the die-centre window 2.7 %
# short.
#
# TopMetal1 is deliberately NOT filled. The chip runs its TopMetal1 power
# stripes across the macro, and floating fill on that layer would sit under
# them.
#
# Usage: fill_macro.sh <gds-in> <gds-out>
# Runs inside IIC-OSIC-TOOLS, needs PDK, PDKPATH and PDK_ROOT.

set -euo pipefail

GDS_IN=${1:?usage: fill_macro.sh <gds-in> <gds-out>}
GDS_OUT=${2:?usage: fill_macro.sh <gds-in> <gds-out>}

: "${PDK:?PDK is not set}"
: "${PDKPATH:?PDKPATH is not set}"

# Filler spacing per layer. Minimum legal spacing is 0.42 um (M1Fil.b to
# M4Fil.b); 0.5 keeps a little margin rather than sitting on the rule.
FILL_DIST_M1=0.75
FILL_DIST_M2=0.75
FILL_DIST_M3=1.25
FILL_DIST_M4=0.50
# Large enough that the PDK filler places no TopMetal1 at all.
FILL_DIST_TM1=10000

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# The PDK filler macros hard-code their distances and only a GUI dialog can
# change them, so copy them into a fake PDK tree, patch the copies, and point
# filler.py at it. Same trick as scripts/add_logo_fill.sh at the chip level.
MACRO_SRC="${PDKPATH}/libs.tech/klayout/tech/macros"
MACRO_DST="${WORK}/${PDK}/libs.tech/klayout/tech/macros"
mkdir -p "$MACRO_DST"
cp "${MACRO_SRC}/sg13cmos5l_filler_ActGatP.lym" \
   "${MACRO_SRC}/sg13cmos5l_filler_Metal.lym" \
   "$MACRO_DST/"

sed -i \
    -e "s/'distance_m1' => [0-9.]*/'distance_m1' => ${FILL_DIST_M1}/" \
    -e "s/'distance_m2' => [0-9.]*/'distance_m2' => ${FILL_DIST_M2}/" \
    -e "s/'distance_m3' => [0-9.]*/'distance_m3' => ${FILL_DIST_M3}/" \
    -e "s/'distance_m4' => [0-9.]*/'distance_m4' => ${FILL_DIST_M4}/" \
    -e "s/'distance_tm1' => [0-9.]*/'distance_tm1' => ${FILL_DIST_TM1}/" \
    "${MACRO_DST}/sg13cmos5l_filler_Metal.lym"

for PATCHED in "'distance_m1' => ${FILL_DIST_M1}" "'distance_m4' => ${FILL_DIST_M4}" "'distance_tm1' => ${FILL_DIST_TM1}"; do
    grep -qF "$PATCHED" "${MACRO_DST}/sg13cmos5l_filler_Metal.lym" || {
        echo "[ERROR] Failed to patch fill distances (PDK macro changed?)"; exit 1; }
done

echo "[INFO] Filling ${GDS_IN}"
echo "[INFO] Fill distances: M1-M4 = ${FILL_DIST_M1}/${FILL_DIST_M2}/${FILL_DIST_M3}/${FILL_DIST_M4} um, TopMetal1 disabled"

# The filler fills EdgeSeal.holes, the area enclosed by the seal ring on 39/0.
# A hardened macro has none, so without this the filler runs, prints "Filling
# M1" and places nothing at all. Wrap the macro in a ring whose hole is its own
# bounding box, fill, then strip the ring again.
klayout -b -rd gds="$GDS_IN" -rd out="${WORK}/sealed.gds" -rd mode=add \
    -r "${SCRIPT_DIR}/seal_ring.py"

PDK_ROOT="$WORK" klayout -zz \
    -rd output_file="${WORK}/filled.gds" \
    -r "${PDKPATH}/libs.tech/klayout/tech/scripts/filler.py" \
    "${WORK}/sealed.gds"

klayout -b -rd gds="${WORK}/filled.gds" -rd out="${GDS_OUT}" -rd mode=strip \
    -r "${SCRIPT_DIR}/seal_ring.py"

echo "[INFO] Wrote ${GDS_OUT}"
klayout -b -rd gds="${GDS_OUT}" -r "${SCRIPT_DIR}/report_density.py"
