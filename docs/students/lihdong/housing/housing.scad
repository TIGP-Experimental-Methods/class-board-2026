// housing.scad - housing for the TIGP 2026 class board (Project 3, exercise E12). Law Lih Dong.
// OpenSCAD 2021.01, no libraries. Set `part` (Customizer or below), F5 to look, F6 + Export for files.
//
//   assembly  both boards in the housing (default)    base    printed base, as it goes on the bed
//   section   the assembly cut open at section_x       cover   printed cover, face up, as on the bed
//   plate     base and cover on one 256 mm P1S plate   labels  optional white inlay for the cover labels
//   lid       laser-cut bottom lid, 2D (Export DXF)    coupon  test print: holes 3.0-3.6, nut pocket, wall
//
// Frame: the front panel's own KiCad frame, panel face up. x 0..180 left to right, y -115 (front edge,
// the panel's screw terminals) to -15 (rear edge, the main board's connectors), z up. KiCad's y axis
// points down, so a KiCad position (x, y) is drawn at (x, -y); positions below are KiCad numbers.
// The panel mesh is used as exported; the main board is turned over onto it (link sockets up, dev
// board down), so main x -> 180 - x and z -> -z.
//
// Heights (z): main board -1.6..0 | panel 11..12.6 | cover 14.8..16.8 | OLED hood top 28.8 | lid -25.4..-22.4
//
// Assembly: (1) the board stack: four M3 x 11 stand-offs between the boards, M3 x 6 pan-head screws
// on both sides; (2) the stack drops into the base, the main-board screw heads sit in the column tops;
// (3) the cover: four M3 x 10 into nuts slid into the posts from outside; (4) the clear acrylic lid
// underneath: four M3 x 10 into the posts' lower nuts. The lid comes off to reach RESET and BOOT.

part      = "assembly";  // [assembly, section, plate, base, cover, labels, lid, coupon]
explode   = 0;           // mm: in the assembly, the cover moves up and the lid down by this much
ghost     = true;        // boards drawn transparent (%); false draws them solid (pictures)
section_x = 147.65;      // the section keeps x < section_x: SMA column AUX/RX and the OLED

/* [Boards] */
pcb      = 1.6;
stack    = 11;           // between the boards' facing surfaces: 8.5 mm socket + 2.5 mm header insulator
main_z0  = -pcb;         // main board's lower face: its components and the dev board point down
face     = stack + pcb;  // the panel's outer face, z = 12.6
holes    = [[4, -19], [176, -19], [4, -111], [176, -111]];   // M3 holes, the same on both boards
dev_drop = 17;           // the dev board hangs this far below the main board (housing brief)

/* [Print rules] */
wall    = 2;             // walls and plates
clr     = 0.3;           // every hole 0.3 mm larger than what goes through it
screw_d = 3 + clr;       // M3; the coupon checks it on the printer
nut_af  = 5.8;           // M3 nut, 5.5 across flats, plus clearance
nut_h   = 2.5;           // pocket height for a 2.4 mm nut
head_d  = 6 + clr;       // M3 pan or cheese head, 5.5-6.0 mm
head_h  = 2.4;

/* [Housing] */
gap       = 3;           // board edge to the inside of the wall
below     = 20.8;        // main board's lower face to the lid: the dev board's 17 mm + 3.8 mm for wires
cover_gap = 2.2;         // panel face to the cover's underside: the SMA hex bases are 2.0 mm tall
hood_gap  = 0.2;         // top of the OLED module to the hood
lid_t     = 3;           // laser-cut acrylic
post      = 10;          // corner posts, 10 x 10 mm, full height
post_out  = 6;           // how far a post stands out from the wall
nut_depth = 5;           // nut centre below the top of a post, and above its bottom
engrave   = 0.6;         // label depth
font      = "Liberation Sans:style=Bold";

$fn = 48;

// ---------------------------------------------------------------- derived numbers
floor_z  = main_z0 - below;     // -22.4: bottom of the base, inside face of the lid
cover_z0 = face + cover_gap;    //  14.8: top of the base, underside of the cover
cover_z1 = cover_z0 + wall;     //  16.8: the face of the instrument

ix0 = -gap;        ix1 = 180 + gap;   iy0 = -115 - gap;  iy1 = -15 + gap;   // inside of the wall
ox0 = ix0 - wall;  ox1 = ix1 + wall;  oy0 = iy0 - wall;  oy1 = iy1 + wall;  // outside of the wall
ex0 = ox0 - post_out;  ex1 = ox1 + post_out;    // outline over the posts: cover and lid
ey0 = oy0 - post_out;  ey1 = oy1 + post_out;

