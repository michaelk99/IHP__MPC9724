# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""The register map, from models/regmap_defs.py, which macros/scripts/regmap_gen.py generates from
macros/dsa1_dig/regmap.yaml, and the TEST_CTRL_0 rules that are more than a field value."""

from __future__ import annotations

import importlib.util
from pathlib import Path

# by file, not through sys.path, so a tool that also imports another checkout's models gets both right
_spec = importlib.util.spec_from_file_location("regmap_defs", Path(__file__).resolve().parent / "regmap_defs.py")
_defs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_defs)
DIES, REGISTERS = _defs.DIES, _defs.REGISTERS

DIE = DIES[0]                   # this chip, cmos5l
REGS = {r["name"]: r for r in REGISTERS[DIE]}
ADDR = {name: r["addr"] for name, r in REGS.items()}
RESET = {r["addr"]: r["reset"] for r in REGS.values()}
TEST_CTRL_0 = ADDR["TEST_CTRL_0"]
TEST_CTRL_1 = ADDR["TEST_CTRL_1"]
CHIP_ID = ADDR["CHIP_ID"]
READ_ONLY = {r["addr"] for r in REGS.values() if r["access"] == "const"}   # a write changes nothing


def field_violation(reg: str, value: int) -> str | None:
    """Why a value breaks a register's hold or forbid rules from the YAML, or None."""
    fields = REGS[reg]["fields"]
    held = [f for f in fields if f["hold"] == 1]
    ones = sum(((1 << (f["msb"] - f["lsb"] + 1)) - 1) << f["lsb"] for f in held)
    if value & ones != ones:
        return f"drops the 0x{ones:04X} base ({', '.join(f['name'] for f in held)})"
    for f in fields:
        width = f["msb"] - f["lsb"] + 1
        v = (value >> f["lsb"]) & ((1 << width) - 1)
        if f["hold"] == 0 and v:
            return f"sets bit {f['lsb']} ({f['name']}): {f['desc'] or 'must stay 0'}"
        if v in f["forbid"]:
            return f"puts {v:0{width}b} in bits {f['msb']}:{f['lsb']} ({f['name']}): {f['desc'] or 'forbidden'}"
    return None


def test_ctrl_violation(value: int) -> str | None:
    """Why a TEST_CTRL_0 value must never be written, or None if it may."""
    why = field_violation("TEST_CTRL_0", value)
    if why:
        return why
    page, nib = (value >> 4) & 3, value & 0xF
    if page == 3:
        return "selects core test page 11, which is undocumented"
    if page == 1 and bin(nib).count("1") > 1:
        return "selects more than one integrator on the core test mux, which shorts them"
    return None


def core_sel(value: int):
    """The core test mux node a TEST_CTRL_0 value selects, None when neutral (startup.md)."""
    page, nib = (value >> 4) & 3, value & 0xF
    if page == 0 or (page == 1 and nib == 0):
        return None
    return (page, nib if page == 1 else 0)


def test_ctrl_transition(prev: int, value: int) -> str | None:
    """Why going from prev to value on TEST_CTRL_0 is unsafe, or None.

    startup.md: neutralize the core test mux before a new node, so the analog
    mux never shorts two core nodes on the way from one to the other.
    """
    a, b = core_sel(prev), core_sel(value)
    if a is not None and b is not None and a != b:
        return "switches the core test mux between two nodes without going through neutral"
    return None


def _bit(reg: str, name: str) -> int:
    """The mask of a bit by its name, per-bit names included."""
    for f in REGS[reg]["fields"]:
        if name in f["bit_names"]:
            return 1 << (f["msb"] - f["bit_names"].index(name))
    raise KeyError(f"{reg} has no bit {name}")


