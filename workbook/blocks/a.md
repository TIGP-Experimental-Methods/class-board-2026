# Section A — Inputs and the NMR receiver (your section)

**What it does.** Everything the instrument hears. Two things live here: the **eight analog inputs** (±10 V, 16-bit, on the front-panel SMAs AI1–AI8, read by one **ADS8688** ADC — an analog-to-digital converter — over SPI, one of the two wiring standards chips use to talk to the microcontroller), and the **NMR receiver**, which is the reason the board is an instrument and not a breakout. The receiver takes 40 microvolts out of a tuned coil, amplifies it a thousand times, protects itself while the transmitter is on, mixes it down to an audio frequency and hands it to the ADC as two channels, I and Q. The spectrum your phone draws at the end of the course comes through your section.

**Parts in your zone (≈ 80).**
- **The eight inputs:** ADS8688IDBTR (TSSOP-38, `/CS` = GPIO 10 — a GPIO is a general-purpose pin on the microcontroller) with its supply decoupling (100 nF + 10 µF on AVDD = +5VA; DVDD = +3V3), REFCAP 10 µF + 1 µF to AGND, REFIO 100 nF, 10 kΩ pull-ups on `/RST` and `/PD`, 33 Ω series on SDO; eight identical input networks, SMA → 1 kΩ → node with 1 nF to AGND and a BAV99 dual diode clamping to ±12 V. Channels 7 and 8 carry the receiver's I and Q through a solder jumper (default: the mixer; alternate: the SMA).
- **The tuned front end:** the RX SMA, two 1N4148W diodes back to back at the connector (the crossed-diode limiter that clips transmitter leakage at ±0.7 V), the tank capacitors (1.2 nF + trim pads; the coil and this capacitor resonate at 89.4 kHz), 100 Ω series, a 1 MΩ DC return.
- **The low-noise amplifier:** **OPA1656** dual op-amp, stage 1 gain 101 (10 kΩ / 100 Ω), stage 2 gain 10 (9.09 kΩ / 1 kΩ), interstage coupling 10 nF / 10 kΩ, a 100 pF across the feedback resistor to roll the response off at 175 kHz.
- **The blanking switch:** a **DG419** analog switch between the two amplifier stages, driven by `RX_BLANK` (GPIO 8), pulled so that the receiver is blanked when nothing drives the line.
- **The I/Q mixer:** two **TS5A23157** dual analog switches wired as a double-balanced commutator, an OPA1612 inverter and a 1.65 V mid-rail buffer, BAV99 clamps at each switch input, the 1 kΩ + 10 nF IF poles at 15.9 kHz, and two difference amplifiers (gain 20, 0.1 % resistors) whose outputs are the I and Q the ADC reads.
- **The clocks:** **Si5351A** clock generator (I²C, address 0x60) with a 25 MHz crystal and its two 4 pF load capacitors; CLK0 = 50 MHz to the transmitter's DDS in Section B; CLK1 = four times the local-oscillator frequency into a **74HC74** dual flip-flop wired as a Johnson counter, whose two outputs are exactly 90° apart.

**Reference numbers.** 1xx = the eight inputs · 7xx = clocks and receiver · 9xx = mixer and IF. Keep them: the footprints on the board carry the same names.

**Schematic** (the circuit drawing)**.** The full PDF pages for your section are `b1_inputs` and `nmr_rx` (link on the course site). Your **gapped sheet** is missing three or four parts — the exact list is in the class repository, `hardware/docs/student-deletions.md`, and you place them back from the PDF. Your **one part from the JLCPCB parts library** (JLCPCB is the factory that makes and assembles our boards; its part numbers look like C12345): the **OPA1656, C1849431** — the low-noise amplifier itself.

