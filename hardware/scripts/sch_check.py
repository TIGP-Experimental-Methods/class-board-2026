"""Layout collision check for the generated schematic sheets (2026-09-17).

Builds every sheet in-process (same list as gen_sch.main), keeps the wire list from BEFORE
split_wires_at_pins, and reports geometry that KiCad would turn into an unintended connection
or that simply overlaps on the page:

  PIN-ON-WIRE    a pin lying in the interior of a wire it was not wired to (KiCad connects it)
  PWR-ENDS       a power-symbol pin that terminates more than one wire (a wire runs into the symbol)
  PIN-STACK      two pins of different symbols at one point (stacked power symbols or a pin-pin short)
  WIRE-THRU      a wire crossing a symbol body without ending at one of that symbol's pins
  WIRE-OVERLAP   two collinear wires sharing more than a point
  BODY-OVERLAP   two symbol bodies overlapping
  LABEL-OVERLAP  a net label whose text box crosses a wire or a symbol that is not its own pin
  TEXT-BLOCK     free text landing on the title block or running off the right edge

Usage (from hardware/scripts):  python sch_check.py [--all] [sheet_name ...]
Exit code = number of PIN-ON-WIRE + PWR-ENDS + PIN-STACK findings (the electrical ones).
"""
import glob
import importlib
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_sch  # noqa: E402

EPS = 1e-6
PAPER = {"A3": (420.0, 297.0), "A2": (594.0, 420.0), "A4": (297.0, 210.0)}
TITLE_BLOCK = (135.0, 45.0)     # width / height of the KiCad default title block from the bottom-right corner
CHAR_W = 0.9                    # text width per character as a fraction of the font size (KiCad default font)

# ---- capture raw wires ------------------------------------------------------------------------
_orig_aj = gen_sch.auto_junctions


def _aj(sh):
    sh.raw_wires = list(sh.wires)
    _orig_aj(sh)


gen_sch.auto_junctions = _aj


def build_all():
    root_uuid = "check"
    sheets = {}
    for fn in (gen_sch.build_base, gen_sch.build_b2, gen_sch.build_b1, gen_sch.build_b3, gen_sch.build_b5, gen_sch.build_link):
        s = fn(root_uuid)
        sheets[s.name] = s
    for path in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sheet_*.py"))):
        name = os.path.splitext(os.path.basename(path))[0]
        mod = importlib.import_module(name)
        s = mod.build(root_uuid)
        sheets[s.name] = s
    return sheets


# ---- geometry ---------------------------------------------------------------------------------
def interior(p, seg):
    x1, y1, x2, y2 = seg
    px, py = p
    if abs(x1 - x2) < EPS:
        return abs(px - x1) < EPS and min(y1, y2) + EPS < py < max(y1, y2) - EPS
    if abs(y1 - y2) < EPS:
        return abs(py - y1) < EPS and min(x1, x2) + EPS < px < max(x1, x2) - EPS
    return False


def at_end(p, seg):
    return (abs(p[0] - seg[0]) < EPS and abs(p[1] - seg[1]) < EPS) or (abs(p[0] - seg[2]) < EPS and abs(p[1] - seg[3]) < EPS)


def seg_hits_box(seg, box):
    """does the segment pass through the OPEN box (x1,y1,x2,y2)?"""
    x1, y1, x2, y2 = seg
    bx1, by1, bx2, by2 = box
    if abs(x1 - x2) < EPS:
        return bx1 + EPS < x1 < bx2 - EPS and max(y1, y2) > by1 + EPS and min(y1, y2) < by2 - EPS
    if abs(y1 - y2) < EPS:
        return by1 + EPS < y1 < by2 - EPS and max(x1, x2) > bx1 + EPS and min(x1, x2) < bx2 - EPS
    return False


def boxes_overlap(a, b, shrink=0.0):
    return (a[0] + shrink < b[2] - shrink and b[0] + shrink < a[2] - shrink and
            a[1] + shrink < b[3] - shrink and b[1] + shrink < a[3] - shrink)


