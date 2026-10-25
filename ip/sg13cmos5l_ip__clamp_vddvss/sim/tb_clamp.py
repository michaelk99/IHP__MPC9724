#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Clamp bench: the cell's CDL in ngspice with the PDK models, typical corner.

    tb_clamp.py [--cdl FILE] [--inv-x N] [--clamp-x N] [--vdd V] [--run DIR]

Leakage vdd to vss at -40, 27 and 125 C, at vdd and 1.1 x vdd (1.2 and 1.32 V). A 10 ns vdd edge
0 to vdd must turn the clamp on, a 1 us and a 100 us ramp must not. A 2 kV
HBM current pulse (1.33 A, 10 ns rise) into an unpowered vdd gives the clamp
voltage with ideal metal. Exit 1 on a failed limit.

--inv-x and --clamp-x scale the inverter and the clamp NMOS, to price them.
--vdd sets the supply the clamp sits on, 1.2 V by default. The gate limit follows at 90 %.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))
import spicerun  # noqa: E402

CELL = "sg13cmos5l_ip__clamp_vddvss"
CDL = os.path.join(HERE, "..", "cdl", CELL + ".cdl")
GATE_ON_FRAC, GATE_OFF = 0.9, 0.3  # clamp gate: fraction of vdd that is on, V that is off
I_OFF = 10e-6                     # A, clamp current allowed during a supply ramp
T_ON_MAX = 20e-9                  # s, edge start to gate at GATE_ON


def dut(cdl, inv_x=1.0, clamp_x=1.0):
    """The CDL as an ngspice subckt: M and rppd R cards as X cards, the clamp
    drain behind a 0 V source so its current can be read."""
    out = []
    for ln in open(cdl):
        t = ln.split()
        if not t or t[0].startswith("*"):
            continue
        if t[0][0] in "Mm":
            name, d, g, s, b, model = t[:6]
            p = dict(kv.split("=") for kv in t[6:])
            x = clamp_x if name == "Mclamp" else inv_x if name in ("Minvn", "Minvp") else 1.0
            if x != 1.0:
                w = float(p["w"].rstrip("u")) * x
                p["w"] = "%gu" % w
                p["ng"] = "%d" % round(int(p["ng"]) * x)
            if name == "Mclamp":
                d = "vdd_cl"
                out.append("Vcl vdd vdd_cl 0")
            out.append("X%s %s %s %s %s %s %s" % (name, d, g, s, b, model,
                       " ".join("%s=%s" % kv for kv in p.items())))
        elif t[0][0] in "Rr":
            sub = re.search(r"\$SUB=(\S+)", ln).group(1)
            p = " ".join(kv for kv in t if re.match(r"^(w|l|b)=", kv))
            out.append("X%s %s %s %s rppd %s" % (t[0], t[1], t[2], sub, p))
        else:
            out.append(ln.rstrip())
    return "\n".join(out)


def deck(sub, body, temp=27):
    return "\n".join([
        "* tb_clamp",
        ".lib cornerMOShv.lib mos_tt",
        ".lib cornerRES.lib res_typ",
        sub,
        "Xdut vdd vss iovdd iovss %s" % CELL,
        "Vvss vss 0 0",
        "Viovdd iovdd 0 3.3",
        "Viovss iovss 0 0",
        ".options klu reltol=1e-4 abstol=1e-15 gmin=1e-15",
        ".temp %g" % temp,
        body,
        ".end", ""])


def run(sub, body, tag, rundir, temp=27):
    r = spicerun.run_deck(deck(sub, body, temp), workdir=rundir, tag=tag)
    got = {}
    for m in re.finditer(r"^RESULT (\S+) (\S+)\s*$", r.out, re.M):
        got[m.group(1)] = float(m.group(2))
    if not got:
        raise SystemExit("tb_clamp: %s gave no results, see %s/%s.log"
                         % (tag, rundir, tag))
    return got


