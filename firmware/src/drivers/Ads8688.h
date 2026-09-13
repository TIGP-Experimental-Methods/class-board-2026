// Ads8688 - 8-channel 16-bit SAR ADC, 500 kS/s aggregate, U101 on the B1 sheet.
// NMR-FIRMWARE.md section 2.5. Datasheet section 8.5 (command and program registers).
//
// Two ways to talk to it, both over 32-bit SPI frames (command in the first 16
// bits, the conversion result in the second 16):
//
//   Manual mode  - send MAN_CH_n, the answer for channel n comes back in the
//                  next frame. This is what the b1 status panel uses: eight
//                  channels, twenty times a second, nothing critical.
//   Auto-scan    - program AUTO_SEQ_EN with a channel mask, send AUTO_RST once,
//                  then every following frame returns the next channel in the
//                  mask, wrapping round. This is what the NMR capture uses,
//                  because there is no per-sample command to send.
//
// Commands (datasheet table "Command Register Map"):
//   NO_OP     0x0000     AUTO_RST  0xA000     RST      0x8500
//   STDBY     0x8200     PWR_DN    0x8300     MAN_AUX  0xE000
//   MAN_CH_n  0xC000 + n * 0x0400
// Program register write: one 16-bit word (address << 9) | (1 << 8) | data,
// then eight more clocks in which the part echoes the byte it stored.
//   0x01  AUTO_SEQ_EN   bit n enables channel n in the auto scan
//   0x02  Channel power down
//   0x05 + n  Range for channel n
//
// Range codes, with the internal 4.096 V reference:
//   0 = +-10.24 V   1 = +-5.12 V   2 = +-2.56 V   5 = 0..10.24 V   6 = 0..5.12 V
// The device always answers in straight binary. readManual() converts that to a
// signed code by flipping the top bit, so a bipolar reading is centred on zero
// and a unipolar reading of 0 V comes back as -32768; toVolts() undoes it either
// way. Keeping one signed type everywhere is what lets the NMR capture buffer be
// a plain int16_t array.
//
// SPI: mode 1 (CPOL 0, CPHA 1), MSB first, 17 MHz. The datasheet allows 17 MHz
// with the internal reference, which is the limit that matters here.
#pragma once
#include <stdint.h>

class Ads8688 {
 public:
  void begin();

  bool setRange(uint8_t ch, uint8_t code);   // ch 0..7
  uint8_t range(uint8_t ch) const { return ch < 8 ? range_[ch] : 0; }

  int16_t readManual(uint8_t ch);
  float toVolts(uint8_t ch, int16_t raw) const;

  // Auto-scan burst over the channels in `mask` (bit n = channel n). Fills `out`
  // interleaved in ascending channel order, n_per_channel scans of it. Paced with
  // esp_timer_get_time() to rate_hz scans per second; if the loop cannot keep up
  // it free-runs and reports what it managed in *achieved_hz. Returns the number
  // of scans actually written (n_per_channel unless the arguments were bad).
  //
  // The caller holds the SPI lock for the whole burst.
  uint32_t burst(uint8_t mask, int16_t* out, uint32_t n_per_channel,
                 uint32_t rate_hz, uint32_t* achieved_hz);

  bool present() const { return present_; }

 private:
  bool programWrite(uint8_t addr, uint8_t data);

  // Reset value of the range registers is 0 (+-10.24 V). Channels 7 and 8 carry
  // the NMR I and Q baseband, which the receiver scales to fit +-5.12 V.
  uint8_t range_[8] = {0, 0, 0, 0, 0, 0, 1, 1};
  bool present_ = false;
};

extern Ads8688 adc;
