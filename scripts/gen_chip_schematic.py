# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Generate schematic/xschem/sg13cmos5l_dsa1_dig_top.sch from the pad plan.

The pad ring, the pad order and the core wiring are already stated twice, in
flow/librelane/config.yaml and in rtl/sg13cmos5l_dsa1_dig_core.sv. A schematic
drawn by hand would be a third statement that has to be kept in step with both,
and the one this replaced had drifted so far it still described the template's
counters and inverters. So it is generated from the pad order instead.

What the schematic is for, and what it is not:

  - it is the reference netlist for the Xschem transient testbench, and the
    picture of the chip in the documentation
  - it is NOT the sign-off LVS reference. That is the synthesized netlist, and
    netgen compares the layout against it inside the flow. See doc/rtl2gds.md.

Run: python3 scripts/gen_chip_schematic.py
"""

from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "flow/librelane/config.yaml"
OUT = ROOT / "schematic/xschem/sg13cmos5l_dsa1_dig_top.sch"

IO = "sg13cmos5l_io/sg13cmos5l_"
PAD_SYM = {
    "input": IO + "IOPadIn.sym",
    "output": IO + "IOPadOut30mA.sym",
    "bidir": IO + "IOPadInOut30mA.sym",
    "analog": IO + "IOPadAnalog.sym",
    "vdd": IO + "IOPadVdd.sym",
    "vss": IO + "IOPadVss.sym",
    "iovdd": IO + "IOPadIOVdd.sym",
    "iovss": IO + "IOPadIOVss.sym",
    "clk": IO + "IOPadIn.sym",
    "rst_n": IO + "IOPadIn.sym",
    "clamp": "sg13cmos5l_ip__clamp_vddvss.sym",     # schematic/xschem, the ESD clamp cell
}

PDK_XSCHEM = Path(os.environ.get("PDK_ROOT", "/foss/pdks")) / \
    os.environ.get("PDK", "ihp-sg13cmos5l") / "libs.tech/xschem"

# The core-side signal pin, per pad kind. The supply pins are read from the
# symbol like everything else: IOPadAnalog and IOPadInOut30mA put theirs at
# different coordinates from the rest, which is not visible until a netlist
# comes out with the supplies on unnamed nets.
SIG_PIN = {"input": "p2c", "clk": "p2c", "rst_n": "p2c", "output": "c2p"}


def sym_pins(sym: str):
    """{pin name: (x, y)} from a symbol's pin boxes, in symbol-local coordinates.

    A name that appears twice keeps both, under 'name' and 'name#2', in file
    order. IOPadAnalog has two pins called 'pad', the bondpad and the bare core
    connection.
    """
    path = ROOT / "macros/dsa1_dig/schematic/xschem" / sym if sym.startswith("dsa1_dig") else \
        ROOT / "schematic/xschem" / sym if sym.startswith("sg13cmos5l_ip__") else PDK_XSCHEM / sym
    out = {}
    for m in re.finditer(r"^B 5 (\S+) (\S+) (\S+) (\S+) \{name=([^\s}]+)", path.read_text(), re.M):
        x1, y1, x2, y2 = (float(m.group(i)) for i in range(1, 5))
        name = m.group(5)
        key = name if name not in out else f"{name}#2"
        out[key] = (round((x1 + x2) / 2), round((y1 + y2) / 2))
    return out

# Side geometry, taken from the padframe picture the template draws.
STEP = 210
WEST_X, EAST_X, NORTH_Y, SOUTH_Y = 220, 2740, -3000, -480
WEST_Y = [-900 - STEP * i for i in range(9)]           # bottom to top, 9 with the clamp cell
EAST_Y = [-900 - STEP * i for i in range(8)]           # bottom to top
ROW_X = [640 + STEP * i for i in range(8)]             # left to right

# The macro, from macros/dsa1_dig/schematic/xschem/dsa1_dig_top.sym.
MACRO_X, MACRO_Y = 1700, -1700
MACRO_SYM = "dsa1_dig_top.sym"
FF_SYM = "sg13cmos5l_stdcells/sg13cmos5l_dfrbp_1.sym"
FF_X, FF_Y, FF_STEP = 700, -1700, 260


def rot(x: int, y: int, r: int):
    """xschem instance rotation, flip 0. Verified against the template's west pads."""
    return [(x, y), (-y, x), (-x, -y), (y, -x)][r]


