#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""The verdict of one KLayout DRC output directory, as run_drc.py leaves it.

    drc_verdict.py verification/drc/<cell>.klayout.drc --expect Pad.d1R=40,Pad.fR_TM1=38,NW.d=2
    drc_verdict.py verification/drc/precheck/<cell>.klayout.drc --no-density --out verdict.txt
    drc_verdict.py --self-test

Passes only when every table ran to the end, nothing raised, every marker
category and count is exactly the expected one (none by default), and every
global density sits inside its limits. Exit code 0 on pass, 1 on fail.

Every *.lyrdb in the directory is counted, not only the merged *_full.lyrdb,
and density is read from *_density.log, because the merged database does not
carry the density rules.
"""
import argparse
import collections
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

DENSITY_RE = re.compile(r"(\w+)\s+Density % =\s*([\d.]+)%\s*\[([^\]]*)\]")
LIMIT_RE = re.compile(r"(Min|Max) = ([\d.]+)%")


def parse_expect(text):
    expect = {}
    for item in filter(None, text.split(",")):
        cat, _, n = item.partition("=")
        expect[cat.strip()] = int(n)
    return expect


def count_markers(d):
    """Markers per category over every report database in d."""
    counts = collections.Counter()
    dbs = sorted(glob.glob(os.path.join(d, "*.lyrdb")))
    for db in dbs:
        for item in ET.parse(db).getroot().iter("item"):
            counts[item.findtext("category", "").strip().strip("'")] += 1
    return dbs, counts


def last_line(path):
    lines = [line for line in open(path, errors="replace").read().splitlines() if line.strip()]
    return lines[-1] if lines else ""


def verdict(d, expect, density=True):
    """(ok, report lines) for the DRC output directory d."""
    lines, ok = [], True

    def fail(msg):
        nonlocal ok
        ok = False
        lines.append("FAIL: " + msg)

    logs = sorted(glob.glob(os.path.join(d, "*.log")))
    runs = [f for f in logs if os.path.basename(f).startswith("drc_run_")]
    tables = [f for f in logs if "drctmp_" in os.path.basename(f)]
    if not runs:
        fail("no drc_run_*.log in %s" % d)
    if not tables:
        fail("no table log in %s" % d)

    for f in logs:
        text = open(f, errors="replace").read()
        if "Traceback" in text or "Exception" in text:
            fail("%s raised" % os.path.basename(f))
    for f in runs:
        if "Total DRC Run time" not in open(f, errors="replace").read():
            fail("%s never finished" % os.path.basename(f))
    for f in tables:
        end = last_line(f)
        if "completed in" in end:
            continue
        # The antenna table never prints a completion line, it stops at its last rule.
        if f.endswith("_antenna.log") and end.endswith("Executing rule Ant.i"):
            continue
        fail("%s stopped early: %s" % (os.path.basename(f), end.split(" : ")[-1]))
    lines.append("tables: %d logs, all completed" % len(tables) if ok else "tables: %d logs" % len(tables))

    dbs, counts = count_markers(d)
    if not dbs:
        fail("no report database in %s" % d)
    for cat in sorted(set(counts) | set(expect)):
        got, want = counts.get(cat, 0), expect.get(cat, 0)
        if got != want:
            fail("%s: %d markers, expected %d" % (cat, got, want))
    lines.append("markers: %d in %d categories %s" % (
        sum(counts.values()), len(counts), ", ".join("%s=%d" % kv for kv in sorted(counts.items()))))

    if density:
        dlogs = [f for f in tables if f.endswith("_density.log")]
        if not dlogs:
            fail("no density log, pass --no-density for a run without the density table")
        for f in dlogs:
            found = DENSITY_RE.findall(open(f, errors="replace").read())
            if not found:
                fail("%s holds no density figure" % os.path.basename(f))
            for layer, pct, limits in found:
                pct = float(pct)
                lim = {k: float(v) for k, v in LIMIT_RE.findall(limits)}
                inside = lim.get("Min", 0.0) <= pct <= lim.get("Max", 100.0)
                note = "%s %.2f %% [%s]" % (layer, pct, limits.strip())
                if inside:
                    lines.append("density: " + note)
                else:
                    fail("density " + note)

    lines.append("PASS" if ok else "FAIL")
    return ok, lines


def self_test():
    import shutil
    import tempfile

    def fixture(tables=("activ", "antenna", "metal1"), items=(), density=(("Metal4", 57.19, 35.0, 60.0),),
                main="Total DRC Run time: 959.22 seconds", extra=None):
        d = tempfile.mkdtemp()
        stamp = "2026-09-23 11:29:18 +0200: Memory Usage (820432K) : "
        for t in tables:
            with open(os.path.join(d, "c.drctmp_c_%s.log" % t), "w") as f:
                if t == "antenna":
                    f.write(stamp + "Executing rule Ant.h\n" + stamp + "Executing rule Ant.i\n")
                else:
                    f.write(stamp + "Executing rule X.a\n" + stamp + "KLayout DRC run for tables '%s' completed in 20.1 seconds\n" % t)
        if density is not None:
            with open(os.path.join(d, "c.drctmp_c_density.log"), "w") as f:
                for layer, pct, lo, hi in density:
                    lim = "Min = %.2f%%,  Max = %.2f%%" % (lo, hi) if hi is not None else "Min = %.2f%%" % lo
                    f.write(stamp + "%-10s Density %% = %.2f%%  [%s]\n" % (layer, pct, lim))
                f.write(stamp + "KLayout DRC run for density table completed in 194.56 seconds\n")
        with open(os.path.join(d, "drc_run_2026_09_23_09_26_01.log"), "w") as f:
            f.write("23-Sep-2026 11:42:00 | INFO    | %s\n" % main)
        body = "".join("<item><tags /><category>'%s'</category><cell>c</cell></item>\n" % c for c in items)
        with open(os.path.join(d, "c.drctmp_c_full.lyrdb"), "w") as f:
            f.write("<?xml version='1.0' encoding='utf-8'?>\n<report-database>\n<categories></categories>\n"
                    "<items>\n%s</items>\n</report-database>\n" % body)
        if extra:
            name, text = extra
            with open(os.path.join(d, name), "a") as f:
                f.write(text)
        return d

    chip = ["Pad.d1R"] * 40 + ["Pad.fR_TM1"] * 38 + ["NW.d"] * 2
    expect = {"Pad.d1R": 40, "Pad.fR_TM1": 38, "NW.d": 2}
    cases = [
        ("clean run passes", fixture(), {}, True, True),
        ("the chip's 80 pass against their expectation", fixture(items=chip), expect, True, True),
        ("the chip's 80 fail without an expectation", fixture(items=chip), {}, True, False),
        ("one marker too many fails", fixture(items=chip + ["NW.d"]), expect, True, False),
        ("an expected category that is absent fails", fixture(items=chip[:78]), expect, True, False),
        ("a new category fails", fixture(items=chip + ["M1.b"]), expect, True, False),
        ("a table that stopped early fails",
         fixture(extra=("c.drctmp_c_metal1.log", "2026-09-23 11:30:00 +0200: Memory Usage (1K) : Executing rule M1.c\n")),
         {}, True, False),
        ("a traceback fails",
         fixture(extra=("drc_run_2026_09_23_09_26_01.log", "Traceback (most recent call last):\n")), {}, True, False),
        ("an exception in a table log fails",
         fixture(extra=("c.drctmp_c_activ.log", "RuntimeError: Exception in DRC\n")), {}, True, False),
        ("a run without its total time fails", fixture(main="Starting"), {}, True, False),
        ("a density over its maximum fails", fixture(density=(("Metal4", 60.4, 35.0, 60.0),)), {}, True, False),
        ("a density under its minimum fails", fixture(density=(("GatPoly", 14.9, 15.0, None),)), {}, True, False),
        ("a missing density log fails when density is asked for", fixture(density=None), {}, True, False),
        ("a missing density log passes with --no-density", fixture(density=None), {}, False, True),
        ("a directory without logs fails", fixture(tables=(), density=None), {}, False, False),
    ]
    bad = 0
    for name, d, exp, dens, want in cases:
        ok, lines = verdict(d, exp, density=dens)
        if ok != want:
            bad += 1
            print("FAIL: %s: verdict %s, expected %s" % (name, ok, want))
            for line in lines:
                print("    " + line)
        shutil.rmtree(d)
    # --out keeps the verdict next to the reports, because git ignores the logs
    import subprocess
    d = fixture(items=chip)
    out = os.path.join(d, "verdict.txt")
    rc = subprocess.run([sys.executable, __file__, d, "--expect", "Pad.d1R=40,Pad.fR_TM1=38,NW.d=2", "--out", out],
                        capture_output=True).returncode
    text = open(out).read() if os.path.exists(out) else ""
    if rc != 0 or not text.endswith("PASS\n") or "Pad.d1R=40" not in text:
        bad += 1
        print("FAIL: --out wrote %r, exit %d" % (text, rc))
    shutil.rmtree(d)
    empty = tempfile.mkdtemp()
    ok, _ = verdict(empty, {}, density=False)
    if ok:
        bad += 1
        print("FAIL: an empty directory passed")
    shutil.rmtree(empty)
    if bad:
        sys.exit(1)
    print("OK: drc_verdict self-test, %d cases" % (len(cases) + 2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", nargs="?")
    ap.add_argument("--expect", default="", help="CAT=N,CAT=N, the only markers allowed")
    ap.add_argument("--no-density", action="store_true", help="the run had no density table, the precheck")
    ap.add_argument("--out", help="also write the verdict here, git ignores the logs it is read from")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.dir:
        ap.error("the DRC output directory is required")
    ok, lines = verdict(args.dir, parse_expect(args.expect), density=not args.no_density)
    print("\n".join(lines))
    if args.out:
        with open(args.out, "w") as f:
            f.write("\n".join(lines) + "\n")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
