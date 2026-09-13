#include "InputsBlock.h"

#include "../../../include/pins.h"
#include "../../drivers/Ads8688.h"
#include "../../drivers/SpiBus.h"

void InputsBlock::begin() {
  // The ADS8688 driver (drivers/Ads8688.h) owns the chip select and the command
  // words; BaseBlock::begin() has already started the shared SPI bus. Under SIM
  // the driver keeps state and the readings below are synthesised.
  spibus::begin();
  adc.begin();
  for (int i = 0; i < kChannels; i++) range_[i] = adc.range(i);
}

void InputsBlock::loop() {
  uint32_t now = millis();
  if (now - lastTick_ < 50) return;   // 20 Hz is enough for the status panel
  lastTick_ = now;
  // During an NMR capture the sequencer holds the bus for the whole burst; a
  // status read that waited for it would stall the main loop, so skip this pass.
  if (!readAll(0)) return;
}

bool InputsBlock::readAll(uint32_t lock_ms) {
#ifdef SIM
  (void)lock_ms;
  // SIM: ch1 = 1 Hz sine 8 Vpp, ch2 = 0.5 Hz triangle, others = offsets + noise.
  float t = millis() / 1000.0f;
  volts_[0] = 4.0f * sinf(2 * PI * 1.0f * t);
  volts_[1] = 5.0f * (2 * fabsf(fmodf(t, 2.0f) - 1.0f) - 1.0f);
  for (int i = 2; i < kChannels; i++) volts_[i] = 0.1f * i + random(-50, 50) / 10000.0f;
#else
  // Manual mode: MAN_CH_n selects the channel, the result arrives in the next
  // frame (drivers/Ads8688.h). The driver flips the top bit so the code is signed.
  spibus::Guard g(lock_ms);
  if (!g.ok) return false;
  for (int i = 0; i < kChannels; i++) volts_[i] = adc.toVolts(i, adc.readManual(i));
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
    if (ch < 1 || ch > kChannels || range < 0 || range > 6) {
      reply["error"] = "ch 1..8, range 0..6";
      return false;
    }
    range_[ch - 1] = range;
    {
      spibus::Guard g(50);
      if (!g.ok) { reply["error"] = "SPI bus busy (nmr capture running)"; return false; }
      adc.setRange(ch - 1, range);   // program register 0x05 + ch-1
    }
    reply["ch"] = ch;
    reply["range"] = range;
    return true;
  }
  reply["error"] = "unknown cmd";
  return false;
}

void InputsBlock::status(JsonObject out) {
  char key[4] = "ai1";
  for (int i = 0; i < kChannels; i++) {
    key[2] = '1' + i;
    out[key] = volts_[i];
  }
  out["range"] = range_[0];   // range of ch1 (the panel shows one selector)
}
