# Chapter 1 — Day 1 + week 1: build it, ship it, log it — then your instrument

**Fri 2026-09-11, 14:20–16:20 (2 h) + Homework 1 (2.5 h).** Two deliverables today: a page that teaches one idea you know to a high-school student, on the public web, before the break; your own phone app measuring something on your ESP32 by the end.

**What this course is.** Methods and skills for building lab equipment, instruments and tools that get used: specify, build with an agent, verify against a number you predicted, ship, log, review. The class board is the shared baseline — fixed by budget and timeline. The software, firmware and app around it are open: if you see a problem in your own lab that this instrument could solve, that is what you should build. Not required, always encouraged, and the demo has room for it.

**Why the first exercise is a teaching page.** The skill is working with an agent that writes code you did not write: **specify** before it starts, **verify** with a number you predicted, **ship** where others can see it, **log** so the next session can resume. Something whose correct behaviour you can compute by hand is the fair test of that loop — and explaining an idea you know to someone who does not is the fastest way to find out whether the code has it right. You are the author; the agent is the junior engineer. The ESP32 comes second because there the answer is not known in advance.

**The five working practices** (10-minute lecture; the rest of the day is practice):
1. **Spec first** — `SPEC.md`, not chat scrollback; a plan before code.
2. **Teach the repo, not the session** — `CLAUDE.md`: conventions, pinout, build/flash/test commands.
3. **Small, fresh sessions** — one task, one session; finish, commit, start clean.
4. **Handover notes, in Markdown** — `PROGRESS.md`: done / verified / next / gotchas. The lab notebook for this course and what the agent reads first next time.
5. **AI writes, you verify** — a number or an observation, written down, or it does not ship.

*Thesis:* an agent is a junior engineer with no memory — as good as the documentation, the spec and the verification you give it.

---

## Part A — In class

