"""C sheet (v0.7): external power input, DRV8871 field-cycling H-bridge, polarizer MOSFET switch.

Source: notes/2026-09-13-v07-nmr-circuits.md sections 5 (H-bridge), 6 + 6.1 (polarizer switch and
the three flyback stuffing options), 7 (external power input) and 8 (grounding).  Everything on this
sheet sits on GND (never AGND): the coil returns are the noisiest currents on the board.

Reference range 9xx (coil switches / external power).  Block = C_SW -> ZONE_C (rules/class-board.dru
rule "owner_C").  Imported by gen_sch.main() and gen_pcb.sheet_modules().
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


def build(root_uuid):
    sh = Sheet("c_switch", "C: external power input, DRV8871 field-cycling H-bridge, polarizer MOSFET switch",
               "A3", 12,
               "J901 7-18 V -> fuse + TVS + P-FET -> +VEXT; DRV8871 to J903; UCC27517 + AOD4184A to J905")
    c = Ctx(sh, BLOCK, 9000)
    sheet_frame(sh, BLOCK, "C (9xx) — EXTERNAL POWER INPUT, FIELD-CYCLING H-BRIDGE, POLARIZER SWITCH", [
        "Input (7): J901 -> F901 5 A fast (0466005.NRHF) -> D931 SMBJ26A (26 V standoff > the 24 V maximum input; the fuse limits the TVS fault current) -> Q901 AOD4185 reverse-polarity P-FET (15 mOhm: 0.375 W at 5 A against 2.75 W for a Schottky) -> +VEXT.",
        "D932 BZX84C12 clamps V_GS of Q901 (AOD4185 maximum +-20 V); R940 enhances the P-FET. C940 + C941 are the +VEXT bulk; D933/R941 show the rail. Loads on +VEXT: OPA564 V+ (NMR TX), DRV8871 VM, UCC27517 VDD. Nothing else.",
        "H-bridge (5): U903 DRV8871, VM = +VEXT. C921 100 uF is sized for the 25 us internal t_OFF window (C = I dt / dV = 2 A x 25 us / 0.5 V); C920 100 nF at the pin. R920 sets I_TRIP = 64 / R_ILIM(kOhm); 1 % because the trip point is directly proportional to it. R921/R922 hold IN1/IN2 low at reset = coast.",
        "D920 SMBJ26A sits VM -> GND, NOT across the coil: the bridge has integral body diodes, so the coil freewheels inside the part and the only real risk is supply pumping (1/2 L I^2 = 1.8 mJ into 100 uF from 15 V = 1.2 V rise). The clamp must fire below the DRV8871's 45 V maximum, which is why the brief's SMBJ58A is wrong here.",
        "Polarizer (6): FET_GATE -> R930 pull-down + R931 damping -> U904 UCC27517 (4 A driver) -> R932 -> Q904 AOD4184A (40 V, 13 A, 7 mOhm). JP904 picks the driver supply: +VEXT (default, V_GS = 12-18 V, R_DS(on) at its 10 V spec point) or +5V_RAW.",
        "Flyback (6.1), one footprint set, three stuffing options: (a) D930 SS54 freewheel, tau = L/R = 2.6 ms — fitted by default; (b) the RC snubber (the Michal route, 2.2 R 5 W + 4700 uF 50 V) over-damped at ~10 ms, +VCOIL <= 24 V — wired EXTERNALLY across J905 pins 1-2, the parts are too big for the board; (c) D934 SMBJ20A fast dump, 591 us, +VCOIL <= 12 V. This board does the ADIABATIC transfer, not the sudden one.",
        "R933 is the optional 10 mOhm Kelvin shunt in the source return (13.4 A x 10 mOhm = 134 mV = 5 % of the ADS8688 +-2.56 V range, so no divider) brought out as ISENSE_COIL for a spare ADC channel. It is fitted as a 0 R link by default so the source return is never open.",
        "Everything on this sheet is on GND (grounding note 8.1/8.2): up to 13 A of polarizer return must never touch the AGND pour. Route the coil pairs tight — TX out and return together, loop area under 1 cm2.",
    ])

    # =============================================================== 7. EXTERNAL POWER INPUT
    sh.box(28, 52, 196, 124, None)
    sh.text("EXTERNAL POWER INPUT (design 7): J901 -> F901 -> D931 -> Q901 -> +VEXT", 30, 50, 2.0, True)

    J01 = c.place("J901", "KF301-5.0-2P", 40, 70, 0)
    c.pwr_pin(J01, 2, "GND", 10.16)
    vin = sh.stub(J01, 1, 7.62)
    sh.label("VIN", vin[0], vin[1], 0)

    F01 = c.place("F901", _sym("FUSE_0466005"), vin[0] + 11.43, vin[1], 90)   # pin 1 left, pin 2 right
    sh.wire(vin[0], vin[1], F01.pin_pos(1)[0], F01.pin_pos(1)[1])
    nf = F01.pin_pos(2)
    yTOP = nf[1]

    # the fused +VIN line runs right to the P-FET source
    x_tvs = nf[0] + 12.7
    x_zen = nf[0] + 25.4
    x_q = nf[0] + 45.72
    sh.wire(nf[0], yTOP, x_q + 2.54, yTOP)

    sh.label("VIN_F", nf[0] + 3.81, yTOP, 0)
    D31 = c.place("D931", "SMBJ26A", x_tvs, yTOP + 12.7, 270)      # K up (pin 1), A down to GND
    sh.wire(D31.pin_pos(1)[0], D31.pin_pos(1)[1], D31.pin_pos(1)[0], yTOP)
    c.pwr_pin(D31, 2, "GND")

    Q01 = c.place("Q901", "AOD4185", x_q, yTOP + 5.08, 0)          # S up, D down, G left
    sx, sy = Q01.pin_pos(3)
    sh.wire(sx, sy, sx, yTOP)
    y_gate = yTOP + 20.32
    gx, gy = Q01.pin_pos(1)
    x_g = x_q - 12.7
    sh.path((gx, gy), (x_g, gy), (x_g, y_gate), (x_zen, y_gate))

    D32 = c.place("D932", "BZX84C12", x_zen, yTOP + 10.16, 270)    # K (pin 3) up to the source, A (pin 1) down to the gate
    sh.wire(D32.pin_pos(3)[0], D32.pin_pos(3)[1], D32.pin_pos(3)[0], yTOP)
    sh.wire(D32.pin_pos(1)[0], D32.pin_pos(1)[1], D32.pin_pos(1)[0], y_gate)
    # D932 pin 2 (NC) is a hidden no-connect pin in the symbol: no NC flag (KiCad calls that dangling).

    R40 = c.place("R940", SYM_R47K, x_zen + 5.08, y_gate + 8.89, 0)
    sh.wire(R40.pin_pos(1)[0], R40.pin_pos(1)[1], R40.pin_pos(1)[0], y_gate)
    c.pwr_pin(R40, 2, "GND")
    sh.text("D932 clamps V_GS to 12 V (AOD4185 maximum +-20 V); R940 enhances the P-FET", x_zen - 6, y_gate + 22, 1.2)

    # +VEXT node
    dx, dy = Q01.pin_pos(2)
    y_ext = yTOP + 17.78
    sh.wire(dx, dy, dx, y_ext)
    sh.wire(dx, y_ext, dx + 63.5, y_ext)
    c.flag(dx + 45.72, y_ext)
    c.power_at(dx + 63.5, y_ext, "+VEXT")
    for ref, lib, off in (("C940", SYM_CP100, 15.24), ("C941", "C0603_100nF", 25.4)):
        cap = c.place(ref, lib, dx + off, y_ext + 8.89, 0)
        sh.wire(cap.pin_pos(1)[0], cap.pin_pos(1)[1], cap.pin_pos(1)[0], y_ext)
        c.pwr_pin(cap, 2, "GND")
    R41 = c.place("R941", "R0603_4R7k", dx + 35.56, y_ext + 8.89, 0)
    sh.wire(R41.pin_pos(1)[0], R41.pin_pos(1)[1], R41.pin_pos(1)[0], y_ext)
    D33 = c.place("D933", "LED_GREEN_0805", dx + 35.56, y_ext + 21.59, 90)   # A up, K down
    sh.wire(R41.pin_pos(2)[0], R41.pin_pos(2)[1], D33.pin_pos(2)[0], D33.pin_pos(2)[1])
    c.pwr_pin(D33, 1, "GND")
    sh.text("+VEXT rail LED: (24 - 2) / 4.7k = 4.7 mA at 24 V, 1.1 mA at 7 V", dx + 20, y_ext + 30, 1.2)
    sh.text("SILKSCREEN at J901:  +VEXT 7-18 V  (24 V only with U802 not fitted — the OPA564 absolute maximum supply is 26 V)",
            30, 118, 1.5, True)

    # =============================================================== 5. H-BRIDGE
    sh.box(206, 52, 344, 148, None)
    sh.text("FIELD-CYCLING H-BRIDGE (design 5): DRV8871, VM = +VEXT", 208, 50, 2.0, True)

    U03 = c.place("U903", "DRV8871DDAR", 272, 100, 0)
    vm = sh.stub(U03, 5, 12.7)
    x_vmL = vm[0] - 40.64
    sh.wire(x_vmL, vm[1], vm[0], vm[1])
    c.power_at(x_vmL, vm[1], "+VEXT")
    for ref, lib, off in (("C920", "C0603_100nF", -12.7), ("C921", SYM_CP100, -22.86)):
        cap = c.place(ref, lib, vm[0] + off, vm[1] + 8.89, 0)
        sh.wire(cap.pin_pos(1)[0], cap.pin_pos(1)[1], cap.pin_pos(1)[0], vm[1])
        c.pwr_pin(cap, 2, "GND")
    D20 = c.place("D920", "SMBJ26A", vm[0] - 33.02, vm[1] + 8.89, 270)
    sh.wire(D20.pin_pos(1)[0], D20.pin_pos(1)[1], D20.pin_pos(1)[0], vm[1])
    c.pwr_pin(D20, 2, "GND")
    sh.text("C921 100 uF: 2 A x 25 us / 0.5 V. D920 clamps VM below the 45 V maximum (SMBJ58A would not).",
            vm[0] - 40, vm[1] + 22, 1.2)

    # logic inputs with their pull-downs
    for pin, ref, net, ln, roff in ((3, "R921", "HB_IN1", 46.99, 46.99), (2, "R922", "HB_IN2", 31.75, 30.48)):
        e = sh.stub(U03, pin, ln)
        sh.label(net, e[0], e[1], 180, "global")
        r = c.place(ref, "R0603_10k", U03.x - roff, e[1] + 8.89, 0)
        sh.wire(r.pin_pos(1)[0], r.pin_pos(1)[1], r.pin_pos(1)[0], e[1])
        c.pwr_pin(r, 2, "GND")
    # ILIM
    e4 = sh.stub(U03, 4, 15.24)
    R20 = c.place("R920", SYM_R32K, e4[0], e4[1] + 8.89, 0)
    sh.wire(R20.pin_pos(1)[0], R20.pin_pos(1)[1], R20.pin_pos(1)[0], e4[1])
    c.pwr_pin(R20, 2, "GND")
    sh.label("ILIM", e4[0] + 3.81, e4[1], 0)
    sh.text("I_TRIP(A) = 64 / R_ILIM(kOhm)  —  32.0 k = 2.0 A (default), 17.8 k = 3.6 A, 15 k minimum",
            U03.x - 44, e4[1] + 22, 1.2)
    # outputs -> coil terminal
    J03 = c.place("J903", "KF301-5.0-2P", U03.x + 40.64, U03.y - 2.54, 0, mirror="y")
    for pin, tpin, net in ((6, 1, "HB_OUT1"), (8, 2, "HB_OUT2")):
        a = U03.pin_pos(pin)
        b = J03.pin_pos(tpin)
        sh.wire(a[0], a[1], b[0], b[1])
        sh.label(net, a[0] + 6.35, a[1], 0)
    for pin, ln in ((1, 12.7), (7, 7.62), (9, 12.7)):
        c.pwr_pin(U03, pin, "GND", ln)
    sh.text("J903: 1 = OUT1, 2 = OUT2 (field-cycling coil, <= 3.6 A peak)", J03.x - 14, U03.y - 12.7, 1.3)
    sh.text("PowerPAD (pad 9 = EP): 3 x 3 array of 0.3 mm vias on a 1.0 mm grid to the bottom GND plane (datasheet 10.1); OUT traces >= 2 mm.",
            U03.x - 60, U03.y + 30, 1.2)

    # =============================================================== 6. POLARIZER SWITCH
    sh.box(28, 156, 344, 262, None)
    sh.text("POLARIZER MOSFET SWITCH (design 6 / 6.1): UCC27517 -> AOD4184A, three flyback options", 30, 154, 2.0, True)

    U04 = c.place("U904", "UCC27517DBVR", 150, 215, 0)
    # --- driver supply select
    vdd = sh.stub(U04, 1, 15.24)
    JP = c.place("JP904", "SolderJumper_3_Bridged12", vdd[0], vdd[1] - 3.81, 0)
    e = sh.stub(JP, 1, 10.16)
    c.power_at(e[0], e[1], "+VEXT", 90)
    e = sh.stub(JP, 3, 10.16)
    c.power_at(e[0], e[1], "+5V_RAW", 270)
    sh.label("VDD904", vdd[0] + 3.81, vdd[1], 0)
    c.flag(vdd[0] + 8.89, vdd[1])       # JP904 feeds VDD904 through passive pins: flag it as driven
    sh.wire(vdd[0], vdd[1], vdd[0] + 27.94, vdd[1])
    for ref, lib, off in (("C930", "C0603_1uF", 17.78), ("C931", "C0603_100nF", 27.94)):
        cap = c.place(ref, lib, vdd[0] + off, vdd[1] + 8.89, 0)
        sh.wire(cap.pin_pos(1)[0], cap.pin_pos(1)[1], cap.pin_pos(1)[0], vdd[1])
        c.pwr_pin(cap, 2, "GND")
    sh.text("JP904 default = pins 1-2 bridged: VDD = +VEXT (V_GS 12-18 V). Cut and bridge 2-3 for +5V_RAW.",
            vdd[0] - 24, vdd[1] - 12.7, 1.2)
    c.pwr_pin(U04, 2, "GND", 10.16)
    c.pwr_pin(U04, 4, "GND", 12.7)

    # --- input: FET_GATE -> R930 pull-down + R931 series
    e3 = sh.stub(U04, 3, 12.7)
    R31 = c.place("R931", "R0603_100", e3[0] - 3.81, e3[1], 90)     # pin 1 left, pin 2 right (at e3)
    n31 = R31.pin_pos(1)
    sh.wire(n31[0], n31[1], n31[0] - 20.32, n31[1])
    sh.label("FET_GATE", n31[0] - 20.32, n31[1], 180, "global")
    R30 = c.place("R930", "R0603_10k", n31[0] - 12.7, n31[1] + 8.89, 0)
    sh.wire(R30.pin_pos(1)[0], R30.pin_pos(1)[1], R30.pin_pos(1)[0], n31[1])
    c.pwr_pin(R30, 2, "GND")
    sh.text("R930 keeps the polarizer off unless driven; R931 damps the edge into the driver input.",
            n31[0] - 24, n31[1] + 22, 1.2)

    # --- output: R932 -> Q904 gate
    e5 = sh.stub(U04, 5, 12.7)
    R32 = c.place("R932", SYM_R10, e5[0] + 3.81, e5[1], 90)         # pin 1 left (at e5), pin 2 right
    y_gate4 = e5[1]
    x_q4 = e5[0] + 25.4
    Q04 = c.place("Q904", "AOD4184A", x_q4, y_gate4 - 2.54, 0)      # G left, D up, S down
    g4 = Q04.pin_pos(1)
    sh.wire(R32.pin_pos(2)[0], R32.pin_pos(2)[1], g4[0], g4[1])

    # --- drain = COIL node, source = the shunt return
    d4 = Q04.pin_pos(2)
    y_coil = e5[1] - 38.1
    y_vcoil = y_coil - 15.24
    sh.wire(d4[0], d4[1], d4[0], y_coil)
    sh.label("COIL", d4[0] + 3.81, y_coil, 0)
    x_j5 = d4[0] + 76.2
    sh.wire(d4[0], y_coil, x_j5 - 20.32, y_coil)

    D34 = c.place("D934", "SMBJ20A", d4[0] + 12.7, y_coil + 3.81, 270)      # K up (COIL), A down (GND)
    sh.wire(D34.pin_pos(1)[0], D34.pin_pos(1)[1], D34.pin_pos(1)[0], y_coil)
    c.pwr_pin(D34, 2, "GND")
    sh.text("Option (b), the RC snubber, is OFF-BOARD: 2.2 R 5 W in series with 4700 uF 50 V, wired externally",
            d4[0] + 20.32, y_coil + 10.16, 1.3, True)
    sh.text("across J905 pins 1-2 (drain to +VCOIL). The 31 x 10 mm resistor and the 22 mm capacitor do not fit",
            d4[0] + 20.32, y_coil + 14.0, 1.3)
    sh.text("on the board (a scan of the whole outline finds no free 22.5 x 22.5 mm square outside this strip).",
            d4[0] + 20.32, y_coil + 17.8, 1.3)
    D30 = c.place("D930", "SS54", d4[0] + 45.72, y_coil - 3.81, 270)        # A down (COIL), K up (+VCOIL)
    sh.wire(D30.pin_pos(1)[0], D30.pin_pos(1)[1], D30.pin_pos(1)[0], y_coil)
    sh.wire(D30.pin_pos(2)[0], D30.pin_pos(2)[1], D30.pin_pos(2)[0], y_vcoil)
    sh.wire(D30.pin_pos(2)[0] - 12.7, y_vcoil, x_j5 - 15.24, y_vcoil)
    c.flag(D30.pin_pos(2)[0] + 5.08, y_vcoil)
    c.power_at(D30.pin_pos(2)[0] - 12.7, y_vcoil, "+VCOIL", 90)

    J05 = c.place("J905", "KF301-5.0-3P", x_j5, y_vcoil + 5.08, 0, mirror="y")
    p1, p2, p3 = J05.pin_pos(1), J05.pin_pos(2), J05.pin_pos(3)
    sh.path(p1, (x_j5 - 15.24, p1[1]), (x_j5 - 15.24, y_vcoil))
    sh.path(p2, (x_j5 - 20.32, p2[1]), (x_j5 - 20.32, y_coil))
    c.pwr_pin(J05, 3, "GND", 10.16)
    sh.text("J905: 1 = +VCOIL (external supply +), 2 = COIL (drain), 3 = GND — the coil goes between 1 and 2.",
            x_j5 - 44, y_vcoil - 8.89, 1.3)

    s4 = Q04.pin_pos(3)
    y_src = s4[1] + 7.62
    sh.wire(s4[0], s4[1], s4[0], y_src)
    R33 = c.place("R933", SYM_R2512, s4[0], y_src + 3.81, 0,
                  value=None if SYM_R2512 != "R2512_10mR" else "0R (10 mOhm shunt option)")
    c.pwr_pin(R33, 2, "GND")
    sh.wire(s4[0], s4[1] + 3.81, s4[0] + 22.86, s4[1] + 3.81)
    sh.label("ISENSE_COIL", s4[0] + 22.86, s4[1] + 3.81, 0, "global")
    sh.text("R933 is FITTED as a 0 R 2512 link (it is the polarizer source return and must never be open).",
            s4[0] - 30, y_src + 14, 1.3, True)
    sh.text("Swap it for the 10 mOhm shunt (1.8 W at 13.4 A, 134 mV = 5 % of the ADS8688 +-2.56 V range) to use ISENSE_COIL.",
            s4[0] - 30, y_src + 18, 1.2)

    # --- flyback option table and the warnings that also go to silkscreen
    rows = [["Option", "Parts", "Decay", "Peak drain", "+VCOIL limit"],
            ["(a) freewheel diode (default)", "D930 SS54 fitted", "tau = L/R = 2.6 ms", "+VCOIL + 0.6 V", "24 V"],
            ["(b) RC snubber (Michal) — OFF-BOARD", "2.2R 5W + 4700uF 50V across J905 pins 1-2", "R*C = 10 ms, over-damped", "V + I0*R = 12 + 29 V", "24 V"],
            ["(c) TVS fast dump", "D934 SMBJ20A (DNP)", "L*I0/(Vclamp - V) = 591 us", "~32 V clamp at 18.5 A", "12 V"]]
    sh.table(32, 232, rows, [58, 74, 52, 40, 28], 1.3)
    sh.text("Flyback stuffing options on one footprint set (design 6.1) — fit ONE; the FET is a 40 V part.", 32, 230, 1.5, True)

    # =============================================================== warnings + test points
    sh.text("SILKSCREEN / WARNINGS (they also go on the board):", 350, 60, 1.6, True)
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
        sh.text(line, 350, y, 1.4, line.endswith("."))
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
