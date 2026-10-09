// Optimize the inversion-recovery protocol, round after round, until it stops
// getting better.
// Ren Qian (Section A), 2026-10-09.
//
//   g++ -std=c++14 -O2 -Wall -Wextra -pthread -o optimize_ir optimize_ir.cpp && ./optimize_ir
//
// THE SCORE (lower is better): sigma(r1) x sqrt(seconds of FINE scanning), the
// worst of three cases for how good the coarse T1 estimate was (x0.7, x1, x1.4).
// Measuring longer always shrinks sigma by sqrt(time), so this product is the
// precision a protocol buys per second. The coarse scans are left out of it on
// purpose: they cost the same whatever the protocol, and counting them let the
// first version of this program "win" by measuring longer and spreading that
// fixed cost thinner - averages 4 -> 16 scored 10 % better and took 60 min.
// One full pass (five samples, coarse included) must fit in 30 minutes, even
// with the estimate x1.4 long, and the
// result is reported as the error on r1 when the rest of those 20 minutes is
// spent repeating the fine scans.
//
// THE CONSTRAINT: precision may not be bought with bias. Every candidate is run
// through the Bloch model - spins followed pulse by pulse, as in bloch_check.cpp
// - under four hardware cases (ideal, t90 10 % short, 3 Hz off resonance, both)
// times the three estimate cases. The fitted r1 must stay within 0.5 % of the
// true one in all twelve, and every sample's T1 within 3 %.
//
// ONE ROUND: change one thing at a time - number of tau points, their range and
// spacing, the recovery wait, averages, unrecorded shots, phase cycle, order -
// score every change, keep the best one that is allowed. Two rounds in a row
// under 1 % better: try 24 random multi-parameter kicks; if none helps, stop.
//
// ASSUMPTIONS, to be measured on the board: 50 ms per shot for acquisition and
// processing; a coarse scan of 4 taus (0.01, 0.1, 0.5, 2.5 s), 4 shots each,
// 1 s recovery, costing the same for every protocol; single-shot noise 1 % of
// the equilibrium signal (only the scale - the ranking does not depend on it).
// Spin model as bloch_check.cpp: 1/T1 = 0.4 + 1.0 [Cu], 1/T2 = 1/T1 + 0.1,
// T2' = 0.667 s.
#include "../../../../firmware/src/relax/T1Fit.h"

#include <algorithm>
#include <atomic>
#include <cmath>
#include <complex>
#include <cstdio>
#include <cstring>
#include <random>
#include <string>
#include <thread>
#include <vector>

using namespace t1fit;
typedef std::complex<double> cplx;

static const double kPi = 3.14159265358979323846;
static const double kT1Water = 2.5, kR1 = 1.0, kT2p = 0.667;
static const double kConc[5] = {0, 1, 2, 5, 10};
static const double kTacq = 0.0012;      // 90 -> the sample that is read, s
static const double kOverhead = 0.050;   // per shot, acquisition + processing (ASSUMPTION)
static const double kPulses = 0.00125;   // t180 + t90
static const double kTauFloor = 0.005;   // shortest 180 -> 90 the gate allows
static const double kSigmaShot = 0.01;

// The coarse scan, chosen in round 0 (chooseCoarse): wait after each shot, s,
// phase scheme and unrecorded shots per point, as in Protocol.
struct Coarse { double wait; int phase, ndummy; };
static Coarse g_coarse = {kCoarseWaitS, 0, kCoarseDummy};
static const double kBiasR1 = 0.005, kBiasT1 = 0.03;
static const double kBudget = 1800;    // s: all five samples, coarse scans included

struct Imperf { const char* name; double flip_deg, off_hz; };
static const Imperf kImp[4] = {{"ideal", 90, 0}, {"t90 -10%", 81, 0}, {"3 Hz off", 90, 3}, {"both", 81, 3}};
static const double kEstF[3] = {0.7, 1.0, 1.4};

static double t1Of(double c) { return 1 / (1 / kT1Water + kR1 * c); }
static double t2Of(double t1) { return 1 / (1 / t1 + 0.1); }

