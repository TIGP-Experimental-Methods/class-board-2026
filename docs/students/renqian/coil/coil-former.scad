// NMR receive coil former, multi-layer, with an integrated tube stop.
// 2026-10-02.
//
// WHY
// The whole noise budget rests on the coil's inductance:
//
//     2.53 mH at 89.4 kHz  ->  C = 1.25 nF to resonate
//     loaded Q = 10        ->  R_p = 14.2 kohm
//     sqrt(4kTR)           ->  15.3 nV/rtHz, the floor no amplifier beats
//
// and it is what decides whether the OPA1656 or the OPA1612 is right, because
// the crossover impedance e_n/i_n falls either side of 14.2 kohm. Hand-wind the
// coil twice and you get two inductances, so none of those numbers describe the
// thing on the bench. This former fixes the diameter, the winding window and
// where the sample sits inside it.
//
// WHY MULTI-LAYER
// The first version of this file had a single layer and the sums said so: to
// reach 2.53 mH on a 19 mm former in one layer takes about 2900 turns and a
// coil 1.2 m long. A receive coil at 89 kHz is a multi-layer solenoid - the
// flanges here enclose a winding WINDOW, length by depth, and you fill it.
//
// HOW IT WORKS
// You give the window; the file tells you how many turns fit, what inductance
// that should give and what capacitor resonates it. Tune WIND_L and WIND_D
// until the inductance is the one you want, then wind until the window is full.
// No spiral groove: a 0.4 mm nozzle cannot cut one at magnet-wire pitch, and a
// half-formed groove makes the winding less repeatable, not more.
//
// PLAIN PLASTIC ONLY - PLA or PETG. NEVER carbon-filled or metal-filled
// filament: carbon fibre conducts, so it carries eddy currents in the coil's
// own field and damps the thing you are trying to measure.
//
// EVERYTHING MARKED "MEASURE" IS A GUESS.

include <BOSL2/std.scad>
$fa = 2; $fs = 0.4;

// ---- the sample --------------------------------------------------------------
TUBE_OD    = 15.0;  // MEASURE: outside diameter of your water tube
TUBE_FIT   = 0.4;   // slack - glass does not forgive being forced
STOP_DEPTH = 30.0;  // MEASURE: how far the tube goes in before it stops. Set it
                    // so the water column sits centred in the window.

// ---- the winding window ------------------------------------------------------
WIRE_D  = 0.40;     // MEASURE: enamelled copper, including the enamel
PACK    = 1.05;     // turns never pack perfectly
WIND_L  = 38.5;    // window length. 38.5 x 2.7 lands on the 2.53 mH the design
                   // notes assume - see the sweep in the echo below if you change
                   // the wire or the tube
WIND_D  = 2.7;     // window depth, i.e. how many layers deep it can go

// ---- the part ----------------------------------------------------------------
WALL      = 1.6;    // former wall; thin keeps the coil close to the sample
FLANGE_T  = 2.0;
FLANGE_EXTRA = 4.0; // how far the flanges stand above the full winding
LEAD_IN   = 12.0;   // plain barrel before the first flange, for the tube to enter
FOOT_W    = 34.0;   // MEASURE: a flat foot so it sits the same way up every time
FOOT_T    = 3.0;    //          replace with whatever your magnet needs
FOOT_HOLE = 3.3;    // M3 clearance

// ---- derived -----------------------------------------------------------------
BORE   = TUBE_OD + 2 * TUBE_FIT;
FORM_D = BORE + 2 * WALL;               // inner diameter of the winding
PITCH  = WIRE_D * PACK;

TURNS_PER_LAYER = floor(WIND_L / PITCH);
LAYERS          = floor(WIND_D / PITCH);
TURNS           = TURNS_PER_LAYER * LAYERS;

FLANGE_D = FORM_D + 2 * (WIND_D + FLANGE_EXTRA);
TOTAL_L  = LEAD_IN + FLANGE_T + WIND_L + FLANGE_T;

// Wheeler's multi-layer approximation, converted to mm:
//   L(uH) = 0.8 a^2 N^2 / (25.4 * (6a + 9b + 10c))
// a = mean winding radius, b = winding length, c = winding depth.
A_MEAN = FORM_D/2 + WIND_D/2;
L_UH   = 0.8 * A_MEAN*A_MEAN * TURNS*TURNS
         / (25.4 * (6*A_MEAN + 9*WIND_L + 10*WIND_D));

// C in nF to resonate at f in kHz with L in uH. Checked against the known pair:
// 2530 uH at 89.4 kHz gives 1.253 nF, which is the number in the design notes.
F0_KHZ = 89.4;
C_NF   = 1e9 / (4 * PI * PI * F0_KHZ*F0_KHZ * L_UH);

WIRE_M = PI * (FORM_D + WIND_D) * TURNS / 1000;   // at the mean diameter

module former() {
  difference() {
    union() {
      cylinder(d = FORM_D, h = TOTAL_L);                       // the barrel
      translate([0, 0, LEAD_IN])
        cylinder(d = FLANGE_D, h = FLANGE_T);                  // lower flange
      translate([0, 0, TOTAL_L - FLANGE_T])
        cylinder(d = FLANGE_D, h = FLANGE_T);                  // upper flange
      linear_extrude(FOOT_T)
        square([FOOT_W, FLANGE_D], center = true);             // flat foot
    }

    // bore, open right through so the tube can be rinsed in place
    translate([0, 0, -1]) cylinder(d = BORE, h = TOTAL_L + 2);

    // the tube stop: a step the tube bottoms out on, so the sample sits at the
    // same height in the window every time
    translate([0, 0, STOP_DEPTH]) cylinder(d = BORE - 2.4, h = TOTAL_L);

    // a notch through each flange to lead the wire ends away
    for (a = [0, 180])
      rotate([0, 0, a])
        translate([FORM_D/2 - 1, -WIRE_D*1.5, LEAD_IN - 1])
          cube([WIND_D + FLANGE_EXTRA + 2, WIRE_D*3, TOTAL_L]);

    for (x = [-FOOT_W/2 + 5, FOOT_W/2 - 5])
      translate([x, 0, -1]) cylinder(d = FOOT_HOLE, h = FOOT_T + 2);

    // the winding recipe, on the part - a jig whose numbers live only in a file
    // is a jig whose numbers get lost
    translate([0, -FLANGE_D/2 + 3.5, TOTAL_L - 0.6])
      linear_extrude(1)
        text(str(TURNS, "T ", WIRE_D, "mm"), size = 3.0,
             halign = "center", valign = "center",
             font = "Liberation Sans:style=Bold");
  }
}

former();

echo(str("bore ", BORE, " for a ", TUBE_OD, " mm tube; winding starts at d ", FORM_D));
echo(str("window ", WIND_L, " long x ", WIND_D, " deep"));
echo(str("  -> ", TURNS_PER_LAYER, " turns per layer x ", LAYERS, " layers = ",
         TURNS, " turns"));
echo(str("overall ", FLANGE_D, " dia x ", TOTAL_L, " long"));
echo("-- what this window should give --");
echo(str("   L ~ ", L_UH/1000, " mH      (Wheeler multi-layer)"));
echo(str("   C ~ ", C_NF, " nF to resonate at ", F0_KHZ, " kHz"));
echo(str("   wire ~ ", WIRE_M, " m"));
echo("Wheeler is an approximation and ignores the glass and the water.");
echo("Measure the finished coil on an LCR bridge and use THAT number.");
