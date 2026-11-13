# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Sizing of ota_fcasc2: the system-level OTA design point (settling budget, input pair, cascode stack, bias, power), then the unit-device design point.

Run from the repo root or from this folder with a Python that has pygmid, numpy and deltasigma:
    python ip/dsm2_core/sizing/size_ota_fcasc2.py [--point equal_l|current] [--compare]
Every number printed here is a gm/ID model estimate, the simulated values are in the README.
"""
from pathlib import Path

import numpy as np
import deltasigma as ds
from pygmid import Lookup as lk

TABLES = Path(__file__).resolve().parent / 'data'
nmos = lk(str(TABLES / 'sg13cmos5l_lv_nmos.mat'))
pmos = lk(str(TABLES / 'sg13cmos5l_lv_pmos.mat'))


def head(s):
    print('\n' + s + '\n' + '-' * len(s))


# System level: 1 mV LSB on 1.5 V, OSR 512, first-order CIFB at H_inf 1.2, C1 = 64 fF
vdd = 1.5
v_lsb = 1e-3
v_fs = vdd
v_ref = v_fs / 2
enob_spec = np.log2(v_fs / v_lsb)
sqnr_peak_spec = 6.02 * enob_spec + 1.76
dsm_osr = 512
dsm_fb = 1000
dsm_fs = 2 * dsm_fb * dsm_osr
ntf = ds.synthesizeNTF(1, dsm_osr, H_inf=1.2)
a, g, b, c = ds.realizeNTF(ntf, form='CIFB')
a1, c1 = np.ravel(a)[0], np.ravel(c)[0]
ABCD = np.array([[1, np.ravel(b)[0], -a1], [c1, 0, 0]], dtype=float)
cap1 = 64e-15
cap2 = 2 * cap1 / a1
temp_k = 300
k_b = 1.38e-23

head('System')
print(f'a1 = {a1:.4f}, C1 = {cap1 * 1e15:.1f} fF, C2 = {cap2 * 1e15:.1f} fF, fs = {dsm_fs / 1e6:.3f} MHz')

# Integrator swing: the state of the ideal modulator at -0.5 dBFS with the thermal noise budget added, seed 1
n_fft = int(dsm_fs)
np.random.seed(1)
nvec = np.arange(n_fft)
u = ds.undbv(-0.5) * np.sin(2 * np.pi * 500 / dsm_fs * nvec)
u += np.random.randn(n_fft) * (v_lsb / np.sqrt(12) / v_ref) * np.sqrt(dsm_osr)
_, _, xmax, _ = ds.simulateDSM(u, ABCD, nlev=2, x0=0)
x_swing = float(np.max(xmax)) * v_ref
print(f'Integrator swing = {x_swing:.3f} V peak differential, {2 * x_swing:.3f} Vpp differential')

# Settling budget
head('System-level design point')
tsettle = 1 / dsm_fs / 2
tslew = tsettle / 2
tslin = tsettle - tslew
n_slin = np.round(np.log(10 ** (sqnr_peak_spec / 20)))
tau = tslin / n_slin
wug = 1 / tau
fug = wug / 2 / np.pi
capltot_est = cap1 + cap1 * cap2 / (cap1 + cap2)
id1_min = capltot_est * (2 * cap1 / cap2) * v_ref / tslew
print(f'Ts/2 = {tsettle * 1e9:.1f} ns, tslew = tslin = {tslew * 1e9:.1f} ns, n = {n_slin:.0f}')
print(f'tau <= {tau * 1e9:.2f} ns, fug >= {fug / 1e6:.3f} MHz, Id1_min (slewing) = {id1_min * 1e9:.1f} nA')

# The system-level leaky-integrator sweep selects 50 dB (deadzone 4.3 LSB), not rerun here
A0_int_dB = 50.0

# Input pair
l1, gm_id_1, fanout = 1.0, 25, 2
gain = cap1 / cap2
beta_max = 1 / (1 + gain)
wt1 = pmos.lookup('GM_CGG', GM_ID=gm_id_1, VDS=0.75, L=l1)
beta_nb = (1 - (1 + fanout * gain) * wug / wt1) / (1 + gain - wug / wt1)
capltot = fanout * cap1 + cap2 * (1 - beta_nb)
gm1_min = capltot * wug / beta_nb
gm_scale = 2
gm1_nb = gm1_min * gm_scale
id1_nb = gm1_nb / gm_id_1
jd1 = pmos.lookup('ID_W', GM_ID=gm_id_1, VDS=0.75, L=l1)
w1_nb = id1_nb / jd1
tau_nb = capltot / (gm1_nb * beta_nb)
a0_ota_min = 10 ** (A0_int_dB / 20) / beta_nb
print(f'beta_max = {beta_max:.4f}, beta = {beta_nb:.4f} (at the target wug), wt1/wug = {wt1 / wug:.2f}')
print(f'gm1 = {gm1_nb * 1e6:.2f} uS, Id1 = {id1_nb * 1e9:.1f} nA, W1 = {w1_nb:.2f} um, L1 = {l1} um, tau = {tau_nb * 1e9:.2f} ns')
print(f'A0 (integrator) = {A0_int_dB:.1f} dB, A0 (OTA, min) = {20 * np.log10(a0_ota_min):.2f} dB')

# Cascode stack at the chosen point
l23 = l45 = 2.0
gm_id_casc, gm_id_csrc = 25, 18
vd_marg = 50e-3
vds25 = 2 / gm_id_csrc + vd_marg
vds34 = vdd / 2 - vds25
vds34_min = 2 / gm_id_casc + vd_marg
vod_swing_design = 2 * (vdd - (2 * vds34_min + 2 * vds25))


def stack_gain(gm1, id1, i5, gmid1, gm_id_n2, l2, vds2, gm_id_n3, gm_id_p4, gm_id_p5, lp1=l1, l3=l23, lp=l45):
    """Folded cascode dc gain and wp2 as in the system-level design point, with the sink current id1 + i5 and the output branch i5."""
    gm3 = gm_id_n3 * i5
    gm4 = gm_id_p4 * i5
    gm5 = gm_id_p5 * i5
    i2 = id1 + i5
    gm2 = gm_id_n2 * i2
    gds1 = gm1 / pmos.lookup('GM_GDS', GM_ID=gmid1, VDS=0.75, VSB=0, L=lp1)
    gds2 = gm2 / nmos.lookup('GM_GDS', GM_ID=gm_id_n2, VDS=vds2, VSB=0, L=l2)
    gds3 = gm3 / nmos.lookup('GM_GDS', GM_ID=gm_id_n3, VDS=vds34, VSB=vds2, L=l3)
    gds4 = gm4 / pmos.lookup('GM_GDS', GM_ID=gm_id_p4, VDS=vds34, VSB=vds25, L=lp)
    gds5 = gm5 / pmos.lookup('GM_GDS', GM_ID=gm_id_p5, VDS=vds25, VSB=0, L=lp)
    gmb3 = gm3 / nmos.lookup('GM_GMB', GM_ID=gm_id_n3, VDS=vds34, VSB=vds2, L=l3)
    w1 = id1 / pmos.lookup('ID_W', GM_ID=gmid1, VDS=0.75, L=lp1)
    w2 = i2 / nmos.lookup('ID_W', GM_ID=gm_id_n2, VDS=vds2, VSB=0, L=l2)
    w3 = i5 / nmos.lookup('ID_W', GM_ID=gm_id_n3, VDS=vds34, VSB=vds2, L=l3)
    cdd1 = pmos.lookup('CDD_W', GM_ID=gmid1, VDS=0.75, L=lp1) * w1
    cdd2 = nmos.lookup('CDD_W', GM_ID=gm_id_n2, VDS=vds2, VSB=0, L=l2) * w2
    css3 = nmos.lookup('CSS_W', GM_ID=gm_id_n3, VDS=vds34, VSB=vds2, L=l3) * w3
    wp2 = (gm3 + gmb3) / (cdd1 + cdd2 + css3)
    r23 = gm3 / gds3 / (gds1 + gds2)
    r45 = gm4 / gds4 / gds5
    rout = 1 / (1 / r23 + 1 / r45)
    return gm1 * rout, wp2


a0_nb, wp2_nb = stack_gain(gm1_nb, id1_nb, id1_nb, gm_id_1, gm_id_csrc, l23, vds25, gm_id_casc, gm_id_casc, gm_id_csrc)
w2 = 2 * id1_nb / nmos.lookup('ID_W', GM_ID=gm_id_csrc, VDS=vds25, VSB=0, L=l23)
w3 = id1_nb / nmos.lookup('ID_W', GM_ID=gm_id_casc, VDS=vds34, VSB=vds25, L=l23)
w4 = id1_nb / pmos.lookup('ID_W', GM_ID=gm_id_casc, VDS=vds34, VSB=vds25, L=l45)
w5 = id1_nb / pmos.lookup('ID_W', GM_ID=gm_id_csrc, VDS=vds25, VSB=0, L=l45)
print(f'A0 = {20 * np.log10(a0_nb):.1f} dB, wp2/wug = {wp2_nb * tau_nb:.1f}, Vo,pp,diff = {vod_swing_design:.3f} V')
print(f'W2 = {w2:.2f} um, W3 = {w3:.2f} um, W4 = {w4:.2f} um, W5 = {w5:.2f} um, all at L = 2 um')

# Bias and power
iref_scale = 1 / 2
print(f'Iref = {id1_nb * iref_scale * 1e9:.1f} nA, Wvbn = {w2 * iref_scale / 2:.2f} um, Wvcn = {w3 * iref_scale:.2f} um, '
      f'Wvbp = {w5 * iref_scale:.2f} um, Wvcp = {w4 * iref_scale:.2f} um, Wtail = {w5 / iref_scale:.2f} um, Wtailc = {w4 / iref_scale:.2f} um')
itot_nb = 5 * id1_nb
print(f'Itot = 5*Id1 = {itot_nb * 1e6:.3f} uA, Ptot = {vdd * itot_nb * 1e6:.2f} uW')

# The system-level beta, evaluated at the target wug, against the beta with the Cgg of the pair it actually sizes
beta_real = cap2 / (cap1 + cap2 + gm1_nb / wt1)
print(f'beta with Cgg1 = gm1/wt1 = {gm1_nb / wt1 * 1e15:.1f} fF: {beta_real:.4f} (the system-level value assumes gm1_min)')

# Unit-device design points
I_U = 200e-9   # every branch is an integer multiple of the 200 nA input


def gmid_at(dev, w, l, i, vds, vsb=0.0):
    """gm/ID of a unit of width w and length l carrying i."""
    gmid = np.arange(4, 30, 0.01)
    j = dev.lookup('ID_W', GM_ID=gmid, VDS=vds, VSB=vsb, L=l)
    return float(np.interp(i / w, j[::-1], gmid[::-1]))


# Unit (W, L) in um per type. 'equal_l' is the design: one L for every NMOS, one L for every PMOS except the
# input pair and MPR. 'current' is the point before that rule (NMOS sources 0.5/4, NMOS cascodes 1/2), kept for comparison.
POINTS = {
    'equal_l': dict(nsrc=(0.5, 3), ncasc=(0.5, 3), nen=(0.5, 3), psrc=(1, 2), pcasc=(3.5, 2), pen=(1, 2), pin=(2, 1)),
    'current': dict(nsrc=(0.5, 4), ncasc=(1, 2), nen=(1, 0.5), psrc=(1, 2), pcasc=(3.5, 2), pen=(1.5, 0.5), pin=(2, 1)),
}
# The other equal-L candidates checked in simulation (README, Sizing), for --compare
CANDIDATES = {
    'N all 0.5/2': dict(nsrc=(0.5, 2), ncasc=(0.5, 2)),
    'N 0.5/3, casc 1/3': dict(nsrc=(0.5, 3), ncasc=(1, 3)),
    'N 0.5/4, casc 1/4': dict(nsrc=(0.5, 4), ncasc=(1, 4)),
    'N all 0.5/4': dict(nsrc=(0.5, 4), ncasc=(0.5, 4)),
    'P casc 1/2': dict(pcasc=(1, 2)),
    'P casc 2/2': dict(pcasc=(2, 2)),
    'P 0.5/1, casc 2/1': dict(psrc=(0.5, 1), pcasc=(2, 1)),
    'pair 2/2': dict(pin=(2, 2)),
    'pair 4/2': dict(pin=(4, 2)),
}
PLVL = (0.5, 10.0)   # MPR, the triode enable switch of the PMOS bias branch, outside the equal-L rule
DEV = dict(nsrc=nmos, ncasc=nmos, psrc=pmos, pcasc=pmos, pin=pmos)
# current per unit, VDS, VSB for the gm/ID lookup
BIAS = dict(nsrc=(I_U, 0.3, 0.0), ncasc=(I_U, vds34, 0.3), psrc=(I_U, 0.15, 0.0), pcasc=(I_U, vds34, 0.15), pin=(150e-9, 0.75, 0.0))

# Branch currents in units of 200 nA
n_tail, n_out, n_fold, n_ref = 6, 5, 8, 1
id1 = n_tail * I_U / 2
i5 = n_out * I_U
i_fold = n_fold * I_U
i_bias = n_ref * I_U   # PMOS reference branch, the 200 nA input comes on top from the reference
assert abs(i_fold - (id1 + i5)) < 1e-12


def evaluate(pt):
    """Model point of one unit set: gm/ID per unit, tau, A0, swing, power."""
    g = {k: gmid_at(DEV[k], *pt[k], *BIAS[k]) for k in DEV}
    l_pin, l_ns, l_nc, l_p = pt['pin'][1], pt['nsrc'][1], pt['ncasc'][1], pt['psrc'][1]
    gm1 = g['pin'] * id1
    cgg1 = gm1 / pmos.lookup('GM_CGG', GM_ID=g['pin'], VDS=0.75, L=l_pin)
    beta = cap2 / (cap1 + cap2 + cgg1)
    tau = (fanout * cap1 + cap2 * (1 - beta)) / (gm1 * beta)
    vgs5 = float(nmos.lookupVGS(GM_ID=g['nsrc'], VDS=0.3, VSB=0, L=l_ns))
    a0, wp2 = stack_gain(gm1, id1, i5, g['pin'], g['nsrc'], l_ns, vgs5, g['ncasc'], g['pcasc'], g['psrc'],
                         lp1=l_pin, l3=l_nc, lp=l_p)
    # Stacked NMOS diodes put the sinks at VGS5, the wide-swing PMOS bias puts the loads at about vds25
    vo_min = vgs5 + 2 / g['ncasc'] + vd_marg
    vo_max = vdd - vds25 - 2 / g['pcasc'] - vd_marg
    itot = 2 * id1 + 2 * i5 + i_bias
    return dict(gmid=g, gm1=gm1, cgg1=cgg1, beta=beta, tau=tau, vgs5=vgs5, a0=a0, wp2=wp2, vo_min=vo_min, vo_max=vo_max,
                swing=2 * (vo_max - vo_min), itot=itot)


# name, block, type, units, function, branch current per device
DEVICES = [
    ('MP1', 'dp', 'pin', 4, 'input pair', id1), ('MP2', 'dp', 'pin', 4, 'input pair', id1),
    ('MPD1', 'dp', 'pin', 2, 'dummy', 0),
    ('MP3', 'pbiascasc', 'psrc', 6, 'tail source', 2 * id1), ('MP10', 'pbiascasc', 'pcasc', 6, 'tail cascode', 2 * id1),
    ('MP4', 'pbiascasc', 'psrc', 5, 'load source', i5), ('MP5', 'pbiascasc', 'psrc', 5, 'load source', i5),
    ('MP6', 'pbiascasc', 'pcasc', 5, 'load cascode', i5), ('MP7', 'pbiascasc', 'pcasc', 5, 'load cascode', i5),
    ('MP8', 'pbiascasc', 'psrc', 1, 'bias reference', i_bias), ('MP9', 'pbiascasc', 'pcasc', 1, 'bias reference cascode', i_bias),
    ('MPR', 'pbiascasc', 'plvl', 1, 'level shift vbp to vcp, triode', i_bias),
    ('MPSW3', 'pbiascasc', 'psrc', 1, 'enable switch', 0), ('MPSW4', 'pbiascasc', 'pcasc', 1, 'enable switch', 0),
    ('MPD2', 'pbiascasc', 'psrc', 48, 'dummy', 0), ('MPD3', 'pbiascasc', 'pcasc', 4, 'dummy', 0),
    ('MN1', 'nbiascasc', 'nsrc', 8, 'sink', i_fold), ('MN2', 'nbiascasc', 'nsrc', 8, 'sink', i_fold),
    ('MN3', 'nbiascasc', 'ncasc', 5, 'folded cascode', i5), ('MN4', 'nbiascasc', 'ncasc', 5, 'folded cascode', i5),
    ('MN5', 'nbiascasc', 'nsrc', 1, 'bias diode vbn', I_U), ('MN6', 'nbiascasc', 'ncasc', 1, 'bias diode vcn', I_U),
    ('MN7', 'nbiascasc', 'nsrc', 1, 'PMOS reference sink', i_bias), ('MN8', 'nbiascasc', 'ncasc', 1, 'PMOS reference sink cascode', i_bias),
    ('MNSW1', 'nbiascasc', 'nsrc', 1, 'enable switch', 0), ('MNSW4', 'nbiascasc', 'nsrc', 1, 'enable switch', 0),
    ('MNSW3', 'nbiascasc', 'ncasc', 1, 'enable switch', 0), ('MNSW5', 'nbiascasc', 'ncasc', 1, 'input pass switch', I_U),
    ('MND1', 'nbiascasc', 'nsrc', 20, 'dummy', 0), ('MND2', 'nbiascasc', 'ncasc', 27, 'dummy', 0),
    ('MNC7', 'nbiascasc', 'ncasc', 1, 'cap on vd7', 0),
    ('MPEN0', 'ena', 'pen', 1, 'enable inverter', 0), ('MNEN0', 'ena', 'nen', 1, 'enable inverter', 0),
    ('MPEN1', 'ena', 'pen', 1, 'enable inverter', 0), ('MNEN1', 'ena', 'nen', 1, 'enable inverter', 0),
]


def print_point(name, pt):
    head(f'Unit-device design point "{name}"')
    r = evaluate(pt)
    for k in DEV:
        w, l = pt[k]
        print(f'{k:6s} unit W = {w:.2f} um, L = {l:.1f} um, {BIAS[k][0] * 1e9:.0f} nA, gm/ID = {r["gmid"][k]:.1f}')
    print(f'Id1 = {id1 * 1e9:.0f} nA, tail = {2 * id1 * 1e9:.0f} nA, output branch = {i5 * 1e9:.0f} nA, '
          f'sink = {i_fold * 1e9:.0f} nA, I_fold/I_tail = {i_fold / (2 * id1):.3f} (rule >= 1.2)')
    print(f'gm1 = {r["gm1"] * 1e6:.2f} uS, Cgg1 = {r["cgg1"] * 1e15:.1f} fF, beta = {r["beta"]:.4f}, tau = {r["tau"] * 1e9:.2f} ns')
    print(f'A0 = {20 * np.log10(r["a0"]):.1f} dB, wp2/wug = {r["wp2"] * r["tau"]:.1f}, VGS5 = {r["vgs5"]:.3f} V')
    print(f'Output range per side {r["vo_min"]:.3f} to {r["vo_max"]:.3f} V, Vo,pp,diff = {r["swing"]:.3f} V')
    print(f'Supply current {r["itot"] * 1e6:.2f} uA (+ {I_U * 1e6:.2f} uA input), Ptot = {vdd * r["itot"] * 1e6:.2f} uW '
          f'(+ {vdd * I_U * 1e6:.2f} uW for the input)')

    head('System-level point against this point (model)')
    rows = [
        ('Id1 (nA)', id1_nb * 1e9, id1 * 1e9),
        ('I_tail (nA)', 2 * id1_nb * 1e9, 2 * id1 * 1e9),
        ('I_out branch (nA)', id1_nb * 1e9, i5 * 1e9),
        ('I_fold/I_tail', 1.0, i_fold / (2 * id1)),
        ('gm1 (uS)', gm1_nb * 1e6, r['gm1'] * 1e6),
        ('beta', beta_nb, r['beta']),
        ('tau (ns)', tau_nb * 1e9, r['tau'] * 1e9),
        ('A0 (dB)', 20 * np.log10(a0_nb), 20 * np.log10(r['a0'])),
        ('Vo,pp,diff (V)', vod_swing_design, r['swing']),
        ('Itot (uA)', itot_nb * 1e6, r['itot'] * 1e6),
        ('Ptot (uW)', vdd * itot_nb * 1e6, vdd * r['itot'] * 1e6),
    ]
    print(f'{"":20s}{"system":>10s}{"units":>10s}')
    for n, v_nb, v_r in rows:
        print(f'{n:20s}{v_nb:10.3f}{v_r:10.3f}')

    head('Devices')
    dims = dict(pt, plvl=PLVL)
    area_blk, area_typ, widths = {}, {}, {}
    print(f'{"name":7s}{"block":11s}{"type":7s}{"W/unit":>7s}{"L":>6s}{"ng":>4s}{"m":>4s}{"I (nA)":>9s}  function')
    for n, blk, typ, m, fn, i in DEVICES:
        w, l = dims[typ]
        pol = 'PMOS' if n.startswith('MP') else 'NMOS'
        area_blk[blk] = area_blk.get(blk, 0) + w * l * m
        area_typ[pol] = area_typ.get(pol, 0) + w * l * m
        widths.setdefault(pol, set()).add((w, l))
        print(f'{n:7s}{blk:11s}{typ:7s}{w:7.2f}{l:6.1f}{1:4d}{m:4d}{i * 1e9:9.0f}  {fn}')
    area_blk['cap_dec'] = 10 * 1.0 * 4.0
    head('Gate area (W*L summed, um^2)')
    for k, a_ in list(area_blk.items()) + list(area_typ.items()):
        print(f'{k:11s}{a_:8.2f}')
    print('cap_dec is 10 HV PMOS 1/4, not part of the LV types')
    for pol, s_ in widths.items():
        print(f'{pol}: {len(s_)} distinct unit sizes W/L {sorted(s_)}')


def compare():
    head('Equal-L candidates against the current point (model, L = 2, 3, 4 interpolated in the L = 1, 5, 10 tables)')
    print(f'{"point":26s}{"A0 dB":>7s}{"tau ns":>8s}{"wp2/wug":>9s}{"swing V":>9s}{"Cgg1 fF":>9s}')
    sets = {'current': POINTS['current'], 'equal_l': POINTS['equal_l']}
    sets.update({k: dict(POINTS['equal_l'], **v) for k, v in CANDIDATES.items()})
    for k, pt in sets.items():
        r = evaluate(pt)
        print(f'{k:26s}{20 * np.log10(r["a0"]):7.1f}{r["tau"] * 1e9:8.2f}{r["wp2"] * r["tau"]:9.1f}{r["swing"]:9.3f}{r["cgg1"] * 1e15:9.1f}')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--point', choices=list(POINTS), default='equal_l', help='unit set to print (default: the design)')
    ap.add_argument('--compare', action='store_true', help='also print the model table of the screened candidates')
    a = ap.parse_args()
    print_point(a.point, POINTS[a.point])
    if a.compare:
        compare()
