// Sequencer - the pulse programmer. NMR-FIRMWARE.md section 3.2.
//
// One scan is: (optionally polarize) - blank the receiver - open the transmit
// gate for the pulse - wait out the dead time while the coil rings down -
// unblank - sample I and Q for a while - blank again - work out the answer -
// wait for the spins to relax - do it again with the next phase of the cycle.
//
// Why a task of its own, pinned to core 1, above the Arduino loop task:
//   * The timing has to hold to a microsecond or two through a pulse that lasts
//     a few hundred. Block code shares the main task with the web server, the
//     status broadcast and OTA; any of those can take milliseconds.
//   * Core 0 is where WiFi and lwIP live. Core 1 runs the Arduino loop task at
//     priority 1, so at priority 5 on core 1 nothing here gets preempted except
//     by interrupts, and the radio keeps running on the other core.
// Interrupts stay enabled throughout. A microsecond of jitter is about two
// degrees at the intermediate frequency, which averaging removes; disabling
// interrupts for seconds at a time would take the WiFi link down with it.
//
// The scans themselves start at arbitrary points of the IF cycle (the waits
// between them run on the ESP32's clock, not the Si5351's), so each record
// starts with its own IF phase. With a phase reference (ref_ch, NMR-FIRMWARE.md
// section 3.9) the sequencer measures that phase from the CLK2 tone recorded
// alongside I and Q and rotates the record back before averaging.
//
// The task never touches the network. When a scan is averaged in, it fills the
// outgoing frame, sets a flag, and the main task sends it from loop().
#pragma once
#include <stddef.h>
#include <stdint.h>

#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <freertos/task.h>

#include "Dsp.h"

// Everything `config` can set. The defaults are the water-at-2.1-mT demo:
// a 89.4 kHz line, an 84 kHz local oscillator, so a 5.4 kHz intermediate
// frequency, a 417 us pulse and a two-second record.
struct NmrConfig {
  double f_tx_hz = 89400.0;
  double f_lo_hz = 84000.0;
  bool echo = false;              // false = free induction decay, true = spin echo
  uint32_t t90_us = 417;
  uint32_t t180_us = 834;
  uint32_t tau_us = 20000;        // echo only: pulse to pulse
  uint32_t t_blank_pre_us = 20;   // receiver blanked this long before the gate opens
  uint32_t t_dead_us = 1000;      // gate closed -> receiver unblanked
  uint32_t t_acq_start_us = 1200; // gate closed -> first sample
  uint32_t t_acq_ms = 2000;       // record length
  uint32_t rate_hz = 100000;      // per channel, before decimation
  uint32_t decim = 4;             // boxcar; the record goes out at rate_hz / decim
  uint32_t n_avg = 1;             // scans in the set
  bool cyclops = true;            // step the pulse phase 0/90/180/270 and rotate back
  uint32_t t_repeat_ms = 3000;    // between scans; at least 3 x T1
  uint32_t polarize_ms = 0;       // Earth's-field option: prepolarizing coil on
  uint32_t t_polarize_settle_ms = 15;  // >= 5 time constants of the reference coil's freewheel decay (tau ~ 2.6 ms)
  uint8_t hb_mode = 0;            // 0 off, 1 forward, 2 reverse (during polarize)
  // The panel input carrying Si5351 CLK2, 0 = none. 1 by default in both builds:
  // the rework (A1) is fitted on every board (Decision #85). A board without the
  // wire fails its first scan set with "reference tone missing on AI1" and the
  // user sends ref_ch 0. An IF under 3.44 kHz (Earth's field) needs ref_ch 0 too.
  uint8_t ref_ch = 1;
  double sim_larmor_hz = 89400.0; // simulation build only
};

class Sequencer {
 public:
  enum State : uint8_t { kIdle = 0, kRunning, kDone, kError };

  // How a finished record leaves this class: the main task hands in the
  // function that puts bytes on the wire.
  typedef void (*Sink)(const uint8_t* data, size_t len);

  bool begin();

  // Validate, and reserve the memory the record needs. On failure nothing
  // changes and *err points at a fixed string for the reply. Refused while a
  // scan set is running.
  bool applyConfig(const NmrConfig& want, const char** err);
  const NmrConfig& config() const { return cfg_; }
  void setSimLarmor(double hz) { cfg_.sim_larmor_hz = hz; }

  bool start(const char** err);
  void abortScanSet();

