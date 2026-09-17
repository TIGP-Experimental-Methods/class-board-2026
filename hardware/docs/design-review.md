# Class board — board-specific design review and verification plan (rev B, v0.7)

This applies `MIXED_SIGNAL_PCB_DESIGN_PRACTICES.md` (binding) to the actual class-board circuitry.  It is written before
placement and routing and maintained through the build.  Each item: the failure it prevents, how it applies here, and
how compliance is verified.  Findings use the practices §21 severity scale and live in §8 of this file.
Sources: brief v0.6 **plus the v0.7 re-spec** (`notes/2026-09-13-nmr-respec-proposal.md`) and the NMR circuit design
(`notes/2026-09-13-v07-nmr-circuits.md`), `requirements.md`, `design-decisions.md`, downloaded datasheets, JLCPCB
4-layer capability (Konnect fab constraints: 4-layer JLC04161H-7628, min trace/space 0.09 mm, min drill 0.15 mm, min
via annular 0.05 mm — we use 0.25/0.2, 0.3 drill, 0.15 ring).  **Routing is by hand (instructor + students in
Workshop 2) and has not started; §9 is therefore still empty.**

---

## 2026-09-17 update (v0.7d) — what this review no longer covers

The instructor's decision of 2026-09-17 (course repo `DECISIONS.md` **#58**; new entries **D-53…D-57** in
`design-decisions.md`) removed the relays and all mains switching, moved the isolated inputs to the front panel and
made the panel student section C.  **The sections below are not rewritten** — they are the record of the review as it
stood.  What they no longer describe:

- **§2 floorplan table, `ZONE_C` row** — that area is now **`ZONE_INSTR`** (power entry `b2_power` + the coil
  switches `c_switch`), its L-shape reaches x 96 on the rear edge, the **relay row and the isolated inputs are not in
  it**, and the instructor's block is placed as one piece at **x 45–86** with J901/J903/J905 at x 51.0 / 62.7 / 76.9
  (rot 180).  `ZONE_B` now also owns the rear-right strip **x 96–179.5, y 0.5–36**.  (D-56)
- **§2 energy map** — the relay coils are no longer a switched-current source on this board (286 mA of +5V_RAW
  returned to the budget).
- **§5.3 B4 — relays (mains-capable)** — **void in full** with D-51: no relay, no `MAINS*` class, no `mains_*` rule,
  no 250 V AC silkscreen rating.  (D-53)
- **§5.4 B4 — isolated inputs** — **valid but relocated**: the analysis holds unchanged, on the **front-panel**
  project, whose `front-panel.kicad_dru` and two `ISO*_KEEPOUT` areas now carry the 2.5 mm rule.  (D-54)
- **§6 routing concept, item 7 "Relay drive/contact"** — void; the corresponding traffic is now seven 3.3 V logic
  lines from the expander to link J8 pins 19…31 odd.
- **§7 manufacturing, through-hole content** — the four KF301-5.0-3P relay terminals and the two 2P isolated-input
  terminals are off the main board; the panel gains a 2×6 shrouded box header and the two 2P terminals.  The panel
  itself is now **4-layer**, 180 × 100 mm, single-sided for assembly except the three link headers.
- **§8 findings: F-21** (relay channels vs mains) — **closed by removal**, not by design.  **F-22** (+VEXT TVS vs
  relay 1) — **void**: relay 1 no longer exists and the pocket it constrained is gone.  **F-02** (relay coils vs
  Darlington drive) — void.  **F-17**'s footprint count is now **341**.
- **New finding F-23** (below) replaces the safety property the relay gate pull-downs used to provide.

## 1. Board, coordinate system and stack-up

- Main board **180 × 100 mm** (v0.7, D-31: the 140 mm outline had 5.2 mm of free rear edge and 5.1 mm of free right
  edge, against the 10.2 mm a KF301-5.0-2P needs for the three new terminals).  Origin front-left; in the PCB file x
  runs right and y runs from the REAR edge (y = 0, terminals, USB-C, jack) to the FRONT edge (y = 100, 2×20 link to the
  panel).  Four M3 holes at (4, 4), (176, 4), (4, 96), (176, 96), 4 mm from the corners (no copper ring).  Everything
  that stood at x ≥ 129 on the 140 mm board moved +40 mm; nothing at x < 129 moved.
- JLC04161H-7628: L1 (F.Cu) signal + power, L2 (In1.Cu) GND, L3 (In2.Cu) GND, L4 (B.Cu) signal + power.  1.6 mm,
  1 oz outer / 0.5 oz inner, prepreg 7628 ≈ 0.2 mm between L1–L2 and L3–L4 (JLC stack table).  Every outer-layer trace
  has a solid GND reference 0.2 mm away; the only interruption of L2/L3 is the isolated-input void (§5.4).
- Failure prevented: reference-plane crossings (practices §4, §5) — none can occur because no plane is split.
- Verify: DRC custom rule forbids tracks/vias-only-copper on In1/In2; rendered inner-layer plots inspected.

## 2. Floorplan, energy map and sensitivity map (v0.7: three sections on 180 × 100 mm)

Energy sources: the two DC-DC modules (100 kHz push-pull, isolation transformers), the relay coils (40 mA switched,
flyback), the dev board (WiFi bursts ~400 mA on +5V_RAW, USB), the 5 V logic buffers, the USB-C/jack entry
(ESD/surge), and — new in v0.7 — the **OPA564 transmit stage** (up to 1 A of coil current, 15.9 V pp at 89 kHz),
the **DRV8871 H-bridge** (to 3.6 A, PWM edges), the **polarizer MOSFET** (to 13 A, switched in ~8 ns at the gate and
dumped through a 2.6 ms freewheel), and the **square local oscillator** (LO_I, LO_Q and CLK1 = 4·f_LO, 3.3 V CMOS
edges).  Sensitive nodes: the **tuned tank and the LNA input (40 µV pk on a 14.2 kΩ source)** — now the most sensitive
node on the board by two orders of magnitude — then the ADS8688 inputs AIN1..8 (1 kΩ / 1 nF), REFCAP/REFIO, the
mixer V_MID network and IF filters, the DAC VREF and VOUT, the op-amp inverting nodes, and the SMA link pins on the
front edge.  Chassis: none (bench instrument); cable shields (SMA) are AGND on the panel.

