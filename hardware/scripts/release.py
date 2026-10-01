"""Build the JLCPCB release package for both boards (D5/D8).

Outputs under hardware/release/<rev>/{main-board,front-panel}/:
  gerbers/*.gbr + *.drl (bottom-left aux origin), <board>-bom.csv, <board>-cpl.csv (JLC columns),
  <board>.pdf (schematic, all sheets), <board>-<layer>.svg + .png (readable layout), <board>.step,
  reports/{erc,drc}.json + summary.txt, hashes.txt (SHA-256 of every file in the folder).
Also hardware/release/<rev>/schematics/<sheet>.pdf (one PDF per sheet the root schematic references).
The netlist is exported fresh from the schematic at every run; hand-soldered parts (Assembly = hand)
go to <board>-hand-solder.csv and never into the JLC BOM/CPL.

Usage: python release.py <rev>   (e.g. python release.py revA)
"""
import csv
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netlist  # noqa: E402

HW = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KICAD_CLI = os.environ.get("KICAD_CLI", "C:/Program Files/KiCad/10.0/bin/kicad-cli.exe")
LAYERS4 = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
VIEWS4 = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu", "F.SilkS", "B.SilkS"]
BOARDS = {  # both boards are 4-layer (180 x 100 mm)
    "main-board": dict(dir=HW, project="class-board", layers=LAYERS4, views=VIEWS4),
    "front-panel": dict(dir=os.path.join(HW, "front-panel"), project="front-panel", layers=LAYERS4, views=VIEWS4),
}


def run(args, **k):
    print("  $", " ".join(a if " " not in a else '"%s"' % a for a in args))
    r = subprocess.run(args, capture_output=True, text=True, **k)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit("command failed: %s" % args[0])
    return r.stdout


def sub_sheets(board):
    """Names of the sheet files the root schematic references (never a hard-coded list)."""
    root = open(os.path.join(board["dir"], board["project"] + ".kicad_sch"), encoding="utf-8").read()
    return sorted(set(re.findall(r'\(property "Sheetfile" "(?:sheets/)?([^"/]+)\.kicad_sch"', root)))


def export_netlist(board, out_dir):
    """Fresh KiCad XML netlist of the schematic as it is now (never a cached copy)."""
    path = os.path.join(out_dir, "_netlist.xml")
    run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", path,
         os.path.join(board["dir"], board["project"] + ".kicad_sch")])
    return path


