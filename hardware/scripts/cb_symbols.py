"""Class-board symbol library generator.

Every BOM line gets one symbol named by its manufacturer part number (or a value-specific
name for passives), with correct pin electrical types, the footprint in the project library,
the datasheet URL and the LCSC / JLC class fields.  Geometry follows the KiCad standard
library conventions (2.54 mm pin grid, pin ends on the 1.27 mm grid).

The symbol definitions are also imported by the schematic generator, which needs the pin
coordinates to compute wire end points.
"""
from sexp import q, num, font

# --------------------------------------------------------------------------------------
# datasheet URLs (verified downloads, see .local/datasheets and docs/design-decisions.md)
DS = {
    "ADS8688": "https://www.ti.com/lit/ds/symlink/ads8688.pdf",
    "DAC8563": "https://www.ti.com/lit/ds/symlink/dac8563.pdf",
    "OPA2192": "https://www.ti.com/lit/ds/symlink/opa2192.pdf",
    "OPA2156": "https://www.ti.com/lit/ds/symlink/opa2156.pdf",
    "INA826": "https://www.ti.com/lit/ds/symlink/ina826.pdf",
    "PGA113": "https://www.ti.com/lit/ds/symlink/pga113.pdf",
    "TL072": "https://www.lcsc.com/datasheet/lcsc_datasheet_1809051915_STMicroelectronics-TL072CDT_C6961.pdf",
    "6N137": "https://www.lcsc.com/datasheet/lcsc_datasheet_1810161120_Lite-On-6N137S-TA1-L_C92651.pdf",
    "AHCT541": "https://www.ti.com/lit/ds/symlink/sn74ahct541.pdf",
    "HCT125": "https://www.lcsc.com/datasheet/lcsc_datasheet_2407241026_Nexperia-74HCT125PW-118_C131316.pdf",
    "LVC1T45": "https://www.ti.com/lit/ds/symlink/sn74lvc1t45.pdf",
    "LVC1G17": "https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf",
    "LM66100": "https://www.ti.com/lit/ds/symlink/lm66100.pdf",
    "AO3400A": "https://www.lcsc.com/datasheet/lcsc_datasheet_1811081213_Alpha---Omega-Semicon-AO3400A_C20917.pdf",
    "MMBT5551": "https://www.lcsc.com/product-detail/C2145.html",
    "AMS1117": "https://www.lcsc.com/datasheet/lcsc_datasheet_2410121508_Advanced-Monolithic-Systems-AMS1117-3-3_C6186.pdf",
    "78L05G": "https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_UTC-Unisonic-Tech-78L05G-AB3-R_C71136.pdf",
    "B0512S": "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2304271700_YLPTEC-B0512S-2WR3_C5369475.pdf",
    "HK4100F": "https://www.lcsc.com/datasheet/lcsc_datasheet_2406241551_Ningbo-Keke-New-Era-Appliance-HK4100F-DC5V-SHG_C12072.pdf",
    "JQC3FF": "https://www.lcsc.com/product-detail/C9221.html",
    "USBC": "https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8588920841703079936",
    "DC005": "https://www.lcsc.com/datasheet/lcsc_datasheet_2211071100_SOFNG-DC005-T20_C111567.pdf",
    "SMA": "https://www.lcsc.com/datasheet/lcsc_datasheet_2405210917_BAT-WIRELESS-BWSMA-KE-Z001_C496549.pdf",
    "KF301-2": "https://www.lcsc.com/datasheet/lcsc_datasheet_2303171000_Cixi-Kefa-Elec-KF301-5-0-2P_C474881.pdf",
    "KF301-3": "https://www.lcsc.com/datasheet/lcsc_datasheet_2303171000_Cixi-Kefa-Elec-KF301-5-0-3P_C474882.pdf",
    "SOCK22": "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2311221543_Megastar-ZX-PM2-54-1-22PY_C7499337.pdf",
    "HDR2x20RA": "https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_Ckmtw-Shenzhen-Cankemeng-B-2100R40P-B110_C124369.pdf",
    "HDR2x20F": "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2203281730_ZHOURI-2-54-2-20_C2977589.pdf",
    "HDR2x10": "https://www.lcsc.com/datasheet/lcsc_datasheet_2003191007_XFCN-PZ254V-12-20P_C492427.pdf",
    "QWIIC": "https://jlcpcb.com/partdetail/XYECONN-XY_SM04B_SRSSTB/C51940130",
    "QWIIC_V": "https://jlcpcb.com/partdetail/XYECONN-XY_BM04B_SRSSTB/C51940129",
    "KF128-10P": "https://www.lcsc.com/product-detail/C474928.html",
    "KF128-2P": "https://www.lcsc.com/product-detail/C474950.html",
    "TCXO": "https://www.lcsc.com/datasheet/lcsc_datasheet_1912111437_KDS-Daishinku-1XTV10000MDA_C253701.pdf",
    "BAV99": "https://www.lcsc.com/datasheet/lcsc_datasheet_2407250951_Nexperia-BAV99-215_C2500.pdf",
    "1N4148W": "https://www.lcsc.com/datasheet/lcsc_datasheet_1811061725_ST-Semtech-1N4148W_C81598.pdf",
    "SMF5.0A": "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2312041000_hongjiacheng-SMF5-0A_C19077497.pdf",
    "FUSE": "https://jlcpcb.com/partdetail/LUTE-1812L15033GR/C18198333",
    "FB": "https://www.lcsc.com/datasheet/lcsc_datasheet_2310301640_Sunlord-GZ1608D601TF_C1002.pdf",
    "LEDR": "https://www.lcsc.com/datasheet/lcsc_datasheet_1810231112_Hubei-KENTO-Elec-KT-0603R_C2286.pdf",
    "LEDG": "https://www.lcsc.com/datasheet/lcsc_datasheet_1806151820_Hubei-KENTO-Elec-KT-0805G_C2297.pdf",
    "LEDY": "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2402181505_XINGLIGHT-XL-1608UYC-06_C965802.pdf",
    # v0.7 / NMR re-spec parts (2026-09-13); pinouts verified against these documents
    "AD9834": "https://www.analog.com/media/en/technical-documentation/data-sheets/AD9834.pdf",
    "SI5351": "https://www.skyworksinc.com/-/media/Skyworks/SL/documents/public/data-sheets/Si5351-B.pdf",
    "X322525": "https://www.lcsc.com/product-detail/C9006.html",
    "OPA564": "https://www.ti.com/lit/ds/symlink/opa564.pdf",
    "OPA1612": "https://www.ti.com/lit/ds/symlink/opa1612.pdf",
    "DG419": "https://www.vishay.com/docs/70051/dg417.pdf",
    "DG413": "https://www.vishay.com/docs/61564/dg411.pdf",
    "TS5A23157": "https://www.ti.com/lit/ds/symlink/ts5a23157.pdf",
    "DRV8871": "https://www.ti.com/lit/ds/symlink/drv8871.pdf",
    "AOD4184A": "https://www.lcsc.com/product-detail/C99124.html",
    "AOD4185": "https://www.lcsc.com/product-detail/C400894.html",
    "UCC27517": "https://www.ti.com/lit/ds/symlink/ucc27517.pdf",
    "SMBJ58A": "https://www.lcsc.com/product-detail/C10226.html",
    "SS54": "https://www.lcsc.com/product-detail/C22452.html",
    "TCA9535": "https://www.ti.com/lit/ds/symlink/tca9535.pdf",
    "TCXO25": "https://www.lcsc.com/product-detail/C47018484.html",
    # NMR re-spec round 3 (notes/2026-09-13-v07-nmr-circuits.md)
    "HC74": "https://assets.nexperia.com/documents/data-sheet/74HC_HCT74.pdf",
    "OPA1656": "https://www.ti.com/lit/ds/symlink/opa1656.pdf",
    "SMBJ": "https://www.littelfuse.com/assetdocs/littelfuse-tvs-diode-smbj-datasheet",
    "BZX84C": "https://www.lcsc.com/product-detail/C112551.html",
    "FUSE5A": "https://www.littelfuse.com/assetdocs/littelfuse-fuse-466-datasheet",
    "LQH32DN": "https://www.lcsc.com/product-detail/C341771.html",
    "RVT100U": "https://www.lcsc.com/product-detail/C37309.html",
    "HV47U": "https://www.lcsc.com/product-detail/C59919.html",
    "RAD4700U": "https://www.lcsc.com/product-detail/C45662.html",
    "GX2512": "https://www.lcsc.com/product-detail/C500718.html",
    "CEMENT5W": "https://www.lcsc.com/product-detail/C1364820.html",
}

FP = "class_board:"   # footprint library nickname

# Chip resistors and ceramic capacitors use KiCad's own standard footprints (user, 2026-09-14): the
# EasyEDA-derived R0603/C0603 lands in class_board.pretty stay in the library for anything else.
CHIP_FP = {"R0603": "Resistor_SMD:R_0603_1608Metric", "R0805": "Resistor_SMD:R_0805_2012Metric",
           "R1206": "Resistor_SMD:R_1206_3216Metric", "R2512": "Resistor_SMD:R_2512_6332Metric",
           "C0603": "Capacitor_SMD:C_0603_1608Metric", "C0805": "Capacitor_SMD:C_0805_2012Metric",
           "C1206": "Capacitor_SMD:C_1206_3216Metric", "C1210": "Capacitor_SMD:C_1210_3225Metric"}


def chip_fp(size):
    """Footprint id for a chip size name such as "R0603" / "C0805"; KiCad standard where one exists."""
    return CHIP_FP.get(size, FP + size)


class Pin:
    __slots__ = ("number", "name", "etype", "x", "y", "angle", "length", "unit", "hide")

    def __init__(self, number, name, etype, x, y, angle, length=2.54, unit=1, hide=False):
        self.number, self.name, self.etype = str(number), name, etype
        self.x, self.y, self.angle, self.length, self.unit, self.hide = x, y, angle, length, unit, hide

    def sexp(self):
        return ('(pin %s line (at %s %s %d) (length %s)%s (name %s %s) (number %s %s))'
                % (self.etype, num(self.x), num(self.y), self.angle, num(self.length),
                   " (hide yes)" if self.hide else "",
                   q(self.name), font(1.27), q(self.number), font(1.27)))


class Symbol:
    def __init__(self, name, ref, value, footprint, description, fields=None,
                 power=False, in_bom=True, on_board=True, units=1, hide_pin_names=False,
                 hide_pin_numbers=False, pin_name_offset=1.016, ref_pos=None, value_pos=None):
        self.name, self.ref, self.value, self.footprint = name, ref, value, footprint
        self.description = description
        self.fields = fields or {}
        self.power, self.in_bom, self.on_board, self.units = power, in_bom, on_board, units
        self.hide_pin_names, self.hide_pin_numbers = hide_pin_names, hide_pin_numbers
        self.pin_name_offset = pin_name_offset
        self.graphics = {u: [] for u in range(0, units + 1)}   # unit 0 = common
        self.pins = []
        self.ref_pos = ref_pos or (0, 0)
        self.value_pos = value_pos or (0, 0)
        self.bbox = None

    def pin(self, *a, **k):
        p = Pin(*a, **k)
        self.pins.append(p)
        return p

    def pin_by_number(self, n):
        for p in self.pins:
            if p.number == str(n):
                return p
        raise KeyError("%s has no pin %s" % (self.name, n))

    def pins_named(self, name):
        return [p for p in self.pins if p.name == name]

    def sexp(self):
        out = ["  (symbol %s" % q(self.name)]
        if self.power:
            out.append("    (power)")
        if self.hide_pin_numbers:
            out.append("    (pin_numbers (hide yes))")
        out.append("    (pin_names (offset %s)%s)" % (num(self.pin_name_offset), " (hide yes)" if self.hide_pin_names else ""))
        out.append("    (exclude_from_sim no) (in_bom %s) (on_board %s)" % ("yes" if self.in_bom else "no", "yes" if self.on_board else "no"))
        rx, ry = self.ref_pos
        vx, vy = self.value_pos
        props = [("Reference", self.ref, (rx, ry), False), ("Value", self.value, (vx, vy), False),
                 ("Footprint", self.footprint, (0, 0), True), ("Datasheet", self.fields.get("Datasheet", ""), (0, 0), True),
                 ("Description", self.description, (0, 0), True)]
        for k, v in self.fields.items():
            if k == "Datasheet":
                continue
            props.append((k, v, (0, 0), True))
        for k, v, (px, py), hide in props:
            if k == "Reference" and self.power:
                hide = True
            out.append("    (property %s %s (at %s %s 0) %s)" % (q(k), q(v), num(px), num(py), font(1.27, hide=hide)))
        for u in range(0, self.units + 1):
            g = list(self.graphics.get(u, []))
            ps = [p.sexp() for p in self.pins if p.unit == u]
            if not g and not ps:
                continue
            out.append("    (symbol %s" % q("%s_%d_1" % (self.name, u)))
            out.extend("      " + x for x in g)
            out.extend("      " + x for x in ps)
            out.append("    )")
        out.append("  )")
        return "\n".join(out)


