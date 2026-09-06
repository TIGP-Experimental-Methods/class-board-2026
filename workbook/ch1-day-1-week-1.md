# Chapter 1 — Day 1 + week 1: build it, ship it, log it — then your instrument

**Fri 2026-09-11, 14:20–16:20 (2 h) + Homework 1 (2.5 h).** Two deliverables today: a small tool your lab could use tomorrow, on the public web, before the break; your own phone app measuring something on your ESP32 by the end.

**What this course is.** Methods and skills for building lab equipment, instruments and tools that get used: specify, build with an agent, verify against a number you predicted, ship, log, review. The class board is the shared baseline — fixed by budget and timeline. The software, firmware and app around it are open: if you see a problem in your own lab that this instrument could solve, that is what you should build. Not required, always encouraged, and the demo has room for it.

**Why the first exercise is a stand-alone tool.** The skill is working with an agent that writes code you did not write: **specify** before it starts, **verify** with a number you predicted, **ship** where others can see it, **log** so the next session can resume. A tool whose correct output you can compute by hand is the fair test of that loop. The ESP32 comes second because there the answer is not known in advance.

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

### A.1 Exercise E1a — build: a lab tool with a check you can compute by hand (14:42, 25 min)
Default: **a CSV → scope tool.** Drop a CSV exported from an oscilloscope, a DAQ or our instrument's Scope tab; get the trace plotted, mean, standard deviation, the dominant frequency from an FFT and the amplitude from a least-squares sine fit. Every lab has this problem; almost none has the tool.

1. **Repo** (in a terminal *outside* the class repo):
   ```sh
   gh repo create <your-github-user>/csv-scope --public --clone && cd csv-scope && code .
   ```
2. **`SPEC.md` — you write it, before any code.** Five lines; the check is the one that matters:
   ```markdown
   # csv-scope — SPEC
   - Input: a CSV with a header row and columns time (s), voltage (V) — Rigol/Keysight style; if only one column, ask for the sample rate. Drag-and-drop or a file button.
   - Output: the trace on a canvas (zoomable by drag); mean, standard deviation, min, max; the dominant frequency (FFT peak, interpolated) and the amplitude and offset of a least-squares sine fit at that frequency.
   - Test file: make_test.py writes test.csv — 1.000 s at 100 kS/s, a 1000.0 Hz sine of amplitude 2.000 V, offset 0.500 V, Gaussian noise 0.050 V rms, seed fixed.
   - Check (predicted before the code exists): mean 0.500 V; sd = √(A²/2 + σ²) = 1.4151 V; frequency 1000.0 Hz within 0.1 %; amplitude 2.000 V within 0.5 %.
   - One file, index.html, canvas + plain JavaScript, no framework, no build, works on a phone; make_test.py is the only other file.
   ```
   The tutor will not write code until this file exists. The sd prediction is the one to get right: the rms of a sine is A/√2 and independent noise adds in quadrature.
3. **Plan, then code.** "Read SPEC.md. Plan in five bullets, then write make_test.py and index.html." Reject a plan that reads the amplitude off the FFT bin height (spectral leakage makes that wrong by up to a third) — the fit is the method.
4. **Run and check.** `uv run --with numpy make_test.py`, open `index.html`, drop `test.csv`. Four numbers on screen against your four predictions. Write the comparison into `SPEC.md`. If one is off, that is the exercise: which one, by how much, and why (window leakage, a truncated FFT length, the offset not fitted).
5. **Commit.**
   ```sh
   git add . && git commit -m "csv-scope: spec, test generator, plot + stats + FFT + sine fit; all four checks pass"
   ```
- ✔ Tool runs; predictions vs results in `SPEC.md`; one commit.
- **Stretch (if you are done at minute 15 — the part worth your time):** bring a **real CSV from your own lab** (scope, lock-in, DAQ) and make the tool read its header; or add an **exponential-decay fit with uncertainties** for ring-downs and lifetimes; or export the FFT as CSV. Whatever you add, write its check first.
- **Alternatives (same rules — one output predicted by hand before the code exists):** an RC / op-amp **filter designer** with a Bode plot (check: f_c and the −45° point) · a **photon or SNR budget calculator** for your own experiment (check: your hand calculation) · a **cart-pole simulation or a game** (check: the period with the recoil factor √(M/(M+m)); reference repo on the course site). Pick in one minute with the tutor. *Stuck at minute 20 on tooling, not on the problem?* Fork the reference repo (course site) and do the check on it.

