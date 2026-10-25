# Makefile for the DSADC1 digital back-end chip on the ihp-sg13cmos5l Open-PDK, built from the chip design template.
#
# SPDX-FileCopyrightText: 2026 Simon Dorrer and Harald Pretl
# Johannes Kepler University, Department for Integrated Circuits
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# ========================================================================

MAKEFILE_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

RUN_TAG = $(shell ls -1 $(LIBRELANE_DIR)/runs 2>/dev/null | tail -n 1)

# Variables
TOP = sg13cmos5l_dsa1_dig_top

.DEFAULT_GOAL := help

# PDK Guard
# Override with: make <target> REQUIRED_PDK=<pdk>, an empty value skips the check
REQUIRED_PDK ?= ihp-sg13cmos5l

# Goals that do not read the PDK
PDK_FREE_GOALS = help clean clean-all

ifneq ($(REQUIRED_PDK),)
ifneq ($(filter-out $(PDK_FREE_GOALS),$(or $(MAKECMDGOALS),$(.DEFAULT_GOAL))),)
ifneq ($(PDK),$(REQUIRED_PDK))
$(error PDK is "$(PDK)", but this chip needs "$(REQUIRED_PDK)". Run `sak-pdk $(REQUIRED_PDK)` in this shell and retry, or pass REQUIRED_PDK= to skip this check)
endif
endif
endif
# ========================================================================


# Cell name for verification targets (default: top-level cell)
# Override with: make <target> CELL=<cellname>
CELL ?= $(TOP)

# PEX mode (1 = C-decoupled, 2 = C-coupled, 3 = full-RC)
# Override with: make <target> EXT_MODE=<1|2|3>
EXT_MODE ?= 1

# full-RC extresist threshold in mOhm (sak-pex.sh -t, only used in EXT_MODE=3; default: 10000 = 10 Ohm)
# Override with: make <target> THRESHOLD=<mOhm>
THRESHOLD ?= 10000

# full-RC extresist minres in mOhm (sak-pex.sh -r, only used in EXT_MODE=3; default: 1000 = 1 Ohm)
# Override with: make <target> MINRES=<mOhm>
MINRES ?= 1000

# full-RC extresist mindelay in ps (sak-pex.sh -y, only used in EXT_MODE=3; default: 1; 0 = gate by resistance)
# Override with: make <target> MINDELAY=<ps>
MINDELAY ?= 1

# KLayout DRC level: precheck, macro, or regular (sak-drc.sh -l, only used by klayout-drc; default: macro)
# Override with: make <target> DRC_LEVEL=<precheck|macro|regular>
DRC_LEVEL ?= macro

# Supply pins that the flat PEX extraction merges into one node, they are dropped from the generated <CELL>_pex.sym so it matches the extracted netlist.
# IOVSS and VSS share the p-substrate, so a flat extraction reports one ground node named VSS and the PEX netlist carries no IOVSS port. Pads that repeat a pin name are dropped down to one pin the same way, only the pin boxes go and the labels stay.
# Override with: make <target> PEX_MERGED_PINS="<pin> <pin> ..."
PEX_MERGED_PINS ?= IOVSS

# Floating-point precision (significant digits) for Xschem's ev function
# Override with: make <target> EV_PRECISION=<digits>
EV_PRECISION ?= 5

# Set the waveform viewer GTKWave or Surfer (default: gtkwave)
# Override with: make <target> WAVEFORM_VIEWER=<gtkwave|surfer>
WAVEFORM_VIEWER ?= gtkwave

# Version for release target
# Override with: make <target> VERSION=<version>
VERSION ?= 1.0.0

# Extra options for the sak-open.py file browser (e.g. --all to include build outputs)
# Override with: make open OPEN_ARGS=<options>
OPEN_ARGS ?=

# The die carries one macro hardened on EZ130, which is characterised at three
# corners, so STA_CORNERS in flow/librelane/config.yaml is reduced to those.
# Keep this list in step with it.
STA_CORNERS := nom_fast_1p32V_m40C nom_slow_1p08V_125C nom_typ_1p20V_25C

# The chip core sits on EZ130 rows, so its decoupling can be the thick-oxide
# DECAPHV cells the macros use: the PDK library has no thick-oxide decap. Both
# are read in place from outside this repo, as in macros/dsa1_dig/Makefile.
# The IO liberty and the bondpad views go into the same fragment, because the
# design config would replace the fragment's LIB and EXTRA_* lists, not extend them.
EZ130_DIR   ?= $(HOME)/projects/OpenBLAU/ip/ez130_8t_v1p1
DECAPHV_DIR ?= $(HOME)/projects/OpenBLAU/ip/ez130_8t_decap_hv
IO_LIB_DIR  := $(abspath ip/sg13cmos5l_io_custom/lib)
BONDPAD_DIR := $(abspath ip/sg13cmos5l_ip__bondpad_70x70/final)
CLAMP_DIR   := $(abspath ip/sg13cmos5l_ip__clamp_vddvss)
CUT_DIR     := $(abspath ip/sg13cmos5l_ip__cut_vdd)
EZ130_SCL    = $(shell python3 $(EZ130_DIR)/scripts/librelane_scl.py $(LIBRELANE_DIR))
CHIP_FRAG    = $(shell python3 $(MACROS_DIR)/scripts/decaphv_frag.py --ez130 $(EZ130_DIR) --decap $(DECAPHV_DIR) \
	--extra-lib nom_typ_1p20V_25C=$(IO_LIB_DIR)/sg13cmos5l_io_typ_1p2V_3p3V_25C.lib \
	--extra-lib nom_fast_1p32V_m40C=$(IO_LIB_DIR)/sg13cmos5l_io_fast_1p32V_3p6V_m40C.lib \
	--extra-lib nom_slow_1p08V_125C=$(IO_LIB_DIR)/sg13cmos5l_io_slow_1p08V_3p0V_125C.lib \
	--extra-lef $(BONDPAD_DIR)/lef/sg13cmos5l_ip__bondpad_70x70.lef \
	--extra-gds $(BONDPAD_DIR)/gds/sg13cmos5l_ip__bondpad_70x70.gds \
	--extra-gds $(CLAMP_DIR)/gds/sg13cmos5l_ip__clamp_vddvss.gds \
	--extra-lib nom_typ_1p20V_25C=$(CLAMP_DIR)/lib/sg13cmos5l_ip__clamp_vddvss.lib \
	--extra-lib nom_fast_1p32V_m40C=$(CLAMP_DIR)/lib/sg13cmos5l_ip__clamp_vddvss.lib \
	--extra-lib nom_slow_1p08V_125C=$(CLAMP_DIR)/lib/sg13cmos5l_ip__clamp_vddvss.lib \
	--extra-gds $(CUT_DIR)/gds/sg13cmos5l_ip__cut_vdd.gds \
	--extra-lib nom_typ_1p20V_25C=$(CUT_DIR)/lib/sg13cmos5l_ip__cut_vdd.lib \
	--extra-lib nom_fast_1p32V_m40C=$(CUT_DIR)/lib/sg13cmos5l_ip__cut_vdd.lib \
	--extra-lib nom_slow_1p08V_125C=$(CUT_DIR)/lib/sg13cmos5l_ip__cut_vdd.lib $(LIBRELANE_DIR))
