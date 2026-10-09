// Housing - the test coupon. PRINT THIS FIRST.
// Ren Qian (Section A), 2026-10-02. Version 2, 2026-10-09.
//
// The brief: "Print a test coupon first (holes 3.0-3.6 mm, one nut pocket, a
// wall of your thickness): it answers the fit for this printer."
//
// Version 1 was drawn for version 1 of the housing, and by 2026-10-09 two of its
// three tests no longer matched what they were testing:
//   - its nut pocket had a flat roof and started on the bed. The base's pockets
//     now have 49 degree roofs and sit on a 2 mm floor. A flat roof sags and the
//     first layer squashes, so the old pocket could have said "the nut does not
//     fit" about a pocket that fits.
//   - its names were engraved in the top face. The cover's names are printed
//     FACE DOWN, in the first three layers, and filled with white.
// So version 2 stops copying the base and cuts a piece out of it instead.
//
// What is on it, and what each part answers:
//   1. A corner of the real base: base() itself, clipped to 20 x 20 x 10 round
//      the front-left screw. Floor, two walls of my thickness, the boss, its nut
//      pocket with the 49 degree roof, the side slot and the screw bore are the
//      base's own geometry, not a copy, so they cannot drift apart again. Does an
//      M3 nut slide in from the slot, and does it stay put while the screw
//      tightens? That answers NUT_AF.
//   2. Seven M3 holes, 3.0 to 3.6 in 0.1 steps, from the corner piece outward.
//      The smallest one an M3 screw passes through cleanly, by hand, is this
//      printer's answer for M3_CLEAR.
//   3. Three holes 6.6, 6.8 and 7.0 for the SMA barrels. SMA_D = 6.6 is the
//      brief's 0.3 over a 6.35 mm (1/4-36) thread, and the low cover has sixteen
//      of them that must all pass at once. Callipers answer it now; a real jack
//      answers it when the boards arrive.
//   4. Names, engraved ENGRAVE deep into the BOTTOM face and filled with white by
//      coupon_labels() - so they print exactly as the cover's do: face down,
//      first three layers. Turn the coupon over to read them. They are mirrored
//      in the file for that reason.
//        a ladder: "H-BRIDGE COIL", the hardest real name (B, R, D, G and E all
//          have gaps narrower than a stroke), at 2.6, 2.2 and 2.0, each tagged
//          with its size at 3.2. 2.2 is what the cover uses; 2.6 says whether
//          going up would fix it, 2.0 how much margin there is.
//        the other 2.2 names exactly as the cover has them, the "≤" included.
//        each hole labelled with its own size, also at 2.2.
//      Whichever is the smallest size still readable across a bench is the
//      floor for REAR_NAME_SIZE and the 2.2 entries in DECK_LABELS.
//
// Until this is printed and measured, M3_CLEAR, NUT_AF, FIT and SMA_D are
// assumptions.
//
// Defines coupon() and coupon_labels(); render them through housing.scad with
// PART = "coupon" or "coupon_labels", and load the two STLs as ONE object with
// two parts, exactly as for the cover halves.

include <BOSL2/std.scad>
include <housing-params.scad>
include <housing-shapes.scad>
include <housing-base.scad>

CL = 78; CW = 39;                         // the plate, WALL thick

// The base's front-left screw is HOLES[2] = (4, -111). Its boss and both walls
// lie inside x -5..11, y -120..-104; the 4 mm more in x and y keep the mouth of
// the nut slot, which leaves the boss on the diagonal into the tray.
CORNER   = [BX0 - GAP - WALL, BY0 - GAP - WALL];   // (-5, -120): the outer corner
CORNER_S = 20;
CORNER_H = 10;                            // floor 2 + pocket 2.5 + roof 3.35 + 2.15 solid

module base_corner()
  translate([-CORNER.x, -CORNER.y, -FLOOR_BOT])
    intersection() {
      base(engrave = false);
      translate([CORNER.x, CORNER.y, FLOOR_BOT]) cube([CORNER_S, CORNER_S, CORNER_H]);
    }

M3_X  = [for (i = [0:6]) 26 + 7*i];       // 3.0 .. 3.6
M3_Y  = 5;
SMA_HOLES = [6.6, 6.8, 7.0];
SMA_HX = [28, 44, 60];
SMA_HY = 16.5;

// [ text, size, x, y ] - x and y as seen in the file, from above. Every one is
// mirrored about its own centre, so turned over it reads the right way round in
// the same place. Turned over about the long edge, everything moves to the other
// end: the ladder ends up on the left, the corner piece on the right.
COUPON_NAMES = concat(
  [ ["2.6", 3.2, CL - 4.9, 35.2], ["H-BRIDGE COIL", 2.6, CL - 22.8, 35.2],
    ["2.2", 3.2, CL - 4.9, 30.9], ["H-BRIDGE COIL", 2.2, CL - 22.8, 30.9],
    ["2.0", 3.2, CL - 4.9, 26.6], ["H-BRIDGE COIL", 2.0, CL - 22.8, 26.6],
    ["COIL ≤24V",    2.2, CL - 48.4, 35.2], ["VEXT 7-18V", 2.2, CL - 67.7, 35.2],
    ["5V IN",        2.2, CL - 44.6, 30.9], ["USB-C 5V",   2.2, CL - 69.1, 30.9],
    ["PWR WIFI ACT", 2.2, CL - 51.4, 26.6] ],
  // written out, because str(3.0) is "3"
  [ for (i = [0:6]) [["3.0", "3.1", "3.2", "3.3", "3.4", "3.5", "3.6"][i],
                     2.2, M3_X[i], M3_Y + 4.3] ],
  [ for (i = [0:2]) [["6.6", "6.8", "7.0"][i], 2.2, SMA_HX[i] + 6.3, SMA_HY] ]
);

module coupon_engraving()
  translate([0, 0, -1]) linear_extrude(ENGRAVE + 1)
    for (N = COUPON_NAMES)
      translate([N[2], N[3]]) mirror([1, 0])
        text(N[0], size = N[1], halign = "center", valign = "center",
             font = "Liberation Sans:style=Bold");

module coupon(engrave = true) {
  difference() {
    union() {
      // The plate stops short of the corner piece, which brings its own floor.
      // A whole plate filled the base's screw bore through that floor - found by
      // sampling both meshes - so the screw would have bottomed out on it. The
      // 1 mm overlap is plain floor in both.
      difference() {
        cube([CL, CW, WALL]);
        translate([-1, -1, -1]) cube([CORNER_S, CORNER_S, WALL + 2]);
      }
      base_corner();
    }
    for (i = [0:6])
      translate([M3_X[i], M3_Y, -1]) cylinder(d = 3.0 + i/10, h = WALL + 2);
    for (i = [0:2])
      translate([SMA_HX[i], SMA_HY, -1]) cylinder(d = SMA_HOLES[i], h = WALL + 2);
    if (engrave) coupon_engraving();
  }
}

// What the engraving removed, for white: the same difference as the cover's.
module coupon_labels() difference() { coupon(engrave = false); coupon(); }