// ---- the protocol ------------------------------------------------------------------

struct Protocol {
  int n;           // tau points
  double lo, hi;   // tau range, in units of the T1 estimate
  int spacing;     // 0 log, 1 linear, 2 dense at short tau, 3 dense at long tau
  double td;       // wait after each shot, in units of the T1 estimate
  int navg;        // recorded shots per point (4, 8, 16: whole CYCLOPS cycles)
  int ndummy;      // unrecorded shots before them, per point
  int phase;       // 180 phase: 0 fixed, 1 follows the 90's CYCLOPS step, 2 alternates x/-x
  int order;       // 0 ascending tau, 1 descending, 2 interleaved short/long
  int joint;       // 1: the coarse scan's points join the T1 fit (fitIRGroups)
};

static const char* kSpacing[4] = {"log", "linear", "dense-short", "dense-long"};
static const char* kPhase[3] = {"180 fixed", "180 follows 90", "180 alternates"};
static const char* kOrder[3] = {"ascending", "descending", "interleaved"};

static std::string describe(const Protocol& p) {
  char b[200];
  std::snprintf(b, sizeof b, "%d pts %.3g-%.3g T1 %s, wait %.3g T1, %d avg + %d dummy, %s, %s",
                p.n, p.lo, p.hi, kSpacing[p.spacing], p.td, p.navg, p.ndummy, kPhase[p.phase], kOrder[p.order]);
  if (p.joint) std::strncat(b, ", joint fit", sizeof b - std::strlen(b) - 1);
  return b;
}

static void tauList(const Protocol& p, double t1est, std::vector<double>& tau) {
  tau.resize(p.n);
  for (int k = 0; k < p.n; ++k) {
    const double u = double(k) / (p.n - 1);
    double v;
    switch (p.spacing) {
      case 0: v = p.lo * std::pow(p.hi / p.lo, u); break;
      case 1: v = p.lo + (p.hi - p.lo) * u; break;
      case 2: v = p.lo + (p.hi - p.lo) * u * u; break;
      default: v = p.lo + (p.hi - p.lo) * std::sqrt(u); break;
    }
    tau[k] = std::max(kTauFloor, v * t1est);
  }
}

static std::vector<int> orderOf(const Protocol& p) {
  std::vector<int> o;
  if (p.order == 0) for (int k = 0; k < p.n; ++k) o.push_back(k);
  else if (p.order == 1) for (int k = p.n - 1; k >= 0; --k) o.push_back(k);
  else for (int i = 0, j = p.n - 1; i <= j; ++i, --j) { o.push_back(i); if (i != j) o.push_back(j); }
  return o;
}

// ---- the spins (same model as bloch_check.cpp) ------------------------------------

struct Spin { double x, y, z, dw; };

static std::vector<Spin> equilibrium(int n, double off_hz) {
  std::vector<Spin> v(n);
  for (int j = 0; j < n; ++j) {
    const double u = (j + 0.5) / n;
    v[j] = {0, 0, 1, 2 * kPi * off_hz + std::tan(kPi * (u - 0.5)) / kT2p};
  }
  return v;
}

static void pulse(std::vector<Spin>& v, double a, double ph) {
  const double ux = std::cos(ph), uy = std::sin(ph), c = std::cos(a), s = std::sin(a);
  for (Spin& m : v) {
    const double d = ux * m.x + uy * m.y;
    const double cx = uy * m.z, cy = -ux * m.z, cz = ux * m.y - uy * m.x;
    m.x = m.x * c + cx * s + ux * d * (1 - c);
    m.y = m.y * c + cy * s + uy * d * (1 - c);
    m.z = m.z * c + cz * s;
  }
}

static void evolve(std::vector<Spin>& v, double t, double t1, double t2) {
  const double e2 = std::exp(-t / t2), e1 = std::exp(-t / t1);
  for (Spin& m : v) {
    const double c = std::cos(m.dw * t), s = std::sin(m.dw * t);
    const double x = m.x * c - m.y * s, y = m.x * s + m.y * c;
    m.x = x * e2; m.y = y * e2; m.z = 1 + (m.z - 1) * e1;
  }
}

