v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
T {Enables, phase delay and decoder} 120 -2180 0 0 0.5 0.5 {}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 300 -2080 0 0 {name=XINVEN
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 260 -2080 240 -2080 {lab=di_dith_en}
C {ipin.sym} 240 -2080 0 0 {name=p1 lab=di_dith_en}
N 340 -2080 360 -2080 {lab=d_en_b}
C {lab_pin.sym} 360 -2080 2 0 {name=l2 sig_type=std_logic lab=d_en_b}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 300 -2000 0 0 {name=XINVENL
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 260 -2000 240 -2000 {lab=di_en}
C {ipin.sym} 240 -2000 0 0 {name=p3 lab=di_en}
N 340 -2000 360 -2000 {lab=d_enl_b}
C {lab_pin.sym} 360 -2000 2 0 {name=l4 sig_type=std_logic lab=d_enl_b}
C {rhigh.sym} 140 -1860 1 0 {name=RDLY
w=0.5e-6
l=40e-6
model=rhigh
body=vss
spiceprefix=X
b=0
m=1
}
N 110 -1860 90 -1860 {lab=di_clk}
C {ipin.sym} 90 -1860 0 0 {name=p5 lab=di_clk}
N 170 -1860 210 -1860 {lab=d_rc}
C {lab_pin.sym} 210 -1860 3 0 {name=l6 sig_type=std_logic lab=d_rc}
C {sg13_lv_nmos.sym} 250 -1820 0 0 {name=MCDLY
l=1u
w=7u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 210 -1860 230 -1860 {}
N 230 -1860 230 -1820 {}
N 270 -1850 290 -1850 {lab=vss}
C {lab_pin.sym} 290 -1850 2 0 {name=l7 sig_type=std_logic lab=vss}
N 270 -1790 290 -1790 {lab=vss}
C {lab_pin.sym} 290 -1790 2 0 {name=l8 sig_type=std_logic lab=vss}
N 270 -1820 290 -1820 {lab=vss}
C {lab_pin.sym} 290 -1820 2 0 {name=l9 sig_type=std_logic lab=vss}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 300 -1760 0 0 {name=XIRC1
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 260 -1760 240 -1760 {lab=d_rc}
C {lab_pin.sym} 240 -1760 0 0 {name=l10 sig_type=std_logic lab=d_rc}
N 340 -1760 360 -1760 {lab=d_rc_b}
C {lab_pin.sym} 360 -1760 2 0 {name=l11 sig_type=std_logic lab=d_rc_b}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 300 -1700 0 0 {name=XIRC2
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 260 -1700 240 -1700 {lab=d_rc_b}
C {lab_pin.sym} 240 -1700 0 0 {name=l12 sig_type=std_logic lab=d_rc_b}
N 340 -1700 360 -1700 {lab=d_dl[1]}
C {lab_pin.sym} 360 -1700 2 0 {name=l13 sig_type=std_logic lab=d_dl[1]}
C {sg13cmos5l_stdcells/sg13cmos5l_dlygate4sd3_1.sym} 300 -1630 0 0 {name=XDLY[3:2]
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 260 -1630 240 -1630 {lab=d_dl[2:1]}
C {lab_pin.sym} 240 -1630 0 0 {name=l14 sig_type=std_logic lab=d_dl[2:1]}
N 340 -1630 360 -1630 {lab=d_dl[3:2]}
C {lab_pin.sym} 360 -1630 2 0 {name=l15 sig_type=std_logic lab=d_dl[3:2]}
T {ph1 = d_dl[2], ph2 = d_dl[3]} 120 -1600 0 0 0.3 0.3 {}
C {sg13cmos5l_stdcells/sg13cmos5l_and2_1.sym} 300 -1520 0 0 {name=XAPH
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 240 -1540 220 -1540 {lab=d_dl[2]}
C {lab_pin.sym} 220 -1540 0 0 {name=l16 sig_type=std_logic lab=d_dl[2]}
N 240 -1500 220 -1500 {lab=d_dl[3]}
C {lab_pin.sym} 220 -1500 0 0 {name=l17 sig_type=std_logic lab=d_dl[3]}
N 360 -1520 380 -1520 {lab=d_p12}
C {lab_pin.sym} 380 -1520 2 0 {name=l18 sig_type=std_logic lab=d_p12}
C {sg13cmos5l_stdcells/sg13cmos5l_and2_1.sym} 300 -1420 0 0 {name=XAPHE
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 240 -1440 220 -1440 {lab=d_p12}
C {lab_pin.sym} 220 -1440 0 0 {name=l19 sig_type=std_logic lab=d_p12}
N 240 -1400 220 -1400 {lab=di_dith_en}
C {lab_pin.sym} 220 -1400 0 0 {name=l20 sig_type=std_logic lab=di_dith_en}
N 360 -1420 380 -1420 {lab=d_ph}
C {lab_pin.sym} 380 -1420 2 0 {name=l21 sig_type=std_logic lab=d_ph}
C {sg13cmos5l_stdcells/sg13cmos5l_nor2_1.sym} 300 -1320 0 0 {name=XNORBI
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 240 -1340 220 -1340 {lab=d_dl[2]}
C {lab_pin.sym} 220 -1340 0 0 {name=l22 sig_type=std_logic lab=d_dl[2]}
N 240 -1300 220 -1300 {lab=d_dl[3]}
C {lab_pin.sym} 220 -1300 0 0 {name=l23 sig_type=std_logic lab=d_dl[3]}
N 360 -1320 380 -1320 {lab=d_nph}
C {lab_pin.sym} 380 -1320 2 0 {name=l24 sig_type=std_logic lab=d_nph}
C {sg13cmos5l_stdcells/sg13cmos5l_and2_1.sym} 300 -1220 0 0 {name=XABVI
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 240 -1240 220 -1240 {lab=d_nph}
C {lab_pin.sym} 220 -1240 0 0 {name=l25 sig_type=std_logic lab=d_nph}
N 240 -1200 220 -1200 {lab=di_dith_en}
C {lab_pin.sym} 220 -1200 0 0 {name=l26 sig_type=std_logic lab=di_dith_en}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 520 -1220 0 0 {name=XIBVI
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 360 -1220 480 -1220 {lab=d_bvi}
N 560 -1220 580 -1220 {lab=d_bvi_b}
C {lab_pin.sym} 580 -1220 2 0 {name=l27 sig_type=std_logic lab=d_bvi_b}
N 420 -1220 420 -1240 {lab=d_bvi}
C {lab_pin.sym} 420 -1240 3 0 {name=l28 sig_type=std_logic lab=d_bvi}
C {sg13cmos5l_stdcells/sg13cmos5l_or2_1.sym} 300 -1120 0 0 {name=XOBVC
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 240 -1140 220 -1140 {lab=d_p12}
C {lab_pin.sym} 220 -1140 0 0 {name=l29 sig_type=std_logic lab=d_p12}
N 240 -1100 220 -1100 {lab=d_en_b}
C {lab_pin.sym} 220 -1100 0 0 {name=l30 sig_type=std_logic lab=d_en_b}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 520 -1120 0 0 {name=XIBVC
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 360 -1120 480 -1120 {lab=d_bvc}
N 560 -1120 580 -1120 {lab=d_bvc_b}
C {lab_pin.sym} 580 -1120 2 0 {name=l31 sig_type=std_logic lab=d_bvc_b}
N 420 -1120 420 -1140 {lab=d_bvc}
C {lab_pin.sym} 420 -1140 3 0 {name=l32 sig_type=std_logic lab=d_bvc}
T {Bit k high: q-side gate on vh, p-side gate on vl, only while d_ph is high} 120 -1050 0 0 0.3 0.3 {}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 300 -1000 0 0 {name=XINVB[2:0]
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 260 -1000 240 -1000 {lab=di_dith[2:0]}
C {ipin.sym} 240 -1000 0 0 {name=p33 lab=di_dith[2:0]}
N 340 -1000 360 -1000 {lab=d_bb[2:0]}
C {lab_pin.sym} 360 -1000 2 0 {name=l34 sig_type=std_logic lab=d_bb[2:0]}
C {sg13cmos5l_stdcells/sg13cmos5l_nand2_1.sym} 300 -900 0 0 {name=XNA1[2:0]
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 240 -920 220 -920 {lab=d_ph}
C {lab_pin.sym} 220 -920 0 0 {name=l35 sig_type=std_logic lab=d_ph}
N 240 -880 220 -880 {lab=di_dith[2:0]}
C {lab_pin.sym} 220 -880 0 0 {name=l36 sig_type=std_logic lab=di_dith[2:0]}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 520 -900 0 0 {name=XIA1[2:0]
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 360 -900 480 -900 {lab=d_c1_b[2:0]}
N 560 -900 580 -900 {lab=d_c1[2:0]}
C {lab_pin.sym} 580 -900 2 0 {name=l37 sig_type=std_logic lab=d_c1[2:0]}
N 420 -900 420 -920 {lab=d_c1_b[2:0]}
C {lab_pin.sym} 420 -920 3 0 {name=l38 sig_type=std_logic lab=d_c1_b[2:0]}
C {sg13cmos5l_stdcells/sg13cmos5l_nand2_1.sym} 300 -800 0 0 {name=XNA0[2:0]
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 240 -820 220 -820 {lab=d_ph}
C {lab_pin.sym} 220 -820 0 0 {name=l39 sig_type=std_logic lab=d_ph}
N 240 -780 220 -780 {lab=d_bb[2:0]}
C {lab_pin.sym} 220 -780 0 0 {name=l40 sig_type=std_logic lab=d_bb[2:0]}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 520 -800 0 0 {name=XIA0[2:0]
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 360 -800 480 -800 {lab=d_c0_b[2:0]}
N 560 -800 580 -800 {lab=d_c0[2:0]}
C {lab_pin.sym} 580 -800 2 0 {name=l41 sig_type=std_logic lab=d_c0[2:0]}
N 420 -800 420 -820 {lab=d_c0_b[2:0]}
C {lab_pin.sym} 420 -820 3 0 {name=l42 sig_type=std_logic lab=d_c0_b[2:0]}
T {Amplitude select, decoded in quantizer2_lfsr: s[0] 100 %, s[1] 67 %, s[2] 133 %, s[3] 33 %} 120 -730 0 0 0.3 0.3 {}
C {ipin.sym} 300 -680 0 0 {name=p43 lab=di_amp_s[3:0]}
N 300 -680 320 -680 {lab=di_amp_s[3:0]}
C {lab_pin.sym} 320 -680 2 0 {name=l44 sig_type=std_logic lab=di_amp_s[3:0]}
C {ipin.sym} 300 -620 0 0 {name=p45 lab=di_amp_s_b[3:0]}
N 300 -620 320 -620 {lab=di_amp_s_b[3:0]}
C {lab_pin.sym} 320 -620 2 0 {name=l46 sig_type=std_logic lab=di_amp_s_b[3:0]}
T {rhigh ladder, centre tap t20 = vc} 860 -2180 0 0 0.5 0.5 {}
C {sg13_lv_pmos.sym} 980 -2060 0 0 {name=MPLAD
l=0.5u
w=1u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 960 -2060 940 -2060 {lab=d_enl_b}
C {lab_pin.sym} 940 -2060 0 0 {name=l47 sig_type=std_logic lab=d_enl_b}
N 1000 -2090 1000 -2120 {lab=vdd}
C {lab_pin.sym} 1000 -2120 3 0 {name=l48 sig_type=std_logic lab=vdd}
N 1000 -2060 1040 -2060 {lab=vdd}
C {lab_pin.sym} 1040 -2060 2 0 {name=l49 sig_type=std_logic lab=vdd}
C {rhigh.sym} 1000 -1960 0 0 {name=RTOP
w=0.5e-6
l=80.4e-6
model=rhigh
body=vss
spiceprefix=X
b=0
m=1
}
N 1000 -2030 1000 -1990 {lab=v_rt}
C {rhigh.sym} 1000 -1860 0 0 {name=RL[7:0]
w=0.5e-6
l=4.08e-6
model=rhigh
body=vss
spiceprefix=X
b=0
m=1
}
N 1000 -1930 1020 -1930 {lab=t[24]}
C {lab_pin.sym} 1020 -1930 2 0 {name=l50 sig_type=std_logic lab=t[24]}
N 1000 -1890 1020 -1890 {lab=t[24:17]}
C {lab_pin.sym} 1020 -1890 2 0 {name=l51 sig_type=std_logic lab=t[24:17]}
N 1000 -1830 1020 -1830 {lab=t[23:16]}
C {lab_pin.sym} 1020 -1830 2 0 {name=l52 sig_type=std_logic lab=t[23:16]}
C {rhigh.sym} 1000 -1700 0 0 {name=RBOT
w=0.5e-6
l=80.4e-6
model=rhigh
body=vss
spiceprefix=X
b=0
m=1
}
N 1000 -1730 1020 -1730 {lab=t[16]}
C {lab_pin.sym} 1020 -1730 2 0 {name=l53 sig_type=std_logic lab=t[16]}
N 1000 -1670 1000 -1650 {lab=vss}
C {lab_pin.sym} 1000 -1650 1 0 {name=l54 sig_type=std_logic lab=vss}
T {taps t24 .. t16, one 3.83 um unit each, RTOP / RBOT 80.4 um (8 x 10.05), about 2.8 uA} 860 -1640 0 0 0.3 0.3 {}
T {Layout twins of the singles: MCDLYD (right, gate vdd: a decap), MPLADD (left, all on vdd)} 860 -1040 0 0 0.25 0.25 {}
C {sg13_lv_nmos.sym} 980 -960 0 0 {name=MCDLYD
l=1u
w=7u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 960 -960 940 -960 {lab=vdd}
C {lab_pin.sym} 940 -960 0 0 {name=l55 sig_type=std_logic lab=vdd}
N 1000 -990 1020 -990 {lab=vss}
C {lab_pin.sym} 1020 -990 2 0 {name=l56 sig_type=std_logic lab=vss}
N 1000 -930 1020 -930 {lab=vss}
C {lab_pin.sym} 1020 -930 2 0 {name=l57 sig_type=std_logic lab=vss}
N 1000 -960 1020 -960 {lab=vss}
C {lab_pin.sym} 1020 -960 2 0 {name=l58 sig_type=std_logic lab=vss}
C {sg13_lv_pmos.sym} 1200 -960 0 0 {name=MPLADD
l=0.5u
w=1u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 1180 -960 1160 -960 {lab=vdd}
C {lab_pin.sym} 1160 -960 0 0 {name=l59 sig_type=std_logic lab=vdd}
N 1220 -930 1240 -930 {lab=vdd}
C {lab_pin.sym} 1240 -930 2 0 {name=l60 sig_type=std_logic lab=vdd}
N 1220 -990 1240 -990 {lab=vdd}
C {lab_pin.sym} 1240 -990 2 0 {name=l61 sig_type=std_logic lab=vdd}
N 1220 -960 1240 -960 {lab=vdd}
C {lab_pin.sym} 1240 -960 2 0 {name=l62 sig_type=std_logic lab=vdd}
C {rhigh.sym} 1200 -1860 0 0 {name=RDUM[1:0]
w=0.5e-6
l=10.05e-6
model=rhigh
body=vss
spiceprefix=X
b=0
m=1
}
N 1200 -1890 1220 -1890 {lab=vss}
C {lab_pin.sym} 1220 -1890 2 0 {name=l63 sig_type=std_logic lab=vss}
N 1200 -1830 1220 -1830 {lab=vss}
C {lab_pin.sym} 1220 -1830 2 0 {name=l64 sig_type=std_logic lab=vss}
C {rhigh.sym} 1340 -1860 0 0 {name=RDUMT[1:0]
w=0.5e-6
l=20e-6
model=rhigh
body=vss
spiceprefix=X
b=0
m=1
}
N 1340 -1890 1360 -1890 {lab=vss}
C {lab_pin.sym} 1360 -1890 2 0 {name=l65 sig_type=std_logic lab=vss}
N 1340 -1830 1360 -1830 {lab=vss}
C {lab_pin.sym} 1360 -1830 2 0 {name=l66 sig_type=std_logic lab=vss}
T {stripe dummies} 1140 -1800 0 0 0.25 0.25 {}
C {sg13_lv_nmos.sym} 1020 -1520 1 0 {name=MAMHN[3:0]
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13_lv_pmos.sym} 1020 -1420 1 1 {name=MAMHP[3:0]
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 990 -1500 970 -1500 {lab=t[21],t[24],t[22],t[23]}
N 990 -1440 970 -1440 {lab=t[21],t[24],t[22],t[23]}
N 970 -1500 970 -1440 {lab=t[21],t[24],t[22],t[23]}
N 1050 -1500 1070 -1500 {lab=vh}
N 1050 -1440 1070 -1440 {lab=vh}
N 1070 -1500 1070 -1440 {lab=vh}
N 970 -1500 950 -1500 {lab=t[21],t[24],t[22],t[23]}
C {lab_pin.sym} 950 -1500 0 0 {name=l67 sig_type=std_logic lab=t[21],t[24],t[22],t[23]}
N 1070 -1500 1090 -1500 {lab=vh}
C {lab_pin.sym} 1090 -1500 2 0 {name=l68 sig_type=std_logic lab=vh}
N 1020 -1540 1020 -1560 {lab=di_amp_s[3:0]}
C {lab_pin.sym} 1020 -1560 3 0 {name=l69 sig_type=std_logic lab=di_amp_s[3:0]}
N 1020 -1400 1020 -1380 {lab=di_amp_s_b[3:0]}
C {lab_pin.sym} 1020 -1380 1 0 {name=l70 sig_type=std_logic lab=di_amp_s_b[3:0]}
N 1020 -1500 1020 -1490 {lab=vss}
C {lab_pin.sym} 1020 -1490 1 0 {name=l71 sig_type=std_logic lab=vss}
N 1020 -1440 1020 -1450 {lab=vdd}
C {lab_pin.sym} 1020 -1450 3 0 {name=l72 sig_type=std_logic lab=vdd}
C {sg13_lv_nmos.sym} 1020 -1260 1 0 {name=MAMLN[3:0]
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13_lv_pmos.sym} 1020 -1160 1 1 {name=MAMLP[3:0]
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 990 -1240 970 -1240 {lab=t[19],t[16],t[18],t[17]}
N 990 -1180 970 -1180 {lab=t[19],t[16],t[18],t[17]}
N 970 -1240 970 -1180 {lab=t[19],t[16],t[18],t[17]}
N 1050 -1240 1070 -1240 {lab=vl}
N 1050 -1180 1070 -1180 {lab=vl}
N 1070 -1240 1070 -1180 {lab=vl}
N 970 -1240 950 -1240 {lab=t[19],t[16],t[18],t[17]}
C {lab_pin.sym} 950 -1240 0 0 {name=l73 sig_type=std_logic lab=t[19],t[16],t[18],t[17]}
N 1070 -1240 1090 -1240 {lab=vl}
C {lab_pin.sym} 1090 -1240 2 0 {name=l74 sig_type=std_logic lab=vl}
N 1020 -1280 1020 -1300 {lab=di_amp_s[3:0]}
C {lab_pin.sym} 1020 -1300 3 0 {name=l75 sig_type=std_logic lab=di_amp_s[3:0]}
N 1020 -1140 1020 -1120 {lab=di_amp_s_b[3:0]}
C {lab_pin.sym} 1020 -1120 1 0 {name=l76 sig_type=std_logic lab=di_amp_s_b[3:0]}
N 1020 -1240 1020 -1230 {lab=vss}
C {lab_pin.sym} 1020 -1230 1 0 {name=l77 sig_type=std_logic lab=vss}
N 1020 -1180 1020 -1190 {lab=vdd}
C {lab_pin.sym} 1020 -1190 3 0 {name=l78 sig_type=std_logic lab=vdd}
T {vc = t20 (ladder centre)} 860 -1120 0 0 0.3 0.3 {}
T {Aux gates: on vh / vl while d_ph is high, floating on Cf over their own input while it is low} 1500 -2180 0 0 0.5 0.5 {}
C {sg13_lv_nmos.sym} 1700 -2060 1 0 {name=MGQHN[2:0]
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13_lv_pmos.sym} 1700 -1960 1 1 {name=MGQHP[2:0]
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 1670 -2040 1650 -2040 {lab=vh}
N 1670 -1980 1650 -1980 {lab=vh}
N 1650 -2040 1650 -1980 {lab=vh}
N 1730 -2040 1750 -2040 {lab=vg_q[2:0]}
N 1730 -1980 1750 -1980 {lab=vg_q[2:0]}
N 1750 -2040 1750 -1980 {lab=vg_q[2:0]}
N 1650 -2040 1630 -2040 {lab=vh}
C {lab_pin.sym} 1630 -2040 0 0 {name=l79 sig_type=std_logic lab=vh}
N 1750 -2040 1770 -2040 {lab=vg_q[2:0]}
C {lab_pin.sym} 1770 -2040 2 0 {name=l80 sig_type=std_logic lab=vg_q[2:0]}
N 1700 -2080 1700 -2100 {lab=d_c1[2:0]}
C {lab_pin.sym} 1700 -2100 3 0 {name=l81 sig_type=std_logic lab=d_c1[2:0]}
N 1700 -1940 1700 -1920 {lab=d_c1_b[2:0]}
C {lab_pin.sym} 1700 -1920 1 0 {name=l82 sig_type=std_logic lab=d_c1_b[2:0]}
N 1700 -2040 1700 -2030 {lab=vss}
C {lab_pin.sym} 1700 -2030 1 0 {name=l83 sig_type=std_logic lab=vss}
N 1700 -1980 1700 -1990 {lab=vdd}
C {lab_pin.sym} 1700 -1990 3 0 {name=l84 sig_type=std_logic lab=vdd}
C {sg13_lv_nmos.sym} 1700 -1800 1 0 {name=MGQLN[2:0]
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13_lv_pmos.sym} 1700 -1700 1 1 {name=MGQLP[2:0]
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 1670 -1780 1650 -1780 {lab=vl}
N 1670 -1720 1650 -1720 {lab=vl}
N 1650 -1780 1650 -1720 {lab=vl}
N 1730 -1780 1750 -1780 {lab=vg_q[2:0]}
N 1730 -1720 1750 -1720 {lab=vg_q[2:0]}
N 1750 -1780 1750 -1720 {lab=vg_q[2:0]}
N 1650 -1780 1630 -1780 {lab=vl}
C {lab_pin.sym} 1630 -1780 0 0 {name=l85 sig_type=std_logic lab=vl}
N 1750 -1780 1770 -1780 {lab=vg_q[2:0]}
C {lab_pin.sym} 1770 -1780 2 0 {name=l86 sig_type=std_logic lab=vg_q[2:0]}
N 1700 -1820 1700 -1840 {lab=d_c0[2:0]}
C {lab_pin.sym} 1700 -1840 3 0 {name=l87 sig_type=std_logic lab=d_c0[2:0]}
N 1700 -1680 1700 -1660 {lab=d_c0_b[2:0]}
C {lab_pin.sym} 1700 -1660 1 0 {name=l88 sig_type=std_logic lab=d_c0_b[2:0]}
N 1700 -1780 1700 -1770 {lab=vss}
C {lab_pin.sym} 1700 -1770 1 0 {name=l89 sig_type=std_logic lab=vss}
N 1700 -1720 1700 -1730 {lab=vdd}
C {lab_pin.sym} 1700 -1730 3 0 {name=l90 sig_type=std_logic lab=vdd}
C {sg13_lv_nmos.sym} 1700 -1540 1 0 {name=MGPHN[2:0]
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13_lv_pmos.sym} 1700 -1440 1 1 {name=MGPHP[2:0]
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 1670 -1520 1650 -1520 {lab=vh}
N 1670 -1460 1650 -1460 {lab=vh}
N 1650 -1520 1650 -1460 {lab=vh}
N 1730 -1520 1750 -1520 {lab=vg_p[2:0]}
N 1730 -1460 1750 -1460 {lab=vg_p[2:0]}
N 1750 -1520 1750 -1460 {lab=vg_p[2:0]}
N 1650 -1520 1630 -1520 {lab=vh}
C {lab_pin.sym} 1630 -1520 0 0 {name=l91 sig_type=std_logic lab=vh}
N 1750 -1520 1770 -1520 {lab=vg_p[2:0]}
C {lab_pin.sym} 1770 -1520 2 0 {name=l92 sig_type=std_logic lab=vg_p[2:0]}
N 1700 -1560 1700 -1580 {lab=d_c0[2:0]}
C {lab_pin.sym} 1700 -1580 3 0 {name=l93 sig_type=std_logic lab=d_c0[2:0]}
N 1700 -1420 1700 -1400 {lab=d_c0_b[2:0]}
C {lab_pin.sym} 1700 -1400 1 0 {name=l94 sig_type=std_logic lab=d_c0_b[2:0]}
N 1700 -1520 1700 -1510 {lab=vss}
C {lab_pin.sym} 1700 -1510 1 0 {name=l95 sig_type=std_logic lab=vss}
N 1700 -1460 1700 -1470 {lab=vdd}
C {lab_pin.sym} 1700 -1470 3 0 {name=l96 sig_type=std_logic lab=vdd}
C {sg13_lv_nmos.sym} 1700 -1280 1 0 {name=MGPLN[2:0]
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13_lv_pmos.sym} 1700 -1180 1 1 {name=MGPLP[2:0]
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 1670 -1260 1650 -1260 {lab=vl}
N 1670 -1200 1650 -1200 {lab=vl}
N 1650 -1260 1650 -1200 {lab=vl}
N 1730 -1260 1750 -1260 {lab=vg_p[2:0]}
N 1730 -1200 1750 -1200 {lab=vg_p[2:0]}
N 1750 -1260 1750 -1200 {lab=vg_p[2:0]}
N 1650 -1260 1630 -1260 {lab=vl}
C {lab_pin.sym} 1630 -1260 0 0 {name=l97 sig_type=std_logic lab=vl}
N 1750 -1260 1770 -1260 {lab=vg_p[2:0]}
C {lab_pin.sym} 1770 -1260 2 0 {name=l98 sig_type=std_logic lab=vg_p[2:0]}
N 1700 -1300 1700 -1320 {lab=d_c1[2:0]}
C {lab_pin.sym} 1700 -1320 3 0 {name=l99 sig_type=std_logic lab=d_c1[2:0]}
N 1700 -1160 1700 -1140 {lab=d_c1_b[2:0]}
C {lab_pin.sym} 1700 -1140 1 0 {name=l100 sig_type=std_logic lab=d_c1_b[2:0]}
N 1700 -1260 1700 -1250 {lab=vss}
C {lab_pin.sym} 1700 -1250 1 0 {name=l101 sig_type=std_logic lab=vss}
N 1700 -1200 1700 -1210 {lab=vdd}
C {lab_pin.sym} 1700 -1210 3 0 {name=l102 sig_type=std_logic lab=vdd}
C {sg13_lv_nmos.sym} 1680 -1000 0 0 {name=MPDQ[2:0]
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 1700 -1030 1720 -1030 {lab=vg_q[2:0]}
C {lab_pin.sym} 1720 -1030 2 0 {name=l103 sig_type=std_logic lab=vg_q[2:0]}
N 1660 -1000 1640 -1000 {lab=d_en_b}
C {lab_pin.sym} 1640 -1000 0 0 {name=l104 sig_type=std_logic lab=d_en_b}
N 1700 -970 1720 -970 {lab=vss}
C {lab_pin.sym} 1720 -970 2 0 {name=l105 sig_type=std_logic lab=vss}
N 1700 -1000 1710 -1000 {lab=vss}
C {lab_pin.sym} 1710 -1000 2 0 {name=l106 sig_type=std_logic lab=vss}
C {sg13_lv_nmos.sym} 1680 -860 0 0 {name=MPDP[2:0]
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 1700 -890 1720 -890 {lab=vg_p[2:0]}
C {lab_pin.sym} 1720 -890 2 0 {name=l107 sig_type=std_logic lab=vg_p[2:0]}
N 1660 -860 1640 -860 {lab=d_en_b}
C {lab_pin.sym} 1640 -860 0 0 {name=l108 sig_type=std_logic lab=d_en_b}
N 1700 -830 1720 -830 {lab=vss}
C {lab_pin.sym} 1720 -830 2 0 {name=l109 sig_type=std_logic lab=vss}
N 1700 -860 1710 -860 {lab=vss}
C {lab_pin.sym} 1710 -860 2 0 {name=l110 sig_type=std_logic lab=vss}
T {Cf: cap_cmomf w 7.6u (rows) x l 4.1u (fingers), 40.1 fF each, CFQD / CFPD layout dummies} 2050 -2180 0 0 0.3 0.3 {}
C {cap_cmomf.sym} 2150 -2040 0 0 {name=CFQ0
model=cap_cmomf
w=7.6e-6
l=4.1e-6
mmin=1
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
}
N 2150 -2070 2150 -2090 {lab=v_bq}
C {lab_pin.sym} 2150 -2090 3 0 {name=l111 sig_type=std_logic lab=v_bq}
N 2150 -2010 2150 -1990 {lab=vg_q[0]}
C {lab_pin.sym} 2150 -1990 1 0 {name=l112 sig_type=std_logic lab=vg_q[0]}
C {cap_cmomf.sym} 2270 -2040 0 0 {name=CFQ1[1:0]
model=cap_cmomf
w=7.6e-6
l=4.1e-6
mmin=1
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
}
N 2270 -2070 2270 -2090 {lab=v_bq}
C {lab_pin.sym} 2270 -2090 3 0 {name=l113 sig_type=std_logic lab=v_bq}
N 2270 -2010 2270 -1990 {lab=vg_q[1]}
C {lab_pin.sym} 2270 -1990 1 0 {name=l114 sig_type=std_logic lab=vg_q[1]}
C {cap_cmomf.sym} 2390 -2040 0 0 {name=CFQ2[1:0]
model=cap_cmomf
w=7.6e-6
l=4.1e-6
mmin=1
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
}
N 2390 -2070 2390 -2090 {lab=v_bq}
C {lab_pin.sym} 2390 -2090 3 0 {name=l115 sig_type=std_logic lab=v_bq}
N 2390 -2010 2390 -1990 {lab=vg_q[2]}
C {lab_pin.sym} 2390 -1990 1 0 {name=l116 sig_type=std_logic lab=vg_q[2]}
C {cap_cmomf.sym} 2510 -2040 0 0 {name=CFQ2[3:2]
model=cap_cmomf
w=7.6e-6
l=4.1e-6
mmin=1
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
}
N 2510 -2070 2510 -2090 {lab=vg_q[2]}
C {lab_pin.sym} 2510 -2090 3 0 {name=l117 sig_type=std_logic lab=vg_q[2]}
N 2510 -2010 2510 -1990 {lab=v_bq}
C {lab_pin.sym} 2510 -1990 1 0 {name=l118 sig_type=std_logic lab=v_bq}
C {cap_cmomf.sym} 2630 -2040 0 0 {name=CFQD
model=cap_cmomf
w=7.6e-6
l=4.1e-6
mmin=1
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
}
N 2630 -2070 2630 -2090 {lab=v_bq}
C {lab_pin.sym} 2630 -2090 3 0 {name=l119 sig_type=std_logic lab=v_bq}
N 2630 -2010 2630 -1990 {lab=v_bq}
C {lab_pin.sym} 2630 -1990 1 0 {name=l120 sig_type=std_logic lab=v_bq}
C {sg13_lv_nmos.sym} 2710 -1940 1 0 {name=MBCQN
l=0.13u
w=21u
ng=6
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13_lv_pmos.sym} 2710 -1840 1 1 {name=MBCQP
l=0.13u
w=21u
ng=6
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 2680 -1920 2660 -1920 {lab=v_bq}
N 2680 -1860 2660 -1860 {lab=v_bq}
N 2660 -1920 2660 -1860 {lab=v_bq}
N 2740 -1920 2760 -1920 {lab=t[20]}
N 2740 -1860 2760 -1860 {lab=t[20]}
N 2760 -1920 2760 -1860 {lab=t[20]}
N 2660 -1920 2640 -1920 {lab=v_bq}
C {lab_pin.sym} 2640 -1920 0 0 {name=l121 sig_type=std_logic lab=v_bq}
N 2760 -1920 2780 -1920 {lab=t[20]}
C {lab_pin.sym} 2780 -1920 2 0 {name=l122 sig_type=std_logic lab=t[20]}
N 2710 -1960 2710 -1980 {lab=d_bvc}
C {lab_pin.sym} 2710 -1980 3 0 {name=l123 sig_type=std_logic lab=d_bvc}
N 2710 -1820 2710 -1800 {lab=d_bvc_b}
C {lab_pin.sym} 2710 -1800 1 0 {name=l124 sig_type=std_logic lab=d_bvc_b}
N 2710 -1920 2710 -1910 {lab=vss}
C {lab_pin.sym} 2710 -1910 1 0 {name=l125 sig_type=std_logic lab=vss}
N 2710 -1860 2710 -1870 {lab=vdd}
C {lab_pin.sym} 2710 -1870 3 0 {name=l126 sig_type=std_logic lab=vdd}
C {sg13_lv_nmos.sym} 2710 -1680 1 0 {name=MBIQN
l=0.13u
w=21u
ng=6
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13_lv_pmos.sym} 2710 -1580 1 1 {name=MBIQP
l=0.13u
w=21u
ng=6
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 2680 -1660 2660 -1660 {lab=v_bq}
N 2680 -1600 2660 -1600 {lab=v_bq}
N 2660 -1660 2660 -1600 {lab=v_bq}
N 2740 -1660 2760 -1660 {lab=vi_p}
N 2740 -1600 2760 -1600 {lab=vi_p}
N 2760 -1660 2760 -1600 {lab=vi_p}
N 2660 -1660 2640 -1660 {lab=v_bq}
C {lab_pin.sym} 2640 -1660 0 0 {name=l127 sig_type=std_logic lab=v_bq}
N 2760 -1660 2780 -1660 {lab=vi_p}
C {lab_pin.sym} 2780 -1660 2 0 {name=l128 sig_type=std_logic lab=vi_p}
N 2710 -1700 2710 -1720 {lab=d_bvi}
C {lab_pin.sym} 2710 -1720 3 0 {name=l129 sig_type=std_logic lab=d_bvi}
N 2710 -1560 2710 -1540 {lab=d_bvi_b}
C {lab_pin.sym} 2710 -1540 1 0 {name=l130 sig_type=std_logic lab=d_bvi_b}
N 2710 -1660 2710 -1650 {lab=vss}
C {lab_pin.sym} 2710 -1650 1 0 {name=l131 sig_type=std_logic lab=vss}
N 2710 -1600 2710 -1610 {lab=vdd}
C {lab_pin.sym} 2710 -1610 3 0 {name=l132 sig_type=std_logic lab=vdd}
C {cap_cmomf.sym} 2150 -1480 0 0 {name=CFP0
model=cap_cmomf
w=7.6e-6
l=4.1e-6
mmin=1
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
}
N 2150 -1510 2150 -1530 {lab=vg_p[0]}
C {lab_pin.sym} 2150 -1530 3 0 {name=l133 sig_type=std_logic lab=vg_p[0]}
N 2150 -1450 2150 -1430 {lab=v_bp}
C {lab_pin.sym} 2150 -1430 1 0 {name=l134 sig_type=std_logic lab=v_bp}
C {cap_cmomf.sym} 2270 -1480 0 0 {name=CFP1[1:0]
model=cap_cmomf
w=7.6e-6
l=4.1e-6
mmin=1
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
}
N 2270 -1510 2270 -1530 {lab=vg_p[1]}
C {lab_pin.sym} 2270 -1530 3 0 {name=l135 sig_type=std_logic lab=vg_p[1]}
N 2270 -1450 2270 -1430 {lab=v_bp}
C {lab_pin.sym} 2270 -1430 1 0 {name=l136 sig_type=std_logic lab=v_bp}
C {cap_cmomf.sym} 2390 -1480 0 0 {name=CFP2[1:0]
model=cap_cmomf
w=7.6e-6
l=4.1e-6
mmin=1
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
}
N 2390 -1510 2390 -1530 {lab=vg_p[2]}
C {lab_pin.sym} 2390 -1530 3 0 {name=l137 sig_type=std_logic lab=vg_p[2]}
N 2390 -1450 2390 -1430 {lab=v_bp}
C {lab_pin.sym} 2390 -1430 1 0 {name=l138 sig_type=std_logic lab=v_bp}
C {cap_cmomf.sym} 2510 -1480 0 0 {name=CFP2[3:2]
model=cap_cmomf
w=7.6e-6
l=4.1e-6
mmin=1
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
}
N 2510 -1510 2510 -1530 {lab=v_bp}
C {lab_pin.sym} 2510 -1530 3 0 {name=l139 sig_type=std_logic lab=v_bp}
N 2510 -1450 2510 -1430 {lab=vg_p[2]}
C {lab_pin.sym} 2510 -1430 1 0 {name=l140 sig_type=std_logic lab=vg_p[2]}
C {cap_cmomf.sym} 2630 -1480 0 0 {name=CFPD
model=cap_cmomf
w=7.6e-6
l=4.1e-6
mmin=1
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
}
N 2630 -1510 2630 -1530 {lab=v_bp}
C {lab_pin.sym} 2630 -1530 3 0 {name=l141 sig_type=std_logic lab=v_bp}
N 2630 -1450 2630 -1430 {lab=v_bp}
C {lab_pin.sym} 2630 -1430 1 0 {name=l142 sig_type=std_logic lab=v_bp}
C {sg13_lv_nmos.sym} 2710 -1380 1 0 {name=MBCPN
l=0.13u
w=21u
ng=6
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13_lv_pmos.sym} 2710 -1280 1 1 {name=MBCPP
l=0.13u
w=21u
ng=6
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 2680 -1360 2660 -1360 {lab=v_bp}
N 2680 -1300 2660 -1300 {lab=v_bp}
N 2660 -1360 2660 -1300 {lab=v_bp}
N 2740 -1360 2760 -1360 {lab=t[20]}
N 2740 -1300 2760 -1300 {lab=t[20]}
N 2760 -1360 2760 -1300 {lab=t[20]}
N 2660 -1360 2640 -1360 {lab=v_bp}
C {lab_pin.sym} 2640 -1360 0 0 {name=l143 sig_type=std_logic lab=v_bp}
N 2760 -1360 2780 -1360 {lab=t[20]}
C {lab_pin.sym} 2780 -1360 2 0 {name=l144 sig_type=std_logic lab=t[20]}
N 2710 -1400 2710 -1420 {lab=d_bvc}
C {lab_pin.sym} 2710 -1420 3 0 {name=l145 sig_type=std_logic lab=d_bvc}
N 2710 -1260 2710 -1240 {lab=d_bvc_b}
C {lab_pin.sym} 2710 -1240 1 0 {name=l146 sig_type=std_logic lab=d_bvc_b}
N 2710 -1360 2710 -1350 {lab=vss}
C {lab_pin.sym} 2710 -1350 1 0 {name=l147 sig_type=std_logic lab=vss}
N 2710 -1300 2710 -1310 {lab=vdd}
C {lab_pin.sym} 2710 -1310 3 0 {name=l148 sig_type=std_logic lab=vdd}
C {sg13_lv_nmos.sym} 2710 -1120 1 0 {name=MBIPN
l=0.13u
w=21u
ng=6
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13_lv_pmos.sym} 2710 -1020 1 1 {name=MBIPP
l=0.13u
w=21u
ng=6
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 2680 -1100 2660 -1100 {lab=v_bp}
N 2680 -1040 2660 -1040 {lab=v_bp}
N 2660 -1100 2660 -1040 {lab=v_bp}
N 2740 -1100 2760 -1100 {lab=vi_n}
N 2740 -1040 2760 -1040 {lab=vi_n}
N 2760 -1100 2760 -1040 {lab=vi_n}
N 2660 -1100 2640 -1100 {lab=v_bp}
C {lab_pin.sym} 2640 -1100 0 0 {name=l149 sig_type=std_logic lab=v_bp}
N 2760 -1100 2780 -1100 {lab=vi_n}
C {lab_pin.sym} 2780 -1100 2 0 {name=l150 sig_type=std_logic lab=vi_n}
N 2710 -1140 2710 -1160 {lab=d_bvi}
C {lab_pin.sym} 2710 -1160 3 0 {name=l151 sig_type=std_logic lab=d_bvi}
N 2710 -1000 2710 -980 {lab=d_bvi_b}
C {lab_pin.sym} 2710 -980 1 0 {name=l152 sig_type=std_logic lab=d_bvi_b}
N 2710 -1100 2710 -1090 {lab=vss}
C {lab_pin.sym} 2710 -1090 1 0 {name=l153 sig_type=std_logic lab=vss}
N 2710 -1040 2710 -1050 {lab=vdd}
C {lab_pin.sym} 2710 -1050 3 0 {name=l154 sig_type=std_logic lab=vdd}
C {iopin.sym} 2450 -860 0 0 {name=p155 lab=vg_q[2:0]}
N 2450 -860 2430 -860 {lab=vg_q[2:0]}
C {lab_pin.sym} 2430 -860 0 0 {name=l156 sig_type=std_logic lab=vg_q[2:0]}
C {iopin.sym} 2450 -800 0 0 {name=p157 lab=vg_p[2:0]}
N 2450 -800 2430 -800 {lab=vg_p[2:0]}
C {lab_pin.sym} 2430 -800 0 0 {name=l158 sig_type=std_logic lab=vg_p[2:0]}
C {iopin.sym} 2450 -740 0 0 {name=p159 lab=vi_p}
N 2450 -740 2430 -740 {lab=vi_p}
C {lab_pin.sym} 2430 -740 0 0 {name=l160 sig_type=std_logic lab=vi_p}
C {iopin.sym} 2450 -680 0 0 {name=p161 lab=vi_n}
N 2450 -680 2430 -680 {lab=vi_n}
C {lab_pin.sym} 2430 -680 0 0 {name=l162 sig_type=std_logic lab=vi_n}
C {iopin.sym} 2450 -620 0 0 {name=p163 lab=vdd}
N 2450 -620 2430 -620 {lab=vdd}
C {lab_pin.sym} 2430 -620 0 0 {name=l164 sig_type=std_logic lab=vdd}
C {iopin.sym} 2450 -560 0 0 {name=p165 lab=vss}
N 2450 -560 2430 -560 {lab=vss}
C {lab_pin.sym} 2430 -560 0 0 {name=l166 sig_type=std_logic lab=vss}
C {title.sym} 160 -40 0 0 {name=l0 author="(c) 2026 Michael Koefinger"}
