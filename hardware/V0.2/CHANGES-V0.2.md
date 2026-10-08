# Class board 2026, revision V0.2: changes from the ordered design

V0.2 is a copy of the design ordered on 2026-10-05 (main board and front panel, class repository `hardware/`, commit 65d7fb1) with the design faults of 2026-10-08 fixed in the schematics and the PCBs. The ordered files in `hardware/` are unchanged; the symbol and footprint library stays shared at `hardware/lib/` (not modified). Fault numbers refer to the course repository's `notes/2026-10-08-class-board-design-faults.md`.

## Files

| Project | Files |
|---|---|
| Main board | `class-board_V0.2.kicad_pro`, `class-board_V0.2.kicad_sch`, `class-board_V0.2.kicad_pcb`, `class-board_V0.2.kicad_dru`, `sheets/<name>_V0.2.kicad_sch` (the eight sheets of the hierarchy), `fp-lib-table`, `sym-lib-table` |
| Front panel | `front-panel/front-panel_V0.2.kicad_pro`, `.kicad_sch`, `.kicad_pcb`, `.kicad_dru`, `fp-lib-table`, `sym-lib-table` |

`sheets/front_panel_link.kicad_sch` of the ordered design is not part of its hierarchy and was not copied.

## How the copy was made

1. Files copied; project renamed with Konnect `rename_project` (project, root schematic, PCB, local settings); sheet files renamed and the root sheet's `Sheetfile` entries, the project name in the sub-sheets' symbol instances and the title-block `rev` (now `V0.2`, also the `REV` text variable) adjusted once by script. UUIDs kept.
2. Library tables point at the shared library: `${KIPRJMOD}/../lib/...` (main board), `${KIPRJMOD}/../../lib/...` (panel). The project-relative 3D-model paths in both PCBs were re-pointed the same way with KiCad's `pcbnew` module.
3. Check before any design change: the exported netlists of the copies equal the originals' apart from the file names; ERC and DRC with schematic parity gave the same results as the originals (table at the end).

All later schematic edits were made with Konnect's tools (this session's MCP client did not pick up Konnect's dynamically loaded tool sets, so Konnect was driven through its own stdio MCP interface). The PCBs were updated with KiCad's own `pcbnew` Python module: KiCad's IPC server was reachable, but no PCB editor was open in it, so Konnect's live `update_pcb_from_schematic` could not be used (the same situation as in FACTS.md, 2026-10-06).

## Changes, main board

