# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Bit-true model of the decimator macro: CIC(N=6, D=32), sinc2^9, sinc2^16, 9-tap compensator.

Cycle accurate against macros/decimator/rtl, one step() per clk_fs edge, so a
testbench can compare sample for sample with no lag search. Every constant here
is read off the RTL and nothing is designed at run time, which is the point: the
model is the reference the RTL is gated against, so it must not share code with
it.

Pure Python on purpose. The host has neither numpy nor cocotb, and an offline
gate that only runs inside the container is a gate that does not get run.
"""

from __future__ import annotations

# Geometry, from decimator_core.sv
DATA_W = 22   # output word
CIC_W = 32    # N*log2(D) + 2, the integrators wrap in this
W = 27        # datapath
ALIGN_W = 6   # CIC gain 2^30 down to 2^(20+F)
RND_W = 4     # F, fraction bits below the output LSB
N = 6         # CIC order
D = 32        # CIC decimation
M1 = 9        # sinc2 sections in the first stage
M2 = 16       # sinc2 sections in the second stage

WP = W + 1        # the compensator pre-adder grows by one
ACC_W = WP + 17   # the largest term is x <<< 15, plus guard
FINAL_W = W - RND_W

# Compensator, from the term table in comp_fir.sv. Five folded taps, six CSD
# terms each, as (tap_scale, [(shift, negate), ...]).
#   b0 =  28997/2^18   b1 = -6243/2^13   b2 = 44815/2^14
#   b3 =  -1639/2^8    b4 =  2467/2^8
COMP_TAPS = (
    (18, ((15, 0), (12, 1), (8, 0), (6, 0), (2, 0), (0, 0))),
    (13, ((13, 1), (11, 0), (7, 1), (5, 0), (2, 1), (0, 0))),
    (14, ((15, 0), (13, 0), (12, 0), (8, 1), (4, 0), (0, 1))),
    (8, ((11, 1), (9, 0), (7, 1), (5, 0), (3, 1), (0, 0))),
    (8, ((11, 0), (9, 0), (6, 1), (5, 1), (2, 0), (0, 1))),
)
NTERM = 6
LAST_STEP = 38  # {tap = 4, term = 6}


def wrap(v: int, width: int) -> int:
    """Two's complement wrap to `width` bits."""
    m = 1 << width
    return ((v + (m >> 1)) & (m - 1)) - (m >> 1)


def comp_tap_value(tap: int) -> float:
    """The tap as a rational, for checking the table against a filter design."""
    scale, terms = COMP_TAPS[tap]
    num = sum((-1 if neg else 1) << sh for sh, neg in terms)
    return num / (1 << scale)


class _Sinc2Chain:
    """M cascaded (1 + z^-1) sections, each rounding one bit so the word stays at W.

    The chain is combinational, only the per-section delays are state, so eval()
    returns the output and the next state without committing.
    """

    def __init__(self, width: int, m: int):
        self.w = width
        self.m = m
        self.sect = [0] * m

    def eval(self, data_in: int):
        chain = data_in
        nxt = [0] * self.m
        for g in range(self.m):
            nxt[g] = chain
            # y = (x[n] + x[n-1] + 1) >>> 1, one bit of growth rounded away
            chain = (chain + self.sect[g] + 1) >> 1
        return chain, nxt


