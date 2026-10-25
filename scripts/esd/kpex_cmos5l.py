#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Ported from OpenBLAU 8f25e634, scripts/kpex_cmos5l.py
# Description: kpex on ihp-sg13cmos5l, and a correct R+C netlist from its 2.5D run
"""kpex 0.4.4 (image 83ae1840458f) on its ihp-sg13cmos5l handle, fixed.

  kpex_cmos5l.py <overlay_dir> [--rc-netlist OUT] extract --pdk ihp-sg13cmos5l ...
  kpex_cmos5l.py --rebuild OUT.pkl <cell>.lvsdb.gz OUT     (writer only)
  --wires: an interconnect, every label its own port node (dco_pex.py)

THE DECK. kpex ships its cmos5l PEX top deck but only 5 of the ~50 rule decks
it includes, so every run dies on `rule_decks//sram_integration.lvs`. The 5 it
ships are byte-identical to the PDK's, so a run-local overlay completes it:

  top deck                  kpex's sg13cmos5l.lvs (the PEX variant)
  rule_decks/*              $PDK_ROOT/ihp-sg13cmos5l LVS rule decks
  auto_name_layers.rb       kpex's (PEX only, not in any PDK)
  rfmos_model_mapping.lvs   EMPTIED: it swaps every rfnmos for a new device
                            with no geometry, for the compare, and the R
                            extractor then dies on it. PEX compares nothing.

THE TECH. kpex's cmos5l tech gives Metal4 no contact above it, so TopVia1
connects nothing and every TopMetal1 shape is cut off from its net's R
network; the overlay carries a copy with TopVia1 filled in.

Two crashes patched: rfnmos device abstracts are extra top cells of the LVSDB
layout (top_cell_bbox), and --blackbox MOM/MIM caps carry no 'C' parameter
(the printer). The console echo of the CSV netlist is dropped (the file
stays): on a large interconnect it costs hours.

THE NETLIST (--rc-netlist). kpex's own 2.5D RC netlist is not a circuit:
every device stays on the bare net while the R network's device-terminal
nodes are separate, so the R never sits between two devices; parallel R
elements between one node pair are ADDED; and all coupling C sits on the bare
nets. This rebuilds it from the same extraction: each device terminal on the
network node(s) of its own terminal polygon, each resistor element as it came,
each cap between the nearest nodes of its two nets on its own layers at the
place the extractor measured it, substrate caps to `vss`. 0 ohm elements and a
terminal's several polygons merge into one node; a terminal with no polygon of
its own (a MOS bulk, a blackboxed MOM's pin) goes to the nearest node of its
net at the device's position. Devices are written for ngspice by parameter
name: KLayout's generic writer puts a MOM's w where C belongs and drops l.
Neither the image nor $PDK_ROOT is touched.
"""

import math
import os
import shutil
import sys
from collections import defaultdict

REC = {"caps": [], "nodes": {}}


def build_overlay(dst):
    import klayout_pex
    pkg = os.path.join(os.path.dirname(klayout_pex.__file__), "pdk")
    kc5 = os.path.join(pkg, "ihp-sg13cmos5l", "libs.tech", "kpex")
    kg2 = os.path.join(pkg, "ihp-sg13g2", "libs.tech", "kpex", "rule_decks")
    pdk = os.path.join(os.environ.get("PDK_ROOT", "/foss/pdks"), "ihp-sg13cmos5l",
                       "libs.tech", "klayout", "tech", "lvs", "rule_decks")
    rd = os.path.join(dst, "rule_decks")
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(pdk, rd)
    shutil.copy(os.path.join(kg2, "auto_name_layers.rb"), rd)
    with open(os.path.join(rd, "rfmos_model_mapping.lvs"), "w") as f:
        f.write("# emptied by kpex_cmos5l.py: PEX keeps the extracted rfnmos\n")
    # kpex's own cmos5l decks must be the PDK's, or this overlay is stale
    for f in os.listdir(os.path.join(kc5, "rule_decks")):
        a, b = os.path.join(kc5, "rule_decks", f), os.path.join(rd, f)
        if open(a, "rb").read() != open(b, "rb").read():
            sys.exit(f"kpex_cmos5l: kpex's {f} differs from the PDK's, re-check")
    top = os.path.join(dst, "sg13cmos5l.lvs")
    shutil.copy(os.path.join(kc5, "sg13cmos5l.lvs"), top)

    # the tech: Metal4 names no contact above it, so TopVia1 joins nothing
    # and every TopMetal1 shape is cut off from its net's R network (kpex
    # logs "ignoring layer TopVia1 ... no bottom/top layers"). z from the
    # tech itself; 0.42 um cut and space are TV1.a/TV1.b.
    import json
    src = os.path.join(os.path.dirname(os.path.dirname(pkg)), "klayout_pex_protobuf",
                       "ihp-sg13cmos5l_tech.pb.json")
    t = json.load(open(src))
    ml = {l["name"]: l for l in t["process_stack"]["layers"]}
    m4 = ml["Metal4"]["metal_layer"]
    if m4.get("contact_above"):
        sys.exit("kpex_cmos5l: kpex's Metal4 has a contact above now, drop this patch")
    m4["contact_above"] = dict(
        name="topvia1_n_cap", layer_below="metal4_con", metal_above="topmetal1_con",
        thickness=round(ml["TopMetal1"]["metal_layer"]["z"] - m4["z"] - m4["thickness"], 4),
        width=0.42, spacing=0.42)
    tech = os.path.join(dst, "ihp-sg13cmos5l_tech.pb.json")
    json.dump(t, open(tech, "w"), indent=1)
    return top, tech


