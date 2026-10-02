// Housing - Ren Qian (Section A)
// 2026-10-02.
//   1 wall round the two boards   2 boss at each M3 hole   3 rear connector cutouts
//   4 floor                        5 M3 nut pockets
//
// Still to do: the cover (two heights - see the brief), the panel-face openings
// (16 SMA, OLED, LEDs, Qwiic, module header, TTL/TX/isolated terminals), labelling,
// and the test coupon.

include <BOSL2/std.scad>

$fa = 2; $fs = 0.4;

// ---- the numbers I chose -----------------------------------------------------
GAP        = 3;      // board edge -> inner wall face
WALL       = 2;      // brief: walls and floor 2 mm
M3_CLEAR   = 3.3;    // brief: holes 0.3 mm over the part. M3 -> 3.3
FLOOR_AIR  = 2;      // air under the lowest thing on the boards
NUT_AF     = 5.8;    // brief: nut across flats
NUT_DEEP   = 2.5;    // brief: pocket depth

PAD_USB    = 3.0;    // USB-C: the moulded boot is much wider than the socket
PAD_DC     = 2.5;    // barrel plug boot
PAD_TERM   = 1.0;

// The three screw terminals sit 2.7 and 3.4 mm apart, and their bodies stop 3.8 mm
// SHORT of the inner wall face - so a wire and a screwdriver have to reach in past
// the wall. Separate openings with usable access leave ribs of 0.7 / 1.4 mm, under
// the 2 mm rule, which will snap. One slot across all three is the way out; set
// false to go back to three openings and accept thin ribs.
TERM_SLOT  = true;

SHOW_BOARDS = true;

// ---- from the meshes and the brief -------------------------------------------
BX0 =    0;  BX1 =  180;
BY0 = -115;  BY1 =  -15;
HOLE_INSET = 4;
BOARD_GAP  = 11;
PCB_T      = 1.6;
Z_TOP      =  15.70;   // top of the OLED
Z_LOW      = -23.40;   // lowest thing under the main board (dev board / DC jack)

// KNOWN MODEL BUG 2026-10-02: J901/J903 are KF301-5.0-2P. eef00d2 fixed that
// footprint's 3D model (offset xyz 0 0 5) but re-exported the PANEL only;
// class-board.stl is from a4a88bc 10-01 19:51, so those two read 5 mm high.
// J905 is the 3P footprint and is correct. Set to 0 after a board re-export.
KF301_FIX = -5.0;

// ---- derived -----------------------------------------------------------------
BW = BX1-BX0;  BD = BY1-BY0;
ISIZE = [BW + 2*GAP, BD + 2*GAP];
OSIZE = [ISIZE.x + 2*WALL, ISIZE.y + 2*WALL];
BOARD_CTR = [(BX0+BX1)/2, (BY0+BY1)/2];

FLOOR_TOP = Z_LOW - FLOOR_AIR;      // -25.40
FLOOR_BOT = FLOOR_TOP - WALL;       // -27.40
H         = Z_TOP - FLOOR_BOT;      // total wall height

MAIN_UNDER = -(BOARD_GAP + PCB_T);  // -12.60
BOSS_H     = MAIN_UNDER - FLOOR_TOP;
BOSS       = 2 * (GAP + HOLE_INSET);

HOLES = [ [BX0+HOLE_INSET, BY1-HOLE_INSET], [BX1-HOLE_INSET, BY1-HOLE_INSET],
          [BX0+HOLE_INSET, BY0+HOLE_INSET], [BX1-HOLE_INSET, BY0+HOLE_INSET] ];
function wdir(h) = [ h.x < BOARD_CTR.x ? -1 : 1, h.y < BOARD_CTR.y ? -1 : 1 ];

