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
