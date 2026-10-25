# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: Vet every cell name in the EZ130 LibreLane SCL config against the library

"""The SCL config, the exclude lists and the techmaps are hand-written, and a
wrong cell name in any of them fails somewhere far away: a bad `FILL_CELLS`
entry is silent, a bad `DIODE_CELL` dies in antenna repair, a liberty-only name
dies in placement as "LEF master not found", a bad techmap pin dies in yosys.

This checks all of them mechanically against `lef/ez130_8t.lef` (the macros) and
`lib/ez130_8t_tt_1p20v_25c.lib` (the cells and their pins), with the role
deciding which list a name has to be in:

  liberty + LEF   anything synthesis or CTS can choose
  LEF only        physical-only cells (fill, welltap)
  pins            every techmap and every <cell>/<pin> triple in the config

It does NOT judge whether the exclude list is the RIGHT set, only that every
name in it exists. Deciding what belongs there is in doc/sg13cmos5l_adaptation.md.

    python3 ip/ez130_8t_v1p1/scripts/check_scl_config.py
"""

import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
IP = os.path.dirname(HERE)
LEF = os.path.join(IP, "lef", "ez130_8t.lef")
LIB = os.path.join(IP, "lib", "ez130_8t_tt_1p20v_25c.lib")
LL = os.path.join(IP, "librelane")


def library():
    lef = set(re.findall(r"^MACRO (\S+)", open(LEF).read(), re.M))
    t = open(LIB).read()
    parts = re.split(r"\n  cell \((\S+?)\) \{\n", t)
    cells = {}
    for i in range(1, len(parts), 2):
        body = parts[i + 1]
        pins = {}
        ps = re.split(r"\n    pin \((\S+?)\) \{\n", body)
        for j in range(1, len(ps), 2):
            head = ps[j + 1].split("\n    }")[0]
            m = re.search(r"direction : (\w+)", head)
            pins[ps[j]] = m.group(1) if m else "?"
        cells[parts[i]] = pins
    return lef, cells


def expand(pat, names):
    if "*" not in pat:
        return [pat]
    rx = re.compile("^" + pat.replace("*", ".*") + "$")
    return sorted(n for n in names if rx.match(n))