CHIP_FRAGS   = $(EZ130_SCL) $(CHIP_FRAG)

# Folder structure
XSCHEM_SCH_DIR  		:= schematic/xschem
XSCHEM_TB_DIR   		:= testbenches/xschem
COCOTB_DIR      		:= testbenches/cocotb
LAY_DIR         		:= layout
SCRIPTS_DIR     		:= scripts
SIM_PLOT_DIR    		:= testbenches/xschem/plot_simulations
RENDER_IMG_DIR  		:= render/img
SRC_DIR         		:= rtl
IP_DIR          		:= ip
MACROS_DIR      		:= macros
RELEASE_DIR     		:= release
NET_SCH_DIR     		:= netlist/schematic
NET_LAY_DIR     		:= netlist/layout
NET_PEX_DIR     		:= netlist/pex
NET_PNL_DIR     		:= netlist/pnl
NET_NL_DIR      		:= netlist/nl
NET_SPICE_DIR   		:= netlist/spice
PACKAGING_DIR   		:= packaging
PACKAGING_RENDER_DIR	:= packaging/render
# Package footprint GDS generated by run_bondplan.py, name taken from packaging/config.yaml
PACKAGE_NAME    		:= $(shell sed -n 's/^PACKAGE_NAME:[[:space:]]*//p' packaging/config.yaml)
LVS_RPT_DIR     		:= verification/lvs
DRC_RPT_DIR     		:= verification/drc
REPORT_DIR      		:= verification/reports
LIBRELANE_DIR   		:= flow/librelane
FLOW_FINAL_DIR  		:= flow/final


# Help Target
help: ## Show this help message
	@echo 'Usage: make <target> [CELL=<cellname>] [EXT_MODE=<1|2|3>] [THRESHOLD=<mOhm>] [MINRES=<mOhm>] [MINDELAY=<ps>] [DRC_LEVEL=<precheck|macro|regular>] [PEX_MERGED_PINS="<pin> ..."] [EV_PRECISION=<digits>] [WAVEFORM_VIEWER=<gtkwave|surfer>] [TB=<testbenchname>] [SCRIPT=<scriptname>] [VERSION=<version>] [OPEN_ARGS=<options>]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z0-9_.-]+:.*## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-20s %s\n", $$1, $$2}'
	@echo ''
	@echo 'CELL defaults to $(TOP). Override to verify subcells.'
	@echo 'EXT_MODE defaults to 1 (C-decoupled). 2=C-coupled, 3=full-RC.'
	@echo 'THRESHOLD/MINRES/MINDELAY are full-RC (EXT_MODE=3) extresist settings for magic-pex (defaults 10000 mOhm / 1000 mOhm / 1 ps).'
	@echo 'DRC_LEVEL defaults to macro. Sets the KLayout DRC level for klayout-drc (precheck|macro|regular).'
	@echo 'PEX_MERGED_PINS defaults to IOVSS. Lists the supply pins that the flat extraction merges, they are dropped from the generated PEX symbol.'
	@echo 'EV_PRECISION defaults to 5 significant digits for Xschem ev function.'
	@echo 'WAVEFORM_VIEWER defaults to gtkwave. Use surfer to launch Surfer instead.'
	@echo 'TB selects the Xschem testbench for sim-gl-xschem (default: <CELL>_tb_tran).'
	@echo 'SCRIPT selects the plotting script for sim-view-xschem (default: plot_<CELL>).'
	@echo 'VERSION defaults to $(VERSION). Used by the release target.'
	@echo 'OPEN_ARGS passes extra options to sak-open.py for the open target (e.g. --all).'
	@echo 'REQUIRED_PDK defaults to $(REQUIRED_PDK). Every target except help, clean and clean-all aborts if $$PDK differs.'
.PHONY: help
# ================================================================================================


# Open Target
open: ## Open the design files of this folder in the sak-open.py file browser (needs the VNC/X11 desktop)
	sak-open.py $(OPEN_ARGS) .
.PHONY: open
# ================================================================================================


# Git Submodule Target
init-submodules: ## Initialize and update git submodules (e.g. flow/artistic)
	git -C $(MAKEFILE_DIR) -c safe.directory='*' submodule update --init
.PHONY: init-submodules
# ================================================================================================


# Simulation Targets
# Testbench for the Xschem simulation targets (default: <CELL>_tb_tran)
# Override with: make <target> TB=<testbenchname>
TB ?= $(CELL)_tb_tran
# Plotting script for sim-view-xschem (default: plot_<CELL>)
# Override with: make <target> SCRIPT=<scriptname>
SCRIPT ?= plot_$(CELL)

sim-rtl-cocotb: ## Run RTL simulation of CELL cell with cocotb (usage: make sim-rtl-cocotb [CELL=<cellname>])
	cd $(COCOTB_DIR) && python3 $(CELL)_tb.py
.PHONY: sim-rtl-cocotb

sim-gl-cocotb: ## Run gate-level simulation of CELL cell with cocotb (usage: make sim-gl-cocotb [CELL=<cellname>])
	cd $(COCOTB_DIR) && GL=1 python3 $(CELL)_tb.py
.PHONY: sim-gl-cocotb

