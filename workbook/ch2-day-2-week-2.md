# Chapter 2 — Workshop 2: Designing printed circuit boards (Fri 18 Sep) + between workshops

**Fri 18 Sep, 14:20–16:20, Room 311, then between workshops.** Today the ESP32 stops being a dev board on a desk and becomes the core of a real piece of lab equipment. You learn enough electronics to understand what we are building, the six KiCad operations you need (KiCad is the free program we draw the schematic and lay out the printed circuit board in), and then we build the skeleton of our class board together — everyone designs a different section, so that as a team we produce a powerful instrument. **Be creative!**

**Prerequisites:** Projects 1 and 2 from Workshop 1 (your web app is online and your phone controls the ESP32 — keep improving them; they are yours); **KiCad 10 installed and opened once** (the preparation for today); the project `hardware/class-board.kicad_pro` opens (the library is in `hardware/lib/`). Bring your laptop; the schematic PDF is on the course site. Optional background: [chapter A](chA-electronics-from-zero.md) (self-study, before today if you have never seen a schematic).

**What the board is for.** The class board is a small **NMR console**. A pair of coils makes a field of about **2 mT**; the protons in a bottle of water precess in that field at **89 kHz**. The board sends a short pulse at that frequency into a coil, blanks its own receiver while the pulse is on, then listens: the decaying signal that comes back — the **free induction decay** — is mixed down to an audio frequency, sampled by the converter and turned into a **spectrum** on your phone. Everything that makes a hospital scanner work is there except the magnet, and the same console reaches a higher field later by changing only the coil, the amplifier and the drive level. *Rule of thumb: the physics is decided by the coil; the board is decided by noise, timing and what happens when you switch an amp off.*

**The hardware model.** The microcontroller stays on the dev board; the **class board is a carrier** it plugs into: the analog front end done properly, isolation, buffers, robust connectors. One design, one order; **JLCPCB** (the factory that makes and assembles our boards) **assembles everything, SMD and through-hole**. You solder nothing. The dev board alone keeps running your app as the permanent fallback.

**Two boards, one instrument.** The main board is **180 × 100 mm** and 4 layers. The **front panel** is a second board of the same size that sits **flat on the back of it and parallel to it**, joined by three 2×20 pin headers (and four M3 stand-offs) that the instructor solders by hand. The panel's outer face is the face of the instrument: **17 SMA connectors** in a 3 × 6 grid — AO1 AO2 TRIG AUX TX FAST1 / AI1 AI2 AI3 AI4 RX FAST2 / AI5 AI6 AI7 AI8 SPARE — the screw terminals for TTL1–8, the TX coil terminal, a Qwiic connector (the small 4-pin socket that carries the I²C bus to a plug-in sensor), the OLED display and the three LEDs, all pointing up out of it. The back of the instrument is the main board's **rear edge**: USB-C, the 5 V jack, the external 7–18 V input, the coil terminals and the relay and isolated-input terminals, each taking its wire straight off the edge. Everything else — the dev board, the expansion header, the second Qwiic, every solder jumper — is inside, reached with the lid off. *Rule of thumb: what a user touches goes on the panel, what stays plugged in goes on the rear edge, what only you touch stays inside.*

**The deadline.** The final Gerber files (the files a factory makes a board from) go for manufacturing on **Mon 28 Sep, 2 pm — a hard cutoff.** Your section must be merged before it.

---

## Part A — In class

### A.1 Setup check — KiCad running
*Help → About KiCad* shows 10.x; open `hardware/class-board.kicad_pro` and the schematic and the PCB open without a missing-library warning. If not, `/tutor L2` finds the first failure.

### A.2 Introduction — what we are building, and who builds which part
**How much background does everyone have?** — one line each: have you read a schematic, soldered, used a CAD program? The instructor pitches the class on the answers.

The board in 3D on the projector, and the three sections — one each:
- **Section A — inputs and the NMR receiver:** the eight analog inputs and the converter that reads them; then the tuned coil, the low-noise amplifier, the blanking switch, the I/Q mixer, the intermediate-frequency filters and the clock generator. [Page](blocks/a.md).
- **Section B — signal generation, timing and the NMR transmitter:** the two analog outputs; the synthesizer that makes the 89 kHz carrier, its reconstruction filter and the power stage that drives the coil; the TTL buffers, the trigger and the I²C expander. [Page](blocks/b.md).
- **Section C — power and switching:** power entry and the rails, the external power input, the relays and isolated inputs, the H-bridge and the polarizer switch. [Page](blocks/c.md).

