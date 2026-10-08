# The class board: hardware and firmware reference

**What this is.** Everything an app or firmware author needs to use the capabilities of the TIGP class board 2026: the two boards as ordered, every connector and what it reaches, the ESP32 pin map, the buses, the protocol of every chip, the signal levels and limits, the reference firmware and its message protocol, and what is verified and what is not.

**Version.** Class repository `class-board-2026` commit `6ef1c7c` (2026-10-06), the design that was sent to manufacture on 2026-10-05 plus the LED-polarity correction of 2026-10-06. Reference written 2026-10-08. Every pin, net and resistor value below was taken from the KiCad netlists of that commit (`kicad-cli sch export netlist`); the printed-circuit boards pass schematic parity. Chip behaviour comes from the manufacturers' datasheets, cited by section where it matters. Where a value could not be established it says *not determined*.

**Authority.** The netlist of the design files wins over every text note. Several notes inside the `.kicad_sch` files, `hardware/README.md`, `hardware/docs/` and the 2026-09-13 design notes describe older revisions (an AGND net and a net tie NT1, solder jumpers JP1xx, link pins 37–40, a 17th SMA, an expansion header, an ADC map starting AI1→AIN_6, TX on link pins 19/21). None of those exist on the ordered boards. When an AI assistant reads the schematic files it will meet these notes; this document is the current state.

**Use it in your own repository.** Project 3 lives in your own repository, where your own Claude session writes the code and never sees the class repository. Copy this file into that repository as `docs/class-board-reference.md` and add one line to its `CLAUDE.md`: *"Hardware facts for the class board are in docs/class-board-reference.md; pin numbers, addresses and limits come only from there."* The tutor does this with you when the repository is set up. The firmware pin header `firmware/include/pins.h` agrees with this document; copy it too.

**Status of the hardware (2026-10-08).** The boards are ordered and expected about 16 October. No class-board firmware has run on a class board yet. Everything marked *verified* below was verified on a bare dev board or on paper, nothing on the assembled instrument. Treat every register sequence as a hypothesis until it has been measured, and say so in your code comments.

---

## Contents

1. The instrument in one page
2. Rules that protect the hardware
3. ESP32-S3 pin map
4. The buses: SPI and I²C
5. The front panel, connector by connector
6. The main board's rear edge: power, coils, option headers, test points
7. The three links between the boards
8. The capabilities, one by one (signal path, chip protocol, code, limits)
9. The reference firmware and its protocol
10. Known defects and open points
11. Sources

---

## 1. The instrument in one page

**Three parts.** A Jinhua #40729 **ESP32-S3-N16R8 dev board** (DevKitC-1 pin order, 16 MB flash, 8 MB PSRAM, native USB) plugs into the **main board** (180 × 100 mm, 4 layers), which carries the converters, the NMR console, the power supplies and the coil switches. The **front panel** (180 × 100 mm, 4 layers) sits face-to-face on the main board on three 2×20 links and carries the signal connectors: 16 SMA jacks, the OLED, three LEDs, a 10-way TTL screw strip, the transmit terminal, a Qwiic socket, a 2×6 module header and two isolated inputs. The main board's rear edge carries the USB-C, the 5 V jack, the +VEXT input and the two coil terminals. The housing holds the sandwich flat, panel up.

**What it can do** (the capabilities an app can use):

| Capability | Front-panel connector | Hardware | Firmware block |
|---|---|---|---|
| 8 analog inputs, 16 bit, ±10.24 V down to ±2.56 V, about 15 kHz bandwidth, up to 500 kS/s in total | SMA AI1–AI8 | ADS8688 (SPI) | `b1` |
| 2 analog outputs, 16 bit, ±10 V, 50 Ω source | SMA AO1, AO2 | DAC8563 (SPI) + OPA2192 | `b3` (stub) |
| 8 TTL outputs, 5 V through 1 kΩ | screw strip TTL1–8 | TCA9535 (I²C) + 74AHCT541 | `b5` |
| 7 module outputs, 5 V TTL through 47 Ω, for relay or H-bridge modules | 2×6 header OUT1–7 (+5 V, GND) | TCA9535 + 74AHCT541 | `b4` |
| 2 fast outputs, 5 V, from GPIO (PWM, RMT, clock) | SMA FAST1, FAST2 | 74HCT125 | `b5` (stub) |
| 1 trigger line, in or out, 5 V | SMA TRIG | 74LVC1T45 | `b5` |
| 2 isolated inputs, 5–24 V | screw terminals ISO IN 1, 2 | 6N137 optocouplers | `b4` |
| OLED 128×64 and a Qwiic socket on the I²C bus | OLED socket, Qwiic | SSD1306 module (I²C 0x3C) | none yet |
| Pulsed NMR console: transmitter from a few hertz to about 1 MHz in 0.19 Hz steps, up to about 15 V pp into the coil; heterodyne I/Q receiver into two ADC channels | SMA TX + terminal TX COIL, SMA RX | Si5351A, AD9834, OPA564, OPA1656, DG419, 74HC74, TS5A23157, OPA1612 | `nmr` |
| Field-cycling H-bridge, 2 A, from the external supply | rear terminal H-BRIDGE COIL | DRV8871 | `b4` |
| Polarizer coil switch, up to 13 A from a separate coil supply | rear terminal +VCOIL COIL GND | UCC27517 + AOD4184A | `b4` |
| 3 panel LEDs (PWR, WIFI, ACT), the dev board's RGB LED | — | GPIO43/44, GPIO48 | `base` (RGB only) |
| WiFi (access point or station), web app, WebSocket, mDNS, OTA | — | ESP32-S3 | `main.cpp` |

**Power.** 5 V in by USB-C or a 5.5/2.1 mm jack (one at a time, section 2) makes +5V_RAW, +3V3 and, through two isolated converters, ±12 V and +5VA. A separate 7–18 V bench supply on the rear terminal (+VEXT) powers only the transmitter power stage, the H-bridge and, by jumper, the polarizer gate driver. The polarizer coil has its own supply terminal (+VCOIL). One ground net: there is no separate analog ground.

**Firmware.** PlatformIO, Arduino framework, two environments: `esp32s3-sim` fakes every chip so the whole app runs on a bare dev board; `esp32s3` is the real board. One WebSocket carries JSON commands and a 20 Hz status broadcast; binary frames carry records. Section 9.

---

## 2. Rules that protect the hardware

These follow from the datasheets and the netlist. They are listed once here and repeated where they apply.

1. **Power-on order: USB (or the 5 V jack) first, let the board boot, then +VEXT, then +VCOIL. Off in reverse.** The transmitter amplifier OPA564 is damaged if its main supply rises before its 3.3 V logic supply (datasheet SBOS372E, Fig. 36). The main board's silkscreen says "USB FIRST, THEN BENCH SUPPLY".
2. **One 5 V source at a time: USB-C or the jack, never both.** The two LM66100 ideal-diode controllers have their chip-enable pins on ground, which the datasheet calls "always on" without reverse-current blocking (SLVSEZ8A §8.3.1). With both connected, the higher source feeds the lower one through about 0.16 Ω. The same applies to the dev board's own USB sockets, which join +5V_RAW through the dev board's 5 V pin: flash through the main board's USB-C.
3. **+VEXT is 7–18 V.** The silkscreen says so, and 18 V is the UCC27517's supply limit when J12 is on 1-2 (the OPA564 itself allows 24 V). The jack is 5 V only.
4. **Keep TX_EN (GPIO40) low except during a pulse.** The amplifier draws 39 mA idle against 5 mA shut down, and blanking relies on the gate being closed.
5. **Never open the receiver (RX_BLANK = 1) while TX_EN = 1 or within the dead time after a pulse** (default 1 ms): the coil rings and the first amplifier stage would be driven into its rails.
6. **Never leave the polarizer on.** FET_GATE = 1 switches a low-resistance coil onto an external supply with no on-board limit. Bound every polarize interval in code (the sequencer allows at most 10 s; the `b4 polarizer` command has no limit).
7. **H-bridge: coast (both inputs low) is the resting state.** Brake or a held direction at the 2 A trip point dissipates about 2.3 W in the DRV8871, which shuts down thermally without telling anyone (no fault pin).
8. **Never program Si5351 CLK0 above 50 MHz.** It is the AD9834's master clock; the fitted BRUZ grade is a 50 MHz part. The firmware's `nmr clock` command does not enforce this.
9. **Three jumper headers need a shunt before use: J3, J11 and J12.** J3 open leaves the receiver's first stage with no feedback at all; J11 open disconnects TX; J12 open leaves the polarizer driver unpowered. J10, J14 and J15 have defined open states (follower; ADC input floating). Section 6.2.
10. **Inputs and outputs are not isolated** (except ISO IN 1/2). Board ground is the USB host's ground and the +VEXT supply's minus. Limits: AI ±22 V continuous; AO must never be driven from outside; MOD and FAST −0.5 to +5.5 V; TTL about −8 to +13 V through its 1 kΩ; TRIG 0–5 V logic; RX millivolts only (never connect TX to RX).
11. **Safe GPIO levels before `pinMode(OUTPUT)`:** `digitalWrite(pin, LOW)` first, then `pinMode(pin, OUTPUT)`, for TX_EN, RX_BLANK, HB_IN1/2 and FET_GATE. The board's 10 k pull-downs hold these five pins low through reset; TRIG_DIR, DDS_PSEL and FAST_OUT1/2 have no pull resistor and are undefined until the firmware runs.
12. **Never use GPIO 0, 3, 45, 46 (strapping) or 35, 36, 37 (octal PSRAM).** They are not wired on the main board; the strapping pins set the boot mode and the PSRAM pins belong to the memory.
13. **Secrets never enter a chat, a prompt or a commit.** WiFi passwords go into the git-ignored `firmware/include/secrets.h`, typed by the person in the editor.

---

## 3. ESP32-S3 pin map

Derived from the dev-board socket nets (main-board J1 = DevKitC-1 left row, J2 = right row), each net followed to the chip pin. Every number agrees with `firmware/include/pins.h`.

