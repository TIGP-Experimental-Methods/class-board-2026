# Class board — design decisions and datasheet-derived changes (rev B, v0.7)

D-01 … D-29 are the rev A (v0.6) record and still hold except where a v0.7 entry supersedes them (said in place).
D-30 … D-49 are the v0.7 re-spec of 2026-09-13: three student sections instead of five zones, a 180 × 100 mm board,
and an NMR console in place of the OPT conditioning chain.

Each entry: what the brief (v0.6) said, what the source says, what was done, and how it is verified.
Datasheets were downloaded on 2026-09-07 (TI direct or LCSC `wmsc` host) into `.local/datasheets/` (not committed;
URLs are in the symbol `Datasheet` fields).  "JLC DB" = the local JLCPCB parts database snapshot used through Konnect
(`get_jlcpcb_database_stats`: 785 089 parts); stock figures are a snapshot, not a live quote.

## D-01 Stack-up: L2 and L3 are both unbroken GND (user, 2026-09-07)

- Brief §3 had L3 as power islands.  User instruction: "the two middle layers both pure ground pour".
- Done: JLC04161H-7628, L1 signal + power, L2 GND, L3 GND, L4 signal + power.  Rails are wide outer-layer
  traces/pours (+5V_RAW 1.0 mm min, other rails 0.5 mm min).  AGND is outer-layer copper joined to GND at NT1 only.
- Consequence: every signal on L1/L4 has an adjacent solid GND reference (≈0.2 mm prepreg), the analog inputs
  reference the plane directly, and there are no plane splits to cross.  Brief §3/§4.1/§8 and `prompt.md` updated.
- Verify: DRC custom rule "no tracks on In1.Cu/In2.Cu"; zone fill review of both inner layers (only the ISO_IN void).

## D-02 Power ORing: LM66100 ideal diodes replace the SS34 Schottky pair

- Brief §4.1: polyfuse + SMF5.0A + SS34 ORing; analysis gate item "+5V_RAW drop at 1.2 A … dev board ≥ 4.5 V".
- Sources: SS34 (MDD) V_F 0.55 V max at 3 A (≈0.4 V at 1.2 A); polyfuse 1812L150/33GR R_initial 40 mΩ min,
  160 mΩ post-trip max; USB 2.0/USB-C 5 V source 4.75–5.25 V, cable drop ≈0.1 V at 1.2 A.
- Worst case with the Schottky: 4.65 − 0.19 − 0.42 ≈ 4.04 V at the dev-board 5 V pin → fails the 4.5 V requirement.
- Done: LM66100DCKR (TI, C2869734, Extended, 1659 in JLC DB) per input, CE = GND (always enabled), ST = GND.
  R_ON 79 mΩ typ / 141 mΩ max → 0.10–0.17 V at 1.2 A; worst case ≈4.3–4.5 V, typical ≈4.8 V.
  Reverse-current blocking gives the OR function (higher source wins).  LM66100 V_IN abs max 6 V vs. TVS
  clamp 9.2 V at 21.7 A: a surge exceeding the TVS breakdown is a stress event for the LM66100 too (Low finding, F-07).
- Verify: bring-up test T-02 (rail voltage at 1.2 A load from a 4.75 V source).

## D-03 Relay drive: AO3400A MOSFET + 1N4148W flyback per relay instead of the ULN2003

- Sources: HK4100F-DC5V coil 125 Ω (40 mA), pull-in ≤ 75 % of rated = 3.75 V, max 130 %.  ULN2003A V_CE(sat)
  0.9 V typ / 1.1 V max at 100 mA (≈0.8 V at 40 mA).  With +5V_RAW at 4.55 V worst case the coil would see ≈3.7 V,
  below the guaranteed pull-in.
- Done: AO3400A (C20917, Basic) per channel, R_DS(on) 48 mΩ at V_GS 2.5 V → coil voltage ≈ +5V_RAW − 2 mV.
  1 k gate series, 10 k gate pull-down (relay OFF while the ESP32 boots/resets), 1N4148W (C81598) flyback
  K → +5V_RAW, A → drain.  Yellow LED + 2.2 k from +5V_RAW to the drain shows "coil on" (1.4 mA).
- Verify: T-08 relay pull-in at 4.5 V supply; DRC RELAY_CONTACT class 1.0 mm clearance / 0.5 mm width.

## D-04 ±12 V modules: minimum-load bleeders and AGND reference

- Source: YLPTEC B0512S-2WR3 datasheet p.2–4: load range 10–100 % (min 16.6 mA), accuracy ±15 % at 10 %, Cout ≤ 560 µF,
  recommended Cin/Cout 4.7 µF, input 4.5–5.5 V, 454 mA full-load input current, isolation 1.5 kVDC, pins
  1 = +Vin, 2 = −Vin, 4 = −Vo, 6 = +Vo.
- Done: 3 × 2.2 k (0603, 65 mW each) bleeders on both rails (16 mA) plus rail LEDs (4.7 k, 2 mA): the −12 V rail
  (OPA2192 only when the OPT chain is unpopulated, ≈3 mA) and the +12 V rail (78L05 ≈17 mA + OPA2192) both sit
  above the 10 % minimum.  Output filter FB + 22 µF + 100 nF (22 µF ≪ 560 µF).  Input FB + 10 µF per module.
- Verify: T-03 rail voltages with the OPT chain unpopulated (expect ±12 V ±15 %, i.e. 10.2–13.8 V).

## D-05 DAC8563 logic level: 74HCT125 translates SCLK/DIN/SYNC to 5 V

- Source: DAC8563 electrical table: V_IH = 0.7 × AVDD = 3.5 V at AVDD = 5 V.  A 3.3 V MCU cannot drive it in spec.
  ADS8688 (DVDD 3.3 V) and PGA113 (separate DVDD) are fine at 3.3 V.
- Alternatives considered: DAC at 3.3 V with gain 1 (0–2.5 V, output stage gain 8 → ref noise ×8 and a
  Thevenin-dependent divider); rejected.  74HCT125PW (C131316) is already the B5 fast-out buffer → no new part type.
- Done: U302 74HCT125 on +5V_RAW/GND next to the DAC; 1A/2A/3A ← SPI_SCLK/SPI_MOSI/CS_DAC, 1Y/2Y/3Y → DAC SCLK/DIN/SYNC,
  all /OE and 4A → GND.  Equal propagation delay on the three lines keeps SPI timing.
- Verify: T-09 DAC writes (SPI 10 MHz) produce the expected VOUTA/VOUTB.

## D-06 DAC gain and reference

- Source: DAC8563 §8: internal 2.5 V reference is DISABLED after power-up; gain register defaults to 2 when the internal
  reference is enabled by command.  VREF pin: 150 nF or larger recommended; ±20 mA load capability.
- Done: /LDAC = AGND (synchronous updates), /CLR pulled up to +5VA (10 k), VREF_DAC decoupled with 1 µF and used as the
  difference-amplifier reference (2 × 10 k = 0.5 mA).  Firmware must enable the internal reference (documented in
  the bring-up plan).  The brief's "GAIN pin" does not exist on this device.

## D-07 Output stage resistors

- AO_n = (1 + R2/R1)·R4/(R3+R4)·DAC_n − (R2/R1)·VREF with R1 = R3 = 10 k, R2 = R4 = 40.2 k (C12447, 1 %) → AO_n =
  4.02·(DAC_n − 2.5 V) = −10.05 … +10.05 V.  Worst-case 1 % mismatch: gain error ≤ 2 %, offset ≤ ~50 mV → firmware
  calibration through the AI loop-back (class exercise).  OPA2192 V_S abs max 40 V (±12 V rails, even at the +15 %
  light-load extreme: 27.6 V), ±65 mA short-circuit → ≈±6 V into a 50 Ω termination, ±10 V into ≥ 1 k.
- 49.9 Ω back-termination and BAV99 clamps to the rails after the resistor (C2500: 1 = A1, 2 = K2, 3 = common).

## D-08 Opto inputs: 5–24 V current limiter

- Source: Lite-On 6N137-L: I_F average max 20 mA, recommended I_FH 5–15 mA, threshold I_TH 5 mA max, V_F 1.38 V typ,
  1.70 V max, V_R 5 V, VCC 2.7–3.6 V or 4.5–5.5 V, R_L 330 Ω–4 kΩ, 0.1 µF between pins 8 and 5, pins 2 = anode,
  3 = cathode, 5 = GND, 6 = VO, 7 = VE, 8 = VCC.
- A single resistor cannot span 5–24 V (5 V needs ≤ 430 Ω total; 24 V through 430 Ω gives 50 mA).
- Done: series 1N4148W (reverse blocking), 220 Ω, Q1 MMBT5551 pass transistor, Q2 MMBT5551 sensing V_BE across
  Rs = 100 Ω ∥ 1 kΩ = 91 Ω → I_LED ≈ 0.62/91 ≈ 6.8 mA (5.5 mA at 85 °C, 7.7 mA cold), 10 k base bias.  At 24 V the
  pass transistor dissipates ≈125 mW (MMBT5551 300 mW, 160 V, C2145 Basic).  6N137 output: 1 k pull-up to +3V3,
  VE = VCC, active LOW when the input is driven.
