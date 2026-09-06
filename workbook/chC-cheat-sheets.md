# Chapter C — Cheat-sheets

## C.0 Words we use

Every tooling term in this workbook is explained the first time it appears in a chapter; this table collects them all in one place.

| Term | Meaning |
|---|---|
| **repository (repo)** | a project folder whose complete history git keeps; on GitHub it also lives online |
| **GitHub** | the website where repositories are stored and shared |
| **git** | the tool that records the history of a folder of files |
| **commit** | save a snapshot of your changes with a one-line message |
| **push** | upload your commits to GitHub |
| **clone** | download a full copy of a repository to your laptop |
| **branch** | a separate line of work inside a repository, so several people can change things without treading on each other |
| **merge** | bring a branch's changes into the main line |
| **pull request (PR)** | a request to merge your branch into the shared project; someone reviews it first, comments, and approves |
| **fork** | your own copy of someone else's repository on GitHub |
| **main** | the main branch, the version everyone builds on |
| **CI (continuous integration)** | an automatic build that GitHub runs on every pull request and reports green or red |
| **GitHub CLI (`gh`)** | GitHub's command-line tool (log in, create repositories, open pull requests from the terminal) |
| **terminal** | the text window where you type commands |
| **Markdown** | plain text with light formatting (`#` headings, `-` lists); what README, SPEC and PROGRESS files are written in |
| **SPEC.md / PROGRESS.md / CLAUDE.md** | plain-text files in the repository: what to build · what was done, verified, next, gotchas · how the project is set up (read by the agent every session) |
| **agent / coding agent** | Claude Code working on your files: it reads them, writes code, runs commands, and reports back |
| **Cloudflare Pages / GitHub Pages** | free services that turn a repository into a public web page |
| **deploy** | publish the page so it is live on the web |
| **ship** | publish it where others can open it |
| **URL** | a web address |
| **firmware** | the program that runs on the microcontroller |
| **microcontroller / dev board** | a small computer on a chip; the *development board* carries it with a USB connector and pins so you can use it directly |
| **ESP32-S3** | the microcontroller we use; it has WiFi |
| **flash / upload** | write the firmware onto the board over USB |
| **toolchain** | the compiler and helper programs that turn source code into firmware |
| **PlatformIO** | the tool (and VS Code extension) that builds and flashes the firmware for us |
| **`pio run -t upload`** | the PlatformIO command that builds the firmware and flashes it |
| **SIM mode** | a build in which the firmware fakes its hardware, so the app and chart work on the bare dev board before the class board exists |
| **access point (AP)** | the board's own WiFi network, which your phone joins (LED blue) |
| **STA (station) mode** | the board joins an existing WiFi network instead of making its own (LED green); needs the network's name and password in `firmware/include/secrets.h` |
| **secret** | a password, a WiFi key, an API token — anything that lets someone else in; never in a chat, a file that is committed, or a screenshot |
| **serial port / serial monitor** | the text connection over USB on which the board prints its log (Windows `COMn`); the monitor is the program that shows it |
| **USB-Serial/JTAG** | the USB-to-serial converter built into the ESP32-S3 chip; because it is inside the chip, the port disappears and reappears at every reset |
| **download mode** | the chip waiting to be flashed instead of running the firmware (log says `waiting for download`); a press of RST leaves it |
| **PWA / the app** | the phone app is a web page served by the board that behaves like an app (progressive web app) |
| **WebSocket** | a live two-way connection between the phone page and the board |
| **JSON** | a plain-text format for structured data, e.g. `{"cmd":"led","r":255}` |
| **status message** | the numbers the board sends the phone many times a second |
| **handler** | the piece of firmware that acts on one command |
| **widget** | one control or readout on the phone app |
| **Python client / `instrument.py`** | a Python program on your PC that talks to the board with the same messages as the phone |
| **OTA (over-the-air)** | updating the firmware over WiFi instead of USB |
| **LittleFS** | the small file store on the board where the app's files live |
| **KiCad** | the free program we draw the schematic and lay out the printed circuit board in |
| **schematic** | the circuit drawing |
| **PCB / layout** | the physical board design with copper tracks |
| **footprint** | the copper pattern a part is soldered onto |
| **symbol** | a part's drawing in the schematic |
| **library** | the set of symbols and footprints for our parts |
| **ERC / DRC** | KiCad's electrical / design rule checks; zero errors means the checks pass |
| **rule area / zone** | the outlined region of the board that is yours to route |
| **routing** | drawing the copper tracks between parts |
| **net** | a set of pins that are connected together |
| **JLCPCB / LCSC** | the factory that makes and assembles our boards, and its parts catalogue |
| **BOM** | the bill of materials, the parts list |
| **Gerbers** | the manufacturing files sent to the factory |
| **STL / STEP** | 3D file formats (for printing / for CAD exchange) |
| **Onshape** | the browser CAD program for the box |
| **ADC / DAC** | analog-to-digital and digital-to-analog converters |
| **GPIO** | a general-purpose pin on the microcontroller |
| **SPI / I²C** | two common wiring standards for chips to talk to the microcontroller |
| **ring buffer** | a fixed-size list that overwrites its oldest entry |
| **the check / the test** | one result you can work out by hand before any code exists (e.g. the cut-off frequency of an RC filter for a given R and C), which the finished page must reproduce |
| **hand-in / deliverable** | what must exist in the repository at the end |
| **ring reviewer** | the classmate who reviews your pull request (A reviews B, B reviews C, …, E reviews A) |

