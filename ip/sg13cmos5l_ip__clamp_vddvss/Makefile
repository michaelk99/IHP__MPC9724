# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: sg13cmos5l_ip__clamp_vddvss, the vdd-to-vss ESD clamp ring cell
#
# Every target runs inside IIC-OSIC-TOOLS with the PDK environment set.
# GDS, CDL and OUT let `make mutants` point each check at a broken input.

.DEFAULT_GOAL := help
SHELL := /bin/bash

REQUIRED_PDK ?= ihp-sg13cmos5l
ifneq ($(REQUIRED_PDK),)
ifneq ($(filter-out help clean,$(or $(MAKECMDGOALS),$(.DEFAULT_GOAL))),)
ifneq ($(PDK),$(REQUIRED_PDK))
$(error PDK is "$(PDK)", but this IP needs "$(REQUIRED_PDK)")
endif
endif
endif

CELL    := sg13cmos5l_ip__clamp_vddvss
GDS     ?= gds/$(CELL).gds
CDL     ?= cdl/$(CELL).cdl
OUT     ?= verification
MUT_DIR ?= /tmp/$(CELL)_mutants
ROWS    ?= abut f2000 f4000
NP      ?= $(shell nproc --ignore 5)
LVS_RUNNER := $(PDK_ROOT)/$(PDK)/libs.tech/klayout/tech/lvs/run_lvs.py
DRC_RUNNER := $(PDK_ROOT)/$(PDK)/libs.tech/klayout/tech/drc/run_drc.py
export KLAYOUT_PATH := $(PDK_ROOT)/$(PDK)/libs.tech/klayout:$(PDK_ROOT)/$(PDK)/libs.tech/klayout/tech

.PHONY: help gen drc magic-drc drc-abut lvs probe sim-clamp check mutants clean

help: ## Show the targets
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

gen: ## Build the GDS and the LEF
	python3 layout/rails.py
	cd layout && klayout -n sg13cmos5l -zz -r clamp_gen.py

# The cell alone, regular deck. Only the density table's global rules may fire.
drc: ## KLayout regular DRC of the cell
	rm -rf $(OUT)/drc/$(CELL).klayout.drc && mkdir -p $(OUT)/drc
	-sak-drc.sh -d -k -l regular -w $(OUT)/drc $(GDS) > /dev/null
	python3 layout/drc_report.py $(OUT)/drc/$(CELL).klayout.drc

# No -f "*": with `gds flatglob *` Magic flattens the top cell away and checks
# an empty cell, which reports 0 on any layout.
magic-drc: ## Magic DRC of the cell, full style
	rm -rf $(OUT)/drc/$(CELL).magic.drc && mkdir -p $(OUT)/drc
	-sak-drc.sh -d -m -w $(OUT)/drc $(GDS) > /dev/null
	@r=$(OUT)/drc/$(CELL).magic.drc; cat $$r/$(CELL).magic.drc.rpt; \
	  grep -q 'drc(full)' $$r/$(CELL).magic.drc.log && grep -q '^\[INFO\] COUNT: 0$$' $$r/$(CELL).magic.drc.rpt \
	  && test ! -e $$r/drc_$(CELL).cellmismatch && echo "PASS: Magic DRC of $(CELL)"

# Flat, so a marker in a shared bondpad context comes back in row coordinates.
drc-abut: ## The cell between IOPadVss and IOPadVdd, abutted and with fillers, DRC against filler rows
	mkdir -p $(OUT)/abut
	cd $(OUT)/abut && klayout -b -r $(CURDIR)/layout/clamp_abut.py -rd out=. -rd gds=$(abspath $(GDS))
	@cd $(OUT)/abut && ok=0; for r in $(ROWS); do for s in "" _ref; do t=clamp_row_$$r$$s; rm -rf $$t.drc; \
	  python3 $(DRC_RUNNER) --path=$$t.gds --topcell=$$t --run_dir=$$t.drc --run_mode=flat --antenna \
	    --mp=$(NP) --density_thr=$(NP) > $$t.drc.log 2>&1; done; \
	  read t x0 x1 <<< "$$(grep "clamp_row_$$r " rows.txt)"; echo "=== $$t"; \
	  python3 $(CURDIR)/layout/drc_report.py $$t.drc --ref $${t}_ref.drc --cell $$x0,$$x1 || ok=1; done; exit $$ok

# run_lvs.py exits 0 on a mismatch, so the verdict is read from its summary.
# Series resistors stay apart: the 25 rppd are compared one by one.
lvs: ## KLayout LVS of the cell against its CDL
	rm -rf $(OUT)/lvs && mkdir -p $(OUT)/lvs
	python3 $(LVS_RUNNER) --layout=$(GDS) --netlist=$(CDL) --topcell=$(CELL) \
	  --run_dir=$(OUT)/lvs --no_series_res > $(OUT)/lvs/lvs.out 2>&1 || true
	@grep -E "Status|Outcome" $(OUT)/lvs/lvs.out
	@grep -q "Comparison mode: PASS (netlists match)" $(OUT)/lvs/lvs.out && echo "PASS: LVS of $(CELL)"

probe: ## Connectivity probe: stripes on their bands, no short, bands edge to edge
	cd layout && klayout -b -r clamp_probe.py -rd gds=$(abspath $(GDS))

sim-clamp: ## Clamp bench: leakage, turn-on, supply ramps, HBM pulse, SIM_ARGS="--vdd 1.5" for another supply
	python3 sim/tb_clamp.py --cdl $(CDL) --run $(OUT)/sim $(SIM_ARGS)

check: drc magic-drc drc-abut lvs probe sim-clamp ## Every check above

mutants: ## Negative controls: each check must fail on its broken input
	bash layout/mutants.sh $(MUT_DIR)

clean: ## Remove check outputs
	rm -rf verification layout/__pycache__
