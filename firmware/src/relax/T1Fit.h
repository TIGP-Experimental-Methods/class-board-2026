// T1Fit - the arithmetic of a T1 measurement by progressive saturation, and of
// the relaxivity that comes out of several of them.
// Ren Qian (Section A), 2026-10-09. docs/students/renqian/relax/SPEC.md.
//
// Header-only, and free of hardware, heap and exceptions, so the same file runs
// on the ESP32-S3 and in the PC test beside the spec (test_t1fit.cpp). Nothing
// here includes a block, so it compiles whether or not the nmr block ever grows
// a T1 mode.
//
// It does not care where the numbers come from, but it insists on one thing:
// TR is the MEASURED pulse-to-pulse time. The sequencer's t_repeat_ms starts
// counting only after a scan has been recorded and processed (Sequencer.cpp,
// the n_avg loop), so the real interval is t_repeat_ms plus the record plus the
// processing, and the processing time is not fixed. Fitting against
// t_repeat_ms would put every point in the wrong place.
#pragma once
#include <math.h>

namespace t1fit {

// ---- one sample: S = S0 (1 - k exp(-TR/T1)) -----------------------------------
// k = 1 is progressive saturation, the method SPEC.md chose; TR is pulse to pulse.
// k = 2 is inversion recovery, 180 - tau - 90 from full recovery, with tau passed
// in place of TR; kept because bloch_check.cpp compares the two.

struct T1Result {
  bool ok = false;        // false: fewer than 3 points, or the minimum ran off the
                          // edge of the search - the TRs never bracketed T1
  bool range_ok = false;  // the TRs reach below T1 and past 3 T1, so the curve was
                          // seen both rising and levelling off
  double s0 = 0, s0_err = 0;
  double t1_s = 0, t1_err = 0;
  double rms = 0;         // residual rms, in the units of S
  int n = 0;
};

namespace detail {
// For a fixed T1 the best S0 is a linear least-squares answer, so the fit only
// has to search one dimension (variable projection). Returns the residual sum
// of squares, and writes the S0 that achieves it.
inline double rssAt(const double* tr, const double* s, int n, double t1, double* s0, double k) {
  double sff = 0, ssf = 0;
  for (int i = 0; i < n; ++i) {
    const double f = 1.0 - k * exp(-tr[i] / t1);
    sff += f * f;
    ssf += s[i] * f;
  }
  *s0 = sff > 0 ? ssf / sff : 0;
  double rss = 0;
  for (int i = 0; i < n; ++i) {
    const double r = s[i] - *s0 * (1.0 - k * exp(-tr[i] / t1));
    rss += r * r;
  }
  return rss;
}
}  // namespace detail

inline T1Result fitT1(const double* tr_s, const double* s, int n, double k = 1.0) {
  T1Result R;
  R.n = n;
  if (n < 3) return R;
  double trMin = tr_s[0], trMax = tr_s[0];
  for (int i = 1; i < n; ++i) {
    if (tr_s[i] < trMin) trMin = tr_s[i];
    if (tr_s[i] > trMax) trMax = tr_s[i];
  }
  if (!(trMin > 0) || !(trMax > trMin)) return R;

  // Search ln T1 from trMin/20 to 20 trMax: a grid first, so a noisy curve with
  // two shallow minima cannot trap the refinement, then golden section round
  // the best grid point.
  const double lo = log(trMin / 20), hi = log(trMax * 20);
  const int G = 64;
  int best = 0;
  double bestRss = 1e300, s0 = 0;
  for (int j = 0; j <= G; ++j) {
    const double r = detail::rssAt(tr_s, s, n, exp(lo + (hi - lo) * j / G), &s0, k);
    if (r < bestRss) { bestRss = r; best = j; }
  }
  if (best == 0 || best == G) return R;  // ran off the edge: T1 not bracketed

  double a = lo + (hi - lo) * (best - 1) / G, b = lo + (hi - lo) * (best + 1) / G;
  const double g = 0.6180339887498949;
  double c = b - g * (b - a), d = a + g * (b - a);
  double fc = detail::rssAt(tr_s, s, n, exp(c), &s0, k);
  double fd = detail::rssAt(tr_s, s, n, exp(d), &s0, k);
  for (int it = 0; it < 200 && (b - a) > 1e-12; ++it) {
    if (fc < fd) { b = d; d = c; fd = fc; c = b - g * (b - a); fc = detail::rssAt(tr_s, s, n, exp(c), &s0, k); }
    else         { a = c; c = d; fc = fd; d = a + g * (b - a); fd = detail::rssAt(tr_s, s, n, exp(d), &s0, k); }
  }
  const double t1 = exp(0.5 * (a + b));
  const double rss = detail::rssAt(tr_s, s, n, t1, &s0, k);

  // Uncertainties from the Jacobian at the minimum: dS/dS0 = f and
  // dS/dT1 = -S0 k exp(-TR/T1) TR / T1^2; covariance = sigma^2 (J^T J)^-1, with
  // sigma^2 estimated from the residuals on n - 2 degrees of freedom.
  double aa = 0, ab = 0, bb = 0;
  for (int i = 0; i < n; ++i) {
    const double e = exp(-tr_s[i] / t1);
    const double f = 1.0 - k * e, h = -s0 * k * e * tr_s[i] / (t1 * t1);
    aa += f * f; ab += f * h; bb += h * h;
  }
  const double det = aa * bb - ab * ab;
  if (!(det > 0)) return R;
  const double sig2 = rss / (n - 2);
  R.ok = true;
  R.range_ok = trMin <= t1 && trMax >= 3 * t1;
  R.s0 = s0;
  R.t1_s = t1;
  R.s0_err = sqrt(sig2 * bb / det);
  R.t1_err = sqrt(sig2 * aa / det);
  R.rms = sqrt(rss / n);
  return R;
}

// ---- inversion recovery with the inversion left free: S = a - b exp(-tau/T1) --
// A perfect 180 gives b = 2a; a short one gives less. Fitting b instead of
// assuming 2a keeps T1 right when t90 is off: bloch_check.cpp has the fixed
// k = 2 fit 6-8% low with pulses 10% short. inversion = b/a, 2 when perfect,
// is worth showing - it is a calibration check on t180 that comes for free.
// S must be signed (phase-sensitive): an inversion recovery passes through zero.

struct IRResult {
  bool ok = false, range_ok = false;
  double a = 0, b = 0;
  double t1_s = 0, t1_err = 0;
  double inversion = 0;  // b / a
  double rms = 0;
  int n = 0;
};

namespace detail {
// For a fixed T1, a and b are linear least squares: S = a + c e with c = -b.
inline double rssIR(const double* tau, const double* s, int n, double t1, double* a, double* c) {
  double se = 0, see = 0, ss = 0, sse = 0;
  for (int i = 0; i < n; ++i) {
    const double e = exp(-tau[i] / t1);
    se += e; see += e * e; ss += s[i]; sse += s[i] * e;
  }
  const double det = n * see - se * se;
  if (!(det > 0)) { *a = 0; *c = 0; return 1e300; }
  *a = (see * ss - se * sse) / det;
  *c = (n * sse - se * ss) / det;
  double rss = 0;
  for (int i = 0; i < n; ++i) {
    const double r = s[i] - *a - *c * exp(-tau[i] / t1);
    rss += r * r;
  }
  return rss;
}
}  // namespace detail

inline IRResult fitIR(const double* tau_s, const double* s, int n) {
  IRResult R;
  R.n = n;
  if (n < 4) return R;  // three parameters; four points is the least that tests them
  double tMin = tau_s[0], tMax = tau_s[0];
  for (int i = 1; i < n; ++i) {
    if (tau_s[i] < tMin) tMin = tau_s[i];
    if (tau_s[i] > tMax) tMax = tau_s[i];
  }
  if (!(tMin > 0) || !(tMax > tMin)) return R;
  const double lo = log(tMin / 20), hi = log(tMax * 20);
  const int G = 64;
  int best = 0;
  double bestRss = 1e300, a = 0, c = 0;
  for (int j = 0; j <= G; ++j) {
    const double r = detail::rssIR(tau_s, s, n, exp(lo + (hi - lo) * j / G), &a, &c);
    if (r < bestRss) { bestRss = r; best = j; }
  }
  if (best == 0 || best == G) return R;
  double l = lo + (hi - lo) * (best - 1) / G, u = lo + (hi - lo) * (best + 1) / G;
  const double g = 0.6180339887498949;
  double p = u - g * (u - l), q = l + g * (u - l);
  double fp = detail::rssIR(tau_s, s, n, exp(p), &a, &c);
  double fq = detail::rssIR(tau_s, s, n, exp(q), &a, &c);
  for (int it = 0; it < 200 && (u - l) > 1e-12; ++it) {
    if (fp < fq) { u = q; q = p; fq = fp; p = u - g * (u - l); fp = detail::rssIR(tau_s, s, n, exp(p), &a, &c); }
    else         { l = p; p = q; fp = fq; q = l + g * (u - l); fq = detail::rssIR(tau_s, s, n, exp(q), &a, &c); }
  }
  const double t1 = exp(0.5 * (l + u));
  const double rss = detail::rssIR(tau_s, s, n, t1, &a, &c);

  // Covariance of (a, c, T1) from the Jacobian: columns 1, e, c e tau / T1^2.
  double M[3][3] = {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}};
  for (int i = 0; i < n; ++i) {
    const double e = exp(-tau_s[i] / t1);
    const double J[3] = {1.0, e, c * e * tau_s[i] / (t1 * t1)};
    for (int r = 0; r < 3; ++r)
      for (int k = 0; k < 3; ++k) M[r][k] += J[r] * J[k];
  }
  const double det = M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
                   - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
                   + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]);
  if (!(det > 0)) return R;
  const double inv22 = (M[0][0] * M[1][1] - M[0][1] * M[1][0]) / det;  // (M^-1)[2][2]
  const double sig2 = rss / (n - 3);
  R.ok = true;
  R.range_ok = tMin <= t1 && tMax >= 3 * t1;
  R.a = a;
  R.b = -c;
  R.t1_s = t1;
  R.t1_err = sqrt(sig2 * inv22);
  R.inversion = a != 0 ? -c / a : 0;
  R.rms = sqrt(rss / n);
  return R;
}

