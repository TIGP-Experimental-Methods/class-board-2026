// Housing - every number in one place.
// Ren Qian (Section A), 2026-10-02.
//
// Two kinds of number live here and it matters which is which:
//   - the ones I chose, which are design decisions and can be argued with
//   - the ones measured off hardware/release/*.stl, which are facts about the
//     boards and must not be "tidied up"
//
// NOT MEASURED YET: nothing has been printed. M3_CLEAR, NUT_AF and FIT are
// assumptions until coupon.stl is printed and a real M3 is tried in its holes.

$fa = 2; $fs = 0.4;

// ---- the ones I chose --------------------------------------------------------
GAP       = 3;          // board edge -> inner wall face
WALL      = 2;          // brief: walls and floor 2 mm
M3_CLEAR  = 3.3;        // brief: holes 0.3 over the part
FLOOR_AIR = 2;          // air under the lowest thing on the boards
NUT_AF    = 5.8;        // brief: nut across flats
NUT_DEEP  = 2.5;

// How far the 45 degree roof over each nut pocket rises. Taking it to the hex's
// across-CORNERS radius rather than its across-flats one puts the pocket's six
// roof faces at atan(3.35/2.9) = 49.1 degrees instead of exactly 45, which is
// the difference between "inside the rule" and "on the line".
// Idea from the instructor's own housing, whose pockets "open at 45 degrees into
// the box, so each nut slides in and cannot turn":
//   https://shaynebennetts.github.io/class-board-instrument/
NUT_ROOF  = NUT_AF/(2*cos(30));   // 3.349
FIT       = 0.3;        // brief's general clearance
ENGRAVE   = 0.6;        // depth of the engraved names
ROUND_R   = 1.0;        // corner rounding on the wire slots

PAD_USB   = 3.0;        // USB-C moulded boot - far wider than the socket
PAD_DC    = 2.5;

// Three separate terminal openings rather than one slot across all three.
// The ribs between them are what decides this: the terminals sit 2.7 and 3.4 mm
// apart, so the rib is 2.7 - 2*PAD_TERM and 3.4 - 2*PAD_TERM. At PAD_TERM = 1.0
// that was 0.7 and 1.4 mm, under the 2 mm wall rule and certain to snap, which
// is why it was one slot before. At 0.35 - which is the brief's own 0.3 rule for
// a hole - the ribs are 2.00 and 2.70 mm, and each opening is then narrow enough
// for a full 45 degree gable, so the flat overhang goes to zero as well. The one
// slot had a 31.4 mm bridge across it.
PAD_TERM  = 0.35;
TERM_SLOT = false;

// A locating lip: without it the only thing holding the cover in place sideways
// is the four screws, and it slides about while you line the holes up. The lip
// drops into the 3 mm gap between the board edge and the inner wall.
LIP_H = 3;
LIP_W = 2;

// ---- measured off the board meshes, and the brief ----------------------------
BX0 =    0;  BX1 =  180;      // both boards 180 x 100 at x 0..180, y -115..-15
BY0 = -115;  BY1 =  -15;
HOLE_INSET = 4;               // brief: mounting holes 4 mm in from the corners
BOARD_GAP  = 11;              // brief: between the two facing board surfaces
PCB_T      = 1.6;
FACE       = PCB_T;           // 1.6 - the panel's outer face
Z_LOW      = -23.40;          // lowest thing under the main board

// the only two things on the panel taller than the SMA threads
OLED  = [[137.5, -101.6], [164.6, -72.7], 15.42];   // 27.0 x 29.0, 13.82 above the face
TXT   = [[105.6, -114.7], [115.8, -104.1], 15.70];  // 10.3 x 10.6, 14.10 above the face
SMA_TOP = 11.40;              // top of an SMA jack  (9.8 above the face)
SMA_HEX = FACE + 2.0;         // brief: hex base 0-2 mm, then the threaded barrel
SMA_D   = 6.6;                // barrel + FIT

SMA_X    = [for (i = [0:5]) 75.65 + 18*i];
SMA_ROWS = [-25.67, -43.67, -61.67];        // rows 1,2 have six; row 3 has four

