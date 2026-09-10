# Chapter 3 — Workshop 3: Firmware and basic mechanical design (PCB housing) (Fri 2 Oct) + between workshops

**Fri 2 Oct, 14:20–16:20, Room 311, then between workshops.** The class board is at the factory (ordered Mon 28 Sep; PCBs and housings are collected together, around Fri 16 Oct). Today has two halves: **mechanical** — a tour of what IAMS can fabricate, the CAD basics, and **Project 3b: a housing for our instrument**; and **firmware** — your block's driver (the firmware that talks to its chips) and its phone panel, running in sim mode on your dev board (the firmware fakes its hardware, so your panel works before the class board exists). Your Project 2 app grows into the instrument's front end.

**Prerequisites:** your zone merged (E9/E10 done); dev board and USB-C cable; **Onshape** (the browser CAD program; free education plan, https://www.onshape.com/en/education/) **or another CAD program you already use**, signed in and opened once. Optional background: [chapter B](chB-how-the-software-works.md).

**The deadline.** Housing files for 3D printing and/or laser cutting go to the workshop on **Fri 9 Oct, 2 pm — a hard cutoff.**

---

## Part A — In class

### A.1 Setup check — a CAD program open
Onshape (or your own CAD program) open and signed in; the dev board on a port (`pio device list`). `/tutor L3` finds the first failure.

### A.2 Introduction — where we are
The merged board in 3D; order status; what the presentation and demonstration (chapter 4) will ask of you — you build towards it from today.

### A.3 Mechanical fabrication techniques 101 — tour of the fabrication facilities at IAMS
What each machine makes well, what it cannot, and what it costs you in design effort:
- **FDM 3D printing** (a plastic filament laid down layer by layer) — boxes, brackets, anything with 2 mm walls and no fine detail; cheap and overnight.
- **Resin 3D printing** — fine detail and smooth surfaces; brittle; small parts.
- **Laser cutting** — flat acrylic or wood panels from a 2D drawing; the fastest route to a front panel or a box of slotted plates.
- **Water-jet cutter** — flat metal and thick plates from the same kind of 2D drawing.
- **Lathe and mill** — turned and machined metal parts; ask before you design for them.
Rule of thumb: if it is a box, print it; if it is a plate, cut it; if it must be metal, talk to the workshop first.

### A.4 Mechanical design 101 — CAD basics
In Onshape, on the projector: a **sketch** on a plane → **extrude** it into a solid → **cut** a pocket or a window (extrude *remove*) → a **hole** (the hole tool knows clearance and tapped sizes) → a **thread** (modelled or just a note for a heat-set insert) → a **sheet-metal bend** (for the laser-cut-and-fold case) → **variables** (height, wall) so the design changes in one place. Everything you need for a housing is these six operations.

### A.5 Tips for fabrication
FDM tolerances (holes **+0.3 mm**, slots +0.2), walls **2 mm**, heat-set inserts for M3, layer direction (print the lid flat; no overhangs > 45° without support), why the **PCB front panel** makes the cutouts trivial (a rectangle and four holes), the **STEP export** (STEP is the 3D file format for CAD exchange) from KiCad (*File → Export → STEP*) that the template already contains. For laser cutting: export a **DXF** (the 2D drawing format cutters read) of each plate; kerf (the width the laser burns away) is about 0.2 mm; slots and tabs join plates without glue.

### A.6 Project 3b — Making a housing for our instrument
Use Onshape (or your favourite CAD program) to draw a housing for your instrument, for 3D printing and/or laser cutting. The **template** is the fast path; a design of your own is welcome if it fits the board and meets the deadline.

**E12 — the housing (start today, finish before the cutoff)**
- [ ] Open the instructor's Onshape template (link on the course site) → *Copy workspace* into your account. (Your own CAD: import the board STEP from `hardware/` and start from its outline.)
- [ ] Check the board STEP sits in it; the three parameters (**height, wall, foot style**) are in the *Variables* table.
- [ ] **Make it yours** — a vent pattern, an embossed name, different feet, a laser-cut acrylic lid, a window for the LED, a colour note in the description. What you change is up to you; the tutor asks what and why.
- [ ] Export the files the workshop needs: *Right-click the part → Export → STL* (the 3D file format for printing; binary, mm) for printed parts, DXF for laser-cut plates → save to `docs/students/<name>/housing/`; commit.
- ✔ *You should see:* the files in your folder; a screenshot of the housing in `docs/students/<name>/housing.png`.

### Break

### A.7 Continue building your app, firmware, website and videos
The second half is software. The board is the shared baseline; what it does — the app, the firmware, the website that presents your project, a video — is yours.

**Software architecture (what you are adding to)**
- **A block is one class with five methods** — `name() / begin() / loop() / handle(cmd, reply) / status(out)` in `firmware/src/blocks/b<N>_<name>/`. It talks only to its own hardware; all its code runs from `loop()` (no tasks, no locks, no `delay()`).
- **Three data paths on one WebSocket** (a live two-way connection between the phone page and the board; `firmware/PROTOCOL.md`): JSON (plain-text structured data) command → reply · 20 Hz **status** broadcast (the strip chart, the alarms) · binary **`stream` / `capture`** frames (the Scope tab, §6).
- **One panel module per block** — `host/pwa/panels/b<N>.js`: `render(el, api)` builds the DOM once, `onStatus(st)` runs 20× per second. `api.send(block, cmd, args)` returns a promise; `api.addAlarm(rule)`.
- **`instrument.py` mirrors the same commands** from a PC (the Python client: a program that talks to the board with the same messages as the phone); **`SIM`** fakes the hardware so all of this runs on a bare dev board; the **alarm engine** evaluates rules `{block, key, op, threshold, action}` on the same status; **OTA** (over-the-air) updates over WiFi.

**E11 — driver + panel in sim (start today, finish between workshops)**
`/tutor L3`. Follow the AI method here too: the block page is your specification (commands, status keys, alarm rule); have your plan name what you will see on the phone before any code. The README's *Add a block* section is the recipe.
1. **Copy the template:** `firmware/src/blocks/template/` → `firmware/src/blocks/b<N>_<name>/` (the stub folder already exists — replace its contents). Rename the class and `name()` → `"b<N>"`.
2. **SIM branch first.** In `status()` return plausible fake values for your keys; in `handle()` accept your commands and store the setpoints; in `loop()` make the fake values move (a slow sine, a counter, a drift towards the setpoint). Flash (write the firmware onto the board over USB) `esp32s3-sim`: your tab shows the generic key/value view.
   ✔ *You should see:* your status keys changing on the phone before a line of panel code exists.
3. **Panel.** Copy `host/pwa/panels/template.js` → `panels/b<N>.js`; `id: 'b<N>'`; one control per command, one readout per status key you care about. `pio run -e esp32s3-sim -t uploadfs`; reload the phone.
4. **One alarm rule** from your panel's button: `api.addAlarm({block:'b<N>', key:…, op:…, threshold:…, action:'notify' | 'relay:1:on'})` — your block page names the sensible one. Trigger it in sim (set a setpoint past the threshold) and watch the toast and, if you chose a relay action, B4's `relay1` flip in the Alarms tab.
5. **Explain one round-trip to the tutor before flashing again:** button → `api.send` → JSON over the WebSocket → `handle()` → reply → toast; and status → `status()` → broadcast → `onStatus()`.
6. **Pair up:** B3 ↔ B1 (a sine into an input), B5 ↔ B4 (a TTL line into an opto) — agree the demonstration hand-shake now.
7. Branch (a separate line of work) `b<N>-fw-<name>` → commit (save a snapshot) → push (upload it to GitHub) → pull request (PR — a request to merge your branch into the shared project; someone reviews it first) — all from VS Code's Source Control panel. CI (continuous integration — the automatic build GitHub runs on every pull request) builds both envs.
- ✔ *You should see:* your panel controlling your block in sim; the alarm firing; PR open.

**Website and video.** Every project has its own project website — `index.html` at the root of its repository, on GitHub Pages, as in Project 1 — and its own card on the class project wall (https://tigp-experimental-methods.github.io/showcase-2026/). **Project 3 is one project: one public repository and one project website per student**, presenting your whole instrument — the section of the class board you designed (Project 3a), its firmware driver and app panel, and the housing (Project 3b) — with pictures, renders or a video, what it does, what was measured, and links to your pull requests in `class-board-2026` and to the class repository. The KiCad design files themselves stay in the class repository (`hardware/`, your zone); your personal repository is the presentation of the work, and may hold the housing CAD export, photos and the video. On the wall it is one card with `project` `"3"`. A video that describes your app or board is optional and recommended — script first, pictures last; the lab's `show-your-work` skills do the production.

---

## Part B — Between workshops: what must be finished for the cutoff — `/tutor HW3`

Before the next workshop: complete the preparation, improve your apps, build and have fun. The preparation this time: the first item is what the workshop needs from you before **Fri 9 Oct, 2 pm**; the second is what the instrument needs before the boards arrive.

- [ ] **E12 Housing files — Fri 9 Oct, 2 pm, hard cutoff.** Finish making it yours; STL and/or DXF in `docs/students/<name>/housing/`, the screenshot next to them; commit and push. The workshop prints and cuts everything together.
- [ ] **E11 Driver + panel PR.** All your commands; **one status value plotted** (pick it in the chart dropdown, screenshot); **the alarm rule**; CI green; PR reviewed by your ring reviewer (the classmate who reviews your pull request; comment only, no second fix round). Fill the `#ifndef SIM` branches as far as you can from the datasheet with `TODO` where you must measure first — pins only from `firmware/include/pins.h`.
- **Keep building** your apps, project websites and video towards the presentation (chapter 4) — whenever you like.

## Beyond the baseline (optional, encouraged)
The driver you just wrote is the baseline. From here the instrument becomes whatever your lab needs: a **data logger** that writes CSV (Scope tab → export, or `instrument.py stream --csv` on a schedule) · a **LINE / Telegram alert** from your alarm rule (`notify` → a short webhook script) · **remote access** from the lab WiFi + a **Python sweep** overnight · a **calibration routine** stored on the board · a **PID / controller block** that closes a loop between an input and an output · a **second node** (an S3-CAM watching a gauge). Write its plan with one verifiable number, build it on a branch, and show it in your presentation. Or show the work: a **video that introduces the board**, a page of **tips for working with AI** or with **KiCad**, a **polished project website**, a **game** that teaches something. **Talk to your instrument from LINE or Telegram** — the extension we most encourage: push notifications when a value drifts or an alarm fires, and bot commands that read a value or switch a relay from your phone, from anywhere. **Can you adapt the instrument to solve a problem in your current research?**

---
**Tutor notes (`/tutor L3`, `/tutor HW3`).** A.1: a CAD program open is the setup check. E12: the template is the fast path; ask what the student changed and why; STL/DXF to their folder; say the cutoff (Fri 9 Oct, 2 pm). E11: SIM branch first; the student names the commands and types the SIM values; every status key shown in the panel must exist in `status()`; no `delay()` in `loop()`; make them explain one round-trip before the second flash; the alarm rule must be theirs. Pairings B3↔B1, B5↔B4: write the agreed hand-shake into both `PROGRESS.md` files.
