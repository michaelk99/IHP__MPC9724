<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# dsm2_core on the DSA1 back end: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put dsm2_core, a 1.5 V delta-sigma modulator, on the cmos5l DSA1 back-end die with its own pads, clock, supply and clamp, controlled from `BIAS_CFG_0/1`, with the DSA1 digital function and its power unchanged when dsm2 is not used.

**Architecture:** The register generator learns per-die field overlays, so `BIAS_CFG_0/1` carry dsm2 controls on this die and the DSA1 bias fields on the DSA1 die. The chip top module holds dsm2, the new VDDA clamp ring cell and every analog net. The core only gates `do_q` and selects the decimator input. The `dsa1_dig` macro is re-hardened as a west column to free the south-east of the core. dsm2 enters first as an abstract (LEF, blackbox, outline GDS) so everything up to a full chip build runs before dsm2's GDS exists.

**Tech Stack:** Python 3 (regmap generator, layout generators in KLayout), SystemVerilog chip RTL, VHDL macro RTL via GHDL and yosys, cocotb with Icarus, LibreLane and OpenROAD, KLayout and Magic DRC/LVS, ngspice, all in `registry.iic.jku.at:5000/iic-osic-tools:next` pinned by digest.

**Spec:** `doc/dsm2_integration.md` on `dsm2/integration`, read it with this plan.

## Global Constraints

- Every tool run uses the pinned `:next` image: amd64 `sha256:65771d5c6be66df4f8a7522421355b53964ce643dc4cc612b605f645063b1af4`, arm64 `sha256:2629177ffdeb631b4536cfb4cab5671b65eb2214bcea26d181bb7a878145f88b`, PDK ihp-sg13cmos5l `5eddf3e96c4b1a42bffe90dd58daa6089a77fc23`.
- Jobs run in throwaway containers of our own (`scripts/in_image.sh`), never in the user's running IIC container. Heavy jobs one at a time on the laptop.
- On `gigaarm`: a scratch checkout, `-e PDK=ihp-sg13cmos5l`, run directories stay there.
- After reset dsm2 is off and in reset, `DEC_SRC` = 0, and the decimator reads `data_in` exactly as in v1.1.1.
- Register resets on this die: `BIAS_CFG_0` = `0x0024` (`DSM_TRIM` = `0100`, `DSM_DITH_AMP` = `01`), `BIAS_CFG_1` = `0x0040` (`ADC_CONV_EN` = 1). The DSA1 die's view of both registers stays bit for bit as today (`0x90EA`, `0xD02C`).
- dsm2 control pins: `di_ena`, `di_rst_b`, `di_trim[3:0]`, `di_dith_en`, `di_dith_amp[1:0]`, `di_vcm_ext`, `di_btest_en`, `di_qout_en`, `di_clk`. Outputs `do_q`, `do_q_b` (gated by `di_qout_en`, to the pads) and `do_q_dec` (ungated, to the core). Analog `vi`, `vcm`, `ibias_test`, `vdd`, `vss`.
- `do_q` changes 2.0 to 5.0 ns after the rising `di_clk`.
- Die 1300 x 1300 um in a QFN24, core 345 to 955 um, a 5 um core ring, `dsa1_dig` about 355 x 570 um at 75 % utilization as the west column. The lead table is the spec's (Pads and package).
- dsm2 box from dsm2's largest estimate, 155 x 185 um, at most about 165 um wide and 300 um tall, plus a 10 um halo, nothing of the chip top over it except at its pins.
- No test pads: `o_tst_ctrl` stays inside the die, `TEST_CTRL_0` is read back over SPI.
- VDD carries the DSA1 filter alone. Every dsm pad sits in a VDDA segment of the pad ring between two `cut_vdd` cells, VDDA enters through an `IOPadVdd` with a second `clamp_vddvss`, and the only VDD cell with a dsm2 input is the `DEC_SRC` gate. `vi`, `vcm`, `ibias_test` come from `padres`.
- Board rule: VDDA always on, no later than IOVDD.
- No level shifters on the chip side. No Claude or Anthropic attribution in commits.
- Never write `TEST_CTRL_0` bit 9, never 11 in bits 7:6, always keep the `0x0500` base, never write `CHIP_ID`.
- EZ130 files stay outside the repo (`EZ130_DIR`, `DECAPHV_DIR`).
- The svn side (EasyConfig, the ESP32 host) is not touched.
- `clk` is constrained at 950 ns in the chip and the macro SDC, so `DEC_SRC` at 1.024 MHz is covered.
- No push and no tag without the user's OK.
- Prose in the house style: no em-dashes, no double-hyphen dashes, no semicolons outside code, no hard wrap, short comments.

## Review Focus

- A host that writes a DSA1 bias profile to this die: it enables dsm2 and switches `DEC_SRC`. Expected: the decimator reads the gated 0 while dsm2 is off, and writing 0 into `BIAS_CFG_1` brings the `data_in` path back. Task 4 tests both.
- `DEC_SRC` low while dsm2 runs: the decimator input must stay a steady 0 while `do_q_dec` toggles. Task 4 proves it with dsm2 enabled. With dsm2 off, its latch preset holds `do_q_dec` low (dsm2, 2026-10-21), and the bench model does the same.
- A name-keyed flow setting (`RSZ_DONT_TOUCH_RX`, the analog net list) that matches nothing after synthesis renames a net: it must fail, not pass silently. Task 7 checks every pattern against the netlist.
- VDDA joined to VDD anywhere (a strap, the substrate in LVS, a global connect): it must show as an LVS mismatch. Task 8 runs LVS against a reference with VDDA tied to VDD and requires a failure.
- The east row arithmetic with the 120 um clamp: the pad gaps must land on the 1 um IO site grid, or OpenROAD.PadRing errors. Task 7 checks the gaps from the DEF.

---

## File map

| File | Change |
|---|---|
| `scripts/image.env`, `scripts/in_image.sh` | new: the pinned image and a runner for throwaway containers |
| `scripts/signoff_env.sh` | the digest comment points at `:next` |
| `macros/scripts/regmap_gen.py` | per-die overlays: `die_fields()`, per-die validation, selftest cases |
| `macros/dsa1_dig/regmap.yaml` | `BIAS_CFG_0/1`: DSA1 fields `only: dsa1`, dsm2 fields `only: cmos5l` |
| generated: `macros/dsa1_dig/rtl/dsa1_regs.vhd`, `.vh`, `sw/dsa1_regs.h`, `models/regmap_defs.py`, `doc/regmap.md` | regenerated |
| `ip/dsm2_core/` | new: blackbox Verilog, cocotb sim model, abstract LEF and outline GDS generator, later the real views |
| `ip/sg13cmos5l_ip__cut_vdd/` | new: the vdd band cut ring cell, generator, GDS, LEF, CDL, Verilog, lib, checks |
| `rtl/sg13cmos5l_dsa1_dig_top.sv` | east pads, second VSS, VDDA clamp, dsm2, analog wires |
| `rtl/sg13cmos5l_dsa1_dig_core.sv` | dsm2 control ports, `do_q` gating, `DEC_SRC` mux |
| `testbenches/cocotb/sg13cmos5l_dsa1_dig_top_tb.py` | pad map, new tests, stdcell models in RTL mode |
| `macros/dsa1_dig/flow/librelane/config.yaml`, `pin_order.cfg` | west column outline, pin sides |
| `flow/librelane/config.yaml`, `pdn_cfg.tcl`, `sg13cmos5l_dsa1_dig_top.sdc` | east pads, dsm2 macro, halo, VDDA and analog special nets, dont-touch, SDC |
| `scripts/check_analog_nets.py` | new: no cell on an analog net, every name pattern matches |
| `verification/lvs/top_lvs.sh`, `scripts/esd/*`, `testbenches/startup/gen_startup.py`, `scripts/gen_chip_schematic.py` | VDDA, dsm2, the second clamp |
| `packaging/config.yaml` | QFN24, the 24-lead `PINOUT`, paddle, guarded analog leads |
| `doc/pinout.md`, `doc/floorplan.md`, `doc/signoff.md`, `packaging/` | the new die |

---

### Task 0: Pinned image and runner

**Files:**
- Create: `scripts/image.env`, `scripts/in_image.sh`
- Modify: `scripts/signoff_env.sh:8`

**Interfaces:**
- Produces: `scripts/in_image.sh '<shell command>'` runs the command at the repo root in a throwaway `:next` container with the five exports set. Every later task uses it.

- [ ] **Step 1: Write the image file**

```sh
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# The sign-off image of the DSM die, IIC-OSIC-TOOLS :next built 2026-10-08, PDK 5eddf3e.
# Two builds of one tag, so results from both hosts are cross-checked once (doc/dsm2_integration.md).
IMAGE_AMD64=registry.iic.jku.at:5000/iic-osic-tools@sha256:65771d5c6be66df4f8a7522421355b53964ce643dc4cc612b605f645063b1af4
IMAGE_ARM64=registry.iic.jku.at:5000/iic-osic-tools@sha256:2629177ffdeb631b4536cfb4cab5671b65eb2214bcea26d181bb7a878145f88b
```

- [ ] **Step 2: Write the runner**

```bash
#!/bin/bash
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Run one shell command at the repo root in a throwaway container of the pinned image.
#   scripts/in_image.sh 'make -C macros/dsa1_dig regmap-check'
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
source "$here/image.env"
case "$(uname -m)" in
    x86_64)  img=$IMAGE_AMD64 ;;
    aarch64) img=$IMAGE_ARM64 ;;
    *) echo "in_image.sh: no image for $(uname -m)" >&2; exit 1 ;;
esac
repo=$(git -C "$here" rev-parse --show-toplevel)
proj=$(dirname "$repo")
exec docker run --rm -v "$proj:/foss/designs" \
    -e PDK=ihp-sg13cmos5l -e PDKPATH=/foss/pdks/ihp-sg13cmos5l -e PDK_ROOT=/foss/pdks \
    -e STD_CELL_LIBRARY=sg13cmos5l_stdcell -e SCL=sg13cmos5l_stdcell \
    -e EZ130_DIR=/foss/designs/OpenBLAU/ip/ez130_8t_v1p1 \
    -e DECAPHV_DIR=/foss/designs/OpenBLAU/ip/ez130_8t_decap_hv \
    "$img" bash -lc "cd /foss/designs/$(basename "$repo") && $1"
```

- [ ] **Step 3: Check that it runs the right image and PDK**