def patch_crashes(top, tech):
    import klayout.db as kdb
    from klayout_pex.pdk_config import PDK, PDKConfig
    from klayout_pex.klayout.lvsdb_extractor import KLayoutExtractionContext as X
    from klayout_pex.klayout.netlist_printer import NetlistPrinter as P
    p = PDK.IHP_SG13CMOS5L
    # cached_property is a non-data descriptor: the instance dict wins
    p.__dict__["config"] = PDKConfig(name=p, pex_lvs_script_path=top,
                                     tech_pb_json_path=tech)

    def top_cell_bbox(self):
        b1 = self.annotated_layout.top_cell().bbox()
        b2 = self.lvsdb.internal_top_cell().bbox()
        return b1 if b1.area() > b2.area() else b2
    X.top_cell_bbox = top_cell_bbox

    # The 2.5D engine echoes its whole CSV netlist to the console line by
    # line, after writing the same CSV to a file: on the chip's pad ring that
    # is hours of printing for one resistor per record (scripts/esd/pex.py).
    import klayout_pex.kpex_cli as cli
    verbatim = cli.subproc
    cli.subproc = lambda msg, *a, **k: None if ";" in str(msg) else verbatim(msg, *a, **k)

    own = P.write_device

    def write_device(self, device):
        dc = device.device_class()
        if isinstance(dc, kdb.DeviceClassCapacitor) and not dc.has_parameter("C"):
            return kdb.NetlistSpiceWriterDelegate.write_device(self, device)
        return own(self, device)
    P.write_device = write_device


