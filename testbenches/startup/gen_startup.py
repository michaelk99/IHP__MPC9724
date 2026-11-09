#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Netlists of the supply start-up bench, from the chip's and the macro's powered netlists.

    python3 testbenches/startup/gen_startup.py [--out testbenches/startup/build] [--tree <repo or worktree>] [--orders a,b]
    python3 testbenches/startup/gen_startup.py --self-test

core.spice   every functional standard cell of the chip, the macro's flattened in, as one
             subcircuit whose ports are the nets to the IO cells. spi2xspice.py turns them into
             XSPICE. Fill, decap, tap and antenna cells carry no logic and stay out, and so does
             the adc_conv gate, whose pad the bench drives.
chip.spice   the IO cells and the clamp and cut cells as transistors from the PDK, around that core,
             and dsm2 as transistors (--dsm2 sch, the default, or pex). Bondpads, IO fillers and
             corners carry no device on these nets and stay out. XSPICE drives a fixed 1.2 V, so
             every core output into a pad or into dsm2 goes through a source scaled by V(VDD_s),
             the core supply at its regulator, and 1 kOhm: with the core supply down the pads and
             dsm2 see the core's outputs down too. dsm2's do_q_dec goes into the core's A-to-D
             bridge. A pad input that no cell drives (the adc_conv gate) gets a source of the same
             kind from a 0/1 level c_<net>, scaled by the regulator of the pad's own rail.
chip_box.spice the same with dsm2 a box: its do_q pads get bench sources like the adc_conv gate.
             The power orders always take it, they have no frames to start dsm2.
dsm2.spice   dsm2's netlist from ip/dsm2_core/spice inside a wrapper subcircuit, so its 5-pin
             sg13cmos5l_SecondaryProtection stays apart from the IO cells' 4-pin one.
stim_*.spice the bench: supplies ramping in either order, the host on the IOVDD rail holding
             rst_n low through the ramp, then three SPI reads (FRAMES). The order bounce has the
             package from packaging/result.md, dsm_clk and dsm2's outputs running, and BOUNCE_FRAMES,
             which toggle miso. The power orders have no frames, only clk and data_in toggling.
tb_*.in      startup_tb.spice with the order and its probes filled in, the solver recipe left to
             run_startup.sh.
cells.lib    the EZ130 typical liberty cut to the cells the core uses. spi2xspice.py cannot
             parse the flop banks' bundles, which the core does not use, and it substitutes pin
             names as text, so B corrupts AB. Every signal pin is renamed P0Q, P1Q, ... here and
             in the core's pin-order stubs alike.

--patch-xspice adds what spi2xspice.py cannot model: the CGX3 clock gates, whose liberty is a
statetable. Each becomes a latch open while CK is low and an AND of CK with it, latch_posedge.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "../.."))
CLAMP = "sg13cmos5l_ip__clamp_vddvss"
CUT = "sg13cmos5l_ip__cut_vdd"
DSM = "dsm2_core"
# dsm2's ngspice views, file and subckt, and their port order
DSM2_DIR = "ip/dsm2_core/spice"
DSM2_VIEWS = {"sch": ("dsm2_core_sch.spice", "dsm2_core"), "pex": ("dsm2_core_pex3.spice", "dsm2_core_pex")}
DSM2_PORTS = ("vi vcm di_clk di_ena di_rst_b di_trim[3] di_trim[2] di_trim[1] di_trim[0] di_dith_en di_dith_amp[1] "
              "di_dith_amp[0] di_vcm_ext di_btest_en di_qout_en do_q do_q_b do_q_dec ibias_test vdd vss").split()
# the oscillator variant (2026-11-02) appends these, its pads' c2p and c2p_en
DSM2_OSC = ["di_osc_en", "di_clk_sel", "do_clk_osc", "do_osc_oe"]
C_DEC_IN = 15e-15                   # the DEC_SRC gate on do_q_dec, dsm2's bench load
# the files of one tree, this one or a worktree of an older tag (--tree)
TREE_FILES = {"chip_pnl": "netlist/pnl/sg13cmos5l_dsa1_dig_top.pnl.v", "bond_report": "packaging/result.md",
              "macro_pnl": "macros/dsa1_dig/final/pnl/dsa1_dig_top.pnl.v",
              "clamp_cdl": f"ip/{CLAMP}/cdl/{CLAMP}.cdl", "cut_cdl": f"ip/{CUT}/cdl/{CUT}.cdl"}
BOND_REPORT = os.path.join(ROOT, TREE_FILES["bond_report"])
MACRO = "dsa1_dig_top"
IO_CELL = re.compile(r"^sg13cmos5l_(IOPad|Filler|Corner|ip__)")
NO_LOGIC = re.compile(r"^(FILLER\d+|DECAPHV\d+|WELLTAP|ANTENNA\d*|decap_vdda)$")             # decap_vdda holds only DECAPHV
SUPPLIES = {"VDD", "VDDA", "VSS", "IOVDD", "IOVSS"}
# The adc_conv gate is left out of the core and its pad is bench driven, the real pulse comes once per 1.95 ms output sample, too rarely for the bounce case
BENCH_DRIVEN = re.compile(r"(^|\.)u_adc_conv_gate$")
WELLS = {"VNW": "VDD", "VPW": "VSS"}     # implicit in the netlist, the CDL lists them
OUTPUTS = {"Y", "Q", "QN", "CO", "S"}     # may stay open, a clock-tree load inverter does


# ---- a structural Verilog reader, enough for LibreLane's netlists ----------------------

TOKEN = re.compile(r"\\\S+\s|[A-Za-z_][A-Za-z0-9_$]*(?:\[\d+\])?|\d+'[bhd][0-9a-fA-F_xz]+|\[\d+:\d+\]|[(){},.;:]")


def tokens(text):
    text = re.sub(r"//.*", "", re.sub(r"/\*.*?\*/", "", text, flags=re.S))
    for t in TOKEN.findall(text):
        yield t.strip() if t.startswith("\\") else t


def net_name(t):
    """An escaped identifier keeps its text, a bit select stays name[i]."""
    return t[1:] if t.startswith("\\") else t


def parse(path):
    """{module: {"ports": [(name, width or None)], "insts": [(cell, inst, {pin: [nets msb first]})]}}"""
    toks = list(tokens(open(path).read()))
    mods, i = {}, 0
    while i < len(toks):
        if toks[i] != "module":
            i += 1
            continue
        name = net_name(toks[i + 1])
        mod = mods[name] = {"ports": [], "insts": []}
        width = {}
        i += 2
        while toks[i] != ";":
            i += 1
        i += 1
        while toks[i] != "endmodule":
            t = toks[i]
            if t in ("input", "output", "inout", "wire"):
                j, w = i + 1, None
                if toks[j].startswith("["):
                    msb, lsb = map(int, toks[j][1:-1].split(":"))
                    w, j = (msb, lsb), j + 1
                while toks[j] != ";":
                    if toks[j] != ",":
                        nm = net_name(toks[j])
                        width[nm] = w
                        if t != "wire":
                            mod["ports"].append((nm, w))
                    j += 1
                i = j + 1
            elif t == "assign":
                raise SystemExit(f"{path}: assign statements are not handled")
            else:
                cell, inst = net_name(t), net_name(toks[i + 1])
                j, pins = i + 3, {}
                while toks[j] != ")" or toks[j + 1] != ";":
                    if toks[j] == ".":
                        pin = toks[j + 1]
                        j += 3
                        nets = []
                        depth = 0
                        while not (toks[j] == ")" and depth == 0):
                            if toks[j] == "{":
                                depth += 1
                            elif toks[j] == "}":
                                depth -= 1
                            elif toks[j] != ",":
                                nets.append(net_name(toks[j]))
                            j += 1
                        pins[pin] = nets
                    j += 1
                mod["insts"].append((cell, inst, pins))
                i = j + 2
        mod["width"] = width
        i += 1
    return mods


def bits(name, w):
    """A port or wire as its bits, msb first."""
    if w is None:
        return [name]
    msb, lsb = w
    step = -1 if msb >= lsb else 1
    return [f"{name}[{b}]" for b in range(msb, lsb + step, step)]


def expand(nets, width):
    """A connection list with whole buses expanded into their bits."""
    out = []
    for n in nets:
        out += bits(n, width.get(n)) if "[" not in n and width.get(n) else [n]
    return out


def spice_pins(path):
    """{cell: [pins in order]} from the .subckt lines of a SPICE or CDL file."""
    pins = {}
    for line in open(path):
        m = re.match(r"\s*\.subckt\s+(\S+)\s+(.*)", line, re.I)
        if m:
            pins[m.group(1)] = m.group(2).split()
    return pins


def pin_map(pins):
    """CDL signal pins to names no other one contains."""
    sig = [p for p in pins if p.upper() not in SUPPLIES and p not in WELLS]
    return {p: f"P{k}Q" for k, p in enumerate(sig)}


PIN_LINE = re.compile(r"\b(pin|function|related_pin|next_state|clocked_on|clear|preset|data_in|enable)\b")


def rename_pins(block, mapping):
    """mapping applied to whole words on the lines that name pins."""
    word = re.compile(r"\b(" + "|".join(map(re.escape, sorted(mapping, key=len, reverse=True))) + r")\b")
    return "\n".join(word.sub(lambda m: mapping[m.group(1)], ln) if PIN_LINE.search(ln) else ln
                     for ln in block.split("\n"))


