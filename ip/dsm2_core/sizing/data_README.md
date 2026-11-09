# gm/ID tables

The four `sg13cmos5l_*.mat` files are the SG13G2 device sweeps of the IHP chip template, renamed when the template was ported (the variable inside is still `sg13g2_lv_nmos` and so on, INFO "IHP SG13G2, 130nm CMOS, PSP"). They are byte-identical to the `sg13g2_*.mat` of ihp-sg13g2-ams-chip-template.

They are valid for SG13CMOS5L because its MOS models are the SG13G2 ones. In iic-osic-tools:next (dd952ba01866) every LV, HV and MOS-cap model file (`_mod`, `_parm`, `_stat`, `_mismatch`, `cornerMOSlv`, `cornerMOShv`, `cornerMOSCAP`) and the `psp103.osdi` are identical between `ihp-sg13g2` and `ihp-sg13cmos5l`. What differs is the diode, cap_cmom and their corner files, which the tables don't use.

The sweep date (2026-02-28) predates that PDK, so a model update in between would not show here.

Every sizing notebook and `size_ota_fcasc2.py` in `macros/` read the files from here.
