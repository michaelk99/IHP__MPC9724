# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Ported from OpenBLAU 8f25e634, scripts/esd/hbm.py
# Description: HBM zap matrix on the extracted pad ring, ngspice
"""Human Body Model zaps on the chip's pad ring: every pad against every
supply group and against the other signal pads, both polarities (JS-001).

  python3 scripts/esd/hbm.py [--ron 1] [--vhbm 2000] [--zap clk:vss:+]
                             [--ideal-ring] [--pkg-gnd] [--jobs N] [--tstop 80n] <run>

<run> holds pex/ports.json and pex/esd_ring_rport.spice (scripts/esd/pex.py)
and sim/io_esd.spice (scripts/esd/models.py). Writes <run>/sim/<tag>/ per zap
and <run>/hbm_r<ron>[_ideal][_pkg].json.

What each deck carries:
- the pad ring and core ring as a Kron-reduced R network between the ports
  (or, with --ideal-ring, every rail one node: the no-metal reference)
- every pad cell, transistor level, from the PDK IO netlist with the
  high-current diodes (models.py)
- the core, at the core-ring port nearest each pad or split over the eight
  ports per rail: the DECAPHV banks (each an RC from its cell count, its C
  and its estimated channel corner), the core's n-well/p-substrate junction
  (vss anode, vdd cathode), the BUFX3 that drives every output pad's c2p (an AND2X1 for adc_conv), and a core input load on every p2c. The core is unpowered: the driver inputs sit at its vss.
- dsm2 as a box, two nodes: vddadsm on VDDA's strap and vssdsm on the VSS strap, where they leave the clipped annulus. The segment's pads (dsm_clk, do_q, do_q_b, vi, vcm, ibias_test) attach their core side there: a BUFX3 as the stand-in for dsm2's output drivers on do_q and do_q_b and on the inout dsm_clk pad's c2p and c2p_en, 50 fF on dsm_clk's p2c, and on each analog pin dsm2's own sg13cmos5l_SecondaryProtection (esd_dsm2_secprot in models.py) with 50 fF at its core node in_<slot>. dsm2's own decap and well junction are not in the model.
- decap_vdda's DECAPHV bank between vddadcp and vssdcp, its two straps, built as the core banks.
- the tester: 100 pF at V, 1.5 kohm, 5 uH, 1 pF at the pin (inside JS-001,
  --selftest); the reference pins at 0 V; every other pin floats (rshunt
  1 Gohm)
"""

import argparse
import json
import math
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import spicerun  # noqa: E402

RAILS = ("vdd", "vss", "iovdd", "iovss")      # the pad cells' supply pins
NETS = RAILS + ("vdda",)                      # the rails of the ring: the segment's vdd is vdda
DRIVER = {"adcconv": "AND2X1"}                # the core cell behind an output pad, else BUFX3
# Core-rail decap: DECAPHV cells, chip top (netlist/pnl) plus macro
# (macros/dsa1_dig/final/pnl). C per cell is the CDL device in ngspice, AC at
# 1.2 V, tt (6.27 / 30.52 / 79.01 fF, flat to 5 V within 4 %). The channel
# corner is the decap_hv library's own estimate ($DECAPHV_DIR/doc/decap_hv.md),
# so each bank is C in series with 1 / (2 pi f_c C).
DECAP = {                  # cell: (count top + macro, C per cell F, corner Hz)
    "DECAPHV8": (339 + 1578, 6.272e-15, 10e9),
    "DECAPHV16": (200 + 575, 30.52e-15, 0.4e9),
    "DECAPHV32": (517 + 78, 79.01e-15, 60e6),
}
# decap_vdda on VDDA (macros/decap_vdda/final/pnl), 67.61 pF
DECAP_VDDA = {"DECAPHV8": (339, 6.272e-15, 10e9), "DECAPHV16": (323, 30.52e-15, 0.4e9),
              "DECAPHV32": (704, 79.01e-15, 60e6)}