**Three owner areas, one per student, plus the base** (the rule areas `ZONE_*` in the board carry exactly these
polygons and the DRC rules `owner_A`, `owner_B`, `owner_C` assert that every footprint whose `Block` field maps to
that section lies inside its polygon — D-30, D-48):

| Zone | Polygon (mm) | Contents (final placement) | Why here |
|---|---|---|---|
| ZONE_C (section C: power, switching, coil switches) | L-shape (0.5, 0.5) (169, 0.5) (169, 36) (37.5, 36) (37.5, 57.5) (0.5, 57.5) | **old B2** x 0–38 / y 0–56: USB-C J201 (13, 5.6) and jack J202 (29.5, 12) on the rear edge, fuses/TVS/LM66100 below, PS201 (11, 31.5) and PS202 (11, 42.5), ±12 V filter/bleeder rows at y 31.5 / 42.5, LDO row at y 52.8. **old B4** x 38–128 / y 0–36: isolated inputs J411/J412 at x 42.7 / 54.0 with their keep-out 37.5–60 × 0–26.5, relays K401–K404 at x 68 / 85 / 102 / 119, y 15.5 with 3P terminals at y 4.2. **new 9xx strip** x 128.4–168.9 / y 0.5–36 (`sheet_c_switch.PLACEMENT`): three terminals on the rear edge — J901 +VEXT (134, 4.2), J903 H-bridge coil (145.7, 4.2), J905 polarizer (159.9, 4.2) — with column A behind J901 (F901, D931, Q901, C940/C941, D932/R940, LED), column B behind J903 (U903 DRV8871 at (146, 13), C920/R920/R921/R922, D920, C921 at (149, 27.5)), column C behind J905 (Q904 AOD4184A at (162, 12.5), U904 UCC27517 (158, 19), JP904, gate network, R933 in the source return, D930 SS54 freewheel, D934 DNP) | All the dirty current stays in one L along the rear and left edges; the three high-current terminals are on the 40 mm of rear edge that the 180 mm outline bought (D-31), 128 mm away from the LNA |
| ZONE_BASE (instructor) | (37.5, 36) (100, 36) (100, 57) (37.5, 57) | Sockets J2 (rear row, y 37.3) and J1 (front row, y 62.7), pin 1 at x 43.3, antenna end at the left; **U505 TCA9535 expander at (94.5, 46)** with C507 and TP501–TP504 (it serves B and C, so it is BASE-owned, D-40); J5 2×10 expansion header at (154, 52) after the +40 shift; Qwiic J3/J4 on the left edge; JP1/JP2, TP1–TP4, R1–R4, NT1 star at (99.2, 67.5) | The dev board sits centrally so both socket rows reach every section; the expander fits in the socket well, the only free pocket left |
| ZONE_A (section A: inputs + NMR receiver) | (0.5, 57.5) (45, 57.5) (45, 57) (100, 57) (100, 99.5) (0.5, 99.5) | **old B1**: eight input networks in a row above the link AI pins (R at y 90.5, C at 87.6, BAV99 at 84.2, columns x 48.2 + 4.8k), ADS8688 U101 (65, 76, rot 270), reference/AVDD/DVDD caps, JP101/JP102 at x 97.5. **new 7xx/9xx receiver** (`sheet_nmr_rx.PLACEMENT`, 93 parts, bbox x 1.9–98.4 / y 59.4–96.6): the **B1 pocket** x 84.5–99.5 takes the front end — crossed diodes D703/D704 and the tank C710–C712 in the row at y 83.5, nearest the link pins 37/39, then R710/R711/JP702 at y 78.7 and U703 OPA1656 + its gain network at y 73.5; the **former OPT area** (x 1–41) takes the rest — band C at y 73.6 the Si5351 U701 (9.19, 73.6) and crystal Y701, band I at y 82.0 the Johnson divider U702, the blanking switch U704, the op-amps U705/U706 and the mixer switches U901/U902, with passive bands at y 59.4–75.3 (clock/rail) and y 89–96.6 (the whole mixer/IF network) | The 40 µV front end is as close to its SMA as the link geometry allows and as far from the clocks as the zone allows (~75 mm); the LO chain and the mixer sit at the far left, behind the ADC, and the IF leaves through JP101/JP102 into ADC channels 7/8 with a few millimetres of trace |
| ZONE_B (section B: outputs, timing, NMR transmitter) | (100, 36) (169, 36) (169, 0.5) (179.5, 0.5) (179.5, 99.5) (100, 99.5) | **old B5**: 74AHCT541 U501 (108, 41.2) + R501–R508, 74HCT125 U502 (105.4, 61), LVC1T45 U503 (114, 61.2), the TCXO option, and the seven 2P terminals now on the right edge at **x 175** (J506, J507, J501–J505). **old B3**: 74HCT125 U302 (105.6, 72.5), DAC8563 U301 (114, 74.8), OPA2192 U303 (114, 83), gain networks and the 49.9 Ω + BAV99 outputs. **new 8xx transmitter** (`sheet_nmr_tx.PLACEMENT`, 46 parts, bbox x 131.7–167.3 / y 38.2–95.1): left column x 129.8–150 — AD9834 U801 (134.01, 41.24), its decoupling, the 200 Ω loads, the reconstruction filter (C808 / L801 / C809), the mid-rail bias, the gain leg and the DDS pull-downs; right column x 150.6–170.4 — OPA564 U802 (158, 62.2), its supplies, the output chain (R813, C818, D801/D802, the snubber, the −20 dB pad) ending at the TX terminal **J802 on the FRONT edge at (166.5, 95.1)** | The 20 mm the board grew plus the old right-hand block give the transmitter a column of its own; the power stage sits directly above its terminal so the coil loop is short, and the DDS is 25 mm from the SPI pins.  J802 could not go on the right edge: terminal J505 reaches y 87.2 and the mounting hole H4 takes the corner, leaving 5.1 mm where 11.2 mm is needed |
| front edge | link J6 at (70, 94.5), rot 0 | 2×20 right-angle male: pads at y 93.23 (even) / 95.77 (odd), body 97.3–99.8 flush with the edge; **pin 1 at the LEFT end** (x 45.87).  v0.7: pins 37–40 = RX / AGND / TX / AGND (D-45) | The only orientation with the mating face at the edge (D-20) |

