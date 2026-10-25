# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Ported from OpenBLAU 8f25e634, scripts/esd/check.py
# Description: static ESD path check of the pad ring: topology plus IR at HBM current
"""For every HBM pairing, the cheapest discharge path through the pad ring,
priced as a voltage at the HBM peak current: a forward diode costs 0.7 V plus
its on-resistance, a rail clamp its calibrated V0 + R*I, metal and substrate
ties their resistance. No transient, no device model beyond that, so it
answers the two questions a simulation cannot be trusted with alone:

- topology: does every pairing have a path in both polarities that does not
  run through a core gate or the 587 ohm secondary-protection resistor;
- point to point: how much of the budget is metal (the extracted ring) and
  how much is devices.

  python3 scripts/esd/check.py <run> [--ron 1] [--vhbm 2000] [--ideal-ring]
                                [--pkg-gnd] [--without <slot>]...
  python3 scripts/esd/check.py --selftest

Reads <run>/sim/io_esd.spice (models.py) and <run>/pex/esd_ring_rport.spice
(pex.py). Writes <run>/check_r<ron>[...].json. Exits 1 when a pairing has
no path: --without <slot> drops a pad cell's devices to prove it can.
"""

import argparse
import heapq
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import spicerun  # noqa: E402

VF = 0.7                    # forward knee of every diode, V
CLAMP = "sg13cmos5l_Clamp_N43N43D4R"
SEC_R = 100.0               # a resistor above this is not an ESD path (the 587 ohm)


def die(msg):
    sys.stderr.write(f"check: {msg}\n")
    sys.exit(1)


def val(s):
    return float(re.sub(r"(?i)(meg|[fpnumkgt])$", lambda m: {
        "f": "e-15", "p": "e-12", "n": "e-9", "u": "e-6", "m": "e-3", "k": "e3",
        "meg": "e6", "g": "e9", "t": "e12"}[m.group(1).lower()], s))


def parse(path):
    """{subckt: (ports, [(inst, nodes, master, {param: value})])}."""
    cells, cur = {}, None
    for ln in spicerun.unwrap(open(path).read().splitlines()):
        t = ln.split()
        if not t or t[0].startswith("*"):
            continue
        if t[0].lower() == ".subckt":
            cur = t[1]
            cells[cur] = ([x for x in t[2:] if "=" not in x], [])
        elif t[0].lower() == ".ends":
            cur = None
        elif cur and t[0][0] in "XxRrDd":
            pos = [x for x in t[1:] if "=" not in x]
            par = dict(x.split("=", 1) for x in t[1:] if "=" in x)
            if t[0][0] in "Xx":
                cells[cur][1].append((t[0], pos[:-1], pos[-1], par))
            elif t[0][0] in "Rr":
                cells[cur][1].append((t[0], pos[:2], "R", {"R": pos[2]}))
            else:
                cells[cur][1].append((t[0], pos[:2], pos[2], par))
    return cells


class Graph:
    """Directed edges with a cost function of the current: (vf, r)."""

    def __init__(self):
        self.e = defaultdict(dict)       # a -> {b: (vf, r, kind)}

    def add(self, a, b, vf, r, kind, both=False):
        for x, y in ((a, b), (b, a)) if both else ((a, b),):
            old = self.e[x].get(y)
            if old and old[0] == vf and old[2] == kind:     # parallel: conductances add
                r = 1.0 / (1.0 / old[1] + 1.0 / r) if old[1] > 0 and r > 0 else 0.0
            elif old and old[0] + old[1] <= vf + r:
                continue
            self.e[x][y] = (vf, r, kind)

    def cheapest(self, src, dst, i):
        """(volts, [(node, kind)]) of the cheapest path src -> any of dst."""
        dst = set(dst)
        best = {s: 0.0 for s in src}
        prev = {}
        q = [(0.0, s) for s in src]
        while q:
            c, n = heapq.heappop(q)
            if n in dst:
                path = [(n, None)]
                while n in prev:
                    n, k = prev[n]
                    path.append((n, k))
                return c, path[::-1]
            if c > best.get(n, 1e18):
                continue
            for m, (vf, r, kind) in self.e[n].items():
                cc = c + vf + r * i
                if cc < best.get(m, 1e18):
                    best[m] = cc
                    prev[m] = (n, kind)
                    heapq.heappush(q, (cc, m))
        return None, []


