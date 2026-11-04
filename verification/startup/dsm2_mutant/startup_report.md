# Supply start-up bench

## core first

- read CHIP_ID: 0x0001, want 0x0001, pass
- read TEST_CTRL_0: 0x0500, want 0x0500, pass
- read AUX_CTRL_0: 0xFF00, want 0xFF00, pass
- do_q pad stays below 0.33 V, highest 0.006 V, until DSM_QOUT_EN at 716.2 us
- do_q_b pad stays below 0.33 V, highest 0.006 V, until DSM_QOUT_EN at 716.2 us
- IOVDD current: peak 17.540 mA at 443.8 us, longest above 10 mA 1 ns, 13.94 uA mean over the last 20 us, pass
- VDD current: peak 1.952 mA at 712.2 us, longest above 10 mA 0 ns, 10.11 uA mean over the last 20 us, pass
- VDDA current: peak 0.835 mA at 745.4 us, longest above 10 mA 0 ns, 1.51 uA mean over the last 20 us, pass
- dsm2 start-up: di_ena rises at 586.25 us, di_rst_b at 716.25 us, di_qout_en at 716.25 us, the writes take effect at 586.25 and 716.25 us, 130.00 us apart, pass
- dsm2's VDDA current: 153.11 nA before DSM_EN, 21.27 uA enabled in reset, 10.07 uA running (mean from 726 us to the end, design 28 uA), peaks 117.7 uA over 100 ns at 711.25 us (design 140) and 271.9 uA over 10 ns at 711.25 us (design 600, dsm2's worst case 370), peaks from DSM_EN on, no latch fight, pass
- dsm2's enable inrush: 30.3 uA over 100 ns at 586.413 us, 102.8 uA over 10 ns, 25.0 pC in the first 10 us after DSM_EN
- dsm2 runs: 32 periods from 726 us, do_q pad 65.6 % ones (want 30 to 70 %), do_q_b its complement in 100.0 %, do_q_dec equal to do_q in 100.0 % (want 95 %), pass
- VDD current 193.54 nA from 512 to 528 us before DSM_EN, 10104.38 nA with dsm2 running, +9910.84 nA, at most 10 % of dsm2's 10.07 uA, FAIL. VDDA 0.002 to 1.495 uA, +1.493 uA
- vi pad: the source delivers -23.11 nA with dsm2 running, peak +1440.83 uA at 110.3 us
- ibias_test pad, DSM_BTEST_EN low: up to +5.22 mV on its 1 MOhm at 152.1 us
- dsm2 disabled, before DSM_EN: up to 10.74 uA over 1 us at 187.8 us, IOVDD 1.25 V, di_clk 0.71 V
- IOVDD off (5 to 150 us): -570.915 uA mean out of its source, -1440.828 uA at 112.7 us at the most negative, negative is the chip back-powering it
- VDD off (5 to 10 us): +0.000 uA mean out of its source, +0.000 uA at 5.0 us at the most negative, negative is the chip back-powering it
- VDDA off (5 to 10 us): +0.000 uA mean out of its source, +0.000 uA at 9.8 us at the most negative, negative is the chip back-powering it
- solver settings: method=gear cshunt=1e-15
- wall time: 1004 min
- dsm2: sch, transistors

FAIL
