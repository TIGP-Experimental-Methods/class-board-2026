// CompleteHousing.scad - Project 3 housing, shaynebennetts.
// Frame: KiCad's, as the meshes come. Front panel face up, underside at z = 11;
// main board turned over, underside up at z = 0, its connectors hanging below.

part  = "all";  // [all, base, cover, cover_labels, sma, sma_labels, oled, lid, lid2d, section]
wall  = 3;      // wall thickness
lid_boss  = 10.5; // lid-support block size from the inner wall faces (see the lid supports below)
gap_x = lid_boss + 1;   // board edge to the end walls: the lid supports fit beside the board, 1 mm clear
gap_y = 3;              // board edge to the front and rear walls; the rear connectors stay at the wall
t     = 1.6;    // PCB thickness
stack = 11;     // stand-off length between the facing board surfaces
below_dev = 5;  // wall extends this far past the dev board's components
nut_af = 5.5 + 2*0.3;   // M3 nut pockets: 5.5 across flats, with 0.3 mm all round
nut_h  = 2.4 + 0.8;     //                 2.4 thick, with 0.8 mm extra height (lid pockets)

// dev board: the header plastic rests on the socket tops (8.5 mm off the main board);
// its PCB and components hang below, lowest point 3.55 + 3.21 mm past the socket tops
socket_top = -(t + 8.5);                  // -10.1
dev_low    = socket_top - 3.55 - 3.21;    // -16.86

z_top = stack + t;            // top of the front panel PCB  = 12.6
wall_top = z_top + 5;         // the walls stand 5 mm over the panel (room for the chips); the cover is a plate on them
z_bot = dev_low - below_dev;  // -21.86

// ---- the boards, transparent -----------------------------------------------
module boards() {
  %translate([0, 0, stack])
    import("../../../../hardware/release/front-panel.stl");
  %translate([180, 0, 0]) rotate([0, 180, 0])
    import("../../../../hardware/release/class-board.stl");
  %devboard();
}

// ---- the ESP32-S3 dev board (Jinhua #40729 = VCC-GND YD-ESP32-S3), hanging from the sockets -----
// Model: models/YD-ESP32-S3.stl, from the STEP by David Scambell via github.com/shkuznetsov/YD-ESP32-S3 (MIT).
// Model frame: x along the board (USB-C at +x), y up through the board (header pins point to -y,
// header plastic bottom at y = -3.55), z across (pin rows at z = +-12.7, J1 at +12.7).
// Sockets J1/J3 on the main board's top side: centre KiCad (80.2, 68.8), top 8.5 mm above the board,
// so in the housing the socket tops are at z = -10.1 and the header plastic rests there.
dev_c      = [180 - 80.2, -68.8];     // socket centre in the housing frame
module devboard() {
  multmatrix([[-1, 0,  0, dev_c[0]],              // USB-C end toward J1 pin 22 (low housing x)
              [ 0, 0, -1, dev_c[1]],              // J1 row (model z +12.7) to KiCad y 81.3
              [ 0,-1,  0, socket_top - 3.55]])    // pins point up into the sockets
    import("models/YD-ESP32-S3.stl");
}

// ---- rectangular wall, open top and bottom ---------------------------------
module walls() {
  translate([-gap_x - wall, -115 - gap_y - wall, z_bot])
    difference() {
      cube([180 + 2*(gap_x + wall), 100 + 2*(gap_y + wall), wall_top - z_bot]);
      translate([wall, wall, -1]) cube([180 + 2*gap_x, 100 + 2*gap_y, wall_top - z_bot + 2]);
    }
}

// ---- corner bosses between the boards, one M3 clearance hole each ----------
holes     = [[4, -19], [176, -19], [4, -111], [176, -111]];   // both boards
boss_wall = 2.5;                      // plastic left around the hole
hole_d    = 3.2 + 0.3;                // M3 clearance plus printed-hole allowance
r_boss    = hole_d/2 + boss_wall;     // 4.25
boss      = [gap_x + 4 + r_boss, gap_y + 4 + r_boss];   // inner wall faces to the far side of the boss

