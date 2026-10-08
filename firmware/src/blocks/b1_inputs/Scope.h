// Scope - the fast path of b1: one panel input sampled at kHz rates and sent as
// binary WebSocket frames (PROTOCOL.md section 6). Two modes, the two every
// oscilloscope has:
//
//   stream   roll mode. Contiguous chunks of `chunk` samples, one binary frame
//            (kind 1) per chunk, until stopped. A stream expires kStreamLeaseMs
//            after the last `stream` command, so a phone that walks out of WiFi
//            range does not leave the board sampling for nobody; the panel
//            renews it every few seconds.
//   capture  one shot (kind 2). Without a trigger: n samples now. With one: the
//            sampler takes bursts of 2n samples and looks for the crossing in
//            the part of the burst that leaves `pre` samples before it and
//            n - pre after it, so the window it sends always fits inside one
//            burst and is evenly spaced throughout - no stitching. `timeout_ms`
//            = 0 waits for the trigger for ever (normal), > 0 gives up after that
//            long and sends the last burst untriggered (auto, trig_index -1).
//
// Why a task: a burst is paced with a busy-wait (drivers/Ads8688.cpp) and the
// main loop must not spin. The sampler runs on core 1 at the NMR sequencer's
// priority, holds the SPI lock for one burst at a time, and hands each finished
// frame to the main task, which sends it (net/WsOut.h: the async-TCP queue is
// only fed from the main task). It never runs while an NMR scan does - both want
// the ADC, and the NMR record matters more.
//
// Two inputs: `ch2` adds a second input to either mode. The ADC scans both
// (auto-scan on a two-channel mask), so the two traces are sampled within a
// couple of microseconds of each other at every point - which is what makes a
// phase or delay between them meaningful. Each mode then sends TWO frames per
// burst, one per input, with the same t_ms and trig_index; the trigger always
// looks at the first input.
//
// Timing, honestly: inside one frame the samples are evenly spaced. On real
// hardware a stream has a short gap between chunks (the main loop sending the
// last one); each frame's t_ms says where it starts. Under SIM the samples are
// computed from one time base, so a SIM stream has no gaps.
#pragma once
#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

class Scope {
 public:
  // Limits. A stream is capped by the WiFi link (PROTOCOL.md section 6: about
  // 200 kB/s for everyone; 20 kS/s of int16 is 40 kB/s). A capture is capped by
  // how long the main loop can wait: a triggered capture holds the core for one
  // burst of 2n samples, so n / rate_hz is kept to a second or less.
  static constexpr uint32_t kStreamMaxHz   = 20000;
  static constexpr uint32_t kCaptureMaxHz  = 250000;
  static constexpr uint32_t kMinHz         = 10;
  static constexpr uint32_t kMaxN          = 10000;   // samples in one capture frame
  static constexpr uint32_t kMaxChunk      = 2000;    // samples in one stream frame
  static constexpr uint32_t kMaxCaptureMs  = 1000;    // n / rate_hz
  static constexpr uint32_t kStreamLeaseMs = 10000;
  // With two inputs: half the stream rate (the same bytes per second on the
  // WiFi) and half the capture length (a triggered burst is 2n scans of 2).
  static constexpr uint32_t kStreamMaxHzDual = kStreamMaxHz / 2;
  static constexpr uint32_t kMaxNDual        = kMaxN / 2;

  enum class Mode : uint8_t { Idle, Stream, Capture };

  struct Trigger {
    bool on = false;
    bool rising = true;
    float level_v = 0.0f;
    uint32_t pre = 0;          // samples kept before the crossing
    uint32_t timeout_ms = 0;   // 0 = normal (wait for ever), > 0 = auto
  };

