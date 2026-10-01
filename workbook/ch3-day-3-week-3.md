# Chapter 3 — Workshop 3: Firmware and basic mechanical design (PCB housing) (Fri 2 Oct) + between workshops

**Fri 2 Oct, 14:20–16:20, Room 311, then between workshops.** The class board is at the factory (ordered Mon 28 Sep; PCBs and housings are collected together, around Fri 16 Oct). Today has two halves: **mechanical** — what you can get made and where, the rules that make printed and cut parts work, how to read an OpenSCAD file, and **Project 3b: a housing for our instrument**; and **firmware** — your section's driver (the firmware that talks to its chips) and its phone panel, running in sim mode on your dev board (the firmware fakes its hardware, so your panel works before the class board exists). Your Project 2 app grows into the instrument's front end.

**The CAD route.** Nobody learns a CAD program (computer-aided design: the program a part is drawn in) today. Claude Code writes the geometry; you specify, look, check the numbers, slice and decide. The geometry is written in **OpenSCAD 2021.01** (the free program in which a part is a short text file of shapes: the AI writes it, you read it and change the numbers) and prepared for the printer in **Bambu Studio** (the slicer: the program that turns a 3D model into the layers and paths the printer follows). A design in another CAD program you already use is welcome too, if it fits the boards and meets the deadline.

**Prerequisites:** your zone merged (E9/E10 done); dev board and USB-C cable; **OpenSCAD and Bambu Studio installed and opened once** ([SETUP.md](../SETUP.md) Step 11); the class repository up to date (Source Control → *Sync Changes*). Optional background: [chapter B](chB-how-the-software-works.md).

**The deadline.** Housing files for 3D printing and/or laser cutting go to the workshop on **Fri 9 Oct, 2 pm — a hard cutoff.**

---

## Part A — In class

### A.1 Setup check — OpenSCAD and Bambu Studio open
OpenSCAD (*Help → About* shows 2021.01) and Bambu Studio open; the class repository up to date, so `hardware/release/` holds `class-board.stl`, `front-panel.stl` and `housing.scad`; the dev board on a port (`pio device list`). `/tutor L3` finds the first failure.

### A.2 Introduction — where we are
The merged board in 3D; order status; what the presentation and demonstration (chapter 4) will ask of you — you build towards it from today.

### A.3 Mechanical fabrication techniques 101 — make it, ask the workshop, order it
Three ways to a part. IAMS has a CO₂ laser cutter for plastics, FDM printers (Bambu Lab P1S), Phrozen resin printers, a water-jet cutter, manual lathes, a drill press, a bandsaw, a mill and an NC 3-axis mill.
- **You, this week.** **FDM 3D printing** (fused deposition modelling: melted plastic laid down one layer at a time) on the P1S — boxes and brackets with 2 mm walls, up to a 256 mm cube, a few dollars overnight. **Resin printing** on the Phrozen printers — 25–50 µm detail, smooth, small, brittle; the part is washed and cured. **Laser cutting** — acrylic 2–10 mm from a DXF drawing; panels, lids, boxes of slotted plates. **Hand tools at your bench** — a hand drill opens a printed hole to size, a tap cuts an M3 thread (2.5 mm hole), files and a hacksaw for the small corrections. You use the hand tools, not the drill press or the bandsaw.
- **The IAMS workshop.** The lathe (anything round), the mill and the NC 3-axis mill (flat faces, pockets, slots), the water-jet (metal, glass or stone 1–100 mm, too thick or too hard for the laser): the serious work, done by the people who work there. Bring a file or a drawing and talk to them first.
- **External services, where most work goes.** CNC machining, laser-cut and bent sheet metal from JLCCNC, resin, nylon and metal printing from JLC3DP: upload a STEP file, choose the material, get a price at once; one to two weeks to Taiwan.

Rule of thumb: if it is a box, print it; if it is a plate, cut it; if it must be metal, talk to the workshop first.

### A.4 Reading OpenSCAD
You will not write OpenSCAD from scratch; you will read what Claude wrote, find the number you want to change and find the cut you distrust. The whole language is three families — shapes, moves and combinations; everything else is a convenience. Seven ideas cover the housing:

1. **Shapes, moved, combined.** Shapes: `cube`, `cylinder`, `sphere`; `square`, `circle`, `text`. Moves: `translate`, `rotate`, `mirror`, `scale`. Combinations: `union`, `difference`, `intersection`. A statement is the moves in front, the shape, a semicolon; save the file and the preview redraws.
   ```openscad
   cube([190, 110, 40]);
   translate([95, 55, 40])
     cylinder(d = 20, h = 30, $fn = 48);
   ```