static cplx readout(const std::vector<Spin>& v, double t2, double ph) {
  cplx acc = 0;
  const double e2 = std::exp(-kTacq / t2);
  for (const Spin& m : v) acc += cplx(m.x, m.y) * std::polar(e2, m.dw * kTacq);
  return acc / double(v.size()) * std::polar(1.0, -ph);
}

struct Run { std::vector<double> tau, sig; double seconds = 0; };

// One sample, a list of taus in a given order, shot by shot, from equilibrium.
// wait is everything after the 90 until the next 180 (overhead + recovery).
static Run simulateRaw(const std::vector<double>& tau, const std::vector<int>& order, double wait, int navg,
                       int ndummy, int phase, double t1, const Imperf& im, int iso) {
  const double t2 = t2Of(t1), a = im.flip_deg * kPi / 180;
  std::vector<Spin> v = equilibrium(iso, im.off_hz);
  std::vector<Spin> r = v;
  pulse(r, a, 0);
  const cplx ref = readout(r, t2, 0);
  Run R;
  R.tau = tau;
  R.sig.assign(tau.size(), 0);
  long k = 0;
  for (int idx : order) {
    double acc = 0;
    for (int s = 0; s < ndummy + navg; ++s, ++k) {
      const double ph90 = (k % 4) * kPi / 2;
      const double ph180 = phase == 0 ? 0 : (phase == 1 ? ph90 : (k % 2) * kPi);
      pulse(v, 2 * a, ph180);
      evolve(v, tau[idx], t1, t2);
      pulse(v, a, ph90);
      if (s >= ndummy) acc += std::real(readout(v, t2, ph90) * std::conj(ref)) / std::abs(ref);
      evolve(v, wait, t1, t2);
      R.seconds += kPulses + tau[idx] + wait;
    }
    R.sig[idx] = acc / navg;
  }
  return R;
}

static Run simulate(const Protocol& p, double t1, double t1est, const Imperf& im, int iso) {
  std::vector<double> tau;
  tauList(p, t1est, tau);
  return simulateRaw(tau, orderOf(p), kOverhead + p.td * t1est, p.navg, p.ndummy, p.phase, t1, im, iso);
}

static double coarseSeconds(const Coarse& c = g_coarse) {
  double t = 0;
  for (double tau : kCoarseTau) t += (kCoarseAvg + c.ndummy) * (kPulses + tau + kOverhead + c.wait);
  return t;
}

// Worst estimate/true ratio of a coarse scan over the five samples and the four
// hardware cases.
static void coarseRange(const Coarse& c, int iso, double* lo, double* hi, bool print) {
  std::vector<double> tau(kCoarseTau, kCoarseTau + 4);
  std::vector<int> order = {0, 1, 2, 3};
  *lo = 9; *hi = 0;
  for (const Imperf& im : kImp) {
    if (print) std::printf("   %-9s", im.name);
    for (double conc : kConc) {
      const Run R = simulateRaw(tau, order, kOverhead + c.wait, kCoarseAvg, c.ndummy, c.phase, t1Of(conc), im, iso);
      const IRResult f = fitIR(R.tau.data(), R.sig.data(), 4);
      const double r = f.ok ? f.t1_s / t1Of(conc) : 0;
      *lo = std::min(*lo, r); *hi = std::max(*hi, r);
      if (print) std::printf("  %4.0f mM %5.3f", conc, r);
    }
    if (print) std::printf("\n");
  }
}

