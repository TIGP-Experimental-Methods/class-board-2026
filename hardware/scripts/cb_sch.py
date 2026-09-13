"""KiCad 9/10 schematic writer used by the class-board generator.

A Sheet collects symbol instances, wires, junctions, labels, no-connects, text and
hierarchical sheet symbols and writes a .kicad_sch file.  Pin positions are computed from
the library definitions in cb_symbols so wires can be attached exactly.

Coordinate convention: schematic x to the right, y DOWN (KiCad).  Symbol libraries use
y UP, so the transform for a symbol at (X, Y) with rotation R (degrees, counter-clockwise
on screen as KiCad shows it) is verified by tools/pcb-style calibration (see gen tests):
   R=0   : (X + x, Y - y)
   R=90  : (X - y, Y - x)      (calibrated with kicad-cli netlist export, 2026-09-07)
   R=180 : (X - x, Y + y)
   R=270 : (X + y, Y + x)
"""
import math
from sexp import q, num, uid, uid_for, font
from cb_symbols import SYMBOLS

GRID = 1.27


def g(v):
    """snap to the 1.27 mm grid"""
    return round(round(v / GRID) * GRID, 4)


def xform(x, y, rot, mirror=None):
    """library (y-up) offset -> schematic (y-down) offset for rotation rot and optional mirror."""
    if mirror == "x":     # mirror about the x axis (flips vertically on screen)
        y = -y
    elif mirror == "y":   # mirror about the y axis (flips horizontally)
        x = -x
    r = rot % 360
    if r == 0:
        return x, -y
    if r == 90:
        return -y, -x
    if r == 180:
        return -x, y
    if r == 270:
        return y, x
    raise ValueError(rot)


class Inst:
    """A placed symbol instance."""

    def __init__(self, ref, libname, x, y, rot=0, mirror=None, unit=1, value=None, fields=None, dnp=False, block=None):
        self.ref, self.lib, self.sym = ref, libname, SYMBOLS[libname]
        self.x, self.y, self.rot, self.mirror, self.unit = x, y, rot, mirror, unit
        self.value = value if value is not None else self.sym.value
        self.fields = dict(fields or {})
        if block:
            self.fields["Block"] = block
        self.dnp = dnp
        self.uuid = uid()
        self.pin_uuids = {}
        self.field_pos = {}   # optional overrides: name -> (x, y, rot, justify)

    def pin_pos(self, number):
        p = self.sym.pin_by_number(number)
        dx, dy = xform(p.x, p.y, self.rot, self.mirror)
        return round(self.x + dx, 4), round(self.y + dy, 4)

    def pin_pos_named(self, name, idx=0):
        p = self.sym.pins_named(name)[idx]
        return self.pin_pos(p.number)

    def pins(self):
        return [p for p in self.sym.pins if p.unit in (0, self.unit)] if self.sym.units > 1 else list(self.sym.pins)

    def bbox(self):
        """screen-space bounding box (x1,y1,x2,y2) of the body incl. pins"""
        b = self.sym.bbox or (-2.54, -2.54, 2.54, 2.54)
        pts = [xform(b[0], b[1], self.rot, self.mirror), xform(b[2], b[3], self.rot, self.mirror),
               xform(b[0], b[3], self.rot, self.mirror), xform(b[2], b[1], self.rot, self.mirror)]
        xs = [self.x + p[0] for p in pts]
        ys = [self.y + p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)


