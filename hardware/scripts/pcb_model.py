"""KiCad 10 board-file writer for the class-board generators.

Board coordinates: x to the right, y down (KiCad).  The generator places footprints, adds
tracks/vias/zones/rule areas/graphics and writes the .kicad_pcb.  Footprint bodies are copied
from the project library (fp_parse) with nets, properties and instance data injected.
"""
import math
import os
import re

from sexp import q, num, uid, uid_for
from fp_parse import parse, find, first, Footprint, load_library

LAYERS_4 = [(0, "F.Cu", "signal"), (4, "In1.Cu", "power"), (6, "In2.Cu", "power"), (2, "B.Cu", "signal")]
LAYERS_2 = [(0, "F.Cu", "signal"), (2, "B.Cu", "signal")]
USER_LAYERS = [(9, "F.Adhes", "user", "F.Adhesive"), (11, "B.Adhes", "user", "B.Adhesive"), (13, "F.Paste", "user"), (15, "B.Paste", "user"),
               (5, "F.SilkS", "user", "F.Silkscreen"), (7, "B.SilkS", "user", "B.Silkscreen"), (1, "F.Mask", "user"), (3, "B.Mask", "user"),
               (17, "Dwgs.User", "user", "User.Drawings"), (19, "Cmts.User", "user", "User.Comments"), (21, "Eco1.User", "user", "User.Eco1"),
               (23, "Eco2.User", "user", "User.Eco2"), (25, "Edge.Cuts", "user"), (27, "Margin", "user"), (31, "F.CrtYd", "user", "F.Courtyard"),
               (29, "B.CrtYd", "user", "B.Courtyard"), (35, "F.Fab", "user"), (33, "B.Fab", "user"), (39, "User.1", "user"), (41, "User.2", "user")]


def flip_layer(name):
    if name.startswith("F."):
        return "B." + name[2:]
    if name.startswith("B."):
        return "F." + name[2:]
    return name


