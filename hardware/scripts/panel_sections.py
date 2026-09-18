"""Front panel in four routing sections (one per student) and back together again.

    python panel_sections.py split            write hardware/front-panel/sections/{A,B,C,D}/ from the master panel
    python panel_sections.py merge            collect the routing of all four sections into
                                              hardware/front-panel/front-panel-merged.kicad_pcb and run DRC on it
    python panel_sections.py check A          report what section A has routed (own nets, foreign nets, moved parts)

How it works.  Every student gets a complete copy of the unrouted panel and a list of NETS to route (SECTION.md and
the note on the board).  The copy is a normal KiCad project: open it, route your nets on F.Cu and B.Cu, drop vias to
the AGND / GND planes where your parts need them, save, commit on your branch.  `merge` starts from the instructor's
master panel and copies in, from each section file, only the tracks, arcs and vias that belong to that section's
nets (plus its GND / AGND items).  Footprint moves, zones and text in a section file are ignored, and a track on a net
that is not yours is ignored too - so nothing a student does can damage another student's work or the master.

Net groups are chosen so that each connection is complete inside one section (every panel net runs from a link
header to a connector, so a geometric cut would leave half-traces on every boundary):
  A  analog      AI1-8, AO1/2, AUX, RX, TX             link J1 -> the SMA field and the TX terminal
  B  digital     TTL1-8, FASTTTL1/2, TRIG_5V, LED_*    link J2 -> the TTL strip, two fast SMAs, TRIG SMA, three LEDs
  C  modules     MOD1-8, MODY1-8, MODOUT1-8, +5V_RAW   link J3 -> pull-downs -> 74AHCT541 -> series R -> module header
  D  isolated    ISO1_*, ISO2_*, OPTO_IN1/2, +3V3, I2C  terminals -> 6N137 chains -> link J3; +3V3 and I2C to OLED/Qwiic
GND and AGND are the inner planes; every section may add the vias and short stubs its own parts need.
"""
import io
import os
import re
import shutil
import subprocess
import sys

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PANEL = os.path.join(HW, "front-panel")
SECTIONS_DIR = os.path.join(PANEL, "sections")
MASTER_PCB = os.path.join(PANEL, "front-panel.kicad_pcb")
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
SHARED = {"GND", "AGND"}

NETS = {
    "A": ("Analog signals: link J1 to the SMA field and the TX coil terminal",
          ["/AI1", "/AI2", "/AI3", "/AI4", "/AI5", "/AI6", "/AI7", "/AI8", "/AO1", "/AO2", "/AUX", "/RX", "/TX"]),
    "B": ("Digital outputs, trigger and LEDs: link J2 to the TTL strip J31, the FAST1/FAST2 and TRIG SMAs, D1-D3",
          ["/TTL1", "/TTL2", "/TTL3", "/TTL4", "/TTL5", "/TTL6", "/TTL7", "/TTL8", "/FASTTTL1", "/FASTTTL2", "/TRIG_5V",
           "/LED_PWR_A", "/LED_WIFI", "/LED_WIFI_A", "/LED_ACT", "/LED_ACT_A"]),
    "C": ("Module outputs: link J3 to the pull-downs R491-R498, the 74AHCT541 U410, the series resistors R481-R488 and the module header J40",
          ["/MOD%d" % i for i in range(1, 9)] + ["/MODY%d" % i for i in range(1, 9)] + ["/MODOUT%d" % i for i in range(1, 9)] + ["+5V_RAW"]),
    "D": ("Isolated inputs, 3.3 V and I2C: terminals J411/J412 to the 6N137 chains and link J3; +3V3 to every part; I2C from J2 to the OLED J30 and the Qwiic J33",
          ["/ISO1_B", "/ISO1_C", "/ISO1_E", "/ISO1_IN+", "/ISO1_IN-", "/ISO1_LEDA", "/ISO1_NODE",
           "/ISO2_B", "/ISO2_C", "/ISO2_E", "/ISO2_IN+", "/ISO2_IN-", "/ISO2_LEDA", "/ISO2_NODE",
           "/OPTO_IN1", "/OPTO_IN2", "+3V3", "/I2C_SCL", "/I2C_SDA"]),
}

# ---------------------------------------------------------------- s-expression helpers (top-level items only)
ITEM_RE = re.compile(r"\n\t\((?=[a-z_]+[\s\n])")


def top_items(text):
    """split a .kicad_pcb into (head, [item texts], tail) where items are the top-level '(...)' blocks."""
    parts = ITEM_RE.split(text)
    head = parts[0]
    items = ["\n\t(" + p for p in parts[1:]]
    # the last item carries the closing ')' of the file
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


