#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Checks of the supply start-up bench, one wrdata file per order.

    python3 testbenches/startup/startup_check.py io_first.txt core_first.txt bounce.txt power_dsa1.txt power_dsm.txt --out verification/startup
    python3 testbenches/startup/startup_check.py --self-test

io_first, core_first: the three SPI reads after reset return the reset values, and no supply current stays above 10 mA for more than 1 us, as latch-up or two drivers fighting would.
Shorter peaks, an output pad charging its load, are reported.
The board order, VDD and VDDA up no later than IOVDD, must also keep dsm2's output pads (do_q, do_q_b) low.
For IOVDD first the pads' rise, the spike that rule avoids, is reported.
Before the reset release the core is XSPICE with every flop at 0, which says nothing about silicon's power-up state.

bounce: VDD and VDDA first through the package, dsm_clk at 1.024 MHz, do_q and do_q_b toggling at every edge, miso toggling through a SPARE_14 read and one adc_conv pulse.
It checks the reads and that no core input crosses its threshold more often than the host's pin does.
The ground and rail bounce, and the swing on vi, vcm and ibias_test, are reported.

power_dsa1, power_dsm: the settled supply currents over a whole number of data_in periods, dsm2 off with dsm_clk low against dsm_clk at 1.024 MHz with the do_q pads switching.
DEC_SRC is low, so VDD must not change.
The two VDD currents must differ by less than the resolution of the run, the largest of the difference between the window's two halves, 0.1 % of the current and 1 pA, the solver's tolerances.
A v1.1.1 current file adds the comparison of the two layouts.
The mean is weighted by time, because the solver's steps are 1 ns on an edge and up to 200 ns between them.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_startup import (BOUNCE_FRAMES, CORE_INPUTS, FRAMES, HOST_PINS, ORDERS, P_WINDOW, POWER_ORDERS, RAMP,  # noqa: E402
                         T_DSM, T_DSM_ON, T_SCLK, T_SECOND)

I_MAX = 10e-3
T_SUSTAINED = 1e-6
REQUIRED = "core_first"             # the supply order the board must use
SEG_PADS = ("v(do_q_pad)", "v(do_q_b_pad)")
SPIKE_V = 0.33                      # a segment output pad above this is a spike, 10 % of IOVDD
ACTIVITY = 0.9                      # the share of the edges the stimulus must show
MISO_EDGES_MIN = 12                 # 0x5555 has 15 in the read
RES_REL = 1e-3                      # the solver's reltol
RES_ABS = 1e-12                     # and its abstol, the floors of a current's resolution
T_BASE = (T_SECOND + RAMP + 10e-6, T_DSM_ON - 5e-6)     # the bounce's quiet window, rails settled, dsm2 not yet on
SUPPLIES = (("IOVDD", "viovdd"), ("VDD", "vvdd"), ("VDDA", "vvdda"))


def load(path):
    with open(path) as fh:
        names = fh.readline().split()
    d = np.loadtxt(path, skiprows=1)
    return {n.lower(): d[:, i] for i, n in enumerate(names)}


def at(w, name, t):
    return float(np.interp(t, w["time"], w[name]))


def tmean(w, name, a, b, absolute=False):
    """Mean of a trace over [a, b] weighted by time. The solver's steps are 1 ns on an edge and up to
    200 ns between them, so a plain mean of the samples weights the edges."""
    t, x = w["time"], np.abs(w[name]) if absolute else w[name]
    inside = (t > a) & (t < b)
    tt = np.concatenate(([a], t[inside], [b]))
    xx = np.concatenate(([np.interp(a, t, x)], x[inside], [np.interp(b, t, x)]))
    return float(np.sum((xx[1:] + xx[:-1]) / 2 * np.diff(tt)) / (b - a))


def pad(i):
    return f"v(output_pad_{i}_)"


def read_word(w, t0, miso, ref):
    """The 16 bits on miso, each just before the falling edge after it was driven."""
    word = 0
    for b in range(15, -1, -1):
        ts = t0 + (22 - b) * T_SCLK - 50e-9
        word = (word << 1) | int(at(w, miso, ts) > at(w, ref, ts) / 2)
    return word


