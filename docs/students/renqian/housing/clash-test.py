# Clash test - does any part of either board end up inside the housing?
# Ren Qian (Section A), 2026-10-08.
#
# The housing is built from numbers measured off the board meshes, so the one
# failure it cannot catch by construction is a number that was measured wrongly.
# This catches that: it takes every vertex of class-board.stl and front-panel.stl
# and asks whether that point is inside base.stl or cover.stl. Anything that
# comes back inside is plastic where a component wants to be.
#
#   python clash-test.py
#
# The method is the instructor's - his housing page describes "a clash test
# checks every point of the three board models against every part":
#   https://shaynebennetts.github.io/class-board-instrument/
# The implementation here is mine.
#
# Point-in-mesh by ray casting along +X, with the housing triangles bucketed
# into a (y, z) grid so each query only tests the few triangles its ray can
# actually hit. Without the grid this is 130k points x 4k triangles per part.

import os, re, struct, sys, math
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

# The cover halves are exported FACE DOWN for the plate - housing-cover.scad
# maps (x, y, z) -> (x, -y, top - z). This maps them back into the frame the
# boards are in. top = LOW_TOP 5.9 / HIGH_TOP 18.2 from housing-params.scad,
# which housing.scad echoes as "low deck top" and "raised top".
def unflip(top):   return lambda p: (p[0], -p[1], top - p[2])

HOUSING = [("base",       os.path.join(HERE, "base.stl"),       lambda p: p),
           ("cover low",  os.path.join(HERE, "cover-low.stl"),  unflip(5.9)),
           ("cover high", os.path.join(HERE, "cover-high.stl"), unflip(18.2))]
# The board meshes are NOT in the housing's frame as they sit on disk. The front
# panel is, but the main board has to be turned over and dropped, exactly as
# boards-assembled.scad does it:
#     translate([180, 0, -GAP]) rotate([0, 180, 0])
# which maps (x, y, z) -> (180 - x, y, -GAP - z), with GAP = 11 mm between the
# two facing board surfaces. Testing the raw mesh instead reports a confident
# clash in the cover's low deck that does not exist.
BOARD_GAP_MM = 11.0

def as_is(p):      return p
def main_board(p): return (180.0 - p[0], p[1], -BOARD_GAP_MM - p[2])

BOARDS  = [("main board",  os.path.join(REPO, "hardware", "release", "class-board.stl"),
            main_board),
           ("front panel", os.path.join(REPO, "hardware", "release", "front-panel.stl"),
            as_is)]

CELL = 4.0          # grid cell, mm
EPS  = 1e-9


