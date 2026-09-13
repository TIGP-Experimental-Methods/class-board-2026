"""Generate the class-board main PCB (D3): placement, outline, zones, rule areas, routing, silkscreen.

Coordinates: x right (0..140), y down (0 = rear edge with USB-C/jack/terminals, 100 = front edge with the
2x20 link).  See docs/design-review.md section 2 for the floorplan and section 6 for the routing concept.

Run from hardware/scripts:  python gen_pcb.py [--no-route]
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netlist                                  # noqa: E402
from fp_parse import load_library               # noqa: E402
from pcb_model import Board, FootprintInst      # noqa: E402

HW = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
W, H = 180.0, 100.0          # v0.7 (2026-09-13): +40 mm on the right: section C gets a 41 mm rear strip for its three terminals, section B a 10 mm strip
SOCKET_ROW_SPACING = 25.4        # D-12: assumed for the Jinhua #40729 clone; 22.86 for an official DevKitC-1
SOCK_X = 70.0                    # dev-board centre x
SOCK_Y = 50.0                    # dev-board centre y
J1_Y = SOCK_Y + SOCKET_ROW_SPACING / 2      # front row (J1 header of the dev board)
J3_Y = SOCK_Y - SOCKET_ROW_SPACING / 2      # rear row (J3 header)
PIN1_X = SOCK_X - 26.67
LINK_Y = 94.5                                # 2x20 right-angle link: pads at 93.23/95.77, plastic body 97.27-99.77, pins overhang the edge
LINK_PIN1_X = SOCK_X - 24.13                 # pin 1 at the left end (rot 0); odd pins in the row nearer the edge

# ------------------------------------------------------------------ zone polygons (owner rule areas)
ZONES = {
    # v0.7 (2026-09-13): three student sections + base. A = inputs + NMR receiver (old B1 + OPT),
    # B = outputs + timing + NMR transmitter (old B3 + B5 + the new right strip), C = power + switching + coil switches
    # (old B2 + B4 + rear-right corner to x = 149). Everything that was at x >= 129 is shifted +20 mm in placement().
    "ZONE_C": [(0.5, 0.5), (169.0, 0.5), (169.0, 36.0), (37.5, 36.0), (37.5, 57.5), (0.5, 57.5)],
    "ZONE_BASE": [(37.5, 36.0), (100.0, 36.0), (100.0, 57.0), (37.5, 57.0)],
    "ZONE_A": [(0.5, 57.5), (45.0, 57.5), (45.0, 57.0), (100.0, 57.0), (100.0, 99.5), (0.5, 99.5)],
    "ZONE_B": [(100.0, 36.0), (169.0, 36.0), (169.0, 0.5), (179.5, 0.5), (179.5, 99.5), (100.0, 99.5)],
}
RELAY_X = [68.0, 85.0, 102.0, 119.0]
# AGND pour (F.Cu + B.Cu): analog band across the front + the +-12 V / +5VA output area of B2
AGND_POLY = [(22.0, 30.0), (37.5, 30.0), (37.5, 57.0), (100.0, 57.0), (100.0, 68.0), (129.0, 68.0), (129.0, 87.5),
             (179.5, 87.5), (179.5, 99.5), (0.5, 99.5), (0.5, 57.0), (22.0, 57.0)]
ISO_KEEPOUT = ((37.5, 0.0), (60.0, 26.5))
# AI channel networks in a row between the link (AI pins 9..23 at x 56.0..73.8) and the ADC: left -> right = AI1 .. AI8
# (planar fan-in, see docs/design-decisions.md D-19)
NET_ROW_X = {1: 48.2, 2: 53.0, 3: 57.8, 4: 62.6, 5: 67.4, 6: 72.2, 7: 77.0, 8: 81.8}   # 4.8 mm pitch: 1.26 mm between clamp bodies for the AIN trace


def dev_pin(row, n):
    """board position of dev-board socket pin n (1..22) of row 'J1' (front) or 'J3' (rear)"""
    return (PIN1_X + 2.54 * (n - 1), J1_Y if row == "J1" else J3_Y)


def link_pin(n):
    """board position of link pin n (1..40); odd pins toward the board interior row, pin 1 at the right"""
    col = (n - 1) // 2
    x = LINK_PIN1_X + 2.54 * col
    y = LINK_Y + 1.27 if n % 2 else LINK_Y - 1.27
    return (x, y)


# ------------------------------------------------------------------ placement
def fp_extent(fp):
    """footprint-local bbox (xmin, ymin, xmax, ymax) of courtyard + silk + pads"""
    c = fp.courtyard
    xs, ys = [c[0], c[2]], [c[1], c[3]]
    if fp.silk:
        xs += [fp.silk[0], fp.silk[2]]; ys += [fp.silk[1], fp.silk[3]]
    for p in fp.pads:
        r = math.radians(p.rot)
        hx = abs(p.sx / 2 * math.cos(r)) + abs(p.sy / 2 * math.sin(r))
        hy = abs(p.sx / 2 * math.sin(r)) + abs(p.sy / 2 * math.cos(r))
        xs += [p.x - hx, p.x + hx]
        ys += [p.y - hy, p.y + hy]
    return min(xs), min(ys), max(xs), max(ys)


def rotated_extent(fp, rot):
    """board-space extent of a footprint placed at (0, 0) with rotation rot"""
    b = fp_extent(fp)
    r = math.radians(rot)
    pts = [(x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r)) for x in (b[0], b[2]) for y in (b[1], b[3])]
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


def placement(lib=None, comps=None):
    P = {}

    def put(ref, x, y, rot=0):
        P[ref] = (round(x, 3), round(y, 3), rot)

    def row(y, x0, items, gap=0.5):
        """pack footprints left to right along y starting at x0 (bbox edge), gap between extents; returns end x"""
        x = x0
        for ref, rot in items:
            e = rotated_extent(lib[comps[ref].footprint.split(":")[1]], rot)
            put(ref, x - e[0], y, rot)
            x += (e[2] - e[0]) + gap
        return x

    # ---- mechanical ------------------------------------------------------------------
    for ref, (x, y) in zip(("H1", "H2", "H3", "H4"), ((4, 4), (136, 4), (4, 96), (136, 96))):
        put(ref, x, y)
    put("FID1", 22, 4); put("FID2", 126.5, 47.0); put("FID3", 12, 60)

    # ---- BASE: sockets (dev board long axis along x, antenna end at the left) -----------------
    put("J1", SOCK_X, J1_Y, 0)
    put("J2", SOCK_X, J3_Y, 0)
    put("J3", 3.4, 61.0, 90)             # Qwiic, cable exits to the left edge
    put("J4", 3.4, 69.0, 90)
    put("J5", 114.0, 52.0, 0)            # 2x10 expansion header (B5 block area, BASE part)
    put("NT1", 99.2, 67.5, 90)          # AGND-GND star at the B1/B3 boundary, next to the ADC digital side
    put("R1", 86.4, 66.5, 90)            # 33 R SCLK under J1-18
    put("R2", 83.8, 66.5, 90)            # 33 R MOSI under J1-17
    put("R3", 61.5, 34.0, 90)            # I2C pull-ups near J3-4/5
    put("R4", 64.0, 34.0, 90)
    put("JP1", 47.5, 66.0, 0)            # LED links (GPIO43/44 -> LED_WIFI/ACT)
    put("JP2", 47.5, 69.5, 0)
    put("TP1", 43.5, 73.0)               # RST
    put("TP2", 43.5, 76.5)               # GND
    put("TP3", 43.5, 80.0)               # +3V3
    put("TP4", 43.5, 83.5)               # +5V_RAW

    # ---- B2 power (x 0-38, y 0-56) ------------------------------------------------------
    put("J201", 13.0, 5.6, 180)          # USB-C, opening at the rear edge
    put("J202", 29.5, 12.0, 270)         # 5 V jack, opening at the rear edge
    put("R201", 3.0, 10.5, 90); put("R202", 20.0, 11.5, 90)      # CC pull-downs
    put("F201", 7.0, 12.5, 0)
    put("D201", 6.5, 17.5, 90); put("C203", 15.5, 17.0, 90)
    put("U201", 11.0, 21.5, 0)
    put("F202", 29.5, 20.5, 0)
    put("D202", 35.0, 24.0, 90); put("C204", 25.2, 24.0, 90)
    put("U202", 29.5, 27.5, 0)
    put("C201", 20.0, 24.5, 90); put("C202", 22.5, 24.5, 90)       # 22 uF + 100 nF bulk on +5V_RAW
    put("R209", 2.7, 23.3, 90); put("D203", 2.7, 27.5, 90)       # +5V_RAW LED
    put("PS201", 11.0, 31.5, 0)          # +12 V module (pins along x at y 33, body toward +y)
    put("PS202", 11.0, 42.5, 0)          # -12 V module
    put("FB201", 5.7, 29.0, 0); put("C216", 9.7, 29.0, 0)        # module inputs (between the module pin rows)
    put("FB202", 5.2, 39.4, 0); put("C217", 9.2, 39.4, 0)
    row(31.5, 22.5, [("FB203", 90), ("C207", 90), ("C209", 0), ("R203", 90), ("R204", 90), ("R205", 90)], gap=0.4)     # +12 V output filter + bleeders
    row(35.9, 22.5, [("R211", 0), ("D205", 0), ("TP201", 0), ("TP202", 0)]); put("TP203", 36.2, 38.4)
    row(42.5, 22.5, [("FB204", 90), ("C206", 90), ("C208", 0), ("R206", 90), ("R207", 90), ("R208", 90)], gap=0.4)     # -12 V
    row(46.6, 22.5, [("R212", 0), ("D206", 0), ("TP204", 0), ("TP205", 0)]); put("TP206", 36.2, 49.1)
    row(52.8, 2.5, [("C213", 90), ("U204", 0), ("C214", 90), ("C215", 90), ("C210", 90), ("U203", 0), ("C211", 90), ("C212", 90)], gap=0.4)
    put("R210", 30.0, 49.2, 0); put("D204", 34.5, 52.8, 90)        # +3V3 LED chain: resistor above the LDO row, LED at its end   # AMS1117 + 78L05

    # ---- B4 switching (x 38-129, y 0-36): isolated inputs at the left, four relays to the right ----
    for n in range(2):
        x0 = (42.7, 54.0)[n]
        put("J41%d" % (n + 1), x0, 4.2, 0)                        # 2P terminal, wire entry at the rear edge
        # isolated side (x0-4 .. x0+4, y 9.5-21): diode, 220 R, 10 k, two transistors, 100 R || 1 k
        put("D42%d" % (n + 1), x0 - 2.7, 10.3, 0)
        put("R43%d" % (n + 1), x0 + 2.4, 10.3, 0)
        put("R44%d" % (n + 1), x0 - 2.5, 12.7, 0)
        put("Q41%d" % (n + 1), x0 + 2.5, 13.7, 0)
        put("Q42%d" % (n + 1), x0 - 2.5, 16.2, 0)
        put("R45%d" % (n + 1), x0 + 2.5, 17.7, 0)
        put("R46%d" % (n + 1), x0 + 2.5, 20.2, 0)
        put("U40%d" % (n + 1), x0 + 0.5, 27.0, 180)               # 6N137: pins 1-4 (isolated) at the top, 5-8 below
        put("R47%d" % (n + 1), x0 - 2.5, 34.0, 0)
        put("C40%d" % (n + 1), x0 + 2.5, 34.0, 0)
    for k in range(4):
        xk = RELAY_X[k]
        put("J40%d" % (k + 1), xk, 4.2, 0)             # 3P terminal
        put("K40%d" % (k + 1), xk, 15.5, 0)             # relay: NO/NC pads left column, COM right column
        put("Q40%d" % (k + 1), xk - 5.5, 24.5, 90)      # MOSFET
        put("R40%d" % (k + 1), xk - 6.0, 28.0, 0)       # gate series 1 k
        put("R41%d" % (k + 1), xk - 6.0, 31.0, 0)       # gate pull-down 10 k
        put("D40%d" % (k + 1), xk + 1.0, 24.5, 90)      # flyback
        put("R42%d" % (k + 1), xk + 5.0, 24.5, 0)       # LED resistor
        put("D41%d" % (k + 1), xk + 5.0, 28.0, 0)       # LED
    put("Q401", RELAY_X[0] - 5.0, 24.5, 90)              # v0.7: +0.5 mm from U402 (was a 0.2 mm pad clearance)

    # ---- B5 digital I/O (right strip + block x 100-129, y 36-68) ------------------------------
    term_y = {"J506": 13.6, "J507": 25.0, "J501": 36.4, "J502": 47.8, "J503": 59.2, "J504": 70.6, "J505": 82.0}
    for ref, y in term_y.items():
        put(ref, 135.0, y, 90)                          # 2P terminals, wire entry at the right edge
    put("U501", 108.0, 41.2, 270)         # 74AHCT541: inputs on the left column, outputs facing the R501-R508 columns
    for i in range(8):
        put("R50%d" % (i + 1), 117.5 + (i % 2) * 3.5, 38.0 + (i // 2) * 2.5, 0)
    put("C501", 113.5, 38.0, 90)            # in line with the +5V_RAW pin (20, top-right corner)
    put("U502", 105.4, 61.0, 0)           # 74HCT125 fast outs (pins up/down)
    put("R509", 101.5, 57.6, 90); put("R510", 101.5, 61.0, 90); put("C502", 109.5, 57.5, 90)
    put("JP501", 104.4, 66.45, 0)         # GPIO44 / U502 1Y select
    put("D501", 110.3, 66.2, 0)           # BAV99 clamp on TRIG_5V (SOT-23)
    put("U503", 114.0, 61.2, 90)          # LVC1T45 (TRIG), pins up/down so its fan-out zones are free
    put("C503", 110.5, 61.2, 90); put("C504", 117.5, 61.2, 90); put("R511", 120.3, 61.2, 0)
    put("X501", 124.6, 59.5, 0); put("R512", 119.5, 57.6, 90); put("R513", 128.0, 59.5, 90); put("C505", 124.6, 63.0, 0)
    put("U504", 124.8, 66.0, 180); put("R514", 121.5, 65.5, 90); put("R515", 128.0, 65.5, 90); put("C506", 118.5, 65.5, 90)
    # v0.7 TCA9535 I2C expander (U505, Block = B5).  ZONE_B5 of the 140 mm board has NO free 8.8 x 8.2 mm pocket
    # left (the x 100-129 / y 47-56 band is taken by the expansion header J5 at y 49.2-54.8, the right strip by the
    # terminals J501-J507), so the expander sits in the free area under the dev board, just west of the B5 boundary
    # and next to U501 whose inputs it drives.  The v0.7 re-plan (160 x 100 board, re-spec 8.1) redraws the zones:
    # extend ZONE_B5 over this pocket or move U505 into the new 20 mm strip -- until then DRC reports the
    # owner_B5 assertion for U505/C507/TP501-504.
    put("U505", 94.5, 46.0, 0)            # TSSOP-24: x 89.9-98.7, y 41.9-50.1 (between the socket rows, clear of J1/J2)
    put("C507", 97.0, 52.8, 90)           # +3V3 decoupling beside the expander
    put("TP501", 84.0, 52.8); put("TP502", 87.0, 52.8)         # EXP_P14 / P15 (spare expander ports)
    put("TP503", 90.0, 52.8); put("TP504", 93.0, 52.8)         # EXP_P16 / P17

    # ---- B3 signal generation (right-front: x 100-129 above y 85.5, to the edge below) -------------
    put("U302", 105.6, 72.5, 0)           # 74HCT125 level shifter (SPI/CS_DAC from J1 come from the left)
    put("C308", 109.4, 73.4, 90)             # beside the 74HCT125, reached from its VCC corner pin without crossing the row
    put("U301", 114.0, 74.8, 0)           # DAC8563 (VSSOP-10)
    put("C301", 111.3, 69.7, 90); put("C302", 110.5, 77.4, 90); put("C303", 117.5, 76.0, 90); put("R311", 117.5, 71.0, 90)
    put("U303", 114.0, 83.0, 0)           # OPA2192 (SOIC-8)
    put("C304", 119.3, 80.0, 0); put("C306", 119.3, 82.6, 0); put("C305", 119.3, 85.2, 0); put("C307", 119.3, 88.0, 0)   # op-amp decoupling
    put("R301", 106.5, 80.0, 90); put("R302", 106.5, 83.4, 90); put("R305", 106.5, 86.8, 90); put("R306", 106.5, 90.2, 90)
    put("R303", 109.2, 81.0, 90); put("R307", 109.2, 87.0, 90)
    put("R304", 109.2, 90.5, 90); put("R308", 112.0, 91.5, 0)
    put("R309", 123.3, 84.0, 0); put("D301", 127.0, 84.0, 90); put("R310", 123.3, 89.0, 0); put("D302", 127.0, 89.0, 90)
    put("TP301", 121.0, 93.5)

    # ---- OPT conditioning (front left, all DNP) ----------------------------------------------
    put("J601", 13.5, 95.7, 180); put("J602", 25.2, 95.7, 180)      # DNP terminals on the front edge, left of the link body
    put("R601", 12.0, 73.5, 0); put("R602", 12.0, 78.5, 0); put("D601", 16.0, 73.5, 0); put("D602", 16.0, 78.5, 0)
    put("U601", 22.0, 76.0, 0); put("JP602", 22.0, 70.5, 0); put("R603", 18.5, 81.2, 0); put("R604", 26.0, 81.2, 0)
    put("U602", 33.0, 74.0, 0); put("JP601", 39.5, 68.5, 0)
    put("U603", 32.0, 84.0, 0); put("R605", 24.5, 84.0, 90); put("R606", 24.5, 87.4, 90); put("C605", 32.0, 90.0, 0); put("C606", 32.0, 79.0, 0)
    put("U604", 9.0, 88.0, 0); put("R607", 14.0, 84.5, 0); put("C607", 14.0, 87.5, 0)
    put("C601", 36.0, 62.0, 0); put("C602", 39.4, 62.0, 0); put("C603", 36.0, 65.0, 0); put("C604", 39.4, 65.0, 0)

    # ---- B1 inputs (centre-front, straight above the link's AI pins) -------------------------------
    put("U101", 65.0, 76.0, 270)          # ADS8688: pins 1-19 left column (x 62.1, y 71.5 -> 80.5), 20-38 right column (x 67.9)
    # decoupling sits outside the 2 mm fan-out bands of the pin columns (x < 57 and x > 72.5); digital corners stay free
    put("C104", 55.5, 74.5, 90); put("C101", 55.5, 77.8, 90)         # REFCAP 1 uF (pin 7), AVDD 1 uF (pin 9)
    put("C105", 51.5, 74.5, 90); put("C106", 51.5, 79.8, 90)         # REFCAP 22 uF, REFIO 10 uF (pin 5)
    put("C103", 75.5, 75.5, 90); put("C102", 75.5, 79.5, 90)         # AVDD 1 uF (pin 30) + 10 uF bulk
    put("C107", 79.0, 68.6, 0); put("C108", 85.5, 69.4, 0)           # DVDD 10 uF + 100 nF above the package
    put("R101", 73.2, 79.0, 90); put("R102", 51.3, 69.0, 0)          # 33 R SDO (right column, below the fan-out), 10 k RST pull-up
    for ai, x in NET_ROW_X.items():          # signal flow from the link (front): R -> C/D node -> ADC
        put("R11%d" % ai, x, 90.5, 90)
        put("C11%d" % ai, x, 87.6, 0)
        put("D11%d" % ai, x, 84.2, 90)
    put("JP101", 97.5, 89.5, 90); put("JP102", 97.5, 95.0, 90)      # AI7/AI8 source select, beside the link body
    put("TP101", 91.0, 88.0)

    # ---- front-panel link (pin 1 at the right end) -------------------------------------------
    put("J6", SOCK_X, LINK_Y, 0)
    # ---- v0.7: everything that sat on the old right edge (x >= 129) moves +40 mm with the outline ------
    for ref in list(P):
        x, y, rot = P[ref]
        if x >= 129.0:
            P[ref] = (round(x + 40.0, 3), y, rot)
    # ---- v0.7: placements contributed by the extra sheet modules (scripts/sheet_*.py, PLACEMENT dict) ----
    for mod in sheet_modules():
        for ref, pos in getattr(mod, "PLACEMENT", {}).items():
            P[ref] = (round(pos[0], 3), round(pos[1], 3), pos[2] if len(pos) > 2 else 0)
    return P


def sheet_modules():
    """import every scripts/sheet_*.py (the v0.7 extra sheets); a module that fails to import is skipped with a note"""
    import glob, importlib
    mods = []
    for path in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sheet_*.py"))):
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            mods.append(importlib.import_module(name))
        except Exception as e:  # noqa: BLE001
            print("sheet module %s skipped: %s" % (name, e))
    return mods


# ------------------------------------------------------------------ build
def build(route=True):
    comps, nets, pad_net = netlist.read(os.path.join(HW, ".netlist.xml"))
    lib = load_library(os.path.join(HW, "lib", "class_board.pretty"))
    P = placement(lib, comps)
    board = Board(layers=4, title="TIGP class board 2026 - main board", height=H)
    missing = [r for r in comps if r not in P]
    if missing:
        raise SystemExit("unplaced: %s" % missing)
    extra = [r for r in P if r not in comps]
    if extra:
        print("placement entries without a schematic part (ignored): %s" % ", ".join(sorted(extra)))
        for r in extra:
            del P[r]
    for ref, comp in sorted(comps.items()):
        fpname = comp.footprint.split(":")[1]
        fp = lib[fpname]
        x, y, rot = P[ref]
        nets_by_pad = {}
        for pad in fp.pads:
            n = pad_net.get((ref, pad.number))
            if n:
                nets_by_pad[pad.number] = n
                board.net(n)
        cdict = dict(value=comp.value, datasheet=comp.datasheet, description=comp.description,
                     fields={k: v for k, v in comp.fields.items() if k not in ("Reference", "Value")},
                     path=comp.path, sheetname=comp.sheetname, sheetfile=comp.sheetfile, dnp=comp.dnp, in_bom=comp.in_bom)
        board.add_footprint(FootprintInst(ref, fp, x, y, rot, cdict, nets_by_pad))
    board.gr_rect(0, 0, W, H, "Edge.Cuts", 0.1)
    # owner rule areas (copper allowed; used by the owner DRC rule)
    for name, pts in ZONES.items():
        board.zone(None, ["F.Cu"], pts, name=name,
                   keepout=dict(tracks="allowed", vias="allowed", pads="allowed", copperpour="allowed", footprints="allowed"))
    # GND planes (inner) and outer pours; AGND pours over the analog band
    full = [(0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)]
    board.zone("GND", ["In1.Cu"], full, priority=0, name="GND_L2", clearance=0.3, thermal_gap=0.4, bridge=0.5)
    board.zone("GND", ["In2.Cu"], full, priority=0, name="GND_L3", clearance=0.3, thermal_gap=0.4, bridge=0.5)
    # outer GND pours: no pad connection (SMD GND pads reach the planes through their own vias; THT pads through the planes)
    board.zone("GND", ["F.Cu"], full, priority=0, name="GND_F", clearance=0.3, pad_connect="none")
    board.zone("GND", ["B.Cu"], full, priority=0, name="GND_B", clearance=0.3, pad_connect="none")
    apoly = AGND_POLY
    board.zone("AGND", ["F.Cu"], apoly, priority=2, name="AGND_F", clearance=0.3, pad_connect="solid")
    board.zone("AGND", ["B.Cu"], apoly, priority=2, name="AGND_B", clearance=0.3, pad_connect="solid")
    # isolation keep-out around the isolated input group: no pours/vias of any net on any layer
    (kx0, ky0), (kx1, ky1) = ISO_KEEPOUT
    iso = [(kx0, ky0), (kx1, ky0), (kx1, ky1), (kx0, ky1)]
    board.zone(None, ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"], iso, name="ISO_KEEPOUT",
               keepout=dict(tracks="allowed", vias="not_allowed", pads="allowed", copperpour="not_allowed", footprints="allowed"))
    # silkscreen
    board.gr_text("TIGP CLASS BOARD 2026 rev B (v0.7)", 70.0, 45.0, size=1.5, thickness=0.2)
    board.gr_text("ESP32-S3-DevKitC-1 (Jinhua #40729)   antenna <-   -> USB", 70.0, 50.0, size=1.0, thickness=0.15)
    board.gr_text("5V IN", 29.5, 17.0, size=1.0, thickness=0.15)
    board.gr_text("USB-C 5V", 13.0, 9.2, size=1.0, thickness=0.15)
    board.gr_text("ISO1 5-24V", 42.7, 8.7, size=1.0, thickness=0.15)
    board.gr_text("ISO2 5-24V", 54.0, 8.7, size=1.0, thickness=0.15)
    for k in range(4):
        board.gr_text("K%d" % (k + 1), RELAY_X[k] - 7.6, 8.9, size=1.0, thickness=0.15)
        for label, dx in (("NO", -5.0), ("COM", 0.0), ("NC", 5.0)):
            board.gr_text(label, RELAY_X[k] + dx, 8.9, size=1.0, thickness=0.15)
    board.gr_text("RELAYS <= 30V DC 1A", 91.5, 33.5, size=1.0, thickness=0.15)
    labels = {"J506": "FAST1 GND", "J507": "FAST2 GND", "J501": "TTL1 TTL2", "J502": "TTL3 TTL4", "J503": "TTL5 TTL6", "J504": "TTL7 TTL8", "J505": "GND GND"}
    for ref, t in labels.items():
        board.gr_text(t, 169.5, term_y_of(ref), size=1.0, thickness=0.15, rot=90)
    board.gr_text("J5 EXPANSION", 114.0, 48.5, size=1.0, thickness=0.15)
    board.gr_text("star", 99.5, 70.3, size=1.0, thickness=0.15)
    board.gr_text("<- pin 1   FRONT PANEL LINK", 118.0, 96.0, size=1.0, thickness=0.15)
    board.gr_text("AI1 .. AI8", 86.0, 87.6, size=1.0, thickness=0.15, rot=90)
    board.gr_text("A: NMR RECEIVER", 22.0, 62.0, size=1.0, thickness=0.15)
    board.gr_text("B: NMR TX", 169.0, 40.0, size=1.0, thickness=0.15, rot=90)
    board.gr_text("C: EXT POWER / COIL SWITCHES", 149.0, 34.0, size=1.0, thickness=0.15)
    board.gr_text("+VEXT 7-18V DC  FUSE 5A", 134.3, 10.5, size=1.0, thickness=0.15)
    board.gr_text("POWER UP: USB FIRST, THEN BENCH SUPPLY", 148.0, 31.5, size=1.0, thickness=0.15)
    board.gr_text("H-BRIDGE COIL", 146.0, 10.5, size=1.0, thickness=0.15)
    board.gr_text("+VCOIL COIL GND  <=24V (SNUBBER) / <=12V (TVS)", 160.0, 10.5, size=1.0, thickness=0.15)
    place_reference_texts(board)
    if route:
        import router
        router.route_board(board, comps, nets, pad_net, W, H, AGND_POLY, ISO_KEEPOUT,
                           stub_hint={"J1": (0, 1), "J2": (0, -1), "J6": (0, -1)}, layer_hint={"J6": 1},
                           priority_file=os.path.join(HW, ".route_priority.json"))
    return board, comps, nets


def text_box(text, x, y, size=1.0):
    w = 1.05 * size * len(text) + 0.3
    h = 1.5 * size
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def place_reference_texts(board, size=1.0):
    """Put every reference designator on a free spot next to (or, for large parts, inside) its footprint.  Candidates
    around the silk outline are scored by overlap with other footprints' silk/pads, board texts, labels already
    placed and the board edge; the cheapest wins."""
    boxes = [(f, f.silk_bbox()) for f in board.footprints]
    placed = []
    for t in board.text_items:
        tb = text_box(t[0], t[1], t[2], t[3])
        if t[4] % 180 == 90:
            cx, cy = t[1], t[2]
            tb = (cx - (tb[3] - tb[1]) / 2, cy - (tb[2] - tb[0]) / 2, cx + (tb[3] - tb[1]) / 2, cy + (tb[2] - tb[0]) / 2)
        placed.append(tb)

    def overlap(a, b):
        return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))

    for f, bb in boxes:
        if f.ref.startswith(("H", "FID")):
            f.ref_pos = (0, -3.0, 0)
            continue
        w = 1.05 * size * len(f.ref) + 0.3
        h = 1.5 * size
        cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        cands = []
        for g in (0.35, 1.0, 1.8):
            for k in range(-4, 5):
                sx = cx + k * max(w, bb[2] - bb[0]) / 4
                sy = cy + k * max(h, bb[3] - bb[1]) / 4
                cands += [(sx, bb[1] - g - h / 2), (sx, bb[3] + g + h / 2), (bb[0] - g - w / 2, sy), (bb[2] + g + w / 2, sy)]
        big = (bb[2] - bb[0]) * (bb[3] - bb[1]) > 40
        if big:      # inside the body: hidden under the part but never in the way (relays, terminals, modules)
            cands += [(cx, cy), (cx, bb[1] + 0.9 + h / 2), (cx, bb[3] - 0.9 - h / 2)]
        best = None
        for k, (tx, ty) in enumerate(cands):
            tb = (tx - w / 2, ty - h / 2, tx + w / 2, ty + h / 2)
            cost = 0.002 * k + 0.05 * abs(tx - cx) + 0.05 * abs(ty - cy)
            if tb[0] < 0.6 or tb[1] < 0.6 or tb[2] > W - 0.6 or tb[3] > H - 0.6:
                cost += 100
            for p in f.pads:                       # own pads (silk over copper is clipped by the mask)
                cost += overlap(tb, (p.x - p.hx - 0.15, p.y - p.hy - 0.15, p.x + p.hx + 0.15, p.y + p.hy + 0.15)) * 8
            for gf, gb in boxes:
                if gf is f:
                    continue
                if gb[0] > tb[2] + 3 or gb[2] < tb[0] - 3 or gb[1] > tb[3] + 3 or gb[3] < tb[1] - 3:
                    continue
                cost += overlap(tb, gb) * 4
            for pb in placed:
                cost += overlap(tb, pb) * 6
            if best is None or cost < best[0]:
                best = (cost, tx, ty, tb)
        _, tx, ty, tb = best
        placed.append(tb)
        dx, dy = tx - f.x, ty - f.y
        r = math.radians(f.rot)
        px = dx * math.cos(r) - dy * math.sin(r)
        py = dx * math.sin(r) + dy * math.cos(r)
        f.ref_pos = (round(px, 3), round(py, 3), 0)


def term_y_of(ref):
    return {"J506": 13.6, "J507": 25.0, "J501": 36.4, "J502": 47.8, "J503": 59.2, "J504": 70.6, "J505": 82.0}[ref]


def main():
    route = "--no-route" not in sys.argv
    board, comps, nets = build(route)
    out = os.path.join(HW, "class-board.kicad_pcb")
    board.write(out, "class-board")
    print("wrote", out, "footprints", len(board.footprints), "nets", len(board.nets), "tracks", len(board.tracks), "vias", len(board.vias))


if __name__ == "__main__":
    main()
