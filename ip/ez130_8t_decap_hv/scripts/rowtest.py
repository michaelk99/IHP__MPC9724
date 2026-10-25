# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: every EZ130 cell around every HV decap, the "place anywhere" proof
#
# Run inside iic-osic-tools:
#   klayout -zz -r rowtest.py -rd dut=DECAPHV8            # -> build/rowtest_DECAPHV8.gds
#   klayout -zz -r rowtest.py -rd dut=DECAP8 -rd base=1   # same harness, EZ130's own
#   klayout -zz -r rowtest.py -rd dut=DECAPHV8 -rd gds=<file> -rd tag=<t>  # another GDS
#
# Three blocks of rows, each row mirrored against the one below as in a real
# floorplan, so every edge of the DUT faces a real neighbour:
#
#   side   row 1: X, DUT, X', DUT, ...   X = every single-height EZ130 cell,
#                                        X' the same cell flipped in x
#          rows 0/2: the library again, each cell's left (row 0) or right
#                    (row 2) edge on a DUT edge, so every cell sits over one
#   self   rows 3..5: DUT abutting DUT (flipped), over and under DUT pairs offset by 0, 1, 3
#                    and 5 sites, and against the other HV sizes
#
# A WELLTAP goes in wherever a row has gone TAP_EVERY without one, so LU.a/b
# stay quiet and anything left is the DUT's. A Metal2 strap ties every VDD
# rail at x = 0, as a PDN does: the flow deck's NW.b1 (1.8 um) is for wells on
# DIFFERENT nets, and it follows connectivity up to TopMetal1. check_rows() then asserts, on the
# boundary layer of what landed, that every row is one gap-free run.

import os
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "..", "..", "scripts"))
from gdswrite import write_gds  # noqa: E402

TAP, TAP_EVERY = "WELLTAP", 14.0                     # um, LU.a/b allow 20
HV = ("DECAPHV8", "DECAPHV16", "DECAPHV32")

dut = globals().get("dut", "DECAPHV8")
base = globals().get("base") == "1"

ly = pya.Layout()
ly.read(os.path.join(ROOT, "..", "ez130_8t_v1p1", "gds", "ez130_8t.gds"))
ly.read(globals().get("gds") or os.path.join(ROOT, "gds", "ez130_8t_decap_hv.gds"))
tag = globals().get("tag", "")
BND = ly.layer(189, 4)
H = ly.cell("FILLER1").bbox(BND).height()
SW = ly.cell("FILLER1").bbox(BND).width()
top = ly.create_cell("rowtest_" + dut + tag)


def width(name):
    b = ly.cell(name).bbox(BND)
    assert b.left == 0 and b.bottom == 0 and b.width() % SW == 0, name
    return b.width()


LIBCELLS = sorted(c.name for c in ly.each_cell()
                  if not c.name.startswith("DECAPHV") and c.name != top.name
                  and c.bbox(BND).height() == H)
FILLERS = sorted((n for n in LIBCELLS if n.startswith("FILLER")),
                 key=width, reverse=True)


class Row:
    def __init__(self, idx):
        self.idx, self.x, self.last_tap = idx, 0, -1e9

    def put(self, name, flip=False):
        """Rows alternate N / FS, so even rows are mirrored in y."""
        w, y = width(name), self.idx * H
        mir = self.idx % 2 == 0
        if mir and flip:
            t = pya.Trans(pya.Trans.R180, self.x + w, y + H)
        elif mir:
            t = pya.Trans(pya.Trans.M0, self.x, y + H)
        elif flip:
            t = pya.Trans(pya.Trans.M90, self.x + w, y)
        else:
            t = pya.Trans(self.x, y)
        top.insert(pya.CellInstArray(ly.cell(name).cell_index(), t))
        if name == TAP:
            self.last_tap = self.x
        self.x += w

    def tap_due(self, ahead=0):
        return (self.x + ahead - self.last_tap) * ly.dbu > TAP_EVERY

    def fill_to(self, x):
        assert self.x <= x, (self.idx, self.x, x)
        for f in FILLERS:
            while self.x + width(f) <= x:
                self.put(f)
        assert self.x == x


