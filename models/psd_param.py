#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""SNR, SNDR and in-band noise of a sine record: calcPSDParam.m ported, and a corrected version.

    from psd_param import calc_psd_param, psd_param
    r = calc_psd_param(y, N, fs, fb, fsig, fres, FS)       # as jku-phd's SKY130_CT-DSM calcPSDParam.m
    m = psd_param(y, fs, fb, FS=2.0)                        # the corrected one, see below
    python3 models/psd_param.py --self-test

calc_psd_param reproduces calcPSDParam.m (jku-phd, SKY130_CT-DSM/system-level/
matlab/utility) to the last digit, checked against MATLAB R2024b. psd_param
keeps its conventions, 0 dBFS for a sine of amplitude FS/2 and SNR as a ratio
of sums over one window, and changes what the review found wrong:

1. MATLAB's hann(N) is the symmetric window, period N-1. Against a coherent
   tone it leaks a skirt at about 1/N of the tone, -94 dBc two bins out at
   N = 16384, which the noise sum picks up. The DSA1 decimator's output reads
   SNR 91.7 dB that way and 126.8 dB with the periodic window, which is its
   22-bit output word's floor. psd_param uses periodic windows.
2. spwr is the sum of the three main-lobe bins, 1.5 times the tone's power for
   Hann, so it reads 1.76 dB high. psd_param divides by the window's noise
   bandwidth in bins.
3. The mean is not removed, the DC skirt is excluded as bins 0 to 10 whatever
   the resolution. psd_param removes it and excludes the window's skirt.
4. Only HD2 and HD3 leave the SNR, and only where they fall unaliased. A
   decimated record folds higher harmonics into the band. psd_param folds
   HD2..HDk and reports THD.
5. The tone must sit on a bin and be given, and the signal is +-1 bin, right
   only for a coherent tone under Hann. psd_param finds the tone, measures its
   offset from the bin, and widens the signal bins and warns when it is off.
6. fres is an input though it is fs/N, a column y broadcasts w'.*y to an N x N
   matrix, and the leakage search sets nb_leak, which nothing reads after the
   temporary fix, so it is not ported.
