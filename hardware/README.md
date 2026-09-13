# hardware/ — the class board in KiCad 10 (rev B, v0.7)

**What the board is.** The class board turns the ESP32-S3 dev board into a small **NMR console**. A pair of coils makes
a field of about **2 mT**; the protons in a bottle of water precess in it at **89 kHz**. The board synthesises a short
pulse at that frequency, drives it into a coil, blanks its own receiver while the pulse is on, then listens: the
**free induction decay** that comes back is amplified, mixed down to an audio frequency, sampled on two channels of the
converter and turned into a **spectrum** on the phone. Everything a hospital scanner does is there except the magnet,
and the same console reaches a higher field later by changing only the coil, the amplifier and the drive level.
*Rule of thumb: the physics is set by the coil; the board is set by noise, by timing, and by what happens when you
switch an amp off.* Around that console sit the general-purpose parts of a lab instrument: eight analog inputs, two
±10 V outputs, eight TTL lines, a trigger, four relays and two isolated inputs.

Design record for v0.7: `notes/2026-09-13-nmr-respec-proposal.md` and `notes/2026-09-13-v07-nmr-circuits.md` in the
course repository; the older full specification is `10-Class-Board-Design-Brief.md` there.

## The KiCad project

The CAD files are generated on the instructor's machine and copied into this folder before Workshop 2. When they are
here, the folder looks like this:

```
hardware/
  class-board.kicad_pro     ONE project: open this
  class-board.kicad_sch     root sheet: interface table + sheet symbols
  sheets/                   base_mcu, b1_inputs, b2_power, b3_outputs, b4_switching, b5_dio_trig,
                            nmr_rx (receiver, mixer, clocks), nmr_tx (DDS + power stage),
                            c_switch (H-bridge, polarizer switch, external power input), front_panel_link
  class-board.kicad_pcb     4-layer main board with the rule areas ZONE_BASE, ZONE_A, ZONE_B, ZONE_C
  class-board.kicad_dru     the custom design rules (loaded from the project root)
  front-panel/              the 2-layer panel PCB: the SMA grid, OLED header, LEDs, 2x20 female link
  student/                  the gapped schematic copies, one per section: a_gapped, b_gapped, c_gapped
  docs/                     design-decisions, requirements, design-review, bring-up, student-deletions
  lib/                      project-local symbols, footprints and 3D models
  jlc/                      Gerbers, drill, BOM.csv, CPL.csv and the quote per order
  AGENTS.md                 rules for the layout agent
```

## How to open
KiCad 10.0.x. Open `class-board.kicad_pro`. Libraries are project-local (`sym-lib-table`, `fp-lib-table` in this
folder); 3D models resolve through the project path variable `CLASS_BOARD_3D`.

## The three sections

| Section | What is in it | The one part you fetch from the JLCPCB parts library |
|---|---|---|
| **A — inputs and the NMR receiver** | ADS8688 and the eight input networks; the tuned coil input and its crossed-diode limiter, the low-noise amplifier, the blanking switch, the I/Q commutating mixer, the IF filters into converter channels 7 and 8, the Si5351A clock generator and the quadrature divider | OPA1656, `C1849431` |
| **B — signal generation, timing and the NMR transmitter** | DAC8563 + OPA2192 (AO1/AO2); the AD9834 DDS, the reconstruction filter and the OPA564 power stage whose enable pin is the transmit gate; 74AHCT541 / 74HCT125 / 74LVC1T45, TRIG, and the I²C expander that drives the DIO lines and the relay drivers | AD9834, `C116589` |
| **C — power and switching** | the external power input (fuse, TVS, reverse-polarity FET); four relays and two isolated inputs; the DRV8871 H-bridge for field cycling; the polarizer MOSFET switch with its three flyback options | DRV8871, `C75864` |
| *instructor* | the base (dev-board socket, buses, link header), the front panel, and the **power-entry sheet** (USB-C, jack, ORing, the rails) — a mistake there spoils every board, so it is not a student exercise | |

Sections are assigned at the start of Workshop 2 (volunteers first, then lots). Review ring: A → B → C → A.

## Reference numbering (the owner rules depend on it)
base 1–99 · 1xx inputs (A) · 2xx power entry and rails (instructor, inside C) · 3xx analog outputs (B) ·
4xx relays and isolated inputs (C) · 5xx DIO, TRIG and the expander (B) · **7xx receiver and clocks (A)** ·
**8xx DDS transmitter and power stage (B)** · **9xx mixer and IF (A); coil switches and the external power input (C)**.
Keep the same references in the gapped copies so footprints keep their positions after *Update PCB from schematic*.

## The two rules for students
1. **Edit only inside your own rule area, and only your own gapped sheet.** Your rule area is `ZONE_A`, `ZONE_B` or
   `ZONE_C` on the PCB; your schematic file is `student/<a|b|c>_gapped.kicad_sch`. Nothing outside it — not the net
   classes, not the instructor's tracks, not another section's copper. What was deleted from your sheet is listed in
   `docs/student-deletions.md`.
2. **Git from VS Code's Source Control panel.** Stage, commit, push and open the pull request from the panel, never
   from a terminal. One pull request per deliverable, reviewed by your ring neighbour.

Also: nothing on In1.Cu (layer 2 is a solid ground plane), decoupling capacitors next to the pin they serve, the
`LCSC` field filled on every part you place, 2.5 mm of clearance around the isolated inputs, and wide traces with no
neck-downs on anything carrying amps.

## Who else edits what
- Layout agent: `astra-layout` branch, `AGENTS.md` rules, never the schematic.
- Instructor: everything else; merges student zones by *copy → Paste Special (in place)* of the tracks inside each
  `ZONE_A` / `ZONE_B` / `ZONE_C`.

## Order (Mon 2026-09-28, 2 pm — hard cutoff)
JLCPCB Economic PCBA, SMD + THT, 5 assembled + 2 bare main boards (4-layer JLC04161H-7628), 6 assembled front panels
(2-layer). BOM columns: Comment, Designator, Footprint, LCSC Part #. CPL: Designator, Mid X, Mid Y, Layer, Rotation.
DNP excluded.
