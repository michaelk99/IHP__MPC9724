#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Spectra and bit-true checks of a recorded F stream.

    python3 models/stream_psd.py prbs.npz [--out DIR] [--show]
    python3 models/stream_psd.py dsm.npz --seq stim_dac_sine_dec.txt [--out DIR]
    python3 models/stream_psd.py --self-test

Reads what bench_record.py in the EasyConfig folder saves: the 22-bit words,
their conversion counts and the stimulus.

prbs  The on-chip PRBS23. The words from the fire on are compared with
      stimulus.predict, and their PSD with what the chain makes of white +-1
      input: |H(f)|^2 folded at the output rate.
dsm   A modulator sequence played into data_in. The words are compared with
      decimator_model run on the same sequence, and the tone gives SNR, SNDR,
      THD and ENOB in the signal band. A record of the DSA1 die's back end
      (die legacy, duo harness) is compared with decimator v4 instead, whose
      bit-true model jku-phd keeps in system-level/python/dec_v4_bit_true.py.

Words are placed by their conversion count, so a conversion lost in transport is skipped, not read as a shift of every word after it. The periodogram takes a run without a count gap.

Levels are dBFS against FULL, the word a +1 input settles at, so a full-scale
sine reads 0 dBFS. Needs numpy and matplotlib.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decimator_model as dm  # noqa: E402
import stimulus as S  # noqa: E402
from bench_plot import BW, FULL, R, chain_response  # noqa: E402
from psd_param import calc_psd_param, cosine_window, HANN, psd_param  # noqa: E402

N_HARM = 5
PSD_MIN = 1024                  # words in the shortest periodogram


# ---- spectra ------------------------------------------------------------------------

def welch(x, fs: float, nseg: int = 1024):
    """One-sided PSD per Hz, Hann, 50 % overlap, each segment's mean removed."""
    x = np.asarray(x, dtype=float)
    nseg = min(nseg, len(x))
    w = cosine_window(nseg, HANN)           # periodic, np.hanning is the symmetric one
    step = nseg // 2
    segs = [x[i:i + nseg] for i in range(0, len(x) - nseg + 1, step)]
    p = np.mean([np.abs(np.fft.rfft((s - s.mean()) * w)) ** 2 for s in segs], axis=0)
    p *= 2 / (fs * (w ** 2).sum())
    p[0] /= 2
    return np.fft.rfftfreq(nseg, 1 / fs), p, len(segs)


