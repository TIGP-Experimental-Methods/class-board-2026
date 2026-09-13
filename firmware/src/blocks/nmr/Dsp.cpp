#include "Dsp.h"

#include <algorithm>
#include <math.h>
#include <stddef.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace dsp {
namespace {

// Median of the Rayleigh distribution is sigma * sqrt(2 ln 2). Dividing the
// median magnitude of the noise bins by this gets back to the noise level per
// quadrature. The median is used rather than the mean because a couple of
// spurious lines (a mains harmonic, a switching spur) would drag a mean up but
// move a median hardly at all.
constexpr float kRayleighMedian = 1.17741f;

// Bins either side of 0 Hz left out of the peak search. Whatever DC removal
// leaves behind lands there, and it is an artefact of the receiver, not a line.
constexpr uint32_t kDcGuard = 2;

}  // namespace

float meanI16(const int16_t* first, uint32_t n, uint32_t stride) {
  if (!first || n == 0 || stride == 0) return 0.0f;
  // A million int16 sum to at most 3.3e10, which int64 holds exactly; summing
  // into a float would start losing counts after about 16 million.
  int64_t sum = 0;
  for (uint32_t i = 0; i < n; i++) sum += first[(size_t)i * stride];
  return static_cast<float>(static_cast<double>(sum) / static_cast<double>(n));
}

uint32_t dcStart(uint32_t n, uint32_t t_acq_ms) {
  if (n == 0) return 0;
  if (t_acq_ms < 1000) return 0;          // no quiet tail: use the whole record
  return n - n / 10;                      // the last tenth
}

void decimate(const int16_t* rawIq, uint32_t nOut, uint32_t decim,
              float dcI, float dcQ, float voltsPerCodeI, float voltsPerCodeQ,
              float* outIq) {
  if (!rawIq || !outIq || decim == 0) return;
  const float inv = 1.0f / static_cast<float>(decim);
  for (uint32_t k = 0; k < nOut; k++) {
    const int16_t* p = rawIq + (size_t)k * decim * 2;
    float si = 0.0f;
    float sq = 0.0f;
    for (uint32_t j = 0; j < decim; j++) {
      si += static_cast<float>(p[2 * j]);
      sq += static_cast<float>(p[2 * j + 1]);
    }
    outIq[2 * k]     = (si * inv - dcI) * voltsPerCodeI;
    outIq[2 * k + 1] = (sq * inv - dcQ) * voltsPerCodeQ;
  }
}

void rotate(float* zIq, uint32_t n, float deg) {
  if (!zIq || n == 0) return;
  const float rad = deg * static_cast<float>(M_PI) / 180.0f;
  const float c = cosf(rad);
  const float s = sinf(rad);
  for (uint32_t k = 0; k < n; k++) {
    const float i = zIq[2 * k];
    const float q = zIq[2 * k + 1];
    zIq[2 * k]     = i * c - q * s;
    zIq[2 * k + 1] = i * s + q * c;
  }
}

void accumulateMean(float* accIq, const float* zIq, uint32_t n, uint32_t scansDone) {
  if (!accIq || !zIq || n == 0) return;
  if (scansDone == 0) {
    for (uint32_t k = 0; k < 2 * n; k++) accIq[k] = zIq[k];
    return;
  }
  const float w = 1.0f / static_cast<float>(scansDone + 1);
  for (uint32_t k = 0; k < 2 * n; k++) accIq[k] += (zIq[k] - accIq[k]) * w;
}

uint32_t fftLength(uint32_t n, uint32_t maxN) {
  uint32_t len = 8;
  while (len < n && len < maxN) len <<= 1;
  if (len > maxN) len = maxN;
  return len;
}

void fft(float* re, float* im, uint32_t n) {
  if (!re || !im || n < 2) return;

  // Bit-reversal permutation: after it, the butterflies can run in place.
  for (uint32_t i = 1, j = 0; i < n; i++) {
    uint32_t bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      std::swap(re[i], re[j]);
      std::swap(im[i], im[j]);
    }
  }

  for (uint32_t len = 2; len <= n; len <<= 1) {
    const double ang = -2.0 * M_PI / static_cast<double>(len);
    const double wr = cos(ang);
    const double wi = sin(ang);
    const uint32_t half = len >> 1;
    for (uint32_t base = 0; base < n; base += len) {
      // The twiddle factor is stepped round the unit circle rather than
      // recomputed with cos/sin per butterfly, which would cost more than the
      // transform itself on a core without trigonometric hardware. The step is
      // kept in double: a float recurrence drifts off the unit circle after a
      // few thousand steps and quietly tilts the spectrum.
      double cr = 1.0;
      double ci = 0.0;
      for (uint32_t k = 0; k < half; k++) {
        const uint32_t a = base + k;
        const uint32_t b = a + half;
        const float tr = static_cast<float>(static_cast<double>(re[b]) * cr - static_cast<double>(im[b]) * ci);
        const float ti = static_cast<float>(static_cast<double>(re[b]) * ci + static_cast<double>(im[b]) * cr);
        re[b] = re[a] - tr;
        im[b] = im[a] - ti;
        re[a] += tr;
        im[a] += ti;
        const double nr = cr * wr - ci * wi;
        ci = cr * wi + ci * wr;
        cr = nr;
      }
    }
  }
}

