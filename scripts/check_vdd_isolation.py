#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Check in the DEF that VDD and VDDA share no pin and that VDDA reaches exactly its segment.

    check_vdd_isolation.py <def> [--segment a,b,...] [--macro dsm2] [--cut-s cut_vdd_s] [--cut-e cut_vdd_e]

VDDA must hold the vdd pin of every segment pad, of the macro, and of the IO fillers and the corner between the two cut cells. VDD must hold none of them.
The south side runs left to right and the east side bottom to top, so the segment is every south cell at or right of the south cut, the south-east corner, and every east cell below the east cut.
"""

import argparse
import re
import sys

SEGMENT = "dsm_clk_pad,do_q_pad,do_q_b_pad,vi_pad,vcm_pad,ib_pad,vdda_pad,clamp_vdda"


def parse(text):
    """Return (components, nets): name -> (master, x, y) in dbu, net -> {(inst, pin)}."""
    comps, nets = {}, {}
    m = re.search(r"^COMPONENTS\s+\d+\s*;(.*?)^END COMPONENTS", text, flags=re.S | re.M)
    for stmt in (m.group(1) if m else "").split(";"):
        c = re.match(r"\s*-\s+(\S+)\s+(\S+)\s.*?\(\s*(-?\d+)\s+(-?\d+)\s*\)", stmt, flags=re.S)
        if c:
            comps[c.group(1)] = (c.group(2), int(c.group(3)), int(c.group(4)))
    m = re.search(r"^SPECIALNETS\s+\d+\s*;(.*?)^END SPECIALNETS", text, flags=re.S | re.M)
    for stmt in (m.group(1) if m else "").split(";"):
        n = re.match(r"\s*-\s+(\S+)(.*)", stmt, flags=re.S)
        if not n:
            continue
        head = re.split(r"\+", n.group(2), maxsplit=1)[0]
        pins = set()
        for inst, pin in re.findall(r"\(\s*(\S+)\s+(\S+)\s*\)", head):
            if inst not in ("PIN", "*"):
                pins.add((inst, pin))
        nets[n.group(1)] = pins
    return comps, nets


def check(text, segment=SEGMENT, macro="dsm2", cut_s="cut_vdd_s", cut_e="cut_vdd_e"):
    """Return a list of failure messages, empty on PASS."""
    comps, nets = parse(text)
    fails = []
    for need in (cut_s, cut_e, macro):
        if need not in comps:
            return ["no component %s in the DEF" % need]
    for net in ("VDD", "VDDA"):
        if net not in nets:
            return ["no special net %s in the DEF" % net]
    names = set(segment.split(",")) | {macro}
    sx = comps[cut_s][1]
    ey = comps[cut_e][2]
    die_south = comps[cut_s][2]
    for name in names:
        if name not in comps:
            fails.append("segment cell %s is not in the DEF" % name)
    # filler and corner cells of the ring on the two sides of the cut cells
    for name, (master, x, y) in comps.items():
        if "Filler" in master or "Corner" in master:
            south = y == die_south and x >= sx
            east = x == comps[cut_e][1] and y < ey
            if south or east or (x == comps[cut_e][1] and y == die_south):
                names.add(name)
    want = {(n, "vdd") for n in names if comps.get(n, ("", 0, 0))[0] != "sg13cmos5l_ip__cut_vdd"}
    got_a = {p for p in nets["VDDA"] if p[1].lower() == "vdd"}
    got_d = {p for p in nets["VDD"] if p[1].lower() == "vdd"}
    for inst, pin in sorted(got_a & got_d):
        fails.append("%s/%s is on both VDD and VDDA" % (inst, pin))
    for inst, pin in sorted(want - got_a):
        fails.append("%s/%s is not on VDDA%s" % (inst, pin, " but on VDD" if (inst, pin) in got_d else ""))
    for inst, pin in sorted(got_a - want):
        fails.append("%s/%s is on VDDA but outside the segment" % (inst, pin))
    for cut in (cut_s, cut_e):
        for net in ("VDD", "VDDA"):
            for inst, pin in sorted(p for p in nets[net] if p[0] == cut):
                fails.append("%s/%s is on %s, the cut cell has no vdd" % (inst, pin, net))
    return fails


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("def_file")
    ap.add_argument("--segment", default=SEGMENT)
    ap.add_argument("--macro", default="dsm2")
    ap.add_argument("--cut-s", default="cut_vdd_s")
    ap.add_argument("--cut-e", default="cut_vdd_e")
    args = ap.parse_args()
    text = open(args.def_file).read()
    fails = check(text, args.segment, args.macro, args.cut_s, args.cut_e)
    comps, nets = parse(text)
    for net in ("VDD", "VDDA"):
        pins = sorted(p for p in nets.get(net, ()) if p[1].lower() == "vdd")
        print("%s: %d vdd pins%s" % (net, len(pins), "" if net == "VDD" else ": " + " ".join(i for i, _ in pins)))
    for f in fails:
        print("FAIL: " + f)
    print("check_vdd_isolation: " + ("FAIL" if fails else "PASS"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