- Verify: T-10 input current at 5 V and 24 V (6.0–8.0 mA), output toggles; DRC ISO_IN class 2.5 mm clearance and no
  copper of any other net under the isolated group on any layer.

## D-09 TRIG output drive

- Source: SN74LVC1T45 I_OH/I_OL ±32 mA at 4.5 V, V_OH ≥ 3.8 V at −32 mA.  Into a 50 Ω termination through 33 Ω the
  level is ≈2.4 V typical (beyond the rated current); into a high-impedance trigger input 5 V.  The brief's 100 Ω
  would give ≈1.5 V into 50 Ω, below TTL V_IH; 33 Ω chosen (documented on the panel silkscreen: "TRIG: hi-Z load").
- BAV99 clamp on the 5 V side to GND/+5V_RAW; DIR = GPIO39 (1 = output).

## D-10 AGND–GND star: KiCad net tie NT1

- Brief allowed "0 Ω 1206 link or net tie".  Done: `NetTie-2_SMD_Pad2.0mm` (copper only, no part, DRC-aware), placed at
  the B1/BASE boundary next to the ADC.  No other AGND–GND join exists (ERC: separate nets; DRC: net-tie exception only).

## D-11 Component library

- Symbols rebuilt (73 + PWR_FLAG) with datasheet pin types; footprints reused from the class repo
  `TIGP-Experimental-Methods/class-board-2026` commit 566fd6f (easyeda2kicad from the same LCSC numbers) plus four new
  imports (LM66100, AO3400A, SN74LVC1G17, SN74LVC1T45) and KiCad-standard mechanical footprints.  Land patterns
  checked against the datasheet drawings: relay (2.54/10.16 × 7.62 grid, pad map 1 = NO, 2 = NC, 3/4 = coil, 5/6 = COM
  from the bottom-view drawing mirrored), module (2.54 pitch positions 1/2/4/6), jack (14.0/7.8/10.75 mm pattern:
  pad 1 = centre pin, 2 = sleeve, 3 = switch), SMA (5.08 mm legs, Ø0.9 pins), KF301 (5.0 pitch, Ø1.2), 1×22 socket
  (2.54, Ø1.02), 2×20 R/A (2.54 × 2.54), USB-C 16P (0.5 pitch pads, 8.64 mm shell holes, 5.78 mm pegs).
- 74LVC1T45 LCSC number resolved: C7843 (76 907 in the DB snapshot).  1×4 OLED socket resolved: XFCN PZ254-1-04-Z-8.5 female header (C2894927, Extended, 23 333 in the DB snapshot),
  KiCad-standard PinSocket_1x04 land pattern (Ø1.0 drill for the 0.64 mm square pins).

## D-12 Dev-board socket row spacing: 25.4 mm ASSUMED — user measurement required

- Official ESP32-S3-DevKitC-1 is 25.5 mm wide with 22.86 mm (0.9 in) row spacing.  The Jinhua #40729 clone is listed
  as 28 × 57 mm (HANDOVER 2026-09-05: "row spacing looks like 25.4 mm").  Two 1×22 sockets are placed at 25.4 mm.
- This is the one dimension the CAD cannot verify; the socket spacing is a single parameter in `gen_pcb.py`
  (`SOCKET_ROW_SPACING`).  Measure a #40729 with calipers before ordering; regenerate if it is 22.86 mm.

## D-13 TCXO option needs a buffer

- Source: KDS 1XTV10000MDA output is a clipped sine into 10 kΩ ∥ 10 pF, VCC 3.3 V, pins 1 = VCONT, 2 = GND, 3 = OUT,
  4 = VCC.  It cannot drive a GPIO directly.  Done: DNP 74LVC1G17 Schmitt buffer with 1 nF coupling, 100 k/100 k bias,
  VCONT 100 k/100 k divider, JP501 (open) to GPIO44.  Zero cost while unpopulated.

## D-14 ADS8688 decoupling values

- Source: datasheet §11.1: AVDD 1 µF (0603) at each supply pin + 10 µF; REFCAP 1 µF + 22 µF directly at the pins (min 10 µF);
  REFIO 10 µF when the internal reference is used; DVDD 10 µF (0805).  REFSEL low = internal 4.096 V reference.
  Pin 3 = DAISY, pin 4 = REFSEL (pin-function table; the datasheet layout figure labels them the other way round —
  both are tied to ground here, so the ambiguity has no effect).  Input abs max ±20 V; 1 MΩ constant input impedance.

## D-15 AMS1117 output capacitor

- Source: datasheet "Stability": 22 µF solid tantalum ensures stability; larger values allowed.  Done: 22 µF X5R 1206 +
  100 nF.  Ceramic ESR is below the tantalum range the device was characterised with; the 1206 (3216) footprint
  accepts a tantalum A-case drop-in if the rail rings at bring-up (T-01 scope check).  Kept because it is the only Basic
  SOT-223 3.3 V LDO with 1 A headroom.

## D-16 Panel LEDs and GPIO43/44 sharing

- LED_PWR = +3V3 directly (series resistor on the panel).  LED_WIFI ← GPIO43 and LED_ACT ← GPIO44 through bridged
  solder jumpers JP1/JP2; GPIO43 doubles as CS_OPT (PGA113) and GPIO44 as the TCXO input — open the jumper when an option
  is populated.  UART0 boot messages on GPIO43 will flicker LED_WIFI at boot (harmless).

## D-17 Expansion header pinout (2×10)

1 +3V3 · 2 +5V_RAW · 3 +12V · 4 −12V · 5 GND · 6 GND · 7 SPI_SCLK · 8 SPI_MOSI · 9 SPI_MISO · 10 GND · 11 I2C_SDA ·
12 I2C_SCL · 13 TRIG_IO · 14 GPIO43 · 15 GPIO44 · 16 AUX_HDR · 17 COND_OUT2 · 18 AGND · 19/20 n/c.

## D-18 BOM additions/removals relative to bom/class-board-bom v0.6

Added: LM66100DCKR ×2 (Ext), AO3400A ×4 (Basic), MMBT5551 ×4 (Basic), 74HCT125PW +1 (same type), SN74LVC1G17DBVR ×1
(DNP), 40.2 k ×4 (Preferred), 220 Ω ×2, 100 Ω ×2, 100 k ×4 (DNP), 0 Ω footprint none.  Removed: SS34 ×2, ULN2003ADR ×1.
Quantities of 2.2 k (+6 bleeders), 1 k, 10 k, 100 nF, 1 µF, 10 µF, 22 µF updated by the netlist-derived BOM in the
release package (authoritative).

## D-19 ADC channel map follows the board geometry (2026-09-08)

- The eight input networks stand in one row straight above the link's AI pins (AI1 left … AI8 right); the ADS8688 sits
  above the row with its analog pins on both long sides.  A planar fan-in (no crossing traces) gives
  AI1→AIN_6, AI2→AIN_7, AI3→AIN_0, AI4→AIN_1, AI5→AIN_2, AI6→AIN_3, AI7→AIN_4, AI8→AIN_5.
- The schematic (b1_inputs) carries this table; the firmware channel-select table must use it.  Any later change of
  the ADC orientation must update both.

## D-20 Front-panel link: pin 1 at the LEFT end, B1 centre-front, B3 right-front (2026-09-08)

- The right-angle 2×20 header must have its mating face at the front edge, which fixes rot 0 (pin 1 at x 45.87,
  odd pins in the row nearer the edge).  The first layout had the connector rotated 180° (pins toward the board
  interior) — wrong mechanically; corrected before routing.
- With the AI pins at x 56–74, the ADC block was moved to the centre-front (5–8 mm AI lines, 15 mm SPI) and the
  DAC/op-amp block to the right-front (AO1/AO2 ≈ 60 mm along the front lane over the AGND pour; op-amp outputs with
  49.9 Ω back-termination and BAV99 clamps tolerate this).

## D-21 AGND copper strategy (2026-09-08)

- AGND pours on F.Cu and B.Cu over the analog band and the ±12 V output area of B2; solid pad connection; islands
  removed.  Fine-pitch AGND pins (ADC, DAC, PGA) get a via to the B.Cu pour at the end of their escape stub because a
  thermal spoke cannot pass between 0.5 mm-pitch pads; other AGND pads either lie in open pour or get a short track to
  the nearest open pour spot.  Pour fragments that carry AGND copper are bridged by 0.5 mm tracks/vias (router pass).
- L2/L3 stay unbroken GND (D-01); AGND and GND meet only at NT1.

## D-22 GND connection of SMD pads: one via per pad (2026-09-08)

- Every SMD GND pad gets its own 0.6/0.3 via to the inner planes (81 vias); THT GND pads connect through the planes.
  The outer GND pours have no pad connection, so the DRC cannot report starved thermal reliefs on them and the return
  path never depends on the outer fill.

## D-23 DRC rule set adjustments found during layout (2026-09-08)

- `relay_contact_clearance` 0.6 mm (was 1.0): the HK4100F package has 0.71 mm between the NO and COM pads, so 1.0 mm
  can only be met between the relay and *other* items; pad-to-pad pairs are excluded from the rule.  30 V DC / 1 A
  contacts need ≥ 0.13 mm (IPC-2221 B2 up to 100 V) — 0.6 mm keeps a > 4× margin.
- `analog_in_clearance` 0.3 mm applies to ANALOG_IN tracks against everything except AGND (the alternating AGND link
  pins and the AGND pour are the guard, not a threat).
