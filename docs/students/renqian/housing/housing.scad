// Housing - Ren Qian (Section A), 2026-10-02.
// This is the entry point. Set PART, press F5, export with F6.
//
//   PART = "base"     the tray: wall, floor, four M3 bosses with nut pockets,
//                     five rear connector openings, ventilation slots
//   PART = "cover"    two heights - a low deck over the SMA field so the threads
//                     come through, a raised box over the OLED / TX terminal end
//   PART = "coupon"   the fit test. PRINT THIS ONE FIRST
//   PART = "cover2d"  flat outline of the cover, for cover.dxf
//
// The work is split across four more files, each of which opens on its own:
//   housing-params.scad   every number, and which of them are measured facts
//   housing-shapes.scad   the two opening shapes, and where the vents go
//   housing-base.scad     module base()
//   housing-cover.scad    module cover()
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

PART = "base";          // "base" | "cover" | "coupon" | "cover2d"

include <BOSL2/std.scad>
include <housing-params.scad>
include <housing-shapes.scad>
include <housing-base.scad>
include <housing-cover.scad>
include <housing-coupon.scad>

if (PART == "base")    base();
if (PART == "cover")   cover();
if (PART == "coupon")  coupon();
if (PART == "cover2d") projection(cut = false) cover();

// ---- check the numbers -------------------------------------------------------
echo(str("PART = ", PART));
echo(str("base   outer ", OSIZE.x, " x ", OSIZE.y, " x ", COVER_SIT-FLOOR_BOT,
         "   bed 256: ", (OSIZE.x<=256 && OSIZE.y<=256) ? "ok" : "NO"));
echo(str("cover  sits at z ", COVER_SIT, "  low deck top ", LOW_TOP,
         "  raised top ", HIGH_TOP));
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
