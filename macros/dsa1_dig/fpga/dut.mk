# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1

# RTL of the design under test, shared by all boards.
#
# dsa1_dig_top is VHDL, and yosys does not read VHDL, so the FPGA flow uses the
# same ghdl-synth output the ASIC flow starts from: rtl_gen/dsa1_dig_top.v.
# The clock-gated rtl_gen/dsa1_dig_top_cg.v is deliberately NOT used here. It
# carries EZ130 CGX3 instances, which mean nothing to an FPGA, and yosys infers
# its own clock enables anyway.
#
# Order matters: the harness is last, the macro and the decimator before it.

TOP_FPGA_DIR := ..

MACRO_DIR := ../..
DEC_DIR   := ../../../decimator/rtl
RTL_GEN   := $(MACRO_DIR)/rtl_gen/dsa1_dig_top.v

DUT_SRCS := \
	$(DEC_DIR)/ce_generator.sv \
	$(DEC_DIR)/cic_n6_d32.sv \
	$(DEC_DIR)/sinc2_chain.sv \
	$(DEC_DIR)/comp_fir.sv \
	$(DEC_DIR)/decimator_core.sv \
	$(DEC_DIR)/decimator_top.sv \
	$(RTL_GEN) \
	../rtl/fs_gen.sv \
	../rtl/dsa1_dig_fpga_top.sv

# the harness includes the register map generated from regmap.yaml
SYNTH_DEPS += $(MACRO_DIR)/rtl/dsa1_regs.vh

# ghdl synth runs from the macro folder, and only if the Verilog is missing or
# older than the VHDL. Every board target depends on this.
$(RTL_GEN): $(wildcard $(MACRO_DIR)/rtl/*.vhd)
	$(MAKE) -C $(MACRO_DIR) $(patsubst $(MACRO_DIR)/%,%,$(RTL_GEN))

PNR_DEPS += $(RTL_GEN)
