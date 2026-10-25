# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1

# Two-board FPGA bring-up bench: the master board's generated inputs, the
# simulation of both boards together, and the unit tests. The board build is
# in ulx3s/. See README.md.

FPGA_DIR := $(CURDIR)
include gen.mk

BUILD      := $(GEN)
MASTER_RTL := $(FPGA_DIR)/rtl
DEC_DIR    := $(ROOT_DIR)/macros/decimator/rtl
DUT_FPGA   := $(ROOT_DIR)/macros/dsa1_dig/fpga/rtl
RTL_GEN    := $(ROOT_DIR)/macros/dsa1_dig/rtl_gen/dsa1_dig_top.v

DUT_SRCS := \
	$(DEC_DIR)/ce_generator.sv \
	$(DEC_DIR)/cic_n6_d32.sv \
	$(DEC_DIR)/sinc2_chain.sv \
	$(DEC_DIR)/comp_fir.sv \
	$(DEC_DIR)/decimator_core.sv \
	$(DEC_DIR)/decimator_top.sv \
	$(RTL_GEN) \
	$(DUT_FPGA)/fs_gen.sv \
	$(DUT_FPGA)/dsa1_dig_fpga_top.sv

# vvp does not reliably exit non-zero on $fatal, so a bench passes on its PASS line.
run_vvp = vvp -n $(1) | tee $(1).out && grep -q '^PASS' $(1).out

.DEFAULT_GOAL := help

help: ## Show this help message
	@grep -hE '^[a-zA-Z0-9_.-]+:.*## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-20s %s\n", $$1, $$2}'
.PHONY: help

