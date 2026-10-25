# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: thick-oxide decap cells for the EZ130 8T row, one HV PMOS each
#
# Run inside iic-osic-tools, from anywhere:
#   klayout -zz -r decap_hv_gen.py
#
# Writes gds/, lef/, cdl/ and verilog/ of ip/ez130_8t_decap_hv.
#
# Each cell is ONE sg13_hv_pmos, gate on VSS, source, drain and well on VDD,
# as large as a cell can hold without constraining its neighbours. "Any
# neighbour" is measured, not assumed: ENVELOPE() reads every single-height
# EZ130 cell and takes the closest any of them brings Activ to its own edge.
# Every inset below is then the larger of two things, what a foreign cell
# needs and what a mirrored copy of this cell needs (doc/decap_hv.md §2):
#
#   ThickGateOx  max(TGO.e/2, TGO.b - a)     0.43
#   NWell tongue max(NW.b/2,  NW.d  - a)     0.31  (EZ130 wells stop at y 1.46)
#   pSD tongue   max(pSD.b/2, pSD.d - a)     bounded by pSD.c/pSD.i1 inside
#   Activ        max(NWell + NW.c1, TGO + TGO.a); channel top TGO - TGO.c
#
# No DigiBnd: it would relax NW.c1 to 0.31, and Magic's deck knows only 0.62.

import json
import os
import re
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.normpath(os.path.join(ROOT, "..", ".."))
EZ = os.path.join(ROOT, "..", "ez130_8t_v1p1")
sys.path.insert(0, os.path.join(REPO, "scripts"))
from gdswrite import write_gds  # noqa: E402

LIB = "ez130_8t_decap_hv"
SIZES = (8, 16, 32)                                   # sites

L = {"activ": (1, 0), "gatpoly": (5, 0), "cont": (6, 0), "m1": (8, 0),
     "m1pin": (8, 2), "m1txt": (8, 25), "psd": (14, 0), "nwell": (31, 0),
     "tgo": (44, 0), "bnd": (189, 4), "bnd_ez": (235, 4)}

PDK = os.path.join(os.environ.get("PDK_ROOT", "/foss/pdks"),
                   os.environ.get("PDK", "ihp-sg13cmos5l"))
R = json.load(open(os.path.join(
    PDK, "libs.tech/klayout/tech/drc/rule_decks/sg13cmos5l_tech_default.json")))["drc_rules"]
DBU = 0.001


def u(v):
    """microns -> dbu, which must land on the 5 nm grid"""
    i = int(round(v / DBU))
    assert i % 5 == 0, "%.4f um is off the 5 nm grid" % v
    return i


def r(key):
    return u(R[key])


def site():
    lef = open(os.path.join(EZ, "lef", "ez130_8t.lef")).read()
    m = re.search(r"^SITE\s+CoreSite\b.*?SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", lef, re.S | re.M)
    return u(float(m.group(1))), u(float(m.group(2)))


def envelope(ez):
    """What a foreign cell brings to the shared edge, over the whole library.

    a     closest Activ to any of the cell's four edges
    nw    bottom of the NWell band, and its x overhang past the boundary
    psd   bottom of the pSD band, and its x overhang
    rail  Metal1 rail half-width
    """
    b_l, nw_y, psd_y, nw_x, psd_x, rail = ez.layer(*L["bnd"]), set(), set(), set(), set(), set()
    a = None
    _, h = site()
    for c in ez.each_cell():
        bb = c.bbox(b_l)
        if bb.empty() or bb.height() != h:
            continue
        act = pya.Region(c.shapes(ez.layer(*L["activ"])))
        if not act.is_empty():
            ab = act.bbox()
            d = min(ab.left - bb.left, bb.right - ab.right,
                    ab.bottom - bb.bottom, bb.top - ab.top)
            a = d if a is None else min(a, d)
        if c.name.startswith("FILLER"):
            nw = pya.Region(c.shapes(ez.layer(*L["nwell"]))).bbox()
            ps = pya.Region(c.shapes(ez.layer(*L["psd"]))).bbox()
            nw_y.add(nw.bottom), nw_x.add(bb.left - nw.left)
            psd_y.add(ps.bottom), psd_x.add(bb.left - ps.left)
            m1 = pya.Region(c.shapes(ez.layer(*L["m1"]))).merged()
            rail.add(min(p.bbox().top for p in m1.each()))
    # the frame must be one frame, or "the" band is not a thing to design to
    assert len(nw_y) == len(psd_y) == len(nw_x) == len(psd_x) == len(rail) == 1
    return {"a": a, "nw_y": nw_y.pop(), "nw_x": nw_x.pop(),
            "psd_y": psd_y.pop(), "psd_x": psd_x.pop(), "rail": rail.pop()}


