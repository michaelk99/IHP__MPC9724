# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1

# Board: Lattice ECP5 Versa Development Kit (LFE5UM-45F-7BG381I, 100 MHz LVDS
# oscillator). The non-5G part, so --um-45k, and --speed 7, the board's grade.
# versa_top.sv sets the harness's board clock to 100 MHz, shows AUX_CTRL_0 on the
# active-low LEDs and inverts the DIP switch. The XIAO ESP32-S3 host wires to
# expansion header X3. See ../README.md.

TOP := versa_top

include ../dut.mk
MODULES_SYNTH := $(DUT_SRCS) versa_top.sv

PCF_FILE := versa.lpf

ARCH        := ecp5
ECP5_DEVICE := --um-45k --package CABGA381 --speed 7

# openFPGALoader has no Versa profile, the FTDI's channel A is the JTAG port.
# With jumper J50 in its factory setting the board's ispCLOCK is in the chain too,
# and --misc-device declares it, so either J50 setting works, see ../README.md.
VERSA_JTAG = -c ft2232 --misc-device 0x00191043,8,ispclock
LOAD_CMD  = openFPGALoader $(VERSA_JTAG) $(BITSTREAM)
FLASH_CMD = openFPGALoader $(VERSA_JTAG) -f $(BITSTREAM)

include $(TOP_FPGA_DIR)/fpga.mk
