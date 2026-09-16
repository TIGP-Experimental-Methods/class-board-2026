"""Grid router for the class-board main PCB (F.Cu / B.Cu only; In1/In2 are unbroken GND planes).

Approach
- 0.125 mm raster per outer layer.  Every copper item is rasterised with a halo of
  (clearance + 0.02 mm grid margin + 0.125 mm half of a default track) so that a *free cell centre*
  guarantees the design-rule clearance for a 0.25 mm track through it.  Wider tracks / larger
  clearances check a disk of extra cells around the path.
- Escape stubs for fine-pitch SMD pads (exact pad-axis segment, then a <= 0.0625 mm 45 deg jog onto
  the grid), so every emitted segment is exactly 0 / 45 / 90 degrees (tools/pcb/audit_angles.py).
- A* with 8-neighbour moves (no corner cutting), via moves (F<->B) with a cost penalty, per-net
  layer restrictions (analog: F.Cu only, no vias).
- Post-processing: within each run of moves that uses two adjacent directions the moves are
  regrouped into one diagonal + one orthogonal segment; 90 degree corners are chamfered with the
  longest 45 degree cut that stays clear.  This turns staircase detours into long diagonals.
- GND: SMD pads get a via to the inner planes; THT pads connect to the planes directly.
- AGND: pads inside the AGND pour get a short track to an 'open' pour spot (so the fill reaches
  them); pads outside are routed to the pour; pour fragments carrying AGND items are bridged.
"""
import heapq
import math
import os
import sys
import time
from fnmatch import fnmatch

import numpy as np

HW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GRID = 0.125
NM = 125000                      # grid pitch in nanometres
MARGIN = 0.02                    # grid margin added to every clearance
HALF_DEF = 0.125                 # half of the default 0.25 mm track
VIA_D, VIA_DRILL = 0.6, 0.3
VIA_COST = {"FAST": 150, "POWER": 50, "POWER_RAW": 50, "ANALOG_OUT": 100, "ANALOG_IN": 100, "Default": 80}     # cells
VIA_CHECK_CELLS = 3              # cells around a via centre that must be free of other nets' halos
CORRIDOR = 6                     # reserved cells beyond an escape stub end
BAND_STRAIGHT = 4                # cells beyond the corridor in which a row's own nets may only move along the stub axis
BAND = 16                        # cells beyond the corridor that are a keep-out for nets not belonging to the pin row
FID_CLR = 0.6                    # pad clearance of fiducials / no-net pads
DEBUG_DUMPS = 12                 # PNG dumps of the raster around the first failures (hardware/.route_debug/)
NECK = 3.0                       # mm: tracks narrower than the class width this close to a pad centre
NECK_W = 0.25
LAYERS = ("F.Cu", "B.Cu")

CLASS_PATTERNS = [("POWER_RAW", "+5V_RAW"), ("POWER_RAW", "+5V_RAW_OR"),
                  ("POWER", "+12V"), ("POWER", "-12V"), ("POWER", "+5VA"), ("POWER", "+3V3"), ("POWER", "AGND"),
                  ("ANALOG_IN", "/b1_inputs/AIN*"), ("ANALOG_IN", "AI?"),
                  ("ANALOG_OUT", "AO?"), ("ANALOG_OUT", "/b3_outputs/AOUT*"),
                  ("FAST", "SPI_*"), ("FAST", "CS_*"), ("FAST", "FAST_OUT?"), ("FAST", "TRIG_*"),
                  ("FAST", "/b3_outputs/DAC_*"), ("FAST", "/base_mcu/*_MCU"),
                  ("ISO_IN", "/b4_switching/ISO*"), ("ISO_IN", "unconnected-(U401-NC*"), ("ISO_IN", "unconnected-(U402-NC*"),
                  ("MAINS", "/b4_switching/RLY_*")]
CLASS_WIDTH = {"Default": 0.25, "POWER_RAW": 1.0, "POWER": 0.5, "ANALOG_IN": 0.25, "ANALOG_OUT": 0.3,
               "FAST": 0.25, "ISO_IN": 0.3, "MAINS": 3.0}
CLASS_CLR = {"Default": 0.2, "POWER_RAW": 0.2, "POWER": 0.2, "ANALOG_IN": 0.3, "ANALOG_OUT": 0.2,
             "FAST": 0.2, "ISO_IN": 0.2, "MAINS": 5.0}
ISO_CLR = 2.5
ORDER = ["ISO_IN", "ANALOG_IN", "ANALOG_OUT", "FAST", "POWER_RAW", "POWER", "MAINS", "Default"]
F_ONLY = set()                  # analog nets may use B.Cu (outer layer over the AGND pour) for the link fan-out
LAYER_BIAS = {"FAST": (1.0, 1.15), "Default": (1.0, 1.05), "ANALOG_IN": (1.0, 1.3), "ANALOG_OUT": (1.0, 1.1)}

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
DIAG = math.sqrt(2.0)


def netclass(name):
    for cls, pat in CLASS_PATTERNS:
        if fnmatch(name, pat):
            return cls
    return "Default"


def disk_offsets(r_cells):
    out = []
    r = int(math.ceil(r_cells))
    for di in range(-r, r + 1):
        for dj in range(-r, r + 1):
            if di * di + dj * dj <= r_cells * r_cells + 1e-9:
                out.append((di, dj))
    return out