// ---- choosing the TRs ------------------------------------------------------------

// The coarse scan: three TRs that between them bracket a T1 anywhere from about
// 50 ms (10 mM Cu2+ is about 0.1 s) to about 10 s (pure water is about 2.5 s).
static const double kCoarseTR[3] = {0.1, 0.5, 3.0};

// The fine scan: n TRs spaced evenly in log from lo*T1 to hi*T1, each clamped to
// what the sequencer can actually do. Returns how many were written.
inline int planTR(double t1_est_s, double tr_min_s, double tr_max_s, double* tr_out, int n,
                  double lo = 0.1, double hi = 5.0) {
  if (n < 2 || !(t1_est_s > 0) || !(hi > lo)) return 0;
  for (int k = 0; k < n; ++k) {
    const double tr = t1_est_s * lo * pow(hi / lo, double(k) / (n - 1));
    tr_out[k] = tr < tr_min_s ? tr_min_s : (tr > tr_max_s ? tr_max_s : tr);
  }
  return n;
}

// How long a set of TRs takes, for the progress screen: every TR gets n_dummy
// unrecorded pulses to reach steady state, then n_avg recorded ones.
inline double scanSeconds(const double* tr_s, int n, int n_dummy, int n_avg) {
  double t = 0;
  for (int i = 0; i < n; ++i) t += tr_s[i] * (n_dummy + n_avg);
  return t;
}

