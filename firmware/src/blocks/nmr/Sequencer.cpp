#include "Sequencer.h"

#include <Arduino.h>
#include <esp_heap_caps.h>
#include <esp_timer.h>
#include <math.h>
#include <string.h>

#include "../../../include/pins.h"
#include "../../drivers/Ad9834.h"
#include "../../drivers/Ads8688.h"
#include "../../drivers/Si5351.h"
#include "../../drivers/SpiBus.h"
#include "../../drivers/Tca9535.h"
#include "../Busy.h"
#include "../Vext.h"

#ifdef SIM
#include <esp_system.h>
#endif

namespace {

// The receiver's two baseband outputs, on panel inputs AI7 (I) and AI8 (Q),
// which are ADC channels AIN_3 and AIN_2 (pins.h kAinOfAi). The auto scan
// returns the channels of its mask in ascending order, so a frame of the
// capture buffer is Q, I - or R, Q, I with the phase reference on AI1 (AIN_1);
// applyConfig works out where each one sits.
constexpr uint8_t kChI = kAinOfAi[6];
constexpr uint8_t kChQ = kAinOfAi[7];

// The ADS8688 converts 500 kS/s in all, shared by the channels of the burst.
constexpr uint32_t kMaxAdcRate = 500000;

// Memory. The board has 8 MB of PSRAM and the WebSocket queues its outgoing
// frames in the same pool (the Arduino build sends every allocation over 4 kB
// to PSRAM), so the console cannot have all of it. Two caps keep the total
// under 6 MB and both are enforced by config:
//   raw capture   channels x int16 x nRaw            <= 4 MB at 2e6 samples in all
//   record frame  8 bytes per complex sample + 28    <= 1 MB at 131072 samples
// 2e6 samples is 4 s at 250 kS/s on two channels, well past anything the
// physics justifies; 131072 complex samples is a 1 MB frame, which is already
// more than a phone wants to receive every few seconds.
constexpr uint32_t kMaxRawTotal = 2000000;
constexpr uint32_t kMaxDec = 131072;
constexpr uint32_t kMaxFft = 16384;       // section 3.3: the longest transform
constexpr size_t kPsramMargin = 512 * 1024;   // left for the network and the app

// Decimation works in blocks so the scratch fits on the task stack.
constexpr uint32_t kChunk = 256;

constexpr uint32_t kTaskStack = 12288;
constexpr UBaseType_t kTaskPriority = 5;   // the Arduino loop task is 1
constexpr BaseType_t kTaskCore = 1;        // WiFi and lwIP have core 0

#ifdef SIM
// The simulated spectrometer (section 3.6). 20 uV at the coil, an LNA gain of
// 1000 and about 0.9 through the mixer make 18 mV at the converter; the water
// line at 2 mT decays with T2* of about 0.4 s; the bench has 3 mV of broadband
// noise and 2 mV of mains hum. The small DC offsets are there so the offset
// removal has something to do.
constexpr float kSimAmpV = 0.018f;
constexpr float kSimT2 = 0.4f;
constexpr float kSimNoiseV = 0.003f;
constexpr float kSimHumV = 0.002f;
constexpr float kSimHumHz = 50.0f;
constexpr float kSimOffsetIV = 0.005f;
constexpr float kSimOffsetQV = -0.004f;
#endif

// The phase reference (section 3.9). The phase that matters is the one at the
// start of the record, so the fit uses the first 20 ms (about a hundred cycles
// at 5.4 kHz): long enough to average the converter noise away, short enough
// that a small error in the assumed sample rate cannot move the answer. The
// fundamental of the 0-3.3 V square wave is 2.1 V; under 0.2 V nothing is there.
constexpr float kRefFitS = 0.020f;
constexpr float kRefMinAmpV = 0.2f;

// +VEXT limits for the OPA564 (blocks/Vext.h, docs/class-board-reference.md
// rule 3): 7 V is its minimum (6.5 V allows for the reading), 24 V its rated
// maximum and 26 V its absolute maximum; at gain 25 the output needs 16 V.
constexpr float kVextMin = 6.5f;
constexpr float kVextMax = 25.0f;
constexpr float kVextClip = 16.0f;

#ifdef SIM
// The simulated reference arrives with a fixed delay of its own (cable, input
// filter): a constant offset, which the correction must not care about.
constexpr float kSimRefLagRad = 0.7f;
#endif

constexpr float kPi = 3.14159265358979f;

// Wait until an absolute microsecond stamp. Short waits spin, because a pulse
// boundary has to land where it was asked to; anything longer than about a
// millisecond and a half hands the core back first, so the idle task still runs.
inline void waitUntil(int64_t due_us) {
  for (;;) {
    const int64_t left = due_us - esp_timer_get_time();
    if (left <= 0) return;
    if (left > 1500) vTaskDelay(pdMS_TO_TICKS(static_cast<uint32_t>((left - 1000) / 1000)));
  }
}

// Volts per ADC code on a channel, whatever range it is programmed to. The
// conversion is linear, so one difference finds the slope and any zero offset
// falls out with the DC removal.
inline float voltsPerCode(uint8_t ch) {
  return (adc.toVolts(ch, 10000) - adc.toVolts(ch, 0)) / 10000.0f;
}

}  // namespace