def parse_pad_order():
    """The four PAD_* lists from the LibreLane config, as (kind, index) per side."""
    text = CONFIG.read_text()
    sides = {}
    for side in ("WEST", "NORTH", "SOUTH", "EAST"):
        # The closing bracket is the one at the start of a line: the entries
        # themselves contain escaped brackets, so a non-greedy .*?\] stops inside
        # the first entry.
        m = re.search(rf"^PAD_{side}:\s*\[(.*?)^\]", text, re.S | re.M)
        if not m:
            raise SystemExit(f"PAD_{side} not found in {CONFIG}")
        body = re.sub(r"#.*", "", m.group(1))
        # The config escapes the brackets for OpenROAD's regex matcher, and YAML
        # doubles the backslashes on top of that. Neither matters here.
        body = body.replace("\\", "").replace('"', "")
        entries = []
        for tok in (t.strip() for t in body.split(",")):
            if not tok:
                continue
            if tok == "clk_pad":
                entries.append(("clk", 0))
                continue
            if tok == "rst_n_pad":
                entries.append(("rst_n", 0))
                continue
            if tok == "clamp_vddvss":
                entries.append(("clamp", 0))
                continue
            g = re.match(r"g_\w+\[(\d+)\]\.(\w+)_pad$", tok)
            if not g:
                raise SystemExit(f"cannot parse pad entry {tok!r}")
            entries.append((g.group(2), int(g.group(1))))
        sides[side] = entries
    return sides


class Sheet:
    def __init__(self):
        self.lines = []
        self.n_inst = 0
        self.n_lab = 0
        self.n_pin = 0

    def inst(self, sym, x, y, r, extra="") -> str:
        self.n_inst += 1
        name = f"x{self.n_inst}"
        self.lines.append(f"C {{{sym}}} {x} {y} {r} 0 {{name={name}{extra}}}")
        return name

    def label(self, x, y, lab, r=0):
        self.n_lab += 1
        self.lines.append(
            f"C {{lab_pin.sym}} {x} {y} {r} 0 "
            f"{{name=l{self.n_lab} sig_type=std_logic lab={lab}}}")

    def port(self, kind, x, y, lab, r=0):
        self.n_pin += 1
        self.lines.append(
            f"C {{devices/{kind}.sym}} {x} {y} {r} 0 {{name=p{self.n_pin} lab={lab}}}")

    def text(self, x, y, s):
        self.lines.append(f"T {{{s}}} {x} {y} 0 0 0.4 0.4 {{}}")


def pad_net(kind, idx):
    """(core-side net, top-level port label, port symbol) for one pad."""
    if kind == "clk":
        return "clk", "clk_PAD", "ipin"
    if kind == "rst_n":
        return "rst_n", "rst_n_PAD", "ipin"
    if kind == "input":
        return ["data_in_pad", "sclk", "mosi", "ss"][idx], f"input_PAD[{idx}]", "ipin"
    if kind == "output":
        core = {0: "miso", 1: "adc_conv"}.get(idx, f"o_tst_ctrl[{idx - 2}]")
        return core, f"output_PAD[{idx}]", "opin"
    if kind == "bidir":
        return None, f"bidir_PAD[{idx}]", "iopin"
    if kind == "analog":
        return None, f"analog_PAD[{idx}]", "iopin"
    if kind == "clamp":
        return None, None, None
    return None, {"vdd": "VDD", "vss": "VSS",
                  "iovdd": "IOVDD", "iovss": "IOVSS"}[kind], "iopin"


def place_pad(sh, kind, idx, x, y, r):
    sym = PAD_SYM[kind]
    pins = sym_pins(sym)
    sh.inst(sym, x, y, r)
    core, port, ptype = pad_net(kind, idx)

    def put(pin, lab, as_port=False):
        dx, dy = rot(*pins[pin], r)
        if as_port:
            sh.port(ptype, x + dx, y + dy, lab, r)
        else:
            sh.label(x + dx, y + dy, lab)

    for supply in ("vss", "vdd", "iovss", "iovdd"):
        put(supply, supply.upper())

    if kind == "clamp":                # no bondpad, the four rails only
        return

    if kind in ("vdd", "vss", "iovdd", "iovss"):
        # The bondpad-side pin carries the same name as the supply it feeds.
        put(f"{kind}#2", port, as_port=True)
        return

    if kind == "analog":
        # Bondpad plus two spare core-side pins, bare and through the series
        # resistor. Neither is connected in this chip.
        put("pad#2", port, as_port=True)
        for pin in ("pad", "padres"):
            dx, dy = rot(*pins[pin], r)
            sh.lines.append(
                f"C {{noconn.sym}} {x + dx} {y + dy} 0 0 {{name=nc_an{idx}_{pin}}}")
        return

    put("pad", port, as_port=True)

    if kind == "bidir":
        # Spare: driven low and never enabled, as the core RTL does.
        put("c2p", "VSS")
        put("c2p_en", "VSS")
        dx, dy = rot(*pins["p2c"], r)
        sh.lines.append(
            f"C {{noconn.sym}} {x + dx} {y + dy} 0 0 {{name=nc_bd{idx}_p2c}}")
        return

    put(SIG_PIN[kind], core)


