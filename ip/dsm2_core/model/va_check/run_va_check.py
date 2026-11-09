#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Compile ../dsm2_core.va, run tb_dsm2_core_va.spice per case and compare the bit stream with the Python loop of dsm_system.py.

Run from the repo root in the sign-off image: python3 ip/dsm2_core/model/va_check/run_va_check.py [--out runs/trl1/va] [--quick] [--jobs 6]
Writes summary.txt in --out. Exits 1 if any check fails.
"""
import argparse
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import dsm_system as ds  # noqa: E402
import psd_bitstream as pb  # noqa: E402

FS, VREF, VSUP = 1.024e6, 0.75, 1.5
A1, LEAK = 1.0 / 3.0, 10 ** (-61.4 / 20)   # dsm_system.py at H_inf 1.2 and A0 61.4 dB, passed to the model on its .model line
DITH_A0 = 76.5e-3   # di_dith_amp 00
YSAT = 1.41   # the model clip
OSC_SCALE, OSC_F = 0.7824, {0: 565.9e3, 4: 822.9e3, 15: 1479.1e3}   # model defaults
TAU = 1e-9   # track time constant of the model, the master lags vi by about this
NSETTLE = 32


def lfsr_codes(n):
    """quantizer2_lfsr: s[i] holds b[k-1-i], new bits nb[j] = XNOR(s[13-j], s[16-j]), code = nb0 + 2 nb1 + 4 nb2"""
    # copied from dither_deadzone.py, whose module imports deltasigma, which the image lacks.
    # quantizer2_README.md matched this rule to the circuit for 200 clocks.
    s = np.zeros(17, np.uint8)
    out = np.empty(n, np.int64)
    for k in range(n):
        nb = [1 ^ s[13 - j] ^ s[16 - j] for j in range(3)]
        out[k] = nb[0] | (nb[1] << 1) | (nb[2] << 2)
        s = np.concatenate(([nb[2], nb[1], nb[0]], s[:-3])).astype(np.uint8)
    return out


def python_bits(n, vdc, vamp=0.0, fsig=0.0, amp=0.0):
    """dsm_system.run_loop1 on the same input, dither as quantizer2 with amplitude amp (V of vo_p - vo_n, 0 is off)."""
    un = vamp / VREF * np.sin(2 * np.pi * fsig / FS * np.arange(n)) if vamp else None
    qd = amp / VREF * (2.0 * lfsr_codes(n) - 7) / 7 if amp else None
    res = ds.run_loop1(n, vdc / VREF, 1 - LEAK, A1, None, un, qd, None, None, None, [0], 0)
    return (res['bits'][:, 0] > 0).astype(int)


def reset_bits(n, vdc, nrst):
    """the model's own loop with q held at 0 for the first nrst clocks and the clip at YSAT, no dither"""
    x, xs, out = 0.0, YSAT / VREF, np.empty(n, int)
    for k in range(n):
        v = 1.0 if (k >= nrst and x >= 0) else -1.0
        out[k] = v > 0
        x = min(max((1 - LEAK) * x + A1 * (vdc / VREF - v), -xs), xs)
    return out


def stair(nclk, vamp, fsig):
    """vi as a PWL staircase: the sample of clock k, stepping at (k - 0.25)/fs while the master holds"""
    u = vamp * np.sin(2 * np.pi * fsig / FS * np.arange(nclk + 1))
    pts = ['0 %.12e' % u[0]]
    for k in range(nclk):
        t = (k + 0.75) / FS
        pts.append('%.9e %.12e %.9e %.12e' % (t, u[k], t + 1e-9, u[k + 1]))
    return 'VI vi vref PWL(\n+ ' + '\n+ '.join(pts) + ')\n'


def run_case(out, osdi, name, nclk, par, vi=None):
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    tb = (HERE / 'tb_dsm2_core_va.spice').read_text()
    if vi:
        tb, cnt = re.subn(r'^VI vi vref .*\n', lambda m: vi, tb, flags=re.M)
        assert cnt == 1
    for k, v in dict(par, nclk=nclk, leak=LEAK).items():
        tb, cnt = re.subn(r'(\.param .*?\b%s=)\S+' % k, r'\g<1>%r' % v, tb)
        assert cnt == 1, k
    (d / 'tb.spice').write_text(tb)
    shutil.copy(osdi, d / 'dsm2_core.osdi')
    r = subprocess.run(['ngspice', '-b', 'tb.spice'], cwd=d, capture_output=True, text=True)
    (d / 'ngspice.log').write_text(r.stdout + r.stderr)
    if r.returncode or not (d / 'tb_dsm2_core_va.raw').exists():
        raise SystemExit('%s: ngspice failed, see %s' % (name, d / 'ngspice.log'))
    names, arr = pb.readraw(d / 'tb_dsm2_core_va.raw')
    return {n: arr[:, i] for i, n in enumerate(names)}


def sample_bits(w, nclk, node='v(do_q)'):
    """the bit of clock k, k = 0 .. nclk-1, at (k + 0.75)/fs"""
    return (np.interp((np.arange(nclk) + 0.75) / FS, w['time'], w[node]) > VSUP / 2).astype(int)


