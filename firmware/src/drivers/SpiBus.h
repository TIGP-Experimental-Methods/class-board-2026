// SpiBus - the one lock on SPI2 (NMR-FIRMWARE.md section 2.1).
//
// Three chips share SPI2: the ADS8688 ADC (b1), the DAC8563 (b3) and the AD9834
// DDS (NMR transmitter). Block code runs on the main task, but the NMR sequencer
// runs on its own task pinned to core 1 and holds the bus for a whole capture
// burst. Without a lock the two tasks would interleave mid-transfer and both
// would read rubbish, so every transfer goes through this mutex.
//
// The mutex is recursive: a sequencer that already holds the bus can still call
// a driver method that takes it (the DDS driver locks on its own, because b3 and
// the NMR block both use it). A plain mutex would deadlock there.
//
// Use the Guard where you can - it releases on every exit path, including an
// early return in the middle of a sequence:
//     spibus::Guard g;            // waits up to 50 ms
//     if (!g.ok) return;          // someone else has the bus: skip this pass
#pragma once
#include <stdint.h>

namespace spibus {

// SPI.begin() on the board's pins, once. Safe to call from several drivers.
void begin();

// true when the bus is ours. timeout_ms = 0 means "try, do not wait".
bool lock(uint32_t timeout_ms = 50);
void unlock();

struct Guard {
  bool ok;
  explicit Guard(uint32_t ms = 50) : ok(lock(ms)) {}
  ~Guard() { if (ok) unlock(); }
  Guard(const Guard&) = delete;
  Guard& operator=(const Guard&) = delete;
};

}  // namespace spibus