Run: `chmod +x scripts/in_image.sh && scripts/in_image.sh 'echo $PDK; cat $PDK_ROOT/$PDK/COMMIT 2>/dev/null; klayout -v; magic --version; id -u'`
Expected: `ihp-sg13cmos5l`, `5eddf3e96c4b...`, `KLayout 0.30.12`, `8.3.684`. Also run `scripts/in_image.sh 'kpex --version; ls $PDK_ROOT/$PDK/libs.ref/sg13cmos5l_io/spice'` and require kpex 0.4.4 or newer and the IO `.spice` models `scripts/esd/models.py` reads, since the ESD bench moves to this image (on 2026.08 it needed 2026.09 for both). If the PDK line says `ihp-sg13g2`, the image's login shell overrode the `-e` export: add `export PDK=ihp-sg13cmos5l ...` in front of the command inside `bash -lc` instead and rerun. Note the uid: if files come out owned by another uid, add `--user $(id -u):$(id -g)` and rerun, and if the image refuses that, clean up root-owned files from inside a throwaway container (`scripts/in_image.sh 'rm -rf <dir>'`), never with sudo.

- [ ] **Step 3b: Disk**

Run: `df -h ~`. The laptop was at 97 %. With less than 30 GB free, list the LibreLane run directories under `flow/librelane/runs` and `macros/*/flow/librelane/runs` with their sizes and ask the user which to delete. Delete nothing without that answer.

- [ ] **Step 4: Baseline on `:next`**

Run: `scripts/in_image.sh 'make -C macros/dsa1_dig regmap-check && make sim-rtl-cocotb'`
Expected: `regmap_gen.py selftest: OK` and every cocotb test passing, as on 2026.08. A failure here is an image difference, not this branch's: write it down in the commit message and stop to report it.

- [ ] **Step 5: Point the sign-off record at the new image**

In `scripts/signoff_env.sh` line 8 replace `hpretl/iic-osic-tools:2026.08` with `registry.iic.jku.at:5000/iic-osic-tools:next`.

- [ ] **Step 6: Commit**

```bash
git add scripts/image.env scripts/in_image.sh scripts/signoff_env.sh
git commit -m "scripts: run every job in the pinned :next image, the DSM die's sign-off image"
```

---

### Task 1: Per-die field overlays in the register generator

**Files:**
- Modify: `macros/scripts/regmap_gen.py` (`die_view` lines 53-73, `validate` lines 104-150, `selftest`)

**Interfaces:**
- Produces: `die_fields(reg, die) -> list[dict]`, the fields one die has. A field with no `only` or `only == die` is the die's own. Another die's field becomes `{"name": "TBD", "bits": ..., "reset": 0, "reserved": True}` where none of its bits is claimed by the die's own fields, and is dropped where any bit is. `die_view` and `validate` both use it.

- [ ] **Step 1: Write the failing selftest cases**

In `selftest()`, append a register `R2` at offset 2 to `base["registers"]` before `validate(base)`:

```python
                {"name": "R2", "offset": 2, "fields": [
                    {"name": "P", "bits": "7:4", "reset": 9, "only": "b", "used": ["b"]},
                    {"name": "Q", "bits": "3:0", "reset": 3, "only": "b", "used": ["b"]},
                    {"name": "S", "bits": "7:2", "reset": 0, "only": "a", "reserved": True},
                    {"name": "T", "bits": "1:0", "reset": 2, "only": "a", "used": ["a"]}]},
```

and after the existing die-view asserts:

```python
    a2, b2 = die_view(base, "a")[2], die_view(base, "b")[2]
    assert [f["name"] for f in a2["fields"]] == ["S", "T"] and a2["reset"] == 0x02, a2
    assert [f["name"] for f in b2["fields"]] == ["P", "Q"] and b2["reset"] == 0x93, b2
```

and two more broken cases in the `for broken, why in (...)` tuple:

```python
                        (lambda m: m["registers"][2]["fields"][0].pop("only"), "used by both"),
                        (lambda m: m["registers"][2]["fields"][3].update(bits="1"), "unassigned"),
```

The first makes `P` shared, so on die `a` it collides with `S`. The second shrinks `T` to bit 1, so on die `a` bit 0 is empty: `Q` (only on `b`) overlaps `T` and is dropped there.

- [ ] **Step 2: Run the selftest to see it fail**

Run: `scripts/in_image.sh 'python3 macros/scripts/regmap_gen.py --selftest'`
Expected: FAIL with `regmap: R2 bit 2 used by both Q and S` among the errors from `validate(base)`.

- [ ] **Step 3: Implement `die_fields` and use it**

Add after `reg_reset`:

```python
def field_bits(field):
    msb, lsb, _ = parse_bits(field["bits"])
    return set(range(lsb, msb + 1))


def die_fields(reg, die):
    """The fields a die has. Another die's field is reserved TBD here, or dropped where this die's own fields
    claim any of its bits, so two dies can lay different fields over the same bits."""
    own = [f for f in reg["fields"] if f.get("only", die) == die]
    claimed = set().union(*(field_bits(f) for f in own)) if own else set()
    out = []
    for f in reg["fields"]:
        if f.get("only", die) == die:
            out.append(f)
        elif not field_bits(f) & claimed:
            out.append({"name": "TBD", "bits": f["bits"], "reset": 0, "reserved": True})
    return out
```

In `die_view` replace

```python
        for f in reg["fields"]:
            f = dict(f)
            if f.get("only", die) != die:
                f = {"name": "TBD", "bits": f["bits"], "reset": 0, "reserved": True}
```

with

```python
        for f in die_fields(reg, die):
            f = dict(f)
```

In `validate` replace the bit-overlap loop and the coverage check. Remove `used = {}` and

```python
            for bit in range(lsb, msb + 1):
                if bit in used:
                    errors.append(f"{reg['name']} bit {bit} used by both {used[bit]} and {field['name']}")
                used[bit] = field["name"]
```

and

```python
        if len(used) != data_width:
            errors.append(f"{reg['name']} leaves bits unassigned: {sorted(set(range(data_width)) - set(used))}")
```

and add after the `for field in reg["fields"]:` loop:

```python
        for die in meta.get("dies", []):
            used = {}
            for field in die_fields(reg, die):
                for bit in sorted(field_bits(field)):
                    if bit in used:
                        errors.append(f"{reg['name']} bit {bit} used by both {used[bit]} and {field['name']} on {die}")
                    used[bit] = field["name"]
            if len(used) != data_width:
                errors.append(f"{reg['name']} leaves bits unassigned on {die}: {sorted(set(range(data_width)) - set(used))}")
```

- [ ] **Step 4: Run the selftest and the stale check**

Run: `scripts/in_image.sh 'python3 macros/scripts/regmap_gen.py --selftest && make -C macros/dsa1_dig regmap-check'`
Expected: `regmap_gen.py selftest: OK`, and `--check` silent: with today's YAML no output file changes, which proves the refactor kept every existing view.

- [ ] **Step 5: Commit**

```bash
git add macros/scripts/regmap_gen.py
git commit -m "regmap_gen: per-die field overlays, two dies may lay different fields on the same bits"
```

---

### Task 2: dsm2 fields in `BIAS_CFG_0/1`

**Files:**
- Modify: `macros/dsa1_dig/regmap.yaml:67-84`
- Regenerate: `macros/dsa1_dig/rtl/dsa1_regs.vhd`, `dsa1_regs.vh`, `macros/dsa1_dig/sw/dsa1_regs.h`, `models/regmap_defs.py`, `doc/regmap.md`

**Interfaces:**
- Consumes: `die_fields` from Task 1.
- Produces: in `models/regmap.py` `REGS["BIAS_CFG_0"]` and `REGS["BIAS_CFG_1"]` with fields `DSM_TRIM` (3:0), `DSM_DITH_EN` (4), `DSM_DITH_AMP` (6:5), `DSM_SPARE` (9:7) and `DSM_EN` (0), `DSM_RST_B` (1), `DEC_SRC` (2), `DSM_BTEST_EN` (3), `DSM_VCM_EXT` (4), `DSM_QOUT_EN` (5), `ADC_CONV_EN` (6). `RESET[2] == 0x0024`, `RESET[3] == 0x0040`. The macro's `o_bias_cfg = {BIAS_CFG_1, BIAS_CFG_0, BIAS_CFG_2[2:0]}`, so `o_bias_cfg[6:3]` is `DSM_TRIM` and `o_bias_cfg[19]` is `DSM_EN`.

- [ ] **Step 1: Write the failing check**

Create `models/test_regmap_dsm2.py`:

```python
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
```

Add it to `regmap-check` in `macros/dsa1_dig/Makefile` after `python3 ../../models/regmap.py`:

```make
	python3 ../../models/test_regmap_dsm2.py
```

- [ ] **Step 2: Run it to see it fail**

Run: `scripts/in_image.sh 'python3 models/test_regmap_dsm2.py'`
Expected: FAIL with `AssertionError: 0x90ea`.

- [ ] **Step 3: Write the overlay**

Replace the `fields:` of `BIAS_CFG_0` and `BIAS_CFG_1` in `macros/dsa1_dig/regmap.yaml`, and their `drives` and `desc`:

```yaml
  - name: BIAS_CFG_0
    offset: 2
    drives: o_bias_cfg[18:3]
    desc: Bias current settings of OTA1 to OTA3 on the DSA1 die. On this die the dsm2 trim and dither.
    fields:
      - {name: OTA3_CFG, bits: "15:12", reset: 0x9, used: [dsa1], only: dsa1}
      - {name: OTA2_CFG, bits: "11:8", reset: 0x0, used: [dsa1], only: dsa1}
      - {name: OTA1_CFG, bits: "7:0", reset: 0xEA, used: [dsa1], only: dsa1}
      - {name: NA, bits: "15:10", reset: 0x0, reserved: true, only: cmos5l}
      - {name: DSM_SPARE, bits: "9:7", reset: 0x0, used: [], only: cmos5l, desc: "Spare, drives nothing"}
      - {name: DSM_DITH_AMP, bits: "6:5", reset: 0x1, used: [cmos5l], only: cmos5l, desc: "dsm2 di_dith_amp, quantizer dither amplitude"}
      - {name: DSM_DITH_EN, bits: "4", reset: 0, used: [cmos5l], only: cmos5l, desc: "dsm2 di_dith_en, quantizer dither on"}
      - {name: DSM_TRIM, bits: "3:0", reset: 0x4, used: [cmos5l], only: cmos5l,
         desc: "dsm2 di_trim, bias 8.33 nA x (16 + 2 x code), 4 is 200 nA. Change only with DSM_EN low"}

  - name: BIAS_CFG_1
    offset: 3
    drives: o_bias_cfg[34:19]
    desc: Bias current settings of the CCRO, comparator, buffer and OTA4 on the DSA1 die. On this die the dsm2 enables and the decimator source.
    fields:
      - {name: CCRO_CFG, bits: "15:12", reset: 0xD, used: [dsa1], only: dsa1}
      - {name: COMP_CFG, bits: "11:8", reset: 0x0, used: [dsa1], only: dsa1}
      - {name: BUF_CFG, bits: "7:4", reset: 0x2, used: [dsa1], only: dsa1}
      - {name: OTA4_CFG, bits: "3:0", reset: 0xC, used: [dsa1], only: dsa1}
      - {name: NA, bits: "15:7", reset: 0x0, reserved: true, only: cmos5l}
      - {name: ADC_CONV_EN, bits: "6", reset: 1, used: [cmos5l], only: cmos5l, desc: "The adc_conv pad, 0 holds it low for a quiet power measurement"}
      - {name: DSM_QOUT_EN, bits: "5", reset: 0, used: [cmos5l], only: cmos5l, desc: "dsm2 di_qout_en, the do_q and do_q_b pads follow the bit stream"}
      - {name: DSM_VCM_EXT, bits: "4", reset: 0, used: [cmos5l], only: cmos5l, desc: "dsm2 di_vcm_ext, vcm_gen off, the vcm pad sets vcm"}
      - {name: DSM_BTEST_EN, bits: "3", reset: 0, used: [cmos5l], only: cmos5l, desc: "dsm2 di_btest_en, ibias_test onto its pad"}
      - {name: DEC_SRC, bits: "2", reset: 0, used: [cmos5l], only: cmos5l,
         desc: "Decimator input, 0 the data_in pad, 1 dsm2 do_q. With 1 clk must be the inverted dsm_clk from one source"}
      - {name: DSM_RST_B, bits: "1", reset: 0, used: [cmos5l], only: cmos5l, desc: "dsm2 di_rst_b, release 130 us after DSM_EN"}
      - {name: DSM_EN, bits: "0", reset: 0, used: [cmos5l], only: cmos5l, desc: "dsm2 di_ena"}
```

In the register map's header comment, after the `only:` line, add:

```yaml
#           Two dies may lay different `only` fields on the same bits, each die then sees its own.
```

- [ ] **Step 4: Regenerate and check**

Run: `scripts/in_image.sh 'make -C macros/dsa1_dig regmap && make -C macros/dsa1_dig regmap-check'`
Expected: `regmap_gen.py selftest: OK`, `test_regmap_dsm2: OK`. Then `git diff --stat` shows only the five generated files and the two edited ones, and `grep -n 'BIAS_CFG_0_RESET_VALUE' macros/dsa1_dig/rtl/dsa1_regs.vhd` shows `x"0024"`.

- [ ] **Step 5: The CHIP_ID warning in the register doc**

`doc/regmap.md` is generated, so the warning goes into the YAML `desc` of `BIAS_CFG_0`, appended: ` A host that writes a DSA1 bias profile checks CHIP_ID first, or it writes dsm2's trim and enables here.` Rerun Step 4.

- [ ] **Step 6: Macro RTL equivalence still holds before any re-harden**

Run: `scripts/in_image.sh 'make -C macros/dsa1_dig lint-vhdl sim-rtl-out'`
Expected: both pass. `sim-gl` against the old hardened netlist now differs only in the two reset words, which Task 6 fixes by re-hardening. Do not run `sim-gl` here.

- [ ] **Step 7: Commit**

```bash
git add macros/dsa1_dig/regmap.yaml macros/dsa1_dig/Makefile models/test_regmap_dsm2.py \
    macros/dsa1_dig/rtl/dsa1_regs.vhd macros/dsa1_dig/rtl/dsa1_regs.vh macros/dsa1_dig/sw/dsa1_regs.h \
    models/regmap_defs.py doc/regmap.md
git commit -m "regmap: dsm2 controls in BIAS_CFG_0/1 on this die, the DSA1 die's bias fields unchanged"
```

---

### Task 3: dsm2 abstract views

**Files:**
- Create: `ip/dsm2_core/README.md`, `ip/dsm2_core/verilog/dsm2_core.v` (blackbox), `ip/dsm2_core/verilog/dsm2_core_model.v` (cocotb model), `ip/dsm2_core/abstract/abstract_gen.py`, `ip/dsm2_core/abstract/check_pins.py`, generated `ip/dsm2_core/lef/dsm2_core.lef` and `ip/dsm2_core/gds/dsm2_core.gds`

**Interfaces:**
- Produces: module `dsm2_core` with ports, in this order: `vdd, vss, vi, vcm, ibias_test, di_clk, di_ena, di_rst_b, di_trim[3:0], di_dith_en, di_dith_amp[1:0], di_vcm_ext, di_btest_en, di_qout_en, do_q, do_q_b, do_q_dec`, 22 pins. `di_qout_en` and `do_q_dec` were requested from dsm2 on 2026-10-21, confirm them before Task 10.
- The bench model puts out a 15-bit LFSR sequence, `x^15 + x^14 + 1`, seed 1, one bit per rising `di_clk` 3 ns after the edge, bit = LFSR bit 0 before the shift, restarting while `di_rst_b` is low. `do_q_dec` is that bit while `di_ena` is high and X while it is low, as an unpowered or disabled output would be, so the bench proves the core's gate. `do_q` and `do_q_b` are the bit and its inverse while `di_ena` and `di_qout_en` are high, and 0 otherwise, as dsm2's gate gives.
- The abstract LEF is 155.0 x 185.0 um: `vi`, `vcm`, `ibias_test`, `vdd` on the east edge, `do_q_b`, `do_q`, `di_clk` on the south edge from its east end, the controls, `di_qout_en` and, at the south end, `do_q_dec` on the west edge. Power pins `vdd` (USE POWER) and `vss` (USE GROUND), OBS on Metal1 to Metal4 over the whole outline except the pin shapes, so the router reaches the pins from outside and never enters the block.

- [ ] **Step 1: Blackbox**

```verilog
// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// dsm2_core: 1.5 V first-order DT delta-sigma modulator, a hard macro. Pin list agreed with the dsm2 design.
`timescale 1ns/10ps
`celldefine
(* blackbox *)
module dsm2_core (vdd, vss, vi, vcm, ibias_test, di_clk, di_ena, di_rst_b, di_trim, di_dith_en,
                  di_dith_amp, di_vcm_ext, di_btest_en, di_qout_en, do_q, do_q_b, do_q_dec);
	inout vdd;
	inout vss;
	inout vi;
	inout vcm;
	inout ibias_test;
	input di_clk;
	input di_ena;
	input di_rst_b;
	input [3:0] di_trim;
	input di_dith_en;
	input [1:0] di_dith_amp;
	input di_vcm_ext;
	input di_btest_en;
	input di_qout_en;
	output do_q;
	output do_q_b;
	output do_q_dec;
endmodule
`endcelldefine
```

- [ ] **Step 2: Simulation model**

```verilog
// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// dsm2_core for the chip cocotb bench only. Not the circuit: a PRBS15 bit stream on di_clk.
// do_q_dec is X while disabled, so the bench proves the chip's DEC_SRC gate.
`timescale 1ns/10ps
module dsm2_core (vdd, vss, vi, vcm, ibias_test, di_clk, di_ena, di_rst_b, di_trim, di_dith_en,
                  di_dith_amp, di_vcm_ext, di_btest_en, di_qout_en, do_q, do_q_b, do_q_dec);
	inout vdd;
	inout vss;
	inout vi;
	inout vcm;
	inout ibias_test;
	input di_clk;
	input di_ena;
	input di_rst_b;
	input [3:0] di_trim;
	input di_dith_en;
	input [1:0] di_dith_amp;
	input di_vcm_ext;
	input di_btest_en;
	input di_qout_en;
	output do_q;
	output do_q_b;
	output do_q_dec;

	reg [14:0] lfsr = 15'd1;
	reg q = 1'b0;
	always @(posedge di_clk) begin
		if (!di_rst_b) begin
			lfsr <= 15'd1;
			q <= #3 1'b0;
		end else begin
			q <= #3 lfsr[0];
			lfsr <= {lfsr[13:0], lfsr[14] ^ lfsr[13]};
		end
	end
	assign do_q_dec = di_ena ? q : 1'bx;
	assign do_q     = di_ena & di_qout_en & q;
	assign do_q_b   = di_ena & di_qout_en & ~q;
endmodule
```

- [ ] **Step 3: Abstract generator**

`ip/dsm2_core/abstract/abstract_gen.py` writes the LEF as text and a GDS with only `prBoundary` (189/4) and the pin shapes on Metal3 plus `Metal3.pin`/`Metal3.text` labels, through `scripts/gdswrite.py` as the clamp generator does (`write_gds(layout, path)`). Pins 1 x 2 um on Metal3 at 10 um pitch: the east pins from 10 um above the south-east corner in the order `vi, vcm, ibias_test, vdd`, the south pins from 10 um west of the south-east corner in the order `do_q_b, do_q, di_clk`, the west pins from 10 um above the south-west corner in the order `do_q_dec, di_qout_en, di_btest_en, di_vcm_ext, di_dith_amp[1:0], di_dith_en, di_trim[3:0], di_rst_b, di_ena`. `vss` is a 2 um ring pin on Metal3 at the outline, as dsm2's guard ring will be. The real LEF replaces all of this in Task 10. The README names the abstract a placeholder and records the dsm2 source (`sg13cmos5l_batmon` `macros/dsm2`, its commit when it arrives).

Run: `scripts/in_image.sh 'cd ip/dsm2_core/abstract && klayout -n sg13cmos5l -zz -r abstract_gen.py'`
Expected: `ip/dsm2_core/lef/dsm2_core.lef` with `SIZE 155.000 BY 185.000`, `CLASS BLOCK`, 22 pins.

- [ ] **Step 4: Check the abstract against the blackbox**

Create `ip/dsm2_core/abstract/check_pins.py`:

```python
# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""The LEF pins of dsm2_core against the blackbox ports: check_pins.py <lef> <verilog>."""
import re
import sys

lef, ver = (open(a).read() for a in sys.argv[1:3])
lef_pins = {re.sub(r"\[\d+\]$", "", p) for p in re.findall(r"^\s*PIN (\S+)", lef, re.M)}
ports = {p.strip() for p in re.search(r"module dsm2_core \(([^)]*)\)", ver).group(1).split(",")}
if lef_pins != ports:
    sys.exit(f"dsm2 pins differ: only in LEF {sorted(lef_pins - ports)}, only in Verilog {sorted(ports - lef_pins)}")
print("PASS: dsm2 pins")
```

Run: `scripts/in_image.sh 'python3 ip/dsm2_core/abstract/check_pins.py ip/dsm2_core/lef/dsm2_core.lef ip/dsm2_core/verilog/dsm2_core.v'`
Expected: `PASS: dsm2 pins`. Rename one pin in a copy of the LEF and require a failure.

- [ ] **Step 5: Commit**

```bash
git add ip/dsm2_core
git commit -m "ip/dsm2_core: blackbox, bench model and a 155 x 185 um abstract until dsm2's views arrive"
```

---

### Task 4: Chip RTL and the cocotb bench

**Files:**
- Modify: `rtl/sg13cmos5l_dsa1_dig_top.sv`, `rtl/sg13cmos5l_dsa1_dig_core.sv`
- Modify: `testbenches/cocotb/sg13cmos5l_dsa1_dig_top_tb.py`
- Create: `ip/sg13cmos5l_ip__cut_vdd/verilog/sg13cmos5l_ip__cut_vdd.v` (the blackbox, so the RTL elaborates before Task 5)

**Interfaces:**
- Consumes: `dsm2_core` from Task 3, the register fields from Task 2.
- Produces: top ports `clk_PAD, rst_n_PAD, input_PAD[3:0], output_PAD[1:0], analog_PAD[2:0], dsm_clk_PAD, do_q_PAD, do_q_b_PAD`, and under `USE_POWER_PINS` `IOVDD, IOVSS, VDD, VSS, VDDA`. `analog_PAD[0..2]` = `vi, vcm, ibias_test`. VDDA is a supply pad, like VDD. Core ports added: `dsm_do_q_dec` (in), `dsm_ena, dsm_rst_b, dsm_trim[3:0], dsm_dith_en, dsm_dith_amp[1:0], dsm_vcm_ext, dsm_btest_en, dsm_qout_en` (out). Instance names: `dsm2`, `vdda_pad` (`IOPadVdd`), `clamp_vdda` (the second `clamp_vddvss`), `cut_vdd_s`, `cut_vdd_e`, `dsm_clk_pad`, `do_q_pad`, `do_q_b_pad`, `g_vss_pads[1].vss_pad`, `vi_pad`, `vcm_pad`, `ib_pad`, core cells `u_dec_src_gate`, `u_adc_conv_gate`.
- Every IO cell of the VDDA segment (`dsm_clk_pad`, `do_q_pad`, `do_q_b_pad`, `vi_pad`, `vcm_pad`, `ib_pad`, `vdda_pad`, `clamp_vdda`) has `.vdd(VDDA)`. Every other IO cell keeps `.vdd(VDD)`.

- [ ] **Step 1: Write the failing tests**

In the testbench:
- Pad map docstring: `output_PAD[1:0]` miso and adc_conv only, `analog_PAD[2:0] vi, vcm, ibias_test`, `dsm_clk_PAD`, `do_q_PAD`, `do_q_b_PAD`, no test pads, VDDA a supply.
- Delete `tst_ctrl(dut)` and `test_tst_ctrl_reaches_the_pads`. The SPI path to `TEST_CTRL_0` stays covered by `test_register_read_invert_write_read`, which reads it back.
- `enable_power` also drives `VDDA` to 1 when the port exists.
- New helpers and tests:

```python
B1 = {f["name"]: f for f in regmap.REGS["BIAS_CFG_1"]["fields"]}
DSM_EN      = 1 << B1["DSM_EN"]["lsb"]
DSM_RST_B   = 1 << B1["DSM_RST_B"]["lsb"]
DEC_SRC     = 1 << B1["DEC_SRC"]["lsb"]
DSM_QOUT_EN = 1 << B1["DSM_QOUT_EN"]["lsb"]
ADC_CONV_EN = 1 << B1["ADC_CONV_EN"]["lsb"]


def pad_bit(dut, name):
    v = getattr(dut, name).value
    return None if not v.is_resolvable else int(v)


async def dsm_clock(dut):
    """dsm_clk is the inverted clk, as DEC_SRC needs on the board."""
    while True:
        await RisingEdge(dut.clk_PAD)
        dut.dsm_clk_PAD.value = 0
        await FallingEdge(dut.clk_PAD)
        dut.dsm_clk_PAD.value = 1


def prbs15(n):
    lfsr, out = 1, []
    for _ in range(n):
        out.append(lfsr & 1)
        lfsr = ((lfsr << 1) | (((lfsr >> 14) ^ (lfsr >> 13)) & 1)) & 0x7FFF
    return out


@cocotb.test()
async def test_dsm_quiet_after_reset(dut):
    """After reset: do_q pads low, and the DEC_SRC gate gives 0 although do_q_dec is X."""
    pads = await bringup(dut)
    cocotb.start_soon(dsm_clock(dut))
    for _ in range(20):
        await RisingEdge(dut.clk_PAD)
        assert pad_bit(dut, "do_q_PAD") == 0 and pad_bit(dut, "do_q_b_PAD") == 0
        assert int(dut.i_sg13cmos5l_dsa1_dig_core.u_dec_src_gate.X.value) == 0


@cocotb.test()
async def test_qout_en_switches_the_pads(dut):
    """DSM_QOUT_EN: the pads follow the stream, and stop again when it is cleared."""
    pads = await bringup(dut)
    cocotb.start_soon(dsm_clock(dut))
    await reg_write(dut, pads, A["BIAS_CFG_1"], ADC_CONV_EN | DSM_EN | DSM_RST_B | DSM_QOUT_EN)
    seen = set()
    for _ in range(64):
        await RisingEdge(dut.clk_PAD)
        q, qb = pad_bit(dut, "do_q_PAD"), pad_bit(dut, "do_q_b_PAD")
        assert q is not None and qb == 1 - q
        seen.add(q)
    assert seen == {0, 1}
    await reg_write(dut, pads, A["BIAS_CFG_1"], ADC_CONV_EN | DSM_EN | DSM_RST_B)
    for _ in range(20):
        await RisingEdge(dut.clk_PAD)
        assert pad_bit(dut, "do_q_PAD") == 0 and pad_bit(dut, "do_q_b_PAD") == 0


@cocotb.test()
async def test_bias_cfg_reaches_dsm2(dut):
    """Every dsm2 control follows its register field."""
    pads = await bringup(dut)
    d = dut.dsm2
    for v0, v1 in ((0x0024, 0x0040), (0x03DB, 0x007F), (0x0000, 0x0040)):
        await reg_write(dut, pads, A["BIAS_CFG_0"], v0)
        await reg_write(dut, pads, A["BIAS_CFG_1"], v1)
        await ClockCycles(dut.clk_PAD, 2)
        assert int(d.di_trim.value) == v0 & 0xF
        assert int(d.di_dith_en.value) == (v0 >> 4) & 1
        assert int(d.di_dith_amp.value) == (v0 >> 5) & 3
        assert int(d.di_ena.value) == v1 & 1
        assert int(d.di_rst_b.value) == (v1 >> 1) & 1
        assert int(d.di_btest_en.value) == (v1 >> 3) & 1
        assert int(d.di_vcm_ext.value) == (v1 >> 4) & 1
        assert int(d.di_qout_en.value) == (v1 >> 5) & 1


@cocotb.test()
async def test_dec_src_decimates_dsm2_bit_exact(dut):
    """DEC_SRC high, pads quiet: the decimator reads do_q_dec, word for word what the model gives."""
    pads = await bringup(dut)
    cocotb.start_soon(dsm_clock(dut))
    await reg_write(dut, pads, A["BIAS_CFG_1"], ADC_CONV_EN | DSM_EN | DSM_RST_B | DEC_SRC)
    words = []
    for _ in range(70):
        await wait_conversion(dut)
        words.append(await read_adc_word(dut, pads))
        assert pad_bit(dut, "do_q_PAD") == 0, "the pads must stay quiet with DSM_QOUT_EN low"
    # The stream starts at an unknown decimation phase p, and the filter forgets its history after about
    # 32 words, so words 40 to 69 must appear in the model for one p and one lag.
    bits = prbs15(128 * 100)
    hit = any(m[lg:lg + 30] == words[40:70]
              for p in range(128) for m in [DecimatorModel().run([0] * p + bits)]
              for lg in range(len(m) - 30))
    assert hit, f"no phase and lag reproduce the chip words {words[40:44]}"
    await reg_write(dut, pads, A["BIAS_CFG_1"], ADC_CONV_EN)


@cocotb.test()
async def test_adc_conv_en_holds_the_pad(dut):
    """ADC_CONV_EN low holds adc_conv low, high brings the strobe back."""
    pads = await bringup(dut)
    await reg_write(dut, pads, A["BIAS_CFG_1"], 0)
    for _ in range(3 * 128):
        await RisingEdge(dut.clk_PAD)
        assert adc_conv(dut) == 0
    await reg_write(dut, pads, A["BIAS_CFG_1"], ADC_CONV_EN)
    await wait_conversion(dut)


@cocotb.test()
async def test_dsa1_profile_then_reset_value_restores_data_in(dut):
    """The DSA1 bias resets here set DEC_SRC with dsm2 off and clear ADC_CONV_EN: the decimator sees the
    gated 0. Writing the reset value back brings data_in and the strobe back."""
    pads = await bringup(dut)
    pads.data_in(1)
    await reg_write(dut, pads, A["BIAS_CFG_0"], 0x90EA)
    await reg_write(dut, pads, A["BIAS_CFG_1"], 0xD02C)
    await ClockCycles(dut.clk_PAD, 40 * 128)      # no strobe on the pad now
    low = await read_adc_word(dut, pads)
    assert abs(low + FULL_SCALE) < FULL_SCALE // 50, f"DEC_SRC with dsm2 off should read -full scale, got {low}"
    await reg_write(dut, pads, A["BIAS_CFG_1"], regmap.RESET[A["BIAS_CFG_1"]])
    for _ in range(40):
        await wait_conversion(dut)
    high = await read_adc_word(dut, pads)
    assert abs(high - FULL_SCALE) < FULL_SCALE // 50, f"data_in held at 1 should read +full scale, got {high}"
```