sim-view-cocotb: ## View CELL cell cocotb simulation waveforms (usage: make sim-view-cocotb [CELL=<cellname>] [WAVEFORM_VIEWER=<gtkwave|surfer>])
	@if [ "$(WAVEFORM_VIEWER)" = "gtkwave" ]; then \
		$(WAVEFORM_VIEWER) $(COCOTB_DIR)/sim_build/$(CELL).fst $(COCOTB_DIR)/$(CELL)_tb.gtkw; \
	elif [ "$(WAVEFORM_VIEWER)" = "surfer" ]; then \
		$(WAVEFORM_VIEWER) -s $(COCOTB_DIR)/$(CELL)_tb.surf.ron $(COCOTB_DIR)/sim_build/$(CELL).fst; \
	else \
		$(WAVEFORM_VIEWER) $(COCOTB_DIR)/sim_build/$(CELL).fst; \
	fi
.PHONY: sim-view-cocotb

sim-gl-xschem: ## Run gate-level simulation of CELL cell with Xschem in batch mode (usage: make sim-gl-xschem [CELL=<cellname>] [TB=<testbenchname>])
	mkdir -p $(XSCHEM_TB_DIR)/simulations
	mkdir -p $(SIM_PLOT_DIR)/data
	cd $(XSCHEM_TB_DIR) && xschem -r -x -q --rcfile xschemrc --command ' \
		xschem set netlist_type spice; \
		set netlist_dir $(abspath $(XSCHEM_TB_DIR)/simulations); \
		xschem save; \
		write_data [save_params] $(abspath $(XSCHEM_TB_DIR)/simulations)/$(TB).save; \
		xschem netlist \
	' $(TB).sch
	cd $(XSCHEM_TB_DIR)/simulations && ngspice -b $(TB).spice
.PHONY: sim-gl-xschem

sim-view-xschem: ## Plot Xschem simulation results (usage: make sim-view-xschem [SCRIPT=<scriptname>])
	SHOW_PLOTS=1 python3 $(SIM_PLOT_DIR)/$(SCRIPT).py
.PHONY: sim-view-xschem

sim-all: ## Simulate the chip (RTL/GL cocotb + GL Xschem)
	$(MAKE) sim-rtl-cocotb
	$(MAKE) sim-gl-cocotb
	$(MAKE) sim-gl-xschem
.PHONY: sim-all
# ================================================================================================


# LibreLane Targets
librelane: check-ez130 ## Run LibreLane with Magic and KLayout DRC checks
	librelane $(CHIP_FRAGS) $(LIBRELANE_DIR)/config.yaml --pdk ${PDK} --pdk-root ${PDK_ROOT} --manual-pdk --save-views-to $(FLOW_FINAL_DIR)/
.PHONY: librelane

librelane-nodrc: check-ez130 ## Run LibreLane without DRC checks
	librelane $(CHIP_FRAGS) $(LIBRELANE_DIR)/config.yaml --pdk ${PDK} --pdk-root ${PDK_ROOT} --manual-pdk --save-views-to $(FLOW_FINAL_DIR)/ --skip KLayout.DRC --skip Magic.DRC --skip KLayout.Antenna --skip KLayout.Density
.PHONY: librelane-nodrc

librelane-magicdrc: check-ez130 ## Run LibreLane with only Magic DRC checks
	librelane $(CHIP_FRAGS) $(LIBRELANE_DIR)/config.yaml --pdk ${PDK} --pdk-root ${PDK_ROOT} --manual-pdk --save-views-to $(FLOW_FINAL_DIR)/ --skip KLayout.DRC
.PHONY: librelane-magicdrc

librelane-klayoutdrc: check-ez130 ## Run LibreLane with only KLayout DRC checks
	librelane $(CHIP_FRAGS) $(LIBRELANE_DIR)/config.yaml --pdk ${PDK} --pdk-root ${PDK_ROOT} --manual-pdk --save-views-to $(FLOW_FINAL_DIR)/ --skip Magic.DRC
.PHONY: librelane-klayoutdrc

check-ez130: ## Fail early if EZ130_DIR or DECAPHV_DIR does not hold the libraries
	@test -f $(EZ130_DIR)/scripts/librelane_scl.py || \
		{ echo "EZ130_DIR is '$(EZ130_DIR)', which has no scripts/librelane_scl.py. Point it at the ez130_8t_v1p1 checkout."; exit 1; }
	@test -f $(DECAPHV_DIR)/lef/ez130_8t_decap_hv.lef || \
		{ echo "DECAPHV_DIR is '$(DECAPHV_DIR)', which has no lef/ez130_8t_decap_hv.lef. Point it at the ez130_8t_decap_hv checkout."; exit 1; }
.PHONY: check-ez130

# The macro's banned cells, plus the PDK's thin-oxide decaps, which the EZ130
# rows replaced at chip level.
CHIP_BANNED_CELLS = $(shell sed -n 's/^BANNED_CELLS := //p' $(MACROS_DIR)/dsa1_dig/Makefile) sg13cmos5l_decap_4 sg13cmos5l_decap_8

check-netlist: ## Fail if any cell that is wrong in silicon, or a thin-oxide decap, reached the chip netlist
	@test -f $(NET_NL_DIR)/$(TOP).nl.v || { echo "No $(NET_NL_DIR)/$(TOP).nl.v. Run 'make build-top' first."; exit 1; }
	@test -n "$(filter DECAP4,$(CHIP_BANNED_CELLS))" || { echo "Could not read BANNED_CELLS from $(MACROS_DIR)/dsa1_dig/Makefile"; exit 1; }
	@bad=0; for c in $(CHIP_BANNED_CELLS); do \
		n=$$(grep -c -E "^\s*$$c " $(NET_NL_DIR)/$(TOP).nl.v); \
		if [ $$n -gt 0 ]; then echo "BANNED CELL in netlist: $$c, $$n instances"; bad=1; fi; \
	done; test $$bad -eq 0 && echo "OK: no banned cell in $(NET_NL_DIR)/$(TOP).nl.v"
.PHONY: check-netlist

librelane-openroad: ## Open the last LibreLane run in OpenROAD GUI
	librelane $(CHIP_FRAGS) $(LIBRELANE_DIR)/config.yaml --pdk ${PDK} --pdk-root ${PDK_ROOT} --manual-pdk --last-run --flow OpenInOpenROAD