R_DECAP = 0.5              # series R of the whole bank to the ring, lumped (assumption)
WELL_A = 20000.0           # core n-well junction, um^2 (assumption: bounds, not measured)
C_LOAD = 50e-15            # a core input behind p2c, or an open padres stub
# --pkg-gnd: VSS and IOVSS shorted in the package (packaging/config.yaml
# EPAD_NETS). Every VSS/IOVSS bond pad reaches one package node through its
# own downbond, and JS-001 then treats the two as one pin group, `gnd`.
PKG_GND = False
UNBONDED = ("iovdd_w5",)       # a ring cell without a wire (UNBONDED_PADS in packaging/config.yaml): never a tester pin
BOND_L, BOND_R = 0.5e-9, 0.05  # per downbond: 500 um of 25 um Au (packaging/result.md)
# On "Timestep too small", in this order, recorded per zap. Priced on a zap
# that converges as is (miso - vs io, RON 1): 0.02 ns step 4 mV, trap 2 mV,
# 1 fF cshunt 0.116 V, 3 fF aborted. So the finer step and trap go first.
RETRY = (("tstep=0.02n", lambda d: d.replace("tran 0.05n", "tran 0.02n")),
         ("method=trap", lambda d: d.replace("method=gear", "method=trap")),
         ("cshunt=1e-15", lambda d: d.replace("cshunt=1e-16", "cshunt=1e-15")),
         ("cshunt=3e-15", lambda d: d.replace("cshunt=1e-16", "cshunt=3e-15")))


def die(msg):
    sys.stderr.write(f"hbm: {msg}\n")
    sys.exit(1)


def decap_banks(table=None):
    """{cell: (C, R)} of the core-rail decap banks, or of another table of the same form."""
    out = {}
    for cell, (n, c, fc) in (table or DECAP).items():
        out[cell] = (n * c, 1.0 / (2 * math.pi * fc * n * c))
    return out


def subckt_ports(path):
    """{subckt: [ports]} from a netlist, continuations folded."""
    out = {}
    for ln in spicerun.unwrap(open(path).read().splitlines()):
        t = ln.split()
        if t and t[0].lower() == ".subckt":
            out[t[1]] = [x for x in t[2:] if "=" not in x]
    return out


CLAMP_CELL = "sg13cmos5l_ip__clamp_vddvss"
CLAMP_X = 3.0              # its NMOS over IHP's Clamp_N43N43D4R


def load(run):
    """(slots, ring, ports.json): the clamp cell is no pad slot, its ports join
    the ring ports."""
    pj = json.load(open(os.path.join(run, "pex", "ports.json")))
    slots = {}
    for p in pj["ports"]:
        if p["kind"] in ("ring", "dsm") or p["master"] == CLAMP_CELL:
            continue
        s = slots.setdefault(p["slot"], dict(master=p["master"], side=p["side"], k=p["k"],
                                             seg=p["seg"], ports=set()))
        if p["master"] != "bondpad":
            s["master"] = p["master"]
        if p["kind"] == "padc":
            s["xy"] = (p["x"], p["y"])
        s["ports"].add(p["name"])
    ring = sorted({p["name"] for p in pj["ports"]
                   if p["kind"] in ("ring", "dsm") or p["master"] == CLAMP_CELL})
    # the core-ring point nearest each pad: where its core-side circuits attach
    rk = {p["k"]: (p["x"], p["y"]) for p in pj["ports"]
          if p["kind"] == "ring" and p["rail"] == "vss"}
    for s in slots.values():
        x, y = s["xy"]
        s["ring_k"] = min(rk, key=lambda k: (rk[k][0] - x) ** 2 + (rk[k][1] - y) ** 2)
        # where the core cell behind the pad sits: a ring point, or dsm2's pins
        s["vdd_net"] = "vdda" if s["seg"] else "vdd"
        s["cv"] = "vddadsm" if s["seg"] else f"vddring_{s['ring_k']}"
        s["cg"] = "vssdsm" if s["seg"] else f"vssring_{s['ring_k']}"
    return slots, ring, pj


def group(slot):
    """The supply group a slot belongs to, or None for a signal pad."""
    head = slot.split("_")[0]
    if not (head in NETS and re.match(r"^[a-z]+_[nesw]\d$", slot)):
        return None
    return "gnd" if PKG_GND and head in ("vss", "iovss") else head


