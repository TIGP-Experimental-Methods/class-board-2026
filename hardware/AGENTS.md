# hardware/ — working instructions (D7), rev B / v0.7

Sources of truth: [`../prompt.md`](../prompt.md) (what to deliver and how to verify),
[`../10-Class-Board-Design-Brief.md`](../10-Class-Board-Design-Brief.md) (the circuit and layout specification, v0.6)
as amended by the v0.7 re-spec `notes/2026-09-13-nmr-respec-proposal.md` and the NMR circuit design
`notes/2026-09-13-v07-nmr-circuits.md` (course repo), [`../tools/pcb/README.md`](../tools/pcb/README.md) (installed
tools).  This file only says how this directory is built and where the validated artifacts are.  Decisions live in
`docs/design-decisions.md` (D-01…D-49); requirement status in `docs/requirements.md` (R-01…R-44); the layout review in
`docs/design-review.md`; the bring-up plan in `docs/bring-up.md` (T-00…T-23).

## The five rules that matter most (v0.7)

1. **Never regenerate the PCB once hand routing has started.**  The main board is routed **by hand** (students in
   Workshop 2, instructor for the base/rails/SPI).  From the first track, `class-board.kicad_pcb` is the hand-edited
   master and `scripts/gen_pcb.py` is only a placement reference — running it would delete every track.  The
   schematic, by contrast, may be regenerated freely: UUIDs are deterministic (D-47), so identical inputs give a
   byte-identical file and every change diffs.
2. **A new circuit block is a new `scripts/sheet_*.py` module**, not an edit to the 1300-line `gen_sch.py`.  Each
   module exposes `build(root_uuid) -> Sheet` (picked up by `gen_sch.main()`) and a module-level `PLACEMENT` dict
   `{ref: (x, y, rot)}` (picked up by `gen_pcb.placement()` through `sheet_modules()`).  A module that fails to
   import is skipped with a printed note, so a broken module never blocks the build — **read the console output**.
   Existing modules: `sheet_nmr_rx.py` (section A, 7xx/9xx), `sheet_nmr_tx.py` (section B, 8xx),
   `sheet_c_switch.py` (section C, 9xx).
3. **Every symbol carries a `Block` field, and it decides which student owns the footprint.**  Values in use:
   `B1`, `OPT`, `NMR_RX` → section **A**; `B3`, `B5`, `NMR_TX` → section **B**; `B2`, `B4`, `C_SW` → section **C**;
   `BASE` → instructor (it is also the escape hatch for a part that serves two sections, e.g. the TCA9535 expander).
   The DRC rules `owner_A/B/C` assert `A.enclosedByArea('ZONE_A'|'ZONE_B'|'ZONE_C')`; a misplaced part is an
   assertion failure, not a silent error.
4. **The design rules live at the project root.**  KiCad reads `<project>.kicad_dru` from the project folder, so
   `class-board.kicad_dru` must exist there; `rules/class-board.kicad_dru` is the edit source and the two must stay
   identical (D-48).  Editing only the copy in `rules/` means the rules never run.  **Order matters**: KiCad
   applies the *last* matching rule, not the most specific one, so the specific blocks (the `mains_*` rules) come
   after the general ones — a generic `copper_to_edge` written later silently replaces a specific `mains_edge`
   (D-51).  No generator writes this file; it is hand-maintained.
5. **Footprints must be in KiCad 10 format** (`kicad-cli fp upgrade` on the library after any import) and the
   library nickname is `class_board:` — **never an `easyeda2kicad:` prefix** in a symbol's `Footprint` field.  After
   adding any footprint, run `python fix_courtyards.py` (courtyard = body ∪ pads + 0.25 mm, D-27) and then
   `place_check.py`, or the collision checks are blind.

## Layout of the directory

