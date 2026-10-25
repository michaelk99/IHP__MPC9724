# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: sg13cmos5l_ip__cut_vdd, the ring cell without the vdd band
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

CELL    := sg13cmos5l_ip__cut_vdd
GDS     ?= gds/$(CELL).gds
CDL     ?= cdl/$(CELL).cdl
OUT     ?= verification
MUT_DIR ?= /tmp/$(CELL)_mutants
ROWS    ?= inout_abut inout_f2000 inout_f4000 vssin_abut vssin_f2000 vssin_f4000
CLAMP   := ../sg13cmos5l_ip__clamp_vddvss/layout
NP      ?= $(shell nproc --ignore 5)
LVS_RUNNER := $(PDK_ROOT)/$(PDK)/libs.tech/klayout/tech/lvs/run_lvs.py
DRC_RUNNER := $(PDK_ROOT)/$(PDK)/libs.tech/klayout/tech/drc/run_drc.py
export KLAYOUT_PATH := $(PDK_ROOT)/$(PDK)/libs.tech/klayout:$(PDK_ROOT)/$(PDK)/libs.tech/klayout/tech

.PHONY: help gen drc magic-drc drc-abut lvs probe probe-filler check mutants clean

help: ## Show the targets
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

gen: ## Build the GDS and the LEF
	python3 $(CLAMP)/rails.py
	cd layout && klayout -n sg13cmos5l -zz -r cut_gen.py

# The cell alone, regular deck. Only the density table's global rules may fire.
drc: ## KLayout regular DRC of the cell
	rm -rf $(OUT)/drc/$(CELL).klayout.drc && mkdir -p $(OUT)/drc
	-sak-drc.sh -d -k -l regular -w $(OUT)/drc $(GDS) > /dev/null
	python3 $(CLAMP)/drc_report.py $(OUT)/drc/$(CELL).klayout.drc

# No -f "*": with `gds flatglob *` Magic flattens the top cell away and checks
# an empty cell, which reports 0 on any layout.
magic-drc: ## Magic DRC of the cell, full style
	rm -rf $(OUT)/drc/$(CELL).magic.drc && mkdir -p $(OUT)/drc
	-sak-drc.sh -d -m -w $(OUT)/drc $(GDS) > /dev/null
	@r=$(OUT)/drc/$(CELL).magic.drc; cat $$r/$(CELL).magic.drc.rpt; \
	  grep -q 'drc(full)' $$r/$(CELL).magic.drc.log && grep -q '^\[INFO\] COUNT: 0$$' $$r/$(CELL).magic.drc.rpt \
	  && test ! -e $$r/drc_$(CELL).cellmismatch && echo "PASS: Magic DRC of $(CELL)"

# Flat, so a marker in a shared bondpad context comes back in row coordinates.
drc-abut: ## The cell between IOPadIn and IOPadOut4mA, and IOPadVss and IOPadIn, abutted and with fillers, DRC against filler rows
	mkdir -p $(OUT)/abut
	cd $(OUT)/abut && klayout -b -r $(CURDIR)/layout/cut_abut.py -rd out=. -rd gds=$(abspath $(GDS))
	@cd $(OUT)/abut && ok=0; for r in $(ROWS); do for s in "" _ref; do t=cut_$$r$$s; rm -rf $$t.drc; \
	  python3 $(DRC_RUNNER) --path=$$t.gds --topcell=$$t --run_dir=$$t.drc --run_mode=flat --antenna \
	    --mp=$(NP) --density_thr=$(NP) > $$t.drc.log 2>&1; done; \
	  read t x0 x1 <<< "$$(grep "cut_$$r " rows.txt)"; echo "=== $$t"; \
	  python3 $(abspath $(CLAMP))/drc_report.py $$t.drc --ref $${t}_ref.drc --cell $$x0,$$x1 || ok=1; done; exit $$ok

# run_lvs.py exits 0 on a mismatch, so the verdict is read from its summary.
# A cell without devices extracts to an empty netlist, so the two flags are needed
# and LVS compares nothing. The ports and the bands are the probe's job.
lvs: ## KLayout LVS of the cell against its CDL (vacuous, no devices)
	rm -rf $(OUT)/lvs && mkdir -p $(OUT)/lvs
	python3 $(LVS_RUNNER) --layout=$(GDS) --netlist=$(CDL) --topcell=$(CELL) \
	  --run_dir=$(OUT)/lvs --disable_tap_extraction --ignore_top_ports_mismatch > $(OUT)/lvs/lvs.out 2>&1 || true
	@grep -E "Status|Outcome" $(OUT)/lvs/lvs.out
	@grep -q "Comparison mode: PASS (netlists match)" $(OUT)/lvs/lvs.out && echo "PASS: LVS of $(CELL)"

probe: ## Bands whole edge to edge, nothing of the vdd band
	cd layout && klayout -b -r cut_probe.py -rd gds=$(abspath $(GDS))

# The PDK's own Filler2000 has the vdd band, so the probe has to fail on it.
probe-filler: ## The probe on the PDK's Filler2000 must fail on the vdd band
	@cd layout && if klayout -b -r cut_probe.py -rd cell=sg13cmos5l_Filler2000 \
	  -rd gds=$(PDK_ROOT)/$(PDK)/libs.ref/sg13cmos5l_io/gds/sg13cmos5l_io.gds > /tmp/$(CELL)_probe_filler.log 2>&1; \
	  then cat /tmp/$(CELL)_probe_filler.log; echo "probe passed on the filler"; exit 1; \
	  else grep -E '^FAIL' /tmp/$(CELL)_probe_filler.log | sed -n '1,3p;$$p'; grep -E 'cut_probe' /tmp/$(CELL)_probe_filler.log; echo "PASS: probe fails on Filler2000, as it should"; fi

check: drc magic-drc drc-abut lvs probe probe-filler ## Every check above

mutants: ## Negative controls: each check must fail on its broken input
	bash layout/mutants.sh $(MUT_DIR)

clean: ## Remove check outputs
	rm -rf verification layout/__pycache__
