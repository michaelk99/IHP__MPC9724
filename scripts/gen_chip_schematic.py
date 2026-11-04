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

It also writes the chip symbol next to it, the pin list the testbench uses.

Run: python3 scripts/gen_chip_schematic.py
"""

from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "flow/librelane/config.yaml"
OUT = ROOT / "schematic/xschem/sg13cmos5l_dsa1_dig_top.sch"
SYM = ROOT / "schematic/xschem/sg13cmos5l_dsa1_dig_top.sym"

IO = "sg13cmos5l_io/sg13cmos5l_"
PAD_SYM = {
    "input": IO + "IOPadIn.sym",
    "output": IO + "IOPadOut30mA.sym",
    "analog": IO + "IOPadAnalog.sym",
    "vdd": IO + "IOPadVdd.sym",
    "vss": IO + "IOPadVss.sym",
    "iovdd": IO + "IOPadIOVdd.sym",
    "iovss": IO + "IOPadIOVss.sym",
    "clk": IO + "IOPadIn.sym",
    "rst_n": IO + "IOPadIn.sym",
    "clamp": "sg13cmos5l_ip__clamp_vddvss.sym",     # schematic/xschem, the ESD clamp cell
    "clamp_vdda": "sg13cmos5l_ip__clamp_vddvss.sym",
    "cut": "sg13cmos5l_ip__cut_vdd.sym",            # schematic/xschem, the vdd band cut
    "vdda": IO + "IOPadVdd.sym",
    "dsm_clk": IO + "IOPadIn.sym",
    "output4": IO + "IOPadOut4mA.sym",
}
DSM2_SYM = "dsm2_core.sym"                          # schematic/xschem, the hard macro's pins
MUX_SYM = "sg13cmos5l_stdcells/sg13cmos5l_mux2_1.sym"
AND_SYM = "sg13cmos5l_stdcells/sg13cmos5l_and2_1.sym"

# The kinds on the VDDA segment of the ring: their vdd pin is VDDA, not VDD.
SEGMENT = {"vdda", "clamp_vdda", "output4", "analog", "dsm_clk"}
# The pad entries of the config that are not g_<group>[i].<kind>_pad.
NAMED = {"clk_pad": ("clk", 0), "rst_n_pad": ("rst_n", 0), "clamp_vddvss": ("clamp", 0),
         "clamp_vdda": ("clamp_vdda", 0), "cut_vdd_s": ("cut", 0), "cut_vdd_e": ("cut", 1),
         "vi_pad": ("analog", 0), "vcm_pad": ("analog", 1), "ib_pad": ("analog", 2),
         "vdda_pad": ("vdda", 0), "dsm_clk_pad": ("dsm_clk", 0),
         "do_q_pad": ("output4", 0), "do_q_b_pad": ("output4", 1)}
# The dsm2 analog pin behind each analog pad, and the pad's port.
ANALOG_NET = ("vi", "vcm", "ibias_test")

PDK_XSCHEM = Path(os.environ.get("PDK_ROOT", "/foss/pdks")) / \
    os.environ.get("PDK", "ihp-sg13cmos5l") / "libs.tech/xschem"

# The core-side signal pin, per pad kind. The supply pins are read from the
# symbol like everything else: IOPadAnalog puts its at different coordinates
# from the rest, which is not visible until a netlist
# comes out with the supplies on unnamed nets.
SIG_PIN = {"input": "p2c", "clk": "p2c", "rst_n": "p2c", "dsm_clk": "p2c", "output": "c2p",
           "output4": "c2p"}


def sym_pins(sym: str):
    """{pin name: (x, y)} from a symbol's pin boxes, in symbol-local coordinates.

    A name that appears twice keeps both, under 'name' and 'name#2', in file
    order. IOPadAnalog has two pins called 'pad', the bondpad and the bare core
    connection.
    """
    local = sym.startswith(("sg13cmos5l_ip__", "dsm2_core"))
    path = ROOT / "macros/dsa1_dig/schematic/xschem" / sym if sym.startswith("dsa1_dig") else \
        ROOT / "schematic/xschem" / sym if local else PDK_XSCHEM / sym
    out = {}
    for m in re.finditer(r"^B 5 (\S+) (\S+) (\S+) (\S+) \{name=([^\s}]+)", path.read_text(), re.M):
        x1, y1, x2, y2 = (float(m.group(i)) for i in range(1, 5))
        name = m.group(5)
        key = name if name not in out else f"{name}#2"
        out[key] = ((x1 + x2) / 2, (y1 + y2) / 2)     # half units: IOPadAnalog's pins sit on x.5
    return out

# Side geometry, taken from the padframe picture the template draws.
STEP = 210
WEST_X, EAST_X, NORTH_Y, SOUTH_Y = 220, 2740, -3000, -480
WEST_Y = [-900 - STEP * i for i in range(8)]           # bottom to top
EAST_Y = [-900 - STEP * i for i in range(8)]           # bottom to top
ROW_X = [640 + STEP * i for i in range(8)]             # left to right

# The macro, from macros/dsa1_dig/schematic/xschem/dsa1_dig_top.sym.
MACRO_X, MACRO_Y = 1700, -1700
MACRO_SYM = "dsa1_dig_top.sym"
DSM_X, DSM_Y = 1700, -1050
FF_SYM = "sg13cmos5l_stdcells/sg13cmos5l_dfrbp_1.sym"
FF_X, FF_Y, FF_STEP = 700, -1700, 260


def rot(x: int, y: int, r: int):
    """xschem instance rotation, flip 0. Verified against the template's west pads."""
    return [(x, y), (-y, x), (-x, -y), (y, -x)][r]


