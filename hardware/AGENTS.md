# CLASS BOARD — LAYOUT AGENT RULES (KiCad 10, 4-layer, JLCPCB Economic PCBA incl. THT)

Source of truth: `10-Class-Board-Design-Brief.md` in the course repo
(`G:\My Drive\2. Presentations\2026\20260910-TIGP`), sections 4–9. Read it before touching the board.
Engineering checklist that binds every decision: `MIXED_SIGNAL_PCB_DESIGN_PRACTICES.md` (same repo).

You place and route. You do **not** change the schematic, footprints, pin assignments, net names, board
outline, stack-up, rule areas (`ZONE_*`), net classes or DRC rules. If any of those must change, stop and ask.

## Branch and commits
Work on branch `astra-layout`. Commit after each numbered phase below with a one-line message
`layout: phase N — <what>`. Never commit with DRC errors you have not listed in the summary.

## Board facts (do not re-derive)
- 4-layer JLC04161H-7628, 1.6 mm. **L1 (F.Cu) signal · L2 (In1.Cu) GND, unbroken · L3 (In2.Cu) power islands · L4 (B.Cu) signal.**
- Rule areas with owners: `ZONE_BASE`, `ZONE_B1` (inputs), `ZONE_B2` (power), `ZONE_B3` (outputs), `ZONE_B4` (switching),
  `ZONE_B5` (DIO/TRIG), `ZONE_OPT` (DNP conditioning). Reference numbering encodes the owner: 1–99 base, 1xx B1, 2xx B2,
  3xx B3, 4xx B4, 5xx B5, 6xx OPT.
- Net classes: `POWER_RAW` 1.0 mm · `POWER` 0.5 mm · `ANALOG_IN` 0.25 mm / 0.3 mm clearance · `ANALOG_OUT` 0.3 mm ·
  `FAST` 0.25 mm · `ISO_IN` clearance 2.5 mm to everything · `RELAY_CONTACT` 0.5 mm / 1.0 mm clearance · `DEFAULT` 0.25 mm.
- One AGND–GND join: the net-tie / 0 Ω link at the B1–BASE boundary. Nothing else joins them.

## Order of work
1. **Inspect.** Open the schematic PDF and the PCB. List the blocks, the fixed items and the rule areas. Do not move anything yet.
2. **Fixed items stay fixed:** the 2×20 link on the front edge (centred), rear-edge terminals / USB-C / jack, the four M3 holes,
   the 2×22 dev-board socket.
3. **Placement inside each ZONE only.** Decoupling capacitors immediately at their IC pins, smallest value closest.
   ADS8688 and DAC8563 near their SMAs' link pins with the socket between them (short SPI). ULN2003 between the relays and the
   socket. Optocouplers with a visible empty 2.5 mm band around their input side. DC-DC modules in the power corner with input
   and output capacitors at their pins; their outputs leave the zone through the LC filters.
4. **Route in this order:** `+5V_RAW` entry → fuses → ORing → modules/LDOs (1.0 mm) → star point and AGND copper → SPI + CS →
   ADC input networks and AO output stages (**L1 only**, over unbroken L2) → `USB_DP/USB_DN` pair → `FAST_OUT`, `TRIG` →
   relay contacts and coil drives (wide, rear) → `ISO_IN` (respect the 2.5 mm band) → DIO and remaining logic (L4 allowed) →
   rails on In2.Cu islands with ≥ 2 vias per transition → pours → DRC → refill → DRC.
5. **Never** place a track on In1.Cu. **Never** split In1.Cu (the only void is under the `ISO_IN` band). **Never** add a second
   AGND–GND connection.
6. Analog nets (`AI*`, `AIN*`, `AO*`, `DAC_*`, `VREF_DAC`) stay on F.Cu with no vias where avoidable and ≥ 2 mm from SPI, FAST,
   relay and DC-DC copper.
7. `SPI_*`, `CS_*`, `FAST_OUT*`, `TRIG_IO` short (< 60 mm) with a ground return adjacent; minimise vias on them.
8. Power: no neck-downs at pads, vias, fuses or connectors; 0.5 mm minimum for rails, 1.0 mm for `+5V_RAW`.
9. Refill zones and run DRC after every phase. Never waive or suppress a DRC error. Zero unrouted nets at the end.
10. **Stop and summarise** in this order — Blocker / High / Medium / Low — each with net, location, mechanism, proposed fix and
    how to verify: placement decisions, routing decisions, remaining DRC items, anything needing engineering review.

## Things that look like shortcuts and are not allowed
Moving a footprint out of its zone to make routing easier · cutting In1.Cu to "separate" analog and digital · widening a trace
by changing its net class · deleting a DNP footprint · changing a footprint to a smaller package · routing an `ISO_IN` net under a
relay · joining AGND and GND at a second point "for a shorter return".
