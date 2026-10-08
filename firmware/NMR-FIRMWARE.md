# NMR console firmware — design contract (class board v0.7, 2026-09-13)

This file is the contract between the drivers, the `nmr` block, the phone app and the Python client.
Design authority: the course repo notes `2026-09-13-v07-nmr-circuits.md` (§9 firmware notes) and
`2026-09-13-nmr-respec-proposal.md` (§8.2 GPIO map); the schematic `hardware/sheets/nmr_rx.kicad_sch`,
`nmr_tx.kicad_sch`, `c_switch.kicad_sch`, `b5_dio_trig.kicad_sch` (TCA9535). When code and this file
disagree, fix the code; when this file and the schematic disagree, the schematic wins — then fix this file.

Demo regime: proton NMR in water at **B0 ≈ 2.1 mT, f_Larmor ≈ 89.4 kHz**, thermal polarization, free
induction decay (FID) after a 90° pulse, heterodyne I/Q receiver, IF ≈ 5.4 kHz into panel inputs AI7 (I)
and AI8 (Q), which are ADS8688 channels AIN_3 and AIN_2. Earth's-field NMR (≈ 2 kHz, with the polarizer coil) is the stretch goal on the same code path.

## 1. GPIO map v0.7 (`include/pins.h`)

| GPIO | Constant | Net | Function | Section |
|---|---|---|---|---|
| 12 / 11 / 13 | `PIN_SPI_SCLK/MOSI/MISO` | SPI_* | SPI2 on IO_MUX pins, shared by ADC, DAC, DDS | base |
| 10 | `PIN_CS_ADC` | CS_ADC | ADS8688 /CS | A |
| 5 | `PIN_CS_DAC` | CS_DAC | DAC8563 /SYNC (via 74HCT125) | B |
| 1 / 2 | `PIN_I2C_SDA/SCL` | I2C_* | 400 kHz; OLED 0x3C, TCA9535 0x20, Si5351A 0x60 | base |
| 16 / 17 | `PIN_OPTO_IN[0..1]` | OPTO_IN1/2 | 6N137 outputs, active LOW (front panel; 1 k pull-ups on the panel, `INPUT_PULLUP` in firmware) | C |
| 21 / 18 | `PIN_FAST_OUT[0..1]` | FAST_OUT1/2 | 74HCT125 → terminals | B |
| 38 / 39 | `PIN_TRIG_IO`, `PIN_TRIG_DIR` | TRIG_IO/DIR | 74LVC1T45; DIR 1 = output to the SMA | B |
| 41 | `PIN_DDS_FSYNC` | DDS_FSYNC | AD9834 frame sync (its SPI chip select, active low) | B |
| 42 | `PIN_DDS_PSEL` | DDS_PSEL | AD9834 PSELECT pin; ignored with PIN/SW = 0 (phase select by the PSEL bit), held low | B |
| 40 | `PIN_TX_EN` | TX_EN | OPA564 enable = transmit gate (10 k pull-down; 1 = transmit) | B |
| 8 | `PIN_RX_BLANK` | RX_BLANK | DG419 receiver blanking: **0 = blanked (default, pull-down), 1 = receive** | A |
| 9 / 14 | `PIN_HB_IN1`, `PIN_HB_IN2` | HB_IN1/2 | DRV8871 H-bridge inputs (10 k pull-downs; 0/0 = coast) | C |
| 47 | `PIN_FET_GATE` | FET_GATE | UCC27517 → AOD4184A polarizer switch (1 = polarizer coil on) | C |
| 4 | `PIN_VEXT_SENSE` | — (rework B6) | +VEXT through a 100 k / 10 k divider, 100 nF across the 10 k (ADC1 channel 3; 24 V reads 2.18 V); floats on an unmodified board | C |
| 6 | `PIN_TX_IFLAG` | TX_IFLAG (rework A2) | OPA564 current-limit flag, active high, from the R811 pad through 1 k; `INPUT_PULLDOWN` | B |
| 7 | `PIN_TX_TFLAG` | TX_TFLAG (rework A2) | OPA564 thermal flag, active high, from the R812 pad through 1 k; `INPUT_PULLDOWN` | B |
| 15 | `PIN_REF_CLK` | — | reserved: Si5351 CLK2 as a digital trigger on the next board revision; no code uses it | B |
| 43 / 44 | — | GPIO43/44 | UART0; panel LED_WIFI/ACT via R717/R718; not driven by firmware | base |
| 19 / 20 | — | USB_DN/DP | native USB | base |
| 48 | `PIN_RGB_LED` | — | WS2812 on the dev board | — |
| 0/45/46, 3, 35–37 | — | — | never used (strapping, unused, PSRAM) | — |

