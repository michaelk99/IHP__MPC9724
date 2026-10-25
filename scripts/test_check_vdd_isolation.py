#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Tests of check_vdd_isolation on a small DEF."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("cvi", Path(__file__).resolve().parent / "check_vdd_isolation.py")
cvi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cvi)

DEF = """COMPONENTS 9 ;
    - IO_FILL_IO_SOUTH_3_0 sg13cmos5l_Filler4000 + FIXED ( 625000 140000 ) N ;
    - IO_FILL_IO_SOUTH_4_0 sg13cmos5l_Filler4000 + FIXED ( 655000 140000 ) N ;
    - IO_CORNER_SOUTH_EAST_INST sg13cmos5l_Corner + FIXED ( 980000 140000 ) FN ;
    - IO_FILL_IO_EAST_6_0 sg13cmos5l_Filler4000 + FIXED ( 980000 950000 ) W ;
    - cut_vdd_s sg13cmos5l_ip__cut_vdd + FIXED ( 645000 140000 ) N ;
    - cut_vdd_e sg13cmos5l_ip__cut_vdd + FIXED ( 980000 940000 ) W ;
    - vi_pad sg13cmos5l_IOPadAnalog + FIXED ( 980000 350000 ) W ;
    - g_vdd_pads\\[0\\].vdd_pad sg13cmos5l_IOPadVdd + FIXED ( 140000 630000 ) FW ;
    - dsm2 dsm2_core + FIXED ( 780000 375000 ) N ;
END COMPONENTS
SPECIALNETS 3 ;
    - VDD ( PIN VDD ) ( * VDD ) ( g_vdd_pads\\[0\\].vdd_pad vdd ) ( IO_FILL_IO_SOUTH_3_0 vdd ) ( IO_FILL_IO_EAST_6_0 vdd ) + USE POWER ;
    - VDDA ( vi_pad vdd ) ( dsm2 vdd )
      ( IO_FILL_IO_SOUTH_4_0 vdd ) ( IO_CORNER_SOUTH_EAST_INST vdd ) + USE POWER ;
    - VSS ( PIN VSS ) ( dsm2 vss ) + USE GROUND ;
END SPECIALNETS
"""
SEG = "vi_pad"


def check(text):
    return cvi.check(text, segment=SEG)


def main():
    assert check(DEF) == []
    # a segment pad moved to VDD
    bad = DEF.replace("( vi_pad vdd ) ", "").replace("( * VDD ) ", "( * VDD ) ( vi_pad vdd ) ")
    f = check(bad)
    assert f == ["vi_pad/vdd is not on VDDA but on VDD"], f
    # a filler on the wrong side of the south cut joins VDDA
    bad = DEF.replace("( IO_FILL_IO_SOUTH_3_0 vdd ) ", "").replace("( dsm2 vdd )", "( dsm2 vdd ) ( IO_FILL_IO_SOUTH_3_0 vdd )")
    f = check(bad)
    assert f == ["IO_FILL_IO_SOUTH_3_0/vdd is on VDDA but outside the segment"], f
    # a filler past the east cut is missing from VDD and sits on VDDA
    bad = DEF.replace("( IO_FILL_IO_EAST_6_0 vdd ) ", "").replace("( dsm2 vdd )", "( dsm2 vdd ) ( IO_FILL_IO_EAST_6_0 vdd )")
    f = check(bad)
    assert f == ["IO_FILL_IO_EAST_6_0/vdd is on VDDA but outside the segment"], f
    # dsm2 on both
    f = check(DEF.replace("( * VDD )", "( * VDD ) ( dsm2 vdd )"))
    assert f == ["dsm2/vdd is on both VDD and VDDA"], f
    # the cut cell must carry no vdd
    f = check(DEF.replace("( * VDD )", "( * VDD ) ( cut_vdd_s vdd )"))
    assert "cut_vdd_s/vdd is on VDD, the cut cell has no vdd" in f, f
    # a segment cell missing from the DEF
    f = cvi.check(DEF, segment="vi_pad,ghost_pad")
    assert f == ["segment cell ghost_pad is not in the DEF", "ghost_pad/vdd is not on VDDA"], f
    print("test_check_vdd_isolation: OK")


if __name__ == "__main__":
    main()
