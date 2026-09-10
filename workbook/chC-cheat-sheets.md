# Chapter C — Cheat-sheets

## C.0 Words we use

Every tooling term in this workbook is explained the first time it appears in a chapter; this table collects them all in one place.

**AI and Claude Code**

| Term | Meaning |
|---|---|
| **LLM (large language model)** | the model behind Claude: text becomes tokens, and one operation repeated — predict the next token |
| **token** | a piece of text of roughly three to four characters; the unit the model reads, writes and is billed in |
| **context window / context** | the entire history of your conversation — your messages, files read, tool output, everything. Every time you submit a request you pay for reprocessing the whole history; mistakes and clutter in it can poison the output |
| **hallucination** | a plausible continuation that was never verified — fluent, confident, wrong. Expected whenever the context or specification is insufficient; caught by tests and independent review, not by reading harder |
| **Claude Code** | an agentic coding tool that runs in your terminal, IDE or desktop app, combining a model with built-in tools for reading files, editing, searching, running commands and web access |
| **agent** | a model that can act — Claude Code working on your files: it reads them, writes code, runs commands, and reports back |
| **tool** | a capability Claude can invoke to act on your machine, such as reading a file, editing it, a calculator or running a shell command |
| **agentic loop** | the cycle of Claude reasoning, calling a tool, reading the result, and deciding the next step, repeated until the task is done |
| **permission prompt** | the approval request before a tool call that can change your system — your control point over an autonomous agent |
| **subagent** | a separate agent with its own fresh context that does one delegated task and returns a short result; several can run in parallel ("agent swarms") |
| **model tiers** | Haiku · Sonnet · Opus · Fable — the same idea at different sizes, about 1 : 3 : 5 : 10 in cost; strong model plans and checks, cheap models do the work |
| **CLAUDE.md** | a Markdown file at the project root, read at the start of every session: standing rules — how to run tests, naming conventions, what never to touch, where the docs are. Keep it under a page |
| **memory** | notes the agent writes for itself and re-reads next session; persistent, small, auto-loaded — not the conversation |
| **skill** | instructions and scripts for one kind of task (make a video, write a report), loaded only when the task matches |
| **MCP server** | Model Context Protocol: a standard plug for giving the agent tools — read a Google Sheet, query a database, control an instrument; each tool's description sits in context, the tool runs outside |
| **hook** | a shell command that runs automatically on an event (after every file edit, before a commit); zero tokens, and the model cannot skip it |
| **compaction** | the automated algorithm behind the context icon that deletes most of the current context without saving useful knowledge anywhere — lossy; unsuitable for long tasks |
| **handover (handover.md / HANDOVER.md)** | the file a session writes before it ends so a fresh session can continue: done, remaining, decisions and why, how to test, open problems. The disk is the memory |
| **vision / SPEC.md / PLAN.md** | the AI method's documents: what you want, in detail · what to build and how to test it · the build broken into small tasks with testable deliverables |
| **PROGRESS.md** | your handover notes for this course: done / verified / next / gotchas, one entry per session |
| **Markdown** | plain text with light formatting (`#` headings, `-` lists); what README, SPEC, PLAN, PROGRESS and handover files are written in |
| **the check / the test** | a result you can predict without the program — a value worked out by hand, a conservation law, a limiting case — which the finished thing must reproduce |
| **independent review** | a fresh Claude session that did not write the plan reads `SPEC.md` and `PLAN.md` and lists the flaws — same author, same blind spots, so never the session that wrote them |
| **show-your-work** | the lab's public pipeline of five Claude skills for slides, reports, videos and renders: https://github.com/iams-yb-lab/show-your-work |
| **hand-in / deliverable** | what must exist in a repository at the end |

**Git, GitHub and the web**

