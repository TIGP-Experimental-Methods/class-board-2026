# Link pinout: main board J6/J7/J8 to front panel J1/J3/J2

Generated from the KiCad netlists of class-board-2026 commit 6ef1c7c (the boards as ordered on 2026-10-05). The main board's J6–J8 are 2×20 female sockets on its back face; the panel's J1–J3 are 2×20 male headers on its inner face. With the panel mirrored onto the main board (panel x = 180 − main x) **pin n mates pin n** on every link. Net names are shown without their sheet prefix; n/c = not connected.

## Main J6 = panel J1 (analog: AI1–AI8, AO1/AO2, RX, AUX, TX)

| Pin | Main-board net | Panel net | Same? |
|---|---|---|---|
| 1 | GND | GND | yes |
| 2 | n/c | n/c | yes |
| 3 | GND | GND | yes |
| 4 | n/c | n/c | yes |
| 5 | GND | GND | yes |
| 6 | n/c | n/c | yes |
| 7 | GND | GND | yes |
| 8 | n/c | n/c | yes |
| 9 | GND | GND | yes |
| 10 | TX | TX | yes |
| 11 | GND | GND | yes |
| 12 | TX | TX | yes |
| 13 | n/c | GND | **no** |
| 14 | n/c | n/c | yes |
| 15 | GND | GND | yes |
| 16 | AO2 | AO2 | yes |
| 17 | GND | GND | yes |
| 18 | AO1 | AO1 | yes |
| 19 | GND | GND | yes |
| 20 | RX | RX | yes |
| 21 | GND | GND | yes |
| 22 | AUX | AUX | yes |
| 23 | GND | GND | yes |
| 24 | AI8 | AI8 | yes |
| 25 | GND | GND | yes |
| 26 | AI7 | AI7 | yes |
| 27 | GND | GND | yes |
| 28 | AI6 | AI6 | yes |
| 29 | GND | GND | yes |
| 30 | AI5 | AI5 | yes |
| 31 | GND | GND | yes |
| 32 | n/c | n/c | yes |
| 33 | GND | GND | yes |
| 34 | AI4 | AI4 | yes |
| 35 | GND | GND | yes |
| 36 | AI3 | AI3 | yes |
| 37 | GND | GND | yes |
| 38 | AI2 | AI2 | yes |
| 39 | GND | GND | yes |
| 40 | AI1 | AI1 | yes |

## Main J7 = panel J3 (power, isolated inputs, module outputs)

| Pin | Main-board net | Panel net | Same? |
|---|---|---|---|
| 1 | +5V_RAW | +5V_RAW | yes |
| 2 | GND | GND | yes |
| 3 | +5V_RAW | +5V_RAW | yes |
| 4 | GND | GND | yes |
| 5 | +3V3 | +3V3 | yes |
| 6 | GND | GND | yes |
| 7 | n/c | n/c | yes |
| 8 | GND | GND | yes |
| 9 | n/c | n/c | yes |
| 10 | GND | GND | yes |
| 11 | n/c | n/c | yes |
| 12 | GND | GND | yes |
| 13 | n/c | n/c | yes |
| 14 | GND | GND | yes |
| 15 | OPTO_IN1 | OPTO_IN1 | yes |
| 16 | GND | GND | yes |
| 17 | OPTO_IN2 | OPTO_IN2 | yes |
| 18 | GND | GND | yes |
| 19 | n/c | n/c | yes |
| 20 | GND | GND | yes |
| 21 | n/c | n/c | yes |
| 22 | GND | GND | yes |
| 23 | MOD1 | MOD1 | yes |
| 24 | GND | GND | yes |
| 25 | MOD2 | MOD2 | yes |
| 26 | GND | GND | yes |
| 27 | MOD3 | MOD3 | yes |
| 28 | GND | GND | yes |
| 29 | MOD4 | MOD4 | yes |
| 30 | GND | GND | yes |
| 31 | MOD5 | MOD5 | yes |
| 32 | GND | GND | yes |
| 33 | MOD6 | MOD6 | yes |
| 34 | GND | GND | yes |
| 35 | MOD7 | MOD7 | yes |
| 36 | GND | GND | yes |
| 37 | n/c | n/c | yes |
| 38 | GND | GND | yes |
| 39 | n/c | n/c | yes |
| 40 | GND | GND | yes |

## Main J8 = panel J2 (digital: TTL1–8, LEDs, +3V3, I²C, TRIG, FAST1/2)

| Pin | Main-board net | Panel net | Same? |
|---|---|---|---|
| 1 | TTL8 | TTL8 | yes |
| 2 | GND | GND | yes |
| 3 | TTL7 | TTL7 | yes |
| 4 | GND | GND | yes |
| 5 | TTL6 | TTL6 | yes |
| 6 | GND | GND | yes |
| 7 | TTL5 | TTL5 | yes |
| 8 | GND | GND | yes |
| 9 | TTL4 | TTL4 | yes |
| 10 | GND | GND | yes |
| 11 | TTL3 | TTL3 | yes |
| 12 | GND | GND | yes |
| 13 | TTL2 | TTL2 | yes |
| 14 | GND | GND | yes |
| 15 | TTL1 | TTL1 | yes |
| 16 | GND | GND | yes |
| 17 | n/c | n/c | yes |
| 18 | GND | GND | yes |
| 19 | n/c | n/c | yes |
| 20 | GND | GND | yes |
| 21 | n/c | n/c | yes |
| 22 | GND | GND | yes |
| 23 | LED_ACT | LED_ACT | yes |
| 24 | GND | GND | yes |
| 25 | LED_WIFI | LED_WIFI | yes |
| 26 | GND | GND | yes |
| 27 | +3V3 | +3V3 | yes |
| 28 | GND | GND | yes |
| 29 | +3V3 | +3V3 | yes |
| 30 | GND | GND | yes |
| 31 | I2C_SCL | I2C_SCL | yes |
| 32 | GND | GND | yes |
| 33 | I2C_SDA | I2C_SDA | yes |
| 34 | GND | GND | yes |
| 35 | TRIG_5V | TRIG_5V | yes |
| 36 | GND | GND | yes |
| 37 | FASTTTL2 | FASTTTL2 | yes |
| 38 | GND | GND | yes |
| 39 | FASTTTL1 | FASTTTL1 | yes |
| 40 | GND | GND | yes |