# ---------------------------------------------------------------- recording
def patch_recorders():
    import klayout.pex as klp
    from klayout_pex.rcx25.extraction_reporter import ExtractionReporter as ER
    from klayout_pex.rcx25.extractor import RCX25Extractor
    from klayout_pex.rcx25.r.r_extractor import RExtractor
    from klayout_pex.klayout.rex_core import klayout_r_extractor_tech

    def c(p):
        return (p.x, p.y)

    def ctr_edge(e):
        return ((e.p1.x + e.p2.x) / 2, (e.p1.y + e.p2.y) / 2)

    o_ovl, o_sw, o_so = ER.output_overlap, ER.output_sidewall, ER.output_sideoverlap

    def output_overlap(self, overlap_cap, bottom_polygon, top_polygon, overlap_area):
        k = overlap_cap.key
        pt = c(overlap_area.bbox().center())
        REC["caps"].append((k.net_top, k.layer_top, pt, k.net_bot, k.layer_bot, pt,
                            overlap_cap.cap_value))
        return o_ovl(self, overlap_cap, bottom_polygon, top_polygon, overlap_area)

    def output_sidewall(self, sidewall_cap, inside_edge, outside_edge):
        k = sidewall_cap.key
        REC["caps"].append((k.net1, k.layer, ctr_edge(inside_edge), k.net2, k.layer,
                            ctr_edge(outside_edge), sidewall_cap.cap_value))
        return o_sw(self, sidewall_cap, inside_edge, outside_edge)

    def output_sideoverlap(self, sideoverlap_cap, inside_edge, outside_polygon,
                           lateral_shield):
        k = sideoverlap_cap.key
        pt = ctr_edge(inside_edge)
        REC["caps"].append((k.net_inside, k.layer_inside, pt, k.net_outside,
                            k.layer_outside, pt, sideoverlap_cap.cap_value))
        return o_so(self, sideoverlap_cap, inside_edge, outside_polygon, lateral_shield)

    ER.output_overlap, ER.output_sidewall = output_overlap, output_sidewall
    ER.output_sideoverlap = output_sideoverlap

    o_init = RCX25Extractor.__init__

    def init(self, *a, **kw):
        o_init(self, *a, **kw)
        t = self.tech_info
        REC.update(cell=self.pex_context.annotated_top_cell.name, dbu=self.pex_context.dbu,
                   sub=t.internal_substrate_layer_name,
                   canon=dict(t.canonical_layer_name_by_gds_pair))
    RCX25Extractor.__init__ = init

    # The R networks, re-extracted from kpex's own request with kpex's own
    # tech, keeping what its result drops: the terminal behind each port.
    o_extract = RExtractor.extract

    def extract(self, rex_request):
        import klayout.db as kdb
        tech = klayout_r_extractor_tech(rex_request.tech)
        for req in rex_request.net_extraction_requests:
            vports, pports, pterm = defaultdict(list), defaultdict(list), defaultdict(list)
            plabel = defaultdict(list)
            regions = defaultdict(__import__("klayout.db", fromlist=["x"]).Region)
            circ = self.pex_context.lvsdb.netlist().circuit_by_name(
                self.pex_context.annotated_top_cell.name)
            for t in req.device_terminals:
                d = circ.device_by_id(t.device_id)
                tn = d.device_class().terminal_definitions()[t.terminal_id].name
                for l2r in t.region_by_layer:
                    for sh in l2r.region.shapes:
                        pports[l2r.layer.id].append(self.shapes_converter.klayout_shape(sh))
                        pterm[l2r.layer.id].append((d.expanded_name(), tn))
            for l2r in req.region_by_layer:
                regions[l2r.layer.id] = self.shapes_converter.klayout_region(l2r.region)
            if REC.get("labels") is None:
                for pin in req.pins:
                    vports[pin.layer.id].append(
                        self.shapes_converter.klayout_point(pin.label_point))
                    plabel[pin.layer.id].append(pin.label)
            else:
                # interconnect: every GDS label on this net's metal is a port.
                # kpex's own pins cannot be used: a net with several labels is
                # named by all of them and kpex files each label elsewhere.
                ly = self.pex_context.annotated_layout
                for (gl, x, y, text) in REC["labels"]:
                    li = ly.find_layer(gl, 0)
                    if li is None or li not in regions:
                        continue
                    box = kdb.Region(kdb.Box(x - 1, y - 1, x + 1, y + 1))
                    if not (regions[li] & box).is_empty():
                        vports[li].append(kdb.Point(x, y))
                        plabel[li].append(text)
            net = klp.RNetExtractor(self.pex_context.dbu).extract(tech, regions, vports, pports)
            nodes, elems = {}, []
            for rn in net.each_node():
                b = rn.location()
                kind, term, label = rn.type(), None, None
                if kind == klp.RNodeType.PolygonPort:
                    term = pterm[rn.layer()][rn.port_index()]
                elif kind == klp.RNodeType.VertexPort:
                    label = plabel[rn.layer()][rn.port_index()]
                nodes[rn.object_id()] = dict(
                    name=f"{req.net_name}.{rn.to_s()}", layer=rn.layer(),
                    xy=((b.p1.x + b.p2.x) / 2, (b.p1.y + b.p2.y) / 2),  # um
                    pin=kind == klp.RNodeType.VertexPort, term=term, label=label)
            for el in net.each_element():
                elems.append((el.a().object_id(), el.b().object_id(), el.resistance()))
            REC["nodes"][req.net_name] = (nodes, elems)
        ly = self.pex_context.annotated_layout
        REC["layers"] = {li: (ly.get_info(li).layer, ly.get_info(li).datatype)
                         for li in ly.layer_indexes()}
        return o_extract(self, rex_request)
    RExtractor.extract = extract


# ---------------------------------------------------------------- assembly
class UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b, keep=None):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if keep == rb:
            ra, rb = rb, ra
        self.p[rb] = ra


# kpex device class -> (ngspice subcircuit, terminal order, parameter writer).
# PDK units are SI; the LVSDB carries um and um^2.
def _mos(sub, rf):
    def f(p):
        s = (f"w={p['W']:.6g}e-6 l={p['L']:.6g}e-6 as={p['AS']:.6g}e-12 "
             f"ad={p['AD']:.6g}e-12 ps={p['PS']:.6g}e-6 pd={p['PD']:.6g}e-6")
        return s + (" rfmode=1" if rf else "")
    return sub, ("D", "G", "S", "B"), f


def _res(sub):
    return sub, (f"{sub}_1", f"{sub}_2", f"{sub}_sub"), \
        lambda p: f"w={p['w']:.6g}e-6 l={p['l']:.6g}e-6 m={p['m']:g} b={p['b']:g}"


