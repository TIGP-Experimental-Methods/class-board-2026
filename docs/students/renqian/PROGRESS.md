# PROGRESS — Ren Qian (Section A)

- **Language:** English (Mandarin fine for explanations)
- **Section:** **A — analog** (front panel: link J1 to the SMA field and the TX coil terminal)
- **Background:** Projects 1 (Unfair Golf) and 2 (Glowmeter) complete and on the class wall. No prior KiCad or PCB layout.
- **Review ring:** open — the old A→B→C→A ring was for the three-section scheme. To confirm under the four-way split.

## Hard dates

- **Mon 28 Sep, 2 pm** — Gerbers go to JLCPCB. My section must be **merged** by then.
- Fri 9 Oct, 2 pm — housing (Project 3b).

## My work folder

`hardware/front-panel/sections/A/front-panel.kicad_pro` — my own complete copy of the unrouted panel.
Hand-in is `hardware/front-panel/sections/A/front-panel.kicad_pcb` committed on my branch.

## My 13 nets

| Net | Net class | Track | Note |
|---|---|---|---|
| `AI1`–`AI8` | `ANALOG_IN` | 0.25 mm | DRC forces **0.3 mm** clearance to anything that is not AGND |
| `AO1`, `AO2` | `ANALOG_OUT` | 0.30 mm | |
| `AUX`, `RX`, `TX` | **`Default`** | 0.25 mm | no netclass pattern matches these three |

Every one of them has only **2 pads** — link header J1 to an SMA — except `TX`, which has 4 (SMA plus the 2-pin KF128 coil terminal). So the job is about 14 point-to-point hops, not a maze.

---

## 2026-09-18 — Workshop 2

**Done**
- Assigned Section A under the new four-way front-panel split.
- Repo pulled to `20d52d1`. Earlier work in this folder was written for the old Section C and has been rewritten.

**Verified**
- All four section copies are generated from the reworked master panel: 16 SMA, 76 footprints, no `J26`, no `TP1`, **0 tracks**. The stale-copy problem that existed earlier today is gone.
- `In1.Cu` = AGND plane, `In2.Cu` = GND plane; `no_inner_tracks` in `front-panel.kicad_dru` rejects any track on either. All routing on F.Cu and B.Cu.
- `AUX`, `RX` and `TX` are **`Default`** class, not `ANALOG_IN` — checked against `netclass_patterns` in the project file. The `AI?` pattern only matches the single-digit AI nets.

**Next**
- [ ] Ask the instructor which scope my E3/E7/E8 now is (see Gotchas)
- [ ] E3 — two questions + the tank design number (draft in `notes.md`, to rewrite in my own words)
- [ ] E8 — fetch OPA1656IDR (C1849431) with `easyeda2kicad` into `hardware/lib/class_board`
- [ ] E7 — route the 13 nets; `panel_sections.py check A` before hand-in
- [ ] Branch `a-renqian`, commit, PR

**Gotchas**
- **The workbook and the hardware now disagree.** The four-section commit `20d52d1` touched only `hardware/`, `README.md` and `AGENTS.md`. `workbook/blocks/a.md` still describes the *old* main-board Section A — the ADS8688, the OPA1656 LNA, the DG419 blanking switch, the Si5351A, the gapped sheets `b1_inputs_gapped` and `nmr_rx_gapped`, and zone `ZONE_A`. There is no Section D page at all. So it is unclear whether my section is now only the 13 panel nets, or still the whole main-board Section A with the panel nets on top. The gapped sheets do still exist in `hardware/student/`. **Asked the instructor.**
- Self-check before hand-in: `python hardware/scripts/panel_sections.py check A` reports own nets, foreign nets and moved parts. The instructor's `merge` takes only my own nets from my copy, so I cannot damage anyone else's work and they cannot damage mine.
- Do not move parts and do not edit the schematic. If a footprint is in the way, say so — the instructor moves it in the master.
- Ground pads connect to their plane with a via next to the pad. Never draw a ground track across the board.