| Term | Meaning |
|---|---|
| **repository** | a project folder that git is watching: the files plus their complete history (in a hidden `.git` folder); on GitHub it also lives online |
| **git** | the tool that records the history of a folder of files |
| **GitHub** | the website that hosts a copy of your repository so you can share it and back it up |
| **commit** | a named snapshot of every file in the repository, with the message you wrote (say why, not what) |
| **stage** | choose which changed files go into the next commit (the **+** in Source Control) |
| **diff** | the lines added and removed between two snapshots |
| **history** | the chain of commits |
| **push / pull / sync** | send your new commits to GitHub / bring down commits others pushed / both |
| **clone** | download a full copy of a repository, with its history |
| **branch** | a separate line of history; experiment on it while `main` stays working |
| **main** | the main branch, the version everyone builds on; in the class repository it is protected |
| **merge** | bring a branch's changes into another branch |
| **pull request (PR)** | push a branch, open a PR on GitHub: someone reads the diff, comments, then merges into `main` |
| **fork** | your own copy of someone else's repository on GitHub |
| **.gitignore** | a text file listing what git must never track: raw data, generated output, caches, **secrets** |
| **CI (continuous integration)** | an automatic build that GitHub runs on every pull request and reports green or red |
| **GitHub CLI (`gh`)** | GitHub's command-line tool |
| **terminal** | the text window where you type commands |
| **deploy** | publish so that anyone with the address can open it; the loop is commit → push → the host builds → live |
| **GitHub Pages** | any public repository with an `index.html` becomes a website at `<user>.github.io/<repository>/` (repository → *Settings → Pages → Deploy from a branch → main → / → Save*) |
| **project website / project page** | `index.html` at the root of a project's repository, on GitHub Pages: title, what it is and why it is interesting, how it works, a picture or GIF or short video of it working, what was verified, links to the live app and the repository, your name. The `README.md` stays the developer-facing document |
| **class project wall** | https://tigp-experimental-methods.github.io/showcase-2026/ — one card per project (picture, title, student, two sentences, buttons *Open the app · Project site · Video · Code*), refreshed every minute, on the projector in class. Repository `TIGP-Experimental-Methods/showcase-2026`: one file `projects/<github-username>--<slug>.json` + one picture in `images/` per project; its `README.md` documents the format. The `project` field is `"1"`, `"2"`, `"3"` or `"extra"` — Project 3 (your board section, its firmware and the housing) is **one** card, one repository and one website; `"3a"`/`"3b"` are legacy |
| **GIF** | a short looping animation in one image file; a screen recording of the app moving, or a phone clip of the LED changing, is the best picture for a project page or a wall card |
| **Cloudflare Pages / Workers** | deploys from a GitHub repository on every push; Workers run server-side code on the free tier — for apps that store data, call an API with a key, or run on a schedule |
| **URL** | a web address |
| **webhook** | the platform (LINE, Telegram) calls your URL whenever a message arrives |
| **API key / bot token** | a password that lets a program act as you; keys are money — never in a repository, never in a chat |
| **secret** | a password, a WiFi key, an API token — anything that lets someone else in; never in a chat, a committed file, or a screenshot |

**Firmware and the board**

| Term | Meaning |
|---|---|
| **firmware** | the program that runs on the microcontroller |
| **microcontroller / dev board** | a small computer on a chip; the *development board* carries it with a USB connector and pins so you can use it directly |
| **ESP32-S3** | the microcontroller we use; it has WiFi. Ours: Jinhua #40729 ESP32-S3 N16R8, USB-C, RGB LED on GPIO 48 |
| **flash / upload** | write the firmware onto the board over USB |
| **toolchain** | the compiler and helper programs that turn source code into firmware |
| **PlatformIO** | the tool (and VS Code extension) that builds and flashes the firmware |
| **Arduino framework** | the programming layer we use on the ESP32 (`setup()` and `loop()`) |
| **`pio run -t upload`** | the PlatformIO command that builds the firmware and flashes it |
| **SIM mode** | a build in which the firmware fakes the class-board hardware, so the app and chart work on the bare dev board |
| **access point (AP)** | the board's own WiFi network, which your phone joins (LED blue) |
| **STA (station) mode** | the board joins an existing WiFi network (LED green); needs the network's name and password in the git-ignored `firmware/include/secrets.h` |
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
| **ADC / DAC** | analog-to-digital and digital-to-analog converters |
| **GPIO** | a general-purpose pin on the microcontroller |
| **SPI / I²C** | two common wiring standards for chips to talk to the microcontroller |
| **ring buffer** | a fixed-size list that overwrites its oldest entry |

**The class board (Workshops 2 and 3)**

| Term | Meaning |
|---|---|
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
| **Onshape** | the browser CAD program for the housing |
| **ring reviewer** | the classmate who reviews your pull request (A reviews B, B reviews C, …, E reviews A) |

## C.0b The AI method in one screen

Slide 26 — the most important slide in the talk.

1. **Vision** — describe what you want, with as much detail as possible.
2. **Specification / Plan** — get AI to produce a detailed specification: plan the project. Break it into many small tasks with testable deliverables. Ask AI to ask you questions.
3. **Review** — review the plan; have AI review the plan to identify improvements and flaws, in a fresh Claude session that did not write it. **Iterate the plan: the first plan is never the last plan.**
4. **Code** — tell AI to run swarms of agents in parallel to complete the build.
5. **Test / Debug / Verify** — the plan and spec include methods to test the code. Fix problems one at a time. Iterate.

**Never trust AI without testing and verifying.**

## C.0c Workflow must-dos

