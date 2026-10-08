// Closed housing for the stacked boards: a printed top covers the front panel with every part
// below it (nothing sticks out; the SMAs, OLED, LEDs, Qwiic, module header and screw terminals
// are reached through openings in the top), the main board hangs under the panel on the three
// 2x20 links, and a laser-cut lid closes the bottom.
// (The earlier open-top version, with the panel itself as the top face, is stacked-open-top.scad.)
//
// Both STLs are in KiCad's frame (x 0..180, y -115..-15, board bottom z = 0, top z = 1.6).
// The panel is drawn from its outer face, mirrored in x (panel x = 180 - main x), so it is
// flipped about the y axis, and x = 90 is the fold line.
// Main socket = 8.5 mm tall, panel header body = 2.5 mm: so the panel's inner face sits
// 11 mm below the main board's bottom face.
// All geometry below is built in that frame (top at -z, lid at +z); `upright` only turns
// the finished model over for viewing, lid down and top up.
//
// Assembly: the two boards go together first as one stack (2x20 links plus four printed
// 11 mm spacers, part = "spacer"), then slide into the housing from the open bottom until the
// panel rests on the four bosses under the top.  One M3 x 35 countersunk screw per corner:
// head flush in the top, through boss, panel, spacer and main board, nut on the main board's
// component side.  Then the lid goes on with four M3 x 10.

upright  = true;  // true: show as a box (lid down, top up)
see_through = false;     // true: housing and lid drawn transparent, to see the boards inside
part     = "assembly";   // "assembly" | "housing" (print, top on the bed) | "spacer" (print 4)
                         // | "lid" (2D, F6 then Export as DXF)

socket_h = 8.5;   // main-board 2x20 female socket body
header_h = 2.5;   // panel 2x20 male header plastic body
stack    = socket_h + header_h;   // main bottom face to panel inner face = 11 mm

main_z0  = 0;            main_z1  = 1.6;            // main board slab
panel_z1 = -stack;       panel_z0 = -stack - 1.6;   // panel board slab (-11 .. -12.6)

// ---- outline, wall, top and lid ----
board_x0 = 0;    board_x1 = 180;    // board outline (both boards, same footprint)
board_y0 = -115; board_y1 = -15;
gap      = 3;    // clearance between board edge and inside of wall
wall_t   = 2;    // wall thickness

// top: above the tallest part on the panel, J32 KF128-5.0 at 14.1 mm (OLED module 13.8, SMA 9.8)
top_clear = 15;    // panel outer face to the top's inner face
top_t     = 2.5;   // printed top thickness
top_z1    = panel_z0 - top_clear;   // inner face of the top (-27.6)
top_z0    = top_z1 - top_t;         // outer face of the top (-30.1)

main_parts_top = 12.4;  // tallest main-board component (DC jack)
floor_clear    = 10;    // room between those parts and the lid (cables, wires into terminals)
lid_t          = 3;     // laser-cut lid sheet (shown only; not part of the print)

wall_z0  = top_z0;                            // wall starts at the top's outer face
floor_z0 = main_parts_top + floor_clear;      // open bottom edge of the wall = inside face of the lid
wall_z1  = floor_z0 + lid_t;                  // outside face of the lid

ix0 = board_x0 - gap;  ix1 = board_x1 + gap;   // inside of the wall
iy0 = board_y0 - gap;  iy1 = board_y1 + gap;
ox0 = ix0 - wall_t;    ox1 = ix1 + wall_t;     // outside of the wall
oy0 = iy0 - wall_t;    oy1 = iy1 + wall_t;

module shell() {   // wall plus the top, one print
    translate([0, 0, wall_z0])
        linear_extrude(floor_z0 - wall_z0)
            difference() {
                translate([ox0, oy0]) square([ox1 - ox0, oy1 - oy0]);
                translate([ix0, iy0]) square([ix1 - ix0, iy1 - iy0]);
            }
    translate([ox0, oy0, top_z0]) cube([ox1 - ox0, oy1 - oy0, top_t]);
}

// ---- lid corner posts: the wall corners extended outward, M3 screw + side-loaded nut ----
lid_ext   = 6;     // how far each post sticks out past the outside of the wall
post_in   = 4;     // how far it reaches back in (through the wall)
post_h    = 12;    // post height, measured from the lid face up the wall
lid_nut_d = 5;     // nut centre, depth from the lid face (M3 x 10 through a 3 mm lid reaches 7)

nut_af = 5.8;      // M3 nut 5.5 across flats + clearance
nut_h  = 2.8;      // M3 nut 2.4 thick + clearance
nut_r  = nut_af / 2 / cos(30);   // across-corners radius for a 6-sided cylinder

// [x, y, outward x direction] of each lid screw: 5 mm in from the post's outer faces
lid_holes = [for (sx = [-1, 1], sy = [-1, 1])
    [sx < 0 ? ox0 - lid_ext + 5 : ox1 + lid_ext - 5,
     sy < 0 ? oy0 - lid_ext + 5 : oy1 + lid_ext - 5, sx]];

