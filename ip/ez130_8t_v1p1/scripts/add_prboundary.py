# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: Give every EZ130 cell a prBoundary.boundary (189/4) beside its 235/4

"""EZ130 draws its cell boundary on 235/4. Nothing in either IHP PDK does.

`sg13cmos5l_stdcell` and every full-custom cell in this repo carry the boundary
on `prBoundary.boundary` **189/4**, and the repo's tooling reads that layer to
get a cell width (see *Full-custom layout* in `CLAUDE.md`). Layer 235 is in
neither PDK's layer properties, so EZ130 reads as having no boundary at all,
and the drawn bbox is not a substitute: it overstates every width by the NWell
overhang.

This copies each cell's 235/4 box onto 189/4 and leaves 235/4 in place, so a
tool that already knew about it keeps working. It is idempotent: a cell that
already has 189/4 is skipped.

**It also rewrites the cell order, and that is not cosmetic.** KLayout's GDS
writer emits structures in the REVERSE of the order it read them, so a plain
read-and-write oscillates between two byte sequences with period 2 and a
rebuild of a tracked GDS is always a diff. `gdswrite.py` cannot see this: it
zeroes the timestamps, and the bytes still move. The library is flat (220
cells, all tops, no children, no properties), so this rebuilds it into a fresh
layout with the cells created in sorted name order, which is canonical and
therefore stable under any number of rebuilds from any input order.

Run inside IIC-OSIC-TOOLS:

    python3 ip/ez130_8t_v1p1/scripts/add_prboundary.py

`--check` verifies without writing, which is what a CI or a `make` target wants.
"""

import argparse
import os
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
IP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(IP, "..", "..", "scripts"))

from gdswrite import write_gds  # noqa: E402

GDS = os.path.join(IP, "gds", "ez130_8t.gds")
LEF = os.path.join(IP, "lef", "ez130_8t.lef")
SRC = (235, 4)          # EZ130's own boundary
DST = (189, 4)          # prBoundary.boundary, what the PDK and this repo read


def lef_sizes(path):
    """MACRO -> (w, h) in um, from the cell LEF's SIZE line."""
    out, cell = {}, None
    for line in open(path):
        f = line.split()
        if not f:
            continue
        if f[0] == "MACRO":
            cell = f[1]
        elif f[0] == "SIZE" and cell:
            out[cell] = (float(f[1]), float(f[3]))
    return out


def boundaries(ly, layer):
    """cell name -> list of boxes on `layer`, in um."""
    li = ly.find_layer(*layer)
    if li is None:
        return {}
    d = ly.dbu
    out = {}
    for c in ly.each_cell():
        b = [s.bbox() for s in c.shapes(li).each()]
        if b:
            out[c.name] = [(x.left * d, x.bottom * d, x.width() * d, x.height() * d) for x in b]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="verify only, do not write")
    args = ap.parse_args()

    ly = pya.Layout()
    ly.read(GDS)
    src, dst = boundaries(ly, SRC), boundaries(ly, DST)

    # The 235/4 box has to be the cell's real footprint before it is worth copying.
    sizes = lef_sizes(LEF)
    for name, boxes in src.items():
        assert len(boxes) == 1, f"{name}: {len(boxes)} shapes on {SRC[0]}/{SRC[1]}"
        x, y, w, h = boxes[0]
        assert (x, y) == (0.0, 0.0), f"{name}: boundary origin {x},{y} is not 0,0"
        if name in sizes:
            lw, lh = sizes[name]
            assert abs(w - lw) < 1e-9 and abs(h - lh) < 1e-9, \
                f"{name}: boundary {w}x{h} != LEF SIZE {lw}x{lh}"
    missing = sorted(set(c.name for c in ly.each_cell()) - set(src))
    assert not missing, f"no {SRC[0]}/{SRC[1]} in: {missing}"

    todo = sorted(set(src) - set(dst))
    for name in sorted(dst):
        assert dst[name] == src[name], f"{name}: existing {DST[0]}/{DST[1]} disagrees with {SRC[0]}/{SRC[1]}"
    print(f"{len(src)} cells, {len(dst)} already on {DST[0]}/{DST[1]}, {len(todo)} to add")

    out = canonical(ly)
    li_src, li_dst = out.layer(*SRC), out.layer(*DST)
    for name in todo:
        c = out.cell(name)
        for s in c.shapes(li_src).each():
            c.shapes(li_dst).insert(s.box)
    assert boundaries(out, DST) == src, "copy did not reproduce the source boundaries"

    tmp = GDS + ".new"
    write_gds(out, tmp)
    same = open(tmp, "rb").read() == open(GDS, "rb").read()
    if args.check:
        os.remove(tmp)
        print("up to date" if same else "STALE: rerun without --check")
        sys.exit(0 if same else 1)
    os.replace(tmp, GDS)
    print(("unchanged " if same else "wrote ") + GDS)


def canonical(ly):
    """A copy with the cells created in sorted name order.

    KLayout writes structures in the reverse of the read order, so a rebuild
    from the tracked file otherwise flips the byte order every time. Requires a
    flat library, which this one is, and asserts it rather than assuming it.
    """
    assert not any(c.child_cells() for c in ly.each_cell()), "not a flat library"
    out = pya.Layout()
    out.dbu = ly.dbu
    # Create layers in sorted order, DST included whether or not the input has
    # it yet, so the first run and every rerun agree on the layer order too.
    order = sorted(ly.layer_indexes(), key=lambda i: (ly.get_info(i).layer, ly.get_info(i).datatype))
    lmap = {}
    seen = set()
    for i in order:
        info = ly.get_info(i)
        if (info.layer, info.datatype) > DST and DST not in seen:
            out.layer(*DST)
            seen.add(DST)
        lmap[i] = out.layer(info)
        seen.add((info.layer, info.datatype))
    if DST not in seen:
        out.layer(*DST)
    for name in sorted(c.name for c in ly.each_cell()):
        src_cell, dst_cell = ly.cell(name), out.create_cell(name)
        for i in ly.layer_indexes():
            dst_cell.shapes(lmap[i]).insert(src_cell.shapes(i))
    return out


if __name__ == "__main__":
    main()
