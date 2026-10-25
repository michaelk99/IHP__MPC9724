# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: probe for the vdd band cut cell
#
#   klayout -b -r cut_probe.py [-rd gds=<file>] [-rd cell=<name>]
#
# Flattens the cell and requires, with every band position read from the IO LEF:
#   (a) the iovss, iovdd and vss bands are whole from x 0 to the cell width
#   (b) nothing of the vdd band: no Metal3, Metal4 or TopMetal1 shape or label in
#       its range, no Metal1, Metal2, via, Cont, Activ or NWell shape overlapping any vdd range
#       (but the vss tap strip on Metal1 and Activ, y 115.62..140.17)
#   (c) the labels are iovss, iovdd and vss, none is vdd
# Run on the PDK's Filler2000 (-rd cell=sg13cmos5l_Filler2000 -rd gds=<IO gds>)
# it has to fail on (b).

import os
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "sg13cmos5l_ip__clamp_vddvss", "layout"))
import rails as rails_mod   # noqa: E402

CELL = "sg13cmos5l_ip__cut_vdd"
BAND = {"Metal3": 30, "Metal4": 50, "TopMetal1": 126}
OTHER = {"Metal1": 8, "Metal2": 10, "Via1": 19, "Via2": 29, "Via3": 49, "TopVia1": 125,
         "Cont": 6, "Activ": 1, "NWell": 31}
# The filler's vss tap strip crosses y 140 by 0.17 um, cut_gen.py keeps it
VSS_STRIP_LAYERS, VSS_STRIP = ("Metal1", "Activ"), (115.62, 140.17)
NUM = {**BAND, **OTHER}


def main():
    gds = globals().get("gds") or os.path.join(HERE, "..", "gds", CELL + ".gds")
    name = globals().get("cell") or CELL
    ly = pya.Layout()
    ly.read(gds)
    top = ly.cell(name)
    dbu = ly.dbu
    # the filler's own width, as the LEF says
    width = top.dbbox_per_layer(ly.layer(189, 4)).width()
    rl = rails_mod.rails()
    bad = []

    def layer_shapes(layer):
        """(datatype, shape, bbox in um) of every flat shape on a layer number."""
        for li in ly.layer_indexes():
            info = ly.get_info(li)
            if info.layer != NUM[layer]:
                continue
            for it in top.begin_shapes_rec(li):
                sh = it.shape()
                if sh.is_text():
                    t = sh.text.transformed(it.trans())
                    yield info.datatype, sh, (t.trans.disp.x * dbu, t.trans.disp.y * dbu) * 2
                else:
                    bb = sh.bbox().transformed(it.trans())
                    yield info.datatype, sh, (bb.left * dbu, bb.bottom * dbu,
                                              bb.right * dbu, bb.top * dbu)

    nbands = 0
    for net in ("iovss", "iovdd", "vss"):
        for layer, y0, y1 in rl[net]:
            li = ly.layer(NUM[layer], 0)
            reg = pya.Region(top.begin_shapes_rec(li)).merged()
            box = pya.Box(0, round(y0 / dbu), round(width / dbu), round(y1 / dbu))
            if (pya.Region(box) - reg).is_empty():
                nbands += 1
            else:
                bad.append("(a) %s %s %g..%g is not whole from x 0 to %g" % (net, layer, y0, y1, width))
    print("(a) %d bands of iovss, iovdd and vss checked, %d whole" % (nbands, nbands))

    per = {}
    union = []
    for layer, y0, y1 in rl["vdd"]:
        per.setdefault(layer, []).append((y0, y1))
        union.append((y0, y1))
    for layer in BAND:
        if layer not in per:
            print("(b) %s: no vdd band in the LEF" % layer)
    n = 0
    for layer, rngs in per.items():
        for dt, sh, (x0, y0, x1, y1) in layer_shapes(layer):
            for a, b in rngs:
                if y0 < b and y1 > a:
                    n += 1
                    bad.append("(b) %s dt %d shape at x %g..%g y %g..%g in the vdd band %g..%g"
                               % (layer, dt, x0, x1, y0, y1, a, b))
    for layer in OTHER:
        for dt, sh, (x0, y0, x1, y1) in layer_shapes(layer):
            if layer in VSS_STRIP_LAYERS and abs(y0 - VSS_STRIP[0]) < 1e-3 and abs(y1 - VSS_STRIP[1]) < 1e-3:
                continue
            if any(y0 < b and y1 > a for a, b in union):
                n += 1
                bad.append("(b) %s dt %d shape at x %g..%g y %g..%g overlaps a vdd range"
                           % (layer, dt, x0, x1, y0, y1))
    print("(b) %d shapes in the vdd ranges %s" % (n, ", ".join(
        "%s %g..%g" % (l, a, b) for l, r in sorted(per.items()) for a, b in r)))
    labels = set()
    for li in ly.layer_indexes():
        if ly.get_info(li).datatype == 25:
            labels |= {it.shape().text.string for it in top.begin_shapes_rec(li)
                       if it.shape().is_text()}
    print("(c) labels %s" % ", ".join(sorted(labels)))
    if "vdd" in {l.lower() for l in labels}:
        bad.append("(c) a vdd label")
    for net in ("iovss", "iovdd", "vss"):
        if net not in labels:
            bad.append("(c) no %s label" % net)
    for b in bad:
        print("FAIL " + b)
    print("cut_probe %s: %s" % (name, "FAIL" if bad else "ok"))
    return 1 if bad else 0


if __name__ == "__main__":
    try:
        r = main()
    except BaseException:
        import traceback
        traceback.print_exc()
        r = 1
    sys.exit(r)