def rot_pt(x, y, deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return x * c - y * s, x * s + y * c


class Net:
    def __init__(self, code, name):
        self.code, self.name = code, name


class PadInst:
    """absolute pad geometry on the board"""
    __slots__ = ("ref", "number", "x", "y", "rot", "sx", "sy", "shape", "kind", "layers", "net", "drill", "hx", "hy")

    def __init__(self, ref, pad, fx, fy, frot, net, back=False):
        self.ref, self.number = ref, pad.number
        # KiCad footprint rotation: positive = counter-clockwise on screen; local pad (x, y) with y down.
        # Rotating a y-down vector by +deg ccw on screen: x' = x cos + y sin ; y' = -x sin + y cos
        # Back-side footprints are stored flipped about the x axis (local y negated, F/B layers swapped).
        py = -pad.y if back else pad.y
        r = math.radians(frot)
        self.x = fx + pad.x * math.cos(r) + py * math.sin(r)
        self.y = fy - pad.x * math.sin(r) + py * math.cos(r)
        self.rot = ((-pad.rot if back else pad.rot) + frot) % 360
        self.sx, self.sy, self.shape, self.kind = pad.sx, pad.sy, pad.shape, pad.kind
        self.layers = [flip_layer(l) for l in pad.layers] if back else pad.layers
        self.net = net
        self.drill = pad.drill
        rr = math.radians(self.rot)
        self.hx = abs(self.sx / 2 * math.cos(rr)) + abs(self.sy / 2 * math.sin(rr))
        self.hy = abs(self.sx / 2 * math.sin(rr)) + abs(self.sy / 2 * math.cos(rr))

    def on_layer(self, layer):
        if self.kind in ("thru_hole", "np_thru_hole"):
            return True
        return layer in self.layers or "*.Cu" in self.layers or (layer == "F.Cu" and "F.Cu" in self.layers) or (layer == "B.Cu" and "B.Cu" in self.layers)


class FootprintInst:
    def __init__(self, ref, fp, x, y, rot, comp, nets_by_pad, side="F.Cu"):
        self.ref, self.fp, self.x, self.y, self.rot, self.comp = ref, fp, x, y, rot, comp
        self.side = side
        self.back = side == "B.Cu"
        self.uuid = uid_for("fp:" + ref)
        self.pads = [PadInst(ref, p, x, y, rot, nets_by_pad.get(p.number), back=self.back) for p in fp.pads]
        self.ref_pos = None      # optional (dx, dy, rot) for the reference text, footprint-local

    def _rot_box(self, b):
        if self.back:
            b = (b[0], -b[3], b[2], -b[1])
        pts = [rot_pt(b[0], b[1], -self.rot), rot_pt(b[2], b[3], -self.rot), rot_pt(b[0], b[3], -self.rot), rot_pt(b[2], b[1], -self.rot)]
        return [self.x + p[0] for p in pts], [self.y + p[1] for p in pts]

    def bbox(self, margin=0.0):
        """board-space bounding box of courtyard + pads (EasyEDA courtyards often cover the body only)"""
        xs, ys = self._rot_box(self.fp.courtyard)
        for p in self.pads:
            xs += [p.x - p.hx, p.x + p.hx]
            ys += [p.y - p.hy, p.y + p.hy]
        return min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin

    def silk_bbox(self, margin=0.0):
        """board-space bounding box of courtyard + pads + silkscreen outline"""
        b = self.bbox(margin)
        if not self.fp.silk:
            return b
        xs, ys = self._rot_box(self.fp.silk)
        return min(b[0], min(xs) - margin), min(b[1], min(ys) - margin), max(b[2], max(xs) + margin), max(b[3], max(ys) + margin)


class Board:
    def __init__(self, layers=4, title="", thickness=1.6, height=100.0):
        self.height = height              # board height: the aux (drill/pos) origin sits at the bottom-left corner
        self.layers = LAYERS_4 if layers == 4 else LAYERS_2
        self.nlayers = layers
        self.title = title
        self.thickness = thickness
        self.nets = {"": Net(0, "")}
        self.footprints = []
        self.tracks = []        # (x1,y1,x2,y2,width,layer,netcode)
        self.vias = []          # (x,y,size,drill,netcode)
        self.zones = []         # dicts
        self.graphics = []      # raw sexp strings
        self.texts = []
        self.text_items = []    # (text, x, y, size, rot) on F.SilkS, for label placement
        self.outline = None     # (x1,y1,x2,y2) or polygon pts
        self.design = {}
        self.netclass_names = {}   # net name -> class

    # ---- nets ----------------------------------------------------------------------------
    def net(self, name):
        if name not in self.nets:
            self.nets[name] = Net(len(self.nets), name)
        return self.nets[name]

    def netcode(self, name):
        return self.net(name).code if name else 0

    # ---- items ---------------------------------------------------------------------------
    def add_footprint(self, inst):
        self.footprints.append(inst)
        return inst

    def track(self, x1, y1, x2, y2, width, layer, netname):
        if abs(x1 - x2) < 1e-6 and abs(y1 - y2) < 1e-6:
            return
        self.tracks.append((round(x1, 6), round(y1, 6), round(x2, 6), round(y2, 6), width, layer, self.netcode(netname)))

    def via(self, x, y, netname, size=0.6, drill=0.3):
        self.vias.append((round(x, 6), round(y, 6), size, drill, self.netcode(netname)))

    def zone(self, netname, layers, pts, priority=0, name="", clearance=0.3, min_thickness=0.25, thermal_gap=0.4, bridge=0.4, keepout=None, pad_connect="thermal"):
        self.zones.append(dict(net=netname, layers=layers, pts=pts, priority=priority, name=name, clearance=clearance,
                               min_thickness=min_thickness, thermal_gap=thermal_gap, bridge=bridge, keepout=keepout, pad_connect=pad_connect))

    def gr_line(self, x1, y1, x2, y2, layer="Edge.Cuts", width=0.1):
        self.graphics.append('  (gr_line (start %s %s) (end %s %s) (stroke (width %s) (type default)) (layer %s) (uuid %s))' % (
            num(x1), num(y1), num(x2), num(y2), num(width), q(layer), q(uid())))

    def gr_rect(self, x1, y1, x2, y2, layer="Edge.Cuts", width=0.1):
        self.graphics.append('  (gr_rect (start %s %s) (end %s %s) (stroke (width %s) (type default)) (fill no) (layer %s) (uuid %s))' % (
            num(x1), num(y1), num(x2), num(y2), num(width), q(layer), q(uid())))

    def gr_text(self, text, x, y, layer="F.SilkS", size=1.0, thickness=0.15, rot=0, justify=None, mirror=False):
        eff = "(effects (font (size %s %s) (thickness %s)%s)%s)" % (num(size), num(size), num(thickness), "" if not mirror else "", (" (justify %s%s)" % (justify or "", " mirror" if mirror else "")) if (justify or mirror) else "")
        self.texts.append('  (gr_text %s (at %s %s %s) (layer %s) (uuid %s) %s)' % (q(text), num(x), num(y), num(rot), q(layer), q(uid()), eff))
        if layer == "F.SilkS":
            self.text_items.append((text, x, y, size, rot))

    # ---- writer --------------------------------------------------------------------------
    def write(self, path, project_name):
        L = ['(kicad_pcb', '\t(version 20241229)', '\t(generator "class_board_gen")', '\t(generator_version "1.0")',
             '\t(general (thickness %s) (legacy_teardrops no))' % num(self.thickness), '\t(paper "A3")',
             '\t(title_block (title %s) (date "2026-09-07") (rev "A") (company "TIGP class board 2026"))' % q(self.title)]
        L.append('\t(layers')
        for lay in self.layers:
            L.append('\t\t(%d %s %s)' % (lay[0], q(lay[1]), lay[2]))
        for lay in USER_LAYERS:
            L.append('\t\t(%d %s %s%s)' % (lay[0], q(lay[1]), lay[2], (" " + q(lay[3])) if len(lay) > 3 else ""))
        L.append('\t)')
        L.append(self.setup_sexp())
        for n in sorted(self.nets.values(), key=lambda n: n.code):
            L.append('\t(net %d %s)' % (n.code, q(n.name)))
        for f in self.footprints:
            L.append(self.footprint_sexp(f, project_name))
        L.extend(self.graphics)
        L.extend(self.texts)
        for (x1, y1, x2, y2, w, layer, net) in self.tracks:
            L.append('\t(segment (start %s %s) (end %s %s) (width %s) (layer %s) (net %d) (uuid %s))' % (num(x1), num(y1), num(x2), num(y2), num(w), q(layer), net, q(uid())))
        for (x, y, size, drill, net) in self.vias:
            L.append('\t(via (at %s %s) (size %s) (drill %s) (layers "F.Cu" "B.Cu") (net %d) (uuid %s))' % (num(x), num(y), num(size), num(drill), net, q(uid())))
        for z in self.zones:
            L.append(self.zone_sexp(z))
        L.append('\t(embedded_fonts no)')
        L.append(')')
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(L) + "\n")

    def setup_sexp(self):
        d = self.design
        if self.nlayers == 4:
            stack = '''\t\t(stackup
\t\t\t(layer "F.SilkS" (type "Top Silk Screen"))
\t\t\t(layer "F.Paste" (type "Top Solder Paste"))
\t\t\t(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
\t\t\t(layer "F.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 1" (type "prepreg") (color "FR4 natural") (thickness 0.2104) (material "FR4 7628") (epsilon_r 4.4) (loss_tangent 0.02))
\t\t\t(layer "In1.Cu" (type "copper") (thickness 0.0152))
\t\t\t(layer "dielectric 2" (type "core") (color "FR4 natural") (thickness 1.065) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
\t\t\t(layer "In2.Cu" (type "copper") (thickness 0.0152))
\t\t\t(layer "dielectric 3" (type "prepreg") (color "FR4 natural") (thickness 0.2104) (material "FR4 7628") (epsilon_r 4.4) (loss_tangent 0.02))
\t\t\t(layer "B.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
\t\t\t(layer "B.Paste" (type "Bottom Solder Paste"))
\t\t\t(layer "B.SilkS" (type "Bottom Silk Screen"))
\t\t\t(copper_finish "HAL lead-free")
\t\t\t(dielectric_constraints no)
\t\t)'''
        else:
            stack = '''\t\t(stackup
\t\t\t(layer "F.SilkS" (type "Top Silk Screen"))
\t\t\t(layer "F.Paste" (type "Top Solder Paste"))
\t\t\t(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
\t\t\t(layer "F.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 1" (type "core") (color "FR4 natural") (thickness 1.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
\t\t\t(layer "B.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
\t\t\t(layer "B.Paste" (type "Bottom Solder Paste"))
\t\t\t(layer "B.SilkS" (type "Bottom Silk Screen"))
\t\t\t(copper_finish "HAL lead-free")
\t\t\t(dielectric_constraints no)
\t\t)'''
        return "\n".join([
            '\t(setup', stack,
            '\t\t(pad_to_mask_clearance 0)', '\t\t(allow_soldermask_bridges_in_footprints no)',
            '\t\t(aux_axis_origin 0 %s)' % num(self.height), '\t\t(allow_soldermask_bridges_in_footprints no)',
            '\t\t(tenting (front yes) (back yes))',
            '\t\t(pcbplotparams (layerselection 0x00000000_00000000_55555555_5755f5ff) (plot_on_all_layers_selection 0x00000000_00000000_00000000_00000000)',
            '\t\t\t(disableapertmacros no) (usegerberextensions yes) (usegerberattributes yes) (usegerberadvancedattributes yes) (creategerberjobfile yes)',
            '\t\t\t(dashed_line_dash_ratio 12) (dashed_line_gap_ratio 3) (svgprecision 4) (plotframeref no) (mode 1) (useauxorigin no)',
            '\t\t\t(hpglpennumber 1) (hpglpenspeed 20) (hpglpendiameter 15) (pdf_front_fp_property_popups yes) (pdf_back_fp_property_popups yes)',
            '\t\t\t(pdf_metadata yes) (pdf_single_document no) (dxfpolygonmode yes) (dxfimperialunits yes) (dxfusepcbnewfont yes) (psnegative no)',
            '\t\t\t(psa4output no) (plot_black_and_white yes) (sketchpadsonfab no) (plotpadnumbers no) (hidednponfab no) (sketchdnponfab yes)',
            '\t\t\t(crossoutdnponfab yes) (subtractmaskfromsilk yes) (outputformat 1) (mirror no) (drillshape 0) (scaleselection 1) (outputdirectory "gerbers/"))',
            '\t)'])

    def footprint_sexp(self, f, project_name):
        fp = f.fp
        node = parse(fp.text)      # fresh tree
        # a board may mix libraries: a footprint is written with the nickname it was loaded from
        fid = "%s:%s" % (getattr(fp, "libnick", "class_board"), fp.name)
        out = []
        out.append('\t(footprint %s' % q(fid))
        out.append('\t\t(layer %s)' % q("B.Cu" if f.back else "F.Cu"))
        back = f.back
        FL = (lambda l: flip_layer(l)) if back else (lambda l: l)
        out.append('\t\t(uuid %s)' % q(f.uuid))
        out.append('\t\t(at %s %s %s)' % (num(f.x), num(f.y), num(f.rot)))
        descr = first(node, "descr")
        if descr:
            out.append('\t\t(descr %s)' % q(descr[1]))
        tags = first(node, "tags")
        if tags:
            out.append('\t\t(tags %s)' % q(tags[1]))
        comp = f.comp
        # properties: Reference/Value visible on silk/fab; others hidden
        props = [("Reference", f.ref, FL("F.SilkS"), False), ("Value", comp.get("value", ""), FL("F.Fab"), False),
                 ("Footprint", fid, FL("F.Fab"), True), ("Datasheet", comp.get("datasheet", ""), FL("F.Fab"), True),
                 ("Description", comp.get("description", ""), FL("F.Fab"), True)]
        for k, v in comp.get("fields", {}).items():
            props.append((k, v, FL("F.Fab"), True))
        rx, ry, rrot = f.ref_pos if f.ref_pos else (0, -(fp.courtyard[3] - fp.courtyard[1]) / 2 - 1.0, 0)
        for k, v, layer, hide in props:
            if k == "Reference":
                at = "(at %s %s %s)" % (num(rx), num(ry), num(rrot))
                size = 1.0
            elif k == "Value":
                at = "(at 0 0 0)"
                size = 1.0
                hide = True
            else:
                at = "(at 0 0 0)"
                size = 1.0
            out.append('\t\t(property %s %s %s (layer %s)%s (uuid %s) (effects (font (size %s %s) (thickness 0.15))%s))' % (
                q(k), q(v), at, q(layer), " (hide yes)" if hide else "", q(uid()), num(size), num(size), " (justify mirror)" if back else ""))
        out.append('\t\t(path %s)' % q(comp.get("path", "")))
        out.append('\t\t(sheetname %s)' % q(comp.get("sheetname", "")))
        out.append('\t\t(sheetfile %s)' % q(comp.get("sheetfile", "")))
        attrs = list(fp.attrs)
        if comp.get("dnp"):
            attrs.append("dnp")
        if not comp.get("in_bom", True):
            for a in ("exclude_from_bom", "exclude_from_pos_files"):
                if a not in attrs:
                    attrs.append(a)
        if not attrs:
            attrs = ["through_hole"] if fp.is_tht() else ["smd"]
        out.append('\t\t(attr %s)' % " ".join(attrs))
        for item in node[2:]:
            if not isinstance(item, list):
                continue
            key = item[0]
            if key in ("layer", "descr", "tags", "property", "attr", "version", "generator", "generator_version", "embedded_fonts", "tedit", "at", "path", "sheetname", "sheetfile"):
                continue
            if key == "pad":
                out.append(self.pad_sexp(item, f))
                continue
            # every instance needs its own item uuids (duplicates confuse KiCad's DRC item lookup)
            if key in ("fp_line", "fp_arc", "fp_circle", "fp_rect", "fp_poly", "fp_text", "fp_text_box", "model", "zone", "group"):
                item = [c for c in item if not (isinstance(c, list) and c and c[0] == "uuid")]
                if key != "model":
                    item = item + [["uuid", uid()]]
                if back and key != "model":
                    item = flip_item(item)
            if key == "fp_text":
                for idx, c in enumerate(item):
                    if isinstance(c, list) and c and c[0] == "at":
                        ang = float(c[3]) if len(c) > 3 else 0.0
                        item[idx] = ["at", c[1], c[2], str(round((ang + f.rot) % 360, 3))]
            out.append(serialize(item, 2))
        out.append('\t\t(embedded_fonts no)')
        out.append('\t)')
        return "\n".join(out)

    def pad_sexp(self, item, f):
        number = item[1]
        # strip any existing net/uuid; KiCad board files store the pad angle as footprint + pad rotation
        children = []
        for c in item[4:]:
            if isinstance(c, list) and c and c[0] in ("net", "uuid", "pinfunction", "pintype"):
                continue
            if isinstance(c, list) and c and c[0] == "at":
                ang = float(c[3]) if len(c) > 3 else 0.0
                if f.back:
                    c = ["at", c[1], str(-float(c[2])), str(round((-ang + f.rot) % 360, 3))]
                else:
                    c = ["at", c[1], c[2], str(round((ang + f.rot) % 360, 3))]
            if f.back and isinstance(c, list) and c and c[0] == "layers":
                c = ["layers"] + [flip_layer(l) for l in c[1:]]
            children.append(c)
        node = list(item[:4]) + children
        s = serialize(node, 2)
        net = None
        for p in f.pads:
            if p.number == number:
                net = p.net
                break
        extra = ""
        if net:
            extra += ' (net %d %s)' % (self.netcode(net), q(net))
        extra += ' (uuid %s)' % q(uid())
        # insert before the final ")"
        return s[:-1].rstrip() + extra + ")"

    def zone_sexp(self, z):
        layers = z["layers"]
        lay = '(layer %s)' % q(layers[0]) if len(layers) == 1 else '(layers %s)' % " ".join(q(l) for l in layers)
        pts = " ".join("(xy %s %s)" % (num(x), num(y)) for x, y in z["pts"])
        L = ['\t(zone (net %d) (net_name %s) %s (uuid %s)' % (self.netcode(z["net"]) if z["net"] else 0, q(z["net"] or ""), lay, q(uid()))]
        if z["name"]:
            L.append('\t\t(name %s)' % q(z["name"]))
        L.append('\t\t(hatch edge 0.5)')
        if z["priority"]:
            L.append('\t\t(priority %d)' % z["priority"])
        if z["keepout"]:
            k = z["keepout"]
            L.append('\t\t(connect_pads (clearance 0))')
            L.append('\t\t(min_thickness 0.25)')
            L.append('\t\t(keepout (tracks %s) (vias %s) (pads %s) (copperpour %s) (footprints %s))' % (
                k.get("tracks", "allowed"), k.get("vias", "allowed"), k.get("pads", "allowed"), k.get("copperpour", "allowed"), k.get("footprints", "allowed")))
            L.append('\t\t(fill (thermal_gap 0.5) (thermal_bridge_width 0.5))')
        else:
            if z["pad_connect"] == "solid":
                L.append('\t\t(connect_pads yes (clearance %s))' % num(z["clearance"]))
            elif z["pad_connect"] == "none":
                L.append('\t\t(connect_pads no (clearance %s))' % num(z["clearance"]))
            else:
                L.append('\t\t(connect_pads (clearance %s))' % num(z["clearance"]))
            L.append('\t\t(min_thickness %s)' % num(z["min_thickness"]))
            L.append('\t\t(filled_areas_thickness no)')
            L.append('\t\t(fill yes (thermal_gap %s) (thermal_bridge_width %s) (island_removal_mode 0) (island_area_min 10))' % (num(z["thermal_gap"]), num(z["bridge"])))
        L.append('\t\t(polygon (pts %s))' % pts)
        L.append('\t)')
        return "\n".join(L)