def liberty_subset(path, keep, maps=None):
    """The liberty's header and the cell groups named in keep, by brace matching, with
    each cell's pins renamed through maps[cell] when given."""
    text = open(path).read()
    out, i = [], 0
    for m in re.finditer(r"\bcell\s*\(\s*\"?([A-Za-z0-9_]+)\"?\s*\)\s*\{", text):
        if m.start() < i:
            continue
        depth, j = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        if not out:
            out.append(text[:m.start()])
        if m.group(1) in keep:
            block = text[m.start():j]
            out.append((rename_pins(block, maps[m.group(1)]) if maps else block) + "\n")
        i = j
    return "".join(out) + "}\n"


def safe(n):
    return re.sub(r"[^A-Za-z0-9_]", "_", n)


# ---- the two netlists ---------------------------------------------------------------------

def io_spice():
    """The IO cells' SPICE of the pinned image's PDK, whose GDS the layout's IO cells come from. Every tree is simulated with it."""
    return os.path.join(os.environ["PDK_ROOT"], os.environ["PDK"], "libs.ref/sg13cmos5l_io/spice/sg13cmos5l_io.spice")


def dsm2_pins(conn):
    """{dsm2 port: net} of the instance, buses msb first as DSM2_PORTS has them."""
    out = {}
    for p, ns in conn.items():
        out.update({p: ns[0]} if len(ns) == 1 else {f"{p}[{len(ns) - 1 - k}]": n for k, n in enumerate(ns)})
    return out


def build(chip_pnl, macro_pnl, cdl, io_spi, clamp_cdl=None, cut_cdl=None, dsm2="box"):
    """The core and the chip around it, dsm2 a box or as transistors ("sch" or "pex").
    The core is the same either way, its ports include dsm2's controls and do_q_dec."""
    chip = parse(chip_pnl)["sg13cmos5l_dsa1_dig_top"]
    macro = parse(macro_pnl)[MACRO]
    cell_pins = spice_pins(cdl)
    io_pins = spice_pins(io_spi)
    for extra in (clamp_cdl, cut_cdl):
        if extra and os.path.exists(extra):
            io_pins.update(spice_pins(extra))

    core, io, dsm = [], [], {}
    for cell, inst, pins in chip["insts"]:
        conn = {p: expand(n, chip["width"]) for p, n in pins.items()}
        if cell == MACRO:
            port_map = {}
            for p, w in macro["ports"]:
                if p in conn:
                    port_map.update(zip(bits(p, w), conn[p]))
            for mcell, minst, mpins in macro["insts"]:
                if NO_LOGIC.match(mcell):
                    continue
                mconn = {p: [port_map.get(b, f"{inst}/{b}") for b in expand(n, macro["width"])] for p, n in mpins.items()}
                core.append((mcell, f"{inst}/{minst}", mconn))
        elif cell == DSM:
            dsm = dsm2_pins(conn)
        elif IO_CELL.match(cell):
            if cell.startswith("sg13cmos5l_IOPad") or cell in (CLAMP, CUT):
                io.append((cell, inst, conn))
        elif BENCH_DRIVEN.search(inst):
            continue
        elif not NO_LOGIC.match(cell):
            core.append((cell, inst, conn))

    core_nets = {n for _, _, c in core for ns in c.values() for n in ns}
    io_nets = {n for _, _, c in io for ns in c.values() for n in ns}
    dports = DSM2_PORTS + (DSM2_OSC if "di_osc_en" in dsm else [])
    if dsm and sorted(dsm) != sorted(dports):
        raise SystemExit(f"dsm2_core pins {sorted(dsm)} are not {dports}")
    if dsm2 != "box" and not dsm:
        raise SystemExit(f"{chip_pnl} has no dsm2_core to simulate, use --dsm2 box")
    dsm_out = {dsm[p] for p in ("do_q", "do_q_b", "do_q_dec", "do_clk_osc") if p in dsm}
    ports = sorted((core_nets & (io_nets | set(dsm.values()))) - SUPPLIES)

    names = {}
    for n in core_nets | io_nets:
        s = safe(n)
        if names.setdefault(s, n) != n:
            raise SystemExit(f"net names {n} and {names[s]} both become {s}")

    def xline(cell, inst, conn, order):
        missing = [p for p in order if p not in conn and p.upper() not in SUPPLIES and p not in WELLS and p not in OUTPUTS]
        if missing:
            raise SystemExit(f"{inst} ({cell}) leaves {missing} unconnected")
        nets = [conn[p][0] if p in conn else f"{inst}/{p}" if p in OUTPUTS else WELLS.get(p, p.upper()) for p in order]
        return f"X{safe(inst)} {' '.join(safe(n) for n in nets)} {cell}"

    lines = [f".subckt core {' '.join(safe(p) for p in ports)}"]
    used = sorted({c for c, _, _ in core})
    for cell in used:
        if cell not in cell_pins:
            raise SystemExit(f"{cell} has no .subckt in {cdl}")
    lines += [xline(c, i, conn, cell_pins[c]) for c, i, conn in core]
    lines.append(".ends core")
    maps = {c: pin_map(cell_pins[c]) for c in used}
    stubs = [f".subckt {c} {' '.join(maps[c].get(p, p) for p in cell_pins[c])}\n.ends {c}" for c in used]

    driven = {n: conn["vdd"][0] for c, _, conn in io for pin, ns in conn.items() if pin == "c2p" for n in ns}
    # core outputs into a pad or a dsm2 control input
    outputs = (set(driven) | {n for p, n in dsm.items() if p.startswith("di_") and p != "di_clk"}) & set(ports)
    # a pad input that no core cell drives, the adc_conv gate, and dsm2's outputs with dsm2 a box. {net: rail of the pad}
    external = {n: r for n, r in driven.items() if n not in core_nets and (dsm2 == "box" or n not in dsm_out)}
    chip_ports = [safe(b) for p, w in chip["ports"] for b in bits(p, w)] + [f"c_{safe(n)}" for n in sorted(external)]
    chip_lines = [f".subckt chip {' '.join(chip_ports)}"]
    for cell, inst, conn in io:
        # the PDK's analog pad shorts padbare to pad inside and has no padbare pin
        chip_lines.append(xline(cell, inst, conn, io_pins[cell]))
    chip_lines.append(f"Xcore {' '.join(('u_' if p in outputs else '') + safe(p) for p in ports)} core")
    # 1 kOhm, a standard cell's output: an ideal source into an output pad's level shifter stalls the solver
    for n in sorted(outputs):
        chip_lines += [f"Ru_{safe(n)} u_{safe(n)} 0 1G", f"B{safe(n)} {safe(n)}_d 0 V=V(u_{safe(n)})*V(VDD_s)/1.2",
                       f"Rd_{safe(n)} {safe(n)}_d {safe(n)} 1k"]
    # a bench source for each of them: its 0/1 level c_<net> from stim_*.spice, scaled by its pad's rail
    for n, rail in sorted(external.items()):
        chip_lines += [f"Bx_{safe(n)} x_{safe(n)} 0 V=V(c_{safe(n)})*V({rail}_s)", f"Rx_{safe(n)} x_{safe(n)} {safe(n)} 1k"]
    if dsm and dsm2 == "box":
        chip_lines += [f"Rx_{safe(dsm[p])} {safe(dsm[p])} 0 1G" for p in ("do_q_dec", "do_osc_oe") if p in dsm]
    elif dsm:
        # a 0 V source in dsm2's supply measures its own current, the pin stays on the chip's net
        nets = [f"dsm2_{safe(dsm['vdd'])}" if p == "vdd" else safe(dsm[p]) for p in dports]
        chip_lines += [f"Vdsm2_vdd {safe(dsm['vdd'])} {nets[dports.index('vdd')]} 0", f"Xdsm2 {' '.join(nets)} dsm2_wrap",
                       f"Cdsm2_dec {safe(dsm['do_q_dec'])} 0 {C_DEC_IN:.3g}"]
    chip_lines.append(".ends chip")
    return {"core": "\n".join(stubs + lines) + "\n", "chip": "\n".join(chip_lines) + "\n",
            "ports": ports, "n_core": len(core), "n_io": len(io), "cells": used, "maps": maps, "outputs": sorted(outputs),
            "chip_ports": chip_ports, "external": {safe(n): r for n, r in sorted(external.items())},
            "dsm2": {p: safe(n) for p, n in dsm.items()} if dsm2 != "box" else {}}


def dsm2_wrapper(path, subckt, ports=DSM2_PORTS):
    """dsm2's netlist inside dsm2_wrap. Nested, its subcircuits are local, so its 5-pin
    sg13cmos5l_SecondaryProtection does not replace the IO cells' 4-pin one."""
    return "\n".join([f"* dsm2_core from {path}, written by gen_startup.py",
                      "* rshunt, 1 TOhm from every node to ground, is in dsm2's header: its operating point needs it.",
                      ".options rshunt=1e12",
                      f".subckt dsm2_wrap {' '.join(ports)}", f".include {path}",
                      f"X1 {' '.join(ports)} {subckt}", ".ends dsm2_wrap"]) + "\n"


# ---- the bench --------------------------------------------------------------------------

T_SCLK = 2.5e-6                     # 400 kHz, as the ESP32 host runs it
T_CLK = 1 / 65536
T_DSM = 1 / 1.024e6                 # dsm_clk
RAMP = 100e-6
T_FIRST, T_SECOND = 10e-6, 150e-6   # ramp starts of the supplies that come first and second
T_RST = 300e-6                      # the host releases rst_n
T_SCLK_ON = 280e-6                  # sclk and clk start with the host's firmware, after both ramps: a clk edge
                                    # into a pad on a rail of a few 10 mV stalls the solver for good
