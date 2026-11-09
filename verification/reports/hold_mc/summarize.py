#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Statistics of run_mc.sh results in ps.

    python3 summarize.py <label> <nominal results> <mc results> [<label> <nominal> <mc> ...]

Slack = arrival at capture D minus capture CK minus hold requirement, without the 50 ps clock uncertainty of the SDC.
"""
import math
import sys

UNC = 50.0  # set_clock_uncertainty -hold of the SDC, ps
FIELDS = ("seed", "skew", "c2q", "arr", "hold", "slack", "ok", "inwin", "dslew", "cslew", "tcm")


def load(path):
    rows = []
    for line in open(path):
        w = line.split()
        if w and w[0] == "RESULT":
            r = dict(zip(FIELDS, [float(x) for x in w[1:]]))
            for k in ("skew", "c2q", "arr", "hold", "slack", "dslew", "cslew"):
                r[k] *= 1e12
            rows.append(r)
    return rows


def stats(v):
    n = len(v)
    m = sum(v) / n
    s = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))
    return m, s


def report(label, nom, mc):
    out = ["== %s" % label]
    n0 = nom[0]
    out.append("nominal: skew %.2f  clk-to-Q %.2f  arrival-minus-CK %.2f  hold %.2f  slack %.2f  (D slew %.1f, common node slew %.1f, 20-80)"
               % (n0["skew"], n0["c2q"], n0["arr"], n0["hold"], n0["slack"], n0["dslew"], n0["cslew"]))
    bad = [int(r["seed"]) for r in mc if r["ok"] != 1 or r["inwin"] != 1]
    out.append("runs: %d, functional or window flags failed: %s" % (len(mc), bad or "none"))
    sl = [r["slack"] for r in mc]
    m, s = stats(sl)
    skew_ = (sum((x - m) ** 3 for x in sl) / len(sl)) / s ** 3
    out.append("slack: mean %.2f  sigma %.2f  min %.2f  max %.2f  skewness %.2f" % (m, s, min(sl), max(sl), skew_))
    out.append("sigmas from mean to zero slack: %.1f" % (m / s))
    out.append("sigmas from mean to %.0f ps, the SDC uncertainty kept as margin: %.1f" % (UNC, (m - UNC) / s))
    out.append("min run in sigma below mean: %.1f" % ((m - min(sl)) / s))
    parts = {k: [r[k] for r in mc] for k in ("skew", "c2q", "hold")}
    for k, v in parts.items():
        pm, ps = stats(v)
        out.append("  %-5s mean %.2f  sigma %.2f" % (k, pm, ps))
    # the covariance form of slack = c2q - skew - hold equals the measured sigma by identity, so only the RSS is printed
    out.append("  root sum of squares of the three %.2f, measured %.2f"
               % (math.sqrt(sum(stats(v)[1] ** 2 for v in parts.values())), s))
    out.append("  distinct hold values %d of %d (bisection step 0.063 ps)" % (len({round(x, 4) for x in parts["hold"]}), len(mc)))
    return out


def main():
    a = sys.argv[1:]
    lines = []
    for i in range(0, len(a), 3):
        lines += report(a[i], load(a[i + 1]), load(a[i + 2]))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
