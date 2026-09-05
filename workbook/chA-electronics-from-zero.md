# Chapter A — Electronics from zero (self-study, ≈ 1 h, optional)

The background deck as text, for anyone who has not read a schematic before. Every idea is pointed at a place on **our** board. Read it before lecture 2; `/tutor A` will quiz you on any section.

## A.1 Charge, voltage, current — and what a schematic is
Current (A) is charge flowing; voltage (V) is the push between two points; a schematic is a graph of *which pins are connected*, nothing else — position on the page means nothing, the net names mean everything. **Ours:** every wire on the board is a net with a name (`+5V_RAW`, `AI1`, `SPI_SCLK`); the same name on two pages is the same wire.

## A.2 Ohm's law and the resistor jobs
V = I·R. Resistors on our board do four jobs: **limit current** (1 kΩ in series with every analog input, 2.2 kΩ before every LED), **set a ratio** (the 10 kΩ/40 kΩ pair that makes 4× in B3), **pull a line to a known level** (10 kΩ pull-ups on the ADC's /RST), and **terminate or isolate a cable** (49.9 Ω at each output, 33 Ω on the SPI data line).

## A.3 Impedance and 50 Ω
A cable is a transmission line; a 50 Ω coax "looks like" 50 Ω to a fast edge. Our outputs have 49.9 Ω in series so the cable sees a matched source; the scope's input can be 1 MΩ (you see the full amplitude) or 50 Ω (you see half — B3's number depends on which). TTL into 50 Ω gives ≈ 2.5 V; into 1 MΩ ≈ 5 V — the note on B5's panel.

## A.4 Capacitors and decoupling
A capacitor stores charge and passes fast changes. A **100 nF right at each IC's supply pin** supplies the nanosecond current spikes the IC draws when it switches; a **10 µF per rail per zone** supplies the microsecond ones; the regulator handles the rest. The distance matters more than the value: the loop from pin to capacitor to ground must be millimetres. Every block has these; every reviewer checks "decoupling next to the pin".

## A.5 Ground is not one thing
Current always returns. Relay coils and the USB supply return large, noisy currents; the ADC measures microvolts. So we have **GND** (power, logic) and **AGND** (signals) joined at **one star point** (a 0 Ω link at the B1/base boundary). If they were joined in two places, noisy return current would flow through the quiet ground. **Ours:** layer 2 is a solid GND plane under the digital parts; AGND copper sits under the ADC and the input networks; B4's isolated inputs have *no* ground to us at all.

## A.6 Diodes: protection and ORing
A diode conducts one way. **BAV99** pairs clamp our inputs and outputs to the ±12 V rails: a 30 V accident flows into the rail, not into the chip. **SS34** Schottky diodes let USB and the jack both feed +5V without fighting (the higher one wins). The **ULN2003** has a diode per channel that absorbs the relay coil's kick when it switches off. A **TVS** is a diode built to eat a static discharge.

## A.7 The op-amp as a black box
An op-amp with two resistors is an **amplifier with a gain set by their ratio**; with a reference on one input it also **shifts** the signal. B3: `AO = 4 × (DAC − 2.5 V)` turns 0–5 V into −10…+10 V. Rules of thumb: it needs supply rails wider than the swing (±12 V for ±10 V), it dislikes driving a capacitor (the cable) directly — hence the 49.9 Ω — and its output cannot exceed its rails (that is what "clipped" means, B3's alarm).

## A.8 ADCs: bits, sample rate, aliasing
16 bits over ±10 V = 0.3 mV per LSB; noise is measured in LSB rms (B1's number). Sampling at rate *f* sees nothing above *f*/2 correctly; anything above it **aliases** back as a false low frequency — the 1 kΩ + 1 nF network in front of each input is a gentle low-pass that helps, and the anti-alias filter in the instructor's conditioning chain does it properly. The Scope tab's rolling mode is limited by WiFi (tens of kS/s), its burst mode by the ADC (500 kS/s aggregate).

## A.9 DACs and reconstruction
A DAC outputs a staircase; a sine at 1 kHz made of 100 steps per period looks fine on a scope, 8 steps do not. The DAC8563 is 16-bit, so amplitude is exact to 0.3 mV, but the *shape* depends on the update rate the firmware achieves over SPI. B3's demo item is a sine; B3's number is its amplitude accuracy.

## A.10 Logic levels
The ESP32 is a **3.3 V** part: it outputs 0 / 3.3 V and must never see 5 V on a pin. **5 V TTL** equipment expects a high above 2 V and outputs up to 5 V. A **74AHCT541** takes 3.3 V in and gives 5 V out (that is B5); a **74LVC1T45** translates either way under a direction pin (TRIG); optocouplers accept 5–24 V in and give 3.3 V out (B4). "5 V-tolerant" means an input that survives 5 V — the ESP32's are not.

## A.11 Isolation
Two circuits are isolated when no copper connects them. A **relay** switches a contact with a magnet; an **optocoupler** sends light across a gap. The gap on the PCB is the **creepage** distance (2.5 mm in B4's rule); copper of any other net under the gap defeats it. Relays here switch ≤ 30 V DC / 1 A — never mains.

## A.12 Rails and where the power goes
5 V in from USB-C or the jack → **+5V_RAW** for everything not voltage-sensitive (dev board, relays, logic, LEDs) → **+3V3** from a linear regulator for the 3.3 V logic and the OLED → **±12 V** from two isolated DC-DC modules for the analog parts only → **+5VA** from +12 V through a 78L05 for the ADC and DAC. Rule (Decision #22): if it does not need a clean rail, it does not get one.

## A.13 Reading a datasheet in five minutes
Pinout diagram (pin 1 is marked — find it on the footprint too) → absolute maximum ratings (what kills it) → recommended operating conditions (the rails) → the typical application circuit (copy its decoupling and reference capacitors — that is where the ADS8688 values on B1 come from) → the timing diagram only when you write the driver.
