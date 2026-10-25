# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Show that the fill of the delivery GDS cannot change its netlist, so top_lvs.sh may read the
# unfilled GDS: fill (datatype 22) merges no two drawn shapes of a layer into one, touches no via,
# and crosses no drawn active or poly. A fill tile that touches one net only lengthens it.
# Fill poly sits on fill active by design, a floating dummy with no contact. Run at the repo root:
#   klayout -b -r verification/lvs/fill_isolation.py [-rd gds=<file>] [-rd out=<file>]
import sys
import pya

gds = globals().get("gds") or "layout/sg13cmos5l_dsa1_dig_top_logo_fill.gds.gz"
out = globals().get("out") or "verification/lvs/fill_isolation.txt"

# conductor layer: the cut layers that land on it
CONDUCTORS = {"Activ": (1, [6]), "GatPoly": (5, [6]), "Metal1": (8, [6, 19]), "Metal2": (10, [19, 29]),
              "Metal3": (30, [29, 49]), "Metal4": (50, [49, 125]), "TopMetal1": (126, [125])}
FILL = 22

ly = pya.Layout()
ly.read(gds)
top = ly.top_cells()[0]


def region(layer, keep):
    r = pya.Region()
    for li in ly.layer_indexes():
        i = ly.get_info(li)
        if i.layer == layer and keep(i.datatype):
            r += pya.Region(top.begin_shapes_rec(li))
    return r


rows, bad = [], 0
fills = {}
for name, (layer, cuts) in CONDUCTORS.items():
    fill = region(layer, lambda d: d == FILL)
    drawn = region(layer, lambda d: d != FILL).merged()
    via = pya.Region()
    for c in cuts:
        via += region(c, lambda d: True)
    n_touch = fill.interacting(drawn).count()
    # one merged polygon per drawn component unless fill joins two of them
    joined = drawn.count() - (drawn + fill).merged().interacting(drawn).count()
    n_via = fill.interacting(via).count()
    fills[name] = fill
    bad += joined + n_via
    rows.append(f"| {name} {layer}/{FILL} | {fill.count()} | {n_touch} | {joined} | {n_via} |")

drawn_act = region(1, lambda d: d != FILL)
drawn_poly = region(5, lambda d: d != FILL)
n_dev = fills["GatPoly"].interacting(drawn_act).count() + fills["Activ"].interacting(drawn_poly).count()
n_dummy = fills["GatPoly"].interacting(fills["Activ"]).count()
bad += n_dev

text = "\n".join([f"Fill isolation of {gds} (top cell {top.name})", "",
                  "| fill layer | fill shapes | touching drawn | drawn components joined | touching a via |",
                  "|---|---|---|---|---|", *rows, "",
                  f"Fill poly or fill active crossing drawn active or poly: {n_dev}",
                  f"Fill poly on fill active, floating dummies: {n_dummy}", "",
                  "PASS: the fill joins no two drawn shapes and touches no via" if not bad else f"FAIL: {bad} fill interactions"])
open(out, "w").write(text + "\n")
print(text)
sys.exit(1 if bad else 0)
