# dsm2_core

Placeholder views of the dsm2 first-order DT delta-sigma modulator, so the chip RTL and flow can be built before the real GDS and LEF are drawn.

Source of the real macro: `sg13cmos5l_batmon`, `macros/dsm2` (commit to be recorded when the views arrive).

| File | What it is |
| --- | --- |
| `verilog/dsm2_core.v` | Blackbox with the agreed 17 ports, 21 pin bits |
| `verilog/dsm2_core_model.v` | Bench-only model: PRBS15 (`x^15 + x^14 + 1`, seed 1) on `di_clk`, not the circuit |
| `abstract/abstract_gen.py` | Writes the placeholder LEF and outline GDS: `klayout -n sg13cmos5l -zz -r abstract_gen.py` |
| `abstract/check_pins.py` | LEF pins against the blackbox ports |
| `lef/dsm2_core.lef`, `gds/dsm2_core.gds` | Generated, 155.0 x 185.0 um, Metal3 pins only |

Pins are 1 x 2 um on Metal3.
East edge from the south-east corner: `vi`, `vcm`, `ibias_test`, `vdd` at 10 um pitch.
South edge: `do_q_b`, `do_q`, `di_clk` at 110, 105 and 100 um from the west edge, so the south-east corner stays free for dsm2's internal `vi` route.
West edge from the south-west corner: `do_q_dec`, the controls, `di_ena` at 10 um pitch.
`vdd` (y 36 to 46 um) and `vss` (y 50 to 60 um) are 2 um deep stubs on the east edge, 10 um tall, for the chip top's straps.
OBS covers Metal1 to Metal4 over the outline except the pin shapes.

The real LEF and GDS replace all of this.