def load(path):
    raw = open(path, "rb").read()
    if raw[:5] == b"solid" and b"facet normal" in raw[:2000]:
        f = [float(x) for x in re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)",
                                          raw.decode("ascii", "replace"))
             for x in x] if False else None
        v = [tuple(map(float, m)) for m in
             re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", raw.decode("ascii", "replace"))]
        return [(v[i], v[i+1], v[i+2]) for i in range(0, len(v), 3)]
    n = struct.unpack("<I", raw[80:84])[0]
    out = []
    for i in range(n):
        d = struct.unpack_from("<12fH", raw, 84 + i*50)
        out.append((d[3:6], d[6:9], d[9:12]))
    return out


class Solid:
    """Triangles indexed by the (y,z) cells their projection covers."""
    def __init__(self, tris):
        self.tris = tris
        self.grid = defaultdict(list)
        self.lo = [min(v[i] for t in tris for v in t) for i in range(3)]
        self.hi = [max(v[i] for t in tris for v in t) for i in range(3)]
        for k, t in enumerate(tris):
            y0 = int(math.floor(min(v[1] for v in t)/CELL))
            y1 = int(math.floor(max(v[1] for v in t)/CELL))
            z0 = int(math.floor(min(v[2] for v in t)/CELL))
            z1 = int(math.floor(max(v[2] for v in t)/CELL))
            for gy in range(y0, y1+1):
                for gz in range(z0, z1+1):
                    self.grid[(gy, gz)].append(k)

    # A ray along +X that lies exactly in a symmetry plane - and the mounting
    # holes put four of them at y = -19 and y = -111 - hits triangle edges
    # head on, where Moller-Trumbore will double count or miss. Three rays
    # nudged by a ten-thousandth of a millimetre, majority vote. That is six
    # orders of magnitude below anything that matters here.
    JITTER = [(0.0, 0.0), (1.3e-4, 0.7e-4), (-0.9e-4, -1.1e-4)]

    def inside(self, p):
        if not all(self.lo[i] - 1e-6 <= p[i] <= self.hi[i] + 1e-6 for i in range(3)):
            return False
        votes = sum(1 for dy, dz in self.JITTER
                    if self._cast(p[0], p[1] + dy, p[2] + dz))
        return votes >= 2

    def _cast(self, px, py, pz):
        cell = self.grid.get((int(math.floor(py/CELL)), int(math.floor(pz/CELL))))
        if not cell:
            return False
        hits = 0
        for k in cell:
            a, b, c = self.tris[k]
            e1 = (b[0]-a[0], b[1]-a[1], b[2]-a[2])
            e2 = (c[0]-a[0], c[1]-a[1], c[2]-a[2])
            # direction (1,0,0):  h = d x e2
            h = (0*e2[2]-0*e2[1], 0*e2[0]-1*e2[2], 1*e2[1]-0*e2[0])
            det = e1[0]*h[0] + e1[1]*h[1] + e1[2]*h[2]
            if -EPS < det < EPS:
                continue
            inv = 1.0/det
            s = (px-a[0], py-a[1], pz-a[2])
            u = inv*(s[0]*h[0] + s[1]*h[1] + s[2]*h[2])
            if u < 0.0 or u > 1.0:
                continue
            q = (s[1]*e1[2]-s[2]*e1[1], s[2]*e1[0]-s[0]*e1[2], s[0]*e1[1]-s[1]*e1[0])
            v = inv*q[0]
            if v < 0.0 or u+v > 1.0:
                continue
            t = inv*(e2[0]*q[0] + e2[1]*q[1] + e2[2]*q[2])
            if t > EPS:
                hits += 1
        return hits % 2 == 1


def main():
    parts = []
    for name, path, xform in HOUSING:
        if not os.path.exists(path):
            print("MISSING %s - export it first" % path); return 1
        tris = [tuple(xform(v) for v in t) for t in load(path)]
        parts.append((name, Solid(tris)))
        print("loaded %-12s %6d facets" % (name, len(tris)))

    bad_total = 0
    for bname, bpath, xform in BOARDS:
        if not os.path.exists(bpath):
            print("MISSING %s" % bpath); return 1
        tris = load(bpath)
        pts = sorted({tuple(round(c, 3) for c in xform(v)) for t in tris for v in t})
        print()
        print("%s: %d facets, %d distinct points" % (bname, len(tris), len(pts)))
        for pname, solid in parts:
            hits = [p for p in pts if solid.inside(p)]
            if hits:
                bad_total += len(hits)
                xs = [p[0] for p in hits]; ys = [p[1] for p in hits]; zs = [p[2] for p in hits]
                print("   CLASH with %s: %d points" % (pname, len(hits)))
                print("      X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f"
                      % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
                for p in hits[:10]:
                    print("      %8.2f %8.2f %8.2f" % p)
                if len(hits) > 10:
                    print("      ... and %d more" % (len(hits)-10))
            else:
                print("   clear of %s" % pname)

    print()
    print("RESULT:", "CLEAR - nothing on either board is inside the housing"
          if bad_total == 0 else "%d clashing points - see above" % bad_total)
    return 1 if bad_total else 0


if __name__ == "__main__":
    sys.exit(main())