def pins(slots, zap, ref):
    """(zap node, [reference nodes]): the package pin where the tester
    connects. With --pkg-gnd that is the package ground node for `gnd`."""
    zn = "pkg_gnd" if group(zap) == "gnd" else f"pad_{zap}"
    if ref == "gnd":
        return zn, ["pkg_gnd"]
    refs = [f"pad_{s}" for s in slots if s not in UNBONDED
            if (group(s) == ref if ref != "io" else group(s) is None and s != zap)]
    return zn, refs


def matrix(slots):
    """[(zap, ref, polarity)]: signal x supply group, supply x supply,
    signal x all other signals. ref is a group name or 'io'."""
    sig = sorted(s for s in slots if group(s) is None)
    sup = sorted({group(s) for s in slots if group(s)})
    out = []
    for s in sig:
        for g in sup:
            out += [(s, g, "+"), (s, g, "-")]
    for i, a in enumerate(sup):
        for b in sup[i + 1:]:
            zap = sorted(x for x in slots if group(x) == a)[0]
            out += [(zap, b, "+"), (zap, b, "-")]
    for s in sig:
        out += [(s, "io", "+"), (s, "io", "-")]
    return out


def ring_net(name):
    """The rail a ring-network port sits on, or None for a pad net."""
    for r in NETS:
        if name.startswith(r + "_") or name.startswith(r + "ring_"):
            return r
    if name in ("vddadsm", "vssdsm", "vddadcp", "vssdcp"):    # dsm2's and decap_vdda's straps
        return "vdda" if name.startswith("vdda") else "vss"
    if name.startswith(("clv_", "cls_")):        # the clamp cell's stripes
        if name.startswith("cls_"):
            return "vss"
        return "vdda" if name.endswith("_vdda") else "vdd"
    m = re.match(r"^pad[c]?_([a-z]+)_[nesw]\d$", name)
    if m and m.group(1) in NETS:
        return m.group(1)
    return None


def core_cell(ports, cell, conn, inst):
    """An EZ130 cell instance, its pins named in `conn`, in the file's order."""
    return f"X{inst} {' '.join(conn[p] for p in ports[cell])} {cell}"


