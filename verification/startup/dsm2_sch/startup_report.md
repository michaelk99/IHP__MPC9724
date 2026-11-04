# Supply start-up bench

## io first

- read CHIP_ID: 0x0001, want 0x0001, pass
- read TEST_CTRL_0: 0x0500, want 0x0500, pass
- read AUX_CTRL_0: 0xFF00, want 0xFF00, pass
- do_q pad rises to 3.30 V at 202.5 us, above 0.33 V from 28.2 to 202.6 us, IOVDD 3.30 V, VDDA 0.79 V, VDD 0.63 V
- do_q_b pad rises to 3.30 V at 205.6 us, above 0.33 V from 28.2 to 205.6 us, IOVDD 3.30 V, VDDA 0.83 V, VDD 0.67 V
- IOVDD current: peak 53.008 mA at 215.4 us, longest above 10 mA 51 ns, 18.37 uA mean over the last 20 us, pass
- VDD current: peak 0.764 mA at 450.0 us, longest above 10 mA 0 ns, 0.04 uA mean over the last 20 us, pass
- VDDA current: peak 3.709 mA at 715.4 us, longest above 10 mA 0 ns, 12.85 uA mean over the last 20 us, pass
- dsm2 start-up: di_ena rises at 586.25 us, di_rst_b at 716.25 us, di_qout_en at 716.25 us, the writes take effect at 586.25 and 716.25 us, 130.00 us apart, pass
- dsm2's known latch fight (6dd2926, quantizer output latch against its preset, fixed GDS due 2026-11-02) occurred: 2 stretches from 712.50 to 715.43 us, 1.95 us in all at 206.9 uA, up to 229.8 uA over 100 ns, left out of the peaks below
- dsm2's VDDA current: 467.87 nA before DSM_EN, 26.04 uA enabled in reset, 12.69 uA running (mean from 726 us to the end, design 28 uA), peaks 67.7 uA over 100 ns at 586.33 us (design 140) and 322.6 uA over 10 ns at 729.10 us (design 600, dsm2's worst case 370), peaks from DSM_EN on outside the latch fight, pass
- dsm2's enable inrush: 67.7 uA over 100 ns at 586.325 us, 213.5 uA over 10 ns, 37.0 pC in the first 10 us after DSM_EN
- dsm2 runs: 32 periods from 726 us, do_q pad 50.0 % ones (want 30 to 70 %), do_q_b its complement in 100.0 %, do_q_dec equal to do_q in 100.0 % (want 95 %), pass
- VDD current 40.38 nA from 512 to 528 us before DSM_EN, 38.29 nA with dsm2 running, -2.08 nA, at most 10 % of dsm2's 12.69 uA, pass. VDDA 0.470 to 12.839 uA, +12.369 uA
- vi pad: the source delivers -53.04 nA with dsm2 running, peak +129.76 uA at 712.5 us
- ibias_test pad, DSM_BTEST_EN low: up to -12.15 mV on its 1 MOhm at 215.4 us
- dsm2 disabled, before DSM_EN: up to 0.60 uA over 1 us at 249.0 us, IOVDD 3.30 V, di_clk 0.00 V
- IOVDD off (5 to 10 us): +0.000 uA mean out of its source, +0.000 uA at 9.8 us at the most negative, negative is the chip back-powering it
- VDD off (5 to 150 us): -0.001 uA mean out of its source, -0.002 uA at 21.5 us at the most negative, negative is the chip back-powering it
- VDDA off (5 to 150 us): -0.000 uA mean out of its source, -0.001 uA at 21.5 us at the most negative, negative is the chip back-powering it
- so the board must bring VDD and VDDA up no later than IOVDD, the order core first
- solver settings: method=gear cshunt=1e-15
- wall time: 1094 min
- dsm2: sch, transistors

## core first