def bom_cpl(board, out_dir, name):
    """BOM (Comment, Designator, Footprint, LCSC Part #) and CPL (Designator, Mid X, Mid Y, Layer, Rotation) for
    populated parts only; positions from kicad-cli pos export (aux origin = bottom-left, y up, mm)."""
    pcb = os.path.join(board["dir"], board["project"] + ".kicad_pcb")
    net_xml = export_netlist(board, out_dir)
    comps, nets, pad_net = netlist.read(net_xml)
    os.remove(net_xml)
    pos_csv = os.path.join(out_dir, "_pos.csv")
    run([KICAD_CLI, "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "--use-drill-file-origin",
         "--exclude-dnp", "-o", pos_csv, pcb])
    positions = {}
    with open(pos_csv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            positions[row["Ref"]] = row
    os.remove(pos_csv)
    groups = {}
    cpl_rows = []
    skipped = []
    hand = []
    for ref, c in sorted(comps.items(), key=lambda kv: (kv[0][0], int("".join(ch for ch in kv[0][1:] if ch.isdigit()) or 0))):
        if c.fields.get("Assembly", "").lower() == "hand":
            # bought separately and soldered by hand (Decision #73: such parts are also DNP and excluded
            # from the BOM in the schematic): never in the JLC BOM or CPL, always on the hand list
            hand.append([ref, c.value, c.footprint.split(":")[-1], c.fields.get("MPN", ""),
                         c.fields.get("Purchase", "") or c.fields.get("LCSC", "")])
            continue
        if c.dnp or not c.in_bom:
            skipped.append((ref, "DNP" if c.dnp else "not in BOM"))
            continue
        if not c.lcsc:
            skipped.append((ref, "NO LCSC NUMBER"))
        key = (c.value, c.footprint.split(":")[-1], c.lcsc)
        groups.setdefault(key, []).append(ref)
        p = positions.get(ref)
        if p is None:
            skipped.append((ref, "no position (pos export)"))
            continue
        cpl_rows.append([ref, "%.4f" % float(p["PosX"]), "%.4f" % float(p["PosY"]), "Top" if p["Side"].lower().startswith("top") else "Bottom", "%.1f" % float(p["Rot"])])
    with open(os.path.join(out_dir, name + "-bom.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (value, fp, lcsc), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
            w.writerow([value, ",".join(refs), fp, lcsc])
    with open(os.path.join(out_dir, name + "-cpl.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        w.writerows(cpl_rows)
    with open(os.path.join(out_dir, name + "-hand-solder.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Value", "Footprint", "MPN", "LCSC (suggestion)"])
        w.writerows(hand)
    return len(groups), len(cpl_rows), skipped, hand


def export_board(name, board, rel):
    out = os.path.join(rel, name)
    os.makedirs(os.path.join(out, "gerbers"), exist_ok=True)
    os.makedirs(os.path.join(out, "reports"), exist_ok=True)
    pcb = os.path.join(board["dir"], board["project"] + ".kicad_pcb")
    sch = os.path.join(board["dir"], board["project"] + ".kicad_sch")
    # gerbers + drill (aux origin)
    run([KICAD_CLI, "pcb", "export", "gerbers", "--layers", board["layers"], "--subtract-soldermask", "--use-drill-file-origin",
         "--no-x2", "--no-netlist", "-o", os.path.join(out, "gerbers") + os.sep, pcb])
    run([KICAD_CLI, "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "--drill-origin", "plot",
         "--excellon-units", "mm", "--generate-map", "--map-format", "gerberx2", "-o", os.path.join(out, "gerbers") + os.sep, pcb])
    # BOM / CPL
    n_lines, n_parts, skipped, hand = bom_cpl(board, out, board["project"])
    # schematic PDF (whole hierarchy) and one PDF per referenced sheet
    run([KICAD_CLI, "sch", "export", "pdf", "-o", os.path.join(out, board["project"] + ".pdf"), sch])
    sheets = sub_sheets(board)
    if sheets:
        sdir = os.path.join(rel, "schematics")
        os.makedirs(sdir, exist_ok=True)
        for sh in sheets:
            run([KICAD_CLI, "sch", "export", "pdf", "-o", os.path.join(sdir, sh + ".pdf"), os.path.join(board["dir"], "sheets", sh + ".kicad_sch")])
    # readable layout exports
    for lay in board["views"]:
        svg = os.path.join(out, "%s-%s.svg" % (board["project"], lay.replace(".", "_")))
        run([KICAD_CLI, "pcb", "export", "svg", "--layers", "%s,Edge.Cuts" % lay, "--page-size-mode", "2", "--exclude-drawing-sheet", "-o", svg, pcb])
        try:
            import pymupdf
            doc = pymupdf.open(svg)
            doc[0].get_pixmap(matrix=pymupdf.Matrix(3, 3)).save(svg[:-4] + ".png")
        except Exception as e:  # pragma: no cover
            print("  (png render skipped: %s)" % e)
    # STEP
    # 3D models of the project libraries are addressed as ${TIGP_BOARD_LIB}/...; pass the variable so the export
    # does not depend on the KiCad preferences of whoever runs this (STEP siblings of the .wrl files are used)
    r = subprocess.run([KICAD_CLI, "pcb", "export", "step", "--subst-models", "--force",
                        "--define-var", "TIGP_BOARD_LIB=" + os.path.join(HW, "lib").replace(os.sep, "/"),
                        "-o", os.path.join(out, board["project"] + ".step"), pcb], capture_output=True, text=True)
    step_ok = r.returncode == 0 and os.path.exists(os.path.join(out, board["project"] + ".step"))
    step_note = (r.stdout + r.stderr)[-1500:]
    # ERC / DRC on the exact release revision
    run([KICAD_CLI, "sch", "erc", "--format", "json", "--severity-all", "-o", os.path.join(out, "reports", "erc.json"), sch])
    run([KICAD_CLI, "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--refill-zones",
         "-o", os.path.join(out, "reports", "drc.json"), pcb])
    erc = json.load(open(os.path.join(out, "reports", "erc.json"), encoding="utf-8"))
    drc = json.load(open(os.path.join(out, "reports", "drc.json"), encoding="utf-8"))
    erc_n = sum(len(s.get("violations", [])) for s in erc.get("sheets", []))
    drc_err = [v for v in drc["violations"] if v["severity"] == "error"]
    drc_warn = [v for v in drc["violations"] if v["severity"] == "warning"]
    unconn = drc.get("unconnected_items", [])
    # copy the editable design too (opens without external libraries: project-local lib tables)
    for f in glob.glob(os.path.join(board["dir"], board["project"] + ".kicad_*")) + glob.glob(os.path.join(board["dir"], "*-lib-table")):
        shutil.copy(f, out)
    if sheets:
        os.makedirs(os.path.join(out, "sheets"), exist_ok=True)
        for sh in sheets:
            shutil.copy(os.path.join(board["dir"], "sheets", sh + ".kicad_sch"), os.path.join(out, "sheets"))
    from collections import Counter
    summary = [
        "%s — release verification summary" % name,
        "board file: %s" % pcb,
        "ERC violations (severity-all): %d" % erc_n,
        "DRC errors: %d   warnings: %d   unconnected items: %d" % (len(drc_err), len(drc_warn), len(unconn)),
        "DRC warning types: %s" % dict(Counter(v["type"] for v in drc_warn)),
        "DRC error types: %s" % dict(Counter(v["type"] for v in drc_err)),
        "BOM lines: %d   CPL parts: %d   skipped (DNP / not in BOM / missing): %d" % (n_lines, n_parts, len(skipped)),
        "hand-soldered parts (Assembly = hand, own CSV, NOT in the JLC BOM/CPL): %d  %s" % (len(hand), [h[0] for h in hand]),
        "skipped: %s" % skipped,
        "STEP export: %s %s" % ("ok" if step_ok else "FAILED", "" if step_ok else step_note.replace("\n", " ")[:600]),
    ]
    with open(os.path.join(out, "reports", "summary.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(summary) + "\n")
    print("\n".join("  " + s for s in summary))
    return dict(erc=erc_n, drc_err=len(drc_err), drc_warn=len(drc_warn), unconnected=len(unconn), step_ok=step_ok, skipped=skipped)


def write_hashes(rel):
    for name in BOARDS:
        out = os.path.join(rel, name)
        if not os.path.isdir(out):
            continue
        lines = []
        for root, _, files in os.walk(out):
            for f in sorted(files):
                if f == "hashes.txt":
                    continue
                p = os.path.join(root, f)
                h = hashlib.sha256(open(p, "rb").read()).hexdigest()
                lines.append("%s  %s" % (h, os.path.relpath(p, out).replace(os.sep, "/")))
        with open(os.path.join(out, "hashes.txt"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


def main():
    rev = sys.argv[1] if len(sys.argv) > 1 else "revA"
    only = sys.argv[2] if len(sys.argv) > 2 else None
    rel = os.path.join(HW, "release", rev)
    os.makedirs(rel, exist_ok=True)
    results = {}
    for name, board in BOARDS.items():
        if only and name != only:
            continue
        print("==", name)
        results[name] = export_board(name, board, rel)
    write_hashes(rel)
    json.dump(results, open(os.path.join(rel, "verification.json"), "w", encoding="utf-8"), indent=2)
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