// ---- the inversion-recovery protocol (SPEC.md decision 3) ---------------------------
// Chosen by optimize_ir.cpp, which scores r1's error per second of measuring
// in the Bloch model under four hardware cases (optimize_ir.log). Starting
// from 0.1 - 5 T1 with a 5 T1 wait, two changes survived:
//   shortest tau 0.1 -> 0.02 T1   ~8 % better, and r1 bias fell 0.33 -> 0.24 %:
//                                 the start of the recovery is where it is steepest
//   wait 5 -> 4 T1                ~8 % more, but r1 bias rose to 0.48 %, against
//                                 a 0.5 % limit - a trade chosen in SPEC.md
// The 3-parameter fit is what makes a shorter wait possible at all: with a
// constant wait every shot starts from the same partly recovered state, which
// only changes a and b, not the shape.
static const int kIRPoints = 8;
static const double kIRLo = 0.02, kIRHi = 5.0;   // tau range, x T1 estimate
static const double kIRWait = 4.0;               // after each shot, x T1 estimate
static const int kIRAvg = 4;                     // one CYCLOPS cycle per point

// Fit T1 from the coarse and the fine scan together (fitIRGroups), not from
// the fine scan alone. optimize_ir.cpp round 2, Monte Carlo over 2000 sets in a
// 30 minute budget: r1's error 0.37 -> 0.31 %, its bias 0.48 -> 0.35 %, and the
// reported error bar 0.92 -> 0.98 of the real scatter. It wins on all three,
// and it gives back the bias that the 4 T1 wait cost.
static const bool kIRJointFit = true;

