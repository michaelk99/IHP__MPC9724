# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Net of each side of the two M1.e pairs in ota_fcasc2_top, through metal and vias only (OTA frame, um).
# Usage, from the repo root: python3 verification/drc/magic_recheck_2026-11-12/trace.py
import klayout.db as db

ly = db.Layout()
ly.read("ip/dsm2_core/gds/dsm2_core.gds")
c = ly.cell("ota_fcasc2_top")
l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(ly, c, []))
metal = ["m1", "v1", "m2", "v2", "m3", "v3", "m4"]
gds = {"m1": (8, 0), "v1": (19, 0), "m2": (10, 0), "v2": (29, 0), "m3": (30, 0), "v3": (49, 0), "m4": (50, 0)}
L = {n: l2n.make_layer(ly.layer(*gds[n]), n) for n in metal}
for i, n in enumerate(metal):
    l2n.connect(L[n])
    if i:
        l2n.connect(L[metal[i - 1]], L[n])
for t, m in [((8, 25), "m1"), ((10, 25), "m2"), ((30, 25), "m3"), ((50, 25), "m4")]:
    l2n.connect(L[m], l2n.make_text_layer(ly.layer(*t), "t" + m))
l2n.extract_netlist()
points = {"strap_low": (30, 8.5), "nbias_line": (30, 8.05), "strap_high": (30, 9.5), "pbias_line": (30, 9.95),
          "nbias_line_x5": (5, 8.05), "nbias_line_x60": (60, 8.05), "pbias_line_x5": (5, 9.95), "pbias_line_x60": (60, 9.95),
          "vi_p_label": (31.915, 4.595)}
for name, (x, y) in points.items():
    net = l2n.probe_net(L["m1"], db.DPoint(x, y))
    print(name, net.expanded_name() if net else None, "cluster", net.cluster_id if net else None)
