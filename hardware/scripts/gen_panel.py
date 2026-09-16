"""Generate the front-panel project (D4 / D-50): front-panel/front-panel.kicad_{sch,pro,pcb}, 2 layers, 180 x 100 mm.

WHAT THE PANEL IS (Decisions #45-#49, notes/2026-09-14-panel-rework-proposal.md)
------------------------------------------------------------------------------
The panel lies flat on the BACK of the main board, parallel to it, carried by three straight 2x20
headers (male on the main board's bottom side, female on the panel's inner face) and four M3
stand-offs.  The panel's OUTER face is the instrument's front: 17 SMA, the OLED, three LEDs, the
10-way TTL screw-terminal strip, the TX coil terminal and a Qwiic socket.

COORDINATE CONVENTION  (read this before changing any number)
-------------------------------------------------------------
Main board: 180 x 100 mm, x right, y down as KiCad draws it; y = 0 is the REAR edge (USB-C, power
and relay terminals), y = 100 the front edge.  The three male headers sit on B.Cu.

Panel: also 180 x 100 mm and drawn with its OUTER face as F.Cu - that is, you look at the panel
from outside the instrument.  The panel is UNDER the main board, so looking at its outer face
means looking at the stack from the other side: one axis must be mirrored.  We mirror x:

        panel_x = 180 - main_x          panel_y = main_y                 (to_panel() below)

so the main board's rear edge (main y = 0) is also the panel's TOP edge (panel y = 0) as drawn,
which is what the "REAR / TOP EDGE" marker on the silkscreen says.  A consequence of the mirror:
the analog header J6 (main x = 12, left) becomes panel J1 at panel x = 168 (right), and the power
header J8 (main x = 168) becomes panel J3 at panel x = 12.

The female footprints are B.Cu (inner face).  KiCad's PinSocket footprint carries the mating
mirror in its own pad geometry (even pins at local x = -2.54, the header has them at +2.54), so
with the x mirror above the numbering comes out unchanged: panel pad k mates main pin k for all
120 pins.  check_link_mating() proves that from the pad coordinates rather than trusting it.

Run from the project root or from scripts/:   python gen_panel.py [--no-route]
"""
import json
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_sch                                   # noqa: E402
import netlist                                   # noqa: E402
from cb_sch import Sheet                         # noqa: E402
from fp_parse import Footprint, load_library     # noqa: E402
from gen_sch import Ctx, auto_junctions, split_wires_at_pins   # noqa: E402
from pcb_model import Board, FootprintInst       # noqa: E402
from sexp import uid_for                         # noqa: E402
import gen_pcb                                   # noqa: E402

HW = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FP_DIR = os.path.join(HW, "front-panel")
PROJECT = "front-panel"
W, H = 180.0, 100.0
KICAD_CLI = os.environ.get("KICAD_CLI", "C:/Program Files/KiCad/10.0/bin/kicad-cli.exe")
KICAD_FP = os.environ.get("KICAD_FP_DIR", "C:/Program Files/KiCad/10.0/share/kicad/footprints")

# ------------------------------------------------------------------ the main board's side of the link
# THESE NUMBERS MUST MATCH THE MASTER PCB (G:\Shared drives\...\TIGP-board_V0.7\class-board.kicad_pcb).
# They are the placement the instructor gives J6/J7/J8 on the main board; the panel is generated from
# them, so if the main board moves a header, change it here and re-run this script.
#   * side B.Cu (bottom), hand-soldered from the top
#   * MAIN_HEADERS values are the CENTRE of the 2x20 pad block, not the footprint anchor: the anchor
#     (what KiCad shows as "at") is printed by main_header_at() and in the report.
#   * rotation 180 with the KiCad standard footprint PinHeader_2x20_P2.54mm_Vertical puts the long
#     axis along y (the 50.8 mm block runs across the 100 mm direction, as the proposal asks) with
#     PIN 1 AT THE REAR (small y).  The footprint is already along y at rotation 0; "rotation 90"
#     would lay the header across the 180 mm direction, where J8 would hang off the board.
MAIN_W, MAIN_H = 180.0, 100.0
MAIN_HEADERS = {"J6": (12.0, 50.0), "J7": (90.0, 50.0), "J8": (168.0, 50.0)}
MAIN_HEADER_ROT = 180
MAIN_HEADER_FP = ("Connector_PinHeader_2.54mm", "PinHeader_2x20_P2.54mm_Vertical")
MAIN_HOLES = [(4.0, 4.0), (176.0, 4.0), (4.0, 96.0), (176.0, 96.0)]     # M3, same pattern on both boards