### A.2 Exercise E1b — ship + log (15:10, 10 min)
1. `git push -u origin main`
2. Cloudflare → *Workers & Pages → Create → Pages → Connect to Git* → `csv-scope` → branch `main` → build command **blank**, output directory `/` → *Save and Deploy* → `https://csv-scope-xxxx.pages.dev` within a minute. *Fallback:* GitHub → *Settings → Pages → Deploy from a branch → main → /*.
3. Open it on your phone; drop or pick `test.csv` from your phone's files (send it to yourself once) — the tool works where your instruments are.
4. `PROGRESS.md`, four lines, your words:
   ```markdown
   # PROGRESS
   ## 2026-09-11 — session 1 (class)
   - Done: csv-scope (index.html, make_test.py) from SPEC.md; deployed to https://csv-scope-xxxx.pages.dev
   - Verified: mean 0.500, sd 1.4152 (pred. 1.4151), f 1000.0 Hz, amp 2.001 V (pred. 2.000) on test.csv; runs on my phone
   - Next: read our Rigol's CSV header (two preamble lines); exponential fit for the cavity ring-down
   - Gotchas: Cloudflare output directory must be "/"; the first plan used the FFT bin height for amplitude — rejected
   ```
   Commit, push; watch the redeploy. That is continuous deployment.
- ✔ Public URL works on your phone; `PROGRESS.md` on GitHub.

### A.3 The instrument on your phone (15:25, 10 min)
Your dev board is pre-flashed with the skeleton and is a WiFi access point (LED blue).
1. Phone joins `instrument-XXXX` (label on the board; password `instrument`); open **http://192.168.4.1**. Tap *Red*; the chart plots `base.counter`.
2. The two files a control touches — open them:
   - `firmware/src/blocks/base/BaseBlock.cpp`: `handle()` receives `{"cmd":"led","args":{"r":255,"g":0,"b":0}}`; `status()` fills the numbers the phone sees at 20 Hz.
   - `host/pwa/panels/base.js`: `render()` builds the controls and calls `api.send('base','led',{r,g,b})`; `onStatus(st)` updates the readouts.
   One JSON message phone → board, one reply, twenty status messages a second board → phone. Firmware ↔ WebSocket ↔ phone app ↔ Python (`host/instrument.py` speaks the same messages). Everything runs from `loop()`; nothing may block. Full protocol: `firmware/PROTOCOL.md` — including §6, the streaming and capture frames your csv-scope tool will one day read.
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
Checkboxes below; LINE group; office hour Wed 16:00. The tutor ends the session with your `PROGRESS.md` — class repo and csv-scope repo.

---

## Part B — Homework 1 (2.5 h) — `/tutor HW1`

- [ ] **E2 finish + merge (0.5 h).** Complete the measurement version if class ran out; the instructor reviews Mon 09-14; address one comment; merge.
- [ ] **E3 Read your block (0.75 h).** V3 (8 min). Your block page: **the two questions** (short answers that show the why, in `docs/students/<name>/notes.md`) and **the design number** — a 15-minute calculation with a numeric answer that feeds a real open item in the design (`notes.md`, with the working). The tutor has the expected magnitude, not your answer.
- [ ] **E4 KiCad ready (0.5 h).** V4 (8 min). KiCad 10; the library is in the repo (`hardware/lib/`, nothing to unzip); open `hardware/class-board.kicad_pro` → PCB → your rule area `ZONE_B<N>` → `docs/students/<name>/zone.png`.
- [ ] **E5 Your SPEC paragraph (0.25 h).** `docs/students/<name>/SPEC.md`: what your block must do; **the number you will measure in the wrap-up, with its expected value and how you will measure it** (your block page names it); how you show it on demo day. Add a second paragraph if you want one: *the extension* — the software or app feature that would make this instrument useful in your lab, and the number that would show it works.
- [ ] Reading: [chapter C](chC-cheat-sheets.md) git and KiCad sections; [chapter A](chA-electronics-from-zero.md) only where you need it (≈ 0.3 h).

**Assessed:** csv-scope URL + `SPEC.md` with predictions vs results + `PROGRESS.md` · merged E2 with the 1/√N numbers · `notes.md` (two answers + the design number) · `zone.png` · `SPEC.md`.

## Beyond the baseline (from today, optional, encouraged)
The hardware is fixed. The software is not. Things this instrument could become with the skills from this chapter alone: a **data logger** that writes CSV your csv-scope tool reads (E2 → the Scope tab → export) · a **LINE / Telegram alert** when a number drifts (the alarm engine's `notify` + a 20-line webhook script) · **remote access** from the lab WiFi (`secrets.h`, mDNS) with a **Python script that runs a sweep** overnight · a **calibration routine** stored on the board · a second node (an S3-CAM watching a gauge). Bring a real problem from your lab to L2; the tutor will help you write its `SPEC.md`. See the workbook README's *Beyond the baseline* list and the L3 "what else" segment.

---
**Tutor notes (`/tutor L1`, `/tutor HW1`).** Assume competence; offer expert mode. E1a: no code before `SPEC.md`; the student derives the four predictions (sd in quadrature), runs the test, explains any miss; reject the FFT-bin-height amplitude plan; push the stretch (their own instrument's CSV, or a fit with uncertainties) on anyone finished by minute 15. E2: the student writes the statistics and the command; the deliverable is the sd-vs-N table with an explanation; do not supply the explanation — ask what changes when N spans a mains period, when the wire is touched, when the pin is grounded; end with "what would you log with this in your lab?" and write the answer under *Next*. E3: the design number needs working and a unit. Never run `pio run -t upload` without naming env and port. Whenever a student finishes early: ask what problem in their lab this could solve, and help them scope it as a `SPEC.md`.
