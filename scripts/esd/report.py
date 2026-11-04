# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Ported from OpenBLAU 8f25e634, scripts/esd/report.py
# Description: summary of the HBM zap matrix: worst voltages per device class
"""Reads <run>/hbm_r<ron>[_ideal].json (hbm.py) and prints, per zap and over
the matrix, the extreme voltages across the three classes of device a zap can
break:

  pad   the zapped pin against the grounded reference pins
  LV    1.2 V devices: core-ring vdd-vss, every pad slot's vdd-vss, c2p
        and p2c against the pad slot's vdd and vss (the pad cell's level
        shifters) and against the core-ring point the core cell sits on
        (BUFX3, AND2X1, the input gate)
  LV15  the same quantities on the VDDA segment's pad slots and at dsm2's
        pins (vddadsm, vssdsm, and the analog pins vi, vcm, ibias_test behind
        dsm2's own protection, in_<slot>, against them): 1.5 V devices, same
        oxide, same indicative limit
  PIN   dsm2's analog pin itself (padres) against vddadsm and vssdsm. Only
        the poly resistors of the two protection cells sit on it, no gate, so
        it is reported and not gated
  HV    3.3 V devices, the pad cells: iovdd-iovss, pad against both IO rails,
        the secondary-protected input node and the analog pads' padres
        against both IO rails, and the vdd-to-iovss rail clamp

  python3 scripts/esd/report.py <run> [--ron 1] [--ideal-ring] [--pkg-gnd] [--json OUT]
  python3 scripts/esd/report.py <run> --tables [--pkg-gnd]

LIMIT_LV / LIMIT_HV are INDICATIVE transient oxide limits for the 100 ns
scale, not foundry numbers: the table reports margin against them and says so.
"""

import argparse
import json
import os
import re
import sys

LIMIT_LV = 4.5      # V, 1.2 V thin-oxide gate, HBM time scale: indicative, unconfirmed
LIMIT_15 = 4.5      # V, the 1.5 V nodes use the same thin oxide: same number, not scaled
LIMIT_HV = 10.0     # V, 3.3 V thick-oxide gate: indicative, unconfirmed

LV = re.compile(r"^(core_vdd_vss_\d|dsm_vdda_vss|dcp_vdda_vss|vdda?_vss@.*|(c2p|p2c)_(vss|core)@.*|"
                r"(vdda?|core)_(c2p|p2c)@.*|in_core@.*|core_in@.*)$")
HV = re.compile(r"^(iovdd_iovss@.*|pad_iovss@.*|pad_iovdd@.*|secprot_iovss@.*|"
                r"iovdd_secprot@.*|vdda?_iovss@.*|padres_iovss@.*|iovdd_padres@.*)$")
RAIL = re.compile(r"^(core_vdd_vss_\d|vdd_vss@.*)$")     # the core rail itself
RAIL15 = re.compile(r"^(dsm_vdda_vss|dcp_vdda_vss|vdda_vss@.*)$")      # the VDDA rail, decap_vdda's straps too
PIN = re.compile(r"^(padres_core|core_padres)@.*$")       # dsm2's analog pin, ahead of its protection
DIN = re.compile(r"^(in_core|core_in)@.*$")               # the same pin behind it, part of LV15


def is15(k, seg):
    """A quantity of the 1.5 V domain: dsm2's pins or a segment slot's."""
    return k in ("dsm_vdda_vss", "dcp_vdda_vss") or k.split("@")[-1] in seg


def worst(d, rx, keep=lambda k: True):
    """(|V|, quantity, V) of the largest excursion among keys matching rx."""
    best = (0.0, None, 0.0)
    for k, hl in d.items():
        if not rx.match(k) or not keep(k):
            continue
        for v in hl:
            if abs(v) > best[0]:
                best = (abs(v), k, v)
    return best


def summarize(res):
    seg = set(res.get("seg", []))
    rows = []
    for t, d in sorted(res["zaps"].items()):
        if "error" in d:
            rows.append(dict(zap=t, error=True))
            continue
        zap, ref, pol = t.split("__")[:3]
        lv = worst(d, LV, lambda k: not is15(k, seg))
        l15 = worst(d, LV, lambda k: is15(k, seg))
        hv, rail, r15, pin, din = worst(d, HV), worst(d, RAIL), worst(d, RAIL15), worst(d, PIN), worst(d, DIN)
        rows.append(dict(zap=zap, ref=ref, pol="+" if pol == "p" else "-",
                         pad_max=d["pad"][0], pad_min=d["pad"][1],
                         ipk=max(abs(x) for x in d["i_zap"]),
                         lv=lv[2], lv_node=lv[1], lv15=l15[2], lv15_node=l15[1],
                         hv=hv[2], hv_node=hv[1],
                         rail=rail[2], rail_node=rail[1], rail15=r15[2], rail15_node=r15[1],
                         pin=pin[2], pin_node=pin[1], din=din[2], din_node=din[1],
                         lv_over=sorted(k for k, hl in d.items() if LV.match(k)
                                        and max(map(abs, hl)) > (LIMIT_15 if is15(k, seg)
                                                                 else LIMIT_LV))))
    return rows


