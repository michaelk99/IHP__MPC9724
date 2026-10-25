#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: Turn EZ130's CDL into an ngspice-callable stdcell view

"""EZ130 ships its cells as CDL and the PDK library ships SPICE, and the two
are not interchangeable for simulation.

    EZ130    MN0 Y A VSS VPW sg13_lv_nmos m=1 w=860.00n l=130.00n ng=1
    PDK      XN0 Y A VSS VSS sg13_lv_nmos w=740.00n l=130.00n ng=1 ... m=1

`sg13_lv_nmos` is a SUBCIRCUIT in this PDK, not a `.model`, so ngspice reads
the M-card as a MOSFET whose model does not exist and stops with "could not
find a valid modelname" and then "incomplete or empty netlist" -- which reads
as a broken deck rather than as a card-type mismatch. netgen is happy with
either, which is why LVS works off the CDL and only simulation needs this.

The conversion is one character per device line, M to X, plus the parameters
carried through untouched. EZ130's cards carry no `ad/as/pd/ps`, so the
junction areas the PDK view supplies are simply absent: fine for a functional
or timing deck, not for a leakage number.

THE BARE `.PARAM` IS ALSO DROPPED, and it is not cosmetic. The CDL's Cadence
header ends `*.SCALE METER / *.MEGA / .PARAM`, a `.PARAM` with nothing on it.
Under `ngbehavior=hsa`, which the container's own `.spiceinit` sets, ngspice
maps that to an HSPICE `.func` and dies with

    ERROR: failed to parse .func in: .func

naming no file and no line. It only fires when a real `.param` or `.temp`
appears BEFORE the include, which is why one deck in this repo hit it and
another, whose `.temp` happens to come after the netlist, never did. That kind
of ordering dependence is worse than a plain failure, so the line goes here
rather than each deck working around it.

    python3 cdl2spice.py [<in.cdl>] [<out.spice>]

Defaults to this library's own CDL, writing next to it. `--selftest` checks the
round trip on the library itself.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IP = os.path.dirname(HERE)
CDL = os.path.join(IP, "cdl", "ez130_8t.cdl")
OUT = os.path.join(IP, "spice", "ez130_8t.spice")

DEV = re.compile(r"^M(?P<name>\S+)\s+(?P<rest>.*)$", re.IGNORECASE)
MODELS = ("sg13_lv_nmos", "sg13_lv_pmos", "sg13_hv_nmos", "sg13_hv_pmos")
# a `.PARAM` carrying no assignment; see the module docstring
EMPTY_PARAM = re.compile(r"^\.param\s*$", re.IGNORECASE)


def convert(text):
    """CDL text -> ngspice text. Returns (text, devices converted)."""
    out, n = [], 0
    for line in text.splitlines():
        m = DEV.match(line)
        if m and any(k in line for k in MODELS):
            out.append("X%s %s" % (m.group("name"), m.group("rest")))
            n += 1
        elif EMPTY_PARAM.match(line):
            out.append("* %s   (dropped: empty .PARAM reads as .func under hsa)"
                       % line.strip())
        else:
            out.append(line)
    return "\n".join(out) + "\n", n


def _selftest():
    src = open(CDL).read()
    txt, n = convert(src)
    assert n > 0, "no devices converted"
    assert not re.search(r"^M\S+.*sg13_lv_", txt, re.M), "an M-card survived"
    assert txt.count(".SUBCKT") == src.count(".SUBCKT"), "subcircuit lost"
    # the CDL really does carry the bare .PARAM, and none survives the convert
    assert re.search(r"^\.param\s*$", src, re.M | re.I), \
        "the CDL no longer has a bare .PARAM -- drop the workaround"
    assert not re.search(r"^\.param\s*$", txt, re.M | re.I), \
        "a bare .PARAM survived; ngspice would read it as .func under hsa"
    # every converted line keeps its four terminals and its model
    for line in txt.splitlines():
        if line.startswith("X") and "sg13_lv_" in line:
            t = line.split()
            assert len(t) >= 6, line
            assert t[5] in MODELS, line
    print("cdl2spice selftest OK: %d devices, %d subcircuits"
          % (n, src.count(".SUBCKT")))


def main():
    if "--selftest" in sys.argv:
        _selftest()
        return
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    src = args[0] if args else CDL
    dst = args[1] if len(args) > 1 else OUT
    txt, n = convert(open(src).read())
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "w").write(txt)
    print("wrote %s (%d devices)" % (dst, n))


if __name__ == "__main__":
    main()
