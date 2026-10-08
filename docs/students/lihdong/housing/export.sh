#!/bin/sh
# Regenerate every production file from housing.scad (macOS; set OPENSCAD for another install).
O="${OPENSCAD:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"
cd "$(dirname "$0")"
"$O" -o base.stl          -D 'part="base"'   housing.scad &
"$O" -o cover.stl         -D 'part="cover"'  housing.scad &
"$O" -o cover_labels.stl  -D 'part="labels"' housing.scad &
"$O" -o coupon.stl        -D 'part="coupon"' housing.scad &
"$O" -o lid.dxf           -D 'part="lid"'    housing.scad &
"$O" -o housing.png --imgsize=1600,1000 --viewall --autocenter --camera=0,0,0,55,0,25,0 -D ghost=false housing.scad &
wait
