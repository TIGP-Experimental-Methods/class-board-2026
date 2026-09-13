"""Minimal KiCad s-expression reader and footprint geometry extraction."""
import math
import os
import re


def parse(text):
    """Parse an s-expression string into nested lists (atoms are str)."""
    tokens = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)
    stack = [[]]
    for t in tokens:
        if t == "(":
            stack.append([])
        elif t == ")":
            node = stack.pop()
            stack[-1].append(node)
        else:
            if t.startswith('"'):
                t = bytes(t[1:-1], "utf-8").decode("unicode_escape") if "\\" in t else t[1:-1]
            stack[-1].append(t)
    return stack[0][0]


def find(node, key):
    return [n for n in node if isinstance(n, list) and n and n[0] == key]


def first(node, key, default=None):
    f = find(node, key)
    return f[0] if f else default


def num(v):
    return float(v)


class Pad:
    __slots__ = ("number", "kind", "shape", "x", "y", "rot", "sx", "sy", "drill", "layers", "node")

    def __init__(self, node):
        self.node = node
        self.number = node[1]
        self.kind = node[2]           # smd | thru_hole | np_thru_hole
        self.shape = node[3]
        at = first(node, "at")
        self.x, self.y = num(at[1]), num(at[2])
        self.rot = num(at[3]) if len(at) > 3 else 0.0
        size = first(node, "size")
        self.sx, self.sy = num(size[1]), num(size[2])
        if self.shape == "custom":
            # approximate a custom pad by the bounding box of its primitives (relative to the anchor)
            xs, ys = [], []
            prim = first(node, "primitives")
            for g in (prim[1:] if prim else []):
                if g[0] == "gr_poly":
                    for xy in first(g, "pts")[1:]:
                        xs.append(num(xy[1])); ys.append(num(xy[2]))
                elif g[0] in ("gr_rect", "gr_line"):
                    for k in ("start", "end"):
                        p = first(g, k); xs.append(num(p[1])); ys.append(num(p[2]))
                elif g[0] == "gr_circle":
                    c, e = first(g, "center"), first(g, "end")
                    r = math.hypot(num(e[1]) - num(c[1]), num(e[2]) - num(c[2]))
                    xs += [num(c[1]) - r, num(c[1]) + r]; ys += [num(c[2]) - r, num(c[2]) + r]
            if xs:
                cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
                r = math.radians(self.rot)
                self.x += cx * math.cos(r) - cy * math.sin(r)
                self.y += cx * math.sin(r) + cy * math.cos(r)
                self.sx, self.sy = max(xs) - min(xs), max(ys) - min(ys)
        d = first(node, "drill")
        self.drill = None
        if d:
            vals = [x for x in d[1:] if not isinstance(x, list) and x != "oval"]
            self.drill = tuple(num(v) for v in vals) if vals else None
        lay = first(node, "layers")
        self.layers = lay[1:] if lay else []

    def half_extent(self):
        """axis-aligned half extents after pad rotation (footprint-local)"""
        r = math.radians(self.rot)
        hx = abs(self.sx / 2 * math.cos(r)) + abs(self.sy / 2 * math.sin(r))
        hy = abs(self.sx / 2 * math.sin(r)) + abs(self.sy / 2 * math.cos(r))
        return hx, hy


class Footprint:
    def __init__(self, path):
        self.path = path
        self.text = open(path, encoding="utf-8").read()
        self.node = parse(self.text)
        self.name = self.node[1]
        self.pads = [Pad(p) for p in find(self.node, "pad")]
        attr = first(self.node, "attr")
        self.attrs = attr[1:] if attr else []
        self.courtyard = self._layer_bbox("F.CrtYd") or self._layer_bbox("F.Fab") or self.pad_bbox()
        self.silk = self._layer_bbox("F.SilkS")
        self.models = [m[1] for m in find(self.node, "model")]

    def _layer_bbox(self, layer):
        xs, ys = [], []
        for item in self.node:
            if not isinstance(item, list) or item[0] not in ("fp_line", "fp_rect", "fp_circle", "fp_poly", "fp_arc"):
                continue
            lay = first(item, "layer")
            if not lay or lay[1] != layer:
                continue
            if item[0] == "fp_circle":
                c, e = first(item, "center"), first(item, "end")
                r = math.hypot(num(e[1]) - num(c[1]), num(e[2]) - num(c[2]))
                xs += [num(c[1]) - r, num(c[1]) + r]; ys += [num(c[2]) - r, num(c[2]) + r]
                continue
            for key in ("start", "end", "center", "mid"):
                for k in find(item, key):
                    xs.append(num(k[1])); ys.append(num(k[2]))
            for pts in find(item, "pts"):
                for xy in find(pts, "xy"):
                    xs.append(num(xy[1])); ys.append(num(xy[2]))
        if not xs:
            return None
        return (min(xs), min(ys), max(xs), max(ys))

    def pad_bbox(self):
        xs, ys = [], []
        for p in self.pads:
            hx, hy = p.half_extent()
            xs += [p.x - hx, p.x + hx]; ys += [p.y - hy, p.y + hy]
        return (min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 0, 0)

    def is_tht(self):
        return "through_hole" in self.attrs or any(p.kind == "thru_hole" for p in self.pads)


def load_library(pretty_dir):
    lib = {}
    for fn in os.listdir(pretty_dir):
        if fn.endswith(".kicad_mod"):
            fp = Footprint(os.path.join(pretty_dir, fn))
            lib[fp.name] = fp
    return lib


if __name__ == "__main__":
    import sys
    lib = load_library(sys.argv[1])
    for name in sorted(lib):
        fp = lib[name]
        b = fp.courtyard
        print("%-50s pads=%2d tht=%d crtyd=(%.2f,%.2f)-(%.2f,%.2f) size=%.1fx%.1f" % (name, len(fp.pads), fp.is_tht(), b[0], b[1], b[2], b[3], b[2] - b[0], b[3] - b[1]))
