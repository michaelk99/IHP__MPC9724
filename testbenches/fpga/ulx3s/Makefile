# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1

# Board: ULX3S (ECP5-85F, 25 MHz), the master side of the two-board bring-up.
# The flow is the DUT's own fpga.mk, the sources and memory images come from
# ../gen.mk. See ../README.md.

TOP := dsa1_master_fpga_top

FPGA_DIR := $(abspath ..)
include ../gen.mk

MODULES_SYNTH := $(MASTER_SRCS)
PCF_FILE      := ulx3s.lpf

ARCH        := ecp5
ECP5_DEVICE := --85k --package CABGA381

OPENFPGALOADER_BOARD := ulx3s
OPENFPGALOADER_FLAGS := --unprotect-flash

include $(ROOT_DIR)/macros/dsa1_dig/fpga/fpga.mk

# $readmemh reads both images during synthesis.
$(BUILD_DIR)/$(TOP).json: $(SEQ_MEM) $(STREAM_MEM)
