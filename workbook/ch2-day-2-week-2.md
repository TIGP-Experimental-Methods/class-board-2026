# Chapter 2 — Workshop 2: Designing printed circuit boards (Fri 18 Sep) + homework 2

**Fri 18 Sep, 14:20–16:20, Room 311, then homework 2.** Today the ESP32 stops being a dev board on a desk and becomes the core of a real piece of lab equipment. You learn enough electronics to understand what we are building, the six KiCad operations you need (KiCad is the free program we draw the schematic and lay out the printed circuit board in), and then we build the skeleton of our class board together — everyone designs a different section, so that as a team we produce a powerful instrument. **Be creative!**

**Prerequisites:** homework 1 done (Projects 1 and 2 — your web app is online and your phone controls the ESP32); **KiCad 10 installed and opened once**; the project `hardware/class-board.kicad_pro` opens (the library is in `hardware/lib/`). Bring your laptop; the schematic PDF is on the course site. Optional background: [chapter A](chA-electronics-from-zero.md) (self-study, before today if you have never seen a schematic).

**The hardware model.** The microcontroller stays on the dev board; the **class board is a carrier** it plugs into: the analog front end done properly, isolation, buffers, robust connectors. One design, five units, one order; **JLCPCB** (the factory that makes and assembles our boards) **assembles everything, SMD and through-hole**. You solder nothing. The dev board alone keeps running your app as the permanent fallback.

**The deadline.** The final Gerber files (the files a factory makes a board from) go for manufacturing on **Mon 28 Sep, 2 pm — a hard cutoff.** Your section must be merged before it.

---

## Part A — In class

### A.1 Setup check — KiCad running
Open `hardware/class-board.kicad_pro`; the schematic and the PCB open without a missing-library warning. If not, `/tutor L2` finds the first failure.

### A.2 Introduction — what we are building, and who builds which part
**How much background does everyone have?** — one line each: have you read a schematic, soldered, used a CAD program? The instructor pitches the next hour on the answers.

The board in 3D on the projector; the five blocks: **B1** precision inputs · **B2** power and rails · **B3** outputs · **B4** switching (relays, optocouplers) · **B5** digital I/O and trigger. Each block has a page in [`workbook/blocks/`](blocks/).

**Block assignment — volunteers first, then lots.** Say which block you want; what is left is drawn by lot. Write your block into `docs/students/<name>/PROGRESS.md` (the tutor asks). Then meet the neighbour who will review your work (the ring: A→B→C→D→E→A).

### A.3 Electronics 101 — a crash course to understand what we are building and how it works
Six ideas, each pointed at a page of the schematic PDF. [Chapter A](chA-electronics-from-zero.md) has the long version. **Ask your Claude tutor to explain any of them — in Mandarin if you like; the tutor may ask you questions back to check that the idea landed.**
- **(a) Rails, decoupling, ground — B2.** Every IC gets a 100 nF at its supply pin and a 10 µF per rail per zone; the two grounds (GND for power and logic, AGND for signals) meet at one star point.
- **(b) What ±10 V and 16 bits buy — B1/B3.** 20 V / 65,536 = 0.3 mV per LSB (the least significant bit, the smallest step the converter can resolve); the rest of the board exists to keep noise below that.
- **(c) The op-amp stage as a black box — B3.** Gain and offset from two resistor ratios; the 49.9 Ω that protects it from the cable.
- **(d) Isolation — B4.** A relay's coil and contacts share no copper; an optocoupler's LED and transistor share no copper; creepage is the distance that keeps it so.
- **(e) 3.3 V vs 5 V logic — B5.** Why a GPIO (a general-purpose pin of the microcontroller) cannot drive TTL, why a buffer can, why "5 V-tolerant" matters.
- **(f) The buses — base.** SPI (three shared wires + one chip-select per device) and I²C (two wires, addresses) tie every block to the dev board.

### A.4 Introduction to PCB design with KiCad, automated production and assembly
**The only six operations** (watch, on the projector, in the base sheet): **place** a 100 nF + 10 µF pair and wire it → **annotate** → *Tools → Update PCB from Schematic* → **drag** the two footprints (the copper patterns the parts are soldered onto) next to the pin → **route** three tracks (`X`, click, click) → **DRC** (`Inspect → DRC`; the design rule check — zero errors means it passes), then the **3D view** (`Alt+3`).