BIAS_CFG_0, BIAS_CFG_1 = ADDR["BIAS_CFG_0"], ADDR["BIAS_CFG_1"]
DSM_TRIM = sum(_bit("BIAS_CFG_0", f"DSM_TRIM{i}") for i in range(4))
DSM_OSC_EN = _bit("BIAS_CFG_0", "DSM_OSC_EN")
DSM_CLK_SEL = _bit("BIAS_CFG_0", "DSM_CLK_SEL")
DSM_EN = _bit("BIAS_CFG_1", "DSM_EN")          # inverted on this chip, 1 is dsm2 off
DSM_RST_B = _bit("BIAS_CFG_1", "DSM_RST_B")    # inverted, 1 holds dsm2 in reset


def dsm2_violation(cfg0: int, cfg1: int, reg: int, data: int) -> str | None:
    """Why writing data to reg breaks a dsm2 rule on this chip, with cfg0 and cfg1 the values it holds, or None."""
    if reg == BIAS_CFG_0:
        if data & DSM_CLK_SEL and not data & DSM_OSC_EN:
            return "sets di_clk_sel without di_osc_en, dsm2 then drives dsm_clk low"
        if (data ^ cfg0) & (DSM_TRIM | DSM_OSC_EN | DSM_CLK_SEL) and not cfg1 & DSM_EN:
            return "changes the trim or the oscillator bits while dsm2 is on, write DSM_EN 1 first"
    if reg == BIAS_CFG_1 and cfg1 & DSM_EN and not data & (DSM_EN | DSM_RST_B):
        return "switches dsm2 on and releases its reset in one write, DSM_RST_B 0 needs 130 us more"
    return None


def dsm_clk_sel_rises(prev: int, value: int) -> bool:
    """The write makes dsm2 drive the dsm_clk pad, so the host must have stopped driving it."""
    return bool(value & DSM_CLK_SEL and not prev & DSM_CLK_SEL)


def _selftest():
    assert ADDR["TEST_CTRL_0"] == 9 and ADDR["CHIP_ID"] == 15 and ADDR["ADC_DATA_CH0_HIGH"] == 0
    assert RESET[2] == 0x0024 and RESET[3] == 0x0040 and RESET[6] == 0x00FF and RESET[9] == 0x0500 and RESET[12] == 0xFF00
    assert RESET[15] == 0x0001 and RESET[0] == RESET[13] == RESET[14] == 0
    assert READ_ONLY == {15}
    ok = (0x0500, 0x0580, 0x0591, 0x0512, 0x0520, 0xFD00, 0x0540)
    assert all(test_ctrl_violation(v) is None for v in ok), [test_ctrl_violation(v) for v in ok]
    for v, why in ((0x0400, "0x0500 base"), (0x0100, "0x0500 base"), (0x0700, "bit 9"),
                   (0x05C0, "7:6"), (0x0530, "page 11"), (0x0513, "more than one integrator")):
        got = test_ctrl_violation(v)
        assert got and why in got, (hex(v), got)
    assert test_ctrl_transition(0x0511, 0x0512) and test_ctrl_transition(0x0511, 0x0510) is None
    assert test_ctrl_transition(0x0510, 0x0512) is None and test_ctrl_transition(0x0520, 0x0511)
    assert (DSM_TRIM, DSM_OSC_EN, DSM_CLK_SEL, DSM_EN, DSM_RST_B) == (0x000F, 0x0080, 0x0100, 0x0001, 0x0002)
    on, off = 0x0040, 0x0041
    assert dsm2_violation(0x0024, on, 2, 0x0025) and dsm2_violation(0x0024, off, 2, 0x0025) is None
    assert dsm2_violation(0x0024, on, 2, 0x0034) is None                    # dither is free
    assert dsm2_violation(0x0024, off, 2, 0x0124) and dsm2_violation(0x0024, off, 2, 0x01A4) is None
    assert dsm2_violation(0x0024, on, 2, 0x00A4)                            # oscillator only with dsm2 off
    assert dsm2_violation(0x0024, off, 3, 0x0040) and dsm2_violation(0x0024, off, 3, 0x0042) is None
    assert dsm_clk_sel_rises(0x0024, 0x0124) and not dsm_clk_sel_rises(0x0124, 0x0124) and not dsm_clk_sel_rises(0x0124, 0x0024)
    print("regmap.py selftest: OK")


if __name__ == "__main__":
    _selftest()