- Power minimum-width rules removed: 1.0 mm (+5V_RAW) and 0.5 mm (POWER) tracks are generated everywhere except the
  last ≤ 1.6 mm into a fine-pitch pin, where the router necks to 0.25 mm; a DRC rule cannot express that exemption.
- Netclass clearances all 0.2 mm (the 0.3/1.0/2.5 mm values live in the custom rules so they do not apply between
  pads of the same footprint).
- `owner_*` assertions use `A.getField('Block')` (verified: a deliberately misplaced R101 is reported).

## D-24 Escape stubs and exact 45° geometry (2026-09-08)

- Every SMD pad of a part with pad pitch < 1.1 mm leaves through an exact pad-axis stub (0.25 mm; 0.3 mm pad on
  0.5 mm pitch leaves 0.225 mm to the neighbour) that ends 0.3 mm past the pad end, then a ≤ 0.0625 mm 45° jog onto
  the 0.125 mm routing grid.  Coordinates are kept in integer nanometres so `tools/pcb/audit_angles.py` (1 nm
  tolerance) passes with 0 off-angle segments.


## D-25 Front-panel link header on the back side, mirrored pad numbering (2026-09-08)

- The panel's 2×20 straight female header (C2977589 footprint HDR-TH_40P-P2.54-V-F) sits on the BACK of the panel so
  the SMAs, OLED and LEDs face the user.  Main-board J6 pin 1 is at x = 45.87 mm in the row nearer the edge (lower
  row on the panel); a back-side footprint is mirrored, so panel J1 pad 2k−1 mates with link pin 2k and pad 2k with
  link pin 2k−1.  `gen_panel.py` asserts this geometrically (same x, same row ⇒ same net) for all 40 positions before
  the board is written; the schematic states the mapping.
- The header rows are 3.5 / 6.04 mm above the panel's bottom edge.  The panel hangs on the connector in front of the
  main board's edge; the exact male pin height (C124369) is not on the LCSC drawing — VERIFY with the parts in hand
  that the panel's bottom edge clears the bench (bring-up T-12).

## D-26 Front-panel geometry deviations from brief 7.8 (2026-09-08)

- SMA grid moved up 9 mm (top-left at panel (60, 54) instead of (60, 45)): with the header at the bottom edge the
  brief's third row (y = 5) would have collided with it.  20 mm pitch, 3 × 4 grid, order as specified.
- OLED socket at (20, 44) with the module hanging below it; LEDs at (20, 62 / 57 / 52) (brief: 55..65 reached the edge).
- Panel copper is AGND on both layers (solid pad connection); GND is a routed net (LED cathodes, OLED GND, link GND
  pins).  Analog-input tracks keep 0.3 mm from everything but AGND (panel DRU).

## D-27 Footprint courtyards rewritten (2026-09-08, user request)

- The EasyEDA/JLC-derived footprints carried body-only courtyards (e.g. TSSOP-38 9.7 × 4.4 mm while the pads span
  8.4 mm), so KiCad's courtyard-overlap check and the placement checker were both blind to pad collisions.
  `scripts/fix_courtyards.py` rewrote every F.CrtYd as one rectangle: body (F.Fab/F.SilkS) ∪ pads + 0.25 mm, never
  smaller than the imported outline.  Rows and stacks were re-spaced afterwards (0.4–0.5 mm courtyard gaps).

## D-28 Router fan-out discipline (2026-09-08)

- Every pin row (fine-pitch SMD and 2.54 mm through-hole) owns an escape corridor (0.75 mm) plus a fan-out band
  (2 mm): inside the band only nets belonging to that row may run, and the first 0.5 mm allows moves along the pin
  axis only.  This removed the walling of pin escapes by foreign tracks; the remaining same-row conflicts are handled
  by re-routing failed nets first in the next pass (`route_iterate.py`).
- Panel link J1: signal pins fan out on B.Cu, the GND pins on F.Cu (`layer_hint_net`), so the GND connection along
  the upper row cannot cross the signal escapes.  Main-board J6 odd pins fan out on B.Cu under the input-network row.


## D-29 Ground pins of fine-pitch ICs: inward stitch under the package (2026-09-08)

- At 0.5 mm pin pitch (ADS8688, DAC8563, PGA113) an AGND pin between two signal pins can never receive its own via
  outside the package: a 0.6 mm via between two 0.25 mm traces at 0.5 mm pitch leaves 0.075 mm.  The router therefore
  gives every AGND/GND pin of a fine-pitch IC a short stub *inward* (0.45 mm past the pad end, under the body), joins
  those stubs with a 0.25 mm track along the pin row and takes the stitch out at the package end, where one via to
  the B.Cu AGND pour (or the GND planes) fits.  The signal pins keep their outward escapes; nothing else may run under
  the body.  Same-net thermal behaviour: the stitch carries only the return current of the ADC's negative inputs.


---

# v0.7 (rev B, 2026-09-13) — three sections and an NMR console

Sources for D-30 … D-49: `notes/2026-09-13-nmr-respec-proposal.md` (the re-spec, §3 and §8 in particular),
`notes/2026-09-13-v07-nmr-circuits.md` (the circuit design, with the instructor-side header correction of
2026-09-13), `bom/v07-new-parts-purchase-2026-09-13.md` (purchase list), `NMR/parts-verified-2026-09-13.md`
(LCSC verification, rounds 1–2) and `notes/2026-09-13-tigp-board-state.md` (state of the KiCad project, defects).
All four live in the course repo `G:\My Drive\2. Presentations\2026\20260910-TIGP`.
What was actually built is in `scripts/gen_sch.py`, `scripts/gen_pcb.py` and the three new sheet modules
`scripts/sheet_nmr_rx.py`, `scripts/sheet_nmr_tx.py`, `scripts/sheet_c_switch.py`; where a script deviates from
the circuit document, the script is the record and the deviation is stated below.

## D-30 Three student sections A/B/C replace the five zones B1…B5/OPT (user, 2026-09-13)

- Re-spec §4 and §8.3: three students, not five.  Section **A** = inputs + NMR receiver (old B1 + the OPT area),
  **B** = outputs + timing + NMR transmitter (old B3 + B5 + the new right-hand strip), **C** = power + switching +
  coil switches (old B2 + B4 + the rear-right strip).  The instructor keeps the base (socket, buses, link) and the panel.
- Alternatives: one gapped schematic sheet per student (would have meant merging sheet pairs inside the 1300-line
  `gen_sch.py`, half a day of work — state report §5a); moving b5 from B to C (part counts 80/53/118, worse).
- Done: the `Block` field on every symbol keeps its old value (`B1`, `B2`, …) and three DRC rules map the old values
  onto the three new owner areas — `owner_A` accepts `B1 | OPT | NMR_RX | A`, `owner_B` accepts `B3 | B5 | NMR_TX | B`,
  `owner_C` accepts `B2 | B4 | C_SW | C` (`rules/class-board.kicad_dru`, also at the project root, D-48).  The zone
  polygons in `gen_pcb.ZONES` are `ZONE_A`, `ZONE_B`, `ZONE_C`, `ZONE_BASE`; `ZONE_OPT` and `ZONE_B1/2/3/4/5` are gone.
- Exception: the TCA9535 expander U505 (+ C507, TP501–TP504) carries `Block = BASE` — it serves B (DIO) and C (relays)
  and physically sits in the socket well between the two socket rows, so it belongs to neither student (D-40).
- Part counts from the netlist (404 components): A = 131 (b1_inputs 38 + nmr_rx 93), B = 111 (b3_outputs 25 +
  b5_dio_trig 41 + nmr_tx 45), C = 138 (b2_power 54 + b4_switching 54 + c_switch 30), base 24.
- Verify: DRC `owner_A/B/C` assertions (0 failures with the rule file at the project root); `gen_student.py` gapping.

## D-31 Main board 180 × 100 mm; everything at x ≥ 129 moved +40 mm (user "can make the panel bigger", 2026-09-13)

- Re-spec §8.1 kept 4 relays, 8 DIO and 8 analog inputs, and added three high-current terminals (external power,
  H-bridge coil, polarizer coil).  The state report §5 measured the free board edge on the 140 mm outline:
  5.2 mm on the rear edge and 5.1 mm on the right edge, against the 10.2 mm a KF301-5.0-2P needs — **no terminal fitted**.
- Alternatives: trim relays 4 → 2 and DIO 8 → 6 (withdrawn by the instructor); 160 × 100 (re-spec §8.1) — grew to 180
  when the three terminals plus the NMR TX and RX blocks were placed for real.
- Done: `W, H = 180.0, 100.0` in `gen_pcb.py`; a single loop shifts every placement with x ≥ 129 by +40 mm, so the old
  right-edge furniture (terminals J501–J507 at x 175, mounting holes H2/H4 at x 176) keeps its relationship to the edge
  and no coordinate inside x < 129 changed.  4-layer area cost at 7 boards ≈ +US$10 for the order.
- Consequence: section C owns the rear strip x 128.4–168.9 (the three terminals on the rear edge), section B the block
  x 129.2–170.5 between the old B5/B3 furniture and the terminal column.
- Verify: `place_check.py`, DRC (courtyards, edge clearance), the zone polygons in §2 of `design-review.md`.

