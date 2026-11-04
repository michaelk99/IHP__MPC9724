#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Activ and GatPoly density of a chip GDS: global, and the worst 800 um window.

    density_window.py <gds> [--step 10]

The layers and the chip area are the regular deck's (density.drc): Activ is 1/0, 1/20 and 1/22 merged, GatPoly 5/0 and 5/22, over the area of prBoundary 189/0.
The deck checks Activ per window (AFil.g2 at least 25 %, AFil.g3 at most 65 %) on 800 um windows at a 400 um step from the lower left, plus a row and a column flush with the upper and right edge.
This prints the worst window on that grid, and on a finer sliding step (--step um, from a raster of that pitch), which is never better.
GatPoly has a global rule only (GFil.g), its windows are for information.
"""

import argparse

import klayout.db as db

LAYERS = {"Activ": ((1, 0), (1, 20), (1, 22)), "GatPoly": ((5, 0), (5, 22))}
WIN, DECK_STEP = 800.0, 400.0


def region(ly, top, pairs):
    r = db.Region()
    for layer, dt in pairs:
        i = ly.find_layer(layer, dt)
        if i is not None:
            r += db.Region(top.begin_shapes_rec(i))
    return r.merged()


def deck_origins(extent):
    """Window origins along one axis, relative to the chip's lower left, as density.drc lays them."""
    n = max(1 + int((extent - WIN) // DECK_STEP), 1)
    xs = [k * DECK_STEP for k in range(n)]
    if extent > WIN + (n - 1) * DECK_STEP:
        xs.append(extent - WIN)
    return xs


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("gds")
    ap.add_argument("--step", type=float, default=10.0, help="sliding step and raster pitch, um")
    a = ap.parse_args()
    ly = db.Layout()
    ly.read(a.gds)
    top = ly.top_cell()
    dbu = ly.dbu
    chip = region(ly, top, [(189, 0)])
    box = chip.bbox()
    w, h = box.width() * dbu, box.height() * dbu
    area = chip.area()
    print("chip %s, %.1f x %.1f um" % (top.name, w, h))
    for name, pairs in LAYERS.items():
        r = region(ly, top, pairs)
        print("%s global %.2f %%" % (name, 100.0 * r.area() / area))
        # deck grid, exact areas
        worst = min((100.0 * (r & db.Region(db.Box(box.left + round(x / dbu), box.bottom + round(y / dbu),
                                                    box.left + round((x + WIN) / dbu), box.bottom + round((y + WIN) / dbu)))).area()
                     / (WIN * WIN / dbu / dbu), x, y) for x in deck_origins(w) for y in deck_origins(h))
        print("%s worst 800 um window on the deck's 400 um grid %.2f %% at (%g, %g)" % (name, *worst))
        # sliding windows from a raster: cell sums, then window sums
        px = round(a.step / dbu)
        nx, ny = int(w // a.step), int(h // a.step)
        ras = r.rasterize(box.p1, db.Vector(px, px), nx, ny)
        k = int(round(WIN / a.step))
        col = [[0.0] * (nx + 1) for _ in range(ny + 1)]      # 2D prefix sums
        for j in range(ny):
            run = 0.0
            for i in range(nx):
                run += ras[j][i]
                col[j + 1][i + 1] = col[j][i + 1] + run
        best = None
        for j in range(ny - k + 1):
            for i in range(nx - k + 1):
                s = col[j + k][i + k] - col[j][i + k] - col[j + k][i] + col[j][i]
                if best is None or s < best[0]:
                    best = (s, i * a.step, j * a.step)
        print("%s worst 800 um window on a %g um sliding step %.2f %% at (%g, %g)"
              % (name, a.step, 100.0 * best[0] / (WIN * WIN / dbu / dbu), best[1], best[2]))


if __name__ == "__main__":
    main()