| # | Change | Reason | Parts |
|---|---|---|---|
| 1 | LM66100 U201 and U202: CE (pin 3) from GND to the device's own VOUT (+5V_RAW). Sheet note corrected. | Fault 1: with CE on GND the two 5 V inputs were paralleled with no reverse blocking. Datasheet SLVSEZ8A 8.3.2: CE = VOUT gives always-on reverse-current blocking; the two devices then diode-OR. | U201, U202 (PCB: short F.Cu link from pad 3 to pad 6 under each SC-70) |
| 2 | **D931 deleted** (not moved). D920, the same SMBJ26A, already sits on +VEXT next to the input after Q901 and is the rail clamp. J901 silkscreen "+VEXT 7-24V DC" and a "+" at pin 1 (the right-hand pin, VIN). | Fault 11: D931 sat ahead of the reverse-polarity FET Q901, so a reversed supply forward-biased it and opened F901. Fault 4: the course runs +VEXT at 24 V. | D931 removed; its two VIN_F stubs removed |
| 3 | +VEXT sense: R942 100 k from +VEXT, R943 10 k to GND, C942 100 nF across R943; tap = new net `VEXT_SENSE` on dev-board socket J1 pin 4 (GPIO4, ADC1). 2.2 V at 24 V. | Fault 12: no rail sensing. ADC2 is unusable with WiFi. | R942 (0603 100 k) at the +VEXT copper near J901/Q901; R943 (0603 10 k) and C942 (0603 100 nF) at J1 pin 4. The long trace therefore carries the 100 k-limited node and the filter capacitor sits at the ADC pin. |
| 4 | 10 k pull resistors: up to +3V3 on CS_DAC (3.3 V side of U302), CS_ADC, DDS_FSYNC; down to GND on TRIG_DIR, FAST_OUT1, FAST_OUT2. No pull-down on DDS_PSEL: the pin is gone (item 7). | Fault 5: the lines float from reset until the firmware runs; DAC start-up race. | R5 CS_DAC, R6 CS_ADC, R7 DDS_FSYNC (pull-ups); R8 TRIG_DIR, R9 FAST_OUT1, R10 FAST_OUT2 (pull-downs); all 0603 10 k on the base sheet. On the PCB R5, R7-R10 sit next to the socket pins, R6 next to U101 (ADS8688) where +3V3 is local. |
| 5 | OPA564 flags to the MCU: TX_IFLAG -> R821 1 k -> `TX_IFLAG_MCU` -> J1 pin 6 (GPIO6); TX_TFLAG -> R822 1 k -> `TX_TFLAG_MCU` -> J1 pin 7 (GPIO7). R811/R812 are now fitted 100 k pull-downs (were DNP 10 k pull-ups to +3V3). Stale note about TCA9535 P1.5/P1.6 removed. | Fault 6: the flags reached no GPIO. | R821, R822 (0603 1 k, new); R811, R812 (0603 100 k, re-placed symbols with the same references, new UUIDs). On the PCB the old R811/R812 pads were junctions of the +3V3 feed of U802 VDIG: R811/R812 were moved next to R821/R822 at J1, and the +3V3 feed was bridged where R811 pad 1 was. |
| 6 | Si5351 CLK2 -> R707 100 R -> new net `REF_CLK` -> J1 pin 8 (GPIO15). TP701 kept. R119 0 R (marked "DNP-0", see open items) from REF_CLK to the AI1 node AIN1 (ADC side of R111). Note "V0.2: CLK2 = f_tx - f_lo phase reference ...". | Fault 18: no common time origin between the transmit pulse and the LO; the phase reference needs CLK2 on a GPIO, optionally on AI1. | R707 (0603 100 R, NMR RX sheet), R119 (0603 0 R, B1 sheet) |
| 7 | AD9834 PSELECT (U801 pin 10) tied to GND; GPIO42 (J2 pin 6) now drives the panel WIFI LED through R717 (0 R); GPIO43 (UART0 TX, J2 pin 2) is unconnected. R718 (GPIO44 -> LED_ACT) is 1 k. Root and base pin maps updated; root sheet pin DDS_PSEL deleted on both sheet blocks. | Fault 7: the WIFI LED on UART0 TX was lit and flickered at boot; 1 k on GPIO44 limits contention with the dev board's USB-UART bridge. | R718 1 k (kept on its 0805 footprint, part C17513 0805W8F1001T5E) |
| 8 | R722 9.1 k -> 10.0 k (stage-2 gain 11); R915, R917, R919, R924 20 k -> 40.2 k and C914, C915 560 pF -> 270 pF (gain 20, pole 14.7 kHz instead of 14.2 kHz). Stale notes ("R712 permanent", JP702/JP703/JP701, "G = 20") rewritten: J3 is a selector by design (1-2 = R712, G = 101; 2-3 = R714, G = 11), J9 1-2 closes the R723 leg. | Faults 2 and 3. | R722 = R0603_10.0k (C95204); R915/917/919/924 = R0603_40R2k (C12447); C914/C915 = 270 pF C0G (C107046, CC0603JRNPO9BN271) |
| 9 | R111-R118 to 0805, 0.4 W anti-surge 1 k (ROHM ESR10EZPF1001, C510097). Same positions on the PCB. | Fault 10: 0.1 W series resistors. | R111-R118 |
| 10 | R933 is the 10 mOhm 2512 shunt by default (R2512_10mR, C500718; was a 0 R link). J13 unchanged (no ADC channel is free). J905 silkscreen "1 +VCOIL  2 COIL  3 GND  (pin 1 = right)  <=24V". No fuse holder added. | Faults 13 and 14. | R933 |
| 11 | Stale notes corrected or removed on every sheet: AGND/NT1 (one ground net), J5/J4, JP1xx/JP70x/JP802/JP904, RN521/RN522 (now: R951-R958 pull DIO1-8 low), 17 SMA (16), link pin numbers (TX on J6 pins 10/12, RX J6 pin 20, MOD1-7 on J7 pins 23-35, OPTO on J7 15/17, J7/J8 roles swapped in the B5 tables and titles), the D-19 channel map (now the netlist: AI1->AIN_1, AI2->AIN_0, AI3->AIN_7, AI4->AIN_6, AI5->AIN_5, AI6->AIN_4, AI7->AIN_3, AI8->AIN_2), "PIN/SW = 1" (now 0), "+VEXT 7-18 V" (7-24 V), the J6 pin table (even = signal, odd = GND), the TCXO option (not on the board). PCB: "AGND-GND Bridge" text deleted; board text "TIGP CLASS BOARD 2026 V0.2". | Fault list, last section. | - |

