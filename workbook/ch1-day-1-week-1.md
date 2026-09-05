# Chapter 1 — Day 1 + week 1: build it, ship it, log it — then your instrument

**Fri 2026-09-11, 14:20–16:20 (2 h) + Homework 1 (2.5 h).** Two promises for today: a physics simulator on the public web before the break; your own phone app talking to your ESP32 by the end.

**Why we start away from the project.** AI-assisted work is a general skill. The same three moves serve a simulation, a website, a video, a report, a KiCad board and a firmware driver: **build** from a written spec, **ship** where others can see it, **log** what you did in plain text. Today you do the three moves twice — once on a pendulum, once on the ESP32 in your hand.

**The five working practices** (the 10-minute lecture; everything else today practises them):
1. **Spec first** — requirements live in a file, `SPEC.md`, not in chat scrollback; ask for a plan before code.
2. **Teach the repo, not the session** — `CLAUDE.md` holds conventions, pinout, build/flash commands, how to test.
3. **Small, fresh sessions** — one task, one session; finish, commit, start clean.
4. **Handover notes, in Markdown** — `PROGRESS.md` at the end of every session: done / verified / next / gotchas. It is your lab notebook for this course and the first thing the AI reads next time.
5. **AI writes, you verify** — no verification plan, no ship. "Verify" means a number or an observation.

*The thesis in one sentence:* an AI agent is a junior engineer with no memory — exactly as good as the documentation, the spec and the verification you give it.

---

## Part A — In class

### A.0 Tutor on (14:25, 7 min)
Open Claude Code **in the class repo** and type `/tutor L1`. Answer its two questions (language; what you have built before). It runs the toolchain check and writes your first `docs/students/<name>/PROGRESS.md`.
- [ ] `git --version` · `gh auth status` · `pio --version` · the board shows up on a port (`pio device list`) · Cloudflare dashboard signed in
- ✔ *You should see:* the tutor's line **toolchain OK**.

### A.1 Exercise E1a — build: the inverted pendulum (14:42, 25 min)
Your own repo, your own spec, one HTML file, a physics check.

1. **Make the repo** (in a terminal *outside* the class repo, e.g. `Documents/tigp`):
   ```sh
   gh repo create <your-github-user>/pendulum --public --clone
   cd pendulum
   code .           # open it in a new VS Code window; start Claude Code there
   ```
2. **Write `SPEC.md` yourself** — five lines, before any code. Template:
   ```markdown
   # Pendulum on a cart — SPEC
   - Shows: a cart on a rail with a pole hinged on it; gravity real; the pole can hang or balance.
   - Controls: push the cart left/right (← → keys and touch on the left/right half of the screen); a toggle "balance" that turns a simple controller on/off.
   - Parameters at the top of the file: L = 1.0 m, m = 0.2 kg, g = 9.81 m/s²; drawn to scale, time real.
   - Check: with balance OFF and the pole hanging, the small-swing period equals 2π√(L/g) = 2.006 s within 5 %.
   - One file, index.html, canvas + plain JavaScript, no framework, no build, works on a phone.
   ```
   The tutor will not write code until this file exists.
3. **Ask for a plan, then the file.** "Read SPEC.md. Propose a plan in five bullets. Then write index.html." Read the plan; if it skips the check, say so.
4. **Run it:** double-click `index.html` (or *Open with Live Server*). Push the cart. Let the pole fall and swing.
5. **The check, with a stopwatch:** time ten full swings of the hanging pole at small amplitude. Divide by ten. Compare with 2.006 s. Write the measured number into `SPEC.md` under the check line: `Measured: 2.0 s (10 swings in 20.1 s) — pass.` If it fails, that is a real finding: ask the tutor why (usually the time step or a wrong length scale) and fix it.
6. **Commit:**
   ```sh
   git add . && git commit -m "Pendulum simulator: spec, first working version, period check passes"
   ```
