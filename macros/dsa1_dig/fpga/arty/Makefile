# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1

# Board: Digilent Arty A7-35T (xc7a35ticsg324-1L, 100 MHz oscillator), built
# with the open openXC7 flow in Docker, see ../arch/xc7.mk. The XIAO ESP32-S3
# host plugs into Pmod JD, in the standard Pmod SPI Type 2A order.
# arty_top.sv sets the harness's board clock to 100 MHz. See ../README.md.

TOP := arty_top

include ../dut.mk
MODULES_SYNTH := $(DUT_SRCS) arty_top.sv

PCF_FILE := arty.xdc

ARCH     := xc7
XC7_PART := xc7a35tcsg324-1

OPENFPGALOADER_BOARD := arty_a7_35t

include $(TOP_FPGA_DIR)/fpga.mk