def n(v):
    """A coordinate for the sheet: whole numbers without the point."""
    return f"{v:g}"


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
            if tok in NAMED:
                entries.append(NAMED[tok])
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
            f"C {{lab_pin.sym}} {n(x)} {n(y)} {r} 0 "
            f"{{name=l{self.n_lab} sig_type=std_logic lab={lab}}}")

    def port(self, kind, x, y, lab, r=0):
        self.n_pin += 1
        self.lines.append(
            f"C {{devices/{kind}.sym}} {n(x)} {n(y)} {r} 0 {{name=p{self.n_pin} lab={lab}}}")

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
        return ["miso", "adc_conv"][idx], f"output_PAD[{idx}]", "opin"
    if kind == "dsm_clk":
        return "dsm_clk", "dsm_clk_PAD", "ipin"
    if kind == "output4":
        return ["dsm_do_q", "dsm_do_q_b"][idx], ["do_q_PAD", "do_q_b_PAD"][idx], "opin"
    if kind == "analog":
        return ANALOG_NET[idx], f"analog_PAD[{idx}]", "iopin"
    if kind in ("clamp", "clamp_vdda", "cut"):
        return None, None, None
    return None, {"vdd": "VDD", "vdda": "VDDA", "vss": "VSS",
                  "iovdd": "IOVDD", "iovss": "IOVSS"}[kind], "iopin"


def place_pad(sh, kind, idx, x, y, r):
    sym = PAD_SYM[kind]
    pins = sym_pins(sym)
    sh.inst(sym, x, y, r)
    core, port, ptype = pad_net(kind, idx)
    vdd = "VDDA" if kind in SEGMENT else "VDD"

    def put(pin, lab, as_port=False):
        dx, dy = rot(*pins[pin], r)
        if as_port:
            sh.port(ptype, x + dx, y + dy, lab, r)
        else:
            sh.label(x + dx, y + dy, lab)

    for supply, net in (("vss", "VSS"), ("vdd", vdd), ("iovss", "IOVSS"), ("iovdd", "IOVDD")):
        if supply in pins:                 # the cut cell has no vdd
            put(supply, net)

    if kind in ("clamp", "clamp_vdda", "cut"):     # no bondpad, the rails only
        return

    if kind in ("vdd", "vdda", "vss", "iovdd", "iovss"):
        # The bondpad-side pin carries the same name as the supply it feeds.
        put(f"{'vdd' if kind == 'vdda' else kind}#2", port, as_port=True)
        return

    if kind == "analog":
        # The bondpad, the series resistor to the dsm2 pin, and the bare core
        # pin, which is not connected.
        put("pad#2", port, as_port=True)
        put("padres", core)
        dx, dy = rot(*pins["pad"], r)
        sh.lines.append(
            f"C {{noconn.sym}} {n(x + dx)} {n(y + dy)} 0 0 {{name=nc_an{idx}_pad}}")
        return

    put("pad", port, as_port=True)
    put(SIG_PIN[kind], core)


