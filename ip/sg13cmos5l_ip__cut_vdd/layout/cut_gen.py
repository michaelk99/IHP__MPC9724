# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: KLayout generator for sg13cmos5l_ip__cut_vdd, writes its GDS and LEF
#
#   klayout -n sg13cmos5l -zz -r cut_gen.py [-rd variant=m3_strip|m4_strip|nwell_straddle -rd out=<gds>]
#
# The PDK's sg13cmos5l_Filler2000 with its vdd band taken out. The band y ranges
# come from the IO LEF through the clamp cell's rails.py. `variant` draws a
# deliberately broken cell for the probe's negative control.

import os
import re
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "..", "..", "..")
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, os.path.join(REPO, "ip", "sg13cmos5l_ip__clamp_vddvss", "layout"))
from gdswrite import write_gds                      # noqa: E402
import rails as rails_mod                           # noqa: E402

CELL = "sg13cmos5l_ip__cut_vdd"
FILLER = rails_mod.FILLER
IO_GDS = os.path.join(os.path.dirname(os.path.dirname(rails_mod.LEF_PATH)), "gds",
                      "sg13cmos5l_io.gds")
GDS = os.path.join(HERE, "..", "gds", CELL + ".gds")
LEF = os.path.join(HERE, "..", "lef", CELL + ".lef")
# Metal3 to TopMetal1 carry the band. Metal1, Metal2 and the vias lose the shapes in a
# vdd range. So do Cont, Activ and NWell: the filler's two n-taps on vdd sit there, and
# their wells run 0.62 um into the neighbours, which would tie VDD and VDDA together.
BAND_LAYERS = {"Metal3": 30, "Metal4": 50, "TopMetal1": 126}
OTHER_LAYERS = {"Metal1": 8, "Metal2": 10, "Via1": 19, "Via2": 29, "Via3": 49, "TopVia1": 125,
                "Cont": 6, "Activ": 1, "NWell": 31}


def vdd_ranges():
    """(per layer y ranges of the vdd band, union of all of them), in um."""
    per = {}
    for layer, y0, y1 in rails_mod.rails()["vdd"]:
        per.setdefault(layer, []).append((y0, y1))
    union = sorted({r for v in per.values() for r in v})
    return per, union


def cut(cell, ly):
    """Take the vdd band out of the copied filler. Returns a count per layer."""
    per, union = vdd_ranges()
    dbu = ly.dbu
    stats = {}
    for li in ly.layer_indexes():
        info = ly.get_info(li)
        name = next((n for n, num in {**BAND_LAYERS, **OTHER_LAYERS}.items()
                     if num == info.layer), None)
        if name is None:
            continue
        # NWell is clipped like a band: a well that only overlaps a range would still tie VDD to VDDA
        ranges = per.get(name) if name in BAND_LAYERS else union if name == "NWell" else None
        if name in BAND_LAYERS and not ranges:
            continue
        gone = clipped = straddle = 0
        for sh in list(cell.shapes(li).each()):
            if sh.is_text():
                if any(a <= sh.text.trans.disp.y * dbu <= b for a, b in (ranges or union)):
                    sh.delete()
                    gone += 1
                continue
            bb = sh.bbox()
            lo, hi = bb.bottom * dbu, bb.top * dbu
            if ranges:      # a band layer: clip at the band edge, whole x
                hit = [(a, b) for a, b in ranges if lo < b and hi > a]
                if not hit:
                    continue
                reg = pya.Region(sh.polygon if not sh.is_box() else sh.box)
                for a, b in hit:
                    reg -= pya.Region(pya.Box(-10**9, round(a / dbu), 10**9, round(b / dbu)))
                sh.delete()
                for p in reg.each():
                    cell.shapes(li).insert(p)
                if reg.is_empty():
                    gone += 1
                else:
                    clipped += 1
            else:           # Metal1, Metal2, vias: whole shapes inside a range
                if any(a <= lo and hi <= b for a, b in union):
                    sh.delete()
                    gone += 1
                elif any(lo < b and hi > a for a, b in union):
                    straddle += 1
        stats[(name, info.datatype)] = (gone, clipped, straddle)
    return stats


def write_lef(path):
    """The filler's LEF macro as text, renamed, without the vdd pin."""
    with open(rails_mod.LEF_PATH, encoding="utf-8") as fh:
        text = fh.read()
    body = re.search(r"^MACRO %s$.*?^END %s$" % (FILLER, FILLER), text, re.S | re.M).group(0)
    body, n = re.subn(r"^  PIN vdd$.*?^  END vdd\n", "", body, flags=re.S | re.M)
    assert n == 1, "no vdd pin in the filler's LEF"
    body = body.replace(FILLER, CELL)
    head = ["# SPDX-FileCopyrightText: 2026 Michael Koefinger",
            "# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1",
            "# Written by layout/cut_gen.py, do not edit.",
            "", "VERSION 5.7 ;", "BUSBITCHARS \"[]\" ;", "DIVIDERCHAR \"/\" ;", ""]
    with open(path, "w") as fh:
        fh.write("\n".join(head) + body + "\n\nEND LIBRARY\n")


def build(variant=""):
    ly = pya.Layout()
    ly.read(IO_GDS)
    cell = ly.cell(FILLER)
    for ci in [c.cell_index() for c in ly.top_cells()]:
        if ci != cell.cell_index():
            ly.prune_cell(ci, -1)
    cell.name = CELL
    for (name, dt), (gone, clipped, straddle) in sorted(cut(cell, ly).items()):
        print("  %-10s dt %-3d removed %4d, clipped %d, kept across a range edge %d"
              % (name, dt, gone, clipped, straddle))
    if variant == "m3_strip":
        a, b = rails_mod.rails()["vdd"][0][1:]
        cell.shapes(ly.layer(30, 0)).insert(pya.DBox(4.0, a, 6.0, b))
    elif variant == "m4_strip":
        a, b = rails_mod.rails()["vdd"][1][1:]
        cell.shapes(ly.layer(50, 0)).insert(pya.DBox(4.0, a, 6.0, b))
    elif variant == "nwell_straddle":     # crosses the lower edge of the Metal4 vdd range
        cell.shapes(ly.layer(31, 0)).insert(pya.DBox(2.0, 100.0, 8.0, 150.0))
    elif variant:
        raise SystemExit("cut_gen: unknown variant %s" % variant)
    return ly


def main():
    variant = globals().get("variant", "")
    gds = globals().get("out", GDS)
    ly = build(variant)
    write_gds(ly, gds)
    print("wrote %s" % gds)
    if not variant:
        write_lef(LEF)
        print("wrote %s" % LEF)


if __name__ == "__main__":
    try:
        main()
    except BaseException as e:      # klayout -r exits 0 on a raised string
        if isinstance(e, SystemExit) and not e.code:
            raise
        import traceback
        traceback.print_exc()
        sys.exit(1)