## D-32 The OPT conditioning chain is deleted; an NMR console takes its place (user, 2026-09-13)

- The OPT chain was a DNP skeleton with placeholder values (`R607 = "Rf (opt)"`, …), no design record and no D-xx
  (state report §5b).  The course now has a physics goal: proton NMR, **B0 = 2.1 mT, f_Larmor = 89.4 kHz**, thermal
  polarization, 60–250 mL of water, coil-detected (re-spec §2, §7.1).
- Architecture: **heterodyne I/Q receiver**.  The coil signal is mixed with a square LO at f_TX − f_IF to an audio IF
  (5.4 kHz design point) and sampled on **ADS8688 channels 7 and 8** through the existing `COND_OUT1`/`COND_OUT2`
  solder-jumper path (JP101/JP102).  The ADC's 15 kHz input filter, which blocks direct sampling, becomes the IF
  anti-alias filter.
- Why not a fast ADC: **every member of the ADS868x family carries the same 15 kHz filter**, so there is no drop-in
  sibling; MCP33131D-10 (US$8.66, 107 in stock) and ADS9224R (9 in stock) would cap the Larmor frequency at ~400 kHz,
  add a QFN-with-thermal-pad footprint class the library does not have, and the ESP32-S3 has no published > 1 MSPS
  external-ADC ingest (re-spec §3, parts-verified Group 3).  The heterodyne route costs ~US$5, reaches ≥ 1 MHz by
  changing only the tank, the LNA gain and the drive level, and is how a real NMR console works.
- Done: sheet `opt_conditioning` removed from `gen_sch.main()`; sheets `nmr_rx` (93 parts, section A, 7xx + 9xx),
  `nmr_tx` (45, section B, 8xx) and `c_switch` (30, section C, 9xx) added as importable modules.  The OPT symbols
  (INA826, PGA113, TL072, OPA2156) stay in the library and their `put()` entries stay in `gen_pcb.placement()`; the
  build filter drops any placement entry that has no schematic part and prints it, so they cost nothing.
- Verify: ERC 0 on the new sheets; netlist (404 components, 10 sheets); `docs/requirements.md` R-34…R-43.

## D-33 Quadrature LO: Si5351A + a 74HC74 Johnson counter, not the Si5351 phase register

- Circuits doc §1.4, from AN619 §6: `CLKx_PHOFF` is 7 bit in units of T_VCO/4, so a 90° offset needs
  PHOFF = f_VCO/f_out ≤ 127, i.e. **f_out ≥ 600 MHz/127 = 4.72 MHz**, with R = 1 and `MSx_INT = 0`.  Our LO is 84 kHz —
  the register would need 7143.  **The phase-offset method is unusable here.**
- Done: U701 Si5351A-B-GT (C504891, I²C 0x60) with Y701 25 MHz crystal (C9006); CLK0 = 50.000 MHz (PLLA, integer
  MultiSynth 12) to the DDS; CLK1 = 4·f_LO (PLLB, so retuning the LO never disturbs the DDS clock) through R704/C706
  (100 Ω + 47 pF, τ = 4.7 ns) into U702 **74HC74D,653** (C27597) wired as a 2-bit Johnson counter — FF1 D = /Q2,
  FF2 D = Q1, both /CLR commoned to R706 (10 k to +3V3A, with a pad to expander port P1.4).  The four states
  00→10→11→01 give LO_I and LO_Q at f_LO, 50 % duty, exactly 90° apart at any frequency; CLK2 goes to a test point.
- Firmware consequence: pulse /CLR after every PLLB change, or the receiver phase jumps by a multiple of 90° between
  runs and coherent averaging collapses (circuits doc §9.2).
- U702 runs from **+3V3A and is referenced to AGND**, with the switches, so the commutation instants share the signal
  ground; CLK1 is the only line that crosses the GND/AGND boundary.
- Verify: T-15 (scope, two channels on LO_I/LO_Q).

## D-34 AD9834 DDS at 50 MHz MCLK, with a 3 MHz reconstruction filter

- Circuits doc §1.3, §2.1, §2.2.  AD9834BRUZ (C116589, TSSOP-20, 75 MHz, 28-bit, **two phase registers** = hardware
  0/90/180/270° phase cycling through PSELECT, which is the spin-echo/CPMG requirement).  50 MHz was chosen over
  75 MHz: Δf = f_MCLK/2²⁸ = **0.186 Hz** = 1/23 of the 4.2 Hz NMR linewidth, the nearest DAC image moves to 48 MHz, it
  is an integer MultiSynth from a 600 MHz PLL, and it keeps a slower, quieter clock next to a 40 µV receiver.
- Alternatives: AD9833 — dearer (US$12.20 vs 10.21) and weaker (12.5 MHz), dropped (parts-verified Group 1).
- Values: R801 6.80 k on FS ADJUST → I_OUT,FS = 18 × 1.20 V/6.80 k = 3.18 mA; R802/R803 200 Ω → 0.636 V pp, inside the
  0.8 V compliance limit; C807 20 pF against clock feedthrough.  Filter: singly-terminated 3rd-order Butterworth,
  f_c = 3 MHz, C808 390 pF / L801 15 µH (LQH32DN150K53L C341771, SRF 26 MHz — a 22 µH part's 19 MHz SRF would spoil the
  image rejection) / C809 130 pF → 72 dB at the 48 MHz image, −0.05 dB at 2 MHz.
- Deviation recorded in `sheet_nmr_tx.py`: RESET and SLEEP get 10 k **pull-downs** (R817/R818) because AD9834 RESET is
  active high and the expander ports are inputs at power-up; AVDD/DVDD come from +3V3 through FB801 as a local `+3V3D`
  rail, with AGND and DGND tied at the device.
- Verify: T-16.

## D-35 OPA564 power stage: single supply from +VEXT, V− = GND; OPA564AIDWPR (C188648), PowerPAD **down**

- Circuits doc §2.3 gives four datasheet reasons (SBOS372E) for single supply: (1) E/S, VDIG and both flags are
  referenced to V−, so V− = GND lets 3.3 V logic drive them directly — at V− = −12 V each needs an optocoupler
  (datasheet Fig. 38); (2) the PowerPAD is internally connected to V−, so at GND it can sit on the ground pour;
  (3) the isolated ±12 V modules give only 166 mA against the OPA564's 39 mA typ/50 mA max quiescent current;
  (4) the single-supply range is +7 to +24 V, so one 18 V rail has more headroom than ±12 V.
- **Part correction (instructor, 2026-09-13, supersedes the circuits doc §2.3 table and parts-verified Group 2):** the
  part is **OPA564AIDWPR, C188648** (1145 in stock, US$5.15), the **pad-down DWP** package, not C201690/DWD (pad-up).
  Pinout used: V+ 2, T_FLAG 3, E/S 4, +IN 5, −IN 6, V_DIG 7, I_FLAG 8, I_SET 9, T_SENSE 12, V−_PWR 13/14, V_OUT 15/16,
  V+_PWR 17–19, V− 1/10/11/20, EP 21.  The pad is V− = GND: it goes straight onto the GND pour with a via array
  (θ_JA 33 °C/W on a high-K board) and the top-side-heatsink discussion of the circuits doc is void.
- Values: mid-rail bias R805/R806 100 k with C811/C812; gain R807 6.49 k over **a single R808 = 270 Ω** (G = 25.0 →
  15.9 V pp = ±7.95 V = 5.6 mA into the 1419 Ω coil = t90 417 µs).  `sheet_nmr_tx.py` deviates from the circuits doc's
  three-value gain ladder: **JP801 carries one fitted R808**, pads 1–2 bridged, pad 3 spare — the 1.00 k (G 7.49) and
  3.32 k (G 2.95) settings of the ≥ 1 MHz builds are a re-stuff of R808, not three populated resistors.
  C813 100 µF blocks DC in the gain leg (DC gain 1); R809 **11.0 k** on ISET → I_LIM = 1.50 A (*never leave ISET open —
  the datasheet says an open pin damages the device*); R810 10 k beats the internal 100 kΩ pull-up on E/S
  (3.3 × 10/110 = 0.30 V < 0.8 V = shut down until firmware raises TX_EN); VDIG = +3V3; R811/R812 DNP (the flags are
  push-pull CMOS); D801/D802 SS54 clamps, R813 4.7 Ω 1 W series, R814/C817 10 Ω + 10 nF snubber, C818 10 µF DC block
  into the coil (Z = 0.18 Ω at 89 kHz — without it the 9 V mid-rail would push 1.3 A DC through a 6.7 Ω coil).
- **Thermal:** quiescent 39 mA × 18 V = 0.70 W, shutdown 5 mA = 0.09 W, NMR pulses ≤ 1 ms at ≤ 1 % duty ≈ 0.04 W;
  a continuous 1 A sine into 2 Ω would be 4.1 W and needs a clip-on heatsink.  Firmware must hold TX_EN low except
  during a pulse — for the thermal budget as much as for blanking.
- **Supply sequencing (real hazard):** the datasheet requires VDIG before V+ (Fig. 36(A) is marked "not allowed").
  VDIG is +3V3 from USB, V+ is +VEXT from the bench supply, so the order is **USB first, then the bench supply**.
  Silkscreen note at J901 is still to be added to `gen_pcb.py` (see F-16); bring-up T-23 tests it.
