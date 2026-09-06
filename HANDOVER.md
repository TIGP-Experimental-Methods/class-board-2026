> **2026-09-07 (course session, lecture-1 review):** **E2 redefined** — `adc_sd` is now the noise of one N-sample average (sd of the N-sample block means across a 4096-sample ring; `set_avg` 1..1024; statistics in `status()`, sampling only in `loop()`); workbook A.4, COURSE-GUIDE, SKILL, BaseBlock/base.js comments and slides L1 agree. Slides L1 = 23 slides (Tutor-on slide, E1a and E2 split, all fit; render with `marp --no-stdin`). Workbook/SETUP: one command per line (no `&&` on Windows), `/tutor CH0` from the `class-board-2026` folder, repo is public so membership is only for push/PR, `pio run -d firmware …`, branch `e2-<name>` created at A.0, KiCad check via Help → About, E1a in a second VS Code window. **Admin still to do by the instructor:** give `students-2026` push on this repo, protect `main`, invite students. Both envs compile.

> **2026-09-07 (course session, videos):** the videos V0–V7 are **not recorded yet**; workbook ch. 0 §0.8 and `SETUP.md` step 10 now say "not yet online" (the agent records *not yet online* and moves on). When V1/V2 are uploaded, replace those notes with links (and the same on the course site: preparation step 8, index row 0, lecture 1–3 materials). Six Jinhua #40729 dev boards were bought 2026-09-07; nothing has run on hardware yet.

