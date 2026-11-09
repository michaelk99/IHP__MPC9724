v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 280 -710 300 -710 {lab=vi_p}
N 280 -670 300 -670 {lab=vi_n}
N 280 -610 300 -610 {lab=di_clk}
N 280 -570 300 -570 {lab=di_en}
N 400 -530 400 -100 {lab=vss}
N 560 -760 600 -760 {lab=d_p}
N 680 -760 760 -760 {lab=d_p_1}
N 840 -760 920 -760 {lab=d_p_2}
N 500 -570 560 -570 {lab=d_n}
N 560 -570 560 -500 {lab=d_n}
N 560 -500 600 -500 {lab=d_n}
N 680 -500 760 -500 {lab=d_n_1}
N 840 -500 920 -500 {lab=d_n_2}
N 1040 -740 1140 -740 {lab=d_p_b}
N 900 -720 920 -720 {lab=d_preset_b}
N 1100 -700 1140 -700 {lab=do_qi_b}
N 640 -920 700 -920 {lab=di_en}
N 640 -880 700 -880 {lab=di_rst_b}
N 400 -990 1350 -990 {lab=vdd}
N 400 -100 1320 -100 {lab=vss}
N 1320 -100 1360 -100 {lab=vss}
N 1260 -560 1300 -560 {lab=do_qi_b}
N 1350 -560 1390 -560 {lab=do_qi_b}
N 1100 -540 1140 -540 {lab=d_n_b}
N 1100 -540 1100 -520 {lab=d_n_b}
N 1040 -520 1100 -520 {lab=d_n_b}
N 1100 -660 1300 -630 {lab=do_qi_b}
N 1100 -620 1300 -670 {lab=do_qi}
N 1100 -580 1140 -580 {lab=do_qi}
N 1100 -700 1100 -660 {lab=do_qi_b}
N 1300 -720 1300 -670 {lab=do_qi}
N 1300 -630 1300 -560 {lab=do_qi_b}
N 1100 -620 1100 -580 {lab=do_qi}
N 1320 -720 1390 -720 {lab=do_qi}
N 1260 -720 1300 -720 {lab=do_qi}
N 1300 -560 1350 -560 {lab=do_qi_b}
N 1300 -720 1320 -720 {lab=do_qi}
N 1350 -990 1390 -990 {lab=vdd}
N 400 -990 400 -730 {lab=vdd}
N 200 -990 400 -990 {lab=vdd}
N 140 -990 200 -990 {lab=vdd}
N 500 -690 560 -690 {lab=d_p}
N 560 -760 560 -690 {lab=d_p}
N 110 -100 200 -100 {lab=vss}
N 200 -100 400 -100 {lab=vss}
C {quantizer2_sal.sym} 400 -630 0 0 {name=XSAL0
}
N 1390 -990 1620 -990 {lab=vdd}
N 1360 -100 2140 -100 {lab=vss}
N 1540 -990 1540 -930 {lab=vdd}
N 1540 -900 1560 -900 {lab=vdd}
N 1560 -990 1560 -900 {lab=vdd}
N 1540 -870 1560 -870 {lab=vdd}
N 1560 -900 1560 -870 {lab=vdd}
N 1480 -900 1500 -900 {lab=vss}
N 1540 -170 1540 -100 {lab=vss}
N 1540 -200 1560 -200 {lab=vss}
N 1560 -200 1560 -100 {lab=vss}
N 1540 -230 1560 -230 {lab=vss}
N 1560 -230 1560 -200 {lab=vss}
N 1480 -200 1500 -200 {lab=vdd}
N 1740 -200 1740 -100 {lab=vss}
N 1740 -230 1740 -200 {lab=vss}
C {iopin.sym} 280 -710 2 0 {name=l1 lab=vi_p}
C {iopin.sym} 280 -670 2 0 {name=l2 lab=vi_n}
C {ipin.sym} 280 -610 2 0 {name=l3 lab=di_clk}
C {ipin.sym} 280 -570 2 0 {name=l4 lab=di_en}
C {lab_wire.sym} 550 -690 0 0 {name=l7 lab=d_p}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 640 -760 0 0 {name=XINV0
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
C {lab_wire.sym} 760 -760 0 0 {name=l8 lab=d_p_1}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_2.sym} 800 -760 0 0 {name=XINV1
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
C {lab_wire.sym} 920 -760 0 0 {name=l9 lab=d_p_2}
C {sg13cmos5l_stdcells/sg13cmos5l_nand2_2.sym} 980 -740 0 0 {name=XGATE_P
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
C {lab_pin.sym} 900 -720 0 0 {name=l28 lab=d_preset_b}
C {lab_wire.sym} 550 -570 0 0 {name=l10 lab=d_n}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 640 -500 0 0 {name=XINV3
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
C {lab_wire.sym} 760 -500 0 0 {name=l11 lab=d_n_1}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_2.sym} 800 -500 0 0 {name=XINV4
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
C {lab_wire.sym} 920 -500 0 0 {name=l12 lab=d_n_2}
C {sg13cmos5l_stdcells/sg13cmos5l_nor2_2.sym} 980 -520 2 1 {name=XGATE_N
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
C {lab_wire.sym} 1100 -740 0 0 {name=l13 lab=d_p_b}
C {lab_wire.sym} 1100 -520 0 0 {name=l14 lab=d_n_b}
C {sg13cmos5l_stdcells/sg13cmos5l_nor2_2.sym} 1200 -720 0 0 {name=XNOR0
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
C {sg13cmos5l_stdcells/sg13cmos5l_nor2_2.sym} 1200 -560 2 1 {name=XNOR1
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
C {opin.sym} 1390 -720 0 0 {name=l15 lab=do_qi}
C {opin.sym} 1390 -560 2 1 {name=l16 lab=do_qi_b}
C {sg13cmos5l_stdcells/sg13cmos5l_and2_2.sym} 760 -900 0 0 {name=XAND_RST
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
C {lab_pin.sym} 640 -920 0 0 {name=l17 lab=di_en}
C {ipin.sym} 640 -880 2 0 {name=l18 lab=di_rst_b}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_4.sym} 760 -580 0 0 {name=XINV7
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
C {sg13_hv_pmos.sym} 1720 -900 0 0 {name=PDUMHV1
l=450n
w=3u
ng=1
m=1
model=sg13_hv_pmos
spiceprefix=X
}
C {sg13_hv_nmos.sym} 1720 -200 0 0 {name=NDUMHV1
l=450n
w=1u
ng=1
m=1
model=sg13_hv_nmos
spiceprefix=X
}
C {iopin.sym} 140 -990 2 0 {name=l25 lab=vdd}
C {iopin.sym} 110 -100 2 0 {name=l26 lab=vss}
C {sg13_hv_pmos.sym} 1520 -900 0 0 {name=PDUMHV
l=450n
w=3u
ng=1
m=1
model=sg13_hv_pmos
spiceprefix=X
}
C {lab_pin.sym} 1480 -900 0 0 {name=l41 lab=vss}
C {sg13_hv_nmos.sym} 1520 -200 0 0 {name=NDUMHV
l=450n
w=1u
ng=1
m=1
model=sg13_hv_nmos
spiceprefix=X
}
C {lab_pin.sym} 1480 -200 0 0 {name=l42 lab=vdd}
 1560 -690 0 0 0.25 0.25 {}
T {Dummies, layout row fill} 1480 -820 0 0 0.25 0.25 {}
T {HV dummies, layout fill} 1500 -300 0 0 0.25 0.25 {}
T {Preset: d_p_b forced high, d_n_b forced low, so the latch holds do_qi low without a fight} 700 -440 0 0 0.25 0.25 {}
N 300 -650 280 -650 {lab=vg_q[2:0]}
C {lab_pin.sym} 280 -650 0 0 {name=l201 sig_type=std_logic lab=vg_q[2:0]}
N 300 -590 280 -590 {lab=vg_p[2:0]}
C {lab_pin.sym} 280 -590 0 0 {name=l202 sig_type=std_logic lab=vg_p[2:0]}
T {Dither network (O1b): ladder, gate switches, flying caps} 2400 -1080 0 0 0.4 0.4 {}
C {quantizer2_dith.sym} 2700 -800 0 0 {name=XDITH
}
N 2560 -900 2540 -900 {lab=di_clk}
C {lab_pin.sym} 2540 -900 0 0 {name=l203 sig_type=std_logic lab=di_clk}
N 2560 -860 2540 -860 {lab=di_dith[2:0]}
C {lab_pin.sym} 2540 -860 0 0 {name=l204 sig_type=std_logic lab=di_dith[2:0]}
N 2560 -820 2540 -820 {lab=di_amp_s[3:0]}
C {lab_pin.sym} 2540 -820 0 0 {name=l205 sig_type=std_logic lab=di_amp_s[3:0]}
N 2560 -780 2540 -780 {lab=di_amp_s_b[3:0]}
C {lab_pin.sym} 2540 -780 0 0 {name=l206 sig_type=std_logic lab=di_amp_s_b[3:0]}
N 2560 -740 2540 -740 {lab=vi_p}
C {lab_pin.sym} 2540 -740 0 0 {name=l207 sig_type=std_logic lab=vi_p}
N 2560 -700 2540 -700 {lab=vi_n}
C {lab_pin.sym} 2540 -700 0 0 {name=l208 sig_type=std_logic lab=vi_n}
N 2840 -900 2860 -900 {lab=vg_q[2:0]}
C {lab_pin.sym} 2860 -900 2 0 {name=l209 sig_type=std_logic lab=vg_q[2:0]}
N 2840 -860 2860 -860 {lab=vg_p[2:0]}
C {lab_pin.sym} 2860 -860 2 0 {name=l210 sig_type=std_logic lab=vg_p[2:0]}
N 2620 -960 2620 -980 {lab=vdd}
C {lab_pin.sym} 2620 -980 3 0 {name=l211 sig_type=std_logic lab=vdd}
N 2660 -960 2660 -980 {lab=di_en}
C {lab_pin.sym} 2660 -980 3 0 {name=l212 sig_type=std_logic lab=di_en}
N 2700 -960 2700 -980 {lab=di_dith_en}
C {lab_pin.sym} 2700 -980 3 0 {name=l213 sig_type=std_logic lab=di_dith_en}
N 2620 -640 2620 -620 {lab=vss}
C {lab_pin.sym} 2620 -620 1 0 {name=l214 sig_type=std_logic lab=vss}
T {Pad drivers, both gated by di_qout_en (low: both outputs low)} 2400 -560 0 0 0.4 0.4 {}
C {sg13cmos5l_stdcells/sg13cmos5l_and2_1.sym} 2500 -460 0 0 {name=XAQ0
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 2440 -480 2420 -480 {lab=do_qi}
C {lab_pin.sym} 2420 -480 0 0 {name=l215 sig_type=std_logic lab=do_qi}
N 2440 -440 2420 -440 {lab=di_qout_en}
C {lab_pin.sym} 2420 -440 0 0 {name=l216 sig_type=std_logic lab=di_qout_en}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 2700 -460 0 0 {name=XQD10
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 2560 -460 2660 -460 {lab=d_qg0}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_2.sym} 2860 -460 0 0 {name=XQD20
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 2740 -460 2820 -460 {lab=d_qg0_b}
N 2900 -460 2940 -460 {lab=do_q}
C {opin.sym} 2940 -460 0 0 {name=p217 lab=do_q}
C {sg13cmos5l_stdcells/sg13cmos5l_and2_1.sym} 2500 -340 0 0 {name=XAQ1
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 2440 -360 2420 -360 {lab=do_qi_b}
C {lab_pin.sym} 2420 -360 0 0 {name=l218 sig_type=std_logic lab=do_qi_b}
N 2440 -320 2420 -320 {lab=di_qout_en}
C {lab_pin.sym} 2420 -320 0 0 {name=l219 sig_type=std_logic lab=di_qout_en}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 2700 -340 0 0 {name=XQD11
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 2560 -340 2660 -340 {lab=d_qg1}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_2.sym} 2860 -340 0 0 {name=XQD21
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 2740 -340 2820 -340 {lab=d_qg1_b}
N 2900 -340 2940 -340 {lab=do_q_b}
C {opin.sym} 2940 -340 0 0 {name=p220 lab=do_q_b}
T {do_q_dec: ungated copy for the decimator, dummy of the same load on do_qi_b} 2400 -220 0 0 0.4 0.4 {}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 2500 -140 0 0 {name=XDC1
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 2460 -140 2440 -140 {lab=do_qi}
C {lab_pin.sym} 2440 -140 0 0 {name=l221 sig_type=std_logic lab=do_qi}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_2.sym} 2660 -140 0 0 {name=XDC2
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 2540 -140 2620 -140 {lab=d_qdec_b}
N 2700 -140 2740 -140 {lab=do_q_dec}
C {opin.sym} 2740 -140 0 0 {name=p222 lab=do_q_dec}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 2500 -40 0 0 {name=XDD1
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 2460 -40 2440 -40 {lab=do_qi_b}
C {lab_pin.sym} 2440 -40 0 0 {name=l223 sig_type=std_logic lab=do_qi_b}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_2.sym} 2660 -40 0 0 {name=XDD2
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 2540 -40 2620 -40 {lab=d_qdum_b}
C {sg13cmos5l_stdcells/sg13cmos5l_and2_1.sym} 2880 -20 0 0 {name=XDDL
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 2700 -40 2820 -40 {lab=d_qdum}
N 2820 0 2800 0 {lab=vss}
C {lab_pin.sym} 2800 0 0 0 {name=l224 sig_type=std_logic lab=vss}
N 2940 -20 2960 -20 {lab=d_qdum_x}
C {lab_pin.sym} 2960 -20 2 0 {name=l225 sig_type=std_logic lab=d_qdum_x}
C {noconn.sym} 2960 -20 2 0 {name=l999}
C {ipin.sym} 3300 -1080 0 0 {name=p226 lab=di_dith_en}
N 3300 -1080 3320 -1080 {lab=di_dith_en}
C {lab_pin.sym} 3320 -1080 2 0 {name=l227 sig_type=std_logic lab=di_dith_en}
C {ipin.sym} 3300 -1040 0 0 {name=p228 lab=di_dith[2:0]}
N 3300 -1040 3320 -1040 {lab=di_dith[2:0]}
C {lab_pin.sym} 3320 -1040 2 0 {name=l229 sig_type=std_logic lab=di_dith[2:0]}
C {ipin.sym} 3300 -1000 0 0 {name=p230 lab=di_amp_s[3:0]}
N 3300 -1000 3320 -1000 {lab=di_amp_s[3:0]}
C {lab_pin.sym} 3320 -1000 2 0 {name=l231 sig_type=std_logic lab=di_amp_s[3:0]}
C {ipin.sym} 3300 -960 0 0 {name=p232 lab=di_amp_s_b[3:0]}
N 3300 -960 3320 -960 {lab=di_amp_s_b[3:0]}
C {lab_pin.sym} 3320 -960 2 0 {name=l233 sig_type=std_logic lab=di_amp_s_b[3:0]}
C {ipin.sym} 3300 -920 0 0 {name=p234 lab=di_qout_en}
N 3300 -920 3320 -920 {lab=di_qout_en}
C {lab_pin.sym} 3320 -920 2 0 {name=l235 sig_type=std_logic lab=di_qout_en}
C {title.sym} 240 -40 0 0 {name=l0 author="(c) 2026 Michael Koefinger"}

N 820 -900 960 -900 {lab=d_preset_b}
C {lab_wire.sym} 930 -900 0 0 {name=l27 lab=d_preset_b}
N 700 -580 720 -580 {lab=d_preset_b}
C {lab_pin.sym} 700 -580 0 0 {name=l19 lab=d_preset_b}
N 800 -580 900 -580 {lab=d_preset}
N 900 -580 900 -540 {lab=d_preset}
N 900 -540 920 -540 {lab=d_preset}
C {lab_wire.sym} 890 -580 0 0 {name=l40 lab=d_preset}
N 1620 -990 1760 -990 {lab=vdd}
N 1740 -990 1740 -930 {lab=vdd}
N 1740 -900 1760 -900 {lab=vdd}
N 1760 -990 1760 -900 {lab=vdd}
N 1740 -870 1760 -870 {lab=vdd}
N 1760 -900 1760 -870 {lab=vdd}
N 1680 -900 1700 -900 {lab=vss}
C {lab_pin.sym} 1680 -900 0 0 {name=l23 lab=vss}
N 1680 -200 1700 -200 {lab=vdd}
C {lab_pin.sym} 1680 -200 0 0 {name=l24 lab=vdd}
