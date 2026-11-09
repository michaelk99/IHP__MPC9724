# XOR of every layer of two GDS files, the one top cell of each mapped to the other
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# klayout -b -r xor.py -rd A=<gds> -rd B=<gds> -rd OUT=<txt>
import sys, pya
a_path, b_path, out = A, B, OUT
la, lb = pya.Layout(), pya.Layout()
la.read(a_path); lb.read(b_path)
print("tops A:", [c.name for c in la.top_cells()], "B:", [c.name for c in lb.top_cells()])
assert len(la.top_cells()) == 1 and len(lb.top_cells()) == 1, "each file must have exactly one top cell"
ca, cb = la.top_cells()[0], lb.top_cells()[0]
a_top, b_top = ca.name, cb.name
la_ = {(i.layer, i.datatype): i for i in la.layer_infos()}
lb_ = {(i.layer, i.datatype): i for i in lb.layer_infos()}
keys = sorted(set(la_) | set(lb_))
tot = 0
lines = []
for k in keys:
    ra, rb = pya.Region(), pya.Region()
    if k in la_: ra = pya.Region(ca.begin_shapes_rec(la.layer(la_[k])))
    if k in lb_: rb = pya.Region(cb.begin_shapes_rec(lb.layer(lb_[k])))
    n = (ra ^ rb).count()
    tot += n
    lines.append("%d/%d  A=%d B=%d  xor=%d" % (k[0], k[1], ra.count(), rb.count(), n))
with open(out, "w") as f:
    f.write("A %s top %s\nB %s top %s\n" % (a_path, a_top, b_path, b_top))
    f.write("\n".join(lines) + "\nlayers %d, total xor polygons %d\n" % (len(keys), tot))
print("layers", len(keys), "xor", tot)
