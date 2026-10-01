# The housing brief (Project 3: the housing)

You design the housing yourself, with Claude Code, from this page. There is no template to fill in and no example
housing to copy. Look at each board on its own first (below); then write your own specification in your own words,
end it with *"Ask me your questions before writing any code"*, answer the questions, and let Claude write
`housing.scad` in your folder `docs/students/<name>/housing/`. Then look at it, check the numbers, slice it, print the
test coupon, and make it yours.

## What the housing holds

- **Two printed circuit boards**, 180 × 100 × 1.6 mm each, stacked parallel **11 mm apart** (the gap between their
  facing surfaces: an 8.5 mm female header socket on a 2.5 mm male insulator), joined by three 2 × 20 pin headers and
  held by **M3 × 11 stand-offs** through the four mounting holes, 4 mm in from the corners.
- The instrument **lies flat**: the **front panel faces up** and is the face of the instrument; the **main board** is
  under it; the **ESP32 dev board**, plugged into the main board's other side, hangs **17 mm below** the main board.
- Through the panel's outer face: 16 SMA connectors, the OLED module, three LEDs, the Qwiic socket, the module header,
  and along the panel's far edge the TTL strip, the TX terminal and the two isolated-input terminals (their wires come
  from the side).
- The main board's rear edge is the back of the instrument: the dev board's USB-C socket, the DC jack, the external
  supply and the coil terminals, each needing an opening with room for the wire and the plug.
- The dev board's RESET and BOOT buttons are inside, so the housing has to open.

## The board models, and where they come from

Every dimension comes from the board models, none from a ruler. They are in `hardware/release/`:

| File | What | How it was made |
|---|---|---|
| `class-board.stl`, `front-panel.stl` | the two boards as light triangle meshes: the board body plus the connectors, LEDs and the OLED socket, nothing else, so OpenSCAD previews them in under a second | from the final KiCad board files with `kicad-cli pcb export stl --subst-models --component-filter "J*,D*"` (J = every connector, D = diodes and LEDs), converted to binary STL |
| `class-board.step`, `front-panel.step` | the same boards as exact STEP geometry for any CAD program, without the small passives and chips | `kicad-cli pcb export step --subst-models --component-filter ...` (connectors, power modules, relays, switches, crystals, fuses, transformers, LEDs; the panel: connectors and LEDs) |

**Open them one at a time before you write anything.** In your folder `docs/students/<name>/housing/`, a file
`boards.scad` with one line — `import("../../../../hardware/release/front-panel.stl");` — then F5 in OpenSCAD: the
front panel appears; drag to rotate, scroll to zoom; find the 16 SMA jacks, the OLED socket, the three LEDs and the
terminals along one edge. Change the file name to `class-board.stl` and save: the main board, with the three link
sockets, the dev-board sockets and the rear-edge connectors. The path is relative to the `.scad` file, so save the file
first; `Can't open import file` in the console means the path is wrong.

Facts about the models you will need: they are in **KiCad's frame**, whose y axis points **down**, so the boards lie at
x 0…180 and y −115…−15 with the board's top surface at z = 1.6 mm; the two boards mate with **panel x = 180 − main x**
(the panel is turned over onto the main board); the main board's link sockets are on its back, so in the housing it is
turned over (sockets up, dev board down). Heights above the panel's outer face, measured from the panel mesh: SMA jacks
9.8 mm (hexagonal base 0–2 mm, then the 6.35 mm threaded barrel) · module header 9.1 · TTL strip 8.8 · OLED module 13.8 ·
TX terminal 14.1 · Qwiic 4.3 · LEDs 1.0. Connector positions can be read from the meshes; the list at the end of this page
is for checking what Claude read.

## Rules for a part that prints

Walls and floor 2 mm; every hole drawn 0.3 mm larger than the part that goes through it; faces that touch the bed flat,
no overhang steeper than 45°, so the parts print without supports; fasteners are M3 screws into **nuts in hexagonal
pockets** (5.8 mm across flats, 2.5 mm deep, open to the side so the nut slides in); everything fits the printer's
256 × 256 × 256 mm. Print a **test coupon** first (holes 3.0–3.6 mm, one nut pocket, a wall of your thickness): it
answers the fit for this printer.

## Think these through before any code is written

- Leave space around every connector for its plug **and the hand that turns it**.
- The cover needs **two heights**: the OLED stands 13.8 mm above the panel face, but an SMA jack only 9.8 mm, and a
  plug nut can only screw onto a thread that comes through the cover. A plate resting on the OLED with holes over the
  SMAs leaves every thread 4 mm below the surface.
- The panel's silkscreen is hidden under the cover: **label the connectors on the front**, for example label text as
  cutouts in a printed plate with a white sheet (or a white printed sheet) behind it.
- **Screw and stand-off lengths set every height**: choose them with the cover and check them in a section view.

## How to work

The AI method: say what the housing is for and what it must hold; ask Claude to ask you its questions before it writes
code; have a fresh Claude session review the file against your specification; then look (rotate it, cut it open, the
boards drawn transparent with `%`), check the numbers (ask for `echo()` lines of the walls, holes, clearances and the
outer size), slice in Bambu Studio and read the supports preview, print the coupon. Never trust the model untested.

## What you hand in, by Fri 9 Oct, 2 pm

In `docs/students/<name>/housing/`: `housing.scad`; the STL of each printed part (for example `base.stl`, `cover.stl`,
`coupon.stl`); the DXF of any laser-cut plate; a screenshot `housing.png`; committed from Source Control. The class
prints and cuts everything together after the cutoff. A design in another CAD program you already use is welcome if it
fits the boards and meets the deadline.

## Connector positions, for checking what Claude read from the meshes

KiCad frame, mm. Main board, rear edge y = 15: USB-C J201 x 18.0 · DC jack J202 x 32.5 · terminals J901 x 49.9,
J903 x 64.3, J905 x 79.9 (3-pole). Mounting holes (4, 19) (176, 19) (4, 111) (176, 111) on both boards. Panel (its
own frame; in the housing x → 180 − x): SMA columns 75.65 + 18 n (n = 0…5), rows 25.67 and 43.67 (six each) and
61.67 (four: n = 0…3) · OLED J30 (151.05, 74.92) · LEDs x 116.5, y 86.95 / 89.90 / 92.85 · Qwiic J33 (121.05,
77.75) · module header J40 (40.1, 107.05) · TTL strip J31 (144.1, 111.0) · TX terminal J32 (110.85, 109.35) ·
isolated inputs J411 (86.85, 110.68), J412 (59.38, 110.61).