Mechanical: 4 × M3 at (4, 4), (176, 4), (4, 96), (176, 96); fiducials at (22, 4), (126.5, 47), (12, 60).  Courtyards are
body + pads + 0.25 mm (D-27); `place_check.py` and the DRC courtyard check run on the placement before routing.

Link-orientation trade (2026-09-08, unchanged in v0.7): with pin 1 at the left the eight AI pins sit at x 56–74, so B1
is centre-front and B3 right-front (D-20).  AI1..AI8 are 5–8 mm long, SPI to the ADC ≈ 15 mm; AO1/AO2 pay with a
≈ 60 mm run along the front lane over the AGND pour.  Channel order follows the geometry (D-19): AI1→AIN_6,
AI2→AIN_7, AI3→AIN_0, AI4→AIN_1, AI5→AIN_2, AI6→AIN_3, AI7→AIN_4, AI8→AIN_5 — and in v0.7 **AIN_4/AIN_5 (channels 7
and 8) carry the mixer I/Q by default**, with JP101/JP102 restoring the panel SMA per channel (D-32).

Section balance (netlist, 404 components): A = 131 parts, B = 111, C = 138, base 24.  C is the largest in count but
the simplest in kind (repeated bleeders, LED resistors, opto limiters); A carries the hardest analog work.

## 3. Grounding and return paths (practices §4)

- One solid GND on L2 and L3.  AGND is a named outer-layer copper region (L1 and L4 pours) covering ZONE_B1, ZONE_B3,
  ZONE_OPT and the front-edge link area, joined to GND at NT1 (net tie, 2 mm pads) at (97, 60), the B1/BASE boundary.
- Return-current reasoning: analog signals (AI, AO, VREF) travel on L1 over the L2 GND plane; their HF return is in the
  plane directly under the trace, their DC return is the AGND copper → NT1.  Digital/power currents (dev board 0.5 A,
  relays, USB) flow in the plane between the rear zones and the socket; they never pass under the analog zones because no
  digital component or trace is placed there (checked in §6).  The 1 A rail current returns from the socket GND pins
  (x ≈ 43/97, y 37/63) to the LM66100/USB-C GND at the rear-left: the plane current density stays in the rear-left
  quadrant; the analog zones are ≥ 20 mm from that path.
- Panel: its copper is AGND; SMA shields are AGND; GND reaches the panel only for I2C/LED/+3V3/+5V_RAW returns, so no
  loop AGND–GND is formed outside NT1.
- **v0.7 additions.**  The AGND pour grows along the new right-hand front strip (polygon corner (179.5, 87.5) →
  (179.5, 99.5)) so the transmitter output area and the front edge stay on analog copper.  Three further rules come
  from the circuit design §8: (i) the whole receiver — tank, limiter, LNA, blanking switch, mixer switches, the
  V_MID network, the IF filters **and the 74HC74 divider** — sits on AGND and runs from +3V3A/±12 V, so the
  commutation instants share the signal ground; (ii) the Si5351, the TCA9535, the DRV8871 return, the polarizer
  source and the **OPA564 V− (its PowerPAD) and coil return** are on GND; (iii) exactly one line crosses the
  boundary in each direction — CLK1 into the divider (damped by R704/C706, τ = 4.7 ns) and C810 into the power
  stage.  AGND and GND still meet only at NT1 (99.2, 67.5).
- Failure prevented: shared-impedance error (a 1 A return dropping mV across the analog reference) and split-plane
  crossings.  Verify: ERC (AGND and GND are separate nets, one tie), DRC (net-tie exception only), inner-layer plots.

## 4. Power integrity and decoupling (practices §7)

| Rail | Source / filter | Local decoupling (loop served) | Check |
|---|---|---|---|
| +5V_RAW | LM66100 ×2 → 22 µF + 100 nF at the OR node; 1.0 mm traces from the connectors to the LDO/modules and to the socket 5V pin (J1-21) | dev board has its own; 100 nF at each 5 V logic IC (74AHCT541, 74HCT125 ×2, LVC1T45 VCCB) within 2 mm of the VCC pin, GND via next to the pad | width 1.0 mm / 1 oz → 0.5 mΩ/mm: 60 mm ≈ 30 mΩ → 36 mV at 1.2 A (T-02) |
| +3V3 | AMS1117, 10 µF in / 22 µF + 100 nF out | 100 nF at 6N137 ×2, LVC1T45 VCCA, ADC DVDD (10 µF + 100 nF) | load ≤ 150 mA est. |
| ±12 V | module → FB 600 Ω → 22 µF + 100 nF; 3 × 2.2 k bleeders | OPA2192 100 nF + 10 µF per rail at the pins; clamps | light-load rise ≤ +15 % (13.8 V) with the 16 mA bleeder (D-04) |
| +5VA | 78L05 (from +12 V) 1 µF in / 10 µF + 100 nF out | ADS8688 1 µF at pins 9 and 30 + 10 µF; DAC8563 100 nF + 10 µF; **DG419 VL (v0.7, D-37)** | 78L05 PSRR + FB isolates 100 kHz module ripple (80 mVp-p max → < 1 mV at AVDD) |
| **+3V3A** (v0.7) | FB901 ferrite from +3V3, 10 µF + 100 nF | 74HC74 divider, both TS5A23157 mixer packages (100 nF each at the pin), the V_MID divider | the mixer must stay at 3.3 V: V_IH = 0.7·V+ (D-38).  Ferrite keeps the LO edges out of the digital rail |
| **+3V3D** (v0.7) | FB801 ferrite from +3V3 | AD9834 AVDD/DVDD (100 nF each) + 10 µF bulk; AGND and DGND tied at the device | a DDS clocked at 50 MHz must not share the MCU rail |
| **+VEXT** (v0.7) | external 7–18 V → 5 A fuse → SMBJ26A → AOD4185 P-FET; 100 µF + 100 nF at the node | OPA564 V+ 47 µF + 100 nF at the pin through its own ferrite; DRV8871 VM 100 µF + 100 nF; UCC27517 VDD 1 µF + 100 nF | sized for 1.5 A (TX) + 3.6 A (bridge) + gate charge; the bulk, not the TVS, absorbs coil pumping (§5.7 item 6) |
| VREF (ADC) | internal 4.096 V | REFCAP 1 µF + 22 µF, REFIO 10 µF placed at pins 5–7 with no vias between pin and capacitor (datasheet 11.1) | VIS |
| VREF_DAC | internal 2.5 V | 1 µF at pin 10; 2 × 10 k load | VIS |

