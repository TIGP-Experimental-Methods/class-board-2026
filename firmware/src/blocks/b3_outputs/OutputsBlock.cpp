#include "OutputsBlock.h"

#include "../../../include/pins.h"
#include "../../drivers/SpiBus.h"
#ifndef SIM
#include <SPI.h>
#endif

static const char* modeName(int m) { return m == 0 ? "off" : (m == 1 ? "dc" : "sine"); }

#ifndef SIM
// One DAC8563 frame (datasheet SLAS719E section 8.5): 24 bits while /SYNC is
// low, MSB first, latched on the falling SCLK edge (mode 1). First byte
// X X C2 C1 C0 A2 A1 A0, then 16 data bits. SCLK and DIN pass through two gates
// of the 74HCT125 whose relative skew is not specified, hence 8 MHz and not the
// ADC's 17. /LDAC is grounded, so every write updates the output at once.
// The caller holds the SPI lock.
static void dacFrame(uint8_t cmdAddr, uint16_t data) {
  SPI.beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE1));
  digitalWrite(PIN_CS_DAC, LOW);
  SPI.transfer(cmdAddr);
  SPI.transfer16(data);
  digitalWrite(PIN_CS_DAC, HIGH);
  SPI.endTransaction();
}
#endif

void OutputsBlock::begin() {
#ifndef SIM
  // The shared SPI2 bus (drivers/SpiBus.h): one lock for ADC, DAC and DDS. Its
  // begin() has already driven /SYNC (PIN_CS_DAC) high.
  spibus::begin();
  // The DAC keeps its registers through an ESP32 reset and powers up with the
  // reference off (its output undefined), so both are set on every start.
  spibus::Guard g;
  if (!g.ok) return;
  dacFrame(0x38, 0x0001);   // internal 2.5 V reference on; this also sets gain 2
  dacFrame(0x1F, 0x8000);   // write and update both channels: mid-scale = 0 V on AO
#endif
}

void OutputsBlock::loop() {
  // The sine is synthesised here at ~1 kHz update rate: fine for the demo
  // (waveform out, seen on the own input). A real AWG would use timer + DMA.
  uint32_t now = millis();
  if (now == lastTick_) return;
  lastTick_ = now;
  float t = now / 1000.0f;
  for (int i = 0; i < 2; i++) {
    Channel& c = ch_[i];
    switch (c.mode) {
      case OFF:  c.volts = 0; break;
      case DC:   c.volts = c.dc; break;
      case SINE: c.volts = c.offset + c.amp * sinf(2 * PI * c.freq * t); break;
    }
    writeDac(i, c.volts);
  }
}

void OutputsBlock::writeDac(int ch, float volts) {   // ch 0 = AO1, 1 = AO2
  volts = constrain(volts, -10.0f, 10.0f);
#ifdef SIM
  (void)ch;
#else
  // Every DAC frame goes out under the SPI lock; if the NMR capture holds the bus
  // this update is skipped and the next loop() pass catches up.
  spibus::Guard g(0);
  if (!g.ok) return;
  // The OPA2192 stage (10 k / 40.2 k, referenced to the DAC's own 2.5 V) gives
  // AO = 4.02 * (V_DAC - 2.5 V), and V_DAC = 5 V * code / 65536, so
  // AO = 10.05 V * (code - 32768) / 32768.
  long code = lroundf(32768.0f + volts * 32768.0f / 10.05f);
  code = constrain(code, 0L, 65535L);
  dacFrame(static_cast<uint8_t>(0x18 | ch), static_cast<uint16_t>(code));   // C = 011: write and update DAC ch
#endif
}

bool OutputsBlock::handle(JsonObjectConst cmd, JsonObject reply) {
  const char* c = cmd["cmd"] | "";
  JsonObjectConst a = argsOf(cmd);
  int ch = a["ch"] | 1;
  if (ch < 1 || ch > 2) {
    reply["error"] = "ch must be 1 or 2";
    return false;
  }
  Channel& x = ch_[ch - 1];

  if (strcmp(c, "set_dc") == 0) {          // {"ch":1,"volts":2.5}
    x.dc = constrain(a["volts"] | 0.0f, -10.0f, 10.0f);
    x.mode = DC;
  } else if (strcmp(c, "sine") == 0) {     // {"ch":1,"freq":10,"amp":5,"offset":0}
    x.freq = constrain(a["freq"] | 1.0f, 0.01f, 50000.0f);
    x.amp = constrain(a["amp"] | 1.0f, 0.0f, 10.0f);
    x.offset = constrain(a["offset"] | 0.0f, -10.0f, 10.0f);
    x.mode = SINE;
  } else if (strcmp(c, "off") == 0) {
    x.mode = OFF;
  } else {
    reply["error"] = "unknown cmd";
    return false;
  }
  reply["ch"] = ch;
  reply["mode"] = modeName(x.mode);
  return true;
}

void OutputsBlock::status(JsonObject out) {
  out["ao1"] = ch_[0].volts;
  out["ao2"] = ch_[1].volts;
  out["mode1"] = modeName(ch_[0].mode);
  out["mode2"] = modeName(ch_[1].mode);
}
