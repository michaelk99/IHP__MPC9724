# SPDX-FileCopyrightText: 2026 Simon Dorrer and Harald Pretl
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1

"""Adds a rectangle on a specified layer to a GDS file.

The rectangle covers the bounding box of the existing layout
plus a specified margin on each side.

Expected KLayout -rd parameters:
    gds_file: path to the GDS file (read and written in-place)
    layer:    GDS layer as layer_number/datatype (e.g. "126/0")
    margin:   extra margin around the logo bounding box in um
    box:      optional "llx,lly,urx,ury" in um, used instead of the bounding box
"""

import pya

layout = pya.Layout()
layout.read(gds_file)

top = layout.top_cell()
layer_num, datatype = (int(x) for x in layer.split("/"))
layer_idx = layout.layer(layer_num, datatype)

dbu = layout.dbu
margin_dbu = int(float(margin) / dbu)

if "box" in globals():
    llx, lly, urx, ury = (int(round(float(v) / dbu)) for v in box.split(","))
    bbox = pya.Box(llx, lly, urx, ury)
else:
    bbox = top.bbox()
rect = pya.Box(
    bbox.left - margin_dbu,
    bbox.bottom - margin_dbu,
    bbox.right + margin_dbu,
    bbox.top + margin_dbu,
)

top.shapes(layer_idx).insert(rect)
layout.write(gds_file)