TCA9535 I²C expander (address 0x20, A0 = A1 = A2 = GND): **P0.0–P0.7 = DIO1–8** (→ 74AHCT541 → terminals),
**P1.0–P1.3 = MODULE_OUT1–4** (2026-09-17: the former RLY_IN1–4, same ports — the first four of the seven
MODULE OUT lines that reach the front panel's module header through a second 74AHCT541 at 5 V; active high,
10 k pull-downs keep them off at boot), **P1.4 = /CLR of
the 74HC74 Johnson counter** (net EXP_P14, TP501, R706 10 k pull-up; pulse low to reset the quadrature LO to state 00), **P1.5–P1.7 = MODULE_OUT5–7** (2026-09-17: P1.4 is the counter clear, so the expander has seven ports for the module
header; the header's eighth signal pin is a **reserved spare**, tied low — it always reads low). All 16 lines are outputs; the expander powers up with every port as an input, so `begin()` writes
the output registers first (all zero except P1.4 = 1), then the configuration registers. In firmware the
module-output bit map is `EXP_BIT_MOD[7] = {0, 1, 2, 3, 5, 6, 7}` (`pins.h`).

Front-panel input AI n is wired to ADS8688 channel `kAinOfAi[n-1]` (`pins.h`): AI1→AIN_1, AI2→AIN_0,
AI3→AIN_7, AI4→AIN_6, AI5→AIN_5, AI6→AIN_4, AI7→AIN_3, AI8→AIN_2. Every panel-input number (b1 `ch`,
status `ai1…ai8`) goes through this table; driver calls take the ADC channel.

I²C addresses: TCA9535 0x20 · Si5351A 0x60 · SSD1306 OLED 0x3C.

Other NMR nets read by the firmware: **TX_IFLAG** and **TX_TFLAG** from the OPA564 (push-pull, 0/3.3 V,
active high = current limit / thermal). On the ordered v0.7 boards they end on the unfitted pull-ups R811 /
R812; the rework of 2026-10-08 (A2) wires those pads to GPIO6 / GPIO7 through 1 k. The firmware configures
both pins `INPUT_PULLDOWN`, so an unmodified board reads "no flag". The same rework plan adds the +VEXT sense
divider on GPIO4 (B6) and wires Si5351 CLK2 to panel input AI1 as the phase reference (A1, §3.9).

## 2. Shared drivers (`firmware/src/drivers/`)

All drivers are plain C++ classes, no Arduino libraries beyond `Wire.h` and `SPI.h`; every hardware access is
inside `#ifndef SIM`; under `SIM` the methods keep state and return plausible values. Header comments say what the
part does and which datasheet section the register writes come from.

### 2.1 `SpiBus.h` — the one lock on SPI2
```cpp
namespace spibus {
void begin();                 // SPI.begin(PIN_SPI_SCLK, PIN_SPI_MISO, PIN_SPI_MOSI) once; idempotent
bool lock(uint32_t timeout_ms = 50);   // FreeRTOS mutex; false on timeout
void unlock();
struct Guard { bool ok; Guard(uint32_t ms = 50); ~Guard(); };   // RAII
}
```
Every SPI transfer in `b1`, `b3`, the DDS driver and the NMR capture takes the lock. The capture task holds it
for the whole burst; `b1::loop()` skips its periodic read when `lock(0)` fails. Chip selects are per driver.

### 2.2 `Tca9535.h`
```cpp
class Tca9535 {
 public:
  bool begin(uint8_t addr = 0x20);      // write outputs (P1.4 = 1), then config (all outputs); returns ACK
  bool writePort(uint8_t port, uint8_t value);   // port 0 or 1
  bool writeBit(uint8_t port, uint8_t bit, bool level);   // read-modify-write on the cached value
  uint8_t cached(uint8_t port) const;
  bool readPort(uint8_t port, uint8_t& value);
  bool present() const;                 // false when begin() saw no ACK (bare dev board): callers degrade quietly
};
extern Tca9535 expander;                // one instance, defined in Tca9535.cpp, begun by BaseBlock::begin()
```
Registers (TCA9535 datasheet): input 0x00/0x01, output 0x02/0x03, polarity 0x04/0x05, configuration 0x06/0x07.

### 2.3 `Si5351.h` — clock generator (AN619 register map)
```cpp
class Si5351 {
 public:
  bool begin(uint8_t addr = 0x60, uint32_t xtal_hz = 25000000);  // crystal, 10 pF load setting; returns ACK
  double latticeStep() const;           // crystal / 2^27 = 0.186 Hz, the grid of §3.9
  static constexpr uint32_t kMsMax;     // 1800, the largest output multisynth divider used (all three clocks)
  static constexpr double kClk2MinHz;   // 900 MHz / (1800 × 128) = 3906 Hz, the slowest CLK2
  bool setClk0(uint32_t hz);            // PLLA integer mode → CLK0 = 50.000 MHz for the AD9834 MCLK
  bool setClk1(double hz);              // PLLB fractional (c = 2^19) → CLK1 = 4 × f_LO; exact on the lattice
  bool setClk2Exact(uint32_t beatWord); // CLK2 = beatWord × latticeStep() from PLLA (fractional MS2), output
                                        // left as it was (enable(2, on) switches it); 0 = off, powered down
  double actualClk0() const;            // the frequencies really programmed
  double actualClk1() const;
  double actualClk2() const;
  bool enable(uint8_t clk, bool on);
  bool resetPllB();                     // register 177 bit 7; call after any CLK1 change
  bool present() const;
};
extern Si5351 clockgen;
```
Sequence for an LO change (circuits note §9.2): `setClk1(4*f_lo)` → `resetPllB()` → pulse /CLR on the expander
(P1.4 low ≥ 1 µs, then high) so the quadrature counter always starts in state 00. Output drive 8 mA on CLK0 and
CLK1. `setClk1` picks R so the multisynth runs at 1 MHz or more and an even multisynth divider that is a multiple
of 32 / R, so MS × R is a multiple of 32 and a lattice frequency comes out exact (84 000.08 Hz LO: R = 4,
MS1 = 664, PLLB = 892.4 MHz). CLK2 is the phase reference (§3.9): PLLA (900 MHz, integer), a fractional MS2
with a denominator up to 2²⁰ − 1, R2 the smallest that brings MS2 to `kMsMax` = 1800 or below (5.4 kHz needs
R2 = 128, MS2 = 1302.08), 2 mA drive, register 18 = 0x0C (0x4C for an even integer divider); off and powered down
(register 18 = 0x80) when the console has no reference channel. Its output is enabled only while a scan set or a
bench `pulse` runs. All three clocks use one multisynth limit, 1800: AN619 §3.2 allows 2048, but 1800–2048 has
not been measured; it puts the slowest CLK2 at 3.9 kHz. `firmware/scripts/lattice_check.py` recomputes all of it
in exact fractions.

### 2.4 `Ad9834.h` — DDS (datasheet "Programming the AD9834")
```cpp
class Ad9834 {
 public:
  void begin(uint32_t mclk_hz = 50000000);   // FSYNC high, PSEL bit 0, RESET bit set
  void setFrequency(double hz);              // B28 = 1, FREQ0 as two 14-bit words; Δf = MCLK / 2^28
  double actualFrequency() const;
  uint32_t frequencyWord() const;            // the 28-bit word written: W of the lattice (§3.9)
  void setPhase(uint8_t reg, double deg);    // PHASE0 / PHASE1, 12-bit
  void setReset(bool on);                    // control-register RESET bit: 1 = output at midscale, phase cleared
  void selectPhase(bool p1);                 // PSEL bit in the control word (PIN/SW = 0)
  void sleep(bool on);                       // SLEEP1/SLEEP12 bits; output stops (used when the console is idle)
};
extern Ad9834 dds;
```
SPI: mode 2 (CPOL = 1, CPHA = 0), MSB first, 16-bit frames, FSYNC low for each frame, ≤ 40 MHz (use 10 MHz).
Control-register bits: B28 (13), HLB (12), FSEL (11), PSEL (10), PIN/SW (9), RESET (8), SLEEP1 (7), SLEEP12 (6),
OPBITEN (5), SIGN/PIB (4), DIV2 (3), MODE (1). Frequency words: FREQ0 = 0x4000 | bits, PHASE0 = 0xC000 | bits,
PHASE1 = 0xE000 | bits. The carrier free-runs; TX_EN gates the power stage, the DDS is never gated.
PIN/SW = 0: the board ties the RESET and SLEEP pins low (R817/R818) and FSELECT to ground, so RESET, SLEEP
and the phase select are register bits; the PSELECT pin (GPIO42) is ignored and held low. Reset during a
write: set the RESET bit, write FREQ0 and the PHASE registers, clear the RESET bit.

### 2.5 `Ads8688.h` — 8-channel 16-bit ADC (datasheet §8.5 command and program registers)
```cpp
class Ads8688 {
 public:
  // The one RST/PD pin is pulled up on the board (R102). Two NO_OP frames, then the eight range registers (their
  // echoes set present()), then AUTO_SEQ_EN = AIN_3 | AIN_2. No AUTO_RST here: burst() sends it.
  void begin();
  bool setRange(uint8_t ch /*0..7*/, uint8_t code);   // program register 0x05 + ch; codes 0, 1, 2, 5, 6 only
  int16_t readManual(uint8_t ch);            // MAN_CH_n (0xC000 + n*0x0400) then a NO_OP frame returns the data
  float toVolts(uint8_t ch, int16_t raw) const;
  // Burst: writes AUTO_SEQ_EN = mask, sends AUTO_RST (its frame carries the previous conversion and is
  // discarded), then one 32-bit NO_OP frame per conversion; fills `out` interleaved in ascending channel
  // order. Arduino SPI.transfer32 inside one SPI transaction, 17 MHz requested (16 MHz actual), SPI mode 1
  // (CPOL 0, CPHA 1), /CS driven through the GPIO set/clear registers. Returns n_per_channel (the count
  // requested) and reports the rate it reached in *achieved_hz.
  uint32_t burst(uint8_t mask, int16_t* out, uint32_t n_per_channel, uint32_t rate_hz, uint32_t* achieved_hz);
  static uint32_t periodUs(uint32_t rate_hz);   // the pacing: whole microseconds per scan of the mask
  bool present() const;
};
extern Ads8688 adc;
```
`burst()` runs on the caller's task (the NMR sequencer task on core 1) with the SPI lock held. It is paced
with `esp_timer_get_time()` to `1e6 / rate_hz` µs per scan of all channels in the mask: gaps under 1.5 ms are
busy-waited, longer ones yield with `vTaskDelay`. If the loop cannot keep up it free-runs, and `*achieved_hz`
(samples per channel per second, from the elapsed time) says what it reached. Target: 2 channels at 100 kS/s
each (default); try 250 kS/s and report what the hardware reaches. Ranges: AI7/AI8 (AIN_3/AIN_2) default ±5.12 V (code 1).
The auto scan returns channels in ascending order, so the NMR mask 0x0C gives Q (AIN_2) before I (AIN_3)
in each frame, and with the phase reference on AI1 the mask 0x0E gives R (AIN_1), Q, I; the sequencer works
out each channel's slot from the mask and `dsp::decimate` takes the stride and the slots. Three channels share
the 500 kS/s, so `rate_hz` is limited to 166 666 per channel with a reference. A rate that does not divide
1 MHz is really 1e6 / `periodUs(rate_hz)`; the reference fit uses that.

## 3. The `nmr` block (`firmware/src/blocks/nmr/NmrBlock.{h,cpp}` + `Sequencer.{h,cpp}` + `Dsp.{h,cpp}`)

`name()` = `"nmr"`. Registered in `main.cpp` after `b5`. The block owns the pins TX_EN, RX_BLANK and,
during a scan with a polarize step, FET_GATE and HB_IN1/2 (otherwise `b4` drives those from its own commands).

### 3.1 Commands (`PROTOCOL.md` §7)
| `cmd` | `args` | `result` |
|---|---|---|
| `config` | any subset of the settings below | the full effective settings incl. `f_tx_actual_hz`, `f_lo_actual_hz` (snapped to the lattice, §3.9), `clk2_actual_hz` with a reference |
| `start` | — | `{state:"running", n_avg}` — runs the scan set in the background |
| `abort` | — | `{state:"idle"}` |
| `pulse` | `{t_us}` (1..5000) | `{t_us, i_flag, t_flag}` — one TX gate without acquisition, for a scope check; refused on +VEXT (§3.2) |
| `clock` | `{clk:0..1, hz}` (CLK0 refused above 50 MHz) | `{clk, hz_actual}` — low-level Si5351 test |
| `dds` | `{hz, phase0_deg, phase1_deg, psel, on}` | the values programmed (`on`, default true, wakes the carrier) |
| `blank` | `{receive:bool}` | `{receive}` — manual RX_BLANK for bench tests |
| `get_record` | — | `{n, rate_hz, scan}` and the last averaged record is resent as a binary frame |
| `sim_larmor` | `{hz}` (SIM only) | `{hz}` — the simulated Larmor frequency |

Settings (defaults): `f_tx_hz` 89400 · `f_lo_hz` 84000 (IF = f_tx − f_lo = 5400 Hz; the sign of the IF tells the
app which side of the LO the line is on) · `sequence` `"fid"` or `"echo"` · `t90_us` 417 · `t180_us` 834 ·
`tau_us` 20000 (echo only) · `t_blank_pre_us` 20 (RX blanked this long before TX_EN rises) · `t_dead_us` 1000
(TX_EN low → RX_BLANK high) · `t_acq_start_us` 1200 (from the end of the pulse to the first ADC sample) ·
`t_acq_ms` 2000 (record length; max 4000) · `rate_hz` 100000 per channel (≤ 250000; ≤ 166666 with `ref_ch`) · `decim` 4 (the decimated rate, paced rate / `decim`, must exceed 2 x |IF| or the line folds over: 25 kS/s for a 5.4 kHz IF; `config` rejects a `decim` that breaks this) · `n_avg` 1 (1..256) ·
`cyclops` true (pulse phase 0/90/180/270 cycled across scans, receiver record rotated back before averaging) ·
`t_repeat_ms` 3000 (time between scans; ≥ 3 × T1 ≈ 3 s for water) · `polarize_ms` 0 (Earth's field: FET_GATE
on for this long before the pulse, then off and `t_polarize_settle_ms` 15 before the pulse) · `hb_mode` `"off"`
(`"fwd"`, `"rev"`: HB_IN1/2 during the polarize step for field cycling) · `ref_ch` 1 (the panel input carrying
Si5351 CLK2, 1..6; the rework wires AI1 on every board, Decision #85; 0 = no phase reference; needs 3.91 kHz ≤ |IF| < 30 kHz
and a `rate_hz` that folds no odd harmonic of the IF onto it, §3.9). `f_lo_hz` is snapped
to the nearest even lattice step (0.37 Hz) and `if_hz` is exact (§3.9).

### 3.2 Timing of one scan (circuits note §9.3) — on a FreeRTOS task pinned to core 1, priority high
1. (optional) polarize: FET_GATE = 1 (+ H-bridge) for `polarize_ms`; FET_GATE = 0; wait `t_polarize_settle_ms`.
2. The pulse phase for this scan: as built, PHASE0 = the pulse phase and PHASE1 = that phase + 90° are
   loaded and PHASE0 is selected (§3.7); the carrier free-runs.
3. RX_BLANK = 0 (blanked), wait `t_blank_pre_us`.
4. TX_EN = 1 for `t90_us`; TX_EN = 0. (`echo`: wait `tau_us`, then select PHASE1 (+90°) with one control-word
   write, TX_EN = 1 for `t180_us`, TX_EN = 0; the write lengthens the spacing, §3.7.) TX_IFLAG / TX_TFLAG
   (GPIO6 / GPIO7) are read in the last microsecond of every gate, while the amplifier still drives, and again
   just after TX_EN falls; a flag stops the scan set here, before the receiver opens.
5. wait `t_dead_us`; RX_BLANK = 1.
6. at `t_acq_start_us` after the last pulse end: `adc.burst(mask, buf, n, rate_hz, &achieved)` with the SPI lock
   held, mask = AIN_3 | AIN_2 (I, Q) and the reference channel when `ref_ch` is set;
   `n = t_acq_ms * rate_hz / 1000` per channel, buffer in PSRAM (`heap_caps_malloc(..., MALLOC_CAP_SPIRAM)`).
7. RX_BLANK = 0 (blanked between scans keeps the LNA quiet). Read the flags again: a current-limit flag → abort
   the scan set with `error:"current limit - check the coil and the gain jumper"`; a thermal flag →
   `error:"thermal - duty cycle too high"`. Never keep pulsing on a flag. Without rework A2 the pull-downs make
   both read 0. With `ref_ch`: the reference phase of this scan (§3.9).
8. Processing on the same task (§3.3), then post the averaged record to the main task; wait `t_repeat_ms`.

Before a scan set (`start`) and before a `pulse`, while `b2 vext_check` is on and `b2` has a reading
(`blocks/Vext.h`): +VEXT below 6.5 V → refused with *"+VEXT below 6.5 V (reads x V) - bench supply off? (or b2
vext_check off if the sense divider is not fitted)"*; above 25 V → *"+VEXT above 25 V (reads x V) - OPA564 limit
(or …)"*. Below 16 V the status says `tx_clip_warning: true` (the gain-25 output clips) and the pulse goes out.
Timing uses `esp_timer_get_time()` busy-waits inside a `portDISABLE_INTERRUPTS()`-free critical region no
longer than the pulse itself; interrupts stay on (WiFi runs on core 0). Microsecond jitter is acceptable: the
received phase evolves at the IF rate, so 1 µs is ≈ 2°.

