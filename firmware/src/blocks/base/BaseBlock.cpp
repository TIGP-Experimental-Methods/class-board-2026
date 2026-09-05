#include "BaseBlock.h"
#include <WiFi.h>
#include "../../../include/pins.h"

void BaseBlock::begin() {
  pixel_.setPin(PIN_RGB_LED);
  pixel_.begin();
  showLed();
}

void BaseBlock::loop() {
  // 10 Hz "signal": a counter (a ramp) and the chip temperature.
  uint32_t now = millis();
  if (now - lastTick_ >= 100) {
    lastTick_ = now;
    counter_++;
    // temperatureRead() is the ESP32-S3's internal sensor (coarse, ~1 degC).
    tempC_ = temperatureRead();
  }
}

bool BaseBlock::handle(JsonObjectConst cmd, JsonObject reply) {
  const char* c = cmd["cmd"] | "";
  JsonObjectConst a = argsOf(cmd);

  if (strcmp(c, "led") == 0) {            // {"r":0..255,"g":..,"b":..}
    r_ = a["r"] | r_;
    g_ = a["g"] | g_;
    b_ = a["b"] | b_;
    showLed();
    reply["r"] = r_; reply["g"] = g_; reply["b"] = b_;
    return true;
  }
  if (strcmp(c, "brightness") == 0) {     // {"value":0..255}
    brightness_ = a["value"] | brightness_;
    showLed();
    reply["brightness"] = brightness_;
    return true;
  }
  if (strcmp(c, "counter_reset") == 0) {
    counter_ = 0;
    reply["counter"] = counter_;
    return true;
  }
  if (strcmp(c, "info") == 0) {
    reply["fw"] = FW_VERSION;
    reply["chip"] = ESP.getChipModel();
    reply["mac"] = WiFi.macAddress();
    reply["ip"] = (WiFi.getMode() & WIFI_AP) ? WiFi.softAPIP().toString() : WiFi.localIP().toString();
#ifdef SIM
    reply["sim"] = true;
#else
    reply["sim"] = false;
#endif
    return true;
  }
  // TODO(E2): add your own command here. Worked example (workbook ch. 1 A.4):
  //   if (strcmp(c, "press") == 0) { presses_++; setLed(a["r"] | 255, a["g"] | 120, a["b"] | 0);
  //                                  reply["presses"] = presses_; return true; }
  // and in status():  out["presses"] = presses_;   (declare uint32_t presses_ = 0; in the header)

  reply["error"] = "unknown cmd";
  return false;
}

void BaseBlock::status(JsonObject out) {
  out["counter"] = counter_;
  out["temp_c"] = tempC_;
  out["uptime_s"] = millis() / 1000;
  out["rssi"] = (WiFi.getMode() & WIFI_STA) && WiFi.isConnected() ? WiFi.RSSI() : 0;
  out["heap_free"] = ESP.getFreeHeap();
  out["clients"] = WiFi.softAPgetStationNum();
  JsonObject led = out["led"].to<JsonObject>();
  led["r"] = r_; led["g"] = g_; led["b"] = b_; led["brightness"] = brightness_;
}

void BaseBlock::setLed(uint8_t r, uint8_t g, uint8_t b) {
  r_ = r; g_ = g; b_ = b;
  showLed();
}

void BaseBlock::showLed() {
  pixel_.setBrightness(brightness_);
  pixel_.setPixelColor(0, pixel_.Color(r_, g_, b_));
  pixel_.show();
}
