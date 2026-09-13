# Message protocol (JSON over WebSocket)

One WebSocket at `ws://<board>/ws` (`instrument.local` or `192.168.4.1`). All messages are UTF-8 JSON text frames. Three message kinds flow over it.

## 1. Request → reply (client to board)

```json
{"id": 1, "block": "base", "cmd": "led", "args": {"r": 255, "g": 0, "b": 0}}
```

| Field | Meaning |
|---|---|
| `id` | any number/string; echoed in the reply so the client can match them |
| `block` | block name: `base`, `b1`…`b5`, `template`, `alarms` |
| `cmd` | command name, block-specific (see §4) |
| `args` | object, may be omitted |

Reply, always exactly one per request:

```json
{"id": 1, "ok": true,  "result": {"r": 255, "g": 0, "b": 0}}
{"id": 1, "ok": false, "error": "unknown cmd"}
```

Requests are handled in the firmware's `loop()`, in order, one at a time.

## 2. Broadcasts (board to every client)

**`hello`** — sent once when a client connects; lists the registered blocks so the app can build its tabs.

```json
{"type": "hello", "fw": "0.1.0", "sim": true, "blocks": ["base", "b1", "b2", "b3", "b4", "b5", "template", "alarms"]}
```

**`status`** — every 50 ms (20 Hz). `t` is the board's `millis()`.

```json
{"type": "status", "t": 123456,
 "blocks": {"base": {"counter": 1234, "temp_c": 41.2, "uptime_s": 123, "rssi": 0, "heap_free": 250000,
                     "clients": 1, "led": {"r": 0, "g": 0, "b": 40, "brightness": 40}},
            "b1": {"ai1": 3.91, "ai2": -1.2, "...": 0, "range": 0},
            "b4": {"relay1": false, "opto1": 17, "...": 0}}}
```

Numeric top-level keys inside a block (`base.counter`, `b1.ai1`, …) are what the live chart can plot and what alarm rules can test. Nested objects (`base.led`) are for display only.

**`alarm`** — when a rule fires (rising edge).

```json
{"type": "alarm", "t": 123456, "rule": 2, "block": "b1", "key": "ai1", "value": 9.4, "action": "relay:1:off"}
```

## 3. HTTP

`GET /api/info` → `{"fw","sim","mac","blocks":[...]}` (same as `hello`, for scripts without WebSocket). Everything else under `/` is the web app served from LittleFS.

## 4. Commands per block

| Block | `cmd` | `args` | `result` |
|---|---|---|---|
| `base` | `led` | `{r,g,b}` 0–255 | `{r,g,b}` |
| | `brightness` | `{value}` 0–255 | `{brightness}` |
| | `counter_reset` | — | `{counter:0}` |
| | `info` | — | `{fw, chip, mac, ip, sim}` |
| `b1` | `read_all` | — | `{ai:[8 volts]}` |
| | `set_range` | `{ch:1..8, range:0..6}` | `{ch, range}` |
| `b2` | `rails` | — | `{v5_raw, v3v3, v12p, v12n, v5a, measured}` |
| `b3` | `set_dc` | `{ch:1..2, volts}` | `{ch, mode}` |
| | `sine` | `{ch, freq, amp, offset}` | `{ch, mode}` |
| | `off` | `{ch}` | `{ch, mode}` |
| `b4` | `relay` | `{n:1..4, on}` | `{n, on}` |
| | `relay_all` | `{on}` | `{on}` |
| | `opto_reset` | — | `{}` |
| `b5` | `dio` | `{n:1..8, level}` | `{mask}` |
| | `dio_mask` | `{mask:0..255}` | `{mask}` |
| | `trig_dir` | `{out}` | `{out}` |
| | `trig` | `{level}` (only when `out`) | `{level}` |
| | `fast_out` | `{n:1..2, freq_hz}` (0 = off) | `{n, freq_hz}` |
| `nmr` | `config` `start` `abort` `pulse` `clock` `dds` `blank` `get_record` | see §7 | see §7 |
| `template` | `set_value` | `{value}` | `{setpoint}` |
| `alarms` | `list` | — | `{rules:[...]}` |
| | `add` | `{block, key, op, threshold, action}` | the new rule incl. `id` |
| | `remove` | `{id}` | `{removed}` |
| | `clear` | — | `{}` |