// Round 0: the cheapest coarse scan whose estimate stays inside x0.8 .. x1.25
// in every case - a margin inside the x0.7 .. x1.4 the score is robust to.
static void chooseCoarse() {
  std::printf("Round 0: the coarse scan. Cheapest one whose T1 estimate stays within x0.8..x1.25 everywhere:\n");
  std::printf("   %6s %-15s %6s %8s  %s\n", "wait", "phase", "dummy", "seconds", "estimate range");
  Coarse best = {0, -1, 0};
  double bestT = 1e9;
  for (double w : {1.0, 2.0, 3.0, 5.0, 8.0, 12.0})
    for (int ph = 0; ph < 3; ++ph)
      for (int d = 0; d <= 1; ++d) {
        const Coarse c = {w, ph, d};
        double lo, hi;
        coarseRange(c, 801, &lo, &hi, false);
        const bool ok = lo >= 0.8 && hi <= 1.25;
        const double t = 5 * coarseSeconds(c);
        if (ok || (ph == 0 && d == 0))
          std::printf("   %5.0fs %-15s %6d %7.0fs  %.3f .. %.3f %s\n", w, kPhase[ph], d, t, lo, hi, ok ? "ok" : "");
        if (ok && t < bestT) { bestT = t; best = c; }
      }
  if (best.phase < 0) { std::printf("   none qualifies - keeping the 1 s scan, results will say so\n"); return; }
  g_coarse = best;
  std::printf("   -> chosen: wait %.0f s, %s, %d dummy: %.0f s for all five samples\n\n",
              best.wait, kPhase[best.phase], best.ndummy, bestT);
}

// ---- scoring --------------------------------------------------------------------------
//
// The budget: one coarse scan per sample, then the fine scan repeated r times
// to fill kBudget (r may be fractional - it stands for averaging longer). Each
// fine point is then the mean of navg x r shots, each coarse point of
// kCoarseAvg. With joint = 1 the coarse points join the T1 fit as a group of
// their own (fitIRGroups: shared T1, their own a and b); with joint = 0 the
// coarse scan only plans the fine one and is thrown away.

static Run coarseRun(double t1, const Imperf& im, int iso) {
  const std::vector<double> tau(kCoarseTau, kCoarseTau + 4);
  const std::vector<int> order = {0, 1, 2, 3};
  return simulateRaw(tau, order, kOverhead + g_coarse.wait, kCoarseAvg, g_coarse.ndummy, g_coarse.phase, t1, im,
                     iso);
}

// The T1 information in one group of points once its own a and c are allowed
// for (the Schur complement of the a, c block), every point weighted w.
static double infoT1(const std::vector<double>& tau, double c, double t1, double w) {
  double M[3][3] = {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}};
  for (double t : tau) {
    const double e = std::exp(-t / t1);
    const double J[3] = {1.0, e, c * e * t / (t1 * t1)};
    for (int r = 0; r < 3; ++r) for (int q = 0; q < 3; ++q) M[r][q] += w * J[r] * J[q];
  }
  const double d = M[0][0] * M[1][1] - M[0][1] * M[1][0];
  if (!(d > 0)) return 0;
  const double v0 = M[0][2], v1 = M[1][2];
  return M[2][2] - (v0 * (M[1][1] * v0 - M[0][1] * v1) + v1 * (M[0][0] * v1 - M[1][0] * v0)) / d;
}

// Fit one sample the way the instrument would: joint or fine scan alone, the
// points weighted by how many shots they average. Returns T1 and both c's.
static bool fitSample(const Protocol& p, const Run& Rc, const Run& Rf, double r, double* t1, double* cc,
                      double* cf) {
  if (p.joint) {
    std::vector<double> tau, s, w;
    std::vector<int> g;
    for (size_t i = 0; i < Rc.tau.size(); ++i) { tau.push_back(Rc.tau[i]); s.push_back(Rc.sig[i]); g.push_back(0); w.push_back(kCoarseAvg); }
    for (size_t i = 0; i < Rf.tau.size(); ++i) { tau.push_back(Rf.tau[i]); s.push_back(Rf.sig[i]); g.push_back(1); w.push_back(p.navg * r); }
    const IRGroupResult G = fitIRGroups(tau.data(), s.data(), g.data(), w.data(), int(tau.size()));
    if (!G.ok) return false;
    *t1 = G.t1_s; *cc = -G.b[0]; *cf = -G.b[1];
    return true;
  }
  const IRResult f = fitIR(Rf.tau.data(), Rf.sig.data(), int(Rf.tau.size()));
  if (!f.ok) return false;
  *t1 = f.t1_s; *cc = 0; *cf = -f.b;
  return true;
}

