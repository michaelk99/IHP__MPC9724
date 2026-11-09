#!/usr/bin/env python3
"""System-level model of the modulator, with the integrator leak and the real noise.

The system-level PSD is taken at 1 Hz bins over a million samples, which cannot be put on the
same axes as a circuit run of a few thousand clock cycles without a noise-bandwidth
correction. This reproduces the same system-level modulator at whatever FFT length the
circuit run used, so the two curves are directly comparable.

Three things are modelled that the plain ideal simulation leaves out:

- the integrator leak from finite OTA gain, x[n+1] = p*x[n] + a1*(u[n]-v[n]) with p = (A0-1)/A0
- the OTA's own input-referred noise, generated with the shape measured on the OTA noise
  testbench, so the flicker rises toward DC instead of sitting flat
- the sampled kT/C of C1 and the OTA's wideband thermal noise folded by the sampling, both
  white

Noise is quoted in band throughout, the way the budget states it.

The loop filter is the first-order CIFB of the system-level design: a1 = 2 - 2/H_inf, which is
1/3 at H_inf = 1.2. The quantizer is the sign of the state, and the PSD normalisation matches
psd_bitstream.py so a full-scale sine sits at 0 dBFS.

For the DC accuracy it also models:

- the leak from the OTA gain by two mappings, --leak-map beta (A0_int = beta*A_OTA, the system-level mapping) or c1c2 (1-p = (C1/C2)/A_OTA per side, charge conservation)
- dither at the quantizer input, --qdither-v, the peak in volts of differential integrator output. The state maps to it as vod = x*V_REF, and the loop shapes the dither like quantization error.
- a chopped OTA error, --chop with --ota-offset and --chop-residue
- noise on VDD, which is the high DAC level, --vdd-noise
- the source resistance and pad capacitance ahead of C1, --rsrc and --cext. Both C1 of sc_int sample the one vi pad, P in phi1 and N in phi2, and each arrives from its last DAC level.
- a DC transfer sweep, --dc-sweep LO:HI:STEP in LSB from mid-scale, decimated sinc2 by OSR as the system-level sweep does. A comma list of up to 12 points also reports the ripple of each decimated output.

Usage: dsm_system.py [-o psd_system.csv] [--fres 1] [--a0-db 61.4] [--ota <spectrum.txt>]
       dsm_system.py --dc-sweep=-750:750:0.25 --noiseless [--a0-db 50] [--qdither-v 30e-3]
"""
import argparse
import os
import sys
from collections import deque
from fractions import Fraction

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psd_bitstream as pb   # noqa: E402, for the one fres -> nfft, tone bin rule

K_B = 1.380649e-23
TEMP = 300.0
V_LSB = 1e-3
RAT_HALF = 5.0      # LSB either side of each rational input that the DC sweep resolves finely
RAT_STEP = 0.05
DEC_DROP = 2        # decimator outputs dropped for the sinc2 start-up
READ_AVG = 16       # decimator outputs averaged into one reading, as the system-level sweep does
TRACE_MAX = 12      # a point list up to this long gets the ripple report
QD_BITS = {'lfsr4': 2, 'lfsr8': 3}


def shaped_noise(n, fs, target_rms, fb, spectrum, rng):
    """White noise shaped to a measured density, scaled to target_rms inside 0..fb."""
    f = np.fft.rfftfreq(n, 1.0 / fs)
    if spectrum is None:
        x = rng.standard_normal(n)
    else:
        d = np.loadtxt(spectrum, skiprows=1)
        fm, sm = d[:, 0], d[:, 1]
        # interpolate the density in log-log, hold the end values outside the measured range
        s = np.exp(np.interp(np.log(np.maximum(f, fm[0])), np.log(fm), np.log(sm)))
        spec = (rng.standard_normal(f.size) + 1j * rng.standard_normal(f.size)) * s
        spec[0] = 0.0
        x = np.fft.irfft(spec, n)
    # scale by what actually lands in band, which is the number the budget quotes
    win = np.hanning(n)
    sp = np.fft.rfft(x * win) / (np.linalg.norm(win, 1) / 2)
    inband = (f > 0) & (f <= fb)
    got = np.sqrt(np.sum(np.abs(sp[inband]) ** 2) / 3.0)
    return x * (target_rms / got) if got > 0 else x * 0.0


