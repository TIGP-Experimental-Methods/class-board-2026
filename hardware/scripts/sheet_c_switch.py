"""C sheet (v0.7): external power input, DRV8871 field-cycling H-bridge, polarizer MOSFET switch.

Source: notes/2026-09-13-v07-nmr-circuits.md sections 5 (H-bridge), 6 + 6.1 (polarizer switch and
the three flyback stuffing options), 7 (external power input) and 8 (grounding).  Everything on this
sheet sits on GND (never AGND): the coil returns are the noisiest currents on the board.

Reference range 9xx (coil switches / external power).  Block = C_SW -> ZONE_C (rules/class-board.dru
rule "owner_C").  Imported by gen_sch.main() and gen_pcb.sheet_modules().

Layout (2026-09-17 spacing rework, layout only -- no circuit change):  the sheet is on A2 so the three
boxed sections, the silkscreen-notes column and the flyback table each get their own clear region.
Rules applied: rail/ground symbols only ever sit on their own stub (c.tap / c.pwr_L / c.comb), passive
columns at >= 10.16 mm pitch, every net label anchored at a wire END and staggered so no label box
crosses a wire, free text collected at the foot of each box, clear of symbols, wires and title block.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cb_sch import Sheet, Inst, g                       # noqa: E402,F401
from cb_symbols import SYMBOLS                          # noqa: E402
from gen_sch import Ctx, sheet_frame, auto_junctions    # noqa: E402

BLOCK = "C_SW"            # -> ZONE_C


def _sym(*names):
    """first library symbol that exists (lets a later cb_symbols addition replace a substitute)"""
    for n in names:
        if n in SYMBOLS:
            return n
    return names[-1]


# values the v0.7 circuit document asks for that are not yet in cb_symbols.SYMBOLS: the preferred name
# is tried first, the substitute (same footprint, nearest stocked value) is used until it appears.
SYM_R32K = _sym("R0603_32k", "R0603_32R0k", "R0603_40R2k")      # R920 ILIM: 32.0 k 1 % -> I_TRIP 2.0 A
SYM_R47K = _sym("R0603_47k", "R0603_100k")                      # R940 P-FET gate pull-down
SYM_R10 = _sym("R0603_10", "R0603_10R", "R0603_100")            # R932 gate resistor (doc: "10 R, pad for 100 R")
SYM_CP100 = _sym("CP_100uF_50V", "CP_100uF_35V")                # C921 / C940 bulk
SYM_R2512 = _sym("R2512_0R", "R2512_0", "R2512_10mR")           # R933 link: 0 R fitted, 10 mOhm is the option


def _fld(inst, name, x, y, rot=0, just="left bottom"):
    """move one Reference/Value text of a placed symbol to clear space (layout only)."""
    inst.field_pos[name] = (x, y, rot, just)
    return inst


def build(root_uuid):
    sh = Sheet("c_switch", "C: external power input, DRV8871 field-cycling H-bridge, polarizer MOSFET switch",
               "A2", 12,
               "J901 7-18 V -> fuse + TVS + P-FET -> +VEXT; DRV8871 to J903; UCC27517 + AOD4184A to J905")
    c = Ctx(sh, BLOCK, 9000)
    sheet_frame(sh, BLOCK, "C (9xx) — EXTERNAL POWER INPUT, FIELD-CYCLING H-BRIDGE, POLARIZER SWITCH", [
        "Input (7): J901 -> F901 5 A fast (0466005.NRHF) -> D931 SMBJ26A (26 V standoff > the 24 V maximum input; the fuse limits the TVS fault current) -> Q901 AOD4185 reverse-polarity P-FET (15 mOhm: 0.375 W at 5 A against 2.75 W for a Schottky) -> +VEXT.",
        "D932 BZX84C12 clamps V_GS of Q901 (AOD4185 maximum +-20 V); R940 enhances the P-FET. C940 + C941 are the +VEXT bulk; D933/R941 show the rail. Loads on +VEXT: OPA564 V+ (NMR TX), DRV8871 VM, UCC27517 VDD. Nothing else.",
        "H-bridge (5): U903 DRV8871, VM = +VEXT. C921 100 uF is sized for the 25 us internal t_OFF window (C = I dt / dV = 2 A x 25 us / 0.5 V); C920 100 nF at the pin. R920 sets I_TRIP = 64 / R_ILIM(kOhm); 1 % because the trip point is directly proportional to it. R921/R922 hold IN1/IN2 low at reset = coast.",
        "D920 SMBJ26A sits VM -> GND, NOT across the coil: the bridge has integral body diodes, so the coil freewheels inside the part and the only real risk is supply pumping (1/2 L I^2 = 1.8 mJ into 100 uF from 15 V = 1.2 V rise). The clamp must fire below the DRV8871's 45 V maximum, which is why the brief's SMBJ58A is wrong here.",
        "Polarizer (6): FET_GATE -> R930 pull-down + R931 damping -> U904 UCC27517 (4 A driver) -> R932 -> Q904 AOD4184A (40 V, 13 A, 7 mOhm). JP904 picks the driver supply: +VEXT (default, V_GS = 12-18 V, R_DS(on) at its 10 V spec point) or +5V_RAW.",
        "Flyback (6.1), one footprint set, three stuffing options: (a) D930 SS54 freewheel, tau = L/R = 2.6 ms — fitted by default; (b) the RC snubber (the Michal route, 2.2 R 5 W + 4700 uF 50 V) over-damped at ~10 ms, +VCOIL <= 24 V — wired EXTERNALLY across J905 pins 1-2, the parts are too big for the board; (c) D934 SMBJ20A fast dump, 591 us, +VCOIL <= 12 V.",
        "R933 is the optional 10 mOhm Kelvin shunt in the source return (13.4 A x 10 mOhm = 134 mV = 5 % of the ADS8688 +-2.56 V range, so no divider) brought out as ISENSE_COIL for a spare ADC channel. It is fitted as a 0 R link by default so the source return is never open.",
        "Everything on this sheet is on GND (grounding note 8.1/8.2): up to 13 A of polarizer return must never touch the AGND pour. Route the coil pairs tight — TX out and return together, loop area under 1 cm2.",
    ])

    # =============================================================== 7. EXTERNAL POWER INPUT
    sh.box(20, 58, 240, 158, None)
    sh.text("EXTERNAL POWER INPUT (design 7): J901 -> F901 -> D931 -> Q901 -> +VEXT", 22, 56, 2.0, True)

    yTOP = 78.74                        # the fused +VIN rail
    J01 = c.place("J901", "KF301-5.0-2P", 33.02, yTOP + 1.27, 0)
    vin = sh.stub(J01, 1, 7.62)         # -> (48.26, yTOP)
    sh.label("VIN", vin[0], vin[1], 0)
    c.pwr_L(J01, 2, "GND", 6.35, 8.89)  # right 6.35, then down to its own GND symbol

    F01 = c.place("F901", _sym("FUSE_0466005"), 63.5, yTOP, 90)   # pin 1 left, pin 2 right
    _fld(F01, "Reference", 59.69, 72.39, 90)
    _fld(F01, "Value", 59.69, 68.58, 90)
    sh.wire(vin[0], vin[1], F01.pin_pos(1)[0], F01.pin_pos(1)[1])
    nf = sh.stub(F01, 2, 6.35)          # -> (73.66, yTOP)
    sh.label("VIN_F", nf[0], nf[1], 0)

    x_tvs = 88.9
    x_zen = 104.14
    x_q = 137.16
    y_gate = yTOP + 22.86               # 101.6: the P-FET gate rail
    y_ext = yTOP + 25.4                 # 104.14: the +VEXT rail

    # the fused +VIN line runs right to the P-FET source
    Q01 = c.place("Q901", "AOD4185", x_q, yTOP + 5.08, 0)         # S up, D down, G left
    sx, sy = Q01.pin_pos(3)
    sh.wire(nf[0], yTOP, sx, yTOP)                                # ends on the source pin

    D31 = c.place("D931", "SMBJ26A", x_tvs, yTOP + 12.7, 270)     # K up (pin 1), A down to GND
    sh.wire(D31.pin_pos(1)[0], D31.pin_pos(1)[1], D31.pin_pos(1)[0], yTOP)
    c.pwr_pin(D31, 2, "GND", 5.08)
    _fld(D31, "Reference", 92.71, 88.90, 90)
    _fld(D31, "Value", 92.71, 93.98, 90)

    gx, gy = Q01.pin_pos(1)
    x_g = x_q - 15.24
    sh.path((gx, gy), (x_g, gy), (x_g, y_gate), (x_zen, y_gate))

    D32 = c.place("D932", "BZX84C12", x_zen, yTOP + 11.43, 270)   # K (pin 3) up to the source, A (pin 1) down to the gate
    sh.wire(D32.pin_pos(3)[0], D32.pin_pos(3)[1], D32.pin_pos(3)[0], yTOP)
    sh.wire(D32.pin_pos(1)[0], D32.pin_pos(1)[1], D32.pin_pos(1)[0], y_gate)
    _fld(D32, "Reference", 107.95, 87.63, 90)
    _fld(D32, "Value", 107.95, 92.71, 90)
    # D932 pin 2 (NC) is a hidden no-connect pin in the symbol: no NC flag (KiCad calls that dangling).

    R40 = c.place("R940", SYM_R47K, 111.76, y_gate + 8.89, 0)
    sh.wire(R40.pin_pos(1)[0], R40.pin_pos(1)[1], R40.pin_pos(1)[0], y_gate)
    c.pwr_pin(R40, 2, "GND", 5.08)

    # +VEXT node: drain -> the rail, decoupling and the indicator hang DOWN, the rail symbol taps UP
    dx, dy = Q01.pin_pos(2)
    sh.wire(dx, dy, dx, y_ext)
    x_vext_end = 213.36
    sh.wire(dx, y_ext, x_vext_end, y_ext)
    c.tap(198.12, y_ext, "PWR_FLAG", 6.35)
    c.tap(x_vext_end, y_ext, "+VEXT", 6.35)
    for ref, lib, x in (("C940", SYM_CP100, 154.94), ("C941", "C0603_100nF", 170.18)):
        cap = c.place(ref, lib, x, y_ext + 8.89, 0)
        sh.wire(cap.pin_pos(1)[0], cap.pin_pos(1)[1], cap.pin_pos(1)[0], y_ext)
        c.pwr_pin(cap, 2, "GND", 5.08)
    R41 = c.place("R941", "R0603_4R7k", 185.42, y_ext + 8.89, 0)
    sh.wire(R41.pin_pos(1)[0], R41.pin_pos(1)[1], R41.pin_pos(1)[0], y_ext)
    D33 = c.place("D933", "LED_GREEN_0805", 185.42, y_ext + 20.32, 90)   # A up, K down
    sh.wire(R41.pin_pos(2)[0], R41.pin_pos(2)[1], D33.pin_pos(2)[0], D33.pin_pos(2)[1])
    _fld(D33, "Reference", 196.85, 121.92, 90)
    _fld(D33, "Value", 196.85, 127.00, 90)
    c.pwr_pin(D33, 1, "GND", 5.08)

    sh.text("D932 clamps V_GS to 12 V (AOD4185 maximum +-20 V); R940 enhances the P-FET", 24, 142, 1.3)
    sh.text("+VEXT rail LED: (24 - 2) / 4.7k = 4.7 mA at 24 V, 1.1 mA at 7 V", 24, 147, 1.3)
    sh.text("SILKSCREEN at J901:  +VEXT 7-18 V  (24 V only with U802 not fitted — the OPA564 absolute maximum supply is 26 V)",
            24, 152.5, 1.5, True)

    # =============================================================== 5. H-BRIDGE
    sh.box(250, 58, 458, 186, None)
    sh.text("FIELD-CYCLING H-BRIDGE (design 5): DRV8871, VM = +VEXT", 252, 56, 2.0, True)

    U03 = c.place("U903", "DRV8871DDAR", 370.84, 125.73, 0)
    # --- VM rail above the part: the decoupling hangs down, the rail symbol taps up at the far end
    vm = sh.stub(U03, 5, 12.7)                  # -> (370.84, 99.06)
    x_vmL = 320.04
    sh.wire(x_vmL, vm[1], vm[0], vm[1])
    c.tap(x_vmL, vm[1], "+VEXT", 6.35)
    for ref, lib, x in (("C920", "C0603_100nF", 358.14), ("C921", SYM_CP100, 345.44)):
        cap = c.place(ref, lib, x, vm[1] + 6.35, 0)
        sh.wire(cap.pin_pos(1)[0], cap.pin_pos(1)[1], cap.pin_pos(1)[0], vm[1])
        c.pwr_pin(cap, 2, "GND", 5.08)
    D20 = c.place("D920", "SMBJ26A", 332.74, vm[1] + 6.35, 270)
    sh.wire(D20.pin_pos(1)[0], D20.pin_pos(1)[1], D20.pin_pos(1)[0], vm[1])
    c.pwr_pin(D20, 2, "GND", 5.08)
    _fld(D20, "Reference", 320.04, 102.87, 90)
    _fld(D20, "Value", 320.04, 107.95, 90)

    # --- logic inputs and ILIM: three lanes of decreasing length so no pull-down leg crosses a lane
    y_res = 138.43                              # the pull-down row, all three at one height
    for pin, ref, lib, net, x_lane, x_res, kind in (
            (3, "R921", "R0603_10k", "HB_IN1", 304.80, 312.42, "global"),
            (2, "R922", "R0603_10k", "HB_IN2", 330.20, 337.82, "global"),
            (4, "R920", SYM_R32K, "ILIM", 350.52, 356.87, "local")):
        px, py = U03.pin_pos(pin)
        sh.wire(px, py, x_lane, py)
        sh.label(net, x_lane, py, 180, kind)
        r = c.place(ref, lib, x_res, y_res, 0)
        sh.wire(r.pin_pos(1)[0], r.pin_pos(1)[1], r.pin_pos(1)[0], py)
        c.pwr_pin(r, 2, "GND", 5.08)

    # --- the three ground pins share one comb, one symbol below the part
    c.comb(U03, [1, 7, 9], "GND", 7.62, 7.62)
    _fld(U03, "Value", 377.19, 158.75)
    _fld(U03, "Reference", 377.19, 113.54)

    # --- outputs -> coil terminal, labels on their own staggered wire ends
    J03 = c.place("J903", "KF301-5.0-2P", 417.83, U03.y - 2.54, 0, mirror="y")
    for pin, tpin, net, x_lbl in ((6, 1, "HB_OUT1", 387.35), (8, 2, "HB_OUT2", 398.78)):
        a = U03.pin_pos(pin)
        b = J03.pin_pos(tpin)
        sh.wire(a[0], a[1], x_lbl, a[1])
        sh.wire(x_lbl, a[1], b[0], b[1])
        sh.label(net, x_lbl, a[1], 0)

    sh.text("J903: 1 = OUT1, 2 = OUT2 (field-cycling coil, <= 3.6 A peak)", 384, 140, 1.3)
    sh.text("C921 100 uF: 2 A x 25 us / 0.5 V. D920 clamps VM below the 45 V maximum (SMBJ58A would not).",
            254, 166, 1.3)
    sh.text("I_TRIP(A) = 64 / R_ILIM(kOhm)  —  32.0 k = 2.0 A (default), 17.8 k = 3.6 A, 15 k minimum",
            254, 171, 1.3)
    sh.text("PowerPAD (pad 9 = EP): 3 x 3 array of 0.3 mm vias on a 1.0 mm grid to the bottom GND plane (datasheet 10.1); OUT traces >= 2 mm.",
            254, 176, 1.2)

    # =============================================================== 6. POLARIZER SWITCH
    sh.box(20, 200, 458, 316, None)
    sh.text("POLARIZER MOSFET SWITCH (design 6 / 6.1): UCC27517 -> AOD4184A, three flyback options", 22, 198, 2.0, True)

    U04 = c.place("U904", "UCC27517DBVR", 160.02, 262.89, 0)

    # --- driver supply select, all of it above the driver
    vdd = sh.stub(U04, 1, 12.7)                 # -> (160.02, 238.76)
    JP = c.place("JP904", "SolderJumper_3_Bridged12", vdd[0], vdd[1] - 3.81, 0)
    c.pwr_L(JP, 1, "+VEXT", 10.16, 7.62)        # out then up: the rail symbol never sits beside a part
    c.pwr_L(JP, 3, "+5V_RAW", 15.24, 7.62)
    _fld(JP, "Value", 121.92, 243.84)           # the long jumper value text off the VDD rail
    x_vdd_end = 205.74
    sh.wire(vdd[0], vdd[1], x_vdd_end, vdd[1])
    sh.label("VDD904", x_vdd_end, vdd[1], 0)
    c.tap(196.85, vdd[1], "PWR_FLAG", 6.35)     # JP904 feeds VDD904 through passive pins: flag it as driven
    for ref, lib, x in (("C930", "C0603_1uF", 172.72), ("C931", "C0603_100nF", 185.42)):
        cap = c.place(ref, lib, x, vdd[1] + 6.35, 0)
        sh.wire(cap.pin_pos(1)[0], cap.pin_pos(1)[1], cap.pin_pos(1)[0], vdd[1])
        c.pwr_pin(cap, 2, "GND", 5.08)
    c.pwr_pin(U04, 2, "GND", 7.62)              # driver GND straight down, on its own
    c.pwr_L(U04, 4, "GND", 5.08, 12.7)          # IN- tied low on its own leg

    # --- input: FET_GATE -> R930 pull-down + R931 series
    e3 = U04.pin_pos(3)
    R31 = c.place("R931", "R0603_100", 140.97, e3[1], 90)         # pin 1 left, pin 2 right
    sh.wire(R31.pin_pos(2)[0], R31.pin_pos(2)[1], e3[0], e3[1])
    n31 = R31.pin_pos(1)
    x_fg = 111.76
    sh.wire(n31[0], n31[1], x_fg, n31[1])
    sh.label("FET_GATE", x_fg, n31[1], 180, "global")
    R30 = c.place("R930", "R0603_10k", 124.46, n31[1] + 8.89, 0)
    sh.wire(R30.pin_pos(1)[0], R30.pin_pos(1)[1], R30.pin_pos(1)[0], n31[1])
    c.pwr_pin(R30, 2, "GND", 5.08)
    _fld(R31, "Reference", 137.16, 256.54, 90)
    _fld(R31, "Value", 137.16, 269.24, 90)

    # --- output: R932 -> Q904 gate
    e5 = U04.pin_pos(5)
    R32 = c.place("R932", SYM_R10, 175.26, e5[1], 90)             # pin 1 left (at OUT), pin 2 right
    sh.wire(e5[0], e5[1], R32.pin_pos(1)[0], R32.pin_pos(1)[1])
    Q04 = c.place("Q904", "AOD4184A", 224.79, e5[1] - 2.54, 0)    # G left, D up, S down
    _fld(R32, "Reference", 171.45, 269.24, 90)
    _fld(R32, "Value", 180.34, 269.24, 90)
    g4 = Q04.pin_pos(1)
    sh.wire(R32.pin_pos(2)[0], R32.pin_pos(2)[1], g4[0], g4[1])

    # --- drain = COIL node, source = the shunt return
    d4 = Q04.pin_pos(2)
    y_coil = 233.68
    y_vcoil = 213.36
    x_j5 = 320.04
    sh.wire(d4[0], d4[1], d4[0], y_coil)
    sh.label("COIL", d4[0], y_coil, 0)
    x_coil_end = 294.64                          # where J905 pin 2 drops onto the COIL rail
    sh.wire(d4[0], y_coil, x_coil_end, y_coil)

    D34 = c.place("D934", "SMBJ20A", 243.84, y_coil + 6.35, 270)  # K up (COIL), A down (GND)
    sh.wire(D34.pin_pos(1)[0], D34.pin_pos(1)[1], D34.pin_pos(1)[0], y_coil)
    c.pwr_pin(D34, 2, "GND", 5.08)
    _fld(D34, "Reference", 247.65, 237.49, 90)
    _fld(D34, "Value", 247.65, 242.57, 90)

    D30 = c.place("D930", "SS54", 266.7, y_coil - 10.16, 270)     # A down (COIL), K up (+VCOIL)
    sh.wire(D30.pin_pos(1)[0], D30.pin_pos(1)[1], D30.pin_pos(1)[0], y_coil)
    sh.wire(D30.pin_pos(2)[0], D30.pin_pos(2)[1], D30.pin_pos(2)[0], y_vcoil)
    _fld(D30, "Reference", 270.51, 220.98, 90)
    _fld(D30, "Value", 270.51, 226.06, 90)

    J05 = c.place("J905", "KF301-5.0-3P", x_j5, y_vcoil + 2.54, 0, mirror="y")
    p1, p2 = J05.pin_pos(1), J05.pin_pos(2)
    sh.wire(254.0, y_vcoil, p1[0], p1[1])        # +VCOIL rail: symbol tap, flag tap, then J905 pin 1
    c.tap(254.0, y_vcoil, "+VCOIL", 6.35)
    c.tap(279.4, y_vcoil, "PWR_FLAG", 6.35)
    sh.path(p2, (x_coil_end, p2[1]), (x_coil_end, y_coil))
    c.pwr_L(J05, 3, "GND", 7.62, 7.62)

    s4 = Q04.pin_pos(3)
    y_isense = s4[1] + 5.08
    sh.wire(s4[0], s4[1], s4[0], y_isense)
    R33 = c.place("R933", SYM_R2512, s4[0], y_isense + 3.81, 0,
                  value=None if SYM_R2512 != "R2512_10mR" else "0R (10 mOhm shunt option)")
    _fld(R33, "Reference", 219.71, 273.05)
    c.pwr_pin(R33, 2, "GND", 5.08)
    sh.wire(s4[0], y_isense, 254.0, y_isense)
    sh.label("ISENSE_COIL", 254.0, y_isense, 0, "global")

    sh.text("J905: 1 = +VCOIL (external supply +), 2 = COIL (drain), 3 = GND — the coil goes between 1 and 2.",
            336, 206, 1.3)
    sh.text("Option (b), the RC snubber, is OFF-BOARD: 2.2 R 5 W in series with 4700 uF 50 V, wired externally",
            330, 243, 1.3, True)
    sh.text("across J905 pins 1-2 (drain to +VCOIL). The 31 x 10 mm resistor and the 22 mm capacitor do not fit",
            330, 247.5, 1.3)
    sh.text("on the board (a scan of the whole outline finds no free 22.5 x 22.5 mm square outside this strip).",
            330, 252, 1.3)
    sh.text("JP904 default = pins 1-2 bridged: VDD = +VEXT (V_GS 12-18 V). Cut and bridge 2-3 for +5V_RAW.",
            24, 292, 1.3)
    sh.text("R930 keeps the polarizer off unless driven; R931 damps the edge into the driver input.",
            24, 297, 1.3)
    sh.text("R933 is FITTED as a 0 R 2512 link (it is the polarizer source return and must never be open).",
            24, 302, 1.3, True)
    sh.text("Swap it for the 10 mOhm shunt (1.8 W at 13.4 A, 134 mV = 5 % of the ADS8688 +-2.56 V range) to use ISENSE_COIL.",
            24, 307, 1.2)

    # --- flyback option table, in free space below the polarizer box
    rows = [["Option", "Parts", "Decay", "Peak drain", "+VCOIL limit"],
            ["(a) freewheel diode (default)", "D930 SS54 fitted", "tau = L/R = 2.6 ms", "+VCOIL + 0.6 V", "24 V"],
            ["(b) RC snubber (Michal) — OFF-BOARD", "2.2R 5W + 4700uF 50V across J905 pins 1-2", "R*C = 10 ms, over-damped", "V + I0*R = 12 + 29 V", "24 V"],
            ["(c) TVS fast dump", "D934 SMBJ20A (DNP)", "L*I0/(Vclamp - V) = 591 us", "~32 V clamp at 18.5 A", "12 V"]]
    sh.text("Flyback stuffing options on one footprint set (design 6.1) — fit ONE; the FET is a 40 V part.", 24, 324, 1.5, True)
    sh.table(24, 327, rows, [58, 74, 52, 40, 28], 1.3)

    # =============================================================== warnings + test points
    x_warn = 502
    sh.text("SILKSCREEN / WARNINGS (they also go on the board):", x_warn, 60, 1.6, True)
    warn = ["USB BEFORE BENCH SUPPLY.",
            "Plug the USB-C cable (or the 5 V jack)",
            "in first and let the board boot, then",
            "switch on the supply at J901. The gate",
            "pull-downs R921/R922/R930 only hold the",
            "bridge and the polarizer off once the",
            "logic rails are up; +VEXT on a dead",
            "board leaves the gates floating.",
            "",
            "+VEXT 7-18 V",
            "(24 V only with U802 not fitted:",
            "the OPA564 maximum supply is 26 V)",
            "",
            "+VCOIL <= 24 V with the snubber",
            "+VCOIL <= 12 V with the TVS",
            "(peak drain must stay under the",
            "AOD4184A 40 V V_DS rating)",
            "",
            "All of this sheet is on GND, never",
            "AGND. Up to 13 A returns through",
            "J905 pin 3."]
    y = 66
    for line in warn:
        sh.text(line, x_warn, y, 1.4, line.endswith("."))
        y += 4.2
    auto_junctions(sh)
    return sh


# ---------------------------------------------------------------------------------------------
# Board placement (mm, KiCad coordinates: x right, y DOWN; y = 0 is the rear edge).  ZONE_C v0.7 is
# [(0.5,0.5),(149,0.5),(149,36),(37.5,36),(37.5,57.5),(0.5,57.5)]; B2 fills x 0-40 / y 0-56 and B4
# fills x 38-128 / y 0-36, so the only free block left for this sheet is the rear-right strip
# x 128-149, y 0.5-36 (20 x 35 mm) plus four ~13 x 6 mm pockets between the relay columns.
PLACEMENT = {
    # --- rear edge (y = 4.2, the J401 overhang convention): the three terminals, 35.6 mm of the 40.5 mm strip
    "J901": (134.00, 4.20, 0),      # +VEXT input, 7-18 V
    "J903": (145.70, 4.20, 0),      # H-bridge -> field-cycling coil (OUT1 / OUT2)
    "J905": (159.90, 4.20, 0),      # polarizer: 1 = +VCOIL, 2 = COIL, 3 = GND
    # --- column A (x 128.5-141.3), behind J901: the input chain
    "F901": (131.00, 11.20, 90),    # 5 A fast fuse
    "D931": (137.50, 11.00, 0),     # SMBJ26A input TVS
    "Q901": (135.50, 17.70, 0),     # AOD4185 reverse-polarity P-FET
    "C940": (135.00, 26.20, 0),     # 100 uF +VEXT bulk
    "D932": (131.00, 33.30, 0),     # BZX84C12 V_GS clamp
    "R940": (135.50, 32.40, 0),     # gate pull-down
    "C941": (134.90, 34.90, 0),     # 100 nF at +VEXT
    "R941": (139.60, 32.00, 0),     # LED series resistor
    "D933": (139.50, 34.60, 0),     # +VEXT rail LED
    # --- column B (x 142.2-155.5), behind J903: the H-bridge
    "U903": (146.00, 13.00, 0),     # DRV8871 (SO-8 PowerPAD: 3 x 3 vias of 0.3 mm on a 1.0 mm grid)
    "C920": (152.50, 10.00, 0),     # 100 nF at VM
    "R920": (152.50, 12.50, 0),     # ILIM
    "R921": (152.50, 15.00, 0),     # IN1 pull-down
    "R922": (152.50, 17.50, 0),     # IN2 pull-down
    "D920": (146.60, 20.50, 0),     # SMBJ26A VM -> GND clamp
    "C921": (149.00, 27.50, 0),     # 100 uF VM bulk, right beside U903 and J903
    # --- column C (x 155.3-168.9), behind J905: the polarizer switch
    "Q904": (162.00, 12.50, 0),     # AOD4184A (TO-252 tab = drain = COIL), close to J905
    "U904": (158.00, 19.00, 0),     # UCC27517 gate driver
    "JP904": (164.00, 18.80, 0),    # VDD select: +VEXT (default) / +5V_RAW
    "C930": (157.50, 22.50, 0),     # 1 uF at VDD
    "C931": (161.30, 22.50, 0),     # 100 nF at VDD
    "R930": (165.10, 22.50, 0),     # FET_GATE pull-down
    "R931": (157.50, 25.00, 0),     # 100 R into IN+
    "R932": (161.30, 25.00, 0),     # gate resistor
    "R933": (159.50, 28.50, 0),     # 0 R 2512 link in the source return (10 mOhm shunt option)
    "D930": (159.60, 33.00, 0),     # SS54 freewheel (option a, fitted)
    "D934": (166.30, 32.00, 90),    # SMBJ20A fast-dump clamp (option c, DNP)
}

# ------------------------------------------------------------------ floorplan notes
# Board 180 x 100 (v0.7, 2026-09-13).  ZONE_C = [(0.5,0.5),(169,0.5),(169,36),(37.5,36),(37.5,57.5),(0.5,57.5)];
# B2 fills x 0-40 / y 0-56 and B4 fills x 38-128 / y 0-36, so the 9xx block owns the rear strip x 128.4-168.9,
# y 0.5-36 (40.5 x 35.5 mm).  All three terminals now sit on the rear edge (10.2 + 10.2 + 15.2 = 35.6 mm of
# the 40.5 mm available) with the same deliberate overhang as J401-J404/J411/J412, and each functional group
# sits in its own column directly behind its terminal.  Nothing is placed outside ZONE_C and the relay pockets
# between the B4 columns are left free.
# Flyback option (b) is off-board: the 31 x 10 mm 5 W resistor and the 22 mm radial 4700 uF capacitor have no
# home on this outline, so they are wired externally across J905 pins 1-2 (see the sheet note and the table).
