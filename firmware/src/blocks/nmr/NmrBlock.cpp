#include "NmrBlock.h"

#include <math.h>
#include <string.h>

#include "../../../include/pins.h"
#include "../../drivers/Ad9834.h"
#include "../../drivers/Si5351.h"
#include "../../drivers/Tca9535.h"
#include "../../net/WsOut.h"

namespace {

const char* stateName(Sequencer::State s) {
  switch (s) {
    case Sequencer::kRunning: return "running";
    case Sequencer::kDone: return "done";
    case Sequencer::kError: return "error";
    default: return "idle";
  }
}

// `config` takes any subset of the settings, so each field is only touched when
// the client actually sent it. A missing key and a key set to null both mean
// "leave this one alone".
void take(JsonObjectConst a, const char* key, uint32_t& v) {
  if (!a[key].isNull()) v = a[key].as<uint32_t>();
}
void take(JsonObjectConst a, const char* key, double& v) {
  if (!a[key].isNull()) v = a[key].as<double>();
}
void take(JsonObjectConst a, const char* key, bool& v) {
  if (!a[key].isNull()) v = a[key].as<bool>();
}

}  // namespace

void NmrBlock::begin() {
#ifndef SIM
  // Safe idle levels first, then the pins become outputs: a pin that is made an
  // output before its level is set glitches to whatever the register held, and
  // one of these pins turns on a transmitter and another lets a coil current
  // through a FET.
  digitalWrite(PIN_TX_EN, LOW);        // transmitter gate closed
  digitalWrite(PIN_RX_BLANK, LOW);     // receiver blanked (the reset state too)
  digitalWrite(PIN_FET_GATE, LOW);     // polarizer off
  digitalWrite(PIN_HB_IN1, LOW);       // H-bridge coasting
  digitalWrite(PIN_HB_IN2, LOW);
  pinMode(PIN_TX_EN, OUTPUT);
  pinMode(PIN_RX_BLANK, OUTPUT);
  pinMode(PIN_FET_GATE, OUTPUT);
  pinMode(PIN_HB_IN1, OUTPUT);
  pinMode(PIN_HB_IN2, OUTPUT);
  // The transmitter flags (rework A2). Unwired, the pull-down reads "no flag".
  pinMode(PIN_TX_IFLAG, INPUT_PULLDOWN);
  pinMode(PIN_TX_TFLAG, INPUT_PULLDOWN);
#endif

  // The DDS master clock has to exist before the DDS is worth talking to; then
  // the default frequencies, so status reports the lattice values from the start.
  clockgen.setClk0(50000000);
  dds.begin(50000000);                 // PHASE0 selected, RESET bit set
  seq_.programClocks();

  seq_.idleHardware();                 // blanked, gate off, carrier asleep
  seq_.begin();                        // buffers and the sequencer task
}

void NmrBlock::loop() {
  // The sequencer cannot touch the network, so this is where a finished record
  // goes out. One frame per pass at most; if the socket is busy it waits for
  // the next one.
  seq_.consumeRecord(&wsBinaryAll);
}

void NmrBlock::fillSettings(JsonObject out) const {
  const NmrConfig& c = seq_.config();
  out["f_tx_hz"] = c.f_tx_hz;
  out["f_lo_hz"] = c.f_lo_hz;
  out["sequence"] = c.echo ? "echo" : "fid";
  out["t90_us"] = c.t90_us;
  out["t180_us"] = c.t180_us;
  out["tau_us"] = c.tau_us;
  out["t_blank_pre_us"] = c.t_blank_pre_us;
  out["t_dead_us"] = c.t_dead_us;
  out["t_acq_start_us"] = c.t_acq_start_us;
  out["t_acq_ms"] = c.t_acq_ms;
  out["rate_hz"] = c.rate_hz;
  out["decim"] = c.decim;
  out["n_avg"] = c.n_avg;
  out["cyclops"] = c.cyclops;
  out["t_repeat_ms"] = c.t_repeat_ms;
  out["polarize_ms"] = c.polarize_ms;
  out["t_polarize_settle_ms"] = c.t_polarize_settle_ms;
  out["hb_mode"] = c.hb_mode == 1 ? "fwd" : (c.hb_mode == 2 ? "rev" : "off");
  out["ref_ch"] = c.ref_ch;
  out["if_hz"] = seq_.ifHz();
  out["n"] = seq_.recordSamples();
  out["record_rate_hz"] = seq_.recordRate();
}

