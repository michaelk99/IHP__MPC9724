v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
T {MNDL} 3160 -440 0 0 0.2 0.2 {}
T {w=0.5u l=10u} 3160 -426 0 0 0.2 0.2 {}
T {ng=1 m=6} 3160 -412 0 0 0.2 0.2 {}
T {sg13_lv_nmos} 3160 -398 0 0 0.2 0.2 {}
T {MNDT} 3440 -440 0 0 0.2 0.2 {}
T {w=1u l=10u} 3440 -426 0 0 0.2 0.2 {}
T {ng=1 m=8} 3440 -412 0 0 0.2 0.2 {}
T {sg13_hv_nmos} 3440 -398 0 0 0.2 0.2 {}
T {MPD} 3160 -680 0 0 0.2 0.2 {}
T {w=0.5u l=5u} 3160 -666 0 0 0.2 0.2 {}
T {ng=1 m=26} 3160 -652 0 0 0.2 0.2 {}
T {sg13_lv_pmos} 3160 -638 0 0 0.2 0.2 {}
T {MNDS} 3160 -210 0 0 0.2 0.2 {}
T {w=10u l=1u} 3160 -196 0 0 0.2 0.2 {}
T {ng=1 m=10} 3160 -182 0 0 0.2 0.2 {}
T {sg13_hv_nmos} 3160 -168 0 0 0.2 0.2 {}
T {MSD} 3500 -680 0 0 0.2 0.2 {}
T {w=0.5u l=10u} 3500 -666 0 0 0.2 0.2 {}
T {ng=1 m=1} 3500 -652 0 0 0.2 0.2 {}
T {sg13_lv_pmos} 3500 -638 0 0 0.2 0.2 {}
T {MSDS} 3640 -570 0 0 0.2 0.2 {}
T {w=0.5u l=10u} 3640 -556 0 0 0.2 0.2 {}
T {ng=1 m=1} 3640 -542 0 0 0.2 0.2 {}
T {sg13_lv_pmos} 3640 -528 0 0 0.2 0.2 {}
T {MNDJ} 3900 -210 0 0 0.2 0.2 {}
T {w=0.5u l=10u} 3900 -196 0 0 0.2 0.2 {}
T {ng=1 m=4} 3900 -182 0 0 0.2 0.2 {}
T {sg13_hv_nmos} 3900 -168 0 0 0.2 0.2 {}
T {RD1} 3320 -212 0 0 0.2 0.2 {}
T {w=0.5u l=17.5u} 3320 -198 0 0 0.2 0.2 {}
T {m=4 R=52.1k} 3320 -184 0 0 0.2 0.2 {}
T {RD2} 3460 -212 0 0 0.2 0.2 {}
T {w=0.5u l=10.975u} 3460 -198 0 0 0.2 0.2 {}
T {m=4 R=32.8k} 3460 -184 0 0 0.2 0.2 {}
T {RD3} 3600 -212 0 0 0.2 0.2 {}
T {w=0.5u l=2.75u} 3600 -198 0 0 0.2 0.2 {}
T {m=46 R=8.45k} 3600 -184 0 0 0.2 0.2 {}
T {bias_gm: constant-current reference, HV/LV NMOS pair with the Pavan supply-rejection loop} -90 -960 0 0 0.6 0.6 {}
T {VDD 1.45 to 1.55 V, ibias_200n sources 200 nA from bias_trim, 24 units of 8.33 nA at code 4. Core legs 200 nA, V_R = dVth(HV - LV) + n UT ln K.} -90 -915 0 0 0.3 0.3 {}
T {Enable and clamps} -80 -822 0 0 0.35 0.35 {}
T {di_ena low: vz to vdd, vx, vy, vs to vss} -80 -792 0 0 0.25 0.25 {}
T {MPBI, MNBI: d_btest_b for the test switch MBS} -80 -772 0 0 0.25 0.25 {}
T {Core} 710 -822 0 0 0.35 0.35 {}
T {M2 LV diode on R1 sets vx, M1 HV (drain vy) shares the gate, M6 sets vy = vx, Cc with Rz on vy} 710 -792 0 0 0.25 0.25 {}
T {Start-up} 2450 -822 0 0 0.35 0.35 {}
T {MSA, MSB: one diode each, 13 x 0.5u/10u in series, always on. MSN = 2 units of M1} 2450 -792 0 0 0.25 0.25 {}
T {Dummies} 3050 -822 0 0 0.35 0.35 {}
T {MPD, MSD on vdd, MSDS on vs, MNDJ, MNDL, MNDS, MNDT on vss, MNDR on vnr (gate vss), MBSD on vbt (gate vdd), RD1 to RD4 with both ends on vss.} 3050 -792 0 0 0.25 0.25 {}
T {They frame the arrays of the layout. Dummies with every terminal on one net are declared, LVS keeps them.} 3050 -772 0 0 0.25 0.25 {}
T {Output} 1470 -822 0 0 0.35 0.35 {}
T {bias_trim: 16 + 2 x code units of 8.33 nA on vz, code 4 gives 200 nA} 1470 -792 0 0 0.25 0.25 {}
T {xtrim2: the same bank on vz and di_trim_b for the test pad, MBS closes on di_btest_en} 1470 -772 0 0 0.25 0.25 {}
P 4 5 -90 -830 680 -830 680 -90 -90 -90 -90 -830 {dash = 8}
P 4 5 700 -830 1440 -830 1440 -90 700 -90 700 -830 {dash = 8}
P 4 5 2440 -830 3020 -830 3020 -90 2440 -90 2440 -830 {dash = 8}
P 4 5 3040 -830 3940 -830 3940 -90 3040 -90 3040 -830 {dash = 8}
P 4 5 1460 -830 2420 -830 2420 -90 1460 -90 1460 -830 {dash = 8}
N 3080 -400 3060 -400 {}
N 3060 -400 3060 -370 {}
N 3060 -370 3120 -370 {}
N 3120 -370 3140 -370 {}
N 3120 -400 3140 -400 {}
N 3140 -400 3140 -370 {}
N 3120 -430 3140 -430 {}
N 3140 -430 3140 -400 {}
N 3360 -400 3340 -400 {}
N 3340 -400 3340 -370 {}
N 3340 -370 3400 -370 {}
N 3400 -370 3420 -370 {}
N 3400 -400 3420 -400 {}
N 3420 -400 3420 -370 {}
N 3400 -430 3420 -430 {}
N 3420 -430 3420 -400 {}
N -20 -700 3940 -700 {}
N -20 -140 3940 -140 {}
N 0 -590 480 -590 {}
N 220 -670 240 -670 {}
N 240 -670 240 -590 {}
N 180 -670 160 -670 {}
N 160 -670 160 -700 {}
N 180 -640 180 -620 {}
N 500 -670 480 -670 {}
N 540 -670 560 -670 {}
N 560 -670 560 -700 {}
N 500 -170 480 -170 {}
N 540 -170 560 -170 {}
N 560 -170 560 -140 {}
N 480 -670 480 -170 {}
N 540 -640 540 -200 {}
N 540 -450 580 -450 {}
N 120 -170 140 -170 {}
N 140 -170 140 -140 {}
N 120 -200 120 -250 {}
N 80 -170 60 -170 {}
N 240 -170 260 -170 {}
N 260 -170 260 -140 {}
N 240 -200 240 -250 {}
N 200 -170 180 -170 {}
N 360 -170 380 -170 {}
N 380 -170 380 -140 {}
N 360 -200 360 -250 {}
N 320 -170 300 -170 {}
N 60 -170 60 -290 {}
N 60 -290 300 -290 {}
N 180 -170 180 -290 {}
N 300 -170 300 -290 {}
N 300 -290 420 -290 {}
N 940 -670 920 -670 {}
N 920 -670 920 -700 {}
N 1100 -670 1080 -670 {}
N 1080 -670 1080 -700 {}
N 1300 -670 1320 -670 {}
N 1320 -670 1320 -700 {}
N 980 -670 1000 -670 {}
N 1000 -670 1000 -590 {}
N 1140 -670 1160 -670 {}
N 1160 -670 1160 -590 {}
N 1260 -670 1240 -670 {}
N 1240 -670 1240 -590 {}
N 1000 -590 1240 -590 {}
N 1100 -640 1100 -590 {}
N 1100 -590 1100 -480 {}
N 1100 -450 1120 -450 {}
N 1120 -450 1120 -420 {}
N 1120 -420 1100 -420 {}
N 1100 -420 1100 -140 {}
N 940 -640 940 -330 {}
N 940 -300 920 -300 {}
N 920 -300 920 -140 {}
N 940 -270 940 -140 {}
N 1060 -450 940 -450 {}
N 840 -420 820 -420 {}
N 820 -420 820 -390 {}
N 840 -390 820 -390 {}
N 820 -390 820 -140 {}
N 840 -360 840 -140 {}
N 1300 -640 1300 -330 {}
N 1300 -360 1240 -360 {}
N 1240 -360 1240 -300 {}
N 1260 -300 980 -300 {}
N 1300 -190 1300 -140 {}
N 1300 -270 1300 -250 {}
N 1300 -250 1260 -250 {}
N 1300 -300 1340 -300 {}
N 1340 -300 1340 -140 {}
N 2620 -600 2620 -620 {}
N 2620 -540 2620 -520 {}
N 2580 -570 2540 -570 {}
N 2620 -570 2740 -570 {}
N 2620 -440 2620 -460 {}
N 2620 -380 2620 -360 {}
N 2580 -410 2540 -410 {}
N 2620 -410 2740 -410 {}
N 2740 -410 2740 -700 {}
N 2800 -170 2820 -170 {}
N 2820 -170 2820 -140 {}
N 2760 -170 2720 -170 {}
N 2960 -260 2960 -140 {}
N 2960 -290 2980 -290 {}
N 2980 -290 2980 -140 {}
N 2800 -200 2800 -290 {}
N 2800 -290 2920 -290 {}
N 2800 -290 2800 -340 {}
N 2960 -320 2960 -400 {}
N 3080 -670 3060 -670 {}
N 3060 -670 3060 -700 {}
N 3120 -670 3140 -670 {}
N 3140 -670 3140 -700 {}
N 3120 -640 3140 -640 {}
N 3140 -640 3140 -670 {}
N 3080 -170 3060 -170 {}
N 3060 -170 3060 -140 {}
N 3120 -170 3140 -170 {}
N 3140 -170 3140 -140 {}
N 3120 -200 3140 -200 {}
N 3140 -200 3140 -170 {}
N 3300 -200 3300 -230 {}
N 3440 -200 3440 -230 {}
N 3420 -670 3400 -670 {}
N 3400 -670 3400 -700 {}
N 3460 -670 3480 -670 {}
N 3480 -670 3480 -700 {}
N 3460 -640 3480 -640 {}
N 3480 -640 3480 -670 {}
N 3600 -560 3620 -560 {}
N 3620 -560 3620 -700 {}
N 3560 -560 3540 -560 {}
N 3540 -590 3540 -560 {}
N 3540 -560 3540 -530 {}
N 3540 -590 3600 -590 {}
N 3540 -530 3600 -530 {}
N 3540 -530 3520 -530 {}
N 3580 -200 3580 -230 {}
N 3820 -170 3800 -170 {}
N 3800 -170 3800 -140 {}
N 3860 -170 3880 -170 {}
N 3880 -170 3880 -140 {}
N 3860 -200 3880 -200 {}
N 3880 -200 3880 -170 {}
N 1540 -460 1540 -700 {}
N 1580 -460 1580 -540 {}
N 1620 -460 1620 -540 {}
N 1660 -200 1660 -140 {}
N 1840 -260 1900 -260 {}
N 1860 -170 1860 -260 {}
N 1900 -170 1920 -170 {}
N 1920 -170 1920 -140 {}
N 1900 -200 1920 -200 {}
N 1920 -200 1920 -170 {}
C {iopin.sym} -20 -700 2 0 {name=p1
lab=vdd}
C {iopin.sym} -20 -140 2 0 {name=p2
lab=vss}
C {ipin.sym} 0 -590 0 0 {name=p3
lab=di_ena}
C {sg13_lv_pmos.sym} 200 -670 0 1 {name=MCL1
l=5u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X}
C {lab_pin.sym} 180 -620 0 0 {name=l1
sig_type=std_logic
lab=vz}
C {sg13_lv_pmos.sym} 520 -670 0 0 {name=MPI
l=0.5u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X}
C {sg13_lv_nmos.sym} 520 -170 0 0 {name=MNI
l=1u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X}
C {lab_wire.sym} 540 -550 0 0 {name=w1
sig_type=std_logic
lab=d_en_b}
C {lab_pin.sym} 580 -450 0 1 {name=l3
sig_type=std_logic
lab=d_en_b}
C {sg13_hv_nmos.sym} 100 -170 0 0 {name=MCL3
l=1u
w=0.5u
ng=1
m=1
model=sg13_hv_nmos
spiceprefix=X}
C {lab_pin.sym} 120 -250 0 1 {name=l4
sig_type=std_logic
lab=vx}
C {sg13_hv_nmos.sym} 220 -170 0 0 {name=MCL4
l=1u
w=0.5u
ng=1
m=1
model=sg13_hv_nmos
spiceprefix=X}
C {lab_pin.sym} 240 -250 0 1 {name=l5
sig_type=std_logic
lab=vy}
C {sg13_lv_nmos.sym} 340 -170 0 0 {name=MCL6
l=1u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X}
C {lab_pin.sym} 360 -250 0 1 {name=l6
sig_type=std_logic
lab=vs}
C {lab_pin.sym} 420 -290 0 1 {name=l7
sig_type=std_logic
lab=d_en_b}
C {sg13_lv_pmos.sym} 960 -670 0 1 {name=M3
l=5u
w=0.5u
ng=1
m=24
model=sg13_lv_pmos
spiceprefix=X}
C {sg13_lv_pmos.sym} 1120 -670 0 1 {name=M5
l=5u
w=0.5u
ng=1
m=12
model=sg13_lv_pmos
spiceprefix=X}
C {sg13_lv_pmos.sym} 1280 -670 0 0 {name=M4
l=5u
w=0.5u
ng=1
m=24
model=sg13_lv_pmos
spiceprefix=X}
C {lab_wire.sym} 1160 -590 0 0 {name=w2
sig_type=std_logic
lab=vz}
C {sg13_hv_nmos.sym} 1080 -450 0 0 {name=M6
l=10u
w=0.5u
ng=1
m=2
model=sg13_hv_nmos
spiceprefix=X}
C {sg13_hv_nmos.sym} 960 -300 0 1 {name=M1
l=10u
w=0.5u
ng=1
m=4
model=sg13_hv_nmos
spiceprefix=X}
C {lab_wire.sym} 940 -510 0 0 {name=w3
sig_type=std_logic
lab=vy}
C {sg13_hv_nmos.sym} 860 -390 0 1 {name=CC
l=10u
w=10u
ng=1
m=20
model=sg13_hv_nmos
spiceprefix=X}
C {sg13_lv_nmos.sym} 1280 -300 0 0 {name=M2
l=10u
w=0.5u
ng=1
m=4
model=sg13_lv_nmos
spiceprefix=X}
C {lab_wire.sym} 1240 -360 0 0 {name=w4
sig_type=std_logic
lab=vx}
C {rhigh.sym} 1300 -220 0 0 {name=R1
w=0.5e-6
l=735e-6
model=rhigh
body=vss
spiceprefix=X
b=0
m=1}
C {lab_pin.sym} 1260 -250 0 0 {name=l20
sig_type=std_logic
lab=vnr}
C {sg13_lv_pmos.sym} 2600 -570 0 0 {name=MSA[12:0]
l=10u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X}
C {lab_pin.sym} 2620 -620 0 0 {name=l10
sig_type=std_logic
lab=vdd,vua[1:12]}
C {lab_pin.sym} 2620 -520 0 0 {name=l11
sig_type=std_logic
lab=vua[1:12],vt1}
C {lab_pin.sym} 2540 -570 0 0 {name=l12
sig_type=std_logic
lab=vt1}
C {sg13_lv_pmos.sym} 2600 -410 0 0 {name=MSB[12:0]
l=10u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X}
C {lab_pin.sym} 2620 -460 0 0 {name=l13
sig_type=std_logic
lab=vt1,vub[1:12]}
C {lab_pin.sym} 2620 -360 0 0 {name=l14
sig_type=std_logic
lab=vub[1:12],vs}
C {lab_pin.sym} 2540 -410 0 0 {name=l15
sig_type=std_logic
lab=vs}
C {sg13_hv_nmos.sym} 2780 -170 0 0 {name=MSN
l=10u
w=0.5u
ng=1
m=2
model=sg13_hv_nmos
spiceprefix=X}
C {lab_pin.sym} 2720 -170 0 0 {name=l16
sig_type=std_logic
lab=vx}
C {sg13_hv_nmos.sym} 2940 -290 0 0 {name=MINJ
l=0.5u
w=4u
ng=1
m=2
model=sg13_hv_nmos
spiceprefix=X}
C {lab_pin.sym} 2800 -340 0 1 {name=l17
sig_type=std_logic
lab=vs}
C {lab_pin.sym} 2960 -400 0 1 {name=l18
sig_type=std_logic
lab=vz}
C {sg13_lv_pmos.sym} 3100 -670 0 0 {name=MPD
hide_texts=true
l=5u
w=0.5u
ng=1
m=26
model=sg13_lv_pmos
spiceprefix=X}
C {sg13_hv_nmos.sym} 3100 -170 0 0 {name=MNDS
hide_texts=true
l=1u
w=10u
ng=1
m=10
model=sg13_hv_nmos
spiceprefix=X}
C {rhigh.sym} 3300 -170 0 0 {name=RD1
hide_texts=true
w=0.5e-6
l=17.5e-6
model=rhigh
body=vss
spiceprefix=X
b=0
m=4}
C {lab_wire.sym} 3300 -230 0 0 {name=w8
sig_type=std_logic
lab=vss}
C {rhigh.sym} 3440 -170 0 0 {name=RD2
hide_texts=true
w=0.5e-6
l=10.975e-6
model=rhigh
body=vss
spiceprefix=X
b=0
m=4}
C {lab_wire.sym} 3440 -230 0 0 {name=w9
sig_type=std_logic
lab=vss}
C {sg13_lv_pmos.sym} 3440 -670 0 0 {name=MSD
hide_texts=true
l=10u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X}
C {sg13_lv_pmos.sym} 3580 -560 0 0 {name=MSDS
hide_texts=true
l=10u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X}
C {lab_pin.sym} 3520 -530 0 0 {name=l19
sig_type=std_logic
lab=vs}
C {rhigh.sym} 3580 -170 0 0 {name=RD3
hide_texts=true
w=0.5e-6
l=2.75e-6
model=rhigh
body=vss
spiceprefix=X
b=0
m=46}
C {lab_wire.sym} 3580 -230 0 0 {name=w10
sig_type=std_logic
lab=vss}
C {sg13_hv_nmos.sym} 3840 -170 0 0 {name=MNDJ
hide_texts=true
l=10u
w=0.5u
ng=1
m=4
model=sg13_hv_nmos
spiceprefix=X}
C {bias_trim.sym} 1500 -440 0 0 {name=xtrim
}
C {lab_pin.sym} 1580 -540 1 0 {name=l21
sig_type=std_logic
lab=vz}
C {lab_pin.sym} 1620 -540 1 0 {name=l23
sig_type=std_logic
lab=di_trim_b[3:0]}
C {iopin.sym} 1900 -260 0 0 {name=p4
lab=ibias_200n}
C {ipin.sym} 0 -540 0 0 {name=p5
lab=di_trim_b[3:0]}
T {Rz} 895 -416 0 0 0.2 0.2 {}
T {w=0.5u l=43.9u} 860 -436 0 0 0.2 0.2 {}
C {rhigh.sym} 910 -390 1 0 {name=RZ
hide_texts=true
w=0.5e-6
l=43.9e-6
model=rhigh
body=vss
spiceprefix=X
b=0
m=1}
C {sg13_hv_nmos.sym} 1880 -170 0 0 {name=MCI
l=10u
w=0.5u
ng=1
m=4
model=sg13_hv_nmos
spiceprefix=X}
T {MCI: pin cap on ibias_200n, absorbs the charge} 1470 -122 0 0 0.2 0.2 {}
T {the OTA enable switch dumps at the di_ena fall} 1470 -108 0 0 0.2 0.2 {}
C {devices/title.sym} -200 0 0 0 {name=l0 author="Michael Koefinger"}
C {sg13_lv_nmos.sym} 3100 -400 0 0 {name=MNDL
hide_texts=true
l=10u
w=0.5u
ng=1
m=6
model=sg13_lv_nmos
spiceprefix=X}
C {lab_pin.sym} 3140 -370 0 1 {name=lMNDL
sig_type=std_logic
lab=vss}
C {sg13_hv_nmos.sym} 3380 -400 0 0 {name=MNDT
hide_texts=true
l=10u
w=1u
ng=1
m=8
model=sg13_hv_nmos
spiceprefix=X}
C {lab_pin.sym} 3420 -370 0 1 {name=lMNDT
sig_type=std_logic
lab=vss}
C {sg13_lv_nmos.sym} 3680 -400 0 0 {name=MNDR
hide_texts=true
l=10u
w=0.5u
ng=1
m=4
model=sg13_lv_nmos
spiceprefix=X}
C {lab_pin.sym} 3700 -430 0 1 {name=lMNDRd
sig_type=std_logic
lab=vnr}
C {lab_pin.sym} 3700 -370 0 1 {name=lMNDRs
sig_type=std_logic
lab=vnr}
C {lab_pin.sym} 3700 -400 0 1 {name=lMNDRb
sig_type=std_logic
lab=vss}
C {lab_pin.sym} 3660 -400 0 0 {name=lMNDRg
sig_type=std_logic
lab=vss}
T {MNDR} 3760 -440 0 0 0.2 0.2 {}
T {w=0.5u l=10u} 3760 -426 0 0 0.2 0.2 {}
T {ng=1 m=4} 3760 -412 0 0 0.2 0.2 {}
T {sg13_lv_nmos} 3760 -398 0 0 0.2 0.2 {}
C {rhigh.sym} 3720 -170 0 0 {name=RD4
hide_texts=true
w=0.5e-6
l=9.28e-6
model=rhigh
body=vss
spiceprefix=X
b=0
m=8}
C {lab_wire.sym} 3720 -230 0 0 {name=w11
sig_type=std_logic
lab=vss}
N 3720 -200 3720 -230 {}
T {RD4} 3730 -300 0 0 0.2 0.2 {}
T {w=0.5u l=9.28u} 3730 -286 0 0 0.2 0.2 {}
T {m=8 R=27.8k} 3730 -272 0 0 0.2 0.2 {}
C {ipin.sym} 0 -490 0 0 {name=p7
lab=di_btest_en}
N 340 -530 340 -550 {}
N 340 -500 360 -500 {}
N 360 -500 360 -550 {}
N 340 -550 360 -550 {}
N 340 -400 360 -400 {}
N 360 -400 360 -350 {}
N 340 -370 340 -350 {}
N 340 -350 360 -350 {}
N 300 -500 280 -500 {}
N 300 -400 280 -400 {}
N 280 -500 280 -400 {}
N 340 -470 340 -430 {}
C {sg13_lv_pmos.sym} 320 -500 0 0 {name=MPBI
l=5u
w=0.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X}
C {sg13_lv_nmos.sym} 320 -400 0 0 {name=MNBI
l=10u
w=0.5u
ng=1
m=2
model=sg13_lv_nmos
spiceprefix=X}
C {lab_pin.sym} 340 -550 1 0 {name=l27
sig_type=std_logic
lab=vdd}
C {lab_pin.sym} 340 -350 3 0 {name=l28
sig_type=std_logic
lab=vss}
C {lab_pin.sym} 280 -450 0 0 {name=l29
sig_type=std_logic
lab=di_btest_en}
C {lab_pin.sym} 340 -450 0 1 {name=l30
sig_type=std_logic
lab=d_btest_b}
N 2020 -460 2020 -700 {}
N 2060 -460 2060 -540 {}
N 2100 -460 2100 -540 {}
N 2140 -200 2140 -140 {}
N 2320 -260 2360 -260 {}
N 2260 -640 2260 -660 {}
N 2260 -610 2280 -610 {}
N 2260 -580 2260 -520 {}
N 2260 -520 2380 -520 {}
C {bias_trim.sym} 1980 -440 0 0 {name=xtrim2
}
C {lab_pin.sym} 2060 -540 1 0 {name=l31
sig_type=std_logic
lab=vz}
C {lab_pin.sym} 2100 -540 1 0 {name=l32
sig_type=std_logic
lab=di_trim_b[3:0]}
C {lab_pin.sym} 2360 -260 0 1 {name=l33
sig_type=std_logic
lab=vbt}
C {sg13_lv_pmos.sym} 2240 -610 0 0 {name=MBS
hide_texts=true
l=5u
w=0.5u
ng=1
m=6
model=sg13_lv_pmos
spiceprefix=X}
T {MBS lv_pmos} 2150 -592 0 0 0.2 0.2 {}
T {0.5u/5u m=6} 2150 -578 0 0 0.2 0.2 {}
C {lab_pin.sym} 2260 -660 1 0 {name=l34
sig_type=std_logic
lab=vbt}
C {lab_pin.sym} 2220 -610 0 0 {name=l35
sig_type=std_logic
lab=d_btest_b}
C {lab_pin.sym} 2280 -610 0 1 {name=l36
sig_type=std_logic
lab=vdd}
C {iopin.sym} 2380 -520 0 0 {name=p6
lab=ibias_test}
C {sg13_lv_pmos.sym} 3360 -560 0 0 {name=MBSD
hide_texts=true
l=5u
w=0.5u
ng=1
m=2
model=sg13_lv_pmos
spiceprefix=X}
T {MBSD} 3445 -612 0 0 0.2 0.2 {}
T {w=0.5u l=5u} 3445 -598 0 0 0.2 0.2 {}
T {ng=1 m=2} 3445 -584 0 0 0.2 0.2 {}
T {sg13_lv_pmos} 3445 -570 0 0 0.2 0.2 {}
N 3380 -560 3400 -560 {}
C {lab_pin.sym} 3380 -590 1 0 {name=l37
sig_type=std_logic
lab=vbt}
C {lab_pin.sym} 3340 -560 0 0 {name=l38
sig_type=std_logic
lab=vdd}
C {lab_pin.sym} 3400 -560 0 1 {name=l39
sig_type=std_logic
lab=vdd}
C {lab_pin.sym} 3380 -530 3 0 {name=l40
sig_type=std_logic
lab=vbt}