class _CompFir:
    """9-tap symmetric compensator, folded and time multiplexed onto one shift-add engine.

    35 of the 128 clocks per output sample are used. The engine walks five taps
    of six CSD terms each, rounding once per tap at that tap's own scale.
    """

    def __init__(self, width: int):
        self.w = width
        self.d = [0] * 8
        self.step = 0
        self.busy = False
        self.acc = 0
        self.out_acc = 0
        self.result = 0

    @property
    def data_out(self) -> int:
        return wrap(self.result, self.w)

    def _folded(self, data_in: int):
        d = self.d
        return (
            wrap(data_in + d[7], WP),
            wrap(d[0] + d[6], WP),
            wrap(d[1] + d[5], WP),
            wrap(d[2] + d[4], WP),
            wrap(d[3], WP),
        )

    def clock(self, data_in: int, ce: bool) -> None:
        tap = self.step >> 3
        term = self.step & 7
        last = term == NTERM

        sh_tap, terms = COMP_TAPS[tap if tap < len(COMP_TAPS) else len(COMP_TAPS) - 1]
        sh_term, neg = terms[term] if term < NTERM else (0, 0)

        op = self._folded(data_in)[tap if tap < 5 else 4]
        addend = wrap(-(op << sh_term) if neg else (op << sh_term), ACC_W)

        rnd = wrap(self.acc + (1 << (sh_tap - 1)), ACC_W)
        prd = wrap(rnd >> sh_tap, WP)

        if ce:
            self.d = [data_in] + self.d[:-1]
            self.step = 0
            self.busy = True
            self.acc = 0
            self.out_acc = 0
        elif self.busy:
            if self.step == LAST_STEP:
                self.result = wrap(self.out_acc + prd, WP)
                self.out_acc = wrap(self.out_acc + prd, WP)
                self.acc = 0
                self.busy = False
            else:
                if last:
                    self.out_acc = wrap(self.out_acc + prd, WP)
                    self.acc = 0
                    self.step = ((tap + 1) << 3)
                else:
                    self.acc = wrap(self.acc + addend, ACC_W)
                    self.step += 1


class DecimatorModel:
    """One step() per clk_fs rising edge, mirroring decimator_core.sv.

    step(bit) takes the value data_in holds going into the edge and returns the
    output word when valid_strobe is high after it, else None. A `bit` of 1 is
    +1 into the CIC and 0 is -1, which is how decimator_top maps the pin.
    """

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.cnt = 0
        self.int_reg = [0] * N
        self.comb_d = [0] * N
        self.cic_out = 0
        self.s1 = _Sinc2Chain(W, M1)
        self.s2 = _Sinc2Chain(W, M2)
        self.s2_in = 0
        self.comp_in = 0
        self.comp = _CompFir(W)
        self.out_reg = 0
        self.vs = False

    def step(self, bit: int):
        ce_cic = (self.cnt & 0x1F) == 0
        ce_s1 = (self.cnt & 0x3F) == 32
        ce_s2 = (self.cnt & 0x7F) == 96

        # --- CIC. Integrators run at clk_fs and are allowed to wrap: modulo
        # anything above the chain gain the comb output is still exact.
        cic_in = 1 if bit else -1
        ir = self.int_reg
        nxt_int = [wrap(ir[0] + cic_in, CIC_W)]
        for i in range(1, N):
            nxt_int.append(wrap(ir[i] + ir[i - 1], CIC_W))

        # The combs are combinational through the chain, one delay each.
        q = []
        prev = ir[N - 1]
        for i in range(N):
            prev = wrap(prev - self.comb_d[i], CIC_W)
            q.append(prev)

        # --- align the CIC gain to the datapath scale, rounding
        cic_sh = wrap(self.cic_out + (1 << (ALIGN_W - 1)), CIC_W) >> ALIGN_W
        s1_in = wrap(cic_sh, W)

        s1_out, s1_next = self.s1.eval(s1_in)
        s2_out, s2_next = self.s2.eval(self.s2_in)

        # --- final round and saturate, from the compensator's held result
        comp_out = self.comp.data_out
        out_rnd = wrap(comp_out + (1 << (RND_W - 1)), W)
        out_trnc = out_rnd >> RND_W
        lim = 1 << (DATA_W - 1)
        out_sat = min(max(out_trnc, -lim), lim - 1)

        # --- commit
        self.comp.clock(self.comp_in, ce_s2)
        if ce_cic:
            self.comb_d = [ir[N - 1]] + q[: N - 1]
            self.cic_out = q[N - 1]
            self.s1.sect = s1_next
        if ce_s1:
            self.s2_in = s1_out
            self.s2.sect = s2_next
        if ce_s2:
            self.comp_in = s2_out
            self.out_reg = out_sat
        self.int_reg = nxt_int
        self.vs = ce_s2
        self.cnt = (self.cnt + 1) & 0x7F

        return self.out_reg if self.vs else None

    def run(self, bits) -> list:
        """Feed a whole bitstream and return one word per valid_strobe."""
        out = []
        for b in bits:
            y = self.step(b)
            if y is not None:
                out.append(y)
        return out