bool NmrBlock::handle(JsonObjectConst cmd, JsonObject reply) {
  const char* c = cmd["cmd"] | "";
  JsonObjectConst a = argsOf(cmd);
  const char* err = "";

  if (strcmp(c, "config") == 0) {
    NmrConfig want = seq_.config();
    take(a, "f_tx_hz", want.f_tx_hz);
    take(a, "f_lo_hz", want.f_lo_hz);
    take(a, "t90_us", want.t90_us);
    take(a, "t180_us", want.t180_us);
    take(a, "tau_us", want.tau_us);
    take(a, "t_blank_pre_us", want.t_blank_pre_us);
    take(a, "t_dead_us", want.t_dead_us);
    take(a, "t_acq_start_us", want.t_acq_start_us);
    take(a, "t_acq_ms", want.t_acq_ms);
    take(a, "rate_hz", want.rate_hz);
    take(a, "decim", want.decim);
    take(a, "n_avg", want.n_avg);
    take(a, "cyclops", want.cyclops);
    take(a, "t_repeat_ms", want.t_repeat_ms);
    take(a, "polarize_ms", want.polarize_ms);
    take(a, "t_polarize_settle_ms", want.t_polarize_settle_ms);
    if (!a["ref_ch"].isNull()) {
      // Read as a signed number: as<uint32_t>() would turn -1 into 0 = "none".
      const long r = a["ref_ch"].as<long>();
      if (r < 0 || r > 8) { reply["error"] = "ref_ch must be 0 (none) or 1..6"; return false; }
      want.ref_ch = static_cast<uint8_t>(r);
    }
    if (!a["sequence"].isNull()) {
      const char* s = a["sequence"] | "";
      if (strcmp(s, "fid") == 0) want.echo = false;
      else if (strcmp(s, "echo") == 0) want.echo = true;
      else { reply["error"] = "sequence must be fid or echo"; return false; }
    }
    if (!a["hb_mode"].isNull()) {
      const char* m = a["hb_mode"] | "";
      if (strcmp(m, "off") == 0) want.hb_mode = 0;
      else if (strcmp(m, "fwd") == 0) want.hb_mode = 1;
      else if (strcmp(m, "rev") == 0) want.hb_mode = 2;
      else { reply["error"] = "hb_mode must be off, fwd or rev"; return false; }
    }
    const NmrConfig before = seq_.config();
    if (!seq_.applyConfig(want, &err)) { reply["error"] = err; return false; }

    // Program the frequencies now, so the reply can say what the hardware will
    // really do rather than what was asked for: f_lo snapped to the lattice, the
    // exact IF, CLK2's divider. The carrier stays asleep and CLK2 off; only the
    // registers are loaded. If CLK2 cannot be set, the old settings come back,
    // so a refused config changes nothing.
    if (!seq_.programClocks()) {
      seq_.applyConfig(before, &err);
      seq_.programClocks();
      reply["error"] = "CLK2 could not be set to the IF - check the Si5351";
      return false;
    }

    fillSettings(reply);
    reply["f_tx_actual_hz"] = dds.actualFrequency();
    reply["f_lo_actual_hz"] = seq_.loActualHz();
    if (seq_.config().ref_ch) reply["clk2_actual_hz"] = clockgen.actualClk2();
    return true;
  }

  if (strcmp(c, "start") == 0) {
    if (!seq_.start(&err)) { reply["error"] = err; return false; }
    reply["state"] = "running";
    reply["n_avg"] = seq_.config().n_avg;
    return true;
  }

  if (strcmp(c, "abort") == 0) {
    seq_.abortScanSet();
    reply["state"] = "idle";
    return true;
  }

  if (strcmp(c, "pulse") == 0) {          // {"t_us":417}
    if (seq_.running()) { reply["error"] = "scan running"; return false; }
    const uint32_t t_us = a["t_us"] | 0u;
    if (t_us < 1 || t_us > 5000) { reply["error"] = "t_us must be 1..5000"; return false; }
    if (const char* p = seq_.supplyProblem()) { reply["error"] = p; return false; }
    // A single gate with the carrier running, for a scope on the coil.
    seq_.prepareHardware();
    seq_.pulseOnce(t_us);
    seq_.idleHardware();
    reply["t_us"] = t_us;
    reply["i_flag"] = seq_.iFlag();
    reply["t_flag"] = seq_.tFlag();
    return true;
  }

  if (strcmp(c, "clock") == 0) {          // {"clk":0|1,"hz":50000000}
    if (seq_.running()) { reply["error"] = "scan running"; return false; }
    const int clk = a["clk"] | -1;
    const double hz = a["hz"] | 0.0;
    if (clk != 0 && clk != 1) { reply["error"] = "clk must be 0 or 1"; return false; }
    if (hz < 2500.0 || hz > 200000000.0) { reply["error"] = "hz must be 2500..200000000"; return false; }
    // CLK0 is the DDS master clock; the fitted AD9834BRUZ is a 50 MHz part.
    if (clk == 0 && hz > 50e6) { reply["error"] = "CLK0 above 50 MHz (AD9834BRUZ limit)"; return false; }
    // A bench clock breaks the lattice: the reference is invalid until the next
    // config or scan set reprograms everything, so it is switched off now.
    clockgen.setClk2Exact(0);
    if (clk == 0) {
      // CLK0 is the DDS master clock: the driver's frequency arithmetic follows it.
      if (clockgen.setClk0(static_cast<uint32_t>(hz))) dds.setMclk(static_cast<uint32_t>(lround(clockgen.actualClk0())));
      reply["hz_actual"] = clockgen.actualClk0();
    } else {
      clockgen.setClk1(hz);
      clockgen.resetPllB();
      expander.pulseJohnsonClear();     // the quadrature divider restarts at 00
      reply["hz_actual"] = clockgen.actualClk1();
    }
    reply["clk"] = clk;
    return true;
  }

  if (strcmp(c, "dds") == 0) {            // {"hz":89400,"phase0_deg":0,"phase1_deg":180,"psel":false,"on":true}
    if (seq_.running()) { reply["error"] = "scan running"; return false; }
    if (!a["hz"].isNull()) {
      const double hz = a["hz"].as<double>();
      if (hz < 0.0 || hz > 25000000.0) { reply["error"] = "hz must be 0..25000000"; return false; }
      dds.setFrequency(hz);
      clockgen.setClk2Exact(0);           // off the lattice: no reference until the next config
    }
    if (!a["phase0_deg"].isNull()) dds.setPhase(0, a["phase0_deg"].as<double>());
    if (!a["phase1_deg"].isNull()) dds.setPhase(1, a["phase1_deg"].as<double>());
    if (!a["psel"].isNull()) dds.selectPhase(a["psel"].as<bool>());
    // The carrier is asleep when the console is idle; a bench test usually wants
    // it running, so "on" (default true) wakes it and takes it out of reset.
    const bool on = a["on"] | true;
    dds.sleep(!on);
    dds.setReset(!on);
    reply["hz"] = dds.actualFrequency();
    reply["phase0_deg"] = dds.actualPhase(0);
    reply["phase1_deg"] = dds.actualPhase(1);
    reply["psel"] = dds.phaseSelected();
    reply["on"] = on;
    return true;
  }

  if (strcmp(c, "blank") == 0) {          // {"receive":true}
    if (seq_.running()) { reply["error"] = "scan running"; return false; }
    const bool receive = a["receive"] | false;
    seq_.setBlank(receive);
    reply["receive"] = receive;
    return true;
  }

  if (strcmp(c, "get_record") == 0) {
    if (!seq_.resendRecord(&wsBinaryAll)) { reply["error"] = "no record yet"; return false; }
    reply["n"] = seq_.recordSamples();
    reply["rate_hz"] = seq_.recordRate();
    reply["scan"] = seq_.scansDone();
    return true;
  }

  if (strcmp(c, "sim_larmor") == 0) {     // {"hz":89400}
#ifdef SIM
    const double hz = a["hz"] | 0.0;
    if (hz < 1000.0 || hz > 1000000.0) { reply["error"] = "hz must be 1000..1000000"; return false; }
    if (seq_.running()) { reply["error"] = "scan running"; return false; }
    seq_.setSimLarmor(hz);
    reply["hz"] = hz;
    return true;
#else
    reply["error"] = "simulation build only";
    return false;
#endif
  }

  reply["error"] = "unknown cmd";
  return false;
}