.PHONY: librelane-openroad

librelane-klayout: ## Open the last LibreLane run in KLayout
	librelane $(CHIP_FRAGS) $(LIBRELANE_DIR)/config.yaml --pdk ${PDK} --pdk-root ${PDK_ROOT} --manual-pdk --last-run --flow OpenInKLayout
.PHONY: librelane-klayout
# ================================================================================================


# Copy Targets
# TODO: KLayout antenna and DRC reports are temporarily commented out until
# IHP fixes the `metal1_pin_offgrid` errors. For now, `make librelane-nodrc` must be used.
# https://github.com/IHP-GmbH/IHP-Open-PDK/issues/683#issuecomment-4065791975
# Using * wildcard to ignore step numbers
copy-reports: ## Copy yosys, antenna, STA, power, IR-drop, LVS and manufacturability reports from the last LibreLane run to verification/reports/
	rm -rf $(REPORT_DIR)/
	mkdir -p $(REPORT_DIR)/
	cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-yosys-synthesis/reports/pre_synth_chk.rpt $(REPORT_DIR)/yosys_synth_check.rpt
	cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-yosys-synthesis/reports/pre_techmap.rpt $(REPORT_DIR)/yosys_pre_techmap.rpt
	cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-yosys-synthesis/reports/post_dff.rpt $(REPORT_DIR)/yosys_post_dff.rpt
	cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-yosys-synthesis/reports/stat.rpt $(REPORT_DIR)/stat.rpt
	cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-openroad-checkantennas-1/reports/antenna.rpt $(REPORT_DIR)/antenna_violations.rpt
	cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-openroad-checkantennas-1/reports/antenna_summary.rpt $(REPORT_DIR)/antenna_summary.rpt
	cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-openroad-stapostpnr/summary.rpt $(REPORT_DIR)/stapostpnr_summary.rpt
	for c in $(STA_CORNERS); do \
		cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-openroad-stapostpnr/$$c/power.rpt $(REPORT_DIR)/stapostpnr_$${c}_power.rpt; \
	done
	cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-openroad-irdropreport/irdrop.rpt $(REPORT_DIR)/irdrop.rpt
# 	cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-magic-drc/reports/drc.magic.rpt $(REPORT_DIR)/drc.magic.rpt
# 	cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-klayout-drc/reports/drc.klayout.json $(REPORT_DIR)/drc.klayout.json
	cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-netgen-lvs/reports/lvs.netgen.rpt $(REPORT_DIR)/lvs.netgen.rpt
	cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-misc-reportmanufacturability/manufacturability.rpt $(REPORT_DIR)/manufacturability.rpt
.PHONY: copy-reports

copy-gds: ## Copy and compress final GDS from the last LibreLane run to layout/ (no logo & filler)
	rm -f $(LAY_DIR)/$(TOP).gds.gz
	mkdir -p $(LAY_DIR)/
	cp -r $(FLOW_FINAL_DIR)/gds/$(TOP).gds $(LAY_DIR)/$(TOP).gds
	gzip $(LAY_DIR)/$(TOP).gds
.PHONY: copy-gds

copy-netlist: ## Copy final spice, pnl and nl netlists from the last LibreLane run to netlist/
	rm -rf $(NET_SPICE_DIR)/
	mkdir -p $(NET_SPICE_DIR)/
	cp -r $(FLOW_FINAL_DIR)/spice/$(TOP).spice $(NET_SPICE_DIR)/$(TOP).spice

	rm -rf $(NET_PNL_DIR)/
	mkdir -p $(NET_PNL_DIR)/
	cp -r $(FLOW_FINAL_DIR)/pnl/$(TOP).pnl.v $(NET_PNL_DIR)/$(TOP).pnl.v

	rm -rf $(NET_NL_DIR)/
	mkdir -p $(NET_NL_DIR)/
	cp -r $(FLOW_FINAL_DIR)/nl/$(TOP).nl.v $(NET_NL_DIR)/$(TOP).nl.v
.PHONY: copy-netlist

copy-render: ## Copy chip render from the last LibreLane run (no logo & fillers) to render/img/
	mkdir -p $(RENDER_IMG_DIR)/
	cp -r $(FLOW_FINAL_DIR)/render/$(TOP).png $(RENDER_IMG_DIR)/$(TOP)_librelane.png
.PHONY: copy-render
# ================================================================================================


# Render Target
render-gds: ## Render images from the final GDS (with logo and filler) using sak-render.py
	mkdir -p $(RENDER_IMG_DIR)/
	sak-render.py -t ihp-sg13cmos5l -w 2048 -s 4 -o $(RENDER_IMG_DIR)/$(TOP) $(LAY_DIR)/$(TOP)_logo_fill.gds.gz
	sak-render.py -t ihp-sg13cmos5l -w 2048 -s 4 -b black -l tm1,tv1,TopMetal1.filler,passiv -o $(RENDER_IMG_DIR)/$(TOP)_black_TM1 $(LAY_DIR)/$(TOP)_logo_fill.gds.gz
.PHONY: render-gds
# ================================================================================================


# Build Targets
build-bondpad: ## Build the bondpad in ip/sg13cmos5l_ip__bondpad_70x70/
	@$(MAKE) -C $(IP_DIR)/sg13cmos5l_ip__bondpad_70x70 all
.PHONY: build-bondpad

build-logos: ## Build the logos in ip/sg13cmos5l_ip__jku/ and ip/sg13cmos5l_ip__jku_names/
	@$(MAKE) -C $(IP_DIR)/sg13cmos5l_ip__jku all
	@$(MAKE) -C $(IP_DIR)/sg13cmos5l_ip__jku_names all
.PHONY: build-logos

build-decimator: ## Build the standalone decimator macro (not on the die, built for its numbers)
	@$(MAKE) -C $(MACROS_DIR)/decimator all
.PHONY: build-decimator

build-dsa1-dig: ## Build the DSADC1 digital back end, the one macro on the die
	@$(MAKE) -C $(MACROS_DIR)/dsa1_dig all
.PHONY: build-dsa1-dig

build-counter: ## Build the counter macro (template archetype, not on the die)
	@$(MAKE) -C $(MACROS_DIR)/counter all
.PHONY: build-counter