def snr(bits, ksig):
    f, _, spec, _ = pb.spectrum(2.0 * bits - 1)
    s, n, _ = pb.split_band(f, spec, ksig)
    return 10 * np.log10(s / n)


def rising(w, node, t0=0.0):
    t, v = w['time'], w[node] - VSUP / 2
    i = np.nonzero((v[:-1] < 0) & (v[1:] >= 0) & (t[1:] > t0))[0]
    return t[i] - v[i] * (t[i + 1] - t[i]) / (v[i + 1] - v[i])


def tmean(w, node, t0):
    """time average of a node over t >= t0, in units of VSUP"""
    m = w['time'] >= t0
    t, v = w['time'][m], w[node][m]
    return np.sum(0.5 * (v[1:] + v[:-1]) * np.diff(t)) / (t[-1] - t[0]) / VSUP


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='runs/trl1/va')
    ap.add_argument('--quick', action='store_true', help='short runs to try the flow')
    ap.add_argument('--jobs', type=int, default=6)
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    osdi = out / 'dsm2_core.osdi'
    subprocess.run(['openvaf', str(HERE.parent / 'dsm2_core.va'), '-o', str(osdi)], check=True)

    ndc = 256 if a.quick else 2048
    fres = 1000.0 if a.quick else 62.5
    nfft, ksig, fsig = pb.plan(fres)
    nsine = NSETTLE + nfft + 8
    vamp = VREF * 10 ** (-6 / 20)
    phase = -360.0 * fsig * (0.5 / FS - TAU)   # sine phase zero where the master stops tracking at clock 0
    dcs = (0.3, 0.0, -0.3, 0.6)
    cases = {'sine_cont_d0': (nsine, dict(vdc=0.0, vamp=vamp, fsig=fsig, phase=phase, dith=0))}
    for dith in (0, 1):
        cases['sine_d%d' % dith] = (nsine, dict(vdc=0.0, dith=dith), stair(nsine, vamp, fsig))
        for vdc in dcs:
            cases['dc_%+.1f_d%d' % (vdc, dith)] = (ndc, dict(vdc=vdc, dith=dith))
    trims = {0: (0, 0, 0, 0), 4: (0, 1, 0, 0), 15: (1, 1, 1, 1)}
    for code, (b3, b2, b1, b0) in trims.items():
        cases['osc_%d' % code] = (200, dict(vdc=0.3, osc=1, csel=1, t3=b3, t2=b2, t1=b1, t0=b0))
    cases['reset'] = (80, dict(vdc=0.3, trst=20.25 / FS))
    cases['qout_off'] = (64, dict(vdc=0.3, qout=0))
    cases['ena_off'] = (64, dict(vdc=0.3, ena=0))
    cases['btest'] = (64, dict(vdc=0.3, btest=1))
    cases['btest_osc'] = (64, dict(vdc=0.3, btest=1, osc=1))
    cases['vcm_ext'] = (64, dict(vdc=0.3, vext=1))
    with ThreadPoolExecutor(a.jobs) as ex:
        futs = {k: ex.submit(run_case, out, osdi, k, *c) for k, c in cases.items()}
        w = {k: f.result() for k, f in futs.items()}

    lines, fails = [], []

    def say(s):
        print(s)
        lines.append(s)

    def check(name, ok):
        if not ok:
            fails.append(name)
            say('  FAIL ' + name)

    c = lfsr_codes(131071 + 64)
    cnt = np.bincount(c[:131071], minlength=8)
    say('LFSR reference: repeats after 131071 clocks %s, codes 0 to 7 over one period %s (16383 or 16384 each)'
        % (np.array_equal(c[131071:], c[:64]), cnt.tolist()))
    check('LFSR period', np.array_equal(c[131071:], c[:64]) and cnt.min() >= 16383 and cnt.max() <= 16384)
    say('(a) DC, %d clocks from clock 0, ones density of do_q: ideal 0.5 + vdc/1.5, model, Python, bits equal' % ndc)
    for dith in (0, 1):
        for vdc in dcs:
            bv = sample_bits(w['dc_%+.1f_d%d' % (vdc, dith)], ndc)
            bp = python_bits(ndc, vdc, amp=DITH_A0 if dith else 0.0)
            say('  vdc %+.1f V dither %s: ideal %.5f  model %.5f  Python %.5f  equal %d of %d'
                % (vdc, 'on ' if dith else 'off', 0.5 + vdc / 1.5, bv.mean(), bp.mean(), np.sum(bv == bp), ndc))
            check('dc %+.1f dither %d bits' % (vdc, dith), np.array_equal(bv, bp))

    say('(b) sine %.1f Hz at -6 dBFS (%.4f V), %d clocks, SNR over %d bins after %d settle clocks (psd_bitstream spectrum, split_band)'
        % (fsig, vamp, nsine, nfft, NSETTLE))
    say('    vi held per clock (PWL staircase) unless "continuous"')
    rv = slice(NSETTLE, NSETTLE + nfft)
    for case, dith in (('sine_d0', 0), ('sine_d1', 1), ('sine_cont_d0', 0)):
        bv = sample_bits(w[case], nsine)
        bp = python_bits(nsine, 0.0, vamp, fsig, DITH_A0 if dith else 0.0)
        say('  dither %s%s: model SNR %.2f dB, Python SNR %.2f dB, bits equal %d of %d, ones %.5f / %.5f'
            % ('on ' if dith else 'off', ', continuous' if 'cont' in case else '', snr(bv[rv], ksig), snr(bp[rv], ksig),
               np.sum(bv == bp), nsine, bv.mean(), bp.mean()))
        check(case + ' bits', np.array_equal(bv, bp))
        r = subprocess.run([sys.executable, str(HERE.parent / 'psd_bitstream.py'), 'tb_dsm2_core_va.raw', str(fres), str(NSETTLE)],
                           cwd=out / case, capture_output=True, text=True)
        say('    psd_bitstream.py on the raw: ' + ', '.join(l for l in r.stdout.splitlines() if 'SNR' in l or 'ones' in l))
    r = subprocess.run([sys.executable, str(HERE.parent / 'dsm_system.py'), '--fres', str(fres), '--noiseless', '--settle', str(NSETTLE),
                        '-o', str(out / 'psd_system.csv')], capture_output=True, text=True)
    say('  dsm_system.py --fres %g --noiseless --settle %d (dither off): ' % (fres, NSETTLE)
        + ', '.join(l for l in r.stdout.splitlines() if 'SNR' in l or 'density' in l))

    say('(c) controls, vdc +0.3 V unless named, expected values in brackets')
    for code in trims:
        x = w['osc_%d' % code]
        tr = rising(x, 'v(do_clk_osc)', 20e-6)
        f, fx, dq = 1 / np.mean(np.diff(tr)), OSC_SCALE * OSC_F[code], tmean(x, 'v(do_q)', 20e-6)
        say('  di_osc_en and di_clk_sel high, di_trim %2d: do_clk_osc %.1f kHz (%.1f), do_osc_oe %.3f V (1.5), do_q time average %.4f (0.7)'
            % (code, 1e-3 * f, 1e-3 * fx, x['v(do_osc_oe)'][-1], dq))
        check('osc %d' % code, abs(f / fx - 1) < 1e-3 and abs(x['v(do_osc_oe)'][-1] - VSUP) < 1e-3 and abs(dq - 0.7) < 0.01)
    x = w['reset']
    b, br = sample_bits(x, 80), reset_bits(80, 0.3, 20)
    run = int(np.argmin(b[20:]))
    qmax = x['v(do_q)'][x['time'] < 20.5 / FS].max()
    say('  di_rst_b released before clock 20: do_q in reset max %.3f V (0), then %d ones before the first 0 (%d), bits equal %d of 80'
        % (qmax, run, int(np.argmin(br[20:])), np.sum(b == br)))
    check('reset', qmax < 1e-3 and np.array_equal(b, br))
    x = w['qout_off']
    bd = sample_bits(x, 64, 'v(do_q_dec)')
    say('  di_qout_en low: do_q max %.3f V (0), do_q_b max %.3f V (0), do_q_dec bits equal Python %d of 64'
        % (x['v(do_q)'].max(), x['v(do_q_b)'].max(), np.sum(bd == python_bits(64, 0.3))))
    check('qout_off', x['v(do_q)'].max() < 1e-3 and x['v(do_q_b)'].max() < 1e-3 and np.array_equal(bd, python_bits(64, 0.3)))
    x = w['ena_off']
    say('  di_ena low, di_qout_en high: do_q max %.3f V (0), do_q_b min %.3f V (1.5), do_q_dec max %.3f V (0), vcm max %.4f V (0, undriven)'
        % (x['v(do_q)'].max(), x['v(do_q_b)'].min(), x['v(do_q_dec)'].max(), np.abs(x['v(vcm)']).max()))
    check('ena_off', x['v(do_q)'].max() < 1e-3 and x['v(do_q_b)'].min() > VSUP - 1e-3 and x['v(do_q_dec)'].max() < 1e-3
          and np.abs(x['v(vcm)']).max() < 1e-3)
    ib, ibo = 1e9 * w['btest']['i(vib)'][-1], 1e9 * w['btest_osc']['i(vib)'][-1]
    say('  di_btest_en high, code 4: %.2f nA out of ibias_test into 0.5 V (199.92). With di_osc_en high too: %.2f nA (0)' % (ib, ibo))
    check('btest', abs(ib / 199.92 - 1) < 1e-3 and abs(ibo) < 0.01)
    v_ext, v_int = np.abs(w['vcm_ext']['v(vcm)']).max(), w['qout_off']['v(vcm)'][-1]
    say('  di_vcm_ext high, nothing driving vcm: vcm max %.4f V (0, undriven). With di_vcm_ext low: %.6f V (0.75)' % (v_ext, v_int))
    check('vcm', v_ext < 1e-3 and abs(v_int - 0.75) < 1e-5)
    say('PASS' if not fails else 'FAIL: ' + ', '.join(fails))
    (out / 'summary.txt').write_text('\n'.join(lines) + '\n')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