### 3.3 Processing (`Dsp.{h,cpp}`, plain float, no library)
- DC offset per channel: the receiver is blanked before the pulse, so the offset cannot be measured there.
  Rule: offset = mean of the **last 10 %** of the record when `t_acq_ms ≥ 1000` (the FID has largely decayed,
  T2* ≈ 0.3–1 s in water at 2 mT), else the mean of the whole record. Subtract per channel.
- Decimate by `decim` (boxcar average of `decim` samples) → complex record z[k] = I + jQ at the paced rate / `decim`
  (the burst paces whole microseconds, so the paced rate is 1e6 / round(1e6 / `rate_hz`); the frame header,
  the spectrum and the reference fit all use it); the boxcar loses 0.6 dB at 5.4 kHz for decim 4 at 100 kS/s, acceptable; never let `rate_hz / decim < 2 x |IF|`.
- CYCLOPS: multiply the record by `exp(-j·phase_pulse)`; with a phase reference, by `exp(-j·Δφ_beat)` as well
  (§3.9), in the same rotation; accumulate the running mean over the scans done.
- Spectrum for status only: radix-2 complex FFT of the averaged record zero-padded to the next power of two
  (≤ 16384 points); Hann window; report `peak_hz` (signed IF frequency, positive = above the LO), `peak_amp`
  (V rms), `noise_rms` (median of the magnitude away from the peak), `snr_db`, and `larmor_hz` = the LO as programmed (`f_lo_actual_hz`) + `peak_hz`.
