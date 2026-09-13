"""Student "gapped" copies (brief 12, D6) — three sections A / B / C (v0.7, proposal 8.3).

One gapped copy per sheet a section owns:
    A (inputs + NMR receiver)     b1_inputs_gapped    nmr_rx_gapped
    B (outputs + timing + NMR TX) b3_outputs_gapped   b5_dio_trig_gapped   nmr_tx_gapped
    C (power switching + coil)    b4_switching_gapped c_switch_gapped
b2_power is NOT gapped: the instructor keeps the power-entry block (proposal 8.3 — it is the block a
student error would brick), so section C only places parts back on b4_switching and c_switch.

Each copy loses 3-4 *items* picked by the brief's rule (a decoupling pair, one repeated channel, one
connector).  The reference designators are unchanged in the full design, so a student who re-places
them with the same references keeps the footprint positions on *Update PCB from schematic*.

Writes  student/<sheet>_gapped.kicad_sch (+ .kicad_pro, + the two library tables)
        docs/student-deletions.md   (with the measured "expected ERC items" per sheet)

Run from the project directory:  python scripts/gen_student.py        [--no-erc]
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
KICAD_CLI = os.environ.get("KICAD_CLI", r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")

# section -> (long name, JLC-library part the section fetches itself, sheets)
# sheet   -> (sheet file, [(what it is, [references], where to find it on the full PDF)])
SECTIONS = [
    ("A", "inputs + NMR receiver",
     ("OPA1656IDR", "C1849431", "SOIC-8", "the LNA op-amp U703 on the NMR RX sheet"),
     [
         ("b1_inputs", [
             ("one complete AI4 input network (the repeated channel: 1 k series, 1 nF, BAV99 clamp)",
              ["R114", "C114", "D114"],
              "B1 sheet, input column 4 (AI4), between the terminal and the ADS8688 pin"),
             ("the ADS8688 AVDD decoupling pair",
              ["C101", "C102"],
              "B1 sheet, at the ADS8688 AVDD pin (top-left of U101)"),
         ]),
         ("nmr_rx", [
             ("the LNA (U703 OPA1656) +-12 V decoupling pair",
              ["C722", "C723"],
              "NMR RX sheet, block 1 (rails/decoupling strip), the C722-C727 row"),
             ("one of the two crossed limiter diodes at the RX connector",
              ["D703"],
              "NMR RX sheet, block 2 (receiver), at the RX pin next to D704"),
             ("one IF RC pole (Q path), R911 + C911",
              ["R911", "C911"],
              "NMR RX sheet, block 4 (mixer/IF), the passive 15.9 kHz pole after U901/U902"),
         ]),
     ]),
    ("B", "outputs + timing + NMR transmitter",
     ("AD9834BRUZ", "C116589", "TSSOP-20", "the DDS U801 on the NMR TX sheet"),
     [
         ("b3_outputs", [
             ("the AO2 difference-amplifier resistor set (the repeated channel)",
              ["R305", "R306", "R307", "R308"],
              "B3 sheet, AO2 half (lower), around the second OPA2192 section"),
             ("the AO2 output series resistor and its BAV99 clamp",
              ["R310", "D302"],
              "B3 sheet, AO2 output, between the op-amp and the AO2 terminal"),
         ]),
         ("b5_dio_trig", [
             ("the 74HCT125 fast-output channel parts (buffer + the two 49.9 R series resistors)",
              ["U502", "R509", "R510"],
              "B5 sheet, fast-output block (FAST1/FAST2)"),
             ("the buffer decoupling pair",
              ["C501", "C502"],
              "B5 sheet, at the 74AHCT541 (C501) and the 74HCT125 (C502) supply pins"),
             ("one TTL screw terminal (TTL1/TTL2)",
              ["J501"],
              "B5 sheet, fast-output block, the 2P terminal at the board edge"),
         ]),
         ("nmr_tx", [
             ("the OPA564 V+ decoupling pair (47 uF bulk + 100 nF)",
              ["C815", "C816"],
              "NMR TX sheet, power-stage block, at the OPA564 V+ pins"),
             ("the output clamp diode to GND",
              ["D802"],
              "NMR TX sheet, power-stage output node, below D801"),
             ("the output isolation resistor",
              ["R813"],
              "NMR TX sheet, between the clamp node and C818 / the TX SMA"),
         ]),
     ]),
    ("C", "power switching + coil drive",
     ("DRV8871DDAR", "C75864", "SOIC-8 (PowerPAD)", "the H-bridge U903 on the coil-switch sheet"),
     [
         ("b4_switching", [
             ("one complete relay channel (relay, coil-on LED, 2.2 k LED resistor)",
              ["K401", "D411", "R421"],
              "B4 sheet, relay channel 1 (leftmost of the four)"),
             ("that channel's 3P screw terminal (NO / COM / NC)",
              ["J401"],
              "B4 sheet, relay channel 1, at the board edge"),
             ("one isolated-input current limiter (series diode, 220 R, 10 k bias, the two MMBT5551 "
              "and their 100 R / 1 k emitter set)",
              ["D421", "R431", "R441", "Q411", "Q421", "R451", "R461"],
              "B4 sheet, isolated input 1 (lower left), between J411 and the 6N137 U401"),
         ]),
         ("c_switch", [
             ("the external-input TVS",
              ["D931"],
              "C sheet, external power input row: J901 -> F901 -> D931 -> Q901"),
             ("the external-input fuse",
              ["F901"],
              "C sheet, external power input row, between J901 and the TVS"),
             ("one H-bridge input pull-down (IN2 = coast at reset)",
              ["R922"],
              "C sheet, DRV8871 block, at the U903 IN1/IN2 pins next to R921"),
         ]),
     ]),
]


# ------------------------------------------------------------------ s-expression surgery
def split_symbols(text):
    """yield (chunk, ref) for every top-level (symbol ...) block; ref is None for the gaps between"""
    i, n = 0, len(text)
    while i < n:
        j = text.find("\n  (symbol ", i)
        if j < 0:
            yield text[i:], None
            return
        yield text[i:j], None
        k, depth = j + 1, 0
        while k < n:
            ch = text[k]
            if ch == '"':
                k = text.find('"', k + 1) + 1
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    k += 1
                    break
            k += 1
        block = text[j:k]
        m = re.search(r'\(property "Reference" "([^"]+)"', block)
        yield block, (m.group(1) if m else None)
        i = k


def delete_symbols(text, refs, lcsc_by_symbol):
    out, removed, info = [], [], {}
    for block, ref in split_symbols(text):
        if ref is not None and ref in refs:
            removed.append(ref)
            info[ref] = prop_info(block, lcsc_by_symbol)
        else:
            out.append(block)
    return "".join(out), removed, info


def prop_info(block, lcsc_by_symbol):
    def p(name):
        m = re.search(r'\(property "%s" "([^"]*)"' % name, block)
        return m.group(1) if m else ""
    fp = p("Footprint")
    m = re.search(r"(C\d{3,})", p("Datasheet"))
    lcsc = m.group(1) if m else ""
    if not lcsc:                                  # instance carries no part number -> ask the library
        s = re.search(r'\(lib_id "[^":]*:?([^"]+)"', block)
        lcsc = lcsc_by_symbol.get(s.group(1), "") if s else ""
    return {"value": p("Value"), "footprint": fp.split(":")[-1], "lcsc": lcsc,
            "descr": p("Description")}


def lcsc_from_library():
    """symbol name -> LCSC part number, from lib/class_board.kicad_sym"""
    path = os.path.join(HW, "lib", "class_board.kicad_sym")
    if not os.path.exists(path):
        return {}
    t = open(path, encoding="utf-8").read()
    out, name = {}, None
    for m in re.finditer(r'\n  \(symbol "([^"]+)"|\(property "LCSC" "([^"]*)"', t):
        if m.group(1):
            name = m.group(1)
        elif name and name not in out:
            out[name] = m.group(2)
    return out


# ------------------------------------------------------------------ ERC
def erc_counts(sch, workdir):
    """-> (total violations, {type: n}) for one standalone schematic file, or None if kicad-cli fails"""
    out = os.path.join(workdir, os.path.basename(sch) + ".erc.json")
    r = subprocess.run([KICAD_CLI, "sch", "erc", "--severity-all", "--format", "json", "-o", out, sch],
                       capture_output=True, text=True)
    if not os.path.exists(out):
        print("  ERC failed on %s: %s" % (sch, (r.stderr or r.stdout).strip()[:200]))
        return None
    data = json.load(open(out, encoding="utf-8"))
    by = {}
    for s in data.get("sheets", []):
        for v in s.get("violations", []):
            by[v["type"]] = by.get(v["type"], 0) + 1
    return sum(by.values()), by


def lib_tables(folder, uri_prefix):
    for name, kind in (("sym-lib-table", "sym"), ("fp-lib-table", "fp")):
        ext = "kicad_sym" if kind == "sym" else "pretty"
        with open(os.path.join(folder, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write('(%s_lib_table\n  (version 7)\n  (lib (name "class_board")(type "KiCad")'
                     '(uri "%s/lib/class_board.%s")(options "")(descr "shared class-board library"))\n)\n'
                     % (kind, uri_prefix, ext))


def sheet_pages():
    """sheet file stem -> (page number in the full schematic, sheet title)"""
    root = open(os.path.join(HW, "class-board.kicad_sch"), encoding="utf-8").read()
    pages = {}
    for m in re.finditer(r'\(property "Sheetfile" "sheets/([^".]+)\.kicad_sch"(?:.|\n)*?\(page "(\d+)"\)', root):
        pages[m.group(1)] = m.group(2)
    out = {}
    for stem, page in pages.items():
        t = open(os.path.join(HW, "sheets", stem + ".kicad_sch"), encoding="utf-8").read(4000)
        m = re.search(r'\(title "([^"]*)"', t)
        out[stem] = (page, m.group(1) if m else stem)
    return out


# ------------------------------------------------------------------ main
def main():
    do_erc = "--no-erc" not in sys.argv
    sdir = os.path.join(HW, "student")
    os.makedirs(sdir, exist_ok=True)
    for f in sorted(os.listdir(sdir)):                       # drop the old five-block copies
        if "_gapped." in f:
            os.remove(os.path.join(sdir, f))
            print("removed stale %s" % f)
    lib_tables(sdir, "${KIPRJMOD}/..")
    pages = sheet_pages()
    lcsc_by_symbol = lcsc_from_library()
    pro_src = json.load(open(os.path.join(HW, "class-board.kicad_pro"), encoding="utf-8"))

    tmp = tempfile.mkdtemp(prefix="cb_erc_")
    lib_tables(tmp, HW.replace("\\", "/"))
    base_erc = {}

    results = []
    for sec, secname, fetch, sheets in SECTIONS:
        for stem, groups in sheets:
            src = os.path.join(HW, "sheets", stem + ".kicad_sch")
            text = open(src, encoding="utf-8").read()
            refs = [r for _, rs, _ in groups for r in rs]
            new, removed, info = delete_symbols(text, set(refs), lcsc_by_symbol)
            missing = sorted(set(refs) - set(removed))
            assert not missing, "%s: references not found: %s" % (stem, missing)
            new = new.replace('(title_block (title "',
                              '(title_block (title "STUDENT COPY (section %s, gapped) - ' % sec, 1)
            dst = os.path.join(sdir, "%s_gapped.kicad_sch" % stem)
            with open(dst, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(new)
            pro = dict(pro_src)
            pro["meta"] = dict(pro_src["meta"], filename="%s_gapped.kicad_pro" % stem)
            with open(os.path.join(sdir, "%s_gapped.kicad_pro" % stem), "w",
                      encoding="utf-8", newline="\n") as fh:
                json.dump(pro, fh, indent=2)
            print("%s / %s: removed %d symbols -> student/%s_gapped.kicad_sch"
                  % (sec, stem, len(removed), stem))

            erc = None
            if do_erc:
                if stem not in base_erc:
                    b = os.path.join(tmp, stem + ".kicad_sch")
                    shutil.copyfile(src, b)
                    json.dump(dict(pro_src, meta=dict(pro_src["meta"], filename=stem + ".kicad_pro")),
                              open(os.path.join(tmp, stem + ".kicad_pro"), "w", encoding="utf-8"), indent=2)
                    base_erc[stem] = erc_counts(b, tmp)
                g = erc_counts(dst, tmp)
                if base_erc[stem] and g:
                    bt, bby = base_erc[stem]
                    gt, gby = g
                    delta = {k: gby.get(k, 0) - bby.get(k, 0) for k in set(bby) | set(gby)
                             if gby.get(k, 0) != bby.get(k, 0)}
                    erc = (bt, gt, delta)
                    print("     ERC standalone: full sheet %d, gapped %d, new %+d  %s"
                          % (bt, gt, gt - bt, delta))
            results.append((sec, secname, fetch, stem, groups, info, erc))
    shutil.rmtree(tmp, ignore_errors=True)
    write_doc(results, pages, do_erc)


def write_doc(results, pages, did_erc):
    L = []
    w = L.append
    w("# Student gapped copies — what each section places back (brief §12, D6; v0.7 three sections)\n")
    w("Generated by `scripts/gen_student.py` from the released sheets in `sheets/`. Do not edit by hand.\n")
    w("The design is built complete, then 3–4 items are deleted per sheet (a decoupling pair, one repeated")
    w("channel, one connector — brief §12). **The reference designators are unchanged in the full design**, so a")
    w("student who re-places a part with the same reference gets the same footprint position back on *Update PCB")
    w("from schematic*. Wires, labels and power symbols of the deleted parts stay in place — the dangling ends")
    w("are the intended ERC findings.\n")
    w("## Sections (v0.7 — `notes/2026-09-13-nmr-respec-proposal.md` §8.3)\n")
    w("| Section | Scope | Gapped sheets to complete | Part to fetch from the JLC library |")
    w("|---|---|---|---|")
    seen = []
    for sec, secname, fetch, stem, _g, _i, _e in results:
        if sec not in [s[0] for s in seen]:
            seen.append((sec, secname, fetch, []))
        seen[[s[0] for s in seen].index(sec)][3].append(stem)
    for sec, secname, fetch, stems in seen:
        w("| **%s** | %s | %s | **%s** (%s, %s) — %s |"
          % (sec, secname, ", ".join("`student/%s_gapped.kicad_sch`" % s for s in stems),
             fetch[0], fetch[1], fetch[2], fetch[3]))
    w("")
    w("`b2_power` is **not** gapped. The instructor keeps the power-entry block (proposal §8.3: it is the block a")
    w("student mistake would brick), so section C places parts back on `b4_switching` and `c_switch` only.\n")
    w("Each section also adds its one JLC-library part: fetch the symbol + footprint with the JLC/LCSC part number")
    w("above, check the pin numbering and the footprint against the datasheet, and commit it to `lib/class_board`.")
    w("The part is already used in the full design — the exercise is the library entry, not the placement.\n")
    w("## What is missing from each sheet\n")
    for sec, secname, fetch, stem, groups, info, erc in results:
        page, title = pages.get(stem, ("?", stem))
        w("### Section %s — `student/%s_gapped.kicad_sch`" % (sec, stem))
        w("")
        w("Full schematic PDF: **page %s**, *%s* (`docs/schematic-full.pdf`).\n" % (page, title))
        w("| Ref | Value | Footprint | LCSC | Item | Where on the full PDF |")
        w("|---|---|---|---|---|---|")
        for what, refs, where in groups:
            for n, r in enumerate(refs):
                d = info[r]
                w("| **%s** | %s | %s | %s | %s | %s |"
                  % (r, d["value"], d["footprint"], d["lcsc"] or "—",
                     what if n == 0 else "〃", where if n == 0 else "〃"))
        w("")
        if erc:
            base, gap, delta = erc
            w("Expected ERC items: **%d new** (standalone ERC on the sheet: %d on the full sheet, %d on the gapped"
              % (gap - base, base, gap))
            w("copy, `--severity-all`)%s" % ("." if not delta else " —"))
            if delta:
                w("")
                for k in sorted(delta):
                    w("- `%s` %+d%s" % (k, delta[k],
                                        "  (fewer — the deleted symbol took its own pins with it)"
                                        if delta[k] < 0 else ""))
            w("")
            w("These are the unconnected pins and dangling wire/label ends left where the parts were removed, and")
            w("they disappear when the parts are placed back. Any *other* ERC item is the student's own.\n")
        elif did_erc:
            w("Expected ERC items: not measured (kicad-cli ERC failed on this sheet).\n")
    w("## How the counts were taken\n")
    w("```")
    w('"C:\\Program Files\\KiCad\\10.0\\bin\\kicad-cli.exe" sch erc --severity-all --format json \\')
    w("      -o <out>.json  student/<sheet>_gapped.kicad_sch")
    w("```")
    w("ERC is run on the sheet **standalone** (not through the root schematic), so the baseline is high: every")
    w("hierarchical/global label that leaves the sheet reads as dangling, and every power input looks undriven.")
    w("Only the *difference* against the same sheet ungapped is meaningful, and that difference is the table above.\n")
    w("## PDFs\n")
    w("```")
    w('"C:\\Program Files\\KiCad\\10.0\\bin\\kicad-cli.exe" sch export pdf -o docs\\schematic-full.pdf class-board.kicad_sch')
    w("```")
    w("`kicad-cli` has no per-sheet option for a hierarchical design — `sch export pdf` always writes the whole")
    w("book. `docs/schematic-full.pdf` is therefore the single reference document; the page number in each table")
    w("above is the sheet's page in it. (Running `sch export pdf` on a file in `sheets/` does produce a one-page")
    w("PDF, but standalone — without the root sheet's page numbering and cross-references — so it is not used.)")
    with open(os.path.join(HW, "docs", "student-deletions.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote docs/student-deletions.md")


if __name__ == "__main__":
    main()