def leak(a):
    """Leak p, and a line naming the mapping when the OTA gain was given."""
    if a.a0_ota_db is None:
        return 1.0 - 10 ** (-a.a0_db / 20), None
    a_ota = 10 ** (a.a0_ota_db / 20)
    if a.leak_map == 'beta':
        beta = a.beta if a.beta is not None else a.c2 / (a.c1 + a.c2 + a.cgg)
        lk, how = 1 / (beta * a_ota), 'beta %.4f' % beta
    else:
        lk, how = (a.c1 / a.c2) / a_ota, 'C1/C2 %.4f' % (a.c1 / a.c2)
    with np.errstate(divide='ignore'):
        a0 = -20 * np.log10(lk)
    return 1.0 - lk, 'leak map %s: A_OTA %.1f dB, %s, A0_int %.2f dB' % (a.leak_map, a.a0_ota_db, how, a0)


def lfsr(n, seed):
    """+-1 from a 23-bit Fibonacci LFSR, s[k] = s[k-18] xor s[k-23], period 2^23-1."""
    b = np.empty(n + 23, np.uint8)
    fill = int(np.random.default_rng([seed, 23]).integers(1, 1 << 23))
    b[:23] = (fill >> np.arange(23)) & 1
    # 18 bits at a time, the nearest tap is 18 back
    for i in range(23, n + 23, 18):
        j = min(i + 18, n + 23)
        b[i:j] = b[i - 18:j - 18] ^ b[i - 23:j - 23]
    return 2.0 * b[23:] - 1.0


def add_noise(a, n, fb, rng, u):
    """Add the input referred terms to u. The draws keep their order, so a seed keeps its record."""
    terms, ota = {}, None
    if not a.noiseless:
        ktc = np.sqrt(2 * K_B * TEMP / (a.osr * a.c1))
        # White noise spreads over the whole Nyquist band, so its per-sample deviation is the in-band figure times sqrt(OSR).
        # The shaped term is scaled by what lands in band instead, so it takes the in-band figure directly.
        white_band = np.sqrt(ktc ** 2 + a.ota_folded ** 2) / a.vref
        flick_band = a.ota_inband / a.vref
        terms = {'kT/C + folded thermal': white_band, 'OTA in band': flick_band}
        u = u + rng.standard_normal(n) * white_band * np.sqrt(a.osr)
        ota = shaped_noise(n, a.fs, flick_band, fb, a.ota, rng)
    if a.ota_offset:
        ota = (0.0 if ota is None else ota) + a.ota_offset / a.vref
    if ota is not None:
        if a.chop:
            # (-1)^n moves the OTA error to fs/2, where the sinc2 decimator has a zero
            ota = ota * np.where(np.arange(n) % 2, -1.0, 1.0)
        u = u + ota
    if a.chop and a.chop_residue:
        u = u + a.chop_residue / a.vref
    if a.dither:
        u = u + rng.standard_normal(n) * (a.dither / a.vref) * np.sqrt(a.osr)
    return u, terms


def late_draws(a, n, rng):
    """VDD noise and quantizer dither, drawn after the input noise so older seeds keep their records."""
    vn = rng.standard_normal(n) * (a.vdd_noise / a.vref) * np.sqrt(a.osr) if a.vdd_noise else None
    qd = None
    if a.qdither_v:
        amp = a.qdither_v / a.vref
        if a.qdither_kind == 'uniform':
            qd = rng.uniform(-amp, amp, n)
        elif a.qdither_kind == 'lfsr':
            qd = amp * lfsr(n, a.seed)
        else:
            # nb LFSR bits per clock into an nb-bit DAC, levels equally spaced over +-amp
            nb = QD_BITS[a.qdither_kind]
            code = (lfsr(n * nb, a.seed).reshape(n, nb) > 0) @ (1 << np.arange(nb))
            top = (1 << nb) - 1
            qd = amp * (2.0 * code - top) / top
    return vn, qd


