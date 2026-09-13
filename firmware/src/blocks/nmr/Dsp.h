// Dsp - the arithmetic of one NMR scan. NMR-FIRMWARE.md section 3.3.
//
// Everything here is a plain function on plain arrays: no Arduino, no FreeRTOS,
// no allocation, no globals. That is deliberate. The signal processing is the
// part most likely to be wrong in a way the hardware cannot tell you about, so
// it has to be testable on a PC with a synthetic record and a known answer
// (compile Dsp.cpp with any C++ compiler and call analyse()).
//
// Conventions used throughout:
//   * A "complex record" is 2 x n floats, interleaved I, Q, I, Q, ... in volts
//     at the ADC input. That is also exactly the payload of the kind-3 binary
//     frame, so the averaged record never has to be copied to be sent.
//   * A "raw record" is 2 x n int16 in ADC codes, interleaved I, Q, because
//     that is the order the ADS8688 auto-scan returns channels 7 and 8 in.
//   * Frequencies are signed and relative to the local oscillator: positive
//     means the line sits above the LO. The Larmor frequency is f_lo + peak.
#pragma once
#include <stdint.h>

namespace dsp {

// Mean of one interleaved channel (stride 2), in ADC codes.
float meanI16(const int16_t* first, uint32_t n, uint32_t stride);

// Where to measure the DC offset. The receiver is blanked before the pulse, so
// the offset cannot be measured before the signal arrives: it has to come from
// a part of the record where the free induction decay is already gone. For a
// record of a second or more that is the last tenth (T2* in water at 2 mT is a
// few hundred milliseconds); a shorter record has no quiet tail, so the whole
// record is used and a little of the signal is subtracted with the offset.
// Returns the index of the first sample to average over.
uint32_t dcStart(uint32_t n, uint32_t t_acq_ms);

// Boxcar-decimate: each output complex sample is the mean of `decim` raw pairs,
// with the DC offset removed and the ADC code converted to volts. Averaging
// `decim` samples is also a (crude) anti-alias filter - crude because its
// response only falls as sin(x)/x, which costs 0.6 dB at 5.4 kHz for decim 4 at
// 100 kS/s. That is the price of a filter that costs one add per sample.
void decimate(const int16_t* rawIq, uint32_t nOut, uint32_t decim,
              float dcI, float dcQ, float voltsPerCodeI, float voltsPerCodeQ,
              float* outIq);

// Rotate every complex sample by `deg`. CYCLOPS moves the transmitter phase
// from scan to scan; the received signal follows it, so the record is rotated
// back by the pulse phase before averaging. Anything that does not follow the
// pulse - amplifier offset, mains hum, converter glitches - does not line up
// and averages away. That is the whole point of the phase cycle.
void rotate(float* zIq, uint32_t n, float deg);

// Running mean over the scan set: acc <- acc + (z - acc) / (scansDone + 1).
// Kept as a mean rather than a sum so the record is in volts after every scan
// and the app can draw it while the set is still running.
void accumulateMean(float* accIq, const float* zIq, uint32_t n, uint32_t scansDone);

// Transform length: the next power of two at or above n, clamped to maxN
// (and to at least 8). A record longer than maxN is analysed over its first
// maxN samples - which is where the signal is anyway.
uint32_t fftLength(uint32_t n, uint32_t maxN);

// Radix-2 complex FFT, in place, n a power of two. Decimation in time with a
// bit-reversal permutation first - the textbook version, because a student
// should be able to read it next to the textbook.
void fft(float* re, float* im, uint32_t n);

struct Spectrum {
  float peak_hz;    // signed, relative to the LO (positive = above it)
  float peak_amp;   // height of the line, V rms in one quadrature
  float noise_rms;  // the same measure, away from the line
  float snr_db;     // 20 log10(peak_amp / noise_rms)
};
// peak_amp is a figure of merit, not the amplitude of the signal in the coil: a
// decay spreads its energy over as many bins as it is wide, so a short-lived
// line reads lower than a long-lived one of the same height. What it is good
// for is comparing one scan set with the next, and for the SNR, which is what
// the status line shows and what tells you averaging is working.

// Hann-windowed spectrum of a complex record, and the line in it.
// `re` and `im` are scratch of nfft floats each (the caller owns them, so this
// function allocates nothing); they hold the magnitude spectrum on return.
// `rate_hz` is the decimated sample rate of zIq.
Spectrum analyse(const float* zIq, uint32_t n, float rate_hz,
                 float* re, float* im, uint32_t nfft);

}  // namespace dsp
