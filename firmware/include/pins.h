// GPIO map of the class board, v0.7 (NMR-FIRMWARE.md section 1).
// Jinhua ESP32-S3 N16R8 dev board, DevKitC-1 pin order.
//
// The eight DIO lines and the seven module outputs are not MCU pins: they come
// from the TCA9535 I2C port expander U505 on B5 (drivers/Tca9535.h), which frees
// GPIO for the NMR console (DDS, TX gate, receiver blanking, the field-cycling
// H-bridge and the polarizer switch). GPIO4/6/7/15 are not connected.
//
// Never use: GPIO 0, 45, 46 (strapping), 3 (unused input, no pull), 35-37 (octal PSRAM).
#pragma once
#include <stdint.h>

// ---- Base: buses ----------------------------------------------------------
constexpr int PIN_SPI_SCLK = 12;   // SPI2 on IO_MUX pins (80 MHz capable)
constexpr int PIN_SPI_MOSI = 11;
constexpr int PIN_SPI_MISO = 13;
constexpr int PIN_I2C_SDA  = 1;    // 400 kHz, 4.7 k pull-ups on the base
constexpr int PIN_I2C_SCL  = 2;
constexpr int PIN_RGB_LED  = 48;   // WS2812 on the dev board itself

// I2C addresses on that one bus.
constexpr uint8_t I2C_ADDR_OLED     = 0x3C;   // SSD1306
constexpr uint8_t I2C_ADDR_EXPANDER = 0x20;   // TCA9535, A0 = A1 = A2 = GND
constexpr uint8_t I2C_ADDR_SI5351   = 0x60;   // Si5351A-B-GT clock generator

// ---- B1 Precision inputs (ADS8688) ---------------------------------------
constexpr int PIN_CS_ADC = 10;     // ADS8688 /CS

// Front-panel input AI n is wired to ADS8688 channel kAinOfAi[n-1] (AIN_0..AIN_7).
// Every place that turns a panel input into an ADC channel goes through this table.
// AI7 and AI8 carry the NMR receiver I and Q when the shunts on J14 / J15 are on
// 2-3 (the headers are always fitted; 1-2 = the panel SMA).
constexpr uint8_t kAinOfAi[8] = {1, 0, 7, 6, 5, 4, 3, 2};

// ---- B3 Signal generation (DAC8563) --------------------------------------
constexpr int PIN_CS_DAC = 5;      // DAC8563 /SYNC, through the 74HCT125 level shifter

// ---- B4 Isolated inputs --------------------------------------------------
// 6N137 outputs on the front panel, active low. Their 1 k pull-ups are on the
// panel, so the firmware adds INPUT_PULLUP to keep them defined without it.
constexpr int PIN_OPTO_IN[2] = {16, 17};       // OPTO_IN1, OPTO_IN2

// ---- B5 Digital I/O & timing ---------------------------------------------
// DIO1..8 are on the expander: see EXP_PORT_DIO below.
// FAST_OUT1, FAST_OUT2: LEDC/MCPWM/RMT -> 74HCT125 -> 49.9 ohm -> panel SMA jacks
// FAST1 / FAST2. No pull resistor: undefined until the firmware sets them.
constexpr int PIN_FAST_OUT[2] = {21, 18};
constexpr int PIN_TRIG_IO  = 38;   // 74LVC1T45 A side
constexpr int PIN_TRIG_DIR = 39;   // 74LVC1T45 DIR: 1 = A->B = output to the TRIG SMA; no pull resistor

// ---- NMR console, section B: transmitter ---------------------------------
constexpr int PIN_DDS_FSYNC = 41;  // AD9834 FSYNC = its SPI chip select, active low
constexpr int PIN_DDS_PSEL  = 42;  // AD9834 PSELECT pin; ignored (PIN/SW = 0), held low; no pull resistor
constexpr int PIN_TX_EN     = 40;  // OPA564 enable = transmit gate (10 k pull-down; 1 = transmit)

// ---- NMR console, section A: receiver ------------------------------------
// DG419 blanking switch. The 10 k pull-down means a reset board comes up blanked,
// which is what protects the LNA if the firmware never runs.
constexpr int PIN_RX_BLANK = 8;    // 0 = blanked (default), 1 = receive

// ---- NMR console, section C: field cycling and polarizer -----------------
constexpr int PIN_HB_IN1   = 9;    // DRV8871 IN1 (10 k pull-down; 0/0 = coast)
constexpr int PIN_HB_IN2   = 14;   // DRV8871 IN2
constexpr int PIN_FET_GATE = 47;   // UCC27517 -> AOD4184A polarizer switch (1 = coil on)

// ---- Base: USB and UART0 (informational) ---------------------------------
constexpr int PIN_USB_DN = 19;
constexpr int PIN_USB_DP = 20;
// GPIO43/44 drive the front-panel LED_WIFI / LED_ACT through R717 / R718.
// The firmware does not drive them; the names stay so the map is complete.
constexpr int PIN_UART0_TX = 43;
constexpr int PIN_UART0_RX = 44;

// ---- TCA9535 port map (U505, NMR-FIRMWARE.md section 1) ------------------
// Port 0 = DIO1..8 into the 74AHCT541. Port 1 = MOD1..MOD7, the module outputs
// to the front-panel module header, and P1.4 (net EXP_P14, test point TP501) =
// /CLR of the 74HC74 Johnson counter.
// All sixteen lines are outputs. The expander powers up with every port as an
// input, so begin() writes the output registers before the configuration
// registers - otherwise a module output could pulse on for one I2C write.
constexpr uint8_t EXP_PORT_DIO  = 0;   // P0.0..P0.7 = DIO1..DIO8
constexpr uint8_t EXP_PORT_CTRL = 1;   // P1.x, below
constexpr uint8_t EXP_BIT_JCLR  = 4;   // P1.4 = EXP_P14 = /CLR of the Johnson counter, R706 10 k pull-up
constexpr int kModuleOutputs = 7;
// Port-1 bit of module output MOD n = EXP_BIT_MOD[n-1]: P1.0..P1.3 = MOD1..MOD4,
// P1.5..P1.7 = MOD5..MOD7. Active high; 10 k pull-downs on the panel.
constexpr uint8_t EXP_BIT_MOD[kModuleOutputs] = {0, 1, 2, 3, 5, 6, 7};

// Power-on value of port 1: every module output off, /CLR released (high).
constexpr uint8_t EXP_CTRL_IDLE = 1 << EXP_BIT_JCLR;

// The OPA564 current-limit and thermal flags (nets TX_IFLAG / TX_TFLAG) are
// push-pull 3.3 V CMOS outputs. In the v0.7 schematic they end on global labels
// and two DNP pull-up footprints (R811 / R812) - they are NOT wired to the
// expander or to any MCU pin, so the firmware reports them as not connected.
// The expander has no spare line left for them; if a bring-up bodge links them
// to a port-1 line, set these to its bit number and the drivers read it there.

constexpr int EXP_BIT_IFLAG = -1;   // -1 = not connected
constexpr int EXP_BIT_TFLAG = -1;