Spectrum analyse(const float* zIq, uint32_t n, float rate_hz,
                 float* re, float* im, uint32_t nfft) {
  Spectrum s = {0.0f, 0.0f, 0.0f, 0.0f};
  if (!zIq || !re || !im || n == 0 || nfft < 8 || rate_hz <= 0.0f) return s;

  const uint32_t nUse = (n < nfft) ? n : nfft;

  // Hann window over the samples we have, zeros over the padding. The window
  // stops the abrupt end of the record from smearing the line across the whole
  // spectrum; it costs a factor two in coherent gain, which sumW takes out.
  double sumW = 0.0;
  for (uint32_t k = 0; k < nUse; k++) {
    const float w = 0.5f * (1.0f - cosf(2.0f * static_cast<float>(M_PI) *
                                        static_cast<float>(k) / static_cast<float>(nUse)));
    re[k] = zIq[2 * k] * w;
    im[k] = zIq[2 * k + 1] * w;
    sumW += static_cast<double>(w);
  }
  for (uint32_t k = nUse; k < nfft; k++) {
    re[k] = 0.0f;
    im[k] = 0.0f;
  }

  fft(re, im, nfft);

  // Magnitudes, in volts rms of one quadrature: a complex tone of amplitude A
  // puts |X| = A * sum(window) in its bin, and A/sqrt(2) is its rms value.
  const float scale = (sumW > 0.0) ? static_cast<float>(1.0 / (sumW * 1.41421356)) : 0.0f;
  for (uint32_t k = 0; k < nfft; k++) re[k] = hypotf(re[k], im[k]) * scale;

  // The line: the largest bin that is not sitting on top of the DC artefact.
  uint32_t kp = kDcGuard + 1;
  float best = -1.0f;
  for (uint32_t k = kDcGuard + 1; k + kDcGuard < nfft; k++) {
    if (re[k] > best) {
      best = re[k];
      kp = k;
    }
  }

  // Parabolic interpolation through the peak and its neighbours: the line is
  // hardly ever exactly on a bin, and a Hann-windowed peak is close enough to a
  // parabola that this recovers most of the difference.
  const float ym = re[(kp + nfft - 1) % nfft];
  const float y0 = re[kp];
  const float yp = re[(kp + 1) % nfft];
  const float den = ym - 2.0f * y0 + yp;
  float d = (den != 0.0f) ? 0.5f * (ym - yp) / den : 0.0f;
  if (d > 0.5f) d = 0.5f;
  if (d < -0.5f) d = -0.5f;

  double idx = static_cast<double>(kp) + static_cast<double>(d);
  if (kp >= nfft / 2) idx -= static_cast<double>(nfft);    // negative frequencies
  s.peak_hz = static_cast<float>(idx * static_cast<double>(rate_hz) / static_cast<double>(nfft));
  s.peak_amp = y0 - 0.25f * (ym - yp) * d;

  // Noise: the median magnitude away from the line and away from DC. The
  // exclusion window is wide enough to clear the skirts of the Hann peak.
  const uint32_t skirt = nfft / 64 + 4;
  uint32_t m = 0;
  for (uint32_t k = 0; k < nfft; k++) {
    if (k <= kDcGuard || k + kDcGuard >= nfft) continue;
    uint32_t dist = (k > kp) ? (k - kp) : (kp - k);
    if (dist > nfft / 2) dist = nfft - dist;              // the spectrum wraps
    if (dist <= skirt) continue;
    im[m++] = re[k];
  }
  if (m >= 8) {
    std::nth_element(im, im + m / 2, im + m);
    s.noise_rms = im[m / 2] / kRayleighMedian;
  }
  if (s.noise_rms > 0.0f && s.peak_amp > 0.0f) {
    s.snr_db = 20.0f * log10f(s.peak_amp / s.noise_rms);
  }
  return s;
}

}  // namespace dsp


