* hold MC control, one mismatch sample per ngspice process
* SPDX-FileCopyrightText: 2026 Michael Koefinger
* SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
* run_mc.sh fills @SEED@, @BENCH@, @VH@ (half supply), @VLO@ and @VHI@ (20 and 80 %).
.control
set num_threads=1
setseed @SEED@
source @BENCH@

* Path run: launch Q drives capture D. Edge 2 is the measured edge.
tran 0.5p 3.8n 0 2p
meas tran tcl when v(cklau)=@VH@ rise=2
meas tran tcc when v(ckcap)=@VH@ rise=2
meas tran tcm when v(com)=@VH@ rise=2
meas tran tdd when v(dcap)=@VH@ fall=1
meas tran td80 when v(dcap)=@VHI@ fall=1
meas tran td20 when v(dcap)=@VLO@ fall=1
meas tran tc20 when v(com)=@VLO@ rise=2
meas tran tc80 when v(com)=@VHI@ rise=2
meas tran q0 find v(qc) at=2.9n
meas tran q1 find v(qc) at=3.78n
let skew = tcc - tcl
let c2q = tdd - tcl
let arr = tdd - tcc
let dslew = td20 - td80
let cslew = tc80 - tc20
let ok = (q0 < @VH@) & (q1 > @VH@)
* Shell variables survive the plot change of the next tran, vectors do not.
set skew = "$&skew"
set c2q = "$&c2q"
set arr = "$&arr"
set ok = "$&ok"
set dslew = "$&dslew"
set cslew = "$&cslew"
set tcm = "$&tcm"
set tcc = "$&tcc"

* Hold search: capture D from an ideal ramp with the launch Q slew, one clock edge only, so the capture CK edge is tcc - 2 ns.
alter rsw = 1e12
alter rsrc = 1
alter @vck[pulse] = [ 0 @VDD@ 1n 53.3p 53.3p 10n 20n ]
setplot const
let trd = $dslew / 0.6
* Window of about 10 sigma around the nominal 24 ps, 11 halvings give 0.06 ps.
let lo = -40p
let hi = 90p
let n = 0
while n < 11
  let tau = (lo + hi) / 2
  let tdv = $tcc - 2n + tau - trd / 2
  alter @vdsrc[pulse] = [ @VDD@ 0 $&tdv $&trd $&trd 100n 200n ]
  tran 0.5p 1.8n 0 2p
  meas tran qe find v(qc) at=1.78n
  set qe = "$&qe"
  setplot const
  if $qe > @VH@
    let hi = tau
  else
    let lo = tau
  end
  let n = n + 1
end
let slack = $arr - hi
* A result at a window end means the window was too small.
let inwin = (hi < 89p) & (lo > -39p)
echo "RESULT @SEED@ $skew $c2q $arr $&hi $&slack $ok $&inwin $dslew $cslew $tcm"
.endc
