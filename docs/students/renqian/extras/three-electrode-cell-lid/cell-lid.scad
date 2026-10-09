// Three-electrode cell lid - fixes the electrode geometry between runs.
// 2026-10-02.
//
// WHY THIS EXISTS
// The uncompensated resistance you are fighting is the solution resistance
// between the working electrode and the tip of the reference. Move the
// reference 2 mm further away and iR drop changes; clamp the electrodes by hand
// and it changes every time you set the cell up. Two experiments run a week
// apart are then not comparable, and no amount of post-hoc iR compensation
// fixes a geometry you did not record.
//
// A lid with the holes in fixed places does not make the geometry correct - it
// makes it the SAME, which is what lets you compare runs and what lets you
// write the spacing down in the method.
//
// PRINT IN PETG, not PLA. PLA is attacked by many solvents and softens around
// 60 C; PETG holds up to the usual aqueous electrolytes and to splashes of
// organics, and takes about 80 C. If the cell sees anything aggressive, check
// the specific chemistry rather than trusting this note - and never print a
// lid for an experiment where a failure would be dangerous.
//
// EVERYTHING MARKED "MEASURE" IS A GUESS. Measure your own cell and electrodes
// with a caliper before printing. The defaults are typical, not yours.

include <BOSL2/std.scad>
$fa = 2; $fs = 0.4;

// ---- the cell ----------------------------------------------------------------
CELL_OD   = 52.0;   // MEASURE: outside diameter of the beaker/cell at the rim
                    //          (100 mL beaker is about 52, 50 mL about 42)
SKIRT_H   = 6.0;    // how far the lid drops over the rim before it stops
SKIRT_GAP = 0.6;    // slack so it goes on wet-gloved; PETG does not flex much
LID_T     = 5.0;    // lid thickness - also the length of hole that guides an
                    // electrode, so thicker holds the angle better

// ---- the electrodes ----------------------------------------------------------
// MEASURE each shaft. These are common sizes, not yours.
WE_D = 6.0;         // MEASURE: working electrode body
CE_D = 6.0;         // MEASURE: counter electrode body (a bare Pt wire is ~1)
// A fat reference CANNOT sit close to the working electrode - two 6 mm shafts
// need their centres 8 mm apart before there is any plastic left between the
// holes, and the electrochemistry wants a few mm. That conflict is exactly why
// a Luggin capillary exists: a thin bent tube whose tip reaches in close while
// the reference body stays out of the way. Put the capillary diameter here, not
// the reference's.
RE_D = 3.0;         // MEASURE: the Luggin capillary (or the reference body if
                    //          you are not using one - then raise WE_RE below)
GAS_D = 4.0;        // MEASURE: sparge tube outside diameter
FIT  = 0.4;         // slack per hole. Electrodes are glass or PTFE and do not
                    // forgive being forced; this is deliberately loose.
MIN_WALL = 1.5;     // least plastic allowed between two holes

// ---- the geometry that matters -----------------------------------------------
// WE_RE is the one number this whole part exists to hold constant. Keep the
// reference close to the working electrode - a few mm - because everything
// between them is uncompensated resistance. Too close and it shields the WE and
// distorts the current distribution; the usual compromise is about twice the
// reference tip diameter away.
WE_RE  = 7.0;       // centre to centre, WE to RE. The check at the bottom of
                    // this file says whether your diameters actually allow it.
WE_CE  = 20.0;      // WE to CE, facing each other across the cell for an even
                    // current distribution
GAS_R  = 18.0;      // sparge tube, off to one side so bubbles do not rise past
                    // the working electrode and chop the current
VENT_D = 5.0;       // the cell must not seal - sparging into a closed vessel
                    // builds pressure

// ---- derived -----------------------------------------------------------------
SKIRT_ID = CELL_OD + SKIRT_GAP;
LID_OD   = SKIRT_ID + 2 * 3.0;         // 3 mm skirt wall
CH       = 0.6;                        // chamfer at each hole mouth, so a glass
                                       // shaft finds the hole instead of chipping

// Hole positions, from the lid centre. WE sits at the centre: it is the one you
// want reproducibly placed, and putting it on the axis means a round cell cannot
// put it anywhere else.
WE_POS = [0, 0];
RE_POS = [WE_RE, 0];
CE_POS = [-WE_CE, 0];
GAS_POS = [0, GAS_R];
VENT_POS = [0, -GAS_R];

module hole(pos, d) {
  translate([pos.x, pos.y, -1])
    cylinder(d = d + 2 * FIT, h = LID_T + 2);
  // chamfer top and bottom
  translate([pos.x, pos.y, LID_T - CH])
    cylinder(d1 = d + 2 * FIT, d2 = d + 2 * FIT + 2 * CH, h = CH + 0.01);
  translate([pos.x, pos.y, 0])
    cylinder(d1 = d + 2 * FIT + 2 * CH, d2 = d + 2 * FIT, h = CH);
}

module lid() {
  difference() {
    union() {
      // the lid plate
      cylinder(d = LID_OD, h = LID_T);
      // the skirt, which is what stops it sliding off the rim
      translate([0, 0, -SKIRT_H])
        tube(h = SKIRT_H, id = SKIRT_ID, wall = 3.0, anchor = BOTTOM);
    }
    hole(WE_POS,  WE_D);
    hole(RE_POS,  RE_D);
    hole(CE_POS,  CE_D);
    hole(GAS_POS, GAS_D);
    hole(VENT_POS, VENT_D);

    // The spacing engraved on the part, because a jig whose dimensions live
    // only in a file is a jig whose dimensions get lost.
    translate([0, LID_OD/2 - 7, LID_T - 0.6])
      linear_extrude(1)
        text(str("WE-RE ", WE_RE, "  WE-CE ", WE_CE), size = 3.2,
             halign = "center", valign = "center",
             font = "Liberation Sans:style=Bold");
  }
}

lid();

echo(str("cell OD assumed ", CELL_OD, " -> skirt id ", SKIRT_ID, ", lid od ", LID_OD));
echo(str("WE-RE ", WE_RE, " mm   WE-CE ", WE_CE, " mm   (these are the numbers to"));
echo(    "   write into your method, and to keep the same between runs)");
echo(str("holes: WE ", WE_D + 2*FIT, "  CE ", CE_D + 2*FIT, "  RE ", RE_D + 2*FIT,
         "  gas ", GAS_D + 2*FIT, "  vent ", VENT_D));

// Does the geometry you asked for physically exist? Two holes need their centres
// at least (r1 + r2 + MIN_WALL) apart or they merge into one slot - which is
// what happened the first time this was drawn, with a 6 mm reference 5 mm from
// a 6 mm working electrode.
function need(d1, d2) = (d1 + 2*FIT)/2 + (d2 + 2*FIT)/2 + MIN_WALL;
echo("-- hole spacing check --");
echo(str("   WE-RE  asked ", WE_RE, "  needs ", need(WE_D, RE_D),
         WE_RE >= need(WE_D, RE_D) ? "   ok" : "   <<< HOLES WILL MERGE"));
echo(str("   WE-CE  asked ", WE_CE, "  needs ", need(WE_D, CE_D),
         WE_CE >= need(WE_D, CE_D) ? "   ok" : "   <<< HOLES WILL MERGE"));
echo(str("   WE-gas asked ", GAS_R, "  needs ", need(WE_D, GAS_D),
         GAS_R >= need(WE_D, GAS_D) ? "   ok" : "   <<< HOLES WILL MERGE"));
echo(    "PETG, not PLA. Every MEASURE value above is a guess until you check it.");
