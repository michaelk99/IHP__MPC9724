# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Ported from OpenBLAU 8f25e634, scripts/spicerun.py
# Description: shared ngspice / xschem plumbing for every SPICE study in the repo
#
# Almost every analog study here is the same three steps: build a deck as text,
# run `ngspice -b` on it, and scrape the `.meas` results out of the batch log.
# That loop used to be re-implemented in each of the nine study scripts, with
# the number regex drifting four different ways between them -- so a deck that
# printed `1.5E-09` was read by some and silently dropped by others. It lives
# here now (see AGENTS.md "Folder structure": tooling used by more than one
# macro belongs to the repo-root scripts/).
#
# Import it from a macro script with the repo root on sys.path, e.g. from
# macros/<macro>/scripts/:
#
#     import os, sys
#     sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
#                                     "..", "..", "..", "scripts"))
#     import spicerun
#
# What it does NOT do: interpret results. Each study keeps its own domain logic
# (which measurement means what, which corner to sweep, when a cell has failed).
# Only "get a deck simulated and its printed numbers back" is shared.

import os
import re
import shutil
import subprocess
import tempfile
from collections import namedtuple

# The container puts both tools on PATH; the absolute path is the fallback for
# an environment that has the tools installed but not exported (the tspc_dff
# characterization runs with a stripped PATH, see char_tspc_dff.py).
NGSPICE = shutil.which("ngspice") or "/foss/tools/bin/ngspice"
XSCHEM = shutil.which("xschem") or "/foss/tools/bin/xschem"

# out     stdout and stderr together: ngspice splits its diagnostics across both
#         and every study wants to see all of them
# deck    where the deck was written (inside a temporary dir unless `workdir`
#         was given, in which case it survives the call)
Run = namedtuple("Run", "out stdout stderr deck")

# An ngspice `.meas`/`print` result line: an identifier, `=`, a number. Anchored
# at the start of the line and required to end on a word boundary, so a value
# embedded in prose is not mistaken for a measurement. Accepts capital E
# exponents and a leading dot, which the per-script variants did not. The name
# may carry parentheses and brackets: a `print` inside `.control` labels its
# columns with the vector name, so an operating point comes back as
# `v(xdut.a) = ...` and a branch current as `i(vdd) = ...`.
# Exported so a study that must parse line by line (because the meaning of a
# result depends on a marker line above it) still accepts the same number forms.
NUMBER = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"

MEAS_RE = re.compile(r"^\s*([A-Za-z_][\w.\[\]()]*)\s*=\s*(%s)\b" % NUMBER, re.M)


class SpiceError(RuntimeError):
    """A tool did not produce what it was asked for (no netlist, no rawfile)."""


CONT_RE = re.compile(r"^\s*\+\s?(.*)$")


def unwrap(lines):
    """Fold SPICE `+` continuations into one logical line each.

    THE one definition, because parsing the wrapped form has now produced two
    separate silent-wrong-answer bugs in this repo:

      * `pex_reduce.py` keyed --merge-parallel on the head line only, merging
        devices that differ on the continuation and orphaning the `+`.
      * `nl2spice.py` read `.subckt tdc_line VDD VSS clk_i ...` and stopped at
        the line break, so it saw 11 of the extracted macro's 59 ports and
        emitted an 11-net instance. All 48 thermometer outputs of the delay
        line were left floating in the SPICE netlist, and the resulting NaN
        and collapsed timestep read exactly like "this circuit is too big to
        simulate".

    kpex wraps essentially every device and every wide `.subckt`, so any tool
    that reads an extracted netlist line-by-line needs this first.
    """
    out = []
    for ln in lines:
        m = CONT_RE.match(ln)
        if m and out:
            out[-1] = out[-1].rstrip() + " " + m.group(1).strip()
        else:
            out.append(ln)
    return out


_MCARD = re.compile(r"^(\s*)M(\S+)(\s+.*)$", re.I)


