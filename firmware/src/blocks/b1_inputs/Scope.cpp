#include "Scope.h"

#include <esp_heap_caps.h>
#include <esp_timer.h>
#include <string.h>

#include "../../drivers/Ads8688.h"
#include "../../drivers/SpiBus.h"
#include "../../net/WsOut.h"
#include "../Busy.h"
#include "SimSignals.h"

namespace {

constexpr uint32_t kTaskStack = 4096;
constexpr UBaseType_t kTaskPriority = 5;   // as the NMR sequencer; the Arduino loop is 1
constexpr BaseType_t kTaskCore = 1;        // WiFi and lwIP have core 0

constexpr uint8_t kKindStream = 1;
constexpr uint8_t kKindCapture = 2;
constexpr uint8_t kBlockId = 1;            // b1
constexpr size_t kHeaderBytes = 28;        // PROTOCOL.md section 6

// Trigger hysteresis: the signal has to go this far past the level the other way
// before a crossing counts again, so noise riding on a slow edge does not fire
// the trigger on every wiggle. 0.5 % of full scale, whatever the range.
constexpr int32_t kHysteresisCodes = 328;

// A capture frame waits this long for room in the WebSocket queue before it is
// dropped; a stream chunk does not wait at all (the next one is already coming).
constexpr uint32_t kCaptureSendWaitMs = 2000;

// On real hardware a stream burst busy-waits on core 1, the core the main loop
// runs on. After every chunk the sampler steps aside for at least this long so
// the loop can send the frame, answer commands and broadcast the status.
constexpr uint32_t kStreamYieldMs = 3;

void* allocBuffer(size_t bytes) {
  void* p = heap_caps_malloc(bytes, MALLOC_CAP_SPIRAM);
  return p ? p : malloc(bytes);
}

// Index of the first trigger crossing that leaves `pre` samples before it and
// n - pre after it inside raw[0 .. len), or -1. `armed` starts false, so a
// crossing only counts once the signal has been on the far side of the level.
int32_t findTrigger(const int16_t* raw, uint32_t len, uint32_t n, uint32_t pre,
                    int32_t level, bool rising) {
  const uint32_t last = n + pre;            // start = k - pre must leave n samples
  bool armed = false;
  for (uint32_t k = 0; k < len && k <= last; k++) {
    const int32_t v = raw[k];
    if (rising) {
      if (v < level - kHysteresisCodes) armed = true;
      else if (armed && v >= level) {
        if (k >= pre) return static_cast<int32_t>(k);
        armed = false;
      }
    } else {
      if (v > level + kHysteresisCodes) armed = true;
      else if (armed && v <= level) {
        if (k >= pre) return static_cast<int32_t>(k);
        armed = false;
      }
    }
  }
  return -1;
}

}  // namespace

// ---------------------------------------------------------------------------
// Main task
// ---------------------------------------------------------------------------
void Scope::begin() {
  if (task_) return;
  xTaskCreatePinnedToCore(&Scope::trampoline, "b1scope", kTaskStack, this, kTaskPriority, &task_,
                          kTaskCore);
}

bool Scope::allocate() {
  if (!raw_) raw_ = static_cast<int16_t*>(allocBuffer(2 * kMaxN * sizeof(int16_t)));
  if (!frame_) frame_ = static_cast<uint8_t*>(allocBuffer(kHeaderBytes + kMaxN * sizeof(int16_t)));
  return raw_ && frame_ && task_;
}

void Scope::setJob(const Job& j) {
  portENTER_CRITICAL(&mux_);
  job_ = j;
  gen_ = gen_ + 1;
  mode_ = j.mode;
  achievedHz_ = 0;
  lastStop_ = "";
  portEXIT_CRITICAL(&mux_);
  if (task_) xTaskNotifyGive(task_);
}

const char* Scope::startStream(uint8_t panel_ch, uint8_t ain, uint32_t rate_hz, uint32_t chunk) {
  if (nmr_busy()) return "an NMR scan is running";
  if (rate_hz < kMinHz || rate_hz > kStreamMaxHz) return "stream rate_hz 10..20000 (0 = stop)";
  if (chunk == 0) chunk = rate_hz / 20;                 // a frame every 50 ms
  const uint32_t maxChunk = rate_hz / 10 > 0 ? rate_hz / 10 : 1;   // <= 100 ms per frame
  if (chunk > maxChunk) chunk = maxChunk;
  if (chunk > kMaxChunk) chunk = kMaxChunk;
  if (chunk < 1) chunk = 1;
  if (!allocate()) return "out of memory";

  leaseUntil_ = millis() + kStreamLeaseMs;
  // The same stream asked for again is a renewal, not a restart: the panel sends
  // it every few seconds and the waveform must not jump when it does.
  if (mode_ == Mode::Stream && job_.panel_ch == panel_ch && job_.rate_hz == rate_hz &&
      job_.n == chunk)
    return nullptr;

  Job j;
  j.mode = Mode::Stream;
  j.panel_ch = panel_ch;
  j.ain = ain;
  j.rate_hz = rate_hz;
  j.n = chunk;
  setJob(j);
  return nullptr;
}

