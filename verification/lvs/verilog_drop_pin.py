#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""A powered Verilog netlist for top_lvs.sh with one named connection dropped from the instances of
the cells a regex matches.

    verilog_drop_pin.py <cell regex> <pin> <in.v> <out.v>
    verilog_drop_pin.py --self-test

Used for the IO cells' vss: their core ground sits on the substrate inside the cell, which Magic
keeps as one implicit node and never exports as a port.
"""
import re
import sys

INST = re.compile(r"^(?P<head>\s*(?P<cell>[A-Za-z0-9_]+) (?:\\\S+ |\S+) \()(?P<body>.*?)\);", re.M | re.S)


def drop(verilog, cell_rx, pin):
    cell_rx = re.compile(cell_rx)
    conn = re.compile(r"\s*\.%s\([^()]*\)" % re.escape(pin))

    def sub(m):
        if not cell_rx.match(m.group("cell")):
            return m.group(0)
        parts = [p for p in re.split(r",(?=\s*\.)", m.group("body")) if not conn.fullmatch(p)]
        return m.group("head") + ",".join(parts) + ");"
    return INST.sub(sub, verilog)


def self_test():
    v = (" sg13cmos5l_IOPadIn \\pad[0]  (.iovdd(IOVDD),\n    .vss(VSS),\n    .pad(p));\n"
         " sg13cmos5l_Corner c (.iovss(VSS),\n    .vss(VSS));\n"
         " dsa1_dig_top m (.VSS(VSS),\n    .vss_x(a));\n")
    out = drop(v, r"^sg13cmos5l_", "vss")
    assert " sg13cmos5l_IOPadIn \\pad[0]  (.iovdd(IOVDD),\n    .pad(p));" in out, out
    assert " sg13cmos5l_Corner c (.iovss(VSS));" in out, out
    assert " dsa1_dig_top m (.VSS(VSS),\n    .vss_x(a));" in out, out
    print("OK: verilog_drop_pin self-test")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    rx, pin, src, dst = sys.argv[1:]
    text = open(src).read()        # src may be dst
    open(dst, "w").write(drop(text, rx, pin))