def cdl_to_ngspice(src, dst):
    """Copy a CDL standard-cell library into something ngspice can read.

    A CDL writes its devices as M cards -- `MN0 Y A VSS VPW sg13_lv_nmos w=..`
    -- and in this PDK `sg13_lv_nmos` is a SUBCIRCUIT, not a `.model`. netgen
    parses that happily, which is why LVS never complains, and ngspice stops
    at the first device with "could not find a valid modelname", naming the
    model rather than the card type. The PDK's own `sg13cmos5l_stdcell.spice`
    writes the identical devices as X cards for exactly this reason.

    The node order is the same either way (d g s b), so the fix is the card
    letter and nothing else. Written into a RUN DIRECTORY and never into
    $PDK_ROOT, the same rule mosfit.py follows.

    One difference stays and is not ours to fix: a CDL carries no `ad`/`as`/
    `pd`/`ps`, so the junction areas fall back to the model defaults instead of
    the drawn values the PDK library states. It moves junction capacitance, not
    topology.

    Returns dst.
    """
    out, n = [], 0
    for line in open(src):
        if _MCARD.match(line) and "=" in line:
            # Swap the CARD LETTER only, in place. Rebuilding the line from the
            # match groups drops its newline: `.` does not span one and `$`
            # matches before it, so every device in a cell ends up glued to the
            # next and to the closing .ENDS, and ngspice reports a .subckt/.ends
            # mismatch a hundred lines later.
            i = len(line) - len(line.lstrip())
            line = line[:i] + "X" + line[i + 1:]
            n += 1
        out.append(line)
    with open(dst, "w") as fh:
        fh.writelines(out)
    if not n:
        raise SystemExit("cdl_to_ngspice: no M cards in %s -- already X cards?"
                         % src)
    return dst


def run_deck(deck, workdir=None, tag="deck", cwd=None, timeout=None,
             keep=None):
    """Write `deck` to a file, run `ngspice -b` on it, return a Run.

    workdir  keep the deck and a `<tag>.log` transcript here, and run with this
             as the working directory (a deck that writes a rawfile or reads a
             model symlink needs that). Default: a temporary directory that is
             removed again, and nothing is kept.
    keep     additional path to copy the deck to, for the `--keep` debug
             options the studies expose.
    timeout  seconds; None waits. A study whose decks can run for half an hour
             should pass its own bound rather than rely on a default.
    """
    if keep:
        with open(keep, "w") as fh:
            fh.write(deck)

    if workdir is not None:
        os.makedirs(workdir, exist_ok=True)
        path = os.path.join(workdir, tag + ".spice")
        with open(path, "w") as fh:
            fh.write(deck)
        res = _ngspice(path, cwd or workdir, timeout)
        with open(os.path.join(workdir, tag + ".log"), "w") as fh:
            fh.write(res.out)
        return res._replace(deck=path)

    with tempfile.TemporaryDirectory(prefix="spicerun_") as td:
        path = os.path.join(td, tag + ".spice")
        with open(path, "w") as fh:
            fh.write(deck)
        return _ngspice(path, cwd, timeout)._replace(deck=path)


def run_file(path, cwd=None, timeout=None):
    """Run `ngspice -b` on a deck that already exists, e.g. one xschem wrote.

    `cwd` matters here: a netlisted testbench refers to its model libraries and
    writes its rawfile by relative path, so it has to run beside itself."""
    return _ngspice(path, cwd or os.path.dirname(path) or None, timeout)


def _ngspice(path, cwd, timeout):
    # A deck that lives in `cwd` is passed by its bare name: some netlisted
    # decks name their own rawfile relative to the deck, and ngspice resolves
    # that against the working directory. A deck outside `cwd` keeps its full
    # path -- naming it by basename would simply not be found.
    arg = path
    if cwd and os.path.dirname(os.path.abspath(path)) == os.path.abspath(cwd):
        arg = os.path.basename(path)
    r = subprocess.run([NGSPICE, "-b", arg], capture_output=True, text=True,
                       cwd=cwd, timeout=timeout)
    return Run(r.stdout + r.stderr, r.stdout, r.stderr, path)


def measures(out, keys=None):
    """Scrape `name = value` result lines into {name: float}.

    With `keys`, only those names are returned and a name the log does not
    carry maps to None -- which is how a study tells "the measurement failed"
    (ngspice prints `failed` for a `.meas` that found no crossing) apart from
    "the measurement was zero"."""
    found = {}
    for m in MEAS_RE.finditer(out):
        found[m.group(1)] = float(m.group(2))
    if keys is None:
        return found
    return {k: found.get(k) for k in keys}


def measure(out, key):
    """One result, or None when the log does not carry it."""
    return measures(out, [key])[key]


def run_measures(deck, keys=None, **kw):
    """run_deck() + measures(), for the studies that want nothing else."""
    return measures(run_deck(deck, **kw).out, keys)