## C.1 git and GitHub — the ten commands you use
```sh
git status                          # what changed
git switch -c e2-<name>             # new branch (e2-<name>, b<N>-<name>, b<N>-fw-<name>)
git add -A                          # stage everything (or: git add path/)
git commit -m "E2: press button + presses counter"
git push -u origin <branch>         # first push of a branch
gh pr create --fill                 # open the PR (then add the screenshot on GitHub)
git switch main && git pull         # back to main, get everyone's merges
git log --oneline -10               # what happened
git diff                            # what you changed, unstaged
git restore <file>                  # undo an unstaged change to one file
```
Rules: `main` is protected; one PR per deliverable; the PR description carries the screenshot; the instructor merges (*Squash and merge*). Review: *Files changed → + on a line → comment*; finish with *Approve* or *Request changes*. Stuck in a merge conflict? Do not fight it — ask the tutor for the fix, then email the instructor (C.7).

## C.2 PlatformIO
```sh
cd firmware
pio run -e esp32s3-sim                 # compile only (SIM = bare dev board)
pio run -e esp32s3-sim -t upload       # flash the code
pio run -e esp32s3-sim -t uploadfs     # flash the web app (host/pwa → LittleFS)
pio device monitor                     # serial console, 115200
pio device list                        # which port is the board on
pio run -e esp32s3 -t upload           # the REAL board (no SIM) — wrap-up only
```
**Flashing and serial**
- A board flashed in class shows in `pio device list` as `USB VID:PID=303A:1001` (the chip's built-in USB-Serial/JTAG); `upload` and `uploadfs` reset it by themselves — no buttons.
- A factory-fresh board shows as `303A:4001` and `upload` fails with *"No serial data received"*: hold **BOOT**, tap **RST**, release BOOT. It comes back as `303A:1001` on a **new COM port** — `pio device list` again and flash to that port (`--upload-port COMx`). Once only.
- No port at all: a **data** cable, the **USB** connector (not UART), then the same BOOT+RST.
- Every reset makes the port disappear and reappear; the serial monitor must reconnect and the first boot lines are lost. Normal.
- Boot log (`pio device monitor`, 115200): `[boot] class-board firmware …` · `[registry] … ready` · `[wifi] AP "instrument-XXXX" password "instrument"  http://192.168.4.1/` (LED blue) or `[wifi] STA <ip>  http://instrument-XXXX.local/` (LED green) · `[http] server started`. `alarms.json does not exist` on the first boot is harmless.
- Log stops at `boot:0x0 (DOWNLOAD(USB/UART0))` / `waiting for download`: the chip is in download mode — press RST (or flash).
- `XXXX` = the last four hex digits of the board's MAC address, printed in the boot log. Windows' own WiFi list may lag behind; the phone's list is the real test.
- Upload works but the app is old: you forgot `uploadfs`. LED colours: blue = access point, green = on the lab WiFi.

**Secrets**
- Never type a password, WiFi key or API token into a Claude chat, a prompt, `PROGRESS.md`, `SPEC.md`, `notes.md`, a commit message, a pull request, an issue or a screenshot. Transcripts are stored; repositories are shared or public; commits are forever.
- Lab WiFi: copy `firmware/include/secrets.h.example` → `firmware/include/secrets.h` (network name filled in, password as `PUT-THE-PASSWORD-HERE`) · **you** type the password into the file in the editor · `git check-ignore -v firmware/include/secrets.h` must print a line (nothing printed → stop, do not commit, tell the instructor) · `git status` before every commit: no `secrets.h` · rebuild, flash.
- The tutor never asks for a secret. Pasted one anyway? Remove it from the chat history if you can, treat it as exposed, tell the instructor.
- Later in the course, bot tokens (LINE / Telegram) and cloud tokens (Cloudflare, GitHub) go the same way: a git-ignored config file or an environment variable, never source code that is committed.

## C.3 KiCad 10 — the six operations and their keys
| Operation | Where | Key |
|---|---|---|
| Place a symbol | schematic | `A` (project library `class_board`) |
| Wire | schematic | `W`; `K` ends a wire |
| Value / edit fields | schematic | `V` / `E` (check the **Footprint** field) |
| Annotate | schematic | *Tools → Annotate* |
| ERC | schematic | *Inspect → Electrical Rules Checker* |
| Update PCB from schematic | schematic → PCB | `F8` |
| Move / rotate a footprint | PCB | `M` / `R` |
| Route a track | PCB | `X`; `V` drops a via and switches layer |
| Fill zones | PCB | `B` |
| DRC | PCB | *Inspect → Design Rules Checker* |
| 3D view | PCB | `Alt+3` |
| Layers | PCB | F.Cu top signals · **In1.Cu = GND, do not route** · In2.Cu power (instructor) · B.Cu bottom signals |

Your rule area is `ZONE_B<N>`; nothing outside it; do not touch net classes or the instructor's tracks. Library: `hardware/lib/class_board.*`; new part: `easyeda2kicad --full --lcsc_id C… --output "<abs path>/hardware/lib/class_board"`.

## C.4 The review checklist (E10; the instructor's merge list)
- [ ] ERC 0 errors · DRC 0 errors, 0 unrouted
- [ ] `LCSC` field on every part
- [ ] values match the PDF
- [ ] decoupling capacitors next to the pins they serve
- [ ] nothing on In1.Cu
- [ ] nothing outside the rule area
- [ ] pin 1 marked on the silkscreen for every IC and connector
- [ ] ground pour joined (no islands)
- [ ] B4: isolation band ≥ 2.5 mm, no copper under it
- [ ] a silkscreen label on every connector
- [ ] CI green

## C.5 The protocol in one screen
Command: `{"id":1,"block":"b4","cmd":"relay","args":{"n":1,"on":true}}` → reply `{"id":1,"ok":true,"result":{…}}`.
Status (20 Hz): `{"type":"status","t":ms,"blocks":{"base":{…},"b1":{…}}}` — numeric top-level keys are chartable and alarmable.
Alarm rule: `{block, key, op: gt|lt|ge|le|eq|ne, threshold, action: notify | relay:<n>:on|off}`.
Scope: `stream {ch, rate_hz, chunk}` (rolling; `rate_hz: 0` stops) · `capture {ch, rate_hz, n, trig:{level, edge, pre}}` (one binary frame). Full list: `firmware/PROTOCOL.md`.

## C.6 The four log lines (`PROGRESS.md`, every session)
```markdown
## 2026-09-18 — L2 (class)
- Done: placed the 4 missing parts on b3_gapped; ERC 0; half of ZONE_B3 routed
- Verified: DRC shows only unrouted items; 3D view looks like the PDF
- Next: finish AO2 routing; E8 OPA2192 from LCSC; open the PR
- Gotchas: F8 put the new footprints outside my zone — drag them in first
```

## C.7 Who to ask
Tutor on your screen (`/tutor <chapter>`) → stuck: ask the tutor for the fix → still stuck: **email the instructor** with a screenshot → your ring reviewer for anything about your block's design.
