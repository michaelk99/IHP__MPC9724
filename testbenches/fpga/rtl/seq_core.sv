// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// ============================================================================
// The master board's sequencer. Runs the ROM program picked by the DIP
// switches at reset and emits one record per SPI transaction and per
// conversion. seqasm.py writes the ROM and bench_capture.py reads the records,
// and both carry the field layouts this decodes and encodes.
//
// A capture waits CAPT_DELAY after adc_conv before it reads HIGH. The slave
// stores a new ADC word only on sclk edges after its three-flop flag
// synchronizer has seen valid_strobe, about four sclk periods, and reading
// sooner returns the previous conversion.
// ============================================================================

`timescale 1ns / 1ps

module seq_core #(
    parameter int RST_CYC    = 4096,   // DUT reset low, then the wait after it, in clk cycles
    parameter int CAPT_DELAY = 1600    // adc_conv to the HIGH read, 64 us at 25 MHz
)(
    input  wire         clk,
    input  wire         rst_b,
    input  wire  [3:0]  program_sel,
    output logic [7:0]  pc,
    input  wire  [31:0] rom_q,         // rom[pc], combinational
    output logic [4:0]  spi_addr,
    output logic [15:0] spi_data,
    output logic        spi_start,
    input  wire         spi_strobe,
    input  wire  [15:0] spi_rx,
    input  wire         spi_busy,
    input  wire         adc_conv,      // synchronized to clk
    output logic        dut_rst_b,
    output logic        loopback,
    output logic        stream_start,
    input  wire  [16:0] stream_index,
    output logic [62:0] rec,
    output logic        rec_valid,
    input  wire         rec_ready,
    output logic        halted,
    output logic        capturing
);
    localparam logic [3:0] OP_SPI = 4'd1, OP_WAITC = 4'd2, OP_STREAM = 4'd3,
                           OP_CAPT = 4'd4, OP_LOOP = 4'd5, OP_RESET = 4'd6;
    localparam logic [2:0] K_SPI = 3'd0, K_ADC = 3'd1, K_START = 3'd2, K_RESET = 3'd3,
                           K_LOOP = 3'd4, K_STREAM = 3'd5, K_END = 3'd7;
    localparam logic [12:0] RST_N = RST_CYC;
    localparam logic [12:0] DLY_N = CAPT_DELAY;

    typedef enum logic [3:0] {
        S_BOOT, S_TABLE, S_FETCH, S_SPI_GO, S_SPI_WAIT, S_REC, S_RST_LO, S_RST_HI,
        S_WAITC, S_CAPT, S_CAPT_DLY, S_HI_GO, S_HI_WAIT, S_LO_GO, S_LO_WAIT, S_HALT
    } state_t;
    state_t state, ret;

    wire [3:0]  op  = rom_q[31:28];
    wire [15:0] arg = rom_q[15:0];

    // Records other than SPI and ADC: the kind, pc at [22:15], one value bit at [0].
    function automatic logic [62:0] mk(input logic [2:0] kind, input logic [7:0] at, input logic v);
        mk = {kind, 37'd0, at, 14'd0, v};
    endfunction

    logic        conv_d, conv_pend;
    logic [10:0] conv_cnt, tag_cnt, cap_cnt;
    logic [16:0] tag_idx, cap_idx;
    logic [15:0] wait_n, hi_q;
    logic        forever_q;
    logic [12:0] dly;
    logic [3:0]  prog_q;
    wire         conv_edge = adc_conv & ~conv_d;

    always_ff @(posedge clk) begin
        if (!rst_b) begin
            state <= S_BOOT;  ret <= S_FETCH;  pc <= '0;
            spi_addr <= '0;  spi_data <= '0;  spi_start <= 1'b0;
            dut_rst_b <= 1'b1;  loopback <= 1'b0;  stream_start <= 1'b0;
            rec <= '0;  rec_valid <= 1'b0;  halted <= 1'b0;  capturing <= 1'b0;
            conv_d <= 1'b0;  conv_pend <= 1'b0;  conv_cnt <= '0;  tag_cnt <= '0;  tag_idx <= '0;
            cap_cnt <= '0;  cap_idx <= '0;  wait_n <= '0;  hi_q <= '0;  forever_q <= 1'b0;
            dly <= '0;  prog_q <= '0;
        end else begin
            spi_start    <= 1'b0;
            stream_start <= 1'b0;
            conv_d       <= adc_conv;

            case (state)
                S_BOOT: begin
                    prog_q <= program_sel;
                    pc     <= {4'd0, program_sel};
                    state  <= S_TABLE;
                end
                S_TABLE: begin
                    pc        <= rom_q[7:0];
                    rec       <= {K_START, prog_q, 16'hD5A1, 40'd0};
                    rec_valid <= 1'b1;
                    ret       <= S_FETCH;
                    state     <= S_REC;
                end
                S_FETCH: begin
                    case (op)
                        OP_SPI: begin
                            spi_addr <= rom_q[20:16];
                            spi_data <= arg;
                            state    <= S_SPI_GO;
                        end
                        OP_WAITC: begin
                            wait_n    <= arg;
                            conv_pend <= 1'b0;
                            pc        <= pc + 8'd1;
                            state     <= S_WAITC;
                        end
                        OP_STREAM: begin
                            stream_start <= 1'b1;
                            rec          <= mk(K_STREAM, pc, 1'b0);
                            rec_valid    <= 1'b1;
                            pc           <= pc + 8'd1;
                            ret          <= S_FETCH;
                            state        <= S_REC;
                        end
                        OP_CAPT: begin
                            wait_n    <= arg;
                            forever_q <= (arg == 16'd0);
                            conv_pend <= 1'b0;
                            capturing <= 1'b1;
                            pc        <= pc + 8'd1;
                            state     <= S_CAPT;
                        end
                        OP_LOOP: begin
                            loopback  <= arg[0];
                            rec       <= mk(K_LOOP, pc, arg[0]);
                            rec_valid <= 1'b1;
                            pc        <= pc + 8'd1;
                            ret       <= S_FETCH;
                            state     <= S_REC;
                        end
                        OP_RESET: begin
                            dut_rst_b <= 1'b0;
                            dly       <= RST_N;
                            state     <= S_RST_LO;
                        end
                        default: begin       // HALT, and anything seqasm never emits
                            rec       <= mk(K_END, pc, 1'b0);
                            rec_valid <= 1'b1;
                            ret       <= S_HALT;
                            state     <= S_REC;
                        end
                    endcase
                end
                S_SPI_GO: if (!spi_busy) begin
                    spi_start <= 1'b1;
                    state     <= S_SPI_WAIT;
                end
                S_SPI_WAIT: if (spi_strobe) begin
                    rec       <= {K_SPI, spi_addr, spi_data, spi_rx, pc, 15'd0};
                    rec_valid <= 1'b1;
                    pc        <= pc + 8'd1;
                    ret       <= S_FETCH;
                    state     <= S_REC;
                end
                S_REC: if (rec_ready) begin
                    rec_valid <= 1'b0;
                    state     <= ret;
                end
                S_RST_LO: if (dly == 13'd0) begin
                    dut_rst_b <= 1'b1;
                    dly       <= RST_N;
                    state     <= S_RST_HI;
                end else begin
                    dly <= dly - 13'd1;
                end
                S_RST_HI: if (dly == 13'd0) begin
                    rec       <= mk(K_RESET, pc, 1'b0);
                    rec_valid <= 1'b1;
                    pc        <= pc + 8'd1;
                    ret       <= S_FETCH;
                    state     <= S_REC;
                end else begin
                    dly <= dly - 13'd1;
                end
                S_WAITC: if (wait_n == 16'd0) begin
                    state <= S_FETCH;
                end else if (conv_pend) begin
                    conv_pend <= 1'b0;
                    wait_n    <= wait_n - 16'd1;
                end
                S_CAPT: if (!forever_q && wait_n == 16'd0) begin
                    capturing <= 1'b0;
                    state     <= S_FETCH;
                end else if (conv_pend) begin
                    conv_pend <= 1'b0;
                    cap_cnt   <= tag_cnt;
                    cap_idx   <= tag_idx;
                    dly       <= DLY_N;
                    state     <= S_CAPT_DLY;
                end
                S_CAPT_DLY: if (dly == 13'd0) begin
                    state <= S_HI_GO;
                end else begin
                    dly <= dly - 13'd1;
                end
                S_HI_GO: if (!spi_busy) begin
                    spi_addr  <= 5'b1_0000;      // read ADC_DATA_CH0_HIGH first
                    spi_data  <= 16'd0;
                    spi_start <= 1'b1;
                    state     <= S_HI_WAIT;
                end
                S_HI_WAIT: if (spi_strobe) begin
                    hi_q  <= spi_rx;
                    state <= S_LO_GO;
                end
                S_LO_GO: if (!spi_busy) begin
                    spi_addr  <= 5'b1_0001;      // then LOW, frozen by the HIGH read
                    spi_start <= 1'b1;
                    state     <= S_LO_WAIT;
                end
                S_LO_WAIT: if (spi_strobe) begin
                    rec       <= {K_ADC, hi_q, spi_rx, cap_cnt, cap_idx};
                    rec_valid <= 1'b1;
                    if (!forever_q) wait_n <= wait_n - 16'd1;
                    ret       <= S_CAPT;
                    state     <= S_REC;
                end
                S_HALT: halted <= 1'b1;
                default: state <= S_HALT;
            endcase

            // Last, so an edge in the cycle a consumer clears the flag is kept.
            if (conv_edge) begin
                conv_cnt  <= conv_cnt + 11'd1;
                tag_cnt   <= conv_cnt + 11'd1;
                tag_idx   <= stream_index;
                conv_pend <= 1'b1;
            end
        end
    end
endmodule
