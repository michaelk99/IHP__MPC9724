#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Scan a GDSII file for shapes a mask shop rejects, standard library only.

    scan_gds.py layout/sg13cmos5l_dsa1_dig_top_logo_fill.gds.gz
    scan_gds.py --self-test

Fails on a PATH with fewer than two distinct points or zero width, and on a
BOUNDARY or BOX of zero area. The KLayout decks merge shapes before they check
them, so none of these shows up as a DRC marker. Also prints the top cells, the
database unit, the prBoundary (189/0) box of each top cell, and cell names
longer than 32 characters. Reads .gz directly. Exit code 0 on pass, 1 on fail.
"""
import argparse
import gzip
import struct
import sys

BOUNDARY, PATH, SREF, AREF, BOX = 0x08, 0x09, 0x0A, 0x0B, 0x2D
NAMES = {BOUNDARY: "BOUNDARY", PATH: "PATH", BOX: "BOX"}
KEEP = 50


def real8(b):
    sign = -1 if b[0] & 0x80 else 1
    return sign * int.from_bytes(b[1:8], "big") / (1 << 56) * 16.0 ** ((b[0] & 0x7F) - 64)


def area2(xy):
    """Twice the signed area of the polygon in the flat XY list."""
    xs, ys = xy[0::2], xy[1::2]
    return sum(xs[i] * ys[i + 1] - xs[i + 1] * ys[i] for i in range(len(xs) - 1)) + xs[-1] * ys[0] - xs[0] * ys[-1]


def scan(path):
    with (gzip.open if path.endswith(".gz") else open)(path, "rb") as f:
        data = f.read()
    res = {"ok": True, "failures": [], "nfail": 0, "tops": [], "dbu_um": None,
           "paths": 0, "boundaries": 0, "boxes": 0, "cells": 0, "long_names": [], "prboundary": {}}
    cells, refs, prb = [], set(), {}
    cell = el = None
    layer = dtype = width = 0
    xy = ()

    def fail(msg):
        res["ok"] = False
        res["nfail"] += 1
        if len(res["failures"]) < KEEP:
            res["failures"].append(msg)

    pos, n = 0, len(data)
    while pos + 4 <= n:
        length = int.from_bytes(data[pos:pos + 2], "big")
        rtype = data[pos + 2]
        if length < 4:
            fail("broken record at byte %d" % pos)
            break
        payload = data[pos + 4:pos + length]
        pos += length
        if rtype == 0x06:
            cell = payload.rstrip(b"\0").decode("ascii", "replace")
            cells.append(cell)
            if len(cell) > 32:
                res["long_names"].append(cell)
        elif rtype in (BOUNDARY, PATH, BOX):
            el, layer, dtype, width, xy = rtype, 0, 0, 0, ()
        elif rtype in (SREF, AREF):
            el = rtype
        elif rtype == 0x12:
            refs.add(payload.rstrip(b"\0").decode("ascii", "replace"))
        elif rtype == 0x0D:
            layer = int.from_bytes(payload, "big", signed=True)
        elif rtype in (0x0E, 0x2E):
            dtype = int.from_bytes(payload, "big", signed=True)
        elif rtype == 0x0F:
            width = int.from_bytes(payload, "big", signed=True)
        elif rtype == 0x10 and el in NAMES:
            xy = struct.unpack(">%di" % (len(payload) // 4), payload)
        elif rtype == 0x11:
            if el in NAMES:
                where = "%s %s %d/%d at (%s)" % (cell, NAMES[el], layer, dtype,
                                                ", ".join(str(v) for v in xy[:2]))
                if el == PATH:
                    res["paths"] += 1
                    pts = list(zip(xy[0::2], xy[1::2]))
                    distinct = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
                    if len(distinct) < 2:
                        fail(where + ": fewer than two distinct points")
                    if width == 0:
                        fail(where + ": zero width")
                else:
                    res["boundaries" if el == BOUNDARY else "boxes"] += 1
                    if len(xy) < 6 or area2(xy) == 0:
                        fail(where + ": zero area")
                    if layer == 189 and dtype == 0:
                        b = prb.setdefault(cell, [min(xy[0::2]), min(xy[1::2]), max(xy[0::2]), max(xy[1::2])])
                        b[:] = [min(b[0], *xy[0::2]), min(b[1], *xy[1::2]), max(b[2], *xy[0::2]), max(b[3], *xy[1::2])]
            el = None
        elif rtype == 0x03:
            res["dbu_um"] = round(real8(payload[8:16]) * 1e6, 12)
        elif rtype == 0x04:
            break
    res["cells"] = len(cells)
    res["tops"] = [c for c in cells if c not in refs]
    dbu = res["dbu_um"] or 1e-3
    res["prboundary"] = {c: tuple(round(v * dbu, 6) for v in prb[c]) for c in res["tops"] if c in prb}
    if not res["tops"]:
        fail("no top cell")
    return res


def report(path, res):
    lines = ["file: %s" % path,
             "cells: %d, top: %s, dbu: %s um" % (res["cells"], ", ".join(res["tops"]), res["dbu_um"]),
             "shapes: %d paths, %d boundaries, %d boxes" % (res["paths"], res["boundaries"], res["boxes"])]
    for top in res["tops"]:
        box = res["prboundary"].get(top)
        lines.append("prBoundary 189/0 in %s: %s" % (top, "(%g, %g) to (%g, %g) um" % box if box else "none"))
    if res["long_names"]:
        lines.append("cell names over 32 characters: %d, %s" % (len(res["long_names"]), ", ".join(res["long_names"][:5])))
    lines += ["FAIL: " + f for f in res["failures"]]
    if res["nfail"] > len(res["failures"]):
        lines.append("FAIL: and %d more" % (res["nfail"] - len(res["failures"])))
    lines.append("degenerate: %d" % res["nfail"])
    lines.append("PASS" if res["ok"] else "FAIL")
    return lines


def self_test():
    import os
    import tempfile

    def rec(rtype, dtype, payload=b""):
        return struct.pack(">HBB", 4 + len(payload), rtype, dtype) + payload

    def name(rtype, s):
        b = s.encode()
        return rec(rtype, 6, b + (b"\0" if len(b) % 2 else b""))

    def i16(rtype, *v):
        return rec(rtype, 2, struct.pack(">%dh" % len(v), *v))

    def i32(rtype, *v):
        return rec(rtype, 3, struct.pack(">%di" % len(v), *v))

    def real8(x):
        # GDSII excess-64 base-16 real
        if x == 0:
            return b"\0" * 8
        e = 64
        while x >= 1:
            x /= 16
            e += 1
        while x < 1 / 16:
            x *= 16
            e -= 1
        return struct.pack(">B", e) + int(x * (1 << 56)).to_bytes(7, "big")

    def boundary(layer, pts):
        return i16(0x08) + i16(0x0D, layer) + i16(0x0E, 0) + i32(0x10, *sum(pts, ())) + rec(0x11, 0)

    def path(layer, pts, width):
        return i16(0x09) + i16(0x0D, layer) + i16(0x0E, 0) + i32(0x0F, width) + i32(0x10, *sum(pts, ())) + rec(0x11, 0)

    def box(layer, pts):
        return i16(0x2D) + i16(0x0D, layer) + i16(0x2E, 0) + i32(0x10, *sum(pts, ())) + rec(0x11, 0)

    def sref(cell):
        return i16(0x0A) + name(0x12, cell) + i32(0x10, 0, 0) + rec(0x11, 0)

    def cell(n, *elements):
        return i16(0x05, *([0] * 12)) + name(0x06, n) + b"".join(elements) + rec(0x07, 0)

    def lib(*cells):
        return (i16(0x00, 600) + i16(0x01, *([0] * 12)) + name(0x02, "LIB")
                + rec(0x03, 5, real8(1e-3) + real8(1e-9)) + b"".join(cells) + rec(0x04, 0))

    square = [(0, 0), (1000, 0), (1000, 1000), (0, 1000), (0, 0)]
    good_leaf = cell("leaf", boundary(8, square), path(8, [(0, 0), (500, 0)], 200), box(8, square))
    top = cell("top", sref("leaf"), boundary(189, [(0, 0), (1600000, 0), (1600000, 1600000), (0, 1600000), (0, 0)]))
    cases = [
        ("clean", lib(good_leaf, top), True),
        ("path with one distinct point", lib(cell("leaf", path(8, [(5, 5), (5, 5)], 200)), top), False),
        ("path of zero width", lib(cell("leaf", path(8, [(0, 0), (500, 0)], 0)), top), False),
        ("flat boundary", lib(cell("leaf", boundary(8, [(0, 0), (1000, 0), (2000, 0), (0, 0)])), top), False),
        ("zero-area box", lib(cell("leaf", box(8, [(0, 0), (0, 0), (0, 0), (0, 0), (0, 0)])), top), False),
    ]
    bad = 0
    d = tempfile.mkdtemp()
    for i, (label, data, want) in enumerate(cases):
        f = os.path.join(d, "t%d.gds.gz" % i if i % 2 else "t%d.gds" % i)
        with (gzip.open if f.endswith(".gz") else open)(f, "wb") as fh:
            fh.write(data)
        res = scan(f)
        if res["ok"] != want:
            bad += 1
            print("FAIL: %s: ok=%s, expected %s: %s" % (label, res["ok"], want, res["failures"]))
        os.remove(f)
    f = os.path.join(d, "clean.gds")
    open(f, "wb").write(lib(good_leaf, top))
    res = scan(f)
    checks = [
        (res["tops"] == ["top"], "top cells %s" % res["tops"]),
        (res["dbu_um"] == 1e-3, "dbu %s" % res["dbu_um"]),
        (res["paths"] == 1 and res["boundaries"] == 2 and res["boxes"] == 1,
         "counts %s %s %s" % (res["paths"], res["boundaries"], res["boxes"])),
        (res["prboundary"].get("top") == (0.0, 0.0, 1600.0, 1600.0), "prBoundary %s" % res["prboundary"]),
    ]
    for good, what in checks:
        if not good:
            bad += 1
            print("FAIL: clean library: " + what)
    os.remove(f)
    os.rmdir(d)
    if bad:
        sys.exit(1)
    print("OK: scan_gds self-test, %d cases" % (len(cases) + len(checks)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gds", nargs="?")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.gds:
        ap.error("a GDS file is required")
    res = scan(args.gds)
    print("\n".join(report(args.gds, res)))
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