// ---------------------------------------------------------------------------
// Memory
// ---------------------------------------------------------------------------
bool Sequencer::ensureBuffers(uint32_t nRawTotal, uint32_t nDec, const char** err) {
  const uint32_t nfft = dsp::fftLength(nDec, kMaxFft);

  const size_t rawBytes = static_cast<size_t>(nRawTotal) * sizeof(int16_t);
  const size_t frameBytes = 28 + static_cast<size_t>(nDec) * 2 * sizeof(float);
  const size_t fftBytes = static_cast<size_t>(nfft) * sizeof(float);

  size_t wanted = 0;
  if (nRawTotal > rawCap_) wanted += rawBytes;
  if (nDec > decCap_) wanted += frameBytes;
  if (nfft > fftCap_) wanted += 2 * fftBytes;
  if (wanted > 0) {
    const size_t free_psram = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
    if (free_psram < wanted + kPsramMargin) {
      *err = "not enough memory for that record - shorten t_acq_ms or raise decim";
      return false;
    }
  }

  // Grow only. A shorter record reuses the buffer it already has, which keeps
  // the big allocations out of the middle of a session where PSRAM is most
  // likely to be fragmented.
  if (nRawTotal > rawCap_) {
    int16_t* p = static_cast<int16_t*>(heap_caps_malloc(rawBytes, MALLOC_CAP_SPIRAM));
    if (!p) { *err = "capture buffer allocation failed"; return false; }
    free(raw_);
    raw_ = p;
    rawCap_ = nRawTotal;
  }
  if (nDec > decCap_) {
    uint8_t* p = static_cast<uint8_t*>(heap_caps_malloc(frameBytes, MALLOC_CAP_SPIRAM));
    if (!p) { *err = "record buffer allocation failed"; return false; }
    if (frameLock_) xSemaphoreTake(frameLock_, portMAX_DELAY);
    free(frame_);
    frame_ = p;
    decCap_ = nDec;
    if (frameLock_) xSemaphoreGive(frameLock_);
  }
  if (nfft > fftCap_) {
    float* a = static_cast<float*>(heap_caps_malloc(fftBytes, MALLOC_CAP_SPIRAM));
    float* b = static_cast<float*>(heap_caps_malloc(fftBytes, MALLOC_CAP_SPIRAM));
    if (!a || !b) {
      free(a);
      free(b);
      *err = "spectrum buffer allocation failed";
      return false;
    }
    free(fftRe_);
    free(fftIm_);
    fftRe_ = a;
    fftIm_ = b;
    fftCap_ = nfft;
  }

  nDec_ = nDec;
  nfft_ = nfft;
  frameLen_ = frameBytes;
  recordReady_ = false;     // whatever was in the old buffer is gone
  return true;
}

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
bool Sequencer::applyConfig(const NmrConfig& want, const char** err) {
  static const char* kOk = "";
  *err = kOk;
  if (running()) { *err = "scan running"; return false; }

  // Ranges. Everything here is a physical limit of the board or of the
  // arithmetic, not a matter of taste, so the reply says which one was hit.
  if (want.f_tx_hz < 1000.0 || want.f_tx_hz > 1000000.0) { *err = "f_tx_hz must be 1000..1000000"; return false; }
  if (want.f_lo_hz < 1000.0 || want.f_lo_hz > 1000000.0) { *err = "f_lo_hz must be 1000..1000000"; return false; }
  if (want.t90_us < 1 || want.t90_us > 5000) { *err = "t90_us must be 1..5000"; return false; }
  if (want.t180_us < 1 || want.t180_us > 10000) { *err = "t180_us must be 1..10000"; return false; }
  if (want.tau_us > 500000) { *err = "tau_us must be 0..500000"; return false; }
  if (want.t_blank_pre_us > 10000) { *err = "t_blank_pre_us must be 0..10000"; return false; }
  if (want.t_dead_us > 100000) { *err = "t_dead_us must be 0..100000"; return false; }
  if (want.t_acq_start_us > 100000) { *err = "t_acq_start_us must be 0..100000"; return false; }
  if (want.t_acq_ms < 1 || want.t_acq_ms > 4000) { *err = "t_acq_ms must be 1..4000"; return false; }
  if (want.rate_hz < 1000 || want.rate_hz > 250000) { *err = "rate_hz must be 1000..250000"; return false; }
  if (want.decim < 1 || want.decim > 1024) { *err = "decim must be 1..1024"; return false; }
  if (want.n_avg < 1 || want.n_avg > 256) { *err = "n_avg must be 1..256"; return false; }
  if (want.t_repeat_ms > 600000) { *err = "t_repeat_ms must be 0..600000"; return false; }
  if (want.polarize_ms > 10000) { *err = "polarize_ms must be 0..10000"; return false; }
  if (want.t_polarize_settle_ms > 1000) { *err = "t_polarize_settle_ms must be 0..1000"; return false; }
  if (want.hb_mode > 2) { *err = "hb_mode must be off, fwd or rev"; return false; }
  if (want.ref_ch == 7 || want.ref_ch == 8) { *err = "ref_ch 7 and 8 carry the receiver I and Q"; return false; }
  if (want.ref_ch > 8) { *err = "ref_ch must be 0 (none) or 1..6"; return false; }

  // The burst: I and Q, plus the reference channel when there is one. The ADC's
  // 500 kS/s is shared, so a third channel lowers the rate each one can have.
  uint8_t mask = static_cast<uint8_t>((1u << kChI) | (1u << kChQ));
  if (want.ref_ch) mask = static_cast<uint8_t>(mask | (1u << kAinOfAi[want.ref_ch - 1]));
  const uint32_t nch = static_cast<uint32_t>(__builtin_popcount(mask));
  if (want.rate_hz * nch > kMaxAdcRate) {
    *err = want.ref_ch ? "rate_hz must be at most 166666 with ref_ch (500 kS/s over three channels)"
                       : "rate_hz must be 1000..250000";
    return false;
  }

  // A complex record sampled at R covers -R/2 to +R/2. If the intermediate
  // frequency is outside that, the line folds over and comes back at the wrong
  // place - the spectrum would look perfectly convincing and be wrong, which is
  // why this is refused rather than warned about.
  const double if_hz = fabs(want.f_tx_hz - want.f_lo_hz);
  const double fs = 1.0e6 / Ads8688::periodUs(want.rate_hz);    // the paced rate
  const double dec_rate = fs / static_cast<double>(want.decim);
  if (dec_rate <= 2.0 * if_hz) {
    *err = "rate_hz / decim must be more than twice the IF - lower decim or move f_lo";
    return false;
  }
  if (want.ref_ch) {
    // CLK2 is the IF itself, and the Si5351 cannot divide its 900 MHz down below
    // 3.9 kHz (Si5351.h kClk2MinHz): an Earth's-field IF of a few hundred hertz
    // has no reference.
    if (if_hz < Si5351::kClk2MinHz + 1.0) {
      *err = "ref_ch needs an IF of at least 3.91 kHz (the slowest CLK2 the Si5351 makes)";
      return false;
    }
    // The ADS8688's own second-order filter (about 15 kHz) takes the tone away
    // above this.
    if (if_hz >= 30000.0) { *err = "ref_ch needs an IF below 30 kHz"; return false; }
    // The reference is a square wave. If one of its odd harmonics folds back to
    // within 100 Hz of the IF at this sample rate, the fit sees it as part of the
    // fundamental and its phase, which moves differently, biases every scan.
    for (int n = 3; n <= 9; n += 2) {
      double f = fmod(n * if_hz, fs);
      if (f > fs / 2.0) f = fs - f;
      if (fabs(f - if_hz) < 100.0) {
        *err = "rate_hz folds a reference harmonic onto the IF - change rate_hz";
        return false;
      }
    }
  }

  // The whole record has to be in the buffer before it can be decimated.
  const uint32_t nRaw = static_cast<uint32_t>(
      (static_cast<uint64_t>(want.t_acq_ms) * want.rate_hz) / 1000u);
  if (nRaw < 16) { *err = "t_acq_ms x rate_hz is too short to process"; return false; }
  if (static_cast<uint64_t>(nRaw) * nch > kMaxRawTotal) {
    *err = "t_acq_ms x rate_hz x channels exceeds the 4 MB capture buffer";
    return false;
  }
  const uint32_t nDec = nRaw / want.decim;
  if (nDec < 16) { *err = "decim leaves too few samples to process"; return false; }
  if (nDec > kMaxDec) {
    *err = "record too long to send - raise decim or shorten t_acq_ms";
    return false;
  }

  if (!ensureBuffers(nRaw * nch, nDec, err)) return false;

  // Where each channel sits in a frame: the number of mask bits below it.
  auto slot = [mask](uint8_t ch) {
    return static_cast<uint32_t>(__builtin_popcount(mask & ((1u << ch) - 1u)));
  };
  chMask_ = mask;
  nch_ = nch;
  offI_ = slot(kChI);
  offQ_ = slot(kChQ);
  offR_ = want.ref_ch ? slot(kAinOfAi[want.ref_ch - 1]) : 0;
  nRaw_ = nRaw;

  cfg_ = want;
  scan_ = 0;
  achieved_hz_ = 0;
  spec_ = dsp::Spectrum{0, 0, 0, 0};
  error_[0] = '\0';
  if (state_ == kError) state_ = kIdle;
  return true;
}