def point_in_poly(x, y, poly):
    inside = False
    n = len(poly)
    for k in range(n):
        x1, y1 = poly[k]
        x2, y2 = poly[(k + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xi:
                inside = not inside
    return inside


class Router:
    def __init__(self, board, comps, nets, pad_net, W, H, agnd_poly, iso_keepout, log=print, stub_hint=None, plane_gnd=True,
                 layer_hint=None, layer_hint_net=None):
        self.board, self.comps, self.nets, self.pad_net = board, comps, nets, pad_net
        self.stub_hint = stub_hint or {}
        self.layer_hint = layer_hint or {}      # ref -> preferred stub layer (0/1) for through-hole pin rows
        self.layer_hint_net = layer_hint_net or {}   # net -> preferred stub layer (overrides the ref hint)
        self.plane_gnd = plane_gnd          # False on 2-layer boards: GND is routed like any other net
        self.W, self.H = W, H
        self.NX, self.NY = int(round(W / GRID)) + 1, int(round(H / GRID)) + 1
        self.log = log
        self.agnd_poly = agnd_poly
        self.iso_keepout = iso_keepout
        # raster: owner netcode per cell, 0 free, -1 blocked
        # one owner raster per clearance level: items are marked with halo = max(own clearance, level)
        self.rasters = {c: [np.zeros((self.NX, self.NY), dtype=np.int32) for _ in LAYERS] for c in sorted(set(CLASS_CLR.values()))}
        self.own = self.rasters[0.2]
        self.iso_mask = np.zeros((self.NX, self.NY), dtype=bool)      # blocks non-ISO nets (both layers)
        self.noniso_mask = np.zeros((self.NX, self.NY), dtype=bool)   # blocks ISO nets
        self.via_ok = np.ones((self.NX, self.NY), dtype=bool)
        self.reserved_arr = np.zeros((self.NX, self.NY), dtype=np.int32)   # escape corridors: netcode
        # fan-out bands in front of pin rows: lane = axis flag of the straight zone (1 = moves along y, 2 = along x);
        # lane_group = footprint id owning the keep-out zone (foreign nets may not enter it)
        self.lane = [np.zeros((self.NX, self.NY), dtype=np.int8) for _ in LAYERS]
        self.lane_group = [np.zeros((self.NX, self.NY), dtype=np.int32) for _ in LAYERS]
        self.net_groups = {}        # net -> set of footprint ids whose pin rows the net belongs to
        self.agnd_vias = set()
        self.pads_by_net = {}       # netname -> [PadInst]
        self.pad_of = {}            # (ref, number) -> PadInst
        self.fp_of_pad = {}         # id(pad) -> FootprintInst
        self.escape = {}            # id(pad) -> (cell (i, j), layer set, corridor cells)
        self.tree_cells = {}        # netname -> set of (L, i, j) copper cells (for targets)
        self.stats = dict(tracks=0, vias=0, failed=[], gnd_vias=0)
        self.segments = []          # (x1, y1, x2, y2, w, layer, net, kind) in nm; kind = "stub" (never ripped) | "route"
        self.vias = []              # (x, y, net, kind)
        self._emit_kind = "stub"
        self.route_owner = [np.zeros((self.NX, self.NY), dtype=np.int32) for _ in LAYERS]   # routed copper cells only
        self.ripped_count = {}      # net -> times its routes were ripped up
        self.rebuilds = 0
        self.reroute_queue = []
        self.RIP_BUDGET = 300
        self.RIP_R = 16             # cells around a blocked escape searched for rippable routes
        self.fine_pitch = {}        # id(pad) -> pitch
        self.stitch = {}            # (footprint id, net) -> dict(layer, cells=[(i, j)...], ends=[(i, j), (i, j)], axis=(dx, dy))
        self.stitched_pads = {}     # id(pad) -> (footprint id, net)
        self._n_dumps = 0
        self._init_raster()

    # ------------------------------------------------------------------ geometry helpers
    def cell(self, x, y):
        return int(round(x / GRID)), int(round(y / GRID))

    def xy(self, i, j):
        return i * GRID, j * GRID

    def inb(self, i, j):
        return 0 <= i < self.NX and 0 <= j < self.NY

    def mark_track_cell(self, layer, i, j, half_w, clr_item, net, code):
        for c, arrs in self.rasters.items():
            halo = clr_item if net == "AGND" else max(clr_item, c)
            self.mark_disk(arrs[layer], i, j, (half_w + halo + MARGIN + HALF_DEF) / GRID, code)

    def mark_pad(self, layer, cx, cy, hx, hy, clr_item, net, code):
        for c, arrs in self.rasters.items():
            halo = clr_item if net == "AGND" else max(clr_item, c)
            self.mark_rect(arrs[layer], cx, cy, hx, hy, halo + MARGIN + HALF_DEF, code)

    def mark_disk(self, own, i, j, r_cells, code):
        r = int(math.ceil(r_cells))
        i0, i1 = max(0, i - r), min(self.NX - 1, i + r)
        j0, j1 = max(0, j - r), min(self.NY - 1, j + r)
        if i0 > i1 or j0 > j1:
            return
        sub = own[i0:i1 + 1, j0:j1 + 1]
        ii, jj = np.ogrid[i0:i1 + 1, j0:j1 + 1]
        m = (ii - i) ** 2 + (jj - j) ** 2 <= r_cells * r_cells + 1e-9
        res = self.reserved_arr[i0:i1 + 1, j0:j1 + 1]
        m &= (res == 0) | (res == code)
        free = sub == 0
        same = sub == code
        sub[m & free] = code
        sub[m & ~free & ~same] = -1

    def mark_rect(self, own, cx, cy, hx, hy, halo, code, mask=None):
        """rectangle (half sizes hx, hy, axis aligned) dilated by halo -> owner code in array own (or into a bool mask)"""
        i0, i1 = self.cell(cx - hx - halo, cy - hy - halo)[0], self.cell(cx + hx + halo, cy + hy + halo)[0]
        j0, j1 = self.cell(cx - hx - halo, cy - hy - halo)[1], self.cell(cx + hx + halo, cy + hy + halo)[1]
        i0, j0 = max(0, i0), max(0, j0)
        i1, j1 = min(self.NX - 1, i1), min(self.NY - 1, j1)
        if i0 > i1 or j0 > j1:
            return
        xs = (np.arange(i0, i1 + 1) * GRID)[:, None]
        ys = (np.arange(j0, j1 + 1) * GRID)[None, :]
        dx = np.maximum(np.abs(xs - cx) - hx, 0.0)
        dy = np.maximum(np.abs(ys - cy) - hy, 0.0)
        m = dx * dx + dy * dy <= halo * halo + 1e-9
        if mask is not None:
            mask[i0:i1 + 1, j0:j1 + 1] |= m
            return
        sub = own[i0:i1 + 1, j0:j1 + 1]
        res = self.reserved_arr[i0:i1 + 1, j0:j1 + 1]
        m &= (res == 0) | (res == code)
        free = sub == 0
        same = sub == code
        sub[m & free] = code
        sub[m & ~free & ~same] = -1

    def pad_layers(self, pad):
        if pad.kind in ("thru_hole", "np_thru_hole"):
            return [0, 1]
        L = []
        if "F.Cu" in pad.layers or "*.Cu" in pad.layers:
            L.append(0)
        if "B.Cu" in pad.layers or "*.Cu" in pad.layers:
            L.append(1)
        return L

    # ------------------------------------------------------------------ raster init
    def _init_raster(self):
        b = self.board
        self.code_of = {n.name: n.code for n in b.nets.values()}
        for f in b.footprints:
            pads = f.pads
            for p in pads:
                self.fp_of_pad[id(p)] = f
                self.pad_of[(f.ref, p.number)] = p
                if p.net:
                    self.pads_by_net.setdefault(p.net, []).append(p)
            # pitch (nearest other pad of the same footprint)
            for p in pads:
                d = min([math.hypot(p.x - q.x, p.y - q.y) for q in pads if q is not p] or [99])
                self.fine_pitch[id(p)] = d
        # edge
        e = self.cell(0.3 + MARGIN + HALF_DEF, 0)[0] + 1
        for arrs in self.rasters.values():
            for own in arrs:
                own[:e, :] = -1
                own[self.NX - e:, :] = -1
                own[:, :e] = -1
                own[:, self.NY - e:] = -1
        self.via_ok[:] = True
        ev = self.cell(0.3 + VIA_D / 2 + MARGIN, 0)[0] + 1
        self.via_ok[:ev, :] = False
        self.via_ok[self.NX - ev:, :] = False
        self.via_ok[:, :ev] = False
        self.via_ok[:, self.NY - ev:] = False
        # ISO keepout: no vias inside
        (kx0, ky0), (kx1, ky1) = self.iso_keepout
        i0, j0 = self.cell(kx0 - VIA_D / 2, ky0 - VIA_D / 2)
        i1, j1 = self.cell(kx1 + VIA_D / 2, ky1 + VIA_D / 2)
        self.via_ok[max(0, i0):i1 + 1, max(0, j0):j1 + 1] = False
        # pads
        for f in b.footprints:
            for p in f.pads:
                code = self.code_of.get(p.net, -1) if p.net else -1
                cls = netclass(p.net) if p.net else "Default"
                clr = CLASS_CLR[cls] if p.net else FID_CLR
                hx, hy = p.hx, p.hy
                if p.kind == "np_thru_hole":
                    hx = hy = (p.drill[0] if p.drill else max(p.sx, p.sy)) / 2
                for L in self.pad_layers(p):
                    self.mark_pad(L, p.x, p.y, hx, hy, clr, p.net, code)
                if cls == "ISO_IN":
                    self.mark_rect(None, p.x, p.y, hx, hy, ISO_CLR + MARGIN + HALF_DEF, 0, mask=self.iso_mask)
                elif p.net:
                    self.mark_rect(None, p.x, p.y, hx, hy, ISO_CLR + MARGIN + HALF_DEF, 0, mask=self.noniso_mask)
                # holes: keep vias 0.5 mm hole-to-hole away
                if p.kind in ("thru_hole", "np_thru_hole") and p.drill:
                    rr = p.drill[0] / 2 + 0.5 + VIA_DRILL / 2 + 0.07
                    i, j = self.cell(p.x, p.y)
                    r = int(math.ceil(rr / GRID))
                    ii, jj = np.ogrid[max(0, i - r):min(self.NX, i + r + 1), max(0, j - r):min(self.NY, j + r + 1)]
                    m = (ii - i) ** 2 + (jj - j) ** 2 <= (rr / GRID) ** 2
                    self.via_ok[max(0, i - r):min(self.NX, i + r + 1), max(0, j - r):min(self.NY, j + r + 1)] &= ~m
        # footprint copper graphics (e.g. the net-tie bridge polygon): blocked for everybody
        for f in b.footprints:
            for item in f.fp.node[2:]:
                if not isinstance(item, list) or item[0] not in ("fp_poly", "fp_rect", "fp_line", "fp_circle"):
                    continue
                lay = next((c for c in item if isinstance(c, list) and c and c[0] == "layer"), None)
                if not lay or lay[1] not in ("F.Cu", "B.Cu"):
                    continue
                xs, ys = [], []
                for c in item:
                    if isinstance(c, list) and c and c[0] in ("start", "end", "center"):
                        xs.append(float(c[1])); ys.append(float(c[2]))
                    if isinstance(c, list) and c and c[0] == "pts":
                        for xy in c[1:]:
                            xs.append(float(xy[1])); ys.append(float(xy[2]))
                if not xs:
                    continue
                cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
                hx, hy = (max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2
                r = math.radians(f.rot)
                sgn = -1 if f.back else 1
                bx = f.x + cx * math.cos(r) + sgn * cy * math.sin(r)
                by = f.y - cx * math.sin(r) + sgn * cy * math.cos(r)
                if f.rot % 180 == 90:
                    hx, hy = hy, hx
                L = 0 if (lay[1] == "F.Cu") != f.back else 1
                for lvl, arrs in self.rasters.items():
                    self.mark_rect(arrs[L], bx, by, hx, hy, lvl + MARGIN + HALF_DEF, -1)
        # seed tree cells with pad copper cells
        for net, pads in self.pads_by_net.items():
            cells = set()
            for p in pads:
                for L in self.pad_layers(p):
                    for c in self.pad_cells(p):
                        cells.add((L,) + c)
            self.tree_cells[net] = cells

    def pad_cells(self, p):
        """grid cells whose centre lies inside the pad copper (shrunk a little)"""
        out = []
        i0, j0 = self.cell(p.x - p.hx, p.y - p.hy)
        i1, j1 = self.cell(p.x + p.hx, p.y + p.hy)
        round_pad = p.shape in ("circle", "oval")
        for i in range(max(0, i0), min(self.NX - 1, i1) + 1):
            for j in range(max(0, j0), min(self.NY - 1, j1) + 1):
                x, y = self.xy(i, j)
                if round_pad:
                    rmin = min(p.hx, p.hy)
                    # oval: distance to the pad's centre segment
                    dx = max(abs(x - p.x) - (p.hx - rmin), 0.0)
                    dy = max(abs(y - p.y) - (p.hy - rmin), 0.0)
                    if dx * dx + dy * dy <= (rmin - 0.05) ** 2 + 1e-9:
                        out.append((i, j))
                elif abs(x - p.x) <= p.hx - 0.05 + 1e-9 and abs(y - p.y) <= p.hy - 0.05 + 1e-9:
                    out.append((i, j))
        if not out:
            out.append(self.cell(p.x, p.y))
        return out

    # ------------------------------------------------------------------ exact segment emission
    def emit(self, x1, y1, x2, y2, w, layer, net):
        """coordinates in nm (ints) -> board track"""
        if x1 == x2 and y1 == y2:
            return
        self.segments.append((x1, y1, x2, y2, w, layer, net, self._emit_kind))

    def connect_nm(self, p, g, w, layer, net):
        """exact 45 deg jog + axis segment from point p to grid point g (both nm tuples)"""
        dx, dy = g[0] - p[0], g[1] - p[1]
        m = min(abs(dx), abs(dy))
        q = p
        if m:
            q = (p[0] + (m if dx > 0 else -m), p[1] + (m if dy > 0 else -m))
            self.emit(p[0], p[1], q[0], q[1], w, layer, net)
        self.emit(q[0], q[1], g[0], g[1], w, layer, net)

    def nm(self, x):
        return int(round(x * 1e6))

    # ------------------------------------------------------------------ escape stubs
    def outward(self, p):
        f = self.fp_of_pad[id(p)]
        # long axis of the pad, pointing away from the footprint centre
        if abs(p.hx - p.hy) > 0.05:
            ax = (1, 0) if p.hx > p.hy else (0, 1)
        else:
            dx, dy = p.x - f.x, p.y - f.y
            ax = (1, 0) if abs(dx) >= abs(dy) else (0, 1)
        dx, dy = p.x - f.x, p.y - f.y
        s = dx if ax[0] else dy
        if abs(s) < 1e-6:
            s = 1.0
        sgn = 1 if s > 0 else -1
        return (ax[0] * sgn, ax[1] * sgn)

    def make_stubs(self):
        """escape stubs for SMD pads of multi-pin parts (pitch < 1.1 mm): exact axial segment past the
        pad end, then onto the grid; a short corridor of grid cells is reserved for the net."""
        reserved = {}
        stubs = []
        self.group_of = {id(f): k + 1 for k, f in enumerate(self.board.footprints)}
        self.make_tht_stubs(stubs, reserved)
        for f in self.board.footprints:
            smd = [p for p in f.pads if p.kind == "smd"]
            if len(smd) < 3:
                continue
            for p in smd:
                if not p.net or self.fine_pitch[id(p)] > 1.1 or len(self.pads_by_net.get(p.net, [])) < 2:
                    continue
                cls = netclass(p.net)
                code = self.code_of[p.net]
                layer0 = 0 if 0 in self.pad_layers(p) else 1
                d0 = self.outward(p)
                has_npth = any(o.kind == "np_thru_hole" for o in f.pads)
                if (p.net == "AGND" or (p.net == "GND" and self.plane_gnd)) and not has_npth:
                    # ground pins of a fine-pitch IC: short stub INWARD (under the body), stitched together along the
                    # pin row and taken out at the package end, where a via fits (D-29)
                    d = (-d0[0], -d0[1])
                    half_len = p.hx if d[0] else p.hy
                    L0 = half_len + 0.45
                    gx, gy = p.x + d[0] * L0, p.y + d[1] * L0
                    gi, gj = int(round(gx / GRID)), int(round(gy / GRID))
                    key = (id(f), p.net)
                    st = self.stitch.setdefault(key, dict(layer=layer0, pads=[], w=0.25, code=code, cls=cls, axis=(abs(d[1]), abs(d[0]))))
                    st["pads"].append((p, (gx, gy), (gi, gj)))
                    self.stitched_pads[id(p)] = key
                    continue
                chosen = None
                for d in (d0, (-d0[0], -d0[1])):
                    half_len = p.hx if d[0] else p.hy
                    L0 = half_len + 0.3
                    qx, qy = p.x + d[0] * L0, p.y + d[1] * L0
                    # first grid cell centre at least 0.0625 beyond q along the axis
                    if d[0]:
                        gi = int(math.ceil((qx + 0.0625 * d[0]) / GRID)) if d[0] > 0 else int(math.floor((qx - 0.0625) / GRID))
                        gj = int(round(qy / GRID))
                    else:
                        gj = int(math.ceil((qy + 0.0625) / GRID)) if d[1] > 0 else int(math.floor((qy - 0.0625) / GRID))
                        gi = int(round(qx / GRID))
                    corridor = [(gi + d[0] * k, gj + d[1] * k) for k in range(0, CORRIDOR)]
                    ok = all(self.inb(i, j) and self.own[layer0][i, j] in (0, code) for (i, j) in corridor)
                    if ok or chosen is None:
                        chosen = (d, qx, qy, gi, gj, corridor)
                    if ok:
                        break
                d, qx, qy, gi, gj, corridor = chosen
                w = 0.25 if self.fine_pitch[id(p)] < 0.6 else min(CLASS_WIDTH[cls], 0.3)
                stubs.append((p, code, cls, (qx, qy), (gi, gj), corridor, w, layer0))
                for c in corridor:
                    reserved[c] = code
        self.reserved = reserved
        for (i, j), code in reserved.items():
            if self.inb(i, j):
                self.reserved_arr[i, j] = code
        self.emit_stitches()
        for p, code, cls, (qx, qy), g, corridor, w, layer in stubs:
            pnm = (self.nm(p.x), self.nm(p.y))
            qnm = (self.nm(qx), self.nm(qy))
            gnm = (g[0] * NM, g[1] * NM)
            self.emit(pnm[0], pnm[1], qnm[0], qnm[1], w, layer, p.net)
            self.connect_nm(qnm, gnm, w, layer, p.net)
            self.escape[id(p)] = (g, layer, corridor)
            # mark the stub + corridor (halo), never overwriting reserved cells of other nets
            cells = self.line_cells(pnm, qnm) + self.jog_line_cells(qnm, gnm) + corridor
            mark_layers = [layer]
            for c_level, arrs in self.rasters.items():
              for mlayer in mark_layers:
                halo = CLASS_CLR[cls] if p.net == "AGND" else max(CLASS_CLR[cls], c_level)
                halo_cells = (w / 2 + halo + MARGIN + HALF_DEF) / GRID
                own = arrs[mlayer]
                r = int(math.ceil(halo_cells))
                for (ci, cj) in cells:
                    for di in range(-r, r + 1):
                        for dj in range(-r, r + 1):
                            if di * di + dj * dj > halo_cells * halo_cells + 1e-9:
                                continue
                            i, j = ci + di, cj + dj
                            if not self.inb(i, j):
                                continue
                            rc = reserved.get((i, j))
                            if rc is not None and rc != code:
                                continue
                            v = own[i, j]
                            if v == 0:
                                own[i, j] = code
                            elif v != code:
                                own[i, j] = -1
                for c in corridor:
                    own[c] = code
            self.tree_cells.setdefault(p.net, set()).update((layer,) + c for c in corridor)
            # fan-out band: straight zone (own nets move along the axis only) + keep-out zone for foreign nets
            d = (corridor[1][0] - corridor[0][0], corridor[1][1] - corridor[0][1])
            pitch = self.fine_pitch[id(p)]
            lat = int(math.ceil(pitch / 2 / GRID))
            flag = 1 if d[1] else 2
            gid = self.group_of[id(self.fp_of_pad[id(p)])]
            self.net_groups.setdefault(p.net, set()).add(gid)
            lane = self.lane[layer]
            lgrp = self.lane_group[layer]
            for k in range(CORRIDOR, CORRIDOR + BAND):
                ci, cj = corridor[0][0] + d[0] * k, corridor[0][1] + d[1] * k
                for t in range(-lat, lat + 1):
                    i, j = (ci + t, cj) if d[1] else (ci, cj + t)
                    if not self.inb(i, j):
                        continue
                    if k < CORRIDOR + BAND_STRAIGHT and lane[i, j] == 0:
                        lane[i, j] = flag
                    if lgrp[i, j] == 0:
                        lgrp[i, j] = gid
            if cls == "ISO_IN":
                for (ci, cj) in cells:
                    self.mark_rect(None, ci * GRID, cj * GRID, w / 2, w / 2, ISO_CLR + MARGIN + HALF_DEF, 0, mask=self.iso_mask)
        # a net whose pad lies inside a fan-out band belongs to that band (e.g. resistors under a header)
        for f in self.board.footprints:
            for p in f.pads:
                if not p.net:
                    continue
                for L in self.pad_layers(p):
                    lg = self.lane_group[L]
                    for (i, j) in self.pad_cells(p):
                        g = int(lg[i, j])
                        if g:
                            self.net_groups.setdefault(p.net, set()).add(g)
        self.log("stubs: %d" % len(stubs))

    def jog_line_cells(self, a, g):
        """cells of the exact 45 deg jog + axis path from point a (nm, may be off-grid) to grid point g"""
        dx, dy = g[0] - a[0], g[1] - a[1]
        m = min(abs(dx), abs(dy))
        q = (a[0] + (m if dx > 0 else -m), a[1] + (m if dy > 0 else -m))
        return self.line_cells(a, q) + self.line_cells(q, g)

    def jog_cells(self, s, g):
        """cells of the exact 45 deg jog + axis path between grid cells s and g"""
        dx, dy = g[0] - s[0], g[1] - s[1]
        m = min(abs(dx), abs(dy))
        q = (s[0] + (m if dx > 0 else -m), s[1] + (m if dy > 0 else -m))
        out = []
        for k in range(m + 1):
            out.append((s[0] + (k if dx > 0 else -k), s[1] + (k if dy > 0 else -k)))
        n = max(abs(g[0] - q[0]), abs(g[1] - q[1]))
        for k in range(1, n + 1):
            out.append((q[0] + (k if g[0] > q[0] else (-k if g[0] < q[0] else 0)), q[1] + (k if g[1] > q[1] else (-k if g[1] < q[1] else 0))))
        return out

    def emit_stitches(self):
        """inward ground stubs of one IC + net joined by a track along the pin row (exact axis geometry)"""
        for key, st in self.stitch.items():
            L = st["layer"]
            code, cls, w = st["code"], st["cls"], st["w"]
            net = key[1]
            ax = st["axis"]                       # row direction (unit, axis aligned)
            pads = sorted(st["pads"], key=lambda t: t[1][0] * ax[0] + t[1][1] * ax[1])
            cells = []
            # pad -> inward point (exact axial segment), inward point sits on the stitch line
            line_c = None
            for p, (gx, gy), (gi, gj) in pads:
                pnm = (self.nm(p.x), self.nm(p.y))
                gnm = (self.nm(gx), self.nm(gy))
                self.emit(pnm[0], pnm[1], gnm[0], gnm[1], w, L, net)
                cells += self.line_cells(pnm, gnm)
                line_c = gnm
            # stitch along the row through the inward points (all share the same lateral coordinate)
            for (p1, g1, _), (p2, g2, _) in zip(pads, pads[1:]):
                a = (self.nm(g1[0]), self.nm(g1[1]))
                b = (self.nm(g2[0]), self.nm(g2[1]))
                self.emit(a[0], a[1], b[0], b[1], w, L, net)
                cells += self.line_cells(a, b)
            # the two row ends, snapped to grid cells along the row axis (exact jog onto the grid)
            ends = []
            for (p, g, _) in (pads[0], pads[-1]):
                sgn = -1 if (p, g, _) == pads[0] else 1
                ex = g[0] + ax[0] * sgn * 0.6
                ey = g[1] + ax[1] * sgn * 0.6
                ci = int(round(ex / GRID)) if ax[0] else int(round(g[0] / GRID))
                cj = int(round(ey / GRID)) if ax[1] else int(round(g[1] / GRID))
                # keep the end on the stitch line laterally: the lateral coordinate is g (exact), so jog onto the grid
                gnm = (self.nm(g[0]), self.nm(g[1]))
                enm = (ci * NM, cj * NM)
                self.connect_nm(gnm, enm, w, L, net)
                cells += self.jog_line_cells(gnm, enm)
                ends.append((ci, cj))
            st["ends"] = ends
            st["cells"] = cells
            for (ci, cj) in cells:
                self.mark_track_cell(L, ci, cj, w / 2, CLASS_CLR[cls], net, code)
            self.tree_cells.setdefault(net, set()).update((L,) + c for c in cells)
        if self.stitch:
            self.log("ground stitches: %d (%d pins)" % (len(self.stitch), sum(len(s["pads"]) for s in self.stitch.values())))

    def make_tht_stubs(self, stubs, reserved):
        """Escape stubs for through-hole connector pins (pitch <= 2.6 mm, >= 4 pins): perpendicular to the pin row,
        away from the part; if another pin blocks the straight way (2-row header, inner row) the stub jogs 45 deg into
        the gap between the pins of the other row and continues straight.  Emitted as (pad, code, cls, q, g, corridor, w)
        with q == pad centre so the generic emitter draws pad -> 45 deg jog -> axis segment."""
        for f in self.board.footprints:
            tht = [p for p in f.pads if p.kind == "thru_hole"]
            if len(tht) < 4:
                continue
            xs = [o.x for o in tht]
            ys = [o.y for o in tht]
            row_x = (max(xs) - min(xs)) >= (max(ys) - min(ys))    # pins spread along x -> escape along y
            for p in tht:
                if not p.net or self.fine_pitch[id(p)] > 2.6:
                    continue
                if (p.net == "GND" and self.plane_gnd) or (p.net == "AGND" and point_in_poly(p.x, p.y, self.agnd_poly)):
                    continue                           # planes / pour connect these directly
                if len(self.pads_by_net.get(p.net, [])) < 2:
                    continue                           # single-pad net: nothing to route
                cls = netclass(p.net)
                code = self.code_of[p.net]
                perp = (0, 1) if row_x else (1, 0)
                comp = (p.y - f.y) if row_x else (p.x - f.x)
                hint = self.stub_hint.get(f.ref)
                if hint is not None:                                  # forced escape direction for the whole part
                    sgn = hint[1] if row_x else hint[0]
                elif abs(comp) < 0.3:
                    sgn = 1
                else:
                    sgn = 1 if comp > 0 else -1
                pitch = self.fine_pitch[id(p)]
                rad = max(p.hx, p.hy)
                chosen = None
                for s in (sgn, -sgn):
                    d = (perp[0] * s, perp[1] * s)
                    along = (lambda o: (o.y - p.y) * s) if row_x else (lambda o: (o.x - p.x) * s)
                    lat = (lambda o: o.x - p.x) if row_x else (lambda o: o.y - p.y)
                    blockers = [o for o in f.pads if o is not p and along(o) > 0.01 and abs(lat(o)) < pitch * 0.75]
                    cands = []
                    if not blockers:
                        cands.append(0.0)                          # straight
                    cands += [pitch / 2, -pitch / 2]                # diagonal into the neighbouring gap
                    for latoff in cands:
                        ahead = [o for o in f.pads if o is not p and along(o) > -0.01 and abs(lat(o) - latoff) < pitch * 0.75 + 0.2]
                        far = max([along(o) + max(o.hx, o.hy) for o in ahead] + [rad]) + 0.4
                        if row_x:
                            gx = round((p.x + latoff) / GRID) * GRID
                            gy = p.y + s * far
                            gj = int(math.ceil(gy / GRID)) if s > 0 else int(math.floor(gy / GRID))
                            gi = int(round(gx / GRID))
                        else:
                            gy = round((p.y + latoff) / GRID) * GRID
                            gx = p.x + s * far
                            gi = int(math.ceil(gx / GRID)) if s > 0 else int(math.floor(gx / GRID))
                            gj = int(round(gy / GRID))
                        corridor = [(gi + d[0] * k, gj + d[1] * k) for k in range(0, CORRIDOR)]
                        lh = self.layer_hint_net.get(p.net, self.layer_hint.get(f.ref))
                        for layer in ((lh, 1 - lh) if lh is not None else (0, 1)):
                            ok = all(self.inb(i, j) and self.own[layer][i, j] in (0, code) for (i, j) in corridor)
                            if ok:
                                chosen = ((gi, gj), corridor, d, layer)
                                break
                        if chosen:
                            break
                    if chosen:
                        break
                if not chosen:
                    continue
                (gi, gj), corridor, d, layer = chosen
                w = min(CLASS_WIDTH[cls], 0.3)
                stubs.append((p, code, cls, (p.x, p.y), (gi, gj), corridor, w, layer))
                for c in corridor:
                    reserved[c] = code

    def line_cells(self, a, b):
        """grid cells touched by the segment a-b (nm) sampled every half cell"""
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / (NM / 2)))
        out = []
        for k in range(n + 1):
            t = k / n
            x = a[0] + (b[0] - a[0]) * t
            y = a[1] + (b[1] - a[1]) * t
            out.append((int(round(x / NM)), int(round(y / NM))))
        return out

    # ------------------------------------------------------------------ passability windows
    def blocked_window(self, code, cls, i0, i1, j0, j1, r_extra_cells, layer, net=None):
        own = self.rasters[CLASS_CLR[cls]][layer][i0:i1 + 1, j0:j1 + 1]
        blk = (own != 0) & (own != code)
        lg = self.lane_group[layer][i0:i1 + 1, j0:j1 + 1]
        groups = self.net_groups.get(net, set()) if net else set()
        foreign = lg != 0
        if groups:
            foreign &= ~np.isin(lg, list(groups))
        if foreign.any():
            halo_cells = (CLASS_WIDTH[cls] / 2 + CLASS_CLR[cls] + MARGIN + HALF_DEF) / GRID
            foreign = self.dilate(foreign, halo_cells)
            # never block the net's own escape corridors / band cells with a neighbouring band's stand-off
            if groups:
                foreign &= ~np.isin(lg, list(groups))
            foreign &= ~(self.reserved_arr[i0:i1 + 1, j0:j1 + 1] == code)
        blk = blk | foreign
        if cls == "ISO_IN":
            blk |= self.noniso_mask[i0:i1 + 1, j0:j1 + 1]
        else:
            blk |= self.iso_mask[i0:i1 + 1, j0:j1 + 1]
        if r_extra_cells > 0:
            blk = self.dilate(blk, r_extra_cells)
        return blk

    @staticmethod
    def dilate(mask, r_cells):
        out = mask.copy()
        r = int(math.ceil(r_cells - 1e-9))
        nx, ny = mask.shape
        for di, dj in disk_offsets(r):
            if di == 0 and dj == 0:
                continue
            src = mask[max(0, -di):nx - max(0, di), max(0, -dj):ny - max(0, dj)]
            out[max(0, di):nx - max(0, -di), max(0, dj):ny - max(0, -dj)] |= src
        return out

    # ------------------------------------------------------------------ A*
    def astar(self, net, cls, starts, targets, layers_allowed, width, clr, pad_centres, window, allow_via=True):
        """starts: list of (L,i,j); targets: set of (L,i,j).  Returns list of (L,i,j) or None."""
        code = self.code_of[net]
        i0, j0, i1, j1 = window
        wx, wy = i1 - i0 + 1, j1 - j0 + 1
        n_xy = wx * wy
        r_extra = max(0.0, width / 2 - HALF_DEF - 0.03) / GRID
        blk_n, blk_w, viablk = [], [], None
        for L in range(2):
            bn = self.blocked_window(code, cls, i0, i1, j0, j1, 0, L, net=net)
            blk_n.append(bn)
            blk_w.append(self.dilate(bn, r_extra) if r_extra > 0 else bn)
        if allow_via:
            vb = blk_n[0] | blk_n[1]
            vb = self.dilate(vb, VIA_CHECK_CELLS)
            vb |= ~self.via_ok[i0:i1 + 1, j0:j1 + 1]
            viablk = vb.ravel().tolist()
        # neck region (near pads of this net): narrow width allowed
        near = np.zeros((wx, wy), dtype=bool)
        if r_extra > 0:
            xs = (np.arange(i0, i1 + 1) * GRID)[:, None]
            ys = (np.arange(j0, j1 + 1) * GRID)[None, :]
            for (px, py) in pad_centres:
                if i0 * GRID - NECK <= px <= i1 * GRID + NECK and j0 * GRID - NECK <= py <= j1 * GRID + NECK:
                    near |= (xs - px) ** 2 + (ys - py) ** 2 <= NECK * NECK
        near_l = near.ravel().tolist()
        pass_l = []
        lane_l = []
        for L in range(2):
            ok = ~blk_w[L] | (~blk_n[L] & near) if r_extra > 0 else ~blk_n[L]
            pass_l.append(ok.ravel().tolist())
            lane_l.append(self.lane[L][i0:i1 + 1, j0:j1 + 1].ravel().tolist())
        # heuristic (octile) to the nearest target xy
        txy = sorted(set((t[1], t[2]) for t in targets))
        if len(txy) > 150:
            step = len(txy) // 150 + 1
            txy = txy[::step]
        ii = np.arange(i0, i1 + 1)[:, None]
        jj = np.arange(j0, j1 + 1)[None, :]
        h = np.full((wx, wy), 1e9)
        for (ti, tj) in txy:
            di = np.abs(ii - ti)
            dj = np.abs(jj - tj)
            h = np.minimum(h, np.maximum(di, dj) + (DIAG - 1) * np.minimum(di, dj))
        h_l = h.ravel().tolist()
        bias = LAYER_BIAS.get(cls, (1.0, 1.0))
        tgt = set()
        for (L, ti, tj) in targets:
            if i0 <= ti <= i1 and j0 <= tj <= j1:
                tgt.add(L * n_xy + (ti - i0) * wy + (tj - j0))
        if not tgt:
            return None
        INF = float("inf")
        if getattr(self, "_dbg_start", None) in [tuple(s_) for s_ in starts]:
            (Ld, sd_i, sd_j) = self._dbg_start
            rem_d = (sd_i - i0) * wy + (sd_j - j0)
            print("DBG astar %s cls %s start %s: pass F=%s B=%s viablk=%s lane=%s layers=%s allow_via=%s r_extra=%.2f" % (
                net, cls, self._dbg_start, pass_l[0][rem_d], pass_l[1][rem_d], (viablk[rem_d] if viablk else None), lane_l[Ld][rem_d], layers_allowed, allow_via, r_extra))
            for k in range(1, 6):
                rem_k = rem_d - k
                print("   up %d: passF=%s passB=%s viablk=%s" % (k, pass_l[0][rem_k], pass_l[1][rem_k], viablk[rem_k] if viablk else None))
            bl = []
            for di_ in range(-3, 4):
                for dj_ in range(-3, 4):
                    if di_ * di_ + dj_ * dj_ <= 9:
                        rr_ = rem_d + di_ * wy + dj_
                        if blk_n[0].ravel()[rr_] or blk_n[1].ravel()[rr_]:
                            bl.append((di_, dj_, bool(blk_n[0].ravel()[rr_]), bool(blk_n[1].ravel()[rr_]), int(self.own[0][sd_i + di_, sd_j + dj_]), int(self.own[1][sd_i + di_, sd_j + dj_]), int(self.lane_group[0][sd_i + di_, sd_j + dj_]), int(self.lane_group[1][sd_i + di_, sd_j + dj_])))
            print("   blocked in disk (di,dj,blkF,blkB,ownF,ownB,grpF,grpB):", bl[:12])
        g = {}
        parent = {}
        heap = []
        for (L, si, sj) in starts:
            if L not in layers_allowed or not (i0 <= si <= i1 and j0 <= sj <= j1):
                continue
            s = L * n_xy + (si - i0) * wy + (sj - j0)
            g[s] = 0.0
            parent[s] = -1
            heapq.heappush(heap, (h_l[s % n_xy], 0.0, s))
        # move table: (di, dj, dflat, cost, corner flats)
        mv = []
        for (di, dj) in DIRS:
            dflat = di * wy + dj
            cost = DIAG if di and dj else 1.0
            corners = (di * wy, dj) if di and dj else None
            mv.append((di, dj, dflat, cost, corners))
        closed = set()
        found = None
        while heap:
            f_, gc, s = heapq.heappop(heap)
            if s in closed:
                continue
            closed.add(s)
            if s in tgt:
                found = s
                break
            L = s // n_xy
            rem = s - L * n_xy
            ci, cj = divmod(rem, wy)
            pl = pass_l[L]
            ll = lane_l[L]
            b = bias[L]
            lane_here = ll[rem]
            for (di, dj, dflat, cost, corners) in mv:
                ni, nj = ci + di, cj + dj
                if ni < 0 or nj < 0 or ni >= wx or nj >= wy:
                    continue
                nrem = rem + dflat
                if not pl[nrem]:
                    continue
                lf = lane_here or ll[nrem]
                if lf and ((lf == 1 and di) or (lf == 2 and dj)):
                    continue
                if corners is not None and (not pl[rem + corners[0]] or not pl[rem + corners[1]]):
                    continue
                ns = L * n_xy + nrem
                ng = gc + cost * b
                if ng < g.get(ns, INF):
                    g[ns] = ng
                    parent[ns] = s
                    heapq.heappush(heap, (ng + h_l[nrem], ng, ns))
            if allow_via and len(layers_allowed) > 1 and not viablk[rem]:
                L2 = 1 - L
                if pass_l[L2][rem]:
                    ns = L2 * n_xy + rem
                    ng = gc + VIA_COST.get(cls, VIA_COST["Default"])
                    if ng < g.get(ns, INF):
                        g[ns] = ng
                        parent[ns] = s
                        heapq.heappush(heap, (ng + h_l[rem], ng, ns))
        if found is None:
            n_s = sum(1 for (L, si, sj) in starts if i0 <= si <= i1 and j0 <= sj <= j1 and L in layers_allowed and pass_l[L][(si - i0) * wy + (sj - j0)])
            n_t = sum(1 for t in tgt if pass_l[t // n_xy][t % n_xy])
            self._fail_info = "passable starts %d/%d, passable targets %d/%d, explored %d, window %dx%d" % (
                n_s, len(starts), n_t, len(tgt), len(closed), wx, wy)
            self._fail_ctx = (net, starts, targets, closed, (i0, j0, wx, wy, n_xy), pass_l)
            return None
        path = []
        s = found
        while s != -1:
            L = s // n_xy
            rem = s - L * n_xy
            ci, cj = divmod(rem, wy)
            path.append((L, ci + i0, cj + j0))
            s = parent[s]
        path.reverse()
        # store passability for smoothing
        self._last_pass = (pass_l, i0, j0, wx, wy, n_xy, lane_l)
        return path

    def debug_dump(self, tag):
        """PNG of the owner raster (both layers) around the failed route: white free, grey other nets, red this net's
        copper, green start cells, blue targets, yellow explored cells.  Only if pymupdf is importable."""
        if not hasattr(self, "_fail_ctx") or self._n_dumps >= DEBUG_DUMPS:
            return
        try:
            import pymupdf
        except Exception:
            return
        net, starts, targets, closed, (i0, j0, wx, wy, n_xy), pass_l = self._fail_ctx
        code = self.code_of[net]
        centres = [[(s[1], s[2]) for s in starts], [(t[1], t[2]) for t in list(targets)[:500]]]
        for which, pts in zip(("start", "target"), centres):
            self._dump_one(tag + "_" + which, net, code, pts, starts, targets, closed, (i0, j0, wx, wy, n_xy))
        self._n_dumps += 1
        del self._fail_ctx

    def _dump_one(self, tag, net, code, pts, starts, targets, closed, geo):
        import pymupdf
        (i0, j0, wx, wy, n_xy) = geo
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        R = 120                                   # cells (15 mm)
        a0, b0 = max(0, int(cx) - R), max(0, int(cy) - R)
        a1, b1 = min(self.NX - 1, int(cx) + R), min(self.NY - 1, int(cy) + R)
        w, h = a1 - a0 + 1, b1 - b0 + 1
        img = bytearray(b"\xff" * (w * 2 * h * 3))
        def put(L, i, j, rgb):
            x = (i - a0) + L * w
            y = j - b0
            if 0 <= x < 2 * w and 0 <= y < h:
                o = (y * 2 * w + x) * 3
                img[o:o + 3] = bytes(rgb)
        for L in range(2):
            own = self.own[L]
            for i in range(a0, a1 + 1):
                col = own[i, b0:b1 + 1]
                for k, v in enumerate(col.tolist()):
                    if v == -1:
                        put(L, i, b0 + k, (60, 60, 60))
                    elif v == code:
                        put(L, i, b0 + k, (230, 80, 80))
                    elif v:
                        put(L, i, b0 + k, (170, 170, 170))
        for s in closed:
            L = s // n_xy
            rem = s - L * n_xy
            ci, cj = divmod(rem, wy)
            put(L, ci + i0, cj + j0, (250, 220, 60))
        for (L, ti, tj) in list(targets)[:5000]:
            put(L, ti, tj, (60, 90, 240))
        for (L, si, sj) in starts:
            put(L, si, sj, (30, 190, 30))
        os.makedirs(os.path.join(HW_DIR, ".route_debug"), exist_ok=True)
        ppm = os.path.join(HW_DIR, ".route_debug", "%02d_%s.ppm" % (self._n_dumps, tag))
        with open(ppm, "wb") as fh:
            fh.write(b"P6 %d %d 255\n" % (2 * w, h))
            fh.write(bytes(img))
        pix = pymupdf.Pixmap(ppm)
        pix = pymupdf.Pixmap(pix, 0) if pix.alpha else pix
        png = ppm[:-4] + ".png"
        pymupdf.Pixmap(pix, 3) if False else None
        pix.save(png)
        os.remove(ppm)
        with open(png[:-4] + ".txt", "w") as fh:
            fh.write("%s\nwindow x %.2f..%.2f mm, y %.2f..%.2f mm (left F.Cu, right B.Cu)\n%s\n" % (
                tag, a0 * GRID, a1 * GRID, b0 * GRID, b1 * GRID, getattr(self, "_fail_info", "")))

    # ------------------------------------------------------------------ smoothing
    def passable(self, L, i, j):
        pass_l, i0, j0, wx, wy, n_xy, lane_l = self._last_pass
        if not (i0 <= i < i0 + wx and j0 <= j < j0 + wy):
            return False
        return pass_l[L][(i - i0) * wy + (j - j0)]

    def move_ok(self, L, p, q):
        """lane rule for a unit move p -> q (both inside the last A* window)"""
        pass_l, i0, j0, wx, wy, n_xy, lane_l = self._last_pass
        lf = 0
        for (i, j) in (p, q):
            if i0 <= i < i0 + wx and j0 <= j < j0 + wy:
                lf = lf or lane_l[L][(i - i0) * wy + (j - j0)]
        di, dj = q[0] - p[0], q[1] - p[1]
        return not (lf and ((lf == 1 and di) or (lf == 2 and dj)))

    def smooth_run(self, L, pts):
        """pts: list of (i, j) on one layer.  Regroup 2-direction windows and chamfer 90 deg corners."""
        if len(pts) < 3:
            return pts
        moves = [(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]) for k in range(len(pts) - 1)]

        def walk(start, seq):
            out = [start]
            p = start
            for (di, dj) in seq:
                p = (p[0] + di, p[1] + dj)
                out.append(p)
            return out

        def ok_seq(start, seq):
            p = start
            for (di, dj) in seq:
                q = (p[0] + di, p[1] + dj)
                if not self.passable(L, q[0], q[1]) or not self.move_ok(L, p, q):
                    return False
                if di and dj and (not self.passable(L, p[0] + di, p[1]) or not self.passable(L, p[0], p[1] + dj)):
                    return False
                p = q
            return True

        def adjacent(a, b):
            # a orthogonal, b diagonal sharing a component (or same)
            if a == b:
                return True
            if (a[0] and a[1]) == (b[0] and b[1]):
                return False
            o, d = (a, b) if not (a[0] and a[1]) else (b, a)
            return (o[0] and o[0] == d[0]) or (o[1] and o[1] == d[1])

        # pass 1: regroup windows of <= 2 adjacent directions into 2 straight segments
        new = []
        k = 0
        n = len(moves)
        while k < n:
            dirs = [moves[k]]
            e = k + 1
            while e < n:
                m = moves[e]
                if m in dirs:
                    e += 1
                    continue
                if len(dirs) == 1 and adjacent(dirs[0], m):
                    dirs.append(m)
                    e += 1
                    continue
                break
            window = moves[k:e]
            if len(dirs) == 2 and len(window) > 2:
                a, b = dirs
                ca, cb = window.count(a), window.count(b)
                start = pts[k]
                cands = [[a] * ca + [b] * cb, [b] * cb + [a] * ca]
                chosen = None
                for seq in cands:
                    if ok_seq(start, seq):
                        chosen = seq
                        break
                if chosen is None:
                    # try splitting: diagonal first up to t, then orth, then rest diagonal (keeps corners in free space)
                    d_, o_ = (a, b) if (a[0] and a[1]) else (b, a)
                    cd, co = window.count(d_), window.count(o_)
                    for t in range(cd - 1, 0, -1):
                        seq = [d_] * t + [o_] * co + [d_] * (cd - t)
                        if ok_seq(start, seq):
                            chosen = seq
                            break
                new.extend(chosen if chosen else window)
            else:
                new.extend(window)
            k = e
        moves = new
        # pass 2: chamfer 90 deg corners (orth A then orth B -> replace k of each by k diagonals)
        changed = True
        it = 0
        while changed and it < 6:
            changed = False
            it += 1
            # split into runs
            runs = []
            for m in moves:
                if runs and runs[-1][0] == m:
                    runs[-1][1] += 1
                else:
                    runs.append([m, 1])
            out = []
            idx = 0
            pos = pts[0]
            k = 0
            while k < len(runs):
                if k + 1 < len(runs):
                    a, na = runs[k]
                    b, nb = runs[k + 1]
                    if not (a[0] and a[1]) and not (b[0] and b[1]) and a != b and (a[0] + b[0], a[1] + b[1]) != (0, 0):
                        d = (a[0] + b[0], a[1] + b[1])
                        best = 0
                        for t in range(min(na, nb), 0, -1):
                            seq = [a] * (na - t) + [d] * t + [b] * (nb - t)
                            if ok_seq(pos, seq):
                                best = t
                                break
                        if best:
                            seq = [a] * (na - best) + [d] * best + [b] * (nb - best)
                            out.extend(seq)
                            for (di, dj) in seq:
                                pos = (pos[0] + di, pos[1] + dj)
                            k += 2
                            changed = True
                            continue
                a, na = runs[k]
                out.extend([a] * na)
                for _ in range(na):
                    pos = (pos[0] + a[0], pos[1] + a[1])
                k += 1
            moves = out
        return walk(pts[0], moves)

    # ------------------------------------------------------------------ path -> tracks + marking
    def commit_path(self, path, net, cls, width, clr, pad_centres):
        code = self.code_of[net]
        # split into layer runs
        runs = []
        for (L, i, j) in path:
            if runs and runs[-1][0] == L:
                runs[-1][1].append((i, j))
            else:
                runs.append([L, [(i, j)]])
        all_cells = []
        for k, (L, pts) in enumerate(runs):
            pts = self.smooth_run(L, pts) if len(pts) > 2 else pts
            runs[k][1] = pts
            # segment emission with neck widths
            def wid(pt):
                if width <= NECK_W + 1e-9:
                    return width
                x, y = self.xy(*pt)
                for (px, py) in pad_centres:
                    if (x - px) ** 2 + (y - py) ** 2 <= NECK * NECK:
                        return NECK_W
                return width
            wpts = [wid(pt) for pt in pts]
            segs = []      # (start, end, dir, width)
            for k in range(len(pts) - 1):
                a, b = pts[k], pts[k + 1]
                d = (b[0] - a[0], b[1] - a[1])
                w_ = min(wpts[k], wpts[k + 1])
                if segs and segs[-1][2] == d and segs[-1][3] == w_:
                    segs[-1] = (segs[-1][0], b, d, w_)
                else:
                    segs.append((a, b, d, w_))
            for (a, b, d, w_) in segs:
                self.emit(a[0] * NM, a[1] * NM, b[0] * NM, b[1] * NM, w_, L, net)
            # mark
            for (i, j) in pts:
                self.mark_track_cell(L, i, j, width / 2, clr, net, code)
                all_cells.append((L, i, j))
                if self._emit_kind == "route":
                    self.route_owner[L][i, j] = code
            if cls == "ISO_IN":
                for (i, j) in pts:
                    self.mark_rect(None, i * GRID, j * GRID, width / 2, width / 2, ISO_CLR + MARGIN + HALF_DEF, 0, mask=self.iso_mask)
            self.stats["tracks"] += 1
        # vias at layer changes
        for k in range(len(runs) - 1):
            i, j = runs[k][1][-1]
            self.add_via(i, j, net, code)
        self.tree_cells.setdefault(net, set()).update(all_cells)
        return all_cells

    def add_via(self, i, j, net, code):
        self.vias.append((i * NM, j * NM, net, self._emit_kind))
        self._mark_via(i, j, net, code)

    def _mark_via(self, i, j, net, code):
        for L in range(2):
            self.mark_track_cell(L, i, j, VIA_D / 2, 0.2, net, code)
            if self._emit_kind == "route":
                for di, dj in disk_offsets(2):
                    if self.inb(i + di, j + dj):
                        self.route_owner[L][i + di, j + dj] = code
        # keep other vias 0.5 mm hole to hole away
        r = int(math.ceil((VIA_DRILL + 0.5 + 0.07) / GRID))
        ii, jj = np.ogrid[max(0, i - r):min(self.NX, i + r + 1), max(0, j - r):min(self.NY, j + r + 1)]
        m = (ii - i) ** 2 + (jj - j) ** 2 <= ((VIA_DRILL + 0.5 + 0.07) / GRID) ** 2
        self.via_ok[max(0, i - r):min(self.NX, i + r + 1), max(0, j - r):min(self.NY, j + r + 1)] &= ~m
        self.stats["vias"] += 1
        self.tree_cells.setdefault(net, set()).update({(0, i, j), (1, i, j)})
        if net == "AGND":
            self.agnd_vias.add((i, j))

    # ------------------------------------------------------------------ pad access points
    def pad_start(self, p):
        """(cells, layers) where routing for this pad begins"""
        if id(p) in self.stitched_pads:
            st = self.stitch[self.stitched_pads[id(p)]]
            return [(st["layer"],) + tuple(e) for e in st["ends"]], [st["layer"]]
        if id(p) in self.escape:
            g, layer, corridor = self.escape[id(p)]
            return [(layer,) + tuple(g)], [layer]
        layers = self.pad_layers(p)
        cells = self.pad_cells(p)
        c = self.cell(p.x, p.y)
        out = [(L,) + c for L in layers] + [(L,) + q for L in layers for q in cells if q != c]
        return out, layers

    def pad_entry_segments(self, p, net):
        """for pads without a stub: connect the exact pad centre to its grid cell (inside the copper)"""
        if id(p) in self.escape:
            return
        c = self.cell(p.x, p.y)
        pnm = (self.nm(p.x), self.nm(p.y))
        gnm = (c[0] * NM, c[1] * NM)
        if pnm == gnm:
            return
        L = self.pad_layers(p)[0]
        self.connect_nm(pnm, gnm, 0.25, L, net)

    # ------------------------------------------------------------------ GND
    def route_gnd(self):
        net = "GND"
        code = self.code_of.get(net)
        if code is None:
            return
        pads = [p for p in self.pads_by_net.get(net, []) if p.kind == "smd"]
        rv = VIA_CHECK_CELLS
        seen_groups = set()
        for p in pads:
            if id(p) in self.stitched_pads:
                key = self.stitched_pads[id(p)]
                if key in seen_groups:
                    continue
                seen_groups.add(key)
                if self.connect_stitch_via(key, code, rv, net):
                    continue
            starts, layers = self.pad_start(p)
            L = layers[0]
            (s0L, si, sj) = starts[0]     # stub end or pad centre cell
            d = self.outward(p) if id(p) in self.escape else None
            placed = False
            cand = []
            if d is not None:
                for k in range(CORRIDOR + BAND + 2, CORRIDOR + BAND + 40):     # beyond the fan-out band
                    cand.append((si + d[0] * k, sj + d[1] * k))
            else:
                f = self.fp_of_pad[id(p)]
                dx, dy = p.x - f.x, p.y - f.y
                nrm = math.hypot(dx, dy) or 1.0
                ux, uy = dx / nrm, dy / nrm
                for dist in (0.9, 1.1, 1.3, 1.6, 2.0, 2.5):
                    for ang in (0, 45, -45, 90, -90, 135, -135, 180):
                        a = math.radians(ang)
                        vx = ux * math.cos(a) - uy * math.sin(a)
                        vy = ux * math.sin(a) + uy * math.cos(a)
                        cand.append(self.cell(p.x + vx * dist, p.y + vy * dist))
            for (ci, cj) in cand:
                if not self.inb(ci, cj) or not self.via_ok[ci, cj]:
                    continue
                if not self.via_spot_free(ci, cj, code, rv):
                    continue
                # straight connection from the start cell (axial for stubs; jog+axis otherwise)
                cells = self.jog_cells((si, sj), (ci, cj))
                if any(not self.cell_free(L, i, j, code) for (i, j) in cells):
                    continue
                self.pad_entry_segments(p, net)
                self.connect_nm((si * NM, sj * NM), (ci * NM, cj * NM), 0.25, L, net)
                for (i, j) in cells:
                    self.mark_track_cell(L, i, j, 0.125, 0.2, net, code)
                self.add_via(ci, cj, net, code)
                self.stats["gnd_vias"] += 1
                placed = True
                break
            if not placed:
                # route to the nearest GND copper (a via placed on the way connects to the planes as well)
                targets = set(self.tree_cells.get(net, set()))
                s_xy = [(si, sj)]
                path = None
                for margin in (6.0, 20.0):
                    win = self.window_for(s_xy, [(t[1], t[2]) for t in list(targets)[:3000]], margin)
                    path = self.astar(net, "Default", starts, targets, [0, 1], 0.25, 0.2, [(p.x, p.y)], win, allow_via=True)
                    if path is not None:
                        break
                if path is None:
                    self.stats["failed"].append(("GND via", self.fp_of_pad[id(p)].ref, p.number, getattr(self, "_fail_info", "")))
                else:
                    self.pad_entry_segments(p, net)
                    self.commit_path(path, net, "Default", 0.25, 0.2, [(p.x, p.y)])

    def connect_stitch_via(self, key, code, rv, net, need_b_open=None):
        """via at the end of a ground stitch, searched outward along the pin row from either end"""
        st = self.stitch[key]
        L = st["layer"]
        ax = st["axis"]
        for k_end, (ei, ej) in enumerate(st["ends"]):
            sgn = -1 if k_end == 0 else 1
            for k in range(0, 40):
                ci, cj = ei + ax[0] * sgn * k, ej + ax[1] * sgn * k
                if not self.inb(ci, cj) or not self.via_ok[ci, cj]:
                    continue
                if need_b_open is not None and (ci, cj) not in need_b_open:
                    continue
                if not self.via_spot_free(ci, cj, code, rv):
                    continue
                cells = self.jog_cells((ei, ej), (ci, cj))
                if any(not self.cell_free(L, i, j, code) for (i, j) in cells):
                    continue
                self.connect_nm((ei * NM, ej * NM), (ci * NM, cj * NM), st["w"], L, net)
                for (i, j) in cells:
                    self.mark_track_cell(L, i, j, st["w"] / 2, 0.2, net, code)
                self.add_via(ci, cj, net, code)
                self.stats["gnd_vias"] += 1
                return True
        return False

    def via_spot_free(self, i, j, code, rv):
        r = int(math.ceil(rv))
        for L in range(2):
            own = self.own[L]
            for di in range(-r, r + 1):
                for dj in range(-r, r + 1):
                    if di * di + dj * dj > rv * rv + 1e-9:
                        continue
                    ii, jj = i + di, j + dj
                    if not self.inb(ii, jj):
                        return False
                    v = own[ii, jj]
                    if v != 0 and v != code:
                        return False
                    if self.iso_mask[ii, jj] and netclass_code_is_not_iso(code):
                        return False
        return True

    def cell_free(self, L, i, j, code):
        if not self.inb(i, j):
            return False
        v = self.own[L][i, j]
        return v == 0 or v == code

    # ------------------------------------------------------------------ AGND
    def open_pour_cells(self, poly, r_open=0.6, layer=0):
        """cells of one layer inside poly where a disk of radius r_open is free (the pour surely fills there)"""
        i0, j0 = self.cell(min(x for x, _ in poly), min(y for _, y in poly))
        i1, j1 = self.cell(max(x for x, _ in poly), max(y for _, y in poly))
        code = self.code_of["AGND"]
        own = self.own[layer][i0:i1 + 1, j0:j1 + 1]
        blk = (own != 0) & (own != code)
        blk |= self.iso_mask[i0:i1 + 1, j0:j1 + 1]
        blk = self.dilate(blk, r_open / GRID)
        # polygon mask
        xs = np.arange(i0, i1 + 1) * GRID
        ys = np.arange(j0, j1 + 1) * GRID
        inpoly = np.zeros_like(blk)
        for a, y in enumerate(ys):
            # scanline
            xsect = []
            n = len(poly)
            for k in range(n):
                x1, y1 = poly[k]
                x2, y2 = poly[(k + 1) % n]
                if (y1 > y) != (y2 > y):
                    xsect.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
            xsect.sort()
            for k in range(0, len(xsect) - 1, 2):
                inpoly[:, a] |= (xs >= xsect[k] + 0.6) & (xs <= xsect[k + 1] - 0.6)
        ok = inpoly & ~blk
        cells = set()
        for a, b in zip(*np.nonzero(ok)):
            cells.add((layer, int(a) + i0, int(b) + j0))
        return cells

    def route_agnd(self):
        net = "AGND"
        if net not in self.code_of:
            return
        code = self.code_of[net]
        pads = self.pads_by_net.get(net, [])
        cls = "POWER"
        width, clr = 0.4, 0.2
        pad_centres = [(p.x, p.y) for p in pads]
        anchors = self.open_pour_cells(self.agnd_poly, 0.6, 0) | self.open_pour_cells(self.agnd_poly, 0.45, 1)
        b_open = set((i, j) for (L, i, j) in anchors if L == 1)
        self.log("AGND anchors: %d" % len(anchors))
        n_via = 0
        seen_groups = set()
        for p in pads:
            if p.kind != "smd" and point_in_poly(p.x, p.y, self.agnd_poly):
                continue                       # THT pad inside the pour: the fill reaches it
            if id(p) in self.stitched_pads:
                key = self.stitched_pads[id(p)]
                if key in seen_groups:
                    continue
                seen_groups.add(key)
                if self.connect_stitch_via(key, code, VIA_CHECK_CELLS, net, need_b_open=b_open):
                    n_via += 1
                    continue
            starts, layers = self.pad_start(p)
            # already open on F?
            if any(s in anchors for s in starts):
                self.pad_entry_segments(p, net)
                continue
            (L, si, sj) = starts[0]
            # 1) a via straight to the B.Cu pour
            d = self.outward(p) if id(p) in self.escape else None
            cand = []
            if d is not None:
                cand = [(si + d[0] * k, sj + d[1] * k) for k in range(CORRIDOR + BAND + 2, CORRIDOR + BAND + 40)]
            else:
                f = self.fp_of_pad[id(p)]
                dx, dy = p.x - f.x, p.y - f.y
                nrm = math.hypot(dx, dy) or 1.0
                ux, uy = dx / nrm, dy / nrm
                for dist in (0.9, 1.1, 1.3, 1.6, 2.0, 2.5):
                    for ang in (0, 45, -45, 90, -90, 135, -135, 180):
                        a = math.radians(ang)
                        cand.append(self.cell(p.x + (ux * math.cos(a) - uy * math.sin(a)) * dist, p.y + (ux * math.sin(a) + uy * math.cos(a)) * dist))
            placed = False
            rejects = dict(b_open=0, via_ok=0, spot=0, path=0)
            for (ci, cj) in cand:
                if not self.inb(ci, cj) or (ci, cj) not in b_open:
                    rejects["b_open"] += 1
                    continue
                if not self.via_ok[ci, cj]:
                    rejects["via_ok"] += 1
                    continue
                if not self.via_spot_free(ci, cj, code, VIA_CHECK_CELLS):
                    rejects["spot"] += 1
                    continue
                cells = self.jog_cells((si, sj), (ci, cj))
                if any(not self.cell_free(L, i, j, code) for (i, j) in cells):
                    rejects["path"] += 1
                    continue
                self.pad_entry_segments(p, net)
                self.connect_nm((si * NM, sj * NM), (ci * NM, cj * NM), NECK_W, L, net)
                for (i, j) in cells:
                    self.mark_track_cell(L, i, j, NECK_W / 2, 0.2, net, code)
                self.add_via(ci, cj, net, code)
                self.agnd_vias.add((ci, cj))
                n_via += 1
                placed = True
                rr2 = ((0.45 + 0.3 + 0.2) / GRID) ** 2
                for a in [a for a in anchors if (a[1] - ci) ** 2 + (a[2] - cj) ** 2 <= rr2]:
                    anchors.discard(a)
                    b_open.discard((a[1], a[2]))
                break
            if placed:
                continue
            # 2) route to any open pour cell (F or B)
            path = None
            for margin in (6.0, 30.0):
                win = self.window_for([(si, sj)], [(a[1], a[2]) for a in anchors], margin)
                path = self.astar(net, "POWER", starts, anchors, [0, 1], width, clr, pad_centres, win, allow_via=True)
                if path is not None:
                    break
            if path is None:
                self.stats["failed"].append(("AGND", self.fp_of_pad[id(p)].ref, p.number, getattr(self, "_fail_info", ""), "via rejects: %s" % rejects))
                self.debug_dump("AGND_%s_%s" % (self.fp_of_pad[id(p)].ref, p.number))
                continue
            self.pad_entry_segments(p, net)
            cells = self.commit_path(path, net, cls, width, clr, pad_centres)
            for (L2, i, j) in cells:
                if (0, i, j) in cells and (1, i, j) in cells:
                    self.agnd_vias.add((i, j))
            rr = (0.6 + width / 2 + 0.2) / GRID
            rr2 = rr * rr
            for (L, i, j) in cells:
                for a in [a for a in anchors if a[0] == L and (a[1] - i) ** 2 + (a[2] - j) ** 2 <= rr2]:
                    anchors.discard(a)
                    b_open.discard((a[1], a[2]))
        self.log("AGND: %d pads via to B pour" % n_via)

    def window_for(self, a_pts, b_pts, margin_mm):
        pts = list(a_pts) + list(b_pts)
        m = int(margin_mm / GRID)
        i0 = max(0, min(p[0] for p in pts) - m)
        j0 = max(0, min(p[1] for p in pts) - m)
        i1 = min(self.NX - 1, max(p[0] for p in pts) + m)
        j1 = min(self.NY - 1, max(p[1] for p in pts) + m)
        return (i0, j0, i1, j1)

    # ------------------------------------------------------------------ signal nets
    def route_net(self, net):
        pads = self.pads_by_net.get(net, [])
        if len(pads) < 2:
            return True
        cls = netclass(net)
        width, clr = CLASS_WIDTH[cls], CLASS_CLR[cls]
        layers_allowed = [0] if cls in F_ONLY else [0, 1]
        pad_centres = [(p.x, p.y) for p in pads]
        # order: start at the pad closest to the centroid, then nearest-neighbour
        cx = sum(p.x for p in pads) / len(pads)
        cy = sum(p.y for p in pads) / len(pads)
        remaining = sorted(pads, key=lambda p: (p.x - cx) ** 2 + (p.y - cy) ** 2)
        first = remaining.pop(0)
        entry_done = False
        connected = [first]
        tree = set(self.pad_start(first)[0])
        ok_all = True
        while remaining:
            # nearest remaining pad to the tree
            best = None
            for p in remaining:
                d = min(math.hypot(p.x - q.x, p.y - q.y) for q in connected)
                if best is None or d < best[0]:
                    best = (d, p)
            p = best[1]
            remaining.remove(p)
            starts, layers = self.pad_start(p)
            targets = set(t for t in tree if t[0] in layers_allowed)
            if not targets:
                targets = tree
            s_xy = [(s[1], s[2]) for s in starts]
            t_xy = [(t[1], t[2]) for t in targets]
            path = None
            for margin in (8.0, 25.0, 200.0):
                win = self.window_for(s_xy, t_xy, margin)
                path = self.astar(net, cls, starts, targets, layers_allowed, width, clr, pad_centres, win,
                                  allow_via=(len(layers_allowed) > 1))
                if path is not None:
                    break
            if path is None and cls in F_ONLY:
                win = self.window_for(s_xy, t_xy, 200.0)
                path = self.astar(net, cls, starts, targets, [0, 1], width, clr, pad_centres, win, allow_via=True)
                if path is not None:
                    self.log("  %s: needed B.Cu" % net)
            if path is None and self._emit_kind == "route":
                blockers = self.find_blockers(net, starts, targets)
                if blockers and self.rebuilds < self.RIP_BUDGET:
                    self.log("  rip-up for %s at %s.%s: %s" % (net, self.fp_of_pad[id(p)].ref, p.number, sorted(blockers)))
                    self.ripup(blockers)
                    win = self.window_for(s_xy, t_xy, 60.0)
                    path = self.astar(net, cls, starts, targets, layers_allowed, width, clr, pad_centres, win,
                                      allow_via=(len(layers_allowed) > 1))
            if path is None:
                self.stats["failed"].append(("net", net, self.fp_of_pad[id(p)].ref, p.number, getattr(self, "_fail_info", "")))
                self.debug_dump("%s_%s_%s" % (net.replace("/", "_").replace("(", "").replace(")", ""), self.fp_of_pad[id(p)].ref, p.number))
                ok_all = False
                continue
            if not entry_done:
                self.pad_entry_segments(first, net)
                entry_done = True
            self.pad_entry_segments(p, net)
            cells = self.commit_path(path, net, cls, width, clr, pad_centres)
            tree.update(cells)
            connected.append(p)
            tree.update(self.pad_start(p)[0])
        return ok_all

    def find_blockers(self, net, starts, targets):
        """routed nets whose copper lies within RIP_R cells of the blocked start or target cells"""
        code = self.code_of[net]
        names = {c: n for n, c in self.code_of.items()}
        found = set()
        pts = list(starts) + list(targets)[:40]
        R = self.RIP_R
        for (L, i, j) in pts:
            i0, i1 = max(0, i - R), min(self.NX - 1, i + R)
            j0, j1 = max(0, j - R), min(self.NY - 1, j + R)
            for LL in range(2):
                sub = self.route_owner[LL][i0:i1 + 1, j0:j1 + 1]
                for c in np.unique(sub):
                    c = int(c)
                    if c and c != code:
                        n = names.get(c)
                        if n and n not in ("GND", "AGND") and self.ripped_count.get(n, 0) < 3:
                            found.add(n)
        return found

    def ripup(self, nets):
        """remove the routed copper of the given nets and rebuild the raster; queue them for re-routing"""
        nets = set(nets)
        self.segments = [s for s in self.segments if not (s[7] == "route" and s[6] in nets)]
        self.vias = [v for v in self.vias if not (v[3] == "route" and v[2] in nets)]
        for n in nets:
            self.ripped_count[n] = self.ripped_count.get(n, 0) + 1
            if n not in self.reroute_queue:
                self.reroute_queue.append(n)
        self.rebuild_raster()

    def process_reroutes(self):
        while self.reroute_queue:
            n = self.reroute_queue.pop(0)
            # drop stale failure records of this net; it gets a fresh attempt
            self.stats["failed"] = [f for f in self.stats["failed"] if not (f[0] == "net" and f[1] == n)]
            t1 = time.time()
            ok = self.route_net(n)
            self.log("  %-9s %-34s %s %.1fs (re-route after rip-up)" % (netclass(n), n[:34], "ok" if ok else "FAIL", time.time() - t1))

    def rebuild_raster(self):
        """re-mark every raster from the recorded copper (pads, stubs, kept routes, vias)"""
        t0 = time.time()
        self.rebuilds += 1
        for arrs in self.rasters.values():
            for a in arrs:
                a[:] = 0
        for a in self.route_owner:
            a[:] = 0
        self.iso_mask[:] = False
        self.noniso_mask[:] = False
        self.via_ok[:] = True
        self.agnd_vias = set()
        self.tree_cells = {}
        self.pads_by_net = {}
        self._init_raster()
        # corridors and stitches keep their ownership
        for key, (g, layer, corridor) in self.escape.items():
            code = None
            for pad_id, pad in ((id(pp), pp) for f in self.board.footprints for pp in f.pads):
                pass
        for f in self.board.footprints:
            for p in f.pads:
                if id(p) in self.escape:
                    g, layer, corridor = self.escape[id(p)]
                    code = self.code_of[p.net]
                    for arrs in self.rasters.values():
                        for c in corridor:
                            arrs[layer][c] = code
                    self.tree_cells.setdefault(p.net, set()).update((layer,) + c for c in corridor)
        for key, st in self.stitch.items():
            self.tree_cells.setdefault(key[1], set()).update((st["layer"],) + c for c in st.get("cells", []))
        # copper: stubs first (their halos may not overwrite reserved corridor cells: mark_disk honours reserved_arr)
        saved_kind = self._emit_kind
        for kind in ("stub", "route"):
            self._emit_kind = kind
            for (x1, y1, x2, y2, w, L, net, k) in self.segments:
                if k != kind:
                    continue
                code = self.code_of[net]
                cls = netclass(net)
                cells = self.line_cells((x1, y1), (x2, y2))
                for (i, j) in cells:
                    if self.inb(i, j):
                        self.mark_track_cell(L, i, j, w / 2, CLASS_CLR[cls], net, code)
                        if kind == "route":
                            self.route_owner[L][i, j] = code
                self.tree_cells.setdefault(net, set()).update((L, i, j) for (i, j) in cells if self.inb(i, j))
                if cls == "ISO_IN":
                    for (i, j) in cells:
                        self.mark_rect(None, i * GRID, j * GRID, w / 2, w / 2, ISO_CLR + MARGIN + HALF_DEF, 0, mask=self.iso_mask)
            for (x, y, net, k) in self.vias:
                if k != kind:
                    continue
                i, j = int(round(x / NM)), int(round(y / NM))
                self._mark_via(i, j, net, self.code_of[net])
                self.tree_cells.setdefault(net, set()).update({(0, i, j), (1, i, j)})
                if net == "AGND":
                    self.agnd_vias.add((i, j))
        self._emit_kind = saved_kind
        self.log("  raster rebuilt (%d) in %.1fs" % (self.rebuilds, time.time() - t0))

    def route_all(self, priority=None):
        t0 = time.time()
        skip0 = ("GND", "AGND") if self.plane_gnd else ("AGND",)
        self.priority = [n for n in (priority or []) if n in self.pads_by_net and len(self.pads_by_net[n]) >= 2 and n not in skip0]
        self.make_stubs()
        if self.plane_gnd:
            self.route_gnd()
            self.log("GND vias: %d  (%.1fs)" % (self.stats["gnd_vias"], time.time() - t0))
        skip = ("GND", "AGND") if self.plane_gnd else ("AGND",)
        names = [n for n in self.pads_by_net if n not in skip and len(self.pads_by_net[n]) >= 2]
        self._emit_kind = "route"

        def extent(n):
            ps = self.pads_by_net[n]
            return (max(p.x for p in ps) - min(p.x for p in ps)) + (max(p.y for p in ps) - min(p.y for p in ps))
        done = set()
        for n in self.priority:                       # nets that failed in the previous pass go first
            t1 = time.time()
            ok = self.route_net(n)
            done.add(n)
            self.log("  %-9s %-34s %s %.1fs (priority)" % (netclass(n), n[:34], "ok" if ok else "FAIL", time.time() - t1))
            self.process_reroutes()
        for cls in ORDER:
            group = sorted([n for n in names if netclass(n) == cls and n not in done], key=extent)
            for n in group:
                t1 = time.time()
                ok = self.route_net(n)
                self.log("  %-9s %-34s %s %.1fs" % (cls, n[:34], "ok" if ok else "FAIL", time.time() - t1))
                self.process_reroutes()
        self._emit_kind = "stub"                      # AGND anchors / bridges are never ripped
        t2 = time.time()
        self.route_agnd()
        self.log("AGND pads done (%.1fs)" % (time.time() - t2))
        t2 = time.time()
        self.bridge_agnd()
        self.log("AGND bridging done (%.1fs)" % (time.time() - t2))
        self.flush()
        self.log("router: %d segments, %d vias, %d failures, %.0fs" % (len(self.segments), len(self.vias), len(self.stats["failed"]), time.time() - t0))
        for f in self.stats["failed"]:
            self.log("   FAILED %s" % (f,))

    # ------------------------------------------------------------------ AGND pour connectivity
    def bridge_agnd(self):
        """connect pour fragments that carry AGND copper (tracks/pads) to the fragment holding NT1"""
        if "AGND" not in self.code_of:
            return
        code = self.code_of["AGND"]
        cells = self.open_pour_cells(self.agnd_poly, 0.12, 0) | self.open_pour_cells(self.agnd_poly, 0.12, 1)
        # AGND copper (tracks, pads, vias) joins the pour it touches; vias join the two layers
        agnd_cells = set(self.tree_cells.get("AGND", set()))
        allc = cells | agnd_cells
        comp = {}
        comps = []
        near = [(0, 0)] + DIRS + [(2, 0), (-2, 0), (0, 2), (0, -2), (3, 0), (-3, 0), (0, 3), (0, -3)]
        for c in allc:
            if c in comp:
                continue
            k = len(comps)
            stack = [c]
            comp[c] = k
            members = [c]
            while stack:
                L, i, j = stack.pop()
                nbrs = [(L, i + di, j + dj) for di, dj in (near if (L, i, j) in agnd_cells else DIRS)]
                if (i, j) in self.agnd_vias:
                    nbrs.append((1 - L, i, j))
                for n in nbrs:
                    if n in allc and n not in comp:
                        comp[n] = k
                        stack.append(n)
                        members.append(n)
            comps.append(members)
        touch = {}
        for c in agnd_cells:
            touch.setdefault(comp[c], set()).add(c)
        if not touch:
            return
        # main component: the one holding NT1's AGND pad
        nt = [p for p in self.pads_by_net.get("AGND", []) if self.fp_of_pad[id(p)].ref == "NT1"]
        main = None
        if nt:
            ci, cj = self.cell(nt[0].x, nt[0].y)
            main = comp.get((0, ci, cj), comp.get((1, ci, cj)))
        if main is None:
            main = max(touch, key=lambda k: len(comps[k]))
        merged = {main}
        others = [k for k in touch if k != main]
        others.sort(key=lambda k: -len(comps[k]))
        n_bridge = 0
        for k in others:
            if k in merged:
                continue
            pour_k = [c for c in comps[k] if c in cells]
            starts = (pour_k or comps[k])[::max(1, len(comps[k]) // 300)]
            targets = set()
            for m in merged:
                targets.update(comps[m])
            s_xy = [(s[1], s[2]) for s in starts]
            t_xy = [(t[1], t[2]) for t in list(targets)[:2000]]
            path = None
            for margin in (10.0, 40.0, 200.0):
                win = self.window_for(s_xy, t_xy, margin)
                path = self.astar("AGND", "POWER", starts, targets, [0, 1], 0.3, 0.2, [], win, allow_via=True)
                if path is not None:
                    break
            if path is None:
                self.stats["failed"].append(("AGND bridge", "component", k, len(comps[k]), getattr(self, "_fail_info", "")))
                continue
            newc = self.commit_path(path, "AGND", "POWER", 0.3, 0.2, [])
            merged.add(k)
            for c in newc:
                if c in comp:
                    merged.add(comp[c])
            n_bridge += 1
        self.log("AGND bridges: %d (components with AGND copper: %d)" % (n_bridge, len(touch)))

    # ------------------------------------------------------------------ output
    def flush(self):
        b = self.board
        for (x1, y1, x2, y2, w, L, net, kind) in self.segments:
            b.track(x1 / 1e6, y1 / 1e6, x2 / 1e6, y2 / 1e6, w, LAYERS[L], net)
        for (x, y, net, kind) in self.vias:
            b.via(x / 1e6, y / 1e6, net, VIA_D, VIA_DRILL)


def netclass_code_is_not_iso(code):
    return True


def route_board(board, comps, nets, pad_net, W, H, agnd_poly, iso_keepout, log=print, stub_hint=None, plane_gnd=True,
                layer_hint=None, priority_file=None, layer_hint_net=None):
    r = Router(board, comps, nets, pad_net, W, H, agnd_poly, iso_keepout, log=log, stub_hint=stub_hint, plane_gnd=plane_gnd,
               layer_hint=layer_hint, layer_hint_net=layer_hint_net)
    prio = []
    if priority_file and os.path.exists(priority_file):
        import json
        prio = json.load(open(priority_file, encoding="utf-8"))
    r.route_all(priority=prio)
    if priority_file:
        import json
        failed_nets = []
        for f in r.stats["failed"]:
            if f[0] == "net" and f[1] not in failed_nets:
                failed_nets.append(f[1])
        new = failed_nets + [n for n in prio if n not in failed_nets]
        json.dump(new, open(priority_file, "w", encoding="utf-8"), indent=1)
        r.log("priority file: %d failed nets recorded (%d total)" % (len(failed_nets), len(new)))
    return r
