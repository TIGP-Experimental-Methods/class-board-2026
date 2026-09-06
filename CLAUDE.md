# CLAUDE.md — class-board-2026

Software for the TIGP teaching instrument (ESP32-S3 + five student blocks + phone PWA + Python CLI). Course planning lives in the sibling repository `20260910-TIGP` (docs 08, 09, 10); this repository is what students clone.

## Start and end of every session
- Read [HANDOVER.md](HANDOVER.md) (latest entry first), then [README.md](README.md) and [firmware/PROTOCOL.md](firmware/PROTOCOL.md).
- End by adding a HANDOVER entry (done / verified / next / gotchas) and committing. Never keep project state in machine-local memory.

## Conventions (binding)
- **Blocks are self-contained.** One folder `firmware/src/blocks/b<N>_<name>/`, one class implementing `Block` (`name/begin/loop/handle/status`), one panel `host/pwa/panels/b<N>.js`. A block never includes or calls another block; the alarm engine is the only cross-block actor (relay actions on `b4`).
- **SIM must always compile and run.** Every block has a `#ifdef SIM` branch that fakes its hardware with plausible values. `pio run -e esp32s3-sim` on a bare dev board is the day-1 experience; do not break it.
- **Real-hardware code is `TODO` until measured.** Do not invent register sequences or values; pin numbers come only from `include/pins.h` (design brief §4.2). Unambiguous GPIO writes (relays, DIO, TRIG_DIR) are implemented; SPI devices and fast outputs are stubs.
- **All block code runs from `loop()`.** WebSocket messages are queued and handled in `loop()`; blocks need no locks, tasks or ISRs (an ISR that only increments a `volatile` counter is fine).
- **Every PR builds in CI** (`.github/workflows/build.yml`: both envs + LittleFS image + ruff). No PR merges red.
- **Students edit only** `firmware/src/blocks/b<N>_*/`, `host/pwa/panels/b<N>.js`, and the one `registry.add` line in `main.cpp` / one `PANELS` entry in `app.js` if their block is new. Everything else is the instructor's; propose changes in the PR description.
- **Protocol changes** go to `firmware/PROTOCOL.md` in the same PR, and `host/instrument.py` must still work.
- **Naming:** block ids `base b1 b2 b3 b4 b5 alarms template`; folders `b1_inputs b2_power b3_outputs b4_switching b5_dio_trig`; commands and status keys `snake_case`; status keys that a panel shows must exist in `status()`.
- **Style:** small files, comments say *why*, no clever abstractions, no new libraries without a line in HANDOVER explaining the choice. PWA is vanilla JS with no build step and no CDN (the board is offline).
- `firmware/data/` is generated (from `host/pwa/` by `scripts/copy_pwa.py`) and git-ignored; edit `host/pwa/` only. `include/secrets.h` is git-ignored.

## Secrets (binding for every agent working in this repository)
- A secret is a password, a WiFi key, an API token (LINE / Telegram bot tokens, Cloudflare or GitHub tokens) — anything that lets someone else in. Never ask the student for one. Never read `firmware/include/secrets.h` aloud, print it, or copy its values anywhere. Never write a secret into any tracked file, commit message, pull request, issue, `PROGRESS.md`, `SPEC.md` or `notes.md`. Chat transcripts are stored; this repository is public; commits are forever.
- Procedure for the lab WiFi: copy `firmware/include/secrets.h.example` to `firmware/include/secrets.h` with the network name filled in and the password as a placeholder such as `PUT-THE-PASSWORD-HERE`; the **student** types the password into that file in the editor, never in the chat; `git check-ignore -v firmware/include/secrets.h` must print a line — if it prints nothing, stop, do not commit, tell the instructor; `git status` before every commit must not list `secrets.h`; then rebuild and flash.
- A secret pasted into the chat is exposed: say so, have the student remove it from the history if they can, and tell the instructor. Later tokens (bots, cloud) go into git-ignored config files or environment variables, never into committed source.

## Hardware facts
The verified behaviour of the Jinhua #40729 board — USB `303A:4001` (factory) vs `303A:1001` (ours), BOOT+RST once at the first flash and the new COM port, the port that disappears at every reset, reading the serial port from an agent (pyserial, `dtr=False`/`rts=False` before opening, never toggled; `pio device monitor` needs an interactive terminal), the expected boot log, `instrument-XXXX` / `instrument-XXXX.local` — is in [tutor/COURSE-GUIDE.md](tutor/COURSE-GUIDE.md), section *Hardware facts*. Read it before flashing or reading a port.

## Quick commands
One command per line (Windows PowerShell 5.1 has no `&&`):
```sh
pio run -d firmware -e esp32s3-sim -t upload
pio run -d firmware -e esp32s3-sim -t uploadfs
pio device monitor            # needs an interactive terminal: the student runs it, an agent reads the port with pyserial instead
pip install -e host/
instrument status
ruff check host/
```
