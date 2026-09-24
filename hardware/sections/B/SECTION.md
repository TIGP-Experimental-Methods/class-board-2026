# Main board — section B

**Front right - the analog outputs (DAC U301 and the output stage) and the NMR transmitter (DDS, filter, power stage, TX terminal side).**

Open `class-board.kicad_pro` in this folder (KiCad 10) and route **inside area B only** — the hatched rule area
`ZONE_B` on the board, corners (109, 59.5), (179.5, 59.5), (179.5, 114.5), (109, 114.5). Everything the instructor has routed so far is
locked: it is finished, leave it. A connection whose two ends are both inside your area is yours; a connection that
leaves the area is the instructor's — do not route it. Other students route the other areas in their own copies, and the
instructor merges all four copies with `hardware/scripts/main_sections.py merge`: only new tracks and vias that lie
completely inside your area are taken from your copy; tracks outside it, moved parts and new zones are ignored.

**Parts in your area** (70): C301-C308 C801-C818 D301 D302 D801 D802 FB801 FB802 J10 J11 L801 R301-R311 R801-R818 TP301 U301-U303 U801 U802

**Connections still to route in your area** (from the DRC of the master when this copy was made; `AGND` and `GND` are
a via from the pad to the plane or to the ground pour next to it):

| Net | Connections |
|---|---|
| `/b3_outputs/VREF_DAC` | 1 |
| `SPI_SCLK` | 1 |
| `SPI_MOSI` | 1 |

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

Hand-in: commit `hardware/sections/B/class-board.kicad_pcb` on your branch from the Source Control panel and ask the tutor to
open the pull request. The tutor is the help desk; questions that need the instructor go to s.p.bennetts@g.iams.sinica.edu.tw.
