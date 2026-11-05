# Mixed-Signal IP Quality Assessment using TRL scale

The provided set of the quality assessment criteria, using TRL (Technology Readiness Level) scale, is a tool for designers to auto evaluate a submitted design. The purpose of this tool is to
have a short overview of IP in terms of its maturity.

---

## TRL1 - Basic principles observed

- [x] Is the IP functionality clearly described? `doc/specifications.md`
- [x] Is the IP principle of operation explained in detail? `doc/specifications.md` (Signal chain), `models/README.md` (What it reproduces). dsm2_core is still an abstract box, see `ip/dsm2_core/README.md`
- [ ] Are the IP architecture design equations fully listed?
- [ ] Do authors supply any mixed-signal HDL functional model (e.g. Verilog-A) of the IP?
- [x] Are functional simulation results of the IP reported for a typical case? `doc/specifications.md` (Verification status), `models/README.md`

*Open: the architecture equations are not listed, and there is no HDL model of dsm2 (`ip/dsm2_core/verilog/dsm2_core_model.v` is a PRBS stand-in for benches).*

## TRL2 - Concept formulation

- [x] Is the IP architecture described at block level? `doc/specifications.md`, `doc/floorplan.md`
- [ ] Are the specifications of each individual block of the IP architecture clearly identified?
- [x] If the IP architecture can be configured by means of internal registers, is their mapping declared? `doc/regmap.md`, generated from `macros/dsa1_dig/regmap.yaml`
- [x] Do authors supply a complete test bench to validate the IP block-level architecture? `testbenches/README.md`, `testbenches/cocotb/`, `models/`. Covers the digital part, dsm2 is a stand-in
- [x] Is any verification procedure given to check the IP block-level performance figures? `AGENTS.md` (the gates), `models/README.md` (gate scripts, `stream_psd.py`)
- [x] Are architectural simulation results of the IP reported for a typical case? `doc/specifications.md` (Verification status), `models/README.md`

*Open: block specifications of dsm2_core beyond its pins, which arrive with its views.*

## TRL3 - Proof of concept at schematic level

- [ ] Are the IP schematics available at transistor level (analog parts) and gate level (digital parts)?
- [x] Are all dependencies of the IP schematics on logic libraries declared? `doc/info.json` (dependencies), `verification/signoff_env.txt` (library md5s)
- [ ] Are the analog IP ports fully specified at electrical level?
- [x] Are the digital IP ports fully specified at logical level (e.g. protocols)? `doc/pinout.md`, `doc/host_protocol.md`
- [ ] Do authors supply a mixed-signal test bench to validate the IP schematics?
- [ ] Is any verification procedure given to check the IP schematic performance figures?
- [ ] Are mixed-signal simulation results of the IP schematics reported for a typical case?

*Open: dsm2_core schematics, a mixed-signal bench (`testbenches/xschem` is still the template's stub), and its simulation results.*

## TRL4 - Full design at schematic level

- [ ] Are the mixed-signal simulation results of the IP schematics extended to process, supply and temperature (PVT) corners?
- [ ] Are the mixed-signal simulation results of the IP schematics extended to technology mismatching?
- [x] Are the authors defining the mixed-signal supply domains of the IP schematics and their individual power requirements? `doc/specifications.md` (Overview, Power), `doc/pinout.md`
- [x] Does the IP description include any power consumption model (e.g. as a function of input stimuli)? `doc/specifications.md` (Power, static and dynamic)

*Open: PVT and mismatch simulations of dsm2_core. The digital part has three-corner STA, which is not a mixed-signal simulation.*

## TRL5 - Full design at layout level

- [ ] Is the IP complete layout available?
- [x] Are all dependencies of the IP layout on logic libraries declared? `doc/info.json` (dependencies), `verification/signoff_env.txt` (library md5s)
- [ ] Do authors supply a clean DRC report?
- [ ] Do authors supply a clean LVS report?
- [ ] Are post-layout mixed-signal simulation results of the IP layout reported for PVT corners?

*Open: dsm2_core is an abstract box until its real layout arrives, so the layout is not complete, and DRC and LVS of the final GDS follow it. The v1.1.1 digital die and the integration run have records in `doc/signoff.md` and `doc/specifications.md`.*

## TRL6 - Full design for SoC integration

- [x] Does the IP come with suitable descriptors for digital-on-top integration (e.g. Liberty, LEF)? `macros/dsa1_dig/final/lef/`, `macros/dsa1_dig/final/lib/`. Only the digital macro, dsm2_core has an abstract LEF without timing
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
- [x] Are the EDA tools and versions used for developing the IP documented? `verification/signoff_env.txt`, `scripts/image.env`, `doc/info.json` (tools)
- [ ] Is the hard IP integrated in any commercial IC?

*Not done, apart from the tool versions.*
