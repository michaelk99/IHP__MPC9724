# FPGA Emulation Flow

Emulates the `counter` macro on three FPGA boards. The synthesis top is `counter_top` from [`../rtl/`](../rtl/), its ports (`clock_i`, `reset_n_i`, `enable_i`, `counter_value_o[7:0]`) map straight onto board pins, without a board-top wrapper. One shared fragment, [`fpga.mk`](fpga.mk), runs the flow, and a board is one folder, see [Adding a Board](#adding-a-board).


## Supported Boards

| Board | Directory | FPGA | Toolchain | Verified here |
| --- | --- | --- | --- | --- |
| pico-ice | [`pico-ice/`](pico-ice/) | Lattice iCE40UP5K | Yosys -> nextpnr-ice40 -> icepack | Bitstream built, default board |
| iCEBreaker | [`icebreaker/`](icebreaker/) | Lattice iCE40UP5K | Yosys -> nextpnr-ice40 -> icepack | Bitstream built |
| ULX3S | [`ulx3s/`](ulx3s/) | Lattice ECP5-85F | Yosys -> nextpnr-ecp5 -> ecppack | Bitstream built |

Pin assignment per board:

| Board | `clock_i` | `reset_n_i` | `enable_i` | `counter_value_o[7:0]` |
| --- | --- | --- | --- | --- |
| pico-ice | 12 MHz oscillator | on-board push button, active low | GPIO | Bottom left PMOD |
| iCEBreaker | 12 MHz oscillator | S1 button, active low | PMOD 1A pin 1 | PMOD 2 |
| ULX3S | 25 MHz oscillator | `BTN_PWRn`, already active low | J1 `gp[0]`, pulled up so it runs by default | The eight on-board LEDs |


## Toolchain

[IIC-OSIC-TOOLS](https://github.com/iic-jku/IIC-OSIC-TOOLS) ships the build chain for all three boards: `verilator`, `yosys`, `nextpnr-ice40` with `icepack` for the iCE40 boards, `nextpnr-ecp5` with `ecppack` for the ULX3S.

The container has no USB access (`openFPGALoader` and `dfu-util` are not installed, `iceprog` is but cannot reach a board), so build the bitstream inside and run `load_bitstream`/`flash_bitstream` on the host. `visualize` and `visualize_generic` need `netlistsvg`, `svgo` and `rsvg-convert`, which are not in the container either.


## Picking a Board

[`Makefile`](Makefile) is a dispatcher that forwards targets to `<BOARD>/Makefile`, with `BOARD ?= pico-ice`:

```sh
make all                     # pico-ice, the default
make BOARD=icebreaker all
make -C icebreaker all
```

`BOARD` is checked against the folders that hold a `Makefile`:

```console
$ make BOARD=nosuchboard synthesis
Unknown BOARD 'nosuchboard'. Available: icebreaker pico-ice ulx3s.
```

The dispatcher handles `help`, `open` and `clean` itself. `clean` cleans **every** board, so `make clean` in the macro removes all FPGA outputs.


## How the Flow Is Put Together

Four layers:

| File | One per | Holds |
| --- | --- | --- |
| [`fpga.mk`](fpga.mk) | flow | The targets themselves and the defaults common to all boards |
| [`arch/<arch>.mk`](arch/) | FPGA architecture | The synthesis, place-and-route and packing toolchain (`ice40`, `ecp5`) |
| `<board>/Makefile` | board | Everything about one board: top module, pin file, device, package, how to load and flash it |
| [`dut.mk`](dut.mk) | design under test | The RTL sources, shared by every board |

A board `Makefile` includes `dut.mk`, names the top module and pin file, sets device and programmer variables, and includes `fpga.mk` last, which pulls in the `arch/` fragment named by `ARCH`:

```make
TOP := counter_top

include ../dut.mk
MODULES_SYNTH := $(DUT_SRCS)

PCF_FILE := icebreaker.pcf

ARCH         := ice40
ICE40_DEVICE := --up5k --package sg48

# openFPGALoader has no dedicated iCEBreaker board profile.
# Must be `=`, not `:=`, since BITSTREAM is only defined later, by fpga.mk.
LOAD_CMD  = iceprog -S $(BITSTREAM)
FLASH_CMD = iceprog $(BITSTREAM)

include $(TOP_FPGA_DIR)/fpga.mk
```

### Set by `dut.mk`

| Variable | | Description |
| --- | --- | --- |
| `SRC_DIR` | mandatory | RTL source directory |
| `DUT_SRCS` | mandatory | Ordered source file list of the design under test |
| `TOP_FPGA_DIR` | mandatory | Path from a board folder back to this one |

### Set by the board `Makefile`

| Variable | | Description |
| --- | --- | --- |
| `TOP` | mandatory | Synthesis top module and instance name |
| `MODULES_SYNTH` | mandatory | Ordered source file list for `TOP`, here just `$(DUT_SRCS)` |
| `PCF_FILE` | mandatory | Board pin constraint file |
| `ARCH` | mandatory | Selects the `arch/<arch>.mk` fragment |
| `ICE40_DEVICE`, `ECP5_DEVICE` | mandatory | Device and package, whichever the board's architecture uses |
| `OPENFPGALOADER_BOARD` | mandatory | openFPGALoader board profile, unless `LOAD_CMD`/`FLASH_CMD` are set instead |
| `OPENFPGALOADER_FLAGS` | optional | Extra openFPGALoader flags |
| `LOAD_CMD`, `FLASH_CMD` | optional | Complete load and flash commands, replacing the openFPGALoader default, for boards it has no profile for |

### Set by `arch/<arch>.mk`

| Variable | | Description |
| --- | --- | --- |
| `TARGET`, `SYNTH_OPTS` | mandatory | Yosys synth pass and its options |
| `SYNTH_CMD` | optional | Complete synthesis command, replacing `TARGET`/`SYNTH_OPTS`, for a synth pass that does not fit the `$(TARGET) $(SYNTH_OPTS) -top $(TOP)` shape |
| `PNR_CMD`, `PNR_OUT` | mandatory | Place-and-route command and its output file |
| `PNR_ARGS`, `PNR_DEPS` | optional | Place-and-route flags, and extra prerequisites |
| `PNR_GUI_CMD` | optional | Interactive place-and-route command. Left empty where there is none, `pr-gui` then says so and stops |
| `PACK_CMD`, `BITSTREAM` | mandatory | Bitstream packing command and output file |

`fpga.mk` and the `arch/` fragments assign with `?=`, so a board `Makefile` can override anything. `fpga.mk` errors when its include comes too early or a mandatory variable is missing.

### Adding a Board

1. Create `<board>/` with a `Makefile` like the one above (`ARCH`, device, package, flash variables) and the pin constraint file it names, mapping `clock_i`, `reset_n_i`, `enable_i` and `counter_value_o[7:0]` onto board pins.
2. For a new FPGA family, also create `arch/<arch>.mk` with its synthesis, place-and-route and packing commands, and check the container carries its toolchain.

`fpga.mk` and the dispatcher stay unchanged. `make help` and `make clean` pick the board up from its folder.


## Makefile Targets

### Show Available Targets

The default target is `help`. In a board folder it also shows the architecture, top cell and constraint file:

```sh
make
make help
make -C ulx3s help
```


### Open the Design Files

Opens a file browser for this folder (`sak-open.py` from the [IIC-OSIC-TOOLS](https://github.com/iic-jku/IIC-OSIC-TOOLS)):

```sh
make open
```

gvim opens the `Makefile` and `README.md`, the desktop's handler a generated `.pdf`. Only the file types listed in [the counter README](../README.md#open-the-design-files) get a button, so the pin constraint files are not shown. The RTL is in [`../rtl/`](../rtl/). `make open OPEN_ARGS=--all` includes the build outputs.

> [!NOTE]
> Needs a display: the container's VNC/noVNC desktop or X11 forwarding. The `.pdf` buttons need the full VNC/noVNC session.


### Flow Targets

```sh
make clean                       # remove <board>/build/ of every board
make -C ulx3s clean              # only this board
make lint-verilog                # Verilator, CELL=counter_top: constants.sv, counter.sv, counter_top.sv
make lint-verilog CELL=counter   # constants.sv with ../rtl/<CELL>.sv (or .v)
make lint-verilog-all            # both in sequence
make synthesis                   # technology-mapped, Yosys synth_* pass from arch/<arch>.mk
make BOARD=ulx3s synthesis
make synthesis_generic           # generic netlist and Yosys graph
make visualize                   # PDF of the technology-mapped netlist
make visualize_generic           # PDF of the generic netlist
make pr                          # place-and-route
make pr-gui                      # in the nextpnr GUI
make gen_bitstream
make load_bitstream              # into SRAM, lost on power cycle
make flash_bitstream             # into the board's flash, survives a power cycle
make convert                     # SystemVerilog top to Verilog
```

> [!NOTE]
> `load_bitstream` and `flash_bitstream` are not part of `make all`. Each board Makefile sets its programmer: `openFPGALoader` for the ULX3S, `iceprog` for the iCEBreaker, `dfu-util` for the pico-ice, since openFPGALoader has a profile for neither iCE40 board. On the pico-ice the RP2040 co-processor is the DFU bootloader and forwards the bitstream to the iCE40 flash, which is why `iceprog` does not work there.


### Build All

```sh
make all
```

Runs `clean`, `lint-verilog-all`, `synthesis`, `pr` and `gen_bitstream` in that order. Outputs go to `<board>/build/`, which is git-ignored, so boards build side by side.
