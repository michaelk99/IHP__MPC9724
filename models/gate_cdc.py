#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Köfinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Check the CDC sweep of make sim-cdc: every word each run read against the bit-true PRBS23 response.

    python3 models/gate_cdc.py macros/dsa1_dig/sims/cdc/*.txt
    python3 models/gate_cdc.py --self-test

A run with sclk at least as fast as clk must match word for word: every flag, one clk period long, meets an sclk edge. A run with sclk slower is the negative control and must not match: some flags fall between sclk edges and leave the old word, and a bench that cannot see that proves nothing.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench_capture as bc  # noqa: E402
import stimulus as S  # noqa: E402

_HEAD = re.compile(r"# clk ([\d.]+) ns, sclk ([\d.]+) ns, jitter ([\d.]+) ns, seed (\d+)")


def read_run(text: str) -> tuple:
    m = _HEAD.match(text)
    if not m:
        raise ValueError("no CDC bench header")
    clk, sclk, jitter, seed = float(m[1]), float(m[2]), float(m[3]), int(m[4])
    words = [bc.word22(int(p[1], 16), int(p[2], 16)) for p in (l.split() for l in text.splitlines()[1:]) if len(p) == 3]
    return clk / sclk, jitter, seed, words


def judge(ratio: float, words: list) -> tuple:
    """(ok, text). Stale words are the ones the model does not have at the best offset."""
    if len(words) < 8:
        return False, f"only {len(words)} words"
    best = bc.align(S.predict(S.PAT_STEADY, True, n_out=len(words)), words)
    diff, off, n = best
    lead = sum(1 for w in words[:off] if w)
    stale = diff + lead
    if ratio >= 1:
        return stale == 0, f"{stale} of {len(words)} words stale" + ("" if stale else f", all match at offset {off}")
    return stale > 0, f"control, {stale} of {len(words)} words stale" + ("" if stale else ": the bench sees no missed flag")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--self-test"]:
        return self_test()
    bad = 0
    print(f"{'sclk/clk':>9} {'jitter':>7} {'seed':>5}  result")
    for path in sorted(argv, key=lambda p: read_run(open(p).read())[0]):
        ratio, jitter, seed, words = read_run(open(path).read())
        ok, text = judge(ratio, words)
        bad += not ok
        print(f"{ratio:9.3f} {jitter:7.1f} {seed:5d}  {'ok' if ok else 'FAIL'}: {text}")
    print("OK: every run as it must be" if not bad else f"FAIL: {bad} runs")
    return 1 if bad else 0


def self_test() -> int:
    good = S.predict(S.PAT_STEADY, True, n_out=48)
    stale = list(good)
    for i in range(3, 48, 7):
        stale[i] = stale[i - 1]                 # the flag missed, the old word read again
    head = "# clk 1000.000 ns, sclk {:.3f} ns, jitter 0.000 ns, seed 1\n"

    def text(sclk, ws):
        return head.format(sclk) + "".join(f"{i} {(w & 0x3FFFFF) >> 16:04x} {w & 0xFFFF:04x}\n" for i, w in enumerate(ws))

    r, _, _, ws = read_run(text(250.0, good))
    assert abs(r - 4.0) < 1e-9 and ws == good
    assert judge(4.0, good)[0]
    assert not judge(4.0, stale)[0]                          # a stale word at a safe ratio fails
    assert judge(0.8, stale)[0] and not judge(0.8, good)[0]  # the control must see stale words
    assert judge(4.0, [0] * 3 + good)[0] and not judge(4.0, [5] * 3 + good)[0]   # settled idle before the fire, or not
    print("OK: gate_cdc self-test")
    return 0


if __name__ == "__main__":
    sys.exit(main())