Failure prevented: decoupling capacitor close in XY but with a long loop (practices §20).  Placement rule used: each
100 nF/1 µF between its supply pin and a GND/AGND via on the same side, loop ≤ 4 mm; bulk capacitors within 10 mm.

## 5. Block-specific risks

### 5.1 B1 — ADC inputs, reference, settling
- Source impedance seen by the ADC: 1 kΩ + 1 nF filter.  ADS8688 has an internal 1 MΩ programmable-gain front end (not a
  bare sampling capacitor), so the kickback settling constraint of a naked SAR does not apply; the RC gives f-3dB = 159 kHz.
  Channel-to-channel crosstalk is set by the device (−100 dB typ) and by keeping the eight nodes ≥ 1 mm apart with AGND
  copper between them.
- BAV99 leakage: < 50 nA at 25 °C into 1 kΩ → 50 µV (0.16 LSB of ±10.24 V / 65536 = 312 µV).  Clamps to ±12 V (±13.8 V
  light load): the ADC abs max is ±20 V → margin.  A +50 V fault gives 36 mA through the 1 kΩ (0603 100 mW: 1.3 W —
  the resistor is the fuse; documented as a limitation).
- Layout: networks in a row along the front side of B1, node (R–C–D junction) short, AIN traces on L1 only over AGND/GND,
  no via; the ADC's digital pins (38..33) face the socket (rear/left), analog pins face the front; DVDD/GND decoupling
  on the digital side.  SPI enters from the socket side only.
- Verify: VIS (rendered close-up), length report, DRC ANALOG_IN clearance 0.3 mm, T-05.

### 5.2 B3 — DAC and output stage
- Difference amplifiers: R1/R2 (VREF side) and R3/R4 (DAC side) placed tight around the OPA2192, feedback R2 adjacent to
  the −IN pin; VREF_DAC routed from the DAC (≤ 20 mm) with 1 µF at the DAC pin.  Output 49.9 Ω + BAV99 then ≈ 50 mm on L1
  to the link (AO class 0.3 mm).  OPA2192 is stable into 1 nF; the coax adds ~100 pF/m — fine with the 49.9 Ω isolation.
- 74HCT125 shifter on +5V_RAW next to the DAC; its outputs (5 V logic edges) are kept ≥ 3 mm from VREF/VOUT copper.
- Verify: T-06 (DAC codes vs AO), T-07 (loop-back through AI).

### 5.3 B4 — relays (mains-capable, D-51)
- Coil loop: +5V_RAW → coil → MOSFET → GND; flyback diode across the coil (short loop); the coil current
  (71 mA switched per relay, 285 mA for four) returns in the plane at the rear.
- Contacts: COM/NO/NC to the 3P terminal on **3 mm tracks with 5 mm clearance to everything that is not the
  same channel** (MAINS / MAINS1…4 classes), **F.Cu only, no vias, 2 mm to the board edge**; board rating
  **250 V AC 5 A MAX per channel, load fused ≤ 5 A** on the silkscreen.  The terminal sits directly behind its
  own relay on the rear edge so the mains copper is as short as the placement allows; contact tracks never
  enter other zones.  The relay's own coil-to-contact spacing is the manufacturer's isolation (1.5 kV test)
  and is excluded from the rules.
- Gate pull-down keeps the relays off through boot; the ESP32-S3 GPIO4/6/7/15 have no strapping function.
- Verify: DRC `mains_*` rules; T-08 (including a meter check of the contact pin functions on a sample relay).

### 5.4 B4 — isolated inputs (safety, practices §15)
- Working voltage ≤ 24 V DC, functional isolation only (not mains): the brief's 2.5 mm clearance on all layers is far
  above IPC-2221 for 24 V (0.1 mm internal / 0.6 mm external uncoated for ≤ 50 V) — deliberately conservative.
- Implementation: nets ISOn_IN+, ISOn_IN−, ISOn_NODE, ISOn_C, ISOn_B, ISOn_E, ISOn_LEDA are in the ISO_IN class (2.5 mm);
  a keep-out rule area over the isolated group removes L1/L4 pours and cuts a void in L2/L3 (the only plane void);
  no via of another net inside it; the 6N137 body spans the barrier (its 10 mm lead spacing package gives > 2.5 mm).
- Verify: DRC (clearance class + rule area), rendered inner layers, T-10.

### 5.5 B5 — logic outputs and TRIG
- Series 1 kΩ on TTL outputs and 49.9 Ω on the fast outputs at the driver; terminals on the right edge; GND on every
  terminal pair (J505, J506/J507) so cables have a return.  TRIG_5V 33 Ω at the LVC1T45, BAV99 clamp at the driver
  (the SMA is on the panel; the link pin is the board entry — accepted stub of the panel trace).
- Verify: T-11, T-12; FAST-class length report (< 60 mm target).

### 5.6 B2 — entry and conversion
- Connector → fuse → TVS → LM66100 in that order along the trace (protection before the protected device, TVS return via
  two GND vias next to its pad).  USB-C shell pads to GND.  Modules: input FB + 10 µF at pins 1/2; outputs FB + 22 µF + 100
  nF at pins 4/6 before the rail leaves the zone; the module bodies (10 mm tall) are the tallest parts after the relays.
