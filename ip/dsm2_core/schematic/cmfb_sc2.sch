v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
T {Dummies of the layout around the sense caps, vdd (PLUS) to vss (MINUS)} 1240 -930 0 0 0.3 0.3 {}
N 1260 -850 1460 -850 {lab=vdd}
N 1260 -650 1460 -650 {lab=vss}
N 1460 -850 1460 -780 {lab=vdd}
N 1460 -720 1460 -650 {lab=vss}
N 480 -990 480 -940 {lab=di_phi2}
N 520 -990 520 -940 {lab=vdd}
N 480 -860 480 -810 {lab=d_phi2_b}
N 520 -860 520 -810 {lab=vss}
N 780 -990 780 -940 {lab=di_phi1}
N 820 -990 820 -940 {lab=vdd}
N 780 -860 780 -810 {lab=d_phi1_b}
N 820 -860 820 -810 {lab=vss}
N 540 -900 650 -900 {lab=vsw_cm_p}
N 650 -900 760 -900 {lab=vsw_cm_p}
N 480 -690 480 -640 {lab=di_phi2}
N 520 -690 520 -640 {lab=vdd}
N 480 -560 480 -510 {lab=d_phi2_b}
N 520 -560 520 -510 {lab=vss}
N 780 -690 780 -640 {lab=di_phi1}
N 820 -690 820 -640 {lab=vdd}
N 780 -560 780 -510 {lab=d_phi1_b}
N 820 -560 820 -510 {lab=vss}
N 540 -600 650 -600 {lab=vsw_vbias}
N 650 -600 760 -600 {lab=vsw_vbias}
N 480 -390 480 -340 {lab=di_phi2}
N 520 -390 520 -340 {lab=vdd}
N 480 -260 480 -210 {lab=d_phi2_b}
N 520 -260 520 -210 {lab=vss}
N 780 -390 780 -340 {lab=di_phi1}
N 820 -390 820 -340 {lab=vdd}
N 780 -260 780 -210 {lab=d_phi1_b}
N 820 -260 820 -210 {lab=vss}
N 540 -300 650 -300 {lab=vsw_cm_n}
N 650 -300 760 -300 {lab=vsw_cm_n}
N 650 -900 650 -780 {lab=vsw_cm_p}
N 650 -720 650 -600 {lab=vsw_vbias}
N 650 -600 650 -480 {lab=vsw_vbias}
N 650 -420 650 -300 {lab=vsw_cm_n}
N 840 -900 1000 -900 {lab=vo_p}
N 1000 -900 1000 -780 {lab=vo_p}
N 840 -300 1000 -300 {lab=vo_n}
N 1000 -420 1000 -300 {lab=vo_n}
N 1000 -560 1000 -480 {lab=vfb}
N 840 -600 1000 -600 {lab=vfb}
N 1000 -560 1100 -560 {lab=vfb}
N 380 -900 460 -900 {lab=vcm}
N 380 -600 460 -600 {lab=vbias}
N 400 -300 460 -300 {lab=vcm}
N 1000 -900 1100 -900 {lab=vo_p}
N 1000 -300 1100 -300 {lab=vo_n}
N 180 -1300 260 -1300 {lab=di_phi1}
N 340 -1300 420 -1300 {lab=d_phi1_b}
N 300 -1400 300 -1340 {lab=vdd}
N 300 -1260 300 -1200 {lab=vss}
N 620 -1300 700 -1300 {lab=di_phi2}
N 780 -1300 860 -1300 {lab=d_phi2_b}
N 740 -1400 740 -1340 {lab=vdd}
N 740 -1260 740 -1200 {lab=vss}
N 220 -1400 300 -1400 {lab=vdd}
N 300 -1400 740 -1400 {lab=vdd}
N 220 -1200 300 -1200 {lab=vss}
N 300 -1200 740 -1200 {lab=vss}
N 1000 -720 1000 -600 {lab=vfb}
N 1000 -600 1000 -560 {lab=vfb}
C {sw_tgate_cmfb2.sym} 500 -900 0 0 {name=XS4
}
C {lab_pin.sym} 480 -990 0 0 {name=l1 lab=di_phi2}
C {lab_pin.sym} 520 -990 0 0 {name=l2 lab=vdd}
C {lab_pin.sym} 480 -810 0 0 {name=l3 lab=d_phi2_b}
C {lab_pin.sym} 520 -810 0 0 {name=l4 lab=vss}
C {sw_tgate_cmfb2.sym} 800 -900 0 0 {name=XS3
}
C {lab_pin.sym} 780 -990 0 0 {name=l5 lab=di_phi1}
C {lab_pin.sym} 820 -990 0 0 {name=l6 lab=vdd}
C {lab_pin.sym} 780 -810 0 0 {name=l7 lab=d_phi1_b}
C {lab_pin.sym} 820 -810 0 0 {name=l8 lab=vss}
C {lab_wire.sym} 650 -900 0 0 {name=l9 lab=vsw_cm_p}
C {sw_tgate_cmfb2.sym} 500 -600 0 0 {name=XS7
}
C {lab_pin.sym} 480 -690 0 0 {name=l10 lab=di_phi2}
C {lab_pin.sym} 520 -690 0 0 {name=l11 lab=vdd}
C {lab_pin.sym} 480 -510 0 0 {name=l12 lab=d_phi2_b}
C {lab_pin.sym} 520 -510 0 0 {name=l13 lab=vss}
C {sw_tgate_cmfb2.sym} 800 -600 0 0 {name=XS6
}
C {lab_pin.sym} 780 -690 0 0 {name=l14 lab=di_phi1}
C {lab_pin.sym} 820 -690 0 0 {name=l15 lab=vdd}
C {lab_pin.sym} 780 -510 0 0 {name=l16 lab=d_phi1_b}
C {lab_pin.sym} 820 -510 0 0 {name=l17 lab=vss}
C {lab_wire.sym} 650 -600 0 0 {name=l18 lab=vsw_vbias}
C {sw_tgate_cmfb2.sym} 500 -300 0 0 {name=XS10
}
C {lab_pin.sym} 480 -390 0 0 {name=l19 lab=di_phi2}
C {lab_pin.sym} 520 -390 0 0 {name=l20 lab=vdd}
C {lab_pin.sym} 480 -210 0 0 {name=l21 lab=d_phi2_b}
C {lab_pin.sym} 520 -210 0 0 {name=l22 lab=vss}
C {sw_tgate_cmfb2.sym} 800 -300 0 0 {name=XS9
}
C {lab_pin.sym} 780 -390 0 0 {name=l23 lab=di_phi1}
C {lab_pin.sym} 820 -390 0 0 {name=l24 lab=vdd}
C {lab_pin.sym} 780 -210 0 0 {name=l25 lab=d_phi1_b}
C {lab_pin.sym} 820 -210 0 0 {name=l26 lab=vss}
C {lab_wire.sym} 650 -300 0 0 {name=l27 lab=vsw_cm_n}
C {cap_cmomf.sym} 650 -750 0 0 {name=C2[3:0]
model=cap_cmomf
w=3e-6
l=4.105e-6
mmin=1
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
}
C {cap_cmomf.sym} 650 -450 2 0 {name=C4[3:0]
model=cap_cmomf
w=3e-6
l=4.105e-6
mmin=1
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
}
C {cap_cmomf.sym} 1000 -750 0 0 {name=C1[2:0]
model=cap_cmomf
w=3e-6
l=11.39e-6
mmin=1
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
}
C {cap_cmomf.sym} 1000 -450 2 0 {name=C3[2:0]
model=cap_cmomf
w=3e-6
l=11.39e-6
mmin=1
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
}
C {opin.sym} 1100 -560 0 0 {name=p7 lab=vfb}
C {ipin.sym} 380 -900 0 0 {name=p5 lab=vcm}
C {ipin.sym} 380 -600 0 0 {name=p6 lab=vbias}
C {lab_pin.sym} 400 -300 2 0 {name=l31 lab=vcm}
C {iopin.sym} 1100 -900 0 0 {name=p4 lab=vo_p}
C {iopin.sym} 1100 -300 0 0 {name=p8 lab=vo_n}
C {inv_lv.sym} 300 -1300 0 0 {name=XINV_vphi1
}
C {ipin.sym} 180 -1300 0 0 {name=p2 lab=di_phi1}
C {lab_pin.sym} 420 -1300 0 1 {name=l35 lab=d_phi1_b}
C {inv_lv.sym} 740 -1300 0 0 {name=XINV_vphi2
}
C {ipin.sym} 620 -1300 0 0 {name=p1 lab=di_phi2}
C {lab_pin.sym} 860 -1300 0 1 {name=l37 lab=d_phi2_b}
C {iopin.sym} 220 -1400 2 0 {name=p9 lab=vdd}
C {iopin.sym} 220 -1200 2 0 {name=p3 lab=vss}
C {title.sym} 220 -80 0 0 {name=l0 author="(c) 2026 Michael Koefinger"}
C {cap_cmomf.sym} 1460 -750 0 0 {name=CDUM_COL[13:0]
model=cap_cmomf
w=3e-6
l=2e-6
mmin=1
mmax=4
subblock=0
m=1
mm_ok=1
spiceprefix=X
}
C {lab_pin.sym} 1260 -850 0 0 {name=l40 lab=vdd}
C {lab_pin.sym} 1260 -650 0 0 {name=l41 lab=vss}
