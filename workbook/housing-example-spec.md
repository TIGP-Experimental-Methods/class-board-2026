# An example housing specification (Project 3b) — a backup, not the starting point

Write your own specification from the [housing brief](housing-brief.md) first; that is the exercise. This page is the
instructor's example, kept for two cases: you are stuck after a real attempt, or you want to see what a complete
specification looks like. The reference file `hardware/release/housing.scad` was produced from it (its cover is one plate
at 14 mm, before the two-height rule below; a copy used as a fallback needs the low region around the SMAs). To use the
reference file: copy it into your folder, change its two `import("...")` lines to the paths below
(`../../../../hardware/release/...`), and change its numbers in OpenSCAD's Customizer.

---

Design a 3D-printed housing for a two-board lab instrument in **OpenSCAD 2021.01**, plain language, no libraries. Write
one file, `housing.scad`, in the folder I am in (`docs/students/<name>/housing/`).

**What it holds.** Two printed circuit boards, 180 × 100 × 1.6 mm each, stacked parallel 11 mm apart (the gap between
their facing surfaces; M3 × 11 stand-offs through the four mounting holes 4 mm in from the corners). The instrument lies
flat: the **front panel faces up**, the main board is under it, and the dev board plugged into the main board hangs
below it by 17 mm. The board meshes exist: `../../../../hardware/release/class-board.stl` and `front-panel.stl`,
exported from KiCad with only the connectors, LEDs and the OLED on them, in KiCad's frame (x 0…180, y −115…−15 because
KiCad's y axis points down, board top surface at z = 1.6). Place them with exactly these two modules and show them
transparent; everything else in the housing is positioned relative to them:

```
z_panel_bot = -1.6;  z_main_top = z_panel_bot - 11;   // z = 0 is the panel's outer face
module main_board()  { translate([0, 0, z_main_top])  mirror([0, 1, 0]) mirror([0, 0, 1]) import("../../../../hardware/release/class-board.stl"); }
module front_panel() { translate([180, 0, z_panel_bot]) mirror([1, 0, 0]) mirror([0, 1, 0]) import("../../../../hardware/release/front-panel.stl"); }
```

(mirror y undoes KiCad's y-down; mirror z turns the main board over so its link sockets face the panel and the dev board
hangs below; mirror x on the panel is the link mating: panel x = 180 − main x.)

**Parts.** (1) A **base**: a tray with a floor and four walls, rounded vertical corners (3 mm), a 0.5 mm chamfer at the
bed, four bosses under the main board's mounting holes so that one M3 screw from below the floor passes through each boss
and the board into the stand-off; four **corner blocks** 8 × 8 mm with an **M3 nut pocket** each (hexagon 5.8 mm across
flats, 2.5 mm deep, open to the inside so the nut slides in) for the cover screws. (2) A **cover** over the panel at **two
heights**: around the 16 SMA jacks it sits low, its underside 2 mm above the panel face on the jacks' hexagonal bases, with
6.7 mm holes through which the 6.35 mm threaded barrels (2 mm to 9.8 mm above the panel face) protrude so that the plug
nuts screw on; over the OLED it is raised, its underside 14.0 mm above the panel face (resting on the OLED module,
13.8 mm); with holes for the four cover screws and the four stand-off screws and these cutouts: the OLED window; 2.5 mm
holes for the three LEDs; an opening for the Qwiic cable; an opening for the module header's plug (23 × 11 mm); openings
for the four screw terminals on the panel's far edge (their bodies pass through). (3) A **test coupon**: 60 × 20 × 4 mm
with holes 3.0, 3.2, 3.4, 3.6 mm, one M3 nut pocket and a wall of my wall thickness. Rear wall openings on the main
board's rear edge for the USB-C (10 × 4.5 mm), the DC jack (10 × 12), and the three screw terminals (12 × 12, 12 × 12,
17 × 12), at the connector positions you read from the mesh.

**Rules.** Wall and floor 2 mm; 6 mm clearance between board edge and inner wall (the corner blocks need it); 3 mm
under the lowest part of the dev board; every hole diameter + 0.3 mm; faces that touch the bed are flat and no overhang is
steeper than 45°, so the base prints open side up and the cover face down without supports. Everything must fit a
256 × 256 × 256 mm printer.

**How the file is written.** Every dimension is a named variable at the top with a Customizer comment
(`wall = 2; // [1.6:0.2:3]`). A variable `part = "all"; // [all, base, cover, cover2d, coupon, section]` selects what is
shown: `all` with the boards transparent, `section` cuts the model in half, `cover2d` is `projection(cut = true)` through
the cover for a DXF. Modules `base()`, `cover()`, `coupon()`. `echo()` lines print the outer size, the clearances, the
wall, the hole sizes and the nut pocket size.

**Design notes (think these through, and ask me about them, before any code is written).** Leave space around every connector for its plug and the hand that turns it. The cover needs **two heights**: the OLED module stands 13.8 mm above the panel face, but an SMA jack only 9.8 mm, and its threaded barrel (6.35 mm, from 2 mm to 9.8 mm above the panel face) must come through the cover or no plug nut can be screwed on; so the cover sits low around the SMAs and is raised over the OLED. The panel's silkscreen is hidden under the cover, so **label the connectors on the front**: for example a printed plate with the label text as cutouts and a white sheet, or a white printed sheet, behind it. **Screw and stand-off lengths set every height**: choose them with the cover, and check them in the section view. Heights above the panel face, measured from the panel mesh: SMA 9.8 mm · module header 9.1 · TTL strip 8.8 · OLED 13.8 · TX terminal 14.1 · Qwiic 4.3 · LEDs 1.0.

**Make it yours:** _(one change: a vent pattern, an embossed name on a wall, feet, a window, an acrylic lid instead of the
printed cover…)_

**Outputs.** `housing.scad`; then, from OpenSCAD, `base.stl`, `cover.stl`, `coupon.stl` (Render F6, Export STL, one
part at a time) and `cover.dxf` from `cover2d`.

**Ask me your questions before writing any code.**

---

*Connector positions on the boards (KiCad frame, mm), for checking what the AI read from the meshes:* main board rear
edge y = 15: USB-C J201 x 18.0 · DC jack J202 x 32.5 · terminals J901 x 49.9, J903 x 64.3, J905 x 79.9 (3-pole).
Mounting holes (4, 19) (176, 19) (4, 111) (176, 111) on both boards. Panel (its own frame; in the housing x → 180 − x):
SMA columns 75.65 + 18 n (n = 0…5), rows 25.67 and 43.67 (six each) and 61.67 (four: n = 0…3) · OLED J30 (151.05,
74.92) · LEDs x 116.5, y 86.95 / 89.90 / 92.85 · Qwiic J33 (121.05, 77.75) · module header J40 (40.1, 107.05) · TTL strip
J31 (144.1, 111.0) · TX terminal J32 (110.85, 109.35) · isolated inputs J411 (86.85, 110.68), J412 (59.38, 110.61).
