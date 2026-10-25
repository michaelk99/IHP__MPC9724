-- SPDX-FileCopyrightText: 2026 Michael Koefinger
-- SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
-- dsa1_dig_top: the digital top with the v5 decimator.
--
-- Identical to dsa1_dig_top except for the decimator behind it. v5 outputs at
-- 512 Hz where v4 output at 256, so adc_conv fires twice as often and the SPI
-- read budget per conversion halves; nothing else here depends on the rate. The
-- flag synchroniser and the register file are unchanged.
--
-- Why v5: v4 does not protect its own signal band, its worst in-band alias is
-- -6.3 dB, and its leakage is dominated by thin-oxide decap fill. See
-- circuit-level/hdl/DSADC1/DEC/decimator_v5/plan.txt.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.dsa1_regs.all;
use work.all;

entity dsa1_dig_top is
    port (
        clk : in  std_ulogic;
        rst_b  : in  std_ulogic;

        sclk : in  std_ulogic;
        mosi : in  std_ulogic;
        miso : out std_ulogic;
        ss   : in  std_ulogic;

        data_in : in std_ulogic;

        adc_conv : out std_ulogic;

        o_bias_cfg			: out std_ulogic_vector(34 downto 0);
        o_rst_ctrl_b		: out std_ulogic_vector(1 downto 0);
        o_en_ctrl			: out std_ulogic_vector(10 downto 0);
        o_lf_cfg			: out std_ulogic_vector(15 downto 0);
        o_clk_cfg			: out std_ulogic_vector(18 downto 0);
        o_tst_ctrl			: out std_ulogic_vector(15 downto 0);
        o_uwb_tx_cfg		: out std_ulogic_vector(29 downto 0);
        o_aux_ctrl			: out std_ulogic_vector(15 downto 0)
    );
end entity dsa1_dig_top;

architecture rtl of dsa1_dig_top is

    -- decimator_v5, 512 Hz output.
    component decimator_top is
        port (
            clk_fs       : in  std_ulogic;
            rst_b        : in  std_ulogic;
            data_in      : in  std_ulogic;
            data_out     : out std_ulogic_vector(21 downto 0);
            valid_strobe : out std_ulogic
        );
    end component;

    signal dec_data_out     : std_ulogic_vector(21 downto 0);
    signal valid_strobe     : std_ulogic;

    -- internal copy of test-control output, so we can tap config bits
    signal tst_ctrl_i          : std_ulogic_vector(15 downto 0);

    -- Decimator enable (BLOCK_CTRL_1 bit0, reset '1' = enabled). The bit is set
    -- in the slave/sclk domain; synchronize it into the decimator clock (clk)
    -- domain before it gates the (synchronous) decimator reset, otherwise the
    -- wide pipeline could sample the transition unevenly -> partial reset.
    signal dec_en              : std_ulogic;            -- raw, sclk domain
    signal dec_en_s1, dec_en_s2, dec_en_s3 : std_ulogic; -- 3-FF sync to clk
    signal dec_rst_b           : std_ulogic;           -- gated decimator reset

    -- CDC: decimator (clk) -> SPI register file (sclk). Only the 1-bit ready
    -- flag (valid_strobe) is synchronized; the 22-bit data is NOT synchronized
    -- (that would just cost area + leakage). The decimator holds dec_data_out
    -- stable across a full decimation window, so it is stable when the
    -- synchronized flag captures it into the slave register file -> the classic
    -- "synchronize the control, let the held data flow through" pattern. The
    -- slave stores the ADC words; coherent two-word read-out is handled there.
    -- TEST_CTRL_0(TEST_CTRL_ADC_CDC_SYNC_EN_BIT) (reset '1'):
    --   '1' = ready flag passed through a 3-FF synchronizer
    --   '0' = direct valid_strobe pass-through (bypassed, test only)
    signal cdc_sync_en         : std_ulogic;

    -- 3-FF flag synchronizer (sclk domain)
    signal flag_s1, flag_s2, flag_s3 : std_ulogic;

    -- read flag + data windows presented to the slave (names match slave ports)
    -- Decimator stimulus test mode (TEST_CTRL_0 bits 15 downto 11). Lets the
    -- step, impulse, gain-linearity and noise responses be measured on silicon
    -- without a precise external bitstream. See the note at the generator below.
    signal stim_en             : std_ulogic;            -- raw, sclk domain
    signal stim_trig           : std_ulogic;            -- raw, sclk domain
    signal stim_en_s1, stim_en_s2, stim_en_s3 : std_ulogic;  -- 3-FF sync to clk
    signal stim_tr_s1, stim_tr_s2, stim_tr_s3 : std_ulogic;  -- 3-FF sync to clk
    signal stim_tr_d           : std_ulogic;            -- for the trigger edge
    signal stim_pat_s1, stim_pat_s2 : std_ulogic_vector(1 downto 0);  -- static config
    signal stim_opt_s1, stim_opt_s2 : std_ulogic;
    signal stim_tog            : std_ulogic;            -- free-running fs/2 idle
    signal stim_armed          : std_ulogic;            -- trigger seen, waiting for the boundary
    signal stim_fired          : std_ulogic;            -- the pattern is running
    signal stim_run            : std_ulogic;            -- step held after start
    signal stim_one            : std_ulogic;            -- impulse, one sample
    signal stim_rep_cnt        : unsigned(5 downto 0);  -- output samples since the fire
    signal stim_pat_cnt        : unsigned(1 downto 0);  -- the period-4 half-scale pattern
    signal stim_lfsr           : std_ulogic_vector(22 downto 0);  -- PRBS23
    signal stim_half           : std_ulogic;            -- the period-4 half-scale bit
    signal stim                : std_ulogic;            -- the generated bit
    signal dec_data_in         : std_ulogic;            -- what reaches the decimator

    signal adc_read_flag_s     : std_ulogic;
    signal adc_data_ch0_high_s : std_ulogic_vector(15 downto 0);
    signal adc_data_ch0_low_s  : std_ulogic_vector(15 downto 0);
