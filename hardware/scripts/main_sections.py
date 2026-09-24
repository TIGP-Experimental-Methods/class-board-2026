"""Main board in four routing areas (one per student) and back together again.

    python main_sections.py areas            (re)draw the four rule areas ZONE_A..ZONE_D and their labels in the master
                                             hardware/class-board.kicad_pcb (KiCad must be closed)
    python main_sections.py split            write hardware/sections/{A,B,C,D}/ from the master: a copy of the board per
                                             student with the instructor's routing locked, SECTION.md, README.md
    python main_sections.py check A          report what section A has routed (inside its area, outside, crossing, moved parts)
    python main_sections.py merge            collect the four sections' routing into hardware/class-board-merged.kicad_pcb
                                             and run DRC on it
    python main_sections.py report           list the remaining connections of the master per area (needs kicad-cli)

How it works.  The main board is divided BY AREA (the instructor's decision, 2026-09-21): four rule areas on the board,
each a student's routing territory.  Every student gets a complete copy of the board in hardware/sections/<X>/ with
everything the instructor has routed so far locked (it is accepted as done).  The student routes the connections
whose both ends lie inside the area, on F.Cu and B.Cu, and drops the vias to the planes that the parts in the area
need.  `merge` starts from the instructor's current master and copies in, from each section file, only the NEW tracks
and vias that lie completely inside that section's area.  Anything that crosses an area boundary is the instructor's
to route; the instructor routes anywhere, in the master, at any time - nothing in the master is locked or restricted.
Footprint moves, zones and text in a section file are ignored at the merge.

Areas (board coordinates: x 0..180 to the right, y 15..115 downwards; the rear edge with the USB-C, the jack and the
terminals is at y = 15, the front edge at y = 115):
  A  rear right    x 96..180, y 15..52, then x 109..180 down to y 59.5    analog inputs: ADC U101, conditioning R11x/C11x/D11x, J14/J15
  B  front right   x 109..180, y 59.5..115                                analog outputs (DAC U301, output stage) + the NMR transmitter
  C  front left    x 0..109, y 75..115                                    the NMR receiver (tank, LNA, mixer, IF, clock) + J5
  D  rear left     x 0..96, y 15..52, then x 0..109 down to y 75          power entry and rails, coil switches, dev-board socket, U502
The link sockets J6/J7/J8, the dev-board rows J1/J2, J5, the mounting holes and the fiducials belong to the instructor
wherever they sit.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from collections import Counter, defaultdict

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
MASTER_PCB = os.path.join(HW, "class-board.kicad_pcb")
SECTIONS_DIR = os.path.join(HW, "sections")
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
OUTLINE = (0.0, 15.0, 180.0, 115.0)          # x0 y0 x1 y1 of the Edge.Cuts rectangle
INSET = 0.5                                   # the drawn rule areas stay this far inside the outline

# polygons on the outline (the drawn areas are inset by INSET at the outline; the tests use these)
AREAS = {
    "A": ("Rear right - the analog inputs: the ADC U101, the input conditioning R11x / C11x / D11x, the AGND-select headers J14 / J15",
          [(96, 15), (180, 15), (180, 59.5), (109, 59.5), (109, 52), (96, 52)]),
    "B": ("Front right - the analog outputs (DAC U301 and the output stage) and the NMR transmitter (DDS, filter, power stage, TX terminal side)",
          [(109, 59.5), (180, 59.5), (180, 115), (109, 115)]),
    "C": ("Front left - the NMR receiver: tank and blanking switch, LNA, I/Q mixer, IF filters, clock generator; the expansion header J5",
          [(0, 75), (109, 75), (109, 115), (0, 115)]),
    "D": ("Rear left - power entry and rails, the coil switches (H-bridge, polarizer), the dev-board socket J1 / J2 and the fast TTL buffer U502",
          [(0, 15), (96, 15), (96, 52), (109, 52), (109, 75), (0, 75)]),
}
INSTRUCTOR_REFS = {"J1", "J2", "J5", "J6", "J7", "J8", "H1", "H2", "H3", "H4", "FID1", "FID2", "FID3"}
# who routes which area (instructor, 2026-09-24: three students on the boards; area C has no student)
ASSIGNED = {"A": "Renqian (branch `a-renqian`)", "B": "Yi-Tsai (branch `w1-yi-tsai`)", "C": "the instructor (no student)", "D": "Lihdong (branch `d-lihdong`)"}
OLD_ZONE_NAMES = {"ZONE_A", "ZONE_B", "ZONE_C", "ZONE_D", "ZONE_INSTR", "ZONE_BASE"}
NS = uuid.UUID("6f1c2a5e-7b1d-4b8e-9a0f-2c3d4e5f6a7b")


def det_uuid(tag):
    return str(uuid.uuid5(NS, "class-board " + tag))


# ---------------------------------------------------------------- geometry
def inside(poly, x, y, tol=0.0):
    """point in polygon (ray casting); a point within tol of an edge counts as inside"""
    n = len(poly)
    j = n - 1
    c = False
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            c = not c
        j = i
    if c or tol <= 0:
        return c
    for i in range(n):
        if _dist_to_segment(x, y, poly[i], poly[(i + 1) % n]) <= tol:
            return True
    return False


def _dist_to_segment(x, y, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L))
    px, py = ax + t * dx, ay + t * dy
    return ((x - px) ** 2 + (y - py) ** 2) ** 0.5


def area_of(x, y):
    for sec, (_, poly) in AREAS.items():
        if inside(poly, x, y):
            return sec
    return None


def drawn_polygon(poly):
    """the rule-area polygon as drawn: inset by INSET where it touches the outline"""
    x0, y0, x1, y1 = OUTLINE
    out = []
    for x, y in poly:
        out.append((x0 + INSET if x == x0 else x1 - INSET if x == x1 else x,
                    y0 + INSET if y == y0 else y1 - INSET if y == y1 else y))
    return out


# ---------------------------------------------------------------- s-expression helpers (top-level items only)
ITEM_RE = re.compile(r"\n\t\((?=[a-z_]+[\s\n])")


def top_items(text):
    """split a .kicad_pcb into (head, [item texts], tail) where items are the top-level '(...)' blocks."""
    parts = ITEM_RE.split(text)
    head = parts[0]
    items = ["\n\t(" + p for p in parts[1:]]
    tail = ""
    if items:
        last = items[-1]
        k = last.rstrip().rfind("\n)")
        if k >= 0:
            tail = last[k:]
            items[-1] = last[:k]
    return head, items, tail


def item_kind(item):
    m = re.match(r"\n\t\(([a-z_]+)", item)
    return m.group(1) if m else ""


def item_uuid(item):
    m = re.search(r'\(uuid\s+"([^"]+)"\)', item)
    return m.group(1) if m else None


def item_net(item):
    m = re.search(r'\(net\s+"((?:[^"\\]|\\.)*)"\)', item)
    if m:
        return m.group(1)
    m = re.search(r'\(net\s+(\d+)\)', item)
    return m.group(1) if m else None


def item_locked(item):
    return "(locked yes)" in item


def item_points(item):
    """the points that must all lie inside an area for a routed item to belong to it"""
    k = item_kind(item)
    pts = []
    if k in ("segment", "arc"):
        for tag in ("start", "mid", "end"):
            m = re.search(r'\(%s\s+([-\d.]+)\s+([-\d.]+)\)' % tag, item)
            if m:
                pts.append((float(m.group(1)), float(m.group(2))))
    elif k == "via":
        m = re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\)', item)
        if m:
            pts.append((float(m.group(1)), float(m.group(2))))
    return pts


def item_area(item):
    """the area an item lies in completely, 'X/Y' when it crosses, None when a point is outside every area"""
    pts = item_points(item)
    secs = [area_of(x, y) for x, y in pts]
    if not secs or None in secs:
        return None
    if len(set(secs)) == 1:
        return secs[0]
    return "/".join(sorted(set(secs)))


def footprints(text):
    """ref -> dict(x, y, rot, layer, block, item)"""
    out = {}
    for item in top_items(text)[1]:
        if item_kind(item) != "footprint":
            continue
        ref = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', item)
        at = re.search(r'\n\t\t\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)', item)
        layer = re.search(r'\n\t\t\(layer\s+"([^"]+)"', item)
        block = re.search(r'\(property\s+"Block"\s+"([^"]*)"', item)
        if ref and at:
            out[ref.group(1)] = dict(x=float(at.group(1)), y=float(at.group(2)), rot=float(at.group(3) or 0),
                                     layer=layer.group(1) if layer else "", block=block.group(1) if block else "")
    return out


def lock_item(item):
    """add (locked yes) to a segment / arc / via (after (width ..) or (drill ..)), as KiCad writes it"""
    if item_locked(item):
        return item
    k = item_kind(item)
    anchor = r'(\n\t\t\(width\s+[-\d.]+\))' if k in ("segment", "arc") else r'(\n\t\t\(drill\s+[^\n]*\))'
    new, n = re.subn(anchor, r'\1\n\t\t(locked yes)', item, count=1)
    if n == 0:   # fall back: before (layer ..) / (layers ..)
        new, n = re.subn(r'(\n\t\t\(layers?\s)', r'\n\t\t(locked yes)\1', item, count=1)
    return new


# ---------------------------------------------------------------- areas (edit the master)
def zone_text(sec, poly):
    pts = " ".join("(xy %g %g)" % (x, y) for x, y in poly)
    return ('\n\t(zone\n\t\t(net 0)\n\t\t(net_name "")\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(uuid "%s")\n\t\t(name "ZONE_%s")\n'
            '\t\t(hatch edge 0.5)\n\t\t(connect_pads\n\t\t\t(clearance 0)\n\t\t)\n\t\t(min_thickness 0.25)\n'
            '\t\t(keepout\n\t\t\t(tracks allowed)\n\t\t\t(vias allowed)\n\t\t\t(pads allowed)\n\t\t\t(copperpour allowed)\n\t\t\t(footprints allowed)\n\t\t)\n'
            '\t\t(placement\n\t\t\t(enabled no)\n\t\t\t(sheetname "")\n\t\t)\n'
            '\t\t(fill\n\t\t\t(thermal_gap 0.5)\n\t\t\t(thermal_bridge_width 0.5)\n\t\t\t(island_removal_mode 0)\n\t\t)\n'
            '\t\t(polygon\n\t\t\t(pts\n\t\t\t\t%s\n\t\t\t)\n\t\t)\n\t)' % (det_uuid("zone " + sec), sec, pts))


def label_text(sec, text, x, y, size=2.0):
    return ('\n\t(gr_text "%s"\n\t\t(at %g %g 0)\n\t\t(layer "Cmts.User")\n\t\t(uuid "%s")\n'
            '\t\t(effects\n\t\t\t(font\n\t\t\t\t(size %g %g)\n\t\t\t\t(thickness 0.25)\n\t\t\t)\n\t\t\t(justify left)\n\t\t)\n\t)'
            % (text.replace('"', "'"), x, y, det_uuid("label " + sec), size, size))


LABEL_AT = {"A": (97, 16.2), "B": (110.5, 60.5), "C": (45, 76), "D": (3, 49.5)}   # free spots on Cmts.User


def is_area_zone(item):
    m = re.search(r'\(name\s+"([^"]+)"\)', item)
    return item_kind(item) == "zone" and m is not None and m.group(1) in OLD_ZONE_NAMES


def is_area_label(item):
    return item_kind(item) == "gr_text" and item_uuid(item) in {det_uuid("label " + s) for s in AREAS}


def areas():
    lock = [f for f in os.listdir(HW) if f.startswith("~") and f.endswith(".lck")]
    if lock:
        sys.exit("KiCad has the master open (%s) - close it first" % " ".join(lock))
    master = io.open(MASTER_PCB, encoding="utf-8").read()
    head, items, tail = top_items(master)
    kept = [it for it in items if not is_area_zone(it) and not is_area_label(it)]
    removed = len(items) - len(kept)
    new = []
    for sec, (what, poly) in AREAS.items():
        new.append(zone_text(sec, drawn_polygon(poly)))
        new.append(label_text(sec, "AREA %s" % sec, *LABEL_AT[sec]))
    io.open(MASTER_PCB, "w", encoding="utf-8", newline="\n").write(head + "".join(kept) + "".join(new) + tail)
    print("master: removed %d old area zones/labels, wrote 4 rule areas ZONE_A..ZONE_D (F.Cu + B.Cu, nothing disallowed) and 4 labels on Cmts.User" % removed)


# ---------------------------------------------------------------- DRC helpers
def run_drc(pcb, out_json):
    if not os.path.exists(KICAD_CLI):
        return None
    subprocess.run([KICAD_CLI, "pcb", "drc", "-o", out_json, "--format", "json", "--severity-all", "--refill-zones", pcb],
                   check=False, capture_output=True)
    if not os.path.exists(out_json):
        return None
    return json.load(io.open(out_json, encoding="utf-8"))


def remaining_by_area(drc):
    """unconnected items of a DRC report -> {area or 'crossing': Counter(net)}, plus the crossing list"""
    by = defaultdict(Counter)
    crossing = []
    for u in drc.get("unconnected_items", []):
        net = None
        for it in u["items"]:
            m = re.search(r"\[([^\]]+)\]", it["description"])
            if m:
                net = m.group(1)
        secs = [area_of(it["pos"]["x"], it["pos"]["y"]) for it in u["items"]]
        if len(set(secs)) == 1 and secs[0] is not None:
            by[secs[0]][net] += 1
        else:
            by["instructor"][net] += 1
            crossing.append((net, "/".join(str(s) for s in secs),
                             [(round(it["pos"]["x"], 1), round(it["pos"]["y"], 1)) for it in u["items"]]))
    return by, crossing


def report():
    tmp = os.path.join(HW, "scratchpad")
    os.makedirs(tmp, exist_ok=True)
    d = run_drc(MASTER_PCB, os.path.join(tmp, "master.drc.json"))
    if d is None:
        sys.exit("kicad-cli not found or DRC failed")
    by, crossing = remaining_by_area(d)
    for sec in list(AREAS) + ["instructor"]:
        c = by.get(sec, Counter())
        print("%-10s %3d remaining connections: %s" % (sec, sum(c.values()), ", ".join("%s x%d" % (n, k) if k > 1 else n for n, k in c.most_common())))
    print("crossing (instructor):")
    for net, secs, pts in crossing:
        print("   %-24s %-8s %s" % (net, secs, pts))
    return by, crossing


# ---------------------------------------------------------------- split
def split():
    master = io.open(MASTER_PCB, encoding="utf-8").read()
    head, items, tail = top_items(master)
    if not any(is_area_zone(it) and '"ZONE_D"' in it for it in items):
        sys.exit("the master has no ZONE_D rule area yet - run `main_sections.py areas` first (KiCad closed)")
    fps = footprints(master)
    tmp = os.path.join(HW, "scratchpad")
    os.makedirs(tmp, exist_ok=True)
    d = run_drc(MASTER_PCB, os.path.join(tmp, "master.drc.json"))
    by, crossing = remaining_by_area(d) if d else ({}, [])
    n_lock = 0
    out_items = []
    for it in items:
        k = item_kind(it)
        if k in ("segment", "arc", "via"):
            if not item_locked(it):
                n_lock += 1
            out_items.append(lock_item(it))
        elif k == "zone":
            # drop the zone fills: the copy is a third of the size and KiCad refills on demand
            out_items.append(re.sub(r'\n\t\t\(filled_polygon.*?\n\t\t\)', "", it, flags=re.S))
        else:
            out_items.append(it)
    for sec, (what, poly) in AREAS.items():
        dst = os.path.join(SECTIONS_DIR, sec)
        os.makedirs(dst, exist_ok=True)
        for name in ("class-board.kicad_pro", "class-board.kicad_dru"):
            shutil.copy(os.path.join(HW, name), os.path.join(dst, name))
        for tbl in ("fp-lib-table", "sym-lib-table"):
            t = io.open(os.path.join(HW, tbl), encoding="utf-8").read().replace("${KIPRJMOD}/lib/", "${KIPRJMOD}/../../lib/")
            io.open(os.path.join(dst, tbl), "w", encoding="utf-8", newline="\n").write(t)
        note = label_text("note " + sec, "SECTION %s - route ONLY inside AREA %s (see SECTION.md). The instructor's routing is locked; tracks outside the area are ignored at the merge." % (sec, sec), 2, 12.5, 1.5)
        io.open(os.path.join(dst, "class-board.kicad_pcb"), "w", encoding="utf-8", newline="\n").write(head + "".join(out_items) + note + tail)
        io.open(os.path.join(dst, "SECTION.md"), "w", encoding="utf-8", newline="\n").write(section_md(sec, what, poly, fps, by.get(sec, Counter())))
        print("section %s: %d parts, %d remaining connections -> %s" % (sec, len(parts_in(sec, fps)), sum(by.get(sec, Counter()).values()), os.path.relpath(dst, HW)))
    io.open(os.path.join(SECTIONS_DIR, "README.md"), "w", encoding="utf-8", newline="\n").write(readme_md(fps, by, crossing))
    record_base(items)
    print("locked %d routed items in the copies (the master is untouched); wrote %s and BASE_UUIDS.txt" % (n_lock, os.path.relpath(os.path.join(SECTIONS_DIR, "README.md"), HW)))


def parts_in(sec, fps):
    return sorted((r for r, f in fps.items() if r not in INSTRUCTOR_REFS and area_of(f["x"], f["y"]) == sec), key=ref_key)


def parked(fps):
    return sorted((r for r, f in fps.items() if area_of(f["x"], f["y"]) is None), key=ref_key)


def ref_key(r):
    m = re.match(r"([A-Za-z]+)(\d*)", r)
    return (m.group(1), int(m.group(2) or 0))


def compact(refs):
    """C101 C102 C103 -> C101-C103"""
    out = []
    i = 0
    while i < len(refs):
        j = i
        while j + 1 < len(refs) and ref_key(refs[j + 1])[0] == ref_key(refs[j])[0] and ref_key(refs[j + 1])[1] == ref_key(refs[j])[1] + 1:
            j += 1
        out.append(refs[i] if j == i else "%s-%s" % (refs[i], refs[j]) if j > i + 1 else "%s %s" % (refs[i], refs[j]))
        i = j + 1
    return " ".join(out)


def poly_words(poly):
    return ", ".join("(%g, %g)" % p for p in poly)


def section_md(sec, what, poly, fps, remaining):
    parts = parts_in(sec, fps)
    rem = "\n".join("| `%s` | %d |" % (n, k) for n, k in remaining.most_common()) or "| (run `main_sections.py report`) | |"
    return """# Main board — section %s

