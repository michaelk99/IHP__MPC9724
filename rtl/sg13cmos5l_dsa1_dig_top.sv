// SPDX-FileCopyrightText: 2026 Simon Dorrer and Harald Pretl
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Description: Top-level chip wrapper.
// Instantiates the padframe, the chip core and custom logos.
// The padframe with bondpads, I/O cells, power ring, corners and fillers is handled by LibreLane.
// The specifications can be found in doc/specifications.md.
// The pinout mapping can be found in doc/pinout.md.
// The floorplan can be found in doc/floorplan.md.

`default_nettype none

// Instance names such as clk_pad next to the clk_PAD port are fixed by the flow.
/* verilator lint_off SIMILARNAME */

`ifdef USE_POWER_PINS
    `define SEG_SUPPLIES .iovdd(IOVDD), .iovss(IOVSS), .vdd(VDDA), .vss(VSS),
`else
    `define SEG_SUPPLIES
`endif

module sg13cmos5l_dsa1_dig_top #(
    // Power / ground pads for digital core / analog front-end
    parameter int unsigned NUM_VDD_PADS    = 1,
    parameter int unsigned NUM_VSS_PADS    = 2,

    // Power / ground pads for I/O
    parameter int unsigned NUM_IOVDD_PADS  = 1,
    parameter int unsigned NUM_IOVSS_PADS  = 1,

    // Signal pads. The chip needs 8 signals of its own: the modulator bitstream, the four SPI lines,
    // the conversion-finish flag, the dedicated clock and reset pads, and the dsm2 pads of the VDDA
    // segment below (3 analog, dsm_clk, do_q, do_q_b). The ring is 8 per side either way.
    parameter int unsigned NUM_INPUT_PADS  = 4,   // data_in, sclk, mosi, ss
    parameter int unsigned NUM_OUTPUT_PADS = 2,   // miso, adc_conv
    parameter int unsigned NUM_ANALOG_PADS = 3    // vi, vcm, ibias_test
) (
    `ifdef USE_POWER_PINS
    inout wire IOVDD,
    inout wire IOVSS,
    inout wire VDD,
    inout wire VSS,
    inout wire VDDA,
    `endif
    inout wire                       clk_PAD,
    inout wire                       rst_n_PAD,
    inout wire [NUM_INPUT_PADS-1 :0] input_PAD,
    inout wire [NUM_OUTPUT_PADS-1:0] output_PAD,
    inout wire [NUM_ANALOG_PADS-1:0] analog_PAD,
    inout wire                       dsm_clk_PAD,
    inout wire                       do_q_PAD,
    inout wire                       do_q_b_PAD
);

    // ======================================================
    // Internal nets
    // ======================================================
    // Clock
    logic                       clk_PAD2CORE;

    // Reset
    logic                       rst_n_PAD2CORE;

    // Inputs
    logic [NUM_INPUT_PADS-1 :0] input_PAD2CORE;

    // Outputs
    logic [NUM_OUTPUT_PADS-1:0] output_CORE2PAD;

    // ======================================================

    // ======================================================
    // VDD - PAD INSTANCES
    // ======================================================
    generate
        for (genvar i = 0; i < NUM_VDD_PADS; i++) begin : g_vdd_pads
            (* keep *)
            sg13cmos5l_IOPadVdd vdd_pad (
                `ifdef USE_POWER_PINS
                .iovdd (IOVDD),
                .iovss (IOVSS),
                .vdd   (VDD),
                .vss   (VSS)
                `endif
            );
        end
    endgenerate
    // ======================================================

    // ======================================================
    // VSS - PAD INSTANCES
    // ======================================================
    generate
        for (genvar i = 0; i < NUM_VSS_PADS; i++) begin : g_vss_pads
            (* keep *)
            sg13cmos5l_IOPadVss vss_pad (
                `ifdef USE_POWER_PINS
                .iovdd (IOVDD),
                .iovss (IOVSS),
                .vdd   (VDD),
                .vss   (VSS)
                `endif
            );
        end
    endgenerate
    // ======================================================

    // ======================================================
    // VDD-TO-VSS ESD CLAMP, a ring cell between the VSS and VDD pads
    // The IHP IO library clamps vdd only to iovss (doc/esd_hbm.md).
    // ======================================================
    (* keep *)
    sg13cmos5l_ip__clamp_vddvss clamp_vddvss (
        `ifdef USE_POWER_PINS
        .iovdd (IOVDD),
        .iovss (IOVSS),
        .vdd   (VDD),
        .vss   (VSS)
        `endif
    );
    // ======================================================

    // ======================================================
    // IOVDD - PAD INSTANCES
    // ======================================================
    generate
        for (genvar i = 0; i < NUM_IOVDD_PADS; i++) begin : g_iovdd_pads
            (* keep *)
            sg13cmos5l_IOPadIOVdd iovdd_pad (
                `ifdef USE_POWER_PINS
                .iovdd (IOVDD),
                .iovss (IOVSS),
                .vdd   (VDD),
                .vss   (VSS)
                `endif
            );
        end
    endgenerate
    // ======================================================

    // ======================================================
    // IOVSS - PAD INSTANCES
    // ======================================================
    generate
        for (genvar i = 0; i < NUM_IOVSS_PADS; i++) begin : g_iovss_pads
            (* keep *)
            sg13cmos5l_IOPadIOVss iovss_pad (
                `ifdef USE_POWER_PINS
                .iovdd (IOVDD),
                .iovss (IOVSS),
                .vdd   (VDD),
                .vss   (VSS)
                `endif
            );
        end
    endgenerate
    // ======================================================

    // ======================================================
    // CLOCK - PAD INSTANCE
    // ======================================================
    sg13cmos5l_IOPadIn clk_pad (
        `ifdef USE_POWER_PINS
        .iovdd (IOVDD),
        .iovss (IOVSS),
        .vdd   (VDD),
        .vss   (VSS),
        `endif
        .p2c   (clk_PAD2CORE),
        .pad   (clk_PAD)
    );
    // ======================================================

    // ======================================================
    // RESET - PAD INSTANCE (active low)
    // ======================================================
    sg13cmos5l_IOPadIn rst_n_pad (
        `ifdef USE_POWER_PINS
        .iovdd (IOVDD),
        .iovss (IOVSS),
        .vdd   (VDD),
        .vss   (VSS),
        `endif
        .p2c   (rst_n_PAD2CORE),
        .pad   (rst_n_PAD)
    );
    // ======================================================

    // ======================================================
    // SIGNAL INPUTS - PAD INSTANCES
    // ======================================================
    generate
        for (genvar i = 0; i < NUM_INPUT_PADS; i++) begin : g_inputs
            sg13cmos5l_IOPadIn input_pad (
                `ifdef USE_POWER_PINS
                .iovdd (IOVDD),
                .iovss (IOVSS),
                .vdd   (VDD),
                .vss   (VSS),
                `endif
                .p2c   (input_PAD2CORE[i]),
                .pad   (input_PAD[i])
            );
        end
    endgenerate
    // ======================================================

    // ======================================================
    // SIGNAL OUTPUTS - PAD INSTANCES
    // ======================================================
    generate
        for (genvar i = 0; i < NUM_OUTPUT_PADS; i++) begin : g_outputs
            sg13cmos5l_IOPadOut30mA output_pad (
                `ifdef USE_POWER_PINS
                .iovdd (IOVDD),
                .iovss (IOVSS),
                .vdd   (VDD),
                .vss   (VSS),
                `endif
                .c2p   (output_CORE2PAD[i]),
                .pad   (output_PAD[i])
            );
        end
    endgenerate
    // ======================================================

    // ======================================================
    // dsm2 AND ITS VDDA SEGMENT OF THE PAD RING
    // ======================================================
    // dsm2 analog nets, here and not in the core so the netlist keeps these names
    wire vi, vcm, ibias_test;
    logic dsm_clk_PAD2CORE, dsm_do_q, dsm_do_q_b, dsm_do_q_dec;

    // The VDDA segment of the pad ring, between cut_vdd_s and cut_vdd_e. Nothing in it is on VDD.
    (* keep *) sg13cmos5l_ip__cut_vdd cut_vdd_s (
        `ifdef USE_POWER_PINS
        .iovdd (IOVDD), .iovss (IOVSS), .vss (VSS)
        `endif
    );
    sg13cmos5l_IOPadIn     dsm_clk_pad (`SEG_SUPPLIES .p2c(dsm_clk_PAD2CORE), .pad(dsm_clk_PAD));
    sg13cmos5l_IOPadOut4mA do_q_pad    (`SEG_SUPPLIES .c2p(dsm_do_q),         .pad(do_q_PAD));
    sg13cmos5l_IOPadOut4mA do_q_b_pad  (`SEG_SUPPLIES .c2p(dsm_do_q_b),       .pad(do_q_b_PAD));
    /* verilator lint_off PINCONNECTEMPTY */
    (* keep *) sg13cmos5l_IOPadAnalog vi_pad  (`SEG_SUPPLIES .pad(analog_PAD[0]), .padres(vi),         .padbare());
    (* keep *) sg13cmos5l_IOPadAnalog vcm_pad (`SEG_SUPPLIES .pad(analog_PAD[1]), .padres(vcm),        .padbare());
    (* keep *) sg13cmos5l_IOPadAnalog ib_pad  (`SEG_SUPPLIES .pad(analog_PAD[2]), .padres(ibias_test), .padbare());
    /* verilator lint_on PINCONNECTEMPTY */
    (* keep *) sg13cmos5l_IOPadVdd vdda_pad (
        `ifdef USE_POWER_PINS
        .iovdd (IOVDD), .iovss (IOVSS), .vdd (VDDA), .vss (VSS)
        `endif
    );
    // VDDA-to-VSS ESD clamp, the signed-off cell on the segment's band. IOPadVdd clamps only to iovss.
    (* keep *) sg13cmos5l_ip__clamp_vddvss clamp_vdda (
        `ifdef USE_POWER_PINS
        .iovdd (IOVDD), .iovss (IOVSS), .vdd (VDDA), .vss (VSS)
        `endif
    );
    (* keep *) sg13cmos5l_ip__cut_vdd cut_vdd_e (
        `ifdef USE_POWER_PINS
        .iovdd (IOVDD), .iovss (IOVSS), .vss (VSS)
        `endif
    );

    logic       dsm_ena, dsm_rst_b, dsm_dith_en, dsm_vcm_ext, dsm_btest_en, dsm_qout_en;
    logic [3:0] dsm_trim;
    logic [1:0] dsm_dith_amp;
    dsm2_core dsm2 (
        `ifdef USE_POWER_PINS
        .vdd (VDDA), .vss (VSS),
        `else
        .vdd (), .vss (),
        `endif
        .vi (vi), .vcm (vcm), .ibias_test (ibias_test),
        .di_clk (dsm_clk_PAD2CORE), .di_ena (dsm_ena), .di_rst_b (dsm_rst_b), .di_trim (dsm_trim),
        .di_dith_en (dsm_dith_en), .di_dith_amp (dsm_dith_amp), .di_vcm_ext (dsm_vcm_ext),
        .di_btest_en (dsm_btest_en), .di_qout_en (dsm_qout_en),
        .do_q (dsm_do_q), .do_q_b (dsm_do_q_b), .do_q_dec (dsm_do_q_dec)
    );
    // ======================================================

    // ======================================================
    // CORE DESIGN
    // ======================================================
    sg13cmos5l_dsa1_dig_core #(
        .NUM_INPUT_PADS  (NUM_INPUT_PADS),
        .NUM_OUTPUT_PADS (NUM_OUTPUT_PADS)
    ) i_sg13cmos5l_dsa1_dig_core (
        `ifdef USE_POWER_PINS
        .VDD            (VDD),
        .VSS            (VSS),
        `endif

        .clk            (clk_PAD2CORE),
        .rst_n          (rst_n_PAD2CORE),

        .input_in       (input_PAD2CORE),

        .output_out     (output_CORE2PAD),

        .dsm_do_q_dec   (dsm_do_q_dec),
        .dsm_ena        (dsm_ena),
        .dsm_rst_b      (dsm_rst_b),
        .dsm_trim       (dsm_trim),
        .dsm_dith_en    (dsm_dith_en),
        .dsm_dith_amp   (dsm_dith_amp),
        .dsm_vcm_ext    (dsm_vcm_ext),
        .dsm_btest_en   (dsm_btest_en),
        .dsm_qout_en    (dsm_qout_en)
    );
    // ======================================================

    // ======================================================
    // LOGOS
    // ======================================================
    // JKU logo
    (* keep *)
    sg13cmos5l_ip__jku jku_logo ();

    // JKU names
    (* keep *)
    sg13cmos5l_ip__jku_names jku_names ();
    // ======================================================

`undef SEG_SUPPLIES

endmodule

`default_nettype wire