// The coarse scan in front of it, also from optimize_ir.cpp round 0. A 1 s wait
// read pure water's T1 at half its value (the previous shot's transverse
// magnetization had not gone); 3 s and one unrecorded shot per tau keeps every
// estimate within x1.00 - x1.14 under all four hardware cases.
static const double kCoarseTau[4] = {0.01, 0.1, 0.5, 2.5};
static const double kCoarseWaitS = 3.0;
static const int kCoarseDummy = 1, kCoarseAvg = 4;

inline int planIR(double t1_est_s, double tau_min_s, double tau_max_s, double* tau_out) {
  return planTR(t1_est_s, tau_min_s, tau_max_s, tau_out, kIRPoints, kIRLo, kIRHi);
}

// How long an inversion-recovery scan takes, for the progress screen: every shot
// is 180 - tau - 90, then the record, then the wait.
inline double scanSecondsIR(const double* tau_s, int n, double t1_est_s, int n_avg,
                            double wait = kIRWait, double per_shot_s = 0.05) {
  double t = 0;
  for (int i = 0; i < n; ++i) t += (tau_s[i] + per_shot_s + wait * t1_est_s) * n_avg;
  return t;
}

// ---- one T1 from several scans: S = a_g - b_g exp(-tau/T1) --------------------------
// The coarse scan and the fine scan wait differently, so they have different a
// and b - but the same T1. Fitting them together keeps the coarse scan's
// information instead of throwing it away. g[i] says which scan point i is
// from (0 .. kMaxGroups-1); w[i] is its weight, proportional to 1/sigma^2
// (number of shots averaged), or null for equal weights.

static const int kMaxGroups = 4;

struct IRGroupResult {
  bool ok = false, range_ok = false;
  double t1_s = 0, t1_err = 0;
  double a[kMaxGroups] = {0, 0, 0, 0}, b[kMaxGroups] = {0, 0, 0, 0};
  int groups = 0, n = 0;
  double rms = 0;  // weighted residual rms
};

namespace detail {
// For a fixed T1, each group's a and c (= -b) is a weighted linear least squares
// of its own. Returns the weighted residual sum of squares.
inline double rssGroups(const double* tau, const double* s, const int* g, const double* w, int n,
                        int G, double t1, double* a, double* c) {
  double S0[kMaxGroups] = {0}, S1[kMaxGroups] = {0}, S2[kMaxGroups] = {0}, Y0[kMaxGroups] = {0},
         Y1[kMaxGroups] = {0};
  for (int i = 0; i < n; ++i) {
    const double e = exp(-tau[i] / t1), wi = w ? w[i] : 1.0;
    const int k = g[i];
    S0[k] += wi; S1[k] += wi * e; S2[k] += wi * e * e; Y0[k] += wi * s[i]; Y1[k] += wi * s[i] * e;
  }
  for (int k = 0; k < G; ++k) {
    const double det = S0[k] * S2[k] - S1[k] * S1[k];
    if (!(det > 0)) return 1e300;
    a[k] = (S2[k] * Y0[k] - S1[k] * Y1[k]) / det;
    c[k] = (S0[k] * Y1[k] - S1[k] * Y0[k]) / det;
  }
  double rss = 0;
  for (int i = 0; i < n; ++i) {
    const double r = s[i] - a[g[i]] - c[g[i]] * exp(-tau[i] / t1);
    rss += (w ? w[i] : 1.0) * r * r;
  }
  return rss;
}
}  // namespace detail

