#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: package GDS of IHP's QFN24 (4 x 4 mm, 0.5 mm pitch) for run_bondplan.py
#
# The leads are copied from Mirror Semiconductor's bond diagram M-QFN24T.5-G3_Bond.dxf (https://www.mirrorsemi.com/CAD/M-QFN24T.5-G3_Bond.dxf, not in the repo), which draws each lead as an open finger. Body, cavity and die pad follow QP Technologies drawing 500378 rev A (QP-QFN24-4MM-0.50MM, JEDEC MO-220), which IHP's 4 x 4 QFN24 matches.
# Layers as in the EUROPRACTICE library: 208/0 body ring and die pad, 210/0 one polygon per lead, 211/0 pin numbers. Pin 1 is the top lead of the left side, counted counterclockwise.
#
# Usage, in the image: python3 scripts/gen_qfn24_4mm.py <bond.dxf> layout/QFN24_4MM.gds

import math
import sys

import klayout.db as db
from shapely.geometry import LineString
from shapely.ops import polygonize, unary_union

BODY, CAVITY, PAD = 4.0, 3.4, 2.4       # mm
CORNER_R, CHAMFER = 0.5, 0.4             # mm, three rounded corners, pin-1 chamfer top left
OPEN_END = 1.681                         # mm, where the DXF leaves every finger open
LABEL_OFFSET, LABEL_SIZE = 0.25, 0.15    # mm, pin numbers outside the body
N = 24


def dxf_lines(path):
    """LINE entities of an ASCII DXF as ((x1, y1), (x2, y2)) in mm."""
    tokens = [t.strip() for t in open(path, encoding="latin-1").read().splitlines()]
    pairs = list(zip(tokens[0::2], tokens[1::2]))
    lines, cur = [], None
    for code, val in pairs:
        if code == "0":
            if cur is not None and len(cur) == 4:
                lines.append(((cur["10"], cur["20"]), (cur["11"], cur["21"])))
            cur = {} if val == "LINE" else None
        elif cur is not None and code in ("10", "20", "11", "21"):
            cur[code] = float(val)
    return lines


def side(c):
    x, y = c
    return "L" if x < 0 and abs(x) >= abs(y) else "R" if x > 0 and abs(x) >= abs(y) else "T" if y > 0 else "B"


def leads(lines):
    """Lead polygons in mm, grouped by side. Each finger is open at its outer end, so it is closed there before polygonizing."""
    key = lambda p: (round(p[0], 4), round(p[1], 4))
    deg = {}
    for a, b in lines:
        for p in (key(a), key(b)):
            deg[p] = deg.get(p, 0) + 1
    ends = [p for p, n in deg.items() if n == 1 and abs(max(abs(p[0]), abs(p[1])) - OPEN_END) < 0.002]
    closing = []
    for s in "LRTB":
        pts = sorted((p for p in ends if side(p) == s), key=lambda p: p[1] if s in "LR" else p[0])
        closing += [LineString([pts[i], pts[i + 1]]) for i in range(0, len(pts) - 1, 2)]
    if len(closing) != N:
        sys.exit(f"gen_qfn24_4mm: {len(closing)} open finger ends, expected {N}")
    faces = polygonize(unary_union([LineString([key(a), key(b)]) for a, b in lines] + closing))
    by = {"L": [], "B": [], "R": [], "T": []}
    for f in faces:
        if f.area < 0.3 and any(f.boundary.distance(c.interpolate(0.5, normalized=True)) < 1e-6 for c in closing):
            by[side((f.centroid.x, f.centroid.y))].append(list(f.exterior.coords)[:-1])
    # The pin 1 and pin 24 fingers join the pin-1 chamfer's tie bar in the DXF, so they are pin 6 and pin 19 mirrored.
    if [len(by[s]) for s in "LBRT"] != [5, 6, 6, 5]:
        sys.exit(f"gen_qfn24_4mm: leads per side {[len(by[s]) for s in 'LBRT']}, expected 5 6 6 5 before the mirror")
    cy = lambda pts: sum(p[1] for p in pts) / len(pts)
    cx = lambda pts: sum(p[0] for p in pts) / len(pts)
    by["L"].append([(x, -y) for x, y in min(by["L"], key=cy)])
    by["T"].append([(-x, y) for x, y in max(by["T"], key=cx)])
    return by


def body():
    h, r, c = BODY / 2, CORNER_R, CHAMFER
    arc = lambda cx, cy, a0, a1: [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in [a0 + (a1 - a0) * i / 16 for i in range(17)]]
    return [(-h + c, h)] + arc(h - r, h - r, 90, 0) + arc(h - r, -h + r, 0, -90) + arc(-h + r, -h + r, -90, -180) + [(-h, h - c)]


def main(dxf, out):
    ly = db.Layout()
    ly.dbu = 0.001
    cell = ly.create_cell("QFN24_4MM")
    um = lambda pts: db.DPolygon([db.DPoint(x * 1000, y * 1000) for x, y in pts])
    l208, l210, l211 = (ly.layer(n, 0) for n in (208, 210, 211))
    ring = db.Region(um(body()).to_itype(ly.dbu)) - db.Region(db.DBox(-CAVITY * 500, -CAVITY * 500, CAVITY * 500, CAVITY * 500).to_itype(ly.dbu))
    cell.shapes(l208).insert(ring)
    cell.shapes(l208).insert(db.DBox(-PAD * 500, -PAD * 500, PAD * 500, PAD * 500))

    by = {s: [((sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)), pts) for pts in v] for s, v in leads(dxf_lines(dxf)).items()}
    order = [("L", lambda t: -t[0][1]), ("B", lambda t: t[0][0]), ("R", lambda t: t[0][1]), ("T", lambda t: -t[0][0])]
    r = BODY / 2 + LABEL_OFFSET
    pin = 1
    for s, k in order:
        for c, chain in sorted(by[s], key=k):
            cell.shapes(l210).insert(um(chain))
            x, y = {"L": (-r, c[1]), "R": (r, c[1]), "B": (c[0], -r), "T": (c[0], r)}[s]
            t = db.DText(str(pin), db.DTrans(x * 1000, y * 1000))
            t.size = LABEL_SIZE * 1000
            cell.shapes(l211).insert(t)
            pin += 1
    lead_r = db.Region(cell.begin_shapes_rec(l210))
    tip = lambda b: min(abs(b.left), abs(b.right)) if abs(b.center().x) > abs(b.center().y) else min(abs(b.bottom), abs(b.top))
    tips = [tip(p.bbox()) * ly.dbu for p in lead_r.each()]
    print(f"gen_qfn24_4mm: {lead_r.count()} leads, area {lead_r.area() * ly.dbu ** 2 / 1e6:.3f} mm2, lead tips {min(tips):.0f} to {max(tips):.0f} um off the centre")
    ly.write(out)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: gen_qfn24_4mm.py <bond.dxf> <out.gds>")
    main(*sys.argv[1:])
