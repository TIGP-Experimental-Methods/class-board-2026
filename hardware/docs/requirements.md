# Class board — requirements and verification register (rev B, v0.7)

Status codes: **C** confirmed requirement (source cited) · **P** proposal made in this build (see design-decisions.md) ·
**A** assumption that still needs an external fact · **Q** open question for the instructor.
Verification: DS = datasheet/calculation, ERC/DRC = KiCad checks on the released files, VIS = rendered inspection,
T-nn = bring-up test in `bring-up.md`.  Numbers are from the design brief v0.6, the BOM v0.6, the downloaded datasheets
(2026-09-07) or the calculation shown.  Rows R-34…R-44 and the rows marked **v0.7** come from the re-spec of
2026-09-13 (`notes/2026-09-13-nmr-respec-proposal.md`) and the circuit design
(`notes/2026-09-13-v07-nmr-circuits.md`); their numbers close against the design coil of that document
(400 turns AWG26, 4 cm × 10 cm: L = 2.53 mH, R_DC = 6.7 Ω, X_L = 1419 Ω and R_p = 14.2 kΩ at Q = 10, tuned with
1.25 nF at 89.4 kHz).  **Nothing in this register is hardware-verified: no board has been built.**

---

## 2026-09-17 update (v0.7d) — rows the register no longer asserts

The instructor's decision of 2026-09-17 (course repo `DECISIONS.md` **#58**, design record **D-53…D-57**) removed the
relays and all mains switching, moved the isolated inputs to the front-panel board and made **section C = the
front-panel project**.  **The rows below are not rewritten**; this is what has changed about them.

| Row | Status after 2026-09-17 |
|---|---|
| **R-14** 4 mains-capable relays, MAINS clearances | **Void** (D-53).  No relay, no terminal, no `MAINS*` class, no `mains_*` rule, no 250 V AC board rating.  Replaced by **R-45** and **R-46**. |
| **R-15** 2 isolated inputs 5–24 V | **Valid, relocated** (D-54): same circuit, same numbers, now on the **front-panel** board; the ISO_IN clearance is verified by the panel's DRC, and T-12 is performed on the panel.  See **R-47**. |
| **R-03 / R-44** GPIO and expander map | **Amended** (D-53): `P1.0–P1.3` are `MOD1–MOD4`, not `RLY_IN1–4`; `P1.5–P1.7` are `MOD5–MOD7`; **P1.4 = `EXP_P14`**, the NMR receiver's 74HC74 `/CLR`.  `OPTO_IN1/2` reach GPIO16/17 over link J8 pins 35/37. |
| **R-22** front panel 180 × 65, 2-layer, 15 SMA at 20 mm | **Superseded**: **180 × 100 mm, 4-layer**, 17 SMA on an **18 mm** grid, plus the isolated inputs and the module header; it is **student section C** (D-55). |
| **R-23** main board, three owner areas ZONE_A/B/C | **Amended** (D-56): the areas are **ZONE_A / ZONE_B / ZONE_INSTR** (+ ZONE_BASE); ZONE_B also owns the rear-right strip x 96–179.5, y 0.5–36; 341 footprints. |
| **R-25** design rules incl. the 5.0 mm / 3.0 mm mains values | **Amended**: every `mains` figure is deleted.  The rule file is `no_inner_tracks`, `iso_in_clearance`, `analog_in_clearance`, the manufacturing margins and `owner_A` / `owner_B` / `owner_INSTR`. |
| **R-26** 97 LCSC lines, ≈ US$720 | **To be recounted**: the relay parts left the main board, the module-header parts joined the panel. |
| **R-29** "no DC-DC module, relay or fast digital trace inside the analog zones" | Valid; the relay clause is moot. |

New rows **R-45…R-47** are at the end of the table.

