#include "WatchBlock.h"

#include <math.h>

#include "../../../include/pins.h"
#include "../../drivers/Ads8688.h"
#include "../../drivers/SpiBus.h"

void WatchBlock::begin() {
  // BaseBlock::begin() has already started the shared bus; calling these again
  // is harmless and keeps the block independent of the order blocks are added.
  spibus::begin();
  adc.begin();
}

void WatchBlock::loop() {
  uint32_t now = millis();
  if (now - lastTick_ < 1000 / kRateHz) return;
  lastTick_ = now;
  // Do not wait for the bus: during an NMR capture the sequencer holds it for
  // the whole burst, and blocking here would stall every other block too.
  if (!sample(0)) return;
  recompute();
}

bool WatchBlock::sample(uint32_t lock_ms) {
#ifdef SIM
  (void)lock_ms;
  // Something with the shape of a real measurement, so the panel and an alarm
  // rule have something to do: a slow walk, noise on top, and a spike every
  // few seconds that the mean hides but the excursion count does not.
  float t = millis() / 1000.0f;
  float walk  = 0.08f * sinf(2 * PI * t / 45.0f);       // ~90 s round trip
  float noise = random(-1000, 1000) / 100000.0f;        // ~10 mV
  float spike = (random(0, 400) == 0) ? random(-80, 80) / 1000.0f : 0.0f;
  v_ = 0.5f + walk + noise + spike;
#else
  spibus::Guard g(lock_ms);
  if (!g.ok) return false;
  const uint8_t ain = kAinOfAi[ch_ - 1];
  v_ = adc.toVolts(ain, adc.readManual(ain));
#endif

  buf_[head_] = v_;
  head_ = (head_ + 1) % window_;
  if (count_ < window_) count_++;
  return true;
}

void WatchBlock::recompute() {
  if (count_ < 2) return;

  // buf_ is a ring of window_ slots; oldest sample is at head_ when full.
  float sum = 0, lo = buf_[0], hi = buf_[0];
  for (int i = 0; i < count_; i++) {
    float x = buf_[i];
    sum += x;
    if (x < lo) lo = x;
    if (x > hi) hi = x;
  }
  mean_ = sum / count_;
  pp_   = hi - lo;

  float ss = 0;
  for (int i = 0; i < count_; i++) {
    float d = buf_[i] - mean_;
    ss += d * d;
  }
  rms_ = sqrtf(ss / (count_ - 1));

  // Drift: the mean of the older half against the mean of the newer half,
  // scaled to volts per minute. Cruder than a least-squares fit and far
  // cheaper, and it is the direction and rough size that matter here.
  int half = count_ / 2;
  if (half >= 1) {
    float a = 0, b = 0;
    for (int i = 0; i < half; i++) {
      a += buf_[(head_ - count_ + i + 2 * window_) % window_];          // older
      b += buf_[(head_ - count_ + half + i + 2 * window_) % window_];   // newer
    }
    a /= half; b /= half;
    float span_min = (half * 2.0f / kRateHz) / 60.0f;
    drift_ = span_min > 0 ? (b - a) / span_min : 0;
  }

  // Excursions is cumulative on purpose: a rule on it fires on the first burst
  // and the count then stays up until the operator clears it with reset.
  if (rms_ > 0 && fabsf(v_ - mean_) > sigma_ * rms_) excursions_++;
}

bool WatchBlock::handle(JsonObjectConst cmd, JsonObject reply) {
  const char* c = cmd["cmd"] | "";
  JsonObjectConst a = argsOf(cmd);

  if (strcmp(c, "set_input") == 0) {              // {"ch":1..8}
    int ch = a["ch"] | 0;
    if (ch < 1 || ch > 8) { reply["error"] = "ch 1..8"; return false; }
    ch_ = ch;
    head_ = 0; count_ = 0; excursions_ = 0;       // the old window is a different signal
    reply["ch"] = ch_;
    return true;
  }

  if (strcmp(c, "set_window") == 0) {             // {"s":1..30}
    float s = a["s"] | 0.0f;
    int n = (int)(s * kRateHz);
    if (n < kRateHz || n > kMaxSamples) {
      reply["error"] = "s 1..30";
      return false;
    }
    window_ = n;
    head_ = 0; count_ = 0;
    reply["window_s"] = (float)window_ / kRateHz;
    return true;
  }

  if (strcmp(c, "set_sigma") == 0) {              // {"k":1..10}
    float k = a["k"] | 0.0f;
    if (k < 1.0f || k > 10.0f) { reply["error"] = "k 1..10"; return false; }
    sigma_ = k;
    reply["sigma"] = sigma_;
    return true;
  }

  if (strcmp(c, "zero") == 0) {
    // Baseline is the current mean, not the current sample - one noisy sample
    // would put the zero in the wrong place.
    if (count_ < 2) { reply["error"] = "no window yet"; return false; }
    baseline_ = mean_;
    reply["baseline"] = baseline_;
    return true;
  }

  if (strcmp(c, "reset") == 0) {
    head_ = 0; count_ = 0; excursions_ = 0;
    reply["ok"] = true;
    return true;
  }

  reply["error"] = "unknown cmd";
  return false;
}

void WatchBlock::status(JsonObject out) {
  out["ch"]         = ch_;
  out["v"]          = v_;
  out["mean"]       = mean_;
  out["rms"]        = rms_;
  out["pp"]         = pp_;
  out["dev"]        = mean_ - baseline_;
  out["drift"]      = drift_;
  out["excursions"] = excursions_;
  out["baseline"]   = baseline_;
  out["n"]          = count_;
}
