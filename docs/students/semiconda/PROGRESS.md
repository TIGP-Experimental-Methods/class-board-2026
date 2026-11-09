# semiconda — PROGRESS

- Language: English
- Background: soldered before; used a CAD program before; never read a schematic
- Section: **C** — front panel board
- Ring: reviews Section A's PR; reviewed by Section B
- Project 1 — Huayu Pocket (Taiwanese Mandarin drills): repository https://github.com/semiconda/huayu-pocket ·
  app https://semiconda.github.io/huayu-pocket/app/ · project page https://semiconda.github.io/huayu-pocket/
- Project 2 — esp32-morse: repository https://github.com/semiconda/esp32-morse

## 2026-11-01 — L1 (between workshops)

- **Done:** Project 2 started. Chose the project: a phone app that sends typed text as Morse
  code on the board's LED (buzzer possibly later), to be followed by a WiFi signal mapper.
  Repository `esp32-morse` created public under `semiconda` and pushed (first commit: README
  with the timing rule, .gitignore). `VISION.md` written as the step-1 vision document —
  send-once with Resend and Stop, 5–40 WPM speed control, three-level live display,
  blocking validation that names unsupported characters, all gap durations from one function
  so Farnsworth timing stays a one-place change later. Working documents (VISION, SPEC, PLAN,
  handover, notes) are gitignored by choice: they stay local, the public repository carries
  only code, README and the project page. Step 1 of Project 2 done — class reference
  firmware and phone app flashed as the hardware baseline.
- **Verified:** board enumerated as `303A:1001` on COM4 (already flashed before, so no
  BOOT+RST needed); `upload` and `uploadfs` both reported *Hash of data verified*; phone
  joined `instrument-F1D8`, opened http://192.168.4.1, **tapping Red turned the LED red and
  the chart of `base.counter` updated live**. `git check-ignore -v VISION.md` printed its
  .gitignore line, so the working documents cannot be committed by accident.
- **Next:** in a second VS Code window, have my own Claude session read `VISION.md`, answer
  its questions, then write `SPEC.md` and `PLAN.md` — no code yet. Review the plan in a
  fresh Claude session before building. Headline test to verify on hardware: ten PARIS at
  10 WPM must take 60.0 s by the phone stopwatch. Then the WiFi map project. Still to do:
  commit the .gitignore change; project website and class-wall entry at the end.
- **Gotchas:** the board's access point did not appear in the phone's WiFi list at first —
  it needs a moment and a rescan; it is not a fault. The serial port opens but prints
  nothing once the board has booted, because the firmware only prints at startup, so silence
  on the port proves nothing either way — press RST to see the boot log. The system Python
  has no pyserial; PlatformIO's own Python (`~/.platformio/penv/Scripts/python.exe`) does.

## 2026-11-03 — HW1 (between workshops): Project 1

- **Done:** Project 1, Huayu Pocket — a phone-sized drill app for Taiwanese Mandarin from zero, built on the
  course textbook (lessons 1-6, 179 words). Followed the AI method twice: v1 (word quiz in eight directions,
  listening with the Ministry of Education's Taiwanese recordings, practice table with stroke order), then v2
  (writing a word stroke by stroke, putting sentence tiles in order, filling a gap). v2 spec and plan were
  reviewed by a fresh session (14 findings, folded in) before any code; 73 sentences written new from each
  lesson's SYNTAX PRACTICE, reviewed again by a fresh session (missing word orders and one tone fixed). A deck
  validator with 35 test fixtures runs on every commit and in GitHub Actions. Deployed on GitHub Pages; project
  page written (`index.html` at the repository root).
- **Verified:** predicted next to measured, on the project page and in `SPEC.md`: 0 repeated wrong-option sets
  in 18,464 repeat showings; every word once before any repeat; 6,776 of 6,776 option sets the answer's length;
  word-order tiles never dealt already correct; gap options exactly as written (20/20); writing traced correctly
  gives "Clean", two deliberate wrong strokes give "2 mistakes". On my phone: writing graded right at the
  default tolerance, and I read all 73 sentences (one changed: no "hot" about a person).
- **Next:** the class wall entry for Project 1; lessons 7-12 as the course reaches them; then Project 2's spec
  and plan.
- **Gotchas:** 我 (wǒ) has no recording in the Ministry's package, so words with it are reading-only — accepted,
  not worked around. Headless Chrome with virtual time barely fires `requestAnimationFrame`, so stroke
  animations never finish there unless shimmed. Removing a pushed commit needs a force-push, which Claude Code's
  auto mode blocks until you say to run it.

## 2026-11-08 — HW1 (between workshops): Project 1, Sounds

- **Done:** Sounds (added 2026-11-06) — hear one syllable, pick it among four that differ only in tone or in one
  look-alike sound — tried on my phone. The project page now describes it as the fourth question kind, explains
  how its options are built, and lists its checks; `handover.md` and `PLAN.md` record the phone check. Commit and
  author names in both project repositories are now `semiconda`; the two repositories were recreated on GitHub to
  drop the old history, so their GitHub Actions run history starts again.
- **Verified:** Sounds on my phone: it works. Headless, before that: 400 of 400 sound questions had four
  different options. Both project sites load after the repositories were recreated.
- **Next:** rewrite the Huayu Pocket project page in my own words; then its class-wall entry. Project 2: T6
  measurements, a video, its page numbers and wall entry.
- **Gotchas:** the project page's kind-share check (⅓ each) was measured before Sounds existed; it was dropped
  from the page rather than left stale — with Sounds on, the expected share is ¼ each, not yet measured. The
  course asks for the spec's checks, predicted next to measured, so the page keeps those and puts the phone
  checks in one line.

## 2026-11-09 — HW1 (between workshops): Project 1 finished

- **Done:** the start screen is now three rows: what to practise (Words, Sentences, Sounds), how (Reading,
  Hearing, Writing) and show in (Pinyin, Characters). I went through the project page line by line: impersonal
  wording, plainer descriptions of each question kind, and a pointer to the guide for adding lessons. The class
  wall card is up.
- **Verified:** the page and the app load at their addresses; the card shows on the class wall.
- **Next:** Project 2: agree a filming method, T6 measurements, a video, the page's numbers and its wall entry.
