# Supply start-up bench

## io first

- read CHIP_ID: 0x0001, want 0x0001, pass
- read TEST_CTRL_0: 0x0500, want 0x0500, pass
- read AUX_CTRL_0: 0xFF00, want 0xFF00, pass
- do_q pad rises to 3.30 V at 202.3 us, above 0.33 V from 28.4 to 202.3 us, IOVDD 3.30 V, VDDA 0.78 V, VDD 0.63 V
- do_q_b pad rises to 3.30 V at 202.3 us, above 0.33 V from 28.4 to 202.3 us, IOVDD 3.30 V, VDDA 0.78 V, VDD 0.63 V
- IOVDD current: peak 53.017 mA at 215.1 us, longest above 10 mA 34 ns, 0.19 uA mean over the last 20 us, pass
- VDD current: peak 0.764 mA at 450.0 us, longest above 10 mA 0 ns, 0.05 uA mean over the last 20 us, pass
- VDDA current: peak 0.002 mA at 320.0 us, longest above 10 mA 0 ns, 0.00 uA mean over the last 20 us, pass
- so the board must bring VDD and VDDA up no later than IOVDD, the order core first
- solver settings: method=gear cshunt=1e-15

## core first

- read CHIP_ID: 0x0001, want 0x0001, pass
- read TEST_CTRL_0: 0x0500, want 0x0500, pass
- read AUX_CTRL_0: 0xFF00, want 0xFF00, pass
- do_q pad stays below 0.33 V, highest 0.006 V
- do_q_b pad stays below 0.33 V, highest 0.006 V
- IOVDD current: peak 17.661 mA at 443.8 us, longest above 10 mA 1 ns, 0.19 uA mean over the last 20 us, pass
- VDD current: peak 0.764 mA at 450.0 us, longest above 10 mA 0 ns, 0.05 uA mean over the last 20 us, pass
- VDDA current: peak 0.203 mA at 188.4 us, longest above 10 mA 0 ns, 0.00 uA mean over the last 20 us, pass
- solver settings: method=gear cshunt=1e-15

## bounce

- read CHIP_ID at 320 us: 0x0001, want 0x0001, pass
- read SPARE_14 at 450 us: 0x5555, want 0x5555, pass
- stimulus ran, dsm_clk: 461 edges, at least 415, pass
- stimulus ran, do_q: 230 edges, at least 207, pass
- stimulus ran, do_q_b: 230 edges, at least 207, pass
- stimulus ran, miso in the SPARE_14 read: 18 edges, at least 12, pass
- stimulus ran, adc_conv: 2 edges, at least 2, pass
- from 295 to 520 us: die VSS +4 mV, IOVSS +4 mV, paddle +4 mV at the worst sample against the board ground
- rails on the die, droop and overshoot against the quiet level: IOVDD-IOVSS 49 and 47 mV, VDD-VSS 17 and 27 mV, VDDA-VSS 15 and 25 mV
- peak currents in the wires: IOVDD 22.9 mA, VDD 0.87 mA, VDDA 1.0 mA, IOVSS downbond 1.3 mA
- vi on the die: +4.1 and -1.9 mV against its quiet level, 6.0 mV peak to peak
- vcm on the die: +4.0 and -1.9 mV against its quiet level, 5.9 mV peak to peak
- ibias_test on the die: +23.8 and -24.2 mV against its quiet level, 48.0 mV peak to peak
- static core inputs move up to 1 mV; no core input glitches, pass
- solver settings: method=gear cshunt=1e-15 reltol=3e-3

## power dsa1

- IOVDD current: 28.54 nA mean over the last 122.1 us, halves 28.54 and 28.54 nA
- VDD current: 12.65 nA mean over the last 122.1 us, halves 12.65 and 12.65 nA
- VDDA current: 2.19 nA mean over the last 122.1 us, halves 2.19 and 2.19 nA
- solver settings: method=gear cshunt=1e-15

## power dsm

- IOVDD current: 18370.80 nA mean over the last 122.1 us, halves 18513.44 and 18228.16 nA
- VDD current: 12.65 nA mean over the last 122.1 us, halves 12.65 and 12.65 nA
- VDDA current: 314.17 nA mean over the last 122.1 us, halves 315.97 and 312.37 nA
- solver settings: method=gear cshunt=1e-15

## VDD isolation

- VDD current with dsm2 off 12.65 nA, with dsm_clk at 1.024 MHz and the do_q pads switching 12.65 nA, difference -0.001 nA, resolution 0.013 nA, equal within the resolution, pass
- VDDA current 2.19 nA with dsm2 off, 314.17 nA running
- IOVDD current 28.54 nA with dsm2 off, 18.37 uA running, the do_q pads' output stages

## DSA1 state against v1.1.1

- IOVDD: 28.54 nA here, 37.54 nA on tapeout/v1.1.1, -24.0 %, over 1 %
- VDD: 12.65 nA here, 21.45 nA on tapeout/v1.1.1, -41.0 %, over 1 %
- VDD + VDDA: 14.84 nA here, 21.45 nA on tapeout/v1.1.1, -30.8 %, over 1 %
- IO cells that differ (here, tapeout/v1.1.1): sg13cmos5l_IOPadAnalog 3 against 2, sg13cmos5l_IOPadIn 7 against 6, sg13cmos5l_IOPadInOut30mA 0 against 2, sg13cmos5l_IOPadOut30mA 2 against 18, sg13cmos5l_IOPadOut4mA 2 against 0, sg13cmos5l_IOPadVdd 2 against 1, sg13cmos5l_IOPadVss 2 against 1, sg13cmos5l_ip__clamp_vddvss 2 against 1, sg13cmos5l_ip__cut_vdd 2 against 0
- the settled current is the pads' leakage plus the switching of the two toggling inputs, so it follows that population
- static current predicted from the cells' DC runs (cell_leakage.md), this chip: IOVDD 3.29 nA, VDD 2.35 nA, VDDA 2.00 nA
- static current predicted from the cells' DC runs (cell_leakage.md), tapeout/v1.1.1: IOVDD 11.39 nA, VDD 10.95 nA

## Core power

- core power from the gate-level VCD, typical corner: 3.075 uW, 3.061 uW on v1.1.1, +0.45 %, within 2 %, pass
- the macro's own `make -C macros/dsa1_dig power-vcd`, the XSPICE core in this bench draws nothing

PASS
