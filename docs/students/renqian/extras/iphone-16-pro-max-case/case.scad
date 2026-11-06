// iPhone 16 Pro Max case
// 2026-10-02. Nothing to do with the class board - kept out of that repository.
//
// PRINT THIS IN TPU, not PLA. A case has to stretch over the phone to get on and
// come off again; PLA will not flex, so either it will not go on at all or it
// cracks at a corner the first time you take it off. TPU 95A, printed slowly
// (20-30 mm/s) and fed from an external spool rather than the AMS.
//
// WHAT IS VERIFIED AND WHAT IS NOT
//   Verified from Apple's tech specs: the body is 163.0 x 77.6 x 8.25 mm.
//   Everything else below - the corner radius, the camera island, and every
//   button and port position - Apple does not publish. The numbers here are
//   estimates and WILL be slightly wrong. Measure your own phone with a caliper
//   (or a ruler against the edge) and correct them before printing the real one.
//   Each one is marked MEASURE.
//
// Measure from the TOP-LEFT corner of the BACK of the phone, looking at the back.

include <BOSL2/std.scad>
$fa = 2; $fs = 0.4;

// ---- verified ----------------------------------------------------------------
PH_H = 163.0;      // Apple tech specs
PH_W = 77.6;
PH_D = 8.25;

// ---- my choices --------------------------------------------------------------
FIT   = 0.35;      // slack around the phone. TPU 0.3-0.4; for a rigid material use 0.6+
WALL  = 2.0;       // side wall
BACK_T  = 1.4;       // back panel
LIP   = 1.8;       // how far the case folds over the front glass, all round
// BOSL2's cuboid takes rounding OR chamfer, not both, and the vertical corners
// are the ones that matter here - so the outer back edge is left square. In TPU
// that is soft enough not to notice.

// ---- MEASURE these -----------------------------------------------------------
PH_R  = 11.5;      // MEASURE: corner radius of the phone body
                   // too small and the case will not seat; too large leaves a gap

// Camera island, as a rectangle on the back. MEASURE all four.
CAM_X = 7.0;       // MEASURE: from the left edge to the left side of the island
CAM_Y = 7.0;       // MEASURE: from the top edge to the top of the island
CAM_W = 38.5;      // MEASURE: island width
CAM_H = 38.5;      // MEASURE: island height
CAM_R = 10.0;      // MEASURE: island corner radius
CAM_PAD = 1.2;     // extra clearance round the island so the case never touches a lens

// Buttons. Y is measured DOWN from the top edge of the phone.
// A single channel per cluster is more forgiving than one hole per button.
ACTION_Y   = 36.0; ACTION_L  = 10.0;   // MEASURE: Action button, left side
VOL_Y      = 54.0; VOL_L     = 44.0;   // MEASURE: volume up+down as one channel
POWER_Y    = 56.0; POWER_L   = 26.0;   // MEASURE: side button, right side
CAMCTRL_Y  = 96.0; CAMCTRL_L = 14.0;   // MEASURE: Camera Control, right side (new on 16)
BTN_DEPTH  = 6.0;                      // how tall the channel is, centred on the phone's thickness

// Bottom: USB-C and the speaker grilles, as one opening. MEASURE both.
BOT_W = 46.0;      // MEASURE: how wide the opening needs to be
BOT_D = 6.5;       // how tall

// ---- derived -----------------------------------------------------------------
CH   = PH_H + 2*FIT;              // cavity
CW   = PH_W + 2*FIT;
CD   = PH_D + FIT;
CR   = PH_R + FIT;
OH   = CH + 2*WALL;               // outer
OW   = CW + 2*WALL;
OD   = CD + BACK_T;
OR   = CR + WALL;

module case() {
  difference() {
    // outer shell
    cuboid([OW, OH, OD], rounding = OR, edges = "Z", anchor = BOTTOM);

    // the phone
    translate([0, 0, BACK_T])
      cuboid([CW, CH, CD + 1], rounding = CR, edges = "Z", anchor = BOTTOM);

    // front opening - the lip is what holds the phone in
    translate([0, 0, BACK_T + 1])
      cuboid([CW - 2*LIP, CH - 2*LIP, CD + 2], rounding = max(CR - LIP, 1),
             edges = "Z", anchor = BOTTOM);

    // camera island, measured from the top-left of the back
    translate([-OW/2 + WALL + FIT + CAM_X + CAM_W/2,
                OH/2 - WALL - FIT - CAM_Y - CAM_H/2,
               -1])
      cuboid([CAM_W + 2*CAM_PAD, CAM_H + 2*CAM_PAD, BACK_T + 2],
             rounding = CAM_R, edges = "Z", anchor = BOTTOM);

    // side buttons: [ side, y from top, length ]
    for (b = [[-1, ACTION_Y,  ACTION_L],
              [-1, VOL_Y,     VOL_L],
              [ 1, POWER_Y,   POWER_L],
              [ 1, CAMCTRL_Y, CAMCTRL_L]])
      translate([b[0] * OW/2, OH/2 - b[1] - b[2]/2, BACK_T + CD/2])
        cuboid([2*WALL + 2, b[2], BTN_DEPTH], rounding = 1, edges = "Y");

    // bottom: USB-C and the speakers
    translate([0, -OH/2, BACK_T + CD/2])
      cuboid([BOT_W, 2*WALL + 2, BOT_D], rounding = 1, edges = "X");
  }
}

case();

echo(str("phone   ", PH_H, " x ", PH_W, " x ", PH_D, "  (Apple tech specs)"));
echo(str("cavity  ", CH, " x ", CW, " x ", CD, "   slack ", FIT, " per side"));
echo(str("case    ", OH, " x ", OW, " x ", OD));
echo(str("lip     ", LIP, " over the glass; front opening ",
         CW - 2*LIP, " x ", CH - 2*LIP));
echo("PRINT IN TPU. Every number marked MEASURE is an estimate - check it first.");
