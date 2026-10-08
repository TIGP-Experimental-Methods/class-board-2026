// Housing tray for the stacked boards: the front panel is the lid (SMAs, OLED, LEDs face out),
// the main board hangs under it on the three 2x20 links, and a floor closes the bottom.
//
// Both STLs are in KiCad's frame (x 0..180, y -115..-15, board bottom z = 0, top z = 1.6).
// The panel is drawn from its outer face, mirrored in x (panel x = 180 - main x), so it is
// flipped about the y axis, and x = 90 is the fold line.
// Main socket = 8.5 mm tall, panel header body = 2.5 mm: so the panel's inner face sits
// 11 mm below the main board's bottom face.
// All geometry below is built in that frame (panel at -z, floor at +z); `upright` only turns
// the finished model over for viewing, floor down and panel on top.

upright  = true;  // true: show as a tray (lid down, front panel on top)
part     = "assembly";   // "assembly" | "housing" (print) | "lid" (2D, F6 then Export as DXF)

socket_h = 8.5;   // main-board 2x20 female socket body
header_h = 2.5;   // panel 2x20 male header plastic body
stack    = socket_h + header_h;   // main bottom face to panel inner face = 11 mm

main_z0  = 0;            main_z1  = 1.6;            // main board slab
panel_z1 = -stack;       panel_z0 = -stack - 1.6;   // panel board slab (-11 .. -12.6)

// ---- outline, wall and lid ----
board_x0 = 0;    board_x1 = 180;    // board outline (both boards, same footprint)
board_y0 = -115; board_y1 = -15;
gap      = 3;    // clearance between board edge and inside of wall
wall_t   = 2;    // wall thickness

main_parts_top = 12.4;  // tallest main-board component (DC jack)
floor_clear    = 10;    // room between those parts and the lid (cables, wires into terminals)
lid_t          = 3;     // laser-cut lid sheet (shown only; not part of the print)

wall_z0  = panel_z0;                          // wall ends flush with the panel's outer face
floor_z0 = main_parts_top + floor_clear;      // open bottom edge of the wall = inside face of the lid
wall_z1  = floor_z0 + lid_t;                  // outside face of the lid

ix0 = board_x0 - gap;  ix1 = board_x1 + gap;   // inside of the wall
iy0 = board_y0 - gap;  iy1 = board_y1 + gap;
ox0 = ix0 - wall_t;    ox1 = ix1 + wall_t;     // outside of the wall
oy0 = iy0 - wall_t;    oy1 = iy1 + wall_t;

module wall() {
    translate([0, 0, wall_z0])
        linear_extrude(floor_z0 - wall_z0)
            difference() {
                translate([ox0, oy0]) square([ox1 - ox0, oy1 - oy0]);
                translate([ix0, iy0]) square([ix1 - ix0, iy1 - iy0]);
            }
}

// ---- lid corner posts: the wall corners extended outward, M3 screw + side-loaded nut ----
lid_ext   = 6;     // how far each post sticks out past the outside of the wall
post_in   = 4;     // how far it reaches back in (through the wall into the board pillar)
post_h    = 12;    // post height, measured from the lid face up the wall
lid_nut_d = 5;     // nut centre, depth from the lid face (M3 x 10 through a 3 mm lid reaches 7)

nut_af = 5.8;      // M3 nut 5.5 across flats + clearance
nut_h  = 2.8;      // M3 nut 2.4 thick + clearance
nut_r  = nut_af / 2 / cos(30);   // across-corners radius for a 6-sided cylinder

// [x, y, outward x direction] of each lid screw: 5 mm in from the post's outer faces
lid_holes = [for (sx = [-1, 1], sy = [-1, 1])
    [sx < 0 ? ox0 - lid_ext + 5 : ox1 + lid_ext - 5,
     sy < 0 ? oy0 - lid_ext + 5 : oy1 + lid_ext - 5, sx]];

module lid_posts() {
    for (sx = [-1, 1], sy = [-1, 1]) {
        x0 = sx < 0 ? ox0 - lid_ext : ox1 - post_in;
        y0 = sy < 0 ? oy0 - lid_ext : oy1 - post_in;
        translate([x0, y0, floor_z0 - post_h])
            cube([lid_ext + post_in, lid_ext + post_in, post_h]);
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

// ---- M3 mounting pillars: wall corner -> board mounting holes ----
// H1-H4 sit at the same (x, y) on both boards (symmetric pattern, so the flip keeps them aligned).
// One screw per corner: head on the panel's outer face, through panel, spacer, main board
// and pillar into a nut in a hex pocket at the pillar's open end (under the lid), so the
// boards stay clamped with the lid off.  M3 x 30: tip at z 17.4, nut seat at 14.4..17.2.
holes     = [[4, -19], [176, -19], [4, -111], [176, -111]];
pillar_r  = 5;     // pillar radius around the hole (nothing on either board within 6 mm; leaves 1.6 mm round the nut pocket)
screw_d   = 3.4;   // M3 clearance hole through every pillar

// solid pillar segments in the spaces the boards leave free
segments = [[panel_z1, main_z0],   // between the boards, 11 mm spacer
            [main_z1, floor_z0]];  // main board up to the floor

// footprint of one pillar: hole boss hulled into its wall corner
module pillar_2d(h) {
    cx = h[0] < 90 ? ix0 : ix1;    // inner face of the nearest side wall
    cy = h[1] > -65 ? iy1 : iy0;   // inner face of the nearest end wall
    hull() {
        translate(h) circle(r = pillar_r, $fn = 48);
        translate([min(cx, h[0]), min(cy, h[1])])
            square([abs(cx - h[0]), abs(cy - h[1])]);
    }
}

module pillars() {
    for (h = holes, s = segments)
        translate([0, 0, s[0]]) linear_extrude(s[1] - s[0]) pillar_2d(h);
}

board_nut_depth = 8;   // hex pocket depth from the pillar's open end (nut sits at the top of it)

module screw_holes() {
    for (h = holes) {
        translate([h[0], h[1], wall_z0 - 1])
            cylinder(d = screw_d, h = floor_z0 - wall_z0 + 2, $fn = 32);
        translate([h[0], h[1], floor_z0 - board_nut_depth])
            rotate([0, 0, 30]) cylinder(r = nut_r, h = board_nut_depth + 1, $fn = 6);
    }
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
        union() { wall(); pillars(); lid_posts(); }
        screw_holes();
        lid_post_cuts();
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
    color("gold", 0.5) housing();
    color("white", 0.5)                      // laser-cut lid
        translate([0, 0, floor_z0]) linear_extrude(lid_t) lid_2d();
}

module oriented() {   // floor/lid down, panel up; rear wall ends up at +y
    if (upright) rotate([180, 0, 0]) children(); else children();
}

if (part == "lid")          lid_2d();
else if (part == "housing") oriented() housing();
else                        oriented() scene();