"""
from __future__ import annotations

import sys

import numpy as np

# 7-term Blackman-Harris, sidelobes below -180 dB
BH7 = (0.27105140069342, 0.43329793923448, 0.21812299954311, 0.06592544638803,
       0.01081174209837, 0.00077658482522, 0.00001388721735)
HANN = (0.5, 0.5)


def cosine_window(n: int, coef, periodic: bool = True) -> np.ndarray:
    """sum_i (-1)^i a_i cos(2 pi i k / L), L = n periodic (DFT-even) or n - 1 symmetric"""
    k = np.arange(n)
    L = n if periodic else n - 1
    return sum((-1) ** i * a * np.cos(2 * np.pi * i * k / L) for i, a in enumerate(coef))


def _mround(x):
    return int(np.floor(x + 0.5))           # MATLAB round, half away from zero, for x >= 0


def calc_psd_param(y, N, fs, fb, fsig, fres, FS, finter=None):
    """calcPSDParam.m, same inputs and outputs in the same order, as a dict."""
    y = np.asarray(y, dtype=float).ravel()
    w = cosine_window(N, HANN, periodic=False)          # hann(N)
    nb = 3
    w1 = np.abs(w).sum()
    w2 = np.sqrt((w ** 2).sum())
    NBW = (w2 / w1) ** 2
    V = np.fft.fft(w * y) / (FS / 4) / w1
    fbin = _mround(fsig / fres)

    dc_bins = set(range(0, 11))
    h = (nb - 1) // 2
    signal_bins = list(range(fbin - h, fbin + h + 1))
    hd2_bins = list(range(2 * fbin - h, 2 * fbin + h + 1))
    hd3_bins = list(range(3 * fbin - h, 3 * fbin + h + 1))
    kb = _mround(fb / fres)
    inband = set(range(0, kb + 1))
    excl = dc_bins | set(signal_bins)
    if finter is not None:
        kint = _mround(finter / fres)
        excl |= set(range(kint - h, kint + h + 1))
    noise_sndr = sorted(inband - excl)
    noise_snr = sorted(inband - excl - set(hd2_bins) - set(hd3_bins))
    noise_snhd3r = sorted(inband - excl - set(hd2_bins))

    P = np.abs(V) ** 2
    spwr = P[signal_bins].sum() if all(b > 0 for b in signal_bins) else 0.0
    hd3pwr = P[hd3_bins].sum()
    HD3 = np.sqrt(hd3pwr) / np.sqrt(spwr)

    # cumulated in-band noise, the removed bins filled from neighbours with the original's indices
    Vn = V[:kb + 1].copy()
    if spwr != 0:
        Vn[signal_bins] = Vn[signal_bins[0] - 2]
    dcl = sorted(dc_bins)
    Vn[dcl] = Vn[[b + 20 for b in dcl]]
    if hd2_bins[-1] < len(Vn):
        Vn[hd2_bins] = Vn[hd2_bins[0] - 2]
    if hd3_bins[-1] < len(Vn):
        Vn[hd3_bins] = Vn[hd3_bins[0] - 2]
    ibn_cum = np.cumsum(np.abs(Vn) ** 2) / NBW / N

    return {"snr": 10 * np.log10(spwr / P[noise_snr].sum()),
            "sndr": 10 * np.log10(spwr / P[noise_sndr].sum()),
            "ibn": 10 * np.log10(ibn_cum[-1]), "V": V, "NBW": NBW,
            "spwr": 10 * np.log10(spwr), "snhd3r": 10 * np.log10(spwr / P[noise_snhd3r].sum()),
            "fbin": fbin, "nb": nb, "ibn_cum": ibn_cum, "HD3": HD3, "hd3pwr": hd3pwr}


def _fold(f, fs):
    f = f % fs
    return fs - f if f > fs / 2 else f


def psd_param(y, fs, fb, FS=2.0, fsig=None, window="bh7", harmonics=5, finter=None):
    """calcPSDParam's measurement with periodic windows, the mean removed, folded
    harmonics, a found and checked tone, and the tone's level read without the
    window's gain. window is "hann" (periodic) or "bh7". Returns a dict."""
    y = np.asarray(y, dtype=float).ravel()
    N = len(y)
    coef = BH7 if window == "bh7" else HANN
    w = cosine_window(N, coef)
    enbw = N * (w ** 2).sum() / w.sum() ** 2            # noise bandwidth in bins, 1.5 for Hann
    X = np.fft.rfft((y - y.mean()) * w) / (FS / 4) / w.sum()
    P = np.abs(X) ** 2
    fres = fs / N
    kb = int(np.floor(fb / fres))
    skirt = len(coef) - 1                               # a coherent tone's half width, and the mean's skirt

    if fsig is None:
        k0 = skirt + 1 + int(np.argmax(P[skirt + 1:kb + 1]))
    else:
        k0 = _mround(fsig / fres)
    # The tone's offset from its bin, from a periodic Hann spectrum whatever the window:
    # there |X(k0 + 1)| / |X(k0)| = (1 + d) / (2 - d) exactly for a tone d bins above k0.
    a, b, c = np.abs(np.fft.rfft((y - y.mean()) * cosine_window(N, HANN))[k0 - 1:k0 + 2])
    r = max(a, c) / b
    off = (2 * r - 1) / (r + 1) * (1 if c > a else -1)
    coherent = abs(off) < 0.01
    half = skirt if coherent else skirt + 2
    warn = [] if coherent else [f"tone {off:+.3f} bins off its bin, leakage past +-{half} bins counts as noise"]

    def lobe(k):
        return set(range(max(k - half, 0), min(k + half, len(P) - 1) + 1))

    sig = lobe(k0)
    harm = {}
    for hh in range(2, harmonics + 1):
        kh = _mround(_fold(hh * k0 * fres, fs) / fres)
        if kh <= kb and not (lobe(kh) & sig):
            harm[hh] = lobe(kh)
    excl = set(range(0, skirt + 1)) | sig
    if finter is not None:
        excl |= lobe(_mround(finter / fres))
    band = set(range(0, kb + 1))
    all_h = set().union(*harm.values()) if harm else set()
    noise = sorted(band - excl - all_h)
    ps = P[sorted(sig)].sum()
    pn = P[noise].sum()
    ph = {hh: P[sorted(s)].sum() for hh, s in harm.items()}
    pht = sum(ph.values())
    sndr = 10 * np.log10(ps / (pn + pht))
    return {"snr": 10 * np.log10(ps / pn), "sndr": sndr,
            "thd": 10 * np.log10(pht / ps) if pht else -np.inf,
            "hd": {hh: 10 * np.log10(v / ps) for hh, v in ph.items()},
            "enob": (sndr - 1.76) / 6.02,
            # the noise bins' mean level over the whole band, as dBFS against a full-scale sine
            "ibn": 10 * np.log10(pn / enbw * len(band) / len(noise)) if noise else np.inf,
            "amp_dbfs": 10 * np.log10(ps / enbw), "peak_dbfs": 20 * np.log10(np.abs(X[k0])),
            "fsig": k0 * fres, "bin": k0, "offset_bins": off, "coherent": coherent, "signal_bins": half,
            "noise_bins": len(noise), "enbw_bins": enbw, "window": window, "N": N, "fres": fres,
            "P": P, "warnings": warn}


