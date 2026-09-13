#include "Si5351.h"

#include <Arduino.h>
#include <math.h>

#include "../../include/pins.h"
#include "Tca9535.h"

#ifndef SIM
#include <Wire.h>
#endif

Si5351 clockgen;

namespace {

constexpr uint8_t kRegStatus     = 0;
constexpr uint8_t kRegOutputEn   = 3;
constexpr uint8_t kRegClkCtrl0   = 16;
constexpr uint8_t kRegPllA       = 26;
constexpr uint8_t kRegPllB       = 34;
constexpr uint8_t kRegMs0        = 42;
constexpr uint8_t kRegMs1        = 50;
constexpr uint8_t kRegPllReset   = 177;
constexpr uint8_t kRegXtalLoad   = 183;

// The VCO of each PLL is specified for 600..900 MHz. Staying near the top gives
// the finest output steps and the lowest phase noise, so the search below always
// prefers the highest PLL frequency it can reach.
constexpr double kVcoMin = 600.0e6;
constexpr double kVcoMax = 900.0e6;

// Fractional denominator. 2^20 - 1 is the largest the part accepts and gives a
// step of 25 MHz / 1048575 at the PLL, which is well under a millihertz once the
// output divider has had its say.
constexpr uint32_t kDenom = 1048575;

#ifndef SIM
void ensureWire() {
  static bool started = false;
  if (started) return;
  started = true;
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 400000);
}
#endif

}  // namespace

bool Si5351::write8(uint8_t reg, uint8_t value) {
#ifdef SIM
  (void)reg;
  (void)value;
  return true;      // the simulated part always takes the write
#else
  if (!present_) return false;
  Wire.beginTransmission(addr_);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
#endif
}

// AN619 section 3.2: the same three-parameter form is used for the PLL feedback
// dividers and for the output multisynths.
Si5351::Divider Si5351::encode(uint32_t a, uint32_t b, uint32_t c) {
  Divider d;
  if (c == 0) c = 1;
  const uint32_t q = static_cast<uint32_t>((128ULL * b) / c);
  d.p1 = 128u * a + q - 512u;
  d.p2 = static_cast<uint32_t>(128ULL * b - static_cast<uint64_t>(c) * q);
  d.p3 = c;
  d.integer = (b == 0);
  return d;
}

// Eight consecutive registers, laid out exactly as AN619 tables 10 to 13.
// rDivExp is only meaningful for an output multisynth (R = 2^rDivExp, 0..7); the
// PLL feedback registers have no R divider and reserved bits there, so pass 0.
bool Si5351::writeDivider(uint8_t baseReg, const Divider& d, uint8_t rDivExp) {
  uint8_t b[8];
  b[0] = static_cast<uint8_t>((d.p3 >> 8) & 0xFF);
  b[1] = static_cast<uint8_t>(d.p3 & 0xFF);
  b[2] = static_cast<uint8_t>(((rDivExp & 0x07) << 4) | ((d.p1 >> 16) & 0x03));
  b[3] = static_cast<uint8_t>((d.p1 >> 8) & 0xFF);
  b[4] = static_cast<uint8_t>(d.p1 & 0xFF);
  b[5] = static_cast<uint8_t>(((d.p3 >> 12) & 0xF0) | ((d.p2 >> 16) & 0x0F));
  b[6] = static_cast<uint8_t>((d.p2 >> 8) & 0xFF);
  b[7] = static_cast<uint8_t>(d.p2 & 0xFF);

  bool ok = true;
  for (uint8_t i = 0; i < 8; i++) ok = write8(static_cast<uint8_t>(baseReg + i), b[i]) && ok;
  return ok;
}

bool Si5351::begin(uint8_t addr, uint32_t xtal_hz) {
  addr_ = addr;
  xtal_ = xtal_hz ? xtal_hz : 25000000;
  oeb_ = 0xFF;
  clk0Actual_ = clk1Actual_ = 0;

#ifdef SIM
  // Same rule as the expander: simulated means present, so the NMR panel can be
  // driven end to end on a bare dev board. Only the real build can fail to find it.
  present_ = true;
  return true;
#else
  ensureWire();
  Wire.beginTransmission(addr_);
  present_ = (Wire.endTransmission() == 0);
  if (!present_) return false;

  // The part loads its NVM after power-up. Reading anything before SYS_INIT
  // clears gives a register map that is about to be overwritten.
  for (int i = 0; i < 100; i++) {
    Wire.beginTransmission(addr_);
    Wire.write(kRegStatus);
    if (Wire.endTransmission(false) != 0) break;
    if (Wire.requestFrom(addr_, static_cast<uint8_t>(1)) != 1) break;
    if ((Wire.read() & 0x80) == 0) break;
    delay(1);
  }

  bool ok = write8(kRegOutputEn, 0xFF);                 // everything off while we set up
  for (uint8_t c = 0; c < 3; c++) {
    ok = write8(static_cast<uint8_t>(kRegClkCtrl0 + c), 0x80) && ok;   // powered down
  }
  // Y701 is a 12 pF crystal and the board has no external load capacitors worth
  // counting, so the internal 10 pF setting is the right one. Bits 5:0 of this
  // register are undocumented but must be written back as 010010.
  ok = write8(kRegXtalLoad, 0xD2) && ok;
  return ok;
#endif
}

