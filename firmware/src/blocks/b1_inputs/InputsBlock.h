// b1_inputs: ADS8688 8-channel 16-bit ADC over SPI (CS = PIN_CS_ADC),
// +-10 V inputs AI1..AI8 on the front-panel SMAs.
// v0.7: the chip is driven through drivers/Ads8688.h, shared with the NMR capture,
// so every transfer takes the SPI lock (drivers/SpiBus.h). Panel input AIn is ADC
// channel kAinOfAi[n-1] (pins.h); `ch` in the commands and the status keys is always
// the panel input number. AI7 and AI8 (AIN_3, AIN_2) carry the receiver I and Q
// when the J14 / J15 shunts are on 2-3, and start on the +-5.12 V range.
// Commands: read_all, set_range {ch, range}   Status: ai1..ai8 (volts), range
#pragma once
#include "../Block.h"

class InputsBlock : public Block {
 public:
  const char* name() const override { return "b1"; }
  void begin() override;
  void loop() override;
  bool handle(JsonObjectConst cmd, JsonObject reply) override;
  void status(JsonObject out) override;

 private:
  static constexpr int kChannels = 8;
  bool readAll(uint32_t lock_ms);   // false = the SPI bus was busy

  float volts_[kChannels] = {};     // index = panel input AI1..AI8
  // ADS8688 range codes: 0 = +-10 V (2.5*Vref), 1 = +-5 V, 2 = +-2.5 V,
  // 5 = 0..10 V, 6 = 0..5 V (datasheet, "Range Select Registers").
  uint8_t range_[kChannels] = {};   // index = panel input AI1..AI8

  uint32_t lastTick_ = 0;
};
