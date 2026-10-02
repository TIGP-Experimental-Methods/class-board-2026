"""check_housing.py - re-run the fit checks on CompleteHousing.scad after any change.

Run from this folder:
    uv run --with trimesh --with numpy --with rtree python check_housing.py
Needs OpenSCAD 2021.01 (default Windows path below, or set the OPENSCAD environment variable).
Takes a few minutes. Prints three checks; the expected results are stated with each.
The board transforms below must stay in step with boards() and devboard() in CompleteHousing.scad.
"""
import os, subprocess, tempfile
import numpy as np, trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
RELEASE = os.path.join(HERE, "..", "..", "..", "..", "hardware", "release")
OPENSCAD = os.environ.get("OPENSCAD", r"C:\Program Files\OpenSCAD\openscad.com")
TMP = tempfile.mkdtemp()

def export(part):
    out = os.path.join(TMP, part + ".stl")
    r = subprocess.run([OPENSCAD, "-o", out, "-D", f'part="{part}"', os.path.join(HERE, "CompleteHousing.scad")],
                       capture_output=True, text=True)
    for line in r.stderr.splitlines():
        if "WARNING" in line or "ERROR" in line:
            print(f"  {part}: {line}")
    return trimesh.load(out)

def board_points(path, T):
    v = np.unique(np.round(trimesh.load(path).vertices, 3), axis=0)
    return trimesh.transform_points(v, T)

T_panel = np.eye(4); T_panel[2, 3] = 11                                              # stack = 11
T_main  = np.array([[-1, 0, 0, 180], [0, 1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]], float)  # turned over
T_dev   = np.array([[-1, 0, 0, 99.8], [0, 0, -1, -68.8], [0, -1, 0, -13.65], [0, 0, 0, 1]], float)  # devboard()

print("exporting parts ...")
parts  = {p: export(p) for p in ("base", "cover", "sma", "oled")}
labels = {p: export(p) for p in ("cover_labels", "sma_labels")}
boards = {"front panel": board_points(os.path.join(RELEASE, "front-panel.stl"), T_panel),
          "main board":  board_points(os.path.join(RELEASE, "class-board.stl"), T_main),
          "dev board":   board_points(os.path.join(HERE, "models", "YD-ESP32-S3.stl"), T_dev)}

print("\n1. Clash test: board-model points inside each part.")
print("   Expected: all 0, except front panel in oled = 4 (corners of the block-shaped OLED model on the bosses)")
print("   and front panel in sma = 64 (the SMA base corners the plate rests on, z = 14.4).")
for bname, P in boards.items():
    for pname, solid in parts.items():
        lo, hi = solid.bounds
        sel = P[np.all((P > lo - 0.01) & (P < hi + 0.01), axis=1)]
        n = int(solid.contains(sel).sum()) if len(sel) else 0
        print(f"   {bname:12s} in {pname:5s}: {n}")

print("\n2. Inlay test: points just inside each label that the host part also fills. Expected: 0.")
for host, lab in (("cover", "cover_labels"), ("sma", "sma_labels")):
    h, l = parts[host], labels[lab]
    pts, fi = trimesh.sample.sample_surface(l, 6000)
    inner = pts - l.face_normals[fi] * 0.03
    inner = inner[l.contains(inner)]
    print(f"   {lab}: {int(h.contains(inner).sum())} of {len(inner)}")

print("\n3. SMA plate with every jack 0.5 mm off (plate shifted in 8 directions).")
print("   Expected: 0 panel points inside, 4 of 4 base corners under the plate for every jack,")
print("   plate underside 14.40 = SMA base top, lip top 17.60 = cover underside.")
plate, panel, base_top = parts["sma"], boards["front panel"], 12.6 + 1.8
print(f"   plate underside {plate.bounds[0][2]:.2f}, lip top {plate.bounds[1][2]:.2f}")
sma = [(75.65 + 18*n, r) for r in (-25.67, -43.67) for n in range(6)] + [(75.65 + 18*n, -61.67) for n in range(4)]
lo, hi = plate.bounds
near = panel[np.all((panel > lo - 1) & (panel < hi + 1), axis=1)]
test = near[np.abs(near[:, 2] - base_top) > 0.02]
for dx in (-0.5, 0, 0.5):
    for dy in (-0.5, 0, 0.5):
        p = plate.copy(); p.apply_translation([dx, dy, 0])
        hits = int(p.contains(test).sum())
        support = []
        for (x, y) in sma:
            r = np.hypot(panel[:, 0] - x, panel[:, 1] - y)
            c = panel[(np.abs(panel[:, 2] - base_top) < 0.02) & (r > 4.0) & (r < 4.7)].copy()
            c[:, 2] += 0.05
            support.append(int(p.contains(c).sum()))
        print(f"   shift ({dx:+.1f},{dy:+.1f}): {hits} points inside, base corners under the plate: min {min(support)} of 4")
