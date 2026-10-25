#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Plots and metrics for the bench records of programs 1 to 6.

    python3 models/bench_plot.py p1.bin p2.bin ... [--out DIR] [--show]
    python3 models/bench_plot.py --self-test

Reads the records bench_capture.py and bench_udp.py save (--save), in the ULX3S
master's framing, one program per file. Each stimulus capture is aligned against
the bit-true model and its metrics are computed. The decimated impulse response
gives the filter's frequency response over the output band, compared with the
exact response of the chain, CIC6 D32, sinc2^9, sinc2^16 and the 9-tap
compensator.

Needs numpy and matplotlib, unlike the rest of models/, so it is not one of the
CI self-tests.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench_capture as bc  # noqa: E402
import decimator_model as dm  # noqa: E402
import stimulus as S  # noqa: E402

FS = 65536.0              # clk_fs, the modulator rate
R = 128                   # decimation
FS_OUT = FS / R           # 512 Hz output rate
BW = 128.0                # signal band, OSR 256
FULL = 1 << 20            # a +1 input settles at this, the gain reference

# Group delay of the chain in clk_fs periods: CIC N(D-1)/2, then half a sample
# per sinc2 section at 2048 and 1024 Hz, then 4 samples of the 9-tap FIR at 512 Hz
CHAIN_DELAY = dm.N * (dm.D - 1) / 2 + dm.M1 * 0.5 * dm.D + dm.M2 * 0.5 * 2 * dm.D + 4 * R
COMP = [dm.comp_tap_value(t) for t in range(5)]
COMP = COMP + COMP[3::-1]  # 9 symmetric taps, b4 in the middle

NAMES = {1: "registers", 2: "step+", 3: "impulse", 4: "steady", 5: "step-", 6: "prbs23"}


# ---- the filter ----------------------------------------------------------------

def chain_response(f) -> np.ndarray:
    """Complex response of the decimation chain at f in Hz, unity at DC."""
    f = np.asarray(f, dtype=float)
    w = 2 * np.pi * f / FS
    with np.errstate(invalid="ignore", divide="ignore"):
        box = np.where(f == 0, 1.0, np.sin(dm.D * w / 2) / (dm.D * np.sin(w / 2)))
    cic = box ** dm.N * np.exp(-1j * w * dm.N * (dm.D - 1) / 2)
    s1 = ((1 + np.exp(-2j * np.pi * f / (FS / dm.D))) / 2) ** dm.M1
    s2 = ((1 + np.exp(-2j * np.pi * f / (FS / (2 * dm.D)))) / 2) ** dm.M2
    zc = np.exp(-2j * np.pi * f / FS_OUT)
    comp = sum(b * zc ** k for k, b in enumerate(COMP)) / sum(COMP)
    return cic * s1 * s2 * comp


def group_delay(f, h) -> np.ndarray:
    """-dphi/domega in seconds, from a response sampled at f."""
    return -np.gradient(np.unwrap(np.angle(h)), 2 * np.pi * np.asarray(f, dtype=float))


def impulse_bode(h, nfft: int = 4096):
    """(f, H) of a decimated impulse response over 0..FS_OUT/2, unity at DC."""
    spec = np.fft.rfft(np.asarray(h, dtype=float), nfft)
    return np.fft.rfftfreq(nfft, 1 / FS_OUT), spec / spec[0]


def first_below(f, mag_db, level: float):
    """The first frequency where mag_db drops below level, linearly interpolated."""
    i = np.nonzero(mag_db < level)[0]
    if not len(i) or i[0] == 0:
        return None
    k = i[0]
    return f[k - 1] + (level - mag_db[k - 1]) * (f[k] - f[k - 1]) / (mag_db[k] - mag_db[k - 1])


def enbw() -> float:
    """One-sided noise bandwidth of the chain in Hz, integral of |H|^2 up to FS/2."""
    f = np.linspace(0, FS / 2, (1 << 19) + 1)
    return float(np.trapezoid(np.abs(chain_response(f)) ** 2, f))


# ---- the metrics ---------------------------------------------------------------

def step_metrics(y) -> dict:
    """Final value, peak, overshoot, 10-90 % rise time and 0.1 % settling of a step."""
    y = np.asarray(y, dtype=float)
    final = y[-1]
    s = np.sign(final) or 1.0
    a = s * y
    peak = y[np.argmax(a)]
    t = np.arange(len(y)) * 1e3 / FS_OUT

    def cross(level):
        k = int(np.nonzero(a >= level * s * final)[0][0])
        return t[k] if k == 0 else t[k - 1] + (level * s * final - a[k - 1]) * (t[k] - t[k - 1]) / (a[k] - a[k - 1])

    out = np.nonzero(np.abs(y - final) > 1e-3 * abs(final))[0]
    return {"final": int(final), "peak": int(peak), "gain": final / FULL,
            "overshoot_pct": 100.0 * (s * peak - s * final) / abs(final),
            "rise_ms": cross(0.9) - cross(0.1),
            "settle_ms": t[out[-1] + 1] if len(out) else 0.0}


