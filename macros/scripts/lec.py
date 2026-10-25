#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: RTL vs hardened netlist equivalence check (EQY, slang gold)
# Vendored from iic-jku/OpenBLAU scripts/lec.py at 690a7c71, with the changes doc/rtl2gds.md lists.
"""Prove a hardened gate netlist equal to its RTL, with EQY.

Gold is the RTL named by the macro's LibreLane config, read through
yosys-slang: synthesis used read_verilog -sv, and a check through the same
frontend proves the netlist equal to its misparse (OpenBLAU doc/lec.md). A config with
USE_SLANG gets read_verilog -sv as gold instead, the other frontend again.

Gate is the netlist on the Liberty functions, rewritten exactly first:
  - physical cells and CTS dummy loads removed;
  - every ICG unwrapped: its flops back on the ungated clock, D' = E ? D : Q;
  - a register stored inverted (reset-to-1 on a clear-only flop) flipped
    back, so its name carries the true value.
Every cell type must be modelled, physical, or a declared hard macro: a cell
without a function reads as a blackbox, and a blackbox proves trivially.
A hard macro becomes ports on both sides (expose -evert): its inputs are
compared, its outputs come in as matched free inputs.

Matching is by name, ports and registers only, minus the FSM state registers
synthesis re-encodes (yosys fsm_detect on gold, read as synthesis reads it).
A single-clock block with an rst_ni starts both sides from one reset cycle.
--gold-booth needs OpenBLAU's booth_check.py, which is not vendored here.

Exits 0 on PASS, 1 on FAIL (a counterexample), 2 on TIMEOUT (a partition
unfinished), 3 on ERROR; with --expect-fail, 0 only on FAIL. The verdict and
the netlist's sha256 go to <out>/verdict.json.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EZ130_LIB = Path(os.environ.get("EZ130_DIR", REPO / "ip" / "ez130_8t_v1p1")) / "lib" / "ez130_8t_tt_1p20v_25c.lib"


def rx(n):
    """n as a regex for an EQY /pattern/, which ends at any slash, escaped or not."""
    return re.escape(n).replace("/", r"\x2f")

# the IHP pad ring: corners, fillers, bond pads and supply pads carry no signal
PHYSICAL = re.compile(r"^(FILLER\w*|DECAP\w*|WELLTAP\w*|ANTENNA\w*|"
                      r"sg13cmos5l_(fill|decap)_\d+|sg13cmos5l_antennanp|"
                      r"sg13cmos5l_(Corner|Filler\d+|IOPad(Vdd|Vss|IOVdd|IOVss))|"
                      r"sg13cmos5l_ip__bondpad_\w+)$")
SUPPLY_PINS = {"iovdd", "iovss", "vdd", "vss"}
INST_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s+(\\\S+\s|[A-Za-z_][\w$]*)\s*\((.*?)\);",
                     re.S | re.M)
PIN_RE = re.compile(r"\.(\w+)\(\s*(\{[^}]*\}|\\\S+\s|[^()\s]+|)\s*\)")
NET_RE = re.compile(r"\\\S+|[A-Za-z_][\w$]*(?:\[\d+\])?|\d+'[bh][0-9a-fA-FxXzZ]+")
KEYWORDS = {"input", "output", "wire", "assign", "module", "inout", "reg"}


# ---------------------------------------------------------------- Liberty

def _groups(text, kind):
    """(name, body) for every top-level `kind (name) { ... }` in text."""
    out, i = [], 0
    pat = re.compile(r"\b%s\s*\(\s*\"?([^)\"]*)\"?\s*\)\s*\{" % kind)
    while True:
        m = pat.search(text, i)
        if not m:
            return out
        depth, j = 1, m.end()
        while depth:
            c = text[j]
            depth += (c == "{") - (c == "}")
            j += 1
        out.append((m.group(1), text[m.end():j - 1]))
        i = j


def _attr(body, name):
    m = re.search(r"\b%s\s*:\s*\"?([^\";]*)\"?\s*;" % name, body)
    return m.group(1).strip() if m else None


def parse_liberty(path):
    """{cell: info} with pins, ff/latch/ICG facts, enough for the guards."""
    text = re.sub(r"/\*.*?\*/", "", Path(path).read_text(), flags=re.S)
    text = text.replace("\\\n", " ")
    cells = {}
    for name, body in _groups(text, "cell"):
        pins = {}
        for pname, pbody in _groups(body, "pin"):
            pins[pname] = {
                "dir": _attr(pbody, "direction"),
                "function": _attr(pbody, "function"),
                "state_function": _attr(pbody, "state_function"),
                "cg_clock": _attr(pbody, "clock_gate_clock_pin") == "true",
                "cg_enable": _attr(pbody, "clock_gate_enable_pin") == "true",
                "cg_test": _attr(pbody, "clock_gate_test_pin") == "true",
                "cg_out": _attr(pbody, "clock_gate_out_pin") == "true",
            }
        ffs = [(v.split(",")[0].strip(), {k: _attr(b, k) for k in ("clocked_on", "next_state",
                                              "clear", "preset")})
               for v, b in _groups(body, "ff")]
        cells[name] = {
            "pins": pins,
            "ff": ffs,
            "latch": bool(_groups(body, "latch")),
            "icg": _attr(body, "clock_gating_integrated_cell"),
        }
    return cells


def has_function(info):
    """Every output pin carries a function Yosys can build."""
    outs = [p for p in info["pins"].values() if p["dir"] == "output"]
    return bool(outs) and all(p["function"] for p in outs)


def is_buffer(info):
    ins = [n for n, p in info["pins"].items() if p["dir"] == "input"]
    outs = [p for p in info["pins"].values() if p["dir"] == "output"]
    return (len(ins) == 1 and len(outs) == 1
            and (outs[0]["function"] or "").strip("() ") == ins[0])


def is_inverter(info):
    ins = [n for n, p in info["pins"].items() if p["dir"] == "input"]
    outs = [p for p in info["pins"].values() if p["dir"] == "output"]
    return (len(ins) == 1 and len(outs) == 1
            and (outs[0]["function"] or "").replace(" ", "") in
            (f"!{ins[0]}", f"(!{ins[0]})", f"{ins[0]}'"))


def set_model(cell, info):
    """Behavioural twin of a clear-only flop that stores its complement:
    the clear becomes a set, D and Q are the true value (see rewrite)."""
    ck, d, q = flop_pins(info)
    clr = info["ff"][0][1]["clear"]
    ins = [n for n, p in info["pins"].items() if p["dir"] == "input"]
    head = f"module LEC_SET_{cell} ({', '.join(ins + [q])});\n"
    head += "".join(f"    input {n};\n" for n in ins) + f"    output reg {q};\n"
    if clr:
        m = re.fullmatch(r"\(?\s*(!?)\s*(\w+)\s*\)?", clr)
        if not m:
            raise SystemExit(f"LEC: cannot model clear '{clr}' of {cell}")
        edge = "negedge" if m.group(1) else "posedge"
        act = f"!{m.group(2)}" if m.group(1) else m.group(2)
        body = (f"    always @(posedge {ck} or {edge} {m.group(2)})\n"
                f"        if ({act}) {q} <= 1'b1; else {q} <= {d};\n")
    else:
        body = f"    always @(posedge {ck}) {q} <= {d};\n"
    return head + body + "endmodule\n"


def icg_pins(info):
    """(clock, enable, test or None, out) of an ICG cell."""
    p = info["pins"]
    get = lambda k: next((n for n, v in p.items() if v[k]), None)
    ck, en, te = get("cg_clock"), get("cg_enable"), get("cg_test")
    out = get("cg_out") or next(n for n, v in p.items() if v["dir"] == "output")
    if not (ck and en):
        raise SystemExit("ICG without clock/enable pin attributes")
    return ck, en, te, out


def flop_pins(info):
    """(clock pin, D pin, Q pin) of a plain posedge flop, else None."""
    if len(info["ff"]) != 1:
        return None
    var, ff = info["ff"][0]
    ck, d = ff["clocked_on"], ff["next_state"]
    if not (ck and d and re.fullmatch(r"\w+", ck) and re.fullmatch(r"\w+", d)):
        return None
    q = next((n for n, v in info["pins"].items()
              if v["dir"] == "output" and (v["function"] or "").strip("() ") == var),
             None)
    return (ck, d, q) if q else None


# ---------------------------------------------------------------- netlist

def parse_netlist(text):
    """(header, {name: [cell, {pin: net}]}, tail) of a flat LibreLane netlist."""
    start = text.index(");") + 2
    insts = {}
    for m in INST_RE.finditer(text, start):
        cell, name, pins = m.group(1), m.group(2).strip(), m.group(3)
        if cell in KEYWORDS:
            continue
        insts[name] = [cell, {p: n.strip() for p, n in PIN_RE.findall(pins)}]
    return insts


def module_ports(text):
    """{port: (dir, width)} of the first module in text."""
    ports = {}
    for d, rng, names in re.findall(
            r"^\s*(input|output|inout)\s+(?:wire\s+)?(\[\s*\d+\s*:\s*\d+\s*\])?\s*([^;]+);",
            text, re.M):
        w = 1
        if rng:
            a, b = map(int, re.findall(r"\d+", rng))
            w = abs(a - b) + 1
        for n in names.split(","):
            ports[n.strip()] = (d, w)
    return ports


def nets(conn):
    """The nets of one pin connection, a {concatenation} split."""
    return [n.strip() for n in NET_RE.findall(conn)] if conn.startswith("{") else [conn]


def v(net):
    """A net as Verilog: an escaped identifier needs its terminating space."""
    return net + " " if net.startswith("\\") and not net.startswith("{") else net


def output_ports(path):
    """{module: {output port}} of a Verilog stub or model file, ANSI or not."""
    res = {}
    text = re.sub(r"/\*.*?\*/", "", re.sub(r"//[^\n]*", "", Path(path).read_text()), flags=re.S)
    for mod, body in re.findall(r"^\s*module\s+(\w+)(.*?)\bendmodule", text, re.S | re.M):
        body = re.sub(r"#\s*\((?:[^()]|\([^()]*\))*\)", "", body, count=1)  # parameters
        head, _, rest = body.partition(");")
        clean = lambda t: re.findall(r"[A-Za-z_]\w*", re.sub(
            r"\[[^]]*\]|=.*|\b(wire|logic|reg|signed|var|bit)\b", " ", t, flags=re.S))
        cur, outs = None, set()
        for it in re.split(r"[,(]", head):  # ANSI: the direction carries over
            m = re.match(r"\s*(input|output|inout)\b(.*)", it, re.S)
            if m:
                cur, it = m.group(1), m.group(2)
            names = clean(it)
            if cur == "output" and names:
                outs.add(names[-1])
        for decl in re.findall(r"^\s*output\b([^;]*);", rest, re.M):  # non-ANSI
            outs |= set(clean(decl))
        res[mod] = outs
    return res


def port_dirs(path):
    """{module: [(port, direction)]} of a Verilog model file, ANSI or not."""
    res = {}
    text = re.sub(r"/\*.*?\*/", "", re.sub(r"//[^\n]*", "", Path(path).read_text()), flags=re.S)
    for mod, body in re.findall(r"^\s*module\s+(\w+)(.*?)\bendmodule", text, re.S | re.M):
        head, _, rest = body.partition(");")
        order = re.findall(r"[A-Za-z_]\w*", re.sub(r"\b(input|output|inout|wire|reg)\b|\[[^]]*\]",
                                                  " ", head))
        dirs = {}
        for d, names in re.findall(r"\b(input|output|inout)\b([^;,)]*(?:,\s*(?!input|output|inout)"
                                   r"[A-Za-z_]\w*)*)", head + ";" + rest):
            for n in re.findall(r"[A-Za-z_]\w*", re.sub(r"\[[^]]*\]|\b(wire|reg)\b", " ", names)):
                dirs.setdefault(n, d)
        res[mod] = [(n, dirs[n]) for n in order if n in dirs]
    return res


def pad_stubs(files, out):
    """Pad cells as port-only blackboxes, supplies dropped and inout read as
    input like an analog macro pin: a signal pad is everted and compared like
    a macro. Returns (stub file, {pad module with a signal pin})."""
    mods = {}
    for f in files:
        mods.update(port_dirs(f))
    lines, signal = [], set()
    for mod, ports in sorted(mods.items()):
        sig = [(n, "input" if d == "inout" else d) for n, d in ports if n not in SUPPLY_PINS]
        signal |= {mod} if sig else set()
        lines.append(f"(* blackbox *)\nmodule {mod} ({', '.join(n for n, _ in sig)});\n"
                     + "".join(f"    {d} {n};\n" for n, d in sig) + "endmodule\n")
    stub = Path(out) / "lec_pads.v"
    stub.write_text("".join(lines))
    return stub, signal, set(mods) - signal


def comb_loops(insts, drop, lib, drivers, loads):
    """Net sets of the combinational cycles (Tarjan SCC, iterative)."""
    comb = lambda i: (i not in drop and insts[i][0] in lib and not lib[insts[i][0]]["ff"]
                      and has_function(lib[insts[i][0]]))
    succ = {}
    for net, drv in drivers.items():
        succ[net] = [o for li, _ in loads.get(net, []) if comb(li)
                     for p, o in insts[li][1].items()
                     if lib[insts[li][0]]["pins"].get(p, {}).get("dir") == "output"]
    index, low, stack, on, out, n = {}, {}, [], set(), [], 0
    for root in succ:
        if root in index:
            continue
        work = [(root, iter(succ.get(root, [])))]
        index[root] = low[root] = n; n += 1; stack.append(root); on.add(root)
        while work:
            v, it = work[-1]
            w = next(it, None)
            if w is None:
                work.pop()
                if work:
                    low[work[-1][0]] = min(low[work[-1][0]], low[v])
                if low[v] == index[v]:
                    scc = set()
                    while True:
                        x = stack.pop(); on.discard(x); scc.add(x)
                        if x == v:
                            break
                    if len(scc) > 1 or v in succ.get(v, []):
                        out.append(scc)
            elif w not in index:
                index[w] = low[w] = n; n += 1; stack.append(w); on.add(w)
                work.append((w, iter(succ.get(w, []))))
            elif w in on:
                low[v] = min(low[v], index[w])
    return out


def named_net(n):
    """A net name synthesis or we made up carries no meaning to match."""
    return bool(n) and not re.match(r"^(_\d+_|net\d+|clknet_|lec_|1'b)", n)


def rewrite(text, lib, blackboxes, mutate=None, outports=None, gold_rst=None,
            stamp=False, pairs=(), mutate_pair=None):
    """Gate netlist ready for Yosys: physical cells out, ICGs unwrapped.

    stamp: every flop's Q also as lec_pq_<k>, for pair_registers. pairs:
    its (gold, flop instance, kind) list, applied after the name rules.
    Returns (text, report dict). Raises SystemExit on anything unmodelled.
    """
    insts = parse_netlist(text)
    report = {"cells": len(insts), "physical": 0, "icg": 0, "gated_flops": 0}

    # coverage guard
    bad = set()
    for name, (cell, _) in insts.items():
        if PHYSICAL.match(cell) or cell in blackboxes:
            continue
        info = lib.get(cell)
        if info is None or not (has_function(info) or info["icg"]):
            bad.add(cell)
    if bad:
        raise SystemExit("LEC: unmodelled cell types (would read as blackboxes): "
                         + " ".join(sorted(bad)))

    outports = outports or {}
    drivers, loads = {}, {}
    for name, (cell, pins) in insts.items():
        info = lib.get(cell)
        for p, conn in pins.items():
            d = info["pins"].get(p, {}).get("dir") if info else None
            if cell in outports:
                d = "output" if p in outports[cell] else "input"
            for n in nets(conn) if conn else []:
                (drivers if d == "output" else loads).setdefault(n, []).append((name, p))

    ports = {re.sub(r"\[.*", "", p) for p in module_ports(text)}
    ports |= {n for n in list(drivers) + list(loads) if re.sub(r"\[.*", "", n) in ports}
    extra, drop = [], set()
    held = set()  # Q nets a gated flop's hold mux reads: no instance load
    for name, (cell, pins) in list(insts.items()):
        if PHYSICAL.match(cell):
            if any(lib.get(cell, {"pins": {}})["pins"].get(p, {}).get("dir") == "output"
                   for p in pins):
                raise SystemExit(f"LEC: physical cell {name} drives a net")
            drop.add(name)
            report["physical"] += 1
    for name, (cell, pins) in list(insts.items()):
        info = lib.get(cell)
        if not info or not info["icg"]:
            continue
        ck, en, te, out = icg_pins(info)
        clk, gclk = pins[ck], pins[out]
        e = v(pins[en]) if not te or not pins.get(te) else f"({v(pins[en])} | {v(pins[te])})"
        stack, flops = [gclk], []
        while stack:
            net = stack.pop()
            for li, lp in loads.get(net, []):
                if li in drop:
                    continue  # physical: an antenna diode on a gated clock
                lcell = insts[li][0]
                linfo = lib[lcell] if lcell in lib else None
                outs = [insts[li][1].get(n) for n, v in (linfo or {"pins": {}})["pins"].items()
                        if v["dir"] == "output"]
                if outs and not any(o and (loads.get(o) or o in ports) for o in outs):
                    drop.add(li)  # CTS dummy load (clkload*): output drives nothing
                    report["clkload"] = report.get("clkload", 0) + 1
                    continue
                if linfo and is_buffer(linfo):
                    stack.append(insts[li][1][next(n for n, v in linfo["pins"].items()
                                                   if v["dir"] == "output")])
                    continue
                fp = flop_pins(linfo) if linfo else None
                if not fp or lp != fp[0]:
                    raise SystemExit(f"LEC: ICG {name} drives {lcell} {li}/{lp}, "
                                     "not a posedge flop clock")
                flops.append(li)
        for fi in flops:
            fck, fd, fq = flop_pins(lib[insts[fi][0]])
            fpins = insts[fi][1]
            nd = f"lec_d_{report['gated_flops']}"
            extra.append(f" wire {nd};\n assign {nd} = {e} ? {v(fpins[fd])} : {v(fpins[fq])};")
            held.add(fpins[fq])
            fpins[fck], fpins[fd] = clk, nd
            report["gated_flops"] += 1
        drop.add(name)
        report["icg"] += 1

    # A register that resets to 1 on a clear-only flop is stored inverted:
    # INV -> D, Q -> INV -> the named register net. Its state then has no name
    # EQY can match, and an unmatched state bit starts anywhere in the proof.
    # Undo it exactly: a set-flop twin on D' = ~D drives the INV outputs.
    models = {}
    twins = []

    def twin(name, outs=(), redrive=True):
        """The flop becomes a set-flop twin on D' = ~D, so its Q lec_tq_k is
        the true value: it drives `outs`, and ~Q the old Q net if redrive."""
        cell, pins = insts[name]
        ck, d, q = flop_pins(lib[cell])
        tq, td = f"lec_tq_{len(twins)}", f"lec_td_{len(twins)}"
        extra.append(f" wire {tq};\n wire {td};\n assign {td} = ~{v(pins[d])};")
        extra.extend(f" assign {v(o)} = {tq};" for o in outs)
        if redrive:
            extra.append(f" assign {v(pins[q])} = ~{tq};")
        models[cell] = set_model(cell, lib[cell])
        insts[name] = [f"LEC_SET_{cell}", {**pins, d: td, q: tq}]
        twins.append(name)
        return tq

    report["inverted_flops"] = 0
    for name, (cell, pins) in list(insts.items()):
        info = lib.get(cell)
        fp = flop_pins(info) if info and name not in drop else None
        if not fp or named_net(pins.get(fp[2])):
            continue
        qnet = pins[fp[2]]
        inv = [(li, lp) for li, lp in loads.get(qnet, [])
               if insts[li][0] in lib and is_inverter(lib[insts[li][0]])]
        outs = [insts[li][1][next(n for n, p in lib[insts[li][0]]["pins"].items()
                                  if p["dir"] == "output")] for li, _ in inv]
        if not any(named_net(o) for o in outs):
            continue
        drop.update(li for li, _ in inv)
        # The hold mux of an unwrapped ICG reads Q too, and it is no instance:
        # left out, Q floats and the proof toggles the register at will.
        twin(name, outs, len(inv) < len(loads.get(qnet, [])) or qnet in ports or qnet in held)
        report["inverted_flops"] += 1

    # The same storage trick with the name left on the flop: dpll's
    # cfg_dco_gain[1] resets to 1 in the RTL, the gate flop clears to 0 and
    # the consumers absorbed the inverters, so the name means the complement.
    # Gold's reset value exposes it: flip the flop the same way and move
    # every other reader of the net onto ~Q.
    flips = {}
    for name, (cell, pins) in insts.items():
        info = lib.get(cell)
        fp = flop_pins(info) if info and name not in drop else None
        if not fp or not gold_rst or not named_net(pins.get(fp[2])):
            continue
        ff = info["ff"][0][1]
        gate_rst = 0 if ff["clear"] else 1 if ff["preset"] else None
        key = pins[fp[2]].lstrip("\\").strip()
        if gate_rst is not None and gold_rst.get(key, gate_rst) != gate_rst:
            if gate_rst == 1:
                raise SystemExit(f"LEC: {key} presets where gold clears: no twin for that")
            if key in ports or re.sub(r"\[\d+\]$", "", key) in ports:
                raise SystemExit(f"LEC: port {key} is stored inverted")
            flips[name] = pins[fp[2]]
    ren = {n: f"lec_qn_{k}" for k, n in enumerate(flips.values())}
    rename_tok = None
    if ren:
        rename_tok = re.compile("|".join(
            re.escape(v(n)) if n.startswith("\\") else
            r"(?<![\w$\\])" + re.escape(n) + r"(?![\w$\[])"
            for n in sorted(ren, key=len, reverse=True)))
        rmap = {**ren, **{v(n): v(q) for n, q in ren.items()}}
        fix = lambda t: rename_tok.sub(lambda m: rmap[m.group(0)], t)
        for name, (cell, pins) in insts.items():
            for p_, conn in pins.items():
                if flips.get(name) == conn:
                    continue  # the flipped flop's own Q keeps the name
                pins[p_] = ren.get(conn, conn) if not conn.startswith("{") else fix(conn)
        extra[:] = [fix(line) for line in extra]
        for name, net in flips.items():
            cell, pins = insts[name]
            ck, d, q = flop_pins(lib[cell])
            qn, td = ren[net], f"lec_tdn_{ren[net][7:]}"
            extra.append(f" wire {qn};\n assign {qn} = ~{v(net)};\n"
                         f" wire {td};\n assign {td} = ~{v(pins[d])};")
            models[cell] = set_model(cell, lib[cell])
            insts[name] = [f"LEC_SET_{cell}", {**pins, d: td}]
    report["polarity_flips"] = len(flips)

    # Registers the name rules miss, paired by simulation (pair_registers).
    # A complement is the folded reset-to-1 case: the twin's true value gets
    # a name. Each lecp_<j> is one more match point, itself proven by EQY.
    pair_maps, pair_lines, lecp = [], [], {}
    for j, (gold, name, kind) in enumerate(pairs):
        cell, pins = insts[name]
        q = pins[flop_pins(lib[cell[8:] if cell.startswith("LEC_SET_") else cell])[2]]
        if kind == "name":
            pair_maps.append((gold, q.lstrip("\\").strip()))
            continue
        if name not in lecp:  # a flop carrying merged registers is twinned once
            src = twin(name) if kind == "complement" else v(q)
            lecp[name] = f"lecp_{j}"
            pair_lines.append(f" wire lecp_{j};\n assign lecp_{j} = {src};")
        pair_maps.append((gold, lecp[name]))
    report["pair_maps"] = pair_maps
    if mutate_pair is not None:
        gold, name, kind = pairs[mutate_pair % len(pairs)]
        cell, pins = insts[name]
        d = flop_pins(lib[cell[8:] if cell.startswith("LEC_SET_") else cell])[1]
        extra.append(f" wire lec_mutp;\n assign lec_mutp = ~{v(pins[d])};")
        pins[d] = "lec_mutp"
        report["mutated"] = f"pair {gold}: {name} ({kind}) D inverted"

    # EQY matches nets by name. Only ports and flop outputs keep a meaning
    # through synthesis; a combinational net keeps its name on whatever the
    # optimizer left there, so it must not become a cut point.
    base = lambda n: re.sub(r"\[\d+\]$", "", n.lstrip("\\").strip())
    named = {base(n) for n in re.findall(r"^\s*wire\s+(?:\[[^]]*\]\s*)?(\\\S+|\w+)", text, re.M)
             if named_net(n)}
    regs, mbits = set(), set()  # mbits: the same, bit by bit (pair_registers)
    strip = lambda n: n.lstrip("\\").strip()
    for name, (cell, pins) in insts.items():
        c0 = cell[8:] if cell.startswith("LEC_SET_") else cell
        fp = flop_pins(lib[c0]) if c0 in lib and name not in drop else None
        if fp and named_net(pins.get(fp[2])):
            regs.add(base(pins[fp[2]]))
            mbits.add(strip(pins[fp[2]]))
    # outputs of hand cells and blackboxes are real signals. Their INPUT nets
    # are not: the gate may name a pin's net after any of its aliases (rfout's
    # a_i[29] for slice_en[30]), which gold computes separately
    bbout = set()
    for name, (cell, pins) in insts.items():
        if name in drop or not (cell in blackboxes or lib.get(cell, {}).get("model")):
            continue
        for p, c in pins.items():
            if p in outports.get(cell, ()):
                bbout |= {n for n in nets(c) if named_net(n)}
                regs |= {base(n) for n in nets(c) if named_net(n)}
                mbits |= {strip(n) for n in nets(c) if named_net(n)}
    for line in extra:
        m = re.match(r"\s*assign (\S+) *= lec_tq_\d+;", line)
        if m:
            regs.add(base(m.group(1)))
            mbits.add(strip(m.group(1)))
    # A combinational loop (tempsensor's ring oscillator) only proves cut at
    # a matched net on it: keep the loop's named nets, fail if it has none.
    loops = comb_loops(insts, drop, lib, drivers, loads)
    for scc in loops:
        cut = {base(n) for n in scc if named_net(n)}
        if not cut:
            raise SystemExit(f"LEC: combinational loop through unnamed nets {sorted(scc)[:4]}")
        regs |= cut
        mbits |= {strip(n) for n in scc if named_net(n)}
        loopnets = {n for s in loops for n in s}
    report["loops"] = len(loops)
    extra += pair_lines  # after the scan above: a lecp_ name is no gold keeper

    # Bound: compared, never reused as a free input downstream. The gate may
    # feed a top output or a macro pin back into logic gold computes
    # separately (rfout's ramp chain off slice_en[30]), or name after a pin
    # the register's own hold path (dpll's dco.dsm_en_i). Not a clock or a
    # net off an input port: every flop hangs off those, binding them merges
    # all into one partition.
    inports = {p for p, (d, w) in module_ports(text).items() if d == "input"}
    clocknets = set()
    for name, (cell, pins) in insts.items():
        c0 = cell[8:] if cell.startswith("LEC_SET_") else cell
        fp = flop_pins(lib[c0]) if c0 in lib and name not in drop else None
        stack = [pins[fp[0]]] if fp else []
        while stack:
            n_ = stack.pop()
            if n_ in clocknets:
                continue
            clocknets.add(n_)
            for di, _ in drivers.get(n_, []):
                c = insts[di][0]
                if c in lib and (is_buffer(lib[c]) or is_inverter(lib[c])):
                    stack.append(insts[di][1][next(pp for pp, vv in lib[c]["pins"].items()
                                                   if vv["dir"] == "input")])
    def hub(net, depth=0):
        if net in clocknets or re.sub(r"\[\d+\]$", "", net) in inports:
            return True
        for di, _ in drivers.get(net, []):
            c = insts[di][0]
            if depth < 16 and c in lib and (is_buffer(lib[c]) or is_inverter(lib[c])):
                a_ = next(pp for pp, vv in lib[c]["pins"].items() if vv["dir"] == "input")
                return hub(insts[di][1][a_], depth + 1)
        return False

    # A top output a flop drives through buffers is that register, and gold
    # reads it by that name: a bind there only merges (dpll's register block,
    # loop filter and lock detector into one partition). Not a macro pin: the
    # gate reads the pin net in the register's own hold path, gold its state
    # (dpll cfg_reg_en, oscreg_en_i: a false FAIL without the bind).
    def regq(net, depth=0):
        for di, dp in drivers.get(net, []):
            c = insts[di][0]
            c0 = c[8:] if c.startswith("LEC_SET_") else c
            fp = flop_pins(lib[c0]) if c0 in lib else None
            if fp:
                return dp == fp[2]
            if depth < 16 and c in lib and is_buffer(lib[c]):
                a_ = next(pp for pp, vv in lib[c]["pins"].items() if vv["dir"] == "input")
                return regq(insts[di][1][a_], depth + 1)
        return False
    free = lambda n: hub(n) or regq(n)
    # A clock off a macro pin needs no second name: the pin is compared as a
    # port, and after flatten every buffer of the tree is a wire, so its names
    # are aliases EQY cuts differently on the two sides (the chip's clk_ref
    # off the FREF pad: 4 false FAILs). A ring oscillator's cut stays.
    for n in bbout & clocknets:
        if n not in (loopnets if loops else set()):
            regs.discard(base(n))
            mbits.discard(strip(n))
    binds = set()
    for p, (d, w) in module_ports(text).items():
        if d == "output":
            bits = [p] if w == 1 else [f"{p}[{i}]" for i in range(w)]
            if not all(free(b) for b in bits):
                binds.add(base(p))
    for name, (cell, pins) in insts.items():
        if cell in blackboxes:
            binds |= {f"{name.lstrip(chr(92)).strip()}.{p}" for p, c in pins.items()
                      if p not in outports.get(cell, ())
                      and not all(hub(n) for n in nets(c))}
    report["binds"] = sorted(binds)

    # Several macro pins on one clock tree rooted at a macro or pad output
    # are one signal: after flatten gold's hand root buffer and the gate's
    # CTS buffers are wires, and EQY cuts the aliases differently on the two
    # sides (the chip: dpll clk_i/clk_ref_i and the SRAM's A_CLK off the FREF
    # pad, false FAILs). The root is compared; those pins are not.
    def troot(net, depth=0):
        for di, dp in drivers.get(net, []):
            c = insts[di][0]
            if depth < 32 and c in lib and is_buffer(lib[c]):
                a_ = next(pp for pp, vv in lib[c]["pins"].items() if vv["dir"] == "input")
                return troot(insts[di][1][a_], depth + 1)
            return (di, dp)
        return None
    trees = {}
    for name, (cell, pins) in insts.items():
        if cell in blackboxes:
            for p, c in pins.items():
                if p not in outports.get(cell, ()) and c and not c.startswith("{"):
                    trees.setdefault(troot(c), []).append(f"{name.lstrip(chr(92)).strip()}.{p}")
    report["nomatch_pins"] = sorted(
        pin for r, pins in trees.items()
        if r and insts[r[0]][0] in blackboxes and len(pins) > 1
        and insts[r[0]][1].get(r[1]) in clocknets for pin in pins)
    report["bbinsts"] = sorted(n.lstrip("\\").strip() for n, (c, _) in insts.items()
                               if c in blackboxes and n not in drop)

    # How many clocks: EQY's own flow (async2sync, formalff -clk2ff) assumes
    # one global clock without checking it. Count the flops' clock roots
    # through buffers; several roots, a negedge or a hand cell -> multiclock.
    def root(net, depth=0):
        for di, dp in drivers.get(net, []):
            c = insts[di][0]
            if depth < 16 and c in lib and (is_buffer(lib[c]) or is_inverter(lib[c])):
                a = next(pp for pp, vv in lib[c]["pins"].items() if vv["dir"] == "input")
                return root(insts[di][1][a], depth + 1)
            return f"{di}.{dp}"
        return net
    clocks, odd = set(), 0
    for name, (cell, pins) in insts.items():
        c0 = cell[8:] if cell.startswith("LEC_SET_") else cell
        if name in drop or c0 not in lib:
            continue
        if lib[c0].get("model"):
            odd += 1
        elif lib[c0]["ff"] or lib[c0]["latch"]:
            fp = flop_pins(lib[c0])
            if fp:
                clocks.add(root(pins[fp[0]]))
            else:
                odd += 1
    report["clocks"] = len(clocks)
    report["multiclock"] = bool(len(clocks) > 1 or odd)
    report["nomatch"] = sorted(named - regs - ports)
    report["keep"] = sorted(regs | {base(p) for p in ports})
    report["regs"] = len(regs)
    if stamp:
        report["matchbits"] = sorted(mbits)
        report["ports"] = sorted({base(p) for p in module_ports(text)})
        # a model cell is flattened on both sides: its registers match by name
        report["model_insts"] = sorted(strip(n) for n, (c, _) in insts.items()
                                       if n not in drop and lib.get(c, {}).get("model"))
        report["stamps"] = {}
        for name, (cell, pins) in insts.items():
            c0 = cell[8:] if cell.startswith("LEC_SET_") else cell
            fp = flop_pins(lib[c0]) if c0 in lib and name not in drop else None
            if not fp or not pins.get(fp[2]):
                continue
            s = f"lec_pq_{len(report['stamps'])}"
            ff = lib[c0]["ff"][0][1]
            report["stamps"][s] = {"inst": name, "q": pins[fp[2]], "cell": cell,
                                   "clear": bool(ff["clear"]), "preset": bool(ff["preset"])}
            extra.append(f" wire {s};\n assign {s} = {v(pins[fp[2]])};")

    if mutate is not None:
        # not a model cell: its one "_o" pin is a placeholder (tspc_dff sorts first)
        comb = sorted(n for n, (c, _) in insts.items()
                      if n not in drop and c in lib and has_function(lib[c])
                      and not lib[c].get("model")
                      and not lib[c]["ff"] and not is_buffer(lib[c]))
        victim = comb[mutate % len(comb)]
        cell, pins = insts[victim]
        op = next(n for n, v in lib[cell]["pins"].items() if v["dir"] == "output")
        net = pins[op]
        pins[op] = "lec_mut"
        extra.append(f" wire lec_mut;\n assign {v(net)} = ~lec_mut;")
        report["mutated"] = f"{victim} ({cell}) output inverted"

    # re-emit: header (ports, wires, assigns) + surviving instances
    body_start = min(m.start() for m in INST_RE.finditer(text, text.index(");") + 2)
                     if m.group(1) not in KEYWORDS)
    head = text[:body_start]
    assigns = "\n".join(re.findall(r"^\s*assign .*;$", text[body_start:], re.M))
    if rename_tok:
        assigns = fix(assigns)
    lines = [head]
    for name, (cell, pins) in insts.items():
        if name in drop:
            continue
        conns = ",\n    ".join(f".{p}({v(n)})" for p, n in pins.items())
        lines.append(f" {cell} {name} ({conns});")
    lines += extra
    lines.append(assigns)
    lines.append("endmodule")
    lines += models.values()
    return "\n".join(lines) + "\n", report


# ---------------------------------------------------------------- config

def resolve(v, cfg_dir):
    if isinstance(v, list):
        return [resolve(x, cfg_dir) for x in v]
    if isinstance(v, str) and v.startswith("dir::"):
        return str((cfg_dir / v[5:]).resolve())
    if isinstance(v, str) and "::" in v:
        raise SystemExit(f"LEC: unsupported config path prefix in {v}")
    return v


def read_config(path):
    path = Path(path).resolve()
    cfg = yaml.safe_load(path.read_text())
    get = lambda k, d=None: resolve(cfg.get(k, d), path.parent)
    return {
        "top": cfg["DESIGN_NAME"],
        "files": get("VERILOG_FILES", []),
        "defines": cfg.get("VERILOG_DEFINES") or [],
        "incdirs": get("VERILOG_INCLUDE_DIRS", []),
        "models": get("EXTRA_VERILOG_MODELS", []),
        "pads": get("PAD_VERILOG_MODELS", []),
        "slang": bool(cfg.get("USE_SLANG")),
        "clock": cfg.get("CLOCK_PORT"),
        "macros": {m: resolve(v.get("vh", []), path.parent)
                   for m, v in (cfg.get("MACROS") or {}).items()},
    }


# ---------------------------------------------------------------- EQY

def eqy_script(cfg, lib_path, gate_v, blackboxes, models, nomatch=(), pins=(), keep=(),
               maps=(), binds=(), work=".", multiclock=False, reset=None, part_timeout=None,
               gold_nomatch=(), known_open=(), no_pins=(), clock_pins=(), gold_booth=(),
               sweep=False):
    """The .eqy file: both sides flattened, macros everted, PDR per partition.
    gold_booth: booth_check's rewrite of gold's multipliers, after its flatten.
    sweep: ABC's scorr (SAT sweeping) ahead of PDR, plain PDR as the fallback."""
    defs = " ".join(f"-D{d}" for d in cfg["defines"])
    incs = " ".join(f"-I{d}" for d in cfg["incdirs"])
    common = [f"read_liberty -ignore_miss_func {lib_path}"]
    for m in models:
        common.append(f"read_verilog -sv -overwrite {m}")
    bb_files = list(dict.fromkeys(f for files in blackboxes.values() for f in files))
    # a stub the RTL already `includes must not reach slang twice
    srcs = list(cfg["files"]) + [str(f) for d in cfg["incdirs"]
                                 for f in Path(d).glob("*.*v")]
    def reached(b):
        return any(re.search(r"^\s*module\s+%s\b" % b, Path(f).read_text(), re.M)
                   for f in srcs if Path(f).is_file())
    slang_bb = [f for b, files in blackboxes.items() if not reached(b) for f in files]
    # yosys-slang cannot put a real parameter on a blackbox cell, and dpll
    # overrides fast_counter's; its value plays no part here, so gold reads
    # a copy of each stub with real parameters as integers
    def tame(f):
        t = Path(f).read_text()
        if not (re.search(r"\bparameter\s+real\b", t)
                and any(re.search(r"^\s*module\s+%s\b" % b, t, re.M) for b in blackboxes)):
            return f
        c = Path(work) / ("stub_" + Path(f).name)
        c.write_text(re.sub(r"\bparameter\s+real\b", "parameter integer", t))
        return str(c)
    gold_files = [tame(f) for f in cfg["files"] + slang_bb]
    # an analog inout pin (dco's vmon) everts into a port nothing drives;
    # its connectivity is LVS's job, so the port stubs read it as an input
    def lib_stub(f):
        t = Path(f).read_text()
        if not re.search(r"\binout\b", t):
            return f
        c = Path(work) / ("lib_" + Path(f).name)
        c.write_text(re.sub(r"\binout\b", "input", t))
        return str(c)
    bb_read = [f"read_verilog -sv -lib -overwrite {defs} {incs} {lib_stub(f)}" for f in bb_files]
    if cfg["slang"] and cfg.get("sv2v"):
        # synthesized through slang, so gold goes through yosys's own frontend,
        # which cannot read the chip's boot_ctrl ROM: sv2v first (OpenBLAU doc/lec.md).
        # The stubs come first: sv2v's output does not define the macros
        gold = [*bb_read, f"read_verilog -formal {cfg['sv2v']}"]
    elif cfg["slang"]:
        gold = [f"read_verilog -sv -formal {defs} {incs} "
                          + " ".join(cfg["files"])]
    else:
        # slang inlines a stub it did not elaborate itself: hand it the stub
        # and name it, or the macro's outputs come out undriven
        # --ignore-initial: silicon powers up anywhere; an RTL initial value on
        # a reset-less flop would make gold 0 where the gate is free
        # --allow-use-before-declare: dpll.sv uses fc_tdc_en_o before its
        # declaration, an LRM error read_verilog accepts silently
        # --no-implicit-memories: an unpacked array stays registers, not a memory
        # whose mapped bits have hidden names, see array_maps()
        gold = [f"read_slang {defs} {incs} --top {cfg['top']} --ignore-initial "
                "--allow-use-before-declare --no-implicit-memories "
                + "".join(f"--blackboxed-module {b} " for b in blackboxes)
                + " ".join(gold_files)]
    bb = " ".join(blackboxes)
    prep = [f"hierarchy -top {cfg['top']}"]
    if bb:
        # keep: a macro with no output (rfout_drv, OUT read as an input) is
        # otherwise removed as unused, and then nothing checks its pins
        prep += [f"blackbox {bb}",
                 "setattr -set keep 1 " + " ".join(f"t:{b}" for b in blackboxes)]
    # flatten leaves every cell's pins behind as public `<inst>.<PIN>` wires,
    # aliases that clash with the RTL names in matching
    prep += ["proc -norom", "flatten"]  # a ROM ($mem_v2) stops xprop
    # a pad with no signal pin (the chip's supply pads) is a blackbox no
    # evert removes, and `sim` cannot run with one left
    # the cells, then the modules (`=`: a selection skips a blackbox module
    # without it), as EQY partitions every module left
    if no_pins:
        prep += ["delete " + " ".join(f"t:{m}" for m in no_pins),
                 "delete " + " ".join(f"={m}" for m in no_pins)]
    if pins:
        prep.append("rename -hide " + " ".join(f"w:*.{p}" for p in sorted(pins)))
    # One clock: async2sync, EQY's own model, which assumes that one clock
    # unchecked. Several or both edges (fast_counter, tempsensor):
    # clk2fflogic, exact. Only then: its sampled-clock wires are shared by
    # every flop, and EQY merges all that share an unmatched net (dpll went
    # to 1 partition of 50). SBY's per-partition multiclock needs xprop off,
    # which loses gold-X-is-don't-care (fast_counter: 24 false fails).
    # dffunmap first: async2sync gives gold's coarse $aldff an immediate
    # output override under reset but the gate's fine $_DFF_PN0_ a synchronous
    # reset, a one-cycle difference in every reset partition (dpll)
    # simplemap splits every multi-bit flop to single bits: a gold cell whose
    # dead bits synthesis dropped would otherwise pull every reader of its
    # live bits into one partition (the DSA1 CIC output, cic_out[4:0])
    prep += ["memory", "dffunmap", "simplemap t:$dff t:$ff",
             "clk2fflogic" if multiclock else "async2sync", "opt_clean"]
    # A hard macro becomes ports, not an EQY blackbox: its pins as outputs
    # are compared on their whole cone, its outputs come in as free inputs
    # matched by instance name. An EQY blackbox cuts at its input nets, and
    # the gate reuses such a net elsewhere under another alias (rfout).
    evert = [f"expose -evert " + " ".join(f"t:{b}" for b in blackboxes)] if blackboxes else []
    # synthesis Booth-encoded the multipliers; gold follows, proven by booth_check
    at = prep.index("flatten")
    gold_prep = prep[1:at + 1] + list(gold_booth) + prep[at + 1:]
    if clock_pins:  # EQY matches every port: an unmatched pin must not be one
        evert.append("delete -port " + " ".join(f"w:{n}" for n in clock_pins))
    # Both sides start from one reset cycle, as silicon does (rst_ctrl): an
    # unmatched register otherwise starts anywhere in the gate and at 0 in
    # gold, whose X then fails to reach an FSM's next state.
    # A register with no reset still starts free.
    if reset and not multiclock:
        evert += [f"sim -clock {reset[0]} -resetn {reset[1]} -rstlen "
                  f"{reset[2] if len(reset) > 2 else 1} -n {reset[2] if len(reset) > 2 else 1} -w"]
    return "\n".join([
        "[options]", "splitnets on", "",
        # the stubs go in after `hierarchy`: it drops the module of a cell
        # slang imported as a blackbox, and evert needs its port directions
        "[gold]", "plugin -i slang", *common, *gold, prep[0],
        *(bb_read if not cfg["slang"] else []), *gold_prep,
        # a gold name the gate lacks cannot match, and an alias of an input
        # port (clk_ref = clk_ref_i) makes EQY cut a port as a partition.
        # %d only takes the top two selections: tag the keepers instead.
        "setattr -set lec_keep 1 " + " ".join(f"w:{k}" for k in keep) + "".join(
            f" w:{g}" for g in dict.fromkeys(re.sub(r"\[\d+\]$", "", g) for g, _ in maps)
            if g not in keep),
        "rename -hide w:* a:lec_keep %d", *evert, "",
        # names the flow made up (buffers, CTS, ours) are never match points
        "[gate]", *common, *bb_read, f"read_verilog -sv {gate_v}", *prep,
        "rename -hide w:net* w:_*_ w:clknet_* w:lec_*", *evert, "",
        "[match *]", *(f"gate-nomatch /^{rx(n)}(\\[\\d+\\])?$/" for n in nomatch),
        # registers synthesis merged: same D, same clock, equal after one edge
        *(f"gold-match /^{rx(g)}$/ /^{rx(t)}$/" for g, t in maps),
        # a gold wire named like the gate register it was paired to: two gold
        # names on one gate net make EQY group their cones into one fragment
        *(f"gold-nomatch /^{rx(n)}$/" for n in gold_nomatch),
        *(f"{s}-nomatch /^{rx(n)}$/" for n in clock_pins for s in ("gold", "gate")), "",
        *(["[collect *]", *(f"bind /^{rx(b)}(\\[\\d+\\])?$/" for b in binds), ""]
          if binds else []),
        # No `use sat`: its miter takes a gold X as don't-care, and with
        # -set-init-undef a partition holding state passed with a mutated
        # clock-gate enable. PDR (sby, xprop) caught it. OpenBLAU doc/lec.md
        # yosys-abc and yices are the only solvers in the image
        # a partition declared open (LEC_OPEN) is not attempted: UNKNOWN at once.
        # EQY matches apply/noapply by the full partition name, no pattern
        *(["[strategy open]", "use dummy", *(f"apply {n}" for n in known_open), ""]
          if known_open else []),
        # PDR has no SAT sweeping, so structure both sides share (gold Booth-
        # encoded) buys it nothing: dpll's multiplier partitions ran past 30 min,
        # scorr first proves them in a second. EQY runs pdr after an unsettled one.
        *(["[strategy sweep]", *(f"noapply {n}" for n in known_open), "use sby",
           "engine abc scorr; pdr", *([f"timeout {part_timeout}"] if part_timeout else []), ""]
          if sweep else []),
        # timeout: SBY stops the partition and EQY's status file says TIMEOUT
        "[strategy pdr]", *(f"noapply {n}" for n in known_open), "use sby", "engine abc pdr",
        *([f"timeout {part_timeout}"] if part_timeout else []), "",
    ]) + "\n"


