# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Decode what the ULX3S master board sends, and check it against models/.

    python3 models/bench_capture.py --port /dev/ttyUSB0 --records 120 --save run.bin
    python3 models/bench_capture.py --file run.bin --stream testbenches/fpga/build/stream.mem
    python3 models/bench_capture.py --hex testbenches/fpga/build/sim/uart_p2.hex
    python3 models/bench_capture.py --self-test

The same decoder reads the two-board simulation's log and the real serial port, so the check that passes in simulation is the check that runs on the bench. The silicon hosts reuse check() through their own tool, which turns their answers into these records. doc/host_protocol.md has the formats. Standard library only: the port is set up with termios.

A record is 63 bits in nine bytes of 7, most significant first, and only the
first byte has bit 7 set. record_tx.sv and seq_core.sv are the other end.

    kind [62:60]  0 SPI       addr [59:55], sent [54:39], received [38:23], pc [22:15]
                  1 ADC       HIGH [59:44], LOW [43:28], conversion [27:17], stream index [16:0]
                  2 START     program [59:56], 0xD5A1 [55:40]
                  3 RESET, 4 LOOPBACK (value in [0]), 5 STREAM, 7 END, all with pc [22:15]

What is checked, from the records alone:

- loopback on: every SPI word comes back as sent
- after a RESET: every SPI transaction against a register model seeded with
  the reset values in dsa1_regs.vhd. A write returns the old value, a read
  the current one. The ADC registers 0 and 1 are skipped.
- every run of ADC records: HIGH[15:6] is zero and the conversion count
  steps by one, so a dropped conversion cannot pass as a shifted word
- a run with STIM_EN in the last TEST_CTRL_0 write: the words against
  stimulus.predict() for that pattern, any leading words exactly zero
- a run after STREAM with STIM_EN clear: the stream index steps by exactly
  128, which proves the DUT runs on the master's clk_fs, and the words against
  decimator_model.py fed the same looped window
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import regmap  # noqa: E402
import stimulus as S  # noqa: E402
from decimator_model import DecimatorModel  # noqa: E402
from stream_window import load_mem, to_mem  # noqa: E402

FRAME = 9
MAGIC = 0xD5A1
K_SPI, K_ADC, K_START, K_RESET, K_LOOP, K_STREAM, K_END = 0, 1, 2, 3, 4, 5, 7
STIM_EN, STIM_TRIG, STIM_OPT = 1 << 11, 1 << 12, 1 << 15
MAX_OFFSET = 6      # pre-fire words a capture may start with
WARM = 48           # output words of history the model gets before comparing


# ---- the wire format ---------------------------------------------------------

def encode(payload: int) -> bytes:
    """The bytes record_tx.sv sends for one payload."""
    return bytes((0x80 if i == 0 else 0) | ((payload >> (7 * (FRAME - 1 - i))) & 0x7F)
                 for i in range(FRAME))


def frames(data: bytes) -> tuple[list[int], int]:
    """Payloads of the complete frames, and the bytes dropped while resyncing."""
    out, cur, dropped = [], None, 0
    for b in data:
        if b & 0x80:
            if cur is not None:
                dropped += len(cur)
            cur = [b]
        elif cur is None:
            dropped += 1
            continue
        else:
            cur.append(b)
        if len(cur) == FRAME:
            p = 0
            for x in cur:
                p = (p << 7) | (x & 0x7F)
            out.append(p)
            cur = None
    if cur is not None:
        dropped += len(cur)
    return out, dropped


def pack(kind: int, pc: int = 0, value: int = 0) -> int:
    return (kind << 60) | ((pc & 0xFF) << 15) | (value & 1)


def pack_spi(addr: int, sent: int, recv: int, pc: int = 0) -> int:
    return (K_SPI << 60) | (addr << 55) | (sent << 39) | (recv << 23) | ((pc & 0xFF) << 15)


def pack_adc(hi: int, lo: int, cnt: int, idx: int) -> int:
    return (K_ADC << 60) | (hi << 44) | (lo << 28) | ((cnt & 0x7FF) << 17) | (idx & 0x1FFFF)


def pack_start(program: int) -> int:
    return (K_START << 60) | (program << 56) | (MAGIC << 40)


def word22(hi: int, lo: int) -> int:
    w = ((hi & 0x3F) << 16) | lo
    return w - (1 << 22) if w & (1 << 21) else w


# ---- the checks ----------------------------------------------------------------

def _first_strobe() -> int:
    m = DecimatorModel()
    for k in range(256):
        if m.step(0) is not None:
            return k
    raise RuntimeError("DecimatorModel never strobes")


