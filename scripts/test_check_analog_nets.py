#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Tests of check_analog_nets on a small hand-written netlist."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("can", Path(__file__).resolve().parent / "check_analog_nets.py")
can = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(can)

NETLIST = r"""
module top (clk_PAD);
  input clk_PAD;
  wire vi, \dsm_do_q , n1;
  sg13cmos5l_IOPadAnalog vi_pad (.padres(vi), .pad(analog_PAD[0]));
  dsm2_core dsm2 (.vi(vi), .do_q(\dsm_do_q ), .vdd(VDDA));
  sg13cmos5l_IOPadOut4mA do_q_pad (.c2p(\dsm_do_q ), .pad(do_q_PAD));
  INVX1 u_gate (.A(n1), .Y(x));
endmodule
"""
SPEC = "vi: vi_pad/padres dsm2/vi\ndsm_do_q: dsm2/do_q do_q_pad/c2p  # escaped name\n"
CFG = 'RSZ_DONT_TOUCH_RX: "^(vi|dsm_do_q|u_gate)$"\n'


def main():
    assert can.check(NETLIST, SPEC, CFG) == []
    # an antenna diode on vi
    bad = NETLIST.replace("endmodule", "  sg13cmos5l_antennanp ant (.A(vi));\nendmodule")
    f = can.check(bad, SPEC)
    assert f == ["vi also touches ant/A"], f
    # vi renamed
    f = can.check(NETLIST.replace("vi", "vx").replace("vx_pad", "vi_pad").replace("dsm2_core dsm2 (.vx(vx)", "dsm2_core dsm2 (.vi(vx)"), SPEC)
    assert f == ["vi not in netlist"], f
    # a net in an assign
    f = can.check(NETLIST.replace("endmodule", "  assign vi = n1;\nendmodule"), SPEC)
    assert f == ["vi appears in an assign"], f
    # a listed pin that is not connected
    f = can.check(NETLIST, SPEC + "vi: vi_pad/padres dsm2/vi u_gate/A\n")
    assert f == ["vi does not touch u_gate/A"], f
    # a regex alternative that matches nothing
    f = can.check(NETLIST, SPEC, 'RSZ_DONT_TOUCH_RX: "^(vi|vcm|u_gate)$"\n')
    assert f == ["regex alternative vcm matches no net and no instance"], f
    # a net inside a concatenation counts as a connection of that pin
    f = can.check(NETLIST.replace("endmodule", "  INVX1 u_cat (.A({vi, n1, 1'b0}), .Y(y));\nendmodule"), SPEC)
    assert f == ["vi also touches u_cat/A"], f
    # a connection that is not a net, a constant or a concatenation of those fails loudly
    for bad in (".A(vi & n1)", ".A({2{vi}})", "vi"):
        f = can.check(NETLIST.replace("endmodule", "  INVX1 u_odd (%s, .Y(y));\nendmodule" % bad), SPEC)
        assert f == ["u_odd: cannot parse the connection %s" % bad], f
    # an optional glob admits antenna diodes on one net only
    spec = SPEC + "n1: u_gate/A ANTENNA_*/A?\n"
    with_diode = NETLIST.replace("endmodule", "  ANTENNA2 ANTENNA_1 (.A(n1));\nendmodule")
    assert can.check(with_diode, spec) == []
    assert can.check(with_diode, SPEC + "n1: u_gate/A\n") == ["n1 also touches ANTENNA_1/A"]
    assert can.check(NETLIST, spec) == []
    # a name that is only an instance does not count as a net in the netlist
    f = can.check(NETLIST, SPEC + "u_gate: u_gate/A\n")
    assert f == ["u_gate not in netlist"], f
    print("test_check_analog_nets: OK")


if __name__ == "__main__":
    main()