def flip_item(item):
    """mirror a footprint graphic/text item about the x axis and swap F/B layers (back-side footprint)"""
    out = []
    for c in item:
        if isinstance(c, list) and c:
            k = c[0]
            if k in ("start", "end", "center", "mid", "xy"):
                c = [k, c[1], str(-float(c[2]))] + list(c[3:])
            elif k == "at":
                ang = float(c[3]) if len(c) > 3 else 0.0
                c = ["at", c[1], str(-float(c[2])), str(round(-ang % 360, 3))]
            elif k == "layer":
                c = ["layer", flip_layer(c[1])]
            elif k == "layers":
                c = ["layers"] + [flip_layer(l) for l in c[1:]]
            elif k == "pts":
                c = ["pts"] + [["xy", p[1], str(-float(p[2]))] if isinstance(p, list) and p and p[0] == "xy" else p for p in c[1:]]
            elif k == "effects":
                c = flip_item(c)
            elif k == "justify":
                c = list(c) + (["mirror"] if "mirror" not in c else [])
        out.append(c)
    if item and item[0] in ("fp_text", "fp_text_box"):
        eff = next((c for c in out if isinstance(c, list) and c and c[0] == "effects"), None)
        if eff is None:
            out.append(["effects", ["justify", "mirror"]])
        elif not any(isinstance(c, list) and c and c[0] == "justify" for c in eff):
            eff.append(["justify", "mirror"])
    return out