| Path | What |
|---|---|
| `class-board.kicad_pro/.kicad_sch`, `sheets/*.kicad_sch` | main board: root + 10 hierarchical sheets (`base_mcu`, `b1_inputs`, `b2_power`, `b3_outputs`, `b4_switching`, `b5_dio_trig`, `nmr_rx`, `nmr_tx`, `c_switch`, `front_panel_link`).  `opt_conditioning` was deleted in v0.7 (D-32) |
| `class-board.kicad_pcb`, `class-board.kicad_dru` | 4-layer main board **180 × 100 mm** and the custom DRC rules KiCad loads; `rules/class-board.kicad_dru` is the edit source |
| `front-panel/front-panel.kicad_*` | 2-layer front panel **180 × 100 mm** (D-50): 17 SMA (3 × 6 grid, one position empty), OLED, 3 LEDs, TTL screw strip, TX terminal, Qwiic; three 2×20 female headers on the inner face mate J6/J7/J8. Panel coordinates are mirrored in x against the main board (`panel x = 180 − main x`); its lib tables point at `../lib`, the KiCad standard footprints come from the global table |
| `lib/class_board.kicad_sym`, `lib/class_board.pretty/`, `lib/class_board.3dshapes/` | project-local library (one symbol per BOM line, LCSC/JLC fields; EasyEDA-derived footprints with rewritten courtyards) |
| `student/<sheet>_gapped.kicad_sch` (+ `.kicad_pro`) | student copies, three sections (brief §12); `docs/student-deletions.md` lists what was removed |
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

- Board coordinates: x right (0…180), y down; rear edge (USB-C, jack, terminals) at y = 0; front edge at y = 100.
  The panel stacks on the **back** of the board on three 2×20 headers (J6/J7/J8, B.Cu, centred on (12, 50) (90, 50)
  (168, 50), rotation 180 so pin 1 is at the rear); the panel is drawn from its outer face, so `gen_panel.py` mirrors
  x (`panel x = 180 − main x`, `panel y = main y`) and the main board's rear edge is the panel's top edge.
- Reference ranges: 1xx B1 · 2xx B2 · 3xx B3 · 4xx B4 · 5xx B5 · 6xx deleted OPT · **7xx clocks + receiver** ·
  **8xx DDS + transmitter** · **9xx mixer/IF, coil switches, external power**.
- A new part needs: a symbol in `cb_symbols.py` with its `LCSC`, library-type and `Datasheet` fields, a footprint in
  `lib/class_board.pretty/` (KiCad 10 format, courtyard rewritten), a `Block` field, a `PLACEMENT` entry, and a line
  in the design record (`docs/design-decisions.md`) with the datasheet number it comes from.
- A `sheet_*.py` module may fall back to a stand-in symbol with the right footprint while a value is missing from
  `cb_symbols.py`; it must then set a `SUBSTITUTE` field and print the substitution, so a stand-in cannot reach a BOM
  unnoticed.  Chase those prints down before ordering.
- Net classes and widths are in `gen_sch.write_project` (and mirrored in `router.py`, unused in v0.7):
  `Default`, `POWER_RAW`, `POWER`, `ANALOG_IN`, `ANALOG_OUT`, `FAST`, `ISO_IN` and — since D-51 — **`MAINS`**
  (5.0 mm clearance, 3.0 mm track) with the four channel classes **`MAINS1…MAINS4`**, which replace
  `RELAY_CONTACT`.  KiCad 10 puts a net in **every** class whose pattern matches, which is what lets a relay
  net be both MAINS and MAINS2.
- Analog/digital ground: everything in the receiver — tank, LNA, blanking switch, mixer switches, V_MID network, IF
  filters **and the 74HC74 divider** — is on AGND and +3V3A; the Si5351, the expander, the H-bridge, the polarizer and
  the OPA564 return are on GND; the two meet only at NT1.  Do not "tidy" a ground symbol from AGND to GND.
- Never hand-edit a file KiCad has open.  Google-Drive-hosted copies can corrupt `.git/index` — work in
  `C:\Claude\TIGP-2026\TIGP-board` and copy back.
- Secrets never enter this directory; `.local*`, `.route*`, `.*.json` scratch files are git-ignored.
