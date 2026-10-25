#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Current density of the chip's supply and named signal nets, from the final DEF.

    em_probe.py <final.def> --lef <tech.lef> --current VDD=0.2 --current VSS=0.2 \\
        --signal clk=0.0004 --out verification/em/em_table.md
    em_probe.py --self-test

For every net and layer it takes the narrowest wire and the via array with the
fewest cuts, and puts the whole net current through it. That is the worst case
by construction, a real strap shares the current with its neighbours. The one
exception is the Metal1 rails, where a single rail carries one row, so they get
the net current divided by the number of rails. DRCFILL patches, which only
bring a via landing up to minimum area, are not current paths. A net with no
routing in the chip DEF, the IO supplies, is listed but not rated: its ring is
inside the pad cells. Currents are in mA, limits are
the average-current limits of the SG13CMOS5L process specification, section
3.5. A ratio of 0.5 or more fails.
"""
import argparse
import collections
import fnmatch
import re
import sys

# mA per um of width for wires, mA per cut for vias
LIMITS = {
    "Cont": 0.3, "Metal1": 1.0, "Via1": 0.4, "Metal2": 2.0, "Via2": 0.4, "Metal3": 2.0,
    "Via3": 0.4, "Metal4": 2.0, "TopVia1": 1.4, "TopMetal1": 15.0,
}
FAIL_RATIO = 0.5

POINT = re.compile(r"\(\s*(\S+)\s+(\S+)(?:\s+\S+)?\s*\)")
RECT = re.compile(r"RECT\s*\([^)]*\)")
VIA_NAME = re.compile(r"(?i)^(top)?via\d")


def parse_lef_widths(path):
    """{routing layer: default width in um} from a tech LEF."""
    widths, layer, routing = {}, None, False
    for line in open(path):
        tok = line.split()
        if not tok:
            continue
        if tok[0] == "LAYER" and len(tok) > 1:
            layer, routing = tok[1], False
        elif tok[0] == "TYPE" and layer:
            routing = tok[1].rstrip(";") == "ROUTING"
        elif tok[0] == "WIDTH" and layer and routing and layer not in widths:
            widths[layer] = float(tok[1])
        elif tok[0] == "END" and len(tok) > 1 and tok[1] == layer:
            layer = None
    return widths


def parse_lef_vias(path):
    """{via name: (cut layer, number of cuts)} from the VIA blocks of a tech LEF."""
    vias, name, layer, cuts, cut_layer = {}, None, None, 0, None
    for line in open(path):
        tok = line.split()
        if not tok:
            continue
        if tok[0].upper() == "VIA" and len(tok) > 1:
            name, layer, cuts, cut_layer = tok[1], None, 0, None
        elif name and tok[0] == "LAYER":
            layer = tok[1]
            if VIA_NAME.match(layer) or layer == "Cont":
                cut_layer = layer
        elif name and tok[0] == "RECT" and layer == cut_layer and cut_layer:
            cuts += 1
        elif name and tok[0] == "END" and len(tok) > 1 and tok[1] == name:
            if cut_layer:
                vias[name] = (cut_layer, max(cuts, 1))
            name = None
    return vias


def section(text, name):
    m = re.search(r"^%s\b.*?;(.*?)^END %s" % (name, name), text, re.S | re.M)
    return m.group(1) if m else ""


def parse_def(path):
    text = open(path).read()
    dbu = int(re.search(r"UNITS DISTANCE MICRONS (\d+)", text).group(1))
    vias = {}
    for m in re.finditer(r"^\s*-\s+(\S+)(.*?);", section(text, "VIAS"), re.S | re.M):
        body = m.group(2)
        layers = re.search(r"\+ LAYERS\s+(\S+)\s+(\S+)\s+(\S+)", body)
        rc = re.search(r"\+ ROWCOL\s+(\d+)\s+(\d+)", body)
        cut = layers.group(2) if layers else None
        vias[m.group(1)] = (cut, int(rc.group(1)) * int(rc.group(2)) if rc else 1)
    return dbu, vias, text


def net_blocks(body):
    """{net name: statement text} for a SPECIALNETS or NETS section body."""
    out = {}
    for m in re.finditer(r"^\s*-\s+(\S+)(.*?);", body, re.S | re.M):
        out[m.group(1).replace("\\", "")] = m.group(2)
    return out


def statements(block):
    """(layer, width in dbu or None, shape, points, via name) per routed statement."""
    for part in re.split(r"\+ ROUTED|\bNEW\b", block)[1:]:
        tok = part.split("+ USE")[0].split("+ SOURCE")[0]
        m = re.match(r"\s*(\S+)\s+(?:(\d+)\s+)?(?:\+\s*SHAPE\s+(\S+)\s+)?(.*)", tok, re.S)
        if not m:
            continue
        layer, width, shape, rest = m.groups()
        # a RECT patch is not a path, TAPER only lets the wire narrow into a pin
        rest = RECT.sub(" ", rest).replace("TAPER", " ")
        pts = POINT.findall(rest)
        tail = POINT.sub(" ", rest).split()
        via = tail[-1] if tail and VIA_NAME.match(tail[-1]) else None
        yield layer, int(width) if width else None, shape, pts, via


def probe(def_path, lef_widths, currents, signals, lef_vias=None):
    """One row per (net, layer): the worst element and its ratio."""
    dbu, vias, text = parse_def(def_path)
    vias = {**(lef_vias or {}), **vias}
    rows = []
    special = net_blocks(section(text, "SPECIALNETS"))
    regular = net_blocks(section(text, "NETS"))
    for net, current in list(currents.items()) + list(signals.items()):
        pool = special if net in currents else regular
        blocks = [b for n, b in pool.items() if fnmatch.fnmatchcase(n, net)]
        if not blocks:
            rows.append((net, "-", "net not found in the DEF", None, 0, current, "", None, None))
            continue
        wires = collections.defaultdict(list)
        via_use = collections.Counter()
        rails = 0
        for layer, width, shape, pts, via in (st for b in blocks for st in statements(b)):
            if via:
                via_use[via] += 1
            # DRCFILL patches only fill out a via landing to minimum area
            if len(pts) >= 2 and shape != "DRCFILL":
                w = width / dbu if width else lef_widths.get(layer)
                if w:
                    wires[layer].append((w, shape or "wire"))
                    rails += shape == "FOLLOWPIN"
        if not wires and not via_use:
            rows.append((net, "none", "no routing at chip level", None, 0, current, "", None, None))
            continue
        for layer in sorted(wires, key=lambda l: list(LIMITS).index(l) if l in LIMITS else 99):
            w, shape = min(wires[layer])
            i = current / rails if shape == "FOLLOWPIN" and rails else current
            src = "net / %d rails" % rails if shape == "FOLLOWPIN" and rails else "whole net"
            lim = LIMITS.get(layer, 0) * w
            rows.append((net, layer, "%s %.2f um" % (shape.lower(), w), w, len(wires[layer]), i, src, lim,
                         i / lim if lim else None))
        per_cut = collections.defaultdict(list)
        for name, n in via_use.items():
            cut, cuts = vias.get(name, (None, 1))
            if cut is None:
                m = re.match(r"(?i)(via\d|topvia\d)", name)
                cut = {"via1": "Via1", "via2": "Via2", "via3": "Via3", "topvia1": "TopVia1"}.get(
                    m.group(1).lower() if m else "", name)
            per_cut[cut].append((cuts, name, n))
        for cut in sorted(per_cut, key=lambda l: list(LIMITS).index(l) if l in LIMITS else 99):
            cuts, name, _ = min(per_cut[cut])
            count = sum(n for _, _, n in per_cut[cut])
            lim = LIMITS.get(cut, 0) * cuts
            rows.append((net, cut, "%d-cut array" % cuts, cuts, count, current, "whole net", lim,
                         current / lim if lim else None))
    return rows


def table(rows):
    out = ["| Net | Layer | Worst element | Count | I (mA) | Source of I | Limit (mA) | Ratio |",
           "|---|---|---|---:|---:|---|---:|---:|"]
    for net, layer, elem, _, count, i, src, lim, ratio in rows:
        out.append("| %s | %s | %s | %d | %.4g | %s | %s | %s |" % (
            net, layer, elem, count, i, src, "%.3g" % lim if lim else "-",
            "%.3g" % ratio if ratio is not None else "-"))
    return out


def verdict(rows):
    missing = [r for r in rows if r[1] == "-"]
    rated = [r for r in rows if r[8] is not None]
    worst = max(rated, key=lambda r: r[8]) if rated else None
    ok = bool(rated) and not missing and worst[8] < FAIL_RATIO
    lines = []
    for r in missing:
        lines.append("FAIL: %s is not in the DEF" % r[0])
    if worst:
        lines.append("max ratio: %.3g, %s %s %s" % (worst[8], worst[0], worst[1], worst[2]))
    lines.append("PASS" if ok else "FAIL")
    return ok, lines


def parse_pairs(items):
    out = {}
    for item in items:
        k, _, v = item.partition("=")
        out[k] = float(v)
    return out


def self_test():
    import os
    import tempfile
    d = tempfile.mkdtemp()
    lef = os.path.join(d, "t.lef")
    open(lef, "w").write("LAYER Metal2\n  TYPE ROUTING ;\n  WIDTH 0.2 ;\nEND Metal2\n"
                         "LAYER Via1\n  TYPE CUT ;\n  WIDTH 0.19 ;\nEND Via1\n"
                         "Via Via2_DV2E_so DEFAULT\n  LAYER Metal2 ;\n    RECT 0 0 1 1 ;\n  LAYER Via2 ;\n    RECT 0 0 1 1 ;\n    RECT 2 0 3 1 ;\n"
                         "  LAYER Metal3 ;\n    RECT 0 0 3 1 ;\nEND Via2_DV2E_so\n")
    df = os.path.join(d, "t.def")
    open(df, "w").write("""VERSION 5.8 ;