### A.0 Tutor on (14:25, 7 min)
Open Claude Code **in the class repo**, type `/tutor L1`, answer its questions (language; what you have built; `expert` if you want each step's whole recipe instead of pacing). It runs the toolchain check and creates `docs/students/<name>/PROGRESS.md`.
- [ ] `git --version` · `gh auth status` · `pio --version` · board on a port (`pio device list`) · Cloudflare dashboard signed in
- ✔ **toolchain OK**

### A.1 Exercise E1a — build: teach one idea to a high-school student (14:42, 25 min)
**Pick a topic you know** — electromagnetism, electronics, classical mechanics, PID control, anything from your own research — and build, with the agent, the thing that teaches it to a high-school student: an interactive simulation, a game, a page with sliders and a live plot. You choose the idea, you write the spec, you predict the number the page must get right, and you check it. The agent writes the code.

| Topic (examples — yours is better) | What the learner can do afterwards | The check you predict before any code exists |
|---|---|---|
| **RC low-pass filter explorer** — sliders for R and C, live Bode plot | predict the cut-off of any RC pair and what happens to the phase | R = 1 kΩ, C = 100 nF → f_c = 1/(2πRC) = 1591.5 Hz; −3.01 dB and −45.0° there; −20 dB at 10 f_c |
| **PID on a cart or a heater** — three sliders, step response | say what P, I and D each do to overshoot and settling | settling time and overshoot from the closed-loop poles for the gains you set |
| **Field of two charges** — drag the charges, see the lines | superposition | the field at one point on the axis, computed by hand |
| **Cart-pole / pendulum** — push the cart, toggle balance | small oscillations, feedback | period 2π√(L/g) × √(M/(M+m)) (reference repo: pendulum-example) |
| **Two-body orbit** — launch speed slider | Kepler's laws | T² ∝ a³ across three orbits |
| **Standing waves on a string** — frequency slider | resonance, nodes | f_n = n·v/2L |
| *Lab tool instead of a teaching page:* **CSV → scope** — drop a scope CSV, get stats + FFT + sine fit | — | mean, sd = √(A²/2 + σ²), f, amplitude (reference repo: csv-scope-example) |

1. **Repo** (in a terminal *outside* the class repo; pick a short name for your topic):
   ```sh
   gh repo create <your-github-user>/rc-filter --public --clone && cd rc-filter && code .
   ```
2. **`SPEC.md` — you write it, before any code.** Five lines; the two checks are the lines that matter:
   ```markdown
   # rc-filter — SPEC
   - Teaches: why a resistor and a capacitor make a low-pass filter. Afterwards a high-school student can predict the cut-off frequency of any RC pair and say what happens to the phase there.
   - Shows: the circuit; sliders for R (100 Ω–100 kΩ) and C (1 nF–10 µF); a live Bode plot (gain in dB and phase, log frequency axis) with a marker at −3 dB; a sine of chosen frequency in and out, side by side in time.
   - Check (predicted before the code exists): R = 1 kΩ, C = 100 nF → f_c = 1/(2πRC) = 1591.5 Hz; gain −3.01 dB and phase −45.0° at f_c; −20.0 dB at 10·f_c (all within 0.1 dB / 0.5°).
   - Teaching check: three questions at the bottom, answers hidden until tapped; the first is "double C — what happens to f_c?" (halves).
   - One file, index.html, canvas + plain JavaScript, no framework, no build, works on a phone.
   ```
   The tutor will not write code until this file exists. The *Teaches* line is the one most people skip: what should the learner be able to do afterwards that they could not before? The *Check* line is the one you must get right yourself, on paper, first.
3. **Plan, then code.** "Read SPEC.md. Plan in five bullets, then write index.html." Read the plan: does it compute the physics from the parameters, or draw a picture that happens to look right? Reject the picture.
4. **Run and check.** Open `index.html`. Set the parameters from your check line. Read the numbers off the page against your predictions. Write the comparison into `SPEC.md`. If one is off, that is the exercise: which one, by how much, and why (a degrees/radians slip, a log axis drawn linearly, the marker on the wrong curve).
5. **Commit.**
   ```sh
   git add . && git commit -m "rc-filter: spec, interactive Bode plot, checks pass at 1 kΩ / 100 nF"
   ```
- ✔ Page runs; predictions vs results in `SPEC.md`; one commit.
- **Stretch (if you are done at minute 15 — the part worth your time):** make the **teaching check** real — the page asks the learner a question and grades the answer · add a **second idea** that builds on the first (RC → RLC resonance; PID → a disturbance) · or start the **explainer video**: the lab's [show-your-work](https://github.com/iams-yb-lab/show-your-work) `education-video` skill turns your `SPEC.md` and page into a script, narration and picture; post it on a YouTube channel of your own and embed it in the page. Optional today; the recommended route for your 60-second video in the wrap-up.
- **Options (same rules — one output predicted before the code exists):** the **CSV → scope lab tool** (every lab has the problem; reference repo `csv-scope-example`) · the **cart-pole** (reference repo `pendulum-example`). Pick in one minute with the tutor. *Stuck at minute 20 on tooling, not on the problem?* Fork a reference repo (links on the course site) and do the check on it.

### A.2 Exercise E1b — ship + log (15:10, 10 min)
1. `git push -u origin main`
2. Cloudflare → *Workers & Pages → Create → Pages → Connect to Git* → your repo → branch `main` → build command **blank**, output directory `/` → *Save and Deploy* → `https://rc-filter-xxxx.pages.dev` within a minute. *Fallback:* GitHub → *Settings → Pages → Deploy from a branch → main → /*.
3. Open it on your phone; move a slider. Send the link to someone who is not a physicist and ask them the first teaching question.
4. `PROGRESS.md`, four lines, your words:
   ```markdown
   # PROGRESS
   ## 2026-09-11 — session 1 (class)
   - Done: rc-filter teaching page (index.html) from SPEC.md; deployed to https://rc-filter-xxxx.pages.dev
   - Verified: f_c 1591 Hz (pred. 1591.5), −3.0 dB / −45° at f_c, −20.0 dB at 10 f_c; sliders work on my phone
   - Next: the teaching questions grade the answer; RLC resonance as idea two; try the education-video skill
   - Gotchas: Cloudflare output directory must be "/"; first plan drew the Bode curve from a lookup table — rejected
   ```
   Commit, push; watch the redeploy. That is continuous deployment.
- ✔ Public URL works on your phone; `PROGRESS.md` on GitHub. This repo is your course page from now on: the wrap-up video and your measured number go here too.

### A.3 The instrument on your phone (15:25, 10 min)
Your dev board is pre-flashed with the skeleton and is a WiFi access point (LED blue).
1. Phone joins `instrument-XXXX` (label on the board; password `instrument`); open **http://192.168.4.1**. Tap *Red*; the chart plots `base.counter`.
2. The two files a control touches — open them:
   - `firmware/src/blocks/base/BaseBlock.cpp`: `handle()` receives `{"cmd":"led","args":{"r":255,"g":0,"b":0}}`; `status()` fills the numbers the phone sees at 20 Hz.
   - `host/pwa/panels/base.js`: `render()` builds the controls and calls `api.send('base','led',{r,g,b})`; `onStatus(st)` updates the readouts.
   One JSON message phone → board, one reply, twenty status messages a second board → phone. Firmware ↔ WebSocket ↔ phone app ↔ Python (`host/instrument.py` speaks the same messages). Everything runs from `loop()`; nothing may block. Full protocol: `firmware/PROTOCOL.md` — including §6, the streaming and capture frames a tool of yours could one day read.
- ✔ Your phone controls your board.

### A.4 Exercise E2 — your phone app measures something on your ESP32 (15:35, 33 min)
**One command out, one live measurement back — with its noise.** You add one command and two status values to the base block, one control and two readouts to its panel, flash, verify against a prediction, and open a pull request. The tutor writes boilerplate; you write the message name, the handler body, the statistics and the widget.

Default: **an averaged ADC reading and its standard deviation**, averaging length set from the phone — the smallest possible version of a data logger.
1. `firmware/src/blocks/base/BaseBlock.h`, `private:` — a ring buffer and its bookkeeping:
   ```cpp
   static constexpr int ADC_PIN = 4;          // free GPIO on the bare dev board (ADC1_CH3)
   static constexpr int ADC_MAX_N = 1000;
   uint16_t adcBuf_[ADC_MAX_N]; int adcHead_ = 0, adcN_ = 16;
   uint32_t lastSample_ = 0; float adcV_ = 0, adcSd_ = 0;
   ```
2. `BaseBlock.cpp`, `loop()` — sample at 1 kHz, no `delay()`, recompute mean and sd over the last `adcN_`:
   ```cpp
   if (micros() - lastSample_ >= 1000) {
     lastSample_ += 1000;
     adcBuf_[adcHead_] = analogReadMilliVolts(ADC_PIN);
     adcHead_ = (adcHead_ + 1) % ADC_MAX_N;
     double s = 0, s2 = 0;
     for (int i = 0; i < adcN_; i++) { int k = (adcHead_ - 1 - i + ADC_MAX_N) % ADC_MAX_N; s += adcBuf_[k]; s2 += (double)adcBuf_[k] * adcBuf_[k]; }
     double mean = s / adcN_;
     adcV_ = mean / 1000.0f;
     adcSd_ = sqrt(fmax(0.0, s2 / adcN_ - mean * mean)) / 1000.0f;
   }
   ```
3. `handle()`, at the `TODO(E2)` marker — the command:
   ```cpp
   if (strcmp(c, "set_avg") == 0) {                   // {"n": 1..1000}
     int n = a["n"] | adcN_;
     if (n < 1 || n > ADC_MAX_N) { reply["error"] = "n out of range"; return false; }
     adcN_ = n; reply["n"] = adcN_; return true;
   }
   ```
   `status()`: `out["adc_v"] = adcV_; out["adc_sd"] = adcSd_; out["avg_n"] = adcN_;`
4. `host/pwa/panels/base.js`, at the `TODO(E2)` marker — a number input `N` with a *Set* button → `api.send('base','set_avg',{n: Number(...)})`; two readouts for `adc_v` (V, 3 decimals) and `adc_sd` (mV, 2 decimals) filled in `onStatus`.
5. **Flash**: `pio run -e esp32s3-sim -t upload && pio run -e esp32s3-sim -t uploadfs` (no port: hold BOOT, tap RST, release; data cable; *USB* connector).
6. **Verify against a prediction.** GPIO 4 floating or with a jumper wire in it. N = 1, 4, 16, 64, 256; record `adc_sd` each time (chart `base.adc_sd`). White noise predicts sd ∝ 1/√N — a factor 16 from N = 1 to 256. It will not be exactly that. Say what you see and why: a quantisation floor? 50/60 Hz pickup on the wire (correlated noise does not average as 1/√N — try N spanning whole mains periods)? Touch the wire. The five numbers and one explanatory sentence go in the PR description. **That is the deliverable**, not the widget.
7. **Ship**: `git switch -c e2-<name>` → commit → `git push -u origin e2-<name>` → `gh pr create --fill` → paste the numbers and a phone screenshot.
- ✔ Your phone sets N and shows the mean and sd live; five sd values with an explanation in the PR.
- *Minimal fallback if a flash problem eats your time:* one command that sets the LED colour and one status counter (`press`/`presses`, snippet in the base block comments). Merge it in HW1 and do the measurement version then.
- *Rules that bite:* status keys shown must exist in `status()`; no `delay()` in `loop()`; `esp32s3-sim` is the env for a bare dev board.
- **Think ahead:** this is a two-number data logger. What would you log in your lab with it — a photodiode, a temperature, a pressure gauge's analog out — and what would you want the phone to do when the number drifts? Write one line into `PROGRESS.md` under *Next*. That line may become your project.

### A.5 The class board and your block (16:05, 10 min)
Page 1 of the schematic; one sentence per block; the 3 × 4 SMA front panel. **Block assignment: volunteers, then lots.** Your block page: [B1](blocks/b1.md) · [B2](blocks/b2.md) · [B3](blocks/b3.md) · [B4](blocks/b4.md) · [B5](blocks/b5.md).

### A.6 Homework brief (16:15, 5 min)
Checkboxes below; LINE group; office hour Wed 16:00. The tutor ends the session with your `PROGRESS.md` — class repo and your day-1 repo.

---

## Part B — Homework 1 (2.5 h) — `/tutor HW1`

- [ ] **E2 finish + merge (0.5 h).** Complete the measurement version if class ran out; the instructor reviews Mon 09-14; address one comment; merge.
- [ ] **E3 Read your block (0.75 h).** V3 (8 min). Your block page: **the two questions** (short answers that show the why, in `docs/students/<name>/notes.md`) and **the design number** — a 15-minute calculation with a numeric answer that feeds a real open item in the design (`notes.md`, with the working). The tutor has the expected magnitude, not your answer.
- [ ] **E4 KiCad ready (0.5 h).** V4 (8 min). KiCad 10; the library is in the repo (`hardware/lib/`, nothing to unzip); open `hardware/class-board.kicad_pro` → PCB → your rule area `ZONE_B<N>` → `docs/students/<name>/zone.png`.
- [ ] **E5 Your SPEC paragraph (0.25 h).** `docs/students/<name>/SPEC.md`: what your block must do; **the number you will measure in the wrap-up, with its expected value and how you will measure it** (your block page names it); how you show it on demo day. Add a second paragraph if you want one: *the extension* — the software or app feature that would make this instrument useful in your lab, and the number that would show it works.
- [ ] Reading: [chapter C](chC-cheat-sheets.md) git and KiCad sections; [chapter A](chA-electronics-from-zero.md) only where you need it (≈ 0.3 h).

**Deliverables by the end of the week (in a repo, by commit or PR):** your day-1 page URL + `SPEC.md` with predictions vs results + `PROGRESS.md` · merged E2 with the 1/√N numbers · `notes.md` (two answers + the design number) · `zone.png` · `SPEC.md`.

## Beyond the baseline (from today, optional, encouraged)
The hardware is the shared baseline — fixed by budget and timeline, and JLC builds it. The software, firmware and app are open, and that is where you can show what you can do. Whenever you finish early, the question is: *what problem in your lab could this instrument solve?* Things it could become with the skills from this chapter alone: a **data logger** that writes CSV a tool of yours reads (E2 → the Scope tab → export) · a **LINE / Telegram alert** when a number drifts (the alarm engine's `notify` + a 20-line webhook script) · **remote access** from the lab WiFi (`secrets.h`, mDNS) with a **Python script that runs a sweep** overnight · a **calibration routine** stored on the board · a **PID / controller block** (the day-1 PID page made real) · a second node (an S3-CAM watching a gauge). Bring a real problem from your lab to L2; the tutor will help you write its `SPEC.md`. Not required; the demo has an optional fifth item for it.

**Grading.** This part of the course is taught, not ranked: everyone who does the exercises, ships their block and demos it receives full marks. There is no score sheet. The feedback you get is on the work itself, in your pull requests.

---
**Tutor notes (`/tutor L1`, `/tutor HW1`).** Assume competence; offer expert mode. E1a: the student picks the topic and writes `SPEC.md` — a learner outcome, the correctness check with a number predicted on paper, a teaching check — before any code; reject plans that draw a picture instead of computing the physics; the student compares prediction and result and explains any miss; push the stretch (a real teaching check, a second idea, the explainer video) on anyone finished by minute 15; the reference repos are for tooling trouble at minute 20, or by choice at minute 0. Never mention marks. E2: the student writes the statistics and the command; the deliverable is the sd-vs-N table with an explanation; do not supply the explanation — ask what changes when N spans a mains period, when the wire is touched, when the pin is grounded; end with "what would you log with this in your lab?" and write the answer under *Next*. E3: the design number needs working and a unit. Never run `pio run -t upload` without naming env and port. Whenever a student finishes early: ask what problem in their lab this could solve, and help them scope it as a `SPEC.md`.
