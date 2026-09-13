// b4_switching: 4 relays, 2 isolated fast inputs (6N137 on PIN_OPTO_IN[0..1],
// active low on the 3V3 side) and, new in v0.7, the section C power switching
// that the NMR console shares: the DRV8871 field-cycling H-bridge and the
// AOD4184A polarizer FET.
//
// v0.7: the relay gates are no longer MCU pins. They are P1.0..P1.3 of the
// TCA9535 expander (drivers/Tca9535.h) into the AO3400A gates; the 10 k gate
// pull-downs are what hold every relay off while the ESP32 boots and while the
// expander still has its ports as inputs.
//
// The H-bridge and the polarizer are real power: up to 2 A through the coil and
// up to 13 A through the polarizer FET. The NMR sequencer owns both during a
// scan, so both commands refuse while a scan is running (blocks/Busy.h).
//
// Commands: relay {n, on}, relay_all {on}, opto_reset,
//           hbridge {mode: off|fwd|rev|brake}, polarizer {on}
// Status:   relay1..relay4 (0/1), opto1, opto2 (edge counts), opto1_level,
//           opto2_level, hbridge (string), polarizer (0/1)
// The alarm engine's "relay" action calls handle() with cmd "relay".
#pragma once
#include "../Block.h"

class SwitchingBlock : public Block {
 public:
  const char* name() const override { return "b4"; }
  void begin() override;
  void loop() override;
  bool handle(JsonObjectConst cmd, JsonObject reply) override;
  void status(JsonObject out) override;

 private:
  // DRV8871 truth table: IN1/IN2 = 0/0 coast, 1/0 forward, 0/1 reverse,
  // 1/1 brake (both low-side devices on, the coil shorted through them).
  enum HbMode { HB_OFF = 0, HB_FWD, HB_REV, HB_BRAKE };

  void setRelay(int idx, bool on);
  void setHbridge(HbMode mode);
  void setPolarizer(bool on);

  bool relay_[4] = {};
  uint32_t optoCount_[2] = {};
  bool optoLevel_[2] = {};
  HbMode hb_ = HB_OFF;
  bool polarizer_ = false;
  uint32_t lastTick_ = 0;
};
