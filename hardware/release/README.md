# hardware/release — files the housing work uses

| File | What | How it was made |
|---|---|---|
| `class-board.stl`, `front-panel.stl` | the two boards as light meshes (board body + connectors, LEDs, OLED socket), binary STL in KiCad's frame (y down, so y = -115..-15; top surface z = 1.6) | `kicad-cli pcb export stl --subst-models --define-var TIGP_BOARD_LIB=<hardware/lib> --component-filter "J*,D*"`, converted to binary |
| `class-board.step`, `front-panel.step` | the same boards as exact STEP geometry for a CAD program, without the small passives and chips (filter: connectors J*, power modules PS*, relays K*, switches SW*, crystals Y*, fuses F*, transformers T*, the LEDs; the panel: J* and its three LEDs) | `kicad-cli pcb export step --subst-models --define-var ... --component-filter ...` — without `--no-dnp`, because the DNP flag on this board means "hand-soldered, not fitted by the factory" (dev-board sockets, link connectors, module header), and the housing needs those bodies |
| `housing.scad` | the reference OpenSCAD housing (base, cover, test coupon; `part` switch; Customizer variables; the two boards shown transparent), made from `workbook/housing-spec-card.md` before its two-height cover rule: this cover is one plate at 14 mm with 10 mm SMA holes, so the SMA nuts cannot be screwed on; a copy used as a fallback needs the low region around the SMAs (card, design notes) | written with Claude Code, checked by rendering |
| `base.stl`, `cover.stl`, `coupon.stl` | the printable parts, binary STL in mm | `openscad -o <part>.stl -D 'part="<part>"' housing.scad` |
| `cover.dxf` | the cover's outline with its holes, for the laser cutter (an acrylic cover instead of a printed one) | `openscad -o cover.dxf -D 'part="cover2d"' housing.scad` |

Re-export after a board change: the commands above, run from `hardware/`; the model paths resolve only with the `TIGP_BOARD_LIB` path variable (SETUP step 9) and after *Update Footprints from Library* (3D models) on the boards.
