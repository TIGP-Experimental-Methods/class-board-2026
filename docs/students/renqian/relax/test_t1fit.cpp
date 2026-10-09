// Tests for firmware/src/relax/T1Fit.h, on the PC.
// Ren Qian (Section A), 2026-10-09.
//
//   g++ -std=c++14 -O2 -Wall -Wextra -o test_t1fit test_t1fit.cpp && ./test_t1fit
//
// The numbers are the simulator's, SPEC.md decision 8: pure water T1 = 2.5 s,
// r1 = 1.0 s^-1 mM^-1, and the five first-round samples of decision 2. A test
// passes on what the fit returns, not on what the code looks like:
//   1. noise-free data comes back exactly
//   2. a curve that never bracketed T1 is refused, not fitted
//   3. with noise, the fit is not biased, and the error bar it reports is the
//      scatter you actually get - an error bar that is too small is worse than none
//   4. the whole chain - coarse scan, plan, fine scan, five samples, r1 - gives
//      back the r1 that was put in
#include "../../../../firmware/src/relax/T1Fit.h"

#include <cmath>
#include <cstdio>
#include <random>
#include <vector>

using namespace t1fit;

static int g_fail = 0;
static void check(bool ok, const char* what) {
  std::printf("  %s  %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) ++g_fail;
}

static const double kT1Water = 2.5;            // s
static const double kR1 = 1.0;                 // s^-1 mM^-1
static const double kConc[5] = {0, 1, 2, 5, 10};
static double t1Of(double c) { return 1.0 / (1.0 / kT1Water + kR1 * c); }

// The shortest pulse-to-pulse TR the sequencer can manage with a short record.
// An ASSUMPTION until it is measured on the board: pulse + dead time + a 20 ms
// record + processing.
static const double kTrMin = 0.03, kTrMax = 600;

struct Stats {
  double sum = 0, sum2 = 0;
  int n = 0;
  void add(double v) { sum += v; sum2 += v * v; ++n; }
  double mean() const { return sum / n; }
  double sd() const { return std::sqrt(std::max(0.0, sum2 / n - mean() * mean())); }
};

// One sample, the way the instrument will do it: coarse, plan, fine.
static T1Result measure(double t1, double s0, double sigma, std::mt19937& rng) {
  std::normal_distribution<double> noise(0.0, sigma);
  double s[8], tr[8];
  for (int i = 0; i < 3; ++i) s[i] = s0 * (1 - std::exp(-kCoarseTR[i] / t1)) + noise(rng);
  const T1Result coarse = fitT1(kCoarseTR, s, 3);
  const double est = coarse.ok ? coarse.t1_s : 1.0;
  planTR(est, kTrMin, kTrMax, tr, 8);
  for (int i = 0; i < 8; ++i) s[i] = s0 * (1 - std::exp(-tr[i] / t1)) + noise(rng);
  return fitT1(tr, s, 8);
}

// The same by inversion recovery: a coarse estimate from 3 points assuming a
// perfect inversion, then 8 taus and the 3-parameter fit. b_over_a < 2 is a
// short 180.
static IRResult measureIR(double t1, double a, double b_over_a, double sigma, std::mt19937& rng) {
  std::normal_distribution<double> noise(0.0, sigma);
  double s[8], tau[8];
  for (int i = 0; i < 3; ++i) s[i] = a * (1 - 2 * std::exp(-kCoarseTR[i] / t1)) + noise(rng);
  const T1Result coarse = fitT1(kCoarseTR, s, 3, 2.0);
  planIR(coarse.ok ? coarse.t1_s : 1.0, kTrMin, kTrMax, tau);
  for (int i = 0; i < 8; ++i) s[i] = a * (1 - b_over_a * std::exp(-tau[i] / t1)) + noise(rng);
  return fitIR(tau, s, 8);
}

int main() {
  std::printf("T1Fit tests - water T1 %.1f s, r1 %.1f s^-1 mM^-1, samples 0 1 2 5 10 mM\n",
              kT1Water, kR1);

  // ---- 1. noise-free --------------------------------------------------------
  std::printf("\n1. noise-free data comes back exactly\n");
  for (double c : kConc) {
    const double t1 = t1Of(c);
    double tr[8], s[8];
    planTR(t1, kTrMin, kTrMax, tr, 8);
    for (int i = 0; i < 8; ++i) s[i] = 2.0 * (1 - std::exp(-tr[i] / t1));
    const T1Result r = fitT1(tr, s, 8);
    char msg[160];
    std::snprintf(msg, sizeof msg, "%4.0f mM: T1 %.6f s (true %.6f), S0 %.6f, TRs %.3f..%.2f s",
                  c, r.t1_s, t1, r.s0, tr[0], tr[7]);
    check(r.ok && r.range_ok && std::fabs(r.t1_s / t1 - 1) < 1e-6 && std::fabs(r.s0 / 2.0 - 1) < 1e-6, msg);
  }

  // ---- 2. refusals ------------------------------------------------------------
  std::printf("\n2. what it must refuse\n");
  {
    const double tr[3] = {0.1, 0.5, 3.0};
    double s[3];
    for (int i = 0; i < 3; ++i) s[i] = 1 - std::exp(-tr[i] / 1000.0);  // T1 = 1000 s
    const T1Result r = fitT1(tr, s, 3);
    check(!r.ok || !r.range_ok, "T1 = 1000 s against TRs of 0.1-3 s: not reported as a good fit");
    check(!fitT1(tr, s, 2).ok, "two points: refused");
  }
  {
    const double tr[8] = {0.03, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2};
    double s[8];
    for (int i = 0; i < 8; ++i) s[i] = 1 - std::exp(-tr[i] / 2.5);
    const T1Result r = fitT1(tr, s, 8);
    check(r.ok && !r.range_ok, "T1 2.5 s with TRs only to 3.2 s: fitted, but flagged - the curve never levelled off");
  }

  // ---- 3. noise, one sample at a time ----------------------------------------
  // sigma relative to S0 = 1: SNR 500 is what the requirements register expects
  // after filtering (R-35); SNR 100 is a pessimistic day.
  const int kTrials = 2000;
  std::mt19937 rng(20261009);
  for (double snr : {500.0, 100.0}) {
    std::printf("\n3. %d noisy repeats per sample, SNR %.0f\n", kTrials, snr);
    std::printf("   %6s %9s %9s %9s %9s %9s\n", "mM", "T1 true", "bias %", "scatter%", "errbar %", "bar/scat");
    for (double c : kConc) {
      const double t1 = t1Of(c);
      Stats fit, bar;
      int bad = 0;
      for (int k = 0; k < kTrials; ++k) {
        const T1Result r = measure(t1, 1.0, 1.0 / snr, rng);
        if (!r.ok || !r.range_ok) { ++bad; continue; }
        fit.add(r.t1_s / t1 - 1);
        bar.add(r.t1_err / t1);
      }
      const double ratio = bar.mean() / fit.sd();
      std::printf("   %6.0f %9.3f %9.3f %9.3f %9.3f %9.2f\n", c, t1,
                  100 * fit.mean(), 100 * fit.sd(), 100 * bar.mean(), ratio);
      char msg[200];
      std::snprintf(msg, sizeof msg,
                    "%4.0f mM: bias within 3 standard errors + 0.1%%, error bar 0.8-1.2x the scatter, %d failed fits",
                    c, bad);
      const double se = fit.sd() / std::sqrt(double(fit.n));
      check(bad == 0 && std::fabs(fit.mean()) < 3 * se + 0.001 && ratio > 0.8 && ratio < 1.2, msg);
    }
  }

  // ---- 4. the whole chain: five samples -> r1 --------------------------------
  for (double snr : {500.0, 100.0}) {
    std::printf("\n4. the whole chain, %d repeats, SNR %.0f: does r1 come back as %.1f?\n", kTrials, snr, kR1);
    Stats r1, r1bar, icpt;
    for (int k = 0; k < kTrials; ++k) {
      T1Result res[5];
      for (int i = 0; i < 5; ++i) res[i] = measure(t1Of(kConc[i]), 1.0, 1.0 / snr, rng);
      const LineResult L = relaxivity(kConc, res, 5);
      if (!L.ok) continue;
      r1.add(L.slope); r1bar.add(L.slope_err); icpt.add(L.icpt);
    }
    std::printf("   r1 = %.4f +- %.4f (scatter), mean error bar %.4f; 1/T1(water) = %.4f (true %.4f)\n",
                r1.mean(), r1.sd(), r1bar.mean(), icpt.mean(), 1 / kT1Water);
    const double se = r1.sd() / std::sqrt(double(r1.n));
    check(r1.n == kTrials, "every repeat produced an r1");
    check(std::fabs(r1.mean() - kR1) < 3 * se + 0.001 * kR1, "r1 unbiased");
    check(r1bar.mean() / r1.sd() > 0.8 && r1bar.mean() / r1.sd() < 1.5,
          "r1 error bar 0.8-1.5x its scatter (6 degrees of freedom per sample make it run a few % small)");
  }

  // ---- time budget, for the progress screen ----------------------------------
  std::printf("\n5. how long one fine scan takes, 2 dummy + 4 recorded pulses per TR\n");
  for (double c : kConc) {
    double tr[8];
    planTR(t1Of(c), kTrMin, kTrMax, tr, 8);
    std::printf("   %4.0f mM: %6.1f s\n", c, scanSeconds(tr, 8, 2, 4));
  }

  // ---- 6. inversion recovery, the method bloch_check.cpp says to use --------
  std::printf("\n6. inversion recovery: noise-free, with a perfect and a short 180\n");
  for (double boa : {2.0, 1.8}) {
    for (double c : kConc) {
      const double t1 = t1Of(c);
      double tau[8], s[8];
      planIR(t1, kTrMin, kTrMax, tau);
      for (int i = 0; i < 8; ++i) s[i] = 1.5 * (1 - boa * std::exp(-tau[i] / t1));
      const IRResult r = fitIR(tau, s, 8);
      char msg[160];
      std::snprintf(msg, sizeof msg, "b/a %.1f, %4.0f mM: T1 %.6f (true %.6f), inversion %.4f",
                    boa, c, r.t1_s, t1, r.inversion);
      check(r.ok && r.range_ok && std::fabs(r.t1_s / t1 - 1) < 1e-6 && std::fabs(r.inversion - boa) < 1e-6, msg);
    }
  }
  {
    const double tau[3] = {0.1, 0.5, 3.0}, s3[3] = {-1, 0, 1};
    check(!fitIR(tau, s3, 3).ok, "IR with three points: refused (three parameters need four)");
  }

  for (double snr : {500.0, 100.0}) {
    std::printf("\n6. IR, %d noisy repeats, SNR %.0f, a short 180 (b/a 1.8)\n", kTrials, snr);
    std::printf("   %6s %9s %9s %9s %9s %9s\n", "mM", "T1 true", "bias %", "scatter%", "errbar %", "bar/scat");
    for (double c : kConc) {
      const double t1 = t1Of(c);
      Stats fit, bar;
      int bad = 0;
      for (int k = 0; k < kTrials; ++k) {
        const IRResult r = measureIR(t1, 1.0, 1.8, 1.0 / snr, rng);
        if (!r.ok || !r.range_ok) { ++bad; continue; }
        fit.add(r.t1_s / t1 - 1);
        bar.add(r.t1_err / t1);
      }
      const double ratio = bar.mean() / fit.sd();
      std::printf("   %6.0f %9.3f %9.3f %9.3f %9.3f %9.2f\n", c, t1,
                  100 * fit.mean(), 100 * fit.sd(), 100 * bar.mean(), ratio);
      char msg[200];
      std::snprintf(msg, sizeof msg, "%4.0f mM: unbiased, error bar 0.8-1.2x the scatter, %d failed fits", c, bad);
      const double se = fit.sd() / std::sqrt(double(fit.n));
      check(bad == 0 && std::fabs(fit.mean()) < 3 * se + 0.001 && ratio > 0.8 && ratio < 1.2, msg);
    }
    Stats r1, r1bar;
    for (int k = 0; k < kTrials; ++k) {
      IRResult res[5];
      for (int i = 0; i < 5; ++i) res[i] = measureIR(t1Of(kConc[i]), 1.0, 1.8, 1.0 / snr, rng);
      const LineResult L = relaxivity(kConc, res, 5);
      if (!L.ok) continue;
      r1.add(L.slope); r1bar.add(L.slope_err);
    }
    std::printf("   whole chain: r1 = %.4f +- %.4f (scatter), mean error bar %.4f\n", r1.mean(), r1.sd(), r1bar.mean());
    const double se = r1.sd() / std::sqrt(double(r1.n));
    check(r1.n == kTrials && std::fabs(r1.mean() - kR1) < 3 * se + 0.001 * kR1, "IR whole chain: r1 comes back as 1.0");
    check(r1bar.mean() / r1.sd() > 0.8 && r1bar.mean() / r1.sd() < 1.5, "IR whole chain: r1 error bar 0.8-1.5x its scatter");
  }

  std::printf("\n7. how long one IR scan takes: 8 taus, 4 shots each, 50 ms + a 4 T1 wait per shot\n");
  for (double c : kConc) {
    double tau[8];
    planIR(t1Of(c), kTrMin, kTrMax, tau);
    std::printf("   %4.0f mM: %6.1f s\n", c, scanSecondsIR(tau, 8, t1Of(c), 4));
  }

  // ---- 8. one T1 from the coarse and the fine scan together -------------------
  // The two scans wait differently, so each has its own a and b; T1 is shared.
  // Coarse: kCoarseTau, a = 0.7, b = 1.3. Fine: planIR, a = 1.0, b = 1.8.
  std::printf("\n8. joint coarse + fine fit (fitIRGroups)\n");
  {
    double tau[8], s[8];
    planIR(0.7, kTrMin, kTrMax, tau);
    for (int i = 0; i < 8; ++i) s[i] = 1.2 * (1 - 1.9 * std::exp(-tau[i] / 0.7));
    int g[8] = {0, 0, 0, 0, 0, 0, 0, 0};
    const IRResult a = fitIR(tau, s, 8);
    const IRGroupResult b = fitIRGroups(tau, s, g, nullptr, 8);
    check(b.ok && std::fabs(b.t1_s / a.t1_s - 1) < 1e-9 && std::fabs(b.t1_err - a.t1_err) < 1e-9 * a.t1_s + 1e-15,
          "one group: the same T1 and error as fitIR");
  }
  for (double c : kConc) {
    const double t1 = t1Of(c);
    double tau[12], s[12];
    int g[12];
    for (int i = 0; i < 4; ++i) { tau[i] = kCoarseTau[i]; g[i] = 0; s[i] = 0.7 - 1.3 * std::exp(-tau[i] / t1); }
    planIR(t1, kTrMin, kTrMax, tau + 4);
    for (int i = 4; i < 12; ++i) { g[i] = 1; s[i] = 1.0 - 1.8 * std::exp(-tau[i] / t1); }
    const IRGroupResult r = fitIRGroups(tau, s, g, nullptr, 12);
    char msg[200];
    std::snprintf(msg, sizeof msg, "%4.0f mM, noise-free: T1 %.6f (true %.6f), a %.4f/%.4f b %.4f/%.4f",
                  c, r.t1_s, t1, r.a[0], r.a[1], r.b[0], r.b[1]);
    check(r.ok && std::fabs(r.t1_s / t1 - 1) < 1e-6 && std::fabs(r.a[0] - 0.7) < 1e-6 && std::fabs(r.b[1] - 1.8) < 1e-6, msg);
  }
  {
    const double tau[5] = {0.1, 0.2, 0.4, 0.8, 1.6}, s5[5] = {-1, -0.5, 0, 0.5, 0.8};
    const int g5[5] = {0, 0, 0, 0, 1};
    check(!fitIRGroups(tau, s5, g5, nullptr, 5).ok, "a group with one point: refused");
  }
  // With noise: coarse 4 shots, fine scanned twice (8 shots) - weights 4 and 8.
  // The joint fit must be unbiased, honest about its error, and better than the
  // fine scan alone, since it uses the coarse scan's points as well.
  for (double snr : {100.0}) {
    std::printf("   %d noisy repeats, SNR %.0f per shot\n", kTrials, snr);
    std::normal_distribution<double> unit(0.0, 1.0);
    const double sig = 1.0 / snr;
    for (double c : kConc) {
      const double t1 = t1Of(c);
      Stats joint, fine, bar;
      for (int k = 0; k < kTrials; ++k) {
        double tau[12], s[12], w[12];
        int g[12];
        for (int i = 0; i < 4; ++i) {
          tau[i] = kCoarseTau[i]; g[i] = 0; w[i] = 4;
          s[i] = 0.7 - 1.3 * std::exp(-tau[i] / t1) + unit(rng) * sig / 2;
        }
        planIR(t1, kTrMin, kTrMax, tau + 4);
        for (int i = 4; i < 12; ++i) {
          g[i] = 1; w[i] = 8;
          s[i] = 1.0 - 1.8 * std::exp(-tau[i] / t1) + unit(rng) * sig / std::sqrt(8.0);
        }
        const IRGroupResult r = fitIRGroups(tau, s, g, w, 12);
        const IRResult f = fitIR(tau + 4, s + 4, 8);
        if (!r.ok || !f.ok) continue;
        joint.add(r.t1_s / t1 - 1); bar.add(r.t1_err / t1); fine.add(f.t1_s / t1 - 1);
      }
      const double ratio = bar.mean() / joint.sd(), se = joint.sd() / std::sqrt(double(joint.n));
      char msg[220];
      std::snprintf(msg, sizeof msg, "%4.0f mM: joint scatter %.3f%% vs fine alone %.3f%%, bias %.3f%%, bar/scatter %.2f",
                    c, 100 * joint.sd(), 100 * fine.sd(), 100 * joint.mean(), ratio);
      check(joint.n == kTrials && std::fabs(joint.mean()) < 3 * se + 0.001 && ratio > 0.8 && ratio < 1.2 &&
                joint.sd() <= fine.sd(), msg);
    }
  }

  std::printf("\n%s: %d failure(s)\n", g_fail ? "FAILED" : "ALL PASSED", g_fail);
  return g_fail ? 1 : 0;
}
