# Workbook — Basic Skills for Experimentalists (TIGP 2026)

**Course objective.** Teach key skills needed in every modern experimental physics lab: **Intelligence** (software / AI) · **Electronics** (how we interface intelligence with the real world) · **Mechanics** (creating physical hardware — CAD). We are not teaching how AI works or electronic/mechanical engineering (that takes years); we aim to give you a crash course in using the tools you need to get started with your own projects.

**Format.** Workshops Fridays 14:20–16:20, Room 311; workshop/tutorial style — you need your laptop, fully prepared before each class ([chapter 0](ch0-before-day-1.md)). Language English; Claude can translate to Mandarin. Access to Claude (Team standard) was provided to everyone enrolled — the invitation e-mail was sent on Sunday 6 Sep. Course website: https://tigp-experimental-methods.github.io/.

**Assessment** is based on the project: 20 % hardware demonstration · 30 % app/software demonstration · 30 % presentation · 20 % project website.

**Schedule**

| Date | What |
|---|---|
| Fri 11 Sep | **Workshop 1: AI for experimentalists** — Project 1 (a web app: a simulator or a game) and Project 2 (your phone controls and measures from the ESP32) |
| Fri 18 Sep | **Workshop 2: Designing printed circuit boards** — Project 3a: turning our ESP32 into a real piece of lab equipment (the class board in KiCad) |
| Fri 25 Sep | Public holiday (no class) |
| Mon 28 Sep, 2 pm | Cutoff for the class PCB order — final Gerber files go to manufacturing |
| Fri 2 Oct | **Workshop 3: Firmware and basic mechanical design (PCB housing)** — Project 3b: making a housing for our instrument |
| Fri 9 Oct, 2 pm | Cutoff for design files for 3D printing / laser cutting |
| ~Fri 16 Oct | Collect printed enclosures and assembled PCBs |
| 26–30 Oct | Project presentations and demonstrations, ~15 minutes each |

**The tutor updates itself: at the start of every `/tutor` session it fetches the latest guide and workbook from GitHub and merges them into your copy (the instructor edits them between sessions). One source for two readers:** you (read it like a lab manual) and the tutor (`/tutor <chapter>` in Claude Code, opened in the `class-board-2026` folder, reads the same chapter and paces you through it, in English or Mandarin). Every chapter has checkboxes, the exact commands, and a *what you should see* line after every step. Tooling terms are explained the first time they appear in a chapter and collected in the glossary, [chapter C, *Words we use*](chC-cheat-sheets.md#c0-words-we-use).

| Chapter | When | `/tutor` |
|---|---|---|
| [0 — Before Workshop 1](ch0-before-day-1.md) — Claude runs [`SETUP.md`](../SETUP.md) and installs the toolchain (the compiler and helper programs that turn source code into firmware, the program on the microcontroller) | before Fri 11 Sep | `/tutor CH0` |
| [1 — Workshop 1: AI for experimentalists — Project 1 and Project 2](ch1-day-1-week-1.md) | Fri 11 Sep, then between workshops (keep improving both projects; preparation for Workshop 2: KiCad installed and opened once) | `/tutor L1`, `/tutor HW1` (HW = between workshops) |
| [2 — Workshop 2: Designing printed circuit boards — Project 3a](ch2-day-2-week-2.md) | Fri 18 Sep, then between workshops (what must be finished for the PCB cutoff, Mon 28 Sep 2 pm) | `/tutor L2`, `/tutor HW2` |
| [3 — Workshop 3: Firmware and basic mechanical design (PCB housing) — Project 3b](ch3-day-3-week-3.md) | Fri 2 Oct, then between workshops (what must be finished for the housing cutoff, Fri 9 Oct 2 pm) | `/tutor L3`, `/tutor HW3` |
| [4 — Presentation and demonstration](ch4-wrap-up-demo.md) | collect ~16 Oct; present 26–30 Oct | `/tutor WRAP`, `/tutor DEMO` |
| [A — Electronics from zero](chA-electronics-from-zero.md) | self-study, before Workshop 2 | `/tutor A` |
| [B — How the instrument's software works](chB-how-the-software-works.md) | self-study, before Workshop 3 | `/tutor B` |
| [C — Cheat-sheets](chC-cheat-sheets.md) — starts with *Words we use*, then the AI method in one screen | always open | — |
| [Your section of the class board](blocks/) — [B1](blocks/b1.md) · [B2](blocks/b2.md) · [B3](blocks/b3.md) · [B4](blocks/b4.md) · [B5](blocks/b5.md) | assigned at the start of Workshop 2 | inside `/tutor L2`, `/tutor HW2` |

**Where things live.** Every project is its own folder next to `class-board-2026` and its own public repository on GitHub (a repository is a project folder whose complete history git keeps, with a copy online): `SPEC.md`, `PLAN.md`, the code (`app/` for a web app, `firmware/` for the board), the developer-facing `README.md`, your handover file, and `index.html` at the root — the **project website**, published with GitHub Pages, that presents the project (what it is, how it works, a picture or short video of it working, what was verified, links to the app and the code). At the end of each project it goes on the **class project wall**, https://tigp-experimental-methods.github.io/showcase-2026/ — one card per project, everyone's, on the projector in class (chapter 1, *Put it on the class project wall*). In the class repository, `docs/students/<name>/` holds your `PROGRESS.md` (done / verified / next / gotchas, one entry per session) and later your section's files. Slides: the course site. Help: work with the tutor; when you want the fix, ask it for the fix; if that does not solve it, e-mail the instructor with a screenshot (address on the course site).

**The "AI method" in 5 steps** is the spine of every chapter: **Vision** (describe what you want, in detail) · **Specification / Plan** (AI writes a detailed spec and a plan of small tasks with testable deliverables; ask it to ask you questions) · **Review** (you review; an independent review in a fresh Claude session that did not write the plan; iterate — the first plan is never the last plan) · **Code** (agents in parallel) · **Test / Debug / Verify** (the plan includes the tests; fix one problem at a time). **Never trust AI without testing and verifying.** The habits that go with it: a written spec before code · teach the repository, not the session (`CLAUDE.md`) · one topic per session · handover notes in Markdown · AI writes, you verify. All of it in one screen: [chapter C, C.0b–C.0d](chC-cheat-sheets.md#c0b-the-ai-method-in-one-screen).

**Beyond the baseline.** The class board's hardware is fixed by budget and timeline; the software, firmware and app are open. Whenever you are ahead: what problem in your lab could this instrument solve? Most encouraged: **talk to your instrument from LINE or Telegram** — push notifications when a value drifts or an alarm fires, bot commands that read a value or switch an output from your phone, from anywhere. Also a data logger, remote access with a Python sweep, a controller block, a second board; or show the work — a video, a project website, a game that teaches something. **Build something great.**