**%s.**

Open `class-board.kicad_pro` in this folder (KiCad 10) and route **inside area %s only** — the hatched rule area
`ZONE_%s` on the board, corners %s. Everything the instructor has routed so far is
locked: it is finished, leave it. A connection whose two ends are both inside your area is yours; a connection that
leaves the area is the instructor's — do not route it. Other students route the other areas in their own copies, and the
instructor merges all four copies with `hardware/scripts/main_sections.py merge`: only new tracks and vias that lie
completely inside your area are taken from your copy; tracks outside it, moved parts and new zones are ignored.

**Parts in your area** (%d): %s

**Connections still to route in your area** (from the DRC of the master when this copy was made; `AGND` and `GND` are
a via from the pad to the plane or to the ground pour next to it):

| Net | Connections |
|---|---|
%s

Rules of the board (the design rules in `class-board.kicad_dru` check them for you with DRC):

- Signal layers are F.Cu and B.Cu only. In1.Cu and In2.Cu are GND planes: no tracks there. AGND is the copper pour on
  F.Cu and B.Cu over the front half of the board (`AGND_F` / `AGND_B`); an AGND pad connects to it directly or with a via.
- Track widths and vias come from the net classes: 0.25 mm / 0.6 mm via for signals, 0.5 mm / 0.8 mm via for POWER,
  1.0 mm for POWER_RAW; clearance 0.2 mm (analog inputs 0.3 mm). Analog nets stay away from the digital ones where you can.
