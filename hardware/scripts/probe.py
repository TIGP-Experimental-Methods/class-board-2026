"""Probe the router raster around a pad's escape point.  Usage: python probe.py <ref> <pad> [panel]"""
import sys
sys.path.insert(0, ".")
import router
from router import GRID
ref, pad = sys.argv[1], sys.argv[2]
if len(sys.argv) > 3 and sys.argv[3] == "panel":
    import gen_panel
    board, comps, nets, pad_net = gen_panel.build(route=False)
    W, H = gen_panel.W, gen_panel.H
    r = router.Router(board, comps, nets, pad_net, W, H, [(0.5, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (0.5, H - 0.5)], ((500.0, 500.0), (501.0, 501.0)), plane_gnd=False)
else:
    import gen_pcb
    board, comps, nets = gen_pcb.build(route=False)
    pad_net = {}
    r = router.Router(board, comps, nets, pad_net, gen_pcb.W, gen_pcb.H, gen_pcb.AGND_POLY, gen_pcb.ISO_KEEPOUT, stub_hint={"J1": (0, 1), "J2": (0, -1), "J6": (0, -1)})
if "route" in sys.argv:
    r.log = lambda *a: None
    r.route_all()
else:
    r.make_stubs()
p = r.pad_of[(ref, pad)]
code = r.code_of[p.net]
print("pad", ref, pad, "net", p.net, "code", code, "at", p.x, p.y, "kind", p.kind, "layers", p.layers)
esc = r.escape.get(id(p))
print("escape:", esc)
starts, layers = r.pad_start(p)
print("starts:", starts[:4], layers)
(L, gi, gj) = starts[0]
for lvl, arrs in sorted(r.rasters.items()):
    for LL in range(2):
        own = arrs[LL]
        print("raster %.1f layer %d around (%.3f, %.3f):" % (lvl, LL, gi * GRID, gj * GRID))
        for j in range(gj - 6, gj + 7):
            row = []
            for i in range(gi - 8, gi + 9):
                v = own[i, j] if r.inb(i, j) else -9
                row.append("." if v == 0 else ("#" if v == -1 else ("O" if v == code else "x")))
            print("   %7.3f %s" % (j * GRID, " ".join(row)))
print("iso_mask at G:", r.iso_mask[gi, gj], "noniso_mask:", r.noniso_mask[gi, gj], "reserved:", r.reserved_arr[gi, gj])
# owner codes of the row just beyond the corridor end (band start)
names = {c: n for n, c in r.code_of.items()}
own = r.own[L]
step = (corridor_d := (esc[2][1][0] - esc[2][0][0], esc[2][1][1] - esc[2][0][1])) if esc else (0, -1)
for k in (5, 6, 7, 8):
    ci, cj = gi + step[0] * k, gj + step[1] * k
    row = [own[ci + (t if step[1] else 0), cj + (t if step[0] else 0)] for t in range(-8, 9)]
    print("k=%d (%.3f,%.3f):" % (k, ci * GRID, cj * GRID), [names.get(int(v), int(v)) if v > 0 else int(v) for v in row])
print("--- column beyond G: via_ok / own F / own B / lane / lane_group")
for k in range(0, 14):
    ci, cj = gi + step[0] * k, gj + step[1] * k
    print("k=%2d (%.3f,%.3f) via_ok=%s ownF=%s ownB=%s lane=%d grp=%d" % (k, ci*GRID, cj*GRID, r.via_ok[ci,cj], names.get(int(r.own[0][ci,cj]), int(r.own[0][ci,cj])), names.get(int(r.own[1][ci,cj]), int(r.own[1][ci,cj])), r.lane[0][ci,cj], r.lane_group[0][ci,cj]))
