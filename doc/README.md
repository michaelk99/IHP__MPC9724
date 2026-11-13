# Documentation

Reference material for this chip and for the IHP SG13CMOS5L Open-PDK it is built on.

## This chip

| Document | Contents |
| --- | --- |
| [specifications.md](specifications.md) | Top-level specifications: technology, supplies, clock, corner list, macro inventory, functional behaviour of every block. |
| [pinout.md](pinout.md) | The QFN24 lead table and the 21 bondpads on four sides, with the `sg13cmos5l_dsa1_dig_top` port and the role each pad carries inside `sg13cmos5l_dsa1_dig_core`. |
| [floorplan.md](floorplan.md) | Die and core geometry, hard-macro placement coordinates, the PDN strategy and the floorplan diagram. |
| [../testbenches/README.md](../testbenches/README.md) | What the chip-level testbenches cover: the cocotb tests, the opt-in PSD run, two register-file properties bring-up software needs, and what is still unverified. |
| [running.md](running.md) | How to run the targets in the IIC-OSIC-TOOLS container, the five exports they need, and what each gate proves. |
| [rtl2gds.md](rtl2gds.md) | How RTL becomes GDS here: the cell library outside the repo, the clock-gate pre-pass, why a hard macro carries its own metal fill, what each verdict means, the traps already hit. |
| [../macros/decimator/rtl/README.md](../macros/decimator/rtl/README.md) | The SystemVerilog sources of the decimation filter: file list, word widths, why the CIC is order 6, and the house rules for editing them. |
| [regmap.md](regmap.md) | The SPI register map, generated from `macros/dsa1_dig/regmap.yaml`. |
| [Datasheet.md](Datasheet.md) | One page of the chip's key numbers, each linked to the document it comes from. |
| [signoff.md](signoff.md) | The sign-off record of the delivered v1.2.1: checks, accepted items, the IHP audit dispositions. |
| [tapeout_status.md](tapeout_status.md) | Status of v1.2.1 after the recheck of every Magic DRC verdict for the flatten flag, 2026-11-12, and the two `M1.e` items in dsm2. |
| [dsm2_integration.md](dsm2_integration.md) | The design spec for integrating `dsm2_core` next to the back end. |
| [esd_hbm.md](esd_hbm.md) | HBM ESD simulation of the pad ring on its extracted metal. |
| [host_protocol.md](host_protocol.md) | How a bench host drives the chip: programs, records, and what the chip requires of any host. |
| [layout_index.md](layout_index.md) | Where each item of IHP's `MPC9724-main/` structure lives in this repo. |
| [TRL-Mixed-Signal-IP.md](TRL-Mixed-Signal-IP.md) and [info.json](info.json) | The TRL self-assessment (TRL3) and IHP's project metadata. |
| [../release/](../release/) | One folder per release. [v.1.2.1](../release/v.1.2.1/README.md) is the delivered chip. |

`specifications.md`, `pinout.md` and `floorplan.md` are written against the design files, not the other way round. If you change a number in [flow/librelane/config.yaml](../flow/librelane/config.yaml), [rtl/](../rtl/) or [packaging/config.yaml](../packaging/config.yaml), mirror it here.

## Tools

| Document | Contents |
| --- | --- |
| [klayout/klayout_cheatsheet.md](klayout/klayout_cheatsheet.md) | KLayout for this PDK: shortcuts, the `SG13_dev` PCell list, layer roles, padframe components, the DRC and LVS menu entries. |
| [librelane/librelane_cheatsheet.md](librelane/librelane_cheatsheet.md) | LibreLane `final/` directory anatomy, non-default routing rules, the complete SG13CMOS5L via and metal-stack tables, the eight LEF/DEF orientations. |
| [verilog/](verilog/) | Verilog and SystemVerilog cheatsheets (external documents, PDK-independent). |

## PDK

| Document | Contents |
| --- | --- |
| [ihp-sg13cmos5l-Open-PDK/sg13cmos5l_os_layout_rules.pdf](ihp-sg13cmos5l-Open-PDK/sg13cmos5l_os_layout_rules.pdf) | The IHP layout rules. The authoritative source when a tool deck and a datasheet disagree. |
| [ihp-sg13cmos5l-Open-PDK/sg13cmos5l_os_process_spec.pdf](ihp-sg13cmos5l-Open-PDK/sg13cmos5l_os_process_spec.pdf) | The IHP process specification. |
| [ihp-sg13cmos5l-Open-PDK/sg13cmos5l_os_layout_cheatsheet.xlsx](ihp-sg13cmos5l-Open-PDK/sg13cmos5l_os_layout_cheatsheet.xlsx) | One sheet of formulas for wire resistance, parasitic capacitance and DC current limits. Read the caveats below before using it. |
| [ihp-sg13cmos5l-Open-PDK/sg13cmos5l_ngspice_mc_mm_guide.md](ihp-sg13cmos5l-Open-PDK/sg13cmos5l_ngspice_mc_mm_guide.md) | How the ngspice model files fit together, what `mm_ok` and `num_sigmas` do, and which corner, Monte Carlo and mismatch runs are possible per device family. |
| [sizing/](sizing/) | gm/ID techsweep plot overviews for the LV and HV MOS devices, the data behind the dsm2 sizing in [ip/dsm2_core/sizing/](../ip/dsm2_core/sizing/). |

## Other

[ihp-structure-proposals/](ihp-structure-proposals/) holds four proposed submission-repo layouts for IHP shuttle chips (an ADC, an LNA, an MCU and an op-amp), PDK-independent and kept verbatim from the SG13G2 template. Their generator `gen_structure.py` is not tracked (see [.gitignore](../.gitignore)).

## Provenance and caveats

The two PDK PDFs are unchanged copies from `libs.doc/doc/` of the SG13CMOS5L PDK (`ihp-sg13cmos5l @ ff32f48`, the PDK in the IIC-OSIC-TOOLS 2026.08 image), renamed to lower case: layout rules **Rev. 0.1 (2025-12-08)**, process specification **Rev. 0.2 (2025-12-15)**, as on each title page. Check that stamp against `$PDK_ROOT/$PDK/libs.doc/doc/` before letting one of them decide a rule.

Three items come from the SG13G2 sibling of this template:

- **The layout cheatsheet is the SG13G2 sheet**, byte-identical to `sg13g2_os_layout_cheatsheet.xlsx`. Its `M5`, `TM2` and `TV2` rows do not exist on this stack, the `M1`..`M4`, `TM1`, `Contact`, `Via 1/2/3` and `TV1` rows apply. On both PDKs the resistance columns use bulk-aluminium resistivity and are optimistic by roughly a factor of two against the tech LEF, and "min. Width" lists 0.42 µm for TopMetal1 where the LEF says 1.64 µm. Take widths from the DRC deck, resistance from the tech LEF or PEX, and current limits from the [LibreLane cheatsheet](librelane/librelane_cheatsheet.md) tables, read out of `sg13cmos5l_tech.lef`.
- **The gm/ID techsweep plots are the SG13G2 sweep.** The LV and HV MOS ngspice models of this PDK are symbolic links into `ihp-sg13g2/libs.tech/ngspice/models/`, so the curves are the same. The `.mat` lookup tables under [ip/dsm2_core/sizing/data/](../ip/dsm2_core/sizing/data/) are byte-identical to the SG13G2 ones under a SG13CMOS5L name, and the PDF captions still read "SG13G2".
- **The Verilog and SystemVerilog cheatsheets** are external documents with no PDK content at all.

Only `regmap.md` is generated, by `make -C macros/dsa1_dig regmap`.
