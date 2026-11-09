# MPC9724 data sheet

A page of pointers. Every number here is taken from the document it links, none is new.

The chip carries `dsa1_dig`, the 128x decimation filter with an SPI slave and the configuration register file, and `dsm2_core`, a first-order discrete-time delta-sigma modulator on its own VDDA segment of the pad ring.

| | |
|---|---|
| Technology | IHP SG13CMOS5L, Metal1 to Metal4 plus TopMetal1 |
| Die | 1300 x 1300 um |
| Package | QFN24, 4 x 4 mm, 0.5 mm pitch, packaged by IHP |
| Supplies | VDD 1.2 V, VDDA 1.5 V (1.45 to 1.55 V) for dsm2, IOVDD 3.3 V |
| Clocks | `clk` 65536 Hz, `sclk` 200 kHz, `dsm_clk` 1.024 MHz for dsm2 |
| Output rate | 512 Hz, 22-bit words over SPI |
| dsm2 input | `vi` single ended, full scale +-0.75 V around VDDA/2 |

| for | see |
|---|---|
| Specification, blocks, operating states | [specifications.md](specifications.md) |
| Pins, leads, board rules | [pinout.md](pinout.md) |
| Bring-up order and the SPI frame | [host_protocol.md](host_protocol.md) |
| Registers | [regmap.md](regmap.md) |
| Floorplan and decoupling | [floorplan.md](floorplan.md) |
| ESD, HBM | [esd_hbm.md](esd_hbm.md) |
| Bond plan | [../packaging/result.md](../packaging/result.md) |
| Sign-off record and dispositions | [signoff.md](signoff.md) |
| TRL checklist | [TRL-Mixed-Signal-IP.md](TRL-Mixed-Signal-IP.md) |
| Where IHP's expected items are in this repository | [layout_index.md](layout_index.md) |
