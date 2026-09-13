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
  uint32_t t_polarize_settle_ms = 5;
  uint8_t hb_mode = 0;            // 0 off, 1 forward, 2 reverse (during polarize)
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
  uint32_t recordRate() const { return cfg_.decim ? cfg_.rate_hz / cfg_.decim : cfg_.rate_hz; }
  double ifHz() const { return cfg_.f_tx_hz - cfg_.f_lo_hz; }
  const dsp::Spectrum& spectrum() const { return spec_; }
  const char* error() const { return error_; }
  bool iFlag() const { return iFlag_; }
  bool tFlag() const { return tFlag_; }
  static bool flagsConnected();

  // Main task only. consumeRecord sends the frame if a new one is waiting;
  // resendRecord sends whatever the last one was (the `get_record` command).
  bool consumeRecord(Sink sink);
  bool resendRecord(Sink sink);

  // Manual bench controls, all refused while a scan set is running.
  void setBlank(bool receive);
  void pulseOnce(uint32_t t_us);
  void prepareHardware();          // program the clocks, the DDS, wake it up
  void idleHardware();             // blanked, gate off, polarizer off, DDS asleep

 private:
  static void trampoline(void* arg);
  void taskLoop();
  void runScanSet();
  bool runOneScan(uint32_t index, float phaseDeg);
  void processScan(uint32_t index, float phaseDeg);
  bool ensureBuffers(uint32_t nRaw, uint32_t nDec, const char** err);
  bool waitMs(uint32_t ms);        // false if the set was aborted while waiting
  void readFlags();
  void setLo(double hz);
  void publish(uint32_t scansAveraged);
  void note(const char* message);   // remember a message, stay in the state we are in
  void fail(const char* message);   // remember it and stop the scan set
#ifdef SIM
  void simBurst(uint32_t nRaw, float phaseDeg, uint32_t index);
#endif

  NmrConfig cfg_;

  TaskHandle_t task_ = nullptr;
  SemaphoreHandle_t frameLock_ = nullptr;

  // PSRAM. raw_ is the interleaved I,Q capture in ADC codes; frame_ is the
  // outgoing binary frame, whose payload doubles as the running-mean
  // accumulator, so the averaged record is never copied; fftRe_/fftIm_ are the
  // scratch the spectrum needs.
  int16_t* raw_ = nullptr;
  uint8_t* frame_ = nullptr;
  float* fftRe_ = nullptr;
  float* fftIm_ = nullptr;
  uint32_t rawCap_ = 0;            // samples per channel that raw_ can hold
  uint32_t decCap_ = 0;            // complex samples that the frame payload can hold
  uint32_t fftCap_ = 0;

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
  dsp::Spectrum spec_ = {0, 0, 0, 0};
  char error_[72] = {0};
};
