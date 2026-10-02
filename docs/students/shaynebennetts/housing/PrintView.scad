// PrintView.scad - shows only what gets printed, without the boards: the base, and beside it
// the top cover and the OLED housing turned face down, and the SMA plate flat, as they go on the plate.
// White = the label inlays (on the cover they are underneath, in the first two layers).
// It reads CompleteHousing.scad, so every change there appears here on the next reload.
include <CompleteHousing.scad>
part = "none";
base();
translate([0, -260, cover_top]) rotate([180, 0, 0]) { cover(); color("white") cover_labels(); }
translate([70, -260, oled_under + oled_top_t]) rotate([180, 0, 0]) oled_housing();
translate([0, -260, -sma_under]) { sma_plate(); color("white") sma_labels(); }