The instructor owns the base (the dev-board socket and the buses), the front panel, and the **power-entry sheet** inside Section C — the rails are the one place where a mistake spoils every board, so they are not a student exercise; you read that sheet, you do not edit it.

**Section assignment — volunteers first, then lots.** Say which section you want; what is left is drawn by lot. Write your section into `docs/students/<name>/PROGRESS.md` (the tutor asks). Then meet the neighbour who will review your work (the ring: A→B→C→A).

### A.3 Electronics 101 — a crash course to understand what we are building and how it works
Seven ideas, each pointed at a page of the schematic PDF. [Chapter A](chA-electronics-from-zero.md) has the long version. **Ask your Claude tutor to explain any of them — in Mandarin if you like; the tutor may ask you questions back to check that the idea landed.**
- **(a) Rails, decoupling, ground — Section C.** Every IC gets a 100 nF at its supply pin and a 10 µF per rail per zone; the two grounds (GND for power and logic, AGND for signals) meet at one star point.
- **(b) What ±10 V and 16 bits buy — Sections A and B.** 20 V / 65,536 = 0.3 mV per LSB (the least significant bit, the smallest step the converter can resolve); the rest of the board exists to keep noise below that.
- **(c) The op-amp stage as a black box — Section B.** Gain and offset from two resistor ratios; the 49.9 Ω that protects it from the cable.
- **(d) Isolation — Section C.** A relay's coil and contacts share no copper; an optocoupler's LED and transistor share no copper; creepage is the distance that keeps it so.
- **(e) 3.3 V vs 5 V logic — Section B.** Why a GPIO (a general-purpose pin of the microcontroller) cannot drive TTL, why a buffer can, why "5 V-tolerant" matters.
- **(f) The buses — base.** SPI (three shared wires + one chip-select per device) and I²C (two wires, addresses) tie every section to the dev board; the I²C expander is why eight digital outputs and four relays cost almost no microcontroller pins.
- **(g) The NMR chain end to end — Sections A, B and C together.** Synthesizer → filter → power stage → coil (B) → the sample → tuned coil → low-noise amplifier → blanking → mixer → converter (A), with the switches and the current that feed it (C). A microvolt signal and an amp of drive current live on the same board; almost every rule above exists to keep them apart.

### A.4 Introduction to PCB design with KiCad, automated production and assembly
**The only six operations** (watch, on the projector, in the base sheet): **place** a 100 nF + 10 µF pair and wire it → **annotate** → *Tools → Update PCB from Schematic* → **drag** the two footprints (the copper patterns the parts are soldered onto) next to the pin → **route** three tracks (`X`, click, click) → **DRC** (`Inspect → DRC`; the design rule check — zero errors means it passes), then the **3D view** (`Alt+3`).