// ---- rear connectors: x,z measured off class-board.stl after the transform ----
// [ name, x0, x1, z0, z1, pad, dz ]
REAR = TERM_SLOT
  ? [ ["USB-C J201",   157.5, 166.5, -14.18, -10.02, PAD_USB,  0],
      ["DC jack J202", 141.7, 152.5, -23.40,  -8.90, PAD_DC,   0],
      ["terminals",     88.8, 138.3, -22.60,  -4.15, PAD_TERM, KF301_FIX] ]
  : [ ["USB-C J201",   157.5, 166.5, -14.18, -10.02, PAD_USB,  0],
      ["DC jack J202", 141.7, 152.5, -23.40,  -8.90, PAD_DC,   0],
      ["term J901",    124.7, 138.3, -17.55,  -4.15, PAD_TERM, KF301_FIX],
      ["term J903",    110.7, 121.3, -17.55,  -4.15, PAD_TERM, KF301_FIX],
      ["term J905 3P",  88.8, 108.0, -22.60,  -8.40, PAD_TERM, 0] ];

REAR_Y = BY1 + GAP;

// ---- the part ----------------------------------------------------------------
difference() {
  union() {
    translate([BOARD_CTR.x, BOARD_CTR.y, FLOOR_BOT])
      rect_tube(h = H, isize = ISIZE, wall = WALL, anchor = BOTTOM);

    // floor
    translate([BOARD_CTR.x, BOARD_CTR.y, FLOOR_BOT])
      cuboid([ISIZE.x, ISIZE.y, WALL], anchor = BOTTOM);

    // bosses, standing on the floor
    for (h = HOLES) {
      s = wdir(h);
      translate([h.x + s.x*WALL/2, h.y + s.y*WALL/2, FLOOR_TOP])
        cuboid([BOSS+WALL, BOSS+WALL, BOSS_H], anchor = BOTTOM);
    }
  }

  // screw holes, right through boss and floor
  for (h = HOLES)
    translate([h.x, h.y, FLOOR_BOT - 1])
      cylinder(d = M3_CLEAR, h = BOSS_H + WALL + 2);

  // nut pockets at the bottom of each boss, open sideways so the nut slides in
  for (h = HOLES) {
    s = wdir(h);
    translate([h.x, h.y, FLOOR_TOP]) {
      cylinder(h = NUT_DEEP, d = NUT_AF/cos(30), $fn = 6);
      // the slide-in channel runs inwards, away from the two walls
      rotate([0, 0, atan2(-s.y, -s.x)])
        translate([0, -NUT_AF/2, 0]) cube([BOSS, NUT_AF, NUT_DEEP]);
    }
  }

  // rear cutouts - clamped so they never cut the floor
  for (c = REAR) {
    p = c[5]; dz = c[6];
    x0 = c[1]-p;  x1 = c[2]+p;
    z0 = max(c[3]+dz-p, FLOOR_TOP);  z1 = c[4]+dz+p;
    translate([(x0+x1)/2, REAR_Y + WALL/2, (z0+z1)/2])
      cuboid([x1-x0, 4*WALL + 20, z1-z0]);
  }
}

if (SHOW_BOARDS) {
  REL = "../../../../hardware/release/";
  %import(str(REL, "front-panel.stl"));
  %translate([180, 0, -BOARD_GAP]) rotate([0, 180, 0]) import(str(REL, "class-board.stl"));
}

// ---- check the numbers -------------------------------------------------------
echo(str("outer      ", OSIZE.x, " x ", OSIZE.y, " x ", H, " mm   (bed 256: ",
         (OSIZE.x<=256 && OSIZE.y<=256) ? "ok" : "NO", ")"));
echo(str("floor      z ", FLOOR_BOT, " .. ", FLOOR_TOP, "   air under the boards ", FLOOR_AIR));
echo(str("boss       ", BOSS, " sq, z ", FLOOR_TOP, " .. ", MAIN_UNDER, " (", BOSS_H, " tall)"));
echo(str("nut pocket ", NUT_AF, " af x ", NUT_DEEP, " deep, slides in from the inside"));
for (c = REAR) {
  p = c[5]; dz = c[6];
  echo(str("cutout ", c[0], "  x ", c[1]-p, "..", c[2]+p,
           "  z ", max(c[3]+dz-p, FLOOR_TOP), "..", c[4]+dz+p));
}
