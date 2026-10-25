# Supply start-up bench

The chip as the measurement bench meets it: the supplies ramping, the host holding `rst_n` low through the ramp, then SPI reads through the pads. Our tapeout sign-off requires this simulation.

```
testbenches/startup/run_startup.sh                       inside IIC-OSIC-TOOLS, at the repo root, the AGENTS.md environment set
testbenches/startup/run_power_v111.sh <worktree> <tag>   the DSA1 state on an older tag's chip, for the report's comparison
testbenches/startup/cell_leakage.py --v111 ...          the DC current of each IO cell type, to explain the comparison
```

It writes `verification/startup/startup_report.md`, `startup.png` and `bounce.png` and exits non-zero on a failed check. The five orders run side by side, `io_first`, `core_first`, `bounce`, `power_dsa1` and `power_dsm`.

## What it simulates

- **The ESD clamp cell** at transistor level from its CDL, `ip/sg13cmos5l_ip__clamp_vddvss`.
- **IO cells as transistors**, from the pinned image's PDK, `libs.ref/sg13cmos5l_io/spice/sg13cmos5l_io.spice`, the PDK the layout's IO cell GDS comes from, for every tree including a v1.1.1 worktree. The repo's snapshot `ip/sg13cmos5l_io_custom` is another PDK version with other LevelDown and clamp diode devices and is not simulated. Models are the typical HV and LV MOS, `rppd` and diode models. `sub!`, the body the IO cells' `rppd` resistors take, is tied to ground. The two clamp copies are in, the cut cells are empty subcircuits, the filler cells carry nothing and the rails of the VDD and VDDA bands are ideal nets.
- **Three core supplies**: IOVDD at 3.3 V, VDD at 1.2 V and VDDA at 1.5 V. The pads of the VDDA segment are the three analog pads, `dsm_clk`, `do_q`, `do_q_b` and the VDDA supply pad.
- **dsm2 is not simulated.** The macro is a box. The `do_q` and `do_q_b` pads get bench sources on the VDDA regulator side with 1 kOhm, which toggle at every rising `dsm_clk` edge, complementary, 5 ns after it, in the orders that run dsm2 (`bounce`, `power_dsm`) and sit low otherwise. The adc_conv gate is left out of the core and its pad is driven the same way on the VDD side, with one pulse of one clk cycle in `bounce`, because the real pulse comes once per output sample, 1.95 ms apart. The pad inputs driven this way are found from the netlist, the ones no core cell drives.
- **The core as XSPICE.** `gen_startup.py` flattens the macro's powered netlist into the chip's and keeps every functional cell, 11666 of 72 types. `spi2xspice.py` turns them into XSPICE gates and flops from the EZ130 typical liberty. Two fixes come first: the liberty is cut to the used cells, because the flop banks' bundles stop its parser, and every pin is renamed `P0Q`, `P1Q`, ..., because it substitutes pin names as text and `B` corrupts `AB`. The 26 `CGX3` clock gates on the sclk tree are a `statetable` it cannot read, so `--patch-xspice` models each as a latch open while CK is low and an AND. Alone, with ideal inputs, this core reads all three registers right.
- **Core outputs follow the core supply.** XSPICE drives a fixed 1.2 V, so each output into a pad goes through a source scaled by the regulator side of VDD and 1 kOhm, a standard cell's output.
- **The host on the IOVDD rail**: every pin it drives, `dsm_clk` among them, is scaled by the regulator side of IOVDD and goes through 50 Ohm. Its clocks, clk and sclk, start 20 us before it releases `rst_n`, after both ramps. mosi moves on sclk's rising edges, because the slave samples on the falling ones, as the host's I2S engine does.
- **Supplies with 0.5 Ohm** of output resistance, grounds with 0.1 Ohm.
- **The orders.** `core_first` is the board order, VDD and VDDA from 10 us and IOVDD from 150 us, each a 100 us ramp. `io_first` is the reverse, IOVDD first. `rst_n` is released at 300 us, then CHIP_ID, TEST_CTRL_0 and AUX_CTRL_0 are read at 400 kHz. `vi` and `vcm` are open (1 MOhm to ground) in these two, as `ibias_test` is in all.
- **Ground bounce (`bounce`)**: VDD and VDDA first, and the package between die and board. Each bond wire is 1 nH and 50 mOhm per mm of its length in `packaging/result.md`, plus 0.5 nH and 10 mOhm of QFN lead. VSS and IOVSS downbond to the paddle, which the leads to the cavity and the exposed pad (0.1 nH) tie to the board ground, as bonded, with every downbond of a net in parallel. 100 nF at each supply pin, 10 pF on each output pin. `vi` and `vcm` come from a source at half of the VDDA regulator voltage through 50 Ohm. From 290 us `dsm_clk` runs at 1.024 MHz and `do_q` and `do_q_b` toggle. CHIP_ID is read, SPARE_14 (16 free bits) is written with 0x5555 and read back, which toggles `miso` at every sclk bit, and one `adc_conv` pulse falls inside that read.
- **The DSA1 power state (`power_dsa1`, `power_dsm`)**: no SPI frames, `sclk` idle low, `clk` and `data_in` toggling at 65.536 kHz, `data_in` on clk's falling edges. `power_dsa1` is dsm2 off with `dsm_clk` low. `power_dsm` has `dsm_clk` at 1.024 MHz and the `do_q` pads switching, with DEC_SRC low. The currents are the mean over the last 8 data_in periods, 125 dsm_clk periods, so the toggling averages out.

