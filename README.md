# class-board-2026

The teaching instrument for **Basic Skills for Experimentalists** (TIGP, 2026): one ESP32-S3 board (the ESP32-S3 is the microcontroller we use — a small computer on a chip, with WiFi) with five student-designed blocks, a phone web app, and a Python client.

| Folder | What | Who edits it |
|---|---|---|
| `hardware/` | KiCad project and library (KiCad is the free program we draw the schematic and lay out the printed circuit board in; the library is the set of symbols and footprints for our parts) | students in their zone (the region of the board that is theirs), instructor merges (brings their changes into the main line) |
| `firmware/` | PlatformIO project (Arduino, ESP32-S3) — the firmware is the program that runs on the microcontroller; PlatformIO is the tool that builds it and writes it onto the board | students in `src/blocks/b<N>_*/` |
| `host/pwa/` | the phone app (plain HTML/JS, no build step) | students in `panels/b<N>.js` |
| `host/instrument.py` | Python command-line client (CLI) speaking the same protocol as the phone | instructor |

**Blocks:** `base` (dev board itself) · `b1_inputs` (ADS8688 8-ch ADC, analog-to-digital converter) · `b2_power` (rails) · `b3_outputs` (DAC8563 digital-to-analog converter + ±10 V) · `b4_switching` (4 relays, 2 optos) · `b5_dio_trig` (8 TTL out, 2 fast out, TRIG). Protocol: [firmware/PROTOCOL.md](firmware/PROTOCOL.md).

Until the class board arrives everything runs in **SIM mode** on a bare Jinhua ESP32-S3 N16R8 dev board (the development board: the microcontroller on a small board with a USB connector and pins): each block fakes its hardware, so the app, the chart and the alarms all work from Workshop 1.

**How this repository fits the course.** **Workshop 1: AI for experimentalists** is **Project 1** (a web app of your choice — a simulator or a game, built with the AI method) and **Project 2** (your own phone app that controls the ESP32 over WiFi). The firmware and app in this repository are **Step 1 of Project 2**: every student flashes them onto their own board first — a known working hardware baseline, which separates hardware problems from software problems — then builds their own app in its own repository, reading this code for the access point, the WebSocket and the LED. They stay the **fallback**: flash them again if your own build stalls and you have a working app on the phone today. They are also the **base for Project 3a** (**Workshop 2: Designing printed circuit boards** — the class board in KiCad, one block per student) and **Project 3b** (**Workshop 3: Firmware and basic mechanical design (PCB housing)**). The course ends with a project presentation and demonstration, 26–30 Oct.

## The student package (everything you need is in this repository — the project folder whose complete history git keeps, stored online on GitHub)

| What | Where |
|---|---|
| **Setup (before Workshop 1)** | [SETUP.md](SETUP.md) — paste the prompt from workbook ch. 0 into Claude Code and it installs the toolchain (the compiler and helper programs that turn source code into firmware) |
| **Workbook** — one chapter per workshop, each with a *between workshops* part ("Before the next workshop: complete the preparation, improve your apps, build and have fun."), the same text the tutor runs | [`workbook/`](workbook/README.md): [ch. 0](workbook/ch0-before-day-1.md) · [ch. 1](workbook/ch1-day-1-week-1.md) · [ch. 2](workbook/ch2-day-2-week-2.md) · [ch. 3](workbook/ch3-day-3-week-3.md) · [ch. 4](workbook/ch4-wrap-up-demo.md) · [A](workbook/chA-electronics-from-zero.md) · [B](workbook/chB-how-the-software-works.md) · [C cheat-sheets](workbook/chC-cheat-sheets.md) |
| **Your block page** (assigned at the start of Workshop 2) | [`workbook/blocks/`](workbook/blocks/): B1 · B2 · B3 · B4 · B5 |
| **The tutor** (self-updating: fetches the latest guide and workbook from GitHub at the start of every session) | `/tutor L1` (etc.) in Claude Code — [`.claude/skills/tutor/`](.claude/skills/tutor/SKILL.md), rules in [`tutor/COURSE-GUIDE.md`](tutor/COURSE-GUIDE.md) |
| **Slides** | Workshop 1 as a PDF on the course site: https://tigp-experimental-methods.github.io/slides/W1-AI-for-experimentalists.pdf (Workshop 2 and 3 slides follow the same way; see [`slides/README.md`](slides/README.md)) |
| **Firmware + app** (Step 1 of Project 2 — the hardware baseline — and its fallback; base for Project 3) | `firmware/`, `host/` — flash it (write it onto the board over USB) in 5 commands below |
| **The class project wall** — one card per project (picture, title, student, two sentences, buttons *Open the app · Project site · Video · Code*), refreshed every minute, on the projector in class; every student pushes their own entries (workbook ch. 1, *Put it on the class project wall*). Project 3 — your board section, its firmware and the housing — is **one** repository, one project website and one card | https://tigp-experimental-methods.github.io/showcase-2026/ — repository https://github.com/TIGP-Experimental-Methods/showcase-2026 (its README documents the entry format) |
| **KiCad library package** | [`hardware/lib/`](hardware/lib/README.md) — project-local, nothing to unzip |
| **Reference repositories for Project 1** | https://github.com/TIGP-Experimental-Methods/pendulum-example (cart-pole) · https://github.com/TIGP-Experimental-Methods/csv-scope-example (CSV → scope lab tool) — options, or a fork (your own copy of one of them on GitHub) if your session stalls |
| **Course site** | https://tigp-experimental-methods.github.io/ |