**Where parts come from, and who assembles them.** Every part carries an **LCSC** number (LCSC is JLCPCB's parts catalogue); `easyeda2kicad` fetches its symbol, footprint and 3D model into our project library. From the finished design KiCad exports the **Gerbers, the BOM and the CPL** (the manufacturing files, the parts list and the placement list); JLCPCB makes the boards and places and solders every part. Rule of thumb: a part without an LCSC number is a part nobody will solder.

### A.5 Project 3a — Turning our ESP32 into a real piece of lab equipment
We build the skeleton of the class board together; each of you adds one section — the missing parts of your section's schematic, then the copper of your zone (the outlined region of the board that is yours). The instructor's rails, connectors and dev-board socket are already there.

#### 3a.1 (E6) — schematic gaps
- [ ] New branch `<section>-<name>`, for example `a-mei` (VS Code: click the branch name bottom-left → *Create new branch…*; a branch is your own line of work inside the repository — the project folder whose complete history git keeps).
- [ ] Open your gapped sheets. Each one is a small KiCad project of its own in `hardware/student/` — open the `.kicad_pro` that sits next to the sheet, not the main project. **Section A:** `b1_inputs_gapped`, `nmr_rx_gapped` · **Section B:** `b3_outputs_gapped`, `b5_dio_trig_gapped`, `nmr_tx_gapped` · **Section C:** `b4_switching_gapped`, `c_switch_gapped`.
- [ ] Put the full PDF pages for your section next to them. Three or four *items* were deleted from each sheet — a decoupling pair, one repeated channel, one connector — and an item can be several parts. Every reference designator, value and footprint is listed in `hardware/docs/student-deletions.md` and repeated on your section page. For each: `A` (add symbol — a part's drawing in the schematic) → search the **project library** `class_board` (the set of symbols and footprints for our parts) → place → wire (`W`) → set the value (`V`) and check the **footprint field** (`E`) says the right package (0603, SOT-23, …).
- [ ] Keep the reference designators the PDF shows (the footprints on the PCB carry the same names, so the parts you place back are already sitting where the instructor put them).
- [ ] `Inspect → ERC` (the electrical rules check). A gapped sheet is checked on its own, apart from the rest of the board, so the count never reaches zero: every label that leaves the sheet and every supply pin reads as a finding. What must disappear are the dangling ends where your parts were missing — walk them with the tutor, and treat anything else new as yours to fix.
- ✔ *You should see:* your sheet matches the PDF; no dangling end left where a part was missing.
- *Tutor asks:* "which footprint does your 10 µF have and why not 0603?"

#### Break

#### 3a.2 (E7, start) — route your zone
- [ ] Open `hardware/class-board.kicad_pro` and its PCB. Every footprint of the board is already placed, the parts you put back included — the reference designators did not change — so your work here is copper, not placement. If *Update PCB from Schematic* does drop a stray footprint, drag it inside your rule area (`ZONE_A`, `ZONE_B` or `ZONE_C`), decoupling capacitors **next to the pin they serve**.
- [ ] Route (`X`): signals on F.Cu (top), long or crossing ones on B.Cu (bottom) via `V`; **both inner layers are unbroken ground planes and carry no tracks at all** — the design rule check rejects any track you draw there. Track widths come from the net classes (a net is a set of pins that are connected together; a net class sets the rules for a group of them — do not change them).
- [ ] Signals that leave the instrument go to the **front panel**, not to the edge of the board: route them to the link headers the instructor has placed (they are on the bottom side, where the panel plugs in). Only power, relay and coil terminals sit on the rear edge.
- [ ] Run `Inspect → DRC` often. Read every message with the tutor; the two classics are *wrong layer* and *unconnected net*.
- ✔ *You should see:* a good part of the zone routed; DRC shows only unrouted-net items for the rest.

#### 3a.3 — pull request and peer review, live (watch)
The instructor opens a pull request (PR — a request to merge a branch into the shared project; someone reviews it first, comments, and approves) from a student branch, requests the ring reviewer (A reviews B, B reviews C, C reviews A), writes one comment against the checklist, shows *Request changes* vs *Approve*.

### A.6 Firmware/software — making our instrument useful and friendly
The board is the shared baseline; what it *does* is yours. From Workshop 3 you write your section's driver and its phone panel, and the app you built in Project 2 grows into the instrument's front end. **Can you adapt it to solve a problem in your current research?** — a logger for a slow drift, an alarm that reaches your phone, a sweep that runs overnight. Start thinking about it now; the tutor will ask.

### A.7 What must be finished for the cutoff
Read your section page (E3), finish the routing (E7), fetch your one part from the JLCPCB parts library (E8), open your pull request (E9), review your neighbour's (E10) — Part B below. **Gerbers go to the factory Mon 28 Sep, 2 pm — hard cutoff.** Your section must be merged before it. Be creative, stay inside your zone.

---

## Part B — Between workshops: what must be finished for the cutoff — `/tutor HW2`

Before the next workshop: complete the preparation, improve your apps, build and have fun. The preparation this time is what the factory order needs from you before **Mon 28 Sep, 2 pm**; the apps are your Project 1 and Project 2 — improve them whenever you like.

- [ ] **E3 Read your section.** Your section page ([`workbook/blocks/`](blocks/): [A](blocks/a.md), [B](blocks/b.md), [C](blocks/c.md)) asks **two questions** whose answers show the *why* of your circuit, and sets **one design number** to compute (working, a unit, one-line conclusion). Write all three into `docs/students/<name>/notes.md`. Ask the tutor to explain anything in the schematic — in Mandarin if that is faster.
- [ ] **E7 Finish routing.** DRC **0 errors, 0 unrouted**; the ground pour joined (`B` refills zones); a 3D screenshot to `docs/students/<name>/zone-3d.png`. Sections A, B and C all contain repeated channels (eight inputs, eight TTL lines, four relays): route one, copy the pattern.
- [ ] **E8 One part from the JLCPCB parts library.** Your section page names it (Section A: the OPA1656 amplifier, `C1849431` · Section B: the AD9834 synthesizer, `C116589` · Section C: the DRV8871 H-bridge, `C75864`). With your own number in place of the example:
  ```sh
  easyeda2kicad --full --lcsc_id C75864 --output "<absolute path>/hardware/lib/class_board"
  ```
  The symbol lands in `class_board.kicad_sym`, the footprint in `class_board.pretty`, the 3D model in `class_board.3dshapes`. Open the symbol in the schematic editor and check the pin numbering and the footprint against the datasheet; the part is already used in the full design, so the exercise is the library entry, not the placement — say in your pull request what you found. Commit `hardware/lib/`. *Teaches:* where parts come from — the LCSC → JLC pipeline.
- [ ] **E9 Open your pull request.** In VS Code's Source Control panel stage `hardware/` (your sheet, the PCB, the library) → commit → push (upload your commits to GitHub, the website where the repository is stored) → *Create Pull Request* with the 3D screenshot in the description → *Reviewers:* your ring reviewer. CI (continuous integration — the automatic build GitHub runs on every pull request) must be green.
- [ ] **E10 Review your peer, then fix yours.** Open their PR → *Files changed* → check out the branch locally → open the PCB → walk the checklist below → leave **≥ 2 comments** → *Approve* or *Request changes*. Then address the comments on your own PR. *Teaches:* reading someone else's layout; being reviewed.

**The review checklist** (also in [chapter C](chC-cheat-sheets.md); the instructor uses the same list at merge):
ERC 0 / DRC 0 · `LCSC` field on every part · values match the PDF · decoupling next to the pins · no tracks on either inner layer · nothing outside your rule area · pin 1 marked on the silkscreen · ground pour joined · Section C creepage ≥ 2.5 mm at the isolated inputs · high-current traces wide, no neck-downs · a silkscreen label on every connector · CI green.

**Mon 28 Sep, 2 pm (instructor):** paste-merge the three zones (select everything inside `ZONE_A` / `ZONE_B` / `ZONE_C` on your branch → *Paste Special → in place* on `main`, the main branch everyone builds on), full DRC, Gerbers/BOM/CPL, JLC quote with assembly, **order**. The PCB file is never text-merged; schematic sheets are separate files and merge in git.

---
**Tutor notes (`/tutor L2`, `/tutor HW2`).** A.2: record the assigned section (A, B or C) in `PROGRESS.md` before anything else. A.3: explain any of the seven ideas on request, in the student's language, and ask one question back — the per-section question bank is in `tutor/COURSE-GUIDE.md`. E6: the gapped sheets are standalone projects in `hardware/student/` (A: `b1_inputs_gapped`, `nmr_rx_gapped` · B: `b3_outputs_gapped`, `b5_dio_trig_gapped`, `nmr_tx_gapped` · C: `b4_switching_gapped`, `c_switch_gapped`); for every placed part ask for value **and** footprint field; standalone ERC never reaches zero — the dangling ends at the placed-back parts must be gone before moving on. E7: nothing outside the student's rule area (`ZONE_A` / `ZONE_B` / `ZONE_C`), no tracks on either inner layer, do not edit net classes or the instructor's tracks; read each DRC message aloud with the student. E3: check the design number's magnitude against the section page only. E8: `--output` must be an absolute path; then the footprint field. E9: PR description needs the 3D screenshot and the reviewer request. E10: at least two comments, each pointing to a checklist line. The cutoff (Mon 28 Sep, 2 pm) is the gate — say it.
