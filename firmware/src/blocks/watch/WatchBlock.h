// watch: a drift and excursion monitor on one front-panel analog input.
//
// Why this and not just an alarm on the raw voltage. The alarm engine can
// already do {block:"b1", key:"ai3", op:"gt", threshold:1.5}. On a real analog
// input that rule chatters: the input is noisy, so it crosses any threshold
// dozens of times a second and fires on the first noise peak rather than on
// the thing you care about. This block watches one channel over a window and
// publishes values that are worth alarming on instead:
//
//   dev        how far the MEAN has moved from the baseline you zeroed at.
//              Noise averages out of this, so a rule on dev fires when the
//              signal has actually moved.
//   drift      volts per minute, from the first half of the window against the
//              second. Catches a slow walk long before dev crosses anything.
//   rms        the noise itself. Alarm on this and you are watching the
//              instrument's health, not its reading - a connector going
//              intermittent shows up here first.
//   excursions samples further than SIGMA sigma from the mean. A count, so a
//              rule on it fires on a burst of spikes that the mean hides.
//
// All of those are top-level numbers in status(), which is what the alarm
// engine needs to see them.
//
// Reads the ADS8688 itself through drivers/Ads8688.h, under the SPI lock,
// because a block never calls another block. Panel input AIn is ADC channel
// kAinOfAi[n-1] (pins.h), the same mapping b1 uses.
//
// Commands: set_input {ch}, set_window {s}, set_sigma {k}, zero, reset
// Status:   ch, v, mean, rms, pp, dev, drift, excursions, baseline, n
#pragma once
#include "../Block.h"

class WatchBlock : public Block {
 public:
  const char* name() const override { return "watch"; }
  void begin() override;
  void loop() override;
  bool handle(JsonObjectConst cmd, JsonObject reply) override;
  void status(JsonObject out) override;

 private:
  // 20 Hz for 30 s. 600 floats is 2.4 kB, which is affordable here; a longer
  // window would be better served by keeping running sums instead.
  static constexpr int kMaxSamples = 600;
  static constexpr int kRateHz = 20;

  bool sample(uint32_t lock_ms);   // false = the SPI bus was busy
  void recompute();

  int   ch_ = 1;                   // panel input AI1..AI8
  int   window_ = 200;             // samples held, = window seconds * kRateHz
  float sigma_ = 3.0f;             // what counts as an excursion

  float buf_[kMaxSamples] = {};
  int   head_ = 0;                 // next write position
  int   count_ = 0;                // how many of buf_ are valid

  float v_ = 0, mean_ = 0, rms_ = 0, pp_ = 0, drift_ = 0;
  float baseline_ = 0;
  uint32_t excursions_ = 0;

  uint32_t lastTick_ = 0;
};
