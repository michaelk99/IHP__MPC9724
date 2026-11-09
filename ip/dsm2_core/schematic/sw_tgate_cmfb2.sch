v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
T {guards} 1600 -400 0 0 0.6 0.6 {}
T {MNG and MPG are the strip-end guards of the layout. Gate on their bulk rail, both terminals on m, so they stay off.} 1220 -60 0 0 0.3 0.3 {}
N 140 -700 660 -700 {lab=vdd}
N 660 -700 1120 -700 {lab=vdd}
N 140 -100 340 -100 {lab=vss}
N 340 -100 1120 -100 {lab=vss}
N 380 -480 380 -430 {lab=p}
N 380 -480 620 -480 {lab=p}
N 620 -480 620 -430 {lab=p}
N 380 -370 380 -320 {lab=m}
N 380 -320 620 -320 {lab=m}
N 620 -370 620 -320 {lab=m}
N 340 -400 380 -400 {lab=vss}
N 340 -400 340 -100 {lab=vss}
N 620 -400 660 -400 {lab=vdd}
N 660 -700 660 -400 {lab=vdd}
N 420 -400 470 -400 {lab=g}
N 530 -400 580 -400 {lab=gb}
N 320 -330 320 -280 {lab=p}
N 320 -220 320 -170 {lab=p}
N 320 -250 400 -250 {lab=vss}
N 220 -250 280 -250 {lab=gb}
N 560 -330 560 -280 {lab=m}
N 560 -220 560 -170 {lab=m}
N 560 -250 640 -250 {lab=vss}
N 460 -250 520 -250 {lab=gb}
N 800 -330 800 -280 {lab=p}
N 800 -220 800 -170 {lab=p}
N 800 -250 880 -250 {lab=vdd}
N 700 -250 760 -250 {lab=g}
N 1040 -330 1040 -280 {lab=m}
N 1040 -220 1040 -170 {lab=m}
N 1040 -250 1120 -250 {lab=vdd}
N 940 -250 1000 -250 {lab=g}
N 1320 -330 1320 -280 {lab=m}
N 1320 -220 1320 -170 {lab=m}
N 1320 -250 1400 -250 {lab=vss}
N 1220 -250 1280 -250 {lab=vss}
N 1560 -330 1560 -280 {lab=m}
N 1560 -220 1560 -170 {lab=m}
N 1560 -250 1640 -250 {lab=vss}
N 1460 -250 1520 -250 {lab=vss}
N 1800 -330 1800 -280 {lab=m}
N 1800 -220 1800 -170 {lab=m}
N 1800 -250 1880 -250 {lab=vdd}
N 1700 -250 1760 -250 {lab=vdd}
N 2040 -330 2040 -280 {lab=m}
N 2040 -220 2040 -170 {lab=m}
N 2040 -250 2120 -250 {lab=vdd}
N 1940 -250 2000 -250 {lab=vdd}
N 1120 -700 2120 -700 {lab=vdd}
N 1120 -100 2120 -100 {lab=vss}
C {iopin.sym} 140 -700 2 0 {name=p5 lab=vdd}
C {iopin.sym} 140 -100 2 0 {name=p6 lab=vss}
C {sg13_lv_nmos.sym} 400 -400 0 1 {name=MN
l=1u
w=1u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13_lv_pmos.sym} 600 -400 2 1 {name=MP
l=1u
w=3u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
C {iopin.sym} 500 -480 2 0 {name=p1 lab=p}
C {iopin.sym} 500 -320 0 0 {name=p2 lab=m}
C {lab_pin.sym} 470 -400 0 0 {name=l5 lab=g}
C {lab_pin.sym} 530 -400 0 0 {name=l6 lab=gb}
C {sg13_lv_nmos.sym} 300 -250 0 0 {name=MND1
l=1u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {lab_pin.sym} 320 -330 0 0 {name=l7 lab=p}
C {lab_pin.sym} 320 -170 0 0 {name=l8 lab=p}
C {lab_pin.sym} 400 -250 0 0 {name=l9 lab=vss}
C {ipin.sym} 220 -250 2 0 {name=p4 lab=gb}
C {sg13_lv_nmos.sym} 540 -250 0 0 {name=MND2
l=1u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {lab_pin.sym} 560 -330 0 0 {name=l11 lab=m}
C {lab_pin.sym} 560 -170 0 0 {name=l12 lab=m}
C {lab_pin.sym} 640 -250 0 0 {name=l13 lab=vss}
C {lab_pin.sym} 460 -250 0 0 {name=l14 lab=gb}
C {sg13_lv_pmos.sym} 780 -250 0 0 {name=MPD1
l=1u
w=1.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
C {lab_pin.sym} 800 -330 0 0 {name=l15 lab=p}
C {lab_pin.sym} 800 -170 0 0 {name=l16 lab=p}
C {lab_pin.sym} 880 -250 0 0 {name=l17 lab=vdd}
C {ipin.sym} 700 -250 2 0 {name=p3 lab=g}
C {sg13_lv_pmos.sym} 1020 -250 0 0 {name=MPD2
l=1u
w=1.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
C {lab_pin.sym} 1040 -330 0 0 {name=l19 lab=m}
C {lab_pin.sym} 1040 -170 0 0 {name=l20 lab=m}
C {lab_pin.sym} 1120 -250 0 0 {name=l21 lab=vdd}
C {lab_pin.sym} 940 -250 0 0 {name=l22 lab=g}
C {sg13_lv_nmos.sym} 1300 -250 0 0 {name=MNG1
l=1u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {lab_pin.sym} 1320 -330 0 0 {name=l23 lab=m}
C {lab_pin.sym} 1320 -170 0 0 {name=l24 lab=m}
C {lab_pin.sym} 1400 -250 0 0 {name=l25 lab=vss}
C {lab_pin.sym} 1220 -250 0 0 {name=l26 lab=vss}
C {sg13_lv_nmos.sym} 1540 -250 0 0 {name=MNG2
l=1u
w=0.5u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {lab_pin.sym} 1560 -330 0 0 {name=l27 lab=m}
C {lab_pin.sym} 1560 -170 0 0 {name=l28 lab=m}
C {lab_pin.sym} 1640 -250 0 0 {name=l29 lab=vss}
C {lab_pin.sym} 1460 -250 0 0 {name=l30 lab=vss}
C {sg13_lv_pmos.sym} 1780 -250 0 0 {name=MPG1
l=1u
w=1.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
C {lab_pin.sym} 1800 -330 0 0 {name=l31 lab=m}
C {lab_pin.sym} 1800 -170 0 0 {name=l32 lab=m}
C {lab_pin.sym} 1880 -250 0 0 {name=l33 lab=vdd}
C {lab_pin.sym} 1700 -250 0 0 {name=l34 lab=vdd}
C {sg13_lv_pmos.sym} 2020 -250 0 0 {name=MPG2
l=1u
w=1.5u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
C {lab_pin.sym} 2040 -330 0 0 {name=l35 lab=m}
C {lab_pin.sym} 2040 -170 0 0 {name=l36 lab=m}
C {lab_pin.sym} 2120 -250 0 0 {name=l37 lab=vdd}
C {lab_pin.sym} 1940 -250 0 0 {name=l38 lab=vdd}