def flatten(cells, cell, nodes, pre, g, ron, clamp):
    """Add a cell's ESD-relevant elements to g, its ports mapped to `nodes`."""
    ports, body = cells[cell]
    m = dict(zip(ports, nodes))

    def nm(x):
        return x if x == "sub!" else m.get(x, f"{pre}{x}")
    for inst, pos, master, par in body:
        p = [nm(x) for x in pos]
        if master == "R" or master in ("rppd", "esd_ptap"):
            r = val(par.get("R", "0"))
            if 0 < r <= SEC_R:
                g.add(p[0], p[1], 0.0, r, "R", both=True)
        elif master in ("esd_dn", "esd_dp"):
            area = val(par["l"]) * val(par["w"]) / 35e-12
            g.add(p[0], p[1], VF, ron / area, master[-2:])
        elif master == CLAMP:                     # gate iovss pad: active, pad -> iovss
            g.add(p[2], p[1], clamp[0], clamp[1], "clamp")
        elif master in ("sg13_hv_nmos", "sg13_lv_nmos"):
            d, _, s, b = p
            a = val(par.get("ad", "1p")) * 1e12
            g.add(b, d, VF, ron * 35 / max(a, 0.1), "nbody")
            g.add(b, s, VF, ron * 35 / max(a, 0.1), "nbody")
        elif master in ("sg13_hv_pmos", "sg13_lv_pmos"):
            d, _, s, b = p
            a = val(par.get("ad", "1p")) * 1e12
            g.add(d, b, VF, ron * 35 / max(a, 0.1), "pbody")
            g.add(s, b, VF, ron * 35 / max(a, 0.1), "pbody")
        elif master in cells:
            flatten(cells, master, p, f"{pre}{inst}.", g, ron, clamp)


def build(run, ron, clamp, ideal, without=()):
    sys.path.insert(0, HERE)
    import hbm
    slots, ring, _ = hbm.load(run)
    cells = parse(os.path.join(run, "sim", "io_esd.spice"))
    g = Graph()
    for s, d in slots.items():
        if s in without:                      # the pad cell's devices removed
            continue
        conn = []
        for p in cells[d["master"]][0]:
            conn.append(f"{p}_{s}" if p in hbm.RAILS else
                        f"padc_{s}" if p == "pad" else f"{p}_{s}")
        flatten(cells, d["master"], conn, f"{s}.", g, ron, clamp)
    if "clv_clamp" in ring and "clamp" not in without:     # the clamp cell, 3 of IHP's
        g.add("clv_clamp", "cls_clamp", clamp[0], clamp[1] / hbm.CLAMP_X, "clamp")
    if hbm.PKG_GND:                          # the package short, one bond wire per pad
        for s in slots:
            if hbm.group(s) == "gnd":
                g.add(f"pad_{s}", "pkg_gnd", 0.0, hbm.BOND_R, "bond", both=True)
    # the core: its n-well junction, vss -> vdd
    for k in range(8):
        g.add(f"vssring_{k}", f"vddring_{k}", VF, ron * 35 / (hbm.WELL_A / 8), "well")
    # the ring
    if ideal:
        for n in {n for s in slots.values() for n in s["ports"]} | set(ring):
            r = hbm.ring_net(n)
            if r:
                g.add(n, r, 0.0, 1e-3, "ring", both=True)
            elif n.startswith("pad_"):
                g.add(n, "padc_" + n[4:], 0.0, 1e-3, "ring", both=True)
    else:
        rp = os.path.join(run, "pex", "esd_ring_rport.spice")
        for ln in open(rp):
            t = ln.split()
            if t and t[0].startswith("R"):
                g.add(t[1], t[2], 0.0, float(t[3]), "ring", both=True)
    return g, slots


def clamp_iv(run):
    """(V0, R) of the RC rail clamp from two HBM zaps on IOPadIOVdd alone."""
    io = os.path.join(run, "sim", "io_esd.spice")
    pdk = os.path.join(os.environ["PDK_ROOT"], os.environ["PDK"])
    pts = []
    for v in (1000.0, 2000.0):
        wd = os.path.join(run, "sim", f"clamp_iv_{int(v)}")
        os.makedirs(wd, exist_ok=True)
        with open(os.path.join(pdk, "libs.tech", "ngspice", ".spiceinit")) as f:
            open(os.path.join(wd, ".spiceinit"), "w").write(
                f.read() + "\nset num_threads=1\n")    # the matrix runs in parallel
        deck = "\n".join([
            "* clamp V-I", ".param RON=1", ".lib cornerMOShv.lib mos_tt",
            ".lib cornerMOSlv.lib mos_tt", ".lib cornerRES.lib res_typ", f".include {io}",
            "Xc vdd 0 io 0 sg13cmos5l_IOPadIOVdd", "Rv vdd 0 1e9", "Rs sub! 0 1m",
            f"Chbm hc 0 100p ic={v}", "Rhbm hc hr 1.5k", "Lhbm hr hz 5u", "Vz hz io 0",
            ".options rshunt=1e9 method=gear", ".control", "tran 0.05n 60n uic",
            "meas tran vpk max v(io)", "meas tran ipk max i(vz)", ".endc", ".end", ""])
        r = spicerun.run_deck(deck, workdir=wd, tag="clamp")
        m = spicerun.measures(r.out, ["vpk", "ipk"])
        if None in m.values():
            die(f"clamp calibration at {v} V failed, see {wd}/clamp.log")
        pts.append((m["ipk"], m["vpk"]))
    (i1, v1), (i2, v2) = pts
    rr = (v2 - v1) / (i2 - i1)
    return v1 - rr * i1, rr, pts


