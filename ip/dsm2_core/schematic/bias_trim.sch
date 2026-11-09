v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
T {bias_trim: PMOS output units on vz, trim on a fixed group of 16, I_out = (16 + 2 code) x I_unit} -20 -880 0 0 0.6 0.6 {}
T {Every group has one series switch of 2 unit devices. The switch gates of a group go straight to its active low pin di_trim_b[k], low is on, the fixed switches are tied to vss.} -20 -835 0 0 0.3 0.3 {}
T {Output units and switches, gate low is on} -20 -760 0 0 0.35 0.35 {}
P 4 5 -60 -770 2460 -770 2460 -380 -60 -380 -60 -770 {dash = 8}
N -20 -700 2400 -700 {}
N 220 -670 240 -670 {}
N 240 -670 240 -700 {}
N 220 -640 220 -580 {}
N 220 -550 240 -550 {}
N 240 -550 240 -670 {}
N 220 -520 220 -440 {}
N 180 -670 100 -670 {}
N 180 -550 160 -550 {}
N 700 -670 720 -670 {}
N 720 -670 720 -700 {}
N 700 -640 700 -580 {}
N 700 -550 720 -550 {}
N 720 -550 720 -670 {}
N 700 -520 700 -440 {}
N 660 -670 640 -670 {}
N 660 -550 640 -550 {}
N 1180 -670 1200 -670 {}
N 1200 -670 1200 -700 {}
N 1180 -640 1180 -580 {}
N 1180 -550 1200 -550 {}
N 1200 -550 1200 -670 {}
N 1180 -520 1180 -440 {}
N 1140 -670 1120 -670 {}
N 1140 -550 1120 -550 {}
N 1660 -670 1680 -670 {}
N 1680 -670 1680 -700 {}
N 1660 -640 1660 -580 {}
N 1660 -550 1680 -550 {}
N 1680 -550 1680 -670 {}
N 1660 -520 1660 -440 {}
N 1620 -670 1600 -670 {}
N 1620 -550 1600 -550 {}
N 2140 -670 2160 -670 {}
N 2160 -670 2160 -700 {}
N 2140 -640 2140 -580 {}
N 2140 -550 2160 -550 {}
N 2160 -550 2160 -670 {}
N 2140 -520 2140 -440 {}
N 2100 -670 2080 -670 {}
N 2100 -550 2080 -550 {}
N 220 -440 2260 -440 {}
N 2340 -670 2320 -670 {}
N 2320 -670 2320 -700 {}
N 2380 -670 2400 -670 {}
N 2400 -670 2400 -700 {}
N 2380 -640 2400 -640 {}
N 2400 -640 2400 -670 {}
C {iopin.sym} -20 -700 2 0 {name=p1
lab=vdd}
C {sg13_lv_pmos.sym} 200 -670 0 0 {name=MPF
l=5u
w=0.5u
ng=1
m=16
model=sg13_lv_pmos
spiceprefix=X}
C {sg13_lv_pmos.sym} 200 -550 0 0 {name=MSF
l=5u
w=0.5u
ng=1
m=2
model=sg13_lv_pmos
spiceprefix=X}
C {lab_wire.sym} 220 -610 0 0 {name=wf
sig_type=std_logic
lab=vdf}
C {ipin.sym} 100 -670 0 0 {name=p3
lab=vz}
C {lab_pin.sym} 160 -550 0 0 {name=lsf
sig_type=std_logic
lab=vss}
C {sg13_lv_pmos.sym} 680 -670 0 0 {name=MP3
l=5u
w=0.5u
ng=1
m=16
model=sg13_lv_pmos
spiceprefix=X}
C {sg13_lv_pmos.sym} 680 -550 0 0 {name=MS3
l=5u
w=0.5u
ng=1
m=2
model=sg13_lv_pmos
spiceprefix=X}
C {lab_wire.sym} 700 -610 0 0 {name=w3
sig_type=std_logic
lab=vd3}
C {lab_pin.sym} 640 -670 0 0 {name=lz3
sig_type=std_logic
lab=vz}
C {lab_pin.sym} 640 -550 0 0 {name=ls3
sig_type=std_logic
lab=di_trim_b[3]}
C {sg13_lv_pmos.sym} 1160 -670 0 0 {name=MP2
l=5u
w=0.5u
ng=1
m=8
model=sg13_lv_pmos
spiceprefix=X}
C {sg13_lv_pmos.sym} 1160 -550 0 0 {name=MS2
l=5u
w=0.5u
ng=1
m=2
model=sg13_lv_pmos
spiceprefix=X}
C {lab_wire.sym} 1180 -610 0 0 {name=w2
sig_type=std_logic
lab=vd2}
C {lab_pin.sym} 1120 -670 0 0 {name=lz2
sig_type=std_logic
lab=vz}
C {lab_pin.sym} 1120 -550 0 0 {name=ls2
sig_type=std_logic
lab=di_trim_b[2]}
C {sg13_lv_pmos.sym} 1640 -670 0 0 {name=MP1
l=5u
w=0.5u
ng=1
m=4
model=sg13_lv_pmos
spiceprefix=X}
C {sg13_lv_pmos.sym} 1640 -550 0 0 {name=MS1
l=5u
w=0.5u
ng=1
m=2
model=sg13_lv_pmos
spiceprefix=X}
C {lab_wire.sym} 1660 -610 0 0 {name=w1
sig_type=std_logic
lab=vd1}
C {lab_pin.sym} 1600 -670 0 0 {name=lz1
sig_type=std_logic
lab=vz}
C {lab_pin.sym} 1600 -550 0 0 {name=ls1
sig_type=std_logic
lab=di_trim_b[1]}
C {sg13_lv_pmos.sym} 2120 -670 0 0 {name=MP0
l=5u
w=0.5u
ng=1
m=2
model=sg13_lv_pmos
spiceprefix=X}
C {sg13_lv_pmos.sym} 2120 -550 0 0 {name=MS0
l=5u
w=0.5u
ng=1
m=2
model=sg13_lv_pmos
spiceprefix=X}
C {lab_wire.sym} 2140 -610 0 0 {name=w0
sig_type=std_logic
lab=vd0}
C {lab_pin.sym} 2080 -670 0 0 {name=lz0
sig_type=std_logic
lab=vz}
C {lab_pin.sym} 2080 -550 0 0 {name=ls0
sig_type=std_logic
lab=di_trim_b[0]}
C {iopin.sym} 2260 -440 0 0 {name=p4
lab=iout}
C {sg13_lv_pmos.sym} 2360 -670 0 0 {name=MPD
hide_texts=true
l=5u
w=0.5u
ng=1
m=40
model=sg13_lv_pmos
spiceprefix=X}
C {iopin.sym} -20 -300 2 0 {name=p5
lab=vss}
C {ipin.sym} 20 -400 0 0 {name=p6
lab=di_trim_b[3:0]}
