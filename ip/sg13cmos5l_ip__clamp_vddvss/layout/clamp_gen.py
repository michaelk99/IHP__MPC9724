# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# From OpenBLAU 8f25e634, ip/sg13cmos5l_ip__rfpad_70x70
# Description: KLayout generator for sg13cmos5l_ip__clamp_vddvss, writes its GDS and LEF
#
#   klayout -n sg13cmos5l -zz -r clamp_gen.py [-rd variant=<mutant>]
#
# A 120 x 180 um IO ring cell without a bondpad. y 0 is the outer edge, as in
# the IO library. The four ring bands run straight across, as in the PDK's
# IO fillers, and the clamp (clamp.py) sits under them on FEOL, Metal1 and
# Metal2. `variant` draws a deliberately broken cell for the checks' negative
# controls, into the scratch path given by -rd out=.

import os
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))
from gdswrite import write_gds       # noqa: E402
sys.path.insert(0, HERE)
from rails import rails              # noqa: E402
import clamp                          # noqa: E402

CELL = "sg13cmos5l_ip__clamp_vddvss"
W, H = clamp.W, 180.0
GDS = os.path.join(HERE, "..", "gds", CELL + ".gds")
LEF = os.path.join(HERE, "..", "lef", CELL + ".lef")
INSET = 1.0               # Metal1 and Metal2 keep this far inside the cell
VIA = {"Via1": 0.19, "Via2": 0.19, "Via3": 0.19, "TopVia1": 0.42}
# Vn.b1: 0.29 beyond 3 cuts, so an array pitches at 0.48. TV1.d wants 0.42 of
# TopMetal1 around a TopVia1, TV1.c 0.10 of Metal4.
ENC = {"Via1": 0.06, "Via2": 0.06, "Via3": 0.06, "TopVia1": 0.42}
PITCH = {"Via1": 0.48, "Via2": 0.48, "Via3": 0.48, "TopVia1": 0.84}
TV1_M4_ENC = 0.10
STRIP_KEEP = 0.80         # supply strip to Metal2 of another net, Mn.f is 0.6
STRIP_MIN = 2.0           # a strip piece narrower than this is dropped
VIA_FLOOR = 200           # per stripe set: OpenBLAU's generator floor

LAYERS = {
    "Metal1": (8, 0), "Metal2": (10, 0), "Metal3": (30, 0), "Metal4": (50, 0),
    "TopMetal1": (126, 0), "Via1": (19, 0), "Via2": (29, 0), "Via3": (49, 0),
    "TopVia1": (125, 0), "prBoundary": (189, 4),
    "Activ": (1, 0), "GatPoly": (5, 0), "Cont": (6, 0), "pSD": (14, 0),
    "NWell": (31, 0), "Substrate": (40, 0), "ThickGateOx": (44, 0),
    "SalBlock": (28, 0), "EXTBlock": (111, 0),
    # LVS reads labels from datatype 25, the LEF and the IO cells' pins are on 2
    "Metal3.text": (30, 25), "Metal4.text": (50, 25), "TopMetal1.text": (126, 25),
    "Metal3.pin": (30, 2), "Metal4.pin": (50, 2), "TopMetal1.pin": (126, 2),
}
# the band each net is labelled on: one per net, the others are separate
# conductors inside an IO cell and meet in the ring
LABEL = {"iovss": ("Metal3", 7.0), "iovdd": ("Metal3", 66.0),
         "vss": ("Metal3", 140.0), "vdd": ("Metal3", 160.0)}


