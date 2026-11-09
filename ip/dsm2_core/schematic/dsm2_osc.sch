v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
T {dsm2_osc: on-chip clock for dsm2_core} 100 -2300 0 0 1.0 1.0 {}
T {-) steers ibias_test: di_osc_en low passes ibias_in to ibias_pad (PMOS MSP), high sends it into the ring (HV NMOS MSN, mirror MD)
-) 5 current-starved inverters, NMOS tails on vg and PMOS tails on vbp, a 6T Schmitt trigger restores the edges
-) a flip-flop divides the ring by 2 (50 % duty), the mux picks di_clk_ext (di_clk_sel low) or the oscillator (high), static settings
-) with di_osc_en low the tails are off, clamps hold the ring at the rails, the flip-flop is in reset and do_clk_osc is low
-) d_btest_or = d_btest_en OR d_osc_en enables the bias_gm test bank} 100 -2200 0 0 0.4 0.4 {}
T {Static inputs, 1.2 V in and 1.5 V out} 100 -1960 0 0 0.5 0.5 {}
C {ipin.sym} 120 -1800 0 0 {name=p1 lab=di_osc_en}
N 120 -1800 260 -1800 {}
C {dsm2_io_rx.sym} 300 -1800 0 0 {name=XRX0}
N 300 -1830 300 -1850 {}
C {lab_pin.sym} 300 -1850 1 0 {name=l2 sig_type=std_logic lab=vdd}
N 300 -1770 300 -1750 {}
C {lab_pin.sym} 300 -1750 3 0 {name=l3 sig_type=std_logic lab=vss}
N 340 -1800 400 -1800 {}
N 370 -1800 370 -1770 {}
C {lab_pin.sym} 370 -1770 3 0 {name=l4 sig_type=std_logic lab=d_osc_en_b}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 440 -1800 0 0 {name=XI0
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 480 -1800 540 -1800 {}
N 510 -1800 510 -1770 {}
C {lab_pin.sym} 510 -1770 3 0 {name=l5 sig_type=std_logic lab=d_osc_en}
C {ipin.sym} 120 -1600 0 0 {name=p6 lab=di_clk_sel}
N 120 -1600 260 -1600 {}
C {dsm2_io_rx.sym} 300 -1600 0 0 {name=XRX1}
N 300 -1630 300 -1650 {}
C {lab_pin.sym} 300 -1650 1 0 {name=l7 sig_type=std_logic lab=vdd}
N 300 -1570 300 -1550 {}
C {lab_pin.sym} 300 -1550 3 0 {name=l8 sig_type=std_logic lab=vss}
N 340 -1600 400 -1600 {}
N 370 -1600 370 -1570 {}
C {lab_pin.sym} 370 -1570 3 0 {name=l9 sig_type=std_logic lab=d_sel_b}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 440 -1600 0 0 {name=XI1
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 480 -1600 540 -1600 {}
N 510 -1600 510 -1570 {}
C {lab_pin.sym} 510 -1570 3 0 {name=l10 sig_type=std_logic lab=do_osc_oe}
N 540 -1600 600 -1600 {}
C {opin.sym} 600 -1600 0 0 {name=p11 lab=do_osc_oe}
T {Bank enable} 100 -1380 0 0 0.5 0.5 {}
C {ipin.sym} 120 -1300 0 0 {name=p12 lab=d_btest_en}
N 120 -1300 240 -1300 {}
C {sg13cmos5l_stdcells/sg13cmos5l_or2_1.sym} 300 -1280 0 0 {name=XBO
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 240 -1260 200 -1260 {}
C {lab_pin.sym} 200 -1260 0 0 {name=l13 sig_type=std_logic lab=d_osc_en}
N 360 -1280 440 -1280 {}
C {opin.sym} 440 -1280 0 0 {name=p14 lab=d_btest_or}
T {Current steering and bias} 640 -1960 0 0 0.5 0.5 {}
C {ipin.sym} 640 -1800 0 0 {name=p15 lab=ibias_in}
N 640 -1800 1140 -1800 {}
C {sg13_lv_pmos.sym} 760 -1720 0 0 {name=MSP
l=0.5u
w=1u
ng=1
m=2
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {MSP 1u/0.5u m2} 788 -1744 0 0 0.22 0.22 {}
N 780 -1750 780 -1800 {}
N 760 -1720 730 -1720 {}
C {lab_pin.sym} 730 -1720 0 0 {name=l16 sig_type=std_logic lab=d_osc_en}
N 780 -1720 810 -1720 {}
C {lab_pin.sym} 810 -1720 2 0 {name=l17 sig_type=std_logic lab=vdd}
N 780 -1690 780 -1640 {}
N 780 -1640 860 -1640 {}
C {opin.sym} 860 -1640 0 0 {name=p18 lab=ibias_pad}
C {sg13_hv_nmos.sym} 1100 -1720 0 0 {name=MSN
l=0.45u
w=1u
ng=1
m=1
model=sg13_hv_nmos
spiceprefix=X
hide_texts=true
}
T {MSN 1u/0.45u hv} 1128 -1744 0 0 0.22 0.22 {}
N 1120 -1750 1120 -1800 {}
N 1100 -1720 1070 -1720 {}
C {lab_pin.sym} 1070 -1720 0 0 {name=l19 sig_type=std_logic lab=d_osc_en}
N 1120 -1720 1150 -1720 {}
C {lab_pin.sym} 1150 -1720 2 0 {name=l20 sig_type=std_logic lab=vss}
N 1120 -1690 1120 -1620 {}
C {sg13_lv_nmos.sym} 1100 -1590 0 0 {name=MD
l=0.5u
w=0.5u
ng=1
m=2
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {MD 0.5u/0.5u m2} 1128 -1614 0 0 0.22 0.22 {}
N 1080 -1590 1040 -1590 {}
N 1040 -1590 1040 -1620 {}
N 1040 -1620 1120 -1620 {}
N 1120 -1590 1150 -1590 {}
C {lab_pin.sym} 1150 -1590 2 0 {name=l21 sig_type=std_logic lab=vss}
N 1120 -1560 1120 -1540 {}
C {lab_pin.sym} 1120 -1540 3 0 {name=l22 sig_type=std_logic lab=vss}
N 1120 -1620 1370 -1620 {}
N 1180 -1620 1180 -1650 {}
C {lab_pin.sym} 1180 -1650 1 0 {name=l23 sig_type=std_logic lab=vg}
C {sg13_lv_nmos.sym} 1390 -1590 0 0 {name=MGD
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {MGD 0.5u/0.5u} 1418 -1614 0 0 0.22 0.22 {}
N 1370 -1620 1410 -1620 {}
N 1390 -1590 1360 -1590 {}
C {lab_pin.sym} 1360 -1590 0 0 {name=l24 sig_type=std_logic lab=d_osc_en_b}
N 1410 -1590 1440 -1590 {}
C {lab_pin.sym} 1440 -1590 2 0 {name=l25 sig_type=std_logic lab=vss}
N 1410 -1560 1410 -1540 {}
C {lab_pin.sym} 1410 -1540 3 0 {name=l26 sig_type=std_logic lab=vss}
C {sg13_lv_nmos.sym} 1550 -1590 0 0 {name=M2
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {M2 0.5u/0.5u} 1578 -1614 0 0 0.22 0.22 {}
N 1530 -1590 1490 -1590 {}
N 1490 -1590 1490 -1670 {}
N 1490 -1670 1370 -1670 {}
N 1370 -1670 1370 -1620 {}
N 1570 -1590 1600 -1590 {}
C {lab_pin.sym} 1600 -1590 2 0 {name=l27 sig_type=std_logic lab=vss}
N 1570 -1560 1570 -1540 {}
C {lab_pin.sym} 1570 -1540 3 0 {name=l28 sig_type=std_logic lab=vss}
C {sg13_lv_pmos.sym} 1550 -1700 0 0 {name=MPD
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {MPD 0.5u/0.5u} 1578 -1724 0 0 0.22 0.22 {}
N 1570 -1670 1570 -1620 {}
N 1530 -1700 1510 -1700 {}
N 1510 -1700 1510 -1650 {}
N 1510 -1650 1570 -1650 {}
N 1570 -1700 1600 -1700 {}
C {lab_pin.sym} 1600 -1700 2 0 {name=l29 sig_type=std_logic lab=vdd}
N 1570 -1730 1570 -1750 {}
C {lab_pin.sym} 1570 -1750 1 0 {name=l30 sig_type=std_logic lab=vdd}
N 1570 -1650 1760 -1650 {}
N 1760 -1650 1790 -1650 {}
C {lab_pin.sym} 1790 -1650 2 0 {name=l31 sig_type=std_logic lab=vbp}
C {sg13_lv_pmos.sym} 1840 -1700 0 0 {name=MPK
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {MPK 0.5u/0.5u} 1868 -1724 0 0 0.22 0.22 {}
N 1860 -1670 1860 -1650 {}
N 1760 -1650 1860 -1650 {}
N 1840 -1700 1810 -1700 {}
C {lab_pin.sym} 1810 -1700 0 0 {name=l32 sig_type=std_logic lab=d_osc_en}
N 1860 -1700 1890 -1700 {}
C {lab_pin.sym} 1890 -1700 2 0 {name=l33 sig_type=std_logic lab=vdd}
N 1860 -1730 1860 -1750 {}
C {lab_pin.sym} 1860 -1750 1 0 {name=l34 sig_type=std_logic lab=vdd}
T {vg: MD diode, M2, MPD and the ring tails are one unit (W 0.5u, L 0.5u), MD m2, so each tail carries about half of ibias_in
M2 and MPD copy the current into vbp for the PMOS tails
MGD and MPK hold vg low and vbp high while di_osc_en is low} 640 -1400 0 0 0.3 0.3 {}
T {Current-starved ring, 5 stages} 2400 -2220 0 0 0.5 0.5 {}
N 2360 -2100 4100 -2100 {}
N 2360 -1860 4100 -1860 {}
C {iopin.sym} 2360 -2100 2 0 {name=p35 lab=vdd}
C {iopin.sym} 2360 -1860 2 0 {name=p36 lab=vss}
C {sg13_lv_pmos.sym} 2500 -2070 0 0 {name=XTP1
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XTP1 0.5u/0.5u} 2528 -2094 0 0 0.22 0.22 {}
C {sg13_lv_pmos.sym} 2500 -2010 0 0 {name=XP1
l=0.13u
w=1u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XP1 1u/0.13u} 2528 -2034 0 0 0.22 0.22 {}
C {sg13_lv_nmos.sym} 2500 -1950 0 0 {name=XN1
l=0.13u
w=1u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XN1 1u/0.13u} 2528 -1974 0 0 0.22 0.22 {}
C {sg13_lv_nmos.sym} 2500 -1890 0 0 {name=XTN1
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XTN1 0.5u/0.5u} 2528 -1914 0 0 0.22 0.22 {}
N 2520 -2070 2560 -2070 {}
N 2560 -2070 2560 -2100 {}
N 2520 -2010 2560 -2010 {}
N 2560 -2010 2560 -2070 {}
N 2520 -1950 2560 -1950 {}
N 2560 -1950 2560 -1860 {}
N 2520 -1890 2560 -1890 {}
N 2480 -2070 2460 -2070 {}
C {lab_pin.sym} 2460 -2070 0 0 {name=l37 sig_type=std_logic lab=vbp}
N 2480 -1890 2460 -1890 {}
C {lab_pin.sym} 2460 -1890 0 0 {name=l38 sig_type=std_logic lab=vg}
N 2480 -2010 2460 -2010 {}
N 2480 -1950 2460 -1950 {}
N 2460 -2010 2460 -1950 {}
N 2460 -1980 2420 -1980 {}
N 2520 -1980 2760 -1980 {}
N 2590 -1980 2590 -2040 {}
C {sg13_lv_nmos.sym} 2610 -2040 0 0 {name=XC1
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XC1 0.5u/0.5u} 2638 -2064 0 0 0.22 0.22 {}
N 2630 -2070 2650 -2070 {}
N 2650 -2070 2650 -2010 {}
N 2650 -2010 2630 -2010 {}
N 2630 -2040 2650 -2040 {}
N 2650 -2040 2670 -2040 {}
C {lab_pin.sym} 2670 -2040 2 0 {name=l39 sig_type=std_logic lab=vss}
N 2630 -1980 2630 -1950 {}
C {lab_pin.sym} 2630 -1950 3 0 {name=l40 sig_type=std_logic lab=n1}
C {sg13_lv_nmos.sym} 2500 -1740 0 0 {name=XK1
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XK1 0.5u/0.13u} 2528 -1764 0 0 0.22 0.22 {}
N 2520 -1770 2520 -1800 {}
C {lab_pin.sym} 2520 -1800 1 0 {name=l41 sig_type=std_logic lab=n1}
N 2480 -1740 2450 -1740 {}
C {lab_pin.sym} 2450 -1740 0 0 {name=l42 sig_type=std_logic lab=d_osc_en_b}
N 2520 -1740 2550 -1740 {}
C {lab_pin.sym} 2550 -1740 2 0 {name=l43 sig_type=std_logic lab=vss}
N 2520 -1710 2520 -1690 {}
C {lab_pin.sym} 2520 -1690 3 0 {name=l44 sig_type=std_logic lab=vss}
C {sg13_lv_pmos.sym} 2840 -2070 0 0 {name=XTP2
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XTP2 0.5u/0.5u} 2868 -2094 0 0 0.22 0.22 {}
C {sg13_lv_pmos.sym} 2840 -2010 0 0 {name=XP2
l=0.13u
w=1u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XP2 1u/0.13u} 2868 -2034 0 0 0.22 0.22 {}
C {sg13_lv_nmos.sym} 2840 -1950 0 0 {name=XN2
l=0.13u
w=1u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XN2 1u/0.13u} 2868 -1974 0 0 0.22 0.22 {}
C {sg13_lv_nmos.sym} 2840 -1890 0 0 {name=XTN2
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XTN2 0.5u/0.5u} 2868 -1914 0 0 0.22 0.22 {}
N 2860 -2070 2900 -2070 {}
N 2900 -2070 2900 -2100 {}
N 2860 -2010 2900 -2010 {}
N 2900 -2010 2900 -2070 {}
N 2860 -1950 2900 -1950 {}
N 2900 -1950 2900 -1860 {}
N 2860 -1890 2900 -1890 {}
N 2820 -2070 2800 -2070 {}
C {lab_pin.sym} 2800 -2070 0 0 {name=l45 sig_type=std_logic lab=vbp}
N 2820 -1890 2800 -1890 {}
C {lab_pin.sym} 2800 -1890 0 0 {name=l46 sig_type=std_logic lab=vg}
N 2820 -2010 2800 -2010 {}
N 2820 -1950 2800 -1950 {}
N 2800 -2010 2800 -1950 {}
N 2800 -1980 2760 -1980 {}
N 2860 -1980 3100 -1980 {}
N 2930 -1980 2930 -2040 {}
C {sg13_lv_nmos.sym} 2950 -2040 0 0 {name=XC2
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XC2 0.5u/0.5u} 2978 -2064 0 0 0.22 0.22 {}
N 2970 -2070 2990 -2070 {}
N 2990 -2070 2990 -2010 {}
N 2990 -2010 2970 -2010 {}
N 2970 -2040 2990 -2040 {}
N 2990 -2040 3010 -2040 {}
C {lab_pin.sym} 3010 -2040 2 0 {name=l47 sig_type=std_logic lab=vss}
N 2970 -1980 2970 -1950 {}
C {lab_pin.sym} 2970 -1950 3 0 {name=l48 sig_type=std_logic lab=n2}
C {sg13_lv_pmos.sym} 2840 -1740 0 0 {name=XK2
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XK2 0.5u/0.13u} 2868 -1764 0 0 0.22 0.22 {}
N 2860 -1770 2860 -1790 {}
C {lab_pin.sym} 2860 -1790 1 0 {name=l49 sig_type=std_logic lab=vdd}
N 2820 -1740 2790 -1740 {}
C {lab_pin.sym} 2790 -1740 0 0 {name=l50 sig_type=std_logic lab=d_osc_en}
N 2860 -1740 2890 -1740 {}
C {lab_pin.sym} 2890 -1740 2 0 {name=l51 sig_type=std_logic lab=vdd}
N 2860 -1710 2860 -1680 {}
C {lab_pin.sym} 2860 -1680 3 0 {name=l52 sig_type=std_logic lab=n2}
C {sg13_lv_pmos.sym} 3180 -2070 0 0 {name=XTP3
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XTP3 0.5u/0.5u} 3208 -2094 0 0 0.22 0.22 {}
C {sg13_lv_pmos.sym} 3180 -2010 0 0 {name=XP3
l=0.13u
w=1u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XP3 1u/0.13u} 3208 -2034 0 0 0.22 0.22 {}
C {sg13_lv_nmos.sym} 3180 -1950 0 0 {name=XN3
l=0.13u
w=1u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XN3 1u/0.13u} 3208 -1974 0 0 0.22 0.22 {}
C {sg13_lv_nmos.sym} 3180 -1890 0 0 {name=XTN3
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XTN3 0.5u/0.5u} 3208 -1914 0 0 0.22 0.22 {}
N 3200 -2070 3240 -2070 {}
N 3240 -2070 3240 -2100 {}
N 3200 -2010 3240 -2010 {}
N 3240 -2010 3240 -2070 {}
N 3200 -1950 3240 -1950 {}
N 3240 -1950 3240 -1860 {}
N 3200 -1890 3240 -1890 {}
N 3160 -2070 3140 -2070 {}
C {lab_pin.sym} 3140 -2070 0 0 {name=l53 sig_type=std_logic lab=vbp}
N 3160 -1890 3140 -1890 {}
C {lab_pin.sym} 3140 -1890 0 0 {name=l54 sig_type=std_logic lab=vg}
N 3160 -2010 3140 -2010 {}
N 3160 -1950 3140 -1950 {}
N 3140 -2010 3140 -1950 {}
N 3140 -1980 3100 -1980 {}
N 3200 -1980 3440 -1980 {}
N 3270 -1980 3270 -2040 {}
C {sg13_lv_nmos.sym} 3290 -2040 0 0 {name=XC3
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XC3 0.5u/0.5u} 3318 -2064 0 0 0.22 0.22 {}
N 3310 -2070 3330 -2070 {}
N 3330 -2070 3330 -2010 {}
N 3330 -2010 3310 -2010 {}
N 3310 -2040 3330 -2040 {}
N 3330 -2040 3350 -2040 {}
C {lab_pin.sym} 3350 -2040 2 0 {name=l55 sig_type=std_logic lab=vss}
N 3310 -1980 3310 -1950 {}
C {lab_pin.sym} 3310 -1950 3 0 {name=l56 sig_type=std_logic lab=n3}
C {sg13_lv_nmos.sym} 3180 -1740 0 0 {name=XK3
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XK3 0.5u/0.13u} 3208 -1764 0 0 0.22 0.22 {}
N 3200 -1770 3200 -1800 {}
C {lab_pin.sym} 3200 -1800 1 0 {name=l57 sig_type=std_logic lab=n3}
N 3160 -1740 3130 -1740 {}
C {lab_pin.sym} 3130 -1740 0 0 {name=l58 sig_type=std_logic lab=d_osc_en_b}
N 3200 -1740 3230 -1740 {}
C {lab_pin.sym} 3230 -1740 2 0 {name=l59 sig_type=std_logic lab=vss}
N 3200 -1710 3200 -1690 {}
C {lab_pin.sym} 3200 -1690 3 0 {name=l60 sig_type=std_logic lab=vss}
C {sg13_lv_pmos.sym} 3520 -2070 0 0 {name=XTP4
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XTP4 0.5u/0.5u} 3548 -2094 0 0 0.22 0.22 {}
C {sg13_lv_pmos.sym} 3520 -2010 0 0 {name=XP4
l=0.13u
w=1u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XP4 1u/0.13u} 3548 -2034 0 0 0.22 0.22 {}
C {sg13_lv_nmos.sym} 3520 -1950 0 0 {name=XN4
l=0.13u
w=1u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XN4 1u/0.13u} 3548 -1974 0 0 0.22 0.22 {}
C {sg13_lv_nmos.sym} 3520 -1890 0 0 {name=XTN4
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XTN4 0.5u/0.5u} 3548 -1914 0 0 0.22 0.22 {}
N 3540 -2070 3580 -2070 {}
N 3580 -2070 3580 -2100 {}
N 3540 -2010 3580 -2010 {}
N 3580 -2010 3580 -2070 {}
N 3540 -1950 3580 -1950 {}
N 3580 -1950 3580 -1860 {}
N 3540 -1890 3580 -1890 {}
N 3500 -2070 3480 -2070 {}
C {lab_pin.sym} 3480 -2070 0 0 {name=l61 sig_type=std_logic lab=vbp}
N 3500 -1890 3480 -1890 {}
C {lab_pin.sym} 3480 -1890 0 0 {name=l62 sig_type=std_logic lab=vg}
N 3500 -2010 3480 -2010 {}
N 3500 -1950 3480 -1950 {}
N 3480 -2010 3480 -1950 {}
N 3480 -1980 3440 -1980 {}
N 3540 -1980 3780 -1980 {}
N 3610 -1980 3610 -2040 {}
C {sg13_lv_nmos.sym} 3630 -2040 0 0 {name=XC4
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XC4 0.5u/0.5u} 3658 -2064 0 0 0.22 0.22 {}
N 3650 -2070 3670 -2070 {}
N 3670 -2070 3670 -2010 {}
N 3670 -2010 3650 -2010 {}
N 3650 -2040 3670 -2040 {}
N 3670 -2040 3690 -2040 {}
C {lab_pin.sym} 3690 -2040 2 0 {name=l63 sig_type=std_logic lab=vss}
N 3650 -1980 3650 -1950 {}
C {lab_pin.sym} 3650 -1950 3 0 {name=l64 sig_type=std_logic lab=n4}
C {sg13_lv_pmos.sym} 3520 -1740 0 0 {name=XK4
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XK4 0.5u/0.13u} 3548 -1764 0 0 0.22 0.22 {}
N 3540 -1770 3540 -1790 {}
C {lab_pin.sym} 3540 -1790 1 0 {name=l65 sig_type=std_logic lab=vdd}
N 3500 -1740 3470 -1740 {}
C {lab_pin.sym} 3470 -1740 0 0 {name=l66 sig_type=std_logic lab=d_osc_en}
N 3540 -1740 3570 -1740 {}
C {lab_pin.sym} 3570 -1740 2 0 {name=l67 sig_type=std_logic lab=vdd}
N 3540 -1710 3540 -1680 {}
C {lab_pin.sym} 3540 -1680 3 0 {name=l68 sig_type=std_logic lab=n4}
C {sg13_lv_pmos.sym} 3860 -2070 0 0 {name=XTP5
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XTP5 0.5u/0.5u} 3888 -2094 0 0 0.22 0.22 {}
C {sg13_lv_pmos.sym} 3860 -2010 0 0 {name=XP5
l=0.13u
w=1u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XP5 1u/0.13u} 3888 -2034 0 0 0.22 0.22 {}
C {sg13_lv_nmos.sym} 3860 -1950 0 0 {name=XN5
l=0.13u
w=1u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XN5 1u/0.13u} 3888 -1974 0 0 0.22 0.22 {}
C {sg13_lv_nmos.sym} 3860 -1890 0 0 {name=XTN5
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XTN5 0.5u/0.5u} 3888 -1914 0 0 0.22 0.22 {}
N 3880 -2070 3920 -2070 {}
N 3920 -2070 3920 -2100 {}
N 3880 -2010 3920 -2010 {}
N 3920 -2010 3920 -2070 {}
N 3880 -1950 3920 -1950 {}
N 3920 -1950 3920 -1860 {}
N 3880 -1890 3920 -1890 {}
N 3840 -2070 3820 -2070 {}
C {lab_pin.sym} 3820 -2070 0 0 {name=l69 sig_type=std_logic lab=vbp}
N 3840 -1890 3820 -1890 {}
C {lab_pin.sym} 3820 -1890 0 0 {name=l70 sig_type=std_logic lab=vg}
N 3840 -2010 3820 -2010 {}
N 3840 -1950 3820 -1950 {}
N 3820 -2010 3820 -1950 {}
N 3820 -1980 3780 -1980 {}
N 3880 -1980 4040 -1980 {}
N 3950 -1980 3950 -2040 {}
C {sg13_lv_nmos.sym} 3970 -2040 0 0 {name=XC5
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XC5 0.5u/0.5u} 3998 -2064 0 0 0.22 0.22 {}
N 3990 -2070 4010 -2070 {}
N 4010 -2070 4010 -2010 {}
N 4010 -2010 3990 -2010 {}
N 3990 -2040 4010 -2040 {}
N 4010 -2040 4030 -2040 {}
C {lab_pin.sym} 4030 -2040 2 0 {name=l71 sig_type=std_logic lab=vss}
N 3990 -1980 3990 -1950 {}
C {lab_pin.sym} 3990 -1950 3 0 {name=l72 sig_type=std_logic lab=n5}
C {sg13_lv_nmos.sym} 3860 -1740 0 0 {name=XK5
l=0.13u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XK5 0.5u/0.13u} 3888 -1764 0 0 0.22 0.22 {}
N 3880 -1770 3880 -1800 {}
C {lab_pin.sym} 3880 -1800 1 0 {name=l73 sig_type=std_logic lab=n5}
N 3840 -1740 3810 -1740 {}
C {lab_pin.sym} 3810 -1740 0 0 {name=l74 sig_type=std_logic lab=d_osc_en_b}
N 3880 -1740 3910 -1740 {}
C {lab_pin.sym} 3910 -1740 2 0 {name=l75 sig_type=std_logic lab=vss}
N 3880 -1710 3880 -1690 {}
C {lab_pin.sym} 3880 -1690 3 0 {name=l76 sig_type=std_logic lab=vss}
C {lab_pin.sym} 2420 -1980 0 0 {name=l77 sig_type=std_logic lab=n5}
C {lab_pin.sym} 4040 -1980 2 0 {name=l78 sig_type=std_logic lab=n5}
T {clamps: n1 n3 n5 to vss, n2 n4 to vdd while di_osc_en is low} 2500 -1625 0 0 0.3 0.3 {}
T {dummies, every terminal on one net, one at each end of each tail strip} 2500 -1550 0 0 0.3 0.3 {}
C {sg13_lv_nmos.sym} 2500 -1460 0 0 {name=XDN1
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XDN1 0.5u/0.5u} 2528 -1484 0 0 0.22 0.22 {}
N 2520 -1490 2550 -1490 {}
C {lab_pin.sym} 2550 -1490 2 0 {name=l79 sig_type=std_logic lab=vss}
N 2480 -1460 2450 -1460 {}
C {lab_pin.sym} 2450 -1460 0 0 {name=l80 sig_type=std_logic lab=vss}
N 2520 -1430 2550 -1430 {}
C {lab_pin.sym} 2550 -1430 2 0 {name=l81 sig_type=std_logic lab=vss}
N 2520 -1460 2550 -1460 {}
C {lab_pin.sym} 2550 -1460 2 0 {name=l82 sig_type=std_logic lab=vss}
C {sg13_lv_nmos.sym} 2700 -1460 0 0 {name=XDN2
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XDN2 0.5u/0.5u} 2728 -1484 0 0 0.22 0.22 {}
N 2720 -1490 2750 -1490 {}
C {lab_pin.sym} 2750 -1490 2 0 {name=l83 sig_type=std_logic lab=vss}
N 2680 -1460 2650 -1460 {}
C {lab_pin.sym} 2650 -1460 0 0 {name=l84 sig_type=std_logic lab=vss}
N 2720 -1430 2750 -1430 {}
C {lab_pin.sym} 2750 -1430 2 0 {name=l85 sig_type=std_logic lab=vss}
N 2720 -1460 2750 -1460 {}
C {lab_pin.sym} 2750 -1460 2 0 {name=l86 sig_type=std_logic lab=vss}
C {sg13_lv_pmos.sym} 2900 -1460 0 0 {name=XDP1
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XDP1 0.5u/0.5u} 2928 -1484 0 0 0.22 0.22 {}
N 2920 -1490 2950 -1490 {}
C {lab_pin.sym} 2950 -1490 2 0 {name=l87 sig_type=std_logic lab=vdd}
N 2880 -1460 2850 -1460 {}
C {lab_pin.sym} 2850 -1460 0 0 {name=l88 sig_type=std_logic lab=vdd}
N 2920 -1430 2950 -1430 {}
C {lab_pin.sym} 2950 -1430 2 0 {name=l89 sig_type=std_logic lab=vdd}
N 2920 -1460 2950 -1460 {}
C {lab_pin.sym} 2950 -1460 2 0 {name=l90 sig_type=std_logic lab=vdd}
C {sg13_lv_pmos.sym} 3100 -1460 0 0 {name=XDP2
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XDP2 0.5u/0.5u} 3128 -1484 0 0 0.22 0.22 {}
N 3120 -1490 3150 -1490 {}
C {lab_pin.sym} 3150 -1490 2 0 {name=l91 sig_type=std_logic lab=vdd}
N 3080 -1460 3050 -1460 {}
C {lab_pin.sym} 3050 -1460 0 0 {name=l92 sig_type=std_logic lab=vdd}
N 3120 -1430 3150 -1430 {}
C {lab_pin.sym} 3150 -1430 2 0 {name=l93 sig_type=std_logic lab=vdd}
N 3120 -1460 3150 -1460 {}
C {lab_pin.sym} 3150 -1460 2 0 {name=l94 sig_type=std_logic lab=vdd}
T {Schmitt restore, divide by 2, clock select} 4260 -2220 0 0 0.5 0.5 {}
N 4260 -2100 4740 -2100 {}
N 4260 -1860 4740 -1860 {}
C {lab_pin.sym} 4260 -2100 0 0 {name=l95 sig_type=std_logic lab=vdd}
C {lab_pin.sym} 4260 -1860 0 0 {name=l96 sig_type=std_logic lab=vss}
C {sg13_lv_pmos.sym} 4360 -2070 0 0 {name=XSP1
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XSP1 0.5u/0.5u} 4388 -2094 0 0 0.22 0.22 {}
C {sg13_lv_pmos.sym} 4360 -2010 0 0 {name=XSP2
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XSP2 0.5u/0.5u} 4388 -2034 0 0 0.22 0.22 {}
C {sg13_lv_nmos.sym} 4360 -1950 0 0 {name=XSN2
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XSN2 0.5u/0.5u} 4388 -1974 0 0 0.22 0.22 {}
C {sg13_lv_nmos.sym} 4360 -1890 0 0 {name=XSN1
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XSN1 0.5u/0.5u} 4388 -1914 0 0 0.22 0.22 {}
N 4380 -2070 4450 -2070 {}
N 4450 -2070 4450 -2100 {}
N 4380 -2010 4450 -2010 {}
N 4450 -2010 4450 -2070 {}
N 4380 -1950 4450 -1950 {}
N 4450 -1950 4450 -1860 {}
N 4380 -1890 4450 -1890 {}
N 4340 -2070 4320 -2070 {}
N 4340 -2010 4320 -2010 {}
N 4340 -1950 4320 -1950 {}
N 4340 -1890 4320 -1890 {}
N 4320 -2070 4320 -1890 {}
N 4320 -1980 4290 -1980 {}
C {lab_pin.sym} 4290 -1980 0 0 {name=l97 sig_type=std_logic lab=n5}
C {lab_pin.sym} 4380 -1980 2 0 {name=l98 sig_type=std_logic lab=r1}
C {lab_pin.sym} 4380 -2040 2 0 {name=l99 sig_type=std_logic lab=sa}
C {lab_pin.sym} 4380 -1920 2 0 {name=l100 sig_type=std_logic lab=sb}
C {sg13_lv_pmos.sym} 4580 -2010 0 0 {name=XSP3
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
hide_texts=true
}
T {XSP3 0.5u/0.5u} 4608 -2034 0 0 0.22 0.22 {}
C {lab_pin.sym} 4560 -2010 0 0 {name=l101 sig_type=std_logic lab=r1}
C {lab_pin.sym} 4600 -2040 2 0 {name=l102 sig_type=std_logic lab=sa}
C {lab_pin.sym} 4600 -1980 2 0 {name=l103 sig_type=std_logic lab=vss}
N 4600 -2010 4640 -2010 {}
N 4640 -2010 4640 -2100 {}
C {sg13_lv_nmos.sym} 4580 -1900 0 0 {name=XSN3
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
hide_texts=true
}
T {XSN3 0.5u/0.5u} 4608 -1924 0 0 0.22 0.22 {}
C {lab_pin.sym} 4560 -1900 0 0 {name=l104 sig_type=std_logic lab=r1}
C {lab_pin.sym} 4600 -1930 2 0 {name=l105 sig_type=std_logic lab=vdd}
C {lab_pin.sym} 4600 -1870 2 0 {name=l106 sig_type=std_logic lab=sb}
N 4600 -1900 4640 -1900 {}
N 4640 -1900 4640 -1860 {}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 4340 -1720 0 0 {name=XR3
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 4300 -1720 4270 -1720 {}
C {lab_pin.sym} 4270 -1720 0 0 {name=l107 sig_type=std_logic lab=r1}
C {sg13cmos5l_stdcells/sg13cmos5l_dfrbp_1.sym} 4560 -1680 0 0 {name=XFF
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 4380 -1720 4420 -1720 {}
N 4420 -1720 4420 -1700 {}
N 4420 -1700 4470 -1700 {}
N 4650 -1680 4680 -1680 {}
N 4680 -1680 4680 -1620 {}
N 4680 -1620 4450 -1620 {}
N 4450 -1620 4450 -1680 {}
N 4450 -1680 4470 -1680 {}
N 4470 -1660 4430 -1660 {}
C {lab_pin.sym} 4430 -1660 0 0 {name=l108 sig_type=std_logic lab=d_osc_en}
N 4650 -1700 4700 -1700 {}
N 4700 -1700 4730 -1700 {}
C {lab_pin.sym} 4730 -1700 2 0 {name=l109 sig_type=std_logic lab=q}
C {ipin.sym} 4300 -1500 0 0 {name=p110 lab=di_clk_ext}
N 4300 -1500 4360 -1500 {}
C {sg13cmos5l_stdcells/sg13cmos5l_mux2_1.sym} 4400 -1480 0 0 {name=XMUX
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 4360 -1460 4330 -1460 {}
C {lab_pin.sym} 4330 -1460 0 0 {name=l111 sig_type=std_logic lab=q}
N 4360 -1420 4330 -1420 {}
C {lab_pin.sym} 4330 -1420 0 0 {name=l112 sig_type=std_logic lab=do_osc_oe}
C {sg13cmos5l_stdcells/sg13cmos5l_buf_2.sym} 4540 -1480 0 0 {name=XBM
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 4440 -1480 4500 -1480 {}
N 4580 -1480 4640 -1480 {}
C {opin.sym} 4640 -1480 0 0 {name=p113 lab=do_clk_mod}
C {sg13cmos5l_stdcells/sg13cmos5l_and2_1.sym} 4400 -1280 0 0 {name=XA
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 4340 -1300 4310 -1300 {}
C {lab_pin.sym} 4310 -1300 0 0 {name=l114 sig_type=std_logic lab=q}
N 4340 -1260 4310 -1260 {}
C {lab_pin.sym} 4310 -1260 0 0 {name=l115 sig_type=std_logic lab=d_osc_en}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_1.sym} 4520 -1280 0 0 {name=XO1
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
C {sg13cmos5l_stdcells/sg13cmos5l_inv_2.sym} 4620 -1280 0 0 {name=XO2
VDD=vdd
VSS=vss
prefix=sg13cmos5l_
}
N 4460 -1280 4480 -1280 {}
N 4560 -1280 4580 -1280 {}
N 4660 -1280 4720 -1280 {}
C {opin.sym} 4720 -1280 0 0 {name=p116 lab=do_clk_osc}
T {pad driver like the do_q drivers of quantizer2, do_clk_osc is low while di_osc_en is low} 4300 -1220 0 0 0.3 0.3 {}
