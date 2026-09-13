#include "Tca9535.h"

#include <Arduino.h>

#include "../../include/pins.h"

#ifndef SIM
#include <Wire.h>
#endif

Tca9535 expander;

#ifndef SIM
namespace {
// Wire.begin() is idempotent on the ESP32 core, so a driver may start the bus
// itself. That keeps a driver usable from a bench sketch that has no BaseBlock.
void ensureWire() {
  static bool started = false;
  if (started) return;
  started = true;
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 400000);
}
}  // namespace
#endif

bool Tca9535::write8(uint8_t reg, uint8_t value) {
#ifdef SIM
  (void)reg;
  (void)value;
  return true;      // the simulated expander always takes the write
#else
  if (!present_) return false;
  Wire.beginTransmission(addr_);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
#endif
}

bool Tca9535::read8(uint8_t reg, uint8_t& value) {
#ifdef SIM
  (void)reg;
  value = 0;        // nothing drives the simulated input pins
  return true;
#else
  if (!present_) return false;
  Wire.beginTransmission(addr_);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;   // repeated start
  if (Wire.requestFrom(addr_, static_cast<uint8_t>(1)) != 1) return false;
  value = static_cast<uint8_t>(Wire.read());
  return true;
#endif
}

bool Tca9535::begin(uint8_t addr) {
  addr_ = addr;
  out_[EXP_PORT_DIO] = 0x00;
  out_[EXP_PORT_CTRL] = EXP_CTRL_IDLE;
  cfg_[EXP_PORT_DIO] = 0x00;
  cfg_[EXP_PORT_CTRL] = 0x00;

#ifdef SIM
  // The SIM build is the whole board in software, expander included: it reports
  // itself present and keeps its port values, so the app behaves the same way on
  // a bare dev board as it will on the real thing. It is the real build, flashed
  // onto a bare dev board, that finds no acknowledge and degrades quietly.
  present_ = true;
  return true;
#else
  ensureWire();
  Wire.beginTransmission(addr_);
  present_ = (Wire.endTransmission() == 0);
  if (!present_) return false;

  // Outputs first (see the header comment), then the direction registers.
  bool ok = write8(kRegOutput + 0, out_[0]);
  ok = write8(kRegOutput + 1, out_[1]) && ok;
  ok = write8(kRegConfig + 0, cfg_[0]) && ok;
  ok = write8(kRegConfig + 1, cfg_[1]) && ok;
  return ok;
#endif
}

bool Tca9535::writePort(uint8_t port, uint8_t value) {
  if (port > 1) return false;
  out_[port] = value;
  return write8(static_cast<uint8_t>(kRegOutput + port), value);
}

bool Tca9535::writeBit(uint8_t port, uint8_t bit, bool level) {
  if (port > 1 || bit > 7) return false;
  uint8_t v = out_[port];
  if (level) {
    v = static_cast<uint8_t>(v | (1u << bit));
  } else {
    v = static_cast<uint8_t>(v & ~(1u << bit));
  }
  return writePort(port, v);
}

uint8_t Tca9535::cached(uint8_t port) const {
  return port > 1 ? 0 : out_[port];
}

bool Tca9535::setInputs(uint8_t port, uint8_t mask) {
  if (port > 1) return false;
  cfg_[port] = mask;
  return write8(static_cast<uint8_t>(kRegConfig + port), mask);
}

bool Tca9535::readPort(uint8_t port, uint8_t& value) {
  if (port > 1) return false;
  return read8(static_cast<uint8_t>(kRegInput + port), value);
}

bool Tca9535::pulseJohnsonClear() {
  if (!present_) return false;
  bool ok = writeBit(EXP_PORT_CTRL, EXP_BIT_JCLR, false);
  ok = writeBit(EXP_PORT_CTRL, EXP_BIT_JCLR, true) && ok;
  return ok;
}
