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
// It is PRINTED AS TWO PARTS, split at SPLIT_Y - see cover_low() and
// cover_high() at the end. cover() is still the whole thing, for looking at,
// for the DXF and for the section view; nothing prints it.
//
// Defines cover(), cover_low() and cover_high(); render them through
// housing.scad with PART = "cover", "cover_low", "cover_high" or "cover2d".

include <BOSL2/std.scad>
include <housing-params.scad>
include <housing-shapes.scad>

// Locating lip, hanging into the base's cavity, FIT inside its inner wall.
module cover_lip()
  translate([CTRB.x, CTRB.y, COVER_SIT - LIP_H])
    rect_tube(h = LIP_H, wall = LIP_W, anchor = BOTTOM,
              isize = [ISIZE.x - 2*FIT - 2*LIP_W, ISIZE.y - 2*FIT - 2*LIP_W]);

// What holds the lip on under the raised box. Found when the cover was split:
// the lip sits FIT inside the cover's wall (it has to - it drops into the base,
// whose inner face is right under the cover's), so nothing joins them sideways;
// under the low deck the deck plate joins them from above, but under the raised
// box the hollow was cut from z 2.9, which took the top of the lip as well. What
// was left was a ring 0.9..2.9 touching nothing - printed face down, a 545 mm2
// strip in mid-air 15.3 mm above the bed. This fills from the wall's inner face
// in to the lip's inner face and tapers back to the wall at 45 degrees, so it
// prints on its own. Under the raised box only: under the low deck it would
// stand 0.3 mm proud of the deck top.
LIP_ROOT = FIT + LIP_W;   // 2.3 - the wall's inner face to the lip's inner face
module cover_lip_root()
  intersection() {
    translate([CTRB.x, CTRB.y, COVER_SIT])
      rect_tube(h = LIP_ROOT, anchor = BOTTOM,
                size   = [ISIZE.x + 1, ISIZE.y + 1],   // 0.5 into the wall: merges
                isize1 = [ISIZE.x - 2*LIP_ROOT, ISIZE.y - 2*LIP_ROOT],
                isize2 = ISIZE);
    translate([-50, SPLIT_Y - 150, -50]) cube([300, 150, 100]);
  }

// The names, flat. One definition, used both to cut the engraving and - by the
// difference at the end of this file - to make the inlay that fills it.
module sma_names()
  for (L = SMA_LABELS)
    translate([L[0], L[1] + 6.5])
      text(L[2], size = 3.2, halign = "center", valign = "center",
           font = "Liberation Sans:style=Bold");

module deck_names()
  for (L = DECK_LABELS)
    translate([L[0], L[1]])
      text(L[2], size = L[4], halign = L[3], valign = "center",
           font = "Liberation Sans:style=Bold");

// Version 2: the rear connectors' names along the low cover's rear edge, and
// my name - SPEC.md decision 6. Both on the low deck, both in the same inlay.
module rear_names()
  for (L = REAR_NAMES)
    translate([L[1], REAR_NAME_ROW[L[2]]])
      text(L[0], size = REAR_NAME_SIZE, halign = "center", valign = "center",
           font = "Liberation Sans:style=Bold");

module my_name()
  translate([MY_NAME[1], MY_NAME[2]])
    text(MY_NAME[0], size = MY_NAME[3], halign = "center", valign = "center",
         font = "Liberation Sans:style=Bold");

module cover(engrave = true) {
  difference() {
    union() {
      // low deck over the SMA field - threads stand 5.5 mm proud of its top
      translate([CTRB.x, (SPLIT_Y + OUT_Y1)/2, COVER_SIT])
        cuboid([OSIZE.x, OUT_Y1 - SPLIT_Y, WALL], anchor = BOTTOM);
      // raised box over the OLED / TX terminal end
      translate([CTRB.x, (SPLIT_Y + OUT_Y0)/2, COVER_SIT])
        cuboid([OSIZE.x, SPLIT_Y - OUT_Y0, HIGH_TOP - COVER_SIT], anchor = BOTTOM);
      cover_lip();
      cover_lip_root();
    }

    // hollow the raised box - but not the lip or the root that holds it on
    difference() {
      translate([CTRB.x, (SPLIT_Y + OUT_Y0)/2, COVER_SIT - 1])
        cuboid([OSIZE.x - 2*WALL, SPLIT_Y - OUT_Y0 - 2*WALL, HIGH_IN - COVER_SIT + 1],
               anchor = BOTTOM);
      cover_lip();
      cover_lip_root();
    }

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
    // "Deep enough" means from below the lip's bottom edge, NOTCH_Z0. It used to
    // start at COVER_SIT - 1 = 2.9, which cleared only the top 1 mm of a lip that
    // reaches down to 0.9 - so a 2 mm strip of lip still stood across every
    // notch, and once the cover was printed face down each strip was a bridge
    // 10.8 to 26 mm long at the very top of the print.
    NOTCH_Z0 = COVER_SIT - LIP_H - 1;
    for (c = FAR_SIDE) {
      ztop = (c[3] + FIT > HIGH_IN - WALL) ? HIGH_TOP + 1 : c[3] + FIT;
      if (ztop > HIGH_TOP)
        translate([(c[1]+c[2])/2, OUT_Y0 + 4, (NOTCH_Z0 + ztop)/2])
          cuboid([c[2]-c[1] + 2*FIT, 2*WALL + 12, ztop - NOTCH_Z0]);
      else
        wire_slot((c[1]+c[2])/2, c[2]-c[1] + 2*FIT, NOTCH_Z0, ztop,
                  HIGH_IN - 0.5, OUT_Y0 + 4, 2*WALL + 12);
    }

    // The panel silkscreen is hidden under the cover, so the names go on top,
    // engraved ENGRAVE deep - and then filled with a second colour, see the
    // labels at the end of this file. engrave = false gives the cover with no
    // names cut, which is only there so the labels can be worked out from it.
    if (engrave) {
      translate([0, 0, LOW_TOP - ENGRAVE])  linear_extrude(ENGRAVE + 1) {
        sma_names(); rear_names(); my_name();
      }
      translate([0, 0, HIGH_TOP - ENGRAVE]) linear_extrude(ENGRAVE + 1) deck_names();
    }

    // the four screws
    for (h = HOLES)
      translate([h.x, h.y, COVER_SIT-1]) cylinder(d = M3_CLEAR, h = HIGH_TOP+2);
  }
}

