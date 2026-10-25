// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Testbench for the hardened dsa1_dig_top: decimator running on PRBS input, SPI read-out of the ADC words after
// every conversion, one register write and read-back. Runs unchanged on the ghdl-synth Verilog of the RTL and on the
// gate-level netlist, so it uses no hierarchical references. Every observation goes to dsa1_dig_top_out.txt, and
// make sim-gl requires the RTL and gate-level files to be identical.
//
// sclk runs permanently, as with the SPI master's sclk_permanent_active = '1': the register file captures a new
// ADC word only on sclk edges while the synchronized flag is high, so CLK_PERIOD must not be shorter than SCLK_PERIOD.
//
// SPI frame of dsa1_ic_bus_slave, 23 falling sclk edges with ss low: 5 address bits MSB first (bit 4 = read only),
// 1 load cycle, 16 data bits MSB first (miso out, mosi in), 1 store cycle. The slave samples mosi on the falling
// edge and drives miso on the rising edge.

`timescale 1ns / 1ps
`include "dsa1_regs.vh"  // generated from macros/dsa1_dig/regmap.yaml

module dsa1_dig_top_tb;

    // Power run: -Pdsa1_dig_top_tb.CLK_PERIOD=15258.789 -Pdsa1_dig_top_tb.SCLK_PERIOD=5000 -Pdsa1_dig_top_tb.N_VCD=8
    parameter real    CLK_PERIOD  = 50.0;
    parameter real    SCLK_PERIOD = 20.0;
    parameter integer N_VCD       = 0;    // conversions dumped to dsa1_dig_top.vcd, 0 = no VCD
    localparam N_CONV   = 60;             // conversions observed in a normal run
    localparam N_SETTLE = 20;             // conversions before the VCD window
    localparam N_STIM   = 40;             // conversions observed per stimulus mode
    localparam N_REP    = 136;            // per repeating mode, two 64-conversion periods

    reg  clk, sclk, rst_b, mosi, ss, data_in;
    wire miso, adc_conv;
    wire [34:0] o_bias_cfg;
    wire [1:0]  o_rst_ctrl_b;
    wire [10:0] o_en_ctrl;
    wire [15:0] o_lf_cfg;
    wire [18:0] o_clk_cfg;
    wire [15:0] o_tst_ctrl;
    wire [29:0] o_uwb_tx_cfg;
    wire [15:0] o_aux_ctrl;

    reg  [22:0] lfsr;                     // PRBS23, x^23 + x^18 + 1
    reg  [15:0] rd;
    integer f_out, n_conv;

    dsa1_dig_top uut (
        .clk(clk), .rst_b(rst_b), .sclk(sclk), .mosi(mosi), .miso(miso), .ss(ss),
        .data_in(data_in), .adc_conv(adc_conv),
        .o_bias_cfg(o_bias_cfg), .o_rst_ctrl_b(o_rst_ctrl_b), .o_en_ctrl(o_en_ctrl), .o_lf_cfg(o_lf_cfg),
        .o_clk_cfg(o_clk_cfg), .o_tst_ctrl(o_tst_ctrl), .o_uwb_tx_cfg(o_uwb_tx_cfg), .o_aux_ctrl(o_aux_ctrl)
    );

    initial begin
        clk = 0;
        forever #(CLK_PERIOD/2) clk = ~clk;
    end

    // Offset by a quarter period so sclk and clk edges never coincide
    initial begin
        sclk = 0;
        #(SCLK_PERIOD/4);
        forever #(SCLK_PERIOD/2) sclk = ~sclk;
    end

    // Modulator bitstream: PRBS, changed 1 ns after each rising clk edge
    initial begin
        lfsr = 23'h1;
        data_in = 1'b0;
        forever begin
            @(posedge clk);
            lfsr <= {lfsr[21:0], lfsr[22] ^ lfsr[17]};
            #1 data_in = lfsr[0];
        end
    end

    // One SPI transaction on the running sclk. Returns the 16 bits shifted out on miso.
    task spi(input [4:0] addr, input [15:0] wdata, output [15:0] rdata);
        reg [22:0] frame;
        integer k;
        begin
            frame = {addr, 1'b0, wdata, 1'b0};
            rdata = 16'h0;
            @(negedge sclk);
            #1 ss = 1'b0;
            mosi = frame[22];
            for (k = 22; k >= 0; k = k - 1) begin
                @(negedge sclk);
                if (k >= 1 && k <= 16) rdata = {rdata[14:0], miso};
                #1 mosi = (k > 0) ? frame[k-1] : 1'b0;
            end
            @(negedge sclk);
            #1 ss = 1'b1;
            mosi = 1'b0;
        end
    endtask

    task log_read(input [4:0] addr, input [8*12-1:0] name);
        begin
            spi(addr, 16'h0000, rd);
            if (^rd === 1'bx) begin
                $display("Error: SPI read of %0s is x at t = %t", name, $time);
                $fatal(1);
            end
            $fwrite(f_out, "%0s %04h\n", name, rd);
        end
    endtask

    // One stimulus pattern: arm, let the filter settle to zero on the idle
    // alternation, fire, then log n conversions. Writing the arm value
    // first also drops the trigger, which is what re-arms after the previous
    // pattern.
    task run_stim(input [15:0] arm, input [15:0] fire, input [8*8-1:0] tag, input integer n);
        begin
            spi({1'b0, `DSA1_TEST_CTRL_0_ADDR}, arm, rd);
            repeat (N_SETTLE) @(posedge adc_conv);
            spi({1'b0, `DSA1_TEST_CTRL_0_ADDR}, fire, rd);
            repeat (n) begin
                @(posedge adc_conv);
                repeat (4) @(posedge sclk);
                log_read({1'b1, `DSA1_ADC_DATA_CH0_HIGH_ADDR}, {tag, "_HI"});
                log_read({1'b1, `DSA1_ADC_DATA_CH0_LOW_ADDR}, {tag, "_LO"});
            end
        end
    endtask

    initial begin
        f_out = $fopen("dsa1_dig_top_out.txt", "w");
        if (f_out == 0) begin
            $display("Error: could not open output file.");
            $finish;
        end
        ss = 1'b1; mosi = 1'b0;
        rst_b = 1'b0;
        // The decimator reset is synchronous, so hold reset over several clk edges.
        repeat (10) @(posedge clk);
        #1 rst_b = 1'b1;

        // Reset values, then a write and read-back of AUX_CTRL_0 (addr 12, not used by the analog core)
        log_read({1'b1, `DSA1_BLOCK_CTRL_1_ADDR}, "BLOCK_CTRL_1");
        log_read({1'b1, `DSA1_TEST_CTRL_0_ADDR}, "TEST_CTRL_0");
        spi({1'b0, `DSA1_AUX_CTRL_0_ADDR}, 16'hA55A, rd);
        log_read({1'b1, `DSA1_AUX_CTRL_0_ADDR}, "AUX_CTRL_0");
        // CHIP_ID at 15 is read only: 0x0001 names this die, the DSA1 die reads 0x0000 there.
        // TEST_CTRL_1 at 13 is storage, which the FPGA harness decodes from the bus.
        log_read({1'b1, `DSA1_CHIP_ID_ADDR}, "CHIP_ID");
        if (rd !== `DSA1_CHIP_ID_RESET) begin
            $display("Error: CHIP_ID reads %04h, not %04h", rd, `DSA1_CHIP_ID_RESET);
            $fatal(1);
        end
        spi({1'b0, `DSA1_CHIP_ID_ADDR}, 16'hBEEF, rd);
        log_read({1'b1, `DSA1_CHIP_ID_ADDR}, "CHIP_ID");
        if (rd !== `DSA1_CHIP_ID_RESET) begin
            $display("Error: a write changed CHIP_ID to %04h", rd);
            $fatal(1);
        end
        spi({1'b0, `DSA1_TEST_CTRL_1_ADDR}, 16'h5AA5, rd);
        log_read({1'b1, `DSA1_TEST_CTRL_1_ADDR}, "TEST_CTRL_1");
        if (rd !== 16'h5AA5) begin
            $display("Error: TEST_CTRL_1 reads %04h after writing 5AA5", rd);
            $fatal(1);
        end
        spi({1'b0, `DSA1_TEST_CTRL_1_ADDR}, 16'h0000, rd);
        $fwrite(f_out, "o_aux_ctrl %04h o_en_ctrl %03h o_bias_cfg %09h\n", o_aux_ctrl, o_en_ctrl, o_bias_cfg);

        // Conversions: read the coherent HIGH/LOW pair after every adc_conv
        n_conv = 0;
        while (n_conv < ((N_VCD > 0) ? N_SETTLE + N_VCD : N_CONV)) begin
            @(posedge adc_conv);
            n_conv = n_conv + 1;
            if (N_VCD > 0 && n_conv == N_SETTLE + 1) begin
                // Level 1 dumps the nets of the DUT scope only, which in the flat netlist are all nets and no cell internals.
                $dumpfile("dsa1_dig_top.vcd");
                $dumpvars(1, uut);
            end
            // Wait for the 3-FF flag synchronizer to move the sample into the register file.
            repeat (4) @(posedge sclk);
            log_read({1'b1, `DSA1_ADC_DATA_CH0_HIGH_ADDR}, "ADC_HIGH");
            log_read({1'b1, `DSA1_ADC_DATA_CH0_LOW_ADDR}, "ADC_LOW");
        end

        // ------------------------------------------------------------
        // Stimulus test mode, TEST_CTRL_0 bit 11 enable, 12 trigger,
        // 14:13 pattern, 15 option. Base 0x0500 keeps FLAG_SYNC_EN and
        // PAD_Q_EN set, which every write to this register has to preserve.
        //
        //   arm         fire        pattern
        //   0x0D00      0x1D00      step +
        //   0x2D00      0x3D00      impulse
        //   0x4D00      0x5D00      half scale, mean +1/2
        //   0x6D00      0x7D00      step -
        //   0xCD00      0xDD00      PRBS23
        //   0x8D00      0x9D00      step +, repeat every 64 conversions
        //   0xAD00      0xBD00      impulse, repeat every 64
        //   0xED00      0xFD00      step -, repeat every 64
        //
        // Enable first and let the pipeline flush to the alternating idle,
        // which the filter rejects, so the output settles to zero. Only then
        // trigger. Firing on the enable edge instead buries the event under
        // the filter's previous contents, about 32 output samples of them.
        //
        // The trigger only arms: the pattern starts at the next valid_strobe,
        // so every shot begins on the same phase of the decimation window.
        // ------------------------------------------------------------
        if (N_VCD == 0) begin
            run_stim(16'h0D00, 16'h1D00, "STEP_P", N_STIM);
            run_stim(16'h2D00, 16'h3D00, "IMP", N_STIM);
            run_stim(16'h4D00, 16'h5D00, "HALF", N_STIM);
            run_stim(16'h6D00, 16'h7D00, "STEP_N", N_STIM);
            run_stim(16'hCD00, 16'hDD00, "PRBS", N_STIM);
            // two periods and more of each repeating pattern, so the wrap is in the log
            run_stim(16'h8D00, 16'h9D00, "STEP_PR", N_REP);
            run_stim(16'hAD00, 16'hBD00, "IMP_R", N_REP);
            run_stim(16'hED00, 16'hFD00, "STEP_NR", N_REP);

            spi({1'b0, `DSA1_TEST_CTRL_0_ADDR}, 16'h0500, rd);          // leave it as we found it
        end

        $display("Simulation complete: %0d conversions.", n_conv);
        $fclose(f_out);
        $finish;
    end

endmodule