def run_check(run, ron, vhbm, ideal, without=()):
    import hbm
    v0, rc, pts = clamp_iv(run)
    g, slots = build(run, ron, (v0, rc), ideal, without)
    ipk = vhbm / 1500.0
    rows = []
    for zap, ref, pol in hbm.matrix(slots):
        zn, refs = hbm.pins(slots, zap, ref)
        src, dst = ([zn], refs) if pol == "+" else (refs, [zn])
        v, path = g.cheapest(src, dst, ipk)
        kinds = [k for _, k in path if k]
        rows.append(dict(zap=zap, ref=ref, pol=pol, v=v,
                         diodes=sum(k in ("dn", "dp", "nbody", "pbody", "well") for k in kinds),
                         clamps=kinds.count("clamp"),
                         r_ring=sum(g.e[a][b][1] for (a, _), (b, _) in zip(path, path[1:])
                                    if g.e[a].get(b, (0, 0, ""))[2] == "ring"),
                         path=[n for n, _ in path]))
    tagn = (f"check_r{ron:g}{'_ideal' if ideal else ''}{'_pkg' if hbm.PKG_GND else ''}"
            f"{''.join('_no_' + w for w in without)}.json")
    json.dump(dict(ron=ron, vhbm=vhbm, ideal_ring=ideal, clamp=dict(v0=v0, r=rc, pts=pts),
                   rows=rows), open(os.path.join(run, tagn), "w"), indent=1)
    print(f"check: rail clamp V = {v0:.2f} V + {rc:.2f} ohm * I "
          f"(from {pts[0][1]:.2f} V at {pts[0][0]:.2f} A, {pts[1][1]:.2f} V at {pts[1][0]:.2f} A)")
    print(f"check: {'zap':>8} {'ref':>6} pol   V@{ipk:.2f}A  diodes clamps  R_ring")
    for r in sorted(rows, key=lambda r: -(r["v"] or 1e9))[:20]:
        vs = "NO PATH" if r["v"] is None else f"{r['v']:7.2f}"
        print(f"check: {r['zap']:>8} {r['ref']:>6}  {r['pol']}   {vs}  {r['diodes']:6d} "
              f"{r['clamps']:6d}  {r['r_ring']:6.3f}")
    miss = [r for r in rows if r["v"] is None]
    print(f"check: {len(rows) - len(miss)} of {len(rows)} pairings have a path; results {tagn}")
    return 1 if miss else 0


def selftest():
    g = Graph()
    g.add("a", "b", VF, 1.0, "dp")
    g.add("a", "b", VF, 1.0, "dp")             # parallel pair: 0.5 ohm
    g.add("b", "c", 0.0, 2.0, "R", both=True)
    v, path = g.cheapest(["a"], ["c"], 1.0)
    assert abs(v - (0.7 + 0.5 + 2.0)) < 1e-9, v
    assert g.cheapest(["c"], ["a"], 1.0)[0] is None     # a diode does not conduct back
    assert abs(val("5.239K") - 5239) < 1e-9 and abs(val("208.211m") - 0.208211) < 1e-12
    print("check: selftest passed")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run", nargs="?")
    ap.add_argument("--ron", type=float, default=1.0)
    ap.add_argument("--vhbm", type=float, default=2000.0)
    ap.add_argument("--ideal-ring", action="store_true")
    ap.add_argument("--pkg-gnd", action="store_true",
                    help="VSS and IOVSS shorted in the package (assumption)")
    ap.add_argument("--without", action="append", default=[],
                    help="drop a pad cell's devices (prove the check can fail)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.run:
        die("no run directory")
    import hbm
    hbm.PKG_GND = a.pkg_gnd
    slots, _, _ = hbm.load(os.path.abspath(a.run))
    for w in a.without:
        if w not in slots and w != "clamp":
            die(f"--without {w}: no such slot or clamp, have {sorted(slots)}")
    sys.exit(run_check(os.path.abspath(a.run), a.ron, a.vhbm, a.ideal_ring, a.without))


if __name__ == "__main__":
    main()
