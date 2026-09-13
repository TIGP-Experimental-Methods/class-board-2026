#include "Ads8688.h"

#include <Arduino.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <math.h>

#include "../../include/pins.h"
#include "SpiBus.h"

#ifndef SIM
#include <SPI.h>
#include <soc/gpio_reg.h>
#include <soc/soc.h>
#endif

Ads8688 adc;

namespace {

constexpr uint16_t kCmdNoOp    = 0x0000;
constexpr uint16_t kCmdAutoRst = 0xA000;
constexpr uint16_t kCmdManCh0  = 0xC000;
constexpr uint16_t kRegAutoSeq = 0x01;
constexpr uint8_t  kRegRange0  = 0x05;

// Full-scale volts for each range code, internal 4.096 V reference.
// Index = range code; the gaps (3, 4, 7) are codes the part does not define.
constexpr float kFullScale[8] = {10.24f, 5.12f, 2.56f, 0.0f, 0.0f, 10.24f, 5.12f, 0.0f};
constexpr bool kBipolar[8]    = {true, true, true, false, false, false, false, false};

#ifndef SIM
constexpr uint32_t kSpiHz = 17000000;

// /CS straight to the GPIO set/clear registers. digitalWrite() would work, but in
// the capture loop it is a measurable part of the per-sample budget and there is
// nothing to gain from the extra indirection when the pin is fixed at compile time.
constexpr uint32_t kCsMask = 1u << PIN_CS_ADC;
inline void csLow()  { REG_WRITE(GPIO_OUT_W1TC_REG, kCsMask); }
inline void csHigh() { REG_WRITE(GPIO_OUT_W1TS_REG, kCsMask); }
#endif

// Wait until `due`. Below a millisecond and a half this is a plain busy-wait,
// which is what a capture needs: the sequencer task owns core 1 and its idle
// task is not watchdogged, so nothing is starved. A longer wait (someone asked
// for a very low sample rate) hands the core back instead of spinning.
inline void paceUntil(int64_t due_us) {
  for (;;) {
    const int64_t left = due_us - esp_timer_get_time();
    if (left <= 0) return;
    if (left > 1500) vTaskDelay(pdMS_TO_TICKS(static_cast<uint32_t>((left - 1000) / 1000)));
  }
}

}  // namespace

// Program-register write: sixteen bits of address + write flag + data, then eight
// more clocks in which the part echoes the byte it stored. The echo is what tells
// us a real ADS8688 is on the end of the bus and not a floating MISO line.
bool Ads8688::programWrite(uint8_t addr, uint8_t data) {
#ifdef SIM
  (void)addr;
  (void)data;
  return true;
#else
  const uint32_t word = (static_cast<uint32_t>(addr) << 9) | (1u << 8) | data;
  SPI.beginTransaction(SPISettings(kSpiHz, MSBFIRST, SPI_MODE1));
  csLow();
  SPI.transfer16(static_cast<uint16_t>(word));
  const uint8_t echo = SPI.transfer(0x00);
  csHigh();
  SPI.endTransaction();
  return echo == data;
#endif
}

void Ads8688::begin() {
#ifdef SIM
  present_ = true;      // simulated board: the ADC answers like the real one
#else
  pinMode(PIN_CS_ADC, OUTPUT);
  digitalWrite(PIN_CS_ADC, HIGH);
  spibus::begin();

  spibus::Guard g(200);
  if (!g.ok) {
    present_ = false;
    return;
  }
  // /RST and /PD are tied high on the board, so the part is already out of reset.
  // Two NO_OP frames flush whatever state a warm restart left in its shift register.
  SPI.beginTransaction(SPISettings(kSpiHz, MSBFIRST, SPI_MODE1));
  csLow(); SPI.transfer32(static_cast<uint32_t>(kCmdNoOp) << 16); csHigh();
  csLow(); SPI.transfer32(static_cast<uint32_t>(kCmdNoOp) << 16); csHigh();
  SPI.endTransaction();

  bool ok = true;
  for (uint8_t ch = 0; ch < 8; ch++) {
    ok = programWrite(static_cast<uint8_t>(kRegRange0 + ch), range_[ch]) && ok;
  }
  present_ = ok;        // every range register echoed back what we wrote

  // Auto-scan defaults to the two NMR channels; b1 never uses auto mode.
  programWrite(kRegAutoSeq, 0xC0);
#endif
}

bool Ads8688::setRange(uint8_t ch, uint8_t code) {
  if (ch > 7) return false;
  if (code > 6 || code == 3 || code == 4) return false;   // undefined codes
  range_[ch] = code;
#ifdef SIM
  return true;
#else
  spibus::Guard g;
  if (!g.ok) return false;
  return programWrite(static_cast<uint8_t>(kRegRange0 + ch), code);
#endif
}