## Flash in 5 commands (VS Code + PlatformIO)

Prerequisites: VS Code with the *PlatformIO IDE* extension (installs its own Python and `pio`), git, the dev board on a USB-C **data** cable plugged into the port marked *USB* (native USB, not *UART*).

```sh
git clone https://github.com/TIGP-Experimental-Methods/class-board-2026.git
cd class-board-2026/firmware
pio run -e esp32s3-sim -t upload        # 1st time: downloads the toolchain
pio run -e esp32s3-sim -t uploadfs      # copies host/pwa/ to the board's LittleFS (its file store)
pio device monitor                      # watch it boot; note the AP name
```

(In VS Code: PlatformIO sidebar → `esp32s3-sim` → *Upload*, then *Upload Filesystem Image*, then *Monitor*.)
If the upload cannot find a port: hold **BOOT**, tap **RST**, release BOOT, retry. Windows needs no driver for native USB.
If the upload says *"No serial data received"* (a factory-fresh board, USB ID `303A:4001`): hold **BOOT**, tap **RST**, release BOOT — the board comes back as `303A:1001` on a **new COM port**; `pio device list` again and flash to that port. Once only; the port also disappears and reappears at every reset, which is normal. All flashing and serial symptoms, and the secrets rule, are on one page: [workbook ch. C, §C.2](workbook/chC-cheat-sheets.md#c2-platformio).

## Open the app on your phone

1. The board's RGB LED turns **blue** = it is an access point (its own WiFi network, which your phone joins). Serial monitor prints `AP "instrument-XXXX" password "instrument"`.
2. On the phone join WiFi `instrument-XXXX`, password `instrument`.
3. Open **http://192.168.4.1** in the browser (type the `http://`; stay connected when the phone warns about no internet, mobile data off on Android). Tap *Red* on the Base tab: the LED changes. The chart plots `base.counter`; pick another key from the dropdown.
4. *Add to Home screen* gives an app icon. (Full "install" prompts need HTTPS, which the board does not have; the shortcut is enough.)

To use the lab WiFi instead: copy `firmware/include/secrets.h.example` to `secrets.h`, fill in SSID/password — type the password into that file yourself, never into a Claude chat; the file is git-ignored (`git check-ignore -v firmware/include/secrets.h` prints a line) — and re-flash. The LED turns **green** and the board is at `http://instrument-XXXX.local` (mDNS: the board announces its own name on the local network, so no IP address is needed; `XXXX` is the same suffix as its access-point name, so several boards can share one network). If joining fails within 10 s it falls back to the AP.

## Python client

```sh
pip install -e host/            # or: uv pip install -e host/
instrument status
instrument send base led --args '{"r":0,"g":255,"b":0}'
instrument stream base.counter --seconds 5 --csv out.csv
instrument alarms list
```

It finds `instrument.local`, then `192.168.4.1`; `--host 10.0.0.42` overrides.

## Add a block (Workshop 3, exercise E11)

1. Copy `firmware/src/blocks/template/` → `firmware/src/blocks/b3_outputs/` (yours). Rename the class and `name()` → `"b3"`.
2. Write the **SIM branch first**: `status()` returns plausible fake values; `handle()` accepts your commands. Flash; your tab appears with a generic key/value view.
3. Copy `host/pwa/panels/template.js` → `panels/b3.js`, set `id: 'b3'`, replace the example control. Add it to `PANELS` in `app.js`. `pio run -t uploadfs`; reload the phone.
4. Register the block in `firmware/src/main.cpp` (one `registry.add(&b3)` line — the stub blocks are already registered, so for B1–B5 you only replace the stub).
5. Fill the `#ifndef SIM` branches with the real driver using the pin constants in `firmware/include/pins.h`.
6. Open a pull request (PR — a request to merge your changes into the shared project; someone reviews it first); CI (continuous integration — the automatic build GitHub runs on every pull request) builds both envs.

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
