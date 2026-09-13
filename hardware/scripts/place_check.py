"""Fast placement checker: courtyard overlaps, pad-to-pad gaps (< min) between different footprints,
courtyard outside the board.  Usage: python place_check.py [min_gap]"""
import sys, itertools
sys.path.insert(0, ".")
import gen_pcb
from pcb_model import Board

def rect_of_pad(p):
    return (p.x - p.hx, p.y - p.hy, p.x + p.hx, p.y + p.hy)

def gap(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0); dy = max(a[1] - b[3], b[1] - a[3], 0)
    return (dx * dx + dy * dy) ** 0.5

def main(min_gap=0.25):
    board, comps, nets = gen_pcb.build(route=False)
    fps = board.footprints
    W, H = gen_pcb.W, gen_pcb.H
    bad = 0
    for f in fps:
        c = f.bbox()
        if c[0] < 0.3 or c[1] < 0.3 or c[2] > W - 0.3 or c[3] > H - 0.3:
            print("EDGE   %-6s courtyard %s" % (f.ref, tuple(round(v, 2) for v in c))); bad += 1
    for a, b in itertools.combinations(fps, 2):
        ca, cb = a.bbox(), b.bbox()
        if gap(ca, cb) > 3.0:
            continue
        if gap(ca, cb) == 0 and not (a.ref.startswith("FID") or b.ref.startswith("FID")):
            ov = (min(ca[2], cb[2]) - max(ca[0], cb[0])) * (min(ca[3], cb[3]) - max(ca[1], cb[1]))
            if ov > 0.01:
                print("COURT  %-6s %-6s overlap %.2f mm2" % (a.ref, b.ref, ov)); bad += 1
        for pa in a.pads:
            ra = rect_of_pad(pa)
            for pb in b.pads:
                if pa.net and pa.net == pb.net:
                    continue
                g = gap(ra, rect_of_pad(pb))
                if g < min_gap:
                    print("PAD    %-6s.%-5s %-6s.%-5s gap %.2f" % (a.ref, pa.number, b.ref, pb.number, g)); bad += 1
    print("issues:", bad)

if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 0.25)