// "Through the panel's outer face" - a hole in the top of the raised deck.
// [ name, x0, x1, y0, y1 ]
PANEL_TOP = [
  ["LEDs D1-D3",   115.4, 117.5,  -93.5,  -86.3],   // 1.00 above the face
  ["Qwiic J33",    119.2, 122.8,  -80.8,  -74.8],   // 4.32
  ["module hdr J40", 22.3, 45.2, -113.0, -103.9],   // 9.10
];

// "along the panel's far edge ... their wires come from the side" - a notch in
// the far wall instead. [ name, x0, x1, z top ]
FAR_SIDE = [
  ["iso J412",      54.4,  66.1, 11.55],
  ["iso J411",      81.8,  93.8, 11.55],
  ["TX term J32",  105.6, 115.8, 15.70],
  ["TTL strip J31", 131.4, 156.8, 10.40],
];

// KNOWN MODEL BUG 2026-10-02: J901/J903 are KF301-5.0-2P. eef00d2 fixed that
// footprint's 3D model (offset xyz 0 0 5) but re-exported the PANEL only, so
// class-board.stl (a4a88bc, 10-01 19:51) still reads them 5 mm high. J905 is 3P
// and correct. Set to 0 after the board STL is re-exported, and re-measure
// rather than trusting this note.
KF301_FIX = -5.0;

// Names, read from the MASTER front panel, not from the section copy - the
// instructor reassigned AUX / RX / TX to different jacks after the sections were
// split, so three of these sixteen would be wrong if taken from my own file.
// [ x, y, text ]
SMA_LABELS = [
  [ 75.65, -25.67, "AI1"], [ 93.65, -25.67, "AI2"], [111.65, -25.67, "AI3"],
  [129.65, -25.67, "AI4"], [147.65, -25.67, "AUX"], [165.65, -25.67, "FAST1"],
  [ 75.65, -43.67, "AI5"], [ 93.65, -43.67, "AI6"], [111.65, -43.67, "AI7"],
  [129.65, -43.67, "AI8"], [147.65, -43.67, "RX"],  [165.65, -43.67, "FAST2"],
  [ 75.65, -61.67, "AO1"], [ 93.65, -61.67, "AO2"], [111.65, -61.67, "TX"],
  [129.65, -61.67, "TRIG"],
];

// [ x, y, text, halign, size ] - the three LEDs are only 2.95 mm apart, so their
// names have to be smaller than the rest or they run into each other.
DECK_LABELS = [
  [ 33.75, -101.5, "MODULE",  "center", 3.2],
  [ 60.25, -101.5, "ISO2",    "center", 3.2],
  [ 87.80, -101.5, "ISO1",    "center", 3.2],
  [110.70, -101.5, "TX COIL", "center", 3.2],
  [144.10, -104.5, "TTL",     "center", 3.2],
  [120.00,  -86.95,"PWR",     "left",   2.2],
  [120.00,  -89.90,"WIFI",    "left",   2.2],
  [120.00,  -92.85,"ACT",     "left",   2.2],
  // QWIIC was at x 126.5, where it ran 1.67 mm into the OLED window and lost
  // half its C - invisible while the names were the cover's own colour, obvious
  // once they were white. At 123.6 it spans 123.78..136.57: 0.68 mm clear of
  // the Qwiic cutout and 1.23 mm clear of the window.
  [123.60,  -77.75,"QWIIC",   "left",   3.2],
];

// ---- the two cover heights ---------------------------------------------------
// The split: the SMA field is at y > -70, everything tall is at y < -70.
SPLIT_Y   = -70;
COVER_SIT = SMA_HEX + FIT;                 // 3.9 - wall top, just over the hex bases
LOW_TOP   = COVER_SIT + WALL;              // 5.9 - SMA threads stand 5.5 proud
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

MAIN_UNDER = -(BOARD_GAP + PCB_T);
BOSS_H     = MAIN_UNDER - FLOOR_TOP;
BOSS       = 2*(GAP + HOLE_INSET);

HOLES = [ [BX0+HOLE_INSET, BY1-HOLE_INSET], [BX1-HOLE_INSET, BY1-HOLE_INSET],
          [BX0+HOLE_INSET, BY0+HOLE_INSET], [BX1-HOLE_INSET, BY0+HOLE_INSET] ];
function wdir(h) = [ h.x < CTRB.x ? -1 : 1, h.y < CTRB.y ? -1 : 1 ];

