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
    print("regmap.py selftest: OK")


if __name__ == "__main__":
    _selftest()