FIRST_STROBE = _first_strobe()


def model_window(bits: list[int], q0: int, n: int) -> list[int]:
    """n model words whose strobes fall on stream positions q0, q0 + 128, ..., looped."""
    m = DecimatorModel()
    s = q0 - FIRST_STROBE - 128 * WARM
    out = []
    for k in range(128 * (WARM + n)):
        y = m.step(bits[(s + k) % len(bits)])
        if y is not None:
            out.append(y)
    return out[WARM:WARM + n]


def stream_lag(words: list[int], idx0: int, bits: list[int], lag_max: int = 512):
    """The latency L for which word k is the model at stream index idx_k - L, or None."""
    for lag in range(lag_max):
        if model_window(bits, idx0 - lag, 4) == words[:4]:
            if model_window(bits, idx0 - lag, len(words)) == words:
                return lag
    return None


def align(want: list[int], got: list[int]):
    """(differences, offset, compared) at the best offset of got against want, or None."""
    best = None
    for off in range(MAX_OFFSET + 1):
        n = min(len(want), len(got) - off)
        if n < 8:
            break
        diff = sum(1 for i in range(n) if want[i] != got[off + i])
        if best is None or diff < best[0]:
            best = (diff, off, n)
    return best


def _check_run(tst, streamed, recs, bits, fails, notes) -> None:
    words = [word22(hi, lo) for hi, lo, _, _ in recs]
    bad_hi = [i for i, r in enumerate(recs) if r[0] & 0xFFC0]
    if bad_hi:
        fails.append(f"HIGH[15:6] not zero in {len(bad_hi)} records, first at {bad_hi[0]}")
    gaps = [i for i in range(1, len(recs)) if (recs[i][2] - recs[i - 1][2]) % 2048 != 1]
    if gaps:
        fails.append(f"conversion dropped before record {gaps[0]}, {len(gaps)} gaps")

    if tst & STIM_EN:
        pat, opt = (tst >> 13) & 3, bool(tst & STIM_OPT)
        name = "prbs23" if (pat == S.PAT_STEADY and opt) else S.PAT_NAMES[pat]
        if not tst & STIM_TRIG:
            fails.append(f"{name}: captured without the trigger set")
            return
        best = align(S.predict(pat, opt, n_out=len(words)), words)
        if best is None:
            fails.append(f"{name}: only {len(words)} words")
            return
        diff, off, n = best
        if diff or any(words[:off]):
            fails.append(f"{name}: {diff} of {n} words differ from the model at offset {off}")
        else:
            notes.append(f"{name}: {n} words match the model at offset {off}, "
                         f"settled at {words[off + n - 1]}")
    elif streamed:
        steps = sorted({(recs[i][3] - recs[i - 1][3]) % (1 << 17) for i in range(1, len(recs))})
        if steps != [128]:
            fails.append(f"stream index steps {steps} per conversion, want 128 only: "
                         f"clk_fs slipped between the boards")
            return
        if bits is None:
            notes.append(f"stream: {len(words)} words, not compared without --stream")
            return
        lag = stream_lag(words, recs[0][3], bits)
        if lag is None:
            fails.append(f"stream: {len(words)} words match the model at no lag")
        else:
            notes.append(f"stream: {len(words)} words match the model, lag {lag}, index steps 128")
    else:
        notes.append(f"{len(words)} words from the external data_in, not compared")


