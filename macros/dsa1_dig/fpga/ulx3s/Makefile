# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1

# Board: ULX3S (Lattice ECP5-85F, 25 MHz oscillator). The default board for
# this macro: dsa1_dig_top is about 1800 flops plus a 27-bit datapath, which is
# comfortable on an 85F and tight to impossible on an iCE40UP5K.
# See ../README.md.

TOP := dsa1_dig_fpga_top

include ../dut.mk
MODULES_SYNTH := $(DUT_SRCS)

PCF_FILE := ulx3s.lpf

ARCH        := ecp5
ECP5_DEVICE := --85k --package CABGA381

OPENFPGALOADER_BOARD := ulx3s
OPENFPGALOADER_FLAGS := --unprotect-flash

include $(TOP_FPGA_DIR)/fpga.mk
