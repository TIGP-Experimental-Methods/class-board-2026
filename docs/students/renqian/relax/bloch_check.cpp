// Does progressive saturation measure T1 at 2 mT, or something else?
// Ren Qian (Section A), 2026-10-09.
//
//   g++ -std=c++14 -O2 -Wall -Wextra -o bloch_check bloch_check.cpp && ./bloch_check
//
// The worry. Progressive saturation assumes that when the next pulse comes,
// nothing is left in the transverse plane from the last one. That needs
// TR >> T2*. NMR-FIRMWARE.md puts T2* in water at 2 mT at 0.3-1 s, and the
// fine scan for water starts at TR = 0.1 x 2.5 s = 0.25 s. If the leftover
// transverse magnetization is rotated back onto z by the next pulse, the
// steady state is no longer 1 - exp(-TR/T1) and the fitted T1 is wrong.
//
// So this follows the spins themselves, pulse by pulse - no formula for the
// signal is assumed anywhere - and hands the result to the same fits the
// instrument will use (firmware/src/relax/T1Fit.h):
//   * isochromats spread over a Lorentzian of offsets, so the FID decays with
//     T2* = 1 / (1/T2 + 1/T2'), T2' being the magnet's inhomogeneity
//   * ideal instantaneous pulses about an axis at the cycle's phase; CYCLOPS
//     steps the phase 0/90/180/270 from pulse to pulse and the receiver
//     follows it, as Sequencer does with cyclops = true
//   * the signal read 1.2 ms after each pulse (t_acq_start_us)
//   * progressive saturation (PS): from equilibrium, 2 unrecorded pulses,
//     4 recorded, TR pulse to pulse
//   * inversion recovery for comparison: from equilibrium every time,
//     180 - tau - 90, so nothing is ever left over. IR2 assumes a perfect
//     inversion (b = 2a); IR3 fits the inversion as well (fitIR)
//   * a SANITY case first: intrinsic T2 made 1 ms, so the transverse
//     magnetization is destroyed long before the next pulse and PS must come
//     out right. If it does, the simulator is sound and any bias in the other
//     cases is the physics, not a bug.
//     The first version of this check made T2' short instead, and PS still
//     came out 30-37% low. That was the lesson, not a bug: dephasing by an
//     inhomogeneous field is REVERSIBLE. The net signal vanishes, but every
//     isochromat keeps its own transverse magnetization, and the next pulse
//     tips it straight back onto z. Only irreversible T2 empties the plane -
//     so progressive saturation needs TR >> T2, not merely TR >> T2*, and in
//     a liquid T2 is close to T1.
//
// ASSUMPTIONS, stated so they can be argued with: 1/T2 = 1/T1 + 0.1 s^-1
// (for Cu2+ in water at low field T2 is close to T1); T2' = 0.667 s, the same
// magnet for every sample, giving T2* = 0.5 s in pure water, inside the
// documented 0.3-1 s; the transmitter on resonance unless stated.
#include "../../../../firmware/src/relax/T1Fit.h"

#include <cmath>
#include <complex>
#include <cstdio>
#include <vector>

using namespace t1fit;
typedef std::complex<double> cplx;

static const double kPi = 3.14159265358979323846;
static const double kT1Water = 2.5, kR1 = 1.0;  // the simulator's numbers, SPEC.md 8
static const double kTacq = 0.0012;              // pulse -> first sample, s
static const double kTrMin = 0.03, kTrMax = 600;

struct Spin { double x, y, z, dw; };
struct Sample { double t1, t2; };

static std::vector<Spin> equilibrium(int n, double offset_hz, double t2p) {
  std::vector<Spin> v(n);
  for (int j = 0; j < n; ++j) {
    const double u = (j + 0.5) / n;
    v[j] = {0, 0, 1, 2 * kPi * offset_hz + std::tan(kPi * (u - 0.5)) / t2p};
  }
  return v;
}

// Rotate every spin by angle a about the transverse axis at phase ph.
static void pulse(std::vector<Spin>& v, double a, double ph) {
  const double ux = std::cos(ph), uy = std::sin(ph), c = std::cos(a), s = std::sin(a);
  for (Spin& m : v) {
    const double d = ux * m.x + uy * m.y;                               // along the axis
    const double cx = uy * m.z, cy = -ux * m.z, cz = ux * m.y - uy * m.x;  // axis x m
    m.x = m.x * c + cx * s + ux * d * (1 - c);
    m.y = m.y * c + cy * s + uy * d * (1 - c);
    m.z = m.z * c + cz * s;
  }
}

static void evolve(std::vector<Spin>& v, double t, const Sample& smp) {
  const double e2 = std::exp(-t / smp.t2), e1 = std::exp(-t / smp.t1);
  for (Spin& m : v) {
    const double c = std::cos(m.dw * t), s = std::sin(m.dw * t);
    const double x = m.x * c - m.y * s, y = m.x * s + m.y * c;
    m.x = x * e2;
    m.y = y * e2;
    m.z = 1 + (m.z - 1) * e1;
  }
}

// What the receiver sees kTacq after the pulse, demodulated at phase ph.
static cplx readout(const std::vector<Spin>& v, const Sample& smp, double ph) {
  cplx acc = 0;
  const double e2 = std::exp(-kTacq / smp.t2);
  for (const Spin& m : v) acc += cplx(m.x, m.y) * std::polar(e2, m.dw * kTacq);
  return acc / double(v.size()) * std::polar(1.0, -ph);
}

