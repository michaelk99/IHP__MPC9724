# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1

# The ECP5 Versa with both digital back ends of the eval board behind one SPI
# bus: this chip's and the DSA1 die's as taped out, switched through
# TEST_CTRL_1, see ../README.md. Same pins and part as ../versa.
# The legacy Verilog comes from ghdl, so run `make legacy-rtl` in the
# IIC-OSIC-TOOLS container once, as for rtl_gen.

TOP := versa_duo_top

include ../dut.mk
include ../legacy.mk
MODULES_SYNTH := $(DUT_SRCS) $(LEGACY_V) versa_duo_top.sv
PNR_DEPS += $(LEGACY_V)

PCF_FILE := ../versa/versa.lpf

ARCH        := ecp5
ECP5_DEVICE := --um-45k --package CABGA381 --speed 7

# openFPGALoader has no Versa profile, the FTDI's channel A is the JTAG port.
# With jumper J50 in its factory setting the board's ispCLOCK is in the chain too,
# and --misc-device declares it, so either J50 setting works, see ../README.md.
VERSA_JTAG = -c ft2232 --misc-device 0x00191043,8,ispclock
LOAD_CMD  = openFPGALoader $(VERSA_JTAG) $(BITSTREAM)
FLASH_CMD = openFPGALoader $(VERSA_JTAG) -f $(BITSTREAM)

include $(TOP_FPGA_DIR)/fpga.mk
