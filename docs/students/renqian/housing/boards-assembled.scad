// Both boards in the positions they actually take in the instrument.
// A VIEWER ONLY - there is no housing in this file. Geometry from workbook/housing-brief.md.
//
//   "Two printed circuit boards, 180 x 100 x 1.6 mm each, stacked parallel 11 mm apart
//    (the gap between their facing surfaces)... the front panel faces up... the main board
//    is under it; the ESP32 dev board... hangs 17 mm below the main board."
//   "the two boards mate with panel x = 180 - main x (the panel is turned over onto the
//    main board); the main board's link sockets are on its back, so in the housing it is
//    turned over (sockets up, dev board down)."
//
// Everything is in KiCad's frame: x 0..180, y -115..-15 (y points DOWN), board body z 0..1.6.

GAP   = 11;      // mm between the two facing board surfaces (8.5 socket + 2.5 male insulator)
ALPHA = 1;       // 1 = solid. Drop to ~0.35 to see one board through the other.

REL = "../../../../hardware/release/";

// ---- front panel -----------------------------------------------------------
// Unchanged. Its outer face (SMA jacks, OLED, LEDs) already points +z = up;
// its link headers already hang below z = 0.
color("ForestGreen", ALPHA)
  import(str(REL, "front-panel.stl"));

// ---- main board ------------------------------------------------------------
// rotate([0,180,0]) maps (x,y,z) -> (-x, y, -z): the board is turned over about its
// vertical axis, which is what puts the link sockets up and the dev board down, and is
// also what produces the brief's "panel x = 180 - main x".
// Then translate: +180 brings x back into 0..180, -GAP drops it below the panel.
translate([180, 0, -GAP])
  rotate([0, 180, 0])
    color("DarkGreen", ALPHA)
      import(str(REL, "class-board.stl"));

// ---- the numbers this file assumes, printed to the console -----------------
echo(str("panel  bottom surface  z = 0"));
echo(str("main   top    surface  z = ", -GAP));
echo(str("gap between them       = ", GAP, " mm"));
echo(str("panel x <-> main x     : panel_x = 180 - main_x"));
echo(str("mounting holes         : (4,-19) (176,-19) (4,-111) (176,-111), same on both"));