def row_fit(lo, hi, size, space):
    """Start coordinates of as many `size` cuts as fit in lo..hi, centred."""
    n = (hi - lo - size) // (size + space) + 1
    if n < 1:
        return []
    used = n * size + (n - 1) * space
    x0 = lo + (hi - lo - used) // 2
    x0 -= x0 % 5
    return [x0 + i * (size + space) for i in range(n)]


def draw(ly, sites, env):
    sw, h = site()
    w = sites * sw
    name = "DECAPHV%d" % sites
    c = ly.create_cell(name)
    box = lambda k, x0, y0, x1, y1: c.shapes(ly.layer(*L[k])).insert(  # noqa: E731
        pya.Box(x0, y0, x1, y1))
    a = env["a"]

    # --- insets, each the binding one of (foreign neighbour, mirrored self) ---
    t = max(r("TGO_e") // 2, r("TGO_b") - a)
    n = max(r("NW_b") // 2, r("NW_d") - a)
    act_lo = max(n + r("NW_c1"), t + r("TGO_a"))       # x and bottom
    act_hi = h - t - r("TGO_c")                        # channel top
    sd = r("Cnt_c") + r("Cnt_a") + r("Cnt_f")          # contacted S/D
    assert sd >= r("Act_c")
    g0, g1 = act_lo + sd, w - act_lo - sd              # gate = channel in x
    assert g0 >= t + r("TGO_c") and g1 - g0 >= r("Gat_a4"), name
    # pSD tongue: the loosest box that still encloses Activ and the gate
    p_x = min(act_lo - r("pSD_c"), g0 - r("pSD_i1"))
    p_y = act_lo - r("pSD_i1")
    assert p_x >= max(r("pSD_b") // 2, r("pSD_d") - a), name
    assert p_y >= max(r("pSD_b") // 2, r("pSD_d") - a), name

    # --- frame: EZ130's own, so the rows abut as for any library cell ---
    rail = env["rail"]
    box("bnd", 0, 0, w, h)
    box("bnd_ez", 0, 0, w, h)
    box("nwell", -env["nw_x"], env["nw_y"], w + env["nw_x"], h + rail)
    box("psd", -env["psd_x"], env["psd_y"], w + env["psd_x"], h + rail)
    for y0, y1 in ((-rail, rail), (h - rail, h + rail)):
        box("m1", 0, y0, w, y1)
        box("m1pin", 0, y0, w, y1)
    for txt, y in (("VSS", 0), ("VDD", h)):
        c.shapes(ly.layer(*L["m1txt"])).insert(pya.Text(txt, pya.Trans(w // 2, y)))

    # --- the device ---
    box("tgo", t, t, w - t, h - t)
    box("nwell", n, n, w - n, env["nw_y"])
    box("psd", p_x, p_y, w - p_x, env["psd_y"])
    box("activ", act_lo, act_lo, w - act_lo, act_hi)
    cnt, cs = r("Cnt_a"), r("Cnt_b")
    endcap = r("M1_c1")

    # gate poly: channel plus the top endcap, plus a contact strip below Activ
    pc_top = act_lo - r("Cnt_e")
    pc_bot = pc_top - cnt
    box("gatpoly", g0, pc_bot - r("Cnt_d"), g1, act_hi + r("Gat_c"))

    # S/D: one contact column each side, a Metal1 strip up to the VDD rail
    strips = []
    ys = row_fit(act_lo + r("Cnt_c"), act_hi - r("Cnt_c"), cnt, cs)
    for x in (act_lo + r("Cnt_c"), w - act_lo - r("Cnt_c") - cnt):
        for y in ys:
            box("cont", x, y, x + cnt, y + cnt)
        s = (x - endcap, ys[0] - endcap, x + cnt + endcap, h - rail)
        box("m1", *s)
        strips.append(s)

    # gate contacts on the strip, a Metal1 bar down into the VSS rail
    bar_x0 = strips[0][2] + r("M1_e")                  # wide-metal spacing
    bar = (bar_x0, rail, w - bar_x0, pc_top + endcap)
    assert strips[0][1] - bar[3] > 0 or bar_x0 - strips[0][2] >= r("M1_b")
    box("m1", *bar)
    xs = row_fit(max(bar[0] + endcap, g0 + r("Cnt_d")),
                 min(bar[2] - endcap, g1 - r("Cnt_d")), cnt, cs)
    assert xs, "%s: no room for a gate contact" % name
    for x in xs:
        box("cont", x, pc_bot, x + cnt, pc_top)

    geo = {"name": name, "w": w, "h": h, "rail": rail, "strips": strips,
           "bar": bar, "W": (act_hi - act_lo) * DBU, "L": (g1 - g0) * DBU,
           "ngc": len(xs), "nsd": 2 * len(ys)}
    print("%-9s %5.2f um wide: PMOS W %.3f L %.3f = %.3f um2, TGO inset %.3f, "
          "%d S/D + %d gate contacts" % (name, w * DBU, geo["W"], geo["L"],
                                         geo["W"] * geo["L"], t * DBU,
                                         geo["nsd"], geo["ngc"]))
    return geo


# --- text views ---------------------------------------------------------------

def spdx(tok):
    # REUSE-IgnoreStart
    return ("%s SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University\n"
            "%s SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1\n"
    # REUSE-IgnoreEnd
            "%s Generated by ip/%s/scripts/decap_hv_gen.py -- do not edit.\n"
            % (tok, tok, tok, LIB))


def f(v):
    return ("%.3f" % (v * DBU)).rstrip("0").rstrip(".")


def lef_macro(g):
    rect = lambda b: "        RECT %s %s %s %s ;\n" % tuple(f(v) for v in b)  # noqa: E731
    w, h, rl = g["w"], g["h"], g["rail"]
    vdd = rect((0, h - rl, w, h + rl)) + "".join(rect(s) for s in g["strips"])
    vss = rect((0, -rl, w, rl)) + rect(g["bar"])
    pin = lambda nm, use, body: (  # noqa: E731
        "  PIN %s\n    DIRECTION INOUT ;\n    USE %s ;\n    SHAPE ABUTMENT ;\n"
        "    PORT\n      LAYER Metal1 ;\n%s    END\n  END %s\n" % (nm, use, body, nm))
    return ("MACRO {n}\n  CLASS CORE SPACER ;\n  ORIGIN 0 0 ;\n  FOREIGN {n} 0 0 ;\n"
            "  SIZE {w} BY {h} ;\n  SYMMETRY X Y ;\n  SITE CoreSite ;\n"
            .format(n=g["name"], w=f(w), h=f(h))
            + pin("VDD", "POWER", vdd) + pin("VSS", "GROUND", vss)
            + "END %s\n" % g["name"])


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)
    print("WROTE %s" % path)


def main():
    ez = pya.Layout()
    ez.read(os.path.join(EZ, "gds", "ez130_8t.gds"))
    assert abs(ez.dbu - DBU) < 1e-12
    env = envelope(ez)
    print("EZ130 envelope: Activ %.3f from the edge, NWell/pSD bands from y %.3f/%.3f, "
          "rail half-width %.3f" % (env["a"] * DBU, env["nw_y"] * DBU,
                                    env["psd_y"] * DBU, env["rail"] * DBU))
    ly = pya.Layout()
    ly.dbu = DBU
    geos = [draw(ly, s, env) for s in SIZES]
    os.makedirs(os.path.join(ROOT, "gds"), exist_ok=True)
    write_gds(ly, os.path.join(ROOT, "gds", LIB + ".gds"))
    print("WROTE %s" % os.path.join(ROOT, "gds", LIB + ".gds"))

    write(os.path.join(ROOT, "lef", LIB + ".lef"),
          spdx("#") + "\nVERSION 5.8 ;\nBUSBITCHARS \"[]\" ;\nDIVIDERCHAR \"/\" ;\n\n"
          + "\n".join(lef_macro(g) for g in geos) + "\nEND LIBRARY\n")
    write(os.path.join(ROOT, "cdl", LIB + ".cdl"), spdx("*") + "".join(
        "\n.SUBCKT %s VDD VNW VPW VSS\n*.PININFO VDD:B VNW:B VPW:B VSS:B\n"
        "MP0 VDD VSS VDD VNW sg13_hv_pmos m=1 w=%.3fu l=%.3fu ng=1\n.ENDS\n"
        % (g["name"], g["W"], g["L"]) for g in geos))
    write(os.path.join(ROOT, "verilog", LIB + ".v"), spdx("//") + "`timescale 1ns/10ps\n" + "".join(
        "\n`celldefine\nmodule %s ();\nendmodule\n`endcelldefine\n" % g["name"] for g in geos))
    write(os.path.join(ROOT, "verilog", LIB + "_pwr.v"), spdx("//") + "`timescale 1ns/10ps\n" + "".join(
        "\n`celldefine\nmodule %s (VDD, VSS);\n"
        "    (* pg_type = \"primary_power\" *) input VDD;\n"
        "    (* pg_type = \"primary_ground\" *) input VSS;\nendmodule\n`endcelldefine\n"
        % g["name"] for g in geos))


main()
