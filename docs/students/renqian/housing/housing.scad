// Housing - Ren Qian (Section A)
// 2026-10-02.  One file, three printed parts: set PART below.
//
//   base    tray: wall, floor, four M3 bosses with nut pockets, rear connector cutouts
//   cover   two heights: a low deck over the SMA field so the threads come through,
//           a raised deck over the OLED / TX terminal end
//   coupon  the fit test: holes 3.0-3.6, one nut pocket, a wall of my thickness
//
// Still to do: the remaining panel-face openings (LEDs, Qwiic, module header, TTL
// strip, the two isolated terminals), labelling, and cover.dxf.

include <BOSL2/std.scad>
$fa = 2; $fs = 0.4;

PART = "base";          // "base" | "cover" | "coupon"

// ---- my numbers --------------------------------------------------------------
GAP       = 3;          // board edge -> inner wall face
WALL      = 2;          // brief: walls and floor 2 mm
M3_CLEAR  = 3.3;        // brief: holes 0.3 over the part
FLOOR_AIR = 2;          // air under the lowest thing on the boards
NUT_AF    = 5.8;        // brief: nut across flats
NUT_DEEP  = 2.5;
FIT       = 0.3;        // brief's general clearance

PAD_USB   = 3.0;        // USB-C moulded boot
PAD_DC    = 2.5;
PAD_TERM  = 1.0;
TERM_SLOT = true;       // one slot for the three rear terminals - see the note below

// ---- from the meshes and the brief -------------------------------------------
BX0 =    0;  BX1 =  180;
BY0 = -115;  BY1 =  -15;
HOLE_INSET = 4;
BOARD_GAP  = 11;
PCB_T      = 1.6;
FACE       = PCB_T;     // 1.6 - the panel's outer face
Z_LOW      = -23.40;    // lowest thing under the main board

// measured off front-panel.stl: the only two things taller than the SMA threads
OLED  = [[137.5, -101.6], [164.6, -72.7], 15.42];   // 27.0 x 29.0, 13.82 above the face
TXT   = [[105.6, -114.7], [115.8, -104.1], 15.70];  // 10.3 x 10.6, 14.10 above the face
SMA_TOP = 11.40;        // top of an SMA jack  (9.8 above the face)
SMA_HEX = FACE + 2.0;   // brief: hex base 0-2 mm, then the threaded barrel
SMA_D   = 6.6;          // barrel + FIT; the brief's 6.35 thread is inside this

// SMA grid, panel frame (= this frame): columns 75.65 + 18n, three rows
SMA_X = [for (i = [0:5]) 75.65 + 18*i];
SMA_ROWS = [-25.67, -43.67, -61.67];        // rows 1,2 have six; row 3 has four

// The brief splits the rest in two. "Through the panel's outer face": these get a
// hole in the top of the raised deck. All measured off front-panel.stl.
// [ name, x0, x1, y0, y1 ]
PANEL_TOP = [
  ["LEDs D1-D3",   115.4, 117.5,  -93.5,  -86.3],   // 1.00 above the face
  ["Qwiic J33",    119.2, 122.8,  -80.8,  -74.8],   // 4.32
  ["module hdr J40", 22.3, 45.2, -113.0, -103.9],   // 9.10
];

// "along the panel's far edge ... their wires come from the side": these get a
// notch in the far wall instead. [ name, x0, x1, z top ]
FAR_SIDE = [
  ["iso J412",      54.4,  66.1, 11.55],
  ["iso J411",      81.8,  93.8, 11.55],
  ["TX term J32",  105.6, 115.8, 15.70],
  ["TTL strip J31", 131.4, 156.8, 10.40],
];

// KNOWN MODEL BUG 2026-10-02: J901/J903 are KF301-5.0-2P. eef00d2 fixed that
// footprint's 3D model (offset xyz 0 0 5) but re-exported the PANEL only, so
// class-board.stl (a4a88bc, 10-01 19:51) still reads them 5 mm high. J905 is 3P
// and correct. Set to 0 after the board STL is re-exported.
KF301_FIX = -5.0;

// ---- the two cover heights ---------------------------------------------------
// The split: the SMA field is at y > -70, everything tall is at y < -70.
SPLIT_Y   = -70;
COVER_SIT = SMA_HEX + FIT;                 // 3.9 - the wall top, just over the hex bases
LOW_TOP   = COVER_SIT + WALL;              // 5.9 - SMA threads stand 5.5 mm proud of this
HIGH_IN   = max(OLED[2], TXT[2]) + 0.5;    // 16.2 - clears the TX terminal
HIGH_TOP  = HIGH_IN + WALL;                // 18.2

