v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
T {2:1 switched-capacitor divider, vcm = vdd/2} 100 -1060 0 0 0.6 0.6 {}
T {-) phase 1 (di_phi1_b low): the flying capacitors sit between vdd and vcm, vcf_t at vdd and vcf_b at vcm
-) phase 2 (di_phi2 high): between vcm and vss, vcf_t at vcm and vcf_b at vss
-) every switch is one device, because vcf_t only swings between vcm and vdd and vcf_b between vss and vcm: MS2 is a PMOS and MS3 an NMOS, so each sits hard off (negative Vgs) while its terminals are at the far rail
-) CF1 has PLUS on vcf_t and CF2 on vcf_b, so whatever each plate carries to the substrate is the same on both nets and cancels at vcm = vdd/2
-) CR is a thick-oxide NMOS on vss, a thin-oxide gate would leak nA at 0.75 V
-) MDEC is supply decoupling in the two layout corners beside the switches, the same thick-oxide NMOS with its gate on vdd
-) MDR and MDS are layout dummies with every terminal on vss: MDR closes both ends of the CR strip, MDS fills the right switch corner beside MS4} 100 -1000 0 0 0.35 0.35 {}
N 100 -800 160 -800 {lab=di_phi1_b}
N 100 -760 160 -760 {lab=di_phi2}
N 100 -720 160 -720 {lab=vdd}
N 100 -680 160 -680 {lab=vss}
N 400 -640 340 -640 {lab=di_phi1_b}
N 440 -670 440 -720 {lab=vdd}
N 440 -640 480 -640 {lab=vdd}
N 440 -610 440 -560 {lab=vcf_t}
N 440 -560 1060 -560 {lab=vcf_t}
N 620 -560 620 -490 {lab=vcf_t}
N 780 -560 780 -490 {lab=vcf_t}
N 620 -430 620 -380 {lab=vcf_b}
N 780 -430 780 -380 {lab=vcf_b}
N 440 -380 1060 -380 {lab=vcf_b}
N 440 -380 440 -330 {lab=vcf_b}
N 400 -300 340 -300 {lab=di_phi2}
N 440 -300 480 -300 {lab=vss}
N 440 -270 440 -230 {lab=vss}
N 1060 -560 1060 -545 {lab=vcf_t}
N 1060 -485 1060 -470 {lab=vcm}
N 1020 -515 980 -515 {lab=di_phi2}
N 1060 -515 1100 -515 {lab=vss}
N 1060 -455 1060 -470 {lab=vcm}
N 1020 -425 980 -425 {lab=di_phi1_b}
N 1060 -425 1100 -425 {lab=vdd}
N 1060 -395 1060 -380 {lab=vcf_b}
N 1060 -470 1140 -470 {lab=vcm}
N 1140 -470 1200 -470 {lab=vcm}
N 1140 -470 1140 -380 {lab=vcm}
N 1140 -380 1300 -380 {lab=vcm}
N 1340 -410 1380 -410 {lab=vss}
N 1340 -380 1380 -380 {lab=vss}
N 1340 -350 1380 -350 {lab=vss}
N 1380 -410 1380 -350 {lab=vss}
N 1380 -350 1380 -310 {lab=vss}
N 1540 -410 1580 -410 {lab=vss}
N 1540 -380 1580 -380 {lab=vss}
N 1540 -350 1580 -350 {lab=vss}
N 1580 -410 1580 -350 {lab=vss}
N 1580 -350 1580 -310 {lab=vss}
N 1460 -380 1500 -380 {lab=vdd}
C {ipin.sym} 100 -800 0 0 {name=p1 lab=di_phi1_b}
C {ipin.sym} 100 -760 0 0 {name=p2 lab=di_phi2}
C {iopin.sym} 100 -720 2 0 {name=p3 lab=vdd}
C {iopin.sym} 100 -680 2 0 {name=p4 lab=vss}
C {iopin.sym} 1200 -470 0 0 {name=p5 lab=vcm}
C {sg13_hv_pmos.sym} 420 -640 0 0 {name=MS1
l=0.45u
w=4u
ng=1
m=1
model=sg13_hv_pmos
spiceprefix=X
}
C {sg13_hv_nmos.sym} 420 -300 0 0 {name=MS4
l=0.45u
w=2u
ng=1
m=1
model=sg13_hv_nmos
spiceprefix=X
}
C {sg13_lv_pmos.sym} 1040 -425 0 0 {name=MS2
l=0.5u
w=4u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
C {sg13_lv_nmos.sym} 1040 -515 0 0 {name=MS3
l=0.5u
w=4u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {cap_cmomf.sym} 620 -460 0 0 {name=CF1[3:0]
model=cap_cmomf
w=4.2e-6
l=12.4e-6
mmin=3
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
hide_texts=true
}
C {cap_cmomf.sym} 780 -460 2 0 {name=CF2[3:0]
model=cap_cmomf
w=4.2e-6
l=12.4e-6
mmin=3
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
hide_texts=true
}
C {sg13_hv_nmos.sym} 1320 -380 0 0 {name=CR
l=10u
w=10u
ng=1
m=7
model=sg13_hv_nmos
spiceprefix=X}
C {lab_pin.sym} 340 -640 0 0 {name=l1 lab=di_phi1_b}
C {lab_pin.sym} 440 -720 0 0 {name=l2 lab=vdd}
C {lab_pin.sym} 480 -640 0 1 {name=l3 lab=vdd}
C {lab_pin.sym} 340 -300 0 0 {name=l4 lab=di_phi2}
C {lab_pin.sym} 480 -300 0 1 {name=l5 lab=vss}
C {lab_pin.sym} 440 -230 0 0 {name=l6 lab=vss}
C {lab_pin.sym} 980 -515 0 0 {name=l7 lab=di_phi2}
C {lab_pin.sym} 1100 -515 0 1 {name=l8 lab=vss}
C {lab_pin.sym} 980 -425 0 0 {name=l9 lab=di_phi1_b}
C {lab_pin.sym} 1100 -425 0 1 {name=l10 lab=vdd}
C {lab_pin.sym} 1380 -310 0 0 {name=l15 lab=vss}
T {CF1} 560 -465 0 0 0.3 0.3 {}
T {CF2} 810 -465 0 0 0.3 0.3 {}
T {PLUS on vcf_t} 540 -440 0 0 0.2 0.2 {}
T {PLUS on vcf_b} 800 -440 0 0 0.2 0.2 {}
C {lab_wire.sym} 520 -560 0 0 {name=l11 lab=vcf_t}
C {lab_wire.sym} 520 -380 0 0 {name=l12 lab=vcf_b}
T {vcm} 1080 -490 0 0 0.3 0.3 {}
C {title.sym} 160 -20 0 0 {name=l0 author="(c) 2026 Michael Koefinger"}
C {sg13_hv_nmos.sym} 1520 -380 0 0 {name=MDEC
l=10u
w=4u
ng=1
m=2
model=sg13_hv_nmos
spiceprefix=X}
C {lab_pin.sym} 1460 -380 0 0 {name=l16 lab=vdd}
C {lab_pin.sym} 1580 -310 0 0 {name=l17 lab=vss}
T {decap} 1500 -440 0 0 0.3 0.3 {}
N 1740 -410 1780 -410 {lab=vss}
N 1740 -380 1780 -380 {lab=vss}
N 1740 -350 1780 -350 {lab=vss}
N 1780 -410 1780 -350 {lab=vss}
N 1780 -350 1780 -310 {lab=vss}
N 1700 -380 1680 -380 {lab=vss}
N 1680 -380 1680 -310 {lab=vss}
N 1680 -310 1780 -310 {lab=vss}
C {sg13_hv_nmos.sym} 1720 -380 0 0 {name=MDR
l=0.45u
w=10u
ng=1
m=2
model=sg13_hv_nmos
spiceprefix=X}
C {lab_pin.sym} 1780 -310 0 0 {name=l18 lab=vss}
N 1940 -410 1980 -410 {lab=vss}
N 1940 -380 1980 -380 {lab=vss}
N 1940 -350 1980 -350 {lab=vss}
N 1980 -410 1980 -350 {lab=vss}
N 1980 -350 1980 -310 {lab=vss}
N 1900 -380 1880 -380 {lab=vss}
N 1880 -380 1880 -310 {lab=vss}
N 1880 -310 1980 -310 {lab=vss}
C {sg13_hv_nmos.sym} 1920 -380 0 0 {name=MDS
l=0.45u
w=1.5u
ng=1
m=1
model=sg13_hv_nmos
spiceprefix=X}
C {lab_pin.sym} 1980 -310 0 0 {name=l19 lab=vss}
T {dummies} 1790 -440 0 0 0.3 0.3 {}