inline IRGroupResult fitIRGroups(const double* tau_s, const double* s, const int* g, const double* w,
                                 int n) {
  IRGroupResult R;
  R.n = n;
  int G = 0, count[kMaxGroups] = {0};
  for (int i = 0; i < n; ++i) {
    if (g[i] < 0 || g[i] >= kMaxGroups) return R;
    if (g[i] + 1 > G) G = g[i] + 1;
    ++count[g[i]];
  }
  for (int k = 0; k < G; ++k) if (count[k] < 2) return R;   // a and b need two points each
  R.groups = G;
  if (n < 2 * G + 2) return R;                               // and T1 one more, plus one to test
  double tMin = tau_s[0], tMax = tau_s[0];
  for (int i = 1; i < n; ++i) {
    if (tau_s[i] < tMin) tMin = tau_s[i];
    if (tau_s[i] > tMax) tMax = tau_s[i];
  }
  if (!(tMin > 0) || !(tMax > tMin)) return R;
  double a[kMaxGroups], c[kMaxGroups];
  const double lo = log(tMin / 20), hi = log(tMax * 20);
  const int Gd = 64;
  int best = 0;
  double bestRss = 1e300;
  for (int j = 0; j <= Gd; ++j) {
    const double r = detail::rssGroups(tau_s, s, g, w, n, G, exp(lo + (hi - lo) * j / Gd), a, c);
    if (r < bestRss) { bestRss = r; best = j; }
  }
  if (best == 0 || best == Gd) return R;
  double l = lo + (hi - lo) * (best - 1) / Gd, u = lo + (hi - lo) * (best + 1) / Gd;
  const double gr = 0.6180339887498949;
  double p = u - gr * (u - l), q = l + gr * (u - l);
  double fp = detail::rssGroups(tau_s, s, g, w, n, G, exp(p), a, c);
  double fq = detail::rssGroups(tau_s, s, g, w, n, G, exp(q), a, c);
  for (int it = 0; it < 200 && (u - l) > 1e-12; ++it) {
    if (fp < fq) { u = q; q = p; fq = fp; p = u - gr * (u - l); fp = detail::rssGroups(tau_s, s, g, w, n, G, exp(p), a, c); }
    else         { l = p; p = q; fp = fq; q = l + gr * (u - l); fq = detail::rssGroups(tau_s, s, g, w, n, G, exp(q), a, c); }
  }
  const double t1 = exp(0.5 * (l + u));
  const double rss = detail::rssGroups(tau_s, s, g, w, n, G, t1, a, c);

  // sigma(T1): the T1 information left after each group's own a and c are
  // allowed for - the Schur complement of each group's 2x2 block, summed.
  double M[kMaxGroups][3][3] = {};
  for (int i = 0; i < n; ++i) {
    const double e = exp(-tau_s[i] / t1), wi = w ? w[i] : 1.0;
    const double J[3] = {1.0, e, c[g[i]] * e * tau_s[i] / (t1 * t1)};
    for (int r = 0; r < 3; ++r) for (int k = 0; k < 3; ++k) M[g[i]][r][k] += wi * J[r] * J[k];
  }
  double info = 0;
  for (int k = 0; k < G; ++k) {
    const double d = M[k][0][0] * M[k][1][1] - M[k][0][1] * M[k][1][0];
    if (!(d > 0)) return R;
    const double v0 = M[k][0][2], v1 = M[k][1][2];
    info += M[k][2][2] - (v0 * (M[k][1][1] * v0 - M[k][0][1] * v1) + v1 * (M[k][0][0] * v1 - M[k][1][0] * v0)) / d;
  }
  if (!(info > 0)) return R;
  const double sig2 = rss / (n - (2 * G + 1));
  R.ok = true;
  R.range_ok = tMin <= t1 && tMax >= 3 * t1;
  R.t1_s = t1;
  R.t1_err = sqrt(sig2 / info);
  for (int k = 0; k < G; ++k) { R.a[k] = a[k]; R.b[k] = -c[k]; }
  double wsum = 0;
  for (int i = 0; i < n; ++i) wsum += w ? w[i] : 1.0;
  R.rms = sqrt(rss / wsum);
  return R;
}

// ---- several samples: 1/T1 = 1/T1(solvent) + r1 [M] -----------------------------