- ✔ *You should see:* the pendulum swinging in your browser; the measured period in `SPEC.md`; one commit.
- *Stretch:* change L to 0.5 m and confirm the period drops by √2. *Stuck at minute 20?* Fork the instructor's reference repo (link on the course site) and continue from there — the check still has to be done by you.
- *Alternatives (same rules, one checkable number):* bouncing ball (coefficient of restitution from successive heights) · two-body orbit (Kepler's third law) · Pong (the ball speed you specified). Choose in one minute with the tutor.

### A.2 Exercise E1b — ship + log (15:10, 10 min)
1. **Push:** `git push -u origin main`.
2. **Deploy:** Cloudflare dashboard → *Workers & Pages → Create → Pages → Connect to Git* → pick `pendulum` → production branch `main` → build command **blank**, build output directory `/` → *Save and Deploy*. About a minute later you get `https://pendulum-xxxx.pages.dev`.
   *Fallback if Cloudflare refuses:* on GitHub, repo *Settings → Pages → Deploy from a branch → main → / (root)* → `https://<user>.github.io/pendulum/`.
3. **Open the URL on your phone.** Touch the left and right halves of the screen: the cart moves.
4. **Log it — you type, the tutor asks the four questions:** create `PROGRESS.md`:
   ```markdown
   # PROGRESS

   ## 2026-09-11 — session 1 (class)
   - Done: pendulum simulator (index.html) from SPEC.md; deployed to https://pendulum-xxxx.pages.dev
   - Verified: small-swing period 2.0 s vs 2.006 s expected (10 swings); touch controls work on my phone
   - Next: add a period readout on screen; try L = 0.5 m
   - Gotchas: Cloudflare needs the build directory "/" not empty; index.html must be in the repo root
   ```
   Commit and push. Watch the Cloudflare deployment list: it rebuilds by itself. That is continuous deployment; you just did it.
- ✔ *You should see:* the pendulum on your phone from a public URL; `PROGRESS.md` visible on GitHub.

### A.3 The instrument on your phone (15:25, 10 min)
Your dev board is already flashed with the skeleton and is a WiFi access point.
1. Power it from your laptop. Its RGB LED is **blue** = access point mode.
2. On your phone join WiFi `instrument-XXXX` (the XXXX is printed on the board's label; password `instrument`).
3. Open **http://192.168.4.1**. Tap *Red* on the Base tab: the LED changes. The chart plots `base.counter`.
4. Look at **the two files a control touches**, open them in VS Code:
   - `firmware/src/blocks/base/BaseBlock.cpp` — `handle()` receives `{"cmd":"led","args":{"r":255,"g":0,"b":0}}` and sets the LED; `status()` fills the numbers the phone sees 20× per second.
   - `host/pwa/panels/base.js` — `render()` builds the buttons and calls `api.send('base','led',{r,g,b})`; `onStatus(st)` updates the numbers.
   One JSON message goes phone → board over a WebSocket; one reply comes back; twenty status messages a second flow board → phone. That is the whole software shape: **firmware ↔ WebSocket ↔ phone app ↔ Python** (`host/instrument.py` speaks the same messages from a PC).
- ✔ *You should see:* your phone controlling your board's LED and the chart moving.

### A.4 Exercise E2 — your phone app talks to your ESP32 (15:35, 33 min)
**One button out, one live number back.** You add one command and one status value to the base block and one button and one readout to its panel, flash it, and open a pull request. The tutor writes boilerplate; **you edit the message name, the handler body and the widget label.**

Default recipe — a *Press me* button that flashes the LED a colour of your choice and counts presses:
1. **Firmware state** — `firmware/src/blocks/base/BaseBlock.h`, inside `private:` add `uint32_t presses_ = 0;`
2. **Firmware command** — `BaseBlock.cpp`, in `handle()` next to the `TODO(E2)` marker:
   ```cpp
   if (strcmp(c, "press") == 0) {          // {"r":..,"g":..,"b":..} optional
     presses_++;
     setLed(a["r"] | 255, a["g"] | 120, a["b"] | 0);
     reply["presses"] = presses_;
     return true;
   }
   ```
3. **Firmware status** — in `status()` add `out["presses"] = presses_;`
4. **Panel** — `host/pwa/panels/base.js`: in `render()` at the `TODO(E2)` marker add
   ```html
   <div class="row"><button class="btn primary" id="press">Press me</button>
        <label>presses</label><span class="value" id="presses">-</span></div>
   ```
   then `els.presses = el.querySelector('#presses');` and
   `el.querySelector('#press').onclick = () => api.send('base', 'press', { r: 255, g: 120, b: 0 });`
   and in `onStatus(st)` add `els.presses.textContent = st.presses ?? '-';`
5. **Flash** (board on the *USB* port, data cable):
   ```sh
   cd firmware
   pio run -e esp32s3-sim -t upload && pio run -e esp32s3-sim -t uploadfs
   ```
   If no port is found: hold **BOOT**, tap **RST**, release **BOOT**, retry. Still nothing: driver, port, cable — then raise a hand.
6. **Verify on the phone:** rejoin `instrument-XXXX`, reload http://192.168.4.1, press the button. LED changes colour, the number climbs. Pick `base.presses` in the chart dropdown: it steps.
7. **Ship it:**
   ```sh
   git switch -c e2-<name>
   git add -A && git commit -m "E2: press button + presses counter (base)"
   git push -u origin e2-<name>
   gh pr create --fill        # add a phone screenshot to the PR description on GitHub
   ```
- ✔ *You should see:* your app on your phone driving your board and showing a live number from it; the PR open with a screenshot. **Nobody leaves without this** — the instructor pairs up anyone stuck at minute 25.
- *Other buttons:* blink pattern (toggle a flag; `loop()` does the timing — never `delay()`), a GPIO high/low on a free pin (4, 5, 6, 7 are free on the bare dev board), brightness step. *Other numbers:* `touchRead(4)` with a jumper wire in GPIO 4 — touch the wire and watch the number; an `analogRead` on GPIO 4; `WiFi.RSSI()` of a client.
- *Rules that bite:* status keys you show must exist in `status()`; no `delay()` in `loop()`; the SIM env is the right one for a bare dev board.

### A.5 The class board and your block (16:05, 10 min)
The instructor shows page 1 of the schematic (block diagram), one sentence per block, and the 3 × 4 SMA front panel. **Block assignment: volunteers first, then lots.** The tutor writes your block into `PROGRESS.md` and opens your block page: [B1](blocks/b1.md) · [B2](blocks/b2.md) · [B3](blocks/b3.md) · [B4](blocks/b4.md) · [B5](blocks/b5.md).

### A.6 Homework brief (16:15, 5 min)
Five checkboxes below; LINE group; office hour Wed 16:00 (the flashing safety net). The tutor ends the session by updating your `PROGRESS.md` — in the class repo **and** in your pendulum repo.

---

## Part B — Homework 1 (2.5 h) — `/tutor HW1`

- [ ] **E2 finish + merge (0.5 h).** Finish the app if it did not fully work in class (Wed office hour for flashing problems). The instructor reviews PRs Mon 09-14; address one comment and merge (*Squash and merge* is fine). *Teaches:* the PR loop.
- [ ] **E3 Read your block (0.5 h).** Watch V3 *Our schematic in 8 minutes* (8 min). Open your block page; the tutor asks its two questions; write your answers in `docs/students/<name>/notes.md` (three sentences each is plenty). *Teaches:* schematic reading.
- [ ] **E4 KiCad ready (0.5 h).** Watch V4 (8 min). Install KiCad 10 (https://www.kicad.org/download/). Unzip the library package (link on the course site, from Mon 09-15) into `hardware/lib/`. Open `hardware/class-board.kicad_pro`, open the PCB, find the rule area `ZONE_B<N>` with your name on it, screenshot it into `docs/students/<name>/zone.png`. *Teaches:* KiCad orientation.
- [ ] **E5 Your SPEC paragraph (0.5 h).** `docs/students/<name>/SPEC.md`: one paragraph — what your block must do, **one number** (the one you will measure in the wrap-up, see your block page), and how you will show it on demo day. Same shape as the pendulum spec, one level up. *Teaches:* spec first.
- [ ] Reading: the rest of this chapter and [chapter C](chC-cheat-sheets.md) git section (≈ 0.3 h). Every work session ends with a `PROGRESS.md` entry and a commit — pendulum repo and class repo alike.

**Assessed at the end of the week:** pendulum URL + its `PROGRESS.md` (from class) · merged E2 · `notes.md` answers · `zone.png` · `SPEC.md` — all in a repo, all by commit or PR.

---
**Tutor notes (`/tutor L1`, `/tutor HW1`).** Order A.0 → A.6; time-box each step and offer the shortcut at 150 % of its budget (E1a: the reference repo; E2: the exact snippet above). E1a: **no code before `SPEC.md` exists**; the student types the parameters, does the timing, writes the measured number. E1b: the student types the four log lines. E2: generate boilerplate from the `press` example, but the student edits the command name, the handler body and the widget label; before commit ask *"what do you see on the phone?"*. Never run `pio run -t upload` without telling the student which port and env. HW1: E3 questions come from the block page; accept short answers that show the *why*; E5 must contain a number.