def check(payloads: list[int], stream_bits: list[int] | None = None):
    """(failures, notes) for one decoded log."""
    fails: list[str] = []
    notes: list[str] = []
    regs = None
    loop = streamed = False
    tst = regmap.RESET[regmap.TEST_CTRL_0]
    runs = []           # (TEST_CTRL_0 at the start, streamed, [(hi, lo, cnt, idx)])
    n_spi = n_checked = 0
    prev = None
    waiting = None      # a stimulus write or STREAM that no conversion has followed yet

    for p in payloads:
        k = p >> 60
        pc = (p >> 15) & 0xFF
        if k == K_START:
            if (p >> 40) & 0xFFFF != MAGIC:
                fails.append("START record without the magic")
            notes.append(f"program {(p >> 56) & 0xF}")
            regs, loop, streamed = None, False, False
            tst = regmap.RESET[regmap.TEST_CTRL_0]
        elif k == K_RESET:
            regs = dict(regmap.RESET)
            tst = regs[regmap.TEST_CTRL_0]
        elif k == K_LOOP:
            loop = bool(p & 1)
        elif k == K_STREAM:
            streamed = True
            waiting = "STREAM"
        elif k == K_SPI:
            addr, sent, recv = (p >> 55) & 0x1F, (p >> 39) & 0xFFFF, (p >> 23) & 0xFFFF
            a, write = addr & 0xF, not addr & 0x10
            n_spi += 1
            if loop:
                n_checked += 1
                if recv != sent:
                    fails.append(f"loopback at pc {pc}: sent 0x{sent:04X}, got 0x{recv:04X}")
            elif regs is not None and a > 1:
                n_checked += 1
                if recv != regs[a]:
                    fails.append(f"pc {pc}: {'write' if write else 'read'} of register {a} "
                                 f"returned 0x{recv:04X}, the model has 0x{regs[a]:04X}")
                if write and a not in regmap.READ_ONLY:
                    regs[a] = sent
            if write and a == regmap.TEST_CTRL_0 and not loop:
                tst = sent
                if sent & STIM_EN:
                    waiting = f"TEST_CTRL_0 = 0x{sent:04X}"
        elif k == K_ADC:
            waiting = None
            if prev != K_ADC:
                runs.append((tst, streamed, []))
            runs[-1][2].append(((p >> 44) & 0xFFFF, (p >> 28) & 0xFFFF,
                                (p >> 17) & 0x7FF, p & 0x1FFFF))
        elif k == K_END:
            notes.append(f"END at pc {pc}")
        else:
            fails.append(f"unknown record kind {k}")
        prev = k

    if not payloads:
        fails.append("no records")
    if waiting:
        fails.append(f"no conversion after {waiting}: the program stalled, is adc_conv wired?")
    if n_spi:
        notes.append(f"{n_checked} of {n_spi} SPI transactions checked")
    for tst_v, streamed_v, recs in runs:
        _check_run(tst_v, streamed_v, recs, stream_bits, fails, notes)
    return fails, notes


# ---- the serial port -----------------------------------------------------------

def read_port(dev: str, records: int, seconds: float) -> tuple[bytes, str]:
    """Raw bytes at 115200 8N1, and why reading stopped: "records", "end" or "timeout"."""
    import termios

    fd = os.open(dev, os.O_RDONLY | os.O_NOCTTY)
    try:
        a = termios.tcgetattr(fd)
        a[0] = a[1] = a[3] = 0
        a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        a[4] = a[5] = termios.B115200
        a[6][termios.VMIN], a[6][termios.VTIME] = 0, 5
        termios.tcsetattr(fd, termios.TCSANOW, a)
        termios.tcflush(fd, termios.TCIFLUSH)
        data = bytearray()
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            data += os.read(fd, 4096)
            recs, _ = frames(bytes(data))
            if any(r >> 60 == K_END for r in recs):
                return bytes(data), "end"
            if len(recs) >= records:
                return bytes(data), "records"
        return bytes(data), "timeout"
    finally:
        os.close(fd)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Decode and check the ULX3S master board's records")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--port", help="serial device of the ULX3S master, e.g. /dev/ttyUSB0")
    src.add_argument("--file", help="raw record bytes saved with --save")
    src.add_argument("--hex", help="one hex byte per line, what the two-board simulation writes")
    src.add_argument("--self-test", action="store_true")
    ap.add_argument("--records", type=int, default=120, help="with --port: stop after this many records")
    ap.add_argument("--seconds", type=float, default=30.0, help="with --port: stop after this long")
    ap.add_argument("--save", help="write the raw record bytes here")
    ap.add_argument("--stream", help="the stream.mem the ULX3S master plays")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.port:
        data, stopped = read_port(args.port, args.records, args.seconds)
    elif args.file:
        data = Path(args.file).read_bytes()
    else:
        data = bytes(int(t, 16) for t in Path(args.hex).read_text().split())
    if args.save and args.port:
        Path(args.save).write_bytes(data)

    payloads, dropped = frames(data)
    fails, notes = check(payloads, load_mem(args.stream) if args.stream else None)
    if args.port and stopped == "timeout":
        fails.append(f"{args.seconds:g} s passed with {len(payloads)} records, no END and fewer than --records {args.records}")
    print(f"{len(payloads)} records, {dropped} bytes dropped resyncing")
    for n in notes:
        print(f"  {n}")
    for f in fails:
        print(f"FAIL: {f}")
    if fails:
        return 1
    print("OK: every check passes")
    return 0


