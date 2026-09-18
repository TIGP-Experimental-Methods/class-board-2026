# Front panel — section C

**Module outputs: link J3 to the pull-downs R491-R498, the 74AHCT541 U410, the series resistors R481-R488 and the module header J40.**

Open `front-panel.kicad_pro` in this folder (KiCad 10). Route the nets in the table below and nothing else. The other
nets stay unrouted in your copy; another student routes them in theirs, and the instructor merges all four copies with
`hardware/scripts/panel_sections.py merge`. Tracks on nets that are not yours, moved parts and new zones are ignored at the merge.

| Net |
|---|
| `MOD1` |
| `MOD2` |
| `MOD3` |
| `MOD4` |
| `MOD5` |
| `MOD6` |
| `MOD7` |
| `MOD8` |
| `MODY1` |
| `MODY2` |
| `MODY3` |
| `MODY4` |
| `MODY5` |
| `MODY6` |
| `MODY7` |
| `MODY8` |
| `MODOUT1` |
| `MODOUT2` |
| `MODOUT3` |
| `MODOUT4` |
| `MODOUT5` |
| `MODOUT6` |
| `MODOUT7` |
| `MODOUT8` |
| `+5V_RAW` |

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

Hand-in: commit `hardware/front-panel/sections/C/front-panel.kicad_pcb` on your branch from the Source Control panel and ask the
tutor to open the pull request. The tutor is the help desk; questions that need the instructor go to s.p.bennetts@g.iams.sinica.edu.tw.