build-inverter: ## Build the inverter macro (template archetype, not on the die)
	@$(MAKE) -C $(MACROS_DIR)/inverter all
.PHONY: build-inverter

# Only dsa1_dig is instantiated in the core, so only it has to be built before
# the top. The decimator, counter and inverter are kept and built on request.
build-macros: ## Build the macros the die needs (dsa1_dig)
	$(MAKE) build-dsa1-dig
.PHONY: build-macros

# Adds the chip logo and fill structures to the final GDS.
# TODO: This step is temporary and will be replaced by a custom LibreLane step in the future.
add-logo-fill: ## Run scripts/add_logo_fill.sh to add the chip logo and fill structures
	cd $(SCRIPTS_DIR) && ./add_logo_fill.sh
.PHONY: add-logo-fill

# TODO: Switch back to `make librelane` once IHP fixes the metal1_pin_offgrid errors.
build-top: ## Build the chip (LibreLane, copy reports/GDS/netlist/render, add logo & filler, render final GDS)
	$(MAKE) librelane-nodrc
	$(MAKE) copy-reports
	$(MAKE) copy-gds
	$(MAKE) copy-netlist
	$(MAKE) copy-render
	$(MAKE) add-logo-fill
	$(MAKE) render-gds
#	$(MAKE) librelane-openroad
.PHONY: build-top

build-all: ## Build the bondpad, logos, macros and the chip top-level
	$(MAKE) init-submodules
	$(MAKE) build-bondpad
	$(MAKE) build-logos
	$(MAKE) build-macros
	$(MAKE) build-top
.PHONY: build-all
# ================================================================================================


# DRC Targets
# The precheck gets its own directory: sak-drc.sh wipes <cell>.klayout.drc on
# every run, so the two levels would overwrite each other. sak-drc.sh fails on
# any marker, so the verdict comes from drc_verdict.py, which knows the 35 the
# regular deck is expected to find on this die.
DRC_EXPECT   ?= Pad.d1R=6,Pad.fR_TM1=29
PRECHECK_GDS ?= $(LAY_DIR)/$(TOP)_logo_fill.gds.gz
PRECHECK_DIR ?= $(DRC_RPT_DIR)/precheck

klayout-drc-minimum: ## Run minimum pre-check KLayout DRC, into its own directory (usage: make klayout-drc-minimum [PRECHECK_GDS=<file>] [PRECHECK_DIR=<dir>])
	mkdir -p $(PRECHECK_DIR)
	-sak-drc.sh -d -k -l precheck -w $(PRECHECK_DIR) $(PRECHECK_GDS)
	python3 scripts/drc_verdict.py $(PRECHECK_DIR)/$(basename $(basename $(notdir $(PRECHECK_GDS)))).klayout.drc --no-density \
		--out $(PRECHECK_DIR)/$(basename $(basename $(notdir $(PRECHECK_GDS)))).klayout.drc/verdict.txt
.PHONY: klayout-drc-minimum

klayout-drc-regular: ## Run regular KLayout DRC of the TOP cell with logo and filler, expecting exactly DRC_EXPECT
	mkdir -p $(DRC_RPT_DIR)
	-sak-drc.sh -d -k -l regular -w $(DRC_RPT_DIR) $(LAY_DIR)/$(TOP)_logo_fill.gds.gz
	python3 scripts/drc_verdict.py $(DRC_RPT_DIR)/$(TOP)_logo_fill.klayout.drc --expect $(DRC_EXPECT) \
		--out $(DRC_RPT_DIR)/$(TOP)_logo_fill.klayout.drc/verdict.txt
.PHONY: klayout-drc-regular

klayout-drc: ## Run KLayout DRC of the CELL cell (usage: make klayout-drc [CELL=<cellname>] [DRC_LEVEL=<precheck|macro|regular>])
	mkdir -p $(DRC_RPT_DIR)
	sak-drc.sh -d -k -l $(DRC_LEVEL) -w $(DRC_RPT_DIR) $(LAY_DIR)/$(CELL).gds.gz
.PHONY: klayout-drc

magic-drc: ## Run Magic DRC of the CELL cell (usage: make magic-drc [CELL=<cellname>])
	mkdir -p $(DRC_RPT_DIR)
	sak-drc.sh -d -m -w $(DRC_RPT_DIR) $(LAY_DIR)/$(CELL).gds.gz
	@r=$(DRC_RPT_DIR)/$(CELL).magic.drc; grep -h 'COUNT:' $$r/$(CELL).magic.drc.rpt && \
		grep -q '^\[INFO\] COUNT: 0$$' $$r/$(CELL).magic.drc.rpt && test ! -e $$r/drc_$(CELL).cellmismatch && \
		echo "PASS: Magic DRC of $(CELL)"
.PHONY: magic-drc

gds-scan: ## Fail on degenerate paths and zero-area shapes in a GDS (usage: make gds-scan [PRECHECK_GDS=<file>])
	python3 scripts/scan_gds.py $(PRECHECK_GDS)
.PHONY: gds-scan

mpw-precheck: klayout-drc-minimum gds-scan ## The foundry precheck of the delivery GDS: minimum DRC and the shape scan (usage: make mpw-precheck [PRECHECK_GDS=<file>] [PRECHECK_DIR=<dir>])
.PHONY: mpw-precheck

# Average currents for the current-density table, in mA, each an upper bound.
# VDD and VSS: the STA's vectorless estimate at the SDC clock rates, without the
# pad group, is 0.236 mA at the fast corner. Real activity is under 10 uA.
# IOVDD and IOVSS: 20 pF x 3.3 V x 100 kHz on miso, rounded up. Their ring is
# inside the pad cells, so they are listed, not rated.
# The clock tree: 5 pF x 1.2 V x 65536 Hz per net. miso inside the core: 1 pF x 1.2 V x 100 kHz.
# VDDA: dsm2 has no supply current figure yet, 1 mA is a placeholder for its strap on Metal3 (10 um wide, rated 20 mA).
EM_CURRENTS ?= --current VDD=0.25 --current VSS=0.25 --current VDDA=1 --current IOVDD=1 --current IOVSS=1 \
	--signal '*clk_PAD*=0.0004' --signal 'i_sg13cmos5l_dsa1_dig_core.miso=0.00012'