UNITS DISTANCE MICRONS 1000 ;
VIAS 2 ;
    - via4_big + VIARULE viaTop1Array + CUTSIZE 420 420 + LAYERS Metal4 TopVia1 TopMetal1 + ROWCOL 3 18 ;
    - via4_one + VIARULE viaTop1Array + CUTSIZE 420 420 + LAYERS Metal4 TopVia1 TopMetal1 ;
END VIAS
SPECIALNETS 2 ;
    - IOVDD ( PIN IOVDD ) ( * iovdd ) + USE POWER ;
    - VDD ( PIN VDD ) ( * VDD ) + USE POWER
      + ROUTED Metal4 0 + SHAPE STRIPE ( 1000 1000 ) via4_one
      NEW Metal4 0 + SHAPE STRIPE ( 1000 2000 ) via4_big
      NEW TopMetal1 1660 + SHAPE STRIPE ( 0 0 ) ( 0 50000 )
      NEW TopMetal1 15000 + SHAPE RING ( 0 0 ) ( 90000 0 )
      NEW Metal4 1000 + SHAPE STRIPE ( 5000 0 ) ( 5000 800000 )
      NEW Metal2 200 + SHAPE STRIPE ( 0 0 ) Via2_DV2E_so
      NEW Metal1 320 + SHAPE FOLLOWPIN ( 0 0 ) ( 800000 * )
      NEW Metal1 320 + SHAPE FOLLOWPIN ( 0 3360 ) ( 800000 * )
      NEW Metal1 320 + SHAPE FOLLOWPIN ( 0 6720 ) ( 800000 * )
      NEW Metal3 200 + SHAPE DRCFILL ( 400 400 ) ( 900 * ) ;