- read CHIP_ID: 0x0001, want 0x0001, pass
- read TEST_CTRL_0: 0x0500, want 0x0500, pass
- read AUX_CTRL_0: 0xFF00, want 0xFF00, pass
- do_q pad stays below 0.33 V, highest 0.006 V, until DSM_QOUT_EN at 716.2 us
- do_q_b pad stays below 0.33 V, highest 0.006 V, until DSM_QOUT_EN at 716.2 us
- IOVDD current: peak 18.075 mA at 716.3 us, longest above 10 mA 1 ns, 18.37 uA mean over the last 20 us, pass
- VDD current: peak 0.764 mA at 450.0 us, longest above 10 mA 0 ns, 0.04 uA mean over the last 20 us, pass
- VDDA current: peak 3.715 mA at 713.5 us, longest above 10 mA 0 ns, 12.85 uA mean over the last 20 us, pass
- dsm2 start-up: di_ena rises at 586.25 us, di_rst_b at 716.25 us, di_qout_en at 716.25 us, the writes take effect at 586.25 and 716.25 us, 130.00 us apart, pass
- dsm2's known latch fight (6dd2926, quantizer output latch against its preset, fixed GDS due 2026-11-02) occurred: 2 stretches from 712.50 to 715.43 us, 1.95 us in all at 206.8 uA, up to 229.7 uA over 100 ns, left out of the peaks below
- dsm2's VDDA current: 467.77 nA before DSM_EN, 26.04 uA enabled in reset, 12.69 uA running (mean from 726 us to the end, design 28 uA), peaks 67.7 uA over 100 ns at 586.33 us (design 140) and 322.2 uA over 10 ns at 729.10 us (design 600, dsm2's worst case 370), peaks from DSM_EN on outside the latch fight, pass
- dsm2's enable inrush: 67.7 uA over 100 ns at 586.325 us, 213.3 uA over 10 ns, 37.0 pC in the first 10 us after DSM_EN
- dsm2 runs: 32 periods from 726 us, do_q pad 50.0 % ones (want 30 to 70 %), do_q_b its complement in 100.0 %, do_q_dec equal to do_q in 100.0 % (want 95 %), pass
- VDD current 40.39 nA from 512 to 528 us before DSM_EN, 38.30 nA with dsm2 running, -2.09 nA, at most 10 % of dsm2's 12.69 uA, pass. VDDA 0.470 to 12.839 uA, +12.369 uA
- vi pad: the source delivers -53.00 nA with dsm2 running, peak +1440.83 uA at 110.3 us
- ibias_test pad, DSM_BTEST_EN low: up to +5.23 mV on its 1 MOhm at 152.1 us
- dsm2 disabled, before DSM_EN: up to 52.09 uA over 1 us at 186.9 us, IOVDD 1.22 V, di_clk 0.81 V
- IOVDD off (5 to 150 us): -570.914 uA mean out of its source, -1440.828 uA at 111.9 us at the most negative, negative is the chip back-powering it
- VDD off (5 to 10 us): -0.000 uA mean out of its source, -0.000 uA at 5.0 us at the most negative, negative is the chip back-powering it
- VDDA off (5 to 10 us): -0.000 uA mean out of its source, -0.000 uA at 5.6 us at the most negative, negative is the chip back-powering it
- solver settings: method=gear cshunt=1e-15
- wall time: 1086 min
- dsm2: sch, transistors

## bounce

- read CHIP_ID at 320 us: 0x0001, want 0x0001, pass
- read SPARE_14 at 580 us: 0x5555, want 0x5555, pass
- stimulus ran, dsm_clk: 151 edges, at least 136, pass
- stimulus ran, do_q: 73 edges, at least 19, pass
- stimulus ran, do_q_b: 73 edges, at least 19, pass
- stimulus ran, miso in the SPARE_14 read: 18 edges, at least 12, pass
- stimulus ran, adc_conv: 2 edges, at least 2, pass
- from 576 to 650 us: die VSS -5 mV, IOVSS -6 mV, paddle -6 mV at the worst sample against the board ground
- rails on the die, droop and overshoot against the quiet level: IOVDD-IOVSS 57 and 37 mV, VDD-VSS 14 and 24 mV, VDDA-VSS 22 and 24 mV
- peak currents in the wires: IOVDD 26.7 mA, VDD 0.85 mA, VDDA 2.7 mA, IOVSS downbond 1.7 mA
- vi on the die: +64.0 and -59.7 mV against its quiet level, 123.7 mV peak to peak
- vcm on the die: +115.7 and -146.5 mV against its quiet level, 262.2 mV peak to peak
- ibias_test on the die: +17.9 and -29.2 mV against its quiet level, 47.1 mV peak to peak
- static core inputs move up to 24 mV; no core input glitches, pass
- dsm2 start-up: di_ena rises at 441.25 us, di_rst_b at 571.25 us, di_qout_en at 571.25 us, the writes take effect at 441.25 and 571.25 us, 130.00 us apart, pass
- dsm2's known latch fight (6dd2926, quantizer output latch against its preset, fixed GDS due 2026-11-02) occurred: 4 stretches from 567.51 to 570.43 us, 1.94 us in all at 205.7 uA, up to 228.1 uA over 100 ns, left out of the peaks below
- dsm2's VDDA current: 467.17 nA before DSM_EN, 26.04 uA enabled in reset, 12.63 uA running (mean from 581 us to the end, design 28 uA), peaks 67.8 uA over 100 ns at 441.32 us (design 140) and 323.3 uA over 10 ns at 646.60 us (design 600, dsm2's worst case 370), peaks from DSM_EN on outside the latch fight, pass
- dsm2's enable inrush: 67.8 uA over 100 ns at 441.323 us, 214.5 uA over 10 ns, 37.0 pC in the first 10 us after DSM_EN
- dsm2 runs: 68 periods from 581 us, do_q pad 51.5 % ones (want 30 to 70 %), do_q_b its complement in 100.0 %, do_q_dec equal to do_q in 100.0 % (want 95 %), pass
- vi pad: the source delivers -56.29 nA with dsm2 running, peak +135.11 uA at 567.5 us
- ibias_test pad, DSM_BTEST_EN low: up to -29.39 mV on its 1 MOhm at 598.8 us
- dsm2 disabled, before DSM_EN: up to 0.49 uA over 1 us at 379.0 us, IOVDD 3.30 V, di_clk 0.00 V
- solver settings: method=gear cshunt=1e-15
- wall time: 1142 min
- dsm2: sch, transistors

PASS