// sigma(r1) when all five samples share kBudget, the estimate off by factor f,
// hardware ideal. Also gives the per-sample sigma(1/T1) used as fit weights.
static double precisionAt(const Protocol& p, double f, int iso, double* sy, double* minutes, double* rOut,
                          const char** why) {
  Run Rf[5], Rc[5];
  double Tf = 0, Tc = 0;
  for (int i = 0; i < 5; ++i) {
    const double t1 = t1Of(kConc[i]);
    Rf[i] = simulate(p, t1, f * t1, kImp[0], iso);
    Rc[i] = coarseRun(t1, kImp[0], iso);
    Tf += Rf[i].seconds; Tc += Rc[i].seconds;
  }
  *minutes = (Tf + Tc) / 60;
  const double r = (kBudget - Tc) / Tf;
  *rOut = r;
  if (r < 1) { *why = "one pass over the budget"; return 1e9; }
  const double w1 = 1 / (kSigmaShot * kSigmaShot);
  for (int i = 0; i < 5; ++i) {
    const double t1 = t1Of(kConc[i]);
    double t1fit, cc, cf;
    if (!fitSample(p, Rc[i], Rf[i], r, &t1fit, &cc, &cf)) { *why = "fit failed"; return 1e9; }
    double info = infoT1(Rf[i].tau, cf, t1fit, p.navg * r * w1);
    if (p.joint) info += infoT1(Rc[i].tau, cc, t1fit, kCoarseAvg * w1);
    if (!(info > 0)) { *why = "no information"; return 1e9; }
    sy[i] = 1 / std::sqrt(info) / (t1 * t1);
  }
  double W = 0, Wx = 0, Wxx = 0;
  for (int i = 0; i < 5; ++i) { const double w = 1 / (sy[i] * sy[i]); W += w; Wx += w * kConc[i]; Wxx += w * kConc[i] * kConc[i]; }
  return std::sqrt(W / (W * Wxx - Wx * Wx));
}

struct Score {
  bool feasible = false;
  double fom = 1e9;         // sigma(r1) in the budget, worst over the estimate cases
  double r1pct15 = 0;       // the same, in % of r1
  double minutes = 0;       // one pass, coarse included, estimate exact
  double biasR1 = 0, biasT1 = 0;  // worst over all twelve cases
  const char* why = "";
};

static Score evaluate(const Protocol& p, int iso) {
  Score S;
  if (p.n < 4 || p.lo <= 0 || p.hi <= p.lo * 1.5) { S.why = "bad shape"; return S; }
  double worst = 0;
  for (int fi = 0; fi < 3; ++fi) {
    double sy[5], minutes = 0, r = 0;
    const double sr1 = precisionAt(p, kEstF[fi], iso, sy, &minutes, &r, &S.why);
    if (sr1 >= 1e9) return S;
    worst = std::max(worst, sr1);
    if (fi == 1) S.minutes = minutes;
    for (int ii = 0; ii < 4; ++ii) {
      double y[5], x[5];
      for (int i = 0; i < 5; ++i) {
        const double t1 = t1Of(kConc[i]);
        const Run Rf = simulate(p, t1, kEstF[fi] * t1, kImp[ii], iso);
        const Run Rc = coarseRun(t1, kImp[ii], iso);
        double t1fit, cc, cf;
        if (!fitSample(p, Rc, Rf, r, &t1fit, &cc, &cf)) { S.why = "fit failed"; return S; }
        S.biasT1 = std::max(S.biasT1, std::fabs(t1fit / t1 - 1));
        x[i] = kConc[i]; y[i] = 1 / t1fit;
      }
      const LineResult L = fitLine(x, y, sy, 5);
      if (!L.ok) { S.why = "line failed"; return S; }
      S.biasR1 = std::max(S.biasR1, std::fabs(L.slope / kR1 - 1));
    }
  }
  S.fom = worst;
  S.r1pct15 = 100 * worst / kR1;
  S.feasible = S.biasR1 <= kBiasR1 && S.biasT1 <= kBiasT1;
  if (!S.feasible) S.why = S.biasR1 > kBiasR1 ? "r1 biased" : "T1 biased";
  return S;
}
// ---- moves -----------------------------------------------------------------------------

