# How the class board files evolved

A chronological record of the hardware directory, reconstructed from the commit history of
`TIGP-Experimental-Methods/class-board-2026`. Written 2026-09-24, four days before the PCB cutoff.

The point of this document is that the *ownership model changed three times* in three weeks, and
the file layout changed with it each time. Documentation from an earlier phase still sits in the
repository describing a model that no longer exists, so knowing which phase a file belongs to is
the difference between doing the right work and the wrong work.

---

## Phase 1 — five blocks (6 September)

The repository starts with a firmware skeleton and a project library built from the bill of
materials with `easyeda2kicad`, 46 of 46 parts. The board is organised as **five blocks, B1 to B5**:
inputs, power, outputs, switching, digital input output with trigger. The student package ships
with workbook chapters and block pages `b1`–`b5`.

Files that date from here and still exist: `hardware/lib/` and the `b1`…`b5` naming that survives
inside sheet filenames long after the blocks themselves are gone.

## Phase 2 — three sections and an NMR console (13 September)

The largest single redesign. Five blocks become **three sections A, B, C**, and the instrument
gains an NMR console: a 2 mT field, protons at 89 kHz, pulse then free induction decay then
spectrum. The main board goes to 180 x 100 mm.

- New schematic sheets `nmr_rx`, `nmr_tx`, `c_switch`; `opt_conditioning` deleted.
- **`hardware/student/<sheet>_gapped.kicad_sch` created** — one standalone project per sheet, with
  three or four items deleted for the student to place back. This is exercise E6.
- Ownership enforced by a `Block` field on every symbol, checked by `owner_*` design rules.

## Phase 3 — the panel becomes a board of its own (16–17 September)

The front panel grows to 180 x 100 mm and moves to sit flat on the back of the main board, joined
by three 2x20 headers. Then v0.7d, on the seventeenth, removes a whole subsystem:

- **All four relays and all mains switching deleted**, and the `b4_switching` sheet with them.
- In their place a **module header**: seven buffered 5 V logic lines on the panel, so anything that
  switches real current is a bought module that brings its own isolation.
- The two isolated inputs move to the panel.
- **Section C is redefined as the whole front-panel project.**

## Phase 4 — the panel splits four ways (18 September)

The first split. The panel is one board, but routing it is divided among four people **by net
group, not by area**, because every panel net runs from a link header at an edge to a connector in
the middle, so a geometric cut would leave half a trace at every boundary.

- **`hardware/front-panel/sections/{A,B,C,D}/` created**, each a complete copy of the unrouted panel
  plus a `SECTION.md` naming its nets.
- **`hardware/scripts/panel_sections.py` created**: split, check, merge.
- **`hardware/student/front-panel/` deleted** — superseded by the above.
- The symbol library is converted to the KiCad 10 format, kept there by `cb_symbols.py`.

Same day, the instructor hand-reworks both boards: links re-placed, jumpers become headers, the
TCXO removed, 16 SMA.

## Phase 5 — the main board splits four ways too (19–21 September)

The instructor routes the main board in stages, 790 tracks on the nineteenth, 1710 on the
twenty-first. Then the same pattern is applied to it:

- **`hardware/sections/{A,B,C,D}/` created**, each a full copy of the main board with the
  instructor's routing **locked**, plus rule areas `ZONE_A`…`ZONE_D`.
- **`hardware/scripts/main_sections.py` created.**
- **The `owner_*` Block-field rules are retired** — the area split replaces them.

Student A routes panel section A and main board area A; both are accepted into the masters on the
twenty-first, and all the section copies are re-split from the updated masters.

## Phase 6 — corrections and named owners (24 September)

- The instructor's masters are saved with **three `PWR_AGND` symbols changed to `PWR_GND`**, a new
  `R441`, and further routing. Five copper zones on the main board, lost in an earlier save, are
  restored.
- **`BASE_UUIDS.txt` added** to both section folders, and the split scripts changed so that the
  instructor's own routing can never be resurrected out of a student copy.
- **Decision #70** names the owners in both section READMEs: A Renqian, **B Yi-Tsai**, C the
  instructor, D Lihdong. Four sections, three students, the fourth kept by the instructor.

---

## What this means for section B, in one place

| Question | Answer |
|---|---|
| Which boards are mine | `hardware/sections/B/class-board.kicad_pcb` and `hardware/front-panel/sections/B/front-panel.kicad_pcb` |
| Which nets on the panel | 16: the TTL strip, FASTTTL1/2, TRIG, the three LEDs |
| Which area on the main board | `ZONE_B`, front right, corners (109, 59.5) to (179.5, 114.5) |
| What happens to tracks on other nets | Silently ignored at merge. They cannot damage anyone, and they cannot count |

## Stale documentation to distrust

These describe Phase 2 or Phase 3 and were never updated:

- `workbook/ch2-day-2-week-2.md` — still says three sections and lists gapped sheets as the work.
- `hardware/README.md` and `hardware/AGENTS.md` — still map sections to gapped sheets and describe
  the retired `owner_*` rules.
- `hardware/student/*_gapped.*` — five projects, untouched since 18 September, belonging to a
  model that no longer decides anything. Whether E6 is still expected is an open question for the
  instructor.

The two `SECTION.md` files are the current authority. When they disagree with the workbook, they win.
