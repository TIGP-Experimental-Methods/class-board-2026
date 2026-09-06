# Chapter 2 — Day 2 + week 2: your part of the board

**Fri 2026-09-18, 14:20–16:20 (2 h) + Homework 2 (3 h), gated by the class PCB order on Mon 09-28.** Today you meet every IC on the board, learn the only six KiCad operations you need, place the parts missing from your sheet, and start routing your zone. This week you finish it, fetch one part from LCSC, open your PR, and review a classmate's.

**Prerequisites:** HW1 done (E2 merged, two answers, KiCad 10 installed, the project opened once (the library is in `hardware/lib/`), `SPEC.md`). Bring your laptop; the schematic PDF is on the course site. Optional background: [chapter A](chA-electronics-from-zero.md) (self-study, before today if you have never seen a schematic).

**The hardware model.** The MCU stays on the dev board; the **class board is a carrier** it plugs into: the analog front end done properly, isolation, buffers, robust connectors. One design, five units, one order; **JLCPCB assembles everything, SMD and through-hole**. You solder nothing. The dev board alone keeps running the app as the permanent fallback.

---

## Part A — In class

### A.1 Electronics essentials, on our schematic (0–20 min)
Six ideas, each pointed at a page of the PDF. [Chapter A](chA-electronics-from-zero.md) has the long version.
- **(a) Rails, decoupling, ground — B2.** Every IC gets a 100 nF at its supply pin and a 10 µF per rail per zone; the two grounds (GND for power and logic, AGND for signals) meet at one star point.
- **(b) What ±10 V and 16 bits buy — B1/B3.** 20 V / 65,536 = 0.3 mV per LSB; the rest of the board exists to keep noise below that.
- **(c) The op-amp stage as a black box — B3.** Gain and offset from two resistor ratios; the 49.9 Ω that protects it from the cable.
- **(d) Isolation — B4.** A relay's coil and contacts share no copper; an optocoupler's LED and transistor share no copper; creepage is the distance that keeps it so.
- **(e) 3.3 V vs 5 V logic — B5.** Why a GPIO cannot drive TTL, why a buffer can, why "5 V-tolerant" matters.
- **(f) The buses — base.** SPI (three shared wires + one chip-select per device) and I²C (two wires, addresses) tie every block to the dev board.

### A.2 Read your block, again (20–30 min)
`/tutor L2`: two harder questions from your block page (*which pins carry the fastest signal; where does your ground join*). Then three minutes with the neighbour who will review your PR (ring: A→B→C→D→E→A).

### A.3 KiCad live — the only six operations (30–45 min, watch)
On the projector, in the base sheet: **place** a 100 nF + 10 µF pair and wire it → **annotate** → *Tools → Update PCB from Schematic* → **drag** the two footprints next to the pin → **route** three tracks (`X`, click, click) → **DRC** (`Inspect → DRC`), then the **3D view** (`Alt+3`). V4 and V5 replay the same steps.

### A.4 Exercise E6 — schematic gaps (45–65 min)
- [ ] `git switch -c b<N>-<name>`; open `hardware/class-board.kicad_pro`; open your sheet `student/b<N>_gapped.kicad_sch`.
- [ ] Put the full PDF page for your block next to it. Your block page lists the 3–4 parts that were deleted. For each: `A` (add symbol) → search the **project library** `class_board` → place → wire (`W`) → set the value (`V`) and check the **footprint field** (`E`) says the right package (0603, SOT-89, …).
- [ ] Keep the reference designators the PDF shows (the footprints on the PCB carry the same names, so *Update PCB* drops the parts exactly where the instructor placed them).
- [ ] `Inspect → ERC` → **0 errors** (warnings about power flags you may ignore only if the tutor agrees).
- ✔ *You should see:* your sheet matches the PDF; ERC 0.
- *Tutor asks:* "which footprint does your 10 µF have and why not 0603?"

### A.5 Break (65–70)

