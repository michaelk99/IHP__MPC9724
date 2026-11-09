# Supply start-up bench

## vdda last

- read CHIP_ID: 0x0001, want 0x0001, pass
- read TEST_CTRL_0: 0x0500, want 0x0500, pass
- read AUX_CTRL_0: 0xFF00, want 0xFF00, pass
- do_q pad stays below 0.33 V, highest 0.000 V, until di_qout_en at 60.0 us
- do_q_b pad stays below 0.33 V, highest 0.000 V, until di_qout_en at 60.0 us
- IOVDD current: peak 17.537 mA at 388.8 us, longest above 10 mA 1 ns, 17.49 uA mean over the last 20 us, pass
- VDD current: peak 0.735 mA at 385.0 us, longest above 10 mA 0 ns, 0.04 uA mean over the last 20 us, pass
- VDDA current: peak 3.141 mA at 450.7 us, longest above 10 mA 0 ns, 12.61 uA mean over the last 20 us, pass
- dsm2 on by default, no SPI write: di_ena rises at 60.09 us, di_qout_en at 60.09 us, both before rst_n at 300 us and staying high, di_rst_b at 447.85 us, 147.85 us after rst_n (want 137.3 to 152.6), pass
- dsm2's VDDA current: -0.05 nA before di_ena, 8.16 uA enabled in reset, 12.48 uA running (mean from 458 us to the end, design 28 uA), peaks 39.0 uA over 100 ns at 506.32 us (design 140) and 313.5 uA over 10 ns at 506.32 us (design 600, dsm2's worst case 370), peaks from di_ena on, no latch fight, pass
- dsm2's enable inrush: -0.0 uA over 100 ns at 59.000 us, -0.0 uA over 10 ns, -0.0 pC in the first 10 us after di_ena
- dsm2 runs: 56 periods from 458 us, do_q pad 51.8 % ones (want 30 to 70 %), do_q_b its complement in 100.0 %, do_q_dec equal to do_q in 100.0 % (want 95 %), pass
- VDD current against dsm2 not checked: with dsm2 on from VDD up there is no window before it. power_dsm and the v1.2.0 start-up orders check it, the core change is VDD logic only
- vi pad: the source delivers -52.52 nA with dsm2 running, peak +115.80 uA at 442.9 us
- ibias_test pad, DSM_BTEST_EN low: up to +5.23 mV on its 1 MOhm at 151.9 us
- dsm2 disabled, before di_ena: up to 0.00 uA over 1 us at 0.0 us, IOVDD -0.00 V, di_clk -0.00 V
- IOVDD off (5 to 150 us): -0.000 uA mean out of its source, -0.259 uA at 100.3 us at the most negative, negative is the chip back-powering it
- VDD off (5 to 10 us): +0.000 uA mean out of its source, -0.000 uA at 9.8 us at the most negative, negative is the chip back-powering it
- VDDA off (5 to 250 us): -0.000 uA mean out of its source, -0.027 uA at 100.3 us at the most negative, negative is the chip back-powering it
- solver settings: method=gear
- wall time: 519 min
- dsm2: sch, transistors

PASS
