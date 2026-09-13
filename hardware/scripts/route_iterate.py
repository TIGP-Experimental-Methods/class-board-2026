"""Run a generator repeatedly; nets that failed are routed first in the next pass (.route_priority.json).
Usage: python route_iterate.py gen_pcb.py|gen_panel.py [max_passes]"""
import os
import re
import subprocess
import sys

HW = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
gen = sys.argv[1]
max_passes = int(sys.argv[2]) if len(sys.argv) > 2 else 4
prio = os.path.join(HW if gen == "gen_pcb.py" else os.path.join(HW, "front-panel"), ".route_priority.json")
if os.path.exists(prio):
    os.remove(prio)
best = None
for k in range(1, max_passes + 1):
    log = os.path.join(HW, ".route_%s_pass%d.log" % (gen.split(".")[0], k))
    with open(log, "w", encoding="utf-8") as fh:
        subprocess.run([sys.executable, "-u", gen], stdout=fh, stderr=subprocess.STDOUT, cwd=os.path.dirname(os.path.abspath(__file__)))
    text = open(log, encoding="utf-8").read()
    m = re.search(r"^router: .*?(\d+) failures, (\d+)s", text, re.M)
    nfail_net = len(re.findall(r"FAILED \('net'", text))
    nfail_all = int(m.group(1)) if m else -1
    print("pass %d: %s   net failures %d   log %s" % (k, m.group(0) if m else "?", nfail_net, os.path.basename(log)), flush=True)
    if nfail_net == 0:
        break
    if best is not None and nfail_net >= best:
        print("no improvement; stopping")
        break
    best = nfail_net
