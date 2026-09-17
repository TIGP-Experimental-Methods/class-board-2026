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
from fp_parse import load_library, load_mixed   # noqa: E402
from pcb_model import Board, FootprintInst      # noqa: E402

HW = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
W, H = 180.0, 100.0          # v0.7 (2026-09-13): +40 mm on the right: section C gets a 41 mm rear strip for its three terminals, section B a 10 mm strip
SOCKET_ROW_SPACING = 25.4        # D-12: assumed for the Jinhua #40729 clone; 22.86 for an official DevKitC-1
# v0.7b (2026-09-16): the dev board moved 10.16 mm (four pin pitches) to the left.  The bottom-side
# panel header J7 stands at x = 90 with its two pad columns 2.54 mm apart -- exactly the socket pitch --
# so a socket pin can never be more than 1.27 mm from a header column.  The socket has to END before
# the header instead, which is what this shift does (last pin x = 86.51, header column x = 88.73).
SOCK_X = 59.20                   # dev-board centre x
SOCK_Y = 54.0                    # dev-board centre y (v0.7b: +4 mm, see RELAY_Y)
J1_Y = SOCK_Y + SOCKET_ROW_SPACING / 2      # front row (J1 header of the dev board)
J3_Y = SOCK_Y - SOCKET_ROW_SPACING / 2      # rear row (J3 header)
PIN1_X = SOCK_X - 26.67

# ---- the front-panel link: three straight 2x20 MALE headers on the BOTTOM side (Decision #45/#48)
# front-panel/ and scripts/gen_panel.py are generated to mate exactly these positions, so the numbers
# below are fixed.  The values are the CENTRE of the 2 x 20 pad block; link_header_at() turns a centre
# into the anchor KiCad stores ("at"), which comes out as (13.27, 25.87) (91.27, ...) (169.27, ...).
LINK_HEADER_FP = "Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical"   # female on the main board (live pins), male on the panel - user 2026-09-17
LINK_HEADER_ROT = 180                      # pin 1 at the rear (small y); the 48 mm block runs along y
LINK_HEADERS = {"J6": (12.0, 50.0), "J7": (90.0, 50.0), "J8": (168.0, 50.0)}
# The header pins go through the board, so nothing on the TOP side may put a pad or a drill in the
# band each header sweeps: two columns at centre_x +- 1.27, y 25.87 .. 74.13.  Keep 2.4 mm from a
# column (header pad radius 0.85 + a through-hole pad radius 1.25 + clearance) and the pins are safe.
LINK_BAND_DX = 2.8
LINK_BAND_Y = (24.6, 75.4)

# ------------------------------------------------------------------ zone polygons (owner rule areas)
ZONES = {
    # v0.7 (2026-09-13): three student sections + base. A = inputs + NMR receiver (old B1 + OPT),
    # B = outputs + timing + NMR transmitter (old B3 + B5).
    # v0.7d (2026-09-17): section C is the FRONT-PANEL board now, so the old ZONE_C of the main
    # board belongs to the instructor and is renamed ZONE_INSTR (power entry B2 + the coil
    # switches of sheet c_switch).  The four relays and the two isolated inputs left the design,
    # which frees the rear strip from x 38 to x 180: the instructor's block is re-laid out in one
    # piece at x 45-86 (it used to be split between a 12 mm pocket and the right-hand edge) and
    # the rear-right, x 96-180, goes to section B, which was the most crowded of the three.
    # v0.7e (2026-09-17, Decision #59 -- even the density before routing): section A was the
    # densest block on the board and the front-right corner (x 130-180, y 68-100) was empty.  The
    # A/B boundary in the front therefore steps out from x 100 to x 113 below y = 71 (section A
    # keeps the room its ADC fan-in needs), section B's analog output block moves 14 mm right into
    # the empty corner and the B5 logic that stood between them moves to the rear-right strip.
    # Above y = 71 the boundary stays at x 100: link header J7 sweeps x 87.2-92.8 down to y 75.4,
    # so nothing of section A can cross it higher up anyway.
    "ZONE_INSTR": [(0.5, 0.5), (96.0, 0.5), (96.0, 36.0), (37.5, 36.0), (37.5, 57.5), (0.5, 57.5)],
    "ZONE_BASE": [(37.5, 36.0), (100.0, 36.0), (100.0, 57.0), (37.5, 57.0)],
    "ZONE_A": [(0.5, 57.5), (45.0, 57.5), (45.0, 57.0), (100.0, 57.0), (100.0, 71.0), (113.0, 71.0),
               (113.0, 99.5), (0.5, 99.5)],
    "ZONE_B": [(96.0, 0.5), (179.5, 0.5), (179.5, 99.5), (113.0, 99.5), (113.0, 71.0), (100.0, 71.0),
               (100.0, 36.0), (96.0, 36.0)],
}