**Your zone on the PCB** (the outlined region of the physical board that is yours to route)**.** `ZONE_A`. The eight input networks in a row along the front edge in SMA order, the ADC in the middle on AGND copper; the receiver in its own corner with the tank pads tight to the RX SMA and **no ground pour under the tank node** (copper there adds capacitance and detunes the resonance). Rules: nothing digital under the analog inputs; the local-oscillator lines (LO_I, LO_Q and the 336 kHz clock) stay at least 5 mm away from the RX SMA, the tank and the amplifier input; SPI enters from the socket side only; nothing on layer 2; stay inside the zone.

## The two questions (E3, between workshops) — short answers that show the *why*
1. **Why is the receiver blanked between the two amplifier stages and not at its input?** *(think: the switch has charge as well as resistance; where does 60 pC hurt more, on a 1.25 nF tank or on a 10 nF coupling capacitor; and how long does each one take to settle)*
2. **Why does the interstage coupling capacitor form a high-pass corner at 1.6 kHz and not at 1.6 Hz?** *(think: the amplifier is driven into its rails during the transmit pulse; how long does each choice take to recover, and how does that compare with the 75 ms the signal lives)*

Harder pair for Workshop 2: with the coil tuned to Q = 10, what is the source resistance the amplifier sees, and which noise of the amplifier — voltage or current — matters at that impedance? Where does your section's analog ground join the rest of the board, and why only there?

## Your design number (E3)
**The tank, and the amplifier that suits it.** The class coil is 400 turns of AWG26 on a 4 cm × 10 cm former: L = 2.53 mH, R_DC = 6.7 Ω. Compute (a) the capacitor that resonates it at 89.4 kHz, (b) the parallel resistance at Q = 10, (c) its Johnson noise density √(4kTR), and (d) for each candidate amplifier, the current noise times that resistance — OPA1656 (6 fA/√Hz) and OPA1612 (1.7 pA/√Hz) — then say which one costs you signal-to-noise and by how many decibels. *Expected magnitude:* C ≈ 1.25 nF; R_p ≈ 14.2 kΩ; tank noise ≈ 15.3 nV/√Hz; the OPA1656 adds ≈ 0.15 dB, the OPA1612 ≈ 5.5 dB — which is why the quieter-looking amplifier is the wrong one. Working, a unit and a one-line conclusion into `docs/students/<name>/notes.md`.

## Your number (E13b)
**Noise floor of one input, in LSB rms** (an LSB is the least significant bit, the smallest step the converter can resolve), with the SMA shorted by a terminator: capture 4000 samples with the Scope tab or `instrument capture`, compute the standard deviation. A good 16-bit converter on a quiet board gives a few LSB. Write the expected value into `notes.md` with your E3 answers; the measured one comes in chapter 4.

## Your software (E11)
Commands `read_all` → 8 volts, `set_range {ch, range}`; status `ai1…ai8`, `range`. Then the part only your section can do: **capture I and Q** — the ADC scanning channels 7 and 8 at 250 kS/s each, the burst stored, the DC offset measured before the pulse and removed, the record decimated, and a **complex FFT** of I + jQ turned into the spectrum your panel draws. SIM: return slow sines plus noise, and a synthetic decaying signal so the spectrum works before the board exists. Alarm rule: `ai1 > 9 V → relay 1 off` (over-range protection story for the demonstration).

## What this section teaches
- **"Low noise" is a property of the source impedance, not of the amplifier.** The famous 1.1 nV/√Hz part is the wrong choice on a 14 kΩ tank.
- **Every AC-coupling corner is also a recovery time.** A capacitor that looks harmless is the classic reason a first NMR build sees nothing.
- **A switch has charge, not just resistance** — and where you put it decides whether that charge is a 48 mV kick or a 6 mV one.
- **What a mixer actually is:** a multiplier you can build out of two switches, and why detecting a phase needs two of everything.
- **A 90° phase shift is a time delay**, and a digital divider is the cheapest exact phase shifter there is.
- **Reading a register definition and turning it into a hard design limit** — the clock generator's own phase offset cannot do this job below 4.72 MHz, and the datasheet says so if you do the arithmetic.
