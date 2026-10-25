// SPDX-FileCopyrightText: 2026 Michael Köfinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// CDC bench for dsa1_dig_top: clk and sclk at any ratio, sclk with a random phase and jitter, PRBS23 from the
// stimulus generator, and the HIGH/LOW pair read after every conversion. make sim-cdc sweeps the ratio and seeds,
// models/gate_cdc.py checks every word against the bit-true model.
//
// Two crossings are exercised: the ready flag, one clk period long, into the sclk domain through its 3-FF
// synchronizer, with the 22-bit word following it unsynchronized, and the stimulus enable and trigger from the
// sclk register file into clk. A flag that no sclk edge sees leaves the old word in the register file, which the
// checker finds. Zero-delay simulation has no metastability, so this shows the capture at every phase, not the
// synchronizer's MTBF.
//
//   vvp -n tb.vvp +clk=1000 +sclk=1250 +jitter=125 +seed=3 +n=48 +out=run.txt       periods in ns

`timescale 1ns / 1ps
`include "dsa1_regs.vh"  // generated from macros/dsa1_dig/regmap.yaml

module dsa1_dig_top_cdc_tb;

    localparam N_SETTLE = 20;
    real    clk_period = 1000.0, sclk_period = 250.0, jitter = 0.0;   // jitter: peak to peak per sclk half period
    integer seed = 1, n_capt = 48;
    reg [8*256-1:0] out_name = "dsa1_dig_top_cdc_out.txt";
    initial begin
        void'($value$plusargs("clk=%f", clk_period));
        void'($value$plusargs("sclk=%f", sclk_period));
        void'($value$plusargs("jitter=%f", jitter));
        void'($value$plusargs("seed=%d", seed));
        void'($value$plusargs("n=%d", n_capt));
        void'($value$plusargs("out=%s", out_name));
    end

    reg  clk, sclk, rst_b, mosi, ss, data_in;
    wire miso, adc_conv;
    /* verilator lint_off UNUSEDSIGNAL */
    wire [34:0] o_bias_cfg;
    wire [1:0]  o_rst_ctrl_b;
    wire [10:0] o_en_ctrl;
    wire [15:0] o_lf_cfg;
    wire [18:0] o_clk_cfg;
    wire [15:0] o_tst_ctrl;
    wire [29:0] o_uwb_tx_cfg;
    wire [15:0] o_aux_ctrl;
    /* verilator lint_on UNUSEDSIGNAL */
    reg  [15:0] hi, lo;
    integer f_out, k, rng;
    real half;

    dsa1_dig_top uut (
        .clk(clk), .rst_b(rst_b), .sclk(sclk), .mosi(mosi), .miso(miso), .ss(ss),
        .data_in(data_in), .adc_conv(adc_conv),
        .o_bias_cfg(o_bias_cfg), .o_rst_ctrl_b(o_rst_ctrl_b), .o_en_ctrl(o_en_ctrl), .o_lf_cfg(o_lf_cfg),
        .o_clk_cfg(o_clk_cfg), .o_tst_ctrl(o_tst_ctrl), .o_uwb_tx_cfg(o_uwb_tx_cfg), .o_aux_ctrl(o_aux_ctrl)
    );

    initial begin
        clk = 0;
        #0.001;                                 // after the plusargs
        forever #(clk_period/2) clk = ~clk;
    end

    // sclk from a random phase, each half period jittered, never on a clk edge by construction
    initial begin
        sclk = 0;
        #0.001;
        rng = seed;                             // $urandom writes its seed back, the header keeps the given one
        #(clk_period * ($urandom(rng) % 1000) / 1000.0 + 0.1);
        forever begin
            half = sclk_period/2 + jitter * (($urandom(rng) % 1001) / 1000.0 - 0.5);
            #(half) sclk = ~sclk;
        end
    end

    initial data_in = 1'b0;                     // the stimulus generator replaces it

    task spi(input [4:0] addr, input [15:0] wdata, output [15:0] rdata);
        reg [22:0] frame;
        integer b;
        begin
            frame = {addr, 1'b0, wdata, 1'b0};
            rdata = 16'h0;
            @(negedge sclk);
            #1 ss = 1'b0;
            mosi = frame[22];
            for (b = 22; b >= 0; b = b - 1) begin
                @(negedge sclk);
                if (b >= 1 && b <= 16) rdata = {rdata[14:0], miso};
                #1 mosi = (b > 0) ? frame[b-1] : 1'b0;
            end
            @(negedge sclk);
            #1 ss = 1'b1;
            mosi = 1'b0;
        end
    endtask

    initial begin
        #0.002;
        f_out = $fopen(out_name, "w");
        $fwrite(f_out, "# clk %0.3f ns, sclk %0.3f ns, jitter %0.3f ns, seed %0d\n", clk_period, sclk_period, jitter, seed);
        ss = 1'b1; mosi = 1'b0;
        rst_b = 1'b0;
        repeat (10) @(posedge clk);
        #1 rst_b = 1'b1;
        spi({1'b0, `DSA1_TEST_CTRL_0_ADDR}, 16'hCD00, hi);           // PRBS23 armed on the idle
        repeat (N_SETTLE) @(posedge adc_conv);
        spi({1'b0, `DSA1_TEST_CTRL_0_ADDR}, 16'hDD00, hi);           // fire at the next conversion
        for (k = 0; k < n_capt; k = k + 1) begin
            @(posedge adc_conv);
            // the flag's three sclk flops and one more edge to load the word
            repeat (5) @(posedge sclk);
            spi({1'b1, `DSA1_ADC_DATA_CH0_HIGH_ADDR}, 16'h0000, hi);
            spi({1'b1, `DSA1_ADC_DATA_CH0_LOW_ADDR}, 16'h0000, lo);
            if (^{hi, lo} === 1'bx) begin
                $display("Error: x on miso at conversion %0d", k);
                $fatal(1);
            end
            $fwrite(f_out, "%0d %04h %04h\n", k, hi, lo);
        end
        $fclose(f_out);
        $finish;
    end

endmodule
