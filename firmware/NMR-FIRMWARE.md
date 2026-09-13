# NMR console firmware — design contract (class board v0.7, 2026-09-13)

This file is the contract between the drivers, the `nmr` block, the phone app and the Python client.
Design authority: the course repo notes `2026-09-13-v07-nmr-circuits.md` (§9 firmware notes) and
`2026-09-13-nmr-respec-proposal.md` (§8.2 GPIO map); the schematic `hardware/sheets/nmr_rx.kicad_sch`,
`nmr_tx.kicad_sch`, `c_switch.kicad_sch`, `b5_dio_trig.kicad_sch` (TCA9535). When code and this file
disagree, fix the code; when this file and the schematic disagree, the schematic wins — then fix this file.

Demo regime: proton NMR in water at **B0 ≈ 2.1 mT, f_Larmor ≈ 89.4 kHz**, thermal polarization, free
induction decay (FID) after a 90° pulse, heterodyne I/Q receiver, IF ≈ 5.4 kHz into ADS8688 channels 7 (I)
and 8 (Q). Earth's-field NMR (≈ 2 kHz, with the polarizer coil) is the stretch goal on the same code path.

## 1. GPIO map v0.7 (`include/pins.h`)

| GPIO | Constant | Net | Function | Section |
|---|---|---|---|---|
| 12 / 11 / 13 | `PIN_SPI_SCLK/MOSI/MISO` | SPI_* | SPI2 on IO_MUX pins, shared by ADC, DAC, DDS | base |
| 10 | `PIN_CS_ADC` | CS_ADC | ADS8688 /CS | A |
| 5 | `PIN_CS_DAC` | CS_DAC | DAC8563 /SYNC (via 74HCT125) | B |
| 1 / 2 | `PIN_I2C_SDA/SCL` | I2C_* | 400 kHz; OLED 0x3C, TCA9535 0x20, Si5351A 0x60 | base |
| 16 / 17 | `PIN_OPTO_IN[0..1]` | OPTO_IN1/2 | 6N137 outputs, active LOW | C |
| 18 / 21 | `PIN_FAST_OUT[0..1]` | FAST_OUT1/2 | 74HCT125 → terminals | B |
| 38 / 39 | `PIN_TRIG_IO`, `PIN_TRIG_DIR` | TRIG_IO/DIR | 74LVC1T45; DIR 1 = output to the SMA | B |
| 41 | `PIN_DDS_FSYNC` | DDS_FSYNC | AD9834 frame sync (its SPI chip select, active low) | B |
| 42 | `PIN_DDS_PSEL` | DDS_PSEL | AD9834 phase-register select (0 = PHASE0, 1 = PHASE1) | B |
| 40 | `PIN_TX_EN` | TX_EN | OPA564 enable = transmit gate (10 k pull-down; 1 = transmit) | B |
| 8 | `PIN_RX_BLANK` | RX_BLANK | DG419 receiver blanking: **0 = blanked (default, pull-down), 1 = receive** | A |
| 9 / 14 | `PIN_HB_IN1`, `PIN_HB_IN2` | HB_IN1/2 | DRV8871 H-bridge inputs (10 k pull-downs; 0/0 = coast) | C |
| 47 | `PIN_FET_GATE` | FET_GATE | UCC27517 → AOD4184A polarizer switch (1 = polarizer coil on) | C |
| 4 / 6 / 7 / 15 | `PIN_EXP[0..3]` | GPIO4/6/7/15 | free, on the 2×10 expansion header | base |
| 43 / 44 | — | GPIO43/44 | header; LED_WIFI/ACT via JP1/JP2; not driven by firmware | base |
| 19 / 20 | — | USB_DN/DP | native USB | base |
| 48 | `PIN_RGB_LED` | — | WS2812 on the dev board | — |
| 0/45/46, 3, 35–37 | — | — | never used (strapping, unused, PSRAM) | — |