begin
    u_decimator_top : decimator_top
        port map (
            clk_fs       => clk,
            rst_b        => dec_rst_b,
            data_in      => dec_data_in,
            data_out     => dec_data_out,
            valid_strobe => valid_strobe
        );

    u_spi_regs : entity work.dsa1_ic_bus_slave
        generic map (
            RESET_ACTIVE => '0',
            ADDR_MSB => DSA1_ADDR_MSB,
            DATA_MSB => DSA1_DATA_MSB
        )
        port map (
            rst_b               => rst_b,
            sclk                => sclk,
            mosi                => mosi,
            miso                => miso,
            ss                  => ss,

            adc_data_ch0_high   => adc_data_ch0_high_s,
            adc_data_ch0_low    => adc_data_ch0_low_s,
            adc_read_flag       => adc_read_flag_s,

            o_bias_cfg          => o_bias_cfg,
            o_rst_ctrl_b        => o_rst_ctrl_b,
            o_en_ctrl           => o_en_ctrl,
            o_dec_en            => dec_en,
            o_lf_cfg            => o_lf_cfg,
            o_clk_cfg           => o_clk_cfg,
            o_tst_ctrl          => tst_ctrl_i,
            o_uwb_tx_cfg        => o_uwb_tx_cfg,
            o_aux_ctrl          => o_aux_ctrl
        );

    o_tst_ctrl  <= tst_ctrl_i;
    cdc_sync_en <= tst_ctrl_i(TEST_CTRL_ADC_CDC_SYNC_EN_BIT);
    stim_en     <= tst_ctrl_i(TEST_CTRL_STIM_EN_BIT);
    stim_trig   <= tst_ctrl_i(TEST_CTRL_STIM_TRIG_BIT);

    -- ----------------------------------------------------------------
    -- Decimator stimulus generator, TEST_CTRL_0 bits 15 downto 11.
    --
    -- The idle pattern is an alternating bitstream, a tone at clk/2, which the
    -- decimator rejects completely, so the output sits at zero with no DC
    -- pedestal to subtract. Every pattern shows the idle until it fires, which
    -- is what makes the baseline well defined on a one-bit input: a +-1 stream
    -- cannot be zero, but an alternation decimates to zero.
    --
    --   PAT  pattern     OPT = 0                  OPT = 1
    --   00   step +      hold '1', once           repeat, 32 idle / 32 held
    --   01   impulse     one broken sample        repeat every 64 output samples
    --   10   steady      half scale, + + + -      PRBS23
    --   11   step -      hold '0', once           repeat, as step +
    --
    -- What each one is for: the two steps give settling, group delay, the
    -- compensator overshoot and the dc gain at both rails, and the negative
    -- rail is a separate path because the core saturates at DATA_MIN. The
    -- impulse gives 2*h[n] on a zero background. Half scale has mean +1/2 and
    -- both its fundamental at clk/4 and its harmonic at clk/2 land on CIC
    -- nulls, so only the dc reaches the output and the two rails plus this
    -- make a three-point gain-linearity check. PRBS23 is a white one-bit
    -- input, so the output variance measures the filter's noise bandwidth.
    --
    -- A settled step is a constant in the ideal, so its ripple is the sinc
    -- chain's per-section truncation noise, measured for free.
    --
    -- Enable and trigger are separate, and that is not optional. The decimator
    -- holds about 32 output samples of history, so firing on the enable edge
    -- buries the event under whatever the filter was full of. Measured that
    -- way first and the impulse was invisible under the decay of the preceding
    -- step. The sequence is: set bit 11, wait for the output to settle to zero
    -- on the idle pattern, then set bit 12.
    --
    -- The trigger only ARMS. The pattern starts at the next valid_strobe, so
    -- every shot begins on the same phase of the 128-cycle decimation window.
    -- Without that the SPI-written trigger lands anywhere in the window and the
    -- impulse response shifts run to run, which is the same trap the VHDL bench
    -- hit and fixed by waiting for adc_conv.
    --
    -- There is no capture logic: the words are read over SPI as always. To
    -- re-arm, write bit 12 low and high again.
    --
    -- The register file is clocked by sclk, so the bits cross into clk with the
    -- same 3-FF treatment dec_en gets. Pattern and option are static
    -- configuration, 2-FF, and are only consumed at the fire.
    -- ----------------------------------------------------------------
    p_stim : process (clk, rst_b)
    begin
        if rst_b = '0' then
            stim_en_s1   <= '0';
            stim_en_s2   <= '0';
            stim_en_s3   <= '0';
            stim_tr_s1   <= '0';
            stim_tr_s2   <= '0';
            stim_tr_s3   <= '0';
            stim_tr_d    <= '0';
            stim_pat_s1  <= (others => '0');
            stim_pat_s2  <= (others => '0');
            stim_opt_s1  <= '0';
            stim_opt_s2  <= '0';
            stim_tog     <= '0';
            stim_armed   <= '0';
            stim_fired   <= '0';
            stim_run     <= '0';
            stim_one     <= '0';
            stim_rep_cnt <= (others => '0');
            stim_pat_cnt <= (others => '0');
            stim_lfsr    <= (0 => '1', others => '0');
        elsif rising_edge(clk) then
            stim_en_s1  <= stim_en;
            stim_en_s2  <= stim_en_s1;
            stim_en_s3  <= stim_en_s2;
            stim_tr_s1  <= stim_trig;
            stim_tr_s2  <= stim_tr_s1;
            stim_tr_s3  <= stim_tr_s2;
            stim_tr_d   <= stim_tr_s3;
            stim_pat_s1 <= tst_ctrl_i(TEST_CTRL_STIM_PAT_HI downto TEST_CTRL_STIM_PAT_LO);
            stim_pat_s2 <= stim_pat_s1;
            stim_opt_s1 <= tst_ctrl_i(TEST_CTRL_STIM_OPT_BIT);
            stim_opt_s2 <= stim_opt_s1;

            stim_tog <= not stim_tog;
            stim_one <= '0';                    -- the impulse lasts one sample

            -- The period-4 half-scale pattern runs only once fired, so the
            -- phase of + + + - is the same on every shot.
            if stim_fired = '1' then
                stim_pat_cnt <= stim_pat_cnt + 1;
            else
                stim_pat_cnt <= (others => '0');
            end if;

            -- PRBS23, x^23 + x^18 + 1, the same generator and seed as
            -- decimator_top_tb.v, so models/ can predict the sequence.
            if stim_fired = '1' and stim_pat_s2 = STIM_PAT_STEADY and stim_opt_s2 = '1' then
                stim_lfsr <= stim_lfsr(21 downto 0) & (stim_lfsr(22) xor stim_lfsr(17));
            end if;

            if stim_en_s3 = '0' or stim_tr_s3 = '0' then
                stim_armed   <= '0';
                stim_fired   <= '0';
                stim_run     <= '0';
                stim_rep_cnt <= (others => '0');
                stim_lfsr    <= (0 => '1', others => '0');
            else
                if stim_tr_d = '0' then         -- the trigger edge only arms
                    stim_armed <= '1';
                end if;

                if valid_strobe = '1' then      -- the decimation boundary
                    if stim_armed = '1' then
                        stim_armed   <= '0';
                        stim_fired   <= '1';
                        stim_rep_cnt <= (others => '0');
                        case stim_pat_s2 is
                            when STIM_PAT_IMPULSE =>
                                stim_one <= '1';
                            when STIM_PAT_STEP_P | STIM_PAT_STEP_N =>
                                stim_run <= '1';
                            when others =>
                                null;           -- the steady patterns need no event
                        end case;
                    elsif stim_fired = '1' and stim_opt_s2 = '1' then
                        stim_rep_cnt <= stim_rep_cnt + 1;
                        case stim_pat_s2 is
                            when STIM_PAT_IMPULSE =>
                                if stim_rep_cnt = 63 then
                                    stim_one     <= '1';
                                    stim_rep_cnt <= (others => '0');
                                end if;
                            when STIM_PAT_STEP_P | STIM_PAT_STEP_N =>
                                if stim_rep_cnt = 31 then
                                    stim_run <= not stim_run;
                                elsif stim_rep_cnt = 63 then
                                    stim_run     <= not stim_run;
                                    stim_rep_cnt <= (others => '0');
                                end if;
                            when others =>
                                null;
                        end case;
                    end if;
                end if;
            end if;
        end if;
    end process;

    -- + + + - repeating, mean +1/2
    stim_half <= '0' when stim_pat_cnt = "11" else '1';

    -- Before the fire, and between the events of a repeating pattern, the
    -- stream is the idle alternation.
    stim <= not stim_tog when stim_one = '1' else
            stim_tog     when stim_fired = '0' else
            '1'          when stim_pat_s2 = STIM_PAT_STEP_P and stim_run = '1' else
            '0'          when stim_pat_s2 = STIM_PAT_STEP_N and stim_run = '1' else
            stim_half    when stim_pat_s2 = STIM_PAT_STEADY and stim_opt_s2 = '0' else
            stim_lfsr(0) when stim_pat_s2 = STIM_PAT_STEADY and stim_opt_s2 = '1' else
            stim_tog;

    dec_data_in <= stim when stim_en_s3 = '1' else data_in;

    -- ----------------------------------------------------------------
    -- Decimator enable -> reset gate. 3-FF synchronizer
    -- brings the sclk-domain config bit into the clk
    -- (clk_fs) domain; the result gates the decimator's synchronous reset.
    -- Disable-only: holding dec_rst_b low clears the pipeline and stops
    -- valid_strobe (no clock gating, so this is not a power-down).
    -- ----------------------------------------------------------------
    p_dec_en_sync : process (clk, rst_b)
    begin
        if rst_b = '0' then
            dec_en_s1 <= '0';
            dec_en_s2 <= '0';
            dec_en_s3 <= '0';
        elsif rising_edge(clk) then
            dec_en_s1 <= dec_en;
            dec_en_s2 <= dec_en_s1;
            dec_en_s3 <= dec_en_s2;
        end if;
    end process;

    dec_rst_b <= rst_b and dec_en_s3;

    -- ----------------------------------------------------------------
    -- 3-FF synchronizer (sclk domain) for the ready flag only. The decimator
    -- holds dec_data_out stable across the window, so it is stable when the
    -- synchronized flag captures it in the slave -> no data-bus synchronizer
    -- needed.
    -- ----------------------------------------------------------------
    p_flag_sync : process (sclk, rst_b)
    begin
        if rst_b = '0' then
            flag_s1 <= '0';
            flag_s2 <= '0';
            flag_s3 <= '0';
        elsif rising_edge(sclk) then
            flag_s1 <= valid_strobe;
            flag_s2 <= flag_s1;
            flag_s3 <= flag_s2;
        end if;
    end process;

    -- Bypass mux: synchronized flag when enabled, direct valid_strobe otherwise
    adc_read_flag_s <= flag_s3 when cdc_sync_en = '1' else valid_strobe;

    -- Data fed directly from the decimator (NOT synchronized; held stable).
    -- Register-map word ordering (sample = read(HIGH_ADDR)(5:0) & read(LOW_ADDR)):
    --   ADC_DATA_CH0_HIGH_ADDR holds the top 6 bits (zero-extended)
    --   ADC_DATA_CH0_LOW_ADDR  holds the low 16 bits
    adc_data_ch0_high_s <= "0000000000" & dec_data_out(21 downto 16);
    adc_data_ch0_low_s  <= dec_data_out(15 downto 0);

    adc_conv <= valid_strobe;
end architecture rtl;
