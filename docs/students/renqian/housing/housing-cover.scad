// Housing - the cover, which has two heights.
// Ren Qian (Section A), 2026-10-02.
//
// The brief's trap: the OLED stands 13.82 mm above the panel face and the TX
// terminal 14.10, but an SMA jack only 9.8, so a flat plate resting on the OLED
// leaves every SMA thread about 4 mm below the surface and no plug nut will
// reach it. Measuring the panel mesh showed those two tall parts are the only
// things above the SMA threads, and both sit at y < -70 while the whole SMA
// field sits at y > -70. So the cover splits there: a low deck over the jacks,
// a raised box over the other end.
//
// Defines module cover() only; render it through housing.scad with
// PART = "cover", or PART = "cover2d" for the flat outline.

include <BOSL2/std.scad>
include <housing-params.scad>
include <housing-shapes.scad>

module cover() {
  difference() {
    union() {
      // low deck over the SMA field - threads stand 5.5 mm proud of its top
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
      cuboid([OLED[1].x-OLED[0].x - 2*FIT, OLED[1].y-OLED[0].y - 2*FIT, WALL+2],
             anchor = BOTTOM);
    // the TX terminal pokes out of the top
    translate([(TXT[0].x+TXT[1].x)/2, (TXT[0].y+TXT[1].y)/2, HIGH_IN-1])
      cuboid([TXT[1].x-TXT[0].x + 2*FIT, TXT[1].y-TXT[0].y + 2*FIT, WALL+2],
             anchor = BOTTOM);

    // "through the panel's outer face": holes in the top of the raised deck
    for (c = PANEL_TOP)
      translate([(c[1]+c[2])/2, (c[3]+c[4])/2, HIGH_IN-1])
        cuboid([c[2]-c[1] + 2*FIT, c[4]-c[3] + 2*FIT, WALL+2], anchor = BOTTOM);

    // "their wires come from the side": a notch in the far wall for each.
    // A notch whose top would land within WALL of the raised deck leaves an
    // unprintable sliver of wall above it - the TX terminal does, 15.70 + FIT
    // against an inner face at HIGH_IN - so those run out through the top edge.
    // The cut is also deep enough to clear the locating lip, which would
    // otherwise stand straight across the wire's path into the terminal.
    for (c = FAR_SIDE) {
      ztop = (c[3] + FIT > HIGH_IN - WALL) ? HIGH_TOP + 1 : c[3] + FIT;
      if (ztop > HIGH_TOP)
        translate([(c[1]+c[2])/2, OUT_Y0 + 4, (COVER_SIT - 1 + ztop)/2])
          cuboid([c[2]-c[1] + 2*FIT, 2*WALL + 12, ztop - (COVER_SIT - 1)]);
      else
        wire_slot((c[1]+c[2])/2, c[2]-c[1] + 2*FIT, COVER_SIT - 1, ztop,
                  HIGH_IN - 0.5, OUT_Y0 + 4, 2*WALL + 12);
    }

    // The panel silkscreen is hidden under the cover, so the names go on top.
    // Engraved, not raised: nothing to knock off, and it needs no support.
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
    for (h = HOLES)
      translate([h.x, h.y, COVER_SIT-1]) cylinder(d = M3_CLEAR, h = HIGH_TOP+2);
  }
}
