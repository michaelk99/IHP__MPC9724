# dsm2_core Python models

Behavioural models of the first-order modulator, delivered by dsm2 and not edited apart from the 2026-11-09 wording change below. They are Python, not HDL. `../verilog/dsm2_core_model.v` is a PRBS stand-in for the cocotb bench, not a functional model.

| File | What it reproduces |
| --- | --- |
| `dsm_system.py` | The system-level modulator: CIFB loop with a1 = 1/3 at `H_inf` 1.2, integrator leak from finite OTA gain, the OTA input noise, kT/C and folded thermal noise. Writes the PSD at any FFT length, or a DC sweep with `--dc-sweep`. Runs with numpy only, `deltasigma` is used for one optional check |
| `psd_bitstream.py` | The PSD and SNR of a simulated bit stream from an ngspice or VACASK raw file. `dsm_system.py` imports its frequency plan. Needs a raw file of `dsm_tb_psd`, which is not in this repo |
| `dither_deadzone.py` | The dither loop with the real 17-bit XNOR LFSR of `quantizer2` (taps 17 and 14, three bits per clock). Gives the DC transfer and the dead zone with and without dither. Needs `deltasigma` |

Smoke runs on 2026-11-08 in the sign-off image: `dsm_system.py` (PSD and DC sweep) ran and wrote its files. `dither_deadzone.py` stopped at `import deltasigma`, which the image does not have. `psd_bitstream.py` was not run for lack of a raw file.

## Setup

The models need Python 3 with `numpy`, `matplotlib` and `python-deltasigma`. The sizing in `../sizing/` also needs `pygmid` and the gm/ID tables in `macros/inverter/scripts/sizing/data/`.

The system-level spec is a battery monitor ADC on a 1.5 V supply from a DC/DC (1.45 to 1.55 V): 1 mV LSB, full scale `vdd` = 1.5 V, reference `vdd/2` = 0.75 V, band edge 1 kHz. The loop is a first-order single-bit CIFB modulator from `synthesizeNTF` with `H_inf` 1.2, so a1 = b1 = 1/3. OSR 512 is the first-order SQNR equation for 10.55 bit, rounded up to a power of 2 and times 4 margin, so fs = 1.024 MHz. C1 = 64 fF, C2 = 2 C1/a1 = 384 fF. Random draws use seed 1 (`rng_seed = 1`, `--seed 1`).

On 2026-11-09 the references to the designer's system-level notebook in `dither_deadzone.py`, `dsm_system.py` and `psd_bitstream.py` were replaced by the setup they stood for. Only comments, docstrings, help and print text changed, no code or number. `psd_bitstream.py` still names `macros/dsm/...` in the designer's tree, which is not part of this repo.
