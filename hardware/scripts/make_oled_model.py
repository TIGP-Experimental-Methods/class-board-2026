"""Write lib/class_board.3dshapes/OLED-0.96in-4P-module.wrl - a box model of the 0.96 in I2C OLED module
as it sits on the panel's vertical 1x4 socket (PZ254-1-04-Z-8.5, 8.5 mm tall).

Footprint frame (class_board:OLED-0.96in-4P-module-socket): origin = centre of the 1x4 pad row,
x along the pins (pin 1 at x = -3.81), +y = towards the bottom of the module (KiCad y down).
The module's PCB (27.3 x 27.8 x 1.2 mm) hangs 11.0 mm above the panel: 8.5 mm socket + 2.5 mm
header body on the module's back.  The glass (26.7 x 19.3 x 1.6) sits on the module's front,
below the header.  Dimensions are the usual Chinese 4-pin module; MEASURE THE REAL MODULE
(Jinhua #32751) before the order - hole spacing 23.5 x 23.8 is the number to check.

VRML: 1 unit = 0.1 inch = 2.54 mm; x right, y = footprint -y, z up.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "lib", "class_board.3dshapes", "OLED-0.96in-4P-module.wrl")

# module geometry in footprint mm (x0, y0, x1, y1, z0, z1, colour)
Z_SOCKET = 8.5
Z_PCB = Z_SOCKET + 2.5           # underside of the module PCB: socket + header plastic body
T_PCB = 1.2
BOXES = [
    # header body on the module's back (between socket and PCB), 10.2 x 2.5 mm, straddling the pin row
    (-5.1, -1.27, 5.1, 1.27, Z_SOCKET, Z_PCB, (0.15, 0.15, 0.15)),
    # the module PCB: top edge 2.2 mm above the pin row, 27.3 x 27.8
    (-13.65, -2.2, 13.65, 25.6, Z_PCB, Z_PCB + T_PCB, (0.05, 0.15, 0.45)),
    # the glass: 26.7 x 19.3, from 5.5 mm below the module's top edge
    (-13.35, 3.3, 13.35, 22.6, Z_PCB + T_PCB, Z_PCB + T_PCB + 1.6, (0.02, 0.02, 0.02)),
    # active display area (visible face, lighter) 21.7 x 11.2, centred on the glass
    (-10.85, 7.35, 10.85, 18.55, Z_PCB + T_PCB + 1.6, Z_PCB + T_PCB + 1.62, (0.25, 0.28, 0.32)),
]


def box(x0, y0, x1, y1, z0, z1, rgb):
    u = 1 / 2.54
    # footprint y down -> VRML y up
    X0, X1 = x0 * u, x1 * u
    Y0, Y1 = -y1 * u, -y0 * u
    Z0, Z1 = z0 * u, z1 * u
    pts = [(X0, Y0, Z0), (X1, Y0, Z0), (X1, Y1, Z0), (X0, Y1, Z0),
           (X0, Y0, Z1), (X1, Y0, Z1), (X1, Y1, Z1), (X0, Y1, Z1)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    coords = ",\n      ".join("%.4f %.4f %.4f" % p for p in pts)
    idx = ",\n      ".join("%d, %d, %d, %d, -1" % f for f in faces)
    return """Shape {
  appearance Appearance {
    material Material {
      diffuseColor %.3f %.3f %.3f
      ambientIntensity 0.3
      specularColor 0.2 0.2 0.2
      shininess 0.1
    }
  }
  geometry IndexedFaceSet {
    solid FALSE
    coord Coordinate { point [
      %s
    ] }
    coordIndex [
      %s
    ]
  }
}
""" % (rgb[0], rgb[1], rgb[2], coords, idx)


def main():
    out = "#VRML V2.0 utf8\n# 0.96 in I2C OLED module (27.3 x 27.8 mm) on an 8.5 mm 1x4 socket - box model, gen: scripts/make_oled_model.py\n"
    out += "".join(box(*b) for b in BOXES)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    print("wrote", os.path.normpath(OUT), len(BOXES), "boxes")


if __name__ == "__main__":
    main()