def item_net(item):
    m = re.search(r'\(net\s+"((?:[^"\\]|\\.)*)"\)', item)
    return m.group(1) if m else None


def footprints(text):
    """ref -> (x, y, rot, layer) for every footprint"""
    out = {}
    for item in top_items(text)[1]:
        if item_kind(item) != "footprint":
            continue
        ref = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', item)
        at = re.search(r'\n\t\t\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)', item)
        layer = re.search(r'\n\t\t\(layer\s+"([^"]+)"', item)
        if ref and at:
            out[ref.group(1)] = (float(at.group(1)), float(at.group(2)), float(at.group(3) or 0), layer.group(1) if layer else "")
    return out


# ---------------------------------------------------------------- split
def split():
    master = io.open(MASTER_PCB, encoding="utf-8").read()
    head, items, tail = top_items(master)
    routed = [it for it in items if item_kind(it) in ("segment", "arc", "via")]
    if routed:
        print("note: the master already has %d routed items; the section copies keep them" % len(routed))
    for sec, (what, nets) in NETS.items():
        d = os.path.join(SECTIONS_DIR, sec)
        os.makedirs(d, exist_ok=True)
        for name in ("front-panel.kicad_pro", "front-panel.kicad_sch", "front-panel.kicad_dru", "front-panel.kicad_prl"):
            src = os.path.join(PANEL, name)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(d, name))
        # library tables: the copy is two folders deeper than the panel project
        for tbl, kind in (("fp-lib-table", "fp_lib_table"), ("sym-lib-table", "sym_lib_table")):
            t = io.open(os.path.join(PANEL, tbl), encoding="utf-8").read().replace("${KIPRJMOD}/../lib/", "${KIPRJMOD}/../../../lib/")
            io.open(os.path.join(d, tbl), "w", encoding="utf-8", newline="\n").write(t)
        # the board: the master plus one note that says whose copy this is
        note = ('\n\t(gr_text "SECTION %s - route ONLY these nets: %s   (see SECTION.md; other nets are ignored at the merge)"\n'
                '\t\t(at 90 8 0)\n\t\t(layer "Cmts.User")\n\t\t(uuid "0000%s000-0000-4000-8000-000000000001")\n'
                '\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.5 1.5)\n\t\t\t\t(thickness 0.2)\n\t\t\t)\n\t\t)\n\t)'
                % (sec, ", ".join(n.lstrip("/") for n in nets), sec.lower() * 4))
        io.open(os.path.join(d, "front-panel.kicad_pcb"), "w", encoding="utf-8", newline="\n").write(head + "".join(items) + note + tail)
        io.open(os.path.join(d, "SECTION.md"), "w", encoding="utf-8", newline="\n").write(section_md(sec, what, nets))
        print("section %s: %d nets -> %s" % (sec, len(nets), os.path.relpath(d, HW)))
    io.open(os.path.join(SECTIONS_DIR, "README.md"), "w", encoding="utf-8", newline="\n").write(readme_md())
    print("wrote", os.path.relpath(os.path.join(SECTIONS_DIR, "README.md"), HW))


def section_md(sec, what, nets):
    rows = "\n".join("| `%s` |" % n.lstrip("/") for n in nets)
    return """# Front panel — section %s

**%s.**

Open `front-panel.kicad_pro` in this folder (KiCad 10). Route the nets in the table below and nothing else. The other
nets stay unrouted in your copy; another student routes them in theirs, and the instructor merges all four copies with
`hardware/scripts/panel_sections.py merge`. Tracks on nets that are not yours, moved parts and new zones are ignored at the merge.

| Net |
|---|
%s

Rules of the board (the design rules in `front-panel.kicad_dru` check them for you with DRC):

- Signal layers are F.Cu and B.Cu only. In1.Cu is the AGND plane and In2.Cu the GND plane: no tracks there.
- Track width 0.25 mm, clearance 0.2 mm (analog inputs 0.3 mm), vias 0.6 / 0.3 mm. Analog nets stay away from the
  digital ones where you can.
- A GND or AGND pad of one of *your* parts connects to its plane with a via next to the pad. Do not draw ground tracks
  across the board.
- Isolated inputs (section D): everything in the ISO groups keeps 2.5 mm from every other net, on every layer; the
  keep-out areas on the board show where.
- Do not move parts, do not edit the schematic. If a part is in the way, say so — the instructor moves it in the master.
- Save, then run DRC (Inspect → Design Rules Checker): your nets should show no unconnected items and no violations.

Hand-in: commit `hardware/front-panel/sections/%s/front-panel.kicad_pcb` on your branch from the Source Control panel and ask the
tutor to open the pull request. The tutor is the help desk; questions that need the instructor go to s.p.bennetts@g.iams.sinica.edu.tw.
""" % (sec, what, rows, sec)