module boss_shape() {   // local frame: wall faces on x = 0 and y = 0, interior toward +x +y
  hull() {
    translate([gap_x + 4, gap_y + 4, 0]) cylinder(r = r_boss, h = stack, $fn = 48);   // holes 4 mm in from the board edges
    cube([boss[0], 0.01, stack]);
    cube([0.01, boss[1], stack]);
  }
}

// One nut pocket per boss, opening at 45 degrees into the box, holding two nuts stacked: the lower
// one takes the main board's screw from below, the upper one the front panel's screw from above.
board_pocket_h = 2*2.4 + 0.8;                 // two M3 nuts plus 0.8 mm = 5.6
board_pocket_z = (stack - board_pocket_h)/2;  // centred: 2.7 mm of plastic at each board

module bosses() {
  for (h = holes) {
    sx = h[0] < 90  ? 1 : -1;
    sy = h[1] < -65 ? 1 : -1;
    wx = sx > 0 ? -gap_x       : 180 + gap_x;    // inner wall face in x
    wy = sy > 0 ? -115 - gap_y : -15 + gap_y;    // inner wall face in y
    difference() {
      translate([wx, wy, 0]) scale([sx, sy, 1]) boss_shape();
      translate([h[0], h[1], -1]) cylinder(d = hole_d, h = stack + 2, $fn = 32);
      translate([h[0], h[1], board_pocket_z]) scale([sx, sy, 1]) nut_pocket(r_boss + 4, board_pocket_h);
    }
  }
}

// ---- rear-wall openings -----------------------------------------------------
// Positions in the main board's own frame (before the flip), from the footprint pads in
// class-board.kicad_pcb; heights are above the board's top face.

// USB-C: a rounded slot 16 x 10 around the mid-mount receptacle, room for the plug boot
usb_x = [18.0 - 3, 18.0 + 3];   // end centres
usb_z = 1.1;                    // receptacle centre
usb_d = 10;

// DC jack: one round hole on the barrel axis of the 3D model (circle fit to its front face)
dc_axis = [32.55, 7.8];  // x, height above the board
dc_d    = 11;

// Terminal wire entries: one rounded slot per terminal block, through its outer poles.
// Entry centre 4.5 mm above the board, read from the J905 model.
terminals = [[47.38, 52.38], [61.78, 66.78], [74.9, 84.9]];   // J901, J903, J905: first and last pole
slot_d    = 6;      // slot height = end diameter
slot_z    = 4.5;    // wire-entry centre above the board

// a hole through the rear wall: round for one x, a rounded slot for two
module rear_slot(xs, z, d) {
  hull() for (x = xs)
    translate([180 - x, -15 + gap_y - 1, -z]) rotate([-90, 0, 0])   // the board's flip: x -> 180 - x, z -> -z
      cylinder(d = d, h = wall + 2, $fn = 64);
}

module terminal_notches() {   // the panel's screw-terminal wires leave through the front wall, above the panel
  for (c = terminal_cuts) translate([c[0], -115 - gap_y - wall - 1, z_top]) cube([c[1] - c[0], wall + 2, wall_top - z_top + 1]);
}

module rear_cutouts() {
  rear_slot(usb_x, usb_z, usb_d);
  rear_slot([dc_axis[0]], dc_axis[1], dc_d);
  for (tb = terminals) rear_slot(tb, slot_z, slot_d);
}

// ---- dev-board USB cable notches: arched, from the wall's bottom edge, in the end wall the ports face ----
// Port centres from the model: across z = -5.65 and +5.85, height y = 1.64 (model frame).
usb_dev_y = [-(-5.65) + dev_c[1], -(5.85) + dev_c[1]];   // housing y: -63.15, -74.65
usb_dev_z = -1.64 + socket_top - 3.55;                    // housing z: -15.29
notch_d   = 5;