def pad_model(a):
    """(charge share fraction, recharge decay per half clock) of the vi pad, or None."""
    if not a.rsrc:
        return None
    if a.cext is None:
        raise SystemExit('--rsrc needs --cext, the capacitance on the pad node')
    kc = a.c1 / (a.c1 + a.cext)
    # C1 stays on the pad for its whole phase, so it recharges with Cext + C1
    dk = np.exp(-0.5 / a.fs / (a.rsrc * (a.cext + a.c1)))
    return kc, dk


def run_loop(n, dc, p, a1, sig=None, un=None, qd=None, vn=None, pad=None, w=None, keep=None, k0=0):
    """Run the loop over time, vectorised over the source levels in dc.

    v[k] = sign(x[k] + qd[k]), x[k+1] = p*x[k] + a1*(ue[k] - fb[k]).
    fb is v with VDD noise on the high level. ue is the source dc + sig, sampled through the pad when there is one, plus un.
    Returns acc (sum of w*v), xmax (peak |x| from k0 on), the bits of the columns in keep, and with a pad the mean charge per clock into both C1 and the mean shift of the sampled source, both in normalised units from k0 on.
    """
    m = dc.size
    if m == 1:
        return run_loop1(n, float(dc[0]), p, a1, sig, un, qd, vn, pad, w, keep, k0)
    x, xmax, acc = np.zeros(m), np.zeros(m), np.zeros(m)
    bits = None if keep is None else np.empty((n, len(keep)), np.int8)
    qsum, ssum = np.zeros(m), np.zeros(m)
    if pad is not None:
        kc, dk = pad
        up = dc + (0.0 if sig is None else sig[0])
        prev = np.ones(m)
    for k in range(n):
        v = np.where((x if qd is None else x + qd[k]) >= 0, 1.0, -1.0)
        fb = v if vn is None else v + (1.0 + v) * (0.5 * vn[k])
        if pad is None:
            ue = dc
        else:
            src = dc if sig is None else dc + sig[k]
            # phi1: C1P arrives from last clock's DAC level, shares with the pad, the pad recharges
            up = src + (up + kc * (prev - up) - src) * dk
            sp = up
            # phi2: C1N arrives from this clock's DAC level
            up = src + (up + kc * (fb - up) - src) * dk
            ue = 0.5 * (sp + up)
            if k >= k0:
                qsum += sp - prev + up - fb
                ssum += ue - src
            prev = fb
        if un is not None:
            ue = ue + un[k]
        x = p * x + a1 * (ue - fb)
        if k >= k0:
            np.maximum(xmax, np.abs(x), out=xmax)
        if w is not None:
            acc += w[k] * v
        if bits is not None:
            bits[k] = v[keep]
    cnt = max(n - k0, 1)
    return {'acc': acc, 'xmax': xmax, 'bits': bits, 'q': qsum / cnt, 'shift': ssum / cnt}