# panel ref -> main-board ref, pin dict (from gen_sch), what it carries
LINKS = [("J1", "J6", gen_sch.LINK_A, "analog"),
         ("J2", "J7", gen_sch.LINK_B, "digital"),
         ("J3", "J8", gen_sch.LINK_C, "power + spares")]
PANEL_HEADER_FP = ("Connector_PinSocket_2.54mm", "PinSocket_2x20_P2.54mm_Vertical")
PANEL_HEADER_ROT = 180

# ------------------------------------------------------------------ panel placement (panel coordinates, mm)
# Keep-outs: each female header occupies a band 5 mm wide and 51 mm tall on the inner face, but its
# pads are through-hole and therefore block BOTH faces - x = 12 / 90 / 168 +- 2.7 mm, y = 24.4..75.6.
# Everything with a hole or a pad must stay out of those bands.
SMA_COLS_X = [40.0, 60.0, 80.0, 100.0, 120.0, 140.0]   # proposal said 30..130; moved +10 mm so that
SMA_ROWS_Y = [25.0, 45.0, 65.0]                        # no column lands on the centre header at x = 90
SMA_NETS = [["AO1", "AO2", "TRIG_5V", "AUX", "TX", "FASTTTL1"],
            ["AI1", "AI2", "AI3", "AI4", "RX", "FASTTTL2"],
            ["AI5", "AI6", "AI7", "AI8", "SPARE", None]]       # None = the empty 18th position
SMA_LABELS = [["AO1", "AO2", "TRIG", "AUX", "TX", "FAST1"],
              ["AI1", "AI2", "AI3", "AI4", "RX", "FAST2"],
              ["AI5", "AI6", "AI7", "AI8", "SPARE", None]]
SMA_REF0 = 10                                   # J10..J26 row-major; J27 would be the empty position

OLED_REF = "J30"
# The OLED is ONE composite footprint, class_board:OLED-0.96in-4P-module-socket (user review 2026-09-17:
# the module must be fixed, and nothing may foul the header solder tails): the vertical 8.5 mm 1x4 socket
# that JLC places (anchor = centre of its pad row) plus the module's outline and its four M2 holes, so the
# module sits on four 11 mm M2 stand-offs and cannot drift from its socket.  The module PCB
# (27.3 x 27.8, panel x 148.8..176.1, y 9.0..36.8) overhangs the solder tails of J1 (x 165..171) with 8 mm
# of air: the PCB hangs 11 mm above the panel, the tails stand 3 mm.  No pad or hole of the footprint lies
# in J1's keep-out band (check_keepouts proves it); the right-hand M2 holes (x 174.2) clear J1's pads by
# 3 mm.  There is no 27 x 28 mm patch on the 180 x 100 panel that is free of BOTH the SMA field and a
# header band, so an overhang of the header tails is the price of the 20 mm SMA grid (Decision #22).
# Pin row 2.2 mm below the module's top edge; pin 1 = GND on the LEFT as seen from the front (the common
# GND-VCC-SCL-SDA module; a VCC-GND-SCL-SDA module must not be plugged in).
OLED_AT = (162.45, 11.2, 0)
# Screw terminals flush with the panel's bottom edge, wire entry off the edge (user, 2026-09-17: "the
# terminal blocks should be at the edge of the front panel allowing the wires to enter from the sides").
# Both KF128 footprints draw their wire openings on the +y side, so rotation 0 faces the bottom edge
# (y = 100); the body silk stops 0.3 mm short of the edge.
TTL_REF, TTL_AT = "J31", (33.0, 96.2, 0)        # KF128-2.54-10P: TTL1..TTL8, GND, GND (silk to y 99.6)
TX_REF, TX_AT = "J32", (120.0, 94.4, 0)         # KF128-5.0-2P: TX coil, below the TX SMA column (silk to y 99.7)
QWIIC_REF, QWIIC_AT = "J33", (150.0, 88.0, 0)   # vertical JST-SH
LED_X = [148.0, 155.0, 162.0]                   # PWR, WIFI, ACT
LED_Y, RES_Y = 50.0, 57.0
TP1_AT = (128.0, 72.0)                          # test pad for the SPARE SMA centre pin
FID_AT = [(20.0, 8.0), (160.0, 95.0)]

TITLE = "TIGP CLASS BOARD 2026   FRONT PANEL   rev B   180 x 100"


def to_panel(x, y):
    """main-board coordinates -> panel coordinates (the panel is drawn from its outer face)"""
    return MAIN_W - x, y


