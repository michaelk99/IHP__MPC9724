# Mixed-Signal IP Quality Assessment using TRL scale

The provided set of the quality assessment criteria, using TRL (Technology Readiness Level) scale, is a tool for designers to auto evaluate a submitted design. The purpose of this tool is to
have a short overview of IP in terms of its maturity.

A level counts only when every box of it and of the levels below is ticked. TRL1 to TRL3 are ticked. The first open box is the modulator-level mismatch Monte Carlo of TRL4, so `doc/info.json` gives `trl` 3.

---

## TRL1 - Basic principles observed

- [x] Is the IP functionality clearly described? `doc/specifications.md`
- [x] Is the IP principle of operation explained in detail? `doc/specifications.md` (Signal chain), `models/README.md` (What it reproduces), `ip/dsm2_core/doc/dsm2_README.md` (the modulator and its blocks)
- [x] Are the IP architecture design equations fully listed? `ip/dsm2_core/model/equations.md` (spec, loop, NTF and STF with values, switched-capacitor realisation, leak, dither, decimation, noise budget), every closed-form value recomputed by `ip/dsm2_core/model/check_equations.py` (96 checks, 0 failed, against model and simulation values, nothing measured)
- [x] Do authors supply any mixed-signal HDL functional model (e.g. Verilog-A) of the IP? `ip/dsm2_core/model/dsm2_core.va` (Verilog-A, OpenVAF and ngspice), checked bit for bit against `ip/dsm2_core/model/dsm_system.py` in `ip/dsm2_core/model/va_check/` (model against model, nothing measured). `ip/dsm2_core/verilog/dsm2_core_model.v` stays a PRBS stand-in for the cocotb bench
- [x] Are functional simulation results of the IP reported for a typical case? `doc/specifications.md` (Verification status), `models/README.md`

## TRL2 - Concept formulation