class Sheet:
    def __init__(self, name, title, paper="A3", page=1, description=""):
        self.name, self.title, self.paper, self.page = name, title, paper, page
        self.description = description
        self.uuid = uid_for("sheet:" + name)
        self.insts = []
        self.wires = []      # (x1,y1,x2,y2)
        self.junctions = []
        self.labels = []     # (text, x, y, rot, kind, shape)  kind: local|hier|global
        self.noconnects = []
        self.texts = []      # (text, x, y, size, bold)
        self.boxes = []      # (x1,y1,x2,y2, title)
        self.sheets = []     # hierarchical sheet symbols: dict
        self.tables = []     # (x, y, rows(list of list), colwidths)
        self.used_pins = set()

    # ---- placement helpers -------------------------------------------------------------
    def add(self, inst):
        inst.uuid = uid_for("sym:%s:%s:u%d" % (self.name, inst.ref, inst.unit))
        self.insts.append(inst)
        return inst

    def place(self, ref, lib, x, y, rot=0, **k):
        return self.add(Inst(ref, lib, g(x), g(y), rot, **k))

    def wire(self, x1, y1, x2, y2):
        x1, y1, x2, y2 = g(x1), g(y1), g(x2), g(y2)
        if abs(x1 - x2) < 1e-6 and abs(y1 - y2) < 1e-6:
            return
        if abs(x1 - x2) > 1e-6 and abs(y1 - y2) > 1e-6:   # never draw a diagonal: make an L
            self.wires.append((x1, y1, x2, y1))
            self.wires.append((x2, y1, x2, y2))
            return
        self.wires.append((x1, y1, x2, y2))

    def path(self, *pts):
        """polyline wire through points"""
        for a, b in zip(pts, pts[1:]):
            self.wire(a[0], a[1], b[0], b[1])

    def wire_pins(self, inst_a, pin_a, inst_b, pin_b, via=None):
        """connect two pins with an L or straight wire; via = 'h' (horizontal first) or 'v'."""
        ax, ay = inst_a.pin_pos(pin_a)
        bx, by = inst_b.pin_pos(pin_b)
        self.route(ax, ay, bx, by, via)
        self.used_pins.add((inst_a.ref, str(pin_a), inst_a.unit))
        self.used_pins.add((inst_b.ref, str(pin_b), inst_b.unit))

    def route(self, ax, ay, bx, by, via=None):
        if abs(ax - bx) < 1e-6 or abs(ay - by) < 1e-6:
            self.wire(ax, ay, bx, by)
        elif via == "v":
            self.wire(ax, ay, ax, by)
            self.wire(ax, by, bx, by)
        else:
            self.wire(ax, ay, bx, ay)
            self.wire(bx, ay, bx, by)

    def junction(self, x, y):
        self.junctions.append((g(x), g(y)))

    def label(self, text, x, y, rot=0, kind="local", shape="bidirectional"):
        self.labels.append((text, g(x), g(y), rot, kind, shape))

    def nc(self, x, y):
        self.noconnects.append((g(x), g(y)))

    def text(self, s, x, y, size=1.27, bold=False):
        self.texts.append((s, x, y, size, bold))

    def box(self, x1, y1, x2, y2, title=None):
        self.boxes.append((x1, y1, x2, y2, title))

    def table(self, x, y, rows, colwidths, size=1.27):
        self.tables.append((x, y, rows, colwidths, size))

    def sheet_symbol(self, name, filename, x, y, w, h, pins, sheet_uuid):
        """pins: list of (name, side('L'|'R'|'T'|'B'), offset, shape)"""
        self.sheets.append(dict(name=name, file=filename, x=x, y=y, w=w, h=h, pins=pins, uuid=sheet_uuid))

    # ---- pin wiring convenience -------------------------------------------------------
    def stub(self, inst, pin, length, direction=None):
        """draw a short wire from a pin outward (away from the body) and return its end."""
        px, py = inst.pin_pos(pin)
        p = inst.sym.pin_by_number(pin)
        # in library coords the pin points from its end toward the body at angle p.angle
        ca, sa = round(math.cos(math.radians(p.angle))), round(math.sin(math.radians(p.angle)))
        dx, dy = xform(-ca, -sa, inst.rot, inst.mirror)
        ex, ey = px + dx * length, py + dy * length
        self.wire(px, py, ex, ey)
        self.used_pins.add((inst.ref, str(pin), inst.unit))
        return round(ex, 4), round(ey, 4)

    def pin_label(self, inst, pin, text, kind="local", length=2.54, shape="bidirectional"):
        """short stub from pin ending in a label"""
        ex, ey = self.stub(inst, pin, length)
        px, py = inst.pin_pos(pin)
        rot = 0 if ex >= px + 1e-6 else (180 if ex < px - 1e-6 else (270 if ey < py else 90))
        self.label(text, ex, ey, rot, kind, shape)
        return ex, ey

    def power(self, inst, pin, net, length=2.54, ref_counter=None):
        """attach a power symbol to a pin via a stub of the given length"""
        ex, ey = self.stub(inst, pin, length)
        px, py = inst.pin_pos(pin)
        libname = "PWR_" + net.replace("+", "p").replace("-", "n")
        # orientation: power symbols draw upward for positive rails, downward for grounds
        if ey < py - 1e-6 or ey > py + 1e-6:   # vertical stub
            rot = 0
        else:
            rot = 0
        ref = "#PWR%03d" % (ref_counter() if ref_counter else len(self.insts))
        self.add(Inst(ref, libname, ex, ey, rot))
        return ex, ey

    # ---- writer --------------------------------------------------------------------------
    def lib_symbols_sexp(self):
        names = sorted({i.lib for i in self.insts})
        out = ["  (lib_symbols"]
        for n in names:
            s = SYMBOLS[n]
            body = s.sexp()
            # rename to class_board:NAME and nested unit names
            body = body.replace('(symbol %s' % q(s.name), '(symbol %s' % q("class_board:" + s.name), 1)
            for u in range(0, s.units + 1):
                body = body.replace('(symbol %s' % q("%s_%d_1" % (s.name, u)), '(symbol %s' % q("%s_%d_1" % (s.name, u)))
            out.append(body)
        out.append("  )")
        return "\n".join(out)

    def write(self, path, project_name, root_uuid, sheet_path):
        L = ['(kicad_sch (version 20250114) (generator "class_board_gen") (generator_version "1.0")',
             "  (uuid %s)" % q(self.uuid), "  (paper %s)" % q(self.paper),
             "  (title_block (title %s) (date \"2026-09-07\") (rev \"A\") (company \"TIGP class board 2026\") (comment 1 %s))" % (q(self.title), q(self.description[:120])),
             self.lib_symbols_sexp()]
        for j in self.junctions:
            L.append("  (junction (at %s %s) (diameter 0) (color 0 0 0 0) (uuid %s))" % (num(j[0]), num(j[1]), q(uid())))
        for n in self.noconnects:
            L.append("  (no_connect (at %s %s) (uuid %s))" % (num(n[0]), num(n[1]), q(uid())))
        for w in self.wires:
            L.append("  (wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid %s))" % (num(w[0]), num(w[1]), num(w[2]), num(w[3]), q(uid())))
        for (x1, y1, x2, y2, title) in self.boxes:
            L.append("  (rectangle (start %s %s) (end %s %s) (stroke (width 0.2) (type dash)) (fill (type none)) (uuid %s))" % (num(x1), num(y1), num(x2), num(y2), q(uid())))
            if title:
                L.append("  (text %s (exclude_from_sim no) (at %s %s 0) %s (uuid %s))" % (q(title), num(x1 + 1.27), num(y1 - 1.27), font(2.0, bold=True, justify="left bottom"), q(uid())))
        for (s, x, y, size, bold) in self.texts:
            L.append("  (text %s (exclude_from_sim no) (at %s %s 0) %s (uuid %s))" % (q(s), num(x), num(y), font(size, bold=bold, justify="left bottom"), q(uid())))
        for (x, y, rows, colw, size) in self.tables:
            L.append(table_sexp(x, y, rows, colw, size))
        for (t, x, y, rot, kind, shape) in self.labels:
            just = "left" if rot in (0, 90) else "right"
            if kind == "local":
                L.append("  (label %s (at %s %s %d) (fields_autoplaced yes) %s (uuid %s))" % (q(t), num(x), num(y), rot, font(1.27, justify=just), q(uid())))
            elif kind == "hier":
                L.append("  (hierarchical_label %s (shape %s) (at %s %s %d) (fields_autoplaced yes) %s (uuid %s))" % (q(t), shape, num(x), num(y), rot, font(1.27, justify=just), q(uid())))
            else:
                L.append("  (global_label %s (shape %s) (at %s %s %d) (fields_autoplaced yes) %s (uuid %s))" % (q(t), shape, num(x), num(y), rot, font(1.27, justify=just), q(uid())))
        for i in self.insts:
            L.append(self.inst_sexp(i, project_name, sheet_path))
        for sh in self.sheets:
            L.append(sheet_sexp(sh, project_name, sheet_path))
        if sheet_path.count("/") == 1:   # root sheet
            L.append("  (sheet_instances (path \"/\" (page \"%s\")))" % self.page)
        L.append(")")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(x for x in L if x) + "\n")

    def inst_sexp(self, i, project_name, sheet_path):
        s = i.sym
        out = ["  (symbol (lib_id %s) (at %s %s %d)%s (unit %d)" % (q("class_board:" + s.name), num(i.x), num(i.y), i.rot,
                                                                 (" (mirror %s)" % i.mirror) if i.mirror else "", i.unit),
               "    (exclude_from_sim no) (in_bom %s) (on_board yes) (dnp %s) (fields_autoplaced yes)" % ("yes" if s.in_bom and not i.ref.startswith("#") else "no", "yes" if i.dnp else "no"),
               "    (uuid %s)" % q(i.uuid)]
        # property placement: reference above-left, value below-left of the body bbox
        bx1, by1, bx2, by2 = i.bbox()
        props = [("Reference", i.ref, False), ("Value", i.value, False), ("Footprint", s.footprint, True),
                 ("Datasheet", s.fields.get("Datasheet", ""), True), ("Description", s.description, True)]
        for k, v in s.fields.items():
            if k != "Datasheet":
                props.append((k, v, True))
        for k, v in i.fields.items():
            props.append((k, v, True))
        for k, v, hide in props:
            if k == "Reference" and s.power:
                hide = True
            if k == "Value" and s.power:
                down_type = s.name in ("PWR_GND", "PWR_AGND", "PWR_n12V")
                # direction the graphic points on screen after rotation
                base = (0, 1) if down_type else (0, -1)
                dx, dy = xform(base[0], -base[1], i.rot)   # base is in screen coords; convert via lib y-up
                if abs(dx) < 1e-6:
                    px, py, rot, just = i.x, i.y + (3.81 if dy > 0 else -3.302), 0, None
                elif dx > 0:
                    px, py, rot, just = i.x + 3.302, i.y, 0, "left"
                else:
                    px, py, rot, just = i.x - 3.302, i.y, 0, "right"
            elif k == "Reference":
                px, py, rot, just = (bx1, by1 - 0.762, 0, "left bottom") if k not in i.field_pos else i.field_pos[k]
            elif k == "Value":
                px, py, rot, just = (bx1, by2 + 0.762, 0, "left top") if k not in i.field_pos else i.field_pos[k]
            else:
                px, py, rot, just = i.x, i.y, 0, None
            if k in i.field_pos:
                px, py, rot, just = i.field_pos[k]
            out.append("    (property %s %s (at %s %s %d) (show_name no) %s)" % (q(k), q(v), num(px), num(py), rot, font(1.27, hide=hide, justify=just)))
        for p in s.pins:
            if s.units > 1 and p.unit not in (0, i.unit):
                continue
            out.append("    (pin %s (uuid %s))" % (q(p.number), q(uid())))
        out.append("    (instances (project %s (path %s (reference %s) (unit %d))))" % (q(project_name), q(sheet_path), q(i.ref), i.unit))
        out.append("  )")
        return "\n".join(out)