module usb_notches() {
  for (y = usb_dev_y)
    hull() {
      translate([-gap_x - wall - 1, y, usb_dev_z]) rotate([0, 90, 0]) cylinder(d = notch_d, h = wall + 2, $fn = 48);
      translate([-gap_x - wall - 1, y - notch_d/2, z_bot - 1]) cube([wall + 2, notch_d, 0.01]);
    }
}

// ---- lid supports: four corner blocks inside, at the bottom edge, M3 up from the lid into a nut ----
// They sit in the end-wall gap beside the board, so the main board still passes them on its way in.
// The holes sit 8 mm in from the outer edges; each nut pocket opens at 45 degrees toward
// the inside of the box, so the nut slides in diagonally.
lid_boss_h = wall_top - z_bot; // column from the wall's bottom edge to the wall top: carries the board bosses and the cover screw
lid_hole_h = 12;     // screw hole depth from the bottom edge: an M3 x 10 through a 3 mm lid reaches 7 mm
lid_off    = 5;      // hole centre from each inner wall face (wall + 5 = 8 mm from the outer edge)
nut_z      = 2.5;    // plastic under the pocket

module lid_boss_shape() {   // local frame: wall faces on x = 0 and y = 0, interior toward +x +y
  hull() {
    translate([lid_off, lid_off, 0]) cylinder(r = lid_boss - lid_off, h = lid_boss_h, $fn = 48);
    cube([lid_boss, 0.01, lid_boss_h]);
    cube([0.01, lid_boss, lid_boss_h]);
  }
}

// an M3 nut pocket at the origin, open at 45 degrees toward +x +y (the inside of the box once mirrored
// into a corner), two flats parallel to the slide so the nut cannot turn
module nut_pocket(len, h = nut_h) {
  hull() for (d = [0, len])
    translate([d, d, 0] / sqrt(2)) rotate(45)
      cylinder(d = nut_af / cos(30), h = h, $fn = 6);
}

cover_nut_z = wall_top - z_bot - 2 - nut_h;   // cover-screw pocket: 2 mm of plastic under the cover

module lid_hole_shape() {   // same frame; cut from the block and the wall together
  translate([lid_off, lid_off, -1]) cylinder(d = hole_d, h = lid_hole_h + 1, $fn = 32);           // bottom lid screw
  translate([lid_off, lid_off, nut_z]) nut_pocket(lid_boss);
  translate([lid_off, lid_off, cover_nut_z - 2]) cylinder(d = hole_d, h = lid_boss_h, $fn = 32);  // cover screw: M3 x 8
  translate([lid_off, lid_off, cover_nut_z]) nut_pocket(lid_boss);
}

module lid_corners(z = z_bot) {   // children() placed in each inner corner at height z, mirrored
  for (sx = [1, -1], sy = [1, -1]) {
    wx = sx > 0 ? -gap_x       : 180 + gap_x;
    wy = sy > 0 ? -115 - gap_y : -15 + gap_y;
    translate([wx, wy, z]) scale([sx, sy, 1]) children();
  }
}

// ---- the bottom lid: one laser-cut plate, the outer size of the box ----------------------------
// Holes: the four lid screws, and a 5 mm screwdriver hole under every terminal screw of J901, J903, J905
// (the terminal screws face down in the housing). Screw axes from the J905 model: over each pole,
// 0.67 mm in from the pad row; the poles from the footprint pads.
lid_t        = 3;    // acrylic thickness
term_hole_d  = 5;
term_screws  = [[47.38, 20.52], [52.38, 20.52],                 // J901 (KiCad x, y)
                [61.78, 20.37], [66.78, 20.37],                 // J903
                [74.9, 20.32], [79.9, 20.32], [84.9, 20.32]];   // J905

