# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""The dsm2 overlay of BIAS_CFG_0/1: this die's fields and resets, and the DSA1 die's view unchanged."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("regmap_defs", Path(__file__).resolve().parent / "regmap_defs.py")
defs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(defs)


def fields(die, reg):
    r = next(r for r in defs.REGISTERS[die] if r["name"] == reg)
    return r["reset"], {f["name"]: (f["msb"], f["lsb"], f["reset"]) for f in r["fields"] if not f["reserved"]}


def main():
    reset, f = fields("cmos5l", "BIAS_CFG_0")
    assert reset == 0x0024, hex(reset)
    assert f == {"DSM_SPARE": (9, 7, 0), "DSM_DITH_AMP": (6, 5, 1), "DSM_DITH_EN": (4, 4, 0), "DSM_TRIM": (3, 0, 4)}, f
    reset, f = fields("cmos5l", "BIAS_CFG_1")
    assert reset == 0x0040, hex(reset)
    assert f == {"ADC_CONV_EN": (6, 6, 1), "DSM_QOUT_EN": (5, 5, 0), "DSM_VCM_EXT": (4, 4, 0), "DSM_BTEST_EN": (3, 3, 0),
                 "DEC_SRC": (2, 2, 0), "DSM_RST_B": (1, 1, 0), "DSM_EN": (0, 0, 0)}, f
    assert fields("dsa1", "BIAS_CFG_0")[0] == 0x90EA and "DSM_TRIM" not in fields("dsa1", "BIAS_CFG_0")[1]
    assert fields("dsa1", "BIAS_CFG_1")[0] == 0xD02C and "DSM_EN" not in fields("dsa1", "BIAS_CFG_1")[1]
    print("test_regmap_dsm2: OK")


if __name__ == "__main__":
    main()
