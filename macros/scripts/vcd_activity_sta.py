#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: Turn a Verilator VCD window into OpenSTA set_power_activity lines

"""Measured switching activity for a gate-level power run.

Copied on 2026-09-12 from OpenBLAU @ 6e50c0b9, scripts/vcd_activity_sta.py, with one change: the time unit is read
from the VCD's own $timescale instead of being assumed to be femtoseconds. Verilator writes fs, Icarus writes ps
here, and the assumption made every window 1000x too short, so every density and all dynamic power came out 1000x
too high. Worth pushing back upstream. Everything else, and the docstring below, is theirs.

`read_vcd` is the obvious way to do this and does not work on a flat netlist:
OpenSTA looks each VCD signal up with `findPin`, and after place-and-route the
design is one level deep with dotted escaped NET names
(\\u_dpll.u_loop_filter.acc_q[3]). Only the top-level ports are pins, so on
`ble_tx` it annotates exactly 125 of them and PROPAGATES every internal toggle
count from there -- which is precisely the number a power state is supposed to
measure rather than infer.

This reads the same VCD itself, counts real transitions per net over a window,
and writes `set_power_activity -pin` for the pin that DRIVES each net. Nets
that no longer exist after synthesis are dropped and counted; what survives is
measured, and the report says how much of the design that covers.

    python3 scripts/vcd_activity_sta.py dump.vcd netlist.v out.tcl \\
        --scope tb_ble_mod/u_dut --period 25 --from 436000 --to 445800

`--period` no longer scales anything; it only reports the window in cycles.

What is written is `-density`, transitions per ns, NOT `-activity`. The two
are the same thing on a single-clock block (`density = activity / period`
reproduces `dco_switch_cap_decoder` to the last digit, 2.63 mW either way)
and they are not the same thing anywhere else: OpenSTA turns an `-activity`
into a density using the period of the clock IT resolves for that pin, so on a
block with five clock domains (`fast_counter`: 0.4, 0.8, 1.6, 25, 25 ns) four
of them are charged at the wrong rate, and on a block whose only fast clock
runs between two macros (`dpll`) the standard cells are charged at that rate
rather than at the reference. A VCD measures a density; write the density.

`--global-density` opens the file with a `-global` line at the mean density of
the nets it is actually APPLIED to, which is the ones the VCD saw and the
netlist did not keep. Taking the mean over the ANNOTATED nets instead is what
this used to do and it is badly wrong: on `fast_counter` that mean is
0.060/ns against 0.0069 over the population it lands on, because it is set by
a 1 percent tail of DCO-rate nets which are annotated already and carry their
own clock trees. The block came out at 8.69 mW and is 5.39.

USE IT ONLY WHERE THE DEFAULT RATE IS WRONG, because it
replaces OpenSTA's propagation rather than only its default: on
`dco_switch_cap_decoder`, whose 2.51 mW is the accepted number, propagation
gives 2.63 mW and the global gives 4.57. Where it earns its place is a block
whose nets mostly did NOT survive synthesis by name and whose fastest clock is
not the rate its logic runs at. `fast_counter` annotates 224 of 4042 nets,
and the other 94 % take 0.1 transitions per cycle of a 2.44 GHz clock,
0.244/ns against the 0.055/ns this VCD measures.

`duty` is the fraction of the window the net is high. A STATIC net is written
at `--act-floor`, not at 0: `report_power` dies with `domain error: argument
not in valid range` on the first zero it is given, naming no pin. The default
1e-9/ns is a transition every 32 s, so it changes no reported digit, and it is
the difference between a number and no number at all. On `dpll` 767 of 829
annotated pins are static.
"""

import argparse
import os
import re
import sys

VAR_RE = re.compile(r"^\s*\$var\s+(\S+)\s+(\d+)\s+(\S+)\s+(\S+)\s*(\[[^\]]*\])?\s*\$end")
SCOPE_RE = re.compile(r"^\s*\$scope\s+\S+\s+(\S+)\s+\$end")
UPSCOPE_RE = re.compile(r"^\s*\$upscope")

# an instance spans lines: `cell inst (.PORT(net),\n   .PORT(net));`
DECL_RE = re.compile(r"^\s*([A-Za-z_][\w$]*)\s+(\\\S+|[A-Za-z_][\w$]*)\s*\(")
CONN_RE = re.compile(r"\.(\w+)\s*\(\s*(\\\S+\s|[^)]*?)\s*\)")


