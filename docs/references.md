# Reference material for the projects

Papers, datasheets and links that the class board and the projects build on. The two PDFs in
[`references/`](references/) are published under Creative Commons licences, so they may be copied here;
everything else is a link to the publisher or manufacturer.

## NMR at the Earth's field — the physics and the two designs the class board follows

| What | Why it matters for you | Where |
|---|---|---|
| **Libbrecht, K. G. — "Notes from the Physics Teaching Lab: NMR Experiments at 21 Gauss"** (arXiv:2508.10738, 2025, CC BY-SA 4.0) | The clearest walk-through of a low-field proton NMR teaching experiment: coil, polarisation, free-induction decay, T1/T2, signal-to-noise. Read this first. | [PDF in this repository](references/Libbrecht-2025-NMR-experiments-at-21-gauss-arXiv-2508.10738.pdf) · [arXiv](https://arxiv.org/abs/2508.10738) |
| **Tayler, M. C. D. and Bodenstedt, S. — "NMRduino: A modular, open-source, low-field magnetic resonance platform"**, J. Magn. Reson. 362, 107665 (2024), CC BY 4.0 | An open-source sub-MHz spectrometer built from a microcontroller, a DDS and a power stage — the same architecture as our board (Si5351/AD9834 clock and DDS, OPA564 transmitter, OPA1656 receiver, commutating mixer). Their design files and firmware are on Zenodo and GitHub. | [PDF in this repository](references/Tayler-Bodenstedt-2024-NMRduino-JMR-362-107665.pdf) · [DOI 10.1016/j.jmr.2024.107665](https://doi.org/10.1016/j.jmr.2024.107665) |
| **Michal, C. A. — "A low-cost spectrometer for NMR measurements in the Earth's magnetic field"**, Meas. Sci. Technol. 21, 105902 (2010) | The classic Earth's-field spectrometer: coil design, pre-polarisation, receiver noise budget. Publisher copyright, so only the link; the Academia Sinica library has access. | [DOI 10.1088/0957-0233/21/10/105902](https://doi.org/10.1088/0957-0233/21/10/105902) |

How the board implements this: [`hardware/docs/design-decisions.md`](../hardware/docs/design-decisions.md)
(the design record, D-1 … D-6x) and [`firmware/NMR-FIRMWARE.md`](../firmware/NMR-FIRMWARE.md) (pulse sequence, I/Q detection, the
scan protocol). Bring-up tests: [`hardware/docs/bring-up.md`](../hardware/docs/bring-up.md).

## Datasheets of the parts on the class board

Read a datasheet the way the workshop showed: pinout and absolute maximum ratings first, then the one section that
concerns your circuit. The part names below are the manufacturer part numbers; the same names appear on the schematic.

| Part | What it does on the board | Datasheet |
|---|---|---|
| ESP32-S3-DevKitC-1 | the microcontroller module (Wi-Fi, USB, all control) | [Espressif user guide](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide.html) · [ESP32-S3 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf) |
| ADS8688IDBTR | 8-channel 16-bit ADC, ±10.24 V inputs (AI1 … AI8) | [TI](https://www.ti.com/lit/ds/symlink/ads8688.pdf) |
| DAC8563SDGSR | dual 16-bit DAC behind the ±10 V outputs AO1/AO2 | [TI](https://www.ti.com/lit/ds/symlink/dac8563.pdf) |
| OPA2192IDR | precision op-amp: the ±10 V output stages | [TI](https://www.ti.com/lit/ds/symlink/opa2192.pdf) |
| AD9834BRUZ | DDS waveform generator: the NMR transmit frequency | [Analog Devices](https://www.analog.com/media/en/technical-documentation/data-sheets/AD9834.pdf) |
| SI5351A-B-GT | I2C clock generator: DDS clock and receiver local oscillator | [Skyworks](https://www.skyworksinc.com/-/media/Skyworks/SL/documents/public/data-sheets/Si5351-B.pdf) |
| OPA564AIDWPR | 1.5 A power op-amp: drives the NMR coil | [TI](https://www.ti.com/lit/ds/symlink/opa564.pdf) |
| OPA1656IDR | low-noise op-amp: the receiver preamplifier | [TI](https://www.ti.com/lit/ds/symlink/opa1656.pdf) |
| OPA1612AIDR | low-noise op-amp: mixer buffers and difference amplifiers | [TI](https://www.ti.com/lit/ds/symlink/opa1612.pdf) |
| TS5A23157DGSR | dual analog switch: the commutating mixer | [TI](https://www.ti.com/lit/ds/symlink/ts5a23157.pdf) |
| DG419DY-T1-E3 | analog switch: receiver blanking | [Vishay](https://www.vishay.com/docs/70051/dg417.pdf) |
| DRV8871DDAR | H-bridge: the field-cycling coil | [TI](https://www.ti.com/lit/ds/symlink/drv8871.pdf) |
| UCC27517DBVR + AOD4184A | gate driver and MOSFET: the polariser switch | [TI](https://www.ti.com/lit/ds/symlink/ucc27517.pdf) · [LCSC C99124](https://www.lcsc.com/product-detail/C99124.html) |
| TCA9535PWR | I2C port expander: the eight digital outputs and the module outputs | [TI](https://www.ti.com/lit/ds/symlink/tca9535.pdf) |
| SN74AHCT541PWR | 5 V TTL buffer for the digital outputs (main board and front panel) | [TI](https://www.ti.com/lit/ds/symlink/sn74ahct541.pdf) |
| 74HCT125PW | 3-state buffers: the fast outputs and the DAC level shift | [Nexperia](https://www.lcsc.com/datasheet/lcsc_datasheet_2407241026_Nexperia-74HCT125PW-118_C131316.pdf) |
| SN74LVC1T45DBVR | bidirectional level translator: the TRIG line | [TI](https://www.ti.com/lit/ds/symlink/sn74lvc1t45.pdf) |
| 6N137S-TA1-L | optocoupler: the two isolated inputs on the front panel | [Lite-On](https://www.lcsc.com/datasheet/lcsc_datasheet_1810161120_Lite-On-6N137S-TA1-L_C92651.pdf) |
| LM66100DCKR | ideal-diode controller: USB and jack power ORing | [TI](https://www.ti.com/lit/ds/symlink/lm66100.pdf) |
| B0512S-2WR3 | isolated 5 V → 12 V converters: the ±12 V rails | [YLPTEC](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2304271700_YLPTEC-B0512S-2WR3_C5369475.pdf) |
| AMS1117-3.3 · 78L05G-AB3-R | 3.3 V and analog 5 V regulators | [AMS1117](https://www.lcsc.com/datasheet/lcsc_datasheet_2410121508_Advanced-Monolithic-Systems-AMS1117-3-3_C6186.pdf) · [78L05](https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_UTC-Unisonic-Tech-78L05G-AB3-R_C71136.pdf) |
| BWSMA-KE-Z001 | the SMA connectors on the front panel | [LCSC](https://www.lcsc.com/datasheet/lcsc_datasheet_2405210917_BAT-WIRELESS-BWSMA-KE-Z001_C496549.pdf) |

## Tools and suppliers

- KiCad documentation: <https://docs.kicad.org/> — the schematic and PCB editors we use in Workshop 2 and 3.
- JLCPCB: <https://jlcpcb.com/> (boards and assembly; the parts library is <https://jlcpcb.com/parts>) and LCSC: <https://www.lcsc.com/> (the same parts, retail).
- PlatformIO: <https://docs.platformio.org/> — how the firmware is built and flashed (see [`SETUP.md`](../SETUP.md)).
- The course website with slides and the project wall: <https://tigp-experimental-methods.github.io/>.

Licences of the copied papers: Libbrecht 2025 — [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/);
Tayler and Bodenstedt 2024 — [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Both are unchanged copies of the authors' versions.
