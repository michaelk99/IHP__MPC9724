#!/usr/bin/env python3
"""PSD of the modulator bit stream from an ngspice or VACASK raw file.

Usage: psd_bitstream.py <raw> [fres|auto] [nsettle] [dumpfile]
Written for macros/dsm/testbenches/xschem/dsm_tb_psd.sch, which saves v(do_q).

The frequency resolution is the only knob. Everything else follows from it, by the same
arithmetic the two testbenches use, so a bench and its evaluation cannot drift apart.

"auto" takes the resolution from the record itself, the largest power of two that fits.
Both benches run to (nsettle + nfft + 8) clocks, so auto recovers the fres they were run
at without anything having to carry it across.

With a dumpfile the sampled stream is written out as one bit per line, so a result can be
kept without keeping the raw it came from.

The bit stream is a held logic level, so it is sampled once per clock in the middle of the
cycle where it has settled, not on the simulator's own uneven time points.
"""
import sys

import numpy as np

FS = 1.024e6
TS = 1.0 / FS
VDD = 1.5
FB = 1000.0
FSIG_TARGET = 750.0   # where the tone would sit if any bin were allowed
DCSKIRT = 2           # Hanning main lobe half width, in bins

# the band holds fb/fres bins, the windowed tone eats 5 and the DC skirt 2, so a resolution
# worth quoting an SNR from wants fb/fres >= MINBINS + 7, which at fb 1 kHz is fres 62.5
MINBINS = 8
FRES_FULL = 62.5


def plan(fres):
    """Everything a run needs, from the frequency resolution alone.

    The tone goes on a bin coprime with the record length, so the input phase never repeats
    inside it, which is what keeps a modulator off a limit cycle locked to the input. An even
    bin is still coherent, it just lets the input repeat.

    For a power-of-two record coprime means odd, which is what the testbenches compute, since
    a netlist cannot take a gcd. The system model runs at the system-level 1 Hz, where the
    record is 1024000 and oddness alone is not enough, so the rule is stated properly here
    and reduces to the benches' version wherever they can reach.
    """
    nfft = int(round(FS / fres))
    if abs(FS / fres - nfft) > 1e-6:
        raise SystemExit('fres %g does not divide fs %g into whole bins' % (fres, FS))
    if nfft & (nfft - 1):
        print('note: fres %g gives nfft %d, not a power of two. Fine for numpy, but the '
              'testbenches cannot follow it, they only do the odd-bin form of this rule'
              % (fres, nfft), file=sys.stderr)
    # floor(x + 0.5), not round(), so this matches the benches: numpy and python round half
    # to even, the simulators round half up
    ksig = int(np.floor(FSIG_TARGET / fres + 0.5))
    while ksig > 0 and np.gcd(ksig, nfft) != 1:
        ksig -= 1
    if ksig < 1:
        raise SystemExit('fres %g is coarser than the tone at %g Hz' % (fres, FSIG_TARGET))
    return nfft, ksig, ksig * fres




def spectrum(v):
    """(f, psd in dBFS, complex spectrum, nbw in Hz) of a +-1 stream, full scale sine at 0 dBFS."""
    win = np.hanning(v.size)
    n1, n2 = np.linalg.norm(win, 1), np.linalg.norm(win, 2)
    # the bit stream carries a DC offset, and its Hanning skirt lands on bins 1 and 2 well
    # above the quantization floor, so take the mean out before the transform
    spec = np.fft.rfft((v - v.mean()) * win) / (n1 / 2)
    f = np.fft.rfftfreq(v.size, TS)
    return f, 20 * np.log10(np.abs(spec) + 1e-20), spec, (n2 / n1) ** 2 * FS


def tone_dbfs(sig):
    """Sine amplitude in dBFS from split_band's signal sum, which is 1.5*A^2 under Hann."""
    return 10 * np.log10(sig / 1.5 + 1e-30)


def split_band(f, spec, ksig):
    """(signal power, in-band noise power, noise bin count) with the tone and DC taken out."""
    lo = max(ksig - 2, 1)   # a coarse fres can put the tone on bin 1, and a negative start
    sig = np.sum(np.abs(spec[lo:ksig + 3]) ** 2)   # would slice from the far end of the array
    inband = (f > 0) & (f <= FB)
    inband[lo:ksig + 3] = False
    inband[:DCSKIRT + 1] = False   # what is left of DC after mean removal
    return sig, np.sum(np.abs(spec[inband]) ** 2), np.count_nonzero(inband)


def notebook_snr(v, ksig, nsig=1):
    """SNR by the system-level method, the one of deltasigma's calcFFT plus calculateSNR.

    Kept so a number here can be put beside a system-level one. It differs from
    split_band in three ways, and the third one matters on a circuit stream:

    - signal is 3 bins, ksig-1 to ksig+1, against 5 here
    - the noise sum runs over the raw in-band bins with no window-skirt allowance
    - **bin 0 and bin 1 are counted as noise, and the mean is never removed**

    The system-level modulator runs at offset = 0 so its DC bin is negligible. A circuit
    stream is not: ours carries a +0.022 mean, which is -27 dBFS in bin 0 against a -97 dBFS
    floor, and this returns 21.95 dB where the shaped noise alone gives 83.89 dB. So use it
    to reproduce a system-level figure, never to judge a circuit.
    """
    nfft = v.size
    win = np.hanning(nfft)
    scale = 1.0 / ((2.0 / 4) * np.linalg.norm(win, 1))   # full scale is 2 for a 1-bit code
    hw = np.fft.fft(v * win, nfft) * scale
    inband = hw[0:int(round(FB * nfft / FS))]
    sb = np.arange(ksig - nsig + 1, ksig + nsig + 2)
    sb = sb[(sb > 0) & (sb <= inband.size)]
    nb = np.delete(np.arange(1, inband.size + 1), sb - 1)
    s, n = np.linalg.norm(inband[sb - 1]), np.linalg.norm(inband[nb - 1])
    return float('inf') if n == 0 else 20 * np.log10(s / n)


