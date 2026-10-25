#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Prefix every module the given Verilog files define, and every use of those names.

    python3 prefix_modules.py legacy_ a.v b.v > out.v

Two designs that both define dsa1_dig_top and decimator_top can then share one
FPGA build. Only names defined in these files change, so a module they
instantiate from elsewhere keeps its name.
"""
import re
import sys


def prefix(prefix: str, texts: list) -> str:
    names = sorted({m for t in texts for m in re.findall(r"^\s*module\s+\\?(\w+)", t, re.M)}, key=len, reverse=True)
    pat = re.compile(r"\b(" + "|".join(map(re.escape, names)) + r")\b")
    return "\n".join(pat.sub(lambda m: prefix + m.group(1), t) for t in texts)


def self_test() -> int:
    a = "module top (input x);\n  dec u_dec (.x(x));\nendmodule\n"
    b = "module dec (input x);\n  other u_o (.x(x));\nendmodule\n"
    out = prefix("legacy_", [a, b])
    assert "module legacy_top" in out and "module legacy_dec" in out, out
    assert "  legacy_dec u_dec " in out, out            # uses renamed, instance names kept
    assert "  other u_o " in out, out                   # a module from elsewhere keeps its name
    print("PASS: prefix_modules self-test")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    sys.stdout.write(prefix(sys.argv[1], [open(f).read() for f in sys.argv[2:]]))
