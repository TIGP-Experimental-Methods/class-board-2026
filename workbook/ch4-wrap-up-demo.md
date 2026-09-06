# Chapter 4 — Wrap-up + demo

**Wrap-up: in the week of 10-19 (boards back ≈ 10-12, bench-checked and boxed by the instructor). Demo: a 5-minute slot in the week of 10-26.**

## Bring-up checklist (instructor, week of 10-12 — you do not repeat it, but read it)
Rails at the test points (+5V, +3V3, ±12 V, +5VA) with no dev board → dev board in, LED blue, AP up, app opens → `esp32s3` build flashed (no SIM) → each block's smoke test: B1 AI1 reads a known voltage · B2 rail LEDs · B3 AO1 sine seen on a scope · B4 relay 1 clicks, opto 1 counts · B5 DIO1 toggles on a scope → boxed.

## Exercise E13 — `/tutor WRAP`
- [ ] **E13a Real hardware.** Board on the *USB* port. Build **without SIM**: `pio run -e esp32s3 -t upload && pio run -e esp32s3 -t uploadfs`. Open your panel. See your block move real hardware:
  B1 a voltage on AI1 · B2 rail LEDs and your status panel · B3 a sine on AO1 into AI1 · B4 relay click and an opto count · B5 a TTL line and TRIG direction.
  Fix one thing with the tutor (there is always one thing). Commit.
- [ ] **E13b One measured number.** Your block page says which; your `SPEC.md` says what you expected. Measure it, write the value **and the method** under the expectation:
  B1 noise floor of one input (LSB rms, 4000-sample capture, SMA terminated) · B2 the four rail voltages + USB current · B3 amplitude accuracy of a 1 kHz sine at ±5 V · B4 relay switching time from an opto timestamp · B5 TTL edge rate on a scope.
  Expected vs measured, and one sentence on the difference. That sentence is the physics.
- [ ] **E13c 60-second phone video.** Landscape, one take is fine: your panel on the phone, your block doing its thing, the number on the scope or multimeter, your name and block at the start. Upload to `docs/students/<name>/` (≤ 50 MB; otherwise a link) and add it to your day-1 page — it is your course page. Recommended route if you like: the lab's `show-your-work` `education-video` skill (script, narration, picture from your `SPEC.md`), posted on your own YouTube channel and embedded in the page; a phone video is equally fine.

**Deliverables:** the number with its method in `SPEC.md`; the video linked from your page.

## Exercise E14 — the 5-minute demo (`/tutor DEMO` to rehearse)
From the class checklist, in this order:
1. **Waveform out** — a sine on AO1, seen on the scope **and** on the instrument's own AI1 in the Scope tab.
2. **Change it from the phone** — frequency or amplitude, live.
3. **Alarm → relay → notification** — an input crosses a threshold, a relay clicks, the phone toasts.
4. **Your block** — its panel and one thing it does, with your measured number. If the live part fails, play your 60-second video. Nobody fails a demo because a cable fell out.
5. **Beyond the baseline (optional)** — anything you built that the course did not ask for: a data logger, a LINE alert, a PID block, a Python sweep, the tool your lab needed. Two minutes if you have it; nothing if you don't.

**Demo script (say it in 5 minutes):** who you are, which block · what the instrument is (one sentence) · items 1–3 (two minutes, shared with the class) · your block (two minutes) · your number and what surprised you (30 seconds) · item 5 if you have one (two more minutes; the slot stretches for it).

Optional, for the brave: present at the IAMS SAIL Club lunch.

---
**Tutor notes (`/tutor WRAP`, `/tutor DEMO`).** WRAP: environment `esp32s3`, never `-sim`; if a smoke test fails, first check the rail LEDs and the USB port, then the block's pins in `pins.h`; the number needs a method sentence. DEMO: rehearse once against the clock; the student speaks, you time; the video is the fallback, not the plan; item 5 only if it exists — never suggest it is expected.
