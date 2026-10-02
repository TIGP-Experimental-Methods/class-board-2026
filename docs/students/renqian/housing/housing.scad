// Housing - Ren Qian (Section A)
// Started 2026-10-02.
//   Step 1: a rectangular wall around the two boards.
//   Step 2: a boss at each of the four M3 mounting holes, merged into the wall.

include <BOSL2/std.scad>

$fa = 2; $fs = 0.4;

// ---- the numbers I chose -----------------------------------------------------
GAP      = 3;        // clear space between a board edge and the inner wall face
WALL     = 2;        // brief: walls and floor 2 mm
M3_CLEAR = 3.3;      // brief: every hole 0.3 mm larger than the part - M3 -> 3.3

SHOW_BOARDS = true;  // boards drawn with % for reference (% is excluded from STL export)

// ---- the numbers that come from the board meshes and the brief, not from me --
BX0 =    0;  BX1 =  180;      // both boards are 180 x 100 at x 0..180, y -115..-15
BY0 = -115;  BY1 =  -15;
HOLE_INSET = 4;               // brief: mounting holes 4 mm in from the corners
BOARD_GAP  = 11;              // brief: between the two facing board surfaces
PCB_T      = 1.6;             // board thickness
Z_TOP      =  15.70;          // top of the OLED module, the tallest thing on the panel
Z_BOT      = -23.40;          // underside of the ESP32 dev board, the lowest thing below

// ---- derived -----------------------------------------------------------------
BW    = BX1 - BX0;                      // 180
BD    = BY1 - BY0;                      // 100
ISIZE = [BW + 2*GAP, BD + 2*GAP];       // inner cavity: 186 x 106
OSIZE = [ISIZE.x + 2*WALL, ISIZE.y + 2*WALL];
H     = Z_TOP - Z_BOT;                  // 39.1
BOARD_CTR = [(BX0+BX1)/2, (BY0+BY1)/2];

// The main board's underside - the boss stops here so the board sits on it.
MAIN_UNDER = -(BOARD_GAP + PCB_T);      // -12.6
BOSS_H     = MAIN_UNDER - Z_BOT;        // 10.8

// A boss centred on its hole, reaching exactly to the inner wall faces, is
// 2 x (GAP + HOLE_INSET) square. It is then grown by WALL towards the two walls
// it meets, so it merges into them as one solid instead of touching face-to-face.
BOSS  = 2 * (GAP + HOLE_INSET);         // 14

HOLES = [ [BX0 + HOLE_INSET, BY1 - HOLE_INSET],     // (  4,  -19)
          [BX1 - HOLE_INSET, BY1 - HOLE_INSET],     // (176,  -19)
          [BX0 + HOLE_INSET, BY0 + HOLE_INSET],     // (  4, -111)
          [BX1 - HOLE_INSET, BY0 + HOLE_INSET] ];   // (176, -111)

// which way each hole faces its nearest walls
function wdir(h) = [ h.x < BOARD_CTR.x ? -1 : 1, h.y < BOARD_CTR.y ? -1 : 1 ];

// ---- the part ----------------------------------------------------------------
difference() {
  union() {
    // the wall
    translate([BOARD_CTR.x, BOARD_CTR.y, Z_BOT])
      rect_tube(h = H, isize = ISIZE, wall = WALL, anchor = BOTTOM);

    // the four bosses
    for (h = HOLES) {
      s = wdir(h);
      translate([h.x + s.x*WALL/2, h.y + s.y*WALL/2, Z_BOT])
        cuboid([BOSS + WALL, BOSS + WALL, BOSS_H], anchor = BOTTOM);
    }
  }

  // the screw runs the full height of each boss
  for (h = HOLES)
    translate([h.x, h.y, Z_BOT - 1])
      cylinder(d = M3_CLEAR, h = BOSS_H + 2);
}

// ---- the boards, for looking only --------------------------------------------
if (SHOW_BOARDS) {
  REL = "../../../../hardware/release/";
  %import(str(REL, "front-panel.stl"));
  %translate([180, 0, -BOARD_GAP]) rotate([0, 180, 0]) import(str(REL, "class-board.stl"));
}

// ---- check the numbers -------------------------------------------------------
echo(str("inner cavity   ", ISIZE.x, " x ", ISIZE.y, " mm   (boards ", BW, " x ", BD,
         ", gap ", GAP, " each side)"));
echo(str("outer size     ", OSIZE.x, " x ", OSIZE.y, " mm   (wall ", WALL, ")"));
echo(str("wall height    ", H, " mm   from z ", Z_BOT, " to z ", Z_TOP));
echo(str("boss           ", BOSS, " mm square, top at z ", MAIN_UNDER,
         " (main board underside), height ", BOSS_H));
echo(str("screw hole     ", M3_CLEAR, " mm through each boss"));
echo(str("material round the hole: ", (BOSS - M3_CLEAR)/2, " mm"));
echo(str("fits the 256 x 256 bed: ", (OSIZE.x <= 256 && OSIZE.y <= 256) ? "yes" : "NO"));
