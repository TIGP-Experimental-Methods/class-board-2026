// Housing - Ren Qian (Section A)
// 2026-10-02.  One file, three printed parts: set PART below.
//
//   base    tray: wall, floor, four M3 bosses with nut pockets, rear connector cutouts
//   cover   two heights: a low deck over the SMA field so the threads come through,
//           a raised deck over the OLED / TX terminal end
//   coupon  the fit test: holes 3.0-3.6, one nut pocket, a wall of my thickness
//
// cover.dxf is PART="cover2d", the flat outline of the cover. Note what it cannot
// be: the cover is a printed part with two heights, and a flat projection has no
// way to carry that. Three of the four far-wall notches do not appear in it at all,
// because the raised deck above them fills their shadow - only the TX one shows,
// and only because it runs out through the top edge. The DXF also carries no
// $INSUNITS, so anything importing it has to be told these are millimetres.
// If a laser-cut plate is ever wanted, draw it as its own 2D part, not from here.
//
// Not done: nothing has been printed. Until coupon.stl is printed and measured,
// M3_CLEAR, NUT_AF and FIT below are assumptions, not results.

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

// The cover's outer edge. These must be the OUTER faces, the same as the base's
// footprint - taking y from the inner faces (BY0-GAP / BY1+GAP) made the cover
// 190 x 106 against a 190 x 110 base, so it dropped inside the walls at both ends.
OUT_Y0 = BY0 - GAP - WALL;      // -120
OUT_Y1 = BY1 + GAP + WALL;      // -10

// Panel labels, read from the MASTER front panel (the file that gets made), not
// from the section copy - the instructor reassigned AUX / RX / TX to different
// jacks after the sections were split. [ x, y, text ]
ENGRAVE = 0.6;
SMA_LABELS = [
  [ 75.65, -25.67, "AI1"], [ 93.65, -25.67, "AI2"], [111.65, -25.67, "AI3"],
  [129.65, -25.67, "AI4"], [147.65, -25.67, "AUX"], [165.65, -25.67, "FAST1"],
  [ 75.65, -43.67, "AI5"], [ 93.65, -43.67, "AI6"], [111.65, -43.67, "AI7"],
  [129.65, -43.67, "AI8"], [147.65, -43.67, "RX"],  [165.65, -43.67, "FAST2"],
  [ 75.65, -61.67, "AO1"], [ 93.65, -61.67, "AO2"], [111.65, -61.67, "TX"],
  [129.65, -61.67, "TRIG"],
];

// Names for the raised deck. Mis-wiring a terminal costs more than plugging a
// coax into the wrong jack, so these matter at least as much as the SMA ones.
// [ x, y, text, halign, size ]
// The three LEDs are only 2.95 mm apart, so their names have to be smaller than
// the rest or they run into each other.
DECK_LABELS = [
  [ 33.75, -101.5, "MODULE",  "center", 3.2],
  [ 60.25, -101.5, "ISO2",    "center", 3.2],
  [ 87.80, -101.5, "ISO1",    "center", 3.2],
  [110.70, -101.5, "TX COIL", "center", 3.2],
  [144.10, -104.5, "TTL",     "center", 3.2],
  [120.00,  -86.95,"PWR",     "left",   2.2],
  [120.00,  -89.90,"WIFI",    "left",   2.2],
  [120.00,  -92.85,"ACT",     "left",   2.2],
  [126.50,  -77.75,"QWIIC",   "left",   3.2],
];

// A locating lip: without it the only thing holding the cover in place sideways
// is the four screws, and it slides about while you line the holes up. The lip
// drops into the 3 mm gap between the board edge and the inner wall.
LIP_H = 3;
LIP_W = 2;

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
      translate([CTRB.x, (SPLIT_Y + OUT_Y1)/2, COVER_SIT])
        cuboid([OSIZE.x, OUT_Y1 - SPLIT_Y, WALL], anchor = BOTTOM);
      // raised box over the OLED / TX terminal end
      translate([CTRB.x, (SPLIT_Y + OUT_Y0)/2, COVER_SIT])
        cuboid([OSIZE.x, SPLIT_Y - OUT_Y0, HIGH_TOP - COVER_SIT], anchor = BOTTOM);
      // locating lip, hanging into the base's cavity
      translate([CTRB.x, CTRB.y, COVER_SIT - LIP_H])
        rect_tube(h = LIP_H, wall = LIP_W, anchor = BOTTOM,
                  isize = [ISIZE.x - 2*FIT - 2*LIP_W, ISIZE.y - 2*FIT - 2*LIP_W]);
    }
    // hollow the raised box
    translate([CTRB.x, (SPLIT_Y + OUT_Y0)/2, COVER_SIT - 1])
      cuboid([OSIZE.x - 2*WALL, SPLIT_Y - OUT_Y0 - 2*WALL, HIGH_IN - COVER_SIT + 1],
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
      // deep enough to clear the locating lip as well as the wall, or the lip
      // would stand straight across the wire's path into the terminal
      translate([(c[1]+c[2])/2, OUT_Y0 + 4, (COVER_SIT - 1 + ztop)/2])
        cuboid([c[2]-c[1] + 2*FIT, 2*WALL + 12, ztop - (COVER_SIT - 1)]);
    }

    // the panel silkscreen is hidden under the cover, so the names go on top.
    // Engraved, not raised: nothing to knock off, and it prints without supports.
    for (L = SMA_LABELS)
      translate([L[0], L[1] + 6.5, LOW_TOP - ENGRAVE])
        linear_extrude(ENGRAVE + 1)
          text(L[2], size = 3.2, halign = "center", valign = "center",
               font = "Liberation Sans:style=Bold");

    for (L = DECK_LABELS)
      translate([L[0], L[1], HIGH_TOP - ENGRAVE])
        linear_extrude(ENGRAVE + 1)
          text(L[2], size = L[4], halign = L[3], valign = "center",
               font = "Liberation Sans:style=Bold");

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