- [x] Is the IP architecture described at block level? `doc/specifications.md`, `doc/floorplan.md`
- [x] Are the specifications of each individual block of the IP architecture clearly identified? `ip/dsm2_core/doc/` (`dsm2_README.md`, `quantizer2_README.md`, `bias_gm_README.md`, `bias_trim_README.md`, `dsm2_osc_README.md`, `sc_int2_README.md`, `cmfb_sc2_README.md`, `vcm_gen_README.md`), `ip/dsm2_core/sizing/` (each notebook starts from the block's spec), `doc/specifications.md` for the digital part
- [x] If the IP architecture can be configured by means of internal registers, is their mapping declared? `doc/regmap.md`, generated from `macros/dsa1_dig/regmap.yaml`
- [x] Do authors supply a complete test bench to validate the IP block-level architecture? `testbenches/README.md`, `testbenches/cocotb/`, `models/`. Covers the digital part. For dsm2 see the transistor-level benches under TRL3
- [x] Is any verification procedure given to check the IP block-level performance figures? `doc/running.md` (the gates), `models/README.md` (gate scripts, `stream_psd.py`)
- [x] Are architectural simulation results of the IP reported for a typical case? `doc/specifications.md` (Verification status), `models/README.md`


## TRL3 - Proof of concept at schematic level

- [x] Are the IP schematics available at transistor level (analog parts) and gate level (digital parts)? Analog: `ip/dsm2_core/spice/dsm2_core_sch.spice` and the block schematics in `ip/dsm2_core/schematic/`. Digital: `macros/dsa1_dig/final/nl/`
- [x] Are all dependencies of the IP schematics on logic libraries declared? `doc/info.json` (dependencies), `verification/signoff_env.txt` (library md5s)
- [x] Are the analog IP ports fully specified at electrical level? `ip/dsm2_core/spice/README.md` (Ports: levels, `vcm` = vdd/2, `ibias_test` at 0.5 V, 1.5 V and 1.2 V domains), `ip/dsm2_core/README.md` (pins), `doc/pinout.md`
- [x] Are the digital IP ports fully specified at logical level (e.g. protocols)? `doc/pinout.md`, `doc/host_protocol.md`
- [x] Do authors supply a mixed-signal test bench to validate the IP schematics? `testbenches/startup/` (core as XSPICE, IO cells, clamp and dsm2 as transistors), `ip/dsm2_core/spice/smoke_sch.spice`
- [x] Is any verification procedure given to check the IP schematic performance figures? `ip/dsm2_core/doc/measurement_plan.md` (a simulated value for every lab number), `ip/dsm2_core/doc/dsm2_README.md`
- [x] Are mixed-signal simulation results of the IP schematics reported for a typical case? `ip/dsm2_core/doc/dsm2_README.md` (SNDR at tt, one run), the start-up bench with dsm2 on by default passes at tt for `core_first`, `io_first` and `vdda_last` (2026-11-06 to 11-07), its record is `testbenches/startup/README.md` and `verification/startup/defon/`

*Done at the block and chip level. The top schematic of dsm2 is delivered as a netlist, the dsm2 block schematics are in `ip/dsm2_core/schematic/`, 11 sheets. The template's chip-level Xschem bench was deleted, the start-up transient is in `testbenches/startup/`.*

## TRL4 - Full design at schematic level

- [x] Are the mixed-signal simulation results of the IP schematics extended to process, supply and temperature (PVT) corners? dsm2 simulated over PVT at five corners, `ip/dsm2_core/doc/dsm2_README.md` (Corners), `ip/dsm2_core/doc/dsm2_osc_README.md`, `ip/dsm2_core/doc/bias_gm_README.md`
- [ ] Are the mixed-signal simulation results of the IP schematics extended to technology mismatching?
- [x] Are the authors defining the mixed-signal supply domains of the IP schematics and their individual power requirements? `doc/specifications.md` (Overview, Power), `doc/pinout.md`
- [x] Does the IP description include any power consumption model (e.g. as a function of input stimuli)? `doc/specifications.md` (Power, static and dynamic)

*Open: Monte Carlo of the whole of dsm2. `bias_gm` and `bias_trim` have a mismatch Monte Carlo of 200 runs each in the delivered READMEs, and `ip/dsm2_core/doc/ota_fcasc2_README.md` reports a local mismatch Monte Carlo of `ota_fcasc2` (100 runs, `tt_mismatch`, 27 C, 1.5 V, before the dummy rows, not rerun), and `dsm2_README.md` lists noise and mismatch runs as missing. A modulator-level mismatch Monte Carlo was started on 2026-11-08 and stopped before any run finished: with the solver options that keep the `dpantenna` diode of `dsm2_io_esd` converging, one 2048-clock schematic run takes on the order of 100 h on a laptop, against 2 to 7 h per run for the delivered PVT set, and looser options abort the run without mismatch at clock 146. Such a run would also leave the standard cells and every `cap_cmomf` unvaried, since the standard cell netlist passes no `mm_ok` and `cap_cmomf` has no mismatch model (`doc/ihp-sg13cmos5l-Open-PDK/sg13cmos5l_ngspice_mc_mm_guide.md`, section 6). The sizing notebooks are gm/ID derivations at tt, not PVT or Monte Carlo evidence. The digital part has three-corner STA, which is not a mixed-signal simulation.*

## TRL5 - Full design at layout level

- [x] Is the IP complete layout available? `layout/sg13cmos5l_dsa1_dig_top_logo_fill.gds.gz`, `release/v.1.2.1/gds/MPC9724.gds.gz`, `ip/dsm2_core/gds/`
- [x] Are all dependencies of the IP layout on logic libraries declared? `doc/info.json` (dependencies), `verification/signoff_env.txt` (library md5s)
- [x] Do authors supply a clean DRC report? IHP's precheck deck on the release file, 0 markers (`verification/submission/precheck_verdict.txt`). The regular KLayout deck shows 37 items, all recommended bondpad rules on IHP's cells and accepted, see `doc/signoff.md` (IHP audit, 2026-11-07)
- [x] Do authors supply a clean LVS report? `verification/submission/lvs.rpt` (`Circuits match uniquely` on the release file), `ip/dsm2_core/lvs/` (dsm2's KLayout LVS, "Netlists match", with the MOM capacitors)
- [ ] Are post-layout mixed-signal simulation results of the IP layout reported for PVT corners? dsm2 has a post-layout simulation of its extracted view at five corners (`ip/dsm2_core/doc/dsm2_README.md`). dsm2's extracted view in the chip start-up bench (the core as XSPICE, the pads as transistors) ran at tt in `core_first` to 500 us and finished on 2026-11-08: dsm2 starts with no SPI write and runs, and every check passes against dsm2's design values (`doc/signoff.md`, `verification/startup/defon/`)

*Open: post-layout over PVT. One block's extracted view at five corners and one chip start-up at tt with dsm2's extracted view are not post-layout over PVT. The records are in `doc/signoff.md` and `doc/specifications.md`.*

## TRL6 - Full design for SoC integration

- [x] Does the IP come with suitable descriptors for digital-on-top integration (e.g. Liberty, LEF)? `macros/dsa1_dig/final/lef/`, `macros/dsa1_dig/final/lib/`. Only the digital macro has timing, dsm2_core has a LEF (`ip/dsm2_core/lef/`) without Liberty
- [x] Is the IP incorporating any BIST mechanism? If so, is it properly documented? the on-chip stimulus generator, `doc/specifications.md` (Stimulus test mode)
- [x] Does the IP document fully define its digital interface? `doc/pinout.md`, `doc/host_protocol.md`, `doc/regmap.md`

## TRL7 - Lab demonstrator prototype

- [ ] Has any dedicated test chip been designed for the hard IP?
- [ ] Is the hard IP test chip fully documented (e.g. pad ring)?
- [ ] Are experimental results available from the IP dedicated test chip (Silicon proven)?
- [ ] Do authors supply any comprehensive comparison between IP test chip and post-layout results?

*Not done. No silicon yet.*

## TRL8 - In-field demonstrator prototype

- [ ] Has the hard IP been integrated in a SoC context?
- [ ] Are experimental IP results available from this SoC (Silicon proven)?
- [ ] Do authors supply any comprehensive comparison between IP SoC and test-chip results?

*Not done. No silicon yet.*

## TRL9 - Commercial application

- [ ] Are the IP authors providing support for bug fixing or enhancement requests?
- [ ] Does the IP documentation include any training materials?
- [x] Are the EDA tools and versions used for developing the IP documented? `verification/signoff_env_v1.2.1.txt` (v1.2.1), `verification/signoff_env.txt` (v1.1.1), `scripts/image.env`, `doc/info.json` (tools)
- [ ] Is the hard IP integrated in any commercial IC?

*Not done, apart from the tool versions.*
