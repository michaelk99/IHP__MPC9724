<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# Start-up with dsm2 on by default, the record

The `STARTUP_DEFON=1` runs of `testbenches/startup/` behind the start-up rows of `doc/signoff.md`. All at tt, 1 MOhm on the vcm pad unless named.

| folder | run | dsm2 | host, wall time |
|---|---|---|---|
| `sch_core_first` | `STARTUP_ORDERS=core_first` | schematic | laptop, 520 min |
| `sch_io_first` | `STARTUP_ORDERS=io_first` | schematic | the ARM64 compute host (`IMAGE_ARM64`), 1980 min, 2026-11-06 to 11-07 |
| `sch_vdda_last` | `STARTUP_ORDERS=vdda_last` | schematic | laptop, 519 min |
| `sch_core_first_vcm10g` | `core_first`, `STARTUP_END_US=480`, 10 GOhm on vcm | schematic | laptop, 197 min |
| `pex_core_first` | `core_first`, `STARTUP_DSM2=pex STARTUP_END_US=500 STARTUP_RELTOL_SWITCH=3e-3:120u` | extracted | laptop, started 2026-11-06, done 2026-11-08 07:38, about 43 h |

Per folder:
- `startup_report_as_run.md`: the checker's report as the run wrote it. That checker held dsm2 to 28 uA average and 140 uA over 100 ns, the 6dd2926 baseline, and left out any stretch above 100 uA for 200 ns before di_rst_b as 6dd2926's latch fight. The delivered dsm2 has no such fight, so in `core_first` that exclusion hid the burst at the IOVDD ramp.
- `startup_report.md`: the committed `startup_check.py` on the same waveform data, no new simulation, 2026-11-08. It uses the variant's design values, 32 uA, 220 uA over 100 ns and 600 uA over 10 ns, and has no exclusion. All five pass.
- `waves.txt`: `testbenches/startup/defon_waves.py` on the same data. dsm2's output edges against di_clk, the burst while IOVDD ramps, vcm, and dsm2's current while VDDA ramps.

Notes:
- The extracted run ran ngspice directly on a testbench that `run_startup.sh` with `STARTUP_RELTOL_SWITCH=3e-3:120u` writes byte for byte, with recipe 1 (`method=gear cshunt=1e-15`). So its as-run report has no solver and wall time lines.
- In `sch_core_first` and `sch_vdda_last` the checker call of the working-tree `run_startup.sh` failed with exit code 127 (`--dsm2: command not found`, a split line). The reports were written by the checker with its defaults, the view read from `dsm2_probes.json`, and its exit code was not seen. `startup_report.md` here is the committed checker's.
- The waveform data (100 to 190 MB per run) are not kept.
- ss -40 C (`STARTUP_CORNER=ss_m40`) was tried in `vdda_last` and did not finish: ngspice stalled at the do_q_b pad diode. Its logs are not kept, so this record has no ss run.
