# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1

# The Arty A7-35T with both digital back ends of the eval board behind one SPI
# bus: this chip's and the DSA1 die's as taped out, switched through
# TEST_CTRL_1, see ../README.md. Same pins as ../arty.
# The legacy Verilog comes from ghdl, so run `make legacy-rtl` in the
# IIC-OSIC-TOOLS container once, as for rtl_gen.

TOP := arty_duo_top

include ../dut.mk
include ../legacy.mk
MODULES_SYNTH := $(DUT_SRCS) $(LEGACY_V) arty_duo_top.sv
PNR_DEPS += $(LEGACY_V)

PCF_FILE := ../arty/arty.xdc

ARCH     := xc7
XC7_PART := xc7a35tcsg324-1

OPENFPGALOADER_BOARD := arty_a7_35t

include $(TOP_FPGA_DIR)/fpga.mk
