# Chapter 4 — Assembly, then the project presentation and demonstration (26–30 Oct)

**Collect the manufactured PCBs and housings around Fri 16 Oct. Assemble your ESP32, PCB and housing. Test and refine your firmware and app. Then present and demonstrate your project, app, website and video — 26–30 Oct, about 15 minutes each.**

**Assessment** is based on the project: 20 % hardware demonstration · 30 % app/software demonstration · 30 % presentation · 20 % project website.

## Bring-up checklist (instructor, before the boards are handed out — you do not repeat it, but read it)
Rails at the test points (+5V, +3V3, ±12 V, +5VA) with no dev board → dev board in, LED blue, AP (the board's own WiFi network) up, app opens → `esp32s3` build flashed (written onto the board over USB; no SIM — the firmware talks to real hardware instead of faking it) → each block's smoke test: B1 AI1 reads a known voltage · B2 rail LEDs · B3 AO1 sine seen on a scope · B4 relay 1 clicks, opto 1 counts · B5 DIO1 toggles on a scope.

## Exercise E13 — assemble and measure — `/tutor WRAP`
- [ ] **E13a Assemble and run on real hardware.** Board into its housing, dev board on the *USB* port. Build **without SIM**, one command per line: `pio run -e esp32s3 -t upload`, then `pio run -e esp32s3 -t uploadfs`. Open your panel. See your block move real hardware:
  B1 a voltage on AI1 · B2 rail LEDs and your status panel · B3 a sine on AO1 into AI1 · B4 relay click and an opto count · B5 a TTL line and TRIG direction.
  Fix one thing with the tutor (there is always one thing). Commit (save a snapshot with a one-line message).
- [ ] **E13b One measured number.** Your block page says which; your plan says what you expected. Measure it, write the value **and the method** under the expectation:
  B1 noise floor of one input (LSB rms, 4000-sample capture, SMA terminated) · B2 the four rail voltages + USB current · B3 amplitude accuracy of a 1 kHz sine at ±5 V · B4 relay switching time from an opto timestamp · B5 TTL edge rate on a scope.
  Expected vs measured, and one sentence on the difference. That sentence is the physics.
- [ ] **E13c A video describing your app or board (optional, recommended).** Your panel on the phone, your block doing its thing, the number on the scope or multimeter, your name and block at the start. A phone video is fine; so is the lab's `show-your-work` `education-video` route (script, narration, pictures from your plan), posted on your own YouTube channel. Link it from your project website. It is also your safety net: if the live part fails in the demonstration, play the video.

**Deliverables:** the measured number with its method, in your repository; the project websites and their cards on the class project wall (https://tigp-experimental-methods.github.io/showcase-2026/) brought up to date with the assembled instrument — a picture or video of the real board, the `updated` date; the video, if you made one, linked from them. Project 3 — your board section, its firmware and app panel, and the housing — is **one** repository, one project website and one card (`project` `"3"`), not separate sites for the board and the housing.

## Exercise E14 — the presentation and demonstration (`/tutor DEMO` to rehearse)
About 15 minutes each, 26–30 Oct. Present and demonstrate your project, app, website and video. **A suggested structure** — use it, or your own:
1. **Who you are, what you built** — Project 1, Project 2, your block; what the instrument is, in one sentence.
2. **Waveform out** — a sine on AO1, seen on the scope **and** on the instrument's own AI1 in the Scope tab.
3. **Change it from the phone** — frequency or amplitude, live, from your app.
4. **Alarm → relay → notification** — an input crosses a threshold, a relay clicks, the phone toasts (or your LINE / Telegram bot speaks).
5. **Your block** — its panel and one thing it does, with your measured number and what surprised you. If the live part fails, play your video. Nobody fails a demonstration because a cable fell out.
6. **Your project websites and anything beyond the baseline** — the data logger, the bot, the PID block, the tool your lab needed. Show it if you have it. The class project wall is on the projector all week; your cards are how the others find your work afterwards.

---
**Tutor notes (`/tutor WRAP`, `/tutor DEMO`).** WRAP: environment `esp32s3`, never `-sim`; if a smoke test fails, first check the rail LEDs and the USB port, then the block's pins in `pins.h`; the number needs a method sentence. DEMO: rehearse once against the clock (~15 minutes); the student speaks, you keep time; the video is the safety net, not the plan; the "beyond the baseline" item only if it exists — never suggest it is expected. State the assessment split if asked; anything further is the instructor's.