// post centres and which way each nut slot opens (-1 left, +1 right)
posts = [for (sx = [-1, 1], sy = [-1, 1])
    [sx < 0 ? ex0 + post/2 : ex1 - post/2, sy < 0 ? ey0 + post/2 : ey1 - post/2, sx]];

// ---------------------------------------------------------------- front panel parts (KiCad numbers)
sma_x = [75.65, 93.65, 111.65, 129.65, 147.65, 165.65];   // columns, 18 mm apart
sma_y = [25.67, 43.67, 61.67];                            // rows
sma = [["AI1", 0, 0], ["AI2", 1, 0], ["AI3", 2, 0], ["AI4", 3, 0], ["AUX", 4, 0], ["FAST1", 5, 0],
       ["AI5", 0, 1], ["AI6", 1, 1], ["AI7", 2, 1], ["AI8", 3, 1], ["RX",  4, 1], ["FAST2", 5, 1],
       ["AO1", 0, 2], ["AO2", 1, 2], ["TX",  2, 2], ["TRIG", 3, 2]];   // names from the panel silkscreen
sma_h      = 9.8;                     // jack height above the panel: hex base 0-2, then the thread
sma_thread = 6.35;                    // 1/4-36 thread
sma_d      = sma_thread + clr + 0.3;  // + 0.3 for where each jack ended up when it was soldered

oled   = [137.55, 164.55, 72.65, 101.65];   // OLED module J30 on its socket [x0, x1, y0, y1]
oled_h = 13.8;                              // its top above the panel face
hood_win = [76.65, 94.65];                  // window rows (y): the 4-pin header end is at y 72.65

opto   = [[76.61, 87.99, 86.00, 96.80],     // U401, U402 6N137: the only chips taller than the
          [49.14, 60.52, 85.92, 96.72]];    // cover gap
opto_h = 4.3;

// openings: [x0, x1, y0, y1], margin around it
windows = [[[118.64, 123.34,  74.10,  81.40], 1.5],   // J33 Qwiic: room for the plug and fingers
           [[114.21, 118.97,  85.66,  94.11], clr],   // D1-D3 LEDs, one slot
           [[ 21.80,  45.70, 102.37, 113.27], 0.5]];  // J40 module header, shrouded 2 x 6
// screw terminals on the front edge, wires from the side: open through the cover and the front wall
notches = [[130.79, 157.25, 107.75],    // J31 TTL OUT 1-8, GND, GND
           [105.30, 116.10, 103.90],    // J32 TX COIL
           [ 81.60,  92.81, 106.43],    // J411 ISO IN 1
           [ 54.13,  65.34, 106.36]];   // J412 ISO IN 2
notch_m = 1;

// ---------------------------------------------------------------- main board rear edge (housing x)
// main x -> 180 - x, z -> -z. USB-C J201 x 18.0, DC jack J202 x 32.55, terminals from their pads.
usb  = [180 - 18.0, -1.6, 14, 9];        // x, z centre, w, h: room for the plug's overmould
dc   = [180 - 32.55, -8.0, 12];          // x, z centre, d: the plug boot enters the wall
term = [[180 - 54.88, 180 - 44.28],      // J901 +VEXT 7-18 V (pads: + at 52.38, GND at 47.38)
        [180 - 69.28, 180 - 58.67],      // J903 H-bridge coil (OUT1 66.78, OUT2 61.78)
        [180 - 87.40, 180 - 72.00]];     // J905 +VCOIL 84.9, COIL 79.9, GND 74.9
term_z = [main_z0 - 8.5, main_z0];       // window from the board face to under the screw heads

// ================================================================ helpers
function kp(x, y) = [x, -y];             // KiCad point to drawing point

module kbox(r, m = 0) {                  // KiCad rectangle [x0, x1, y0, y1], grown by m
    translate([r[0] - m, -r[3] - m]) square([r[1] - r[0] + 2*m, r[3] - r[2] + 2*m]);
}

module outline_2d() {                    // cover and lid: the wall plus the posts, rounded corners
    translate([ex0, ey0]) offset(r = 3) offset(delta = -3) square([ex1 - ex0, ey1 - ey0]);
}

module label(t, size, ha = "center", va = "center") {
    text(t, size = size, font = font, halign = ha, valign = va);
}

module teardrop_2d(d) {                  // a round hole with a 45 deg roof: prints without support
    hull() { circle(d = d); translate([0, d/2 * sqrt(2)]) square(0.01, center = true); }
}