def build():
    sides = parse_pad_order()
    sh = Sheet()

    sh.text(300, -3200, "sg13cmos5l_dsa1_dig_top: DSADC1 digital back end and the dsm2 modulator, QFN24")
    sh.text(300, -3150,
            "Generated by scripts/gen_chip_schematic.py from the PAD_* lists in "
            "flow/librelane/config.yaml. Do not hand edit.")
    sh.text(300, -3100,
            "Sign-off LVS is netgen against the synthesized netlist, not this sheet. "
            "See doc/rtl2gds.md.")

    for (kind, idx), y in zip(sides["WEST"], WEST_Y):
        place_pad(sh, kind, idx, WEST_X, y, 1)
    for (kind, idx), y in zip(sides["EAST"], EAST_Y):
        place_pad(sh, kind, idx, EAST_X, y, 3)
    for (kind, idx), x in zip(sides["NORTH"], ROW_X):
        place_pad(sh, kind, idx, x, NORTH_Y, 2)
    for (kind, idx), x in zip(sides["SOUTH"], ROW_X):
        place_pad(sh, kind, idx, x, SOUTH_Y, 0)

    # Three-flop synchronizer on the bitstream. data_in has no timing
    # relationship to clk, so the core resynchronizes it before the macro.
    # DEC_SRC (o_bias_cfg[21]) selects dsm2's do_q_dec in place of the pad.
    # Synthesis maps these to EZ130 cells, whose views stay out of this repo,
    # so the PDK's dfrbp_1, mux2_1 and and2_1 stand in. Functionally identical,
    # Q_N left open.
    ff = sym_pins(FF_SYM)
    mx, an = sym_pins(MUX_SYM), sym_pins(AND_SYM)
    mux_x, mux_y = FF_X - 260, FF_Y
    sh.inst(MUX_SYM, mux_x, mux_y, 0)
    for pin, lab in (("A0", "data_in_pad"), ("A1", "dsm_bit"), ("S", "o_bias_cfg[21]"),
                     ("X", "data_in_mux")):
        sh.label(mux_x + mx[pin][0], mux_y + mx[pin][1], lab)
    src = "data_in_mux"
    for stage in range(3):
        fy = FF_Y + FF_STEP * stage
        sh.inst(FF_SYM, FF_X, fy, 0)
        out = f"data_in_s{stage + 1}"
        for pin, lab in (("CLK", "clk"), ("D", src), ("RESET_B", "rst_n"), ("Q", out)):
            sh.label(FF_X + ff[pin][0], fy + ff[pin][1], lab)
        sh.lines.append(
            f"C {{noconn.sym}} {n(FF_X + ff['Q_N'][0])} {n(fy + ff['Q_N'][1])} 0 0 "
            f"{{name=nc_ffqn{stage}}}")
        src = out
    sh.text(FF_X - 170, FF_Y - 160, "bitstream synchronizer, 3 stages, with the DEC_SRC mux")
    for (gx, gy), (a_net, b_net, x_net) in zip(
            ((FF_X - 260, FF_Y - 300), (MACRO_X + 600, MACRO_Y - 300)),
            (("dsm_do_q_dec", "o_bias_cfg[21]", "dsm_bit"),
             ("adc_conv_raw", "o_bias_cfg[25]", "adc_conv"))):
        sh.inst(AND_SYM, gx, gy, 0)
        for pin, lab in (("A", a_net), ("B", b_net), ("X", x_net)):
            sh.label(gx + an[pin][0], gy + an[pin][1], lab)
    sh.text(MACRO_X + 540, MACRO_Y - 340, "adc_conv gate")

    # The macro. Its pins come from the symbol, which symbol-gl regenerates from
    # the powered netlist, so a port change shows up here rather than silently.
    mp = sym_pins(MACRO_SYM)
    sh.inst(MACRO_SYM, MACRO_X, MACRO_Y, 0)
    macro_net = {"clk": "clk", "data_in": "data_in_s3", "mosi": "mosi",
                 "rst_b": "rst_n", "sclk": "sclk", "ss": "ss",
                 "adc_conv": "adc_conv_raw", "miso": "miso",
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

    # dsm2 as the hard macro it is, on VDDA. The config bits come off
    # o_bias_cfg as in rtl/sg13cmos5l_dsa1_dig_core.sv.
    dp = sym_pins(DSM2_SYM)
    dsm_net = {"vdd": "VDDA", "vss": "VSS", "vi": "vi", "vcm": "vcm",
               "ibias_test": "ibias_test", "di_clk": "dsm_clk", "di_ena": "o_bias_cfg[19]",
               "di_rst_b": "o_bias_cfg[20]", "di_trim": "o_bias_cfg[6:3]",
               "di_dith_en": "o_bias_cfg[7]", "di_dith_amp": "o_bias_cfg[9:8]",
               "di_vcm_ext": "o_bias_cfg[23]", "di_btest_en": "o_bias_cfg[22]",
               "di_qout_en": "o_bias_cfg[24]", "do_q": "dsm_do_q", "do_q_b": "dsm_do_q_b",
               "do_q_dec": "dsm_do_q_dec"}
    sh.inst(DSM2_SYM, DSM_X, DSM_Y, 0)
    for pin, (dx, dy) in dp.items():
        sh.label(DSM_X + dx, DSM_Y + dy, dsm_net[pin.split("[")[0]])

    head = ["v {xschem version=3.4.8RC file_version=1.3}", "G {}", "K {}",
            "V {}", "S {}", "F {}", "E {}"]
    OUT.write_text("\n".join(head + sh.lines) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: "
          f"{sh.n_inst} instances, {sh.n_lab} labels, {sh.n_pin} ports")


CHIP_TOP = ("VDD", "VDDA")
CHIP_BOTTOM = ("VSS",)
CHIP_RIGHT = ("clk_PAD", "rst_n_PAD", "IOVSS", "IOVDD", "analog_PAD[0..2]", "input_PAD[0..3]",
              "output_PAD[0..1]", "dsm_clk_PAD", "do_q_PAD", "do_q_b_PAD")


def write_symbol():
    """The chip symbol: the supplies on top and bottom, the pads on the right."""
    h = 20 * len(CHIP_RIGHT) + 20
    out = ["v {xschem version=3.4.8RC file_version=1.3}", "G {}",
           'K {type=primitive\nformat="@name @pinlist @symname"\n'
           'spectre_format="@name ( @pinlist ) @symname"\ntemplate="name=x1"}',
           "V {}", "S {}", "F {}", "E {}"]
    pins = []
    for i, n in enumerate(CHIP_TOP):
        pins.append((n, -40 + 80 * i, -h - 20, "t"))
    for n in CHIP_BOTTOM:
        pins.append((n, 0, h + 20, "b"))
    for i, n in enumerate(CHIP_RIGHT):
        pins.append((n, 160, -h + 40 + 40 * i, "r"))
    for n, x, y, side in pins:
        if side == "r":
            out.append(f"L 7 160 {y} 140 {y} {{}}")
        else:
            out.append(f"L 7 {x} {y} {x} {y + (20 if side == 't' else -20)} {{}}")
    for n, x, y, side in pins:
        pin = n.split("[")[0]
        out.append(f"B 5 {x - 2.5} {y - 2.5} {x + 2.5} {y + 2.5} "
                   f"{{name={n} dir=inout sim_pinname={pin}}}")
    out.append(f"P 4 5 -140 {-h} 140 {-h} 140 {h} -140 {h} -140 {-h} {{}}")
    out.append(f"T {{@symname}} 20 {-h - 1} 0 0 0.2 0.2 {{}}")
    out.append(f"T {{@name}} 20 {-h - 17} 0 0 0.2 0.2 {{}}")
    for n, x, y, side in pins:
        if side == "r":
            out.append(f"T {{{n}}} 135 {y + 4} 0 1 0.2 0.2 {{}}")
        else:
            out.append(f"T {{{n}}} {x - 5} {y + (-4 if side == 't' else 4)} 0 1 0.2 0.2 {{}}")
    SYM.write_text("\n".join(out) + "\n")
    print(f"wrote {SYM.relative_to(ROOT)}: {len(pins)} pins")


if __name__ == "__main__":
    build()
    write_symbol()
