# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# python3 gds_compare.py <a.gds.gz> <b.gds.gz> <top of a> <top of b>
# Element-level compare of two GDS files: per structure, the multiset of elements (BOUNDARY to ENDEL), top name mapped.
import gzip, struct, sys, collections
A_TOP, B_TOP = sys.argv[3].encode(), sys.argv[4].encode()
def structs(p, top):
    d = gzip.open(p).read(); i = 0; cur = None; S = {}; el = []; els = None; texts = 0
    while i < len(d):
        n, t = struct.unpack('>HH', d[i:i+4]); t >>= 8
        if n == 0: break
        b = d[i+4:i+n]
        if t in (0x12, 0x06): b = b.rstrip(b'\0'); b = b'TOP' if b == top else b
        if t == 0x19: b = b.rstrip(b'\0')
        if t == 0x06: cur = b; els = collections.Counter()
        elif t == 0x07: S[cur] = els
        elif t == 0x0C: texts += 1
        if els is not None and t not in (0x05, 0x06, 0x07):
            el.append((t, b))
            if t == 0x11: els[tuple(el)] += 1; el = []
        i += n
    return S, texts
a, ta = structs(sys.argv[1], A_TOP); b, tb = structs(sys.argv[2], B_TOP)
print('structures', len(a), len(b), 'texts', ta, tb, 'same names', set(a) == set(b))
print('structures with differing elements', sum(1 for k in a if a[k] != b.get(k)))
