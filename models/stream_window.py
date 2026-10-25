# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Cut a window of the modulator record into the master board's BRAM image.

    python3 models/stream_window.py <stim_dac_sine_dec.txt> <stream.mem> [--start 65536] [--bits 131072]

Stream bit p is bit p % 8 of byte p // 8, one byte per line, which is how
bitstream_src.sv reads it. 131072 bits is 1024 output words, and 42 Hz is
coherent in any multiple of 256 at 512 Hz, so the looped window has no seam in
the tone. The default start skips the modulator's first second.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decimator_model import read_stimulus  # noqa: E402


def to_mem(bits: list[int]) -> str:
    assert len(bits) % 8 == 0
    return "".join(f"{sum(bits[8 * i + j] << j for j in range(8)):02x}\n"
                   for i in range(len(bits) // 8))


def load_mem(path) -> list[int]:
    bits = []
    for line in Path(path).read_text().splitlines():
        tok = line.split("//", 1)[0].strip()
        if tok:
            v = int(tok, 16)
            bits.extend((v >> j) & 1 for j in range(8))
    return bits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Cut a window of the modulator record into a .mem")
    ap.add_argument("stim")
    ap.add_argument("out")
    ap.add_argument("--start", type=int, default=65536)
    ap.add_argument("--bits", type=int, default=131072)
    a = ap.parse_args(argv)
    bits = read_stimulus(a.stim)
    if a.start + a.bits > len(bits):
        print(f"stream_window: the record has {len(bits)} bits, the window ends at {a.start + a.bits}")
        return 1
    win = bits[a.start:a.start + a.bits]
    Path(a.out).write_text(to_mem(win))
    assert load_mem(a.out) == win
    print(f"stream_window: {a.bits} bits from {a.start} of {len(bits)}, {sum(win)} ones, into {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
