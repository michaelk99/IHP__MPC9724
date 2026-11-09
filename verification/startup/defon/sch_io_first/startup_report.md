# Supply start-up bench

## io first

- read CHIP_ID: 0x0001, want 0x0001, pass
- read TEST_CTRL_0: 0x0500, want 0x0500, pass
- read AUX_CTRL_0: 0xFF00, want 0xFF00, pass
- do_q pad rises to 3.30 V at 112.7 us, above 0.33 V from 28.7 to 199.9 us, IOVDD 3.30 V, VDDA -0.00 V, VDD 0.00 V
- do_q_b pad rises to 3.30 V at 112.7 us, above 0.33 V from 28.7 to 199.9 us, IOVDD 3.30 V, VDDA -0.00 V, VDD 0.00 V
- IOVDD current: peak 53.003 mA at 213.5 us, longest above 10 mA 84 ns, 17.49 uA mean over the last 20 us, pass
- VDD current: peak 0.735 mA at 385.0 us, longest above 10 mA 0 ns, 0.04 uA mean over the last 20 us, pass
- VDDA current: peak 3.141 mA at 456.5 us, longest above 10 mA 0 ns, 12.61 uA mean over the last 20 us, pass
- dsm2 on by default, no SPI write: di_ena rises at 200.12 us, di_qout_en at 200.12 us, both before rst_n at 300 us and staying high, di_rst_b at 447.85 us, 147.85 us after rst_n (want 137.3 to 152.6), pass
- dsm2's VDDA current: 1287.45 nA before di_ena, 8.33 uA enabled in reset, 12.48 uA running (mean from 458 us to the end, design 32 uA), peaks 45.8 uA over 100 ns at 442.85 us (design 220) and 314.7 uA over 10 ns at 481.91 us (design 600, dsm2's worst case 370), peaks from di_ena on, pass
- dsm2's enable inrush: 5.3 uA over 100 ns at 219.884 us, 5.3 uA over 10 ns, 26.2 pC in the first 10 us after di_ena
- dsm2 runs: 56 periods from 458 us, do_q pad 51.8 % ones (want 30 to 70 %), do_q_b its complement in 100.0 %, do_q_dec equal to do_q in 100.0 % (want 95 %), pass
- VDD current against dsm2 not checked: with dsm2 on from VDD up there is no window before it. power_dsm and the v1.2.0 start-up orders check it, the core change is VDD logic only
- vi pad: the source delivers -52.56 nA with dsm2 running, peak +116.75 uA at 442.9 us
- ibias_test pad, DSM_BTEST_EN low: up to -12.33 mV on its 1 MOhm at 213.4 us
- dsm2 disabled, before di_ena: up to 1.79 uA over 1 us at 197.0 us, IOVDD 3.30 V, di_clk 0.00 V
- IOVDD off (5 to 10 us): -0.000 uA mean out of its source, -0.000 uA at 5.6 us at the most negative, negative is the chip back-powering it
- VDD off (5 to 150 us): -0.001 uA mean out of its source, -0.002 uA at 21.3 us at the most negative, negative is the chip back-powering it
- VDDA off (5 to 150 us): -0.000 uA mean out of its source, -0.000 uA at 21.3 us at the most negative, negative is the chip back-powering it
- so the board must bring VDD and VDDA up no later than IOVDD, the order core first
- dsm2: sch, transistors

PASS
