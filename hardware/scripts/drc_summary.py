"""Summarise a kicad-cli DRC JSON report: counts per type, then the worst pairs per type.
Usage: python drc_summary.py <report.json> [max_pairs]"""
import collections
import json
import re
import sys


def ref_of(desc):
    m = re.search(r"of (\w+)", desc)
    return m.group(1) if m else desc[:24]


def main(path, npairs=30):
    d = json.load(open(path, encoding="utf-8"))
    counts = collections.Counter((v["severity"], v["type"]) for v in d.get("violations", []))
    counts.update(("error", "unconnected_items") for _ in d.get("unconnected_items", []))
    for (sev, typ), n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print("%5d  %-8s %s" % (n, sev, typ))
    print("total", sum(counts.values()))
    for typ in sorted(set(v["type"] for v in d.get("violations", []))):
        L = [v for v in d["violations"] if v["type"] == typ]
        if typ.startswith("silk"):
            c = collections.Counter(tuple(sorted(ref_of(it["description"]) for it in v["items"])) for v in L)
            print("== %s %d" % (typ, len(L)))
            for k, n in c.most_common(npairs):
                print("   %3d %s" % (n, " / ".join(k)))
        else:
            print("== %s %d" % (typ, len(L)))
            for v in L[:npairs]:
                items = " | ".join("%s @(%.1f,%.1f)" % (it["description"][:40], it["pos"]["x"], it["pos"]["y"]) for it in v["items"])
                print("   %s :: %s" % (v["description"][:60], items[:150]))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 30)