def serialize(node, indent=0):
    """serialize a parsed s-expression list; strings that look like identifiers stay bare, others quoted."""
    if not isinstance(node, list):
        return atom(node)
    parts = [str(node[0]) if not isinstance(node[0], list) else serialize(node[0])]
    for c in node[1:]:
        parts.append(serialize(c) if isinstance(c, list) else atom(c))
    return "\t" * indent + "(" + " ".join(parts) + ")"


_BARE = re.compile(r'^-?\d+(\.\d+)?$|^[A-Za-z_][A-Za-z0-9_.*-]*$')
_KEYWORDS = {"yes", "no", "smd", "thru_hole", "np_thru_hole", "rect", "circle", "oval", "roundrect", "custom", "trapezoid", "default", "solid", "dash",
             "front", "back", "none", "left", "right", "top", "bottom", "mirror", "through_hole", "exclude_from_pos_files", "exclude_from_bom",
             "allow_missing_courtyard", "allow_soldermask_bridges", "dnp", "board_only", "outline", "background", "italic", "bold",
             "user", "reference", "value", "edge", "full", "chamfered", "hatch", "not_allowed", "allowed", "inner", "outer"}


def atom(a):
    s = str(a)
    if re.match(r'^-?\d+(\.\d+)?$', s):
        return s
    if s in _KEYWORDS:
        return s
    # layer names, footprint names, property values -> quoted
    return q(s)
