# Main board — section A

**Rear right - the analog inputs: the ADC U101, the input conditioning R11x / C11x / D11x, the AGND-select headers J14 / J15.**

Open `class-board.kicad_pro` in this folder (KiCad 10) and route **inside area A only** — the hatched rule area
`ZONE_A` on the board, corners (96, 15.5), (179.5, 15.5), (179.5, 59.5), (109, 59.5), (109, 52), (96, 52). Everything the instructor has routed so far is
locked: it is finished, leave it. A connection whose two ends are both inside your area is yours; a connection that
leaves the area is the instructor's — do not route it. Other students route the other areas in their own copies, and the
instructor merges all four copies with `hardware/scripts/main_sections.py merge`: only new tracks and vias that lie
completely inside your area are taken from your copy; tracks outside it, moved parts and new zones are ignored.

**Parts in your area** (49): C101-C108 C111-C118 C501 C507 D111-D118 J14 J15 R101 R102 R111-R118 R501-R508 U101 U501 U505

**Connections still to route in your area** (from the DRC of the master when this copy was made; `AGND` and `GND` are
a via from the pad to the plane or to the ground pour next to it):

| Net | Connections |
|---|---|
| `AGND` | 11 |
| `GND` | 1 |
| `/b1_inputs/AIN7` | 1 |
| `/b1_inputs/AIN8` | 1 |

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

Hand-in: commit `hardware/sections/A/class-board.kicad_pcb` on your branch from the Source Control panel and ask the tutor to
open the pull request. The tutor is the help desk; questions that need the instructor go to s.p.bennetts@g.iams.sinica.edu.tw.
