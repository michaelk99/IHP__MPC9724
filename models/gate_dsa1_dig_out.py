# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Check a dsa1_dig_top_out.txt against the bit-true model, pattern by pattern.

`make sim-gl` proves the hardened netlist equals the RTL, and both come from the
same source, so it cannot prove either is right. This runs the five on-chip
stimulus modes through models/, the five single ones and the three repeating
ones, and requires every output word to match.

    python3 models/gate_dsa1_dig_out.py macros/dsa1_dig/sims/rtl/dsa1_dig_top_out.txt

The bench starts counting conversions at the SPI write that sets the trigger,
while the trigger only arms and the pattern fires at the next valid_strobe, so
the file carries a couple of pre-fire samples. Those are exactly zero, because
the idle alternation decimates to zero, and the alignment search below absorbs
them. It is a property of the bench, not of the design.
"""

from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stimulus as S  # noqa: E402

# tag in the log -> (pattern, option), matching run_stim() in dsa1_dig_top_tb.v
CASES = [
    ("STEP_P", S.PAT_STEP_P, False),
    ("IMP", S.PAT_IMPULSE, False),
    ("HALF", S.PAT_STEADY, False),
    ("STEP_N", S.PAT_STEP_N, False),
    ("PRBS", S.PAT_STEADY, True),
    ("STEP_PR", S.PAT_STEP_P, True),
    ("IMP_R", S.PAT_IMPULSE, True),
    ("STEP_NR", S.PAT_STEP_N, True),
]
MAX_OFFSET = 6


def read_words(path: Path):
    """tag -> the signed 22-bit words, from the HIGH/LOW pairs the bench logs."""
    out = collections.defaultdict(list)
    high = {}
    for line in path.read_text().splitlines():
        m = re.match(r"(\w+)_(HI|LO)\s+([0-9a-fA-F]{4})", line.strip())
        if not m:
            continue
        tag, half, val = m.group(1), m.group(2), int(m.group(3), 16)
        if half == "HI":
            high[tag] = val
        elif tag in high:
            # HIGH carries the top 6 bits, LOW the bottom 16.
            w = ((high[tag] & 0x3F) << 16) | val
            out[tag].append(w - (1 << 22) if w & (1 << 21) else w)
    return out


def main(argv) -> int:
    if len(argv) != 2:
        print("usage: gate_dsa1_dig_out.py <dsa1_dig_top_out.txt>")
        return 2

    words = read_words(Path(argv[1]))
    if not words:
        print(f"FAIL: no stimulus words in {argv[1]}")
        return 1

    bad = 0
    for tag, pat, opt in CASES:
        got = words.get(tag)
        if not got:
            print(f"FAIL: {tag} missing from the log")
            bad += 1
            continue
        want = S.predict(pat, opt, n_out=len(got))

        best = None
        for off in range(MAX_OFFSET + 1):
            n = min(len(want), len(got) - off)
            if n < 8:
                break
            diff = sum(1 for i in range(n) if want[i] != got[off + i])
            if best is None or diff < best[0]:
                best = (diff, off, n)
        diff, off, n = best

        if diff:
            first = next(i for i in range(n) if want[i] != got[off + i])
            print(f"FAIL: {tag}, {diff} of {n} differ, first at {first}: "
                  f"model {want[first]}, sim {got[off + first]}")
            bad += 1
        else:
            print(f"OK: {tag:7s} {n} words match the model "
                  f"(settled {got[off + n - 1]})")

    if bad:
        return 1
    print(f"OK: all {len(CASES)} stimulus patterns match the bit-true model")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