module lid2d() {
  difference() {
    translate([-gap_x - wall, -115 - gap_y - wall])
      square([180 + 2*(gap_x + wall), 100 + 2*(gap_y + wall)]);
    for (sx = [1, -1], sy = [1, -1])
      translate([(sx > 0 ? -gap_x : 180 + gap_x) + sx*lid_off, (sy > 0 ? -115 - gap_y : -15 + gap_y) + sy*lid_off])
        circle(d = hole_d, $fn = 32);
    for (sc = term_screws)
      translate([180 - sc[0], -sc[1]]) circle(d = term_hole_d, $fn = 48);   // the board's flip: x -> 180 - x
  }
}

module lid() { translate([0, 0, z_bot - lid_t]) linear_extrude(lid_t) lid2d(); }

// ---- the top cover: printed, screwed into the corner columns through the same corner positions ----
// Heights above the panel face (z_top), from front-panel.stl: OLED 13.82, SMA 9.8 (square base 1.8),
// LEDs 1.0, Qwiic 4.32, module header 9.1, TTL strip 8.8, isolated inputs 9.95, TX terminal 14.1.
cover_under = wall_top;            // the cover lies on the walls, 5 mm over the panel
cover_top   = cover_under + 2;     // a 2 mm plate; the OLED gets its own housing (below)
low_under   = z_top + 2.5;         // LED area: 1.5 mm over the 1.0 mm LEDs
low_t       = 2;                   // plate thickness there
low_rim     = 2;                   // rim joining the LED plate to the cover
sma_under   = z_top + 1.8;         // SMA plate: rests on the jacks' 1.8 mm square bases
sma_t       = 2;                   // 6 mm of thread stands above it for the plug nuts
sma_lip     = 2.5;                 // the SMA plate reaches this far under the cover around its opening
sma_tol     = 0.5;                 // allowed error in where each SMA jack is soldered
sma_fit     = 0.3 + sma_tol;       // gap between the SMA plate and the cover opening
sma_d       = 6.35 + 2*(sma_tol + 0.15);   // 1/4-36 SMA thread, 0.5 mm placement error, 0.15 printed-hole allowance = 7.65
// The plate rests on the corners of the 6.5 mm square SMA bases (4.6 mm from the jack axis): with a hole
// radius of 3.83 and a jack 0.5 mm off, every corner still has at least 0.27 mm of plate over it.
led_d       = 3;

sma_xy  = concat([for (r = [-25.67, -43.67], n = [0:5]) [75.65 + 18*n, r]],
                 [for (n = [0:3]) [75.65 + 18*n, -61.67]]);
led_xy  = [[116.5, -86.96], [116.5, -89.90], [116.45, -92.85]];

module sma_zone() {   // 2D outline of the SMA field: rows 1-2 full, row 3 short; 9 mm round each jack
  offset(r = 3) offset(delta = -3) {
    translate([66.65, -52.67]) square([108, 36]);
    translate([66.65, -70.67]) square([72, 20]);
  }
}
module led_zone() { offset(r = 2) offset(delta = -2) translate([112.5, -96.5]) square([8, 13.2]); }

// windows straight through the cover: [x0, x1, y0, y1], from the mesh outlines plus clearance
windows = [
  [20.80, 46.70, -114.50, -102.40],   // module header J40, room for the plug
  [117.25, 124.85, -82.75, -72.75],   // Qwiic J33
];
// screw terminals: through the top for the screws, and out through the front wall for the wires
terminal_cuts = [
  [53.38, 67.13, -100.81],    // J412 isolated input: x0, x1, back edge y
  [80.85, 93.45, -105.83],    // J411 isolated input
  [104.55, 116.85, -103.05],  // J32 TX terminal
  [130.40, 157.80, -107.00],  // J31 TTL strip
];
// OLED J30: footprint origin (151.05, 74.92) in KiCad, so y is negated here. From the footprint:
// module 27 x 29 (x +-13.5, y -2.27..26.73 below the origin), glass 26.7 x 19.3 (y 3.23..22.53),
// four 2.4 mm holes for M2 at x +-12, y -0.77 and 25.23.
oled_o     = [151.05, -74.92];
oled       = [oled_o[0] - 14, oled_o[0] + 14, oled_o[1] - 27.23, oled_o[1] + 2.77];   // module outline + 0.5
oled_holes = [for (x = [-12, 12], y = [-0.77, 25.23]) [oled_o[0] + x, oled_o[1] - y]];
oled_win   = [oled_o[0], oled_o[1] - (3.23 + 22.53)/2, 24, 14];   // display window over the glass centre: x, y, w, h

