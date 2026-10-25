# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Ported from OpenBLAU 8f25e634, scripts/esd/ring_clip.py
# Description: metal-only clip of the chip's pad ring, labelled for kpex --wires
"""The pad ring and the core ring of the chip GDS, metal and vias only,
cut down to the nets that carry ESD current, with one port label per pad slot
and rail. kpex extracts it as an interconnect (scripts/esd/pex.py).

  klayout -b -r scripts/esd/ring_clip.py -rd out=<dir>

Writes <out>/esd_ring.gds (top cell esd_ring) and <out>/ports.json.

Reads the unfilled GDS: fill is isolated metal and carries no ESD current.

Ports, all on datatype 25 of their layer:
  <rail>_<slot>   one per rail band of a pad cell, at the cell's centre line.
                  Repeated names on one slot are one node (the bands of a rail
                  in one cell are via-stitched), which is where the pad cell's
                  ESD devices attach.
  pad_<slot>      the bond pad plate
  padc_<slot>     the pad cell's pad terminal (the 3 um pin strip at the
                  outer edge)
  <rail>ring_<k>  the core ring, eight points per rail, where the core decap
                  and the core circuits attach
"""

import json
import math
import os
import re
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
GDS = os.path.join(REPO, "layout", "sg13cmos5l_dsa1_dig_top.gds.gz")
IO_LEF = os.path.join(os.environ.get("PDK_ROOT", "/foss/pdks"),
                      os.environ.get("PDK", "ihp-sg13cmos5l"),
                      "libs.ref", "sg13cmos5l_io", "lef", "sg13cmos5l_io.lef")
TOP = "sg13cmos5l_dsa1_dig_top"
CLAMP = "sg13cmos5l_ip__clamp_vddvss"
CLAMP_DIR = os.path.join(REPO, "ip", CLAMP)
sys.path.insert(0, os.path.join(CLAMP_DIR, "layout"))
import clamp  # noqa: E402  the clamp cell's geometry, read, not copied

# conductor stack, bottom up: (name, gds layer); vias between
STACK = [("Metal1", 8), ("Via1", 19), ("Metal2", 10), ("Via2", 29), ("Metal3", 30),
         ("Via3", 49), ("Metal4", 50), ("TopVia1", 125), ("TopMetal1", 126)]
METALS = {n: l for n, l in STACK if "Via" not in n}
RAILS = ("vdd", "vss", "iovdd", "iovss")
DIE = 1600.0
# inside the core ring's inner conductor (W 363.4, S 364.24, N 1235.12, E 1236.8)
CORE_BOX = (364.5, 364.5, 1235.0, 1235.0)
# core ring conductor centre lines (W, E, S, N), read off the GDS: Metal4 on
# W and E, TopMetal1 on S and N, vdd inner on every side
RING = {"vss": (335.9, 1264.3, 336.74, 1262.62), "vdd": (355.9, 1244.3, 356.74, 1242.62)}
# bond pad label -> slot name (no brackets, no "__", for SPICE node names)
SIGNAL = {"output_PAD[0]": "miso", "output_PAD[1]": "adcconv",
          **{f"output_PAD[{i}]": f"tst{i - 2}" for i in range(2, 18)},
          "input_PAD[0]": "datain", "input_PAD[1]": "sclk", "input_PAD[2]": "mosi",
          "input_PAD[3]": "ss", "rst_n_PAD": "rstn", "clk_PAD": "clk",
          "analog_PAD[0]": "ana0", "analog_PAD[1]": "ana1",
          "bidir_PAD[0]": "bidir0", "bidir_PAD[1]": "bidir1"}


def die(msg):
    sys.stderr.write(f"ring_clip: {msg}\n")
    sys.exit(1)


def lef_pins(path):
    """{macro: {pin: [(layer, x0, y0, x1, y1)]}} from a LEF, rectangles only."""
    out, mac, pin, lay = {}, None, None, None
    for ln in open(path):
        t = ln.split()
        if not t:
            continue
        if t[0] == "MACRO":
            mac = t[1]
            out[mac] = {}
        elif t[0] == "PIN" and mac:
            pin = t[1]
            out[mac].setdefault(pin, [])
        elif t[0] == "END" and len(t) > 1 and t[1] == pin:
            pin = None
        elif t[0] == "LAYER" and pin:
            lay = t[1]
        elif t[0] == "RECT" and pin:
            out[mac][pin].append((lay, *map(float, t[1:5])))
    return out