| ID | Requirement | Acceptance criterion | Source | Status | Verification |
|---|---|---|---|---|---|
| R-01 | Carrier for Jinhua #40729 (ESP32-S3-DevKitC-1 pin order, 2×22) | socket pin names match the Espressif v1.1 header tables; 5V pin fed from +5V_RAW; 3V3 pins open | brief 7.1, Espressif user guide, HANDOVER 2026-09-05 | C | ERC, T-01 |
| R-02 | Socket row spacing | footprint spacing equals the measured #40729 spacing (25.4 mm assumed) | HANDOVER 2026-09-05 ("looks like 25.4"), official 22.86 | **A** | user measurement before order |
| R-03 | **v0.7** GPIO interface contract | every net on the GPIO of the v0.7 map (re-spec 8.2, root-sheet table): 41 DDS_FSYNC, 42 DDS_PSEL, 40 TX_EN, 8 RX_BLANK, 9/14 HB_IN1/2, 47 FET_GATE; DIO1–8 and RELAY1–4 on the TCA9535; 4/6/7/15 free to the expansion header; 0/45/46 strapping, 3, 35–37, 48 unused | re-spec 8.2 (D-40) | C | netlist audit (release), ERC |
| R-04 | +5V_RAW entry: USB-C or 5 V jack, 1.5 A polyfuse + SMF5.0A per input, ORed | rail ≥ 4.5 V at the dev-board pin with 1.2 A load from a 4.75 V source | brief 4.1, analysis gate; DS LM66100 R_ON ≤ 141 mΩ; fuse R ≤ 160 mΩ | P (D-02) | DS calc (≥ 4.29 V worst, 4.8 V typ), T-02 |
| R-05 | +3V3 ≤ 500 mA capability, est. < 150 mA load | AMS1117 dissipation ≤ (5.25−3.3)×0.15 = 0.3 W on SOT-223 with copper | brief 4.1, DS AMS1117 | C | DS, T-03 |
| R-06 | ±12 V isolated rails, 166 mA each, referenced to AGND | rails within ±15 % (10.2–13.8 V) at the actual loads; minimum 10 % load always present | brief 4.1, DS B0512S-2WR3 | C + P (D-04) | DS calc, T-03 |
| R-07 | +5VA analog supply from +12 V, ≤ 100 mA | 78L05G dissipation at 17 mA = 0.12 W ≤ 350 mW; ripple from the module attenuated by 78L05 PSRR + FB/22 µF | brief 4.1, DS 78L05G | C | DS, T-03 |
| R-08 | Single AGND–GND star | exactly one net tie; no other copper joins the nets | brief 4.1/7.1 | C | ERC (separate nets), DRC net-tie |
| R-09 | 8 analog inputs ±10 V, 16 bit, SMA on the panel | ADS8688 range ±10.24 V, input network 1 k / 1 nF / BAV99 clamps to ±12 V; abs max ±20 V honoured with 1 k limiting | brief 7.3, DS ADS8688 | C | DS, T-05 |
| R-10 | Input bandwidth | f-3dB = 1/(2π·1 k·1 nF) = 159 kHz; **the ADS8688 analog filter is 15 kHz, not 15 MHz** (corrected 2026-09-13 — it is the reason the NMR receiver is heterodyne, D-32); ADC input 1 MΩ constant | brief 7.3, DS ADS8688 | C | calc, T-05, T-07 |
| R-11 | ADC reference and decoupling per datasheet | REFCAP 1 µF + 22 µF, REFIO 10 µF, AVDD 1 µF ×2 + 10 µF, DVDD 10 µF + 100 nF, REFSEL low | DS ADS8688 §11.1 | C (D-14) | ERC, VIS |
| R-12 | 2 analog outputs ±10 V from DAC8563 | AO = 4.02·(DAC−2.5 V); 16-bit; drive ±10 V into ≥ 1 kΩ, ≈±6 V into 50 Ω | brief 7.4; DS DAC8563, OPA2192 | C + P (D-05..07) | DS calc, T-06 |
| R-13 | DAC logic levels | all DAC inputs driven with V_IH ≥ 3.5 V (74HCT125 at 5 V) | DS DAC8563 V_IH = 0.7·AVDD | P (D-05) | ERC, T-06 |
| R-14 | 4 relays SPDT **mains-capable**: 10 A @ 277 V AC / 28 V DC contacts (JQC-3FF/005-1ZS, C9221); board rating **250 V AC 5 A MAX per channel, load fused ≤ 5 A** | coil reaches ≥ pull-in (3.75 V) at +5V_RAW ≥ 4.5 V (70 Ω, 71 mA, 4 × 71 = 285 mA); relays OFF at boot/reset; MAINS copper 5 mm to everything else and 5 mm channel-to-channel, 2 mm inside a channel, 2 mm to the edge, F.Cu only, no vias, tracks ≥ 3 mm | brief 7.5, DS JQC-3FF/005-1ZS, note `2026-09-16-mains-safe-relays.md` | P (D-03, D-51) | DS calc, DRC `mains_*` rules, T-08 |
| R-15 | 2 isolated inputs, 5–24 V | LED current 5–15 mA over 5–24 V; 2.5 mm clearance from the isolated group to everything else on all layers | brief 7.5, DS 6N137 | P (D-08) | DS calc, DRC ISO_IN, T-10 |
| R-16 | 8 TTL DIO outputs 5 V | 74AHCT541 V_OH ≥ 3.8 V at 8 mA; 1 k series limits a short to 5 mA | brief 7.6, DS | C | T-11 |
| R-17 | 2 fast TTL outputs | 74HCT125, 49.9 Ω series, high-Z loads | brief 7.6 | C | T-11 |
| R-18 | Bidirectional TRIG on the panel SMA | 5 V TTL into high-Z; DIR = GPIO39; ≈2.4 V into 50 Ω documented | brief 7.6; DS LVC1T45 | C + P (D-09) | T-12 |
| R-19 | TCXO option footprint, DNP | 10 MHz path to GPIO44 with a Schmitt buffer (now SN74LVC1G17DBVR C7836, SOT-23-5), zero cost unpopulated; **v0.7** the NMR clocks come from the Si5351A instead (D-33), so this stays an option | brief 7.6; parts-verified R2.2 | P (D-13, D-49) | VIS |
| R-20 | **v0.7 — superseded.** The OPT conditioning chain is deleted; COND_OUT1/COND_OUT2 now carry the NMR receiver I and Q baseband | COND_OUT1/2 reach ADC channels 7/8 only through JP101/JP102 (default: mixer; the jumpers restore AI7/AI8 from the panel SMA) | re-spec 3.2 (D-32) | C | ERC, VIS, T-20 |
| R-21 | Front-panel link pinout | 2×20, exactly brief 7.8 | brief 7.8 | C | ERC netlist audit of J6 |
| R-22 | **v0.7** Front panel 180 × 65 mm, 2-layer: **15 SMA in a 3 × 5 grid** at 20 mm pitch (row 3 column 5 = SPARE, centre pin to TP1 only), OLED 1×4 socket (now J17), 3 LEDs, 2×20 female on the back, 4×M3 | geometry per `gen_panel.py`: columns x 50/70/90/110/130, panel rows y 54/34/14; link pins 37–40 = RX/AGND/TX/AGND | re-spec 8.1 (D-45, D-46) | C | DRC, VIS, `gen_panel.py` mating audit |
| R-23 | **v0.7** Main board **180 × 100 mm**, 4 layers, 4×M3 at (4,4) (176,4) (4,96) (176,96), front-edge link, rear-edge terminals/USB/jack plus three new terminals on the rear-right strip | outline and holes as drawn; **three** owner areas ZONE_A/B/C plus ZONE_BASE, not five zones | re-spec 8.1 (D-30, D-31) | C | DRC (owner_A/B/C), VIS |
| R-24 | Stack-up L1 sig/pwr, L2 GND, L3 GND, L4 sig/pwr | no tracks on inner layers; only the ISO_IN void interrupts them | user 2026-09-07 | C (D-01) | DRC rule, VIS |
| R-25 | Design rules: clearance 0.2 mm (0.3 analog in, 2.5 iso, **5.0 mains**), track 0.25 (0.5 power, 1.0 +5V_RAW, **3.0 mains**), via 0.6/0.3 (**no via on mains**), copper-edge 0.3 (**2.0 mains**) | JLC 4-layer capability (min 0.09 mm trace/space, 0.15 drill) exceeded with margin | brief 8.1; JLC capability page (Konnect fab constraints) | C | DRC |
| R-26 | JLC Economic PCBA, SMD + THT, top side only; DNP excluded | BOM/CPL only populated parts; every part has an LCSC number and stock; **v0.7** 97 distinct LCSC lines (v0.6: 44), ≈ 22 of them new, and Basic/Preferred/Extended must still be read by hand in the JLC BOM tool before ordering | brief 3/10; `bom/v07-new-parts-purchase-2026-09-13.md` | C + **A** (library type) | release BOM/CPL reconciliation, JLC BOM tool |
| R-27 | Quantities: 5 assembled + 2 bare main, 6 assembled panels | order note in the release README | brief 3 | C | n/a |
| R-28 | Student gapped copies, **one per section A/B/C** (three, not five) | each copy opens; ERC lists exactly the intended unconnected pins | brief 12 + re-spec 4 (D-30) | C | ERC on student sheets |
| R-29 | Analog copper separation from switching sources | no DC-DC module, relay or fast digital trace inside the analog zones; measured module-to-ADC distance ≥ 15 mm | brief 7.2, practices 8/11 | C | VIS (rendered layout), distance table in design-review |
| R-30 | Track geometry | only 0/45/90° segments (audit_angles.py); corner quality reviewed | prompt 3 | C | tools/pcb/audit_angles.py |
| R-31 | Fast nets (SPI, CS, FAST_OUT, TRIG) < 60 mm, GND-adjacent | lengths listed in the release report | brief 4.3 | C | length report from the PCB generator |
| R-32 | USB D+/D− from USB-C to GPIO19/20 short (< 30 mm) with GND adjacent | full speed; no stubs | brief 7.1 | C | length report |
| R-33 | 1×4 OLED socket LCSC number | verified JLC part or hand-soldered generic header | brief 13 | C | XFCN PZ254-1-04-Z-8.5, LCSC C2894927 (2.54 mm 1×4 female, 8.5 mm) in the library and the panel BOM; stock to be re-checked at order time |
| R-34 | **NMR transmit level and 90° pulse** | with JP801/R808 = 270 Ω (G = 25.0) the OPA564 delivers 15.9 V pp from an 18 V +VEXT = ±7.95 V into the 1419 Ω design coil = 5.6 mA → B1 = 28.2 µT → t90 = π/(γB1) = **417 µs** (within 1.5 % of the 411 µs measured on the TeachSpin apparatus at 10 V); TX_EN low except during a pulse | circuits doc 0 and 2.3; DS OPA564 SBOS372E | P (D-35) | DS calc, T-16, T-17 |
| R-35 | **Receiver gain and noise** | LNA gain 101 × 10 = 1000 (± the 1 % of D-49); total input-referred noise 15.6 nV/√Hz against a 14.2 kΩ tank = **NF 0.15 dB**; 40 µV pk of coil signal → 1.02 V pk at the ADC (conversion gain 25.5) = 6540 LSB; single-shot SNR ≈ 15 in 15 kHz, ≈ 500 after filtering to the linewidth | circuits doc 3.2 and 4.3; DS OPA1656 | P (D-36) | DS calc, T-18, T-20 |
| R-36 | **Receiver blanking and dead time** | RX_BLANK = 0, or un-driven, leaves the receiver blanked; total dead time ≤ 1 ms = coil ring-down 0.25 ms + amplifier recovery 0.5 µs + AC-coupling recovery 0.30 ms (1.59 kHz corner) + charge-injection settling 0.70 ms, i.e. ≤ 1.3 % of T2* = 75 ms | circuits doc 3.3; DS DG419 | P (D-37, D-39) | DS calc, T-19 |
| R-37 | **Quadrature local oscillator** | LO_I and LO_Q at f_LO = CLK1/4, 50 % duty, 90° apart **by construction** at any frequency (2-bit Johnson counter); /CLR pulsed after every PLLB change so the counter always starts in state 00; measured phase error ≤ 2° | circuits doc 1.4; Si5351 AN619 §6 | P (D-33) | DS calc, T-15 |
| R-38 | **IF chain bandwidth and channel map** | passive pole 15.9 kHz (1.00 k / 10 nF) and active pole 14.2 kHz (20.0 k / 560 pF) ahead of the ADS8688 15 kHz filter; I → COND_OUT1 → JP101 → channel 7, Q → COND_OUT2 → JP102 → channel 8, ±5.12 V range, 250 kS/s per channel; difference-amp CMRR ≥ 54 dB (0.1 % thin film) | circuits doc 4.2–4.4 | P (D-32, D-38) | DS calc, T-20 |
| R-39 | **Mixer logic-level compatibility** | TS5A23157 V_IH = 0.7·V+; at V+ = +3V3A that is 2.31 V against a 3.3 V CMOS LO (1.0 V of margin).  The mixer and the flip-flop must never be moved to +5VA | DS TS5A23157 | P (D-38) | DS, T-20 |
| R-40 | **H-bridge current limit** | I_TRIP = 64/R_ILIM(kΩ): R920 = 32.0 kΩ 1 % → 2.0 A (17.8 k → 3.6 A); ILIM never open and R_ILIM ≥ 15 kΩ; IN1/IN2 pulled down = coast at reset; the VM clamp fires below the 45 V device maximum (SMBJ26A, ~42 V) | DS DRV8871 §7.3.3; parts-verified R2.5 | P (D-42) | DS calc, T-21 |
| R-41 | **Polarizer switch current and voltage limits** | AOD4184A 40 V / 13 A, 7 mΩ at V_GS ≥ 10 V; peak drain voltage = +VCOIL + V_flyback < 40 V → **+VCOIL ≤ 24 V with the external RC snubber, ≤ 12 V with the SMBJ20A**; the fitted SS54 freewheel gives τ = L/R = 2.6 ms (adiabatic).  A sudden turn-off (τ ≲ 50 µs, needing 241 V) is out of reach on a 40 V FET — designed-in limit | circuits doc 6 and 6.1; DS AOD4184A, SS54 | P (D-43) | DS calc, T-22 |
| R-42 | **External power input range and protection** | J901 accepts 7–18 V DC (silkscreen), 24 V only with U802 unfitted; 5 A fuse, SMBJ26A clamp (26 V standoff), reverse polarity blocked by an AOD4185 P-FET (0.375 W at 5 A) whose V_GS is clamped to 12 V; loads are the OPA564 V+, the DRV8871 VM and the UCC27517 VDD only | circuits doc 7; parts-verified Group 7 | P (D-41) | DS calc, T-14 |
| R-43 | **Supply sequencing** | VDIG (+3V3, from USB) is applied **before** V+ (+VEXT, bench supply); the reverse order is marked "not allowed" in the OPA564 datasheet.  Board and documentation must say "USB first, then the bench supply" | DS OPA564 SBOS372E Fig. 36 | P (D-35) | DS, T-23; **the silkscreen note at J901 is still missing (F-16)** |
| R-44 | **DIO and relays through the I²C expander** | TCA9535 at 0x20: P0.0–P0.7 → DIO1–8 (74AHCT541), P1.0–P1.3 → RLY_IN1–4 (AO3400A gates), P1.4–P1.7 spare on TP501–TP504; every relay stays off while the expander ports are still inputs (10 k gate pull-downs); ~100 µs update, not timing-critical | re-spec 8.1/8.2; DS TCA9535 | P (D-40) | ERC, T-10, T-11 |
| R-45 | **v0.7d** Module header: 7 buffered 5 V TTL outputs for a bought relay / H-bridge module | TCA9535 `P1.0–P1.3` + `P1.5–P1.7` = MODULE OUT 1…7 → link J8 pins 19…31 odd (GND on every adjacent even pin) → one 74AHCT541 on +5V_RAW on the panel, 47 Ω in series → 2×6 shrouded box header (1,2 = +5 V; 3…10 = OUT 1…8; 11,12 = GND).  V_OH ≥ 3.8 V into a 5 mA opto input; OUT 8 is a reserved spare (J8 pin 33 not connected on the main board); module coil current is **not** taken from +5V_RAW by design (the rail is fused at 1.5 A) | Decision #58 e/f (D-53) | P (D-53) | netlist audit of J8 19…33, **T-10** |
| R-46 | **v0.7d** MODULE OUT lines defined at power-up | Every `MOD1…MOD7` line sits at a **defined low** while the TCA9535 ports are still inputs (power-up, reset, I²C not configured) and while the link is unmated: **10 kΩ pull-down to GND at each 74AHCT541 input on the panel**.  **Not built today** — only MOD8 has one (R489) | D-57; TCA9535 ports are inputs at reset with no internal pull-up/pull-down | **Q → P** (D-57), open | panel schematic review (7 pull-downs); **T-10** (all outputs low with firmware idle and through a reset) |
| R-47 | **v0.7d** The two isolated inputs live on the front-panel board | Terminals J411/J412, the 1N4148W + 220 Ω + 2 × MMBT5551 current source (I_LED ≈ 6.8 mA over 5–24 V) and the 6N137S with its 1 kΩ pull-up are all on the panel; `OPTO_IN1/2` reach GPIO16/17 over J8 pins 35/37, active LOW; `ISO_IN` class, 2.5 mm clearance on every layer and no foreign copper under either isolated group, enforced by `front-panel.kicad_dru` and the two `ISO*_KEEPOUT` areas | Decision #58 g (D-54, D-08 unchanged) | P (D-54) | panel DRC (`iso_in_clearance`), `gen_panel.py` mating audit, **T-12** on the panel |

