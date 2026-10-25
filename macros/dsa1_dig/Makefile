# SPDX-FileCopyrightText: 2026 Simon Dorrer and Harald Pretl
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1

MAKEFILE_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

RUN_TAG = $(shell ls -1 $(LIBRELANE_DIR)/runs 2>/dev/null | tail -n 1)

# Variables
TOP = dsa1_dig_top

.DEFAULT_GOAL := help

# PDK Guard
# Override with: make <target> REQUIRED_PDK=<pdk>, an empty value skips the check
REQUIRED_PDK ?= ihp-sg13cmos5l

# Goals that do not read the PDK
PDK_FREE_GOALS = help clean lint-vhdl

ifneq ($(REQUIRED_PDK),)
ifneq ($(filter-out $(PDK_FREE_GOALS),$(or $(MAKECMDGOALS),$(.DEFAULT_GOAL))),)
ifneq ($(PDK),$(REQUIRED_PDK))
$(error PDK is "$(PDK)", but this macro needs "$(REQUIRED_PDK)". Run `sak-pdk $(REQUIRED_PDK)` in this shell and retry, or pass REQUIRED_PDK= to skip this check)
endif
endif
endif
# ================================================================================================


# EZ130 8T standard cells and the thick-oxide decoupling. Both are read in
# place from outside this repo: EZ130 is a prerelease and does not ship here.
# librelane_scl.py writes a copy of the library's LibreLane fragment with every
# dir:: made absolute and prints its path, which has to come FIRST on the
# librelane command line. Without it the run silently hardens on the PDK's own
# sg13cmos5l_stdcell.
EZ130_DIR   ?= $(HOME)/projects/OpenBLAU/ip/ez130_8t_v1p1
DECAPHV_DIR ?= $(HOME)/projects/OpenBLAU/ip/ez130_8t_decap_hv
EZ130_SCL    = $(shell python3 $(EZ130_DIR)/scripts/librelane_scl.py $(LIBRELANE_DIR))
# The decap fragment must follow the SCL fragment and precede the design
# config: it rewrites LIB to carry both liberties per corner, and a later
# file replaces that key rather than merging into it.
DECAP_FRAG   = $(shell python3 ../scripts/decaphv_frag.py --ez130 $(EZ130_DIR) --decap $(DECAPHV_DIR) $(LIBRELANE_DIR))

check-ez130: ## Fail early if EZ130_DIR does not hold the cell library
	@test -f $(EZ130_DIR)/scripts/librelane_scl.py || \
		{ echo "EZ130_DIR is '$(EZ130_DIR)', which has no scripts/librelane_scl.py. Point it at the ez130_8t_v1p1 checkout."; exit 1; }
	@test -f $(DECAPHV_DIR)/lef/ez130_8t_decap_hv.lef || \
		{ echo "DECAPHV_DIR is '$(DECAPHV_DIR)', which has no lef/ez130_8t_decap_hv.lef. Point it at the ez130_8t_decap_hv checkout."; exit 1; }
.PHONY: check-ez130

# Cells that must never reach a netlist. CGTSX* is inverted in silicon and
# DFFRQ2X*/DFFRQ4X* simulate as x, see the library's own README.
BANNED_CELLS := DECAP4 DECAP8 DECAP16 DECAP32 CGTSX1 CGTSX1P5 CGTSX2 CGTSX3 DFFRQ2X1 DFFRQ2X1P5 DFFRQ2X2 DFFRQ2X3 DFFRQ4X1 DFFRQ4X1P5 DFFRQ4X2 DFFRQ4X3 BUFX1 BUFX2 DLY1X2

# EZ130 is characterised at three corners only, so the six-corner list the
# template uses does not apply. Keep this in step with STA_CORNERS in
# flow/librelane/config.yaml.
STA_CORNERS := nom_fast_1p32V_m40C nom_slow_1p08V_125C nom_typ_1p20V_25C

# Cell name for verification targets (default: top-level cell)
# Override with: make <target> CELL=<cellname>
CELL ?= $(TOP)

# PEX mode (1 = C-decoupled, 2 = C-coupled, 3 = full-RC)
# Override with: make <target> EXT_MODE=<1|2|3>
EXT_MODE ?= 3

# full-RC extresist threshold in mOhm (sak-pex.sh -t, only used in EXT_MODE=3; default: 10000 = 10 Ohm)
# Override with: make <target> THRESHOLD=<mOhm>
THRESHOLD ?= 10000

# full-RC extresist minres in mOhm (sak-pex.sh -r, only used in EXT_MODE=3; default: 1000 = 1 Ohm)
# Override with: make <target> MINRES=<mOhm>
MINRES ?= 1000

# full-RC extresist mindelay in ps (sak-pex.sh -y, only used in EXT_MODE=3; default: 1; 0 = gate by resistance)
# Override with: make <target> MINDELAY=<ps>
MINDELAY ?= 1

# Floating-point precision (significant digits) for xschem's ev function
# Override with: make <target> EV_PRECISION=<digits>
EV_PRECISION ?= 5