def side_along(t, w, h):
    """Side letter of a ring cell from its transform, the nearest die edge, and
    its centre's coordinate along that side."""
    c = t * pya.DPoint(w / 2, h / 2)
    x, y = c.x, c.y
    return min((("w", y, x), ("e", y, DIE - x), ("s", x, y), ("n", x, DIE - y)),
               key=lambda e: e[2])[:2]


def slot_numbers(cells):
    """{instance index: (side, slot)}: the pad cells numbered per side in their
    order, bottom to top (W, E) and left to right (S, N), as in doc/pinout.md.
    The clamp cell is no pad slot, so the pads keep their numbers."""
    per = {}
    for i, (side, a) in cells.items():
        per.setdefault(side, []).append((a, i))
    return {i: (side, k + 1) for side, lst in per.items() for k, (_, i) in enumerate(sorted(lst))}


def band_labels(macro, pins, t, w=80.0):
    """[(rail, layer, x, y)] at the centre of each rail rectangle, on the
    cell's centre line across the ring (the rectangles run along it)."""
    out, xc = [], w / 2
    for rail in RAILS:
        band = [r for r in pins.get(rail, []) if r[4] > 3.0]  # not the pad strip
        full = [r for r in band if r[3] - r[1] >= 70.0]
        if not full and band:
            # a band split along the pad: the piece on the centre line, else
            # the widest, at its own centre
            on = [r for r in band if r[1] <= xc <= r[3]]
            full = [max(on or band, key=lambda r: r[3] - r[1])]
        for lay, x0, y0, x1, y1 in full:
            x = xc if x0 <= xc <= x1 else (x0 + x1) / 2
            p = t * pya.DPoint(x, (y0 + y1) / 2)
            out.append((rail, lay, p.x, p.y))
    return out


def clamp_labels(t):
    """[(rail, x, y)] of the clamp: every Metal2 stripe of its three blocks, at
    the fingers' centroid, so the stripes up to the bands are extracted."""
    m = clamp.Mos(clamp.CL_COLS, clamp.CL_Y0, clamp.CL_GATES, 0.6, ("vss", "vdd"),
                  drain_w={"vdd": 1.18})
    yc = (m.y0 + m.y1) / 2
    out = []
    for s0, s1, rail in clamp.CL_STRIPES:
        for xf in clamp.BLOCKS.values():
            p = t * pya.DPoint(clamp.xmap((s0 + s1) / 2, xf), yc)
            out.append((rail, p.x, p.y))
    return out


def extract(regions, dbu):
    """LayoutToNetlist over the clipped stack: (l2n, {layer name: l2n layer})."""
    ly = pya.Layout()
    ly.dbu = dbu
    c = ly.create_cell("clip")
    for n, l in STACK:
        c.shapes(ly.layer(l, 0)).insert(regions[n])
    l2n = pya.LayoutToNetlist(pya.RecursiveShapeIterator(ly, c, []))
    lay = {n: l2n.make_layer(ly.layer(l, 0), n) for n, l in STACK}
    for n, _ in STACK:
        l2n.connect(lay[n])
    for i in range(0, len(STACK) - 2, 2):
        lo, via, hi = STACK[i][0], STACK[i + 1][0], STACK[i + 2][0]
        l2n.connect(lay[lo], lay[via])
        l2n.connect(lay[via], lay[hi])
    l2n.extract_netlist()
    return l2n, lay, ly


