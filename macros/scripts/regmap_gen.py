#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: Generate every derived view of a macro's register map YAML
# parse_bits, reg_reset and validate follow iic-jku/OpenBLAU macros/ble_tx/scripts/regmap_gen.py at 690a7c71.
"""Render macros/<macro>/regmap.yaml into the files that use the register map.

  rtl/<package>.vhd        the VHDL package: addresses, reset values, field bits, enums
  rtl/<package>.vh         the same as Verilog defines, for the benches
  sw/<package>.h           C header for the hosts
  models/regmap_defs.py    stdlib-only Python data: registers, fields, per-die bit names, write rules
  doc/regmap.md            the register tables

regmap_gen.py writes them, --check exits 1 when one is stale, --selftest runs the unit tests.
The YAML keys are described at the top of regmap.yaml.
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- helpers

def parse_bits(spec):
    """'15:0' -> (15, 0, 16), '3' -> (3, 3, 1)."""
    spec = str(spec)
    if ":" in spec:
        msb, lsb = (int(x) for x in spec.split(":"))
    else:
        msb = lsb = int(spec)
    if msb < lsb:
        raise ValueError(f"bad bit range {spec!r}: msb < lsb")
    return msb, lsb, msb - lsb + 1


def reg_reset(reg):
    """Reset value of a whole register word, from its fields."""
    value = 0
    for field in reg["fields"]:
        _, lsb, _ = parse_bits(field["bits"])
        value |= int(field.get("reset", 0)) << lsb
    return value


def field_bits(field):
    msb, lsb, _ = parse_bits(field["bits"])
    return set(range(lsb, msb + 1))


def die_fields(reg, die):
    """The fields a die has. Another die's field is reserved TBD here, or dropped where this die's own fields
    claim any of its bits, so two dies can lay different fields over the same bits."""
    own = [f for f in reg["fields"] if f.get("only", die) == die]
    claimed = set().union(*(field_bits(f) for f in own)) if own else set()
    out = []
    for f in reg["fields"]:
        if f.get("only", die) == die:
            out.append(f)
        elif not field_bits(f) & claimed:
            out.append({"name": "TBD", "bits": f["bits"], "reset": 0, "reserved": True})
    return out


def die_view(regmap, die):
    """The registers as one die has them: `dies` overrides applied, the fields of `die_fields`,
    and `used` resolved to a bool."""
    regs = []
    for reg in regmap["registers"]:
        r = {k: v for k, v in reg.items() if k not in ("fields", "dies")}
        r.update(reg.get("dies", {}).get(die, {}))
        r.setdefault("access", "rw")
        fields = []
        for f in die_fields(reg, die):
            f = dict(f)
            if r["access"] == "rw" and "value" in r:  # storage where the other die has a constant
                _, lsb, width = parse_bits(f["bits"])
                f["reset"] = (r["value"] >> lsb) & ((1 << width) - 1)
            f["used"] = die in f.get("used", [])
            fields.append(f)
        r["fields"] = fields
        r["reset"] = reg_reset(r)
        regs.append(r)
    return regs


def own_die(regmap):
    """The die this repository builds: the first of meta.dies."""
    return regmap["meta"]["dies"][0]


def bit_names(field):
    """Name of every bit of a field, msb first: NAME<k> for a multi-bit field, NAME for a single
    bit or a reserved field, a per-bit `names` entry where the sheet does not count down."""
    msb, lsb, width = parse_bits(field["bits"])
    out = []
    for bit in range(msb, lsb - 1, -1):
        if bit in field.get("names", {}):
            out.append(field["names"][bit])
        elif width == 1 or field.get("reserved"):
            out.append(field["name"])
        else:
            out.append(f"{field['name']}{bit - lsb}")
    return out


def load(path):
    regmap = yaml.safe_load(Path(path).read_text())
    validate(regmap)
    return regmap


# ---------------------------------------------------------------- validation

def validate(regmap):
    errors = []
    meta = regmap["meta"]
    data_width, addr_width = meta["data_width"], meta["addr_width"]
    dies = set(meta.get("dies", []))
    seen = {}
    for reg in regmap["registers"]:
        off = reg["offset"]
        if off in seen:
            errors.append(f"offset {off} claimed by both {seen[off]} and {reg['name']}")
        seen[off] = reg["name"]
        if off >= 1 << addr_width:
            errors.append(f"{reg['name']} at {off} runs past the {addr_width}-bit address space")
        for field in reg["fields"]:
            msb, lsb, width = parse_bits(field["bits"])
            if msb >= data_width:
                errors.append(f"{reg['name']}.{field['name']} bit {msb} exceeds the {data_width}-bit word")
            reset = field.get("reset")
            if reset is None:
                errors.append(f"{reg['name']}.{field['name']} has no reset value")
            elif reset >= 1 << width:
                errors.append(f"{reg['name']}.{field['name']} reset {reset} does not fit in {width} bit(s)")
            for key in ("hold",):
                if key in field and field[key] >= 1 << width:
                    errors.append(f"{reg['name']}.{field['name']} {key} does not fit in {width} bit(s)")
            if "hold" in field and field["hold"] != reset:
                errors.append(f"{reg['name']}.{field['name']} holds {field['hold']} but resets to {reset}")
            if reset is not None and reset in field.get("forbid", []):
                errors.append(f"{reg['name']}.{field['name']} resets to a forbidden value")
            for bit in field.get("names", {}):
                if not lsb <= bit <= msb:
                    errors.append(f"{reg['name']}.{field['name']} names bit {bit} outside {field['bits']}")
            for d in set(field.get("used", [])) | ({field["only"]} if "only" in field else set()):
                if d not in dies:
                    errors.append(f"{reg['name']}.{field['name']} names die {d}, not in meta.dies")
        for die in meta.get("dies", []):
            used = {}
            for field in die_fields(reg, die):
                for bit in sorted(field_bits(field)):
                    if bit in used:
                        errors.append(f"{reg['name']} bit {bit} used by both {used[bit]} and {field['name']} on {die}")
                    used[bit] = field["name"]
            if len(used) != data_width:
                errors.append(f"{reg['name']} leaves bits unassigned on {die}: {sorted(set(range(data_width)) - set(used))}")
        if reg.get("access") == "const" and reg.get("value") != reg_reset(reg):
            errors.append(f"{reg['name']} value {reg.get('value')} is not what its fields reset to")
    if errors:
        raise SystemExit("\n".join(f"regmap: {e}" for e in errors))


# ---------------------------------------------------------------- VHDL

def vhdl_word(value, width):
    return f'x"{value:0{(width + 3) // 4}X}"' if width % 4 == 0 else f'"{value:0{width}b}"'


def gen_vhdl(regmap, src):
    meta = regmap["meta"]
    aw, dw = meta["addr_width"], meta["data_width"]
    rng = f"natural range 0 to 2**REG_SIZE_BIT-1"
    out = [f"-- Generated by macros/scripts/regmap_gen.py from {src}, do not edit.",
           "-- SPDX-FileCopyrightText: 2026 Michael Koefinger",
           "-- SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1",
           "library ieee;", "use ieee.std_logic_1164.all;", "",
           f"package {meta['vhdl_package']} is", "",
           f"    constant REG_SIZE_BIT : natural := {aw};  -- address bits, the frame's first bit is the read flag",
           f"    constant DSA1_ADDR_MSB : natural := {aw};",
           f"    constant DSA1_DATA_MSB : natural := {dw - 1};",
           f"    constant ADC_REG_CNT : {rng} := {meta['adc_regs']};", ""]
    regs = die_view(regmap, own_die(regmap))
    for reg in regs:
        name = reg.get("vhdl", reg["name"])
        out.append(f"    -- {reg['name']}: {reg.get('desc', '').strip().splitlines()[0] if reg.get('desc') else ''}".rstrip(": "))
        out.append(f"    constant {name}_ADDR : {rng} := {reg['offset']};")
        if reg["access"] == "rw":
            out.append(f"    constant {name}_RESET_VALUE : std_ulogic_vector({dw - 1} downto 0) := {vhdl_word(reg['reset'], dw)};")
        if reg["access"] == "const":
            out.append(f"    constant {name}_VALUE : std_ulogic_vector({dw - 1} downto 0) := {vhdl_word(reg['value'], dw)};")
        for f in reg["fields"]:
            msb, lsb, width = parse_bits(f["bits"])
            if "vhdl" in f:
                if width == 1:
                    out.append(f"    constant {f['vhdl']} : natural := {lsb};")
                else:
                    out.append(f"    constant {f['vhdl']}_LO : natural := {lsb};")
                    out.append(f"    constant {f['vhdl']}_HI : natural := {msb};")
            for key, val in f.get("enum", {}).items():
                out.append(f"    constant {f['name']}_{key} : std_ulogic_vector({width - 1} downto 0) := {vhdl_word(val, width)};")
        out.append("")
    out.append(f"end package {meta['vhdl_package']};")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- Verilog and C

def gen_vh(regmap, src):
    meta = regmap["meta"]
    p = meta["c_prefix"]
    out = [f"// Generated by macros/scripts/regmap_gen.py from {src}, do not edit.",
           "// SPDX-FileCopyrightText: 2026 Michael Koefinger",
           "// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1",
           f"`ifndef {p}_REGS_VH", f"`define {p}_REGS_VH"]
    for reg in die_view(regmap, own_die(regmap)):
        n = f"{p}_{reg['name']}"
        out.append(f"`define {n}_ADDR {meta['addr_width']}'d{reg['offset']}")
        out.append(f"`define {n}_RESET {meta['data_width']}'h{reg['reset']:04X}")
        for f in reg["fields"]:
            if f.get("reserved"):
                continue
            msb, lsb, _ = parse_bits(f["bits"])
            out.append(f"`define {n}_{f['name']}_LSB {lsb}")
            out.append(f"`define {n}_{f['name']}_MSB {msb}")
    out.append("`endif")
    return "\n".join(out) + "\n"


def gen_h(regmap, src):
    meta = regmap["meta"]
    p = meta["c_prefix"]
    out = [f"/* Generated by macros/scripts/regmap_gen.py from {src}, do not edit. */",
           "/* SPDX-FileCopyrightText: 2026 Michael Koefinger */",
           "/* SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1 */",
           f"#ifndef {p}_REGS_H", f"#define {p}_REGS_H", ""]
    for reg in die_view(regmap, own_die(regmap)):
        n = f"{p}_{reg['name']}"
        out.append(f"#define {n}_ADDR {reg['offset']}u")
        out.append(f"#define {n}_RESET 0x{reg['reset']:04X}u")
        for f in reg["fields"]:
            if f.get("reserved"):
                continue
            msb, lsb, width = parse_bits(f["bits"])
            out.append(f"#define {n}_{f['name']}_LSB {lsb}u")
            out.append(f"#define {n}_{f['name']}_MASK 0x{((1 << width) - 1) << lsb:04X}u")
        out.append("")
    out.append(f"#endif /* {p}_REGS_H */")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- Python

def gen_py(regmap, src):
    """Plain data, no import beyond the standard library, so every tool and CI can read it."""
    meta = regmap["meta"]
    dies = {}
    for die in meta["dies"]:
        regs = []
        for reg in die_view(regmap, die):
            fields = []
            for f in reg["fields"]:
                msb, lsb, _ = parse_bits(f["bits"])
                fields.append(dict(name=f["name"], msb=msb, lsb=lsb, reset=f["reset"],
                                   used=f["used"], reserved=bool(f.get("reserved")),
                                   hold=f.get("hold"), forbid=list(f.get("forbid", [])),
                                   enum=dict(f.get("enum", {})), bit_names=bit_names(f),
                                   desc=" ".join(str(f.get("desc", "")).split())))
            regs.append(dict(name=reg["name"], addr=reg["offset"], access=reg["access"],
                             reset=reg["reset"], fields=fields))
        dies[die] = regs
    return (f'"""Generated by macros/scripts/regmap_gen.py from {src}, do not edit."""\n'
            "# SPDX-FileCopyrightText: 2026 Michael Koefinger\n"
            "# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1\n\n"
            f"ADDR_WIDTH = {meta['addr_width']}\n"
            f"DATA_WIDTH = {meta['data_width']}\n"
            f"DIES = {meta['dies']!r}\n"
            f"REGISTERS = {dies!r}\n")


# ---------------------------------------------------------------- Markdown

def gen_md(regmap, src):
    out = ["<!--", "SPDX-FileCopyrightText: 2026 Michael Koefinger", "SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1",
           "-->", "", "# Register map", "",
           f"Generated by `macros/scripts/regmap_gen.py` from `{src}`, do not edit.",
           "16-bit registers, 4-bit addresses. The SPI frame is in [host_protocol.md](host_protocol.md).", "",
           "| Addr | Register | Reset | Access | Drives | " + " | ".join(f"Used on {d}" for d in regmap["meta"]["dies"]) + " |",
           "|---|---|---|---|---|" + "---|" * len(regmap["meta"]["dies"])]
    views = {d: {r["offset"]: r for r in die_view(regmap, d)} for d in regmap["meta"]["dies"]}
    use = lambda r: ", ".join(f["name"] for f in r["fields"] if f["used"]) or "nothing"
    for reg in die_view(regmap, own_die(regmap)):
        cells = []
        for d in regmap["meta"]["dies"]:
            r = views[d][reg["offset"]]
            extra = "" if r["access"] == reg["access"] else f" ({r['access']}, reset 0x{r['reset']:04X})"
            cells.append(use(r) + extra)
        out.append(f"| {reg['offset']} | {reg['name']} | 0x{reg['reset']:04X} | {reg['access']} | {reg.get('drives', '')} | "
                   + " | ".join(cells) + " |")
    for reg in die_view(regmap, own_die(regmap)):
        out += ["", f"## {reg['offset']} {reg['name']}", ""]
        if reg.get("desc"):
            out += [" ".join(reg["desc"].split()), ""]
        out += ["| Bits | Field | Reset | Rule | Description |", "|---|---|---|---|---|"]
        for f in reg["fields"]:
            rule = []
            if "hold" in f:
                rule.append(f"always {f['hold']}")
            if f.get("forbid"):
                rule.append("never " + ", ".join(str(v) for v in f["forbid"]))
            desc = " ".join(str(f.get("desc", "")).split())
            if f.get("enum"):
                desc += (" " if desc else "") + ", ".join(f"{k} = {v}" for k, v in f["enum"].items())
            if f.get("only"):
                desc += (" " if desc else "") + f"(only on {f['only']})"
            out.append(f"| {f['bits']} | {f['name']} | 0x{f['reset']:X} | {', '.join(rule)} | {desc} |")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- targets

def targets(macro_dir):
    macro_dir = Path(macro_dir)
    return [(gen_vhdl, macro_dir / "rtl" / "dsa1_regs.vhd"),
            (gen_vh, macro_dir / "rtl" / "dsa1_regs.vh"),
            (gen_h, macro_dir / "sw" / "dsa1_regs.h"),
            (gen_py, REPO / "models" / "regmap_defs.py"),
            (gen_md, REPO / "doc" / "regmap.md")]


def run(yaml_path, check):
    yaml_path = Path(yaml_path).resolve()
    regmap = load(yaml_path)
    src = str(yaml_path.relative_to(REPO)) if yaml_path.is_relative_to(REPO) else yaml_path.name
    stale = []
    for gen, path in targets(yaml_path.parent):
        text = gen(regmap, src)
        if check:
            if not path.exists() or path.read_text() != text:
                stale.append(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    for path in stale:
        print(f"regmap: {path} is stale, run make regmap", file=sys.stderr)
    return 1 if stale else 0


# ---------------------------------------------------------------- tests

def selftest():
    base = {"meta": {"addr_width": 2, "data_width": 8, "dies": ["a", "b"], "vhdl_package": "p",
                     "c_prefix": "T", "adc_regs": 0},
            "registers": [
                {"name": "R0", "offset": 0, "fields": [
                    {"name": "X", "bits": "7:4", "reset": 5, "used": ["a"]},
                    {"name": "Y", "bits": "3:1", "reset": 2, "only": "a", "used": ["a"], "vhdl": "R0_Y", "enum": {"TWO": 2}},
                    {"name": "Z", "bits": "0", "reset": 1, "hold": 1, "names": {0: "ZED"}}]},
                {"name": "ID", "offset": 1, "access": "const", "value": 0x21, "dies": {"b": {"access": "rw", "value": 0}},
                 "fields": [{"name": "ID", "bits": "7:0", "reset": 0x21, "used": ["a", "b"]}]},
                {"name": "R2", "offset": 2, "fields": [
                    {"name": "P", "bits": "7:4", "reset": 9, "only": "b", "used": ["b"]},
                    {"name": "Q", "bits": "3:0", "reset": 3, "only": "b", "used": ["b"]},
                    {"name": "S", "bits": "7:2", "reset": 0, "only": "a", "reserved": True},
                    {"name": "T", "bits": "1:0", "reset": 2, "only": "a", "used": ["a"]}]}]}
    validate(base)
    a, b = die_view(base, "a"), die_view(base, "b")
    assert a[0]["reset"] == 0x55 and b[0]["reset"] == 0x51, (a[0]["reset"], b[0]["reset"])
    assert [f["name"] for f in b[0]["fields"]] == ["X", "TBD", "Z"] and not b[0]["fields"][0]["used"]
    assert a[1]["access"] == "const" and a[1]["reset"] == 0x21
    assert b[1]["access"] == "rw" and b[1]["reset"] == 0, b[1]
    a2, b2 = die_view(base, "a")[2], die_view(base, "b")[2]
    assert [f["name"] for f in a2["fields"]] == ["S", "T"] and a2["reset"] == 0x02, a2
    assert [f["name"] for f in b2["fields"]] == ["P", "Q"] and b2["reset"] == 0x93, b2
    assert bit_names(base["registers"][0]["fields"][0]) == ["X3", "X2", "X1", "X0"]
    assert bit_names({"name": "TBD", "bits": "2:1", "reserved": True}) == ["TBD", "TBD"]
    assert bit_names({"name": "T", "bits": "5:0", "names": {2: "T1", 1: "T2"}}) == ["T5", "T4", "T3", "T1", "T2", "T0"]
    v = gen_vhdl(base, "t.yaml")
    assert "constant R0_ADDR : natural range 0 to 2**REG_SIZE_BIT-1 := 0;" in v, v
    assert 'constant R0_RESET_VALUE : std_ulogic_vector(7 downto 0) := x"55";' in v, v
    assert 'constant ID_VALUE : std_ulogic_vector(7 downto 0) := x"21";' in v and "ID_RESET_VALUE" not in v, v
    assert "constant R0_Y_LO : natural := 1;" in v and "constant R0_Y_HI : natural := 3;" in v, v
    assert 'constant Y_TWO : std_ulogic_vector(2 downto 0) := "010";' in v, v
    ns = {}
    exec(gen_py(base, "t.yaml"), ns)
    assert ns["REGISTERS"]["b"][1]["access"] == "rw" and ns["REGISTERS"]["a"][0]["fields"][2]["hold"] == 1
    for broken, why in ((lambda m: m["registers"][0]["fields"][0].update(bits="7:3"), "used by both"),
                        (lambda m: m["registers"][0]["fields"].pop(), "unassigned"),
                        (lambda m: m["registers"][0]["fields"][2].update(hold=0), "holds"),
                        (lambda m: m["registers"][1].update(value=0x22), "not what its fields"),
                        (lambda m: m["registers"][1].update(offset=0), "claimed by both"),
                        (lambda m: m["registers"][0]["fields"][0].update(used=["c"]), "not in meta.dies"),
                        (lambda m: m["registers"][2]["fields"][0].pop("only"), "used by both"),
                        (lambda m: m["registers"][2]["fields"][3].update(bits="1"), "unassigned")):
        m = yaml.safe_load(yaml.safe_dump(base))
        broken(m)
        try:
            validate(m)
            raise AssertionError(f"validate missed: {why}")
        except SystemExit as e:
            assert why in str(e), (why, str(e))
    # --check sees a stale file and a missing one
    with tempfile.TemporaryDirectory() as td:
        y = Path(td) / "m" / "regmap.yaml"
        y.parent.mkdir()
        y.write_text(yaml.safe_dump(base))
        global REPO
        repo, REPO = REPO, Path(td)
        try:
            assert run(y, check=True) == 1
            assert run(y, check=False) == 0 and run(y, check=True) == 0
            (Path(td) / "doc" / "regmap.md").write_text("old\n")
            assert run(y, check=True) == 1
        finally:
            REPO = repo
    print("regmap_gen.py selftest: OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("yaml", nargs="?", default=str(REPO / "macros" / "dsa1_dig" / "regmap.yaml"))
    ap.add_argument("--check", action="store_true", help="exit 1 if a generated file is stale")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    return run(a.yaml, a.check)


if __name__ == "__main__":
    sys.exit(main())
