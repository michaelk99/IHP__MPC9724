#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Negative controls for top_lvs.sh: edit the reference netlist copy so the layout must no longer match.

    mutate_reference.py vdda_to_vdd  <chip pnl copy>    VDDA joined to VDD
    mutate_reference.py and3bx1_swap <macro pnl copy>   AB and B of the first AND3BX1 swapped
    mutate_reference.py cut_pin      <chip pnl copy>    the iovdd pin of the first cut_vdd cell moved to VDD
    mutate_reference.py dsm2_pins    <chip pnl copy>    the nets of dsm2's di_ena and di_rst_b swapped
"""
import re
import sys


def vdda_to_vdd(text):
    text = re.sub(r"^\s*VDDA,\s*\n|^\s*inout VDDA;\s*\n", "", text, flags=re.M)
    text, n = re.subn(r"\bVDDA\b", "VDD", text)
    assert n, "no VDDA in the netlist"
    return text


def and3bx1_swap(text):
    m = re.search(r"^ AND3BX1 \S+ \((.*?)\);", text, flags=re.M | re.S)
    assert m, "no AND3BX1 in the netlist"
    body = m.group(1)
    ab = re.search(r"\.AB\(([^)]*)\)", body)
    b = re.search(r"\.B\(([^)]*)\)", body)
    assert ab and b and ab.group(1) != b.group(1)
    new = body.replace(f".AB({ab.group(1)})", ".AB(@@)").replace(f".B({b.group(1)})", f".B({ab.group(1)})").replace(".AB(@@)", f".AB({b.group(1)})")
    return text[:m.start(1)] + new + text[m.end(1):]


def cut_pin(text):
    m = re.search(r"^ sg13cmos5l_ip__cut_vdd \S+ \(\.iovdd\(IOVDD\)", text, flags=re.M)
    assert m, "no cut_vdd cell in the netlist"
    return text[:m.end() - len("IOVDD)")] + "VDD)" + text[m.end():]


def dsm2_pins(text):
    m = re.search(r"^ dsm2_core \S+ \((.*?)\);", text, flags=re.M | re.S)
    assert m, "no dsm2_core in the netlist"
    body = m.group(1)
    a = re.search(r"\.di_ena\(([^)]*)\)", body)
    b = re.search(r"\.di_rst_b\(([^)]*)\)", body)
    assert a and b and a.group(1) != b.group(1)
    new = body.replace(f".di_ena({a.group(1)})", ".di_ena(@@)").replace(f".di_rst_b({b.group(1)})", f".di_rst_b({a.group(1)})").replace(".di_ena(@@)", f".di_ena({b.group(1)})")
    return text[:m.start(1)] + new + text[m.end(1):]


MUTANTS = {"vdda_to_vdd": vdda_to_vdd, "and3bx1_swap": and3bx1_swap, "cut_pin": cut_pin, "dsm2_pins": dsm2_pins}

if __name__ == "__main__":
    name, path = sys.argv[1:3]
    text = MUTANTS[name](open(path).read())
    open(path, "w").write(text)
