// Housing - Ren Qian (Section A), 2026-10-02.
// Version 2, 2026-10-08, from SPEC.md: no vents, white names front and back,
// pole marks on the rear wall, and my name on the cover.
// This is the entry point. Set PART, press F5, export with F6.
//
//   PART = "base"        the tray: wall, floor, four M3 bosses with nut pockets,
//                        the rear connector openings              -> base.stl
//   PART = "base_labels" the pole marks on the rear wall as a separate part
//                        for white; load with base.stl as one object
//                                                             -> base-labels.stl
//   PART = "cover_low"   the cover's low deck over the SMA field     -> cover-low.stl
//   PART = "cover_high"  the cover's raised box over the OLED end    -> cover-high.stl
//   PART = "cover_low_labels", "cover_high_labels"
//                        the names as a separate part for a second colour, to be
//                        loaded together with their half as one object
//                                       -> cover-low-labels.stl, cover-high-labels.stl
//                        Both come out FACE DOWN, ready for the plate. The cover
//                        has two heights 12.3 mm apart and cannot print as one
//                        part without supports - see the split in housing-cover.
//   PART = "cover"       the whole cover in place, for looking at only
//   PART = "coupon"      the fit test. PRINT THIS ONE FIRST          -> coupon.stl
//   PART = "coupon_labels" its names, for white, loaded with coupon.stl as one
//                        object - the same as the cover's     -> coupon-labels.stl
//   PART = "cover2d"     flat outline of the whole cover, for cover.dxf
//
// The work is split across four more files, each of which opens on its own:
//   housing-params.scad   every number, and which of them are measured facts
//   housing-shapes.scad   the wire-entry shape
//   housing-base.scad     base(), and its pole-mark inlay
//   housing-cover.scad    cover(), and its two printed halves
//   housing-coupon.scad   coupon(), and its names for white
//
// About cover.dxf: it is the flat outline of the cover, and it cannot be more
// than that. The cover is a printed part with two heights and a flat projection
// has no way to carry that. Three of the four far-wall notches do not appear in
// it at all, because the raised deck above them fills their shadow - only the TX
// one shows, and only because it runs out through the top edge. There is no
// $INSUNITS in it either, so whatever reads it has to be told these are
// millimetres. If a laser-cut plate is ever wanted, draw it as its own 2D part.
//
// NOT DONE: nothing has been printed. Until coupon.stl is printed and measured,
// M3_CLEAR, NUT_AF and FIT are assumptions, not results.

PART = "base";  // [base, base_labels, cover_low, cover_high, cover_low_labels, cover_high_labels, cover, coupon, coupon_labels, cover2d, assembly]

include <BOSL2/std.scad>
include <housing-params.scad>
include <housing-shapes.scad>
include <housing-base.scad>
include <housing-cover.scad>
include <housing-coupon.scad>

if (PART == "base")       base();
if (PART == "base_labels") base_labels();
if (PART == "cover_low")  cover_low();
if (PART == "cover_high") cover_high();
if (PART == "cover_low_labels")  cover_low_labels();
if (PART == "cover_high_labels") cover_high_labels();
if (PART == "cover")      cover();
if (PART == "coupon")  coupon();
if (PART == "coupon_labels") coupon_labels();
if (PART == "cover2d") projection(cut = false) cover();

// Everything in place for housing.png: the boards where they really sit, and the
// two cover halves lifted and pulled apart so the split shows. Preview only (F5);
// the colours do not survive F6.
// It draws the EXPORTED STL files, not the modules - so export first. Two
// reasons: the picture is then of exactly the files handed in, and the label
// inlays (a cover minus a cover, inside an intersection) are more CSG than the
// preview can draw - it gave up and painted the whole cover white and lost the
// base walls. face_down() undoes itself, so it turns the face-down halves back.
EXPLODE_Z = 28;
EXPLODE_Y = 10;
if (PART == "assembly") {
  color("Teal")          import("base.stl");
  color("White")         import("base-labels.stl");
  color("ForestGreen")   import("../../../../hardware/release/front-panel.stl");
  color("DarkGreen")     translate([180, 0, -BOARD_GAP]) rotate([0, 180, 0])
                           import("../../../../hardware/release/class-board.stl");
  translate([0, 0, EXPLODE_Z]) face_down(LOW_TOP) {
    color("SteelBlue")      import("cover-low.stl");
    color("White")          import("cover-low-labels.stl");
  }
  translate([0, -EXPLODE_Y, EXPLODE_Z]) face_down(HIGH_TOP) {
    color("LightSteelBlue") import("cover-high.stl");
    color("White")          import("cover-high-labels.stl");
  }
}

// ---- check the numbers -------------------------------------------------------
echo(str("PART = ", PART));
echo(str("base   outer ", OSIZE.x, " x ", OSIZE.y, " x ", COVER_SIT-FLOOR_BOT,
         "   bed 256: ", (OSIZE.x<=256 && OSIZE.y<=256) ? "ok" : "NO"));
echo(str("cover  sits at z ", COVER_SIT, "  low deck top ", LOW_TOP,
         "  raised top ", HIGH_TOP));