### A.6 Exercise E7 (start) — route your zone (70–100 min)
- [ ] Open the PCB; *Update PCB from Schematic*; the new footprints appear near your zone — drag them inside `ZONE_B<N>`, decoupling capacitors **next to the pin they serve**.
- [ ] Route (`X`): signals on F.Cu (top), long or crossing ones on B.Cu (bottom) via `V`; **nothing on In1.Cu (layer 2 is GND)**, power on In2.Cu only if the instructor's rails are there already. Track widths come from the net classes (do not change them).
- [ ] Every 15 minutes: `Inspect → DRC`. Read every message with the tutor; the two classics are *wrong layer* and *unconnected net*.
- ✔ *You should see:* about half the zone routed; DRC shows only unrouted-net items for the rest.

### A.7 PR + peer review, live (100–110 min, watch)
The instructor opens a PR from a student branch, requests the ring reviewer, writes one comment against the checklist, shows *Request changes* vs *Approve*.

### A.8 Homework brief (110–120)
The timeline to the order: **PR Wed 09-23 · reviews Fri 09-25 · fixes Sun 09-27 · order Mon 09-28.** Slip here = slip everywhere.

---

## Part B — Homework 2 (3 h) — `/tutor HW2`

- [ ] **E7 Finish routing (1.25 h).** DRC **0 errors, 0 unrouted**; the ground pour joined (`B` refills zones); a 3D screenshot to `docs/students/<name>/zone-3d.png`. B1/B4/B5 owners have replicated channels: route one, copy the pattern. Watch V5 *Route, DRC, PR, review* (10 min) first.
- [ ] **E8 One part from LCSC (0.25 h).** Your block page names it (e.g. B4: the relay, C12072). In the repo root:
  ```sh
  easyeda2kicad --full --lcsc_id C12072 --output "<absolute path>/hardware/lib/class_board"
  ```
  The symbol lands in `class_board.kicad_sym`, the footprint in `class_board.pretty`, the 3D model in `class_board.3dshapes`. Open the symbol in the schematic editor, check pin 1 against the datasheet, and swap it into your sheet in place of the instructor's copy (or add it as the second footprint alternative). Commit `hardware/lib/`. *Teaches:* where parts come from — the LCSC → JLC pipeline.
- [ ] **E9 PR by Wed 09-23 (0.25 h).** `git add hardware/` (your sheet, the PCB, the library) → commit → push → `gh pr create` with the 3D screenshot in the description → *Reviewers:* your ring reviewer. CI must be green.
- [ ] **E10 Review your peer by Fri 09-25 (0.5 h); fix yours by Sun 09-27 (0.25 h).** Open their PR → *Files changed* → check out the branch locally → open the PCB → walk the checklist below → leave **≥ 2 comments** → *Approve* or *Request changes*. Then address the comments on your own PR. *Teaches:* reading someone else's layout; being reviewed.
- [ ] Slack ≈ 0.4 h.

**The review checklist** (also in [chapter C](chC-cheat-sheets.md); the instructor uses the same list at merge):
ERC 0 / DRC 0 · `LCSC` field on every part · values match the PDF · decoupling next to the pins · nothing on In1.Cu · nothing outside your rule area · pin 1 marked on the silkscreen · ground pour joined · B4 creepage ≥ 2.5 mm · a silkscreen label on every connector · CI green.

**Mon 09-28 (instructor):** paste-merge the five zones (select everything inside `ZONE_B<N>` on your branch → *Paste Special → in place* on `main`), full DRC, Gerbers/BOM/CPL, JLC quote with assembly, **order**. The PCB file is never text-merged; schematic sheets are separate files and merge in git.

---
**Tutor notes (`/tutor L2`, `/tutor HW2`).** E6: for every placed part ask for value **and** footprint field; ERC 0 before moving on. E7: nothing outside `ZONE_B<N>`, nothing on In1.Cu, do not edit net classes or the instructor's tracks; read each DRC message aloud with the student. E8: `--output` must be an absolute path; then the footprint field. E9: PR description needs the 3D screenshot and the reviewer request. E10: at least two comments, each pointing to a checklist line. Deadlines are gates — say the dates.
