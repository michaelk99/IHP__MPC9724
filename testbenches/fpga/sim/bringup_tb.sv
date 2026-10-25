// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// ============================================================================
// Both boards, wired pin for pin as the jumpers connect them. The two
// oscillators are independent and DUT_PPM apart. The UART is decoded here and
// every byte goes to LOG, one hex byte per line, for models/bench_capture.py.
//
// Stops at the END record or after N_ADC conversion records. +vcd dumps
// everything, which is only sensible with a short TIMEOUT_MS.
// ============================================================================

`timescale 1ns / 1ps

module bringup_tb;
    parameter     SEQ_MEM    = "seq.mem";
    parameter     STREAM_MEM = "stream.mem";
    parameter     LOG        = "uart.hex";
    parameter int PROGRAM    = 0;
    parameter int EXT_FS     = 1;      // DUT SW1: take clk_fs from the master
    parameter int DUT_PPM    = 50;     // DUT oscillator this much fast
    parameter int N_ADC      = 48;
    parameter int TIMEOUT_MS = 600;

    localparam real BIT_NS   = 1.0e9 / 115200.0;
    localparam real T_M_HALF = 20.0;
    localparam real T_D_HALF = 20.0 * (1.0 - DUT_PPM * 1.0e-6);

    logic clk_m = 1'b0, clk_d = 1'b0, rst_n = 1'b0;
    always #(T_M_HALF) clk_m = ~clk_m;
    always #(T_D_HALF) clk_d = ~clk_d;

    wire data_in, clk_fs, sclk, mosi, ss, miso, adc_conv, dut_rst_n, tx;
    wire [7:0] led_m, led_d;

    dsa1_master_fpga_top #(.SEQ_MEM(SEQ_MEM), .STREAM_MEM(STREAM_MEM)) u_master (
        .clk_board(clk_m), .rst_n_btn(rst_n), .sw(4'(PROGRAM)),
        .data_in_pin(data_in), .clk_fs_pin(clk_fs), .sclk_pin(sclk), .mosi_pin(mosi),
        .ss_pin(ss), .miso_pin(miso), .adc_conv_pin(adc_conv), .dut_rst_n_pin(dut_rst_n),
        .uart_tx_pin(tx), .led(led_m));

    dsa1_dig_fpga_top u_dut (
        .clk_board(clk_d), .rst_n_btn(1'b1), .rst_n_pin(dut_rst_n), .ext_fs_sw(EXT_FS != 0),
        .clk_fs_pin(clk_fs), .data_in_pin(data_in), .sclk_pin(sclk), .mosi_pin(mosi),
        .ss_pin(ss), .miso_pin(miso), .adc_conv_pin(adc_conv), .led(led_d));

    integer     fd, n_bytes = 0, n_adc = 0, pos = 0;
    logic [7:0] b;
    logic [2:0] kind;

    initial begin
        if ($test$plusargs("vcd")) begin
            $dumpfile("bringup_tb.vcd");
            $dumpvars(0, bringup_tb);
        end
        fd = $fopen(LOG, "w");
        #1000 rst_n = 1'b1;
        #(TIMEOUT_MS * 1.0e6);
        $display("FAIL: timeout after %0d ms, %0d bytes, %0d conversion records",
                 TIMEOUT_MS, n_bytes, n_adc);
        $fclose(fd);
        $finish;
    end

    initial forever begin
        @(negedge tx);
        #(BIT_NS * 1.5);
        for (int i = 0; i < 8; i++) begin
            b[i] = tx;
            #(BIT_NS);
        end
        if (tx !== 1'b1) begin
            $display("FAIL: UART framing error at byte %0d", n_bytes);
            $fclose(fd);
            $finish;
        end
        $fwrite(fd, "%02x\n", b);
        n_bytes = n_bytes + 1;
        if (b[7]) begin
            kind = b[6:4];
            pos  = 1;
        end else begin
            pos = pos + 1;
        end
        if (pos == 9) begin
            if (kind == 3'd1) n_adc = n_adc + 1;
            if (kind == 3'd7 || n_adc >= N_ADC) begin
                $display("DONE: program %0d, %0d bytes, %0d conversion records at %0t",
                         PROGRAM, n_bytes, n_adc, $time);
                $fclose(fd);
                $finish;
            end
        end
    end
endmodule
