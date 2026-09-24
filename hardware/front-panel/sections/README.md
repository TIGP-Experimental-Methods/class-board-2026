# Front panel — four routing sections

The front panel is one board, but its routing is done by four students, one section each. Every section folder holds a
complete copy of the unrouted panel and a `SECTION.md` with the nets to route. The instructor merges the four copies
with `python hardware/scripts/panel_sections.py merge`, which takes only each section's own nets from each copy.

| Section | Who | Routes | Nets |
|---|---|---|---|
| **A** | Renqian (branch `a-renqian`) | Analog signals: link J1 to the SMA field and the TX coil terminal | 13 |
| **B** | Yi-Tsai (branch `w1-yi-tsai`) | Digital outputs, trigger and LEDs: link J2 to the TTL strip J31, the FAST1/FAST2 and TRIG SMAs, D1-D3 | 16 |
| **C** | the instructor (no student) | Module outputs: link J3 to the pull-downs R491-R498, the 74AHCT541 U410, the series resistors R481-R488 and the module header J40 | 25 |
| **D** | Lihdong (branch `d-lihdong`) | Isolated inputs, 3.3 V and I2C: terminals J411/J412 to the 6N137 chains and link J3; +3V3 to every part; I2C from J2 to the OLED J30 and the Qwiic J33 | 19 |

GND and AGND are the inner planes: every section drops the vias its own parts need. Nothing else is shared.

Why by nets and not by area: every panel net runs from a link header at an edge to a connector in the middle of the board,
so a geometric cut would leave half a trace on every boundary. With net groups each connection is complete in one copy.