def deck(run, slots, ring, zap, ref, pol, a):
    io = os.path.join(run, "sim", "io_esd.spice")
    ports = subckt_ports(io)
    L = [f"* HBM {zap} vs {ref} {pol}{a.vhbm} V, RON {a.ron}",
         f".param RON={a.ron}",
         ".lib cornerMOShv.lib mos_tt", ".lib cornerMOSlv.lib mos_tt",
         ".lib cornerRES.lib res_typ",
         f".include {io}"]
    # ring
    if a.ideal_ring:
        names = sorted({n for s in slots.values() for n in s["ports"]} | set(ring))
        for n in names:
            r = ring_net(n)
            if r:
                L.append(f"Rid_{n} {n} {r} 1m")
            elif n.startswith("pad_"):
                L.append(f"Rid_{n} {n} padc_{n[4:]} 1m")
    else:
        rp = os.path.join(run, "pex", "esd_ring_rport.spice")
        rports = subckt_ports(rp)["esd_ring_rport"]
        L += [f".include {rp}", f"Xring {' '.join(rports)} esd_ring_rport"]
    # pads, and the core cell behind each
    for s, d in sorted(slots.items()):
        m = d["master"]
        cv, cg = d["cv"], d["cg"]
        core = dict(VDD=cv, VNW=cv, VPW=cg, VSS=cg, A=cg, B=cg)
        conn = []
        for p in ports[m]:
            if p in RAILS:
                conn.append(f"{d['vdd_net'] if p == 'vdd' else p}_{s}")
            elif p == "pad":
                conn.append(f"padc_{s}")
            elif p == "p2c":                  # a core input, or an open stub (bidir)
                conn.append(f"p2c_{s}")
                L.append(f"Cl_p2c_{s} p2c_{s} {cg} {C_LOAD}")
            elif p == "padres":               # analog pin of dsm2: its protection, then its input
                conn.append(f"padres_{s}")
                L.append(f"Xsp_{s} padres_{s} in_{s} {cv} {cg} esd_dsm2_secprot")
                L.append(f"Cl_in_{s} in_{s} {cg} {C_LOAD}")
            elif p in ("c2p", "c2p_en"):      # output and its enable: the core cell that drives each
                n = f"{p}_{s}"
                conn.append(n)
                cell = DRIVER.get(s, "BUFX3")
                L.append(core_cell(ports, cell, dict(core, Y=n), f"drv_{p}_{s}"))
            else:
                die(f"{m}: port {p} has no rule")
        L.append(f"Xp_{s} {' '.join(conn)} {m}")
    # the drawn clamp cells, on their stripe ports, their in-cell metal extracted with the ring
    for c in ("clamp", "clamp_vdda"):
        if f"clv_{c}" in ring and c not in a.no_clamp:
            L.append(f"Xclampcell_{c} clv_{c} cls_{c} esd_clamp_vddvss_cell")
    # a vdd-to-vss clamp not yet drawn, on a slot's rail ports behind its in-cell metal
    if a.clamp:
        # --clamp-x scales it as wider cells would: x clamps in parallel, the metal R over x
        n = a.clamp_x
        L += [f"Rclv vdd_{a.clamp} clv {a.clamp_r / n:g}", f"Rcls vss_{a.clamp} cls {a.clamp_r / n:g}"]
        L += [f"Xclamp{i} clv cls esd_clamp_vddvss" for i in range(int(n))]
        if n != int(n):
            L.append(f"Xclamph clv cls esd_clamp_vddvss_half")
    # core, split over the eight core-ring points per rail
    for k in range(8):
        v, g = f"vddring_{k}", f"vssring_{k}"
        L.append(f"Rdc{k} {v} dcm{k} {R_DECAP * 8:.4g}")
        for cell, (c, r) in decap_banks().items():
            L.append(f"C{cell}_{k} dcm{k} dc{cell}_{k} {c / 8:.4g}")
            L.append(f"R{cell}_{k} dc{cell}_{k} {g} {r * 8:.4g}")
        L.append(f"Dwell{k} {g} {v} esd_dn_hc area={WELL_A / 35 / 8:.4g}")
    L.append(f"Rdcp vddadcp dcpm {R_DECAP:.4g}")
    for cell, (c, r) in decap_banks(DECAP_VDDA).items():
        L.append(f"Cdcp{cell} dcpm dcp{cell} {c:.4g}")
        L.append(f"Rdcp{cell} dcp{cell} vssdcp {r:.4g}")
    L.append("Rsub sub! vssring_0 1e9")       # sub! is tied through ptaps; keep it defined
    # tester
    zn, refs = pins(slots, zap, ref)
    if PKG_GND:                                # the package short, one downbond per pad
        for s in sorted(x for x in slots if group(x) == "gnd"):
            L += [f"Lbw_{s} pad_{s} bw_{s} {BOND_L:g}", f"Rbw_{s} bw_{s} pkg_gnd {BOND_R:g}"]
    if not refs:
        die(f"no reference pins for {ref}")
    v = a.vhbm if pol == "+" else -a.vhbm
    L += tester(v, zn)
    L += [f"Rref{i} {n} 0 1m" for i, n in enumerate(refs)]
    # probes: every ring port, the core-side nodes, the tester current
    save = sorted({n for s in slots.values() for n in s["ports"]} | set(ring))
    for s, d in sorted(slots.items()):
        pp = ports.get(d["master"], [])
        save += [f"{p}_{s}" for p in ("p2c", "padres", "c2p") if p in pp]
        save += [f"in_{s}"] if "padres" in pp else []
        if "p2c" in pp:                        # the secondary-protected node
            save.append(f"xp_{s}.xi{leveldown_index(io, d['master'])}.net1")
    save += ["pkg_gnd"] if PKG_GND else []
    L += [".options cshunt=1e-16 rshunt=1e9 method=gear reltol=1e-3 abstol=1e-9 vntol=1e-5",
          ".control", "set filetype=binary",
          f"tran 0.05n {a.tstop} uic",
          "write zap.raw " + " ".join(f"v({n})" for n in save) + " i(vzap)",
          ".endc", ".end"]
    return "\n".join(L) + "\n"


_LD = {}


def leveldown_index(io, master):
    """The instance suffix of LevelDown inside a pad cell (XI0, XI4, ...)."""
    if master not in _LD:
        cur, idx = None, None
        for ln in open(io):
            t = ln.split()
            if t and t[0] == ".subckt":
                cur = t[1]
            elif cur == master and t and t[-1] == "sg13cmos5l_LevelDown":
                idx = t[0][2:].lower()
        if idx is None:
            die(f"{master}: no LevelDown instance")
        _LD[master] = idx
    return _LD[master]


