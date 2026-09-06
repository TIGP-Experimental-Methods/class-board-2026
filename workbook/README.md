# Workbook — Basic Skills for Experimentalists (TIGP 2026)

One source for two readers: **you** (read it like a lab manual) and **the tutor** (`/tutor <chapter>` in Claude Code reads the same chapter and paces you through it, in English or Mandarin). Every chapter has checkboxes, the exact commands, and a *what you should see* line after every step. Tooling terms are explained the first time they appear in a chapter and collected in the glossary, [chapter C, *Words we use*](chC-cheat-sheets.md#c0-words-we-use).

| Chapter | When | `/tutor` |
|---|---|---|
| [0 — Before day 1](ch0-before-day-1.md) — Claude runs [`SETUP.md`](../SETUP.md) for the toolchain (the compiler and helper programs that turn source code into firmware, the program on the microcontroller) | before Fri 09-11 | `/tutor CH0` |
| [1 — Day 1 + week 1: build it, ship it, log it — then your instrument](ch1-day-1-week-1.md) (*ship*: publish it where others can open it) | Fri 09-11 + HW1 | `/tutor L1`, `/tutor HW1` |
| [2 — Day 2 + week 2: your part of the board](ch2-day-2-week-2.md) | Fri 09-18 + HW2 | `/tutor L2`, `/tutor HW2` |
| [3 — Day 3 + week 3: make it work, make it yours](ch3-day-3-week-3.md) | Fri 10-02 + HW3 | `/tutor L3`, `/tutor HW3` |
| [4 — Wrap-up + demo](ch4-wrap-up-demo.md) | week of 10-19; demos 10-26 | `/tutor WRAP`, `/tutor DEMO` |
| [A — Electronics from zero](chA-electronics-from-zero.md) | self-study, before L2 | `/tutor A` |
| [B — How the instrument's software works](chB-how-the-software-works.md) | self-study, before L3 | `/tutor B` |
| [C — Cheat-sheets](chC-cheat-sheets.md) — starts with *Words we use*, the glossary | always open | — |
| [Your block](blocks/) — [B1](blocks/b1.md) · [B2](blocks/b2.md) · [B3](blocks/b3.md) · [B4](blocks/b4.md) · [B5](blocks/b5.md) | from day 1 | inside `/tutor HW1` |

**Where things live.** Your project files: `docs/students/<name>/` (`PROGRESS.md`, `SPEC.md`, `notes.md` — plain-text files: what was done / verified / next / gotchas, what to build, your own notes — later `box.stl` and your video). Your personal page: your own day-1 repository (a project folder whose complete history git keeps, stored online on GitHub; it holds the page that teaches one idea). Slides and videos: the course site https://tigp-experimental-methods.github.io/. Help: stuck? ask the tutor for the fix; after that, email the instructor with a screenshot (address on the course site).

**The five working practices** (they are the spine of every chapter): spec first · teach the repository (`CLAUDE.md`, the file the coding agent — Claude Code working on your files — reads every session) · small fresh sessions · handover notes in Markdown (plain text with light formatting; `PROGRESS.md`) · AI writes, you verify.

**Beyond the baseline.** The hardware is the shared baseline — fixed by budget and timeline. The software, firmware and app are open. Whenever you are ahead: what problem in your lab could this instrument solve? A data logger to CSV · LINE/Telegram alerts from the alarm engine · remote access + a Python sweep · a calibration routine · a PID/controller block · a second node. Bring a real problem to L2; the tutor helps you write its `SPEC.md`. Not required; the demo has an optional fifth item for it. **Talk to your instrument from LINE or Telegram** — the extension we most encourage: push notifications when a value drifts or an alarm fires, and bot commands that read a value or switch a relay from your phone, from anywhere.
