// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Description: Top-level chip core.
// Instantiates the DSADC1 digital back end and connects it to the pad ring.

`default_nettype none

module sg13cmos5l_dsa1_dig_core #(
    parameter int unsigned NUM_INPUT_PADS,
    parameter int unsigned NUM_OUTPUT_PADS
)(
    `ifdef USE_POWER_PINS
    inout  wire VDD,
    inout  wire VSS,
    `endif

    input  logic clk,       // modulator sample clock, 65536 Hz
    input  logic rst_n,     // reset (active low)

    input  logic [NUM_INPUT_PADS-1 :0] input_in,        // Input value
    output logic [NUM_OUTPUT_PADS-1:0] output_out,      // Output value

    // dsm2, which sits in the top module with its pads and analog nets
    input  logic       dsm_do_q_dec,
    output logic       dsm_ena,
    output logic       dsm_rst_b,
    output logic [3:0] dsm_trim,
    output logic       dsm_dith_en,
    output logic [1:0] dsm_dith_amp,
    output logic       dsm_vcm_ext,
    output logic       dsm_btest_en,
    output logic       dsm_qout_en
);

    // ======================================================
    // Input Assignments
    // ======================================================
    logic data_in_pad;   // the 1-bit modulator bitstream
    logic sclk;          // SPI clock, a second clock domain
    logic mosi;
    logic ss;            // SPI slave select, active low

    assign data_in_pad = input_in[0];
    assign sclk        = input_in[1];
    assign mosi        = input_in[2];
    assign ss          = input_in[3];
    // ======================================================

    // ======================================================
    // Bitstream synchronizer
    // ======================================================
    // data_in arrives from a pad with no timing relationship to clk. Three
    // stages, matching what the back end already does internally for its
    // valid_strobe and dec_en crossings. The pad-to-first-flop path is a
    // false path, see the SDC.
    //
    // The macro's own SDC constrains data_in as a negedge-launched half-cycle
    // path, because in the full ADC the comparator launches the bitstream on
    // the falling edge. Here the launch is a posedge flop, so the macro sees a
    // full 15.26 us period instead of half of one. That is a relaxation, and
    // the chip-level STA reads the macro's Liberty, not its SDC.
    //
    // DEC_SRC picks dsm2's bit, which changes on the rising dsm_clk, so it needs clk = the inverted dsm_clk.
    //
    // Costs three clk cycles, about 46 us, so a sample-for-sample comparison
    // against the MATLAB model shifts by three input samples.
    logic data_in_s1, data_in_s2, data_in_s3;
    logic dec_src, dsm_bit, adc_conv_en;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            data_in_s1 <= 1'b0;
            data_in_s2 <= 1'b0;
            data_in_s3 <= 1'b0;
        end else begin
            data_in_s1 <= dec_src ? dsm_bit : data_in_pad;
            data_in_s2 <= data_in_s1;
            data_in_s3 <= data_in_s2;
        end
    end
    // ======================================================

    // ======================================================
    // DSADC1 digital back end (digital macro)
    // ======================================================
    // o_bias_cfg drives dsm2 below. The other configuration bits stay inside the die, on the chip so
    // that the taped area is comparable against the older dsa1_dig_top.
    logic        miso;
    logic        adc_conv;
    logic [34:0] o_bias_cfg;
    logic [1:0]  o_rst_ctrl_b;
    logic [10:0] o_en_ctrl;
    logic [15:0] o_lf_cfg;
    logic [18:0] o_clk_cfg;
    logic [15:0] o_tst_ctrl;
    logic [29:0] o_uwb_tx_cfg;
    logic [15:0] o_aux_ctrl;

    dsa1_dig_top dsa1_dig (
        `ifdef USE_POWER_PINS
        .VDD(VDD),
        .VSS(VSS),
        `endif
        .clk         (clk),
        .rst_b       (rst_n),
        .sclk        (sclk),
        .mosi        (mosi),
        .miso        (miso),
        .ss          (ss),
        .data_in     (data_in_s3),
        .adc_conv    (adc_conv),
        .o_bias_cfg  (o_bias_cfg),
        .o_rst_ctrl_b(o_rst_ctrl_b),
        .o_en_ctrl   (o_en_ctrl),
        .o_lf_cfg    (o_lf_cfg),
        .o_clk_cfg   (o_clk_cfg),
        .o_tst_ctrl  (o_tst_ctrl),
        .o_uwb_tx_cfg(o_uwb_tx_cfg),
        .o_aux_ctrl  (o_aux_ctrl)
    );

    // o_bias_cfg = {BIAS_CFG_1, BIAS_CFG_0, BIAS_CFG_2[2:0]}, dsm2 fields in doc/regmap.md
    localparam int unsigned CFG0 = 3;
    localparam int unsigned CFG1 = 19;
    assign dsm_trim     = o_bias_cfg[CFG0+3:CFG0];
    assign dsm_dith_en  = o_bias_cfg[CFG0+4];
    assign dsm_dith_amp = o_bias_cfg[CFG0+6:CFG0+5];
    assign dsm_ena      = o_bias_cfg[CFG1+0];
    assign dsm_rst_b    = o_bias_cfg[CFG1+1];
    assign dec_src      = o_bias_cfg[CFG1+2];
    assign dsm_btest_en = o_bias_cfg[CFG1+3];
    assign dsm_vcm_ext  = o_bias_cfg[CFG1+4];
    assign dsm_qout_en  = o_bias_cfg[CFG1+5];
    assign adc_conv_en  = o_bias_cfg[CFG1+6];

    // The only VDD cell with a dsm2 input. With DEC_SRC low its NMOS stack is cut, so a running or
    // unpowered dsm2 makes nothing on VDD switch. Hand placed so synthesis keeps exactly this.
    (* keep *) AND2X1 u_dec_src_gate (.A(dsm_do_q_dec), .B(dec_src), .Y(dsm_bit));
    // ======================================================

    // ======================================================
    // Output Assignments
    // ======================================================
    // miso is push-pull and forced low while ss is high, which is correct for
    // a single slave on its own bus. There is no miso_oe to drive a shared one.
    assign output_out[0] = miso;
    // One clk cycle wide, about 15.3 us, at the 512 Hz output rate.
    // ADC_CONV_EN low holds the pad still for a quiet power measurement
    (* keep *) AND2X1 u_adc_conv_gate (.A(adc_conv), .B(adc_conv_en), .Y(output_out[1]));
    // ======================================================

    // Configuration bits that nothing on this chip reads.
    /* verilator lint_off UNUSEDSIGNAL */
    wire _unused = &{1'b0, o_tst_ctrl, o_bias_cfg[34:26], o_bias_cfg[18:10], o_bias_cfg[2:0],
                     o_rst_ctrl_b, o_en_ctrl, o_lf_cfg, o_clk_cfg, o_uwb_tx_cfg, o_aux_ctrl, 1'b0};
    /* verilator lint_on UNUSEDSIGNAL */
endmodule

`default_nettype wire