Each change carries a dated "V0.2 (2026-10-08)" note on its sheet.

## Changes, front panel

| # | Change | Reason |
|---|---|---|
| 12 | F1, 1.5 A polyfuse (same part as F201: `FUSE_1812L150`, footprint `class_board:F1812`, C18198333), between +5V_RAW and the module header J40 pins 1-2 (new net `/+5V_MOD`). PCB: F1 next to J40; J40 pin 1 no longer passes +5V_RAW on to U410/U401/U402/C410 (that branch is now fed from the B.Cu trunk through a new 0.8 mm via at (43.1, 95.05)); 1.0 mm tracks. | Fault 15: the module header +5 V was unfused. |
| 12 | Silkscreen: "ISO IN 1  5-24 V" at J411 (copy of the ISO IN 2 text); the AO/AI/TRIG caption now reads "AO +-10 V   TRIG 5 V logic in/out / AI +-10 V (+-22 V max), 1 kohm series" without "outer copper = AGND"; panel title "rev C" -> "V0.2". | Faults 8, 10, 13. |
| 12 | Schematic notes: one ground net, 16 SMA, J1/J2/J3 mate J6/J8/J7, MOD1-7 on J3 23-35, OPTO on J3 15/17, 6N137 on +5V_RAW, WIFI/ACT from GPIO42/GPIO44 through R717/R718, stale GPIO names beside unconnected J3 pins removed. | Fault list, last section. |
| 13 | R717/R718 relocation: nothing changes on the panel (LED_WIFI/LED_ACT keep their link pins). | - |

## New reference designators and values

| Ref | Value | Footprint | Sheet | PCB position (mm) |
|---|---|---|---|---|
| R5 | 10k (C25804) | R_0603 | base_mcu | 63.69, 78.40 |
| R6 | 10k | R_0603 | base_mcu | 124.35, 34.45 (next to U101) |
| R7 | 10k | R_0603 | base_mcu | 68.52, 60.10 |
| R8 | 10k | R_0603 | base_mcu | 73.85, 59.60 |
| R9 | 10k | R_0603 | base_mcu | 95.71, 59.60 |
| R10 | 10k | R_0603 | base_mcu | 78.43, 78.40 |
| R119 | DNP-0 (0 R, C21189) | R_0603 | b1_inputs | 107.50, 28.50 |
| R707 | 100 (C22775) | R_0603 | nmr_rx | 67.50, 86.50 |
| R821, R822 | 1k (C21190) | R_0603 | nmr_tx | 66.23 / 68.77, 77.00 |
| R811, R812 (re-placed) | 100k (C25803), fitted | R_0603 | nmr_tx | 66.23 / 68.77, 73.50 |
| R942 | 100k | R_0603 | c_switch | 55.75, 29.25 |
| R943 | 10k | R_0603 | c_switch | 60.42, 78.35 |
| C942 | 100nF (C14663) | C_0603 | c_switch | 58.75, 77.00 |
| F1 (panel) | 1.5A polyfuse | class_board:F1812 | front panel | 48.50, 104.35 |

Removed: D931. Changed values: R718 1k, R722 10.0k, R915/R917/R919/R924 40.2k, C914/C915 270pF, R933 10mR, R111-R118 1k 0805 0.4 W.

## PCB routing

