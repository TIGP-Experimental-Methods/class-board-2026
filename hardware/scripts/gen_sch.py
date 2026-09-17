"""Generate the class-board hierarchical schematic (D2).

Run from hardware/scripts:  python gen_sch.py
Writes ../class-board.kicad_sch (root), ../sheets/*.kicad_sch and ../class-board.kicad_pro.

Design sources: 10-Class-Board-Design-Brief.md v0.6, docs/design-decisions.md (datasheet-derived
changes: LM66100 ORing, 74HCT125 DAC level shift,
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

    # ---- spacing-rework helpers (2026-09-17): symbols never sit mid-wire, grounds never above a wire ----
    def tap(self, x, y, net, length=2.54, direction=None):
        """rail / ground / PWR_FLAG symbol on its own short stub from a bus point: up for rails and flags,
        down for GND / AGND / -12V (override with direction='up'|'down')."""
        down = net in ("GND", "AGND", "-12V")
        if direction:
            down = direction == "down"
        ey = y + length if down else y - length
        self.sh.wire(x, y, x, ey)
        if net == "PWR_FLAG":
            return self.flag(x, ey, 180 if down else 0)
        gnd_type = net in ("GND", "AGND", "-12V")
        rot = 0 if down == gnd_type else 180
        return self.power_at(x, ey, net, rot)

    def pwr_L(self, inst, pin, net, out=2.54, leg=5.08, direction=None):
        """stub outward from the pin by `out`, then a vertical leg to the symbol (down for grounds)."""
        ex, ey = self.sh.stub(inst, pin, out)
        return self.tap(ex, ey, net, leg, direction)

    def comb(self, inst, pins, net, out=5.08, tail=5.08, direction=None):
        """adjacent pins on one side of a symbol: stub each by `out`, join the stub ends with one bus wire,
        one symbol on a `tail` stub beyond the last pin (down for grounds, up for rails)."""
        ends = [self.sh.stub(inst, p, out) for p in pins]
        xs = sorted({e[0] for e in ends})
        ys = sorted({e[1] for e in ends})
        down = net in ("GND", "AGND", "-12V")
        if direction:
            down = direction == "down"
        if len(xs) == 1:            # pins in a column -> vertical bus, symbol below (or above) the column
            self.sh.wire(xs[0], ys[0], xs[0], ys[-1])
            return self.tap(xs[0], ys[-1] if down else ys[0], net, tail)
        self.sh.wire(xs[0], ys[0], xs[-1], ys[0])   # pins in a row -> horizontal bus, symbol at the far end
        return self.tap(xs[-1], ys[0], net, tail, direction)

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

    def wrap(s, n=185):
        """split a long note into page-wide lines so nothing runs off the right edge"""
        out, cur = [], ""
        for w in s.split(" "):
            if cur and len(cur) + 1 + len(w) > n:
                out.append(cur)
                cur = w
            else:
                cur = w if not cur else cur + " " + w
        if cur:
            out.append(cur)
        return out

    notes = []
    for s in [
        "Dev board: Jinhua #40729, ESP32-S3-DevKitC-1 v1.1 pin order (Espressif user guide). 3V3 pins NOT connected (dev board LDO must not fight the carrier's AMS1117).",
        "Strapping pins IO0/IO45/IO46 left open; IO3 is unused as well (v0.7: it was DIO8 — the strapping question is closed by not using it). IO35-37 (octal PSRAM) and IO48 (on-board WS2812) unused.",
        "GPIO map v0.7 (re-spec 8.2, interface contract): IO41 DDS_FSYNC, IO42 DDS_PSEL, IO40 TX_EN, IO8 RX_BLANK, IO9/IO14 HB_IN1/HB_IN2, IO47 FET_GATE. DIO1-8 and RELAY1-4 moved to the TCA9535 I2C expander (B5), which frees IO4/6/7/15 to the expansion header.",
        "I2C addresses: TCA9535 GPIO expander 0x20 (A0 = A1 = A2 = GND, B5), Si5351A clock generator 0x60, OLED 0x3C. 400 kHz, 4.7 k pull-ups here; Qwiic J4 inside the box and a second Qwiic on the front panel (through the link).",
        "Socket row spacing 25.4 mm ASSUMED from the 28 mm-wide clone (HANDOVER 2026-09-05) — MEASURE a #40729 before ordering (docs/design-decisions.md D-12).",
        "SPI2 on IO_MUX pins: 33 R series at the source on SCLK/MOSI (here) and on SDO at the ADC (B1). All inter-sheet signals are global labels; rails are power symbols.",
    ]:
        notes += wrap(s)
    sheet_frame(sh, "BASE", "BASE — ESP32-S3 dev-board socket, I2C, expansion header, star point", notes)
    # Layout rules (2026-09-17 spacing rework): every ground symbol stands upright at the end of its own
    # stub, adjacent ground pins share one comb, rails leave a connector sideways then turn up, and no wire
    # crosses a label.  Checked by scripts/sch_check.py and by the SVG render.

    # ---------------- GPIO map v0.7 (the interface contract lives on this sheet) ----------------
    gpio07 = [["GPIO", "Net", "Function", "Block"],
              ["12 / 11 / 13", "SPI_SCLK/MOSI/MISO", "SPI2 on IO_MUX, 33 R at source", "base"],
              ["10 / 5", "CS_ADC / CS_DAC", "ADS8688 /CS; DAC8563 /SYNC", "B1 / B3"],
              ["1 / 2", "I2C_SDA / I2C_SCL", "400 kHz: 0x20, 0x60, 0x3C", "base"],
              ["16 / 17", "OPTO_IN1 / 2", "panel opto outputs, active LOW", "panel"],
              ["18 / 21", "FAST_OUT1 / 2", "74HCT125 -> 49.9 R -> panel link", "B5"],
              ["38 / 39", "TRIG_IO / TRIG_DIR", "74LVC1T45 (1 = out to the SMA)", "B5"],
              ["41 / 42", "DDS_FSYNC / DDS_PSEL", "AD9834 sync / phase select", "NMR TX"],
              ["40 / 47", "TX_EN / FET_GATE", "OPA564 enable; polarizer FET", "TX / C_SW"],
              ["8", "RX_BLANK", "receiver blanking switch", "NMR RX"],
              ["9 / 14", "HB_IN1 / HB_IN2", "DRV8871 field-cycling bridge", "C_SW"],
              ["4 / 6 / 7 / 15", "GPIO4/6/7/15", "freed -> expansion header J5", "base"],
              ["43 / 44", "GPIO43 / GPIO44", "LED_WIFI/ACT via JP1/JP2; hdr", "base"],
              ["expander", "DIO1-8, MOD OUT 1-7", "P00-P07 -> 541; P10-P13/P15-P17 -> panel", "B5"],
              ["0/45/46, 3, 48", "-", "strapping / unused / PSRAM 35-37", "-"]]
    sh.text("GPIO map v0.7 (re-spec 8.2) — interface contract", 14, 48, 1.5, True)
    sh.table(14, 50, gpio07, [20, 28, 48, 12], 1.2)

    # ---------------- dev-board sockets -------------------------------------------------
    J1 = c.place("J1", "DEVKIT_SOCKET_J1", 120, 140, 0, value="DevKit J1 (left row)")
    J2 = c.place("J2", "DEVKIT_SOCKET_J3", 190, 140, 0, value="DevKit J3 (right row)")
    sh.box(129, 108, 181, 172, None)
    for k, s in enumerate(["ESP32-S3-DevKitC-1 /", "Jinhua #40729, plugged in;", "the USB-C ports face the",
                           "rear / power edge.", "", "antenna u.FL -> pigtail ->", "rear SMA bulkhead"]):
        if s:
            sh.text(s, 131, 114 + k * 3.6, 1.4)
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
            continue                      # the two supply pins are wired below, clear of the signal labels
        elif net in ("MOSI_MCU", "SCLK_MCU", "RST"):
            c.label_pin(J1, pin, net, 5.08)
        else:
            c.glabel_pin(J1, pin, net, 5.08)
    # J1 pins 21/22: +5V_RAW turns up well clear of the label column, GND turns down below the socket
    c.pwr_L(J1, 21, "+5V_RAW", 25.4, 7.62)
    c.pwr_L(J1, 22, "GND", 12.7, 5.08)
    for pin, net in j3nets.items():
        if net is None:
            c.nc_pin(J2, pin)
        elif net == "GND":
            continue
        else:
            c.glabel_pin(J2, pin, net, 5.08)
    # J3 grounds: pin 1 on its own stub above the label column, pins 21/22 on one comb below it
    c.pwr_L(J2, 1, "GND", 22.86, 5.08)
    c.comb(J2, [21, 22], "GND", out=22.86, tail=5.08)
    sh.text("IO0, IO45, IO46 = strapping (open); IO3 unused (v0.7)", 150, 180, 1.2)
    sh.text("IO35-37 = octal PSRAM, IO48 = on-board RGB LED", 150, 183.5, 1.2)

    # SPI source series resistors (33 R): SCLK_MCU -> R1 -> SPI_SCLK, MOSI_MCU -> R2 -> SPI_MOSI
    for k, (ref, net_in, net_out, y) in enumerate([("R1", "SCLK_MCU", "SPI_SCLK", 192), ("R2", "MOSI_MCU", "SPI_MOSI", 204)]):
        r = c.place(ref, "R0603_33", 60, y, 90)
        r.field_pos["Reference"] = (56.19, y - 3.3, 270, "left bottom")
        r.field_pos["Value"] = (56.19, y + 4.3, 270, "left bottom")
        e1 = sh.stub(r, 1, 3.81)
        sh.label(net_in, e1[0], e1[1], 180)
        e2 = sh.stub(r, 2, 3.81)
        sh.label(net_out, e2[0], e2[1], 0, "global")
    sh.text("33 R source termination for the 80 MHz-capable SPI2 lines (practices 14)", 30, 214, 1.2)
    # RST test point (rotated so its label reads horizontally beside the symbol, not across it)
    tp = c.place("TP1", "TestPoint", 60, 224, 90)
    tp.field_pos["Reference"] = (55.5, 220, 270, "left bottom")
    c.label_pin(tp, 1, "RST", 5.08)
    # ---------------- I2C pull-ups ------------------------------------------------------
    for k, (ref, net) in enumerate([("R3", "I2C_SDA"), ("R4", "I2C_SCL")]):
        r = c.place(ref, "R0603_4R7k", 250 + k * 12.7, 76, 0)
        c.pwr_pin(r, 1, "+3V3", 2.54)
        e = sh.stub(r, 2, 3.81)
        sh.label(net, e[0], e[1], 270, "global")
    sh.text("I2C 400 kHz pull-ups (OLED 0x3C + Qwiic J4 inside + the panel Qwiic)", 240, 60, 1.2)
    # ---------------- Qwiic connector ------------------------------------------------------
    # v0.8: the second Qwiic (J3, left edge) moved to the front panel, where a sensor can be
    # plugged in from the front; J4 stays inside the box for an internal module.
    # Drawn with its pins to the left (rot 180) so the +3V3 leg can rise clear of the ground stubs.
    j = c.place("J4", "QWIIC_SM04B-SRSS", 270, 120, 180)
    c.comb(j, [5, 6], "GND", out=25.4, tail=2.54)   # the two shell pins, one comb
    c.pwr_L(j, 1, "GND", 25.4, 5.08)
    c.pwr_L(j, 2, "+3V3", 33.02, 10.16)
    c.glabel_pin(j, 3, "I2C_SDA", 7.62)
    c.glabel_pin(j, 4, "I2C_SCL", 7.62)
    sh.text("Qwiic J4 (inside the box)", 246, 140, 1.2)
    # ---------------- expansion header J5 (2x10) -------------------------------------------
    J5 = c.place("J5", "HDR_2x10_MALE", 330, 110, 0)
    # D-17 v0.7: pins 16/17 (AUX_HDR, COND_OUT2 — the OPT chain is replaced by the NMR receiver) and the two
    # spares 19/20 now carry the four GPIO freed by the expander.
    exp = {1: "+3V3", 2: "+5V_RAW", 3: "+12V", 4: "-12V", 5: "GND", 6: "GND", 7: "SPI_SCLK", 8: "SPI_MOSI", 9: "SPI_MISO", 10: "GND",
           11: "I2C_SDA", 12: "I2C_SCL", 13: "TRIG_IO", 14: "GPIO43", 15: "GPIO44", 16: "GPIO4", 17: "GPIO6", 18: "AGND", 19: "GPIO7", 20: "GPIO15"}
    # stub out / leg: a pin further down the connector keeps its symbol clear of the pins above it
    legs = {1: (12.7, 7.62), 3: (20.32, 12.7), 5: (27.94, 5.08),
            2: (12.7, 7.62), 4: (35.56, 5.08), 6: (30.48, 5.08), 10: (25.4, 5.08), 18: (35.56, 5.08)}
    for pin, net in exp.items():
        if net is None:
            c.nc_pin(J5, pin)
        elif pin in legs:
            c.pwr_L(J5, pin, net, legs[pin][0], legs[pin][1])
        else:
            c.glabel_pin(J5, pin, net, 7.62)
    exp_rows = [["Pins", "Signals (D-17, v0.7)"],
                ["1-6", "+3V3  +5V_RAW  +12V  -12V  GND  GND"],
                ["7-12", "SPI_SCLK  SPI_MOSI  SPI_MISO  GND  I2C_SDA  I2C_SCL"],
                ["13-18", "TRIG_IO  GPIO43  GPIO44  GPIO4  GPIO6  AGND"],
                ["19-20", "GPIO7  GPIO15"]]
    sh.text("Expansion header J5 (2x10), pinout D-17 v0.7:", 287, 137, 1.2)
    sh.text("the four GPIO freed by the expander (4/6/7/15) took pins 16/17/19/20", 287, 140.5, 1.2)
    sh.table(287, 143, exp_rows, [14, 92], 1.3)
    # ---------------- panel LED links ----------------------------------------------------
    for k, (ref, a, b) in enumerate([("JP1", "GPIO43", "LED_WIFI"), ("JP2", "GPIO44", "LED_ACT")]):
        jp = c.place(ref, "SolderJumper_2_Bridged", 270, 170 + k * 15.24, 0)
        e = sh.stub(jp, 1, 3.81)
        sh.label(a, e[0], e[1], 180, "global")
        e = sh.stub(jp, 2, 3.81)
        sh.label(b, e[0], e[1], 0, "global")
    sh.text("Panel LED drive: bridged by default; open JP1 when the OPT chain uses GPIO43 as CS,", 232, 200, 1.2)
    sh.text("JP2 when the TCXO option feeds GPIO44", 232, 203.5, 1.2)
    # ---------------- star point -----------------------------------------------------------
    nt = c.place("NT1", "NetTie_2", 330, 225, 0)
    c.pwr_L(nt, 1, "AGND", 7.62, 5.08)
    c.pwr_L(nt, 2, "GND", 7.62, 5.08)
    sh.text("The ONLY AGND-GND join (net tie NT1, copper only).", 300, 240, 1.3, True)
    sh.text("Placed at the B1/BASE boundary.", 300, 243.5, 1.3, True)
    # power flags for the grounds (no power_out pin drives GND/AGND): flag above the link, symbol below it
    for k, net in enumerate(["GND", "AGND"]):
        x0 = 240 + k * 35.56
        sh.wire(x0, 225, x0 + 10.16, 225)
        c.tap(x0, 225, "PWR_FLAG")
        c.tap(x0 + 10.16, 225, net)
    sh.text("PWR_FLAGs: GND and AGND are references", 240, 210, 1.2)
    sh.text("without a power_out driver", 240, 213.5, 1.2)
    # ---------------- mechanical --------------------------------------------------------------
    for k in range(4):
        c.place("H%d" % (k + 1), "MountingHole", 40 + k * 12.7, 250, 0)
    for k in range(3):
        c.place("FID%d" % (k + 1), "Fiducial", 100 + k * 12.7, 250, 0)
    sh.text("4 x M3 mounting holes (4 mm from the corners) and 3 assembly fiducials", 40, 262, 1.2)
    # test points: the rail ones point up (symbol above the pad), the ground one down
    for k, (ref, net) in enumerate([("TP2", "GND"), ("TP3", "+3V3"), ("TP4", "+5V_RAW")]):
        tp = c.place(ref, "TestPoint", 170 + k * 20, 250, 0 if net == "GND" else 180)
        c.pwr_pin(tp, 1, net, 2.54)
    sh.text("Rail test points", 170, 262, 1.2)
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
    # Layout rules (2026-09-17 spacing rework): a rail symbol sits on its own stub ABOVE a bus, never mid-wire;
    # a ground symbol sits on its own stub with nothing beneath; adjacent ground pins share one comb; passives on a
    # 10.16 mm pitch; a wire never passes through a symbol.  Checked by scripts/sch_check.py.

    def entry(n, dref, cref, uref):
        """fused node n -> TVS + 10 uF -> LM66100 -> +5V_RAW (one per input)"""
        D = c.place(dref, "SMF5.0A", 85, n[1] + 12.7, 270)      # rot 270: pin 1 (K) at the TOP -> node, pin 2 (A) at the bottom -> GND
        Cc = c.place(cref, "C0805_10uF", 95, n[1] + 12.7, 0)
        U = c.place(uref, "LM66100DCKR", 120, n[1] + 2.54, 0)
        vin = U.pin_pos(1)
        assert abs(vin[1] - n[1]) < 1e-6, (uref, vin, n)
        sh.wire(n[0], n[1], vin[0], vin[1])
        c.tap(105, n[1], "PWR_FLAG")     # the fused node has no power-output pin: flag it (ERC)
        for part in (D, Cc):
            t = part.pin_pos(1)
            sh.wire(t[0], t[1], t[0], n[1])
            c.pwr_pin(part, 2, "GND")
        c.pwr_pin(U, 3, "GND", 2.54)   # CE low = enabled
        c.pwr_pin(U, 2, "GND")
        c.pwr_pin(U, 5, "GND", 2.54)   # ST not used -> GND per datasheet
        c.nc_pin(U, 4)
        out = sh.stub(U, 6, 5.08)
        c.tap(out[0], out[1], "+5V_RAW")
        return U

    # ---------------- USB-C ----------------------------------------------------------------
    J = c.place("J201", "USB-C-16P-2MD-073", 40, 80, 0)
    vb1 = sh.stub(J, "A4B9", 5.08)
    vb2 = sh.stub(J, "B4A9", 5.08)
    sh.wire(vb1[0], vb1[1], vb2[0], vb2[1])
    F1 = c.place("F201", "FUSE_1812L150", 70, vb1[1], 90)
    sh.wire(vb1[0], vb1[1], F1.pin_pos(1)[0], F1.pin_pos(1)[1])
    entry(F1.pin_pos(2), "D201", "C203", "U201")
    # D+/D- pairs
    for pins, net in ((("A6", "B6"), "USB_DP"), (("A7", "B7"), "USB_DN")):
        e1 = sh.stub(J, pins[0], 5.08)
        e2 = sh.stub(J, pins[1], 5.08)
        sh.wire(e1[0], e1[1], e2[0], e2[1])
        sh.label(net, e2[0], e2[1], 0, "global")
    c.nc_pin(J, "A8")
    c.nc_pin(J, "B8")
    # CC pull-downs (5.1 k = UFP sink): CC1 runs past CC2's resistor, each resistor hangs from its own stub end
    for pin, xr, ref in (("A5", 76.2, "R201"), ("B5", 63.5, "R202")):
        p = J.pin_pos(pin)
        sh.wire(p[0], p[1], xr, p[1])
        r = c.place(ref, "R0603_5R1k", xr, p[1] + 3.81, 0)   # pin 1 exactly on the stub end
        c.pwr_pin(r, 2, "GND")
    # shield + GND pins: one comb, one GND symbol below the connector
    c.comb(J, ["13", "14", "A1B12", "B1A12"], "GND", out=5.08, tail=5.08)
    sh.text("CC1/CC2 5.1k = UFP sink, 5 V. Shield pads to GND directly (no chassis).", 30, 118, 1.2)
    # ---------------- DC jack ----------------------------------------------------------------
    J2 = c.place("J202", "DC005-T20", 40, 160, 0)
    tip = sh.stub(J2, 1, 5.08)
    F2 = c.place("F202", "FUSE_1812L150", 70, tip[1], 90)
    sh.wire(tip[0], tip[1], F2.pin_pos(1)[0], F2.pin_pos(1)[1])
    entry(F2.pin_pos(2), "D202", "C204", "U202")
    c.pwr_L(J2, 2, "GND", 5.08, 5.08)
    c.nc_pin(J2, 3)
    sh.text("Jack: 5 V DC, centre +, 5.5/2.1 mm, 1.5-3 A. Switch pin unused.", 30, 185, 1.2)
    # ---------------- ORed node -> +5V_RAW with bulk caps + LED ---------------------------------
    x0, yb = 170, 100
    cols = [x0 + 7.62, x0 + 17.78, x0 + 33.02]
    sh.wire(x0, yb, cols[-1], yb)
    c.flag(x0, yb)                       # PWR_FLAG at the bus end: the ideal diodes drive the rail
    C1 = c.place("C201", "C1206_22uF", cols[0], yb + 8.89, 0)
    C2 = c.place("C202", "C0603_100nF", cols[1], yb + 8.89, 0)
    for cap in (C1, C2):
        t = cap.pin_pos(1)
        sh.wire(t[0], t[1], t[0], yb)
        c.pwr_pin(cap, 2, "GND")
    c.tap(x0 + 25.4, yb, "+5V_RAW")
    R9 = c.place("R209", "R0603_1k", cols[2], yb + 8.89, 0)
    sh.wire(R9.pin_pos(1)[0], R9.pin_pos(1)[1], R9.pin_pos(1)[0], yb)
    Dl = c.place("D203", "LED_GREEN_0805", cols[2], yb + 20.32, 90)   # rot 90: A (pin 2) at the top, K (pin 1) at the bottom
    sh.wire(R9.pin_pos(2)[0], R9.pin_pos(2)[1], Dl.pin_pos(2)[0], Dl.pin_pos(2)[1])
    c.pwr_pin(Dl, 1, "GND")
    sh.text("+5V_RAW rail (both LM66100 outputs): bulk 22 uF + 100 nF, green LED (2.9 mA); PWR_FLAG = ideal diodes drive the rail", 160, 92, 1.2)
    # ---------------- +3V3 LDO ----------------------------------------------------------------
    U4 = c.place("U204", "AMS1117-3.3", 240, 105, 0)
    vin = U4.pin_pos(3)
    sh.wire(vin[0] - 10.16, vin[1], vin[0], vin[1])
    c.tap(vin[0] - 10.16, vin[1], "+5V_RAW")
    C13 = c.place("C213", "C0805_10uF", vin[0] - 5.08, vin[1] + 8.89, 0)
    sh.wire(C13.pin_pos(1)[0], C13.pin_pos(1)[1], C13.pin_pos(1)[0], vin[1])
    c.pwr_pin(C13, 2, "GND")
    c.pwr_pin(U4, 1, "GND", 5.08)      # past the value text
    c.nc_pin(U4, 4)   # tab duplicate of VOUT: joined on the PCB by the footprint
    vo = U4.pin_pos(2)
    ocols = [vo[0] + 5.08, vo[0] + 15.24, vo[0] + 25.4]
    sh.wire(vo[0], vo[1], ocols[-1], vo[1])
    C14 = c.place("C214", "C1206_22uF", ocols[0], vo[1] + 8.89, 0)
    C15 = c.place("C215", "C0603_100nF", ocols[1], vo[1] + 8.89, 0)
    for cap in (C14, C15):
        t = cap.pin_pos(1)
        sh.wire(t[0], t[1], t[0], vo[1])
        c.pwr_pin(cap, 2, "GND")
    c.tap(vo[0] + 10.16, vo[1], "+3V3")
    R10 = c.place("R210", "R0603_1k", ocols[2], vo[1] + 8.89, 0)
    sh.wire(R10.pin_pos(1)[0], R10.pin_pos(1)[1], R10.pin_pos(1)[0], vo[1])
    D4 = c.place("D204", "LED_GREEN_0805", ocols[2], vo[1] + 20.32, 90)
    sh.wire(R10.pin_pos(2)[0], R10.pin_pos(2)[1], D4.pin_pos(2)[0], D4.pin_pos(2)[1])
    c.pwr_pin(D4, 1, "GND")
    sh.text("+3V3: AMS1117-3.3 (SOT-223), 22 uF ceramic out (tantalum 3216 drop-in if needed), pin 4 = tab (same VOUT net on the footprint)", 200, 138, 1.2)
    # ---------------- isolated modules ---------------------------------------------------------
    for k, (ref, sign, ymod) in enumerate([("PS201", "+", 152), ("PS202", "-", 207)]):
        ps = c.place(ref, "B0512S-2WR3", 240, ymod, 0)
        pin1 = ps.pin_pos(1)
        fb = c.place("FB20%d" % (1 + k), "FB0603_600R", 210, pin1[1], 90)
        e = sh.stub(fb, 1, 7.62)
        c.tap(e[0], e[1], "+5V_RAW")
        sh.wire(fb.pin_pos(2)[0], fb.pin_pos(2)[1], pin1[0], pin1[1])
        cin = c.place("C21%d" % (6 + k), "C0805_10uF", 220.98, pin1[1] + 8.89, 0)
        sh.wire(cin.pin_pos(1)[0], cin.pin_pos(1)[1], cin.pin_pos(1)[0], pin1[1])
        c.pwr_pin(cin, 2, "GND")
        c.tap(220.98, pin1[1], "PWR_FLAG")         # filtered input node is driven (flag above the input cap column)
        c.pwr_L(ps, 2, "GND", 2.54, 5.08)           # -Vin: out, then down to GND
        if sign == "+":
            fbo = c.place("FB203", "FB0603_600R", 275, ps.pin_pos(6)[1], 90)
            sh.wire(ps.pin_pos(6)[0], ps.pin_pos(6)[1], fbo.pin_pos(1)[0], fbo.pin_pos(1)[1])
            c.pwr_L(ps, 4, "AGND", 2.54, 5.08)      # -Vo -> AGND below the line
            node = fbo.pin_pos(2)
            parts = [("C207", "C1206_22uF"), ("C209", "C0603_100nF"), ("R203", "R0603_2R2k"), ("R204", "R0603_2R2k"), ("R205", "R0603_2R2k"), ("R211", "R0603_4R7k")]
            rail, led_ref, led_rot, led_top_pin, led_gnd_pin = "+12V", "D205", 90, 2, 1     # LED: A (pin 2) at the top toward the resistor, K down to AGND
            note = "+12V: FB + 22 uF + 100 nF at the module; 3 x 2.2k = 16 mA bleeder guarantees the 10 % minimum load with 78L05 load included"
        else:
            e6 = sh.stub(ps, 6, 2.54)               # +Vo -> AGND drawn above the line
            c.tap(e6[0], e6[1], "AGND", 5.08, "up")
            fbo = c.place("FB204", "FB0603_600R", 275, ps.pin_pos(4)[1], 90)
            sh.wire(ps.pin_pos(4)[0], ps.pin_pos(4)[1], fbo.pin_pos(1)[0], fbo.pin_pos(1)[1])
            node = fbo.pin_pos(2)
            parts = [("C206", "C1206_22uF"), ("C208", "C0603_100nF"), ("R206", "R0603_2R2k"), ("R207", "R0603_2R2k"), ("R208", "R0603_2R2k"), ("R212", "R0603_4R7k")]
            rail, led_ref, led_rot, led_top_pin, led_gnd_pin = "-12V", "D206", 270, 1, 2    # LED: K (pin 1) at the top toward -12V, A down to AGND
            note = "-12V: module #2 with +Vo on AGND; FB in the -Vo line; 3 x 2.2k bleeder (16 mA) + LED keep the 10 % minimum load"
        mcols = [node[0] + 7.62 + i * 10.16 for i in range(len(parts))]
        bus_end = mcols[-1] + 7.62
        sh.wire(node[0], node[1], bus_end, node[1])
        c.tap(mcols[0], node[1], "PWR_FLAG")       # above the first passive column, clear of the FB text
        last = None
        for (pref, plib), xc in zip(parts, mcols):
            part = c.place(pref, plib, xc, node[1] + 8.89, 0)
            t = part.pin_pos(1)
            sh.wire(t[0], t[1], t[0], node[1])
            if pref in ("R211", "R212"):
                last = part
            else:
                c.pwr_pin(part, 2, "AGND")
        c.tap(bus_end, node[1], rail)
        dl = c.place(led_ref, "LED_GREEN_0805", mcols[-1], node[1] + 20.32, led_rot)
        sh.wire(last.pin_pos(2)[0], last.pin_pos(2)[1], dl.pin_pos(led_top_pin)[0], dl.pin_pos(led_top_pin)[1])
        c.pwr_pin(dl, led_gnd_pin, "AGND")
        sh.text(note, 200, ymod + 35, 1.2)
        if sign == "+":
            sh.text("Isolated 2 W modules: input 4.5-5.5 V, 454 mA full load, ripple 80 mVp-p max, Cout <= 560 uF, 1.5 kVDC isolation (YLPTEC datasheet)", 200, ymod + 40, 1.2)
    # ---------------- +5VA LDO ------------------------------------------------------------------
    U3 = c.place("U203", "78L05G-AB3-R", 350, 105, 0)
    vin = U3.pin_pos(3)
    sh.wire(vin[0] - 10.16, vin[1], vin[0], vin[1])
    c.tap(vin[0] - 10.16, vin[1], "+12V")
    C10 = c.place("C210", "C0603_1uF", vin[0] - 5.08, vin[1] + 8.89, 0)
    sh.wire(C10.pin_pos(1)[0], C10.pin_pos(1)[1], C10.pin_pos(1)[0], vin[1])
    c.pwr_pin(C10, 2, "AGND")
    c.pwr_pin(U3, 2, "AGND", 5.08)     # past the value text
    vo = U3.pin_pos(1)
    sh.wire(vo[0], vo[1], vo[0] + 20.32, vo[1])
    C11 = c.place("C211", "C0805_10uF", vo[0] + 5.08, vo[1] + 8.89, 0)
    C12 = c.place("C212", "C0603_100nF", vo[0] + 15.24, vo[1] + 8.89, 0)
    for cap in (C11, C12):
        t = cap.pin_pos(1)
        sh.wire(t[0], t[1], t[0], vo[1])
        c.pwr_pin(cap, 2, "AGND")
    c.tap(vo[0] + 10.16, vo[1], "+5VA")
    sh.text("+5VA: 78L05G from +12V (dropout 1.7 V), ADC/DAC analog supply, AGND-referenced; 0.12 W at 17 mA", 296, 128, 1.2)
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
    # Layout rules (2026-09-17 spacing rework): channels on a 21.59 mm pitch so a clamp never reaches the next
    # channel; the eight AIN_nGND pins share ONE comb whose bus runs well to the left of the AIN labels; the
    # reference network breaks out downward-left (upper pin = further left, so no wire crosses another); rails
    # go up, grounds go down, every power symbol sits on its own stub.  Checked by scripts/sch_check.py.
    chan_pins = ["12", "14", "16", "18", "21", "23", "25", "27"]
    gnd_pins = ["13", "15", "17", "19", "20", "22", "24", "26"]
    X_IN, X_JP, X_R, X_C, X_D, X_LBL = 29.21, 45.72, 85.09, 96.52, 121.92, 149.86
    def flat_text(inst, cx, cy, where="split"):
        """reference / value of a rot-90 passive drawn horizontally (KiCad adds the symbol rotation to the
        stored angle, so 270 + 90 = upright): both above, both below, or reference above and value below."""
        if where == "above":
            ref, val = (cx - 3.81, cy - 3.3, "left bottom"), (cx - 11.43, cy - 3.3, "left bottom")
        elif where == "below":
            ref, val = (cx - 3.81, cy + 3.3, "left top"), (cx - 11.43, cy + 3.3, "left top")
        else:
            ref, val = (cx - 3.81, cy - 3.3, "left bottom"), (cx - 3.81, cy + 3.3, "left top")
        inst.field_pos["Reference"] = (ref[0], ref[1], 270, ref[2])
        inst.field_pos["Value"] = (val[0], val[1], 270, val[2])

    # ---------------- 8 input networks, one row each ----------------------------------------
    for i in range(8):
        y = 54.61 + i * 21.59
        if i >= 6:                      # AI7/AI8: solder jumper to the OPT chain, common pin on the row line
            jp = c.place("JP10%d" % (i - 5), "SolderJumper_3_Bridged12", X_JP, y - 3.81, 0)
            e = sh.stub(jp, 1, 5.08)
            sh.label("AI%d" % (i + 1), e[0], e[1], 180, "global")
            e = sh.stub(jp, 3, 3.81)
            sh.label("COND_OUT%d" % (i - 5), e[0], e[1], 0, "global")
            x_in = jp.pin_pos(2)[0]
        else:
            x_in = X_IN
            sh.label("AI%d" % (i + 1), x_in, y, 180, "global")
        sh.wire(x_in, y, X_R - 3.81, y)
        r = c.place("R1%02d" % (11 + i), "R0603_1k", X_R, y, 90)
        flat_text(r, X_R, y)
        node = r.pin_pos(2)
        sh.wire(node[0], node[1], X_LBL, y)
        sh.label("AIN%d" % (i + 1), X_LBL, y, 0)
        cap = c.place("C1%02d" % (11 + i), "C0603_1nF", X_C, y + 7.62, 0)   # reference text clear of the row wire
        sh.wire(X_C, cap.pin_pos(1)[1], X_C, y)
        c.pwr_pin(cap, 2, "AGND")
        d = c.place("D1%02d" % (11 + i), "BAV99", X_D, y + 8.89, 180)   # COM up, A1 right (-12V), K2 left (+12V)
        sh.wire(X_D, d.pin_pos(3)[1], X_D, y)
        e = sh.stub(d, 1, 2.54)        # rail symbols upright (horizontal ones rotate their text onto BAV99)
        c.power_at(e[0], e[1], "-12V")
        e = sh.stub(d, 2, 2.54)
        c.power_at(e[0], e[1], "+12V")
    sh.text("8 identical input networks: 1 k -> node (1 nF to AGND, BAV99 clamps to the rails) -> AINn -> ADC channel per the D-19 table", 25.4, 236.22, 1.3)
    # ---------------- ADS8688 -----------------------------------------------------------------
    U = c.place("U101", "ADS8688IDBTR", 274.32, 119.38, 0)
    U.field_pos["Value"] = (288.29, 158.75, 0, "left top")   # off the bottom pin numbers
    for i in range(8):                  # AINn labels on the channel pins
        e = sh.stub(U, chan_pins[i], 12.7)
        sh.label("AIN%d" % (i + 1), e[0], e[1], 180)
    c.comb(U, gnd_pins, "AGND", out=30.48, tail=2.54)   # one AGND bus left of the labels, one symbol below it
    # AUX unused: both pins on one short bus, the symbol parked left of the reference wiring
    e10 = sh.stub(U, "10", 5.08)
    e11 = sh.stub(U, "11", 5.08)
    sh.wire(e10[0], e10[1], e11[0], e11[1])
    sh.wire(e10[0], e10[1], 243.84, e10[1])
    c.power_at(243.84, e10[1], "AGND", 270)
    # reference network below-left: REFIO breaks out further left than REFCAP so the two never cross
    refio = sh.stub(U, "5", 40.64)
    sh.wire(refio[0], refio[1], refio[0], 165.1)
    C6 = c.place("C106", "C0805_10uF", refio[0], 168.91, 0)
    c.pwr_pin(C6, 2, "AGND")
    refcap = sh.stub(U, "7", 27.94)
    sh.wire(refcap[0], refcap[1], refcap[0], 165.1)
    C4 = c.place("C104", "C0603_1uF", refcap[0], 168.91, 0)
    C5 = c.place("C105", "C1206_22uF", refcap[0] + 15.24, 168.91, 0)
    sh.wire(C4.pin_pos(1)[0], 165.1, C5.pin_pos(1)[0], 165.1)
    for cap in (C4, C5):
        c.pwr_pin(cap, 2, "AGND")
    c.pwr_pin(U, "6", "AGND", 5.08)
    c.pwr_pin(U, "4", "AGND", 10.16)    # REFSEL low = internal reference
    sh.text("REFSEL low = internal 4.096 V reference; REFCAP 1 uF + 22 uF, REFIO 10 uF (ADS8688 datasheet 8.3.3 / 11.1)", 196.85, 190.5, 1.2)
    # supplies: AVDD bus above the chip, 1 uF at each pin + 10 uF bulk hanging off it
    e9 = sh.stub(U, "9", 10.16)
    e30 = sh.stub(U, "30", 10.16)
    y_av = e9[1]
    sh.wire(228.6, y_av, e30[0], y_av)
    for ref, lib, xc in (("C101", "C0603_1uF", 259.08), ("C103", "C0603_1uF", 246.38), ("C102", "C0805_10uF", 233.68)):
        cap = c.place(ref, lib, xc, 76.2, 0)
        sh.wire(xc, cap.pin_pos(1)[1], xc, y_av)
        c.pwr_pin(cap, 2, "AGND")
    c.tap(228.6, y_av, "+5VA", 5.08)
    # DVDD bus to the right of the chip: +3V3 tap, 10 uF + 100 nF to GND
    e34 = sh.stub(U, "34", 15.24)
    sh.wire(e34[0], e34[1], 314.96, e34[1])
    c.tap(289.56, e34[1], "+3V3", 5.08)
    for ref, lib, xc in (("C107", "C0805_10uF", 302.26), ("C108", "C0603_100nF", 314.96)):
        cap = c.place(ref, lib, xc, 71.12, 0)
        sh.wire(xc, cap.pin_pos(1)[1], xc, e34[1])
        c.pwr_pin(cap, 2, "GND")
    sh.text("AVDD 1 uF at pins 9 and 30 + 10 uF bulk; DVDD 10 uF + 100 nF", 228.6, 50.8, 1.2)
    # ---------------- digital side ------------------------------------------------------------
    c.glabel_pin(U, "38", "CS_ADC", 7.62)
    c.glabel_pin(U, "37", "SPI_SCLK", 7.62)
    c.glabel_pin(U, "1", "SPI_MOSI", 7.62)
    e = sh.stub(U, "36", 7.62)          # SDO -> 33 R source resistor, well clear of the label column
    R1 = c.place("R101", "R0603_33", 332.74, e[1], 90)
    flat_text(R1, 332.74, e[1])
    sh.wire(e[0], e[1], R1.pin_pos(1)[0], e[1])
    e2 = sh.stub(R1, 2, 2.54)
    sh.label("SPI_MISO", e2[0], e2[1], 0, "global")
    c.pwr_L(U, "3", "GND", 12.7, 5.08)  # DAISY = GND, symbol on its own leg below the stub
    e = sh.stub(U, "2", 7.62)           # RST/PD: down and out, pull-up on the run, label at the far end
    sh.wire(e[0], e[1], e[0], 119.38)
    sh.wire(e[0], 119.38, 307.34, 119.38)
    sh.wire(307.34, 119.38, 320.04, 119.38)
    sh.label("ADC_RST", 320.04, 119.38, 0)
    R2 = c.place("R102", "R0603_10k", 307.34, 115.57, 0)
    R2.field_pos["Value"] = (310.9, 116.2, 0, "left")
    c.pwr_pin(R2, 1, "+3V3")
    c.nc_pin(U, "35")
    sh.text("RST/PD pulled up to DVDD (10k); firmware may pull it low for reset/power-down", 294.64, 132.08, 1.2)
    # ---------------- bottom grounds ----------------------------------------------------------
    ends = [sh.stub(U, p, 10.16) for p in ("8", "28", "29", "31", "32")]
    y_gb = ends[0][1]
    sh.wire(257.81, y_gb, ends[-1][0], y_gb)
    c.tap(257.81, y_gb, "AGND", 7.62)
    c.pwr_pin(U, "33", "GND", 15.24)
    tp = c.place("TP101", "TestPoint", 330.2, 190.5, 0)
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
    # Layout rules (2026-09-17 spacing rework): the /OE pins alternate with the signal pins, so their comb bus
    # runs left of the input labels; /LDAC and /CLR break out at different depths and both leave downward (one
    # up + one down would have to cross); decoupling columns on a 12.7 mm pitch; every free text clear of the
    # title block and of the right edge.  Checked by scripts/sch_check.py.
    def rail_up(inst, pin, net, length=2.54):
        """rail or ground symbol on an UPWARD stub: the graphic points up, so its value text is pushed
        clear of the bars (the default position puts the text inside them)."""
        e = sh.stub(inst, pin, length)
        down_type = net in ("GND", "AGND", "-12V")
        sym = c.power_at(e[0], e[1], net, 180 if down_type else 0)
        if down_type:
            sym.field_pos["Value"] = (e[0], e[1] - 4.83, 0, None)
        return e

    def flat_text(inst, cx, cy, where="split"):
        """reference / value of a rot-90 passive drawn horizontally (KiCad adds the symbol rotation to the
        stored angle, so 270 + 90 = upright): both above, both below, or reference above and value below."""
        if where == "above":
            ref, val = (cx - 3.81, cy - 3.3, "left bottom"), (cx - 11.43, cy - 3.3, "left bottom")
        elif where == "below":
            ref, val = (cx - 3.81, cy + 3.3, "left top"), (cx - 11.43, cy + 3.3, "left top")
        else:
            ref, val = (cx - 3.81, cy - 3.3, "left bottom"), (cx - 3.81, cy + 3.3, "left top")
        inst.field_pos["Reference"] = (ref[0], ref[1], 270, ref[2])
        inst.field_pos["Value"] = (val[0], val[1], 270, val[2])

    # ---------------- 74HCT125 level shifter ---------------------------------------------------
    X2, Y2 = 78.74, 106.68
    U2 = c.place("U302", "74HCT125PW", X2, Y2, 0)
    U2.field_pos["Value"] = (62.23, 127.0, 0, "left top")      # off the GND stub below the body
    U2.field_pos["Reference"] = (62.23, 89.41, 0, "left bottom")   # off the VCC pin number
    for pin, net in (("2", "SPI_SCLK"), ("5", "SPI_MOSI"), ("9", "CS_DAC")):
        c.glabel_pin(U2, pin, net, 7.62)
    for pin, net in (("3", "DAC_SCLK"), ("6", "DAC_DIN"), ("8", "DAC_SYNC")):
        c.label_pin(U2, pin, net, 7.62)
    c.nc_pin(U2, "11")
    c.comb(U2, ["1", "4", "10", "12", "13"], "GND", out=25.4, tail=7.62)   # 4 x /OE + the unused 4A input
    c.pwr_pin(U2, "14", "+5V_RAW", 5.08)
    c.pwr_pin(U2, "7", "GND", 5.08)
    C8 = c.place("C308", "C0603_100nF", 101.6, 76.2, 0)
    c.pwr_pin(C8, 1, "+5V_RAW")
    c.pwr_pin(C8, 2, "GND")
    sh.text("SPI -> 5 V level shift for the DAC (three channels, 4th input grounded)", 44.45, 146.05, 1.2)
    # ---------------- DAC8563 -------------------------------------------------------------------
    X1, Y1 = 165.1, 105.41
    U1 = c.place("U301", "DAC8563SDGSR", X1, Y1, 0)
    U1.field_pos["Value"] = (168.91, 121.92, 0, "left top")        # off the bottom pin number
    for pin, net in (("6", "DAC_SYNC"), ("7", "DAC_SCLK"), ("8", "DAC_DIN")):
        c.label_pin(U1, pin, net, 5.08)
    c.pwr_L(U1, "4", "AGND", 20.32, 7.62)       # /LDAC = AGND: out past the labels, then down
    e = sh.stub(U1, "5", 12.7)                  # /CLR: down and out to its pull-up, clear of /LDAC
    sh.wire(e[0], e[1], e[0], 130.81)
    sh.wire(e[0], 130.81, 143.51, 130.81)
    Rc = c.place("R311", "R0603_10k", 147.32, 130.81, 90)   # rot 90: pin 1 (left) = /CLR, pin 2 (right) -> +5VA
    flat_text(Rc, 147.32, 130.81)
    c.pwr_L(Rc, 2, "+5VA", 2.54, 5.08)
    c.pwr_pin(U1, "9", "+5VA", 5.08)
    c.pwr_pin(U1, "3", "AGND", 5.08)
    C2 = c.place("C302", "C0603_100nF", 139.7, 80.01, 0)
    C3 = c.place("C303", "C0805_10uF", 152.4, 80.01, 0)
    for cap in (C2, C3):
        c.pwr_pin(cap, 1, "+5VA")
        c.pwr_pin(cap, 2, "AGND")
    # VREF: 1 uF close to the pin, test point on the line, global label at the far end
    e = sh.stub(U1, "10", 5.08)
    sh.wire(e[0], e[1], 187.96, e[1])
    sh.wire(187.96, e[1], 217.17, e[1])
    sh.label("VREF_DAC", 217.17, e[1], 0, "global")
    C1 = c.place("C301", "C0603_1uF", 187.96, 115.57, 0)
    sh.wire(187.96, C1.pin_pos(1)[1], 187.96, e[1])
    c.pwr_pin(C1, 2, "AGND")
    c.place("TP301", "TestPoint", 204.47, e[1], 180)        # probe hangs below the VREF line
    c.label_pin(U1, "1", "DAC_A", 7.62)
    c.label_pin(U1, "2", "DAC_B", 7.62)
    sh.text("VREF 2.5 V out, 1 uF (>= 150 nF required by the datasheet)", 175.26, 133.35, 1.2)
    # ---------------- two difference amplifiers -------------------------------------------------
    for ch, (unit, dac, out_net, Ya) in enumerate([(1, "DAC_A", "AO1", 90.17), (2, "DAC_B", "AO2", 152.4)]):
        u = c.place("U303", "OPA2192IDR", 299.72, Ya, 0, unit=unit)
        pp, pm, po = ("3", "2", "1") if ch == 0 else ("5", "6", "7")
        plus, minus, out = u.pin_pos(pp), u.pin_pos(pm), u.pin_pos(po)
        # non-inverting: DAC -> R3 10k -> +IN ; R4 40.2k from +IN to AGND
        r3 = c.place("R30%d" % (1 + 4 * ch), "R0603_10k", plus[0] - 12.7, plus[1], 90)
        flat_text(r3, plus[0] - 12.7, plus[1], "above")
        sh.wire(r3.pin_pos(2)[0], plus[1], plus[0], plus[1])
        e = sh.stub(r3, 1, 15.24)
        sh.label(dac, e[0], e[1], 180)
        r4 = c.place("R30%d" % (2 + 4 * ch), "R0603_40R2k", plus[0] - 5.08, plus[1] - 7.62, 0)
        sh.wire(r4.pin_pos(2)[0], r4.pin_pos(2)[1], r4.pin_pos(2)[0], plus[1])
        rail_up(r4, 1, "AGND")
        # inverting: VREF -> R1 10k -> -IN ; R2 40.2k from -IN to OUT, routed below the amplifier
        r1 = c.place("R30%d" % (3 + 4 * ch), "R0603_10k", minus[0] - 25.4, minus[1], 90)
        flat_text(r1, minus[0] - 25.4, minus[1], "below")
        sh.wire(r1.pin_pos(2)[0], minus[1], minus[0], minus[1])
        e = sh.stub(r1, 1, 5.08)
        sh.label("VREF_DAC", e[0], e[1], 180, "global")
        yfb = minus[1] + 12.7                                        # clear of the amplifier's value text
        r2 = c.place("R30%d" % (4 + 4 * ch), "R0603_40R2k", out[0] + 2.54, yfb, 90)
        flat_text(r2, out[0] + 2.54, yfb)
        sh.wire(minus[0] - 2.54, minus[1], minus[0] - 2.54, yfb)     # branch off the R1 wire, no doubled segment
        sh.wire(minus[0] - 2.54, yfb, r2.pin_pos(1)[0], yfb)
        sh.wire(r2.pin_pos(2)[0], yfb, out[0] + 10.16, yfb)
        sh.wire(out[0] + 10.16, yfb, out[0] + 10.16, out[1])
        sh.wire(out[0], out[1], out[0] + 10.16, out[1])
        # 49.9 R back-termination -> AO node -> BAV99 clamp -> label
        rs = c.place("R3%02d" % (9 + ch), "R0603_49R9", out[0] + 20.32, out[1], 90)
        flat_text(rs, out[0] + 20.32, out[1])
        sh.wire(out[0] + 10.16, out[1], rs.pin_pos(1)[0], out[1])
        node = rs.pin_pos(2)
        sh.wire(node[0], node[1], node[0] + 20.32, node[1])
        sh.label(out_net, node[0] + 20.32, node[1], 0, "global")
        d = c.place("D30%d" % (1 + ch), "BAV99", node[0] + 10.16, node[1] + 8.89, 180)
        sh.wire(d.pin_pos(3)[0], d.pin_pos(3)[1], d.pin_pos(3)[0], node[1])
        e = sh.stub(d, 1, 2.54)
        c.power_at(e[0], e[1], "-12V")
        e = sh.stub(d, 2, 2.54)
        c.power_at(e[0], e[1], "+12V")
    # ---------------- OPA2192 power unit and its decoupling --------------------------------------
    U3p = c.place("U303", "OPA2192IDR", 375.92, 121.92, 0, unit=3)
    c.pwr_pin(U3p, "8", "+12V", 5.08)
    c.pwr_pin(U3p, "4", "-12V", 5.08)
    for ref, lib, xc, yc, rail in (("C304", "C0603_100nF", 389.89, 105.41, "+12V"), ("C306", "C0805_10uF", 402.59, 105.41, "+12V"),
                                   ("C305", "C0603_100nF", 389.89, 140.97, "-12V"), ("C307", "C0805_10uF", 402.59, 140.97, "-12V")):
        cap = c.place(ref, lib, xc, yc, 0)
        rail_up(cap, 1, rail)
        c.pwr_pin(cap, 2, "AGND")
    sh.text("OPA2192 supplies +-12 V: 100 nF + 10 uF per rail to AGND", 335.28, 182.88, 1.2)
    sh.text("AO_n = (1+R2/R1) x R4/(R3+R4) x DAC_n - (R2/R1) x VREF = 4.02 x DAC_n - 4.02 x 2.5 V", 245.11, 196.85, 1.3)
    auto_junctions(sh)
    return sh


# ================================================================== B5 DIO/TRIG
def build_b5(root_uuid):
    # A2 (2026-09-17): the eight buffered outputs, the fast outputs, the TRIG chain, the expander and the
    # TCXO option do not fit on A3 with the spacing the rework asks for.
    sh = Sheet("b5_dio_trig", "B5: 8 TTL DIO, 2 fast TTL outs, bidirectional TRIG, TCXO option", "A2", 7, "74AHCT541 x8 with 1 k series; 74HCT125 fast outs with 49.9 R; 74LVC1T45 TRIG with 33 R + BAV99 clamp; DNP TCXO + Schmitt buffer")
    c = Ctx(sh, "B5", 5000)

    def wrap(s, n=260):
        """split a long note into page-wide lines so nothing runs off the right edge"""
        out, cur = [], ""
        for w in s.split(" "):
            if cur and len(cur) + 1 + len(w) > n:
                out.append(cur)
                cur = w
            else:
                cur = w if not cur else cur + " " + w
        if cur:
            out.append(cur)
        return out

    def flat_fields(inst, x, y):
        """ref above / value below a symbol placed at rot 90, drawn horizontally"""
        inst.field_pos["Reference"] = (x - 3.81, y - 3.3, 270, "left bottom")
        inst.field_pos["Value"] = (x - 3.81, y + 4.3, 270, "left bottom")

    notes = []
    for s in [
        "74AHCT541 (TTL-compatible inputs accept 3.3 V) buffers DIO1..8 to 5 V; 1 k series per output limits a shorted output to 5 mA (students!). Outputs are static/slow (kHz): 1 k x 100 pF cable = 100 ns. v0.8: TTL1..8 and FASTTTL1/2 leave on the panel link, not on board-edge terminals.",
        "v0.7: DIO1..8 keep their names but are no longer MCU pins — they come from the TCA9535 I2C expander U505 (address 0x20, A0 = A1 = A2 = GND), P00..P07. The 541 runs at +5V_RAW while the expander drives 3.3 V: the AHCT TTL thresholds (VIH 2.0 V) accept that. v0.7d: P10..P13 and P15..P17 = MODULE OUT 1..7 to the panel link J8 (P10..P13 are the ports the four relay gates used); P14 stays EXP_P14, the Johnson-counter /CLR of the NMR receiver; MODULE OUT 8 is reserved (J8 pin 33 not connected).",
        "74HCT125: FAST_OUT1/2 (MCPWM/RMT) -> 49.9 R series -> the panel link -> the two fast SMAs on the panel; drive +-6 mA rated, so a 50 R termination gives ~1 V: fast outs are for high-impedance TTL loads.",
        "TRIG: 74LVC1T45 A = TRIG_IO (3.3 V), B = 5 V side -> 33 R -> TRIG_5V -> panel SMA; DIR (GPIO39) 1 = output. Into a 50 R termination ~2.4 V typ (beyond the rated 32 mA), 5 V into high-Z. BAV99 clamps B to GND/+5V_RAW.",
        "TCXO option (all DNP): clipped-sine 10 MHz -> 1 nF -> Schmitt buffer biased at VCC/2 -> 74LVC1G17 -> JP501 -> GPIO44 (open JP2 on the base sheet when used). VCONT at 1.65 V from a divider.",
    ]:
        notes += wrap(s)
    sheet_frame(sh, "B5", "B5 — DIGITAL I/O AND TIMING: 8 x 5 V TTL outputs, 2 fast outputs, bidirectional TRIG (panel SMA), 10 MHz TCXO option", notes)
    # Layout rules (2026-09-17 spacing rework): a ground symbol stands upright on its own stub, adjacent
    # ground pins share one comb, the eight series resistors are fanned out to a 10.16 mm column, and no wire
    # crosses another wire or a label.  Checked by scripts/sch_check.py and by the SVG render.

    # ---------------- 74AHCT541: DIO1..8 -> 1 k -> TTL1..8 --------------------------------
    U1 = c.place("U501", "SN74AHCT541PWR", 95, 130, 0)
    for i in range(8):
        c.glabel_pin(U1, str(2 + i), "DIO%d" % (i + 1), 7.62)
    c.comb(U1, ["1", "19"], "GND", out=7.62, tail=5.08)      # OE1 + OE2 tied low on one comb
    c.pwr_pin(U1, "20", "+5V_RAW", 5.08)
    c.pwr_pin(U1, "10", "GND", 5.08)
    xres = 133.35
    for i in range(8):
        px, py = U1.pin_pos(str(18 - i))
        ty = 88.9 + i * 10.16                                 # output rows on a 10.16 mm pitch
        jog = 107.95 + (i if i < 4 else 7 - i) * 2.54         # fan: no two wires cross
        sh.wire(px, py, jog, py)
        sh.wire(jog, py, jog, ty)
        r = c.place("R50%d" % (i + 1), "R0603_1k", xres, ty, 90)
        flat_fields(r, xres, ty)
        sh.wire(jog, ty, r.pin_pos(1)[0], r.pin_pos(1)[1])
        # v0.8: TTL1..8 leave the sheet as GLOBAL labels (they used to end on the J501-J504
        # terminals at the board edge; the terminal strip is on the front panel now).
        e = sh.stub(r, 2, 7.62)
        sh.label("TTL%d" % (i + 1), e[0], e[1], 0, "global")
    c.decouple("C501", "C0603_100nF", 70, 85, "+5V_RAW", "GND")
    # v0.8 (panel rework): the edge terminals J501-J505 are gone. TTL1..TTL8 travel on the
    # panel link (J7) to a 10-way screw-terminal strip on the front panel, which also carries
    # the two GND wires that J505 used to provide.
    sh.text("TTL1..TTL8 leave this sheet as global labels -> panel link J7 -> the 10-way screw-terminal strip", 60, 180, 1.3)
    sh.text("on the front panel (TTL1..8 + 2 x GND). The board-edge terminals J501-J505 are gone (v0.8).", 60, 183.5, 1.3)

    # ---------------- 74HCT125: the two fast outputs --------------------------------------
    U2 = c.place("U502", "74HCT125PW", 270, 105, 0)
    for pin, net in (("2", "FAST_OUT1"), ("5", "FAST_OUT2")):
        c.glabel_pin(U2, pin, net, 7.62)
    # every grounded input and enable on one comb, its bus clear of the two global labels
    c.comb(U2, ["1", "4", "9", "10", "12", "13"], "GND", out=25.4, tail=5.08)
    c.nc_pin(U2, "8")
    c.nc_pin(U2, "11")
    c.pwr_pin(U2, "14", "+5V_RAW", 5.08)
    c.pwr_pin(U2, "7", "GND", 5.08)
    c.decouple("C502", "C0603_100nF", 325, 72, "+5V_RAW", "GND")
    for k, (pin, ty) in enumerate((("3", 88.9), ("6", 109.22))):
        px, py = U2.pin_pos(pin)
        jog = px + 6.35
        sh.wire(px, py, jog, py)
        sh.wire(jog, py, jog, ty)
        r = c.place("R5%02d" % (9 + k), "R0603_49R9", jog + 7.62, ty, 90)
        flat_fields(r, jog + 7.62, ty)
        sh.wire(jog, ty, r.pin_pos(1)[0], r.pin_pos(1)[1])
        # v0.8: global labels instead of the J506/J507 edge terminals - the fast outputs go to
        # two SMA connectors on the front panel, where the coax already is.
        e = sh.stub(r, 2, 7.62)
        sh.label("FASTTTL%d" % (k + 1), e[0], e[1], 0, "global")
    sh.text("FASTTTL1/2 leave this sheet as global labels -> panel link J7 ->", 235, 140, 1.3)
    sh.text("the two fast SMAs on the front panel (49.9 R series).", 235, 143.5, 1.3)
    sh.text("The edge terminals J506/J507 are gone (v0.8).", 235, 147, 1.3)

    # ---------------- 74LVC1T45: bidirectional TRIG ---------------------------------------
    U3 = c.place("U503", "SN74LVC1T45DBVR", 430, 105, 0)
    c.glabel_pin(U3, "3", "TRIG_IO", 7.62)
    c.glabel_pin(U3, "5", "TRIG_DIR", 7.62)
    # VCCA and VCCB are 2.54 mm apart: each stub steps aside before its rail symbol
    a1 = sh.stub(U3, "1", 5.08)
    sh.wire(a1[0], a1[1], a1[0] - 10.16, a1[1])
    c.tap(a1[0] - 10.16, a1[1], "+3V3")
    b1 = sh.stub(U3, "6", 10.16)
    sh.wire(b1[0], b1[1], b1[0] + 10.16, b1[1])
    c.tap(b1[0] + 10.16, b1[1], "+5V_RAW")
    c.pwr_pin(U3, "2", "GND", 5.08)
    b = sh.stub(U3, "4", 5.08)
    r = c.place("R511", "R0603_33", b[0] + 3.81, b[1], 90)
    flat_fields(r, b[0] + 3.81, b[1])
    sh.wire(b[0], b[1], r.pin_pos(1)[0], r.pin_pos(1)[1])
    node = r.pin_pos(2)
    sh.wire(node[0], node[1], node[0] + 17.78, node[1])
    sh.label("TRIG_5V", node[0] + 17.78, node[1], 0, "global")
    d = c.place("D501", "BAV99", node[0] + 8.89, node[1] + 15.24, 180)
    sh.wire(d.pin_pos(3)[0], d.pin_pos(3)[1], d.pin_pos(3)[0], node[1])
    c.pwr_L(d, 1, "GND", 2.54, 5.08)            # clamp to GND, symbol below the diode
    c.pwr_L(d, 2, "+5V_RAW", 7.62, 5.08)        # clamp to +5V_RAW, symbol above its own stub
    for k, (ref, rail) in enumerate([("C503", "+3V3"), ("C504", "+5V_RAW")]):
        c.decouple(ref, "C0603_100nF", 490 + k * 15.24, 105, rail, "GND")
    sh.text("TRIG_DIR = 1: TRIG_IO drives the SMA (output); 0: SMA -> TRIG_IO (input, 5 V tolerant)", 400, 145, 1.3)

    # ---------------- U505: TCA9535 I2C GPIO expander (v0.7, re-spec 8.2) ----------------------
    U5 = c.place("U505", "TCA9535PWR", 140, 270, 0, block="BASE")   # expander serves B and C: owned by the base (sits under the dev board)
    c.pwr_pin(U5, "24", "+3V3", 5.08)
    c.pwr_pin(U5, "12", "GND", 5.08)
    c.comb(U5, ["21", "2", "3"], "GND", out=15.24, tail=5.08)       # A0, A1, A2 -> GND: address 0x20
    c.glabel_pin(U5, "23", "I2C_SDA", 7.62)
    c.glabel_pin(U5, "22", "I2C_SCL", 7.62)
    c.nc_pin(U5, "1")                                # INT (open drain) unused: the firmware polls the outputs
    for i in range(8):                               # P00..P07 (pins 4..11) -> 74AHCT541 inputs A1..A8
        c.glabel_pin(U5, str(4 + i), "DIO%d" % (i + 1), 7.62)
    for i in range(4):                               # P10..P13 (pins 13..16) -> MOD1..MOD4 (the ports the relay gates used)
        c.glabel_pin(U5, str(13 + i), "MOD%d" % (i + 1), 7.62)
    c.glabel_pin(U5, "17", "EXP_P14", 7.62)          # P14 is taken: /CLR of the 74HC74 Johnson counter (nmr_rx)
    for i in range(3):                               # P15..P17 (pins 18..20) -> MOD5..MOD7
        c.glabel_pin(U5, str(18 + i), "MOD%d" % (i + 5), 7.62)
    c.decouple("C507", "C0603_100nF", 195, 245, "+3V3", "GND").fields["Block"] = "BASE"
    tp = c.place("TP501", "TestPoint", 215, 282.54, 90, block="BASE")   # /CLR of the Johnson counter, for bring-up
    tp.field_pos["Reference"] = (210.5, 278.5, 270, "left bottom")
    c.glabel_pin(tp, 1, "EXP_P14", 5.08)
    for k, s in enumerate([
            "U505 TCA9535 (TSSOP-24, address 0x20, A0 = A1 = A2 = GND): the I2C port expander that replaced 12 direct GPIO in v0.7 — P00..P07 = DIO1..8 into the",
            "74AHCT541 above; P10..P13 and P15..P17 = MODULE OUT 1..7, the 3.3 V module outputs, to the panel link J8 (v0.7d). P14 is NOT free: it is EXP_P14, the",
            "/CLR of the 74HC74 Johnson counter on the NMR receiver sheet (TP501 is its test point). MODULE OUT 8 is reserved: J8 pin 33 is not connected on this",
            "board and the panel pulls it down. MOD1..MOD4 keep the ports the relay gates used, so the firmware mapping is unchanged. Every port is an input",
            "after power-up and after a reset: the pull-down on the panel buffer decides the state of a module."]):
        sh.text(s, 70, 335 + k * 3.6, 1.3)

    # ---------------- 10 MHz TCXO option (every part DNP) ----------------------------------
    X = c.place("X501", "1XTV10000MDA", 350, 270, 0, dnp=True)
    c.pwr_pin(X, "4", "+3V3", 3.81)
    c.pwr_pin(X, "2", "GND", 3.81)
    vc = sh.stub(X, "1", 7.62)                       # VCONT node: the divider column sits on the stub end
    rv1 = c.place("R512", "R0603_100k", vc[0], vc[1] - 10.16, 0, dnp=True)
    rv2 = c.place("R513", "R0603_100k", vc[0], vc[1] + 10.16, 0, dnp=True)
    sh.wire(vc[0], rv1.pin_pos(2)[1], vc[0], rv2.pin_pos(1)[1])
    c.pwr_pin(rv1, 1, "+3V3")
    c.pwr_pin(rv2, 2, "GND")
    o = sh.stub(X, "3", 5.08)
    cc = c.place("C505", "C0603_1nF", o[0] + 3.81, o[1], 90, dnp=True)
    flat_fields(cc, o[0] + 3.81, o[1])
    n2 = cc.pin_pos(2)
    U4 = c.place("U504", "SN74LVC1G17DBVR", n2[0] + 33.02, n2[1] + 2.54, 0, dnp=True)
    a = U4.pin_pos("2")
    # R514/R515 bias the Schmitt input at VCC/2: the divider midpoint sits ON the A line as a four-way
    # junction (v0.7 drew the column across the line without a wire end, so KiCad never joined it — fixed 2026-09-17).
    mid = (n2[0] + 15.24, n2[1])
    sh.wire(n2[0], n2[1], mid[0], mid[1])
    sh.wire(mid[0], mid[1], a[0], a[1])
    rb1 = c.place("R514", "R0603_100k", mid[0], mid[1] - 10.16, 0, dnp=True)   # pin 2 (bottom) toward the line
    rb2 = c.place("R515", "R0603_100k", mid[0], mid[1] + 10.16, 0, dnp=True)   # pin 1 (top) toward the line
    sh.wire(mid[0], rb1.pin_pos(2)[1], mid[0], mid[1])
    sh.wire(mid[0], mid[1], mid[0], rb2.pin_pos(1)[1])
    c.pwr_pin(rb1, 1, "+3V3")
    c.pwr_pin(rb2, 2, "GND")
    c.pwr_pin(U4, "5", "+3V3", 3.81)
    c.pwr_pin(U4, "3", "GND", 3.81)
    c.nc_pin(U4, "1")
    yv = sh.stub(U4, "4", 6.35)
    jp = c.place("JP501", "SolderJumper_2_Open", yv[0] + 3.81, yv[1], 0)
    e = sh.stub(jp, 2, 10.16)
    sh.label("GPIO44", e[0], e[1], 0, "global")
    c.decouple("C506", "C0603_100nF", 455, 295, "+3V3", "GND").dnp = True
    sh.text("10 MHz timebase option — all parts DNP by default (zero cost);", 320, 320, 1.3)
    sh.text("JP501 open until a firmware use exists", 320, 323.5, 1.3)
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
# v0.8 (Decisions #45, #48, #49): the front panel stacks flat on the BACK of the main board on
# three straight 2x20 male headers instead of one right-angle 2x20 on the front edge.
#   J6 = analog  (left,   x ~ 12 mm)   J7 = digital (centre, x ~ 90 mm)   J8 = power + spares (right, x ~ 168 mm)
# One rule for all three: an odd pin is a signal (row 1) and the even pin next to it is that
# signal's return (row 2) - AGND for everything analog, GND for everything digital.
# A pin whose value is None is spare: not connected on the main board, brought to a labelled
# test pad on the panel so a later panel part needs no new main-board revision.
LINK_A = {1: "AI1", 2: "AGND", 3: "AI2", 4: "AGND", 5: "AI3", 6: "AGND", 7: "AI4", 8: "AGND",
          9: "AI5", 10: "AGND", 11: "AI6", 12: "AGND", 13: "AI7", 14: "AGND", 15: "AI8", 16: "AGND",
          17: "RX", 18: "AGND", 19: "TX", 20: "AGND", 21: "TX", 22: "AGND",     # TX on two pins: coil current
          23: "AUX", 24: "AGND", 25: "AO1", 26: "AGND", 27: "AO2", 28: "AGND",
          29: None, 30: "AGND", 31: None, 32: "AGND", 33: None, 34: "AGND",
          35: None, 36: "AGND", 37: None, 38: "AGND", 39: None, 40: "AGND"}
LINK_B = {1: "TTL1", 2: "GND", 3: "TTL2", 4: "GND", 5: "TTL3", 6: "GND", 7: "TTL4", 8: "GND",
          9: "TTL5", 10: "GND", 11: "TTL6", 12: "GND", 13: "TTL7", 14: "GND", 15: "TTL8", 16: "GND",
          17: "FASTTTL1", 18: "GND", 19: "FASTTTL2", 20: "GND", 21: "TRIG_5V", 22: "GND",
          23: "I2C_SDA", 24: "GND", 25: "I2C_SCL", 26: "GND", 27: "+3V3", 28: "GND",
          29: "LED_PWR", 30: "GND", 31: "LED_WIFI", 32: "GND", 33: "LED_ACT", 34: "GND",
          35: None, 36: "GND", 37: None, 38: "GND", 39: None, 40: "GND"}
# v0.7d (2026-09-17): the four relays and the two isolated inputs left the main board. The eight
# free expander ports are now MOD1..MOD7 ("module outputs", 3.3 V logic) and the two opto outputs come
# back from the panel, so J8 carries them all. gen_panel.py builds the panel against exactly this map.
LINK_C = {1: "+5V_RAW", 2: "GND", 3: "+5V_RAW", 4: "GND", 5: "+3V3", 6: "GND",
          7: "GPIO4", 8: "GND", 9: "GPIO6", 10: "GND", 11: "GPIO7", 12: "GND", 13: "GPIO15", 14: "GND",
          15: "GPIO43", 16: "GND", 17: "GPIO44", 18: "GND",
          19: "MOD1", 20: "GND", 21: "MOD2", 22: "GND", 23: "MOD3", 24: "GND", 25: "MOD4", 26: "GND",
          27: "MOD5", 28: "GND", 29: "MOD6", 30: "GND", 31: "MOD7", 32: "GND", 33: None, 34: "GND",   # 33 = MODULE OUT 8, reserved: no expander port is free
          35: "OPTO_IN1", 36: "GND", 37: "OPTO_IN2", 38: "GND", 39: None, 40: "GND"}
LINKS = [("J6", LINK_A, "analog", 12), ("J7", LINK_B, "digital", 90), ("J8", LINK_C, "rails, GPIO, module outputs", 168)]


def link_rows(pins, per_row=6):
    """table rows "pins | signals" for one header, six pins to a line"""
    rows = [["Pins", "Signals (odd = signal, even = its return)"]]
    for k in range(0, 40, per_row):
        nums = range(k + 1, min(k + per_row, 40) + 1)
        rows.append(["%d-%d" % (k + 1, min(k + per_row, 40)),
                     "  ".join(pins[n] or "spare" for n in nums)])
    return rows


def build_link(root_uuid):
    sh = Sheet("front_panel_link", "Front-panel link J6/J7/J8 (3 x 2x20, bottom side)", "A3", 9,
               "Three straight 2x20 male headers; every signal has GND/AGND on the adjacent pin")
    # power-symbol reference range 6xxx: the deleted OPT sheet used to own it, and the NMR
    # receiver sheet already uses 7xxx - sharing the range gave duplicate #PWR references
    # (kicad-cli then warns "schematic has annotation errors").
    c = Ctx(sh, "BASE", 6000)

    def wrap(s, n=260):
        """split a long note into page-wide lines so nothing runs off the right edge"""
        out, cur = [], ""
        for w in s.split(" "):
            if cur and len(cur) + 1 + len(w) > n:
                out.append(cur)
                cur = w
            else:
                cur = w if not cur else cur + " " + w
        if cur:
            out.append(cur)
        return out

    notes = []
    for s in [
        "The panel stacks flat on the BACK of the main board (Decision #45). J6/J7/J8 are mounted on the BOTTOM side of the main board and hand-soldered from the top; they mate the panel's three female headers. Positions along the 180 mm edge: x ~ 12 (J6), x ~ 90 (J7), x ~ 168 (J8) mm.",
        "Odd pins = row 1 (signal), even pins = row 2 (return): every signal pin has its return, AGND or GND, on the adjacent even pin. The whole even row of a header is one net, so it is drawn as one comb with a single symbol. J6 carries the analog signals (nearest the panel SMAs), J7 the digital ones, J8 the rails, the free GPIO, the seven module outputs MODULE OUT 1..7 and the two isolated-input returns OPTO_IN1/2.",
        "LED_PWR is +3V3 (always on; the LED series resistor sits on the panel). LED_WIFI / LED_ACT come from GPIO43 / GPIO44 through JP1 / JP2 (base sheet). GPIO4/6/7/15/43/44 on J8 are the same nets as on the expansion header J5. TX is on two pins (19 and 21) so the coil current has two paths.",
        "Pins marked spare are not connected on the main board; on the panel they reach labelled test pads, so a later panel part needs no new main-board revision. Panel copper is AGND and meets GND only at the star point NT1 on the main board.",
        "The three headers (and the panel's three female headers) are bought separately and soldered by the instructor: they carry the field Assembly = hand and are excluded from the JLC BOM and CPL.",
    ]:
        notes += wrap(s)
    sheet_frame(sh, "LINK", "FRONT-PANEL LINK - three 2x20 straight male headers on the BOTTOM side of the main board (v0.8)", notes)
    # Layout rules (2026-09-17 spacing rework): the twenty returns of a header share one comb with one
    # ground symbol, a rail leaves the header sideways and turns up on its own stub, and no wire crosses a
    # label.  Checked by scripts/sch_check.py and by the SVG render.
    for k, (ref, pins, what, xmm) in enumerate(LINKS):
        J = c.place(ref, "HDR_2x20_FEMALE", 60 + k * 130, 150, 0)   # FEMALE on the main board: its pins are live (user, 2026-09-17)
        # every even pin is the return of the odd pin beside it and they are all one net:
        # one comb down the right-hand row, one symbol below the last pin
        c.comb(J, list(range(2, 41, 2)), "AGND" if ref == "J6" else "GND", out=10.16, tail=7.62)
        skip = set()
        if ref == "J7":                      # pin 27 = +3V3, pin 29 = LED_PWR (+3V3 as well): one comb
            c.comb(J, [27, 29], "+3V3", out=30.48, tail=7.62)
            skip = {27, 29}
        elif ref == "J8":
            c.comb(J, [1, 3], "+5V_RAW", out=30.48, tail=7.62)
            c.pwr_L(J, 5, "+3V3", 38.1, 17.78)
            skip = {1, 3, 5}
        for pin in range(1, 41, 2):
            if pin in skip:
                continue
            net = pins[pin]
            if net is None:
                c.nc_pin(J, pin)
            else:
                c.glabel_pin(J, pin, net, 7.62)
        sh.text("%s - %s, at x = %d mm on the bottom side" % (ref, what, xmm), 34 + k * 130, 112, 1.6, True)
        sh.table(20 + k * 132, 200, link_rows(pins), [14, 110], 1.25)
        sh.text("%s pin table" % ref, 20 + k * 132, 198, 1.3, True)
    sh.text("Pin 29 of J7 (LED_PWR) is +3V3 directly; the panel LED series resistor sits on the panel PCB.", 20, 265, 1.3)
    sh.text("MODULE OUT 1..7 (J8 pins 19-31 odd) are 3.3 V logic from the TCA9535 expander: the panel buffers them to 5 V TTL to drive commercial", 20, 268.5, 1.3)
    sh.text("opto-isolated relay modules (5 mA per input). MODULE OUT 8 (pin 33) is RESERVED: no expander port is free for it, so it is not connected", 20, 272, 1.3)
    sh.text("on the main board and the panel pulls it down. OPTO_IN1/2 (pins 35, 37) come the other way: the two 6N137 isolated inputs live on the panel", 20, 275.5, 1.3)
    sh.text("and their open-collector outputs reach GPIO16/17 here. Spare pins: J6 has 6 (29-39 odd), J7 has 3 (35-39 odd), J8 has 2 (33, 39).", 20, 279, 1.3)
    auto_junctions(sh)
    return sh


# ================================================================== ROOT
def build_root(sheets, root_uuid):
    sh = Sheet("class-board", "TIGP class board 2026 — root", "A3", 1, "ESP32-S3 laboratory instrument carrier + NMR console: base + 3 student sections (A inputs/receiver, B outputs/timing/transmitter, C power/switching) + front panel link")
    sh.uuid = root_uuid
    sh.text("TIGP CLASS BOARD 2026 — laboratory instrument carrier (ESP32-S3 dev board) with NMR console, rev B (v0.7, 2026-09-13)", 12.7, 16, 3.5, True)
    sh.text("Design brief v0.6 + notes/2026-09-13-nmr-respec-proposal.md (v0.7) + hardware/docs/design-decisions.md. Interface nets between sheets are global labels; rails are power symbols; AGND meets GND only at NT1.", 12.7, 21, 1.5)
    sh.text("Stack-up: L1 signal/power, L2 GND, L3 GND, L4 signal/power. Board 180 x 100 mm, 4 x M3. Bottom side: three 2x20 straight male headers (J6 at x 12, J7 at x 90, J8 at x 168 mm) carry the front panel (180 x 100, 17 SMA) flat on the back of the board. Rear edge: USB-C, 5 V jack, external power, H-bridge and polarizer coil terminals. Sections: A = B1 + NMR RX, B = B3 + B5 + NMR TX, C = the front-panel board; the power entry and the coil switches are the instructor’s (ZONE_INSTR). v0.7d: the four relays and the two isolated inputs left the main board — it offers 5 V TTL module outputs instead and switches no mains.", 12.7, 25, 1.5)
    core = ["base_mcu", "b2_power", "b1_inputs", "b3_outputs", "b5_dio_trig", "front_panel_link"]
    order = [n for n in core if n in sheets] + [n for n in sheets if n not in core]
    titles = {"base_mcu": "BASE: dev-board socket, buses, expansion, star point", "b2_power": "B2 (C): power entry, +-12 V, LDOs",
              "b1_inputs": "B1 (A): 8 x +-10 V inputs, ADS8688", "b3_outputs": "B3 (B): DAC8563 + OPA2192 -> AO1/AO2",
              "b5_dio_trig": "B5 (B): TCA9535 -> 8 TTL DIO + 8 module outputs, 2 fast outs, TRIG", "front_panel_link": "LINK: 3 x 2x20 to the front panel (bottom side)"}
    for k, name in enumerate(order):
        col, row = k % 4, k // 4
        x, y = 12.7 + col * 100, 35 + row * 45
        s = sheets[name]
        sh.sheets.append(dict(name=name, file="sheets/%s.kicad_sch" % name, x=g(x), y=g(y), w=88.9, h=30.48, pins=[], uuid=s.uuid, page=s.page))
        sh.text(titles.get(name, s.title), x + 1.5, y + 27, 1.3)
    # interface tables
    gpio = [["GPIO", "Net", "Function", "Section"], ["12/11/13", "SPI_SCLK/MOSI/MISO", "SPI2 IO_MUX, 33 R at source (ADC, DAC, DDS)", "base"], ["10", "CS_ADC", "ADS8688 /CS", "A"], ["5", "CS_DAC", "DAC8563 /SYNC (via 74HCT125)", "B"],
            ["1/2", "I2C_SDA/SCL", "400 kHz: OLED 0x3C, TCA9535 0x20, Si5351A 0x60, Qwiic J4 + panel Qwiic", "base"], ["16/17", "OPTO_IN1/2", "the two isolated inputs, now on the front panel; active LOW", "panel"], ["18/21", "FAST_OUT1/2", "74HCT125 -> 49.9 R -> panel link -> 2 fast SMAs on the panel", "B"],
            ["38/39", "TRIG_IO / TRIG_DIR", "74LVC1T45; DIR 1 = output to the panel SMA", "B"], ["41/42", "DDS_FSYNC / DDS_PSEL", "AD9834 frame sync / phase-register select", "B"],
            ["40", "TX_EN", "OPA564 enable = transmit gate (10 k pull-down)", "B"], ["8", "RX_BLANK", "DG419 receiver blanking (pull-up: blanked)", "A"],
            ["9/14", "HB_IN1/2", "DRV8871 H-bridge inputs (10 k pull-downs)", "C"], ["47", "FET_GATE", "UCC27517 -> AOD4184A polarizer switch", "C"],
            ["TCA9535 P00-P07", "DIO1..8", "74AHCT541 -> 1 k -> panel link -> panel TTL strip", "B"], ["TCA9535 P10-P13, P15-P17", "MODULE OUT 1..7", "3.3 V -> panel link J8 -> 5 V TTL buffers on the panel (OUT 8 reserved, J8 pin 33 n/c)", "B"], ["TCA9535 P14", "EXP_P14", "/CLR of the 74HC74 Johnson counter (NMR RX); TP501", "A"],
            ["4/6/7/15", "GPIO4/6/7/15", "free -> 2x10 expansion header", "base"], ["19/20", "USB_DN/DP", "native USB from the carrier USB-C", "base"],
            ["43/44", "GPIO43/44", "header; LED_WIFI/ACT via JP1/JP2; TCXO option", "base"], ["3, 0/45/46, 35-37, 48", "-", "strapping / PSRAM / on-board LED: unused", "-"]]
    sh.table(12.7, 180, gpio, [34, 40, 92, 14], 1.3)
    rails = [["Rail", "Source", "Budget", "Feeds"], ["+5V_RAW", "USB-C or jack via polyfuse + TVS + LM66100", "<= 1.5 A (est. 0.87-1.07 A)", "dev board, 5 V logic, LDO, DC-DC, the panel through J8"],
             ["+3V3", "AMS1117-3.3", "<= 500 mA (est. < 150 mA)", "logic side, OLED, optos, Qwiic"], ["+12V / -12V", "B0512S-2WR3 x2, AGND-referenced", "166 mA each (est. 40 / 20 mA incl. bleeders)", "78L05, OPA2192, clamps, OPT"],
             ["+5VA", "78L05G from +12V", "<= 100 mA (est. 17 mA)", "ADS8688 / DAC8563 AVDD"], ["AGND", "star point NT1 (net tie) to GND", "-", "L1/L4 analog copper, panel copper (through J6)"]]
    sh.table(200, 180, rails, [26, 62, 52, 60], 1.3)
    sh.text("GPIO map v0.7 (interface contract, brief 4.2 + proposal 8.2)", 12.7, 177, 1.5, True)
    sh.text("Rails (brief 4.1, updated per design-decisions D-02/D-04; +VEXT 7-18 V external input on the C sheet)", 200, 177, 1.5, True)
    sh.text("Reference ranges: base 1-99, B1 100-199, B2 200-299, B3 300-399, B5 500-599, NMR RX 700-799, NMR TX 800-899, coil switches / external power 900-999. B4 (400-499, relays and isolated inputs) was deleted in v0.7d; the owner-zone DRC uses the Block field.", 12.7, 272, 1.4)
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
            {"name": "ISO_IN", "clearance": 0.2, "track_width": 0.3, "via_diameter": 0.6, "via_drill": 0.3, "bus_width": 12, "wire_width": 6, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 5}],
            "meta": {"version": 4},
            "net_colors": None, "netclass_assignments": None,
            "netclass_patterns": [
                {"netclass": "POWER_RAW", "pattern": "+5V_RAW"}, {"netclass": "POWER_RAW", "pattern": "+5V_RAW_OR"},
                {"netclass": "POWER", "pattern": "+12V"}, {"netclass": "POWER", "pattern": "-12V"}, {"netclass": "POWER", "pattern": "+5VA"}, {"netclass": "POWER", "pattern": "+3V3"}, {"netclass": "POWER", "pattern": "AGND"},
                {"netclass": "ANALOG_IN", "pattern": "/b1_inputs/AIN*"}, {"netclass": "ANALOG_IN", "pattern": "AI?"},
                {"netclass": "ANALOG_OUT", "pattern": "AO?"}, {"netclass": "ANALOG_OUT", "pattern": "/b3_outputs/AOUT*"},
                {"netclass": "FAST", "pattern": "SPI_*"}, {"netclass": "FAST", "pattern": "CS_*"}, {"netclass": "FAST", "pattern": "FAST_OUT?"}, {"netclass": "FAST", "pattern": "TRIG_*"},
                {"netclass": "FAST", "pattern": "/b3_outputs/DAC_*"}, {"netclass": "FAST", "pattern": "/base_mcu/*_MCU"}]},
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
    for fn in (build_base, build_b2, build_b1, build_b3, build_b5, build_link):
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
