# Chapter B — How the instrument's software works (self-study, optional)

Read before lecture 3; `/tutor B` answers questions on it. The authoritative message list is `firmware/PROTOCOL.md`.

## B.1 The shape
```
 phone (web app, served by the board)  ──┐
                                          ├── one WebSocket ──  firmware on the ESP32-S3  ──  blocks  ──  hardware
 PC (instrument.py, Python)           ──┘
```
Everything a human or a script does is a **JSON command** (JSON: a plain-text format for structured data, e.g. `{"cmd":"led","r":255}`) to a **block**; everything the board tells you is a **status** broadcast, an **alarm** event, or a **binary sample frame**.

## B.2 The microcontroller and the firmware loop
The ESP32-S3 (our microcontroller — a small computer on a chip, with WiFi) runs the firmware (the program on the microcontroller) as Arduino code: `setup()` once, then `loop()` forever, thousands of times a second. Our `loop()` does four things in order: service WiFi and the web server, hand queued messages to the right block's `handle()`, call every block's `loop()`, and every 50 ms collect every block's `status()` into one broadcast. Because everything runs from `loop()`, no block needs threads or locks — and none may call `delay()`, which would freeze all of them.

## B.3 WiFi: access point or station
With no `secrets.h` the board is its own network `instrument-XXXX` at `192.168.4.1` (LED blue). With credentials it joins the lab WiFi (LED green) and is found as `instrument-XXXX.local` (XXXX = the four hex digits in the access-point name) via mDNS. If joining fails within 10 s it falls back to the access point. The web app is served from the board's flash (LittleFS, the small file store on the board), so it works with no internet.

## B.4 The WebSocket and the three message kinds
One WebSocket (a live two-way connection between the phone page and the board) at `ws://<board>/ws`. **Request → reply:** `{"id":1,"block":"b4","cmd":"relay","args":{"n":1,"on":true}}` → `{"id":1,"ok":true,"result":{"n":1,"on":true}}`; the `id` lets the client match them. **Broadcasts:** `hello` on connect (which blocks exist), `status` at 20 Hz (every block's numbers), `alarm` when a rule fires. **Binary frames** (PROTOCOL §6): `stream` chunks for the rolling scope, one `capture` frame for a triggered burst; a 28-byte header then `int16` samples.

## B.5 The PWA (the phone app)
Plain HTML/CSS/JS in `host/pwa/` (a PWA, progressive web app, is a web page — here served by the board — that behaves like an app), no framework, no build step, no CDN (the board is offline). `app.js` owns the socket, the tabs, the chart and the alarm toasts; each block has one **panel module** `panels/b<N>.js` exporting `{id, title, render(el, api), onStatus(st)}`. `api.send(block, cmd, args)` returns a promise with the result; `api.toast(msg)`; `api.addAlarm(rule)`. *Add to Home screen* makes it an icon; the service worker caches the shell.

## B.6 JSON
Text that both JavaScript and C++ (ArduinoJson) read the same way: objects `{}` with `"key": value`, arrays `[]`, numbers, strings, `true/false`. Our rule: commands and status keys are `snake_case`; numeric top-level status keys are what the chart can plot and alarms can test; nested objects are display-only.

## B.7 The Python client
`host/instrument.py` (the Python client: a program on your PC that talks to the board with the same messages as the phone; typer + websockets): `instrument status`, `instrument send b3 sine --args '{"ch":1,"freq":1000,"amp":5}'`, `instrument stream b1.ai1 --seconds 5 --csv out.csv`, `instrument alarms add …`, and (new) `instrument scope` / `instrument capture` into CSV or NumPy. Anything the phone can do, a script can do — sweeps, logging, plots with matplotlib.

## B.8 Blocks and the registry
A block is one C++ class implementing `Block` (five methods). `main.cpp` registers each one; the `hello` message lists them; the app makes a tab per block, with a generic key/value view until a panel module exists. Students edit only their block folder and their panel file.

## B.9 SIM mode
`pio run -e esp32s3-sim` (the build command of PlatformIO, the tool that builds and flashes the firmware) compiles with `-DSIM=1`: every block's `#ifdef SIM` branch fakes its hardware with plausible, moving values. That is why the whole app, chart and alarm engine work on a bare dev board on day 1 and why you can write your driver in week 3 while the board is at the factory. The real branch is `#ifndef SIM` and stays `TODO` until measured.

## B.10 The alarm engine
Rules are data, not code: `{block, key, op, threshold, action}`. Twenty times a second the engine tests every rule against the same status the app sees, fires once on the rising edge, runs the action (`notify` → toast on every phone; `relay:<n>:on|off` → block B4) and broadcasts an `alarm` message. Rules persist in `/alarms.json` on the board. Every block owner adds one rule — the demo's "alarm → relay → notification" step.

## B.11 OTA and the flash layout
The firmware is flashed (written onto the board) over USB once; afterwards it can update itself over WiFi (OTA, over-the-air; ArduinoOTA). The flash holds the program, a second slot for OTA, and the LittleFS partition with the web app (`pio run -t uploadfs`). Two uploads, two things: **code** (`upload`) and **web app** (`uploadfs`).

## B.12 Where the E2 app fits
Your day-1 `press` command and `presses` number were a block command and a status key on `base`. Your week-3 driver is the same idea with your block's hardware behind it, plus SIM values and one alarm rule. Nothing new in shape — that is the point.
