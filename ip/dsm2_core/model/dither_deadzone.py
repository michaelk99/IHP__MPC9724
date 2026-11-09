#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""DC transfer and dead zone of the first-order loop with the quantizer2 dither, against no dither.

The setup and the dc sweep are the system-level ones: 1.5 V supply, 1 mV LSB, first-order single-bit CIFB loop with H_inf 1.2, OSR 512,
sinc^2 decimation, 0.25 LSB steps over +-8 LSB, 0.1 mVrms input noise, dead zone as the span with |out| < 0.5 LSB. The only change is the quantizer: v = sign(y + d) with d the quantizer2 dither,
three bits per clock of a 17 bit XNOR Fibonacci LFSR (taps 17, 14) from the all-zero reset, levels A (2c - 7) / 7 of vo_p - vo_n.
A second sweep at 0.01 LSB over +-1.5 LSB with 64 decimated samples per point resolves the sub-LSB zones of the circuit leak.

usage: dither_deadzone.py [--out DIR]    (a Python with python-deltasigma)
"""
import argparse
from pathlib import Path

import deltasigma as ds
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# System-level spec and loop: OSR from the first-order SQNR equation, next power of 2, times 4 margin
vdd = 1.5
v_lsb = 0.001
v_fs = vdd
v_ref = v_fs / 2
enob_spec = np.log2(v_fs / v_lsb)
sqnr_peak_spec = 6.02 * enob_spec + 1.76
dsm_qlvls = 2
dsm_qbits = np.log2(dsm_qlvls)
osr = 10 ** ((sqnr_peak_spec - 6.02 * dsm_qbits - 1.76 - 10 * np.log10(3 / np.pi ** 2)) / 30)
dsm_osr = 2 ** np.ceil(np.log2(osr)) * 4
dsm_order = 1
dsm_ntf = ds.synthesizeNTF(dsm_order, dsm_osr, H_inf=1.2)
a, g, b, c = ds.realizeNTF(dsm_ntf, form='CIFB')
b = np.hstack((np.atleast_1d(b[0]), np.zeros((b.shape[0] - 1, ))))
a1, c1 = np.ravel(a)[0], np.ravel(c)[0]
ABCD = np.vstack((np.array([1, b[0], -a1]), np.array([c1, 0, 0])))
v_per_unit = v_ref
rng_seed = 1

# Integrator dc gain: the course sweep and the sc_int2 leak, schematic 2.72e-4 and Magic PEX 3.41e-4 per cycle
A0_CASES = [(30, "30 dB"), (40, "40 dB"), (50, "50 dB, course minimum"), (60, "60 dB"),
            (-20 * np.log10(3.41e-4), "69.3 dB, sc_int2 PEX leak"), (-20 * np.log10(2.72e-4), "71.3 dB, sc_int2 schematic leak"),
            (200, "no leak, measure floor")]
# Dither peak A (V of vo_p - vo_n), from the quantizer2 README: code 7 at tt per amplitude select, s[0] at the corner ends
DITHER_CASES = [(0.0, "off"), (76.5e-3, "s[0] tt 76.5 mV"), (0.655 * 76.5e-3, "s[1] tt 50.1 mV"), (1.365 * 76.5e-3, "s[2] tt 104.4 mV"),
                (0.305 * 76.5e-3, "s[3] tt 23.3 mV"), (70.0e-3, "s[0] ss -40 C 70.0 mV"), (82.5e-3, "s[0] ff 125 C 82.5 mV")]


def lfsr_codes(n):
    """quantizer2_lfsr: s[i] holds b[k-1-i], new bits nb[j] = XNOR(s[13-j], s[16-j]), code = nb0 + 2 nb1 + 4 nb2"""
    s = np.zeros(17, np.uint8)
    out = np.empty(n, np.int64)
    for k in range(n):
        nb = [1 ^ s[13 - j] ^ s[16 - j] for j in range(3)]
        out[k] = nb[0] | (nb[1] << 1) | (nb[2] << 2)
        s = np.concatenate(([nb[2], nb[1], nb[0]], s[:-3])).astype(np.uint8)
    return out


def run_loop(u, ABCD, d):
    """ds.simulateDSM for one 2-level first-order loop with an extra term d at the quantizer, vectorised over rows of u"""
    x = np.zeros(u.shape[0])
    v = np.empty_like(u)
    for n in range(u.shape[1]):
        y = ABCD[1, 0] * x + ABCD[1, 1] * u[:, n]
        # ds quantizer for 2 levels: +1 at y >= 0
        v[:, n] = np.where(y + d[n] >= 0, 1.0, -1.0)
        x = ABCD[0, 0] * x + ABCD[0, 1] * u[:, n] + ABCD[0, 2] * v[:, n]
    return v


def sweep(offset_sweep, n_dec, a0_db, amp, thnoise, codes):
    dec_order = dsm_order + 1
    p = 1 - 10 ** (-a0_db / 20)
    abcd = ABCD.copy()
    abcd[0, 0] = p
    d = amp / v_per_unit * (2.0 * codes - 7) / 7
    u = offset_sweep[:, None] + thnoise[None, :]
    v = run_loop(u, abcd, d)
    vout = np.empty(len(offset_sweep))
    for i in range(len(offset_sweep)):
        v_dec = ds.sinc_decimate(v[i], dec_order, int(dsm_osr))
        vout[i] = np.mean(v_dec[dec_order:])
    return vout


def check_loop():
    """the vectorised loop has to equal ds.simulateDSM without dither, bit for bit"""
    np.random.seed(rng_seed)
    u = 0.3e-3 / v_per_unit + np.random.randn(4096) * 0.1e-3 / v_per_unit * np.sqrt(dsm_osr)
    for a0_db in (50, 71.31):
        abcd = ABCD.copy()
        abcd[0, 0] = 1 - 10 ** (-a0_db / 20)
        ref = ds.simulateDSM(u, abcd, nlev=dsm_qlvls, x0=0)[0].squeeze()
        mine = run_loop(u[None, :], abcd, np.zeros(len(u)))[0]
        assert np.array_equal(ref, mine), "loop differs from ds.simulateDSM at %g dB" % a0_db


def flat_width(offset_sweep, vout, v_lsb_norm):
    """the system-level dead zone measure: the span of inputs whose output stays within half an LSB of 0"""
    flat = np.abs(vout) < 0.5 * v_lsb_norm
    w = np.ptp(offset_sweep[flat]) / v_lsb_norm if flat.any() else 0
    return w, bool(flat[0] or flat[-1])


def still_width(offset_sweep, vout, v_lsb_norm, tol=0.03):
    """the widest run of inputs around 0 over which the output moves by less than tol LSB"""
    x, y = offset_sweep / v_lsb_norm, vout / v_lsb_norm
    best = 0.0
    for i in range(len(x)):
        lo = hi = y[i]
        for j in range(i + 1, len(x)):
            lo, hi = min(lo, y[j]), max(hi, y[j])
            if hi - lo >= tol:
                break
            if x[i] <= 0 <= x[j]:
                best = max(best, x[j] - x[i])
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".")
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    check_loop()
    print("ABCD", ABCD.round(4).tolist(), "OSR", int(dsm_osr), "loop equals ds.simulateDSM")

    v_lsb_norm = v_lsb / v_per_unit
    dec_order = dsm_order + 1
    sigma = 0.1e-3 / v_per_unit
    runs = {}
    for name, n_dec, step, span in (("course", 16, 0.25, 8), ("fine", 64, 0.01, 1.5)):
        N_dc = int((n_dec + dec_order) * dsm_osr)
        offset_sweep = np.arange(-span, span + step / 2, step) * v_lsb_norm
        np.random.seed(rng_seed)
        thnoise = np.random.randn(N_dc) * sigma * np.sqrt(dsm_osr)
        codes = lfsr_codes(N_dc)
        res = np.zeros((len(A0_CASES), len(DITHER_CASES), len(offset_sweep)))
        for k, (a0_db, _) in enumerate(A0_CASES):
            for j, (amp, _) in enumerate(DITHER_CASES):
                res[k, j] = sweep(offset_sweep, n_dec, a0_db, amp, thnoise, codes)
        runs[name] = (offset_sweep, res)

    xs, rc = runs["course"]
    xf, rf = runs["fine"]
    print("\nDead zone in LSB (1 LSB = 1 mV). 0.25 LSB sweep: system-level measure, |out| < 0.5 LSB, 0.25 LSB steps."
          "\nfine: span around 0 where the output moves < 0.03 LSB, 0.01 LSB steps, 64 decimated samples.")
    hdr = "%-30s" % "A0 \\ dither" + "".join("%17s" % lab.split(" mV")[0] for _, lab in DITHER_CASES)
    print(hdr)
    for k, (_, alab) in enumerate(A0_CASES):
        row = []
        for j in range(len(DITHER_CASES)):
            w, clip = flat_width(xs, rc[k, j], v_lsb_norm)
            row.append("%s%.2f / %.2f" % (">" if clip else "", w, still_width(xf, rf[k, j], v_lsb_norm)))
        print("%-30s" % alab + "".join("%17s" % r for r in row))

    fig, axs = plt.subplots(2, 2, figsize=(13, 9))
    for ax, k in zip(axs.flat, (2, 3, 4, 5)):
        ax.plot(xs * v_per_unit / 1e-3, xs / v_lsb_norm, "k--", lw=1, label="ideal")
        for j, (_, dlab) in enumerate(DITHER_CASES):
            if j in (0, 1, 3, 4):
                ax.plot(xs * v_per_unit / 1e-3, rc[k, j] * v_per_unit / 1e-3, lw=1.3, label="dither " + dlab)
        ax.set_title("A0 " + A0_CASES[k][1])
        ax.set_xlabel("Input Voltage (mV)")
        ax.set_ylabel("Decimated Output (mV)")
        ax.grid(True)
        ax.legend(fontsize=8)
    fig.suptitle("DC transfer, the 0.25 LSB sweep with the quantizer2 dither")
    fig.tight_layout()
    fig.savefig(out / "dither_deadzone.png", dpi=110)

    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
    for ax, k in zip(axs, (2, 5)):
        for j, (_, dlab) in enumerate(DITHER_CASES):
            if j in (0, 1, 4):
                ax.plot(xf / v_lsb_norm, (rf[k, j] - xf) / v_lsb_norm, lw=1.2, label="dither " + dlab)
        ax.set_title("A0 " + A0_CASES[k][1] + ", fine sweep")
        ax.set_xlabel("Input (LSB)")
        ax.set_ylabel("Output minus input (LSB)")
        ax.grid(True)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "dither_deadzone_fine.png", dpi=110)
    print("\nplots:", out / "dither_deadzone.png", out / "dither_deadzone_fine.png")


if __name__ == "__main__":
    main()