Slide 30 — five habits that follow from how LLMs work.

| Must do | Why |
|---|---|
| **Put all needed data in the prompt** | the model attends only to what is in the window; paste the data rather than hoping it was memorised |
| **One topic per session** | the whole transcript is resent and competes for attention; new topic, new chat |
| **Summarise files first** | let a disposable session turn PDFs and images into a detailed Markdown summary; work from that |
| **Cheap workers, strong planner** | route bulk steps to smaller models in fresh contexts; keep the strong model for planning and review |
| **Verify independently** | numbers, citations and code get checked by a separate reviewer or by tests written before the work |

## C.0d When things go wrong

**Oops, I made a mistake** (slide 39). Save your tokens: **stop the execution.** Don't rot or poison your context: **rewind.**

**Context is full** (slides 40–41). Start a new session — but first:

> Please finish what you are working on and document anything from this session that may be useful to future Claude sessions in .md files in this directory and a handover.md file to allow Claude to continue our work in a new session.

Commit. New session; tell it to read the handover file first. Do not rely on compaction — it is lossy. Hand over at about half the window, while the agent can still write a good summary.

**Failure modes specific to agents** (slide 34) — caught by mechanism (hooks, git, tests), not by reading harder:

| Failure | What it looks like | Countermeasure |
|---|---|---|
| **Gaming the test** | makes a failing test pass by weakening the test, hard-coding the value, or catching the exception | protect tests in git; review test diffs first |
| **Claims without running** | "all tests pass" with no test output | a hook that runs the tests and pastes the result |
| **Scope creep** | asked to fix one function, refactors the module | say "change nothing else"; review the diff for files you did not expect |
| **Loops** | the same fix repeatedly with small variations | set a step budget; after three failures, stop and ask |
| **Wrong target** | edits a similarly-named file, or the copy in the wrong folder | give explicit paths; keep the workspace tidy |
| **Destructive actions** | deletes, force-pushes, drops a table to "start clean" | deny-list those commands in hooks; work on a branch; commit first |

And beyond hallucination (slide 33): it invents specifics (look up every number you did not supply) · agrees with you (state the question neutrally) · errors are small — right structure, wrong sign (test with known answers and limiting cases) · requirements dropped (number them; have the reviewer tick each off) · errors multiply — 95 % per step is 36 % over 20 steps (verify at each step) · stale context (new topic, new session). **Rule: use AI where checking is easier than doing.**

## C.1 git and GitHub — from VS Code's Source Control panel (no terminal required)

Source Control is the branching icon in the left bar. Changed files are marked **M**, new files **U**; click one to see its diff. Everything git in this course is done here; the one terminal command you will meet is the secrets check at the bottom, and Claude runs it for you.

