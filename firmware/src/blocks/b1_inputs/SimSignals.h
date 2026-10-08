// What a SIM board pretends is plugged into AI1..AI8. One model for both paths,
// so the 20 Hz voltmeter and the kHz scope agree about every input:
//
//   AI1  1 Hz sine, 4 V amplitude        (slow: the strip chart's demo)
//   AI2  0.5 Hz triangle, +-5 V          (slow)
//   AI3  1 kHz sine, 2 V amplitude, on 0.2 V, 10 mV noise   (a scope signal)
//   AI4  250 Hz logic square 0 / 3.3 V with 40 us RC edges  (a trigger signal)
//   AI5..AI8  0.4 .. 0.7 V offsets with 5 mV noise          (AI7/AI8 = NMR I/Q idle)
//
// AI3 and AI4 are far too fast for a 20 Hz reading, so their voltmeter values
// jump about - a real voltmeter sampling a 1 kHz sine would do the same.
// Values pass through the input's range (b1SimCode) so a range that is too small
// clips, as the real converter does.
#pragma once
#ifdef SIM
#include <math.h>
#include <stdint.h>

#include "../../drivers/Ads8688.h"

// Uniform noise in [-1, 1] from a caller-owned LCG state.
inline float b1SimNoise(uint32_t& seed) {
  seed = seed * 1664525u + 1013904223u;
  return static_cast<float>(static_cast<int32_t>(seed >> 9) - (1 << 22)) / static_cast<float>(1 << 22);
}

// Volts on panel input `i` (0 = AI1) at time t seconds.
inline float b1SimVolts(int i, double t, uint32_t& seed) {
  constexpr float kTwoPi = 6.2831853f;
  switch (i) {
    case 0: return 4.0f * sinf(kTwoPi * static_cast<float>(fmod(t, 1.0)));
    case 1: return 5.0f * (2.0f * fabsf(static_cast<float>(fmod(t, 2.0)) - 1.0f) - 1.0f);
    case 2: return 0.2f + 2.0f * sinf(kTwoPi * static_cast<float>(fmod(t * 1000.0, 1.0)))
                   + 0.01f * b1SimNoise(seed);
    case 3: {
      constexpr double kPeriod = 1.0 / 250.0;
      constexpr float kTau = 40e-6f;
      const float p = static_cast<float>(fmod(t, kPeriod));
      const float half = static_cast<float>(kPeriod / 2);
      const float v = p < half ? 3.3f * (1.0f - expf(-p / kTau)) : 3.3f * expf(-(p - half) / kTau);
      return v + 0.005f * b1SimNoise(seed);
    }
    default: return 0.1f * i + 0.005f * b1SimNoise(seed);
  }
}

// The signed code the ADS8688 would return for `v` on ADC channel `ain` at its
// current range (the inverse of Ads8688::toVolts), clipped at full scale.
inline int16_t b1SimCode(uint8_t ain, float v) {
  const float off = adc.toVolts(ain, 0);
  const float lsb = adc.toVolts(ain, 1) - off;
  if (lsb <= 0.0f) return 0;
  const float code = roundf((v - off) / lsb);
  if (code > 32767.0f) return 32767;
  if (code < -32768.0f) return -32768;
  return static_cast<int16_t>(code);
}
#endif