// ---------------------------------------------------------------------------
// Task
// ---------------------------------------------------------------------------
bool Sequencer::begin() {
  if (!frameLock_) frameLock_ = xSemaphoreCreateMutex();

  const char* err = nullptr;
  if (!applyConfig(cfg_, &err)) {
    // No PSRAM for the default record - a dev board without the memory, say.
    // The message is kept for whoever tries to run something, but the console
    // stays idle rather than shouting "error" at a class that is not using it.
    note(err);
  }
  if (!task_) {
    xTaskCreatePinnedToCore(&Sequencer::trampoline, "nmrseq", kTaskStack, this,
                            kTaskPriority, &task_, kTaskCore);
  }
  return task_ != nullptr;
}

void Sequencer::trampoline(void* arg) {
  static_cast<Sequencer*>(arg)->taskLoop();
}

void Sequencer::taskLoop() {
  for (;;) {
    // Asleep until start() pokes us. No polling, no timer: the task costs
    // nothing at all between scan sets.
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    runScanSet();
  }
}

bool Sequencer::start(const char** err) {
  static const char* kOk = "";
  *err = kOk;
  if (running()) { *err = "scan already running"; return false; }
  if (!task_) { *err = "sequencer task did not start"; return false; }
  if (!raw_ || !frame_) { *err = error_[0] ? error_ : "no record buffer - send config first"; return false; }
  if (const char* p = supplyProblem()) { *err = p; return false; }

  // State and the busy flag go up here, on the main task, so that the reply to
  // `start` is already true and b4 refuses the polarizer from the very next
  // command rather than from whenever the task happens to wake.
  error_[0] = '\0';
  abort_ = false;
  scan_ = 0;
  recordReady_ = false;
  spec_ = dsp::Spectrum{0, 0, 0, 0};
  state_ = kRunning;
  g_nmrBusy = true;
  xTaskNotifyGive(task_);
  return true;
}