// ---- the split ---------------------------------------------------------------
// Why two parts. A printed part needs one flat face that can lie on the bed,
// and the cover has two - the low deck top at 5.9 and the raised top at 18.2,
// 12.3 mm apart. Measured on the one-piece cover.stl: printed face down, the
// whole low deck was a 10 658 mm2 flat ceiling 12.3 mm above the bed, held
// along one edge; printed the other way up it was worse, 11 056 mm2 at 3 mm
// plus 7 359 mm2 at 15.3 mm. Either way it broke the brief's "no overhang
// steeper than 45 degrees, so the parts print without supports". Workshop 3
// A.5 gives the remedy in three words: "split the part".
//
// The cut is at SPLIT_Y, where the design already changes height, so nothing
// is cut through except the locating lip, which each half keeps a U of:
//   cover_low   y SPLIT_Y+FIT .. -10   the deck over the SMA field, its 16
//               names, the near pair of screws (y = -19)
//   cover_high  y -120 .. SPLIT_Y      the raised box, OLED window, Qwiic, LEDs,
//               the far-edge notches, its names, the far pair (y = -111)
// Each half has two of the four screws, so no new fastener. The low half is
// what gives up the FIT gap at the joint - it loses 0.3 mm of deck nobody will
// miss, where taking it off the high half would thin its 2 mm end wall.
// The 16 SMA barrels through the low deck locate it far better than the lip.
//
// Both come out FACE DOWN, top on the bed, ready for the plate - the class
// prints these after the cutoff, and a cover printed the wrong way up is the
// expensive mistake. rotate 180 about x maps (x, y, z) -> (x, -y, -z); then
// the old top face is lifted to z = 0. clash-test.py undoes exactly this.

module low_half()  translate([-50, SPLIT_Y + FIT, -50]) cube([300, 150, 100]);
module high_half() translate([-50, SPLIT_Y - 150, -50]) cube([300, 150, 100]);

module cover_low_asm()  intersection() { cover(); low_half(); }
module cover_high_asm() intersection() { cover(); high_half(); }

module face_down(top) translate([0, 0, top]) rotate([180, 0, 0]) children();

module cover_low()  face_down(LOW_TOP)  cover_low_asm();
module cover_high() face_down(HIGH_TOP) cover_high_asm();

// ---- the names, in a second colour --------------------------------------------
// The brief: "label text as cutouts in the cover with a white sheet behind".
// Engraved names in the cover's own colour cannot be read across a bench, so
// they have to differ in colour - but not by cutting through. A, O, R, Q, 4, 6,
// 8 and 0 all have closed middles that would fall out, and nearly every name
// here has one (AI1, AO2, TRIG, QWIIC, MODULE). And there is nowhere for a
// sheet: the low deck sits FIT = 0.3 mm over the SMA hex bases, so a sheet
// means a higher deck and less thread for the plug nut.
//
// So the names are an inlay: a separate part that exactly fills the 0.6 mm
// engraving, printed in white. It is worked out as the cover without names
// minus the cover with them, so it is precisely what the engraving removed -
// clipped by every hole and window without having to list them again.
//
// In Bambu Studio: import cover-low.stl and cover-low-labels.stl TOGETHER and
// answer Yes to "load as a single object with multiple parts", then give the
// labels part white. Same for the high half. Printed face down, the names are
// the first three layers only, so the AMS swaps colour a handful of times, not
// every layer. With no AMS, print the cover alone: the names are still there,
// engraved.
module cover_low_labels_asm()
  intersection() { difference() { cover(engrave = false); cover(); } low_half(); }
module cover_high_labels_asm()
  intersection() { difference() { cover(engrave = false); cover(); } high_half(); }

module cover_low_labels()  face_down(LOW_TOP)  cover_low_labels_asm();
module cover_high_labels() face_down(HIGH_TOP) cover_high_labels_asm();