- The app receives the averaged **time-domain** complex record (§3.4) and computes its own spectrum in JS.

### 3.4 Binary frame, kind 3 (extends `PROTOCOL.md` §6; same 28-byte header)
`uint8 kind = 3` · `uint8 block_id = 9` · `uint8 ch = 0` · `uint8 bits = 32` (float32 pairs) · `uint32 t_ms` ·
`uint32 rate_hz` (the decimated rate) · `uint32 n` (complex samples) · `int32 trig_index` = scans averaged so
far · `float32 volts_per_lsb` = 1.0 · `float32 offset_v` = the IF frequency programmed (`f_tx − f_lo`, Hz, so the
app can label the axis in Larmor Hz) · then `n × (float32 I, float32 Q)` in volts at the ADC input. Sent to every
client after every scan (`ws.binaryAll`); `get_record` resends the last one. Because block code runs on the main
task, the sequencer posts a "record ready" flag and the main task serialises the frame in `loop()`.

### 3.5 Status keys
`state` (idle / running / done / error) · `scan` · `n_avg` · `f_tx_hz` · `f_lo_hz` · `if_hz` (exact) · `rate_hz`
(achieved, per channel) · `peak_hz` · `larmor_hz` (= the LO as programmed + `peak_hz`) · `peak_amp` · `snr_db` ·
`ref_ch` · `ref_phase_deg` · `ref_amp` (V) · `i_flag` · `t_flag` (true/false) · `tx_clip_warning` · `error`
(string, when state = error) · `sim` (bool).

