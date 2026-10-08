// Housing - the wire-entry shape.
// Ren Qian (Section A), 2026-10-02; vents removed 2026-10-08 (version 2).
//
// A slot cut through a vertical wall has one problem: its ceiling is an
// overhang. This is the answer to it.
//
// There used to be a second shape here, the vent. Version 1 had 24 vent slots
// in the two ends and the far wall; version 2 has none - SPEC.md decision 1,
// "no vents, the walls stay clean", because the first version had too many
// holes. What gets warm inside is the AMS1117, the isolated supply modules and
// the NMR power amplifier during a pulse: the box will run somewhat above room
// temperature, nowhere near the 60 degrees at which PLA softens.

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