// ================================================================ base
module walls() {
    translate([0, 0, floor_z]) linear_extrude(cover_z0 - floor_z) difference() {
        translate([ox0, oy0]) square([ox1 - ox0, oy1 - oy0]);
        translate([ix0, iy0]) square([ix1 - ix0, iy1 - iy0]);
    }
}

module posts_solid() {
    for (p = posts) translate([p[0] - post/2, p[1] - post/2, floor_z]) cube([post, post, cover_z0 - floor_z]);
}

module post_cuts() {                     // a screw hole through each post, a nut pocket at each end
    for (p = posts) {
        translate([p[0], p[1], floor_z - 1]) cylinder(d = screw_d, h = cover_z0 - floor_z + 2);
        for (zc = [cover_z0 - nut_depth, floor_z + nut_depth])
            translate([p[0], p[1], zc - nut_h/2]) {
                rotate([0, 0, 30]) cylinder(d = nut_af / cos(30), h = nut_h, $fn = 6);
                translate([p[2] < 0 ? -post : 0, -nut_af/2, 0]) cube([post, nut_af, nut_h]);   // slot out
            }
    }
}

// columns under the main board's corners: the stack sits on them, its screw heads in the recesses
module column_2d(h) {
    cx = h[0] < 90 ? ix0 : ix1;
    cy = h[1] > -65 ? iy1 : iy0;
    hull() {
        translate(h) circle(r = 5);      // nothing on the main board within 6 mm of a hole
        translate([min(cx, h[0]), min(cy, h[1])]) square([abs(cx - h[0]), abs(cy - h[1])]);
    }
}

module columns() {
    for (h = holes) translate([0, 0, floor_z]) linear_extrude(main_z0 - floor_z) column_2d(h);
}

module column_cuts() {
    for (h = holes) translate([h[0], h[1], main_z0 - head_h - clr]) cylinder(d = head_d, h = head_h + clr + 1);
}

module rear_window(x, z, w, h, r) {      // rounded window through the rear wall
    translate([x, oy1 + 1, z]) rotate([90, 0, 0]) linear_extrude(wall + 2)
        offset(r = r) square([w - 2*r, h - 2*r], center = true);
}

module rear_cuts() {
    rear_window(usb[0], usb[1], usb[2], usb[3], 3);
    translate([dc[0], oy1 + 1, dc[1]]) rotate([90, 0, 0]) linear_extrude(wall + 2) teardrop_2d(dc[2]);
    for (t = term)
        rear_window((t[0] + t[1]) / 2, (term_z[0] + term_z[1]) / 2, t[1] - t[0] + 2, term_z[1] - term_z[0], 1);
}

module front_notches() {                 // wire entry for the panel's terminals, from the panel face up
    for (n = notches)
        translate([n[0] - notch_m, oy0 - 1, face]) cube([n[1] - n[0] + 2*notch_m, wall + 2, cover_z0 - face + 1]);
}

// engraved on the rear wall's outside, read from behind (so the text runs towards -x)
module rear_text(x, z, t, size = 2.4) {
    translate([x, oy1 - engrave, z]) rotate([90, 0, 180]) linear_extrude(engrave + 1) label(t, size);
}

module rear_labels() {
    names = [[usb[0], "USB-C", "5 V"], [dc[0], "DC IN", "5 V"],
             [(term[0][0] + term[0][1]) / 2, "EXT IN", "7-18 V"],
             [(term[1][0] + term[1][1]) / 2, "H-BRIDGE", "COIL"],
             [(term[2][0] + term[2][1]) / 2, "COIL", "SUPPLY"]];
    for (n = names) { rear_text(n[0], -16.6, n[1]); rear_text(n[0], -19.9, n[2]); }
    poles = [[180 - 52.38, "+"], [180 - 47.38, "-"],                      // J901
             [180 - 66.78, "1"], [180 - 61.78, "2"],                      // J903
             [180 - 84.90, "+"], [180 - 79.90, "C"], [180 - 74.90, "-"]]; // J905
    for (p = poles) rear_text(p[0], 1.2, p[1]);
}

module base() {
    difference() {
        union() { walls(); posts_solid(); columns(); }
        post_cuts();
        column_cuts();
        rear_cuts();
        front_notches();
        rear_labels();
    }
}

// ================================================================ cover
hood_in  = [oled[0] - clr, oled[1] + clr, oled[2] - clr, oled[3] + clr];
hood_z1  = face + oled_h + hood_gap;     // inside of the hood's top
hood_top = hood_z1 + wall;
opto_top = face + opto_h + clr;          // inside of the bumps over U401/U402