def main():
    lef, lib = library()
    errs, notes = [], []

    cfg = yaml.safe_load(open(os.path.join(LL, "config.yaml")))

    def val(var):
        """The value as one space-separated string, as the checks read it."""
        v = cfg.get(var)
        if v is None:
            return None
        return " ".join(map(str, v)) if isinstance(v, list) else str(v)

    # role -> (variable, must be in liberty?)
    roles = [
        ("SYNTH_DRIVING_CELL", True), ("SYNTH_CLK_DRIVING_CELL", True),
        ("CTS_ROOT_BUFFER", True),
        ("CTS_CLK_BUFFERS", True), ("DECAP_CELLS", True),
        ("TRISTATE_CELLS", True), ("FILL_CELLS", False),
        ("CELL_PAD_EXCLUDE", False),
    ]
    for var, need_lib in roles:
        v = val(var)
        if v is None:
            errs.append(f"{var}: not set in config.yaml")
            continue
        for pat in v.split():
            pat = pat.split("/")[0]
            got = expand(pat, lef)
            if not got:
                errs.append(f"{var}: '{pat}' matches no LEF MACRO")
                continue
            for c in got:
                if need_lib and c not in lib:
                    errs.append(f"{var}: {c} is not a liberty cell (placement would fail)")
            notes.append(f"  {var:<24} {pat:<12} -> {len(got)} cell(s): {' '.join(got[:6])}")

    # DIODE_CELL is CELL/PIN, and the slash is load-bearing: every LibreLane
    # consumer splits on it, and odb.py and reader.py unpack into exactly two
    # variables, so a bare name crashes RUN_HEURISTIC_DIODE_INSERTION with
    # "not enough values to unpack" and names no variable. antenna_repair.tcl
    # takes element 0, which is why a bare name survives until something turns
    # the heuristic pass on.
    dv = val("DIODE_CELL")
    if not dv:
        errs.append("DIODE_CELL: not set in config.yaml")
    elif "/" not in dv:
        errs.append(f"DIODE_CELL: '{dv}' must be CELL/PIN, not a bare cell name")
    else:
        dcell, dpin = dv.split("/", 1)
        if dcell not in lef:
            errs.append(f"DIODE_CELL: {dcell} matches no LEF MACRO")
        if dcell not in lib:
            errs.append(f"DIODE_CELL: {dcell} is not a liberty cell "
                        "(placement would fail)")
        elif dpin not in lib[dcell]:
            errs.append(f"DIODE_CELL: {dcell} has no pin {dpin} "
                        f"(has {sorted(lib[dcell])})")
        notes.append(f"  {'DIODE_CELL':<24} {dcell} pin {dpin}")

    # CELL/PIN[/PIN] role cells
    for var in ("SYNTH_BUFFER_CELL", "SYNTH_TIEHI_CELL", "SYNTH_TIELO_CELL"):
        v = val(var)
        if not v:
            errs.append(f"{var}: not set")
            continue
        cell, *pins = v.split("/")
        if cell not in lib:
            errs.append(f"{var}: {cell} not in liberty")
            continue
        bad = [p for p in pins if p not in lib[cell]]
        if bad:
            errs.append(f"{var}: {cell} has no pin(s) {bad}")
        notes.append(f"  {var:<24} {v}")

    for var in ("SYNTH_DRIVING_CELL", "SYNTH_CLK_DRIVING_CELL"):
        c, _, p = (val(var) or "").partition("/")
        if c in lib and p not in lib[c]:
            errs.append(f"{var}: {c} has no pin {p}")

    # exclude lists: existence only
    for f in ("synth_exclude.cells", "pnr_exclude.cells"):
        names = [l.strip() for l in open(os.path.join(LL, f))
                 if l.strip() and not l.lstrip().startswith("#")]
        miss = [n for n in names if n not in lef]
        if miss:
            errs.append(f"{f}: not LEF MACROs: {miss}")
        nolib = [n for n in names if n not in lib]
        notes.append(f"  {f:<24} {len(names)} names, all exist"
                     + (f", {len(nolib)} not in liberty: {nolib}" if nolib else ""))

    # techmaps: every instantiated cell and every pin it connects
    for f in ("latch_map.v", "tribuff_map.v", "rca_map.v"):
        src = open(os.path.join(LL, f)).read()
        # An instantiation of a LIBRARY cell: the name is upper case, which is
        # what tells it from the \$pos operators rca_map.v also instantiates.
        for m in re.finditer(r"^\s+([A-Z][A-Z0-9]*)\s+(\w+)\s*\((.*?)\);",
                             src, re.S | re.M):
            cell, inst, conns = m.group(1), m.group(2), m.group(3)
            if cell not in lib:
                errs.append(f"{f}: {cell} is not a liberty cell")
                continue
            pins = re.findall(r"\.(\w+)\(", conns)
            bad = [p for p in pins if p not in lib[cell]]
            if bad:
                errs.append(f"{f}: {cell} has no pin(s) {bad} (has {sorted(lib[cell])})")
            notes.append(f"  {f:<24} {cell:<10} pins {' '.join(pins)}")

    # ICG, named in the design config rather than here, checked in the same shape
    for icg in ("CGX3/E/CK/ECK",):
        cell, en, clk, gclk = icg.split("/")
        if cell not in lib:
            errs.append(f"ICG {icg}: {cell} not in liberty")
        else:
            bad = [p for p in (en, clk, gclk) if p not in lib[cell]]
            if bad:
                errs.append(f"ICG {icg}: {cell} has no pin(s) {bad} (has {sorted(lib[cell])})")
            notes.append(f"  {'ICG':<24} {icg}")

    print(f"library: {len(lef)} LEF macros, {len(lib)} liberty cells")
    print("\n".join(notes))
    if errs:
        print("\nFAIL")
        for e in errs:
            print("  " + e)
        sys.exit(1)
    print("\nOK: every cell and pin named in the SCL config exists")


if __name__ == "__main__":
    main()