// ---- derived -----------------------------------------------------------------
BW = BX1-BX0;  BD = BY1-BY0;
ISIZE = [BW + 2*GAP, BD + 2*GAP];
OSIZE = [ISIZE.x + 2*WALL, ISIZE.y + 2*WALL];
CTRB  = [(BX0+BX1)/2, (BY0+BY1)/2];

FLOOR_TOP = Z_LOW - FLOOR_AIR;
FLOOR_BOT = FLOOR_TOP - WALL;
WALL_H    = COVER_SIT - FLOOR_BOT;

MAIN_UNDER = -(BOARD_GAP + PCB_T);
BOSS_H     = MAIN_UNDER - FLOOR_TOP;
BOSS       = 2*(GAP + HOLE_INSET);

HOLES = [ [BX0+HOLE_INSET, BY1-HOLE_INSET], [BX1-HOLE_INSET, BY1-HOLE_INSET],
          [BX0+HOLE_INSET, BY0+HOLE_INSET], [BX1-HOLE_INSET, BY0+HOLE_INSET] ];
function wdir(h) = [ h.x < CTRB.x ? -1 : 1, h.y < CTRB.y ? -1 : 1 ];

REAR = TERM_SLOT
  ? [ ["USB-C J201",   157.5, 166.5, -14.18, -10.02, PAD_USB, 0],
      ["DC jack J202", 141.7, 152.5, -23.40,  -8.90, PAD_DC,  0],
      ["terminals",     88.8, 138.3, -22.60,  -4.15, PAD_TERM, KF301_FIX] ]
  : [ ["USB-C J201",   157.5, 166.5, -14.18, -10.02, PAD_USB, 0],
      ["DC jack J202", 141.7, 152.5, -23.40,  -8.90, PAD_DC,  0],
      ["term J901",    124.7, 138.3, -17.55,  -4.15, PAD_TERM, KF301_FIX],
      ["term J903",    110.7, 121.3, -17.55,  -4.15, PAD_TERM, KF301_FIX],
      ["term J905 3P",  88.8, 108.0, -22.60,  -8.40, PAD_TERM, 0] ];
REAR_Y = BY1 + GAP;

// =============================================================================
module base() {
  difference() {
    union() {
      translate([CTRB.x, CTRB.y, FLOOR_BOT])
        rect_tube(h = WALL_H, isize = ISIZE, wall = WALL, anchor = BOTTOM);
      translate([CTRB.x, CTRB.y, FLOOR_BOT])
        cuboid([ISIZE.x, ISIZE.y, WALL], anchor = BOTTOM);
      for (h = HOLES) {
        s = wdir(h);
        translate([h.x + s.x*WALL/2, h.y + s.y*WALL/2, FLOOR_TOP])
          cuboid([BOSS+WALL, BOSS+WALL, BOSS_H], anchor = BOTTOM);
      }
    }
    for (h = HOLES)
      translate([h.x, h.y, FLOOR_BOT-1]) cylinder(d = M3_CLEAR, h = BOSS_H+WALL+2);
    for (h = HOLES) {
      s = wdir(h);
      translate([h.x, h.y, FLOOR_TOP]) {
        cylinder(h = NUT_DEEP, d = NUT_AF/cos(30), $fn = 6);
        rotate([0,0,atan2(-s.y,-s.x)]) translate([0,-NUT_AF/2,0]) cube([BOSS,NUT_AF,NUT_DEEP]);
      }
    }
    for (c = REAR) {
      p = c[5]; dz = c[6];
      x0 = c[1]-p; x1 = c[2]+p;
      z0 = max(c[3]+dz-p, FLOOR_TOP); z1 = c[4]+dz+p;
      translate([(x0+x1)/2, REAR_Y+WALL/2, (z0+z1)/2]) cuboid([x1-x0, 4*WALL+20, z1-z0]);
    }
  }
}