module cover_labels_2d() {
    for (s = sma) translate(kp(sma_x[s[1]], sma_y[s[2]] + 6.0)) label(s[0], 3.0);
    for (l = [["PWR", 86.95], ["WIFI", 89.90], ["ACT", 92.85]])
        translate(kp(113.2, l[1])) label(l[0], 2.2, "right");
    translate(kp(116.2, 77.75)) label("QWIIC", 2.6, "right");
    translate(kp(33.75, 99.6)) label("MODULE OUT", 2.6);
    translate(kp(59.74, 101.2)) label("ISO IN 2", 2.4);
    translate(kp(87.23, 101.2)) label("ISO IN 1", 2.4);
    translate(kp(110.70, 101.0)) label("TX COIL", 2.4);
    for (p = [[56.88, "+"], [61.88, "-"], [84.35, "+"], [89.35, "-"]]) translate(kp(p[0], 103.95)) label(p[1], 2.2);
    for (i = [0:9]) translate(kp(132.67 + 2.54*i, 105.35)) label(i < 8 ? str(i + 1) : "G", 2.2);
    translate(kp(129.5, 110.5)) label("TTL OUT", 2.1, "right");
    translate(kp(9, 41)) label("CLASS BOARD", 4.4, "left");
    translate(kp(9, 47.5)) label("INSTRUMENT", 4.4, "left");
    translate(kp(9, 55)) label("LAW LIH DONG  -  TIGP 2026", 2.8, "left");
    translate(kp(9, 60.5)) label("AI ±10 V   AO ±10 V   TRIG 5 V TTL", 2.5, "left");
}

module hood() {                          // over the OLED: walls, and a top of two bars bridging in x
    difference() {
        translate([hood_in[0] - wall, -hood_in[3] - wall, cover_z0])
            cube([hood_in[1] - hood_in[0] + 2*wall, hood_in[3] - hood_in[2] + 2*wall, hood_top - cover_z0]);
        translate([0, 0, cover_z0 - 1]) linear_extrude(hood_z1 - cover_z0 + 1) kbox(hood_in);
        translate([hood_in[0], -hood_win[1], hood_z1 - 1])        // window: the full inner width
            cube([hood_in[1] - hood_in[0], hood_win[1] - hood_win[0], wall + 2]);
    }
}

module bumps() {                         // raised blocks over the two optocouplers
    for (o = opto) translate([0, 0, cover_z0]) linear_extrude(opto_top + 1.2 - cover_z0) kbox(o, clr + wall);
}

module cover() {
    difference() {
        union() {
            translate([0, 0, cover_z0]) linear_extrude(wall) outline_2d();
            hood();
            bumps();
        }
        translate([0, 0, cover_z0 - 1]) linear_extrude(wall + 2) {
            for (s = sma) translate(kp(sma_x[s[1]], sma_y[s[2]])) circle(d = sma_d);
            for (w = windows) kbox(w[0], w[1]);
            kbox(hood_in);                                          // the OLED goes up into the hood
            for (p = posts) translate([p[0], p[1]]) circle(d = screw_d);
        }
        for (n = notches)                                           // terminals: open to the front edge
            translate([n[0] - notch_m, ey0 - 1, cover_z0 - 1])
                cube([n[1] - n[0] + 2*notch_m, -n[2] + notch_m - ey0 + 1, wall + 2]);
        for (o = opto) translate([0, 0, cover_z0 - 1]) linear_extrude(opto_top - cover_z0 + 1) kbox(o, clr);
        for (h = holes)                                             // the panel's screw heads
            translate([h[0], h[1], cover_z0 - 1]) cylinder(d = head_d, h = face + head_h + clr - cover_z0 + 1);
        translate([0, 0, cover_z1 - engrave]) linear_extrude(engrave + 1) cover_labels_2d();
    }
}

module labels() {                        // fills the engraving exactly: load with the cover, second colour
    translate([0, 0, cover_z1 - engrave]) linear_extrude(engrave) cover_labels_2d();
}

// ================================================================ lid, coupon
module lid_2d() {
    difference() {
        outline_2d();
        for (p = posts) translate([p[0], p[1]]) circle(d = screw_d);
    }
}

