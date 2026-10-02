// Housing - Ren Qian (Section A)
// Started 2026-10-02.
//   Step 1: a rectangular wall around the two boards.
//   Step 2: a boss at each of the four M3 mounting holes, merged into the wall.
//   Step 3: cutouts in the rear wall for the five rear-edge connectors.

include <BOSL2/std.scad>

$fa = 2; $fs = 0.4;

// ---- the numbers I chose -----------------------------------------------------
GAP      = 3;        // clear space between a board edge and the inner wall face
WALL     = 2;        // brief: walls and floor 2 mm
M3_CLEAR = 3.3;      // brief: every hole 0.3 mm larger than the part - M3 -> 3.3

// Clearance added all round each rear cutout. The plug is wider than the socket,
// so these are not the brief's 0.3 mm: they are "will the cable physically go in".
PAD_USB  = 3.0;      // USB-C: the moulded boot is far wider than the 8.9 x 4.2 socket
PAD_DC   = 2.5;      // barrel plug boot
PAD_TERM = 1.0;      // screw terminals: wire entry + screwdriver

SHOW_BOARDS = true;  // boards drawn with % (excluded from STL export)

// ---- from the board meshes and the brief, not from me ------------------------
BX0 =    0;  BX1 =  180;      // both boards 180 x 100 at x 0..180, y -115..-15
BY0 = -115;  BY1 =  -15;
HOLE_INSET = 4;               // brief: mounting holes 4 mm in from the corners
BOARD_GAP  = 11;              // brief: between the two facing board surfaces
PCB_T      = 1.6;
Z_TOP      =  15.70;
Z_BOT      = -23.40;

// KNOWN MODEL BUG, 2026-10-02. J901 and J903 are KF301-5.0-2P. Commit eef00d2
// fixed that footprint's 3D model ("raised 5 mm so the terminals sit on the
// board") but re-exported the PANEL only; class-board.stl is from a4a88bc,
// 10-01 19:51, so it still has the old model and those two read 5 mm high.
// J905 is the 3P footprint and is unaffected. Set to 0 once the board STL is
// re-exported - and check the mesh again rather than trusting this note.
KF301_FIX = -5.0;

// ---- derived -----------------------------------------------------------------
BW    = BX1 - BX0;
BD    = BY1 - BY0;
ISIZE = [BW + 2*GAP, BD + 2*GAP];
OSIZE = [ISIZE.x + 2*WALL, ISIZE.y + 2*WALL];
H     = Z_TOP - Z_BOT;
BOARD_CTR  = [(BX0+BX1)/2, (BY0+BY1)/2];
MAIN_UNDER = -(BOARD_GAP + PCB_T);
BOSS_H     = MAIN_UNDER - Z_BOT;
BOSS       = 2 * (GAP + HOLE_INSET);

HOLES = [ [BX0 + HOLE_INSET, BY1 - HOLE_INSET], [BX1 - HOLE_INSET, BY1 - HOLE_INSET],
          [BX0 + HOLE_INSET, BY0 + HOLE_INSET], [BX1 - HOLE_INSET, BY0 + HOLE_INSET] ];
function wdir(h) = [ h.x < BOARD_CTR.x ? -1 : 1, h.y < BOARD_CTR.y ? -1 : 1 ];

// ---- the five rear connectors ------------------------------------------------
// x and z measured off class-board.stl after the housing transform (panel x = 180 - main x).
// [ name, x0, x1, z0, z1, pad, dz ]
REAR = [
  ["USB-C J201",     157.5, 166.5, -14.18, -10.02, PAD_USB,  0],
  ["DC jack J202",   141.7, 152.5, -23.40,  -8.90, PAD_DC,   0],
  ["term J901",      124.7, 138.3, -17.55,  -4.15, PAD_TERM, KF301_FIX],
  ["term J903",      110.7, 121.3, -17.55,  -4.15, PAD_TERM, KF301_FIX],
  ["term J905 3P",    88.8, 108.0, -22.60,  -8.40, PAD_TERM, 0],
];

REAR_Y = BY1 + GAP;                 // -12, the inner face of the rear wall

// ---- the part ----------------------------------------------------------------
difference() {
  union() {
    translate([BOARD_CTR.x, BOARD_CTR.y, Z_BOT])
      rect_tube(h = H, isize = ISIZE, wall = WALL, anchor = BOTTOM);

    for (h = HOLES) {
      s = wdir(h);
      translate([h.x + s.x*WALL/2, h.y + s.y*WALL/2, Z_BOT])
        cuboid([BOSS + WALL, BOSS + WALL, BOSS_H], anchor = BOTTOM);
    }
  }

  for (h = HOLES)
    translate([h.x, h.y, Z_BOT - 1])
      cylinder(d = M3_CLEAR, h = BOSS_H + 2);

  // rear cutouts - cut right through the wall, and through the boss where they meet it
  for (c = REAR) {
    p = c[5]; dz = c[6];
    x0 = c[1] - p;  x1 = c[2] + p;
    z0 = c[3] + dz - p;  z1 = c[4] + dz + p;
    translate([(x0+x1)/2, REAR_Y + WALL/2, (z0+z1)/2])
      cuboid([x1-x0, 4*WALL + 20, z1-z0]);
  }
}

// ---- the boards, for looking only --------------------------------------------
if (SHOW_BOARDS) {
  REL = "../../../../hardware/release/";
  %import(str(REL, "front-panel.stl"));
  %translate([180, 0, -BOARD_GAP]) rotate([0, 180, 0]) import(str(REL, "class-board.stl"));
}

// ---- check the numbers -------------------------------------------------------
echo(str("inner cavity   ", ISIZE.x, " x ", ISIZE.y, "   outer ", OSIZE.x, " x ", OSIZE.y));
echo(str("wall height    ", H, "   z ", Z_BOT, " .. ", Z_TOP));
echo(str("boss           ", BOSS, " sq, top z ", MAIN_UNDER, ", ", M3_CLEAR, " hole"));
for (c = REAR) {
  p = c[5]; dz = c[6];
  echo(str("cutout ", c[0], "  x ", c[1]-p, "..", c[2]+p,
           "  z ", c[3]+dz-p, "..", c[4]+dz+p,
           "   (", (c[2]+p)-(c[1]-p), " x ", (c[4]+dz+p)-(c[3]+dz-p), ")",
           dz != 0 ? str("  [model shifted ", dz, "]") : ""));
}
// ribs left between neighbouring cutouts, and the clash with the near boss
echo(str("rib J905|J903  ", (110.7-PAD_TERM) - (108.0+PAD_TERM), " mm"));
echo(str("rib J903|J901  ", (124.7-PAD_TERM) - (121.3+PAD_TERM), " mm"));
echo(str("USB-C cutout reaches x ", 166.5+PAD_USB,
         " ; boss at x176 starts at ", (BX1-HOLE_INSET) - BOSS/2 - WALL,
         " -> material left beside that screw: ",
         (BX1-HOLE_INSET) - (166.5+PAD_USB) - M3_CLEAR/2, " mm"));