- A GND pad of one of *your* parts connects to the plane with a via next to the pad. Do not draw ground tracks across the board.
- Do not move parts, do not edit the schematic, do not update the PCB from the schematic (F8) — this copy has no schematic on
  purpose. If a part is in the way, say so: the instructor moves it in the master.
- Save, then run DRC (Inspect → Design Rules Checker): the connections inside your area should show as connected and
  your tracks should show no violations.

Hand-in: commit `hardware/sections/%s/class-board.kicad_pcb` on your branch from the Source Control panel and ask the tutor to
open the pull request. The tutor is the help desk; questions that need the instructor go to s.p.bennetts@g.iams.sinica.edu.tw.
""" % (sec, what, sec, sec, poly_words(drawn_polygon(poly)), len(parts), compact(parts), rem, sec)


def readme_md(fps, by, crossing):
    lines = ["# Main board — four routing areas\n",
             "The main board is one board, but its routing is finished by four students, one area each. Every section folder holds a",
             "complete copy of the board with the instructor's routing locked and a `SECTION.md` with the parts and the connections",
             "to route. The instructor merges the four copies with `python hardware/scripts/main_sections.py merge`, which takes from",
             "each copy only the new tracks and vias that lie completely inside that copy's area. A connection that crosses an area",
             "boundary is the instructor's; the instructor routes anywhere in the master at any time.\n",
             "| Area | Who | Where | Routes | Parts | Connections left |", "|---|---|---|---|---|---|"]
    for sec, (what, poly) in AREAS.items():
        lines.append("| **%s** | %s | %s | %s | %d | %d |" % (sec, ASSIGNED.get(sec, "-"), what.split(" - ")[0], what.split(" - ", 1)[1], len(parts_in(sec, fps)), sum(by.get(sec, Counter()).values())))
    lines += ["", "The link sockets J6 / J7 / J8, the dev-board rows J1 / J2, the expansion header J5, the mounting holes and the fiducials",
              "belong to the instructor wherever they sit."]
    p = parked(fps)
    if p:
        lines += ["", "Not yet placed (parked outside the outline; the instructor places them): " + compact(p) + "."]
    if crossing:
        c = Counter(net for net, _, _ in crossing)
        lines += ["", "**Connections that cross an area boundary — the instructor's (%d):** %s." % (
            len(crossing), ", ".join("%s x%d" % (n, k) if k > 1 else n for n, k in c.most_common()))]
    lines += ["", "Why by area: the main board's remaining work is mostly local — vias from pads to the planes and short links between",
              "neighbouring parts — so a geometric cut gives each student a coherent piece of the board to learn on, and the few",
              "long connections (SPI, I²C, the rails between areas) stay with the instructor.", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- check / merge
BASE_FILE = os.path.join(SECTIONS_DIR, "BASE_UUIDS.txt")


def base_uuids():
    """uuids of every routed item that was ever in the master when a split was made (so a copy can never bring back
    something the instructor deleted afterwards)"""
    if not os.path.exists(BASE_FILE):
        return set()
    return {l.strip() for l in io.open(BASE_FILE, encoding="utf-8") if l.strip() and not l.startswith("#")}


def record_base(items):
    u = base_uuids() | {item_uuid(it) for it in items if item_kind(it) in ("segment", "arc", "via")}
    os.makedirs(SECTIONS_DIR, exist_ok=True)
    io.open(BASE_FILE, "w", encoding="utf-8", newline="\n").write(
        "# routed items (segments/arcs/vias) that were ever in the master: never taken from a section copy\n" + "\n".join(sorted(x for x in u if x)) + "\n")


def collect(sec):
    """(inside items, outside/crossing items, moved refs, locked-but-changed count) from a section's board vs the master"""
    path = os.path.join(SECTIONS_DIR, sec, "class-board.kicad_pcb")
    text = io.open(path, encoding="utf-8").read()
    master = io.open(MASTER_PCB, encoding="utf-8").read()
    master_uuids = {item_uuid(it) for it in top_items(master)[1]} | base_uuids()
    inside_items, foreign = [], []
    for it in top_items(text)[1]:
        if item_kind(it) not in ("segment", "arc", "via"):
            continue
        if item_uuid(it) in master_uuids or item_locked(it):
            continue                      # the instructor's routing: the master has it, or he has deleted it since - never resurrected
        a = item_area(it)
        (inside_items if a == sec else foreign).append((a, it))
    fm, fs = footprints(master), footprints(text)
    moved = sorted(r for r in fm if r in fs and (abs(fm[r]["x"] - fs[r]["x"]) > 0.01 or abs(fm[r]["y"] - fs[r]["y"]) > 0.01 or fm[r]["rot"] != fs[r]["rot"]))
    return inside_items, foreign, moved


