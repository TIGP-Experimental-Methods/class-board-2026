# TIGP class board 2026 — hardware (rev B, v0.7)

Two boards: the **main board** (ESP32-S3 dev-board carrier / lab instrument **and NMR console**, 4-layer
**180 × 100 mm**) and the **front panel** (2-layer **180 × 100 mm**), which mounts **flat on the back of the main
board and parallel to it**, joined by **three straight 2×20 pin headers** (2.54 mm: males on the main board's bottom
side, females on the panel's inner face, hand-soldered by the instructor).  The panel's outer face is the instrument's
face: 17 SMA in a 3 × 6 grid, the TTL screw-terminal strip, the TX coil terminal, a Qwiic, the OLED and 3 LEDs, all
vertical.  The main board's rear edge is the back: USB-C, the 5 V jack, the external 7–18 V input, the coil terminals
and the relay and isolated-input terminals, every one taking its wire off the edge and recessed behind the housing's
back wall.
Specification: `10-Class-Board-Design-Brief.md` v0.6 as amended by the v0.7 re-spec
`notes/2026-09-13-nmr-respec-proposal.md` and the circuit design `notes/2026-09-13-v07-nmr-circuits.md` (all three in
the course repository, not here); build/verification contract: `prompt.md` (same place); working instructions for this
directory: [`AGENTS.md`](AGENTS.md).

## What v0.7 changed (2026-09-13)

- **Three student sections instead of five zones** (D-30): **A** = analog inputs + NMR receiver · **B** = analog
  outputs, digital I/O, timing + NMR transmitter · **C** = power, switching + coil switches.  The instructor keeps the
  base (dev-board socket, buses, expansion header, link) and the front panel.  Ownership is enforced by the DRC rules
  `owner_A` / `owner_B` / `owner_C` on each footprint's `Block` field.
- **An NMR console replaces the OPT conditioning chain** (D-32).  Target: proton NMR at **B0 = 2.1 mT,
  f_Larmor = 89.4 kHz**, thermal polarization, 60–250 mL of water, coil-detected; the architecture reaches ≥ 1 MHz by
  changing only the tank, the LNA gain and the drive level.  Three new blocks:
  - **NMR receiver** (section A, 7xx/9xx): Si5351A + 74HC74 Johnson counter for an exact quadrature LO, tuned tank
    with a crossed-diode limiter, OPA1656 LNA (gain 1000), DG419 blanking between the stages, a double-balanced I/Q
    commutating mixer on two TS5A23157 and IF difference amplifiers into **ADS8688 channels 7 and 8**.
  - **NMR transmitter** (section B, 8xx): AD9834 DDS on a 50.000 MHz clock, 3 MHz Butterworth reconstruction filter,
    OPA564 power stage running single-supply from `+VEXT` (15.9 V pp = a 417 µs 90° pulse), TX on the panel SMA and on
    the coil terminal beside it on the panel.
  - **Power and coil switches** (section C, 9xx): an external 7–18 V / 5 A input with fuse, TVS and a P-FET
    (`+VEXT`), a DRV8871 field-cycling H-bridge, and a UCC27517 + AOD4184A polarizer switch with three flyback
    stuffing options (adiabatic transfer only).
- **Board 180 × 100 mm** (D-31): everything that stood at x ≥ 129 moved +40 mm, which bought 40 mm of rear edge for
  the three new terminals and a column for the transmitter.  The panel grows to **180 × 100 mm** with a
  **3 × 6 SMA grid** (18 positions, 17 fitted: row 1 AO1 AO2 TRIG AUX TX FAST1 · row 2 AI1 AI2 AI3 AI4 RX FAST2 ·
  row 3 AI5 AI6 AI7 AI8 SPARE), stacks flat on the back of the main board through three straight 2×20 headers, and
  takes over the TTL screw terminals, the two fast outputs, the TX coil terminal and one Qwiic (course decisions #45,
  #48 and #49; `notes/2026-09-14-panel-rework-proposal.md` in the course repository).
- **DIO1–8 and RELAY1–4 moved to a TCA9535 I²C expander** (D-40), which freed the 7 GPIO the NMR block needs and
  GPIO 4/6/7/15 for the expansion header.  All 4 relays, 8 DIO and 8 analog inputs are kept.
- **The four relay channels are built to switch mains** (course decision #50): **Hongfa JQC-3FF/005-1ZS** (C9221,
  10 A @ 277 V AC, 19 × 15.5 mm, 5 pins, coil 5 V / 70 Ω ≈ 71 mA) replaces the 3 A HK4100F; the contact nets are the
  **`MAINS`** net class — 5 mm clearance to all other copper on every layer, F.Cu only, no vias, tracks ≥ 3 mm,
  enforced by the DRC.  System rating **250 V AC, 5 A maximum per channel** (set by the copper), the load carrying its
  own fuse of 5 A or less, the rating on the silkscreen per channel.  The AO3400A drivers and the flyback diodes are
  unchanged.  In the housing the rear terminals are recessed behind the back wall.

## Status

**Schematic and placement are generated and current; the main board is not routed.**

- Schematic: root + **10 sheets**, 404 component instances, **ERC clean on the new sheets** (`nmr_rx`, `nmr_tx`,
  `c_switch`); the `opt_conditioning` sheet is gone.
- PCB: 404 footprints placed, the four `ZONE_*` owner rule areas, the GND planes and the AGND pours written,
  **0 track segments** — routing is by hand (Workshop 2: students route their own section, the instructor routes the
  base, the rails and SPI).
- DRC: the custom rules now **load** (the file is at the project root, D-48) and the `owner_A/B/C` assertions pass on
  the generated placement.  A clean DRC on a routed board does not exist yet.
- Front panel: the generated files are still the 180 × 65, 3 × 5 version — the panel and the link sheet must be
  regenerated for the 180 × 100 outline, the 3 × 6 grid and the three headers; the released
  `release/revA/front-panel/` package is the **v0.6** panel and must be rebuilt.
- **No hardware has been built and nothing in `docs/bring-up.md` has been executed** (T-00…T-23 all pending).
  `docs/requirements.md` marks the honest status of every requirement.

## What is where

| Item | Path |
|---|---|
| Main-board project (KiCad 10) | `class-board.kicad_pro`, `class-board.kicad_sch`, `sheets/*.kicad_sch`, `class-board.kicad_pcb`, **`class-board.kicad_dru`** (the rules KiCad actually loads; `rules/class-board.kicad_dru` is the edit source) |
| Schematic sheets | `base_mcu`, `b1_inputs`, `b2_power`, `b3_outputs`, `b4_switching`, `b5_dio_trig`, **`nmr_rx`**, **`nmr_tx`**, **`c_switch`**, `front_panel_link` |
| Sheet modules (v0.7) | `scripts/sheet_nmr_rx.py`, `scripts/sheet_nmr_tx.py`, `scripts/sheet_c_switch.py` — each exposes `build(root_uuid) → Sheet` for `gen_sch.py` and a `PLACEMENT` dict for `gen_pcb.py` |
| Front-panel project | `front-panel/front-panel.kicad_pro/.kicad_sch/.kicad_pcb/.kicad_dru` (generated by `scripts/gen_panel.py`) |
| Project-local library | `lib/class_board.kicad_sym`, `lib/class_board.pretty/`, `lib/class_board.3dshapes/` (both projects use it through their `sym-lib-table` / `fp-lib-table`) |
| Release package | `release/<rev>/main-board/`, `release/<rev>/front-panel/` (Gerbers, drill, BOM, CPL, PDFs, SVG/PNG, STEP, reports, hashes) — only the v0.6 front panel exists so far |
| Design record | `docs/design-decisions.md` (D-01…D-49), `docs/requirements.md` (R-01…R-44), `docs/design-review.md` (floorplan, grounding, PDN, block risks incl. §5.7 NMR, manufacturing, findings F-01…F-20, layout log), `docs/bring-up.md` (T-00…T-23), `docs/student-deletions.md` |
| Student copies | `student/<sheet>_gapped.kicad_sch` (+ `.kicad_pro`, lib tables): section A = `b1_inputs` + `nmr_rx`, B = `b3_outputs` + `b5_dio_trig` + `nmr_tx`, C = `b4_switching` + `c_switch`.  After the panel rework `b5_dio_trig` no longer carries the TTL and fast-output terminals — those nets leave the sheet on the instructor's link sheet.  `b2_power` is **not** gapped — the instructor keeps the power-entry block.  Each copy is a **standalone one-sheet project**: the student opens `student/<sheet>_gapped.kicad_pro`, and ERC there runs standalone (high baseline — only the difference against the ungapped sheet is meaningful, `docs/student-deletions.md`), while the PCB stays the main project |
| Generators | `scripts/` — see `AGENTS.md`; the schematic and the placement are generated, edit the scripts |

## Reference-designator ranges

| Range | Block |
|---|---|
| 1xx | B1 analog inputs (ADS8688 and the eight input networks) — section A |
| 2xx | B2 power entry and rails — section C (instructor-owned within C) |
| 3xx | B3 analog outputs (DAC8563, OPA2192) — section B |
| 4xx | B4 relays (mains-capable channels, `MAINS` net class) and isolated inputs — section C |
| 5xx | B5 digital I/O, fast outputs, TRIG, TCXO option — section B |
| 6xx | former OPT conditioning chain — **deleted in v0.7** |
| **7xx** | **clocks and receiver**: Si5351A, crystal, 74HC74 divider, tank, limiter, LNA, blanking — section A |
| **8xx** | **DDS and transmitter**: AD9834, reconstruction filter, OPA564 power stage, TX terminal — section B |
| **9xx** | **mixer, IF, coil switches and external power**: mixer switches and IF amplifiers (section A); H-bridge, polarizer switch, +VEXT input (section C) |

## Order / assembly configuration the package supports

- **Main board: 7 boards, 180 × 100 mm, 4-layer** JLC04161H-7628 stack-up, 1.6 mm — **5 assembled + 2 bare**;
  Economic PCBA, **top side only** (every JLC-assembled part is on F.Cu; the three link headers on the bottom side are
  hand-soldered, below), SMD + THT; DNP parts (TCXO option, the SMBJ20A fast-dump clamp, the I²C pull-ups duplicated
  on the RX sheet, the flag pull-ups) are excluded from BOM and CPL.
- **Front panel: 6 boards, 180 × 100 mm, 2-layer**, 1.6 mm, all assembled; every assembled part is on the outer
  face, so assembly is single-sided on this board too.
- **The link is hand-soldered, not assembled:** three 2×20 straight males on the main board's bottom side and three
  2×20 straight females on the panel's inner face — the cheapest stocked pair (#49), soldered by the instructor and
  excluded from BOM and CPL, with four M3 stand-offs matched to the stack height.
- BOM columns *Comment, Designator, Footprint, LCSC Part #*; CPL *Designator, Mid X, Mid Y, Layer, Rotation*, origin
  bottom-left, mm, y up.  **Check the component rotations in JLC's upload preview** — still not done (finding F-13),
  and v0.7 adds exposed-pad and fine-pitch packages (HSOP-20 PowerPAD, SO-8-EP, TSSOP-24, MSOP-10, TO-252).
- 97 distinct LCSC lines (v0.6: 44).  **Read Basic/Preferred/Extended by hand in the JLC BOM tool before ordering**
  (D-49): about 22 new lines, the ADI/TI/Vishay silicon certainly Extended at ≈ US$3 each per order.  Estimated order
  cost ≈ US$720 (v0.6 ≈ US$500).  Order cutoff: **Mon 28 Sep 2 pm**.

## Generation rule (v0.7) — the PCB becomes the master

UUIDs are deterministic (`uuid5`, D-47), so regenerating the schematic produces a byte-identical file for identical
inputs and every change diffs.  Therefore:

> **Regenerate the schematic freely.  Never regenerate the PCB once hand routing has started** — from that moment
> `class-board.kicad_pcb` is the hand-edited master and `scripts/gen_pcb.py` is only the placement reference.
> Running it would delete every track.

## Interface summary

- Rails: +5V_RAW (USB-C / jack, LM66100 ORing) → +3V3 (AMS1117); ±12 V isolated modules → +5VA (78L05);
  **+3V3A** (ferrite-filtered, for the Johnson divider and the mixer switches); **+VEXT** (external 7–18 V input, for
  the OPA564, the DRV8871 and the polarizer gate driver only).  AGND ↔ GND only at the net tie NT1.  L2 and L3 are
  unbroken GND planes (D-01).
- ADC channel map (D-19, must match the firmware): AI1→AIN_6, AI2→AIN_7, AI3→AIN_0, AI4→AIN_1, AI5→AIN_2, AI6→AIN_3,
  AI7→AIN_4, AI8→AIN_5.  In v0.7 **channels 7 and 8 (AIN_4/AIN_5) carry the mixer I and Q by default**; JP101/JP102
  restore the panel SMA per channel.
- GPIO v0.7 (D-40, root sheet carries the table): 41 DDS_FSYNC · 42 DDS_PSEL · 40 TX_EN · 8 RX_BLANK · 9/14 HB_IN1/2 ·
  47 FET_GATE; DIO1–8 = TCA9535 P0.0–P0.7, RELAY1–4 = P1.0–P1.3; GPIO 4/6/7/15 free to the expansion header; GPIO 3
  unused.  I²C: OLED 0x3C, TCA9535 0x20, Si5351A 0x60.
- Link: **three straight 2×20 headers** (2.54 mm, 120 pins) replace the single right-angle connector — one for the
  analog signals, one for the digital lines, one for power and the spare pins, with a return pin beside every signal.
  The pin assignment is rewritten together with the link sheet and `gen_panel.py`; the mirrored pad numbering of the
  panel-side headers (D-25) must be asserted geometrically on all three.
- **Power-on order: USB first, then the +VEXT bench supply** (the OPA564 requires VDIG before V+, D-35).
- Open items to close with hardware in hand: dev-board socket row spacing 25.4 mm (D-12), the header stack height
  and the M3 stand-offs matched to it (#49), the land patterns of the new packages (F-12), the CPL rotations (F-13).

## Release status

No main-board release exists.  `release/revA/verification.json` covers the v0.6 front panel only.  A v0.7 release
requires: hand routing finished, DRC 0 errors / 0 unconnected with zones refilled, the angle audit clean, the BOM
without missing LCSC numbers, `scripts/release.py` fixed to find `kicad-cli` (F-15), and the JLC rotation preview
checked.