Alarm rule fields: `op` ∈ `gt lt ge le eq ne`; `action` = `notify` or `relay:<n>:on` / `relay:<n>:off`. Rules fire once per rising edge and are saved to `/alarms.json` on the board.

## 5. Status keys per block

`base`: counter, temp_c, uptime_s, rssi, heap_free, clients, led{r,g,b,brightness} ·
`b1`: ai1…ai8, range · `b2`: v5_raw, v3v3, v12p, v12n, v5a, measured ·
`b3`: ao1, ao2, mode1, mode2 · `b4`: relay1…relay4, opto1, opto2, opto1_level, opto2_level ·
`b5`: dio, dio1…dio8, trig_dir, trig, fast1_hz, fast2_hz · `template`: value, setpoint · `alarms`: rules, active ·
`nmr`: see §7

## 6. Streaming and capture (Decision #26, 2026-09-06 — specified, not yet implemented)

The 20 Hz `status` broadcast is the slow channel. Fast data uses **binary WebSocket frames** on the same socket, in two modes that every real oscilloscope has:

**Rolling (continuous stream).** `{"id":7,"block":"b1","cmd":"stream","args":{"ch":1,"rate_hz":10000,"chunk":500}}` starts a stream; the board then sends one binary frame per `chunk` samples (here every 50 ms) until `{"cmd":"stream","args":{"ch":1,"rate_hz":0}}`. The app appends frames to a rolling buffer and draws the last N ms — a chart recorder / scope in roll mode.

**Triggered (burst capture).** `{"id":8,"block":"b1","cmd":"capture","args":{"ch":1,"rate_hz":100000,"n":4000,"trig":{"level":1.0,"edge":"rising","pre":1000}}}` arms a capture: the board samples into RAM (DMA), waits for the trigger crossing, keeps `pre` samples before it, and sends **one** binary frame with all `n` samples. `trig` omitted = capture immediately.

**Binary frame layout** (little-endian): `uint8 kind` (1 = stream chunk, 2 = capture, 3 = NMR record — §7) · `uint8 block_id` · `uint8 ch` · `uint8 bits` (12 or 16) · `uint32 t_ms` of the first sample · `uint32 rate_hz` · `uint32 n` · `int32 trig_index` (−1 if none) · `float32 volts_per_lsb` · `float32 offset_v` · then `n × int16` raw samples. Total 28-byte header + 2 n bytes; 4000 samples = 8 kB, which WiFi moves many times per second.

**Sources and realistic limits:** the dev board's internal ADC (`base`, 12-bit, noisy, GPIO 1–10) sustains a few kS/s rolling and ~80 kS/s burst via ADC continuous/DMA; the class board's ADS8688 (`b1`, 16-bit, ±10 V) gives tens of kS/s per channel rolling and up to 500 kS/s aggregate in burst. Rolling streams are capped by the WiFi link (budget ≈ 200 kB/s → ≈ 100 kS/s of int16 total across all clients); the board refuses `rate_hz` above the cap with `ok:false`.

**Where it lives:** the sampler + frame encoder are instructor-owned in `base` (dev-board ADC, so it works from Workshop 1 in sim and on the bare board); `b1` reuses the encoder with the ADS8688 (block owner extends it in E11). The PWA gets a **Scope** tab: roll / single / auto-trigger, timebase, cursor, "download CSV" of the visible buffer (Web Share on phones). `instrument.py` gets `scope` (stream to CSV/NumPy) and `capture`.

**Same socket, no extra ports:** text frames stay JSON as above; the app tells them apart by frame type (`typeof data === "string"`).

## 7. NMR console (block `nmr`)