2. **Extrude: a 2D sketch pulled up.** A 2D shape plus a height is a solid. `offset(r)` rounds the corners (the mill radius, drawn in). Read it inside out: the sketch first, then the extrusion.
   ```openscad
   linear_extrude(height = 40)
     offset(r = 3) offset(delta = -3)
       square([190, 110]);
   ```
3. **Cut: `difference()` keeps the first shape and removes the rest** — what the mill does. The pocket is a cube moved in by the wall thickness; let a cut overshoot the face so it cuts cleanly.
   ```openscad
   difference() {
     cube([190, 110, 40]);
     translate([2, 2, 2]) cube([186, 106, 40]);
   }
   ```
4. **Revolve: `rotate_extrude()` spins a half-profile** around the z axis — anything the lathe makes: stand-offs, knobs, bushings. The profile must stay at x ≥ 0.
   ```openscad
   rotate_extrude($fn = 64)
     polygon([[1.6, 0], [5, 0], [5, 1.5],
              [3, 1.5], [3, 11], [1.6, 11]]);
   ```
5. **Holes: a cylinder subtracted, repeated with `for()`.** One line writes a whole grid of holes. Every hole gets **+0.3 mm** (printed holes come out small, A.5). A circle is a polygon: `$fn` sets its number of sides, and too few sides make the hole small.
   ```openscad
   for (x = [75.65 : 18 : 165.65], y = [25.67, 43.67])
     translate([x, y, -1])
       cylinder(d = 6.5 + 0.3, h = 5, $fn = 48);
   ```
6. **What the language lacks, and what we do instead.** No threads: a hexagonal **nut pocket**, and the thread is a note. No fillets on 3D edges: `hull()` of cylinders, or `offset()` in the sketch. Lettering: `text()` extruded 0.6 mm. No STEP: STL for the printer, and a DXF for the laser from `projection(cut = true)`. The BOSL2 library adds rounded boxes, screw holes and real threads, for later.
   ```openscad
   cylinder(d = 5.8 / cos(30), h = 2.5, $fn = 6);
   hull() for (x = [3, 37], y = [3, 27])
     translate([x, y]) cylinder(r = 3, h = 10);
   linear_extrude(0.6) text("TIGP", size = 8);
   ```
7. **Variables, modules and the Customizer: one file becomes a template.** Variables sit at the top; a comment after one becomes a slider or a drop-down in the **Customizer** (*Window → Customizer*: the panel that changes the variables without touching the code). A `module` is a named part. The **part switch** at the bottom chooses what is drawn. `%` shows a shape transparent and never printed (the boards); `#` highlights one in red. `echo()` prints the numbers you would otherwise measure.
   ```openscad
   wall = 2;     // [1.6:0.2:3]
   part = "all"; // [all, base, cover, cover2d, coupon, section]
   %import("class-board.stl");
   if (part == "cover") cover();
   echo("wall", wall);
   ```

**Out of OpenSCAD.** F5 previews; **F6** renders the exact geometry, and only a rendered model can be exported: *File → Export → Export as STL* (or 3MF, a print format that also carries colours and settings), one part at a time — set `part` in the Customizer, F6, export. A plate for the laser leaves as a 2D drawing: the `cover2d` part is `projection(cut = true)` through the cover; F6, then *File → Export → Export as DXF*. Three console messages account for most of what goes wrong — read the console before asking the AI, and paste the line to it when you do:
- `Can't open import file` — the path to a board mesh is wrong relative to your `.scad` file; the board is simply missing from the preview.
- `Current top level object is empty` — nothing was drawn: usually the `part` variable matched none of the `if` lines.
- `Ignoring unknown variable` — a misspelt name; the shape that used it silently vanishes.

