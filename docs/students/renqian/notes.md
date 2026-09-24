# Section A — E3 notes

> **Draft.** The reasoning and the arithmetic are worked out here so I can check them.
> The submitted text must be in my own words — the course's rule is that the learning step
> is mine. Anything I cannot re-derive without looking, I do not yet understand.
>
> **Scope caveat:** these answers follow `workbook/blocks/a.md`, which describes the old
> main-board Section A. Since commit `20d52d1` the front panel is split four ways and my
> routing job is the panel's 13 analog nets. The workbook was not updated. If E3 has been
> rescoped to the panel only, the questions below may no longer be the right ones — asked.

---

## Question 1 — Why is the receiver blanked *between* the two amplifier stages, not at its input?

A real analog switch is not just a resistance. When it changes state, charge stored in the
gate–channel capacitance is dumped into whatever is connected to it — **charge injection**,
about **60 pC** for the DG419. That charge has to go somewhere, and where it lands is decided
by the capacitance it lands on:

    dV = Q / C

| Put the switch here | C it kicks | dV |
|---|---|---|
| at the input, on the tank | 1.25 nF | **48 mV** |
| between the stages, on the coupling cap | 10 nF | **6 mV** |

So the interstage position is already 8x gentler. But that is the smaller half of the argument.

**The decisive point is where it sits in the gain chain.** A disturbance between stage 1 and
stage 2 has already passed the 101x gain of stage 1, so referred back to the input it is

    6 mV / 101 = 59 uV

against **48 mV** for a kick injected directly onto the tank. That is a factor of about **800**.
The signal we are trying to see is ~40 uV, so the tank kick is more than a thousand times the
signal and the interstage kick is comparable to it — a completely different problem.

**And the tank kick does not merely settle, it rings.** The tank is a resonator at Q = 10, so
an impulse into it rings at exactly 89.4 kHz — the signal frequency — and decays with

    tau = 2Q / w0 = 20 / 561717 = 35.6 us

Ringing at the signal frequency is indistinguishable from an FID: no filter downstream can
remove it, because it lives exactly where the signal lives. The interstage node, by contrast,
is a simple RC (10 kohm x 10 nF, tau = 100 us) and what it produces is a broadband step, not a
tone at 89.4 kHz — the IF filtering and the mixer reject it.

**A fourth reason, permanent rather than transient.** A switch across the tank loads it. Its
on-resistance and its off-state capacitance sit directly across a 14.2 kohm resonator, dropping
Q and shifting f0. That cost is paid on every shot, not just after switching. It is the same
principle as the rule that no ground pour may go under the tank node: anything you put near
that node detunes it.

---

## Question 2 — Why is the interstage high-pass corner at 1.6 kHz and not 1.6 Hz?

**Because an AC-coupling corner is also a recovery time,** and the transmit pulse drives stage 1
hard into its rails. While that happens the coupling capacitor charges to a wrong voltage, and
the receiver is blind until it discharges back. That recovery is set by the same RC that sets
the corner:

    tau = 1 / (2 pi f_c)

| Corner | tau | recovery (a few tau) |
|---|---|---|
| 1.6 kHz (10 kohm x 10 nF) | **100 us** | ~0.3–0.5 ms |
| 1.6 Hz | **100 ms** | ~0.3–0.5 s |

The free induction decay lives about **T2\* = 75 ms**.

- With a **1.6 Hz** corner, one time constant (100 ms) is already longer than the entire signal.
  The amplifier returns to its linear region well after the FID has died. **You would see
  nothing at all** — and the board would look broken rather than mistuned, which is why this is
  the classic first-NMR-build failure.
- With a **1.6 kHz** corner, recovery costs ~100 us, about **0.1%** of the signal's lifetime.
  Effectively the whole FID survives.

**What the high corner costs: nothing that matters.** The corner only has to sit *below* the
signal frequency. At 89.4 kHz the signal is more than fifty times above 1.6 kHz, so the
high-pass does not attenuate it. Given that, you want the corner as **high** as you can put it,
because every decade higher is a decade faster recovery. 1.6 kHz is the design pushing the
corner up as far as the signal allows.

---

## Design number — the tank, and the amplifier that suits it

Class coil: 400 turns AWG26 on a 4 cm x 10 cm former. **L = 2.53 mH**, R_DC = 6.7 ohm.
Target **f0 = 89.4 kHz**, loaded **Q = 10**. (w0 = 2*pi*f0 = 5.617e5 rad/s.)