def tran(tr, vdd, tstop, step, gate_on):
    return "\n".join([
        "Vvdd vdd 0 pwl(0 0 1n 0 %g %g)" % (1e-9 + tr, vdd),
        ".control",
        "tran %g %g" % (step, tstop),
        "let ig = i(v.xdut.vcl)",
        "meas tran gpk max v(xdut.clamp_g)",
        "meas tran ipk max ig",
        "meas tran ton when v(xdut.clamp_g)=%g rise=1" % gate_on,
        "meas tran toff when v(xdut.clamp_g)=0.6 fall=1",
        "echo RESULT gpk $&gpk",
        "echo RESULT ipk $&ipk",
        "echo RESULT ton $&ton",
        "echo RESULT toff $&toff",
        ".endc"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdl", default=CDL)
    ap.add_argument("--inv-x", type=float, default=1.0)
    ap.add_argument("--clamp-x", type=float, default=1.0)
    ap.add_argument("--vdd", type=float, default=1.2)
    ap.add_argument("--run", default=os.path.join(HERE, "..", "verification", "sim"))
    a = ap.parse_args()
    os.makedirs(a.run, exist_ok=True)
    init = os.path.join(os.environ["PDK_ROOT"], os.environ["PDK"],
                        "libs.tech", "ngspice", ".spiceinit")
    with open(init) as src, open(os.path.join(a.run, ".spiceinit"), "w") as dst:
        dst.write(src.read())
    sub = dut(a.cdl, a.inv_x, a.clamp_x)
    gate_on = GATE_ON_FRAC * a.vdd
    bad = []

    print("Clamp bench, %s, typical models, vdd %g V" % (os.path.basename(a.cdl), a.vdd))
    print("\nLeakage vdd to vss, DC, nA")
    print("%8s %10s %10s %10s" % ("vdd", "-40 C", "27 C", "125 C"))
    for v in (a.vdd, round(1.1 * a.vdd, 4)):
        row = []
        for t in (-40, 27, 125):
            body = "\n".join(["Vvdd vdd 0 %g" % v, ".control", "op",
                              "let ivdd = -i(vvdd)", "echo RESULT ivdd $&ivdd",
                              ".endc"])
            row.append(run(sub, body, "leak_%g_%d" % (v, t), a.run, t)["ivdd"])
        print("%7.2f V %10.4g %10.4g %10.4g" % (v, *[x * 1e9 for x in row]))

    print("\nvdd 0 to V in tr, 27 C: clamp gate, clamp current")
    print("%8s %6s %10s %12s %12s %12s" % ("tr", "V", "gate pk V", "Iclamp pk",
                                           "gate>%.2f at" % gate_on, "gate<0.6 at"))
    cases = (("10n", 10e-9, a.vdd, 4e-6, 0.05e-9), ("1u", 1e-6, a.vdd, 6e-6, 1e-9),
             ("100u", 100e-6, a.vdd, 150e-6, 20e-9))
    res = {}
    for name, tr, v, tstop, step in cases:
        r = run(sub, tran(tr, v, tstop, step, gate_on), "ramp_" + name, a.run)
        res[name] = r
        ton = "%.2f ns" % ((r["ton"] - 1e-9) * 1e9) if "ton" in r else "never"
        toff = "%.3f us" % (r["toff"] * 1e6) if "toff" in r else "-"
        print("%8s %6.2f %10.3f %10.4g A %12s %12s" % (name, v, r["gpk"], r["ipk"],
                                                     ton, toff))
    r = res["10n"]
    if r["gpk"] < gate_on or "ton" not in r or r["ton"] - 1e-9 > T_ON_MAX:
        bad.append("a 10 ns edge leaves the gate under %.2f V within %g ns"
                   % (gate_on, T_ON_MAX * 1e9))
    for name in ("1u", "100u"):
        r = res[name]
        if r["gpk"] > GATE_OFF or r["ipk"] > I_OFF:
            bad.append("a %s ramp lifts the gate to %.3f V, %.3g A"
                       % (name, r["gpk"], r["ipk"]))

    # 2 kV HBM: 1.33 A peak, 10 ns rise, 150 ns decay, into an unpowered vdd
    body = "\n".join([
        "Vvdd vdd_src 0 0",
        "Rvdd vdd_src vdd 1e9",
        "Ihbm 0 vdd exp(0 1.33 0 3n 10n 150n)",
        ".control", "tran 0.05n 600n",
        "meas tran vpk max v(vdd)",
        "meas tran ipk max i(v.xdut.vcl)",
        "echo RESULT vpk $&vpk", "echo RESULT ipk $&ipk", ".endc"])
    r = run(sub, body, "hbm", a.run)
    print("\n2 kV HBM into vdd, 1.33 A: vdd peak %.3f V, clamp current peak %.3f A"
          % (r["vpk"], r["ipk"]))

    for b in bad:
        print("tb_clamp: FAIL " + b)
    if not bad:
        print("\ntb_clamp: ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
