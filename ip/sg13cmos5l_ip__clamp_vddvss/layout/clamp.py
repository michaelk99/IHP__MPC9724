# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# From OpenBLAU 8f25e634, ip/sg13cmos5l_ip__rfpad_70x70
# Description: the RC-triggered vdd-to-vss supply clamp, drawn by clamp_gen.py
"""IHP's IOPadVdd clamp with its source on vss, the clamp NMOS three of IHP's
756 um blocks. FEOL, Metal1 and Metal2 only, under the IO bands (y 0 is the
outer edge, as in the IO library):

  resistor    rppd, 25 x (1 x 20 um), vdd to clamp_rc
  capacitor   14 x hv_nmos 9.5 / 9, clamp_rc to vss
  inverter    hv_nmos 108 / 0.5, hv_pmos 350 / 0.5, clamp_rc to clamp_g
  clamp       hv_nmos 2268 / 0.6, vdd to vss, blocks A, B, C

    y  62.9..129.6  clamp blocks: A x 3.9..27.4, B its mirror about x 40,
                    C its mirror about x 60
    y  67.1..114.7  resistor, x 28.5..51.1, between A and B
    y  11.3..57.7   capacitor x 4.8..50.8, inverter x 94.9..114.2 under C

Every MOS has horizontal gates, fingers stacked in y, and one or two activ
columns in x. `Mos` describes them all.
"""

import pya

W = 120.0
GRID = 0.005

# Block placement as x -> off + sgn * x: A as drawn, B and C mirrored.
A = ((0.0, 1),)
BLOCKS = {"A": (0.0, 1), "B": (80.0, -1), "C": (120.0, -1)}
EDGES = ((0.0, 1), (W, -1))   # the two vss lanes


def snap(v):
    return round(round(v / GRID) * GRID, 3)


def xmap(x, xf):
    return xf[0] + xf[1] * x


# vss lane down each cell edge, Metal1 and Metal2, 1 um inside the edge: it
# taps the rings that touch it and carries vss down to the trigger.
LANE_M1 = (1.0, 4.8)
LANE_M2 = (1.0, 4.0)

CONT, CONT_PITCH = 0.16, 0.34
V1, V1_PITCH = 0.19, 0.48  # Vn.b1: 0.29 beyond 3 cuts
RING_GAP, RING_W = 0.70, 0.80
TGO_X, TGO_Y = 0.30, 0.34  # beyond poly in x, TGO.c beyond the gate in y
TGO_RING = 0.30            # TGO.b is 0.27
PSD_X = 0.45               # pSD past a p+ gate's end, pSD.i1 0.40

# ---- the clamp NMOS: IHP's own finger, L 0.6, source 0.64 with Metal1 0.21,
# drain 1.18 with Metal1 0.62, end source 0.47. Two 9 um activ columns (the
# 10 um finger limit), gates contacted between them.
CL_COLS = ((5.8, 14.8), (16.6, 25.6))
CL_GATE_X = 15.7
CL_Y0 = 64.4
CL_GATES = 42              # 2 x 42 x 9 = 756 um per block, IHP's is 757
# Metal2 over the fingers, alternating, each running straight up: vss ends in
# the vss Metal3 band (140..158), vdd passes under it into the vdd Metal3 band
# (160..178) and reaches the vdd Metal4 band (140..155.8) through a Metal3
# island cut out of the vss band.
CL_STRIPES = ((5.8, 7.4, "vss"), (8.2, 9.8, "vdd"), (10.6, 12.2, "vss"),
              (13.0, 14.6, "vdd"), (16.8, 18.4, "vss"), (19.2, 20.8, "vdd"),
              (21.6, 23.2, "vss"), (24.0, 25.6, "vdd"))
STRIPE_TOP = {"vss": 158.0, "vdd": 178.0}
ISLAND_Y = (140.0, 148.0)  # leaves the vss band 9.4 um whole above the holes
ISLAND_KEEP = 0.60         # Mn.f, the band is wider than 10 um
GATE_BUS = 0.50
GATE_LINE = (59.0, 60.0)   # Metal2: the three gate buses and the inverter output

# ---- the trigger
TR_Y0 = 11.3               # ring bottom, Pad.d1R: Activ 11.2 um from a bondpad
RES_LINE = (56.0, 57.0)    # Metal2, clamp_rc: capacitor, inverter, resistor
# capacitor: two blocks, 4 and 3 gates of L 9.5 over two 9 um columns
CAP = ({"cols": ((6.6, 15.6), (17.4, 26.4)), "gate_x": 16.5, "gates": 4},
       {"cols": ((29.2, 38.2), (40.0, 49.0)), "gate_x": 39.1, "gates": 3})