# ---- v0.7e density rework (Decision #59) -----------------------------------------------------
# The NMR receiver (93 footprints in a 40 x 40 mm pocket) is stretched in x about the left edge;
# the output chain it shares with the ADC moves right with the ADC.  U703 is pinned: link header
# J7 sweeps x 87.2-92.8 for y 24.6-75.4 and the IF amplifier sits right against that band.
RX_SPLIT_X = 45.0                # left cluster (stretched) | right-hand output chain (shifted)
RX_X0, RX_STRETCH = 1.0, 1.22    # x' = RX_X0 + (x - RX_X0) * RX_STRETCH: 40 mm of width becomes 47
RX_RIGHT_DX = 12.0
RX_PINNED = {"U703"}
B3_DX = 14.0                     # b3_outputs: into the empty front-right corner

# ---- the rear edge (Decision #46, #50) -----------------------------------------------------
# Every screw terminal on the rear edge is rotated 180 degrees.  The KF301/KF128 footprints draw
# their wire openings (the two arrow marks and the open-sided body outline) on the +y side of the
# footprint, so at rotation 0 the wire enters from the board interior and at 180 from the edge.
TERM_Y = 4.0                 # screw-terminal pad row: 4 mm in, body face flush with the board edge

# ---- the instructor's block (sheet_c_switch, 9xx), v0.7d -------------------------------------
# sheet_c_switch.PLACEMENT draws the three columns of the block (+VEXT input chain, H-bridge,
# polarizer switch) side by side at x 128.5-169 -- where link header J8 and, until v0.7c, the
# relay row stood.  With the relays gone the whole block moves left in one piece, into the strip
# the relays and the isolated inputs left free, and keeps its designed internal geometry.
# C_SHIFT is chosen so that the right-hand column ends before the band link header J7 sweeps
# (x 87.2-92.8) and the left-hand column starts after the B2 power block (x <= 37.5).
C_SHIFT = (-83.0, 0.0)
# the three rear-edge terminals: on the edge (y = TERM_Y) and rotated 180, so the wire enters
# from outside the board (Decision #46).  J903 no longer has to hide on the right edge: the M3
# hole H2 that pushed it there is 90 mm away now.
C_TERMINALS = {"J901": (51.0, TERM_Y, 180), "J903": (62.7, TERM_Y, 180), "J905": (76.9, TERM_Y, 180)}
# ---- individual parts that had to move out of a link-header band or a re-laid-out block -------
# (filled in from scripts/place_check.py; every entry is a part the 2026-09-16 rework displaced)
FIXUP = {
    # v0.7d: section B gets the rear-right strip (x 96-180, y 0.5-36) that the relays used to
    # occupy, so the OPA564 power stage and its output chain move out of the cramped right-hand
    # edge into it -- as one block, translated by (-20, -50) from sheet_nmr_tx.PLACEMENT, which
    # keeps the geometry the circuit was drawn with.  Gains: the +VEXT branch is no longer a
    # column of eight 0603 parts at 2.3 mm pitch squeezed between link header J8 and the board
    # edge, the power stage (the hottest part on the board) sits at the rear edge with air around
    # it, and the TX pair reaches link header J6 (x 12) over a shorter path.
    "U802": (138.00, 12.20, 0),
    "FB802": (146.89, 4.00, 0), "C816": (146.89, 7.21, 0), "C814": (146.89, 9.63, 0),
    "C815": (135.52, 22.28, 0),
    "R809": (146.89, 12.00, 0), "R810": (146.89, 14.32, 0),
    "R811": (146.89, 16.64, 0), "R812": (146.89, 18.96, 0),
    "R813": (144.88, 22.58, 0), "C818": (141.72, 30.49, 0),
    "D801": (144.47, 26.97, 0), "D802": (134.63, 28.09, 0),
    "R814": (147.04, 30.32, 0), "C817": (132.49, 31.23, 0),
    "JP802": (147.33, 33.24, 0), "R815": (136.27, 31.18, 0), "R816": (140.05, 33.24, 0),
    # the 10 MHz TCXO option (eight DNP parts) leaves the TRIG cluster; v0.7e moves it on into the
    # last empty pocket of the rear-right strip, right of the OPA564 block and left of the M3 hole
    "X501": (162.00, 12.00, 0), "R512": (157.00, 10.00, 90), "R513": (167.00, 12.00, 90),
    "C505": (162.00, 16.50, 0), "U504": (162.20, 21.00, 180),
    "R514": (157.00, 20.50, 90), "R515": (167.00, 20.50, 90), "C506": (157.00, 16.00, 90),
    # the I2C expander was under the dev board and on link header J7 in v0.7b; v0.7e puts it in the
    # rear-right strip next to the 74AHCT541 it drives (DIO1-8) and its MOD1-7 test point with it
    "U505": (108.0, 26.0, 0), "C507": (116.0, 26.0, 0), "TP501": (121.0, 26.0, 0),
    # the I2C pull-ups followed the dev board
    "R3": (40.0, 44.5, 0), "R4": (40.0, 47.5, 0),
}
# AGND pour (F.Cu + B.Cu): analog band across the front + the +-12 V / +5VA output area of B2
# (v0.7e: the analog band follows b3_outputs 14 mm to the right, to x 148)
AGND_POLY = [(22.0, 30.0), (37.5, 30.0), (37.5, 57.0), (100.0, 57.0), (100.0, 68.0), (148.0, 68.0), (148.0, 87.5),
             (179.5, 87.5), (179.5, 99.5), (0.5, 99.5), (0.5, 57.0), (22.0, 57.0)]
