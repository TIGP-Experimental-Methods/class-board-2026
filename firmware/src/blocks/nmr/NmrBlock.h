// nmr - the pulsed NMR console. NMR-FIRMWARE.md section 3, PROTOCOL.md section 7.
//
// What the experiment is: protons in water sit in a small static field (about
// 2.1 mT here, so they precess at about 89.4 kHz). A short burst at that
// frequency tips them over; when it stops they precess freely and induce a
// signal of a few microvolts in the coil, which decays away in a fraction of a
// second. The receiver mixes that against a local oscillator at f_lo, so what
// comes out is a complex signal at the difference frequency (about 5.4 kHz)
// which the ADS8688 samples on channels 7 (I) and 8 (Q). Repeat, average, and
// the line appears out of the noise.
//
// This block is the thin part: it validates commands, keeps the settings, and
// hands the record to the WebSocket. The interesting parts are next door -
// Sequencer (the pulse programmer, on its own task) and Dsp (the arithmetic).
//
// Commands: config, start, abort, pulse, clock, dds, blank, get_record,
//           sim_larmor (simulation build only)
// Status:   state, scan, n_avg, f_tx_hz, f_lo_hz, if_hz, rate_hz, peak_hz,
//           larmor_hz, peak_amp, snr_db, i_flag, t_flag, error, sim
//
// While a scan set runs the block owns TX_EN, RX_BLANK, DDS_PSEL and - if the
// scan polarizes - FET_GATE and HB_IN1/2. b4 refuses to touch those two for the
// duration (blocks/Busy.h).
#pragma once
#include "../Block.h"
#include "Sequencer.h"

class NmrBlock : public Block {
 public:
  const char* name() const override { return "nmr"; }
  void begin() override;
  void loop() override;
  bool handle(JsonObjectConst cmd, JsonObject reply) override;
  void status(JsonObject out) override;

 private:
  void fillSettings(JsonObject out) const;

  Sequencer seq_;
};