def readme_md():
    lines = ["# Front panel — four routing sections\n",
             "The front panel is one board, but its routing is done by four students, one section each. Every section folder holds a",
             "complete copy of the unrouted panel and a `SECTION.md` with the nets to route. The instructor merges the four copies",
             "with `python hardware/scripts/panel_sections.py merge`, which takes only each section's own nets from each copy.\n",
             "| Section | Routes | Nets |", "|---|---|---|"]
    for sec, (what, nets) in NETS.items():
        lines.append("| **%s** | %s | %d |" % (sec, what, len(nets)))
    lines += ["", "GND and AGND are the inner planes: every section drops the vias its own parts need. Nothing else is shared.",
              "", "Why by nets and not by area: every panel net runs from a link header at an edge to a connector in the middle of the board,",
              "so a geometric cut would leave half a trace on every boundary. With net groups each connection is complete in one copy.", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- check / merge
def collect(sec):
    """(kept items, foreign items, moved refs) from a section's board"""
    path = os.path.join(SECTIONS_DIR, sec, "front-panel.kicad_pcb")
    text = io.open(path, encoding="utf-8").read()
    master = io.open(MASTER_PCB, encoding="utf-8").read()
    own = set(NETS[sec][1]) | SHARED
    kept, foreign = [], []
    for it in top_items(text)[1]:
        if item_kind(it) not in ("segment", "arc", "via"):
            continue
        net = item_net(it)
        (kept if net in own else foreign).append(it)
    fm, fs = footprints(master), footprints(text)
    moved = sorted(r for r in fm if r in fs and (abs(fm[r][0] - fs[r][0]) > 0.01 or abs(fm[r][1] - fs[r][1]) > 0.01 or fm[r][2] != fs[r][2]))
    return kept, foreign, moved


def check(sec):
    kept, foreign, moved = collect(sec)
    nets = sorted({item_net(i) for i in kept})
    print("section %s: %d own items on %d nets: %s" % (sec, len(kept), len(nets), " ".join(n.lstrip("/") for n in nets)))
    if foreign:
        print("   ignored: %d items on nets that are not section %s's: %s" % (len(foreign), sec, " ".join(sorted({(item_net(i) or "?").lstrip("/") for i in foreign}))))
    if moved:
        print("   WARNING: parts moved in the section copy (ignored at the merge): %s" % " ".join(moved))
    missing = [n for n in NETS[sec][1] if n not in nets]
    if missing:
        print("   not routed yet: %s" % " ".join(n.lstrip("/") for n in missing))


def merge():
    master = io.open(MASTER_PCB, encoding="utf-8").read()
    head, items, tail = top_items(master)
    added = []
    seen = set()
    for sec in NETS:
        if not os.path.exists(os.path.join(SECTIONS_DIR, sec, "front-panel.kicad_pcb")):
            print("section %s: no board file, skipped" % sec)
            continue
        kept, foreign, moved = collect(sec)
        n = 0
        for it in kept:
            key = re.sub(r'\(uuid "[^"]+"\)', "", it)     # identical geometry from two sections (shared ground) counts once
            if key in seen:
                continue
            seen.add(key)
            added.append(it)
            n += 1
        print("section %s: %d items taken, %d foreign ignored%s" % (sec, n, len(foreign), (", moved parts ignored: " + " ".join(moved)) if moved else ""))
    out = os.path.join(PANEL, "front-panel-merged.kicad_pcb")
    io.open(out, "w", encoding="utf-8", newline="\n").write(head + "".join(items) + "".join(added) + tail)
    print("wrote", os.path.relpath(out, HW), "with", len(added), "routed items")
    if os.path.exists(KICAD_CLI):
        rep = os.path.join(PANEL, "front-panel-merged.drc.json")
        subprocess.run([KICAD_CLI, "pcb", "drc", "-o", rep, "--format", "json", "--severity-all", "--refill-zones", out], check=False, capture_output=True)
        if os.path.exists(rep):
            import json
            d = json.load(open(rep, encoding="utf-8"))
            from collections import Counter
            c = Counter(v["type"] for v in d.get("violations", []))
            print("DRC on the merged board: %d unconnected, violations %s" % (len(d.get("unconnected_items", [])), dict(c) or "none"))
    print("Open the merged board in KiCad, look, then replace front-panel.kicad_pcb with it by hand when you accept it.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "split"
    if cmd == "split":
        split()
    elif cmd == "merge":
        merge()
    elif cmd == "check":
        for sec in (sys.argv[2:] or list(NETS)):
            check(sec)
    else:
        print(__doc__)