def rect(x1, y1, x2, y2, fill="background", width=0.254):
    return "(rectangle (start %s %s) (end %s %s) (stroke (width %s) (type default)) (fill (type %s)))" % (
        num(x1), num(y1), num(x2), num(y2), num(width), fill)


def poly(pts, width=0.254, fill="none"):
    return "(polyline (pts %s) (stroke (width %s) (type default)) (fill (type %s)))" % (
        " ".join("(xy %s %s)" % (num(x), num(y)) for x, y in pts), num(width), fill)


def arc(sx, sy, mx, my, ex, ey, width=0.254, fill="none"):
    return "(arc (start %s %s) (mid %s %s) (end %s %s) (stroke (width %s) (type default)) (fill (type %s)))" % (
        num(sx), num(sy), num(mx), num(my), num(ex), num(ey), num(width), fill)


def circle(cx, cy, r, width=0.254, fill="none"):
    return "(circle (center %s %s) (radius %s) (stroke (width %s) (type default)) (fill (type %s)))" % (
        num(cx), num(cy), num(r), num(width), fill)


def text(s, x, y, size=1.27):
    return "(text %s (at %s %s 0) %s)" % (q(s), num(x), num(y), font(size))


# --------------------------------------------------------------------------------------
def box_symbol(name, ref, value, footprint, description, left=(), right=(), top=(), bottom=(),
               fields=None, width=None, pin_len=2.54, in_bom=True):
    """Rectangular IC/connector symbol.

    left/right: sequences of (number, name, etype) or None for a gap, listed top->bottom.
    top/bottom: listed left->right.  Pins sit on a 2.54 mm grid; body edges are on 1.27.
    """
    s = Symbol(name, ref, value, footprint, description, fields=fields, in_bom=in_bom)
    left, right = list(left), list(right)
    if top:      # vertical pin names occupy the top rows: keep side pins clear of them
        left, right = [None, None] + left, [None, None] + right
    if bottom:
        left, right = left + [None, None], right + [None, None]
    n_side = max(len(left), len(right), 1)
    n_tb = max(len(top), len(bottom))
    longest = 0
    for grp in (left, right):
        for p in grp:
            if p:
                longest = max(longest, len(p[1]))
    if width is None:
        width = max(2.54 * (n_tb + 1), 2.54 * 4, 1.27 * (2 * longest + 8) if (left and right) else 1.27 * (longest + 8))
        width = 2.54 * round(width / 2.54)
    if n_tb:
        width = max(width, 2.54 * (n_tb + 1))
    half_w = width / 2
    height = 2.54 * (n_side + 1)
    if top or bottom:
        height = max(height, 2.54 * 3)
    half_h = height / 2
    s.graphics[0].append(rect(-half_w, half_h, half_w, -half_h))
    s.bbox = (-half_w, -half_h, half_w, half_h)

    def col(grp, xside, angle):
        n = len(grp)
        y0 = 2.54 * (n - 1) / 2
        for i, p in enumerate(grp):
            if p is None:
                continue
            s.pin(p[0], p[1], p[2], xside, y0 - 2.54 * i, angle, pin_len)
    col(left, -half_w - pin_len, 0)
    col(right, half_w + pin_len, 180)

    def row(grp, yside, angle):
        n = len(grp)
        x0 = -2.54 * (n - 1) / 2
        for i, p in enumerate(grp):
            if p is None:
                continue
            s.pin(p[0], p[1], p[2], x0 + 2.54 * i, yside, angle, pin_len)
    row(top, half_h + pin_len, 270)
    row(bottom, -half_h - pin_len, 90)
    s.ref_pos = (-half_w, half_h + 1.27)
    s.value_pos = (-half_w, -half_h - 1.27)
    return s


def two_pin(name, ref, value, footprint, description, kind, fields=None, in_bom=True, pin_names=("", "")):
    """Vertical 2-pin passive: pin 1 at top (0,3.81), pin 2 at bottom (0,-3.81)."""
    s = Symbol(name, ref, value, footprint, description, fields=fields, in_bom=in_bom,
               hide_pin_numbers=True, hide_pin_names=True, pin_name_offset=0)
    g = s.graphics[0]
    if kind == "R":
        g.append(rect(-1.016, -2.54, 1.016, 2.54, fill="none"))
        L = 1.27
        s.ref_pos, s.value_pos = (2.032, 1.27), (2.032, -1.27)
    elif kind == "C":
        g.append(poly([(-2.032, 0.762), (2.032, 0.762)], 0.508))
        g.append(poly([(-2.032, -0.762), (2.032, -0.762)], 0.508))
        L = 2.794
        s.ref_pos, s.value_pos = (1.27, 2.032), (1.27, -2.032)
    elif kind == "CP":     # polarised: pin 1 = + (straight plate), pin 2 = - (curved plate)
        g.append(poly([(-2.032, 0.762), (2.032, 0.762)], 0.508))
        g.append(arc(-2.032, -0.508, 0, -1.524, 2.032, -0.508, 0.508))
        g.append(poly([(-2.921, 1.524), (-2.159, 1.524)], 0))
        g.append(poly([(-2.54, 1.143), (-2.54, 1.905)], 0))
        L = 2.794
        s.ref_pos, s.value_pos = (1.27, 2.032), (1.27, -2.032)
    elif kind == "L":
        for y0 in (1.905, 0.635, -0.635, -1.905):
            g.append(arc(0, y0 + 0.635, 0.635, y0, 0, y0 - 0.635))
        L = 1.27
        s.ref_pos, s.value_pos = (2.032, 1.27), (2.032, -1.27)
    elif kind == "FB":
        g.append(poly([(-2.7686, 0.4064), (-1.7018, 2.2606), (2.7686, -0.3048), (1.6764, -2.159), (-2.7686, 0.4064)], 0))
        L = 2.54
        s.ref_pos, s.value_pos = (3.81, 1.27), (3.81, -1.27)
    elif kind == "FUSE":
        g.append(rect(-0.762, -2.54, 0.762, 2.54, fill="none"))
        g.append(poly([(0, 2.54), (0, -2.54)], 0))
        g.append(poly([(-1.524, 2.54), (-1.524, 1.524), (1.524, -1.524), (1.524, -2.54)], 0))
        L = 1.27
        s.ref_pos, s.value_pos = (2.032, 1.27), (2.032, -1.27)
    else:
        raise ValueError(kind)
    s.pin(1, pin_names[0], "passive", 0, 3.81, 270, L)
    s.pin(2, pin_names[1], "passive", 0, -3.81, 90, L)
    s.bbox = (-2.54, -3.81, 2.54, 3.81)
    return s


def diode(name, ref, value, footprint, description, kind="D", fields=None, k_pin=1, a_pin=2, nc_pin=None):
    """Horizontal diode: cathode (K) on the left pin at (-3.81,0), anode (A) on the right (3.81,0).
    nc_pin adds the unused third lead of a 3-pad SOT-23 diode package (hidden, no_connect)."""
    s = Symbol(name, ref, value, footprint, description, fields=fields, hide_pin_numbers=True,
               hide_pin_names=True)
    g = s.graphics[0]
    g.append(poly([(-1.27, 1.27), (-1.27, -1.27)]))                         # cathode bar
    g.append(poly([(1.27, 1.27), (1.27, -1.27), (-1.27, 0), (1.27, 1.27)]))  # triangle pointing left (to K)
    if kind in ("TVS", "ZENER"):
        g.append(poly([(-1.27, 1.27), (-1.778, 1.27)], 0.254))
        g.append(poly([(-1.27, -1.27), (-0.762, -1.27)], 0.254))
    if kind == "LED":
        g.append(poly([(-3.048, -0.762), (-4.572, -2.286), (-3.81, -2.286), (-4.572, -2.286), (-4.572, -1.524)], 0))
        g.append(poly([(-1.778, -0.762), (-3.302, -2.286), (-2.54, -2.286), (-3.302, -2.286), (-3.302, -1.524)], 0))
    s.pin(k_pin, "K", "passive", -3.81, 0, 0, 2.54)
    s.pin(a_pin, "A", "passive", 3.81, 0, 180, 2.54)
    if nc_pin is not None:
        s.pin(nc_pin, "NC", "no_connect", 0, -3.81, 90, 2.54, hide=True)
    s.ref_pos, s.value_pos = (0, 2.54), (0, -2.54)
    s.bbox = (-3.81, -1.905, 3.81, 1.905)
    return s


def bav99(name, footprint, fields):
    """BAV99 dual series diode: pin 1 = A1 (anode D1), pin 2 = K2 (cathode D2),
    pin 3 = common (K1 + A2).  Pin 1 left, pin 2 right, pin 3 bottom centre."""
    s = Symbol(name, "D", "BAV99", footprint, "Dual series switching diode, SOT-23 (clamp pair): 1=A1 2=K2 3=K1/A2",
               fields=fields, hide_pin_names=True)
    g = s.graphics[0]
    g.append(poly([(-3.81, 1.27), (-3.81, -1.27), (-1.27, 0), (-3.81, 1.27)]))   # D1 anode(1)->K at common
    g.append(poly([(-1.27, 1.27), (-1.27, -1.27)]))
    g.append(poly([(1.27, 1.27), (1.27, -1.27), (3.81, 0), (1.27, 1.27)]))       # D2 anode(common)->K(2)
    g.append(poly([(3.81, 1.27), (3.81, -1.27)]))
    g.append(poly([(-1.27, 0), (1.27, 0)], 0))
    g.append(poly([(0, 0), (0, -2.54)], 0))
    s.pin(1, "A1", "passive", -6.35, 0, 0, 2.54)
    s.pin(2, "K2", "passive", 6.35, 0, 180, 2.54)
    s.pin(3, "COM", "passive", 0, -5.08, 90, 2.54)
    s.ref_pos, s.value_pos = (0, 2.54), (0, 3.81)
    s.bbox = (-6.35, -5.08, 6.35, 1.905)
    return s


def npn(name, value, footprint, description, fields, pins=("1", "2", "3")):
    """NPN: base pin left (-2.54,0), collector top (2.54,5.08), emitter bottom (2.54,-5.08).
    pins = (B, E, C) numbers  (SOT-23 MMBT5551: 1=B, 2=E, 3=C)."""
    s = Symbol(name, "Q", value, footprint, description, fields=fields, hide_pin_names=True)
    g = s.graphics[0]
    g.append(poly([(0.635, 1.27), (0.635, -1.27)], 0.508))
    g.append(poly([(0.635, 0.635), (2.54, 2.54)]))
    g.append(poly([(0.635, -0.635), (2.54, -2.54)]))
    g.append(poly([(2.54, -2.54), (1.524, -2.286), (1.905, -1.524), (2.54, -2.54)], 0.254, "outline"))
    g.append(circle(1.27, 0, 2.8, 0.254))
    s.pin(pins[0], "B", "input", -2.54, 0, 0, 3.175)
    s.pin(pins[1], "E", "passive", 2.54, -5.08, 90, 2.54)
    s.pin(pins[2], "C", "passive", 2.54, 5.08, 270, 2.54)
    s.ref_pos, s.value_pos = (5.08, 1.27), (5.08, -1.27)
    s.bbox = (-2.54, -5.08, 5.08, 5.08)
    return s