em-probe: ## Current density of the supply, clock and miso nets from the final DEF, into verification/em/
	mkdir -p verification/em
	python3 scripts/em_probe.py $(FLOW_FINAL_DIR)/def/$(TOP).def --lef $(EZ130_DIR)/lef/ez130_tech.lef \
		$(EM_CURRENTS) --out verification/em/em_table.md
.PHONY: em-probe
# ================================================================================================


# LVS Targets
schematic: ## Regenerate the top-level Xschem schematic from the pad plan
	python3 $(SCRIPTS_DIR)/gen_chip_schematic.py
	python3 $(MACROS_DIR)/dsa1_dig/scripts/verilog2sym.py $(NET_PNL_DIR)/$(TOP).pnl.v $(XSCHEM_SCH_DIR)/$(TOP).sym --check
.PHONY: schematic

klayout-lvs-netlist: ## Export CDL schematic netlist from Xschem for KLayout LVS (usage: make klayout-lvs-netlist [CELL=<cellname>] [EV_PRECISION=<digits>])
	mkdir -p $(NET_SCH_DIR)
	xschem -s -r -x -q --rcfile $(XSCHEM_SCH_DIR)/xschemrc --command ' \
		set spiceprefix 1; \
		set lvs_netlist 1; \
		set top_is_subckt 1; \
		set lvs_ignore 1; \
		set ev_precision $(EV_PRECISION); \
		set netlist_dir $(NET_SCH_DIR); \
		xschem set netlist_name [file tail [file rootname [xschem get current_name]]]_klayout.cdl; \
		xschem netlist \
	' $(XSCHEM_SCH_DIR)/$(CELL).sch
.PHONY: klayout-lvs-netlist

klayout-lvs: ## Run KLayout LVS of the CELL cell (usage: make klayout-lvs [CELL=<cellname>])
	$(MAKE) klayout-lvs-netlist CELL=$(CELL)
	mkdir -p $(LVS_RPT_DIR)
	mkdir -p $(NET_LAY_DIR)
	sak-lvs.sh -d -k -w $(LVS_RPT_DIR) -s $(NET_SCH_DIR)/$(CELL)_klayout.cdl -l $(LAY_DIR)/$(CELL).gds.gz -c $(CELL)
	mv $(LVS_RPT_DIR)/$(CELL).klayout.lvs/$(CELL)_extracted.cir $(NET_LAY_DIR)/$(CELL)_klayout.cir
.PHONY: klayout-lvs

magic-lvs-netlist: ## Export SPICE schematic netlist from Xschem for Magic + Netgen LVS (usage: make magic-lvs-netlist [CELL=<cellname>] [EV_PRECISION=<digits>])
	mkdir -p $(NET_SCH_DIR)
	xschem -s -r -x -q --rcfile $(XSCHEM_SCH_DIR)/xschemrc --command ' \
		set spiceprefix 1; \
		set lvs_netlist 0; \
		set top_is_subckt 1; \
		set lvs_ignore 1; \
		set ev_precision $(EV_PRECISION); \
		set netlist_dir $(NET_SCH_DIR); \
		xschem set netlist_name [file tail [file rootname [xschem get current_name]]]_magic.spice; \
		xschem netlist \
	' $(XSCHEM_SCH_DIR)/$(CELL).sch
.PHONY: magic-lvs-netlist

magic-lvs: ## Run Magic + Netgen LVS of the CELL cell (usage: make magic-lvs [CELL=<cellname>])
	mkdir -p $(LVS_RPT_DIR)
	mkdir -p $(NET_LAY_DIR)
	$(MAKE) magic-lvs-netlist CELL=$(CELL)
	sak-lvs.sh -d -w $(LVS_RPT_DIR) -s $(NET_SCH_DIR)/$(CELL)_magic.spice -l $(LAY_DIR)/$(CELL).gds.gz -c $(CELL)
	mv $(LVS_RPT_DIR)/$(CELL).magic.lvs/$(CELL).ext.spc $(NET_LAY_DIR)/$(CELL)_magic.ext.spc
.PHONY: magic-lvs
# ================================================================================================


# PEX Targets
symbol-pex: ## Build the Xschem PEX symbol <CELL>_pex.sym from <CELL>.sym (usage: make symbol-pex [CELL=<cellname>])
	@if [ ! -f $(XSCHEM_SCH_DIR)/$(CELL).sym ]; then \
		echo "No symbol $(XSCHEM_SCH_DIR)/$(CELL).sym found, skipping PEX symbol generation."; \
	else \
		sed 's/type=subcircuit/type=primitive/' $(XSCHEM_SCH_DIR)/$(CELL).sym > $(XSCHEM_SCH_DIR)/$(CELL)_pex.sym; \
		if ! grep -q 'type=primitive' $(XSCHEM_SCH_DIR)/$(CELL)_pex.sym; then \
			rm -f $(XSCHEM_SCH_DIR)/$(CELL)_pex.sym; \
			echo "ERROR: $(XSCHEM_SCH_DIR)/$(CELL).sym declares neither type=subcircuit nor type=primitive!"; \
			exit 1; \
		fi; \
		python3 $(SCRIPTS_DIR)/prune_pex_symbol.py $(XSCHEM_SCH_DIR)/$(CELL)_pex.sym --merged $(PEX_MERGED_PINS); \
		echo "Wrote $(XSCHEM_SCH_DIR)/$(CELL)_pex.sym (copy of $(CELL).sym with type=primitive)."; \
	fi
.PHONY: symbol-pex

check-ports: ## Compare the pins of <CELL>.sym with the ports of the layout SPICE netlist (usage: make check-ports [CELL=<cellname>])
	python3 $(SCRIPTS_DIR)/check_top_ports.py $(XSCHEM_SCH_DIR)/$(CELL).sym $(NET_SPICE_DIR)/$(CELL).spice
.PHONY: check-ports