**(a) The resonating capacitor**

    C = 1 / (w0^2 L) = 1 / ((5.617e5)^2 x 2.53e-3)

    C = 1.253 nF   ~ 1.25 nF

Matches the 1.2 nF + trim pads actually fitted — the trim is there because the coil's real
inductance will not be exactly 2.53 mH.

**(b) The parallel resistance at Q = 10**

    R_p = Q w0 L = 10 x 5.617e5 x 2.53e-3

    R_p = 14.21 kohm

(Cross-check: R_p = Q / (w0 C) = 10 / (5.617e5 x 1.253e-9) = 14.21 kohm. Same.)

This is the source impedance the amplifier actually sees — **not** the 6.7 ohm of the wire.
That distinction is the whole exercise.

**(c) Johnson noise of that resistance**

    e_tank = sqrt(4 k T R_p) = sqrt(4 x 1.381e-23 x 300 x 14211)

    e_tank = 15.34 nV/rtHz

This is the noise floor set by the tank itself. No amplifier can do better; the only question
is how much it adds.

**(d) Each candidate amplifier's current noise into that resistance**

    e_i = i_n x R_p

| Amp | i_n | i_n x R_p | e_n | total sqrt(e_tank^2 + e_n^2 + e_i^2) | penalty |
|---|---|---|---|---|---|
| **OPA1656** | 6 fA/rtHz | **0.085 nV** | 2.9 nV | 15.62 nV/rtHz | **0.15 dB** |
| **OPA1612** | 1.7 pA/rtHz | **24.16 nV** | 1.1 nV | 28.64 nV/rtHz | **5.42 dB** |

The OPA1612 has **less than half** the voltage noise of the OPA1656 — 1.1 nV against 2.9 nV —
and on a datasheet it is plainly the quieter part. On this tank it is **5.3 dB worse**, because
its current noise flowing in 14.2 kohm produces 24 nV/rtHz, which swamps everything else.

**The clean way to see it — the crossover impedance** e_n / i_n, the source resistance at which
an amplifier's two noises contribute equally:

| Amp | e_n / i_n |
|---|---|
| OPA1656 | **483 kohm** |
| OPA1612 | **647 ohm** |

Our tank sits at 14.2 kohm. That is far **below** the OPA1656's crossover, so the OPA1656 is
still voltage-noise dominated and its tiny current noise is irrelevant. It is far **above** the
OPA1612's crossover, so the OPA1612 is deep into its current-noise regime. Same tank, opposite
sides of the line.

**Conclusion (one line):** the 2.53 mH coil resonates at 89.4 kHz with 1.25 nF and presents
14.2 kohm at Q = 10, whose own Johnson noise is 15.3 nV/rtHz; the OPA1656 adds 0.15 dB to that
and the lower-voltage-noise OPA1612 adds 5.4 dB — so "low noise" is a statement about the
source impedance, not about the amplifier.

---

## Harder pair (Workshop 2)

1. **Source resistance at Q = 10, and which amplifier noise matters there.** R_p = 14.2 kohm
   (part b). **Current noise matters**, and the crossover impedances above are the proof: at
   14.2 kohm the OPA1612 is ~22x above its 647 ohm crossover and therefore current-noise
   dominated, while the OPA1656 is ~34x below its 483 kohm crossover and still voltage-noise
   dominated. The tank impedance is what decides which specification on the datasheet you
   should be reading.

