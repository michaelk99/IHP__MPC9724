# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1

TOP = decap_vdda
LIBRELANE_DIR := flow/librelane
FLOW_FINAL_DIR := flow/final
FINAL_DIR := final

# EZ130 and the thick-oxide decap, from the repo's ip/
EZ130_DIR   ?= $(abspath ../../ip/ez130_8t_v1p1)
DECAPHV_DIR ?= $(abspath ../../ip/ez130_8t_decap_hv)
EZ130_SCL    = $(shell python3 $(EZ130_DIR)/scripts/librelane_scl.py $(LIBRELANE_DIR))
DECAP_FRAG   = $(shell python3 ../scripts/decaphv_frag.py --ez130 $(EZ130_DIR) --decap $(DECAPHV_DIR) $(LIBRELANE_DIR))

.DEFAULT_GOAL := help

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

LL = librelane $(EZ130_SCL) $(DECAP_FRAG) $(LIBRELANE_DIR)/config.yaml --pdk ${PDK} --pdk-root ${PDK_ROOT} --manual-pdk

# OpenSTA rejects the empty *PORTS section that RCX writes for a design with no ports, so the run is split around RCX and the line is dropped
librelane: ## Run LibreLane with Magic and KLayout DRC
	$(LL) --to OpenROAD.RCX
	r=$$(ls -1 $(LIBRELANE_DIR)/runs | tail -n 1) && sed -i '/^\*PORTS$$/d' $(LIBRELANE_DIR)/runs/$$r/*-openroad-rcx/nom/$(TOP).nom.spef
	$(LL) --last-run --from OpenROAD.STAPostPNR --save-views-to $(FLOW_FINAL_DIR)/

fill: ## Add metal fill to the last run's GDS, writes flow/final/gds/$(TOP).fill.gds
	../scripts/fill_macro.sh $(FLOW_FINAL_DIR)/gds/$(TOP).gds $(FLOW_FINAL_DIR)/gds/$(TOP).fill.gds

copy-final: ## Copy the views of the last run to final/, the GDS with fill
	rm -rf $(FINAL_DIR)/
	mkdir -p $(FINAL_DIR)/gds
	cp $(FLOW_FINAL_DIR)/gds/$(TOP).fill.gds $(FINAL_DIR)/gds/$(TOP).gds
	for d in lef lib nl pnl spef vh; do cp -r $(FLOW_FINAL_DIR)/$$d $(FINAL_DIR)/$$d; done

.PHONY: help librelane fill copy-final
