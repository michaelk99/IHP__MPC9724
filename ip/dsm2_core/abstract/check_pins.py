# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""The LEF pins of dsm2_core against the blackbox ports: check_pins.py <lef> <verilog>."""
import re
import sys

lef, ver = (open(a).read() for a in sys.argv[1:3])
lef_pins = {re.sub(r"\[\d+\]$", "", p) for p in re.findall(r"^\s*PIN (\S+)", lef, re.M)}
ports = {p.strip() for p in re.search(r"module dsm2_core \(([^)]*)\)", ver).group(1).split(",")}
if lef_pins != ports:
    sys.exit(f"dsm2 pins differ: only in LEF {sorted(lef_pins - ports)}, only in Verilog {sorted(ports - lef_pins)}")
print("PASS: dsm2 pins")
