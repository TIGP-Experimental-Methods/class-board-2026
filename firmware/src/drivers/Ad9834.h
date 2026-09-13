// Ad9834 - 75 MHz DDS, U801 on the NMR TX sheet. NMR-FIRMWARE.md section 2.4.
//
// It makes the transmitter carrier. The carrier free-runs the whole time: what
// turns the pulse on and off is TX_EN into the OPA564 enable pin, not the DDS.
// Gating the DDS instead would restart its phase accumulator and throw away the
// phase reference the receiver is measuring against, which is the whole point of
// a coherent spectrometer.
//
// Interface (AD9834 datasheet, "Programming the AD9834"): a write-only three-wire
// port. FSYNC low frames one 16-bit word, MSB first, clocked in on the falling
// edge of SCLK - that is SPI mode 2 (CPOL 1, CPHA 0). The part takes 40 MHz; we
// use 10 MHz because nothing here is in a hurry and the traces are long.
//
// The top two bits of every word say where it goes:
//   00  control register
//   01  FREQ0     10  FREQ1     11 x  PHASE0 (110) / PHASE1 (111)
//
// Control-register bits: B28 (13), HLB (12), FSEL (11), PSEL (10), PIN/SW (9),
// RESET (8), SLEEP1 (7), SLEEP12 (6), OPBITEN (5), SIGN/PIB (4), DIV2 (3), MODE (1).
// We keep B28 = 1 (a frequency word is two consecutive 14-bit writes) and
// PIN/SW = 1 (FSELECT and PSELECT come from the pins, so the sequencer can flip
// the pulse phase with one GPIO write instead of an SPI frame).
//
// Frequency resolution: delta f = MCLK / 2^28 = 50 MHz / 2^28 = 0.186 Hz, which
// at an 89.4 kHz Larmor frequency is about 2 ppm - far finer than the line width.
#pragma once
#include <stdint.h>

class Ad9834 {
 public:
  void begin(uint32_t mclk_hz = 50000000);

  void setFrequency(double hz);
  double actualFrequency() const { return actual_; }

  void setPhase(uint8_t reg, double deg);    // reg 0 = PHASE0, 1 = PHASE1; 12-bit
  double actualPhase(uint8_t reg) const { return reg < 2 ? phaseDeg_[reg] : 0.0; }

  void setReset(bool on);                    // 1 = output parked at midscale
  void selectPhase(bool p1);                 // drives PIN_DDS_PSEL
  bool phaseSelected() const { return psel_; }
  void sleep(bool on);                       // SLEEP1 + SLEEP12: stop the output

 private:
  void writeWord(uint16_t word);
  void writeControl();

  uint32_t mclk_ = 50000000;
  uint32_t freqWord_ = 0;
  double actual_ = 0;
  double phaseDeg_[2] = {0, 0};
  bool psel_ = false;
  bool reset_ = true;
  bool sleep_ = false;
};

extern Ad9834 dds;
