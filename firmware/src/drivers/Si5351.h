// Si5351 - Si5351A-B-GT clock generator, U701 on the NMR RX sheet, I2C 0x60,
// 25 MHz crystal Y701. NMR-FIRMWARE.md section 2.3.
//
// It makes the two clocks the console needs:
//   CLK0  50.000 MHz, the AD9834 master clock (must be exact: every transmitter
//         frequency is a fraction of it). Integer PLLA: 25 MHz x 36 = 900 MHz,
//         output multisynth 18. Integer mode all the way = lowest spurs.
//   CLK1  4 x f_LO into the 74HC74 Johnson counter, which divides by four and
//         gives I and Q exactly 90 degrees apart. Fractional PLLB, because f_LO
//         has to follow the Larmor line and is nowhere near a nice divisor.
//   CLK2  unused, on a test point.
//
// Register map (Skyworks AN619, "Manually Generating an Si5351 Register Map"):
//   0     device status, bit 7 SYS_INIT
//   3     output enable control, bit n = 1 disables CLKn
//   16-18 CLK0..CLK2 control: [7] PDN, [6] MSn_INT, [5] MSn_SRC (0 PLLA, 1 PLLB),
//         [4] INV, [3:2] CLK source (11 = multisynth n), [1:0] drive (11 = 8 mA)
//   26-33 Multisynth NA = the PLLA feedback divider
//   34-41 Multisynth NB = the PLLB feedback divider
//   42-49 Multisynth 0 = the CLK0 output divider
//   50-57 Multisynth 1 = the CLK1 output divider
//   177   PLL reset, bit 7 PLLB_RST, bit 5 PLLA_RST
//   183   crystal internal load capacitance, bits [7:6] (11 = 10 pF); bits [5:0]
//         must be written back as 010010
//
// Every divider, feedback or output, is written as a + b/c encoded into three
// parameters (AN619 section 3.2):
//   P1 = 128a + floor(128b/c) - 512,  P2 = 128b - c*floor(128b/c),  P3 = c
//
// On a bare dev board nothing acknowledges at 0x60: present() stays false and
// every call is a quiet no-op that still remembers what was asked for.
#pragma once
#include <stdint.h>

class Si5351 {
 public:
  bool begin(uint8_t addr = 0x60, uint32_t xtal_hz = 25000000);

  bool setClk0(uint32_t hz);      // PLLA, integer where the arithmetic allows it
  bool setClk1(double hz);        // PLLB, fractional
  double actualClk1() const { return clk1Actual_; }
  double actualClk0() const { return clk0Actual_; }

  bool enable(uint8_t clk, bool on);
  bool resetPllB();               // register 177 bit 7; call after any CLK1 change
  bool present() const { return present_; }

 private:
  struct Divider {                // a + b/c, already reduced to the three parameters
    uint32_t p1, p2, p3;
    bool integer;
  };

  static Divider encode(uint32_t a, uint32_t b, uint32_t c);
  bool writeDivider(uint8_t baseReg, const Divider& d, uint8_t rDivExp);
  bool write8(uint8_t reg, uint8_t value);

  uint8_t addr_ = 0x60;
  uint32_t xtal_ = 25000000;
  bool present_ = false;
  uint8_t oeb_ = 0xFF;            // register 3 cache: 1 = output disabled
  double clk0Actual_ = 0;
  double clk1Actual_ = 0;
};

extern Si5351 clockgen;

namespace si5351 {
// Pulse the Johnson counter's /CLR through the expander (P1.4 low, then high) so
// the quadrature divider always restarts in state 00. Same call as
// Tca9535::pulseJohnsonClear(); it lives here too because the sequence that
// needs it is setClk1 -> resetPllB -> clear, and that reads better in one place.
bool pulseJohnsonClear();
}  // namespace si5351
