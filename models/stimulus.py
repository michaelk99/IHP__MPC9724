# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""The on-chip stimulus patterns of TEST_CTRL_0 bits 15:11, as a bit generator.

Mirrors `p_stim` in macros/dsa1_dig/rtl/dsa1_dig_top.vhd so the bit-true
decimator model can predict what the chip produces for each pattern. Together
with decimator_model.py this turns an FPGA or silicon measurement into a
sample-for-sample gate rather than a plausibility check.

Why the prediction is well defined even though the SPI write lands at an
arbitrary moment: the trigger only arms, and the pattern starts at the next
valid_strobe. Before that the stream is the idle alternation, which the filter
rejects completely, so the filter is in the same settled state at every
valid_strobe. The response after the fire therefore does not depend on which
valid_strobe it was, and neither does the impulse polarity: the idle toggle and
the decimation counter both run from the same reset, and valid_strobe lands on
an even count, so the toggle phase at the fire is always the same.

    from stimulus import Stimulus, PAT_STEP_P
    from decimator_model import DecimatorModel

    m, s = DecimatorModel(), Stimulus(PAT_STEP_P, opt=False)
    out = []
    for _ in range(128 * 120):
        y = m.step(s.next_bit(m.vs))
        if y is not None:
            out.append(y)
"""

from __future__ import annotations

PAT_STEP_P = 0b00
PAT_IMPULSE = 0b01
PAT_STEADY = 0b10
PAT_STEP_N = 0b11

PAT_NAMES = {PAT_STEP_P: "step+", PAT_IMPULSE: "impulse",
             PAT_STEADY: "steady", PAT_STEP_N: "step-"}

REPEAT = 64      # output samples between re-fires, and the step square period
LFSR_SEED = 1    # 23'h1, the same seed decimator_top_tb.v uses

# The idle toggle runs from rst_b, but the decimator's clock-enable counter runs
# from dec_rst_b, which the three-flop dec_en synchronizer releases three clocks
# later. Three is odd, so the toggle is inverted relative to the decimation
# window compared with a model that starts both together. It matters: it sets
# the impulse polarity and the exact overshoot of the step. Measured against the
# RTL, not assumed.
TOG_PHASE = 1


class Stimulus:
    """One pattern, advanced one clk_fs edge at a time.

    `settle` is how many valid_strobe events pass on the idle pattern before
    the fire. The RTL waits for an SPI write instead, but the filter is settled
    either way, so any value past the group delay gives the same answer.
    """

    def __init__(self, pat: int, opt: bool = False, settle: int = 20,
                 phase: int = TOG_PHASE):
        self.pat = pat
        self.opt = bool(opt)
        self.settle = settle
        self.tog = phase & 1
        self.armed = False
        self.fired = False
        self.run = False
        self.one = False
        self.rep_cnt = 0
        self.pat_cnt = 0
        self.lfsr = LFSR_SEED
        self._vs_seen = 0

    def _bit(self) -> int:
        """The output bit for this cycle, from the state before it advances."""
        if self.one:
            return 1 - self.tog
        if not self.fired:
            return self.tog
        if self.pat == PAT_STEP_P and self.run:
            return 1
        if self.pat == PAT_STEP_N and self.run:
            return 0
        if self.pat == PAT_STEADY:
            return self.lfsr & 1 if self.opt else (0 if self.pat_cnt == 3 else 1)
        return self.tog

    def next_bit(self, valid_strobe: bool) -> int:
        """Advance one clk_fs edge and return the bit the decimator sees."""
        bit = self._bit()

        self.tog ^= 1
        self.one = False

        self.pat_cnt = (self.pat_cnt + 1) & 3 if self.fired else 0

        if self.fired and self.pat == PAT_STEADY and self.opt:
            fb = ((self.lfsr >> 22) & 1) ^ ((self.lfsr >> 17) & 1)
            self.lfsr = ((self.lfsr << 1) | fb) & 0x7FFFFF

        if valid_strobe:
            self._vs_seen += 1
            if not self.fired and not self.armed and self._vs_seen >= self.settle:
                self.armed = True          # stands in for the SPI trigger write
            elif self.armed:
                self.armed = False
                self.fired = True
                self.rep_cnt = 0
                if self.pat == PAT_IMPULSE:
                    self.one = True
                elif self.pat in (PAT_STEP_P, PAT_STEP_N):
                    self.run = True
            elif self.fired and self.opt:
                # the RTL compares the count before this strobe's increment, a VHDL signal
                old = self.rep_cnt
                self.rep_cnt += 1
                if self.pat == PAT_IMPULSE:
                    if old == REPEAT - 1:
                        self.one = True
                        self.rep_cnt = 0
                elif self.pat in (PAT_STEP_P, PAT_STEP_N):
                    if old == REPEAT // 2 - 1:
                        self.run = not self.run
                    elif old == REPEAT - 1:
                        self.run = not self.run
                        self.rep_cnt = 0
        return bit


def predict(pat: int, opt: bool = False, n_out: int = 40, settle: int = 20) -> list:
    """The output words the chip produces for one pattern, from the fire onward."""
    from decimator_model import DecimatorModel

    model = DecimatorModel()
    stim = Stimulus(pat, opt, settle)
    out = []
    fired_at = None
    # Enough edges for the settle, the fire and n_out samples after it.
    for _ in range(128 * (settle + n_out + 8)):
        y = model.step(stim.next_bit(model.vs))
        if y is None:
            continue
        if fired_at is None:
            if stim.fired:
                fired_at = True
            continue
        out.append(y)
        if len(out) >= n_out:
            break
    return out


if __name__ == "__main__":
    for pat, opt, tag in ((PAT_STEP_P, False, "step+"),
                          (PAT_IMPULSE, False, "impulse"),
                          (PAT_STEADY, False, "half"),
                          (PAT_STEP_N, False, "step-"),
                          (PAT_STEADY, True, "prbs")):
        w = predict(pat, opt)
        print(f"{tag:8s} first={w[0]:>9d} peak={max(w, key=abs):>9d} last={w[-1]:>9d}")
