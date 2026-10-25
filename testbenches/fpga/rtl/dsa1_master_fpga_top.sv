// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// ============================================================================
// Master board of the two-board bring-up, standing in for the rest of the ADC
// and for the lab host. It owns clk_fs and data_in, as the chip's real
// surroundings do, runs dsa1_ic_bus_master against the DUT's SPI slave, and
// reports every transaction and conversion over the FTDI UART.
//
// dsa1_ic_bus_master comes from jku-phd through ghdl synth, never copied, with
// sclk left running: the slave takes a new ADC word only on sclk edges.
//
// In loopback mosi feeds miso inside this FPGA and ss stays high, so a
// connected DUT sees no transaction.
// ============================================================================

`timescale 1ns / 1ps

module dsa1_master_fpga_top #(
    parameter int CLK_HZ     = 25_000_000,
    parameter int FS_HZ      = 65_536,
    parameter int BAUD       = 115_200,
    // relative to ulx3s/ and to rtl/ alike, where yosys may resolve them from
    parameter     SEQ_MEM    = "../build/seq.mem",
    parameter     STREAM_MEM = "../build/stream.mem"
)(
    input  wire       clk_board,
    input  wire       rst_n_btn,       // active low, asynchronous
    input  wire [3:0] sw,              // program number, read at reset
    output wire       data_in_pin,
    output wire       clk_fs_pin,
    output wire       sclk_pin,
    output wire       mosi_pin,
    output wire       ss_pin,
    input  wire       miso_pin,
    input  wire       adc_conv_pin,
    output wire       dut_rst_n_pin,
    output wire       uart_tx_pin,
    output wire [7:0] led              // program, loopback, capturing, halted, adc_conv
);
    // ---- reset and input synchronizers --------------------------------------
    logic [1:0] rst_sync;
    always_ff @(posedge clk_board or negedge rst_n_btn) begin
        if (!rst_n_btn) rst_sync <= 2'b00;
        else            rst_sync <= {rst_sync[0], 1'b1};
    end
    wire rst_b = rst_sync[1];

    logic [3:0] sw_s1, sw_s2;
    logic       conv_s1, conv_s2;
    always_ff @(posedge clk_board) begin
        {sw_s2, sw_s1}     <= {sw_s1, sw};
        {conv_s2, conv_s1} <= {conv_s1, adc_conv_pin};
    end

    // ---- clk_fs and the bitstream -------------------------------------------
    wire        clk_fs, fall, stream_start;
    wire [16:0] stream_index;

    fs_gen #(.CLK_HZ(CLK_HZ), .FS_HZ(FS_HZ)) u_fs (
        .clk(clk_board), .rst_b(rst_b), .clk_fs(clk_fs), .fall(fall));

    bitstream_src #(.MEM_FILE(STREAM_MEM), .N_BITS(131072)) u_src (
        .clk(clk_board), .rst_b(rst_b), .fall(fall), .start(stream_start),
        .data_in(data_in_pin), .index(stream_index));

    assign clk_fs_pin = clk_fs;

    // ---- program ROM and sequencer ------------------------------------------
    logic [31:0] rom [0:255];
    initial $readmemh(SEQ_MEM, rom);

    wire [7:0]  pc;
    wire [31:0] rom_q = rom[pc];
    wire [4:0]  spi_addr;
    wire [15:0] spi_data, spi_rx;
    wire        spi_start, spi_strobe, spi_busy;
    wire        loopback, dut_rst_b, halted, capturing;
    wire [62:0] rec;
    wire        rec_valid, rec_ready;

    seq_core u_seq (
        .clk(clk_board), .rst_b(rst_b), .program_sel(sw_s2),
        .pc(pc), .rom_q(rom_q),
        .spi_addr(spi_addr), .spi_data(spi_data), .spi_start(spi_start),
        .spi_strobe(spi_strobe), .spi_rx(spi_rx), .spi_busy(spi_busy),
        .adc_conv(conv_s2), .dut_rst_b(dut_rst_b), .loopback(loopback),
        .stream_start(stream_start), .stream_index(stream_index),
        .rec(rec), .rec_valid(rec_valid), .rec_ready(rec_ready),
        .halted(halted), .capturing(capturing));

    assign dut_rst_n_pin = dut_rst_b;

    // ---- the SPI master -----------------------------------------------------
    wire sclk_i, mosi_i, ss_i;
    wire miso_i = loopback ? mosi_i : miso_pin;

    dsa1_ic_bus_master u_master (
        .sclk(sclk_i), .mosi(mosi_i), .miso(miso_i), .ss(ss_i),
        .data_received(spi_rx), .data_received_strobe(spi_strobe),
        .data_to_be_sent(spi_data), .addr_to_be_sent(spi_addr), .start_comm(spi_start),
        .sclk_permanent_active(1'b1), .transmit_flag(spi_busy),
        .clk(clk_board), .rst(rst_b));

    assign sclk_pin = sclk_i;
    assign mosi_pin = mosi_i;
    assign ss_pin   = loopback ? 1'b1 : ss_i;

    // ---- UART ---------------------------------------------------------------
    record_tx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) u_rec (
        .clk(clk_board), .rst_b(rst_b), .payload(rec), .valid(rec_valid),
        .ready(rec_ready), .tx(uart_tx_pin));

    assign led = {sw_s2, loopback, capturing, halted, conv_s2};
endmodule