def prefix(eqy_text, side):
    """The [gold] or [gate] script of an .eqy file up to its flatten: the
    design read and flattened, before any clock model or renaming."""
    s = eqy_text.split(f"[{side}]\n", 1)[1].split("\n[", 1)[0].splitlines()
    return s[:next(i for i, l in enumerate(s) if l.startswith("flatten")) + 1]


def gold_fsms(eqy_text, out, synth=None):
    """Registers synthesis re-encodes: yosys's own fsm_detect on gold, read the
    way LibreLane's synthesis reads it. FSM_RECODE turns dpll's u_sar.state_q
    one-hot under the same name, so its bits are no match points. synth: the
    read_slang line for a USE_SLANG design, whose gold is sv2v's."""
    gold = prefix(eqy_text, "gold")
    ys, fl = Path(out) / "gold_fsm.ys", Path(out) / "gold_fsm.txt"
    lines = []
    for l in gold:
        if l.startswith("plugin"):
            continue
        if l.startswith("read_slang"):  # synthesis reads with read_verilog
            l = "read_verilog -sv " + " ".join(
                t for t in l.split()[1:] if t.startswith(("-D", "-I")) or t.endswith((".sv", ".v")))
        elif synth and l.startswith("read_verilog -formal"):
            l = synth
        lines.append(l)
    # synth's own order: fsm_detect skips a $dffe, so no enable folding first
    # fsm_detect marks what it takes "auto"; an RTL fsm_encoding "none" it skips
    lines += ["opt_expr", "opt_clean", "opt -nodffe -nosdff", "fsm_detect",
              f"select -write {fl} a:fsm_encoding=auto"]
    ys.write_text("\n".join(lines) + "\n")
    if subprocess.call(["yosys", "-q", "-l", str(Path(out) / "gold_fsm.log"), "-s", str(ys)],
                       stdout=subprocess.DEVNULL) != 0:
        raise SystemExit(f"LEC: FSM detection failed, see {out}/gold_fsm.log")
    return sorted({l.split("/", 1)[1] for l in fl.read_text().split() if "/" in l})