RONS = (0.5, 1, 2, 4)


def band(vals, fmt="{:.1f}"):
    """'a .. b' over RON, one number when the band is under 0.05 V."""
    lo, hi = min(vals), max(vals)
    return fmt.format(lo) if hi - lo < 0.05 else f"{fmt.format(lo)} .. {fmt.format(hi)}"


def tables(run, pkg):
    """Markdown: the summary per RON, per zapped pin, and every LV node over
    the limit, from <run>/hbm_r<ron>[_pkg].json and the RON 1 ideal ring."""
    sfx = "_pkg" if pkg else ""
    res = {}
    for r in RONS:
        f = os.path.join(run, f"hbm_r{r:g}{sfx}.json")
        if os.path.isfile(f):
            res[r] = json.load(open(f))
    ideal = os.path.join(run, f"hbm_r1_ideal{sfx}.json")
    ideal = json.load(open(ideal)) if os.path.isfile(ideal) else None
    rows = {r: [x for x in summarize(d) if "error" not in x] for r, d in res.items()}
    rons = sorted(res)
    print("| | " + " | ".join(f"RON {r:g}" for r in rons) + " |")
    print("|---|" + "---|" * len(rons))

    def line(name, f):
        print(f"| {name} | " + " | ".join(f(rows[r], res[r]) for r in rons) + " |")

    def worst_of(rw, key):
        return max(rw, key=lambda x: abs(x[key]))
    line("zaps run / of", lambda rw, d: f"{len(rw)} / {len(d['zaps'])}")
    line("retried: 0.02 ns step / trap / cshunt", lambda rw, d: " / ".join(str(sum(
        str(z.get("retry", "")).startswith(k) or (k == "cshunt" and "cshunt" in z)
        for z in d["zaps"].values())) for k in ("tstep", "method", "cshunt")))
    line("still rising past half the window", lambda rw, d: str(sum(
        "error" not in z and z["late_rise"][0] > 0.1 for z in d["zaps"].values())))
    line("pad, max / min V", lambda rw, d: f"{max(x['pad_max'] for x in rw):.1f} / "
         f"{min(x['pad_min'] for x in rw):.1f}")
    for key, nm in (("lv", "worst LV V"), ("lv15", "worst 1.5 V node V"), ("hv", "worst HV V"),
                    ("rail", "core rail, worst V"), ("rail15", "VDDA rail, worst V"),
                    ("din", "dsm2 analog pin behind its protection, worst V"),
                    ("pin", "dsm2 analog pin ahead of its protection, worst V")):
        line(nm, lambda rw, d, key=key: f"{worst_of(rw, key)[key]:.2f}")
        line(nm + ": node, zap", lambda rw, d, key=key: (lambda x: (
            f"`{x[key + '_node']}`, `{x['zap']}` {x['pol']} vs {x['ref']}"))(
            worst_of(rw, key)))
    line(f"zaps with an LV or 1.5 V node over {LIMIT_LV} V",
         lambda rw, d: str(sum(bool(x["lv_over"]) for x in rw)))
    print()
    # per zapped pin
    pinsl = sorted({x["zap"] for x in rows[rons[0]]})
    irows = [x for x in summarize(ideal) if "error" not in x] if ideal else []
    print("| pad | pad max V | pad min V | worst LV V | worst 1.5 V node V | worst HV V "
          "| ideal ring: max / min V |")
    print("|---|---|---|---|---|---|---|")
    for p in pinsl:
        def ext(rw, key, f):
            return f([x[key] for x in rw if x["zap"] == p])
        pmax = [ext(rows[r], "pad_max", max) for r in rons]
        pmin = [ext(rows[r], "pad_min", min) for r in rons]
        lv = [ext(rows[r], "lv", lambda v: max(v, key=abs)) for r in rons]
        l15 = [ext(rows[r], "lv15", lambda v: max(v, key=abs)) for r in rons]
        hv = [ext(rows[r], "hv", lambda v: max(v, key=abs)) for r in rons]
        idl = (f"{ext(irows, 'pad_max', max):.1f} / {ext(irows, 'pad_min', min):.1f}"
               if any(x["zap"] == p for x in irows) else "")
        print(f"| `{p}` | {band(pmax)} | {band(pmin)} | {band(lv)} | {band(l15)} | {band(hv)} | {idl} |")
    print()
    # every zap with a quantity over its limit: the worst one per RON, and
    # how many quantities are over
    seg = set(next(iter(res.values())).get("seg", []))
    for rx, lim, nm, keep in ((LV, LIMIT_LV, "LV", lambda k: not is15(k, seg)),
                              (LV, LIMIT_15, "1.5 V", lambda k: is15(k, seg)),
                              (HV, LIMIT_HV, "HV", lambda k: True)):
        per = {}
        for r in rons:
            for t, z in res[r]["zaps"].items():
                if "error" in z:
                    continue
                zap, ref, pol = t.split("__")[:3]
                q = {k: max(hl, key=abs) for k, hl in z.items() if rx.match(k) and keep(k)}
                if not q:
                    continue
                k = max(q, key=lambda k: abs(q[k]))
                per.setdefault((zap, ref, pol), {})[r] = (q[k], k, sum(abs(v) > lim for v in q.values()))
        hit = {k: v for k, v in per.items() if any(abs(x[0]) > lim for x in v.values())}
        print(f"{nm}: {len(hit)} zaps put a quantity over {lim} V at some RON; per RON " +
              ", ".join(f"{r:g}: {sum(abs(v[r][0]) > lim for v in per.values() if r in v)}"
                        for r in rons))
        if not hit or nm == "HV":         # HV: the counts, the summary has the worst
            print()
            continue
        print()
        print("| zap | worst quantity | " + " | ".join(f"RON {r:g}" for r in rons) +
              f" | quantities over {lim} V |")
        print("|---|---|" + "---|" * len(rons) + "---|")
        for k, v in sorted(hit.items(), key=lambda kv: -max(abs(x[0]) for x in kv[1].values())):
            zap, ref, pol = k
            qs = sorted({x[1] for x in v.values()})
            ns = [x[2] for x in v.values()]
            print(f"| `{zap}` {'+' if pol == 'p' else '-'} vs {ref} | "
                  f"{', '.join(f'`{q}`' for q in qs)} | " +
                  " | ".join(f"{v[r][0]:.2f}" if r in v else "" for r in rons) +
                  f" | {min(ns)}{'' if min(ns) == max(ns) else f' .. {max(ns)}'} |")
        print()


