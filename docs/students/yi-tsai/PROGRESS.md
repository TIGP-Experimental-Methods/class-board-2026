# Yi-Tsai Liang — progress

GitHub: `tojestspacja` · branch `w1-yi-tsai` · section: not yet assigned (assigned at the start of Workshop 2)

## My repositories and pages

| What | Repository | Page |
|---|---|---|
| Project 1 — THROUGH (quantum tunnelling platformer) | https://github.com/tojestspacja/md-simulation | https://tojestspacja.github.io/md-simulation/quantum/ |
| Resonance — playable explainer for magnetic resonance | https://github.com/tojestspacja/mr-simulation | https://tojestspacja.github.io/mr-simulation/ |
| Project 2 — Resonance Tuner (ESP32-S3 firmware + phone game) | not published yet | — |

Local folder names do not match the repository names: `resonance-response/` is the clone of
`tojestspacja/mr-simulation`, and the folder `mr-simulation/` is the unpublished Project 2.

---

## 2026-09-18 — before Workshop 2 (preparation)

- Done: KiCad 10.0 confirmed installed and `hardware/class-board.kicad_pro` opened for the first time (B12.2); JLCPCB signup and parts library opened but the account is **not created yet** (B12.3 still open); branch `w1-yi-tsai` created from `origin/main` and this file started (B12.4); `handover.md` written for the Resonance repo and the Project 2 folder.
- Verified: KiCad window title reads *class-board — KiCad 10.0* with the footprint libraries loaded and no missing-library dialog, which is the B12.2 check; `git fetch` puts this branch on `origin/main` at `ee81601`; Project 1 and Resonance both load from their published pages.
- Next: finish the JLCPCB sign-up and log in once, which is the whole B12.3 check; then W2.D.1; make Project 2 a real repository before it needs a wall entry.
- Gotchas: KiCad's first run opens a *KiCad Setup* wizard that silently blocks the project from loading until it is finished — built-in libraries chosen, anonymous data collection left off. There are two clones of `class-board-2026` on this machine and the one KiCad actually opened, under `private/MET-Physics/course-corpus/raw/`, is one commit behind `origin/main`, missing the instructor's 2026-09-18 board rework (Decision #66: links re-placed, jumpers to headers, TCXO removed, 16 SMA) — open the copy in `tigp-2026/` instead. The Project 2 folder `mr-simulation/` is not a git repository at all, and that name is already taken on GitHub by the Resonance web app, so it needs a different repository name.

## 2026-10-02 — Project 3: housing, probe and data models (design stage)

- Done: `docs/students/yi-tsai/housing/` — printed housing (shell, OLED hood, coupon, bottom plate), probe (former, 50 mL sleeve, tripod cradle, B0 Helmholtz pair as a reference), the whole bench in `instrument.scad`, a physics simulator `spectrum.py`, a 3D-printed data model after Jones et al. 2021, and laser / water-jet versions of every part (`cut-*.scad`, `export_cut.py`, `CUT-LIST.md`). One shared parameter file, `nmr-params.scad`. Landing page: the folder's `README.md`. Project 3 card on the class wall points there until the Project 3 site exists.
- Verified: every .scad file runs with no errors or OpenSCAD warnings; STLs render as single valid solids; the simulator reproduces the coil pair's design calibration (59.7 kHz/A) under constant-current drive. Nothing printed, cut or measured yet.
- Next: the board-side decisions that block a real scan — TX/RX on one coil (RX clamp diodes across the transmitter, scan aborts), B0 at constant current (voltage drive drifts 138 Hz/min); print the coupon; then water, a D₂O blank and frozen water.
- Gotchas: probe.scad's "151 Hz spread" is the winding's worst points, not the linewidth — over the 50 mL tube's water the field gives about 2 Hz (18 ppm); `export_cut.py --spectrum jet` clears `cut/laser` before exporting.

## 2026-10-03 — Project 3 has one home: tojestspacja/nmr-instrument

- Done: the Project 3 material moved from `docs/students/yi-tsai/housing/` to https://github.com/tojestspacja/nmr-instrument (history kept with `git subtree`), site https://tojestspacja.github.io/nmr-instrument/ with the simulator at `/simulator/`. The duplicate simulator copy in `housing/sim/` is gone. This folder now holds only the course hand-in (housing.scad, base-shell/hood/coupon STL, bottom-plate.dxf, housing.png), a stamped snapshot written by `tools/handin.py` in nmr-instrument. The real boards and firmware stay here; nmr-instrument pins them in `hardware/README.md` to main @ eef00d2.
- Verified: every OpenSCAD file runs without errors or warnings at its new path; the board meshes load from this repository beside it; the flat-part re-export and the hand-in STLs are byte-identical to before.
- Next: design changes go to nmr-instrument, then `py tools/handin.py` refreshes this folder before the 9 Oct hand-in.
- Gotchas: never edit the hand-in copy here; it is overwritten by the next snapshot.