def read_stimulus(path: str) -> list:
    """Read the MATLAB bitstream export, one `time value` pair per line, value +-1."""
    bits = []
    with open(path) as fh:
        first = fh.readline()
        if first and first.split()[0].replace(".", "", 1).replace("-", "", 1).isdigit():
            fh.seek(0)  # no header
        for line in fh:
            parts = line.split()
            if len(parts) == 2:
                bits.append(1 if int(parts[1]) == 1 else 0)
    return bits


def _gate(stim_path: str, rtl_path: str, max_lag: int = 64) -> int:
    """Compare the model against a simulated RTL output file, absorbing pipeline latency."""
    bits = read_stimulus(stim_path)
    with open(rtl_path) as fh:
        rtl = [int(line) for line in fh if line.strip()]

    # The testbench assigns data_in non-blocking at the same edge the DUT samples
    # it, so the DUT sees each sample one edge late, and it holds 0 (-1 into the
    # CIC) through reset. A lag search absorbs the constant part of that.
    model = DecimatorModel().run([0, 0] + bits)

    best, lag, span = None, 0, 0
    for lg in range(max_lag + 1):
        k = min(len(model), len(rtl) - lg)
        if k < 1000:
            break
        diff = sum(1 for i in range(k) if model[i] != rtl[lg + i])
        if best is None or diff < best:
            best, lag, span = diff, lg, k

    print(f"model {len(model)} samples, rtl {len(rtl)}")
    print(f"rtl vs model: {best} of {span} differ at lag {lag}")
    if best:
        firsts = [i for i in range(span) if model[i] != rtl[lag + i]][:3]
        print(f"  first at {firsts}")
        print(f"  model {[model[i] for i in firsts]}")
        print(f"  rtl   {[rtl[lag + i] for i in firsts]}")
    return 0 if best == 0 else 1


def self_test() -> int:
    """Check the model against what is known without simulating anything.

    Runs anywhere, needs no cell library and no simulator, so CI can run it even
    though it cannot build the design.
    """
    # The CSD term table must reconstruct the tap values in the comp_fir.sv header.
    want = (28997 / 2 ** 18, -6243 / 2 ** 13, 44815 / 2 ** 14, -1639 / 2 ** 8, 2467 / 2 ** 8)
    for t, w in enumerate(want):
        got = comp_tap_value(t)
        if got != w:
            print(f"FAIL: tap b{t} is {got}, expected {w}")
            return 1

    # A held +1 must settle on 2^20 times the compensator dc gain. This is the
    # one check that does not depend on the model agreeing with itself.
    dc = sum(want[:4]) * 2 + want[4]
    expect = round((1 << 20) * dc)
    y = DecimatorModel().run([1] * (128 * 40))
    if y[-1] != expect:
        print(f"FAIL: dc output {y[-1]}, expected {expect}")
        return 1
    if len(y) != 40:
        print(f"FAIL: {len(y)} output samples for {128 * 40} inputs, expected 40")
        return 1

    # -1 is the mirror of +1 and the output must saturate at neither end here.
    yn = DecimatorModel().run([0] * (128 * 40))
    if yn[-1] != -expect:
        print(f"FAIL: negative dc output {yn[-1]}, expected {-expect}")
        return 1

    print(f"OK: taps reconstruct, dc gain {dc:.9f}, settled output {expect}")
    return 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        raise SystemExit(self_test())
    if len(sys.argv) != 3:
        print("usage: decimator_model.py <stimulus.txt> <rtl_output.txt>")
        print("       decimator_model.py --self-test")
        raise SystemExit(2)
    raise SystemExit(_gate(sys.argv[1], sys.argv[2]))