def selftest():
    """--fail-over exits 1 on an errored zap and on a run where none ran."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        z = dict(pad=[1.0, -1.0], i_zap=[1.0, -1.0], late_rise=[0.0, 0.0], core_vdd_vss_0=[1.0, -1.0])
        for tag, zaps, want in (("ok", {"a__vss__p__r1": z}, 0),
                                ("err", {"a__vss__p__r1": z, "b__vss__p__r1": {"error": "x"}}, 1),
                                ("none", {"a__vss__p__r1": {"error": "x"}}, 1)):
            os.makedirs(os.path.join(d, tag))
            json.dump(dict(ron=1.0, vhbm=2000.0, ideal_ring=False, zaps=zaps),
                      open(os.path.join(d, tag, "hbm_r1.json"), "w"))
            sys.argv = ["report.py", os.path.join(d, tag), "--fail-over"]
            if main() != want:
                die(f"selftest: {tag} did not exit {want}")
    print("report: selftest passed")


def die(msg):
    sys.stderr.write(f"report: {msg}\n")
    sys.exit(1)


def main():
    if sys.argv[1:] == ["--selftest"]:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run")
    ap.add_argument("--ron", type=float, default=1.0)
    ap.add_argument("--ideal-ring", action="store_true")
    ap.add_argument("--pkg-gnd", action="store_true")
    ap.add_argument("--json")
    ap.add_argument("--clamp", metavar="SLOT", help="the run with hbm.py --clamp SLOT")
    ap.add_argument("--no-clamp", action="append", default=[], choices=("clamp", "clamp_vdda"),
                    help="the run with hbm.py --no-clamp")
    ap.add_argument("--fail-over", action="store_true",
                    help="exit 1 when a zap errored, or a 1.2 V or 1.5 V node is over its limit. dsm2's pin ahead of its protection and HV are not gated")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--tables", action="store_true", help="markdown over the RON sweep")
    a = ap.parse_args()
    if a.tables:
        return tables(a.run, a.pkg_gnd)
    name = (f"hbm_r{a.ron:g}{'_ideal' if a.ideal_ring else ''}"
            f"{'_pkg' if a.pkg_gnd else ''}{'_clamp_' + a.clamp if a.clamp else ''}"
            f"{''.join('_no_' + c for c in a.no_clamp)}.json")
    res = json.load(open(os.path.join(a.run, name)))
    rows = summarize(res)
    ok = [r for r in rows if "error" not in r]
    print(f"report: {name}: {len(ok)} of {len(rows)} zaps, {res['vhbm']:.0f} V, "
          f"RON {res['ron']} ohm{', ideal ring' if res['ideal_ring'] else ''}"
          f"{', VSS = IOVSS in the package' if res.get('pkg_gnd') else ''}")
    if not ok:
        print("report: no zap ran")
        return 1
    hdr = f"{'zap':>7} {'ref':>5} pol  pad max/min V   Ipk A    V  (node)"
    for title, key in (("LV (1.2 V devices)", "lv"), ("1.5 V nodes", "lv15"),
                       ("HV (3.3 V devices)", "hv")):
        lim = LIMIT_HV if key == "hv" else LIMIT_LV
        print(f"\nworst {title}, indicative limit {lim} V:\n{hdr}")
        for r in sorted(ok, key=lambda r: -abs(r[key]))[:a.top]:
            print(f"{r['zap']:>7} {r['ref']:>5}  {r['pol']}  {r['pad_max']:7.2f} "
                  f"{r['pad_min']:7.2f}  {r['ipk']:5.2f}  {r[key]:6.2f} ({r[key + '_node']})")
    lv = max(ok, key=lambda r: abs(r["lv"]))
    l15 = max(ok, key=lambda r: abs(r["lv15"]))
    hv = max(ok, key=lambda r: abs(r["hv"]))
    rail = max(ok, key=lambda r: abs(r["rail"]))
    din = max(ok, key=lambda r: abs(r["din"]))
    pin = max(ok, key=lambda r: abs(r["pin"]))
    over = [r for r in ok if r["lv_over"]]
    pmax = max(r["pad_max"] for r in ok)
    pmin = min(r["pad_min"] for r in ok)
    summ = dict(file=name, vhbm=res["vhbm"], ron=res["ron"], ideal_ring=res["ideal_ring"],
                pkg_gnd=res.get("pkg_gnd", False),
                zaps=len(rows), failed=len(rows) - len(ok), pad_max=pmax, pad_min=pmin,
                lv_worst=dict(v=lv["lv"], node=lv["lv_node"],
                              zap=f"{lv['zap']}:{lv['ref']}:{lv['pol']}"),
                lv15_worst=dict(v=l15["lv15"], node=l15["lv15_node"],
                                zap=f"{l15['zap']}:{l15['ref']}:{l15['pol']}"),
                hv_worst=dict(v=hv["hv"], node=hv["hv_node"],
                              zap=f"{hv['zap']}:{hv['ref']}:{hv['pol']}"),
                rail_worst=dict(v=rail["rail"], node=rail["rail_node"],
                                zap=f"{rail['zap']}:{rail['ref']}:{rail['pol']}"),
                dsm2_in_worst=dict(v=din["din"], node=din["din_node"],
                                   zap=f"{din['zap']}:{din['ref']}:{din['pol']}"),
                dsm2_pin_worst=dict(v=pin["pin"], node=pin["pin_node"],
                                    zap=f"{pin['zap']}:{pin['ref']}:{pin['pol']}"),
                lv_over_limit={f"{r['zap']}:{r['ref']}:{r['pol']}": r["lv_over"] for r in over},
                limits=dict(lv=LIMIT_LV, lv15=LIMIT_15, hv=LIMIT_HV, source="indicative, unconfirmed"),
                rows=rows)
    print(f"\nreport: pad {pmax:.2f} / {pmin:.2f} V; LV worst {lv['lv']:.2f} V at {lv['lv_node']} "
          f"({summ['lv_worst']['zap']}); 1.5 V worst {l15['lv15']:.2f} V at {l15['lv15_node']} "
          f"({summ['lv15_worst']['zap']}); HV worst {hv['hv']:.2f} V at {hv['hv_node']} "
          f"({summ['hv_worst']['zap']}); core rail worst {rail['rail']:.2f} V at "
          f"{rail['rail_node']} ({summ['rail_worst']['zap']}); dsm2 analog pin behind its protection "
          f"{din['din']:.2f} V at {din['din_node']} ({summ['dsm2_in_worst']['zap']}), ahead of it "
          f"{pin['pin']:.2f} V at {pin['pin_node']} ({summ['dsm2_pin_worst']['zap']}, not gated); "
          f"{len(over)} zaps put an LV or 1.5 V node over {LIMIT_LV} V")
    if a.json:
        json.dump(summ, open(a.json, "w"), indent=1)
    return 1 if a.fail_over and (over or len(ok) < len(rows)) else 0


if __name__ == "__main__":
    sys.exit(main())
