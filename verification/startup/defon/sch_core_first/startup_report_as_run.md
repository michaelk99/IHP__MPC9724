# Supply start-up bench

## core first

- read CHIP_ID: 0x0001, want 0x0001, pass
- read TEST_CTRL_0: 0x0500, want 0x0500, pass
- read AUX_CTRL_0: 0xFF00, want 0xFF00, pass
- do_q pad stays below 0.33 V, highest 0.000 V, until di_qout_en at 60.0 us
- do_q_b pad stays below 0.33 V, highest 0.000 V, until di_qout_en at 60.0 us
- IOVDD current: peak 17.536 mA at 443.8 us, longest above 10 mA 1 ns, 17.50 uA mean over the last 20 us, pass
- VDD current: peak 0.735 mA at 450.0 us, longest above 10 mA 0 ns, 0.04 uA mean over the last 20 us, pass
- VDDA current: peak 3.496 mA at 186.3 us, longest above 10 mA 0 ns, 12.61 uA mean over the last 20 us, pass
- dsm2 on by default, no SPI write: di_ena rises at 60.02 us, di_qout_en at 60.02 us, both before rst_n at 300 us and staying high, di_rst_b at 447.85 us, 147.85 us after rst_n (want 137.3 to 152.6), pass
- dsm2's known latch fight (6dd2926, quantizer output latch against its preset, fixed GDS due 2026-11-02) occurred: 1 stretch from 186.17 to 186.47 us, 0.30 us in all at 133.7 uA, up to 167.0 uA over 100 ns, left out of the peaks below
- dsm2's VDDA current: 1292.73 nA before di_ena, 8.62 uA enabled in reset, 12.48 uA running (mean from 458 us to the end, design 28 uA), peaks 85.3 uA over 100 ns at 186.05 us (design 140) and 312.4 uA over 10 ns at 463.36 us (design 600, dsm2's worst case 370), peaks from di_ena on outside the latch fight, pass
- dsm2's enable inrush: 5.3 uA over 100 ns at 79.862 us, 5.3 uA over 10 ns, 26.3 pC in the first 10 us after di_ena
- dsm2 runs: 56 periods from 458 us, do_q pad 51.8 % ones (want 30 to 70 %), do_q_b its complement in 100.0 %, do_q_dec equal to do_q in 100.0 % (want 95 %), pass
- VDD current against dsm2 not checked: with dsm2 on from VDD up there is no window before it. power_dsm and the v1.2.0 start-up orders check it, the core change is VDD logic only
- vi pad: the source delivers -47.79 nA with dsm2 running, peak +1440.83 uA at 110.3 us
- ibias_test pad, DSM_BTEST_EN low: up to +5.23 mV on its 1 MOhm at 152.1 us
- dsm2 disabled, before di_ena: up to 1.80 uA over 1 us at 57.0 us, IOVDD 0.00 V, di_clk 0.55 V
- IOVDD off (5 to 150 us): -570.915 uA mean out of its source, -1440.828 uA at 117.9 us at the most negative, negative is the chip back-powering it
- VDD off (5 to 10 us): +0.000 uA mean out of its source, -0.000 uA at 9.8 us at the most negative, negative is the chip back-powering it
- VDDA off (5 to 10 us): +0.000 uA mean out of its source, +0.000 uA at 9.8 us at the most negative, negative is the chip back-powering it
- solver settings: method=gear
- wall time: 520 min
- dsm2: sch, transistors

PASS