// each post tapers back into the wall at 45 deg underneath, so it prints top-down without support
module lid_posts() {
    for (sx = [-1, 1], sy = [-1, 1]) {
        x0 = sx < 0 ? ox0 - lid_ext : ox1 - post_in;
        y0 = sy < 0 ? oy0 - lid_ext : oy1 - post_in;
        wx = sx < 0 ? ox0 : ox1 - post_in;   // the part of the post inside the wall footprint
        wy = sy < 0 ? oy0 : oy1 - post_in;
        hull() {
            translate([x0, y0, floor_z0 - post_h])
                cube([lid_ext + post_in, lid_ext + post_in, post_h]);
            translate([wx, wy, floor_z0 - post_h - lid_ext])
                cube([post_in, post_in, lid_ext]);
        }
    }
}

module lid_post_cuts() {
    for (h = lid_holes) {
        translate([h[0], h[1], floor_z0 - post_h - 1])   // screw hole
            cylinder(d = screw_d, h = post_h + 2, $fn = 32);
        translate([h[0], h[1], floor_z0 - lid_nut_d - nut_h/2]) {
            rotate([0, 0, 30]) cylinder(r = nut_r, h = nut_h, $fn = 6);   // nut pocket
            translate([h[2] < 0 ? -10 : 0, -nut_af/2, 0])                // slot out the side
                cube([10, nut_af, nut_h]);
        }
    }
}

// laser-cut lid: outline over the posts, the four lid-screw holes
module lid_2d() {
    difference() {
        translate([ox0 - lid_ext, oy0 - lid_ext])
            offset(r = 2) offset(delta = -2)
                square([ox1 - ox0 + 2*lid_ext, oy1 - oy0 + 2*lid_ext]);
        for (h = lid_holes) translate([h[0], h[1]]) circle(d = screw_d, $fn = 32);
    }
}

// ---- M3 board screws: bosses under the top, loose spacers between the boards ----
// H1-H4 sit at the same (x, y) on both boards (symmetric pattern, so the flip keeps them aligned).
// Nothing is fixed to the wall below the panel, so the board stack slides in from the open bottom.
// M3 x 35 countersunk: head in the top at z -30.1, tip at 4.9; nut on the main board 1.6..4.0.
holes     = [[4, -19], [176, -19], [4, -111], [176, -111]];
pillar_r  = 5;     // boss radius around the hole (nothing on either board within 6 mm)
screw_d   = 3.4;   // M3 clearance hole
csk_d     = 6.6;   // countersink diameter at the top's outer face (M3 head 6.0)
spacer_d  = 7;     // printed spacer between the boards

// footprint of one boss: hole boss hulled into its wall corner
module pillar_2d(h) {
    cx = h[0] < 90 ? ix0 : ix1;    // inner face of the nearest side wall
    cy = h[1] > -65 ? iy1 : iy0;   // inner face of the nearest end wall
    hull() {
        translate(h) circle(r = pillar_r, $fn = 48);
        translate([min(cx, h[0]), min(cy, h[1])])
            square([abs(cx - h[0]), abs(cy - h[1])]);
    }
}

module bosses() {   // from the top's inner face down onto the panel's outer face
    for (h = holes)
        translate([0, 0, top_z1 - 0.01]) linear_extrude(panel_z0 - top_z1 + 0.01) pillar_2d(h);
}

module screw_holes() {
    for (h = holes) {
        translate([h[0], h[1], top_z0 - 1])
            cylinder(d = screw_d, h = panel_z0 - top_z0 + 2, $fn = 32);
        translate([h[0], h[1], top_z0 - 0.01])   // 90 deg countersink, flush head
            cylinder(d1 = csk_d, d2 = screw_d, h = (csk_d - screw_d) / 2, $fn = 32);
    }
}

module spacer() {
    difference() {
        cylinder(d = spacer_d, h = stack, $fn = 48);
        translate([0, 0, -1]) cylinder(d = screw_d, h = stack + 2, $fn = 32);
    }
}

// ---- openings in the top, for the parts on the panel's outer face ----
// Positions in the front panel's own KiCad coordinates (x right, y down, as in front-panel.kicad_pcb),
// courtyards from the PCB; pk() maps them into this frame.
function pk(x, y) = [180 - x, -y];

// SMA jacks J10-J25 (9.8 mm tall, so 7.7 mm below the top's outer face): holes big enough for
// the cable plug's 8 mm coupling nut to reach down onto the jack
sma_d   = 12;
sma_xs  = [75.65, 93.65, 111.65, 129.65, 147.65, 165.65];
sma_pos = concat([for (x = sma_xs) [x, 25.67]],
                 [for (x = sma_xs) [x, 43.67]],
                 [for (i = [0:3]) [sma_xs[i], 61.67]]);

// rectangular openings: [x0, x1, y0, y1] courtyard in panel coordinates, margin
windows = [[[137.55, 164.55,  72.65, 101.65], 0.75],   // J30 OLED module on its socket (13.8 mm tall)
           [[118.64, 123.34,  74.10,  81.40], 2.0 ],   // J33 Qwiic, room for the plug and cable
           [[114.21, 118.97,  85.66,  94.11], 0.5 ],   // D1-D3 green LEDs, one slot
           [[ 21.80,  45.70, 102.37, 113.27], 1.0 ]];  // J40 2x6 shrouded module header