TCA9535 I²C expander (address 0x20, A0 = A1 = A2 = GND): **P0.0–P0.7 = DIO1–8** (→ 74AHCT541 → terminals),
**P1.0–P1.3 = RLY_IN1–4** (relay gates, active high, 10 k pull-downs keep them off at boot), **P1.4 = /CLR of
the 74HC74 Johnson counter** (10 k pull-up; pulse low to reset the quadrature LO to state 00), P1.5–P1.7 spare
on test points. All 16 lines are outputs; the expander powers up with every port as an input, so `begin()` writes
the output registers first (all zero except P1.4 = 1), then the configuration registers.

I²C addresses: TCA9535 0x20 · Si5351A 0x60 · SSD1306 OLED 0x3C.

Other NMR nets read by the firmware: **I_FLAG** and **T_FLAG** from the OPA564 (push-pull, 0/3.3 V, active
high = current limit / thermal). Look up their pins in `hardware/sheets/nmr_tx.kicad_sch` (search the
net names); if they are on the expander spare lines P1.5/P1.6, read them through the TCA9535 (configure those
two as inputs); if they are on test points only, report them as "not connected" in status and skip.

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
  bool setInputs(uint8_t port, uint8_t mask);    // bits that become inputs (I_FLAG / T_FLAG if wired there)
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
  bool setClk0(uint32_t hz);            // PLLA integer mode → CLK0 = 50.000 MHz for the AD9834 MCLK
  bool setClk1(double hz);              // PLLB fractional → CLK1 = 4 × f_LO (the Johnson counter divides by 4)
  double actualClk1() const;            // the frequency really programmed
  bool enable(uint8_t clk, bool on);
  bool resetPllB();                     // register 177 bit 7; call after any CLK1 change
  bool present() const;
};
extern Si5351 clockgen;
```
Sequence for an LO change (circuits note §9.2): `setClk1(4*f_lo)` → `resetPllB()` → pulse /CLR on the expander
(P1.4 low ≥ 1 µs, then high) so the quadrature counter always starts in state 00. CLK2 unused. Output drive 8 mA.

### 2.4 `Ad9834.h` — DDS (datasheet "Programming the AD9834")
```cpp
class Ad9834 {
 public:
  void begin(uint32_t mclk_hz = 50000000);   // FSYNC high, PSEL low, RESET bit set
  void setFrequency(double hz);              // B28 = 1, FREQ0 as two 14-bit words; Δf = MCLK / 2^28
  double actualFrequency() const;
  void setPhase(uint8_t reg, double deg);    // PHASE0 / PHASE1, 12-bit
  void setReset(bool on);                    // control-register RESET bit: 1 = output at midscale, phase cleared
  void selectPhase(bool p1);                 // drives PIN_DDS_PSEL (hardware PSELECT: control bit PIN/SW = 1)
  void sleep(bool on);                       // SLEEP1/SLEEP12 bits; output stops (used when the console is idle)
};
extern Ad9834 dds;
```
SPI: mode 2 (CPOL = 1, CPHA = 0), MSB first, 16-bit frames, FSYNC low for each frame, ≤ 40 MHz (use 10 MHz).
Control-register bits: B28 (13), HLB (12), FSEL (11), PSEL (10), PIN/SW (9), RESET (8), SLEEP1 (7), SLEEP12 (6),
OPBITEN (5), SIGN/PIB (4), DIV2 (3), MODE (1). Frequency words: FREQ0 = 0x4000 | bits, PHASE0 = 0xC000 | bits,
PHASE1 = 0xE000 | bits. The carrier free-runs; TX_EN gates the power stage, the DDS is never gated.

### 2.5 `Ads8688.h` — 8-channel 16-bit ADC (datasheet §8.5 command and program registers)
```cpp
class Ads8688 {
 public:
  void begin();                              // /RST and /PD are pulled high on the board; NO_OP, AUTO_RST
  bool setRange(uint8_t ch /*0..7*/, uint8_t code);   // program register 0x05 + ch; codes as in InputsBlock.h
  int16_t readManual(uint8_t ch);            // MAN_CH_n (0xC000 + n*0x0400) then a NO_OP frame returns the data
  float toVolts(uint8_t ch, int16_t raw) const;
  // Burst: AUTO_RST scan over the channels in `mask` (bit n = channel n), one 32-bit frame per conversion,
  // as fast as the loop allows; fills `out` interleaved in channel order; returns samples per channel achieved.
  // Uses spi_device_polling_transmit on a dedicated device handle at 17 MHz (SPI mode 1: CPOL 0, CPHA 1).
  uint32_t burst(uint8_t mask, int16_t* out, uint32_t n_per_channel, uint32_t rate_hz, uint32_t* achieved_hz);
};
extern Ads8688 adc;
```
`burst()` runs on the caller's task (the NMR sequencer task on core 1) with the SPI lock held. Pace it with
`esp_timer_get_time()` so the sample interval is `1e6 / rate_hz` µs per scan of all channels in the mask; if the
loop cannot keep up, report the achieved rate rather than fail. Target: 2 channels at 100 kS/s each (default);
try 250 kS/s and report what the hardware reaches. Ranges: AIN7/8 default ±5.12 V (code 1).

## 3. The `nmr` block (`firmware/src/blocks/nmr/NmrBlock.{h,cpp}` + `Sequencer.{h,cpp}` + `Dsp.{h,cpp}`)

`name()` = `"nmr"`. Registered in `main.cpp` after `b5`. The block owns the pins TX_EN, RX_BLANK, DDS_PSEL and,
during a scan with a polarize step, FET_GATE and HB_IN1/2 (otherwise `b4` drives those from its own commands).

### 3.1 Commands (`PROTOCOL.md` §7)
| `cmd` | `args` | `result` |
|---|---|---|
| `config` | any subset of the settings below | the full effective settings incl. `f_tx_actual_hz`, `f_lo_actual_hz` |
| `start` | — | `{state:"running", n_avg}` — runs the scan set in the background |
| `abort` | — | `{state:"idle"}` |
| `pulse` | `{t_us}` (1..5000) | `{t_us}` — one TX gate without acquisition, for a scope check |
| `clock` | `{clk:0..1, hz}` | `{clk, hz_actual}` — low-level Si5351 test |
| `dds` | `{hz, phase0_deg, phase1_deg, psel}` | the values programmed |
| `blank` | `{receive:bool}` | `{receive}` — manual RX_BLANK for bench tests |
| `get_record` | — | `{n, rate_hz}` and the last averaged record is resent as a binary frame |
| `sim_larmor` | `{hz}` (SIM only) | `{hz}` — the simulated Larmor frequency |

Settings (defaults): `f_tx_hz` 89400 · `f_lo_hz` 84000 (IF = f_tx − f_lo = 5400 Hz; the sign of the IF tells the
app which side of the LO the line is on) · `sequence` `"fid"` or `"echo"` · `t90_us` 417 · `t180_us` 834 ·
`tau_us` 20000 (echo only) · `t_blank_pre_us` 20 (RX blanked this long before TX_EN rises) · `t_dead_us` 1000
(TX_EN low → RX_BLANK high) · `t_acq_start_us` 1200 (from the end of the pulse to the first ADC sample) ·
`t_acq_ms` 2000 (record length; max 4000) · `rate_hz` 100000 per channel · `decim` 4 (the decimated rate `rate_hz / decim` must exceed 2 x |IF| or the line folds over: 25 kS/s for a 5.4 kHz IF; `config` rejects a `decim` that breaks this) · `n_avg` 1 (1..256) ·
`cyclops` true (pulse phase 0/90/180/270 cycled across scans, receiver record rotated back before averaging) ·
`t_repeat_ms` 3000 (time between scans; ≥ 3 × T1 ≈ 3 s for water) · `polarize_ms` 0 (Earth's field: FET_GATE
on for this long before the pulse, then off and `t_polarize_settle_ms` 5 before the pulse) · `hb_mode` `"off"`
(`"fwd"`, `"rev"`: HB_IN1/2 during the polarize step for field cycling).

### 3.2 Timing of one scan (circuits note §9.3) — on a FreeRTOS task pinned to core 1, priority high
1. (optional) polarize: FET_GATE = 1 (+ H-bridge) for `polarize_ms`; FET_GATE = 0; wait `t_polarize_settle_ms`.
2. `DDS_PSEL` = the pulse phase for this scan (PHASE0/PHASE1 preloaded; for 90°/270° reload PHASE1 before
   the scan; `dds.setReset(false)` and the carrier free-runs).
3. RX_BLANK = 0 (blanked), wait `t_blank_pre_us`.
4. TX_EN = 1 for `t90_us`; TX_EN = 0. (`echo`: wait `tau_us`, TX_EN = 1 for `t180_us` with +90° phase, TX_EN = 0.)
5. wait `t_dead_us`; RX_BLANK = 1.
6. at `t_acq_start_us` after the last pulse end: `adc.burst(mask ch7|ch8, buf, n, rate_hz, &achieved)` with the
   SPI lock held; `n = t_acq_ms * rate_hz / 1000` per channel, buffer in PSRAM (`heap_caps_malloc(..., MALLOC_CAP_SPIRAM)`).
7. RX_BLANK = 0 (blanked between scans keeps the LNA quiet). Read I_FLAG / T_FLAG: a current-limit flag during
   the pulse → abort the scan set with `error:"current limit — check the coil and the gain jumper"`; a thermal
   flag → `error:"thermal — duty cycle too high"`. Never keep pulsing on a flag.
8. Processing on the same task (§3.3), then post the averaged record to the main task; wait `t_repeat_ms`.
Timing uses `esp_timer_get_time()` busy-waits inside a `portDISABLE_INTERRUPTS()`-free critical region no
longer than the pulse itself; interrupts stay on (WiFi runs on core 0). Microsecond jitter is acceptable: the
received phase evolves at the IF rate, so 1 µs is ≈ 2°.

### 3.3 Processing (`Dsp.{h,cpp}`, plain float, no library)
- DC offset per channel: the receiver is blanked before the pulse, so the offset cannot be measured there.
  Rule: offset = mean of the **last 10 %** of the record when `t_acq_ms ≥ 1000` (the FID has largely decayed,
  T2* ≈ 0.3–1 s in water at 2 mT), else the mean of the whole record. Subtract per channel.
- Decimate by `decim` (boxcar average of `decim` samples) → complex record z[k] = I + jQ at `rate_hz / decim`; the boxcar loses 0.6 dB at 5.4 kHz for decim 4 at 100 kS/s, acceptable; never let `rate_hz / decim < 2 x |IF|`.
- CYCLOPS: multiply the record by `exp(-j·phase_pulse)`; accumulate the running mean over the scans done.
- Spectrum for status only: radix-2 complex FFT of the averaged record zero-padded to the next power of two
  (≤ 16384 points); Hann window; report `peak_hz` (signed IF frequency, positive = above the LO), `peak_amp`
  (V rms), `noise_rms` (median of the magnitude away from the peak), `snr_db`, and `larmor_hz = f_lo + peak_hz`.
- The app receives the averaged **time-domain** complex record (§3.4) and computes its own spectrum in JS.

### 3.4 Binary frame, kind 3 (extends `PROTOCOL.md` §6; same 28-byte header)
`uint8 kind = 3` · `uint8 block_id = 9` · `uint8 ch = 0` · `uint8 bits = 32` (float32 pairs) · `uint32 t_ms` ·
`uint32 rate_hz` (the decimated rate) · `uint32 n` (complex samples) · `int32 trig_index` = scans averaged so
far · `float32 volts_per_lsb` = 1.0 · `float32 offset_v` = the IF frequency programmed (`f_tx − f_lo`, Hz, so the
app can label the axis in Larmor Hz) · then `n × (float32 I, float32 Q)` in volts at the ADC input. Sent to every
client after every scan (`ws.binaryAll`); `get_record` resends the last one. Because block code runs on the main
task, the sequencer posts a "record ready" flag and the main task serialises the frame in `loop()`.

### 3.5 Status keys
`state` (idle / running / done / error) · `scan` · `n_avg` · `f_tx_hz` · `f_lo_hz` · `if_hz` · `rate_hz` (achieved)
· `peak_hz` · `larmor_hz` · `peak_amp` · `snr_db` · `i_flag` · `t_flag` · `error` (string, when state = error) ·
`sim` (bool).

### 3.6 SIM behaviour
Under `-DSIM=1` the sequencer runs the same state machine with the same delays (so the app and the timing are
exercised on a bare dev board) and `Ads8688::burst` is replaced by a synthesiser: an FID
`A·exp(−t/T2*)·exp(j·2π·(f_larmor_sim − f_lo)·t + j·φ_pulse)` with A = 20 µV × LNA gain 1000 × mixer gain (≈ 0.9)
≈ 18 mV at the ADC, T2* = 0.4 s, white noise 3 mV rms, a 50 Hz hum line at 2 mV, `f_larmor_sim` = 89 400 Hz
(settable by `sim_larmor`). Averaging must visibly improve the SNR in the app.

## 4. Changes to existing blocks (drivers agent)
- `b5`: DIO1–8 through `expander.writePort(0, mask)`; `PIN_DIO[]` removed from `pins.h`. Fast outputs and TRIG
  unchanged. If the expander is absent, `dio` commands return `error:"expander not present"`.
- `b4`: relays through `expander.writeBit(1, n-1, on)`; new commands `hbridge {mode: off|fwd|rev|brake}` (HB_IN1/2
  = 0/0, 1/0, 0/1, 1/1) and `polarizer {on}` (FET_GATE); status adds `hbridge`, `polarizer`. Both refuse with
  `error:"nmr scan running"` while `nmr` is running (a global `nmr_busy()` in `blocks/nmr/NmrBlock.h` — the
  drivers agent adds a small header `blocks/Busy.h` with `extern volatile bool g_nmrBusy;` so it compiles before
  the nmr block exists).
- `b1`: real ADS8688 reads through `adc.readManual` under the SPI lock; `set_range` through `adc.setRange`.
- `b3`: DAC8563 writes take the SPI lock (existing TODOs stay as they are otherwise).
- `base`: `expander.begin()`, `clockgen.begin()`, `spibus::begin()` in `BaseBlock::begin()`; `info` adds
  `expander` and `clockgen` presence.

## 5. The app (`host/pwa/panels/nmr.js`) and the Python client (`host/instrument.py`)
- Tab **NMR**: settings form (f_tx, f_lo, sequence, t90, t_acq, n_avg, cyclops, polarize) → `config`; buttons
  Start / Abort / Pulse; a progress line (scan i / n, achieved rate, flags); two canvases: **FID** (|z| and I, Q
  vs time) and **Spectrum** (JS radix-2 FFT of the received record, Hann window, x-axis in Hz relative to the
  LO with a second label row in Larmor Hz = f_lo + f, a marker on the peak, SNR in the corner). Binary frames
  arrive on the same WebSocket; `app.js` already gives panels `api.on('status', …)`; add `api.on('binary', …)`
  dispatch by `kind` (kind 3 → the nmr panel) in `app.js` if it does not exist yet. Phone-first: everything
  stacks at 400 px; touch targets ≥ 44 px; the canvases redraw on resize.
- `instrument.py`: `nmr_config(**kw)`, `nmr_start()`, `nmr_wait(timeout_s)` (polls status), `nmr_record()`
  (returns rate, numpy complex array, n_avg) and `nmr_spectrum()` (numpy FFT, Hz relative to the LO); a
  `python instrument.py nmr --n-avg 8 --csv fid.csv` sub-command. ruff clean (E501 = 120 as configured in pyproject).

## 6. Build and verification
`pio run -d firmware -e esp32s3-sim` and `pio run -d firmware -e esp32s3` must both compile warning-free for the
new files. No hardware exists yet: the sim build is the test — flash it only when the user asks. Keep every
hardware access inside `#ifndef SIM`. No secrets, no hour/minute estimates, no "homework" in any comment.