def prbs_theory(f, fs_clk: float) -> np.ndarray:
    """One-sided PSD per Hz of the decimated words for white +-1 input, in FULL units.

    The input's two-sided PSD is 1/fs_clk, the chain shapes it, and decimation
    by R folds every image of f spaced fs_clk/R apart onto f."""
    f = np.asarray(f, dtype=float)
    fo = fs_clk / R
    m = np.arange(-R // 2, R // 2)[:, None]
    h2 = np.abs(chain_response((f[None, :] + m * fo) * 65536.0 / fs_clk)) ** 2
    return 2 * h2.sum(axis=0) / fs_clk


def log_average(f, p, per_decade: int = 20, keep=()):
    """Mean power in log-spaced bands, for display only. Bins in keep, and bands
    narrower than a bin, stay raw, so a tone is not smeared."""
    f, p = np.asarray(f), np.asarray(p)
    keep = set(keep)
    lo = np.log10(f[1]) if f[0] == 0 else np.log10(f[0])
    edges = 10 ** np.arange(np.floor(lo), np.log10(f[-1]) + 1e-9, 1 / per_decade)
    fo, po = [], []
    i = 1 if f[0] == 0 else 0
    while i < len(f):
        if i in keep:
            fo.append(f[i])
            po.append(p[i])
            i += 1
            continue
        hi = edges[np.searchsorted(edges, f[i], side="right")] if f[i] < edges[-1] else np.inf
        j = i
        while j < len(f) and f[j] < hi and j not in keep:
            j += 1
        fo.append(np.exp(np.mean(np.log(f[i:j]))))
        po.append(p[i:j].mean())
        i = j
    return np.array(fo), np.array(po)


# ---- bit-true alignment -----------------------------------------------------------

def _pair(rec, ref, k: int):
    """rec and ref overlapped at offset k: rec word k + i is ref word i"""
    rec, ref = np.asarray(rec), np.asarray(ref)
    if k < 0:
        ref, k = ref[-k:], 0
    n = min(len(rec) - k, len(ref))
    return rec[k:k + n], ref[:n]


def by_count(word, count):
    """The record placed by conversion count, so word i of the result is conversion i.
    Returns those words, a mask of the ones that arrived, and each record word's index
    in them. Conversions lost in transport are holes, not a shift of everything after."""
    word, count = np.asarray(word, dtype=np.int64), np.asarray(count, dtype=np.int64)
    if not len(word):
        raise ValueError("no words in the record, nothing converted")
    pos = np.concatenate([[0], np.cumsum(np.diff(count) % 65536)])
    w = np.zeros(pos[-1] + 1, dtype=np.int64)
    got = np.zeros(pos[-1] + 1, dtype=bool)
    w[pos], got[pos] = word, True
    return w, got, pos


def align(rec, ref, lo: int, hi: int, m: int = 256, skip: int = 64, got=None):
    """The offset k in [lo, hi] where rec word k + i equals ref word i for i in
    skip..skip+m, else None. A negative k is a record that starts after ref does.
    With got from by_count only the words that arrived count, at least half the window.

    Matching past the first skip words finds the offset even when the start
    differs, a filter not settled before the fire, and compare() then says so."""
    got = np.ones(len(rec), dtype=bool) if got is None else got
    for k in range(lo, hi + 1):
        a, b = _pair(rec, ref, k)
        g = _pair(got, ref, k)[0][skip:skip + m]
        if len(a) >= skip + m and g.sum() >= m // 2 and np.array_equal(a[skip:skip + m][g], b[skip:skip + m][g]):
            return k
    return None


def compare(rec, ref, k: int, got=None) -> dict:
    a, b = _pair(rec, ref, k)
    g = np.ones(len(a), dtype=bool) if got is None else _pair(got, ref, k)[0]
    d = np.flatnonzero((a != b) & g)
    return {"offset": k, "compared": int(g.sum()), "differ": len(d), "lost": int((~g).sum()), "first": d[:5].tolist()}


def psd_window(count, skip: int) -> tuple:
    """(start, n) of the periodogram: n a power of two, from word skip on, inside one
    run of the record without a count gap, the longest such run."""
    breaks = np.flatnonzero(np.diff(np.asarray(count, dtype=np.int64)) % 65536 != 1) + 1
    runs = zip(np.r_[0, breaks], np.r_[breaks, len(count)])
    start, n = max(((max(a, skip), int(e) - max(a, skip)) for a, e in runs), key=lambda r: (r[1], -r[0]))
    if n < PSD_MIN:
        raise ValueError(f"too few words for a spectrum: {max(n, 0)} without a count gap after the first {skip}, {PSD_MIN} needed")
    return int(start), 1 << int(np.log2(n))


def model_cached(key: str, out: str, make):
    path = os.path.join(out, f"model_{key}.npy")
    if os.path.exists(path):
        return np.load(path)
    y = np.array(make(), dtype=np.int64)
    np.save(path, y)
    return y


def dsm_model(bits, n_out: int, lead_max: int = 8, probe: int = 400):
    """Model words for the played sequence. The DUT's reset release and data_in
    synchronizer add or eat a few clk_fs edges, which shifts the decimation
    phase, so the lead-in is found from a short probe and only then run in full.
    A lead L > 0 is L zeros before the first bit, L < 0 drops -L bits."""
    def run(lead, nbits):
        src = [0] * lead + list(bits[:nbits]) if lead >= 0 else list(bits[-lead:nbits])
        return dm.DecimatorModel().run(src)
    order = sorted(range(-lead_max, lead_max + 1), key=abs)
    return run, [(L, run(L, probe * R)) for L in order], n_out


# ---- the two kinds of record -----------------------------------------------------

def load(path: str) -> dict:
    z = np.load(path)
    return {"word": z["word"].astype(np.int64), "count": z["count"].astype(np.int64),
            "meta": json.loads(str(z["meta"])), "name": os.path.splitext(os.path.basename(path))[0]}


def analyse_prbs(r: dict, out: str) -> dict:
    meta = r["meta"]
    w, got, pos = by_count(r["word"], r["count"])
    fs = meta["fs_clk"] / R
    t = meta.get("trigger_after", 0)
    t = int(pos[t]) if t < len(pos) else len(w)     # the marks count record words, not conversions
    n_after = len(w) - t
    ref = model_cached(f"prbs23_{n_after}", out, lambda: S.predict(S.PAT_STEADY, opt=True, n_out=n_after))
    k = align(w, ref, t - 8, t + 64, got=got)
    res = {"kind": "prbs", "fs_out": fs, "gaps": int((np.diff(r["count"]) % 65536 != 1).sum())}
    res["bittrue"] = compare(w, ref, k, got) if k is not None else None
    x = (r["word"][pos >= k] if k is not None else r["word"]) / FULL
    f, p, nseg = welch(x, fs, 1024)
    th = prbs_theory(f, meta["fs_clk"])
    band = (f > 2 * fs / 1024) & (f <= BW)
    dev = 10 * np.log10(p[band] / th[band])
    res.update({"f": f, "p": p, "theory": th, "segments": nseg, "x": x,
                "var": float(x.var()), "var_theory": float(np.trapezoid(th, f)),
                "band_dev_mean": float(dev.mean()), "band_dev_sd": float(dev.std()),
                "level_dbfs_hz": float(10 * np.log10(th[1] / 0.5))})
    return res


def _dec_v4():
    """decimator v4's bit-true model, kept in jku-phd with the v4 RTL"""
    sys.path.insert(0, os.path.join(os.environ.get("JKU_PHD_DIR", os.path.join(os.path.dirname(__file__), "../../jku-phd")),
                                    "system-level/python"))
    from dec_v4_bit_true import dec_v4
    return dec_v4


def analyse_dsm(r: dict, out: str, seq: str, skip_s: float = 1.0) -> dict:
    meta = r["meta"]
    w, got, _ = by_count(r["word"], r["count"])
    legacy = meta.get("die") == "legacy"
    dec = 256 if legacy else R
    fs = meta["fs_clk"] / dec
    res = {"kind": "dsm", "die": "legacy, decimator v4" if legacy else "this chip, decimator v5",
           "fs_out": fs, "gaps": int((np.diff(r["count"]) % 65536 != 1).sum())}
    if seq:
        bits = dm.read_stimulus(seq)[: meta.get("play_bits", None)]
        if legacy:
            dec_v4 = _dec_v4()

            def run(lead, nbits):
                return dec_v4(bits[:nbits], npre=lead) if lead >= 0 else dec_v4(bits[-lead:nbits], npre=0)
            probes = [(L, run(L, 400 * dec)) for L in sorted(range(-8, 9), key=abs)]
        else:
            run, probes, _ = dsm_model(bits, len(w))
        best = None
        for lead, y in probes:
            k = align(w, y, -64, 64, 128, got=got)
            if k is not None:
                best = (lead, k)
                break
        if best is not None:
            lead, k = best
            ref = model_cached(f"dsm_{'v4' if legacy else 'v5'}_{len(bits)}_{lead}", out, lambda: run(lead, len(bits)))
            res["bittrue"] = {**compare(w, ref, k, got), "lead": lead}
        else:
            res["bittrue"] = None
    x = r["word"] / FULL
    s, n = psd_window(r["count"], int(skip_s * fs))     # a gap would smear the tone
    seg = x[s:s + n]
    band = BW * meta["fs_clk"] / 65536.0    # the 128 Hz band, scaled to the clk_fs the host ran
    m = psd_param(seg, fs, band, FS=2.0, window="bh7", harmonics=N_HARM)
    old = calc_psd_param(seg, n, fs, band, m["fsig"], fs / n, 2.0)
    # per bin, as calcPSDParam plots it: the tone reads its level in dBFS and the noise per
    # noise bandwidth, 2.6 bins for BH7, whose sidelobes stay below the 22-bit word's floor
    res.update(m)
    res.update({"band": band, "f": np.fft.rfftfreq(n, 1 / fs), "p": m["P"], "x": x, "seg": (s, n),
                "nbw": m["enbw_bins"] * fs / n, "calc_psd_param": {k: old[k] for k in ("snr", "sndr", "ibn", "spwr")}})
    return res


# ---- report and plots -------------------------------------------------------------

def report(res: dict, name: str) -> str:
    L = [f"# {name}" + (f", {res['die']}" if "die" in res else ""), ""]
    bt = res.get("bittrue")
    L.append(f"- output rate {res['fs_out']:.3f} Hz, {len(res['x'])} words analysed, {res['gaps']} count gaps in the record")
    if res["kind"] == "none":
        L.append("- no model: the die's own input")
    elif bt:
        extra = f", lead-in {bt['lead']} clk_fs edges" if "lead" in bt else ""
        extra += f", {bt['lost']} conversions lost in transport, skipped" if bt.get("lost") else ""
        L.append(f"- bit-true against the model: {bt['differ']} of {bt['compared']} words differ, from word {bt['offset']}{extra}")
    else:
        L.append("- bit-true: no alignment with the model found")
    if res["kind"] == "prbs":
        L += [f"- Welch PSD, {res['segments']} Hann segments of 1024, 50 % overlap",
              f"- variance {res['var']:.4e} FS^2, the chain predicts {res['var_theory']:.4e} ({10 * np.log10(res['var'] / res['var_theory']):+.3f} dB)",
              f"- in-band level {res['level_dbfs_hz']:.2f} dBFS/Hz predicted, measured minus predicted {res['band_dev_mean']:+.3f} dB mean, {res['band_dev_sd']:.2f} dB sd over the band"]
    else:
        s, n = res["seg"]
        c = res["calc_psd_param"]
        L += [f"- {n}-point periodogram, 7-term Blackman-Harris, from word {s}, bin {res['fs_out'] / n:.4f} Hz, {res['noise_bins']} noise bins",
              f"- tone {res['fsig']:.4f} Hz at {res['amp_dbfs']:.2f} dBFS, {res['offset_bins']:+.3f} bins off its bin",
              f"- SNR {res['snr']:.2f} dB, SNDR {res['sndr']:.2f} dB, THD {res['thd']:.2f} dB, ENOB {res['enob']:.2f} bit, IBN {res['ibn']:.1f} dBFS, in {res['band']:.1f} Hz",
              f"- calcPSDParam on the same words: SNR {c['snr']:.2f} dB, SNDR {c['sndr']:.2f} dB, IBN {c['ibn']:.1f} dBFS, its symmetric Hann's skirt, see psd_param.py"]
        L += [f"- {w}" for w in res["warnings"]]
    return "\n".join(L) + "\n"


def figures(res: dict, name: str) -> list:
    """(file name, figure) for the time and spectrum plots, with the backend the caller chose."""
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.3, "axes.titlesize": 10})
    figs = []
    fs, x = res["fs_out"], res["x"]
    band = BW * fs / 512.0

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5), gridspec_kw={"height_ratios": [2, 1]})
    t = np.arange(len(x)) / fs
    a1.plot(t, x, lw=0.4, color="C0")
    a1.set(xlabel="time (s)", ylabel="word / FULL", title=f"{name}: recorded words")
    z = slice(0, min(len(x), int(0.25 * fs)))
    a2.step(t[z] * 1e3, x[z], where="post", lw=0.8, color="C0")
    a2.set(xlabel="time (ms)", ylabel="word / FULL", title="first 250 ms")
    fig.tight_layout()
    figs.append((f"{name}_time.png", fig))

    f, p = res["f"], res["p"]
    db = lambda v: 10 * np.log10(np.maximum(v, 1e-30) / 0.5)
    if res["kind"] == "prbs":
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
        a1.semilogx(f[1:], db(p[1:]), lw=0.5, color="C0", alpha=0.35, label="Welch, raw bins")
        fa, pa = log_average(f, p)
        a1.semilogx(fa, db(pa), lw=1.5, color="C0", label="Welch, log-averaged")
        a1.semilogx(f[1:], db(res["theory"][1:]), "--", lw=1.2, color="C3", label=r"chain $|H(f)|^2$, folded, white $\pm$1 input")
        a1.axvline(band, color="0.4", lw=0.8, ls=":")
        a1.text(band, a1.get_ylim()[0] + 3, f" {band:.0f} Hz band edge", fontsize=8, color="0.3")
        a1.set(ylabel="PSD (dBFS/Hz)", title=f"{name}: PRBS23 through the decimator")
        a1.legend(loc="lower left", fontsize=8)
        a2.semilogx(f[1:], db(p[1:]) - db(res["theory"][1:]), lw=0.5, color="C0")
        a2.axhline(0, color="C3", lw=1)
        a2.set(xlabel="frequency (Hz)", ylabel="measured - chain (dB)", ylim=(-6, 6))
        bt = res.get("bittrue")
        txt = f"bit-true: {bt['differ']} of {bt['compared']} differ" if bt else "no model alignment"
        a1.text(0.99, 0.97, f"{txt}\nin band {res['band_dev_mean']:+.2f} dB against the chain",
                transform=a1.transAxes, ha="right", va="top", fontsize=8, bbox=dict(fc="w", ec="0.7"))
    else:
        fig, a1 = plt.subplots(figsize=(8, 4.5))
        k0 = res["bin"]
        dbb = lambda v: 10 * np.log10(np.maximum(v, 1e-30))
        a1.semilogx(f[1:], dbb(p[1:]), lw=0.4, color="C0", alpha=0.35, label="Blackman-Harris 7 periodogram, raw bins")
        hw = res["signal_bins"]
        fa, pa = log_average(f, p, keep=set(range(k0 - hw, k0 + hw + 1)))
        a1.semilogx(fa, dbb(pa), lw=1.3, color="C0", label="log-averaged, the tone's bins raw")
        a1.axvline(band, color="0.4", lw=0.8, ls=":")
        # the output word's rounding alone, LSB 1/FULL, white: 4 (LSB^2 / 12) ENBW / N per bin
        rfloor = 10 * np.log10(4 * (1.0 / FULL) ** 2 / 12 * res["enbw_bins"] / res["seg"][1])
        a1.axhline(rfloor, color="C3", lw=0.9, ls="--", label="22-bit output word, rounding alone")
        for h in range(2, N_HARM + 1):
            kh = k0 * h
            if kh + hw < len(f):
                a1.annotate(f"H{h}", (f[kh], dbb(p[kh - hw:kh + hw + 1].max())), textcoords="offset points",
                            xytext=(0, 6), ha="center", fontsize=7, color="C3")
        a1.set(xlabel="frequency (Hz)", ylabel=f"PSD (dBFS/NBW), NBW = {res['nbw'] * 1e3:.1f} mHz",
               title=f"{name}: {'its own input' if res['kind'] == 'none' else 'modulator sequence'} through {res.get('die', 'the decimator')}")
        a1.legend(loc="lower left", fontsize=8)
        bt = res.get("bittrue")
        txt = f"bit-true: {bt['differ']} of {bt['compared']} differ\n" if bt else ""
        a1.text(0.99, 0.97, f"{txt}tone {res['fsig']:.2f} Hz, {res['amp_dbfs']:.2f} dBFS\n"
                f"SNR {res['snr']:.1f} dB, SNDR {res['sndr']:.1f} dB\nTHD {res['thd']:.1f} dB, ENOB {res['enob']:.2f} bit\n"
                f"in {res['band']:.1f} Hz, {res['seg'][1]} points, BH7",
                transform=a1.transAxes, ha="right", va="top", fontsize=8, bbox=dict(fc="w", ec="0.7"))
    lo, hi = a1.get_ylim()
    a1.set_ylim(lo, hi + 0.25 * (hi - lo))       # room for the result box above the curve
    fig.tight_layout()
    figs.append((f"{name}_psd.png", fig))
    return figs