Import the model at the top with the other model imports: `from decimator_model import DecimatorModel` (the bench already puts `models/` on `sys.path` for `regmap`, use the same mechanism). The bit-exact test aligns 30 consecutive words, which absorbs the unknown start offset of the stream relative to the decimator phase.

In the runner add, in both RTL and GL mode, the stdcell models for the hand-placed cells, the dsm2 model and the cut cell blackbox:

```python
    if not gl:
        sources.append(Path(pdk_root) / pdk / "libs.ref" / scl / "verilog" / f"{scl}.v")
        sources.append(Path(pdk_root) / pdk / "libs.ref" / scl / "verilog" / "sg13cmos5l_udp.v")
    sources += [root_path / "ip/dsm2_core/verilog/dsm2_core_model.v",
                root_path / "ip/sg13cmos5l_ip__cut_vdd/verilog/sg13cmos5l_ip__cut_vdd.v"]
```

- [ ] **Step 2: Run them to see them fail**

Run: `scripts/in_image.sh 'make sim-rtl-cocotb'`
Expected: elaboration error, `dsm_clk_PAD` / `dsm2` not found.

- [ ] **Step 3: Core**

In `rtl/sg13cmos5l_dsa1_dig_core.sv` add the ports:

```systemverilog
    // dsm2, which sits in the top module with its pads and analog nets
    input  logic       dsm_do_q_dec,
    output logic       dsm_ena,
    output logic       dsm_rst_b,
    output logic [3:0] dsm_trim,
    output logic       dsm_dith_en,
    output logic [1:0] dsm_dith_amp,
    output logic       dsm_vcm_ext,
    output logic       dsm_btest_en,
    output logic       dsm_qout_en,
```

Remove the bidir and analog ports and the `NUM_BIDIR_PADS` and `NUM_ANALOG_PADS` parameters. After the macro instance:

```systemverilog
    // o_bias_cfg = {BIAS_CFG_1, BIAS_CFG_0, BIAS_CFG_2[2:0]}, dsm2 fields in doc/regmap.md
    localparam int unsigned CFG0 = 3;
    localparam int unsigned CFG1 = 19;
    logic dec_src, adc_conv_en, dsm_bit;
    assign dsm_trim     = o_bias_cfg[CFG0+3:CFG0];
    assign dsm_dith_en  = o_bias_cfg[CFG0+4];
    assign dsm_dith_amp = o_bias_cfg[CFG0+6:CFG0+5];
    assign dsm_ena      = o_bias_cfg[CFG1+0];
    assign dsm_rst_b    = o_bias_cfg[CFG1+1];
    assign dec_src      = o_bias_cfg[CFG1+2];
    assign dsm_btest_en = o_bias_cfg[CFG1+3];
    assign dsm_vcm_ext  = o_bias_cfg[CFG1+4];
    assign dsm_qout_en  = o_bias_cfg[CFG1+5];
    assign adc_conv_en  = o_bias_cfg[CFG1+6];

    // The only VDD cell with a dsm2 input. With DEC_SRC low its NMOS stack is cut, so a running or
    // unpowered dsm2 makes nothing on VDD switch. Hand placed so synthesis keeps exactly this.
    (* keep *) AND2X1 u_dec_src_gate (.A(dsm_do_q_dec), .B(dec_src), .X(dsm_bit));
```

Change the synchronizer's first stage from `data_in_s1 <= data_in_pad;` to `data_in_s1 <= dec_src ? dsm_bit : data_in_pad;`, and add to its comment: `DEC_SRC picks dsm2's bit, which changes on the rising dsm_clk, so it needs clk = the inverted dsm_clk.`

Outputs: delete `assign output_out[17:2] = o_tst_ctrl;` and its comment, `output_out` is `[1:0]` now. `adc_conv` goes through a gate:

```systemverilog
    // ADC_CONV_EN low holds the pad still for a quiet power measurement
    (* keep *) AND2X1 u_adc_conv_gate (.A(adc_conv), .B(adc_conv_en), .X(output_out[1]));
```

Rewrite the comment above the macro that says the 145 configuration bits stay inside the die: `o_bias_cfg` now drives dsm2, the rest still stays inside. Put `o_tst_ctrl`, `o_bias_cfg[34:26]`, `o_bias_cfg[18:10]` and `o_bias_cfg[2:0]` into the `_unused` list, and drop `bidir_in`, `analog_padres`, `analog_padbare` from it.

- [ ] **Step 4: Top**

In `rtl/sg13cmos5l_dsa1_dig_top.sv`:
- Parameters: `NUM_VSS_PADS = 2`, `NUM_OUTPUT_PADS = 2` (miso, adc_conv), `NUM_ANALOG_PADS = 3`, remove `NUM_BIDIR_PADS`, the bidir port, nets and generate block, and the `g_analogs` generate block. Update the parameter comment to the new pad count.
- Ports: add `inout wire VDDA` under `USE_POWER_PINS` next to `VDD`, and `inout wire dsm_clk_PAD, inout wire do_q_PAD, inout wire do_q_b_PAD`.
- Near the top of the module:

```systemverilog
`ifdef USE_POWER_PINS
    `define PAD_SUPPLIES .iovdd(IOVDD), .iovss(IOVSS), .vdd(VDD), .vss(VSS),
    `define SEG_SUPPLIES .iovdd(IOVDD), .iovss(IOVSS), .vdd(VDDA), .vss(VSS),
`else
    `define PAD_SUPPLIES
    `define SEG_SUPPLIES
`endif
```

and `` `undef PAD_SUPPLIES `` `` `undef SEG_SUPPLIES `` before `endmodule`. `SEG_SUPPLIES` is for the IO cells of the VDDA segment: their core side and their vdd band are VDDA.
- The segment:

```systemverilog
    // dsm2 analog nets, here and not in the core so the netlist keeps these names
    wire vi, vcm, ibias_test;
    logic dsm_clk_PAD2CORE, dsm_do_q, dsm_do_q_b, dsm_do_q_dec;

    // The VDDA segment of the pad ring, between cut_vdd_s and cut_vdd_e. Nothing in it is on VDD.
    (* keep *) sg13cmos5l_ip__cut_vdd cut_vdd_s (
        `ifdef USE_POWER_PINS
        .iovdd (IOVDD), .iovss (IOVSS), .vss (VSS)
        `endif
    );
    sg13cmos5l_IOPadIn     dsm_clk_pad (`SEG_SUPPLIES .p2c(dsm_clk_PAD2CORE), .pad(dsm_clk_PAD));
    sg13cmos5l_IOPadOut4mA do_q_pad    (`SEG_SUPPLIES .c2p(dsm_do_q),         .pad(do_q_PAD));
    sg13cmos5l_IOPadOut4mA do_q_b_pad  (`SEG_SUPPLIES .c2p(dsm_do_q_b),       .pad(do_q_b_PAD));
    (* keep *) sg13cmos5l_IOPadAnalog vi_pad  (`SEG_SUPPLIES .pad(analog_PAD[0]), .padres(vi),         .padbare());
    (* keep *) sg13cmos5l_IOPadAnalog vcm_pad (`SEG_SUPPLIES .pad(analog_PAD[1]), .padres(vcm),        .padbare());
    (* keep *) sg13cmos5l_IOPadAnalog ib_pad  (`SEG_SUPPLIES .pad(analog_PAD[2]), .padres(ibias_test), .padbare());
    (* keep *) sg13cmos5l_IOPadVdd vdda_pad (
        `ifdef USE_POWER_PINS
        .iovdd (IOVDD), .iovss (IOVSS), .vdd (VDDA), .vss (VSS)
        `endif
    );
    // VDDA-to-VSS ESD clamp, the signed-off cell on the segment's band. IOPadVdd clamps only to iovss.
    (* keep *) sg13cmos5l_ip__clamp_vddvss clamp_vdda (
        `ifdef USE_POWER_PINS
        .iovdd (IOVDD), .iovss (IOVSS), .vdd (VDDA), .vss (VSS)
        `endif
    );
    (* keep *) sg13cmos5l_ip__cut_vdd cut_vdd_e (
        `ifdef USE_POWER_PINS
        .iovdd (IOVDD), .iovss (IOVSS), .vss (VSS)
        `endif
    );

    logic       dsm_ena, dsm_rst_b, dsm_dith_en, dsm_vcm_ext, dsm_btest_en, dsm_qout_en;
    logic [3:0] dsm_trim;
    logic [1:0] dsm_dith_amp;
    dsm2_core dsm2 (
        `ifdef USE_POWER_PINS
        .vdd (VDDA), .vss (VSS),
        `else
        .vdd (), .vss (),
        `endif
        .vi (vi), .vcm (vcm), .ibias_test (ibias_test),
        .di_clk (dsm_clk_PAD2CORE), .di_ena (dsm_ena), .di_rst_b (dsm_rst_b), .di_trim (dsm_trim),
        .di_dith_en (dsm_dith_en), .di_dith_amp (dsm_dith_amp), .di_vcm_ext (dsm_vcm_ext),
        .di_btest_en (dsm_btest_en), .di_qout_en (dsm_qout_en),
        .do_q (dsm_do_q), .do_q_b (dsm_do_q_b), .do_q_dec (dsm_do_q_dec)
    );
