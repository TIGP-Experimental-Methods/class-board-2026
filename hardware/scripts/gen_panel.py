"""Generate the front-panel project (D4): hardware/front-panel/front-panel.kicad_{sch,pro,pcb}, 2-layer 180 x 65 mm.

Panel coordinates in the design brief (7.8) are x right, y UP from the bottom edge; KiCad y = 65 - y_panel.
The 2x20 straight female header sits on the BACK of the panel (B.Cu), mating with the main board's right-angle
male J6.  Seen from the front, male pin 1 is at x = 45.87 mm in the lower row; a back-side footprint is mirrored, so
the female pad numbers are swapped pairwise: panel J1 pad 2k-1 <-> link pin 2k, pad 2k <-> link pin 2k-1.  The
mapping is asserted geometrically below (same x, same row => same net).

Spec v0.7 (2026-09-13): panel 180 x 65 mm (main board grows to 180 x 100 on the right-hand side; the link
connector stays centred at main-board x = 70, so the panel header keeps its x relative to the left edge).
SMA grid is 3 x 5 at 20 mm pitch (columns 50/70/90/110/130), the new column carries TX, RX and SPARE.
Link pins 37-40 are now RX / AGND / TX / AGND (+5V_RAW no longer reaches the panel).

Run from hardware/scripts:  python gen_panel.py [--no-route]
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_sch                                   # noqa: E402
import netlist                                   # noqa: E402
from cb_sch import Sheet                         # noqa: E402
from fp_parse import load_library                # noqa: E402
from gen_sch import Ctx, LINK, auto_junctions, split_wires_at_pins   # noqa: E402
from pcb_model import Board, FootprintInst       # noqa: E402
from sexp import uid, uid_for                             # noqa: E402
import gen_pcb                                   # noqa: E402

HW = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FP_DIR = os.path.join(HW, "front-panel")
PROJECT = "front-panel"
W, H = 180.0, 65.0
KICAD_CLI = os.environ.get("KICAD_CLI", "C:/Program Files/KiCad/10.0/bin/kicad-cli.exe")

# v0.7 link pinout: 37-40 carry the NMR coil ports RX/TX (with AGND) instead of +5V_RAW/GND/n-c/n-c.  gen_sch.LINK (main board) is owned by
# gen_sch.py; the panel keeps its own copy so the two can be updated independently, and warns if they disagree.
LINK_V07 = {37: "RX", 38: "AGND", 39: "TX", 40: "AGND"}
PANEL_LINK = dict(LINK)
PANEL_LINK.update(LINK_V07)

SMA_COLS_X = [50.0, 70.0, 90.0, 110.0, 130.0]   # 20 mm pitch, 5 columns (v0.7)
SMA_ROWS_PANEL_Y = [54.0, 34.0, 14.0]           # brief: top-left at (60, 45); moved up 9 mm so row 3 clears the link header (D-26)
SMA_NETS = [["AO1", "AO2", "TRIG_5V", "AUX", "TX"],
            ["AI1", "AI2", "AI3", "AI4", "RX"],
            ["AI5", "AI6", "AI7", "AI8", "SPARE"]]
SMA_LABELS = [["AO1", "AO2", "TRIG", "AUX", "TX"],
              ["AI1", "AI2", "AI3", "AI4", "RX"],
              ["AI5", "AI6", "AI7", "AI8", "SPARE"]]
LINK_X = 70.0                                   # header centre x (same as the main board J6, unchanged by the 160 mm outline)
LINK_ROW_Y = 65.0 - 4.77                        # KiCad y of the header centre: rows at 4.77 +- 1.27 mm above the bottom edge
LED_Y_PANEL = [62.0, 57.0, 52.0]                # PWR, WIFI, ACT
OLED_X, OLED_Y_PANEL = 20.0, 44.0
SMA_REF0 = 2                                    # J2..J16 = SMA grid, row-major; J17 = OLED socket
OLED_REF = "J%d" % (SMA_REF0 + 15)
SPARE_TP_XY = (140.0, 51.0)                     # test pad for the SPARE SMA centre pin (KiCad coords)


def ky(y_panel):
    return H - y_panel


def sma_ref(row, col):
    return "J%d" % (SMA_REF0 + row * len(SMA_COLS_X) + col)


def mate(p):
    """link pin that faces female pad p (mirrored back-side footprint)"""
    return p + 1 if p % 2 else p - 1


def check_link_table():
    diff = [p for p in LINK_V07 if LINK.get(p) != LINK_V07[p]]
    if diff:
        print("NOTE: gen_sch.LINK still has the pre-v0.7 pinout on pins %s (%s); the panel uses %s."
              % (sorted(diff), {p: LINK.get(p) for p in sorted(diff)}, {p: LINK_V07[p] for p in sorted(diff)}))
        print("      Apply scratchpad/panel_gen_sch_patch.py to the main-board generator to make them agree.")


# ------------------------------------------------------------------ schematic
def build_sheet():
    sh = Sheet("front-panel", "TIGP class board 2026 - front panel", "A3", 1,
               "15 SMA on a 20 mm grid, OLED 1x4 socket, 3 LEDs, 2x20 female link (back side)")
    c = Ctx(sh, "PANEL", 100)
    sh.box(10, 10, 400, 280, "FRONT PANEL - 2-layer 180 x 65 mm; copper = AGND, joined to GND only through the main-board star")
    sh.text("J1 is mounted on the BACK of the panel: female pad 2k-1 mates with link pin 2k and pad 2k with link pin 2k-1 (mirrored footprint). Net names follow the link pins (brief 7.8, v0.7 pins 37-40).", 14, 16, 1.3)
    sh.text("TRIG: 5 V into open circuit, about 2.4 V into 50 ohm (74LVC1T45 + 33 ohm). AI1..AI8 +-10 V, 1 kOhm series on the main board. AO1/AO2 +-10 V, 49.9 ohm back-terminated.", 14, 20, 1.3)
    sh.text("RX (link pin 37) = NMR receive coil into the LNA (section A); TX (link pin 39) = NMR transmit coil from the OPA564 stage (section B); AGND on pins 38/40 beside them. SPARE: SMA shield to AGND, centre pin to test pad TP1 only.", 14, 24, 1.3)
    # link header
    J = c.place("J1", "HDR_2x20_FEMALE", 60, 110, 0)
    for pad in range(1, 41):
        net = PANEL_LINK.get(mate(pad))
        if net is None:
            c.nc_pin(J, str(pad))
        elif net in ("GND", "AGND", "+3V3", "+5V_RAW"):
            c.pwr_pin(J, str(pad), net, 7.62 if (pad // 2) % 2 else 12.7)
        else:
            c.glabel_pin(J, str(pad), net, 7.62)
    # SMAs
    for r, row in enumerate(SMA_NETS):
        for k, net in enumerate(row):
            S = c.place(sma_ref(r, k), "BWSMA-KE-Z001", 160 + 48 * k, 50 + 60 * r, 0)
            c.glabel_pin(S, "5", net, 7.62)
            for leg in ("1", "2", "3", "4"):
                c.pwr_pin(S, leg, "AGND", 5.08)
            sh.text("panel label: %s" % SMA_LABELS[r][k], 152 + 48 * k, 72 + 60 * r, 1.1)
    # test pad for the SPARE centre pin (nothing else on the net)
    TP = c.place("TP1", "TestPoint", 160 + 48 * 4, 212, 0)
    c.glabel_pin(TP, "1", "SPARE", 5.08)
    sh.text("SPARE SMA: fitted, shield to AGND, centre pin to TP1 only (no link pin)", 280, 222, 1.1)
    # OLED socket
    O = c.place(OLED_REF, "HDR_1x4_FEMALE", 60, 200, 0)
    c.pwr_pin(O, "1", "GND", 7.62)
    c.pwr_pin(O, "2", "+3V3", 7.62)
    c.glabel_pin(O, "3", "I2C_SCL", 7.62)
    c.glabel_pin(O, "4", "I2C_SDA", 7.62)
    sh.text("0.96in I2C OLED module (GND VCC SCL SDA), address 0x3C, hangs below the socket", 40, 214, 1.2)
    # LEDs (row pitch 17.78 mm and a 5.08 mm label stub keep each R pin 2 clear of the next row's label wire;
    # the R-D node carries a local label because kicad-cli 10.0.3 omits UNNAMED nets from the kicadxml netlist,
    # which would leave the LED anodes without a net - and therefore unrouted - on the board)
    sh.text("LED_PWR = +3V3 from the link (pin 31); 1 k series -> ~1 mA", 100, 228, 1.1)
    for i, (sig, colour) in enumerate([("LED_PWR", "LED_GREEN_0805"), ("LED_WIFI", "LED_YELLOW_0603"), ("LED_ACT", "LED_GREEN_0805")]):
        y = 232 + 17.78 * i
        R = c.place("R%d" % (i + 1), "R0603_1k", 60, y, 0)
        D = c.place("D%d" % (i + 1), colour, 85, y, 0)
        c.glabel_pin(R, "1", sig, 5.08)
        sh.wire_pins(R, "2", D, "2")
        sh.label(sig + "_A", 70, R.pin_pos("2")[1], 0, "local")
        c.pwr_pin(D, "1", "GND", 5.08)
    # power flags (the link pins are passive); +5V_RAW no longer reaches the panel (v0.7)
    for i, net in enumerate(["+3V3", "GND", "AGND"]):
        x = 300 + 20 * i
        c.flag(x, 240, 0)
        c.power_at(x, 245.08, net, 0)
        sh.wire(x, 240, x, 245.08)
    # mechanical
    for i in range(4):
        Hh = c.place("H%d" % (i + 1), "MountingHole", 300 + 20 * i, 262, 0)
        for pin in Hh.pins():
            c.nc_pin(Hh, pin)
    for i in range(2):
        F = c.place("FID%d" % (i + 1), "Fiducial", 380 + 15 * i, 262, 0)
        for pin in F.pins():
            c.nc_pin(F, pin)
    split_wires_at_pins(sh)
    auto_junctions(sh)
    return sh


def write_schematic():
    os.makedirs(FP_DIR, exist_ok=True)
    root_uuid = uid_for("root:" + PROJECT)
    sh = build_sheet()
    sh.write(os.path.join(FP_DIR, PROJECT + ".kicad_sch"), PROJECT, root_uuid, "/" + root_uuid)
    gen_sch.write_project(os.path.join(FP_DIR, PROJECT + ".kicad_pro"))
    pro = json.load(open(os.path.join(FP_DIR, PROJECT + ".kicad_pro"), encoding="utf-8"))
    pro["meta"]["filename"] = PROJECT + ".kicad_pro"
    pro["text_variables"] = {"REV": "B", "BOARD": "TIGP class board 2026 front panel"}
    json.dump(pro, open(os.path.join(FP_DIR, PROJECT + ".kicad_pro"), "w", encoding="utf-8", newline="\n"), indent=2)
    for name, uri, kind in (("sym-lib-table", "${KIPRJMOD}/../lib/class_board.kicad_sym", "sym"), ("fp-lib-table", "${KIPRJMOD}/../lib/class_board.pretty", "fp")):
        with open(os.path.join(FP_DIR, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write('(%s_lib_table\n  (version 7)\n  (lib (name "class_board")(type "KiCad")(uri "%s")(options "")(descr "shared class-board library"))\n)\n' % (kind, uri))
    with open(os.path.join(FP_DIR, PROJECT + ".kicad_dru"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write('''(version 1)
# front panel: 2-layer, AGND copper; generic manufacturing margins (JLC 2-layer: 0.127/0.127 mm, drill 0.3 mm)
(rule "analog_in_clearance"
	(condition "A.NetClass == 'ANALOG_IN' && A.Type == 'Track' && B.NetName != 'AGND'")
	(constraint clearance (min 0.3mm)))
(rule "hole_to_hole"
	(constraint hole_to_hole (min 0.5mm))
	(condition "A.Type == 'Via' || A.Type == 'Pad'"))
(rule "annular_ring"
	(constraint annular_width (min 0.15mm))
	(condition "A.Type == 'Via'"))
(rule "copper_to_edge"
	(constraint edge_clearance (min 0.3mm)))
''')
    return sh


def export_netlist():
    out = os.path.join(FP_DIR, ".netlist.xml")
    subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", out, os.path.join(FP_DIR, PROJECT + ".kicad_sch")], check=True)
    return out


# ------------------------------------------------------------------ board
def placement():
    P = {}

    def put(ref, x, y, rot=0, side="F.Cu"):
        P[ref] = (round(x, 3), round(y, 3), rot, side)

    for ref, (x, y) in zip(("H1", "H2", "H3", "H4"), ((4, 4), (W - 4, 4), (4, H - 4), (W - 4, H - 4))):
        put(ref, x, y)
    put("FID1", 12, 46); put("FID2", 168, 21)
    put("J1", LINK_X, LINK_ROW_Y, 0, "B.Cu")
    for r, ypanel in enumerate(SMA_ROWS_PANEL_Y):
        for k, x in enumerate(SMA_COLS_X):
            put(sma_ref(r, k), x, ky(ypanel), 0)
    put("TP1", SPARE_TP_XY[0], SPARE_TP_XY[1], 0)
    put(OLED_REF, OLED_X, ky(OLED_Y_PANEL), 0)
    for i, yp in enumerate(LED_Y_PANEL):
        put("D%d" % (i + 1), 20.0, ky(yp), 0)
        put("R%d" % (i + 1), 26.5, ky(yp), 0)
    return P


def build(route=True):
    comps, nets, pad_net = netlist.read(os.path.join(FP_DIR, ".netlist.xml"))
    lib = load_library(os.path.join(HW, "lib", "class_board.pretty"))
    P = placement()
    missing = [r for r in comps if r not in P]
    assert not missing, "unplaced: %s" % missing
    board = Board(layers=2, title="TIGP class board 2026 - front panel", height=H)
    for ref, comp in sorted(comps.items()):
        fp = lib[comp.footprint.split(":")[1]]
        x, y, rot, side = P[ref]
        nets_by_pad = {}
        for pad in fp.pads:
            nn = pad_net.get((ref, pad.number))
            if nn:
                nets_by_pad[pad.number] = nn
                board.net(nn)
        cdict = dict(value=comp.value, datasheet=comp.datasheet, description=comp.description,
                     fields={k: v for k, v in comp.fields.items() if k not in ("Reference", "Value")},
                     path=comp.path, sheetname=comp.sheetname, sheetfile=comp.sheetfile, dnp=comp.dnp, in_bom=comp.in_bom)
        board.add_footprint(FootprintInst(ref, fp, x, y, rot, cdict, nets_by_pad, side=side))
    board.gr_rect(0, 0, W, H, "Edge.Cuts", 0.1)
    full = [(0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)]
    board.zone("AGND", ["F.Cu"], full, priority=0, name="AGND_F", clearance=0.3, pad_connect="solid")
    board.zone("AGND", ["B.Cu"], full, priority=0, name="AGND_B", clearance=0.3, pad_connect="solid")
    # silkscreen
    board.gr_text("TIGP CLASS BOARD 2026   FRONT PANEL   rev B", 90.0, 3.0, size=1.5, thickness=0.2)
    for r, ypanel in enumerate(SMA_ROWS_PANEL_Y):
        for k, x in enumerate(SMA_COLS_X):
            board.gr_text(SMA_LABELS[r][k], x, ky(ypanel) + 5.6, size=1.2, thickness=0.2)
    board.gr_text("AO: +-10 V   TRIG: 5 V TTL (~2.4 V into 50 ohm)   AUX: input to the conditioning chain", 90.0, 3.0 + 3.2, size=1.0, thickness=0.15)
    board.gr_text("AI1..AI8: +-10 V inputs, 1 kOhm series", 70.0, 63.0, size=1.0, thickness=0.15)
    board.gr_text("RX / TX: NMR coil ports (link 37 / 39)", 140.0, 40.0, size=1.0, thickness=0.15)
    board.gr_text("SPARE: TP1 only", 140.0, 46.0, size=1.0, thickness=0.15)
    board.gr_text("OLED 0.96in  GND VCC SCL SDA", 20.0, ky(OLED_Y_PANEL) - 2.6, size=1.0, thickness=0.15)
    for i, (lab, yp) in enumerate(zip(("PWR", "WIFI", "ACT"), LED_Y_PANEL)):
        board.gr_text(lab, 14.0, ky(yp), size=1.0, thickness=0.15)
    board.gr_text("LINK J1 on the back: pin 1 = left, lower row", 25.0, 56.6, size=1.0, thickness=0.15)
    gen_pcb.W, gen_pcb.H = W, H
    gen_pcb.place_reference_texts(board)
    if route:
        import router
        agnd = [(0.5, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (0.5, H - 0.5)]
        router.route_board(board, comps, nets, pad_net, W, H, agnd, ((500.0, 500.0), (501.0, 501.0)), plane_gnd=False,
                           stub_hint={"J1": (0, -1)},          # link pins escape upward, between the pins of the other row
                           layer_hint={"J1": 1}, layer_hint_net={"GND": 0},   # signals fan out on B.Cu, the GND pins on F.Cu
                           priority_file=os.path.join(FP_DIR, ".route_priority.json"))
    return board, comps, nets, pad_net


def check_link_mating(board, comps, pad_net):
    """geometric audit: every female pad must carry the net of the male pin at the same (x, row) — brief 7.8"""
    male = {}
    for n in range(1, 41):
        x, y = gen_pcb.link_pin(n)
        male[(round(x, 2), "low" if n % 2 else "up")] = (n, PANEL_LINK.get(n))
    J1 = next(f for f in board.footprints if f.ref == "J1")
    rows = sorted(set(round(p.y, 2) for p in J1.pads))
    assert len(rows) == 2
    errors = []
    for p in J1.pads:
        row = "low" if round(p.y, 2) == rows[1] else "up"     # larger KiCad y = nearer the bottom edge = lower row
        key = (round(p.x, 2), row)
        if key not in male:
            errors.append("pad %s at %s has no male pin" % (p.number, key))
            continue
        n, net = male[key]
        pnet = None if (not p.net or p.net.startswith("unconnected-")) else p.net
        if pnet != net:
            errors.append("pad %s @%s: panel net %s, link pin %d net %s" % (p.number, key, p.net, n, net))
    return errors


def print_link_table(board):
    """the link pinout as generated: main-board pin -> net -> panel pad (and where that pad sits)"""
    J1 = next(f for f in board.footprints if f.ref == "J1")
    pads = {p.number: p for p in J1.pads}
    print("\n link pin | net       | panel pad | panel x,y (mm)")
    for n in range(1, 41):
        p = pads.get(str(mate(n)))
        print("   %2d     | %-9s |    %2d     | %7.2f %6.2f" % (n, PANEL_LINK.get(n) or "n/c", mate(n), p.x, p.y))


def main():
    route = "--no-route" not in sys.argv
    check_link_table()
    write_schematic()
    export_netlist()
    board, comps, nets, pad_net = build(route)
    errs = check_link_mating(board, comps, pad_net)
    if errs:
        for e in errs:
            print("LINK MATING ERROR:", e)
        raise SystemExit(1)
    print("link mating audit: 40 pads match the main-board J6 pins")
    out = os.path.join(FP_DIR, PROJECT + ".kicad_pcb")
    board.write(out, PROJECT)
    print("wrote", out, "footprints", len(board.footprints), "nets", len(board.nets), "tracks", len(board.tracks), "vias", len(board.vias))
    print_link_table(board)


if __name__ == "__main__":
    main()
