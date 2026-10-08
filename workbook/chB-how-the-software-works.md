# Chapter B — How the instrument's software works (self-study, optional)

Read before Workshop 3; `/tutor B` answers questions on it. The authoritative message list is `firmware/PROTOCOL.md`.

## B.1 The shape
```
 phone (web app, served by the board)  ──┐
                                          ├── one WebSocket ──  firmware on the ESP32-S3  ──  blocks  ──  hardware
 PC (instrument.py, Python)           ──┘
```
Everything a human or a script does is a **JSON command** (JSON: a plain-text format for structured data, e.g. `{"cmd":"led","r":255}`) to a **block**; everything the board tells you is a **status** broadcast, an **alarm** event, or a **binary sample frame**.

## B.2 The microcontroller and the firmware loop
The ESP32-S3 (our microcontroller — a small computer on a chip, with WiFi) runs the firmware (the program on the microcontroller) as Arduino code: `setup()` once, then `loop()` forever, thousands of times a second. Our `loop()` does four things in order: call every block's `loop()`, let the over-the-air updater check for new firmware (OTA, B.11), hand the queued messages to the right block's `handle()`, and every 50 ms collect every block's `status()` into one broadcast. WiFi and the web server run on their own task (a second program the chip runs alongside `loop()`); all it does with a message is put it in the queue. Because all block code runs from `loop()`, no block needs threads or locks — and none may call `delay()`, which would freeze all of them. The NMR console (B.8) is the one exception: its pulse timing runs on a task of its own.

## B.3 WiFi: access point or station
With no `secrets.h` the board is its own network `instrument-XXXX` at `192.168.4.1` (LED blue). With credentials it joins the lab WiFi (LED green) and is found as `instrument-XXXX.local` (XXXX = the four hex digits in the access-point name) via mDNS. If joining fails within 10 s it falls back to the access point. The web app is served from the board's flash (LittleFS, the small file store on the board), so it works with no internet.

## B.4 The WebSocket and the three message kinds
One WebSocket (a live two-way connection between the phone page and the board) at `ws://<board>/ws`. **Request → reply:** `{"id":1,"block":"b4","cmd":"module","args":{"n":1,"on":true}}` → `{"id":1,"ok":true,"result":{"n":1,"on":true}}`; the `id` lets the client match them. **Broadcasts:** `hello` on connect (which blocks exist), `status` at 20 Hz (every block's numbers), `alarm` when a rule fires. **Binary frames** (PROTOCOL §6): a 28-byte header, then the samples. Today there is one kind, the NMR record (kind 3): after every scan the board sends the averaged complex record to every client. The rolling-stream and triggered-capture frames of PROTOCOL §6, and a Scope tab to show them, are specified but not built yet.

## B.5 The PWA (the phone app)
Plain HTML/CSS/JS in `host/pwa/` (a PWA, progressive web app, is a web page — here served by the board — that behaves like an app), no framework, no build step, no CDN (the board is offline). `app.js` owns the socket, the tabs, the chart and the alarm toasts; each block has one **panel module** `panels/<id>.js` exporting `{id, title, render(el, api), onStatus(st)}`. `api.send(block, cmd, args)` returns a promise with the result; `api.toast(msg)`; `api.addAlarm(rule)`. *Add to Home screen* makes it an icon; the service worker caches the shell.

## B.6 JSON
Text that both JavaScript and C++ (ArduinoJson) read the same way: objects `{}` with `"key": value`, arrays `[]`, numbers, strings, `true/false`. Our rule: commands and status keys are `snake_case`; numeric top-level status keys are what the chart can plot and alarms can test; nested objects are display-only.

## B.7 The Python client
`host/instrument.py` (the Python client: a program on your PC that talks to the board with the same messages as the phone; typer + websockets): `instrument status`, `instrument send b3 sine --args '{"ch":1,"freq":1,"amp":5}'`, `instrument stream b1.ai1 --seconds 5 --csv out.csv` (one status value at 20 Hz), `instrument alarms add …` / `list` / `remove` / `clear`, and `instrument nmr --n-avg 8 --csv fid.csv`. Without `--host` it talks to `192.168.4.1`; on the lab network add `--host instrument-XXXX.local`. There is no `scope` or `capture` command yet (B.4). Anything the phone can do, a script can do — sweeps, logging, plots with matplotlib.

## B.8 Blocks and the registry
A driver is one C++ class implementing `Block` (five methods — the firmware calls each driver a *block*). `main.cpp` registers each one; the `hello` message lists them; the app makes a tab per block, with a generic key/value view until a panel module exists. Students edit only the driver folders and panel files of their own section.

**One of the blocks is the NMR console.** Besides the drivers for the three sections the firmware carries an **`nmr`** block, and the app an **NMR** tab: it runs the experiment end to end — the pulse, the free induction decay that comes back, the spectrum. It is shared, like the base block: it is nobody's section exercise, but it uses all three of them.

## B.9 SIM mode
`pio run -e esp32s3-sim` (the build command of PlatformIO, the tool that builds and flashes the firmware) compiles with `-DSIM=1`: every block's `#ifdef SIM` branch fakes its hardware with plausible, moving values. That is why the whole app, chart and alarm engine work on a bare dev board in Workshop 1 and why you can write your driver between Workshop 3 and the presentation, while the board is at the factory. The real branch is `#ifndef SIM` and stays `TODO` until measured.

## B.10 The alarm engine
Rules are data, not code: `{block, key, op, threshold, action}`. Twenty times a second the engine tests every rule against the same status the app sees — numbers, and true/false keys as 1/0, so `b4.polarizer eq 1` works — fires once on the rising edge, runs the action (`module:<n>:on|off` switches a module output on Section C's front panel; `notify` does nothing more) and broadcasts an `alarm` message to every connected client, which the app shows as a toast on every phone. Rules persist in `/alarms.json` on the board. Every section adds one rule — the demonstration's "alarm → module output → notification" step.

## B.11 OTA and the flash layout
The firmware is flashed (written onto the board) over USB once; afterwards it can update itself over WiFi (OTA, over-the-air; ArduinoOTA). The flash holds the program, a second slot for OTA, and the LittleFS partition with the web app (`pio run -t uploadfs`). Two uploads, two things: **code** (`upload`) and **web app** (`uploadfs`).

## B.12 Where your Project 2 app fits
In Project 2 your phone sent a command to the ESP32 (set the LED's colour) and read a value back (a temperature, a counter, an ADC reading). In this firmware those are a block command and a status key on `base` — `handle()` acts on the command, `status()` fills the numbers the phone sees. A driver in Workshop 3 (E11) is the same idea with the class board's hardware behind it, plus SIM values and one alarm rule. Nothing new in shape — that is the point.
