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

// PIN/SW (bit 9) = 0: every function is register-controlled, including FSEL.
uint16_t Ad9834::control() const {
  uint16_t c = kB28;                   // 28-bit frequency writes
  if (fsel_) c |= kFsel;
  if (psel_) c |= kPsel;
  if (reset_) c |= kReset;
  if (sleep_) c |= (kSleep1 | kSleep12);
  return c;
}

void Ad9834::writeControl() { writeWord(control()); }

void Ad9834::begin(uint32_t mclk_hz) {
  mclk_ = mclk_hz ? mclk_hz : 50000000;
  reset_ = true;
  sleep_ = false;
  psel_ = false;
  fsel_ = false;
  phaseDeg_[0] = phaseDeg_[1] = 0;
  freqWord_ = 0;
  actual_ = 0;

#ifndef SIM
  pinMode(PIN_DDS_FSYNC, OUTPUT);
  digitalWrite(PIN_DDS_FSYNC, HIGH);   // idle high: no frame in progress
  digitalWrite(PIN_DDS_PSEL, LOW);     // ignored with PIN/SW = 0; held at a defined level
  pinMode(PIN_DDS_PSEL, OUTPUT);
  spibus::begin();
#endif

  // RESET parks the DAC at midscale and clears the phase accumulator. The
  // sequencer clears it once the frequency and both phase registers are loaded.
  writeControl();
  setPhase(0, 0.0);
  setPhase(1, 90.0);
}

void Ad9834::setMclk(uint32_t hz) {
  if (hz == 0) return;
  mclk_ = hz;
  actual_ = static_cast<double>(freqWord_) * mclk_ / 268435456.0;
}

void Ad9834::setFrequency(double hz) {
  if (hz < 0) hz = 0;
  const double maxHz = mclk_ * 0.5;
  if (hz > maxHz) hz = maxHz;

  // delta f = MCLK / 2^28, so word = round(hz * 2^28 / MCLK).
  double w = hz * 268435456.0 / static_cast<double>(mclk_);
  if (w > 268435455.0) w = 268435455.0;
  const uint32_t word = static_cast<uint32_t>(llround(w));

  // Under RESET the register in use is rewritten; while the output runs the
  // other one is loaded and FSEL flips to it afterwards (header comment).
  const bool live = !reset_;
  const bool target = live ? !fsel_ : fsel_;
#ifndef SIM
  spibus::Guard g;
  if (!g.ok) return;                   // nothing written: the state below stays true
  const uint16_t prefix = target ? 0x8000 : 0x4000;   // FREQ1 : FREQ0
  SPI.beginTransaction(SPISettings(kSpiHz, MSBFIRST, SPI_MODE2));
  // B28 = 1 means the next two writes to the register are its low then its high
  // 14 bits. The control word (still selecting the old register) comes first, in
  // the same transaction.
  frame(control());
  frame(static_cast<uint16_t>(prefix | (word & 0x3FFF)));
  frame(static_cast<uint16_t>(prefix | ((word >> 14) & 0x3FFF)));
  if (live) {
    fsel_ = target;
    frame(control());                  // switch the output to the new register
  }
  SPI.endTransaction();
#endif
  fsel_ = target;
  freqWord_ = word;
  actual_ = static_cast<double>(word) * mclk_ / 268435456.0;
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
  writeControl();
}


void Ad9834::sleep(bool on) {
  sleep_ = on;
  writeControl();
}