# Set the waveform viewer GTKWave or Surfer (default: gtkwave)
# Override with: make <target> WAVEFORM_VIEWER=<gtkwave|surfer>
WAVEFORM_VIEWER ?= gtkwave

# Extra options for the sak-open.py file browser (e.g. --all to include build outputs)
# Override with: make open OPEN_ARGS=<options>
OPEN_ARGS ?=

# Folder structure
COCOTB_DIR      := testbenches/cocotb
VERILOG_TB_DIR 	:= testbenches/verilog
XSCHEM_TB_DIR  	:= testbenches/xschem
XSCHEM_SCH_DIR  := schematic/xschem
SCRIPTS_DIR   	:= scripts
SIM_PLOT_DIR  	:= testbenches/xschem/plot_simulations
RENDER_IMG_DIR 	:= render/img
REPORT_DIR     	:= verification
SRC_DIR 		:= rtl
NET_NL_DIR    	:= netlist/nl
NET_PNL_DIR  	:= netlist/pnl
NET_SPICE_DIR 	:= netlist/spice
XSPICE_DIR  	:= netlist/xspice
NET_PEX_DIR   	:= netlist/pex
LIBRELANE_DIR 	:= flow/librelane
FLOW_FINAL_DIR 	:= flow/final
FINAL_DIR      	:= final
LAY_DIR        	:= final/gds

# Variables for simulation and linting targets
# constants.sv defines the `DECIMATOR_MAX_DEFAULT / `CLK_FREQ_DEFAULT macros and must
# compile before any module that references them, so it is the first entry in MODULES_SIM
# and in both branches of _SIM_SRCS / _LINT_SRCS below (Yosys 0.64 cannot parse
# `import pkg::*` in a module header, see rtl/constants.sv).
# LibreLane reads one language per run, so rtl-gen turns the VHDL into Verilog
# with ghdl synth first (decimator_top is left unbound) and the yosys pre-pass
# then clock-gates that together with the decimator RTL.
VHDL_SRCS := \
	$(SRC_DIR)/dsa1_regs.vhd \
	$(SRC_DIR)/dsa1_ic_bus_slave.vhd \
	$(SRC_DIR)/dsa1_dig_top.vhd

# The decimator RTL is the sibling macro's, one copy for both. Listed, not
# globbed, so the order is the same every run: the yosys pre-pass emits its
# netlist in source order and ABC maps that order differently, which moves the
# mapped area by about 1 % with no design change.
DEC_SRCS := \
	../decimator/rtl/ce_generator.sv \
	../decimator/rtl/cic_n6_d32.sv \
	../decimator/rtl/sinc2_chain.sv \
	../decimator/rtl/comp_fir.sv \
	../decimator/rtl/decimator_core.sv \
	../decimator/rtl/decimator_top.sv

RTL_GEN_DIR := rtl_gen
RTL_GEN     := $(RTL_GEN_DIR)/$(TOP).v
RTL_CG      := $(RTL_GEN_DIR)/$(TOP)_cg.v
MODULES_SYNTH := $(RTL_GEN) $(DEC_SRCS)
MODULES_SIM   := $(MODULES_SYNTH)

# Source files for sim-rtl-verilog: auto-selects MODULES_SIM when CELL == TOP, constants.sv + single-file otherwise (auto-detecting .sv/.v)
_SIM_SRCS = $(if $(filter $(CELL),$(TOP)),$(MODULES_SIM),$(SRC_DIR)/constants.sv $(or $(wildcard $(SRC_DIR)/$(CELL).sv),$(SRC_DIR)/$(CELL).v))

# Source files for lint-verilog: constants + all synthesis sources for TOP, constants.sv + single-file (auto-detecting .sv/.v) otherwise
_LINT_SRCS = $(if $(filter $(CELL),$(TOP)),$(SRC_DIR)/constants.sv $(MODULES_SYNTH),$(SRC_DIR)/constants.sv $(or $(wildcard $(SRC_DIR)/$(CELL).sv),$(SRC_DIR)/$(CELL).v))

# Testbench extension: prefers <CELL>_tb.sv, falls back to <CELL>_tb.v (dot is added at use site)
_TB_EXT = $(if $(wildcard $(VERILOG_TB_DIR)/$(CELL)_tb.sv),sv,v)