module cover() {
  difference() {
    union() {
      translate([-gap_x - wall, -115 - gap_y - wall, cover_under])
        cube([180 + 2*(gap_x + wall), 100 + 2*(gap_y + wall), cover_top - cover_under]);   // the plate
      translate([0, 0, low_under]) linear_extrude(cover_under - low_under + 0.01)
        offset(r = low_rim) led_zone();                                                   // the LED plate and its rim
    }
    translate([0, 0, low_under + low_t]) linear_extrude(cover_top) led_zone();           // the LED well
    translate([0, 0, z_top - 1]) linear_extrude(low_under - z_top + 1) offset(r = low_rim) led_zone();
    translate([0, 0, z_top]) linear_extrude(cover_top) sma_zone();                        // opening for the SMA plate
    for (p = led_xy) translate([p[0], p[1], z_top]) cylinder(d = led_d, h = 30, $fn = 32);
    for (w = windows) translate([w[0], w[2], z_top - 1]) cube([w[1] - w[0], w[3] - w[2], 30]);
    for (c = terminal_cuts) translate([c[0], -125, z_top - 1]) cube([c[1] - c[0], c[2] + 125, 30]);
    translate([oled[0], oled[2], z_top - 1]) cube([oled[1] - oled[0], oled[3] - oled[2], 30]);   // under the OLED housing
    lid_corners(0) translate([lid_off, lid_off, z_top]) cylinder(d = hole_d, h = 30, $fn = 32);   // M3 x 8, button head
    cover_labels(inlay + 1);                 // pockets for the white inlay
  }
}

// ---- the SMA plate: a flat printed piece in the cover's SMA opening -------------------------------
// It rests on the jacks' square bases; a lip under the cover around the opening holds it down.
// Prints flat, plate down, lip up, no support.
module sma_plate() {
  difference() {
    union() {
      translate([0, 0, sma_under]) linear_extrude(sma_t) offset(r = sma_lip) sma_zone();                 // plate
      translate([0, 0, sma_under + sma_t - 0.01]) linear_extrude(cover_under - sma_under - sma_t + 0.01)
        difference() { offset(r = sma_lip) sma_zone(); offset(r = sma_fit) sma_zone(); }                 // lip up to the cover
    }
    for (p = sma_xy) translate([p[0], p[1], z_top]) cylinder(d = sma_d, h = 20, $fn = 48);
    sma_labels(inlay + 1);                   // pockets for the white inlay
  }
}

// ---- the OLED housing: four walls standing on the cover, a 2 mm top over the module ------------------
// Bolted down with M2 through the module's own four holes. Small bosses under the top press on the
// module's PCB corners, so the top clears the glass and never clamps it.
oled_wall   = 2;
oled_top_t  = 2;
oled_glass  = 1.5;                     // glass thickness on the module PCB (check on the module)
oled_under  = z_top + 13.82 + 0.2;     // the top's underside, 0.2 mm over the glass
m2_d        = 2.2 + 0.3;               // M2 clearance plus printed-hole allowance
oled_boss_d = 4.5;