class Gen:
    def __init__(self, variant=""):
        self.variant = variant
        self.ly = pya.Layout(True)
        self.ly.dbu = 0.001
        self.top = self.ly.cell(self.ly.add_cell(CELL))
        self.m3_holes = []
        self.bands = rails()

    def lay(self, name):
        return self.ly.layer(*LAYERS[name])

    def box(self, name, x0, y0, x1, y1):
        self.top.shapes(self.lay(name)).insert(pya.DBox(x0, y0, x1, y1))

    def _variant(self, name, params):
        lib = pya.Library.library_by_name("SG13_dev", "sg13cmos5l")
        ids = {lib.layout().pcell_declaration(i).name(): i
               for i in lib.layout().pcell_ids()}
        return self.ly.add_pcell_variant(lib, ids[name], params)

    def _cut(self, name, cx, cy):
        a = VIA[name] / 2.0
        self.box(name, cx - a, cy - a, cx + a, cy + a)

    def _fill_vias(self, name, area, pitch=None, enc=None):
        """Cuts on a `pitch` grid wherever the cut plus its enclosure lies
        wholly inside `area`."""
        pitch = pitch or PITCH[name]
        a = VIA[name] / 2.0 + (ENC[name] if enc is None else enc)
        bb = area.bbox()
        n = 0
        y = bb.bottom * self.ly.dbu + a
        while y < bb.top * self.ly.dbu - a:
            x = bb.left * self.ly.dbu + a
            while x < bb.right * self.ly.dbu - a:
                probe = pya.Region(pya.DBox(x - a, y - a, x + a,
                                            y + a).to_itype(self.ly.dbu))
                if (probe - area).is_empty():
                    self._cut(name, x, y)
                    n += 1
                x += pitch
            y += pitch
        return n

    def _lattice(self, name, core):
        """Cuts of `name` on one PITCH lattice for the whole cell wherever the
        centre lies in `core`, a Manhattan region already shrunk by half a cut
        plus enclosure. Array references of a one-cut cell, one per rectangle
        of `core`. A row on an edge two rectangles share goes to the upper one."""
        p = int(round(PITCH[name] * 1000))
        off = p // 2
        cname = "%s_%s" % (CELL, name.lower())
        if self.ly.has_cell(cname):
            cell = self.ly.cell(cname)
        else:
            cell = self.ly.create_cell(cname)
            h = int(round(VIA[name] * 500))
            cell.shapes(self.lay(name)).insert(pya.Box(-h, -h, h, h))
        boxes = [t.bbox() for t in core.decompose_trapezoids_to_region().each()]
        starts = {(bx.bottom, bx.left, bx.right) for bx in boxes}
        n = 0
        for bx in boxes:
            kx0 = -((off - bx.left) // p)
            ky0 = -((off - bx.bottom) // p)
            kx1 = (bx.right - off) // p
            ky1 = (bx.top - off) // p
            if ky1 * p + off == bx.top and any(
                    y == bx.top and lft < bx.right and r > bx.left
                    for y, lft, r in starts):
                ky1 -= 1
            nx, ny = kx1 - kx0 + 1, ky1 - ky0 + 1
            if nx <= 0 or ny <= 0:
                continue
            self.top.insert(pya.CellInstArray(
                cell.cell_index(), pya.Trans(kx0 * p + off, ky0 * p + off),
                pya.Vector(p, 0), pya.Vector(0, p), nx, ny))
            n += nx * ny
        return n

    def _band(self, x0, y0, x1, y1):
        return pya.Region(pya.DBox(x0, y0, x1, y1).to_itype(self.ly.dbu))

    def _rail(self, layer, y0, y1):
        """The rail on `layer` in band y0..y1: every drawn piece that reaches a
        cell edge, so the vdd islands in the vss band are left out."""
        band = self._band(0.0, y0, W, y1)
        edges = self._band(0.0, y0, 0.001, y1) + self._band(W - 0.001, y0, W, y1)
        drawn = pya.Region(self.top.shapes(self.lay(layer))).merged()
        return (drawn & band).interacting(edges)

    def io_rails(self):
        """The fillers' bands, straight across. The vss Metal3 band loses the
        islands the vdd stripes come up through (clamp.islands)."""
        holes = pya.Region()
        for h in self.m3_holes:
            holes.insert(h.to_itype(self.ly.dbu))
        if self.variant == "no_island_holes":
            holes = pya.Region()
        for net in ("iovss", "iovdd", "vss", "vdd"):
            for layer, y0, y1 in self.bands[net]:
                band = self._band(0.0, y0, W, y1)
                if layer == "Metal3":
                    band -= holes
                if self.variant == "iovss_gap" and net == "iovss" and y0 == 34.5 \
                        and layer == "Metal3":
                    band -= self._band(60.0, y0, 61.0, y1)
                self.top.shapes(self.lay(layer)).insert(band)

    def tie_rails(self):
        """Stitch each iovss and iovdd band on Metal3, Metal4 and TopMetal1 into
        one conductor, as the fillers do."""
        um = lambda v: int(round(v * 1000))  # noqa: E731
        self.tie_counts = {}
        for net in ("iovss", "iovdd"):
            for layer, y0, y1 in self.bands[net]:
                if layer != "Metal3":
                    continue
                m3 = self._rail("Metal3", y0, y1)
                m4 = self._rail("Metal4", y0, y1)
                tm1 = self._rail("TopMetal1", y0, y1)
                via3 = self._lattice("Via3", (m3 & m4).sized(-um(VIA["Via3"] / 2 + ENC["Via3"])))
                tv1 = self._lattice("TopVia1", m4.sized(-um(VIA["TopVia1"] / 2 + TV1_M4_ENC))
                                    & tm1.sized(-um(VIA["TopVia1"] / 2 + ENC["TopVia1"])))
                self.tie_counts["%s %.1f" % (net, y0)] = (via3, tv1)
                if via3 < 1000 or tv1 < 100:
                    raise AssertionError("%s %.1f: %d Via3, %d TopVia1" % (net, y0, via3, tv1))

    def supply_strips(self):
        """Metal2 under the vss and vdd Metal3 bands, INSET inside the cell
        edges, less the clamp's Metal2 of the other net, Via2 up to the rail.
        The clamp's stripes of the same net merge into it."""
        dbu = self.ly.dbu
        ko = int(round(STRIP_KEEP / dbu))
        sliver = int(round(STRIP_MIN / 2.0 / dbu))
        enc = int(round((VIA["Via2"] / 2 + ENC["Via2"]) / dbu))
        self.strip_via2 = {}
        for net in ("vss", "vdd"):
            layer, y0, y1 = [b for b in self.bands[net] if b[0] == "Metal3"][0]
            other = pya.Region()
            for n, r in self.clamp.m2.items():
                if n != net:
                    other += r
            strip = (self._band(INSET, y0, W - INSET, y1) - other.merged().sized(ko)).merged()
            strip = strip.sized(-sliver).sized(sliver) & strip
            self.top.shapes(self.lay("Metal2")).insert(strip)
            # the Via2 also land on this net's stripes the sliver filter dropped
            own = self.clamp.m2.get(net, pya.Region()) & self._band(0.0, y0, W, y1)
            land = (strip + own).merged()
            self.clamp.m2.setdefault(net, pya.Region()).insert(strip)
            n = self._lattice("Via2", (land & self._rail("Metal3", y0, y1)).sized(-enc))
            self.strip_via2[net] = n

    def pins_labels(self):
        """A pin shape on every band layer, as the fillers carry, and one LVS
        label per net."""
        for net in ("iovss", "iovdd", "vss", "vdd"):
            for layer, y0, y1 in self.bands[net]:
                got = self._rail(layer, y0, y1)
                if got.is_empty():
                    raise AssertionError("no %s %s band at y %.1f" % (net, layer, y0))
                self.top.shapes(self.lay(layer + ".pin")).insert(got)
            layer, y_lib = LABEL[net]
            b = [x for x in self.bands[net] if x[0] == layer and x[1] == y_lib][0]
            self.top.shapes(self.lay(layer + ".text")).insert(
                pya.DText(net, pya.DTrans(pya.DVector(W / 2.0, b[2] - 2.0))))

    def check(self):
        """What DRC does not see: the cell outline, and Metal1/Metal2 INSET
        inside it, since the IO cells' own run to within 0.21 um of theirs."""
        dbu = self.ly.dbu
        bb = self.top.dbbox()
        if abs(bb.left) > 1e-6 or abs(bb.bottom) > 1e-6 or abs(bb.right - W) > 1e-6 \
                or abs(bb.top - H) > 1e-6:
            raise AssertionError("cell bbox %s, want 0 0 %g %g" % (bb, W, H))
        inner = self._band(INSET, INSET, W - INSET, H - INSET)
        for layer in ("Metal1", "Metal2"):
            r = pya.Region(self.top.begin_shapes_rec(self.lay(layer)))
            if not (r - inner).is_empty():
                raise AssertionError("%s within %g um of the cell edge at %s"
                                     % (layer, INSET, (r - inner).bbox().to_dtype(dbu)))
        feol = pya.Region()
        for layer in ("Activ", "GatPoly", "NWell", "ThickGateOx"):
            feol += pya.Region(self.top.begin_shapes_rec(self.lay(layer)))
        if feol.bbox().bottom * dbu < clamp.TR_Y0 - 1e-6 and self.variant != "low_activ":
            raise AssertionError("FEOL below y %.1f, Pad.d1R" % clamp.TR_Y0)
        c = dict(self.clamp.counts)
        c.update({"Via2 strip " + k: v for k, v in self.strip_via2.items()})
        floor = {"Via1 clamp vss", "Via1 clamp vdd", "Via2 island", "Via3 island",
                 "Via2 strip vss", "Via2 strip vdd"}
        low = {k: c.get(k, 0) for k in floor if c.get(k, 0) < VIA_FLOOR}
        if low:
            raise AssertionError("via floor %d: %s" % (VIA_FLOOR, low))
        return c

    def mutate(self):
        """The negative controls, each a defect one check has to catch."""
        dbu = self.ly.dbu
        v = self.variant
        if v == "vdd_vss_short":     # a Metal2 bar from a vdd stripe onto a vss one
            self.box("Metal2", 7.4, 100.0, 8.2, 100.6)
        elif v == "open_stripe":     # one vdd stripe of block B cut above the fingers
            a, b = sorted((80 - 13.0, 80 - 14.6))
            cut = self._band(a, 130.0, b, 131.0)
            m2 = pya.Region(self.top.shapes(self.lay("Metal2"))) - cut
            self.top.shapes(self.lay("Metal2")).clear()
            self.top.shapes(self.lay("Metal2")).insert(m2)
        elif v == "m2_spacing":      # a Metal2 tab 0.1 um from a stripe of another net
            self.box("Metal2", 7.5, 100.0, 7.8, 101.0)
        elif v == "low_activ":       # Activ 9.6 um from the west neighbour's pad opening
            self.box("Activ", 2.0, 1.0, 4.0, 3.0)
        elif v == "drop_inv_nmos":   # the inverter NMOS gates gone
            n = self.clamp.inv[0]
            gp = pya.Region()
            for a, b in n.gate_ys:
                gp.insert(pya.DBox(n.poly_x[0], a, n.poly_x[1], b).to_itype(dbu))
            r = pya.Region(self.top.shapes(self.lay("GatPoly"))) - gp
            self.top.shapes(self.lay("GatPoly")).clear()
            self.top.shapes(self.lay("GatPoly")).insert(r)
        elif v not in ("", "no_island_holes", "iovss_gap", "low_activ"):
            raise ValueError("unknown variant %s" % v)

    def build(self):
        self.clamp = clamp.Clamp(self).islands()
        self.io_rails()
        self.tie_rails()
        self.clamp.build()
        self.supply_strips()
        self.pins_labels()
        self.box("prBoundary", 0.0, 0.0, W, H)
        self.mutate()
        self.counts = self.check()
        for key in sorted(self.counts):
            print("  %-26s %6d" % (key, self.counts[key]))
        for key in sorted(self.tie_counts):
            print("  tie %-12s Via3 %5d  TopVia1 %4d" % ((key,) + self.tie_counts[key]))
        return self.ly, self.top

    def write_lef(self, path):
        """The abstract, in the IO library's style: one PORT per band rectangle
        and the fillers' OBS."""
        dbu = self.ly.dbu
        out = ["# SPDX-FileCopyrightText: 2026 Michael Koefinger",
               "# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1",
               "# Written by layout/clamp_gen.py, do not edit.",
               "", "VERSION 5.7 ;", "BUSBITCHARS \"[]\" ;", "DIVIDERCHAR \"/\" ;", "",
               "MACRO %s" % CELL,
               "    CLASS PAD SPACER ;",
               "    ORIGIN 0.000 0.000 ;",
               "    FOREIGN %s 0.000 0.000 ;" % CELL,
               "    SIZE %.3f BY %.3f ;" % (W, H),
               "    SYMMETRY X Y R90 ;",
               "    SITE sg13cmos5l_ioSite ;"]
        use = {"iovdd": "POWER", "iovss": "GROUND", "vdd": "POWER", "vss": "GROUND"}
        for net in ("iovdd", "iovss", "vdd", "vss"):
            out += ["  PIN %s" % net, "    DIRECTION INOUT ;", "    USE %s ;" % use[net]]
            for layer, y0, y1 in self.bands[net]:
                pins = pya.Region(self.top.shapes(self.lay(layer + ".pin")))
                rects = (pins & self._band(0.0, y0, W, y1)).merged()
                for b in sorted((t.bbox() for t in rects.decompose_trapezoids_to_region().each()),
                                key=lambda b: (b.bottom, b.left)):
                    out += ["    PORT", "      LAYER %s ;" % layer,
                            "        RECT %.3f %.3f %.3f %.3f ;" % (
                                b.left * dbu, b.bottom * dbu, b.right * dbu, b.top * dbu),
                            "    END"]
            out.append("  END %s" % net)
        out += ["  OBS"]
        for layer, top in (("Metal1", H), ("Metal2", H), ("Metal3", 178.0), ("Metal4", 178.0),
                           ("TopMetal1", 134.5), ("Via1", H), ("Via2", H)):
            out += ["    LAYER %s ;" % layer, "      RECT 0.000 0.000 %.3f %.3f ;" % (W, top)]
        out += ["  END", "END %s" % CELL, "", "END LIBRARY", ""]
        with open(path, "w") as fh:
            fh.write("\n".join(out))


def main():
    variant = globals().get("variant", "")
    gds = globals().get("out", GDS)
    g = Gen(variant)
    g.build()
    write_gds(g.ly, gds)
    print("wrote %s" % gds)
    if not variant:
        g.write_lef(LEF)
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