// CLK0 = the AD9834 master clock. Prefer an exact integer solution: PLL = xtal*m
// with m whole, and an even whole output divider. For 50 MHz from 25 MHz that is
// m = 36 (900 MHz) and divider 18, which is what the design asks for. If no
// integer solution exists (the `clock` test command can ask for anything), fall
// back to the same fractional search setClk1 uses, on PLLA.
bool Si5351::setClk0(uint32_t hz) {
  if (hz == 0) {
    clk0Actual_ = 0;
    return enable(0, false);
  }

  uint32_t bestDiv = 0, bestMul = 0;
  for (uint32_t d = 6; d <= 1800; d += 2) {
    const uint64_t pll = static_cast<uint64_t>(hz) * d;
    if (pll < static_cast<uint64_t>(kVcoMin)) continue;
    if (pll > static_cast<uint64_t>(kVcoMax)) break;
    if (pll % xtal_ != 0) continue;
    bestDiv = d;                      // keep going: the last hit is the highest PLL
    bestMul = static_cast<uint32_t>(pll / xtal_);
  }

  bool ok;
  if (bestDiv != 0) {
    ok = writeDivider(kRegPllA, encode(bestMul, 0, 1), 0);
    ok = writeDivider(kRegMs0, encode(bestDiv, 0, 1), 0) && ok;
    // MS0_INT = 1: integer output divider, PLLA source, 8 mA drive.
    ok = write8(kRegClkCtrl0, 0x4F) && ok;
    clk0Actual_ = static_cast<double>(xtal_) * bestMul / bestDiv;
  } else {
    uint8_t rExp = 0;
    double fms = hz;
    while (fms < 1.0e6 && rExp < 7) { rExp++; fms *= 2.0; }
    uint32_t d = static_cast<uint32_t>(kVcoMax / fms);
    if (d > 900) d = 900;
    d &= ~1u;
    if (d < 8) d = 8;
    const double pll = fms * d;
    const uint32_t a = static_cast<uint32_t>(pll / xtal_);
    const double frac = pll / xtal_ - a;
    uint32_t b = static_cast<uint32_t>(llround(frac * kDenom));
    if (b >= kDenom) b = kDenom - 1;
    ok = writeDivider(kRegPllA, encode(a, b, kDenom), 0);
    ok = writeDivider(kRegMs0, encode(d, 0, 1), rExp) && ok;
    ok = write8(kRegClkCtrl0, 0x4F) && ok;
    clk0Actual_ = static_cast<double>(xtal_) * (a + static_cast<double>(b) / kDenom) /
                  (static_cast<double>(d) * (1u << rExp));
  }

  ok = write8(kRegPllReset, 0x20) && ok;     // PLLA_RST
  ok = enable(0, true) && ok;
  return ok && present_;
}

// CLK1 = 4 x f_LO. The Johnson counter divides by four, so an audio-rate LO of
// 84 kHz asks for 336 kHz here - far below what a multisynth alone can reach from
// a 600 MHz VCO, which is what the R divider after it is for. Strategy:
//   1. double R until the multisynth output is above 1 MHz (a comfortable range),
//   2. pick the largest even whole multisynth divider that keeps the PLL at or
//      below 900 MHz (that also keeps it above 675 MHz, so always in spec),
//   3. put the whole of the remainder into the fractional PLL feedback divider.
// An integer, even output divider with a fractional PLL is the low-spur choice
// AN619 recommends, and it is the phase relationship at the counter that matters.
bool Si5351::setClk1(double hz) {
  if (!(hz > 0.0)) {
    clk1Actual_ = 0;
    return enable(1, false);
  }

  uint8_t rExp = 0;
  double fms = hz;
  while (fms < 1.0e6 && rExp < 7) { rExp++; fms *= 2.0; }

  uint32_t d = static_cast<uint32_t>(kVcoMax / fms);
  if (d > 900) d = 900;                 // fractional multisynths stop at 900
  d &= ~1u;                             // even: required for integer mode
  if (d < 8) d = 8;

  double pll = fms * d;
  if (pll < kVcoMin || pll > kVcoMax) {
    // Only reachable for an out-of-range request (below ~4.6 kHz or above
    // 112 MHz). Clamp rather than write nonsense into the part.
    clk1Actual_ = 0;
    return false;
  }

  const uint32_t a = static_cast<uint32_t>(pll / xtal_);
  const double frac = pll / xtal_ - a;
  uint32_t b = static_cast<uint32_t>(llround(frac * kDenom));
  if (b >= kDenom) b = kDenom - 1;
  if (a < 15 || a > 90) {
    clk1Actual_ = 0;
    return false;                       // feedback divider outside the 15..90 spec
  }

  bool ok = writeDivider(kRegPllB, encode(a, b, kDenom), 0);
  ok = writeDivider(kRegMs1, encode(d, 0, 1), rExp) && ok;
  // MS1_INT = 1, MS1_SRC = PLLB, source = multisynth 1, 8 mA drive.
  ok = write8(static_cast<uint8_t>(kRegClkCtrl0 + 1), 0x6F) && ok;

  clk1Actual_ = static_cast<double>(xtal_) * (a + static_cast<double>(b) / kDenom) /
                (static_cast<double>(d) * (1u << rExp));

  ok = enable(1, true) && ok;
  return ok && present_;
}

bool Si5351::resetPllB() {
  return write8(kRegPllReset, 0x80);
}

bool Si5351::enable(uint8_t clk, bool on) {
  if (clk > 2) return false;
  if (on) {
    oeb_ = static_cast<uint8_t>(oeb_ & ~(1u << clk));
  } else {
    oeb_ = static_cast<uint8_t>(oeb_ | (1u << clk));
  }
  return write8(kRegOutputEn, oeb_);
}

namespace si5351 {
bool pulseJohnsonClear() { return expander.pulseJohnsonClear(); }
}  // namespace si5351
