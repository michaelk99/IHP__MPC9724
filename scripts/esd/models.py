# SPDX-FileCopyrightText: 2026 Harald Pretl, Johannes Kepler University
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Ported from OpenBLAU 8f25e634, scripts/esd/models.py
# Description: IO library netlist with high-current ESD diodes, for the HBM bench
"""Writes <run>/io_esd.spice: the PDK's sg13cmos5l_io.spice with every
dantenna/dpantenna replaced by esd_dn/esd_dp, a high-current diode, and every
`ptap1 R=` substrate tie as `esd_ptap`: the PDK's own ptap1 subcircuit takes
w/l and not the R= the IO netlist writes. Appended: the EZ130 cells the core
hangs on the pads (BUFX3 behind every output pad, TIELO behind the bidir
pads' c2p and c2p_en), from $EZ130_DIR's CDL with M cards turned into X.

The PDK diode cards are fitted from -15 V to +1 V for reverse bias only, with
an area-scaled rs of kilohms and a high-injection knee near 5 uA, so at HBM
current they read kilovolts forward.

Needs the IO netlist with the substrate (`sub!`) and its ties drawn in, which
ships as `.spice` in hpretl/iic-osic-tools:2026.09 (PDK c271a7e). The sign-off
image 2026.08 ships a `.spi` without either and with another port order, so
the bench reads the port order from the file.

RON is the on-resistance of a 35 um^2 junction, the esd PCell's 2 kV diode,
and every diode scales from it by area. It is unknown for this process, so the
bench sweeps it. The rail clamps stay PSP: an RC-triggered clamp conducts as a
MOSFET and needs no snapback model.

  python3 scripts/esd/models.py <run dir>       (needs $PDK_ROOT, $PDK, $EZ130_DIR)
  python3 scripts/esd/models.py --selftest
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CORE_CELLS = ("BUFX3", "TIELO")   # what the core drives the pads with
# area parameters from the PDK cards (diodes.lib darea/dparea, per um^2),
# normalized to a 35 um^2 device
MODELS = """\
* high-current ESD diodes: PDK saturation current, ideality, junction C and
* breakdown per um^2, times 35 um^2; rs = RON for that area; no transit time
.model esd_dn_hc D (is={35*2.315e-19} n=1.009 rs={RON} cj0={35*9.371e-16} m=0.3036
+ vj=0.696 fc=0.5 bv=11.64 ibv=1e-6 tt=0)
.model esd_dp_hc D (is={35*8.569e-20} n=1.003 rs={RON} cj0={35*8.252e-16} m=0.3171
+ vj=0.6628 fc=0.5 bv=12.14 ibv=1e-6 tt=0)

* n+ in p-well (dantenna) and p+ in n-well (dpantenna), PDK node order
.subckt esd_dn 1 2 l=780n w=780n
D1 1 2 esd_dn_hc area={l*w/35p}
.ends esd_dn
.subckt esd_dp 1 2 l=780n w=780n
D1 1 2 esd_dp_hc area={l*w/35p}
.ends esd_dp

* substrate tie, as the IO netlist writes it (R= from the drawn tap area)
.subckt esd_ptap 1 2 R=1
R1 1 2 {R}
.ends esd_ptap

