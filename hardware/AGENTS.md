# hardware/ — working instructions (D7), rev B / v0.7

Sources of truth: [`../prompt.md`](../prompt.md) (what to deliver and how to verify),
[`../10-Class-Board-Design-Brief.md`](../10-Class-Board-Design-Brief.md) (the circuit and layout specification, v0.6)
as amended by the v0.7 re-spec `notes/2026-09-13-nmr-respec-proposal.md` and the NMR circuit design
`notes/2026-09-13-v07-nmr-circuits.md` (course repo), [`../tools/pcb/README.md`](../tools/pcb/README.md) (installed
tools).  This file only says how this directory is built and where the validated artifacts are.  Decisions live in
`docs/design-decisions.md` (D-01…D-57); requirement status in `docs/requirements.md` (R-01…R-47); the layout review in
`docs/design-review.md`; the bring-up plan in `docs/bring-up.md` (T-00…T-23).

**2026-09-17 — v0.7d (course-repo Decision #58; facts in `notes/2026-09-17-relays-optos-hbridge-facts.md`).**  The four
JQC-3FF relays, their terminals, drivers, flyback diodes and coil LEDs, **all mains switching**, the whole
`b4_switching` sheet, the `MAINS`/`MAINS1…4` net classes and every `mains_*` DRC rule are **deleted**.  In their place
the free TCA9535 ports are **MODULE OUT 1…7** (`MOD1…MOD7`), carried to the panel on link J8 pins 19…31 odd and
buffered there to 5 V TTL for a commercial relay / H-bridge module.  The two isolated inputs (6N137 U401/U402,
terminals J411/J412) **moved to the front-panel board** with their circuit unchanged; `OPTO_IN1/2` come back over J8
pins 35/37 to GPIO16/17.  **Student section C is now the front-panel project** (`front-panel/`), and the main board's
former `ZONE_C` — the power entry (`b2_power`) and the coil switches (`c_switch`: +VEXT input, DRV8871 H-bridge,
polarizer) — is the instructor's **`ZONE_INSTR`**.  Everything below is written for that state.

## The five rules that matter most (v0.7)

1. **Never regenerate the PCB once hand routing has started.**  The main board is routed **by hand** (students in
   Workshop 2, instructor for the base/rails/SPI).  From the first track, `class-board.kicad_pcb` is the hand-edited
   master and `scripts/gen_pcb.py` is only a placement reference — running it would delete every track.  The
   schematic, by contrast, may be regenerated freely: UUIDs are deterministic (D-47), so identical inputs give a
   byte-identical file and every change diffs.
   *The exception, taken twice while the board was still empty:* on **2026-09-16** (Decision #55, D-52) and again on
   **2026-09-17** (Decision #58, D-56 — the v0.7d re-placement after the relays came out) the board had **0 tracks and
   0 vias**, so there was no hand work to lose; the backup of the pre-rework board is at `release/pre-rework-20260913/`.
   The checked-in board still has 0 tracks and 0 vias, and **341 footprints**; rule 1 applies from the first track.
2. **A new circuit block is a new `scripts/sheet_*.py` module**, not an edit to the 1300-line `gen_sch.py`.  Each
   module exposes `build(root_uuid) -> Sheet` (picked up by `gen_sch.main()`) and a module-level `PLACEMENT` dict
   `{ref: (x, y, rot)}` (picked up by `gen_pcb.placement()` through `sheet_modules()`).  A module that fails to
   import is skipped with a printed note, so a broken module never blocks the build — **read the console output**.
   Existing modules: `sheet_nmr_rx.py` (section A, 7xx/9xx), `sheet_nmr_tx.py` (section B, 8xx),
   `sheet_c_switch.py` (**the instructor's block**, 9xx — it was section C until 2026-09-17).
3. **Every symbol carries a `Block` field, and it decides who owns the footprint.**  Values in use on the main board:
   `B1`, `OPT`, `NMR_RX` → section **A**; `B3`, `B5`, `NMR_TX` → section **B**; `B2`, `C_SW` → the **instructor**
   (`ZONE_INSTR`); `BASE` → instructor base area (it is also the escape hatch for a part that serves two sections,
   e.g. the TCA9535 expander).  `B4` is retired — that sheet no longer exists.  The DRC rules are `owner_A`,
   `owner_B` and **`owner_INSTR`** (`A.enclosedByArea('ZONE_A'|'ZONE_B'|'ZONE_INSTR')`); a misplaced part is an
   assertion failure, not a silent error.  **Section C has no area on the main board**: it is the front-panel
   project in `front-panel/`.
4. **The design rules live at the project root.**  KiCad reads `<project>.kicad_dru` from the project folder, so
   `class-board.kicad_dru` must exist there; `rules/class-board.kicad_dru` is the edit source and the two must stay
   identical (D-48).  Editing only the copy in `rules/` means the rules never run.  **Order matters**: KiCad
   applies the *last* matching rule, not the most specific one, so a narrower rule must be written *after* the
   general one — that is why the panel's per-area `iso1_inside` / `iso2_inside` clearances sit after
   `iso_in_clearance` in `front-panel/front-panel.kicad_dru` (the same trap cost a day with the retired `mains_*`
   rules, D-51/D-52).  The main board's rule file is now `no_inner_tracks`, `iso_in_clearance`,
   `analog_in_clearance`, the three manufacturing rules and `owner_A` / `owner_B` / `owner_INSTR`: **no `mains_*`
   rules** (D-53).  `iso_in_clearance` is kept but has no members on the main board any more — the ISO_IN nets live
   on the panel (D-54).  No generator writes this file; it is hand-maintained.
5. **Footprints must be in KiCad 10 format** (`kicad-cli fp upgrade` on the library after any import) and the
   library nickname is `class_board:` — **never an `easyeda2kicad:` prefix** in a symbol's `Footprint` field.  After
   adding any footprint, run `python fix_courtyards.py` (courtyard = body ∪ pads + 0.25 mm, D-27) and then
   `place_check.py`, or the collision checks are blind.

## Layout of the directory

| Path | What |
|---|---|
| `class-board.kicad_pro/.kicad_sch`, `sheets/*.kicad_sch` | main board: root + **9** hierarchical sheets (`base_mcu`, `b1_inputs`, `b2_power`, `b3_outputs`, `b5_dio_trig`, `nmr_rx`, `nmr_tx`, `c_switch`, `front_panel_link`).  `opt_conditioning` was deleted in v0.7 (D-32); **`b4_switching` was deleted on 2026-09-17** (D-53/D-54) |
| `class-board.kicad_pcb`, `class-board.kicad_dru` | 4-layer main board **180 × 100 mm** and the custom DRC rules KiCad loads; `rules/class-board.kicad_dru` is the edit source |
| `front-panel/front-panel.kicad_*` | **4-layer** front panel **180 × 100 mm** (D-50, 4 layers since Decision #57): 16 SMA (3 × 6 grid at **18 mm** pitch, two positions empty; J26 removed 2026-09-18), OLED module socket, 3 LEDs, TTL screw strip, TX terminal, Qwiic, **the two isolated 5–24 V inputs** (D-54) and **the module header** (74AHCT541 + 2×6 shrouded box header, D-53); three 2×20 female headers on the inner face mate J6/J7/J8 and are the **only** parts on that face — the panel is single-sided for assembly otherwise.  **This project is student section C** (D-55).  Panel coordinates are mirrored in x against the main board (`panel x = 180 − main x`); its lib tables point at `../lib`, the KiCad standard footprints come from the global table |
| `front-panel/sections/{A,B,C,D}/` | **2026-09-18: the panel routing is divided among the four students by NETS** (A analog, B digital + LEDs, C module outputs, D isolated inputs + 3.3 V + I2C). Each folder is a complete copy of the unrouted panel with a `SECTION.md`; `scripts/panel_sections.py split|check|merge` regenerates the copies from the master, reports what a section routed, and merges only each section's own nets (plus its GND/AGND vias) into `front-panel-merged.kicad_pcb` with a DRC run. The instructor accepts the merged board by hand. Replaces the old generated `student/front-panel/` copy. |
| `lib/class_board.kicad_sym`, `lib/class_board.pretty/`, `lib/class_board.3dshapes/` | project-local library (one symbol per BOM line, LCSC/JLC fields; EasyEDA-derived footprints with rewritten courtyards) |
| `student/<sheet>_gapped.kicad_sch` (+ `.kicad_pro`) | student copies for sections **A** and **B** (brief §12); section **C** is the whole front-panel project, unrouted, not a gapped sheet.  `docs/student-deletions.md` lists what was removed |
| `release/<rev>/{main-board,front-panel}/` | Gerbers + drill (bottom-left aux origin), BOM/CPL (JLC columns), PDFs, SVG/PNG, STEP, ERC/DRC reports, `hashes.txt` |
| `scripts/` | the generators (below).  **The schematic and the placement are generated: edit the scripts, not the KiCad files — except the routed PCB, which is hand-edited (rule 1).** |

## Build chain (run from `hardware/scripts`, Python 3.13, KiCad 10.0 `kicad-cli`)

`kicad-cli` is found through the `KICAD_CLI` environment variable, default
`C:/Program Files/KiCad/10.0/bin/kicad-cli.exe`.  (`scripts/release.py` still hard-codes a foreign path — finding
F-15; fix it before building a release.)

```
python cb_symbols.py            # -> lib/class_board.kicad_sym
python gen_sch.py               # -> class-board.kicad_sch + sheets/*.kicad_sch + class-board.kicad_pro
                                #    (root + the 7 built-in sheets + every scripts/sheet_*.py module)
kicad-cli sch export netlist --format kicadxml -o ../.netlist.xml ../class-board.kicad_sch
kicad-cli sch erc --severity-all --format json -o ../.erc.json ../class-board.kicad_sch
kicad-cli fp upgrade ../lib/class_board.pretty      # after importing any footprint (KiCad 10 format)
python fix_courtyards.py        # after importing footprints: courtyard = body + pads + 0.25 mm
python place_check.py           # fast courtyard/pad collision check of the placement in gen_pcb.py
python gen_pcb.py --no-route    # placement + zones + rule areas -> class-board.kicad_pcb   (SEE RULE 1)
kicad-cli pcb drc --severity-all --schematic-parity --refill-zones --format json -o ../.drc.json ../class-board.kicad_pcb
python ../../tools/pcb/audit_angles.py ../class-board.kicad_pcb
python gen_panel.py             # front panel: schematic, netlist, board, routing, link-mating audit
python gen_student.py           # student gapped copies + docs/student-deletions.md
python release.py <rev>         # release package for both boards (re-runs ERC/DRC/audit on the saved files)
```

`router.py` / `route_iterate.py` / `layout_report.py` / `probe.py` are the v0.6 scripted-router tools.  They are kept
for reference only: v0.7 routing is done by hand in the KiCad GUI, and running the router would overwrite the board.

Checks that must be clean before a release: ERC 0, DRC 0 errors and 0 unconnected items (with zones refilled), the
`owner_A/B/C` assertions passing, angle audit ok, `place_check.py` 0 collisions, `gen_panel.py` link-mating audit,
BOM without missing LCSC numbers, and the JLC rotation preview checked by hand.

## Conventions

- Owner areas on the main board (`gen_pcb.ZONES`): **ZONE_INSTR** (0.5, 0.5)–(96, 36)–(37.5, 57.5)–(0.5, 57.5) L-shape
  along the rear-left and left edges — power entry plus the instructor block placed as one piece at **x 45–86** on the
  rear edge, terminals `J901` / `J903` / `J905` at x **51.0 / 62.7 / 76.9**, rotation 180 (wire entry off the edge,
  Decision #46); **ZONE_BASE** (37.5, 36)–(100, 57); **ZONE_A** the front-left; **ZONE_B** x 100–179.5 front **plus the
  rear-right strip x 96–179.5, y 0.5–36** that the relay row used to occupy (D-56).
- Board coordinates: x right (0…180), y down; rear edge (USB-C, jack, terminals) at y = 0; front edge at y = 100.
  The panel stacks on the **back** of the board on three 2×20 headers (J6/J7/J8 on B.Cu). **Since the instructor's
  hand rework of 2026-09-18** (both boards hand-edited, generators retired, outlines drawn at y 15–115): J6 ↔ panel J1 =
  analog along the rear edge (pads x 114.4–162.6, y 19.5/22.0), J7 ↔ panel J3 = power + OPTO_IN + MOD1–7 on the right
  edge (x 169.2/171.7, y 30.9–79.1), J8 ↔ panel J2 = digital on the left edge (x 3.7/6.3, y 53.5–101.8). The panel is
  drawn from its outer face: `panel x = 180 − main x`, `panel y = main y`; the main board's rear edge is the panel's top
  edge. Pin maps: course repo `notes/2026-09-18-board-rework-review.md`.
- Reference ranges: 1xx B1 · 2xx B2 · 3xx B3 · **4xx retired B4 — now used on the panel only** (J411/J412 and the
  isolated-input parts that moved with them, plus the module-header block U410 / C410 / R481–R489 / J40) · 5xx B5 ·
  6xx deleted OPT · **7xx clocks + receiver** · **8xx DDS + transmitter** · **9xx mixer/IF, coil switches, external
  power**.
- A new part needs: a symbol in `cb_symbols.py` with its `LCSC`, library-type and `Datasheet` fields, a footprint in
  `lib/class_board.pretty/` (KiCad 10 format, courtyard rewritten), a `Block` field, a `PLACEMENT` entry, and a line
  in the design record (`docs/design-decisions.md`) with the datasheet number it comes from.
- A `sheet_*.py` module may fall back to a stand-in symbol with the right footprint while a value is missing from
  `cb_symbols.py`; it must then set a `SUBSTITUTE` field and print the substitution, so a stand-in cannot reach a BOM
  unnoticed.  Chase those prints down before ordering.
- Net classes and widths are in `gen_sch.write_project` (and mirrored in `router.py`, unused in v0.7):
  `Default`, `POWER_RAW`, `POWER`, `ANALOG_IN`, `ANALOG_OUT`, `FAST`, `ISO_IN`.  **`MAINS` and `MAINS1…MAINS4` were
  deleted on 2026-09-17 with the relays** (D-53) — do not reintroduce them on the main board.  `ISO_IN` is still
  declared but has **no matching pattern** here: the isolated inputs are on the panel, and it is the panel project
  that must carry the class, the 2.5 mm rule and the two keep-out areas (D-54).  Remember that KiCad 10 puts a net
  in **every** class whose pattern matches.
- Analog/digital ground: everything in the receiver — tank, LNA, blanking switch, mixer switches, V_MID network, IF
  filters **and the 74HC74 divider** — is on AGND and +3V3A; the Si5351, the expander, the H-bridge, the polarizer and
  the OPA564 return are on GND; the two meet only at NT1.  Do not "tidy" a ground symbol from AGND to GND.
- Never hand-edit a file KiCad has open.  Google-Drive-hosted copies can corrupt `.git/index` — work in
  `C:\Claude\TIGP-2026\TIGP-board` and copy back.
- Secrets never enter this directory; `.local*`, `.route*`, `.*.json` scratch files are git-ignored.