def slots_of(run):
    return load(os.path.abspath(run))[0]


def tag(zap, ref, pol, ron):
    return f"{zap}__{ref}__{'p' if pol == '+' else 'n'}__r{ron:g}"


def extremes(run_dir, slots, zap, ref):
    """{quantity: (vmax, vmin)} from one zap's rawfile."""
    names, npt, vals = spicerun.read_raw(os.path.join(run_dir, "zap.raw"))
    col = {n.lower(): i for i, n in enumerate(names)}

    def v(n):
        i = col.get(f"v({n.lower()})")
        return None if i is None else [row[i] for row in vals]

    t = [row[0] for row in vals]
    mid = min(range(len(t)), key=lambda k: abs(t[k] - t[-1] / 2))
    late = [0.0]                 # rise over the second half of the window, V

    def pair(a, b, key, out):
        va, vb = v(a), v(b)
        if va is None or vb is None:
            return
        d = [x - y for x, y in zip(va, vb)]
        hi, lo = max(d), min(d)
        out[key] = (hi, lo)
        # still climbing at the end? a charged floating rail plateaus, fine
        late[0] = max(late[0], abs(d[-1]) - max(abs(x) for x in d[:mid + 1]))

    out = {}
    zn, refs = pins(slots, zap, ref)
    pair(zn, sorted(refs)[0], "pad", out)
    i = col.get("i(vzap)")
    if i is not None:
        cur = [row[i] for row in vals]
        out["i_zap"] = (max(cur), min(cur))
    for k in range(8):
        pair(f"vddring_{k}", f"vssring_{k}", f"core_vdd_vss_{k}", out)
    pair("vddadsm", "vssdsm", "dsm_vdda_vss", out)
    pair("vddadcp", "vssdcp", "dcp_vdda_vss", out)
    for s, d in slots.items():
        vd, cv, cg = d["vdd_net"], d["cv"], d["cg"]
        pair(f"{vd}_{s}", f"vss_{s}", f"{vd}_vss@{s}", out)
        pair(f"iovdd_{s}", f"iovss_{s}", f"iovdd_iovss@{s}", out)
        pair(f"{vd}_{s}", f"iovss_{s}", f"{vd}_iovss@{s}", out)
        pair(f"padc_{s}", f"iovss_{s}", f"pad_iovss@{s}", out)
        pair(f"padc_{s}", f"iovdd_{s}", f"pad_iovdd@{s}", out)
        # LV: the pad cell's level shifter against its own rails, the core
        # cell (BUFX3, the input gate) against the core ring or dsm2's pins
        for n, tagn in ((f"c2p_{s}", "c2p"), (f"p2c_{s}", "p2c")):
            pair(n, f"vss_{s}", f"{tagn}_vss@{s}", out)
            pair(f"{vd}_{s}", n, f"{vd}_{tagn}@{s}", out)
            pair(n, cg, f"{tagn}_core@{s}", out)
            pair(cv, n, f"core_{tagn}@{s}", out)
        pair(f"padres_{s}", f"iovss_{s}", f"padres_iovss@{s}", out)
        pair(f"iovdd_{s}", f"padres_{s}", f"iovdd_padres@{s}", out)
        pair(f"padres_{s}", cg, f"padres_core@{s}", out)
        pair(cv, f"padres_{s}", f"core_padres@{s}", out)
        pair(f"in_{s}", cg, f"in_core@{s}", out)          # behind dsm2's protection, at its gates
        pair(cv, f"in_{s}", f"core_in@{s}", out)
        net1 = [c for c in col if c.startswith(f"v(xp_{s}.") and c.endswith(".net1)")]
        if net1:
            n = net1[0][2:-1]
            pair(n, f"iovss_{s}", f"secprot_iovss@{s}", out)
            pair(f"iovdd_{s}", n, f"iovdd_secprot@{s}", out)
    out["late_rise"] = (late[0], t[-1])
    return out


