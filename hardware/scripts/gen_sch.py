"""Generate the class-board hierarchical schematic (D2).

Run from hardware/scripts:  python gen_sch.py
Writes ../class-board.kicad_sch (root), ../sheets/*.kicad_sch and ../class-board.kicad_pro.

Design sources: 10-Class-Board-Design-Brief.md v0.6, docs/design-decisions.md (datasheet-derived
changes: LM66100 ORing, MOSFET relay drivers, opto current limiter, 74HCT125 DAC level shift,
ADS8688/DAC8563 decoupling values).  Interface nets between sheets are GLOBAL labels; rails are
power symbols.  The single AGND-GND join is the net tie NT1 on the base sheet.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import uid, uid_for, q, num  # noqa: E402
from cb_sch import Sheet, Inst, g, xform  # noqa: E402
from cb_symbols import SYMBOLS  # noqa: E402

HW = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT = "class-board"

# ------------------------------------------------------------------ helpers
class Ctx:
    """per-sheet reference/power counters and wiring helpers"""

    def __init__(self, sheet, block, pwr_base):
        self.sh, self.block = sheet, block
        self.npwr = pwr_base

    def pwr_ref(self):
        self.npwr += 1
        return "#PWR%04d" % self.npwr

    def place(self, ref, lib, x, y, rot=0, **k):
        k.setdefault("block", self.block)
        return self.sh.add(Inst(ref, lib, g(x), g(y), rot, **k))

    def power_at(self, x, y, net, rot=0):
        """place a power symbol with its pin at (x,y)"""
        lib = "PWR_" + net.replace("+", "p").replace("-", "n")
        return self.sh.add(Inst(self.pwr_ref(), lib, g(x), g(y), rot))

    def pwr_pin(self, inst, pin, net, length=2.54):
        """stub from the pin and a power symbol oriented along the stub direction"""
        px, py = inst.pin_pos(pin)
        ex, ey = self.sh.stub(inst, pin, length)
        dx, dy = ex - px, ey - py
        down_type = net in ("GND", "AGND", "-12V")
        # rotation that makes the graphic point along (dx, dy): bar types point up at rot 0, gnd types down
        if abs(dx) < 1e-6:
            want = "down" if dy > 0 else "up"
        else:
            want = "right" if dx > 0 else "left"
        if down_type:
            rot = {"down": 0, "right": 90, "up": 180, "left": 270}[want]
        else:
            rot = {"up": 0, "left": 90, "down": 180, "right": 270}[want]
        self.power_at(ex, ey, net, rot)
        return ex, ey

    def flag(self, x, y, rot=0):
        return self.sh.add(Inst(self.pwr_ref(), "PWR_FLAG", g(x), g(y), rot))

    def glabel_pin(self, inst, pin, text, length=2.54, shape="bidirectional"):
        return self.sh.pin_label(inst, pin, text, "global", length, shape)

    def label_pin(self, inst, pin, text, length=2.54):
        return self.sh.pin_label(inst, pin, text, "local", length)

    def nc_pin(self, inst, pin):
        x, y = inst.pin_pos(pin)
        self.sh.nc(x, y)

    def decouple(self, ref, lib, x, y, rail, gnd, rot=0):
        """vertical capacitor: pin 1 (top) -> rail, pin 2 (bottom) -> gnd, both via power symbols"""
        c = self.place(ref, lib, x, y, rot)
        self.pwr_pin(c, 1, rail)
        self.pwr_pin(c, 2, gnd)
        return c


def split_wires_at_pins(sh):
    """KiCad connects a pin only to a wire END point: split segments where a pin end lies inside."""
    pins = set()
    for i in sh.insts:
        for p in i.pins():
            pins.add(i.pin_pos(p.number))
    changed = True
    while changed:
        changed = False
        out = []
        for (x1, y1, x2, y2) in sh.wires:
            hit = None
            for (px, py) in pins:
                if abs(x1 - x2) < 1e-6 and abs(px - x1) < 1e-6 and min(y1, y2) + 1e-6 < py < max(y1, y2) - 1e-6:
                    hit = (px, py)
                    break
                if abs(y1 - y2) < 1e-6 and abs(py - y1) < 1e-6 and min(x1, x2) + 1e-6 < px < max(x1, x2) - 1e-6:
                    hit = (px, py)
                    break
            if hit:
                out.append((x1, y1, hit[0], hit[1]))
                out.append((hit[0], hit[1], x2, y2))
                changed = True
            else:
                out.append((x1, y1, x2, y2))
        sh.wires = out


def auto_junctions(sh):
    """add junction dots where 3 or more wire/pin ends meet or a wire end lands on another wire"""
    from collections import defaultdict
    split_wires_at_pins(sh)
    pts = defaultdict(int)
    segs = sh.wires
    for (x1, y1, x2, y2) in segs:
        pts[(x1, y1)] += 1
        pts[(x2, y2)] += 1
    for i in sh.insts:
        if i.sym.power:
            continue
        for p in i.pins():
            pos = i.pin_pos(p.number)
            if pos in pts:
                pts[pos] += 1
    for (px, py), n in list(pts.items()):
        # a wire end lying in the interior of another wire counts as a T
        for (x1, y1, x2, y2) in segs:
            if (x1, y1) == (px, py) or (x2, y2) == (px, py):
                continue
            if abs(x1 - x2) < 1e-6 and abs(px - x1) < 1e-6 and min(y1, y2) < py < max(y1, y2):
                n += 2
            elif abs(y1 - y2) < 1e-6 and abs(py - y1) < 1e-6 and min(x1, x2) < px < max(x1, x2):
                n += 2
        if n >= 3:
            sh.junction(px, py)


def sheet_frame(sh, block, title, notes):
    sh.text(title, 12.7, 14, 3.0, True)
    y = 19
    for n in notes:
        sh.text(n, 12.7, y, 1.5)
        y += 3.2


# ================================================================== BASE
def build_base(root_uuid):
    sh = Sheet("base_mcu", "Base: ESP32-S3 dev-board socket, buses, expansion, star point", "A3", 2,
               "Jinhua #40729 (ESP32-S3-DevKitC-1 pin order) in two 1x22 sockets")
    c = Ctx(sh, "BASE", 0)
    sheet_frame(sh, "BASE", "BASE — ESP32-S3 dev-board socket, I2C, expansion header, star point", [
        "Dev board: Jinhua #40729, ESP32-S3-DevKitC-1 v1.1 pin order (Espressif user guide). 3V3 pins NOT connected (dev board LDO must not fight the carrier's AMS1117).",
        "Strapping pins IO0/IO45/IO46 left open; IO3 is unused as well (v0.7: it was DIO8 — the strapping question is closed by not using it). IO35-37 (octal PSRAM) and IO48 (on-board WS2812) unused.",
        "GPIO map v0.7 (re-spec 8.2, interface contract): IO41 DDS_FSYNC, IO42 DDS_PSEL, IO40 TX_EN, IO8 RX_BLANK, IO9/IO14 HB_IN1/HB_IN2, IO47 FET_GATE. DIO1-8 and RELAY1-4 moved to the TCA9535 I2C expander (B5), which frees IO4/6/7/15 to the expansion header.",
        "I2C addresses: TCA9535 GPIO expander 0x20 (A0 = A1 = A2 = GND, B5), Si5351A clock generator 0x60, OLED 0x3C. 400 kHz, 4.7 k pull-ups here, 2 Qwiic ports for anything else.",
        "Socket row spacing 25.4 mm ASSUMED from the 28 mm-wide clone (HANDOVER 2026-09-05) — MEASURE a #40729 before ordering (docs/design-decisions.md D-12).",
        "SPI2 on IO_MUX pins: 33 R series at the source on SCLK/MOSI (here) and on SDO at the ADC (B1). All inter-sheet signals are global labels; rails are power symbols.",
    ])
    # ---------------- dev-board sockets -------------------------------------------------
    J1 = c.place("J1", "DEVKIT_SOCKET_J1", 120, 120, 0, value="DevKit J1 (left row)")
    J2 = c.place("J2", "DEVKIT_SOCKET_J3", 190, 120, 0, value="DevKit J3 (right row)")
    sh.box(129, 88, 181, 152, None)
    sh.text("ESP32-S3-DevKitC-1 / Jinhua #40729 (plugged in, USB-C ports face the rear/power edge)", 130, 92, 1.4)
    sh.text("antenna u.FL -> pigtail -> rear SMA bulkhead", 130, 95.5, 1.4)
    # GPIO map v0.7 (re-spec 8.2): the DIO/RELAY pins are freed; IO4/6/7/15 go to the expansion header, IO3 stays unused
    j1nets = {1: None, 2: None, 3: "RST", 4: "GPIO4", 5: "CS_DAC", 6: "GPIO6", 7: "GPIO7", 8: "GPIO15", 9: "OPTO_IN1", 10: "OPTO_IN2",
              11: "FAST_OUT1", 12: "RX_BLANK", 13: None, 14: None, 15: "HB_IN1", 16: "CS_ADC", 17: "MOSI_MCU", 18: "SCLK_MCU", 19: "SPI_MISO", 20: "HB_IN2",
              21: "+5V_RAW", 22: "GND"}
    j3nets = {1: "GND", 2: "GPIO43", 3: "GPIO44", 4: "I2C_SDA", 5: "I2C_SCL", 6: "DDS_PSEL", 7: "DDS_FSYNC", 8: "TX_EN", 9: "TRIG_DIR", 10: "TRIG_IO",
              11: None, 12: None, 13: None, 14: None, 15: None, 16: None, 17: "FET_GATE", 18: "FAST_OUT2", 19: "USB_DP", 20: "USB_DN", 21: "GND", 22: "GND"}
    for pin, net in j1nets.items():
        if net is None:
            c.nc_pin(J1, pin)
        elif net in ("+5V_RAW", "GND"):
            c.pwr_pin(J1, pin, net, 7.62 if net == "GND" else 12.7)
        elif net in ("MOSI_MCU", "SCLK_MCU", "RST"):
            c.label_pin(J1, pin, net, 5.08)
        else:
            c.glabel_pin(J1, pin, net, 5.08)
    for pin, net in j3nets.items():
        if net is None:
            c.nc_pin(J2, pin)
        elif net == "GND":
            c.pwr_pin(J2, pin, net, 5.08 if pin == 21 else 12.7)
        else:
            c.glabel_pin(J2, pin, net, 5.08)
    sh.text("IO0, IO45, IO46 = strapping (open); IO3 unused (v0.7)", 200, 156, 1.2)
    sh.text("IO35-37 = octal PSRAM, IO48 = on-board RGB LED", 200, 159, 1.2)
    # ---------------- GPIO map v0.7 (the interface contract lives on this sheet) ----------------
    gpio07 = [["GPIO", "Net", "Function", "Block"],
              ["12 / 11 / 13", "SPI_SCLK/MOSI/MISO", "SPI2 on IO_MUX, 33 R at source", "base"],
              ["10 / 5", "CS_ADC / CS_DAC", "ADS8688 /CS; DAC8563 /SYNC", "B1 / B3"],
              ["1 / 2", "I2C_SDA / I2C_SCL", "400 kHz: 0x20, 0x60, 0x3C", "base"],
              ["16 / 17", "OPTO_IN1 / 2", "6N137 outputs, active LOW", "B4"],
              ["18 / 21", "FAST_OUT1 / 2", "74HCT125 -> 49.9 R -> terminals", "B5"],
              ["38 / 39", "TRIG_IO / TRIG_DIR", "74LVC1T45 (1 = out to the SMA)", "B5"],
              ["41 / 42", "DDS_FSYNC / DDS_PSEL", "AD9834 sync / phase select", "NMR TX"],
              ["40 / 47", "TX_EN / FET_GATE", "OPA564 enable; polarizer FET", "TX / B4"],
              ["8", "RX_BLANK", "receiver blanking switch", "NMR RX"],
              ["9 / 14", "HB_IN1 / HB_IN2", "DRV8871 field-cycling bridge", "B4"],
              ["4 / 6 / 7 / 15", "GPIO4/6/7/15", "freed -> expansion header J5", "base"],
              ["43 / 44", "GPIO43 / GPIO44", "LED_WIFI/ACT via JP1/JP2; hdr", "base"],
              ["expander", "DIO1-8, RLY_IN1-4", "P00-P07 -> 541; P10-P13 relays", "B5 / B4"],
              ["0/45/46, 3, 48", "-", "strapping / unused / PSRAM 35-37", "-"]]
    sh.text("GPIO map v0.7 (re-spec 8.2) — interface contract", 14, 42, 1.5, True)
    sh.table(14, 44, gpio07, [20, 28, 48, 12], 1.2)
    # SPI source series resistors (33 R): SCLK_MCU -> R1 -> SPI_SCLK, MOSI_MCU -> R2 -> SPI_MOSI
    for k, (ref, net_in, net_out, y) in enumerate([("R1", "SCLK_MCU", "SPI_SCLK", 175), ("R2", "MOSI_MCU", "SPI_MOSI", 185)]):
        r = c.place(ref, "R0603_33", 60, y, 90)
        e1 = sh.stub(r, 1, 3.81)
        sh.label(net_in, e1[0], e1[1], 180)
        e2 = sh.stub(r, 2, 3.81)
        sh.label(net_out, e2[0], e2[1], 0, "global")
    sh.text("33 R source termination for the 80 MHz-capable SPI2 lines (practices 14)", 40, 195, 1.2)
    # RST test point
    tp = c.place("TP1", "TestPoint", 60, 160, 90)
    e = sh.stub(tp, 1, 3.81)
    sh.label("RST", e[0], e[1], 180)
    # ---------------- I2C pull-ups ------------------------------------------------------
    for k, (ref, net) in enumerate([("R3", "I2C_SDA"), ("R4", "I2C_SCL")]):
        r = c.place(ref, "R0603_4R7k", 250 + k * 12.7, 60, 0)
        c.pwr_pin(r, 1, "+3V3", 2.54)
        e = sh.stub(r, 2, 3.81)
        sh.label(net, e[0], e[1], 270, "global")
    sh.text("I2C 400 kHz pull-ups (OLED 0x3C + 2 Qwiic ports)", 240, 45, 1.2)
    # ---------------- Qwiic connectors ----------------------------------------------------
    for k, ref in enumerate(["J3", "J4"]):
        j = c.place(ref, "QWIIC_SM04B-SRSS", 250, 90 + k * 30, 0)
        c.pwr_pin(j, 1, "GND")
        c.pwr_pin(j, 2, "+3V3")
        c.glabel_pin(j, 3, "I2C_SDA")
        c.glabel_pin(j, 4, "I2C_SCL")
        c.pwr_pin(j, 5, "GND")
        c.pwr_pin(j, 6, "GND")
    # ---------------- expansion header J5 (2x10) -------------------------------------------
    J5 = c.place("J5", "HDR_2x10_MALE", 330, 110, 0)
    # D-17 v0.7: pins 16/17 (AUX_HDR, COND_OUT2 — the OPT chain is replaced by the NMR receiver) and the two
    # spares 19/20 now carry the four GPIO freed by the expander.
    exp = {1: "+3V3", 2: "+5V_RAW", 3: "+12V", 4: "-12V", 5: "GND", 6: "GND", 7: "SPI_SCLK", 8: "SPI_MOSI", 9: "SPI_MISO", 10: "GND",
           11: "I2C_SDA", 12: "I2C_SCL", 13: "TRIG_IO", 14: "GPIO43", 15: "GPIO44", 16: "GPIO4", 17: "GPIO6", 18: "AGND", 19: "GPIO7", 20: "GPIO15"}
    for pin, net in exp.items():
        if net is None:
            c.nc_pin(J5, pin)
        elif net in ("+3V3", "+5V_RAW", "+12V", "-12V", "GND", "AGND"):
            c.pwr_pin(J5, pin, net, {1: 12.7, 2: 12.7, 3: 7.62, 4: 7.62, 5: 17.78, 6: 17.78, 10: 12.7, 18: 12.7}[pin])
        else:
            c.glabel_pin(J5, pin, net, 7.62)
    exp_rows = [["Pins", "Signals (D-17, v0.7)"],
                ["1-6", "+3V3  +5V_RAW  +12V  -12V  GND  GND"],
                ["7-12", "SPI_SCLK  SPI_MOSI  SPI_MISO  GND  I2C_SDA  I2C_SCL"],
                ["13-18", "TRIG_IO  GPIO43  GPIO44  GPIO4  GPIO6  AGND"],
                ["19-20", "GPIO7  GPIO15"]]
    sh.table(287, 140, exp_rows, [14, 92], 1.3)
    sh.text("Expansion header J5 (2x10), pinout D-17 v0.7: the four GPIO freed by the expander (4/6/7/15) took pins 16/17/19/20", 287, 138, 1.2)
    # ---------------- panel LED links ----------------------------------------------------
    for k, (ref, a, b) in enumerate([("JP1", "GPIO43", "LED_WIFI"), ("JP2", "GPIO44", "LED_ACT")]):
        jp = c.place(ref, "SolderJumper_2_Bridged", 250, 170 + k * 12.7, 0)
        e = sh.stub(jp, 1, 3.81)
        sh.label(a, e[0], e[1], 180, "global")
        e = sh.stub(jp, 2, 3.81)
        sh.label(b, e[0], e[1], 0, "global")
    sh.text("Panel LED drive: bridged by default; open JP1 when the OPT chain uses GPIO43 as CS, JP2 when the TCXO option feeds GPIO44", 215, 195, 1.2)
    # ---------------- star point -----------------------------------------------------------
    nt = c.place("NT1", "NetTie_2", 330, 190, 0)
    c.pwr_pin(nt, 1, "AGND", 7.62)
    c.pwr_pin(nt, 2, "GND", 7.62)
    sh.text("The ONLY AGND-GND join (net tie NT1, copper only). Placed at the B1/BASE boundary.", 300, 205, 1.3, True)
    # power flags for the grounds (no power_out pin drives GND/AGND)
    f1 = c.flag(370, 60)
    c.power_at(370, 60, "GND")
    f2 = c.flag(385, 60)
    c.power_at(385, 60, "AGND")
    sh.text("PWR_FLAGs: GND and AGND are references without a power_out driver", 355, 52, 1.2)
    # ---------------- mechanical --------------------------------------------------------------
    for k in range(4):
        c.place("H%d" % (k + 1), "MountingHole", 40 + k * 12.7, 230, 0)
    for k in range(3):
        c.place("FID%d" % (k + 1), "Fiducial", 100 + k * 12.7, 230, 0)
    sh.text("4 x M3 mounting holes (4 mm from the corners) and 3 assembly fiducials", 40, 240, 1.2)
    # test points
    for k, (ref, net) in enumerate([("TP2", "GND"), ("TP3", "+3V3"), ("TP4", "+5V_RAW")]):
        tp = c.place(ref, "TestPoint", 150 + k * 15, 230, 0)
        c.pwr_pin(tp, 1, net, 2.54)
    auto_junctions(sh)
    return sh


# ================================================================== B2 POWER
def build_b2(root_uuid):
    sh = Sheet("b2_power", "B2: power entry, ORing, isolated +-12 V, LDOs", "A3", 3, "USB-C / 5 V jack -> LM66100 ORing -> +5V_RAW; 2x B0512S-2WR3 -> +-12 V; 78L05 -> +5VA; AMS1117 -> +3V3")
    c = Ctx(sh, "B2", 1000)
    sheet_frame(sh, "B2", "B2 — POWER: USB-C / 5 V jack entry, ideal-diode ORing, +-12 V isolated modules, +5VA and +3V3 LDOs", [
        "Entry: 1.5 A polyfuse -> SMF5.0A TVS -> LM66100 ideal diode per input (CE = GND, always on; the higher source wins, reverse current blocked). Drop ~0.18 V typ at 1.2 A vs 0.5 V for the Schottky ORing (D-02).",
        "+-12 V: two unregulated B0512S-2WR3 (10 % minimum load rule!): +12 V rail loaded by 78L05 + bleeder, -12 V rail by OPA2192 + 3 x 2.2k bleeder (16 mA) so both stay inside the +-15 % envelope (datasheet p.3/4).",
        "78L05G (SOT-89, 350 mW max): +12 V -> +5VA for ADS8688/DAC8563 AVDD; ~17 mA -> 0.12 W. AMS1117-3.3: 22 uF output required for stability (datasheet 'Stability'); ceramic used, tantalum drop-in (3216) if the rail rings.",
        "All power-module outputs are referenced to AGND (-12 V module: +Vo = AGND). GND and AGND meet only at NT1 (base sheet).",
    ])
    # ---------------- USB-C ----------------------------------------------------------------
    J = c.place("J201", "USB-C-16P-2MD-073", 40, 80, 0)
    # VBUS pins tied together -> F201
    vb1 = sh.stub(J, "A4B9", 5.08)
    vb2 = sh.stub(J, "B4A9", 5.08)
    sh.wire(vb1[0], vb1[1], vb2[0], vb2[1])
    F1 = c.place("F201", "FUSE_1812L150", 70, vb1[1], 90)
    sh.wire(vb1[0], vb1[1], F1.pin_pos(1)[0], F1.pin_pos(1)[1])
    # TVS + input cap after the fuse
    n1 = F1.pin_pos(2)
    D1 = c.place("D201", "SMF5.0A", 85, n1[1] + 12.7, 90)     # K up (pin1 at top), A down -> GND
    C3 = c.place("C203", "C0805_10uF", 95, n1[1] + 12.7, 0)
    sh.wire(n1[0], n1[1], 105, n1[1])
    sh.wire(D1.pin_pos(1)[0], D1.pin_pos(1)[1], D1.pin_pos(1)[0], n1[1])
    sh.wire(C3.pin_pos(1)[0], C3.pin_pos(1)[1], C3.pin_pos(1)[0], n1[1])
    c.pwr_pin(D1, 2, "GND")
    c.pwr_pin(C3, 2, "GND")
    U1 = c.place("U201", "LM66100DCKR", 120, n1[1] + 2.54, 0)
    vin = U1.pin_pos(1)
    sh.wire(105, n1[1], 105, vin[1])
    sh.wire(105, vin[1], vin[0], vin[1])
    c.pwr_pin(U1, 3, "GND", 2.54)   # CE low = enabled
    c.pwr_pin(U1, 2, "GND")
    c.pwr_pin(U1, 5, "GND", 2.54)   # ST not used -> GND per datasheet
    c.nc_pin(U1, 4)
    out1 = sh.stub(U1, 6, 5.08)
    c.power_at(out1[0], out1[1], "+5V_RAW")
    # CC pull-downs (5.1 k = UFP sink): stubs of different length, resistors hang below
    for k, (ref, pin) in enumerate([("R201", "A5"), ("R202", "B5")]):
        e = sh.stub(J, pin, 7.62 + k * 7.62)
        r = c.place(ref, "R0603_5R1k", e[0], e[1] + 8.89, 0)
        sh.wire(e[0], e[1], r.pin_pos(1)[0], r.pin_pos(1)[1])
        c.pwr_pin(r, 2, "GND")
    # D+/D- pairs
    for pins, net in ((("A6", "B6"), "USB_DP"), (("A7", "B7"), "USB_DN")):
        e1 = sh.stub(J, pins[0], 5.08)
        e2 = sh.stub(J, pins[1], 5.08)
        sh.wire(e1[0], e1[1], e2[0], e2[1])
        sh.label(net, e2[0] + 0.0, e2[1], 0, "global")
    c.nc_pin(J, "A8")
    c.nc_pin(J, "B8")
    for pin, ln in (("13", 5.08), ("14", 10.16), ("A1B12", 15.24), ("B1A12", 20.32)):
        c.pwr_pin(J, pin, "GND", ln)
    sh.text("CC1/CC2 5.1k = UFP sink, 5 V. Shield pads to GND directly (no chassis).", 30, 125, 1.2)
    # ---------------- DC jack ----------------------------------------------------------------
    J2 = c.place("J202", "DC005-T20", 40, 160, 0)
    tip = sh.stub(J2, 1, 5.08)
    F2 = c.place("F202", "FUSE_1812L150", 70, tip[1], 90)
    sh.wire(tip[0], tip[1], F2.pin_pos(1)[0], F2.pin_pos(1)[1])
    n2 = F2.pin_pos(2)
    D2 = c.place("D202", "SMF5.0A", 85, n2[1] + 12.7, 90)
    C4 = c.place("C204", "C0805_10uF", 95, n2[1] + 12.7, 0)
    sh.wire(n2[0], n2[1], 105, n2[1])
    sh.wire(D2.pin_pos(1)[0], D2.pin_pos(1)[1], D2.pin_pos(1)[0], n2[1])
    sh.wire(C4.pin_pos(1)[0], C4.pin_pos(1)[1], C4.pin_pos(1)[0], n2[1])
    c.pwr_pin(D2, 2, "GND")
    c.pwr_pin(C4, 2, "GND")
    U2 = c.place("U202", "LM66100DCKR", 120, n2[1] + 2.54, 0)
    vin2 = U2.pin_pos(1)
    sh.wire(105, n2[1], 105, vin2[1])
    sh.wire(105, vin2[1], vin2[0], vin2[1])
    c.pwr_pin(U2, 3, "GND", 2.54)
    c.pwr_pin(U2, 2, "GND")
    c.pwr_pin(U2, 5, "GND", 2.54)
    c.nc_pin(U2, 4)
    out2 = sh.stub(U2, 6, 5.08)
    c.power_at(out2[0], out2[1], "+5V_RAW")
    c.pwr_pin(J2, 2, "GND", 5.08)
    c.nc_pin(J2, 3)
    sh.text("Jack: 5 V DC, centre +, 5.5/2.1 mm, 1.5-3 A. Switch pin unused.", 30, 190, 1.2)
    # ---------------- ORed node -> +5V_RAW with bulk caps + LED ---------------------------------
    x0 = 170
    sh.wire(x0, 100, x0 + 25.4, 100)
    c.power_at(x0 + 25.4, 100, "+5V_RAW")
    c.flag(x0, 100)
    C1 = c.place("C201", "C1206_22uF", x0 + 5.08, 110, 0)
    C2 = c.place("C202", "C0603_100nF", x0 + 15.24, 110, 0)
    for cap in (C1, C2):
        t = cap.pin_pos(1)
        sh.wire(t[0], t[1], t[0], 100)
        c.pwr_pin(cap, 2, "GND")
    R9 = c.place("R209", "R0603_1k", x0 + 35, 112, 0)
    sh.wire(R9.pin_pos(1)[0], R9.pin_pos(1)[1], R9.pin_pos(1)[0], 100)
    sh.wire(x0 + 25.4, 100, R9.pin_pos(1)[0], 100)
    Dl = c.place("D203", "LED_GREEN_0805", x0 + 35, 125, 90)   # A at top? pin2 A at (3.81,0) -> rot 90 -> A up
    sh.wire(R9.pin_pos(2)[0], R9.pin_pos(2)[1], Dl.pin_pos(2)[0], Dl.pin_pos(2)[1])
    c.pwr_pin(Dl, 1, "GND")
    sh.text("+5V_RAW rail (both LM66100 outputs): bulk 22 uF + 100 nF, green LED (2.9 mA); PWR_FLAG = ideal diodes drive the rail", 160, 92, 1.2)
    # ---------------- +3V3 LDO ----------------------------------------------------------------
    U4 = c.place("U204", "AMS1117-3.3", 240, 105, 0)
    vin = c.pwr_pin(U4, 3, "+5V_RAW", 7.62)
    C13 = c.place("C213", "C0805_10uF", vin[0] + 2.54, vin[1] + 10.16, 0)
    sh.wire(vin[0] + 2.54, vin[1], C13.pin_pos(1)[0], C13.pin_pos(1)[1])
    c.pwr_pin(C13, 2, "GND")
    c.pwr_pin(U4, 1, "GND")
    c.nc_pin(U4, 4)   # tab duplicate of VOUT: connected on the PCB by the footprint (pads 2 and 4 same net via pad numbering)
    vo = sh.stub(U4, 2, 7.62)
    c.power_at(vo[0], vo[1], "+3V3")
    C14 = c.place("C214", "C1206_22uF", vo[0] - 5.08, vo[1] + 10.16, 0)
    C15 = c.place("C215", "C0603_100nF", vo[0] + 5.08, vo[1] + 10.16, 0)
    for cap in (C14, C15):
        t = cap.pin_pos(1)
        sh.wire(t[0], t[1], t[0], vo[1])
        c.pwr_pin(cap, 2, "GND")
    sh.wire(vo[0] - 5.08, vo[1], vo[0] + 5.08, vo[1])
    R10 = c.place("R210", "R0603_1k", vo[0] + 15.24, vo[1] + 12, 0)
    sh.wire(R10.pin_pos(1)[0], R10.pin_pos(1)[1], R10.pin_pos(1)[0], vo[1])
    sh.wire(vo[0] + 5.08, vo[1], R10.pin_pos(1)[0], vo[1])
    D4 = c.place("D204", "LED_GREEN_0805", R10.pin_pos(2)[0], vo[1] + 25, 90)
    sh.wire(R10.pin_pos(2)[0], R10.pin_pos(2)[1], D4.pin_pos(2)[0], D4.pin_pos(2)[1])
    c.pwr_pin(D4, 1, "GND")
    sh.text("+3V3: AMS1117-3.3 (SOT-223), 22 uF ceramic out (tantalum 3216 drop-in if needed), pin 4 = tab (same VOUT net on the footprint)", 200, 145, 1.2)
    # ---------------- isolated modules ---------------------------------------------------------
    for k, (ref, sign) in enumerate([("PS201", "+"), ("PS202", "-")]):
        yb = 165 + k * 78
        ps = c.place(ref, "B0512S-2WR3", 240, yb, 0)
        fb = c.place("FB20%d" % (1 + k), "FB0603_600R", 210, ps.pin_pos(1)[1], 90)
        c.pwr_pin(fb, 1, "+5V_RAW", 5.08)
        sh.wire(fb.pin_pos(2)[0], fb.pin_pos(2)[1], ps.pin_pos(1)[0], ps.pin_pos(1)[1])
        cin = c.place("C21%d" % (6 + k), "C0805_10uF", 226, yb + 8, 0)
        sh.wire(cin.pin_pos(1)[0], cin.pin_pos(1)[1], cin.pin_pos(1)[0], ps.pin_pos(1)[1])
        c.flag(217.17, ps.pin_pos(1)[1], 180)   # filtered input node: flag as driven (drawn below the line)
        c.pwr_pin(cin, 2, "GND")
        c.pwr_pin(ps, 2, "GND", 5.08)
        if sign == "+":
            fbo = c.place("FB203", "FB0603_600R", 275, ps.pin_pos(6)[1], 0)   # horizontal: pin1 left? rot 0 -> pin1 at top; use rot 90
            fbo.rot = 90
            sh.wire(ps.pin_pos(6)[0], ps.pin_pos(6)[1], fbo.pin_pos(1)[0], fbo.pin_pos(1)[1])
            node = fbo.pin_pos(2)
            sh.wire(node[0], node[1], node[0] + 30.48, node[1])
            c.power_at(node[0] + 30.48, node[1], "+12V")
            c.flag(node[0] + 2.54, node[1])
            co1 = c.place("C207", "C1206_22uF", node[0] + 5.08, node[1] + 8.89, 0)
            co2 = c.place("C209", "C0603_100nF", node[0] + 12.7, node[1] + 8.89, 0)
            for cap in (co1, co2):
                t = cap.pin_pos(1)
                sh.wire(t[0], t[1], t[0], node[1])
                c.pwr_pin(cap, 2, "AGND")
            # -Vo -> AGND
            c.pwr_pin(ps, 4, "AGND", 5.08)
            # bleeder 3x 2.2k
            for i in range(3):
                r = c.place("R20%d" % (3 + i), "R0603_2R2k", node[0] + 20.32 + i * 5.08, node[1] + 8.89, 0)
                sh.wire(r.pin_pos(1)[0], r.pin_pos(1)[1], r.pin_pos(1)[0], node[1])
                c.pwr_pin(r, 2, "AGND")
            # LED +12 via 4.7k
            rl = c.place("R211", "R0603_4R7k", node[0] + 40.64, node[1] + 8.89, 0)
            sh.wire(rl.pin_pos(1)[0], rl.pin_pos(1)[1], rl.pin_pos(1)[0], node[1])
            sh.wire(node[0] + 30.48, node[1], rl.pin_pos(1)[0], node[1])
            dl = c.place("D205", "LED_GREEN_0805", rl.pin_pos(2)[0], node[1] + 21, 90)
            sh.wire(rl.pin_pos(2)[0], rl.pin_pos(2)[1], dl.pin_pos(2)[0], dl.pin_pos(2)[1])
            c.pwr_pin(dl, 1, "AGND")
            sh.text("+12V: FB + 22 uF + 100 nF at the module; 3 x 2.2k = 16 mA bleeder guarantees the 10 % minimum load with 78L05 load included", node[0] - 40, yb + 34, 1.2)
        else:
            # +Vo -> AGND ; -Vo -> FB -> -12V
            c.pwr_pin(ps, 6, "AGND", 5.08)
            fbo = c.place("FB204", "FB0603_600R", 275, ps.pin_pos(4)[1], 90)
            sh.wire(ps.pin_pos(4)[0], ps.pin_pos(4)[1], fbo.pin_pos(1)[0], fbo.pin_pos(1)[1])
            node = fbo.pin_pos(2)
            sh.wire(node[0], node[1], node[0] + 30.48, node[1])
            c.power_at(node[0] + 30.48, node[1], "-12V")
            c.flag(node[0] + 2.54, node[1])
            co1 = c.place("C206", "C1206_22uF", node[0] + 5.08, node[1] - 8.89, 180)   # pin2 up to AGND? rot180: pin1 at bottom
            co2 = c.place("C208", "C0603_100nF", node[0] + 12.7, node[1] - 8.89, 180)
            for cap in (co1, co2):
                t = cap.pin_pos(1)     # pin 1 now at the bottom -> -12V node
                sh.wire(t[0], t[1], t[0], node[1])
                c.pwr_pin(cap, 2, "AGND")
            for i in range(3):
                r = c.place("R20%d" % (6 + i), "R0603_2R2k", node[0] + 20.32 + i * 5.08, node[1] - 8.89, 180)
                sh.wire(r.pin_pos(1)[0], r.pin_pos(1)[1], r.pin_pos(1)[0], node[1])
                c.pwr_pin(r, 2, "AGND")
            rl = c.place("R212", "R0603_4R7k", node[0] + 40.64, node[1] - 8.89, 180)
            sh.wire(rl.pin_pos(1)[0], rl.pin_pos(1)[1], rl.pin_pos(1)[0], node[1])
            sh.wire(node[0] + 30.48, node[1], rl.pin_pos(1)[0], node[1])
            dl = c.place("D206", "LED_GREEN_0805", rl.pin_pos(2)[0], node[1] - 21, 90)   # K down toward -12V side, A up to AGND
            sh.wire(rl.pin_pos(2)[0], rl.pin_pos(2)[1], dl.pin_pos(1)[0], dl.pin_pos(1)[1])
            c.pwr_pin(dl, 2, "AGND")
            sh.text("-12V: module #2 with +Vo on AGND; FB in the -Vo line; 3 x 2.2k bleeder (16 mA) + LED keep the 10 % minimum load without the OPT chain", node[0] - 40, yb + 22, 1.2)
    sh.text("Isolated 2 W modules: input 4.5-5.5 V, 454 mA full load, ripple 80 mVp-p max, Cout <= 560 uF, 1.5 kVDC isolation (YLPTEC datasheet)", 200, 152, 1.2)
    # ---------------- +5VA LDO ------------------------------------------------------------------
    U3 = c.place("U203", "78L05G-AB3-R", 350, 105, 0)
    vin = c.pwr_pin(U3, 3, "+12V", 7.62)
    C10 = c.place("C210", "C0603_1uF", vin[0] + 2.54, vin[1] + 10.16, 0)
    sh.wire(vin[0] + 2.54, vin[1], C10.pin_pos(1)[0], C10.pin_pos(1)[1])
    c.pwr_pin(C10, 2, "AGND")
    c.pwr_pin(U3, 2, "AGND")
    vo = sh.stub(U3, 1, 7.62)
    c.power_at(vo[0], vo[1], "+5VA")
    C11 = c.place("C211", "C0805_10uF", vo[0] - 5.08, vo[1] + 10.16, 0)
    C12 = c.place("C212", "C0603_100nF", vo[0] + 5.08, vo[1] + 10.16, 0)
    for cap in (C11, C12):
        t = cap.pin_pos(1)
        sh.wire(t[0], t[1], t[0], vo[1])
        c.pwr_pin(cap, 2, "AGND")
    sh.wire(vo[0] - 5.08, vo[1], vo[0] + 5.08, vo[1])
    sh.text("+5VA: 78L05G from +12V (dropout 1.7 V), ADC/DAC analog supply, AGND-referenced; 0.12 W at 17 mA", 300, 138, 1.2)
    # ---------------- test points ---------------------------------------------------------------
    for k, (ref, net) in enumerate([("TP201", "+5V_RAW"), ("TP202", "+3V3"), ("TP203", "+12V"), ("TP204", "-12V"), ("TP205", "+5VA"), ("TP206", "AGND")]):
        tp = c.place(ref, "TestPoint", 40 + k * 15, 240, 0)
        c.pwr_pin(tp, 1, net, 2.54)
    sh.text("Rail test points", 40, 252, 1.2)
    auto_junctions(sh)
    return sh


# ================================================================== B1 INPUTS
def build_b1(root_uuid):
    sh = Sheet("b1_inputs", "B1: eight +-10 V inputs, ADS8688", "A3", 4, "AI1..AI8 -> 1k / 1nF / BAV99 clamp -> ADS8688 AIN_0..7; ch 7/8 solder jumpers to the OPT chain")
    c = Ctx(sh, "B1", 2000)
    sheet_frame(sh, "B1", "B1 — PRECISION INPUTS: 8 x (1 k / 1 nF / BAV99 clamp) -> ADS8688 16-bit SAR ADC", [
        "Input network per channel: 1 k series (limits clamp current to 36 mA at +-50 V), 1 nF to AGND (f-3dB ~160 kHz), BAV99 clamps to the +-12 V rails. ADC input +-10.24 V range, 1 MOhm input impedance, abs max +-20 V.",
        "ADS8688 decoupling per datasheet 11.1: AVDD 1 uF at each pin + 10 uF; REFCAP 1 uF + 22 uF (min 10 uF) direct at pins; REFIO 10 uF (internal 4.096 V ref, REFSEL low); DVDD 10 uF + 100 nF. DAISY = GND, RST/PD pulled to DVDD.",
        "Channel mapping (firmware table, D-19): AI1->AIN_6, AI2->AIN_7, AI3->AIN_0, AI4->AIN_1, AI5->AIN_2, AI6->AIN_3, AI7->AIN_4, AI8->AIN_5 (package order = planar fan-in from the link, no crossings). AI7/AI8 switch to the OPT chain with JP101/JP102 (default: SMA path).",
        "AGND = analog reference copper (L1/L4 pours), joined to GND only at NT1 (base). SDO has a 33 R source resistor.",
    ])
    U = c.place("U101", "ADS8688IDBTR", 260, 130, 0)
    # AI1..AI8 -> ADC channels 6,7,0,1,2,3,4,5 (package order: planar fan-in from the link, design-decisions D-19)
    chan_pins = ["12", "14", "16", "18", "21", "23", "25", "27"]
    gnd_pins = ["13", "15", "17", "19", "20", "22", "24", "26"]
    # 8 input networks, one row each (17.78 mm pitch), connected to the ADC by local labels AIN1..AIN8
    for i in range(8):
        y = 55 + i * 17.78
        x_lab = 40
        if i >= 6:
            jp = c.place("JP10%d" % (i - 5), "SolderJumper_3_Bridged12", x_lab + 15.24, y - 3.81, 0)
            e = sh.stub(jp, 1, 5.08)
            sh.label("AI%d" % (i + 1), e[0], e[1], 180, "global")
            e = sh.stub(jp, 3, 3.81)
            sh.label("COND_OUT%d" % (i - 5), e[0], e[1], 0, "global")
            cpin = jp.pin_pos(2)
            xr = cpin[0] + 12.7
            sh.wire(cpin[0], cpin[1], cpin[0], y)
            sh.wire(cpin[0], y, xr - 3.81, y)
        else:
            sh.label("AI%d" % (i + 1), x_lab, y, 180, "global")
            xr = x_lab + 30.48
            sh.wire(x_lab, y, xr - 3.81, y)
        r = c.place("R1%02d" % (11 + i), "R0603_1k", xr, y, 90)
        node = r.pin_pos(2)
        xend = node[0] + 50.8
        sh.wire(node[0], node[1], xend, y)
        sh.label("AIN%d" % (i + 1), xend, y, 0)
        cap = c.place("C1%02d" % (11 + i), "C0603_1nF", node[0] + 7.62, y + 6.35, 0)
        sh.wire(cap.pin_pos(1)[0], cap.pin_pos(1)[1], cap.pin_pos(1)[0], y)
        c.pwr_pin(cap, 2, "AGND")
        d = c.place("D1%02d" % (11 + i), "BAV99", node[0] + 30.48, y + 8.89, 180)   # COM up, A1 right (-12V), K2 left (+12V)
        sh.wire(d.pin_pos(3)[0], d.pin_pos(3)[1], d.pin_pos(3)[0], y)
        e = sh.stub(d, 1, 2.54)
        c.power_at(e[0], e[1], "-12V")
        e = sh.stub(d, 2, 2.54)
        c.power_at(e[0], e[1], "+12V")
    sh.text("8 identical input networks: 1 k -> node (1 nF to AGND, BAV99 clamps to the rails) -> AINn -> ADC channel per the D-19 table", 40, 200, 1.3)
    # ADC side: AINn labels on the channel pins, AGND on the channel ground pins
    for i in range(8):
        e = sh.stub(U, chan_pins[i], 10.16)
        sh.label("AIN%d" % (i + 1), e[0], e[1], 180)
        c.pwr_pin(U, gnd_pins[i], "AGND", 5.08)
    # AUX unused
    c.pwr_pin(U, "10", "AGND", 3.81)
    c.pwr_pin(U, "11", "AGND", 3.81)
    # reference pins
    refio = sh.stub(U, "5", 12.7)
    C6 = c.place("C106", "C0805_10uF", refio[0], refio[1] + 7.62, 0)
    sh.wire(refio[0], refio[1], C6.pin_pos(1)[0], C6.pin_pos(1)[1])
    c.pwr_pin(C6, 2, "AGND")
    refcap = sh.stub(U, "7", 25.4)
    C4 = c.place("C104", "C0603_1uF", refcap[0], refcap[1] + 7.62, 0)
    C5 = c.place("C105", "C1206_22uF", refcap[0] - 7.62, refcap[1] + 7.62, 0)
    sh.wire(refcap[0], refcap[1], C5.pin_pos(1)[0], refcap[1])
    for cap in (C4, C5):
        sh.wire(cap.pin_pos(1)[0], cap.pin_pos(1)[1], cap.pin_pos(1)[0], refcap[1])
        c.pwr_pin(cap, 2, "AGND")
    c.pwr_pin(U, "6", "AGND", 5.08)
    c.pwr_pin(U, "4", "AGND", 7.62)   # REFSEL low = internal reference
    sh.text("REFSEL low = internal 4.096 V reference; REFCAP 1 uF + 22 uF, REFIO 10 uF (ADS8688 datasheet 8.3.3 / 11.1)", 195, 215, 1.2)
    # supplies: 1 uF at each AVDD pin (drawn beside the pin), 10 uF bulk, DVDD 10 uF + 100 nF
    for pin, cref, dx in (("9", "C101", -20.32), ("30", "C103", -35.56)):
        e = U.pin_pos(pin)
        cap = c.place(cref, "C0603_1uF", e[0] + dx, e[1] - 12.7, 0)
        c.pwr_pin(cap, 1, "+5VA")
        c.pwr_pin(cap, 2, "AGND")
    e9 = U.pin_pos("9")
    c.pwr_pin(U, "9", "+5VA", 5.08)
    c.pwr_pin(U, "30", "+5VA", 12.7)
    C2 = c.place("C102", "C0805_10uF", e9[0] - 48.26, e9[1] - 12.7, 0)
    c.pwr_pin(C2, 1, "+5VA")
    c.pwr_pin(C2, 2, "AGND")
    e34 = sh.stub(U, "34", 20.32)
    c.power_at(e34[0], e34[1], "+3V3")
    C7 = c.place("C107", "C0805_10uF", e34[0] + 20.32, e34[1] - 7.62, 0)
    C8 = c.place("C108", "C0603_100nF", e34[0] + 33.02, e34[1] - 7.62, 0)
    for cap in (C7, C8):
        c.pwr_pin(cap, 1, "+3V3")
        c.pwr_pin(cap, 2, "GND")
    sh.text("AVDD 1 uF at pins 9 and 30 + 10 uF bulk; DVDD 10 uF + 100 nF", 200, 60, 1.2)
    # grounds
    for k, pin in enumerate(("8", "28", "29", "31", "32")):
        c.pwr_pin(U, pin, "AGND", 5.08 + (k % 3) * 6.35)
    c.pwr_pin(U, "33", "GND", 5.08 + 5 * 6.35 % 19.05)
    # digital side
    c.glabel_pin(U, "38", "CS_ADC", 7.62)
    c.glabel_pin(U, "37", "SPI_SCLK", 7.62)
    c.glabel_pin(U, "1", "SPI_MOSI", 7.62)
    e = sh.stub(U, "36", 3.81)
    R1 = c.place("R101", "R0603_33", e[0] + 3.81, e[1], 90)
    sh.wire(e[0], e[1], R1.pin_pos(1)[0], R1.pin_pos(1)[1])
    e2 = sh.stub(R1, 2, 2.54)
    sh.label("SPI_MISO", e2[0], e2[1], 0, "global")
    c.pwr_pin(U, "3", "GND", 20.32)   # DAISY
    e = sh.stub(U, "2", 12.7)
    sh.label("ADC_RST", e[0] - 5.08, e[1], 0)
    R2 = c.place("R102", "R0603_10k", e[0] + 5.08, e[1] - 7.62, 0)
    sh.wire(e[0], e[1], R2.pin_pos(2)[0], e[1])
    sh.wire(R2.pin_pos(2)[0], R2.pin_pos(2)[1], R2.pin_pos(2)[0], e[1])
    c.pwr_pin(R2, 1, "+3V3")
    c.nc_pin(U, "35")
    sh.text("RST/PD pulled up to DVDD (10k); firmware may pull it low for reset/power-down", 290, 150, 1.2)
    tp = c.place("TP101", "TestPoint", 360, 200, 0)
    c.pwr_pin(tp, 1, "AGND", 2.54)
    auto_junctions(sh)
    return sh


# ================================================================== B3 OUTPUTS
def build_b3(root_uuid):
    sh = Sheet("b3_outputs", "B3: DAC8563 + OPA2192 -> AO1/AO2 (+-10 V)", "A3", 5, "SPI level shift (74HCT125), DAC 0-5 V, difference amplifiers x4 around VREF 2.5 V, 49.9 R back-termination, BAV99 clamps")
    c = Ctx(sh, "B3", 3000)
    sheet_frame(sh, "B3", "B3 — SIGNAL GENERATION: DAC8563 (0-5 V, internal 2.5 V ref) -> OPA2192 difference amplifiers -> AO1/AO2 = +-10 V", [
        "DAC8563 logic thresholds are 0.7 x AVDD = 3.5 V at AVDD = 5 V, so a 74HCT125 (TTL-compatible inputs, 5 V outputs, tPD ~20 ns equal on all three lines) translates SCLK/DIN/SYNC (D-05).",
        "AO_n = 4 x (DAC_n - VREF): R1 = R3 = 10 k, R2 = R4 = 40.2 k (1 %, gain 4.02): 0..5 V in -> -10.05..+10.05 V out; offset/gain calibrated in firmware via AI loopback. VREF drives 2 x 10 k (0.5 mA of the +-20 mA capability).",
        "Output: 49.9 R back-termination, BAV99 clamps to +-12 V. OPA2192 short-circuit current +-65 mA: into a 50 R termination the swing is limited to ~+-6 V; full +-10 V into >= 1 k loads.",
        "Gain = 2 is the DAC default once the internal reference is enabled by firmware (reset default: reference off, gain 1). /LDAC = AGND (synchronous), /CLR pulled up to +5VA.",
    ])
    # level shifter
    U2 = c.place("U302", "74HCT125PW", 70, 110, 0)
    for pin, net in (("2", "SPI_SCLK"), ("5", "SPI_MOSI"), ("9", "CS_DAC")):
        c.glabel_pin(U2, pin, net, 7.62)
    for pin in ("1", "4", "10", "13", "12"):
        c.pwr_pin(U2, pin, "GND", 3.81)
    c.nc_pin(U2, "11")
    for pin, net in (("3", "DAC_SCLK"), ("6", "DAC_DIN"), ("8", "DAC_SYNC")):
        c.label_pin(U2, pin, net, 7.62)
    c.pwr_pin(U2, "14", "+5V_RAW", 3.81)
    c.pwr_pin(U2, "7", "GND", 3.81)
    C8 = c.place("C308", "C0603_100nF", 100, 70, 0)
    c.pwr_pin(C8, 1, "+5V_RAW")
    c.pwr_pin(C8, 2, "GND")
    sh.text("SPI -> 5 V level shift for the DAC (three channels, 4th input grounded)", 40, 150, 1.2)
    # DAC
    U1 = c.place("U301", "DAC8563SDGSR", 170, 110, 0)
    for pin, net in (("6", "DAC_SYNC"), ("7", "DAC_SCLK"), ("8", "DAC_DIN")):
        c.label_pin(U1, pin, net, 7.62)
    c.pwr_pin(U1, "4", "AGND", 5.08)
    e = sh.stub(U1, "5", 5.08)
    Rc = c.place("R311", "R0603_10k", e[0] - 5.08, e[1] + 7.62, 0)
    sh.wire(e[0], e[1], Rc.pin_pos(1)[0], e[1])
    sh.wire(Rc.pin_pos(1)[0], Rc.pin_pos(1)[1], Rc.pin_pos(1)[0], e[1])
    c.pwr_pin(Rc, 2, "+5VA")
    e = sh.stub(U1, "9", 5.08)
    c.power_at(e[0], e[1], "+5VA")
    C2 = c.place("C302", "C0603_100nF", 150, 75, 0)
    C3 = c.place("C303", "C0805_10uF", 160, 75, 0)
    for cap in (C2, C3):
        c.pwr_pin(cap, 1, "+5VA")
        c.pwr_pin(cap, 2, "AGND")
    c.pwr_pin(U1, "3", "AGND", 5.08)
    # VREF
    e = sh.stub(U1, "10", 7.62)
    sh.label("VREF_DAC", e[0], e[1], 0, "global")
    C1 = c.place("C301", "C0603_1uF", e[0] - 2.54, e[1] + 8.89, 0)
    sh.wire(C1.pin_pos(1)[0], C1.pin_pos(1)[1], C1.pin_pos(1)[0], e[1])
    c.pwr_pin(C1, 2, "AGND")
    sh.text("VREF 2.5 V out, 1 uF (>= 150 nF required by the datasheet)", 175, 135, 1.2)
    tp = c.place("TP301", "TestPoint", 215, 140, 0)
    e = sh.stub(tp, 1, 2.54)
    sh.label("VREF_DAC", e[0], e[1], 270, "global")
    # DAC outputs -> labels
    c.label_pin(U1, "1", "DAC_A", 7.62)
    c.label_pin(U1, "2", "DAC_B", 7.62)
    # op-amp stages
    U3a = c.place("U303", "OPA2192IDR", 300, 90, 0, unit=1)
    U3b = c.place("U303", "OPA2192IDR", 300, 160, 0, unit=2)
    U3p = c.place("U303", "OPA2192IDR", 370, 120, 0, unit=3)
    c.pwr_pin(U3p, "8", "+12V", 2.54)
    c.pwr_pin(U3p, "4", "-12V", 2.54)
    C4 = c.place("C304", "C0603_100nF", 392, 105, 0)
    C6 = c.place("C306", "C0805_10uF", 407, 105, 0)
    for cap in (C4, C6):
        c.pwr_pin(cap, 1, "+12V")
        c.pwr_pin(cap, 2, "AGND")
    C5 = c.place("C305", "C0603_100nF", 392, 140, 180)
    C7 = c.place("C307", "C0805_10uF", 407, 140, 180)
    for cap in (C5, C7):
        c.pwr_pin(cap, 1, "-12V")
        c.pwr_pin(cap, 2, "AGND")
    sh.text("OPA2192 supplies +-12 V, 100 nF + 10 uF each to AGND", 355, 160, 1.2)
    for ch, (u, dac, out_net, base) in enumerate([(U3a, "DAC_A", "AO1", 300), (U3b, "DAC_B", "AO2", 310)]):
        plus = u.pin_pos("3" if ch == 0 else "5")
        minus = u.pin_pos("2" if ch == 0 else "6")
        out = u.pin_pos("1" if ch == 0 else "7")
        # non-inverting: DAC -> R3 10k -> +IN ; R4 40.2k +IN -> AGND
        r3 = c.place("R30%d" % (1 + 4 * ch), "R0603_10k", plus[0] - 12.7, plus[1], 90)
        sh.wire(r3.pin_pos(2)[0], r3.pin_pos(2)[1], plus[0], plus[1])
        e = sh.stub(r3, 1, 10.16)
        sh.label(dac, e[0], e[1], 180)
        r4 = c.place("R30%d" % (2 + 4 * ch), "R0603_40R2k", plus[0] - 5.08, plus[1] - 7.62, 0)
        sh.wire(r4.pin_pos(2)[0], r4.pin_pos(2)[1], r4.pin_pos(2)[0], plus[1])
        c.pwr_pin(r4, 1, "AGND")
        # inverting: VREF -> R1 10k -> -IN ; R2 40.2k from -IN to OUT, routed below the amplifier
        r1 = c.place("R30%d" % (3 + 4 * ch), "R0603_10k", minus[0] - 25.4, minus[1], 90)
        sh.wire(r1.pin_pos(2)[0], r1.pin_pos(2)[1], minus[0], minus[1])
        e = sh.stub(r1, 1, 5.08)
        sh.label("VREF_DAC", e[0], e[1], 180, "global")
        yfb = minus[1] + 7.62
        r2 = c.place("R30%d" % (4 + 4 * ch), "R0603_40R2k", out[0] - 2.54, yfb, 90)
        sh.wire(minus[0], minus[1], minus[0] - 2.54, minus[1])
        sh.wire(minus[0] - 2.54, minus[1], minus[0] - 2.54, yfb)
        sh.wire(minus[0] - 2.54, yfb, r2.pin_pos(1)[0], yfb)
        sh.wire(r2.pin_pos(2)[0], yfb, out[0] + 5.08, yfb)
        sh.wire(out[0] + 5.08, yfb, out[0] + 5.08, out[1])
        sh.wire(out[0], out[1], out[0] + 5.08, out[1])
        # 49.9 R -> AO node -> clamp -> label
        rs = c.place("R3%02d" % (9 + ch), "R0603_49R9", out[0] + 12.7, out[1], 90)
        sh.wire(out[0] + 5.08, out[1], rs.pin_pos(1)[0], rs.pin_pos(1)[1])
        node = rs.pin_pos(2)
        sh.wire(node[0], node[1], node[0] + 20.32, node[1])
        sh.label(out_net, node[0] + 20.32, node[1], 0, "global")
        d = c.place("D30%d" % (1 + ch), "BAV99", node[0] + 10.16, node[1] + 8.89, 180)
        sh.wire(d.pin_pos(3)[0], d.pin_pos(3)[1], d.pin_pos(3)[0], node[1])
        e = sh.stub(d, 1, 2.54)
        c.power_at(e[0], e[1], "-12V")
        e = sh.stub(d, 2, 2.54)
        c.power_at(e[0], e[1], "+12V")
    sh.text("AO_n = (1+R2/R1) x R4/(R3+R4) x DAC_n - (R2/R1) x VREF = 4.02 x DAC_n - 4.02 x 2.5 V", 250, 215, 1.3)
    auto_junctions(sh)
    return sh


# ================================================================== B4 SWITCHING
def build_b4(root_uuid):
    sh = Sheet("b4_switching", "B4: 4 relays (MOSFET drive) + 2 isolated 5-24 V inputs", "A3", 6, "AO3400A + 1N4148W flyback per relay; 6N137 inputs with a 2-transistor current limiter")
    c = Ctx(sh, "B4", 4000)
    sheet_frame(sh, "B4", "B4 — ISOLATED SWITCHING: 4 x SPDT relay (3 A / 30 VDC) on AO3400A MOSFETs; 2 x 6N137 isolated inputs, 5-24 V", [
        "Relay drive: AO3400A (48 mOhm) instead of a Darlington: the 5 V coil gets the full +5V_RAW (HK4100F pull-in <= 3.75 V guaranteed, coil 125 R = 40 mA). 1 k gate series, 1N4148W flyback across the coil. Yellow LED shows coil on.",
        "v0.7: the gates are driven by RLY_IN1..4 from the TCA9535 I2C expander (B5, address 0x20), not by a GPIO. The 10 k gate pull-down is what keeps every relay OFF while the ESP32 boots and while the expander powers up with all its ports as inputs (high-impedance) — it must not be omitted.",
        "Contacts: COM/NO/NC to a 3P terminal. Rated 3 A at 30 VDC / 250 VAC by the relay, but this board is limited to <= 30 V DC, 1 A (silkscreen). NO = pad 1, NC = pad 2, COM = pads 5/6 (HK4100F drawing, bottom view mirrored).",
        "Isolated input: series 1N4148W (reverse blocking) -> 220 R -> Q1 pass transistor with Q2 sensing 0.65 V across Rs (100 R || 1 k = 91 R): LED current ~6.5-7 mA from 5 V to 24 V (6N137 needs 5-15 mA). At 24 V Q1 dissipates ~125 mW (MMBT5551 300 mW).",
        "6N137: VCC/VE = +3V3, 1 k pull-up; output LOW when the input is driven (inverting). The isolated side nets (ISO1_*, ISO2_*) have a 2.5 mm clearance class and no copper of any other net underneath.",
    ])
    for k in range(4):
        x0 = 40 + k * 90
        y0 = 70
        K = c.place("K40%d" % (k + 1), "HK4100F-DC5V-SHG", x0 + 45, y0, 0)
        coil_p = K.pin_pos(3)
        coil_m = K.pin_pos(4)
        yA = coil_p[1]                 # +5V_RAW node line
        yB = coil_m[1] + 15.24         # drain node line
        xL = K.x - 33.02
        sh.wire(coil_p[0], coil_p[1], xL, yA)
        sh.wire(coil_m[0], coil_m[1], coil_m[0] - 2.54, coil_m[1])
        sh.wire(coil_m[0] - 2.54, coil_m[1], coil_m[0] - 2.54, yB)
        sh.wire(coil_m[0] - 2.54, yB, xL, yB)
        c.power_at(xL, yA, "+5V_RAW")
        # flyback: K up on the +5V_RAW line, A down on the drain line
        df = c.place("D40%d" % (k + 1), "1N4148W", K.x - 15.24, (yA + yB) / 2, 270)
        sh.wire(df.pin_pos(1)[0], df.pin_pos(1)[1], df.pin_pos(1)[0], yA)
        sh.wire(df.pin_pos(2)[0], df.pin_pos(2)[1], df.pin_pos(2)[0], yB)
        # coil-on LED: +5V_RAW -> 2.2k -> LED -> drain
        rl = c.place("R42%d" % (k + 1), "R0603_2R2k", K.x - 24.13, yA + 3.81, 0)
        dl = c.place("D41%d" % (k + 1), "LED_YELLOW_0603", K.x - 24.13, yA + 11.43, 90)
        sh.wire(rl.pin_pos(1)[0], rl.pin_pos(1)[1], rl.pin_pos(1)[0], yA)
        sh.wire(rl.pin_pos(2)[0], rl.pin_pos(2)[1], dl.pin_pos(2)[0], dl.pin_pos(2)[1])
        sh.wire(dl.pin_pos(1)[0], dl.pin_pos(1)[1], dl.pin_pos(1)[0], yB)
        # MOSFET: drain on the drain line at xL, source to GND, gate from RLY_INn (expander) via 1 k, 10 k pull-down
        Q = c.place("Q40%d" % (k + 1), "AO3400A", xL - 2.54, yB + 12.7, 0)
        d = Q.pin_pos(3)
        sh.wire(d[0], d[1], d[0], yB)
        c.pwr_pin(Q, 2, "GND")
        gpos = Q.pin_pos(1)
        rg = c.place("R40%d" % (k + 1), "R0603_1k", gpos[0] - 10.16, gpos[1], 90)
        sh.wire(rg.pin_pos(2)[0], rg.pin_pos(2)[1], gpos[0], gpos[1])
        e = sh.stub(rg, 1, 3.81)
        sh.label("RLY_IN%d" % (k + 1), e[0], e[1], 180, "global")
        rpd = c.place("R41%d" % (k + 1), "R0603_10k", gpos[0] - 2.54, gpos[1] + 8.89, 0)
        sh.wire(rpd.pin_pos(1)[0], rpd.pin_pos(1)[1], rpd.pin_pos(1)[0], gpos[1])
        c.pwr_pin(rpd, 2, "GND")
        # contacts -> terminal J40n: 1 = NO, 2 = COM, 3 = NC (straight wires; the second COM pad joins via a short drop)
        J = c.place("J40%d" % (k + 1), "KF301-5.0-3P", K.x + 30.48, y0 - 1.27, 0, mirror="y")
        no = K.pin_pos(1)
        com1 = K.pin_pos(5)
        nc = K.pin_pos(2)
        com2 = K.pin_pos(6)
        t1 = J.pin_pos(1)
        t2 = J.pin_pos(2)
        t3 = J.pin_pos(3)
        sh.wire(no[0], no[1], t1[0], t1[1])
        sh.wire(com1[0], com1[1], t2[0], t2[1])
        sh.wire(nc[0], nc[1], t3[0], t3[1])
        xd = t2[0] - 3.81
        sh.wire(com2[0], com2[1], xd, com2[1])
        sh.wire(xd, com2[1], xd, com1[1])
        sh.label("RLY_NO%d" % (k + 1), t1[0] - 8.89, no[1], 0)
        sh.label("RLY_COM%d" % (k + 1), t2[0] - 8.89, com1[1], 0)
        sh.label("RLY_NC%d" % (k + 1), t3[0] - 8.89, nc[1], 0)
        sh.text("J40%d: 1 = NO, 2 = COM, 3 = NC   (<= 30 V DC, 1 A)" % (k + 1), x0 + 5, y0 + 62, 1.2)
    sh.text("v0.7 gate drive: RLY_IN1..4 = TCA9535 P10..P13 (expander U505 on B5, I2C address 0x20) through the 1 k series resistor; the 10 k pull-down holds every relay off at boot and while the expander ports are still inputs.", 40, 142, 1.3)
    # ---- opto inputs -------------------------------------------------------------------------
    for k in range(2):
        x0 = 40 + k * 190
        y0 = 190
        n = k + 1
        J = c.place("J41%d" % n, "KF301-5.0-2P", x0, y0, 0)
        inp = sh.stub(J, 1, 10.16)    # IN+
        inm = sh.stub(J, 2, 5.08)     # IN-
        sh.label("ISO%d_IN+" % n, inp[0] - 5.08, inp[1], 0)
        sh.label("ISO%d_IN-" % n, inm[0] - 2.54, inm[1], 0)
        ds = c.place("D42%d" % n, "1N4148W", inp[0] + 7.62, inp[1], 180)   # A left (pin2), K right (pin1)
        sh.wire(inp[0], inp[1], ds.pin_pos(2)[0], ds.pin_pos(2)[1])
        xA, yA0 = ds.pin_pos(1)                                            # node after the diode
        sh.label("ISO%d_NODE" % n, xA + 1.27, yA0, 0)
        # 220 R -> Q1 collector
        rs = c.place("R43%d" % n, "R0603_220", xA + 8.89, yA0, 90)
        sh.wire(xA, yA0, rs.pin_pos(1)[0], rs.pin_pos(1)[1])
        Q1 = c.place("Q41%d" % n, "MMBT5551", xA + 17.78, yA0 + 10.16, 0)
        col, base, emit = Q1.pin_pos(3), Q1.pin_pos(1), Q1.pin_pos(2)
        sh.wire(rs.pin_pos(2)[0], rs.pin_pos(2)[1], col[0], yA0)
        sh.wire(col[0], yA0, col[0], col[1])
        sh.label("ISO%d_C" % n, rs.pin_pos(2)[0] + 1.27, yA0, 0)
        # 10 k bias from the node to the base line
        rb = c.place("R44%d" % n, "R0603_10k", xA + 2.54, yA0 + 6.35, 0)
        sh.wire(xA + 2.54, yA0, rb.pin_pos(1)[0], rb.pin_pos(1)[1])
        sh.wire(rb.pin_pos(2)[0], rb.pin_pos(2)[1], base[0], base[1])
        sh.label("ISO%d_B" % n, rb.pin_pos(2)[0] + 3.81, base[1], 0)
        # Q2 (mirrored: base on the right) senses the emitter resistor
        Q2 = c.place("Q42%d" % n, "MMBT5551", xA + 15.24, yA0 + 25.4, 0, mirror="y")
        q2c, q2b, q2e = Q2.pin_pos(3), Q2.pin_pos(1), Q2.pin_pos(2)
        sh.wire(q2c[0], q2c[1], q2c[0], base[1])
        y_e = emit[1]
        sh.wire(q2b[0], q2b[1], q2b[0], y_e)
        sh.wire(q2b[0], y_e, emit[0], y_e)
        r100 = c.place("R45%d" % n, "R0603_100", emit[0] + 5.08, y_e + 3.81, 0)
        r1k = c.place("R46%d" % n, "R0603_1k", emit[0] + 12.7, y_e + 3.81, 0)
        sh.wire(emit[0], y_e, r1k.pin_pos(1)[0], y_e)
        sh.label("ISO%d_E" % n, emit[0] + 1.27, y_e, 0)
        y_a = q2e[1] + 2.54                                                 # LED anode line
        for r in (r100, r1k):
            sh.wire(r.pin_pos(2)[0], r.pin_pos(2)[1], r.pin_pos(2)[0], y_a)
        sh.wire(q2e[0], q2e[1], q2e[0], y_a)
        # opto: anode on the anode line, cathode back to IN-
        U = c.place("U40%d" % n, "6N137S-TA1-L", r1k.pin_pos(2)[0] + 33.02, y_a + 5.08, 0)
        an, ka = U.pin_pos(2), U.pin_pos(3)
        sh.wire(q2e[0], y_a, an[0], y_a)
        sh.wire(an[0], y_a, an[0], an[1])
        sh.label("ISO%d_LEDA" % n, r1k.pin_pos(2)[0] + 5.08, y_a, 0)
        y_ret = U.bbox()[3] + 5.08
        sh.wire(ka[0], ka[1], ka[0] - 5.08, ka[1])
        sh.wire(ka[0] - 5.08, ka[1], ka[0] - 5.08, y_ret)
        sh.wire(ka[0] - 5.08, y_ret, inm[0], y_ret)
        sh.wire(inm[0], inm[1], inm[0], y_ret)
        c.nc_pin(U, "1")
        c.nc_pin(U, "4")
        c.pwr_pin(U, "8", "+3V3", 3.81)
        c.pwr_pin(U, "5", "GND", 3.81)
        c.pwr_pin(U, "7", "+3V3", 7.62)
        vo = sh.stub(U, "6", 10.16)
        rp = c.place("R47%d" % n, "R0603_1k", vo[0] - 2.54, vo[1] - 8.89, 0)
        sh.wire(rp.pin_pos(2)[0], rp.pin_pos(2)[1], rp.pin_pos(2)[0], vo[1])
        c.pwr_pin(rp, 1, "+3V3")
        sh.label("OPTO_IN%d" % n, vo[0], vo[1], 0, "global")
        cb = c.place("C40%d" % n, "C0603_100nF", U.x + 22.86, U.y - 15.24, 0)
        c.pwr_pin(cb, 1, "+3V3")
        c.pwr_pin(cb, 2, "GND")
        sh.text("J41%d: 1 = IN+, 2 = IN- (5-24 V DC, isolated, 1.5 kV opto)" % n, x0, y0 + 80, 1.2)
    auto_junctions(sh)
    return sh


# ================================================================== B5 DIO/TRIG
def build_b5(root_uuid):
    sh = Sheet("b5_dio_trig", "B5: 8 TTL DIO, 2 fast TTL outs, bidirectional TRIG, TCXO option", "A3", 7, "74AHCT541 x8 with 1 k series; 74HCT125 fast outs with 49.9 R; 74LVC1T45 TRIG with 33 R + BAV99 clamp; DNP TCXO + Schmitt buffer")
    c = Ctx(sh, "B5", 5000)
    sheet_frame(sh, "B5", "B5 — DIGITAL I/O AND TIMING: 8 x 5 V TTL outputs, 2 fast outputs, bidirectional TRIG (panel SMA), 10 MHz TCXO option", [
        "74AHCT541 (TTL-compatible inputs accept 3.3 V) buffers DIO1..8 to 5 V; 1 k series per output limits a shorted output to 5 mA (students!). Outputs are static/slow (kHz): 1 k x 100 pF cable = 100 ns.",
        "v0.7: DIO1..8 keep their names but are no longer MCU pins — they come from the TCA9535 I2C expander U505 (address 0x20, A0 = A1 = A2 = GND), P00..P07. The 541 runs at +5V_RAW while the expander drives 3.3 V: the AHCT TTL thresholds (VIH 2.0 V) accept that. P10..P13 = RLY_IN1..4 (relay gates, B4), P14..P17 = spare on test points EXP_P14..P17.",
        "74HCT125: FAST_OUT1/2 (MCPWM/RMT) -> 49.9 R series -> terminals; drive +-6 mA rated, so a 50 R termination gives ~1 V: fast outs are for high-impedance TTL loads.",
        "TRIG: 74LVC1T45 A = TRIG_IO (3.3 V), B = 5 V side -> 33 R -> TRIG_5V -> panel SMA; DIR (GPIO39) 1 = output. Into a 50 R termination ~2.4 V typ (beyond the rated 32 mA), 5 V into high-Z. BAV99 clamps B to GND/+5V_RAW.",
        "TCXO option (all DNP): clipped-sine 10 MHz -> 1 nF -> Schmitt buffer biased at VCC/2 -> 74LVC1G17 -> JP501 -> GPIO44 (open JP2 on the base sheet when used). VCONT at 1.65 V from a divider.",
    ])
    U1 = c.place("U501", "SN74AHCT541PWR", 70, 110, 0)
    for i in range(8):
        c.glabel_pin(U1, str(2 + i), "DIO%d" % (i + 1), 7.62)
        ypin = U1.pin_pos(str(18 - i))
        r = c.place("R50%d" % (i + 1), "R0603_1k", ypin[0] + 10.16 + (i % 2) * 12.7, ypin[1], 90)
        sh.wire(ypin[0], ypin[1], r.pin_pos(1)[0], r.pin_pos(1)[1])
        e = sh.stub(r, 2, 5.08 + (1 - i % 2) * 12.7)
        sh.label("TTL%d" % (i + 1), e[0], e[1], 0)
    c.pwr_pin(U1, "1", "GND", 3.81)
    c.pwr_pin(U1, "19", "GND", 3.81)
    c.pwr_pin(U1, "20", "+5V_RAW", 3.81)
    c.pwr_pin(U1, "10", "GND", 3.81)
    cb = c.place("C501", "C0603_100nF", 100, 70, 0)
    c.pwr_pin(cb, 1, "+5V_RAW")
    c.pwr_pin(cb, 2, "GND")
    # terminals for TTL outputs
    for k in range(5):
        J = c.place("J50%d" % (k + 1), "KF301-5.0-2P", 175, 80 + k * 17.78, 0, mirror="y")
        if k < 4:
            for p, ch in ((1, 2 * k + 1), (2, 2 * k + 2)):
                e = sh.stub(J, p, 7.62)
                sh.label("TTL%d" % ch, e[0], e[1], 180)
        else:
            c.pwr_pin(J, 1, "GND", 12.7)
            c.pwr_pin(J, 2, "GND", 5.08)
    sh.text("J501-J504: TTL1..TTL8 (5 V TTL out, 1 k series); J505: GND GND", 130, 175, 1.2)
    # fast outs
    U2 = c.place("U502", "74HCT125PW", 260, 90, 0)
    for pin, net in (("2", "FAST_OUT1"), ("5", "FAST_OUT2")):
        c.glabel_pin(U2, pin, net, 7.62)
    for pin in ("1", "4", "10", "13", "9", "12"):
        c.pwr_pin(U2, pin, "GND", 3.81)
    c.nc_pin(U2, "8")
    c.nc_pin(U2, "11")
    c.pwr_pin(U2, "14", "+5V_RAW", 3.81)
    c.pwr_pin(U2, "7", "GND", 3.81)
    cb2 = c.place("C502", "C0603_100nF", 290, 60, 0)
    c.pwr_pin(cb2, 1, "+5V_RAW")
    c.pwr_pin(cb2, 2, "GND")
    for k, pin in enumerate(("3", "6")):
        y = U2.pin_pos(pin)
        r = c.place("R5%02d" % (9 + k), "R0603_49R9", y[0] + 10.16, y[1], 90)
        sh.wire(y[0], y[1], r.pin_pos(1)[0], r.pin_pos(1)[1])
        e = sh.stub(r, 2, 5.08)
        sh.label("FASTTTL%d" % (k + 1), e[0], e[1], 0)
        J = c.place("J50%d" % (6 + k), "KF301-5.0-2P", 345, 80 + k * 17.78, 0, mirror="y")
        e = sh.stub(J, 1, 7.62)
        sh.label("FASTTTL%d" % (k + 1), e[0], e[1], 180)
        c.pwr_pin(J, 2, "GND", 7.62)
    sh.text("J506/J507: FASTTTL1/2 + GND (5 V TTL, 49.9 R series)", 250, 125, 1.2)
    # TRIG
    U3 = c.place("U503", "SN74LVC1T45DBVR", 260, 175, 0)
    c.glabel_pin(U3, "3", "TRIG_IO", 7.62)
    c.glabel_pin(U3, "5", "TRIG_DIR", 7.62)
    c.pwr_pin(U3, "1", "+3V3", 3.81)
    c.pwr_pin(U3, "6", "+5V_RAW", 3.81)
    c.pwr_pin(U3, "2", "GND", 3.81)
    b = sh.stub(U3, "4", 5.08)
    r = c.place("R511", "R0603_33", b[0] + 3.81, b[1], 90)
    sh.wire(b[0], b[1], r.pin_pos(1)[0], r.pin_pos(1)[1])
    node = r.pin_pos(2)
    sh.wire(node[0], node[1], node[0] + 17.78, node[1])
    sh.label("TRIG_5V", node[0] + 17.78, node[1], 0, "global")
    d = c.place("D501", "BAV99", node[0] + 8.89, node[1] + 8.89, 180)
    sh.wire(d.pin_pos(3)[0], d.pin_pos(3)[1], d.pin_pos(3)[0], node[1])
    e = sh.stub(d, 1, 2.54)
    c.power_at(e[0], e[1], "GND")
    e = sh.stub(d, 2, 2.54)
    c.power_at(e[0], e[1], "+5V_RAW")
    for k, (ref, rail) in enumerate([("C503", "+3V3"), ("C504", "+5V_RAW")]):
        cc = c.place(ref, "C0603_100nF", 300 + k * 10.16, 150, 0)
        c.pwr_pin(cc, 1, rail)
        c.pwr_pin(cc, 2, "GND")
    sh.text("TRIG_DIR = 1: TRIG_IO drives the SMA (output); 0: SMA -> TRIG_IO (input, 5 V tolerant)", 240, 205, 1.2)
    # TCXO option (DNP)
    X = c.place("X501", "1XTV10000MDA", 70, 235, 0, dnp=True)
    c.pwr_pin(X, "4", "+3V3", 3.81)
    c.pwr_pin(X, "2", "GND", 3.81)
    vc = sh.stub(X, "1", 5.08)
    rv1 = c.place("R512", "R0603_100k", vc[0] - 2.54, vc[1] - 8.89, 0, dnp=True)
    rv2 = c.place("R513", "R0603_100k", vc[0] - 2.54, vc[1] + 8.89, 0, dnp=True)
    sh.wire(vc[0], vc[1], rv1.pin_pos(2)[0], vc[1])
    sh.wire(rv1.pin_pos(2)[0], rv1.pin_pos(2)[1], rv1.pin_pos(2)[0], rv2.pin_pos(1)[1])
    c.pwr_pin(rv1, 1, "+3V3")
    c.pwr_pin(rv2, 2, "GND")
    o = sh.stub(X, "3", 5.08)
    cc = c.place("C505", "C0603_1nF", o[0] + 5.08, o[1], 90, dnp=True)
    sh.wire(o[0], o[1], cc.pin_pos(1)[0], cc.pin_pos(1)[1])
    n2 = cc.pin_pos(2)
    U4 = c.place("U504", "SN74LVC1G17DBVR", n2[0] + 17.78, n2[1] + 2.54, 0, dnp=True)
    a = U4.pin_pos("2")
    sh.wire(n2[0], n2[1], a[0], a[1])
    rb1 = c.place("R514", "R0603_100k", n2[0] + 5.08, n2[1] - 8.89, 0, dnp=True)
    rb2 = c.place("R515", "R0603_100k", n2[0] + 5.08, n2[1] + 8.89, 0, dnp=True)
    sh.wire(rb1.pin_pos(2)[0], rb1.pin_pos(2)[1], rb1.pin_pos(2)[0], rb2.pin_pos(1)[1])
    c.pwr_pin(rb1, 1, "+3V3")
    c.pwr_pin(rb2, 2, "GND")
    c.pwr_pin(U4, "5", "+3V3", 3.81)
    c.pwr_pin(U4, "3", "GND", 3.81)
    c.nc_pin(U4, "1")
    yv = sh.stub(U4, "4", 5.08)
    jp = c.place("JP501", "SolderJumper_2_Open", yv[0] + 6.35, yv[1], 0)
    sh.wire(yv[0], yv[1], jp.pin_pos(1)[0], jp.pin_pos(1)[1])
    e = sh.stub(jp, 2, 3.81)
    sh.label("GPIO44", e[0], e[1], 0, "global")
    cd = c.place("C506", "C0603_100nF", U4.x + 15.24, U4.y - 12.7, 0, dnp=True)
    c.pwr_pin(cd, 1, "+3V3")
    c.pwr_pin(cd, 2, "GND")
    sh.text("10 MHz timebase option — all parts DNP by default (zero cost); JP501 open until a firmware use exists", 40, 268, 1.2)
    # ---------------- U505: TCA9535 I2C GPIO expander (v0.7, re-spec 8.2) ----------------------
    U5 = c.place("U505", "TCA9535PWR", 200, 250, 0, block="BASE")   # expander serves B and C: owned by the base (sits under the dev board)
    c.pwr_pin(U5, "24", "+3V3", 3.81)
    c.pwr_pin(U5, "12", "GND", 3.81)
    for pin in ("21", "2", "3"):                     # A0, A1, A2 -> GND: address 0x20
        c.pwr_pin(U5, pin, "GND", 5.08)
    c.glabel_pin(U5, "23", "I2C_SDA", 7.62)
    c.glabel_pin(U5, "22", "I2C_SCL", 7.62)
    c.nc_pin(U5, "1")                                # INT (open drain) unused: the firmware polls the outputs
    for i in range(8):                               # P00..P07 (pins 4..11) -> 74AHCT541 inputs A1..A8
        c.glabel_pin(U5, str(4 + i), "DIO%d" % (i + 1), 7.62)
    for i in range(4):                               # P10..P13 (pins 13..16) -> relay MOSFET gates (B4)
        c.glabel_pin(U5, str(13 + i), "RLY_IN%d" % (i + 1), 7.62)
    for i in range(4):                               # P14..P17 (pins 17..20) -> spare, on test points
        c.glabel_pin(U5, str(17 + i), "EXP_P1%d" % (4 + i), 7.62)
    c.decouple("C507", "C0603_100nF", 270, 235, "+3V3", "GND").fields["Block"] = "BASE"
    for i in range(4):
        tp = c.place("TP50%d" % (i + 1), "TestPoint", 300 + i * 17.78, 230, 0, block="BASE")
        c.glabel_pin(tp, 1, "EXP_P1%d" % (4 + i), 3.81)
    sh.text("U505 TCA9535 (TSSOP-24, address 0x20, A0 = A1 = A2 = GND): the I2C port expander that replaced 12 direct GPIO in v0.7 —", 40, 197, 1.3)
    sh.text("P00..P07 = DIO1..8 into the 74AHCT541 above, P10..P13 = RLY_IN1..4 to the relay gates (B4), P14..P17 spare on TP501..TP504.", 40, 200.5, 1.3)
    sh.text("Every port is an input after power-up and after a reset: the relay gate pull-downs (B4) are what set the safe state.", 40, 204, 1.3)
    auto_junctions(sh)
    return sh


# ================================================================== OPT conditioning
def build_opt(root_uuid):
    sh = Sheet("opt_conditioning", "OPT: instructor signal-conditioning chain (all DNP)", "A3", 8, "INA826 -> PGA113 -> TL072 anti-alias -> COND_OUT1; OPA2156 TIA -> COND_OUT2; AUX SMA routed to the header or the PGA")
    c = Ctx(sh, "OPT", 6000)
    sheet_frame(sh, "OPT", "OPT — SIGNAL CONDITIONING (instructor zone, every part DNP): INA826 in-amp -> PGA113 -> TL072 2nd-order anti-alias -> COND_OUT1; OPA2156 TIA -> COND_OUT2", [
        "Populated only if the instructor decides to; the footprints cost nothing. COND_OUT1/2 reach the ADC channels 7/8 only through JP101/JP102 (B1). AUX SMA -> JP601: A = expansion header (default), B = PGA CH1.",
        "INA826 gain = 1 + 49.4 k / RG: RG open -> G = 1, 5.49 k -> 10, 499 R -> 100 (3-pad jumper JP602 selects). Values are placeholders on DNP footprints (no LCSC number) and belong to the instructor's later choice.",
        "TL072 Sallen-Key: fc = 1 / (2 pi sqrt(R1 R2 C1 C2)); with 10 k / 10 k / 1 nF / 1 nF fc = 15.9 kHz (placeholder, set at population). OPA2156 TIA: gain = -Rf; Cf sets the bandwidth (placeholders).",
        "All option ICs run on +-12 V / +5VA / +3V3 and use AGND; PGA113 CS = GPIO43 (open JP1 on the base sheet when populated).",
    ])
    # sensor input terminal + protection
    J = c.place("J601", "KF301-5.0-2P", 40, 90, 0, dnp=True)
    ins = []
    for k, pin in enumerate(("1", "2")):
        e = sh.stub(J, pin, 5.08 + k * 2.54)
        yk = e[1] + k * 17.78
        sh.wire(e[0], e[1], e[0], yk)
        r = c.place("R60%d" % (1 + k), "R0603_1k", e[0] + 7.62, yk, 90, dnp=True, value="1k (opt)")
        sh.wire(e[0], yk, r.pin_pos(1)[0], r.pin_pos(1)[1])
        n = r.pin_pos(2)
        d = c.place("D60%d" % (1 + k), "BAV99", n[0] + 10.16, n[1] + 8.89, 180, dnp=True)
        sh.wire(d.pin_pos(3)[0], d.pin_pos(3)[1], d.pin_pos(3)[0], n[1])
        sh.wire(n[0], n[1], d.pin_pos(3)[0], n[1])
        ee = sh.stub(d, 1, 2.54)
        c.power_at(ee[0], ee[1], "-12V")
        ee = sh.stub(d, 2, 2.54)
        c.power_at(ee[0], ee[1], "+12V")
        ins.append((d.pin_pos(3)[0], n[1]))
    U1 = c.place("U601", "INA826AIDR", 120, 95, 0, dnp=True)
    pp = U1.pin_pos("4")
    pm = U1.pin_pos("1")
    sh.wire(ins[0][0], ins[0][1], pp[0] - 5.08, ins[0][1])
    sh.wire(pp[0] - 5.08, ins[0][1], pp[0] - 5.08, pp[1])
    sh.wire(pp[0] - 5.08, pp[1], pp[0], pp[1])
    sh.wire(ins[1][0], ins[1][1], pm[0] - 2.54, ins[1][1])
    sh.wire(pm[0] - 2.54, ins[1][1], pm[0] - 2.54, pm[1])
    sh.wire(pm[0] - 2.54, pm[1], pm[0], pm[1])
    sh.label("COND_IN+", ins[0][0], ins[0][1], 0)
    sh.label("COND_IN-", ins[1][0], ins[1][1], 0)
    # RG jumper: 3-pad: C = RG pin 2, A = 5.49k path, B = 499 path ; other RG pin to both resistors
    rg1 = sh.stub(U1, "2", 5.08)
    rg2 = sh.stub(U1, "3", 5.08)
    jp = c.place("JP602", "SolderJumper_3_Open", rg1[0] - 2.54, rg1[1] - 22.86, 0)
    sh.wire(rg1[0], rg1[1], jp.pin_pos(2)[0], rg1[1])
    sh.wire(jp.pin_pos(2)[0], jp.pin_pos(2)[1], jp.pin_pos(2)[0], rg1[1])
    ra = c.place("R603", "R0603_1k", jp.pin_pos(1)[0] - 7.62, jp.pin_pos(1)[1] + 12.7, 0, dnp=True, value="5.49k (G=10)")
    rb = c.place("R604", "R0603_1k", jp.pin_pos(3)[0] + 7.62, jp.pin_pos(3)[1] + 12.7, 0, dnp=True, value="499 (G=100)")
    sh.wire(jp.pin_pos(1)[0], jp.pin_pos(1)[1], ra.pin_pos(1)[0], jp.pin_pos(1)[1])
    sh.wire(ra.pin_pos(1)[0], jp.pin_pos(1)[1], ra.pin_pos(1)[0], ra.pin_pos(1)[1])
    sh.wire(jp.pin_pos(3)[0], jp.pin_pos(3)[1], rb.pin_pos(1)[0], jp.pin_pos(3)[1])
    sh.wire(rb.pin_pos(1)[0], jp.pin_pos(3)[1], rb.pin_pos(1)[0], rb.pin_pos(1)[1])
    yb = max(ra.pin_pos(2)[1], rg2[1]) + 2.54
    sh.wire(ra.pin_pos(2)[0], ra.pin_pos(2)[1], ra.pin_pos(2)[0], yb)
    sh.wire(rb.pin_pos(2)[0], rb.pin_pos(2)[1], rb.pin_pos(2)[0], yb)
    sh.wire(ra.pin_pos(2)[0], yb, rb.pin_pos(2)[0], yb)
    sh.wire(rg2[0], rg2[1], rg2[0], yb)
    c.pwr_pin(U1, "8", "+12V", 3.81)
    c.pwr_pin(U1, "5", "-12V", 3.81)
    c.pwr_pin(U1, "6", "AGND", 5.08)
    o = sh.stub(U1, "7", 7.62)
    sh.label("INA_OUT", o[0], o[1], 0)
    # PGA113
    U2 = c.place("U602", "PGA113AIDGSR", 200, 100, 0, dnp=True)
    c.label_pin(U2, "3", "INA_OUT", 7.62)
    aux = sh.stub(U2, "2", 7.62)
    jpa = c.place("JP601", "SolderJumper_3_Bridged12", aux[0] - 7.62, aux[1] + 12.7, 0)
    sh.wire(aux[0], aux[1], jpa.pin_pos(3)[0] + 0, aux[1])
    sh.wire(jpa.pin_pos(3)[0], aux[1], jpa.pin_pos(3)[0], jpa.pin_pos(3)[1])
    e = sh.stub(jpa, 2, 3.81)
    sh.label("AUX", e[0], e[1], 270, "global")
    e = sh.stub(jpa, 1, 3.81)
    sh.label("AUX_HDR", e[0], e[1], 180, "global")
    c.pwr_pin(U2, "4", "AGND", 5.08)
    c.glabel_pin(U2, "9", "GPIO43", 7.62)
    c.glabel_pin(U2, "7", "SPI_SCLK", 7.62)
    c.glabel_pin(U2, "8", "SPI_MOSI", 7.62)
    c.pwr_pin(U2, "1", "+5VA", 3.81)
    c.pwr_pin(U2, "10", "+3V3", 3.81)
    c.pwr_pin(U2, "6", "AGND", 3.81)
    po = sh.stub(U2, "5", 7.62)
    sh.label("PGA_OUT", po[0], po[1], 0)
    sh.text("PGA113: CS = GPIO43 (CS_OPT), DIO = SPI_MOSI (write-only use), VREF = AGND", 170, 140, 1.2)
    for k, (ref, rail, gnd) in enumerate([("C601", "+5VA", "AGND"), ("C602", "+3V3", "GND"), ("C603", "+12V", "AGND"), ("C604", "-12V", "AGND")]):
        cc = c.place(ref, "C0603_100nF", 40 + k * 12.7, 150, 0, dnp=True)
        c.pwr_pin(cc, 1, rail)
        c.pwr_pin(cc, 2, gnd)
    sh.text("option decoupling (DNP)", 40, 162, 1.2)
    # TL072 Sallen-Key (unit A), unit B unused (inputs tied)
    U3a = c.place("U603", "TL072CDT", 300, 95, 0, unit=1, dnp=True)
    U3b = c.place("U603", "TL072CDT", 300, 150, 0, unit=2, dnp=True)
    U3p = c.place("U603", "TL072CDT", 360, 95, 0, unit=3, dnp=True)
    c.pwr_pin(U3p, "8", "+12V", 2.54)
    c.pwr_pin(U3p, "4", "-12V", 2.54)
    plus = U3a.pin_pos("3")
    minus = U3a.pin_pos("2")
    out = U3a.pin_pos("1")
    r1 = c.place("R605", "R0603_10k", plus[0] - 25.4, plus[1], 90, dnp=True, value="10k (opt)")
    r2 = c.place("R606", "R0603_10k", plus[0] - 12.7, plus[1], 90, dnp=True, value="10k (opt)")
    sh.wire(r1.pin_pos(2)[0], r1.pin_pos(2)[1], r2.pin_pos(1)[0], r2.pin_pos(1)[1])
    sh.wire(r2.pin_pos(2)[0], r2.pin_pos(2)[1], plus[0], plus[1])
    e = sh.stub(r1, 1, 3.81)
    sh.label("PGA_OUT", e[0], e[1], 180)
    c1 = c.place("C605", "C0603_1nF", plus[0] - 6.35, plus[1] + 7.62, 0, dnp=True, value="1nF (opt)")
    sh.wire(c1.pin_pos(1)[0], c1.pin_pos(1)[1], c1.pin_pos(1)[0], plus[1])
    c.pwr_pin(c1, 2, "AGND")
    c2 = c.place("C606", "C0603_1nF", r2.pin_pos(1)[0] + 0, plus[1] - 10.16, 90, dnp=True, value="1nF (opt)")   # from mid node up to output line
    mid = r2.pin_pos(1)
    sh.wire(mid[0], mid[1], mid[0], mid[1] - 5.08)
    c2.x, c2.y = g(mid[0] + 12.7), g(mid[1] - 10.16)
    sh.wire(mid[0], mid[1] - 5.08, c2.pin_pos(1)[0], mid[1] - 5.08)
    sh.wire(c2.pin_pos(1)[0], mid[1] - 5.08, c2.pin_pos(1)[0], c2.pin_pos(1)[1])
    sh.wire(c2.pin_pos(2)[0], c2.pin_pos(2)[1], out[0] + 5.08, c2.pin_pos(2)[1])
    sh.wire(out[0] + 5.08, c2.pin_pos(2)[1], out[0] + 5.08, out[1])
    sh.wire(out[0], out[1], out[0] + 12.7, out[1])
    sh.wire(minus[0], minus[1], minus[0] - 2.54, minus[1])
    sh.wire(minus[0] - 2.54, minus[1], minus[0] - 2.54, minus[1] + 12.7)
    sh.wire(minus[0] - 2.54, minus[1] + 12.7, out[0] + 5.08, minus[1] + 12.7)
    sh.wire(out[0] + 5.08, minus[1] + 12.7, out[0] + 5.08, out[1])
    sh.label("COND_OUT1", out[0] + 12.7, out[1], 0, "global")
    # unit B: tie -IN to OUT, +IN to AGND
    pb = U3b.pin_pos("5")
    mb = U3b.pin_pos("6")
    ob = U3b.pin_pos("7")
    c.pwr_pin(U3b, "5", "AGND", 3.81)
    sh.wire(mb[0], mb[1], mb[0] - 2.54, mb[1])
    sh.wire(mb[0] - 2.54, mb[1], mb[0] - 2.54, mb[1] + 10.16)
    sh.wire(mb[0] - 2.54, mb[1] + 10.16, ob[0] + 2.54, mb[1] + 10.16)
    sh.wire(ob[0] + 2.54, mb[1] + 10.16, ob[0] + 2.54, ob[1])
    sh.wire(ob[0], ob[1], ob[0] + 2.54, ob[1])
    sh.text("unused unit B: follower with +IN at AGND", 285, 170, 1.2)
    # OPA2156 TIA (unit A) + photodiode terminal
    U4a = c.place("U604", "OPA2156IDR", 300, 220, 0, unit=1, dnp=True)
    U4b = c.place("U604", "OPA2156IDR", 300, 260, 0, unit=2, dnp=True)
    U4p = c.place("U604", "OPA2156IDR", 360, 220, 0, unit=3, dnp=True)
    c.pwr_pin(U4p, "8", "+12V", 2.54)
    c.pwr_pin(U4p, "4", "-12V", 2.54)
    J2 = c.place("J602", "KF301-5.0-2P", 200, 220, 0, dnp=True)
    pd1 = sh.stub(J2, 1, 7.62)
    pd2 = sh.stub(J2, 2, 7.62)
    m = U4a.pin_pos("2")
    p = U4a.pin_pos("3")
    o = U4a.pin_pos("1")
    sh.wire(pd1[0], pd1[1], pd1[0] + 25.4, pd1[1])
    sh.wire(pd1[0] + 25.4, pd1[1], pd1[0] + 25.4, m[1])
    sh.wire(pd1[0] + 25.4, m[1], m[0] - 5.08, m[1])
    c.power_at(pd2[0], pd2[1], "AGND")
    c.pwr_pin(U4a, "3", "AGND", 3.81)
    yfb1 = m[1] + 10.16
    yfb2 = m[1] + 17.78
    rf = c.place("R607", "R0603_100k", o[0] - 2.54, yfb1, 90, dnp=True, value="Rf (opt)")
    cf = c.place("C607", "C0603_1nF", o[0] - 2.54, yfb2, 90, dnp=True, value="Cf (opt)")
    sh.wire(m[0], m[1], m[0] - 5.08, m[1])
    sh.wire(m[0] - 5.08, m[1], m[0] - 5.08, yfb2)
    for part, yy in ((rf, yfb1), (cf, yfb2)):
        sh.wire(m[0] - 5.08, yy, part.pin_pos(1)[0], yy)
        sh.wire(part.pin_pos(2)[0], yy, o[0] + 5.08, yy)
    sh.wire(o[0] + 5.08, yfb2, o[0] + 5.08, o[1])
    sh.wire(o[0], o[1], o[0] + 12.7, o[1])
    sh.label("COND_OUT2", o[0] + 12.7, o[1], 0, "global")
    sh.label("PD_IN", pd1[0], pd1[1], 0)
    # unit B follower
    mb = U4b.pin_pos("6")
    ob = U4b.pin_pos("7")
    c.pwr_pin(U4b, "5", "AGND", 3.81)
    sh.wire(mb[0], mb[1], mb[0] - 2.54, mb[1])
    sh.wire(mb[0] - 2.54, mb[1], mb[0] - 2.54, mb[1] + 10.16)
    sh.wire(mb[0] - 2.54, mb[1] + 10.16, ob[0] + 2.54, mb[1] + 10.16)
    sh.wire(ob[0] + 2.54, mb[1] + 10.16, ob[0] + 2.54, ob[1])
    sh.wire(ob[0], ob[1], ob[0] + 2.54, ob[1])
    sh.text("J602: photodiode (1 = cathode to -IN, 2 = AGND). TIA output = -I_pd x Rf", 180, 250, 1.2)
    auto_junctions(sh)
    return sh


# ================================================================== FRONT PANEL LINK
LINK = {1: "AO1", 2: "AGND", 3: "AO2", 4: "AGND", 5: "TRIG_5V", 6: "GND", 7: "AUX", 8: "AGND",
        9: "AI1", 10: "AGND", 11: "AI2", 12: "AGND", 13: "AI3", 14: "AGND", 15: "AI4", 16: "AGND",
        17: "AI5", 18: "AGND", 19: "AI6", 20: "AGND", 21: "AI7", 22: "AGND", 23: "AI8", 24: "AGND",
        25: "I2C_SDA", 26: "GND", 27: "I2C_SCL", 28: "GND", 29: "+3V3", 30: "GND",
        31: "LED_PWR", 32: "GND", 33: "LED_WIFI", 34: "GND", 35: "LED_ACT", 36: "GND",
        37: "RX", 38: "AGND", 39: "TX", 40: "AGND"}


def build_link(root_uuid):
    sh = Sheet("front_panel_link", "Front-panel link J6 (2x20, brief 7.8)", "A3", 9, "Every signal has GND/AGND on the adjacent pin")
    c = Ctx(sh, "BASE", 7000)
    sheet_frame(sh, "LINK", "FRONT-PANEL LINK — J6 2x20 right-angle male (front edge), pinout per design brief 7.8", [
        "Odd pins = row A, even pins = row B. Analog signals AO1/AO2/AUX/AI1-8 are each paired with AGND; TRIG_5V, I2C, LEDs and rails with GND. Panel copper is AGND and reaches GND only through the main-board star point NT1.",
        "LED_PWR is +3V3 (always on, resistor on the panel). LED_WIFI/LED_ACT come from GPIO43/GPIO44 through JP1/JP2 (base sheet). Pins 37/39 = RX/TX (the NMR receive/transmit coil ports, analog) to the panel SMAs with AGND on 38/40 (v0.7); +5V_RAW no longer reaches the panel.",
    ])
    J = c.place("J6", "HDR_2x20_RA_MALE", 150, 130, 0)
    for pin, net in LINK.items():
        if net is None:
            c.nc_pin(J, pin)
        elif net in ("GND", "AGND", "+3V3", "+5V_RAW"):
            c.pwr_pin(J, pin, net, 7.62 if (pin // 2) % 2 else 12.7)
        elif net == "LED_PWR":
            c.pwr_pin(J, pin, "+3V3", 12.7)
        else:
            c.glabel_pin(J, pin, net, 7.62)
    sh.text("Pin 31 (LED_PWR) = +3V3 directly; the panel LED series resistor sits on the panel PCB", 240, 72, 1.2)
    rows = [["Pins", "Signals"], ["1-8", "AO1 AGND AO2 AGND TRIG_5V GND AUX AGND"], ["9-16", "AI1 AGND AI2 AGND AI3 AGND AI4 AGND"],
            ["17-24", "AI5 AGND AI6 AGND AI7 AGND AI8 AGND"], ["25-30", "I2C_SDA GND I2C_SCL GND +3V3 GND"], ["31-36", "LED_PWR GND LED_WIFI GND LED_ACT GND"],
            ["37-40", "RX AGND TX AGND"]]
    sh.table(240, 100, rows, [18, 110], 1.4)
    auto_junctions(sh)
    return sh


# ================================================================== ROOT
def build_root(sheets, root_uuid):
    sh = Sheet("class-board", "TIGP class board 2026 — root", "A3", 1, "ESP32-S3 laboratory instrument carrier + NMR console: base + 3 student sections (A inputs/receiver, B outputs/timing/transmitter, C power/switching) + front panel link")
    sh.uuid = root_uuid
    sh.text("TIGP CLASS BOARD 2026 — laboratory instrument carrier (ESP32-S3 dev board) with NMR console, rev B (v0.7, 2026-09-13)", 12.7, 16, 3.5, True)
    sh.text("Design brief v0.6 + notes/2026-09-13-nmr-respec-proposal.md (v0.7) + hardware/docs/design-decisions.md. Interface nets between sheets are global labels; rails are power symbols; AGND meets GND only at NT1.", 12.7, 21, 1.5)
    sh.text("Stack-up: L1 signal/power, L2 GND, L3 GND, L4 signal/power. Board 160 x 100 mm, 4 x M3. Front edge: 2x20 link to the SMA/OLED/LED panel (160 x 65, 3 x 5 SMA). Rear edge: USB-C, 5 V jack, terminals, external power. Sections: A = B1 + NMR RX, B = B3 + B5 + NMR TX, C = B2 + B4 + coil switches.", 12.7, 25, 1.5)
    core = ["base_mcu", "b2_power", "b1_inputs", "b3_outputs", "b4_switching", "b5_dio_trig", "front_panel_link"]
    order = [n for n in core if n in sheets] + [n for n in sheets if n not in core]
    titles = {"base_mcu": "BASE: dev-board socket, buses, expansion, star point", "b2_power": "B2 (C): power entry, +-12 V, LDOs",
              "b1_inputs": "B1 (A): 8 x +-10 V inputs, ADS8688", "b3_outputs": "B3 (B): DAC8563 + OPA2192 -> AO1/AO2", "b4_switching": "B4 (C): 4 relays, 2 isolated inputs",
              "b5_dio_trig": "B5 (B): TCA9535 -> 8 TTL DIO + relays, 2 fast outs, TRIG", "front_panel_link": "LINK: 2x20 to the front panel"}
    for k, name in enumerate(order):
        col, row = k % 4, k // 4
        x, y = 12.7 + col * 100, 35 + row * 45
        s = sheets[name]
        sh.sheets.append(dict(name=name, file="sheets/%s.kicad_sch" % name, x=g(x), y=g(y), w=88.9, h=30.48, pins=[], uuid=s.uuid, page=s.page))
        sh.text(titles.get(name, s.title), x + 1.5, y + 27, 1.3)
    # interface tables
    gpio = [["GPIO", "Net", "Function", "Section"], ["12/11/13", "SPI_SCLK/MOSI/MISO", "SPI2 IO_MUX, 33 R at source (ADC, DAC, DDS)", "base"], ["10", "CS_ADC", "ADS8688 /CS", "A"], ["5", "CS_DAC", "DAC8563 /SYNC (via 74HCT125)", "B"],
            ["1/2", "I2C_SDA/SCL", "400 kHz: OLED 0x3C, TCA9535 0x20, Si5351A 0x60, 2 Qwiic", "base"], ["16/17", "OPTO_IN1/2", "6N137 outputs, 1 k pull-up, active LOW", "C"], ["18/21", "FAST_OUT1/2", "74HCT125 -> 49.9 R -> terminals", "B"],
            ["38/39", "TRIG_IO / TRIG_DIR", "74LVC1T45; DIR 1 = output to the SMA", "B"], ["41/42", "DDS_FSYNC / DDS_PSEL", "AD9834 frame sync / phase-register select", "B"],
            ["40", "TX_EN", "OPA564 enable = transmit gate (10 k pull-down)", "B"], ["8", "RX_BLANK", "DG419 receiver blanking (pull-up: blanked)", "A"],
            ["9/14", "HB_IN1/2", "DRV8871 H-bridge inputs (10 k pull-downs)", "C"], ["47", "FET_GATE", "UCC27517 -> AOD4184A polarizer switch", "C"],
            ["TCA9535 P00-P07", "DIO1..8", "74AHCT541 -> 1 k -> terminals (I2C expander)", "B"], ["TCA9535 P10-P13", "RLY_IN1..4", "AO3400A relay gates (10 k pull-down)", "C"],
            ["4/6/7/15", "GPIO4/6/7/15", "free -> 2x10 expansion header", "base"], ["19/20", "USB_DN/DP", "native USB from the carrier USB-C", "base"],
            ["43/44", "GPIO43/44", "header; LED_WIFI/ACT via JP1/JP2; TCXO option", "base"], ["3, 0/45/46, 35-37, 48", "-", "strapping / PSRAM / on-board LED: unused", "-"]]
    sh.table(12.7, 180, gpio, [34, 40, 92, 14], 1.3)
    rails = [["Rail", "Source", "Budget", "Feeds"], ["+5V_RAW", "USB-C or jack via polyfuse + TVS + LM66100", "<= 1.5 A (est. 1.0-1.2 A)", "dev board, relays, 5 V logic, LDO, DC-DC"],
             ["+3V3", "AMS1117-3.3", "<= 500 mA (est. < 150 mA)", "logic side, OLED, optos, Qwiic"], ["+12V / -12V", "B0512S-2WR3 x2, AGND-referenced", "166 mA each (est. 40 / 20 mA incl. bleeders)", "78L05, OPA2192, clamps, OPT"],
             ["+5VA", "78L05G from +12V", "<= 100 mA (est. 17 mA)", "ADS8688 / DAC8563 AVDD"], ["AGND", "star point NT1 (net tie) to GND", "-", "L1/L4 analog copper, panel copper"]]
    sh.table(200, 180, rails, [26, 62, 52, 60], 1.3)
    sh.text("GPIO map v0.7 (interface contract, brief 4.2 + proposal 8.2)", 12.7, 177, 1.5, True)
    sh.text("Rails (brief 4.1, updated per design-decisions D-02/D-04; +VEXT 7-18 V external input on the C sheet)", 200, 177, 1.5, True)
    sh.text("Reference ranges: base 1-99, B1 100-199, B2 200-299, B3 300-399, B4 400-499, B5 500-599, NMR RX 700-799, NMR TX 800-899, coil switches / external power 900-999 (owner-zone DRC uses the Block field: A / B / C).", 12.7, 272, 1.4)
    sh.text("Student gapped copies (D6) are derived from these sheets: see hardware/student/ and docs/student-deletions.md.", 12.7, 276, 1.4)
    return sh


# ================================================================== project file
def write_project(path):
    pro = {
        "board": {"3dviewports": [], "design_settings": {
            "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "copper_text_size_h": 1.0, "copper_text_size_v": 1.0, "copper_text_thickness": 0.15,
                         "courtyard_line_width": 0.05, "other_line_width": 0.1, "silk_line_width": 0.15, "silk_text_size_h": 1.0, "silk_text_size_v": 1.0, "silk_text_thickness": 0.15,
                         "pad_drill": 0.3, "pad_size": [0.6, 0.6]},
            "diff_pair_dimensions": [], "drc_exclusions": [],
            "rules": {"max_error": 0.005, "min_clearance": 0.2, "min_connection": 0.0, "min_copper_edge_clearance": 0.3, "min_hole_clearance": 0.2, "min_hole_to_hole": 0.5,
                      "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1, "min_resolved_spokes": 2, "min_silk_clearance": 0.0, "min_text_height": 1.0, "min_text_thickness": 0.1,
                      "min_through_hole_diameter": 0.3, "min_track_width": 0.2, "min_via_annular_width": 0.15, "min_via_diameter": 0.6, "solder_mask_to_copper_clearance": 0.0,
                      "use_height_for_length_calcs": True},
            "rule_severities": {"courtyards_overlap": "error", "copper_edge_clearance": "error", "silk_over_copper": "warning", "silk_overlap": "warning",
                                "lib_footprint_issues": "warning", "lib_footprint_mismatch": "warning", "footprint_type_mismatch": "ignore", "starved_thermal": "warning",
                                "text_height": "warning", "text_thickness": "warning", "isolated_copper": "warning", "solder_mask_bridge": "error", "unresolved_variable": "warning"},
            "track_widths": [0.2, 0.25, 0.3, 0.5, 0.8, 1.0], "via_dimensions": [{"diameter": 0.6, "drill": 0.3}, {"diameter": 0.8, "drill": 0.4}]},
                  "layer_presets": [], "viewports": []},
        "boards": [], "cvpcb": {"equivalence_files": []},
        "erc": {"erc_exclusions": [], "meta": {"version": 0}, "pin_map": [], "rule_severities": {}},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": "class-board.kicad_pro", "version": 3},
        "net_settings": {"classes": [
            {"name": "Default", "clearance": 0.2, "track_width": 0.25, "via_diameter": 0.6, "via_drill": 0.3, "bus_width": 12, "wire_width": 6, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647},
            {"name": "POWER_RAW", "clearance": 0.2, "track_width": 1.0, "via_diameter": 0.8, "via_drill": 0.4, "bus_width": 12, "wire_width": 6, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 0},
            {"name": "POWER", "clearance": 0.2, "track_width": 0.5, "via_diameter": 0.8, "via_drill": 0.4, "bus_width": 12, "wire_width": 6, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 1},
            {"name": "ANALOG_IN", "clearance": 0.2, "track_width": 0.25, "via_diameter": 0.6, "via_drill": 0.3, "bus_width": 12, "wire_width": 6, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 2},
            {"name": "ANALOG_OUT", "clearance": 0.2, "track_width": 0.3, "via_diameter": 0.6, "via_drill": 0.3, "bus_width": 12, "wire_width": 6, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 3},
            {"name": "FAST", "clearance": 0.2, "track_width": 0.25, "via_diameter": 0.6, "via_drill": 0.3, "bus_width": 12, "wire_width": 6, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 4},
            {"name": "ISO_IN", "clearance": 0.2, "track_width": 0.3, "via_diameter": 0.6, "via_drill": 0.3, "bus_width": 12, "wire_width": 6, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 5},
            {"name": "RELAY_CONTACT", "clearance": 0.2, "track_width": 0.5, "via_diameter": 0.8, "via_drill": 0.4, "bus_width": 12, "wire_width": 6, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 6}],
            "meta": {"version": 4},
            "net_colors": None, "netclass_assignments": None,
            "netclass_patterns": [
                {"netclass": "POWER_RAW", "pattern": "+5V_RAW"}, {"netclass": "POWER_RAW", "pattern": "+5V_RAW_OR"},
                {"netclass": "POWER", "pattern": "+12V"}, {"netclass": "POWER", "pattern": "-12V"}, {"netclass": "POWER", "pattern": "+5VA"}, {"netclass": "POWER", "pattern": "+3V3"}, {"netclass": "POWER", "pattern": "AGND"},
                {"netclass": "ANALOG_IN", "pattern": "/b1_inputs/AIN*"}, {"netclass": "ANALOG_IN", "pattern": "AI?"},
                {"netclass": "ANALOG_OUT", "pattern": "AO?"}, {"netclass": "ANALOG_OUT", "pattern": "/b3_outputs/AOUT*"},
                {"netclass": "FAST", "pattern": "SPI_*"}, {"netclass": "FAST", "pattern": "CS_*"}, {"netclass": "FAST", "pattern": "FAST_OUT?"}, {"netclass": "FAST", "pattern": "TRIG_*"},
                {"netclass": "FAST", "pattern": "/b3_outputs/DAC_*"}, {"netclass": "FAST", "pattern": "/base_mcu/*_MCU"},
                {"netclass": "ISO_IN", "pattern": "/b4_switching/ISO*"}, {"netclass": "ISO_IN", "pattern": "unconnected-(U401-NC*"}, {"netclass": "ISO_IN", "pattern": "unconnected-(U402-NC*"},
                {"netclass": "RELAY_CONTACT", "pattern": "/b4_switching/RLY_*"}]},
        "pcbnew": {"last_paths": {"gencad": "", "idf": "", "netlist": "", "plot": "", "pos_files": "", "specctra_dsn": "", "step": "", "svg": "", "vrml": ""}, "page_layout_descr_file": ""},
        "schematic": {"annotate_start_num": 0, "bom_export_filename": "", "bom_fmt_presets": [], "bom_fmt_settings": {}, "bom_presets": [], "bom_settings": {},
                      "connection_grid_size": 50.0, "drawing": {"default_line_thickness": 6.0, "default_text_size": 50.0, "field_names": [], "intersheets_ref_own_page": False,
                                                                 "intersheets_ref_prefix": "", "intersheets_ref_short": False, "intersheets_ref_show": False, "intersheets_ref_suffix": "",
                                                                 "junction_size_choice": 3, "label_size_ratio": 0.375, "operating_point_overlay_i_precision": 3, "operating_point_overlay_i_range": "~",
                                                                 "operating_point_overlay_v_precision": 3, "operating_point_overlay_v_range": "~", "overbar_offset_ratio": 1.23, "pin_symbol_size": 25.0, "text_offset_ratio": 0.15},
                      "legacy_lib_dir": "", "legacy_lib_list": [], "meta": {"version": 1}, "net_format_name": "", "page_layout_descr_file": "", "plot_directory": "", "spice_current_sheet_as_root": False,
                      "spice_external_command": "spice \"%I\"", "spice_model_current_sheet_as_root": True, "spice_save_all_currents": False, "spice_save_all_dissipations": False, "spice_save_all_voltages": False,
                      "subpart_first_id": 65, "subpart_id_separator": 0},
        "sheets": [], "text_variables": {"REV": "A", "BOARD": "TIGP class board 2026"},
    }
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(pro, fh, indent=2)


def main():
    root_uuid = uid_for("root:" + PROJECT)
    sheets = {}
    for fn in (build_base, build_b2, build_b1, build_b3, build_b4, build_b5, build_link):
        s = fn(root_uuid)
        sheets[s.name] = s
    # v0.7 (2026-09-13): the OPT conditioning sheet is deleted; extra sheets come from scripts/sheet_*.py,
    # each exposing build(root_uuid) -> Sheet (and PLACEMENT for gen_pcb). A module that fails to import is skipped.
    import glob, importlib
    for path in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sheet_*.py"))):
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            mod = importlib.import_module(name)
            s = mod.build(root_uuid)
            sheets[s.name] = s
        except Exception as e:  # noqa: BLE001
            print("sheet module %s skipped: %s" % (name, e))
    root = build_root(sheets, root_uuid)
    refs = {}
    for s in sheets.values():
        for i in s.insts:
            if i.ref.startswith("#"):
                continue
            key = (i.ref, i.unit)
            assert key not in refs, "duplicate reference %s unit %d in %s and %s" % (i.ref, i.unit, refs[key], s.name)
            refs[key] = s.name
    os.makedirs(os.path.join(HW, "sheets"), exist_ok=True)
    root.write(os.path.join(HW, PROJECT + ".kicad_sch"), PROJECT, root_uuid, "/" + root_uuid)
    for name, s in sheets.items():
        s.write(os.path.join(HW, "sheets", name + ".kicad_sch"), PROJECT, root_uuid, "/" + root_uuid + "/" + s.uuid)
    write_project(os.path.join(HW, PROJECT + ".kicad_pro"))
    n = sum(len([i for i in s.insts if not i.sym.power]) for s in sheets.values())
    print("root + %d sheets, %d component instances" % (len(sheets), n))


if __name__ == "__main__":
    main()
