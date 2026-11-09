# dsm2_core sizing derivations

gm/ID derivations of the dsm2 blocks, rebuilt after the fact from the spec. Each one reads the drawn sizes from `../schematic/` (and from the exported netlists in `netlist/` for `cmfb_sc2` and `quantizer2`) and compares. Nothing here changes a schematic.

| File | Sizes |
| --- | --- |
| `size_bias_gm.ipynb` | `bias_gm`, the 200 nA reference |
| `size_bias_trim.ipynb` | `bias_trim`, the trimmed output, reads `bias_gm.sch` too |
| `size_dsm2_osc.ipynb` | `dsm2_osc`, the ring oscillator |
| `size_sw_tgate.ipynb`, `size_sw_tgate_cmfb2.ipynb` | the two transmission-gate switches, on resistance from the tables |
| `size_sc_int2.ipynb` | `sc_int2`, the switched-capacitor integrator, runs `size_ota_fcasc2.py` |
| `size_cmfb_sc2.ipynb` | `cmfb_sc2`, the common-mode feedback |
| `size_vcm_gen.ipynb` | `vcm_gen`, the common-mode voltage generator |
| `size_quantizer2.ipynb` | `quantizer2`, the comparator and the dither |
| `size_ota_fcasc2.py` | `ota_fcasc2`, the OTA of the integrator, `--point equal_l\|current`, `--compare` |

## Run

Requirements: Python 3 with `pygmid`, `numpy`, `jupyter` and, for the `.py`, `python-deltasigma`. The notebooks run from this folder, the script from here or from the repo root. The system-level values they start from (1.5 V, 1 mV LSB, OSR 512 at 1.024 MHz, first-order CIFB with a1 = 1/3, C1 = 64 fF, seed 1 in the `.py`) are listed in `../model/README.md`.

```sh
cd ip/dsm2_core/sizing
jupyter nbconvert --to notebook --execute --inplace size_bias_gm.ipynb
python3 size_ota_fcasc2.py
```

The tables are `macros/inverter/scripts/sizing/data/*.mat`, shared and not copied. The stored outputs were made from this tree on 2026-11-07, `size_quantizer2.ipynb` on 2026-11-08. The text outputs equal the delivered ones. `data_README.md` is the designer's note on the tables, delivered as is and written for the designer's `data/` folder, which is `macros/inverter/scripts/sizing/data/` here. The notebooks and the docs name files by their paths in the designer's tree (`macros/...`), which do not exist here. The `netlist/` files are the designer's exports without their `sch_path` and `sym_path` comment lines.

`python-deltasigma` is not in the sign-off image, and 0.2 does not import on current numpy, scipy and Python 3.12 as it is. The 2026-11-07 rerun of the `.py` and of `size_sc_int2.ipynb` used a throwaway first-order stand-in for the four calls the script makes (`synthesizeNTF`, `realizeNTF`, `undbv`, `simulateDSM`), not the library. The text outputs of `size_sc_int2.ipynb`, which runs the script, equal the delivered ones. The stand-in is not kept, so this rerun cannot be repeated here without a working `python-deltasigma`.

## What these numbers are

The tables are gm/ID tables of the SG13G2 devices (variable `sg13g2_lv_nmos`, INFO "IHP SG13G2, 130nm CMOS, PSP"). They were swept with the SG13G2 PSP models, which SG13CMOS5L shares: in the PDK of iic-osic-tools:next dd952ba01866 every MOS model file (`sg13g2_moslv`, `moshv` and `moscap` `_mod`, `_parm`, `_stat`, `_mismatch`, the MOS corner files) and `psp103.osdi` are byte-identical between ihp-sg13g2 and ihp-sg13cmos5l. Only the diode and capacitor models differ, and the tables do not use them. The sweep is dated 2026-02-28, older than that PDK, so a model update in between is not ruled out by the files alone.

They are sizing derivations at typical conditions, not evidence over PVT or mismatch.
