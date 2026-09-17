# TIGP class board 2026 — hardware (rev B, v0.7)

Two boards: the **main board** (ESP32-S3 dev-board carrier / lab instrument **and NMR console**, 4-layer
**180 × 100 mm**) and the **front panel** (**4-layer 180 × 100 mm**: 17 SMA on an 18 mm grid, OLED module socket,
3 LEDs, TTL screw strip, TX terminal, Qwiic, two isolated 5–24 V inputs, a 5 V TTL module header, three 2×20 links).
Specification: [`../10-Class-Board-Design-Brief.md`](../10-Class-Board-Design-Brief.md) v0.6 as amended by the v0.7
re-spec `notes/2026-09-13-nmr-respec-proposal.md` and the circuit design `notes/2026-09-13-v07-nmr-circuits.md` (both
in the course repo); build/verification contract: [`../prompt.md`](../prompt.md); working instructions for this
directory: [`AGENTS.md`](AGENTS.md).

## What changed on 2026-09-17 (v0.7d — course-repo Decision #58)

- **The four relays and all mains switching are gone** (D-53).  K401–K404 (JQC-3FF), the terminals J401–J404, the
  AO3400A drivers, the flyback diodes and the coil LEDs are deleted, the whole `b4_switching` sheet with them, and so
  are the `MAINS` / `MAINS1…4` net classes and every `mains_*` DRC rule.  Students who want to switch mains buy a
  ready-made opto-isolated relay module.
- **A module header replaces them.**  TCA9535 ports **P10–P13 and P15–P17 are MODULE OUT 1…7** (`MOD1…MOD7`; P14
  stays the 74HC74 `/CLR` of the NMR receiver).  They cross to the panel on **link J8 pins 19…31 odd**, where one
  **74AHCT541** on +5V_RAW buffers them to 5 V TTL, 47 Ω in series, into a **2×6 shrouded box header**
  (+5 V ×2, OUT1…8, GND ×2; **OUT 8 is a reserved spare**, J8 pin 33 not connected on the main board and held low
  on the panel).
- **The two isolated inputs moved to the front panel** (D-54), circuit unchanged: terminals J411/J412, the 1N4148W +
  220 Ω + MMBT5551 current source and the 6N137 stay together, and `OPTO_IN1/2` return over **J8 pins 35/37** to
  **GPIO16/17**.  The `ISO_IN` class, the 2.5 mm rule and the two keep-outs moved with them.
- **Student section C is the front-panel board** (D-55), a 4-layer project of its own.  The main board's former
  `ZONE_C` — power entry (`b2_power`) plus the coil switches (`c_switch`: +VEXT input, DRV8871 H-bridge, polarizer) —
  is the instructor's **`ZONE_INSTR`** (D-56); `ZONE_B` grew to take the rear-right strip (x 96–179.5, y 0.5–36).
- **The main board was re-placed (v0.7d):** 341 footprints, 0 tracks, the instructor block as one piece at
  **x 45–86** on the rear edge with J901 / J903 / J905 at x **51.0 / 62.7 / 76.9**, rotation 180.

## What v0.7 changed (2026-09-13)