### A.5 Tips for fabrication
- **Fastening: a nut in a pocket is the printed thread** — the class standard. An M3 nut is 5.5 mm across flats, so the pocket is 5.8 mm across flats and 2.5 mm deep, open to the side so the nut slides in; the screw pulls it tight. The alternative is a **heat-set insert** (a brass thread melted in with a soldering iron; 4.0 mm hole for M3). Never print a thread below about M8.
- **Tolerances.** Holes **+0.3 mm**, slots +0.2; a sliding fit needs a 0.2–0.3 mm gap, a press fit 0.05–0.1 mm of interference. Print a **test coupon** first: it answers the fit for your printer.
- **Layers are the weak direction** — about half the strength across them; orient the load along the layers and print flat when you can.
- **Overhangs.** 45° prints on air, steeper needs support; re-orient, split the part, use a chamfer instead of a fillet at the bed. Faces that touch the bed are flat.
- **The numbers.** Walls **2 mm**, infill 15–25 %, layers 0.2 mm (0.1 for looks); strength comes from the walls, not the infill.
- **Materials.** **PLA** by default (stiff, easy, soft at 60 °C) · **PETG** tougher, 80 °C · **ASA/ABS** ~100 °C and UV-stable, in an enclosed printer (the P1S is) · TPU for rubber parts · PA-CF (carbon-filled nylon) for strong ones.
- **The PCB front panel** makes the cutouts simple: it *is* the face of the instrument, so the front of the box is a plate with holes where the panel's parts are.
- **Laser cutting.** One **DXF** (the 2D drawing format cutters read) per plate; kerf (the width the laser burns away) about 0.2 mm; slots a little tight, tabs a little loose, and slots and tabs join plates without glue.

### A.6 Project 3b — Making a housing for our instrument
We build the housing together, one step at a time, on the shared screen: you in your own Claude Code session with OpenSCAD open beside it. A design of your own, or one in another CAD program you already use, is welcome if it fits the boards and meets the deadline.

**What the housing has to hold.** Two boards, 180 × 100 mm each, stacked 11 mm apart on four M3 × 11 stand-offs — one sandwich. The instrument lies flat: the **front panel faces up** and is the face of the instrument (the SMA connectors, the screw terminals, the OLED and the LEDs come through it); the main board is under it, and the dev board hangs below the main board. Over the panel lies a **printed front cover**: a flat plate whose underside is 14 mm above the panel face, resting on the OLED module so the module cannot work loose, with cut-outs for the 16 SMA connectors, the OLED window, the three LEDs, the Qwiic socket, the module header and the four screw terminals on the panel's far edge (the TTL strip, the TX terminal, the two isolated inputs), and solid plastic over everything else, so the solder tails and header pins are covered and nothing conductive can touch them. The panel's screw terminals take their wires from the side. The **back** is the main board's rear edge — USB-C, the DC jack, the external supply and the coil terminals — which come through openings in the rear wall, with room for the wires. The cover is fastened with M3 screws into **nuts in pockets** in the base. Every dimension comes from the board models, none from a ruler, and the housing has to open, because the dev board's RESET and BOOT buttons are inside.

**The guided build — eight steps after the preparation**
0. **Where the board models come from** (preparation, shown once). The meshes `hardware/release/class-board.stl` and `front-panel.stl` (STL: the 3D file format for printing, a surface of triangles) were made from the KiCad files before the workshop with one command, keeping only the parts the housing touches — the connectors, the LEDs and the OLED: `kicad-cli pcb export stl --subst-models --define-var TIGP_BOARD_LIB=<path> --component-filter "J*,D*" -o class-board.stl hardware/class-board.kicad_pcb`. You can re-run it with the tutor; it needs the `TIGP_BOARD_LIB` path variable of SETUP Step 9.
1. **Specify.** Copy the [housing specification card](housing-spec-card.md) into your Claude Code prompt and change at least its *Make it yours* line. It ends with *"Ask me your questions before writing any code."*
2. **Answer** Claude's questions.
3. **Generate.** Claude writes `housing.scad` in your folder; open it in OpenSCAD with *Design → Automatic Reload and Preview* on, so every save redraws it. ✔ *You should see:* the base, the cover and the two transparent boards; the console shows the echoed numbers.
4. **Look.** Rotate it; set `part` to `section` in the Customizer to cut the model in half; the boards are drawn transparent with `%`. Find one thing wrong (there is usually one: a cutout off by a connector pitch, a wall through a connector) and say it to Claude in a sentence.
5. **Check the numbers** in the console against the card: the wall, every hole size, the clearance to the boards, the nut pocket, the outer size against the 256 mm of the P1S.
6. **Fix and iterate.** The sentence from step 4 becomes a change; save; the preview reloads. Then **make it yours** — a vent pattern, an embossed name, feet, a window, an acrylic lid instead of the printed cover.
7. **Export and slice.** Set `part` to each of `base`, `cover`, `coupon` in turn, F6, *File → Export → Export as STL*; set `cover2d`, F6, *Export as DXF*. In Bambu Studio: import, the base flat on the plate open side up, the cover face down; look at the supports preview (many supports means turn the part or change the design); slice and read the print time and the grams.
8. **Coupon and files.** Put the test coupon on the plate (holes 3.0–3.6 mm, an M3 nut pocket, a wall of your thickness); save a screenshot; commit from Source Control.

