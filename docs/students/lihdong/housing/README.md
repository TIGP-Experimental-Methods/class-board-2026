# Housing — Law Lih Dong (E12)

`housing.scad` (OpenSCAD 2021.01, no libraries) holds every part; `part` chooses what is drawn.
`./export.sh` regenerates all the files below from it.

| File | What | How it is made |
|---|---|---|
| `base.stl` | Base: four 2 mm walls, four corner posts with side-loaded M3 nut pockets, four columns the board stack sits on, rear openings with engraved names | 3D print, bottom down, no supports |
| `cover.stl` | Cover: 2.2 mm above the panel so 5.6 mm of SMA thread stands clear; hood over the OLED 14 mm above the panel; bumps over the two optocouplers; engraved labels | 3D print, face up, no supports |
| `cover_labels.stl` | Optional white inlay that fills the cover's engraved labels | load together with `cover.stl` as one object, second colour |
| `coupon.stl` | Test print: holes 3.0–3.6 mm, an SMA thread hole, a nut pocket, a 2 mm wall | 3D print first |
| `lid.dxf` | Bottom lid; comes off to reach the dev board's RESET and BOOT | laser cut, 3 mm clear acrylic |
| `housing.png` | Screenshot of the assembly | |

Outer size 202 × 122 mm (posts included); 42 mm from the bottom of the lid to the cover face, 54 mm to the top of the OLED hood.

**Hardware:** 4 × M3 × 11 stand-offs and 8 × M3 × 6 pan-head screws (the board stack); 8 × M3 × 10 screws and
8 × M3 nuts (cover and lid); 4 stick-on feet taller than the lid screw heads.

**Assembly:** build the board stack; drop it into the base (the main board's screw heads sit in the column
tops); slide four nuts into the upper pockets and screw the cover on; four nuts into the lower pockets and screw
the lid on.

**Checked:** every point of both board meshes against the parts — nothing above the 2.2 mm cover gap lies
outside an opening, the SMA threads clear their holes by 0.3 mm, nothing on the main board reaches a column,
the dev board's 17 mm space ends 3.8 mm above the lid. Earlier versions: `stacked-open-top.scad`, `stacked.scad`.