"""


# A vdd-to-vss supply clamp: IHP's IOPadVdd RC clamp with its source on vss and the
# NMOS doubled, as OpenBLAU's RF pad carries it (OpenBLAU 8f25e634, models.py RFPAD).
# hbm.py --clamp places it in a slot, to price it before it is drawn.
CLAMP = """
* vdd-to-vss RC clamp, on its own ports
.subckt esd_clamp_vddvss clv cls
Xcl clv clg cls cls sg13_hv_nmos w=1512u l=0.6u ng=168
Xcap cls rc cls cls sg13_hv_nmos w=126u l=9.5u ng=14
Xinvn clg rc cls cls sg13_hv_nmos w=108u l=0.5u ng=16
Xinvp clg rc clv clv sg13_hv_pmos w=350u l=0.5u ng=50
Rtrig clv rc 129.3k
.ends esd_clamp_vddvss
.subckt esd_clamp_vddvss_half clv cls
Xcl clv clg cls cls sg13_hv_nmos w=756u l=0.6u ng=84
Xcap cls rc cls cls sg13_hv_nmos w=126u l=9.5u ng=14
Xinvn clg rc cls cls sg13_hv_nmos w=108u l=0.5u ng=16
Xinvp clg rc clv clv sg13_hv_pmos w=350u l=0.5u ng=50
Rtrig clv rc 129.3k
.ends esd_clamp_vddvss_half
* the drawn clamp cell, ip/sg13cmos5l_ip__clamp_vddvss: three of IHP's clamp blocks
.subckt esd_clamp_vddvss_cell clv cls
Xcl clv clg cls cls sg13_hv_nmos w=2268u l=0.6u ng=252
Xcap cls rc cls cls sg13_hv_nmos w=126u l=9.5u ng=14
Xinvn clg rc cls cls sg13_hv_nmos w=108u l=0.5u ng=16
Xinvp clg rc clv clv sg13_hv_pmos w=350u l=0.5u ng=50
Rtrig clv rc 129.3k
.ends esd_clamp_vddvss_cell
"""


def die(msg):
    sys.stderr.write(f"models: {msg}\n")
    sys.exit(1)


def patch(lines):
    """The netlist with the antenna diodes swapped for the high-current ones."""
    out, n = [], 0
    for ln in lines:
        new = re.sub(r"\bdantenna\b", "esd_dn", ln)
        new = re.sub(r"\bdpantenna\b", "esd_dp", new)
        new = re.sub(r"\bptap1 R=", "esd_ptap R=", new)
        n += new != ln
        out.append(new)
    return out, n


def core_cells(cdl, cells=CORE_CELLS):
    """The named subcircuits of a CDL, M cards as X (the PDK MOS are subckts)."""
    out, keep = [], False
    for ln in open(cdl):
        t = ln.split()
        if t and t[0].upper() == ".SUBCKT":
            keep = t[1] in cells
        if keep:
            if re.match(r"^\s*M", ln) and "=" in ln:
                i = len(ln) - len(ln.lstrip())
                ln = ln[:i] + "X" + ln[i + 1:]
            out.append(ln)
        if t and t[0].upper() == ".ENDS":
            keep = False
    got = {ln.split()[1] for ln in out if ln.split()[0].upper() == ".SUBCKT"}
    if got != set(cells):
        die(f"{cdl}: missing {sorted(set(cells) - got)}")
    return out


def build(run):
    pdk = os.path.join(os.environ.get("PDK_ROOT", "/foss/pdks"),
                       os.environ.get("PDK", "ihp-sg13cmos5l"))
    spi = os.path.join(pdk, "libs.ref", "sg13cmos5l_io", "spice", "sg13cmos5l_io.spice")
    if not os.path.isfile(spi):
        die(f"no {spi}: run in hpretl/iic-osic-tools:2026.09 (see the docstring)")
    lines = open(spi).readlines()
    if not any("ptap1" in ln for ln in lines):
        die(f"{spi} carries no substrate ties: not the netlist this was written for")
    lines, nd = patch(lines)
    if nd < 10:
        die(f"only {nd} diodes swapped: has the library changed?")
    ez = os.environ.get("EZ130_DIR")
    if not ez:
        die("EZ130_DIR is not set")
    core = core_cells(os.path.join(ez, "cdl", "ez130_8t.cdl"))
    os.makedirs(run, exist_ok=True)
    dst = os.path.join(run, "io_esd.spice")
    with open(dst, "w") as f:
        f.write(f"* generated by scripts/esd/models.py from {spi}\n")
        f.write(".global sub!\n")
        f.write(MODELS)
        f.write(CLAMP)
        f.writelines(lines)
        f.write(f"\n* EZ130 core cells behind the pads, from {ez}/cdl/ez130_8t.cdl\n")
        f.writelines(core)
    print(f"models: {dst}: {nd} diodes swapped, core cells {', '.join(CORE_CELLS)}")
    return dst


def selftest():
    spi = [".subckt c vss iovss pad\n", "XD1 sub! pad dantenna l=1u w=2u m=1\n",
           "XD2 pad vss dpantenna l=1u w=2u m=1\n", ".ends\n"]
    out, n = patch(spi)
    s = "".join(out)
    assert n == 2, n
    assert "esd_dn l=1u" in s and "esd_dp l=1u" in s and "antenna" not in s
    assert patch(["XR0 a sub! ptap1 R=5\n"])[0] == ["XR0 a sub! esd_ptap R=5\n"]
    import tempfile
    p = os.path.join(tempfile.mkdtemp(), "c.cdl")
    open(p, "w").write(".SUBCKT INVX1 A VDD VSS Y\nMN0 Y A VSS VSS sg13_lv_nmos w=1u\n.ENDS\n"
                       ".SUBCKT BUFX3 A VDD VNW VPW VSS Y\nMP1 Y n VDD VNW sg13_lv_pmos w=1u\n"
                       ".ENDS\n")
    got = core_cells(p, ("BUFX3",))
    assert got[0].startswith(".SUBCKT BUFX3") and got[1].startswith("XP1 ") and len(got) == 3, got
    print("models: selftest passed")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    elif len(sys.argv) == 2:
        build(sys.argv[1])
    else:
        die(__doc__)