def not_gold_regs(keep, gold_ffs, gold_names, mapped, ports):
    """Gate register names that gold has as a net but not as a register. yosys
    names a re-encoded FSM's one-hot bits after gold's decode wires
    (n296 = state == 2'b01), and matched by name they would cut gold's
    combinational net against a gate flop."""
    base = lambda n: re.sub(r"\[\d+\]$", "", n)
    regs = {base(n) for ns in gold_ffs for n in ns}
    nets = {base(n) for n in gold_names}
    return sorted(r for r in keep if r in nets and r not in regs | set(mapped) | set(ports))


def array_maps(gate_bits, gold_ffs):
    """(gold, gate) name pairs for unpacked arrays. read_verilog -sv made
    synthesis one register per element, a[i] with bits a[i][j]. slang with
    --no-implicit-memories keeps one register a, element 0 of an ascending
    [0:N-1] array in its top bits. N is the gate's element count, and an
    array whose gold width does not split into N words is left alone. An
    element missing its top bit but not the one below gets the top bit mapped
    there: synthesis merged two copies of the sign."""
    width = {}
    for ns in gold_ffs:
        for n in ns:
            m = re.fullmatch(r"(.*)\[(\d+)\]", n)
            if m:
                width[m[1]] = max(width.get(m[1], 0), int(m[2]) + 1)
    elems = {}
    for b in gate_bits:
        m = re.fullmatch(r"(.*)\[(\d+)\]\[(\d+)\]", b)
        if m and m[1] in width:
            elems.setdefault(m[1], set()).add((int(m[2]), int(m[3])))
    maps = []
    for a, ij in sorted(elems.items()):
        n = max(i for i, _ in ij) + 1
        if width[a] % n:
            continue
        w = width[a] // n
        maps += [(f"{a}[{(n - 1 - i) * w + j}]", f"{a}[{i}][{j}]") for i, j in sorted(ij)]
        # a top bit synthesis merged into the bit below it, two copies of the sign. EQY still
        # proves the mapped bit's own next state, so a wrong pairing fails, it does not hide.
        maps += [(f"{a}[{(n - 1 - i) * w + w - 1}]", f"{a}[{i}][{w - 2}]") for i in range(n)
                 if (i, w - 1) not in ij and (i, w - 2) in ij]
    return maps