```

No `assign` on an analog net, synthesis would put a buffer there.
- The other IO cells keep their current instances with `.vdd(VDD)`. The second VSS pad comes from `NUM_VSS_PADS = 2`.
- Core instance: connect the new ports, drop the bidir and analog ones.
- Blackbox for the cut cell, `ip/sg13cmos5l_ip__cut_vdd/verilog/sg13cmos5l_ip__cut_vdd.v`, as the clamp's with ports `(vss, iovdd, iovss)` and the header comment `vdd band cut: an IO ring cell that carries iovss, iovdd and vss but no vdd band`.

- [ ] **Step 5: Run the bench**

Run: `scripts/in_image.sh 'make sim-rtl-cocotb'`
Expected: every test passes, the six new ones included. `test_register_read_invert_write_read` reads the old resets and fails until Task 6 re-hardens the macro, since the RTL bench uses the hardened netlist. Mark that one expected-fail in the commit message, and record that Task 6 Step 5 reruns it. The same holds for any new test that relies on the new reset of `BIAS_CFG_1` (`ADC_CONV_EN` = 1): with the old netlist it resets to `0xD02C`, so run those after writing `0x0040` first, as the tests above do where it matters, and rerun all of them after Task 6.

- [ ] **Step 6: Mutants**

Swap `.B(dec_src)` for `.B(1'b1)` in `u_dec_src_gate`, rerun `test_dsm_quiet_after_reset`, require FAIL, restore. Swap `.B(adc_conv_en)` for `.B(1'b1)` in `u_adc_conv_gate`, rerun `test_adc_conv_en_holds_the_pad`, require FAIL, restore.

- [ ] **Step 7: Lint and commit**

Run: `scripts/in_image.sh 'verilator --lint-only -Wall -Irtl -Iip/dsm2_core/verilog rtl/sg13cmos5l_dsa1_dig_top.sv rtl/sg13cmos5l_dsa1_dig_core.sv ip/dsm2_core/verilog/dsm2_core.v ip/sg13cmos5l_ip__cut_vdd/verilog/*.v ip/sg13cmos5l_io_custom/verilog/sg13cmos5l_io.v ip/sg13cmos5l_ip__clamp_vddvss/verilog/*.v 2>&1 | grep -v DECLFILENAME | head -40'` and fix every warning in the two RTL files.

```bash
git add rtl testbenches/cocotb/sg13cmos5l_dsa1_dig_top_tb.py ip/sg13cmos5l_ip__cut_vdd/verilog
git commit -m "rtl: dsm2 in a VDDA segment of the pad ring, the DEC_SRC and adc_conv gates, and their cocotb tests"
```

---

### Task 5: The vdd band cut cell

**Files:**
- Create: `ip/sg13cmos5l_ip__cut_vdd/{Makefile,README.md,layout/cut_gen.py,layout/cut_probe.py,cdl,gds,lef,lib}`
- Reuse: `ip/sg13cmos5l_ip__clamp_vddvss/layout/rails.py` (reads the band positions from the IO LEF), `ip/sg13cmos5l_ip__clamp_vddvss/layout/clamp_abut.py` and `drc_report.py` (abutment DRC), `scripts/gdswrite.py`

**Interfaces:**
- Produces: cell `sg13cmos5l_ip__cut_vdd`, 10 x 180 um, `CLASS PAD SPACER`, `SITE sg13cmos5l_ioSite`, pins `iovss`, `iovdd`, `vss` on their bands as `sg13cmos5l_Filler2000` has them, no `vdd` pin and no metal of the vdd band on any layer. CDL `.SUBCKT sg13cmos5l_ip__cut_vdd vss iovdd iovss` with no devices, a dummy liberty and the blackbox from Task 4.

- [ ] **Step 1: A probe that fails today**

`layout/cut_probe.py <gds>` flattens the cell and requires: (a) the iovss, iovdd and vss bands each run from x 0 to x 10 on every layer the filler has them, (b) no shape on Metal1 to TopMetal1 inside the vdd band's y ranges from `rails.py` (Metal3 160 to 178, Metal4 140 to 155.8, TopMetal1 141.5 to 156.5, read from the LEF, not pasted). Run it on a copy of `sg13cmos5l_Filler2000` streamed from the PDK IO GDS and require FAIL on (b).

- [ ] **Step 2: The generator**

`layout/cut_gen.py`, run as `klayout -n sg13cmos5l -zz -r cut_gen.py`, copies `sg13cmos5l_Filler2000`'s GDS cell from the PDK IO library, deletes every shape inside the vdd band's y ranges on every metal and via layer, renames the cell, writes GDS through `write_gds` and the LEF as text (the filler's LEF with the `vdd` pin removed and the vdd band ranges written as nothing). If the filler has shapes that straddle a band edge, it clips them at the band edge and the probe proves the remaining bands whole.

- [ ] **Step 3: Checks**

Makefile targets as in `ip/sg13cmos5l_ip__clamp_vddvss`: `gen`, `drc` (KLayout regular, only the density globals may fire), `magic-drc`, `drc-abut` (the cell between `IOPadIn` and `IOPadOut4mA`, and between `IOPadVss` and `IOPadIn`, abutted and with fillers, against the same rows without the cell), `lvs` (empty netlist, matches with its three ports), `probe`.

Run: `scripts/in_image.sh 'make -C ip/sg13cmos5l_ip__cut_vdd gen drc magic-drc drc-abut lvs probe'`
Expected: every target passes. In the abutted row the vdd band on each side ends at the cell edge, 10 um apart.

- [ ] **Step 4: Mutant**

Generate a variant with one 2 um Metal3 strip left in the vdd band. Expected: `probe` fails on (b).

- [ ] **Step 5: The second clamp copy**

Nothing to build: `clamp_vdda` is the signed-off `sg13cmos5l_ip__clamp_vddvss` on the segment's band. Rerun its clamp bench at 1.5 V (`make -C ip/sg13cmos5l_ip__clamp_vddvss sim-clamp` with the supply set to 1.5 V, add a `VDD=` option to `sim/tb_clamp.py` if it has none): leakage at -40, 27 and 125 C, on for a 10 ns edge, off on the board's ramp. Record the numbers in the cut cell's README under "VDDA clamp".

- [ ] **Step 6: Commit**

```bash
git add ip/sg13cmos5l_ip__cut_vdd ip/sg13cmos5l_ip__clamp_vddvss/sim
git commit -m "ip: cut_vdd, the ring cell that bounds the VDDA segment, and the clamp bench at 1.5 V"
```

---

### Task 6: Re-harden `dsa1_dig` as the west column

**Files:**
- Modify: `macros/dsa1_dig/flow/librelane/config.yaml` (`DIE_AREA`, density), `pin_order.cfg`, `dsa1_dig_top.sdc` (clk period)
- Regenerated by the flow: `macros/dsa1_dig/final/*`, `netlist/*`, `verification/*`, `render/*`

**Interfaces:**
- Consumes: the regenerated VHDL package from Task 2.
- Produces: `macros/dsa1_dig/final/lef/dsa1_dig_top.lef` about 355 x 570 um, `rst_b`, `clk` and the SPI pins on the north edge, `data_in` and `adc_conv` on the south, `o_bias_cfg[*]` on the east edge in its south part, the other config outputs spread over west and south.

- [ ] **Step 1: Outline**

The site grid is the EZ130 row height and site width in `$EZ130_DIR/lef/ez130_tech.lef`. Read both and pick the outline nearest 355 x 570 um that is a multiple of them, so that the 137.7k um2 of cells fill about 75 % of its core, with the width at or below 355 um (the dsm2 room east of it depends on that). Set `DIE_AREA: [0, 0, <w>, <h>]` and raise `PL_TARGET_DENSITY_PCT` to 85 if placement asks for it. If detailed routing does not converge to 0 DRC errors, step back to about 370 x 590 um (70 %) and tell the user, since that takes 15 um from dsm2's width.

- [ ] **Step 1b: Clock**

In `macros/dsa1_dig/flow/librelane/dsa1_dig_top.sdc` change `create_clock -name clk  -period 1000.0 -waveform {0.0 500.0}` to `-period 950.0 -waveform {0.0 475.0}` with the comment `# 950 ns covers clk at 1.024 MHz, the inverted dsm_clk when DEC_SRC reads dsm2`. Leave every other key of the macro config as it is, the PDN settings included, so the macro ring keeps one top-level layer free as now.

- [ ] **Step 2: Pin order**

```
#N
rst_b
clk
sclk
mosi
ss
miso

#W
o_rst_ctrl_b.*
o_en_ctrl.*
o_lf_cfg.*
o_clk_cfg.*

#E
o_bias_cfg.*

#S
data_in
adc_conv
o_tst_ctrl.*
o_uwb_tx_cfg.*
o_aux_ctrl.*
```

The pins follow the pads: `rst_n`, `clk` and SPI on the north side, `data_in` and `adc_conv` on the south. The west edge faces only the supply pads.

Then check `FP_PIN_ORDER_CFG` handling of `#E` for the south part: OpenROAD places a side's pins evenly. If `o_bias_cfg` must sit low on the east edge, add `$` padding lines or an `@min_distance` per the LibreLane pin order syntax. Write down which.

- [ ] **Step 3: Harden on gigaarm or the laptop**

Run (laptop): `scripts/in_image.sh 'make -C macros/dsa1_dig build-top'` in the background, 30 to 60 min. On gigaarm see Task 9.
Expected: LibreLane finishes, DRC 0 in Magic and KLayout, LVS clean, antenna 0, setup and hold met in all three corners.

- [ ] **Step 4: Macro gates**

Run: `scripts/in_image.sh 'make -C macros/dsa1_dig check-netlist lec sim-gl model-gate sim-cdc'`
Expected: every gate passes, `verification/lec_verdict.json` says equivalent, and `make -C macros/dsa1_dig lec-fail` finds its mutant.

- [ ] **Step 5: Chip bench on the new netlist**

Run: `scripts/in_image.sh 'make sim-rtl-cocotb'`
Expected: every test passes, `test_register_read_invert_write_read` included, now reading `0x0024` and `0x0040`.

- [ ] **Step 6: Commit**

```bash
git add macros/dsa1_dig
git commit -m "dsa1_dig: re-hardened as a west column with the dsm2 register resets"
```

---

### Task 7: Chip top flow with the dsm2 abstract

**Files:**
- Modify: `flow/librelane/config.yaml`, `flow/librelane/pdn_cfg.tcl`, `flow/librelane/sg13cmos5l_dsa1_dig_top.sdc`, `Makefile` (`CHIP_FRAG` extra LEF/GDS/lib for the new cells)
- Create: `scripts/check_analog_nets.py`

**Interfaces:**
- Consumes: everything above.
- Produces: a routed, filled chip GDS with the dsm2 abstract, `netlist/nl/sg13cmos5l_dsa1_dig_top.nl.v`, the DEF.

- [ ] **Step 1: Die and pads**

```yaml
DIE_AREA:  [0, 0, 1300, 1300]
CORE_AREA: [345, 345, 955, 955]

# West (bottom to top): supplies and the vdd clamp only.
PAD_WEST: [
    "g_vss_pads\\[0\\].vss_pad",         # VSS, downbonded to the paddle, ground lead 5
    clamp_vddvss,                       # vdd-to-vss ESD clamp, 120 um, no bondpad
    "g_vdd_pads\\[0\\].vdd_pad",         # VDD, lead 4
    "g_iovss_pads\\[0\\].iovss_pad",     # IOVSS, downbonded to the paddle, ground lead 3
    "g_iovdd_pads\\[0\\].iovdd_pad"      # IOVDD, lead 2
]

# North (left to right): reset, clock and the SPI slave.
PAD_NORTH: [
    rst_n_pad,                          # rst_n, lead 24
    clk_pad,                            # clk, lead 23
    "g_inputs\\[1\\].input_pad",         # sclk, lead 22
    "g_inputs\\[2\\].input_pad",         # mosi, lead 21
    "g_inputs\\[3\\].input_pad",         # ss, lead 20
    "g_outputs\\[0\\].output_pad"        # miso, lead 19
]

# East (bottom to top): dsm2's analog pads, VDDA and its clamp.
PAD_EAST: [
    vi_pad,                             # vi, lead 14
    vcm_pad,                            # vcm, lead 15
    ib_pad,                             # ibias_test, lead 16
    vdda_pad,                           # VDDA, IOPadVdd on the segment's band, lead 17
    clamp_vdda,                         # VDDA-to-VSS ESD clamp, a second clamp_vddvss, 120 um
    cut_vdd_e                           # vdd band cut, the VDDA segment ends here
]

# South (left to right): data_in, adc_conv, dsm2's ground, clock and bit stream.
PAD_SOUTH: [
    "g_inputs\\[0\\].input_pad",         # data_in, lead 7
    "g_outputs\\[1\\].output_pad",       # adc_conv, lead 8
    "g_vss_pads\\[1\\].vss_pad",         # second VSS, downbonded to the paddle, ground lead 9
    cut_vdd_s,                          # vdd band cut, the VDDA segment starts here
    dsm_clk_pad,                        # dsm_clk, lead 10
    do_q_pad,                           # do_q, lead 11
    do_q_b_pad                          # do_q_b, lead 12
]
```

Rewrite the pad spacing comment for 660 um between the corners: west holds 4 x 80 + 120 um with 36 um gaps and 38 um ends, east 4 x 80 + 120 + 10 um with 30 um, north 6 x 80 um with 24 um gaps and 30 um ends, south 6 x 80 + 10 um with 20 um gaps and 25 um ends. Check every gap in the first run's DEF.

Core ring: set `PDN_CORE_RING_VWIDTH` and `PDN_CORE_RING_HWIDTH` to 5, keep the spacings at 5. Check in the first run's DEF that the ring fits between the IO cells' inner edge (320 um) and the core (345 um), and that `PDN_CORE_RING_CONNECT_TO_PADS` still reaches every supply pad.

- [ ] **Step 2: dsm2 macro and placement**

Add to `MACROS`:

```yaml
  dsm2_core:
    gds:
      - dir::../../ip/dsm2_core/gds/dsm2_core.gds
    lef:
      - dir::../../ip/dsm2_core/lef/dsm2_core.lef
    vh:
      - dir::../../ip/dsm2_core/verilog/dsm2_core.v
    instances:
      dsm2:
        location: [<x>, <y>]
        orientation: N
```

`<x>, <y>`: the south-east of the core, the east edge of the box plus halo 20 um inside `CORE_AREA[2]` (955), the lower edge about 30 um above `CORE_AREA[1]` so the south pins have room to the south pads, and the analog pins level with `vi_pad` to `vdda_pad` (bondpad centres at y 398 to 746). Use the 155 x 185 um box until dsm2's outline arrives. Move `dsa1_dig` (370.02 x 588 um after Task 6) to the west edge of the core: `location: ["expr::345 + 5", "expr::345 + 11"]` as a first value, so its east edge sits at about 720 and a 30 um channel stays before dsm2's halo at 750 to 760. That keeps dsm2's room at 165 um wide. Check both from the first run's DEF, then fix them. Add `PL_MACRO_HALO: "10 10"` or the per-instance halo the LibreLane version supports. `PDN_OBSTRUCTIONS` on every metal up to TopMetal1 over the dsm2 box grown by the halo, so no strap crosses it. `ROUTING_OBSTRUCTIONS` on TopMetal1 over the dsm2 box. Metal1 to Metal4 inside the box are already blocked by the abstract's OBS, which leaves the pins reachable from outside, so do not put routing obstructions on those layers or the router cannot reach the control pins. Fill keep-out: in `scripts/add_logo_fill.sh` add a `RECT_LAYERx` entry with the nofill datatype 23 on every metal over the box grown by the halo, as the logo entries do.

In the `Makefile`, add the `cut_vdd` LEF, GDS and lib to `CHIP_FRAG` through `macros/scripts/decaphv_frag.py`'s `--extra-lef/--extra-gds/--extra-lib`, as for `clamp_vddvss`.

- [ ] **Step 3: Analog nets and VDDA in the PDN**

In `pdn_cfg.tcl`, after the existing grids:

```tcl
# VDDA: the pad ring's segment between the two cut_vdd cells, and dsm2's supply. Not VDD anywhere.
add_global_connection -net VDDA -inst_pattern {^(dsm_clk_pad|do_q_pad|do_q_b_pad|vi_pad|vcm_pad|ib_pad|vdda_pad|clamp_vdda)$} -pin_pattern {^vdd$} -power
add_global_connection -net VDDA -inst_pattern {^dsm2$} -pin_pattern {^vdd$} -power
add_global_connection -net VSS  -inst_pattern {^dsm2$} -pin_pattern {^vss$} -ground
```

and draw the VDDA, `vi`, `vcm`, `ibias_test` wires as special-net shapes on Metal3 in the existing pdngen wrapper (the same hook the file already uses), from each pad's core-edge pin straight west to the dsm2 pin at its y, the signals 2 um wide, `vi` with a VSS track 2 um wide on each side at minimum spacing, each VSS track joined by Via3 to the VSS core ring where it crosses it. VDDA is a 10 um strap from the segment's vdd band (its Metal3 at the core edge of `vdda_pad` and `clamp_vdda`, IO cell y 160 to 178) west to dsm2's `vdd` pin, the way the core ring joins VDD's band. The core ring must not join the segment: after pdngen, assert that no VDD shape touches the vdd pins of the eight segment cells, and that the VDDA strap touches no VDD shape. All of this is Metal3, under the core ring on Metal4 and TopMetal1. Read the core ring layers out of `pdn_cfg.tcl` first, and if Metal3 is used there, stop and report. The coordinates come from the placed pads and the dsm2 location, read in the wrapper from OpenDB, not pasted. After drawing, assert in the same Tcl that no shape of another net lies within the Metal3 minimum spacing of each drawn wire and fail otherwise.

If `add_global_connection` on a net that is not in `VDD_NETS` errors, add `VDDA` to `VDD_NETS` as a second power net with no stripes of its own, and rerun. Record which of the two worked.

- [ ] **Step 4: Don't touch and SDC**

```yaml
RSZ_DONT_TOUCH_RX: "^(vi|vcm|ibias_test|dsm_clk_PAD2CORE|dsm_do_q|dsm_do_q_b|dsm_do_q_dec|u_dec_src_gate|u_adc_conv_gate)$"
```

Remove the four `analog_PAD*` entries from `RSZ_DONT_TOUCH_LIST`. In the SDC add:

```tcl
# dsm2 runs on its own clock pin and has no timed path to anything of the core: its controls are static
# registers, do_q_dec reaches the core only through the synchronizer, and its pads are observed off chip.
set_false_path -from [get_ports {dsm_clk_PAD}]
set_false_path -to   [get_ports {do_q_PAD do_q_b_PAD}]
set_false_path -to   [get_pins {dsm2/*}]
set_false_path -from [get_pins {dsm2/do_q dsm2/do_q_b dsm2/do_q_dec}]
set_false_path -through [get_ports {analog_PAD[*]}]
```

and shrink `sclk_outputs` to `output_PAD[0]` alone, the test pads are gone. Change `create_clock -name clk -period 1000.0 -waveform {0.0 500.0}` to `-period 950.0 -waveform {0.0 475.0}` and the comment to `clk: the modulator clock, 65.536 kHz with data_in, 1.024 MHz with DEC_SRC, constrained at 950 ns`.

The names in `RSZ_DONT_TOUCH_RX` are a first guess. After the first synthesis, read the real net names of these nets and the instance names of `u_dec_src_gate` and `u_adc_conv_gate` from `netlist/nl/sg13cmos5l_dsa1_dig_top.nl.v` (a flattened core prefixes them), and write the regex from those, with the two gate instances in it.

- [ ] **Step 5: The analog net checker, failing first**

`scripts/check_analog_nets.py <netlist> <spec>` reads the gate-level netlist and a list of `net: allowed instance/pin...`, and fails if a net touches anything more (buffer, antenna diode, tie) or appears in an `assign`, or if a net in the list is not in the netlist. With `--rx <config.yaml>` it also splits `RSZ_DONT_TOUCH_RX` into its alternatives and fails on any alternative that matches no net and no instance in the netlist. The spec for this chip, in `flow/librelane/analog_nets.txt`, names taken from the netlist:

```
vi:          vi_pad/padres dsm2/vi
vcm:         vcm_pad/padres dsm2/vcm
ibias_test:  ib_pad/padres dsm2/ibias_test
dsm_clk_PAD2CORE: dsm_clk_pad/p2c dsm2/di_clk
dsm_do_q:    dsm2/do_q do_q_pad/c2p
dsm_do_q_b:  dsm2/do_q_b do_q_b_pad/c2p
dsm_do_q_dec: dsm2/do_q_dec u_dec_src_gate/A
```

The last three prove that the bit stream reaches its pads with nothing on VDD in between, and that the only VDD cell on `do_q_dec` is the hand-placed gate. VDDA is a power net and is checked in Step 6 instead: every `vdd` pin in the netlist is on VDD except the eight segment cells and `dsm2`, which are on VDDA.

Test it on a hand-written 10-line netlist with an extra `sg13cmos5l_antennanp` on `vi` and require FAIL, on one where `vi` is renamed and require FAIL with `vi not in netlist`, and with a regex alternative that matches nothing and require FAIL.

- [ ] **Step 6: Build**

Run: `scripts/in_image.sh 'make build-top'` in the background (laptop), or on gigaarm (Task 9).
Expected: LibreLane finishes. Then:
- `scripts/in_image.sh 'make check-netlist && python3 scripts/check_analog_nets.py netlist/nl/sg13cmos5l_dsa1_dig_top.nl.v flow/librelane/analog_nets.txt --rx flow/librelane/config.yaml'` passes.
- Keep-out: a KLayout script, `scripts/check_keepout.py <gds> <box>`, flattens the top cell without the `dsm2_core` instance and fails on any shape on Metal1 to TopMetal1 inside the dsm2 box, except the drawn and routed wires that end on a dsm2 pin within 2 um of the box edge. Require PASS on the chip, and FAIL on a copy with one Metal2 rectangle added inside the box.
- `scripts/in_image.sh 'make sim-gl-cocotb'`: every test passes on the gate-level netlist.
- VDD isolation: in the DEF, list every instance pin on VDD and on VDDA. VDD has no pin of a segment cell or of dsm2, VDDA has no other. A copy of the netlist with one segment cell's `vdd` moved to VDD must fail this check.
- `scripts/in_image.sh 'make em-probe'` and the IR report from `make copy-reports`: the 5 um core ring within the v1.1.1 limits (worst EM ratio 0.5, IR as reported then).
- The DEF shows every east pad gap on the 1 um site grid and 20 um gaps.
- STA: setup and hold met for `clk` and `sclk`, no path from or to dsm2.
- `make copy-reports`, then DRC: only the expected density markers, `DRC_EXPECT` re-derived if bondpad markers change.

- [ ] **Step 7: Bond plan**

Run: `scripts/in_image.sh 'make bondplan'`
First set `packaging/config.yaml` to the QFN24: `PACKAGE_NAME: OP_QFN24_A4_FIT`, `SHEET_TEXT_SCALE` key `"QFN24(5x5)"`, `GUARDED_PINS: [[14, 15, 16, 17]]`, `EPAD_NETS` as today, and `PINOUT`:

```yaml
PINOUT:
  # Left side, top to bottom (pins 1-6)
  1:  ~
  2:  "IOVDD"                     # I/O supply
  3:  "IOVSS"                     # ground lead, bonded to the paddle
  4:  "VDD"                       # core supply, 1.2 V
  5:  "VSS"                       # ground lead, bonded to the paddle
  6:  ~
  # Bottom side, left to right (pins 7-12)
  7:  "input_PAD[0]"              # data_in, the 1-bit modulator bitstream
  8:  "output_PAD[1]"             # adc_conv, 512 Hz strobe
  9:  "VSS"                       # ground lead, bonded to the paddle
  10: "dsm_clk_PAD"               # dsm2 clock, 1.024 MHz
  11: "do_q_PAD"                  # do_q
  12: "do_q_b_PAD"                # do_q_b
  # Right side, bottom to top (pins 13-18)
  13: ~                           # keeps other wires off the analog leads
  14: "analog_PAD[0]"             # vi
  15: "analog_PAD[1]"             # vcm
  16: "analog_PAD[2]"             # ibias_test
  17: "VDDA"                      # dsm2 supply, 1.5 V, IOPadVdd
  18: ~                           # keeps other wires off the analog leads
  # Top side, right to left (pins 19-24)
  19: "output_PAD[0]"             # miso
  20: "input_PAD[3]"              # ss
  21: "input_PAD[2]"              # mosi
  22: "input_PAD[1]"              # sclk
  23: "clk_PAD"                   # decimator clock
  24: "rst_n_PAD"                 # reset, active low
```

Set `PACKAGE_PADDLE` from the EUROPRACTICE QFN24 drawing. The draft used 3200 um, which is not confirmed. If the drawing gives no paddle size, ask the user.

Expected: 23 wires, every lead as in the table, minimum wire gap at or above 60 um, no crossing, no guard warning on leads 14 to 17, wire lengths near the draft's 1396 to 1788 um. Review `packaging/result.md` and the render.

- [ ] **Step 8: Commit**

```bash
git add flow/librelane scripts/check_analog_nets.py Makefile layout netlist render verification packaging
git commit -m "chip: dsm2 abstract on the east, VDDA and analog nets drawn, the west column macro"
```

---

### Task 8: Benches and documents for the new die

**Files:**
- Modify: `verification/lvs/top_lvs.sh`, `scripts/esd/ring_clip.py`, `scripts/esd/hbm.py`, `scripts/esd/check.py`, `testbenches/startup/gen_startup.py`, `scripts/gen_chip_schematic.py`, `doc/pinout.md`, `doc/floorplan.md`, `doc/specifications.md`

- [ ] **Step 1: Top LVS**

In `top_lvs.sh` compare both `clamp_vddvss` copies device by device as today, the empty `cut_vdd` by its pins, and black-box `dsm2_core` by its pins until Task 10. VDDA must be its own net in the reference. Run it, require a match. Then make a reference copy with VDDA joined to VDD and require a mismatch. Then the existing mutant.

- [ ] **Step 2: ESD**

`ring_clip.py` reads every slot of all four sides from the DEF (the ring is 1300 um now) and adds clamp stripe ports for `clamp_vdda`. `hbm.py` gets the VDDA band segment as its own rail, cut at the two `cut_vdd` cells, the `IOPadVdd` clamp on it and the second clamp. Replace the `hpretl/iic-osic-tools:2026.09` mentions in `scripts/esd/pex.py` and `scripts/esd/models.py` with the `:next` image. `check.py` gets the zap pairs of VDDA, `vi`, `vcm`, `ibias_test`, `dsm_clk`, `do_q`, `do_q_b` against every supply. Run the full sweep (on gigaarm). Expected: every pair has a path, the peak on 1.2 V and on 1.5 V nodes reported, and with `--without clamp_vdda` the VDDA pairs fail.

- [ ] **Step 3: Start-up and bounce**

`gen_startup.py` keeps the new pads, both clamp copies and the cut cells, and adds VDDA as a third supply with its own ramp on the segment's band. Run the board order (VDD and VDDA no later than IOVDD) and require it clean as for v1.1.1, then run IOVDD before VDDA once and report the segment's output spike that the board rule avoids. Bounce: `do_q`, `do_q_b` at 1.024 MHz with `miso` and `adc_conv` switching, report the swing on `vi` and VDDA. The v1.1.1 bounce stimulus switched the test pads, which are gone, so the bench toggles `miso` through SPI reads instead.

- [ ] **Step 4: DSA1 power**

There is no v1.1.1 power row in `doc/signoff.md`, so both numbers are made here, on both layouts. (a) The start-up bench in the DSA1 state (VDD, IOVDD and VDDA on, dsm2 off, `dsm_clk` low, `data_in` toggling at 65.536 kHz) on this branch and on a `tapeout/v1.1.1` worktree: the settled VDD and IOVDD currents, which are the IO cells' and clamps' (the XSPICE core draws nothing). Then the VDD isolation case on this branch: the same with `dsm_clk` at 1.024 MHz and the `do_q` pads switching (a model of dsm2's outputs driving them), `DEC_SRC` low. Its VDD current must equal the dsm2-off one within the bench's resolution, write both into the report. (b) `make -C macros/dsa1_dig power-vcd` on this branch against the 3.061 uW typical of v1.1.1. Expected: (a) within 1 % or the difference named with its cause, (b) within 2 %. Write both into `verification/startup/startup_report.md`.

- [ ] **Step 5: Schematic and docs**

`make schematic`, then `doc/pinout.md` (the QFN24 lead table from the spec, the test pads gone, board notes: VDD and VDDA no later than IOVDD, VDDA always on, `dsm_clk` low when unused, `vi` and `vcm` within 0 V to VDDA and at 0 V or open while VDDA ramps, `ibias_test` read with an SMU at 0 to 0.8 V or across 1 Mohm to ground, never 10 Mohm, and switched on before a measurement), `doc/floorplan.md` (the new floorplan), `doc/specifications.md` (dsm2 section from the spec's table).

- [ ] **Step 6: Commit**

```bash
git add verification scripts testbenches/startup doc schematic
git commit -m "benches: LVS, ESD, start-up and bounce with VDDA, dsm2 and the second clamp"
```

---

### Task 9: gigaarm and the cross-host check

**Files:** none in the repo, notes into the commit message of the first gigaarm result.

- [ ] **Step 1:** On gigaarm, `git clone` the laptop's branch into `~/scratch/sg13cmos5l_dsa1_dig` (push nothing: clone over ssh from the laptop or copy a bundle with `git bundle create`). Check `docker image inspect` shows the arm64 digest of `scripts/image.env`.
- [ ] **Step 2:** EZ130 and DECAPHV: check `~/projects/OpenBLAU/ip/ez130_8t_v1p1` exists on gigaarm. If not, stop and ask the user before copying a prerelease library there.
- [ ] **Step 3:** Run the same `make -C ip/sg13cmos5l_ip__cut_vdd drc lvs` and the chip `klayout-drc-regular` and `top_lvs.sh` on both hosts on the same commit. Expected: equal marker counts and the same LVS verdict. A difference means the two builds disagree, which is reported before any gigaarm result is used.

---

### Task 10: dsm2's real views, full sign-off, release

Needs dsm2's GDS and LEF (end of the week of 2026-10-19 at the earliest).

- [ ] **Step 1:** Copy dsm2's `final/gds`, `final/lef`, CDL and pin list into `ip/dsm2_core/`, with the dsm2 commit in the README. Compare its LEF pin names to `dsm2_core.v` (the Task 3 check), and its outline to 150 x 170 um. A difference stops here and goes back to the dsm2 session. Also ask dsm2 for its input-bench result (at VDD 1.08 and 1.32 V against VDDA 1.45 and 1.55 V: no extra VDDA current beyond the receivers' figures, the bias at code 4 within one trim step, the `di_ena` edge at the OTA at least 30 ns) and record it with dsm2's commit in `doc/signoff.md`.
- [ ] **Step 2:** Rebuild the chip (`make build-top`), Task 7 Step 6 checks, `top_lvs.sh` with dsm2 compared device by device.
- [ ] **Step 3:** Every row of `doc/signoff.md` on the delivery GDS, in its order, on `:next`: check-netlist, macro XOR against `macros/dsa1_dig/final/gds` (0), the same XOR for the dsm2 cell against `ip/dsm2_core/gds/dsm2_core.gds` (0), `mpw-precheck`, `klayout-drc-regular` (with the antenna and latch-up decks), Magic DRC, `fill_isolation.py`, `top_lvs.sh` and mutant, LibreLane LVS/STA/antenna via `copy-reports`, `em-probe`, start-up, bounce, ESD, `make bondplan`, chip cocotb RTL and GL, `signoff_env.txt` with the `:next` digest.
- [ ] **Step 4:** `make release VERSION=1.2.0`, `doc/signoff.md`, the new md5 into `scripts/submission.sh`, a `submission.sh` dry run.
- [ ] **Step 5:** Commit, then ask the user before any push or tag.
