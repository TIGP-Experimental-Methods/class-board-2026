// Tca9535 - 16-bit I2C port expander, U505 on the B5 sheet, address 0x20
// (A0 = A1 = A2 = GND). NMR-FIRMWARE.md section 2.2.
//
// Register map (TCA9535 datasheet, table "Register Addresses"):
//   0x00 / 0x01  input port 0 / 1      (read back the pin, even on an output)
//   0x02 / 0x03  output port 0 / 1     (the value driven when the pin is an output)
//   0x04 / 0x05  polarity inversion    (left at 0: we never invert in hardware)
//   0x06 / 0x07  configuration         (1 = input, 0 = output; reset value 0xFF)
//
// What the sixteen lines do on this board (pins.h):
//   P0.0..P0.7  DIO1..DIO8 into the 74AHCT541 buffer (b5)
//   P1.0..P1.3  RLY_IN1..4, the relay gates, active high (b4)
//   P1.4        /CLR of the 74HC74 Johnson counter that makes the quadrature LO
//   P1.5..P1.7  spare, on test points TP502..TP504
//
// Order matters in begin(). The part resets with every port configured as an
// input, so the pins float at whatever the board's pull resistors say. If we
// configured the ports first and wrote the output registers second, the reset
// value of the output registers (0xFF) would drive all four relays on and pull
// /CLR low for the length of one I2C write. So: write the outputs, then the
// configuration.
//
// On a bare dev board there is no expander and nothing acknowledges at 0x20.
// begin() then returns false, present() stays false and every write is a quiet
// no-op that still updates the cached value, so the app and the status panel
// behave exactly as they will on real hardware.
#pragma once
#include <stdint.h>

class Tca9535 {
 public:
  bool begin(uint8_t addr = 0x20);

  bool writePort(uint8_t port, uint8_t value);              // port 0 or 1
  bool writeBit(uint8_t port, uint8_t bit, bool level);     // read-modify-write on the cache
  uint8_t cached(uint8_t port) const;

  // Bits set in `mask` become inputs on that port. Used only if a bring-up bodge
  // brings the OPA564 flags to the spare P1 lines (see EXP_BIT_IFLAG in pins.h).
  bool setInputs(uint8_t port, uint8_t mask);
  bool readPort(uint8_t port, uint8_t& value);

  bool present() const { return present_; }

  // Pulse /CLR (P1.4) low then high so the Johnson counter restarts in state 00.
  // Call it after every PLLB change, or the I and Q phases land wherever the
  // counter happened to be. The 74HC74 only needs a few tens of nanoseconds; one
  // I2C write at 400 kHz is several microseconds, so there is margin to spare.
  bool pulseJohnsonClear();

 private:
  static constexpr uint8_t kRegInput  = 0x00;
  static constexpr uint8_t kRegOutput = 0x02;
  static constexpr uint8_t kRegConfig = 0x06;

  bool write8(uint8_t reg, uint8_t value);
  bool read8(uint8_t reg, uint8_t& value);

  uint8_t addr_ = 0x20;
  bool present_ = false;
  uint8_t out_[2] = {0x00, 0x10};   // all DIO low; relays off; /CLR released (P1.4 = 1)
  uint8_t cfg_[2] = {0x00, 0x00};   // every line an output
};

extern Tca9535 expander;   // the one instance; BaseBlock::begin() starts it
