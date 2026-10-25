# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Ported from OpenBLAU 8f25e634, scripts/esd/pex.py
# Description: R extraction of the pad ring, Kron-reduced onto its ports
"""The pad ring as a resistor network between its ports.

  python3 scripts/esd/pex.py <run> clip | extract | reduce | all
  python3 scripts/esd/pex.py --selftest

clip     scripts/esd/ring_clip.py -> <run>/pex/esd_ring.gds, ports.json
extract  kpex 2.5D, R only, through scripts/esd/kpex_cmos5l.py --wires
         (kpex 0.4.4, image hpretl/iic-osic-tools:2026.09)
reduce   Kron reduction onto the ports (exact at DC): esd_ring_rport.spice,
         one resistor per port pair whose conductance is not negligible

The reduction is where the network becomes simulable: the extraction carries
every via of the ring, the reduced network only what one port sees of another.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
import spicerun  # noqa: E402

G_MIN = 1e-6        # drop a reduced branch above 1 Mohm: nothing of ESD size flows


def die(msg):
    sys.stderr.write(f"pex: {msg}\n")
    sys.exit(1)


def clip(run):
    out = os.path.join(run, "pex")
    r = subprocess.run(["klayout", "-b", "-r", os.path.join(HERE, "ring_clip.py"),
                        "-rd", f"out={out}"])
    if r.returncode:
        die("ring_clip failed")


def extract(run, threads):
    pex = os.path.join(run, "pex")
    cwd = os.path.join(pex, ".kpex_cwd")     # kpex writes one file into cwd's parent
    os.makedirs(cwd, exist_ok=True)
    cmd = [sys.executable, os.path.join(HERE, "kpex_cmos5l.py"),
           os.path.join(pex, "deck"), "--wires", "--rc-netlist",
           os.path.join(pex, "esd_ring_rc.spice"), "extract", "--pdk", "ihp-sg13cmos5l",
           "--gds", os.path.join(pex, "esd_ring.gds"), "--cell", "esd_ring",
           "--out_dir", os.path.join(pex, "out"), "--2.5D", "--mode", "R",
           "--cache-lvs", "False", "--threads", str(threads)]
    with open(os.path.join(pex, "kpex.log"), "w") as log:
        r = subprocess.run(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
    if r.returncode:
        die(f"kpex failed, see {pex}/kpex.log")


def read_r(path):
    """(ports, [(a, b, ohm)]) of a flat resistor subcircuit."""
    ports, rs = None, []
    for ln in spicerun.unwrap(open(path).read().splitlines()):
        t = ln.split()
        if not t or t[0].startswith("*"):
            continue
        if t[0].lower() == ".subckt":
            ports = t[2:]
        elif t[0][0] in "Rr":
            v = spicerun_value(t[3])
            if v < 1e11:                 # Rfloat/Ridle, 1 Tohm: no DC path
                rs.append((t[1], t[2], v))
        elif t[0][0] in "Cc" or t[0].lower() == ".ends":
            continue
        else:
            die(f"{path}: unexpected card {t[0]}: an interconnect extraction has R only")
    if ports is None:
        die(f"{path}: no .subckt")
    return ports, rs


def spicerun_value(s):
    m = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3,
         "meg": 1e6, "g": 1e9, "t": 1e12}
    s = s.lower()
    for suf in sorted(m, key=len, reverse=True):
        if s.endswith(suf):
            return float(s[:-len(suf)]) * m[suf]
    return float(s)


def kron(ports, rs):
    """Reduced conductance matrix onto `ports` (dense, ports x ports), after
    dropping every connected component that holds no port."""
    import numpy as np
    import scipy.sparse as sp
    import scipy.sparse.linalg as sla
    from scipy.sparse.csgraph import connected_components

    names = sorted({n for a, b, _ in rs for n in (a, b)} | set(ports))
    idx = {n: i for i, n in enumerate(names)}
    n = len(names)
    i = np.array([idx[a] for a, _, _ in rs] + [idx[b] for _, b, _ in rs])
    j = np.array([idx[b] for _, b, _ in rs] + [idx[a] for a, _, _ in rs])
    g = np.array([1.0 / r for _, _, r in rs] * 2)
    A = sp.coo_matrix((g, (i, j)), shape=(n, n)).tocsr()
    _, lab = connected_components(A, directed=False)
    pidx = np.array([idx[p] for p in ports])
    live = np.isin(lab, lab[pidx])
    G = sp.diags(np.asarray(A.sum(axis=1)).ravel()) - A
    keep = np.where(live)[0]
    G = G[keep][:, keep].tocsc()
    pos = {k: m for m, k in enumerate(keep)}
    P = np.array([pos[k] for k in pidx])
    mask = np.ones(len(keep), bool)
    mask[P] = False
    I_ = np.where(mask)[0]
    Gpp = G[P][:, P].toarray()
    if len(I_):
        Gpi = G[P][:, I_]
        Gii = G[I_][:, I_].tocsc()
        lu = sla.splu(Gii)
        X = lu.solve(Gpi.T.toarray())          # Gii^-1 Gip
        Gpp = Gpp - Gpi @ X
    return Gpp


def write_rport(ports, Gr, path, name="esd_ring_rport"):
    n, k = len(ports), 0
    with open(path, "w") as f:
        f.write(f"* {name}: Kron-reduced pad-ring resistance, scripts/esd/pex.py\n")
        f.write(f".subckt {name} {' '.join(ports)}\n")
        for a in range(n):
            for b in range(a + 1, n):
                g = -Gr[a, b]
                if g > G_MIN:
                    f.write(f"R{k} {ports[a]} {ports[b]} {1.0 / g:.6g}\n")
                    k += 1
        f.write(".ends\n")
    return k


def reduce(run):
    pex = os.path.join(run, "pex")
    ports, rs = read_r(os.path.join(pex, "esd_ring_rc.spice"))
    want = {p["name"] for p in json.load(open(os.path.join(pex, "ports.json")))["ports"]}
    if set(ports) != want:
        die(f"extracted ports differ from ports.json: missing {sorted(want - set(ports))[:8]}, "
            f"extra {sorted(set(ports) - want)[:8]}")
    dangling = sorted(set(ports) - {n for a, b, _ in rs for n in (a, b)})
    if dangling:
        die(f"ports that touch no resistor: {dangling[:10]}")
    Gr = kron(ports, rs)
    k = write_rport(ports, Gr, os.path.join(pex, "esd_ring_rport.spice"))
    print(f"pex: {len(rs)} R over {len(ports)} ports -> {k} reduced branches")


def selftest():
    import numpy as np
    # a ladder a-x-y-b of 1+2+3 ohm, with c hanging off x by 4 ohm, and an
    # island with no port: a-b must read 6, a-c 5, b-c 9
    rs = [("a", "x", 1.0), ("x", "y", 2.0), ("y", "b", 3.0), ("x", "c", 4.0),
          ("i1", "i2", 1.0)]
    G = kron(["a", "b", "c"], rs)

    def r2(p, q):                               # two-port resistance from G
        Gs = G.copy()
        k = [0, 1, 2]
        k.remove(q)
        Gs = Gs[np.ix_(k, k)]
        e = np.zeros(2)
        e[k.index(p)] = 1
        return np.linalg.solve(Gs, e)[k.index(p)]
    assert abs(r2(0, 1) - 6) < 1e-9 and abs(r2(0, 2) - 5) < 1e-9 and abs(r2(1, 2) - 9) < 1e-9
    assert abs(spicerun_value("1.5k") - 1500) < 1e-9 and spicerun_value("2meg") == 2e6
    print("pex: selftest passed")


def main():
    a = sys.argv[1:]
    if a == ["--selftest"]:
        return selftest()
    if len(a) != 2 or a[1] not in ("clip", "extract", "reduce", "all"):
        die(__doc__)
    run, stage = os.path.abspath(a[0]), a[1]
    threads = int(os.environ.get("ESD_NJOBS", os.cpu_count() or 4))
    if stage in ("clip", "all"):
        clip(run)
    if stage in ("extract", "all"):
        extract(run, threads)
    if stage in ("reduce", "all"):
        reduce(run)


if __name__ == "__main__":
    main()
