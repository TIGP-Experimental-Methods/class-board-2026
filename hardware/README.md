# hardware/ — the class board in KiCad 10

Spec: `10-Class-Board-Design-Brief.md` in the course repo (`…\2026\20260910-TIGP`). This folder is what the brief calls D1–D8.

```
hardware/
  lib/                      project library (D1): symbol/class_board.kicad_sym, class_board.pretty (as class_board/), packages3d/
                            generated from the BOM's LCSC numbers with JLC2KiCadLib (see lib/jlc2kicad_*.log); reviewed footprints only
  class-board.kicad_pro     ONE project (D2/D3)
  class-board.kicad_sch     root: interface table + sheet symbols
  sheets/                   base_mcu, b2_power, b1_inputs, b3_outputs, b4_switching, b5_dio_trig, opt_conditioning, front_panel_link
  class-board.kicad_pcb     4-layer main board with rule areas ZONE_BASE, ZONE_B1..B5, ZONE_OPT (owner-DRC in rules/)
  front-panel/              2-layer panel PCB (D4): 12 SMA at 20 mm, OLED header, 3 LEDs, 2x20 female link
  rules/class-board.kicad_dru   custom DRC (D7)
  student/                  gapped schematic copies per block (D6): b1_gapped.kicad_sch ... b5_gapped.kicad_sch
  jlc/                      Gerbers, drill, BOM.csv, CPL.csv, quote PDF per order (D5)
  AGENTS.md                 rules for the layout agent (GPT-Astra / Codex computer use)
```

## How to open
KiCad 10.0.x. Open `class-board.kicad_pro`. Libraries are project-local (`sym-lib-table`, `fp-lib-table` in this folder);
3D models resolve through the project path variable `CLASS_BOARD_3D` → `${KIPRJMOD}/lib/class_board/packages3d`.

## Who edits what
- Students: only inside their `ZONE_B<N>` on the PCB and only their `student/b<N>_gapped.kicad_sch`. One PR per deliverable.
- Layout agent: `astra-layout` branch, `AGENTS.md` rules, never the schematic.
- Instructor: everything else; merges student zones by *copy → Paste Special (in place)* of the tracks inside each `ZONE_B<N>`.

## Reference numbering (the owner-DRC depends on it)
base 1–99 · B1 100–199 · B2 200–299 · B3 300–399 · B4 400–499 · B5 500–599 · OPT 600–699. Keep the same references in the
gapped copies so footprints keep their positions after *Update PCB from schematic*.

## Order (Mon 2026-09-28)
JLCPCB Economic PCBA, SMD + THT, 5 assembled + 2 bare main boards (4-layer JLC04161H-7628), 6 assembled front panels (2-layer).
BOM columns: Comment, Designator, Footprint, LCSC Part #. CPL: Designator, Mid X, Mid Y, Layer, Rotation. DNP excluded.
