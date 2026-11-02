# Assembling the class board: soldering, first power-up, the stack and the housing

The factory (JLCPCB) fitted every surface-mount part and the large through-hole parts: the SMA jacks, the screw
terminals, the USB-C socket, the 5 V jack and the two isolated converters. What remains is yours: the 2.54 mm
headers and sockets, the jumper shunts, three labels, the first power-up, plugging the two boards together and
putting the instrument into its housing. This page is the list the tutor refers to. Work through it in order; each
step says what to check before the next.

Rule of thumb: **look before you solder**. The records do not say exactly which connectors the factory fitted on
each board, so step 1 is an inspection, and a part that is already there is skipped.

## 0. What you need

**Your kit** (one per board): the main board (class board v0.7, 180 × 100 mm, "rev B" on the silkscreen), the
front panel (same size, "rev C"), the ESP32-S3 dev board (Jinhua #40729), and connectors from the class stock:

| Part | Where it goes | Pieces per board |
|---|---|---|
| 1×20 female socket, 8.5 mm body (Jinhua 10116) | main board J1, J2 (the dev board plugs in here) | 2 |
| 2×20 female socket, 8.5 mm body (10108) | main board J6, J7, J8, on the **back** of the board | 3 |
| 2×20 male header, cut from a 2×40 strip (41522) | panel J1, J2, J3, on the panel's **inner** face | 3 |
| 1×3 male header, cut from a 1×40 strip (41504) | main board J3, J9, J10, J11, J12, J14, J15, **only if the factory left them empty** | up to 7 |
| 2.54 mm jumper shunt (15293) | on the seven 1×3 headers | 7 |
| 1×4 female socket (33637) | panel J30, the OLED socket, **only if J30 is empty or carries a male header** | 1 |
| 2×6 male header, cut from a 2×40 strip | panel J40, **only if the factory left it empty** | 1 |
| M3 × 11 mm stand-off, female–female, with 2 × M3 × 6 screws | between the two boards, four corners (lab stock) | 4 + 8 |
| M2 × 10 mm stand-off with PM2 × 5 screws (22500, 22578) | the OLED module, when it arrives | 4 + 8 |

The OLED modules are not in stock yet. The board works without one: the class firmware does not drive it, and J30 is
a socket, so the module plugs in later without soldering.

**Tools:** a temperature-controlled soldering iron with a small chisel or conical tip, 0.5–0.8 mm solder (the
boards are lead-free HASL; leaded or lead-free solder both wet it), flux, flush cutters, masking tape, a multimeter,
a magnifier or a phone camera, and a USB-C data cable. Desoldering wick or a pump only if a wrong part has to come
off. Solder in a ventilated place and wash your hands afterwards.

**Orientation words used below.** The *rear edge* of the main board is the edge with the USB-C socket, the 5 V jack
and the three screw terminals. The *component side* carries the surface-mount parts and faces the dev board. The
*back* is the plain side; the front panel sits on it. On the panel, the *outer face* carries the SMA jacks and is the
face of the instrument; the *inner face* looks at the main board. **Pin 1 of every header footprint is the square
pad.** The 1×3 headers carry no position labels on the silkscreen, so count from the square pad.

## 1. Inspect the boards

1. Main board, component side: find J1 and J2, two rows of 22 holes, 25.4 mm apart, under the silkscreen
   "ESP32-S3-DevKitC-1". They should be empty. Find the seven 1×3 positions J3, J9, J10, J11, J12, J14, J15: note
   whether the factory fitted a header on them. J13 (1×2, near the centre) stays empty whatever you find.
2. Main board, back: J6 along the rear edge (right half), J7 along the right edge, J8 along the left edge, each a
   2×20 field of holes. They should be empty.
3. Panel, inner face: J1 along the rear edge, J2 and J3 along the two side edges, 2×20 each. Empty.
4. Panel, outer face: J30, four holes in a row next to the four M2 holes of the OLED, silkscreen GND VCC SCL SDA.
   Empty, or a **male** header, which is wrong and comes off in step 6. J40, the 2×6 module header: the factory
   preview showed a shrouded header fitted; if it is there, leave it.
5. With the meter on ohms, from the main board's ground (the shell of the USB-C socket, or test point TP2) to
   +5V_RAW (TP4), +3V3 (TP3), +12 V (TP203), −12 V (TP204) and +5VA (TP205): none below about 1 kΩ. A reading near
   zero is a short from the factory; stop and show the instructor.

## 2. Cut and mark the headers

1. From a 2×40 male strip cut three 2×20 pieces per panel (one strip gives two). Cut between pins with the flush
   cutters, square to the strip; file nothing. The strip has a short side (about 3 mm) and a long side (about 6 mm):
   the short side goes into the panel, the long side into the socket.
2. If J40 was empty: cut a 2×6 piece from a spare half. It has no key, so mark its pin-1 corner with a paint dot
   or a scratch now.
3. If the 1×3 positions were empty: cut seven 1×3 pieces from a 1×40 male strip.

## 3. Main board: the dev-board sockets J1 and J2

The footprints have 22 holes; the sockets have 20 pins. Solder them offset: nothing is lost.

- **J1** (count from the square pad): holes 1 and 2 are the dev board's two 3V3 pins, which the main board does not connect. Put the socket in **holes 3 to 22**, leaving
  the two holes at the square-pad end empty. Hole 21 (5 V in) and hole 22 (ground) keep their socket pins.
- **J2**: holes 21 and 22 are two of the dev board's four ground pins. Put the socket in **holes 1 to 20**, leaving
  the two holes at the far end empty. Ground stays through J2 hole 1 and J1 hole 22.

The placement above is the recommended answer to an open question to the instructor; follow what the instructor
says on the day if it differs.

How to solder them straight: plug both sockets onto the dev board's pins first, so the dev board holds them at the
right spacing. Check the orientation: the dev board's two **3V3** pins (printed on the dev board) sit at the
square-pad end of J1, its **5V** pin at hole 21, and its two USB-C sockets point away from the square pads. Push
the four free socket tails into the holes, turn the board over, tape the dev board down, solder one pin at each
end of each socket, look that both sockets stand square, then solder the rest. Unplug the dev board. Each joint is
a small shiny cone; a dull blob or a bridge to the neighbouring pad is reworked with the iron and a little flux.

**Tails on the back.** The J1 and J2 tails come through on the back, inside the 11 mm gap that the panel will
cover. On the instructor's first board three rework wires are soldered to those tails (section 9); nothing is
soldered there on a student board.

## 4. Panel: the three link headers J1, J2, J3

1. Push a 2×20 piece into panel J1 from the **inner** face, short side into the board, so the plastic body sits
   on the inner face and the long pins stand up from it. The pin-1 square pad takes any pin; the header has no
   polarity, the board does.
2. Tape it, turn the panel over, solder the two corner pins on the outer face, check that the body sits flat and
   square, then solder the other 38. The joints land among the SMA jacks; they are 9.8 mm tall, keep the iron
   clear of them.
3. The same for J2 and J3 along the side edges.

## 5. Main board: the three link sockets J6, J7, J8, soldered while mated

The three 2×20 sockets must line up with the three panel headers to within a fraction of a millimetre, so solder
them plugged onto the panel:

1. Push a socket onto each of the panel's three headers, all the way down onto the header body.
2. Lay the main board **back down** onto the three socket tails. The panel and the main board meet **rear edge to
   rear edge**; the panel's silkscreen says "REAR / TOP EDGE ... meets the main board's rear edge". Only this way do
   the three fields line up: main J6 on panel J1, J7 on J3, J8 on J2, pin for pin.
3. Fit the four M3 × 11 stand-offs between the boards with a screw from each side, finger-tight, so the boards are
   parallel and the sockets sit flat against the main board's back.
4. Solder the 120 pins on the main board's **component side**. They sit among small parts; use the fine tip and
   work from the outside in. Look at every row with the magnifier: no bridges between the two rows, which are 2.54 mm
   apart.
5. Take the screws out and pull the boards apart, straight and evenly, a little at each corner. They come apart
   again whenever a jumper or the dev board needs reaching.

## 6. Panel: J30 and J40

- **J30 empty:** push the 1×4 female socket in from the outer face, body on the outer face, and solder the four
  tails on the inner face. Pin 1 (square pad) is GND.
- **J30 with a male header:** the OLED module's own pins cannot plug into it. Cut the plastic strip away from the
  four pins with the flush cutters, pull each pin out with the iron on its joint, clear the four holes with wick,
  then fit the female socket as above. Ask the tutor for help the first time.
- **J40 empty:** push the marked 2×6 piece in from the outer face. Pin 1, the marked corner, goes on the square
  pad: it is at the right-hand end of the row nearer the board's centre. Solder on the inner face. Pins 1 and 2
  carry +5 V, 11 and 12 ground; a cable plugged in backwards puts 5 V on a module's ground, so the mark matters.

## 7. Main board: option headers, shunts and labels

1. If the seven 1×3 positions were empty, solder a 1×3 piece on each from the component side, pin 1 on the
   square pad.
2. Fit the shunts. Each 1×3 header is a selector and **every one carries a shunt**; an open header leaves a stage
   without feedback or a driver without supply. Positions for the NMR console, counted from the square pad:

| Header | Shunt | What it selects |
|---|---|---|
| J3 | 1-2 | receiver stage 1 gain 101 (2-3: gain 11) |
| J9 | 1-2 | receiver stage 2 gain 10 |
| J10 | 1-2 | transmitter gain 25 (open: follower, for a first test) |
| J11 | 1-2 | transmitter output direct (2-3: through the 20 dB pad) |
| J12 | **2-3** | polarizer gate driver fed from 5 V. 1-2 feeds it from the bench supply and is allowed only below 18 V; the course runs 24 V |
| J14 | 2-3 | ADC channel 7 = receiver I (1-2: panel input AI7) |
| J15 | 2-3 | ADC channel 8 = receiver Q (1-2: panel input AI8) |

3. Three labels, because the silkscreen misleads: on J905 (the 3-way terminal at the rear) "1 +VCOIL · 2 COIL ·
   3 GND" with pin 1 marked, the printed legend is in reverse order; on J901 (the 24 V input) "+" at pin 1, the
   square pad, no polarity is printed; on the panel's J411 "ISO IN 1". A strip of masking
   tape and a fine pen are enough.

## 8. First power-up

Two rules from the board: **one 5 V source at a time**, the USB-C socket on the main board or the 5 V jack, never
both; and **USB first, then the bench supply**, off in the reverse order. The transmitter amplifier is damaged if
its 24 V arrives before the 3.3 V logic.

1. **Without the dev board.** Plug a USB-C cable from a laptop or a 5 V / 2 A supply into the main board's USB-C
   socket at the rear edge. Four LEDs by the rear edge light: D203 (+5 V), D204 (+3V3), D205 (+12 V), D206 (−12 V).
   With the meter against ground: TP3 3.30 V (3.24 to 3.36), TP203 +12 V and TP204 −12 V (within 1.2 V), TP205
   5.00 V (4.85 to 5.15). A dark LED or a rail out of range: unplug and show the instructor. After a few minutes
   nothing on the board should be too hot to touch; the 3.3 V regulator runs warm, that is normal.
2. **Unplug. Dev board in.** Orientation as in step 3: 3V3 pins at the square-pad end of J1, USB sockets away from
   it, the two unsocketed pins of each row hanging over the empty holes. Press it fully home.
3. **Plug the USB-C into the main board again.** The dev board's RGB LED comes on. A fresh dev board has nothing
   useful on it yet; a board flashed in Workshop 1 starts the simulator build and shows blue (its own WiFi network).
4. **Flash the real build.** In VS Code, open the class repository's `firmware` folder in the PlatformIO terminal,
   one command per line:

   ```
   pio run -e esp32s3 -t upload
   pio run -e esp32s3 -t uploadfs
   ```

   The first command writes the firmware, the second the web app. A dev board that has never been flashed ignores
   the upload until you hold **BOOT**, tap **RST** and release BOOT; it then comes back on a **new COM port**, and the
   upload works to that port (`--upload-port COMx` if PlatformIO picks the wrong one). This is needed once. BOOT and
   RST are the two small buttons on the dev board, reachable while the panel is off.
5. **Watch it boot.** The serial monitor in PlatformIO shows `[boot]`, then one `[registry] <name> ready` line per
   block, then `[wifi] AP instrument-XXXX` or `[wifi] STA <ip>` and `[http] server started`. With no WiFi credentials
   in your git-ignored `secrets.h` the board opens its own network `instrument-XXXX` (password `instrument`); join it
   and open 192.168.4.1. The RGB LED: yellow while joining, green on your network, blue on its own.
6. Unplug the USB before the next step.

## 9. The instructor's first board

The first board carries the rework of `notes/2026-10-08-board-rework-plan.md` before anything is done to the
others; whether the other boards get it is decided after that board's measurements. It touches the J1 tails on the
back and is done after step 3 and before step 10: A2, two wires with 1 kΩ in series from the pads of R811 and R812
(the pad on the U802 side) to the J1 tails at pins 6 and 7; B6, a 100 kΩ / 10 kΩ divider with 100 nF across the
10 kΩ from +VEXT (the C940 pad, or the J901 side of F901) to the J1 tail at pin 4; A1, the clock generator's CLK2
from TP701 into the AI1 path, as an SMA pigtail into the panel's AI1 jack or a wire to the R111 pad on the link
side. Pins 4, 6 and 7 keep a socket pin under the offset of step 3. The bring-up order after that is section E of
the rework plan: rails, then the analog loop-back, the digital lines, the transmitter at 24 V into a dummy load with
J10 open first, the receiver, and last the H-bridge and polarizer with the external fuse.

## 10. Plug the two boards together

1. USB unplugged. Main board component side down, dev board hanging below. Panel outer face up.
2. Rear edge to rear edge, the three headers over the three sockets, press down evenly at the four corners until
   the socket bodies meet the header bodies: the gap between the boards is 11 mm all round.
3. Four M3 × 11 stand-offs in the corner holes, M3 × 6 screws from both sides. Do not use longer screws from the
   two sides into an 11 mm stand-off: the tips meet.
4. USB in. The panel's three LEDs: D1 PWR on; D2 WIFI lit and flickering during boot (it shares a serial line),
   then under the firmware's control; D3 ACT. Open the app: the **A** / **B** / **C** smoke tests of workbook chapter 4
   (a voltage on AI1, a sine from AO1, a TTL line, a module output, an isolated input) show that the panel is
   connected. One wrong reading on a whole group of signals means a link header mated one pin off: unplug and look.
5. The 24 V bench supply on J901 only now, + to the labelled pin, current limit set, over-voltage limit at 25 V.
   D933 (+VEXT) lights. The coil supply on J905 last, through the in-line fuse. Switch off in the reverse order.

The jumpers, the dev board's buttons and the terminal screws all face down inside the stack: to reach them, open
the housing and turn the instrument over.

## 11. Into the housing

Your housing is your own design, so its README is the authority; the common points:

1. Print and check the test coupon first; fit an M3 screw and a nut in it.
2. Anything that goes **between** the panel and its cover goes on before the stack enters the housing: Yi-Tsai's
   OLED surround sits in the cover window and goes onto the panel before the shell.
3. Lower the mated stack in, rear edge to the rear wall: the USB-C, the 5 V jack and the three terminals show in
   the rear openings, the SMA field and the module header in the cover openings.
4. Cover on, then the bottom lid; the lid's small holes sit under the terminal screws where the design has them.
5. Stick-on feet taller than the lid's screw heads.

The OLED module, when it comes, plugs into J30 with its pins in the order **GND VCC SCL SDA**, the same as the
silkscreen. Modules with VCC and GND swapped exist and would be powered backwards; read the pin names on the
module before plugging it in. It is held by four M2 × 10 stand-offs or by the cover, as your design says.

## Where this page sits

The bring-up page `hardware/docs/bring-up.md` holds the instructor's full measurement sequence; the board
reference `docs/class-board-reference.md` §6.2 and §7 the jumper table and the link pinout; workbook chapter 4
the exercises that start once the app runs on the real board.