def nmos(name, value, footprint, description, fields, pins=("1", "2", "3")):
    """N-MOSFET: gate left (-2.54,-1.905), drain top (2.54,5.08), source bottom (2.54,-5.08).
    pins = (G, S, D) numbers (SOT-23 AO3400A: 1=G, 2=S, 3=D)."""
    s = Symbol(name, "Q", value, footprint, description, fields=fields, hide_pin_names=True)
    g = s.graphics[0]
    g.append(poly([(0.254, 2.54), (0.254, -2.54)], 0.254))
    for y in (1.905, 0, -1.905):
        g.append(poly([(0.762, y + 0.635), (0.762, y - 0.635)], 0.508))
    g.append(poly([(0.762, 1.905), (2.54, 1.905), (2.54, 2.54)]))
    g.append(poly([(0.762, -1.905), (2.54, -1.905), (2.54, -2.54)]))
    g.append(poly([(0.762, 0), (2.54, 0), (2.54, -1.905)]))
    g.append(poly([(1.27, 0.508), (1.905, 0), (1.27, -0.508), (1.27, 0.508)], 0.254, "outline"))
    g.append(circle(1.524, 0, 2.8, 0.254))
    s.pin(pins[0], "G", "input", -2.54, -2.54, 0, 2.794)
    s.pin(pins[1], "S", "passive", 2.54, -5.08, 90, 2.54)
    s.pin(pins[2], "D", "passive", 2.54, 5.08, 270, 2.54)
    s.ref_pos, s.value_pos = (5.08, 1.27), (5.08, -1.27)
    s.bbox = (-2.54, -5.08, 5.08, 5.08)
    return s


def pmos(name, value, footprint, description, fields, pins=("1", "2", "3")):
    """P-MOSFET: the vertical mirror of nmos() - gate left (-2.54,+2.54), source top (2.54,5.08),
    drain bottom (2.54,-5.08), body-diode arrow pointing out of the channel.
    pins = (G, S, D) numbers (TO-252 AOD4185: 1=G, 2=D/tab, 3=S)."""
    s = Symbol(name, "Q", value, footprint, description, fields=fields, hide_pin_names=True)
    g = s.graphics[0]
    g.append(poly([(0.254, 2.54), (0.254, -2.54)], 0.254))
    for y in (1.905, 0, -1.905):
        g.append(poly([(0.762, y + 0.635), (0.762, y - 0.635)], 0.508))
    g.append(poly([(0.762, 1.905), (2.54, 1.905), (2.54, 2.54)]))
    g.append(poly([(0.762, -1.905), (2.54, -1.905), (2.54, -2.54)]))
    g.append(poly([(0.762, 0), (2.54, 0), (2.54, 1.905)]))
    g.append(poly([(1.905, 0.508), (1.27, 0), (1.905, -0.508), (1.905, 0.508)], 0.254, "outline"))
    g.append(circle(1.524, 0, 2.8, 0.254))
    s.pin(pins[0], "G", "input", -2.54, 2.54, 0, 2.794)
    s.pin(pins[1], "S", "passive", 2.54, 5.08, 270, 2.54)
    s.pin(pins[2], "D", "passive", 2.54, -5.08, 90, 2.54)
    s.ref_pos, s.value_pos = (5.08, 1.27), (5.08, -1.27)
    s.bbox = (-2.54, -5.08, 5.08, 5.08)
    return s


def crystal4(name, value, footprint, description, fields, pin_names=("OSC1", "GND", "OSC2", "GND")):
    """4-pad SMD crystal: pins 1 and 3 are the terminals (left/right), pins 2 and 4 the case
    tabs on the bottom (v0.7 lib report section 6: terminals sit on one diagonal, tabs on the other)."""
    s = Symbol(name, "Y", value, footprint, description, fields=fields, pin_name_offset=0)
    g = s.graphics[0]
    g.append(rect(-0.508, 1.778, 0.508, -1.778, fill="none"))          # quartz plate
    g.append(poly([(-1.016, 1.778), (-1.016, -1.778)], 0.508))          # electrode
    g.append(poly([(1.016, 1.778), (1.016, -1.778)], 0.508))            # electrode
    g.append(poly([(-2.54, 0), (-1.016, 0)], 0))
    g.append(poly([(1.016, 0), (2.54, 0)], 0))
    g.append(poly([(-2.54, -2.54), (-2.54, -2.032), (2.54, -2.032), (2.54, -2.54)], 0))   # case tabs
    s.pin(1, pin_names[0], "passive", -5.08, 0, 0, 2.54)
    s.pin(3, pin_names[2], "passive", 5.08, 0, 180, 2.54)
    s.pin(2, pin_names[1], "passive", -2.54, -5.08, 90, 2.54)
    s.pin(4, pin_names[3], "passive", 2.54, -5.08, 90, 2.54)
    s.ref_pos, s.value_pos = (0, 2.794), (0, 4.064)
    s.bbox = (-5.08, -5.08, 5.08, 2.54)
    return s


def dual_opamp(name, value, footprint, description, fields, pins):
    """Dual op-amp, three units: A, B and power."""
    s = Symbol(name, "U", value, footprint, description, fields=fields, units=3, pin_name_offset=0.254)
    tri = poly([(-5.08, 5.08), (5.08, 0), (-5.08, -5.08), (-5.08, 5.08)], 0.254, "background")
    for u, (o, m, p) in ((1, ("OUTA", "-INA", "+INA")), (2, ("OUTB", "-INB", "+INB"))):
        s.graphics[u].append(tri)
        s.pin(pins[o], "", "output", 7.62, 0, 180, 2.54, unit=u)
        s.pin(pins[m], "-", "input", -7.62, -2.54, 0, 2.54, unit=u)
        s.pin(pins[p], "+", "input", -7.62, 2.54, 0, 2.54, unit=u)
    s.graphics[3].append(poly([(-2.54, 2.54), (2.54, 0), (-2.54, -2.54), (-2.54, 2.54)], 0.254, "background"))
    s.pin(pins["V+"], "V+", "power_in", 0, 7.62, 270, 5.08, unit=3)
    s.pin(pins["V-"], "V-", "power_in", 0, -7.62, 90, 5.08, unit=3)
    s.ref_pos, s.value_pos = (0, 5.08), (0, -5.08)
    s.bbox = (-7.62, -7.62, 7.62, 7.62)
    return s


def power_symbol(net, style="bar"):
    s = Symbol("PWR_" + net.replace("+", "p").replace("-", "n"), "#PWR", net, "", "Power symbol: " + net,
               power=True, hide_pin_numbers=True, hide_pin_names=True, pin_name_offset=0)
    g = s.graphics[0]
    if style == "gnd":
        g.append(poly([(0, 0), (0, -1.27), (1.27, -1.27), (0, -2.54), (-1.27, -1.27), (0, -1.27)], 0))
        s.pin(1, net, "power_in", 0, 0, 270, 0)
        s.value_pos = (0, -3.81)
    elif style == "agnd":
        g.append(poly([(0, 0), (0, -1.27)], 0))
        g.append(poly([(-1.27, -1.27), (1.27, -1.27)], 0.254))
        g.append(poly([(-0.762, -1.905), (0.762, -1.905)], 0.254))
        g.append(poly([(-0.254, -2.54), (0.254, -2.54)], 0.254))
        s.pin(1, net, "power_in", 0, 0, 270, 0)
        s.value_pos = (0, -3.81)
    elif style == "neg":
        g.append(poly([(0, 0), (0, -1.27)], 0))
        g.append(poly([(-1.27, -1.27), (1.27, -1.27)], 0.254))
        s.pin(1, net, "power_in", 0, 0, 270, 0)
        s.value_pos = (0, -2.54)
    else:
        g.append(poly([(0, 0), (0, 1.27)], 0))
        g.append(poly([(-1.27, 1.27), (1.27, 1.27)], 0.254))
        s.pin(1, net, "power_in", 0, 0, 90, 0)
        s.value_pos = (0, 2.54)
    s.in_bom = False
    return s


