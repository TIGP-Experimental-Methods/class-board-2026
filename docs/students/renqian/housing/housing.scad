// Housing - Ren Qian (Section A)
// Started 2026-10-02. Step 1: a rectangular wall around the two boards.

include <BOSL2/std.scad>

// ---- the numbers I chose -----------------------------------------------------
GAP   = 3;        // clear space between a board edge and the inner wall face
WALL  = 2;        // brief: walls and floor 2 mm

SHOW_BOARDS = true;   // draw the boards with % for reference (% is excluded from STL export)

// ---- the numbers that come from the board meshes, not from me ----------------
// Both boards are 180 x 100 and sit at x 0..180, y -115..-15 in KiCad's frame.
BX0 =    0;  BX1 =  180;
BY0 = -115;  BY1 =  -15;

// z extent of the assembled stack, measured off the two meshes with BOARD_GAP applied:
BOARD_GAP = 11;      // brief: between the two facing board surfaces
Z_TOP     =  15.70;  // top of the OLED module, the tallest thing on the panel
Z_BOT     = -23.40;  // underside of the ESP32 dev board, the lowest thing on the main board

// ---- derived -----------------------------------------------------------------
BW    = BX1 - BX0;                      // 180
BD    = BY1 - BY0;                      // 100
ISIZE = [BW + 2*GAP, BD + 2*GAP];       // inner cavity: 186 x 106
OSIZE = [ISIZE.x + 2*WALL, ISIZE.y + 2*WALL];
H     = Z_TOP - Z_BOT;                  // 39.1
BOARD_CTR = [(BX0+BX1)/2, (BY0+BY1)/2];     // 90, -65

// ---- the wall ----------------------------------------------------------------
// rect_tube gives the loop directly: inner size + wall thickness, no difference() needed.
// Add rounding = 3 for rounded outer corners; ichamfer / chamfer are there too.
translate([BOARD_CTR.x, BOARD_CTR.y, Z_BOT])
  rect_tube(h = H, isize = ISIZE, wall = WALL, anchor = BOTTOM);

// ---- the boards, for looking only --------------------------------------------
if (SHOW_BOARDS) {
  REL = "../../../../hardware/release/";
  %import(str(REL, "front-panel.stl"));
  %translate([180, 0, -BOARD_GAP]) rotate([0, 180, 0]) import(str(REL, "class-board.stl"));
}

// ---- check the numbers -------------------------------------------------------
echo(str("inner cavity  ", ISIZE.x, " x ", ISIZE.y, " mm   (boards ", BW, " x ", BD,
         ", gap ", GAP, " each side)"));
echo(str("outer size    ", OSIZE.x, " x ", OSIZE.y, " mm   (wall ", WALL, ")"));
echo(str("wall height   ", H, " mm   from z ", Z_BOT, " to z ", Z_TOP));
echo(str("fits the 256 x 256 bed: ", (OSIZE.x <= 256 && OSIZE.y <= 256) ? "yes" : "NO"));