def link_net(v):
    """net name a link pin carries on the panel; LED_PWR is +3V3 (the series resistor is on the panel)"""
    if v is None:
        return None
    return "+3V3" if v == "LED_PWR" else v


def sma_ref(row, col):
    return "J%d" % (SMA_REF0 + row * len(SMA_COLS_X) + col)


def sma_list():
    """(ref, net, label, x, y) for every fitted SMA"""
    out = []
    for r, row in enumerate(SMA_NETS):
        for k, net in enumerate(row):
            if net:
                out.append((sma_ref(r, k), net, SMA_LABELS[r][k], SMA_COLS_X[k], SMA_ROWS_Y[r]))
    return out


# ------------------------------------------------------------------ footprint libraries
# Footprints the generator needs beyond whatever the netlist asks for (the main board's male header
# is not on the panel, but its geometry is needed for the mating audit).
EXTRA_FOOTPRINTS = ["%s:%s" % MAIN_HEADER_FP]


def load_footprints(needed=()):
    """footprints keyed by their full library id ("nickname:name").

    fp_parse.load_library only reads lib/class_board.pretty; the panel also uses KiCad standard
    footprints (the 2x20 socket, the 0603 resistor), which
    come from the global footprint library table and are read here straight from the KiCad
    installation.  Each footprint remembers the nickname it must be written to the board with.
    """
    lib = {}
    for name, fp in load_library(os.path.join(HW, "lib", "class_board.pretty")).items():
        fp.libnick = "class_board"
        lib["class_board:" + name] = fp
    for fid in list(needed) + EXTRA_FOOTPRINTS:
        if fid in lib:
            continue
        nick, name = fid.split(":")
        path = os.path.join(KICAD_FP, nick + ".pretty", name + ".kicad_mod")
        assert os.path.exists(path), "footprint %s is neither in lib/class_board.pretty nor in %s" % (fid, KICAD_FP)
        fp = Footprint(path)
        fp.libnick = nick
        lib[fid] = fp
    return lib


# ------------------------------------------------------------------ header geometry and the mating audit
def back_pad_xy(fx, fy, rot, px, py):
    """board position of a footprint-local pad (px, py) for a footprint placed on the BACK side.

    Same arithmetic as pcb_model.PadInst: a back-side footprint is stored flipped about the x axis
    and KiCad rotation is counter-clockwise on screen.
    """
    py = -py
    r = math.radians(rot)
    return fx + px * math.cos(r) + py * math.sin(r), fy - px * math.sin(r) + py * math.cos(r)