klayout-pex: ## Run Parasitic Extraction with KPEX of the CELL cell (usage: make klayout-pex [CELL=<cellname>] [EXT_MODE=<1|2|3>])
	mkdir -p $(NET_PEX_DIR)
	$(MAKE) symbol-pex CELL=$(CELL)
	$(MAKE) check-ports CELL=$(CELL)
	PDK_UNDERSCORED=$$(echo $$PDK | sed -e 's/-/_/g'); \
	case $(EXT_MODE) in \
		1) echo "WARNING: KPEX does not support C-decoupled (C) mode yet, using C-coupled (CC) mode instead."; KPEX_MODE=CC ;; \
		2) KPEX_MODE=CC ;; \
		3) KPEX_MODE=RC ;; \
		*) echo "Invalid EXT_MODE: $(EXT_MODE). Use 1, 2, or 3."; exit 1;; \
	esac; \
	kpex \
	--pdk $$PDK_UNDERSCORED \
	--cell $(CELL) \
	--schematic $(XSCHEM_SCH_DIR)/$(CELL).sch \
	--gds $(LAY_DIR)/$(CELL).gds.gz \
	--magic \
	--magic_mode $$KPEX_MODE \
	--out_dir $(NET_PEX_DIR) \
	--out_spice $(NET_PEX_DIR)/$(CELL)_klayout_pex_$(EXT_MODE).spice
#	--2.5D
#	--mode $$KPEX_MODE
	sed -i 's/$(CELL)/$(CELL)_pex/g' $(NET_PEX_DIR)/$(CELL)_klayout_pex_$(EXT_MODE).spice
	rm -rf $(NET_PEX_DIR)/$(CELL)__$(CELL)
	rm -f $(CELL).nodes $(CELL).sim
	@if [ -f $(XSCHEM_SCH_DIR)/$(CELL)_pex.sym ]; then \
		echo "Reordering pins in $(CELL)_klayout_pex_$(EXT_MODE).spice to match $(CELL)_pex.sym..."; \
		sak-pin-reorder.py $(XSCHEM_SCH_DIR)/$(CELL)_pex.sym $(NET_PEX_DIR)/$(CELL)_klayout_pex_$(EXT_MODE).spice --format spice; \
	else \
		echo "No symbol $(XSCHEM_SCH_DIR)/$(CELL)_pex.sym found, skipping pin reorder."; \
	fi
	python3 $(SCRIPTS_DIR)/check_pex_ports.py $(NET_PEX_DIR)/$(CELL)_klayout_pex_$(EXT_MODE).spice
.PHONY: klayout-pex

magic-pex: ## Run Parasitic Extraction with Magic of the CELL cell (usage: make magic-pex [CELL=<cellname>] [EXT_MODE=<1|2|3>] [THRESHOLD=<mOhm>] [MINRES=<mOhm>] [MINDELAY=<ps>])
	mkdir -p $(NET_PEX_DIR)
	$(MAKE) symbol-pex CELL=$(CELL)
	$(MAKE) check-ports CELL=$(CELL)
	sak-pex.sh -d -m $(EXT_MODE) -n $(CELL)_pex -t $(THRESHOLD) -r $(MINRES) -y $(MINDELAY) -w $(NET_PEX_DIR) $(LAY_DIR)/$(CELL).gds.gz
	mv $(NET_PEX_DIR)/$(CELL).pex.spice $(NET_PEX_DIR)/$(CELL)_magic_pex_$(EXT_MODE).spice
	rm -f $(NET_PEX_DIR)/pex_$(CELL).tcl
	@if [ -f $(XSCHEM_SCH_DIR)/$(CELL)_pex.sym ]; then \
		echo "Reordering pins in $(CELL)_magic_pex_$(EXT_MODE).spice to match $(CELL)_pex.sym..."; \
		sak-pin-reorder.py $(XSCHEM_SCH_DIR)/$(CELL)_pex.sym $(NET_PEX_DIR)/$(CELL)_magic_pex_$(EXT_MODE).spice --format spice; \
	else \
		echo "No symbol $(XSCHEM_SCH_DIR)/$(CELL)_pex.sym found, skipping pin reorder."; \
	fi
	python3 $(SCRIPTS_DIR)/check_pex_ports.py $(NET_PEX_DIR)/$(CELL)_magic_pex_$(EXT_MODE).spice
.PHONY: magic-pex
# ================================================================================================


# Verify Targets
klayout-verify: ## Verify CELL cell with KLayout (usage: make klayout-verify [CELL=<cellname>])
	$(MAKE) klayout-drc CELL=$(CELL)
	$(MAKE) klayout-lvs CELL=$(CELL)
#	$(MAKE) klayout-pex CELL=$(CELL)
.PHONY: klayout-verify

magic-verify: ## Verify CELL cell with Magic (usage: make magic-verify [CELL=<cellname>])
	$(MAKE) magic-drc CELL=$(CELL)
	$(MAKE) magic-lvs CELL=$(CELL)
	$(MAKE) magic-pex CELL=$(CELL)
.PHONY: magic-verify
# ================================================================================================


# Packaging Target
bondplan: ## Generate the bondplan (die in package + bondwires + pin table) in packaging/ (usage: make bondplan [VERSION=<version>])
	cd $(PACKAGING_DIR) && python3 scripts/run_bondplan.py config.yaml VERSION=$(VERSION)
.PHONY: bondplan
# ================================================================================================


# Build, Verify, Simulate and Package All Target
all: ## Build, verify, simulate and package the whole chip
	$(MAKE) build-all
	$(MAKE) magic-drc CELL=$(TOP)
	$(MAKE) magic-drc CELL=$(TOP)_logo_fill
#	$(MAKE) klayout-verify
#	$(MAKE) magic-verify
	$(MAKE) sim-all
	$(MAKE) bondplan
.PHONY: all
# ================================================================================================


