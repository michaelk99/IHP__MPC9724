// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// ============================================================================
// FPGA evaluation harness for dsa1_dig_top. Not part of the chip.
// ----------------------------------------------------------------------------
// The point of evaluating the top level rather than the decimator alone is that
// the readout is the chip's own: an SPI master reads the decimated word out of
// ADC_DATA_CH0_HIGH and _LOW exactly as it will in silicon, so the bring-up
// software is exercised at the same time as the filter.
//
// The harness adds only what a board needs and the chip gets from its padframe:
//
//   - a 65536 Hz clock, from the board oscillator through fs_gen, or from the
//     master board's clk_fs pin when SW1 is on at reset, or when a host asked
//     for it through AUX_CTRL_0 (below). The second is the chip's real
//     situation: clock and bitstream both arrive from outside.
//   - a reset synchronizer on the push button ANDed with the master's reset pin,
//     which is pulled up so the board still runs alone
//   - the three-flop synchronizer on data_in that sg13cmos5l_dsa1_dig_core
//     puts in front of the macro, so the FPGA sees what the silicon will
//
// Read HIGH before LOW. The slave latches the low word when the high word is
// read, so a pair belongs to one conversion. See testbenches/README.md.
// ============================================================================

`timescale 1ns / 1ps
`include "../../rtl/dsa1_regs.vh"  // generated from macros/dsa1_dig/regmap.yaml

