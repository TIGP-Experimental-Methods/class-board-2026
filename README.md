# class-board-2026

The teaching instrument for **Basic Skills for Experimentalists** (TIGP, 2026): one ESP32-S3 board with five student-designed blocks, a phone web app, and a Python client.

| Folder | What | Who edits it |
|---|---|---|
| `hardware/` | KiCad project and library | students in their zone, instructor merges |
| `firmware/` | PlatformIO project (Arduino, ESP32-S3) | students in `src/blocks/b<N>_*/` |
| `host/pwa/` | the phone app (plain HTML/JS, no build step) | students in `panels/b<N>.js` |
| `host/instrument.py` | Python CLI mirroring the same protocol | instructor |

**Blocks:** `base` (dev board itself) · `b1_inputs` (ADS8688 8-ch ADC) · `b2_power` (rails) · `b3_outputs` (DAC8563 + ±10 V) · `b4_switching` (4 relays, 2 optos) · `b5_dio_trig` (8 TTL out, 2 fast out, TRIG). Protocol: [firmware/PROTOCOL.md](firmware/PROTOCOL.md).

Until the class board arrives everything runs in **SIM mode** on a bare Jinhua ESP32-S3 N16R8 dev board: each block fakes its hardware, so the app, the chart and the alarms all work on day 1.

## Flash in 5 commands (VS Code + PlatformIO)

Prerequisites: VS Code with the *PlatformIO IDE* extension (installs its own Python and `pio`), git, the dev board on a USB-C **data** cable plugged into the port marked *USB* (native USB, not *UART*).

```sh
git clone https://github.com/TIGP-Experimental-Methods/class-board-2026.git
cd class-board-2026/firmware
pio run -e esp32s3-sim -t upload        # 1st time: downloads the toolchain (~10 min)
pio run -e esp32s3-sim -t uploadfs      # ships host/pwa/ to the board's LittleFS
pio device monitor                      # watch it boot; note the AP name
```

(In VS Code: PlatformIO sidebar → `esp32s3-sim` → *Upload*, then *Upload Filesystem Image*, then *Monitor*.)
If the upload cannot find a port: hold **BOOT**, tap **RST**, release BOOT, retry. Windows needs no driver for native USB.

## Open the app on your phone

1. The board's RGB LED turns **blue** = it is an access point. Serial monitor prints `AP "instrument-XXXX" password "instrument"`.
2. On the phone join WiFi `instrument-XXXX`, password `instrument`.
3. Open **http://192.168.4.1** in the browser. Tap *Red* on the Base tab: the LED changes. The chart plots `base.counter`; pick another key from the dropdown.
4. *Add to Home screen* gives an app icon. (Full "install" prompts need HTTPS, which the board does not have; the shortcut is enough.)

To use the lab WiFi instead: copy `firmware/include/secrets.h.example` to `secrets.h`, fill in SSID/password, re-flash. The LED turns **green** and the board is at `http://instrument.local` (mDNS). If joining fails within 10 s it falls back to the AP.

## Python client

```sh
pip install -e host/            # or: uv pip install -e host/
instrument status
instrument send base led --args '{"r":0,"g":255,"b":0}'
instrument stream base.counter --seconds 5 --csv out.csv
instrument alarms list
```

It finds `instrument.local`, then `192.168.4.1`; `--host 10.0.0.42` overrides.

## Add a block (Session 3, exercise E11)

1. Copy `firmware/src/blocks/template/` → `firmware/src/blocks/b3_outputs/` (yours). Rename the class and `name()` → `"b3"`.
2. Write the **SIM branch first**: `status()` returns plausible fake values; `handle()` accepts your commands. Flash; your tab appears with a generic key/value view.
3. Copy `host/pwa/panels/template.js` → `panels/b3.js`, set `id: 'b3'`, replace the example control. Add it to `PANELS` in `app.js`. `pio run -t uploadfs`; reload the phone.
4. Register the block in `firmware/src/main.cpp` (one `registry.add(&b3)` line — the stub blocks are already registered, so for B1–B5 you only replace the stub).
5. Fill the `#ifndef SIM` branches with the real driver using the pin constants in `firmware/include/pins.h`.
6. Open a PR; CI builds both envs.

The rules: a block talks only to its own hardware; all block code runs from `loop()` (no tasks, no locks); every status key you show in the panel is one your `status()` emits.

## Add an alarm rule

Rules are data: `{block, key, op, threshold, action}`, evaluated 20× per second on the same status the app sees; they fire once when the condition becomes true.

- On the phone: **Alarms** tab → pick `b1.ai1`, `gt`, `9`, action `relay 1 off` → *Add rule*.
- From a panel: `api.addAlarm({ block: 'b2', key: 'v5_raw', op: 'lt', threshold: 4.9, action: 'notify' })` (see `panels/template.js`).
- From Python: `instrument alarms add --block b1 --key ai1 --op gt --threshold 9 --action relay:1:off`.

`action` is `notify` (toast on every phone, browser notification if allowed) or `relay:<n>:on|off` (block b4). Rules persist on the board in `/alarms.json`.

## Layout

```
firmware/
  platformio.ini            envs esp32s3 (real) and esp32s3-sim (-DSIM=1)
  include/pins.h            GPIO map v0.6 (design brief §4.2)
  include/secrets.h.example WiFi credentials template
  scripts/copy_pwa.py       pre-build: host/pwa -> firmware/data
  src/main.cpp              WiFi, mDNS, OTA, HTTP + WebSocket, 20 Hz broadcast
  src/blocks/Block.h        the 5-method interface
  src/blocks/Registry.*     list of blocks
  src/blocks/base/          LED, counter, temperature
  src/blocks/template/      copy-me block
  src/blocks/b1_inputs/ … b5_dio_trig/
  src/alarm/AlarmEngine.*   rules, block "alarms"
  PROTOCOL.md
host/
  pwa/                      index.html app.js style.css sw.js manifest, panels/*.js
  instrument.py, pyproject.toml
.github/workflows/build.yml  both envs + ruff on every push/PR
```