const char* Scope::startCapture(uint8_t panel_ch, uint8_t ain, uint32_t rate_hz, uint32_t n,
                                const Trigger& trig) {
  if (nmr_busy()) return "an NMR scan is running";
  if (rate_hz < kMinHz || rate_hz > kCaptureMaxHz) return "capture rate_hz 10..250000";
  if (n < 16 || n > kMaxN) return "capture n 16..10000";
  if (static_cast<uint64_t>(n) * 1000 > static_cast<uint64_t>(kMaxCaptureMs) * rate_hz)
    return "capture longer than 1 s (n / rate_hz): use stream for slow signals";
  if (trig.on && trig.pre >= n) return "trig.pre must be less than n";
  if (trig.timeout_ms > 60000) return "timeout_ms 0..60000";
  if (!allocate()) return "out of memory";

  Job j;
  j.mode = Mode::Capture;
  j.panel_ch = panel_ch;
  j.ain = ain;
  j.rate_hz = rate_hz;
  j.n = n;
  j.trig = trig;
  setJob(j);
  return nullptr;
}

void Scope::stop() {
  Job j;
  j.panel_ch = job_.panel_ch;
  setJob(j);
  lastStop_ = "stopped";
}

void Scope::poll() {
  const size_t len = frameLen_;
  if (len == 0) return;
  static uint32_t waitingSince = 0;
  if (!wsBinaryReady()) {
    // Nobody connected, or the queue is full: a stream chunk is dropped at once,
    // a capture gets a couple of seconds to find room.
    const uint32_t now = millis();
    if (frame_[0] == kKindCapture) {
      if (waitingSince == 0) waitingSince = now ? now : 1;
      if (now - waitingSince < kCaptureSendWaitMs) return;
    }
    dropped_ = dropped_ + 1;
  } else {
    wsBinaryAll(frame_, len);
    frames_ = frames_ + 1;
  }
  waitingSince = 0;
  frameLen_ = 0;
}

// ---------------------------------------------------------------------------
// Sampler task
// ---------------------------------------------------------------------------
void Scope::trampoline(void* self) { static_cast<Scope*>(self)->run(); }

void Scope::run() {
  for (;;) {
    Job j;
    uint32_t gen;
    portENTER_CRITICAL(&mux_);
    j = job_;
    gen = gen_;
    portEXIT_CRITICAL(&mux_);

    if (j.mode == Mode::Idle) {
      ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
      continue;
    }
    if (j.mode == Mode::Stream) runStream(j, gen);
    else runCapture(j, gen);
  }
}

void Scope::finish(uint32_t gen, const char* why) {
  portENTER_CRITICAL(&mux_);
  if (gen == gen_) {
    job_.mode = Mode::Idle;
    mode_ = Mode::Idle;
    lastStop_ = why;
  }
  portEXIT_CRITICAL(&mux_);
}

bool Scope::sample(const Job& j, int16_t* out, uint32_t n, int64_t t0_us, uint32_t* achieved_hz) {
#ifdef SIM
  // Computed from one time base, so consecutive stream chunks join up exactly.
  const double dt = 1.0 / static_cast<double>(j.rate_hz);
  const double t0 = static_cast<double>(t0_us) * 1e-6;
  for (uint32_t i = 0; i < n; i++)
    out[i] = b1SimCode(j.ain, b1SimVolts(j.panel_ch - 1, t0 + i * dt, seed_));
  *achieved_hz = j.rate_hz;
  return true;
#else
  (void)t0_us;
  spibus::Guard g(50);
  if (!g.ok) return false;
  return adc.burst(static_cast<uint8_t>(1u << j.ain), out, n, j.rate_hz, achieved_hz) == n;
#endif
}

bool Scope::waitForSlot(uint32_t gen) {
  while (frameLen_ != 0) {
    if (stale(gen)) return false;
    vTaskDelay(1);
  }
  return !stale(gen);
}

void Scope::publish(uint8_t kind, const Job& j, uint32_t t_ms, uint32_t rate_hz,
                    const int16_t* samples, uint32_t n, int32_t trig_index) {
  const float offset_v = adc.toVolts(j.ain, 0);
  const float volts_per_lsb = adc.toVolts(j.ain, 1) - offset_v;
  uint8_t* f = frame_;
  f[0] = kind;
  f[1] = kBlockId;
  f[2] = j.panel_ch;
  f[3] = 16;
  memcpy(f + 4, &t_ms, 4);          // the ESP32 is little-endian, as the frame is
  memcpy(f + 8, &rate_hz, 4);
  memcpy(f + 12, &n, 4);
  memcpy(f + 16, &trig_index, 4);
  memcpy(f + 20, &volts_per_lsb, 4);
  memcpy(f + 24, &offset_v, 4);
  memcpy(f + kHeaderBytes, samples, n * sizeof(int16_t));
  achievedHz_ = rate_hz;
  lastVolts_ = offset_v + volts_per_lsb * samples[n - 1];
  frameLen_ = kHeaderBytes + n * sizeof(int16_t);   // last: hands the frame over
}

