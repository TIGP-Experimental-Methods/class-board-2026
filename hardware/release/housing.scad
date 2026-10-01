// housing.scad — a printed housing for the TIGP class board (main board + front panel)
// Reference version, Workshop 3 (Lecture 3: CAD for AI experimentalists). OpenSCAD 2021.01, plain language, no library.
//
// How to read this file (top to bottom):
//   1. Variables: every dimension has a name; the comments after them make Customizer sliders / drop-downs.
//   2. The two boards, imported as meshes and shown transparent (%) so the housing is designed around them.
//   3. Modules: base(), cover(), coupon() — each a named part made of shapes, moves and combinations.
//   4. The part switch at the bottom chooses what is shown / exported.
//   5. echo() lines print the numbers you would otherwise have to measure.
//
// Frame: the KiCad board frame, millimetres. The boards span x 0..180, y 15..115.
// The instrument lies flat: the FRONT PANEL FACES UP (+z), the main board is under it, the dev board hangs below.

/* [Which part] */
part = "all";          // [all, base, cover, coupon, section]

/* [Walls and clearances] */
wall      = 2;         // [1.6:0.2:3]   wall and floor thickness
clear_xy  = 6;         // [3:1:10]      gap between board edge and inner wall (room for the corner blocks)
clear_z   = 3;         // [1:0.5:6]     gap under the lowest part of the dev board
fit       = 0.3;       // [0.1:0.05:0.5] printed holes come out small: added to every hole diameter
chamfer   = 0.5;       // [0:0.1:1]     chamfer at the bed against the elephant's foot

/* [What the boards are] */
board_x   = 180;       // board outline, both boards
board_y   = 100;
board_t   = 1.6;
stack     = 11;        // header stack: gap between the facing surfaces of the two boards (M3 x 11 stand-offs)
devboard_h = 17;       // how far the dev board hangs below the main board (socket 8.5 + header 2.5 + PCB 1.6 + parts 4)
hole_inset = 4;        // the four M3 mounting holes sit 4 mm from the board edges
standoff_d = 5.5;      // across-flats of the M3 stand-offs / nuts

/* [Front cover] */
cover_t   = 2;         // cover plate thickness
oled_top  = 13.8;      // top of the OLED module above the panel face (vendor model) - the cover presses on it
sma_hole  = 10;        // hole for an SMA plug to reach the connector below the plate
led_hole  = 2.5;
nut_af    = 5.5;       // M3 nut across flats
nut_t     = 2.5;       // M3 nut thickness
screw_d   = 3.4;       // M3 clearance hole

/* [Look] */
text_label = "TIGP";   // embossed on the +y wall
$fn = 48;

// ---------- derived numbers (do not edit) ----------
y0 = 15;                                   // board y origin in the KiCad frame
inner_x = board_x + 2*clear_xy;            // inside the walls
inner_y = board_y + 2*clear_xy;
outer_x = inner_x + 2*wall;
outer_y = inner_y + 2*wall;
// z levels, in the instrument frame (panel face up).  z = 0 is the panel's outer face.
z_panel_bot  = -board_t;                   // panel underside
z_main_top   = z_panel_bot - stack;        // main board's component side (faces the panel)
z_main_bot   = z_main_top - board_t;       // main board's other side: the dev board sockets are here
z_floor      = z_main_bot - devboard_h - clear_z;   // inside of the floor
z_base_bot   = z_floor - wall;             // underside of the base
z_cover_bot  = oled_top + 0.2;             // the cover's underside, resting on the OLED module
z_cover_top  = z_cover_bot + cover_t;
base_h       = z_cover_bot - z_base_bot;   // the base walls reach up to the cover
x0 = -clear_xy - wall;                     // outer corner of the housing
yy0 = y0 - clear_xy - wall;

// mounting holes (both boards; the panel is mirrored in x, which leaves these four unchanged)
holes = [[hole_inset, y0 + hole_inset], [board_x - hole_inset, y0 + hole_inset],
         [hole_inset, y0 + board_y - hole_inset], [board_x - hole_inset, y0 + board_y - hole_inset]];
// corner blocks for the cover screws (nut pocket in each)
corner_block = 8;
corners = [[x0 + wall, yy0 + wall], [x0 + outer_x - wall - corner_block, yy0 + wall],
           [x0 + wall, yy0 + outer_y - wall - corner_block], [x0 + outer_x - wall - corner_block, yy0 + outer_y - wall - corner_block]];