# Release Target
release: ## Copy the gds, netlist files and chip renders to the release folder (usage: make release VERSION=<version>)
	mkdir -p $(RELEASE_DIR)/v.$(VERSION)/gds
	mkdir -p $(RELEASE_DIR)/v.$(VERSION)/netlist
	mkdir -p $(RELEASE_DIR)/v.$(VERSION)/img
	cp -f $(LAY_DIR)/$(TOP)_logo_fill.gds.gz $(RELEASE_DIR)/v.$(VERSION)/gds/$(TOP)_logo_fill.gds.gz
	cp -r $(NET_SCH_DIR)/. $(RELEASE_DIR)/v.$(VERSION)/netlist/schematic
	cp -r $(NET_LAY_DIR)/. $(RELEASE_DIR)/v.$(VERSION)/netlist/layout
	cp -r $(NET_PNL_DIR)/. $(RELEASE_DIR)/v.$(VERSION)/netlist/pnl
	cp -r $(NET_SPICE_DIR)/. $(RELEASE_DIR)/v.$(VERSION)/netlist/spice
	cp -f $(RENDER_IMG_DIR)/$(TOP)_black.png $(RELEASE_DIR)/v.$(VERSION)/img/$(TOP)_black.png
	cp -f $(RENDER_IMG_DIR)/$(TOP)_white.png $(RELEASE_DIR)/v.$(VERSION)/img/$(TOP)_white.png
	cp -f $(RENDER_IMG_DIR)/$(TOP)_black_TM1.png $(RELEASE_DIR)/v.$(VERSION)/img/$(TOP)_black_TM1.png
	cp -f $(RENDER_IMG_DIR)/$(TOP)_librelane.png $(RELEASE_DIR)/v.$(VERSION)/img/$(TOP)_librelane.png
	cp -f $(PACKAGING_RENDER_DIR)/*_bondplan_black.png $(RELEASE_DIR)/v.$(VERSION)/img/
	cp -f $(PACKAGING_RENDER_DIR)/*_bondplan_white.png $(RELEASE_DIR)/v.$(VERSION)/img/
	mkdir -p $(RELEASE_DIR)/v.$(VERSION)/packaging
	cp -f $(PACKAGING_DIR)/layout/$(TOP)_bondplan.gds $(PACKAGING_DIR)/result.md $(RELEASE_DIR)/v.$(VERSION)/packaging/
.PHONY: release
# ================================================================================================


# Regression Target
regression: ## Regression test target for IIC-OSIC-TOOLS
# 	Analog macro: inverter (Xschem + CACE + DRC/LVS/PEX + build-top)
	$(MAKE) -C $(MACROS_DIR)/inverter sim-xschem TB=inverter_tb_dc_vout
# 	ONE CACE run: the lightweight AC VDD sweep (no Monte-Carlo) to keep runtime short.
	cd $(MACROS_DIR)/inverter/verification/cace && cace inverter.yaml -p ac_params && rm -rf _runs _docs netlist
# 	KLayout & Magic DRC, LVS and PEX of the inverter_top cell.
	$(MAKE) -C $(MACROS_DIR)/inverter klayout-verify CELL=inverter_top
	$(MAKE) -C $(MACROS_DIR)/inverter magic-verify CELL=inverter_top
	$(MAKE) -C $(MACROS_DIR)/inverter build-top

# 	Digital macro: counter (Verilator, Icarus, cocotb, yosys/FPGA, LibreLane, xspice)
	$(MAKE) -C $(MACROS_DIR)/counter lint-verilog-all
	$(MAKE) -C $(MACROS_DIR)/counter sim-rtl-verilog
	$(MAKE) -C $(MACROS_DIR)/counter sim-rtl-cocotb
	$(MAKE) -C $(MACROS_DIR)/counter build-fpga
# 	librelane-magicdrc: full RTL-to-GDS. KLayout DRC skipped for runtime.
	$(MAKE) -C $(MACROS_DIR)/counter librelane-magicdrc
	$(MAKE) -C $(MACROS_DIR)/counter copy-final
# 	Gate-level flows that depend on the LibreLane outputs above.
	$(MAKE) -C $(MACROS_DIR)/counter sim-gl-cocotb
	$(MAKE) -C $(MACROS_DIR)/counter generate-xspice
	$(MAKE) -C $(MACROS_DIR)/counter sim-gl-xschem

# 	Top-level assembly
	$(MAKE) init-submodules
	$(MAKE) build-bondpad
	$(MAKE) -C $(IP_DIR)/sg13cmos5l_ip__jku all
# 	librelane-nodrc: full RTL-to-GDS. DRC is skipped for runtime.
	$(MAKE) librelane-nodrc
.PHONY: regression
# ================================================================================================


# Clean Targets
clean: ## Delete all generated chip top-level files and folders (LibreLane runs, layout, netlists, render, reports, simulation and packaging outputs)
	rm -rf $(LIBRELANE_DIR)/runs $(FLOW_FINAL_DIR)
	rm -rf $(LAY_DIR)
	rm -rf $(NET_SCH_DIR) $(NET_LAY_DIR) $(NET_PEX_DIR) $(NET_PNL_DIR) $(NET_NL_DIR) $(NET_SPICE_DIR)
	rm -rf $(RENDER_IMG_DIR)
	rm -rf $(DRC_RPT_DIR) $(LVS_RPT_DIR) $(REPORT_DIR)
	rm -rf $(XSCHEM_SCH_DIR)/simulations $(XSCHEM_TB_DIR)/simulations
	rm -rf $(SIM_PLOT_DIR)/data $(SIM_PLOT_DIR)/figures $(SIM_PLOT_DIR)/__pycache__
	rm -rf $(COCOTB_DIR)/sim_build
	rm -rf $(SCRIPTS_DIR)/__pycache__ $(COCOTB_DIR)/__pycache__ $(PACKAGING_DIR)/scripts/__pycache__
	rm -rf $(PACKAGING_RENDER_DIR)
	rm -f $(PACKAGING_DIR)/result.md
	rm -f $(PACKAGING_DIR)/layout/$(TOP)_bondplan.gds $(PACKAGING_DIR)/layout/$(TOP)_logo_TM1.gds.gz
	rm -f $(PACKAGING_DIR)/layout/$(PACKAGE_NAME).gds
.PHONY: clean

clean-all: ## Delete all generated files of the chip top-level, the IPs and the macros
	$(MAKE) clean
	$(MAKE) -C $(IP_DIR)/sg13cmos5l_ip__bondpad_70x70 clean
	$(MAKE) -C $(IP_DIR)/sg13cmos5l_ip__jku clean
	$(MAKE) -C $(IP_DIR)/sg13cmos5l_ip__jku_names clean
	$(MAKE) -C $(MACROS_DIR)/decimator clean
	$(MAKE) -C $(MACROS_DIR)/dsa1_dig clean
	$(MAKE) -C $(MACROS_DIR)/counter clean
	$(MAKE) -C $(MACROS_DIR)/inverter clean
.PHONY: clean-all
# ================================================================================================