def read_stream(path):
    """Read back a stream written by the dumpfile argument, as +-1."""
    bits = np.array([int(l) for l in open(path) if l.strip() and not l.startswith('#')])
    return np.where(bits > 0, 1.0, -1.0)


def readraw(path):
    """Minimal binary rawfile reader, enough for one ngspice transient plot."""
    with open(path, 'rb') as fp:
        data = fp.read()
    head_end = data.find(b'Binary:\n') + len(b'Binary:\n')
    head = data[:head_end].decode('latin1')
    nvars = int([l for l in head.splitlines() if l.startswith('No. Variables')][0].split(':')[1])
    npts = int([l for l in head.splitlines() if l.startswith('No. Points')][0].split(':')[1])
    lines = head.splitlines()
    vstart = lines.index('Variables:') + 1
    names = [lines[vstart + i].split('\t')[2] for i in range(nvars)]
    flags = [l for l in lines if l.startswith('Flags')][0]
    cplx = 'complex' in flags
    arr = np.frombuffer(data[head_end:], dtype=np.complex128 if cplx else np.float64)
    arr = arr[:nvars * npts].reshape(npts, nvars)
    if cplx:
        arr = arr.real
    return names, arr


def main():
    names, arr = readraw(RAW)
    idx = {n: i for i, n in enumerate(names)}
    t = arr[:, idx['time']]
    # ngspice names the node v(do_q), VACASK names it do_q
    q = arr[:, idx['v(do_q)'] if 'v(do_q)' in idx else idx['do_q']]

    tstart = NSETTLE * TS
    navail = max(int((t[-1] - tstart) / TS), 0)
    if FRES == 'auto':
        fres = FS / 2 ** int(np.log2(max(navail, 1)))
    else:
        fres = float(FRES)
    nfft, ksig, fsig = plan(fres)

    if navail < nfft:
        # truncating would quietly hand back a different fres than the one asked for, and the
        # SNR that comes out of it looks entirely reasonable, so refuse instead
        raise SystemExit('raw holds %d samples after %d settle clocks, fres %g needs %d.\n'
                         'Run to %g ms, or ask for fres %g which this raw does support.'
                         % (navail, NSETTLE, fres, nfft, 1e3 * (NSETTLE + nfft + 8) * TS,
                            FS / 2 ** int(np.log2(max(navail, 1)))))
    tsamp = tstart + (np.arange(nfft) + 0.75) * TS
    bits = np.interp(tsamp, t, q)
    v = np.where(bits > VDD / 2, 1.0, -1.0)
    ntrans = np.count_nonzero(np.diff(v))

    print('fres %g Hz, nfft %d, tone on bin %d = %g Hz' % (fres, nfft, ksig, fsig))
    print('samples %d, mean %+.6f, ones %.2f %%' % (v.size, v.mean(), 50 * (1 + v.mean())))
    print('transitions %d' % ntrans)

    if DUMP:
        with open(DUMP, 'w') as fp:
            fp.write('# bit stream of %s, sampled at (n + 0.75)*Ts from clock %d on\n'
                     '# fs=%g fres=%g nfft=%d ksig=%d fsig=%g\n'
                     '# nsettle=%d samples=%d mean=%+.6f transitions=%d\n'
                     % (RAW, NSETTLE, FS, fres, nfft, ksig, fsig,
                        NSETTLE, v.size, v.mean(), ntrans))
            fp.write(''.join('%d\n' % b for b in (v > 0).astype(int)))
        print('wrote %s' % DUMP)

    f, psd, spec, nbw = spectrum(v)
    sig, noise, nbins = split_band(f, spec, ksig)
    print('bin width %.1f Hz, tone %.2f dBFS, %d noise bins in band'
          % (f[1] - f[0], tone_dbfs(sig), nbins))
    if noise > 0:
        snr = 10 * np.log10(sig / noise)
        print('in-band noise %.2f dBFS, SNR %.2f dB, ENOB %.2f bit'
              % (10 * np.log10(noise), snr, (snr - 1.76) / 6.02))
        if nbins < MINBINS:
            print('  warning: %d noise bins is too few to average, use fres %g'
                  % (nbins, FRES_FULL))
        nb = notebook_snr(v, ksig)
        print('system-level definition %.2f dB%s'
              % (nb, '' if abs(nb - snr) < 1 else
                 '   <- counts bin 0 and 1 as noise, and this stream has a %+.4f mean'
                 % v.mean()))
    else:
        print('in-band noise has no bin of its own at fres %g, use %g'
              % (fres, FRES_FULL))
    # nbw_hz lets plot_psd.py put this on the same axes as a PSD taken at another FFT length
    np.savetxt('psd.csv', np.column_stack((f, psd)), delimiter=',',
               header='nbw_hz=%.6g\nf,psd_dbfs' % nbw, comments='# ')
    print('wrote psd.csv, %d bins, NBW %.4g Hz' % (f.size, nbw))


if __name__ == '__main__':
    # module level so main() can read them, guarded so plot_psd.py can import the helpers
    RAW = sys.argv[1] if len(sys.argv) > 1 else 'dsm_tb_psd.raw'
    FRES = sys.argv[2] if len(sys.argv) > 2 else '250'
    NSETTLE = int(sys.argv[3]) if len(sys.argv) > 3 else 32
    DUMP = sys.argv[4] if len(sys.argv) > 4 else None
    main()