# Help Target
help: ## Show this help message
	@echo 'Usage: make <target> [CELL=<cellname>] [EXT_MODE=<1|2|3>] [THRESHOLD=<mOhm>] [MINRES=<mOhm>] [MINDELAY=<ps>] [WAVEFORM_VIEWER=<gtkwave|surfer>] [TB=<testbenchname>] [SCRIPT=<scriptname>] [OPEN_ARGS=<options>] [FORCE=1]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z0-9_.-]+:.*## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-20s %s\n", $$1, $$2}'
	@echo ''
	@echo 'CELL defaults to $(TOP). Override to lint or simulate subcells.'
	@echo 'EXT_MODE defaults to 3 (full-RC). 1=C-decoupled, 2=C-coupled.'
	@echo 'THRESHOLD/MINRES/MINDELAY are full-RC (EXT_MODE=3) extresist settings for magic-pex (defaults 10000 mOhm / 1000 mOhm / 1 ps).'
	@echo 'WAVEFORM_VIEWER defaults to gtkwave. Use surfer to launch Surfer instead.'
	@echo 'TB selects the Xschem testbench for sim-gl-xschem (default: <CELL>_tb_tran).'
	@echo 'SCRIPT selects the plotting script for sim-view-xschem (default: plot_<CELL>).'
	@echo 'OPEN_ARGS passes extra options to sak-open.py for the open target (e.g. --all).'
	@echo 'FORCE=1 lets symbol-gl overwrite an existing symbol instead of refusing.'
	@echo 'REQUIRED_PDK defaults to $(REQUIRED_PDK). Every target except help and clean aborts if $$PDK differs.'
.PHONY: help
# ================================================================================================


# Open Target
open: ## Open the design files of this folder in the sak-open.py file browser (needs the VNC/X11 desktop)
	sak-open.py $(OPEN_ARGS) .
.PHONY: open
# ================================================================================================


# RTL Generation Target
# The yosys pre-pass has to know the EZ130 liberty, which lives outside this
# repo, so the script is resolved into rtl_gen/ rather than run in place.
CG_YS      := ../scripts/clockgate_pre_$(TOP:_top=).ys
EZ130_LIB   = $(EZ130_DIR)/lib/ez130_8t_tt_1p20v_25c.lib

$(RTL_GEN): $(VHDL_SRCS)
	mkdir -p $(RTL_GEN_DIR)/work
	ghdl synth --std=08 --workdir=$(RTL_GEN_DIR)/work --out=verilog $(VHDL_SRCS) -e $(TOP) > $@.tmp
	mv $@.tmp $@

lint-vhdl: ## Analyze the VHDL sources with GHDL
	mkdir -p $(RTL_GEN_DIR)/work
	ghdl -a --std=08 --workdir=$(RTL_GEN_DIR)/work $(VHDL_SRCS)
.PHONY: lint-vhdl

$(RTL_CG): $(RTL_GEN) $(DEC_SRCS) $(CG_YS) ../scripts/sdffe_to_dffe.v | check-ez130
	mkdir -p $(RTL_GEN_DIR)
	sed 's|@EZ130_LIB@|$(EZ130_LIB)|' $(CG_YS) > $(RTL_GEN_DIR)/clockgate_pre.ys
	yosys -q -l $(RTL_GEN_DIR)/clockgate_pre.log -s $(RTL_GEN_DIR)/clockgate_pre.ys
	@grep -A1 "Executing CLOCK_GATE" $(RTL_GEN_DIR)/clockgate_pre.log | tail -1

rtl-gen: $(RTL_CG) ## ghdl synth the VHDL, then clock-gate it with the yosys pre-pass, into rtl_gen/
.PHONY: rtl-gen

check-netlist: ## Fail if any cell that is wrong in silicon reached the final netlist
	@test -f $(FINAL_DIR)/nl/$(TOP).nl.v || { echo "No $(FINAL_DIR)/nl/$(TOP).nl.v. Run 'make build-top' first."; exit 1; }
	@bad=0; for c in $(BANNED_CELLS); do \
		if grep -q " $$c " $(FINAL_DIR)/nl/$(TOP).nl.v; then echo "BANNED CELL in netlist: $$c"; bad=1; fi; \
	done; test $$bad -eq 0 && echo "OK: no banned cell in $(FINAL_DIR)/nl/$(TOP).nl.v"
.PHONY: check-netlist
# ================================================================================================


# Linter Targets
lint-verilog: ## Lint Verilog source files with Verilator (usage: make lint-verilog [CELL=<cellname>])
	verilator --lint-only -I"$(SRC_DIR)" $(_LINT_SRCS)
.PHONY: lint-verilog

lint-verilog-all: ## Lint all Verilog source files (decimator, dsa1_dig_top)
	$(MAKE) lint-verilog CELL=decimator
	$(MAKE) lint-verilog
.PHONY: lint-verilog-all
# ================================================================================================


# Simulation Targets
# Testbench for the Xschem simulation targets (default: <CELL>_tb_tran)
# Override with: make <target> TB=<testbenchname>
TB ?= $(CELL)_tb_tran
# Plotting script for sim-view-xschem (default: plot_<CELL>)
# Override with: make <target> SCRIPT=<scriptname>
SCRIPT ?= plot_$(CELL)

sim-rtl-verilog: ## Run RTL simulation of CELL cell with Icarus Verilog (usage: make sim-rtl-verilog [CELL=<cellname>])
	iverilog -g2012 -DSIM -o $(VERILOG_TB_DIR)/test_$(CELL) $(_SIM_SRCS) $(VERILOG_TB_DIR)/$(CELL)_tb.$(_TB_EXT)
	cd $(VERILOG_TB_DIR) && vvp test_$(CELL)
	rm -f $(VERILOG_TB_DIR)/test_$(CELL)