module oled_housing() {
  difference() {
    union() {
      difference() {
        translate([oled[0] - oled_wall, oled[2] - oled_wall, cover_top])
          cube([oled[1] - oled[0] + 2*oled_wall, oled[3] - oled[2] + 2*oled_wall, oled_under + oled_top_t - cover_top]);
        translate([oled[0], oled[2], cover_top - 1]) cube([oled[1] - oled[0], oled[3] - oled[2], oled_under - cover_top + 1]);
      }
      for (p = oled_holes)   // bosses down to the module PCB
        translate([p[0], p[1], oled_under - oled_glass - 0.2]) cylinder(d = oled_boss_d, h = oled_glass + 0.21, $fn = 32);
    }
    for (p = oled_holes) translate([p[0], p[1], 0]) cylinder(d = m2_d, h = 50, $fn = 24);
    translate([oled_win[0] - oled_win[2]/2, oled_win[1] - oled_win[3]/2, oled_under - 1]) cube([oled_win[2], oled_win[3], 10]);
  }
}

// ---- labels ----------------------------------------------------------------------------------------
// Names from the boards' silkscreen and pad nets. Walls: engraved into the outer face. Cover and SMA plate:
// a white inlay, flush, two 0.2 mm layers deep, exported as its own STL (part cover_labels / sma_labels);
// in Bambu Studio load both STLs as one object with two parts and give the labels the white filament.
label_font = "Liberation Sans:style=Bold";
engrave    = 0.6;
inlay      = 0.4;
minus      = "−";
y_rear  = -15 + gap_y + wall;     // outer wall faces
y_front = -115 - gap_y - wall;
x_left  = -gap_x - wall;

module ltext(txt, size, ha = "center") text(txt, size = size, font = label_font, halign = ha, valign = "center");
module rear_text(x, z, txt, size)  translate([x, y_rear - engrave, z]) rotate([0, 0, 180]) rotate([90, 0, 0]) linear_extrude(engrave + 1) ltext(txt, size);
module front_text(x, z, txt, size) translate([x, y_front + engrave, z]) rotate([90, 0, 0]) linear_extrude(engrave + 1) ltext(txt, size);
module left_text(y, z, txt, size)  translate([x_left + engrave, y, z]) rotate([0, 0, -90]) rotate([90, 0, 0]) linear_extrude(engrave + 1) ltext(txt, size);

// rear wall, main board connectors (KiCad x -> 180 - x): names under the openings, poles over the terminals
rear_labels = [
  [180 - 18.0,  -17, "USB 5V", 3], [180 - 34.9, -17, "DC 5V", 3],
  [180 - 49.88, -17, "7-18V", 2.6], [180 - 64.28, -17, "HB OUT", 2.6], [180 - 79.9, -17, "COIL", 2.6],
  [180 - 47.38, 2.5, minus, 2.5], [180 - 52.38, 2.5, "+", 2.5],                            // J901 GND, VIN
  [180 - 61.78, 2.5, "2", 2.5],   [180 - 66.78, 2.5, "1", 2.5],                            // J903 OUT2, OUT1
  [180 - 74.9,  2.5, minus, 2.5], [180 - 79.9, 2.5, "C", 2.5], [180 - 84.9, 2.5, "+", 2.5], // J905 GND, COIL, +VCOIL
];
// front wall, panel terminals: names under the notches, poles under the names
front_labels = concat([
  [60.25, 9, "ISO IN 2", 2.8], [87.15, 9, "ISO IN 1", 2.8], [110.70, 9, "TX COIL", 2.8], [144.10, 9, "TTL OUT", 2.8],
  [56.88, 5, "+", 2.5], [61.88, 5, minus, 2.5], [84.35, 5, "+", 2.5], [89.35, 5, minus, 2.5],
  [108.35, 5, "TX", 2.5], [113.35, 5, "G", 2.5]],
  [for (i = [0:9]) [132.67 + 2.54*i, 5, i < 8 ? str(i + 1) : "G", 2.2]]);

