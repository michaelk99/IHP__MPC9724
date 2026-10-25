# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1

# Generated inputs of the master board: the ghdl-synth SPI master and the two
# memory images. Included by ./Makefile and ulx3s/Makefile, which set FPGA_DIR
# to this folder, as an absolute path, first.
#
# The master VHDL is read in place from the jku-phd checkout and never copied.
# Its ghdl output stays in build/, which git ignores.

ROOT_DIR    := $(abspath $(FPGA_DIR)/../..)
JKU_PHD_DIR ?= $(abspath $(ROOT_DIR)/../jku-phd)
MASTER_VHD  := $(JKU_PHD_DIR)/circuit-level/hdl/DSADC1/SPI/src/dsa1_ic_bus_master.vhd
STIM_FILE   ?= $(JKU_PHD_DIR)/circuit-level/hdl/DSADC1/DEC/decimator_v5/sim/stim_dac_sine_dec.txt
REGS_VHD    := $(ROOT_DIR)/macros/dsa1_dig/rtl/dsa1_regs.vhd

# 25 MHz / (2 * 62) = 201.6 kHz sclk, well above the 65536 Hz sample clock
HALF_CLK_PERIOD_INDEX ?= 62
# the window skips the modulator's first second
STREAM_START ?= 65536

GEN        := $(FPGA_DIR)/build
MASTER_V   := $(GEN)/dsa1_ic_bus_master.v
SEQ_MEM    := $(GEN)/seq.mem
STREAM_MEM := $(GEN)/stream.mem

MASTER_SRCS := \
	$(ROOT_DIR)/macros/dsa1_dig/fpga/rtl/fs_gen.sv \
	$(FPGA_DIR)/rtl/uart_tx.sv \
	$(FPGA_DIR)/rtl/record_tx.sv \
	$(FPGA_DIR)/rtl/bitstream_src.sv \
	$(FPGA_DIR)/rtl/seq_core.sv \
	$(MASTER_V) \
	$(FPGA_DIR)/rtl/dsa1_master_fpga_top.sv

$(GEN):
	mkdir -p $@

check-jku: ## Fail early when the jku-phd checkout is missing
	@test -f $(MASTER_VHD) || { echo "No $(MASTER_VHD). Point JKU_PHD_DIR at the jku-phd checkout."; exit 1; }
.PHONY: check-jku

$(MASTER_V): $(wildcard $(MASTER_VHD)) $(REGS_VHD) | check-jku $(GEN)
	mkdir -p $(GEN)/work
	ghdl synth --std=08 --workdir=$(GEN)/work -gHALF_CLK_PERIOD_INDEX=$(HALF_CLK_PERIOD_INDEX) \
		--out=verilog $(REGS_VHD) $(MASTER_VHD) -e dsa1_ic_bus_master > $@.tmp
	mv $@.tmp $@

$(SEQ_MEM): $(FPGA_DIR)/seq/seqasm.py $(FPGA_DIR)/seq/programs.seq $(FPGA_DIR)/seq/startup.seq $(ROOT_DIR)/models/regmap.py $(REGS_VHD) | $(GEN)
	python3 $(FPGA_DIR)/seq/seqasm.py $(FPGA_DIR)/seq/programs.seq -o $@

$(STREAM_MEM): $(wildcard $(STIM_FILE)) | $(GEN)
	@test -f $(STIM_FILE) || { echo "No $(STIM_FILE). Set STIM_FILE or JKU_PHD_DIR."; exit 1; }
	python3 $(ROOT_DIR)/models/stream_window.py $(STIM_FILE) $@ --start $(STREAM_START)