# AI channel networks in a row between link header J6 (AI1..AI8 on pins 1..15 odd, y 25.9..43.7) and
# the ADC: left -> right = AI1 .. AI8 (planar fan-in, see docs/design-decisions.md D-19).
# v0.7e: 6.2 mm pitch instead of 4.8, so 2.66 mm of gap between clamp bodies for the AIN trace,
# and the row reaches to x 93 -- the front of the board is free that far right once the receiver's
# output chain moves right with it, and the extra width is what lets the receiver itself expand.
NET_ROW_X = {1: 50.0, 2: 56.2, 3: 62.4, 4: 68.6, 5: 74.8, 6: 81.0, 7: 87.2, 8: 93.4}


def dev_pin(row, n):
    """board position of dev-board socket pin n (1..22) of row 'J1' (front) or 'J3' (rear)"""
    return (PIN1_X + 2.54 * (n - 1), J1_Y if row == "J1" else J3_Y)


def link_header_at(lib, ref):
    """the anchor (x, y, rot) that puts link header `ref`'s pad block where the panel expects it.

    A back-side footprint is stored flipped about the x axis, and KiCad rotation is counter-clockwise
    on screen, so the anchor is derived rather than typed in (same arithmetic as pcb_model.PadInst).
    """
    fp = lib[LINK_HEADER_FP]
    cx, cy = LINK_HEADERS[ref]
    xs = [q.x for q in fp.pads]
    ys = [q.y for q in fp.pads]
    lx, ly = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    r = math.radians(LINK_HEADER_ROT)
    dx = lx * math.cos(r) + (-ly) * math.sin(r)
    dy = -lx * math.sin(r) + (-ly) * math.cos(r)
    return round(cx - dx, 3), round(cy - dy, 3), LINK_HEADER_ROT