## Requirements the build cannot verify without hardware

**Status of the whole register: nothing here is hardware-verified.**  No main board has been built, and the main board
is not routed, so even the DRC-based verifications hold only for the placement, the zones and the owner rules.

R-02 (socket spacing) needs a physical #40729 and a caliper.  R-04…R-18 and R-34…R-44 are verified by calculation and
datasheet only; the bring-up plan (`bring-up.md`, T-00…T-23) turns each into a measurement.  No SIM-firmware and no
other board result is used as evidence for this design.  Open items carried into v0.7:

- **R-02 / D-12** dev-board socket row spacing 25.4 mm, assumed, never measured.
- **R-26 / D-49** JLC library type (Basic/Preferred/Extended) unread for most of the ≈ 22 new lines.
- **R-33** OLED socket stock to be re-checked at order time (the panel now uses the composite
  `class_board:OLED-0.96in-4P-module-socket`, Decision #56).
- **R-46 / D-57** the seven MODULE OUT pull-downs on the panel are a **requirement, not yet built** — the single
  highest-priority open item of the v0.7d change.
- **D-25** panel header mating height.
- IC land patterns still unchecked against datasheets — for the v0.6 ICs and for every new v0.7 package
  (HSOP-20 PowerPAD, SO-8-EP, TSSOP-24, MSOP-10, SOIC-14, TO-252, SMB): `design-review.md` F-12.
- CPL rotations never checked in the JLC upload preview: F-13.
