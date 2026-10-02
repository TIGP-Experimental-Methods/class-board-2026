// export.scad - every printed part in its printing orientation, and the bottom lid as a 2D drawing.
// Run by the command line: openscad -D 'which="cover"' -o cover.stl export.scad   (the lid: -D 'which="lid"' -o bottom_lid_3mm.dxf)
include <../CompleteHousing.scad>
part  = "none";
which = "base";
if (which == "base")         translate([0, 0, -z_bot]) base();                                       // bottom edge down
if (which == "cover")        translate([0, 0, cover_top]) rotate([180, 0, 0]) cover();               // face down
if (which == "cover_labels") translate([0, 0, cover_top]) rotate([180, 0, 0]) cover_labels();        // same transform
if (which == "sma")          translate([0, 0, -sma_under]) sma_plate();                              // plate down, lip up
if (which == "sma_labels")   translate([0, 0, -sma_under]) sma_labels();                             // same transform
if (which == "oled")         translate([0, 0, oled_under + oled_top_t]) rotate([180, 0, 0]) oled_housing();   // face down
if (which == "lid")          lid2d();                                                                // laser: DXF
