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
`b5`: dio, dio1…dio8, trig_dir, trig, fast1_hz, fast2_hz · `template`: value, setpoint · `alarms`: rules, active
