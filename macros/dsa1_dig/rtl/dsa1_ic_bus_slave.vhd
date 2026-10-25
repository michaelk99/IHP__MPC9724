-- SPDX-FileCopyrightText: 2026 Michael Koefinger
-- SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;

use work.dsa1_regs.all;
use work.all;

entity dsa1_ic_bus_slave is
    generic (
	RESET_ACTIVE 			: std_ulogic := '0';
    ADDR_MSB 				: natural := 4; 	-- BIT_SIZE = addr_msb + 1
	DATA_MSB 				: natural := 15 	-- BIT_SIZE = data_msb + 1
    );

    port (
	rst_b   			: in std_ulogic;     --Reset (low active)
	sclk   				: in std_ulogic;    --serial clock
	mosi				: in std_ulogic;    --master out slave in
	miso    			: out std_ulogic;   --master in slave out
	ss      			: in std_ulogic;    --slave select

	-- ADC data: the words are stored here (held in the SPI register file) on
	-- adc_read_flag. dsa1_dig_top only synchronizes the data + flag across the
	-- clk->sclk boundary; the holding registers live in the slave.
	adc_data_ch0_high	: in std_ulogic_vector(15 downto 0);
	adc_data_ch0_low	: in std_ulogic_vector(15 downto 0);
	adc_read_flag		: in std_ulogic;

	o_bias_cfg			: out std_ulogic_vector(34 downto 0);
	o_rst_ctrl_b		: out std_ulogic_vector(1 downto 0);
	o_en_ctrl			: out std_ulogic_vector(10 downto 0);
	o_dec_en			: out std_ulogic;   -- BLOCK_CTRL_1 bit0: decimator enable
	o_lf_cfg			: out std_ulogic_vector(15 downto 0);
	o_clk_cfg			: out std_ulogic_vector(18 downto 0);
	o_tst_ctrl			: out std_ulogic_vector(15 downto 0);
    o_uwb_tx_cfg		: out std_ulogic_vector(29 downto 0);
    o_aux_ctrl			: out std_ulogic_vector(15 downto 0)
    );
end dsa1_ic_bus_slave;

architecture rtl of dsa1_ic_bus_slave is

    signal addressReg : std_ulogic_vector(ADDR_MSB downto 0); -- shift register for received address
    signal address : natural range 0 to 2**REG_SIZE_BIT-1; -- received address mapped to data register

    signal txReg : std_ulogic_vector(DATA_MSB downto 0); -- shift register for transmitting data
    signal txRegDelay : std_ulogic_vector(DATA_MSB downto 0); -- additional register to delay the transmitting data process

    signal cnt : integer range 0 to DATA_MSB;
    signal fetchFlag : std_ulogic; -- flag to read data from dataReg
    signal storeFlag : std_ulogic; -- flag to store data to dataReg
    signal readBit : std_ulogic; -- 0 = write, 1 = read only

    type storage_register is array (0 to 2**REG_SIZE_BIT-1) of std_ulogic_vector(DATA_MSB downto 0);
    signal dataReg : storage_register; -- storage register for whole data

    type spi_states is (receive_addr, load_data, tranceive_data, store_data);
    signal state : spi_states; -- actual SPI state

    -- Coherent multi-word read-out (register-file feature, NOT CDC; cf. the
    -- "block data update" bit on many sensor SPI maps). Loaded on the HIGH-word
    -- read and retained until the next HIGH read, so the following LOW read
    -- returns the companion word from the same sample even if the ADC holding
    -- register updates between the two read transactions. See adc_low_freeze_reg.
    signal adc_data_ch0_low_freeze : std_ulogic_vector(DATA_MSB downto 0);
