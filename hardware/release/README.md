# hardware/release — the board models the housing work uses

| File | What | How it was made |
|---|---|---|
| `class-board.stl`, `front-panel.stl` | the two boards as light meshes (board body + connectors, LEDs, OLED socket), binary STL in KiCad's frame (y down, so y = -115..-15; top surface z = 1.6) | `kicad-cli pcb export stl --subst-models --define-var TIGP_BOARD_LIB=<hardware/lib> --component-filter "J*,D*"`, converted to binary |
| `class-board.step`, `front-panel.step` | the same boards as exact STEP geometry for a CAD program, without the small passives and chips (filter: connectors J*, power modules PS*, relays K*, switches SW*, crystals Y*, fuses F*, transformers T*, the LEDs; the panel: J* and its three LEDs) | `kicad-cli pcb export step --subst-models --define-var ... --component-filter ...` — without `--no-dnp`, because the DNP flag on this board means "hand-soldered, not fitted by the factory" (dev-board sockets, link connectors, module header), and the housing needs those bodies |

Two known gaps in these models (found 2026-10-16 when the housing hand-ins were checked; fixed at the next re-export): the ESP32-S3 dev board is absent, since the filter exports connectors and LEDs only, so allow for its body hanging about 17 mm below the main board (see `workbook/housing-brief.md`) when placing a floor; and the J901/J903 screw-terminal bodies in `class-board.stl` sit several millimetres too deep (a 3D-model offset in the KF301 footprint), while J905 and the panel's terminals are right, so take the J901/J903 heights from J905.

No housing files live here. Each student designs their own housing from `workbook/housing-brief.md` with Claude Code, in `docs/students/<name>/housing/`; the first step is to open each of these two models on its own in OpenSCAD (`import("../../../../hardware/release/front-panel.stl");` from that folder, F5) and look at it.

Re-export after a board change: the commands above, run from `hardware/`; the model paths resolve only with the `TIGP_BOARD_LIB` path variable (SETUP step 9) and after *Update Footprints from Library* (3D models) on the boards.