def liberty_outputs(lib_paths):
    """cell -> set of output pin names, from the liberty files."""
    out = {}
    cell = pin = None
    for path in lib_paths:
        with open(path, errors="ignore") as fh:
            for line in fh:
                m = re.match(r'\s*cell\s*\(\s*"?([\w$]+)"?\s*\)', line)
                if m:
                    cell = m.group(1)
                    out.setdefault(cell, set())
                    continue
                # `bus (therm_o)` carries ONE direction for all 48 bits and
                # the per-bit `pin (therm_o[0])` blocks carry none, so a bus
                # read as a pin leaves every output of a hard macro unknown.
                m = re.match(r'\s*(?:pin|bus)\s*\(\s*"?([\w$\[\]]+)"?\s*\)',
                             line)
                if m:
                    pin = m.group(1)
                    continue
                if cell and pin and re.match(r'\s*direction\s*:\s*"?output', line):
                    out[cell].add(pin)
    return out


def strip_escape(name):
    """Verilog escaped identifier -> the plain name OpenSTA reports."""
    name = name.strip()
    return name[1:].rstrip() if name.startswith("\\") else name


def netlist_nets(path):
    """Every net token the netlist mentions, ports included.

    The -global population is "VCD nets the netlist does not have", and that
    is not the same as "nets with no driver in it": a clock PORT has no driver
    and is charged as a clock, so leaving it in the population puts the
    fastest net in the design into the average for the slowest logic.
    """
    out = set()
    txt = open(path, errors="ignore").read()
    for m in re.finditer(r"\.\w+\(([^)]*)\)", txt):
        for tok in m.group(1).replace("{", "").replace("}", "").split(","):
            t = strip_escape(tok)
            if t:
                out.add(t)
    return out


def macro_instances(path, macro_cells):
    """Instance names of the hard macros.

    Their VCD subtree is a SIMULATION MODEL and has no standard cells behind
    it, so it must not set the default for the ones that do: `u_dl_a`'s
    behavioural pointer is 32 bits at 2.44 transitions per ns and there is no
    gate in the netlist that follows it.
    """
    out = set()
    for line in open(path, errors="ignore"):
        m = DECL_RE.match(line)
        if m and m.group(1) not in ("module", "input", "output", "wire",
                                    "assign", "endmodule"):
            if m.group(1) in macro_cells:
                out.add(strip_escape(m.group(2)))
    return out


def netlist_drivers(path, cell_outputs):
    """net name -> "instance/port" of the pin that drives it.

    Line-oriented on purpose: one instance spans several lines and its
    connection list contains parentheses, so a regex over the whole file
    stops at the wrong one.
    """
    drivers = {}
    cell = inst = None
    buf = ""
    with open(path, errors="ignore") as fh:
        for line in fh:
            if cell is None:
                m = DECL_RE.match(line)
                if not m or m.group(1) in ("module", "input", "output",
                                           "wire", "assign", "endmodule"):
                    continue
                cell, inst = m.group(1), strip_escape(m.group(2))
                buf = line[m.end():]
            else:
                buf += line
            if ");" not in buf:
                continue
            outs = cell_outputs.get(cell)
            if outs:
                for m in CONN_RE.finditer(buf):
                    port, net = m.group(1), strip_escape(m.group(2))
                    # A BUSSED CONNECTION IS NOT A NET. A hard macro's bus
                    # comes through as .therm_o({\a[47] , \a[46] , ...}),
                    # so the port token matches no liberty pin and all 48
                    # taps -- the busiest nets in fast_counter -- read as
                    # undriven. Expand it MSB first, the order Yosys writes.
                    if net.startswith("{") and port in outs:
                        bits = [strip_escape(b)
                                for b in net.strip("{}").split(",")]
                        hi = len(bits) - 1
                        for i, b in enumerate(bits):
                            if b:
                                drivers.setdefault(
                                    b, "%s/%s[%d]" % (inst, port, hi - i))
                        continue
                    if port in outs and net:
                        drivers.setdefault(net, "%s/%s" % (inst, port))
            cell = inst = None
            buf = ""
    return drivers