- Verify: T-17, T-23.

## D-36 LNA = OPA1656 (FET input), chosen on **current** noise, not voltage noise

- Circuits doc §3.2.  Source impedance at resonance is R_p = Q·X_L = 14.2 kΩ (tank noise 15.3 nV/√Hz).
  OPA1612: e_n 1.1 nV/√Hz but i_n 1.7 pA/√Hz × 14.2 kΩ = 24.1 nV/√Hz → **NF 5.5 dB** (3.5× more averages).
  OPA1656: e_n 2.9 nV/√Hz, i_n 6 fA/√Hz → 15.6 nV/√Hz total → **NF 0.15 dB**.
- Done: U703 **OPA1656IDR** (C1849431); both are dual SOIC-8 with the same pinout and within US$0.01, so the footprint
  takes either and the OPA1612 stays the documented alternate for a tank tapped below ~1 kΩ.  Gain 101 (R712 10.0 k /
  R713 100, JP702 + R714 1.00 k selects G = 11 for the ≥ 1 MHz build) × 10 (R722/R723) = **1000**, which is exactly the
  gain that puts 40 µV pk of coil signal at 1.02 V pk on the ADC (§4.3).  Bandwidth: GBW 53 MHz at G = 101 →
  f_3dB 525 kHz, 0.12 dB of gain error at 89.4 kHz.
- The other three op-amp units are OPA1612 (U705 inverter + V_MID buffer, U706 the two I/Q difference amplifiers),
  where the source impedances are 1–10 kΩ resistor networks and current noise does not matter.
- Verify: T-18.

## D-37 Blanking switch: DG419DY (C6581) replaces the ADG1419; pin 5 VL = +5VA

- Parts-verified Group 2 / R2.1: **ADG1419 (C22368) is out of stock at LCSC and costs US$6.92** — the biggest
  availability and cost risk on the BOM.  DG419DY-T1-E3 (C6581, US$1.62, 1851 in stock, SOIC-8, ±15 V) is the same
  SPDT function on the same kind of process.  Alternative considered: DG413DY quad SPST (C141600, cheaper, 25 Ω) —
  rejected because it is not pin-compatible and the schematic would have to be redrawn.
- Penalty accepted: R_on ~45 Ω instead of 2 Ω.  The switch sits between two amplifier stages, in series with a 10 kΩ
  load, so 45 Ω is 0.45 % of gain — irrelevant.  It would not be acceptable in a 50 Ω path.
- **Pin 5 (VL) is a real logic-supply pin on the DG419, not an ADG1419 no-connect:** it takes **+5VA**, and the
  datasheet specifies the part at VL = 5 V with V_IH 2.4 V / V_IL 0.8 V, so 3.3 V CMOS drive has 0.9 V of margin.
  Supplies V+ = +12 V, V− = −12 V, GND = AGND.
- Verify: ERC (VL is driven, not floating); T-19.

## D-38 The I/Q commutating mixer runs at +3V3A, not +5VA

- Circuits doc §4.1: TS5A23157 control inputs are specified **V_IH = 0.7·V+**.  At V+ = 5 V that is 3.5 V, which a
  3.3 V CMOS LO never meets at any temperature; at V+ = 3.3 V it is 2.31 V, 1.0 V of margin.
- Done: FB901 + 10 µF + 100 nF make **+3V3A** from +3V3; U901/U902 (2 × TS5A23157DGSR, C11133) and the 74HC74 run from
  it; the switch signal range is then 0…3.3 V, so the AC-coupled inputs are biased on V_MID = 1.65 V (U705B buffer)
  and clamped by BAV99 (D905–D908) in case the ±12 V LNA saturates.  **Do not "fix" this to 5 V later.**
- Topology: double-balanced commutator — U901 switches S+/S− into I+ and Q+, U902 the same with the inputs swapped
  (I−, Q−); difference amplifiers G = 20 with 0.1 % thin-film resistors (CMRR ≈ 1/(4·tol) = 54 dB, against 34 dB at
  1 %, which would put tens of mV of LO feedthrough on the ADC).  Conversion gain 2 × (2/π) × 20 = 25.5.
  Reference legs return to AGND so COND_OUT1/2 are centred on 0 V for the ADC's ±5.12 V range.
- Alternatives: SA612/NE602 Gilbert cell (not in the JLC library at all — only the MC1496 is, with 100 pieces), and
  its ~5 dBm compression and 1/f noise hurt at a 10 kHz IF; ceramic IF filters do not exist at 10 kHz
  (re-spec §8.4, parts-verified Group 8).  The commutating ("Tayloe") mixer is US$1 and gives I and Q directly.
- Verify: T-20.

## D-39 RX_BLANK is blanked by default — 10 k pull-**down** to AGND

- Circuits doc §3.3: the DG419 truth table is logic 0 → SW1 on, and SW1 ties the stage-2 input to AGND, so
  **RX_BLANK = 0 is blanked** and 1 is receive (the net keeps its GPIO-map name but is *active-low-receive*).
- The circuits doc's netlist table §3.1 says "R724 10 kΩ to +3V3 — RX_BLANK pull-up (default = blanked)", which
  contradicts its own §3.3 argument.  **`sheet_nmr_rx.py` implements the pull-DOWN** (R724 10 k to AGND): an
  un-driven GPIO (boot, reset, a crashed sequencer) then leaves the receiver blanked, which is the intent.
- Blanking placement: **between the stages**, not at the LNA input.  The DG419's 60 pC of charge injection lands on
  C720 = 10 nF as 6 mV (decaying with τ = R721·C720 = 100 µs) instead of on the 1.25 nF tank as a 48 mV kick that
  would ring for 36 µs at full gain.
- The coupling-capacitor trap: the interstage corner is **1.59 kHz** (10 nF / 10 k), not the innocent-looking
  1.6 Hz of 1 µF / 100 k — after transmit leakage drives the LNA into the rails, a 1.6 Hz corner takes 300 ms to
  recover (four T2* periods, the classic reason a first NMR build sees nothing), a 1.59 kHz corner 0.3 ms, at a cost
  of 0.016 % of amplitude and 1.0° of phase at 89.4 kHz.  Dead-time budget ≈ 1 ms = 1.3 % of T2*.
- Verify: T-19.

## D-40 DIO1–8 and RELAY1–4 move to a TCA9535 I²C expander (U505, owned by BASE)

- Re-spec §8.1: keeping 4 relays and 8 DIO while adding 7 NMR control lines needed 12 GPIO that do not exist.  DIO and
  relays were never timing-critical (the 2026-09-04 spec already had them on an expander, ~100 µs update).
- Done: **TCA9535PWR (UMW) C22396388**, US$0.37, 14 k in stock, TSSOP-24, I²C 0x20 (A0 = A1 = A2 = GND).
  P0.0–P0.7 → DIO1–8 into the existing 74AHCT541; P1.0–P1.3 → RLY_IN1–4 into the existing AO3400A relay gates;
  P1.4–P1.7 spare on TP501–TP504 (P1.4 also feeds the Johnson counter /CLR pad, D-33).  This frees GPIO 4/6/7/15,
  which go to the expansion header (D-17 v0.7), and GPIO 3 is now simply **unused** — the old DIO8 strapping question
  is closed by not using the pin.
- Alternatives: PCA9555PW (C128392, US$1.14) and MCP23017 (C47023, US$1.06) — register-compatible but ~3× the price
  with less stock.  TCA9535 has no internal pull-ups, which is irrelevant for outputs.
- Safety property kept: the 10 k gate pull-down on each relay MOSFET is what holds the relays off during boot **and**
  while the expander powers up with all ports as inputs.  It must not be omitted.
- Block ownership: U505 carries `Block = BASE` and sits at (94.5, 46) in the socket well — it serves both B and C.
- Verify: ERC; T-11 (DIO via the expander), T-10 (relays).

## D-41 External power input: 7–18 V, fuse + SMBJ26A + P-FET (new `+VEXT` rail)

- Circuits doc §7.  The OPA564 (to 1.5 A) and the DRV8871 (to 3.6 A) cannot run from the 2 W isolated ±12 V modules.
- Done: J901 KF301-5.0-2P (C474881, 17 A, **pitch 5.0 mm not 5.08**) → F901 5 A fast-blow 0466005.NRHF (C57525;
  no 5 A-hold PPTC exists in 1812) → D931 **SMBJ26A** (C123820, 26 V standoff > the 24 V maximum input) →
  Q901 **AOD4185** P-FET (C400894, −40 V, 15 mΩ: 0.375 W at 5 A against 2.75 W for a Schottky) with R940 47 k gate
  pull-down and D932 BZX84C12 clamping V_GS (AOD4185 rating ±20 V); C940 100 µF + C941 100 nF bulk; D933/R941 rail LED.
- **The honest limit, on the silkscreen: "+VEXT 7–18 V".**  The OPA564's absolute-maximum supply is 26 V and no TVS
  both passes 24 V and clamps below 26 V (clamping ratios ~1.6×), so 24 V is permitted only with U802 unfitted.  At
  18 V the transmitter still delivers the 15.9 V pp / 417 µs 90° pulse, so nothing is lost.
- Loads on +VEXT: OPA564 V+, DRV8871 VM, UCC27517 VDD and the polarizer gate charge.  Nothing else — ±12 V, +5VA and
  +3V3 are untouched.
