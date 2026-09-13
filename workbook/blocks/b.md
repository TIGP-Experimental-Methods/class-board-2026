# Section B — Signal generation, timing and the NMR transmitter (your section)

**What it does.** Everything the instrument says and everything it times. Three things live here: the **two analog outputs** AO1 and AO2 (−10 … +10 V, 16-bit, DC or waveforms, from a **DAC8563** — a DAC is a digital-to-analog converter — and an **OPA2192** dual op-amp), the **NMR transmitter** (a direct digital synthesizer that makes the 89.4 kHz carrier, a reconstruction filter that cleans it, and a power op-amp whose enable pin is the transmit gate), and the **digital lines** that let the instrument talk to other equipment — eight 5 V TTL outputs, two fast outputs, the TRIG SMA, and the I²C expander that drives them. The demonstration's first item — a waveform out, seen on a scope and on the instrument's own input — is yours, and so is the pulse that starts every NMR experiment.

**Parts in your zone (≈ 95).**
- **The analog outputs:** DAC8563SDGSR (VSSOP-10; AVDD = +5VA; internal 2.5 V reference on `VREF_DAC` with 100 nF; `/SYNC` = GPIO 5 — a GPIO is a general-purpose pin on the microcontroller — DIN = MOSI, SCLK, the SPI wiring); OPA2192 on ±12 V, each channel a **difference amplifier** with a 10 kΩ / 40.2 kΩ network: `AO = 4 × (DAC − VREF)`, so 0–5 V in gives −10…+10 V out; per output a 49.9 Ω series resistor then the SMA, with a BAV99 clamp to ±12 V.
- **The synthesizer:** **AD9834** DDS (TSSOP-20, 28-bit, clocked at 50 MHz from Section A's clock generator) with its bias and reference capacitors, a 6.80 kΩ full-scale resistor and 200 Ω load resistors; `FSYNC` = GPIO 41, `PSELECT` = GPIO 42. Its **two phase registers** are what make 0°/90°/180°/270° phase cycling possible — you switch the transmitted phase with one pin.
- **The reconstruction filter:** a 3rd-order Butterworth low-pass at 3 MHz (390 pF, 15 µH, 130 pF) that removes the staircase the DAC leaves behind, then a 1 µF capacitor that blocks DC into the power stage.
- **The power stage:** **OPA564** (1.5 A, 17 MHz) on a single supply from the external power input, biased at mid-rail, with its **enable pin used as the transmit gate** (`TX_EN` = GPIO 40), a current flag and a thermal flag read back by the firmware, and its thermal pad soldered to the ground pour with a via array. AC-coupled out to the TX SMA and the coil terminal.
- **The digital lines:** SN74AHCT541 octal buffer at +5V (3.3 V in, TTL out) for DIO1–8; 74HCT125 quad buffer for the two fast outputs (GPIO 18, 21); **SN74LVC1T45** level translator for TRIG (A side +3V3 = GPIO 38, B side +5V → 100 Ω → SMA, direction from GPIO 39; BAV99 clamp on the B side); 100 nF at every supply pin; screw terminals along the rear edge.
- **The I²C expander:** a **TCA9535** on the I²C bus. It drives the eight DIO lines here and the four relay drivers in Section C, which is how the board keeps enough direct microcontroller pins for the NMR signals. Anything timing-critical — the fast outputs, TRIG, the transmit gate — stays on a direct pin.

**Reference numbers.** 3xx = the analog outputs · 5xx = DIO, TRIG and the expander · 8xx = the DDS and the power stage. Keep them: the footprints on the board carry the same names.

**Schematic** (the circuit drawing)**.** Your section is three sheets of the full PDF `hardware/docs/schematic-full.pdf`: **`b3_outputs`, page 5**, **`b5_dio_trig`, page 7** and **`nmr_tx`, page 11** (also on the course site). You complete a **gapped copy** of each — a small KiCad project of its own in `hardware/student/`; open the `.kicad_pro` next to the sheet:

| Gapped sheet | Place back | What it is |
|---|---|---|
| `student/b3_outputs_gapped` (page 5) | **R305**, **R307** 10k · **R306**, **R308** 40.2k, all R0603 | the AO2 difference-amplifier resistor set (the repeated channel) |
| | **R310** 49.9 R0603 · **D302** BAV99 SOT-23 | the AO2 output series resistor and its clamp |
| `student/b5_dio_trig_gapped` (page 7) | **U502** 74HCT125PW TSSOP-14 · **R509**, **R510** 49.9 R0603 | the 74HCT125 fast-output channel |
| | **C501**, **C502** 100nF C0603 | the buffer decoupling pair |
| | **J501** KF301-5.0-2P | one TTL screw terminal |
| `student/nmr_tx_gapped` (page 11) | **C815** 47µF 35V · **C816** 100nF C0603 | the OPA564 V+ decoupling pair |
| | **D802** SS54 SMA | the output clamp diode to GND |
| | **R813** 4.7 Ω 1 W R2512 | the output isolation resistor |

`hardware/docs/student-deletions.md` is the authority for this list and says where each part sits on the PDF. Your **one part from the JLCPCB parts library** (JLCPCB is the factory that makes and assembles our boards; its part numbers look like C12345): the **AD9834BRUZ, C116589**, TSSOP-20 — the synthesizer U801 itself.

**Your zone on the PCB** (the outlined region of the physical board that is yours to route)**.** `ZONE_B`. The DAC on the socket side and the op-amp next to the SMAs, feedback resistors tight to the op-amp; the buffers near the socket end and the terminals along the rear edge, with the fast nets short and a ground return beside them; the synthesizer, its filter and the power stage in a line towards the TX connector. **The transmit current is the enemy of Section A:** route the transmit output and its return as a close pair and keep that loop under a square centimetre, well away from the receiver's ground.

## The two questions (E3, between workshops) — short answers that show the *why*
1. **Why does the power stage run from a single supply with its negative rail on ground, rather than from ±12 V?** *(think: what the enable pin and the two flags are measured against; what that would cost in optocouplers; and where the thermal pad of the package sits electrically)*
2. **What sets the ±10 V swing of AO1?** *(the DAC gives 0–5 V; find the 4× and the subtraction of 2.5 V in the resistor network; what limits the swing at the top — the rails or the op-amp)*

Harder pair for Workshop 2: why can a 3.3 V pin not drive 5 V TTL directly, and why must a 5 V TTL signal from another instrument not go straight into the microcontroller? What does the reconstruction filter have to reject, and at what frequency does the nearest image of the synthesizer sit?

## Your design number (E3)
**The 90° pulse.** The class coil is 400 turns, L = 2.53 mH, and B/I = 5.03 mT/A. Compute (a) its reactance at 89.4 kHz, (b) the current your transmitter must drive for a rotating field of 28.2 µT, (c) the voltage that takes across the coil, and (d) the pulse length for a 90° flip from t₉₀ = π/(γB₁) with γ = 2.675 × 10⁸ rad s⁻¹ T⁻¹. Then the sanity check the whole design rests on: at that drive, how much current does the power stage actually deliver, and what is the 1.5 A rating for? *Expected magnitude:* X_L ≈ 1419 Ω; ≈ 5.6 mA; ≈ ±7.95 V; t₉₀ ≈ 417 µs — and the milliamps say the 1.5 A is for the megahertz version of this instrument, not for this experiment. Working, a unit and a one-line conclusion into `docs/students/<name>/notes.md`.

## Your number (E13b)
**Amplitude accuracy of a 1 kHz sine at ±5 V** on AO1, into a scope's high-impedance input: measure peak-to-peak and compare with the setpoint (expect within about 1 % once the 1 % resistors are calibrated in firmware). If you have time, the second number is the TTL edge rate on a fast output: the 10–90 % rise time and the high level into 1 MΩ and into 50 Ω.

## Your software (E11)
Commands `set_dc {ch, volts}`, `sine {ch, freq, amp, offset}`, `off {ch}`; `dio {n, level}`, `trig_dir {out}`, `fast_out {n, freq_hz}`; status `ao1, ao2, mode1, mode2, dio1…dio8, trig_dir`. Then the part only your section can do: the **DDS driver** (write the frequency as two words, load the two phase registers, switch phase with the pin) and the **pulse programmer** — a table of `{time, which line changes, which phase}` run from a timer so the pulse edges land within microseconds: blank the receiver, gate the transmitter on for 417 µs, gate it off, wait a millisecond, unblank, tell Section A to capture. SIM: report the setpoints and pretend the sequence ran. Alarm rule: `ao1 > 9.5 → notify` ("output clipped"). Pair with Section A in Workshop 3: your sine into their AI1, and your pulse into their receiver.

## What this section teaches
- **A power op-amp is mostly a thermal and a protection problem**, not an amplification one.
- **An enable pin referenced to the negative rail dictates the whole supply topology** — one line in a datasheet decides how the board is powered.
- **DC blocking is not optional when you bias at mid-rail**, and the capacitor that does it has to be sized, not guessed.
- **A DAC makes images as well as a signal**, and the reconstruction filter is what decides whether your carrier is clean; an inductor that has stopped being an inductor at 48 MHz filters nothing.
- **Timing is a design specification, not an afterthought:** microsecond edges come from hardware timers, not from software delays.
- **Logic levels are a contract** — 3.3 V, 5 V TTL, "5 V-tolerant" — and buffers are how you keep it.
