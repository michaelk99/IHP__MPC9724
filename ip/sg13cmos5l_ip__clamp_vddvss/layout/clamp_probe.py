# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# From OpenBLAU 8f25e634, ip/sg13cmos5l_ip__rfpad_70x70
# Description: connectivity probe for the clamp cell, the checks LVS cannot make
#
#   klayout -b -r clamp_probe.py [-rd gds=<file>]
#
# LVS compares devices. It merges the stripes of one block through their
# fingers, so a stripe cut off its band passes, and it drops iovss and iovdd,
# which carry no device. DRC reads two touching shapes of two nets as one
# polygon. So, on metal only:
#   1. every vdd stripe reaches the vdd Metal3 and Metal4 bands on its own
#      column, every vss stripe the vss Metal3 band
#   2. vdd, vss, iovss, iovdd, the clamp gate and the RC node are six nets
#   3. every band is solid and runs edge to edge, each iovss and iovdd band
#      one conductor on Metal3, Metal4 and TopMetal1
#   4. the rings, lanes, gate buses and the inverter are on their nets

import os
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rails import rails  # noqa: E402
import clamp             # noqa: E402

CELL = "sg13cmos5l_ip__clamp_vddvss"
W, H = clamp.W, 180.0
METAL = {"m1": (8, 0), "m2": (10, 0), "m3": (30, 0), "m4": (50, 0), "tm1": (126, 0),
         "v1": (19, 0), "v2": (29, 0), "v3": (49, 0), "tv1": (125, 0)}
STACK = (("m1", "v1", "m2"), ("m2", "v2", "m3"), ("m3", "v3", "m4"), ("m4", "tv1", "tm1"))


def flat(ly, top, clip=None):
    """{name: merged Region} of every metal and via, optionally clipped."""
    out = {}
    for n, (l, d) in METAL.items():
        r = pya.Region(top.begin_shapes_rec(ly.layer(l, d))).merged()
        out[n] = r & clip if clip is not None else r
    return out


class Net:
    """LayoutToNetlist over the regions of `flat`."""

    def __init__(self, regions, dbu, layers=None):
        ly = pya.Layout()
        ly.dbu = dbu
        top = ly.create_cell("probe")
        for n, r in regions.items():
            top.shapes(ly.layer(*METAL[n])).insert(r)
        self.ly = ly
        self.l2n = pya.LayoutToNetlist(pya.RecursiveShapeIterator(ly, top, []))
        self.L = {n: self.l2n.make_layer(ly.layer(*METAL[n]), n) for n in METAL}
        for lo, via, hi in STACK:
            if layers and not {lo, via, hi} <= set(layers):
                continue
            self.l2n.connect(self.L[lo])
            self.l2n.connect(self.L[hi])
            self.l2n.connect(self.L[lo], self.L[via])
            self.l2n.connect(self.L[via], self.L[hi])
        for n in METAL:
            self.l2n.connect(self.L[n])
        self.l2n.extract_netlist()

    def at(self, layer, x, y):
        n = self.l2n.probe_net(self.L[layer], pya.DPoint(x, y))
        return None if n is None else n.cluster_id