int16_t Ads8688::readManual(uint8_t ch) {
  if (ch > 7) return 0;
#ifdef SIM
  // Something plausible to draw: a slow sine on ch 0, a triangle on ch 1, small
  // offsets elsewhere. The b1 block keeps its own richer simulation; this is the
  // fallback for anyone who calls the driver directly.
  const float t = millis() / 1000.0f;
  float v = 0.1f * ch;
  if (ch == 0) v = 4.0f * sinf(2.0f * static_cast<float>(PI) * t);
  if (ch == 1) v = 5.0f * (2.0f * fabsf(fmodf(t, 2.0f) - 1.0f) - 1.0f);
  const float fs = kFullScale[range_[ch]];
  if (fs <= 0) return 0;
  float code = kBipolar[range_[ch]] ? v * 32768.0f / fs : (v / fs) * 65536.0f - 32768.0f;
  if (code > 32767.0f) code = 32767.0f;
  if (code < -32768.0f) code = -32768.0f;
  return static_cast<int16_t>(lroundf(code));
#else
  if (!present_) return 0;
  SPI.beginTransaction(SPISettings(kSpiHz, MSBFIRST, SPI_MODE1));
  // The command frame returns the previous conversion; the channel we asked for
  // comes back in the following frame, which is why NO_OP is sent straight after.
  csLow(); SPI.transfer32(static_cast<uint32_t>(kCmdManCh0 + ch * 0x0400) << 16); csHigh();
  csLow(); const uint32_t r = SPI.transfer32(static_cast<uint32_t>(kCmdNoOp) << 16); csHigh();
  SPI.endTransaction();
  // Straight binary out of the part; flip the top bit to get a signed code.
  return static_cast<int16_t>(static_cast<uint16_t>(r & 0xFFFF) ^ 0x8000);
#endif
}

float Ads8688::toVolts(uint8_t ch, int16_t raw) const {
  if (ch > 7) return 0.0f;
  const uint8_t code = range_[ch];
  const float fs = kFullScale[code];
  if (fs <= 0.0f) return 0.0f;
  if (kBipolar[code]) return static_cast<float>(raw) * fs / 32768.0f;
  // Unipolar: undo the sign flip, then scale 0..65535 over 0..fs.
  return (static_cast<float>(raw) + 32768.0f) * fs / 65536.0f;
}

uint32_t Ads8688::burst(uint8_t mask, int16_t* out, uint32_t n_per_channel,
                        uint32_t rate_hz, uint32_t* achieved_hz) {
  if (achieved_hz) *achieved_hz = 0;
  if (!out || mask == 0 || n_per_channel == 0) return 0;

  // The auto scan walks the mask in ascending channel order, which is exactly
  // the order the caller expects in `out`, so only the count matters here.
  uint32_t nch = 0;
  for (uint8_t c = 0; c < 8; c++) {
    if (mask & (1u << c)) nch++;
  }

  // Pace to whole scans of the mask. A period of zero means "as fast as it goes".
  const int64_t period_us = rate_hz ? (1000000 + rate_hz / 2) / rate_hz : 0;

#ifndef SIM
  if (!present_) return 0;
  programWrite(kRegAutoSeq, mask);
  SPI.beginTransaction(SPISettings(kSpiHz, MSBFIRST, SPI_MODE1));
  // AUTO_RST restarts the sequence at the lowest enabled channel. Its own frame
  // still carries the previous conversion, so it is sent and thrown away; from
  // the next frame on, each NO_OP returns the next channel in the mask.
  csLow(); SPI.transfer32(static_cast<uint32_t>(kCmdAutoRst) << 16); csHigh();
#else
  // The simulated converter: a decaying tone plus noise, so a capture drawn in
  // the app looks like a signal even on a bare dev board. The NMR block puts its
  // own free-induction decay here; this is what a bare `capture` sees.
  uint32_t seed = 12345;
#endif

  const int64_t t0 = esp_timer_get_time();
  for (uint32_t s = 0; s < n_per_channel; s++) {
    if (period_us) paceUntil(t0 + static_cast<int64_t>(s) * period_us);
#ifndef SIM
    for (uint32_t k = 0; k < nch; k++) {
      csLow();
      const uint32_t r = SPI.transfer32(static_cast<uint32_t>(kCmdNoOp) << 16);
      csHigh();
      out[s * nch + k] = static_cast<int16_t>(static_cast<uint16_t>(r & 0xFFFF) ^ 0x8000);
    }
#else
    const float t = rate_hz ? static_cast<float>(s) / static_cast<float>(rate_hz) : s * 1e-5f;
    const float env = expf(-t / 0.4f);
    for (uint32_t k = 0; k < nch; k++) {
      seed = seed * 1664525u + 1013904223u;
      const float noise = (static_cast<int32_t>(seed >> 8) % 2001 - 1000) * 0.3f;
      const float phase = 2.0f * static_cast<float>(PI) * 5400.0f * t + (k ? 1.5708f : 0.0f);
      out[s * nch + k] = static_cast<int16_t>(lroundf(6000.0f * env * sinf(phase) + noise));
    }
#endif
  }
  const int64_t t1 = esp_timer_get_time();

#ifndef SIM
  SPI.endTransaction();
#endif

  if (achieved_hz) {
    const int64_t dt = t1 - t0;
    *achieved_hz = dt > 0 ? static_cast<uint32_t>((static_cast<int64_t>(n_per_channel) * 1000000) / dt)
                          : 0;
  }
  return n_per_channel;
}
