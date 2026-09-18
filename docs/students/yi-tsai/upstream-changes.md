# Record of upstream changes merged into `w1-yi-tsai`

What the instructor changed in the class repository, and what it means for my work.
Newest entry first.

---

## 2026-09-18 — merged `origin/main` (4 commits, during Workshop 2)

Merged `b6091c9..20d52d1` into `w1-yi-tsai`. Working tree was clean, no conflicts.

| Commit | Time | What |
|---|---|---|
| `78ad796` | 16:17 | `lib/class_board.kicad_sym` replaced with the copy the instructor saved from KiCad |
| `b6091c9` | 16:21 | Two new project libraries packaged with 3D models, and the library tables updated so the schematic resolves on any machine |
| `f3b2383` | 17:18 | New `docs/references.md`: low-field NMR papers, datasheets of every board part, tools and suppliers |
| `20d52d1` | 17:25 | **The front panel is now routed in four sections instead of one** |

Totals: 46 files, about 241k lines added, about 12k removed. Almost all of it is the
generated panel copies and the regenerated symbol library, not hand-written change.

### 1. The front panel split — the change that matters

The front panel used to be one board owned end to end by one student. It is now **one board
whose routing is divided among four students by net group**, not by area. Each section folder
under `hardware/front-panel/sections/` holds a *complete* copy of the unrouted panel plus a
`SECTION.md` listing the nets that copy is responsible for.

| Panel section | Routes | Nets |
|---|---|---|
| A | Analog: link J1 to the SMA field and the TX coil terminal | 13 |
| B | Digital outputs, trigger, LEDs: link J2 to the TTL strip, FAST1/FAST2, TRIG, D1–D3 | 16 |
| C | Module outputs: link J3 to pull-downs, the 74AHCT541 buffer, series resistors, module header | 25 |
| D | Isolated inputs, 3.3 V and I2C: the 6N137 chains, +3V3 everywhere, I2C to OLED and Qwiic | 19 |

Why by nets: every panel net runs from a link header at an edge to a connector in the middle,
so a geometric cut would leave half a trace on every boundary. Net groups keep each connection
whole inside one copy.

The instructor recombines them with `python hardware/scripts/panel_sections.py merge`, which
takes only each section's own nets from each copy. Tracks on nets that are not mine, moved
parts and new zones are **ignored** at the merge, so I cannot damage anyone else's work — and
nobody can damage mine.

`hardware/student/front-panel/` was deleted. If I had work there it is gone; I had none.

### 2. Two naming collisions to keep straight

- **Panel section A is not class-board section A.** The main board still has sections A and B
  for students as `ZONE_A` and `ZONE_B`, unchanged by this merge. The panel's A–D are a
  separate, four-way split of a different board.
- **Four panel sections, three students on the course.** Who routes the fourth is not stated
  anywhere I can find. Question for the instructor.

### 3. Documentation that did not change

The workbook and the tutor guide were **not** touched by these four commits. They still describe
three sections where C is "the front panel board" owned whole. The hardware no longer matches
that description. Treat the hardware as current and ask before relying on the workbook's
section model.

### 4. Worth reading, given my own work

New `docs/references.md` collects low-field NMR sources, two of them as PDFs in the repository
because they are Creative Commons: Libbrecht 2025 on a 21-gauss teaching experiment, and
NMRduino 2024, which uses the same architecture as our board (Si5351/AD9834 clock and DDS,
OPA564 transmitter, OPA1656 receiver, commutating mixer). Michal 2010 by link only.

### 5. Still open after this merge

My section is not assigned yet, so I do not know which copy, if any, is mine.