- Verify: T-14, T-23.

## D-42 Field-cycling H-bridge: DRV8871DDAR **C75864** (commercial), ILIM always fitted

- Parts-verified Group 3: the re-spec's C701805 is the **Q1 automotive** DRV8871DDARQ1, US$4.15 with 749 in stock;
  **C75864 is the plain commercial part at US$2.01 with 14 463 in stock** — same function, half the price, 19× the
  stock.  The re-spec had them the wrong way round.
- Done: U903 DRV8871 with VM = +VEXT, C920 100 nF at the pin and C921 **100 µF** bulk (sized for the 25 µs internal
  t_OFF window: C = I·Δt/ΔV = 2 A × 25 µs/0.5 V); R920 **32.0 kΩ 1 %** → I_TRIP = 64/R_ILIM(kΩ) = **2.0 A**
  (17.8 k → 3.6 A is the alternative stuffing; the minimum allowed R_ILIM is 15 kΩ and the pin must **never** be left
  open); R921/R922 10 k pull-downs on IN1/IN2 so the bridge coasts at reset; J903 KF301-5.0-2P to the coil.
- **D920 SMBJ26A sits VM → GND, not across the coil.**  The bridge's output FETs have body diodes, so the coil
  freewheels inside the part; the real risk is supply pumping (½LI² = 1.8 mJ into 100 µF from 15 V = a 1.2 V rise),
  and a clamp must fire below the DRV8871's 45 V maximum — which the re-spec's SMBJ58A (74 V breakdown, ~94 V clamp)
  never does.  See D-49.
- PowerPAD: SO-8-EP, a 3 × 3 array of 0.3 mm vias on a 1.0 mm grid to the GND pour, OUT traces ≥ 2 mm for 3.6 A
  (datasheet §10.1).
- Verify: T-21.

## D-43 Polarizer switch AOD4184A + UCC27517, and the three flyback options (adiabatic only)

- Circuits doc §6 and §6.1.  U904 **UCC27517DBVR (UMW) C20623191** (US$0.142, 87 k in stock; TI C99395 is the
  alternate) drives Q904 **AOD4184A C99124** (40 V, 13 A, 7 mΩ, TO-252 — the one part whose "Library Type: Extended"
  was read directly off a JLC page).  R930 10 k pull-down (FET off unless driven), R931 100 Ω edge damping,
  R932 10 Ω gate resistor, C930/C931 at VDD, JP904 selects VDD = +VEXT (default, V_GS 12–18 V at the 7 mΩ spec point)
  or +5V_RAW; silkscreen: +VEXT ≤ 18 V when JP904 selects +VEXT.  J905 KF301-5.0-3P: 1 = +VCOIL, 2 = COIL, 3 = GND.
- Flyback, one footprint set, three stuffings: **(a) D930 SS54 freewheel — fitted**, τ = L/R = 2.6 ms;
  **(b) RC snubber (the Michal route), 2.2 Ω 5 W + 4700 µF 50 V — wired externally across J905 pins 1–2**, because the
  5 W axial resistor and the 4700 µF radial capacitor are too big for the board (this is `sheet_c_switch.py`'s
  deviation from the circuits doc, which drew THT footprints for them); **(c) D934 SMBJ20A (C294873) fast dump —
  DNP**, 591 µs, +VCOIL ≤ 12 V.
