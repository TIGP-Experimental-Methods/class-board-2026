# Chapter 1 — Workshop 1: AI for experimentalists (Fri 11 Sep) + homework 1

**Fri 11 Sep 2026, 14:20–16:20, Room 311, then homework 1.** Four parts, in the order of the slides: a setup check · a short introduction to AI and the tools we use · **Project 1 — build a web app (a simulator or a game)** · **Project 2 — control a microcontroller over the net with your phone.** Both projects are built with Claude Code by the "AI method" in 5 steps (§1.3) and both continue as homework. The slides are the reference for the introduction: https://tigp-experimental-methods.github.io/slides/W1-AI-for-experimentalists.pdf. Words we use are explained the first time they appear and collected in [chapter C, C.0](chC-cheat-sheets.md#c0-words-we-use).

**Think about what you want to make.** You will be asked in the first half hour. Suggestions from the slides: loading a freight train game · inverted pendulum simulator · phase-locking coupled pendula · unfair golf · billiards · a calculator or simulator for something from your research.

**Two VS Code windows all afternoon.** The class repository `class-board-2026` (a repository is a project folder whose complete history the tool git keeps) with the tutor in one window; your own project with plain Claude Code in a second window. The tutor paces you and checks your work; Claude in the project window builds.

---

## 1.1 Setup check

Everyone needs: the laptop prepared as in [chapter 0](ch0-before-day-1.md) · Claude access — the invitation was e-mailed on Sunday 6 Sep; you are signed in to the Claude Code extension · the class repository cloned (downloaded with its history) into your course folder · the ESP32 board (provided) and a USB-C data cable (the instructor has spares).

Open the class repository (*File → Open Folder…* → `class-board-2026`), open the Claude Code panel and type `/tutor L1`. Answer its questions: language, what you have built before, `expert` if you want whole recipes instead of pacing. The tutor then runs the toolchain check (the toolchain is the compiler and helper programs that turn source code into firmware, the program that runs on the microcontroller), creates your branch `w1-<name>` in the class repository (a branch is a separate line of work inside a repository; `main`, the version everyone builds on, is protected, so your files in the class repository go on your branch) and creates `docs/students/<name>/PROGRESS.md` — your handover notes: done / verified / next / gotchas, the file the next session reads first.

- [ ] `git --version` · `gh auth status` · `pio --version` · board on a port (`pio device list`) · signed in to the Cloudflare dashboard
- ✔ **toolchain OK**

If a tool fails: the tutor gives the fix when you ask for it; if that does not solve it, e-mail the instructor with a screenshot and start Project 1 anyway — it needs only VS Code, Claude and GitHub.

## 1.2 Introduction to AI and the tools we use — the reading list

This is not a second lecture. Each row is one slide section, its claim and the rule of thumb the slides draw from it. Read the slides for the argument; come back to this table when you need the rule.

