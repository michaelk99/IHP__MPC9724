#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Every marker of one KLayout DRC run directory, and the verdict.

    drc_report.py <run_dir>                  pass on no marker outside the density table
    drc_report.py <run_dir> --ref <ref_dir> --cell X0,X1
                                             pass when no category grows against the
                                             reference and no new marker enters x X0..X1

The run must have finished: the run log carries its total time and every
table log ends in "completed in" (the antenna table ends at its last rule).
The density table's rules are global densities, met at chip level with fill,
and are listed but not failed. They are read from the run's density log, not
typed here. Markers compare by category and geometry, so a row and its
reference must place the shared cells at the same coordinates. A neighbour's
own marker can come back with another extent when the cell next to it changes
(an Activ guard strip that a filler continues and the clamp does not), so the
row passes on equal counts per category, and fails on any new marker that
reaches into the clamp's own x range.
"""
import argparse
import collections
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET


def markers(d):
    out = collections.Counter()
    dbs = glob.glob(os.path.join(d, "*.lyrdb"))
    for db in dbs:
        for it in ET.parse(db).getroot().iter("item"):
            cat = it.findtext("category", "").strip().strip("'")
            vals = tuple(sorted(v.text or "" for v in it.iter("value")))
            out[(cat, vals)] += 1
    return dbs, out


def finished(d):
    bad = []
    runs = glob.glob(os.path.join(d, "drc_run_*.log"))
    if not runs or not all("Total DRC Run time" in open(f, errors="replace").read() for f in runs):
        bad.append("the run log has no total run time")
    tables = [f for f in glob.glob(os.path.join(d, "*.log"))
              if not os.path.basename(f).startswith("drc_run_") and not f.endswith(".drc.log")]
    if not tables:
        bad.append("no table logs")
    for f in tables:
        text = open(f, errors="replace").read()
        if "Traceback" in text or "Exception" in text:
            bad.append("%s raised" % os.path.basename(f))
        lines = [ln for ln in text.splitlines() if ln.strip()]
        end = lines[-1] if lines else ""
        if "completed in" not in end and not (f.endswith("_antenna.log") and "Ant." in end):
            bad.append("%s stopped early" % os.path.basename(f))
    density = set()
    for f in tables:
        if f.endswith("_density.log"):
            density |= set(re.findall(r"Executing rule (\S+)", open(f).read()))
    return bad, tables, density


def show(cnt, title):
    cats = collections.Counter()
    for (cat, _), n in cnt.items():
        cats[cat] += n
    print("%s: %d markers %s" % (title, sum(cats.values()),
                                 " ".join("%s=%d" % kv for kv in sorted(cats.items()))))
    for (cat, vals), n in sorted(cnt.items()):
        print("    %-14s %s%s" % (cat, "; ".join(v[:90] for v in vals), " x%d" % n if n > 1 else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--ref")
    ap.add_argument("--cell", help="X0,X1 of the clamp in the row")
    a = ap.parse_args()
    bad, tables, density = finished(a.run)
    dbs, cnt = markers(a.run)
    if not dbs:
        bad.append("no report database")
    print("%s: %d tables" % (a.run, len(tables)))
    show(cnt, "markers")
    if a.ref:
        rbad, _, rdens = finished(a.ref)
        bad += ["reference: " + b for b in rbad]
        density |= rdens
        _, ref = markers(a.ref)
        show(ref, "reference markers")
        new = cnt - ref
        gone = ref - cnt
        show(new, "markers the reference does not have")
        show(gone, "reference markers this run does not have")
        x0, x1 = (float(v) for v in a.cell.split(","))
        cats = collections.Counter()
        for (cat, _), n in cnt.items():
            cats[cat] += n
        for (cat, _), n in ref.items():
            cats[cat] -= n
        fail = {}
        for cat, n in cats.items():
            if n > 0 and cat not in density:
                fail[(cat, ("%d more than the reference" % n,))] = n
        for k, n in new.items():
            xs = [float(v) for v in re.findall(r"(-?[\d.]+),-?[\d.]+", " ".join(k[1]))]
            if k[0] not in density and xs and max(xs) > x0 and min(xs) < x1:
                fail[k] = n
    else:
        fail = {k: n for k, n in cnt.items() if k[0] not in density}
    dens = sorted({k[0] for k in cnt if k[0] in density})
    print("density table rules, global, not failed here: %s" % (", ".join(dens) or "none"))
    for b in bad:
        print("FAIL " + b)
    for (cat, vals), n in sorted(fail.items()):
        print("FAIL %s at %s" % (cat, "; ".join(v[:90] for v in vals)))
    ok = not bad and not fail
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
