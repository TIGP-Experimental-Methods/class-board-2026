// Housing - the test coupon. PRINT THIS FIRST.
// Ren Qian (Section A), 2026-10-02.
//
// The brief: "Print a test coupon first (holes 3.0-3.6 mm, one nut pocket, a
// wall of your thickness): it answers the fit for this printer."
//
// Seven holes in 0.1 mm steps. Whichever one an M3 screw first passes through
// cleanly is this printer's answer, and that number belongs in M3_CLEAR in
// housing-params.scad - which then changes every hole in the base and the
// cover. The nut pocket is identical to the one in the base, so it also answers
// whether a real M3 nut slides into 5.8 mm across flats, and the wall is the
// thickness the whole box uses.
//
// Until this is printed and measured, M3_CLEAR, NUT_AF and FIT are assumptions.
//
// Defines module coupon() only; render it through housing.scad with
// PART = "coupon".

include <BOSL2/std.scad>
include <housing-params.scad>

module coupon() {
  L = 62; W = 26;
  difference() {
    union() {
      cuboid([L, W, WALL], anchor = BOTTOM);                                  // the plate
      translate([0, W/2 - WALL/2, 0]) cuboid([L, WALL, 10], anchor = BOTTOM); // a wall of my thickness
      translate([L/2 - 11, -W/2 + 9, 0])
        cuboid([18, 16, NUT_DEEP + WALL], anchor = BOTTOM);                   // the boss for the pocket
    }

    // holes 3.0 .. 3.6 in 0.1 steps
    for (i = [0:6])
      translate([-L/2 + 6 + i*7, -2, -1]) cylinder(d = 3.0 + i*0.1, h = WALL+2);

    // one nut pocket, exactly as the base has it
    translate([L/2 - 11, -W/2 + 9, 0]) {
      translate([0,0,-1]) cylinder(d = M3_CLEAR, h = NUT_DEEP+WALL+2);
      cylinder(h = NUT_DEEP, d = NUT_AF/cos(30), $fn = 6);
      translate([0, -NUT_AF/2, 0]) cube([20, NUT_AF, NUT_DEEP]);
    }

    // Engraved text at the three sizes, because the cover's names are engraved
    // and the small ones are marginal: measured on the glyph itself, size 2.2
    // gives a 0.440 mm stroke and size 3.2 gives 0.640 mm, against a line about
    // 0.42 mm wide from a 0.4 mm nozzle. 2.2 is therefore one extrusion wide -
    // it may come out, or the slicer may skip it and the letter never appears.
    // Each sample is labelled with its own size, so the print says which works.
    // Whichever is the smallest legible one is the floor for DECK_LABELS.
    for (i = [0:2]) {
      s = [2.2, 2.6, 3.2][i];
      translate([-L/2 + 10 + i*17, 6, WALL - ENGRAVE])
        linear_extrude(ENGRAVE + 1)
          text(str(s), size = s, halign = "center", valign = "center",
               font = "Liberation Sans:style=Bold");
    }
  }
}
