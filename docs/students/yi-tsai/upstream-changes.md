# Record of upstream changes merged into `w1-yi-tsai`

What the instructor changed in the class repository, and what it means for my work.
Newest entry first.

---

## 2026-09-24 (later) — merged `origin/main` (3 more commits)

Merged to `31a7a2a`. Two conflicts, both in panel section B.

- `front-panel.kicad_pro` — took upstream.
- `front-panel.kicad_pcb` — **rebuilt rather than kept this time.** Upstream's fresh split is the
  base and my 200 segments plus one GND via were transplanted onto it, giving 264. KiCad 10 names
  nets rather than numbering them, so nothing could be silently remapped, and the two sets share
  no net: the base's 64 segments are all student A's accepted analog routing.

Why rebuild and not keep mine: the new masters carry the three `PWR_AGND` to `PWR_GND` symbols,
a new `R441` and restored zones. Staying on my old base would have meant routing against a board
that no longer exists.

**The ground swap is resolved.** The instructor made the same three-symbol change in the master,
so it is now official and no longer mine to justify.

**Decision #70** names the owners: A Renqian, B me, C the instructor, D Lihdong. That answers the
four-sections-three-students question from the previous entry.

After the rebase, `kicad-cli pcb drc` parses the file and reports 69 unconnected items, down from
103 on the base alone, so my routing closes 34 connections. It also reports 131 clearance
violations, nearly all "zone clearance, actual 0.0000" — the copper pours need refilling in KiCad
before that number means anything.

Full file-by-file chronology in [hardware-history.md](hardware-history.md).

## 2026-09-24 — merged `origin/main` (14 commits, four days before the cutoff)

Merged up to `81bddc8`. One conflict, resolved. **A second deliverable appeared.**

### The conflict, and why my side won

`hardware/front-panel/sections/B/front-panel.kicad_pcb` conflicted. My side had my 200 routed
segments; the upstream side had 90 segments on section **A's** analog nets, put there when the
instructor re-split the panel copies after accepting student A's work.

Kept my side. Nothing is lost: `panel_sections.py merge` reads only each section's *own* nets
out of each copy, so A's segments in my file were never going to be read, and A's routing is
already in the master. Upstream's only change to that file was those 90 segments, nothing
structural, so my copy is not missing any base update.

### The second deliverable — the main board is now split too

The **main board** has been divided into four routing areas as well, the same way the panel was.
My copy is `hardware/sections/B/class-board.kicad_pcb`, a full copy with the instructor's
routing **locked**.

Area B is the front right: the analog outputs (DAC U301 and its output stage) and the NMR
transmitter (DDS, filter, power stage, TX terminal side). Rule area `ZONE_B`, corners
(109, 59.5) to (179.5, 114.5). 70 parts.

22 connections left to route in the area:

| Net | Connections |
|---|---|
| `AGND` | 7 |
| `GND` | 3 |
| `+3V3` | 2 |
| `/nmr_tx/+VEXT_TX` | 2 |
| `-12V` | 2 |
| `/nmr_tx/TX_VMID`, `/b3_outputs/VREF_DAC`, `+12V`, `SPI_SCLK`, `SPI_MOSI`, `/nmr_tx/TX_FB` | 1 each |

A connection with both ends inside my area is mine. One that leaves the area is the
instructor's and I must not route it. **That copy deliberately has no schematic** — do not
press F8 / Update PCB from Schematic on it.

So I now have **two** boards to hand in, not one:
`hardware/sections/B/class-board.kicad_pcb` and
`hardware/front-panel/sections/B/front-panel.kicad_pcb`.

### Also in this merge

- The symbol library was converted to the KiCad 10 format and a script now keeps it that way.
- The `owner_*` Block-field DRC rules are retired, replaced by the area split.
- Student A's work was accepted into both masters on 09-21.
- My own earlier branch was merged into `main` by the instructor on 09-19.

### Open

Three `PWR_AGND` symbols in my panel section schematic are changed to `PWR_GND`. Uncommitted
intent unknown, now committed in the snapshot. The section rules say the schematic is not mine
to edit. Decide before the pull request.

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
