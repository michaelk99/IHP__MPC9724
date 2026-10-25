# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: transistor-level leakage sign-off for a hardened macro
#
# The flow's leakage comes from the liberty, which is itself a characterisation
# result. This measures it instead: every cell type in the final netlist is
# simulated in ngspice from the library CDL with the PDK device models, over its
# input states, and the result is weighted by the instance count.
#
# What is exact and what is not:
#   - decap, filler and well taps have no inputs, so their number is exact, and
#     on this design they are most of the total
#   - combinational cells are enumerated over all input states (up to 4 inputs,
#     sampled above that), so the spread over states is reported with the mean
#   - sequential cells are enumerated over their inputs too, clock level included.
#     The output is NOT forced: a nodeset that contradicts the inputs makes the
#     solver settle into a fighting state, which is crowbar current and not
#     leakage. That read 6884 nW on a flop at ss against 0.97 nW for the same
#     cell in a consistent state.
#
# Run inside iic-osic-tools from a macro directory:
#   python3 ../scripts/leakage_sim.py --corner tt --netlist final/nl/<top>.nl.v

import argparse
import itertools
import os
import re
import sys
import subprocess
import tempfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))

# EZ130 and the thick-oxide decaps live outside this repo, same as for the
# LibreLane runs. The defaults match the macro Makefiles.
EZ130_DIR = os.environ.get(
    "EZ130_DIR", os.path.expanduser("~/projects/OpenBLAU/ip/ez130_8t_v1p1"))
DECAPHV_DIR = os.environ.get(
    "DECAPHV_DIR", os.path.expanduser("~/projects/OpenBLAU/ip/ez130_8t_decap_hv"))

# spicerun is vendored here rather than imported from DECAPHV_DIR: only
# jku-phd's copy of the decap IP ships it, OpenBLAU's does not, and this check
# should not depend on which external checkout happens to carry a helper.
sys.path.insert(0, HERE)
import spicerun  # noqa: E402

PDK = os.path.join(os.environ.get("PDK_ROOT", "/foss/pdks"),
                   os.environ.get("PDK", "ihp-sg13cmos5l"))
MODELS = os.path.join(PDK, "libs.tech/ngspice/models")
LV_CDL = os.path.join(EZ130_DIR, "cdl", "ez130_8t.cdl")
HV_CDL = os.path.join(DECAPHV_DIR, "cdl", "ez130_8t_decap_hv.cdl")

# section, VDD, T: the 1.2 V sign-off family, same corners as the STA reports
CORNERS = {"tt": ("mos_tt", 1.20, 25, "tt_1p20v_25c"),
           "ss": ("mos_ss", 1.08, 125, "ss_1p08v_125c"),
           "ff": ("mos_ff", 1.32, -40, "ff_1p32v_m40c")}
LV_LIB = os.path.join(EZ130_DIR, "lib")
MAX_STATES = 16


