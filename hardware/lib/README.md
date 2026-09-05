# Class board library (the "library package")

Every part on the BOM, fetched from LCSC/EasyEDA with `easyeda2kicad` (46 parts: symbols named by manufacturer part number, 36 footprints, STEP + WRL for each). It is **project-local**: cloning the repo *is* installing it.

| File | What |
|---|---|
| `class_board.kicad_sym` | all symbols (fields: `LCSC Part`, `Datasheet`, `Manufacturer`) |
| `class_board.pretty/` | footprints; 3D model paths are `${KIPRJMOD}/lib/class_board.3dshapes/…` |
| `class_board.3dshapes/` | STEP + WRL per footprint |
| `../sym-lib-table`, `../fp-lib-table` | the project tables that register `class_board` (next to the `.kicad_pro`) |
| `lcsc_codes.txt`, `e2k_done.txt`, `fetch_missing.sh`, `*.log` | how it was generated; rerun `fetch_missing.sh` to fetch anything new in `lcsc_codes.txt` |

**Students (E4):** open `hardware/class-board.kicad_pro`; *Preferences → Manage Symbol Libraries → Project Specific* lists `class_board`. Nothing to unzip. **E8:** add your one part with
```sh
easyeda2kicad --full --lcsc_id C12072 --output "<absolute path to>/hardware/lib/class_board"
```
then set its footprint field and commit `hardware/lib/`.

**Instructor review before the schematic gate (design brief §11):** every IC footprint checked against its datasheet (pin 1, pitch, pad size) — `TODO`; the 74LVC1T45 and 1×4 OLED header C-numbers are still TBD (design brief §13).

Generated 2026-09-06. Lesson learned: `easyeda2kicad` exits 1 on "already exists" — judge success by the LCSC id appearing in the `.kicad_sym`, not by the exit code; pace requests ≥ 25 s apart (EasyEDA 403s after ~15 quick calls).