  // All of these run on the main task.
  void begin();
  // `ain` is the ADC channel (pins.h kAinOfAi), `panel_ch` the AI number the
  // frame carries; `panel_ch2` = 0 means one input. Return nullptr when
  // accepted, else the reason.
  const char* startStream(uint8_t panel_ch, uint8_t ain, uint32_t rate_hz, uint32_t chunk,
                          uint8_t panel_ch2 = 0, uint8_t ain2 = 0);
  const char* startCapture(uint8_t panel_ch, uint8_t ain, uint32_t rate_hz, uint32_t n,
                           const Trigger& trig, uint8_t panel_ch2 = 0, uint8_t ain2 = 0);
  void stop();
  // Call every loop(): sends a finished frame, if there is one.
  void poll();

  Mode mode() const { return mode_; }
  uint8_t channel() const { return job_.panel_ch; }
  uint8_t channel2() const { return job_.panel_ch2; }
  uint32_t rateHz() const { return achievedHz_ ? achievedHz_ : job_.rate_hz; }
  uint32_t chunk() const { return job_.n; }
  uint32_t frames() const { return frames_; }
  uint32_t dropped() const { return dropped_; }
  const char* lastStop() const { return lastStop_; }
  // The newest sample of the channel being streamed, in volts (NAN if none).
  float lastVolts() const { return lastVolts_; }

 private:
  struct Job {
    Mode mode = Mode::Idle;
    uint8_t panel_ch = 1;
    uint8_t ain = 0;
    uint8_t panel_ch2 = 0;     // 0 = one input
    uint8_t ain2 = 0;
    uint32_t rate_hz = 1000;
    uint32_t n = 500;          // stream: chunk; capture: window length
    Trigger trig;
  };

  static void trampoline(void* self);
  void run();
  void runStream(const Job& j, uint32_t gen);
  void runCapture(const Job& j, uint32_t gen);

  // Fill `out` with n scans at rate_hz: one sample per scan, or two
  // interleaved in ascending ADC-channel order (Ads8688::burst). `t0_us` is the
  // time base of the first scan (SIM only: makes the stream continuous).
  // Returns false if the SPI bus could not be had.
  bool sample(const Job& j, int16_t* out, uint32_t n, int64_t t0_us, uint32_t* achieved_hz);
  bool waitForSlot(uint32_t gen);   // until the main task has sent the last frame
  // One frame for one input: samples raw[(first + k) * stride + slot], k < n.
  void publish(uint8_t kind, uint8_t panel_ch, uint8_t ain, uint32_t t_ms, uint32_t rate_hz,
               const int16_t* raw, uint32_t first, uint32_t stride, uint32_t slot, uint32_t n,
               int32_t trig_index);
  // Both inputs of a burst (or the one), waiting for the slot between them.
  bool publishAll(uint8_t kind, const Job& j, uint32_t gen, uint32_t t_ms, uint32_t rate_hz,
                  uint32_t first, uint32_t n, int32_t trig_index);
  static bool dual(const Job& j) { return j.panel_ch2 != 0; }
  // Where the first input sits in an interleaved scan.
  static uint32_t slotA(const Job& j) { return dual(j) && j.ain > j.ain2 ? 1 : 0; }
  bool stale(uint32_t gen) const { return gen != gen_; }
  bool allocate();
  void setJob(const Job& j);
  void finish(uint32_t gen, const char* why);

  TaskHandle_t task_ = nullptr;
  portMUX_TYPE mux_ = portMUX_INITIALIZER_UNLOCKED;

  Job job_;                          // written by the main task under mux_
  volatile uint32_t gen_ = 0;        // bumped on every new job or stop
  volatile Mode mode_ = Mode::Idle;
  volatile uint32_t leaseUntil_ = 0;

  int16_t* raw_ = nullptr;           // 2 * kMaxN samples: one triggered burst
  uint8_t* frame_ = nullptr;         // header + kMaxN samples
  volatile size_t frameLen_ = 0;     // > 0: a frame waits for the main task

  volatile uint32_t achievedHz_ = 0;
  volatile uint32_t frames_ = 0;
  volatile uint32_t dropped_ = 0;
  volatile float lastVolts_ = NAN;
  const char* volatile lastStop_ = "";

#ifdef SIM
  uint32_t seed_ = 2463534242u;
#endif
};
