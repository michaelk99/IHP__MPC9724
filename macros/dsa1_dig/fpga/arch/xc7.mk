# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1

# Xilinx 7-series, the open openXC7 flow: Yosys (synth_xilinx) -> nextpnr-xilinx
# -> fasm2frames -> xc7frames2bit. Every step runs in the openXC7 image, started
# from the host with docker, so run these targets on the host, not inside the
# IIC-OSIC-TOOLS container, which has no docker. Only rtl_gen/dsa1_dig_top.v
# needs the container, for ghdl, and dut.mk says so when it is missing.
#
# The chip database is generated once per device, about a minute, and cached
# outside the repository in CHIPDB_DIR.
#
# nextpnr-xilinx does not model speed grades, so the part is the -1 of the die.
# The Arty's xc7a35ticsg324-1L is the same die, package and ID code.

OPENXC7_IMAGE ?= regymm/openxc7:latest
XC7_PART      ?= xc7a35tcsg324-1
XC7_FAMILY    ?= artix7
XC7_DEVICE    := $(firstword $(subst -, ,$(XC7_PART)))
PRJXRAY_DB    ?= /nextpnr-xilinx/xilinx/external/prjxray-db
CHIPDB_DIR    ?= $(HOME)/.cache/openxc7
CHIPDB        := $(CHIPDB_DIR)/$(XC7_DEVICE).bin

# The repository is mounted at the same path inside the container, so every
# relative path of the board Makefile still resolves. CHIPDB_DIR is created
# first, or the docker daemon creates it as root on the first mount.
XC7_REPO ?= $(abspath $(TOP_FPGA_DIR)/../../..)
OPENXC7  = mkdir -p $(CHIPDB_DIR) && docker run --rm -u $(shell id -u):$(shell id -g) -e HOME=/tmp \
	-v $(XC7_REPO):$(XC7_REPO) -v $(CHIPDB_DIR):$(CHIPDB_DIR) -w $(CURDIR) $(OPENXC7_IMAGE)

# -nosrl keeps every flop a flop, so the count stays comparable with the ASIC.
TARGET     ?= synth_xilinx
SYNTH_OPTS ?= -family xc7 -flatten -abc9 -nosrl -nolutram
SYNTH_CMD  ?= $(OPENXC7) yosys -DFPGA -p '$(TARGET) $(SYNTH_OPTS) -top $(TOP); write_json $(BUILD_DIR)/$(TOP).json;' $(MODULES_SYNTH)

PNR_OUT  ?= $(BUILD_DIR)/$(TOP).fasm
PNR_DEPS += $(CHIPDB)
PNR_CMD  ?= $(OPENXC7) nextpnr-xilinx --chipdb $(CHIPDB) --xdc $(PCF_FILE) --json $(BUILD_DIR)/$(TOP).json \
	--fasm $(PNR_OUT) --log $(BUILD_DIR)/$(TOP)_pnr.log

BITSTREAM ?= $(BUILD_DIR)/$(TOP).bit
PACK_CMD  ?= $(OPENXC7) bash -c 'fasm2frames --part $(XC7_PART) --db-root $(PRJXRAY_DB)/$(XC7_FAMILY) $(PNR_OUT) > $(BUILD_DIR)/$(TOP).frames && \
	xc7frames2bit --part_file $(PRJXRAY_DB)/$(XC7_FAMILY)/$(XC7_PART)/part.yaml --part_name $(XC7_PART) \
	--frm_file $(BUILD_DIR)/$(TOP).frames --output_file $(BITSTREAM)'
LOAD_CMD  ?= openFPGALoader --board=$(OPENFPGALOADER_BOARD) $(BITSTREAM)
FLASH_CMD ?= openFPGALoader --board=$(OPENFPGALOADER_BOARD) --write-flash $(BITSTREAM)

# A truncated .frames file still packs into a .bit that loads, reports DONE and
# does nothing, so a failed step must not leave its output behind.
.DELETE_ON_ERROR:

$(CHIPDB):
	$(OPENXC7) bash -c 'pypy3 /nextpnr-xilinx/xilinx/python/bbaexport.py --device $(XC7_PART) --bba $(CHIPDB_DIR)/$(XC7_DEVICE).bba && \
		bbasm -l $(CHIPDB_DIR)/$(XC7_DEVICE).bba $@ && rm $(CHIPDB_DIR)/$(XC7_DEVICE).bba'
