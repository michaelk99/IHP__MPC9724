# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: thick-oxide decap cells for the EZ130 8T row
#
# Inside IIC-OSIC-TOOLS:
#   podman exec <container> bash -lc 'cd $DESIGNS/ip/ez130_8t_decap_hv && make verify'

.DEFAULT_GOAL := help

PDK_DIR  ?= $(PDK_ROOT)/$(PDK)
PYTHON3  ?= python3
COMMON   := ../../scripts
LIB      := ez130_8t_decap_hv
CELLS    ?= DECAPHV8 DECAPHV16 DECAPHV32
GDS      := gds/$(LIB).gds

.PHONY: help views drc drc-magic drc-row qa char verify clean

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

views: ## GDS, LEF, CDL and Verilog from the generator
	cd scripts && klayout -zz -r decap_hv_gen.py

# LU.a is the tapless library's: a cell alone is 20 um from any WELLTAP.
drc: ## KLayout DRC, both PDK decks, each cell alone
	@for c in $(CELLS); do echo "== $$c"; rm -rf build/drc_$$c; \
	  $(PYTHON3) $(COMMON)/drc_check.py --path=$(GDS) --topcell=$$c \
	    --run_dir=build/drc_$$c --no_density --waive "LU.a:$$c=1" || exit 1; done

drc-magic: ## Magic DRC, each cell alone
	@mkdir -p build
	cd scripts && magic -dnull -noconsole -rcfile $(PDK_DIR)/libs.tech/magic/$(PDK).magicrc \
	  magic_drc.tcl > ../build/magic_drc.log 2>&1
	@grep -A20 '^MAGIC' build/magic_drc.log
	@awk '/^MAGIC/ {n++; s += $$3} END {exit !(n == $(words $(CELLS)) && s == 0)}' build/magic_drc.log

# The one that matters: every EZ130 cell, in both orientations, beside, above
# and below each HV cell, and the HV cells against each other. Minutes per cell.
drc-row: ## Neighbour harness per cell, must report 0 markers
	@for c in $(CELLS); do echo "== $$c"; \
	  ( cd scripts && klayout -zz -r rowtest.py -rd dut=$$c ) || exit 1; \
	  rm -rf build/drc_rt_$$c; \
	  $(PYTHON3) $(COMMON)/drc_check.py --path=build/rowtest_$$c.gds \
	    --topcell=rowtest_$$c --run_dir=build/drc_rt_$$c --no_density \
	    --mp=$${OPENBLAU_NJOBS:-4} || exit 1; done

qa: ## sclqa: CDL vs GDS pin-for-pin, DRC, LEF vs GDS, Verilog vs liberty
	cd $(COMMON) && $(PYTHON3) -m sclqa $(CURDIR) -o $(CURDIR)/build/sclqa_report.md

char: ## C and leakage at tt/ss/ff against EZ130's LV decaps, writes lib/
	cd scripts && $(PYTHON3) char_decap_hv.py

verify: drc drc-magic qa drc-row ## Everything that can fail

clean: ## Remove build/
	rm -rf build
