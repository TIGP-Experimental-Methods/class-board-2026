#include "DioTrigBlock.h"

#include "../../../include/pins.h"
#include "../../drivers/Tca9535.h"

#ifndef SIM
// LEDC channels for FAST1 / FAST2. Channels share a timer in pairs (0-1, 2-3,
// 4-5, 6-7), and the timer sets the frequency, so the two outputs sit on
// different pairs to run at independent frequencies. analogWrite() would take
// channels from 7 downwards; 2 and 4 stay clear of it and of channel 0.
static const uint8_t kFastLedc[2] = {2, 4};
// Arduino core 2.0.17 clocks the S3's LEDC from the 40 MHz crystal
// (esp32-hal-ledc.c, LEDC_USE_XTAL_CLK), not the 80 MHz APB clock.
static const uint32_t kLedcClockHz = 40000000;
#endif

void DioTrigBlock::begin() {
  // The expander is started by BaseBlock::begin() and comes up with port 0 all
  // zero, so DIO1..8 are already low. This write just makes that explicit.
  writeDio();
#ifndef SIM
  pinMode(PIN_TRIG_DIR, OUTPUT);
  digitalWrite(PIN_TRIG_DIR, LOW);      // safe default: TRIG SMA is an input
  pinMode(PIN_TRIG_IO, INPUT);
  // The fast outputs have no pull resistor: hold them low until fast_out starts a clock.
  for (int i = 0; i < 2; i++) {
    digitalWrite(PIN_FAST_OUT[i], LOW);
    pinMode(PIN_FAST_OUT[i], OUTPUT);
  }
#endif
}

void DioTrigBlock::loop() {
#ifndef SIM
  if (!trigOut_) trigLevel_ = digitalRead(PIN_TRIG_IO);
#endif
}

void DioTrigBlock::writeDio() {
  // One I2C write sets all eight lines at once, so they change together - an
  // improvement on the eight separate GPIO writes this block used in v0.6.
  expander.writePort(EXP_PORT_DIO, mask_);
}

bool DioTrigBlock::setFast(int idx, float hz) {
#ifdef SIM
  fastHz_[idx] = hz;
  return true;
#else
  const int pin = PIN_FAST_OUT[idx];
  const uint8_t ch = kFastLedc[idx];
  if (hz <= 0) {                          // stop: back to a plain low output
    ledcDetachPin(pin);
    digitalWrite(pin, LOW);
    pinMode(pin, OUTPUT);
    fastHz_[idx] = 0;
    return true;
  }
  // The timer counts the LEDC clock through 2^bits steps per period, so the
  // resolution is the largest that fits: freq * 2^bits <= 40 MHz (1..14 bits).
  // Only the 50 % duty matters for a square wave, so one bit is enough at the top.
  const uint32_t f = static_cast<uint32_t>(lroundf(hz));
  uint8_t bits = 1;
  while (bits < 14 && (static_cast<uint64_t>(f) << (bits + 1)) <= kLedcClockHz) bits++;
  const uint32_t got = ledcSetup(ch, f, bits);   // the frequency the divider really gives
  if (got == 0) return false;                    // divider out of range: nothing changed
  ledcAttachPin(pin, ch);
  ledcWrite(ch, 1u << (bits - 1));               // 50 % duty
  fastHz_[idx] = static_cast<float>(got);
  return true;
#endif
}

bool DioTrigBlock::handle(JsonObjectConst cmd, JsonObject reply) {
  const char* c = cmd["cmd"] | "";
  JsonObjectConst a = argsOf(cmd);

  if (strcmp(c, "dio") == 0) {            // {"n":1..8,"level":true}
    if (!expander.present()) { reply["error"] = "expander not present"; return false; }
    int n = a["n"] | 0;
    if (n < 1 || n > 8) { reply["error"] = "n must be 1..8"; return false; }
    if (a["level"] | false) mask_ |= 1 << (n - 1); else mask_ &= ~(1 << (n - 1));
    writeDio();
    reply["mask"] = mask_;
    return true;
  }
  if (strcmp(c, "dio_mask") == 0) {       // {"mask":0..255}
    if (!expander.present()) { reply["error"] = "expander not present"; return false; }
    mask_ = a["mask"] | 0;
    writeDio();
    reply["mask"] = mask_;
    return true;
  }
  if (strcmp(c, "trig_dir") == 0) {       // {"out":true}
    const bool out = a["out"] | false;
    if (out && !trigOut_) trigLevel_ = false;   // an output starts low
#ifndef SIM
    // Never two drivers on one line: the side that stops driving lets go first.
    if (out && !trigOut_) {
      // Input -> output: the level shifter drives GPIO38 until DIR goes high, so
      // GPIO38 waits as a pulled-down input, then DIR turns the shifter round,
      // then GPIO38 drives.
      pinMode(PIN_TRIG_IO, INPUT_PULLDOWN);
      digitalWrite(PIN_TRIG_DIR, HIGH);
      digitalWrite(PIN_TRIG_IO, LOW);
      pinMode(PIN_TRIG_IO, OUTPUT);
    } else if (!out && trigOut_) {
      // Output -> input: GPIO38 lets go first, held low by its pull-down so the
      // SMA sees no pulse while DIR is still high; then DIR hands the line to
      // the SMA side; then the pull-down goes.
      pinMode(PIN_TRIG_IO, INPUT_PULLDOWN);
      digitalWrite(PIN_TRIG_DIR, LOW);
      pinMode(PIN_TRIG_IO, INPUT);
    }
#endif
    trigOut_ = out;
    reply["out"] = trigOut_;
    return true;
  }
  if (strcmp(c, "trig") == 0) {           // {"level":true} - only when trig_dir out
    if (!trigOut_) { reply["error"] = "TRIG is an input; send trig_dir out=true first"; return false; }
    trigLevel_ = a["level"] | false;
#ifndef SIM
    digitalWrite(PIN_TRIG_IO, trigLevel_);
#endif
    reply["level"] = trigLevel_;
    return true;
  }
  if (strcmp(c, "fast_out") == 0) {       // {"n":1..2,"freq_hz":1000}
    int n = a["n"] | 0;
    if (n < 1 || n > 2) { reply["error"] = "n must be 1 or 2"; return false; }
    // 0 = off; otherwise about 3 Hz .. 20 MHz. 20 MHz is both the LEDC's limit
    // (two clock steps per period) and more than the 74HCT125 buffer passes
    // cleanly; below about 2.4 Hz the LEDC divider runs out even at 14 bits.
    // Refused in both builds, so SIM answers as the board does.
    float hz = a["freq_hz"] | 0.0f;
    hz = constrain(hz, 0.0f, 20e6f);
    if ((hz > 0.0f && hz < 3.0f) || !setFast(n - 1, hz)) {
      reply["error"] = "frequency not reachable (LEDC: about 3 Hz..20 MHz)";
      return false;
    }
    reply["n"] = n; reply["freq_hz"] = fastHz_[n - 1];   // the frequency really produced
    return true;
  }
  reply["error"] = "unknown cmd";
  return false;
}

void DioTrigBlock::status(JsonObject out) {
  out["dio"] = mask_;
  char key[5] = "dio1";
  for (int i = 0; i < 8; i++) { key[3] = '1' + i; out[key] = (mask_ >> i) & 1; }
  out["trig_dir"] = trigOut_;
  out["trig"] = trigLevel_;
  out["fast1_hz"] = fastHz_[0]; out["fast2_hz"] = fastHz_[1];
}
