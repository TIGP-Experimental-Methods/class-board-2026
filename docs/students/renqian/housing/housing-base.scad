// Housing - the base tray.
// Ren Qian (Section A), 2026-10-02.
//
// Wall and floor, four M3 bosses with nut pockets, the five rear connector
// openings and the ventilation slots. Defines module base() only; render it
// through housing.scad with PART = "base".

include <BOSL2/std.scad>
include <housing-params.scad>
include <housing-shapes.scad>

module base() {
  difference() {
    union() {
      // wall
      translate([CTRB.x, CTRB.y, FLOOR_BOT])
        rect_tube(h = WALL_H, isize = ISIZE, wall = WALL, anchor = BOTTOM);
      // floor
      translate([CTRB.x, CTRB.y, FLOOR_BOT])
        cuboid([ISIZE.x, ISIZE.y, WALL], anchor = BOTTOM);
      // a boss at each mounting hole, 14 mm square so that, centred on its hole,
      // it reaches exactly to both inner wall faces; then grown by WALL towards
      // those walls so it merges into them as one solid rather than touching
      // face to face. It stops at the main board's underside, so the board
      // sits on it.
      for (h = HOLES) {
        s = wdir(h);
        translate([h.x + s.x*WALL/2, h.y + s.y*WALL/2, FLOOR_TOP])
          cuboid([BOSS+WALL, BOSS+WALL, BOSS_H], anchor = BOTTOM);
      }
    }

    // the screw runs the full height of each boss and through the floor
    for (h = HOLES)
      translate([h.x, h.y, FLOOR_BOT-1]) cylinder(d = M3_CLEAR, h = BOSS_H+WALL+2);

    // nut pocket at the bottom of each boss, open sideways so the nut slides in
    for (h = HOLES) {
      s = wdir(h);
      translate([h.x, h.y, FLOOR_TOP]) {
        cylinder(h = NUT_DEEP, d = NUT_AF/cos(30), $fn = 6);
        rotate([0,0,atan2(-s.y,-s.x)])
          translate([0,-NUT_AF/2,0]) cube([BOSS,NUT_AF,NUT_DEEP]);
      }
    }

    // the five rear connectors, clamped so they never cut the floor
    for (c = REAR) {
      p = c[5]; dz = c[6];
      x0 = c[1]-p; x1 = c[2]+p;
      z0 = max(c[3]+dz-p, FLOOR_TOP); z1 = c[4]+dz+p;
      wire_slot((x0+x1)/2, x1-x0, z0, z1, COVER_SIT - WALL,
                REAR_Y + WALL/2, 4*WALL + 20);
    }

    vents();
  }
}