CAP_L = 9.5
# inverter under block C: gates contacted at the left end, one Metal2 bus for
# both devices, S/D Metal1 continuous across both columns
INV_GATE_X = 96.8
INV_NMOS = {"cols": ((97.65, 104.4), (105.2, 111.95)), "gates": 8}     # 16 x 6.75
INV_PMOS = {"cols": ((97.4, 104.4), (105.2, 112.2)), "gates": 25}      # 50 x 7
INV_L = 0.5
OUT_STRIPE = (106.2, 107.8)
VSS_STRIPE = (109.9, 111.5)
VDD_STRIPE = (110.2, 111.8)  # block C's outer vdd stripe, run down
NW_TIE = 0.24              # NW.e
NW_SPACE = 1.00            # to the NMOS ring below
# resistor: rppd 1 x 20 um, 13 + 12 in series, pitch 1.8 (EXTB.b 0.31)
RES_X0, RES_PITCH = 28.5, 1.8
RES_Y = (67.5, 94.3)       # body bottoms of the two tiers
RES_N = (13, 12)
RES_L = 20.0
RES_HEAD = (-0.43, -0.13)  # the PCell's Metal1 head below the body, the one
#                            above is body top + (0.13, 0.43)


class Mos:
    """One MOS: activ columns, horizontal gates, S/D strips.

    `sd` alternates nets from the bottom, starting with sd[0]. Regions are
    `sd_w` wide (`drain_w` per net overrides) and the two end ones `sd_end`.
    Each gate is contacted at `gate_x`, between the columns or left of them.
    `m1` gives per net the S/D Metal1 width and its contact rows, `m1_ext`
    per column the x extent of the S/D Metal1.
    """

    def __init__(self, cols, y0, gates, L, sd, sd_w=0.64, sd_end=0.47,
                 m1=None, drain_w=None, pmos=False, poly_x=None, gate_x=None,
                 m1_ext=None):
        self.cols, self.y0, self.gates, self.L = cols, y0, gates, L
        self.sd, self.sd_w, self.sd_end = sd, sd_w, sd_end
        self.m1 = m1 or {}
        self.pmos = pmos
        self.gate_x = gate_x
        self.poly_x = poly_x or (cols[0][0] - 0.4, cols[-1][1] + 0.4)
        self.m1_ext = m1_ext or [(c0 + 0.05, c1 - 0.05) for c0, c1 in cols]
        self.regions, self.gate_ys = [], []
        y = y0
        for i in range(gates + 1):
            net = sd[i % 2]
            w = sd_end if i in (0, gates) else (drain_w or {}).get(net, sd_w)
            self.regions.append((net, snap(y), snap(y + w), i))
            y += w
            if i < gates:
                self.gate_ys.append((snap(y), snap(y + L)))
                y += L
        self.y1 = snap(y)

    def tgo(self):
        return (self.poly_x[0] - TGO_X, self.y0 - TGO_Y,
                self.poly_x[1] + TGO_X, self.y1 + TGO_Y)