### 3.6 SIM behaviour
Under `-DSIM=1` the sequencer runs the same state machine with the same delays (so the app and the timing are
exercised on a bare dev board) and its own synthesiser `Sequencer::simBurst` takes the place of the ADC burst: an FID
`A·exp(−t/T2*)·exp(j·2π·(f_larmor_sim − f_lo)·t + j·φ_pulse)` with A = 20 µV × LNA gain 1000 × mixer gain (≈ 0.9)
≈ 18 mV at the ADC, T2* = 0.4 s, white noise 3 mV rms, a 50 Hz hum line at 2 mV with a different phase every
scan, DC offsets of +5 mV (I) and −4 mV (Q), `f_larmor_sim` = 89 400 Hz (settable by `sim_larmor`). Since
2026-10-08 every scan also gets a random beat phase (`esp_random()`), as the hardware does (§3.8), and with
`ref_ch` set (the default, 1) the reference input carries a 0–3.3 V square wave at |IF| whose phase follows that
beat (the other way for a negative IF) plus a fixed 0.7 rad lag. So the SIM build shows the correction by
default, and the defect with `ref_ch` 0: there, averaging scans cancels part of the signal and the SNR does not
grow; with the reference it grows by √N (checked with a Python port of the arithmetic; the SIM build itself has
not been run since).
`b2` reports +VEXT = 24.0 V.