begin

    communication_rising_edge : process (sclk, rst_b, ss) is  -- write to miso
    begin
        if rst_b= RESET_ACTIVE or ss = '1' then
            miso <= '0';
        elsif sclk'event and sclk = '1' then
            if ss = '0' then
                case state is
                    when receive_addr =>
						miso <= addressReg(0);
                    when load_data =>
						miso <= addressReg(0);
                    when tranceive_data =>
                        miso <= txReg(DATA_MSB); -- put data from dataReg(adress) to miso
                    when store_data =>
                        miso <= '0';
                end case;
            end if;
        end if;
    end process;

    communication_falling_edge : process (sclk, rst_b, ss) is -- read from mosi
    begin
        if rst_b= RESET_ACTIVE or ss = '1' then
			addressReg <= (others=>'0');
			state <= receive_addr;
			txReg <= (others=>'0');
			fetchFlag <= '0';
			storeFlag <= '0';
			cnt <= 0;

        elsif sclk'event and sclk = '0' and ss = '0' then
            case state is
                when receive_addr =>
					addressReg(ADDR_MSB downto 1) <= addressReg(ADDR_MSB - 1 downto 0);
                    addressReg(0) <= mosi; --shift register for address: shift left out and right in
                    if cnt < ADDR_MSB then
                        cnt <= cnt+1;
                    else -- all address bits are received
                        cnt <= 0;
                        fetchFlag <= '1'; -- get delayed data from dataRegister(address)
                        state <= load_data;
                    end if;
                when load_data => -- get data from dataRegister
                    fetchFlag <= '0';
					txReg <= txRegDelay;
                    state <= tranceive_data;
                when tranceive_data =>
					txReg(DATA_MSB downto 1) <= txReg(DATA_MSB - 1 downto 0);
                    txReg(0) <= mosi; --shift register for transmitting data: shift left out and right in
                    if cnt < DATA_MSB then
                        cnt <= cnt+1;
                    else -- all transmitting data are transmitted
                        cnt <= 0;
                        storeFlag <= '1';
                        state <= store_data; -- store new data to dataRegister(address)
                    end if;
                when store_data =>
                    storeFlag <= '0';
                    state <= receive_addr;
            end case;
        end if;
    end process;

    storageProcess : process (sclk, rst_b) is
    begin
        if rst_b= RESET_ACTIVE then
			-- CTRL REG
			dataReg(BIAS_CFG_0_ADDR) 		<= BIAS_CFG_0_RESET_VALUE;
			dataReg(BIAS_CFG_1_ADDR) 		<= BIAS_CFG_1_RESET_VALUE;
			dataReg(BIAS_CFG_2_ADDR) 		<= BIAS_CFG_2_RESET_VALUE;
			dataReg(BLOCK_CTRL_0_ADDR) 		<= BLOCK_CTRL_0_RESET_VALUE;
			dataReg(BLOCK_CTRL_1_ADDR) 		<= BLOCK_CTRL_1_RESET_VALUE;
			dataReg(TRIM_CFG_0_ADDR) 		<= TRIM_CFG_0_RESET_VALUE;
			dataReg(CLK_CFG_0_ADDR)			<= CLK_CFG_0_RESET_VALUE;
			dataReg(TEST_CTRL_0_ADDR) 		<= TEST_CTRL_0_RESET_VALUE;
            dataReg(UWB_TX_CFG_0_ADDR) 		<= UWB_TX_CFG_0_RESET_VALUE;
            dataReg(UWB_TX_CFG_1_ADDR) 		<= UWB_TX_CFG_1_RESET_VALUE;
            dataReg(AUX_CTRL_0_ADDR) 		<= AUX_CTRL_0_RESET_VALUE;

			-- ADC + REMAINING REG
			dataReg(0 to ADC_REG_CNT-1)								<= (others => (others => '0'));
			dataReg((AUX_CTRL_0_ADDR+1) to (2**ADDR_MSB-1))		<= (others => (others => '0'));
        elsif sclk'event and sclk = '1' then
            -- Hold the ADC words in the register file (updated from the
            -- synchronized inputs on adc_read_flag).
            if adc_read_flag = '1' then
                dataReg(ADC_DATA_CH0_HIGH_ADDR) <= adc_data_ch0_high;
                dataReg(ADC_DATA_CH0_LOW_ADDR)  <= adc_data_ch0_low;
            end if;

            if fetchFlag = '1' then
                -- Block-data-update: the LOW read is served from the frozen
                -- companion (adc_data_ch0_low_freeze) for a coherent pair.
                case address is
                    when ADC_DATA_CH0_HIGH_ADDR =>
                        txRegDelay <= dataReg(ADC_DATA_CH0_HIGH_ADDR);
                    when ADC_DATA_CH0_LOW_ADDR  =>
                        txRegDelay <= adc_data_ch0_low_freeze;
                    when CHIP_ID_ADDR           =>
                        txRegDelay <= CHIP_ID_VALUE;    -- read only, a constant
                    when others                 =>
                        txRegDelay <= dataReg(address);
                end case;
            elsif storeFlag = '1' and readBit = '0' and address /= CHIP_ID_ADDR then
                dataReg(address) <= txReg; --only store new data to dataReg if readBit = '0'
            end if;
        end if;
    end process;

    -- Dedicated register: latch the companion LOW word at the HIGH-word read.
    adc_low_freeze_reg : process (sclk, rst_b) is
    begin
        if rst_b = RESET_ACTIVE then
            adc_data_ch0_low_freeze <= (others => '0');
        elsif sclk'event and sclk = '1' then
            if fetchFlag = '1' and address = ADC_DATA_CH0_HIGH_ADDR then
                adc_data_ch0_low_freeze <= dataReg(ADC_DATA_CH0_LOW_ADDR);
            end if;
        end if;
    end process;

    address <= to_integer(unsigned(addressReg(REG_SIZE_BIT-1 downto 0))); --map addresReg to address (1st Bit is R/!W)
    readBit <= addressReg(ADDR_MSB); --get readBit from addresss (1st Bit of address, 1 = read only, 0 = read and write)

	-- adc_data_valid <= adc_data_valid_s;

	 --Register to Output links:
	o_bias_cfg <= dataReg(BIAS_CFG_1_ADDR)(15 downto 0) & dataReg(BIAS_CFG_0_ADDR)(15 downto 0) & dataReg(BIAS_CFG_2_ADDR)(2 downto 0);
	o_rst_ctrl_b <= dataReg(BLOCK_CTRL_0_ADDR)(15 downto 14);
	o_en_ctrl <= dataReg(BLOCK_CTRL_0_ADDR)(10 downto 0);
	o_dec_en <= dataReg(BLOCK_CTRL_1_ADDR)(BLOCK_CTRL_1_DEC_EN_BIT);
	o_lf_cfg <= dataReg(TRIM_CFG_0_ADDR)(15 downto 0);
	o_clk_cfg <= dataReg(BLOCK_CTRL_0_ADDR)(13 downto 11) & dataReg(CLK_CFG_0_ADDR)(15 downto 0);
	o_tst_ctrl <= dataReg(TEST_CTRL_0_ADDR);
    o_uwb_tx_cfg <= dataReg(UWB_TX_CFG_1_ADDR)(14 downto 0) & dataReg(UWB_TX_CFG_0_ADDR)(14 downto 0);
    o_aux_ctrl <= dataReg(AUX_CTRL_0_ADDR);

end architecture rtl;