struct LineResult {
  bool ok = false;
  double slope = 0, slope_err = 0;  // r1, s^-1 mM^-1
  double icpt = 0, icpt_err = 0;    // 1/T1 of the solvent, s^-1
  double chi2_nu = 0;               // > 1: the points scatter more than their error bars say
  int n = 0;
};

// Weighted straight line y = icpt + slope x. If chi2/nu > 1 the errors are scaled
// up by sqrt(chi2/nu): the scatter, not the error bars, is then the honest
// measure. Any sy <= 0 (a noise-free simulation) falls back to equal weights,
// with the error taken from the residuals.
inline LineResult fitLine(const double* x, const double* y, const double* sy, int n) {
  LineResult L;
  L.n = n;
  if (n < 3) return L;  // two points always fit a line; three is the least that tests it
  bool weighted = true;
  for (int i = 0; i < n; ++i) if (!(sy[i] > 0)) weighted = false;
  double S = 0, Sx = 0, Sy = 0, Sxx = 0, Sxy = 0;
  for (int i = 0; i < n; ++i) {
    const double w = weighted ? 1.0 / (sy[i] * sy[i]) : 1.0;
    S += w; Sx += w * x[i]; Sy += w * y[i]; Sxx += w * x[i] * x[i]; Sxy += w * x[i] * y[i];
  }
  const double D = S * Sxx - Sx * Sx;
  if (!(D > 0)) return L;
  L.slope = (S * Sxy - Sx * Sy) / D;
  L.icpt = (Sxx * Sy - Sx * Sxy) / D;
  double chi2 = 0;
  for (int i = 0; i < n; ++i) {
    const double w = weighted ? 1.0 / (sy[i] * sy[i]) : 1.0;
    const double r = y[i] - L.icpt - L.slope * x[i];
    chi2 += w * r * r;
  }
  L.chi2_nu = chi2 / (n - 2);
  const double scale = weighted ? (L.chi2_nu > 1 ? L.chi2_nu : 1.0) : L.chi2_nu;
  L.slope_err = sqrt(scale * S / D);
  L.icpt_err = sqrt(scale * Sxx / D);
  L.ok = true;
  return L;
}

// r1 from a set of per-sample results. Samples whose T1 fit failed are left
// out. Fixed arrays, no heap: at most kMaxSamples.
static const int kMaxSamples = 16;
inline LineResult relaxivity(const double* conc_mM, const T1Result* t1, int n) {
  double x[kMaxSamples], y[kMaxSamples], sy[kMaxSamples];
  if (n > kMaxSamples) n = kMaxSamples;
  int m = 0;
  for (int i = 0; i < n; ++i) {
    if (!t1[i].ok) continue;
    x[m] = conc_mM[i];
    y[m] = 1.0 / t1[i].t1_s;
    sy[m] = t1[i].t1_err / (t1[i].t1_s * t1[i].t1_s);  // sigma of 1/T1
    ++m;
  }
  return fitLine(x, y, sy, m);
}

// The same from inversion-recovery results.
inline LineResult relaxivity(const double* conc_mM, const IRResult* t1, int n) {
  double x[kMaxSamples], y[kMaxSamples], sy[kMaxSamples];
  if (n > kMaxSamples) n = kMaxSamples;
  int m = 0;
  for (int i = 0; i < n; ++i) {
    if (!t1[i].ok) continue;
    x[m] = conc_mM[i];
    y[m] = 1.0 / t1[i].t1_s;
    sy[m] = t1[i].t1_err / (t1[i].t1_s * t1[i].t1_s);
    ++m;
  }
  return fitLine(x, y, sy, m);
}

// The same from joint coarse + fine fits.
inline LineResult relaxivity(const double* conc_mM, const IRGroupResult* t1, int n) {
  double x[kMaxSamples], y[kMaxSamples], sy[kMaxSamples];
  if (n > kMaxSamples) n = kMaxSamples;
  int m = 0;
  for (int i = 0; i < n; ++i) {
    if (!t1[i].ok) continue;
    x[m] = conc_mM[i];
    y[m] = 1.0 / t1[i].t1_s;
    sy[m] = t1[i].t1_err / (t1[i].t1_s * t1[i].t1_s);
    ++m;
  }
  return fitLine(x, y, sy, m);
}

}  // namespace t1fit