- **Designed-in limit:** peak drain voltage must stay under the AOD4184A's 40 V, so a genuinely non-adiabatic
  turn-off (τ ≲ 50 µs at 2.1 kHz, which needs L·I0/50 µs = 241 V of headroom, Michal's published figure) is out of
  reach.  **This board does the adiabatic transfer, not the sudden one.**  +VCOIL ≤ 24 V with the snubber,
  ≤ 12 V with the TVS.
- Verify: T-22.

## D-44 R933 is fitted as a 0 Ω link, not as the 10 mΩ shunt

- Circuits doc §6 lists R933 as an optional 10 mΩ 2512 current-sense resistor, **DNP**.  A DNP part in the source
  return means the polarizer source path is *open* on an unmodified board.
- Done: `sheet_c_switch.py` fits **R933 = 0 Ω 2512** (C2889851) in the source return and brings the node out as
  `ISENSE_COIL` for a spare ADC channel.  Swapping it for a 10 mΩ 2 W part (C500718) turns on the current sense:
  13.4 A × 10 mΩ = 134 mV = 5 % of the ADS8688's ±2.56 V range = 3400 LSB, so no divider is needed; Kelvin-connect
  through 1 kΩ + 100 nF.  P = I²R = 1.8 W at 13.4 A, so it needs the 2 W part (or two 20 mΩ in parallel).
- Verify: T-00 continuity of the source return; T-22.

## D-45 Link pins 37–40 become RX / AGND / TX / AGND

- Re-spec §8.1: the NMR coils need panel connectors.  Pins 37–40 of the 2×20 link carried +5V_RAW/GND and two spares.
- Done: `gen_sch.LINK` and `gen_panel.LINK_V07` both give 37 = RX, 38 = AGND, 39 = TX, 40 = AGND; **+5V_RAW no longer
  reaches the panel** (nothing on the panel draws it: the OLED and the LEDs run from +3V3).  `gen_panel.py` keeps its
  own copy of the four pins and prints a warning if the two tables disagree, and still asserts the whole 40-position
  mirrored mating map geometrically before writing the board (D-25).
- Consequence for section A: RX enters at link pin 37 (x 91.6) and the crossed-diode limiter sits within 5 mm of it;
  TX leaves section B at link pin 39 **and** at the board-edge terminal J802.
- Verify: `gen_panel.py` mating audit; ERC; T-05.

## D-46 Front panel 180 × 65 mm with a 3 × 5 SMA grid (TX, RX, SPARE in the new column)

- Re-spec §8.1.  The panel grows with the main board; the link connector stays centred at main-board x = 70, so the
  panel header keeps its x relative to the left edge and the existing SMA grid does not move.
- Done: `gen_panel.py` W, H = 180, 65; columns at x = 50/70/90/110/130 (20 mm pitch), rows at panel y = 54/34/14
  (D-26).  Row 1 `AO1 AO2 TRIG AUX TX`, row 2 `AI1 AI2 AI3 AI4 RX`, row 3 `AI5 AI6 AI7 AI8 SPARE`.
  **AI7/AI8 stay usable as SMA inputs**: JP101/JP102 on the main board select SMA or mixer per channel (default:
  mixer).  15 SMA are J2…J16, so the **OLED socket is now J17** (it was J14 with 12 SMA) — a renumbering the firmware
  does not see but the panel BOM does.  The SPARE SMA is fitted with its shield on AGND and its centre pin on
  **TP1** only (no link pin).
- Also fixed in the same pass: the panel LED wiring bug — the R–D node now carries a local label, because
  kicad-cli 10.0.3 omits UNNAMED nets from the kicadxml netlist, which left the LED anodes with no net and therefore
  unrouted on the board.
- Verify: `gen_panel.py` link-mating assertion, panel DRC, VIS; T-05.

## D-47 Deterministic UUIDs — and after routing starts, the PCB is the master

- State report §6.13: `gen_sch.py` minted a fresh `uuid4` for every object on every run, so all sheets were rewritten
  byte-differently each time (no reviewable diff) and any KiCad-side edit was unrecoverable after a regeneration.
- Done: `sexp.uid()` is now `uuid5` over a fixed namespace and a per-run sequence counter, and `sexp.uid_for(key)` is
  `uuid5` of a stable key (the root sheet uses `uid_for("root:class-board")`).  The same inputs produce the same file,
  byte for byte, so schematic changes diff.
- **The working rule that follows:** the schematic may be regenerated freely at any time.  The PCB may not — once
  hand routing starts, `class-board.kicad_pcb` becomes the hand-edited master and `gen_pcb.py` is only a placement
  reference.  Regenerating it would delete every track.  (`AGENTS.md` carries this rule.)
- Verify: run `gen_sch.py` twice and diff.

## D-48 The custom design rules live at the project root (and use owner_A/B/C)

- State report §2 / §6.2: KiCad reads `<project>.kicad_dru` from the project folder, so `rules/class-board.kicad_dru`
  was **never loaded** — every claim in the design review that "DRC verifies" the owner rule, the ISO_IN 2.5 mm band,
  the relay-contact clearance or `no_inner_tracks` was unsupported.  Copying the file to the root took the DRC count
  from 127 to 327 violations, of which 199 were `owner_*` assertions failing because the checked-in board file had
  lost its `ZONE_*` rule areas.
- Done: the identical file now exists as **`class-board.kicad_dru` at the project root** (`rules/` keeps its copy as
  the edit source), with the three v0.7 owner rules of D-30; `gen_pcb.py` writes the four `ZONE_*` rule areas into
  every generated board.
- Verify: `kicad-cli pcb drc --severity-all` reports the rules by name; owner assertions pass.

## D-49 Part-number and stocked-value corrections taken from the LCSC verification

- **DRV8871 = C75864** (commercial DRV8871DDAR) — *not* C701805 (Q1 automotive, 2× the price, 1/19 the stock).
- **OPA564 = C188648** (OPA564AIDWPR, PowerPAD **down**) — *not* C201690 (DWD, pad up).  Instructor correction,
  2026-09-13; it is what makes D-35's ground-pour thermal path possible.
- **SMBJ58A (C10226) is dropped from the design.**  74 V breakdown / ~94 V clamp is above the DRV8871's 45 V maximum
  *and* above the AOD4184A's 40 V V_DS, so in both places the semiconductor dies before the clamp conducts.
  Replaced by **SMBJ26A (C123820)** on +VEXT and on DRV8871 VM, and **SMBJ20A (C294873)** as the polarizer fast dump.
- **Crystal load capacitors: 3.9 pF (C519107), not 4 pF.**  The Si5351 datasheet §4.1.1 asks for two 4 pF capacitors
  with a 12 pF crystal and `XTAL_CL = 10 pF`; the JLC component API shows Basic C0G 0603 exists only at
  20/22/47/100 pF, and 3.9 pF (C519107) is the stocked NP0 value nearest 4 pF.  `XTAL_CL` is unchanged, and the
  Si5351 output frequency is calibrated in firmware anyway.
- **9.09 kΩ → 9.1 kΩ (C23260, Basic).**  9.09 k is Extended; the LNA stage-2 gain becomes 1 + 9100/1000 = **10.1**
  instead of 10.0, i.e. 1 % of gain, far inside the ±5 % the coil and tank Q carry.
- Also from the verification: KF301 pitch is **5.0 mm, not 5.08** (C474881 2P 17 A, C474882 3P); the 25 MHz TCXO
  C47018484 has 102 pieces from an obscure vendor, so **Y701 is the plain crystal C9006** (73 795 in stock) and the
  TCXO stays an unfitted accuracy option; 74LVC1G17 = **C7836** (SOT-23-5) replaces the v0.6 C426705 (SOT-353 —
  a different land pattern).
- **Open:** JLC's Basic/Preferred/Extended column is JavaScript-rendered and could not be read automatically; the
  purchase list's classes come from the component-search API, and every line must still be checked by hand in the JLC
  BOM tool before the 28 Sep order (≈ 22 new lines, the ADI/TI/Vishay parts certainly Extended at ~US$3 each).
- Verify: release BOM reconciliation; JLC BOM tool at order time.

## D-50 The panel stacks on the BACK of the board: three 2x20 link headers, connectors move to the panel (2026-09-16)

User decisions #45-#49 (course repo `DECISIONS.md`, proposal `notes/2026-09-14-panel-rework-proposal.md`): the front
panel no longer hangs off the front edge on one right-angle 2x20 header; it lies flat on the **back** of the main
board on three **straight 2x20 male headers** (J6 analog at x ~ 12 mm, J7 digital at x ~ 90 mm, J8 power + spares at
x ~ 168 mm), mounted on the **bottom side (B.Cu)** and hand-soldered from the top.

What was done on the schematic side (`scripts/gen_sch.py`, `cb_symbols.py`, `sheet_nmr_tx.py`):

- New symbol `HDR_2x20_MALE`, KiCad standard footprint `Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical`;
  `HDR_2x20_FEMALE` (panel side) moved to `Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical`.  Both are
  bought separately and soldered by the instructor, so both are `in_bom = no` **and** carry the field
  `Assembly = hand`: `release.py` skips them in the JLC BOM/CPL and writes them to `<board>-hand-solder.csv`
  instead, with the field `Purchase` as the suggested C-number (male C5224014, female 8.5 mm C5124634; the stack is
  8.5 + 2.5 = **11 mm**, so the M3 stand-offs are 11 mm).
- Pin assignment in the dicts `LINK_A` / `LINK_B` / `LINK_C`: odd pin = signal, the even pin beside it = that
  signal's return (AGND on J6, GND on J7 and J8).  Tables in the proposal note section 2.  No RESET / BOOT pins.
- Off the main board: `J501`-`J507` (the TTL and fast-TTL edge terminals, B5), `J802` (the TX coil terminal, NMR TX)
  and `J3` (the second Qwiic, base).  `TTL1..8` and `FASTTTL1/2` now leave the B5 sheet as **global** labels so the
  link sheet can reach them; `J4` stays as the internal Qwiic.  The right edge and the front-right corner of the
  main board become free area.
- New panel-side symbols for the parts that took over: `KF128-2.54-10P` (C474928, 10-way 2.54 mm vertical-entry
  screw terminal, 8 A: TTL1..8 + 2 x GND), `KF128-5.0-2P` (C474950, 24 A: the TX coil), `QWIIC_BM04B-SRSS`
  (C51940129, vertical JST-SH 4-pin); `HDR_1x4_FEMALE` (the OLED socket) becomes right-angle
  (`Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Horizontal`) so the module lies flat on the panel.
  The three EasyEDA footprints were repaired the usual way (prefix stripped, `fp upgrade --force`, courtyard
  rewritten) and the two mechanical shell pads of the JST footprint were numbered 5 / 6 to match the symbol.
- Housekeeping found on the way: the link sheet and `sheet_nmr_rx.py` both numbered their power symbols from 7000,
  which gave duplicate `#PWR` references (`kicad-cli` then warned "schematic has annotation errors").  The link
  sheet now uses the 6xxx range that the deleted OPT sheet left free.

Verified: ERC 0 errors (the one remaining warning is the pre-existing 0.0254 mm root-sheet wire); the netlist puts
each of TTL1-8, FASTTTL1/2, TRIG_5V, AI1-8, RX, AO1/AO2, AUX, I2C_SDA/SCL, LED_WIFI/LED_ACT on exactly one link pin
and TX on two (J6 19 and 21); `J3`, `J501`-`J507` and `J802` are gone; the six sheets that should not have changed
are identical apart from UUIDs.  **The PCB was not touched** (rule 1): `gen_pcb.py` still holds the old placement and
must not be run; the instructor does `Update PCB from Schematic` by hand and places J6/J7/J8 on **B.Cu**.


### D-50a Panel generated: `gen_panel.py` rewritten for 180 x 100 (2026-09-16)

`front-panel/front-panel.kicad_{sch,pro,pcb,dru}` are regenerated from `scripts/gen_panel.py`; the old 180 x 65
one-header panel is gone.

- **Coordinate convention.** The panel is drawn with its **outer face as F.Cu**, so panel coordinates are mirrored
  in x against the main board: `panel x = 180 - main x`, `panel y = main y`.  The main board's rear edge (y = 0) is
  therefore the panel's top edge, marked `REAR / TOP EDGE` on both silkscreens.  Consequence: the analog header
  **J6 (main x 12) is panel J1 at panel x 168** and the power header **J8 (main x 168) is panel J3 at panel x 12**.
- **Main-board side (`MAIN_HEADERS`, must match the master PCB).**  Footprint
  `Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical` on **B.Cu**, pad block centred on (12, 50), (90, 50),
  (168, 50), **rotation 180** - KiCad `at` values (13.27, 25.87) / (91.27, 25.87) / (169.27, 25.87), pin 1 at the
  rear edge.  The footprint's long axis is already along y at rotation 0, so the "rotation 90" of the first
  placement note would have laid the headers across the 180 mm direction (J8 would leave the board); 180 keeps them
  along y and puts pin 1 at the rear.  M3 holes (4, 4) (176, 4) (4, 96) (176, 96) on both boards.
- **Mating.** With that mirror **panel pad k mates main pin k on all 120 pins**: D-25's pairwise swap does not come
  back, because the KiCad `PinSocket` footprint already carries the mating mirror in its own pad geometry (even pins
  at local x = -2.54 against the header's +2.54).  `check_link_mating()` derives each male pin's physical position,
  maps it into panel coordinates and asserts the female pad there carries the same net, for all 120 pins, before the
  board is written; `print_mating_table()` prints the table.
- **Panel layout** (panel coordinates, outer face): SMA grid 3 x 6 at 20 mm pitch, columns **40/60/80/100/120/140**
  (the proposal's 30..130 would have put a column on the centre header at x = 90), rows 25/45/65; 17 fitted
  (J10-J26, row-major; the 18th position, J27, is empty).  OLED socket J30 (right-angle 1x4) pads at y 38 running
  left from x 163, module area 145.7-172.7 x 11-38, held by **H5/H6, M2 (2.2 mm), 23.5 mm apart at y 13.5**; LEDs
  D1-D3 with R1-R3 at x 148/155/162, y 50 and 57; TTL strip J31 (KF128-2.54-10P) centred (33, 88); TX terminal J32
  (KF128-5.0-2P) at (120, 88), under the TX SMA column; Qwiic J33 at (150, 88); TP1 (SPARE) at (128, 72); FID1 (20, 8),
  FID2 (160, 95).  Keep-out: the three female headers are through-hole, so they block both faces over
  x = 12/90/168 +- 2.7 mm, y = 24.4..75.6; `check_keepouts()` asserts no outer-face pad enters those bands.
- **Spare link pins** are left unconnected on the panel (the proposal wanted labelled test pads; only TP1 for the
  SPARE SMA is fitted).  GPIO4/6/7/15/43/44 and +5V_RAW reach the panel but nothing on it uses them yet.
- **Tooling.** `gen_panel.py` now loads KiCad standard footprints (`PinSocket_2x20`, `PinSocket_1x04` horizontal,
  `R_0603_1608Metric`, `MountingHole_2.2mm_M2`) straight from the KiCad installation beside `lib/class_board.pretty`
  and writes each footprint with its own library nickname (`PanelBoard.footprint_sexp`); the project `fp-lib-table`
  still lists only `class_board`, the standard libraries come from the global table.  H5/H6 use the shared M3
  mounting-hole symbol with a per-instance footprint override (`PanelSheet.inst_sexp`).  The router cannot join
  +5V_RAW's two neighbouring pins with a 1.0 mm POWER_RAW track, so `build()` draws that one link pad to pad.
- **Verified 2026-09-16:** ERC **0 errors** (6 warnings: the six GPIO global labels have one pin each), DRC
  **0 errors, 0 unconnected items, 0 schematic-parity issues** (2 cosmetic warnings: J30 and J31 carry their own
  reference text inside their own silk outline), keep-out and 120-pin mating audits pass, two consecutive runs
  byte-identical.  Board: 39 footprints, 43 nets, 681 tracks, 79 vias.
- **Renders:** `docs/front-panel-v07-stacked-top.png` / `-bottom.png` (bottom mirrored).  `kicad-cli pcb render`
  hangs at "Loading 3D models..." on this machine (no 3D context in a headless console), so the pictures are the
  2D layer plots the release script already uses: `pcb export svg` of F/B copper + silk + mask + Edge.Cuts,
  rasterised with pymupdf.

## D-51 The relay channels are built for mains: 10 A relay, MAINS net class, 5 mm reinforced spacing (2026-09-16)

User decision #50 (course repo `DECISIONS.md`, analysis `notes/2026-09-16-mains-safe-relays.md`): *"Make sure the
relays are capable of switching 110 V AC wall plug.  It isn't the aim but it will almost certainly happen if you give
someone a relay and a controller.  Let's make sure it is safe."*  A prohibition printed on the silkscreen is not a
design, so the channels are built for the use that will happen.

**Relay.**  `HK4100F-DC5V-SHG` (C12072, SPDT 3 A, coil 125 Ω) is replaced by **Hongfa `JQC-3FF/005-1ZS(551)`,
LCSC C9221**: SPDT **10 A @ 277 V AC / 10 A @ 28 V DC** (AgCdO), coil 5 V **70 Ω = 71 mA**, 19 × 15.5 × 15 mm,
5 pins, on the KiCad standard footprint `Relay_THT:Relay_SPDT_Hongfa_JQC-3FF_0XX-1Z`.  About +US$0.2 per relay.
The Songle `SRD-05VDC-SL-C` (C35449) is a drop-in alternate: its KiCad footprint
`Relay_SPDT_SANYOU_SRD_Series_Form_C` is the same pattern as the Hongfa land, shifted only in origin — the five pad
positions agree to within 0.05 mm — so either part can be fitted to the board.  The HK4100F symbol stays in
`cb_symbols.py` for reference, unused.

**Pin numbers are the footprint pad names**, which use the IEC / EN 50005 relay numbering:
**A1, A2 = coil** (A1 is the + terminal by convention; the coil has no internal diode, so the polarity is only a
drawing convention — the flyback diode sets the direction), **11 = COM**, **12 = NC** (break), **14 = NO** (make).
The symbol declares exactly those numbers, so the netlist maps pin to pad without a translation table.  The relay
case also prints its own contact diagram: check a sample with a meter at bring-up (T-08) before any mains test.

**Wiring (B4 sheet).**  A1 → +5V_RAW; A2 → the AO3400A drain, with the 1N4148W flyback across the coil and the
yellow coil-on LED unchanged; 11/14/12 → J40x pads 2/1/3 (COM / NO / NC, the terminal order the sheet already used).
The single COM pin replaces the HK4100F's two, so the short COM drop wire is gone.

**Board rating.**  The relay is 10 A; the **board** is rated **250 V AC 5 A MAX per channel, load fused ≤ 5 A** —
3 mm of 1 oz outer copper carries 5 A with a small rise, and short-circuit protection comes from the load circuit,
not from the board.  IEC 62368-1 for 250 V rms working voltage, pollution degree 2, FR4 (material group IIIb):
basic clearance ≈ 1.5 mm, **reinforced = 2 × = 5.0 mm**.  Taiwan is 110 V, but 220 V outlets exist and two channels
can sit on different legs, so the rules are written for 250 V.

**Net classes** (`gen_sch.write_project`): `RELAY_CONTACT` (0.2 mm clearance, 0.5 mm track) is replaced by **`MAINS`**
(clearance **5.0 mm**, track **3.0 mm**, via 0.6/0.3 as Default — vias are forbidden by a rule) plus the four channel
classes **`MAINS1…MAINS4`** with the same numbers.  Patterns: `/b4_switching/RLY_*` → MAINS and
`/b4_switching/RLY_*1…*4` → MAINS1…MAINS4.  **KiCad 10 puts a net in every class whose pattern matches**, which is
what makes the channel rules possible; verified by DRC (the `mains_between_channels*` rules fire, and they can only
match a net that is in MAINS *and* in MAINSn).  `RLY_IN1…4` (the expander gate nets) are global labels with no sheet
path, so the pattern does not catch them.

**Design rules** (`class-board.kicad_dru`, identical copy in `rules/`):

| Rule | Constraint | Why |
|---|---|---|
| `mains_to_other` | clearance ≥ 5.0 mm to any non-MAINS item, all layers, zones included | reinforced insulation between the mains side and the SELV instrument a student touches |
| `mains_between_channels1…4` | ≥ 5.0 mm between different channel classes | two channels can be on different 110 V legs (220 V between them) |
| `mains_within_channel1…4` | ≥ 2.0 mm between the nets of one channel | basic spacing at the switched voltage |
| `mains_edge` | edge clearance ≥ 2.0 mm | a metal lid or a hand at the board edge |
| `mains_layers_inner` / `mains_layers_back` / `mains_no_via` | `disallow track zone` on inner and B.Cu, `disallow via` | mains never enters the inner layers or the bottom side, where the panel headers are |
| `mains_width` | track width ≥ 3.0 mm | 5 A on 1 oz outer copper |

Pad pairs **inside one footprint** are excluded from the clearance rules (`A.memberOfFootprint(B)`): the
coil-to-contact distance of the relay itself is the manufacturer's isolation (1 500 V AC test, basic), not a spacing
the layout may change.

**Rule order matters and cost an hour.**  KiCad applies the **last** matching rule, not the most specific one: with
the MAINS block written in the middle of the file, the generic `copper_to_edge` (0.3 mm) silently replaced
`mains_edge` (2.0 mm), and `analog_in_clearance` (0.3 mm) would have replaced `mains_to_other` for an
analog-track-to-mains pair.  The MAINS block therefore stands **last** in the file, with a comment saying so.  For
the same reason the 2.0 mm within-channel rule wins over the 5.0 mm MAINS *net class* clearance — a custom rule
always beats a net class.

**Rails.**  4 × 71 mA = **285 mA** of coil current from +5V_RAW, against 160 mA before: the root-sheet rails table
estimate goes from 1.0–1.2 A to **1.15–1.35 A** against the ≤ 1.5 A budget.

**Verified 2026-09-16.**  Library 141 symbols; `gen_sch.py` clean; **ERC 0 errors** (the one pre-existing cosmetic
root-wire warning); netlist: K401–K404 carry `Relay_THT:Relay_SPDT_Hongfa_JQC-3FF_0XX-1Z` / C9221, `RLY_NO/COM/NC1–4`
land on relay pads 14/11/12 and terminal pads 1/2/3, coil A1 on +5V_RAW and A2 on the driver drain; `gen_student.py`
regenerates (K401 is still a Section C place-back item, now with the new footprint and LCSC number); an
md5-with-UUIDs-blanked comparison against a rebuild from the previous scripts shows **only** `b4_switching` and the
root sheet changed.  Rules test on a scratch copy of the board: **no parse errors**, and on the current (pre-mains)
placement the rules fire **60 clearance errors** — 51 `mains_to_other` + 9 `mains_between_channels2/3/4` — while a
synthetic board with a deliberately bad track also fires `mains_width`, `mains_layers_inner`, `mains_layers_back`,
`mains_no_via`, `mains_edge` and `mains_within_channel1`.  (The master board has no tracks yet, so only the
placement can violate anything.)

**Still to do on the master PCB (instructor, KiCad GUI — the PCB is hand-edited, never regenerated):**
*Update PCB from Schematic* swaps K401–K404 to the larger footprint in place; then re-space the relay row and the
four 3P terminals along the rear edge at ≈ 22 mm pitch with each terminal **directly behind its own relay** and the
coil pins pointing inward; run DRC and clear what the MAINS rules flag; add the per-channel silkscreen rating
("250 V AC 5 A MAX — load must have its own fuse ≤ 5 A") and a mains-warning symbol; optionally route a 1 mm slot
between the coil pins and the contact pins of each relay (free at JLC, adds creepage).  `gen_pcb.py` must not be run
(rule 1) — and it could not be anyway: it resolves footprints only from `lib/class_board.pretty`, and the new relay,
like the panel-link headers, comes from a KiCad standard library.

**Open for the instructor** (note §5): 5 A on 1 oz copper as above, or order the main board in **2 oz outer copper**
and label the channels 10 A (a JLC price step)?  And: fit the optional slot or not?
