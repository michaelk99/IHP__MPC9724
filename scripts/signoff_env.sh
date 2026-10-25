#!/bin/bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Print the environment the sign-off ran in, for verification/signoff_env.txt.
# Run it inside the container, at the repo root. The container cannot see its
# own image digest, so the host passes it:
#
#   d=$(docker image inspect --format '{{index .RepoDigests 0}}' registry.iic.jku.at:5000/iic-osic-tools:next)
#   docker exec <container> bash -lc "cd <repo> && scripts/signoff_env.sh $d" > verification/signoff_env.txt
set -u
digest=${1:-"not given, pass it from the host"}
: "${EZ130_DIR:?EZ130_DIR is not set}" "${DECAPHV_DIR:?DECAPHV_DIR is not set}"

md5() { md5sum "$1" | cut -d' ' -f1; }

echo "# Sign-off environment, written by scripts/signoff_env.sh"
echo "date: $(date -u +%Y-%m-%dT%H:%MZ)"
echo "git: $(git rev-parse HEAD) on $(git rev-parse --abbrev-ref HEAD), $( [ -z "$(git status --porcelain --untracked-files=no)" ] && echo clean || echo 'MODIFIED tracked files')"
echo "image: IIC-OSIC-TOOLS ${IIC_OSIC_TOOLS_VERSION:-unknown}, $digest"
echo "architecture: $(uname -m)"
echo "PDK: ${PDK:-unset}, commit $(cat "${PDK_ROOT:-/foss/pdks}/${PDK:-ihp-sg13cmos5l}/COMMIT" 2>/dev/null || echo unknown)"
echo "KLayout: $(klayout -v | sed 's/^KLayout //')"
echo "Magic: $(magic --version 2>/dev/null)"
echo "Netgen: $(netgen -batch quit 2>&1 | sed -n 's/^Netgen \([^ ]*\).*/\1/p' | head -1)"
echo "Yosys: $(yosys -V | sed 's/^Yosys //')"
echo "OpenROAD: $(openroad -version 2>/dev/null | tail -1 | sed "s/ *$//")"
echo "LibreLane: $(python3 -c 'import librelane; print(librelane.__version__)' 2>/dev/null)"
echo "Icarus: $(iverilog -V 2>/dev/null | head -1 | sed 's/^Icarus Verilog version //')"
echo "GHDL: $(ghdl --version 2>/dev/null | head -1)"
echo "EZ130 8T, read from outside the repo, md5:"
for f in gds/ez130_8t.gds lef/ez130_8t.lef lef/ez130_tech.lef cdl/ez130_8t.cdl verilog/ez130_8t.v \
         lib/ez130_8t_tt_1p20v_25c.lib lib/ez130_8t_ff_1p32v_m40c.lib lib/ez130_8t_ss_1p08v_125c.lib; do
    echo "  $(md5 "$EZ130_DIR/$f")  $f"
done
echo "EZ130 DECAPHV, read from outside the repo, md5:"
for f in gds/ez130_8t_decap_hv.gds lef/ez130_8t_decap_hv.lef cdl/ez130_8t_decap_hv.cdl; do
    echo "  $(md5 "$DECAPHV_DIR/$f")  $f"
done