# MATLAB R2024b, calcPSDParam.m on y1 of the self-test, 2026-09-29
_REF_Y1 = {"snr": 73.9947046923, "sndr": 73.0688547442, "ibn": -79.9904345569, "NBW": 9.15583226515e-05,
           "spwr": -4.25944705644, "snhd3r": 73.9934872505, "fbin": 1344, "nb": 3,
           "HD3": 3.34292903576e-06, "hd3pwr": 4.19092230126e-12}


def self_test() -> int:
    N = 16384
    n = np.arange(N)
    rng = np.random.default_rng(7)
    # a 0.5 amplitude coherent sine, sigma 1e-4 white noise, HD2 at -80 dBc
    y1 = 0.5 * np.sin(2 * np.pi * 1344 * n / N + 0.3) + 1e-4 * rng.standard_normal(N) \
        + 5e-5 * np.sin(2 * np.pi * 2688 * n / N)

    r = calc_psd_param(y1, N, 512.0, 128.0, 1344 * 512 / N, 512 / N, 2.0)
    for k, v in _REF_Y1.items():
        assert abs(r[k] - v) <= 1e-9 * max(1, abs(v)), (k, r[k], v)

    # the corrected one on the same record: SNR 10 log10(0.125 / (1e-8 / 2)), HD2 -80 dBc, amplitude -6.02 dBFS
    want = 10 * np.log10(0.125 / 0.5e-8)      # the expected value, one record scatters about 0.1 dB
    for win in ("hann", "bh7"):
        m = psd_param(y1, 512.0, 128.0, 2.0, window=win)
        assert m["coherent"] and m["bin"] == 1344, m["offset_bins"]
        assert abs(m["snr"] - want) < 0.3 and abs(m["hd"][2] + 80) < 0.5, (win, m["snr"], m["hd"])   # the noise in its bins moves it +-0.3 dB
        assert abs(m["amp_dbfs"] + 6.0206) < 0.01 and abs(m["peak_dbfs"] + 6.0206) < 0.01
        assert abs(m["ibn"] - 10 * np.log10(0.5e-8 / 0.5)) < 0.2, m["ibn"]

    # the symmetric window's ceiling: a coherent sine rounded to 20 fraction bits, dithered by
    # half an LSB rms as the modulator's noise does on the chip, or the rounding error is periodic
    # and lands on the harmonics
    lsb = 2.0 ** -20
    q = np.round((0.63 * np.sin(2 * np.pi * 1344 * n / N) + 0.5 * lsb * rng.standard_normal(N)) / lsb) * lsb
    floor = 10 * np.log10((0.63 ** 2 / 2) / ((lsb ** 2 / 12 + (0.5 * lsb) ** 2) / 2))
    old = calc_psd_param(q, N, 500.0, 125.0, 1344 * 500 / N, 500 / N, 2.0)["snr"]
    new = psd_param(q, 500.0, 125.0, 2.0, window="hann")["snr"]
    assert old < floor - 25 and abs(new - floor) < 0.5, (old, new, floor)

    # a DC offset does not reach the noise, an off-bin tone is found and flagged
    m = psd_param(y1 + 0.01, 512.0, 128.0, 2.0)
    assert abs(m["snr"] - want) < 0.3
    off = 0.5 * np.sin(2 * np.pi * 1344.3 * n / N) + 1e-4 * rng.standard_normal(N)
    m = psd_param(off, 512.0, 128.0, 2.0)
    assert not m["coherent"] and abs(m["offset_bins"] - 0.3) < 0.05 and m["warnings"], m["offset_bins"]
    assert abs(m["snr"] - want) < 1.0, m["snr"]

    # a harmonic above the Nyquist rate folds into the band and leaves the SNR:
    # bin 3000 is 93.75 Hz, its HD5 at 468.75 Hz folds to 43.25 Hz
    fold = 0.5 * np.sin(2 * np.pi * 3000 * n / N) + 1e-4 * rng.standard_normal(N) \
        + 5e-5 * np.sin(2 * np.pi * 5 * 3000 * n / N)
    m = psd_param(fold, 512.0, 128.0, 2.0, harmonics=5)
    assert 5 in m["hd"] and abs(m["hd"][5] + 80) < 0.5 and abs(m["snr"] - want) < 0.3, m["hd"]
    print("PASS: psd_param self-test")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    print(__doc__)
