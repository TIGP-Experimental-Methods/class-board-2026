# Chapter 3 — Day 3 + week 3: Firmware and Mechanical 101 — make it work, make it yours

**Fri 2026-10-02, 14:20–16:20 + Homework 3.** The board is on order (placed 09-28, back ≈ 10-12); **everything today runs in sim mode on your dev board**. You write your block's driver and its phone panel — the E2 app grown into a real block panel — and design your box from the instructor's template.

**Prerequisites:** your zone merged (E9/E10 done); dev board; Onshape account (free education plan, https://www.onshape.com/en/education/). Optional background: [chapter B](chB-how-the-software-works.md).

---

## Part A — In class

### A.1 Where we are
The merged board in 3D; order status; the **demo checklist** (chapter 4) — you build towards it from today.

### A.2 Software architecture
- **A block is one class with five methods** — `name() / begin() / loop() / handle(cmd, reply) / status(out)` in `firmware/src/blocks/b<N>_<name>/`. It talks only to its own hardware; all its code runs from `loop()` (no tasks, no locks, no `delay()`).
- **Three data paths on one WebSocket** (`firmware/PROTOCOL.md`): JSON command → reply · 20 Hz **status** broadcast (the strip chart, the alarms) · binary **`stream` / `capture`** frames (the Scope tab, §6).
- **One panel module per block** — `host/pwa/panels/b<N>.js`: `render(el, api)` builds the DOM once, `onStatus(st)` runs 20× per second. `api.send(block, cmd, args)` returns a promise; `api.addAlarm(rule)`.
- **`instrument.py` mirrors the same commands** from a PC; **`SIM`** fakes the hardware so all of this runs on a bare dev board; the **alarm engine** evaluates rules `{block, key, op, threshold, action}` on the same status; **OTA** updates over WiFi.

### A.3 Exercise E11 — driver + panel in sim (finished in HW3)
`/tutor L3`. The README's *Add a block* section is the recipe; your block page lists your commands, status keys and alarm rule.
1. **Copy the template:** `firmware/src/blocks/template/` → `firmware/src/blocks/b<N>_<name>/` (the stub folder already exists — replace its contents). Rename the class and `name()` → `"b<N>"`.
2. **SIM branch first.** In `status()` return plausible fake values for your keys; in `handle()` accept your commands and store the setpoints; in `loop()` make the fake values move (a slow sine, a counter, a drift towards the setpoint). Flash `esp32s3-sim`: your tab shows the generic key/value view.
   ✔ *You should see:* your status keys changing on the phone before a line of panel code exists.
3. **Panel.** Copy `host/pwa/panels/template.js` → `panels/b<N>.js`; `id: 'b<N>'`; one control per command, one readout per status key you care about. `pio run -e esp32s3-sim -t uploadfs`; reload the phone.
4. **One alarm rule** from your panel's button: `api.addAlarm({block:'b<N>', key:…, op:…, threshold:…, action:'notify' | 'relay:1:on'})` — your block page names the sensible one. Trigger it in sim (set a setpoint past the threshold) and watch the toast and, if you chose a relay action, B4's `relay1` flip in the Alarms tab.
5. **Explain one round-trip to the tutor before flashing again:** button → `api.send` → JSON over the WebSocket → `handle()` → reply → toast; and status → `status()` → broadcast → `onStatus()`.
6. **Pair up:** B3 ↔ B1 (a sine into an input), B5 ↔ B4 (a TTL line into an opto) — agree the demo hand-shake now.
7. Branch `b<N>-fw-<name>` → commit → push → PR (CI builds both envs).
- ✔ *You should see:* your panel controlling your block in sim; the alarm firing; PR open.

### A.4 Break

### A.5 Boxes for electronics
FDM tolerances (holes **+0.3 mm**, slots +0.2), walls **2 mm**, heat-set inserts for M3, layer direction (print the lid flat; no overhangs > 45° without support), why the **PCB front panel** makes the cutouts trivial (a rectangle and four holes), the **STEP export** from KiCad (*File → Export → STEP*) that the template already contains. The laser cutter is the alternative for flat acrylic panels; not used for the box.

### A.6 Exercise E12 (start) — your box
- [ ] Open the instructor's Onshape template (link on the course site) → *Copy workspace* into your account.
- [ ] Check the board STEP sits in it; the three parameters (**height, wall, foot style**) are in the *Variables* table.
- [ ] Change **one thing** that makes it yours: a vent pattern, an embossed name, different feet, a colour note in the description. One. The tutor will hold you to it.
- [ ] *Right-click the part → Export → STL* (binary, mm) → save to `docs/students/<name>/box.stl`; commit.
- ✔ *You should see:* the STL in your folder; a screenshot of the box in `docs/students/<name>/box.png`.

### A.7 Tips and what else
Bot alerts from the alarm engine (LINE / Telegram webhook from a PC script); **the Scope tab on a real signal and `instrument capture` into NumPy**; scripted sweeps with `instrument.py`; your 60-second video and demo slides with the lab's `show-your-work` skills (2-minute live demo); OTA; where to take this — your own lab's instrument.

---

## Part B — Homework 3 — `/tutor HW3`

- [ ] **E11 Driver + panel PR by Fri 10-09.** All your commands; **one status value plotted** (pick it in the chart dropdown, screenshot); **the alarm rule**; CI green; PR reviewed by your ring reviewer (comment only, no second fix round). Watch V6 *A block driver + app panel, end to end, in sim mode* first. Fill the `#ifndef SIM` branches as far as you can from the datasheet with `TODO` where you must measure first — pins only from `firmware/include/pins.h`.
- [ ] **E12 Box STL.** Finish the one change; `box.stl` in your folder; the instructor prints all five the following week.
- [ ] Watch V7 *The box: template to STL to Bambu*; read this chapter.

**Deliverables (by commit or PR):** the merged driver + panel PR (block works in sim, alarm rule present, one value plotted) · `box.stl`.

## Beyond the baseline (optional, encouraged)
The driver you just wrote is the baseline. From here the instrument becomes whatever your lab needs: a **data logger** that writes CSV (Scope tab → export, or `instrument.py stream --csv` on a schedule) · a **LINE / Telegram alert** from your alarm rule (`notify` → a 20-line webhook script) · **remote access** from the lab WiFi + a **Python sweep** overnight · a **calibration routine** stored on the board · a **PID / controller block** that closes a loop between an input and an output · a **second node** (an S3-CAM watching a gauge). Write its `SPEC.md` with one verifiable number, build it on a branch, and bring it to the demo as the optional fifth item.

---
**Tutor notes (`/tutor L3`, `/tutor HW3`).** E11: SIM branch first; the student names the commands and types the SIM values; every status key shown in the panel must exist in `status()`; no `delay()` in `loop()`; make them explain one round-trip before the second flash; the alarm rule must be theirs. E12: exactly one change; STL to their folder. Pairings B3↔B1, B5↔B4: write the agreed hand-shake into both `PROGRESS.md` files.
