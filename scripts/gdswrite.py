# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Description: Write a GDS reproducibly -- same geometry in, same bytes out

"""`write_gds(layout, path)` instead of `layout.write(path)`.

KLayout stamps the current wall-clock time into two GDS records, `BGNLIB` and
`BGNSTR`. Every rebuild of a **tracked** GDS therefore produces a diff that is
16 bytes of date and nothing else, and `git status` stops meaning anything
after a `make gds`. Three `decap_hv` cells sat modified in the working tree for
that reason alone, and telling that apart from a real geometry change took a
byte-level comparison.

`SaveLayoutOptions.gds2_write_timestamps = False` writes zeros there instead,
so the same generator run twice gives byte-identical files. Nothing else about
the format changes and every tool reads them the same.

Import it from a generator with the repo's usual relative-to-`__file__` hop:

    HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))
    from gdswrite import write_gds

`python3 scripts/gdswrite.py` runs the selftest, which writes the same layout
twice a second apart and requires the two files to be identical.
"""

import os
import sys

import pya


def save_options(fmt="GDS2"):
    """SaveLayoutOptions with the timestamps suppressed."""
    opt = pya.SaveLayoutOptions()
    opt.format = fmt
    opt.gds2_write_timestamps = False
    return opt


def write_gds(layout, path, **kw):
    """`layout.write(path)`, minus the wall-clock stamp.

    Extra keyword arguments are set on the SaveLayoutOptions, so a caller that
    needs e.g. `gds2_max_vertex_count` can still say so.
    """
    opt = save_options()
    for k, v in kw.items():
        setattr(opt, k, v)
    layout.write(path, opt)
    return path


def _selftest():
    import hashlib
    import tempfile
    import time

    def build():
        ly = pya.Layout()
        ly.dbu = 0.001
        top = ly.create_cell("SELFTEST")
        top.shapes(ly.layer(8, 0)).insert(pya.Box(0, 0, 1000, 2000))
        return ly

    def sha(p):
        with open(p, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()

    with tempfile.TemporaryDirectory() as td:
        a = write_gds(build(), os.path.join(td, "a.gds"))
        time.sleep(1.1)                      # cross a second boundary
        b = write_gds(build(), os.path.join(td, "b.gds"))
        if sha(a) != sha(b):
            sys.stderr.write("gdswrite: FAIL, two writes differ\n")
            return 1
        # and prove the selftest can fail: with stamps on they must differ
        opt = pya.SaveLayoutOptions()
        opt.format = "GDS2"
        opt.gds2_write_timestamps = True
        c = os.path.join(td, "c.gds")
        d = os.path.join(td, "d.gds")
        build().write(c, opt)
        time.sleep(1.1)
        build().write(d, opt)
        if sha(c) == sha(d):
            sys.stderr.write("gdswrite: FAIL, stamped writes did NOT differ -- "
                             "the selftest proves nothing\n")
            return 1
    print("gdswrite: OK (identical without stamps, different with them)")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest())