def check(w, order):
    """(ok, notes, quiet): quiet is False when a segment output pad rose above SPIKE_V."""
    t = w["time"]
    notes, ok = [], True
    for t0, addr, name, want, _ in FRAMES:
        word = read_word(w, t0, pad(0), "v(iovdd)")
        good = word == want
        ok &= good
        notes.append(f"read {name}: 0x{word:04X}, want 0x{want:04X}, {'pass' if good else 'FAIL'}")

    quiet = True
    for p in SEG_PADS:
        if p not in w:
            ok, quiet = False, False
            notes.append(f"{p[2:-5]} pad trace missing from the data, FAIL")
            continue
        k = int(np.argmax(w[p]))
        high = w[p] > SPIKE_V
        if np.any(high):
            quiet = False
            tb = t[high]
            notes.append(f"{p[2:-5]} pad rises to {w[p][k]:.2f} V at {t[k] * 1e6:.1f} us, above {SPIKE_V} V from "
                         f"{tb[0] * 1e6:.1f} to {tb[-1] * 1e6:.1f} us, IOVDD {at(w, 'v(iovdd)', t[k]):.2f} V, "
                         f"VDDA {at(w, 'v(vdda)', t[k]):.2f} V, VDD {at(w, 'v(vdd)', t[k]):.2f} V")
        else:
            notes.append(f"{p[2:-5]} pad stays below {SPIKE_V} V, highest {w[p][k]:.3f} V")

    for sup, src in SUPPLIES:
        if f"i({src})" not in w:
            ok = False
            notes.append(f"{sup} current trace missing from the data, FAIL")
            continue
        i = np.abs(w[f"i({src})"])
        k = int(np.argmax(i))
        end = tmean(w, f"i({src})", t[-1] - 20e-6, t[-1], absolute=True)
        longest, start = 0.0, None
        for j in range(len(t)):
            if i[j] > I_MAX and start is None:
                start = j
            elif i[j] <= I_MAX and start is not None:
                longest, start = max(longest, t[j] - t[start]), None
        good = longest <= T_SUSTAINED
        ok &= good
        notes.append(f"{sup} current: peak {i[k] * 1e3:.3f} mA at {t[k] * 1e6:.1f} us, longest above "
                     f"{I_MAX * 1e3:.0f} mA {longest * 1e9:.0f} ns, {end * 1e6:.2f} uA mean over the last 20 us, "
                     f"{'pass' if good else 'FAIL'}")
    return ok, notes, quiet


def crossings(x, thr):
    """How often x crosses thr."""
    above = x > thr
    return int(np.count_nonzero(above[1:] != above[:-1]))


def swing(x, base):
    """(highest, lowest) of x against its quiet mean."""
    return float(np.max(x) - base), float(np.min(x) - base)


def check_activity(w, win, notes):
    """True when the bounce's aggressors ran: dsm_clk and the do_q pads at their rate, miso toggling through the SPARE_14 read, the adc_conv pulse. A dead stimulus would report small swings."""
    t = w["time"]
    span = float(t[win][-1] - t[win][0])
    spare = BOUNCE_FRAMES[-1][0]
    reads = (t > spare) & (t < spare + 24 * T_SCLK)
    half = float(np.mean(w["v(iovdd_b)"][win])) / 2
    need = {"dsm_clk": ("v(dsm_clk_pad_b)", win, 2 * ACTIVITY * span / T_DSM),
            "do_q": ("v(do_q_pad_b)", win, ACTIVITY * span / T_DSM),
            "do_q_b": ("v(do_q_b_pad_b)", win, ACTIVITY * span / T_DSM),
            "miso in the SPARE_14 read": ("v(output_pad_0__b)", reads, MISO_EDGES_MIN),
            "adc_conv": ("v(output_pad_1__b)", win, 2)}
    ok = True
    for what, (name, sel, least) in need.items():
        if name not in w:
            ok = False
            notes.append(f"{what}: trace {name} missing from the data, FAIL")
            continue
        n = crossings(w[name][sel], half)
        good = n >= least
        ok &= good
        notes.append(f"stimulus ran, {what}: {n} edges, at least {least:.0f}, {'pass' if good else 'FAIL'}")
    return ok


