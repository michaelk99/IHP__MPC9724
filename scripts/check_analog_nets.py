#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Check that the analog and dsm2 nets of the gate-level netlist touch only the cells the spec allows.

    check_analog_nets.py <netlist.v> <spec> [--rx <config.yaml>]

The spec has one line per net, `net: inst/pin inst/pin ...`, with # comments.
A token ending in ? is an inst-glob/pin-glob that may match any number of extra pins, for example `ANTENNA_*/A?`.
A net fails if it touches a pin outside its list (a buffer, an antenna diode, a tie), if a listed pin is missing, if it appears in an assign, or if it is not in the netlist.
With --rx every alternative of RSZ_DONT_TOUCH_RX must match a net or an instance name.
"""

import argparse
import fnmatch
import re
import sys

STMT_SKIP = ("module", "endmodule", "input", "output", "inout", "wire", "wand", "wor", "reg", "supply0", "supply1", "tri", "parameter", "localparam")
NAME = r"(?:\\\S+\s|[A-Za-z_][\w$]*)"


def norm(name):
    return name.strip().lstrip("\\")


def parse_netlist(text):
    """Return (conns, assigned, nets, insts, unparsed): net -> {(inst, pin)}, nets in assigns, net names, instance names, connections no regex reads."""
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"\(\*.*?\*\)", "", text, flags=re.S)
    conns, assigned, names, insts, unparsed = {}, set(), set(), set(), []
    for stmt in text.split(";"):
        stmt = stmt.strip()
        if not stmt:
            continue
        word = stmt.split(None, 1)[0]
        if word == "assign":
            for ident in re.findall(NAME, stmt[len("assign"):]):
                assigned.add(norm(ident))
            continue
        if word in ("wire", "input", "output", "inout", "wand", "wor", "tri", "supply0", "supply1"):
            for ident in re.findall(NAME, stmt[len(word):]):
                names.add(norm(ident))
            continue
        if word in STMT_SKIP:
            # a module header holds port names, which are nets of that module
            if word == "module":
                for ident in re.findall(NAME, stmt.split("(", 1)[-1]):
                    names.add(norm(ident))
            continue
        m = re.match(r"(%s)\s+(%s)\s*\((.*)\)\s*$" % (NAME, NAME), stmt, flags=re.S)
        if not m:
            continue
        inst = norm(m.group(2))
        insts.add(inst)
        for part in split_top(m.group(3)):
            c = re.fullmatch(r"\.(\w+)\s*\((.*)\)", part.strip(), flags=re.S)
            try:
                if not c:
                    raise ValueError
                pin, nets = c.group(1), conn_nets(c.group(2))
            except ValueError:
                unparsed.append("%s: cannot parse the connection %s" % (inst, " ".join(part.split())))
                continue
            for net in nets:
                conns.setdefault(net, set()).add((inst, pin))
                names.add(net)
    return conns, assigned, names, insts, unparsed


def conn_nets(expr):
    """The net names in the expression of one pin connection: empty, a net, a bit of a bus, a constant or a concatenation of those. Anything else raises ValueError."""
    expr = expr.strip()
    if not expr or re.fullmatch(r"\d+'[sS]?[bBoOdDhH][0-9a-fA-FxXzZ_]+", expr):
        return []
    if expr.startswith("{") and expr.endswith("}"):
        out = []
        for part in split_top(expr[1:-1]):
            out += conn_nets(part)
        return out
    if re.fullmatch(r"(?:\\\S+|[A-Za-z_][\w$]*)(?:\s*\[\d+\])?", expr):
        return [norm(re.sub(r"\s+\[", "[", expr))]
    raise ValueError(expr)


def split_top(text):
    """Split on commas outside any bracket."""
    parts, depth, cur = [], 0, ""
    for ch in text:
        depth += ch in "([{"
        depth -= ch in ")]}"
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return parts


def parse_spec(text):
    """Return net -> (required pins, optional pin globs). A token ending in ? is a glob that may match any number of pins."""
    spec = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        net, _, rest = line.partition(":")
        toks = rest.split()
        spec[net.strip()] = (set(tuple(t.split("/", 1)) for t in toks if not t.endswith("?")),
                             [tuple(t[:-1].split("/", 1)) for t in toks if t.endswith("?")])
    return spec


def rx_alternatives(config_text):
    m = re.search(r'^RSZ_DONT_TOUCH_RX:\s*"(.*)"\s*$', config_text, flags=re.M)
    if not m:
        return None
    rx = m.group(1)
    if rx.startswith("^(") and rx.endswith(")$"):
        rx = rx[2:-2]
    return rx.split("|")


def check(netlist_text, spec_text, config_text=None):
    """Return a list of failure messages, empty on PASS."""
    conns, assigned, nets, insts, fails = parse_netlist(netlist_text)
    for net, (allowed, optional) in parse_spec(spec_text).items():
        if net not in nets and net not in assigned:
            fails.append("%s not in netlist" % net)
            continue
        if net in assigned:
            fails.append("%s appears in an assign" % net)
        touched = conns.get(net, set())
        extra = {(i, p) for i, p in touched - allowed if not any(fnmatch.fnmatchcase(i, gi) and fnmatch.fnmatchcase(p, gp) for gi, gp in optional)}
        for inst, pin in sorted(extra):
            fails.append("%s also touches %s/%s" % (net, inst, pin))
        for inst, pin in sorted(allowed - touched):
            fails.append("%s does not touch %s/%s" % (net, inst, pin))
    if config_text is not None:
        alts = rx_alternatives(config_text)
        if alts is None:
            fails.append("no RSZ_DONT_TOUCH_RX in the config")
        for alt in alts or []:
            if not any(re.fullmatch(alt, n) for n in nets | insts):
                fails.append("regex alternative %s matches no net and no instance" % alt)
    return fails


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("netlist")
    ap.add_argument("spec")
    ap.add_argument("--rx", metavar="CONFIG")
    args = ap.parse_args()
    fails = check(open(args.netlist).read(), open(args.spec).read(), open(args.rx).read() if args.rx else None)
    for f in fails:
        print("FAIL: " + f)
    print("check_analog_nets: " + ("FAIL" if fails else "PASS"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