void Sequencer::abortScanSet() {
  abort_ = true;
  if (!running()) state_ = kIdle;       // nothing was running: just clear "done"
}

void Sequencer::note(const char* message) {
  if (!message) return;
  strncpy(error_, message, sizeof(error_) - 1);
  error_[sizeof(error_) - 1] = '\0';
}

void Sequencer::fail(const char* message) {
  note(message);
  state_ = kError;
}

// ---------------------------------------------------------------------------
// Hardware
// ---------------------------------------------------------------------------
// The frequencies, on the lattice of section 3.9 (Si5351.h): the DDS clock, the
// carrier word W, the LO word V (the even word nearest f_lo_hz), and CLK2 at
// exactly (W - V) when there is a reference channel. The carrier is written
// first because its word is what the rest is worked out from. Called at
// `config` (so the reply says what the hardware does), at boot and before every
// scan set.
bool Sequencer::programClocks() {
  // The DDS master clock. Every transmit frequency is a fraction of it, so it
  // is programmed again rather than trusted to have survived whatever else has
  // been going on (an `nmr clock` command, say), and the DDS driver is told, so
  // its frequency words are worked out from it.
  clockgen.setClk0(50000000);
  dds.setMclk(static_cast<uint32_t>(lround(clockgen.actualClk0())));
  dds.setFrequency(cfg_.f_tx_hz);
  const uint32_t txWord = dds.frequencyWord();

  const double step = clockgen.latticeStep();
  const uint32_t loWord = 2u * static_cast<uint32_t>(lround(cfg_.f_lo_hz / (2.0 * step)));
  // The Johnson counter divides CLK1 by four to make I and Q. Which of its four
  // states it lands in after a frequency change is anyone's guess, and a wrong
  // state is a 90 degree receiver phase error, so it is always cleared.
  clockgen.setClk1(4.0 * step * loWord);
  clockgen.resetPllB();
  expander.pulseJohnsonClear();

  if (!cfg_.ref_ch) {
    clockgen.setClk2Exact(0);            // off and powered down: nothing reads it
    return true;
  }
  // The divider only; prepareHardware() switches the output on for a scan set.
  const int64_t beat = static_cast<int64_t>(txWord) - static_cast<int64_t>(loWord);
  return clockgen.setClk2Exact(static_cast<uint32_t>(beat < 0 ? -beat : beat));
}

// Both read back from the drivers, whose arithmetic is exact in a double for a
// lattice frequency (Si5351.cpp), so after programClocks() the IF is (W - V) x
// step; after a bench `clock` or `dds` command it is whatever those set.
double Sequencer::loActualHz() const {
  return clockgen.actualClk1() / 4.0;
}

double Sequencer::ifHz() const {
  return dds.actualFrequency() - loActualHz();
}

double Sequencer::sampleRate() const {
  return 1.0e6 / Ads8688::periodUs(cfg_.rate_hz);
}

const char* Sequencer::supplyProblem() {
  const float v = g_vextVolts;
  if (!g_vextCheck || isnan(v)) return nullptr;        // check off, or no b2 to measure it
  if (v < kVextMin) {
    snprintf(supplyMsg_, sizeof(supplyMsg_),
             "+VEXT below 6.5 V (reads %.1f V) - bench supply off? (or b2 vext_check off if the sense divider is not fitted)",
             static_cast<double>(v));
    return supplyMsg_;
  }
  if (v > kVextMax) {
    snprintf(supplyMsg_, sizeof(supplyMsg_),
             "+VEXT above 25 V (reads %.1f V) - OPA564 limit (or b2 vext_check off if the sense divider is not fitted)",
             static_cast<double>(v));
    return supplyMsg_;
  }
  return nullptr;
}

bool Sequencer::txClipWarning() {
  const float v = g_vextVolts;
  return g_vextCheck && !isnan(v) && v < kVextClip;
}

bool Sequencer::prepareHardware() {
#ifndef SIM
  // The coils first: b4 may have left the polarizer or the H-bridge on, and a
  // scan must never start with either (the polarize step switches them itself).
  digitalWrite(PIN_FET_GATE, LOW);
  digitalWrite(PIN_HB_IN1, LOW);
  digitalWrite(PIN_HB_IN2, LOW);
#endif
  // Park the phase accumulator while the frequency and phase registers are
  // loaded, then let the carrier run. Loading a frequency into a running
  // accumulator puts a step in the middle of the carrier; the receiver measures
  // phase, so that step would show up as a spurious signal.
  dds.sleep(false);
  dds.setReset(true);
  const bool ok = programClocks();
  dds.setPhase(0, 0.0);
  dds.setPhase(1, 180.0);
  dds.selectPhase(false);
  dds.setReset(false);
  // The reference runs for the scan set only (or the one bench pulse), so the
  // panel input is free and quiet while the console is idle.
  if (cfg_.ref_ch && ok) clockgen.enable(2, true);
  return ok;
}