def gold_regs(eqy_text, out):
    """Gold's registers by a Yosys pass over the [gold] script of `eqy_text`
    up to its flatten: ({net[bit]: async reset value}, [the public names of
    each flop output bit], {every public net[bit]})."""
    gold = prefix(eqy_text, "gold")
    js = Path(out) / "gold_rst.json"
    ys = Path(out) / "gold_rst.ys"
    ys.write_text("\n".join(gold + ["opt_clean", f"write_json {js}"]) + "\n")  # merge $buf aliases
    if subprocess.call(["yosys", "-q", "-l", str(Path(out) / "gold_rst.log"), str(ys)],
                       stdout=subprocess.DEVNULL) != 0:
        raise SystemExit(f"LEC: gold read failed, see {out}/gold_rst.log")
    top = next(m for m in json.loads(js.read_text())["modules"].values()
               if m.get("attributes", {}).get("top"))
    names = {}
    for n, w in top["netnames"].items():
        if w.get("hide_name"):
            continue
        off = int(w.get("offset", 0))
        for i, bit in enumerate(w["bits"]):
            names.setdefault(bit, []).append(n if len(w["bits"]) == 1 and not off
                                             else f"{n}[{i + off}]")
    rst, ffs = {}, []
    for c in top["cells"].values():
        q = c["connections"].get("Q", [])
        if re.search(r"dff|^\$ff$", c["type"]):
            ffs += [sorted(names[b]) for b in q if b in names]
        if c["type"] in ("$adff", "$adffe"):
            val = c["parameters"]["ARST_VALUE"]
            val = val if isinstance(val, str) else format(val, f"0{len(q)}b")
            vals = [val[::-1][i] for i in range(len(q))]
        elif c["type"] in ("$aldff", "$aldffe"):  # slang's form: a constant AD
            vals = [str(b) for b in c["connections"]["AD"]]
        else:
            continue
        for bit, val in zip(q, vals):
            if val in ("0", "1"):
                for n in names.get(bit, []):
                    rst[n] = int(val)
    return rst, ffs, {n for ns in names.values() for n in ns}