def vcd_ticks_per_ns(path):
    """Time units per ns from the VCD's own $timescale, e.g. 1000 for 1ps, 1e6 for 1fs."""
    unit_ns = {"s": 1e9, "ms": 1e6, "us": 1e3, "ns": 1.0, "ps": 1e-3, "fs": 1e-6}
    with open(path) as fh:
        head = fh.read(4096)
    m = re.search(r"\$timescale\s+(\d+)\s*([munpf]?s)\s*\$end", head)
    if not m:
        raise SystemExit(f"{path}: no $timescale found")
    return 1.0 / (int(m.group(1)) * unit_ns[m.group(2)])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("vcd")
    ap.add_argument("netlist")
    ap.add_argument("outfile")
    ap.add_argument("--scope", required=True, help="e.g. tb_ble_mod/u_dut")
    ap.add_argument("--period", type=float, required=True, help="clock ns")
    ap.add_argument("--from", dest="t_from", type=float, default=None, help="ns")
    ap.add_argument("--to", dest="t_to", type=float, default=None, help="ns")
    ap.add_argument("--liberty", nargs="+", default=None,
                    help="liberty files; default = the PDK standard cells")
    ap.add_argument("--global-density", action="store_true",
                    help="open with -global at the mean measured density; "
                         "see the module docstring before using it")
    ap.add_argument("--act-floor", type=float, default=1e-9,
                    help="density (per ns) written for a static net; 0 kills "
                         "report_power (see the module docstring)")
    args = ap.parse_args()

    libs = args.liberty
    if not libs:
        pdk = os.path.join(os.environ["PDK_ROOT"], os.environ["PDK"])
        libs = [os.path.join(pdk, "libs.ref", "sg13cmos5l_stdcell", "lib",
                             "sg13cmos5l_stdcell_typ_1p20V_25C.lib")]

    cell_outputs = liberty_outputs(libs)
    # the macro cells are exactly the ones the EXTRA liberties declare; the
    # SCL's fill, tap and decap cells are in neither, which is why this is not
    # "everything the standard-cell liberty does not have"
    macro_cells = set(liberty_outputs(libs[1:])) if len(libs) > 1 else set()
    macros = macro_instances(args.netlist, macro_cells)
    have = netlist_nets(args.netlist)
    drivers = netlist_drivers(args.netlist, cell_outputs)
    print("netlist: %d driven nets, %d macro instance(s)"
          % (len(drivers), len(macros)))

    target = args.scope.split("/")
    tick_ns = vcd_ticks_per_ns(args.vcd)
    t0 = None if args.t_from is None else int(args.t_from * tick_ns)
    t1 = None if args.t_to is None else int(args.t_to * tick_ns)

    # ---- pass 1: the header, ident -> [net names] inside the DUT ----------
    ident_nets = {}
    stack = []
    with open(args.vcd) as fh:
        for line in fh:
            m = SCOPE_RE.match(line)
            if m:
                stack.append(m.group(1))
                continue
            if UPSCOPE_RE.match(line):
                if stack:
                    stack.pop()
                continue
            m = VAR_RE.match(line)
            if m and stack[:len(target)] == target:
                width, ident, name, rng = (int(m.group(2)), m.group(3),
                                           m.group(4), m.group(5))
                base = ".".join(stack[len(target):] + [name])
                if width == 1:
                    names = [base]
                else:
                    hi = int(rng.strip("[]").split(":")[0]) if rng else width - 1
                    lo = int(rng.strip("[]").split(":")[1]) if rng and ":" in rng else 0
                    step = -1 if hi >= lo else 1
                    names = ["%s[%d]" % (base, b)
                             for b in range(hi, lo + step, step)]
                ident_nets.setdefault(ident, []).append(names)
                continue
            if line.startswith("$enddefinitions"):
                break

        # ---- pass 2: transitions and high time per identifier bit --------
        val = {}          # ident -> list of chars, MSB first
        trans = {}        # ident -> list of transition counts
        hitime = {}       # ident -> list of fs spent high
        last_t = {}       # ident -> list of last change time
        now = 0
        started = t0 is None
        # Without --from the window opens at the FIRST timestamp in the file, not at 0. A testbench that calls
        # $dumpvars only once the design has settled writes a VCD whose history starts late, and counting the
        # silent lead-in as part of the window divides every density by it (31 ms of dump inside a 418 ms
        # simulation understated the decimator's dynamic power by 13x).
        t_open = t0 if t0 is not None else None
        t_close = None

        def ensure(ident, n):
            if ident not in val:
                val[ident] = ["x"] * n
                trans[ident] = [0] * n
                hitime[ident] = [0] * n
                last_t[ident] = [t_open] * n

        def setbits(ident, bits):
            n = len(bits)
            ensure(ident, n)
            v, tr, ht, lt = val[ident], trans[ident], hitime[ident], last_t[ident]
            for i in range(min(n, len(v))):
                nb = bits[i]
                ob = v[i]
                if nb == ob:
                    continue
                if started:
                    if ob == "1":
                        ht[i] += now - lt[i]
                    if ob in "01" and nb in "01":
                        tr[i] += 1
                    lt[i] = now
                v[i] = nb

        for line in fh:
            if line.startswith("#"):
                now = int(line[1:])
                if t_open is None:
                    t_open = now
                    for ident in val:
                        last_t[ident] = [t_open] * len(val[ident])
                if t1 is not None and now > t1:
                    t_close = t1
                    break
                if not started and now >= t0:
                    started = True
                    for ident in val:
                        last_t[ident] = [t_open] * len(val[ident])
                continue
            if not line.strip() or line[0] in "$r":
                continue
            c = line[0]
            if c in "bB":
                bits, ident = line[1:].strip().split()
                n = len(ident_nets.get(ident, [[]])[0]) or len(bits)
                bits = bits.rjust(n, "0" if bits[0] in "01" else bits[0])[-n:]
                setbits(ident, list(bits))
            elif c in "01xzXZ":
                ident = line[1:].strip()
                setbits(ident, [c])
        if t_close is None:
            t_close = now
        if t_open is None:
            t_open = 0

    win_fs = max(1, t_close - t_open)
    win_ns = win_fs / tick_ns
    ncyc = win_ns / args.period

    # ---- emit --------------------------------------------------------------
    hit = miss = 0
    lines = []
    # The population the -global default actually lands on. Deduplicated BY VCD
    # IDENTIFIER, and an identifier any of whose names matched is left out
    # entirely: Verilator dumps one net under every scope it crosses, so
    # `clk_i` also appears as `u_ring.clk_i`, `clkb`, `u_retime.CLK` and three
    # more, all sharing one identifier. Those aliases are the FASTEST nets in
    # the design and they are annotated already, so leaving them in the
    # population lifts its mean from 0.0069 to 0.0421 per ns on fast_counter
    # and the block reports 8.69 mW instead of 5.39.
    matched_ident = set()
    seen_ident = {}
    for ident, groups in ident_nets.items():
        if ident not in val:
            continue
        tr, ht, lt, v = trans[ident], hitime[ident], last_t[ident], val[ident]
        for names in groups:
            for i, net in enumerate(names):
                if i >= len(tr):
                    break
                pin = drivers.get(net)
                if pin is None:
                    miss += 1
                    continue
                high = ht[i] + ((t_close - lt[i]) if v[i] == "1" else 0)
                dens = max(tr[i] / win_ns, args.act_floor)
                duty = min(1.0, max(0.0, high / win_fs))
                lines.append("set_power_activity -pin [get_pins {%s}] "
                             "-density %.6g -duty %.4f" % (pin, dens, duty))
                matched_ident.add(ident)
                hit += 1

    for ident, groups in ident_nets.items():
        if ident in matched_ident or ident not in trans:
            continue
        names = groups[0]
        if any(n in have for n in names):
            continue
        # a macro's simulation internals sit BELOW its instance path, so the
        # test is on every prefix and not on the first component
        if any(n[:i] in macros
               for n in names for i in range(len(n)) if n[i:i + 1] == "."):
            continue
        tr = trans[ident]
        n = len(groups[0])
        seen_ident[ident] = (max(sum(tr) / len(tr) / win_ns, args.act_floor), n)
    wsum = sum(d * n for d, n in seen_ident.values())
    wn = sum(n for _, n in seen_ident.values())
    mean = wsum / wn if wn else 0.0
    unmatched = [1] * wn
    with open(args.outfile, "w") as fo:
        fo.write("# generated by scripts/vcd_activity_sta.py -- do not edit\n")
        fo.write("# %s, window %.1f ns = %.1f clock cycles of %.3f ns\n"
                 % (os.path.basename(args.vcd), win_ns, ncyc, args.period))
        fo.write("# %d nets annotated, %d VCD nets absent from the netlist\n"
                 % (hit, miss))
        if args.global_density:
            fo.write("# and the mean over the %d VCD nets that did NOT survive "
                     "synthesis by name, for every net that takes the "
                     "default\n" % len(unmatched))
            fo.write("set_power_activity -global -density %.6g\n" % mean)
        fo.write("\n".join(lines) + "\n")
    print("%s: %d pins annotated, %d VCD nets not in the netlist, "
          "window %.1f ns (%.0f cycles), mean density %.4g /ns"
          % (args.outfile, hit, miss, win_ns, ncyc, mean))


if __name__ == "__main__":
    main()
