#include "PowerBlock.h"

#include <math.h>

#include "../../../include/pins.h"
#include "../Vext.h"

void PowerBlock::begin() {
#ifdef SIM
  measured_ = true;   // sim values wobble, so they look measured
#else
  // TODO(B2): configure the rail-sense inputs if the board has any.
  measured_ = false;
  // 11 dB attenuation spans about 0..3.1 V at the pin, so 24 V (2.18 V after the
  // divider) sits where the calibrated reading is good.
  analogSetPinAttenuation(PIN_VEXT_SENSE, ADC_11db);
#endif
  readVext();         // a value before the first scan set can ask for one
}

// Sixteen readings averaged, so one noisy conversion does not refuse a scan set.
// The 100 nF across the divider's 10 k keeps the pin steady between them.
void PowerBlock::readVext() {
#ifdef SIM
  g_vextVolts = 24.0f;
#else
  uint32_t mv = 0;
  for (int i = 0; i < 16; i++) mv += analogReadMilliVolts(PIN_VEXT_SENSE);
  g_vextVolts = static_cast<float>(mv) / 16.0f / 1000.0f * kVextDivider;
#endif
}

void PowerBlock::loop() {
  uint32_t now = millis();
  if (now - lastVextTick_ >= 500) {   // 2 Hz
    lastVextTick_ = now;
    readVext();
  }
  if (now - lastTick_ < 200) return;   // 5 Hz
  lastTick_ = now;
#ifdef SIM
  // SIM: nominal rails with a few mV of noise; the 5 V rail sags slowly over
  // 30 s so an alarm rule like "v5_raw < 4.9 -> notify" can be tested.
  float t = millis() / 1000.0f;
  v5raw_ = 5.0f - 0.15f * (0.5f + 0.5f * sinf(2 * PI * t / 30.0f)) + random(-5, 5) / 1000.0f;
  v3v3_  = 3.30f + random(-3, 3) / 1000.0f;
  v12p_  = 12.0f + random(-20, 20) / 1000.0f;
  v12n_  = -12.0f + random(-20, 20) / 1000.0f;
  v5a_   = 5.00f + random(-3, 3) / 1000.0f;
#else
  // TODO(B2): read the real rails here; nominal values stay otherwise.
#endif
}

bool PowerBlock::handle(JsonObjectConst cmd, JsonObject reply) {
  const char* c = cmd["cmd"] | "";
  if (strcmp(c, "rails") == 0) {
    status(reply);
    return true;
  }
  if (strcmp(c, "vext_check") == 0) {   // {"on":false} when the sense divider is not fitted
    g_vextCheck = argsOf(cmd)["on"] | true;
    reply["on"] = static_cast<bool>(g_vextCheck);
    return true;
  }
  reply["error"] = "unknown cmd";
  return false;
}

void PowerBlock::status(JsonObject out) {
  out["v5_raw"] = v5raw_;
  out["v3v3"] = v3v3_;
  out["v12p"] = v12p_;
  out["v12n"] = v12n_;
  out["v5a"] = v5a_;
  out["measured"] = measured_;
  out["vext"] = roundf(g_vextVolts * 10.0f) / 10.0f;
  out["vext_measured"] = true;
  out["vext_check"] = static_cast<bool>(g_vextCheck);
}
