# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Ported from OpenBLAU 8f25e634, scripts/esd/report.py
# Description: summary of the HBM zap matrix: worst voltages per device class
"""Reads <run>/hbm_r<ron>[_ideal].json (hbm.py) and prints, per zap and over
the matrix, the extreme voltages across the three classes of device a zap can
break:

  pad   the zapped pin against the grounded reference pins
  LV    1.2 V devices: core-ring vdd-vss, every pad slot's vdd-vss, c2p,
        c2p_en and p2c against the pad slot's vdd and vss (the pad cell's
        level shifters) and against the core-ring point the core cell sits
        on (BUFX3, TIELO, the input gate)
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
LIMIT_HV = 10.0     # V, 3.3 V thick-oxide gate: indicative, unconfirmed

LV = re.compile(r"^(core_vdd_vss_\d|vdd_vss@.*|(c2p|c2pen|p2c)_(vss|core)@.*|"
                r"(vdd|core)_(c2p|c2pen|p2c)@.*)$")
HV = re.compile(r"^(iovdd_iovss@.*|pad_iovss@.*|pad_iovdd@.*|secprot_iovss@.*|"
                r"iovdd_secprot@.*|vdd_iovss@.*|padres_iovss@.*|iovdd_padres@.*)$")
RAIL = re.compile(r"^(core_vdd_vss_\d|vdd_vss@.*)$")     # the core rail itself


def worst(d, rx):
    """(|V|, quantity, V) of the largest excursion among keys matching rx."""
    best = (0.0, None, 0.0)
    for k, hl in d.items():
        if not rx.match(k):
            continue
        for v in hl:
            if abs(v) > best[0]:
                best = (abs(v), k, v)
    return best


def summarize(res):
    rows = []
    for t, d in sorted(res["zaps"].items()):
        if "error" in d:
            rows.append(dict(zap=t, error=True))
            continue
        zap, ref, pol = t.split("__")[:3]
        lv, hv, rail = worst(d, LV), worst(d, HV), worst(d, RAIL)
        rows.append(dict(zap=zap, ref=ref, pol="+" if pol == "p" else "-",
                         pad_max=d["pad"][0], pad_min=d["pad"][1],
                         ipk=max(abs(x) for x in d["i_zap"]),
                         lv=lv[2], lv_node=lv[1], hv=hv[2], hv_node=hv[1],
                         rail=rail[2], rail_node=rail[1],
                         lv_over=sorted(k for k, hl in d.items() if LV.match(k)
                                        and max(map(abs, hl)) > LIMIT_LV)))
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
    for key, nm in (("lv", "worst LV V"), ("hv", "worst HV V"), ("rail", "core rail, worst V")):
        line(nm, lambda rw, d, key=key: f"{worst_of(rw, key)[key]:.2f}")
        line(nm + ": node, zap", lambda rw, d, key=key: (lambda x: (
            f"`{x[key + '_node']}`, `{x['zap']}` {x['pol']} vs {x['ref']}"))(
            worst_of(rw, key)))
    line(f"zaps with an LV node over {LIMIT_LV} V",
         lambda rw, d: str(sum(bool(x["lv_over"]) for x in rw)))
    print()
    # per zapped pin
    pinsl = sorted({x["zap"] for x in rows[rons[0]]})
    irows = [x for x in summarize(ideal) if "error" not in x] if ideal else []
    print("| pad | pad max V | pad min V | worst LV V | worst HV V | ideal ring: max / min V |")
    print("|---|---|---|---|---|---|")
    for p in pinsl:
        def ext(rw, key, f):
            return f([x[key] for x in rw if x["zap"] == p])
        pmax = [ext(rows[r], "pad_max", max) for r in rons]
        pmin = [ext(rows[r], "pad_min", min) for r in rons]
        lv = [ext(rows[r], "lv", lambda v: max(v, key=abs)) for r in rons]
        hv = [ext(rows[r], "hv", lambda v: max(v, key=abs)) for r in rons]
        idl = (f"{ext(irows, 'pad_max', max):.1f} / {ext(irows, 'pad_min', min):.1f}"
               if any(x["zap"] == p for x in irows) else "")
        print(f"| `{p}` | {band(pmax)} | {band(pmin)} | {band(lv)} | {band(hv)} | {idl} |")
    print()
    # every zap with a quantity over its limit: the worst one per RON, and
    # how many quantities are over
    for rx, lim, nm in ((LV, LIMIT_LV, "LV"), (HV, LIMIT_HV, "HV")):
        per = {}
        for r in rons:
            for t, z in res[r]["zaps"].items():
                if "error" in z:
                    continue
                zap, ref, pol = t.split("__")[:3]
                q = {k: max(hl, key=abs) for k, hl in z.items() if rx.match(k)}
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run")
    ap.add_argument("--ron", type=float, default=1.0)
    ap.add_argument("--ideal-ring", action="store_true")
    ap.add_argument("--pkg-gnd", action="store_true")
    ap.add_argument("--json")
    ap.add_argument("--clamp", metavar="SLOT", help="the run with hbm.py --clamp SLOT")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--tables", action="store_true", help="markdown over the RON sweep")
    a = ap.parse_args()
    if a.tables:
        return tables(a.run, a.pkg_gnd)
    name = (f"hbm_r{a.ron:g}{'_ideal' if a.ideal_ring else ''}"
            f"{'_pkg' if a.pkg_gnd else ''}{'_clamp_' + a.clamp if a.clamp else ''}.json")
    res = json.load(open(os.path.join(a.run, name)))
    rows = summarize(res)
    ok = [r for r in rows if "error" not in r]
    print(f"report: {name}: {len(ok)} of {len(rows)} zaps, {res['vhbm']:.0f} V, "
          f"RON {res['ron']} ohm{', ideal ring' if res['ideal_ring'] else ''}"
          f"{', VSS = IOVSS in the package' if res.get('pkg_gnd') else ''}")
    hdr = (f"{'zap':>7} {'ref':>5} pol  pad max/min V   Ipk A    LV V  (node)"
           "            HV V  (node)")
    for title, key in (("LV (1.2 V devices)", "lv"), ("HV (3.3 V devices)", "hv")):
        lim = LIMIT_LV if key == "lv" else LIMIT_HV
        print(f"\nworst {title}, indicative limit {lim} V:\n{hdr}")
        for r in sorted(ok, key=lambda r: -abs(r[key]))[:a.top]:
            print(f"{r['zap']:>7} {r['ref']:>5}  {r['pol']}  {r['pad_max']:7.2f} "
                  f"{r['pad_min']:7.2f}  {r['ipk']:5.2f}  {r['lv']:6.2f} ({r['lv_node']:<16}) "
                  f"{r['hv']:6.2f} ({r['hv_node']})")
    lv = max(ok, key=lambda r: abs(r["lv"]))
    hv = max(ok, key=lambda r: abs(r["hv"]))
    rail = max(ok, key=lambda r: abs(r["rail"]))
    over = [r for r in ok if r["lv_over"]]
    pmax = max(r["pad_max"] for r in ok)
    pmin = min(r["pad_min"] for r in ok)
    summ = dict(file=name, vhbm=res["vhbm"], ron=res["ron"], ideal_ring=res["ideal_ring"],
                pkg_gnd=res.get("pkg_gnd", False),
                zaps=len(rows), failed=len(rows) - len(ok), pad_max=pmax, pad_min=pmin,
                lv_worst=dict(v=lv["lv"], node=lv["lv_node"],
                              zap=f"{lv['zap']}:{lv['ref']}:{lv['pol']}"),
                hv_worst=dict(v=hv["hv"], node=hv["hv_node"],
                              zap=f"{hv['zap']}:{hv['ref']}:{hv['pol']}"),
                rail_worst=dict(v=rail["rail"], node=rail["rail_node"],
                                zap=f"{rail['zap']}:{rail['ref']}:{rail['pol']}"),
                lv_over_limit={f"{r['zap']}:{r['ref']}:{r['pol']}": r["lv_over"] for r in over},
                limits=dict(lv=LIMIT_LV, hv=LIMIT_HV, source="indicative, unconfirmed"),
                rows=rows)
    print(f"\nreport: pad {pmax:.2f} / {pmin:.2f} V; LV worst {lv['lv']:.2f} V at {lv['lv_node']} "
          f"({summ['lv_worst']['zap']}); HV worst {hv['hv']:.2f} V at {hv['hv_node']} "
          f"({summ['hv_worst']['zap']}); core rail worst {rail['rail']:.2f} V at "
          f"{rail['rail_node']} ({summ['rail_worst']['zap']}); {len(over)} zaps put an LV "
          f"node over {LIMIT_LV} V")
    if a.json:
        json.dump(summ, open(a.json, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