// FIVE CONNECTORS, FOUR OPENINGS. The DC jack ends at x 152.5 and the USB-C
// starts at 157.5, so there is 5.0 mm between them, and PAD_USB alone takes 3.0
// of it. The rib would be 5.0 - PAD_USB - PAD_DC = -0.5 mm: the two openings
// overlap and print as one 30.3 mm opening from z -17.2 up to the gables.
// That is the right answer rather than a fault. Any rib I could fit here would
// be under 2 mm, which is the trap PAD_TERM exists to avoid, and the only way
// to widen it is to take clearance off the USB-C boot - the one opening that
// needs it most. Measured on base.stl: continuous 139.20..169.45 at z = -9.
// Where the two 45 degree gables separate again, at z about -6.5, they leave a
// wedge of plastic whose tip is 0.15 mm wide. The slicer will drop the first
// layer or two of it. That is cosmetic; it is not a bridge and needs no support.
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

// ---- names for the back, and my name (version 2) -----------------------------
// SPEC.md decisions 4 and 6, and answers 1, 2 and 4.
// Everything here was read from hardware/class-board.kicad_pcb - the pad nets
// and the silkscreen printed beside each connector - not from a photo or the
// brief. The main board is turned over in the housing, so housing x = 180 - x.

// The names go on the TOP of the low cover along its rear edge, one above each
// opening: the rear wall has no room for them - the DC opening runs from the
// floor to within 2.4 mm of the wall top. Two staggered rows, because the
// openings are only 15 to 18 mm apart and "H-BRIDGE COIL" is 26 mm long at
// 2.6 (measured, not estimated); staggered, a name only has to clear the next
// name in its own row, 31 mm or more away.
// Size 2.2, not 2.6: at 2.6 with 0.8 mm everywhere, the back row sat 0.8 mm
// from the AI1-FAST1 names and "5V IN" read as one line with "AUX" below it.
// 2.2 frees 0.8 mm, and all of it goes to that one gap: the rows now sit
// 0.6 mm in from the cover's rear edge (y -10), 0.8 mm apart, and 1.87 mm
// clear of the AI1-FAST1 names (their tops at y -17.59). Glyphs are 2.16 mm
// tall at 2.2. 2.2 is the smallest size on the coupon - legibility unproven.
// [ text, x = centre of its REAR opening, row 0 nearer the edge | row 1 ]
REAR_NAME_SIZE = 2.2;
REAR_NAME_ROW  = [-11.68, -14.64];
REAR_NAMES = [
  ["COIL ≤24V",    98.40, 0],   // J905  silkscreen "+VCOIL COIL GND <=24V"
  ["H-BRIDGE COIL",    116.00, 1],   // J903  silkscreen "H-BRIDGE COIL"
  ["VEXT 7-18V",       131.50, 0],   // J901  silkscreen "+VEXT 7-18V DC FUSE 5A"
  ["5V IN",            147.10, 1],   // J202  silkscreen "5V IN"
  ["USB-C 5V",         162.00, 0],   // J201  silkscreen "USB-C 5V"
];

// The poles, engraved in the rear wall under each terminal opening, one mark
// at each wire entry. x is the pad, from the board file:
//   J901  pad 1 /c_switch/VIN  +    pad 2 GND  -
//   J903  pad 1 HB_OUT1  1          pad 2 HB_OUT2  2   - an H-bridge: the two
//         poles take turns being positive, so + and - would be a lie
//   J905  pad 1 +VCOIL  +   pad 2 COIL  C   pad 3 GND  -
// U+2212 is a real minus, not a hyphen.
POLE_SIZE = 3.2;
POLES = [
  ["+",      127.62], ["−", 132.62],                        // J901
  ["1",      113.22], ["2",      118.23],                        // J903
  ["+",       95.10], ["C",      100.10], ["−", 105.10],    // J905
];
// Centred in the band between the bottom of the base and the lowest terminal
// opening - 4.45 mm, so the 3.15 mm glyphs keep 0.65 mm each side.
POLE_TOP = min([for (i = [2:4]) REAR[i][3] + REAR[i][6] - REAR[i][5]]);
POLE_Z   = (FLOOR_BOT + POLE_TOP) / 2;

// My name, one line, in the empty left part of the low cover: no SMA there
// left of x 72. 57.4 mm wide at size 6 (measured), centred in x -2 .. 70.
MY_NAME = ["TEE REN QIAN", 34.0, -40.0, 6.0];   // [ text, x, y, size ]