def run_loop1(n, dc, p, a1, sig, un, qd, vn, pad, w, keep, k0):
    """run_loop for one point in plain floats, about 50x faster there. Same operations in the same order."""
    lst = [None if z is None else z.tolist() for z in (sig, un, qd, vn, w)]
    sig, un, qd, vn, w = lst
    x = xmax = acc = qsum = ssum = 0.0
    bits = None if keep is None else np.empty((n, 1), np.int8)
    if pad is not None:
        kc, dk = pad
        up = dc + (0.0 if sig is None else sig[0])
        prev = 1.0
    for k in range(n):
        v = 1.0 if (x if qd is None else x + qd[k]) >= 0 else -1.0
        fb = v if vn is None else v + (1.0 + v) * (0.5 * vn[k])
        if pad is None:
            ue = dc
        else:
            src = dc if sig is None else dc + sig[k]
            up = src + (up + kc * (prev - up) - src) * dk
            sp = up
            up = src + (up + kc * (fb - up) - src) * dk
            ue = 0.5 * (sp + up)
            if k >= k0:
                qsum += sp - prev + up - fb
                ssum += ue - src
            prev = fb
        if un is not None:
            ue = ue + un[k]
        x = p * x + a1 * (ue - fb)
        if k >= k0 and abs(x) > xmax:
            xmax = abs(x)
        if w is not None:
            acc += w[k] * v
        if bits is not None:
            bits[k, 0] = v
    cnt = max(n - k0, 1)
    return {'acc': np.array([acc]), 'xmax': np.array([xmax]), 'bits': bits,
            'q': np.array([qsum / cnt]), 'shift': np.array([ssum / cnt])}


def sinc2_weights(r, navg):
    """w with sum(w*v) = mean(sinc_decimate(v, 2, r)[DEC_DROP:]) for len(v) = (navg + DEC_DROP)*r."""
    tri = np.convolve(np.ones(r), np.ones(r)) / r ** 2
    w = np.zeros((navg + DEC_DROP) * r)
    for j in range(DEC_DROP, DEC_DROP + navg):
        end = r * (j + 1)       # one past output sample r-1 + j*r
        w[end - tri.size:end] += tri
    return w / navg


def flat_zones(xin, y, tol=0.25, span=1.0):
    """Widest input window where y moves less than tol, and the count of regions wider than span."""
    o = np.argsort(xin, kind='stable')
    xs, ys = xin[o], y[o]
    hi, lo = deque(), deque()
    j, best, wins = 0, (0.0, 0.0, 0.0), []
    for i in range(xs.size):
        while hi and ys[hi[-1]] <= ys[i]:
            hi.pop()
        hi.append(i)
        while lo and ys[lo[-1]] >= ys[i]:
            lo.pop()
        lo.append(i)
        while ys[hi[0]] - ys[lo[0]] >= tol:
            j += 1
            if hi[0] < j:
                hi.popleft()
            if lo[0] < j:
                lo.popleft()
        width = xs[i] - xs[j]
        if width > span:
            wins.append((xs[j], xs[i]))
            if width > best[0]:
                best = (width, xs[j], xs[i])
    regions = 0
    end = -np.inf
    for s, e in wins:
        if s > end:
            regions += 1
        end = max(end, e)
    return best, regions


def near(u):
    """The simplest fraction close to u, as text."""
    return str(Fraction(float(u)).limit_denominator(16))


def sinc2_stream(v, r):
    """deltasigma.sinc_decimate(v, 2, r), the same arithmetic, so a trace does not need deltasigma."""
    x = np.asarray(v, float)
    for _ in range(2):
        x = np.cumsum(x)
        x = np.concatenate((x[:r], x[r:] - x[:-r])) / r
    return x[r - 1::r]


def sweep_points(spec):
    if ',' in spec:
        return np.array([float(t) for t in spec.split(',')])
    lo, hi, st = (float(t) for t in spec.split(':'))
    return lo + st * np.arange(int(np.floor((hi - lo) / st + 0.5)) + 1)