### 3.7 As built (2026-09-13)

Three details of the block as written differ from §3.1–§3.6 above; they are refinements, not
disagreements, and the code is the authority for them.

* **Phase registers.** The scan-set preparation is exactly as §3.2 says (RESET → frequency → PHASE0 = 0,
  PHASE1 = 180 → RESET off), but each scan then loads PHASE0 = the pulse phase of that scan and
  PHASE1 = that phase + 90°, and selects PHASE0 with the PSEL bit. For a free induction decay that is
  the same thing as §3.2; for an echo it is what lets the refocusing pulse be 90° out of phase with
  one control-word write instead of reloading a phase register in the middle of a sequence. The write
  is made **after** `tau_us` has elapsed and before TX_EN rises, so it lengthens the pulse spacing by
  the time of one SPI write under the lock (a few microseconds). `tau_us` is measured edge to edge,
  from the end of the 90° pulse to that write, not centre to centre.
* **Memory.** The capture buffer is grown on demand at `config` rather than allocated for the absolute
  maximum at `begin()`: 2 channels × 4000 ms × 250 kS/s really is 4 MB, and holding that plus the
  outgoing record permanently would be 6 of the board's 8 MB. `config` refuses what does not fit
  (PROTOCOL.md §7.2) and the buffer is never shrunk, so it is allocated at most a handful of times in
  a session. The record frame doubles as the running-mean accumulator, which saves a copy of it.
* **`dds` takes an `on` argument** (default true) so a bench test can stop the carrier again; the idle
  console keeps the DDS asleep.

### 3.8 Scan-to-scan phase (open problem, 2026-10-08)

The complex running mean of §3.3 assumes that every scan's record starts at the same IF phase. As built it
does not. The carrier (AD9834, clocked by Si5351 CLK0) and the local oscillator (Si5351 CLK1) free-run for the
whole scan set from the same crystal, so the IF reference is coherent with the Si5351 and its phase advances
continuously at f_tx − f_lo. The scans are not: they are spaced by `vTaskDelay` (`t_repeat_ms`, the polarize
step) and the pulse starts on a busy-wait, neither tied to the IF. Each pulse therefore lands at an effectively
random point of the IF cycle (185 µs at 5.4 kHz), and the record of each scan starts with a random phase.
Averaging such records attenuates the signal instead of the noise, and the CYCLOPS rotation by the pulse
phase loses its meaning. The SIM build reproduces this (§3.6).