| GPIO | Constant in `pins.h` | Net | Reaches | Direction | Idle / reset state |
|---|---|---|---|---|---|
| 1 | `PIN_I2C_SDA` | I2C_SDA | TCA9535 U505, Si5351A U701, panel OLED and Qwiic; 4.7 k to +3V3 | open-drain | high |
| 2 | `PIN_I2C_SCL` | I2C_SCL | same devices; 4.7 k to +3V3 | open-drain | high |
| 5 | `PIN_CS_DAC` | CS_DAC | 74HCT125 U302 → DAC8563 /SYNC (5 V) | out | no pull: set high in `begin()` |
| 8 | `PIN_RX_BLANK` | RX_BLANK | DG419 U704 IN; 10 k to GND | out | low = receiver blanked |
| 9 | `PIN_HB_IN1` | HB_IN1 | DRV8871 U903 IN1; 10 k to GND | out | low |
| 10 | `PIN_CS_ADC` | CS_ADC | ADS8688 U101 pin 38 /CS | out | no pull: set high in `begin()` |
| 11 | `PIN_SPI_MOSI` | MOSI_MCU → SPI_MOSI (33 Ω) | ADS8688 SDI, AD9834 SDATA, U302 → DAC8563 DIN | out | — |
| 12 | `PIN_SPI_SCLK` | SCLK_MCU → SPI_SCLK (33 Ω) | ADS8688 SCLK, AD9834 SCLK, U302 → DAC8563 SCLK | out | — |
| 13 | `PIN_SPI_MISO` | SPI_MISO (33 Ω) | ADS8688 SDO, the only device on MISO | in | — |
| 14 | `PIN_HB_IN2` | HB_IN2 | DRV8871 IN2; 10 k to GND | out | low |
| 16 | `PIN_OPTO_IN[0]` | OPTO_IN1 | panel 6N137 U401 output, 1 k to +3V3 on the panel | in | high = no input |
| 17 | `PIN_OPTO_IN[1]` | OPTO_IN2 | panel 6N137 U402 output, 1 k to +3V3 | in | high = no input |
| 18 | `PIN_FAST_OUT[1]` | FAST_OUT2 | 74HCT125 U502 → 49.9 Ω → panel SMA FAST2 (J21) | out | no pull: undefined until set |
| 19 | `PIN_USB_DN` | USB_D_N | USB-C J201 D− (and the dev board's own native-USB socket) | bidir | — |
| 20 | `PIN_USB_DP` | USB_D_P | USB-C J201 D+ | bidir | — |
| 21 | `PIN_FAST_OUT[0]` | FAST_OUT1 | 74HCT125 U502 → 49.9 Ω → panel SMA FAST1 (J15) | out | no pull |
| 38 | `PIN_TRIG_IO` | TRIG_IO | 74LVC1T45 U503 A side (3.3 V); B side → 33 Ω → panel SMA TRIG (J12) | bidir | set by GPIO39 |
| 39 | `PIN_TRIG_DIR` | TRIG_DIR | 74LVC1T45 DIR: 1 = output to the SMA, 0 = input | out | no pull: undefined until set |
| 40 | `PIN_TX_EN` | TX_EN | OPA564 U802 enable; 10 k to GND | out | low = transmitter off |
| 41 | `PIN_DDS_FSYNC` | DDS_FSYNC | AD9834 U801 /FSYNC (its chip select) | out | no pull: set high in `begin()` |
| 42 | `PIN_DDS_PSEL` | DDS_PSEL | AD9834 PSELECT pin, ignored (PIN/SW = 0); no pull | out | hold low |
| 43 | `PIN_UART0_TX` | GPIO43 | 0 Ω → panel LED D2 "WIFI" through 1 k | out | UART0 TX: idles high, LED lit, flickers with boot messages |
| 44 | `PIN_UART0_RX` | GPIO44 | 0 Ω → panel LED D3 "ACT" through 1 k | out | UART0 RX; the dev board's USB-UART bridge can drive it |
| 47 | `PIN_FET_GATE` | FET_GATE | 100 Ω → UCC27517 U904 IN+ → AOD4184A gate; 10 k to GND | out | low = polarizer off |
| 48 | `PIN_RGB_LED` | — | the WS2812 on the dev board itself; nothing on the main board | out | — |
| 0, 3, 4, 6, 7, 15, 35, 36, 37, 45, 46 | — | not connected | — | — | never use 0/3/45/46 (strapping), 35–37 (PSRAM); 4/6/7/15 are free pins with no connector |

Other socket pins: the dev board's **3V3 pins are not connected** to the main board's +3V3 (the ESP32 runs from the dev board's own regulator; all main-board logic runs from the AMS1117). The dev board's **5V pin is +5V_RAW**: the dev board is powered by the main board, and its own USB sockets back-feed +5V_RAW. RST (EN) reaches test point TP1 only.

I²C addresses: TCA9535 **0x20** (A0 = A1 = A2 = GND), Si5351A **0x60** (fixed), SSD1306 OLED **0x3C** (the usual module; not fixed by the netlist).

---

## 4. The buses: SPI and I²C

### 4.1 SPI2 (GPIO12 SCLK, 11 MOSI, 13 MISO), three devices

| Device | Chip select | Mode | Clock used by the firmware | Frame | Logic level at the chip |
|---|---|---|---|---|---|
| ADS8688 U101 (ADC) | GPIO10, active low | mode 1 (CPOL 0, CPHA 1) | 17 MHz requested, 16 MHz actual | 32 bit | 3.3 V (DVDD = +3V3); it is the only device that drives MISO |
| AD9834 U801 (DDS) | GPIO41 /FSYNC, active low, per 16-bit word | mode 2 (CPOL 1, CPHA 0) | 10 MHz | 16 bit | 3.3 V |
| DAC8563 U301 (DAC) | GPIO5 /SYNC, active low, per 24-bit frame | mode 1 (CPOL 0, CPHA 1: data clocked on the falling edge) | not yet written | 24 bit | **5 V**: SCLK, DIN and /SYNC pass through the 74HCT125 U302 (VCC = +5VA, always enabled) |

Three different modes on one bus, so every transaction is wrapped in its own `SPI.beginTransaction(SPISettings(...))`, and on the class firmware in the SPI lock `spibus::Guard` (section 9.3). The DAC's buffered lines toggle during every ADC or DDS transfer; the DAC ignores them while /SYNC is high. Series 33 Ω resistors sit in SCLK and MOSI at the ESP32 and in MISO at the ADC's SDO pin.

Hard-wired pins: ADS8688 /RST//PD pulled high (10 k), DAISY, /REFSEL and AUX_IN on GND (internal 4.096 V reference, no daisy chain). AD9834 RESET and SLEEP pulled low (10 k each), FSELECT on GND, so reset, sleep and the phase select are **register bits** (PIN/SW = 0). DAC8563 /LDAC on GND (every write-and-update takes effect at once), /CLR pulled high.

### 4.2 I²C (GPIO1 SDA, GPIO2 SCL), 400 kHz

| Device | Where | Address | Role |
|---|---|---|---|
| TCA9535 U505 | main board | 0x20 | 16 outputs: TTL1–8, module outputs 1–7, the receiver's counter clear |
| Si5351A U701 | main board | 0x60 | clock generator: DDS master clock, receiver local oscillator |
| SSD1306 OLED module | panel socket J30 | 0x3C (module) | display |
| Qwiic socket J33 | panel | the user's device | 3.3 V I²C expansion |

Pull-ups 4.7 k to +3V3 on the main board only (an OLED module usually adds its own). The bus leaves the main board on link J8 pins 31 (SCL) and 33 (SDA). Arduino-ESP32's `Wire` serialises transactions with its own mutex; the class firmware adds no lock of its own. The firmware starts the bus once in `BaseBlock::begin()` with `Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 400000)`.

---

## 5. The front panel, connector by connector

Panel labels are printed below each jack. Front view, three rows of six jacks; `x` grows to the right.

### 5.1 The 16 SMA jacks

| Row, column | Ref | Label | Signal | Direction | Goes to |
|---|---|---|---|---|---|
| top 1 | J16 | **AI1** | analog input 1 | in | ADS8688 channel AIN_1 |
| top 2 | J17 | **AI2** | analog input 2 | in | AIN_0 |
| top 3 | J18 | **AI3** | analog input 3 | in | AIN_7 |
| top 4 | J19 | **AI4** | analog input 4 | in | AIN_6 |
| top 5 | J14 | **AUX** | spare receiver input | — | **not connected** on the ordered boards (reaches only the unfitted R715) |
| top 6 | J15 | **FAST1** | fast output 1 | out | GPIO21 via 74HCT125 and 49.9 Ω |
| middle 1 | J22 | **AI5** | analog input 5 | in | AIN_5 |
| middle 2 | J23 | **AI6** | analog input 6 | in | AIN_4 |
| middle 3 | J24 | **AI7** | analog input 7, or receiver I | in | AIN_3 through header J14 (1-2 = this jack, 2-3 = receiver I) |
| middle 4 | J25 | **AI8** | analog input 8, or receiver Q | in | AIN_2 through header J15 (1-2 = this jack, 2-3 = receiver Q) |
| middle 5 | J13 | **RX** | NMR receiver input (the coil) | in | tank, limiter, LNA |
| middle 6 | J21 | **FAST2** | fast output 2 | out | GPIO18 via 74HCT125 and 49.9 Ω |
| bottom 1 | J10 | **AO1** | analog output 1 | out | DAC8563 A via OPA2192 and 49.9 Ω |
| bottom 2 | J11 | **AO2** | analog output 2 | out | DAC8563 B via OPA2192 and 49.9 Ω |
| bottom 3 | J20 | **TX** | NMR transmitter output | out | OPA564 through header J11; the same net as terminal J32 |
| bottom 4 | J12 | **TRIG** | trigger, in or out | bidir | 74LVC1T45 B side through 33 Ω |

All shields are GND. The panel caption reads "AO +-10 V · TRIG 5 V TTL (~2.4 V into 50 ohm) · AI +-10 V, 1 kohm series · outer copper = AGND"; the last phrase is stale, there is one ground net.

### 5.2 OLED socket J30 (1×4, for a 0.96-inch SSD1306 module on four M2 stand-offs)

Pin 1 GND · pin 2 VCC (+3V3) · pin 3 SCL · pin 4 SDA. Check your module's pin order against these labels before plugging it in; modules exist with VCC and GND swapped.

### 5.3 TTL screw strip J31 (10-way, 2.54 mm), silk "TTL OUT 1..8 (5 V)"

Pins 1–8 = TTL1–TTL8, pins 9 and 10 = GND. TTLn is TCA9535 port 0 bit n−1, buffered to 5 V by the 74AHCT541 U501 on the main board, 1 kΩ in series. Output only.

### 5.4 TX terminal J32 (2-way, 5 mm), silk "TX COIL"

Pin 1 = TX (the same net as SMA J20), pin 2 = GND. No +/− marks; the legend sits above pin 1. Connect the transmit coil here or at the SMA, not both at once with different loads.

### 5.5 Qwiic J33 (JST SH 1 mm, vertical), silk "QWIIC"

Pin 1 GND · 2 +3V3 · 3 SDA · 4 SCL, the standard Qwiic order. 3.3 V only.

### 5.6 Module header J40 (2×6 shrouded box header, polarised), silk "MODULE OUT 1..7 5 V TTL (8 = spare)"

| Pins | Signal |
|---|---|
| 1, 2 | +5V_RAW (unfused on the panel; about 0.4 A available, less from a USB port) |
| 3 – 9 | OUT1 – OUT7 = TCA9535 P1.0, P1.1, P1.2, P1.3, P1.5, P1.6, P1.7, buffered to 5 V by the panel's 74AHCT541 U410, 47 Ω in series |
| 10 | OUT8: no driver, held low (reserved) |
| 11, 12 | GND |

Made for commercial opto-isolated relay or H-bridge modules (about 5 mA per input). Active high; 10 k pull-downs keep every output low at power-up.

### 5.7 Isolated inputs J411 (right) and J412 (left), 2-way 5 mm screw terminals

Pin 1 = **+**, pin 2 = **−** (silk marks). J412 is labelled "ISO IN 2 5-24 V"; J411 carries only the + and − marks and is ISO IN 1. The input side is a constant-current LED drive (about 7 mA from 5 V up) through a 1N4148W reverse-blocking diode, a 220 Ω resistor and a two-transistor current limiter into a 6N137 optocoupler; it has no connection to board ground. The output is **active low** on GPIO16 (ISO IN 1) and GPIO17 (ISO IN 2): input energised = GPIO reads 0.

### 5.8 LEDs D1–D3 (green 0805)

| LED | Label | Driven by |
|---|---|---|
| D1 | PWR | +3V3 through 1 k: on whenever the main board's 3.3 V is up |
| D2 | WIFI | GPIO43 (UART0 TX) through 0 Ω and 1 k |
| D3 | ACT | GPIO44 (UART0 RX) through 0 Ω and 1 k |

GPIO43/44 are the ESP32's UART0 pins, not the USB port the firmware prints to. After reset GPIO43 is UART0 TX and idles high, so **D2 is lit by default and flickers with the ROM boot messages**. To use D2/D3 as indicators, configure GPIO43/44 as plain outputs after boot and never use UART0 (the dev board's USB-UART bridge drives GPIO44 when that USB socket is connected). The LED polarity of the ordered boards was corrected at the factory (cathode on the GND pad).

---

## 6. The main board's rear edge: power, coils, option headers, test points

### 6.1 Connectors (rear edge, seen from the component side)

| Connector | Silk | Pins | Notes |
|---|---|---|---|
| J201 USB-C | USB-C 5V | VBUS → 1.5 A polyfuse → TVS → LM66100 → +5V_RAW; D+/D− → GPIO20/19 | flashing and the serial console; 5.1 k on CC1/CC2 (a 5 V sink) |
| J202 DC jack 5.5/2.1 mm | 5V IN | centre = +5 V → 1.5 A polyfuse → TVS → LM66100 → +5V_RAW; sleeve = GND | **5 V only**; not together with USB-C (rule 2) |
| J901 2-way 5 mm | +VEXT 7-18V DC FUSE 5A | pin 1 (right, x 52.4) = +, pin 2 = GND; no +/− printed | 5 A fast fuse, 26 V TVS, reverse-polarity P-FET; a reversed supply blows the fuse |
| J903 2-way 5 mm | H-BRIDGE COIL | pin 1 = DRV8871 OUT1, pin 2 = OUT2 | the field-cycling coil, current regulated at 2.0 A |
| J905 3-way 5 mm | +VCOIL COIL GND <=24V | pin 1 = +VCOIL (the polarizer supply's +), pin 2 = COIL (FET drain), pin 3 = GND (that supply's −) | the coil goes between pins 1 and 2. **The legend is printed in the reverse order of the pins**: seen from above, the pins run GND, COIL, +VCOIL from left to right. Wire by pin number. No fuse: the supply must limit the current |

### 6.2 Option headers (1×3 jumper selectors, no position labels printed; pin 1 is the square pad)

| Header | Sheet | 1-2 | 2-3 | Open | Shunt required? |
|---|---|---|---|---|---|
| **J3** | receiver, stage-1 feedback | R712 10 k: gain **101** | R714 1 k: gain **11** | **no feedback: the stage saturates** | **yes, always** |
| **J9** | receiver, stage 2 | gain **10.1** (9.1 k / 1 k) | — | follower, gain 1 | no |
| **J10** | transmitter gain | gain **25** | — | follower, gain 1 (bring-up into a dummy load) | no |
| **J11** | transmitter output | direct output (4.7 Ω, 10 µF coupling) | **−20 dB** tap (910 Ω / 100 Ω) | TX disconnected | **yes** |
| **J12** | polarizer gate-driver supply | from **+VEXT** (only with +VEXT ≤ 18 V) | from **+5V_RAW** | driver unpowered, coil stays off | **yes, to use the polarizer** |
| **J14** | ADC channel AIN_3 | panel **AI7** | receiver **I** | AIN_3 floats (reads about +2 V) | one or the other |
| **J15** | ADC channel AIN_2 | panel **AI8** | receiver **Q** | AIN_2 floats | one or the other |
| J13 (1×2) | coil current sense | shorts the (already 0 Ω) R933 | — | — | no; replace R933 by a 10 mΩ shunt and read ISENSE_COIL here to measure the polarizer current |

Default for the NMR demonstration: J3 1-2, J9 1-2, J10 1-2, J11 1-2, J12 as the supply dictates, J14 2-3, J15 2-3. Default for a general-purpose instrument without the receiver: J14 1-2, J15 1-2 (all eight AI jacks live), J3 still fitted.

### 6.3 Test points

TP1 RST · TP2 GND · TP3/TP202 +3V3 · TP4/TP201 +5V_RAW · TP203 +12V · TP204 −12V · TP205 +5VA · TP301 VREF_DAC (2.5 V when the DAC's reference is on) · TP501 EXP_P14 (the receiver counter's /CLR) · TP701 Si5351 CLK2 (spare clock, a scope trigger) · TP702 V_MID (mixer bias, 1.65 V). There is no net tie and no AGND test point.

---

## 7. The three links between the boards

Main-board J6/J7/J8 are 2×20 female sockets on the main board's back; panel J1/J2/J3 are 2×20 male headers on the panel's inner face. With the panel mirrored onto the main board (panel x = 180 − main x), **pin n mates pin n** on all three, and 119 of the 120 pins carry the same signal on both sides (the exception, J6/J1 pin 13, is unconnected on the main board and GND on the panel). On J6/J1 the signals are on the even pins and the odd pins are GND; on J7/J3 and J8/J2 the signals are on the odd pins and the even pins are GND.

| Link | Role | Signal pins (main board = panel) |
|---|---|---|
| **J6 = J1** | analog | 10, 12 TX · 16 AO2 · 18 AO1 · 20 RX · 22 AUX · 24 AI8 · 26 AI7 · 28 AI6 · 30 AI5 · 34 AI4 · 36 AI3 · 38 AI2 · 40 AI1 (2, 4, 6, 8, 14, 32 unused) |
| **J7 = J3** | power, isolated inputs, module outputs | 1, 3 +5V_RAW · 5 +3V3 · 15 OPTO_IN1 · 17 OPTO_IN2 · 23, 25, 27, 29, 31, 33, 35 MOD1–MOD7 (odd pins here; the even pins 2–40 are GND) |
| **J8 = J2** | digital | 1, 3, 5, 7, 9, 11, 13, 15 TTL8…TTL1 · 23 LED_ACT · 25 LED_WIFI · 27, 29 +3V3 · 31 I2C_SCL · 33 I2C_SDA · 35 TRIG_5V · 37 FASTTTL2 · 39 FASTTTL1 (odd pins here; even pins GND) |

On J7 and J8 the signals are on the **odd** pins and the even pins are GND; on J6 the signals are on the even pins and the odd pins are GND. Full pin-by-pin tables with both sides' net names are in the class repository under `hardware/docs/link-pinout.md`.

---
## 8. The capabilities, one by one

Each subsection gives the signal path with the fitted values, the numbers an app needs, the chip's protocol as it must be used on this board, a minimal Arduino snippet with the constants of `pins.h`, the state of the reference firmware, and the traps. Three start-up rules apply to every sketch:

- **Drive every SPI chip select high before the first SPI transfer:** `PIN_CS_ADC`, `PIN_CS_DAC`, `PIN_DDS_FSYNC` have no pull-up on the board and float at reset. In particular the DAC's /SYNC floats while the ADC is being configured, and the DAC can swallow ADC traffic as a command (section 10).
- **Start I²C with explicit pins before any library touches `Wire`:** `Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 400000)`. This Arduino core's ESP32-S3 defaults are SDA = GPIO8 and SCL = GPIO9, which on this board are the receiver blanking and the H-bridge input. A bare `Wire.begin()` would toggle the H-bridge.
- **The chips keep their state through an ESP32 reset.** The TCA9535, DAC8563 and ADS8688 are reset only by a power cycle. `setup()` rewrites every output and register every time.

### 8.1 Analog inputs AI1–AI8 (ADS8688)

```
panel SMA AIn → link J6/J1 → R11n 1 kΩ → node: C11n 1 nF to GND, BAV99 clamp to ±12 V → ADS8688 AIN_x (1 MΩ inside)
AI7, AI8 only: SMA → J14/J15 pin 1; shunt 1-2 = this SMA, 2-3 = NMR receiver I / Q
```

| Panel input | AI1 | AI2 | AI3 | AI4 | AI5 | AI6 | AI7 | AI8 |
|---|---|---|---|---|---|---|---|---|
| ADS8688 channel | AIN_1 | AIN_0 | AIN_7 | AIN_6 | AIN_5 | AIN_4 | AIN_3 | AIN_2 |

This is `kAinOfAi[8] = {1, 0, 7, 6, 5, 4, 3, 2}` in `pins.h`: **the panel number is never the ADC channel number.** Every range register and every manual-read command takes the ADC channel.

| Quantity | Value |
|---|---|
| Resolution | 16 bit, straight binary (0 V reads 0x8000 on bipolar ranges) |
| Ranges (internal 4.096 V reference), code → span → LSB | 0: ±10.24 V, 312.5 µV · 1: ±5.12 V, 156 µV · 2: ±2.56 V, 78 µV · 5: 0–10.24 V, 156 µV · 6: 0–5.12 V, 78 µV. Codes 3, 4, 7 do not exist on this part |
| Volts from the 16-bit code | bipolar: (code − 32768) × span/32768 · unipolar: code × span/65536 |
| Bandwidth | about 15 kHz (the ADC's internal second-order filter); the board's 1 kΩ / 1 nF corner is 159 kHz |
| Input impedance | 1 kΩ + 1 MΩ to an internal bias; the 1 kΩ costs 0.1 % of gain |
| Sample rate | 500 kS/s in total across the channels scanned; one 32-bit frame at 16 MHz plus pacing in software |
| Open input | reads about +2 V (the internal bias through 1 MΩ), not 0 V |
| Safe input | ±10.24 V measured · to about ±12.6 V no clamp current · about **±22 V continuous** (above that the 0.1 W series resistor overheats and the clamp current lifts the ±12 V rails) · board unpowered: keep within ±1 V |
| Default ranges in the class firmware | all ±10.24 V except AIN_3 and AIN_2 (AI7, AI8, the receiver I/Q) at ±5.12 V |

**Protocol (ADS8688 datasheet SBAS582C §8.4–8.5).** SPI mode 1, MSB first, 16 MHz or less (the limit is 17 MHz; the Arduino core rounds 17 down to 16). /CS low for a whole **32-clock frame**: the 16-bit command goes out in the first 16 clocks, the conversion result of the channel selected in the *previous* frame comes back in the last 16. A short frame invalidates the next result.

| Command | Word | Effect |
|---|---|---|
| NO_OP | 0x0000 | keep converting in the current mode |
| MAN_Ch_n | 0xC000 \| (n << 10) | convert channel n from the next frame on |
| AUTO_RST | 0xA000 | start the auto scan over the channels enabled in register 0x01, lowest first |
| RST / STDBY / PWR_DN | 0x8500 / 0x8200 / 0x8300 | registers to default / standby / power down (15 ms to recover) |

Program registers (24-clock frame): write `(addr << 9) | 0x100 | data`, the chip echoes `data` in clocks 17–24 (the class driver uses the echo as its presence check). Register 0x01 = channels in the auto scan (bit n), 0x02 = channel power-down, 0x03 = SDO format (keep 0), **0x05 + n = range of channel n** (bits 3–0, the codes above). After a register write the chip is idle: send MAN_Ch_n or AUTO_RST before expecting data. The result of a MAN_Ch_n command arrives one frame later.

```cpp
#include <SPI.h>
#include "pins.h"
static const SPISettings kAdcSpi(16000000, MSBFIRST, SPI_MODE1);
static uint32_t adcFrame(uint16_t cmd) {                 // one complete 32-clock frame
  SPI.beginTransaction(kAdcSpi); digitalWrite(PIN_CS_ADC, LOW);
  uint32_t r = SPI.transfer32((uint32_t)cmd << 16);
  digitalWrite(PIN_CS_ADC, HIGH); SPI.endTransaction(); return r;
}
static bool adcWriteReg(uint8_t addr, uint8_t value) {   // program write, checks the echo
  SPI.beginTransaction(kAdcSpi); digitalWrite(PIN_CS_ADC, LOW);
  SPI.transfer16((addr << 9) | 0x0100 | value); uint8_t echo = SPI.transfer(0);
  digitalWrite(PIN_CS_ADC, HIGH); SPI.endTransaction(); return echo == value;
}
float readPanelInput(int ai) {                            // ai = 1..8, range code 0
  uint8_t ch = kAinOfAi[ai - 1];
  adcFrame(0xC000 | (ch << 10));                          // select: this frame returns old data
  uint16_t code = adcFrame(0x0000) & 0xFFFF;              // next frame: the selected channel
  return ((int32_t)code - 32768) * 10.24f / 32768.0f;
}
void setup() {
  for (int cs : {PIN_CS_ADC, PIN_CS_DAC, PIN_DDS_FSYNC}) { digitalWrite(cs, HIGH); pinMode(cs, OUTPUT); }
  SPI.begin(PIN_SPI_SCLK, PIN_SPI_MISO, PIN_SPI_MOSI);
  delay(15);
  for (uint8_t ch = 0; ch < 8; ch++) adcWriteReg(0x05 + ch, 0);   // all ±10.24 V
}
```

**Class firmware.** Driver `drivers/Ads8688.{h,cpp}`, instance `adc`, started by `b1`: `setRange(ch, code)`, `readManual(ch)` (caller holds the SPI lock), `toVolts(ch, raw)`, `burst(mask, buf, n, rate_hz, &achieved)` (auto scan, caller holds the lock; used by the NMR sequencer). Block `b1`: commands `read_all`, `set_range {ch 1..8, range}`; status `ai1…ai8` in volts. **State: implemented from the datasheet, never run on a board.** Known bug: `set_range` accepts codes 3 and 4, which the chip does not have, and reports them as set.

**Traps.** The panel-to-channel table; the one-frame delay of a manual read; complete frames only; the straight-binary code (the class driver flips the top bit into a signed `int16_t`); an open input reads +2 V; with J14/J15 on 2-3 the AI7/AI8 jacks are disconnected.

### 8.2 Analog outputs AO1, AO2 (DAC8563 + OPA2192)

```
DAC8563 VOUTA/B (0–5 V) → OPA2192 difference amplifier (10 k / 40.2 k, reference = the DAC's own 2.5 V) → 49.9 Ω → link J6/J1 → panel SMA AO1 / AO2; BAV99 clamps to ±12 V
```

| Quantity | Value |
|---|---|
| Transfer function | AO = 4.02 × (V_DAC − 2.5 V) = **10.05 V × (code − 32768) / 32768** |
| Code for a voltage | code = 32768 + AO × 3260, clamped to 0…65535 (code 32768 = 0 V exactly, independent of the reference error) |
| Range, resolution | ±10.05 V, 307 µV per step; the panel says ±10 V |
| Source resistance | 49.9 Ω: full swing into ≥ 1 kΩ, half into 50 Ω, about ±3 V into 50 Ω before the op-amp's ±65 mA limit |
| Speed | slew about 3 V/µs at the output; in practice limited by the SPI update rate |
| Power-up | the DAC's internal reference is **off** and the outputs undefined until the firmware sends the enable; after a warm reset the DAC holds its last value |
| Safe external voltage | **never drive an AO from outside**; beyond about ±12.6 V the clamp conducts into the ±12 V rails |
| Top of the range | the DAC output cannot exceed its 5 V supply (+5VA from the 78L05); a low +5VA saturates the top codes, not determined until measured |

**Protocol (DAC8563 datasheet SLAS719E §8.5).** 24-bit frames while /SYNC (GPIO5, through the 5 V buffer U302) is low, MSB first, data latched on the **falling** SCLK edge (SPI mode 1). **Keep the clock at or below 8 MHz:** SCLK and DIN pass through two gates of the 74HCT125 whose relative skew is not guaranteed. First byte `X X C2 C1 C0 A2 A1 A0`, then 16 data bits. /LDAC is grounded on this board, so every write updates the output at once; /CLR is tied high and cannot be used.

| Purpose | Bytes |
|---|---|
| Enable the internal 2.5 V reference (also sets both gains to 2) | `38 00 01` |
| Write DAC-A / DAC-B and update it | `18 hh ll` / `19 hh ll` |
| Write both and update both | `1F hh ll` |
| Software reset | `28 00 01` |
| Power down both outputs (1 kΩ to GND) | `20 00 13` |

```cpp
static const SPISettings kDacSpi(8000000, MSBFIRST, SPI_MODE1);
static void dacFrame(uint8_t cmdAddr, uint16_t data) {
  SPI.beginTransaction(kDacSpi); digitalWrite(PIN_CS_DAC, LOW);
  SPI.transfer(cmdAddr); SPI.transfer16(data);
  digitalWrite(PIN_CS_DAC, HIGH); SPI.endTransaction();
}
void setAO(int ao, float volts) {                         // ao = 1 or 2
  long code = lroundf(32768.0f + volts * 32768.0f / 10.05f);
  dacFrame(0x18 | (ao - 1), (uint16_t)constrain(code, 0L, 65535L));
}
// in setup(), after SPI.begin() and the chip selects: dacFrame(0x38, 0x0001); dacFrame(0x1F, 0x8000);
```

**Class firmware.** No driver class. Block `b3` (`blocks/b3_outputs/OutputsBlock.cpp`) has the command layer `set_dc {ch, volts}`, `sine {ch, freq, amp, offset}`, `off {ch}` and status `ao1, ao2, mode1, mode2`, but **the DAC initialisation and the SPI frame are TODO stubs**: on real hardware the status reports voltages that are not produced. The comment in that file uses gain 4 and 65535; the board gives 4.02 and 65536. The `sine` command updates once per millisecond, so anything above a few hundred hertz is aliased.

**Traps.** Enable the reference first and write mid-scale to both channels in every `setup()`. The buffered SCLK/DIN reach the DAC during every ADC and DDS transfer; the DAC ignores them only while /SYNC is high, so /SYNC must be high before the first ADC transfer (section 10).

### 8.3 TTL outputs TTL1–8 and module outputs OUT1–7 (TCA9535 + 74AHCT541)

```
TCA9535 port 0 bit n−1 (3.3 V) → 10 k pull-down → 74AHCT541 U501 (5 V) → 1 kΩ → link J8/J2 → panel J31 pin n "TTLn"
TCA9535 port 1 bits 0,1,2,3,5,6,7 (3.3 V) → link J7/J3 → panel 10 k pull-down → 74AHCT541 U410 (5 V) → 47 Ω → J40 pins 3–9 "OUT1–7"
TCA9535 port 1 bit 4 → EXP_P14 = /CLR of the receiver's quadrature counter (10 k pull-up): normally 1
```

| Quantity | TTL1–8 | OUT1–7 |
|---|---|---|
| Direction, logic | output only, bit 1 = high | output only, bit 1 = module on |
| Level | 0 / 5 V through **1 kΩ** (2.5 V into 1 kΩ, 4.5 V into 10 kΩ) | 0 / 5 V through **47 Ω** |
| Loads | CMOS/HCT inputs, an opto-coupler or LED (about 3 mA); not a bipolar 74xx input | relay or H-bridge module inputs, ≤ 8 mA each; **not short-proof** (a short exceeds the buffer's 25 mA maximum) |
| Short to GND or 5 V | 5 mA, harmless | avoid |
| External voltage | about −8 V to +13 V survives through the 1 kΩ; never connect to a supply | −0.5 to +5.5 V |
| Speed | one I²C port write (about 75 µs at 400 kHz): kilohertz at most; all eight lines of a port change together | same |
| Power-up | all low (pull-downs) until the firmware writes the port | all low |
| +5 V on J40 pins 1–2 | — | +5V_RAW, unfused on the panel; about 0.4 A spare, less from a USB port |

**Protocol (TCA9535 datasheet SCPS201F §6.6).** I²C address 0x20, 400 kHz, one command byte then data. Registers 0x00/0x01 input ports (read the pin levels), **0x02/0x03 output ports**, 0x04/0x05 polarity inversion (inputs only), **0x06/0x07 configuration** (1 = input, 0 = output; power-up 0xFF). The registers come in pairs: writing `0x02, P0, P1` sets both output ports in one transaction. **Write the output registers before the configuration registers** at start-up, or every line pulses high for the duration of one write. Safe idle values: port 0 = 0x00, port 1 = 0x10 (`EXP_CTRL_IDLE`: modules off, /CLR released). Never clear port 1 wholesale: bit 4 is the counter clear.

```cpp
static bool expWrite(uint8_t reg, uint8_t v) {
  Wire.beginTransmission(I2C_ADDR_EXPANDER); Wire.write(reg); Wire.write(v);
  return Wire.endTransmission() == 0;
}
uint8_t out0 = 0x00, out1 = EXP_CTRL_IDLE;
void expBegin() {                                          // after Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 400000)
  expWrite(0x02, out0); expWrite(0x03, out1);              // outputs first
  expWrite(0x06, 0x00); expWrite(0x07, 0x00);              // then all 16 lines become outputs
}
void ttl(int n, bool level)    { bitWrite(out0, n - 1, level);            expWrite(0x02, out0); }
void module(int n, bool on)    { bitWrite(out1, EXP_BIT_MOD[n - 1], on);  expWrite(0x03, out1); }
```

**Class firmware.** Driver `drivers/Tca9535.{h,cpp}`, instance `expander`, started by `base`: `writePort`, `writeBit`, `cached`, `readPort`, `present`, `pulseJohnsonClear`. Block `b5`: `dio {n 1..8, level}`, `dio_mask {mask}`; status `dio`, `dio1…dio8`. Block `b4`: `module {n 1..7, on}`, `module_all {on}`; status `module1…module7`. Both answer `"expander not present"` on a bare dev board in the real build. **State: implemented, never run on a board.** The output cache is written from two tasks without a lock (the NMR sequencer pulses the counter clear); a lost update is possible.

### 8.4 Fast outputs FAST1, FAST2 (GPIO → 74HCT125 → SMA)

```
GPIO21 (FAST1) / GPIO18 (FAST2) → 74HCT125 U502 (5 V, always enabled) → 49.9 Ω → link J8/J2 → panel SMA J15 / J21
```

Any signal the ESP32 can put on a GPIO: LEDC PWM, MCPWM, RMT pulse trains, a clock. 0 / 5 V into a high-impedance load; about 1.2–1.9 V into 50 Ω at 24–38 mA, which is at the buffer's absolute maximum, so **use high-impedance loads** (a 1 MΩ scope input at the end of a 50 Ω cable is fine: the 49.9 Ω is a back termination). Clean edges to about 10 MHz, degraded above about 20 MHz (the buffer's 15 ns transition time); the class firmware's 40 MHz limit is not realistic. No pull resistor: undefined until the firmware configures the pin. External voltage −0.5 to +5.5 V.

```cpp
ledcSetup(0, 1000 /*Hz*/, 8 /*bit*/); ledcAttachPin(PIN_FAST_OUT[0], 0); ledcWrite(0, 128);   // 1 kHz square wave on FAST1
```

**Class firmware.** Block `b5`: `fast_out {n 1..2, freq_hz}` stores and reports the frequency; **the real branch is a TODO stub** (the pins are never configured).

### 8.5 TRIG, in or out (74LVC1T45)

```
GPIO38 TRIG_IO ↔ 74LVC1T45 U503 A side (3.3 V); GPIO39 TRIG_DIR → DIR (no pull resistor)
U503 B side (5 V) ↔ 33 Ω ↔ TRIG_5V: BAV99 clamp to GND / +5V_RAW ↔ link J8/J2 pin 35 ↔ panel SMA J12
```

| DIR (GPIO39) | Flow | GPIO38 | Level at the SMA |
|---|---|---|---|
| 1 | out: GPIO38 → SMA | output | 0 / 5 V open circuit, about 2.5 V into 50 Ω (50 mA, at the part's maximum; short = 100 mA, too much) |
| 0 | in: SMA → GPIO38 | input | **high ≥ 3.5 V, low ≤ 1.5 V** (the input side runs at 5 V, so a 3.3 V source is below the guaranteed high); edges faster than 5 ns/V required, no sine waves |

With nothing plugged in and DIR = 0 the input floats and GPIO38 reads noise. From reset until the firmware runs, DIR is undefined (no pull resistor), so the SMA may be driven for that interval. Switching order: **input → output:** `pinMode(PIN_TRIG_IO, INPUT_PULLDOWN)`, DIR high, then `pinMode(PIN_TRIG_IO, OUTPUT)`; **output → input:** `pinMode(PIN_TRIG_IO, INPUT)`, then DIR low. Never drive TRIG from outside while it is an output. External voltage 0–5 V logic; a 50 Ω generator up to about ±10 V is absorbed by the clamp.

```cpp
void trigBegin() { pinMode(PIN_TRIG_DIR, OUTPUT); digitalWrite(PIN_TRIG_DIR, LOW); pinMode(PIN_TRIG_IO, INPUT); }
void trigOut(bool level) { pinMode(PIN_TRIG_IO, INPUT_PULLDOWN); digitalWrite(PIN_TRIG_DIR, HIGH);
                           pinMode(PIN_TRIG_IO, OUTPUT); digitalWrite(PIN_TRIG_IO, level); }
void trigIn()            { pinMode(PIN_TRIG_IO, INPUT); digitalWrite(PIN_TRIG_DIR, LOW); }
```

**Class firmware.** Block `b5`: `trig_dir {out}`, `trig {level}` (only when out); status `trig_dir`, `trig`. Implemented, never run; the input-to-output switch makes GPIO38 an output before raising DIR, which briefly puts two drivers on one line (section 10).

### 8.6 Isolated inputs ISO IN 1, 2 (6N137)

```
J411/J412 pin 1 (+) → 1N4148W → 220 Ω → MMBT5551 current source (about 7 mA, limited by a second transistor across 91 Ω) → 6N137 LED → pin 2 (−)
6N137 output (open collector, +5V_RAW supply) → 1 kΩ to +3V3 → link J7/J3 pins 15/17 → GPIO16 / GPIO17
```

| Quantity | Value |
|---|---|
| Input | 5–24 V DC, pin 1 positive; about 7 mA constant current; reversed polarity blocked by the diode |
| Turn-on | full current from about 4.5 V; a 3.3 V source is not guaranteed to switch it |
| Maximum | not specified; about 30 V continuous (transistor dissipation) and about 75 V reverse (the diode's class) are estimates not checked against the fitted parts |
| Output logic | **active low**: voltage present → GPIO reads 0; nothing connected → 1 |
| Speed | 6N137 75 ns; pulses of 1 µs and longer are safe |
| Isolation | the opto-coupler is rated 5 kV; the panel's 2.5 mm clearance and the screw terminals set the practical limit: floating low-voltage sources and ground-loop breaking, **not mains** |

```cpp
volatile uint32_t isoCount[2];
void IRAM_ATTR iso1Isr() { isoCount[0]++; }
void isoBegin() { pinMode(PIN_OPTO_IN[0], INPUT_PULLUP); attachInterrupt(PIN_OPTO_IN[0], iso1Isr, FALLING); }
bool iso1Present() { return digitalRead(PIN_OPTO_IN[0]) == LOW; }
```

**Class firmware.** Block `b4`: status `opto1`, `opto2` (falling-edge counts), `opto1_level`, `opto2_level`; command `opto_reset`. Polled at 10 Hz in `loop()`, so pulse trains above about 5 Hz are under-counted; the interrupt counter is a TODO.

### 8.7 OLED and Qwiic (I²C)

OLED socket J30: GND, VCC (+3V3), SCL, SDA. The usual 0.96-inch 128×64 SSD1306 module at **0x3C** with its own charge pump. Qwiic J33: the standard 3.3 V Qwiic order (GND, 3V3, SDA, SCL) for any Qwiic/STEMMA-QT sensor.

SSD1306 essentials (datasheet §8.1.5, §10): every write starts with a control byte, 0x00 = commands follow, 0x40 = display data follows. Init for 128×64 with the internal charge pump: `AE D5 80 A8 3F D3 00 40 8D 14 20 00 A1 C8 DA 12 81 CF D9 F1 DB 40 A4 A6 2E AF`. Memory: 128 columns × 8 pages, one byte = 8 vertical pixels; in horizontal addressing mode (`20 00`) a full frame is 1024 bytes in one stream after `21 00 7F` and `22 00 07`. Use a library:

```cpp
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
Adafruit_SSD1306 oled(128, 64, &Wire, -1, 400000UL, 400000UL);   // both clock arguments: keep the bus at 400 kHz
void oledBegin() {
  Wire.beginTransmission(I2C_ADDR_OLED); bool present = Wire.endTransmission() == 0;   // begin() does not check
  if (present && oled.begin(SSD1306_SWITCHCAPVCC, I2C_ADDR_OLED, false, false)) {
    oled.clearDisplay(); oled.setTextColor(SSD1306_WHITE); oled.setCursor(0, 0);
    oled.println("class board"); oled.display();
  }
}
// U8g2 alternative: U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE, PIN_I2C_SCL, PIN_I2C_SDA);
```

**Traps.** Adafruit_SSD1306 defaults to address 0x3D for 64-pixel-high displays: always pass `I2C_ADDR_OLED`. Its constructor's second clock argument defaults to 100 kHz and the library sets the bus clock around every transfer: pass 400000 twice or the shared bus slows down after every `display()`. `begin()` returns true without a display; probe the address first. A full `display()` holds the bus for about 23 ms, during which expander writes wait. Check the module's pin order against the socket labels before plugging it in. **The class firmware has no OLED code**; the address constant exists and is unused.

### 8.8 NMR receiver (RX jack → I/Q at the ADC)

```
panel SMA J13 "RX" → link J6/J1 pin 20 → tank 1.32 nF to GND, 1 MΩ to GND, crossed 1N4148W limiter (±0.6 V)
 → 100 Ω → OPA1656 stage 1, gain by J3 (1-2: 101 · 2-3: 11 · open: NO FEEDBACK)
 → 10 nF → DG419 blanking switch (RX_BLANK = GPIO8: 0 = stage-2 input grounded = blanked, 1 = receive)
 → OPA1656 stage 2, gain by J9 (1-2: 10.1 · open: 1), 175 kHz low-pass
 → double-balanced commutating mixer (2 × TS5A23157, +3V3A, bias 1.65 V), switched by the quadrature LO
 → IF networks 1 kΩ / 10 nF → OPA1612 difference amplifiers, gain 10, 12 kHz low-pass → COND_OUT1 (I), COND_OUT2 (Q)
 → J14 / J15 pin 3 → (shunt 2-3) → 1 kΩ → ADS8688 AIN_3 (I) / AIN_2 (Q)
Local oscillator: Si5351A CLK1 = 4 × f_LO → 74HC74 Johnson counter ÷4 → LO_I, LO_Q exactly 90° apart; /CLR = TCA9535 P1.4
```

| Setting (J3, J9) | LNA gain | RX → ADC, |I + jQ| per volt | Largest coil signal before the ADC clips (±5.12 V range) |
|---|---|---|---|
| 1-2, 1-2 (default) | 1020 | about 13 000 (82 dB) | 0.4 mV peak |
| 1-2, open | 101 | 1300 | 4 mV |
| 2-3, 1-2 | 111 | 1400 | 3.6 mV |
| 2-3, open | 11 | 140 | 37 mV |

Mixer plus difference amplifier: 20 × 2/π ≈ 12.7 per volt at the LNA output (the design notes say 25.5; they counted the difference-amplifier gain as 20, but the 1 kΩ IF resistors sit in series with its 1 kΩ inputs, so it is 10). For the design coil signal of 40 µV peak expect about 40 mV at the LNA output and **about 0.5 V peak at the ADC** (about 3300 LSB on ±5.12 V), half the figure in the schematic note; the SIM build assumes 18 mV. Reconcile against a measurement. The mixer inputs clamp at about ±1.6 V around the 1.65 V bias, so the ADC clips first in every row above. Baseband bandwidth about 10 kHz (the IF filters and the ADC's own filter). The output is the complex record at **IF = f_tx − f_lo** (positive = the line is above the local oscillator); for the proton demonstration f_tx ≈ 89.4 kHz, f_lo = 84 kHz, IF ≈ 5.4 kHz.

**Si5351A (I²C 0x60, 25 MHz crystal, register map in Skyworks AN619).** CLK0 = 50.000 MHz exactly (PLLA = 25 × 36 = 900 MHz integer, MS0 = 18) is the DDS master clock and must never go higher. CLK1 = 4 f_LO from PLLB (fractional feedback a + b/c, output multisynth MS1 even integer, R divider 1…128); frequency step at the LO about 2 mHz. Register sequence: wait for SYS_INIT (reg 0 bit 7 = 0) · reg 3 = 0xFF (outputs off) · regs 16–23 = 0x80 · reg 183 = 0xD2 (crystal load 10 pF: the board fits 3.9 pF on each crystal pin) · the divider registers (PLLA at 26, PLLB at 34, MS0 at 42, MS1 at 50; eight bytes each encoding P1 = 128a + floor(128b/c) − 512, P2 = 128b − c·floor(128b/c), P3 = c) · reg 16 = 0x4F (CLK0: integer, PLLA, 8 mA), reg 17 = 0x6F (CLK1: PLLB) · reg 177 = 0xA0 (reset both PLLs) · reg 3 = 0xFC (CLK0, CLK1 on). **After every change of CLK1:** reset PLLB (reg 177 = 0x80), then pulse the counter clear (TCA9535 P1.4 low for one write, then high) so the quadrature counter restarts in state 00; without it the receiver phase is off by a random multiple of 90°. CLK2 is unused (test point TP701).

**Blanking (DG419).** GPIO8 low (the reset default, 10 k pull-down) grounds the stage-2 input; high passes the signal. Never raise it while TX_EN is high or inside the dead time after a pulse. Blanking protects stage 2; the crossed diodes protect stage 1. The 10 nF / 10 kΩ coupling recovers in about 100 µs.

**Limits.** The receiver is for microvolt to millivolt signals; the limiter conducts above about 0.5 V. **Never connect TX to RX**: the transmitter can deliver 1.5 A, more than the limiter diodes carry. The AUX jack is not connected on the ordered boards (R715 unfitted).

**Class firmware.** Drivers `Si5351` (`setClk0`, `setClk1`, `resetPllB`, `enable`, `actualClk1`), `Tca9535::pulseJohnsonClear`; block `nmr` owns RX_BLANK during a scan (`blank {receive}` for bench tests). State: implemented, never run.

### 8.9 NMR transmitter (DDS → power stage → TX)

```
Si5351 CLK0 50 MHz → AD9834 (SPI mode 2, FSYNC = GPIO41; 6.8 kΩ full-scale resistor → 3 mA → 200 Ω → about 0.6 V pp sine)
 → 3 MHz third-order Butterworth → 1 µF → OPA564 non-inverting (single supply from +VEXT, mid-rail bias; gain by J10: 1-2 = 25, open = 1)
 → 4.7 Ω, 10 µF AC coupling → J11 (1-2 direct · 2-3 −20 dB pad · open = disconnected) → TX → link J6/J1 pins 10, 12 → panel SMA J20 "TX" and terminal J32 "TX COIL"
TX_EN = GPIO40 → OPA564 enable (10 k pull-down: off at reset); 1 = transmit, on in 3 µs, off in 1 µs
```

| Quantity | Value |
|---|---|
| Frequency | 0.19 Hz steps (50 MHz / 2²⁸), usable to about 1 MHz on this board |
| Output, J10 1-2 | about **15 V pp** around +VEXT/2; needs +VEXT of about 16 V (typical output swing) to 17.5 V (worst case) for a clean sine. At 12 V it clips to about 11 V pp, at 15 V slightly. For 12 V use a lower gain (R808 1 kΩ gives 7.5, 3.3 kΩ gives 3) or accept the clipping |
| Output, J10 open | about 0.6 V pp (bring-up into a dummy load) |
| J11 2-3 | −20 dB: about 1.5 V pp from a 90 Ω source |
| Current limit | 1.5 A (R809 11 kΩ); the ISET pin must never be left open |
| Expected load | the tuned coil (design 2.5 mH, 1.4 kΩ reactance at 89 kHz: about 6 mA); the on-board snubber and pad draw up to about 50 mA peak |
| Into test equipment | ±8 V into a 50 Ω scope input is 0.6 W and above the usual 5 V rms limit: use a 1 MΩ input or J11 2-3 |
| Amplitude control | **none in the DDS**: only J10, J11 and the resistor options |
| Flags | the OPA564's current-limit and thermal flags end on unfitted pull-ups and reach no GPIO; the firmware reports them as `null`. Thermal shutdown is silent |
| Idle current | 39 mA at TX_EN = 1 against 5 mA shut down: keep TX_EN low between pulses |

**AD9834 protocol (datasheet, "Programming the AD9834").** 16-bit words, MSB first, FSYNC low per word, data clocked on the falling SCLK edge with SCLK high when FSYNC falls = **SPI mode 2**, 10 MHz. PIN/SW = 0 on this board (the RESET and SLEEP pins are strapped low, FSELECT to ground), so reset, sleep, frequency select and phase select are **register bits**. Control word (DB15:14 = 00): B28 (bit 13) = 1 for two-word frequency writes · FSEL (11) · PSEL (10) · PIN/SW (9) = 0 · RESET (8) · SLEEP1 (7) · SLEEP12 (6) · OPBITEN, SIGN/PIB, DIV2, MODE = 0. FREQ0 = `0x4000 | 14 bits` written LSBs then MSBs; FREQ1 = `0x8000 | …`; PHASE0 = `0xC000 | 12 bits`, PHASE1 = `0xE000 | 12 bits` (0.088° per step). f = MCLK × word / 2²⁸. Start-up: control `0x2100` (B28 + RESET), FREQ0 low word, FREQ0 high word, PHASE0, PHASE1, control `0x2000` (RESET off: the carrier runs). Phase switch during a sequence: one control word, `0x2000` (PHASE0) or `0x2400` (PHASE1). RESET zeroes the phase accumulator and parks the output at midscale without clearing the registers; SLEEP1 + SLEEP12 (`0x20C0`) stops the clock and powers the DAC down for an idle console. The carrier is never gated at the DDS; TX_EN gates the power stage, so the phase reference survives between pulses. **Consecutive 28-bit writes to the same frequency register are not allowed** while the output runs: for a live retune write the other register and flip FSEL (the class firmware always rewrites FREQ0, which is harmless only under RESET or SLEEP).

```cpp
static void ddsWord(uint16_t w) { digitalWrite(PIN_DDS_FSYNC, LOW); SPI.transfer16(w); digitalWrite(PIN_DDS_FSYNC, HIGH); }
void ddsStart(double hz) {                                 // after SPI.begin(); PSEL pin held low
  uint32_t w = (uint32_t)llround(hz * 268435456.0 / 50e6);
  SPI.beginTransaction(SPISettings(10000000, MSBFIRST, SPI_MODE2));
  ddsWord(0x2100);                                         // B28 = 1, RESET = 1
  ddsWord(0x4000 | (w & 0x3FFF)); ddsWord(0x4000 | ((w >> 14) & 0x3FFF));
  ddsWord(0xC000); ddsWord(0xE000 | 1024);                 // PHASE0 = 0°, PHASE1 = 90°
  ddsWord(0x2000);                                         // RESET = 0: carrier runs
  SPI.endTransaction();
}
void txPulse(uint32_t t_us, uint32_t dead_us) {            // RX blanked first; levels set LOW before pinMode(OUTPUT)
  digitalWrite(PIN_RX_BLANK, LOW); delayMicroseconds(20);
  int64_t t0 = esp_timer_get_time(); digitalWrite(PIN_TX_EN, HIGH);
  while (esp_timer_get_time() - t0 < t_us) {}
  digitalWrite(PIN_TX_EN, LOW);
  int64_t t1 = esp_timer_get_time(); while (esp_timer_get_time() - t1 < dead_us) {}
  digitalWrite(PIN_RX_BLANK, HIGH);                        // receive
}
```

**OPA564 rules.** Supply order USB first (VDIG = +3V3), then +VEXT; the reverse damages the part. E/S has an internal 100 kΩ pull-up against the board's 10 kΩ pull-down, so an undriven GPIO40 means shut down. Use the follower setting (J10 open) only into a resistive dummy load, not into a tuned coil (input differential at turn-off not determined).

**Class firmware.** Driver `Ad9834` (`begin`, `setFrequency`, `setPhase`, `setReset`, `selectPhase`, `sleep`); block `nmr`: `config`, `start`, `abort`, `pulse {t_us}`, `clock {clk, hz}`, `dds {hz, phase0_deg, phase1_deg, psel, on}`, `blank`, `get_record`; the sequencer runs on a core-1 task (section 9). State: compiles in both builds, **never run on a board**. The `clock` command does not refuse CLK0 above 50 MHz.

### 8.10 Coil switches: field-cycling H-bridge and the polarizer (rear terminals)

```
J901 (+VEXT in, 7–18 V) → 5 A fuse → 26 V TVS → reverse-polarity P-FET → +VEXT
H-bridge: GPIO9 HB_IN1, GPIO14 HB_IN2 (10 k pull-downs) → DRV8871 (VM = +VEXT, ILIM 32 kΩ → 2.0 A) → J903 pins 1, 2
Polarizer: GPIO47 FET_GATE (10 k pull-down) → UCC27517 (VDD by J12: 1-2 +VEXT, 2-3 +5V_RAW) → AOD4184A → J905: 1 = +VCOIL (external supply +), 2 = COIL (drain), 3 = GND
Flyback fitted: SS54 freewheel diode from COIL to +VCOIL (τ = L/R, about 2.6 ms for the reference coil); SMBJ20A fast-dump option unfitted
```

| IN1 (GPIO9) | IN2 (GPIO14) | DRV8871 |
|---|---|---|
| 0 | 0 | **coast** (outputs high-impedance; sleeps after 1 ms; the reset state) |
| 1 | 0 | forward: OUT1 high, OUT2 low |
| 0 | 1 | reverse |
| 1 | 1 | brake (both outputs low) |

DRV8871: current regulated at 2.0 A by chopping (not a fault); overcurrent at 3.7 A retries after 3 ms; undervoltage below 6.1 V and thermal shutdown recover silently, **no fault pin**; at the 2 A trip point it dissipates about 2.3 W. 3.3 V logic is fine (V_IH 1.5 V). Transitions need no detour through coast (220 ns dead time is built in). Keep +VEXT ≥ 6.5 V or it sits in undervoltage lockout.

Polarizer: FET_GATE = 1 → coil on (UCC27517 IN− is grounded, so OUT follows IN+; a floating input gives OUT low). J12 1-2 is allowed only with +VEXT ≤ 18 V (driver supply and gate rating); J12 open = no drive, coil stays off. The FET is 40 V / 13 A; +VCOIL ≤ 24 V, **no fuse**: the coil supply must limit the current. After switching off, wait at least 5 τ (about 13 ms for the reference coil) before the pulse; the class default of 5 ms leaves about 15 % of the current. To measure the coil current, replace R933 (0 Ω, 2512) by a 10 mΩ shunt and read ISENSE_COIL at J13 with an AI input on ±2.56 V.

```cpp
void coilBegin() { for (int p : {PIN_HB_IN1, PIN_HB_IN2, PIN_FET_GATE}) { digitalWrite(p, LOW); pinMode(p, OUTPUT); } }
void hbridge(bool in1, bool in2) { digitalWrite(PIN_HB_IN1, in1); digitalWrite(PIN_HB_IN2, in2); }
bool polarize(uint32_t ms) {                                // bounded: never returns with the coil on
  if (ms > 10000) return false;
  digitalWrite(PIN_FET_GATE, HIGH); delay(ms); digitalWrite(PIN_FET_GATE, LOW); return true;
}
```

**Class firmware.** Block `b4`: `hbridge {mode off|fwd|rev|brake}`, `polarizer {on}`, both refused with `"nmr scan running"` during a scan; status `hbridge`, `polarizer`. **`polarizer {on:true}` has no time limit**: a dropped WebSocket leaves the coil on until reset. The NMR sequencer's own polarize step is bounded at 10 s and turns the coil off before the pulse; after every scan set it drives FET_GATE and HB_IN1/2 low without telling `b4`, whose status can then be stale.

### 8.11 Indicators

Panel D1 PWR: on with +3V3. D2 WIFI = GPIO43, D3 ACT = GPIO44, through 0 Ω links and 1 kΩ, active high, about 1 mA. These are the ESP32's **UART0** pins: GPIO43 idles high after reset (D2 lit) and flickers with the ROM's boot messages; GPIO44 can be driven by the dev board's USB-UART bridge when that socket is connected. To use them as indicators: `pinMode(PIN_UART0_TX, OUTPUT)` after boot, never use UART0 (the firmware prints to the native USB, so nothing else does), and do not connect the dev board's UART USB socket. The class firmware does not drive them yet. Dev-board RGB LED: WS2812 on GPIO48, `neopixelWrite(PIN_RGB_LED, r, g, b)` or Adafruit_NeoPixel (the class firmware shows the WiFi state: yellow joining, green station, blue access point).

### 8.12 Power rails

| Rail | Source | Nominal | Budget | Feeds |
|---|---|---|---|---|
| +5V_RAW | USB-C or jack via LM66100 | 5 V | 1.5 A polyfuse per input; a USB 2 port gives 0.5 A | dev board, AMS1117, both ±12 V converters, the 5 V buffers, the panel (opto-couplers, module buffer, J40 +5 V) |
| +3V3 | AMS1117 | 3.3 V | 1 A | ADC digital, expander, Si5351, level shifter, **OPA564 logic**, panel OLED/Qwiic/LEDs/opto pull-ups |
| +3V3A, +3V3D | ferrite beads from +3V3 | 3.3 V | — | counter and mixer; DDS |
| +12 V, −12 V | two isolated 2 W converters (B0512S) | ±12 V unregulated, about +5 % at light load | 167 mA each, 17 mA minimum load (bleeders fitted) | the op-amps, the DG419, the input clamps, the 78L05 |
| +5VA | 78L05 from +12 V | 5 V | 100 mA | ADC analog, DAC, DAC level shifter, DG419 logic |
| +VEXT | J901 | 7–18 V | 5 A fuse | **only** the OPA564, the DRV8871 and (J12 1-2) the gate driver |
| +VCOIL | J905 pin 1 | the user's supply, ≤ 24 V | external | the polarizer coil only |

**No rail is measurable by the firmware**: no divider reaches a GPIO or an ADC input, and the ADC's AUX input is grounded. The `b2 rails` status reports constants with `measured: false`. The only indicators are the LEDs D203 (+5V_RAW), D204 (+3V3), D205 (+12 V), D206 (−12 V) and D933 (+VEXT) on the main board.

---
## 9. The reference firmware and its protocol

The class repository's `firmware/` is the reference and the fallback. It is the known working baseline for Project 2 on a bare dev board (the SIM build ran on 2026-09-07) and the starting point for Project 3. Full command tables are in `firmware/PROTOCOL.md`; the NMR contract is `firmware/NMR-FIRMWARE.md`. What follows is the part an author needs every day, taken from the code at commit `6ef1c7c`.

### 9.1 Build, flash, talk to it

| Item | Value |
|---|---|
| Toolchain | PlatformIO, `platform = espressif32 @ ^7.1.1` (Arduino core 2.0.17), board `esp32-s3-devkitc-1`, QIO flash + octal PSRAM, `default_16MB.csv` partitions (two 6.25 MB app slots, 3.4 MB LittleFS) |
| Environments | `esp32s3-sim` (default): `-DSIM=1`, every chip faked, runs on a bare dev board · `esp32s3`: the real board |
| Serial | `Serial` is the chip's native USB (`ARDUINO_USB_CDC_ON_BOOT=1`, `ARDUINO_USB_MODE=1`), which is why the board enumerates as `303A:1001` |
| Libraries | ESPAsyncWebServer, AsyncTCP, ArduinoJson 7, Adafruit NeoPixel |
| Commands | `pio run -d firmware -e esp32s3-sim -t upload` (program) · `pio run -d firmware -e esp32s3-sim -t uploadfs` (the web app; `scripts/copy_pwa.py` copies `host/pwa/` into `firmware/data/` before every build) · add `--upload-port COMx` when needed |
| First flash of a factory-fresh board | it enumerates as `303A:4001` and ignores the automatic reset: hold BOOT, tap RST, release BOOT; it re-enumerates as `303A:1001` on a **new COM port**; flash to that port. Afterwards uploads reset it automatically |
| Reading the port from an agent | `pio device monitor` needs an interactive terminal. Use pyserial with `s.dtr = False; s.rts = False` set **before** `s.open()` and never toggled (toggling can enter download mode). The port disappears and reappears at every reset |
| Network | with `include/secrets.h` (git-ignored; `WIFI_SSID`, `WIFI_PASSWORD`) the board joins that network and opens **no** access point; otherwise, or after 10 s without a connection, it opens the access point `instrument-XXXX` / password `instrument` at 192.168.4.1. mDNS and OTA name: `instrument-XXXX.local` (XXXX = the last four hex digits of the MAC, printed in the boot log). There is no `instrument.local` |
| Boot log | `[boot] class-board firmware 0.1.0 (SIM)`, one `[registry] <name> ready` per block, `[wifi] AP "instrument-XXXX" …` or `[wifi] STA <ip> …`, `[http] server started` |
| OTA | enabled, no password, no `espota` upload environment configured, never used |

### 9.2 Structure

- `main.cpp` boots Serial, LittleFS, registers the blocks in the order `base, b1, b2, b3, b4, b5, nmr, template, alarms`, calls every `begin()` in that order (base first: it starts the SPI lock, I²C, the expander and the clock generator), starts WiFi, mDNS, OTA, the HTTP server (the web app from LittleFS, `GET /api/info`) and the WebSocket at `/ws`.
- `loop()`: every block's `loop()`, OTA, the queued WebSocket requests (at most 32 pending; extra or fragmented messages are dropped without a reply), then every 50 ms the status broadcast. The web server itself runs on the AsyncTCP task.
- **A block** is one class with `name() / begin() / loop() / handle(cmd, reply) / status(out)` in `src/blocks/<id>/`, registered by one line in `main.cpp`, with one panel file `host/pwa/panels/<id>.js` and one entry in `PANELS` in `app.js`. All block code runs on the main task, so blocks need no locks for their own state; a block never calls another block; under `SIM` it fakes its hardware. Copy `src/blocks/template/` to start a new one. The alarm engine is the one cross-block actor (`module:N:on|off` actions on `b4`).
- `blocks/Busy.h`: `g_nmrBusy` is set while a scan runs; `b4` refuses `hbridge` and `polarizer` then.
- `net/WsOut.h`: `wsBinaryAll(data, len)` is the only way to send a binary frame, **from the main task only**; a worker task sets a flag and the block's `loop()` sends.

### 9.3 Drivers (`src/drivers/`), one global instance each

| Instance | Started by | Public methods |
|---|---|---|
| `spibus` (namespace) | `base` | `begin()`, `lock(ms)`, `unlock()`, `Guard g(ms)` with `g.ok`. A recursive FreeRTOS mutex around SPI2. Every SPI transaction sits inside a Guard; periodic readers use `Guard g(0)` and skip the pass when the bus is busy; the NMR capture holds it for the whole burst |
| `Tca9535 expander` | `base` | `begin(addr)`, `writePort(port, v)`, `writeBit(port, bit, level)`, `cached(port)`, `setInputs(port, mask)`, `readPort(port, v)`, `present()`, `pulseJohnsonClear()` |
| `Si5351 clockgen` | `base` | `begin(addr, xtal_hz)`, `setClk0(hz)`, `setClk1(hz)`, `actualClk0()`, `actualClk1()`, `enable(clk, on)`, `resetPllB()`, `present()` |
| `Ad9834 dds` | `nmr` | `begin(mclk_hz)`, `setFrequency(hz)`, `actualFrequency()`, `setPhase(reg, deg)`, `setReset(on)`, `selectPhase(p1)`, `sleep(on)`; takes the SPI lock itself (mode 2, 10 MHz) |
| `Ads8688 adc` | `b1` | `begin()`, `setRange(ch, code)`, `range(ch)`, `readManual(ch)`, `toVolts(ch, raw)`, `burst(mask, out, n, rate_hz, &achieved)`, `present()`; mode 1, 17 MHz requested (16 MHz actual); `readManual` and `burst` require the caller to hold the lock |

There is no DAC8563 driver (section 8.2). In SIM every driver reports itself present and returns plausible values; in the real build on a bare dev board `present()` is false and the blocks answer `"expander not present"`, read 0 V, or end an NMR scan in `error`.

### 9.4 The WebSocket protocol in one screen

One WebSocket at `ws://<host>/ws`. Text frames are JSON; binary frames carry records.

```json
{"id": 7, "block": "b5", "cmd": "dio", "args": {"n": 3, "level": true}}      ← request, one per message
{"id": 7, "ok": true, "result": {"mask": 4}}                                   ← reply to that client only
{"id": 7, "ok": false, "error": "expander not present"}
{"type": "hello", "fw": "0.1.0", "sim": true, "blocks": ["base","b1","b2","b3","b4","b5","nmr","template","alarms"]}   ← on connect
{"type": "status", "t": 123456, "blocks": {"base": {...}, "b1": {"ai1": 3.91, ...}, ...}}   ← every 50 ms to everyone
```

Replies have no `type`; broadcasts do. Numeric top-level status keys are what the app's chart plots and what alarm rules test. `GET /api/info` returns `{fw, sim, mac, blocks}` for scripts without a WebSocket.

| Block | Commands | Status keys |
|---|---|---|
| `base` | `led {r,g,b}` · `brightness {value}` · `counter_reset` · `info` | `counter, temp_c, uptime_s, rssi, heap_free, clients` (stations on the access point), `led{}` |
| `b1` | `read_all` · `set_range {ch 1..8, range}` | `ai1…ai8`, `range` |
| `b2` | `rails` | `v5_raw, v3v3, v12p, v12n, v5a, measured` (constants; nothing is measurable) |
| `b3` | `set_dc {ch, volts}` · `sine {ch, freq, amp, offset}` · `off {ch}` | `ao1, ao2, mode1, mode2` (stub below the command layer) |
| `b4` | `module {n 1..7, on}` · `module_all {on}` · `opto_reset` · `hbridge {mode}` · `polarizer {on}` | `module1…module7, opto1, opto2, opto1_level, opto2_level, hbridge, polarizer` |
| `b5` | `dio {n, level}` · `dio_mask {mask}` · `trig_dir {out}` · `trig {level}` · `fast_out {n, freq_hz}` (stub) | `dio, dio1…dio8, trig_dir, trig, fast1_hz, fast2_hz` |
| `nmr` | `config {…}` · `start` · `abort` · `pulse {t_us}` · `clock {clk, hz}` · `dds {hz, phase0_deg, phase1_deg, psel, on}` · `blank {receive}` · `get_record` · `sim_larmor {hz}` (SIM) | `state, scan, n_avg, f_tx_hz, f_lo_hz, if_hz, rate_hz, peak_hz, larmor_hz, peak_amp, snr_db, i_flag, t_flag, error, sim` |
| `alarms` | `list` · `add {block, key, op, threshold, action}` · `remove {id}` · `clear` | `rules, active` |
| `template` | `set_value {value}` | `value, setpoint` |

Binary frame, 28-byte little-endian header then payload: `uint8 kind, uint8 block_id, uint8 ch, uint8 bits, uint32 t_ms, uint32 rate_hz, uint32 n, int32 trig_index, float32 volts_per_lsb, float32 offset_v`. Only **kind 3** exists today: the averaged NMR record, `n` pairs of float32 I, Q in volts at the ADC input, `rate_hz` = the decimated rate, `trig_index` = scans averaged so far, `offset_v` = the IF in hertz. The streaming and capture frames (kinds 1 and 2) of `PROTOCOL.md` §6 are specified, not implemented. The Python client `host/instrument.py` (`pip install -e host/`) and the web app `host/pwa/` speak this protocol and work as test clients for any firmware that keeps it.

NMR `config` settings and limits: `f_tx_hz` (default 89400), `f_lo_hz` (84000), `sequence` fid|echo, `t90_us` 417, `t180_us` 834, `tau_us`, `t_blank_pre_us` 20, `t_dead_us` 1000, `t_acq_start_us` 1200, `t_acq_ms` 2000 (≤ 4000), `rate_hz` 100000 (≤ 250000 per channel), `decim` 4 (the decimated rate must exceed twice the IF), `n_avg` 1..256, `cyclops`, `t_repeat_ms` 3000, `polarize_ms` ≤ 10000, `t_polarize_settle_ms` 5, `hb_mode`. A scan: phase registers loaded · RX blanked · TX_EN high for t90 · dead time · RX open · ADC burst of AIN_3 and AIN_2 into PSRAM · RX blanked · DC offset, decimation, CYCLOPS rotation, running mean · one kind-3 frame to every client.

### 9.5 What has run and what has not

| Part | SIM build on a bare dev board | Real build on the class board |
|---|---|---|
| WiFi, mDNS, HTTP, WebSocket, status broadcast, `base`, the web app, `instrument.py` | ran on 2026-09-07 (the pre-v0.7 build; those code paths are unchanged) | never (no board yet) |
| Alarm rules and their persistence | ran pre-v0.7 | never |
| `b1` ADC, `b4` modules and coil switches, `b5` DIO and TRIG, the drivers, the `nmr` block, binary frames | compile; no record of a run on any board | never: register sequences from the datasheets, unmeasured |
| `b3` DAC, `b5` fast outputs, opto interrupt counter | command layer only | **stubs** |

The class repository's `CLAUDE.md` says the same: every `#ifndef SIM` branch is a hypothesis until `hardware/docs/bring-up.md` records a measurement.

### 9.6 Starting your own firmware (Project 3)

The class firmware is not packaged as a library, so **copy** the parts you need into your repository and note the class commit you copied from:

```
firmware/platformio.ini                 both environments and the memory settings
firmware/include/pins.h                 the only source of pin numbers
firmware/include/secrets.h.example      the template; secrets.h stays git-ignored
firmware/src/main.cpp                   WiFi, mDNS, OTA, WebSocket, queue, broadcast
firmware/src/net/WsOut.h
firmware/src/blocks/Block.h Registry.h Registry.cpp Busy.h Busy.cpp
firmware/src/blocks/base/               starts the SPI lock, I²C, the expander, the clock generator
firmware/src/drivers/                   all five driver pairs
firmware/src/blocks/<what your instrument needs>
firmware/src/alarm/                     if you want alarm rules
```

Add `firmware/.pio/`, `firmware/include/secrets.h` and `firmware/data/` to `.gitignore`; register only the blocks you copied, `base` first; keep `host/pwa/` next to `firmware/` or change the path in `scripts/copy_pwa.py`.

**Keep as they are:** `pins.h` with `kAinOfAi` and `EXP_BIT_MOD`; the drivers and the SPI-lock discipline; the expander's outputs-before-configuration start; the safe-level-then-`pinMode` order for the five console pins; RX_BLANK low by default and TX_EN low except in a pulse; the CLK1 → PLLB reset → counter clear order; `wsBinaryAll` from the main task only; no `delay()` in a block (long timing belongs on a task like the sequencer, which never touches the network); the `#ifdef SIM` branches so you can build on a bare dev board until the boards arrive. **Yours to replace:** the protocol, the block names, the app, the WiFi logic and the LED colours. If you keep the class protocol, the class web app and `instrument.py` are ready-made test clients.

---

## 10. Known defects and open points (2026-10-08)

Found while writing this document by comparing the code with the datasheets and the netlist. None has been fixed yet.

**Reference firmware and app**

1. **The `alarm` broadcast is never sent**: `main.cpp` never installs the engine's notify callback, so a `notify` action shows nothing in the app.
2. **The Section C panel (`host/pwa/panels/b4.js`) sends `relay`/`relay_all` and reads `relay1..4`**; the firmware has `module`/`module_all`/`module1..7`. Every button on that tab fails with "unknown cmd"; no controls exist for the H-bridge or the polarizer. The alarm actions `relay:N:on|off` offered by `alarms.js`, `b1.js` and `instrument.py` are ignored by the engine (only `module:` acts). Alarm rules on boolean keys never fire (ArduinoJson does not count a boolean as a number).
3. **DAC8563 and fast outputs are stubs** (sections 8.2, 8.4); the opto inputs are polled at 10 Hz (8.6).
4. **Start-up race on the DAC chip select**: GPIO5 is driven high only in `b3`'s `begin()`, after `b1` has clocked about 280 SPI cycles into the ADC with the DAC's /SYNC floating. Drive GPIO5, GPIO10 and GPIO41 high before the first SPI transfer (for example in `spibus::begin()`), or add a 10 kΩ pull-up to CS_DAC in the next revision.
5. `trig_dir` makes GPIO38 an output before raising DIR (two drivers on one line for a moment); `set_range` accepts the non-existent range codes 3 and 4; `b4 polarizer` has no time limit; the NMR sequencer's ADC burst busy-waits on core 1 and starves the main loop (no status, no `abort`) for `t_acq_ms`; after a scan the sequencer drives FET_GATE and HB_IN1/2 low without updating `b4`'s status; the expander cache is shared by two tasks without a lock.
6. `Ad9834::setFrequency` always rewrites FREQ0 (forbidden for consecutive writes while the output runs; harmless under RESET, as the sequencer uses it); `nmr clock` accepts CLK0 above the AD9834's 50 MHz; the `Ad9834.h` comment says 75 MHz.
7. **Scan-to-scan phase**: the DDS and the LO share the Si5351 crystal, but each scan starts after a `vTaskDelay` on the ESP32's own clock, so the IF phase of each record is effectively random (period 185 µs at 5.4 kHz). The firmware averages the complex records directly, which attenuates the signal along with the noise and defeats CYCLOPS. Remedies to choose from: estimate and remove each scan's phase from its own data before averaging, re-establish a common time origin in hardware each scan, or average magnitude spectra. A design decision and a bench test are needed.
8. Documentation: `PROTOCOL.md` and `instrument.py` say `instrument.local` (the name is `instrument-XXXX.local`); the block list in `PROTOCOL.md` omits `nmr`; `NMR-FIRMWARE.md` §2.5 describes an ADC driver that differs from the code; workbook chapter B presents the Scope tab and streaming as existing; `hardware/README.md` describes the September design.

**Hardware, as ordered**

9. **The two LM66100s do not OR the 5 V inputs** (chip-enable on ground = always on, no reverse-current blocking): one 5 V source at a time. Next revision: each chip-enable to the other input, or to the output.
10. **J3 must always carry a shunt** (no feedback otherwise); the schematic note that R712 is permanent is wrong. J11 and J12 likewise need a shunt to do anything.
11. Receiver gains differ from the design notes: stage 2 is 10.1 (not 11), the difference amplifiers give 10 (not 20), so the ADC sees about half the designed amplitude. No loss of sensitivity; adjust expectations and the SIM.
12. The transmitter at gain 25 clips below about 16–17.5 V of +VEXT; the DDS level is about 0.6 V pp (the design note's 3.18 mA uses a 1.20 V reference, the datasheet's formula 1.15 V).
13. TRIG_DIR, DDS_PSEL and FAST_OUT1/2 have no pull resistors: undefined from reset until the firmware runs. A pull-down on TRIG_DIR would make "input" the hardware default.
14. The OPA564's current-limit and thermal flags reach no GPIO (the pull-ups R811/R812 are unfitted and there is no spare expander line); thermal shutdown is invisible to the firmware.
15. Panel LEDs WIFI and ACT sit on UART0 (8.11). The J905 legend is printed in the reverse order of its pins (6.1). J901 has no +/− marks. J411 has no "ISO IN 1" legend.
16. A reversed supply on J901 forward-biases the TVS and blows the 5 A fuse. The ±12 V rails cannot sink current, so several overdriven AI inputs raise them. FAST and TRIG into 50 Ω exceed their drivers' ratings. MOD outputs are not short-proof.
17. Not determined until measured: the ADC rate the burst reaches; whether +5VA lets AO reach +10 V; the isolated inputs' exact threshold; the FAST outputs' usable frequency; whether the dev board has a blocking diode on its 5 V pin and series resistors on GPIO43/44.

**Stale text an assistant will meet** (ignore it): in the `.kicad_sch` notes and `hardware/README.md`, the AGND net and net tie NT1, an expansion header J5, Qwiic J4, solder jumpers JP1/JP2/JP101/JP102/JP70x/JP802/JP904, resistor arrays RN521/RN522, 17 SMA with a spare and TP1, module outputs on J8 pins 19–33, OPTO_IN on J8 pins 35/37, TX on link pins 19/21 or J6.32, link pins 37–40 = RX/AGND/TX/AGND, a pairwise pad swap on the panel headers, the D-19 channel map (AI1→AIN_6), the OPA564 flags on TCA9535 P1.5/P1.6, "PIN/SW = 1", the 6N137 on +3V3, a main-board TX terminal, an AD9834 with 75 MHz (the fitted BRUZ grade is a 50 MHz part). The main PCB also has a copper zone named `AGND_B` that is on the TX net.

---

## 11. Sources

- Netlists: `kicad-cli sch export netlist --format kicadxml` of `hardware/class-board.kicad_sch` and `hardware/front-panel/front-panel.kicad_sch` at commit `6ef1c7c`; positions and silkscreen from the two `.kicad_pcb` files; BOMs from `kicad-cli sch export bom`.
- Firmware: `firmware/` at the same commit (last source change 2026-09-30).
- Datasheets, cited by section in the text: TI ADS8688 (SBAS582C), DAC8563 (SLAS719E), TCA9535 (SCPS201F), SN74AHCT541 (SCLS269Q), SN74LVC1T45 (SCES515N), OPA564 (SBOS372E), OPA1656 (SBOS901C), OPA1612 (SBOS450C), OPA2192, TS5A23157 (SCDS165F), DRV8871 (SLVSCY9B), UCC27517 (SLUSAY4D), LM66100 (SLVSEZ8A), LM78L05 (SNVS754O); Nexperia 74HCT125 Rev. 8; Vishay DG419 (70051 Rev. G); Skyworks Si5351A/B/C Rev 1.3 and AN619 Rev 0.8; Analog Devices AD9834 Rev. D; Lite-On 6N137 (DS70-2008-0035 B); Solomon Systech SSD1306 Rev 1.1; AOS AOD4184A, AOD4185; Mornsun B_S-2WR3; Advanced Monolithic AMS1117; Espressif ESP32-S3 datasheet v2.2 and the DevKitC-1 user guide. Links in `docs/references.md`.
- The detailed working notes behind this document (connectivity tables, chip-by-chip datasheet extracts, the firmware audit, the signal-path derivations) are kept in the course repository under `notes/2026-10-08-board-reference/`.
