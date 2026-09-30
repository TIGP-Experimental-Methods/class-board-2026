#include "SwitchingBlock.h"

#include "../../../include/pins.h"
#include "../../drivers/Tca9535.h"
#include "../Busy.h"

static const char* hbName(int m) {
  switch (m) {
    case 1: return "fwd";
    case 2: return "rev";
    case 3: return "brake";
    default: return "off";
  }
}

void SwitchingBlock::begin() {
  // Module outputs: nothing to configure here. The expander comes up with
  // MOD1..MOD7 low (BaseBlock::begin() writes the output registers before the
  // direction registers) and the panel pull-downs hold them low until then.
#ifndef SIM
  // The 1 k pull-ups are on the front panel; the internal pull-up keeps the
  // inputs defined when the panel is unplugged.
  for (int i = 0; i < 2; i++) pinMode(PIN_OPTO_IN[i], INPUT_PULLUP);
  // Both power outputs start off and stay off until someone asks. Drive them low
  // before making them outputs so the pin cannot glitch high on the way.
  digitalWrite(PIN_HB_IN1, LOW);
  digitalWrite(PIN_HB_IN2, LOW);
  digitalWrite(PIN_FET_GATE, LOW);
  pinMode(PIN_HB_IN1, OUTPUT);
  pinMode(PIN_HB_IN2, OUTPUT);
  pinMode(PIN_FET_GATE, OUTPUT);
  // TODO(B4): attachInterrupt() on PIN_OPTO_IN[] (FALLING) to count edges
  // faster than loop() can poll; keep the ISR to a volatile counter++.
#endif
}

void SwitchingBlock::loop() {
  uint32_t now = millis();
  if (now - lastTick_ < 100) return;
  lastTick_ = now;
#ifdef SIM
  // SIM: opto 1 sees a 2 Hz square wave, opto 2 sees nothing.
  bool level = ((now / 250) % 2) == 0;
  if (level != optoLevel_[0]) { optoLevel_[0] = level; if (!level) optoCount_[0]++; }
#else
  for (int i = 0; i < 2; i++) {
    bool level = digitalRead(PIN_OPTO_IN[i]);
    if (level != optoLevel_[i]) { optoLevel_[i] = level; if (!level) optoCount_[i]++; }
  }
#endif
}

void SwitchingBlock::setModule(int idx, bool on) {
  module_[idx] = on;
  // Expander port 1, active high (MOD5..MOD7 skip P1.4, the counter clear).
  expander.writeBit(EXP_PORT_CTRL, EXP_BIT_MOD[idx], on);
}

void SwitchingBlock::setHbridge(HbMode mode) {
  hb_ = mode;
#ifndef SIM
  const bool in1 = (mode == HB_FWD) || (mode == HB_BRAKE);
  const bool in2 = (mode == HB_REV) || (mode == HB_BRAKE);
  // Drop to coast first: going straight from forward to reverse would put both
  // sides of the bridge through a shoot-through window the DRV8871 has to catch.
  digitalWrite(PIN_HB_IN1, LOW);
  digitalWrite(PIN_HB_IN2, LOW);
  digitalWrite(PIN_HB_IN1, in1);
  digitalWrite(PIN_HB_IN2, in2);
#endif
}

void SwitchingBlock::setPolarizer(bool on) {
  polarizer_ = on;
#ifndef SIM
  digitalWrite(PIN_FET_GATE, on ? HIGH : LOW);
#endif
}

bool SwitchingBlock::handle(JsonObjectConst cmd, JsonObject reply) {
  const char* c = cmd["cmd"] | "";
  JsonObjectConst a = argsOf(cmd);

  if (strcmp(c, "module") == 0) {         // {"n":1..7,"on":true}
    if (!expander.present()) { reply["error"] = "expander not present"; return false; }
    int n = a["n"] | 0;
    if (n < 1 || n > kModuleOutputs) { reply["error"] = "n must be 1..7"; return false; }
    setModule(n - 1, a["on"] | false);
    reply["n"] = n; reply["on"] = module_[n - 1];
    return true;
  }
  if (strcmp(c, "module_all") == 0) {     // {"on":false}
    if (!expander.present()) { reply["error"] = "expander not present"; return false; }
    const bool on = a["on"] | false;
    // One port write for all seven, so the outputs change together.
    uint8_t v = expander.cached(EXP_PORT_CTRL);
    for (int i = 0; i < kModuleOutputs; i++) {
      module_[i] = on;
      const uint8_t bit = static_cast<uint8_t>(1u << EXP_BIT_MOD[i]);
      v = on ? static_cast<uint8_t>(v | bit) : static_cast<uint8_t>(v & ~bit);
    }
    expander.writePort(EXP_PORT_CTRL, v);
    reply["on"] = on;
    return true;
  }
  if (strcmp(c, "opto_reset") == 0) {
    optoCount_[0] = optoCount_[1] = 0;
    return true;
  }
  if (strcmp(c, "hbridge") == 0) {        // {"mode":"off"|"fwd"|"rev"|"brake"}
    if (nmr_busy()) { reply["error"] = "nmr scan running"; return false; }
    const char* m = a["mode"] | "off";
    HbMode mode;
    if (strcmp(m, "off") == 0) mode = HB_OFF;
    else if (strcmp(m, "fwd") == 0) mode = HB_FWD;
    else if (strcmp(m, "rev") == 0) mode = HB_REV;
    else if (strcmp(m, "brake") == 0) mode = HB_BRAKE;
    else { reply["error"] = "mode must be off, fwd, rev or brake"; return false; }
    setHbridge(mode);
    reply["mode"] = hbName(hb_);
    return true;
  }
  if (strcmp(c, "polarizer") == 0) {      // {"on":true}
    if (nmr_busy()) { reply["error"] = "nmr scan running"; return false; }
    setPolarizer(a["on"] | false);
    reply["on"] = polarizer_;
    return true;
  }
  reply["error"] = "unknown cmd";
  return false;
}

void SwitchingBlock::status(JsonObject out) {
  char key[8] = "module1";
  for (int i = 0; i < kModuleOutputs; i++) {
    key[6] = static_cast<char>('1' + i);
    out[key] = module_[i];
  }

  out["opto1"] = optoCount_[0]; out["opto2"] = optoCount_[1];
  out["opto1_level"] = optoLevel_[0]; out["opto2_level"] = optoLevel_[1];
  out["hbridge"] = hbName(hb_);
  out["polarizer"] = polarizer_;
}
