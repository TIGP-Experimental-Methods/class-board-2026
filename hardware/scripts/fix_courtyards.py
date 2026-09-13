"""Rewrite F.CrtYd of every footprint in lib/class_board.pretty as one rectangle covering
body (F.Fab / F.SilkS outline) + pads + 0.25 mm (IPC-7351 nominal), never smaller than the imported courtyard.
The EasyEDA imports drew the body only, which made KiCad's courtyard-overlap check meaningless."""
import glob
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fp_parse import Footprint  # noqa: E402
from sexp import uid            # noqa: E402

MARGIN = 0.25
LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib", "class_board.pretty")


def main():
    n = 0
    for path in sorted(glob.glob(os.path.join(LIB, "*.kicad_mod"))):
        fp = Footprint(path)
        xs, ys = [], []
        for p in fp.pads:
            hx, hy = p.half_extent()
            if p.kind == "np_thru_hole":
                hx = hy = (p.drill[0] if p.drill else max(p.sx, p.sy)) / 2
            xs += [p.x - hx, p.x + hx]
            ys += [p.y - hy, p.y + hy]
        for layer in ("F.Fab", "F.SilkS"):
            b = fp._layer_bbox(layer)
            if b:
                xs += [b[0], b[2]]
                ys += [b[1], b[3]]
        old = fp._layer_bbox("F.CrtYd")
        if not xs:
            continue
        x0, y0, x1, y1 = min(xs) - MARGIN, min(ys) - MARGIN, max(xs) + MARGIN, max(ys) + MARGIN
        if old:
            x0, y0, x1, y1 = min(x0, old[0]), min(y0, old[1]), max(x1, old[2]), max(y1, old[3])
        s = fp.text
        # drop existing courtyard graphics
        s2 = re.sub(r'\t\(fp_(line|rect|circle|arc|poly)\b(?:(?!\n\t\()[\s\S])*?\(layer "F\.CrtYd"\)[\s\S]*?\n\t\)\n', '', s)
        rect = ('\t(fp_rect\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(stroke\n\t\t\t(width 0.05)\n\t\t\t(type default)\n\t\t)\n'
                '\t\t(fill no)\n\t\t(layer "F.CrtYd")\n\t\t(uuid "%s")\n\t)\n' % (round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2), uid()))
        # insert before the first pad
        k = s2.find("\t(pad ")
        s2 = s2[:k] + rect + s2[k:]
        open(path, "w", encoding="utf-8").write(s2)
        n += 1
        print("%-50s court %6.2f x %6.2f  (was %s)" % (fp.name, x1 - x0, y1 - y0, "%.2f x %.2f" % (old[2] - old[0], old[3] - old[1]) if old else "-"))
    print("rewrote", n)


if __name__ == "__main__":
    main()