**E12 — the housing (start today, finish before the cutoff)**
- [ ] Copy the [specification card](housing-spec-card.md) and change what you want changed.
- [ ] Paste it into Claude Code (your folder is `docs/students/<name>/housing/`); answer its questions.
- [ ] Claude writes `housing.scad` in `docs/students/<name>/housing/`; open it in OpenSCAD.
- [ ] Look and check: the section view, the echoed numbers against the card.
- [ ] **Make it yours** — what you change is up to you; the tutor asks what and why.
- [ ] Export `base.stl`, `cover.stl`, `coupon.stl` and `cover.dxf`; slice the base and the cover in Bambu Studio.
- [ ] Save a screenshot of the housing as `housing.png` in the same folder.
- [ ] Commit from Source Control.
- **If your own run stalls:** copy `hardware/release/housing.scad` (the instructor's reference file, made from the same card) into your folder, change its two `import("...")` lines to the paths on the card (`../../../../hardware/release/class-board.stl` and `front-panel.stl`; otherwise the console says `Can't open import file`), and change its numbers in the Customizer.
- ✔ *You should see:* the preview with both boards inside the housing and no warning in the console; `housing.scad`, the three STL files, `cover.dxf` and `housing.png` in `docs/students/<name>/housing/`.

### Break

### A.7 Continue building your app, firmware, website and videos
The second half is software. The board is the shared baseline; what it does — the app, the firmware, the website that presents your project, a video — is yours.

**Software architecture (what you are adding to)**
- **A driver is one class with five methods** — `name() / begin() / loop() / handle(cmd, reply) / status(out)` in `firmware/src/blocks/<id>/` (the firmware calls each driver a *block*, and your section owns the blocks for its own hardware: Section A `b1_inputs` and the receiver capture · Section B `b3_outputs` and `b5_dio_trig` · Section C `b4_switching`, the module outputs and the isolated inputs). A driver talks only to its own hardware; all its code runs from `loop()` (no tasks, no locks, no `delay()`).
- **Three data paths on one WebSocket** (a live two-way connection between the phone page and the board; `firmware/PROTOCOL.md`): JSON (plain-text structured data) command → reply · 20 Hz **status** broadcast (the strip chart, the alarms) · binary **`stream` / `capture`** frames (the Scope tab, §6).
- **One panel module per driver** — `host/pwa/panels/<id>.js`: `render(el, api)` builds the DOM once, `onStatus(st)` runs 20× per second. `api.send(block, cmd, args)` returns a promise; `api.addAlarm(rule)`.
- **`instrument.py` mirrors the same commands** from a PC (the Python client: a program that talks to the board with the same messages as the phone); **`SIM`** fakes the hardware so all of this runs on a bare dev board; the **alarm engine** evaluates rules `{block, key, op, threshold, action}` on the same status; **OTA** (over-the-air) updates over WiFi.

**E11 — driver + panel in sim (start today, finish between workshops)**
`/tutor L3`. Follow the AI method here too: your section page is your specification (commands, status keys, alarm rule); have your plan name what you will see on the phone before any code. The README's *Add a driver* section is the recipe.
1. **Copy the template:** `firmware/src/blocks/template/` → your section's driver folder (the stub folders already exist — replace their contents). Rename the class and `name()` to match the folder.
2. **SIM branch first.** In `status()` return plausible fake values for your keys; in `handle()` accept your commands and store the setpoints; in `loop()` make the fake values move (a slow sine, a counter, a drift towards the setpoint). Flash (write the firmware onto the board over USB) `esp32s3-sim`: your tab shows the generic key/value view.
   ✔ *You should see:* your status keys changing on the phone before a line of panel code exists.
3. **Panel.** Copy `host/pwa/panels/template.js` → `panels/<id>.js`, with `id` matching your driver; one control per command, one readout per status key you care about. `pio run -e esp32s3-sim -t uploadfs`; reload the phone.
4. **One alarm rule** from your panel's button: `api.addAlarm({block:'<id>', key:…, op:…, threshold:…, action:'notify' | 'module:1:on'})` — your section page names the sensible one. Trigger it in sim (set a setpoint past the threshold) and watch the toast and, if you chose a module-output action, Section C's `module1` flip in the Alarms tab.
5. **Explain one round-trip to the tutor before flashing again:** button → `api.send` → JSON over the WebSocket → `handle()` → reply → toast; and status → `status()` → broadcast → `onStatus()`.
6. **Pair up:** Section B ↔ Section A (a sine into an input, and later the transmit pulse into the receiver), Section B ↔ Section C (a TTL line into an optocoupler) — agree the demonstration hand-shake now.
7. Branch (a separate line of work) `<section>-fw-<name>` → commit (save a snapshot) → push (upload it to GitHub) → pull request (PR — a request to merge your branch into the shared project; someone reviews it first) — all from VS Code's Source Control panel. CI (continuous integration — the automatic build GitHub runs on every pull request) builds both envs.
- ✔ *You should see:* your panel controlling your section in sim; the alarm firing; PR open.

**Website and video.** Every project has its own project website — `index.html` at the root of its repository, on GitHub Pages, as in Project 1 — and its own card on the class project wall (https://tigp-experimental-methods.github.io/showcase-2026/). **Project 3 is one project: one public repository and one project website per student**, presenting your whole instrument — the section of the class board you designed (Project 3a), its firmware driver and app panel, and the housing (Project 3b) — with pictures, renders or a video, what it does, what was measured, and links to your pull requests in `class-board-2026` and to the class repository. The KiCad design files themselves stay in the class repository (`hardware/`, your zone); your personal repository is the presentation of the work, and may hold the housing CAD export, photos and the video. On the wall it is one card with `project` `"3"`. A video that describes your app or board is optional and recommended — script first, pictures last; the lab's `show-your-work` skills do the production.

---

## Part B — Between workshops: what must be finished for the cutoff — `/tutor HW3`

Before the next workshop: complete the preparation, improve your apps, build and have fun. The preparation this time: the first item is what the workshop needs from you before **Fri 9 Oct, 2 pm**; the second is what the instrument needs before the boards arrive.

- [ ] **E12 Housing files — Fri 9 Oct, 2 pm, hard cutoff.** Finish making it yours; `housing.scad`, the STL of each part (`base.stl`, `cover.stl`, `coupon.stl`), `cover.dxf` and the screenshot `housing.png` in `docs/students/<name>/housing/`; commit and push. The workshop prints and cuts everything together.
- [ ] **E11 Driver + panel PR.** All your commands; **one status value plotted** (pick it in the chart dropdown, screenshot); **the alarm rule**; CI green; PR reviewed by your ring reviewer (the classmate who reviews your pull request; comment only, no second fix round). Fill the `#ifndef SIM` branches as far as you can from the datasheet with `TODO` where you must measure first — pins only from `firmware/include/pins.h`.
- **Keep building** your apps, project websites and video towards the presentation (chapter 4) — whenever you like.

## Beyond the baseline (optional, encouraged)
The driver you just wrote is the baseline. From here the instrument becomes whatever your lab needs: a **data logger** that writes CSV (Scope tab → export, or `instrument.py stream --csv` on a schedule) · a **LINE / Telegram alert** from your alarm rule (`notify` → a short webhook script) · **remote access** from the lab WiFi + a **Python sweep** overnight · a **calibration routine** stored on the board · a **PID / controller block** that closes a loop between an input and an output · a **second node** (an S3-CAM watching a gauge). Write its plan with one verifiable number, build it on a branch, and show it in your presentation. Or show the work: a **video that introduces the board**, a page of **tips for working with AI** or with **KiCad**, a **polished project website**, a **game** that teaches something. **Talk to your instrument from LINE or Telegram** — the extension we most encourage: push notifications when a value drifts or an alarm fires, and bot commands that read a value or switch a module output from your phone, from anywhere. **Can you adapt the instrument to solve a problem in your current research?**

---
**Tutor notes (`/tutor L3`, `/tutor HW3`).** A.1: OpenSCAD 2021.01 and Bambu Studio open is the setup check. E12: the eight steps of A.6, starting from the specification card (`workbook/housing-spec-card.md`); edits only in `docs/students/<name>/housing/`; if the student's run stalls, the fallback is a copy of `hardware/release/housing.scad` with its two import paths changed to the card's; ask what the student changed and why; `housing.scad`, STL per part, DXF and PNG in that folder; say the cutoff (Fri 9 Oct, 2 pm). E11: SIM branch first; the student names the commands and types the SIM values; every status key shown in the panel must exist in `status()`; no `delay()` in `loop()`; make them explain one round-trip before the second flash; the alarm rule must be theirs. Pairings B↔A and B↔C: write the agreed hand-shake into both `PROGRESS.md` files.