def netlist_xschem(sch, out_dir, xschemrc=None, tcl=None, cwd=None,
                   timeout=120, flat=True, ext=".spice"):
    """Netlist `sch` with xschem and return the path of the written deck.

    xschem exits non-zero on paths that nonetheless produced a good netlist, so
    the check is on the file: it must exist and be non-empty. `tcl` passes a
    --tcl preamble, which is how the LVS and lvs_ignore variants are selected,
    and also how the netlist type is switched. `ext` follows that type: xschem
    names the file after it, so a `set netlist_type spectre` preamble (VACASK)
    needs ext=".spectre".
    """
    cmd = [XSCHEM]
    if xschemrc:
        cmd += ["--rcfile", xschemrc]
    if tcl:
        cmd += ["--tcl", tcl]
    cmd += ["-n", "-q", "-x"]
    if flat:
        cmd += ["-s"]                 # flatten the hierarchy into one deck
    cmd += ["-o", out_dir, sch]

    # xschem resolves a relative schematic against $PWD, not the process cwd:
    # without this a `./x.sch` from another directory exits 1 and says nothing
    wd = cwd or os.path.dirname(sch) or None
    env = dict(os.environ, PWD=os.path.abspath(wd)) if wd else None
    r = subprocess.run(cmd, cwd=wd, env=env,
                       capture_output=True, text=True, timeout=timeout)
    path = os.path.join(out_dir,
                        os.path.splitext(os.path.basename(sch))[0] + ext)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        raise SpiceError("xschem did not netlist %s\n%s\n%s"
                         % (path, r.stdout, r.stderr))
    return path


def _raw_num(tok):
    """One rawfile value: real, or `re,im` for a complex (ac) rawfile."""
    if "," in tok:
        re_s, im_s = tok.split(",", 1)
        return complex(float(re_s), float(im_s))
    return float(tok)


def read_ascii_raw(path):
    """Parse an ngspice ASCII rawfile -> (varnames, npoints, values[pt][var]).

    Values from an `ac` sweep are complex: ngspice writes them as `re,im` and
    they come back as Python complex.  A `tran`/`dc` rawfile still yields
    floats, so existing callers are unaffected.
    """
    with open(path) as fh:
        lines = [ln.rstrip("\n") for ln in fh]

    nvar = npt = 0
    varnames, i = [], 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("No. Variables:"):
            nvar = int(s.split(":")[1])
        elif s.startswith("No. Points:"):
            npt = int(s.split(":")[1])
        elif s.startswith("Variables:"):
            for j in range(nvar):
                varnames.append(lines[i + 1 + j].split()[1])   # idx name type
            i += nvar
        elif s.startswith("Values:"):
            i += 1
            break
        i += 1

    # One point spans nvar lines: the first carries "<index> <value>", the rest
    # only the value.
    vals = []
    while i < len(lines) and len(vals) < npt:
        if not lines[i].strip():
            i += 1
            continue
        row = [_raw_num(lines[i].split()[-1])]
        for j in range(1, nvar):
            row.append(_raw_num(lines[i + j].split()[-1]))
        vals.append(row)
        i += nvar
    return varnames, npt, vals


def read_raw(path):
    """An ngspice rawfile, binary (its default) or ASCII -> (varnames, npoints,
    values[pt][var]). Real plots only in binary: a `tran` or `dc` result."""
    with open(path, "rb") as fh:
        data = fh.read()
    k = data.find(b"Binary:\n")
    if k < 0:
        return read_ascii_raw(path)
    head = data[:k].decode("latin-1").splitlines()
    nvar = next(int(h.split(":")[1]) for h in head if h.startswith("No. Variables:"))
    npt = next(int(h.split(":")[1]) for h in head if h.startswith("No. Points:"))
    if any(h.startswith("Flags:") and "complex" in h for h in head):
        raise SpiceError("read_raw: complex binary rawfile, write it as ascii")
    i = next(n for n, h in enumerate(head) if h.startswith("Variables:"))
    varnames = [head[i + 1 + j].split()[1] for j in range(nvar)]
    import struct
    flat = struct.unpack_from("<%dd" % (nvar * npt), data, k + len(b"Binary:\n"))
    return varnames, npt, [list(flat[p * nvar:(p + 1) * nvar]) for p in range(npt)]


def col_index(varnames, node):
    """Column of a node voltage, tolerating bare `col[0]` or `v(col[0])`."""
    lower = [v.lower() for v in varnames]
    for want in (node.lower(), "v(%s)" % node.lower()):
        if want in lower:
            return lower.index(want)
    raise KeyError(node)