void Sequencer::idleHardware() {
#ifndef SIM
  digitalWrite(PIN_TX_EN, LOW);        // transmitter off
  digitalWrite(PIN_RX_BLANK, LOW);     // receiver blanked: the LNA stays quiet
  digitalWrite(PIN_FET_GATE, LOW);     // polarizer off
  digitalWrite(PIN_HB_IN1, LOW);       // H-bridge coasting
  digitalWrite(PIN_HB_IN2, LOW);
#endif
  dds.selectPhase(false);
  dds.sleep(true);                     // no carrier while nothing is transmitting
  clockgen.enable(2, false);           // no reference either: AI1 is quiet
}

void Sequencer::setBlank(bool receive) {
#ifndef SIM
  digitalWrite(PIN_RX_BLANK, receive ? HIGH : LOW);
#else
  (void)receive;
#endif
}

void Sequencer::pulseOnce(uint32_t t_us) {
  // A single gate for a scope check, run straight from the main task: a few
  // milliseconds of busy-wait is less trouble than waking the sequencer for it.
  iFlag_ = false;
  tFlag_ = false;
  setBlank(false);
  waitUntil(esp_timer_get_time() + cfg_.t_blank_pre_us);
  gate(t_us);
}

// One transmit gate. The flags are sampled in the last microsecond of the gate,
// while the amplifier still drives (a current limit shows only then), and again
// just after it closes; the reads do not lengthen the pulse.
int64_t Sequencer::gate(uint32_t t_us) {
#ifndef SIM
  const int64_t on = esp_timer_get_time();
  digitalWrite(PIN_TX_EN, HIGH);
  if (t_us > 1) waitUntil(on + t_us - 1);
  readFlags();
  waitUntil(on + t_us);
  digitalWrite(PIN_TX_EN, LOW);
  readFlags();
#else
  waitUntil(esp_timer_get_time() + t_us);
#endif
  return esp_timer_get_time();
}

// The OPA564 flags on GPIO6 / GPIO7 (rework A2), active high. Without the
// rework the pull-downs hold them at 0, which reads as "no flag". The flags
// latch for the scan: a read ORs into them, the start of a scan clears them.
void Sequencer::readFlags() {
#ifndef SIM
  if (digitalRead(PIN_TX_IFLAG) == HIGH) iFlag_ = true;
  if (digitalRead(PIN_TX_TFLAG) == HIGH) tFlag_ = true;
#endif
}

bool Sequencer::flagFailed() {
  if (iFlag_) {
    fail("current limit - check the coil and the gain jumper");
    return true;
  }
  if (tFlag_) {
    fail("thermal - duty cycle too high");
    return true;
  }
  return false;
}

bool Sequencer::waitMs(uint32_t ms) {
  const int64_t due = esp_timer_get_time() + static_cast<int64_t>(ms) * 1000;
  for (;;) {
    if (abort_) return false;
    const int64_t left = due - esp_timer_get_time();
    if (left <= 0) return true;
    // Sliced so an abort is acted on promptly even in a long relaxation wait.
    const uint32_t slice = (left > 20000) ? 20u : static_cast<uint32_t>((left + 999) / 1000);
    vTaskDelay(pdMS_TO_TICKS(slice ? slice : 1u));
  }
}