$(RTL_GEN): $(wildcard $(ROOT_DIR)/macros/dsa1_dig/rtl/*.vhd)
	$(MAKE) -C $(ROOT_DIR)/macros/dsa1_dig rtl_gen/dsa1_dig_top.v


# Unit tests
sim-dut-extclk: $(RTL_GEN) | $(BUILD) ## Unit test: the DUT harness takes clk_fs and reset from the master's pins
	iverilog -g2012 -grelative-include -o $(BUILD)/dut_extclk.vvp $(DUT_SRCS) sim/dut_extclk_tb.sv
	$(call run_vvp,$(BUILD)/dut_extclk.vvp)
.PHONY: sim-dut-extclk

sim-record-tx: | $(BUILD) ## Unit test: records come out as framed 8N1 bytes
	iverilog -g2012 -grelative-include -o $(BUILD)/record_tx.vvp $(MASTER_RTL)/uart_tx.sv $(MASTER_RTL)/record_tx.sv sim/record_tx_tb.sv
	$(call run_vvp,$(BUILD)/record_tx.vvp)
.PHONY: sim-record-tx

sim-bitstream-src: | $(BUILD) ## Unit test: the BRAM window plays bit for bit and wraps
	iverilog -g2012 -grelative-include -o $(BUILD)/bitstream_src.vvp $(MASTER_RTL)/bitstream_src.sv sim/bitstream_src_tb.sv
	$(call run_vvp,$(BUILD)/bitstream_src.vvp)
.PHONY: sim-bitstream-src

TOP_FPGA_DIR := $(ROOT_DIR)/macros/dsa1_dig/fpga
include $(TOP_FPGA_DIR)/legacy.mk

sim-duo-switch: $(RTL_GEN) $(LEGACY_V) | $(BUILD) ## Unit test: one bus to both digital back ends, this chip's and the DSA1 die's, switched through TEST_CTRL_1
	iverilog -g2012 -grelative-include -o $(BUILD)/duo_switch.vvp $(DUT_SRCS) $(LEGACY_V) sim/duo_switch_tb.sv
	$(call run_vvp,$(BUILD)/duo_switch.vvp)
.PHONY: sim-duo-switch

sim-arty-top: $(RTL_GEN) | $(BUILD) ## Unit test: the Arty A7 DUT build converts at 512 Hz from its 100 MHz oscillator
	iverilog -g2012 -grelative-include -o $(BUILD)/arty_top.vvp $(DUT_SRCS) $(ROOT_DIR)/macros/dsa1_dig/fpga/arty/arty_top.sv sim/arty_top_tb.sv
	$(call run_vvp,$(BUILD)/arty_top.vvp)
.PHONY: sim-arty-top

sim-versa-top: $(RTL_GEN) | $(BUILD) ## Unit test: the ECP5 Versa DUT build, 100 MHz clock, LEDs show AUX_CTRL_0 active low, switch
	iverilog -g2012 -grelative-include -o $(BUILD)/versa_top.vvp $(DUT_SRCS) $(ROOT_DIR)/macros/dsa1_dig/fpga/versa/versa_top.sv sim/versa_top_tb.sv
	$(call run_vvp,$(BUILD)/versa_top.vvp)
.PHONY: sim-versa-top

sim-versa-duo-top: $(RTL_GEN) $(LEGACY_V) | $(BUILD) ## Unit test: the ECP5 Versa build with both back ends, as sim-versa-top plus the bus switch
	iverilog -g2012 -grelative-include -DDUO -o $(BUILD)/versa_duo_top.vvp $(DUT_SRCS) $(LEGACY_V) \
		$(ROOT_DIR)/macros/dsa1_dig/fpga/versa_duo/versa_duo_top.sv sim/versa_top_tb.sv
	$(call run_vvp,$(BUILD)/versa_duo_top.vvp)
.PHONY: sim-versa-duo-top

sim-unit: sim-dut-extclk sim-record-tx sim-bitstream-src sim-arty-top sim-versa-top sim-versa-duo-top sim-duo-switch ## All seven unit tests
.PHONY: sim-unit


# Both boards together
PROGRAM ?= 0
EXT_FS  ?= 1
DUT_PPM ?= 50
N_ADC   ?= 48
SIM_OUT := $(BUILD)/sim
SIM_TAG := p$(PROGRAM)_ext$(EXT_FS)_ppm$(DUT_PPM)

sim: $(RTL_GEN) $(MASTER_V) $(SEQ_MEM) $(STREAM_MEM) ## Both boards on PROGRAM, then models/bench_capture.py on the UART log
	mkdir -p $(SIM_OUT)
	iverilog -g2012 -grelative-include -o $(SIM_OUT)/$(SIM_TAG).vvp \
		-Pbringup_tb.PROGRAM=$(PROGRAM) -Pbringup_tb.EXT_FS=$(EXT_FS) \
		-Pbringup_tb.DUT_PPM=$(DUT_PPM) -Pbringup_tb.N_ADC=$(N_ADC) \
		-Pbringup_tb.SEQ_MEM=\"$(SEQ_MEM)\" -Pbringup_tb.STREAM_MEM=\"$(STREAM_MEM)\" \
		-Pbringup_tb.LOG=\"$(SIM_OUT)/$(SIM_TAG).hex\" \
		$(DUT_SRCS) $(filter-out $(DUT_SRCS),$(MASTER_SRCS)) sim/bringup_tb.sv
	vvp -n $(SIM_OUT)/$(SIM_TAG).vvp | tee $(SIM_OUT)/$(SIM_TAG).out
	@grep -q '^DONE' $(SIM_OUT)/$(SIM_TAG).out
	python3 $(ROOT_DIR)/models/bench_capture.py --hex $(SIM_OUT)/$(SIM_TAG).hex --stream $(STREAM_MEM)
.PHONY: sim


# Program 7 with the DUT on its own oscillator, 2000 ppm off. The stream index
# then steps 127 or 129 per conversion now and then, and the checker has to say so.
sim-slip: ## Negative check: a DUT not on the master's clk_fs must fail the checker
	@if $(MAKE) --no-print-directory sim PROGRAM=7 EXT_FS=0 DUT_PPM=2000 N_ADC=24 > $(BUILD)/slip.out 2>&1; then \
		echo "FAIL: the checker passed a DUT that was not on the master's clock"; exit 1; fi
	@grep -m1 'slipped' $(BUILD)/slip.out || { echo "FAIL: sim-slip failed for another reason, see $(BUILD)/slip.out"; exit 1; }
	@echo "OK: a DUT on its own clock is caught"
.PHONY: sim-slip

sim-all: sim-unit ## Unit tests, all eight programs, and the slip check
	@for p in 0 1 2 3 4 5 6 7; do $(MAKE) --no-print-directory sim PROGRAM=$$p || exit 1; done
	@$(MAKE) --no-print-directory sim-slip
.PHONY: sim-all

# Master board build
build-master: ## Master board bitstream, ULX3S, into ulx3s/build/
	$(MAKE) -C ulx3s gen_bitstream
.PHONY: build-master

load-master: ## Load the master bitstream into the ULX3S SRAM
	$(MAKE) -C ulx3s load_bitstream
.PHONY: load-master

clean: ## Remove build/
	rm -rf $(BUILD)
	$(MAKE) -C ulx3s clean
.PHONY: clean