def collinear_overlap(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    if abs(ax1 - ax2) < EPS and abs(bx1 - bx2) < EPS and abs(ax1 - bx1) < EPS:
        lo, hi = max(min(ay1, ay2), min(by1, by2)), min(max(ay1, ay2), max(by1, by2))
        return hi - lo > EPS
    if abs(ay1 - ay2) < EPS and abs(by1 - by2) < EPS and abs(ay1 - by1) < EPS:
        lo, hi = max(min(ax1, ax2), min(bx1, bx2)), min(max(ax1, ax2), max(bx1, bx2))
        return hi - lo > EPS
    return False


def inst_box(i):
    """screen bbox; power symbols get a tight box around their graphic instead of the +-2.54 default"""
    if i.sym.power:
        pts = [(-1.4, -0.3), (1.4, -0.3), (-1.4, 2.8), (1.4, 2.8)]       # lib y-up: graphic from the pin outward
        if i.sym.name in ("PWR_GND", "PWR_AGND", "PWR_n12V"):
            pts = [(-1.4, 0.3), (1.4, 0.3), (-1.4, -2.8), (1.4, -2.8)]
        tp = [gen_sch.xform(x, y, i.rot, i.mirror) for x, y in pts]
        xs = [i.x + p[0] for p in tp]
        ys = [i.y + p[1] for p in tp]
        return min(xs), min(ys), max(xs), max(ys)
    return i.bbox()


def label_box(lbl):
    text, x, y, rot, kind, shape = lbl
    w = len(text) * 1.27 * CHAR_W + (3.0 if kind != "local" else 0.8)
    h = 1.9
    if rot == 0:
        return x, y - h / 2, x + w, y + h / 2
    if rot == 180:
        return x - w, y - h / 2, x, y + h / 2
    if rot == 90:
        return x - h / 2, y - w, x + h / 2, y
    return x - h / 2, y, x + h / 2, y + w


def text_box(t):
    s, x, y, size, bold = t
    return x, y - size * 0.7, x + len(s) * size * CHAR_W, y + size * 0.7


# ---- checks -----------------------------------------------------------------------------------
def check_sheet(sh):
    R = defaultdict(list)
    raw = getattr(sh, "raw_wires", sh.wires)
    pins = []          # (inst, pinno, pos)
    pin_at = defaultdict(list)
    inst_pins = defaultdict(set)
    for i in sh.insts:
        for p in i.pins():
            if p.hide:
                continue
            pos = i.pin_pos(p.number)
            pins.append((i, p.number, pos))
            pin_at[pos].append(i)
            inst_pins[i.ref, i.unit].add(pos)
    # PIN-ON-WIRE and PWR-ENDS
    for i, pn, pos in pins:
        if i.sym.name == "PWR_FLAG":
            continue
        n_end = sum(1 for seg in raw if at_end(pos, seg))
        hits = [seg for seg in raw if interior(pos, seg)]
        for seg in hits:
            # a pin lying on a wire with no wire of its own is an intentional tap (a cap on a rail line);
            # a pin that is ALSO wired elsewhere, or a power pin, is an unintended connection
            if i.sym.power or n_end > 0 or len(hits) > 1:
                R["PIN-ON-WIRE"].append("%s pin %s at (%.2f,%.2f) lies on wire (%.2f,%.2f)-(%.2f,%.2f)" % ((i.ref, pn) + pos + seg))
            else:
                R["TAP"].append("%s pin %s" % (i.ref, pn))
        if i.sym.power:
            n = sum(1 for seg in raw if at_end(pos, seg))
            if n > 1:
                R["PWR-ENDS"].append("%s (%s) at (%.2f,%.2f) terminates %d wires" % (i.ref, i.value, pos[0], pos[1], n))
    # PIN-STACK
    for pos, lst in pin_at.items():
        refs = sorted({i.ref for i in lst})
        if len(refs) > 1 and any(i.sym.name == "PWR_FLAG" for i in lst) and all(i.sym.power for i in lst):
            continue        # a PWR_FLAG on a power pin is the usual way to flag a ground
        if len(refs) > 1:
            kind = "stacked power symbols" if all(i.sym.power for i in lst) else "PIN-PIN SHORT"
            R["PIN-STACK"].append("%s at (%.2f,%.2f): %s" % (kind, pos[0], pos[1], " ".join(refs)))
    # WIRE-THRU
    for i in sh.insts:
        box = inst_box(i)
        mine = inst_pins[i.ref, i.unit]
        for seg in raw:
            if any(at_end(p, seg) for p in mine):
                continue
            if seg_hits_box(seg, box):
                R["WIRE-THRU"].append("wire (%.2f,%.2f)-(%.2f,%.2f) crosses %s (%s)" % (seg + (i.ref, i.value)))
    # WIRE-OVERLAP
    for a in range(len(raw)):
        for b in range(a + 1, len(raw)):
            if collinear_overlap(raw[a], raw[b]):
                R["WIRE-OVERLAP"].append("(%.2f,%.2f)-(%.2f,%.2f) with (%.2f,%.2f)-(%.2f,%.2f)" % (raw[a] + raw[b]))
    # BODY-OVERLAP
    boxes = [(i, inst_box(i)) for i in sh.insts]
    for a in range(len(boxes)):
        for b in range(a + 1, len(boxes)):
            ia, ba = boxes[a]
            ib, bb = boxes[b]
            if ia.ref == ib.ref:
                continue
            shrink = -0.5 if (ia.sym.power and ib.sym.power) else 0.3     # power symbols carry a value text ~3.6 mm wide
            if boxes_overlap(ba, bb, shrink):
                R["BODY-OVERLAP"].append("%s (%s) with %s (%s) near (%.1f,%.1f)" % (ia.ref, ia.value, ib.ref, ib.value, max(ba[0], bb[0]), max(ba[1], bb[1])))
    # LABEL-OVERLAP
    for lbl in sh.labels:
        lb = label_box(lbl)
        anchor = (lbl[1], lbl[2])
        for seg in raw:
            if at_end(anchor, seg):
                continue
            if seg_hits_box(seg, lb):
                R["LABEL-OVERLAP"].append("label %s at (%.2f,%.2f) crosses wire (%.2f,%.2f)-(%.2f,%.2f)" % ((lbl[0],) + anchor + seg))
        for i, box in boxes:
            if anchor in inst_pins[i.ref, i.unit]:
                continue
            if boxes_overlap(lb, box, 0.2):
                R["LABEL-OVERLAP"].append("label %s at (%.2f,%.2f) over %s" % (lbl[0], anchor[0], anchor[1], i.ref))
        for other in sh.labels:
            if other is lbl or other[0] + str(other[1:3]) <= lbl[0] + str(lbl[1:3]):
                continue
            if boxes_overlap(lb, label_box(other), 0.2):
                R["LABEL-OVERLAP"].append("label %s at (%.2f,%.2f) over label %s" % (lbl[0], anchor[0], anchor[1], other[0]))
    # TEXT-OVERLAP: free text over symbols (power symbols extended by their value text), labels or wires
    for t in sh.texts:
        tb_ = text_box(t)
        for i, box in boxes:
            if i.sym.power:
                box = (box[0] - 2.5, box[1] - 2.5, box[2] + 2.5, box[3] + 2.5)   # value text around the graphic
            if boxes_overlap(tb_, box, 0.2):
                R["TEXT-OVERLAP"].append("text %r at (%.0f,%.0f) over %s" % (t[0][:40], t[1], t[2], i.ref))
        for lbl in sh.labels:
            if boxes_overlap(tb_, label_box(lbl), 0.2):
                R["TEXT-OVERLAP"].append("text %r at (%.0f,%.0f) over label %s" % (t[0][:40], t[1], t[2], lbl[0]))
        for seg in raw:
            if seg_hits_box(seg, tb_):
                R["TEXT-OVERLAP"].append("text %r at (%.0f,%.0f) over wire (%.1f,%.1f)-(%.1f,%.1f)" % ((t[0][:40], t[1], t[2]) + seg))
    # TEXT-BLOCK
    pw, ph = PAPER.get(sh.paper, PAPER["A3"])
    tb = (pw - TITLE_BLOCK[0], ph - TITLE_BLOCK[1], pw, ph)
    for t in sh.texts:
        box = text_box(t)
        if boxes_overlap(box, tb):
            R["TEXT-BLOCK"].append("text on the title block: %r at (%.0f,%.0f)" % (t[0][:50], t[1], t[2]))
        elif box[2] > pw - 12:
            R["TEXT-BLOCK"].append("text runs off the right edge (ends %.0f): %r at (%.0f,%.0f)" % (box[2], t[0][:50], t[1], t[2]))
    return R


ORDER = ["PIN-ON-WIRE", "PWR-ENDS", "PIN-STACK", "WIRE-THRU", "WIRE-OVERLAP", "BODY-OVERLAP", "LABEL-OVERLAP", "TEXT-OVERLAP", "TEXT-BLOCK", "TAP"]
ELECTRICAL = ORDER[:3]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_all = "--all" in sys.argv
    sheets = build_all()
    total = defaultdict(int)
    bad = 0
    for name, sh in sheets.items():
        if args and name not in args:
            continue
        R = check_sheet(sh)
        counts = " ".join("%s=%d" % (k, len(R[k])) for k in ORDER if R[k])
        print("== %s (%s): %s" % (name, sh.paper, counts or "clean"))
        for k in ORDER:
            items = R[k]
            total[k] += len(items)
            if k in ELECTRICAL:
                bad += len(items)
            lim = len(items) if show_all else (0 if k == "TAP" else 12)
            for it in items[:lim]:
                print("   %-13s %s" % (k, it))
            if len(items) > lim:
                print("   %-13s ... %d more" % (k, len(items) - lim))
    print("== TOTAL: " + " ".join("%s=%d" % (k, total[k]) for k in ORDER))
    sys.exit(min(bad, 200))


if __name__ == "__main__":
    main()
