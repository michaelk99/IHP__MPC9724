# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# From OpenBLAU 8f25e634, ip/sg13cmos5l_ip__rfpad_70x70
# Description: read a LEF macro's supply rail bands, so the clamp cell never
#              writes a rail y position down

import os
import re
import sys

LEF_PATH = os.path.join(os.environ.get("PDK_ROOT", "/foss/pdks"),
                        os.environ.get("PDK", "ihp-sg13cmos5l"),
                        "libs.ref", "sg13cmos5l_io", "lef", "sg13cmos5l_io.lef")
# the bands the clamp cell copies, those of the IO filler cells
FILLER = "sg13cmos5l_Filler2000"

SUPPLY = ("iovss", "iovdd", "vss", "vdd")


def rails(lef_path=LEF_PATH, macro=FILLER):
    """Supply rail bands of `macro`, as {net: [(layer, y0, y1), ...]}.

    Only Metal3, Metal4 and TopMetal1 count, and a band is a rail only if it
    spans the whole cell width.
    """
    with open(lef_path, encoding="utf-8") as fh:
        text = fh.read()
    body = re.search(r"^MACRO %s$(.*?)^END %s$" % (macro, macro),
                     text, re.S | re.M)
    if body is None:
        raise KeyError("no MACRO %s in %s" % (macro, lef_path))
    width = float(re.search(r"SIZE\s+([\d.]+)\s+BY", body.group(1)).group(1))

    out = {n: set() for n in SUPPLY}
    net = layer = None
    for line in body.group(1).splitlines():
        line = line.strip()
        if line.startswith("#"):
            continue
        m = re.match(r"PIN\s+(\S+)", line)
        if m:
            net, layer = m.group(1), None
            continue
        # A bare END closes a PORT, "END <name>" closes the PIN.
        if line == "END":
            layer = None
            continue
        if line.startswith("END "):
            net = layer = None
            continue
        m = re.match(r"LAYER\s+(\S+)\s*;", line)
        if m:
            layer = m.group(1)
            continue
        m = re.match(r"RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s*;", line)
        if m and net in out and layer in ("Metal3", "Metal4", "TopMetal1"):
            x0, y0, x1, y1 = (float(v) for v in m.groups())
            if x0 == 0.0 and x1 == width:
                out[net].add((layer, y0, y1))
    return {n: sorted(v) for n, v in out.items()}


def selftest():
    """The bands the IO fillers have, read 2026-10-07 from the 2026.08 image."""
    got = rails()
    assert got["iovdd"] == [
        ("Metal3", 66.0, 91.5), ("Metal3", 93.5, 119.0),
        ("Metal4", 66.0, 91.5), ("Metal4", 93.5, 119.0),
        ("TopMetal1", 66.0, 91.5), ("TopMetal1", 93.5, 119.0),
    ], got["iovdd"]
    assert got["iovss"] == [
        ("Metal3", 7.0, 32.5), ("Metal3", 34.5, 60.0), ("Metal3", 126.0, 134.0),
        ("Metal4", 7.0, 32.5), ("Metal4", 34.5, 60.0), ("Metal4", 126.0, 134.0),
        ("TopMetal1", 7.0, 32.5), ("TopMetal1", 34.5, 60.0),
        ("TopMetal1", 126.0, 134.0),
    ], got["iovss"]
    assert got["vdd"] == [("Metal3", 160.0, 178.0), ("Metal4", 140.0, 155.8)], got["vdd"]
    assert got["vss"] == [("Metal3", 140.0, 158.0), ("Metal4", 162.2, 178.0)], got["vss"]
    print("rails: selftest ok")


if __name__ == "__main__":
    sys.exit(selftest())
