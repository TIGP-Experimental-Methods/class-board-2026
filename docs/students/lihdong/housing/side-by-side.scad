// Both boards in one view, laid out flat next to each other (not stacked).
// Front panel on the left, main board 20 mm to its right.
gap = 20;

import("../../../../hardware/release/front-panel.stl");

translate([180 + gap, 0, 0])
    import("../../../../hardware/release/class-board.stl");