.PHONY: sim-rtl-verilog

sim-view-verilog: ## View CELL cell Verilog simulation waveforms (usage: make sim-view-verilog [CELL=<cellname>] [WAVEFORM_VIEWER=<gtkwave|surfer>])
	@if [ "$(WAVEFORM_VIEWER)" = "gtkwave" ]; then \
		$(WAVEFORM_VIEWER) $(VERILOG_TB_DIR)/$(CELL)_tb.vcd $(VERILOG_TB_DIR)/$(CELL)_tb.gtkw; \
	elif [ "$(WAVEFORM_VIEWER)" = "surfer" ]; then \
		$(WAVEFORM_VIEWER) -s $(VERILOG_TB_DIR)/$(CELL)_tb.surf.ron $(VERILOG_TB_DIR)/$(CELL)_tb.vcd; \
	else \
		$(WAVEFORM_VIEWER) $(VERILOG_TB_DIR)/$(CELL)_tb.vcd; \
	fi
.PHONY: sim-view-verilog

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

sim-all: ## Simulate the macro (RTL Verilog + RTL/GL cocotb + GL Xschem for dsa1_dig_top)
	$(MAKE) sim-rtl-verilog
	$(MAKE) sim-rtl-cocotb
	$(MAKE) sim-gl-cocotb
	$(MAKE) sim-gl-xschem
.PHONY: sim-all
# ================================================================================================


# Gate-level equality
# EZ130's Verilog models and the empty stubs for its LEF-only cells (FILLER*,
# WELLTAP), which a gate-level netlist needs in order to elaborate.
SCL_VERILOG := $(EZ130_DIR)/verilog/ez130_8t.v
SCL_STUBS   := ../scripts/ez130_phys_stubs.v
SIM_DIR     := sims

# Depends on the ghdl-synth Verilog: MODULES_SIM is only expanded inside the
# recipe, so without this the sim happily runs a stale netlist.
sim-rtl-out: $(RTL_GEN) ## Simulate the RTL and write $(TOP)_out.txt into sims/rtl
	mkdir -p $(SIM_DIR)/rtl
	iverilog -g2012 -Irtl -o $(SIM_DIR)/rtl/tb.vvp $(MODULES_SIM) $(VERILOG_TB_DIR)/$(TOP)_tb.v
	cd $(SIM_DIR)/rtl && vvp -n tb.vvp
.PHONY: sim-rtl-out

sim-gl-out: ## Simulate the hardened netlist and write $(TOP)_out.txt into sims/gl
	@test -f $(FINAL_DIR)/nl/$(TOP).nl.v || { echo "No $(FINAL_DIR)/nl/$(TOP).nl.v. Run 'make build-top' first."; exit 1; }
	mkdir -p $(SIM_DIR)/gl
	iverilog -g2012 -Irtl -o $(SIM_DIR)/gl/tb.vvp $(SCL_VERILOG) $(SCL_STUBS) $(FINAL_DIR)/nl/$(TOP).nl.v $(VERILOG_TB_DIR)/$(TOP)_tb.v
	cd $(SIM_DIR)/gl && vvp -n tb.vvp
.PHONY: sim-gl-out

# Dynamic power from a gate-level VCD
# The flow's own power__total assumes a default toggle rate, which at 65 kHz is
# meaningless. read_vcd annotates only the top-level pins of a flat netlist, so
# the activity comes from vcd_activity_sta.py as per-pin densities instead.
# The liberty is EZ130's, not the PDK's: the cells in this netlist are EZ130.
POWER_CLK_PERIOD  ?= 15258.789    # ns, 65.536 kHz
POWER_SCLK_PERIOD ?= 5000.0        # ns, 200 kHz SPI
POWER_N_VCD       ?= 4

sim-power-vcd: ## Gate-level simulation at the real clock, dumping a VCD window for power analysis
	@test -f $(FINAL_DIR)/nl/$(TOP).nl.v || { echo "No $(FINAL_DIR)/nl/$(TOP).nl.v. Run 'make build-top' first."; exit 1; }
	mkdir -p $(SIM_DIR)/power
	iverilog -g2012 -Irtl -P$(TOP)_tb.CLK_PERIOD=$(POWER_CLK_PERIOD) -P$(TOP)_tb.SCLK_PERIOD=$(POWER_SCLK_PERIOD) -P$(TOP)_tb.N_VCD=$(POWER_N_VCD) -o $(SIM_DIR)/power/tb.vvp $(SCL_VERILOG) $(SCL_STUBS) $(FINAL_DIR)/nl/$(TOP).nl.v $(VERILOG_TB_DIR)/$(TOP)_tb.v
	cd $(SIM_DIR)/power && vvp -n tb.vvp
.PHONY: sim-power-vcd