// ---------------------------------------------------------------------------
// One scan
// ---------------------------------------------------------------------------
bool Sequencer::runOneScan(uint32_t index, float phaseDeg) {
  iFlag_ = false;
  tFlag_ = false;

  // 1. Prepolarize (Earth's-field option). The polarizer FET carries the coil
  //    current, so it is switched off again before anything is transmitted.
  if (cfg_.polarize_ms > 0) {
#ifndef SIM
    digitalWrite(PIN_HB_IN1, cfg_.hb_mode == 1 ? HIGH : LOW);
    digitalWrite(PIN_HB_IN2, cfg_.hb_mode == 2 ? HIGH : LOW);
    digitalWrite(PIN_FET_GATE, HIGH);
#endif
    const bool ok = waitMs(cfg_.polarize_ms);
#ifndef SIM
    digitalWrite(PIN_FET_GATE, LOW);
    digitalWrite(PIN_HB_IN1, LOW);
    digitalWrite(PIN_HB_IN2, LOW);
#endif
    if (!ok) return false;
    // The field has to settle before the pulse, or the line is somewhere else.
    if (!waitMs(cfg_.t_polarize_settle_ms)) return false;
  }

  // 2. The phase of this scan's pulse. PHASE0 carries it and PHASE1 carries it
  //    plus 90 degrees, so the refocusing pulse of an echo is one control-word
  //    write away (the PSEL bit, about 2 us of SPI, sent during tau while the
  //    transmitter is off). Written before the receiver is blanked, because the
  //    phase-register writes take time that the timing cannot spare.

  dds.setPhase(0, static_cast<double>(phaseDeg));
  dds.setPhase(1, static_cast<double>(phaseDeg) + 90.0);
  dds.selectPhase(false);

  // 3. Blank the receiver before the transmitter can do anything to it.
  setBlank(false);
  waitUntil(esp_timer_get_time() + cfg_.t_blank_pre_us);

  // 4. The pulse. digitalWrite costs well under a microsecond, which at the
  //    intermediate frequency is a degree or two of phase - inside the jitter
  //    the contract allows. A flag raised during the pulse stops the set here,
  //    before the receiver opens.
  int64_t pulseEnd = gate(cfg_.t90_us);
  if (flagFailed()) return false;      // before an echo's second pulse can fire

  if (cfg_.echo) {
    // Spin echo: a second pulse of twice the length, 90 degrees out of phase,
    // tau after the first. It turns the dephasing round so the signal comes
    // back at 2 tau - the part of the decay that is the magnet, not the sample.
    waitUntil(pulseEnd + cfg_.tau_us);
    dds.selectPhase(true);
    pulseEnd = gate(cfg_.t180_us);
    if (flagFailed()) return false;
  }
  if (abort_) return false;

  // 5. Dead time: the coil is still ringing with hundreds of volts of what we
  //    just put into it. Unblanking early is how receivers die.
  waitUntil(pulseEnd + cfg_.t_dead_us);
  setBlank(true);

  // 6. Acquisition.
  waitUntil(pulseEnd + cfg_.t_acq_start_us);
  acqStartMs_ = millis();
#ifdef SIM
  simBurst(nRaw_, phaseDeg, index);
  achieved_hz_ = cfg_.rate_hz;
  // The simulated converter is far quicker than the real one; wait out the rest
  // of the record so the app and the sequence see the same timing either way.
  waitUntil(pulseEnd + cfg_.t_acq_start_us + static_cast<int64_t>(cfg_.t_acq_ms) * 1000);
#else
  {
    // The whole burst runs with the bus held: b1 and b3 skip their turn rather
    // than interleave a frame into a conversion.
    spibus::Guard g(200);
    if (!g.ok) {
      fail("SPI bus busy - another block is holding it");
      return false;
    }
    uint32_t achieved = 0;
    const uint32_t got = adc.burst(chMask_, raw_, nRaw_, cfg_.rate_hz, &achieved);
    achieved_hz_ = achieved;
    if (got < nRaw_) {
      fail("ADC burst short - check the converter");
      return false;
    }
    // The reference fit assumes the paced sample instants. A burst that fell
    // behind free-ran at an unknown rate, and its phase would be meaningless.
    const uint32_t paced = 1000000u / Ads8688::periodUs(cfg_.rate_hz);
    if (cfg_.ref_ch && achieved < paced - paced / 100) {
      fail("ADC fell behind rate_hz on three channels - lower rate_hz");
      return false;
    }
  }
#endif

  // 7. Blanked again between scans, then look at what the transmitter thought
  //    of it all, and at the phase reference.
  setBlank(false);
  readFlags();
  if (flagFailed()) return false;
  if (cfg_.ref_ch && !measureReference(index)) return false;
  return true;
}

// The phase of the CLK2 tone at the start of the record (section 3.9). CLK2 is
// exactly f_tx - f_lo, so its phase moves with the beat between carrier and LO,
// which is what sets the IF phase of this scan's signal. The rotation that brings
// this scan's reference phase back to the first scan's brings its signal back too.
// For a negative IF, CLK2 runs at |IF| and its phase moves the other way.
bool Sequencer::measureReference(uint32_t index) {
  const uint8_t refAdc = kAinOfAi[cfg_.ref_ch - 1];
  const double fs = sampleRate();
  const double ifHzNow = ifHz();
  const float w = static_cast<float>(2.0 * M_PI * fabs(ifHzNow) / fs);
  uint32_t nFit = static_cast<uint32_t>(fs * kRefFitS);
  if (nFit < 64) nFit = 64;
  if (nFit > nRaw_) nFit = nRaw_;

  const dsp::Tone t = dsp::fitTone(raw_ + offR_, nFit, nch_, w);
  refAmp_ = t.amp * fabsf(voltsPerCode(refAdc));
  refPhaseDeg_ = t.phase * 180.0f / kPi;
  refMeasured_ = true;
  if (refAmp_ < kRefMinAmpV) {
    char msg[64];
    snprintf(msg, sizeof(msg), "reference tone missing on AI%u - is CLK2 wired?",
             static_cast<unsigned>(cfg_.ref_ch));
    fail(msg);
    return false;
  }
  if (index == 0) refPhase0Deg_ = refPhaseDeg_;
  const float d = refPhaseDeg_ - refPhase0Deg_;
  beatRotDeg_ = ifHzNow >= 0.0 ? -d : d;
  return true;
}

