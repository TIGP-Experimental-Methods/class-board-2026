"""NMR RX sheet (section A) — v0.7.

Si5351A clock generator + 74HC74 Johnson quadrature divider, tuned tank with crossed-diode
limiter, two-stage LNA, DG419 blanking, double-balanced I/Q commutating mixer on two
TS5A23157 and the IF difference amplifiers that drive COND_OUT1/COND_OUT2 (= ADS8688 ch 7/8).

Design source: notes/2026-09-13-v07-nmr-circuits.md sections 0, 1, 3, 4 and 8.
Every value below carries the justification given there.

Interface (global labels)
  in   RX          panel SMA centre pin (the receive coil), from the link sheet
       AUX         panel AUX SMA, alternative LNA input through JP701 (open by default)
       RX_BLANK    GPIO8, active-low-receive (0 = blanked)
       I2C_SDA/SCL 400 kHz bus, Si5351A at 0x60
       EXP_P14     TCA9535 P1.4 -> /CLR of the Johnson counter (10 k pull-up here)
  out  CLK0_MCLK   50.000 MHz to the AD9834 MCLK on the NMR TX sheet (R703 = 33 R here)
       COND_OUT1   I baseband  -> JP101 -> ADS8688 AIN (channel 7)
       COND_OUT2   Q baseband  -> JP102 -> ADS8688 AIN (channel 8)
  rails +3V3, +3V3A (made here: FB901 + 10 uF + 100 nF), +5VA (DG419 VL), +-12V, GND, AGND
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cb_sch import Sheet, Inst, g              # noqa: E402,F401
from cb_symbols import SYMBOLS                 # noqa: E402
from gen_sch import Ctx, sheet_frame, auto_junctions   # noqa: E402

BLOCK = "NMR_RX"
HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# ------------------------------------------------------------------ symbol resolution
# The second symbol batch (74HC74D, OPA1656IDR, C0G values, 0.1 % resistors, PWR_p3V3A /
# PWR_V_MID) is written by another agent.  Everything here degrades gracefully: passives fall
# back to the generic R0603/C0603 symbol with an explicit Value (footprint and netlist value are
# then still right), op-amps fall back to the OPA1612 the design document names as the alternate,
# and the two new power symbols fall back to labels.  SUBS records what had to be substituted.
SUBS = []


def _first(cands, fallback, what):
    for n in cands:
        if n in SYMBOLS:
            return n
    SUBS.append((what, fallback))
    return fallback


def _short(v):
    """'1.00k' -> '1k', '20.0k' -> '20k', '9.09k' -> '9.09k'"""
    if "." not in v:
        return v
    head, tail = v.split(".", 1)
    frac = tail.rstrip("kMRmunpF")
    suf = tail[len(frac):]
    return head + suf if frac.strip("0") == "" else v


def _rsym(v):
    c = ["R0603_" + v, "R0603_" + v.replace(".", "R"), "R0603_" + _short(v)]
    return _first(c, "R0603_10k", "R %s" % v)


def _csym(v):
    if v in ("10uF", "22uF"):
        return _first(["C0805_" + v, "C1206_" + v], "C0805_10uF", "C %s" % v)
    c = ["C0603_" + v, "C0603_" + v.replace(".", "R"), "C0603_" + _short(v)]
    return _first(c, "C0603_100nF", "C %s" % v)


FF_SYM = _first(["74HC74D,653", "74HC74D", "74HC74", "SN74HC74D", "74HC74DR"], "SN74AHCT541PWR", "74HC74D,653")
LNA_SYM = _first(["OPA1656IDR", "OPA1656"], "OPA1612AIDR", "OPA1656IDR")
FB_SYM = _first(["FB0603_600R"], "FB0603_600R", "FB 600R")
HAS_3V3A = "PWR_p3V3A" in SYMBOLS
HAS_VMID = "PWR_V_MID" in SYMBOLS
if not HAS_3V3A:
    SUBS.append(("PWR_p3V3A", "global label +3V3A"))
if not HAS_VMID:
    SUBS.append(("PWR_V_MID", "local label V_MID"))

A3V3 = ("p", "+3V3A") if HAS_3V3A else ("g", "+3V3A")
VMID = ("p", "V_MID") if HAS_VMID else ("l", "V_MID")

# ------------------------------------------------------------------ part table (ref -> symbol, value, dnp)
PART = {}


def _reg(ref, lib, value=None, dnp=False):
    PART[ref] = (lib, value, dnp)
    return ref


def _R(ref, v, dnp=False):
    return _reg(ref, _rsym(v), v, dnp)


def _C(ref, v):
    return _reg(ref, _csym(v), v)


# --- clocks (section 1) -------------------------------------------------------------------
_reg("U701", "SI5351A-B-GT")
_reg("Y701", "X322525MOB4SI", "25 MHz")
# The 3.9 pF NP0 symbol is named C0603_4pF (the design value); _csym would fall back to the 100 nF part.
_reg("C701", _first(["C0603_4pF"], "C0603_100nF", "C 3.9pF"), "3.9pF")
_reg("C702", _first(["C0603_4pF"], "C0603_100nF", "C 3.9pF"), "3.9pF")   # 12 pF crystal + 10 pF internal (datasheet 4.1.1)
_C("C703", "100nF"); _C("C704", "1uF"); _C("C705", "100nF")
_R("R701", "4.7k", dnp=True); _R("R702", "4.7k", dnp=True)   # base board already fits the I2C pull-ups
_R("R703", "33")                                          # CLK0 = 50.000 MHz -> AD9834 MCLK
_R("R704", "100"); _C("C706", "47pF")                     # CLK1 = 4*f_LO, tau = 4.7 ns
_R("R705", "33")                                          # CLK2 -> test point
_reg("U702", FF_SYM, "74HC74D,653")
_C("C707", "100nF"); _R("R706", "10k")                    # /CLR pull-up to +3V3A, pad to TCA9535 P1.4
_reg("TP701", "TestPoint", "CLK2")

# --- receiver (section 3) -----------------------------------------------------------------
_reg("JP701", "SolderJumper_3_Open", "AUX -> LNA (open)")
_reg("D703", "1N4148W"); _reg("D704", "1N4148W")          # crossed-diode limiter at the connector
_C("C710", "1.2nF"); _C("C711", "100pF"); _C("C712", "22pF")   # tank trim, 1.25 nF total
_R("R710", "100"); _R("R711", "1M")
_reg("U703", LNA_SYM, "OPA1656IDR")
_R("R712", "10.0k"); _R("R713", "100"); _R("R714", "1.00k")    # G = 101; R714 = the document's R712b
_reg("JP702", "SolderJumper_3_Bridged12", "G=101 / G=11")
_C("C720", "10nF"); _R("R721", "10k")                     # f_HP = 1.59 kHz, tau = 100 us
_reg("U704", "DG419DY-T1-E3")
_reg("R722", _first(["R0603_9R09k"], "R0603_10k", "R 9.1k"), "9.1k")   # symbol named for the 9.09 k design value
_R("R723", "1.00k"); _C("C721", "100pF")                  # G = 10, pole 175 kHz
_reg("JP703", "SolderJumper_2_Bridged", "open = G 1")
for _r in ("C722", "C723", "C724", "C725"):
    _C(_r, "100nF")
_C("C726", "10uF"); _C("C727", "10uF")
_R("R724", "10k")                                         # RX_BLANK pull-DOWN: un-driven = blanked

# --- mixer and IF (section 4) --------------------------------------------------------------
_reg("FB901", FB_SYM, "600R@100MHz")
_C("C905", "10uF"); _C("C906", "100nF")                   # +3V3A
_reg("U705", "OPA1612AIDR")
_R("R901", "10.0k"); _R("R902", "10.0k")                  # unity-gain inverter, 0.1 %
_R("R903", "10k"); _R("R904", "10k"); _R("R905", "100")   # V_MID = 1.65 V buffer
for _r in ("C901", "C902", "C903", "C904"):
    _C(_r, "10nF")
for _r in ("R906", "R907", "R908", "R909"):
    _R(_r, "10k")
for _r in ("D905", "D906", "D907", "D908"):
    _reg(_r, "BAV99")
_reg("U901", "TS5A23157DGSR"); _reg("U902", "TS5A23157DGSR")
_C("C907", "100nF"); _C("C908", "100nF")
for _r in ("R910", "R911", "R912", "R913"):
    _R(_r, "1.00k")
for _r in ("C910", "C911", "C912", "C913"):
    _C(_r, "10nF")                                        # passive IF pole 15.9 kHz
_reg("U706", "OPA1612AIDR")
for _r in ("R914", "R916", "R918", "R923"):
    _R(_r, "1.00k")
for _r in ("R915", "R917", "R919", "R924"):
    _R(_r, "20.0k")                                       # G_diff = 20, 0.1 % thin film
_C("C914", "560pF"); _C("C915", "560pF")                  # active pole 14.2 kHz
for _r in ("C916", "C917", "C918", "C919"):
    _C(_r, "100nF")
_reg("TP702", "TestPoint", "V_MID")


# ------------------------------------------------------------------ drawing helpers
def _place(c, ref, x, y, rot=0, unit=1):
    lib, val, dnp = PART[ref]
    return c.place(ref, lib, x, y, rot, unit=unit, value=val, dnp=dnp)


def _hook(c, inst, pin, spec, length=5.08):
    kind, name = spec
    if kind == "p":
        c.pwr_pin(inst, pin, name, length)
    elif kind == "g":
        c.glabel_pin(inst, pin, name, length)
    elif kind == "l":
        c.label_pin(inst, pin, name, length)
    elif kind == "n":
        c.nc_pin(inst, pin)


def _hooks(c, inst, spec_list, length=5.08):
    for item in spec_list:
        _hook(c, inst, item[0], item[1], item[2] if len(item) > 2 else length)


def _farm(c, x0, y0, dx, dy, nrow, items):
    """grid of small parts: items = (ref, rot, [(pin, spec), ...])"""
    for k, (ref, rot, hooks) in enumerate(items):
        inst = _place(c, ref, x0 + (k // nrow) * dx, y0 + (k % nrow) * dy, rot)
        _hooks(c, inst, hooks)


def _net_at(c, sh, x, y, spec, pwr_rot=270):
    kind, name = spec
    if kind == "p":
        c.power_at(x, y, name, pwr_rot)
    else:
        sh.label(name, x, y, 0, "global" if kind == "g" else "local")


# ================================================================== schematic
def build(root_uuid):
    sh = Sheet("nmr_rx", "NMR RX (A): tank, LNA, blanking, I/Q mixer, IF -> ADC ch 7/8", "A2", 10,
               "Si5351A + 74HC74 Johnson divider; OPA1656 LNA x1000; DG419 blanking; two TS5A23157 as a "
               "double-balanced commutator; OPA1612 difference amplifiers -> COND_OUT1/2")
    c = Ctx(sh, BLOCK, 7000)
    sheet_frame(sh, BLOCK, "NMR RX (section A) — clocks, tuned tank, LNA, blanking, I/Q commutating mixer, IF", [
        "Design coil: 400 turns AWG26, 4 cm x 10 cm, L = 2.53 mH, R_DC = 6.7 R. Tuned with 1.25 nF at f_Larmor = 89.4 kHz (B0 = 2.1 mT): X_L = 1419 R, R_p = Q*X_L = 14.2 kOhm at Q = 10, tank noise 15.3 nV/rtHz, signal 40 uV pk (v0.7 NMR circuits doc section 0).",
        "LNA: the source impedance is 14.2 kOhm, so CURRENT noise decides. OPA1656 (FET, 6 fA/rtHz) gives NF = 0.15 dB; the OPA1612 (1.7 pA/rtHz) would cost 5.5 dB = 3.5x more averages. Gain 101 x 10 = 1000 puts 40 mV pk at the mixer and 1.02 V pk on the ADC (section 3.2 / 4.3).",
        "Blanking sits BETWEEN the stages: 60 pC of DG419 charge injection lands on C720 = 10 nF as 6 mV, not on the 1.25 nF tank as 48 mV. Interstage coupling 10 nF / 10 k = 1.59 kHz, so the receiver recovers in 0.3 ms instead of the 300 ms a 1 uF / 100 k would need (section 3.3). RX_BLANK: 0 = blanked (default, 10 k pull-down R724), 1 = receive — an un-driven GPIO leaves the receiver blanked.",
        "Quadrature LO: the Si5351 phase register cannot do 90 deg below 4.72 MHz (PHOFF is 7 bit in units of T_VCO/4, AN619 section 6). U702 is a 2-bit Johnson counter on CLK1 = 4*f_LO: FF1 D = /Q2, FF2 D = Q1 -> LO_I and LO_Q exactly 90 deg apart at any frequency (section 1.4). Pulse /CLR after every PLLB change so the counter always starts in state 00.",
        "Mixer supply is +3V3A, NOT +5VA: the TS5A23157 needs V_IH = 0.7*V+ = 3.5 V at 5 V, which a 3.3 V CMOS LO never meets; at 3.3 V it is 2.31 V with 1.0 V of margin (section 4.1). FB901 + 10 uF + 100 nF make +3V3A from +3V3.",
        "Double-balanced commutator: U901 switches S+/S- into COM (I+ and Q+), U902 the same with the inputs swapped (I- and Q-). The difference amplifiers (G = 20, 0.1 % thin film -> CMRR 54 dB) reject V_MID and the LO-synchronous charge injection; the reference leg returns to AGND so COND_OUT1/2 are centred on 0 V for the ADC's +-5.12 V range (section 4.2).",
        "Grounding (section 8): everything analog on AGND, including U702 (which runs from +3V3A) and the switches, so the commutation instants share the signal ground. The Si5351 is on GND; the single line that crosses is CLK1, damped by R704 / C706. AGND meets GND only at NT1 on the base sheet.",
    ])

    # ---------------------------------------------------------------- 1. CLOCKS
    sh.text("1 — CLOCKS: Si5351A (I2C 0x60) + 74HC74 Johnson quadrature divider", 25, 56, 2.2, True)
    U701 = _place(c, "U701", 65, 85)
    _hooks(c, U701, [(1, ("p", "+3V3"), 7.62), (7, ("p", "+3V3"), 13.97), (8, ("p", "GND"), 7.62),
                     (4, ("g", "I2C_SCL"), 7.62), (5, ("g", "I2C_SDA"), 7.62),
                     (2, ("l", "XTAL_A"), 7.62), (3, ("l", "XTAL_B"), 7.62),
                     (10, ("l", "SI_CLK0"), 7.62), (9, ("l", "SI_CLK1"), 7.62), (6, ("l", "SI_CLK2"), 7.62)])
    Y701 = _place(c, "Y701", 65, 130)
    _hooks(c, Y701, [(1, ("l", "XTAL_A")), (3, ("l", "XTAL_B")), (2, ("p", "GND")), (4, ("p", "GND"))])
    sh.text("C9006 is a 12 pF crystal: XTAL_CL = 10 pF internal + 4 pF on each of XA/XB = 2 pF external", 25, 143, 1.3)

    U702 = _place(c, "U702", 175, 95)
    _hooks(c, U702, [(14, A3V3, 6.35), (7, ("p", "AGND"), 6.35),
                     (1, ("g", "EXP_P14"), 6.35), (13, ("g", "EXP_P14"), 6.35),
                     (4, A3V3, 6.35), (10, A3V3, 6.35),
                     (3, ("l", "CLK1"), 6.35), (11, ("l", "CLK1"), 6.35),
                     (2, ("l", "LO_QN"), 6.35), (8, ("l", "LO_QN"), 6.35),
                     (12, ("l", "LO_I"), 6.35), (5, ("l", "LO_I"), 6.35),
                     (9, ("l", "LO_Q"), 6.35), (6, ("n", ""))])
    sh.text("U702 = 74HC74D,653 dual D flip-flop as a 2-bit Johnson counter. Pins: 1/13 /CLR, 2/12 D, 3/11 CLK,", 140, 143, 1.3)
    sh.text("4/10 /PRE, 5/9 Q, 6/8 /Q, 7 GND, 14 VCC. States 00 -> 10 -> 11 -> 01: LO_Q lags LO_I by exactly 90 deg.", 140, 146.5, 1.3)

    # +3V3A: FB901 + 10 uF + 100 nF from +3V3
    FB = _place(c, "FB901", 255, 75, 90)
    c.pwr_pin(FB, 1, "+3V3", 5.08)
    e = sh.stub(FB, 2, 7.62)
    sh.wire(e[0], e[1], 290, e[1])
    c.flag(272, e[1])
    _net_at(c, sh, 290, e[1], A3V3, 270)
    sh.text("+3V3A — analog 3.3 V for U702 / U901 / U902 (section 4.1)", 235, 63, 1.4, True)

    TP701 = _place(c, "TP701", 300, 95, 0)
    c.label_pin(TP701, 1, "CLK2_TP", 5.08)
    sh.text("CLK2 = spare clock / scope trigger", 285, 110, 1.3)

    # clock + rail passive farm
    _farm(c, 350, 60, 66, 8.89, 8, [
        ("C701", 90, [(1, ("l", "XTAL_A")), (2, ("p", "GND"))]),
        ("C702", 90, [(1, ("l", "XTAL_B")), (2, ("p", "GND"))]),
        ("C703", 90, [(1, ("p", "+3V3")), (2, ("p", "GND"))]),
        ("C704", 90, [(1, ("p", "+3V3")), (2, ("p", "GND"))]),
        ("C705", 90, [(1, ("p", "+3V3")), (2, ("p", "GND"))]),
        ("R701", 90, [(1, ("p", "+3V3")), (2, ("g", "I2C_SDA"))]),
        ("R702", 90, [(1, ("p", "+3V3")), (2, ("g", "I2C_SCL"))]),
        ("R703", 90, [(1, ("l", "SI_CLK0")), (2, ("g", "CLK0_MCLK"))]),
        ("R704", 90, [(1, ("l", "SI_CLK1")), (2, ("l", "CLK1"))]),
        ("C706", 90, [(1, ("l", "CLK1")), (2, ("p", "AGND"))]),
        ("R705", 90, [(1, ("l", "SI_CLK2")), (2, ("l", "CLK2_TP"))]),
        ("R706", 90, [(1, A3V3), (2, ("g", "EXP_P14"))]),
        ("C707", 90, [(1, A3V3), (2, ("p", "AGND"))]),
        ("C905", 90, [(1, A3V3), (2, ("p", "AGND"))]),
        ("C906", 90, [(1, A3V3), (2, ("p", "AGND"))]),
        ("C907", 90, [(1, A3V3), (2, ("p", "AGND"))]),
        ("C908", 90, [(1, A3V3), (2, ("p", "AGND"))]),
        ("C916", 90, [(1, ("p", "+12V")), (2, ("p", "AGND"))]),
        ("C917", 90, [(1, ("p", "-12V")), (2, ("p", "AGND"))]),
        ("C918", 90, [(1, ("p", "+12V")), (2, ("p", "AGND"))]),
        ("C919", 90, [(1, ("p", "-12V")), (2, ("p", "AGND"))]),
        ("C722", 90, [(1, ("p", "+12V")), (2, ("p", "AGND"))]),
        ("C723", 90, [(1, ("p", "-12V")), (2, ("p", "AGND"))]),
        ("C724", 90, [(1, ("p", "+12V")), (2, ("p", "AGND"))]),
        ("C725", 90, [(1, ("p", "-12V")), (2, ("p", "AGND"))]),
        ("C726", 90, [(1, ("p", "+12V")), (2, ("p", "AGND"))]),
        ("C727", 90, [(1, ("p", "-12V")), (2, ("p", "AGND"))]),
    ])
    sh.text("Decoupling: C703/C704 VDD, C705 VDDO (Si5351, GND); C707 U702, C906/C907/C908 +3V3A (AGND);", 350, 52, 1.3)
    sh.text("C722-C727 U703/U704 +-12 V, C916-C919 U705/U706 +-12 V (all AGND). C905 = 10 uF on +3V3A.", 350, 55.5, 1.3)

    # ---------------------------------------------------------------- 2. RECEIVER
    sh.text("2 — RECEIVER: crossed-diode limiter, tuned tank, OPA1656 x1000, DG419 blanking", 25, 170, 2.2, True)
    sh.text("RX = link pin 37 (panel SMA, receive coil). D703/D704 and their AGND return sit within 5 mm of the pin.", 25, 178, 1.3)

    U703a = _place(c, "U703", 100, 200, 0, unit=1)
    _hooks(c, U703a, [(3, ("l", "RX_IN"), 6.35), (2, ("l", "LNA_FB1"), 6.35), (1, ("l", "LNA1_OUT"), 6.35)])
    U703b = _place(c, "U703", 100, 240, 0, unit=2)
    _hooks(c, U703b, [(5, ("l", "ST2_IN"), 6.35), (6, ("l", "LNA_FB2"), 6.35), (7, ("l", "LNA_OUT"), 6.35)])
    U703p = _place(c, "U703", 165, 195, 0, unit=3)
    _hooks(c, U703p, [(8, ("p", "+12V"), 6.35), (4, ("p", "-12V"), 6.35)])
    sh.text("Stage 1: G = 1 + R712/R713 = 1 + 10 000/100 = 101", 78, 214, 1.3)
    sh.text("Stage 2: G = 1 + R722/R723 = 1 + 9090/1000 = 10.0", 78, 254, 1.3)

    U704 = _place(c, "U704", 240, 210, 0)
    _hooks(c, U704, [(8, ("l", "BLK_IN"), 6.35), (2, ("p", "AGND"), 6.35), (6, ("g", "RX_BLANK"), 6.35),
                     (1, ("l", "ST2_IN"), 6.35), (4, ("p", "+12V"), 6.35), (5, ("p", "+5VA"), 6.35),
                     (3, ("p", "AGND"), 6.35), (7, ("p", "-12V"), 6.35)])
    sh.text("DG419: logic 0 -> SW1 on, so RX_BLANK = 0 ties the stage-2 input (D) to AGND = BLANKED.", 205, 232, 1.3)
    sh.text("VL = +5VA (V_IH = 2.4 V, so a 3.3 V CMOS drive has 0.9 V of margin); V+/V- = +-12 V.", 205, 235.5, 1.3)
    sh.text("RX_BLANK: 0 = blanked (default, 10 k pull-down), 1 = receive.", 205, 241, 1.3, True)
    sh.text("R724 goes to AGND, not to +3V3 as the design document's netlist table says: logic 0 blanks, so only a", 205, 244.2, 1.3, True)
    sh.text("pull-DOWN gives the blanked-by-default the same document asks for in section 3.3 (instructor, 2026-09-13).", 205, 247.4, 1.3, True)

    JP701 = _place(c, "JP701", 75, 275, 0)
    _hooks(c, JP701, [(1, ("g", "AUX")), (2, ("l", "RX_IN")), (3, ("p", "AGND"))])
    sh.text("JP701: AUX -> LNA input (1-2), or AUX to AGND (2-3). Open by default.", 40, 288, 1.3)
    JP702 = _place(c, "JP702", 175, 275, 0)
    _hooks(c, JP702, [(1, ("l", "JP702A")), (2, ("l", "LNA_FB1")), (3, ("l", "JP702B"))])
    sh.text("JP702: stage-1 feedback select. 1-2 bridged (default) = R712, G = 101; cut and bridge 2-3 = R714, G = 11.", 140, 288, 1.3)
    JP703 = _place(c, "JP703", 300, 275, 90)
    _hooks(c, JP703, [(1, ("l", "ST2_GAIN")), (2, ("p", "AGND"))])
    sh.text("JP703 is in series with the R723 ground leg: cut it and stage 2 becomes a unity follower (G = 1).", 265, 291.5, 1.3)

    _farm(c, 340, 180, 66, 8.89, 8, [
        ("D703", 0, [(1, ("p", "AGND")), (2, ("g", "RX"))]),
        ("D704", 180, [(1, ("g", "RX")), (2, ("p", "AGND"))]),
        ("C710", 90, [(1, ("g", "RX")), (2, ("p", "AGND"))]),
        ("C711", 90, [(1, ("g", "RX")), (2, ("p", "AGND"))]),
        ("C712", 90, [(1, ("g", "RX")), (2, ("p", "AGND"))]),
        ("R711", 90, [(1, ("g", "RX")), (2, ("p", "AGND"))]),
        ("R710", 90, [(1, ("g", "RX")), (2, ("l", "RX_IN"))]),
        ("R712", 90, [(1, ("l", "LNA1_OUT")), (2, ("l", "JP702A"))]),
        ("R714", 90, [(1, ("l", "LNA1_OUT")), (2, ("l", "JP702B"))]),
        ("R713", 90, [(1, ("l", "LNA_FB1")), (2, ("p", "AGND"))]),
        ("C720", 90, [(1, ("l", "LNA1_OUT")), (2, ("l", "BLK_IN"))]),
        ("R721", 90, [(1, ("l", "ST2_IN")), (2, ("p", "AGND"))]),
        ("R722", 90, [(1, ("l", "LNA_FB2")), (2, ("l", "LNA_OUT"))]),
        ("C721", 90, [(1, ("l", "LNA_FB2")), (2, ("l", "LNA_OUT"))]),
        ("R723", 90, [(1, ("l", "LNA_FB2")), (2, ("l", "ST2_GAIN"))]),
        ("R724", 90, [(1, ("g", "RX_BLANK")), (2, ("p", "AGND"))]),
    ])
    sh.text("Tank: C710 1.2 nF + C711 100 pF + C712 22 pF = 1.322 nF of pads; stuff to the 1.25 nF the coil needs.", 340, 172, 1.3)
    sh.text("Preferred practice is to tune AT THE COIL: 1 m of RG174 adds ~100 pF = 8 % detune.", 340, 175.5, 1.3)

    # ---------------------------------------------------------------- 3. MIXER + IF
    sh.text("3 — I/Q COMMUTATING MIXER AND IF (9xx): double-balanced, both switch packages used", 25, 297, 2.2, True)
    U705a = _place(c, "U705", 60, 315, 0, unit=1)
    _hooks(c, U705a, [(3, ("p", "AGND"), 6.35), (2, ("l", "INV_N"), 6.35), (1, ("l", "S_MINUS"), 6.35)])
    sh.text("U705A: unity-gain inverter, S- = -S+", 33, 330, 1.3)
    U705b = _place(c, "U705", 145, 315, 0, unit=2)
    _hooks(c, U705b, [(5, ("l", "VMID_DIV"), 6.35), (6, ("l", "VMID_BUF"), 6.35), (7, ("l", "VMID_BUF"), 6.35)])
    sh.text("U705B: V_MID = 1.65 V buffer (R903/R904 from +3V3A), R905 = 100 R in series out", 108, 330, 1.3)
    U705p = _place(c, "U705", 210, 308, 0, unit=3)
    _hooks(c, U705p, [(8, ("p", "+12V"), 6.35), (4, ("p", "-12V"), 6.35)])

    U901 = _place(c, "U901", 275, 320, 0)
    _hooks(c, U901, [(1, ("l", "LO_I"), 6.35), (5, ("l", "LO_Q"), 6.35),
                     (10, ("l", "IF_IP"), 6.35), (6, ("l", "IF_QP"), 6.35),
                     (9, ("l", "SN_A"), 6.35), (2, ("l", "SP_A"), 6.35),
                     (7, ("l", "SN_A"), 6.35), (4, ("l", "SP_A"), 6.35),
                     (8, A3V3, 6.35), (3, ("p", "AGND"), 6.35)])
    sh.text("U901 = I+ / Q+  (NO = S+, NC = S-)", 248, 353, 1.3)
    U902 = _place(c, "U902", 360, 320, 0)
    _hooks(c, U902, [(1, ("l", "LO_I"), 6.35), (5, ("l", "LO_Q"), 6.35),
                     (10, ("l", "IF_IN"), 6.35), (6, ("l", "IF_QN"), 6.35),
                     (9, ("l", "SP_B"), 6.35), (2, ("l", "SN_B"), 6.35),
                     (7, ("l", "SP_B"), 6.35), (4, ("l", "SN_B"), 6.35),
                     (8, A3V3, 6.35), (3, ("p", "AGND"), 6.35)])
    sh.text("U902 = I- / Q-  (inputs SWAPPED: NO = S-, NC = S+)", 333, 353, 1.3)

    U706a = _place(c, "U706", 445, 315, 0, unit=1)
    _hooks(c, U706a, [(3, ("l", "DIF_I_P"), 6.35), (2, ("l", "DIF_I_N"), 6.35), (1, ("g", "COND_OUT1"), 6.35)])
    sh.text("U706A: I difference amp, G = 20 -> COND_OUT1 (JP101, ADC ch 7)", 415, 330, 1.3)
    U706b = _place(c, "U706", 445, 355, 0, unit=2)
    _hooks(c, U706b, [(5, ("l", "DIF_Q_P"), 6.35), (6, ("l", "DIF_Q_N"), 6.35), (7, ("g", "COND_OUT2"), 6.35)])
    sh.text("U706B: Q difference amp, G = 20 -> COND_OUT2 (JP102, ADC ch 8)", 415, 370, 1.3)
    U706p = _place(c, "U706", 530, 308, 0, unit=3)
    _hooks(c, U706p, [(8, ("p", "+12V"), 6.35), (4, ("p", "-12V"), 6.35)])

    TP702 = _place(c, "TP702", 60, 338, 0)
    e = sh.stub(TP702, 1, 5.08)
    sh.wire(e[0], e[1], e[0] + 20.32, e[1])
    c.flag(e[0] + 7.62, e[1])
    _net_at(c, sh, e[0] + 20.32, e[1], VMID, 270)
    sh.text("V_MID = 1.65 V, made by U705B; PWR_FLAG because no power_output pin drives it", 33, 336, 1.3)

    # BAV99 clamps on the four switch inputs (3 pins each)
    for k, (ref, node) in enumerate([("D905", "SP_A"), ("D906", "SN_A"), ("D907", "SN_B"), ("D908", "SP_B")]):
        d = _place(c, ref, 120 + k * 60, 342, 0)
        _hooks(c, d, [(1, ("p", "AGND")), (2, A3V3), (3, ("l", node))])
    sh.text("D905-D908: BAV99 clamps to AGND / +3V3A — the LNA runs on +-12 V and must not push the switch inputs outside 0..3.3 V.", 105, 334, 1.3)

    _farm(c, 40, 360, 66, 8.89, 5, [
        ("R901", 90, [(1, ("l", "LNA_OUT")), (2, ("l", "INV_N"))]),
        ("R902", 90, [(1, ("l", "INV_N")), (2, ("l", "S_MINUS"))]),
        ("R903", 90, [(1, A3V3), (2, ("l", "VMID_DIV"))]),
        ("R904", 90, [(1, ("l", "VMID_DIV")), (2, ("p", "AGND"))]),
        ("R905", 90, [(1, ("l", "VMID_BUF")), (2, VMID)]),
        ("C901", 90, [(1, ("l", "LNA_OUT")), (2, ("l", "SP_A"))]),
        ("C902", 90, [(1, ("l", "S_MINUS")), (2, ("l", "SN_A"))]),
        ("C903", 90, [(1, ("l", "S_MINUS")), (2, ("l", "SN_B"))]),
        ("C904", 90, [(1, ("l", "LNA_OUT")), (2, ("l", "SP_B"))]),
        ("R906", 90, [(1, ("l", "SP_A")), (2, VMID)]),
        ("R907", 90, [(1, ("l", "SN_A")), (2, VMID)]),
        ("R908", 90, [(1, ("l", "SN_B")), (2, VMID)]),
        ("R909", 90, [(1, ("l", "SP_B")), (2, VMID)]),
        ("R910", 90, [(1, ("l", "IF_IP")), (2, ("l", "IF_IPF"))]),
        ("R911", 90, [(1, ("l", "IF_QP")), (2, ("l", "IF_QPF"))]),
        ("R912", 90, [(1, ("l", "IF_IN")), (2, ("l", "IF_INF"))]),
        ("R913", 90, [(1, ("l", "IF_QN")), (2, ("l", "IF_QNF"))]),
        ("C910", 90, [(1, ("l", "IF_IPF")), (2, VMID)]),
        ("C911", 90, [(1, ("l", "IF_QPF")), (2, VMID)]),
        ("C912", 90, [(1, ("l", "IF_INF")), (2, VMID)]),
        ("C913", 90, [(1, ("l", "IF_QNF")), (2, VMID)]),
        ("R914", 90, [(1, ("l", "IF_INF")), (2, ("l", "DIF_I_N"))]),
        ("R915", 90, [(1, ("l", "DIF_I_N")), (2, ("g", "COND_OUT1"))]),
        ("C914", 90, [(1, ("l", "DIF_I_N")), (2, ("g", "COND_OUT1"))]),
        ("R916", 90, [(1, ("l", "IF_IPF")), (2, ("l", "DIF_I_P"))]),
        ("R917", 90, [(1, ("l", "DIF_I_P")), (2, ("p", "AGND"))]),
        ("R918", 90, [(1, ("l", "IF_QNF")), (2, ("l", "DIF_Q_N"))]),
        ("R919", 90, [(1, ("l", "DIF_Q_N")), (2, ("g", "COND_OUT2"))]),
        ("C915", 90, [(1, ("l", "DIF_Q_N")), (2, ("g", "COND_OUT2"))]),
        ("R923", 90, [(1, ("l", "IF_QPF")), (2, ("l", "DIF_Q_P"))]),
        ("R924", 90, [(1, ("l", "DIF_Q_P")), (2, ("p", "AGND"))]),
    ])

    lv = [["Node", "Level", "Note"],
          ["coil, tuned Q = 10", "40 uV pk", "4 uV untuned x Q (regimes doc section 2)"],
          ["LNA out (101 x 10)", "40 mV pk", "OPA1656, f_3dB = 525 kHz at G = 101"],
          ["mixer, 2 x (2/pi) x 20", "x 25.5", "square LO fundamental 4/pi, cos*cos halves it"],
          ["ADC in (I and Q)", "1.02 V pk", "6540 LSB of the +-5.12 V / 16-bit range"],
          ["noise at the ADC", "0.40 mV/rtHz", "15.6 nV/rtHz x 25 500 — noise limited, as it must be"]]
    sh.text("End-to-end level plan (section 4.3)", 476, 253, 1.6, True)
    sh.table(476, 255, lv, [30, 22, 46], 1.25)
    sh.text("SNR ~ 15 single shot in 15 kHz; ~ 500 after filtering to the 13 Hz linewidth.", 476, 278, 1.3)

    auto_junctions(sh)
    return sh


# ================================================================== PCB placement
# ZONE_A, v0.7: the old OPT area x 0.5-45 / y 57.5-99.5 (free except the Qwiic ports J3/J4 at
# x 3.4 and the test points TP1-TP4 at x 43.5) plus the B1 pocket x 84-102.5 / y 71-86.8 next to
# the link.  The RX front end (limiter, tank, LNA) goes in the pocket, within a few mm of link
# pins 37/39 at x = 91.6 / 94.1, y = 95.8.  The LO parts (U701, Y701, U702) stay at x < 20, far
# from the LNA (section 8 note 4).  This is a starting point for the instructor's hand layout.
_EST = {"C0603": (3.30, 1.95), "R0603": (3.30, 1.85), "L0603": (3.35, 1.80), "C0805": (4.45, 2.35),
        "C1206": (5.20, 2.60), "SOD-123F": (5.10, 2.55), "SOT-23-3": (4.05, 3.60),
        "SOIC-8": (5.60, 7.50), "SOIC-14": (9.30, 7.50), "MSOP-10": (3.85, 6.35),
        "TSSOP-20": (7.10, 7.60), "CRYSTAL": (4.80, 4.10), "TestPoint": (2.50, 2.50),
        "SolderJumper-3": (4.60, 3.00), "SolderJumper-2": (3.30, 2.50)}


def _load_lib():
    """the project library plus every KiCad standard footprint this sheet asks for.

    Since Decision #47 the chip resistors and capacitors sit on KiCad's own
    Resistor_SMD / Capacitor_SMD lands, so the packing below has to measure those too.
    """
    try:
        from fp_parse import load_mixed
        ids = sorted(set(s.footprint for s in SYMBOLS.values() if s.footprint))
        return load_mixed(os.path.join(HW, "lib", "class_board.pretty"), ids)
    except Exception:                                    # noqa: BLE001
        try:
            from fp_parse import load_library
            return load_library(os.path.join(HW, "lib", "class_board.pretty"))
        except Exception:                                # noqa: BLE001
            return {}


_LIB = _load_lib()


def _extent(ref, rot):
    """board-space (xmin, ymin, xmax, ymax) of the footprint of `ref` placed at (0, 0)"""
    import math
    name = SYMBOLS[PART[ref][0]].footprint.split(":")[-1]
    fp = _LIB.get(name)
    if fp is None:
        w, h = next((v for k, v in _EST.items() if name.startswith(k)), (4.0, 4.0))
        b = (-w / 2.0, -h / 2.0, w / 2.0, h / 2.0)
    else:
        cx = fp.courtyard
        xs, ys = [cx[0], cx[2]], [cx[1], cx[3]]
        if fp.silk:
            xs += [fp.silk[0], fp.silk[2]]
            ys += [fp.silk[1], fp.silk[3]]
        for p in fp.pads:
            r = math.radians(p.rot)
            hx = abs(p.sx / 2 * math.cos(r)) + abs(p.sy / 2 * math.sin(r))
            hy = abs(p.sx / 2 * math.sin(r)) + abs(p.sy / 2 * math.cos(r))
            xs += [p.x - hx, p.x + hx]
            ys += [p.y - hy, p.y + hy]
        b = (min(xs), min(ys), max(xs), max(ys))
    r = math.radians(rot)
    pts = [(x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r))
           for x in (b[0], b[2]) for y in (b[1], b[3])]
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


def _default_rot(ref):
    """0603 passives stand on end (narrow); everything else keeps its natural orientation"""
    name = SYMBOLS[PART[ref][0]].footprint.split(":")[-1]
    return 90 if name in ("R0603", "C0603", "L0603", "R_0603_1608Metric", "C_0603_1608Metric",
                          "L_0603_1608Metric") else 0


# The three panel-link headers (J6 x 12, J7 x 90, J8 x 168) stand on the BOTTOM of the board and
# their pins go through it, so a top-side pad may not sit in the band they sweep (y 24.6 .. 75.4).
# gen_pcb.LINK_HEADERS is the single source of those positions; this list only has to be wide
# enough (header pad column at centre +- 1.27, plus the pad and the clearance).
_LINK_BANDS = [(12.0 - 3.4, 12.0 + 3.4), (90.0 - 3.4, 90.0 + 3.4), (168.0 - 3.4, 168.0 + 3.4)]
_LINK_BAND_Y = (24.6, 75.4)


def _step_over_bands(x, w, y):
    """move x right until the span [x, x+w] clears every link-header band on this row"""
    if not (_LINK_BAND_Y[0] <= y <= _LINK_BAND_Y[1]):
        return x
    moved = True
    while moved:
        moved = False
        for (b0, b1) in _LINK_BANDS:
            if x < b1 and x + w > b0:
                x = b1
                moved = True
    return x


def _row(P, y, x0, x1, refs, gap=0.5, rots=None):
    """pack refs left to right along the row centred on y; returns what did not fit"""
    x = x0
    left = []
    for k, ref in enumerate(refs):
        rot = (rots or {}).get(ref, _default_rot(ref))
        e = _extent(ref, rot)
        w = e[2] - e[0]
        x = _step_over_bands(x, w, y)
        if x + w > x1 + 1e-6:
            left = refs[k:]
            break
        P[ref] = (round(x - e[0], 3), round(y, 3), rot)
        x += w + gap
    return left


def _fill(P, rows, refs, gap=0.5, rots=None):
    for (y, x0, x1) in rows:
        if not refs:
            break
        refs = _row(P, y, x0, x1, refs, gap, rots)
    if refs:
        print("sheet_nmr_rx: PLACEMENT overflow, not placed: %s" % ", ".join(refs))
    return refs


def _placement():
    P = {}
    # ---- B1 pocket (x 84-102.5, y 71-86.8): limiter, tank, LNA, gain jumper, LNA decoupling ----
    # ZONE_A stops at x = 100, so the pocket rows end at 99.5 (copper stays inside the owner area).
    _row(P, 73.5, 77.5, 99.5, ["U703", "R712", "R713", "R714"], rots={"U703": 90})
    _row(P, 78.7, 77.5, 99.5, ["JP702", "R710", "R711", "C722", "C723"])
    # crossed diodes last in the row = nearest the link pins 37/39 at x 91.6 / 94.1
    _row(P, 83.5, 84.5, 99.5, ["C710", "C711", "C712", "D703", "D704"],
         rots={"D703": 90, "D704": 90})
    # ---- OPT area: passive bands and two IC bands ------------------------------------------
    # Obstacles inside the zone: the LDO strip of B2 ends at y 56.4, the Qwiic ports J3/J4 occupy
    # x 0.35-6.65 up to y 72.65, TP1-TP4 sit at x 42.3-44.8, the M3 hole H3 at x 0.55-7.45 /
    # y 92.55-99.45, and the link body J6 starts at x 44.35.
    # band C (y 70.4-76.8): crystal oscillator, kept at x < 17 and away from the LNA (section 8 note 4)
    _row(P, 73.6, 7.2, 41.0, ["U701", "Y701"])
    # band I (y 78.3-85.8): Johnson divider, blanking switch, op-amps, mixer switches
    _row(P, 82.0, 1.0, 41.0, ["U702", "U704", "U705", "U706", "U901", "U902"])
    # passive band P1 (above and beside the clocks) — clock, rail and receiver passives
    p1 = ["C701", "C702", "C703", "C704", "C705", "R701", "R702", "R703", "R704", "C706", "R705",
          "R706", "C707", "FB901", "C905", "C906", "C907", "C908", "C916", "C917", "C918", "C919",
          "C724", "C725", "C726", "C727", "C720", "R721", "R722", "C721", "R723", "R724",
          "JP701", "JP703", "TP701", "TP702"]
    # the rows step around the dev-board socket J1, which sits at y 66.7 from x 33.2 (v0.7b),
    # and around the bottom-side link header J6 at x 12 (see _step_over_bands)
    _fill(P, [(59.4, 7.2, 41.0), (63.2, 7.2, 41.0), (69.8, 25.1, 41.0),
              (73.0, 25.1, 41.0), (76.6, 25.1, 41.0)], p1)
    # passive band P2 (below the ICs) — the whole mixer / IF network
    p2 = ["R901", "R902", "R903", "R904", "R905", "C901", "C902", "C903", "C904",
          "R906", "R907", "R908", "R909", "D905", "D906", "D907", "D908",
          "R910", "R911", "R912", "R913", "C910", "C911", "C912", "C913",
          "R914", "R915", "C914", "R916", "R917", "R918", "R919", "C915", "R923", "R924"]
    _fill(P, [(89.0, 1.0, 41.0), (92.8, 8.2, 41.0), (96.6, 8.2, 41.0)], p2)
    missing = [r for r in PART if r not in P]
    if missing:
        print("sheet_nmr_rx: PLACEMENT missing %s" % ", ".join(sorted(missing)))
    return P


if SUBS:
    print("sheet_nmr_rx: symbol substitutions (Value and footprint are still correct): %s"
          % ", ".join("%s -> %s" % t for t in sorted(set(SUBS))))

PLACEMENT = _placement()

# bounding box of everything this module places (diagnostic)
BBOX = (min(v[0] for v in PLACEMENT.values()), min(v[1] for v in PLACEMENT.values()),
        max(v[0] for v in PLACEMENT.values()), max(v[1] for v in PLACEMENT.values()))