def one(run, slots, ring, z, a):
    zap, ref, pol = z
    t = tag(zap, ref, pol, a.ron) + ("__ideal" if a.ideal_ring else "") + \
        ("__pkg" if PKG_GND else "") + (f"__clamp_{a.clamp}_x{a.clamp_x:g}" if a.clamp else "") + \
        "".join(f"__no_{c}" for c in a.no_clamp)
    wd = os.path.join(run, "sim", t)
    raw = os.path.join(wd, "zap.raw")
    if not (a.reuse and os.path.isfile(raw)):
        if os.path.isfile(raw):
            os.remove(raw)                  # never read a previous run's rawfile
        os.makedirs(wd, exist_ok=True)      # the PDK's .spiceinit loads the PSP OSDI
        pdk = os.path.join(os.environ["PDK_ROOT"], os.environ["PDK"])
        with open(os.path.join(pdk, "libs.tech", "ngspice", ".spiceinit")) as f:
            open(os.path.join(wd, ".spiceinit"), "w").write(
                f.read() + "\nset num_threads=1\n")    # the matrix runs in parallel
        d = deck(run, slots, ring, zap, ref, pol, a)
        r = spicerun.run_deck(d, workdir=wd, tag="zap", timeout=a.timeout)
        for name, change in RETRY:            # the deck's first line names the rung
            if "simulation(s) aborted" not in r.out:
                break
            r = spicerun.run_deck(f"* retry: {name}\n" + change(d), workdir=wd, tag="zap",
                                  timeout=a.timeout)
        if not os.path.isfile(raw) or "simulation(s) aborted" in r.out:
            return t, dict(error=r.out[-2000:])
    if "simulation(s) aborted" in open(os.path.join(wd, "zap.log")).read():
        return t, dict(error="ngspice aborted, see zap.log")        # a reused partial raw
    try:
        res = extremes(wd, slots, zap, ref)
        m = re.match(r"\* retry: (\S+)", open(os.path.join(wd, "zap.spice")).readline())
        if m:
            res["retry"] = m.group(1)
        if a.drop_raw:
            os.remove(raw)
        return t, res
    except Exception as e:                     # a truncated rawfile: report, not crash
        return t, dict(error=f"{type(e).__name__}: {e}")


def tester(v, node):
    """The HBM tester network into `node` (JS-001, 100 pF / 1.5 kohm)."""
    return [f"Chbm hc 0 100p ic={v}", "Rhbm hc hr 1.5k", "Lhbm hr hz 5u",
            "Ctst hz 0 1p", f"Vzap hz {node} 0"]


def check_unbonded():
    """hbm.UNBONDED must name the slot of the pad that packaging/config.yaml leaves without a wire."""
    import yaml
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    west = yaml.safe_load(open(os.path.join(root, "flow/librelane/config.yaml")))["PAD_WEST"]
    left = yaml.safe_load(open(os.path.join(root, "packaging/config.yaml")))["UNBONDED_PADS"] or {}
    cells = [c for c in west if not str(c).startswith("clamp")]    # clamp cells take no slot number
    want = []
    for name, n in left.items():
        idx = [i + 1 for i, c in enumerate(cells) if name.lower() + "_pad" in str(c)]
        want += [f"{name.lower()}_w{i}" for i in idx[len(idx) - n:]] if n else []
    if sorted(want) != sorted(UNBONDED):
        die(f"hbm.UNBONDED {UNBONDED} does not match UNBONDED_PADS in packaging/config.yaml, slots {want}")


def selftest():
    check_unbonded()
    """The tester into a short at 2 kV against JS-001: Ips 1.20..1.48 A,
    rise (10..90 %) 2..10 ns, decay (to 36.8 %) 130..170 ns."""
    deck = "\n".join(["* HBM source into a short"] + tester(2000.0, "0") + [
        ".control", "tran 0.02n 600n uic", "meas tran ipk max i(vzap)",
        "meas tran t10 when i(vzap)=0.1328 rise=1", "meas tran t90 when i(vzap)=1.195 rise=1",
        "meas tran tpk when i(vzap)=1.3 rise=1",
        "meas tran tdec when i(vzap)=0.4886 fall=1", ".endc", ".end", ""])
    m = spicerun.measures(spicerun.run_deck(deck).out, ["ipk", "t10", "t90", "tdec"])
    if None in m.values():
        die(f"source selftest: a measurement failed: {m}")
    rise, decay = (m["t90"] - m["t10"]) * 1e9, m["tdec"] * 1e9
    ok = 1.20 <= m["ipk"] <= 1.48 and 2 <= rise <= 10 and 130 <= decay <= 170
    print(f"hbm: source at 2 kV into a short: Ipk {m['ipk']:.3f} A, rise {rise:.2f} ns, "
          f"decay {decay:.1f} ns: {'passed' if ok else 'FAILED'}")
    for cell, (c, r) in decap_banks().items():
        print(f"hbm: core decap {cell}: {c * 1e12:.2f} pF behind {r:.3f} ohm")
    for cell, (c, r) in decap_banks(DECAP_VDDA).items():
        print(f"hbm: VDDA decap {cell}: {c * 1e12:.2f} pF behind {r:.3f} ohm")
    if not ok:
        sys.exit(1)