# --------------------------------------------------------------------------------------
def build_library():
    S = {}

    def add(sym):
        assert sym.name not in S, sym.name
        S[sym.name] = sym
        return sym

    def f(lcsc, jlc, mpn, mfr, ds, **extra):
        d = {"LCSC": lcsc, "JLC_CLASS": jlc, "MPN": mpn, "Manufacturer": mfr, "Datasheet": ds}
        d.update(extra)
        return d

    # ---- passives (one symbol per BOM line) --------------------------------------------
    R = [("0", "0603WAF0000T5E", "C21189", "Basic"), ("33", "0603WAF330JT5E", "C23140", "Basic"),
         ("49.9", "0603WAF499JT5E", "C23185", "Basic"), ("100", "0603WAF1000T5E", "C22775", "Basic"),
         ("220", "0603WAF2200T5E", "C22962", "Basic"), ("1k", "0603WAF1001T5E", "C21190", "Basic"),
         ("2.2k", "0603WAF2201T5E", "C4190", "Basic"), ("4.7k", "0603WAF4701T5E", "C23162", "Basic"),
         ("5.1k", "0603WAF5101T5E", "C23186", "Basic"), ("10k", "0603WAF1002T5E", "C25804", "Basic"),
         ("40.2k", "0603WAF4022T5E", "C12447", "Preferred"), ("100k", "0603WAF1003T5E", "C25803", "Basic"),
         # NMR re-spec values (LCSC numbers verified against the JLCPCB component API, 2026-09-13)
         ("10", "0603WAF100JT5E", "C22859", "Basic"), ("200", "0603WAF2000T5E", "C8218", "Basic"),
         ("270", "0603WAF2700T5E", "C22966", "Basic"), ("910", "0603WAF9100T5E", "C23264", "Extended"),
         ("6.8k", "0603WAF6801T5E", "C23212", "Basic"), ("6.49k", "0603WAF6491T5E", "C23088", "Extended"),
         ("11k", "0603WAF1102T5E", "C25950", "Basic"), ("47k", "0603WAF4702T5E", "C25819", "Basic"),
         ("1M", "0603WAF1004T5E", "C22935", "Basic")]
    for val, mpn, lcsc, cls in R:
        add(two_pin("R0603_" + val.replace(".", "R"), "R", val, chip_fp("R0603"),
                    "Resistor %s 1%% 0603 100 mW (Uniroyal %s)" % (val, mpn), "R",
                    fields=f(lcsc, cls, mpn, "UNI-ROYAL", "https://www.lcsc.com/product-detail/%s.html" % lcsc)))
    C = [("100nF", "CC0603KRX7R9BB104", "C14663", "C0603", "100 nF 50 V X7R 0603", "Yageo", "Basic"),
         ("1nF", "CL10B102KB8NNNC", "C1588", "C0603", "1 nF 50 V X7R 0603 (input RC)", "Samsung", "Basic"),
         ("10nF", "CL10B103KB8NNNC", "C1589", "C0603", "10 nF 50 V X7R 0603", "Samsung", "Basic"),
         ("1uF", "CL10A105KB8NNNC", "C15849", "C0603", "1 uF 50 V X5R 0603", "Samsung", "Basic"),
         ("4.7uF", "CL10A475KA8NQNC", "C69335", "C0603", "4.7 uF 25 V X5R 0603", "Samsung", "Extended"),
         ("10uF", "CL21A106KAYNNNE", "C15850", "C0805", "10 uF 25 V X5R 0805", "Samsung", "Basic"),
         ("22uF", "CL31A226KAHNNNE", "C12891", "C1206", "22 uF 25 V X5R 1206", "Samsung", "Basic"),
         # C0G/NP0 filter, tank and timing capacitors (NMR re-spec); C0G is required, not a preference
         ("20pF", "CL10C200JB8NNNC", "C1648", "C0603", "20 pF 50 V C0G 5% 0603", "Samsung", "Basic"),
         ("22pF", "CL10C220JB8NNNC", "C1653", "C0603", "22 pF 50 V C0G 5% 0603 (tank trim)", "Samsung", "Basic"),
         ("47pF", "CL10C470JB8NNNC", "C1671", "C0603", "47 pF 50 V C0G 5% 0603 (CLK1 shunt)", "Samsung", "Basic"),
         ("100pF", "CL10C101JB8NNNC", "C14858", "C0603", "100 pF 50 V C0G 5% 0603", "Samsung", "Basic"),
         ("130pF", "CC0603JRNPO9BN131", "C519399", "C0603", "130 pF 50 V NP0 5% 0603 (filter C3)", "YAGEO", "Extended"),
         ("390pF", "CC0603JRNPO9BN391", "C107050", "C0603", "390 pF 50 V NP0 5% 0603 (filter C1)", "YAGEO", "Extended"),
         ("560pF", "CC0603JRNPO0BN561", "C513644", "C0603", "560 pF 100 V NP0 5% 0603 (IF active pole)", "YAGEO", "Extended"),
         ("1.2nF", "CC0603JRNPO9BN122", "C576816", "C0603", "1.2 nF 50 V NP0 5% 0603 (tank trim)", "YAGEO", "Extended"),
         ("10uF", "CL31B106KBHNNNE", "C89632", "C1206", "10 uF 50 V X7R 1206 (coil DC block)", "Samsung", "Extended")]
    for val, mpn, lcsc, fp, desc, mfr, cls in C:
        add(two_pin("C%s_%s" % (fp[1:], val), "C", val, chip_fp(fp), "Capacitor " + desc + " (%s %s)" % (mfr, mpn), "C",
                    fields=f(lcsc, cls, mpn, mfr, "https://www.lcsc.com/product-detail/%s.html" % lcsc)))
    # ---- round-3 discrete passives (NMR re-spec) ---------------------------------------
    # 3.9 pF is the stocked NP0 value nearest the 4 pF the Si5351 crystal note asks for; the
    # symbol keeps the name C0603_4pF because that is the design value the sheet modules ask for.
    add(two_pin("C0603_4pF", "C", "3.9pF", chip_fp("C0603"),
                "Capacitor 3.9 pF 50 V NP0 0603 (Si5351 crystal load; circuits note 1.2 asks for 4 pF - "
                "3.9 pF is the stocked NP0 value, XTAL_CL = 10 pF unchanged) (YAGEO CC0603BRNPO9BN3R9)", "C",
                fields=f("C519107", "Extended", "CC0603BRNPO9BN3R9", "YAGEO", "https://www.lcsc.com/product-detail/C519107.html")))
    # 0.1 % thin film (Yageo RT0603BRD07 series): the difference-amp and inverter ratios.
    # Named with the trailing zeros the design uses, so the sheet modules pick these over the 1 % parts.
    for val, mpn, lcsc, desc in (
            ("1.00k", "RT0603BRD071KL", "C110776", "IF series / difference-amp input"),
            ("10.0k", "RT0603BRD0710KL", "C95204", "stage-1 feedback and the unity-gain inverter pair"),
            ("20.0k", "RT0603BRD0720KL", "C723637", "difference-amp feedback, G_diff = 20")):
        add(two_pin("R0603_" + val, "R", val, chip_fp("R0603"),
                    "Resistor %s ohm 0.1%% 25 ppm thin film 0603 (%s; 0.1%% gives CMRR ~54 dB where 1%% gives 34 dB)" % (val, desc), "R",
                    fields=f(lcsc, "Extended", mpn, "YAGEO", "https://www.lcsc.com/product-detail/%s.html" % lcsc)))
    add(two_pin("R0603_9R09k", "R", "9.1k", chip_fp("R0603"),
                "Resistor 9.1 kOhm 1% 0603 fitted where the design says 9.09 kOhm (stage-2 gain 10.01 instead of 10.00). "
                "The exact E96 9.09 kOhm is C23125 (Extended, 93 k stock) if the ratio must be exact (UNI-ROYAL 0603WAF9101T5E)", "R",
                fields=f("C23260", "Basic", "0603WAF9101T5E", "UNI-ROYAL", "https://www.lcsc.com/product-detail/C23260.html")))
    add(two_pin("R0603_32k", "R", "32k", chip_fp("R0603"),
                "Resistor 32 kOhm 0.1% thin film 0603 (DRV8871 ILIM, I_TRIP = 64/R_kOhm = 2.0 A - the trip point is "
                "directly proportional to it).  No 1% thick-film 32 k is stocked; this thin-film part is the JLC option (YAGEO RT0603BRD0732KL)", "R",
                fields=f("C861325", "Extended", "RT0603BRD0732KL", "YAGEO", "https://www.lcsc.com/product-detail/C861325.html")))
    add(two_pin("R0805_10R", "R", "10", chip_fp("R0805"),
                "Resistor 10 ohm 1% 0805 125 mW (MOSFET gate resistor / OPA564 output snubber; the land also takes 100 ohm)", "R",
                fields=f("C17415", "Basic", "0805W8F100JT5E", "UNI-ROYAL", "https://www.lcsc.com/product-detail/C17415.html")))
    add(two_pin("R2512_4R7", "R", "4.7 1W", chip_fp("R2512"), "Resistor 4.7 ohm 1% 2512 1 W 200 V", "R",
                fields=f("C2999606", "Extended", "FRC2512F4R70TS", "Ever Ohms", "https://www.lcsc.com/product-detail/C2999606.html")))
    add(two_pin("R2512_0R", "R", "0", chip_fp("R2512"),
                "Link 0 ohm 2512 1 W - bridges the 10 mOhm sense pads when the shunt is not fitted", "R",
                fields=f("C2889851", "Extended", "2512 0R 1W", "Uniroyal", "https://www.lcsc.com/product-detail/C2889851.html")))
    add(two_pin("FB0603_120R_3A", "FB", "120R@100MHz 3A", FP + "L0603",
                "Ferrite bead 120 ohm @100 MHz, 3 A, 100 mOhm DCR, 0603 (OPA564 +VEXT branch - the 600 ohm bead is a "
                "200 mA part and must not be used there) (HCB1608KF-121T30)", "FB",
                fields=f("C353920", "Extended", "HCB1608KF-121T30", "Hua Cheng", "https://www.lcsc.com/product-detail/C353920.html")))
    add(two_pin("R2512_10mR", "R", "10mR", chip_fp("R2512"), "Current-sense resistor 10 mOhm 1% 2512 2 W (polarizer current, DNP; Kelvin-connect)", "R",
                fields=f("C500718", "Extended", "GX2512-2W-10mR-1%", "Gaoxin", DS["GX2512"])))
    add(two_pin("R_5W_2R2", "R", "2.2 5W", FP + "RES-TH_BD9.5-L22.0-P28.00-D1.0",
                "Resistor 2.2 ohm 5 W wirewound/cement axial through-hole, 22 mm body on 28 mm pads (flyback snubber, circuits note 6.1b)", "R",
                fields=f("C1364820", "Extended", "AC05000002208JAC00", "Vishay", DS["CEMENT5W"])))
    add(two_pin("L_15uH", "L", "15uH", FP + "IND-SMD_L3.2-W2.5-LQH32CN1R0M53L",
                "Inductor 15 uH +-10%, 300 mA, SRF 26 MHz, 1210 (Murata LQH32DN150K53L) - reconstruction filter L2", "L",
                fields=f("C341771", "Extended", "LQH32DN150K53L", "Murata", DS["LQH32DN"])))
    add(two_pin("FUSE_0466005", "F", "5A fast", FP + "F1206",
                "Fuse 5 A fast-blow, 32 V, 1206 (Littelfuse 0466005.NRHF) - +VEXT input; not resettable", "FUSE",
                fields=f("C57525", "Extended", "0466005.NRHF", "Littelfuse", DS["FUSE5A"])))
    # polarised capacitors: pin 1 = + (anode).  All three lands have pad 1 = + (silk + sign
    # by pad 1 on the two SMD cans; the polarity stripe on the radial land is beside pad 2).
    add(two_pin("CP_100uF_35V", "C", "100uF 35V", FP + "CAP-SMD_BD8.0-L8.3-W8.3-LS9.3-FD",
                "Aluminium electrolytic 100 uF 35 V, SMD can 8x10 mm (ROQANG RVT1V101M0810) - +VEXT bulk; PIN 1 = +", "CP",
                fields=f("C37309", "Extended", "RVT1V101M0810", "ROQANG", DS["RVT100U"])))
    add(two_pin("CP_47uF_35V", "C", "47uF 35V", FP + "CAP-SMD_BD6.3-L6.6-W6.6-FD",
                "Aluminium electrolytic 47 uF 35 V, SMD can 6.3 mm (Honor HV470M035E055ETR) - OPA564 local bulk; PIN 1 = +", "CP",
                fields=f("C59919", "Extended", "HV470M035E055ETR", "CapXon", DS["HV47U"])))
    add(two_pin("CP_4700uF_50V_THT", "C", "4700uF 50V", FP + "CAP-TH_BD22.0-P10.00-D0.8-FD",
                "Aluminium electrolytic 4700 uF 50 V radial, 22 mm body, 10 mm pitch (flyback snubber option, DNP); PIN 1 = +", "CP",
                fields=f("C45662", "Extended", "KM478M050N35RR0VH2FP0", "Dongguan Chengxing", DS["RAD4700U"])))
    add(two_pin("FB0603_600R", "FB", "600R@100MHz", FP + "L0603", "Ferrite bead 600 ohm @100 MHz 0603 (Sunlord GZ1608D601TF)", "FB",
                fields=f("C1002", "Basic", "GZ1608D601TF", "Sunlord", DS["FB"])))
    add(two_pin("FUSE_1812L150", "F", "1.5A polyfuse", FP + "F1812", "Resettable fuse 1.5 A hold / 3 A trip, 33 V, 1812 (LUTE 1812L150/33GR)", "FUSE",
                fields=f("C18198333", "Extended", "1812L150/33GR", "LUTE", DS["FUSE"])))

    # ---- diodes / LEDs -----------------------------------------------------------------
    add(diode("1N4148W", "D", "1N4148W", FP + "SOD-123F_L2.7-W1.6-LS3.8-RD", "Switching diode 75 V 150 mA SOD-123 (pin 1 = K)",
              fields=f("C81598", "Basic", "1N4148W", "ST(Semtech)", DS["1N4148W"])))
    add(diode("SMF5.0A", "D", "SMF5.0A", FP + "SOD-123FL_L2.7-W1.8-LS3.8-RD", "TVS 5.0 V standoff, 6.4-7.0 V breakdown, 200 W, SOD-123FL (pin 1 = K)", "TVS",
              fields=f("C19077497", "Preferred", "SMF5.0A", "hongjiacheng", DS["SMF5.0A"])))
    add(bav99("BAV99", FP + "SOT-23-3_L2.9-W1.6-P1.90-LS2.8-BR", f("C2500", "Basic", "BAV99,215", "Nexperia", DS["BAV99"])))
    add(diode("SMBJ58A", "D", "SMBJ58A", FP + "SMB_L4.6-W3.6-LS5.3-RD",
              "TVS unidirectional 58 V standoff, 64.4-71.2 V breakdown, 600 W, SMB/DO-214AA (pin 1 = K, pin 2 = A)", "TVS",
              fields=f("C10226", "Extended", "SMBJ58A", "Ruilon", DS["SMBJ58A"])))
    add(diode("SMBJ26A", "D", "SMBJ26A", FP + "SMB_L4.6-W3.6-LS5.3-RD",
              "TVS unidirectional 26 V standoff, 28.9 V breakdown min, ~42 V clamp, 600 W, SMB (pin 1 = K, pin 2 = A) - +VEXT input and DRV8871 VM", "TVS",
              fields=f("C123820", "Extended", "SMBJ26A", "MDD (Microdiode)", DS["SMBJ"])))
    add(diode("SMBJ20A", "D", "SMBJ20A", FP + "SMB_L4.6-W3.6-LS5.3-RD",
              "TVS unidirectional 20 V standoff, 22.2 V breakdown min, ~32.4 V clamp at 18.5 A, 600 W, SMB (pin 1 = K, pin 2 = A) - "
              "polarizer fast-dump clamp; the SMBJ58A must NOT be used there (circuits note 6.1c)", "TVS",
              fields=f("C294873", "Extended", "SMBJ20A", "SEMIWARE", DS["SMBJ"])))
    add(diode("BZX84C12", "D", "BZX84C12", FP + "SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR",
              "Zener 12 V 5% 350 mW, SOT-23 (pin 1 = A, pin 2 = NC, pin 3 = K) - clamps the AOD4185 gate-source to within its +-20 V rating", "ZENER",
              fields=f("C112551", "Extended", "BZX84C12", "Changjiang(CJ)", DS["BZX84C"]), k_pin=3, a_pin=1, nc_pin=2))
    add(diode("SS54", "D", "SS54", FP + "SMA_L4.4-W2.8-LS5.4-R-RD",
              "Schottky rectifier 40 V 5 A, SMA/DO-214AC (pin 1 = A, pin 2 = K - the opposite convention to the SMB TVS above)",
              fields=f("C22452", "Basic", "SS54", "MDD", DS["SS54"]), k_pin=2, a_pin=1))
    add(diode("LED_RED_0603", "D", "RED", FP + "LED-SMD_L1.6-W0.8-R-RD", "LED red 0603 (KENTO KT-0603R), pin 1 = K", "LED",
              fields=f("C2286", "Basic", "KT-0603R", "Hubei KENTO", DS["LEDR"])))
    add(diode("LED_GREEN_0805", "D", "GREEN", FP + "LED0805-R-RD", "LED green 0805 (KENTO KT-0805G), pin 1 = K", "LED",
              fields=f("C2297", "Basic", "KT-0805G", "Hubei KENTO", DS["LEDG"])))
    add(diode("LED_YELLOW_0603", "D", "YELLOW", FP + "LED0603-RD-YELLOW", "LED yellow 0603 (XINGLIGHT XL-1608UYC-06), pin 1 = K", "LED",
              fields=f("C965802", "Extended", "XL-1608UYC-06", "XINGLIGHT", DS["LEDY"])))

    # ---- transistors -------------------------------------------------------------------
    add(npn("MMBT5551", "MMBT5551", FP + "SOT-23-3_L2.9-W1.6-P1.90-LS2.8-BR", "NPN 160 V 600 mA 300 mW SOT-23 (1=B 2=E 3=C)",
            f("C2145", "Basic", "MMBT5551", "Changjing", DS["MMBT5551"]), pins=("1", "2", "3")))
    add(nmos("AO3400A", "AO3400A", FP + "SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR", "N-MOSFET 30 V 5.7 A 48 mOhm@2.5V SOT-23 (1=G 2=S 3=D)",
             f("C20917", "Basic", "AO3400A", "Alpha & Omega", DS["AO3400A"]), pins=("1", "2", "3")))
    add(nmos("AOD4184A", "AOD4184A", FP + "TO-252-2_L6.6-W6.1-P4.57-LS9.9-TL-CW",
             "N-MOSFET 40 V 50 A 8.5 mOhm@10V TO-252/DPAK, tab on the RIGHT (1=G 2=D/tab 3=S)",
             f("C99124", "Basic", "AOD4184A", "Alpha & Omega", DS["AOD4184A"]), pins=("1", "3", "2")))
    add(pmos("AOD4185", "AOD4185", FP + "TO-252-3_L6.6-W6.1-P4.57-LS9.9-BR-CW",
             "P-MOSFET -40 V -40 A 23 mOhm@-10V TO-252/DPAK, tab on the LEFT (1=G 2=D/tab 3=S)",
             f("C400894", "Extended", "AOD4185", "Alpha & Omega", DS["AOD4185"]), pins=("1", "3", "2")))

    # ---- ICs ---------------------------------------------------------------------------
    add(box_symbol("ADS8688IDBTR", "U", "ADS8688IDBTR", FP + "TSSOP-38_L9.7-W4.4-P0.50-LS6.4-BL",
        "8-ch 16-bit SAR ADC, +-10.24 V inputs, 500 kSPS, TSSOP-38",
        left=[("16", "AIN_0P", "input"), ("17", "AIN_0GND", "input"), ("18", "AIN_1P", "input"), ("19", "AIN_1GND", "input"),
              ("21", "AIN_2P", "input"), ("20", "AIN_2GND", "input"), ("23", "AIN_3P", "input"), ("22", "AIN_3GND", "input"),
              ("25", "AIN_4P", "input"), ("24", "AIN_4GND", "input"), ("27", "AIN_5P", "input"), ("26", "AIN_5GND", "input"),
              ("12", "AIN_6P", "input"), ("13", "AIN_6GND", "input"), ("14", "AIN_7P", "input"), ("15", "AIN_7GND", "input"),
              None, ("10", "AUX_IN", "input"), ("11", "AUX_GND", "input"), None,
              ("5", "REFIO", "passive"), ("7", "REFCAP", "passive"), ("6", "REFGND", "power_in"), ("4", "~{REFSEL}", "input")],
        right=[("38", "~{CS}", "input"), ("37", "SCLK", "input"), ("1", "SDI", "input"), ("36", "SDO", "output"),
               ("3", "DAISY", "input"), ("2", "~{RST}/~{PD}", "input"), ("35", "DNC", "no_connect")] + [None] * 17,
        top=[("9", "AVDD", "power_in"), ("30", "AVDD", "power_in"), ("34", "DVDD", "power_in")],
        bottom=[("8", "AGND", "power_in"), ("28", "AGND", "power_in"), ("29", "AGND", "power_in"), ("31", "AGND", "power_in"),
                ("32", "AGND", "power_in"), ("33", "DGND", "power_in")],
        fields=f("C527390", "Extended", "ADS8688IDBTR", "Texas Instruments", DS["ADS8688"]), width=20.32))
    add(box_symbol("DAC8563SDGSR", "U", "DAC8563SDGSR", FP + "VSSOP-10_L3.0-W3.0-P0.50-LS4.9-BL",
        "Dual 16-bit DAC, 2.5 V internal reference, SPI, VSSOP-10",
        left=[("6", "~{SYNC}", "input"), ("7", "SCLK", "input"), ("8", "DIN", "input"), ("4", "~{LDAC}", "input"), ("5", "~{CLR}", "input")],
        right=[("1", "VOUTA", "output"), ("2", "VOUTB", "output"), None, ("10", "VREFIN/VREFOUT", "passive"), None],
        top=[("9", "AVDD", "power_in")], bottom=[("3", "GND", "power_in")],
        fields=f("C1554729", "Extended", "DAC8563SDGSR", "Texas Instruments", DS["DAC8563"]), width=17.78))
    OP8 = {"OUTA": "1", "-INA": "2", "+INA": "3", "V-": "4", "+INB": "5", "-INB": "6", "OUTB": "7", "V+": "8"}
    add(dual_opamp("OPA2192IDR", "OPA2192IDR", FP + "SOIC-8_L4.9-W3.9-P1.27-LS6.0-BL", "Dual precision op-amp, 36 V, RRIO, SOIC-8",
                   f("C110074", "Extended", "OPA2192IDR", "Texas Instruments", DS["OPA2192"]), OP8))
    add(dual_opamp("OPA2156IDR", "OPA2156IDR", FP + "SOIC-8_L4.9-W3.9-P1.27-LS6.0-BL", "Dual low-noise op-amp (TIA option, DNP), SOIC-8",
                   f("C1850241", "Extended", "OPA2156IDR", "Texas Instruments", DS["OPA2156"]), OP8))
    add(dual_opamp("TL072CDT", "TL072CDT", FP + "SOIC-8_L5.0-W4.0-P1.27-LS6.0-BL", "Dual JFET op-amp (anti-alias option, DNP), SO-8",
                   f("C6961", "Basic", "TL072CDT", "STMicroelectronics", DS["TL072"]), OP8))
    add(box_symbol("INA826AIDR", "U", "INA826AIDR", FP + "SOIC-8_L4.9-W3.9-P1.27-LS6.0-BL", "Instrumentation amplifier (option, DNP), SOIC-8",
        left=[("4", "IN+", "input"), ("1", "IN-", "input"), None, ("2", "RG", "passive"), ("3", "RG", "passive")],
        right=[("7", "OUT", "output"), None, None, ("6", "REF", "input"), None],
        top=[("8", "VS+", "power_in")], bottom=[("5", "VS-", "power_in")],
        fields=f("C38433", "Extended", "INA826AIDR", "Texas Instruments", DS["INA826"]), width=12.7))
    add(box_symbol("PGA113AIDGSR", "U", "PGA113AIDGSR", FP + "VSSOP-10_L3.0-W3.0-P0.50-LS4.9-BL", "Programmable-gain amplifier, 2-ch mux, SPI (option, DNP), VSSOP-10",
        left=[("3", "VCAL/CH0", "input"), ("2", "CH1", "input"), ("4", "VREF", "input"), None, ("9", "~{CS}", "input"), ("7", "SCLK", "input"), ("8", "DIO", "bidirectional")],
        right=[("5", "VOUT", "output")] + [None] * 6,
        top=[("1", "AVDD", "power_in"), ("10", "DVDD", "power_in")], bottom=[("6", "GND", "power_in")],
        fields=f("C2057394", "Extended", "PGA113AIDGSR", "Texas Instruments", DS["PGA113"]), width=15.24))
    add(box_symbol("6N137S-TA1-L", "U", "6N137S-TA1-L", FP + "SOP-8_L9.8-W6.6-P2.54-LS10.3-BL", "High-speed optocoupler 10 MBd, open-collector output, 3.3/5 V, SOP-8",
        left=[("2", "ANODE", "passive"), ("3", "CATHODE", "passive"), None, ("1", "NC", "no_connect"), ("4", "NC", "no_connect")],
        right=[("6", "VO", "open_collector"), ("7", "VE", "input"), None, None, None],
        top=[("8", "VCC", "power_in")], bottom=[("5", "GND", "power_in")],
        fields=f("C92651", "Extended", "6N137S-TA1-L", "Lite-On", DS["6N137"]), width=15.24))
    add(box_symbol("SN74AHCT541PWR", "U", "SN74AHCT541PWR", FP + "TSSOP-20_L6.5-W4.4-P0.65-LS6.4-BL", "Octal buffer, 5 V TTL-compatible inputs, TSSOP-20",
        left=[("2", "A1", "input"), ("3", "A2", "input"), ("4", "A3", "input"), ("5", "A4", "input"), ("6", "A5", "input"), ("7", "A6", "input"),
              ("8", "A7", "input"), ("9", "A8", "input"), None, ("1", "~{OE1}", "input"), ("19", "~{OE2}", "input")],
        right=[("18", "Y1", "output"), ("17", "Y2", "output"), ("16", "Y3", "output"), ("15", "Y4", "output"), ("14", "Y5", "output"),
               ("13", "Y6", "output"), ("12", "Y7", "output"), ("11", "Y8", "output"), None, None, None],
        top=[("20", "VCC", "power_in")], bottom=[("10", "GND", "power_in")],
        fields=f("C50989", "Extended", "SN74AHCT541PWR", "Texas Instruments", DS["AHCT541"]), width=12.7))
    add(box_symbol("74HCT125PW", "U", "74HCT125PW", FP + "TSSOP-14_L5.0-W4.4-P0.65-LS6.4-BL", "Quad 3-state buffer, TTL-compatible inputs, TSSOP-14",
        left=[("2", "1A", "input"), ("1", "~{1OE}", "input"), ("5", "2A", "input"), ("4", "~{2OE}", "input"),
              ("9", "3A", "input"), ("10", "~{3OE}", "input"), ("12", "4A", "input"), ("13", "~{4OE}", "input")],
        right=[("3", "1Y", "tri_state"), None, ("6", "2Y", "tri_state"), None, ("8", "3Y", "tri_state"), None, ("11", "4Y", "tri_state"), None],
        top=[("14", "VCC", "power_in")], bottom=[("7", "GND", "power_in")],
        fields=f("C131316", "Extended", "74HCT125PW,118", "Nexperia", DS["HCT125"]), width=12.7))
    add(box_symbol("SN74LVC1T45DBVR", "U", "SN74LVC1T45DBVR", FP + "SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BR", "1-bit bidirectional level translator, SOT-23-6",
        left=[("3", "A", "bidirectional"), None, ("5", "DIR", "input")], right=[("4", "B", "bidirectional"), None, None],
        top=[("1", "VCCA", "power_in"), ("6", "VCCB", "power_in")], bottom=[("2", "GND", "power_in")],
        fields=f("C7843", "Extended", "SN74LVC1T45DBVR", "Texas Instruments", DS["LVC1T45"]), width=12.7))
    add(box_symbol("SN74LVC1G17DBVR", "U", "SN74LVC1G17DBVR", FP + "SOT-23-5_L3.0-W1.7-P0.95-LS2.8-BR", "Single Schmitt-trigger buffer (TCXO option, DNP), SOT-23-5",
        left=[("2", "A", "input"), None, ("1", "NC", "no_connect")], right=[("4", "Y", "output"), None, None],
        top=[("5", "VCC", "power_in")], bottom=[("3", "GND", "power_in")],
        fields=f("C7836", "Extended", "SN74LVC1G17DBVR", "Texas Instruments", DS["LVC1G17"]), width=10.16))
    add(box_symbol("LM66100DCKR", "U", "LM66100DCKR", FP + "SC-70-6_L2.0-W1.3-P0.65-LS2.1-BL", "Ideal-diode controller with integrated FET, 1.5 A, 5.5 V, SC-70-6",
        left=[("1", "VIN", "power_in"), None, ("3", "~{CE}", "input")], right=[("6", "VOUT", "passive"), None, ("5", "~{ST}", "passive")],
        top=[("4", "NC", "no_connect")], bottom=[("2", "GND", "power_in")],
        fields=f("C2869734", "Extended", "LM66100DCKR", "Texas Instruments", DS["LM66100"]), width=12.7))
    add(box_symbol("AMS1117-3.3", "U", "AMS1117-3.3", FP + "SOT-223-3_L6.5-W3.4-P2.30-LS7.0-BR", "3.3 V 1 A LDO, SOT-223 (pins 2 and 4 = VOUT/tab)",
        left=[("3", "VIN", "power_in")], right=[("2", "VOUT", "power_out")], top=[("4", "VOUT", "power_out")], bottom=[("1", "GND", "power_in")],
        fields=f("C6186", "Basic", "AMS1117-3.3", "Advanced Monolithic Systems", DS["AMS1117"]), width=10.16))
    add(box_symbol("78L05G-AB3-R", "U", "78L05G-AB3-R", FP + "SOT-89-3_L4.5-W2.5-P1.50-LS4.2-BR", "5 V 100 mA linear regulator, SOT-89 (1=OUT 2=GND/tab 3=IN)",
        left=[("3", "IN", "power_in")], right=[("1", "OUT", "power_out")], bottom=[("2", "GND", "power_in")],
        fields=f("C71136", "Basic", "78L05G-AB3-R", "UTC", DS["78L05G"]), width=10.16))
    add(box_symbol("B0512S-2WR3", "PS", "B0512S-2WR3", FP + "PWRM-TH_IBXX05S-2WR3", "Isolated DC-DC 5 V -> 12 V 2 W, unregulated, 1.5 kVDC, SIP-4 (1=+Vin 2=-Vin 4=-Vo 6=+Vo)",
        left=[("1", "+VIN", "power_in"), ("2", "-VIN", "power_in")], right=[("6", "+VO", "passive"), ("4", "-VO", "passive")],
        fields=f("C5369475", "Extended", "B0512S-2WR3", "YLPTEC", DS["B0512S"]), width=15.24))
    add(box_symbol("1XTV10000MDA", "X", "10 MHz TCXO", FP + "OSC-SMD_4P-L3.2-W2.5-BL", "VC-TCXO 10 MHz +-1.5 ppm, 3.3 V, clipped sine (option, DNP), 3.2x2.5 mm",
        left=[("1", "VCONT", "input")], right=[("3", "OUT", "output")], top=[("4", "VCC", "power_in")], bottom=[("2", "GND", "power_in")],
        fields=f("C253701", "Extended", "1XTV10000MDA", "KDS Daishinku", DS["TCXO"]), width=12.7))
    # ---- v0.7 / NMR re-spec ICs (2026-09-13) --------------------------------------------
    add(box_symbol("AD9834BRUZ", "U", "AD9834BRUZ", FP + "TSSOP-20_L6.5-W4.4-P0.65-LS6.4-BL",
        "10-bit 75 MHz DDS waveform generator, SPI, sine/triangle/square out, TSSOP-20",
        left=[("13", "SDATA", "input"), ("14", "SCLK", "input"), ("15", "~{FSYNC}", "input"), ("8", "MCLK", "input"), None,
              ("11", "RESET", "input"), ("12", "SLEEP", "input"), ("9", "FSELECT", "input"), ("10", "PSELECT", "input"), None,
              ("1", "FS_ADJUST", "passive"), ("2", "REFOUT", "output"), ("3", "COMP", "passive"), ("6", "CAP/2.5V", "passive"),
              ("17", "VIN", "input")],
        right=[("19", "IOUT", "output"), ("20", "IOUTB", "output"), ("16", "SIGNBITOUT", "output")] + [None] * 12,
        top=[("4", "AVDD", "power_in"), ("5", "DVDD", "power_in")],
        bottom=[("18", "AGND", "power_in"), ("7", "DGND", "power_in")],
        fields=f("C116589", "Extended", "AD9834BRUZ", "Analog Devices", DS["AD9834"]), width=25.4))
    add(box_symbol("SI5351A-B-GT", "U", "SI5351A-B-GT", FP + "MSOP-10_L3.0-W3.0-P0.50-LS5.0-BL",
        "I2C clock generator, 3 outputs, 2.5 kHz - 200 MHz, 25 MHz crystal, MSOP-10",
        left=[("4", "SCL", "input"), ("5", "SDA", "bidirectional"), None, ("2", "XA", "input"), ("3", "XB", "input")],
        right=[("10", "CLK0", "output"), ("9", "CLK1", "output"), ("6", "CLK2", "output"), None, None],
        top=[("1", "VDD", "power_in"), ("7", "VDDO", "power_in")], bottom=[("8", "GND", "power_in")],
        fields=f("C504891", "Extended", "SI5351A-B-GT", "Skyworks", DS["SI5351"]), width=12.7))
    add(crystal4("X322525MOB4SI", "25 MHz", FP + "CRYSTAL-SMD_4P-L3.2-W2.5-BL",
        "Crystal 25 MHz +-10 ppm, 8 pF load, SMD 3225 4-pad (1/3 = terminals, 2/4 = case ground)",
        f("C9006", "Basic", "X322525MOB4SI", "YXC", DS["X322525"])))
    add(box_symbol("OPA564AIDWPR", "U", "OPA564AIDWPR", FP + "HSOP-20_L12.9-W7.5-P1.27-BL-EP-A",
        "Power op-amp 1.5 A, 24 V, 17 MHz, adjustable current limit, HSOP-20 PowerPAD down (pad 21 = V-)",
        left=[("5", "+IN", "input"), ("6", "-IN", "input"), None, ("4", "E/~{S}", "input"), ("9", "ISET", "passive"), ("12", "TSENSE", "passive")],
        right=[("15", "VOUT", "output"), ("16", "VOUT", "passive"), None, ("3", "TFLAG", "output"), ("8", "IFLAG", "output"), None],
        top=[("2", "V+", "power_in"), ("17", "V+PWR", "power_in"), ("18", "V+PWR", "power_in"), ("19", "V+PWR", "power_in"), ("7", "VDIG", "power_in")],
        bottom=[("1", "V-", "power_in"), ("10", "V-", "power_in"), ("11", "V-", "power_in"), ("20", "V-", "power_in"),
                ("13", "V-PWR", "power_in"), ("14", "V-PWR", "power_in"), ("21", "EP", "power_in")],
        fields=f("C188648", "Extended", "OPA564AIDWPR", "Texas Instruments", DS["OPA564"]), width=20.32))
    add(dual_opamp("OPA1612AIDR", "OPA1612AIDR", FP + "SOIC-8_L5.0-W4.0-P1.27-LS6.0-BL",
                   "Dual ultra-low-noise op-amp 1.1 nV/rtHz, 36 V, 40 MHz, SOIC-8",
                   f("C94590", "Extended", "OPA1612AIDR", "Texas Instruments", DS["OPA1612"]), OP8))
    add(box_symbol("DG419DY-T1-E3", "U", "DG419DY-T1-E3", FP + "SOIC-8_L4.9-W3.9-P1.27-LS6.0-BL",
        "SPDT analog switch, 44 V, 25 ohm, SOIC-8.  PIN 5 IS VL (logic supply) - tie it to the logic rail; "
        "it is NOT the no-connect that pin 5 of the ADG1419 is (v0.7 lib report 8.1)",
        left=[("2", "S1", "passive"), ("8", "S2", "passive"), None, ("6", "IN", "input")],
        right=[("1", "D", "passive"), None, None, None],
        top=[("4", "V+", "power_in"), ("5", "VL", "power_in")],
        bottom=[("3", "GND", "power_in"), ("7", "V-", "power_in")],
        fields=f("C6581", "Extended", "DG419DY-T1-E3", "Vishay Siliconix", DS["DG419"]), width=12.7))
    add(box_symbol("DG413DY-T1-E3", "U", "DG413DY-T1-E3", FP + "SOIC-16_L9.9-W3.9-P1.27-LS6.0-BL",
        "Quad SPST analog switch (2 NO + 2 NC), 44 V, 25 ohm, SOIC-16 (pin 12 = VL logic supply)",
        left=[("1", "IN1", "input"), ("16", "IN2", "input"), ("9", "IN3", "input"), ("8", "IN4", "input"), None,
              ("3", "S1", "passive"), ("14", "S2", "passive"), ("11", "S3", "passive"), ("6", "S4", "passive")],
        right=[("2", "D1", "passive"), ("15", "D2", "passive"), ("10", "D3", "passive"), ("7", "D4", "passive")] + [None] * 5,
        top=[("13", "V+", "power_in"), ("12", "VL", "power_in")],
        bottom=[("5", "GND", "power_in"), ("4", "V-", "power_in")],
        fields=f("C141600", "Extended", "DG413DY-T1-E3", "Vishay Siliconix", DS["DG413"]), width=12.7))
    add(box_symbol("TS5A23157DGSR", "U", "TS5A23157DGSR", FP + "MSOP-10_L3.0-W3.0-P0.50-LS5.0-BL",
        "Dual SPDT analog switch, 1.65-5.5 V, 5 ohm, VSSOP-10",
        left=[("1", "IN1", "input"), ("5", "IN2", "input"), None, ("10", "COM1", "bidirectional"), ("6", "COM2", "bidirectional")],
        right=[("9", "NC1", "bidirectional"), ("2", "NO1", "bidirectional"), ("7", "NC2", "bidirectional"), ("4", "NO2", "bidirectional"), None],
        top=[("8", "V+", "power_in")], bottom=[("3", "GND", "power_in")],
        fields=f("C11133", "Extended", "TS5A23157DGSR", "Texas Instruments", DS["TS5A23157"]), width=12.7))
    add(box_symbol("DRV8871DDAR", "U", "DRV8871DDAR", FP + "SO-8_L4.9-W3.9-P1.27-LS6.0-BL-EP",
        "Brushed-DC H-bridge driver 6.5-45 V, 3.6 A peak, adjustable current limit, SO-8 PowerPAD (pad 9 = thermal/GND)",
        left=[("3", "IN1", "input"), ("2", "IN2", "input"), None, ("4", "ILIM", "passive")],
        right=[("6", "OUT1", "output"), ("8", "OUT2", "output"), None, None],
        top=[("5", "VM", "power_in")],
        bottom=[("1", "GND", "power_in"), ("7", "PGND", "power_in"), ("9", "EP", "power_in")],
        fields=f("C75864", "Extended", "DRV8871DDAR", "Texas Instruments", DS["DRV8871"]), width=12.7))
    add(box_symbol("UCC27517DBVR", "U", "UCC27517DBVR", FP + "SOT-23-5_L3.0-W1.7-P0.95-LS2.8-BR",
        "Single 4 A gate driver, non-inverting, 4.5-18 V, SOT-23-5 (UMW second source)",
        left=[("3", "IN+", "input"), ("4", "IN-", "input")], right=[("5", "OUT", "output"), None],
        top=[("1", "VDD", "power_in")], bottom=[("2", "GND", "power_in")],
        fields=f("C20623191", "Extended", "UCC27517DBVR", "UMW", DS["UCC27517"]), width=10.16))
    add(box_symbol("TCA9535PWR", "U", "TCA9535PWR", FP + "TSSOP-24_L7.8-W4.4-P0.65-LS6.4-BL",
        "16-bit I2C GPIO expander, 3 address pins, interrupt output, TSSOP-24 (pin-compatible with PCA9555PW)",
        left=[("22", "SCL", "input"), ("23", "SDA", "bidirectional"), ("1", "~{INT}", "open_collector"), None,
              ("21", "A0", "input"), ("2", "A1", "input"), ("3", "A2", "input")] + [None] * 10,
        right=[("4", "P00", "bidirectional"), ("5", "P01", "bidirectional"), ("6", "P02", "bidirectional"), ("7", "P03", "bidirectional"),
               ("8", "P04", "bidirectional"), ("9", "P05", "bidirectional"), ("10", "P06", "bidirectional"), ("11", "P07", "bidirectional"), None,
               ("13", "P10", "bidirectional"), ("14", "P11", "bidirectional"), ("15", "P12", "bidirectional"), ("16", "P13", "bidirectional"),
               ("17", "P14", "bidirectional"), ("18", "P15", "bidirectional"), ("19", "P16", "bidirectional"), ("20", "P17", "bidirectional")],
        top=[("24", "VCC", "power_in")], bottom=[("12", "GND", "power_in")],
        fields=f("C22396388", "Extended", "TCA9535PWR", "UMW", DS["TCA9535"]), width=12.7))
    add(box_symbol("2T025000VX", "X", "25 MHz XO", FP + "OSC-SMD_4P-L2.5-W2.0-BL_X1G0054210307",
        "Oscillator 25 MHz, 3.3 V, 2.5x2.0 mm 4-pad (option, DNP: replaces the crystal on the Si5351 input)",
        left=[("1", "NC/GND", "passive")], right=[("3", "OUT", "output")],
        top=[("4", "VDD", "power_in")], bottom=[("2", "GND", "power_in")],
        fields=f("C47018484", "Extended", "2T025000VX", "Huaxin", DS["TCXO25"]), width=12.7))
    add(box_symbol("74HC74D", "U", "74HC74D", FP + "SOIC-14_L8.7-W3.9-P1.27-LS6.0-BL",
        "Dual D flip-flop with set and reset, positive edge triggered, SOIC-14 "
        "(quadrature LO: wired as a 2-bit Johnson counter, circuits note 1.4).  "
        "Pin names follow the TI convention; Nexperia calls PRE = SD, CLR = RD, CLK = CP",
        left=[("2", "1D", "input"), ("3", "1CLK", "input"), ("4", "~{1PRE}", "input"), ("1", "~{1CLR}", "input"), None,
              ("12", "2D", "input"), ("11", "2CLK", "input"), ("10", "~{2PRE}", "input"), ("13", "~{2CLR}", "input")],
        right=[("5", "1Q", "output"), ("6", "~{1Q}", "output"), None, None, None,
               ("9", "2Q", "output"), ("8", "~{2Q}", "output"), None, None],
        top=[("14", "VCC", "power_in")], bottom=[("7", "GND", "power_in")],
        fields=f("C27597", "Extended", "74HC74D,653", "Nexperia", DS["HC74"]), width=12.7))
    add(dual_opamp("OPA1656IDR", "OPA1656IDR", FP + "SOIC-8_L5.0-W4.0-P1.27-LS6.0-BL",
                   "Dual FET-input low-noise op-amp, 2.9 nV/rtHz and 6 fA/rtHz, 53 MHz, 36 V, SOIC-8 "
                   "(LNA first stage: current noise, not voltage noise, decides on a 14 kOhm tank)",
                   f("C1849431", "Extended", "OPA1656IDR", "Texas Instruments", DS["OPA1656"]), OP8))
    add(box_symbol("HK4100F-DC5V-SHG", "K", "HK4100F-DC5V-SHG", FP + "RELAY-TH_HK4100F-DC5V-SHG", "Relay SPDT 5 V coil 125 ohm, 3 A 30 VDC contacts (1=NO 2=NC 3/4=coil 5/6=COM)",
        left=[("3", "COIL+", "passive"), ("4", "COIL-", "passive")], right=[("1", "NO", "passive"), ("5", "COM", "passive"), ("2", "NC", "passive"), ("6", "COM", "passive")],
        fields=f("C12072", "Extended", "HK4100F-DC5V-SHG", "Ningbo Huike", DS["HK4100F"]), width=12.7))
    # v0.8 (D-51, 2026-09-16): the four switching channels must survive a student plugging a wall socket
    # into them, so the relay is a 10 A "sugar cube" on the KiCad standard Hongfa land.  Pin NUMBERS are the
    # footprint pad names, which use the IEC/EN 50005 relay numbering: A1/A2 = coil (A1 is the + terminal by
    # convention; the coil has no internal diode, so the polarity is only a drawing convention), 11 = common,
    # 12 = normally-closed (break), 14 = normally-open (make).  The Songle SRD-05VDC-SL-C fits the same land.
    add(box_symbol("JQC-3FF-005-1ZS", "K", "JQC-3FF/005-1ZS", "Relay_THT:Relay_SPDT_Hongfa_JQC-3FF_0XX-1Z",
        "Relay SPDT 5 V coil 70 ohm, 10 A 277 V AC / 28 V DC contacts, pins per footprint",
        left=[("A1", "COIL+", "passive"), ("A2", "COIL-", "passive")],
        right=[("14", "NO", "passive"), ("11", "COM", "passive"), ("12", "NC", "passive")],
        fields=f("C9221", "Extended", "JQC-3FF/005-1ZS(551)", "Hongfa", DS["JQC3FF"]), width=12.7))

    # ---- connectors --------------------------------------------------------------------
    add(box_symbol("USB-C-16P-2MD-073", "J", "USB-C 16P", FP + "USB-C-SMD_TYPE-C-16PIN-2MD-073", "USB Type-C receptacle 16-pin, power + USB 2.0",
        right=[("A4B9", "VBUS", "passive"), ("B4A9", "VBUS", "passive"), None,
               ("A6", "D+", "bidirectional"), ("B6", "D+", "bidirectional"), ("A7", "D-", "bidirectional"), ("B7", "D-", "bidirectional"), None,
               ("A8", "SBU1", "no_connect"), ("B8", "SBU2", "no_connect"), None, ("A5", "CC1", "bidirectional"), ("B5", "CC2", "bidirectional"), None,
               ("13", "SHIELD", "passive"), ("14", "SHIELD", "passive"), ("A1B12", "GND", "power_in"), ("B1A12", "GND", "power_in")],
        fields=f("C2765186", "Extended", "TYPE-C 16PIN 2MD(073)", "SHOU HAN", DS["USBC"]), width=12.7))
    add(box_symbol("DC005-T20", "J", "DC005-T20", FP + "DC-IN-TH_DC005-T20", "DC barrel jack 5.5/2.1 mm, 3 A (pad 1 = centre pin, 2 = sleeve, 3 = switch)",
        right=[("1", "TIP", "passive"), ("2", "SLEEVE", "passive"), ("3", "SWITCH", "passive")],
        fields=f("C111567", "Extended", "DC005-T20", "SOFNG", DS["DC005"]), width=12.7))
    add(box_symbol("BWSMA-KE-Z001", "J", "SMA", FP + "SMA-TH_BWSMA-KE-Z001", "SMA female vertical PCB connector, 50 ohm (5 = centre, 1-4 = shield legs)",
        right=[("5", "SIG", "passive"), ("1", "GND", "passive"), ("2", "GND", "passive"), ("3", "GND", "passive"), ("4", "GND", "passive")],
        fields=f("C496549", "Extended", "BWSMA-KE-Z001", "BAT Wireless", DS["SMA"]), width=10.16))
    add(box_symbol("KF301-5.0-2P", "J", "KF301-5.0-2P", FP + "CONN-TH_P5.00_KF301-5.0-2P", "Screw terminal 5.0 mm 2P, 300 V 16 A",
        right=[("1", "1", "passive"), ("2", "2", "passive")], fields=f("C474881", "Extended", "KF301-5.0-2P", "Cixi Kefa", DS["KF301-2"]), width=10.16))
    add(box_symbol("KF301-5.0-3P", "J", "KF301-5.0-3P", FP + "CONN-TH_3P-P5.00_KF301-5.0-3P", "Screw terminal 5.0 mm 3P, 300 V 16 A",
        right=[("1", "1", "passive"), ("2", "2", "passive"), ("3", "3", "passive")], fields=f("C474882", "Extended", "KF301-5.0-3P", "Cixi Kefa", DS["KF301-3"]), width=10.16))
    # dev board sockets: pin names = ESP32-S3-DevKitC-1 v1.1 header order (Espressif user guide)
    J1 = ["3V3", "3V3", "RST", "IO4", "IO5", "IO6", "IO7", "IO15", "IO16", "IO17", "IO18", "IO8", "IO3", "IO46", "IO9", "IO10", "IO11", "IO12", "IO13", "IO14", "5V", "GND"]
    J3 = ["GND", "IO43/TX", "IO44/RX", "IO1", "IO2", "IO42", "IO41", "IO40", "IO39", "IO38", "IO37", "IO36", "IO35", "IO0", "IO45", "IO48", "IO47", "IO21", "IO20", "IO19", "GND", "GND"]

    def ptype(n):
        if n == "3V3":
            return "power_out"
        if n in ("5V", "GND"):
            return "power_in"
        return "bidirectional"
    add(box_symbol("DEVKIT_SOCKET_J1", "J", "DevKitC-1 J1 socket 1x22", FP + "HDR-TH_22P-P2.54-V-F", "1x22 female socket, dev-board header J1 (Megastar ZX-PM2.54-1-22PY)",
        left=[(str(i + 1), n, ptype(n)) for i, n in enumerate(J1)], fields=f("C7499337", "Extended", "ZX-PM2.54-1-22PY", "Megastar", DS["SOCK22"]), width=12.7))
    add(box_symbol("DEVKIT_SOCKET_J3", "J", "DevKitC-1 J3 socket 1x22", FP + "HDR-TH_22P-P2.54-V-F", "1x22 female socket, dev-board header J3 (Megastar ZX-PM2.54-1-22PY)",
        right=[(str(i + 1), n, ptype(n)) for i, n in enumerate(J3)], fields=f("C7499337", "Extended", "ZX-PM2.54-1-22PY", "Megastar", DS["SOCK22"]), width=12.7))
    add(box_symbol("HDR_2x20_RA_MALE", "J", "Panel link 2x20 R/A", FP + "HDR-TH_40P-P2.54-H-R2-C20-S2.54-W10.0", "2x20 right-angle male header (Ckmtw B-2100R40P-B110), front-panel link",
        left=[(str(i), str(i), "passive") for i in range(1, 41, 2)], right=[(str(i), str(i), "passive") for i in range(2, 41, 2)],
        fields=f("C124369", "Extended", "B-2100R40P-B110", "Ckmtw", DS["HDR2x20RA"]), width=7.62))
    # Panel link, main-board side: three of these sit on the BOTTOM of the main board (v0.8).
    # Hand-soldered by the instructor from a separately bought bag, so in_bom=False (out of the
    # JLC BOM and CPL) and Assembly = "hand" (release.py lists them for the instructor instead).
    add(box_symbol("HDR_2x20_MALE", "J", "Panel link 2x20 male", "Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical",
        "2x20 straight male pin header, 2.54 mm, KiCad standard footprint. Bottom side of the main board, hand-soldered from the top; mates the panel's female headers.",
        left=[(str(i), str(i), "passive") for i in range(1, 41, 2)], right=[(str(i), str(i), "passive") for i in range(2, 41, 2)],
        fields={"Assembly": "hand", "MPN": "2x20 straight pin header 2.54 mm", "Manufacturer": "any", "Purchase": "C5224014",
                "Datasheet": "https://www.lcsc.com/product-detail/C5224014.html"}, width=7.62, in_bom=False))
    # Panel link, panel side: three of these on the panel's inner face, also hand-soldered.
    add(box_symbol("HDR_2x20_FEMALE", "J", "Panel link 2x20 female", "Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical",
        "2x20 straight female header 8.5 mm, 2.54 mm, KiCad standard footprint. Panel inner face, hand-soldered; mates the main board's male headers.",
        left=[(str(i), str(i), "passive") for i in range(1, 41, 2)], right=[(str(i), str(i), "passive") for i in range(2, 41, 2)],
        fields={"Assembly": "hand", "MPN": "2x20 female header 8.5 mm", "Manufacturer": "any", "Purchase": "C5124634",
                "Datasheet": "https://www.lcsc.com/product-detail/C5124634.html"}, width=7.62, in_bom=False))
    add(box_symbol("HDR_2x10_MALE", "J", "Expansion 2x10", FP + "HDR-TH_20P-P2.54-V-M-R2-C10-S2.54", "2x10 straight male header (XFCN PZ254V-12-20P), expansion",
        left=[(str(i), str(i), "passive") for i in range(1, 21, 2)], right=[(str(i), str(i), "passive") for i in range(2, 21, 2)],
        fields=f("C492427", "Extended", "PZ254V-12-20P", "XFCN", DS["HDR2x10"]), width=7.62))
    # Panel screw terminals (v0.8): the TTL strip and the TX coil pair move to the panel.
    add(box_symbol("KF128-2.54-10P", "J", "KF128-2.54-10P", FP + "CONN-TH_10P-P2.54_KF128-2.54-10P",
        "Screw terminal 2.54 mm 10P, wire entry from the top (vertical), 130 V 8 A",
        right=[(str(i), str(i), "passive") for i in range(1, 11)],
        fields=f("C474928", "Extended", "KF128-2.54-10P", "Cixi Kefa", DS["KF128-10P"]), width=10.16))
    add(box_symbol("KF128-5.0-2P", "J", "KF128-5.0-2P", FP + "CONN-TH_P5.00_KF128-5.0-2P",
        "Screw terminal 5.0 mm 2P, wire entry from the top (vertical), 250 V 24 A",
        right=[("1", "1", "passive"), ("2", "2", "passive")],
        fields=f("C474950", "Extended", "KF128-5.0-2P", "Cixi Kefa", DS["KF128-2P"]), width=10.16))
    # Vertical (top-entry) Qwiic for the panel; the horizontal one below stays on the main board.
    add(box_symbol("QWIIC_BM04B-SRSS", "J", "Qwiic (vertical)", FP + "CONN-SMD_BM04B-SRSS-TB",
        "JST-SH 1.0 mm 4-pin vertical / top entry (Qwiic: 1=GND 2=3V3 3=SDA 4=SCL; 5,6 = shell)",
        right=[("1", "GND", "power_in"), ("2", "3V3", "power_in"), ("3", "SDA", "bidirectional"), ("4", "SCL", "bidirectional"), ("5", "SHELL", "passive"), ("6", "SHELL", "passive")],
        fields=f("C51940129", "Extended", "XY-BM04B-SRSS-TB", "XYECONN", DS["QWIIC_V"]), width=10.16))
    add(box_symbol("QWIIC_SM04B-SRSS", "J", "Qwiic", FP + "CONN-SMD_4P-P1.00_XY-SM04B-SRSS-TB", "JST-SH 1.0 mm 4-pin horizontal (Qwiic: 1=GND 2=3V3 3=SDA 4=SCL; 5,6 = shell)",
        right=[("1", "GND", "power_in"), ("2", "3V3", "power_in"), ("3", "SDA", "bidirectional"), ("4", "SCL", "bidirectional"), ("5", "SHELL", "passive"), ("6", "SHELL", "passive")],
        fields=f("C51940130", "Extended", "XY-SM04B-SRSS-TB", "XYECONN", DS["QWIIC"]), width=10.16))
    add(box_symbol("HDR_1x4_FEMALE", "J", "OLED 0.96in module on 1x4 socket 8.5 mm", "class_board:OLED-0.96in-4P-module-socket", "0.96in I2C OLED module (GND VCC SCL SDA) on a vertical 8.5 mm 1x4 female header (C2894927); the footprint carries the module outline and its four M2 holes",
        right=[("1", "GND", "power_in"), ("2", "VCC", "power_in"), ("3", "SCL", "bidirectional"), ("4", "SDA", "bidirectional")],
        fields=f("C2894927", "Extended", "PZ254-1-04-Z-8.5", "XFCN", "https://www.lcsc.com/product-detail/C2894927.html"), width=10.16))

    # ---- mechanical / no-part symbols ---------------------------------------------------
    nt = Symbol("NetTie_2", "NT", "AGND-GND star", FP + "NetTie-2_SMD_Pad2.0mm", "Net tie: single AGND-GND star point (copper only)",
                in_bom=False, hide_pin_numbers=True, hide_pin_names=True, pin_name_offset=0)
    nt.graphics[0].append(poly([(-1.27, 0), (1.27, 0)], 0.254))
    nt.pin(1, "1", "passive", -2.54, 0, 0, 2.54)
    nt.pin(2, "2", "passive", 2.54, 0, 180, 2.54)
    nt.ref_pos, nt.value_pos, nt.bbox = (0, 1.27), (0, -1.27), (-2.54, -1.27, 2.54, 1.27)
    add(nt)
    for nm, fp, desc, bridged in (("SolderJumper_3_Bridged12", "SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm", "3-pad solder jumper, 1-2 bridged by default", True),
                                  ("SolderJumper_3_Open", "SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm", "3-pad solder jumper, open", False)):
        jp = Symbol(nm, "JP", nm, FP + fp, desc, in_bom=False, hide_pin_names=True, pin_name_offset=0)
        g = jp.graphics[0]
        g.append(poly([(-2.54, 0), (-2.032, 0)], 0))
        g.append(poly([(2.54, 0), (2.032, 0)], 0))
        g.append(poly([(0, -1.27), (0, -1.016)], 0))
        g.append(rect(-0.508, 1.016, 0.508, -1.016, "outline", 0))
        g.append(circle(-1.27, 0, 1.016, 0))
        g.append(circle(1.27, 0, 1.016, 0))
        if bridged:
            g.append(rect(-1.27, 0.508, 0, -0.508, "outline", 0))
        jp.pin(1, "A", "passive", -5.08, 0, 0, 2.54)
        jp.pin(2, "C", "passive", 0, -3.81, 90, 2.54)
        jp.pin(3, "B", "passive", 5.08, 0, 180, 2.54)
        jp.ref_pos, jp.value_pos, jp.bbox = (-2.54, -2.54), (0, 2.794), (-5.08, -3.81, 5.08, 1.27)
        add(jp)
    for nm, fp, desc, bridged in (("SolderJumper_2_Bridged", "SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm", "2-pad solder jumper, bridged by default", True),
                                  ("SolderJumper_2_Open", "SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", "2-pad solder jumper, open", False)):
        jp = Symbol(nm, "JP", nm, FP + fp, desc, in_bom=False, hide_pin_names=True, pin_name_offset=0)
        g = jp.graphics[0]
        g.append(circle(-0.762, 0, 0.762, 0))
        g.append(circle(0.762, 0, 0.762, 0))
        if bridged:
            g.append(rect(-0.762, 0.508, 0.762, -0.508, "outline", 0))
        jp.pin(1, "A", "passive", -3.81, 0, 0, 2.286)
        jp.pin(2, "B", "passive", 3.81, 0, 180, 2.286)
        jp.ref_pos, jp.value_pos, jp.bbox = (0, 2.032), (0, -2.032), (-3.81, -1.27, 3.81, 1.27)
        add(jp)
    tp = Symbol("TestPoint", "TP", "TP", FP + "TestPoint_Pad_D1.5mm", "Test point pad 1.5 mm", in_bom=False, hide_pin_numbers=True, hide_pin_names=True, pin_name_offset=0)
    tp.graphics[0].append(circle(0, 3.302, 0.762, 0))
    tp.pin(1, "1", "passive", 0, 0, 90, 2.54)
    tp.ref_pos, tp.value_pos, tp.bbox = (0, 5.588), (2.54, 3.302), (-1.27, 0, 1.27, 4.064)
    add(tp)
    mh = Symbol("MountingHole", "H", "M3", FP + "MountingHole_3.2mm_M3", "Mounting hole 3.2 mm for M3", in_bom=False)
    mh.graphics[0].append(circle(0, 0, 1.27, 1.27))
    mh.ref_pos, mh.value_pos, mh.bbox = (0, 2.54), (0, -2.54), (-1.27, -1.27, 1.27, 1.27)
    add(mh)
    fid = Symbol("Fiducial", "FID", "Fiducial", FP + "Fiducial_1mm_Mask2mm", "Fiducial mark 1 mm, 2 mm mask", in_bom=False)
    fid.graphics[0].append(circle(0, 0, 0.635, 0, "outline"))
    fid.graphics[0].append(circle(0, 0, 1.27, 0.254))
    fid.ref_pos, fid.value_pos, fid.bbox = (0, 2.54), (0, -2.54), (-1.27, -1.27, 1.27, 1.27)
    add(fid)
    for net, style in (("GND", "gnd"), ("AGND", "agnd"), ("+5V_RAW", "bar"), ("+3V3", "bar"), ("+12V", "bar"), ("-12V", "neg"), ("+5VA", "bar"), ("VREF_DAC", "bar"),
                      ("+3V3A", "bar"), ("+VEXT", "bar"), ("+VCOIL", "bar"), ("V_MID", "bar")):
        add(power_symbol(net, style))
    pf = Symbol("PWR_FLAG", "#FLG", "PWR_FLAG", "", "Power flag: marks a net as driven (grounds without a power_out pin)",
                power=True, in_bom=False, hide_pin_numbers=True, hide_pin_names=True, pin_name_offset=0)
    pf.graphics[0].append(poly([(0, 0), (0, 1.27), (-1.016, 1.905), (0, 2.54), (1.016, 1.905), (0, 1.27)], 0))
    pf.pin(1, "pwr", "power_out", 0, 0, 90, 0)
    pf.value_pos = (0, 3.81)
    add(pf)
    return S


SYMBOLS = build_library()


def write_library(path):
    out = ['(kicad_symbol_lib (version 20241209) (generator "class_board_gen") (generator_version "1.0")']
    for name in sorted(SYMBOLS):
        out.append(SYMBOLS[name].sexp())
    out.append(")")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")


if __name__ == "__main__":
    import sys
    write_library(sys.argv[1] if len(sys.argv) > 1 else "class_board.kicad_sym")
    print(len(SYMBOLS), "symbols")