- Thermal: 78L05 0.12 W (SOT-89 tab on ≥ 50 mm² copper), AMS1117 ≤ 0.3 W (tab pad + copper), modules 2 W class at
  ≤ 25 % load, LM66100 ≤ 0.2 W each — no part above 0.3 W; no precision part within 15 mm of the LDOs.

### 5.7 NMR console — block-specific risks (v0.7)

The receiver amplifies 40 µV by 1000 within 100 mm of a 1 A transmitter, a 13 A switch and a square-wave
oscillator.  Six mechanisms, each with the mitigation that is already in the design and the part of the hand layout
that must not be got wrong (circuit design §8; D-33, D-35…D-39, D-41…D-43):

| # | Mechanism | Why it bites here | Mitigation in the design | What the layout must do | Verify |
|---|---|---|---|---|---|
| 1 | **LO edges coupling into the LNA** | LO_I, LO_Q and CLK1 are 3.3 V CMOS squares at 84–336 kHz with nanosecond edges; their *fundamental* mixes to DC and is harmless, but the edges radiate broadband into a 14.2 kΩ node | LO chain damped at the source (R704 100 Ω + C706 47 pF, τ = 4.7 ns; R703/R705 33 Ω); divider and switches on +3V3A/AGND; placement keeps the clocks at x < 17 and the tank at x > 84 (≈ 75 mm apart) | LO_I, LO_Q and CLK1 stay **≥ 5 mm** from the RX SMA, the tank pads, R710 and the U703 + input, and run on an inner-referenced outer-layer path with GND plane between them and the LNA; no LO track under the tank | T-18 noise floor, T-20 DC offset |
| 2 | **Transmit return current** | Up to 1 A (and 13 A at the polarizer) must return to J802 / J905; if any of it shares copper with the receiver pour it appears as a differential signal in front of a gain of 1000 | TX out and TX return both on GND, terminal on the front edge directly under the power stage; receiver entirely on AGND; single tie at NT1 | TX and its return routed as a **close pair, loop area < 1 cm²**; the coil return never touches the AGND pour; polarizer pair likewise, ≥ 2 mm wide | T-17, T-22 |
| 3 | **Coupling-capacitor recovery** | After transmit leakage saturates the LNA, an innocent 1 µF / 100 k interstage coupling (1.6 Hz) takes 300 ms to recover — four T2* periods, and the classic reason a first NMR build shows nothing | Interstage corner deliberately at **1.59 kHz** (C720 10 nF / R721 10 k): 0.3 ms recovery for 0.016 % of amplitude and 1.0° of phase at 89.4 kHz (D-39) | Do not "improve" the corner by enlarging C720; keep C720/R721 adjacent to the switch | T-19 |
| 4 | **Switch charge injection** | The DG419 injects ~60 pC.  On the 1.25 nF tank that is a 48 mV kick ringing for 36 µs at full gain; the TS5A23157 injects 3 pC LO-synchronously, which is a DC offset after the mixer | Blanking placed **between the stages**, where 60 pC lands on 10 nF as 6 mV (τ = 100 µs); mixer differential with 0.1 % difference amps (CMRR 54 dB) so the LO-synchronous injection cancels (D-38, D-39) | The two IF paths must be **mirror images** (R914–R917 as matched pairs, placed symmetrically) or the cancellation is lost | T-19, T-20 |
| 5 | **PowerPAD thermal paths** | OPA564 (0.70 W quiescent, 4.1 W in the worst continuous case) and DRV8871 (3.6 A) have no other heat path than their exposed pads | OPA564 is the **pad-down DWP part** (C188648) with the pad at V− = GND (θ_JA 33 °C/W on a high-K board); duty cycle held to ≤ 1 % by TX_EN (D-35); DRV8871 datasheet §10.1 | OPA564 pad soldered onto the GND pour with a via array; DRV8871 pad with a **3 × 3 array of 0.3 mm vias on a 1.0 mm grid** to a bottom-layer GND pour; OUT traces ≥ 2 mm; no precision part within 15 mm | T-17 thermal, T-21 |
| 6 | **+VEXT pumping and clamping** | Coil energy returns to VM (½LI² = 1.8 mJ → a 1.2 V rise on 100 µF), and no TVS both passes 24 V and clamps below the OPA564 26 V maximum | C921 100 µF sized for the 25 µs t_OFF window; SMBJ26A on VM and on the input (clamps ~42 V, below the DRV8871 45 V); ferrite + 47 µF local at the OPA564 V+; **silkscreen limit +VEXT 7–18 V** (D-41, D-42) | Bulk capacitor within a few millimetres of the DRV8871 VM pin; the OPA564 branch fed through its own ferrite, not tapped off the H-bridge node | T-14, T-21 |

Two more properties worth stating because they constrain the layout rather than a component: **the tank node must have
no ground pour under it** (added capacitance detunes the resonance), and **the crossed-diode limiter D703/D704 with its
AGND return must sit within 5 mm of the J703/link pin-37 centre pin** — a limiter after a length of trace limits nothing.

## 6. Routing concept (practices §6, prompt §3)

**v0.7: the main board is routed by hand** — students route their own section in the KiCad GUI during Workshop 2 and
the instructor routes the base, the rails and SPI.  The description below is the v0.6 scripted router
(`scripts/router.py`), kept because the *rules* it encodes are the rules the hand layout must follow — corridors,
fan-out bands, layer discipline, the AGND pour strategy and the class widths.  Running the router now would
overwrite the hand-routed board (D-47).  Two v0.7 additions to the critical-net list: **the TX chain**
(OPA564 output → R813 → C818 → J802 and link pin 39) routed as a close pair with its GND return, ≥ 1 mm wide, loop
area < 1 cm²; and **the LO chain** (CLK1, LO_I, LO_Q) kept ≥ 5 mm from the tank, the limiter and the LNA input,
with a ground plane between them (§5.7).  The H-bridge and polarizer nets carry 2–13 A: ≥ 2 mm copper, straight
runs to their terminals, and never across the AGND pour.