2. **Where does the analog ground join the rest of the board, and why only there?** AGND and
   GND meet at **one star point** (the instructor's power-entry sheet, `b2_power`). Only there,
   because two joins make a loop: return current from the digital side would then have a path
   through the analog ground, and the voltage it develops across that copper adds directly to a
   40 uV signal. One join means digital return current has no reason to flow in AGND at all.
   On the panel this is why my AI/AO/RX/TX nets take their return from the AGND plane (In1.Cu)
   via a via beside the pad, and why I must not draw ground tracks across the board.
   *To confirm against `b2_power` on the schematic PDF rather than asserting it.*

---

## E13b — expected value (measured in chapter 4)

**Noise floor of one input in LSB rms**, SMA shorted with a terminator, 4000 samples, standard
deviation. The ADS8688 on +-10 V gives 20 V / 65536 = **305 uV per LSB**. A good 16-bit
converter on a quiet board should give **a few LSB rms** — so of order 1–3 LSB, i.e. roughly
0.3–1 mV rms. If it comes out much larger, the first suspects are digital return current in
the analog ground and the local-oscillator lines coupling into the input networks.

---

## E8 — the JLCPCB library part (OPA1656IDR, C1849431)

Fetched with `easyeda2kicad --full --lcsc_id C1849431`. The part is **already in
`hardware/lib/class_board`**, as the section page says it would be, so the exercise is the
library entry, not the placement. I fetched it to a scratch folder instead of using
`--overwrite`, so the instructor's own curated entry is untouched, and compared the two.

### Pin numbering — checked against the OPA1656 datasheet

| Pin | Function | easyeda2kicad | library |
|---|---|---|---|
| 1 | OUT A | OUTA | output |
| 2 | -IN A | -INA | input |
| 3 | +IN A | +INA | input |
| 4 | V- | V- | power_in |
| 5 | +IN B | +INB | input |
| 6 | -IN B | -INB | input |
| 7 | OUT B | OUTB | output |
| 8 | V+ | V+ | power_in |

Both agree, and both match the standard dual-op-amp SOIC-8 arrangement in the datasheet.
**The numbering is right.** Two things about the fetched symbol are not:

1. **Every pin comes out as `unspecified`.** The library's entry types them properly
   (output / input / power_in). This matters: with `unspecified` pins ERC cannot tell an
   unconnected input from a driven one, and cannot flag a power pin that nothing drives -
   so a fetched-as-is symbol quietly disables the checks that catch real wiring mistakes.
2. **It arrives as one symbol; the library splits it into three units** - op-amp A
   (1/2/3), op-amp B (5/6/7), and the power pins (4/8) on their own. That is the normal
   way to draw a dual op-amp: each half can be placed where its own circuit is, and the
   supply pins appear once on the rails sheet instead of being dragged around twice.

### Footprint — the two differ, and the library's is the better land pattern

| | library `SOIC-8_L5.0-W4.0-...` | fetched `SOIC-8_L4.9-W3.9-...` |
|---|---|---|
| pad X | ±1.90, ±0.63 (1.27 mm pitch) | **identical** |
| pad Y | ±2.71 mm | ±2.60 mm |
| pad size | 0.568 × 1.95 mm | 0.588 × 1.800 mm |

The pitch and the 6.0 mm lead span are the same, so both fit the same physical part. The
library's pads sit **0.11 mm further out and are 0.15 mm longer** - more room for the
solder fillet at the toe, which is the more forgiving land pattern. The library holds
three SOIC-8 variants (`L4.9-W3.9`, the same with a `EP3.1` thermal pad, and `L5.0-W4.0`)
and the design uses `L5.0-W4.0`, so this looks like a deliberate choice, not an accident.

**What I would say in the pull request:** the fetched part is correct where it counts
(pin numbering, pitch, lead span) but would be a downgrade if committed over the existing
entry - it loses the pin electrical types that ERC depends on, loses the three-unit split,
and lands a tighter footprint. So nothing in `hardware/lib/` is changed by this exercise.

### E8, second reading — C474881 (KF301-5.0-2P screw terminal)

The workshop outline gives E8 as `--lcsc_id C474881` (the 2-pin screw terminal) while the
workbook's ch. 2 gives it per section (Section A: OPA1656, C1849431). The two disagree, so
I did both. C474881 is **also already in `hardware/lib/class_board`**, so again a check.

| | pad 1 | pad 2 | size | drill |
|---|---|---|---|---|
| board (J411, J412) | -2.5 | +2.5 | 2.2 x 2.2 | 1.400 |
| `hardware/lib` | -2.5 | +2.5 | 2.2 x 2.2 | 1.400 |
| easyeda2kicad | -2.5 | +2.5 | 2.2 x 2.2 | 1.400 |

**All three agree exactly** on everything that reaches the factory - 5.0 mm pitch, 2.2 mm
pads, 1.4 mm drill. The difference is drawing only: the board and the library each carry
**17** graphic elements, the fetched one **21**. So importing it would *add* four silkscreen
or fab shapes that neither the board nor the library has - it would create a mismatch
rather than resolve one. Same verdict as the OPA1656: leave the library alone.

**On the `lib_footprint_mismatch` warnings.** Two of the three on the front panel are this
footprint, on **J411 and J412** - and those are the isolated-input terminals, which
`front-panel/sections/D/SECTION.md` assigns to **Section D**, not to me. The pads match the
library exactly, so it is a metadata difference from the library being re-saved in KiCad 10
format (commit `78ad796`), not a geometry problem. Nothing to fix, and not my section's to
fix in any case.