# ---------------------------------------------------------------- pairing

def aag_read(aag, amap):
    """An ASCII AIGER and yosys's -map: (header, inputs, latches, outputs,
    ands, {'input'|'output': [name per index]})."""
    lines = Path(aag).read_text().splitlines()
    m, ni, nl, no, na = map(int, lines[0].split()[1:6])
    ins = [int(l) for l in lines[1:1 + ni]]
    lat = [list(map(int, l.split())) for l in lines[1 + ni:1 + ni + nl]]
    outs = [int(l) for l in lines[1 + ni + nl:1 + ni + nl + no]]
    ands = [tuple(map(int, l.split())) for l in lines[1 + ni + nl + no:1 + ni + nl + no + na]]
    names = {"input": [None] * ni, "output": [None] * no}
    for l in Path(amap).read_text().splitlines():
        f = l.split()
        if len(f) == 4 and f[0] in names:
            names[f[0]][int(f[1])] = f[3]
    return ins, lat, outs, ands, names


def aig_compile(ins, lat, outs, ands):
    """step(inputs, latches, M) -> (outputs, next latches) as straight-line
    Python: every AIG variable a local, M the all-lanes mask."""
    lit = lambda x: ("0" if x == 0 else "M" if x == 1 else
                     f"a{x >> 1}" if not x & 1 else f"(a{x >> 1} ^ M)")
    src = ["def step(I, L, M):"]
    src += [f" a{x >> 1} = I[{k}]" for k, x in enumerate(ins)]
    src += [f" a{l[0] >> 1} = L[{k}]" for k, l in enumerate(lat)]
    src += [f" a{a >> 1} = {lit(b)} & {lit(c)}" for a, b, c in sorted(ands)]
    src.append(" return [" + ", ".join(lit(x) for x in outs) + "], ["
               + ", ".join(lit(l[1]) for l in lat) + "]")
    env = {}
    exec(compile("\n".join(src), "<aig>", "exec"), env)
    return env["step"]


def stimulus(names, lanes, cycles, seed, reset=None, rstlen=1):
    """Per input a word per cycle, seeded by its name so both sides draw the
    same stream. A third of the lanes toggle each bit at 1/2, 1/8 and 1/64 a
    cycle: long quiet windows reach deep states, fast ones cover the rest.
    In half the lanes a bus is sign-extended from a random width: a uniform
    24-bit word always saturates a clamp (dpll's mod_i), and the clamped bits
    then all carry one trace."""
    import random
    M = (1 << lanes) - 1
    thirds = [sum(1 << i for i in range(lanes) if i % 3 == k) for k in range(3)]
    out = {}
    for n in names:
        if n is None:
            continue
        r = random.Random(f"{seed}/{n}")
        w, seq = r.getrandbits(lanes), []
        for t in range(cycles):
            if n == reset:
                seq.append(0 if t < rstlen else M)
                continue
            b = [r.getrandbits(lanes) for _ in range(6)]
            w ^= ((b[0] & thirds[0]) | (b[0] & b[1] & b[2] & thirds[1])
                  | (b[0] & b[1] & b[2] & b[3] & b[4] & b[5] & thirds[2]))
            seq.append(w)
        out[n] = seq
    buses = {}
    for n in out:
        m = re.fullmatch(r"(.*)\[(\d+)\]", n)
        if m and n != reset:
            buses.setdefault(m.group(1), []).append((int(m.group(2)), n))
    for bus, bits in sorted(buses.items()):
        if len(bits) < 4:
            continue
        bits = [n for _, n in sorted(bits)]
        r = random.Random(f"{seed}/{bus}/ext")
        pats = []  # the width changes per cycle: few lanes may reach the state that samples it
        for _ in range(8):
            width = [r.randrange(1, len(bits) + 1) if l % 2 else 0 for l in range(lanes)]
            pats.append(([sum(1 << l for l in range(lanes) if width[l] == j + 1)
                          for j in range(len(bits))],
                         [sum(1 << l for l in range(lanes) if 0 < width[l] <= k)
                          for k in range(len(bits))]))
        for t in range(cycles):
            sel, ext = pats[t % len(pats)]
            sign = 0
            for j, n in enumerate(bits):
                sign |= out[n][t] & sel[j]
            for k, n in enumerate(bits):
                out[n][t] = (out[n][t] & ~ext[k] & M) | (sign & ext[k])
    return out


def aig_traces(aag, amap, stim, lanes, cycles):
    """{output name: (blake2b of its trace in canonical polarity, polarity,
    toggles)}. Equal and complement traces share a hash."""
    ins, lat, outs, ands, names = aag_read(aag, amap)
    step = aig_compile(ins, lat, outs, ands)
    M = (1 << lanes) - 1
    zero = [0] * cycles
    ivec = [stim.get(n, zero) if n else zero for n in names["input"]]
    L = [M if len(l) > 2 and l[2] == 1 else 0 for l in lat]  # uninitialized: 0
    h = [hashlib.blake2b(digest_size=16) for _ in outs]
    first = [None] * len(outs)
    prev = [None] * len(outs)
    tog = [0] * len(outs)
    nb = (lanes + 7) // 8
    for t in range(cycles):
        o, L = step([s[t] for s in ivec], L, M)
        for k, w in enumerate(o):
            if first[k] is None:
                first[k] = w & 1
            h[k].update(((w ^ M) if first[k] else w).to_bytes(nb, "little"))
            if prev[k] is not None:
                tog[k] += (w ^ prev[k]).bit_count()
            prev[k] = w
    return {n: (h[k].hexdigest(), first[k], tog[k])
            for k, n in enumerate(names["output"]) if n}


