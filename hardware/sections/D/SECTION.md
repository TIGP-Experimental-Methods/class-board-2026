# Main board — section D

**Rear left - power entry and rails, the coil switches (H-bridge, polarizer), the dev-board socket J1 / J2 and the fast TTL buffer U502.**

Open `class-board.kicad_pro` in this folder (KiCad 10) and route **inside area D only** — the hatched rule area
`ZONE_D` on the board, corners (0.5, 15.5), (96, 15.5), (96, 52), (109, 52), (109, 75), (0.5, 75). Everything the instructor has routed so far is
locked: it is finished, leave it. A connection whose two ends are both inside your area is yours; a connection that
leaves the area is the instructor's — do not route it. Other students route the other areas in their own copies, and the
instructor merges all four copies with `hardware/scripts/main_sections.py merge`: only new tracks and vias that lie
completely inside your area are taken from your copy; tracks outside it, moved parts and new zones are ignored.

**Parts in your area** (111): C201-C204 C206-C217 C502-C504 C703-C705 C707 C722-C727 C905-C908 C916-C921 C930 C931 C940 C941 D201-D206 D501 D920 D930-D934 F201 F202 F901 FB201-FB204 FB901 J12 J13 J201 J202 J901 J903 J905 PS201 PS202 Q901 Q904 R201-R212 R509-R511 R920-R922 R930-R933 R940 R941 TP201-TP204 U201-U204 U502 U503 U903 U904

**Connections still to route in your area** (from the DRC of the master when this copy was made; `AGND` and `GND` are
a via from the pad to the plane or to the ground pour next to it):

| Net | Connections |
|---|---|
| `GND` | 10 |
| `AGND` | 10 |
| `+3V3` | 3 |
| `+5V_RAW` | 3 |
| `/c_switch/VDD904` | 1 |
| `/b5_dio_trig/FASTTTL1` | 1 |
| `+VCOIL` | 1 |
| `/b5_dio_trig/TRIG_5V` | 1 |
| `/b5_dio_trig/FASTTTL2` | 1 |

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

Hand-in: commit `hardware/sections/D/class-board.kicad_pcb` on your branch from the Source Control panel and ask the tutor to
open the pull request. The tutor is the help desk; questions that need the instructor go to s.p.bennetts@g.iams.sinica.edu.tw.
