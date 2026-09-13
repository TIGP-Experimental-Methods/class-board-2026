// GPIO map of the class board, v0.7 (NMR-FIRMWARE.md section 1).
// Jinhua ESP32-S3 N16R8 dev board, DevKitC-1 pin order.
//
// What changed from v0.6: the eight DIO lines and the four relay gates are no
// longer MCU pins. They come from the TCA9535 I2C port expander U505 on B5, which
// freed twelve GPIO for the NMR console (DDS, TX gate, receiver blanking, the
// field-cycling H-bridge and the polarizer switch) and put GPIO4/6/7/15 on the
// expansion header. PIN_DIO[] and PIN_RELAY[] are gone on purpose: code that
// still references them must move to the expander (see drivers/Tca9535.h).
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

// ---- B3 Signal generation (DAC8563) --------------------------------------
constexpr int PIN_CS_DAC = 5;      // DAC8563 /SYNC, through the 74HCT125 level shifter

// ---- B4 Isolated switching -----------------------------------------------
// The four relay gates moved to the expander: see EXP_BIT_RLY1 below.
constexpr int PIN_OPTO_IN[2] = {16, 17};       // 6N137 outputs (3V3 side, active low)

// ---- B5 Digital I/O & timing ---------------------------------------------
// DIO1..8 moved to the expander: see EXP_PORT_DIO below.
constexpr int PIN_FAST_OUT[2] = {18, 21};      // MCPWM/RMT -> 74HCT125 -> terminals
constexpr int PIN_TRIG_IO  = 38;   // 74LVC1T45 A side
constexpr int PIN_TRIG_DIR = 39;   // 74LVC1T45 DIR: 1 = A->B = output to the TRIG SMA

// ---- NMR console, section B: transmitter ---------------------------------
constexpr int PIN_DDS_FSYNC = 41;  // AD9834 FSYNC = its SPI chip select, active low
constexpr int PIN_DDS_PSEL  = 42;  // AD9834 PSELECT pin: 0 = PHASE0, 1 = PHASE1
constexpr int PIN_TX_EN     = 40;  // OPA564 enable = transmit gate (10 k pull-down; 1 = transmit)

// ---- NMR console, section A: receiver ------------------------------------
// DG419 blanking switch. The 10 k pull-down means a reset board comes up blanked,
// which is what protects the LNA if the firmware never runs.
constexpr int PIN_RX_BLANK = 8;    // 0 = blanked (default), 1 = receive

// ---- NMR console, section C: field cycling and polarizer -----------------
constexpr int PIN_HB_IN1   = 9;    // DRV8871 IN1 (10 k pull-down; 0/0 = coast)
constexpr int PIN_HB_IN2   = 14;   // DRV8871 IN2
constexpr int PIN_FET_GATE = 47;   // UCC27517 -> AOD4184A polarizer switch (1 = coil on)

// ---- Base: expansion header and USB (informational) ----------------------
constexpr int PIN_EXP[4] = {4, 6, 7, 15};   // free, on the 2x10 expansion header
constexpr int PIN_USB_DN = 19;
constexpr int PIN_USB_DP = 20;
// GPIO43/44 reach the header and the LED_WIFI / LED_ACT jumpers JP1 / JP2.
// The firmware does not drive them; the names stay so the map is complete.
constexpr int PIN_UART0_TX = 43;
constexpr int PIN_UART0_RX = 44;

// ---- TCA9535 port map (U505, NMR-FIRMWARE.md section 1) ------------------
// Port 0 = DIO1..8 into the 74AHCT541. Port 1 = relay gates, the Johnson-counter
// clear, and three spare lines brought out on test points TP502..TP504.
// All sixteen lines are outputs. The expander powers up with every port as an
// input, so begin() writes the output registers before the configuration
// registers - otherwise a relay could glitch on for the length of one I2C write.
constexpr uint8_t EXP_PORT_DIO  = 0;   // P0.0..P0.7 = DIO1..DIO8
constexpr uint8_t EXP_PORT_CTRL = 1;   // P1.x, below
constexpr uint8_t EXP_BIT_RLY1  = 0;   // P1.0..P1.3 = RLY_IN1..4, active high
constexpr uint8_t EXP_BIT_JCLR  = 4;   // P1.4 = /CLR of the 74HC74 Johnson counter, 10 k pull-up
constexpr uint8_t EXP_BIT_SPARE5 = 5;  // P1.5..P1.7 = EXP_P15..P17, test points only
constexpr uint8_t EXP_BIT_SPARE6 = 6;
constexpr uint8_t EXP_BIT_SPARE7 = 7;

// Power-on value of port 1: every relay off, /CLR released (high).
constexpr uint8_t EXP_CTRL_IDLE = 1 << EXP_BIT_JCLR;

// The OPA564 current-limit and thermal flags (nets TX_IFLAG / TX_TFLAG) are
// push-pull 3.3 V CMOS outputs. In the v0.7 schematic they end on global labels
// and two DNP pull-up footprints (R811 / R812) - they are NOT wired to the
// expander or to any MCU pin, so the firmware reports them as not connected.
// If a bring-up bodge links them to the spare expander lines, set these to the
// P1 bit numbers (5 and 6) and the drivers read them through the expander.
constexpr int EXP_BIT_IFLAG = -1;   // -1 = not connected
constexpr int EXP_BIT_TFLAG = -1;