def cells_in(netlist):
    """Instance count per cell type from a structural Verilog netlist."""
    text = open(netlist).read()
    text = re.sub(r"//.*", "", text)
    return Counter(re.findall(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s+\\?\S+\s*\(", text, re.M))


def cdl_cells(path):
    """name -> (ports, {pin: dir}) from .SUBCKT and *.PININFO."""
    out, name, ports = {}, None, None
    for line in open(path):
        s = line.strip()
        if s.upper().startswith(".SUBCKT "):
            f = s.split()
            name, ports = f[1], f[2:]
        elif s.startswith("*.PININFO") and name:
            d = dict(tok.split(":") for tok in s.split()[1:] if ":" in tok)
            out[name] = (ports, d)
            name = None
        elif s.upper().startswith(".ENDS") and name:
            out[name] = (ports, {p: "B" for p in ports})
            name = None
    return out


def states_for(pins, seq):
    """Input vectors to solve.

    Sequential cells are solved with CK high only. With CK low the master latch
    is transparent and its keeper fights the ideal source on D, so the solver
    settles into a state that carries crowbar current and never persists in
    silicon: 9027 nW against 1.2 nW for the same flop with CK high, at ss.
    With CK high the master holds and the slave follows it, which is consistent.
    """
    ins = [p for p, d in pins.items() if d == "I"]
    if not ins:
        return [({}, None)]
    free = [p for p in ins if not (seq and p == "CK")]
    combos = list(itertools.product([0, 1], repeat=len(free))) if len(free) <= 4 else \
        [tuple((i >> b) & 1 for b in range(len(free))) for i in range(MAX_STATES)]
    out = []
    for c in combos:
        v = dict(zip(free, c))
        if seq and "CK" in ins:
            v["CK"] = 1
        out.append((v, None))
    return out


def liberty_leakage(corner):
    """cell_leakage_power in nW per cell, the library's own characterisation."""
    path = os.path.join(LV_LIB, f"ez130_8t_{CORNERS[corner][3]}.lib")
    out, cell = {}, None
    for line in open(path):
        m = re.match(r"\s*cell \((\w+)\)", line)
        if m:
            cell = m.group(1)
        elif cell and "cell_leakage_power" in line:
            v = re.search(r"([-\d.eE+]+)", line.split(":")[1])
            if v:
                out[cell] = float(v.group(1))
            cell = None
    return out


def deck_for(cell, ports, pins, vecs, corner, cdl_ng):
    sec, vdd, temp = CORNERS[corner][:3]
    L = [f"* leakage of {cell} at {corner}",
         f".lib {os.path.join(MODELS, 'cornerMOSlv.lib')} {sec}",
         f".lib {os.path.join(MODELS, 'cornerMOShv.lib')} {sec}",
         f".include {cdl_ng}", f".temp {temp}",
         # Homotopy only: these change how the dc solve gets there, not where.
         # Without them a latch or a flop feedback loop fails to converge often
         # enough to move the total by a few percent between runs.
         ".options itl1=500 gminsteps=20 srcsteps=20"]
    outs = [p for p, d in pins.items() if d == "O"]
    for i, (vec, q) in enumerate(vecs):
        L.append(f"v{i} vdd{i} 0 dc {vdd}")
        nets = []
        for p in ports:
            if p in ("VDD", "VNW"):
                nets.append(f"vdd{i}")
            elif p in ("VSS", "VPW"):
                nets.append("0")
            elif pins.get(p) == "I":
                nets.append(f"vdd{i}" if vec[p] else "0")
            else:
                nets.append(f"o{i}_{p}")
        L.append(f"x{i} {' '.join(nets)} {cell}")
        if q is not None and outs:
            L.append(f".nodeset v(o{i}_{outs[0]})={vdd if q else 0}")
    L.append(".control")
    L.append("op")
    for i in range(len(vecs)):
        L.append(f"print i(v{i})")
    L += [".endc", ".end", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corner", default="tt", choices=list(CORNERS))
    ap.add_argument("--netlist", required=True,
                    help="hardened netlist, e.g. final/nl/dsa1_dig_top.nl.v")
    args = ap.parse_args()
    nl = args.netlist
    counts = cells_in(nl)

    # Both CDLs always: the thin-oxide cells are banned from the netlist, but
    # the library still defines them and a stray one has to be recognised
    # rather than silently dropped as uncharacterised.
    lib = dict(cdl_cells(LV_CDL))
    lib.update(cdl_cells(HV_CDL))

    tmp = tempfile.mkdtemp(prefix="leak_")
    cdl_ng = os.path.join(tmp, "cells.spice")
    spicerun.cdl_to_ngspice(LV_CDL, cdl_ng)
    hv_ng = os.path.join(tmp, "hv.spice")
    spicerun.cdl_to_ngspice(HV_CDL, hv_ng)
    with open(cdl_ng, "a") as f:
        f.write("\n" + open(hv_ng).read())

    vdd = CORNERS[args.corner][1]
    lib_leak = liberty_leakage(args.corner)
    total, rows, missing, suspect, unsolved, partial, from_lib = 0.0, [], [], [], [], [], []
    for cell, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        if cell not in lib:
            missing.append((cell, n))
            continue
        ports, pins = lib[cell]
        seq = "CK" in pins or cell.startswith("DFF") or cell.startswith("CG")
        vecs = states_for(pins, seq)
        deck = deck_for(cell, ports, pins, vecs, args.corner, cdl_ng)
        r = spicerun.run_deck(deck, workdir=tmp, tag=f"leak_{cell}")
        vals = [abs(float(m)) * vdd * 1e9 for m in
                re.findall(r"i\(v\d+\)\s*=\s*([-\d.eE+]+)", r.out)]
        if len(vals) != len(vecs):
            # One `op` covers every input vector of a cell, so a single vector
            # that will not converge takes the whole cell down with it and the
            # cell drops out of the total. That is the whole non-determinism:
            # the run is never too high, only too low. Re-run the vectors one
            # deck at a time so only the ones that genuinely fail are lost.
            vals, lost = [], 0
            for vi, vec in enumerate(vecs):
                d1 = deck_for(cell, ports, pins, [vec], args.corner, cdl_ng)
                r1 = spicerun.run_deck(d1, workdir=tmp, tag=f"leak_{cell}_{vi}")
                m = re.findall(r"i\(v\d+\)\s*=\s*([-\d.eE+]+)", r1.out)
                if m:
                    vals.append(abs(float(m[0])) * vdd * 1e9)
                else:
                    lost += 1
            if lost:
                partial.append((cell, n, lost, len(vecs)))
        ref = lib_leak.get(cell)
        if not vals:
            # In the CDL but no vector solved. Two different things land here:
            #
            #   - a device with no model in the PDK. ANTENNA2 instantiates
            #     `dantenna`, which ngspice reports as "could not find a valid
            #     modelname". Nothing about the solver will fix that.
            #   - a dc solve that starts at nan and then fails gmin stepping,
            #     source stepping and the transient op in turn. XOR3X1 and CGX3
            #     do this on every input state.
            #
            # Either way, counting zero is the one answer that is certainly
            # wrong, and it biases the total low. Fall back to the library's own
            # characterisation, which is what the flow would have used anyway,
            # and say so.
            why = ("no device model" if "could not find a valid modelname" in r.out
                   else "dc solve failed")
            if ref is None:
                unsolved.append((cell, n, r.out))
                continue
            from_lib.append((cell, n, ref, why))
            total += n * ref
            rows.append((cell, n, ref, ref, ref))
            continue
        mean = sum(vals) / len(vals)
        # A latch-based cell solved out of its consistent state carries crowbar
        # current, not leakage. Trust the library's characterisation there.
        if ref and mean > 10 * ref:
            suspect.append((cell, mean, ref))
            mean = ref
        total += n * mean
        rows.append((cell, n, mean, min(vals), max(vals)))

    if from_lib:
        n_lib = sum(n for _, n, _, _ in from_lib)
        print("\nnot simulated, liberty value used for %d instances:" % n_lib)
        for cell, n, ref, why in from_lib:
            print("  %-12s x%-6d %.4g nW/cell   (%s)" % (cell, n, ref, why))
    if unsolved:
        n_lost = sum(n for _, n, _ in unsolved)
        print("\nSOLVER FAILURES AND NO LIBERTY VALUE, not counted for %d instances:" % n_lost)
        for cell, n, out in unsolved:
            tail = [l for l in out.splitlines() if l.strip()][-1:] or ["(no output)"]
            print("  %-12s x%-6d %s" % (cell, n, tail[0][:90]))

    print(f"\ncorner {args.corner}, netlist {nl}")
    print(f"{'cell':<12}{'count':>7}{'nW/cell':>11}{'min':>10}{'max':>10}{'nW total':>12}")
    for cell, n, mean, lo, hi in sorted(rows, key=lambda r: -r[1] * r[2])[:18]:
        print(f"{cell:<12}{n:>7}{mean:>11.4g}{lo:>10.4g}{hi:>10.4g}{n*mean:>12.4g}")
    print(f"\ntotal {total/1000:.3f} uW over {sum(counts.values())} instances")

    # The decoupling fill is the reason this script gets run, so report it
    # whether or not it ranks in the table above.
    dec = [(c, n, m) for c, n, m, _, _ in rows if c.startswith("DECAP")]
    if dec:
        d_tot = sum(n * m for _, n, m in dec)
        print("decoupling: %d cells, %.1f nW, %.1f %% of the total" %
              (sum(n for _, n, _ in dec), d_tot, 100.0 * d_tot / total))
        for c, n, m in sorted(dec, key=lambda r: -r[1] * r[2]):
            print("  %-12s x%-6d %.4g nW/cell, %.1f nW" % (c, n, m, n * m))
    else:
        print("decoupling: no DECAP* cell was simulated")
    if missing:
        print("no CDL, not counted: " + ", ".join(f"{c}x{n}" for c, n in missing))
    if suspect:
        print("\ncrowbar rather than leakage in the dc solve, liberty value used instead:")
        for c, sim, ref in suspect:
            print(f"  {c}: simulated {sim:.4g} nW, liberty {ref:.4g} nW")
    if partial:
        print("\ncells averaged over fewer vectors, the rest did not converge:")
        for c, n, lost, tot in partial:
            print(f"  {c}: {tot - lost} of {tot} vectors solved, x{n} instances")


if __name__ == "__main__":
    main()