def aig_export(script, expose, out, tag, evert, multiclock):
    """The design of a yosys script prefix as ASCII AIGER, the nets `expose`
    selects as outputs; the clock model is the one EQY gets. None on failure
    (a combinational loop has no AIGER)."""
    aag, amap = Path(out) / f"{tag}.aag", Path(out) / f"{tag}.map"
    ys = Path(out) / f"{tag}.ys"
    ys.write_text("\n".join(script + [
        "memory", "dffunmap", expose, "clk2fflogic" if multiclock else "async2sync",
        # a blackbox left after the evert has no pins here (the chip's supply
        # pads), and AIGER has no cell for it
        "dffunmap", "opt_clean", *evert, "delete t:* t:$* %d", "chformal -remove",
        "setundef -zero",
        "setundef -undriven -anyseq", "splitnets -ports", "techmap", "opt_clean",
        # techmap of a ROM lookup ($shiftx) makes x bits of its own
        "setundef -zero", "aigmap", "opt_clean", f"write_aiger -ascii -map {amap} {aag}"]) + "\n")
    rc = subprocess.call(["yosys", "-q", "-l", str(Path(out) / f"{tag}.log"), "-s", str(ys)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return (aag, amap) if rc == 0 else None


PAIR_QUIET = 4  # lane toggles below which a trace pairs with nothing


def classify(gold_t, gate_t, targets, stamps, gold_names, gold_hash):
    """Pairs for the gold targets off their traces: [(gold, stamp, kind)] and
    one (class, gold, stamp or '', note) row per target. kind: 'name' (an
    equal named flop), 'alias' (equal, hidden), 'complement' (hidden)."""
    byhash = {}
    for s, (h, pol, tog) in gate_t.items():
        if s in stamps and tog >= PAIR_QUIET:
            byhash.setdefault(h, []).append((s, pol))
    pairs, rows, used = [], [], {}
    for gold, seen in sorted(targets.items()):
        if seen is None:
            rows.append(("unseen", gold, "", "not a register output after the clock model"))
            continue
        h, pol, tog = gold_t[seen]
        if tog == 0:
            # not tied to a gate constant: the gate never reads that net, so
            # gold's readers would see a free value there (dpll sar_load)
            rows.append(("constant", gold, "", ""))
            continue
        if tog < PAIR_QUIET:
            rows.append(("quiet", gold, "", f"{tog} toggles"))
            continue
        qn = lambda s: stamps[s]["q"].lstrip("\\").strip()
        cands = byhash.get(h, [])
        # a candidate matched by name to a gold register of the same trace is
        # that register's flop: only a merge (cwg_q[5] into cw_q[5]) takes it
        expl = [c for c in cands if gold_hash.get(qn(c[0])) == h]
        pick = [c for c in cands if c not in expl] or expl
        if len(pick) != 1:
            rows.append(("ambiguous" if pick else "unpaired", gold, "",
                         " ".join(qn(s) for s, _ in pick[:4])))
            continue
        s, spol = pick[0]
        st = stamps[s]
        if spol == pol:
            kind = "name" if named_net(qn(s)) else "alias"
        elif qn(s) in gold_names:
            rows.append(("conflict", gold, s, f"complement of {qn(s)}, a gold name"))
            continue
        elif st["cell"].startswith("LEC_SET_") or st["preset"] or not st["clear"]:
            rows.append(("conflict", gold, s, f"complement on {st['cell']}: no exact twin"))
            continue
        else:
            kind = "complement"
        # synthesis merges duplicate registers (the chip's two csn
        # synchronizers): one flop may carry several gold names, one polarity
        if used.setdefault(s, kind) != kind:
            rows.append(("conflict", gold, s, f"flop already paired as {used[s]}"))
            continue
        pairs.append((gold, s, kind))
        rows.append((kind, gold, s, f"{st['inst']} Q={qn(s)}"))
    return pairs, rows


def pair_registers(gold_eqy, gate_eqy, rep, ffs, gold_names, skip, hide, out, evert,
                   multiclock, reset, lanes, cycles, seed):
    """Gold register bits no gate name reaches (a reset-to-1 bit stored
    inverted with the inverter folded away, a register renamed or merged),
    paired with the gate flop whose simulated trace equals them or their
    complement. A pair is only a hint: EQY proves every one it becomes."""
    t0 = time.time()
    ports, mb = set(rep["ports"]), set(rep["matchbits"])
    base = lambda n: re.sub(r"\[\d+\]$", "", n)
    inside = tuple(f"{i}." for i in rep["model_insts"])
    hit = lambda a: a in mb or base(a) in ports or a.startswith(inside)
    targets = {}
    for al in ffs:
        if any(hit(a) or a in skip or base(a) in skip for a in al):
            continue
        # gold hides every `<inst>.<PIN>` name: the one to match must not be one
        pin = lambda a: "." in a and base(a).rsplit(".", 1)[1] in hide
        targets[min(al, key=lambda a: (pin(a), a.count("."), len(a), a))] = al
    stats = {"targets": len(targets)}
    if not targets:
        return [], [], stats, []
    g = aig_export(prefix(gold_eqy, "gold"), "expose -dff", out, "pair_gold", evert, multiclock)
    h = aig_export(prefix(gate_eqy, "gate"), "expose w:lec_pq_*", out, "pair_gate", evert,
                   multiclock)
    if not (g and h):
        stats["skipped"] = f"no AIGER, see {out}/pair_{'gold' if not g else 'gate'}.log"
        return [], [], stats, []
    names = set()
    for m in (g[1], h[1]):
        names |= {l.split()[3] for l in Path(m).read_text().splitlines()
                  if l.startswith("input ") and len(l.split()) == 4}
    stim = stimulus(sorted(names), lanes, cycles, seed, reset)
    gold_t = aig_traces(*g, stim, lanes, cycles)
    gate_t = aig_traces(*h, stim, lanes, cycles)
    gold_hash = {}
    for al in ffs:
        seen = next((a for a in al if a in gold_t), None)
        if seen:
            gold_hash.update({a: gold_t[seen][0] for a in al})
    seen_of = {t: next((a for a in al if a in gold_t), None) for t, al in targets.items()}
    stamps = rep["stamps"]
    pairs, rows = classify(gold_t, gate_t, seen_of, stamps, gold_names, gold_hash)
    for kind, *_ in rows:
        stats[kind] = stats.get(kind, 0) + 1
    # dpll's ref_phase_q[10:0] sits on flops named phase_err_mod, which gold
    # computes (ref - fc): only its register may match there
    regnames = {a for al in ffs for a in al}
    unmatch = sorted({q for g, s, k in pairs if k == "name"
                      for q in [stamps[s]["q"].lstrip("\\").strip()]
                      if q in gold_names and q not in regnames})
    stats["seconds"] = round(time.time() - t0)
    return [(gold, stamps[s]["inst"], kind) for gold, s, kind in pairs], rows, stats, unmatch


# ---------------------------------------------------------------- verdict

VERDICT_RC = {"PASS": 0, "OPEN": 0, "FAIL": 1, "TIMEOUT": 2, "ERROR": 3}


def tally(work):
    """{partition: status} from EQY's work dir: what its strategy wrote (PASS,
    FAIL, UNKNOWN, TIMEOUT, ERROR; pdr, or open for a LEC_OPEN one), None if
    unfinished."""
    parts = {}
    for p in sorted((Path(work) / "partitions").glob("*.il")):
        got = [s.read_text().split() for s in
               sorted((Path(work) / "strategies" / p.stem).glob("*/status"))]
        got = [w[0] for w in got if w]
        parts[p.stem] = next((s for s in ("FAIL", "PASS") if s in got), got[-1] if got else None)
    return parts


def judge(rc, log_text, parts, lost=(), timed_out=False, known_open=()):
    """FAIL (a counterexample) beats ERROR beats TIMEOUT beats OPEN beats PASS.
    A PASS needs every partition proven and EQY's own verdict; OPEN, every one
    proven but those declared open (--open)."""
    status = set(parts.values())
    if "FAIL" in status:
        return "FAIL"
    if lost or "ERROR" in status:
        return "ERROR"
    if not parts:
        return "TIMEOUT" if timed_out else "ERROR"
    unfinished = {n for n, s in parts.items() if s != "PASS"}  # also UNKNOWN, TIMEOUT
    if unfinished:
        return "OPEN" if unfinished <= set(known_open) else "TIMEOUT"
    if timed_out:
        return "TIMEOUT"
    ok = rc == 0 and "Successfully proved designs equivalent" in log_text
    return "PASS" if ok else "ERROR"


def session_pids(sid):
    """Live processes of session sid, off /proc (Linux); a zombie counts dead."""
    pids = []
    for d in Path("/proc").glob("[0-9]*"):
        try:
            f = (d / "stat").read_text().rsplit(")", 1)[1].split()
            if int(f[3]) == sid and f[0] != "Z":
                pids.append(int(d.name))
        except (OSError, ValueError, IndexError):
            pass
    return pids


def kill_session(sid, grace=10):
    """SIGTERM, then SIGKILL, the whole session: EQY and SBY put each job in
    its own process group, so killing EQY's group leaves yosys-abc running."""
    linux = Path("/proc").is_dir()  # elsewhere the group is all we reach
    for sig, wait in ((signal.SIGTERM, grace), (signal.SIGKILL, 2)):
        for pid in session_pids(sid) if linux else [-sid]:
            try:
                os.kill(pid, sig)
            except OSError:
                pass
        t = time.time()
        while linux and time.time() - t < wait and session_pids(sid):
            time.sleep(0.2)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    """Repo-relative where possible: verdict.json must not carry a host path."""
    p = Path(path).resolve()
    return str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p)


def run(args):
    cfg = read_config(args.config)
    if args.gold:  # the RTL before a pre-pass that the config hands synthesis
        cfg["files"] = [str(Path(g).resolve()) for g in args.gold]
    lib_path = Path(args.liberty or EZ130_LIB).resolve()
    lib = parse_liberty(lib_path)
    bbs = {}
    for b in filter(None, (args.blackbox or "").split(",")):
        b, _, stub = b.partition("=")
        files = [str(Path(stub).resolve())] if stub else cfg["macros"].get(b) or []
        if not files:
            raise SystemExit(f"LEC: blackbox {b} needs a stub: MACROS.{b}.vh or {b}=<file>")
        bbs[b] = files
    models = [str(Path(m).resolve()) for m in args.model] + [
        m for m in cfg["models"] if not any(Path(m).stem == b for b in bbs)]
    for m in models:  # a modelled hand cell passes the coverage guard
        for mod in re.findall(r"^\s*module\s+(\w+)", Path(m).read_text(), re.M):
            lib.setdefault(mod, {"pins": {"_o": {"dir": "output", "function": "model"}},
                                 "ff": [], "latch": False, "icg": None, "model": True})

    nl = Path(args.netlist).resolve()
    # a block's netlist: <macro>/build/lec; the chip's (netlist/nl): <repo>/build/lec
    home = next((q.parent for q in nl.parents if q.name == "flow"), REPO)
    out = Path(args.out).resolve() if args.out else home / "build" / "lec" / cfg["top"]
    if args.mutate is not None or args.mutate_pair is not None:
        out = out.with_name(out.name + "_mut")
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    nl_text = nl.read_text()
    synth, no_pins = None, set()
    if cfg["slang"]:
        cfg["sv2v"] = out / "gold_sv2v.v"
        cmd = (["sv2v", *(f"-D{d}" for d in cfg["defines"]), *(f"-I{d}" for d in cfg["incdirs"]),
                f"--top={cfg['top']}", "-w", str(cfg["sv2v"])] + list(cfg["files"]))
        if subprocess.call(cmd, stdout=subprocess.DEVNULL) != 0:
            raise SystemExit("LEC: sv2v failed on the RTL: " + " ".join(cmd))
        synth = (" ".join(["read_slang", *(f"-D{d}" for d in cfg["defines"]),
                           *(f"-I{d}" for d in cfg["incdirs"]), "--top", cfg["top"],
                           "--ignore-initial", "--allow-use-before-declare"]
                          + list(cfg["files"])))
    if cfg["pads"]:  # every signal pad the netlist uses is a macro
        stub, signal, no_pins = pad_stubs(cfg["pads"], out)
        used = set(re.findall(r"^\s*(sg13cmos5l_\w+)\s", nl_text, re.M))
        bbs.update({m: [str(stub)] for m in sorted(signal & used)})

    outs = {}
    for f in [f for fs in bbs.values() for f in fs] + models:
        outs.update(output_ports(f))
    missing = [b for b in bbs if b not in outs]
    if missing:
        raise SystemExit(f"LEC: no module {missing} in the blackbox stubs")
    no_pins = sorted(no_pins)
    gold_eqy = eqy_script(cfg, lib_path, "", bbs, models, work=out, no_pins=no_pins)
    gold_rst, gold_ffs, gold_names = gold_regs(gold_eqy, out)
    fsms = gold_fsms(gold_eqy, out, synth)
    booth_lines, booth_rows = [], []
    if args.gold_booth:  # the proofs outlive out/, which every run clears
        try:
            import booth_check
        except ImportError:
            raise SystemExit("LEC: --gold-booth needs OpenBLAU's booth_check.py, not vendored here")
        booth_lines, booth_rows = booth_check.check(prefix(gold_eqy, "gold"), out / "booth",
                                                    args.jobs, cache=out.parent / "booth_proofs")
    tops = module_ports(nl_text)
    rst = args.reset or next((p for p in sorted(tops) if re.fullmatch(r"rst_ni?", p)
                              and tops[p][0] == "input"), None)
    clock = args.clock or cfg["clock"]
    # a reset or clock off a pad is an everted pad pin, <instance>.<output>
    everted = {f"{i.lstrip(chr(92)).strip()}.{q}" for i, (c, _) in parse_netlist(nl_text).items()
               if c in bbs for q in outs.get(c, ())}
    for flag, name in (("--clock", args.clock), ("--reset", args.reset)):
        if name and name not in everted and tops.get(name, ("",))[0] != "input":
            raise SystemExit(f"LEC: {flag} {name} is no input and no macro output")
    maps = [m.split("=", 1) for m in args.map]
    if args.array_maps:
        gate_bits = re.findall(r"^\s*wire\s+\\(\S+\[\d+\]\[\d+\])\s*;", nl_text, re.M)
        amaps = array_maps(gate_bits, gold_ffs)
        maps += [list(m) for m in amaps]
        print(f"LEC array maps: {len(amaps)} register bits")
    pairs, unmatch = [], []
    if not args.no_pair:
        text1, rep1 = rewrite(nl_text, lib, set(bbs), None, outs, gold_rst, stamp=True)
        (out / "pair_gate.v").write_text(text1)
        gate1_eqy = eqy_script(cfg, lib_path, out / "pair_gate.v", bbs, models, work=out)
        evert = ["expose -evert " + " ".join(f"t:{b}" for b in bbs)] if bbs else []
        pairs, rows, pst, unmatch = pair_registers(
            gold_eqy, gate1_eqy, rep1, gold_ffs, gold_names, set(fsms) | {g for g, _ in maps},
            set(re.findall(r"^\s*\.(\w+)\(", nl_text, re.M)), out, evert,
            rep1["multiclock"] or args.multiclock, rst,
            args.pair_lanes, args.pair_cycles, args.pair_seed)
        (out / "pairs.txt").write_text("".join(f"{c:10s} {g:40s} {n}\n" for c, g, s, n in rows))
        paired = sum(pst.get(k, 0) for k in ("name", "alias", "complement"))
        print(f"LEC pairing: paired={paired} " + " ".join(f"{k}={v}" for k, v in pst.items())
              + (f"  ({out / 'pairs.txt'})" if rows else ""))
    if args.mutate_pair is not None and not pairs:
        raise SystemExit("LEC: --mutate-pair with no pairs")
    gate_text, rep = rewrite(nl_text, lib, set(bbs), args.mutate, outs, gold_rst,
                             pairs=pairs, mutate_pair=args.mutate_pair)
    maps += [list(m) for m in rep.pop("pair_maps")]
    gate_v = out / "gate.v"
    gate_v.write_text(gate_text)
    eqy = out / f"{cfg['top']}.eqy"
    nomatch, keep, binds = rep.pop("nomatch"), rep.pop("keep"), rep.pop("binds")
    unmatch_pins = rep.pop("nomatch_pins")
    nomatch = sorted(set(nomatch) | set(fsms))
    rep["fsm_recoded"] = len(fsms)
    decodes = not_gold_regs(keep, gold_ffs, gold_names, {re.sub(r"\[\d+\]$", "", t) for _, t in maps},
                            {re.sub(r"\[\d+\]$", "", p) for p in tops})
    nomatch = sorted(set(nomatch) | set(decodes))
    rep["gate_regs_not_gold_regs"] = len(decodes)
    reset = (clock, rst, args.rstlen) if rst and (clock in tops or clock in everted) else None
    rep["reset_start"] = bool(reset) and not (rep["multiclock"] or args.multiclock)
    rep_bbinsts = rep.pop("bbinsts")
    used = {c for c in re.findall(r"^\s*([A-Za-z_]\w*)\s+\\?\S+\s*\(", gate_text, re.M)}
    pins = {p for c in used if c in lib for p in lib[c]["pins"]}
    pins |= set(re.findall(r"^\s*\.(\w+)\(", gate_text, re.M))  # model/macro pins
    eqy.write_text(eqy_script(cfg, lib_path, gate_v, bbs, models, nomatch, pins, keep,
                              maps, binds, out,
                              rep["multiclock"] or args.multiclock, reset, args.part_timeout,
                              unmatch, args.open, no_pins, unmatch_pins, booth_lines,
                              args.sweep))
    print("LEC gate prep: " + ", ".join(f"{k}={v}" for k, v in rep.items())
          + f", unmatched_names={len(nomatch)}")
    if args.emit_only:
        return 0
    t0 = time.time()
    log = out / "eqy.log"
    timed_out = False
    with open(log, "w") as f:
        # the image links bin/eqy to yosys/bin/eqy, and eqy finds its plugins
        # relative to the path it was called by: call the real file (TODO W16,
        # iic-jku/IIC-OSIC-TOOLS#367)
        eqy_bin = os.path.realpath(shutil.which("eqy") or "eqy")
        p = subprocess.Popen([eqy_bin, "-f", str(eqy), "-d", str(out / "work"),
                              "-j", str(args.jobs)],
                             stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            rc = p.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_session(p.pid)
            rc = p.wait()
    dt = time.time() - t0
    text = log.read_text()
    work = out / "work"
    parts = tally(work)
    # every macro instance must reach the comparison, as everted ports;
    # a run killed before matching has no matched.ids and is a TIMEOUT
    ids = work / "matched.ids"
    lost = [i for i in rep_bbinsts if f" {i}." not in ids.read_text()] if ids.exists() else []
    if lost:
        print(f"LEC: macro pins never compared: {lost[:4]} ({len(lost)} instances)")
    verdict = judge(rc, text, parts, lost, timed_out, args.open)
    gone = sorted(set(args.open) - set(parts))
    if gone:  # renamed by a new netlist, or proven: the list is stale
        print(f"LEC: declared open but no such partition: {' '.join(gone)}")
    failed = [n for n, s in parts.items() if s == "FAIL"]
    unfinished = [n for n, s in parts.items() if s not in ("PASS", "FAIL")]
    proved = sum(s == "PASS" for s in parts.values())
    print(f"LEC {verdict} {cfg['top']} rc={rc} partitions={proved}/{len(parts)} proved "
          f"failed={len(failed)} unfinished={len(unfinished)}"
          + (f" (declared open: {len(args.open)})" if args.open else "") + f" {dt:.0f}s  ({log})")
    for tag, names in (("failed", failed), ("unfinished", unfinished)):
        for n in names[:8]:
            print(f"  {tag}: {n} ({parts[n] or 'no result'})")
        if len(names) > 8:
            print(f"  ... {len(names) - 8} more {tag}")
    if verdict == "ERROR":
        for line in text.splitlines():
            if re.search(r"(ERROR|failed|not equivalent|could not)", line, re.I):
                print("  " + line.strip())
    (out / "verdict.json").write_text(json.dumps({
        "top": cfg["top"], "verdict": verdict,
        "netlist": rel(nl), "netlist_sha256": sha256(nl), "config": rel(args.config),
        "partitions": len(parts), "proved": proved, "failed": failed, "unfinished": unfinished,
        "declared_open": args.open, "gold_booth": booth_rows, "sweep": args.sweep,
        "mutate": args.mutate, "mutate_pair": args.mutate_pair, "paired": len(pairs),
        "timed_out": timed_out, "seconds": round(dt),
        "lec_sha256": sha256(__file__), "image": os.environ.get("IIC_OSIC_TOOLS_VERSION", ""),
        "argv": sys.argv[1:],
    }, indent=1) + "\n")
    if args.expect_fail:
        # a mutant must fail on a counterexample; a timeout or an error proves
        # nothing about the check's teeth
        good = verdict == "FAIL"
        print("LEC expect-fail: " + ("OK, not proven" if good else
                                     "WRONG, it proved" if verdict == "PASS" else
                                     f"INCONCLUSIVE, {verdict}"))
        return 0 if good else 1
    return VERDICT_RC[verdict]


# ---------------------------------------------------------------- selftest

def selftest():
    lib_txt = r"""
library (t) {
 cell (BUFX1) { pin (A) { direction : input; } pin (Y) { direction : output; function : "A"; } }
 cell (NAND2X1) { pin (A) { direction : input; } pin (B) { direction : input; }
   pin (Y) { direction : output; function : "!(A * B)"; } }
 cell (DFFX1) { ff (IQ,IQN) { clocked_on : "CK"; next_state : "D"; }
   pin (CK) { direction : input; } pin (D) { direction : input; }
   pin (Q) { direction : output; function : "IQ"; } }
 cell (CGX1) { clock_gating_integrated_cell : "latch_posedge";
   pin (CK) { direction : input; clock_gate_clock_pin : true; }
   pin (E) { direction : input; clock_gate_enable_pin : true; }
   pin (ECK) { direction : output; clock_gate_out_pin : true; state_function : "CK * QE"; } }
 cell (MYSTERY) { pin (A) { direction : input; } pin (Y) { direction : output; } }
 cell (FILLER1) { }
 cell (ANTENNA2) { pin (A) { direction : input; } }
 cell (INVX1) { pin (A) { direction : input; } pin (Y) { direction : output; function : "!A"; } }
 cell (DFFRX1) { ff (IQ,IQN) { clocked_on : "CK"; next_state : "D"; clear : "!RB"; }
   pin (CK) { direction : input; } pin (D) { direction : input; } pin (RB) { direction : input; }
   pin (Q) { direction : output; function : "IQ"; } }
}
"""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.lib"
        p.write_text(lib_txt)
        lib = parse_liberty(p)
    assert flop_pins(lib["DFFX1"]) == ("CK", "D", "Q")
    assert icg_pins(lib["CGX1"]) == ("CK", "E", None, "ECK")
    assert is_buffer(lib["BUFX1"]) and not has_function(lib["MYSTERY"])
    nl = """module t (clk, en, a, q0, q1);
 input clk; input en; input a; output q0; output q1;
 wire g; wire gb;
 CGX1 icg (.CK(clk), .E(en), .ECK(g));
 BUFX1 cb (.A(g), .Y(gb));
 DFFX1 f0 (.CK(gb), .D(a), .Q(q0));
 DFFX1 f1 (.CK(g), .D(q0), .Q(q1));
 BUFX1 clkload0 (.A(g), .Y(dangle));
 DFFX1 f2 (.CK(clk), .D(q1), .Q(n2));
 NAND2X1 u0 (.A(n2), .B(a), .Y(n3));
 FILLER1 fill_1 ();
 ANTENNA2 ant_0 (.A(g));
endmodule
"""
    out, rep = rewrite(nl, lib, set())
    assert rep["icg"] == 1 and rep["gated_flops"] == 2 and rep["physical"] == 2, rep
    assert rep["clkload"] == 1 and "clkload0" not in out
    assert "CGX1" not in out and "FILLER1" not in out
    assert "assign lec_d_0 = en ?" in out and out.count(".CK(clk)") == 3, out
    try:
        rewrite(nl.replace("BUFX1 cb", "MYSTERY cb"), lib, set())
        raise AssertionError("unmodelled cell not caught")
    except SystemExit as e:
        assert "MYSTERY" in str(e)
    rewrite(nl.replace("NAND2X1 u0", "MYSTERY u0"), lib, {"MYSTERY"})  # declared: ok
    # a reset-to-1 register on a gated clock: stored inverted AND held by the
    # unwrapped ICG's mux, which reads the old Q net and must still find it
    inv = """module t2 (clk, rst_n, en, a, q);
 input clk; input rst_n; input en; input a; output q;
 wire g; wire _1_; wire _2_; wire cfg;
 CGX1 icg (.CK(clk), .E(en), .ECK(g));
 INVX1 i0 (.A(a), .Y(_1_));
 DFFRX1 f0 (.CK(g), .D(_1_), .RB(rst_n), .Q(_2_));
 INVX1 i1 (.A(_2_), .Y(cfg));
 BUFX1 o (.A(cfg), .Y(q));
endmodule
"""
    out, rep = rewrite(inv, lib, set())
    assert rep["gated_flops"] == 1 and rep["inverted_flops"] == 1, rep
    assert "assign lec_d_0 = en ? _1_ : _2_;" in out and "assign _2_ = ~lec_tq_0;" in out, out
    out, rep = rewrite(nl, lib, set(), mutate=0)
    assert "~lec_mut" in out and "mutated" in rep
    ring = nl.replace(" FILLER1 fill_1 ();",
                      " NAND2X1 r0 (.A(en), .B(\\ring[1] ), .Y(\\ring[0] ));\n"
                      " BUFX1 r1 (.A(\\ring[0] ), .Y(r1n));\n"
                      " NAND2X1 r2 (.A(r1n), .B(r1n), .Y(\\ring[1] ));")
    assert rewrite(ring, lib, set())[1]["loops"] == 1
    try:
        rewrite(ring.replace("\\ring[1] ", "_9_").replace("\\ring[0] ", "_8_")
                .replace("r1n", "_7_"), lib, set())
        raise AssertionError("unnamed loop not caught")
    except SystemExit as e:
        assert "loop" in str(e)
    with tempfile.TemporaryDirectory() as td:
        c = Path(td) / "flow" / "config.yaml"
        c.parent.mkdir()
        c.write_text("DESIGN_NAME: t\nVERILOG_FILES: ['dir::../rtl/t.sv']\n")
        cfg = read_config(c)
        assert cfg["files"] == [str((Path(td) / "rtl" / "t.sv").resolve())], cfg
        assert cfg["clock"] is None
        (Path(td) / "rtl").mkdir()
        (Path(td) / "rtl" / "t.sv").write_text("module t; endmodule\n")
        # the reset start goes into both sides, and never with clk2fflogic
        sim = "sim -clock clk_i -resetn rst_ni -rstlen 1 -n 1 -w"
        e = eqy_script(cfg, "x.lib", "g.v", {}, [], work=td, reset=("clk_i", "rst_ni"))
        assert e.count(sim) == 2, e
        assert sim not in eqy_script(cfg, "x.lib", "g.v", {}, [], work=td)
        assert sim not in eqy_script(cfg, "x.lib", "g.v", {}, [], work=td,
                                     multiclock=True, reset=("clk_i", "rst_ni"))
        assert "timeout" not in eqy_script(cfg, "x.lib", "g.v", {}, [], work=td)
        # the booth rewrite goes into gold right after its flatten, never into gate
        e = eqy_script(cfg, "x.lib", "g.v", {}, [], work=td, gold_booth=["booth"])
        gold, gate = e.split("[gold]\n")[1].split("[gate]\n")
        assert "flatten\nbooth\n" in gold and "booth" not in gate, e
        # the sweep goes first, plain PDR stays behind it, both skip an open one
        e = eqy_script(cfg, "x.lib", "g.v", {}, [], work=td, sweep=True, known_open=["t.x"])
        assert e.index("[strategy sweep]") < e.index("[strategy pdr]"), e
        assert "[strategy sweep]\nnoapply t.x\nuse sby\nengine abc scorr; pdr\n" in e, e
        assert "[strategy sweep]" not in eqy_script(cfg, "x.lib", "g.v", {}, [], work=td)
        assert "engine abc pdr\ntimeout 60\n" in eqy_script(cfg, "x.lib", "g.v", {}, [],
                                                             work=td, part_timeout=60)
    # verdicts off an EQY work dir: status files, not the log's wording
    with tempfile.TemporaryDirectory() as td:
        w = Path(td)
        (w / "partitions").mkdir()
        for n, s in (("t.a", "PASS"), ("t.b.0", "PASS"), ("t.c", None)):
            (w / "partitions" / f"{n}.il").write_text("")
            if s:
                (w / "strategies" / n / "pdr").mkdir(parents=True)
                (w / "strategies" / n / "pdr" / "status").write_text(s + "\n")
        parts = tally(w)
        assert parts == {"t.a": "PASS", "t.b.0": "PASS", "t.c": None}, parts
        done = "Successfully proved designs equivalent"
        assert judge(2, "", parts) == "TIMEOUT"
        assert judge(2, "", parts, timed_out=True) == "TIMEOUT"
        assert judge(0, done, {**parts, "t.c": "PASS"}) == "PASS"
        assert judge(1, done, {**parts, "t.c": "PASS"}) == "ERROR"  # EQY itself failed
        assert judge(0, done, {**parts, "t.c": "PASS"}, lost=["u_m"]) == "ERROR"
        assert judge(2, "", {**parts, "t.c": "UNKNOWN"}) == "TIMEOUT"
        assert judge(2, "", {**parts, "t.c": "FAIL"}, timed_out=True) == "FAIL"
        assert judge(2, "", {**parts, "t.c": "ERROR"}) == "ERROR"
        assert judge(1, "", {}) == "ERROR" and judge(1, "", {}, timed_out=True) == "TIMEOUT"
        # declared open: OPEN only if every unfinished one is declared
        assert judge(2, "", parts, known_open=["t.c"]) == "OPEN"
        assert judge(2, "", {**parts, "t.a": None}, known_open=["t.c"]) == "TIMEOUT"
        assert judge(2, "", {**parts, "t.a": "FAIL"}, known_open=["t.c"]) == "FAIL"
        (w / "strategies" / "t.c" / "open").mkdir(parents=True)
        (w / "strategies" / "t.c" / "open" / "status").write_text("UNKNOWN\n")
        assert tally(w)["t.c"] == "UNKNOWN", tally(w)
    # pairing: a latch and its stored complement share a trace hash
    with tempfile.TemporaryDirectory() as td:
        a, m = Path(td) / "t.aag", Path(td) / "t.map"
        a.write_text("aag 4 1 2 3 1\n2\n4 5\n6 4 1\n4\n6\n8\n8 4 2\n")
        m.write_text("input 0 0 i\noutput 0 0 a\noutput 1 0 b\noutput 2 0 c\n")
        st = stimulus(["i"], 64, 8, 1)
        tr = aig_traces(a, m, st, 64, 8)
        assert tr["a"][0] == tr["b"][0] and tr["a"][1] != tr["b"][1], tr
        assert tr["a"][2] == 7 * 64 and tr["c"][0] != tr["a"][0], tr
    s1 = stimulus([f"x[{k}]" for k in range(8)] + ["r"], 64, 16, 1, reset="r")
    assert s1 == stimulus([f"x[{k}]" for k in range(8)] + ["r"], 64, 16, 1, reset="r")
    assert s1["r"][0] == 0 and s1["r"][1] == (1 << 64) - 1
    ff = {"cell": "DFFRX1", "clear": True, "preset": False}
    stamps = {"s0": {**ff, "inst": "f0", "q": "_5_"}, "s1": {**ff, "inst": "f1", "q": "_6_"},
              "s2": {**ff, "inst": "f2", "q": "_7_"}, "s3": {**ff, "inst": "f3", "q": "\\x_q[2] "},
              "s4": {**ff, "inst": "f4", "q": "y_q"},
              "s5": {**ff, "inst": "f5", "q": "_8_", "preset": True}}
    gold_t = {"c": ("h1", 0, 9), "k": ("h0", 0, 0), "q": ("h2", 0, 2), "a": ("h3", 0, 9),
              "n": ("h4", 1, 9), "t": ("h5", 0, 9), "p": ("h6", 0, 9)}
    gate_t = {"s0": ("h1", 1, 9), "s1": ("h3", 0, 9), "s2": ("h3", 0, 9), "s3": ("h4", 1, 9),
              "s4": ("h5", 1, 9), "s5": ("h6", 1, 9)}
    pairs, rows = classify(gold_t, gate_t, {g: g for g in gold_t}, stamps, {"y_q"}, {})
    assert pairs == [("c", "s0", "complement"), ("n", "s3", "name")], pairs
    assert {r[1]: r[0] for r in rows} == {"c": "complement", "k": "constant", "q": "quiet",
                                          "a": "ambiguous", "n": "name", "t": "conflict",
                                          "p": "conflict"}, rows
    # a merge: the one candidate is another gold register's own flop
    pairs, _ = classify({"m": ("h7", 0, 9), "w": ("h7", 0, 9)}, {"s4": ("h7", 0, 9)},
                        {"m": "m"}, stamps, {"y_q", "w"}, {"y_q": "h7"})
    assert pairs == [("m", "s4", "name")], pairs
    # merged duplicates: two gold registers on one gate flop, one twin
    pairs, rows = classify({"c1": ("h1", 0, 9), "c2": ("h1", 0, 9)}, {"s0": ("h1", 1, 9)},
                           {"c1": "c1", "c2": "c2"}, stamps, set(), {})
    assert pairs == [("c1", "s0", "complement"), ("c2", "s0", "complement")], pairs
    # pad models: ports and directions, ANSI or not; supplies dropped
    with tempfile.TemporaryDirectory() as td:
        pm = Path(td) / "pads.v"
        pm.write_text("module P1 (iovdd, vss, pad, p2c);\n inout iovdd;\n inout vss;\n"
                      " inout pad;\n output p2c;\nendmodule\nmodule P2 (inout vdd, inout vss);\n"
                      "endmodule\n(* blackbox *)\nmodule P3 (\n inout vss, inout pad, inout bare\n);\n"
                      "endmodule\n")
        assert port_dirs(pm)["P3"] == [("vss", "inout"), ("pad", "inout"), ("bare", "inout")]
        stub, signal, no_pins = pad_stubs([pm], td)
        assert signal == {"P1", "P3"} and no_pins == {"P2"}, (signal, no_pins)
        s = stub.read_text()
        assert "module P1 (pad, p2c);\n    input pad;\n    output p2c;" in s and "vdd" not in s, s
    # a reset-to-1 register folded: INV into D and into the reader, hidden Q
    fold = """module t3 (clk, rst_n, en, a, b, y);
 input clk; input rst_n; input en; input a; input b; output y;
 wire g; wire _1_; wire _2_;
 CGX1 icg (.CK(clk), .E(en), .ECK(g));
 INVX1 i0 (.A(a), .Y(_1_));
 DFFRX1 f0 (.CK(g), .D(_1_), .RB(rst_n), .Q(_2_));
 NAND2X1 u0 (.A(_2_), .B(b), .Y(y));
endmodule
"""
    out, rep = rewrite(fold, lib, set(), stamp=True)
    assert rep["inverted_flops"] == 0 and "assign lec_pq_0 = _2_;" in out, out
    assert rep["stamps"]["lec_pq_0"]["inst"] == "f0" and rep["matchbits"] == []
    out, rep = rewrite(fold, lib, set(), pairs=[("cfg_q", "f0", "complement")])
    for line in ("LEC_SET_DFFRX1 f0", "assign lec_td_0 = ~lec_d_0;", "assign _2_ = ~lec_tq_0;",
                 "assign lecp_0 = lec_tq_0;", "assign lec_d_0 = en ? _1_ : _2_;"):
        assert line in out, (line, out)
    assert rep["pair_maps"] == [("cfg_q", "lecp_0")] and "lec_pq" not in out
    out, rep = rewrite(fold, lib, set(), pairs=[("cfg_q", "f0", "alias")])
    assert "assign lecp_0 = _2_;" in out and "LEC_SET_" not in out, out
    out, rep = rewrite(fold, lib, set(), pairs=[("a_q", "f0", "complement"),
                                                ("b_q", "f0", "complement")])
    assert out.count("LEC_SET_DFFRX1 f0") == 1 and "lecp_1" not in out, out
    assert rep["pair_maps"] == [("a_q", "lecp_0"), ("b_q", "lecp_0")], rep["pair_maps"]
    out, rep = rewrite(fold, lib, set(), pairs=[("cfg_q", "f0", "complement")], mutate_pair=0)
    assert "assign lec_mutp = ~lec_td_0;" in out and ".D(lec_mutp)" in out, out
    # a flop-driven output is a register, not bound; a gate-driven one is
    comb = """module t4 (clk, a, q, y);
 input clk;
 input a;
 output q;
 output y;
 wire n;
 DFFX1 f0 (.CK(clk), .D(a), .Q(n));
 BUFX1 b0 (.A(n), .Y(q));
 NAND2X1 u0 (.A(n), .B(a), .Y(y));
endmodule
"""
    assert rewrite(comb, lib, set())[1]["binds"] == ["y"], rewrite(comb, lib, set())[1]["binds"]
    with tempfile.TemporaryDirectory() as td:
        c = Path(td) / "config.yaml"
        c.write_text("DESIGN_NAME: t\nVERILOG_FILES: []\n")
        e = eqy_script(read_config(c), "x.lib", "g.v", {}, [], work=td,
                       maps=[("cfg_q[0]", "lecp_0"), ("cfg_q[1]", "lecp_1")],
                       gold_nomatch=["pe_mod[3]"])
        assert "gold-match /^cfg_q\\[0\\]$/ /^lecp_0$/" in e and e.count(" w:cfg_q") == 1, e
        assert "gold-nomatch /^pe_mod\\[3\\]$/" in e, e
        e = eqy_script(read_config(c), "x.lib", "g.v", {}, [], work=td, known_open=["t.m.0"])
        assert "[strategy open]\nuse dummy\napply t.m.0\n" in e, e
        assert "[strategy pdr]\nnoapply t.m.0\nuse sby" in e, e
        assert "strategy open" not in eqy_script(read_config(c), "x.lib", "g.v", {}, [], work=td)
    # the timeout kill reaches a child in its own process group, as SBY's are
    if Path("/proc").is_dir():
        p = subprocess.Popen([sys.executable, "-c",
                              "import os, subprocess, time; subprocess.Popen([%r, '-c', "
                              "'import os, time; os.setpgrp(); time.sleep(60)']); "
                              "time.sleep(60)" % sys.executable], start_new_session=True)
        t = time.time()
        while len(session_pids(p.pid)) < 2 and time.time() - t < 10:
            time.sleep(0.1)
        assert len(session_pids(p.pid)) == 2, session_pids(p.pid)
        kill_session(p.pid, grace=2)
        p.wait()
        assert not session_pids(p.pid), session_pids(p.pid)
    # EQY ends a /pattern/ at any slash, and yosys leaves source paths in net names
    n = "_553_$func$/x/y.v:15$1.$result"
    assert "/" not in rx(n) and re.fullmatch(rx(n), n), rx(n)
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "t.v").write_text("module t; endmodule\n")
        (Path(td) / "c.yaml").write_text("DESIGN_NAME: t\nVERILOG_FILES: ['dir::t.v']\n")
        e = eqy_script(read_config(Path(td) / "c.yaml"), "x.lib", "g.v", {}, [], nomatch=[n], work=td)
    assert "gate-nomatch /^" + rx(n) in e and "--no-implicit-memories" in e, e
    # every multi-bit flop split to single bits, so a flop cell whose dead bits
    # synthesis dropped does not merge every reader of its live bits
    assert "dffunmap\nsimplemap t:$dff t:$ff\n" in e, e
    # a gate flop named after a gold decode wire is no match point, a gold register is
    keep = ["u.state_is_1", "u.cnt", "u.n515", "q", "u.pair_t", "u.arr[0]"]  # u.arr[0]: gold lacks it
    gold_ffs = [["u.cnt[0]"], ["u.cnt[1]"], ["u.state[0]"]]
    gold_names = {"u.cnt[0]", "u.cnt[1]", "u.state[0]", "u.state[1]", "u.state_is_1", "u.n515", "q"}
    assert not_gold_regs(keep, gold_ffs, gold_names, {"u.pair_t"}, {"q"}) == ["u.n515", "u.state_is_1"]
    # unpacked arrays: gate a[i][j] from read_verilog, gold one register a from
    # slang, element 0 of [0:N-1] in the top bits
    gold_ffs = [[f"u.a[{k}]"] for k in range(12)] + [["u.b[0]"]]
    got = dict(array_maps(["u.a[0][0]", "u.a[0][3]", "u.a[2][1]", "u.c[0][0]"], gold_ffs))
    assert got == {"u.a[8]": "u.a[0][0]", "u.a[11]": "u.a[0][3]", "u.a[1]": "u.a[2][1]"}, got
    assert array_maps(["u.a[0][0]", "u.a[4][0]"], gold_ffs) == []  # 12 bits do not split in 5
    # an element's top bit that synthesis merged into the bit below it (both the sign) maps onto that flop
    got = dict(array_maps([f"u.a[{i}][{j}]" for i in range(3) for j in range(4) if (i, j) != (1, 3)], gold_ffs))
    assert got["u.a[7]"] == "u.a[1][2]" and got["u.a[6]"] == "u.a[1][2]", got
    print("lec.py selftest: OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", help="the macro's LibreLane config")
    ap.add_argument("--netlist", help="flow/final*/nl/<top>.nl.v")
    ap.add_argument("--liberty", help="cell functions (default: EZ130 tt)")
    ap.add_argument("--blackbox",
                    help="comma list of hard macros: name (MACROS.<name>.vh) or name=stub.v")
    ap.add_argument("--model", action="append", default=[],
                    help="functional Verilog read on both sides (repeatable)")
    ap.add_argument("--map", action="append", default=[], metavar="GOLD=GATE",
                    help="gold register bit proved against a merged gate one (repeatable)")
    ap.add_argument("--gold", action="append", default=[], metavar="FILE",
                    help="gold RTL instead of the config's VERILOG_FILES (repeatable)")
    ap.add_argument("--array-maps", action="store_true",
                    help="map ascending unpacked arrays, gate a[i][j] to gold a[k], see array_maps()")
    ap.add_argument("--multiclock", action="store_true",
                    help="exact clk2fflogic model even with one clock root")
    ap.add_argument("--mutate", type=int, help="invert the Nth gate output: must fail")
    ap.add_argument("--mutate-pair", type=int, metavar="K",
                    help="invert D of the Kth simulation-paired flop: must fail")
    ap.add_argument("--no-pair", action="store_true",
                    help="match by name only, no simulation pairing")
    ap.add_argument("--pair-lanes", type=int, default=1024)
    ap.add_argument("--pair-cycles", type=int, default=512)
    ap.add_argument("--pair-seed", type=int, default=1)
    ap.add_argument("--expect-fail", action="store_true", help="exit 0 only if not proven")
    ap.add_argument("--emit-only", action="store_true", help="write the EQY files, do not run")
    ap.add_argument("--timeout", type=int, metavar="SEC",
                    help="wall clock for EQY; on expiry the run is killed and reads TIMEOUT")
    ap.add_argument("--part-timeout", type=int, metavar="SEC",
                    help="SBY timeout per partition (EQY reports it TIMEOUT)")
    ap.add_argument("--clock", help="clock of the reset start, if not CLOCK_PORT (a pad's <inst>.p2c)")
    ap.add_argument("--reset", help="active-low reset, if not an rst_n(i) input (a pad's <inst>.p2c)")
    ap.add_argument("--rstlen", type=int, default=1, help="reset cycles of the reset start")
    ap.add_argument("--open", action="append", default=[], metavar="PARTITION",
                    help="a partition known not to finish: not attempted; the verdict is "
                         "OPEN (exit 0) if every other one proves (repeatable)")
    ap.add_argument("--gold-booth", action="store_true",
                    help="Booth-encode gold's multipliers as synthesis did, each rewrite "
                         "proven exhaustively first (booth_check.py)")
    ap.add_argument("--sweep", action="store_true",
                    help="ABC scorr (SAT sweeping) before PDR, plain PDR after an unsettled "
                         "partition; what makes --gold-booth pay off")
    ap.add_argument("--out", help="work directory (default <macro>/build/lec/<top>)")
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    if not (a.config and a.netlist):
        ap.error("--config and --netlist are required")
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
