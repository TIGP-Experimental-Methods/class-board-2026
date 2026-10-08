// Housing - the two opening shapes, and where the vents go.
// Ren Qian (Section A), 2026-10-02.
//
// Both are slots cut through a vertical wall, so both have the same problem:
// the ceiling of the slot is an overhang. These are the two answers to it.

include <housing-params.scad>

// A wire entry. Its ceiling would be a flat 90 degree overhang - against the
// brief's 45 degree rule, and a bridge the slicer wants to support - so it gets
// a 45 degree gable. Where a full gable would break through into the part above
// it is capped at zcap, leaving a shorter flat top: still a much smaller bridge
// than the full width. The same slope leads the wire in.
// ROUND_R then softens the corners - shrink by R, grow back by R, which rounds
// the convex corners and takes the bare "house" look off it. Costs about 2R of
// flat at the apex, which at R = 1 is nothing.
//   cx, w      centre and width across the wall
//   z0, z1     bottom and top of the straight part
//   zcap       the gable may not go above this
//   ycen, dep  where the slot sits through the wall, and how deep to cut
function gable_rise(w, z1, zcap) = min(w/2, max(0, zcap - z1));
module wire_slot(cx, w, z0, z1, zcap, ycen, dep) {
  r = gable_rise(w, z1, zcap);
  f = w/2 - r;                       // half-width of whatever flat top remains
  translate([cx, ycen + dep/2, 0])
    rotate([90, 0, 0])
      linear_extrude(height = dep)
        offset(r = ROUND_R) offset(r = -ROUND_R)
          polygon([[-w/2, z0], [w/2, z0], [w/2, z1],
                   [ f, z1 + r], [-f, z1 + r], [-w/2, z1]]);
}

// A vent is a teardrop - a half circle at the bottom, straight sides, and a top
// that is a half circle with a 45 degree point on it.
//
// It was a plain stadium (a half circle at each end) until I sliced it. A circle
// has every tangent angle on it somewhere, including horizontal at the very top,
// so a round-topped hole ALWAYS contains surface the slicer scores as needing
// support - a 1.5 mm cap on each of these - and 24 of them is 83 mm2 of it,
// which was 89% of everything flagged in the whole part.
//
// The fix is the standard teardrop: hull the top circle with a point sqrt(2)*r
// above its centre. The tangents from a point at that distance touch the circle
// at exactly 45 degrees, so the top becomes two 45 degree faces and the sub-45
// surface goes to zero, while the shoulders stay round. It is not the row of
// gabled houses I rejected before - only the last 1.5 mm comes to a point.
//
// The apex is placed AT z1 and the circle dropped to z1 - sqrt(2)*r, so the vent
// keeps exactly its old envelope and the 2 mm of solid wall above it.
module vent_slot(cx, w, z0, z1, ycen, dep) {
  r = w/2;
  translate([cx, ycen + dep/2, 0])
    rotate([90, 0, 0])
      linear_extrude(height = dep)
        hull() {
          translate([0, z0 + r])            circle(r = r);     // round bottom
          translate([0, z1 - r*sqrt(2)])    circle(r = r);     // the shoulders
          translate([0, z1 - 0.01])         circle(r = 0.01);  // the 45 deg point
        }
}

// Ventilation. The dev board and the power module sit in a closed 190 x 110 x 45
// box with no way for warm air to leave. Slots go in the two ends and the far
// wall - not the near wall, which is already full of connector openings.
VENT_W     = 3;
VENT_PITCH = 12;
VENT_Z0    = FLOOR_TOP + 3;     // -22.40
VENT_Z1    = COVER_SIT - WALL;  //   1.90

// Positions chosen to miss the corner bosses, which fill y -10..-26 and
// -104..-120 at the ends, and x -5..11 and 169..183 on the far wall.
VENT_Y = [for (i = [0:5]) -35 - i*VENT_PITCH];        // -35 .. -95
VENT_X = [for (i = [0:11])  22 + i*VENT_PITCH];       //  22 .. 154

module vents() {
  // the two ends: the slot is turned a quarter turn so it cuts through x
  for (wx = [BX0 - GAP - WALL/2, BX1 + GAP + WALL/2])
    for (cy = VENT_Y)
      translate([wx, cy, 0]) rotate([0, 0, 90])
        vent_slot(0, VENT_W, VENT_Z0, VENT_Z1, 0, 4*WALL);
  // the far wall
  for (cx = VENT_X)
    vent_slot(cx, VENT_W, VENT_Z0, VENT_Z1, BY0 - GAP - WALL/2, 4*WALL);
}
