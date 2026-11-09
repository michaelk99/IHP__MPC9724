<!--
SPDX-FileCopyrightText: 2026 Michael Koefinger
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-->

# dsm2_core architecture design equations

The design equations of the first-order single-bit modulator in `dsm2_core`, each with its symbols, the values of this design and the file the value comes from or is checked against. Paths are relative to `ip/dsm2_core/`. Every closed-form value on this page was recomputed from its equation, see [Checks](#checks). Simulation values are quoted from the READMEs as they stand. "Sim" marks a simulation result from a README, "model" a result of the Python models, "derived" a value computed on this page.

Units in the loop equations are normalised to the DAC reference $V_\mathrm{REF}$: the input is $u = (v_\mathrm{i} - v_\mathrm{cm})/V_\mathrm{REF}$, the state is $x = v_\mathrm{od}/V_\mathrm{REF}$ with $v_\mathrm{od}$ = `vo_p - vo_n` of `sc_int2`, and the output is $v = \pm 1$ (`do_q` high is $+1$). This is the mapping of `model/dsm_system.py` ("The state maps to it as vod = x*V_REF").

## 1. Specification

| Symbol | Meaning | Value | Source |
| --- | --- | --- | --- |
| $V_\mathrm{DD}$ | supply, from a DC/DC | 1.5 V (1.45 to 1.55 V) | `model/README.md` Setup |
| $V_\mathrm{FS}$ | full-scale input range | $V_\mathrm{DD}$ = 1.5 V | `model/README.md` Setup |
| $V_\mathrm{REF}$ | DAC reference, half the full scale | $V_\mathrm{DD}/2$ = 0.75 V | `model/README.md` Setup |
| $v_\mathrm{cm}$ | `vcm`, the input and DAC midpoint | $V_\mathrm{DD}/2$ = 0.75 V | `doc/dsm2_README.md` (`vcm_gen` in the block) |
| $V_\mathrm{LSB}$ | resolution | 1 mV | `model/README.md` Setup |
| $f_\mathrm{b}$ | band edge | 1 kHz | `model/README.md` Setup |
| $N$ | quantizer bits | 1 (2 levels) | `model/README.md` Setup |
| $L$ | loop order | 1 | `model/README.md` Setup |

The DAC levels are `vdd` and `vss`, so the feedback is $v_\mathrm{cm} \pm V_\mathrm{REF}$ and the input range is $-1 \le u \le 1$.

The code is ratiometric to the supply. `vcm` sits at $V_\mathrm{DD}/2$ and the DAC levels `vdd` and `vss` sit $\pm V_\mathrm{DD}/2$ from it, so the reference scales with `vdd` and for a fixed $v_\mathrm{i} - v_\mathrm{cm}$ the bit mean and its sensitivity are

$$
\bar{v} = \frac{v_\mathrm{i} - v_\mathrm{cm}}{V_\mathrm{DD}/2}, \qquad \frac{d\bar{v}}{\bar{v}} = -\frac{dV_\mathrm{DD}}{V_\mathrm{DD}}
$$

Over 1.45 to 1.55 V the code moves by +3.4 % to $-3.2$ %, at $v_\mathrm{i} - v_\mathrm{cm}$ = 0.3 V from 0.4 to 0.4138 and 0.3871 (`doc/dsm2_README.md`, Corners). Noise on `vdd` enters on the high DAC level only, in `model/dsm_system.py` the feedback is $v + (1+v)\,v_\mathrm{n}/2$ (`--vdd-noise`).

Resolution and the peak SQNR it asks for:

$$
\mathrm{ENOB} = \log_2\frac{V_\mathrm{FS}}{V_\mathrm{LSB}} = \log_2 1500 = 10.55\ \mathrm{bit}
$$

$$
\mathrm{SQNR_{spec}} = 6.02\,\mathrm{ENOB} + 1.76 = 65.28\ \mathrm{dB}
$$

The circuit noise budget equals the quantization noise of one LSB, in band:

$$
v_\mathrm{th} = \frac{V_\mathrm{LSB}}{\sqrt{12}} = 288.68\ \mu\mathrm{V_{rms}}
$$

Peak SQNR of an $L$-th order loop with an $N$-bit quantizer and a full-scale sine, in the linear model:

$$
\mathrm{SQNR} = 6.02\,N + 1.76 + 10\log_{10}\frac{2L+1}{\pi^{2L}} + (2L+1)\,10\log_{10}\mathrm{OSR}
$$

For $L = N = 1$ the shaping term is $10\log_{10}(3/\pi^2) = -5.17$ dB. Solved for the OSR that meets the spec, then rounded up to a power of two and multiplied by a margin of 4, because a first-order loop is tonal and the circuit noise should dominate:

$$
\mathrm{OSR_{min}} = 10^{\left(\mathrm{SQNR_{spec}} - 6.02 N - 1.76 - 10\log_{10}(3/\pi^2)\right)/30} = 122.7
$$

$$
\mathrm{OSR} = 4 \cdot 2^{\lceil \log_2 \mathrm{OSR_{min}} \rceil} = 4 \cdot 128 = 512
$$

$$
f_\mathrm{s} = 2 f_\mathrm{b}\,\mathrm{OSR} = 1.024\ \mathrm{MHz}
$$

Source: `model/README.md` Setup ("OSR 512 is the first-order SQNR equation for 10.55 bit, rounded up to a power of 2 and times 4 margin"), the same lines in `model/dither_deadzone.py`.

The margin of 4 buys $30\log_{10}4 = 18.1$ dB. At OSR 512 the formula gives, with the full-scale sine $V_\mathrm{sig} = V_\mathrm{REF}/\sqrt{2} = 0.530$ V rms:

$$
\mathrm{SQNR}(512) = 83.89\ \mathrm{dB}, \qquad v_\mathrm{q} = V_\mathrm{sig}\,10^{-\mathrm{SQNR}/20} = 33.9\ \mu\mathrm{V_{rms}}
$$

$$
\mathrm{SNR} = 10\log_{10}\frac{V_\mathrm{sig}^2}{v_\mathrm{q}^2 + v_\mathrm{th}^2} = 65.22\ \mathrm{dB}
$$

So with the full budget $v_\mathrm{th}$ spent, the SNR lands 0.06 dB under $\mathrm{SQNR_{spec}}$. With $v_\mathrm{q} = v_\mathrm{th}$ (no margin) it would be 62.27 dB (derived).

## 2. The loop

### Block diagram as equations

First-order CIFB (cascade of integrators with feedback), one delaying integrator, the quantizer reads the state, dither $d$ added at the quantizer:

$$
x[n+1] = x[n] + b_1\,u[n] - a_1\,v[n]
$$

$$
y[n] = c_1\,x[n]
$$

$$
v[n] = \mathrm{sgn}\big(y[n] + d[n]\big), \qquad \mathrm{sgn}(0) = +1
$$

This is the update of `run_loop` in `model/dsm_system.py` (`v[k] = sign(x[k] + qd[k]), x[k+1] = p*x[k] + a1*(ue[k] - fb[k])`, with $p = 1$ for the ideal integrator) and of `run_loop` in `model/dither_deadzone.py`.

### NTF synthesis and coefficients

The NTF is synthesised for order 1, OSR 512 and an out-of-band gain $H_\infty = 1.2$ (`synthesizeNTF(1, 512, H_inf=1.2)`). A first-order NTF with its zero at $z = 1$ and a real pole $z_\mathrm{p}$ has its largest gain at $z = -1$:

$$
\mathrm{NTF}(z) = \frac{z-1}{z-z_\mathrm{p}}, \qquad \lvert\mathrm{NTF}(-1)\rvert = \frac{2}{1+z_\mathrm{p}} = H_\infty \quad\Rightarrow\quad z_\mathrm{p} = \frac{2}{H_\infty} - 1 = \frac{2}{3}
$$

The CIFB realisation (`realizeNTF(ntf, 'CIFB')`, only $b_1$ kept) gives

$$
a_1 = 1 - z_\mathrm{p} = 2 - \frac{2}{H_\infty} = \frac{1}{3}, \qquad b_1 = a_1 = \frac{1}{3}, \qquad c_1 = 1
$$

$b_1 = a_1$ sets $\mathrm{STF}(1) = 1$. Source: `model/README.md` Setup ("a1 = b1 = 1/3"), `model/dsm_system.py` (`a1 = 2 - 2 / a.hinf`).

ABCD matrix, rows $[x[n+1],\ y[n]]$, columns $[x[n],\ u[n],\ v[n]]$:

$$
\mathrm{ABCD} = \begin{bmatrix} 1 & b_1 & -a_1 \\ c_1 & 0 & 0 \end{bmatrix} = \begin{bmatrix} 1 & 1/3 & -1/3 \\ 1 & 0 & 0 \end{bmatrix}
$$

Source: the `ABCD` assembled in `model/dither_deadzone.py` and `sizing/size_ota_fcasc2.py`.

### NTF and STF

With the linear quantizer model $v = k\,y + e$:

$$
\mathrm{NTF}_k(z) = \frac{z-1}{z-1+k a_1 c_1}, \qquad \mathrm{STF}_k(z) = \frac{k\,b_1 c_1}{z-1+k a_1 c_1}
$$

With $k = 1$, the convention of the synthesis:

$$
\mathrm{NTF}(z) = \frac{z-1}{z-\frac{2}{3}} = \frac{1-z^{-1}}{1-\frac{2}{3}z^{-1}}, \qquad \mathrm{STF}(z) = \frac{\frac{1}{3}}{z-\frac{2}{3}} = \frac{\frac{1}{3}z^{-1}}{1-\frac{2}{3}z^{-1}}
$$

At $f_\mathrm{b}$ ($\omega = \pi/\mathrm{OSR}$): $\lvert\mathrm{NTF}\rvert = 1.84\cdot10^{-2}$ ($-34.7$ dB), $\lvert\mathrm{STF}\rvert = 0.99989$, STF phase $-18.4$ mrad (derived).

### Quantizer gain normalisation

A 1-bit quantizer has no defined gain: $v$ depends only on the sign of $y + d$, so any positive scale of $x$ and $d$ gives the same bits. With $x' = x/a_1$ and $d' = d/a_1$ the loop becomes

$$
x'[n+1] = x'[n] + u[n] - v[n], \qquad v[n] = \mathrm{sgn}\big(x'[n] + d'[n]\big)
$$

which is the $a_1 = 1$ loop. So the bit stream is the one of the gain-normalised model with $k a_1 = 1$, $k = 3$:

$$
\mathrm{NTF}(z) = 1 - z^{-1}, \qquad \mathrm{STF}(z) = z^{-1}
$$

This is the NTF that the SQNR equation of section 1 assumes. $H_\infty$ only scales the state: the integrator swing goes with $a_1$, which is why 1.2 instead of the textbook 2 ($a_1 = 1$) fits the OTA output range on 1.5 V (section 4). The scaling holds with the leak $p$ of section 4 as well, since $p$ is not touched. In the normalised loop the dither is $d' = d/a_1$, so the nominal $A = 75$ mV ($d/V_\mathrm{REF} = 0.1$) is 0.3 of the DAC level.

## 3. In-band quantization noise and SQNR

Linear model, $e$ white and uniform with variance $\sigma_e^2 = \Delta^2/12$, normalised NTF $1 - z^{-1}$, $W = \pi/\mathrm{OSR}$:

$$
N_\mathrm{q} = \frac{\sigma_e^2}{\pi}\int_0^{W}\left\lvert 1 - e^{-j\omega}\right\rvert^2 d\omega = \frac{\sigma_e^2}{\pi}\left(2W - 2\sin W\right) \approx \sigma_e^2\,\frac{\pi^2}{3\,\mathrm{OSR}^3}
$$

$$
\mathrm{SQNR} = 10\log_{10}\frac{1/2}{N_\mathrm{q}}
$$

with the full-scale sine power $1/2$ in units of $V_\mathrm{REF}^2$.

| Step $\Delta$ | $\sigma_e^2$ | $N_\mathrm{q}$ | in-band rms | SQNR at 0 dBFS | at $-6$ dBFS |
| --- | --- | --- | --- | --- | --- |
| $V_\mathrm{FS}/2^N = 1$ (the equation of section 1) | 1/12 | $2.04\cdot10^{-9}$ | 33.9 uV | 83.89 dB | 77.87 dB |
| level spacing 2 of $v = \pm 1$ | 1/3 | $8.17\cdot10^{-9}$ | 67.8 uV | 77.87 dB | 71.85 dB |

The two rows bracket the linear estimate, since a 1-bit quantizer has no defined step. The first row is the one the design uses. `doc/dsm2_README.md` (In-band SNDR) quotes 78.0 dB ideal at $-6$ dBFS against a floor-fit SQNR of 74.4 dB (sim, schematic). An ideal loop of `model/dsm_system.py` at $-6$ dBFS, $2^{20}$ samples, with `--dither 13e-6` (the in-band figure of the bench), gives 74.5 dB (model, see Checks), and `doc/dsm2_README.md` gives 74.9 +- 1.3 dB for an ideal first-order loop without dither fed with the input of its bench. A first-order loop is tonal, so the simulated SQNR sits 3 to 4 dB under the first row.

With the integrator leak $p$ of section 4 the normalised NTF is $(z-p)/(z-p+1)$ and

$$
N_\mathrm{q}(p) \approx \sigma_e^2\left[\frac{(1-p)^2}{\mathrm{OSR}} + p\,\frac{\pi^2}{3\,\mathrm{OSR}^3}\right]
$$

The SQNR loss against $p = 1$ does not depend on $\sigma_e^2$:

| Integrator gain $1/(1-p)$ | $1-p$ | SQNR loss (derived) |
| --- | --- | --- |
| 50 dB, the system-level minimum | $3.16\cdot10^{-3}$ | 2.51 dB |
| 69.3 dB, leak bench, Magic mode 3 view (sim) | $3.41\cdot10^{-4}$ | 0.04 dB |
| 71.3 dB, leak bench, schematic (sim) | $2.72\cdot10^{-4}$ | 0.02 dB |

Leak values: `doc/sc_int2_README.md` (Leak bench).

## 4. Switched-capacitor realisation

### Coefficient from the capacitor ratio

`sc_int2` is fully differential. Each sampling capacitor $C_1$ takes `vi` in one phase and the DAC level in the other, the two branches swap roles every phase (`doc/sc_int2_README.md`, Structure), and both deliver their charge into $C_2$ in phase 2. With the DAC at $v_\mathrm{cm} \pm V_\mathrm{REF}$ the charge balance per clock is

$$
\Delta v_\mathrm{od} = \frac{2C_1}{C_2}\left(v_\mathrm{i} - v_\mathrm{DAC}\right) = \frac{2C_1}{C_2}\,V_\mathrm{REF}\,(u - v)
$$

$$
a_1 = b_1 = \frac{2C_1}{C_2} = \frac{1}{3}, \qquad C_2 = \frac{2C_1}{a_1} = 6\,C_1
$$

$b_1 = a_1$ holds by construction because the same $C_1$ samples the input and the DAC. $c_1 = 1$ because the quantizer reads $v_\mathrm{od}$ directly.

| Symbol | Value | Source |
| --- | --- | --- |
| $C_1$ | 64 fF, 2 units of 32 fF (estimated real), 87.95 fF in the schematic (model value) | `doc/sc_int2_README.md` Capacitors |
| $C_2$ | 384 fF, 12 units, 527.7 fF model | same |
| $C_1/C_2$ | 1/6 exactly by unit count | same |

### kT/C and the capacitor floor

$C_1$ from the budget, putting the sampled noise at $v_\mathrm{th}$:

$$
C_1 \ge \frac{kT}{\mathrm{OSR}\,v_\mathrm{th}^2} = 0.097\ \mathrm{fF} \quad (T = 300\ \mathrm{K})
$$

kT/C is no sizing argument here. The floor is 10 fF, and the 64 fF are set by leakage and droop (`sizing/size_sc_int2.ipynb`, capacitors cell). Each capacitor takes $kT/C_1$ per phase, but both carry the input with the signal gain $2C_1/C_2$ against $C_1/C_2$ per capacitor, so the input sees $kT/C_1$ per sample, not $2kT/C_1$ (`doc/sc_int2_README.md`, Noise with Ideal Noisy Switches):

$$
v_\mathrm{n,kTC} = \sqrt{\frac{kT}{C_1\,\mathrm{OSR}}} = 11.24\ \mu\mathrm{V_{rms}}\ \text{in band}, \quad 355\ \mathrm{nV}/\sqrt{\mathrm{Hz}}
$$

With the 87.95 fF model value it is 9.59 uV. pnoise gives 10.61 uV for the switches with the real OTA and 11.25 uV with an ideal opamp (sim, same README).

### Swing

For a DC input $u$ the state of the first-order loop stays inside

$$
\lvert x\rvert \le a_1 (1 + \lvert u\rvert), \qquad \lvert v_\mathrm{od}\rvert \le a_1 (1 + \lvert u\rvert)\,V_\mathrm{REF}
$$

At $-0.5$ dBFS ($u = 0.944$) that is 0.486 V peak differential, the ideal loop with the noise budget gives 0.491 V (model), 0.983 V peak to peak against the 1.604 V output range of `ota_fcasc2` (model), 4.3 dB margin. The largest step per clock is $2 a_1 V_\mathrm{REF} = 0.5$ V differential, 0.25 V per side. Source: `sizing/size_sc_int2.ipynb`, swing cell. The dither adds up to its amplitude $A$ (section 5) to the peak.

### Integrator leak from finite OTA gain

Charge balance on the virtual ground with OTA gain $A_\mathrm{OTA}$ and input capacitance $C_\mathrm{p}$, fraction of the old state kept per clock (`sizing/size_sc_int2.ipynb`, leakage cell):

$$
p = \frac{C_2(1+A_\mathrm{OTA}) + C_\mathrm{p}}{C_1 + C_2(1+A_\mathrm{OTA}) + C_\mathrm{p}}, \qquad 1 - p \approx \frac{C_1}{C_2\,A_\mathrm{OTA}}
$$

$C_\mathrm{p}$ drops out to first order. The integrator DC gain is $A_\mathrm{0,int} = 1/(1-p) \approx (C_2/C_1)\,A_\mathrm{OTA}$.

The system-level design maps the OTA gain through the feedback factor instead, $A_\mathrm{0,int} = \beta A_\mathrm{OTA}$ with $\beta = C_2/(C_1 + C_2 + C_\mathrm{gg1})$, and asks for $A_\mathrm{0,int} \ge 50$ dB (`sizing/size_ota_fcasc2.py`, from a leaky-integrator sweep that is not in this repo):

$$
A_\mathrm{OTA} \ge \frac{A_\mathrm{0,int}}{\beta} = 51.7\ \mathrm{dB}\ (\beta = 0.820), \quad 52.1\ \mathrm{dB}\ (\beta = 0.785)
$$

(`doc/ota_fcasc2_README.md`, Sizing). The $\beta$ map is the conservative one: at $A_\mathrm{OTA}$ = 58.8 dB it gives 56.7 dB of integrator gain ($\beta$ = 0.785), the charge balance 74.4 dB (derived). `model/dsm_system.py` has both, `--leak-map beta` and `--leak-map c1c2`.

| Case | $1-p$ | $A_\mathrm{0,int}$ | Source |
| --- | --- | --- | --- |
| charge balance, $A_\mathrm{OTA}$ = 55.3 dB (unit-device point, model) | $2.86\cdot10^{-4}$ | 70.9 dB | `sizing/size_sc_int2.ipynb` |
| charge balance, $A_\mathrm{OTA}$ = 58.8 dB (sim) | $1.91\cdot10^{-4}$ | 74.4 dB | same |
| $(C_1/C_2)/A_\mathrm{OTA}$ at 58.29 dB in place (sim) | $2.03\cdot10^{-4}$ | 73.9 dB | `doc/sc_int2_README.md` Leak bench |
| leak bench fit, `cap_cmomf` schematic, earlier layout (sim) | $2.72\cdot10^{-4}$ | 71.3 dB | same |
| leak bench fit, `cap_cmomf` Magic mode 3, earlier layout (sim) | $3.41\cdot10^{-4}$ | 69.3 dB | same |
| leak bench fit, final layout, schematic (sim) | $2.91\cdot10^{-4}$ | 70.7 dB | same |
| leak bench fit, final layout, Magic mode 3 (sim) | $2.73\cdot10^{-4}$ | 71.3 dB | same |

The final layout, the one taped out, reads $2.91\cdot10^{-4}$ (schematic) and $2.73\cdot10^{-4}$ (Magic mode 3), 1.45 and 1.34 times its prediction, so the $2.72\cdot10^{-4}$ used on this page is within 1 % of the final extracted value. On the earlier layout the fitted leak is 1.34 (schematic) and 1.68 (mode 3) times the `(C1/C2)/A` prediction of the same table. That README leaves the 1.34 of the schematic open (its 1 pS anchors across the plates are worth at most $3\cdot10^{-5}$ per cycle) and reads the extra 1.25 of mode 3 over the schematic as slower settling from the extracted wiring and plate capacitance (inference there).

Effect on the loop: the 1 in the ABCD matrix becomes $p$, $x[n+1] = p\,x[n] + a_1(u[n] - v[n])$, and

$$
\mathrm{NTF}_k(z) = \frac{z-p}{z-p+k a_1}, \qquad \mathrm{STF}_k(z) = \frac{k a_1}{z-p+k a_1}
$$

The NTF zero moves from $z = 1$ to $z = p$, so the noise floor no longer goes to zero at DC. Normalised ($k a_1 = 1$), $\lvert\mathrm{NTF}(1)\rvert = (1-p)/(2-p) \approx 1-p$, $-71.3$ dB at $1-p = 2.72\cdot10^{-4}$. The in-band cost is the table of section 3, the DC cost is the dead zone of section 5.

### Static gain error

Finite OTA gain also leaves a static error per charge transfer, the second gain criterion of `ota_fcasc2`:

$$
\epsilon_\mathrm{s} = \frac{1}{1 + \beta A_\mathrm{OTA}} = 0.32\ \% \quad (A_\mathrm{OTA} = 51.73\ \mathrm{dB},\ \beta = 0.820)
$$

which is the CACE limit `err_d` $\le$ 0.32 % of `doc/ota_fcasc2_README.md`. It scales $a_1$ and $b_1$ alike, which the 1-bit loop absorbs into the state scale (section 2), so it does not change the bits.

The DC gain of the leaky loop follows from the STF with the normalised quantizer gain $k a_1 = 1$:

$$
\bar{v} = \mathrm{STF}(1)\,u = \frac{u}{2-p} \approx \big(1 - (1-p)\big)\,u
$$

a gain error of $-(1-p) = -2.7\cdot10^{-4}$ at 71.3 dB. The loop of `model/dsm_system.py` gives $-2.70\cdot10^{-4}$ to $-2.77\cdot10^{-4}$ at $1-p = 2.72\cdot10^{-4}$ for four inputs away from low-order rationals ($u$ = 0.1414, 0.3142, $-0.4330$, 0.6343), within 2 % for these four. The leaky loop locks onto rational inputs over ranges that scale with $1-p$, so a single input inside or near such a lock range deviates, $u = -0.2$ gives $-5.9\cdot10^{-5}$ at the design leak. At $1-p = 10^{-2}$ the lock ranges are 37 times wider and single inputs scatter by 10 to 20 %, the four give $-8.6\cdot10^{-3}$ to $-1.02\cdot10^{-2}$ (0.1414 sits 0.0015 from 1/7), and only their mean, $-9.7\cdot10^{-3}$, is compared (see Checks). The $k = 1$ form $a_1/(1-p+a_1)$ would give $(1-p)/a_1$, three times more, which the simulation does not support. Both are far inside the "gain 1.00 within 0.01" of `doc/measurement_plan.md`.

### Settling

The output moves in phase 2 only, $T_\mathrm{s}/2 = 488.3$ ns, split equally into slewing and linear settling, $t_\mathrm{slew} = t_\mathrm{lin} = 244.1$ ns. The dynamic error must stay under the spec resolution:

$$
\epsilon_\mathrm{d} = 10^{-\mathrm{SQNR_{spec}}/20} = 5.45\cdot10^{-4}, \qquad n = \left\lceil \ln\frac{1}{\epsilon_\mathrm{d}} \right\rceil = \lceil 7.52 \rceil = 8
$$

$$
\tau \le \frac{t_\mathrm{lin}}{n} = 30.52\ \mathrm{ns}, \qquad \omega_\mathrm{ug} \ge \frac{1}{\tau} = 32.8\ \mathrm{Mrad/s}, \qquad f_\mathrm{ug} \ge 5.22\ \mathrm{MHz}
$$

`sizing/size_ota_fcasc2.py` rounds instead of ceiling, which also gives 8.

Closed-loop time constant of the OTA in phase 2, fanout $\mathrm{FO} = 2$:

$$
\beta = \frac{C_2}{C_1 + C_2 + C_\mathrm{gg1}}, \qquad C_\mathrm{Ltot} = \mathrm{FO}\cdot C_1 + C_2(1-\beta), \qquad \tau = \frac{C_\mathrm{Ltot}}{\beta\,g_\mathrm{m1}}
$$

| Capacitors | $\beta$ | $C_\mathrm{Ltot}$ | $\tau$ | Source |
| --- | --- | --- | --- | --- |
| real, 64 / 384 fF | 0.7861 | 210 fF | 17.65 ns | `sizing/size_sc_int2.ipynb`, settling cell |
| model, 87.95 / 527.7 fF | 0.8042 | 279 fF | 22.92 ns | same |

with $g_\mathrm{m1}$ = 15.15 uS and $C_\mathrm{gg1}$ = 40.5 fF of the unit-device point of `sizing/size_ota_fcasc2.py` (model). The settling testbench measures $\beta$ = 0.785 and $\tau$ = 16.2 ns (sim, `doc/ota_fcasc2_README.md`).

### Slew

The largest output step per side is $a_1 V_\mathrm{REF} = 0.25$ V. The folded cascode puts at most $I_\mathrm{D1}$, half the tail current, into one output:

$$
\mathrm{SR} = \frac{I_\mathrm{D1}}{C_\mathrm{Ltot}}, \qquad I_\mathrm{D1} > \frac{C_\mathrm{Ltot}}{t_\mathrm{slew}}\cdot\frac{2C_1}{C_2}\cdot V_\mathrm{REF}
$$

`sizing/size_ota_fcasc2.py` evaluates the bound with $C_\mathrm{Ltot} = C_1 + C_1 C_2/(C_1+C_2) = 118.9$ fF, which gives 121.7 nA. With the $\mathrm{FO} = 2$ load of the $\tau$ equation, $2C_1 + C_1 C_2/(C_1+C_2) = 182.9$ fF, it is 187.2 nA (derived). The drawn $I_\mathrm{D1}$ is 600 nA (`doc/ota_fcasc2_README.md`).

The OTA slews until the remaining step is small enough to settle linearly, then settles with $\tau$:

$$
v_\mathrm{lin} = \frac{I_\mathrm{D1}\,\tau}{C_\mathrm{Ltot}}, \qquad t_\mathrm{sl} = \left(a_1 V_\mathrm{REF} - v_\mathrm{lin}\right)\frac{C_\mathrm{Ltot}}{I_\mathrm{D1}}, \qquad \epsilon = \frac{v_\mathrm{lin}}{a_1 V_\mathrm{REF}}\,e^{-(T_\mathrm{s}/2 - t_\mathrm{sl})/\tau}
$$

| Capacitors | SR | $v_\mathrm{lin}$ | $t_\mathrm{sl}$ | $\epsilon$ |
| --- | --- | --- | --- | --- |
| real | 2.86 V/us | 0.050 V | 70 ns | $1.0\cdot10^{-11}$ |
| model | 2.15 V/us | 0.049 V | 93 ns | $6.5\cdot10^{-9}$ |

Both are far under $\epsilon_\mathrm{d}$. Source: `sizing/size_sc_int2.ipynb`, settling cell.

## 5. Dither

### LFSR

17-bit XNOR Fibonacci register, taps 17 and 14, reset to all zeros (`doc/quantizer2_README.md`, `model/dither_deadzone.py`):

$$
b[k] = \overline{b[k-17] \oplus b[k-14]}
$$

Three new bits per clock by a leap-forward update form the code

$$
c[n] = b[3n] + 2\,b[3n+1] + 4\,b[3n+2], \qquad c \in \{0, \dots, 7\}
$$

The bit sequence has period $2^{17}-1 = 131071$, a prime, so $\gcd(3, 131071) = 1$ and the code sequence also repeats after 131071 clocks. Over one period codes 0 to 6 appear 16384 times and code 7 16383 times (derived, the all-ones state is the excluded one of an XNOR register). A 16-bit register would repeat after $65535/3 = 21845$ clocks.

### Levels and amplitude

The three auxiliary pairs of `quantizer2`, weights 1 : 2 : 4, each add $\pm A/7$ times their weight, so the comparator decides on $v_\mathrm{od} + d$ with

$$
d[n] = A\,\frac{2c[n] - 7}{7} \in \left\{\pm\frac{A}{7}, \pm\frac{3A}{7}, \pm\frac{5A}{7}, \pm A\right\}, \qquad \overline{d} = 0, \qquad d_\mathrm{rms} = A\sqrt{3/7} = 0.655\,A
$$

$A$ is in volts of $v_\mathrm{od}$. In the loop equations $d$ enters as $d/V_\mathrm{REF}$.

| `di_dith_amp` | Ladder tap | Share of `s[0]` | $A$ nominal | $A$ at tt (sim) |
| --- | --- | --- | --- | --- |
| 00 (`s[0]`) | 3 steps | 100 % | 75 mV | 76.5 mV |
| 01 (`s[1]`) | 2 steps | 67 % | 50 mV | 50.1 mV (65.5 %) |
| 10 (`s[2]`) | 4 steps | 133 % | 100 mV | 104.4 mV (136.5 %) |
| 11 (`s[3]`) | 1 step | 33 % | 25 mV | 23.3 mV (30.5 %) |

Sources: `doc/dsm2_README.md` Ports (the percentages), `doc/quantizer2_README.md` Dither (sim, 67 to 85 mV window of the system model, all corners of `s[0]` inside it), `sizing/size_quantizer2.ipynb` (75 mV nominal, 31.6 mV per ladder step).

### Cost in shaped noise

The dither enters where $e$ does, so the NTF shapes it like quantization error. In the normalised loop of section 2 ($d' = d/(a_1 V_\mathrm{REF})$, $\sigma_e^2 = 1/3$ for the level spacing 2):

$$
\frac{\sigma_{d'}^2}{\sigma_e^2} = \frac{9}{7}\left(\frac{A}{a_1 V_\mathrm{REF}}\right)^2 = 0.116 \quad (A = 75\ \mathrm{mV}), \qquad 10\log_{10}(1 + 0.116) = 0.48\ \mathrm{dB}
$$

The same number in volts: dither variance $2.41\cdot10^{-3}\ \mathrm{V^2}$ against $(2 a_1 V_\mathrm{REF})^2/12 = 0.0208\ \mathrm{V^2}$ on the integrator output scale.

### The dead zone it is there to break

With the leak $p < 1$ and a DC input near zero, the loop locks into the period-2 limit cycle $v = +1, -1, +1, \dots$ From $x[n+1] = p\,x[n] + a_1(u - v[n])$ the two states of that cycle are

$$
x_+ = a_1\left(\frac{u}{1-p} + \frac{1}{1+p}\right), \qquad x_- = a_1\left(\frac{u}{1-p} - \frac{1}{1+p}\right)
$$

($x_+$ before the $+1$ decision). The cycle exists while $x_+ \ge 0 > x_-$, and its mean output is 0 whatever $u$ is:

$$
\lvert u\rvert < \frac{1-p}{1+p}, \qquad W_\mathrm{dz} = 2\,\frac{1-p}{1+p}\,V_\mathrm{REF} \approx (1-p)\,V_\mathrm{REF} \approx \frac{V_\mathrm{REF}}{A_\mathrm{0,int}}
$$

The width does not depend on $a_1$. The dither can only break the cycle where it can flip a decision, that is where one of the states is smaller than the dither peak. The cycle survives where $\lvert x_\pm\rvert > A/V_\mathrm{REF}$:

$$
\lvert u\rvert < (1-p)\left(\frac{1}{1+p} - \frac{A}{a_1 V_\mathrm{REF}}\right), \qquad W_\mathrm{dz,d} = 2(1-p)\left(\frac{1}{1+p} - \frac{A}{a_1 V_\mathrm{REF}}\right)V_\mathrm{REF}
$$

and the period-2 zone is gone for $A \ge a_1 V_\mathrm{REF}/(1+p) \approx 125$ mV. The 75 mV nominal leaves $(0.5 - 0.3)/0.5 = 0.4$ of the undithered width.

| $A$ | $W_\mathrm{dz}$, leak $2.72\cdot10^{-4}$ (schematic) | leak $3.41\cdot10^{-4}$ (mode 3) | `doc/measurement_plan.md` C0 to C4, leak $2.72\cdot10^{-4}$ (model, with noise) |
| --- | --- | --- | --- |
| off | 0.204 mV | 0.256 mV | 0.12 mV |
| 76.5 mV (00) | 0.079 mV | 0.099 mV | 0.05 mV |
| 50.1 mV (01) | 0.122 mV | 0.153 mV | 0.08 mV |
| 104.4 mV (10) | 0.034 mV | 0.042 mV | 0.03 mV |
| 23.3 mV (11) | 0.166 mV | 0.208 mV | 0.11 mV |

The two closed-form columns match a noiseless run of the loop of `model/dsm_system.py` with the LFSR codes within 0.003 mV (see Checks). The measurement plan values come from `model/dither_deadzone.py` with 0.1 mVrms input noise and a 0.03 LSB flatness rule, so they are narrower, the noise breaks the cycle as well, and the order of the five cases is the same. At the 50 dB system-level minimum the undithered width is 2.38 mV. The 4.3 LSB that `sizing/size_ota_fcasc2.py` quotes for 50 dB uses another rule, the span with $\lvert\mathrm{out}\rvert < 0.5$ LSB, with 0.1 mVrms noise, and is not comparable. Dead zones around other rational inputs (`--dc-rational` of `model/dsm_system.py`) are not covered by these equations.

Scope: noiseless loop, offset-free comparator with $\mathrm{sgn}(0) = +1$. A comparator offset $V_\mathrm{os}$ of $v_\mathrm{od}$ moves the zone centre by $(1-p)\,V_\mathrm{os}/a_1$, about 20 uV at the 25 mV (3 sigma) of `sizing/size_quantizer2.ipynb`, and leaves the width. At the zone edge the mean output steps away from 0, it does not ramp, so a flatness rule measures a different width.

### Idle tones

Outside the dead zone the ideal loop is a rotation. In the normalised loop of section 2 the state advances by $1+u$ modulo 2 every clock, so $x$ is a sawtooth, and its even harmonics alias to multiples of

$$
f_\mathrm{tone} = f_\mathrm{s}\,\lvert\bar{v}\rvert
$$

After the $1 - z^{-1}$ from $x$ to $v$ each of these spurs has the same amplitude, $2\lvert\bar{v}\rvert$ of full scale. The first one is in band for $\lvert v_\mathrm{i} - v_\mathrm{cm}\rvert < f_\mathrm{b} V_\mathrm{REF}/f_\mathrm{s} = 0.73$ mV. The loop of `model/dsm_system.py` confirms both at 0.25 to 1.125 mV (see Checks): the spur at $f_\mathrm{tone}$ and the largest spur below 20 kHz read $2\lvert\bar{v}\rvert$ within 0.01 dB, $-63.5$ dBFS at 0.25 mV, $-54.0$ dBFS at 0.75 mV, $-50.5$ dBFS at 1.125 mV, and each largest spur sits at a multiple of $f_\mathrm{tone}$. With the leak the pattern changes, which this page does not cover.

`doc/measurement_plan.md` (3.6) states the relation as "fs times the mean divided by 2", in band below about 1.5 mV. That is a factor 2 off, and its own table fits $f_\mathrm{tone} = f_\mathrm{s}\lvert\bar{v}\rvert$ with $2\lvert\bar{v}\rvert$: $-64.3$ dBFS at 0.25 mV against $-63.5$, and $-120.8$ dBFS at 1.0 mV, where the first spur has left the band. The same section gives the dither 7 to 9 dB less spur at 0.25 and 0.5 mV (model).

## 6. Decimation in the models

The models read the stream with a $\mathrm{sinc}^{L+1} = \mathrm{sinc}^2$ filter decimating by $R = \mathrm{OSR} = 512$ (`sinc2_stream` and `sinc2_weights` in `model/dsm_system.py`, `ds.sinc_decimate(v, 2, 512)` in `model/dither_deadzone.py`):

$$
H(z) = \left(\frac{1}{R}\,\frac{1-z^{-R}}{1-z^{-1}}\right)^2, \qquad \lvert H(f)\rvert = \left(\frac{\sin(\pi f R/f_\mathrm{s})}{R\,\sin(\pi f/f_\mathrm{s})}\right)^2
$$

$$
w[m] = \sum_{j=0}^{2R-2} h[j]\, v[(m+1)R - 1 - j], \qquad h = \frac{\mathbf{1}_R \ast \mathbf{1}_R}{R^2}, \qquad \sum_j h[j] = 1
$$

The output rate is $f_\mathrm{s}/R = 2$ kHz. $H$ has zeros at multiples of 2 kHz and at $f_\mathrm{s}/2$ for even $R$, which is where `--chop` moves the OTA error. The droop at $f_\mathrm{b}$ is $-7.84$ dB, which does not matter for DC readings.

One DC reading drops the first $L+1 = 2$ outputs (the filter fill) and averages the next $N_\mathrm{avg}$:

$$
\bar{w} = \frac{1}{N_\mathrm{avg}}\sum_{m=2}^{N_\mathrm{avg}+1} w[m] = \sum_n g[n]\,v[n], \qquad \text{record } (N_\mathrm{avg} + 2)\,R \text{ clocks}
$$

$$
\text{code in LSB} = \bar{w}\,\frac{V_\mathrm{REF}}{V_\mathrm{LSB}} = 750\,\bar{w}
$$

$N_\mathrm{avg}$ = 16 (`--dc-navg`, and the 0.25 LSB sweep of `model/dither_deadzone.py`, 9216 clocks), 64 in its fine sweep (33792 clocks). The ripple report of `--dc-sweep` groups 16 outputs into one reading (`READ_AVG`). The plain stream mean of `doc/measurement_plan.md` is `2 mean(do_q) - 1` against the expected `(vi - vcm) / 0.75 V`.

The PSD of `model/psd_bitstream.py` (`spectrum`, `tone_dbfs`) and `model/dsm_system.py` uses a Hann window $w_\mathrm{H}$, scaled so a full-scale sine reads 0 dBFS:

$$
S[k] = \frac{\sum_n v[n]\,w_\mathrm{H}[n]\,e^{-j2\pi kn/N}}{\tfrac{1}{2}\sum_n w_\mathrm{H}[n]}, \qquad \mathrm{NBW} = \frac{\sum w_\mathrm{H}^2}{\left(\sum w_\mathrm{H}\right)^2}\,f_\mathrm{s} = 1.5\,\frac{f_\mathrm{s}}{N}
$$

The tone is the sum of 5 bins over 1.5 (the Hann noise bandwidth in bins), the noise is every other bin in $(0, f_\mathrm{b}]$. `model/psd_bitstream.py` also removes the stream mean and drops the two DC skirt bins, `model/dsm_system.py` does neither.

## 7. Thermal noise budget as the models apply it

The budget is $v_\mathrm{th} = 288.68$ uV in band (section 1). The models add circuit noise as white noise at the input. White noise puts $1/\mathrm{OSR}$ of its power below $f_\mathrm{b}$, so an in-band figure $v_\mathrm{band}$ becomes a per-sample deviation

$$
\sigma_u = \frac{v_\mathrm{band}}{V_\mathrm{REF}}\sqrt{\mathrm{OSR}}
$$

which is $\sigma_u = 8.71\cdot10^{-3}$, or 6.53 mV per sample in volts, for 288.68 uV (`add_noise` in `model/dsm_system.py`, and its `--dither` option).

`model/dsm_system.py` sums three terms, each quoted in band:

$$
v_\mathrm{white} = \sqrt{v_\mathrm{kTC}^2 + v_\mathrm{fold}^2}, \qquad v_\mathrm{kTC} = \sqrt{\frac{2kT}{\mathrm{OSR}\,C_1}}
$$

plus the OTA term $v_\mathrm{OTA}$, shaped to a measured spectrum when `--ota` is given and scaled to its in-band value. Its defaults are $v_\mathrm{kTC}$ = 15.90 uV, $v_\mathrm{fold}$ = 130.30 uV and $v_\mathrm{OTA}$ = 892.95 uV, 902.5 uV in total, 9.9 dB over the budget (derived). `doc/sc_int2_README.md` (What Is Missing) records that this script still takes $2kT/C_1$ and the old closed-loop OTA numbers as defaults.

The referral that holds, from the charge balance in `doc/sc_int2_README.md` (Which referral holds): the switches give $kT/C_1$ per sample (section 4), and a differential OTA input noise $v_\mathrm{n}$ reaches $v_\mathrm{od}$ with $C_1/C_2$ and the input with $2C_1/C_2$, so it refers to the input with 1/2:

$$
v_\mathrm{in} = \sqrt{\frac{kT}{C_1\,\mathrm{OSR}} + \left(\frac{v_\mathrm{n,OTA}}{2}\right)^2 + v_\mathrm{fold}^2} = \sqrt{11.24^2 + 25.63^2 + 8.38^2}\ \mu\mathrm{V} = 29.21\ \mu\mathrm{V_{rms}}
$$

with $v_\mathrm{n,OTA}$ = 51.26 uV, the open-loop differential input noise of `ota_fcasc2` over 1 Hz to 1 kHz that `doc/sc_int2_README.md` uses in its referral table (sim). `doc/ota_fcasc2_README.md` gives 50.32 uV for the current schematic (40.5 / 50.3 / 63.0 uV over 45 PVT points), 25.2 uV referred, which moves the total to 28.8 uV. pnoise of `sc_int2` gives 28.64 uV at tt (ideal caps, sim), 35.34 uV at the worst of 45 operating points (ss, 125 C, 1.45 V), 18.2 dB under the budget. With 28.64 uV and $v_\mathrm{q}$ = 33.9 uV the full-scale SNR estimate is 81.55 dB (derived, linear model). The budget calculation itself, `noise_budget.py`, and `doc/noise-budget.md` are in the designer's tree, not in this repo.

## Checks

`model/check_equations.py` recomputes every closed-form value on this page from its equation and compares it with the value the repo files state. It needs numpy only, imports `model/dsm_system.py` for the loop and the decimator, prints the comparison table and exits 1 on a mismatch (about 10 minutes, most of it in the dead zone runs). Run on 2026-11-09 in the sign-off image of `scripts/image.env`: 96 comparisons, 0 failed. The 78.0 dB of `doc/dsm2_README.md` is 0.13 dB from the formula (row 3) and passes because that row has a 0.16 dB tolerance, the ideal-loop SQNR is compared with the 74.9 +- 1.3 dB spread of that README, every other row is within rounding of its reference.

| Group | Recomputed | Compared with | Match |
| --- | --- | --- | --- |
| 1 | bit mean 0.41379 and 0.38710 at 0.3 V for 1.45 and 1.55 V | `doc/dsm2_README.md` Corners | yes |
| 1 | ENOB 10.5507 bit, $\mathrm{SQNR_{spec}}$ 65.275 dB, $\mathrm{OSR_{min}}$ 122.72, OSR 512, $f_\mathrm{s}$ 1.024 MHz, $v_\mathrm{th}$ 288.675 uV | `model/README.md`, `model/dsm_system.py`, `sizing/size_sc_int2.ipynb` | yes |
| 2 | $a_1$ as `model/dsm_system.py` main computes it (read from its source) equals $1 - z_\mathrm{p} = 1/3$, max of $\lvert\mathrm{NTF}\rvert$ on the unit circle 1.2, NTF and STF from the ABCD matrix equal the closed forms to $10^{-15}$, $\mathrm{STF}(1) = 1$ | `model/dsm_system.py`, `model/README.md`, derived | yes |
| 2 | bit stream of $a_1 = 1/3$ against $a_1 = 1$ with $d/a_1$, leak and dither, $2^{16}$ clocks: 0 bits differ | derived | yes |
| 3 | SQNR 83.888 dB from the exact integral against 83.886 dB from the formula, 77.87 dB at $-6$ dBFS against the 78.0 dB of `doc/dsm2_README.md` | formula, README | 0.13 dB, rounding not traced |
| 3 | ideal loop at $-6$ dBFS, $2^{20}$ samples, 13 uV in-band dither: 74.47 dB. `model/dsm_system.py --noiseless --dither 13e-6 --nfft 1048576 --a0-db 400 --ampl-dbfs -6` gives 74.52 dB | 74.4 dB floor fit and 74.9 +- 1.3 dB of `doc/dsm2_README.md` | yes |
| 3 | leak approximation of $N_\mathrm{q}(p)$ within 0.7 % of the exact integral at 50, 69.3 and 71.3 dB | derived | yes |
| 4 | $a_1 = 2C_1/C_2$, $C_\mathrm{1,min}$ 0.0970 fF, kT/C 11.240 and 9.588 uV, 355.4 nV/$\sqrt{\mathrm{Hz}}$ | `sizing/size_sc_int2.ipynb`, `doc/sc_int2_README.md` (355.6) | yes |
| 4 | leak $2.857\cdot10^{-4}$ and $1.911\cdot10^{-4}$, $(C_1/C_2)/A_\mathrm{OTA}$ $2.029\cdot10^{-4}$, 71.31 and 69.34 dB, $A_\mathrm{OTA} \ge$ 51.72 and 52.10 dB | `sizing/size_sc_int2.ipynb`, `doc/sc_int2_README.md`, `doc/ota_fcasc2_README.md` | yes |
| 4 | $n$ = 8, $\tau_\mathrm{max}$ 30.518 ns, $\beta$ 0.7861 and 0.8042, $C_\mathrm{Ltot}$ 210.1 and 279.2 fF, $\tau$ 17.65 and 22.92 ns, SR 2.855 and 2.149 V/us, swing bound 0.486 V, step 0.5 V | `sizing/size_sc_int2.ipynb` | yes |
| 4 | static error 0.315 % at 51.73 dB and $\beta$ 0.820, $\beta$ map 56.70 dB at 58.8 dB and $\beta$ 0.785 | `doc/ota_fcasc2_README.md` (0.32 %), derived | yes |
| 4 | DC gain error of the leaky loop, `run_loop`, $2^{20}$ clocks, four inputs away from low-order rationals: $-2.70\cdot10^{-4}$ to $-2.77\cdot10^{-4}$ against $1/(2-p) - 1 = -2.719\cdot10^{-4}$, and the mean $-9.68\cdot10^{-3}$ against $-9.901\cdot10^{-3}$ at $1-p = 10^{-2}$ | derived | within 2 % per input for these four, mean within 3 % at $10^{-2}$ where single inputs range $-8.6\cdot10^{-3}$ to $-1.02\cdot10^{-2}$ (up to 14 % off) |
| 5 | leap-forward codes equal the serial register, code period 131071, dither rms 49.10 mV, code 3 level 10.93 mV at 76.5 mV, ratio 0.116 | `doc/quantizer2_README.md` (11.0 mV), `sizing/size_quantizer2.ipynb` | yes |
| 5 | dead zone, closed form against a noiseless run of `run_loop` (0.002 mV grid, $2^{17}$ clocks, mean over the last $3\cdot2^{15}$), 10 cases | derived | within 0.003 mV |
| 5 | idle tones of the ideal loop at 0.25, 0.375, 0.5, 0.75, 1.0 and 1.125 mV, 1 Hz bins: the spur at $f_\mathrm{s}\lvert\bar{v}\rvert$ and the largest spur below 20 kHz both $2\lvert\bar{v}\rvert$ within 0.01 dB (absolute tolerance), the largest is a multiple of $f_\mathrm{s}\lvert\bar{v}\rvert$, which multiple is a tie-break since all multiples are equal within 0.01 dB and a bin-centred one wins, in band below 0.732 mV | derived, `doc/measurement_plan.md` 3.6 (factor 2 off) | yes |
| 6 | `sinc2_weights` sum to 1 over 9216 clocks, `sinc2_stream` equals the convolution with $h$, $\sum g\,v$ equals the mean of outputs 2 to 17 | `model/dsm_system.py` | to $10^{-12}$ |
| 7 | white noise with $\sigma_u$ lands 291 uV in band against 288.68 uV (one draw of $2^{20}$), 29.21 uV total, 18.24 and 20.27 dB margins | `model/dsm_system.py`, `doc/sc_int2_README.md` | yes |
| 7 | total with $v_\mathrm{n,OTA}$ = 50.32 uV: 28.80 uV | `doc/ota_fcasc2_README.md` | yes |

What the checks found against the repo:

- `model/dsm_system.py` defaults put 902.5 uV in band, 9.9 dB over the budget, with $2kT/C_1$ where the README referral is $kT/C_1$. Known, `doc/sc_int2_README.md` What Is Missing.
- The slew bound in `sizing/size_ota_fcasc2.py` uses $C_1$ as load, its $\tau$ uses $2C_1$. 121.7 nA against 187.2 nA, both far under the 600 nA drawn.
- The stored output of `sizing/size_quantizer2.ipynb` (dither cell) prints 0.06 dB of shaped dither noise against a 1.5 V step. Its own text and this page give 0.48 dB against the 0.5 V step of the integrator output.
- `doc/measurement_plan.md` 3.6 puts the offset spur at "fs times the mean divided by 2", in band below about 1.5 mV. The spur sits at $f_\mathrm{s}\lvert\bar{v}\rvert$ with amplitude $2\lvert\bar{v}\rvert$ and is in band below 0.73 mV, which the plan's own table supports.
- `sizing/size_quantizer2.ipynb` (offset cell) turns 25 mV of comparator offset into about 9 uV at the input with a leak of $3.5\cdot10^{-4}$, which is $(1-p)V_\mathrm{os}$. The dead zone section gives $(1-p)V_\mathrm{os}/a_1$, 26 uV at that leak.
- The OTA noise of the referral: `doc/sc_int2_README.md` uses 51.26 uV, `doc/ota_fcasc2_README.md` carries 50.32 uV for the current schematic. The page quotes both, the total moves from 29.21 to 28.8 uV.
- "All 8 codes appear equally often" in `doc/quantizer2_README.md` holds to one count: code 7 appears 16383 times per period, the others 16384.

Not checked:

- `synthesizeNTF` and `realizeNTF` were not run, `python-deltasigma` is not in the image. The first-order closed forms above stand in for them, and the ABCD matrix of the repo files was rebuilt from them.
- $g_\mathrm{m1}$, $C_\mathrm{gg1}$, the OTA gains and the output range come from gm/ID tables through `sizing/size_ota_fcasc2.py` and were taken as given, not recomputed.
- The 50 dB integrator gain requirement comes from a leaky-integrator sweep that is not in this repo and was not rerun.
- The pnoise, leak bench and settling bench values are simulation results from the READMEs, used as given.
- The 78.0 dB ideal SQNR at $-6$ dBFS in `doc/dsm2_README.md` is 0.13 dB above the formula, where it was rounded was not traced.