Decided 2026-10-08 (rework plan, items A1 and C): a hardware phase reference. Si5351 CLK2 is programmed to
exactly f_tx − f_lo and wired to a panel input; its phase in each record is that scan's beat phase, and the
record is rotated by it before averaging (§3.9). Without the wire (`ref_ch` 0) the console behaves as described
above. A trigger variant for the next board revision (CLK2 on GPIO15, the pulse started on its edge) is kept
open in `pins.h` (`PIN_REF_CLK`).

### 3.9 Phase reference (rework A1, 2026-10-08)

**Why it works.** The phase of the signal at the start of a record is (f_tx − f_lo) × t_pulse modulo one cycle,
plus constants: the carrier sets the phase of the nuclear precession, the LO demodulates it. Both come from the
Si5351's crystal, so the beat between them is a fixed clock; the firmware fires each pulse at an arbitrary point
of its cycle. A third output of the same crystal, CLK2, at exactly f_tx − f_lo carries the same beat phase. It is
recorded alongside I and Q, its phase at the start of each record is measured, and the record is rotated so that
every scan matches the first.

**Exactness.** CLK2 must equal the beat to the last digit: a 1 mHz error drifts 280° over a 13-minute scan set. So
all three frequencies sit on one lattice of the crystal (Si5351.h, `scripts/lattice_check.py`):

| Clock | Frequency | How |
|---|---|---|
| carrier | f_tx = W × 25 MHz / 2²⁷ | AD9834 word W over 2²⁸ at MCLK = CLK0 = 50 MHz = 25 MHz × 36 / 18 (PLLA, integer) |
| LO | f_lo = V × 25 MHz / 2²⁷, V even | CLK1 = 4 f_lo from PLLB = 25 MHz × (a + b / 2¹⁹), MS1 × R1 a multiple of 32: a + b/c = V × MS1 × R1 / 2²⁵ is exact |
| reference | CLK2 = (W − V) × 25 MHz / 2²⁷ | PLLA 900 MHz / (MS2 × R2), MS2 = 36 × 2²⁷ / ((W − V) R2) as a reduced fraction, denominator < 2²⁰ |

`config` snaps `f_lo_hz` to the nearest even V (steps of 0.37 Hz; 84 000 → 84 000.08 Hz) and reports
`f_lo_actual_hz`, the exact `if_hz` = (W − V) × 25 MHz / 2²⁷ (5 399.99 Hz at the defaults) and `clk2_actual_hz`.
The slowest CLK2 is 900 MHz / (1800 × 128) = 3.91 kHz, so `ref_ch` needs |IF| ≥ 3.91 kHz; the Earth's-field case
(f_tx 2.1 kHz, f_lo 1.9 kHz, IF 200 Hz: the LO lands on 1 899.90 Hz exactly, but CLK2 cannot make 200 Hz) has no
reference: `config` refuses it until `ref_ch` is 0.