DEVICES = {
    "sg13_lv_nmos": _mos("sg13_lv_nmos", False), "sg13_lv_pmos": _mos("sg13_lv_pmos", False),
    "sg13_hv_nmos": _mos("sg13_hv_nmos", False), "sg13_hv_pmos": _mos("sg13_hv_pmos", False),
    "rfnmos": _mos("sg13_lv_nmos", True), "rfpmos": _mos("sg13_lv_pmos", True),
    "rfnmoshv": _mos("sg13_hv_nmos", True), "rfpmoshv": _mos("sg13_hv_pmos", True),
    "rhigh": _res("rhigh"), "rppd": _res("rppd"), "rsil": _res("rsil"),
    # mmin/mmax are not LVS parameters: the writer reads them off the metals
    # drawn inside the device's marker (1..4, 2..4 and 3..4 all occur here)
    "cap_cmomf": ("cap_cmomf", ("mim_top", "mim_btm"),
                  lambda p: f"w={p['w']:.6g}e-6 l={p['l']:.6g}e-6 mmin={p['mmin']} "
                            f"mmax={p['mmax']} m={p['m']:g}"),
    "pnpMPA": ("pnpMPA", ("C", "B", "E"),
               lambda p: f"a={p['A']:.6g}e-12 p={p['P']:.6g}e-6 m={p['m']:g}"),
}


def spice_name(s):
    return s.replace("\\$", "n").replace("$", "_").replace(",", "_")


