"""NMR transmitter sheet (section B, 8xx): AD9834 DDS -> reconstruction filter -> OPA564 -> TX.

Source: notes/2026-09-13-v07-nmr-circuits.md sections 0, 2, 8 and 9, with the instructor-side
corrections of 2026-09-13:
  * the power op-amp is the OPA564AIDWPR (C188648), PowerPAD DOWN: EP (pin 21) = V- = GND and
    goes straight onto the ground pour with a via array; there is no top-side heatsink,
  * single supply +VEXT (7-18 V), V- = GND, VDIG = +3V3 (datasheet SBOS372E section 2.3),
  * RESET / SLEEP get 10 k pull-DOWNS (AD9834 RESET is active high, so the part must run when
    the expander line is still an input),
  * MCLK comes from the Si5351A CLK0 on the RX sheet (global label CLK0_MCLK, 50.000 MHz).

The module is imported by scripts/gen_sch.py (build) and scripts/gen_pcb.py (PLACEMENT).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cb_sch import Sheet, Inst, g            # noqa: E402,F401
from gen_sch import Ctx, sheet_frame, auto_junctions   # noqa: E402
import cb_symbols                            # noqa: E402
from cb_symbols import SYMBOLS               # noqa: E402

BLOCK = "NMR_TX"          # -> ZONE_B

# ---------------------------------------------------------------- symbol resolution
# The v0.7 passive values are being added to cb_symbols.py by another agent.  Until a value
# lands this module uses an EXISTING symbol with the SAME FOOTPRINT and overrides the Value
# field with the design value (plus a SUBSTITUTE field, so a stand-in cannot slip into a BOM
# unnoticed).  The one exception is R814: no symbol in the library carries the R0805 land, so
# a temporary symbol TXTMP_R0805_10R is built with cb_symbols own two_pin() helper -- the
# footprint has to be right or the PCB placement would have to move when the real symbol
# lands.  Every fallback is listed by build() on each run, and the real symbol is picked up
# automatically as soon as cb_symbols has it.
FPL = "class_board:"
FALLBACKS = []      # (real symbol name, value, footprint, how)
_REF_OF = {"R": "R", "C": "C", "CP": "C", "L": "L", "FB": "FB"}


def part(names, kind, value, footprint, description, generic=None):
    """(library symbol, value override or None, real symbol name) for one passive"""
    if isinstance(names, str):
        names = (names,)
    for n in names:
        if n in SYMBOLS:
            return (n, None, names[0])
    if generic and generic in SYMBOLS and SYMBOLS[generic].footprint == FPL + footprint:
        FALLBACKS.append((names[0], value, footprint, "value-only on " + generic))
        return (generic, value, names[0])
    tmp = "TXTMP_" + names[0]
    if tmp not in SYMBOLS:
        SYMBOLS[tmp] = cb_symbols.two_pin(
            tmp, _REF_OF[kind], value, FPL + footprint,
            description + " [placeholder: %s pending in cb_symbols.py]" % names[0], kind,
            fields={"SUBSTITUTE": "placeholder for %s - no LCSC part assigned yet" % names[0]})
    FALLBACKS.append((names[0], value, footprint, "temporary symbol " + tmp))
    return (tmp, value, names[0])


def pl(c, ref, spec, x, y, rot=0, **kw):
    """place a passive, carrying the design value when a stand-in symbol is in use"""
    lib, value, real = spec
    if value is not None:
        kw["value"] = value
        f = dict(kw.pop("fields", None) or {})
        f["SUBSTITUTE"] = "stand-in for %s: the value is correct, no LCSC part assigned yet" % real
        kw["fields"] = f
    return c.place(ref, lib, x, y, rot, **kw)


GR = "R0603_10k"        # generic symbol on the R0603 land
GC = "C0603_100nF"      # generic symbol on the C0603 land

R_100 = part("R0603_100", "R", "100", "R0603", "Resistor 100 R 1% 0603", GR)
R_200 = part("R0603_200", "R", "200", "R0603", "Resistor 200 R 1% 0603 (AD9834 IOUT / IOUTB load)", GR)
R_270 = part("R0603_270", "R", "270", "R0603", "Resistor 270 R 1% 0603 (OPA564 gain leg, G = 25)", GR)
R_910 = part("R0603_910", "R", "910", "R0603", "Resistor 910 R 1% 0603 (-20 dB output pad)", GR)
R_10K = part("R0603_10k", "R", "10k", "R0603", "Resistor 10 k 1% 0603", GR)
R_11K = part("R0603_11k", "R", "11.0k", "R0603", "Resistor 11.0 k 1% 0603 (OPA564 ISET, I_LIM = 1.50 A)", GR)
R_100K = part("R0603_100k", "R", "100k", "R0603", "Resistor 100 k 1% 0603", GR)
R_6R8K = part("R0603_6R8k", "R", "6.80k", "R0603", "Resistor 6.80 k 1% 0603 (AD9834 FS ADJUST)", GR)
R_6R49K = part("R0603_6R49k", "R", "6.49k", "R0603", "Resistor 6.49 k 1% 0603 (OPA564 feedback)", GR)
R_4R7_2512 = part("R2512_4R7", "R", "4.7 1W", "R2512",
                  "Resistor 4.7 R 1% 2512 1 W (TX output series isolation)", "R2512_10mR")
# no symbol in the library carries the R0805 land, so this one needs a temporary symbol
R_10R_0805 = part("R0805_10R", "R", "10", "R0805", "Resistor 10 R 1% 0805 0.25 W (OPA564 output snubber)")
C_20P = part("C0603_20pF", "C", "20pF", "C0603", "Capacitor 20 pF C0G 50 V 0603 (AD9834 IOUT, clock feedthrough)", GC)
C_130P = part("C0603_130pF", "C", "130pF", "C0603", "Capacitor 130 pF C0G 5% 50 V 0603 (filter C3)", GC)
C_390P = part("C0603_390pF", "C", "390pF", "C0603", "Capacitor 390 pF C0G 5% 50 V 0603 (filter C1)", GC)
C_10N = part("C0603_10nF", "C", "10nF", "C0603", "Capacitor 10 nF X7R 0603", GC)
C_100N = part("C0603_100nF", "C", "100nF", "C0603", "Capacitor 100 nF X7R 0603", GC)
C_1U = part("C0603_1uF", "C", "1uF", "C0603", "Capacitor 1 uF X7R 25 V 0603", GC)
C_10U = part("C0805_10uF", "C", "10uF", "C0805", "Capacitor 10 uF X5R 25 V 0805")
# C818: the design asks for 10 uF X7R 50 V 1210; 1206 X7R (C89632) is the accepted stand-in
C_10U_HV = part(("C1210_10uF", "C1206_10uF"), "C", "10uF 50V X7R", "C1206",
                "Capacitor 10 uF X7R 50 V 1206 (TX DC block; 1210 preferred)", "C1206_22uF")
CP_47U = part("CP_47uF_35V", "CP", "47uF 35V", "CAP-SMD_BD6.3-L6.6-W6.6-FD", "Aluminium electrolytic 47 uF 35 V")
CP_100U = part("CP_100uF_35V", "CP", "100uF 35V", "CAP-SMD_BD8.0-L8.3-W8.3-LS9.3-FD", "Aluminium electrolytic 100 uF 35 V")
L_15UH = part("L_15uH", "L", "15uH", "IND-SMD_L3.2-W2.5-LQH32CN1R0M53L", "Inductor 15 uH, SRF 26 MHz, 1210 (filter L2)")
FB_3A = part("FB0603_120R_3A", "FB", "120R@100MHz 3A", "L0603",
             "Ferrite bead 120 ohm @100 MHz, 3 A, 0603 (+VEXT into the OPA564 V+ branch)", "FB0603_600R")

VEXT = "+VEXT"       # external 7-18 V input, sourced on the C sheet
VEXT_TX = "+VEXT_TX"  # +VEXT through FB802: the OPA564 V+ branch only
V3D = "+3V3D"        # +3V3 through FB801: AD9834 AVDD/DVDD, AGND-referenced


def _pwr_lib(net):
    return "PWR_" + net.replace("+", "p").replace("-", "n")


def rail_pin(c, inst, pin, net, length=2.54):
    """power symbol on a pin when the rail has one, otherwise a global label"""
    if _pwr_lib(net) in SYMBOLS:
        return c.pwr_pin(inst, pin, net, length)
    return c.sh.pin_label(inst, pin, net, "global", length)


def rail_at(c, x, y, net, rot=0, lrot=0):
    """power symbol at a wire end when the rail has one, otherwise a global label"""
    if _pwr_lib(net) in SYMBOLS:
        return c.power_at(x, y, net, rot)
    return c.sh.label(net, x, y, lrot, "global")


# ================================================================== sheet
# Layout rework 2026-09-17 (geometry only -- no reference, value, footprint, pin or net changed):
#   * the sheet moved from A3 to A2 so every block has room to breathe,
#   * every rail / ground symbol sits on its own stub (c.tap / c.comb / c.pwr_pin), never mid-wire,
#   * adjacent ground pins (AGND+DGND on the DDS, the seven V- pins on the OPA564) share one comb
#     with a single symbol on a tail,
#   * label rotations corrected: a label on an UPWARD stub is rot 90, on a DOWNWARD stub rot 270
#     (the opposite convention put the text back over its own part and wire),
#   * passive columns at >= 10.16 mm pitch, free text moved into bands that carry no geometry.
def build(root_uuid):
    sh = Sheet("nmr_tx", "NMR TX (B): AD9834 DDS, reconstruction filter, OPA564 power stage -> TX", "A2", 11,
               "AD9834 on a 50 MHz MCLK -> 3 MHz Butterworth reconstruction filter -> OPA564 single-supply power stage from +VEXT -> TX")
    c = Ctx(sh, BLOCK, 8000)
    sheet_frame(sh, BLOCK, "NMR TX (section B) — AD9834 DDS + reconstruction filter + OPA564 power stage -> TX", [
        "DDS: AD9834BRUZ, MCLK = CLK0_MCLK = 50.000 MHz from the Si5351A on the RX sheet; df = f_MCLK / 2^28 = 0.186 Hz per LSB. R801 6.80 k on FS ADJUST -> I_OUT,FS = 18 x 1.20 V / 6.80 k = 3.18 mA;",
        "R802 / R803 200 R loads -> 0.636 V pp at IOUT, inside the 0.8 V output-compliance limit (datasheet pins 19/20). C807 20 pF C0G on IOUT prevents clock feedthrough. FSELECT tied to DGND (frequency selected by the FSEL control bit).",
        "Reconstruction filter: singly-terminated 3rd-order Butterworth, f_c = 3 MHz, source resistance = the 200 R DAC load, prototype g = 1.5 / 1.3333 / 0.5 -> C808 390 pF, L801 15 uH (LQH32DN150K53L, SRF 26 MHz), C809 130 pF.",
        "The nearest image at 48 MHz is down (48/3)^3 = 72 dB; passband -0.05 dB at 2 MHz, flat at 89 kHz. C810 1 uF couples into the power stage (f_HP = 3.2 Hz against the 100 k || 100 k bias divider).",
        "Power stage: SINGLE supply +VEXT (7-18 V), V- = GND. E/S, VDIG and both flags are referenced to V-, so V- = GND lets 3.3 V logic drive them directly; on +-12 V every one of them would need an optocoupler (SBOS372E Fig. 38).",
        "Gain: non-inverting, R807 6.49 k over R808 270 R -> G = 25.0 (15.9 V pp = +-7.95 V = 5.6 mA into the 1419 R coil = t90 417 us at 89.4 kHz). Alternative R808 stuffings: 1.00 k -> G 7.49 and 3.32 k -> G 2.95 for the >= 1 MHz settings.",
        "Protection: R809 11.0 k on ISET -> I_LIM = 1.50 A (NEVER leave ISET open — the datasheet says an open pin damages the device). R810 10 k beats the internal 100 k pull-up on E/S: 3.3 x 10/110 = 0.30 V < 0.8 V = shut down until firmware raises TX_EN.",
        "D801 / D802 SS54 clamp the output to +VEXT and to GND; R813 4.7 R 1 W isolates it; R814 / C817 (10 R + 10 nF) is the datasheet snubber; C818 10 uF blocks the 9 V mid-rail out of the coil (Z = 0.18 R at 89 kHz). JP802 + R815/R816 = the -20 dB pad option.",
        "Sequencing (SBOS372E Fig. 36): VDIG (+3V3, from USB) must come up BEFORE V+ (+VEXT, bench supply) — silkscreen note next to the external power input. PowerPAD pin 21 = V- = GND, pad DOWN on the ground pour with a via array (theta_JA 33 C/W).",
        "Grounding (re-spec 8.1): the AD9834 AGND and DGND are tied together AT THE DEVICE and belong to the AGND pour; AVDD/DVDD come from +3V3 through FB801 (local rail +3V3D). The OPA564 and the coil return are on GND. C810 is the only signal crossing the two pours.",
    ])

    # ============================================================ AD9834 DDS
    U1 = c.place("U801", "AD9834BRUZ", 149.86, 149.86, 0)
    U1.field_pos["Value"] = (134.62, 181.61, 0, "left top")   # default lands on the AGND/DGND pin names

    # ---- +3V3 -> FB801 -> +3V3D bus above the device -----------------------------------------
    fb = c.place("FB801", "FB0603_600R", 149.86, 99.06, 0)
    c.pwr_pin(fb, 1, "+3V3", 5.08)
    ybus = 111.76
    sh.wire(fb.pin_pos(2)[0], fb.pin_pos(2)[1], fb.pin_pos(2)[0], ybus)
    sh.wire(109.22, ybus, 172.72, ybus)          # the bus ENDS on C802's pin: no dangling tail
    sh.label(V3D, 109.22, ybus, 180, "global")
    c.tap(140.97, ybus, "PWR_FLAG", 2.54)        # flag on its own stub, not sitting on the bus
    for pin in ("4", "5"):                       # AVDD, DVDD
        p = U1.pin_pos(pin)
        sh.wire(p[0], p[1], p[0], ybus)
    for ref, lib, x in (("C806", C_10U, 118.11), ("C801", C_100N, 130.81), ("C802", C_100N, 172.72)):
        cap = pl(c, ref, lib, x, ybus + 3.81, 0)
        c.pwr_pin(cap, 2, "AGND")
    sh.text("+3V3 -> FB801 -> +3V3D: AVDD (C801) and DVDD (C802) 100 nF each plus C806 10 uF bulk, all returned to AGND", 186.69, 97.79, 1.3)

    # ---- digital inputs (left side) -----------------------------------------------------------
    for pin, net in (("13", "SPI_MOSI"), ("14", "SPI_SCLK"), ("15", "DDS_FSYNC"), ("8", "CLK0_MCLK"),
                     ("11", "DDS_RESET"), ("12", "DDS_SLEEP"), ("10", "DDS_PSEL")):
        c.glabel_pin(U1, pin, net, 12.7)
    # FSELECT runs out PAST the label column on a clear lane (the neighbouring pins are 2.54 mm
    # away, so an AGND symbol anywhere between the pin and the labels would sit on their stubs).
    c.pwr_pin(U1, "9", "AGND", 25.4)             # FSELECT tied to DGND (= AGND at the device)
    c.nc_pin(U1, "16")                           # SIGNBITOUT unused

    # 10 k pull-downs: the AD9834 RESET is ACTIVE HIGH, so an undriven line must not reset the
    # part, and SLEEP must not put it to sleep.  Both lines go to TCA9535 spare pins later.
    for k, (ref, net) in enumerate((("R817", "DDS_RESET"), ("R818", "DDS_SLEEP"))):
        r = pl(c, ref, R_10K, 62.23 + k * 13.97, 243.84, 0)
        e = sh.stub(r, 1, 5.08)
        sh.label(net, e[0], e[1], 90, "global")  # stub points UP -> the label must extend UP
        c.pwr_pin(r, 2, "AGND")

    # ---- analog set-up pins: fan down to a row below the device --------------------------------
    # descending ladder (the highest pin gets the longest stub) so no two stubs cross; columns 10.16 apart
    yrow = 186.69
    analog = [("1", 50.80, "R801", R_6R8K, "AGND"),      # FS ADJUST 6.80 k
              ("2", 40.64, "C804", C_10N, "AGND"),       # REFOUT 10 nF
              ("3", 30.48, "C805", C_10N, V3D),          # COMP -> AVDD
              ("6", 20.32, "C803", C_100N, "AGND"),      # CAP/2.5V 100 nF
              ("17", 10.16, "R804", R_10K, "AGND")]      # VIN (comparator unused) -> AGND
    for pin, ln, ref, lib, ret in analog:
        e = sh.stub(U1, pin, ln)
        sh.wire(e[0], e[1], e[0], yrow)
        prt = pl(c, ref, lib, e[0], yrow + 3.81, 0)
        if ret == V3D:
            e2 = sh.stub(prt, 2, 5.08)
            sh.label(V3D, e2[0], e2[1], 270, "global")     # stub points DOWN -> the label extends DOWN; global like the bus label
        else:
            c.pwr_pin(prt, 2, ret)

    # ---- AGND / DGND tied at the device: one comb, ONE symbol on a tail -------------------------
    c.comb(U1, ["18", "7"], "AGND", 5.08, 5.08)
    sh.text("AGND (18) and DGND (7) tied at the device; both on the AGND pour (re-spec 8.1)", 160.02, 189.23, 1.2)

    # ============================================================ DAC load + reconstruction filter
    yf = U1.pin_pos("19")[1]                     # IOUT line
    n0 = sh.stub(U1, "19", 10.16)
    e20 = sh.stub(U1, "20", 5.08)
    R803 = pl(c, "R803", R_200, e20[0], e20[1] + 3.81, 0)
    c.pwr_pin(R803, 2, "AGND")
    for ref, lib, x in (("R802", R_200, 189.23), ("C807", C_20P, 201.93), ("C808", C_390P, 214.63)):
        prt = pl(c, ref, lib, x, yf + 3.81, 0)
        c.pwr_pin(prt, 2, "AGND")
    L1 = pl(c, "L801", L_15UH, 227.33, yf, 90)          # rot 90: pin 1 left, pin 2 right
    sh.wire(n0[0], yf, L1.pin_pos(1)[0], yf)
    sh.wire(L1.pin_pos(2)[0], yf, 241.30, yf)
    C809 = pl(c, "C809", C_130P, 241.30, yf + 3.81, 0)
    c.pwr_pin(C809, 2, "AGND")
    C810 = pl(c, "C810", C_1U, 257.81, yf, 90)
    sh.wire(241.30, yf, C810.pin_pos(1)[0], yf)
    sh.wire(C810.pin_pos(2)[0], yf, 274.32, yf)
    sh.label("TX_VMID", 274.32, yf, 0)
    sh.text("Singly-terminated 3rd-order Butterworth, f_c = 3 MHz, R = 200 R (the DAC load doubles as the filter source):", 176.53, 151.13, 1.2)
    sh.text("C808 = 1.5/(2 pi f_c R) = 398 pF, L801 = 1.3333 R/(2 pi f_c) = 14.1 uH, C809 = 0.5/(2 pi f_c R) = 133 pF.", 176.53, 154.33, 1.2)
    sh.text("C810 is the ONLY connection between the AGND (DDS) domain and the GND (power-stage) domain.", 176.53, 157.53, 1.2)

    # ============================================================ mid-rail bias network
    ym = 214.63
    sh.wire(278.13, ym, 328.93, ym)
    sh.label("TX_VMID", 278.13, ym, 180)
    R805 = pl(c, "R805", R_100K, 290.83, ym - 3.81, 0)
    e = sh.stub(R805, 1, 7.62)
    sh.label(VEXT_TX, e[0], e[1], 90)            # stub points UP
    for ref, lib, x in (("R806", R_100K, 303.53), ("C811", C_10U, 316.23), ("C812", C_100N, 328.93)):
        prt = pl(c, ref, lib, x, ym + 3.81, 0)
        c.pwr_pin(prt, 2, "GND")
    sh.text("Mid-rail bias: V_mid = VEXT/2 = 9.0 V at 18 V; 100 k || 100 k = 50 k filtered by C811/C812 (f = 0.32 Hz).", 278.13, 234.95, 1.2)

    # ============================================================ OPA564 power stage
    U2 = c.place("U802", "OPA564AIDWPR", 400.05, 179.07, 0)
    U2.field_pos["Value"] = (387.35, 168.91, 0, "right bottom")   # default lands on the V- pin stack
    U2.field_pos["Reference"] = (389.89, 160.02, 0, "left bottom")  # default sits on the V+ pin numbers
    e = sh.stub(U2, "5", 7.62)                   # +IN
    sh.label("TX_VMID", e[0], e[1], 180)
    e = sh.stub(U2, "6", 7.62)                   # -IN
    sh.label("TX_FB", e[0], e[1], 180)

    # ---- enable and current limit ---------------------------------------------------------------
    # E/S runs out on a long line with R810 hanging from it; ISET stays SHORT so that R809 sits
    # under the E/S line and clear of R810 -- no stub crosses another part.
    e = sh.stub(U2, "4", 25.4)                   # E/S
    sh.label("TX_EN", e[0], e[1], 180, "global")
    R810 = pl(c, "R810", R_10K, 370.84, e[1] + 3.81, 0)
    c.pwr_pin(R810, 2, "GND")
    e = sh.stub(U2, "9", 7.62)                   # ISET
    R809 = pl(c, "R809", R_11K, e[0], e[1] + 3.81, 0)
    c.pwr_pin(R809, 2, "GND")
    c.nc_pin(U2, "12")                           # T_SENSE unused (datasheet: may be left open)

    # ---- supplies --------------------------------------------------------------------------------
    vp = [sh.stub(U2, p, 15.24) for p in ("2", "17", "18", "19")]
    yvp = vp[0][1]
    # FB802: >= 3 A ferrite bead between +VEXT and the OPA564 V+ branch (circuits note 7, last
    # row), separate from FB801 which filters +3V3 for the DDS.  Everything on this side of the
    # bead is the local net +VEXT_TX: C815/C816, the R805 half of the mid-rail divider and the
    # D801 output clamp.
    FB2 = pl(c, "FB802", FB_3A, 353.06, yvp, 90)          # rot 90: pin 1 left, pin 2 right
    FB2.field_pos["Reference"] = (354.33, 143.00, 0, "left bottom")  # its own lane: the 14-char value runs up past it
    rail_pin(c, FB2, 1, VEXT, 7.62)
    sh.wire(FB2.pin_pos(2)[0], yvp, vp[-1][0], yvp)
    for ref, lib, x in (("C816", C_100N, 368.30), ("C815", CP_47U, 381.00)):
        prt = pl(c, ref, lib, x, yvp + 3.81, 0)
        c.pwr_pin(prt, 2, "GND")
    sh.wire(388.62, yvp, 388.62, 139.70)
    sh.label(VEXT_TX, 388.62, 139.70, 90)        # branch points UP
    c.tap(360.68, yvp, "PWR_FLAG", 5.08)         # +VEXT_TX is behind a bead: flag it, on its own stub
    sh.text("FB802 (120 R @ 100 MHz, 3 A) isolates the OPA564 V+ branch from the +VEXT input; C815 47 uF + C816 100 nF sit after it, at the V+ pins (SBOS372E Fig. 35).", 330.20, 119.38, 1.2)
    sh.text("Single +VEXT 7-18 V; total supply <= 24 V, absolute max 26 V. D801 clamps the output to +VEXT_TX, the same post-bead node.", 330.20, 122.58, 1.2)

    ed = sh.stub(U2, "7", 10.16)                 # VDIG
    sh.wire(ed[0], ed[1], ed[0], 142.24)
    c.power_at(ed[0], 142.24, "+3V3", 0)
    sh.wire(ed[0], ed[1], 417.83, ed[1])
    C814 = pl(c, "C814", C_100N, 417.83, ed[1] + 3.81, 0)
    c.pwr_pin(C814, 2, "GND")

    # V- (1/10/11/20), V-PWR (13/14) and the PowerPAD EP (21): one comb, ONE GND on a tail
    c.comb(U2, ["1", "10", "11", "20", "13", "14", "21"], "GND", 10.16, 7.62)
    sh.text("V- (1/10/11/20), V-PWR (13/14) and the PowerPAD EP (21) are all GND:", 345.44, 240.03, 1.2)
    sh.text("pad DOWN onto the ground pour with a via array, theta_JA 33 C/W.", 345.44, 243.23, 1.2)

    # ---- flags -------------------------------------------------------------------------------------
    for pin, net in (("3", "TX_TFLAG"), ("8", "TX_IFLAG")):
        c.glabel_pin(U2, pin, net, 7.62)
    for k, (ref, net) in enumerate((("R811", "TX_IFLAG"), ("R812", "TX_TFLAG"))):
        r = pl(c, ref, R_10K, 441.96 + k * 12.7, 285.75, 0, dnp=True)
        c.pwr_pin(r, 1, "+3V3")
        e = sh.stub(r, 2, 5.08)
        sh.label(net, e[0], e[1], 270, "global")  # stub points DOWN
    sh.text("I_FLAG / T_FLAG are push-pull CMOS referenced to V- = GND, so R811 / R812 are DNP", 430.53, 320.04, 1.2)
    sh.text("footprints only. Both flags go to TCA9535 spare inputs; poll them after every pulse.", 430.53, 323.24, 1.2)

    # ---- gain network -------------------------------------------------------------------------------
    yg = 276.86
    sh.wire(278.13, yg, 311.15, yg)
    sh.label("TX_FB", 278.13, yg, 180)
    # R807 hangs BELOW the rail: above it the stub would land on the C811 GND pin of the bias block
    R807 = pl(c, "R807", R_6R49K, 290.83, yg + 3.81, 0)
    e = sh.stub(R807, 2, 5.08)
    sh.label("TX_A", e[0], e[1], 270)            # stub points DOWN
    JP1 = c.place("JP801", "SolderJumper_3_Bridged12", 316.23, yg, 0)
    sh.wire(JP1.pin_pos(1)[0], JP1.pin_pos(1)[1], 311.15, yg)
    JP1.field_pos["Value"] = (330.20, 271.78, 0, "left bottom")   # 24 chars: keep it off the R808 leg
    c.nc_pin(JP1, 3)
    pj = JP1.pin_pos(2)
    R808 = pl(c, "R808", R_270, pj[0], pj[1] + 10.16, 0)
    sh.wire(pj[0], pj[1], R808.pin_pos(1)[0], R808.pin_pos(1)[1])
    C813 = pl(c, "C813", CP_100U, pj[0], pj[1] + 24.13, 0)
    sh.wire(R808.pin_pos(2)[0], R808.pin_pos(2)[1], C813.pin_pos(1)[0], C813.pin_pos(1)[1])
    c.pwr_pin(C813, 2, "GND")
    sh.text("G = 1 + R807/R808 = 1 + 6490/270 = 25.0. C813 blocks DC in the gain leg, so the DC gain is 1 and the output", 278.13, 323.85, 1.2)
    sh.text("sits at V_mid (f_HP = 5.9 Hz). JP801 (1-2 bridged) opens the gain leg for a unity-gain bring-up; pad 3 is a", 278.13, 327.05, 1.2)
    sh.text("spare for an external gain resistor.", 278.13, 330.25, 1.2)

    # ---- output chain ----------------------------------------------------------------------------------
    o15 = sh.stub(U2, "15", 10.16)
    o16 = sh.stub(U2, "16", 10.16)
    sh.wire(o15[0], o15[1], o16[0], o16[1])
    xo, yo = o16[0], o16[1]
    sh.wire(429.26, yo, 429.26, 167.64)
    sh.label("TX_A", 429.26, 167.64, 90)         # branch points UP

    D801 = c.place("D801", "SS54", 443.23, 163.83, 270)        # A down (output node), K up (+VEXT)
    sh.wire(D801.pin_pos(1)[0], D801.pin_pos(1)[1], D801.pin_pos(1)[0], yo)
    e = sh.stub(D801, 2, 5.08)
    sh.label(VEXT_TX, e[0], e[1], 90)            # stub points UP
    D802 = c.place("D802", "SS54", 457.20, 185.42, 270)        # K up (output node), A down (GND)
    sh.wire(D802.pin_pos(2)[0], D802.pin_pos(2)[1], D802.pin_pos(2)[0], yo)
    c.pwr_pin(D802, 1, "GND")
    R813 = pl(c, "R813", R_4R7_2512, 487.68, yo, 90)
    R813.field_pos["Reference"] = (483.87, 169.00, 0, "left bottom")
    sh.wire(xo, yo, R813.pin_pos(1)[0], yo)
    R814 = pl(c, "R814", R_10R_0805, 469.90, yo + 3.81, 0)
    C817 = pl(c, "C817", C_10N, 469.90, yo + 17.78, 0)
    sh.wire(R814.pin_pos(2)[0], R814.pin_pos(2)[1], C817.pin_pos(1)[0], C817.pin_pos(1)[1])
    c.pwr_pin(C817, 2, "GND")
    C818 = pl(c, "C818", C_10U_HV, 504.19, yo, 90)
    sh.wire(R813.pin_pos(2)[0], yo, C818.pin_pos(1)[0], yo)

    # -20 dB pad option: JP802 pads 1-2 bridged = full output, 2-3 = divided
    JP2 = c.place("JP802", "SolderJumper_3_Bridged12", 541.02, yo, 0)
    JP2.field_pos["Value"] = (513.08, 186.69, 0, "left top")      # 24 chars: keep it off the TX leg
    sh.wire(C818.pin_pos(2)[0], yo, JP2.pin_pos(1)[0], yo)
    ypad = 154.94
    sh.wire(514.35, yo, 514.35, ypad)
    R815 = pl(c, "R815", R_910, 525.78, ypad, 90)
    sh.wire(514.35, ypad, R815.pin_pos(1)[0], ypad)
    sh.wire(R815.pin_pos(2)[0], ypad, 551.18, ypad)
    sh.wire(551.18, ypad, 551.18, yo)
    sh.wire(551.18, yo, JP2.pin_pos(3)[0], yo)
    R816 = pl(c, "R816", R_100, 538.48, ypad + 3.81, 0)       # pin 1 on the pad tap, pin 2 down to GND
    c.pwr_pin(R816, 2, "GND")
    sh.text("-20 dB pad: 100/(910+100) = 0.099 into a high-Z load.", 490.22, 143.51, 1.2)

    # TX node -> the panel link J6 (pins 19 and 21, two pins for the coil current)
    # v0.8: the board-edge screw terminal J802 is gone; the TX coil is connected on the front
    # panel, at the 2P screw terminal beside the TX SMA (Decision #49).
    pt = JP2.pin_pos(2)
    sh.wire(pt[0], pt[1], pt[0], 201.93)
    sh.label("TX", pt[0], 201.93, 270, "global")  # branch points DOWN
    sh.text("TX leaves this sheet as a global label -> panel link J6 pins 19 and 21 (AGND on 20 and 22)", 455.93, 220.98, 1.2)
    sh.text("-> the TX SMA and the 2P screw terminal on the panel. Route TX and its return as a close pair,", 455.93, 224.18, 1.2)
    sh.text("loop area < 1 cm2; up to 1 A of coil current must never share copper with the receiver pour.", 455.93, 227.38, 1.2)

    # ---- notes and the level / bandwidth table (a band with no geometry in it) --------------------------
    sh.text("R817 / R818: 10 k pull-downs (RESET is active HIGH on the AD9834).", 48.26, 260.35, 1.2)
    sh.text("Both lines go to TCA9535 spare pins P1.5 / P1.6 — global labels until the expander sheet claims them.", 48.26, 263.55, 1.2)
    sh.text("R801 6.80 k: I_OUT,FS = 18 x V_REFOUT / R_SET = 18 x 1.20 / 6800 = 3.18 mA. C805 decouples COMP to AVDD (datasheet Fig. 1).", 48.26, 273.05, 1.2)
    rows = [["JP801 / R808", "G", "V_out pp", "f_3dB = 17 MHz / G", "SR limit = 40/(pi V_pp)"],
            ["270 R (fitted)", "25.0", "15.9 V", "680 kHz", "800 kHz"],
            ["1.00 k", "7.49", "4.76 V", "2.27 MHz", "2.67 MHz"],
            ["3.32 k", "2.95", "1.88 V", "5.8 MHz", "6.8 MHz"]]
    sh.text("Level plan from 0.636 V pp at the DDS output (re-spec 2.3). Top row = the 89.4 kHz NMR setting: +-7.95 V into 1419 R = 5.6 mA = t90 417 us.", 48.26, 283.21, 1.3)
    sh.table(48.26, 285.75, rows, [30, 12, 18, 34, 40], 1.3)
    sh.text("Firmware (re-spec 9.1 / 9.3): hold DDS_RESET high while writing, B28 = 1, PIN/SW set for hardware PSELECT; the carrier free-runs and is gated ONLY by TX_EN.", 48.26, 306.07, 1.3)
    sh.text("TX_EN must be low except during a pulse — for the thermal budget as much as for receiver blanking (quiescent 39 mA x 18 V = 0.70 W, shutdown 5 mA = 0.09 W).", 48.26, 309.27, 1.3)

    if FALLBACKS:
        print("sheet_nmr_tx: %d symbols still missing from cb_symbols (Value and footprint are correct): %s"
              % (len(FALLBACKS), "; ".join("%s = %s on %s [%s]" % t for t in FALLBACKS)))
    auto_junctions(sh)
    return sh

# ================================================================== PCB placement (ZONE_B)
# Board outline v0.7 final: 180 x 100; everything that sat at x >= 129 moved +40 mm with the
# outline, so the free block in ZONE_B is now x 129.2 - 170.5, y 36.5 - 99.5 (nearest
# neighbours: R513 / R515 at x <= 128.9, the J501-J507 terminal column at x >= 170.8).
#   left column  x 129.8 - 150.0 : AD9834, reconstruction filter, mid-rail bias, gain leg
#   right column x 150.6 - 170.4 : OPA564, its supplies and the whole output chain
# v0.8: J802 and the J501-J507 terminal column left the board, so the right edge is free area.
PLACEMENT = {
    # --- AD9834 DDS and its decoupling / set-up passives ---
    "U801": (134.01, 41.24, 0),
    "C801": (139.73, 38.21, 0), "C802": (143.51, 38.21, 0), "C806": (147.86, 38.40, 0),
    "FB801": (139.76, 40.57, 0),
    "C803": (143.57, 41.01, 0), "C804": (147.35, 41.01, 0), "C805": (139.73, 42.93, 0),
    "R801": (143.51, 43.38, 0), "R804": (147.29, 43.38, 0),
    # --- DAC loads and the reconstruction filter ---
    "R802": (146.31, 45.70, 0), "R803": (131.69, 46.64, 0),
    "C807": (135.47, 46.69, 0), "C808": (146.31, 48.07, 0),
    "L801": (141.13, 46.69, 0), "C809": (131.69, 49.01, 0), "C810": (135.47, 49.11, 0),
    # --- gain leg, mid-rail bias and the DDS pull-downs ---
    "C813": (143.88, 54.01, 0), "JP801": (132.35, 51.82, 0),
    "R807": (131.69, 54.98, 0), "R808": (135.47, 54.98, 0),
    "R805": (131.69, 57.30, 0), "R806": (135.47, 57.30, 0),
    "C811": (132.26, 59.86, 0), "C812": (136.61, 59.95, 0),
    "R817": (140.39, 59.90, 0), "R818": (144.17, 59.90, 0),
    # --- OPA564 power stage (right column, next to J802) ---
    "U802": (158.00, 62.20, 0),
    "FB802": (166.89, 54.00, 0),          # >= 3 A bead, first part on the +VEXT branch
    "C816": (166.89, 57.21, 0), "C814": (166.89, 59.63, 0), "C815": (155.52, 72.28, 0),
    "R809": (166.89, 62.00, 0), "R810": (166.89, 64.32, 0),
    "R811": (166.89, 66.64, 0), "R812": (166.89, 68.96, 0),
    # --- output chain, clamps and the -20 dB pad (lowest, closest to J802) ---
    "R813": (164.88, 72.58, 0), "C818": (161.72, 80.49, 0),
    "D801": (164.47, 76.97, 0), "D802": (154.63, 78.09, 0),
    "R814": (167.04, 80.32, 0), "C817": (152.49, 81.23, 0),
    "JP802": (167.33, 83.24, 0), "R815": (156.27, 81.18, 0), "R816": (160.05, 83.24, 0),
    # --- TX terminal: FRONT edge, as far right as the board allows (extent x 160.5-171.8).
    #     It cannot go on the right edge as first planned: terminal J505 reaches y 87.2 and
    #     mounting hole H4 (172.6-179.4 / 92.5-99.5) takes the corner, leaving a 5.1 mm gap
    #     where the 2P terminal needs 11.2 mm.
}