class Clamp:
    """Draws into clamp_gen.Gen `g`. `m2[net]` collects each net's Metal2 so
    the supply strips can keep off it."""

    def __init__(self, g):
        self.g = g
        self.dbu = g.ly.dbu
        self.m2 = {}
        self.counts = {}

    # primitives
    def rect(self, layer, x0, y0, x1, y1, net=None, xf=A):
        for t in xf:
            a, b = sorted((xmap(x0, t), xmap(x1, t)))
            box = pya.DBox(snap(a), snap(y0), snap(b), snap(y1))
            self.g.box(layer, box.left, box.bottom, box.right, box.top)
            if layer == "Metal2":
                if net is None:
                    raise AssertionError("Metal2 without a net at %s" % box)
                self.m2.setdefault(net, pya.Region()).insert(box.to_itype(self.dbu))

    def cut(self, layer, cx, cy, size, xf=A):
        a = size / 2.0
        self.rect(layer, cx - a, cy - a, cx + a, cy + a, xf=xf)

    def count(self, key, n=1):
        self.counts[key] = self.counts.get(key, 0) + n

    def cut_row(self, layer, x0, cy, n, pitch, size, xf=A, vertical=False):
        """n cuts from centre (x0, cy) on `pitch`, along x (or y), as one
        array reference of a one-cut cell per placement."""
        if n <= 0:
            return
        name = "%s_%s" % (self.g.top.name, layer.lower())
        ly = self.g.ly
        if ly.has_cell(name):
            cell = ly.cell(name)
        else:
            cell = ly.create_cell(name)
            h = int(round(size / 2.0 / self.dbu))
            cell.shapes(self.g.lay(layer)).insert(pya.Box(-h, -h, h, h))
        step = pya.Vector(0, int(round(pitch / self.dbu))) if vertical else \
            pya.Vector(int(round(pitch / self.dbu)), 0)
        for t in xf:
            x = xmap(x0, t)
            if t[1] < 0 and not vertical:
                x -= (n - 1) * pitch
            org = pya.Vector(int(round(snap(x) / self.dbu)), int(round(snap(cy) / self.dbu)))
            self.g.top.insert(pya.CellInstArray(cell.cell_index(), pya.Trans(org),
                                                step, pya.Vector(0, 0), n, 1))

    def via_row(self, x0, x1, cy, key, xf=A):
        """Via1 along y = cy wherever a cut fits 0.155 inside x0..x1."""
        n = int((x1 - 0.155 - V1 / 2.0 - (x0 + 0.25)) / V1_PITCH + 1e-9) + 1
        self.cut_row("Via1", x0 + 0.25, cy, n, V1_PITCH, V1, xf)
        self.count(key, n * len(xf))

    def ring(self, inner, ptype, xf=A, skip=()):
        """A tap ring RING_W wide around `inner` (x0, y0, x1, y1): p+ on the
        substrate (vss) or n+ in the well (vdd). `skip` names sides not drawn
        ('l', 'r', 'b', 't'), where another ring already has one."""
        x0, y0, x1, y1 = inner
        o = (x0 - RING_W, y0 - RING_W, x1 + RING_W, y1 + RING_W)
        sides = {"b": (o[0], o[1], o[2], y0), "t": (o[0], y1, o[2], o[3]),
                 "l": (o[0], y0, x0, y1), "r": (x1, y0, o[2], y1)}
        for key, (a, b, c, d) in sides.items():
            if key in skip:
                continue
            self.rect("Activ", a, b, c, d, xf=xf)
            self.rect("Metal1", a, b, c, d, xf=xf)
            if ptype:
                self.rect("Substrate", a, b, c, d, xf=xf)
                self.rect("pSD", a - 0.03, b - 0.03, c + 0.03, d + 0.03, xf=xf)
            horiz = (c - a) > (d - b)
            lo, hi = (a, c) if horiz else (b, d)
            if horiz and "l" in skip:   # the other ring's corner has contacts
                lo += RING_W
            mid = ((b + d) if horiz else (a + c)) / 2.0
            n = int((hi - 0.30 - (lo + 0.30)) / 0.50 + 1e-9) + 1
            if horiz:
                self.cut_row("Cont", lo + 0.30, mid, n, 0.50, CONT, xf)
            else:
                self.cut_row("Cont", mid, lo + 0.30, n, 0.50, CONT, xf, vertical=True)
            self.count("Cont ring", n * len(xf))
        return o

    def mos(self, m, stripes, gate_via=True, xf=A, tag=""):
        """Draw Mos `m`, Via1 from each S/D strip to every stripe of its net."""
        for c0, c1 in m.cols:
            self.rect("Activ", c0, m.y0, c1, m.y1, xf=xf)
        if m.pmos:              # one pSD over both columns, pSD.i1 wants 0.40
            self.rect("pSD", m.cols[0][0] - PSD_X, m.y0 - 0.30,
                      m.cols[-1][1] + PSD_X, m.y1 + 0.30, xf=xf)
        self.rect("ThickGateOx", *m.tgo(), xf=xf)
        for a, b in m.gate_ys:
            self.rect("GatPoly", m.poly_x[0], a, m.poly_x[1], b, xf=xf)
            self.gate_contact(m.gate_x, a, b, gate_via, xf, tag)
        for net, a, b, i in m.regions:
            mw, rows = m.m1.get(net, (0.21, (0.0,)))
            # the contact keeps half a region from the gate(s) it faces
            if i == 0:
                cy = b - m.sd_w / 2.0
            elif i == m.gates:
                cy = a + m.sd_w / 2.0
            else:
                cy = (a + b) / 2.0
            for (c0, c1), (e0, e1) in zip(m.cols, m.m1_ext):
                self.rect("Metal1", e0, cy - mw / 2.0, e1, cy + mw / 2.0, xf=xf)
                n = int((c1 - 0.20 - (c0 + 0.20)) / CONT_PITCH + 1e-9) + 1
                for dy in rows:
                    self.cut_row("Cont", c0 + 0.20, cy + dy, n, CONT_PITCH, CONT, xf)
                    self.count("Cont " + tag, n * len(xf))
            for s0, s1, n in stripes:
                if n == net:
                    self.via_row(s0, s1, cy, "Via1 %s %s" % (tag, net), xf)

    def gate_contact(self, x, a, b, via, xf, tag):
        """Contacts down the gate at x (a column of them on a long gate), a
        Metal1 pad, and a Via1 at its centre."""
        cy = (a + b) / 2.0
        n = max(1, int(((b - a) - 0.30) / CONT_PITCH) + 1)
        y = cy - (n - 1) * CONT_PITCH / 2.0
        for _ in range(n):
            self.cut("Cont", x, y, CONT, xf)
            y += CONT_PITCH
        pad = 0.25 if (b - a) < 1.0 else (b - a) / 2.0 - 0.05
        self.rect("Metal1", x - 0.20, cy - pad, x + 0.20, cy + pad, xf=xf)
        if via:
            self.cut("Via1", x, cy, V1, xf)
            self.count("Via1 gate " + tag, len(xf))

    # the clamp blocks
    def clamp(self):
        m = Mos(CL_COLS, CL_Y0, CL_GATES, 0.6, ("vss", "vdd"),
                drain_w={"vdd": 1.18}, m1={"vdd": (0.62, (-0.17, 0.17))},
                gate_x=CL_GATE_X)
        self.cl = m
        xf = tuple(BLOCKS.values())
        self.mos(m, CL_STRIPES, xf=xf, tag="clamp")
        t = m.tgo()
        self.cl_ring = self.ring((t[0] - 0.40, m.y0 - RING_GAP, t[2] + TGO_RING,
                                  m.y1 + RING_GAP), True, xf=xf)
        r = self.cl_ring
        for s0, s1, net in CL_STRIPES:
            # vss stripes start on the ring's bottom side and tap it there and
            # on its top side: block B's ring touches no lane
            y0 = r[1] if net == "vss" else m.y0
            self.rect("Metal2", s0, y0, s1, STRIPE_TOP[net], net=net, xf=xf)
            if net == "vss":
                for yc in (r[1] + RING_W / 2.0, r[3] - RING_W / 2.0):
                    self.via_row(s0, s1, yc, "Via1 ring vss", xf)
        g0, g1 = CL_GATE_X - GATE_BUS / 2.0, CL_GATE_X + GATE_BUS / 2.0
        self.rect("Metal2", g0, GATE_LINE[0], g1, m.gate_ys[-1][1], net="gate", xf=xf)
        self.rect("Metal2", g0, GATE_LINE[0], OUT_STRIPE[1], GATE_LINE[1], net="gate")

    def islands(self):
        """Record the Metal3 holes BEFORE clamp_gen.io_rails draws the band."""
        self.isl = []
        for s0, s1, net in CL_STRIPES:
            if net != "vdd":
                continue
            for t in BLOCKS.values():
                a, b = sorted((xmap(s0, t), xmap(s1, t)))
                self.isl.append(pya.DBox(a, ISLAND_Y[0], b, ISLAND_Y[1]))
                self.g.m3_holes.append(pya.DBox(
                    a - ISLAND_KEEP, ISLAND_Y[0], b + ISLAND_KEEP,
                    ISLAND_Y[1] + ISLAND_KEEP))
        return self

    def island_vias(self):
        R = lambda b: pya.Region(b.to_itype(self.dbu))  # noqa: E731
        for isl in self.isl:
            self.g.box("Metal3", isl.left, isl.bottom, isl.right, isl.top)
            self.count("Via2 island", self.g._fill_vias("Via2", R(isl)))
            self.count("Via3 island", self.g._fill_vias("Via3", R(isl)))

    def lanes(self):
        lane_y = (TR_Y0, STRIPE_TOP["vss"])
        self.rect("Metal1", LANE_M1[0], lane_y[0], LANE_M1[1], lane_y[1], xf=EDGES)
        self.rect("Metal2", LANE_M2[0], lane_y[0], LANE_M2[1], lane_y[1], net="vss",
                  xf=EDGES)
        core = pya.Region()
        for t in EDGES:
            a, b = sorted((xmap(LANE_M2[0], t), xmap(LANE_M2[1], t)))
            core.insert(pya.DBox(a, lane_y[0], b, lane_y[1]).to_itype(self.dbu))
        e = int(round((V1 / 2.0 + 0.06) / self.dbu))
        self.counts["Via1 lane"] = self.g._lattice("Via1", core.sized(-e))

    # the trigger
    def capacitor(self):
        """hv_nmos, gate clamp_rc, source, drain and bulk vss. Its S/D Metal1
        runs out to the rings: the capacitor carries no current."""
        y0 = TR_Y0 + RING_W + RING_GAP
        self.caps = []
        for k, c in enumerate(CAP):
            (a0, a1), (b0, b1) = c["cols"]
            m = Mos(c["cols"], y0, c["gates"], CAP_L, ("vss", "vss"), sd_end=0.64,
                    gate_x=c["gate_x"],
                    m1_ext=((a0 - 1.2, a1 - 0.05), (b0 + 0.05, b1 + 1.2)))
            self.caps.append(m)
            self.mos(m, (), gate_via=False, tag="cap")
            t = m.tgo()
            inner = (t[0] - TGO_RING, TR_Y0 + RING_W, t[2] + TGO_RING, m.y1 + RING_GAP)
            self.ring(inner, True, skip=("l",) if k else ())
            gx = c["gate_x"]
            self.rect("Metal2", gx - GATE_BUS / 2.0, m.gate_ys[0][0], gx + GATE_BUS / 2.0,
                      RES_LINE[1], net="clamp_rc")
            for a, b in m.gate_ys:          # a column of Via1 on each long gate
                y = a + 0.40
                while y <= b - 0.40 + 1e-9:
                    self.cut("Via1", gx, y, V1)
                    self.count("Via1 gate cap")
                    y += V1_PITCH
        self.rect("Metal2", CAP[0]["gate_x"] - GATE_BUS / 2.0, RES_LINE[0],
                  INV_GATE_X + GATE_BUS / 2.0, RES_LINE[1], net="clamp_rc")

    def inverter(self):
        def dev(spec, y, sd, pmos):
            (c0, c1), (d0, d1) = spec["cols"]
            return Mos(spec["cols"], y, spec["gates"], INV_L, sd, sd_end=0.64,
                       pmos=pmos, gate_x=INV_GATE_X,
                       poly_x=(INV_GATE_X - 0.30, d1 + 0.4),
                       m1_ext=((c0 + 0.05, d1 - 0.05), (d0, d1 - 0.05)))

        n = dev(INV_NMOS, TR_Y0 + RING_W + RING_GAP, ("vss", "gate"), False)
        self.mos(n, ((OUT_STRIPE[0], OUT_STRIPE[1], "gate"),
                     (VSS_STRIPE[0], VSS_STRIPE[1], "vss")), tag="inv")
        t = n.tgo()
        n_ring = self.ring((t[0] - TGO_RING, TR_Y0 + RING_W, t[2] + TGO_RING,
                            n.y1 + RING_GAP), True)
        # the PMOS in its own well, NW_SPACE above the NMOS ring
        py = n_ring[3] + NW_SPACE + NW_TIE + RING_W + RING_GAP
        p = dev(INV_PMOS, py, ("vdd", "gate"), True)
        self.mos(p, ((OUT_STRIPE[0], OUT_STRIPE[1], "gate"),
                     (VDD_STRIPE[0], VDD_STRIPE[1], "vdd")), tag="inv")
        t = p.tgo()
        p_ring = self.ring((t[0] - TGO_RING, py - RING_GAP, t[2] + TGO_RING,
                            p.y1 + RING_GAP), False)
        self.rect("NWell", p_ring[0] - NW_TIE, p_ring[1] - NW_TIE,
                  p_ring[2] + NW_TIE, p_ring[3] + NW_TIE)
        if p_ring[3] + NW_TIE > GATE_LINE[0]:
            raise AssertionError("the inverter reaches the gate line")
        self.inv = (n, p)
        # Metal2: the shared gate bus, the output, the supplies and ring taps
        self.rect("Metal2", INV_GATE_X - GATE_BUS / 2.0, n.gate_ys[0][0],
                  INV_GATE_X + GATE_BUS / 2.0, RES_LINE[1], net="clamp_rc")
        self.rect("Metal2", OUT_STRIPE[0], n.y0, OUT_STRIPE[1], GATE_LINE[1], net="gate")
        self.rect("Metal2", VSS_STRIPE[0], TR_Y0, VSS_STRIPE[1], n.y1, net="vss")
        self.rect("Metal2", VSS_STRIPE[0], TR_Y0, W - LANE_M2[1], TR_Y0 + RING_W,
                  net="vss")
        self.via_row(VSS_STRIPE[0], VSS_STRIPE[1], TR_Y0 + RING_W / 2.0, "Via1 ring")
        self.rect("Metal2", VDD_STRIPE[0], p_ring[1], VDD_STRIPE[1], CL_Y0, net="vdd")
        for yc in (p_ring[1] + RING_W / 2.0, p_ring[3] - RING_W / 2.0):
            self.via_row(VDD_STRIPE[0], VDD_STRIPE[1], yc, "Via1 ring")

    def resistor(self):
        """25 rppd in series, vdd at the upper tier's left end, clamp_rc at the
        lower tier's left end: a serpentine closed by Metal1 bars on the heads."""
        var = self.g._variant("rppd", {"w": "1u", "l": "%gu" % RES_L})
        xs1 = [RES_X0 + k * RES_PITCH for k in range(RES_N[0])]
        xs2 = [xs1[-1] - j * RES_PITCH for j in range(RES_N[1])]
        insts = []
        for xs, y0 in ((xs1, RES_Y[0]), (xs2, RES_Y[1])):
            for x in xs:
                insts.append(self.g.top.insert(pya.DCellInstArray(
                    var, pya.DTrans(pya.DVector(x, y0)))))
        for i in insts:
            i.flatten()
        # one SalBlock, EXTBlock and pSD per tier: per strip they sit 0.40
        # apart, under Sal.b
        for xs, y0 in ((xs1, RES_Y[0]), (xs2, RES_Y[1])):
            x0, x1 = min(xs), max(xs) + 1.0
            self.rect("SalBlock", x0 - 0.2, y0, x1 + 0.2, y0 + RES_L)
            self.rect("EXTBlock", x0 - 0.2, y0 - 0.61, x1 + 0.2, y0 + RES_L + 0.61)
            self.rect("pSD", x0 - 0.18, y0 - 0.61, x1 + 0.18, y0 + RES_L + 0.61)
        self.g.top.shapes(self.g.ly.layer(8, 2)).clear()   # the PCell's pins
        self.g.top.shapes(self.g.ly.layer(63, 0)).clear()  # and its labels

        def head(x, y0, top):
            h0, h1 = (RES_L + 0.13, RES_L + 0.43) if top else RES_HEAD
            return (x + 0.02, y0 + h0, x + 0.98, y0 + h1)

        def bar(x_a, x_b, y0, top):
            a, b = head(x_a, y0, top), head(x_b, y0, top)
            self.rect("Metal1", min(a[0], b[0]), a[1], max(a[2], b[2]), a[3])

        # lower tier: current enters strip 12 at the top and leaves strip 0 at
        # the bottom, upper tier: enters strip 11 (the leftmost) at the bottom
        for k in range(RES_N[0] - 1, 0, -1):
            bar(xs1[k], xs1[k - 1], RES_Y[0], top=(RES_N[0] - 1 - k) % 2 == 1)
        for j in range(RES_N[1] - 1, 0, -1):
            bar(xs2[j], xs2[j - 1], RES_Y[1], top=(RES_N[1] - 1 - j) % 2 == 0)
        # the tiers meet on the right: upper strip 0 bottom to lower strip 12 top
        lo, hi = head(xs1[-1], RES_Y[0], True), head(xs2[0], RES_Y[1], False)
        self.rect("Metal1", lo[0], lo[1], lo[2], hi[3])
        # vdd: a Metal2 jog from block A's inner vdd stripe
        h = head(xs2[-1], RES_Y[1], False)
        cy = (h[1] + h[3]) / 2.0
        self.rect("Metal2", CL_STRIPES[-1][0], cy - 0.30, h[2], cy + 0.30, net="vdd")
        self.via_row(h[0] - 0.10, h[2] + 0.10, cy, "Via1 res")
        # clamp_rc: Metal1 down from the lower tier's first head, under the
        # gate line, onto the clamp_rc line
        h = head(xs1[0], RES_Y[0], False)
        self.rect("Metal1", h[0], RES_LINE[0], h[2], h[3])
        self.via_row(h[0] - 0.10, h[2] + 0.10, (RES_LINE[0] + RES_LINE[1]) / 2.0,
                     "Via1 res")

    def build(self):
        self.lanes()
        self.clamp()
        self.island_vias()
        self.capacitor()
        self.inverter()
        self.resistor()
        return self