def dc_sweep(a, p, a1, fb, rng, a0_db):
    """DC transfer over the range, all points at once."""
    fs_lsb = a.vref / V_LSB
    main_pts = sweep_points(a.dc_sweep)
    lo, hi = main_pts.min(), main_pts.max()
    rats, rat_pts, rat_id = [], [], []
    for q in range(1, a.dc_rational + 1):
        for pn in range(-q, q + 1):
            c = fs_lsb * pn / q
            if np.gcd(pn, q) == 1 and lo <= c <= hi:
                f = c + RAT_STEP * np.arange(-round(RAT_HALF / RAT_STEP), round(RAT_HALF / RAT_STEP) + 1)
                f = f[(f >= lo) & (f <= hi)]
                rat_id += [len(rats)] * f.size
                rats.append('%d/%d' % (pn, q))
                rat_pts.append(f)
    rat_pts = np.concatenate(rat_pts) if rat_pts else np.zeros(0)
    pts = np.concatenate((main_pts, rat_pts, [a.dc_cal]))
    nm, nr = main_pts.size, rat_pts.size

    r = int(a.osr)
    n = (a.dc_navg + DEC_DROP) * r
    w = sinc2_weights(r, a.dc_navg)
    un, terms = add_noise(a, n, fb, rng, np.zeros(n))
    if a.noiseless and not (a.dither or a.ota_offset or (a.chop and a.chop_residue)):
        un = None
    vn, qd = late_draws(a, n, rng)
    pad = pad_model(a)
    dc = pts * V_LSB / a.vref
    trace = ',' in a.dc_sweep and nm <= TRACE_MAX
    keep = list(range(nm)) if trace else [0, nm // 2, nm - 1]
    res = run_loop(n, dc, p, a1, un=un, qd=qd, vn=vn, pad=pad, w=w, keep=keep, k0=DEC_DROP * r)
    out = res['acc'] * fs_lsb

    print('a1 %.4f, leak p %.6f from A0 %.1f dB, dc sweep' % (a1, p, a0_db))
    for k, val in terms.items():
        print('  noise %-22s %8.2f uV in band' % (k, val * a.vref * 1e6))
    print('points %g..%g LSB %s (%d), %d rationals q <= %d at +-%g LSB step %g (%d), cal at %g LSB'
          % (lo, hi, 'listed' if ',' in a.dc_sweep else 'step %g' % (main_pts[1] - main_pts[0] if nm > 1 else 0),
             nm, len(rats), a.dc_rational, RAT_HALF, RAT_STEP, nr, a.dc_cal))
    print('%d clocks per point, sinc2 by %d, first %d outputs dropped, %d averaged'
          % (n, r, DEC_DROP, a.dc_navg))
    try:
        import deltasigma as ds
        ref = np.array([np.mean(ds.sinc_decimate(res['bits'][:, i].astype(float), 2, r)[DEC_DROP:])
                        for i in range(len(keep))])
        print('sinc2 check against deltasigma.sinc_decimate on %d points: max difference %.3g LSB'
              % (len(keep), np.max(np.abs(ref - res['acc'][keep])) * fs_lsb))
    except ImportError:
        print('deltasigma not importable, sinc2 check skipped')

    xin, y = pts[:-1], out[:-1]
    err = y - xin
    gcal = a.dc_cal / out[-1]
    # a calibrated code cannot leave the full-scale range
    errc = np.clip(y * gcal, -fs_lsb, fs_lsb) - xin
    (fw, fa, fbz), nreg = flat_zones(xin, y)
    if nm > 1:
        g, off = np.polyfit(main_pts, out[:nm], 1)
        print('gain error from fit %+.1f ppm, offset %+.3f LSB, over the main points'
              % ((g - 1) * 1e6, off))
    if fw:
        print('flat zone: widest %.2f LSB, %+.2f..%+.2f LSB near u = %s, %d regions over 1 LSB'
              % (fw, fa, fbz, near(0.5 * (fa + fbz) / fs_lsb), nreg))
    else:
        print('flat zone: none, the output moves 0.25 LSB within every 1 LSB of input')
    i, ic = np.argmax(np.abs(err)), np.argmax(np.abs(errc))
    print('max |DC error| %.3f LSB at %+.2f LSB, raw' % (abs(err[i]), xin[i]))
    print('max |DC error| %.3f LSB at %+.2f LSB, after one-point gain cal at %g LSB (x%.6f), clipped to full scale'
          % (abs(errc[ic]), xin[ic], a.dc_cal, gcal))
    if nr:
        ec = np.abs(errc[nm:])
        rid = np.array(rat_id)
        worst = sorted(((ec[rid == k].max(), rats[k]) for k in range(len(rats))), reverse=True)[:6]
        print('worst rationals after cal: ' + ', '.join('%s %.2f' % (s, e) for e, s in worst))
    if trace:
        print('ripple of the decimated output, one reading = %d outputs, %d readings per point:'
              % (READ_AVG, a.dc_navg // READ_AVG))
        fd = a.fs / r
        for i in range(nm):
            yd = sinc2_stream(res['bits'][:, i], r)[DEC_DROP:] * fs_lsb
            rd = yd[:yd.size // READ_AVG * READ_AVG].reshape(-1, READ_AVG).mean(axis=1)
            win = np.hanning(yd.size)
            sp = np.abs(np.fft.rfft((yd - yd.mean()) * win)) * 2 / win.sum()
            k = 2 + np.argmax(sp[2:]) if sp.size > 2 else 0
            print('  %+9.3f LSB (vi %.5f V): mean %+9.3f, error %+.3f, output ptp %.3f, largest spur %.3f LSB '
                  'at %.1f Hz, readings ptp %.3f, std %.3f LSB'
                  % (pts[i], a.vref + pts[i] * V_LSB, yd.mean(), yd.mean() - pts[i], np.ptp(yd), sp[k],
                     k * fd / yd.size, np.ptp(rd) if rd.size else 0.0, rd.std() if rd.size else 0.0))
    sw = res['xmax'][:-1].max() * a.vref * 1e3
    print('state swing %.1f mV differential peak, %.1f mV per side, over all points' % (sw, sw / 2))

    if pad is not None:
        ref = run_loop(n, dc, p, a1, un=un, qd=qd, vn=vn, pad=None, w=w, k0=DEC_DROP * r)
        dout = out - ref['acc'] * fs_lsb
        ds_lsb = res['shift'] * fs_lsb
        iavg = res['q'] * a.c1 * a.vref * a.fs
        print('pad: Rsrc %g ohm, Cext %g F, tau %.3g s, share %.3g, against Rsrc = 0'
              % (a.rsrc, a.cext, a.rsrc * a.cext, pad[0]))
        if nm <= 10:
            for k in range(nm):
                print('  vi %.4f V (%+g LSB): output shift %+.4f LSB, sampled mean shift %+.4f LSB, '
                      'mean input current %+.4f nA'
                      % (a.vref + pts[k] * V_LSB, pts[k], dout[k], ds_lsb[k], iavg[k] * 1e9))
        print('  max |output shift| %.4f LSB, max |sampled mean shift| %.4f LSB, max |current| %.4f nA'
              % (np.abs(dout[:-1]).max(), np.abs(ds_lsb[:-1]).max(), np.abs(iavg[:-1]).max() * 1e9))

    o = np.argsort(xin, kind='stable')
    out_path = a.out or 'dc_system.csv'
    np.savetxt(out_path, np.column_stack((xin, y, err, errc, res['xmax'][:-1] * a.vref * 1e3))[o],
               delimiter=',', header='in_lsb,out_lsb,err_lsb,err_cal_lsb,swing_mv', comments='# ')
    print('wrote %s, %d points' % (out_path, xin.size))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-o', '--out', default=None, help='default psd_system.csv, or dc_system.csv with --dc-sweep')
    ap.add_argument('--nfft', type=int, default=None)
    ap.add_argument('--fres', type=float, default=None,
                    help='frequency resolution in Hz. Sets nfft and the tone bin by the same '
                         'rule the testbenches use, so one knob drives model and bench alike. '
                         'the system-level PSD run uses 1 Hz, which is 1024000 samples and about 2 s')
    ap.add_argument('--settle', type=int, default=160)
    ap.add_argument('--fs', type=float, default=1.024e6)
    ap.add_argument('--osr', type=float, default=512)
    ap.add_argument('--hinf', type=float, default=1.2)
    ap.add_argument('--ksig', type=int, default=None,
                    help='signal bin, odd keeps it coherent (default from --fres)')
    ap.add_argument('--ampl-dbfs', type=float, default=-6.0)
    ap.add_argument('--a0-db', type=float, default=61.4, help='integrator dc gain')
    ap.add_argument('--a0-ota-db', type=float, default=None,
                    help='OTA dc gain. Given, --leak-map turns it into the leak and --a0-db is ignored')
    ap.add_argument('--leak-map', choices=('beta', 'c1c2'), default='beta',
                    help='beta: A0_int = beta*A_OTA, the system-level mapping. c1c2: 1-p = (C1/C2)/A_OTA per side')
    ap.add_argument('--c1', type=float, default=64e-15)
    ap.add_argument('--c2', type=float, default=384e-15)
    ap.add_argument('--cgg', type=float, default=22e-15, help='OTA input gate capacitance per side')
    ap.add_argument('--beta', type=float, default=None, help='feedback factor, default C2/(C1+C2+Cgg)')
    ap.add_argument('--vref', type=float, default=0.75)
    ap.add_argument('--ota', default=None, help='OTA input-referred noise spectrum, V/sqrt(Hz)')
    ap.add_argument('--ota-inband', type=float, default=892.95e-6)
    ap.add_argument('--ota-folded', type=float, default=130.30e-6)
    ap.add_argument('--noiseless', action='store_true')
    ap.add_argument('--dither', type=float, default=None,
                    help='white input noise in Vrms, as the system-level PSD run does. It '
                         'injects v_lsb/sqrt(12) = 288.68e-6 with a fixed seed. '
                         'A noiseless first-order loop is chaotic and its SNR moves '
                         'several dB on any change, this is what makes the number repeatable')
    ap.add_argument('--qdither-v', type=float, default=0.0,
                    help='dither at the quantizer input, V of differential integrator output')
    ap.add_argument('--qdither-kind', choices=('lfsr', 'lfsr4', 'lfsr8', 'uniform'), default='lfsr',
                    help='lfsr: +-V per clock from a 23-bit LFSR. lfsr4, lfsr8: 4 or 8 equal levels over +-V from 2 or 3 LFSR bits per clock. uniform: uniform in +-V')
    ap.add_argument('--ota-offset', type=float, default=0.0, help='OTA offset, V input referred')
    ap.add_argument('--chop', action='store_true',
                    help='multiply the OTA error by (-1)^n. Pass --ota too, a white OTA model has nothing to move')
    ap.add_argument('--chop-residue', type=float, default=0.0, help='offset left after chopping, V')
    ap.add_argument('--vdd-noise', type=float, default=0.0,
                    help='white noise on VDD, the high DAC level, Vrms in band like --dither')
    ap.add_argument('--rsrc', type=float, default=0.0, help='source resistance to the vi pad, ohm')
    ap.add_argument('--cext', type=float, default=None, help='capacitance from the vi pad to ground, F')
    ap.add_argument('--dc-sweep', default=None, metavar='LO:HI:STEP',
                    help='DC transfer in LSB from mid-scale. The full range is --dc-sweep=-750:750:0.25, with the = because of the leading minus. A comma list of points works too')
    ap.add_argument('--dc-navg', type=int, default=16, help='decimated outputs averaged per point')
    ap.add_argument('--dc-cal', type=float, default=700.0, help='one-point gain calibration input, LSB')
    ap.add_argument('--dc-rational', type=int, default=8,
                    help='also sweep finely around every p/q with q up to this, 0 for none')
    ap.add_argument('--seed', type=int, default=1)
    a = ap.parse_args()

    a1 = 2 - 2 / a.hinf
    p, how = leak(a)
    with np.errstate(divide='ignore'):
        a0_db = a.a0_db if how is None else -20 * np.log10(1 - p)
    if how:
        print(how)
    rng = np.random.default_rng(a.seed)
    if a.dc_sweep:
        dc_sweep(a, p, a1, a.fs / (2 * a.osr), rng, a0_db)
        return
    a.out = a.out or 'psd_system.csv'

    if a.fres is not None:
        nfft, ksig, _ = pb.plan(a.fres)
        a.nfft = a.nfft or nfft
        a.ksig = a.ksig if a.ksig is not None else ksig
    if a.nfft is None:
        a.nfft = 4096
    if a.ksig is None:
        a.ksig = pb.plan(a.fs / a.nfft)[1]

    n, fb = a.nfft + a.settle, a.fs / (2 * a.osr)

    fsig = a.ksig * a.fs / a.nfft
    u = 10 ** (a.ampl_dbfs / 20) * np.sin(2 * np.pi * fsig / a.fs * np.arange(n))
    pad = pad_model(a)
    tone = None
    if pad is not None:
        # the tone goes through the pad, the noise is circuit noise and adds after sampling
        tone, u = u, np.zeros(n)
    u, terms = add_noise(a, n, fb, rng, u)
    vn, qd = late_draws(a, n, rng)

    if pad is None and vn is None and qd is None:
        x, v, xs = 0.0, np.empty(n), np.empty(n)
        for k in range(n):
            v[k] = 1.0 if x >= 0 else -1.0
            x = p * x + a1 * (u[k] - v[k])
            xs[k] = x
        swing = np.max(np.abs(xs[a.settle:]))
    else:
        res = run_loop(n, np.zeros(1), p, a1, sig=tone, un=u, qd=qd, vn=vn, pad=pad, keep=[0], k0=a.settle)
        v, swing = res['bits'][:, 0].astype(float), res['xmax'][0]

    b = v[a.settle:]
    win = np.hanning(a.nfft)
    n1, n2 = np.linalg.norm(win, 1), np.linalg.norm(win, 2)
    nbw = (n2 / n1) ** 2
    spec = np.fft.rfft(b * win) / (n1 / 2)
    f = np.fft.rfftfreq(a.nfft, 1.0 / a.fs)
    psd = 20 * np.log10(np.abs(spec) + 1e-20)

    sig = np.arange(max(a.ksig - 2, 1), a.ksig + 3)
    band = (f > 0) & (f <= fb)
    band[sig] = False
    ps = np.sum(np.abs(spec[sig]) ** 2)
    # no nbw here: the window factors cancel in the ratio, 1.5*A^2 over 3*sigma^2
    pn = np.sum(np.abs(spec[band]) ** 2)

    print('a1 %.4f, leak p %.6f from A0 %.1f dB, %d + %d samples, %.1f Hz bins'
          % (a1, p, a0_db, a.settle, a.nfft, a.fs / a.nfft))
    tot = np.sqrt(sum(v ** 2 for v in terms.values())) * a.vref if terms else 0.0
    for k, val in terms.items():
        print('  noise %-22s %8.2f uV in band' % (k, val * a.vref * 1e6))
    if terms:
        print('  noise %-22s %8.2f uV in band' % ('total', tot * 1e6))
    print('state swing %.1f mV differential peak, %.1f mV per side'
          % (swing * a.vref * 1e3, swing * a.vref * 1e3 / 2))
    print('tone %.1f Hz at bin %d, %.1f dBFS, density %.2f %%'
          % (fsig, a.ksig, a.ampl_dbfs, 50 * (1 + b.mean())))
    print('tone measured %.2f dBFS' % pb.tone_dbfs(ps))
    if pn > 0 and band.sum():
        snr = 10 * np.log10(ps / pn)
        print('in-band noise %.2f dBFS, SNR %.2f dB, ENOB %.2f bit'
              % (10 * np.log10(pn), snr, (snr - 1.76) / 6.02))
    else:
        print('no in-band bins left beside the signal, raise --nfft', file=sys.stderr)

    np.savetxt(a.out, np.column_stack((f, psd)), delimiter=',',
               header='nbw_hz=%.6g\nf,psd_dbfs' % (nbw * a.fs), comments='# ')
    print('wrote %s, %d bins, NBW %.4g Hz' % (a.out, f.size, nbw * a.fs))


if __name__ == '__main__':
    main()