## Solver settings, and why

The IO cells' clamps, level shifters and antenna diodes stall ngspice ("timestep too small") or make it creep without end while one supply is near 0 or at the edges. What it took, each found by a run that stalled without it:
- the largest step capped at 200 ns, since the default, a fiftieth of the run, strides into the clamps' turn-on
- the antenna diodes with a transit time of 0 (`diodes_bench.lib`, a copy of the PDK's `diodes.lib`): their 700 ns stalled the solver when ground bounce nudged one forward, and here they only ever sit reverse biased or near 0
- the host's and the core's sources scaled by the regulator sides, not by the chip's own rails, which formed a loop with the pads
- no clock edge during a ramp: one into a pad on a rail of a few 10 mV stalled the solver for good
- `run_startup.sh`'s `RECIPES`, tried in turn: 1 fF on every node, then a looser reltol, then 1 TOhm to ground, then the trapezoidal method, with a watchdog that ends an attempt after 15 minutes without progress. Each order's report names the recipe that ran

## What it checks

Per supply order, in `startup_check.py`:
- the three reads return 0x0001, 0x0500 and 0xFF00
- no supply current (IOVDD, VDD, VDDA) stays above 10 mA for more than 1 us, as latch-up or fighting drivers would. Shorter peaks are reported
- in the board order the `do_q` and `do_q_b` pads stay below 0.33 V. For IOVDD first the pads' rise is reported, the spike the board rule avoids

For `bounce`: the CHIP_ID and SPARE_14 reads, that the stimulus ran (dsm_clk, do_q and do_q_b at 90 % of their edges, at least 12 miso edges in the SPARE_14 read, the adc_conv pulse), and no core input crossing its threshold more often than the host's pin does between 295 us and the end. It reports the die's VSS, IOVSS and paddle against the board ground, droop and overshoot of IOVDD to IOVSS, VDD to VSS and VDDA to VSS on the die, the peak current in the supply wires, and the swing of `vi`, `vcm` and `ibias_test` on the die (the `padres` side of the analog pads) against their quiet level.

For the power orders: the VDD current of `power_dsm` must equal the one of `power_dsa1` within the resolution of the runs, the larger of the difference between the window's two halves and 0.1 % of the current. With `verification/startup/power_v111.json` present, the report also compares the DSA1 state with the v1.1.1 chip.

`run_isolation_mutant.sh` is a real broken input for the isolation check: a copy of the netlist with the `vdd` pins of the two `do_q` pads on VDD must make the check fail, and it requires that. It runs `power_dsm` on the copy.

Each check has a broken input in the self-tests (`--self-test` of both scripts): a sustained current, one on the VDDA wire, a wrong read, a pad spike, a glitch, a 1 % rise of VDD with dsm2 running, a dead aggressor in the bounce, and traces or currents missing from the data, which fail instead of passing.

## What it cannot say

- **The power-up state of the flops.** XSPICE starts every flop at 0. Silicon starts them anywhere, and the chip has no power-on reset, so until the first `rst_n` low the registers, and with them the dsm2 control inputs, are undefined. The host must hold `rst_n` low until all supplies are up, which this bench assumes and does not prove.
- **The core's supply current.** The XSPICE gates draw nothing from VDD, so the VDD current is the IO cells' and the clamps' only. The core's own is 3.061 uW typical on v1.1.1, from `make power-vcd`.
- **dsm2.** Its outputs are bench sources and its inputs are open, so nothing of the macro's own supply current, noise or loading is in it.
- Package, bond wire and board parasitics in the two supply orders, and any corner but typical. The bounce case has the package, with assumed wire and board values. Its core draws no current and its decap cells are not in it, so VDD to VSS there shows the IO cells' core side only.
