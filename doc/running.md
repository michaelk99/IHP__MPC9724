# Running the flows and the gates

## Running anything

Every target runs inside an IIC-OSIC-TOOLS container, started with `docker run` or entered with `docker exec <your IIC-OSIC-TOOLS container>`. The projects directory is mounted at `/foss/designs`, so this repo is `/foss/designs/sg13cmos5l_dsa1_dig`.

```sh
docker exec <your IIC-OSIC-TOOLS container> bash -lc '
  cd /foss/designs/sg13cmos5l_dsa1_dig
  export PDK=ihp-sg13cmos5l PDKPATH=/foss/pdks/ihp-sg13cmos5l PDK_ROOT=/foss/pdks
  export STD_CELL_LIBRARY=sg13cmos5l_stdcell SCL=sg13cmos5l_stdcell
  export EZ130_DIR=/foss/designs/sg13cmos5l_dsa1_dig/ip/ez130_8t_v1p1
  export DECAPHV_DIR=/foss/designs/sg13cmos5l_dsa1_dig/ip/ez130_8t_decap_hv
  make <target>'
```

**All five exports matter.** A parse-time guard in each `Makefile` catches a wrong `PDK`, but `STD_CELL_LIBRARY` is only set by `sak-pdk` in an interactive shell, and without it LibreLane dies looking for `sg13g2_stdcell/config.tcl` under the CMOS5L PDK. `EZ130_DIR` and `DECAPHV_DIR` default to `ip/ez130_8t_v1p1` and `ip/ez130_8t_decap_hv`, EZ130 8T v1.1 (ETH Zurich, Apache-2.0).

A full macro or chip harden is 30 to 60 minutes. Run it in the background.

## The gates, and what each one proves

| target | proves |
|---|---|
| `make -C macros/<m> sim-gl` | the hardened netlist is the RTL |
| `make -C macros/<m> model-gate` | the RTL is the design, against `models/` |
| `make -C macros/dsa1_dig sim-cdc` | the ready flag and the stimulus bits cross between clk and sclk at every phase, sclk 1.05 to 12.7 times clk, and a 0.8 control run is caught |
| `make -C macros/<m> check-netlist` | no cell that is wrong in silicon got in |
| `make -C macros/dsa1_dig lec`, `lec-fail` | the hardened netlist is the RTL for every input sequence, and the check can fail |
| `make -C macros/dsa1_dig regmap-check` | every file made from `regmap.yaml` is current |
| `make klayout-drc-regular`, `magic-drc` | geometry |
| netgen LVS, in the flow | layout against the synthesized netlist |
| `make sim-rtl-cocotb`, `sim-gl-cocotb` | pad mapping and the bitstream synchronizer |

`sim-gl` and `model-gate` are not interchangeable. The first compares two things that share a source and would agree if both were wrong. `models/` is the independent description.
