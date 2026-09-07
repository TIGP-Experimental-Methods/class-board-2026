# Chapter 1 — Day 1 + week 1: build it, ship it, log it — then your instrument

**Fri 2026-09-11, 14:20–16:20 + Homework 1.** Two deliverables today (a deliverable is what must exist in your repository — the project folder whose complete history git keeps — at the end): a page that teaches one idea you know to a high-school student, on the public web, before the break; your own phone app measuring something on your ESP32 (the microcontroller we use — a small computer on a chip, with WiFi) by the end. Tooling terms are explained the first time they appear and collected in the glossary, [chapter C](chC-cheat-sheets.md#c0-words-we-use).

**Why the first exercise is a teaching page.** The skill is working with an agent (Claude Code working on your files: it reads them, writes code, runs commands, and reports back) that writes code you did not write — so the first thing you build is something whose correct behaviour you can compute by hand. You are the author; the agent is the junior engineer. The ESP32 comes second because there the answer is not known in advance.

**The five working practices** (a short lecture; the rest of the day is practice):
1. **Spec first** — `SPEC.md` (a plain-text file saying what to build), not the chat history; a plan before code.
2. **Teach the repository, not the session** — `CLAUDE.md` (the file the agent reads at the start of every session): conventions, pinout, build/flash/test commands.
3. **Small, fresh sessions** — one task, one session; finish, commit (save a snapshot of your changes with a one-line message), start clean.
4. **Handover notes, in Markdown** (plain text with light formatting) — `PROGRESS.md`: done / verified / next / gotchas. The lab notebook for this course and what the agent reads first next time.
5. **AI writes, you verify** — a number or an observation, written down, or it does not ship.

*Thesis:* an agent is a junior engineer with no memory — as good as the documentation, the spec and the verification you give it.

---

## Part A — In class

### A.0 Tutor on
Open Claude Code **in the class repository** (VS Code: *File → Open Folder…* → `class-board-2026`), type `/tutor L1`, answer its questions (language; what you have built; `expert` if you want each step's whole recipe instead of pacing). It runs the toolchain check (the toolchain is the compiler and helper programs that turn source code into firmware), creates the branch `e2-<name>` (a branch is a separate line of work inside a repository, so several people can change things without getting in each other's way — everything you commit in the class repository today goes on it, `PROGRESS.md` included) and creates `docs/students/<name>/PROGRESS.md`.
- [ ] `git --version` · `gh auth status` · `pio --version` · board on a port (`pio device list`) · Cloudflare dashboard signed in
- ✔ **toolchain OK**

### A.1 Exercise E1a — build: teach one idea to a high-school student
**Pick a topic you know** — electromagnetism, electronics, classical mechanics, PID control, anything from your own research — and build, with the agent, the thing that teaches it to a high-school student: an interactive simulation, a game, a page with sliders and a live plot. You choose the idea, you write the spec, you predict the number the page must get right, and you check it. The agent writes the code.

| Topic (examples — yours is better) | What the learner can do afterwards | The check you predict before any code exists |
|---|---|---|
| **RC low-pass filter explorer** — sliders for R and C, live Bode plot | predict the cut-off of any RC pair and what happens to the phase | R = 1 kΩ, C = 100 nF → f_c = 1/(2πRC) = 1591.5 Hz; −3.01 dB and −45.0° there; −20 dB at 10 f_c |
| **PID on a cart or a heater** — three sliders, step response | say what P, I and D each do to overshoot and settling | settling time and overshoot from the closed-loop poles for the gains you set |
| **Field of two charges** — drag the charges, see the lines | superposition | the field at one point on the axis, computed by hand |
| **Cart-pole / pendulum** — push the cart, toggle balance | small oscillations, feedback | period 2π√(L/g) × √(M/(M+m)) (reference repository: pendulum-example) |
| **Two-body orbit** — launch speed slider | Kepler's laws | T² ∝ a³ across three orbits |
| **Standing waves on a string** — frequency slider | resonance, nodes | f_n = n·v/2L |
| *Lab tool instead of a teaching page:* **CSV → scope** — drop a scope CSV, get stats + FFT + sine fit | — | mean, sd = √(A²/2 + σ²), f, amplitude (reference repository: csv-scope-example) |

1. **Repository.** Open a terminal (the text window where you type commands), go up one level to your course folder, next to `class-board-2026`, and create your own repository there (pick a short name for your topic); one command per line:
   ```sh
   cd ..
   gh repo create <your-github-user>/rc-filter --public --clone
   cd rc-filter
   code .
   ```
   `code .` opens the new folder in a second VS Code window. In *that* window you work with plain Claude Code (there is no `/tutor` there); keep the class-repository window for the tutor. `--public` or `--private` — your choice. Cloudflare Pages (a free service that turns a repository into a public web page) deploys private repositories too; the fallback, GitHub Pages (the same service from GitHub, the website where repositories are stored and shared), needs a public one.
2. **`SPEC.md` — you write it, before any code.** Five lines; the two checks are the lines that matter:
   ```markdown
   # rc-filter — SPEC
   - Teaches: why a resistor and a capacitor make a low-pass filter. Afterwards a high-school student can predict the cut-off frequency of any RC pair and say what happens to the phase there.
   - Shows: the circuit; sliders for R (100 Ω–100 kΩ) and C (1 nF–10 µF); a live Bode plot (gain in dB and phase, log frequency axis) with a marker at −3 dB; a sine of chosen frequency in and out, side by side in time.
   - Check (predicted before the code exists): R = 1 kΩ, C = 100 nF → f_c = 1/(2πRC) = 1591.5 Hz; gain −3.01 dB and phase −45.0° at f_c; −20.0 dB at 10·f_c (all within 0.1 dB / 0.5°).
   - Teaching check: three questions at the bottom, answers hidden until tapped; the first is "double C — what happens to f_c?" (halves).
   - One file, index.html, canvas + plain JavaScript, no libraries, nothing to compile, works on a phone.
   ```
   Do not ask Claude for code until this file exists (the tutor will hold you to it). The *Teaches* line is the one most people skip: what should the learner be able to do afterwards that they could not before? The *Check* line is the one you must get right yourself, on paper, first.
3. **Plan, then code.** "Read SPEC.md. Plan in five bullets, then write index.html." Read the plan: does it compute the physics from the parameters, or draw a picture that happens to look right? Reject the picture.
4. **Run and check.** Open `index.html` in a browser (double-click it in your file manager). Set the parameters from your check line. Read the numbers off the page against your predictions. Write the comparison into `SPEC.md`. If one is off, that is the exercise: which one, by how much, and why (a degrees/radians slip, a log axis drawn linearly, the marker on the wrong curve).
5. **Commit.**
   ```sh
   git add .
   git commit -m "rc-filter: spec, interactive Bode plot, checks pass at 1 kΩ / 100 nF"
   ```
- ✔ Page runs; predictions vs results in `SPEC.md`; one commit.
- **Stretch (if you finish early — the part worth your time):** make the **teaching check** real — the page asks the learner a question and checks the answer · add a **second idea** that builds on the first (RC → RLC resonance; PID → a disturbance) · or start the **explainer video**: the lab's [show-your-work](https://github.com/iams-yb-lab/show-your-work) `education-video` skill turns your `SPEC.md` and page into a script, narration and picture; post it on a YouTube channel of your own and embed it in the page. Optional today; the recommended route for your 60-second video in the wrap-up.
- **Options (same rules — one output predicted before the code exists):** the **CSV → scope lab tool** (every lab has the problem; reference repository `csv-scope-example`) · the **cart-pole** (reference repository `pendulum-example`). Pick with the tutor. *Stuck on tooling, not on the problem?* Fork a reference repository (make your own copy of it on GitHub; links on the course site) and do the check on it.

### A.2 Exercise E1b — ship + log (before the break)
1. `git push -u origin main` (push: upload your commits to GitHub; `main` is the main branch, the version everyone builds on)
2. Cloudflare → *Workers & Pages → Create → Pages → Connect to Git* → your repository → branch `main` → build command **blank**, output directory `/` → *Save and Deploy* → `https://<project-name>.pages.dev` once the deploy finishes. *Fallback:* GitHub → *Settings → Pages → Deploy from a branch → main → /*.
3. Open it on your phone; move a slider. Send the link to someone who is not a physicist and ask them the first teaching question.
4. `PROGRESS.md`, four lines, your words:
   ```markdown
   # PROGRESS
   ## 2026-09-11 — session 1 (class)
   - Done: rc-filter teaching page (index.html) from SPEC.md; deployed to https://rc-filter.pages.dev
   - Verified: f_c 1591 Hz (pred. 1591.5), −3.0 dB / −45° at f_c, −20.0 dB at 10 f_c; sliders work on my phone
   - Next: the teaching questions check the answer; RLC resonance as idea two; try the education-video skill
   - Gotchas: Cloudflare output directory must be "/"; first plan drew the Bode curve from a lookup table — rejected
   ```
   Commit, push; watch the redeploy. From now on every push republishes the page.
- ✔ Public URL (web address) works on your phone; `PROGRESS.md` on GitHub. This repository is your course page from now on: the wrap-up video and your measured number go here too.

### A.3 The instrument on your phone (after the break)
Your dev board (the development board: the ESP32 on a small board with a USB connector and pins) is flashed in class — you write the skeleton firmware onto it over USB yourself (A.4 step 5; a brand-new board needs BOOT+RST once) — and then it is a WiFi access point (its own WiFi network, which your phone joins; LED blue).
1. Phone joins `instrument-XXXX` (label on the board; password `instrument`). The phone will warn that this network has no internet: choose to stay connected, and on Android switch mobile data off for now, or the phone silently jumps back to it. Type **http://192.168.4.1** into the browser yourself, with the `http://` (the browser otherwise tries `https`, which the board does not serve). Tap *Red*; the chart plots `base.counter`.
2. The two files a control touches — open them:
   - `firmware/src/blocks/base/BaseBlock.cpp`: `handle()` receives the message `{"id":1,"block":"base","cmd":"led","args":{"r":255,"g":0,"b":0}}` and reads `cmd` and `args`; `status()` fills the numbers the phone sees at 20 Hz.
   - `host/pwa/panels/base.js`: `render()` builds the controls and calls `api.send('base','led',{r,g,b})`; `onStatus(st)` updates the readouts.
   One JSON message (JSON: the plain-text format for structured data you see in the braces above) phone → board over a WebSocket (a live two-way connection between the phone page and the board), one reply, twenty status messages a second board → phone. `host/instrument.py` (a Python program on your PC) speaks the same messages. Everything runs from `loop()`; nothing may block. Full protocol: `firmware/PROTOCOL.md`.
- ✔ Your phone controls your board.

### A.4 Exercise E2 — your phone app measures something on your ESP32
**One command out, one live measurement back — with its noise.** You add one command and three status values to the base block, one control and two readouts to its panel, flash, verify against a prediction, and open a pull request (PR — a request to merge your changes into the shared project; someone reviews it first, comments, and approves). The tutor writes the boilerplate (the repetitive scaffolding code); you write the message name, the handler body (the piece of firmware that acts on one command), the statistics and the widget (one control or readout on the phone app).

Default: **an averaged ADC (analog-to-digital converter) reading and the noise of that average**, averaging length set from the phone — the smallest possible version of a data logger. The board samples GPIO 4 at 1 kHz into a ring buffer (a fixed-size list that overwrites its oldest entry) of 4096 samples; the statistics are computed 20 times a second, when the status message is built, not per sample.
1. `firmware/src/blocks/base/BaseBlock.h`, `private:` — the ring buffer and its bookkeeping:
   ```cpp
   static constexpr int ADC_PIN = 4;        // free GPIO on the bare dev board (ADC1_CH3)
   static constexpr int ADC_MAX_N = 4096;   // 8 kB of samples: the last 4 s at 1 kHz
   uint16_t adcBuf_[ADC_MAX_N];             // millivolts
   int adcHead_ = 0;                        // next slot to write
   int adcN_ = 16;                          // averaging length n, set from the phone (1..1024)
   uint32_t lastSample_ = 0;
   ```
2. `BaseBlock.cpp`, `loop()` — sample at 1 kHz, no `delay()`, nothing else:
   ```cpp
   uint32_t now = micros();
   if (now - lastSample_ >= 1000) {
     lastSample_ = now;
     adcBuf_[adcHead_] = analogReadMilliVolts(ADC_PIN);
     adcHead_ = (adcHead_ + 1) % ADC_MAX_N;
   }
   ```
3. `handle()`, at the `TODO(E2)` marker — the command:
   ```cpp
   if (strcmp(c, "set_avg") == 0) {                   // {"n": 1..1024}
     int n = a["n"] | adcN_;
     if (n < 1 || n > 1024) { reply["error"] = "n must be 1..1024"; return false; }
     adcN_ = n; reply["n"] = adcN_; return true;
   }
   ```
   `status()` — the statistics. Split the 4096 samples into `blocks = 4096 / n` consecutive blocks of `n`, take each block's mean; `adc_v` is the mean of the newest block, `adc_sd` is the standard deviation of all the block means — the noise of one n-sample average:
   ```cpp
   int n = adcN_, blocks = ADC_MAX_N / n;
   double sum = 0, sum2 = 0, newest = 0;
   for (int k = 0; k < blocks; k++) {                 // block k ends k*n samples before the newest
     double s = 0;
     for (int i = 0; i < n; i++) s += adcBuf_[(adcHead_ - 1 - k * n - i + ADC_MAX_N) % ADC_MAX_N];
     double m = s / n / 1000.0;                       // this block's mean, in V
     if (k == 0) newest = m;
     sum += m; sum2 += m * m;
   }
   double mean = sum / blocks;
   out["adc_v"]  = newest;
   out["adc_sd"] = sqrt(fmax(0.0, sum2 / blocks - mean * mean));
   out["avg_n"]  = n;
   ```
4. `host/pwa/panels/base.js`, at the `TODO(E2)` marker — a number input `N` (1..1024) with a *Set* button → `api.send('base','set_avg',{n: Number(...)})`; two readouts for `adc_v` (V, 3 decimals) and `adc_sd` (mV, 2 decimals) filled in `onStatus`; add `adcV: el.querySelector('#adc-v'), adcSd: el.querySelector('#adc-sd')` to the `els` object in `render()` so `onStatus` can find them.
5. **Flash** (from the class repository root; one command per line):
   ```sh
   pio device list
   pio run -d firmware -e esp32s3-sim -t upload
   pio run -d firmware -e esp32s3-sim -t uploadfs
   ```
   Your board is brand new, so expect the first-flash trap: if `upload` ends with **"No serial data received"**, hold **BOOT**, tap **RST**, release BOOT, then `pio device list` again — the board is now on a **new COM port** — and flash to that port. From then on both commands reset it by themselves. Two things are normal: **the board's USB port disappears and reappears at every reset** (the USB-to-serial converter is inside the chip), so a serial monitor has to reconnect after every flash and the first boot lines may be missing; and the new COM port after BOOT+RST (ours went COM6 → COM10; `--upload-port COMx` if PlatformIO picks the wrong one). No port at all: a data cable, the *USB* connector, then the same BOOT+RST.

   > **Secrets stay out of the chat.** A secret is a password, a WiFi key, an API token (the LINE / Telegram bot tokens later in the course) — anything that lets someone else in. Never type one into a Claude chat, a prompt, `PROGRESS.md`, `SPEC.md`, `notes.md`, a commit message, a pull request, an issue, the logbook or a screenshot: chat transcripts are stored, repositories are shared or public, commits are forever. Today your board runs its own access point and needs no secret. When you want it on a lab WiFi network instead: (a) the tutor (or you) copies `firmware/include/secrets.h.example` to `firmware/include/secrets.h` with the network name filled in and the password as a placeholder such as `PUT-THE-PASSWORD-HERE`; (b) **you** type the password into that file in the editor — not in the chat; (c) `git check-ignore -v firmware/include/secrets.h` must print a line (the `.gitignore` rule that keeps the file out of every commit) — if it prints nothing, stop, do not commit, tell the instructor; (d) `git status` before every commit: `secrets.h` must not be listed; (e) rebuild and flash. The tutor never asks for a secret and never repeats one. Pasted one anyway? Delete it from the chat history if you can, treat it as exposed, and tell the instructor — a WiFi password may need changing.
6. **Verify against a prediction.** GPIO 4 (a general-purpose pin on the microcontroller) floating, or with a short jumper wire in it. Set N = 1, 4, 16, 64, 256 from the phone and record `adc_sd` each time (chart `base.adc_sd`). `adc_sd` is the noise of one N-sample average; at N = 1 it is the noise of a single sample. For independent samples adc_sd(N) = adc_sd(1)/√N — a factor 16 from N = 1 to 256. Your table in the pull request has three columns: N, measured `adc_sd`, predicted adc_sd(1)/√N. It will not obey exactly; say what you see and why. One thing to know: at N = 256 the estimate comes from only 16 block means, so it is itself uncertain by roughly 20 % — a deviation smaller than that is not a deviation. **The table and one explanatory sentence are the deliverable**, not the widget.
7. **Ship** (publish it where others can open it), on your `e2-<name>` branch from A.0 — one command per line:
   ```sh
   git add firmware/src/blocks/base host/pwa/panels/base.js docs/students/<name>
   git commit -m "E2: set_avg + adc_v/adc_sd, sd vs N table"
   git push -u origin e2-<name>
   gh pr create --fill
   ```
   Then paste the table, the sentence and a phone screenshot into the pull request description on GitHub.
- ✔ Your phone sets N and shows the mean and its noise live; the three-column table with an explanation is in the pull request.
- *Minimal fallback if flashing keeps failing:* one command that sets the LED colour and one status counter (`press`/`presses`); the tutor writes it. Merge it (bring the branch's changes into the main line) in HW1 and do the measurement version then.
- *Rules:* status keys shown must exist in `status()`; no `delay()` in `loop()`; `esp32s3-sim` is the build environment (env) for a bare dev board — SIM mode, in which the firmware fakes the hardware it does not have.
- **Think ahead:** this is a two-number data logger. What would you log in your lab with it — a photodiode, a temperature, a pressure gauge's analog out — and what would you want the phone to do when the number drifts? Write one line into `PROGRESS.md` under *Next*. That line may become your project.

### A.5 The class board and your block
Page 1 of the schematic (the circuit drawing); one sentence per block; the front panel with its twelve SMA connectors (3 × 4). **Block assignment: volunteers first, then drawn by lot.** Your block page: [B1](blocks/b1.md) · [B2](blocks/b2.md) · [B3](blocks/b3.md) · [B4](blocks/b4.md) · [B5](blocks/b5.md).

### A.6 Homework brief (end of class)
Checkboxes below. Stuck? Work with the tutor; when you want the fix, ask it for the fix; if that does not solve it, email the instructor with a screenshot. The tutor ends the session with your `PROGRESS.md` — class repository (on your `e2-<name>` branch) and your day-1 repository.

---

## Part B — Homework 1 — `/tutor HW1`

- [ ] **E2 finish + merge.** Complete the measurement version if class ran out; merge once it has been reviewed.
- [ ] **E3 Read your block.** Watch V3 when it is online (link on the Preparation page; your block page has everything it shows). Your block page: **the two questions** (short answers that show the why, in `docs/students/<name>/notes.md`) and **the design number** — a calculation with a numeric answer that feeds a real open item in the design (`notes.md`, with the working). The tutor has the expected magnitude, not your answer.
- [ ] **E4 KiCad ready.** Watch V4 when it is online (link on the Preparation page). KiCad (the free program we draw the schematic in and lay out the printed circuit board with) 10; the library (the set of symbols and footprints for our parts) is in the repository (`hardware/lib/`, nothing to unzip); open `hardware/class-board.kicad_pro` → PCB (the physical board design) → your rule area `ZONE_B<N>` (the outlined region of the board that is yours to route) → `docs/students/<name>/zone.png`.
- [ ] **E5 Your SPEC paragraph.** `docs/students/<name>/SPEC.md`: what your block must do; **the number you will measure in the wrap-up, with its expected value and how you will measure it** (your block page names it); how you show it on demo day. Add a second paragraph if you want one: *the extension* — the software or app feature that would make this instrument useful in your lab, and the number that would show it works.
- [ ] Reading: [chapter C](chC-cheat-sheets.md) git and KiCad sections; [chapter A](chA-electronics-from-zero.md) only where you need it.

**Deliverables for Homework 1 (in a repository, by commit or pull request; the date is agreed in class):** your day-1 page URL + `SPEC.md` with predictions vs results + `PROGRESS.md` · merged E2 with the sd-vs-N table · `notes.md` (two answers + the design number) · `zone.png` · `SPEC.md`.

## Beyond the baseline (from today, optional, encouraged)
The hardware is the shared baseline — fixed by budget and timeline, and JLC (JLCPCB, the factory that makes and assembles our boards) builds it. The software, firmware and app are open, and that is where you can show what you can do. Whenever you finish early, the question is: *what problem in your lab could this instrument solve?* Things it could become with the skills from this chapter alone: a **data logger** that writes a CSV file a tool of yours reads · a **LINE / Telegram alert** when a number drifts · **remote access** from the lab WiFi with a **Python script that runs a sweep** overnight · a **calibration routine** stored on the board · a **PID / controller block** (the day-1 PID page made real) · a second board watching something else. Bring a real problem from your lab to L2; the tutor will help you write its `SPEC.md`. Not required; the demo has an optional fifth item for it. Or show the work: a **video that introduces the board**, a page of **tips for working with AI** or with **KiCad**, a **polished web page**, a **game** that teaches something. **Just build something great.** **Talk to your instrument from LINE or Telegram** — the extension we most encourage: push notifications when a value drifts or an alarm fires, and bot commands that read a value or switch a relay from your phone, from anywhere.

---
**Tutor notes (`/tutor L1`, `/tutor HW1`).** Assume competence; offer expert mode. E1a: the student picks the topic and writes `SPEC.md` — a learner outcome, the correctness check — one result you can work out by hand before the code exists, a teaching check — before any code; reject plans that draw a picture instead of computing the physics; the student compares prediction and result and explains any miss; push the stretch (a real teaching check, a second idea, the explainer video) on anyone who finishes early; the reference repositories are for tooling trouble, or by choice from the start. E2: create the branch `e2-<name>` at A.0 — nothing goes on `main`; the student writes the statistics (the block-means loop in `status()`) and the command; the deliverable is the three-column sd-vs-N table (N, measured, predicted from N = 1) with one explanatory sentence; do not supply the explanation — at most one neutral prompt ("what changes when the wire is touched, or when N spans whole mains periods?"); end with "what would you log with this in your lab?" and write the answer under *Next*. E3: the design number needs working and a unit. Never run `pio run -t upload` without naming env and port; *No serial data received* = BOOT+RST once and a new COM port; the port disappearing after every reset is normal (COURSE-GUIDE, *Hardware facts*). Secrets never pass through the tutor (rule 15). Whenever a student finishes early: ask what problem in their lab this could solve, and help them scope it as a `SPEC.md`.