def check_bounce(w):
    t = w["time"]
    notes, ok = [], True
    for t0, _, name, want, wdata in BOUNCE_FRAMES:
        if want is None:
            continue
        word = read_word(w, t0, "v(output_pad_0__b)", "v(iovdd_b)")
        good = word == want
        ok &= good
        notes.append(f"read {name} at {t0 * 1e6:.0f} us: 0x{word:04X}, want 0x{want:04X}, {'pass' if good else 'FAIL'}")

    win = (t > T_DSM_ON + 5e-6)
    base = (t > T_BASE[0]) & (t < T_BASE[1])
    ok &= check_activity(w, win, notes)
    s = {"t0": float(t[win][0]), "t1": float(t[win][-1])}
    for g in ("vss", "iovss", "paddle"):
        x = w[f"v({g})"][win]
        s[g] = float(x[np.argmax(np.abs(x))])
    for rail, hi, lo in (("io", "v(iovdd)", "v(iovss)"), ("core", "v(vdd)", "v(vss)"), ("seg", "v(vdda)", "v(vss)")):
        d = w[hi] - w[lo]
        b0 = float(np.mean(d[base]))
        s[rail + "_droop"], s[rail + "_over"] = b0 - float(np.min(d[win])), float(np.max(d[win])) - b0
    for sup in ("iovdd", "vdd", "vdda"):
        s["i_" + sup] = float(np.max(np.abs(w[f"i(lw_{sup})"][win])))
    s["i_iovss"] = float(np.max(np.abs(w["i(lw_iovss_0)"][win])))
    # the analog pins against their quiet level, on the die (padres side) and the pad
    for nm, net in (("vi", "v(xchip.vi)"), ("vcm", "v(xchip.vcm)"), ("ibias_test", "v(xchip.ibias_test)")):
        s[nm] = swing(w[net][win], float(np.mean(w[net][base])))
    # a core input that crosses its threshold more often than the host's pin did glitched
    glitches, margin = [], {}
    vss, vdd = w["v(vss)"][win], w["v(vdd)"][win]
    io = w["v(iovdd_b)"][win]
    for nm, net in CORE_INPUTS.items():
        x = w[f"v(xchip.{net})".lower()][win] - vss
        host = w[f"v({HOST_PINS[nm].lower()}_b)"][win]
        n_core, n_host = crossings(x, float(np.mean(vdd - vss)) / 2), crossings(host, float(np.mean(io)) / 2)
        if n_core != n_host:
            glitches.append(f"{nm} {n_core} against {n_host}")
        if n_host == 0:
            margin[nm] = float(np.max(np.abs(x - x[0])))
    s["glitches"], s["margin"] = glitches, margin
    ok &= not glitches
    notes.append(f"from {s['t0'] * 1e6:.0f} to {s['t1'] * 1e6:.0f} us: die VSS {s['vss'] * 1e3:+.0f} mV, IOVSS {s['iovss'] * 1e3:+.0f} mV, "
                 f"paddle {s['paddle'] * 1e3:+.0f} mV at the worst sample against the board ground")
    notes.append(f"rails on the die, droop and overshoot against the quiet level: IOVDD-IOVSS {s['io_droop'] * 1e3:.0f} and {s['io_over'] * 1e3:.0f} mV, "
                 f"VDD-VSS {s['core_droop'] * 1e3:.0f} and {s['core_over'] * 1e3:.0f} mV, VDDA-VSS {s['seg_droop'] * 1e3:.0f} and {s['seg_over'] * 1e3:.0f} mV")
    notes.append(f"peak currents in the wires: IOVDD {s['i_iovdd'] * 1e3:.1f} mA, VDD {s['i_vdd'] * 1e3:.2f} mA, VDDA {s['i_vdda'] * 1e3:.1f} mA, IOVSS downbond {s['i_iovss'] * 1e3:.1f} mA")
    for nm, label in (("vi", "vi"), ("vcm", "vcm"), ("ibias_test", "ibias_test")):
        hi, lo = s[nm]
        notes.append(f"{label} on the die: {hi * 1e3:+.1f} and {lo * 1e3:+.1f} mV against its quiet level, {(hi - lo) * 1e3:.1f} mV peak to peak")
    notes.append(f"static core inputs move up to {max(margin.values()) * 1e3 if margin else 0:.0f} mV; "
                 + (f"glitches: {', '.join(glitches)}, FAIL" if glitches else "no core input glitches, pass"))
    return ok, notes, s


def power_means(w, order, need=("IOVDD", "VDD", "VDDA")):
    """{supply: (mean, mean of the window's first half, mean of the second)} of the delivered current over the last P_WINDOW.
    A supply in need whose current is not in the data is an error, v1.1.1 has no VDDA and passes need without it."""
    missing = [sup for sup, src in SUPPLIES if sup in need and f"i({src})" not in w]
    if missing:
        raise SystemExit(f"{order}: the current of {', '.join(missing)} is not in the data")
    t1 = float(w["time"][-1])
    t0, tm = t1 - P_WINDOW, t1 - P_WINDOW / 2
    return {sup: (-tmean(w, f"i({src})", t0, t1), -tmean(w, f"i({src})", t0, tm), -tmean(w, f"i({src})", tm, t1))
            for sup, src in SUPPLIES if f"i({src})" in w}


