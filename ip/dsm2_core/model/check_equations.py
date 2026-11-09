#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Recompute the closed-form values of equations.md and compare them with the values the repo files state.

Needs numpy only and imports dsm_system.py from this folder. Prints the comparison table and exits 1 on any mismatch.
About 10 minutes, most of it in the dead zone runs.

usage: check_equations.py
"""
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsm_system as dsm  # noqa: E402

ROWS = []


def chk(name, got, ref, tol, src):
    """tol is relative unless ref is 0."""
    ok = abs(got - ref) <= tol * (abs(ref) if ref else 1.0)
    ROWS.append((name, got, ref, ok, src))


# 1. Specification
VDD, V_LSB, FB = 1.5, 1e-3, 1e3
V_FS, V_REF, VCM = VDD, VDD / 2, VDD / 2
ENOB = np.log2(V_FS / V_LSB)
SQNR_SPEC = 6.02 * ENOB + 1.76
N_Q = 1
K_NTF1 = 10 * np.log10(3 / np.pi ** 2)
OSR_MIN = 10 ** ((SQNR_SPEC - 6.02 * N_Q - 1.76 - K_NTF1) / 30)
OSR = 2 ** np.ceil(np.log2(OSR_MIN)) * 4
FS = 2 * FB * OSR
SQNR_OSR = 6.02 * N_Q + 1.76 + K_NTF1 + 30 * np.log10(OSR)
V_SIG = V_REF / np.sqrt(2)
V_TH = V_LSB / np.sqrt(12)
V_Q = V_SIG * 10 ** (-SQNR_OSR / 20)
SNR_PRED = 10 * np.log10(V_SIG ** 2 / (V_Q ** 2 + V_TH ** 2))
SNR_EQ = 10 * np.log10(V_SIG ** 2 / (2 * V_TH ** 2))
chk('ENOB (bit)', ENOB, 10.55, 1e-3, 'model/README.md Setup')
chk('OSR', OSR, 512, 0, 'model/README.md Setup')
chk('fs (Hz)', FS, 1.024e6, 0, 'model/README.md Setup')
chk('v_th budget (uV)', V_TH * 1e6, 288.68, 1e-4, 'dsm_system.py --dither help')
chk('SQNR_spec for n_slin (dB)', SQNR_SPEC, 65.3, 1e-3, 'size_sc_int2.ipynb cell 15 output')
# ratiometric: vcm and the DAC levels follow vdd
for vdd_x, ref in ((1.45, 0.4138), (1.55, 0.3871)):
    chk('bit mean at vi - vcm = 0.3 V, vdd %.2f V' % vdd_x, 0.3 / (vdd_x / 2), ref, 2e-4, 'dsm2_README.md Corners')
print('spec: ENOB %.4f, SQNR_spec %.3f dB, OSR_min %.2f, OSR %d, fs %.0f Hz' % (ENOB, SQNR_SPEC, OSR_MIN, OSR, FS))
print('      SQNR(OSR) %.3f dB, v_sig %.4f V, v_th %.3f uV, v_q %.2f uV, SNR pred %.2f dB, SNR(v_q = v_th) %.2f dB'
      % (SQNR_OSR, V_SIG, V_TH * 1e6, V_Q * 1e6, SNR_PRED, SNR_EQ))

# 2. Loop
H_INF = 1.2
P0 = 2 / H_INF - 1          # NTF pole of (z-1)/(z-p0) with |NTF(-1)| = H_inf
A1 = 1 - P0
B1, C1C = A1, 1.0
# a1 as dsm_system.py main computes it, read from its source
try:
    _m = re.search(r'^\s*a1 = (.+)$', open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dsm_system.py')).read(), re.M)
    _a1_repo = eval(_m.group(1), {}, {'a': type('Args', (), {'hinf': H_INF})})
    chk('a1 of dsm_system.py main at H_inf 1.2', _a1_repo, A1, 1e-12, 'dsm_system.py main')
except Exception as exc:
    # a changed source line fails the row instead of stopping the script
    ROWS.append(('a1 of dsm_system.py main at H_inf 1.2', float('nan'), A1, False, 'dsm_system.py main, read failed: %s' % exc))
chk('a1', A1, 1 / 3, 1e-12, 'model/README.md Setup')
ABCD = np.array([[1, B1, -A1], [C1C, 0, 0]])
w = np.linspace(1e-3, np.pi, 20001)
z = np.exp(1j * w)


def tf(abcd, z, p=None):
    a = abcd[0, 0] if p is None else p
    l0 = abcd[1, 0] * abcd[0, 1] / (z - a) + abcd[1, 1]
    l1 = abcd[1, 0] * abcd[0, 2] / (z - a) + abcd[1, 2]
    ntf = 1 / (1 - l1)
    return ntf, l0 * ntf


ntf, stf = tf(ABCD, z)
chk('max |NTF| on unit circle', np.max(np.abs(ntf)), H_INF, 1e-9, 'H_inf 1.2, model/README.md')
chk('NTF from ABCD = (z-1)/(z-2/3)', np.max(np.abs(ntf - (z - 1) / (z - 2 / 3))), 0, 1e-12, 'derived')
chk('STF from ABCD = (1/3)/(z-2/3)', np.max(np.abs(stf - (1 / 3) / (z - 2 / 3))), 0, 1e-12, 'derived')
chk('STF(1), limit z -> 1', abs(tf(ABCD, np.array([1.0 + 1e-9 + 0j]))[1][0]), 1.0, 1e-6, 'derived')
fb_w = np.pi / OSR
print('NTF at f_b: %.4e (k=1), %.4e (k=3); STF at f_b %.6f, phase %.4f rad'
      % (abs((np.exp(1j * fb_w) - 1) / (np.exp(1j * fb_w) - 2 / 3)), abs(1 - np.exp(-1j * fb_w)),
         abs((1 / 3) / (np.exp(1j * fb_w) - 2 / 3)), np.angle((1 / 3) / (np.exp(1j * fb_w) - 2 / 3))))

# bit stream invariance under a1 scaling, with leak and dither
rng = np.random.default_rng(1)
n = 1 << 16
u = 0.5 * np.sin(2 * np.pi * 37 / n * np.arange(n)) + rng.standard_normal(n) * 0.01
d = 0.1 * (2.0 * rng.integers(0, 8, n) - 7) / 7
pl = 1 - 2.72e-4


def bits(a1, scale):
    x, v = 0.0, np.empty(n)
    for k in range(n):
        v[k] = 1.0 if x + d[k] * scale >= 0 else -1.0
        x = pl * x + a1 * (u[k] - v[k])
    return v


diff = np.count_nonzero(bits(A1, 1.0) != bits(1.0, 1 / A1))
chk('bits a1=1/3 vs a1=1 (dither scaled by 1/a1), differing', diff, 0, 0, 'derived')

# 3. In-band quantization noise
W = np.pi / OSR
for delta, tag in ((1.0, 'Delta = V_REF (formula)'), (2.0, 'Delta = 2 V_REF (levels +-1)')):
    s2 = delta ** 2 / 12
    nq_exact = s2 / np.pi * (2 * W - 2 * np.sin(W))
    nq_appr = s2 * np.pi ** 2 / (3 * OSR ** 3)
    print('in-band q-noise, %s: exact %.4e, approx %.4e, SQNR %.3f dB, rms %.2f uV'
          % (tag, nq_exact, nq_appr, 10 * np.log10(0.5 / nq_exact), np.sqrt(nq_exact) * V_REF * 1e6))
    if delta == 1.0:
        chk('SQNR formula vs exact integral (dB)', 10 * np.log10(0.5 / nq_exact), SQNR_OSR, 2e-3, 'derived')
        # tolerance 0.16 dB, the page flags the 0.13 dB gap
        chk('SQNR at -6 dBFS (dB), tol 0.16 dB', SQNR_OSR - 6.02, 78.0, 2e-3, 'dsm2_README.md In-band SNDR, 78.0 dB ideal')
# leak floor
for a0db, tag in ((50.0, '50 dB'), (-20 * np.log10(2.72e-4), 'leak 2.72e-4'), (-20 * np.log10(3.41e-4), 'leak 3.41e-4')):
    p = 1 - 10 ** (-a0db / 20)
    ww = np.linspace(0, W, 200001)
    zz = np.exp(1j * ww)
    ntf_n = (zz - p) / (zz - p + 1)
    nq_l = getattr(np, 'trapezoid', getattr(np, 'trapz', None))(np.abs(ntf_n) ** 2, ww) / np.pi
    nq_0 = (2 * W - 2 * np.sin(W)) / np.pi
    appr = (1 - p) ** 2 / OSR + p * np.pi ** 2 / (3 * OSR ** 3)
    print('leak %s: 1-p %.3e, in-band |NTF|^2 exact %.4e, approx %.4e, ideal %.4e, SQNR loss %.2f dB'
          % (tag, 1 - p, nq_l, appr, nq_0, 10 * np.log10(nq_l / nq_0)))
    chk('leak NTF approx, %s' % tag, appr, nq_l, 2e-2, 'derived')

# simulated SQNR of the ideal loop at -6 dBFS, 2^20 samples, Hann, 5-bin tone
nfft = 1 << 20
ksig = 687
assert np.gcd(ksig, nfft) == 1
ut = 10 ** (-6 / 20) * np.sin(2 * np.pi * ksig / nfft * np.arange(nfft + 160))
ut += np.random.default_rng(1).standard_normal(ut.size) * (13e-6 / V_REF) * np.sqrt(OSR)
res = dsm.run_loop1(ut.size, 0.0, 1.0, A1, None, ut, None, None, None, None, [0], 160)
vb = res['bits'][160:, 0].astype(float)
win = np.hanning(nfft)
sp = np.fft.rfft(vb * win) / (win.sum() / 2)
f = np.fft.rfftfreq(nfft, 1 / FS)
band = (f > 0) & (f <= FB)
sig = np.arange(ksig - 2, ksig + 3)
band[sig] = False
band[:3] = False
snr_sim = 10 * np.log10(np.sum(np.abs(sp[sig]) ** 2) / np.sum(np.abs(sp[band]) ** 2))
print('ideal loop sim, -6 dBFS, 13 uV in-band dither, 2^20 samples: SNR %.2f dB' % snr_sim)
chk('ideal loop SQNR at -6 dBFS (dB)', snr_sim, 74.9, 1.3 / 74.9, 'dsm2_README.md, 74.9 +- 1.3 dB ideal loop without dither')

# 4. SC realisation
KB, T = 1.38e-23, 300
C1, C2 = 64e-15, 384e-15
C1M, C2M, CGG = 87.954e-15, 527.724e-15, 40.5e-15
chk('a1 = 2 C1/C2', 2 * C1 / C2, A1, 1e-12, 'sc_int2_README.md Capacitors')
chk('C1_min kT/C (fF)', KB * T / (OSR * V_TH ** 2) * 1e15, 0.097, 5e-3, 'size_sc_int2.ipynb cell 7')
chk('kT/C1 in band (uV)', np.sqrt(KB * T / (C1 * OSR)) * 1e6, 11.24, 1e-3, 'sc_int2_README.md line 288')
chk('kT/C1 in band, model C1 (uV)', np.sqrt(KB * T / (C1M * OSR)) * 1e6, 9.59, 1e-3, 'size_sc_int2.ipynb cell 11')
print('dsm_system kT/C term sqrt(2kT/(OSR C1)): %.2f uV' % (np.sqrt(2 * dsm.K_B * dsm.TEMP / (OSR * C1)) * 1e6))
print('kT/C1 density: %.1f nV/rtHz' % (np.sqrt(KB * T / (C1 * OSR)) / np.sqrt(FB) * 1e9))
chk('kT/C1 density (nV/rtHz)', np.sqrt(KB * T / (C1 * OSR)) / np.sqrt(FB) * 1e9, 355.6, 1e-3, 'sc_int2_README.md line 288')


def keep(a, c1, c2, cp):
    return (c2 * (1 + a) + cp) / (c1 + c2 * (1 + a) + cp)


a_mod, a_sim = 10 ** (55.3 / 20), 10 ** (58.8 / 20)
chk('leak, charge balance, A 55.3 dB', 1 - keep(a_mod, C1M, C2M, CGG), 2.86e-4, 5e-3, 'size_sc_int2.ipynb cell 20')
chk('leak, charge balance, A 58.8 dB', 1 - keep(a_sim, C1M, C2M, CGG), 1.91e-4, 5e-3, 'size_sc_int2.ipynb cell 20')
chk('leak (C1/C2)/A at 58.29 dB', (1 / 6) / 10 ** (58.29 / 20), 2.03e-4, 5e-3, 'sc_int2_README.md leak bench')
chk('integrator gain from 2.72e-4 (dB)', -20 * np.log10(2.72e-4), 71.3, 1e-3, 'sc_int2_README.md leak bench')
chk('integrator gain from 3.41e-4 (dB)', -20 * np.log10(3.41e-4), 69.3, 1e-3, 'sc_int2_README.md leak bench')
chk('A_OTA min = 50 dB / beta 0.820 (dB)', 50 - 20 * np.log10(0.820), 51.7, 1e-3, 'ota_fcasc2_README.md Sizing')
chk('A_OTA min = 50 dB / beta 0.785 (dB)', 50 - 20 * np.log10(0.785), 52.1, 1e-3, 'ota_fcasc2_README.md Sizing')
a_ota = 10 ** (58.8 / 20)
beta_r = C2 / (C1 + C2 + CGG)
print('integrator gain at A_OTA 58.8 dB: beta map %.1f dB, charge-balance map %.1f dB'
      % (20 * np.log10(beta_r * a_ota), 20 * np.log10(a_ota * C2 / C1)))

chk('static error 1/(1+beta A) at 51.73 dB, beta 0.820 (%)', 100 / (1 + 0.820 * 10 ** (51.73 / 20)), 0.32, 2e-2, 'ota_fcasc2_README.md CACE err_d limit')
# DC gain of the leaky loop: linear model with k a1 = 1 gives 1/(2-p)
# inputs away from low-order rationals, -0.2 only printed: it sits at the edge of a lock range
uu = np.array([0.1414, 0.3142, -0.4330, 0.6343, -0.2])
nn = 1 << 20
wg = np.zeros(nn)
wg[nn // 8:] = 1.0 / (nn - nn // 8)
for leak in (2.72e-4, 1e-2):
    ge = dsm.run_loop(nn, uu, 1 - leak, A1, w=wg)['acc'] / uu - 1
    print('leaky DC gain, 1-p %.2e: per input %s, 1/(2-p) - 1 = %.3e, (1-p)/a1 = %.3e'
          % (leak, ' '.join('%.3e' % g for g in ge), 1 / (1 + leak) - 1, leak / A1))
    if leak < 1e-3:
        for u_g, g in zip(uu[:4], ge[:4]):
            chk('DC gain error 1-p %.2e, u %+.4f, sim against 1/(2-p)' % (leak, u_g), g, 1 / (1 + leak) - 1, 0.05, 'derived')
    else:
        # lock ranges scale with 1-p, single inputs scatter 10 to 20 % here, so the mean is compared
        chk('DC gain error 1-p %.2e, mean of 4 inputs, sim against 1/(2-p)' % leak, ge[:4].mean(), 1 / (1 + leak) - 1, 0.05, 'derived')

TS2 = 1 / (2 * FS)
T_SLEW = T_LIN = TS2 / 2
EPS = 10 ** (-SQNR_SPEC / 20)
N_TAU = np.ceil(np.log(1 / EPS))
TAU_MAX = T_LIN / N_TAU
chk('n time constants', N_TAU, 8, 0, 'size_sc_int2.ipynb cell 15')
chk('tau max (ns)', TAU_MAX * 1e9, 30.52, 1e-3, 'size_sc_int2_README / cell 15 limit')
print('eps_d %.3e, ln(1/eps) %.3f, Ts/2 %.2f ns, tau_max %.3f ns, w_ug %.4e rad/s, f_ug %.4f MHz'
      % (EPS, np.log(1 / EPS), TS2 * 1e9, TAU_MAX * 1e9, 1 / TAU_MAX, 1 / TAU_MAX / 2 / np.pi / 1e6))
GM1, FO, ID1 = 15.15e-6, 2, 600e-9
for tag, c1, c2, tau_ref, cl_ref, sr_ref in (('real', C1, C2, 17.65, 210, 2.86), ('model', C1M, C2M, 22.92, 279, 2.15)):
    beta = c2 / (c1 + c2 + CGG)
    cl = FO * c1 + c2 * (1 - beta)
    tau = cl / (GM1 * beta)
    chk('tau %s caps (ns)' % tag, tau * 1e9, tau_ref, 5e-3, 'size_sc_int2.ipynb cell 15')
    chk('C_Ltot %s caps (fF)' % tag, cl * 1e15, cl_ref, 5e-3, 'size_sc_int2.ipynb cell 15')
    chk('slew rate %s (V/us)' % tag, ID1 / cl / 1e6, sr_ref, 5e-3, 'size_sc_int2.ipynb cell 15')
    step = A1 * V_REF
    v_lin = ID1 * tau / cl
    t_sl = (step - v_lin) * cl / ID1
    err = v_lin * np.exp(-(TS2 - t_sl) / tau) / step
    print('%s: beta %.4f, C_Ltot %.1f fF, tau %.2f ns, v_lin %.4f V, t_slew %.1f ns, error %.1e'
          % (tag, beta, cl * 1e15, tau * 1e9, v_lin, t_sl * 1e9, err))
chk('beta real caps', C2 / (C1 + C2 + CGG), 0.7861, 1e-3, 'size_sc_int2.ipynb cell 5')
id_script = (C1 + C1 * C2 / (C1 + C2)) * (2 * C1 / C2) * V_REF / T_SLEW
id_fo2 = (2 * C1 + C1 * C2 / (C1 + C2)) * (2 * C1 / C2) * V_REF / T_SLEW
print('Id1_min slewing: %.1f nA with C_L = C1 (size_ota_fcasc2.py), %.1f nA with C_L = 2 C1' % (id_script * 1e9, id_fo2 * 1e9))
x_b = A1 * (1 + 10 ** (-0.5 / 20)) * V_REF
chk('state bound at -0.5 dBFS (V)', x_b, 0.486, 2e-3, 'size_sc_int2.ipynb cell 13')
chk('state step at full scale, differential (V)', 2 * A1 * V_REF, 0.5, 1e-12, 'size_sc_int2.ipynb cell 13')

# 5. Dither
def lfsr_codes(n):
    s = np.zeros(17, np.uint8)
    out = np.empty(n, np.int64)
    for k in range(n):
        nb = [1 ^ s[13 - j] ^ s[16 - j] for j in range(3)]
        out[k] = nb[0] | (nb[1] << 1) | (nb[2] << 2)
        s = np.concatenate(([nb[2], nb[1], nb[0]], s[:-3])).astype(np.uint8)
    return out


def lfsr_bits(n):
    """serial form: b[k] = XNOR(b[k-17], b[k-14]), all-zero start"""
    b = np.zeros(n + 17, np.uint8)
    for k in range(17, n + 17):
        b[k] = 1 ^ b[k - 17] ^ b[k - 14]
    return b[17:]


P_LFSR = 2 ** 17 - 1
codes = lfsr_codes(2 * P_LFSR + 10)
ser = lfsr_bits(3 * 50)
chk('leap-forward = serial bits (first 50 codes)', np.count_nonzero(codes[:50] - (ser[0::3] + 2 * ser[1::3] + 4 * ser[2::3])), 0, 0, 'derived')
per = next(k for k in range(1, len(codes) - P_LFSR) if np.array_equal(codes[k:k + 200], codes[:200]))
chk('code period (clocks)', per, 131071, 0, 'quantizer2_README.md LFSR')
cnt = np.bincount(codes[:P_LFSR], minlength=8)
print('codes per period:', cnt.tolist())
chk('65535/3 (16-bit period)', 65535 / 3, 21845, 0, 'quantizer2_README.md LFSR')
A = 75e-3
lev = A * (2 * np.arange(8) - 7) / 7
chk('dither rms at 75 mV (mV)', np.sqrt(np.mean(lev ** 2)) * 1e3, 49.1, 2e-3, 'size_quantizer2.ipynb cell 23')
chk('code 3 level at 76.5 mV (mV)', abs(76.5 * (2 * 3 - 7) / 7), 11.0, 1e-2, 'quantizer2_README.md Dither')
ratio = (9 / 7) * (A / (A1 * V_REF)) ** 2
print('dither / q-error variance ratio %.4f, %.2f dB more shaped noise; with the 1.5 V step %.3f dB'
      % (ratio, 10 * np.log10(1 + ratio), 10 * np.log10(1 + np.mean(lev ** 2) / 1.5 ** 2 * 12)))
chk('dither / q-error ratio', ratio, 0.12, 4e-2, 'size_quantizer2.ipynb cell 22 text')


# dead zone, noiseless, mean of the bit stream over the last part of a record
def dead_zone(p, amp, half_mv=0.4, step_mv=0.002, n=1 << 17, settle=1 << 15):
    uu = np.arange(-half_mv, half_mv + step_mv / 2, step_mv) * 1e-3 / V_REF
    qd = None if amp == 0 else (amp / V_REF) * (2.0 * lfsr_codes(n) - 7) / 7
    w = np.zeros(n)
    w[settle:] = 1.0 / (n - settle)
    m = dsm.run_loop(n, uu, p, A1, qd=qd, w=w)['acc']
    zero = np.abs(m) < 1e-12
    i0 = np.argmin(np.abs(uu))
    if not zero[i0]:
        return 0.0
    lo = hi = i0
    while lo > 0 and zero[lo - 1]:
        lo -= 1
    while hi < uu.size - 1 and zero[hi + 1]:
        hi += 1
    return (uu[hi] - uu[lo]) * V_REF * 1e3 + step_mv


def dz_formula(p, amp):
    h = (1 - p) * (1 / (1 + p) - (amp / V_REF) / A1)
    return max(2 * h * V_REF * 1e3, 0.0)


for leak in (2.72e-4, 3.41e-4):
    p = 1 - leak
    for amp in (0.0, 76.5e-3, 50.1e-3, 104.4e-3, 23.3e-3):
        sim = dead_zone(p, amp)
        fo = dz_formula(p, amp)
        print('dead zone leak %.2e, A %5.1f mV: formula %.4f mV, noiseless sim %.4f mV' % (leak, amp * 1e3, fo, sim))
        # absolute tolerance: two steps of the 0.002 mV grid
        chk('dead zone leak %.2e A %.1f mV (mV)' % (leak, amp * 1e3), sim, fo, 0.004 / fo, 'derived, sim with dsm_system.run_loop')
p50 = 1 - 10 ** (-50 / 20)
print('dead zone at 50 dB, no dither: %.3f mV' % dz_formula(p50, 0.0))
print('A for no period-2 zone: %.1f mV' % (A1 * V_REF / (1 + (1 - 2.72e-4)) * 1e3))

# idle tone of the ideal loop: spurs at multiples of fs |u|, each with amplitude 2 |u|
for off_mv in (0.25, 0.375, 0.5, 0.75, 1.0, 1.125):
    u_it = off_mv * 1e-3 / V_REF
    nt = 1024000
    vt = dsm.run_loop1(nt + 4096, u_it, 1.0, A1, None, None, None, None, None, None, [0], 0)['bits'][4096:, 0].astype(float)
    wt = np.hanning(nt)
    st = np.fft.rfft((vt - vt.mean()) * wt) / (wt.sum() / 2)
    ft = np.fft.rfftfreq(nt, 1 / FS)
    f1 = FS * u_it

    def amp_at(k):
        # power of 5 bins over the Hann noise bandwidth, free of scalloping
        return np.sqrt(np.sum(np.abs(st[k - 2:k + 3]) ** 2) / 1.5)

    kt = 3 + np.argmax(np.abs(st[3:20001]))
    k1 = int(round(f1 * nt / FS))
    mult = ft[kt] / f1
    print('idle tone %.3f mV: fs |u| = %.1f Hz at %.2f dBFS, largest spur below 20 kHz %.0f Hz = %.2f x fs |u| at %.2f dBFS, 2|u| = %.2f dBFS'
          % (off_mv, f1, 20 * np.log10(amp_at(k1)), ft[kt], mult, 20 * np.log10(amp_at(kt)), 20 * np.log10(2 * u_it)))
    # absolute tolerance 0.01 dB
    chk('idle tone %.3f mV, spur at fs |u| (dBFS)' % off_mv, 20 * np.log10(amp_at(k1)), 20 * np.log10(2 * u_it), 0.01 / abs(20 * np.log10(2 * u_it)), 'derived, 2 |u|')
    chk('idle tone %.3f mV, largest spur < 20 kHz over fs |u|' % off_mv, mult, round(mult), 0.01, 'derived, a multiple of fs |u|')
    chk('idle tone %.3f mV, largest spur < 20 kHz (dBFS)' % off_mv, 20 * np.log10(amp_at(kt)), 20 * np.log10(2 * u_it), 0.01 / abs(20 * np.log10(2 * u_it)), 'derived, 2 |u|')
chk('idle tone in band below (mV)', FB / FS * V_REF * 1e3, 0.732, 1e-3, 'derived, measurement_plan.md 3.6 says about 1.5 mV')

# 6. Decimation
R = int(OSR)
wts = dsm.sinc2_weights(R, 16)
chk('sinc2 weights sum', wts.sum(), 1.0, 1e-12, 'dsm_system.py sinc2_weights')
chk('record per DC point (clocks)', wts.size, (16 + 2) * R, 0, 'dsm_system.py dc_sweep')
vv = np.sign(np.random.default_rng(2).standard_normal(20 * R))
tri = np.convolve(np.ones(R), np.ones(R)) / R ** 2
direct = np.convolve(vv, tri)[R - 1::R][:20]
chk('sinc2_stream = convolution with tri', np.max(np.abs(dsm.sinc2_stream(vv, R)[:20] - direct)), 0, 1e-12, 'dsm_system.py sinc2_stream')
chk('sum(w v) = mean of outputs 2..17', abs(np.dot(wts, vv[:wts.size]) - dsm.sinc2_stream(vv[:wts.size], R)[2:18].mean()), 0, 1e-12, 'dsm_system.py sinc2_weights')
hf = lambda f: (np.sin(np.pi * f * R / FS) / (R * np.sin(np.pi * f / FS))) ** 2
print('sinc2 |H| at 1 kHz %.4f (%.2f dB), at fs/2 %.2e, output rate %.0f Hz' % (hf(1e3), 20 * np.log10(hf(1e3)), hf(FS / 2), FS / R))

# 7. Noise budget
nwh = np.random.default_rng(3).standard_normal(1 << 20) * V_TH * np.sqrt(OSR)
spw = np.fft.rfft(nwh) / nwh.size
fr = np.fft.rfftfreq(nwh.size, 1 / FS)
inb = np.sqrt(2 * np.sum(np.abs(spw[(fr > 0) & (fr <= FB)]) ** 2))
chk('white per-sample sigma*sqrt(OSR) lands v_th in band (uV)', inb * 1e6, V_TH * 1e6, 1e-2, 'dsm_system.py add_noise')
chk('per-sample sigma (mV)', V_TH * np.sqrt(OSR) * 1e3, 6.532, 1e-3, 'derived')
tot = np.sqrt(11.24 ** 2 + 25.63 ** 2 + 8.38 ** 2)
chk('budget total, kT/C + OTA/2 + folded (uV)', tot, 29.21, 2e-3, 'sc_int2_README.md Which referral holds')
chk('OTA term vn_d/2 (uV)', 51.26 / 2, 25.63, 1e-4, 'sc_int2_README.md Which referral holds')
chk('budget total with vn_d 50.32 uV (uV)', np.sqrt(11.24 ** 2 + (50.32 / 2) ** 2 + 8.38 ** 2), 28.8, 2e-3, 'ota_fcasc2_README.md vn_d')
chk('beta map at 58.8 dB, beta 0.785 (dB)', 58.8 + 20 * np.log10(0.785), 56.7, 1e-3, 'derived')
chk('pnoise worst vs budget (dB)', 20 * np.log10(288.7 / 35.34), 18.2, 3e-3, 'sc_int2_README.md Noise over Operating Points')
chk('pnoise tt vs budget (dB)', 20 * np.log10(288.7 / 28.0), 20.3, 3e-3, 'sc_int2_README.md Result')
dflt = np.sqrt((2 * dsm.K_B * dsm.TEMP / (OSR * C1)) + 130.30e-6 ** 2 + 892.95e-6 ** 2)
print('dsm_system defaults in band: total %.1f uV' % (dflt * 1e6))
snr_c = 20 * np.log10(V_SIG / np.sqrt((28.64e-6) ** 2 + V_Q ** 2))
print('SNR at 0 dBFS with pnoise 28.64 uV and v_q %.1f uV: %.2f dB' % (V_Q * 1e6, snr_c))

print('\n%-58s %14s %14s  ok  source' % ('check', 'recomputed', 'repo'))
for name, got, ref, ok, src in ROWS:
    print('%-58s %14.6g %14.6g  %s  %s' % (name, got, ref, 'yes' if ok else 'NO ', src))
nfail = sum(not r[3] for r in ROWS)
print('%d checks, %d failed' % (len(ROWS), nfail))
sys.exit(1 if nfail else 0)
