// Screw-cap pencil tube - the drawing-tube kind.
// 2026-10-02.  PART = "body" | "cap"
//
// Printed standing up, which is what makes the thread come out round: lying it
// down would put the thread profile across the layers and it would not turn.
// The body is tall - check it against your printer's Z before you start.
//
// The thread is a coarse 4 mm pitch ISO form. Fine threads do not print: at
// 0.4 mm nozzle the flanks of an M44x1.5 are two extrusions wide and the cap
// binds. Coarse means fewer, bigger flanks and about a turn and a half to close.
//
// THREAD_SLOP is the number to change if the cap is tight or sloppy. It is the
// only fit in the part, and it is the one thing a printer's tolerance will move.

include <BOSL2/std.scad>
include <BOSL2/threading.scad>
$fa = 2; $fs = 0.4;

PART = "body";          // "body" | "cap"

// ---- what goes in it ---------------------------------------------------------
INNER_D   = 40;         // MEASURE: wide enough for a handful of pens; 40 is roomy
INNER_L   = 180;        // MEASURE: a standard pen is about 150, a ruler is not

// ---- the part ----------------------------------------------------------------
WALL      = 2.0;
BASE_T    = 2.5;        // the closed end
THREAD_L  = 16;         // how much thread is on the neck
PITCH     = 4.0;        // coarse, so it prints and so it closes in ~1.5 turns
THREAD_SLOP = 0.35;     // CHANGE ME if the cap binds or rattles
CAP_WALL  = 2.2;
CAP_TOP   = 2.5;
FLUTES    = 16;         // grip grooves round the cap
FLUTE_D   = 2.4;

// ---- derived -----------------------------------------------------------------
TUBE_OD   = INNER_D + 2 * WALL;             // 44
THREAD_D  = TUBE_OD;                        // thread cut into the tube wall itself
CAP_OD    = THREAD_D + 2 * CAP_WALL;        // 48.4
CAP_H     = THREAD_L + CAP_TOP + 2;
BODY_H    = BASE_T + INNER_L + THREAD_L;

module body() {
  difference() {
    union() {
      cylinder(d = TUBE_OD, h = BODY_H - THREAD_L);
      translate([0, 0, BODY_H - THREAD_L])
        threaded_rod(d = THREAD_D, l = THREAD_L, pitch = PITCH,
                     internal = false, bevel2 = true, anchor = BOTTOM);
    }
    // the bore, closed at the bottom
    translate([0, 0, BASE_T]) cylinder(d = INNER_D, h = BODY_H);
  }
}

module cap() {
  difference() {
    cylinder(d = CAP_OD, h = CAP_H);
    // the female thread. internal=true is BOSL2's version to subtract - it adds
    // the clearance a nut needs; THREAD_SLOP is on top of that, for the printer.
    translate([0, 0, -1])
      threaded_rod(d = THREAD_D + THREAD_SLOP, l = THREAD_L + 2, pitch = PITCH,
                   internal = true, bevel1 = true, anchor = BOTTOM);
    // grip flutes
    for (i = [0 : FLUTES - 1])
      rotate([0, 0, i * 360 / FLUTES])
        translate([CAP_OD/2, 0, -1])
          cylinder(d = FLUTE_D, h = CAP_H + 2);
  }
}

if (PART == "body") body();
if (PART == "cap")  cap();

echo(str("PART = ", PART));
echo(str("bore ", INNER_D, " x ", INNER_L, " usable"));
echo(str("body ", TUBE_OD, " dia x ", BODY_H, " tall   <- check this against your Z"));
echo(str("cap  ", CAP_OD, " dia x ", CAP_H, " tall"));
echo(str("thread M", THREAD_D, " x ", PITCH, " coarse, ", THREAD_L,
         " long = ", THREAD_L/PITCH, " turns to close"));
echo(str("fit: THREAD_SLOP ", THREAD_SLOP, " - raise it if the cap binds, lower it if it rattles"));
