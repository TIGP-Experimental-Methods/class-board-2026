import sys
sys.path.insert(0, ".")
import router, gen_panel
board, comps, nets, pad_net = gen_panel.build(route=False)
W, H = gen_panel.W, gen_panel.H
r = router.Router(board, comps, nets, pad_net, W, H, [(0.5, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (0.5, H - 0.5)], ((500.0, 500.0), (501.0, 501.0)), plane_gnd=False, stub_hint={"J1": (0, -1)}, log=lambda *a: None)
r.make_stubs()
orig = r.astar
def astar(net, cls, starts, targets, *a, **k):
    path = orig(net, cls, starts, targets, *a, **k)
    if net == "GND":
        print("  astar starts", [(L, i*0.125, j*0.125) for (L,i,j) in starts][:3], "-> path", None if path is None else (len(path), [(L, i*0.125, j*0.125) for (L,i,j) in (path[0], path[-1])]))
    return path
r.astar = astar
pads = r.pads_by_net["GND"]
print("GND pads:", [(r.fp_of_pad[id(p)].ref, p.number, round(p.x,2), round(p.y,2)) for p in pads])
r.route_all()
print("failed:", r.stats["failed"])
