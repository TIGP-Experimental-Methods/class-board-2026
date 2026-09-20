# Main board — four routing areas

The main board is one board, but its routing is finished by four students, one area each. Every section folder holds a
complete copy of the board with the instructor's routing locked and a `SECTION.md` with the parts and the connections
to route. The instructor merges the four copies with `python hardware/scripts/main_sections.py merge`, which takes from
each copy only the new tracks and vias that lie completely inside that copy's area. A connection that crosses an area
boundary is the instructor's; the instructor routes anywhere in the master at any time.

| Area | Where | Routes | Parts | Connections left |
|---|---|---|---|---|
| **A** | Rear right | the analog inputs: the ADC U101, the input conditioning R11x / C11x / D11x, the AGND-select headers J14 / J15 | 49 | 53 |
| **B** | Front right | the analog outputs (DAC U301 and the output stage) and the NMR transmitter (DDS, filter, power stage, TX terminal side) | 70 | 22 |
| **C** | Front left | the NMR receiver: tank and blanking switch, LNA, I/Q mixer, IF filters, clock generator; the expansion header J5 | 78 | 25 |
| **D** | Rear left | power entry and rails, the coil switches (H-bridge, polarizer), the dev-board socket J1 / J2 and the fast TTL buffer U502 | 111 | 31 |

The link sockets J6 / J7 / J8, the dev-board rows J1 / J2, the expansion header J5, the mounting holes and the fiducials
belong to the instructor wherever they sit.

Not yet placed (parked outside the outline; the instructor places them): J4 R3 R4 R701 R702 R719 TP1-TP4 TP101 TP205 TP206.

**Connections that cross an area boundary — the instructor's (66):** GND x10, +3V3 x9, I2C_SDA x6, I2C_SCL x6, +5V_RAW x5, AGND x5, +5VA x4, -12V x3, +12V x3, SPI_SCLK x2, SPI_MOSI x2, /base_mcu/RST, /b3_outputs/CS_DAC, /b1_inputs/CS_ADC, SPI_MISO, +VEXT, +3V3A, /b1_inputs/AUX, /b5_dio_trig/EXP_P14, /nmr_rx/CLK0_MCLK, /base_mcu/TX_EN, /b1_inputs/RX.

Why by area: the main board's remaining work is mostly local — vias from pads to the planes and short links between
neighbouring parts — so a geometric cut gives each student a coherent piece of the board to learn on, and the few
long connections (SPI, I²C, the rails between areas) stay with the instructor.