void Sequencer::processScan(uint32_t index, float phaseDeg) {
  if (!raw_ || !frame_ || nDec_ == 0) return;

  const float vI = voltsPerCode(kChI);
  const float vQ = voltsPerCode(kChQ);

  // DC offset from the quiet tail of the record (section 3.3).
  const uint32_t from = dsp::dcStart(nRaw_, cfg_.t_acq_ms);
  const uint32_t nDc = nRaw_ - from;
  const int16_t* tail = raw_ + static_cast<size_t>(from) * nch_;
  const float dcI = dsp::meanI16(tail + offI_, nDc, nch_);
  const float dcQ = dsp::meanI16(tail + offQ_, nDc, nch_);

  // CYCLOPS: the record is rotated back by the pulse phase, so the signal from
  // every scan lands on top of itself and everything that ignored the pulse
  // does not. With a phase reference the beat phase of this scan is taken out
  // in the same rotation (zero without one).
  const float rot = (cfg_.cyclops ? -phaseDeg : 0.0f) + (cfg_.ref_ch ? beatRotDeg_ : 0.0f);

  float* acc = reinterpret_cast<float*>(frame_ + 28);
  float chunk[2 * kChunk];

  if (frameLock_) xSemaphoreTake(frameLock_, portMAX_DELAY);
  for (uint32_t done = 0; done < nDec_; done += kChunk) {
    const uint32_t m = (nDec_ - done < kChunk) ? (nDec_ - done) : kChunk;
    dsp::decimate(raw_ + static_cast<size_t>(done) * cfg_.decim * nch_, nch_, offI_, offQ_, m,
                  cfg_.decim, dcI, dcQ, vI, vQ, chunk);
    dsp::rotate(chunk, m, rot);
    dsp::accumulateMean(acc + static_cast<size_t>(done) * 2, chunk, m, index);
  }
  publish(index + 1);
  if (frameLock_) xSemaphoreGive(frameLock_);

  // The spectrum is for the status line only; the app does its own. Reading the
  // accumulator without the lock is safe: this task is its only writer.
  if (fftRe_ && fftIm_) {
    spec_ = dsp::analyse(acc, nDec_, static_cast<float>(recordRate()), fftRe_, fftIm_, nfft_);
  }
  recordReady_ = true;
}

// Fill in the 28-byte header in front of the payload (PROTOCOL.md section 7.4).
// Written field by field rather than through a struct so the layout on the wire
// is visible here and cannot drift with a compiler's idea of padding.
void Sequencer::publish(uint32_t scansAveraged) {
  uint8_t* h = frame_;
  h[0] = 3;                      // kind 3: an averaged NMR record
  h[1] = 9;                      // block id of the nmr block
  h[2] = 0;                      // ch: the record is one complex channel
  h[3] = 32;                     // bits: float32 pairs, not int16
  const uint32_t t_ms = acqStartMs_;
  const uint32_t rate = static_cast<uint32_t>(lround(recordRate()));   // the header field is whole hertz
  const uint32_t n = nDec_;
  const int32_t scans = static_cast<int32_t>(scansAveraged);
  const float vpl = 1.0f;        // the payload is already in volts
  const float if_hz = static_cast<float>(ifHz());
  memcpy(h + 4, &t_ms, 4);
  memcpy(h + 8, &rate, 4);
  memcpy(h + 12, &n, 4);
  memcpy(h + 16, &scans, 4);
  memcpy(h + 20, &vpl, 4);
  memcpy(h + 24, &if_hz, 4);
}

void Sequencer::runScanSet() {
  iFlag_ = false;
  tFlag_ = false;
  refMeasured_ = false;
  beatRotDeg_ = 0.0f;
  bool ok = prepareHardware();          // false only when CLK2 was wanted and not set
  if (!ok) fail("CLK2 could not be set to the IF - check the Si5351");

  for (uint32_t s = 0; ok && s < cfg_.n_avg; s++) {
    if (abort_) break;
    // The four steps of the phase cycle. With n_avg not a multiple of four the
    // cycle is left unbalanced, which is the user's choice: the app offers
    // multiples of four and nothing breaks if you ignore it.
    const float phase = cfg_.cyclops ? 90.0f * static_cast<float>(s % 4) : 0.0f;
    if (!runOneScan(s, phase)) { ok = false; break; }
    processScan(s, phase);
    scan_ = s + 1;
    if (s + 1 < cfg_.n_avg && !waitMs(cfg_.t_repeat_ms)) break;
  }

  idleHardware();
  if (state_ != kError) state_ = (abort_ || !ok) ? kIdle : kDone;
  abort_ = false;
  g_nmrBusy = false;
}

// ---------------------------------------------------------------------------
// Handing the record to the main task
// ---------------------------------------------------------------------------
bool Sequencer::consumeRecord(Sink sink) {
  if (!recordReady_ || !sink || !frame_) return false;
  // A short timeout, not portMAX_DELAY: the main task also serves the web
  // server, and a record that misses this pass goes out on the next one.
  if (frameLock_ && xSemaphoreTake(frameLock_, pdMS_TO_TICKS(20)) != pdTRUE) return false;
  sink(frame_, frameLen_);
  if (frameLock_) xSemaphoreGive(frameLock_);
  recordReady_ = false;
  return true;
}

bool Sequencer::resendRecord(Sink sink) {
  if (!sink || !frame_ || scan_ == 0) return false;
  if (frameLock_ && xSemaphoreTake(frameLock_, pdMS_TO_TICKS(20)) != pdTRUE) return false;
  sink(frame_, frameLen_);
  if (frameLock_) xSemaphoreGive(frameLock_);
  return true;
}

