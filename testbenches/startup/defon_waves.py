# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Numbers of a STARTUP_DEFON=1 run that startup_check.py does not report: dsm2's output edges against di_clk,
its current burst while IOVDD ramps, vcm while it runs, and its current while VDDA ramps.

    python3 testbenches/startup/defon_waves.py testbenches/startup/build_defon/startup_core_first.txt

An output edge is clocked when it lies -1 to +25 ns from the last di_clk rise. Thresholds are VDDA/2 for dsm2's
1.5 V nets and 0.6 V for di_rst_b, as in startup_check.py."""
import sys

import numpy as np
import pandas as pd

HALF = 0.75
I_DSM2 = "i(v.xchip.vdsm2_vdd)"
CLK = "v(xchip.dsm_clk_pad2core)"
OUTS = ("v(xchip.dsm_do_q)", "v(xchip.dsm_do_q_b)", "v(xchip.dsm_do_q_dec)")
WIN = (-1e-9, 25e-9)


def cross(t, x, thr, rising=None):
    a = x > thr
    k = np.nonzero(a[1:] != a[:-1])[0]
    if rising is not None:
        k = k[a[k + 1] == rising]
    return t[k] + (t[k + 1] - t[k]) * (thr - x[k]) / (x[k + 1] - x[k])


def mean(t, x, a, b):
    s = (t >= a) & (t <= b)
    return np.trapezoid(x[s], t[s]) / (t[s][-1] - t[s][0])


def peak_mean(t, x, a, b, width):
    # the checker's method: the time integral on a 1 ns grid
    q = np.concatenate(([0.0], np.cumsum((x[1:] + x[:-1]) / 2 * np.diff(t))))
    g = np.arange(a, b - width, 1e-9)
    m = (np.interp(g + width, t, q) - np.interp(g, t, q)) / width
    k = int(np.argmax(m))
    return m[k], g[k]


def main(path):
    d = pd.read_csv(path, sep=r"\s+")
    c = {n.lower(): d[n].to_numpy() for n in d.columns}
    t, i = c["time"], c[I_DSM2]
    at = lambda n, x: float(np.interp(x, t, c[n]))
    rst = cross(t, c["v(xchip.dsm_rst_b)"], 0.6, True)[0]
    print(f"{path}: data to {t[-1] * 1e6:.2f} us, di_rst_b rises at {rst * 1e6:.2f} us")

    rises = cross(t, c[CLK], HALF, True)
    print(f"{len(rises)} di_clk rises from {rises[0] * 1e6:.2f} us")
    for n in OUTS:
        e = cross(t, c[n], HALF)
        e = e[e > rises[0] + WIN[0]]
        k = np.searchsorted(rises, e - WIN[0]) - 1
        dl = np.where(k >= 0, e - rises[np.maximum(k, 0)], np.inf)
        ok = (dl >= WIN[0]) & (dl <= WIN[1])
        print(f"{n}: {len(e)} edges, {ok.sum()} clocked at {dl[ok].min() * 1e9:.2f} to {dl[ok].max() * 1e9:.2f} ns after a di_clk rise"
              + "".join(f", one at {te * 1e6:.3f} us {x * 1e9:.1f} ns after a rise ({(te - rst) * 1e9:+.1f} ns from di_rst_b)"
                        for te, x in zip(e[~ok], dl[~ok])))

    # the burst: from di_ena until IOVDD is at 95 % of its end value
    on = cross(t, c["v(xchip.dsm_ena)"], 0.6, True)[0]
    up = float(t[np.nonzero(c["v(iovdd)"] > 0.95 * c["v(iovdd)"][-1])[0][0]])
    if up <= on:
        print(f"IOVDD up at {up * 1e6:.1f} us, before di_ena at {on * 1e6:.1f} us: no burst window")
    else:
        p, a = peak_mean(t, i, on, up, 100e-9)
        print(f"dsm2 from di_ena at {on * 1e6:.1f} us to IOVDD up at {up * 1e6:.1f} us: {p * 1e6:.1f} uA over 100 ns at {a * 1e6:.2f} us, "
              f"di_clk {at(CLK, a + 50e-9):.2f} V, IOVDD {at('v(iovdd)', a + 50e-9):.2f} V there")
        s = (t >= on) & (t < up)
        for lim in (100e-6, 30e-6):
            k = np.nonzero(s & (i > lim))[0]
            if len(k):
                print(f"  above {lim * 1e6:.0f} uA from {t[k[0]] * 1e6:.3f} to {t[k[-1]] * 1e6:.3f} us ({(t[k[-1]] - t[k[0]]) * 1e6:.3f} us), "
                      f"di_clk {c[CLK][k[0]]:.2f} to {c[CLK][k[-1]]:.2f} V, IOVDD {c['v(iovdd)'][k[0]]:.2f} to {c['v(iovdd)'][k[-1]]:.2f} V")
            else:
                print(f"  never above {lim * 1e6:.0f} uA")

    print(f"vcm {mean(t, c['v(xchip.vcm)'], rst + 10e-6, t[-1]):.4f} V, mean from 10 us after di_rst_b to the end")

    # VDDA's ramp, 5 to 95 % of its end value
    v = c["v(vdda)"]
    r0, r1 = (float(t[np.nonzero(v > f * v[-1])[0][0]]) for f in (0.05, 0.95))
    p1, a1 = peak_mean(t, i, r0, r1, 1e-6)
    s = (t >= r0) & (t <= r1)
    k = np.argmax(i[s])
    print(f"VDDA ramp {r0 * 1e6:.1f} to {r1 * 1e6:.1f} us: dsm2 at most {p1 * 1e6:.2f} uA over 1 us at {a1 * 1e6:.1f} us, "
          f"largest sample {i[s][k] * 1e6:.1f} uA at {t[s][k] * 1e6:.1f} us")
    for w0 in np.arange(r0 // 50e-6 * 50e-6, rst - 50e-6, 50e-6):
        print(f"  {w0 * 1e6:.0f} to {(w0 + 50e-6) * 1e6:.0f} us: dsm2 {mean(t, i, w0, w0 + 50e-6) * 1e6:.2f} uA, VDDA {at('v(vdda)', w0 + 50e-6):.3f} V")


if __name__ == "__main__":
    main(sys.argv[1])