| Slides | The claim | Rule of thumb |
|---|---|---|
| 13–15 | **How LLMs work.** Text becomes tokens (pieces of a few characters), tokens become numbers; one operation repeated — predict the next token; training fits the weights once, inference runs them. | Fluency is not correctness. The model does not learn from your conversation. |
| 19–21 | **Context.** Every message resends the whole conversation (the context window: everything so far — your messages, files read, tool output). The unchanged start is cached and cheap; off-topic history is paid for and competes for attention. | Keep context small: **one topic per session.** New topic, new chat. |
| 22–23 | **Files and Markdown.** A dropped-in PDF or image is an expensive prefix, resent on every turn and mostly noise. | Let a separate session read each file and write a detailed Markdown summary; the main session works from the digest. |
| 24–25 | **Model tiers.** Haiku · Sonnet · Opus · Fable, the same idea at different sizes, at about 1 : 3 : 5 : 10 cost. | The strong model plans and checks; cheap models do the work, each in its own fresh context, in parallel. |
| 26 | **The AI method in 5 steps** — the most important slide in the talk. | §1.3 below. |
| 27 | **Reviewing.** Never let the author grade its own work — same context, same blind spots. | An independent reviewer that sees only the spec and the output (e.g. Codex reviews Claude); tests written first; loop, don't hope. |
| 28 | **Long projects.** A session is not a project. Long work is a chain of short sessions joined by documents on disk. | At about 50 % context, write the handover and commit; start fresh. The disk is the memory. |
| 29 | **CLAUDE.md, memory, skills, MCP, hooks, extensions** — six places to put what the agent should know, each costing context differently. | Keep `CLAUDE.md` under a page. Prefer hooks for anything that must always happen. |
| 30 | **Workflow must-dos.** | Put all needed data in the prompt · one topic per session · summarise files first · cheap workers, strong planner · verify independently ([C.0c](chC-cheat-sheets.md#c0c-workflow-must-dos)). |
| 32–35 | **Failure modes.** Hallucinations follow from the process; beyond them the model invents specifics, agrees with you, makes small errors in correct-looking structure, drops requirements, compounds errors, applies stale context. An agent adds: gaming the test, claims without running, scope creep, loops, wrong target, destructive actions. | Use AI where checking is easier than doing. Agent failures are caught by mechanism — hooks, git, tests — not by reading harder ([C.0d](chC-cheat-sheets.md#c0d-when-things-go-wrong)). |
| 37–38 | **Tools.** Four ways to run an agent (Claude Cowork, Claude Design, the Codex app, VS Code + agents). Our choice: **VS Code + the Claude Code extension** — low lock-in; the whole folder is the context. Know the window: new session · prompt · permissions · model and thinking level · context level · menu · extensions · git · file explorer. | Anything with a codebase, or that you will still be working on next year → VS Code. |
| 39 | **Oops, I made a mistake.** | Save your tokens: stop the execution. Don't poison your context: rewind. |
| 40 | **Context is full.** Start a new session. | First, prompt: *"Please finish what you are working on and document anything from this session that may be useful to future Claude sessions in .md files in this directory and a handover.md file to allow Claude to continue our work in a new session."* |
| 41 | **Compaction is lossy.** Clicking the context icon deletes most of the context without saving useful knowledge anywhere. | Have Claude document the session in hierarchical, searchable `.md` files instead; always a log and a handover file. |
| 42 | **Menu items.** Permissions and mode; model selection; thinking on (the instructor uses medium or high). | Check your usage often. Check whether unnecessary skills or hooks clutter every session. |
| 43–50 | **Git.** Why version control (safety net, understanding, collaboration; git is the tool, GitHub hosts a copy). Four words: repository, commit (a named snapshot), diff (what changed), history. The loop edit → stage → commit **in VS Code's Source Control panel — no terminal required.** Branches: main always runs. GitHub: push, pull, clone, pull request. `.gitignore` and undo. | Commit small and often. Commit before the agent starts; ask it to commit as it goes; review the diff, not the file; give it a branch; never let it rewrite history. Tests go in git too. |
| 52–53 | **Deployment.** GitHub hosts code; GitHub Pages hosts static pages; Cloudflare Pages + Workers host apps with a backend; YouTube unlisted hosts video. The loop: commit → push → the host builds → live. | Static page → GitHub Pages is enough; stores data, calls an API with a key, or runs on a schedule → Cloudflare Workers. Secrets never go in the repository. |
| 55–59 | **Apps that talk to you.** Telegram (@BotFather, the easiest start), LINE (Messaging API, what everyone in Taiwan has), ntfy.sh for alerts only; a webhook on a Cloudflare Worker; Google Sheets as a database; an LLM inside your app via an API key. Two ways AI makes software smarter: A — AI-written code (default); B — an LLM in the loop, at the hard step. | Tokens are passwords. Start with Telegram, then port to LINE. Default to A; reach for B at the hard step. |
| 61–62 | **Video.** Script first, pictures last: document → script → audio → visuals timed to the audio. The lab's pipeline is public: https://github.com/iams-yb-lab/show-your-work (five Claude skills). Pictures of hardware: Blender first, Unreal for scenery. | Label generated imagery. |

## 1.3 The "AI method" in 5 steps

The most important slide in the talk (slide 26). Both projects today, and everything in Workshops 2 and 3, follow it.

1. **Vision.** Describe what you want, with as much detail as possible.
2. **Specification / Plan.** Get AI to produce a detailed specification — plan the project. Break the project into many small tasks with testable deliverables. **Ask AI to ask you questions.**
3. **Review.** Review the plan yourself; have AI review the plan to identify improvements and flaws — e.g. use Codex to review Claude. **Iterate the plan: the first plan is never the last plan.**
4. **Code** (using agent swarms). Tell AI to run swarms of agents in parallel to complete the build — subagents, each with its own fresh context.
5. **Test / Debug / Verify.** Ensure your plan and spec include methods to test the code. Fix problems one at a time. Iterate.

**Never trust AI without testing and verifying.**

## 1.4 Project 1 — Build a web app (a simulator or a game)

**What do you want to make?** Suggestions: loading a freight train game · inverted pendulum simulator · phase-locking coupled pendula · unfair golf · billiards · a calculator or simulator for something from your research. Pick something you understand well enough to know when it is wrong.

The five steps from the slides, as a walk-through. Every step ends with *what you should see*.

### Step 1 — Decide what to make, and write the vision

Write the vision in your own words, in as much detail as you can: what is on the screen, what the user can change, what must be physically right, what it runs on. A paragraph is enough; a page is better. Example (write your own):

> An inverted pendulum on a cart, drawn side-on in the browser. Sliders for pendulum length, mass and friction; a button that nudges the pendulum; a switch that turns a balancing controller on and off; a plot of angle against time under the drawing. The motion is integrated from the equations of motion, not animated to look right. Hanging down, with no friction and a small nudge, the swing period must be 2π√(L/g); with friction zero the total energy must stay constant to 0.1 % of its starting value over a long run. One page, `index.html`, plain JavaScript, no build step, works on a phone.

*What you should see:* a vision you could hand to a colleague and they would build the same thing.

### Step 2 — Follow the AI method to a working local demo

**Repository.** Your project gets its own repository next to `class-board-2026` in your course folder. Two routes, same result:

- *VS Code:* create a folder, open it (*File → Open Folder…*), *Source Control → Initialize Repository*, then *Publish Branch* — choose public or private (your choice; Cloudflare Pages deploys private repositories, GitHub Pages needs a public one).
- *Terminal* (the text window where you type commands), one command per line, from the course folder: `gh repo create <your-github-user>/<project-name> --public --clone` (or `--private`), then `code <project-name>`.

*What you should see:* a second VS Code window with an empty project; Source Control shows no changes; the repository exists on GitHub.

**Specification and plan.** In the project window, open Claude Code and paste your vision with this:

> Here is my vision: […]. Ask me questions until you can write a detailed specification. Then write `SPEC.md` — what it does, what the user sees, the physics or rules with the equations, and how we will test that it is right — and `PLAN.md`, the build broken into many small tasks, each with a testable deliverable. Do not write any code yet.

Answer the questions. Then **read both files** — this is the step most people skip. Check that:

- the spec computes the physics from the parameters rather than drawing a picture that happens to look right;
- the spec names at least one test you can predict without the program: a value you can work out by hand (a pendulum period, a cut-off frequency), a conservation law (energy, momentum), a limiting case (zero friction → constant speed; zero load → the train accelerates at F/m). This is *one* of the checks, not the whole project — but it is the one that catches "right structure, wrong sign";
- every task in the plan says what "done" looks like.

**Review.** Independent means a different context. Open a new Claude session (or Codex, if you have it) and ask:

> Read `SPEC.md` and `PLAN.md`. You did not write them. Find flaws, missing requirements, physics errors and tasks that cannot be tested. Do not approve anything; list problems, most serious first.

Fold what matters back into the files. The first plan is never the last plan. Then **commit** (save a named snapshot): Source Control → stage both files with **+** → message `spec and plan v1` → *Commit*. A clean commit before the agent starts is your undo button.

**Code.** Back in the project session:

> Work through `PLAN.md` one task at a time. Where tasks are independent, use subagents in parallel. After each task, run its test, then commit with a message that says why. Change nothing outside the current task. Tell me when you are done or blocked.

Read each permission prompt (the approval request before Claude runs a command or edits a file) before you approve it. *What you should see:* files appearing; commits appearing in Source Control; each diff readable.

**Test, debug, verify.** Open `index.html` in a browser (double-click it, or ask Claude to start a local server and give you the address). Run the checks the spec names yourself — set the parameters, read the numbers off the page, compare with what you predicted. Write the comparison into `SPEC.md`. If one is wrong, that is the exercise: describe exactly what you see and what you expected, and fix **one problem at a time**. If the agent tries the same fix three times, stop it, rewind, and rethink the plan.

*What you should see:* the page runs; predictions and results side by side in `SPEC.md`; a commit history that tells the story.

**When the context fills** (the context indicator in the Claude panel is about half full, or answers get worse): paste the slide-40 prompt — *"Please finish what you are working on and document anything from this session that may be useful to future Claude sessions in .md files in this directory and a handover.md file to allow Claude to continue our work in a new session."* — commit, start a new session, and tell it to read `handover.md` first.

### Step 3 — Deploy it on the web: GitHub or Cloudflare

Deploy means publish it so anyone with the address can open it. Push first (upload your commits to GitHub): Source Control → *Sync Changes* (or *Publish Branch* the first time). Then one of:

- **Cloudflare Pages:** dashboard → *Workers & Pages → Create → Pages → Connect to Git* → your repository → branch `main` → build command **blank**, output directory `/` → *Save and Deploy*. Address: `https://<project-name>.pages.dev`.
- **GitHub Pages** (public repository): on GitHub, your repository → *Settings → Pages → Deploy from a branch → main → / (root) → Save*. Address: `https://<user>.github.io/<project-name>`.
- Or ask Claude: *"Deploy this on GitHub Pages"* — you supply the accounts, it does the wiring. Read what it changes.

*What you should see:* the address opens on your phone; move a slider. From now on every push republishes the page.

### Step 4 — Create a report that explains the concept or game in detail

The report is `README.md` in your repository (it is what GitHub shows on the repository's front page). It explains the concept or the game in detail: what it is and why it is interesting; the physics or rules, with the equations; how to use or play it; the checks you ran and their results; what you would do next; a screenshot and the live address. Ask Claude for a draft from `SPEC.md` and the commit history, then edit it — the report is yours, in your words. Commit, push.

*What you should see:* someone who has not seen the app understands from the README what it does and why the numbers are right.

### Step 5 — Improve the presentation (optional extension)

Markdown → slides → website → YouTube video. The lab's show-your-work skills (`slide-deck`, `technical-report`, `education-video`) turn your README into each of these; the order is document → script → narration → pictures timed to the audio (slide 61). This is also the route to the presentation and the project website at the end of the course.

**Habits that make this safe** (slides 45, 49): commit before the agent starts · ask it to commit as it goes · review the diff, not the file · one idea per commit · never let it rewrite history — if it asks to force-push or reset, say no.

## 1.5 Project 2 — Control a microcontroller over the net with your phone

**Aim** (slide 67): create a phone app that lets you control and measure from hardware — the ESP32 — over WiFi. Example: a phone app that controls the brightness and colour of the ESP32's LED. A camera is available for anyone who wants to try that too. Follow the AI method again; the vision is now about a physical thing you can see change.

### The facts you need about the board

- The board is a **Jinhua #40729 ESP32-S3 N16R8 dev board** (the development board: the ESP32-S3 microcontroller — a small computer on a chip, with WiFi — on a small board with a USB-C connector and pins). Its RGB LED is a WS2812 on GPIO 48 (a GPIO is a general-purpose pin); the antenna is a u.FL connector. Use the connector marked *USB* (native USB, not *UART*) and a data cable.
- Firmware is built with **PlatformIO** (the tool and VS Code extension that compiles and flashes — writes onto the board over USB) and the **Arduino framework**. Board name in PlatformIO: `esp32-s3-devkitc-1`.
- **The first flash of a factory-fresh board fails once, by design.** `upload` ends with *"No serial data received"*: hold **BOOT**, tap **RST**, release BOOT. The board comes back on a **new COM port** — run `pio device list` again and flash to that port (`--upload-port COMx` if PlatformIO picks the wrong one). After that every flash resets the board by itself.
- **The port disappears and reappears at every reset** — the USB-to-serial converter is inside the chip. A serial monitor must reconnect after every flash and the first boot lines may be missing. Normal.
- **Two ways onto WiFi.** The board can run its own access point (its own WiFi network, which your phone joins) — no password of yours involved. Or it joins an existing network, in which case the network's name and password go in a git-ignored file `firmware/include/secrets.h` (git-ignored: listed in `.gitignore`, so git never commits it).

> **Secrets never enter a Claude interaction.** A secret is a password, a WiFi key, an API token — anything that lets someone else in. Never type one into a Claude chat, a prompt, `PROGRESS.md`, `SPEC.md`, a commit message, a pull request or a screenshot: transcripts are stored, repositories are shared or public, commits are forever. The pattern: Claude (or you) creates `secrets.h` from `secrets.h.example` with the network name filled in and the password as a placeholder such as `PUT-THE-PASSWORD-HERE`; **you** type the password into that file in the editor; `git check-ignore -v firmware/include/secrets.h` must print a line (nothing printed → stop, do not commit, tell the instructor); `git status` before every commit — `secrets.h` must not be listed. The tutor never asks for a secret and never repeats one. Pasted one anyway? Delete it from the chat if you can, treat it as exposed, tell the instructor.

### Suggested path — your own app, by the AI method

**Vision.** A page served by the ESP32 itself over WiFi, opened in the phone's browser: a colour picker and a brightness slider for the LED, and one live measurement that updates on its own — the chip temperature, an ADC (analog-to-digital converter) pin in volts, a counter. You decide what to measure.

**Where.** A folder `esp32-app/` in your Project 1 repository, or a second repository — your choice. Commit before Claude starts.

**Specification and plan.** Paste the vision and the board facts above, and add:

> Scaffold a PlatformIO project (Arduino framework, board `esp32-s3-devkitc-1`, WS2812 LED on GPIO 48). The board runs its own WiFi access point and serves one web page with a colour control, a brightness slider and one live readout. Write `SPEC.md` and `PLAN.md` first, with tests I can do with my phone and eyes; ask me questions before writing them. Do not write code yet. Never ask me for a WiFi password.

Read the plan. Name the test yourself: *tap red → the LED is red; slide brightness to zero → the LED is off; the readout changes when I warm the chip with a finger* — or, for a counter that counts at a fixed rate, the value it must show after a known time. Then review (a fresh session or Codex), iterate, commit.

**Code, then flash.** Let Claude build; `pio device list` for the port; flash from the project folder, one command per line: `pio run -t upload`. The first time, expect the BOOT+RST trap above. Watch the boot log (`pio device monitor`, 115200) for the network name and address the firmware prints.

**Verify.** Phone joins the board's network (stay connected when the phone warns there is no internet; on Android switch mobile data off), open the address the board printed — type the `http://`. Run your test. Write what you saw into `PROGRESS.md`, then commit.

*What you should see:* your phone changes the LED's colour and brightness; one number on the page moves by itself and you can say why.

### Reference and fallback — the class firmware and phone app

The class repository already contains a firmware and phone app that do exactly this and more: `firmware/` (PlatformIO, Arduino) and `host/pwa/` (the phone app — a web page served by the board). The base block controls the LED and reports a 10 Hz counter and the chip temperature; the app charts any value and has an alarm engine. Use it three ways: start from it and change it; read it while Claude builds yours (`firmware/PROTOCOL.md` describes every message); or flash it when your own build stalls. It is also the base for Projects 3a and 3b in Workshops 2 and 3, so every student flashes it at least once.

From the class repository root, one command per line:

```sh
pio device list
pio run -d firmware -e esp32s3-sim -t upload
pio run -d firmware -e esp32s3-sim -t uploadfs
```

`esp32s3-sim` is the build for a bare dev board (SIM mode: the firmware fakes the class-board hardware it does not have); `uploadfs` copies the phone app onto the board. Then: LED blue = access point running · phone joins `instrument-XXXX` (label on the board or in the boot log), password `instrument` · open **http://192.168.4.1** — type the `http://`, stay connected when the phone warns about no internet, mobile data off on Android · tap *Red* on the Base tab; the chart plots `base.counter`. To make it *yours*, change one thing: a command in `firmware/src/blocks/base/BaseBlock.cpp` (`handle()` acts on a command, `status()` fills the numbers the phone sees) and a control in `host/pwa/panels/base.js` (`render()` builds the controls, `onStatus()` updates the readouts).

### Measure something — ideas

The chip's own temperature (`temperatureRead()`, coarse steps of about 1 °C — a finger on the chip moves it) · the counter (counts at a fixed rate, so you can predict its value after a known time) · an ADC pin in volts (GPIO 4 floating, or with a jumper wire in it). *One idea with a prediction in it:* sample the ADC continuously into a buffer, let the phone set an averaging length N, and show the mean of the last N samples and the noise of such N-sample averages. For independent samples that noise falls as 1/√N — from N = 1 to N = 256 a factor 16. It will not obey exactly; saying what you see and why (mains pickup, a touched wire) is the interesting part.

## 1.6 Homework 1 — `/tutor HW1`

- [ ] **Project 1 finished:** deployed at a public address; the report (`README.md`) explains the concept or game in detail; the spec's checks have been run and their results are in the report.
- [ ] **Project 2 finished:** your phone controls the board's LED colour and brightness and shows one live measurement — your own build, or the class firmware with one change of your own.
- [ ] **KiCad 10 installed and opened once** — the free program the class board is drawn in; Workshop 2 needs it running (`SETUP.md` step 9, or tell Claude: *"install KiCad 10 as in SETUP.md step 9"*). ✔ *Help → About KiCad* shows 10.x.
- [ ] **JLCPCB and LCSC accounts** — the factory that makes and assembles our boards and its parts catalogue: https://jlcpcb.com and https://www.lcsc.com. Sign up; nothing to order.
- [ ] `PROGRESS.md` up to date in both places: `docs/students/<name>/` in the class repository (on `w1-<name>`, with the addresses of your project repository and live page) and `handover.md`/`PROGRESS.md` in your own repository. Both pushed.
- [ ] Optional: Step 5 of Project 1 — slides, a project website, a video.

**Hand-in.** Your own repository is public or private, your choice; the class-repository files go in one pull request (a request to merge your branch into the shared project; someone reviews it first) from `w1-<name>`, opened from GitHub or with `gh pr create --fill`. Bring both projects to Workshop 2. **Your part of the class board is assigned at the start of Workshop 2.** Reading before then: [chapter A](chA-electronics-from-zero.md) where you need it; [chapter C](chC-cheat-sheets.md) C.1–C.2. How the projects count is on the course site.

## 1.7 Beyond the baseline

The class board's hardware is fixed by budget and timeline; the software, firmware and app are open, and that is where you show what you can do. The extension we most encourage: **talk to your instrument from LINE or Telegram** — push notifications when a value drifts or an alarm fires, bot commands that read a value or switch an output from your phone, from anywhere (slide 55: start with Telegram, then port to LINE; tokens are passwords). Also: a data logger, remote access with a Python script that runs a sweep, a controller block, a second board. Whenever you are ahead, ask what problem in your lab this could solve. **Build something great.**

---
**Tutor notes (`/tutor L1`, `/tutor HW1`).** Assume competence; offer expert mode. Pace the AI method, do not run it: for each project the student writes the vision; Claude in the *project* window writes `SPEC.md`/`PLAN.md`; you read them with the student and refuse to move to code until the student has reviewed both and can name at least one test they can predict without the program. Insist on an independent review (fresh session or Codex) and one iteration of the plan. Before every commit ask *"what do you see?"* — never accept "it works"; the observation goes into `PROGRESS.md`. Project 1: reject a spec that draws a picture instead of computing the physics; the report is in the student's words. Project 2: the student's own build is the path; when it stalls, offer the class firmware (`pio run -d firmware -e esp32s3-sim -t upload`, then `-t uploadfs`) as the fallback and let them change one thing in `BaseBlock.cpp` + `panels/base.js`. Know the first-flash trap: *No serial data received* = hold BOOT, tap RST, release, `pio device list`, new COM port, flash again — once; the port vanishing at every reset is normal. Never run an upload without naming the environment and the port. Never handle secrets (COURSE-GUIDE rule 15): the student types a WiFi password into `secrets.h` in the editor, `git check-ignore -v` proves it is ignored, `git status` before every commit. Create `w1-<name>` at the start; nothing goes on `main`; `docs/students/<name>/PROGRESS.md` in the class repository and a `handover.md` in the student's own repository are kept in step — end every session with both. Homework: both projects finished, KiCad opened, JLCPCB/LCSC accounts; block assignment is Workshop 2 — do not assign or discuss blocks. Grades are not your topic.
