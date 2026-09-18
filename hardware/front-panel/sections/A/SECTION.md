# Front panel — section A

**Analog signals: link J1 to the SMA field and the TX coil terminal.**

Open `front-panel.kicad_pro` in this folder (KiCad 10). Route the nets in the table below and nothing else. The other
nets stay unrouted in your copy; another student routes them in theirs, and the instructor merges all four copies with
`hardware/scripts/panel_sections.py merge`. Tracks on nets that are not yours, moved parts and new zones are ignored at the merge.

| Net |
|---|
| `AI1` |
| `AI2` |
| `AI3` |
| `AI4` |
| `AI5` |
| `AI6` |
| `AI7` |
| `AI8` |
| `AO1` |
| `AO2` |
| `AUX` |
| `RX` |
| `TX` |

Rules of the board (the design rules in `front-panel.kicad_dru` check them for you with DRC):

- Signal layers are F.Cu and B.Cu only. In1.Cu is the AGND plane and In2.Cu the GND plane: no tracks there.
- Track width 0.25 mm, clearance 0.2 mm (analog inputs 0.3 mm), vias 0.6 / 0.3 mm. Analog nets stay away from the
  digital ones where you can.
- A GND or AGND pad of one of *your* parts connects to its plane with a via next to the pad. Do not draw ground tracks
  across the board.
- Isolated inputs (section D): everything in the ISO groups keeps 2.5 mm from every other net, on every layer; the
  keep-out areas on the board show where.
- Do not move parts, do not edit the schematic. If a part is in the way, say so — the instructor moves it in the master.
- Save, then run DRC (Inspect → Design Rules Checker): your nets should show no unconnected items and no violations.

Hand-in: commit `hardware/front-panel/sections/A/front-panel.kicad_pcb` on your branch from the Source Control panel and ask the
tutor to open the pull request. The tutor is the help desk; questions that need the instructor go to s.p.bennetts@g.iams.sinica.edu.tw.