module coupon() {                        // print this first: which hole takes an M3, does the nut go in
    difference() {
        union() {
            cube([64, 24, wall]);
            translate([50, 12, 0]) cube([post, post, 12]);                       // a post with a nut pocket
            translate([4, 20, 0]) cube([40, wall, 12]);                          // a wall of this thickness
        }
        for (i = [0:6]) translate([6 + 6*i, 7, -1]) cylinder(d = 3.0 + 0.1*i, h = wall + 2);   // 3.0 ... 3.6
        translate([55, 6, -1]) cylinder(d = sma_d, h = wall + 2);               // an SMA jack's thread
        translate([55, 17, -1]) cylinder(d = screw_d, h = 14);
        translate([55, 17, 12 - nut_depth - nut_h/2]) {                     // as in the base's posts
            rotate([0, 0, 30]) cylinder(d = nut_af / cos(30), h = nut_h, $fn = 6);
            translate([0, -nut_af/2, 0]) cube([post, nut_af, nut_h]);
        }
        translate([0, 0, wall - engrave]) linear_extrude(1) {
            translate([6, 13]) label("3.0", 3);
            translate([42, 13]) label("3.6", 3);
        }
    }
}

// ================================================================ boards
module boards_mesh() {
    color("steelblue") translate([0, 0, stack]) import("../../../../hardware/release/front-panel.stl");
    color("seagreen") translate([180, 0, 0]) rotate([0, 180, 0]) import("../../../../hardware/release/class-board.stl");
    // the dev board's space: 17 mm below the main board, around its two socket rows (main x 53.5-106.9)
    color("dimgray", 0.5) translate([180 - 115, -82.8, main_z0 - dev_drop]) cube([70, 28, dev_drop]);
}

module boards() { if (ghost) %boards_mesh(); else boards_mesh(); }

// ================================================================ scenes
// render(): with the board meshes loaded, the plain preview draws cut-outs as missing walls
module scene() {
    boards();
    color("#F2C14E") render() base();
    color("#30363D") translate([0, 0, explode]) render() cover();
    color("white") translate([0, 0, explode]) render() labels();
    color("white", 0.45) translate([0, 0, floor_z - lid_t - explode]) linear_extrude(lid_t) lid_2d();
}

module plate() {                         // the Bambu Lab P1S plate, 256 x 256: base and cover together
    color("#DDDDDD") translate([0, 0, -0.6]) cube([256, 256, 0.6]);
    color("#F2C14E") translate([27 - ex0, 4 - ey0, -floor_z]) render() base();
    color("#30363D") translate([27 - ex0, 130 - ey0, -cover_z0]) render() cover();
}

// ---------------------------------------------------------------- numbers to check (console)
echo(str("outer size with the posts: ", ex1 - ex0, " x ", ey1 - ey0, " mm; walls ", ox1 - ox0, " x ", oy1 - oy0));
echo(str("height: base ", cover_z0 - floor_z, ", lid to cover face ", cover_z1 - floor_z + lid_t,
         ", lid to hood top ", hood_top - floor_z + lid_t, " mm"));
echo(str("SMA thread standing clear of the cover: ", sma_h - cover_gap - wall, " mm; hole ", sma_d, " mm"));
echo(str("cover over the panel ", cover_gap, " mm (SMA base 2.0, pin tails 1.3); bumps over U401/U402 to ",
         opto_top - face, " mm (chip ", opto_h, ")"));
echo(str("OLED: hood ", hood_z1 - face, " mm above the panel (module ", oled_h, "); window y ", hood_win[0], "..", hood_win[1]));
echo(str("dev board to the lid: ", below - dev_drop, " mm; board to wall: ", gap, " mm"));
echo(str("cover screws M3 x 10: tip ", 10 - wall, " mm into the post, nut centre at ", nut_depth, " mm"));
echo(str("lid screws M3 x 10: tip ", 10 - lid_t, " mm into the post, nut centre at ", nut_depth, " mm"));

// ---------------------------------------------------------------- what is drawn
if      (part == "base")    translate([0, 0, -floor_z]) base();
else if (part == "cover")   translate([0, 0, -cover_z0]) cover();
else if (part == "labels")  translate([0, 0, -cover_z0]) labels();
else if (part == "lid")     lid_2d();
else if (part == "coupon")  coupon();
else if (part == "plate")   plate();
else if (part == "section") intersection() {
    union() { boards_mesh(); color("#F2C14E") base(); color("#30363D") cover(); color("white") labels();
              color("white", 0.45) translate([0, 0, floor_z - lid_t]) linear_extrude(lid_t) lid_2d(); }
    translate([-50, -200, -100]) cube([section_x + 50, 400, 300]);
}
else scene();