void NmrBlock::status(JsonObject out) {
  const NmrConfig& c = seq_.config();
  out["state"] = stateName(seq_.state());
  out["scan"] = seq_.scansDone();
  out["n_avg"] = c.n_avg;
  out["f_tx_hz"] = c.f_tx_hz;
  out["f_lo_hz"] = c.f_lo_hz;
  out["if_hz"] = seq_.ifHz();
  // The rate the converter really managed, once it has been asked to manage it.
  out["rate_hz"] = seq_.achievedRate() ? seq_.achievedRate() : c.rate_hz;

  if (seq_.scansDone() > 0) {
    const dsp::Spectrum& s = seq_.spectrum();
    out["peak_hz"] = s.peak_hz;
    out["larmor_hz"] = seq_.loActualHz() + static_cast<double>(s.peak_hz);
    out["peak_amp"] = s.peak_amp;
    out["snr_db"] = s.snr_db;
  }

  out["ref_ch"] = c.ref_ch;
  if (c.ref_ch && seq_.refMeasured()) {
    out["ref_phase_deg"] = seq_.refPhaseDeg();
    out["ref_amp"] = seq_.refAmp();
  }

  // The transmitter's current-limit and thermal flags on GPIO6 / GPIO7 (rework
  // A2). Without the rework the pull-downs make them read false.
  out["i_flag"] = seq_.iFlag();
  out["t_flag"] = seq_.tFlag();
  out["tx_clip_warning"] = Sequencer::txClipWarning();

  if (seq_.state() == Sequencer::kError && seq_.error()[0]) out["error"] = seq_.error();
#ifdef SIM
  out["sim"] = true;
#else
  out["sim"] = false;
#endif
}