def self_test() -> int:
    # The BRAM image round-trips.
    with tempfile.TemporaryDirectory() as tmp:
        bits = [(i * 7 >> 2) & 1 for i in range(64)]
        p = Path(tmp) / "s.mem"
        p.write_text(to_mem(bits))
        assert load_mem(p) == bits

    # Frames round-trip, and a stream joined mid-frame resyncs on the next one.
    ps = [pack_start(2), pack_spi(0x09, 0x1D00, 0x0D00, 40), pack_adc(0x3F, 0xFFFF, 5, 1234)]
    data = b"".join(encode(p) for p in ps)
    assert frames(data) == (ps, 0)
    assert frames(data[4:]) == (ps[1:], 5)

    # Loopback: a word that does not come back fails.
    f, _ = check([pack_start(0), pack(K_LOOP, 17, 1),
                  pack_spi(0x0C, 0xA5A5, 0xA5A5), pack_spi(0x0C, 0x5A5A, 0x5A5B)])
    assert len(f) == 1 and "loopback" in f[0], f

    # Register model: a write returns the reset value, a read the new one.
    r2 = regmap.RESET[2]
    ok = [pack_start(1), pack(K_RESET), pack_spi(0x02, 0x6F15, r2), pack_spi(0x12, 0, 0x6F15)]
    assert check(ok)[0] == [], check(ok)
    f, _ = check(ok[:3] + [pack_spi(0x12, 0, r2)])
    assert len(f) == 1 and "register 2" in f[0], f

    # Stimulus: the model's own step response passes, one dropped conversion fails.
    want = S.predict(S.PAT_STEP_P, False, n_out=40)

    def adc(ws, cnts):
        return [pack_adc((w >> 16) & 0x3F, w & 0xFFFF, c, 0) for w, c in zip(ws, cnts)]

    head = [pack_start(2), pack_spi(0x09, 0x1D00, 0)]
    cnts = list(range(1, 42))
    f, notes = check(head + adc([0] + want, cnts))
    assert f == [] and any("offset 1" in n for n in notes), (f, notes)
    cnts[10:] = [c + 1 for c in cnts[10:]]
    f, _ = check(head + adc([0] + want, cnts))
    assert any("dropped" in x for x in f), f

    # Stream: a synthetic window is found at the lag it was made with, a slip is caught.
    bits = [((i * 2654435761) >> 7) & 1 for i in range(1 << 17)]
    lag, idx0 = 37, 20000
    ws = model_window(bits, idx0 - lag, 8)
    recs = [pack_start(7), pack(K_STREAM)] + [
        pack_adc((w >> 16) & 0x3F, w & 0xFFFF, k + 1, idx0 + 128 * k) for k, w in enumerate(ws)]
    f, notes = check(recs, bits)
    assert f == [] and any("lag 37" in n for n in notes), (f, notes)
    w = ws[3]
    recs[5] = pack_adc((w >> 16) & 0x3F, w & 0xFFFF, 4, idx0 + 128 * 3 + 1)
    f, _ = check(recs, bits)
    assert any("slipped" in x for x in f), f

    # A program that stalls after arming, adc_conv not wired for example, is a FAIL, not an OK.
    f, _ = check([pack_start(2), pack(K_RESET), pack_spi(0x09, 0x0D00, 0x0500)])
    assert any("stalled" in x for x in f), f
    f, _ = check([pack_start(7), pack(K_RESET), pack(K_STREAM)])
    assert any("stalled" in x for x in f), f

    # The serial port: running out of time is a FAIL, reaching the record count is not.
    import pty
    import threading
    import tty
    mfd, sfd = pty.openpty()
    tty.setraw(mfd)

    def later(b):                       # read_port flushes what was there before it opened
        threading.Timer(0.3, os.write, (mfd, b)).start()

    later(b"".join(encode(p) for p in ps))
    data, why = read_port(os.ttyname(sfd), records=10, seconds=1.0)
    assert frames(data)[0] == ps and why == "timeout", (len(data), why)
    later(b"".join(encode(p) for p in ps))
    data, why = read_port(os.ttyname(sfd), records=3, seconds=5.0)
    assert why == "records", why
    later(encode(pack_start(2)))
    assert main(["--port", os.ttyname(sfd), "--records", "5", "--seconds", "1"]) == 1
    os.close(mfd)
    os.close(sfd)

    # CHIP_ID is read only: a write shifts out 0x0001 and leaves it there
    f, _ = check([pack_start(1), pack(K_RESET), pack_spi(0x0F, 0xBEEF, 0x0001), pack_spi(0x1F, 0, 0x0001)])
    assert f == [], f
    f, _ = check([pack_start(1), pack(K_RESET), pack_spi(0x0F, 0xBEEF, 0x0001), pack_spi(0x1F, 0, 0xBEEF)])
    assert f, "CHIP_ID read back what was written to it"
    print("OK: bench_capture self-test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
