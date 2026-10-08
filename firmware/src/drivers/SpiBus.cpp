#include "SpiBus.h"

#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>

#ifndef SIM
#include <SPI.h>
#include "../../include/pins.h"
#endif

namespace spibus {
namespace {

SemaphoreHandle_t gMutex = nullptr;
bool gStarted = false;

// The mutex exists even in the SIM build: the NMR sequencer task runs there too,
// so the lock has to behave the same way or the timing code would not be tested.
void ensureMutex() {
  if (!gMutex) gMutex = xSemaphoreCreateRecursiveMutex();
}

}  // namespace

void begin() {
  ensureMutex();
  if (gStarted) return;
  gStarted = true;
#ifndef SIM
  // All three chip selects high before the first clock edge. None has a pull-up
  // on the board and GPIO5 floats at reset: the DAC's /SYNC (through the
  // always-enabled 74HCT125) would otherwise take ADC traffic as a DAC command.
  // Level first, then output, so no pin glitches low on the way.
  const int cs[] = {PIN_CS_ADC, PIN_CS_DAC, PIN_DDS_FSYNC};
  for (int pin : cs) {
    digitalWrite(pin, HIGH);
    pinMode(pin, OUTPUT);
  }
  SPI.begin(PIN_SPI_SCLK, PIN_SPI_MISO, PIN_SPI_MOSI);
#endif
}

bool lock(uint32_t timeout_ms) {
  ensureMutex();
  if (!gMutex) return false;
  return xSemaphoreTakeRecursive(gMutex, pdMS_TO_TICKS(timeout_ms)) == pdTRUE;
}

void unlock() {
  if (gMutex) xSemaphoreGiveRecursive(gMutex);
}

}  // namespace spibus
