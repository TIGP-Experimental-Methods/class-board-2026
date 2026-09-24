# Main board — section C

**Front left - the NMR receiver: tank and blanking switch, LNA, I/Q mixer, IF filters, clock generator; the expansion header J5.**

Open `class-board.kicad_pro` in this folder (KiCad 10) and route **inside area C only** — the hatched rule area
`ZONE_C` on the board, corners (0.5, 75), (109, 75), (109, 114.5), (0.5, 114.5). Everything the instructor has routed so far is
locked: it is finished, leave it. A connection whose two ends are both inside your area is yours; a connection that
leaves the area is the instructor's — do not route it. Other students route the other areas in their own copies, and the
instructor merges all four copies with `hardware/scripts/main_sections.py merge`: only new tracks and vias that lie
completely inside your area are taken from your copy; tracks outside it, moved parts and new zones are ignored.

**Parts in your area** (104): C210-C212 C701 C702 C706 C710-C712 C720-C727 C901-C904 C910-C919 D205 D206 D703 D704 D905-D908 J3 J9 PS201 PS202 R1 R2 R203-R208 R211 R212 R703-R706 R710-R716 R721-R724 R901-R919 R923 R924 TP203 TP204 TP501 TP701 TP702 U203 U701-U706 U901 U902 Y701

**Connections still to route in your area** (from the DRC of the master when this copy was made; `AGND` and `GND` are
a via from the pad to the plane or to the ground pour next to it):

| Net | Connections |
|---|---|
| `/b3_outputs/CS_DAC` | 1 |
| `+12V` | 1 |

Rules of the board (the design rules in `class-board.kicad_dru` check them for you with DRC):

- Signal layers are F.Cu and B.Cu only. In1.Cu and In2.Cu are GND planes: no tracks there. AGND is the copper pour on
  F.Cu and B.Cu over the front half of the board (`AGND_F` / `AGND_B`); an AGND pad connects to it directly or with a via.
- Track widths and vias come from the net classes: 0.25 mm / 0.6 mm via for signals, 0.5 mm / 0.8 mm via for POWER,
  1.0 mm for POWER_RAW; clearance 0.2 mm (analog inputs 0.3 mm). Analog nets stay away from the digital ones where you can.
- A GND pad of one of *your* parts connects to the plane with a via next to the pad. Do not draw ground tracks across the board.
- Do not move parts, do not edit the schematic, do not update the PCB from the schematic (F8) — this copy has no schematic on
  purpose. If a part is in the way, say so: the instructor moves it in the master.
- Save, then run DRC (Inspect → Design Rules Checker): the connections inside your area should show as connected and
  your tracks should show no violations.

Hand-in: commit `hardware/sections/C/class-board.kicad_pcb` on your branch from the Source Control panel and ask the tutor to
open the pull request. The tutor is the help desk; questions that need the instructor go to s.p.bennetts@g.iams.sinica.edu.tw.
