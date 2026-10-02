# HANDOVER — Project 3 housing (shaynebennetts)

For a Claude session picking this up cold. Written 2026-10-02 at the end of `/tutor L3`.
Deadline for the housing files: **Fri 9 Oct 2026, 2 pm** (hard cutoff, workbook ch. 3).

**Resume:** in `class-board-2026` on branch `w1-shaynebennetts`, run `/tutor HW3` (the between-workshops part of ch. 3),
read this file and `../PROGRESS.md`, open `PrintView.scad` for the user, and run `check_housing.py` after any change.
Everything below is committed and pushed (class repo `w1-shaynebennetts`, `class-board-instrument` `main`, wall `main`).

## What exists

One parametric OpenSCAD 2021.01 model, `CompleteHousing.scad`, for the class board sandwich (front panel face up,
main board turned over 11 mm below it, ESP32-S3 dev board hanging from the main board's sockets). Five printed parts
and one laser-cut part, all exported in print orientation to `export/`:

| Part | `part =` | Export | Process |
|---|---|---|---|
| Base: four walls, corner columns, board bosses, rear openings, front wire notches, engraved labels | `base` | `base.stl` | print, bottom edge down, single colour |
| Top cover: 2 mm plate on the wall top | `cover` + `cover_labels` | `cover.stl` + `cover_labels.stl` | print face down, two colours (labels = first 2 layers) |
| SMA plate: flat, sits in the cover's SMA opening | `sma` + `sma_labels` | `sma_plate.stl` + `sma_labels.stl` | print plate down, two colours (labels = top 2 layers) |
| OLED housing: four walls + 2 mm top, bolted through the OLED's M2 holes | `oled` | `oled_housing.stl` | print face down, single colour |
| Bottom lid | `lid2d` | `bottom_lid_3mm.dxf` | laser cut, 3 mm acrylic |

`check_housing.py` re-runs the fit checks (see *How changes were checked*).
Viewer files (each `include`s the main file, so they follow every change): `PrintView.scad` (all printed parts laid
out as on the plate — the user likes this one), `CoverView.scad`, `OledView.scad`. `export/export.scad` regenerates
every export from the command line (see its header). `housing.png` is the course screenshot. `models/` holds the
dev-board mesh (`YD-ESP32-S3.stl`, MIT, from github.com/shkuznetsov/YD-ESP32-S3; the 20 MB STEP is git-ignored —
re-download it from there if needed; FreeCAD 1.1 `freecadcmd` converted it).

## Project 3 repository, website and wall card (created 2026-10-02)

- Repository: https://github.com/shaynebennetts/class-board-instrument (public; local clone `C:\Claude\TIGP-2026-2\class-board-instrument`,
  next to `class-board-2026`; listed in the parent folder's `.gitignore` like the other project repositories).
- Website: https://shaynebennetts.github.io/class-board-instrument/ (GitHub Pages, `main`, `/`). `index.html` introduces the
  board and the housing and has a **Files** section linking every OpenSCAD and production file in this folder (blob = view,
  raw = download, on branch `w1-shaynebennetts`). **If files here are renamed or moved, those links break** — check them with curl.
- Pictures: `images/` there, re-rendered by `tools/make_renders.sh` (`tools/render_views.scad` includes this model by a
  relative path, so the two repositories must stay side by side; `tools/make_gif.py` builds the turntable GIF).
- Wall card: `showcase-2026/projects/shaynebennetts--class-board-instrument.json` + `images/shaynebennetts--class-board-instrument.gif`
  (`project` `"3"`, `live_url` empty until there is an app). Update `blurb`, `image` and `updated` as the project moves on.
- The user wants these files public **as an example for students**. That reverses Decision #80 in `tutor/COURSE-GUIDE.md`
  and workbook ch. 3 ("no reference housing anywhere, the tutor never writes one"); the guide still says so — the
  instructor's to update.
- The page says the housing is designed, not printed, and that firmware, app and measurements follow. Update it then.

Two-colour printing in Bambu Studio: drag a part and its `_labels` STL in together, answer **Yes** to "load as a single
object with multiple parts", give the labels the white filament. The pairs share one coordinate frame.

## The frame (read before touching coordinates)

KiCad's frame as the meshes in `hardware/release/` come: y negated (board y −115..−15), x 0..180.
Front panel: imported as is, lifted by `stack` = 11 → panel top face `z_top` = 12.6. Panel KiCad (x, y) = housing (x, −y).
Main board: `translate([180,0,0]) rotate([0,180,0])` → its underside up at z = 0, KiCad x → 180 − x, z → −z.
Rear openings are written in the main board's own frame and flipped in `rear_slot()`.
Dev board: `multmatrix` in `devboard()`, header plastic on the socket tops at z = −10.1.

## Numbers and where they came from (all measured, none guessed unless marked)

- Board extents, link headers, connector bodies and heights: `front-panel.stl` / `class-board.stl` (vertex clustering).
- Positions of holes, pads, screws: the KiCad files (`hardware/class-board.kicad_pcb`, `hardware/front-panel/front-panel.kicad_pcb`).
- Labels: silkscreen **and** copper — every SMA centre pin, LED, TTL pin, terminal pole checked against its pad net and
  traced through the link headers (panel J1/J2/J3 ↔ main J6/J8/J7) to the same net on the main board.
- SMA jacks: square base 6.5 mm, 1.8 mm tall; barrel 6.35 (1/4-36) to 9.8 mm. The SMA plate rests on the base corners.
- OLED: footprint J30 gives the module outline, the glass (26.7 × 19.3) and four 2.4 mm holes for M2 at 24 × 26.
  The 3D model is a plain 13.82 mm block, so the clash test always reports its 4 top corners touching the OLED bosses.
- Dev board: Jinhua #40729 = VCC-GND YD-ESP32-S3 (57.15 × 27.94). Port identity from the user: **COM** on the buttons'
  side (model z −5.65, housing y −63.15), **USB** on the regulator's side (z +5.85, y −74.65).
- 3D-model quirks: the DC jack model sits 2.35 mm off its pin pads in x (the hole follows the **model**, user's call);
  the J901/J903 terminal models sit ~2.7 mm low (sizes taken from J905, which sits right).

## User's decisions this session (keep them)

- Wall 3 mm; 3 mm board gap front/rear, `gap_x` = 11.5 at the ends so the lid supports pass beside the board.
- Walls end 5 mm past the dev board (`below_dev`) and 5 mm above the panel face (`wall_top`); the cover is a plate on them.
- All nut pockets open at **45 degrees** into the box (shared `nut_pocket()`); M3 nut pockets 0.3 mm all round,
  lid pockets 0.8 mm extra height; board bosses hold **two nuts stacked** in one pocket (5.6 mm).
- Lid screw holes 8 mm from the outer edges; corner columns run full height (print without support under them).
- Rear openings are rounded slots/holes: USB 16 × 10, DC 11, terminal slots 6 mm high.
- Top cover 2 mm; OLED gets its own housing; SMA field is a separate flat piece; labels white inlay 0.4 mm on top
  pieces, engraved 0.6 mm on walls.
- SMA plate: 0.5 mm placement tolerance on every jack (`sma_tol`): holes 7.65, edge gap 0.8; verified with the plate
  shifted 0.5 mm in 8 directions (no clash, every jack keeps 4 base corners under the plate, lip top = cover underside 17.6).

## Open items

1. **Main board dev-board socket spacing is 25.0 mm; the YD-ESP32-S3 rows are 25.4 mm** (footprint and model).
   The board is not ordered; the user said "we can bump it": move J1 to y 81.5 and J2 to y 56.1 in KiCad and reroute.
   The housing already assumes 25.4 (centre 68.8 unchanged).
2. DC jack hole is on the model axis, 2.35 mm off the pads — measure the real jack before printing.
3. OLED display window and glass thickness (`oled_win`, `oled_glass` = 1.5) are from the footprint / a typical module — check.
4. The LED well in the cover is the only feature that needs a (small, paint-on) support.
5. Panel silkscreen says module header pin 10 is spare, but the copper routes MODOUT8 there.
6. Course checklist items not done: the test coupon (`coupon.stl`: holes 3.0–3.6, an M3 pocket, a wall), slicing in
   Bambu Studio (time, grams). E11 (drivers + panels in sim, a pull request) not started.
7. Screws: board M3 × 6 or × 7 (never × 8 — the tips meet), lid M3 × 10, cover M3 × 8 button head, OLED M2 (~× 8, check).

## How changes were checked (repeat after any edit)

- Render with `openscad.com` (no warnings) and look at the PNG.
- `check_housing.py` in this folder runs all three checks in a few minutes and prints the expected result beside each:
  `uv run --with trimesh --with numpy --with rtree python check_housing.py`
  1. clash test — every vertex of the three board meshes tested for containment in each part (expected 0, except
     OLED 4 = block-model corners and SMA 64 = base corners the plate rests on);
  2. inlay test — points just inside each label must not be inside its host part (0);
  3. SMA plate shifted 0.5 mm in 8 directions — no clash, 4 of 4 base corners supported, heights 14.40 / 17.60.
  Last run 2026-10-02: all as expected. Its board transforms must stay in step with `boards()` / `devboard()`.
- Then re-export with `export/export.scad` (header has the command line) and check the links on the project page.

## Gotchas (cost real time this session)

- **Never write this file with Python's default `open(p, "w")` on Windows** — it encodes cp1252; a non-ASCII character
  made it raise mid-write and the file was left **empty**. It was rebuilt and verified against earlier STL exports.
  Use the Edit tool or `open(p, "w", encoding="utf-8")`; the file is ASCII-only now (the minus sign is `"−"`).
- OpenSCAD top-level variables are evaluated in order: a variable used by another must be defined above it
  (module bodies are fine).
- Relative import paths only work once the `.scad` file is saved in this folder; the user opens files from here.
- **A relative `import()` inside an included file is resolved from the top-level file's folder**, not the included file's.
  The view files sit next to `CompleteHousing.scad`, so they work; a file elsewhere that includes it (e.g. a render
  script) must re-import the meshes with its own paths (see `class-board-instrument/tools/render_views.scad`).
  `export/export.scad` is one folder down but only exports parts that import nothing.
- The model was moved here from `class-board-2026/housing/` (absolute paths, untracked) on 2026-10-02; that empty folder
  may still exist while an old OpenSCAD window holds it — delete it, never edit there.
- Background bash: a bare `cat > file` without a heredoc waits for stdin forever.
