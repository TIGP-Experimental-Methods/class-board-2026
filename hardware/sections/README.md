# Main board — four routing areas

The main board is one board, but its routing is finished by four students, one area each. Every section folder holds a
complete copy of the board with the instructor's routing locked and a `SECTION.md` with the parts and the connections
to route. The instructor merges the four copies with `python hardware/scripts/main_sections.py merge`, which takes from
each copy only the new tracks and vias that lie completely inside that copy's area. A connection that crosses an area
boundary is the instructor's; the instructor routes anywhere in the master at any time.

| Area | Who | Where | Routes | Parts | Connections left |
|---|---|---|---|---|---|
| **A** | Renqian (branch `a-renqian`) | Rear right | the analog inputs: the ADC U101, the input conditioning R11x / C11x / D11x, the AGND-select headers J14 / J15 | 49 | 1 |
| **B** | Yi-Tsai (branch `w1-yi-tsai`) | Front right | the analog outputs (DAC U301 and the output stage) and the NMR transmitter (DDS, filter, power stage, TX terminal side) | 70 | 3 |
| **C** | the instructor (no student) | Front left | the NMR receiver: tank and blanking switch, LNA, I/Q mixer, IF filters, clock generator; the expansion header J5 | 104 | 2 |
| **D** | Lihdong (branch `d-lihdong`) | Rear left | power entry and rails, the coil switches (H-bridge, polarizer), the dev-board socket J1 / J2 and the fast TTL buffer U502 | 83 | 8 |

The link sockets J6 / J7 / J8, the dev-board rows J1 / J2, the expansion header J5, the mounting holes and the fiducials
belong to the instructor wherever they sit.

Not yet placed (parked outside the outline; the instructor places them): J4 J5 R3 R4 R701 R702 R717-R719 TP1-TP4 TP101 TP205 TP206.

**Connections that cross an area boundary — the instructor's (59):** GND x10, +3V3 x9, I2C_SDA x5, I2C_SCL x5, AGND x4, +5V_RAW x2, +5VA x2, -12V x2, +12V x2, SPI_SCLK x2, SPI_MOSI x2, /base_mcu/RST, /base_mcu/GPIO4, /base_mcu/GPIO6, /base_mcu/GPIO7, /base_mcu/GPIO15, /base_mcu/RX_BLANK, SPI_MISO, /b5_dio_trig/EXP_P14, /base_mcu/TRIG_IO, /base_mcu/GPIO43, /b5_dio_trig/LED_WIFI, /nmr_rx/CLK0_MCLK, /base_mcu/GPIO44, /b5_dio_trig/LED_ACT.

Why by area: the main board's remaining work is mostly local — vias from pads to the planes and short links between
neighbouring parts — so a geometric cut gives each student a coherent piece of the board to learn on, and the few
long connections (SPI, I²C, the rails between areas) stay with the instructor.