def build():
    sides = parse_pad_order()
    sh = Sheet()

    sh.text(300, -3200, "sg13cmos5l_dsa1_dig_top: DSADC1 digital back end, 32-pad QFN")
    sh.text(300, -3150,
            "Generated by scripts/gen_chip_schematic.py from the PAD_* lists in "
            "flow/librelane/config.yaml. Do not hand edit.")
    sh.text(300, -3100,
            "Sign-off LVS is netgen against the synthesized netlist, not this sheet. "
            "See doc/rtl2gds.md.")

    for (kind, idx), y in zip(sides["WEST"], WEST_Y, strict=True):
        place_pad(sh, kind, idx, WEST_X, y, 1)
    for (kind, idx), y in zip(sides["EAST"], EAST_Y, strict=True):
        place_pad(sh, kind, idx, EAST_X, y, 3)
    for (kind, idx), x in zip(sides["NORTH"], ROW_X, strict=True):
        place_pad(sh, kind, idx, x, NORTH_Y, 2)
    for (kind, idx), x in zip(sides["SOUTH"], ROW_X, strict=True):
        place_pad(sh, kind, idx, x, SOUTH_Y, 0)

    # Three-flop synchronizer on the bitstream. data_in has no timing
    # relationship to clk, so the core resynchronizes it before the macro.
    # Synthesis maps these to EZ130 DFFRQX3, whose views stay outside this
    # repo, so the PDK's dfrbp_1 stands in. Functionally identical, Q_N left open.
    ff = sym_pins(FF_SYM)
    src = "data_in_pad"
    for stage in range(3):
        fy = FF_Y + FF_STEP * stage
        sh.inst(FF_SYM, FF_X, fy, 0)
        out = f"data_in_s{stage + 1}"
        for pin, lab in (("CLK", "clk"), ("D", src), ("RESET_B", "rst_n"), ("Q", out)):
            sh.label(FF_X + ff[pin][0], fy + ff[pin][1], lab)
        sh.lines.append(
            f"C {{noconn.sym}} {FF_X + ff['Q_N'][0]} {fy + ff['Q_N'][1]} 0 0 "
            f"{{name=nc_ffqn{stage}}}")
        src = out
    sh.text(FF_X - 170, FF_Y - 160, "bitstream synchronizer, 3 stages")

    # The macro. Its pins come from the symbol, which symbol-gl regenerates from
    # the powered netlist, so a port change shows up here rather than silently.
    mp = sym_pins(MACRO_SYM)
    sh.inst(MACRO_SYM, MACRO_X, MACRO_Y, 0)
    macro_net = {"clk": "clk", "data_in": "data_in_s3", "mosi": "mosi",
                 "rst_b": "rst_n", "sclk": "sclk", "ss": "ss",
                 "adc_conv": "adc_conv", "miso": "miso",
                 "VDD": "VDD", "VSS": "VSS",
                 "o_tst_ctrl": "o_tst_ctrl[0..15]"}
    for pin, (dx, dy) in mp.items():
        base = pin.split("[")[0]
        # A bus pin left on a noconn collapses to a single net, which shorts all
        # its bits together. The configuration outputs stay inside the die but
        # they are still 145 separate signals, so each bus keeps its own name.
        sh.label(MACRO_X + dx, MACRO_Y + dy, macro_net.get(base, pin))
    sh.text(MACRO_X - 140, MACRO_Y - 230,
            "145 configuration bits stay on die, only o_tst_ctrl is bonded out")

    head = ["v {xschem version=3.4.8RC file_version=1.3}", "G {}", "K {}",
            "V {}", "S {}", "F {}", "E {}"]
    OUT.write_text("\n".join(head + sh.lines) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: "
          f"{sh.n_inst} instances, {sh.n_lab} labels, {sh.n_pin} ports")


if __name__ == "__main__":
    build()
