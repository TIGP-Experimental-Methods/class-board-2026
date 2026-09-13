"""Layout metrics for the review log (design-review.md §9): per-net routed length and via count for the critical
nets, distances from the switching sources to the ADC, layer usage.  Reads the saved .kicad_pcb.
Usage: python layout_report.py [board.kicad_pcb]  -> prints Markdown"""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fp_parse import parse, find, first  # noqa: E402

HW = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CRITICAL = ["SPI_SCLK", "SPI_MOSI", "SPI_MISO", "CS_ADC", "CS_DAC", "/base_mcu/SCLK_MCU", "/base_mcu/MOSI_MCU",
            "USB_DP", "USB_DN", "TRIG_IO", "TRIG_DIR", "TRIG_5V", "FAST_OUT1", "FAST_OUT2", "AO1", "AO2",
            "AI1", "AI2", "AI3", "AI4", "AI5", "AI6", "AI7", "AI8", "+5V_RAW", "+3V3", "+12V", "-12V", "+5VA", "AGND"]


def main(path):
    root = parse(open(path, encoding="utf-8").read())
    nets = {int(n[1]): n[2] for n in find(root, "net")}
    length = {}
    vias = {}
    layers = {}
    for s in find(root, "segment"):
        a, b = first(s, "start"), first(s, "end")
        w = float(first(s, "width")[1])
        lay = first(s, "layer")[1]
        net = nets[int(first(s, "net")[1])]
        L = math.hypot(float(b[1]) - float(a[1]), float(b[2]) - float(a[2]))
        length[net] = length.get(net, 0.0) + L
        layers[lay] = layers.get(lay, 0.0) + L
    for v in find(root, "via"):
        net = nets[int(first(v, "net")[1])]
        vias[net] = vias.get(net, 0) + 1
    pos = {}
    for f in find(root, "footprint"):
        at = first(f, "at")
        ref = next((p[2] for p in find(f, "property") if p[1] == "Reference"), "?")
        pos[ref] = (float(at[1]), float(at[2]))

    def dist(a, b):
        return math.hypot(pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]) if a in pos and b in pos else float("nan")
    out = ["| Net | routed length (mm) | vias |", "|---|---|---|"]
    for n in CRITICAL:
        if n in length:
            out.append("| %s | %.1f | %d |" % (n, length[n], vias.get(n, 0)))
    out.append("")
    out.append("Layer copper length: " + ", ".join("%s %.0f mm" % (k, v) for k, v in sorted(layers.items())))
    out.append("Total vias: %d; nets with vias: %d" % (sum(vias.values()), len(vias)))
    out.append("")
    out.append("| Distance | mm |\n|---|---|")
    for a, b in (("PS201", "U101"), ("PS202", "U101"), ("K401", "U101"), ("K404", "U101"), ("U204", "U101"), ("J201", "U101"), ("U101", "J6"), ("U301", "J1"), ("U101", "J1")):
        out.append("| %s to %s (centres) | %.1f |" % (a, b, dist(a, b)))
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HW, "class-board.kicad_pcb"))