module wall_labels() {
  for (l = rear_labels)  rear_text(l[0], l[1], l[2], l[3]);
  for (l = front_labels) front_text(l[0], l[1], l[2], l[3]);
  // dev board ports (user, on the board): COM on the buttons' side (model z -5.65), USB on the regulator's (z +5.85)
  left_text(usb_dev_y[0], usb_dev_z + 6, "COM", 3);
  left_text(usb_dev_y[1], usb_dev_z + 6, "USB", 3);
  left_text((usb_dev_y[0] + usb_dev_y[1])/2, usb_dev_z + 10.5, "ESP32", 3);
}

// cover, seen from above: [x, y, text, size, halign]
cover_label_list = concat([
  [33.75, -99.6, "MODULE OUT", 2.6, "center"],
  [116.0, -77.75, "QWIIC", 2.5, "right"],
  [111.5, -86.96, "PWR", 2.5, "right"], [111.5, -89.90, "WIFI", 2.5, "right"], [111.5, -92.85, "ACT", 2.5, "right"],
  [60.13, -96.3, "ISO IN 2", 2.5, "center"], [56.88, -99.3, "+", 2.5, "center"], [61.88, -99.3, minus, 2.5, "center"],
  [87.15, -101.3, "ISO IN 1", 2.5, "center"], [84.35, -104.3, "+", 2.5, "center"], [89.35, -104.3, minus, 2.5, "center"],
  [110.70, -98.6, "TX COIL", 2.5, "center"], [108.35, -101.5, "TX", 2.5, "center"], [113.35, -101.5, "G", 2.5, "center"],
  [123.5, -111, "TTL", 2.5, "center"]],
  [for (i = [0:9]) [132.67 + 2.54*i, -105.5, i < 8 ? str(i + 1) : "G", 2.2, "center"]]);
module cover_labels(h = inlay) {   // h > inlay cuts the pocket clean through the top face
  for (l = cover_label_list)
    translate([l[0], l[1], cover_top - inlay]) linear_extrude(h)
      text(l[2], size = l[3], font = label_font, halign = l[4], valign = "center");
}

// SMA plate: each jack's name 6.5 mm in front of it, in the same order as sma_xy
sma_names = ["AI1", "AI2", "AI3", "AI4", "AUX", "FAST1",
             "AI5", "AI6", "AI7", "AI8", "RX", "FAST2",
             "AO1", "AO2", "TX", "TRIG"];
module sma_labels(h = inlay) {
  for (i = [0 : len(sma_xy) - 1])
    translate([sma_xy[i][0], sma_xy[i][1] - 6.5, sma_under + sma_t - inlay]) linear_extrude(h) ltext(sma_names[i], 2.5);
}

// ---- the base: wall plus bosses, minus the openings --------------------------
module base() {
  difference() {
    union() { walls(); bosses(); lid_corners() lid_boss_shape(); }
    rear_cutouts();
    usb_notches();
    terminal_notches();
    lid_corners() lid_hole_shape();
    wall_labels();
  }
}

// ---- part switch ------------------------------------------------------------
if (part == "all")  { boards(); base(); %lid(); %cover(); %sma_plate(); %oled_housing();
                      color("white") { cover_labels(); sma_labels(); } }
if (part == "cover_labels") cover_labels();
if (part == "sma_labels")   sma_labels();
if (part == "sma")   sma_plate();
if (part == "cover") cover();
if (part == "oled")  oled_housing();
if (part == "base") base();
if (part == "lid")  lid();
if (part == "lid2d") lid2d();      // F6, then File -> Export -> Export as DXF
if (part == "section") {
  boards();
  difference() { base(); translate([-50, -200, -100]) cube([140, 400, 200]); }   // keeps x > 90
}

echo("outer x y h", 180 + 2*(gap_x + wall), 100 + 2*(gap_y + wall), wall_top - z_bot);
echo("boss", boss, "hole", hole_d, "wall around hole", boss_wall);
echo("lid", 180 + 2*(gap_x + wall), 100 + 2*(gap_y + wall), "x", lid_t, "screw holes in from each outer edge", wall + lid_off,
     "clearance block to board", gap_x - lid_boss);
