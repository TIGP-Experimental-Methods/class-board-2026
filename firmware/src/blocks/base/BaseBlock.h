// "base" block: the things every board has, even a bare dev board.
//   * RGB status LED (WS2812 on GPIO48) - colour + brightness from the phone
//   * a free-running counter and the chip temperature as a "signal" so the
//     live chart has something to draw on day 1
//   * uptime, WiFi RSSI, free heap
// Students' day-1 exercise E2 adds one command + one live measurement here
// (workbook ch. 1 A.4: set_avg {n} + adc_v / adc_sd from a 1 kHz ring buffer on GPIO 4;
//  the LED 'press' button + 'presses' counter is the minimal fallback).
#pragma once
#include <Adafruit_NeoPixel.h>
#include "../Block.h"

class BaseBlock : public Block {
 public:
  const char* name() const override { return "base"; }
  void begin() override;
  void loop() override;
  bool handle(JsonObjectConst cmd, JsonObject reply) override;
  void status(JsonObject out) override;

  // Used by main.cpp to show WiFi state on the LED before a client connects.
  void setLed(uint8_t r, uint8_t g, uint8_t b);

 private:
  void showLed();

  Adafruit_NeoPixel pixel_{1, /*pin*/ 48, NEO_GRB + NEO_KHZ800};
  uint8_t r_ = 0, g_ = 0, b_ = 40;   // boot colour: dim blue
  uint8_t brightness_ = 40;          // 0..255
  uint32_t counter_ = 0;             // increments 10x per second
  uint32_t lastTick_ = 0;
  float tempC_ = 0;
};