| You want to | In VS Code |
|---|---|
| see what changed | Source Control; click a file for its diff |
| stage | **+** next to the file (or next to *Changes* for all) |
| commit | type the message, press *Commit* |
| push | *Publish Branch* the first time; *Sync Changes* afterwards |
| pull others' work | *Sync Changes* |
| new branch | click the branch name (bottom-left) → *Create new branch…* |
| back to main | branch name → `main`; then *Sync* |
| history | Source Control → *Graph*; a file's *Timeline* (bottom of Explorer) |
| undo an uncommitted change | right-click the file → *Discard Changes* |
| undo a commit | Graph → right-click the commit → *Revert* (a new commit that reverses it) |
| new project (one repository per project, public) | a folder next to `class-board-2026` named for the project → *File → Open Folder…* → *Source Control → Initialize Repository* → *Publish Branch* → **public** |
| publish the project website | GitHub → repository → *Settings → Pages → Deploy from a branch → main → / → Save*; `index.html` at the root is the page, the app is in `app/` |
| put a project on the class wall | Claude clones `TIGP-Experimental-Methods/showcase-2026` next to `class-board-2026` (`gh repo clone …`; later *Sync Changes*) → write `projects/<github-username>--<slug>.json` (title, student, github, project, blurb, live_url, site_url, repo_url, image, video_url, updated — the format is in the wall's README) → picture into `images/` (under 8 MB) → Claude runs `python scripts/build.py` → stage both files, commit, *Sync Changes* |
| open a pull request | push the branch; GitHub offers *Compare & pull request* |
| is this file ignored? (the secrets check) | ask Claude to run `git check-ignore -v firmware/include/secrets.h` — it must print the rule; nothing printed means the file is NOT ignored |

Rules: every project is its own public repository under your own GitHub account — push at every milestone (plan reviewed, first working version, deployed, project page written). `main` in the class repository is protected — your work there goes on your branch (`w1-<name>`, later `b<N>-<name>`, `b<N>-fw-<name>`); one pull request per deliverable; the pull request description carries the screenshot; the instructor merges (*Squash and merge*). Review: *Files changed → + on a line → comment*; finish with *Approve* or *Request changes*. With an agent: commit before it starts · ask it to commit as it goes · review the diff, not the file · never let it rewrite history — say no to force-push and reset. Stuck in a merge conflict? Do not fight it — ask the tutor for the fix, then e-mail the instructor (C.7).

## C.2 PlatformIO
```sh
cd firmware
pio run -e esp32s3-sim                 # compile only (SIM = bare dev board)
pio run -e esp32s3-sim -t upload       # flash the code
pio run -e esp32s3-sim -t uploadfs     # flash the web app (host/pwa → LittleFS)
pio device monitor                     # serial console, 115200
pio device list                        # which port is the board on
pio run -e esp32s3 -t upload           # the REAL class board (no SIM) — from Workshop 3
```
(Or from the repository root with `-d firmware`. In VS Code: PlatformIO side bar → `esp32s3-sim` → *Upload*, *Upload Filesystem Image*, *Monitor*.)

**Flashing and serial**
- A board already carrying our firmware shows in `pio device list` as `USB VID:PID=303A:1001` (the chip's built-in USB-Serial/JTAG); `upload` and `uploadfs` reset it by themselves — no buttons.
- A factory-fresh board shows as `303A:4001` and `upload` fails with *"No serial data received"*: hold **BOOT**, tap **RST**, release BOOT. It comes back as `303A:1001` on a **new COM port** — `pio device list` again and flash to that port (`--upload-port COMx`). Once only.
- No port at all: a **data** cable, the **USB** connector (not UART), then the same BOOT+RST.
- Every reset makes the port disappear and reappear; the serial monitor must reconnect and the first boot lines are lost. Normal.
- Boot log of the class firmware (`pio device monitor`, 115200): `[boot] class-board firmware …` · `[registry] … ready` · `[wifi] AP "instrument-XXXX" password "instrument"  http://192.168.4.1/` (LED blue) or `[wifi] STA <ip>  http://instrument-XXXX.local/` (LED green) · `[http] server started`. `alarms.json does not exist` on the first boot is harmless.
- Log stops at `boot:0x0 (DOWNLOAD(USB/UART0))` / `waiting for download`: the chip is in download mode — press RST (or flash).
- `XXXX` = the last four hex digits of the board's MAC address, printed in the boot log. Windows' own WiFi list may lag behind; the phone's list is the real test.
- Upload works but the app is old: you forgot `uploadfs`. LED colours: blue = access point, green = on an existing WiFi network.
- Phone: join the board's network; stay connected when it warns about no internet; Android — mobile data off; type the `http://` yourself.

**Secrets**
- Never type a password, WiFi key or API token into a Claude chat, a prompt, `PROGRESS.md`, `SPEC.md`, a commit message, a pull request, an issue or a screenshot. Transcripts are stored; repositories are shared or public; commits are forever.
- An existing WiFi network: copy `firmware/include/secrets.h.example` → `firmware/include/secrets.h` (network name filled in, password as `PUT-THE-PASSWORD-HERE`) · **you** type the password into the file in the editor · `git check-ignore -v firmware/include/secrets.h` must print a line (nothing printed → stop, do not commit, tell the instructor) · `git status` before every commit: no `secrets.h` · rebuild, flash.
- The tutor never asks for a secret. Pasted one anyway? Remove it from the chat history if you can, treat it as exposed, tell the instructor.
- Bot tokens (LINE / Telegram) and cloud keys (Cloudflare, GitHub, Anthropic) go the same way: a git-ignored config file, an environment variable, or the host's secret store (Cloudflare → *Settings → Variables*) — never source code that is committed. If a key is ever committed, revoke it; the history is public forever.

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

## C.4 The review checklist (the instructor's merge list for the class board)
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
## 2026-09-11 — Workshop 1 (class)
- Done: pendulum simulator from SPEC.md, app at https://alice.github.io/pendulum-sim/app/, project page drafted; class firmware flashed, phone controls the LED
- Verified: period 2.007 s at L = 1 m (predicted 2.006 s); energy drift 0.03 % with no friction; LED red on tap
- Next: brightness slider in my own ESP32 app; finish the project page and the wall entry; KiCad installed
- Gotchas: first plan animated the swing instead of integrating it — rejected; first flash needed BOOT+RST, new COM port
```

## C.7 Who to ask
Tutor on your screen (`/tutor <chapter>`) → stuck: ask the tutor for the fix → still stuck: **e-mail the instructor** with a screenshot → from Workshop 2, your ring reviewer for anything about your section of the board.