def resolution(m):
    """The least current change this run can resolve: the two halves of the window disagree by this much."""
    mean, a, b = m
    return max(abs(a - b), RES_REL * abs(mean), RES_ABS)


def check_power(w, order):
    m = power_means(w, order)
    notes = []
    for sup, v in m.items():
        notes.append(f"{sup} current: {v[0] * 1e9:.2f} nA mean over the last {P_WINDOW * 1e6:.1f} us, halves {v[1] * 1e9:.2f} and {v[2] * 1e9:.2f} nA")
    return True, notes, m


def power_isolation(a, b):
    """(ok, notes) of the dsm2 off against dsm2 running on VDD."""
    d = b["VDD"][0] - a["VDD"][0]
    res = max(resolution(a["VDD"]), resolution(b["VDD"]))
    good = abs(d) <= res
    notes = [f"VDD current with dsm2 off {a['VDD'][0] * 1e9:.2f} nA, with dsm_clk at 1.024 MHz and the do_q pads switching {b['VDD'][0] * 1e9:.2f} nA, "
             f"difference {d * 1e9:+.3f} nA, resolution {res * 1e9:.3f} nA, {'equal within the resolution, pass' if good else 'DIFFERENT, FAIL'}"]
    if "VDDA" in a and "VDDA" in b:
        notes.append(f"VDDA current {a['VDDA'][0] * 1e9:.2f} nA with dsm2 off, {b['VDDA'][0] * 1e9:.2f} nA running")
        notes.append(f"IOVDD current {a['IOVDD'][0] * 1e9:.2f} nA with dsm2 off, {b['IOVDD'][0] * 1e6:.2f} uA running, the do_q pads' output stages")
    return good, notes