def write_rc_netlist(rec, lvsdb, out, rmin=1e-3, wires=False):
    import json
    import klayout.db as kdb
    lvs = kdb.LayoutVsSchematic()
    lvs.read(lvsdb)
    circ = lvs.netlist().circuit_by_name(rec["cell"])
    base = lambda n: n.name or f"${n.cluster_id}"
    # identity is the cluster id: an LVSDB read back from file gives two
    # islands of one name the same expanded name AND the same pin name
    eid = lambda n: f"{n.expanded_name()}#{n.cluster_id}"
    if wires:                      # interconnect: a net is its name, every label a node
        eid = base
    key = {base(n) for n in circ.each_net()}
    seen, pname = defaultdict(int), {}
    for p in circ.each_pin():      # vdd_gm, vdd_gm$1, ... as kpex writes them
        k = seen[p.name()]
        seen[p.name()] += 1
        pname[p.id()] = p.name() + (f"${k}" if k else "")
    lname = rec["layers"]

    # kpex keys a network by net NAME, so one network can hold several
    # islands of one name (the -gm's vss is 30, joined only in the parent).
    # Islands are told apart below by DC connectivity and the devices on them.
    uf = UF()
    terms, pins = defaultdict(list), defaultdict(list)
    geo = defaultdict(list)        # (net, gds pair | "*") -> [(x, y, node)], um
    rlist = []
    for net, (nodes, elems) in rec["nodes"].items():
        for nd in nodes.values():
            uf.find(nd["name"])
            if nd["pin"]:
                pins[net].append(nd["name"])
            if nd["term"]:
                terms[tuple(nd["term"])].append(nd["name"])
            geo[(net, lname.get(nd["layer"]))].append((*nd["xy"], nd["name"]))
            geo[(net, "*")].append((*nd["xy"], nd["name"]))
        for a, b, r in elems:
            na, nb = nodes[a]["name"], nodes[b]["name"]
            if r < rmin:
                uf.union(na, nb)
            else:
                rlist.append((na, nb, r))
    for ns in terms.values():      # one device terminal, several polygons
        for n in ns[1:]:
            uf.union(ns[0], n)
    labels = defaultdict(list)
    if wires:                      # one node per label: a leaf pin is one port
        for net, (nodes, _) in rec["nodes"].items():
            for nd in nodes.values():
                if nd.get("label"):
                    labels[nd["label"]].append(nd["name"])
        lost = sorted({t for *_, t in rec["labels"]} - set(labels))
        if lost:
            sys.exit(f"rc-netlist: labels with no node: {lost[:10]}")
        for ns in labels.values():   # repeated labels: one leaf pin, one port
            for n in ns[1:]:
                uf.union(ns[0], n)
    dcc = UF()                     # DC components: 0 ohm groups joined by R
    for n in list(uf.p):
        dcc.find(uf.find(n))
    for a, b, _ in rlist:
        dcc.union(uf.find(a), uf.find(b))
    comp = lambda n: dcc.find(uf.find(n))

    # A shorted dummy (every terminal on one net) carries no current and no
    # C to anything else, and LVS purges it too. Keeping it would also let it
    # claim a substrate-tied piece of metal as its net: the reg's dummy poly
    # resistors did that to vss.
    devices, dummies = [], 0
    for d in circ.each_device():
        if d.device_class().name not in DEVICES:
            continue
        tn = [d.net_for_terminal(t.id()) for t in d.device_class().terminal_definitions()]
        if len({base(n) for n in tn if n is not None}) == 1:
            dummies += 1
            continue
        devices.append(d)
    unknown = sorted({d.device_class().name for d in circ.each_device()} - set(DEVICES))
    if unknown:
        sys.exit(f"rc-netlist: no ngspice mapping for {unknown}")

    # pass 1: terminals on their own polygon's node name their component's net
    comp_nets = defaultdict(set)
    for d in devices:
        dc = d.device_class()
        for tn in DEVICES[dc.name][1]:
            ns = terms.get((d.expanded_name(), tn))
            if ns:
                comp_nets[comp(ns[0])].add(eid(d.net_for_terminal(dc.terminal_id(tn))))
    pin_of = {eid(circ.net_for_pin(p)): pname[p.id()] for p in circ.each_pin()}

    # pass 1b: a MOM or resistor terminal with no node of its own (its port
    # layer is not one kpex maps: "Could not find a layer for device") takes
    # every network piece of its net that touches its terminal shapes. The
    # coarse bank's c1 bar runs slice to slice THROUGH each MOM's own bus, so
    # without this it is 29 pieces. Bulk and substrate terminals never do
    # this: joining islands through the substrate would be a short.
    joined = []
    for d in devices:
        dc = d.device_class()
        if dc.name.startswith("sg13_") or dc.name.startswith("rf"):
            continue
        for tn in DEVICES[dc.name][1]:
            if tn.endswith("_sub") or tn in ("B",) or terms.get((d.expanded_name(), tn)):
                continue
            n0 = d.net_for_terminal(dc.terminal_id(tn))
            reg = kdb.Region()
            for nt in n0.each_terminal():
                if nt.device().id() == d.id() and nt.terminal_id() == dc.terminal_id(tn):
                    for r in lvs.shapes_of_terminal(nt).values():
                        reg += r
            if reg.is_empty():
                continue
            box = reg.bbox().enlarged(int(0.5 / rec["dbu"]))      # 0.5 um to the wire end
            dbu = rec["dbu"]
            hit = [n for x, y, n in geo.get((base(n0), "*"), [])
                   if box.contains(kdb.Point(round(x / dbu), round(y / dbu)))]
            pieces = {}
            for n in hit:
                pieces.setdefault(comp(n), n)
            if not pieces:
                continue
            first = next(iter(pieces.values()))
            for n in list(pieces.values())[1:]:
                uf.union(first, n)
                dcc.union(uf.find(first), uf.find(n))
            terms[(d.expanded_name(), tn)] = [first]
            comp_nets[comp(first)].add(eid(n0))
            joined.append((d.expanded_name(), tn, eid(n0), len(pieces)))
    # components may have merged: recompute which nets they carry
    cn = defaultdict(set)
    for c_, es in comp_nets.items():
        cn[dcc.find(c_)] |= es
    comp_nets = cn

    # every LVS net must be ONE DC piece: count pieces per network name
    # against the LVS nets of that name (a cut-off strap has no device on it)
    lvs_count = defaultdict(int)
    for n in circ.each_net():
        lvs_count[base(n)] += 1
    pieces = {}
    for net, (nodes, _) in rec["nodes"].items():
        cs = {comp(nd["name"]) for nd in nodes.values()}
        pieces[net] = (len(cs), lvs_count.get(net, 0))

    written = {}                   # names written for nets with no R network

    def nearest(net, e, x, y):
        pts = geo.get((net, "*")) or []
        own = [p for p in pts if e in comp_nets.get(comp(p[2]), ())]
        pts = own or [p for p in pts if not comp_nets.get(comp(p[2]))]
        if not pts:                # no R network: the pin, or the bare net name,
            bare = pin_of.get(e, net)  # which is also what its caps are written on
            written[spice_name(bare)] = net
            return bare, None
        b = min(pts, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)
        return uf.find(b[2]), math.hypot(b[0] - x, b[1] - y)

    # every device terminal on a node
    placed, attached = [], []
    for d in devices:
        dc = d.device_class()
        x, y = d.trans.disp.x, d.trans.disp.y
        row = []
        for tn in DEVICES[dc.name][1]:
            n0 = d.net_for_terminal(dc.terminal_id(tn))
            e = eid(n0)
            ns = terms.get((d.expanded_name(), tn))
            if ns:
                node = uf.find(ns[0])
            else:
                node, dist = nearest(base(n0), e, x, y)
                attached.append((d.expanded_name(), tn, e, dist))
                if dist is not None:
                    comp_nets[comp(node)].add(e)
            row.append((node, e))
        placed.append((d, row))

    # each LVS pin to the component that carries its net
    port_of, ties = {}, []
    for lab, ns in labels.items():
        rep = uf.find(ns[0])
        if rep in port_of:
            # two leaves' contacts on ONE polygon (a lead overlapping the
            # array's tank bar): one node, two ports. Overwriting the first
            # left it dangling, which cut the array off dco_core's tank (+14 %
            # in f); the second port joins the node through 1 mohm instead
            ties.append((lab, port_of[rep]))
            continue
        port_of[rep] = lab
    for p in ([] if wires else circ.each_pin()):
        n0 = circ.net_for_pin(p)
        e = eid(n0)
        cs = {c for c, s in comp_nets.items() if e in s}
        if len(cs) > 1:
            sys.exit(f"rc-netlist: pin {pname[p.id()]} ({e}) is {len(cs)} unjoined pieces")
        cand = [n for n in pins.get(base(n0), []) if comp(n) in cs] if cs else \
               [n for n in pins.get(base(n0), [])
                if not comp_nets.get(comp(n)) and uf.find(n) not in port_of]
        if cand:
            rep = uf.find(cand[0])
        elif cs:
            rep = next(nd for d, row in placed for nd, ee in row if ee == e)
        else:
            continue               # no network: the bare net is the pin name
        if rep in port_of:
            sys.exit(f"rc-netlist: pins {port_of[rep]} and {pname[p.id()]} on one node")
        port_of[rep] = pname[p.id()]
        comp_nets[comp(rep)].add(e)

    def name(node):
        r = uf.find(node) if node in uf.p else node
        return port_of.get(r, r)

    body = [f"Rtie{k} {spice_name(a)} {spice_name(b)} 1e-3" for k, (a, b) in enumerate(ties)]

    def write_devices():         # after the MOM markers: they give each its stack
        for d, row in placed:
            dc = d.device_class()
            sub, order, par = DEVICES[dc.name]
            prm = {pd.name: d.parameter(pd.id()) for pd in dc.parameter_definitions()}
            if dc.name == "cap_cmomf":
                prm["mmin"], prm["mmax"] = mom_stack[d.expanded_name()]
            body.append(f"X{spice_name(d.expanded_name())} "
                        f"{' '.join(spice_name(name(n)) for n, _ in row)} {sub} {par(prm)}")
    for i, (a, b, r) in enumerate(rlist):
        na, nb = name(a), name(b)
        if na != nb:
            body.append(f"Rp{i} {spice_name(na)} {spice_name(nb)} {r:.6g}")

    # caps at the nearest node of each net, on its own layer if it has one;
    # location also picks the right island of a split net
    gnd = next((r for r, pn in port_of.items() if pn == "vss"), "vss")
    gds = {v: k for k, v in rec["canon"].items()}
    dist, missing = [], defaultdict(int)

    def near(net, layer, xy):      # xy in dbu, node geometry in um
        if net == rec["sub"]:
            return name(gnd)
        if net not in key:
            missing[net] += 1
            return None
        pts = geo.get((net, gds.get(layer))) or geo.get((net, "*"))
        if not pts:
            written[spice_name(name(net))] = net
            return name(net)
        x, y = xy[0] * rec["dbu"], xy[1] * rec["dbu"]
        b = min(pts, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)
        dist.append(math.hypot(b[0] - x, b[1] - y))
        return name(b[2])

    # A blackboxed MOM keeps its PDK device AND its fingers stay metal, so
    # kpex extracts the same capacitor twice. Drop the caps inside a MOM's
    # marker (Recog.momf, 99/40) between its own two terminal nets: the model
    # carries those. Finger coupling to anything else stays.
    mom, mom_stack = [], {}        # (marker, {net, net}, device, dropped fF, w*l, mmin, mmax)
    ly = kdb.Layout()
    ly.read(rec.get("gds") or os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(lvsdb)))), rec["cell"] + ".gds"))
    if abs(ly.dbu - rec["dbu"]) > 1e-12:
        sys.exit(f"rc-netlist: GDS dbu {ly.dbu} is not the extraction's {rec['dbu']}")
    li = ly.find_layer(99, 40)
    if li is not None:
        mk = kdb.Region(ly.cell(rec["cell"]).begin_shapes_rec(li)).merged()
        metal = {gl: (kdb.Region(ly.cell(rec["cell"]).begin_shapes_rec(ly.find_layer(gl, 0)))
                      if ly.find_layer(gl, 0) is not None else kdb.Region())
                 for gl in (8, 10, 30, 50)}
        for d in devices:
            if d.device_class().name != "cap_cmomf":
                continue
            dc = d.device_class()
            p0 = kdb.Point(round(d.trans.disp.x / ly.dbu), round(d.trans.disp.y / ly.dbu))
            m = [poly for poly in mk.each() if poly.bbox().enlarged(1).contains(p0)]
            if len(m) != 1:
                sys.exit(f"rc-netlist: MOM {d.expanded_name()} in {len(m)} markers")
            nets = {base(d.net_for_terminal(dc.terminal_id(t))) for t in ("mim_top", "mim_btm")}
            # A metal is part of the stack when it is a COMB inside the marker:
            # two interlocking polygons, one per terminal, filling a fifth of
            # it or more, with area/perimeter (half the finger width) about
            # 0.10 um. The buffer's decap MOMs sit over standard-cell decaps,
            # whose Metal1 is 21 pieces at 0.21 um and fills 43 %.
            mr = kdb.Region(m[0])

            def comb(gl):
                r = (metal[gl] & mr).merged()
                return (r.count() <= 4 and r.area() > 0.2 * mr.area()
                        and r.area() * ly.dbu < 0.15 * r.perimeter())
            stack = [k + 1 for k, gl in enumerate((8, 10, 30, 50)) if comb(gl)]
            if not stack:
                sys.exit(f"rc-netlist: MOM {d.expanded_name()} has no metal in its marker")
            mom_stack[d.expanded_name()] = (min(stack), max(stack))
            mom.append([m[0], nets, d.expanded_name(), 0.0,
                        d.parameter(dc.parameter_id("w")) * d.parameter(dc.parameter_id("l")),
                        min(stack), max(stack)])

    def own_mom(n1, p1, n2, p2):
        for m in mom:
            if {n1, n2} == m[1] and all(
                    m[0].bbox().contains(kdb.Point(round(p[0]), round(p[1])))
                    and m[0].inside(kdb.Point(round(p[0]), round(p[1]))) for p in (p1, p2)):
                return m
        return None

    if any(d.device_class().name == "cap_cmomf" for d, _ in placed) and len(mom_stack) != \
            sum(d.device_class().name == "cap_cmomf" for d, _ in placed):
        sys.exit("rc-netlist: a MOM with no marker, so no metal stack")
    write_devices()
    acc = defaultdict(float)
    for n1, l1, p1, n2, l2, p2, cf in rec["caps"]:
        m = own_mom(n1, p1, n2, p2) if mom else None
        if m:
            m[3] += cf
            continue
        a, b = near(n1, l1, p1), near(n2, l2, p2)
        if a is None or b is None or a == b:
            continue
        acc[(a, b) if a < b else (b, a)] += cf
    for i, ((a, b), cf) in enumerate(sorted(acc.items())):
        body.append(f"Cp{i} {spice_name(a)} {spice_name(b)} {cf * 1e-15:.6g}")

    # A conductor with capacitors and nothing else (floating metal, or a net
    # the extraction left without R) has no DC path, and the operating point
    # goes singular. 1 Tohm to vss gives it one and changes nothing at signal
    # frequencies; the count is reported.
    dc_nodes = set()
    for ln in body:
        w = ln.split()
        if w[0][0] in "XR":
            dc_nodes.update(t for t in (w[1:-1] if w[0][0] == "X" else w[1:3]) if "=" not in t)
    ports_ = {spice_name(pname[p.id()]) for p in circ.each_pin()} if not wires else \
        {spice_name(l) for l in labels}
    floating = sorted({t for ln in body if ln.startswith("Cp") for t in ln.split()[1:3]}
                      - dc_nodes - ports_)
    gname = spice_name(name(gnd))
    body += [f"Rfloat{k} {n} {gname} 1e12" for k, n in enumerate(floating)]
    # An idle piece: metal of a net with no device and no port on it. On the
    # substrate net that is a tie LVS joins through the substrate (the reg's
    # dummy-resistor ends); anywhere else it is metal cut off, and the check
    # fails on it. Either way it gets 1 Tohm, or the operating point is singular.
    live = {comp(n) for d, row in placed for n, _ in row if n in uf.p}
    live |= {comp(r) for r in port_of}
    idle = defaultdict(int)
    for net, (nodes, _) in rec["nodes"].items():
        seen = set()
        for nd in nodes.values():
            c_ = comp(nd["name"])
            if c_ in live or c_ in seen:
                continue
            seen.add(c_)
            idle[net] += 1
            body.append(f"Ridle{len(seen)}_{spice_name(net)} "
                        f"{spice_name(name(nd['name']))} {gname} 1e12")

    # for the checks: the LVS net of every written node (by its component),
    # and every sanitized name must stay unique
    node_net, node_base, conflicts, raw = {}, {}, [], {}
    for net, (nodes, _) in rec["nodes"].items():
        for nd in nodes.values():
            node_base[spice_name(name(nd["name"]))] = net
    node_base.update(written)
    for n in list(uf.p):
        o = name(n)
        so = spice_name(o)
        if raw.setdefault(so, o) != o:
            sys.exit(f"rc-netlist: {raw[so]} and {o} both write as {so}")
        es = comp_nets.get(comp(n), set())
        if len(es) > 1:
            conflicts.append((so, sorted(es)))
        node_net[so] = next(iter(es)) if len(es) == 1 else None
    devs = [dict(name=d.expanded_name(), cls=d.device_class().name,
                 params={pd.name: d.parameter(pd.id())
                         for pd in d.device_class().parameter_definitions()},
                 terms=DEVICES[d.device_class().name][1], nets=[e for _, e in row],
                 nodes=[spice_name(name(n)) for n, _ in row]) for d, row in placed]
    ports = sorted(labels) if wires else [pname[p.id()] for p in circ.each_pin()]
    with open(out, "w") as f:
        f.write(f"* {rec['cell']}: kpex 0.4.4 2.5D RC, rebuilt by kpex_cmos5l.py\n")
        f.write(f".subckt {rec['cell']} {' '.join(map(spice_name, ports))}\n")
        f.write("\n".join(body) + "\n.ends\n")
    dist.sort()
    info = dict(ports=ports, resistors=len(rlist), caps=len(acc),
                cap_records=len(rec["caps"]), unknown_cap_nets=dict(missing),
                cap_node_dist_um_p50=dist[len(dist) // 2] if dist else 0,
                cap_node_dist_um_p99=dist[int(len(dist) * 0.99)] if dist else 0,
                attached_by_position=attached, devices=devs,
                port_nets={spice_name(pname[p.id()]): eid(circ.net_for_pin(p))
                           for p in circ.each_pin()} if not wires else {},
                label_comp={lab: str(comp(ns[0])) for lab, ns in labels.items()},
                unconnected_pieces=sorted(
                    (net, len({comp(nd["name"]) for nd in nodes.values()} -
                              {comp(ns[0]) for ns in labels.values()} - set(comp_nets)))
                    for net, (nodes, _) in rec["nodes"].items()),
                node_net=node_net, node_base=node_base, substrate=rec["sub"],
                substrate_net=node_base.get(spice_name(name(gnd)), "vss"),
                label_networks={lab: sorted({net for net, (nodes, _) in rec["nodes"].items()
                                             for nd in nodes.values() if nd.get("label") == lab})
                                for lab in labels},
                joined_through_device=joined, network_pieces=pieces,
                floating_nodes=floating, idle_pieces=dict(idle), shorted_dummies=dummies,
                mom_dropped=[dict(device=m[2], nets=sorted(m[1]), dropped_fF=m[3],
                                  area_um2=m[4], mmin=m[5], mmax=m[6]) for m in mom],
                short_conflicts=conflicts)
    with open(os.path.splitext(out)[0] + ".json", "w") as f:
        json.dump(info, f)
    print(f"rc-netlist: {out} {len(devs)} devices, {len(rlist)} R, {len(acc)} C, "
          f"{len(attached)} terminals attached by position")


def main():
    a = sys.argv[1:]
    wires = "--wires" in a
    if wires:
        a.remove("--wires")
    if a[:1] == ["--rebuild"]:     # <pickle> <lvsdb> <out>: writer only, no kpex
        import pickle
        write_rc_netlist(pickle.load(open(a[1], "rb")), a[2], a[3], wires=wires)
        return
    if len(a) < 2:
        sys.exit(__doc__)
    top, tech = build_overlay(os.path.abspath(a.pop(0)))
    rc = None
    if a[0] == "--rc-netlist":
        a.pop(0)
        rc = os.path.abspath(a.pop(0))
    import klayout_pex.version as v
    if v.__version__ != "0.4.4":
        sys.exit(f"kpex_cmos5l: written against kpex 0.4.4, this is {v.__version__}")
    patch_crashes(top, tech)
    if rc:
        patch_recorders()
    if wires:                      # the labels the recorder turns into ports
        import klayout.db as kdb
        gly = kdb.Layout()
        gly.read(a[a.index("--gds") + 1])
        top_ = gly.cell(a[a.index("--cell") + 1])
        REC["labels"] = [(gly.get_info(li).layer, t.text.trans.disp.x,
                          t.text.trans.disp.y, t.text.string)
                         for li in gly.layer_indexes() if gly.get_info(li).datatype == 25
                         for t in top_.shapes(li).each(kdb.Shapes.STexts)]
    from klayout_pex.kpex_cli import KpexCLI
    KpexCLI().main(["kpex"] + a)
    if rc:
        import glob
        import pickle
        REC["gds"] = os.path.abspath(a[a.index("--gds") + 1])
        pk = os.path.splitext(rc)[0] + ".pkl"
        with open(pk, "wb") as f:
            pickle.dump(REC, f)
        out_dir = a[a.index("--out_dir") + 1]
        lvsdb = glob.glob(os.path.join(out_dir, f"*__{REC['cell']}", f"{REC['cell']}.lvsdb.gz"))
        write_rc_netlist(REC, lvsdb[0], rc, wires=wires)


if __name__ == "__main__":
    main()
