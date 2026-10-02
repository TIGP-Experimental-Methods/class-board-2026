// iPad Air 5 stand - two angles, prints flat with no supports.
// 2026-10-02.
//
// Verified from Apple's tech specs: the Air 5 is 247.6 x 178.5 x 6.1 mm. The
// only dimension that matters here is the 6.1 thickness - and the one that will
// catch you out is your CASE. A folio adds 2-4 mm, so measure the tablet IN its
// case and put that in CASE_T.
//
// PRINTS ON ITS SIDE. The whole part is one constant cross-section extruded, so
// there is nothing to overhang: every slot wall comes out as a vertical face.
// That is also why the slots can be at any angle - the usual worry about an
// overhanging slot roof simply does not apply in this orientation.
//
// Print TWO and stand them 120-150 mm apart. Two narrow supports hold a tablet
// better than one wide one, use less filament, and print in parallel.

include <BOSL2/std.scad>
$fa = 2; $fs = 0.4;

// ---- the tablet --------------------------------------------------------------
PAD_T   = 6.1;      // Apple tech specs, iPad Air 5
CASE_T  = 3.0;      // MEASURE: what your case adds. 0 if you use it bare.
SLOT_GAP = 1.0;     // so it drops in rather than has to be pushed
SLOT_W  = PAD_T + CASE_T + SLOT_GAP;

// ---- the wedge ---------------------------------------------------------------
DEPTH    = 110;     // front to back on the desk
BACK_H   = 70;      // height at the back
FRONT_H  = 12;      // height at the front - the lip that stops it sliding out
WIDTH    = 60;      // along the tablet's edge (the extrusion)
SLOT_LEN = 40;      // how far the slot goes into the wedge

// Two angles, measured from the desk. Upright for typing, laid back for video.
ANGLE_A  = 68;
ANGLE_B  = 55;
SLOT_A_X = 68;      // where each slot meets the desk, from the front
SLOT_B_X = 34;
ROUND_R  = 2.5;     // nothing sharp against the screen

// ---- derived -----------------------------------------------------------------
// Top edge of the wedge at a given x, so the check below can ask whether a slot
// stays inside the material.
function top_at(x) = FRONT_H + (BACK_H - FRONT_H) * x / DEPTH;
function tip(x0, a)  = [x0 + SLOT_LEN * cos(a), SLOT_LEN * sin(a)];
function fits(x0, a) = tip(x0, a).y < top_at(tip(x0, a).x) - 3;

module wedge() {
  polygon([[0, 0], [DEPTH, 0], [DEPTH, BACK_H], [0, FRONT_H]]);
}

module slot(x0, a) {
  translate([x0, 0])
    rotate(a - 90)
      translate([-SLOT_W/2, -3])
        square([SLOT_W, SLOT_LEN + 3]);
}

module profile() {
  difference() {
    wedge();
    slot(SLOT_A_X, ANGLE_A);
    slot(SLOT_B_X, ANGLE_B);
  }
}

linear_extrude(WIDTH)
  offset(r = ROUND_R) offset(r = -ROUND_R) profile();

echo(str("iPad Air 5: 247.6 x 178.5 x 6.1 mm (Apple tech specs)"));
echo(str("slot ", SLOT_W, " = ", PAD_T, " tablet + ", CASE_T, " case + ", SLOT_GAP));
echo(str("wedge ", DEPTH, " deep, ", FRONT_H, " -> ", BACK_H, " tall, ", WIDTH,
         " wide. PRINT TWO."));
echo("-- does each slot stay inside the wedge? --");
echo(str("   ", ANGLE_A, " deg at x ", SLOT_A_X, ": tip ", tip(SLOT_A_X, ANGLE_A),
         "  top there ", top_at(tip(SLOT_A_X, ANGLE_A).x),
         fits(SLOT_A_X, ANGLE_A) ? "   ok" : "   <<< BREAKS OUT"));
echo(str("   ", ANGLE_B, " deg at x ", SLOT_B_X, ": tip ", tip(SLOT_B_X, ANGLE_B),
         "  top there ", top_at(tip(SLOT_B_X, ANGLE_B).x),
         fits(SLOT_B_X, ANGLE_B) ? "   ok" : "   <<< BREAKS OUT"));
echo("CASE_T is the number that will catch you out - measure it in the case.");