def impulse_metrics(h) -> dict:
    h = np.asarray(h, dtype=float)
    k = np.arange(len(h))
    f, H = impulse_bode(h)
    db = 20 * np.log10(np.abs(H))
    band = f <= BW
    gd = group_delay(f[band][1:], H[band][1:])
    return {"sum": int(h.sum()), "energy": float((h ** 2).sum()), "peak": int(h[np.argmax(np.abs(h))]),
            "peak_ms": float(np.argmax(np.abs(h)) * 1e3 / FS_OUT),
            "centroid_ms": float((k * h).sum() / h.sum() * 1e3 / FS_OUT),
            "f3db": first_below(f, db, -3.0), "ripple_db": float(db[band].max() - db[band].min()),
            "at_nyquist_db": float(db[-1]), "gd_spread_ms": float((gd.max() - gd.min()) * 1e3)}


def chain_metrics() -> dict:
    f = np.linspace(0, FS_OUT / 2, 4097)
    db = 20 * np.log10(np.abs(chain_response(f)))
    band = f <= BW
    worst = -np.inf
    for k in range(1, int(FS / 2 // FS_OUT) + 1):      # the bands that alias into 0..BW
        fa = np.linspace(k * FS_OUT - BW, min(k * FS_OUT + BW, FS / 2), 513)
        worst = max(worst, float(20 * np.log10(np.abs(chain_response(fa)).max())))
    return {"f3db": first_below(f, db, -3.0), "ripple_db": float(db[band].max() - db[band].min()),
            "alias_db": worst, "delay_ms": CHAIN_DELAY / FS * 1e3, "enbw_hz": enbw()}


# ---- the records ---------------------------------------------------------------

def parse_run(data: bytes, path: str | None = None) -> dict:
    """One program's records: its number, the SPI traffic and the aligned capture."""
    payloads, _ = bc.frames(data)
    run = {"path": path, "program": None, "spi": 0, "tst": None, "words": [], "counts": []}
    tst = None
    for p in payloads:
        k = p >> 60
        if k == bc.K_START:
            run["program"] = (p >> 56) & 0xF
        elif k == bc.K_SPI:
            run["spi"] += 1
            addr, sent = (p >> 55) & 0x1F, (p >> 39) & 0xFFFF
            if not addr & 0x10 and addr & 0xF == 9:
                tst = sent
        elif k == bc.K_ADC:
            if run["tst"] is None:
                run["tst"] = tst
            run["words"].append(bc.word22((p >> 44) & 0xFFFF, (p >> 28) & 0xFFFF))
            run["counts"].append((p >> 17) & 0x7FF)
    run["name"] = NAMES.get(run["program"], f"program {run['program']}")
    run["y"] = run["model"] = None
    run["diff"] = None
    tst = run["tst"]
    if tst is not None and tst & bc.STIM_EN and tst & bc.STIM_TRIG and run["words"]:
        pat, opt = (tst >> 13) & 3, bool(tst & bc.STIM_OPT)
        run["name"] = "prbs23" if pat == S.PAT_STEADY and opt else S.PAT_NAMES[pat] + (" repeat" if opt else "")
        model = S.predict(pat, opt, n_out=len(run["words"]))
        diff, off, n = bc.align(model, run["words"])
        run.update(y=run["words"][off:off + n], model=model[:n], diff=diff, offset=off)
    return run


def metrics_report(runs) -> str:
    ch = chain_metrics()
    lines = ["# Bench metrics", "",
             f"Output rate {FS_OUT:.0f} Hz, band {BW:.0f} Hz, a +1 input settles near 2^20 = {FULL}.", "",
             "| Program | Pattern | Words | Model mismatches | Metrics |", "|---|---|---:|---:|---|"]
    by = {r["name"]: r for r in runs}
    for r in runs:
        if r["y"] is None:
            lines.append(f"| {r['program']} | {r['name']} | {len(r['words'])} | | {r['spi']} SPI transactions |")
            continue
        y, text = r["y"], ""
        if r["name"] in ("step+", "step-", "steady"):
            m = step_metrics(y)
            text = (f"final {m['final']}, gain {abs(m['gain']):.6f} ({20 * np.log10(abs(m['gain'])):+.4f} dB), "
                    f"peak {m['peak']}, overshoot {m['overshoot_pct']:.2f} %, rise 10-90 % {m['rise_ms']:.2f} ms, "
                    f"settled to 0.1 % after {m['settle_ms']:.1f} ms")
        elif r["name"] == "impulse":
            m = impulse_metrics(y)
            text = (f"peak {m['peak']} at {m['peak_ms']:.1f} ms, sum {m['sum']}, centroid {m['centroid_ms']:.2f} ms, "
                    f"-3 dB at {m['f3db']:.1f} Hz, ripple 0..{BW:.0f} Hz {m['ripple_db']:.3f} dB, "
                    f"{m['at_nyquist_db']:.1f} dB at {FS_OUT / 2:.0f} Hz, group delay spread {m['gd_spread_ms']:.2e} ms")
        elif r["name"] == "prbs23":
            base = step_metrics(by["step+"]["y"])["final"] if "step+" in by and by["step+"]["y"] else 1048232
            tail = np.asarray(y[len(y) // 2:], dtype=float)
            theory = base * np.sqrt(2 * ch["enbw_hz"] / FS)
            text = (f"rms {tail.std():.0f} over the last {len(tail)} words, against {theory:.0f} for a white +-1 "
                    f"input through the chain's noise bandwidth. {len(tail)} correlated words scatter widely, a "
                    f"longer capture tightens it")
        lines.append(f"| {r['program']} | {r['name']} | {len(y)} | {r['diff']} | {text} |")
    if "step+" in by and "step-" in by and by["step+"]["y"] and by["step-"]["y"]:
        lines += ["", f"Step symmetry: step+ plus step- settles at "
                      f"{by['step+']['y'][-1] + by['step-']['y'][-1]} LSB."]
    if "steady" in by and "step+" in by and by["steady"]["y"] and by["step+"]["y"]:
        err = by["steady"]["y"][-1] - by["step+"]["y"][-1] / 2
        lines.append(f"Linearity: half scale minus half the step is {err:g} LSB, "
                     f"{1e6 * err / by['step+']['y'][-1]:.2f} ppm of the step.")
    lines += ["", "The chain, computed from the model's constants:", "",
              f"- -3 dB at {ch['f3db']:.1f} Hz, passband ripple 0..{BW:.0f} Hz {ch['ripple_db']:.3f} dB",
              f"- worst alias into the band, from {FS_OUT:.0f} Hz multiples +-{BW:.0f} Hz up to "
              f"{FS / 2:.0f} Hz: {ch['alias_db']:.1f} dB",
              f"- group delay {ch['delay_ms']:.3f} ms ({CHAIN_DELAY:.0f} clk_fs periods), linear phase",
              f"- noise bandwidth {ch['enbw_hz']:.2f} Hz", ""]
    return "\n".join(lines)


# ---- the figures ---------------------------------------------------------------

def figures(runs) -> list:
    """(file name, figure) for every plot of these runs, with the backend the caller chose."""
    import matplotlib.pyplot as plt
    figs = []
    stim = [r for r in runs if r["y"] is not None]
    if stim:
        fig, axs = plt.subplots(len(stim), 1, figsize=(8, 2.2 * len(stim)), sharex=True, squeeze=False)
        for ax, r in zip(axs[:, 0], stim):
            t = np.arange(len(r["y"])) * 1e3 / FS_OUT
            ax.plot(t, r["model"], "-", color="0.6", lw=1, label="bit-true model")
            ax.plot(t, r["y"], "o", ms=3, label="measured")
            ax.set_ylabel("LSB")
            ax.set_title(f"program {r['program']}, {r['name']}: {r['diff']} mismatches in {len(r['y'])} words",
                         fontsize=9)
            ax.grid(alpha=0.3)
        axs[0, 0].legend(fontsize=8)
        axs[-1, 0].set_xlabel("time after the fire, ms")
        fig.tight_layout()
        figs.append(("time_domain.png", fig))

    imp = next((r for r in runs if r["name"] == "impulse" and r["y"]), None)
    if imp:
        f, H = impulse_bode(imp["y"])
        fc = np.linspace(0, FS_OUT / 2, 2049)
        Hc = chain_response(fc)
        fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(8, 8), sharex=True)
        a1.plot(fc, 20 * np.log10(np.abs(Hc)), "-", color="0.6", lw=2, label="chain, from the model's constants")
        a1.plot(f, 20 * np.log10(np.abs(H)), "--", lw=1, label="measured, FFT of the impulse capture")
        a1.set_ylabel("magnitude, dB")
        a1.set_ylim(-80, 5)
        # phase with the capture's bulk delay taken out, so the ripple shows
        gd = group_delay(f[1:], H[1:])
        band = f[1:] <= BW
        tau = float(np.median(gd[band]))
        a2.plot(f, np.degrees(np.unwrap(np.angle(H)) + 2 * np.pi * f * tau), lw=1)
        a2.set_ylabel(f"phase + {tau * 1e3:.2f} ms delay, deg")
        a3.plot(f[1:], gd * 1e3, lw=1, label="measured")
        a3.axhline(CHAIN_DELAY / FS * 1e3, color="0.6", lw=1, ls=":", label="chain delay")
        a3.set_ylabel("group delay, ms")
        a3.set_xlabel("frequency, Hz")
        a3.legend(fontsize=8)
        for a in (a1, a2, a3):
            a.axvline(BW, color="r", lw=0.8, ls=":")
            a.grid(alpha=0.3)
        a1.legend(fontsize=8)
        a1.set_title("frequency response from the impulse capture, band edge dotted. Near 256 Hz the decimated "
                     "response folds in the band above it,\nso the measurement leaves the chain there, and its "
                     "group delay bends up", fontsize=9)
        fig.tight_layout()
        figs.append(("bode_impulse.png", fig))

    f = np.logspace(0, np.log10(FS / 2), 20000)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.semilogx(f, 20 * np.log10(np.abs(chain_response(f)) + 1e-30), lw=1)
    for k in range(1, int(FS / 2 // FS_OUT) + 1):
        ax.axvspan(k * FS_OUT - BW, k * FS_OUT + BW, color="r", alpha=0.08, lw=0)
    ax.axvspan(1, BW, color="g", alpha=0.08, lw=0)
    ax.set_ylim(-250, 10)
    ax.set_xlabel("frequency, Hz")
    ax.set_ylabel("magnitude, dB")
    ax.set_title("the chain up to clk_fs/2: band green, bands that alias into it red", fontsize=9)
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    figs.append(("chain_fullband.png", fig))
    return figs


def plot_all(runs, out: str, show: bool) -> None:
    import matplotlib
    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for name, fig in figures(runs):
        fig.savefig(os.path.join(out, name), dpi=150)
    if show:
        plt.show()


def self_test() -> int:
    ok = 0

    def check(cond, what):
        nonlocal ok
        if not cond:
            print("FAIL: " + what)
            sys.exit(1)
        ok += 1

    step = S.predict(S.PAT_STEP_P, False, n_out=60)
    m = step_metrics(step)
    check(m["final"] == 1048232 and m["peak"] == 1128189, f"step+ final/peak {m['final']} {m['peak']}")
    check(abs(m["overshoot_pct"] - 100.0 * (1128189 - 1048232) / 1048232) < 1e-9, "step+ overshoot")
    check(0 < m["rise_ms"] < 40, f"step+ rise time {m['rise_ms']} ms")
    check(abs(m["gain"] - 1048232 / FULL) < 1e-12, "step+ gain against 2^20")

    half = step_metrics(S.predict(S.PAT_STEADY, False, n_out=60))
    check(half["final"] == 524116 and 2 * half["final"] == m["final"], "half scale is exactly half the step")

    # the analytic chain: unity at DC, linear phase, 1261 clk_fs periods of delay
    f = np.linspace(1.0, BW, 64)
    check(abs(abs(chain_response(np.array([0.0]))[0]) - 1.0) < 1e-12, "chain response at DC")
    gd = group_delay(f, chain_response(f))
    check(np.allclose(gd, CHAIN_DELAY / FS, atol=1e-9), f"chain group delay {gd[0]} s")

    # the model's own impulse, through the FFT, matches the chain in the passband
    imp = np.array(S.predict(S.PAT_IMPULSE, False, n_out=48), dtype=float)
    fb, h = impulse_bode(imp)
    band = fb <= BW
    err = np.abs(20 * np.log10(np.abs(h[band])) - 20 * np.log10(np.abs(chain_response(fb[band]))))
    check(err.max() < 0.05, f"impulse FFT against the chain, worst {err.max():.4f} dB in 0..{BW:.0f} Hz")

    # records survive the round trip through the framing
    tst = 0x0500 | bc.STIM_EN | bc.STIM_TRIG | (S.PAT_IMPULSE << 13)
    payloads = [bc.pack_start(3), bc.pack_spi(9, tst, 0x0500)]
    payloads += [bc.pack_adc((w >> 16) & 0x3F, w & 0xFFFF, i, 0) for i, w in enumerate(imp.astype(int))]
    run = parse_run(b"".join(bc.encode(p) for p in payloads))
    check(run["program"] == 3 and run["name"] == "impulse" and run["diff"] == 0, f"parsed run {run['name']}")

    print(f"OK: bench_plot self-test, {ok} checks")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="record files, one program each")
    ap.add_argument("--out", default="bench_plots", help="where the figures and metrics.md go")
    ap.add_argument("--show", action="store_true", help="also open the figures")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.files:
        ap.error("give at least one record file")
    runs = [parse_run(open(p, "rb").read(), p) for p in args.files]
    os.makedirs(args.out, exist_ok=True)
    report = metrics_report(runs)
    with open(os.path.join(args.out, "metrics.md"), "w") as f:
        f.write(report)
    print(report, end="")
    plot_all(runs, args.out, args.show)
    return 0


if __name__ == "__main__":
    sys.exit(main())