void Scope::runStream(const Job& j, uint32_t gen) {
  const uint32_t n = j.n;
  const int64_t t0 = esp_timer_get_time();
  uint64_t done = 0;                 // samples sent so far (the SIM time base)
  while (!stale(gen)) {
    if (nmr_busy()) { finish(gen, "an NMR scan started"); return; }
    if (static_cast<int32_t>(millis() - leaseUntil_) > 0) { finish(gen, "lease expired"); return; }

#ifdef SIM
    // The chunk covers [start, start + n / rate). Sleep until it has "happened".
    const int64_t start = t0 + static_cast<int64_t>(done * 1000000ULL / j.rate_hz);
    const int64_t end = t0 + static_cast<int64_t>((done + n) * 1000000ULL / j.rate_hz);
    while (esp_timer_get_time() < end) {
      if (stale(gen)) return;
      const int64_t left_ms = (end - esp_timer_get_time()) / 1000;
      vTaskDelay(pdMS_TO_TICKS(left_ms > 1 ? static_cast<uint32_t>(left_ms) : 1u));
    }
#else
    (void)t0;
    const int64_t start = esp_timer_get_time();
#endif

    uint32_t achieved = 0;
    if (!sample(j, raw_, n, start, &achieved)) { vTaskDelay(2); continue; }   // bus busy
    if (!waitForSlot(gen)) return;
    publish(kKindStream, j, static_cast<uint32_t>(start / 1000), achieved, raw_, n, -1);
    done += n;
#ifndef SIM
    vTaskDelay(pdMS_TO_TICKS(kStreamYieldMs));
#endif
  }
}

void Scope::runCapture(const Job& j, uint32_t gen) {
  const uint32_t n = j.n;
  const bool trig = j.trig.on;
  const uint32_t len = trig ? 2 * n : n;
  const uint32_t armedAt = millis();

  // The level as a raw code on this channel's current range.
  const float off = adc.toVolts(j.ain, 0);
  const float lsb = adc.toVolts(j.ain, 1) - off;
  float lv = lsb > 0.0f ? roundf((j.trig.level_v - off) / lsb) : 0.0f;
  if (lv > 32767.0f) lv = 32767.0f;
  if (lv < -32768.0f) lv = -32768.0f;
  const int32_t level = static_cast<int32_t>(lv);

  while (!stale(gen)) {
    if (nmr_busy()) { finish(gen, "an NMR scan started"); return; }

    const int64_t t0 = esp_timer_get_time();
    uint32_t achieved = 0;
    if (!sample(j, raw_, len, t0, &achieved)) { vTaskDelay(2); continue; }
#ifdef SIM
    // The real burst takes len / rate; so does this one, or the trigger rate
    // and the "auto" timeout would not behave like the hardware's.
    const uint32_t burstMs = static_cast<uint32_t>(static_cast<uint64_t>(len) * 1000 / j.rate_hz);
    vTaskDelay(pdMS_TO_TICKS(burstMs > 1 ? burstMs : 1u));
#endif
    const uint32_t rate = achieved ? achieved : j.rate_hz;
    const uint32_t t0_ms = static_cast<uint32_t>(t0 / 1000);

    if (!trig) {
      if (!waitForSlot(gen)) return;
      publish(kKindCapture, j, t0_ms, rate, raw_, n, -1);
      finish(gen, "done");
      return;
    }

    const int32_t k = findTrigger(raw_, len, n, j.trig.pre, level, j.trig.rising);
    if (k >= 0) {
      const uint32_t first = static_cast<uint32_t>(k) - j.trig.pre;
      if (!waitForSlot(gen)) return;
      publish(kKindCapture, j, t0_ms + static_cast<uint32_t>(static_cast<uint64_t>(first) * 1000 / rate),
              rate, raw_ + first, n, static_cast<int32_t>(j.trig.pre));
      finish(gen, "triggered");
      return;
    }
    if (j.trig.timeout_ms && millis() - armedAt >= j.trig.timeout_ms) {
      if (!waitForSlot(gen)) return;
      publish(kKindCapture, j, t0_ms, rate, raw_, n, -1);   // auto: show what is there
      finish(gen, "auto (no trigger)");
      return;
    }
    // Between attempts the main loop gets the core back - for a tenth of a burst,
    // so a Stop pressed during a long, never-firing capture is answered in time.
    const uint32_t restMs = 2 + static_cast<uint32_t>(static_cast<uint64_t>(len) * 100 / j.rate_hz);
    vTaskDelay(pdMS_TO_TICKS(restMs));
  }
}
