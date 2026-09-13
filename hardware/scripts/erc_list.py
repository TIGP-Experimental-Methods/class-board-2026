"""Print kicad-cli ERC/DRC JSON reports as compact lines (positions in mm)."""
import json
import sys
import collections

path = sys.argv[1]
d = json.load(open(path, encoding="utf-8"))
cnt = collections.Counter()
if "sheets" in d:
    for sh in d["sheets"]:
        for v in sh["violations"]:
            cnt[(v["severity"], v["type"])] += 1
            items = " | ".join("%s @(%.1f,%.1f)" % (it.get("description", "")[:55], it["pos"]["x"] * 100 if it["pos"]["x"] < 20 else it["pos"]["x"], it["pos"]["y"] * 100 if it["pos"]["y"] < 20 else it["pos"]["y"]) for it in v.get("items", []))
            print(sh["path"][:18].ljust(18), v["severity"][:4], v["type"], ":", v["description"][:60], "::", items[:180])
else:
    for key in ("violations", "unconnected_items", "schematic_parity"):
        for v in d.get(key, []):
            cnt[(key, v["severity"], v["type"])] += 1
            items = " | ".join("%s @(%.2f,%.2f)" % (it.get("description", "")[:60], it["pos"]["x"], it["pos"]["y"]) for it in v.get("items", []))
            print(key[:10].ljust(10), v["severity"][:4], v["type"], ":", v["description"][:70], "::", items[:200])
print("----")
for k, v in sorted(cnt.items()):
    print(v, k)
print("total", sum(cnt.values()))