echo(str("cover  split at y ", SPLIT_Y, " with a ", FIT, " mm gap:  low ",
         OSIZE.x, " x ", OUT_Y1 - SPLIT_Y - FIT, " x ", LOW_TOP - (COVER_SIT - LIP_H),
         "   high ", OSIZE.x, " x ", SPLIT_Y - OUT_Y0, " x ", HIGH_TOP - (COVER_SIT - LIP_H),
         "   both printed face down"));
echo(str("SMA thread proud of the low deck: ", SMA_TOP - LOW_TOP, " mm"));
echo(str("raised deck inner z ", HIGH_IN, " clears TX terminal ", TXT[2],
         " by ", HIGH_IN - TXT[2]));
echo(str("coupon ", CL, " x ", CW, ": M3 holes 3.0..3.6, SMA holes 6.6 6.8 7.0, the base's own corner and nut pocket, names face down at 2.0 2.2 2.6"));

// Two screw lengths, not one: the near pair's heads land on the low deck and the
// far pair's on the raised deck, 12.3 mm higher.
echo(str("screws: near pair M3 x 30 (needs ", LOW_TOP - (FLOOR_TOP + NUT_DEEP - 1),
         "), far pair M3 x 45 (needs ", HIGH_TOP - (FLOOR_TOP + NUT_DEEP - 1), ")"));

echo("-- wire slots: flat ceiling left after the 45 deg gable (0 = none) --");
for (c = REAR) {
  p = c[5]; w = (c[2]+p) - (c[1]-p); z1 = c[4]+c[6]+p;
  r = gable_rise(w, z1, COVER_SIT - WALL);
  echo(str("   base  ", c[0], "  width ", w, " -> flat ", w - 2*r));
}
for (c = FAR_SIDE) {
  w = c[2]-c[1] + 2*FIT; z1 = c[3] + FIT;
  r = (z1 > HIGH_IN - WALL) ? -1 : gable_rise(w, z1, HIGH_IN - 0.5);
  echo(str("   cover ", c[0], "  width ", w, " -> ",
           r < 0 ? "runs out through the top edge, no ceiling" : str("flat ", w - 2*r)));
}
echo("   vents  none - version 2, SPEC.md decision 1");
echo(str("pole marks at z ", POLE_Z, ", in the band ", FLOOR_BOT, " .. ", POLE_TOP,
         " (", POLE_TOP - FLOOR_BOT, " mm for ", POLE_SIZE, " text)"));

// The DC jack and the USB-C sit 5.0 mm apart (152.5 -> 157.5). Negative here
// means the two openings merge into one, which they do. See REAR in
// housing-params.scad for why that is the right answer.
RIB_DC_USB = 5.0 - PAD_USB - PAD_DC;
echo(str("   DC/USB rib ", RIB_DC_USB, " mm -> ",
         RIB_DC_USB <= 0 ? "merged: 5 connectors, 4 openings"
                         : "separate, 5 openings"));

// ---- printing ----------------------------------------------------------------
// Measured on the version 2 STLs, not estimated. Nothing needs support:
//   base        bottom face on the plate. The only flat ceilings left are the
//               tops of the pole-mark grooves, 0.6 mm deep and 7 mm2 in all, and
//               with the white part loaded they are filled. Nut pockets roofed
//               at 49 degrees, wire entries gabled at 45, no vents.
//   cover-low, cover-high
//               face down, as exported. Apart from the bed face, only the floors
//               of the name grooves - which the white parts fill.
//   bed       190 x 110 - fits 256 x 256; does NOT fit an A1 mini (180 x 180)
//   PLA       base 102 g, cover-low 28.6 g, cover-high 35.5 g; white 0.4 g
//   walls     set wall loops to 4 or more. Every wall here is 2.0 mm, which at
//             0.42 mm line width is 4.8 lines; at the default 2 loops the middle
//             of every wall is infill, including the 2.00 mm rib between the
//             J903 and J905 terminal openings.
//   wall generator
//             ARACHNE, not Classic, which is what the A1 profile starts with.
//             Sliced in Bambu Studio 2026-10-09 on the coupon, which carries
//             the cover's own 2.2 names: with Classic the first layer - the
//             face you read - put white on 0.8 % of "H-BRIDGE COIL" and under
//             16 % of every other 2.2 name. Their strokes are 0.44 mm, the
//             first-layer line is 0.5 mm, and elephant-foot compensation takes
//             0.075 off each side, so Classic drops them. With Arachne it is
//             95-97 %. The 3.2 names come out either way.
//   infill    25%. The four bosses are the only bulk and they carry the screws.
//   brim      yes. 190 mm of 2 mm floor is a corner-lift shape.
//   support   none.
//   colour    load each part together with its -labels.stl and answer Yes to
//             "load as a single object with multiple parts"; the labels part is
//             white, the body a dark colour so the white reads. The covers'
//             names are the first 3 layers; the base's marks are on an upright
//             wall and span about 16 - SPEC.md decision 4 accepts the swaps.
//             No AMS: print the bodies alone and every name is still engraved.