def check_rows(rows, total):
    for r in rows:
        band = pya.Box(-1000, r * H + 100, total + 1000, (r + 1) * H - 100)
        got = (pya.Region(top.begin_shapes_rec(BND)) & pya.Region(band)).merged()
        assert got.count() == 1, "row %d has a hole: %d pieces" % (r, got.count())
        assert got.bbox().left == 0 and got.bbox().right == total, (
            "row %d spans %s, not 0..%d" % (r, got.bbox(), total))


# --- side: every library cell beside, above and below the DUT -----------------
def side(passes):
    """Row 1 cycles the library `passes` times: a wide cell in rows 0/2 skips
    DUT edges, so one pass does not always leave an edge for every cell."""
    mid, below, above = Row(1), Row(0), Row(2)
    edges = []
    mid.put(TAP)
    for _ in range(passes):
        for name in LIBCELLS:
            for flip in (False, True):
                if mid.tap_due(width(name) + width(dut)):
                    mid.put(TAP)
                mid.put(name, flip)
                edges.append((mid.x, mid.x + width(dut)))
                mid.put(dut)
    mid.put(TAP)
    for row, align in ((below, "left"), (above, "right")):
        queue = [(n, f) for n in LIBCELLS for f in (False, True)]
        row.put(TAP)
        for left, right in edges:
            if not queue:
                break
            name, flip = queue[0]
            x = left if align == "left" else right - width(name)
            if x - row.x < 0:
                continue
            if row.tap_due(x - row.x + width(name)):
                if x - row.x < width(TAP):
                    continue                          # no room here, try a later edge
                row.put(TAP)
            row.fill_to(x)
            row.put(name, flip)
            queue.pop(0)
        if queue:
            return None
    return mid, below, above


for passes in range(1, 6):
    got = side(passes)
    if got:
        break
    top.clear()
assert got, "the library does not stack onto the DUT edges in 5 passes"
mid, below, above = got
total = max(r.x for r in got)
for r in got:
    while r.x < total:
        step = min(total, r.x + 16 * SW)
        if r.tap_due(width(TAP)) and total - r.x >= width(TAP) + 16 * SW:
            r.put(TAP)
            continue
        r.fill_to(step)

# --- self: DUT against DUT and against the other HV sizes ---------------------
others = [] if base else [n for n in HV if n != dut]
rows = [Row(3), Row(4), Row(5)]
for r in rows:
    r.put(TAP)
for off in (0, 1, 3, 5):
    x0 = max(r.x for r in rows)
    for r in rows:
        r.fill_to(x0)
    rows[1].put(dut)
    rows[1].put(dut, True)
    for r in (rows[0], rows[2]):
        r.fill_to(x0 + off * SW)
        r.put(dut)
        r.put(dut, True)
    # a tap closes each pair: two 13.44 um cells are all LU.a's 20 um allows
    x1 = max(r.x for r in rows)
    for r in rows:
        r.fill_to(x1)
        r.put(TAP)
    for o in others:
        rows[1].put(o)
        for r in (rows[0], rows[2]):
            r.put(o)
    x1 = max(r.x for r in rows)
    for r in rows:
        r.fill_to(x1)
        r.put(TAP)
end = max(r.x for r in rows)
for r in rows:
    r.fill_to(end)

# the PDN stand-in: Via1 on every VDD rail inside the first WELLTAP, one strap
tap_w = width(TAP)
v1, m2 = ly.layer(19, 0), ly.layer(10, 0)
cx, vh = tap_w // 2, 95                               # Via1 is 0.19 um
for k in range(0, 7, 2):
    top.shapes(v1).insert(pya.Box(cx - vh, k * H - vh, cx + vh, k * H + vh))
top.shapes(m2).insert(pya.Box(cx - 200, -300, cx + 200, 6 * H + 300))

check_rows(range(3), total)
for r in rows:
    band = pya.Box(-1000, r.idx * H + 100, end + 1000, (r.idx + 1) * H - 100)
    got = (pya.Region(top.begin_shapes_rec(BND)) & pya.Region(band)).merged()
    assert got.count() == 1 and got.bbox().left == 0, "row %d has a hole" % r.idx

out = os.path.join(ROOT, "build", "rowtest_%s%s.gds" % (dut, tag))
os.makedirs(os.path.dirname(out), exist_ok=True)
write_gds(ly, out)
print("WROTE %s: %d library cells x 2 orientations, %.1f um wide"
      % (out, len(LIBCELLS), total * ly.dbu))