struct Move { Protocol p; std::string what; };

static bool valid(const Protocol& p) {
  return p.n >= 4 && p.n <= 16 && p.lo >= 0.002 && p.lo <= 0.8 && p.hi >= 0.5 && p.hi <= 10 &&
         p.hi > 1.5 * p.lo && p.td >= 0.2 && p.td <= 8;
}

static std::vector<Move> movesFrom(const Protocol& p) {
  std::vector<Move> m;
  auto add = [&](Protocol q, const char* fmt, double v) {
    if (!valid(q)) return;
    char b[80]; std::snprintf(b, sizeof b, fmt, v); m.push_back({q, b});
  };
  for (int d : {-2, -1, 1, 2}) { Protocol q = p; q.n += d; add(q, "points -> %.0f", q.n); }
  for (double f : {1 / 1.5, 1.5}) { Protocol q = p; q.lo *= f; add(q, "shortest tau -> %.3g T1", q.lo); }
  for (double f : {1 / 1.25, 1.25}) { Protocol q = p; q.hi *= f; add(q, "longest tau -> %.3g T1", q.hi); }
  for (int s = 0; s < 4; ++s) if (s != p.spacing) { Protocol q = p; q.spacing = s; add(q, "spacing -> %.0f", s); }
  for (double f : {1 / 1.6, 1 / 1.25, 1.25, 1.6}) { Protocol q = p; q.td *= f; add(q, "wait -> %.3g T1", q.td); }
  for (int a : {4, 8, 16}) if (a != p.navg) { Protocol q = p; q.navg = a; add(q, "averages -> %.0f", a); }
  for (int d = 0; d <= 2; ++d) if (d != p.ndummy) { Protocol q = p; q.ndummy = d; add(q, "dummies -> %.0f", d); }
  for (int s = 0; s < 3; ++s) if (s != p.phase) { Protocol q = p; q.phase = s; add(q, "phase cycle -> %.0f", s); }
  for (int s = 0; s < 3; ++s) if (s != p.order) { Protocol q = p; q.order = s; add(q, "order -> %.0f", s); }
  { Protocol q = p; q.joint = 1 - p.joint; add(q, "joint coarse + fine fit -> %.0f", q.joint); }
  return m;
}

static std::vector<Score> scoreAll(const std::vector<Move>& ms, int iso) {
  std::vector<Score> out(ms.size());
  std::atomic<size_t> next(0);
  unsigned nt = std::max(1u, std::thread::hardware_concurrency());
  std::vector<std::thread> th;
  for (unsigned t = 0; t < nt; ++t)
    th.emplace_back([&]() { for (size_t i; (i = next++) < ms.size();) out[i] = evaluate(ms[i].p, iso); });
  for (auto& t : th) t.join();
  return out;
}

static void line(const char* tag, const Score& s, const std::string& what) {
  std::printf("%-7s %8.4f  %6.2f%%  %6.1f min  r1 bias %4.2f%%  T1 bias %4.2f%%  %s\n", tag, s.fom, s.r1pct15,
              s.minutes, 100 * s.biasR1, 100 * s.biasT1, what.c_str());
  std::fflush(stdout);
}

// ---- verification: Monte Carlo with noise, and the coarse scan --------------------------