def main(gds):
    ly = pya.Layout()
    ly.read(gds)
    top = ly.cell(CELL)
    dbu = ly.dbu
    bands = rails()
    band = {(n, lay): (y0, y1) for n in bands for lay, y0, y1 in bands[n]}
    regs = flat(ly, top)
    full = Net(regs, dbu)
    bad = []

    def mid(net, lay):
        y0, y1 = band[(net, lay)]
        return (y0 + y1) / 2.0

    # the rails, probed where each band is solid
    rail = {"vss": full.at("m3", W / 2, 155.0), "vdd": full.at("m3", W / 2, mid("vdd", "Metal3")),
            "vdd_m4": full.at("m4", W / 2, 152.0), "vss_m4": full.at("m4", W / 2, mid("vss", "Metal4"))}
    for net in ("iovss", "iovdd"):
        for lay, y0, y1 in bands[net]:
            if lay == "Metal3":
                rail["%s %.1f" % (net, y0)] = full.at("m3", W / 2, (y0 + y1) / 2)
    gate = full.at("m2", 40.0, sum(clamp.GATE_LINE) / 2)
    rc = full.at("m2", 40.0, sum(clamp.RES_LINE) / 2)
    for k, v in rail.items():
        if v is None:
            bad.append("no metal on the %s band" % k)

    # 1. per stripe, on its own column: Metal2 and up, nothing else joins it
    for s0, s1, net in clamp.CL_STRIPES:
        for blk, t in clamp.BLOCKS.items():
            a, b = sorted((clamp.xmap(s0, t), clamp.xmap(s1, t)))
            col = pya.Region(pya.DBox(a, 0, b, H).to_itype(dbu))
            cn = Net(flat(ly, top, col), dbu, layers=("m2", "v2", "m3", "v3", "m4", "tv1", "tm1"))
            x = (a + b) / 2
            s = cn.at("m2", x, clamp.CL_Y0 + 2.0)
            m3 = cn.at("m3", x, mid(net, "Metal3") if net == "vdd" else 155.0)
            want = [("m3", m3)]
            if net == "vdd":
                want.append(("m4", cn.at("m4", x, 152.0)))
            for lay, n in want:
                if s is None or n is None or s != n:
                    bad.append("block %s %s stripe at x %.1f does not reach the %s %s band"
                               % (blk, net, x, net, lay))

    # 2. six nets
    nets = {"vss": rail["vss"], "vdd": rail["vdd"], "gate": gate, "clamp_rc": rc}
    for k in rail:
        if k.startswith("io"):
            nets[k] = rail[k]
    if len(set(nets.values())) != len(nets) or None in nets.values():
        bad.append("nets shorted or missing: %s" % nets)
    if rail["vdd_m4"] != rail["vdd"]:
        bad.append("the vdd Metal3 and Metal4 bands are not one net")
    if rail["vss_m4"] in (rail["vdd"], gate, rc):
        bad.append("the vss Metal4 band is shorted")

    # 3. every band solid and edge to edge, iovss and iovdd one conductor each
    holes = pya.Region()
    for s0, s1, net in clamp.CL_STRIPES:
        if net == "vdd":
            for t in clamp.BLOCKS.values():
                a, b = sorted((clamp.xmap(s0, t), clamp.xmap(s1, t)))
                holes.insert(pya.DBox(a - clamp.ISLAND_KEEP, clamp.ISLAND_Y[0],
                                      b + clamp.ISLAND_KEEP,
                                      clamp.ISLAND_Y[1] + clamp.ISLAND_KEEP).to_itype(dbu))
    lname = {"Metal3": "m3", "Metal4": "m4", "TopMetal1": "tm1"}
    for net in bands:
        for lay, y0, y1 in bands[net]:
            want = pya.Region(pya.DBox(0, y0, W, y1).to_itype(dbu))
            if (net, lay) == ("vss", "Metal3"):
                want -= holes
            got = regs[lname[lay]] & pya.Region(pya.DBox(0, y0, W, y1).to_itype(dbu))
            if not (want - got).is_empty():
                bad.append("%s %s band at y %.1f has a gap at %s"
                           % (net, lay, y0, (want - got).bbox().to_dtype(dbu)))
            # the vdd islands sit inside the holes and are not part of the band
            pieces = (got - holes).merged().count() if (net, lay) == ("vss", "Metal3") \
                else got.merged().count()
            if pieces != 1:
                bad.append("%s %s band at y %.1f is %d pieces" % (net, lay, y0, pieces))
            yc = (y0 + y1) / 2 if (net, lay) != ("vss", "Metal3") else 155.0
            ends = {full.at(lname[lay], 0.05, yc), full.at(lname[lay], W - 0.05, yc)}
            if len(ends) != 1 or None in ends:
                bad.append("%s %s band at y %.1f: the two cell edges are not one net"
                           % (net, lay, y0))
            if net.startswith("io"):
                ids = {full.at(n, x, yc) for n in ("m3", "m4", "tm1") for x in (0.05, W - 0.05)}
                if len(ids) != 1:
                    bad.append("%s band at y %.1f is %d nets over Metal3, Metal4, TopMetal1"
                               % (net, y0, len(ids)))

    # 4. rings, lanes, gate buses, inverter
    yc = (clamp.CL_Y0 + 120.0) / 2
    want = {"left lane": (("m2", 2.5, 100.0), rail["vss"]),
            "right lane": (("m2", W - 2.5, 100.0), rail["vss"]),
            "inverter output": (("m2", sum(clamp.OUT_STRIPE) / 2, 30.0), gate),
            "inverter gate bus": (("m2", clamp.INV_GATE_X, 30.0), rc),
            "capacitor gate bus": (("m2", clamp.CAP[0]["gate_x"], 40.0), rc)}
    for blk, t in clamp.BLOCKS.items():
        want["block %s ring" % blk] = (("m1", clamp.xmap(clamp.CL_COLS[1][1] + 1.4, t), yc),
                                       rail["vss"])
        want["block %s gate bus" % blk] = (("m2", clamp.xmap(clamp.CL_GATE_X, t), yc), gate)
    for what, ((lay, x, y), net) in want.items():
        got = full.at(lay, x, y)
        if got is None or got != net:
            bad.append("the %s at (%.1f, %.1f) is not on its net" % (what, x, y))

    for b in bad:
        print("FAIL " + b)
    if bad:
        print("clamp_probe: %d problem(s)" % len(bad))
        return 1
    print("clamp_probe: ok, 24 stripes on their bands, 6 nets, %d bands edge to edge"
          % sum(len(v) for v in bands.values()))
    return 0


if __name__ == "__main__":
    path = globals().get("gds") or os.path.join(HERE, "..", "gds", CELL + ".gds")
    try:
        rc_ = main(path)
    except BaseException:
        import traceback
        traceback.print_exc()
        rc_ = 1
    sys.exit(rc_)