All new connections are routed (no unrouted connection on either board). Track width 0.25 mm for signals, 1.0 mm for the panel +5 V feed; vias 0.6/0.3 mm (0.8/0.4 mm on the panel); no tracks on the inner layers; zones refilled. The routes were found by a simple grid maze router written for this job (0.1 mm grid, both outer layers, clearances from the board's rules plus margin), so the long ones are correct but not elegant:

| Connection | Length (mm) | Vias |
|---|---|---|
| TX_IFLAG, U802 pin 8 -> R821/R811 at J1 | 101 | 2 |
| TX_TFLAG, U802 pin 3 -> R822/R812 at J1 | 95 | 4 |
| VEXT_SENSE, R942 -> R943/C942 at J1 pin 4 | 69 | 5 |
| REF_CLK, J1 pin 8 / R707 -> R119 at AI1 | 86 | 7 (mostly B.Cu, shielded from the F.Cu analog inputs by the two GND planes) |
| GPIO42, J2 pin 6 -> existing track to R717 | 23 | 1 |
| +3V3 to the pull-ups R5 / R7 / R6 | 11 / 17 / 7 | 2 / 2 / 0 |
| all others (CE links, PSELECT GND via, pull-resistor signal and GND vias, R707/R119 local, divider local) | 1-12 each | 0-2 |

Other PCB edits: the R113 GND via moved 0.35 mm (the 0805 pad was 0.17 mm from it); an orphaned +3V3 via (the old R812 stub junction) removed and the B.Cu trunk straightened; dangling stubs of the old flag tracks removed. Reference texts of the new parts are on the silkscreen, except R6, R821 and R943, whose references are on F.Fab (no free silkscreen spot next to them).

## Checks before and after

| Check | Ordered design | V0.2 copy before changes | V0.2 final |
|---|---|---|---|
| Main ERC | 0 errors, 2 warnings (J13 pin types) | same | same |
| Main DRC + parity | 0 errors, 5 warnings (silkscreen, D205/D206/R212/PS201), 0 unconnected, 1 parity warning (J13 BOM flag) | same | same |
| Panel ERC | 0 / 0 | same | same |
| Panel DRC + parity | 0 errors, 3 warnings (PWR/WIFI/ACT silkscreen), 0 unconnected, 0 parity | same | same |

kicad-cli reports no missing symbol or footprint library for either project. 3D models: the same two models as in the ordered design do not resolve (`HDR-TH_3P-P2.54-V-M.step` is missing from `lib/class_board.3dshapes`; `${KICAD10_MIKE_JLCPCB_LIB}` is not defined on this machine); everything else resolves.

## What a reviewer should check

1. **Open both projects in KiCad 10 and run Update PCB from Schematic (dry run)**: it should report nothing to change. The PCB was updated with the `pcbnew` module, not with KiCad's own update.
2. **R119 must be marked Do Not Populate** in its symbol properties (and the footprint follows on the next update): Konnect cannot set KiCad's DNP attribute, so R119 carries the value "DNP-0" but is still a BOM line. Fit it only for the reference-channel mode.
3. **Two parts have no entry of their own in `lib/class_board.kicad_sym`**: C914/C915 (270 pF C0G) use the `C0603_560pF` symbol and R111-R118 (1 k 0805 0.4 W) the `R0603_1k` symbol, with value, footprint, LCSC, MPN and manufacturer set on the instance. Add `C0603_270pF` and `R0805_1k_0W4` in the Symbol Editor and swap the instances before ordering. (R718 keeps the old practice of the ordered design: a 0603 library symbol with an 0805 footprint on the instance.)
4. The four long routes (flags, VEXT_SENSE, REF_CLK): tidy by hand if wanted; check REF_CLK (a square wave) against the analog input traces at its two F.Cu stretches near R119 and near the dev-board socket.
5. Silkscreen next to the new parts (R6, R821, R943 references on F.Fab), and the new J901 "+" and J905 legend.
6. The panel F1 feed: J40 pins 1-2 now take +5V_MOD only; U410/U401/U402/C410 are fed by the new via at (43.1, 95.05).
7. U201/U202 CE links run under the SC-70 bodies between the pad rows (at least 0.3 mm from the GND pads 2 and 5).
8. Pins notes on the root sheet: the J6/J7/J8 x positions in the stack-up note ("J6 at x 12, J7 at x 90, J8 at x 168") were left as they were and are worth checking against the PCB.

## Not done, or left open

- The AD9834 full-scale current note still says 3.18 mA (fault 4: 3.0 mA by the datasheet formula); the AD9834 description field still says "75 MHz"; the B5 title-block comment still mentions the TCXO option (Konnect has no title-block tool).
- No fuse on +VCOIL, no Schmitt-trigger TRIG input, no line drivers for 50 ohm loads, no AMS1117 tab copper, no DAC headroom change (faults 8, 9, 14, 17, 19 were not in the V0.2 brief).
- No gerbers or other outputs were generated.