The `nmr` block runs a pulsed nuclear-magnetic-resonance experiment on the class board: it transmits a
burst at `f_tx`, blanks the receiver while the coil rings down, then samples the heterodyne receiver's
I and Q outputs (ADS8688 channels 7 and 8) and averages over scans. The receiver mixes the signal down
against a local oscillator at `f_lo`, so what the app and the Python client see is a complex record at
the intermediate frequency **IF = f_tx − f_lo** (positive = the line is above the local oscillator).
Demo regime: protons in water at about 2.1 mT, Larmor ≈ 89.4 kHz, IF ≈ 5.4 kHz.

### 7.1 Commands

| `cmd` | `args` | `result` |
|---|---|---|
| `config` | any subset of the settings in §7.2 | the full effective settings, plus `f_tx_actual_hz`, `f_lo_actual_hz` |
| `start` | — | `{state:"running", n_avg}` — the scan set runs in the background |
| `abort` | — | `{state:"idle"}` |
| `pulse` | `{t_us}` 1–5000 | `{t_us}` — one transmit gate without acquisition, for a scope check |
| `clock` | `{clk:0..1, hz}` | `{clk, hz_actual}` — low-level Si5351 test |
| `dds` | `{hz, phase0_deg, phase1_deg, psel}` | the values programmed |
| `blank` | `{receive:bool}` | `{receive}` — manual receiver blanking for bench tests |
| `get_record` | — | `{n, rate_hz}`, and the last averaged record is resent as a binary frame (§7.4) |
| `sim_larmor` | `{hz}` (simulation build only) | `{hz}` — the simulated Larmor frequency |

### 7.2 Settings (`config`), with their defaults

`f_tx_hz` 89400 · `f_lo_hz` 84000 · `sequence` `"fid"` or `"echo"` · `t90_us` 417 · `t180_us` 834 ·
`tau_us` 20000 (echo only) · `t_blank_pre_us` 20 · `t_dead_us` 1000 · `t_acq_start_us` 1200 ·
`t_acq_ms` 2000 (max 4000) · `rate_hz` 100000 per channel · `decim` 16 · `n_avg` 1 (1–256) ·
`cyclops` true (the pulse phase steps 0/90/180/270 across scans and the record is rotated back before
averaging) · `t_repeat_ms` 3000 · `polarize_ms` 0 · `hb_mode` `"off"` / `"fwd"` / `"rev"`.

The record the clients receive is decimated: its sample rate is `rate_hz / decim`. Complex sampling
covers −rate/2 to +rate/2, so the decimated rate must be more than twice the IF or the line folds over.

### 7.3 Status keys

`state` (`idle` / `running` / `done` / `error`) · `scan` (scans done in this set) · `n_avg` · `f_tx_hz` ·
`f_lo_hz` · `if_hz` · `rate_hz` (the rate the ADC really achieved) · `peak_hz` (signed, relative to the
local oscillator) · `larmor_hz` (= `f_lo_hz` + `peak_hz`) · `peak_amp` (V) · `snr_db` · `i_flag` (the
transmit amplifier hit its current limit) · `t_flag` (thermal) · `error` (string, when `state` is
`error`) · `sim`.

A current-limit or thermal flag stops the scan set: the board never keeps pulsing on a flag.

### 7.4 Binary frame, kind 3 — the averaged record

Same 28-byte header as §6, so one parser handles both:

`uint8 kind = 3` · `uint8 block_id = 9` · `uint8 ch = 0` · `uint8 bits = 32` (float32 pairs) ·
`uint32 t_ms` · `uint32 rate_hz` (the **decimated** rate) · `uint32 n` (complex samples) ·
`int32 trig_index` = **scans averaged so far** · `float32 volts_per_lsb = 1.0` (the payload is already
in volts) · `float32 offset_v` = **the IF in Hz** (`f_tx − f_lo`, so a client can label its frequency
axis in Larmor Hz) · then `n × (float32 I, float32 Q)` in volts at the ADC input.

The board sends one frame to every client after every scan, and `get_record` resends the last one.
The app (`host/pwa/panels/nmr.js`) draws the free induction decay from this record and computes the
spectrum itself; `host/instrument.py` turns it into a numpy complex array.