static double progressiveSaturation(const Sample& smp, double tr, double a, double off,
                                    bool cyclops, double t2p) {
  std::vector<Spin> v = equilibrium(4001, off, t2p);
  cplx sum = 0;
  for (int k = 0; k < 6; ++k) {  // 2 unrecorded, then 4 recorded
    const double ph = cyclops ? (k % 4) * kPi / 2 : 0;
    pulse(v, a, ph);
    if (k >= 2) sum += readout(v, smp, ph);
    evolve(v, tr, smp);
  }
  return std::abs(sum) / 4;
}

static double inversionRecovery(const Sample& smp, double tau, double a, double off, cplx ref,
                                double t2p) {
  std::vector<Spin> v = equilibrium(4001, off, t2p);
  pulse(v, 2 * a, 0);  // t180 = 2 x t90, so a short t90 makes a short 180 too
  evolve(v, tau, smp);
  pulse(v, a, 0);
  const cplx s = readout(v, smp, 0);
  return std::real(s * std::conj(ref)) / std::abs(ref);  // signed: IR goes negative
}

int main() {
  std::printf("Progressive saturation (PS) against inversion recovery (IR), spins followed pulse by pulse\n");
  std::printf("1/T1 = %.1f + %.1f[Cu],  1/T2 = 1/T1 + 0.1;  T2' = 0.667 s (T2* in water 0.50 s) unless stated\n\n",
              1 / kT1Water, kR1);

  const double conc[5] = {0, 1, 2, 5, 10};
  // t2fix > 0 overrides the intrinsic T2 for every sample
  struct Case { const char* name; double flip; double off; bool cyc; double t2p; double t2fix; };
  const Case cases[] = {
    {"SANITY: intrinsic T2 = 1 ms, transverse magnetization destroyed - PS must come out right here",
     90, 0, true, 0.667, 0.001},
    {"(the first, wrong sanity case: T2' = 1 ms - dephased, not destroyed)", 90, 0, true, 0.001, 0},
    {"90 deg pulses, on resonance, CYCLOPS", 90, 0, true, 0.667, 0},
    {"90 deg pulses, on resonance, no phase cycling", 90, 0, false, 0.667, 0},
    {"90 deg pulses, 3 Hz off resonance, CYCLOPS", 90, 3, true, 0.667, 0},
    {"81 deg pulses (t90 10% short), on resonance, CYCLOPS", 81, 0, true, 0.667, 0},
  };

  for (const Case& cs : cases) {
    std::printf("%s\n", cs.name);
    std::printf("   %4s %7s %7s %8s %7s %8s %7s %8s %7s %5s\n", "mM", "T1 true", "T2*",
                "PS T1", "PS err", "IR2 T1", "IR2 err", "IR3 T1", "IR3 err", "b/a");
    T1Result psR[5], irR[5];
    IRResult ir3[5];
    for (int i = 0; i < 5; ++i) {
      const double t1 = 1 / (1 / kT1Water + kR1 * conc[i]);
      const Sample smp = {t1, cs.t2fix > 0 ? cs.t2fix : 1 / (1 / t1 + 0.1)};
      const double t2s = 1 / (1 / smp.t2 + 1 / cs.t2p);
      const double a = cs.flip * kPi / 180;
      double tr[8], s[8];
      planTR(t1, kTrMin, kTrMax, tr, 8);
      for (int k = 0; k < 8; ++k) s[k] = progressiveSaturation(smp, tr[k], a, cs.off, cs.cyc, cs.t2p);
      psR[i] = fitT1(tr, s, 8);
      // IR: the reference phase is a plain FID from equilibrium
      std::vector<Spin> v = equilibrium(4001, cs.off, cs.t2p);
      pulse(v, a, 0);
      const cplx ref = readout(v, smp, 0);
      for (int k = 0; k < 8; ++k) s[k] = inversionRecovery(smp, tr[k], a, cs.off, ref, cs.t2p);
      irR[i] = fitT1(tr, s, 8, 2.0);
      ir3[i] = fitIR(tr, s, 8);
      std::printf("   %4.0f %7.3f %7.3f %8.4f %6.1f%% %8.4f %6.1f%% %8.4f %6.1f%% %5.2f\n", conc[i], t1, t2s,
                  psR[i].t1_s, 100 * (psR[i].t1_s / t1 - 1), irR[i].t1_s, 100 * (irR[i].t1_s / t1 - 1),
                  ir3[i].t1_s, 100 * (ir3[i].t1_s / t1 - 1), ir3[i].inversion);
    }
    const LineResult lp = relaxivity(conc, psR, 5), li = relaxivity(conc, irR, 5),
                     l3 = relaxivity(conc, ir3, 5);
    std::printf("   r1:  PS %.4f (%+.1f%%)   IR2 %.4f (%+.1f%%)   IR3 %.4f (%+.1f%%)   true %.1f\n\n",
                lp.slope, 100 * (lp.slope / kR1 - 1), li.slope, 100 * (li.slope / kR1 - 1),
                l3.slope, 100 * (l3.slope / kR1 - 1), kR1);
  }
  return 0;
}