Method: 0.125 mm raster per outer layer, A* with 8-neighbour moves and a via penalty, escape stubs for every fine-pitch
pad (exact pad-axis segment + ≤ 0.0625 mm 45° jog onto the grid), then two smoothing passes: (1) every run of moves
that uses only two adjacent directions is regrouped into one diagonal and one orthogonal segment; (2) every 90° corner
is chamfered with the longest 45° cut that stays clear.  All emitted segments are exactly 0/45/90° (audit_angles).
Order: ISO nets (inside the keep-out) → analog inputs → analog outputs → FAST (SPI, CS, TRIG, FAST_OUT) → +5V_RAW →
POWER → relay contacts → everything else, each class shortest-extent first; then AGND; then AGND pour bridging.

Critical nets and corridors:
1. **+5V_RAW** 1.0 mm (0.25 mm necks at fine-pitch pins): LM66100 outputs → bulk caps → socket J1-21, relay coils, 5 V
   logic, LDO/module inputs; F.Cu and B.Cu, vias 0.8/0.4 where the class calls for them (0.6/0.3 used by the router).
2. **AGND**: F.Cu + B.Cu pours over B1, OPT, the link area, B3 and the ±12 V output area of B2 (polygon AGND_POLY);
   solid pad connection.  Fine-pitch AGND pins (ADC, DAC) get a via to the B.Cu pour right at their escape stub; other
   AGND pads either sit in open pour or get a short track to the nearest open pour spot.  Pour fragments that carry
   AGND copper are bridged with 0.5 mm tracks/vias so the fill is one net.  GND and AGND meet only at NT1.
3. **SPI + CS** (FAST): J1-16..19 (x 81–89, y 63) → ADC (x 62–68, y 71–80) ≈ 15 mm and → 74HCT125 in B3 (104, 72)
   ≈ 20 mm; 0.25 mm, vias cost-penalised (150 cells) so they stay on F.Cu where possible.
4. **AIN networks and AO stage**: F.Cu only, no vias (the router falls back to B.Cu only if F.Cu is impossible and logs
   it); the AI lines from the link go straight up into the resistor row; network outputs fan into the ADC's analog pins
   without crossings (D-19).
5. **USB D+/D−**: J201 (x 13, y 6) → J2 pins 19/20 (x 89, y 37): ≈ 85 mm (finding F-04), 0.25 mm, no stubs.
6. **FAST_OUT / TRIG**: J1-11, J2-18 → 74HCT125 (105.5, 61); TRIG_IO/DIR J2-9/10 → LVC1T45 (114.5, 61.5);
   TRIG_5V → link pin 5 (x 51, y 95.8).
7. **Relay drive/contact**: local to B4; contacts **3.0 mm wide, 5 mm clearance** to every net that is not the
   same mains channel, F.Cu only, no vias, 2 mm to the edge (DRU `mains_*` rules; the relay's own pad-to-pad
   spacing is excluded).  Inside one channel the rule is 2 mm.
8. **ISO_IN**: local, inside the keep-out, 0.3 mm; 2.5 mm to every non-ISO item (DRU rule + router masks).
9. **DIO1..8, GPIO43/44, I2C**: socket pins → B5 / Qwiic / link on F.Cu or B.Cu (B.Cu cost ×1.05).
Layer discipline: L2/L3 are untouched GND planes (DRU `no_inner_tracks`); every SMD GND pad has its own via (81
vias), THT GND pads connect to the planes directly; outer GND pours have no pad connection (they hang on the vias).
Power-width minimum rules were removed from the DRU because a rule cannot exempt the 0.25 mm necks at fine-pitch pins
(D-23); the generator enforces the class widths everywhere else.

## 7. Manufacturing and assembly (practices §17)

- JLC Economic PCBA, top side only (all SMD and THT on F.Cu).  Three 1 mm fiducials on the top.  Courtyards: no overlap
  (DRC).  Silkscreen: reference designators 1.0 mm text outside pads; connector pin-1 marks; rating texts on relay
  terminals ("≤30 V DC 1 A"), jack ("5 V ⎓ centre +"), opto ("5–24 V isolated"), panel TRIG ("hi-Z load").
- Rotation convention: footprints are EasyEDA/JLC land patterns for the same LCSC numbers, so the CPL rotation is the
  KiCad rotation (documented in the release notes with the pin-1 rendering per IC).  JLC's online preview is the
  remaining manufacturer-side check the user must perform at upload — **still not done** (F-13).
- **v0.7 BOM scale.**  404 components on the main board (v0.6: 254), **97 distinct LCSC lines** (v0.6: 44).  About 22
  of the new lines are the NMR console's silicon and specials — AD9834, Si5351A + 25 MHz crystal, 74HC74, OPA564
  (C188648), OPA1656, 2 × OPA1612, DG419, 2 × TS5A23157, DRV8871 (C75864), AOD4184A, AOD4185, UCC27517, TCA9535,
  SN74LVC1G17 (C7836), SMBJ26A ×2, SMBJ20A, SS54 ×3, BZX84C12, the 5 A fuse, the 15 µH inductor — plus the new
  passive values (0.1 % thin film 1.00 k / 10.0 k / 20.0 k, 3.9 pF NP0, 32.0 k, 4.7 Ω 2512, 10 Ω 0805, electrolytics).
  The ADI/TI/Vishay parts are certainly **Extended** (≈ US$3 feeder fee each per order, material on a 7-board run);
  JLC's library-type column is JavaScript-rendered and **must be read by hand in the JLC BOM tool before ordering**
  (D-49).  Estimated order cost: v0.6 ≈ US$500 → ≈ US$720.
- **Through-hole content.**  17 screw terminals (v0.6: 15) — 4 × KF301-5.0-3P on the relays, 2 × 2P isolated inputs,
  7 × 2P on the right edge, and the four new ones: J802 (TX), J901 (+VEXT), J903 (H-bridge coil) and J905 (polarizer,
  3P) — plus the two 1×22 sockets, the 2×20 link, the 2×10 header, USB-C, the jack, the two DC-DC modules and the four
  relays.  **Pitch is 5.0 mm, not 5.08** (parts-verified Group 6); the KiCad `TerminalBlock_…_P5.08mm` family must not
  be used, and the error is cumulative on the 3P part.  THT content raises the JLC Economic-PCBA per-board fee.