// ---------------------------------------------------------------------------
// The simulated spectrometer
// ---------------------------------------------------------------------------
#ifdef SIM
void Sequencer::simBurst(uint32_t nRaw, float phaseDeg, uint32_t index) {
  if (!raw_) return;
  const float codeI = 1.0f / voltsPerCode(kChI);
  const float codeQ = 1.0f / voltsPerCode(kChQ);

  const double ifSim = cfg_.sim_larmor_hz - loActualHz();
  const double fs = sampleRate();                 // the paced rate, as the converter runs
  const float rate = static_cast<float>(fs);

  // The beat phase of this scan (section 3.8): the pulse lands at a random point
  // of the f_tx - f_lo cycle, so the record starts at a random IF phase. Without
  // a reference this is what spoils the average; with one it is what the
  // reference measures and takes out.
  const float beat = static_cast<float>(esp_random() >> 8) * (2.0f * kPi / 16777216.0f);

  // The signal is carried by a phasor stepped one sample at a time rather than
  // by a sine call per sample: a million calls to sinf would take longer than
  // the acquisition it is pretending to be.
  float dph = static_cast<float>(2.0 * M_PI * ifSim / fs);
  dph = fmodf(dph, 2.0f * kPi);
  const float wr = cosf(dph);
  const float wi = sinf(dph);
  const float phi = phaseDeg * kPi / 180.0f + beat;
  float cr = cosf(phi);
  float ci = sinf(phi);

  // The reference: CLK2, a 0-3.3 V square wave at |IF| on the reference input,
  // sampled at the paced instants. Its phase follows the beat (the other way
  // for a negative IF) plus a fixed lag.
  const bool ref = cfg_.ref_ch != 0;
  const uint8_t refAdc = ref ? kAinOfAi[cfg_.ref_ch - 1] : 0;
  const float refVpc = voltsPerCode(refAdc);
  const float refZero = adc.toVolts(refAdc, 0);
  const double ifRef = ifHz();
  const float drr = static_cast<float>(fmod(2.0 * M_PI * fabs(ifRef) / fs, 2.0 * M_PI));
  const float rwr = cosf(drr);
  const float rwi = sinf(drr);
  const float rphi = (ifRef >= 0.0 ? beat : -beat) + kSimRefLagRad;
  float rr = cosf(rphi);
  float ri = sinf(rphi);
  // Clamped like the I/Q path: 3.3 V is over the top of the +-2.56 V range.
  auto toCode = [](float c) {
    if (c > 32767.0f) c = 32767.0f;
    if (c < -32768.0f) c = -32768.0f;
    return static_cast<int16_t>(lroundf(c));
  };
  const int16_t codeHigh = toCode((3.3f - refZero) / refVpc);
  const int16_t codeLow = toCode((0.0f - refZero) / refVpc);

  // Mains hum, with a phase that is different every scan: it is not tied to the
  // pulse, so averaging has to remove it, and it does.
  const float dhum = 2.0f * kPi * kSimHumHz / rate;
  const float hwr = cosf(dhum);
  const float hwi = sinf(dhum);
  const float humPhi = static_cast<float>((index * 2654435761u) >> 20) * (2.0f * kPi / 4096.0f);
  float hr = cosf(humPhi);
  float hi = sinf(humPhi);

  const float decay = expf(-1.0f / (kSimT2 * rate));
  float env = 1.0f;

  // Uniform noise of the right rms: a uniform variable on [-a, a] has rms
  // a / sqrt(3). It is not Gaussian, but the transform averages enough samples
  // per bin that the spectrum cannot tell.
  const float noiseAmp = kSimNoiseV * 1.7320508f;
  uint32_t seed = 22222u + index * 7919u;

  for (uint32_t k = 0; k < nRaw; k++) {
    seed = seed * 1664525u + 1013904223u;
    const float nI = (static_cast<float>((seed >> 9) & 0xFFFF) * (1.0f / 32768.0f) - 1.0f) * noiseAmp;
    seed = seed * 1664525u + 1013904223u;
    const float nQ = (static_cast<float>((seed >> 9) & 0xFFFF) * (1.0f / 32768.0f) - 1.0f) * noiseAmp;

    const float sig = kSimAmpV * env;
    const float vI = sig * cr + kSimHumV * hr + nI + kSimOffsetIV;
    const float vQ = sig * ci + kSimHumV * hi + nQ + kSimOffsetQV;

    float ci_code = vI * codeI;
    float cq_code = vQ * codeQ;
    if (ci_code > 32767.0f) ci_code = 32767.0f;
    if (ci_code < -32768.0f) ci_code = -32768.0f;
    if (cq_code > 32767.0f) cq_code = 32767.0f;
    if (cq_code < -32768.0f) cq_code = -32768.0f;
    int16_t* frame = raw_ + static_cast<size_t>(k) * nch_;
    frame[offI_] = static_cast<int16_t>(lroundf(ci_code));
    frame[offQ_] = static_cast<int16_t>(lroundf(cq_code));
    if (ref) frame[offR_] = ri >= 0.0f ? codeHigh : codeLow;

    // Step the phasors on. They drift off the unit circle after a few thousand
    // multiplications, so all are pulled back now and then - cheaper than a
    // trigonometric call per sample and just as accurate.
    const float nr = cr * wr - ci * wi;
    ci = cr * wi + ci * wr;
    cr = nr;
    const float nhr = hr * hwr - hi * hwi;
    hi = hr * hwi + hi * hwr;
    hr = nhr;
    const float nrr = rr * rwr - ri * rwi;
    ri = rr * rwi + ri * rwr;
    rr = nrr;
    env *= decay;
    if ((k & 1023u) == 1023u) {
      const float m = sqrtf(cr * cr + ci * ci);
      if (m > 0.0f) { cr /= m; ci /= m; }
      const float mh = sqrtf(hr * hr + hi * hi);
      if (mh > 0.0f) { hr /= mh; hi /= mh; }
      const float mr = sqrtf(rr * rr + ri * ri);
      if (mr > 0.0f) { rr /= mr; ri /= mr; }
    }
  }
}
#endif