// screw terminals along the panel's bottom edge (y 115): notched out through the wall as well,
// so the wires come in from the side and the screws are reached from above
notches = [[130.79, 157.25, 107.75],   // J31 KF128-2.54 10P
           [105.30, 116.10, 103.90],   // J32 KF128-5.0 2P
           [ 81.60,  92.81, 106.43],   // J411 KF301-5.0 2P
           [ 54.13,  65.34, 106.36]];  // J412 KF301-5.0 2P
notch_margin = 1;

module rect_k(x0, x1, y0, y1) {   // panel-coordinate rectangle, drawn in this frame
    a = pk(x1, y1);  b = pk(x0, y0);
    translate(a) square([b[0] - a[0], b[1] - a[1]]);
}

module top_cuts() {
    translate([0, 0, top_z0 - 1]) linear_extrude(top_t + 2) {
        for (p = sma_pos) translate(pk(p[0], p[1])) circle(d = sma_d, $fn = 64);
        for (w = windows) let (r = w[0], m = w[1])
            offset(r = min(m, 1)) offset(delta = m - min(m, 1))
                rect_k(r[0], r[1], r[2], r[3]);
    }
    for (n = notches)   // from the top's outer face down to the panel's outer face
        translate([0, 0, top_z0 - 1]) linear_extrude(panel_z0 - top_z0 + 1)
            rect_k(n[0] - notch_margin, n[1] + notch_margin, n[2] - notch_margin, -oy0 + 1);
}

// ---- connector cutouts in the rear wall (main board rear edge, y = -15) ----
// Positions measured from class-board.stl.  The STL shows J901/J903 (2P) 5.05 mm too low;
// all three KF301 terminals really sit on the board top (z 1.6) and are 10 mm tall.
rear_y0 = iy1 - 1;            // just inside the rear wall's inner face
rear_t  = wall_t + 2;         // cut through the full wall thickness

// USB-C J201: mouth x 13.5..22.5, centre z 1.6 (mid-mount); oversize for plug overmolds
usb_x = 18;      usb_z = 1.6;
usb_w = 14;      usb_h = 9;            // cable boots are bigger than the 9 x 3.2 receptacle

// DC jack J202 (DC005): barrel at x 32.55, z 8.0; front face is 4.1 mm back from the
// board edge, so the plug boot has to pass into the wall
dc_x = 32.55;    dc_z = 8.0;    dc_d = 12;

// screw terminals: [x0, x1] of each body; window from board top to under the screw heads
terminals = [[44.28, 54.88],   // J901 2P
             [58.67, 69.28],   // J903 2P
             [72.00, 87.40]];  // J905 3P
term_margin = 1;
term_z0 = main_z1;   term_z1 = main_z1 + 8.5;

module rear_cut(x, z, w, h, r) {   // rounded-rectangle window through the rear wall
    translate([x, rear_y0, z]) rotate([-90, 0, 0])
        linear_extrude(rear_t)
            offset(r = r) square([w - 2*r, h - 2*r], center = true);
}

module cutouts() {
    rear_cut(usb_x, usb_z, usb_w, usb_h, 3);
    translate([dc_x, rear_y0, dc_z]) rotate([-90, 0, 0])
        cylinder(d = dc_d, h = rear_t, $fn = 64);
    for (t = terminals)
        rear_cut((t[0] + t[1]) / 2, (term_z0 + term_z1) / 2,
                 t[1] - t[0] + 2*term_margin, term_z1 - term_z0, 1);
}

module housing() {
    difference() {
        union() { shell(); bosses(); lid_posts(); }
        screw_holes();
        lid_post_cuts();
        top_cuts();
        cutouts();
    }
}

// ---- scene ----
module scene() {
    color("seagreen")
        import("../../../../hardware/release/class-board.stl");
    color("steelblue")                       // front panel, flipped and mated
        translate([180, 0, -stack])
            rotate([0, 180, 0])
                import("../../../../hardware/release/front-panel.stl");
    color("silver")                          // spacers between the boards
        for (h = holes) translate([h[0], h[1], panel_z1]) spacer();
    // render(): F5 then shows the finished solid; with the two board STLs loaded the plain
    // preview runs out of elements and draws the cut-outs as missing walls
    color("gold", see_through ? 0.4 : 1) render() housing();
    color("white", see_through ? 0.4 : 1)    // laser-cut lid
        translate([0, 0, floor_z0]) linear_extrude(lid_t) lid_2d();
}

module oriented() {   // lid down, top up; rear wall ends up at +y
    if (upright) rotate([180, 0, 0]) children(); else children();
}

if (part == "lid")          lid_2d();
else if (part == "housing") housing();   // as built: top at the lowest z, i.e. on the bed
else if (part == "spacer")  spacer();
else                        oriented() scene();