T_DSM_ON = 290e-6                   # dsm_clk and dsm2's outputs start, when the ramps are over
# (start, address, name, value read or None, value written or None)
FRAMES = [(320e-6, 15, "CHIP_ID", 0x0001, None), (385e-6, 9, "TEST_CTRL_0", 0x0500, None),
          (450e-6, 12, "AUX_CTRL_0", 0xFF00, None)]
T_END = 515e-6
# SPARE_14 is 16 free read-write bits. 0x5555 on miso toggles it at every sclk bit, 15 times per read.
SPARE_ADDR, MISO_PATTERN = 14, 0x5555
BOUNCE_FRAMES = [(320e-6, 15, "CHIP_ID", 0x0001, None), (385e-6, SPARE_ADDR, "SPARE_14", None, MISO_PATTERN),
                 (450e-6, SPARE_ADDR, "SPARE_14", MISO_PATTERN, None)]
T_END_BOUNCE = 520e-6
ADC_CONV_AT = 456e-6                # one adc_conv pulse, one clk cycle wide, inside the SPARE_14 read
# The settled currents are means over a whole number of data_in periods, 8 of them are also 125 dsm_clk periods
P_WINDOW = 8 * T_CLK
T_END_POWER = 520e-6
ORDERS = ("io_first", "core_first", "bounce", "power_dsa1", "power_dsm", "vdda_last")
POWER_ORDERS = ("power_dsa1", "power_dsm")
# The package in the order bounce. Bond wire 25 um gold, about 1 nH and 50 mOhm per mm, plus the QFN
# lead and its board pad. Each supply pin has 100 nF on the board, each output 10 pF of trace and receiver.
L_MM, R_MM = 1e-9, 0.05
L_LEAD, R_LEAD = 0.5e-9, 0.01
L_EP, R_EP = 0.1e-9, 0.002          # the exposed pad, soldered to the board ground
C_DEC, R_DEC = 100e-9, 0.01
C_PIN = 10e-12
R_SRC = 50                          # the host's pins, and the analog sources vi and vcm in the bounce case
V_VCM = 0.5                         # vi and vcm sit at this fraction of VDDA
# With dsm2 as transistors the host starts it as specified: DSM_EN, 130 us, then DSM_RST_B, here with DSM_QOUT_EN.
# BIAS_CFG_1 keeps ADC_CONV_EN at its reset 1. A write takes effect T_STORE after the frame starts, half an sclk period
# before the store bit's sampling edge, as the bench measured it (586.25 us for the frame at 530 us).
BIAS_CFG_1, DSM_ON, DSM_RUN = 3, 0x0041, 0x0063
T_DSM_WAIT = 130e-6
T_STORE = 22.5 * T_SCLK
DSM2_FRAMES = FRAMES + [(530e-6, BIAS_CFG_1, "BIAS_CFG_1", None, DSM_ON), (660e-6, BIAS_CFG_1, "BIAS_CFG_1", None, DSM_RUN)]
T_END_DSM2 = 760e-6
# the bounce: CHIP_ID, DSM_EN, SPARE_14 written in the wait, DSM_RST_B, then SPARE_14 read back with dsm2 running
BOUNCE_DSM2_FRAMES = [BOUNCE_FRAMES[0], (385e-6, BIAS_CFG_1, "BIAS_CFG_1", None, DSM_ON), (450e-6, *BOUNCE_FRAMES[1][1:]),
                      (515e-6, BIAS_CFG_1, "BIAS_CFG_1", None, DSM_RUN), (580e-6, *BOUNCE_FRAMES[2][1:])]