- Two new package classes the library did not have before v0.7: **HSOP-20 with PowerPAD** (OPA564) and **SO-8-EP**
  (DRV8871), plus TSSOP-24, MSOP-10, SOIC-14, TO-252 and SMB/SMA bodies.  None of their land patterns has been checked
  against the datasheet drawing (F-12), and `fix_courtyards.py` must be run after any footprint import (D-27).

## 8. Findings log (Blocker / High / Medium / Low — practices §21)

| ID | Sev | Where | Mechanism | Fix / disposition | Verification |
|---|---|---|---|---|---|
| F-01 | High | +5V_RAW entry | Schottky ORing + polyfuse worst-case drop → dev-board 5 V pin ≈ 4.0 V | LM66100 ideal diodes (D-02) | T-02 |
| F-02 | High | Relay coils | Darlington saturation leaves the coil below the guaranteed pull-in at low supply | AO3400A drivers (D-03) | T-08 |
| F-03 | High | DAC8563 logic | V_IH 3.5 V not met by a 3.3 V MCU | 74HCT125 level shift (D-05) | T-06 |
| F-04 | Medium | USB_DP/USB_DN | ≈ 85 mm instead of the brief's < 30 mm target (socket geometry) | full-speed only; pair routed over GND, no stubs; accepted | T-04 |
| F-05 | Medium | ±12 V rails | unregulated modules rise at light load | 16 mA bleeders (D-04) | T-03 |
| F-06 | Medium | AMS1117 | ceramic output capacitor vs datasheet's tantalum | 22 µF X5R + 100 nF; 3216 tantalum drop-in if T-01 shows ringing | T-01 |
| F-07 | Low | LM66100 vs TVS | TVS clamps at 9.2 V during a 21 A surge, LM66100 abs max 6 V | accepted for a bench instrument; the polyfuse limits energy | — |
| F-08 | Low | Opto pass transistor | ≈125 mW at 24 V continuous in SOT-23 | MMBT5551 (300 mW), copper on the collector pad | T-10 |
| F-09 | Medium | Socket row spacing | 25.4 mm assumed for the clone | user measurement before order (D-12) | caliper |
| F-10 | Medium | TRIG into 50 Ω | ≈2.4 V, below TTL V_IH when terminated | documented; hi-Z trigger loads intended | T-12 |
| F-11 | **High** | Custom design rules | `rules/class-board.kicad_dru` is not where KiCad looks (`<project>.kicad_dru`), so the owner rules, the ISO_IN 2.5 mm band, the relay-contact clearance and `no_inner_tracks` never ran; every "DRC verifies" claim in this document was unsupported (state report §2) | **Fixed** (D-48): the identical file is now at the project root as `class-board.kicad_dru`, with the three v0.7 owner rules; `gen_pcb.py` writes the four `ZONE_*` rule areas into every board | `kicad-cli pcb drc --severity-all` names the rules; owner assertions pass |
| F-12 | **Medium** | IC land patterns | Brief D1 requires a visual land-pattern check for every IC; D-11 documents checks only for connectors/relay/module/jack/SMA/socket/USB-C.  The IC patterns are inherited easyeda2kicad output, and D-27 showed the import quality was poor enough that every courtyard had to be rewritten.  v0.7 adds seven package classes, including two exposed-pad ones | **Open.**  Check each new package (HSOP-20 PowerPAD, SO-8-EP, TSSOP-24, MSOP-10, SOIC-14, TO-252, SMB) against its datasheet drawing before the 28 Sep order; run `fix_courtyards.py` after every import | datasheet drawing vs footprint; `place_check.py` |
| F-13 | **Medium** | CPL rotations | Never checked in JLC's upload preview — there was not even a main-board CPL to check (state report §6.4).  The new fine-pitch and exposed-pad parts are the ones a rotation error destroys | **Open.**  Check every IC in the JLC preview at upload (TSSOP-20/24, MSOP-10, HSOP-20, SO-8-EP, SOT-23-5, TO-252, SMA/SMB) | JLC upload preview |
| F-14 | **Medium** | Generator reproducibility | `gen_sch.py` minted a fresh uuid4 for every object on every run: no reviewable diff, and any KiCad-side edit was lost on the next regeneration | **Fixed** (D-47): `sexp.uid()` is uuid5 over a fixed namespace and a per-run counter, `uid_for(key)` is uuid5 of a stable key.  The working rule that follows: regenerate the schematic freely, **never regenerate the PCB once hand routing has started** | run `gen_sch.py` twice and diff |
| F-15 | **Medium** | Tooling paths | `release.py` and `gen_panel.py` hard-coded another user's `kicad-cli` path, so neither ran on this machine | **Partly fixed**: `gen_panel.py` and `gen_student.py` now read `KICAD_CLI` from the environment with the standard install as the default.  **`scripts/release.py:24` still carries the foreign path** — the release package cannot be built until it is changed | run both scripts on a clean machine |
| F-16 | **Medium** | Silkscreen — external power | The OPA564 requires VDIG before V+ ("not allowed" the other way round) and +VEXT must stay ≤ 18 V with U802 fitted; `gen_pcb.py` prints the section labels but **not** these two notes at J901, nor "+VEXT ≤ 18 V when JP904 selects +VEXT" | **Open.**  Add the three texts to `gen_pcb.py` before the release (R-42, R-43, D-35, D-41, D-43) | VIS on the silkscreen plot; T-23 |
| F-17 | **Blocker for release** | Main board copper | The checked-in `class-board.kicad_pcb` has 404 footprints, the zones and the rule areas, and **0 track segments**.  The scripted router's best attempt (another machine, 4.5 h) still failed 41 nets | **By design in v0.7**: routing is the Workshop 2 exercise — students route their section in the KiCad GUI and the instructor routes the base, rails and SPI.  Nothing may be released until DRC is clean with zones refilled | DRC 0 errors, 0 unconnected |
| F-18 | **Low** | Silkscreen crowding | v0.6 had 98 `silk_overlap` + 28 `silk_over_copper` warnings: reference designators printed on neighbouring parts' pads | **Mitigated**: `place_reference_texts()` scores candidate positions against other footprints, pads, board texts and the edge and picks the cheapest.  Re-count after the next DRC run | DRC warning count |
| F-19 | **Medium** | B3 courtyards | C301 (111.3, 69.7) and C308 (109.4, 72.5) overlap — a DRC **error** — while `place_check.py` reports no collision, so the two checkers disagree (state report §6.9).  Both parts keep these coordinates in v0.7 | **Open.**  Re-space the pair in `gen_pcb.placement()` and make `place_check.py` agree with the KiCad courtyard check | DRC courtyard check; `place_check.py` |
| F-20 | **Low** | +VEXT absolute limit | No TVS both passes 24 V and clamps below the OPA564's 26 V absolute maximum (clamping ratios ~1.6×), so a 24 V input is outside what the protection can guarantee | **Accepted and documented**: silkscreen "+VEXT 7–18 V"; 24 V only with U802 unfitted.  At 18 V the 417 µs 90° pulse is unaffected (D-41) | T-14 |
| F-21 | **High** | Relay channels vs mains | A relay and a controller in a student's hands means a wall plug in a screw terminal sooner or later; v0.7 had a 3 A signal relay and 0.6 mm contact clearance with vias allowed — a mains net beside the inner GND planes | **Fixed** (D-51, user decision #50): 10 A relay (C9221), MAINS / MAINS1…4 net classes, 5 mm reinforced clearance, F.Cu only, no vias, 3 mm tracks, 2 mm to the edge, 250 V AC 5 A MAX per channel on the silkscreen.  The **layout** still has to be redone: the master PCB keeps the old 17 mm relay pitch and fails the new rules with 60 clearance errors until the row and the terminals are re-spaced | `kicad-cli pcb drc --severity-all` names the `mains_*` rules; DRC 0 errors before release |