**Wiring and settings.** Test point TP701 (CLK2 through R705 33 Ω) to panel input AI1 (ADS8688 AIN_1): an SMA
pigtail or a wire. The rework is fitted on every board (Decision #85), so `ref_ch` is 1 by default in both
builds: AIN_1 joins the burst (frames R, Q, I; ≤ 166 666 S/s per channel), CLK2 runs (2 mA) during every scan set
and bench `pulse`, off while the console is idle, and the correction is on. A board without the wire fails its first scan set with *"reference tone missing on AI1 - is CLK2 wired?"*;
`config {ref_ch: 0}` then turns CLK2 off and the console runs without the correction.

**Per scan.** After the burst: a least-squares fit of m + A cos(ωk + φ) to the reference samples of the first
20 ms of the record (about a hundred cycles at 5.4 kHz), ω = 2π |IF| / f_s with f_s the paced sample rate
(`dsp::fitTone`: three linear unknowns, float accumulation, solved in double). φ_ref is the phase of the tone at
the first sample; A in volts is `ref_amp` (2.1 V for the 0–3.3 V square wave's fundamental). The first scan's
φ_ref is the set's φ_ref0. The record is rotated by −(φ_ref − φ_ref0) (by +(φ_ref − φ_ref0) for a negative IF,
where CLK2 runs at |IF| and its phase turns the other way), in the same rotation as CYCLOPS, then averaged. The
first scan is unchanged; every other one is lined up with it. Constant offsets (the cable, the converter's input
filter, the 2 µs between the R and the I/Q samples of a frame) cancel in the difference. Status: `ref_ch`,
`ref_phase_deg` (this scan's φ_ref), `ref_amp`.

**Limits.** `config` refuses `ref_ch` when |IF| < 3.91 kHz (CLK2 cannot be that slow), when |IF| ≥ 30 kHz (*"ref_ch
needs an IF below 30 kHz"*: the ADS8688's own second-order filter, about 15 kHz, takes the tone away), and when an
odd harmonic of the square wave (3rd to 9th) folds back to within 100 Hz of the IF at the paced sample rate
(*"rate_hz folds a reference harmonic onto the IF - change rate_hz"*: the fit would take it for part of the
fundamental). The defaults pass all three. A `config` whose CLK2 cannot be programmed is refused with *"CLK2 could
not be set to the IF - check the Si5351"* and leaves the old settings in place.

**Keeping the common phase.** Within a scan set the DDS is never reset or put to sleep and the Johnson counter is
never cleared, or the reference and the data lose their common phase. Everything that resets a phase
(`programClocks`, the DDS reset, the counter clear, the PLL resets) happens once, in `prepareHardware()`, before the
first scan. A bench `clock` or `dds` command switches CLK2 off and `if_hz` then reports what those commands set;
the next `config` or scan set reprograms the lattice.

**Checks.** `ref_amp` under 0.2 V stops the set (*"reference tone missing on AI1 - is CLK2 wired?"*); an unwired
input is expected to read a steady level and no tone (not yet measured). A burst more than 1 % behind the paced rate stops it (*"ADC fell
behind rate_hz on three channels - lower rate_hz"*): the fit assumes the paced sample instants. Bench check (rework
plan A1): a scope on AI1 shows the CLK2 square wave at the IF; two scans 3 s apart show the same I/Q phase at
the start of the FID. None of this has run on a board.

## 4. Changes to existing blocks (drivers agent)
- `b5`: DIO1–8 through `expander.writePort(0, mask)`; `PIN_DIO[]` removed from `pins.h`. Fast outputs and TRIG
  unchanged. If the expander is absent, `dio` commands return `error:"expander not present"`.
- `b4`: module outputs through `expander.writeBit(1, EXP_BIT_MOD[n-1], on)` (`module {n:1..7, on}`, `module_all {on}`);
  new commands `hbridge {mode: off|fwd|rev|brake}` (HB_IN1/2
  = 0/0, 1/0, 0/1, 1/1) and `polarizer {on, ms}` (FET_GATE, switched off again after at most `ms`, ≤ 10 000 ms);
  status adds `hbridge`, `polarizer`. Both refuse with `error:"nmr scan running"` while `nmr` is running
  (`nmr_busy()` and `g_nmrBusy` live in `blocks/Busy.h`, so `b4` does not include the nmr block).
- `b1`: real ADS8688 reads through `adc.readManual` under the SPI lock; `set_range` through `adc.setRange`.
- `b3`: DAC8563 frames are real SPI transfers under the SPI lock (AO = 10.05 V × (code − 32768)/32768).
- `base`: `expander.begin()`, `clockgen.begin()`, `spibus::begin()` in `BaseBlock::begin()`; `info` adds
  `expander` and `clockgen` presence.
- `b2` (2026-10-08, rework B6): +VEXT on GPIO4 (11:1 divider, 11 dB attenuation, `analogReadMilliVolts`, 16
  readings averaged at 2 Hz) into `g_vextVolts` (`blocks/Vext.h`, the same pattern as `Busy.h`); status `vext`,
  `vext_measured`, `vext_check`; command `vext_check {on}` (RAM only, on at start-up) into `g_vextCheck`.

## 5. The app (`host/pwa/panels/nmr.js`) and the Python client (`host/instrument.py`)
- Tab **NMR**: settings form (f_tx, f_lo, sequence, t90, t_acq, n_avg, cyclops, polarize, phase reference
  none / AI1…AI6 = `ref_ch`) → `config`; the reference phase and amplitude in the progress line; buttons
  Start / Abort / Pulse; a progress line (scan i / n, achieved rate, flags); two canvases: **FID** (|z| and I, Q
  vs time) and **Spectrum** (JS radix-2 FFT of the received record, Hann window, x-axis in Hz relative to the
  LO with a second label row in Larmor Hz = f_lo + f, a marker on the peak, SNR in the corner). Binary frames
  arrive on the same WebSocket; `app.js` already gives panels `api.on('status', …)`; add `api.on('binary', …)`
  dispatch by `kind` (kind 3 → the nmr panel) in `app.js` if it does not exist yet. Phone-first: everything
  stacks at 400 px; touch targets ≥ 44 px; the canvases redraw on resize.
- `instrument.py`: `nmr_config(**kw)`, `nmr_start()`, `nmr_wait(timeout_s)` (polls status), `nmr_record()`
  (returns rate, numpy complex array, n_avg) and `nmr_spectrum()` (numpy FFT, Hz relative to the LO); a
  `python instrument.py nmr --n-avg 8 --csv fid.csv` sub-command. ruff clean (line length 140 as configured in `host/pyproject.toml`).

## 6. Build and verification
`pio run -d firmware -e esp32s3-sim` and `pio run -d firmware -e esp32s3` must both compile warning-free for the
new files. No hardware exists yet: the sim build is the test — flash it only when the user asks. Keep every
hardware access inside `#ifndef SIM`. No secrets, no hour/minute estimates, no "homework" in any comment.