END SPECIALNETS
NETS 2 ;
    - clknet_0_clk ( u1 Y ) ( u0 CK )
      + ROUTED Metal3 ( 100 100 ) ( 100 9000 ) ;
    - clk ( PIN clk_PAD ) ( u0 CK )
      + ROUTED Metal2 ( 100 100 ) ( 100 9000 ) Via1_XX_so
      NEW Metal2 TAPER ( 100 9000 ) ( 900 9000 )
      NEW Metal2 ( 900 9000 ) RECT ( -100 -100 100 100 ) ;
END NETS
""")
    open(lef, "a").write("LAYER Metal3\n  TYPE ROUTING ;\n  WIDTH 0.2 ;\nEND Metal3\n")
    rows = probe(df, parse_lef_widths(lef), {"VDD": 0.2, "IOVDD": 1.0}, {"clk*": 0.0004}, parse_lef_vias(lef))
    got = {(r[0], r[1]): r for r in rows}
    bad = 0

    def check(cond, what):
        nonlocal bad
        if not cond:
            bad += 1
            print("FAIL: " + what)

    check(abs(got["VDD", "TopMetal1"][3] - 1.66) < 1e-9, "narrowest TopMetal1 is the 1.66 um strap: %s" % (got.get(("VDD", "TopMetal1")),))
    check(got["VDD", "TopVia1"][3] == 1 and got["VDD", "TopVia1"][4] == 2, "fewest TopVia1 cuts is 1, two arrays: %s" % (got.get(("VDD", "TopVia1")),))
    check(abs(got["VDD", "TopVia1"][8] - 0.2 / 1.4) < 1e-9, "single cut ratio 0.2/1.4: %s" % (got["VDD", "TopVia1"][8],))
    check(abs(got["VDD", "Metal1"][5] - 0.2 / 3) < 1e-9, "a rail carries a third of 0.2 mA: %s" % (got["VDD", "Metal1"][5],))
    check(abs(got["clk*", "Metal2"][3] - 0.2) < 1e-9, "clk width from the LEF default: %s" % (got.get(("clk*", "Metal2")),))
    check(got["clk*", "Via1"][3] == 1, "a LEF via counts one cut: %s" % (got.get(("clk*", "Via1")),))
    check(got["VDD", "Via2"][3] == 2, "a LEF via with two cut rectangles counts two cuts: %s" % (got.get(("VDD", "Via2")),))
    check(("clk*", "Metal3") in got, "a pattern takes every matching net: %s" % sorted(got))
    check({l for n, l in got if n == "clk*"} == {"Metal2", "Metal3", "Via1"}, "TAPER and RECT are not vias: %s" % sorted(got))
    check(("VDD", "Metal3") not in got, "a DRCFILL patch carries no current: %s" % (got.get(("VDD", "Metal3")),))
    check(got.get(("IOVDD", "none"), [None] * 9)[8] is None, "an unrouted net is listed, unrated: %s" % (got.get(("IOVDD", "none")),))
    ok, lines = verdict(rows)
    check(ok, "0.2 mA passes: %s" % lines)
    rows1 = probe(df, parse_lef_widths(lef), {"VDD": 1.0}, {})
    ok, lines = verdict(rows1)
    via1 = [r for r in rows1 if r[1] == "TopVia1"][0]
    check(not ok and via1[8] > FAIL_RATIO, "1 mA fails, and one TopVia1 cut alone is over the line: %s" % lines)
    ok, lines = verdict(probe(df, parse_lef_widths(lef), {"VDD": 0.2, "VDDX": 0.2}, {}))
    check(not ok, "a net missing from the DEF fails: %s" % lines)
    os.remove(lef)
    os.remove(df)
    os.rmdir(d)
    if bad:
        sys.exit(1)
    print("OK: em_probe self-test, 14 checks")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("def_file", nargs="?")
    ap.add_argument("--lef", help="tech LEF, for the default width of signal routing and the cut count of its vias")
    ap.add_argument("--current", action="append", default=[], metavar="NET=mA", help="a supply net and its average current")
    ap.add_argument("--signal", action="append", default=[], metavar="NET=mA",
                    help="a signal net, or a glob over nets, and the average current of each")
    ap.add_argument("--out", help="also write the table and the verdict here, as markdown")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.def_file or not args.current:
        ap.error("a DEF and at least one --current are required")
    rows = probe(args.def_file, parse_lef_widths(args.lef) if args.lef else {},
                 parse_pairs(args.current), parse_pairs(args.signal), parse_lef_vias(args.lef) if args.lef else None)
    ok, lines = verdict(rows)
    text = "\n".join(table(rows) + [""] + lines) + "\n"
    print(text, end="")
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
