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

// What the local oscillator really is: the Si5351 makes 4 x f_lo and the
// Johnson counter divides it by four. If there is no clock generator on the bus
// (a bare dev board) the driver reports nothing and we fall back to the request.
double actualLo(double asked) {
  const double clk1 = clockgen.actualClk1();
  return clk1 > 0.0 ? clk1 / 4.0 : asked;
}

double actualTx(double asked) {
  const double f = dds.actualFrequency();
  return f > 0.0 ? f : asked;
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
#endif

  // The DDS master clock has to exist before the DDS is worth talking to.
  clockgen.setClk0(50000000);
  dds.begin(50000000);                 // also sets PIN_DDS_PSEL low (PHASE0)

  // If the flags ever get bodged onto the spare expander lines, those two lines
  // have to become inputs; with EXP_BIT_IFLAG at -1 this does nothing at all.
  if (Sequencer::flagsConnected()) {
    uint8_t mask = 0;
    if (EXP_BIT_IFLAG >= 0) mask |= static_cast<uint8_t>(1u << (EXP_BIT_IFLAG & 7));
    if (EXP_BIT_TFLAG >= 0) mask |= static_cast<uint8_t>(1u << (EXP_BIT_TFLAG & 7));
    expander.setInputs(EXP_PORT_CTRL, mask);
  }

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
  out["if_hz"] = c.f_tx_hz - c.f_lo_hz;
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
    if (!seq_.applyConfig(want, &err)) { reply["error"] = err; return false; }

    // Program the two frequencies now, so the reply can say what the hardware
    // will really do rather than what was asked for. The carrier stays asleep;
    // only the registers are loaded.
    const NmrConfig& eff = seq_.config();
    clockgen.setClk1(4.0 * eff.f_lo_hz);
    clockgen.resetPllB();
    expander.pulseJohnsonClear();
    dds.setFrequency(eff.f_tx_hz);

    fillSettings(reply);
    reply["f_tx_actual_hz"] = actualTx(eff.f_tx_hz);
    reply["f_lo_actual_hz"] = actualLo(eff.f_lo_hz);
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
    // A single gate with the carrier running, for a scope on the coil.
    seq_.prepareHardware();
    seq_.pulseOnce(t_us);
    seq_.idleHardware();
    reply["t_us"] = t_us;
    return true;
  }

  if (strcmp(c, "clock") == 0) {          // {"clk":0|1,"hz":50000000}
    if (seq_.running()) { reply["error"] = "scan running"; return false; }
    const int clk = a["clk"] | -1;
    const double hz = a["hz"] | 0.0;
    if (clk != 0 && clk != 1) { reply["error"] = "clk must be 0 or 1"; return false; }
    if (hz < 2500.0 || hz > 200000000.0) { reply["error"] = "hz must be 2500..200000000"; return false; }
    if (clk == 0) {
      clockgen.setClk0(static_cast<uint32_t>(hz));
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
  out["if_hz"] = c.f_tx_hz - c.f_lo_hz;
  // The rate the converter really managed, once it has been asked to manage it.
  out["rate_hz"] = seq_.achievedRate() ? seq_.achievedRate() : c.rate_hz;

  if (seq_.scansDone() > 0) {
    const dsp::Spectrum& s = seq_.spectrum();
    out["peak_hz"] = s.peak_hz;
    out["larmor_hz"] = c.f_lo_hz + static_cast<double>(s.peak_hz);
    out["peak_amp"] = s.peak_amp;
    out["snr_db"] = s.snr_db;
  }

  // v0.7 brings the transmitter's current-limit and thermal flags to test
  // points only, so there is nothing to read: null says "not connected", which
  // is not the same answer as false.
  if (Sequencer::flagsConnected()) {
    out["i_flag"] = seq_.iFlag();
    out["t_flag"] = seq_.tFlag();
  } else {
    out["i_flag"] = nullptr;
    out["t_flag"] = nullptr;
  }

  if (seq_.state() == Sequencer::kError && seq_.error()[0]) out["error"] = seq_.error();
#ifdef SIM
  out["sim"] = true;
#else
  out["sim"] = false;
#endif
}