def plot(res: dict, name: str, out: str, show: bool) -> list:
    import matplotlib
    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    files = []
    for fn, fig in figures(res, name):
        files.append(os.path.join(out, fn))
        fig.savefig(files[-1], dpi=150)
    if show:
        plt.show()
    plt.close("all")
    return files


# ---- self-test ---------------------------------------------------------------------

def self_test() -> int:
    rng = np.random.default_rng(1)
    fs = 512.0

    # Welch of white noise reads its variance per Hz, and integrates back to it
    x = 0.1 * rng.standard_normal(1 << 16)
    f, p, _ = welch(x, fs, 1024)
    assert abs(10 * np.log10(p[5:-5].mean() / (2 * 0.01 / fs))) < 0.1
    assert abs(np.trapezoid(p, f) / 0.01 - 1) < 0.02

    # the chain's PSD for white +-1 input integrates to the variance the bit-true model gives it
    fo = np.linspace(0, 256, 4097)
    var = np.trapezoid(prbs_theory(fo, 65536.0), fo)
    y = np.array(dm.DecimatorModel().run(rng.integers(0, 2, 4200 * R).tolist())[200:]) / FULL
    assert abs(y.var() / var - 1) < 0.1, (y.var(), var)

    # log averaging keeps the level of a flat spectrum and a tone bin raw
    fa, pa = log_average(np.arange(1000.0), np.ones(1000), keep={500})
    assert np.allclose(pa, 1) and 500.0 in fa

    # alignment finds a known offset, and compare counts differences
    ref = rng.integers(-1000, 1000, 500)
    rec = np.concatenate([rng.integers(-1000, 1000, 17), ref])
    assert align(rec, ref, 0, 40, 64) == 17
    rec2 = rec.copy()
    rec2[17] += 5                               # an unsettled first word still aligns
    assert align(rec2, ref, 0, 40, 64) == 17 and compare(rec2, ref, 17)["first"] == [0]
    # a record that starts after the reference's first word has a negative offset
    assert align(ref[9:], ref, -40, 40, 64) == -9
    c = compare(ref[9:], ref, -9)
    assert c["differ"] == 0 and c["compared"] == len(ref) - 9
    rec[17 + 300] += 1
    c = compare(rec, ref, 17)
    assert c["differ"] == 1 and c["first"] == [300]

    # conversions lost in transport: the count says how many, the words after the gap
    # still line up with the model, and the count wraps at 65536 on the way
    rec = np.concatenate([rng.integers(-1000, 1000, 17), ref])
    cnt = (65500 + np.arange(len(rec))) % 65536
    keep = np.r_[0:17 + 200, 17 + 207:len(rec)]     # 7 conversions lost after model word 200
    w, got, pos = by_count(rec[keep], cnt[keep])
    assert len(w) == len(rec) and got.sum() == len(keep) and pos[17 + 200] == 17 + 207
    assert align(w, ref, 0, 40, 64, got=got) == 17
    c = compare(w, ref, 17, got)
    assert c["differ"] == 0 and c["lost"] == 7 and c["compared"] == len(ref) - 7, c
    w[17 + 300] += 1
    c = compare(w, ref, 17, got)
    assert c["differ"] == 1 and c["first"] == [300], c
    # the positional pairing this replaces reads every word after the gap as wrong
    assert compare(rec[keep], ref, 17)["differ"] > 250
    # a window that lost most of its words aligns nowhere
    lost = np.ones(len(rec), bool)
    lost[17:17 + 300] = False
    assert align(rec, ref, 0, 40, 64, got=lost) is None

    # an empty record says so instead of failing deep in numpy
    try:
        by_count(np.zeros(0, np.int64), np.zeros(0, np.int64))
        raise AssertionError("by_count took an empty record")
    except ValueError as e:
        assert "no words" in str(e), e

    # the periodogram takes a gap-free run: the whole record after the skip without a gap,
    # else the longest run, and never one shorter than PSD_MIN
    cnt = np.arange(20000)
    assert psd_window(cnt, 512) == (512, 16384)
    cnt[6000:] += 5
    assert psd_window(cnt, 512) == (6000, 8192)
    try:
        psd_window(np.arange(600), 512)
        raise AssertionError("psd_window took 88 words")
    except ValueError as e:
        assert "too few" in str(e), e

    # both analyses pair by count, so a record that lost conversions in transport stays bit-true
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        ref = np.array(S.predict(S.PAT_STEADY, opt=True, n_out=1500))
        rec = np.concatenate([np.zeros(20, np.int64), ref])
        keep = np.r_[0:900, 908:len(rec)]
        bt = analyse_prbs({"word": rec[keep], "count": np.arange(len(rec))[keep] % 65536,
                           "meta": {"fs_clk": 65536, "trigger_after": 20}}, tmp)["bittrue"]
        assert bt and bt["differ"] == 0 and bt["lost"] == 8 and bt["offset"] == 20, bt

        u, acc, bits = 0.5 * np.sin(2 * np.pi * 37.1 * np.arange(1400 * R) / 65536), 0.0, []
        for v in u:                             # first-order modulator, a tone that never repeats in whole words
            bits.append(int(acc >= 0))
            acc += v - (1 if bits[-1] else -1)
        seq = os.path.join(tmp, "seq.txt")
        with open(seq, "w") as fh:
            fh.writelines(f"{i} {2 * b - 1}\n" for i, b in enumerate(bits))
        y = np.array(dm.DecimatorModel().run(bits))
        keep = np.r_[0:1200, 1205:len(y)]
        res = analyse_dsm({"word": y[keep], "count": np.arange(len(y))[keep],
                           "meta": {"fs_clk": 65536, "play_bits": len(bits)}}, tmp, seq, skip_s=0.25)
        bt = res["bittrue"]
        assert bt and bt["differ"] == 0 and bt["lost"] == 5 and bt["lead"] == 0, bt
        assert res["seg"] == (128, 1024), res["seg"]
        assert "5 conversions lost in transport" in report(res, "dsm"), report(res, "dsm")
    print("PASS: stream_psd self-test")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("record", nargs="*")
    ap.add_argument("--seq", default=os.path.join(os.environ.get("JKU_PHD_DIR", "../jku-phd"),
                                                  "circuit-level/hdl/DSADC1/DIG_TOP/sim/stim_dac_sine_dec.txt"),
                    help="the modulator sequence a dsm record played")
    ap.add_argument("--out", default=".")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    os.makedirs(a.out, exist_ok=True)
    for path in a.record:
        r = load(path)
        kind = r["meta"]["stim"]
        if kind == "prbs":
            res = analyse_prbs(r, a.out)
        elif kind in ("dsm", "none"):
            # none: whatever the die converts, its own modulator on silicon, so spectrum and metrics only
            res = analyse_dsm(r, a.out, a.seq if kind == "dsm" and os.path.exists(a.seq) else None)
            res["kind"] = kind
        else:
            sys.exit(f"{path}: stimulus {kind}, only prbs, dsm and none are analysed")
        text = report(res, r["name"])
        print(text)
        with open(os.path.join(a.out, f"{r['name']}_metrics.md"), "w") as fh:
            fh.write(text)
        for fn in plot(res, r["name"], a.out, a.show):
            print(f"wrote {fn}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
