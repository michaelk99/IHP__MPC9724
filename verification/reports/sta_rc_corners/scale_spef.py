#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Scale every wire capacitance (ground and coupling) and every wire resistance of a SPEF by one factor each.
# The net total in *D_NET follows the cap factor. Pin loads (*L) are not scaled, the three SPEFs read here have none.
# usage: scale_spef.py <in> <out> <r_factor> <c_factor>
import sys

src, dst, rf, cf = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
sect = None
with open(src) as f, open(dst, "w") as o:
    for line in f:
        w = line.split()
        if line.startswith("*D_NET") and len(w) == 3:
            line = f"{w[0]} {w[1]} {float(w[2]) * cf:.6g}\n"
            sect = None
        elif line.startswith("*CAP"):
            sect = "c"
        elif line.startswith("*RES"):
            sect = "r"
        elif line.startswith("*END") or line.startswith("*CONN"):
            sect = None
        elif sect and w and w[0].isdigit():
            fac = cf if sect == "c" else rf
            w[-1] = f"{float(w[-1]) * fac:.6g}"
            line = " ".join(w) + "\n"
        o.write(line)