def check(sec):
    path = os.path.join(SECTIONS_DIR, sec, "class-board.kicad_pcb")
    if not os.path.exists(path):
        print("section %s: no board file" % sec)
        return
    inside_items, foreign, moved = collect(sec)
    nets = Counter(item_net(it) for _, it in inside_items)
    print("section %s: %d new items inside area %s on %d nets: %s" % (sec, len(inside_items), sec, len(nets), " ".join(sorted(n.lstrip("/") for n in nets if n))))
    if foreign:
        where = Counter(a or "outside" for a, _ in foreign)
        print("   ignored: %d items outside area %s or crossing a boundary (%s), nets: %s" % (
            len(foreign), sec, ", ".join("%s x%d" % kv for kv in where.most_common()),
            " ".join(sorted({(item_net(it) or "?").lstrip("/") for _, it in foreign}))))
    if moved:
        print("   WARNING: parts moved in the section copy (ignored at the merge): %s" % " ".join(moved))


def merge():
    master = io.open(MASTER_PCB, encoding="utf-8").read()
    head, items, tail = top_items(master)
    added, seen = [], set()
    for sec in AREAS:
        if not os.path.exists(os.path.join(SECTIONS_DIR, sec, "class-board.kicad_pcb")):
            print("section %s: no board file, skipped" % sec)
            continue
        inside_items, foreign, moved = collect(sec)
        n = 0
        for _, it in inside_items:
            key = re.sub(r'\(uuid "[^"]+"\)', "", it)
            if key in seen:
                continue
            seen.add(key)
            added.append(it)
            n += 1
        print("section %s: %d items taken, %d outside/crossing ignored%s" % (sec, n, len(foreign), (", moved parts ignored: " + " ".join(moved)) if moved else ""))
    out = os.path.join(HW, "class-board-merged.kicad_pcb")
    io.open(out, "w", encoding="utf-8", newline="\n").write(head + "".join(items) + "".join(added) + tail)
    print("wrote", os.path.relpath(out, HW), "with", len(added), "routed items added to the master")
    d = run_drc(out, os.path.join(HW, "class-board-merged.drc.json"))
    if d:
        c = Counter(v["type"] for v in d.get("violations", []))
        print("DRC on the merged board: %d unconnected, violations %s" % (len(d.get("unconnected_items", [])), dict(c) or "none"))
    print("Open the merged board in KiCad, look, then replace class-board.kicad_pcb with it by hand when you accept it.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "areas":
        areas()
    elif cmd == "split":
        split()
    elif cmd == "merge":
        merge()
    elif cmd == "report":
        report()
    elif cmd == "check":
        for sec in (sys.argv[2:] or list(AREAS)):
            check(sec)
    else:
        print(__doc__)
