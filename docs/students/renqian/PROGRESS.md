# PROGRESS — Ren Qian

*Written by the tutor; correct anything that is wrong or that you would put differently.*

- **Language:** English (Mandarin fine for explanations)
- **Project 3 — the instrument.** Decision #78 (2026-10-02) retired the "Project 3a / 3b" labels:
  Project 3 is the instrument, its housing and its project website. The class board is the shared
  platform designed together in Workshop 2, and the analog side of it was mine.
- **Background:** Projects 1 (Unfair Golf) and 2 (Glowmeter) complete and on the class wall. No
  prior KiCad or PCB layout before this course.
- **Review ring:** still open. The old A→B→C→A ring was for the three-section scheme and has not
  been restated for the four-way split. E11 needs a ring reviewer, so this has to be settled.

## Hard dates

- ~~**Mon 28 Sep, 2 pm** — Gerbers to JLCPCB; my section merged by then.~~ **Met** — PR #3 merged
  Wed 24 Sep 20:27, three days early.
- **Fri 9 Oct, 2 pm** — the housing files. All six exist; nothing has been printed yet.

## Where things stand

| | state |
|---|---|
| Front panel, my 13 nets | merged. Master panel: **0 DRC violations, 0 unconnected** |
| Main board area A | merged. Master board: **0 violations, 0 unconnected** |
| Housing hand-in | 6 of 6 files present, all three parts CGAL `Simple: yes` |
| Test coupon | **not printed** — so the hole sizes are still assumptions |
| Project wall | Project 3 card added 2026-10-02 |
| Project website | live, but several sections still say "To write" |
| E3 (notes.md) | still the tutor's draft — **mine to rewrite, and it is graded** |
| E11 drivers + panels | not started |

---

## 2026-10-02 — Workshop 3, the housing

**Done**
- Setup step 11: OpenSCAD 2021.01 and Bambu Studio were already installed; **BOSL2 was missing** and
  was cloned into the library folder. Repo was 46 commits behind and is now current.
- `housing.scad` plus five files beside it: params, shapes, base, cover, coupon. Everything measured
  off `hardware/release/*.stl`, nothing off a ruler.
- Base: wall and floor 2 mm, four M3 bosses with side-entry nut pockets, five rear connector
  openings, 24 ventilation slots. 190 × 110 × 31.3.
- Cover: two heights. A low deck over the SMA field so a thread stands **5.5 mm proud**, and a
  raised box clearing the **13.82 mm** OLED and the **14.10 mm** TX terminal. Locating lip, and the
  sixteen jack names engraved on top because the panel silkscreen is hidden under it.
- Coupon: holes 3.0–3.6 in 0.1 steps, a nut pocket identical to the base's, a wall, and engraved
  text at 2.2 / 2.6 / 3.2 mm.
- Project 3 card on the class wall.

**Verified**
- Every wire entry and every vent has **no flat ceiling**: the connector openings get a 45° gable,
  the vents are stadiums. The only overhang left in the whole design is the 5.8 mm bridge over each
  nut pocket.
- The cover was **190 × 106 against a 190 × 110 base** — x had been taken from the outer face and y
  from the inner. Caught by measuring the exported DXF, now both 190 × 110.
- The jack names were read from the **master** panel, not from my section copy. Those two disagree:
  the instructor reassigned AUX / RX / TX to different jacks after the sections were split, so three
  of the sixteen labels would have been wrong.
- `class-board.stl` carries a **stale 3D model**: J901 and J903 (KF301-5.0-2P) read 5 mm high.
  Commit `eef00d2` fixed that footprint but re-exported the panel only. `KF301_FIX` compensates and
  goes back to 0 once the board STL is re-exported. **Worth telling the instructor** — every student
  designing a housing will hit it.
- Engraved text: measured on the glyph, size 2.2 gives a **0.440 mm** stroke against roughly 0.42 mm
  from a 0.4 mm nozzle. The three LED names are one extrusion wide and may not appear at all.

**Next**
- [ ] **Print the coupon.** Which hole takes an M3, whether the nut slides into 5.8 mm, and which
      text size is legible. Until then `M3_CLEAR`, `NUT_AF` and `FIT` are assumptions.
- [ ] Read the supports preview, especially the four nut pockets.
- [ ] Buy fasteners: **M3 × 30 ×2 and M3 × 45 ×2** — the near pair's heads land on the low deck and
      the far pair's on the raised deck, 12.3 mm higher. Plus M3 × 11 stand-offs and four M3 nuts.
- [ ] Write the specification **from `workbook/housing-brief.md`, not from the files** — we built
      this backwards, so a spec reverse-engineered from the design would make the review circular.
- [ ] Then a fresh Claude session reviews the design against that specification.
- [ ] E3 in `notes.md`, in my own words.
- [ ] E11, and settle who my ring reviewer is.
- [ ] Finish the project website — it is 20% of the mark and Decision #78 asks for a good one.

**Gotchas**
- **BOSL2 owns a lot of short names.** `CTR` and `BACK` are direction constants; using either as my
  own variable produced assertion failures pointing at BOSL2's own files and at the wrong line in
  mine. Prefix your own names.
- `%` geometry is excluded from F6 and from STL export, which is what makes it safe for the
  reference boards — but it also means it will not appear in a `--render` picture.
- OpenSCAD writes **ASCII** STL, so a re-export changes the file even when the geometry is
  identical. Compare facet and vertex counts, not the md5.

---

## 2026-09-24 — review follow-up, merged

- `AUX` was on **B.Cu**, the wrong side for its reference plane — the router had picked that layer
  only because it was emptier. Moved to F.Cu, 13 segments down to 8.
- 17 GND stitching vias added, so signal vias that change plane have a local return path. Under-
  stitched vias 36/38 → 13/38.
- PR #3 merged 20:27, before the 2 pm Monday cutoff.
- At hand-in, four connections in main-board area A were still open; they are closed in the master
  now, which is where the 0/0 above comes from.

## 2026-09-21 — first hand-in

- PR #2: front panel 13/13 nets, main board area A 47/53.

## 2026-09-18 — Workshop 2

**Done**
- Assigned Section A under the four-way front-panel split.

**Verified**
- `In1.Cu` = AGND plane, `In2.Cu` = GND plane; `no_inner_tracks` rejects any track on either, so all
  routing is on F.Cu and B.Cu.
- `AUX`, `RX` and `TX` are **`Default`** class, not `ANALOG_IN` — the `AI?` netclass pattern only
  matches the single-digit AI nets.

**Standing rules**
- Do not move parts and do not edit the schematic. If a footprint is in the way, say so — the
  instructor moves it in the master.
- Ground pads reach their plane through a via next to the pad. Never a ground track across the board.
- The merge takes only my own nets from my copy, so I cannot damage anyone else's work and they
  cannot damage mine.
