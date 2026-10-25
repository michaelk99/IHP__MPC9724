#!/bin/bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Run one shell command at the repo root in a throwaway container of the pinned image.
#   scripts/in_image.sh 'make -C macros/dsa1_dig regmap-check'
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
source "$here/image.env"
case "$(uname -m)" in
    x86_64)  img=$IMAGE_AMD64 ;;
    aarch64) img=$IMAGE_ARM64 ;;
    *) echo "in_image.sh: no image for $(uname -m)" >&2; exit 1 ;;
esac
repo=$(git -C "$here" rev-parse --show-toplevel)
proj=$(dirname "$repo")
# The image's login shell resets PDK, so the exports go inside bash -lc.
env_vars="export PDK=ihp-sg13cmos5l PDKPATH=/foss/pdks/ihp-sg13cmos5l PDK_ROOT=/foss/pdks STD_CELL_LIBRARY=sg13cmos5l_stdcell SCL=sg13cmos5l_stdcell EZ130_DIR=/foss/designs/OpenBLAU/ip/ez130_8t_v1p1 DECAPHV_DIR=/foss/designs/OpenBLAU/ip/ez130_8t_decap_hv"
# --skip stops the entrypoint from starting a UI.
exec docker run --rm -v "$proj:/foss/designs" "$img" --skip bash -lc "$env_vars && cd /foss/designs/$(basename "$repo") && $1"