power-vcd: sim-power-vcd ## Report power per corner from the gate-level VCD (verification/power_vcd_<corner>.rpt)
	mkdir -p $(REPORT_DIR)
	python3 ../scripts/vcd_activity_sta.py $(SIM_DIR)/power/$(TOP).vcd $(FINAL_DIR)/nl/$(TOP).nl.v $(SIM_DIR)/power/$(TOP).act.tcl \
		--scope $(TOP)_tb/uut --period $(POWER_CLK_PERIOD) --liberty $(EZ130_DIR)/lib/ez130_8t_tt_1p20v_25c.lib
	@for c in $(STA_CORNERS); do \
		case $$c in *fast*) l=ff_1p32v_m40c ;; *slow*) l=ss_1p08v_125c ;; *) l=tt_1p20v_25c ;; esac; \
		TOP=$(TOP) NETLIST=$(FINAL_DIR)/nl/$(TOP).nl.v SPEF=$(FINAL_DIR)/spef/nom/$(TOP).nom.spef \
		LIBS=$(EZ130_DIR)/lib/ez130_8t_$$l.lib SDC=$(LIBRELANE_DIR)/$(TOP).sdc CLOCK_PERIOD=1000 \
		CLOCKS="clk $(POWER_CLK_PERIOD) sclk $(POWER_SCLK_PERIOD)" ACT=$(SIM_DIR)/power/$(TOP).act.tcl \
		sta -no_splash -exit ../scripts/power_vcd.tcl > $(REPORT_DIR)/power_vcd_$$c.rpt || exit 1; \
		echo "== $$c"; grep -E "^Total|^Sequential|^Combinational|^Clock" $(REPORT_DIR)/power_vcd_$$c.rpt; \
	done
.PHONY: power-vcd

# The check that the hardened netlist is the RTL. One testbench, run on both,
# and the two output files must be identical.
sim-gl: sim-rtl-out sim-gl-out ## Require the gate-level output to equal the RTL output, sample for sample
	@cmp $(SIM_DIR)/rtl/$(TOP)_out.txt $(SIM_DIR)/gl/$(TOP)_out.txt \
		&& echo "OK: gate-level output identical to RTL ($$(wc -l < $(SIM_DIR)/rtl/$(TOP)_out.txt) samples)"
.PHONY: sim-gl

# sim-gl only says the two agree, and they share a source. This says both are
# right: the five on-chip stimulus patterns against the bit-true model.
MODEL_GATE := ../../models/gate_dsa1_dig_out.py

model-gate: ## Require the RTL and gate-level stimulus responses to match the bit-true model
	@test -f $(SIM_DIR)/rtl/$(TOP)_out.txt || { echo "No $(SIM_DIR)/rtl/$(TOP)_out.txt. Run 'make sim-rtl-out' first."; exit 1; }
	python3 $(MODEL_GATE) $(SIM_DIR)/rtl/$(TOP)_out.txt
	@test -f $(SIM_DIR)/gl/$(TOP)_out.txt && python3 $(MODEL_GATE) $(SIM_DIR)/gl/$(TOP)_out.txt \
		|| echo "skipping gate level, no $(SIM_DIR)/gl/$(TOP)_out.txt"
.PHONY: model-gate

# The CDC between clk and sclk. Each ratio runs with several seeds, so the sclk phase at
# every ready flag is random, and each sclk half period jitters by CDC_JITTER of a period.
# 0.8 is the negative control: sclk slower than clk, where the bench must see flags that
# fall between sclk edges. Zero-delay simulation, so no metastability, see the bench.
CDC_CLK_PERIOD ?= 1000
CDC_RATIOS     ?= 0.8 1.05 1.3 1.7 2.1 3.3 6.1 12.7
CDC_SEEDS      ?= 1 2 3
CDC_JITTER     ?= 0.1
CDC_SIM        ?= gl