static void verify(const char* name, const Protocol& p) {
  const int iso = 4001, trials = 2000;
  std::printf("\n%s at 4001 isochromats: %s\n", name, describe(p).c_str());
  const Score s = evaluate(p, iso);
  line("score", s, s.feasible ? "feasible" : s.why);
  double sy[5], minutes = 0, r = 0;
  const char* why = "";
  const double pred = precisionAt(p, 1.0, iso, sy, &minutes, &r, &why);
  Run Rf[5], Rc[5];
  for (int i = 0; i < 5; ++i) {
    Rf[i] = simulate(p, t1Of(kConc[i]), t1Of(kConc[i]), kImp[0], iso);
    Rc[i] = coarseRun(t1Of(kConc[i]), kImp[0], iso);
  }
  std::mt19937 rng(9102026);
  std::normal_distribution<double> g(0, 1);
  const double sf = kSigmaShot / std::sqrt(p.navg * r), sc = kSigmaShot / std::sqrt(double(kCoarseAvg));
  double sum = 0, sum2 = 0, bar = 0;
  int ok = 0;
  for (int t = 0; t < trials; ++t) {
    LineResult L;
    if (p.joint) {
      IRGroupResult f[5];
      for (int i = 0; i < 5; ++i) {
        std::vector<double> tau, y, w;
        std::vector<int> gr;
        for (size_t k = 0; k < Rc[i].tau.size(); ++k) { tau.push_back(Rc[i].tau[k]); y.push_back(Rc[i].sig[k] + g(rng) * sc); gr.push_back(0); w.push_back(kCoarseAvg); }
        for (size_t k = 0; k < Rf[i].tau.size(); ++k) { tau.push_back(Rf[i].tau[k]); y.push_back(Rf[i].sig[k] + g(rng) * sf); gr.push_back(1); w.push_back(p.navg * r); }
        f[i] = fitIRGroups(tau.data(), y.data(), gr.data(), w.data(), int(tau.size()));
      }
      L = relaxivity(kConc, f, 5);
    } else {
      IRResult f[5];
      for (int i = 0; i < 5; ++i) {
        std::vector<double> y = Rf[i].sig;
        for (double& v : y) v += g(rng) * sf;
        f[i] = fitIR(Rf[i].tau.data(), y.data(), p.n);
      }
      L = relaxivity(kConc, f, 5);
    }
    if (!L.ok) continue;
    ++ok; sum += L.slope; sum2 += L.slope * L.slope; bar += L.slope_err;
  }
  const double mean = sum / ok, sd = std::sqrt(std::max(0.0, sum2 / ok - mean * mean));
  std::printf("  Monte Carlo, %d sets in %.0f min (fine scan x%.2f): r1 = %.4f +- %.4f = %.2f%% (predicted %.2f%%), "
              "error bar / scatter %.2f\n", ok, kBudget / 60, r, mean, sd, 100 * sd / kR1, 100 * pred / kR1,
              (bar / ok) / sd);
}
// The fine scan is planned on the coarse scan's T1. The score is only robust if
// that estimate lands inside x0.7 .. x1.4, under every hardware case.
static void checkCoarse() {
  std::printf("\nCoarse scan at 4001 isochromats (taus 0.01 0.1 0.5 2.5 s, 4 shots, wait %.0f s, %s, %d dummy), "
              "estimate / true T1:\n", g_coarse.wait, kPhase[g_coarse.phase], g_coarse.ndummy);
  double lo, hi;
  coarseRange(g_coarse, 4001, &lo, &hi, true);
  std::printf("   range %.3f .. %.3f -> %s\n", lo, hi,
              lo >= 0.7 && hi <= 1.4 ? "inside x0.7..x1.4, the robustness cases cover it"
                                     : "OUTSIDE x0.7..x1.4 - the score's robustness cases do not cover the coarse scan");
}