Layout findings are appended during placement/routing (§9).

## 9. Layout review log

**2026-09-16 — placement reworked and regenerated (D-52, Decision #55).**  398 footprints, 0 tracks, 0 vias.
The three panel-link headers went on the bottom (J6/J7/J8 at the anchors `gen_panel.py` mated), the dev board moved
10.8 mm left and 4 mm forward to clear J7 and the relay COM pins, section B2 was re-floorplanned around the J6 band,
the four mains relays went into a row at 21.6 / 19.6 / 19.6 mm pitch with their 3P terminals directly behind them
and every rear-edge screw terminal rotated 180° (wire entry from the edge), and section C was split around the relay
row with J903 moved to the right edge.  `ZONE_C` grew to the board's right edge along the rear strip (`ZONE_B` lost
the empty 10 × 35 mm rear-right corner).  DRC: **0 errors**, 499 unconnected items, no courtyard and no
`pth_inside_courtyard` errors; `place_check.py` 0 collisions; the generator is deterministic (run twice, byte-identical).
Renders: `docs/board-top-v07b-placement.png`, `docs/board-bottom-v07b-headers.png`, `docs/board-zones-v07b.png`.
Routing has still **not** started.

| F-22 | **Medium** | +VEXT TVS vs relay 1 | D931 was 4.63 mm from relay 1's NC pin where `mains_to_other` asks 5.00 mm: the pocket between the isolated inputs and relay 1 is 12 mm wide, and the 5 mm MAINS envelope on one side plus the 2.5 mm ISO_IN band on the other left ~0.5 mm too little for the P-FET, the TVS and the bulk capacitor in one column | **Fixed** (D-52, second pass): the side strip beside the bulk capacitor was re-stacked — C940 1.9 mm left, D931 to (68.85, 29.0, rot 90) where the envelope opens out, R940/R941/C941 to the ends of the same strip.  DRC 0 errors | `kicad-cli pcb drc --severity-all --refill-zones` |
| F-23 | **High** | MODULE OUT 1…7 at power-up | Every TCA9535 port is an **input** at power-up and reset (no internal pull-up or pull-down), and the 10 kΩ relay-gate pull-downs that used to define those lines were deleted with the relays.  `MOD1…MOD7` now run unterminated from the expander across link J8 into the panel's 74AHCT541 inputs: the buffer output is indeterminate and can switch a connected relay / H-bridge module at power-up, on reset, and whenever the link is unmated | **Open — requirement, not yet built** (D-57): fit a **10 kΩ pull-down to GND on each of MOD1…MOD7 at the 74AHCT541 input on the panel**.  Checked 2026-09-17 in `scripts/gen_panel.py`: only **MOD8** has one (R489, because that link pin has no driver); MOD1…MOD7 have none | panel schematic review; **T-10** — every MODULE OUT pin low with the firmware not running, and low through a reset |

(the rest is still the placeholder — **routing has not started**.  In v0.7 the main board is routed **by hand**: students route
their own section in Workshop 2 and the instructor routes the base, the rails and SPI, so this log is filled in from
the finished hand layout, not from `router.py`.  It must record: distances module↔ADC and LO↔LNA, the TX/polarizer
return loop areas, corner quality, the via list, the pour fills and the final DRC result.)

**2026-09-17 — relays removed, isolated inputs moved to the panel, board re-placed (v0.7d, D-53…D-57,
Decision #58).**  **341 footprints**, 0 tracks, 0 vias.  The four relays, their terminals and drive parts and the
whole `b4_switching` sheet are gone, with the `MAINS*` classes and the `mains_*` / `inside_K40x` / `inside_J40x`
rules; the two isolated inputs went to the front-panel project with their ISO_IN rule and keep-outs; the seven free
TCA9535 ports became MODULE OUT 1…7 on link J8 pins 19…31 odd (pin 33 = the reserved OUT 8, not connected).  The
instructor's block (power entry + `c_switch`) is one piece at **x 45–86** on the rear edge — J901 (51.0), J903
(62.7), J905 (76.9), all rot 180 — inside the renamed **`ZONE_INSTR`**; `ZONE_B` took the rear-right strip
x 96–179.5, y 0.5–36.  Renders: `docs/board-top-v07d-placement.png`, `docs/board-bottom-v07d-headers.png`,
`docs/board-zones-v07d.png`.  Routing has still **not** started.  *(DRC/`place_check` results for this placement are
recorded by whoever regenerated the board — this entry documents the design change, not a checking run.)*
