// Housing - Ren Qian (Section A), 2026-10-02.
// This is the entry point. Set PART, press F5, export with F6.
//
//   PART = "base"     the tray: wall, floor, four M3 bosses with nut pockets,
//                     the rear connector openings, ventilation slots
//   PART = "cover_low"   the cover's low deck over the SMA field     -> cover-low.stl
//   PART = "cover_high"  the cover's raised box over the OLED end    -> cover-high.stl
//                        Both come out FACE DOWN, ready for the plate. The cover
//                        has two heights 12.3 mm apart and cannot print as one
//                        part without supports - see the split in housing-cover.
//   PART = "cover"       the whole cover in place, for looking at only
//   PART = "coupon"      the fit test. PRINT THIS ONE FIRST
//   PART = "cover2d"     flat outline of the whole cover, for cover.dxf
//
// The work is split across four more files, each of which opens on its own:
//   housing-params.scad   every number, and which of them are measured facts
//   housing-shapes.scad   the two opening shapes, and where the vents go
//   housing-base.scad     module base()
//   housing-cover.scad    cover(), and its two printed halves
//   housing-coupon.scad   module coupon()
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

PART = "base";  // [base, cover_low, cover_high, cover, coupon, cover2d, assembly]

include <BOSL2/std.scad>
include <housing-params.scad>
include <housing-shapes.scad>
include <housing-base.scad>
include <housing-cover.scad>
include <housing-coupon.scad>

if (PART == "base")       base();
if (PART == "cover_low")  cover_low();
if (PART == "cover_high") cover_high();
if (PART == "cover")      cover();
if (PART == "coupon")  coupon();
if (PART == "cover2d") projection(cut = false) cover();

// Everything in place for housing.png: the boards where they really sit, and the
// two cover halves lifted and pulled apart so the split shows. Preview only (F5);
// the colours do not survive F6.
EXPLODE_Z = 28;
EXPLODE_Y = 10;
if (PART == "assembly") {
  color("Teal")          base();
  color("ForestGreen")   import("../../../../hardware/release/front-panel.stl");
  color("DarkGreen")     translate([180, 0, -BOARD_GAP]) rotate([0, 180, 0])
                           import("../../../../hardware/release/class-board.stl");
  color("SteelBlue")     translate([0, 0, EXPLODE_Z])              cover_low_asm();
  color("LightSteelBlue") translate([0, -EXPLODE_Y, EXPLODE_Z])    cover_high_asm();
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
echo(str("coupon holes 3.0..3.6 step 0.1, nut pocket ", NUT_AF, " af x ", NUT_DEEP));

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
echo(str("   vents  stadium ", VENT_W, " mm wide, no ceiling at all"));

// The DC jack and the USB-C sit 5.0 mm apart (152.5 -> 157.5). Negative here
// means the two openings merge into one, which they do. See REAR in
// housing-params.scad for why that is the right answer.
RIB_DC_USB = 5.0 - PAD_USB - PAD_DC;
echo(str("   DC/USB rib ", RIB_DC_USB, " mm -> ",
         RIB_DC_USB <= 0 ? "merged: 5 connectors, 4 openings"
                         : "separate, 5 openings"));

// ---- printing ----------------------------------------------------------------
// Measured on base.stl, not estimated: the ONLY flat ceilings in the base are
// the four nut pockets, 221 mm2 in total at z = -22.90, each one a 5.8 mm
// bridge. Everything else that faces downward is either a wall or a 45.0 degree
// gable. So: no supports. Turning them on would fill the vents and the nut
// pockets with material that cannot be got out again.
//   bed       190 x 110 - fits 256 x 256; does NOT fit an A1 mini (180 x 180)
//   volume    79.2 cm3 -> about 88 g of PLA
//   walls     set wall loops to 4 or more. Every wall here is 2.0 mm, which at
//             0.42 mm line width is 4.8 lines; at the default 2 loops the middle
//             of every wall is infill, including the 2.00 mm rib between the
//             J903 and J905 terminal openings.
//   infill    25%. The four bosses are the only bulk and they carry the screws.
//   brim      yes. 190 mm of 2 mm floor is a corner-lift shape.
//   support   none. See above.