**Where parts come from, and who assembles them.** Every part carries an **LCSC** number (LCSC is JLCPCB's parts catalogue); `easyeda2kicad` fetches its symbol, footprint and 3D model into our project library. From the finished design KiCad exports the **Gerbers, the BOM and the CPL** (the manufacturing files, the parts list and the placement list); JLCPCB makes the boards and places and solders every part. Rule of thumb: a part without an LCSC number is a part nobody will solder.

### A.5 Project 3a — Turning our ESP32 into a real piece of lab equipment
We build the skeleton of the class board together; each of you adds one section — the missing parts of your block's schematic, then the copper of your zone (the outlined region of the board that is yours). The instructor's rails, connectors and dev-board socket are already there.

#### 3a.1 (E6) — schematic gaps
- [ ] `git switch -c b<N>-<name>` (a new branch: your own line of work inside the repository — the project folder whose complete history git keeps); open `hardware/class-board.kicad_pro`; open your sheet `student/b<N>_gapped.kicad_sch`.
- [ ] Put the full PDF page for your block next to it. Your block page lists the 3–4 parts that were deleted. For each: `A` (add symbol — a part's drawing in the schematic) → search the **project library** `class_board` (the set of symbols and footprints for our parts) → place → wire (`W`) → set the value (`V`) and check the **footprint field** (`E`) says the right package (0603, SOT-89, …).
- [ ] Keep the reference designators the PDF shows (the footprints on the PCB carry the same names, so *Update PCB* drops the parts exactly where the instructor placed them).
- [ ] `Inspect → ERC` (the electrical rules check) → **0 errors** (warnings about power flags you may ignore only if the tutor agrees).
- ✔ *You should see:* your sheet matches the PDF; ERC 0.
- *Tutor asks:* "which footprint does your 10 µF have and why not 0603?"

#### Break

#### 3a.2 (E7, start) — route your zone
- [ ] Open the PCB; *Update PCB from Schematic*; the new footprints appear near your zone — drag them inside `ZONE_B<N>`, decoupling capacitors **next to the pin they serve**.
- [ ] Route (`X`): signals on F.Cu (top), long or crossing ones on B.Cu (bottom) via `V`; **nothing on In1.Cu (layer 2 is GND)**, power on In2.Cu only if the instructor's rails are there already. Track widths come from the net classes (a net is a set of pins that are connected together; a net class sets the rules for a group of them — do not change them).
- [ ] Run `Inspect → DRC` often. Read every message with the tutor; the two classics are *wrong layer* and *unconnected net*.
- ✔ *You should see:* a good part of the zone routed; DRC shows only unrouted-net items for the rest.

#### 3a.3 — pull request and peer review, live (watch)
The instructor opens a pull request (PR — a request to merge a branch into the shared project; someone reviews it first, comments, and approves) from a student branch, requests the ring reviewer (A reviews B, B reviews C, …, E reviews A), writes one comment against the checklist, shows *Request changes* vs *Approve*.

### A.6 Firmware/software — making our instrument useful and friendly
The board is the shared baseline; what it *does* is yours. From Workshop 3 you write your block's driver and its phone panel, and the app you built in Project 2 grows into the instrument's front end. **Can you adapt it to solve a problem in your current research?** — a logger for a slow drift, an alarm that reaches your phone, a sweep that runs overnight. Start thinking about it now; the tutor will ask.

### A.7 Homework brief
Read your block page (E3), finish the routing (E7), fetch your LCSC part (E8), open your pull request (E9), review your neighbour's (E10) — Part B below. **Gerbers go to the factory Mon 28 Sep, 2 pm — hard cutoff.** Be creative, stay inside your zone.

---

## Part B — Homework 2 — `/tutor HW2`

- [ ] **E3 Read your block.** Your block page ([`workbook/blocks/b<N>.md`](blocks/)) asks **two questions** whose answers show the *why* of your circuit, and sets **one design number** to compute (working, a unit, one-line conclusion). Write all three into `docs/students/<name>/notes.md`. Ask the tutor to explain anything in the schematic — in Mandarin if that is faster.
- [ ] **E7 Finish routing.** DRC **0 errors, 0 unrouted**; the ground pour joined (`B` refills zones); a 3D screenshot to `docs/students/<name>/zone-3d.png`. B1/B4/B5 owners have replicated channels: route one, copy the pattern.
- [ ] **E8 One part from LCSC.** Your block page names it (e.g. B4: the relay, C12072). In the repository root:
  ```sh
  easyeda2kicad --full --lcsc_id C12072 --output "<absolute path>/hardware/lib/class_board"
  ```
  The symbol lands in `class_board.kicad_sym`, the footprint in `class_board.pretty`, the 3D model in `class_board.3dshapes`. Open the symbol in the schematic editor, check pin 1 against the datasheet, and swap it into your sheet in place of the instructor's copy (or add it as the second footprint alternative). Commit `hardware/lib/`. *Teaches:* where parts come from — the LCSC → JLC pipeline.
- [ ] **E9 Open your pull request.** In VS Code's Source Control panel stage `hardware/` (your sheet, the PCB, the library) → commit → push (upload your commits to GitHub, the website where the repository is stored) → *Create Pull Request* (or `gh pr create`) with the 3D screenshot in the description → *Reviewers:* your ring reviewer. CI (continuous integration — the automatic build GitHub runs on every pull request) must be green.
- [ ] **E10 Review your peer, then fix yours.** Open their PR → *Files changed* → check out the branch locally → open the PCB → walk the checklist below → leave **≥ 2 comments** → *Approve* or *Request changes*. Then address the comments on your own PR. *Teaches:* reading someone else's layout; being reviewed.

**The review checklist** (also in [chapter C](chC-cheat-sheets.md); the instructor uses the same list at merge):
ERC 0 / DRC 0 · `LCSC` field on every part · values match the PDF · decoupling next to the pins · nothing on In1.Cu · nothing outside your rule area · pin 1 marked on the silkscreen · ground pour joined · B4 creepage ≥ 2.5 mm · a silkscreen label on every connector · CI green.

**Mon 28 Sep, 2 pm (instructor):** paste-merge the five zones (select everything inside `ZONE_B<N>` on your branch → *Paste Special → in place* on `main`, the main branch everyone builds on), full DRC, Gerbers/BOM/CPL, JLC quote with assembly, **order**. The PCB file is never text-merged; schematic sheets are separate files and merge in git.

---
**Tutor notes (`/tutor L2`, `/tutor HW2`).** A.2: record the assigned block in `PROGRESS.md` before anything else. A.3: explain any of the six ideas on request, in the student's language, and ask one question back. E6: for every placed part ask for value **and** footprint field; ERC 0 before moving on. E7: nothing outside `ZONE_B<N>`, nothing on In1.Cu, do not edit net classes or the instructor's tracks; read each DRC message aloud with the student. E3: check the design number's magnitude against the block page only. E8: `--output` must be an absolute path; then the footprint field. E9: PR description needs the 3D screenshot and the reviewer request. E10: at least two comments, each pointing to a checklist line. The cutoff (Mon 28 Sep, 2 pm) is the gate — say it.