  State state() const { return static_cast<State>(state_); }
  bool running() const { return state_ == kRunning; }
  uint32_t scansDone() const { return scan_; }
  uint32_t achievedRate() const { return achieved_hz_; }
  uint32_t recordSamples() const { return nDec_; }
  // The sample rate the burst really paces (whole microseconds per frame), and
  // the decimated rate of the record: what the time and frequency axes use.
  double sampleRate() const;
  double recordRate() const { return sampleRate() / (cfg_.decim ? cfg_.decim : 1); }
  // The frequencies as programmed, read back from the drivers: after `config`
  // or a scan set they sit on the lattice of section 3.9 (carrier W x step, LO
  // V x step, IF exactly (W - V) x step); after a bench `clock` or `dds`
  // command they say what that command set.
  double loActualHz() const;
  double ifHz() const;
  const dsp::Spectrum& spectrum() const { return spec_; }
  const char* error() const { return error_; }
  bool iFlag() const { return iFlag_; }
  bool tFlag() const { return tFlag_; }
  bool refMeasured() const { return refMeasured_; }
  float refPhaseDeg() const { return refPhaseDeg_; }
  float refAmp() const { return refAmp_; }

  // +VEXT against the transmitter's limits (blocks/Vext.h). supplyProblem() is
  // nullptr when a pulse may go out, else the reason (in a buffer of its own:
  // the status error of the last scan set stays as it was); txClipWarning()
  // says the gain-25 output would clip at this supply.
  const char* supplyProblem();
  static bool txClipWarning();

  // Main task only. consumeRecord sends the frame if a new one is waiting;
  // resendRecord sends whatever the last one was (the `get_record` command).
  bool consumeRecord(Sink sink);
  bool resendRecord(Sink sink);

  // Manual bench controls, all refused while a scan set is running.
  void setBlank(bool receive);
  void pulseOnce(uint32_t t_us);
  bool programClocks();            // CLK0, the carrier word, the LO, CLK2's divider; false if CLK2 failed
  bool prepareHardware();          // program the clocks, the DDS, wake it up, CLK2 on; programClocks()'s answer
  void idleHardware();             // blanked, gate off, polarizer off, DDS asleep, CLK2 off

 private:
  static void trampoline(void* arg);
  void taskLoop();
  void runScanSet();
  bool runOneScan(uint32_t index, float phaseDeg);
  bool measureReference(uint32_t index);
  void processScan(uint32_t index, float phaseDeg);
  bool ensureBuffers(uint32_t nRawTotal, uint32_t nDec, const char** err);
  bool waitMs(uint32_t ms);        // false if the set was aborted while waiting
  int64_t gate(uint32_t t_us);     // one transmit gate, flags sampled at its end; returns the end time
  void readFlags();                // ORs the flag pins into iFlag_ / tFlag_
  bool flagFailed();               // fail() on a set flag
  void publish(uint32_t scansAveraged);
  void note(const char* message);   // remember a message, stay in the state we are in
  void fail(const char* message);   // remember it and stop the scan set
#ifdef SIM
  void simBurst(uint32_t nRaw, float phaseDeg, uint32_t index);
#endif

  NmrConfig cfg_;

  TaskHandle_t task_ = nullptr;
  SemaphoreHandle_t frameLock_ = nullptr;

  // PSRAM. raw_ is the interleaved capture in ADC codes; frame_ is the
  // outgoing binary frame, whose payload doubles as the running-mean
  // accumulator, so the averaged record is never copied; fftRe_/fftIm_ are the
  // scratch the spectrum needs.
  int16_t* raw_ = nullptr;
  uint8_t* frame_ = nullptr;
  float* fftRe_ = nullptr;
  float* fftIm_ = nullptr;
  uint32_t rawCap_ = 0;            // int16 samples (all channels) that raw_ can hold
  uint32_t decCap_ = 0;            // complex samples that the frame payload can hold
  uint32_t fftCap_ = 0;

  // The burst: which ADC channels, how many, and where each sits in a frame
  // (ascending ADC channel: R, Q, I with a reference, else Q, I).
  uint8_t chMask_ = 0;
  uint32_t nch_ = 2;
  uint32_t offI_ = 1, offQ_ = 0, offR_ = 0;

  uint32_t nRaw_ = 0;              // samples per channel this configuration takes
  uint32_t nDec_ = 0;              // complex samples it turns into
  uint32_t nfft_ = 0;
  size_t frameLen_ = 0;

  volatile uint8_t state_ = kIdle;
  volatile bool abort_ = false;
  volatile bool recordReady_ = false;
  volatile uint32_t scan_ = 0;
  volatile uint32_t achieved_hz_ = 0;
  volatile uint32_t acqStartMs_ = 0;   // millis() at the first sample of the scan
  volatile bool iFlag_ = false;
  volatile bool tFlag_ = false;

  // Phase reference of the scan set: the first scan's phase, this scan's phase
  // and amplitude, and the rotation that lines this scan up with the first.
  volatile bool refMeasured_ = false;
  volatile float refPhaseDeg_ = 0.0f;
  volatile float refAmp_ = 0.0f;
  float refPhase0Deg_ = 0.0f;
  float beatRotDeg_ = 0.0f;

  dsp::Spectrum spec_ = {0, 0, 0, 0};
  char error_[128] = {0};
  char supplyMsg_[128] = {0};
};