def main():
    if sys.argv[1:] == ["--selftest"]:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run")
    ap.add_argument("--ron", type=float, default=1.0)
    ap.add_argument("--vhbm", type=float, default=2000.0)
    ap.add_argument("--zap", action="append", help="zap:ref:pol, repeatable; default all")
    ap.add_argument("--ideal-ring", action="store_true")
    ap.add_argument("--pkg-gnd", action="store_true",
                    help="VSS and IOVSS shorted in the package")
    ap.add_argument("--tstop", default="80n",
                    help="each zap is checked for a quantity still rising")
    ap.add_argument("--jobs", type=int, default=int(os.environ.get("ESD_NJOBS", "4")))
    ap.add_argument("--timeout", type=float, default=3600)
    ap.add_argument("--reuse", action="store_true", help="read existing rawfiles")
    ap.add_argument("--drop-raw", action="store_true", help="delete each rawfile once read")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--clamp", metavar="SLOT", help="price a vdd-to-vss clamp on SLOT's rail ports")
    ap.add_argument("--clamp-r", type=float, default=0.4,
                    help="Ohm per side for the clamp's in-cell metal, OpenBLAU extracted 0.41")
    ap.add_argument("--clamp-x", type=float, default=1.0, help="clamp size, in steps of 0.5")
    ap.add_argument("--no-clamp", action="append", default=[], choices=("clamp", "clamp_vdda"),
                    help="leave a drawn clamp cell out, repeatable")
    a = ap.parse_args()
    if a.clamp and a.clamp not in slots_of(a.run):
        die(f"--clamp {a.clamp}: no such slot")
    global PKG_GND
    PKG_GND = a.pkg_gnd
    run = os.path.abspath(a.run)
    slots, ring, _ = load(run)
    zaps = matrix(slots)
    if a.zap:
        zaps = [tuple(z.split(":")) for z in a.zap]
    if a.list:
        for z in zaps:
            print(*z)
        print(f"{len(zaps)} zaps")
        return
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        res = dict(ex.map(lambda z: one(run, slots, ring, z, a), zaps))
    name = (f"hbm_r{a.ron:g}{'_ideal' if a.ideal_ring else ''}{'_pkg' if PKG_GND else ''}"
            f"{'_clamp_' + a.clamp if a.clamp else ''}{f'_x{a.clamp_x:g}' if a.clamp and a.clamp_x != 1 else ''}"
            f"{''.join('_no_' + c for c in a.no_clamp)}.json")
    if a.zap and os.path.isfile(os.path.join(run, name)):     # a rerun merges in
        old = json.load(open(os.path.join(run, name)))["zaps"]
        old.update(res)
        res = old
    json.dump(dict(ron=a.ron, vhbm=a.vhbm, ideal_ring=a.ideal_ring, pkg_gnd=PKG_GND,
                   seg=sorted(s for s, d in slots.items() if d["seg"]), zaps=res),
              open(os.path.join(run, name), "w"), indent=1)
    late = [t for t, r in res.items() if "error" not in r and r["late_rise"][0] > 0.1]
    for t in late:
        print(f"hbm: {t}: still rising {res[t]['late_rise'][0]:.2f} V past half the window, "
              f"lengthen --tstop")
    bad = [t for t, r in res.items() if "error" in r]
    print(f"hbm: {len(res) - len(bad)} of {len(res)} zaps ran, results in {name}")
    for t in bad:
        print(f"hbm: {t} FAILED: {res[t]['error'][-300:]}")
    bad += late
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