// =============================================================================
module cover() {
  difference() {
    union() {
      // low deck over the SMA field
      translate([CTRB.x, (SPLIT_Y + BY1 + GAP)/2, COVER_SIT])
        cuboid([OSIZE.x, (BY1+GAP) - SPLIT_Y, WALL], anchor = BOTTOM);
      // raised box over the OLED / TX terminal end
      translate([CTRB.x, (SPLIT_Y + BY0 - GAP)/2, COVER_SIT])
        cuboid([OSIZE.x, SPLIT_Y - (BY0-GAP), HIGH_TOP - COVER_SIT], anchor = BOTTOM);
    }
    // hollow the raised box
    translate([CTRB.x, (SPLIT_Y + BY0 - GAP)/2, COVER_SIT - 1])
      cuboid([OSIZE.x - 2*WALL, SPLIT_Y - (BY0-GAP) - 2*WALL, HIGH_IN - COVER_SIT + 1],
             anchor = BOTTOM);
    // SMA barrels come through the low deck
    for (r = [0:2]) for (i = [0 : (r == 2 ? 3 : 5)])
      translate([SMA_X[i], SMA_ROWS[r], COVER_SIT-1]) cylinder(d = SMA_D, h = WALL+2);
    // window over the OLED
    translate([(OLED[0].x+OLED[1].x)/2, (OLED[0].y+OLED[1].y)/2, HIGH_IN-1])
      cuboid([OLED[1].x-OLED[0].x - 2*FIT, OLED[1].y-OLED[0].y - 2*FIT, WALL+2], anchor=BOTTOM);
    // the TX terminal pokes out of the top
    translate([(TXT[0].x+TXT[1].x)/2, (TXT[0].y+TXT[1].y)/2, HIGH_IN-1])
      cuboid([TXT[1].x-TXT[0].x + 2*FIT, TXT[1].y-TXT[0].y + 2*FIT, WALL+2], anchor=BOTTOM);
    // "through the panel's outer face": holes in the top of the raised deck
    for (c = PANEL_TOP)
      translate([(c[1]+c[2])/2, (c[3]+c[4])/2, HIGH_IN-1])
        cuboid([c[2]-c[1] + 2*FIT, c[4]-c[3] + 2*FIT, WALL+2], anchor = BOTTOM);

    // "their wires come from the side": a notch in the far wall for each,
    // from the cover's seating face up to just over the part
    // A notch whose top would land within WALL of the raised deck leaves an
    // unprintable sliver of wall above it (the TX terminal does: 15.70 + FIT
    // against an inner face at HIGH_IN), so those run out through the top edge.
    for (c = FAR_SIDE) {
      ztop = (c[3] + FIT > HIGH_IN - WALL) ? HIGH_TOP + 1 : c[3] + FIT;
      translate([(c[1]+c[2])/2, BY0 - GAP, (COVER_SIT - 1 + ztop)/2])
        cuboid([c[2]-c[1] + 2*FIT, 2*WALL + 4, ztop - (COVER_SIT - 1)]);
    }

    // the four screws
    for (h = HOLES) translate([h.x, h.y, COVER_SIT-1]) cylinder(d = M3_CLEAR, h = HIGH_TOP+2);
  }
}

// =============================================================================
module coupon() {
  L = 62; W = 26;
  difference() {
    union() {
      cuboid([L, W, WALL], anchor = BOTTOM);                       // the plate
      translate([0, W/2 - WALL/2, 0]) cuboid([L, WALL, 10], anchor = BOTTOM);  // a wall of my thickness
      translate([L/2 - 11, -W/2 + 9, 0]) cuboid([18, 16, NUT_DEEP + WALL], anchor = BOTTOM);
    }
    // holes 3.0 .. 3.6 in 0.1 steps - which one takes an M3 on THIS printer
    for (i = [0:6])
      translate([-L/2 + 6 + i*7, -2, -1]) cylinder(d = 3.0 + i*0.1, h = WALL+2);
    // one nut pocket, exactly as the base has it
    translate([L/2 - 11, -W/2 + 9, 0]) {
      translate([0,0,-1]) cylinder(d = M3_CLEAR, h = NUT_DEEP+WALL+2);
      cylinder(h = NUT_DEEP, d = NUT_AF/cos(30), $fn = 6);
      translate([0, -NUT_AF/2, 0]) cube([20, NUT_AF, NUT_DEEP]);
    }
  }
}

// =============================================================================
if (PART == "base")   base();
if (PART == "cover")  cover();
if (PART == "coupon") coupon();
// flat outline of the cover, for the DXF (a laser-cut plate, if you go that way)
if (PART == "cover2d") projection(cut = false) cover();

echo(str("PART = ", PART));
echo(str("base   outer ", OSIZE.x, " x ", OSIZE.y, " x ", COVER_SIT-FLOOR_BOT,
         "   bed 256: ", (OSIZE.x<=256 && OSIZE.y<=256) ? "ok" : "NO"));
echo(str("cover  sits at z ", COVER_SIT, "  low deck top ", LOW_TOP,
         "  raised top ", HIGH_TOP));
echo(str("SMA thread proud of the low deck: ", SMA_TOP - LOW_TOP, " mm"));
echo(str("raised deck inner z ", HIGH_IN, " clears TX terminal ", TXT[2],
         " by ", HIGH_IN - TXT[2]));
echo(str("coupon holes 3.0..3.6 step 0.1, nut pocket ", NUT_AF, " af x ", NUT_DEEP));