def pad_block_centre(fp):
    """footprint-local centre of the pad block"""
    xs = [p.x for p in fp.pads]
    ys = [p.y for p in fp.pads]
    return (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0


def anchor_for_centre(fp, cx, cy, rot):
    """footprint anchor ("at" in KiCad) that puts the pad block's centre at (cx, cy), back side"""
    lx, ly = pad_block_centre(fp)
    dx, dy = back_pad_xy(0.0, 0.0, rot, lx, ly)
    return round(cx - dx, 3), round(cy - dy, 3)


def main_header_at(lib, ref):
    """the (x, y, rot) the instructor must give the main-board header `ref`"""
    fp = lib["%s:%s" % MAIN_HEADER_FP]
    cx, cy = MAIN_HEADERS[ref]
    x, y = anchor_for_centre(fp, cx, cy, MAIN_HEADER_ROT)
    return x, y, MAIN_HEADER_ROT


def main_pin_xy(lib, ref, pin):
    """physical position of main-board pin `pin` of header `ref`, in MAIN-board coordinates"""
    fp = lib["%s:%s" % MAIN_HEADER_FP]
    pad = next(p for p in fp.pads if p.number == str(pin))
    fx, fy, rot = main_header_at(lib, ref)
    return back_pad_xy(fx, fy, rot, pad.x, pad.y)


def panel_header_at(lib, pref, mref):
    """anchor of the panel female header that mates main-board header `mref`"""
    fp = lib["%s:%s" % PANEL_HEADER_FP]
    cx, cy = to_panel(*MAIN_HEADERS[mref])
    x, y = anchor_for_centre(fp, cx, cy, PANEL_HEADER_ROT)
    return x, y, PANEL_HEADER_ROT


def mating_map(lib):
    """[(panel ref, main ref, pin, net, panel pad number, panel x, y)] for all 120 pins.

    Each main-board pin is mapped into panel coordinates and the female pad at that exact point is
    looked up; the pad NUMBER is whatever the geometry gives (it need not equal the pin number).
    """
    fp = lib["%s:%s" % PANEL_HEADER_FP]
    out = []
    for pref, mref, pins, _what in LINKS:
        fx, fy, rot = panel_header_at(lib, pref, mref)
        pads = {}
        for pad in fp.pads:
            x, y = back_pad_xy(fx, fy, rot, pad.x, pad.y)
            pads[(round(x, 2), round(y, 2))] = pad.number
        for pin in range(1, 41):
            px, py = to_panel(*main_pin_xy(lib, mref, pin))
            key = (round(px, 2), round(py, 2))
            out.append((pref, mref, pin, link_net(pins[pin]), pads.get(key), round(px, 3), round(py, 3)))
    return out


def check_link_mating(board, lib):
    """every female pad must carry the net of the male pin at the same physical point (D-25, extended to 3 headers)"""
    errors = []
    by_ref = {f.ref: f for f in board.footprints}
    for (pref, mref, pin, net, padnum, px, py) in mating_map(lib):
        if padnum is None:
            errors.append("%s: no female pad at the position of %s pin %d (%.2f, %.2f)" % (pref, mref, pin, px, py))
            continue
        pad = next((p for p in by_ref[pref].pads if p.number == padnum), None)
        if pad is None or abs(pad.x - px) > 0.02 or abs(pad.y - py) > 0.02:
            errors.append("%s pad %s is not where %s pin %d is" % (pref, padnum, mref, pin))
            continue
        pnet = None if (not pad.net or pad.net.startswith("unconnected-")) else pad.net
        if pnet != net:
            errors.append("%s pad %s: panel net %s, %s pin %d net %s" % (pref, padnum, pnet, mref, pin, net))
    return errors


def print_mating_table(lib):
    print("\n  MATING TABLE - main-board pin -> panel pad (panel coordinates, outer face)")
    print("  main pin | net        | panel pad | panel x,y (mm)")
    for (pref, mref, pin, net, padnum, px, py) in mating_map(lib):
        print("  %s-%-2d    | %-10s | %s pad %-2s |  %7.2f %6.2f%s"
              % (mref, pin, net or "spare", pref, padnum, px, py, "   <- pad number != pin number" if str(padnum) != str(pin) else ""))


# ================================================================== schematic
class PanelSheet(Sheet):
    """Sheet that lets one instance override its symbol's footprint (kept for one-off overrides)."""

    def inst_sexp(self, i, project_name, sheet_path):
        out = Sheet.inst_sexp(self, i, project_name, sheet_path)
        over = getattr(i, "footprint_override", None)
        if over:
            out = out.replace('(property "Footprint" "%s"' % i.sym.footprint,
                              '(property "Footprint" "%s"' % over, 1)
        return out


def build_sheet():
    sh = PanelSheet("front-panel", "TIGP class board 2026 - front panel (180 x 100, stacked on the back)", "A2", 1,
                    "17 SMA, OLED, 3 LEDs, TTL strip, TX terminal, Qwiic; three 2x20 female headers on the inner face")
    c = Ctx(sh, "PANEL", 100)
    sh.box(10, 10, 584, 412, "FRONT PANEL - 2 layers, 180 x 100 mm; copper = AGND, joined to GND only at the main-board star point NT1")
    sh.text("The panel lies FLAT ON THE BACK of the main board (Decision #45). J1 / J2 / J3 are 2x20 FEMALE headers on the panel's INNER face (B.Cu); they mate J6 / J7 / J8, the male headers on the main board's bottom side.", 14, 17, 1.4)
    sh.text("Panel coordinates are mirrored in x against the main board (panel x = 180 - main x, panel y = main y), because the panel is drawn from its OUTER face. The main board's REAR edge is therefore the panel's TOP edge.", 14, 21, 1.4)
    sh.text("With that mirror, panel pad k mates main-board pin k on all three headers (the KiCad PinSocket footprint already carries the mating mirror). gen_panel.py proves it from the pad coordinates before the board is written.", 14, 25, 1.4)
    sh.text("So the analog header J6 (main x = 12) is panel J1 at panel x = 168, the digital header J7 stays at x = 90, and the power header J8 (main x = 168) is panel J3 at panel x = 12.", 14, 29, 1.4)
    sh.text("Pins marked spare are not connected on the main board and are left unconnected here. SPARE (the 18th SMA position is empty; the fitted SPARE SMA) has its shield on AGND and its centre pin on TP1 only.", 14, 33, 1.4)
    sh.text("J30 is one footprint: the vertical 8.5 mm 1x4 socket (JLC C2894927) plus the OLED module's outline and its four M2 (2.2 mm) holes. The module lies flat on four 11 mm M2 stand-offs; measure the real module's hole spacing (23.5 x 23.8 assumed) before the order.", 14, 37, 1.4)
    sh.text("AO1/AO2: +-10 V, 49.9 ohm back-terminated. AI1..AI8: +-10 V, 1 kohm series on the main board. TRIG: 5 V into open circuit, about 2.4 V into 50 ohm. FAST1/FAST2 = the main-board nets FASTTTL1 / FASTTTL2.", 14, 41, 1.4)

    # ---- the three link headers ----------------------------------------------------------
    for k, (pref, mref, pins, what) in enumerate(LINKS):
        x0 = 90 + 170 * k
        J = c.place(pref, "HDR_2x20_FEMALE", x0, 130, 0)
        sh.text("%s - %s (inner face): mates %s, the %s header" % (pref, what, mref, what), x0 - 45, 100, 1.6, True)
        sh.text("panel x = %.0f mm (main board x = %.0f mm)" % (to_panel(*MAIN_HEADERS[mref])[0], MAIN_HEADERS[mref][0]), x0 - 45, 104, 1.3)
        for pin in range(1, 41):
            net = link_net(pins[pin])
            # four stub lengths in turn so the ground symbols stand in four columns (as on the link sheet)
            stub = (7.62, 12.7, 17.78, 22.86)[(pin // 2) % 4]
            if pin % 2:
                stub += 20.32           # a rail on an odd pin shares its side with the signal labels
            if net is None:
                c.nc_pin(J, str(pin))
            elif net in ("GND", "AGND", "+3V3", "+5V_RAW"):
                c.pwr_pin(J, str(pin), net, stub)
            else:
                c.glabel_pin(J, str(pin), net, 7.62)

    # ---- SMAs ----------------------------------------------------------------------------
    sh.text("17 SMA on a 20 mm grid (3 x 6, the 18th position is empty). Shields on AGND; the panel copper is AGND on both layers.", 14, 196, 1.5, True)
    for r, row in enumerate(SMA_NETS):
        for k, net in enumerate(row):
            if not net:
                continue
            x, y = 60 + 85 * k, 210 + 55 * r
            S = c.place(sma_ref(r, k), "BWSMA-KE-Z001", x, y, 0)
            c.glabel_pin(S, "5", net, 7.62)
            for leg in ("1", "2", "3", "4"):
                c.pwr_pin(S, leg, "AGND", 5.08)
            sh.text("panel label: %s   (%.0f, %.0f) mm" % (SMA_LABELS[r][k], SMA_COLS_X[k], SMA_ROWS_Y[r]), x - 8, y + 13, 1.2)

    # ---- panel connectors ----------------------------------------------------------------
    T = c.place(TTL_REF, "KF128-2.54-10P", 60, 375, 0)
    for i in range(1, 9):
        c.glabel_pin(T, str(i), "TTL%d" % i, 7.62)
    c.pwr_pin(T, "9", "GND", 7.62)
    c.pwr_pin(T, "10", "GND", 12.7)
    sh.text("TTL1..8 out (5 V, 1 kohm series on the main board) + 2 x GND", 40, 355, 1.3)

    X = c.place(TX_REF, "KF128-5.0-2P", 150, 368, 0)
    c.glabel_pin(X, "1", "TX", 7.62)
    c.pwr_pin(X, "2", "AGND", 7.62)
    sh.text("TX coil terminal, beside the TX SMA (kept: user 2026-09-16)", 128, 355, 1.3)

    Q = c.place(QWIIC_REF, "QWIIC_BM04B-SRSS", 220, 375, 0)
    c.pwr_pin(Q, "1", "GND", 7.62)
    c.pwr_pin(Q, "2", "+3V3", 12.7)
    c.glabel_pin(Q, "3", "I2C_SDA", 7.62)
    c.glabel_pin(Q, "4", "I2C_SCL", 7.62)
    c.pwr_pin(Q, "5", "GND", 17.78)
    c.pwr_pin(Q, "6", "GND", 22.86)
    sh.text("Qwiic (vertical): sensor from the front; shell pads on GND", 198, 355, 1.3)

    O = c.place(OLED_REF, "HDR_1x4_FEMALE", 300, 375, 0)
    c.pwr_pin(O, "1", "GND", 7.62)
    c.pwr_pin(O, "2", "+3V3", 12.7)
    c.glabel_pin(O, "3", "I2C_SCL", 7.62)
    c.glabel_pin(O, "4", "I2C_SDA", 7.62)
    sh.text("0.96 in I2C OLED (0x3C) on an 8.5 mm vertical socket: the module lies flat on four M2 stand-offs (holes in the footprint)", 278, 355, 1.3)

    # ---- LEDs ----------------------------------------------------------------------------
    sh.text("PWR is +3V3 from the link (1 kohm -> about 1 mA); WIFI / ACT come from GPIO43 / GPIO44 through JP1 / JP2 on the main board.", 355, 340, 1.3)
    for i, (sig, colour, lab) in enumerate([("+3V3", "LED_GREEN_0805", "PWR"), ("LED_WIFI", "LED_YELLOW_0603", "WIFI"),
                                            ("LED_ACT", "LED_GREEN_0805", "ACT")]):
        y = 355 + 17.78 * i
        R = c.place("R%d" % (i + 1), "R0603_1k", 370, y, 0)
        D = c.place("D%d" % (i + 1), colour, 395, y, 0)
        if sig == "+3V3":
            c.pwr_pin(R, "1", "+3V3", 5.08)
        else:
            c.glabel_pin(R, "1", sig, 5.08)
        sh.wire_pins(R, "2", D, "2")
        # the R-D node needs a name: kicad-cli 10.0.3 omits UNNAMED nets from the kicadxml netlist,
        # which would leave the LED anodes without a net and therefore unrouted (D-46)
        sh.label("LED_%s_A" % lab, 380, R.pin_pos("2")[1], 0, "local")
        c.pwr_pin(D, "1", "GND", 5.08)
        sh.text("panel label: %s" % lab, 388, y + 7, 1.2)

    # ---- test pad, power flags, mechanical ------------------------------------------------
    TP = c.place("TP1", "TestPoint", 450, 355, 0)
    c.glabel_pin(TP, "1", "SPARE", 5.08)
    sh.text("SPARE SMA: shield on AGND, centre pin on TP1 only (no link pin)", 424, 348, 1.2)

    for i, net in enumerate(["+3V3", "GND", "AGND", "+5V_RAW"]):
        x = 60 + 30 * i
        c.flag(x, 400, 0)
        c.power_at(x, 405.08, net, 0)
        sh.wire(x, 400, x, 405.08)
    sh.text("The panel is passive: the rails come in through the link, so each one carries a power flag.", 60, 396, 1.2)

    for i in range(4):
        Hh = c.place("H%d" % (i + 1), "MountingHole", 200 + 25 * i, 405, 0)
        for pin in Hh.pins():
            c.nc_pin(Hh, pin)
    sh.text("H1-H4: M3, same pattern as the main board (stand-offs). The OLED module's M2 holes are part of J30.", 200, 398, 1.2)
    for i in range(2):
        F = c.place("FID%d" % (i + 1), "Fiducial", 360 + 20 * i, 405, 0)
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
    # Library tables: our own library is a project path; the KiCad standard footprint libraries
    # (the 2x20 socket, the 0603 resistor) come from the global table.
    for name, uri, kind in (("sym-lib-table", "${KIPRJMOD}/../lib/class_board.kicad_sym", "sym"),
                            ("fp-lib-table", "${KIPRJMOD}/../lib/class_board.pretty", "fp")):
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
    subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", out,
                    os.path.join(FP_DIR, PROJECT + ".kicad_sch")], check=True)
    return out


# ================================================================== board
class PanelBoard(Board):
    """Board writer that keeps each footprint's own library nickname (the panel mixes libraries)."""

    def footprint_sexp(self, f, project_name):
        out = Board.footprint_sexp(self, f, project_name)
        nick = getattr(f.fp, "libnick", "class_board")
        if nick != "class_board":
            out = out.replace('"class_board:%s"' % f.fp.name, '"%s:%s"' % (nick, f.fp.name))
        # The class_board footprints name their 3D models "${KIPRJMOD}/lib/class_board.3dshapes/..." - right
        # for the main board, whose project file sits next to lib/, but the panel project lives in
        # front-panel/, one level down, so KiCad's 3D viewer showed bare pads for every SMA, terminal,
        # Qwiic and LED (user, 2026-09-17).  Rewrite the path to the shared library.
        out = out.replace('"${KIPRJMOD}/lib/class_board.3dshapes/', '"${KIPRJMOD}/../lib/class_board.3dshapes/')
        return out


def placement(lib):
    """ref -> (x, y, rotation, side) in panel coordinates"""
    P = {}

    def put(ref, x, y, rot=0, side="F.Cu"):
        P[ref] = (round(x, 3), round(y, 3), rot, side)

    # the three female headers: position and rotation are derived from the main board, never typed in
    for pref, mref, _pins, _what in LINKS:
        x, y, rot = panel_header_at(lib, pref, mref)
        put(pref, x, y, rot, "B.Cu")
    for ref, net, lab, x, y in sma_list():
        put(ref, x, y)
    put(OLED_REF, OLED_AT[0], OLED_AT[1], OLED_AT[2])
    put(TTL_REF, TTL_AT[0], TTL_AT[1], TTL_AT[2])
    put(TX_REF, TX_AT[0], TX_AT[1], TX_AT[2])
    put(QWIIC_REF, QWIIC_AT[0], QWIIC_AT[1], QWIIC_AT[2])
    for i, x in enumerate(LED_X):
        put("D%d" % (i + 1), x, LED_Y)
        put("R%d" % (i + 1), x, RES_Y)
    put("TP1", TP1_AT[0], TP1_AT[1])
    for i, (x, y) in enumerate(MAIN_HOLES):
        put("H%d" % (i + 1), *to_panel(x, y))
    for i, (x, y) in enumerate(FID_AT):
        put("FID%d" % (i + 1), x, y)
    return P


def check_keepouts(board):
    """nothing with a pad or a hole may sit in the band the inner-face headers occupy"""
    bands = []
    for pref, mref, _pins, _what in LINKS:
        cx, cy = to_panel(*MAIN_HEADERS[mref])
        bands.append((pref, cx - 2.7, cy - 25.6, cx + 2.7, cy + 25.6))
    errors = []
    for f in board.footprints:
        if f.side == "B.Cu":
            continue
        for p in f.pads:
            for (pref, x0, y0, x1, y1) in bands:
                if x0 - 0.5 < p.x < x1 + 0.5 and y0 - 0.5 < p.y < y1 + 0.5:
                    errors.append("%s pad %s at (%.2f, %.2f) sits in the keep-out band of %s" % (f.ref, p.number, p.x, p.y, pref))
    return errors


def silkscreen(board, lib):
    t = board.gr_text
    t("^  R E A R  /  T O P   E D G E  ^   (this edge meets the main board's rear edge)", 90.0, 2.6, size=1.2, thickness=0.18)
    t(TITLE, 90.0, 6.4, size=1.5, thickness=0.2)
    t("AO +-10 V   TRIG 5 V TTL (~2.4 V into 50 ohm)   AI +-10 V, 1 kohm series   panel copper = AGND", 90.0, 9.6, size=1.0, thickness=0.15)
    for ref, net, lab, x, y in sma_list():
        t(lab, x, y + 5.6, size=1.2, thickness=0.2)
    # the three link headers, seen from the outer face
    for pref, mref, _pins, what in LINKS:
        cx, _cy = to_panel(*MAIN_HEADERS[mref])
        t("%s = %s" % (pref, mref), cx, 79.0, size=1.0, thickness=0.15)
    # OLED: outline, M2 holes and pin labels are part of the J30 footprint
    # LEDs
    for x, lab in zip(LED_X, ("PWR", "WIFI", "ACT")):
        t(lab, x, 53.4, size=1.0, thickness=0.15)
    # TTL strip
    labels = ["TTL1", "TTL2", "TTL3", "TTL4", "TTL5", "TTL6", "TTL7", "TTL8", "GND", "GND"]
    fp = lib["class_board:CONN-TH_10P-P2.54_KF128-2.54-10P"]
    for num, lab in zip([str(i) for i in range(1, 11)], labels):
        pad = next(p for p in fp.pads if p.number == num)
        t(lab, TTL_AT[0] + pad.x, TTL_AT[1] - 5.2, size=1.0, thickness=0.15, rot=90)
    t("TTL OUT 1..8  (5 V)", TTL_AT[0], TTL_AT[1] - 9.4, size=1.0, thickness=0.15)     # above the pin labels; the strip is on the edge
    t("TX COIL", TX_AT[0], TX_AT[1] - 7.2, size=1.0, thickness=0.15)
    t("QWIIC", QWIIC_AT[0], QWIIC_AT[1] - 4.4, size=1.0, thickness=0.15)
    t("TP1 SPARE", TP1_AT[0], TP1_AT[1] - 2.6, size=1.0, thickness=0.15)
    # inner face
    board.gr_text("J1 J2 J3 mate J6 J7 J8 of the main board; pin 1 marked", 90.0, 85.0,
                  layer="B.SilkS", size=1.3, thickness=0.2, justify="mirror")
    for pref, mref, _pins, _what in LINKS:
        cx, _cy = to_panel(*MAIN_HEADERS[mref])
        x, y, _rot = panel_header_at(lib, pref, mref)
        board.gr_text("%s pin 1" % pref, cx, y - 3.2, layer="B.SilkS", size=1.0, thickness=0.15, justify="mirror")
        board.gr_text("%s pin 40" % pref, cx, y + 51.4, layer="B.SilkS", size=1.0, thickness=0.15, justify="mirror")
    board.gr_text("REAR / TOP EDGE", 90.0, 3.4, layer="B.SilkS", size=1.2, thickness=0.18, justify="mirror")


def build(route=True):
    comps, nets, pad_net = netlist.read(os.path.join(FP_DIR, ".netlist.xml"))
    lib = load_footprints(sorted({c.footprint for c in comps.values()}))
    P = placement(lib)
    missing = [r for r in comps if r not in P]
    assert not missing, "unplaced: %s" % missing
    extra = [r for r in P if r not in comps]
    assert not extra, "placed but not in the netlist: %s" % extra
    board = PanelBoard(layers=2, title="TIGP class board 2026 - front panel", height=H)
    for ref, comp in sorted(comps.items()):
        fp = lib[comp.footprint]
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
    silkscreen(board, lib)
    gen_pcb.W, gen_pcb.H = W, H
    gen_pcb.place_reference_texts(board)
    for f in board.footprints:
        if f.ref == TTL_REF:
            f.ref_pos = (13.0, -9.4, 0)     # beside the "TTL OUT" caption; the strip body is on the edge
        elif f.ref == TX_REF:
            f.ref_pos = (7.0, -7.2, 0)      # beside the "TX COIL" caption
        elif f.ref == OLED_REF:
            f.ref_pos = (7.6, -3.3, 0)      # right of the pin labels, above the module's top edge
    if route:
        import router
        agnd = [(0.5, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (0.5, H - 0.5)]
        router.route_board(board, comps, nets, pad_net, W, H, agnd, ((500.0, 500.0), (501.0, 501.0)), plane_gnd=False,
                           # the headers stand along y, so their pins escape along x: J1 and J2 to the
                           # left (SMA field, TTL strip), J3 to the right (everything it feeds)
                           stub_hint={"J1": (-1, 0), "J2": (-1, 0), "J3": (1, 0)},
                           layer_hint={"J1": 1, "J2": 1, "J3": 1},     # signals fan out on B.Cu ...
                           layer_hint_net={"GND": 0},                  # ... the GND pins on F.Cu
                           priority_file=os.path.join(FP_DIR, ".route_priority.json"))
        # +5V_RAW is the one net the automatic router cannot finish: its two pads (J3 pins 1 and 3)
        # are neighbours in the same pin column, and a 1.0 mm POWER_RAW track does not fit in the
        # fan-out lanes it escapes into.  Straight from pad to pad is both shorter and cleaner.
        code = board.netcode("+5V_RAW")
        board.tracks = [tr for tr in board.tracks if tr[6] != code]      # its escape stubs lead nowhere
        pads = {p.number: p for p in next(f for f in board.footprints if f.ref == "J3").pads}
        a, b = pads["1"], pads["3"]
        board.track(a.x, a.y, b.x, b.y, 1.0, "B.Cu", "+5V_RAW")
    return board, comps, nets, pad_net, lib


def main():
    route = "--no-route" not in sys.argv
    sh = write_schematic()
    print("schematic: %d symbols, %d wires" % (len(sh.insts), len(sh.wires)))
    export_netlist()
    board, comps, nets, pad_net, lib = build(route)
    errs = check_keepouts(board) + check_link_mating(board, lib)
    if errs:
        for e in errs:
            print("PANEL ERROR:", e)
        raise SystemExit(1)
    print("link mating audit: 120 female pads carry the net of the main-board pin they touch")
    out = os.path.join(FP_DIR, PROJECT + ".kicad_pcb")
    board.write(out, PROJECT)
    print("wrote", out, "footprints", len(board.footprints), "nets", len(board.nets),
          "tracks", len(board.tracks), "vias", len(board.vias))
    print_mating_table(lib)
    print("\n  MAIN-BOARD HEADERS - the placement the panel was generated for (KiCad 'at' values):")
    for _pref, mref, _pins, what in LINKS:
        x, y, rot = main_header_at(lib, mref)
        cx, cy = MAIN_HEADERS[mref]
        print("    %s (%s): footprint %s:%s, side B.Cu, at (%.2f, %.2f) rot %d  -> pad block centred on (%.1f, %.1f), pin 1 at the rear"
              % (mref, what, MAIN_HEADER_FP[0], MAIN_HEADER_FP[1], x, y, rot, cx, cy))


if __name__ == "__main__":
    main()
