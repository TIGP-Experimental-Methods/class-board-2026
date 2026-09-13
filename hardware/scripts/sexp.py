"""Tiny S-expression helpers for writing KiCad files (no external deps)."""
import uuid as _uuid

# Deterministic UUIDs (2026-09-13): the same script run twice yields the same files, so a
# hand-routed PCB keeps its symbol<->footprint links across schematic regenerations.
# uid() hands out a reproducible sequence; uid_for(key) derives a UUID from a stable key
# (sheet name, reference designator) and is used for everything the PCB refers to.
_NS = _uuid.UUID("6f0c3b2e-5c1a-4e3f-9b7d-2a8e1c4d5f60")
_seq = [0]

def uid():
    _seq[0] += 1
    return str(_uuid.uuid5(_NS, "seq:%d" % _seq[0]))

def uid_for(key):
    return str(_uuid.uuid5(_NS, "key:" + str(key)))

def uid_reset():
    _seq[0] = 0

def q(s):
    """Quote a string for KiCad s-expressions."""
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\n")
    return '"%s"' % s

def num(v):
    """Format a number compactly (KiCad style)."""
    if isinstance(v, int):
        return str(v)
    s = ("%.6f" % v).rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    return s

def font(size=1.27, hide=False, justify=None, bold=False):
    parts = ["(font (size %s %s)%s)" % (num(size), num(size), " (bold yes)" if bold else "")]
    if justify:
        parts.append("(justify %s)" % justify)
    if hide:
        parts.append("(hide yes)")
    return "(effects %s)" % " ".join(parts)