int main(int argc, char** argv) {

  const Protocol start = {kIRPoints, kIRLo, kIRHi, 0, kIRWait, kIRAvg, 0, 0, 0, 0};  // T1Fit.h today
  int iso = 801;
  std::printf("Inversion-recovery protocol optimization. Score = sigma(r1) x sqrt(seconds), worst of estimate "
              "x0.7/x1/x1.4; %%-column = r1 error if all five get 30 min, coarse included.\n");
  std::printf("Constraint: r1 bias <= %.1f%% and T1 bias <= %.0f%% under ideal / t90 -10%% / 3 Hz off / both.\n\n",
              100 * kBiasR1, 100 * kBiasT1);
  std::printf("%-7s %8s  %7s  %10s\n", "round", "score", "r1 30m", "one set");

  chooseCoarse();
  Protocol cur = start;
  Score cs = evaluate(cur, iso);
  line("start", cs, describe(cur));
  if (!cs.feasible) std::printf("  (the starting protocol itself is not feasible: %s)\n", cs.why);
  if (argc > 1 && std::string(argv[1]) == "--start") { checkCoarse(); return 0; }
  // The whole day on one scale: the protocol before any optimization, after
  // round 1 (adopted in T1Fit.h), and after round 2.
  if (argc > 1 && std::string(argv[1]) == "--compare") {
    verify("ORIGINAL (8 pts 0.1-5 T1, wait 5 T1)", Protocol{8, 0.1, 5.0, 0, 5.0, 4, 0, 0, 0, 0});
    verify("ROUND 1 (T1Fit.h)", start);
    verify("ROUND 2 (+ joint fit)", Protocol{kIRPoints, kIRLo, kIRHi, 0, kIRWait, kIRAvg, 0, 0, 0, 1});
    return 0;
  }

  std::mt19937 rng(42);
  int flat = 0;
  for (int round = 1; round <= 60; ++round) {
    const std::vector<Move> ms = movesFrom(cur);
    const std::vector<Score> sc = scoreAll(ms, iso);
    int best = -1;
    for (size_t i = 0; i < ms.size(); ++i)
      if (sc[i].feasible && (best < 0 || sc[i].fom < sc[best].fom)) best = int(i);
    double gain = best >= 0 ? 1 - sc[best].fom / cs.fom : 0;
    char tag[16];
    if (best >= 0 && gain > 0) {
      cur = ms[best].p; cs = sc[best];
      std::snprintf(tag, sizeof tag, "%d", round);
      line(tag, cs, ms[best].what + "   (" + std::to_string(int(100 * gain * 10 + 0.5) / 10.0).substr(0, 4) + "% better)");
    }
    if (gain >= 0.01) { flat = 0; continue; }
    if (++flat < 2 && best >= 0 && gain > 0) continue;
    // stuck: random kicks of two to four parameters at once
    std::vector<Move> kicks;
    std::uniform_int_distribution<int> pick(0, 7), ni(4, 16), sp(0, 3), av(0, 2), du(0, 2), ph(0, 2), od(0, 2);
    std::uniform_real_distribution<double> lf(std::log(0.002), std::log(0.8)), hf(std::log(0.5), std::log(10.0)),
        tf(std::log(0.2), std::log(8.0));
    while (kicks.size() < 24) {
      Protocol q = cur;
      const int k = 2 + int(rng() % 3);
      for (int j = 0; j < k; ++j) switch (pick(rng)) {
          case 0: q.n = ni(rng); break;
          case 1: q.lo = std::exp(lf(rng)); break;
          case 2: q.hi = std::exp(hf(rng)); break;
          case 3: q.spacing = sp(rng); break;
          case 4: q.td = std::exp(tf(rng)); break;
          case 5: q.navg = 4 << av(rng); break;
          case 6: q.ndummy = du(rng); break;
          default: q.phase = ph(rng); q.order = od(rng); break;
        }
      if (valid(q)) kicks.push_back({q, "kick: " + describe(q)});
    }
    const std::vector<Score> ks = scoreAll(kicks, iso);
    int kb = -1;
    for (size_t i = 0; i < kicks.size(); ++i)
      if (ks[i].feasible && (kb < 0 || ks[i].fom < ks[kb].fom)) kb = int(i);
    if (kb >= 0 && ks[kb].fom < cs.fom * 0.99) {
      cur = kicks[kb].p; cs = ks[kb]; flat = 0;
      std::snprintf(tag, sizeof tag, "%dk", round);
      line(tag, cs, kicks[kb].what);
      continue;
    }
    std::printf("stop    no single change and no kick improves the score by 1 %% any more\n");
    break;
  }

  std::printf("\nRESULT  %s\n", describe(cur).c_str());
  checkCoarse();
  verify("START", start);
  verify("BEST", cur);
  return 0;
}
