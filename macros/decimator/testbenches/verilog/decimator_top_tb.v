// SPDX-FileCopyrightText: 2026 Michael Koefinger
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
// Testbench for the hardened decimator_top: step response, then a pseudo-random bitstream.
// Runs unchanged on the RTL and on the gate-level netlist, so it uses no hierarchical references (the netlist is flat).
// Every output sample goes to decimator_top_out.txt, and make sim-gl requires the RTL and gate-level files to be identical.

`timescale 1ns / 1ps

module decimator_top_tb;

    // Override for power runs: -Pdecimator_top_tb.CLK_PERIOD=15258.789 (65.536 kHz) -Pdecimator_top_tb.N_VCD=16
    parameter real    CLK_PERIOD = 10.0;
    parameter integer N_VCD      = 0;     // output periods of PRBS input dumped to decimator_top.vcd, 0 = no VCD
    localparam DECIMATION = 256;
    localparam N_STEP     = 100;   // output samples of step response
    localparam N_PRBS     = 400;   // output samples of pseudo-random input

    reg  clk_fs;
    reg  rst_b;
    reg  data_in;
    wire signed [21:0] data_out;
    wire valid_strobe;

    reg  [22:0] lfsr;              // PRBS23, x^23 + x^18 + 1
    integer f_out;
    integer n_out;

    decimator_top uut (
        .clk_fs      (clk_fs),
        .rst_b       (rst_b),
        .data_in     (data_in),
        .data_out    (data_out),
        .valid_strobe(valid_strobe)
    );

    initial begin
        clk_fs = 0;
        forever #(CLK_PERIOD/2) clk_fs = ~clk_fs;
    end

    initial begin
        f_out = $fopen("decimator_top_out.txt", "w");
        if (f_out == 0) begin
            $display("Error: could not open output file.");
            $finish;
        end
        n_out   = 0;
        lfsr    = 23'h1;
        rst_b   = 1'b0;
        data_in = 1'b0;
        // Synchronous reset needs clock edges, so hold it over several.
        repeat (10) @(posedge clk_fs);
        #1 rst_b = 1'b1;

        // Step from -1 to +1, a fixed number of cycles after reset (the RTL testbench aligns via a hierarchical path instead).
        repeat (64) @(posedge clk_fs);
        #1 data_in = 1'b1;

        wait (n_out == N_STEP);

        // Activity window for power analysis: a whole number of output periods of settled PRBS input.
        // Level 1 dumps the nets of the DUT scope only, which in the flat netlist are all nets and no cell internals.
        if (N_VCD > 0) begin
            $dumpfile("decimator_top.vcd");
            $dumpvars(1, uut);
        end

        // Pseudo-random bitstream, changed 1 ns after each rising edge like the step.
        // A power run ends with its VCD window, so the VCD spans exactly N_VCD output periods.
        while (n_out < N_STEP + ((N_VCD > 0) ? N_VCD : N_PRBS)) begin
            @(posedge clk_fs);
            lfsr <= {lfsr[21:0], lfsr[22] ^ lfsr[17]};
            #1 data_in = lfsr[0];
        end

        $display("Simulation complete: %0d output samples.", n_out);
        $fclose(f_out);
        $finish;
    end

    // Sample the outputs away from the edge. An x anywhere fails the run, so a broken cell model cannot pass by comparing x to x.
    always @(negedge clk_fs) begin
        if (rst_b && valid_strobe === 1'b1) begin
            if (^data_out === 1'bx) begin
                $display("Error: data_out is x at output sample %0d, t = %t", n_out, $time);
                $fclose(f_out);
                $fatal(1);
            end
            $fwrite(f_out, "%d\n", data_out);
            n_out = n_out + 1;
        end else if (rst_b && valid_strobe !== 1'b0) begin
            $display("Error: valid_strobe is %b at t = %t", valid_strobe, $time);
            $fatal(1);
        end
    end

endmodule