- **Three student sections instead of five zones** (D-30): **A** = analog inputs + NMR receiver · **B** = analog
  outputs, digital I/O, timing + NMR transmitter · **C** = power, switching + coil switches.  *(Superseded
  2026-09-17, D-55: **C is now the front-panel board**, and the power entry and coil switches became the
  instructor's `ZONE_INSTR`.)*  The instructor keeps the base (dev-board socket, buses, expansion header, link).
  Ownership is enforced by the DRC rules `owner_A` / `owner_B` / **`owner_INSTR`** on each footprint's `Block` field.
- **An NMR console replaces the OPT conditioning chain** (D-32).  Target: proton NMR at **B0 = 2.1 mT,
  f_Larmor = 89.4 kHz**, thermal polarization, 60–250 mL of water, coil-detected; the architecture reaches ≥ 1 MHz by
  changing only the tank, the LNA gain and the drive level.  Three new blocks:
  - **NMR receiver** (section A, 7xx/9xx): Si5351A + 74HC74 Johnson counter for an exact quadrature LO, tuned tank
    with a crossed-diode limiter, OPA1656 LNA (gain 1000), DG419 blanking between the stages, a double-balanced I/Q
    commutating mixer on two TS5A23157 and IF difference amplifiers into **ADS8688 channels 7 and 8**.
  - **NMR transmitter** (section B, 8xx): AD9834 DDS on a 50.000 MHz clock, 3 MHz Butterworth reconstruction filter,
    OPA564 power stage running single-supply from `+VEXT` (15.9 V pp = a 417 µs 90° pulse), TX on the panel SMA and on
    a board-edge terminal.
  - **Power and coil switches** (section C, 9xx): an external 7–18 V / 5 A input with fuse, TVS and a P-FET
    (`+VEXT`), a DRV8871 field-cycling H-bridge, and a UCC27517 + AOD4184A polarizer switch with three flyback
    stuffing options (adiabatic transfer only).
- **Board 180 × 100 mm** (D-31): everything that stood at x ≥ 129 moved +40 mm, which bought 40 mm of rear edge for
  the three new terminals and a column for the transmitter.  The panel grows to 180 × 65 mm with a **3 × 5 SMA grid**;
  the new column carries TX, RX and SPARE, and link pins 37–40 became RX / AGND / TX / AGND (D-45, D-46).
  *(Panel geometry superseded: 180 × 100 mm, **4-layer**, 17 SMA at **18 mm** pitch — D-50/D-50a and Decisions
  #57/#58.)*
- **DIO1–8 and RELAY1–4 moved to a TCA9535 I²C expander** (D-40), which freed the 7 GPIO the NMR block needs and
  GPIO 4/6/7/15 for the expansion header.  *(Superseded 2026-09-17, D-53: the four relay ports P10–P13, plus
  P15–P17, are now MODULE OUT 1…7; the relays themselves are gone.)*

## Status

**Schematic and placement are generated and current; the main board is not routed.**

- Schematic: root + **9 sheets** (`opt_conditioning` gone in v0.7, **`b4_switching` gone in v0.7d**).
- PCB: **341 footprints** placed, the `ZONE_A` / `ZONE_B` / `ZONE_INSTR` / `ZONE_BASE` rule areas, the GND planes and
  the AGND pours written, **0 track segments and 0 vias** — routing is by hand (Workshop 2: students route their own
  section, the instructor routes the base, the rails and SPI).
- DRC: the custom rules **load** (the file is at the project root, D-48) and the `owner_A` / `owner_B` /
  `owner_INSTR` assertions pass on the generated placement.  A clean DRC on a routed board does not exist yet.
- Front panel: 4-layer 180 × 100 with the 18 mm SMA grid, the isolated inputs and the module header; it is
  **student section C** and is placed but not routed.  The released `release/revA/front-panel/` package is the
  **v0.6** panel and must be rebuilt.
- **No hardware has been built and nothing in `docs/bring-up.md` has been executed** (T-00…T-23 all pending).
  `docs/requirements.md` marks the honest status of every requirement.

## What is where

| Item | Path |
|---|---|
| Main-board project (KiCad 10) | `class-board.kicad_pro`, `class-board.kicad_sch`, `sheets/*.kicad_sch`, `class-board.kicad_pcb`, **`class-board.kicad_dru`** (the rules KiCad actually loads; `rules/class-board.kicad_dru` is the edit source) |
| Schematic sheets | `base_mcu`, `b1_inputs`, `b2_power`, `b3_outputs`, `b5_dio_trig`, **`nmr_rx`**, **`nmr_tx`**, **`c_switch`**, `front_panel_link` (`b4_switching` deleted 2026-09-17, D-53/D-54) |
| Sheet modules (v0.7) | `scripts/sheet_nmr_rx.py` (A), `scripts/sheet_nmr_tx.py` (B), `scripts/sheet_c_switch.py` (**instructor**) — each exposes `build(root_uuid) → Sheet` for `gen_sch.py` and a `PLACEMENT` dict for `gen_pcb.py` |
| Front-panel project | `front-panel/front-panel.kicad_pro/.kicad_sch/.kicad_pcb/.kicad_dru` (generated by `scripts/gen_panel.py`) — **4-layer, and this is student section C** |
| Project-local library | `lib/class_board.kicad_sym`, `lib/class_board.pretty/`, `lib/class_board.3dshapes/` (both projects use it through their `sym-lib-table` / `fp-lib-table`) |
| Release package | `release/<rev>/main-board/`, `release/<rev>/front-panel/` (Gerbers, drill, BOM, CPL, PDFs, SVG/PNG, STEP, reports, hashes) — only the v0.6 front panel exists so far |
| Design record | `docs/design-decisions.md` (D-01…D-57), `docs/requirements.md` (R-01…R-47), `docs/design-review.md` (floorplan, grounding, PDN, block risks incl. §5.7 NMR, manufacturing, findings F-01…F-23, layout log), `docs/bring-up.md` (T-00…T-23), `docs/student-deletions.md` |
| Student copies | `student/<sheet>_gapped.kicad_sch` (+ `.kicad_pro`, lib tables): section A = `b1_inputs` + `nmr_rx`, B = `b3_outputs` + `b5_dio_trig` + `nmr_tx`.  **Section C is the whole front-panel project**, unrouted, not a gapped sheet (D-55).  `b2_power` and `c_switch` are **not** gapped — they are the instructor's `ZONE_INSTR` |
| Generators | `scripts/` — see `AGENTS.md`; the schematic and the placement are generated, edit the scripts |

## Reference-designator ranges

| Range | Block |
|---|---|
| 1xx | B1 analog inputs (ADS8688 and the eight input networks) — section A |
| 2xx | B2 power entry and rails — **instructor (`ZONE_INSTR`)** |
| 3xx | B3 analog outputs (DAC8563, OPA2192) — section B |
| 4xx | former B4 relays and isolated inputs.  The relays are **deleted**; the isolated inputs (J411/J412 and their parts) and the new module-header block (U410, C410, R481–R489, J40) are on the **front panel** — section C |
| 5xx | B5 digital I/O, fast outputs, TRIG, TCXO option — section B |
| 6xx | former OPT conditioning chain — **deleted in v0.7** |
| **7xx** | **clocks and receiver**: Si5351A, crystal, 74HC74 divider, tank, limiter, LNA, blanking — section A |
| **8xx** | **DDS and transmitter**: AD9834, reconstruction filter, OPA564 power stage, TX terminal — section B |
| **9xx** | **mixer, IF, coil switches and external power**: mixer switches and IF amplifiers (section A); H-bridge, polarizer switch, +VEXT input (**instructor, `ZONE_INSTR`**) |

## Order / assembly configuration the package supports

- **Main board: 7 boards, 180 × 100 mm, 4-layer** JLC04161H-7628 stack-up, 1.6 mm — **5 assembled + 2 bare**;
  Economic PCBA, **top side only** (all parts are on F.Cu), SMD + THT; DNP parts (TCXO option, the SMBJ20A fast-dump
  clamp, the I²C pull-ups duplicated on the RX sheet, the flag pull-ups) are excluded from BOM and CPL.
- **Front panel: 6 boards, 180 × 100 mm, 4-layer**, 1.6 mm, all assembled; every part on the outer face except the
  three 2×20 female link headers on the inner face (THT, CPL layer "Bottom") — the panel is single-sided for
  assembly apart from those headers (Decision #58 d).
- BOM columns *Comment, Designator, Footprint, LCSC Part #*; CPL *Designator, Mid X, Mid Y, Layer, Rotation*, origin
  bottom-left, mm, y up.  **Check the component rotations in JLC's upload preview** — still not done (finding F-13),
  and v0.7 adds exposed-pad and fine-pitch packages (HSOP-20 PowerPAD, SO-8-EP, TSSOP-24, MSOP-10, TO-252).
- The line count and cost below are the 2026-09-13 figures and **must be recounted after v0.7d**: the relays, their
  terminals, drivers, diodes and LEDs came off the main board and the module-header parts (74AHCT541, box header,
  47 Ω, 10 k) went onto the panel.  As counted then: 97 distinct LCSC lines (v0.6: 44), estimated order cost
  ≈ US$720 (v0.6 ≈ US$500).  **Read Basic/Preferred/Extended by hand in the JLC BOM tool before ordering** (D-49):
  the ADI/TI/Vishay silicon is certainly Extended at ≈ US$3 each per order.  Order cutoff: **Mon 28 Sep 2 pm**.

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
- GPIO v0.7d (D-40, D-53, D-54; root sheet carries the table): 41 DDS_FSYNC · 42 DDS_PSEL · 40 TX_EN · 8 RX_BLANK ·
  9/14 HB_IN1/2 · 47 FET_GATE · **16/17 OPTO_IN1/2 (the isolated inputs, now on the panel, over J8 pins 35/37)**;
  DIO1–8 = TCA9535 P0.0–P0.7, **MODULE OUT 1…7 = P1.0–P1.3 and P1.5–P1.7** (P1.4 = the NMR receiver's 74HC74 `/CLR`);
  GPIO 4/6/7/15 free to the expansion header; GPIO 3 unused.  I²C: OLED 0x3C, TCA9535 0x20, Si5351A 0x60.
- Link J6/J1: pinout per brief 7.8 with **pins 37–40 = RX / AGND / TX / AGND** (D-45); the panel's back-side header
  has pairwise-swapped pad numbers (D-25), asserted geometrically by `gen_panel.py`.  **J8 (panel J3)** carries the
  rails, the free GPIO, **MODULE OUT 1…7 on pins 19…31 odd** (pin 33 = the reserved OUT 8, not connected) and
  **OPTO_IN1/2 on pins 35/37**, each with GND on the adjacent even pin.
- **Power-on order: USB first, then the +VEXT bench supply** (the OPA564 requires VDIG before V+, D-35).
- Open items to close with hardware in hand: dev-board socket row spacing 25.4 mm (D-12), panel header mating height
  (D-25), the land patterns of the new packages (F-12), the CPL rotations (F-13).

## Release status

No main-board release exists.  `release/revA/verification.json` covers the v0.6 front panel only.  A v0.7 release
requires: hand routing finished, DRC 0 errors / 0 unconnected with zones refilled, the angle audit clean, the BOM
without missing LCSC numbers, `scripts/release.py` fixed to find `kicad-cli` (F-15), and the JLC rotation preview
checked.