def _selftest_cdl():
    """cdl_to_ngspice: M -> X, and NOTHING else, newlines included."""
    src = os.path.join(tempfile.mkdtemp(), "in.cdl")
    dst = src + ".out"
    with open(src, "w") as fh:
        fh.write(".SUBCKT INVX1 A VDD VNW VPW VSS Y\n"
                 "*.PININFO A:I Y:O\n"
                 "MN0 Y A VSS VPW sg13_lv_nmos m=1 w=300.0n l=130.00n ng=1\n"
                 "MP0 Y A VDD VNW sg13_lv_pmos m=1 w=480.00n l=130.00n ng=1\n"
                 ".ENDS\n"
                 "* Model card, not a device: MOSFET\n")
    cdl_to_ngspice(src, dst)
    got = open(dst).read().splitlines()
    assert got[2].startswith("XN0 Y A VSS VPW sg13_lv_nmos"), got[2]
    assert got[3].startswith("XP0 "), got[3]
    assert got[4] == ".ENDS", got[4]
    assert got[5].startswith("* Model card"), got[5]
    assert len(got) == 6, got
    # and it must refuse a library that is already X cards, rather than
    # silently copying one that would then be included twice over
    with open(src, "w") as fh:
        fh.write(".SUBCKT A B\nXN0 B B B B sg13_lv_nmos w=1u\n.ENDS\n")
    try:
        cdl_to_ngspice(src, dst)
    except SystemExit:
        pass
    else:
        raise AssertionError("cdl_to_ngspice accepted a library with no M cards")
    print("cdl_to_ngspice selftest OK")


def _selftest_raw():
    """read_raw: a binary file decodes to what was packed, ASCII falls through."""
    import struct
    d = tempfile.mkdtemp()
    b = os.path.join(d, "b.raw")
    with open(b, "wb") as fh:
        fh.write(b"Title: t\nPlotname: Transient Analysis\nFlags: real\n"
                 b"No. Variables: 2\nNo. Points: 2\nVariables:\n"
                 b"\t0\ttime\ttime\n\t1\tv(a)\tvoltage\nBinary:\n")
        fh.write(struct.pack("<4d", 0.0, 1.5, 1e-9, -0.25))
    names, n, v = read_raw(b)
    assert names == ["time", "v(a)"] and n == 2 and v == [[0.0, 1.5], [1e-9, -0.25]], v
    a = os.path.join(d, "a.raw")
    with open(a, "w") as fh:
        fh.write("Title: t\nNo. Variables: 2\nNo. Points: 1\nVariables:\n"
                 "\t0\ttime\ttime\n\t1\tv(a)\tvoltage\nValues:\n0\t0.0\n\t2.0\n")
    assert read_raw(a)[2] == [[0.0, 2.0]]
    print("read_raw selftest OK")


def selftest():
    _selftest_cdl()
    _selftest_raw()
    """Check the scraper against the shapes ngspice actually prints."""
    log = "\n".join([
        "tcq                 =  1.234500e-11",
        "q_e = 1.5E-09",
        "per=.5",
        "i_vdd               = -2.32e-05",
        "vc_max              =   1.4998",
        "o12 = 0.75",
        "v(xdut.a) = 1.020000e+00",
        "i(vdd) = -2.3e-05",
        "tfail               = failed",
        "note: the limit = 40 fF was reached",     # prose, not a measurement
    ])
    got = measures(log)
    assert got["v(xdut.a)"] == 1.02, got           # a print'ed vector name
    assert got["i(vdd)"] == -2.3e-05, got
    assert got["tcq"] == 1.2345e-11, got
    assert got["q_e"] == 1.5e-09, got              # capital E
    assert got["per"] == 0.5, got                  # leading dot
    assert got["i_vdd"] == -2.32e-05, got
    assert got["vc_max"] == 1.4998, got
    assert got["o12"] == 0.75, got
    assert "tfail" not in got                      # `failed` is not a number
    assert "limit" not in got                      # not at the start of a line
    assert measure(log, "tcq") == 1.2345e-11
    assert measure(log, "nosuch") is None
    assert measures(log, ["per", "nosuch"]) == {"per": 0.5, "nosuch": None}
    assert col_index(["time", "v(q)"], "Q") == 1
    print("spicerun selftest: measurement scraper OK (ngspice at %s)" % NGSPICE)


if __name__ == "__main__":
    selftest()