module dsa1_dig_fpga_top #(
    parameter int CLK_HZ = 25_000_000,   // board oscillator
    parameter int FS_HZ  = 65_536,       // modulator sample rate
    parameter int ACC_W  = 32,
    parameter bit LED_AUX = 1'b0,        // 0: adc_conv and o_tst_ctrl[6:0], 1: o_aux_ctrl[7:0]
    parameter bit DUO     = 1'b0         // 1: also the DSA1 die's digital back end, behind a bus switch
)(
    input  wire        clk_board,
    input  wire        rst_n_btn,        // active low, asynchronous
    input  wire        rst_n_pin,        // from the master board, pulled up
    input  wire        ext_fs_sw,        // SW1, read in reset: 1 takes clk_fs from the pin
    input  wire        clk_fs_pin,       // 65536 Hz from the master board
    input  wire        data_in_pin,      // the one-bit modulator stream
    input  wire        sclk_pin,
    input  wire        mosi_pin,
    input  wire        ss_pin,           // active low
    output wire        miso_pin,
    output wire        adc_conv_pin,
    output wire [7:0]  led               // see LED_AUX
);
    // ---- reset, two flops into the board domain -----------------------------
    wire rst_n = rst_n_btn & rst_n_pin;
    logic [1:0] rst_sync;
    always_ff @(posedge clk_board or negedge rst_n) begin
        if (!rst_n) rst_sync <= 2'b00;
        else        rst_sync <= {rst_sync[0], 1'b1};
    end
    wire rst_b = rst_sync[1];

    // ---- 65536 Hz clock, own or the master's --------------------------------
    wire clk_fs_int;
    /* verilator lint_off UNUSEDSIGNAL */
    wire fs_fall;
    /* verilator lint_on UNUSEDSIGNAL */
    fs_gen #(.CLK_HZ(CLK_HZ), .FS_HZ(FS_HZ), .ACC_W(ACC_W)) u_fs (
        .clk(clk_board), .rst_b(rst_b), .clk_fs(clk_fs_int), .fall(fs_fall));

    // A host without a hand on the board picks the clock and, with DUO, the back end
    // through TEST_CTRL_1, plain storage on both dies:
    //   bit 0  clk_fs from the pin, 0 from fs_gen, applied at the next reset
    //   bit 1  the bus to the legacy slave, 0 to this chip's, DUO only
    // The harness takes the writes off the bus itself, so it works whichever slave is
    // selected and needs no port on either die. A DUT reset clears the dies' copies,
    // this one it keeps until the board button, since P resets the DUT on the pin's clock.
    wire [15:0] tc1_word;
    wire        tc1_tog;
    tc1_sniff u_tc1 (.sclk(sclk_pin), .ss(ss_pin), .mosi(mosi_pin), .data(tc1_word), .tog(tc1_tog));
    // the toggle through two flops, the word it announces has been still since the write
    logic [2:0]  tc1_s = 3'b000;
    logic        tc1_primed = 1'b0;
    logic [15:0] tc1 = 16'h0000;
    always_ff @(posedge clk_board or negedge rst_n_btn) begin
        if (!rst_n_btn) begin
            tc1_primed <= 1'b0;
            tc1 <= 16'h0000;
        end else begin
            tc1_primed <= 1'b1;
            if (tc1_primed && tc1_s[2] != tc1_s[1]) tc1 <= tc1_word;
        end
    end
    always_ff @(posedge clk_board) tc1_s <= {tc1_s[1:0], tc1_tog};
    wire ext_req    = tc1[`DSA1_TEST_CTRL_1_CLK_FS_EXT_LSB];
    wire legacy_req = DUO && tc1[`DSA1_TEST_CTRL_1_BUS_DSA1_LSB];
    wire [15:0] o_aux_ctrl, o_aux_ctrl_legacy;

    // The bus moves on a rising edge of ss, at the start of the gap between two
    // frames, so neither slave ever sees part of one. The request comes from a
    // write, whose own ss rise follows it.
    logic [2:0] ss_s = 3'b111;
    logic       sel_legacy = 1'b0;
    always_ff @(posedge clk_board or negedge rst_n_btn) begin
        if (!rst_n_btn) begin
            ss_s <= 3'b111;
            sel_legacy <= 1'b0;
        end else begin
            ss_s <= {ss_s[1:0], ss_pin};
            if (ss_s[1] && !ss_s[2]) sel_legacy <= legacy_req;
        end
    end

    // The select only moves in reset, so the mux never glitches a running design.
    logic ext_fs;
    always_ff @(posedge clk_board) begin
        if (!rst_b) ext_fs <= ext_fs_sw | ext_req;
    end
    wire clk_fs = ext_fs ? clk_fs_pin : clk_fs_int;

    // ---- input synchronizer, as sg13cmos5l_dsa1_dig_core does ---------------
    logic d1, d2, d3;
    always_ff @(posedge clk_fs) begin
        if (!rst_b) {d1, d2, d3} <= 3'b000;
        else        {d1, d2, d3} <= {data_in_pin, d1, d2};
    end

    // ---- the macro, and with DUO the DSA1 die's back end next to it ----------
    // sclk and mosi reach both, since each needs a running sclk for its ADC flag
    // synchronizer. ss reaches only the selected one, miso and adc_conv come from it.
    wire        adc_conv, adc_conv_legacy, miso, miso_legacy;
    wire [15:0] o_tst_ctrl;
    /* verilator lint_off UNUSEDSIGNAL */
    wire [34:0] o_bias_cfg;
    wire [1:0]  o_rst_ctrl_b;
    wire [10:0] o_en_ctrl;
    wire [15:0] o_lf_cfg;
    wire [18:0] o_clk_cfg;
    wire [29:0] o_uwb_tx_cfg;
    /* verilator lint_on UNUSEDSIGNAL */

    dsa1_dig_top u_dut (
        .clk         (clk_fs),
        .rst_b       (rst_b),
        .sclk        (sclk_pin),
        .mosi        (mosi_pin),
        .miso        (miso),
        .ss          (ss_pin | sel_legacy),
        .data_in     (d3),
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

    // The DSA1 die's back end as taped out, decimator v4 at 256 Hz, from legacy.mk.
    generate
        if (DUO) begin : g_legacy
            /* verilator lint_off PINCONNECTEMPTY */
            legacy_dsa1_dig_top u_legacy (
                .clk(clk_fs), .rst_b(rst_b), .sclk(sclk_pin), .mosi(mosi_pin), .miso(miso_legacy),
                .ss(ss_pin | !sel_legacy), .data_in(d3), .adc_conv(adc_conv_legacy),
                .o_bias_cfg(), .o_rst_ctrl_b(), .o_en_ctrl(), .o_lf_cfg(), .o_clk_cfg(), .o_tst_ctrl(),
                .o_uwb_tx_cfg(), .o_aux_ctrl(o_aux_ctrl_legacy));
            /* verilator lint_on PINCONNECTEMPTY */
        end else begin : g_single
            assign {miso_legacy, adc_conv_legacy} = 2'b00;
            assign o_aux_ctrl_legacy = 16'h0000;
        end
    endgenerate

    assign miso_pin     = sel_legacy ? miso_legacy : miso;
    assign adc_conv_pin = sel_legacy ? adc_conv_legacy : adc_conv;
    // AUX_CTRL_0 drives nothing on the chip, so a board shows it on its LEDs, all
    // eight, and a host writes it freely, with none of TEST_CTRL_0's rules. With DUO
    // the LEDs are the selected back end's.
    wire [15:0] aux_sel = sel_legacy ? o_aux_ctrl_legacy : o_aux_ctrl;
    assign led = !LED_AUX ? {adc_conv, o_tst_ctrl[6:0]} : aux_sel[7:0];
endmodule

// TEST_CTRL_1 as the host writes it, taken off the bus. Framed as dsa1_ic_bus_slave
// frames: ss high resets, sclk falling shifts mosi in, 5 address bits (the read flag
// first), a load bit, then 16 data bits. The word counts at its last bit, the 22nd
// falling edge, when the slave stores it too. A read or a frame cut short is nothing.
module tc1_sniff #(
    parameter logic [3:0] ADDR = `DSA1_TEST_CTRL_1_ADDR
)(
    input  wire         sclk,
    input  wire         ss,
    input  wire         mosi,
    output logic [15:0] data = 16'h0000,    // sclk domain, the last word written to ADDR
    output logic        tog = 1'b0          // sclk domain, flips with every such write
);
    logic [4:0]  cnt;                        // falling edges of this frame so far
    logic [20:0] sh;                         // the bits before this edge, the first in sh[20] at the 22nd
    always_ff @(negedge sclk or posedge ss) begin
        if (ss) begin
            cnt <= 5'd0;
        end else begin
            sh <= {sh[19:0], mosi};
            if (cnt != 5'd31) cnt <= cnt + 5'd1;
            if (cnt == 5'd21 && !sh[20] && sh[19:16] == ADDR) begin
                data <= {sh[14:0], mosi};
                tog  <= ~tog;
            end
        end
    end
endmodule
