#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Rewrite a macro's CDL the way Magic's ext2spice writes the devices, for netgen in top_lvs.sh.

    cdl_magic.py <in.cdl> <out.spice> [--reference FILE ...] [--different OUT]

M and D cards become X calls, R cards with $SUB and $[model] become X calls with the substrate as third pin.
Two device kinds Magic does not extract are dropped and counted: ptap1 (a substrate tie, its two nodes are one node in the layout) and cap_cmomf (metal fingers, no device layer).
A subckt that a --reference file also defines is dropped here when both bodies are the same, else it is kept and its name goes to --different, for the caller to resolve.
"""
import argparse
import re
import sys

DROP_MODELS = ("ptap1", "cap_cmomf")


def convert(text, drop_subckts=()):
    lines = []
    for raw in text.splitlines():
        if raw.startswith("+") and lines:
            lines[-1] += " " + raw[1:].strip()
        else:
            lines.append(raw.rstrip())
    out, dropped, skip = [], {m: 0 for m in DROP_MODELS}, False
    for line in lines:
        tok = line.split()
        if not tok or line.startswith("*"):
            out.append(line)
            continue
        key = tok[0].lower()
        if key == ".subckt" and tok[1] in drop_subckts:
            skip = True
            continue
        if skip:
            skip = key != ".ends"
            continue
        if key.startswith(".") or key[0] == "x":
            out.append(line)
            continue
        if any(m in tok for m in DROP_MODELS):
            dropped[next(m for m in DROP_MODELS if m in tok)] += 1
            continue
        if key[0] in "md":
            out.append("X" + line)
            continue
        m = re.match(r"^(R\S*) (\S+) (\S+) \S+ \$SUB=(\S+) \$\[(\w+)\] (.*)$", line, re.I)
        if m:
            params = " ".join(p for p in m.group(6).split() if p != "b=0")
            out.append("X%s %s %s %s %s %s" % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), params))
            continue
        sys.exit("cdl_magic.py: card not converted: " + line)
    return "\n".join(out) + "\n", dropped


def subckts(text):
    """Map each subckt name to its body as lowercase token lines, continuation lines joined."""
    out, name = {}, None
    for line in re.sub(r"\n\+", " ", text).splitlines():
        tok = line.lower().split()
        if not tok or tok[0].startswith("*"):
            continue
        if tok[0] == ".subckt":
            name = line.split()[1]
            out[name] = [tok[2:]]
        elif tok[0] == ".ends":
            name = None
        elif name:
            out[name].append(tok)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cdl")
    ap.add_argument("out")
    ap.add_argument("--reference", nargs="*", default=[])
    ap.add_argument("--different", help="file that gets the names defined differently in a reference")
    a = ap.parse_args()
    cdl = open(a.cdl).read()
    mine = subckts(convert(cdl)[0])
    same, diff = [], []
    for ref in a.reference:
        theirs = subckts(open(ref).read())
        for name in sorted(set(mine) & set(theirs)):
            (same if mine[name] == theirs[name] else diff).append(name)
            print("cdl_magic.py: %s also in %s, %s" % (name, ref, "same, dropped here" if mine[name] == theirs[name] else "DIFFERENT, kept here"))
    text, dropped = convert(cdl, same)
    open(a.out, "w").write(text)
    if a.different:
        open(a.different, "w").write("".join(n + "\n" for n in diff))
    print("cdl_magic.py: dropped " + ", ".join("%d %s" % (n, m) for m, n in dropped.items()))


if __name__ == "__main__":
    main()