def in_link_band(x, y, margin=0.0):
    """does a top-side pad at (x, y) sit in the band one of the three bottom-side headers sweeps?"""
    if not (LINK_BAND_Y[0] - margin <= y <= LINK_BAND_Y[1] + margin):
        return False
    return any(abs(x - cx) <= LINK_BAND_DX + margin for cx, _cy in LINK_HEADERS.values())


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

    def put(ref, x, y, rot=0, side="F.Cu"):
        P[ref] = (round(x, 3), round(y, 3), rot) if side == "F.Cu" else (round(x, 3), round(y, 3), rot, side)

    def extent(ref, rot):
        """board-space extent of ref's footprint placed at (0, 0) with this rotation"""
        return rotated_extent(lib[comps[ref].footprint], rot)

    def centre(ref, cx, cy, rot=0):
        """put ref so that the CENTRE of its footprint lands on (cx, cy)"""
        e = extent(ref, rot)
        put(ref, cx - (e[0] + e[2]) / 2.0, cy - (e[1] + e[3]) / 2.0, rot)

    def row(y, x0, items, gap=0.5):
        """pack footprints left to right along y starting at x0 (bbox edge); returns the end x"""
        x = x0
        for ref, rot in items:
            e = extent(ref, rot)
            put(ref, x - e[0], y, rot)
            x += (e[2] - e[0]) + gap
        return x

    def flow(segments, items, gap=0.5, label=""):
        """pack (ref, rot) items into a list of (y, x0, x1) row segments; print what did not fit"""
        left = list(items)
        for (y, x0, x1) in segments:
            x = x0
            while left:
                ref, rot = left[0]
                e = extent(ref, rot)
                w = e[2] - e[0]
                if x + w > x1 + 1e-6:
                    break
                put(ref, x - e[0], y, rot)
                x += w + gap
                left.pop(0)
        if left:
            print("placement: %s did not fit: %s" % (label, ", ".join(r for r, _ in left)))
        return left

    # ---- mechanical ------------------------------------------------------------------
    for ref, (x, y) in zip(("H1", "H2", "H3", "H4"), ((4, 4), (176, 4), (4, 96), (176, 96))):
        put(ref, x, y)
    # fiducials: clear of the three link-header bands (x 12 / 90 / 168, y 25.9 .. 74.1)
    put("FID1", 22, 4); put("FID2", 172.0, 91.0); put("FID3", 54.0, 62.0)

    # ---- BASE: sockets (dev board long axis along x, antenna end at the left) -----------------
    put("J1", SOCK_X, J1_Y, 0)
    put("J2", SOCK_X, J3_Y, 0)
    put("J4", 3.4, 69.0, 90)             # Qwiic, cable exits to the left edge (J3 left the board with the panel rework)
    # 2x10 expansion header (B5 block area, BASE part).  The other agent moved J5 to the standard
    # KiCad PinHeader_2x10 on 2026-09-17; that footprint runs its ten rows along y, where the old
    # class_board footprint ran them along x, so the header is placed rotated and centred on the
    # spot it has always had rather than anchored on pin 1.
    centre("J5", 114.0, 52.0, 90)
    put("NT1", 99.2, 67.5, 90)           # AGND-GND star at the B1/B3 boundary, next to the ADC digital side
    put("R1", 86.4, 62.5, 90)            # 33 R SCLK
    put("R2", 83.8, 62.5, 90)            # 33 R MOSI
    put("R3", 61.5, 34.0, 90)            # I2C pull-ups
    put("R4", 64.0, 34.0, 90)
    # v0.7e: the six base links/test points used to stand at x 42-49, in the only direction the NMR
    # receiver could grow.  They move to the pocket between link header J7's band (pads must stay
    # clear of x 87.2-92.8 down to y 75.4) and the star point NT1 -- which also puts JP1/JP2 next to
    # the J7 pins their LED nets leave on (pins 31/33) instead of 45 mm away.
    put("JP1", 95.5, 69.0, 0)            # LED links (GPIO43/44 -> LED_WIFI/ACT)
    put("JP2", 95.5, 72.5, 0)
    put("TP1", 95.0, 58.5)               # RST
    put("TP2", 98.3, 58.5)               # GND
    put("TP3", 95.0, 61.5)               # +3V3
    put("TP4", 98.3, 61.5)               # +5V_RAW

    # ---- the three panel-link headers, bottom side (Decision #45/#48) --------------------------
    for ref in LINK_HEADERS:
        hx, hy, hrot = link_header_at(lib, ref)
        put(ref, hx, hy, hrot, side="B.Cu")

    # ---- B2 power (x 0.5-37.5, y 0.5-57) ------------------------------------------------
    # Link header J6 sweeps a band at x 8.6-15.4 for y 24.6-75.4 and its pins go through the board,
    # so no top-side pad may stand there.  Everything below y 24.6 keeps its 2026-09-13 place; the
    # rest is re-flowed into the 22 mm strip right of the band (the two +-12 V modules and the
    # output filters) and the 8 mm strip left of it (regulators, LED chains and test points).
    put("J201", 13.0, 5.6, 180)          # USB-C, opening at the rear edge
    put("J202", 27.6, 12.0, 270)         # 5 V jack, opening at the rear edge
    put("R201", 3.0, 10.5, 90); put("R202", 20.0, 10.3, 90)      # CC pull-downs
    put("F201", 7.0, 12.5, 0)
    put("D201", 6.5, 17.5, 90); put("C203", 15.5, 17.0, 90)
    put("U201", 11.0, 21.5, 0)
    put("F202", 28.6, 19.0, 0)
    put("D202", 32.5, 24.0, 90); put("C204", 25.2, 24.0, 90)
    put("U202", 30.0, 25.0, 0)
    put("C201", 20.0, 24.5, 90); put("C202", 22.5, 24.5, 90)       # 22 uF + 100 nF bulk on +5V_RAW
    put("R209", 2.7, 23.3, 90); put("D203", 2.7, 27.5, 90)         # +5V_RAW LED
    # The two +-12 V modules stand on end (rotation 90): their four pins then form one column, which
    # fits between the J6 band and the dev-board socket row and leaves a full-width band below them.
    put("PS201", 16.6, 41.0, 90)         # +12 V module, pin column at x 17.1
    put("PS202", 24.3, 41.0, 90)        # -12 V module, pin column at x 24.85
    put("U204", 20.4, 17.0, 90)          # AMS1117-3.3: too wide for the strip left of the J6 band
    flow([(27.9, 15.7, 37.3)], [("FB201", 0), ("C216", 0), ("FB202", 0), ("C217", 0)],
         gap=0.4, label="B2 module inputs")
    flow([(51.5, 15.7, 37.3)], [("FB203", 90), ("C207", 0), ("C209", 0), ("R203", 90), ("R204", 90), ("R205", 90), ("R211", 0)],
         gap=0.4, label="+12 V filter")
    flow([(55.2, 15.7, 37.3)], [("FB204", 90), ("C206", 0), ("C208", 0), ("R206", 90), ("R207", 90), ("R208", 90), ("R212", 0)],
         gap=0.4, label="-12 V filter")
    # the strip right of the modules; the gap at y 35-39 is the dev-board socket row J2
    flow([(29.5, 31.3, 35.4), (32.8, 31.3, 35.4), (36.1, 31.3, 37.3), (38.0, 31.3, 37.3), (44.5, 31.3, 37.3), (47.5, 31.3, 37.3)],
         [("C213", 0), ("C214", 0), ("C215", 0), ("C210", 0), ("C211", 0)], gap=0.4, label="LDO decoupling")
    flow([(32.0, 0.7, 8.4)], [("TP201", 0), ("TP202", 0)], gap=0.4, label="B2 TP row 1")
    flow([(35.2, 0.7, 8.4)], [("TP203", 0), ("TP204", 0)], gap=0.4, label="B2 TP row 2")
    flow([(38.4, 0.7, 8.4)], [("TP205", 0), ("TP206", 0)], gap=0.4, label="B2 TP row 3")
    flow([(42.6, 0.7, 8.4)], [("U203", 0)], label="78L05")
    flow([(47.6, 0.7, 8.4)], [("D205", 90), ("D206", 90)], gap=0.4, label="rail LEDs")
    flow([(52.6, 0.7, 8.4)], [("R210", 0), ("D204", 90)], gap=0.4, label="+3V3 LED")
    flow([(56.2, 0.7, 8.4)], [("C212", 0)], label="78L05 output cap")

    # ---- B5 digital I/O; the TTL/FAST terminals left with the panel rework ---------------------
    # v0.7e: the 74AHCT541 TTL output block (20 + 16 pads in one 8 x 8 mm pocket) was the second
    # densest spot on the board and stood between J5 and the dev-board socket.  It moves into the
    # empty rear-right strip x 98-122, y 6-32 together with the expander that drives it (FIXUP),
    # which leaves x 100-130 / y 36-70 as a wide-open lane for the SPI and TTL escapes.
    put("U501", 108.0, 12.0, 270)         # 74AHCT541: inputs on the left column, outputs facing R501-R508
    for i in range(8):
        put("R50%d" % (i + 1), 116.0 + (i % 2) * 3.5, 8.0 + (i // 2) * 2.4, 0)
    put("C501", 101.0, 12.0, 90)
    # the fast/TRIG cluster stays under J5, spread over the full width of the lane
    put("U502", 105.6, 61.5, 0)           # 74HCT125 fast outs (pins up/down)
    put("R509", 101.0, 57.6, 90); put("R510", 101.0, 61.0, 90); put("C502", 110.0, 58.0, 90)
    put("JP501", 104.0, 67.0, 0)          # GPIO44 / U502 1Y select
    put("D501", 112.5, 66.5, 0)           # BAV99 clamp on TRIG_5V (SOT-23)
    put("U503", 119.0, 61.0, 90)          # LVC1T45 (TRIG)
    put("C503", 114.0, 61.0, 90); put("C504", 124.0, 61.0, 90); put("R511", 127.5, 61.0, 0)
    put("X501", 124.6, 59.5, 0); put("R512", 119.5, 57.6, 90); put("R513", 128.0, 59.5, 90); put("C505", 124.6, 63.0, 0)
    put("U504", 124.8, 66.0, 180); put("R514", 121.5, 65.5, 90); put("R515", 128.0, 65.5, 90); put("C506", 118.5, 65.5, 90)
    # v0.7b: the TCA9535 expander used to sit under the dev board at x 94.5, which is (a) outside
    # ZONE_B (the owner_B assertion failed) and (b) on top of link header J7.  It moves to the free
    # pocket between the B5 column and the NMR transmitter, inside ZONE_B.
    put("U505", 127.3, 41.3, 0)           # TSSOP-24 (moved by FIXUP)
    put("C507", 127.3, 46.6, 0)           # +3V3 decoupling beside the expander
    put("TP501", 131.5, 74.0)             # EXP_P14 = Johnson-counter /CLR, the only expander test point left

    # ---- B3 signal generation (right-front) -------------------------------------------------
    # v0.7e: the block keeps its internal geometry and moves B3_DX = 14 mm right, into the corner
    # that the relay rework left empty.  AO1/AO2 reach link header J6 on the far left either way;
    # 14 mm on two nets buys 25 footprints' worth of density out of the middle of the board.
    def put3(ref, x, y, rot=0):
        put(ref, x + B3_DX, y, rot)
    put3("U302", 105.6, 72.5, 0)          # 74HCT125 level shifter
    put3("C308", 109.4, 73.4, 90)
    put3("U301", 114.0, 74.8, 0)          # DAC8563 (VSSOP-10)
    put3("C301", 111.3, 69.7, 90); put3("C302", 110.5, 77.4, 90); put3("C303", 117.5, 76.0, 90); put3("R311", 117.5, 71.0, 90)
    put3("U303", 114.0, 83.0, 0)          # OPA2192 (SOIC-8)
    put3("C304", 119.3, 80.0, 0); put3("C306", 119.3, 82.6, 0); put3("C305", 119.3, 85.2, 0); put3("C307", 119.3, 88.0, 0)
    put3("R301", 106.5, 80.0, 90); put3("R302", 106.5, 83.4, 90); put3("R305", 106.5, 86.8, 90); put3("R306", 106.5, 90.2, 90)
    put3("R303", 109.2, 81.0, 90); put3("R307", 109.2, 87.0, 90)
    put3("R304", 109.2, 90.5, 90); put3("R308", 112.0, 91.5, 0)
    put3("R309", 123.3, 84.0, 0); put3("D301", 127.0, 84.0, 90); put3("R310", 123.3, 89.0, 0); put3("D302", 127.0, 89.0, 90)
    put3("TP301", 121.0, 93.5)

    # ---- B1 inputs (centre-front) ---------------------------------------------------------
    # v0.7e: the ADC and its left-hand decoupling move 3 mm right, so that the package sits in the
    # middle of the wider AI clamp row; C102/C103/R101 and U703 (the receiver's IF amplifier, which
    # cannot move -- link header J7) pin the right-hand side, so the DVDD pair moves above the
    # package instead of beside it.
    put("U101", 68.0, 76.0, 270)          # ADS8688
    put("C104", 58.5, 74.5, 90); put("C101", 58.5, 77.8, 90)
    put("C105", 54.5, 74.5, 90); put("C106", 54.5, 79.8, 90)
    put("C103", 75.5, 75.5, 90); put("C102", 75.5, 79.5, 90)
    put("C107", 71.0, 69.4, 0); put("C108", 75.5, 69.4, 0)           # DVDD 10 uF + 100 nF above the package
    put("R101", 73.2, 79.0, 90); put("R102", 54.3, 69.0, 0)
    for ai, x in NET_ROW_X.items():          # AI clamp networks, left -> right = AI1 .. AI8
        put("R11%d" % ai, x, 90.5, 90)
        put("C11%d" % ai, x, 87.6, 0)
        put("D11%d" % ai, x, 84.2, 90)
    put("JP101", 106.0, 89.5, 90); put("JP102", 106.0, 95.0, 90)    # AI7/AI8 source select (v0.7e: +8.5)
    put("TP101", 99.5, 95.0)

    # ---- placements contributed by the extra sheet modules (scripts/sheet_*.py, PLACEMENT dict) ----
    for mod in sheet_modules():
        for ref, pos in getattr(mod, "PLACEMENT", {}).items():
            P[ref] = (round(pos[0], 3), round(pos[1], 3), pos[2] if len(pos) > 2 else 0)

    # ---- the instructor's block (sheet_c_switch): translated into the freed rear strip ---------
    import sheet_c_switch
    for ref, pos in sheet_c_switch.PLACEMENT.items():
        put(ref, pos[0] + C_SHIFT[0], pos[1] + C_SHIFT[1], pos[2] if len(pos) > 2 else 0)
    for ref, pos in C_TERMINALS.items():
        put(ref, pos[0], pos[1], pos[2])
    # ---- parts of the two NMR sheets that would stand on a link header -----------------------
    for ref, pos in FIXUP.items():
        put(ref, pos[0], pos[1], pos[2])
    # ---- v0.7e: give the NMR receiver the room the base links and the ADC row gave up ---------
    # sheet_nmr_rx.PLACEMENT draws the receiver as rows of 0603 parts at ~2 mm pitch in a 40 mm
    # wide pocket; an x-stretch about the left edge keeps every row, every group and the order of
    # the circuit exactly as drawn and simply opens the gaps (2.0 -> 2.3 mm between bodies).  The
    # output chain on the right (the mixer/IF parts that feed the ADC) follows the ADC instead.
    for ref, comp in (comps or {}).items():
        if ref not in P or comp.fields.get("Block") != "NMR_RX" or ref in RX_PINNED:
            continue
        pos = P[ref]
        if pos[0] < RX_SPLIT_X:
            x = RX_X0 + (pos[0] - RX_X0) * RX_STRETCH
        else:
            x = pos[0] + RX_RIGHT_DX
        P[ref] = (round(x, 3),) + tuple(pos[1:])
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
    # the netlist mixes the project library with KiCad's own (chip R/C since Decision #47, the relay
    # and the three panel headers since #50/#48); every footprint keeps the nickname it came from
    lib = load_mixed(os.path.join(HW, "lib", "class_board.pretty"),
                     [c.footprint for c in comps.values()] + [LINK_HEADER_FP])
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
        fp = lib[comp.footprint]
        pos = P[ref]
        x, y, rot = pos[0], pos[1], pos[2]
        side = pos[3] if len(pos) > 3 else "F.Cu"
        nets_by_pad = {}
        for pad in fp.pads:
            n = pad_net.get((ref, pad.number))
            if n:
                nets_by_pad[pad.number] = n
                board.net(n)
        cdict = dict(value=comp.value, datasheet=comp.datasheet, description=comp.description,
                     fields={k: v for k, v in comp.fields.items() if k not in ("Reference", "Value")},
                     path=comp.path, sheetname=comp.sheetname, sheetfile=comp.sheetfile, dnp=comp.dnp, in_bom=comp.in_bom)
        board.add_footprint(FootprintInst(ref, fp, x, y, rot, cdict, nets_by_pad, side=side))
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
    # silkscreen
    board.gr_text("TIGP CLASS BOARD 2026 rev B (v0.7d)", 60.0, 45.0, size=1.5, thickness=0.2)
    board.gr_text("ESP32-S3-DevKitC-1 (Jinhua #40729)   antenna <-   -> USB", 60.0, 50.0, size=1.0, thickness=0.15)
    board.gr_text("5V IN", 29.5, 17.0, size=1.0, thickness=0.15)
    board.gr_text("USB-C 5V", 13.0, 9.2, size=1.0, thickness=0.15)
    board.gr_text("J5 EXPANSION", 114.0, 48.5, size=1.0, thickness=0.15)
    board.gr_text("star", 99.5, 70.3, size=1.0, thickness=0.15)
    board.gr_text("AI1 .. AI8", 86.0, 87.6, size=1.0, thickness=0.15, rot=90)
    board.gr_text("A: NMR RECEIVER", 22.0, 62.0, size=1.0, thickness=0.15)
    board.gr_text("B: NMR TX", 175.0, 60.0, size=1.0, thickness=0.15, rot=90)
    board.gr_text("INSTRUCTOR: POWER + COIL SWITCHES", 60.0, 38.5, size=1.0, thickness=0.15)
    board.gr_text("NO MAINS ON THIS BOARD", 155.0, 90.0, size=1.0, thickness=0.15)
    board.gr_text("MOD1-7 -> 5V TTL ON THE PANEL", 155.0, 93.5, size=1.0, thickness=0.15)
    board.gr_text("+VEXT 7-18V DC  FUSE 5A", 51.0, 8.7, size=1.0, thickness=0.15)
    board.gr_text("POWER UP: USB FIRST, THEN BENCH SUPPLY", 60.0, 55.0, size=1.0, thickness=0.15)
    board.gr_text("H-BRIDGE COIL", 62.7, 8.7, size=1.0, thickness=0.15)
    board.gr_text("+VCOIL COIL GND  <=24V", 76.9, 8.7, size=1.0, thickness=0.15)
    # the three panel-link headers are on the bottom; label them on the back silkscreen
    for ref, (cx, cy) in LINK_HEADERS.items():
        board.gr_text("%s  PANEL LINK  pin 1 ->" % ref, cx, cy - 27.5, layer="B.SilkS", size=1.0, thickness=0.15, mirror=True)
    place_reference_texts(board)
    if route:
        import router
        router.route_board(board, comps, nets, pad_net, W, H, AGND_POLY, ((0.0, 0.0), (0.0, 0.0)),
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


def main():
    route = "--no-route" not in sys.argv
    board, comps, nets = build(route)
    out = os.path.join(HW, "class-board.kicad_pcb")
    board.write(out, "class-board")
    print("wrote", out, "footprints", len(board.footprints), "nets", len(board.nets), "tracks", len(board.tracks), "vias", len(board.vias))


if __name__ == "__main__":
    main()