def table_sexp(x, y, rows, colw, size):
    """simple table drawn with text and lines (KiCad table object is version sensitive; lines are robust)."""
    L = []
    rowh = size * 2.2
    total_w = sum(colw)
    n = len(rows)
    # grid lines
    for r in range(n + 1):
        yy = y + r * rowh
        L.append("  (polyline (pts (xy %s %s) (xy %s %s)) (stroke (width 0.15) (type default)) (uuid %s))" % (num(x), num(yy), num(x + total_w), num(yy), q(uid())))
    xx = x
    for c in range(len(colw) + 1):
        L.append("  (polyline (pts (xy %s %s) (xy %s %s)) (stroke (width 0.15) (type default)) (uuid %s))" % (num(xx), num(y), num(xx), num(y + n * rowh), q(uid())))
        if c < len(colw):
            xx += colw[c]
    for r, row in enumerate(rows):
        xx = x
        for c, cell in enumerate(row):
            L.append("  (text %s (exclude_from_sim no) (at %s %s 0) %s (uuid %s))" % (q(str(cell)), num(xx + 0.8), num(y + r * rowh + rowh * 0.72), font(size, bold=(r == 0), justify="left bottom"), q(uid())))
            xx += colw[c]
    return "\n".join(L)


def sheet_sexp(sh, project_name, parent_path):
    x, y, w, h = sh["x"], sh["y"], sh["w"], sh["h"]
    L = ["  (sheet (at %s %s) (size %s %s) (fields_autoplaced yes) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000))" % (num(x), num(y), num(w), num(h)),
         "    (uuid %s)" % q(sh["uuid"]),
         "    (property \"Sheetname\" %s (at %s %s 0) %s)" % (q(sh["name"]), num(x), num(y - 0.7), font(1.5, justify="left bottom", bold=True)),
         "    (property \"Sheetfile\" %s (at %s %s 0) %s)" % (q(sh["file"]), num(x), num(y + h + 0.6), font(1.27, justify="left top"))]
    for (name, side, off, shape) in sh["pins"]:
        if side == "L":
            px, py, rot, just = x, y + off, 180, "right"
        elif side == "R":
            px, py, rot, just = x + w, y + off, 0, "left"
        elif side == "T":
            px, py, rot, just = x + off, y, 90, "left"
        else:
            px, py, rot, just = x + off, y + h, 270, "right"
        L.append("    (pin %s %s (at %s %s %d) %s (uuid %s))" % (q(name), shape, num(px), num(py), rot, font(1.27, justify=just), q(uid())))
    L.append("    (instances (project %s (path %s (page %s))))" % (q(project_name), q(parent_path), q(str(sh.get("page", 2)))))
    L.append("  )")
    return "\n".join(L)
