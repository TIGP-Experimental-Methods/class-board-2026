#include "Ad9834.h"

#include <Arduino.h>
#include <math.h>

#include "../../include/pins.h"
#include "SpiBus.h"

#ifndef SIM
#include <SPI.h>
#endif

Ad9834 dds;

namespace {
// Control-register bit positions, datasheet table "Control Register Bits".
constexpr uint16_t kB28    = 1u << 13;
constexpr uint16_t kFsel   = 1u << 11;
constexpr uint16_t kPsel   = 1u << 10;
constexpr uint16_t kPinSw  = 1u << 9;
constexpr uint16_t kReset  = 1u << 8;
constexpr uint16_t kSleep1 = 1u << 7;
constexpr uint16_t kSleep12 = 1u << 6;

#ifndef SIM
constexpr uint32_t kSpiHz = 10000000;

// One 16-bit frame: FSYNC low, sixteen clocks, FSYNC high. The caller holds the
// SPI transaction so a two-word frequency write is not interrupted between its
// halves - the part latches a 28-bit word only when both halves have arrived.
inline void frame(uint16_t word) {
  digitalWrite(PIN_DDS_FSYNC, LOW);
  SPI.transfer16(word);
  digitalWrite(PIN_DDS_FSYNC, HIGH);
}
#endif
}  // namespace

void Ad9834::writeWord(uint16_t word) {
#ifdef SIM
  (void)word;
#else
  spibus::Guard g;
  if (!g.ok) return;
  SPI.beginTransaction(SPISettings(kSpiHz, MSBFIRST, SPI_MODE2));
  frame(word);
  SPI.endTransaction();
#endif
}

void Ad9834::writeControl() {
  uint16_t c = kB28 | kPinSw;          // 28-bit frequency writes, pin-controlled select
  if (reset_) c |= kReset;
  if (sleep_) c |= (kSleep1 | kSleep12);
  // FSEL and PSEL are pin-controlled (PIN/SW = 1), so these bits are ignored.
  // They are cleared anyway so a reader of a register dump is not misled.
  c &= static_cast<uint16_t>(~(kFsel | kPsel));
  writeWord(c);
}

void Ad9834::begin(uint32_t mclk_hz) {
  mclk_ = mclk_hz ? mclk_hz : 50000000;
  reset_ = true;
  sleep_ = false;
  psel_ = false;
  phaseDeg_[0] = phaseDeg_[1] = 0;
  freqWord_ = 0;
  actual_ = 0;

#ifndef SIM
  pinMode(PIN_DDS_FSYNC, OUTPUT);
  digitalWrite(PIN_DDS_FSYNC, HIGH);   // idle high: no frame in progress
  pinMode(PIN_DDS_PSEL, OUTPUT);
  digitalWrite(PIN_DDS_PSEL, LOW);     // PHASE0
  spibus::begin();
#endif

  // RESET parks the DAC at midscale and clears the phase accumulator. The
  // sequencer clears it once the frequency and both phase registers are loaded.
  writeControl();
  setPhase(0, 0.0);
  setPhase(1, 90.0);
}

void Ad9834::setFrequency(double hz) {
  if (hz < 0) hz = 0;
  const double maxHz = mclk_ * 0.5;
  if (hz > maxHz) hz = maxHz;

  // delta f = MCLK / 2^28, so word = round(hz * 2^28 / MCLK).
  double w = hz * 268435456.0 / static_cast<double>(mclk_);
  if (w > 268435455.0) w = 268435455.0;
  freqWord_ = static_cast<uint32_t>(llround(w));
  actual_ = static_cast<double>(freqWord_) * mclk_ / 268435456.0;

#ifndef SIM
  spibus::Guard g;
  if (!g.ok) return;
  SPI.beginTransaction(SPISettings(kSpiHz, MSBFIRST, SPI_MODE2));
  // B28 = 1 means the next two writes to FREQ0 are its low then its high 14 bits.
  // The control word has to come first, in the same transaction.
  uint16_t c = kB28 | kPinSw;
  if (reset_) c |= kReset;
  if (sleep_) c |= (kSleep1 | kSleep12);
  frame(c);
  frame(static_cast<uint16_t>(0x4000 | (freqWord_ & 0x3FFF)));
  frame(static_cast<uint16_t>(0x4000 | ((freqWord_ >> 14) & 0x3FFF)));
  SPI.endTransaction();
#endif
}

void Ad9834::setPhase(uint8_t reg, double deg) {
  if (reg > 1) return;
  // Wrap into 0..360 so a sequencer can hand over -90 or 450 without thinking.
  double d = fmod(deg, 360.0);
  if (d < 0) d += 360.0;
  phaseDeg_[reg] = d;

  // 12-bit register: one count is 360 / 4096 = 0.088 degrees.
  const uint16_t bits = static_cast<uint16_t>(llround(d * 4096.0 / 360.0)) & 0x0FFF;
  const uint16_t prefix = (reg == 0) ? 0xC000 : 0xE000;
  writeWord(static_cast<uint16_t>(prefix | bits));
}

void Ad9834::setReset(bool on) {
  reset_ = on;
  writeControl();
}

void Ad9834::selectPhase(bool p1) {
  psel_ = p1;
#ifndef SIM
  digitalWrite(PIN_DDS_PSEL, p1 ? HIGH : LOW);
#endif
}

void Ad9834::sleep(bool on) {
  sleep_ = on;
  writeControl();
}