def main(out):
    ly = pya.Layout()
    ly.read(GDS)
    top = ly.cell(TOP)
    if top is None:
        die(f"no cell {TOP} in {GDS}")
    dbu = ly.dbu
    io = lef_pins(IO_LEF)
    io.update(lef_pins(os.path.join(CLAMP_DIR, "lef", f"{CLAMP}.lef")))

    # clip: the die minus the core, every conductor flattened, merged
    die_box = top.dbbox()
    core = pya.Region(pya.DBox(*CORE_BOX).to_itype(dbu))
    ann = pya.Region(die_box.to_itype(dbu)) - core
    regions = {}
    for n, l in STACK:
        li = ly.find_layer(l, 0)
        r = pya.Region(top.begin_shapes_rec(li)) if li is not None else pya.Region()
        regions[n] = (r & ann).merged()

    # ports
    ports = []
    centre = {}                  # (side, slot) -> pad cell centre
    insts = [i for i in top.each_inst() if i.cell.name.startswith("sg13cmos5l_IOPad")]
    clamps = [i for i in top.each_inst() if i.cell.name == CLAMP]
    numbers = slot_numbers({j: side_along(i.dcplx_trans, 80.0, i.cell.dbbox().height())
                            for j, i in enumerate(insts)})
    for j, inst in enumerate(insts):
        m = inst.cell.name
        t = inst.dcplx_trans
        h = inst.cell.dbbox().height()
        side, k = numbers[j]
        centre[(side, k)] = t * pya.DPoint(40.0, h / 2)
        for rail, lay, x, y in band_labels(m, io[m], t):
            ports.append(dict(kind="rail", rail=rail, layer=lay, x=x, y=y,
                              side=side, k=k, master=m))
        p = t * pya.DPoint(40.0, 1.5)
        ports.append(dict(kind="padc", layer="TopMetal1", x=p.x, y=p.y,
                          side=side, k=k, master=m))
    # the clamp cell: its bands, and a port on every stripe for the clamp itself
    if len(clamps) != 1:
        die(f"{len(clamps)} instances of {CLAMP}, want 1")
    t = clamps[0].dcplx_trans
    w, h = clamps[0].cell.dbbox().width(), clamps[0].cell.dbbox().height()
    side = side_along(t, w, h)[0]
    for rail, lay, x, y in band_labels(CLAMP, io[CLAMP], t, w):
        ports.append(dict(kind="rail", rail=rail, layer=lay, x=x, y=y,
                          side=side, k=0, master=CLAMP))
    for rail, x, y in clamp_labels(t):
        ports.append(dict(kind="clamp", rail=rail, layer="Metal2", x=x, y=y,
                          side=side, k=0, master=CLAMP))

    # bond pad plates: the chip's own pad labels name them
    names = {}
    tm_lbl = ly.find_layer(126, 25)
    for s in top.shapes(tm_lbl).each(pya.Shapes.STexts):
        x, y = s.text.trans.disp.x * dbu, s.text.trans.disp.y * dbu
        name = s.text.string
        key = min(centre, key=lambda c: (centre[c].x - x) ** 2 + (centre[c].y - y) ** 2)
        if key in names:
            die(f"two pad labels on slot {key}: {names[key]} and {name}")
        base = name.lower()
        if base in RAILS:
            names[key] = f"{base}_{key[0]}{key[1]}"
        elif name in SIGNAL:
            names[key] = SIGNAL[name]
        else:
            die(f"pad label {name} has no slot name")
        ports.append(dict(kind="pad", layer="TopMetal1", x=x, y=y,
                          side=key[0], k=key[1], master="bondpad"))
    # every pad slot must reach all four rails: a slot missing one leaves that
    # node of its HBM subcircuit floating, which simulates as a clamp that is
    # not there and fails nothing
    names[(side, 0)] = "clamp"
    for key in list(centre) + [(side, 0)]:
        have = {p["rail"] for p in ports if p["kind"] == "rail"
                and (p["side"], p["k"]) == key}
        if have != set(RAILS):
            die(f"pad slot {key}: no port on {sorted(set(RAILS) - have)}")
    slots = {(p["side"], p["k"]) for p in ports if p["kind"] == "padc"}
    if slots != set(names) - {(side, 0)}:
        die(f"pad slots without a label: {sorted(slots - set(names))}")

    # core ring, eight points per rail on its Metal4 sides and TopMetal1 top/bottom
    ring = []
    for rail, (w, e, so, no) in RING.items():
        for i, (x, y, lay) in enumerate([(w, 600.0, "Metal4"), (w, 1000.0, "Metal4"),
                                         (e, 600.0, "Metal4"), (e, 1000.0, "Metal4"),
                                         (600.0, so, "TopMetal1"), (1000.0, so, "TopMetal1"),
                                         (600.0, no, "TopMetal1"), (1000.0, no, "TopMetal1")]):
            ring.append(dict(kind="ring", rail=rail, layer=lay, x=x, y=y, k=i,
                             name=f"{rail}ring_{i}"))

    for p in ports:
        slot = names[(p["side"], p["k"])]
        p["slot"] = slot
        p["name"] = {"rail": f"{p.get('rail')}_{slot}", "pad": f"pad_{slot}",
                     "padc": f"padc_{slot}",
                     "clamp": f"{'clv' if p.get('rail') == 'vdd' else 'cls'}_{slot}"}[p["kind"]]
    ports += ring

    # every port must land on its own layer's metal
    for p in ports:
        pt = pya.DBox(p["x"] - 0.05, p["y"] - 0.05, p["x"] + 0.05, p["y"] + 0.05).to_itype(dbu)
        if regions[p["layer"]].interacting(pya.Region(pt)).is_empty():
            if p["kind"] == "pad":       # a label on the plate edge: step inward 1 um
                p["x"], p["y"] = step_in(p["x"], p["y"])
                pt = pya.DBox(p["x"] - 0.05, p["y"] - 0.05,
                              p["x"] + 0.05, p["y"] + 0.05).to_itype(dbu)
            if regions[p["layer"]].interacting(pya.Region(pt)).is_empty():
                die(f"port {p['name']} at ({p['x']:.2f}, {p['y']:.2f}) is not on {p['layer']}")

    # nets: one extraction, every port probed onto the net under it
    l2n, lay, _ = extract(regions, dbu)
    net_of = {}
    for p in ports:
        net = l2n.probe_net(lay[p["layer"]], pya.DPoint(p["x"], p["y"]))
        if net is None:
            die(f"port {p['name']} probes no net")
        net_of[p["name"]] = net.cluster_id
    # a stripe port off its rail's metal would leave the clamp floating, silently
    on = {}
    for p in ports:
        if p["kind"] == "rail":
            on.setdefault(p["rail"], set()).add(net_of[p["name"]])
    for p in ports:
        if p["kind"] == "clamp":
            cid = l2n.probe_net(lay["Metal2"], pya.DPoint(p["x"], p["y"])).cluster_id
            if cid not in on[p["rail"]]:
                die(f"{p['name']} at ({p['x']:.2f}, {p['y']:.2f}) is not on {p['rail']}'s metal")
    groups = {}
    for p in ports:
        net = p.get("rail") or p["slot"]
        if p["kind"] in ("pad", "padc") and p["slot"].split("_")[0] in RAILS:
            net = p["slot"].split("_")[0]      # a supply pad's plate is its rail
        p["net"] = net
        groups.setdefault(net, []).append(p)
    # a rail may split into islands: reported, not fatal, since the deck
    # joins nothing that is not drawn
    islands = {}
    for net, ps in sorted(groups.items()):
        ids = sorted({net_of[p["name"]] for p in ps})
        islands[net] = [[p["name"] for p in ps if net_of[p["name"]] == i] for i in ids]
        if len(ids) > 1:
            print(f"ring_clip: {net} is {len(ids)} islands: " +
                  "; ".join(f"{len(g)} ports from {g[0]}" for g in islands[net]))
    # no two nets may share metal: a short here is a layout defect
    owner = {}
    for net, ps in groups.items():
        for p in ps:
            o = owner.setdefault(net_of[p["name"]], net)
            if o != net:
                die(f"{o} shares metal with {net} at {p['name']}")
    # keep the metal of the probed nets only
    keep_ids = set(net_of.values())
    circ = l2n.netlist().top_circuit()
    kept = {n: pya.Region() for n, _ in STACK}
    for net in circ.each_net():
        if net.cluster_id in keep_ids:
            for n, _ in STACK:
                kept[n] += l2n.shapes_of_net(net, lay[n], True)
    for n in kept:
        kept[n].merge()
    report = {k: v for k, v in islands.items() if len(v) > 1}

    # write
    oly = pya.Layout()
    oly.dbu = dbu
    oc = oly.create_cell("esd_ring")
    for n, l in STACK:
        oc.shapes(oly.layer(l, 0)).insert(kept[n])
    for p in ports:
        oc.shapes(oly.layer(METALS[p["layer"]], 25)).insert(
            pya.DText(p["name"], pya.DTrans(p["x"], p["y"])))
    os.makedirs(out, exist_ok=True)
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    from gdswrite import write_gds
    write_gds(oly, os.path.join(out, "esd_ring.gds"))
    json.dump(dict(gds=os.path.relpath(GDS, REPO), ports=ports,
                   islands=report),
              open(os.path.join(out, "ports.json"), "w"), indent=1)
    area = {n: kept[n].area() * dbu * dbu for n, _ in STACK}
    print(f"ring_clip: {len(ports)} ports, {len(names)} pads; kept um2 " +
          ", ".join(f"{n} {a:.0f}" for n, a in area.items()))


def step_in(x, y):
    """Move a point 1 um from the die edge toward the die centre."""
    dx, dy = DIE / 2 - x, DIE / 2 - y
    if abs(dx) > abs(dy):
        return x + math.copysign(1.0, dx), y
    return x, y + math.copysign(1.0, dy)


out = globals().get("out")
if not out:
    die("usage: klayout -b -r ring_clip.py -rd out=<dir>")
main(out)