T_END_BOUNCE_DSM2 = 650e-6
ADC_CONV_AT_DSM2 = 586e-6
# dsm_clk starts this long before DSM_RST_B: dsm2's clocks cost minutes each, so the 130 us wait runs without them
T_DSM_LEAD = 2 * T_SCLK
# STARTUP_DEFON=1: the chip since v1.2.1, dsm2 on from reset with no SPI write. di_ena and di_qout_en follow VDD up,
# di_rst_b rises on the 10th rising clk edge after rst_n. Start-up orders only.
DEFON = os.environ.get("STARTUP_DEFON", "") == "1"
T_DEFON_RUN = T_SCLK_ON + (-(-(T_RST - T_SCLK_ON) // T_CLK) + 9) * T_CLK
# STARTUP_END_US ends a DEFON start-up run early, for the slow extracted view. Reads it cuts off are reported, not judged.
END_US = os.environ.get("STARTUP_END_US")
# STARTUP_CORNER=ss_m40: ss MOS, worst-case R and C, -40 C, with dsm2's cold tolerances. Default tt 27 C.
CORNER = os.environ.get("STARTUP_CORNER", "tt")
COLD = {"mos_tt": "mos_ss", "res_typ": "res_wcs", "cap_typ": "cap_wcs"}
# vdda_last: VDD first, IOVDD second as in core_first, VDDA once IOVDD is up, with dsm2 already enabled
T_VDDA_LAST = T_SECOND + RAMP
VI_PAD = "analog_PAD_0_"            # dsm2's vi, which a source at half of VDDA drives when dsm2 is in
VCM_PAD = "analog_PAD_1_"           # dsm2's vcm, 0.96 MOhm out of vcm_gen, so 1 MOhm would halve it
# Breakpoints every 0.25 ns from 1 to 6 ns after both dsm_clk edges, as dsm2's loop benches place them from 1 to 4 ns
# after di_clk, plus 2 ns for the dsm_clk pad. Without them dsm2 stalls about 16 clocks in at its vi ESD diode.
BRK = [1e-9 + k * 0.25e-9 for k in range(21)]


def ramp_starts(order):
    """{supply: start of its ramp}."""
    io, core = (T_FIRST, T_SECOND) if order == "io_first" else (T_SECOND, T_FIRST)
    return {"IOVDD": io, "VDD": core, "VDDA": T_VDDA_LAST if order == "vdda_last" else core}


def frames(order, dsm2=False):
    if order in POWER_ORDERS:
        return []
    if order == "bounce":
        assert not (dsm2 and DEFON), "STARTUP_DEFON has no bounce"
        return BOUNCE_DSM2_FRAMES if dsm2 else BOUNCE_FRAMES
    return DSM2_FRAMES if dsm2 and not DEFON else FRAMES


def dsm2_times(order):
    """(DSM_EN, DSM_RST_B) as they reach dsm2, the store edges of the two BIAS_CFG_1 writes.
    With DEFON VDD's ramp at half, then the 10th clk edge after rst_n."""
    if DEFON:
        return (T_SECOND if order == "io_first" else T_FIRST) + RAMP / 2, T_DEFON_RUN
    on, run = [t0 + T_STORE for t0, a, _, _, wd in frames(order, True) if a == BIAS_CFG_1 and wd is not None]
    return on, run


def dsm2_run_specified():
    return DSM2_FRAMES[-1][0] + T_STORE


def t_end(order, dsm2=False):
    if dsm2 and DEFON and order not in POWER_ORDERS:
        if END_US:
            assert float(END_US) * 1e-6 >= T_DEFON_RUN + 30e-6, "STARTUP_END_US leaves under 20 us of modulation to check"
            return float(END_US) * 1e-6
        return max(T_END, T_DEFON_RUN + T_END_DSM2 - dsm2_run_specified())
    if dsm2 and order not in POWER_ORDERS:
        return T_END_BOUNCE_DSM2 if order == "bounce" else T_END_DSM2
    return T_END_BOUNCE if order == "bounce" else T_END_POWER if order in POWER_ORDERS else T_END


def t_dsm_clk(order, dsm2=False):
    """When dsm_clk starts, None when it stays low."""
    if dsm2 and order not in POWER_ORDERS:
        return dsm2_times(order)[1] - T_DSM_LEAD
    return T_DSM_ON if order in ("bounce", "power_dsm") else None


def dsm_active(order):
    return order in ("bounce", "power_dsm")


def frame_bits(addr, wdata=None):
    """23 bits, mosi order: the read flag, 4 address bits, a load cycle, 16 data bits, a store cycle."""
    word = ((addr & 0xF) | (0x10 if wdata is None else 0)) << 18 | ((wdata or 0) & 0xFFFF) << 1
    return [(word >> k) & 1 for k in range(22, -1, -1)]


def bond_lengths(path=BOND_REPORT):
    """{net: um} of the pad-to-lead wires, ("EPAD", net): [um, ...] for the downbonds (a net may have
    several) and ("lead", pin): um for the lead-to-cavity bonds, from the bond table."""
    out, col = {}, None
    for line in open(path):
        f = [x.strip() for x in line.strip().strip("|").split("|")]
        if f[0] == "Pin":           # the header names the columns, the table gained a Signal column once
            col = {name: k for k, name in enumerate(f)}
            continue
        if col is None or len(f) != len(col) or not (f[0].isdigit() or f[0] == "EPAD"):
            continue
        um, die = float(f[col["Length (um)"]]), f[col["Die pad"]]
        if f[0] == "EPAD":
            out.setdefault(("EPAD", die), []).append(um)
        elif die == "EPAD":
            out[("lead", int(f[0]))] = um
        else:
            out[safe(die)] = um
    return out


def wire(a, b, um, name, lead=True):
    """A bond wire, with its QFN lead when it ends on one, a to b."""
    r, l = R_MM * um / 1000 + (R_LEAD if lead else 0), L_MM * um / 1000 + (L_LEAD if lead else 0)
    return [f"Rw_{name} {a} w_{name} {r:.4g}", f"Lw_{name} w_{name} {b} {l:.4g}"]


def pwl(points):
    """0/1 steps as a PWL with 1 ns edges."""
    out, last = [(0.0, points[0][1])], points[0][1]
    for t, v in points[1:]:
        if v != last:
            out += [(t, last), (t + 1e-9, v)]
            last = v
    return "PWL(" + " ".join(f"{t:.10g} {v}" for t, v in out) + ")"


def pulse(t0, width, period, edge="1n"):
    return f"PULSE(0 1 {t0:.8g} {edge} {edge} {width:.8g} {period:.8g})"


# the chip's ports as the DSA1 die has them, bits msb first, for tests that give no netlist
DSA1_PORTS = (["clk_PAD", "do_q_PAD", "do_q_b_PAD", "dsm_clk_PAD", "rst_n_PAD", "VSS", "VDDA", "VDD", "IOVSS", "IOVDD"]
              + [f"analog_PAD_{i}_" for i in (2, 1, 0)] + [f"input_PAD_{i}_" for i in (3, 2, 1, 0)]
              + [f"output_PAD_{i}_" for i in (1, 0)] + ["c_dsm_do_q", "c_dsm_do_q_b", "c_i_sg13cmos5l_dsa1_dig_core_output_out_1_"])
ANALOG_BIAS = ("analog_PAD_0_", "analog_PAD_1_")        # vi and vcm of the DSA1 die


def stimulus(order, bonds=None, ports=None, dsm2=False):
    """The bench netlist for one order: io_first, core_first, bounce, power_dsa1 or power_dsm. ports are the
    chip subcircuit's, as build() returns them, the DSA1 die's when not given. dsm2 is True with dsm2 as transistors."""
    ports = ports or DSA1_PORTS
    dsm2 = dsm2 and order not in POWER_ORDERS
    has = lambda n: n in ports
    vdda = has("VDDA")
    t0s = ramp_starts(order)
    pkg = order == "bounce"
    pw = order in POWER_ORDERS
    mosi, ss = [(0, 0)], [(0, 1)]
    for t0, addr, _, _, wdata in frames(order, dsm2):
        f = frame_bits(addr, wdata)
        # the slave samples bit i on sclk's falling edge t0 + (i + 1) T, so bit i goes out on the rising
        # edge half a period before it, as the host's I2S engine does
        ss += [(t0 + 1e-9, 0), (t0 + 24 * T_SCLK + 1e-9, 1)]
        mosi += [(t0 + 1e-9, f[0])] + [(t0 + (i + 0.5) * T_SCLK + 1e-9, f[i]) for i in range(1, 23)]
        mosi += [(t0 + 23.5 * T_SCLK + 1e-9, 0)]
    host = {"rst_n_PAD": "PWL(0 0 {t} 0 {t2} 1)".format(t=T_RST, t2=T_RST + 100e-9),
            "clk_PAD": pulse(T_SCLK_ON, T_CLK / 2 - 1e-9, T_CLK),
            # data_in toggles on clk's falling edges in the power orders, the DSA1 state of the board
            "input_PAD_0_": pulse(T_SCLK_ON + T_CLK / 2, T_CLK / 2 - 1e-9, T_CLK) if pw else "DC 0",
            # sclk idles low in the power orders: 400 kHz does not fit a whole number of the window's periods
            "input_PAD_1_": "DC 0" if pw else pulse(T_SCLK_ON + T_SCLK / 2, T_SCLK / 2 - 1e-9, T_SCLK),
            "input_PAD_2_": pwl(mosi), "input_PAD_3_": pwl(sorted(ss)),
            "dsm_clk_PAD": "DC 0" if t_dsm_clk(order, dsm2) is None else pulse(t_dsm_clk(order, dsm2), T_DSM / 2 - 1e-9, T_DSM)}
    host = {k: v for k, v in host.items() if has(k)}
    # a bench supply has output resistance, and ideal sources stall the solver when the ESD clamps wake
    # board nodes: the die's own without the package, a pin node _b behind its bond wire with it
    b = (lambda n: n + "_b") if pkg else (lambda n: n)
    # with dsm2 in, the bounce starts with the supplies up: dsm2's VDDA ramp needs backward Euler, which the package's
    # wires make far too slow, and the bounce is measured after the ramps anyway
    ramp = lambda t, v: f"{v}" if pkg and dsm2 else f"PWL(0 0 {t:.6g} 0 {t + RAMP:.6g} {v})"
    lines = [f"* {order}: the supply ramps, the host on the IOVDD rail, written by gen_startup.py",
             f"VIOVDD IOVDD_s 0 {ramp(t0s['IOVDD'], 3.3)}", f"RIOVDD IOVDD_s {b('IOVDD')} 0.5",
             f"VVDD VDD_s 0 {ramp(t0s['VDD'], 1.2)}", f"RVDD VDD_s {b('VDD')} 0.5"]
    if vdda:
        lines += [f"VVDDA VDDA_s 0 {ramp(t0s['VDDA'], 1.5)}", f"RVDDA VDDA_s {b('VDDA')} 0.5"]
    if dsm2 and not pkg:
        lines += ["* maxord=1 makes gear backward Euler: with the second order dsm2 stalls on the VDDA ramp near 0.35 V, at vcm and its",
                  "* switched-cap nodes, with any of the bench's or dsm2's own tolerances",
                  ".options maxord=1"]
    if pkg:
        bonds = bonds or bond_lengths()
        for n in ("IOVDD", "VDD") + (("VDDA",) if vdda else ()):
            lines += [f"Cd_{n} {n}_b dec_{n} {C_DEC:.4g}", f"Rd_{n} dec_{n} 0 {R_DEC:.4g}"] + wire(f"{n}_b", n, bonds[n], n)
        # VSS and IOVSS downbond to the paddle, which the leads to the cavity and the exposed pad tie to the board
        for n in ("IOVSS", "VSS"):
            for k, um in enumerate(bonds[("EPAD", n)]):
                lines += wire(n, "PADDLE", um, f"{n}_{k}", lead=False)
        for pin in sorted(k[1] for k in bonds if isinstance(k, tuple) and k[0] == "lead"):
            lines += wire("PADDLE", "0", bonds[("lead", pin)], f"lead{pin}")
        lines += [f"Rw_EP PADDLE w_EP {R_EP:.4g}", f"Lw_EP w_EP 0 {L_EP:.4g}", "Vsub sub! PADDLE 0"]
    else:
        lines += ["RIOVSS IOVSS 0 0.1", "RVSS VSS 0 0.1", "Vsub sub! 0 0"]
    # the host's pins swing at its supply through 50 Ohm, as a microcontroller output does. They follow
    # the regulator side, IOVDD_s: scaled by the chip's own rail they would form a loop with the pads.
    for pad, src in host.items():
        lines += [f"V{pad}_l {pad}_l 0 {src}", f"B{pad} {pad}_d 0 V=V({pad}_l)*V(IOVDD_s)", f"R{pad} {pad}_d {b(pad)} {R_SRC}"]
        if pkg:
            lines += wire(b(pad), pad, bonds[pad], pad)
    outs = [p for p in ports if p.startswith("output_PAD_") or p in ("do_q_PAD", "do_q_b_PAD")]
    for p in outs:
        lines.append(f"C{p} {b(p)} 0 {C_PIN:.4g}" if pkg else f"C{p} {p} 0 5p")
        if pkg:
            lines += wire(p, b(p), bonds[p], p)
    # vi and vcm: a source tracking VDDA in the bounce case, open (1 MOhm) otherwise, as the board holds them while VDDA ramps. The other analog pads stay at 1 MOhm.
    # With dsm2 as transistors only vi is driven, in every order, and vcm is left to dsm2's vcm_gen with 10 GOhm.
    analog = [p for p in ports if p.startswith(("analog_PAD_", "bidir_PAD_"))]
    for p in analog:
        if dsm2 and p == VI_PAD:
            lines += [f"B{p} {p}_d 0 V={V_VCM}*V(VDDA_s)", f"R{p} {p}_d {b(p)} {R_SRC}"] + (wire(b(p), p, bonds[p], p) if pkg else [])
        elif pkg and vdda and p in ANALOG_BIAS and not dsm2:
            lines += [f"B{p} {p}_d 0 V={V_VCM}*V(VDDA_s)", f"R{p} {p}_d {b(p)} {R_SRC}"] + wire(b(p), p, bonds[p], p)
        elif pkg and p in bonds:
            lines += [f"R{p} {b(p)} 0 {'10G' if dsm2 and p == VCM_PAD else '1Meg'}"] + wire(b(p), p, bonds[p], p)
        else:
            lines.append(f"R{p} {p} 0 {'10G' if dsm2 and p == VCM_PAD else '1Meg'}")
    # The 0/1 levels of the bench-driven pad inputs. dsm2's outputs toggle at every rising dsm_clk edge, complementary, as a worst case of the bit stream. The adc_conv pulse is one clk cycle wide.
    for c in (p for p in ports if p.startswith("c_")):
        if dsm_active(order) and c in ("c_dsm_do_q", "c_dsm_do_q_b"):
            first = T_DSM_ON + 5e-9 + (T_DSM if c == "c_dsm_do_q_b" else 0)
            src = pulse(first, T_DSM - 1e-9, 2 * T_DSM)
        elif order == "bounce" and c.endswith("output_out_1_"):
            src = pulse(ADC_CONV_AT_DSM2 if dsm2 else ADC_CONV_AT, T_CLK - 1e-9, 1)
        else:
            src = "DC 0"
        lines.append(f"V{c} {c} 0 {src}")
    if dsm2:
        t0 = t_dsm_clk(order, True)
        for k, d in enumerate(BRK):
            lines += [f"Vbrk{k} brk{k} 0 PULSE(0 1 {t0 + d:.12g} 1p 1p {T_DSM / 2 - 2e-12:.12g} {T_DSM / 2:.12g})", f"Rbrk{k} brk{k} 0 1Meg"]
    lines.append("Xchip " + " ".join(ports) + " chip")
    # ngspice's default largest step, T_END / 50, strides into the IO clamps' turn-on at 12.4 us and stalls
    lines.append(f".tran 5n {t_end(order, dsm2):.6g} 0 200n")
    return "\n".join(lines) + "\n"


# each core input and the pin the host drives it through
HOST_PINS = {"rst_n": "rst_n_PAD", "sclk": "input_PAD_1_", "ss": "input_PAD_3_", "mosi": "input_PAD_2_",
             "clk": "clk_PAD", "data_in": "input_PAD_0_"}
CORE_INPUTS = {"rst_n": "i_sg13cmos5l_dsa1_dig_core_rst_n", "sclk": "i_sg13cmos5l_dsa1_dig_core_sclk",
               "ss": "i_sg13cmos5l_dsa1_dig_core_ss", "mosi": "i_sg13cmos5l_dsa1_dig_core_mosi",
               "clk": "clk_PAD2CORE", "data_in": "i_sg13cmos5l_dsa1_dig_core_data_in_pad"}


# dsm2's pins that the checks read, with dsm2 as transistors
DSM2_PROBES = ("di_clk", "di_ena", "di_rst_b", "di_qout_en", "do_q", "do_q_b", "do_q_dec")


def dsm2_probes(dsm2):
    """{dsm2 pin: wrdata name of its net} for DSM2_PROBES, from build()'s pin map."""
    return {p: f"v(xchip.{dsm2[p]})" for p in DSM2_PROBES}


def probes(order, ports=None, dsm2=None):
    """(.save names, wrdata names) of an order. dsm2 is build()'s pin map with dsm2 as transistors."""
    ports = ports or DSA1_PORTS
    outs = [p for p in ports if p.startswith("output_PAD_") or p in ("do_q_PAD", "do_q_b_PAD")]
    v = ["IOVDD", "VDD", "rst_n_PAD", "input_PAD_1_", "input_PAD_2_", "input_PAD_3_"] + outs
    cur = ["VIOVDD", "VVDD"]
    if "VDDA" in ports:
        v.append("VDDA")
        cur.append("VVDDA")
    if order == "bounce":
        v += ["VSS", "IOVSS", "PADDLE", "IOVDD_b", "VDD_b", "VDDA_b"] + [f"{p}_b" for p in outs]
        v += [f"xchip.{n}" for n in CORE_INPUTS.values()] + [f"{p}_b" for p in HOST_PINS.values()]
        v += ["dsm_clk_PAD_b", "xchip.vi", "xchip.vcm", "xchip.ibias_test", "analog_PAD_0_", "analog_PAD_1_"]
        cur += ["Lw_IOVDD", "Lw_VDD", "Lw_VDDA", "Lw_IOVSS_0"]
    if dsm2 and order not in POWER_ORDERS:
        cur.append("v.xchip.Vdsm2_vdd")
        v += [p for p in ("dsm_clk_PAD", "analog_PAD_0_", "analog_PAD_0__d", "analog_PAD_1_", "analog_PAD_2_",
                          "xchip.vi", "xchip.vcm", "xchip.ibias_test") + (("analog_PAD_0__b",) if order == "bounce" else ()) if p not in v]
        v += [n[2:-1] for n in dsm2_probes(dsm2).values() if n[2:-1] not in v]
    return [f"{c}#branch" for c in cur] + [f"v({n})" for n in v], [f"i({c})" for c in cur] + [f"v({n})" for n in v]


def testbench(template, order, ports=None, dsm2=None):
    """startup_tb.spice for one order, @CSHUNT@ left to run_startup.sh."""
    def cont(names):
        return "\n+ ".join(" ".join(names[i:i + 6]) for i in range(0, len(names), 6))
    real = bool(dsm2) and order not in POWER_ORDERS
    save, wr = probes(order, ports, dsm2)
    if CORNER == "ss_m40":
        for a, b in COLD.items():
            template = template.replace(f" {a}\n", f" {b}\n")
        # dsm2's tolerances at -40 C. XSPICE forces trtol to 1 anyway.
        template = template.replace("\n.control", "\n.temp -40\n.options gmin=1e-10 reltol=1e-3 trtol=7\n.control", 1)
    else:
        assert CORNER == "tt", f"STARTUP_CORNER {CORNER} is not tt or ss_m40"
    return (template.replace("@ORDER@", order).replace("@SAVE@", cont(save)).replace("@WRDATA@", cont(wr))
            .replace("@CHIP@", "chip.spice" if real else "chip_box.spice")
            .replace("@DSM2@", ".include dsm2.spice" if real else "* dsm2 is a box in this order"))


def clamp_spice(cdl):
    """The clamp cell's CDL as ngspice reads it: MOS as calls of the PDK's model subcircuits,
    each rppd as a call with the substrate as third pin."""
    out = []
    for ln in cdl.splitlines():
        if re.match(r"^[Mm]\S* ", ln):
            ln = "X" + ln
        m = re.match(r"^R(\S+) (\S+) (\S+) \S+ \$SUB=(\S+) \$\[(\w+)\] (.*?) b=0$", ln)
        if m:
            ln = f"XR{m[1]} {m[2]} {m[3]} {m[4]} {m[5]} {m[6]}"
        if not ln.startswith("*.PININFO"):
            out.append(ln)
    return "\n".join(out) + "\n"


def patch_xspice(core_spice, xspice):
    """core.xspice with every CGX3 of core.spice modelled, CDL pins CK E GCLK."""
    add = []
    for line in core_spice.splitlines():
        f = line.split()
        if f and f[0].startswith("X") and f[-1] == "CGX3":
            inst, ck, en, gclk = f[0][1:], f[1], f[2], f[3]
            add += [f"A{inst}_l {en} ~{ck} NULL NULL {inst}_qe NULL dlatch",
                    f"A{inst}_g [{ck} {inst}_qe] {gclk} d_lut_AND2X1"]
    if "d_lut_AND2X1" not in xspice or ".model dlatch" not in xspice:
        raise SystemExit("core.xspice lacks the AND2 or latch model the clock gates need")
    head, tail = xspice.rsplit(".ends core", 1)
    return head + "\n".join(["* CGX3 clock gates, added by gen_startup.py --patch-xspice", *add]) + "\n.ends core" + tail, len(add) // 2


def self_test():
    import tempfile
    v = """
module m (a, y, VDD, VSS);
 input [1:0] a; output y; inout VDD; inout VSS;
 NAND2X1 g (.A(a[1]), .B(a[0]), .Y(y), .VDD(VDD), .VSS(VSS));
 FILLER1 f (.VDD(VDD), .VSS(VSS));
endmodule
"""
    top = """
module sg13cmos5l_dsa1_dig_top (p, q, d, VDD, VDDA, VSS, IOVDD, IOVSS);
 inout p; inout q; inout d; inout VDD; inout VDDA; inout VSS; inout IOVDD; inout IOVSS;
 wire \\x.in[0] ; wire n1; wire o; wire dq; wire ac; wire dqd; wire o2;
 sg13cmos5l_IOPadIn pi (.pad(p), .p2c(\\x.in[0] ), .vdd(VDD), .vss(VSS), .iovdd(IOVDD), .iovss(IOVSS));
 INVX1 inv (.A(\\x.in[0] ), .Y(n1), .VDD(VDD), .VSS(VSS));
 dsa1_dig_top \\i.mac  (.a({n1, \\x.in[0] }), .y(o), .VDD(VDD), .VSS(VSS));
 sg13cmos5l_IOPadOut30mA po (.pad(q), .c2p(o), .vdd(VDD), .vss(VSS), .iovdd(IOVDD), .iovss(IOVSS));
 sg13cmos5l_IOPadOut4mA pd (.pad(d), .c2p(dq), .vdd(VDDA), .vss(VSS), .iovdd(IOVDD), .iovss(IOVSS));
 sg13cmos5l_IOPadOut30mA pa (.pad(q), .c2p(ac), .vdd(VDD), .vss(VSS), .iovdd(IOVDD), .iovss(IOVSS));
 dsm2_core dsm (.vdd(VDDA), .vss(VSS), .do_q(dq), .do_q_b(dqb), .do_q_dec(dqd), .vi(vi), .vcm(vcm), .ibias_test(ib), .di_clk(ck),
    .di_ena(n1), .di_rst_b(o), .di_trim({n1, o, n1, o}), .di_dith_en(n1), .di_dith_amp({o, n1}), .di_vcm_ext(n1), .di_btest_en(n1), .di_qout_en(o));
 NAND2X1 dec (.A(dqd), .B(n1), .Y(o2), .VDD(VDD), .VSS(VSS));
 AND2X1 \\i.u_adc_conv_gate  (.A(n1), .B(o), .Y(ac), .VDD(VDD), .VSS(VSS));
 sg13cmos5l_ip__cut_vdd cut (.iovdd(IOVDD), .iovss(IOVSS), .vss(VSS));
endmodule
"""
    cdl = ".SUBCKT NAND2X1 A B Y VDD VSS\n.ENDS\n.SUBCKT INVX1 A Y VDD VNW VPW VSS\n.ENDS\n"
    cut = ".SUBCKT sg13cmos5l_ip__cut_vdd vss iovdd iovss\n*.PININFO vss:B\n.ENDS\n"
    io = ".subckt sg13cmos5l_IOPadIn vss vdd iovss iovdd p2c pad\n.ends\n" \
         ".subckt sg13cmos5l_IOPadOut30mA vss vdd iovss iovdd c2p pad\n.ends\n" \
         ".subckt sg13cmos5l_IOPadOut4mA vss vdd iovss iovdd c2p pad\n.ends\n"
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for name, text in (("t.v", top), ("m.v", v.replace("module m", "module dsa1_dig_top")), ("c.cdl", cdl), ("io.spi", io), ("cut.cdl", cut)):
            paths.append(os.path.join(d, name))
            open(paths[-1], "w").write(text)
        r = build(*paths[:4], None, paths[4])
        rs = build(*paths[:4], None, paths[4], dsm2="sch")
        no_dsm = paths[0] + ".nodsm"
        open(no_dsm, "w").write(top.replace(top[top.index(" dsm2_core"):top.index(" NAND2X1 dec")], ""))
        try:
            build(no_dsm, *paths[1:4], None, paths[4], dsm2="sch")
            raise AssertionError("dsm2 as transistors needs a dsm2_core in the netlist")
        except SystemExit as e:
            assert "no dsm2_core" in str(e), e
    # dsm2's controls and do_q_dec are core ports with dsm2 a box too, so one core.xspice serves every order
    assert r["ports"] == ["dqd", "n1", "o", "x.in[0]"] and rs["ports"] == r["ports"] and rs["core"] == r["core"], r["ports"]
    assert "Bn1 n1_d 0 V=V(u_n1)*V(VDD_s)/1.2" in r["chip"] and "Xcore dqd u_n1 u_o x_in_0_ core" in r["chip"], r["chip"]
    # dsm2 a box: its do_q pad and the adc_conv gate are bench sources on the pad's rail, do_q_dec held low
    assert r["external"] == {"ac": "VDD", "dq": "VDDA"} and "Rx_dqd dqd 0 1G" in r["chip"] and r["dsm2"] == {}, r["external"]
    # dsm2 as transistors: on VDDA through a 0 V sense source, its outputs drive the pad and the core
    assert rs["external"] == {"ac": "VDD"} and "Bx_dq" not in rs["chip"] and "Rx_dqd" not in rs["chip"], rs["chip"]
    assert "Vdsm2_vdd VDDA dsm2_VDDA 0" in rs["chip"] and "Cdsm2_dec dqd 0 1.5e-14" in rs["chip"], rs["chip"]
    assert "Xdsm2 vi vcm ck n1 o n1 o n1 o n1 o n1 n1 n1 o dq dqb dqd ib dsm2_VDDA VSS dsm2_wrap" in rs["chip"], rs["chip"]
    assert rs["dsm2"]["di_trim[3]"] == "n1" and rs["dsm2"]["di_dith_amp[0]"] == "n1" and rs["dsm2"]["vdd"] == "VDDA", rs["dsm2"]
    assert dsm2_probes(rs["dsm2"])["di_ena"] == "v(xchip.n1)" and dsm2_probes(rs["dsm2"])["do_q_dec"] == "v(xchip.dqd)"
    w = dsm2_wrapper("/x/dsm2_core_pex3.spice", "dsm2_core_pex")
    assert ".options rshunt=1e12\n" in w and ".subckt dsm2_wrap vi vcm di_clk di_ena" in w and ".include /x/dsm2_core_pex3.spice" in w and "vdd vss dsm2_core_pex\n.ends" in w, w
    assert "Bx_dq x_dq 0 V=V(c_dq)*V(VDDA_s)" in r["chip"] and "Rx_ac x_ac ac 1k" in r["chip"], r["chip"]
    assert r["chip_ports"][-2:] == ["c_ac", "c_dq"] and ".subckt chip p q d VDD VDDA VSS IOVDD IOVSS c_ac c_dq" in r["chip"], r["chip"]
    assert "Xcut VSS IOVDD IOVSS sg13cmos5l_ip__cut_vdd" in r["chip"] and "Xdsm" not in r["core"] and "u_adc" not in r["core"], r["core"]
    assert "Xi_mac_g n1 x_in_0_ o VDD VSS NAND2X1" in r["core"], r["core"]      # a[1] is the msb, n1
    assert "Xinv x_in_0_ n1 VDD VDD VSS VSS INVX1" in r["core"], r["core"]   # wells to the rails
    assert ".subckt INVX1 P0Q P1Q VDD VNW VPW VSS" in r["core"], r["core"]
    assert "FILLER1" not in r["core"] and r["n_core"] == 3 and r["n_io"] == 5
    assert "Xpi VSS VDD IOVSS IOVDD x_in_0_ p sg13cmos5l_IOPadIn" in r["chip"], r["chip"]
    assert "Xpo VSS VDD IOVSS IOVDD o q sg13cmos5l_IOPadOut30mA" in r["chip"], r["chip"]
    lib = 'library (x) {\n  a : 1;\n  cell (AND2X1) {\n    pin (Y) { function : "A&B"; }\n  }\n  cell (BANK) {\n    bundle (D) { x : y; }\n  }\n}\n'
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.lib"), "w").write(lib)
        sub = liberty_subset(os.path.join(d, "x.lib"), {"AND2X1"})
    assert "cell (AND2X1)" in sub and "BANK" not in sub and sub.count("{") == sub.count("}"), sub
    # B must not touch AB, and the supplies keep their names
    m = pin_map(["AB", "B", "Y", "VDD", "VNW", "VSS"])
    assert m == {"AB": "P0Q", "B": "P1Q", "Y": "P2Q"}, m
    blk = 'cell (NOR2BX1) {\n pin (Y) {\n  function : "(AB * !B)";\n  related_pin : "AB";\n  values ("1, 2");\n }\n pin (AB) {\n'
    out = rename_pins(blk, m)
    assert '"(P0Q * !P1Q)"' in out and "pin (P2Q)" in out and 'related_pin : "P0Q"' in out and "pin (P0Q)" in out, out
    x = ".subckt core a\nAg [a b] y d_lut_AND2X1\n.model dlatch d_dlatch\n.ends core\n.model d_lut_AND2X1 d_lut\n"
    out, n = patch_xspice("Xcg ck en gck VDD VDD VSS VSS CGX3\nXo a y VDD VSS INVX1\n", x)
    assert n == 1 and "Acg_l en ~ck NULL NULL cg_qe NULL dlatch" in out and "Acg_g [ck cg_qe] gck d_lut_AND2X1" in out, out
    assert out.index("Acg_g") < out.index(".ends core"), out
    assert frame_bits(15)[:6] == [1, 1, 1, 1, 1, 0] and frame_bits(15)[6:] == [0] * 17 and len(frame_bits(15)) == 23
    # a write as the cocotb bench frames it, (addr << 18) | (data << 1)
    assert frame_bits(9, 0xFDAF) == [((9 << 18 | 0xFDAF << 1) >> k) & 1 for k in range(22, -1, -1)]
    assert frame_bits(9, 0xFDAF)[:6] == [0, 1, 0, 0, 1, 0] and frame_bits(9, 0xFDAF)[-1] == 0
    # a write as the cocotb bench frames it, (addr << 18) | (data << 1)
    assert frame_bits(9, 0xFDAF) == [((9 << 18 | 0xFDAF << 1) >> k) & 1 for k in range(22, -1, -1)]
    assert frame_bits(9, 0xFDAF)[:6] == [0, 1, 0, 0, 1, 0] and frame_bits(9, 0xFDAF)[-1] == 0
    import importlib.util
    spec = importlib.util.spec_from_file_location("regmap", os.path.join(ROOT, "models/regmap.py"))
    rm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rm)
    # the bounce frames use a register that holds any 16 bits, and 0x5555 flips miso at every bit
    assert rm.ADDR["SPARE_14"] == SPARE_ADDR and rm.RESET[SPARE_ADDR] == 0 and rm.CHIP_ID == 15
    assert [MISO_PATTERN >> k & 1 for k in range(15, -1, -1)] == [0, 1] * 8
    # every mosi change sits half a period from the falling edge that samples the bit
    st = stimulus("io_first")
    assert "Vsub sub! 0 0" in st and "RVSS VSS 0 0.1" in st and "Lw_" not in st, st
    import re as _re
    pts = [float(x) for x in _re.search(r"Vinput_PAD_2__l \S+ 0 PWL\((.*?)\)", st).group(1).split()[0::2]]
    starts = [t0 for t0, *_ in FRAMES]      # bit 0 is set as ss falls, a period before its sample
    phase = [((t - 1e-9) % T_SCLK) / T_SCLK for t in pts
             if t > FRAMES[0][0] + T_SCLK and not any(abs(t - t0) < 1e-8 for t0 in starts)]
    assert all(abs(ph - 0.5) < 0.01 or abs(ph - 0.5004) < 0.01 for ph in phase), phase
    # and at each sampling edge mosi carries the bit that edge takes
    m = _re.search(r"Vinput_PAD_2__l \S+ 0 PWL\((.*?)\)", st).group(1).split()
    tv = [(float(a), float(b)) for a, b in zip(m[0::2], m[1::2])]
    level = lambda x: [v for t, v in tv if t <= x][-1]
    for t0, addr, *_ in FRAMES:
        assert [level(t0 + (i + 1) * T_SCLK - 1e-8) for i in range(23)] == frame_bits(addr), addr
    # IOVDD first: VDD and VDDA come 140 us later together, on 1.2 V and 1.5 V
    assert "VIOVDD IOVDD_s 0 PWL(0 0 1e-05 0 0.00011 3.3)" in st and "VVDDA VDDA_s 0 PWL(0 0 0.00015 0 0.00025 1.5)" in st, st
    assert "VVDD VDD_s 0 PWL(0 0 0.00015 0 0.00025 1.2)" in st and "RVDDA VDDA_s VDDA 0.5" in st, st
    # dsm2 off and dsm_clk low outside the orders that run it, data_in still
    assert "Vdsm_clk_PAD_l dsm_clk_PAD_l 0 DC 0" in st and "Vc_dsm_do_q c_dsm_do_q 0 DC 0" in st and "Vinput_PAD_0__l input_PAD_0__l 0 DC 0" in st, st
    # the bounce order: its writes on mosi, the package in place of the ideal grounds
    bonds = {safe(n): 1000.0 for n in ["clk_PAD", "rst_n_PAD", "IOVDD", "VDD", "VDDA", "dsm_clk_PAD", "do_q_PAD", "do_q_b_PAD"]
             + [f"input_PAD[{i}]" for i in range(4)] + [f"output_PAD[{i}]" for i in range(2)] + [f"analog_PAD[{i}]" for i in range(3)]}
    bonds.update({("EPAD", "VSS"): [500.0, 480.0], ("EPAD", "IOVSS"): [500.0], ("lead", 3): 500.0, ("lead", 5): 500.0})
    sb = stimulus("bounce", bonds)
    m = _re.search(r"Vinput_PAD_2__l \S+ 0 PWL\((.*?)\)", sb).group(1).split()
    tv = [(float(a), float(b)) for a, b in zip(m[0::2], m[1::2])]
    for t0, addr, _, _, wdata in BOUNCE_FRAMES:
        assert [level(t0 + (i + 1) * T_SCLK - 1e-8) for i in range(23)] == frame_bits(addr, wdata), addr
    for ln in ("Rw_VSS_0 VSS w_VSS_0 0.025", "Lw_VSS_1 w_VSS_1 PADDLE 4.8e-10", "Lw_IOVSS_0 w_IOVSS_0 PADDLE 5e-10",
               "Lw_lead3 w_lead3 0 1e-09", "Lw_lead5 w_lead5 0 1e-09", "Vsub sub! PADDLE 0",
               "Rinput_PAD_1_ input_PAD_1__d input_PAD_1__b 50", "Lw_input_PAD_1_ w_input_PAD_1_ input_PAD_1_ 1.5e-09",
               "Coutput_PAD_1_ output_PAD_1__b 0 1e-11", "Lw_IOVDD w_IOVDD IOVDD 1.5e-09", "Cd_VDD VDD_b dec_VDD 1e-07",
               "Cd_VDDA VDDA_b dec_VDDA 1e-07", "Lw_VDDA w_VDDA VDDA 1.5e-09", "RVDDA VDDA_s VDDA_b 0.5",
               "VVDD VDD_s 0 PWL(0 0 1e-05 0 0.00011 1.2)", "RVDD VDD_s VDD_b 0.5",
               "Banalog_PAD_0_ analog_PAD_0__d 0 V=0.5*V(VDDA_s)", "Ranalog_PAD_1_ analog_PAD_1__d analog_PAD_1__b 50",
               "Ranalog_PAD_2_ analog_PAD_2__b 0 1Meg", "Lw_do_q_PAD w_do_q_PAD do_q_PAD_b 1.5e-09",
               "Cdo_q_b_PAD do_q_b_PAD_b 0 1e-11"):
        assert ln in sb, (ln, sb)
    assert "Vc_dsm_do_q c_dsm_do_q 0 PULSE(0 1 0.000290005 " in sb and "Vc_dsm_do_q_b c_dsm_do_q_b 0 PULSE(0 1 0.000290981" in sb, sb
    assert "Vdsm_clk_PAD_l dsm_clk_PAD_l 0 PULSE(0 1 0.00029 1n 1n 4.8728125e-07 9.765625e-07)" in sb, sb
    assert "Vc_i_sg13cmos5l_dsa1_dig_core_output_out_1_ c_i_sg13cmos5l_dsa1_dig_core_output_out_1_ 0 PULSE(0 1 0.000456 " in sb, sb
    assert "RVSS" not in sb and sb.rstrip().endswith(".tran 5n 0.00052 0 200n"), sb
    assert all(b[0] >= a[0] + 24 * T_SCLK for a, b in zip(BOUNCE_FRAMES, BOUNCE_FRAMES[1:])) and BOUNCE_FRAMES[-1][0] + 24 * T_SCLK < T_END_BOUNCE
    assert T_DSM_ON > T_SECOND + RAMP and ADC_CONV_AT > BOUNCE_FRAMES[-1][0] and ADC_CONV_AT + T_CLK < BOUNCE_FRAMES[-1][0] + 24 * T_SCLK
    # the power orders: data_in toggles on clk's falling edge, dsm_clk and the outputs only in power_dsm
    p1, p2 = stimulus("power_dsa1"), stimulus("power_dsm")
    assert "Vinput_PAD_0__l input_PAD_0__l 0 PULSE(0 1 0.00028762" in p1 and "Vdsm_clk_PAD_l dsm_clk_PAD_l 0 DC 0" in p1, p1
    assert "Vc_dsm_do_q c_dsm_do_q 0 DC 0" in p1 and "Vc_dsm_do_q c_dsm_do_q 0 PULSE" in p2 and "Vc_dsm_do_q_b c_dsm_do_q_b 0 PULSE" in p2, p2
    assert "Vdsm_clk_PAD_l dsm_clk_PAD_l 0 PULSE" in p2 and "Vinput_PAD_0__l" in p2 and "PULSE(0 1 0.00028762" in p2, p2
    assert "Vinput_PAD_1__l input_PAD_1__l 0 DC 0" in p1 and "Vinput_PAD_1__l input_PAD_1__l 0 DC 0" in p2 and "Vinput_PAD_1__l input_PAD_1__l 0 PULSE" in st, (p1, st)
    assert "Vinput_PAD_3__l input_PAD_3__l 0 PWL(0 1)" in p1 and p1.rstrip().endswith(".tran 5n 0.00052 0 200n"), p1     # ss stays high, no frame
    assert abs(P_WINDOW * 1.024e6 - 125) < 1e-9 and T_END_POWER - P_WINDOW > T_DSM_ON + 50e-6
    # a die with no VDDA, dsm2 or bench-driven pad, v1.1.1: nothing of them in its stimulus
    old = ["clk_PAD", "rst_n_PAD", "VSS", "VDD", "IOVSS", "IOVDD", "analog_PAD_1_", "analog_PAD_0_", "bidir_PAD_1_", "bidir_PAD_0_"] \
        + [f"input_PAD_{i}_" for i in (3, 2, 1, 0)] + [f"output_PAD_{i}_" for i in range(17, -1, -1)]
    po = stimulus("power_dsa1", None, old)
    assert "VDDA" not in po and "dsm" not in po and "Rbidir_PAD_0_ bidir_PAD_0_ 0 1Meg" in po and "Coutput_PAD_17_ output_PAD_17_ 0 5p" in po, po
    assert po.rstrip().endswith("Xchip " + " ".join(old) + " chip\n.tran 5n 0.00052 0 200n"), po
    tb = testbench("x @ORDER@\n.save @SAVE@\nwrdata f @WRDATA@\n", "bounce")
    assert "x bounce" in tb and "Lw_IOVDD#branch" in tb and "i(Lw_VDDA)" in tb and "v(xchip.clk_PAD2CORE)" in tb and "v(xchip.vi)" in tb, tb
    assert all(len(ln.split()) <= 7 for ln in tb.splitlines() if ln.startswith("+")), tb
    rows = "| 4 | IOVDD | IOVDD | a | b | 1296.0 | x | y | z |\n| 5 | VSS | EPAD | a | b | 500.0 | x | 0.0 | z |\n" \
           "| EPAD | VSS | VSS | a | b | 480.0 | x | - | z |\n| EPAD | VSS | VSS | a | b | 470.0 | x | - | z |\n" \
           "| 8 | miso | output_PAD[0] | a | b | 1699.1 | x | y | z |\n| 9 | x | y | 1.0 |\n"
    head = "| Pin | Signal | Die pad | Die x/y (um) | Package x/y (um) | Length (um) | Angle (deg) | Skew (deg) | Min gap (um) |\n|---|---|---|---|---|---|---|---|---|\n"
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "r.md"), "w").write("| Bondwires | 23 |\n" + head + rows)
        bl = bond_lengths(os.path.join(d, "r.md"))
    assert bl == {"IOVDD": 1296.0, ("lead", 5): 500.0, ("EPAD", "VSS"): [480.0, 470.0], "output_PAD_0_": 1699.1}, bl
    assert pwl([(0, 1), (1e-6, 1), (2e-6, 0)]) == "PWL(0 1 2e-06 1 2.001e-06 0)", pwl([(0, 1), (1e-6, 1), (2e-6, 0)])
    st = stimulus("core_first")
    assert "VVDD VDD_s 0 PWL(0 0 1e-05 0 0.00011 1.2)" in st and "VIOVDD IOVDD_s 0 PWL(0 0 0.00015 0 0.00025 3.3)" in st, st
    assert "VVDDA VDDA_s 0 PWL(0 0 1e-05 0 0.00011 1.5)" in st, st
    assert "Brst_n_PAD rst_n_PAD_d 0 V=V(rst_n_PAD_l)*V(IOVDD_s)" in st and "Rrst_n_PAD rst_n_PAD_d rst_n_PAD 50" in st, st
    assert "PULSE(0 1 0.00028125 " in st and "PULSE(0 1 0.00028 1n" in st and st.rstrip().endswith(".tran 5n 0.000515 0 200n"), st
    assert "RVDD VDD_s VDD 0.5" in st and "Coutput_PAD_0_ output_PAD_0_ 0 5p" in st and "Ranalog_PAD_0_ analog_PAD_0_ 0 1Meg" in st, st
    assert all(t0 % T_SCLK < 1e-12 or T_SCLK - t0 % T_SCLK < 1e-12 for t0, *_ in FRAMES + BOUNCE_FRAMES)     # frames start on an sclk falling edge
    assert all(b[0] >= a[0] + 24 * T_SCLK for a, b in zip(FRAMES, FRAMES[1:])) and FRAMES[-1][0] + 24 * T_SCLK < T_END
    assert "Bo o_d 0 V=V(u_o)*V(VDD_s)/1.2" in r["chip"] and "Rd_o o_d o 1k" in r["chip"], r["chip"]
    # dsm2 as transistors: its start-up frames, DSM_EN then 130 us later DSM_RST_B with DSM_QOUT_EN, dsm_clk from 5 us before
    real = [p for p in DSA1_PORTS if not p.startswith("c_dsm")]
    for order in ("core_first", "bounce"):
        on, run = dsm2_times(order)
        assert abs(run - on - T_DSM_WAIT) < 1e-12, (order, on, run)
        sr = stimulus(order, bonds if order == "bounce" else None, real, True)
        m = _re.search(r"Vinput_PAD_2__l \S+ 0 PWL\((.*?)\)", sr).group(1).split()
        tv = [(float(a), float(b)) for a, b in zip(m[0::2], m[1::2])]
        for t0, addr, _, _, wdata in frames(order, True):
            assert [level(t0 + (i + 1) * T_SCLK - 1e-8) for i in range(23)] == frame_bits(addr, wdata), (order, addr)
        assert f"Vdsm_clk_PAD_l dsm_clk_PAD_l 0 PULSE(0 1 {run - 5e-6:.8g} " in sr and "Vc_dsm" not in sr, sr
        assert "Banalog_PAD_0_ analog_PAD_0__d 0 V=0.5*V(VDDA_s)" in sr and "Banalog_PAD_1_" not in sr, sr
        assert f"Ranalog_PAD_1_ analog_PAD_1_{'_b' if order == 'bounce' else ''} 0 10G" in sr, sr
        # the bounce starts with the supplies up and keeps the second order, the start-up orders ramp with backward Euler
        assert ("VVDDA VDDA_s 0 1.5\n" in sr and "maxord" not in sr) if order == "bounce" else (".options maxord=1" in sr and "VVDDA VDDA_s 0 PWL(" in sr), sr
        assert sr.rstrip().endswith(f".tran 5n {t_end(order, True):.6g} 0 200n"), sr
        assert f"Vbrk0 brk0 0 PULSE(0 1 {run - 5e-6 + 1e-9:.12g} 1p 1p " in sr and "Vbrk20 brk20 0 PULSE(0 1 " in sr and "Vbrk21" not in sr, sr
    assert dsm2_times("core_first") == (530e-6 + T_STORE, 660e-6 + T_STORE) and T_END_DSM2 >= dsm2_times("core_first")[1] + 40e-6
    assert dsm2_times("bounce") == (385e-6 + T_STORE, 515e-6 + T_STORE) and [f[2] for f in frames("bounce", True) if f[3] is not None] == ["CHIP_ID", "SPARE_14"]
    assert [f[1:] for f in frames("core_first", True)[3:]] == [(3, "BIAS_CFG_1", None, 0x41), (3, "BIAS_CFG_1", None, 0x63)]
    assert rm.ADDR["BIAS_CFG_1"] == BIAS_CFG_1 and rm.RESET[BIAS_CFG_1] == 0x0040 and DSM_ON == 0x40 | 1 and DSM_RUN == 0x40 | 0x20 | 2 | 1
    assert "Ranalog_PAD_0_ analog_PAD_0__d analog_PAD_0__b 50" in sr and "Vc_i_sg13cmos5l_dsa1_dig_core_output_out_1_ c_i_sg13cmos5l_dsa1_dig_core_output_out_1_ 0 PULSE(0 1 0.000586 " in sr, sr
    bf = frames("bounce", True)
    assert all(b[0] >= a[0] + 24 * T_SCLK for a, b in zip(bf, bf[1:])) and bf[-1][0] + 24 * T_SCLK < T_END_BOUNCE_DSM2
    assert ADC_CONV_AT_DSM2 > bf[-1][0] and ADC_CONV_AT_DSM2 + T_CLK < bf[-1][0] + 24 * T_SCLK and bf[0][0] > T_RST
    # the power orders keep the box, they have no frames to start dsm2
    assert stimulus("power_dsm", None, DSA1_PORTS, True) == stimulus("power_dsm")
    tb = testbench("@DSM2@\n.include @CHIP@\n.save @SAVE@\nwrdata f @WRDATA@\n", "core_first", real, rs["dsm2"])
    assert ".include dsm2.spice\n.include chip.spice" in tb and "v.xchip.Vdsm2_vdd#branch" in tb and "i(v.xchip.Vdsm2_vdd)" in tb and "v(xchip.n1)" in tb, tb
    tb = testbench("@DSM2@\n.include @CHIP@\n.save @SAVE@\n", "power_dsm", None, rs["dsm2"])
    assert "* dsm2 is a box" in tb and "chip_box.spice" in tb and "Vdsm2" not in tb, tb
    cs = clamp_spice("Mclamp vdd g vss vss sg13_hv_nmos w=2268u l=0.6u ng=252\n"
                     "Rtrig1 vdd rt1 5.172k $SUB=vss $[rppd] w=1u l=20u b=0\n*.PININFO vdd:B\n")
    assert cs == "XMclamp vdd g vss vss sg13_hv_nmos w=2268u l=0.6u ng=252\nXRtrig1 vdd rt1 vss rppd w=1u l=20u\n", cs
    print("OK: gen_startup self-test")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(HERE, "build"))
    ap.add_argument("--tree", help="the repo or a worktree of an older tag to take the netlists from, default this one")
    ap.add_argument("--orders", default=",".join(ORDERS), help="comma separated, default all")
    ap.add_argument("--dsm2", default="sch", choices=("sch", "pex", "box"),
                    help="dsm2 as its schematic or extracted netlist, or a box with bench sources, default sch. The power orders always take the box")
    ap.add_argument("--patch-xspice", action="store_true", help="add the clock gates to <out>/core.xspice")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if a.patch_xspice:
        x = os.path.join(a.out, "core.xspice")
        text, n = patch_xspice(open(os.path.join(a.out, "core.spice")).read(), open(x).read())
        open(x, "w").write(text)
        print(f"core.xspice: {n} CGX3 clock gates added")
        return 0
    f = {k: os.path.join(a.tree or ROOT, v) for k, v in TREE_FILES.items()}
    f["io_spi"] = io_spice()
    cdl = os.path.join(os.environ["EZ130_DIR"], "cdl/ez130_8t.cdl")
    orders = a.orders.split(",")
    r = build(f["chip_pnl"], f["macro_pnl"], cdl, f["io_spi"], f["clamp_cdl"], f["cut_cdl"])
    os.makedirs(a.out, exist_ok=True)
    open(os.path.join(a.out, "core.spice"), "w").write(r["core"])
    open(os.path.join(a.out, "chip_box.spice"), "w").write(r["chip"])
    real = None
    if a.dsm2 != "box" and any(o not in POWER_ORDERS for o in orders):
        real = build(f["chip_pnl"], f["macro_pnl"], cdl, f["io_spi"], f["clamp_cdl"], f["cut_cdl"], dsm2=a.dsm2)
        assert real["core"] == r["core"], "the core must not depend on the dsm2 view"
        open(os.path.join(a.out, "chip.spice"), "w").write(real["chip"])
        name, subckt = DSM2_VIEWS[a.dsm2]
        open(os.path.join(a.out, "dsm2.spice"), "w").write(dsm2_wrapper(os.path.join(a.tree or ROOT, DSM2_DIR, name), subckt,
                                                                          DSM2_PORTS + (DSM2_OSC if "di_osc_en" in real["dsm2"] else [])))
        open(os.path.join(a.out, "dsm2_probes.json"), "w").write(json.dumps({"view": a.dsm2, **dsm2_probes(real["dsm2"])}, indent=1))
    elif os.path.exists(os.path.join(a.out, "dsm2_probes.json")):
        os.remove(os.path.join(a.out, "dsm2_probes.json"))      # the checker reads it as dsm2 being in
    open(os.path.join(a.out, "clamp.spice"), "w").write(clamp_spice(open(f["clamp_cdl"]).read()) + (
        clamp_spice(open(f["cut_cdl"]).read()) if os.path.exists(f["cut_cdl"]) else ""))
    lib = liberty_subset(os.path.join(os.environ["EZ130_DIR"], "lib/ez130_8t_tt_1p20v_25c.lib"), set(r["cells"]), r["maps"])
    open(os.path.join(a.out, "cells.lib"), "w").write(lib)
    template = open(os.path.join(HERE, "startup_tb.spice")).read().replace("@IO_SPI@", f["io_spi"])
    bonds = bond_lengths(f["bond_report"]) if os.path.exists(f["bond_report"]) else None
    for order in orders:
        rr = real if real and order not in POWER_ORDERS else r
        open(os.path.join(a.out, f"stim_{order}.spice"), "w").write(stimulus(order, bonds, rr["chip_ports"], rr is real))
        open(os.path.join(a.out, f"tb_{order}.in"), "w").write(testbench(template, order, rr["chip_ports"], rr["dsm2"]))
    print(f"core: {r['n_core']} cells of {len(r['cells'])} types, {len(r['ports'])} ports to {r['n_io']} IO cells, "
          f"{len(r['outputs'])} of them outputs scaled by VDD, {len(r['external'])} pad inputs driven by the bench with dsm2 a box"
          + (f", {len((real or {}).get('external', {}))} with dsm2 {a.dsm2}" if real else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