def compare_v111(this, old):
    """Lines comparing the settled currents of the DSA1 state on this layout with the v1.1.1 file."""
    notes = []
    vdd = this["VDD"][0] + this.get("VDDA", (0,))[0]
    for label, mine, then in (("IOVDD", this["IOVDD"][0], old["iovdd"]), ("VDD", this["VDD"][0], old["vdd"]),
                              ("VDD + VDDA", vdd, old["vdd"])):
        d = mine / then - 1
        notes.append(f"{label}: {mine * 1e9:.2f} nA here, {then * 1e9:.2f} nA on {old['tag']}, {d * 100:+.1f} %"
                     + (", within 1 %" if abs(d) <= 0.01 else ", over 1 %"))
    inv = old.get("inventory", {})
    if inv:
        mine = this_inventory(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..")))
        diff = {k: (mine.get(k, 0), inv.get(k, 0)) for k in sorted(set(mine) | set(inv)) if mine.get(k, 0) != inv.get(k, 0)}
        notes.append("IO cells that differ (here, " + old["tag"] + "): " + ", ".join(f"{k} {a} against {b}" for k, (a, b) in diff.items()))
        notes.append("the settled current is the pads' leakage plus the switching of the two toggling inputs, so it follows that population")
        leak = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../verification/startup/cell_leakage.md")
        if os.path.exists(leak):
            notes += ["static current predicted from the cells' DC runs (cell_leakage.md), " + ln[2:] for ln in open(leak).read().splitlines() if ln.startswith("- ")]
    return notes


V111_CORE_UW = 3.061                # typical total of the core on v1.1.1, doc/specifications.md
CORE_TOL = 0.02


def core_power(report):
    """(ok, note) of the macro's gate-level VCD power, the typical corner's total, against v1.1.1's."""
    for line in open(report):
        f = line.split()
        if f and f[0] == "Total":
            uw = float(f[4]) * 1e6
            d = uw / V111_CORE_UW - 1
            good = abs(d) <= CORE_TOL
            return good, (f"core power from the gate-level VCD, typical corner: {uw:.3f} uW, {V111_CORE_UW} uW on v1.1.1, {d * 100:+.2f} %, "
                          f"{'within' if good else 'OVER'} {CORE_TOL * 100:.0f} %, {'pass' if good else 'FAIL'}")
    raise SystemExit(f"{report} has no Total line")


def this_inventory(root):
    """IO cell counts of a tree's chip netlist."""
    import re
    text = open(os.path.join(root, "netlist/pnl/sg13cmos5l_dsa1_dig_top.pnl.v")).read()
    inv = {}
    for m in re.finditer(r"^ (sg13cmos5l_(?:IOPad\w+|ip__clamp_vddvss|ip__cut_vdd)) ", text, flags=re.M):
        inv[m.group(1)] = inv.get(m.group(1), 0) + 1
    return inv


def plot_bounce(w, s, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t0 = BOUNCE_FRAMES[-1][0]
    sel = (w["time"] > T_DSM_ON - 5e-6)
    us = w["time"][sel] * 1e6
    fig, axes = plt.subplots(4, 1, figsize=(9, 10), sharex=True)
    for g in ("vss", "iovss", "paddle"):
        axes[0].plot(us, w[f"v({g})"][sel] * 1e3, lw=0.7, label=g.upper())
    axes[0].set(ylabel="vs board ground (mV)")
    axes[0].legend(fontsize=7)
    for lbl, hi, lo in (("IOVDD-IOVSS", "v(iovdd)", "v(iovss)"), ("VDD-VSS", "v(vdd)", "v(vss)"), ("VDDA-VSS", "v(vdda)", "v(vss)")):
        d = (w[hi] - w[lo])[sel]
        axes[1].plot(us, (d - d[0]) * 1e3, lw=0.7, label=lbl)
    axes[1].set(ylabel="die rail change (mV)")
    axes[1].legend(fontsize=7)
    for net, lbl in (("v(xchip.vi)", "vi"), ("v(xchip.vcm)", "vcm"), ("v(xchip.ibias_test)", "ibias_test")):
        x = w[net][sel]
        axes[2].plot(us, (x - x[0]) * 1e3, lw=0.7, label=lbl)
    axes[2].set(ylabel="analog pins on the die (mV)")
    axes[2].legend(fontsize=7)
    for nm in ("sclk", "rst_n", "ss", "mosi"):
        axes[3].plot(us, (w[f"v(xchip.{CORE_INPUTS[nm]})".lower()] - w["v(vss)"])[sel], lw=0.7, label=nm)
    axes[3].set(ylabel="core inputs vs die VSS (V)", xlabel="time (us)")
    axes[3].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out, dpi=120)


def plot(waves, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(4, len(waves), figsize=(6 * len(waves), 9), sharex=True, squeeze=False)
    for col, (order, w) in enumerate(waves.items()):
        us = w["time"] * 1e6
        a = axes[:, col]
        a[0].plot(us, w["v(iovdd)"], label="IOVDD")
        a[0].plot(us, w["v(vdd)"], label="VDD")
        a[0].plot(us, w["v(vdda)"], label="VDDA")
        a[0].plot(us, w["v(rst_n_pad)"], "--", label="rst_n pad")
        a[0].set(title=order.replace("_", " "), ylabel="V")
        a[0].legend(fontsize=7)
        for lbl, src in (("IOVDD", "viovdd"), ("VDD", "vvdd"), ("VDDA", "vvdda")):
            a[1].plot(us, np.abs(w[f"i({src})"]) * 1e3, label=lbl)
        a[1].set(ylabel="|I| (mA)", yscale="log")
        a[1].legend(fontsize=7)
        for p in SEG_PADS:
            a[2].plot(us, w[p], label=p[2:-5])
        a[2].set(ylabel="dsm2 output pads (V)")
        a[2].legend(fontsize=7)
        a[3].plot(us, w[pad(0)], label="miso")
        a[3].plot(us, w["v(input_pad_3_)"], label="ss", alpha=0.6)
        a[3].set(ylabel="V", xlabel="time (us)")
        a[3].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out, dpi=120)


def synth(order="core_first", spike=False, i_vdd=15e-6):
    """A wave set that passes, for the self-test."""
    t = np.linspace(0, 520e-6, 52001)
    io = np.clip((t - 10e-6) / 100e-6, 0, 1) * 3.3
    w = {"time": t, "v(iovdd)": io, "v(vdd)": io / 3.3 * 1.2, "v(vdda)": io / 3.3 * 1.5, "v(rst_n_pad)": io * (t > 300e-6),
         "i(viovdd)": -1e-6 * np.ones_like(t), "i(vvdd)": -i_vdd * np.ones_like(t), "i(vvdda)": -2e-6 * np.ones_like(t),
         "v(input_pad_3_)": io, "v(do_q_pad)": np.zeros_like(t), "v(do_q_b_pad)": np.zeros_like(t)}
    for i in range(2):
        w[pad(i)] = np.zeros_like(t)
    miso = np.zeros_like(t)
    for t0, _, _, want, _ in FRAMES:
        for b in range(16):
            if want >> b & 1:
                tb = t0 + (22 - b) * T_SCLK
                miso[(t > tb - T_SCLK) & (t < tb)] = 3.3
    w[pad(0)] = miso
    if spike:
        w["v(do_q_pad)"] = 1.5 * np.exp(-((t - 60e-6) / 20e-6) ** 2)
    return w


def self_test():
    import tempfile
    w = synth()
    ok, notes, quiet = check(w, "x")
    assert ok and quiet and any("do_q pad stays below" in n for n in notes), notes
    # IOVDD first: the do_q pad rises while VDDA is low, reported, not a failure of the run itself
    ok, notes, quiet = check(synth(spike=True), "x")
    assert ok and not quiet and any("do_q pad rises to 1.50 V at 60.0 us" in n and "VDDA 0.75 V" in n for n in notes), notes
    bad = dict(w)
    bad["i(viovdd)"] = w["i(viovdd)"].copy()
    bad["i(viovdd)"][1000] = -0.05                        # one sample, an edge: reported, passes
    ok, notes, _ = check(bad, "x")
    assert ok and any("IOVDD current: peak 50.000 mA" in n for n in notes), notes
    bad["i(viovdd)"][1000:1150] = -0.05                   # 1.5 us: sustained, fails
    ok, notes, _ = check(bad, "x")
    assert not ok, notes
    # missing traces fail, they do not pass vacuously
    bad = {k: v for k, v in w.items() if k != "v(do_q_pad)"}
    ok, notes, quiet = check(bad, "x")
    assert not ok and not quiet and any("do_q pad trace missing" in n for n in notes), notes
    bad = {k: v for k, v in w.items() if k != "i(vvdda)"}
    ok, notes, _ = check(bad, "x")
    assert not ok and any("VDDA current trace missing" in n for n in notes), notes
    try:
        power_means(bad, "power_dsa1")
        raise AssertionError("a missing VDDA current must stop the power check")
    except SystemExit as e:
        assert "VDDA" in str(e), e
    assert power_means(bad, "power_dsa1", need=("IOVDD", "VDD")).keys() == {"IOVDD", "VDD"}
    bad = dict(w)
    bad["i(vvdda)"] = w["i(vvdda)"].copy()
    bad["i(vvdda)"][20000:20400] = -0.05                  # the VDDA wire is watched too
    ok, notes, _ = check(bad, "x")
    assert not ok and any(n.startswith("VDDA current") and "FAIL" in n for n in notes), notes
    bad = dict(w)
    bad[pad(0)] = np.zeros_like(w["time"])
    ok, notes, _ = check(bad, "x")
    assert not ok and any("read CHIP_ID: 0x0000" in n for n in notes), notes
    # bounce: miso toggling as read, the analog pins moving, then a glitch on rst_n that its host pin does not have
    t = np.linspace(0, 520e-6, 104001)
    one = np.ones_like(t)
    w = {"time": t, "v(iovdd_b)": 3.3 * one, "v(iovdd)": 3.3 * one, "v(vdd)": 1.2 * one, "v(vdda)": 1.5 * one}
    for n in ("vss", "iovss", "paddle"):
        w[f"v({n})"] = 0 * one
    for n in ("iovdd", "vdd", "vdda", "iovss_0"):
        w[f"i(lw_{n})"] = 0 * one
    w["v(xchip.vi)"] = 0.75 * one + 0.002 * np.sin(2 * np.pi * 1.024e6 * t) * (t > T_DSM_ON)
    w["v(xchip.vcm)"], w["v(xchip.ibias_test)"] = 0.75 * one, 0 * one
    miso = np.zeros_like(t)
    for t0, _, _, want, _ in BOUNCE_FRAMES:
        for b in range(16 if want is not None else 0):
            if want >> b & 1:
                tb = t0 + (22 - b) * T_SCLK
                miso[(t > tb - T_SCLK) & (t < tb)] = 3.3
    w["v(output_pad_0__b)"] = miso
    ph = lambda per, lag=0: 3.3 * ((t > T_DSM_ON) & (((t - T_DSM_ON - lag) / per) % 1 < 0.5))
    w["v(dsm_clk_pad_b)"], w["v(do_q_pad_b)"], w["v(do_q_b_pad_b)"] = ph(T_DSM), ph(2 * T_DSM), ph(2 * T_DSM, T_DSM)
    w["v(output_pad_1__b)"] = 3.3 * ((t > 456e-6) & (t < 471e-6))
    for nm, net in CORE_INPUTS.items():
        w[f"v(xchip.{net})".lower()] = 1.2 * one if nm == "rst_n" else 0 * one
        w[f"v({HOST_PINS[nm].lower()}_b)"] = 3.3 * one if nm == "rst_n" else 0 * one
    ok, notes, s = check_bounce(w)
    with tempfile.TemporaryDirectory() as d:
        plot_bounce(w, s, os.path.join(d, "b.png"))
        plot({"io_first": synth(), "core_first": synth()}, os.path.join(d, "s.png"))
        assert os.path.getsize(os.path.join(d, "b.png")) > 5000 and os.path.getsize(os.path.join(d, "s.png")) > 5000
    assert ok and abs(s["vi"][0] - 0.002) < 1e-4 and abs(s["vi"][1] + 0.002) < 1e-4 and s["seg_droop"] == 0, (notes, s)
    assert any("vi on the die: +2.0 and -2.0 mV" in n for n in notes), notes
    bad = dict(w)
    bad["v(xchip.i_sg13cmos5l_dsa1_dig_core_rst_n)"] = w["v(xchip.i_sg13cmos5l_dsa1_dig_core_rst_n)"].copy()
    bad["v(xchip.i_sg13cmos5l_dsa1_dig_core_rst_n)"][(t > 400e-6) & (t < 400.02e-6)] = 0.2
    ok, notes, _ = check_bounce(bad)
    assert not ok and any("rst_n 2 against 0" in n for n in notes), notes
    bad = dict(w)
    bad["v(output_pad_0__b)"] = np.zeros_like(t)
    ok, notes, _ = check_bounce(bad)
    assert not ok and any("read SPARE_14 at 450 us: 0x0000" in n for n in notes), notes
    assert any("stimulus ran, miso in the SPARE_14 read: 0 edges" in n and "FAIL" in n for n in notes), notes
    # a dead stimulus fails, each aggressor alone, and a missing trace fails too
    for tr, what in (("v(dsm_clk_pad_b)", "dsm_clk"), ("v(do_q_pad_b)", "do_q"), ("v(do_q_b_pad_b)", "do_q_b"), ("v(output_pad_1__b)", "adc_conv")):
        bad = dict(w)
        bad[tr] = np.zeros_like(t)
        ok, notes, _ = check_bounce(bad)
        assert not ok and any(f"stimulus ran, {what}: 0 edges" in n for n in notes), (what, notes)
    bad = dict(w)
    del bad["v(do_q_pad_b)"]
    ok, notes, _ = check_bounce(bad)
    assert not ok and any("trace v(do_q_pad_b) missing" in n for n in notes), notes
    # half the do_q edges is still a dead pad
    bad = dict(w)
    bad["v(do_q_pad_b)"] = np.where(t < 400e-6, w["v(do_q_pad_b)"], 0.0)
    ok, notes, _ = check_bounce(bad)
    assert not ok, notes
    # power: the same current with the dsm2 running passes, a rise of 1 % of VDD's current does not
    a = check_power(synth(i_vdd=15e-6), "power_dsa1")[2]
    b = check_power(synth(i_vdd=15e-6 * 1.0004), "power_dsm")[2]
    ok, notes = power_isolation(a, b)
    assert ok and "equal within the resolution" in notes[0], notes
    b = check_power(synth(i_vdd=15e-6 * 1.01), "power_dsm")[2]
    ok, notes = power_isolation(a, b)
    assert not ok and "DIFFERENT" in notes[0], notes
    # dense samples on a short spike must not weigh more than their time: 1 uA for 1 us of 10, 1000 samples inside it
    tt = np.concatenate((np.linspace(0, 9e-6, 10), np.linspace(9e-6, 10e-6, 1000)[1:]))
    xx = np.where(tt > 9e-6, 1e-6, 0.0)
    assert abs(tmean({"time": tt, "x": xx}, "x", 0, 10e-6) - 1e-7) < 1e-8 and np.mean(xx) > 0.9e-6
    # a ripple that the window's halves disagree about widens the resolution
    r = synth(i_vdd=15e-6)
    r["i(vvdd)"] = r["i(vvdd)"] * (1 + 0.05 * (r["time"] > 520e-6 - P_WINDOW / 2))
    m = check_power(r, "power_dsa1")[2]
    assert resolution(m["VDD"]) > 0.02 * 15e-6, m
    notes = compare_v111({"IOVDD": (47e-9, 0, 0), "VDD": (10e-9, 0, 0), "VDDA": (5e-9, 0, 0)}, {"tag": "t", "iovdd": 47.2e-9, "vdd": 20e-9})
    assert notes[0] == "IOVDD: 47.00 nA here, 47.20 nA on t, -0.4 %, within 1 %", notes
    assert notes[1] == "VDD: 10.00 nA here, 20.00 nA on t, -50.0 %, over 1 %", notes
    assert notes[2] == "VDD + VDDA: 15.00 nA here, 20.00 nA on t, -25.0 %, over 1 %", notes
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "p.rpt"), "w").write("Sequential 1 2 3 4 35.6%\nTotal 1.1e-06 7.3e-07 1.1e-06 3.074653e-06 100.0%\n")
        ok, note = core_power(os.path.join(d, "p.rpt"))
        assert ok and "3.075 uW" in note and "+0.45 %" in note, note
        open(os.path.join(d, "p.rpt"), "w").write("Total 1.1e-06 7.3e-07 1.1e-06 3.2e-06 100.0%\n")
        ok, note = core_power(os.path.join(d, "p.rpt"))
        assert not ok and "OVER" in note, note
    print("OK: startup_check self-test")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("waves", nargs="*", help="the wrdata file of each order given, in ORDERS' order")
    ap.add_argument("--orders", default=",".join(ORDERS), help="the orders the files are of, default all")
    ap.add_argument("--v111", help="settled currents of the v1.1.1 layout, as --export-power writes them")
    ap.add_argument("--export-power", nargs=3, metavar=("TREE", "TAG", "JSON"), help="write the DSA1 state currents of the power_dsa1 file "
                    "given, for the chip netlist of TREE called TAG, to JSON and stop")
    ap.add_argument("--out", default="verification/startup")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if a.export_power:
        tree, tag, dest = a.export_power
        m = power_means(load(a.waves[0]), "power_dsa1", need=("IOVDD", "VDD"))
        json.dump({"tag": tag, "iovdd": m["IOVDD"][0], "vdd": m["VDD"][0], "inventory": this_inventory(tree)}, open(dest, "w"), indent=1)
        return 0
    os.makedirs(a.out, exist_ok=True)
    waves = dict(zip(a.orders.split(","), (load(p) for p in a.waves)))
    lines, all_ok, power = ["# Supply start-up bench", ""], True, {}
    for (order, w), path in zip(waves.items(), a.waves):
        quiet = True
        if order == "bounce":
            ok, notes, stats = check_bounce(w)
            plot_bounce(w, stats, os.path.join(a.out, "bounce.png"))
        elif order in POWER_ORDERS:
            ok, notes, power[order] = check_power(w, order)
        else:
            ok, notes, quiet = check(w, order)
        if order == REQUIRED:
            ok &= quiet
        elif not quiet:
            notes.append(f"so the board must bring VDD and VDDA up no later than IOVDD, the order {REQUIRED.replace('_', ' ')}")
        c = os.path.join(os.path.dirname(path), f"solver_{order}.txt")
        if os.path.exists(c):
            notes.append(f"solver settings: {open(c).read().strip()}")
        all_ok &= ok
        lines += [f"## {order.replace('_', ' ')}", ""] + [f"- {n}" for n in notes] + [""]
    if power and len(power) != 2:
        raise SystemExit("the power orders come as a pair, power_dsa1 and power_dsm, for the VDD isolation check")
    if len(power) == 2:
        ok, notes = power_isolation(power["power_dsa1"], power["power_dsm"])
        all_ok &= ok
        lines += ["## VDD isolation", ""] + [f"- {n}" for n in notes] + [""]
    if "power_dsa1" in power and a.v111:
        lines += ["## DSA1 state against v1.1.1", ""] + [f"- {n}" for n in compare_v111(power["power_dsa1"], json.load(open(a.v111)))] + [""]
    rpt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../macros/dsa1_dig/verification/power_vcd_nom_typ_1p20V_25C.rpt")
    if power and not os.path.exists(rpt):
        raise SystemExit(f"{rpt} is missing, run make -C macros/dsa1_dig power-vcd")
    if power:
        ok, note = core_power(rpt)
        all_ok &= ok
        lines += ["## Core power", "", f"- {note}", "- the macro's own `make -C macros/dsa1_dig power-vcd`, the XSPICE core in this bench draws nothing", ""]
    lines.append("PASS" if all_ok else "FAIL")
    text = "\n".join(lines) + "\n"
    open(os.path.join(a.out, "startup_report.md"), "w").write(text)
    startup = {k: v for k, v in waves.items() if k in ("io_first", "core_first")}
    if startup:
        plot(startup, os.path.join(a.out, "startup.png"))
    print(text)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
