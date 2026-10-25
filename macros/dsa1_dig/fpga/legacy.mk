# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1

# The DSA1 die's own digital back end, which the eval board carries next to this
# chip: decimator v4 and the SPI slave as taped out on 2026-08-10. That is
# jku-phd at LEGACY_REV, checked equal to the RTL delivered in the IIC svn
# (TO_IHPSG13G2/cad_libs/TO_DSA1_DIGITAL). Read from there, never copied into
# this repo, and its ghdl output stays in legacy/build, which git ignores.
#
# Both designs name their top dsa1_dig_top and their decimator decimator_top,
# so every module the legacy defines gets the prefix legacy_.
# ghdl needs the IIC-OSIC-TOOLS container, like rtl_gen.
#
# Include after TOP_FPGA_DIR is set.

LEGACY_REV  ?= c353a7e
JKU_PHD_DIR ?= $(abspath $(TOP_FPGA_DIR)/../../../../jku-phd)
LEGACY_DIR  := $(TOP_FPGA_DIR)/legacy/build
# .sv, since dec_top.v uses parameter int, which yosys reads only as SystemVerilog
LEGACY_V    := $(LEGACY_DIR)/legacy_dsa1_dig.sv
_LEGACY_HDL := circuit-level/hdl/DSADC1
_LEGACY_SRC := SPI/src/dsa1_regs.vhd SPI/src/dsa1_ic_bus_slave.vhd DIG_TOP/src/dsa1_dig_top.vhd DEC/decimator_v4/src/dec_top.v

$(LEGACY_V):
	@git -C $(JKU_PHD_DIR) cat-file -e $(LEGACY_REV) 2>/dev/null || \
		{ echo "No commit $(LEGACY_REV) in '$(JKU_PHD_DIR)'. Point JKU_PHD_DIR at the jku-phd checkout."; exit 1; }
	mkdir -p $(LEGACY_DIR)/src $(LEGACY_DIR)/work
	for f in $(_LEGACY_SRC); do git -C $(JKU_PHD_DIR) show $(LEGACY_REV):$(_LEGACY_HDL)/$$f > $(LEGACY_DIR)/src/$$(basename $$f) || exit 1; done
	ghdl synth --std=08 --workdir=$(LEGACY_DIR)/work --out=verilog \
		$(addprefix $(LEGACY_DIR)/src/,dsa1_regs.vhd dsa1_ic_bus_slave.vhd dsa1_dig_top.vhd) -e dsa1_dig_top > $(LEGACY_DIR)/dsa1_dig_top.v
	python3 $(TOP_FPGA_DIR)/scripts/prefix_modules.py legacy_ $(LEGACY_DIR)/dsa1_dig_top.v $(LEGACY_DIR)/src/dec_top.v > $@.tmp
	mv $@.tmp $@

legacy-rtl: $(LEGACY_V) ## The DSA1 die's digital back end at LEGACY_REV, prefixed, into legacy/build (container)
.PHONY: legacy-rtl
