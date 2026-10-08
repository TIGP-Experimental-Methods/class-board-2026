#include "SwitchingBlock.h"

#include "../../../include/pins.h"
#include "../../drivers/Tca9535.h"
#include "../Busy.h"

#ifndef SIM
#include <driver/pcnt.h>

// The falling edges of OPTO_IN1/2 (an input switching on) are counted by the
// ESP32's hardware pulse counter, one unit per input, so a fast pulse train costs
// no CPU time: an interrupt per edge would starve loop() and the NMR sequencer on
// core 1. Nothing else in this firmware uses the pulse counter.
static const pcnt_unit_t kOptoUnit[2] = {PCNT_UNIT_0, PCNT_UNIT_1};
static const int16_t kPcntLimit = 32767;        // the counter is 16-bit signed
static volatile uint32_t gOptoWraps[2] = {0, 0};

// The counter returns to 0 when it reaches its high limit; this interrupt counts
// those wraps, so it runs once per 32767 edges, not once per edge.
static void optoWrapIsr(void* arg) {
  gOptoWraps[reinterpret_cast<intptr_t>(arg)]++;
}

static void optoCounterBegin(int i) {
  pcnt_config_t c = {};
  c.pulse_gpio_num = PIN_OPTO_IN[i];
  c.ctrl_gpio_num = PCNT_PIN_NOT_USED;
  c.lctrl_mode = PCNT_MODE_KEEP;
  c.hctrl_mode = PCNT_MODE_KEEP;
  c.pos_mode = PCNT_COUNT_DIS;
  c.neg_mode = PCNT_COUNT_INC;                  // falling edge = an input switching on
  c.counter_h_lim = kPcntLimit;
  c.counter_l_lim = -kPcntLimit;
  c.unit = kOptoUnit[i];
  c.channel = PCNT_CHANNEL_0;
  pcnt_unit_config(&c);
  // Glitch filter: pulses shorter than 80 APB cycles (1 us at 80 MHz) are ignored.
  pcnt_set_filter_value(kOptoUnit[i], 80);
  pcnt_filter_enable(kOptoUnit[i]);
  pcnt_isr_handler_add(kOptoUnit[i], optoWrapIsr, reinterpret_cast<void*>(static_cast<intptr_t>(i)));
  pcnt_event_enable(kOptoUnit[i], PCNT_EVT_H_LIM);
  pcnt_counter_pause(kOptoUnit[i]);
  pcnt_counter_clear(kOptoUnit[i]);
  pcnt_counter_resume(kOptoUnit[i]);
}

// Wraps x 32767 + the counter, read again if a wrap was counted in between.
static uint32_t optoCounterRead(int i) {
  uint32_t wraps;
  int16_t count = 0;
  do {
    wraps = gOptoWraps[i];
    pcnt_get_counter_value(kOptoUnit[i], &count);
  } while (wraps != gOptoWraps[i]);
  return wraps * static_cast<uint32_t>(kPcntLimit) + static_cast<uint32_t>(count);
}
#endif

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
  // Edges are counted in hardware; loop() only polls the levels for the status.
  pcnt_isr_service_install(0);
  for (int i = 0; i < 2; i++) optoCounterBegin(i);
#endif
}

void SwitchingBlock::loop() {
  uint32_t now = millis();
  // The polarizer deadline is checked on every pass, not at the 10 Hz below:
  // the coil must never stay on longer than asked.
  if (polarizer_) {
#ifndef SIM
    // The NMR sequencer switches FET_GATE off after every scan without telling
    // this block; once the pin is low there is nothing left to time.
    if (digitalRead(PIN_FET_GATE) == LOW) polarizer_ = false;
#endif
    if (polarizer_ && static_cast<int32_t>(now - polarizerOffAt_) >= 0) {
      // During a scan the sequencer owns FET_GATE (it switched the coil off when
      // the scan started and does again when it ends): only the deadline goes.
      if (nmr_busy()) polarizer_ = false;
      else setPolarizer(false, 0);
    }
  }
  if (now - lastTick_ < 100) return;
  lastTick_ = now;
#ifdef SIM
  // SIM: opto 1 sees a 2 Hz square wave, opto 2 sees nothing.
  bool level = ((now / 250) % 2) == 0;
  if (level != optoLevel_[0]) { optoLevel_[0] = level; if (!level) optoCount_[0]++; }
#else
  for (int i = 0; i < 2; i++) {
    optoLevel_[i] = digitalRead(PIN_OPTO_IN[i]);
    // Never step backwards: a read in the microseconds between the counter's
    // return to 0 and its wrap interrupt would come out 32767 short.
    const uint32_t n = optoCounterRead(i);
    if (n > optoCount_[i]) optoCount_[i] = n;
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

void SwitchingBlock::setPolarizer(bool on, uint32_t ms) {
  // FET_GATE switches a low-resistance coil onto an external supply with no
  // on-board current limit, so "on" always comes with a deadline that loop() keeps.
  polarizer_ = on;
  polarizerOffAt_ = millis() + ms;
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
    // One port write for all seven, so the outputs change together. The driver
    // does the read-modify-write under its lock, so the counter clear (P1.4),
    // which the NMR task pulses, is never written back stale from here.
    uint8_t mask = 0;
    for (int i = 0; i < kModuleOutputs; i++) {
      module_[i] = on;
      mask = static_cast<uint8_t>(mask | (1u << EXP_BIT_MOD[i]));
    }
    expander.writeMasked(EXP_PORT_CTRL, mask, on ? mask : 0);
    reply["on"] = on;
    return true;
  }
  if (strcmp(c, "opto_reset") == 0) {
#ifndef SIM
    for (int i = 0; i < 2; i++) {
      pcnt_counter_clear(kOptoUnit[i]);
      gOptoWraps[i] = 0;
    }
#endif
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
  if (strcmp(c, "polarizer") == 0) {      // {"on":true,"ms":10000}
    if (nmr_busy()) { reply["error"] = "nmr scan running"; return false; }
    const bool on = a["on"] | false;
    // as<float>() so that 500.0 counts as 500 (the | default would ignore a float).
    long ms = a["ms"].isNull() ? static_cast<long>(kPolarizerMaxMs) : lroundf(a["ms"].as<float>());
    ms = on ? constrain(ms, 1L, static_cast<long>(kPolarizerMaxMs)) : 0L;
    setPolarizer(on, static_cast<uint32_t>(ms));
    reply["on"] = polarizer_;
    reply["ms"] = ms;
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
#ifdef SIM
  out["hbridge"] = hbName(hb_);
  out["polarizer"] = polarizer_;
#else
  // The NMR sequencer drives these pins low after every scan without telling
  // this block, so the status reads the pins themselves. On the ESP32 an OUTPUT
  // pin keeps its input buffer on (OUTPUT = 0x03 = input | output in this core),
  // so digitalRead() returns the level being driven.
  const bool in1 = digitalRead(PIN_HB_IN1) == HIGH;
  const bool in2 = digitalRead(PIN_HB_IN2) == HIGH;
  out["hbridge"] = hbName(in1 ? (in2 ? HB_BRAKE : HB_FWD) : (in2 ? HB_REV : HB_OFF));
  out["polarizer"] = digitalRead(PIN_FET_GATE) == HIGH;
#endif
}
