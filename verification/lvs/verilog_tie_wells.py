#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""A powered Verilog netlist for top_lvs.sh with every cell's well pins connected: VNW to VDD, VPW to VSS.

    verilog_tie_wells.py <cells.cdl> [<more.cdl> ...] <in.pnl.v> <out.pnl.v>
    verilog_tie_wells.py --self-test

The EZ130 CDL gives every cell VNW and VPW pins and the powered Verilog connects neither, so read
as they are each instance gets two floating nets. Tied here per instance, the reference keeps the
CDL's cells as they are, and the layout's cells, whose wells are ports of their own, match them
cell by cell. A well region the taps do not reach still shows up, as a net that never meets VDD.
"""
import re
import sys

INST = re.compile(r"^(?P<lead>\s*)(?P<cell>[A-Za-z0-9_]+) (?P<inst>\\\S+ |\S+) \(", re.M)


def well_cells(cdl_text):
    cells = set()
    for m in re.finditer(r"^\s*\.subckt\s+(\S+)\s+(.*)$", cdl_text, re.I | re.M):
        pins = m.group(2).split()
        if "VNW" in pins and "VPW" in pins:
            cells.add(m.group(1))
    return cells


def tie(verilog, cells):
    def sub(m):
        if m.group("cell") not in cells:
            return m.group(0)
        return f"{m.group('lead')}{m.group('cell')} {m.group('inst')} (.VNW(VDD), .VPW(VSS), "
    return INST.sub(sub, verilog)


def self_test():
    cells = well_cells(".SUBCKT INVX1 A Y VDD VNW VPW VSS\n.ENDS\n.SUBCKT FILLER1 VDD VSS\n.ENDS\n")
    assert cells == {"INVX1"}, cells
    v = " INVX1 _1_ (.VSS(VSS),\n    .A(a));\n INVX1 \\u.x[0]  (.VSS(VSS));\n FILLER1 f (.VDD(VDD));\n dsa1_dig_top m (.VDD(VDD));\n"
    out = tie(v, cells)
    assert " INVX1 _1_ (.VNW(VDD), .VPW(VSS), .VSS(VSS)," in out, out
    assert " INVX1 \\u.x[0]  (.VNW(VDD), .VPW(VSS), .VSS(VSS));" in out, out
    assert " FILLER1 f (.VDD(VDD));" in out and " dsa1_dig_top m (.VDD(VDD));" in out, out
    print("OK: verilog_tie_wells self-test")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    *cdls, src, dst = sys.argv[1:]
    cells = set().union(*(well_cells(open(c).read()) for c in cdls))
    open(dst, "w").write(tie(open(src).read(), cells))