sim-cdc: $(if $(filter rtl,$(CDC_SIM)),$(RTL_GEN)) ## Sweep clk against sclk, phase and jitter, every word against the model (CDC_SIM=gl|rtl)
	mkdir -p $(SIM_DIR)/cdc
	rm -f $(SIM_DIR)/cdc/*.txt
	iverilog -g2012 -Irtl -o $(SIM_DIR)/cdc/tb.vvp \
		$(if $(filter rtl,$(CDC_SIM)),$(MODULES_SIM),$(SCL_VERILOG) $(SCL_STUBS) $(FINAL_DIR)/nl/$(TOP).nl.v) \
		$(VERILOG_TB_DIR)/$(TOP)_cdc_tb.v
	cd $(SIM_DIR)/cdc && for r in $(CDC_RATIOS); do for s in $(CDC_SEEDS); do \
		sp=$$(python3 -c "print($(CDC_CLK_PERIOD) / $$r)"); \
		vvp -n tb.vvp +clk=$(CDC_CLK_PERIOD) +sclk=$$sp +jitter=$$(python3 -c "print($$sp * $(CDC_JITTER))") \
			+seed=$$s +out=r$${r}_s$$s.txt > /dev/null || exit 1; \
	done; done
	python3 ../../models/gate_cdc.py $(SIM_DIR)/cdc/*.txt
.PHONY: sim-cdc
# ================================================================================================


# Equivalence Targets
# EQY proves the hardened netlist equal to the RTL, partition by partition. Gold is ghdl's Verilog
# from before the clock-gate pre-pass plus the decimator sources, read through slang, so the proof
# also covers the pre-pass. ghdl is on both sides: the VHDL's meaning is model-gate's to check.
LEC_OUT     := $(SIM_DIR)/lec
LEC_TIMEOUT ?= 5400
LEC_MUTANT  ?= 3000
LEC_ARGS     = --config $(LIBRELANE_DIR)/config.yaml --netlist $(FINAL_DIR)/nl/$(TOP).nl.v \
	--liberty $(EZ130_DIR)/lib/ez130_8t_tt_1p20v_25c.lib --multiclock --array-maps \
	--gold $(RTL_GEN) $(addprefix --gold ,$(DEC_SRCS)) --timeout $(LEC_TIMEOUT)

lec: ## Prove the hardened netlist equal to the RTL with EQY, verdict in verification/lec_verdict.json
	@test -f $(RTL_GEN) || { echo "No $(RTL_GEN). Run 'make $(RTL_GEN)' first."; exit 1; }
	python3 ../scripts/lec.py $(LEC_ARGS) --out $(LEC_OUT); rc=$$?; \
		cp $(LEC_OUT)/verdict.json $(REPORT_DIR)/lec_verdict.json; exit $$rc
.PHONY: lec

lec-fail: ## Invert gate output LEC_MUTANT and require lec to find it
	@test -f $(RTL_GEN) || { echo "No $(RTL_GEN). Run 'make $(RTL_GEN)' first."; exit 1; }
	python3 ../scripts/lec.py $(LEC_ARGS) --out $(LEC_OUT) --mutate $(LEC_MUTANT) --expect-fail
.PHONY: lec-fail
# ================================================================================================


# Register Map Targets
# regmap.yaml is the single source of the register map. These write, or check, every file made
# from it: rtl/dsa1_regs.vhd and .vh, sw/dsa1_regs.h, models/regmap_defs.py and doc/regmap.md.
REGMAP_GEN := ../scripts/regmap_gen.py

regmap: ## Generate the register map files from regmap.yaml
	python3 $(REGMAP_GEN) regmap.yaml
.PHONY: regmap

regmap-check: ## Fail if a file generated from regmap.yaml is stale, and self-test the generator
	python3 $(REGMAP_GEN) regmap.yaml --check
	python3 $(REGMAP_GEN) --selftest
	python3 ../../models/regmap.py
	python3 ../../models/test_regmap_dsm2.py
.PHONY: regmap-check
# ================================================================================================

# LibreLane Targets
librelane: rtl-gen check-ez130 ## Run LibreLane with Magic and KLayout DRC checks.
	librelane $(EZ130_SCL) $(DECAP_FRAG) $(LIBRELANE_DIR)/config.yaml --pdk ${PDK} --pdk-root ${PDK_ROOT} --manual-pdk --save-views-to $(FLOW_FINAL_DIR)/
.PHONY: librelane

librelane-nodrc: rtl-gen check-ez130 ## Run LibreLane without DRC checks
	librelane $(EZ130_SCL) $(DECAP_FRAG) $(LIBRELANE_DIR)/config.yaml --pdk ${PDK} --pdk-root ${PDK_ROOT} --manual-pdk --save-views-to $(FLOW_FINAL_DIR)/ --skip KLayout.DRC --skip Magic.DRC
.PHONY: librelane-nodrc

librelane-magicdrc: rtl-gen check-ez130 ## Run LibreLane with only Magic DRC checks
	librelane $(EZ130_SCL) $(DECAP_FRAG) $(LIBRELANE_DIR)/config.yaml --pdk ${PDK} --pdk-root ${PDK_ROOT} --manual-pdk --save-views-to $(FLOW_FINAL_DIR)/ --skip KLayout.DRC
.PHONY: librelane-magicdrc

librelane-klayoutdrc: rtl-gen check-ez130 ## Run LibreLane with only KLayout DRC checks
	librelane $(EZ130_SCL) $(DECAP_FRAG) $(LIBRELANE_DIR)/config.yaml --pdk ${PDK} --pdk-root ${PDK_ROOT} --manual-pdk --save-views-to $(FLOW_FINAL_DIR)/ --skip Magic.DRC
.PHONY: librelane-klayoutdrc

librelane-openroad: ## Open the last LibreLane run in OpenROAD GUI
	librelane $(EZ130_SCL) $(DECAP_FRAG) $(LIBRELANE_DIR)/config.yaml --pdk ${PDK} --pdk-root ${PDK_ROOT} --manual-pdk --last-run --flow OpenInOpenROAD
.PHONY: librelane-openroad

librelane-klayout: ## Open the last LibreLane run in KLayout
	librelane $(EZ130_SCL) $(DECAP_FRAG) $(LIBRELANE_DIR)/config.yaml --pdk ${PDK} --pdk-root ${PDK_ROOT} --manual-pdk --last-run --flow OpenInKLayout
.PHONY: librelane-klayout
# ================================================================================================


# Copy Targets
# Using * wildcard to ignore step numbers
copy-reports: ## Copy yosys, antenna, STA, power, IR-drop, DRC, LVS and manufacturability reports from the last LibreLane run to verification/
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
	cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-magic-drc/reports/drc.magic.rpt $(REPORT_DIR)/drc.magic.rpt
	cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-klayout-drc/reports/drc.klayout.json $(REPORT_DIR)/drc.klayout.json
	cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-netgen-lvs/reports/lvs.netgen.rpt $(REPORT_DIR)/lvs.netgen.rpt
	cp $(LIBRELANE_DIR)/runs/${RUN_TAG}/*-misc-reportmanufacturability/manufacturability.rpt $(REPORT_DIR)/manufacturability.rpt
.PHONY: copy-reports

copy-final: ## Copy final output gds, lef, lib, nl, pnl, spef, and vh folders from the last LibreLane run to final/
	rm -rf $(FINAL_DIR)/
	mkdir -p $(FINAL_DIR)/
	cp -r $(FLOW_FINAL_DIR)/gds  $(FINAL_DIR)/gds
	cp -r $(FLOW_FINAL_DIR)/lef  $(FINAL_DIR)/lef
	cp -r $(FLOW_FINAL_DIR)/lib  $(FINAL_DIR)/lib
	cp -r $(FLOW_FINAL_DIR)/nl   $(FINAL_DIR)/nl
	cp -r $(FLOW_FINAL_DIR)/pnl  $(FINAL_DIR)/pnl
	cp -r $(FLOW_FINAL_DIR)/spef $(FINAL_DIR)/spef
	cp -r $(FLOW_FINAL_DIR)/vh   $(FINAL_DIR)/vh
.PHONY: copy-final

copy-netlist: ## Copy final output spice, pnl and nl netlists from the last LibreLane run to netlist/
	rm -rf $(NET_SPICE_DIR)/
	mkdir -p $(NET_SPICE_DIR)/
	cp -r $(FLOW_FINAL_DIR)/spice/${TOP}.spice $(NET_SPICE_DIR)/${TOP}.spice

	rm -rf $(NET_PNL_DIR)/
	mkdir -p $(NET_PNL_DIR)/
	cp -r $(FLOW_FINAL_DIR)/pnl/${TOP}.pnl.v $(NET_PNL_DIR)/${TOP}.pnl.v

	rm -rf $(NET_NL_DIR)/
	mkdir -p $(NET_NL_DIR)/
	cp -r $(FLOW_FINAL_DIR)/nl/${TOP}.nl.v $(NET_NL_DIR)/${TOP}.nl.v
.PHONY: copy-netlist

copy-render: ## Copy macro render from the last LibreLane run to render/img/
	mkdir -p $(RENDER_IMG_DIR)/
	cp -r $(FLOW_FINAL_DIR)/render/${TOP}.png $(RENDER_IMG_DIR)/${TOP}_librelane.png
.PHONY: copy-render
# ================================================================================================


# Render Target
render-gds: ## Render images from the final GDS using sak-render.py
	mkdir -p $(RENDER_IMG_DIR)/
	sak-render.py -t ihp-sg13cmos5l -w 2048 -s 4 -o $(RENDER_IMG_DIR)/${TOP} $(FINAL_DIR)/gds/${TOP}.gds
.PHONY: render-gds
# ================================================================================================


# Xschem Symbol Targets
symbol-gl: ## Scaffold <CELL>.sym for a new macro, once, from the powered netlist ports (usage: make symbol-gl [CELL=<cellname>] [FORCE=1])
	python3 $(SCRIPTS_DIR)/verilog2sym.py $(NET_PNL_DIR)/$(CELL).pnl.v $(XSCHEM_SCH_DIR)/$(CELL).sym $(if $(FORCE),--force)
.PHONY: symbol-gl

symbol-check: ## Check <CELL>.sym against the powered netlist ports, runs inside generate-xspice (usage: make symbol-check [CELL=<cellname>])
	python3 $(SCRIPTS_DIR)/verilog2sym.py $(NET_PNL_DIR)/$(CELL).pnl.v $(XSCHEM_SCH_DIR)/$(CELL).sym --check
.PHONY: symbol-check
# ================================================================================================


# Generate XSPICE Target
generate-xspice: ## Generate XSPICE model from the LibreLane-extracted SPICE netlist
	$(MAKE) symbol-check CELL=$(TOP)
	mkdir -p $(XSPICE_DIR)
	python3 $(SCRIPTS_DIR)/spi2xspice.py $(PDK_ROOT)/$(PDK)/libs.ref/sg13cmos5l_stdcell/lib/sg13cmos5l_stdcell_typ_1p50V_25C.lib -io_time=500p -time=50p -idelay=5p -odelay=50p -cload=250f $(NET_SPICE_DIR)/${TOP}.spice $(XSPICE_DIR)/${TOP}.xspice
	sak-pin-reorder.py $(XSCHEM_SCH_DIR)/${TOP}.sym $(XSPICE_DIR)/${TOP}.xspice --format xspice
.PHONY: generate-xspice
# ================================================================================================


# Build Targets
# The top level, not the decimator alone: the SPI slave is the readout, so a
# host reads the decimated word out of ADC_DATA_CH0_HIGH and _LOW exactly as it
# will from the chip, and the bring-up sequence gets exercised with it.
build-fpga: ## Build the FPGA bitstream (usage: make build-fpga [BOARD=<board>])
	@$(MAKE) -C fpga all
.PHONY: build-fpga

synth-fpga: ## Synthesise for the FPGA and report utilisation, no place and route
	@$(MAKE) -C fpga synthesis
.PHONY: synth-fpga

pnr-fpga: ## Place and route for the FPGA, which is where the utilisation is decided
	@$(MAKE) -C fpga pr
.PHONY: pnr-fpga

clean-fpga: ## Remove the FPGA build outputs of every board
	@$(MAKE) -C fpga clean
.PHONY: clean-fpga

build-top: ## Build macro (run LibreLane with KLayout & Magic DRC checks, copy reports, copy final files, copy netlists, generate XSPICE model, copy render, and render final GDS)
	$(MAKE) librelane
	$(MAKE) copy-reports
	$(MAKE) copy-final
	$(MAKE) copy-netlist
	$(MAKE) generate-xspice
	$(MAKE) copy-render
	$(MAKE) render-gds
#	$(MAKE) librelane-openroad
.PHONY: build-top
# ================================================================================================


# DRC & LVS Verification Targets
# The LibreLane flow already includes DRC and LVS checks with Magic and KLayout, and they are saved in the verification/ folder.
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
		echo "Wrote $(XSCHEM_SCH_DIR)/$(CELL)_pex.sym (copy of $(CELL).sym with type=primitive)."; \
	fi
.PHONY: symbol-pex

klayout-pex: ## Run Parasitic Extraction with KPEX on the final GDS (usage: make klayout-pex [CELL=<cellname>] [EXT_MODE=<1|2|3>])
	@if [ ! -f $(LAY_DIR)/$(CELL).gds ]; then \
		echo "No layout $(LAY_DIR)/$(CELL).gds found. Run 'make build-top' (or 'make copy-final') first."; \
		exit 1; \
	fi
	mkdir -p $(NET_PEX_DIR)
	$(MAKE) symbol-pex CELL=$(CELL)
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
	--schematic $(NET_SPICE_DIR)/$(CELL).spice \
	--gds $(LAY_DIR)/$(CELL).gds \
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

magic-pex: ## Run Parasitic Extraction with Magic on the final GDS (usage: make magic-pex [CELL=<cellname>] [EXT_MODE=<1|2|3>] [THRESHOLD=<mOhm>] [MINRES=<mOhm>] [MINDELAY=<ps>])
	@if [ ! -f $(LAY_DIR)/$(CELL).gds ]; then \
		echo "No layout $(LAY_DIR)/$(CELL).gds found. Run 'make build-top' (or 'make copy-final') first."; \
		exit 1; \
	fi
	mkdir -p $(NET_PEX_DIR)
	$(MAKE) symbol-pex CELL=$(CELL)
	sak-pex.sh -d -m $(EXT_MODE) -n $(CELL)_pex -t $(THRESHOLD) -r $(MINRES) -y $(MINDELAY) -w $(NET_PEX_DIR) $(LAY_DIR)/$(CELL).gds
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


# Lint, Build, Verify and Simulate All Target
all: ## Lint, build, verify and simulate the macro
	$(MAKE) lint-verilog-all
	$(MAKE) build-fpga
	$(MAKE) build-top
	$(MAKE) magic-pex
#	$(MAKE) klayout-pex
	$(MAKE) sim-all
.PHONY: all
# ================================================================================================


# Clean Target
clean: ## Delete all generated files and folders (LibreLane runs, final, netlists, render, reports, simulation and FPGA outputs)
	rm -rf $(LIBRELANE_DIR)/runs $(FLOW_FINAL_DIR)
	rm -rf $(FINAL_DIR)
	rm -rf $(NET_NL_DIR) $(NET_PNL_DIR) $(NET_SPICE_DIR) $(XSPICE_DIR) $(NET_PEX_DIR)
	rm -rf $(RENDER_IMG_DIR)
	rm -rf $(REPORT_DIR)
	rm -rf $(XSCHEM_SCH_DIR)/simulations $(XSCHEM_TB_DIR)/simulations
	rm -rf $(SIM_PLOT_DIR)/data $(SIM_PLOT_DIR)/figures $(SIM_PLOT_DIR)/__pycache__
	rm -rf $(COCOTB_DIR)/sim_build
	rm -rf $(SCRIPTS_DIR)/__pycache__ $(COCOTB_DIR)/__pycache__
	rm -f $(VERILOG_TB_DIR)/*.vcd
	$(MAKE) -C fpga clean
.PHONY: clean
# ================================================================================================