// ---------- the boards, from KiCad (kicad-cli pcb export stl, connectors only) ----------
// KiCad's y axis points down, so the exported mesh has y in -115..-15; mirror([0,1,0]) puts it at +15..+115.
module main_board() {        // component side faces +z in the export; here it must face the panel (+z): keep as is
  translate([0, 0, z_main_top - board_t]) mirror([0, 1, 0]) import("class-board.stl");
}
module front_panel() {       // outer face (F.Cu) is +z in the export: faces up, as wanted; mirror in x = the link mating
  translate([board_x, 0, z_panel_bot]) mirror([1, 0, 0]) mirror([0, 1, 0]) import("front-panel.stl");
}
module boards() { %color("green") main_board(); %color("royalblue") front_panel(); }

// ---------- helpers ----------
module rounded_rect(x, y, r) { offset(r = r) offset(delta = -r) square([x, y]); }
module nut_pocket(h = nut_t) { cylinder(d = (nut_af + fit) / cos(30), h = h, $fn = 6); }   // $fn=6 is inscribed: scale to across-flats
module m3_hole(h) { cylinder(d = screw_d + fit, h = h); }

// ---------- the base: a tray with corner blocks and bosses for the stand-off screws ----------
module base() {
  difference() {
    union() {
      difference() {
        // the block, rounded corners, a chamfer at the bed
        translate([x0, yy0, z_base_bot]) hull() {
          translate([chamfer, chamfer, 0]) linear_extrude(0.01) rounded_rect(outer_x - 2*chamfer, outer_y - 2*chamfer, 3);
          translate([0, 0, chamfer]) linear_extrude(base_h - chamfer) rounded_rect(outer_x, outer_y, 3);
        }
        // the pocket: the mill removes material, so does difference()
        translate([x0 + wall, yy0 + wall, z_floor]) linear_extrude(base_h) rounded_rect(inner_x, inner_y, 1);
      }
      // corner blocks (nut pockets for the cover screws)
      for (c = corners) translate([c[0], c[1], z_floor]) cube([corner_block, corner_block, base_h - wall]);
      // bosses under the main board's four mounting holes
      for (h = holes) translate([h[0], h[1], z_floor]) cylinder(d = 8, h = z_main_bot - z_floor);
    }
    // cover screws: hole through each corner block, nut pocket open to the inside face near the top
    for (c = corners) translate([c[0] + corner_block/2, c[1] + corner_block/2, z_floor]) {
      m3_hole(base_h);
      translate([0, 0, base_h - wall - 6]) hull() { nut_pocket(); translate([c[0] < 90 ? 10 : -10, 0, 0]) nut_pocket(); }
    }
    // stand-off screws: from under the floor, through the boss, through the board, into the stand-off
    for (h = holes) translate([h[0], h[1], z_base_bot - 1]) { m3_hole(50); cylinder(d = 6.5, h = 1 + wall + 2); }  // counterbore for the head
    // rear-edge openings (main board, y = 15 edge): USB-C J201, DC jack J202, terminals J901/J903/J905
    rear_opening(18.0, 10, 4.5, z_main_top);              // USB-C: 10 x 4.5, flush with the board surface
    rear_opening(32.5, 10, 12, z_main_top);               // DC jack body 9 x 11
    rear_opening(49.9, 12, 12, z_main_top);               // KF301 2P: wire entry
    rear_opening(64.3, 12, 12, z_main_top);
    rear_opening(79.9, 17, 12, z_main_top);               // KF301 3P
    // panel-edge wire slot (y = 115 edge): the panel's screw terminals take wires from the side
    translate([55, y0 + board_y + clear_xy - 1, 0]) cube([100, wall + 2, z_cover_bot + 1]);
    // embossed label is added, not cut: see below
  }
  // embossed text on the +y wall, 0.6 mm proud
  translate([x0 + outer_x/2, yy0 + outer_y, z_floor + 6]) rotate([90, 0, 0]) mirror([0,0,1])
    linear_extrude(0.6) text(text_label, size = 8, halign = "center", font = "Liberation Sans:style=Bold");
}
// an opening in the -y (rear) wall centred at x, width w, height h, from the given board surface upwards
module rear_opening(x, w, h, z_from) {
  translate([x - w/2, yy0 - 1, z_from]) cube([w, wall + 2, h]);
}

