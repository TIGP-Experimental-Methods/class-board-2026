#include "InputsBlock.h"

#include "../../../include/pins.h"
#include "../../drivers/Ads8688.h"
#include "../../drivers/SpiBus.h"
#include "SimSignals.h"

void InputsBlock::begin() {
  // The ADS8688 driver (drivers/Ads8688.h) owns the chip select and the command
  // words; BaseBlock::begin() has already started the shared SPI bus. Under SIM
  // the driver keeps state and the readings below are synthesised.
  spibus::begin();
  adc.begin();
  for (int i = 0; i < kChannels; i++) range_[i] = adc.range(kAinOfAi[i]);
  scope_.begin();
}

void InputsBlock::loop() {
  scope_.poll();                      // a finished scope frame goes out first
  uint32_t now = millis();
  if (now - lastTick_ < 50) return;   // 20 Hz is enough for the status panel
  lastTick_ = now;
  // During an NMR capture the sequencer holds the bus for the whole burst; a
  // status read that waited for it would stall the main loop, so skip this pass.
  // A scope stream holds it for one chunk at a time, so the same applies - and
  // the streamed input's reading comes from the stream instead.
  if (!readAll(0) && scope_.mode() == Scope::Mode::Stream && !isnan(scope_.lastVolts()))
    volts_[scope_.channel() - 1] = scope_.lastVolts();
}

bool InputsBlock::readAll(uint32_t lock_ms) {
#ifdef SIM
  (void)lock_ms;
  // SIM: the same signals the scope sees (SimSignals.h), through each input's range.
  const double t = millis() / 1000.0;
  for (int i = 0; i < kChannels; i++) {
    const uint8_t ch = kAinOfAi[i];
    volts_[i] = adc.toVolts(ch, b1SimCode(ch, b1SimVolts(i, t, seed_)));
  }
#else
  // Manual mode: MAN_CH_n selects the channel, the result arrives in the next
  // frame (drivers/Ads8688.h). The driver flips the top bit so the code is signed.
  spibus::Guard g(lock_ms);
  if (!g.ok) return false;
  for (int i = 0; i < kChannels; i++) {
    const uint8_t ch = kAinOfAi[i];
    volts_[i] = adc.toVolts(ch, adc.readManual(ch));
  }
#endif
  return true;
}

bool InputsBlock::handle(JsonObjectConst cmd, JsonObject reply) {
  const char* c = cmd["cmd"] | "";
  JsonObjectConst a = argsOf(cmd);

  if (strcmp(c, "read_all") == 0) {
    if (!readAll(50)) { reply["error"] = "SPI bus busy (nmr capture running)"; return false; }
    JsonArray ai = reply["ai"].to<JsonArray>();
    for (int i = 0; i < kChannels; i++) ai.add(volts_[i]);
    return true;
  }
  if (strcmp(c, "set_range") == 0) {     // {"ch":1..8,"range":0..6}
    int ch = a["ch"] | 0;
    int range = a["range"] | -1;
    if (ch < 1 || ch > kChannels || range < 0 || range > 6 || range == 3 || range == 4) {
      reply["error"] = "ch 1..8, range 0, 1, 2, 5 or 6";
      return false;
    }
    {
      spibus::Guard g(150);              // a scope chunk holds the bus up to 100 ms
      if (!g.ok) { reply["error"] = "SPI bus busy (nmr capture running)"; return false; }
      if (!adc.setRange(kAinOfAi[ch - 1], range)) { reply["error"] = "range not accepted"; return false; }
    }
    range_[ch - 1] = range;
    reply["ch"] = ch;
    reply["range"] = range;
    return true;
  }
  if (scopeCommand(c, a, reply)) return !reply["error"].is<const char*>();
  reply["error"] = "unknown cmd";
  return false;
}

// stream / capture / stop. Returns false only when `c` is not one of them;
// a refused request returns true with reply["error"] set.
bool InputsBlock::scopeCommand(const char* c, JsonObjectConst a, JsonObject reply) {
  const bool isStream = strcmp(c, "stream") == 0;
  const bool isCapture = strcmp(c, "capture") == 0;
  if (strcmp(c, "stop") == 0) {
    scope_.stop();
    reply["mode"] = "idle";
    return true;
  }
  if (!isStream && !isCapture) return false;

  const int ch = a["ch"] | 1;
  if (ch < 1 || ch > kChannels) { reply["error"] = "ch 1..8"; return true; }
  const uint32_t rate = a["rate_hz"] | 0u;
#ifndef SIM
  if (!adc.present()) { reply["error"] = "ADS8688 not found (bare dev board? flash esp32s3-sim)"; return true; }
#endif

  if (isStream) {
    if (rate == 0) {                     // {"ch":1,"rate_hz":0} = stop, as in the spec
      if (scope_.mode() == Scope::Mode::Stream) scope_.stop();
      reply["ch"] = ch;
      reply["rate_hz"] = 0;
      return true;
    }
    const char* why = scope_.startStream(ch, kAinOfAi[ch - 1], rate, a["chunk"] | 0u);
    if (why) { reply["error"] = why; return true; }
    reply["ch"] = ch;
    reply["rate_hz"] = rate;
    reply["chunk"] = scope_.chunk();
    reply["lease_s"] = Scope::kStreamLeaseMs / 1000;
    return true;
  }

  Scope::Trigger trig;
  JsonObjectConst t = a["trig"].as<JsonObjectConst>();
  if (!t.isNull()) {
    trig.on = true;
    trig.level_v = t["level"] | 0.0f;
    const char* edge = t["edge"] | "rising";
    if (strcmp(edge, "rising") != 0 && strcmp(edge, "falling") != 0) {
      reply["error"] = "trig.edge rising or falling";
      return true;
    }
    trig.rising = strcmp(edge, "rising") == 0;
    trig.pre = t["pre"] | 0u;
    trig.timeout_ms = a["timeout_ms"] | 0u;
  }
  const uint32_t n = a["n"] | 1000u;
  const char* why = scope_.startCapture(ch, kAinOfAi[ch - 1], rate, n, trig);
  if (why) { reply["error"] = why; return true; }
  reply["ch"] = ch;
  reply["rate_hz"] = rate;
  reply["n"] = n;
  reply["armed"] = true;
  reply["trig"] = trig.on;
  return true;
}

void InputsBlock::status(JsonObject out) {
  char key[4] = "ai1";
  for (int i = 0; i < kChannels; i++) {
    key[2] = '1' + i;
    out[key] = volts_[i];
  }
  out["range"] = range_[0];   // range of AI1 (kept for older panels and scripts)
  JsonArray r = out["ranges"].to<JsonArray>();   // an array, so the chart does not list it
  for (int i = 0; i < kChannels; i++) r.add(range_[i]);

  JsonObject s = out["scope"].to<JsonObject>();
  const Scope::Mode m = scope_.mode();
  s["mode"] = m == Scope::Mode::Stream ? "stream" : m == Scope::Mode::Capture ? "armed" : "idle";
  s["ch"] = scope_.channel();
  s["rate_hz"] = scope_.rateHz();
  s["frames"] = scope_.frames();
  s["dropped"] = scope_.dropped();
  if (*scope_.lastStop()) s["last"] = scope_.lastStop();
}