> **2026-09-06 (course session 81f223c7):** `PROTOCOL.md` §6 adds **streaming + triggered capture as binary frames** (Decision #26 in the course repo) — specified, not implemented. Implement in `blocks/base/` first (internal ADC via `analogContinuous*` / ADC DMA, frame encoder), then the PWA **Scope** tab (roll / single / auto, timebase, cursor, CSV download) and `instrument.py scope|capture`. For day 1 (Decisions #25/#27): `blocks/base/` carries the **E2 markers with the measurement recipe in comments** (`set_avg {n}` → `adc_v`/`adc_sd`/`avg_n` from a 1 kHz ring buffer on GPIO 4; the LED `press` button is the fallback) — the student writes it; nothing functional to add there.

> **2026-09-07 (course session, plain language):** every tooling term is explained on first use per chapter/deck, "repo" → "repository", "PR" → "pull request (PR)"; glossary = `workbook/chC-cheat-sheets.md` §C.0; L1 has a "Words you will hear today" slide; **tutor rule 14** = explain every term the first time, no jargon. Keep this standard in every new student-facing file.

> **2026-09-07 (course session):** new **`SETUP.md`** at the repo root — the agent-readable pre-class setup students point Claude Code at (raw URL in workbook ch. 0 and on the course site's preparation page); ch. 0 rewritten to the Claude-driven flow; **the dev board is USB-C** (USB-C data cable); "a number predicted on paper" reworded to "one result you can work out by hand before the code exists" in ch. 1 / COURSE-GUIDE / L1 slides. Untested on a clean machine — dry-run SETUP.md before 09-11.

> **2026-09-06 (course session, latest):** Decision #30 (course repo): no pre-class check-in, no tutor checkpoints, no fixed review step, **no student deadline dates in this repo** (agreed in class; the class order Mon 09-28 may be stated), public/private repo = student's choice, no SAIL Club, demo format **and length** agreed in class (no "5-minute"), LINE/Telegram interaction with the instrument = the most-encouraged extension.

> **2026-09-06 (course session, later):** **no LINE group** (never agreed) — help and the pre-class check-in go by **email to the instructor**; the LINE/Telegram alert feature is unaffected. **No office hour** (never agreed — removed everywhere); tutor rule 8 = the fix on request only, after 15 minutes stuck (never volunteered), then the LINE group; rule 3 = homework must stay short; setup advice = "stuck on any setup problem → ask for help in the LINE group" (no "come early").

> **2026-09-06 (course session, Decision #29):** **no time or effort estimates anywhere students can read** — workbook, tutor guide/skill, slides, README carry no hour/minute budgets, no "10-hour promise", no video lengths, no 150 % rule; the tutor never says how long a step should take. The budgets live only in the course repo's planning docs. Timetable facts (14:20–16:20, dates, deadlines, 5-minute demo, 60-second video) stay.

> **2026-09-06 (course session, Decisions #27 + #28 applied):** workbook ch. 1 E1a = **the student as author** — pick a topic you know (EM / electronics / mechanics / PID) and build the page / simulation / game that teaches it to a high-school student, from a five-line `SPEC.md` with a learner outcome and a number predicted on paper; options with reference repos: `csv-scope-example` (lab tool), `pendulum-example` (cart-pole). E2 = the averaged-ADC measurement (sd vs N). E3 = two questions + a **design number** per block page. Tutor: 13 rules (12 never patronise, 13 push beyond the baseline / never talk about marks), expert mode. **Grading is not a topic of the materials** (no score sheet, no outcome statements — students are graded by the instructor; the tutor refers questions about marks to the instructor); demo item 5 (beyond the baseline) optional. Slides L1/L3 re-rendered. Firmware compiles (`esp32s3-sim`).

# HANDOVER — class-board-2026

Latest entry first. Every session appends one entry: done / verified / next / gotchas. Decisions the instructor has confirmed go under "Decision record" and are not re-litigated.

## Decision record
- **2026-09-06 (course Decisions #27/#28):** E1a default = teach one idea (student's choice) with a predicted check; csv-scope and cart-pole remain options with reference repos; E2 = measurement with its noise; E3 gains a design number per block; tutor never patronises, pushes beyond the baseline, does not discuss grades; grading is not a topic of the materials (no score sheet, no outcome statements — the instructor grades); demo item 5 optional. No YouTube channel in the pre-class list (the explainer video is an optional stretch). **Decision #29:** time/effort estimates are internal to the course repo; none in student-facing files.
_(the items under "Decisions to confirm" below become entries here once the instructor answers)_

---

## 2026-09-06 — Software skeleton created (firmware + PWA + Python CLI + CI)

**Done (by Claude, from course docs 08 §4, 09, 10 §4.2/§7 in the `20260910-TIGP` repo):**
- `firmware/` PlatformIO project: envs `esp32s3` (real) and `esp32s3-sim` (`-DSIM=1`), board `esp32-s3-devkitc-1`, `qio_opi` memory, `default_16MB.csv`, LittleFS, USB-CDC console. Libraries: `esp32async/ESPAsyncWebServer` 3.12.0 + `esp32async/AsyncTCP` 3.5.0 (the current maintained forks on the registry; `mathieucarbou/*` are frozen at 3.6.0/3.3.2), `ArduinoJson` 7.4.3, `Adafruit NeoPixel` 1.15.5. Platform `espressif32 @ ^7.1.1` → Arduino core 2.0.17.
- `src/main.cpp`: STA from `include/secrets.h` (via `__has_include`; 10 s timeout) → fallback soft-AP `instrument-XXXX` / `instrument` at 192.168.4.1; mDNS `instrument.local`; ArduinoOTA; HTTP static from LittleFS + `/api/info`; WebSocket `/ws` with `hello` on connect, 20 Hz `status` broadcast; incoming messages queued and handled in `loop()` so blocks are single-threaded.
- `src/blocks/Block.h` (name/begin/loop/handle/status), `Registry`, `base` (LED, counter, temp, uptime, RSSI, heap), `template` (copy-me with TODOs, SIM branch, `set_value`, alarm-hook comment), stubs `b1_inputs` `b2_power` `b3_outputs` `b4_switching` `b5_dio_trig` — all compile in both envs and return plausible SIM values; `include/pins.h` has every GPIO from brief §4.2.
- `src/alarm/AlarmEngine`: rules `{block,key,op,threshold,action}` evaluated on each status snapshot, rising-edge firing, actions `notify` / `relay:N:on|off` (calls `b4.handle`), persisted to `/alarms.json`; exposed as block `alarms` (list/add/remove/clear).
- `firmware/PROTOCOL.md` documents all messages, commands and status keys.
- `host/pwa/`: vanilla single-page app (dark, phone-first, no CDN): tabs from `hello.blocks`, canvas chart of any numeric `block.key`, reconnecting `api.send()`, panels `base b1 b2 b3 b4 b5 template alarms`, generic key/value panel for blocks without a panel file, `sw.js` + manifest. `scripts/copy_pwa.py` copies it to `firmware/data/` before every build.
- `host/instrument.py` (typer + websockets, `pyproject.toml`, `pip install -e host/`): `status`, `send`, `stream --seconds --csv`, `alarms list|add|remove`; resolves `instrument.local` then `192.168.4.1`, `--host` overrides.
- `.github/workflows/build.yml`: matrix build of both envs + `buildfs`, ruff check + format on `host/`.
- Root `README.md`, `CLAUDE.md`, `.gitignore`.

**Verified on this machine (Windows, PlatformIO 6.1.19 in `C:\Users\USER\.pio-venv`):**
- `pio run -e esp32s3-sim` → SUCCESS, RAM 15.5 % (50 816 B), Flash 13.9 % (911 717 B of 6 553 600).
- `pio run -e esp32s3` → SUCCESS, Flash 14.0 % (915 721 B). No compiler warnings from project sources.
- `pio run -e esp32s3-sim -t buildfs` → SUCCESS (14 PWA files copied, LittleFS image built).
- `ruff check host/` and `ruff format --check host/` clean; `node --check` passes on every PWA module; `python host/instrument.py --help` runs.

**NOT tested (no hardware in hand, no git repo yet):**
- Nothing has run on a board: WiFi AP/STA, mDNS on the AP interface, OTA, LittleFS mount + static serving, WebSocket traffic at 20 Hz, NeoPixel on GPIO48, `temperatureRead()` values, alarm firing, `/alarms.json` persistence.
- The PWA has not been opened in a browser against a live board (only syntax-checked). Chart, tabs, toasts, panel wiring are unexercised.
- `instrument.py` against a live board. The CI workflow has never run (repo not initialised/pushed).
- `secrets.h` STA path.

**Next:**
1. `git init`, first commit, push to `TIGP-Experimental-Methods/class-board-2026`; confirm CI green.
2. Flash a Jinhua N16R8: `pio run -e esp32s3-sim -t upload && pio run -e esp32s3-sim -t uploadfs`; join the AP; open `http://192.168.4.1`; toggle LED; chart `base.counter`; add an alarm; run `instrument status`. Fix what breaks and record it here.
3. Answer the decisions below, then update README/CLAUDE accordingly.
4. Workbook ch. 0–1 and the tutor skill (per 08 §9) reference these paths and commands.

**Decisions to confirm (instructor):**
- **Template block is registered** and shows as a tab ("Template") on day 1 so students see the copy-me example working. Remove `registry.add(&tpl)` in `main.cpp` and the `PANELS` entry if the extra tab is unwanted.
- **B2 has no rail sensing** in board v0.6 (only LEDs + test points), so `b2` reports nominal values with `measured:false` on real hardware; SIM values wobble. If a sense path is wanted, decide where (ADS8688 ch 7/8 via the OPT jumpers, or an ESP ADC pin) — this affects the schematic.
- **Relay/DIO/TRIG_DIR GPIO writes are implemented** in the `#ifndef SIM` branches (unambiguous pin map); SPI drivers (ADS8688, DAC8563) and the fast outputs are `TODO` stubs. Sine on B3 is synthesised in `loop()` at ~1 kHz, not a real AWG.
- **Alarm actions** are `notify` and `relay:N:on|off` only; `notify` = WebSocket broadcast (PWA toast + browser Notification). LINE/Telegram push would need a bridge (e.g. in `instrument.py`) since the board is on its own AP.
- **Alarm rules fire on the rising edge only** and a relay action is not undone when the condition clears (student decides; a second rule handles the other edge).
- **PWA "install"**: the board serves plain HTTP, so the service worker and the install prompt do not activate on phones (browsers require HTTPS). "Add to Home screen" still works as a shortcut. Accept, or plan HTTPS (self-signed cert = warnings) / a laptop proxy.
- **Platform pin** `espressif32 @ ^7.1.1` (Arduino core 2.0.17) rather than the pioarduino fork with core 3.x. Proven and simple; core-3 APIs (`ledcAttach`, new `Serial` behaviour) are not available.
- **Protocol shape**: `hello` message on connect, `alarms` as a pseudo-block, 20 Hz broadcast only when a client is connected. `status.t` is `millis()`.

**Gotchas:**
- `firmware/data/` is generated and git-ignored; edit `host/pwa/` only, then `pio run -t uploadfs`.
- The Windows path has spaces (`G:\My Drive\2. Presentations\...`); PlatformIO coped, but toolchains live in `C:\Users\USER\.platformio` (2.5 GB after first build).
- `pio` on this machine: `C:\Users\USER\.pio-venv\Scripts\pio` (not on PATH). Set `PYTHONIOENCODING=utf-8` in Git Bash to avoid UnicodeEncodeError from `pio pkg` commands.
- Adafruit NeoPixel is constructed with pin 48 in the header and re-pointed to `PIN_RGB_LED` in `begin()`, so the header stays free of `pins.h`.