// ---------- the front cover: a plate over the panel ----------
module cover() {
  difference() {
    translate([x0, yy0, z_cover_bot]) linear_extrude(cover_t) rounded_rect(outer_x, outer_y, 3);
    // SMA plugs: the 16 connectors on a 18 mm grid (panel x = 180 - main x: the mesh is mirrored, these are panel coordinates)
    for (p = sma) translate([board_x - p[0], y0 + p[1] - y0, z_cover_bot - 1]) cylinder(d = sma_hole, h = cover_t + 2);
    // OLED window (the module's glass is 27 x 19 at the module centre; the cover presses on the module's frame)
    translate([board_x - 151.05 - 27.0/2, 74.92 - 29.0/2 + 4, z_cover_bot - 1]) cube([27.0, 22, cover_t + 2]);
    // LEDs
    for (y = [86.95, 89.90, 92.85]) translate([board_x - 116.5, y, z_cover_bot - 1]) cylinder(d = led_hole + fit, h = cover_t + 2);
    // Qwiic socket (cable from above)
    translate([board_x - 121.05 - 4, 77.75 - 6, z_cover_bot - 1]) cube([8, 12, cover_t + 2]);
    // module header J40 (shrouded 2x6, IDC plug 22 x 9)
    translate([board_x - 40.1 - 11.5, 107.05 - 5.5, z_cover_bot - 1]) cube([23, 11, cover_t + 2]);
    // screw terminals on the panel's +y edge: TTL strip J31, TX J32, isolated inputs J411, J412 (bodies pass through)
    translate([board_x - 144.1 - 13.5, 111.0 - 4, z_cover_bot - 1]) cube([27, 10, cover_t + 2]);
    translate([board_x - 110.85 - 6, 109.35 - 6, z_cover_bot - 1]) cube([12, 12, cover_t + 2]);
    translate([board_x - 86.85 - 6, 110.68 - 6, z_cover_bot - 1]) cube([12, 12, cover_t + 2]);
    translate([board_x - 59.38 - 6, 110.61 - 6, z_cover_bot - 1]) cube([12, 12, cover_t + 2]);
    // the four stand-off screws (through the cover and the panel into the stand-offs)
    for (h = holes) translate([h[0], h[1], z_cover_bot - 1]) m3_hole(cover_t + 2);
    // the cover screws into the corner blocks
    for (c = corners) translate([c[0] + corner_block/2, c[1] + corner_block/2, z_cover_bot - 1]) m3_hole(cover_t + 2);
  }
}
// SMA positions in PANEL coordinates (x, y) from the KiCad file: columns 75.65 .. 165.65 (18 mm), rows 25.67 / 43.67 / 61.67
sma = [[75.65,25.67],[93.65,25.67],[111.65,25.67],[129.65,25.67],[147.65,25.67],[165.65,25.67],
       [75.65,43.67],[93.65,43.67],[111.65,43.67],[129.65,43.67],[147.65,43.67],[165.65,43.67],
       [75.65,61.67],[93.65,61.67],[111.65,61.67],[129.65,61.67]];

// ---------- a test coupon: print this first ----------
module coupon() {
  difference() {
    translate([0, 0, 0]) cube([60, 20, 4]);
    for (i = [0:3]) translate([8 + i*12, 7, -1]) cylinder(d = 3.0 + i*0.2, h = 6);   // 3.0, 3.2, 3.4, 3.6
    translate([52, 10, -1]) m3_hole(6);
    translate([52, 10, 1.5]) nut_pocket(3);                                           // an M3 nut pocket
  }
  translate([0, 20, 0]) cube([60, wall, 4]);                                          // a wall at the chosen thickness
}

// ---------- the part switch ----------
if (part == "all")     { boards(); base(); color("sandybrown") cover(); }
if (part == "base")    { base(); }
if (part == "cover")   { cover(); }
if (part == "coupon")  { coupon(); }
if (part == "section") { boards(); difference() { union() { base(); color("sandybrown") cover(); } translate([90, -50, -100]) cube([200, 300, 200]); } }

// ---------- the numbers you would otherwise measure ----------
echo(str("outer size: ", outer_x, " x ", outer_y, " x ", z_cover_top - z_base_bot, " mm (P1S bed 256)"));
echo(str("inner clearance to the board edge: ", clear_xy, " mm; floor to dev board: ", clear_z, " mm"));
echo(str("cover underside at ", z_cover_bot, " mm above the panel face (OLED top ", oled_top, ")"));
echo(str("wall ", wall, " mm; holes +", fit, " mm; SMA hole ", sma_hole, " mm; M3 clearance ", screw_d + fit, " mm"));
echo(str("nut pocket across flats ", nut_af + fit, " mm, depth ", nut_t, " mm"));
