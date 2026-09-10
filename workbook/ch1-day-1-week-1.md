# Chapter 1 — Workshop 1: AI for experimentalists (Fri 11 Sep) + between workshops

**Fri 11 Sep 2026, 14:20–16:20, Room 311.** Four parts, in the order of the slides: a setup check · a short introduction to AI and the tools we use · **Project 1 — build a web app (a simulator or a game)** · **Project 2 — control a microcontroller over the net with your phone.** Both projects are built with Claude Code by the "AI method" in 5 steps (§1.3); between the workshops you keep improving them (§1.6). The slides are the reference for the introduction: https://tigp-experimental-methods.github.io/slides/W1-AI-for-experimentalists.pdf. Words we use are explained the first time they appear and collected in [chapter C, C.0](chC-cheat-sheets.md#c0-words-we-use).

**Think about what you want to make.** You will be asked in the first half hour. Suggestions from the slides: loading a freight train game · inverted pendulum simulator · phase-locking coupled pendula · unfair golf · billiards · a calculator or simulator for something from your research.

**Two VS Code windows all afternoon.** The class repository `class-board-2026` (a repository is a project folder whose complete history the tool git keeps, with a copy online on GitHub) with the tutor in one window; your own project with plain Claude Code in a second window. The tutor paces you and checks your work; Claude in the project window builds.

**Every project is its own repository and its own website.** Each project gets its own folder next to `class-board-2026` in your course folder and its own repository on GitHub, under your personal GitHub account, public. Each has a public **project website** — a page that presents the project — and at the end of each project you add it to the **class project wall**, https://tigp-experimental-methods.github.io/showcase-2026/, the page where everyone's projects appear as they are finished. §1.4 Steps 2–4 explain all three; Project 2 and the later projects follow the same pattern.

---

## 1.1 Setup check

Everyone needs: the laptop prepared as in [chapter 0](ch0-before-day-1.md) · Claude access — the invitation was e-mailed on Sunday 6 Sep; you are signed in to the Claude Code extension · the class repository cloned (downloaded with its history) into your course folder · the ESP32 board (provided) and a USB-C data cable (the instructor has spares).

Open the class repository (*File → Open Folder…* → `class-board-2026`), open the Claude Code panel and type `/tutor L1`. The tutor first checks GitHub for updates to itself and the workbook and brings them in — the instructor edits both between sessions, so you always work from the latest version. Answer its questions: language, what you have built before, `expert` if you want whole recipes instead of pacing. The tutor then runs the toolchain check (the toolchain is the compiler and helper programs that turn source code into firmware, the program that runs on the microcontroller), creates your branch `w1-<name>` in the class repository (a branch is a separate line of work inside a repository; `main`, the version everyone builds on, is protected, so your files in the class repository go on your branch) and creates `docs/students/<name>/PROGRESS.md` — your handover notes: done / verified / next / gotchas, the file the next session reads first.

- [ ] `git --version` · `gh auth status` · `pio --version` · board on a port (`pio device list`) · signed in to GitHub in the browser · your Cloudflare account exists and is connected to GitHub (you may need both hosts today — a static page goes on GitHub Pages, anything with a backend, a bot webhook or a secret on Cloudflare Pages + Workers)
- ✔ **toolchain OK**

**The tutor does the mechanical work and you approve it** — creating the project folder and repository, enabling GitHub Pages, cloning the wall, writing the wall entry, running the build script and the secrets check. You do the part that is the learning: write the vision, review the plan, name the test, report what you see, and press *Commit* / *Sync Changes* in Source Control. **The instructor is not the help desk during class; the tutor is — only when the tutor cannot fix it do you go to the instructor.**

If a tool fails: the tutor gives the fix when you ask for it; if that does not solve it, e-mail the instructor with a screenshot and start Project 1 anyway — it needs only VS Code, Claude and GitHub.

## 1.2 Introduction to AI and the tools we use — the reading list

This is not a second lecture. Each row is one slide section, its claim and the rule of thumb the slides draw from it. Read the slides for the argument; come back to this table when you need the rule.

| Slides | The claim | Rule of thumb |
|---|---|---|
| 13–15 | **How LLMs work.** Text becomes tokens (pieces of a few characters), tokens become numbers; one operation repeated — predict the next token; training fits the weights once, inference runs them. | Fluency is not correctness. The model does not learn from your conversation. |
| 18–20 | **Context.** Every message resends the whole conversation (the context window: everything so far — your messages, files read, tool output). The unchanged start is cached and cheap; off-topic history is paid for and competes for attention. | Keep context small: **one topic per session.** New topic, new chat. |
| 21–22 | **Files and Markdown.** A dropped-in PDF or image is an expensive prefix, resent on every turn and mostly noise. | Let a separate session read each file and write a detailed Markdown summary; the main session works from the digest. |
| 23–24 | **Model tiers.** Haiku · Sonnet · Opus · Fable, the same idea at different sizes, at about 1 : 3 : 5 : 10 cost. | The strong model plans and checks; cheap models do the work, each in its own fresh context, in parallel. |
| 25 | **The AI method in 5 steps** — the most important slide in the talk. | §1.3 below. |
| 26 | **Reviewing.** Never let the author grade its own work — same context, same blind spots. | An independent reviewer that sees only the spec and the output — a fresh Claude session, not the one that wrote them; tests written first; loop, don't hope. |
| 27 | **Long projects.** A session is not a project. Long work is a chain of short sessions joined by documents on disk. | At about 50 % context, write the handover and commit; start fresh. The disk is the memory. |
| 28 | **CLAUDE.md, memory, skills, MCP, hooks, extensions** — six places to put what the agent should know, each costing context differently. | Keep `CLAUDE.md` under a page. Prefer hooks for anything that must always happen. |
| 29 | **Workflow must-dos.** | Put all needed data in the prompt · one topic per session · summarise files first · cheap workers, strong planner · verify independently ([C.0c](chC-cheat-sheets.md#c0c-workflow-must-dos)). |
| 31–34 | **Failure modes.** Hallucinations follow from the process; beyond them the model invents specifics, agrees with you, makes small errors in correct-looking structure, drops requirements, compounds errors, applies stale context. An agent adds: gaming the test, claims without running, scope creep, loops, wrong target, destructive actions. | Use AI where checking is easier than doing. Agent failures are caught by mechanism — hooks, git, tests — not by reading harder ([C.0d](chC-cheat-sheets.md#c0d-when-things-go-wrong)). |
| 36–37 | **Tools.** The slides compare four ways to run an agent (Claude Cowork, Claude Design, OpenAI's Codex app, VS Code + agents). Our choice, and the only one this course uses: **VS Code + the Claude Code extension** — low lock-in; the whole folder is the context. Know the window: new session · prompt · permissions · model and thinking level · context level · menu · extensions · git · file explorer. | Anything with a codebase, or that you will still be working on next year → VS Code. |
| 38 | **Oops, I made a mistake.** | Save your tokens: stop the execution. Don't poison your context: rewind. |
| 39 | **Context is full.** Start a new session. | First, prompt: *"Please finish what you are working on and document anything from this session that may be useful to future Claude sessions in .md files in this directory and a handover.md file to allow Claude to continue our work in a new session."* |
| 40 | **Compaction is lossy.** Clicking the context icon deletes most of the context without saving useful knowledge anywhere. | Have Claude document the session in hierarchical, searchable `.md` files instead; always a log and a handover file. |
| 41 | **Menu items.** Permissions and mode; model selection; thinking on (the instructor uses medium or high). | Check your usage often. Check whether unnecessary skills or hooks clutter every session. |
| 42–49 | **Git.** Why version control (safety net, understanding, collaboration; git is the tool, GitHub hosts a copy). Four words: repository, commit (a named snapshot), diff (what changed), history. The loop edit → stage → commit **in VS Code's Source Control panel — no terminal required.** Branches: main always runs. GitHub: push, pull, clone, pull request. `.gitignore` and undo. | Commit small and often. Commit before the agent starts; ask it to commit as it goes; review the diff, not the file; give it a branch; never let it rewrite history. Tests go in git too. |
| 51–52 | **Deployment.** GitHub hosts code; GitHub Pages hosts static pages; Cloudflare Pages + Workers host apps with a backend; YouTube unlisted hosts video. The loop: commit → push → the host builds → live. | Static page → GitHub Pages is enough; stores data, calls an API with a key, or runs on a schedule → Cloudflare Workers. Secrets never go in the repository. |
| 54–59 | **Apps that talk to you.** Telegram (@BotFather, the easiest start), LINE (Messaging API, what everyone in Taiwan has), ntfy.sh for alerts only; a webhook on a Cloudflare Worker; Google Sheets as a database; an LLM inside your app via an API key. Two ways AI makes software smarter: A — AI-written code (default); B — an LLM in the loop, at the hard step. | Tokens are passwords. Start with Telegram, then port to LINE. Default to A; reach for B at the hard step. |
| 61–62 | **Video.** Script first, pictures last: document → script → audio → visuals timed to the audio. The lab's pipeline is public: https://github.com/iams-yb-lab/show-your-work (five Claude skills). Pictures of hardware: Blender first, Unreal for scenery. | Label generated imagery. |

## 1.3 The "AI method" in 5 steps

The most important slide in the talk (slide 25). Both projects today, and everything in Workshops 2 and 3, follow it.

1. **Vision.** Describe what you want, with as much detail as possible.
2. **Specification / Plan.** Get AI to produce a detailed specification — plan the project. Break the project into many small tasks with testable deliverables. **Ask AI to ask you questions.**
3. **Review.** Review the plan yourself; have AI review the plan to identify improvements and flaws — in a fresh Claude session that did not write it. **Iterate the plan: the first plan is never the last plan.**
4. **Code** (using agent swarms). Tell AI to run swarms of agents in parallel to complete the build — subagents, each with its own fresh context.
5. **Test / Debug / Verify.** Ensure your plan and spec include methods to test the code. Fix problems one at a time. Iterate.

**Never trust AI without testing and verifying.**

## 1.4 Project 1 — Build a web app (a simulator or a game)

**What do you want to make?** Suggestions: loading a freight train game · inverted pendulum simulator · phase-locking coupled pendula · unfair golf · billiards · a calculator or simulator for something from your research. Pick something you understand well enough to know when it is wrong.

The five steps from the slides, as a walk-through. Every step ends with *what you should see*.

### Step 1 — Decide what to make, and write the vision

Write the vision in your own words, in as much detail as you can: what is on the screen, what the user can change, what must be physically right, what it runs on. A paragraph is enough; a page is better. Example (write your own):

> An inverted pendulum on a cart, drawn side-on in the browser. Sliders for pendulum length, mass and friction; a button that nudges the pendulum; a switch that turns a balancing controller on and off; a plot of angle against time under the drawing. The motion is integrated from the equations of motion, not animated to look right. Hanging down, with no friction and a small nudge, the swing period must be 2π√(L/g); with friction zero the total energy must stay constant to 0.1 % of its starting value over a long run. One page, `app/index.html`, plain JavaScript, no build step, works on a phone.

*What you should see:* a vision you could hand to a colleague and they would build the same thing.

### Step 2 — Follow the AI method to a working local demo

**Repository.** Every project in this course is its own repository, public, under your own GitHub account. In VS Code: create a folder next to `class-board-2026`, named for the project (for example `pendulum-sim`), open it in a second window (*File → Open Folder…*), *Source Control → Initialize Repository*, then *Publish Branch* → **public**. The app itself lives in `app/` (`app/index.html`); the root of the repository is kept for the project page (Step 4). The tutor checks this before you start and asks you to push (upload your commits to GitHub) at every milestone — plan reviewed, first working version, deployed, project page written. Git is used from VS Code's Source Control panel throughout the course; when a terminal command is unavoidable, Claude runs it and tells you what it did.

*What you should see:* a second VS Code window with an empty project; Source Control shows no changes; the repository exists on GitHub and is public.

**Specification and plan.** In the project window, open Claude Code and paste your vision with this:

> Here is my vision: […]. Ask me questions until you can write a detailed specification. Then write `SPEC.md` — what it does, what the user sees, the physics or rules with the equations, and how we will test that it is right — and `PLAN.md`, the build broken into many small tasks, each with a testable deliverable. The app lives in `app/index.html`; keep the repository root free for a project page. Do not write any code yet.

Answer the questions. Then **read both files** — this is the step most people skip. Check that:

- the spec computes the physics from the parameters rather than drawing a picture that happens to look right;
- the spec names at least one test you can predict without the program: a value you can work out by hand (a pendulum period, a cut-off frequency), a conservation law (energy, momentum), a limiting case (zero friction → constant speed; zero load → the train accelerates at F/m). This is *one* of the checks, not the whole project — but it is the one that catches "right structure, wrong sign";
- every task in the plan says what "done" looks like.

**Review.** Independent means a different context. Open a new Claude session — one that has not seen the files being written — and ask:

> Read `SPEC.md` and `PLAN.md`. You did not write them. Find flaws, missing requirements, physics errors and tasks that cannot be tested. Do not approve anything; list problems, most serious first.

Fold what matters back into the files. The first plan is never the last plan. Then **commit** (save a named snapshot): Source Control → stage both files with **+** → message `spec and plan v1` → *Commit* → *Sync Changes* (push). A clean commit before the agent starts is your undo button; the push is your backup. **Milestone: plan reviewed.**

**Code.** Back in the project session:

> Work through `PLAN.md` one task at a time. Where tasks are independent, use subagents in parallel. After each task, run its test, then commit with a message that says why. Change nothing outside the current task. Tell me when you are done or blocked.

Read each permission prompt (the approval request before Claude runs a command or edits a file) before you approve it. *What you should see:* files appearing; commits appearing in Source Control; each diff readable.

**Test, debug, verify.** Open `app/index.html` in a browser (double-click it, or ask Claude to start a local server and give you the address). Run the checks the spec names yourself — set the parameters, read the numbers off the page, compare with what you predicted. Write the comparison into `SPEC.md`. If one is wrong, that is the exercise: describe exactly what you see and what you expected, and fix **one problem at a time**. If the agent tries the same fix three times, stop it, rewind, and rethink the plan.

*What you should see:* the page runs; predictions and results side by side in `SPEC.md`; a commit history that tells the story. Push. **Milestone: first working version.**

**When the context fills** (the context indicator in the Claude panel is about half full, or answers get worse): paste the slide-39 prompt — *"Please finish what you are working on and document anything from this session that may be useful to future Claude sessions in .md files in this directory and a handover.md file to allow Claude to continue our work in a new session."* — commit, start a new session, and tell it to read `handover.md` first.

### Step 3 — Deploy it on the web: GitHub Pages and/or Cloudflare Pages

Deploy means publish it so anyone with the address can open it. Push first: Source Control → *Sync Changes*. Which host depends on what you built — **you may need both, so have both accounts ready.** A static page (the project page; an app that runs entirely in the browser, like today's simulator or game) goes on **GitHub Pages**: on GitHub, your repository → *Settings → Pages → Deploy from a branch → main → / (root) → Save* — or the tutor enables it for you with one `gh api` command and tells you. A minute later the repository is a website at `https://<user>.github.io/<repository>/` and the app is at `https://<user>.github.io/<repository>/app/`. (Until Step 4 the root address shows nothing useful — that is expected.)

- Anything with a backend, a bot webhook or a secret (an API key, a bot token, a scheduled task) goes on **Cloudflare Pages + Workers** — dashboard → *Workers & Pages → Create → Pages → Connect to Git* → your repository → branch `main` → build command **blank**, output directory `/` → *Save and Deploy*. Address: `https://<project-name>.pages.dev/app/`. The project page (Step 4) is on GitHub Pages either way.
- Or ask Claude: *"Deploy this on GitHub Pages"* or *"Deploy this on Cloudflare"* — you supply the accounts, it does the wiring. Read what it changes.

*What you should see:* the app's address opens on your phone; move a slider. From now on every push republishes the page. **Milestone: deployed.**

### Step 4 — Create the report: the project website

The report is a public **project website** — `index.html` at the root of your repository, served by GitHub Pages at `https://<user>.github.io/<repository>/`. It explains the concept or the game in detail, so that someone who has not seen the app understands what it does and why the numbers are right:

- the title and your name;
- what it is and why it is interesting;
- how it works — the physics or the rules, with the equations;
- a picture, a GIF (a short looping animation — a screen recording of the app moving is ideal) or a short video of it working;
- what was verified — the checks the spec named, predicted next to measured;
- a link to the live app (`…/app/`) and a link to the repository.

Ask Claude for a draft from `SPEC.md`, the commit history and your notes — *"Write `index.html` at the repository root: a project page with these sections […]; plain HTML and CSS, no build step; link to `app/` and to the repository on GitHub."* Then edit it: the page is yours, in your words. `README.md` stays the developer-facing document — how to run it, how the code is organised, how it is tested; GitHub shows it on the repository's front page. Commit, push. **Milestone: project page written.**

*What you should see:* the project page opens at the root address, on a phone too; its link opens the app.

### Put it on the class project wall

The class project wall — https://tigp-experimental-methods.github.io/showcase-2026/ — is a page of cards, one per project: a picture, the title, your name, two sentences, and the buttons *Open the app · Project site · Video · Code*. It refreshes itself every minute; in class it is on the projector, so everyone sees each other's projects appear. It is the class noticeboard — for seeing each other's work as it appears, borrowing ideas and talking. At the end of each project you add your entry with the tutor:

1. The wall is the repository `TIGP-Experimental-Methods/showcase-2026`; every student can push to it. The first time, Claude clones it next to `class-board-2026` (it runs `gh repo clone TIGP-Experimental-Methods/showcase-2026` and tells you); afterwards, open that folder and *Sync Changes* first, so you have everyone's latest entries.
2. Write `projects/<your-github-username>--<slug>.json` (the slug is a short name for the project — `alice--pendulum-sim.json`) with the fields `title`, `student`, `github` (your username), `project` (`"1"`, `"2"`, `"3"` — your whole instrument from Workshops 2–3, one card — or `"extra"`), `blurb` (two sentences: what it does, and one thing that works or surprised you), `live_url` (the app's address; empty for an app that runs only on the board), `site_url` (the project website), `repo_url`, `image` (`images/<the same name>.png`, `.jpg`, `.gif`, `.webp` or `.mp4`, under 8 MB — a GIF or a short phone video of the thing moving is best), `video_url` (optional) and `updated` (`YYYY-MM-DD`). The wall's `README.md` documents the format; the tutor reads it and drafts the file with you.
3. Copy the picture into `images/`.
4. Claude runs `python scripts/build.py` — it validates every entry and says what is wrong.
5. Source Control: stage both files, commit (message `add <title>`), *Sync Changes*. Within a minute your card is on the wall — on the projector, if you are in class.

Update the entry whenever the project moves on: a new picture, a better blurb, the `updated` date.

### Step 5 — Improve the presentation (optional extension)

Markdown → slides → website → YouTube video. The lab's show-your-work skills (`slide-deck`, `technical-report`, `education-video`) turn your project page into each of these; the order is document → script → narration → pictures timed to the audio (slide 61). This is also the route to the presentation at the end of the course.

**Habits that make this safe** (slides 44, 48): commit before the agent starts · ask it to commit as it goes · review the diff, not the file · one idea per commit · never let it rewrite history — if it asks to force-push or reset, say no.

## 1.5 Project 2 — Control a microcontroller over the net with your phone

**Aim** (slide 67): create a phone app that lets you control and measure from hardware — the ESP32 — over WiFi. Example: a phone app that controls the brightness and colour of the ESP32's LED. Follow the AI method again; the vision is now about a physical thing you can see change. A camera is available for anyone who wants to try a camera app: an **ESP32-S3-N16R8-CAM development board with an OV3660 camera module** (Jinhua #41395, https://jin-hua.com.tw/page/product/show.aspx?num=41395&kw=ESP32&lang=TW) — ask the instructor.

**Two steps.** Step 1 flashes the class repository's reference firmware and phone app onto your own board and proves that the board, the cable, the WiFi and your phone all work. **Starting from a known working hardware baseline is an essential part of any experimental physics workflow — it separates hardware problems from software problems.** Step 2 is your own app, by the AI method. If your own build stalls, the class firmware remains the fallback, so you always have a working app on the phone.

### The facts you need about the board

- The board is a **Jinhua #40729 ESP32-S3 N16R8 dev board** (the development board: the ESP32-S3 microcontroller — a small computer on a chip, with WiFi — on a small board with a USB-C connector and pins). Its RGB LED is a WS2812 on GPIO 48 (a GPIO is a general-purpose pin); the antenna is a u.FL connector. Use the connector marked *USB* (native USB, not *UART*) and a data cable.
- Firmware is built with **PlatformIO** (the tool and VS Code extension that compiles and flashes — writes onto the board over USB) and the **Arduino framework**. Board name in PlatformIO: `esp32-s3-devkitc-1`.
- **The first flash of a factory-fresh board fails once, by design.** `upload` ends with *"No serial data received"*: hold **BOOT**, tap **RST**, release BOOT. The board comes back on a **new COM port** — run `pio device list` again and flash to that port (`--upload-port COMx` if PlatformIO picks the wrong one). After that every flash resets the board by itself.
- **The port disappears and reappears at every reset** — the USB-to-serial converter is inside the chip. A serial monitor must reconnect after every flash and the first boot lines may be missing. Normal.
- **Two ways onto WiFi.** The board can run its own access point (its own WiFi network, which your phone joins) — no password of yours involved. Or it joins an existing network, in which case the network's name and password go in a git-ignored file `firmware/include/secrets.h` (git-ignored: listed in `.gitignore`, so git never commits it).

> **Secrets never enter a Claude interaction.** A secret is a password, a WiFi key, an API token — anything that lets someone else in. Never type one into a Claude chat, a prompt, `PROGRESS.md`, `SPEC.md`, a commit message, a pull request or a screenshot: transcripts are stored, repositories are shared or public, commits are forever. The pattern: Claude (or you) creates `secrets.h` from `secrets.h.example` with the network name filled in and the password as a placeholder such as `PUT-THE-PASSWORD-HERE`; **you** type the password into that file in the editor; then ask Claude to run the secrets check — `git check-ignore -v firmware/include/secrets.h` must print a line (nothing printed → stop, do not commit, tell the instructor); before every commit, `secrets.h` must not appear in Source Control's changes. The tutor never asks for a secret and never repeats one. Pasted one anyway? Delete it from the chat if you can, treat it as exposed, tell the instructor.

### Step 1 — The hardware baseline: flash the reference firmware and phone app

The class repository already contains a firmware and a phone app that do what Project 2 asks, and more: `firmware/` (PlatformIO, Arduino) and `host/pwa/` (the phone app — a web page served by the board). The base block controls the LED and reports a counter and the chip temperature; the app charts any value and has an alarm engine. The code is already in your clone; the tutor walks you through building and flashing it with Claude. From the class repository root, one command per line:

```sh
pio device list
pio run -d firmware -e esp32s3-sim -t upload
pio run -d firmware -e esp32s3-sim -t uploadfs
```

`esp32s3-sim` is the build for a bare dev board (SIM mode: the firmware fakes the class-board hardware it does not have); `uploadfs` copies the phone app onto the board. The first `upload` of a factory-fresh board ends with *No serial data received*: hold **BOOT**, tap **RST**, release BOOT, `pio device list` again, flash to the new port — once. Then: LED blue = the board's access point is running · your phone or laptop joins the WiFi `instrument-XXXX` (the label on the board, or the boot log), password `instrument` · open **http://192.168.4.1** — type the `http://`, stay connected when the phone warns about no internet, mobile data off on Android · tap *Red* on the Base tab; the chart plots `base.counter`; the temperature moves when you put a finger on the chip.

*What you should see:* from the phone or the computer you change the LED's colour, and live values from the board update on the page. Write what you saw into `PROGRESS.md`. **From here on, everything is software** — if something later does not work, the hardware is not the reason.

The same firmware is the base for Projects 3a and 3b, and `firmware/PROTOCOL.md` describes every message it understands — Claude can read both while it builds yours.

### Step 2 — Your own app, by the AI method

**Vision.** A page served by the ESP32 itself over WiFi, opened in the phone's browser: a colour picker and a brightness slider for the LED, and one live measurement that updates on its own — the chip temperature, an ADC (analog-to-digital converter) pin in volts, a counter. You decide what to measure.

**Repository.** Project 2 is its own repository, like Project 1: a folder next to `class-board-2026`, named for the project (for example `esp32-phone-app`), opened in its own VS Code window, *Source Control → Initialize Repository*, *Publish Branch*, public. The firmware goes in `firmware/`; the repository root is kept for the project page. The tutor checks this before you start. Commit before Claude starts; push at every milestone.

**Specification and plan.** Paste the vision and the board facts above, and add:

> Scaffold a PlatformIO project in `firmware/` (Arduino framework, board `esp32-s3-devkitc-1`, WS2812 LED on GPIO 48). The board runs its own WiFi access point and serves one web page with a colour control, a brightness slider and one live readout. The class repository next to this one (`../class-board-2026`) has a working reference — read its `firmware/` and `firmware/PROTOCOL.md` for the access point, the web server and the LED — but build mine from my specification. Write `SPEC.md` and `PLAN.md` first, with tests I can do with my phone and eyes; ask me questions before writing them. Do not write code yet. Never ask me for a WiFi password.

Read the plan. Name the test yourself: *tap red → the LED is red; slide brightness to zero → the LED is off; the readout changes when I warm the chip with a finger* — or, for a counter that counts at a fixed rate, the value it must show after a known time. Then review in a fresh Claude session, iterate, commit, push.

**Code, then flash.** Let Claude build; `pio device list` for the port; flash from the project folder, one command per line: `pio run -d firmware -t upload`. Your board went through the first-flash trap in Step 1, so it now resets by itself. Watch the boot log (`pio device monitor`, 115200) for the network name and address the firmware prints.

**Verify.** Phone joins the board's network (stay connected when the phone warns there is no internet; on Android switch mobile data off), open the address the board printed — type the `http://`. Run your test. Write what you saw into `PROGRESS.md`, then commit and push.

*What you should see:* your phone changes the LED's colour and brightness; one number on the page moves by itself and you can say why.

**If your own build stalls:** flash the class firmware again (Step 1) — you have a working app on the phone today — and continue your own build between workshops. To make the class firmware *yours* in the meantime, change one thing: a command in `firmware/src/blocks/base/BaseBlock.cpp` (`handle()` acts on a command, `status()` fills the numbers the phone sees) and a control in `host/pwa/panels/base.js` (`render()` builds the controls, `onStatus()` updates the readouts); `uploadfs` again.

### The project page and the wall

The project website is `index.html` at the root of the Project 2 repository, as in Project 1 — with one difference: the live app runs on the board, so nobody can open it from the internet. The page carries a short video or GIF of the phone changing the LED instead, and there is no "live app" link. Then add the wall entry (§1.4, *Put it on the class project wall*) with `project` `"2"`, `live_url` empty, and the video or GIF as the image.

### Measure something — ideas

The chip's own temperature (`temperatureRead()`, coarse steps of about 1 °C — a finger on the chip moves it) · the counter (counts at a fixed rate, so you can predict its value after a known time) · an ADC pin in volts (GPIO 4 floating, or with a jumper wire in it). *One idea with a prediction in it:* sample the ADC continuously into a buffer, let the phone set an averaging length N, and show the mean of the last N samples and the noise of such N-sample averages. For independent samples that noise falls as 1/√N — from N = 1 to N = 256 a factor 16. It will not obey exactly; saying what you see and why (mains pickup, a touched wire) is the interesting part.

## 1.6 Between workshops — `/tutor HW1`

**Before the next workshop: complete the preparation, improve your apps, build and have fun.** The apps are your Project 1 and Project 2 — try the ideas above, add a measurement, make the project pages better. The tutor is there whenever you want it: `/tutor HW1` (HW1 means "between workshops"). Both projects come back in Workshop 2, where your Project 2 app grows into the front end of the instrument.

**Preparation for Workshop 2** — the only thing needed before Fri 18 Sep:

- [ ] **KiCad 10 installed and opened once** — the free program the class board is drawn in; Workshop 2 needs it running (`SETUP.md` step 9, or tell Claude: *"install KiCad 10 as in SETUP.md step 9"*). ✔ *Help → About KiCad* shows 10.x.
- [ ] **a JLCPCB account** — the factory that makes and assembles our boards: https://jlcpcb.com. Sign up; nothing to order. Parts come from the JLCPCB parts library (no LCSC account needed).

**Your notes.** `docs/students/<name>/PROGRESS.md` in the class repository (on your branch `w1-<name>`, with the addresses of your project repositories and pages) and `handover.md` in each of your own repositories stay in step — end every session with both, pushed. When you want your class-repository notes merged, open a pull request (a request to merge your branch into the shared project; someone reviews it first) from `w1-<name>`: push the branch; GitHub offers *Compare & pull request*. **Your part of the class board is assigned at the start of Workshop 2.** Reading before then: [chapter A](chA-electronics-from-zero.md) where you need it; [chapter C](chC-cheat-sheets.md) C.1–C.2. How the projects count is on the course site.

## 1.7 Beyond the baseline

The class board's hardware is fixed by budget and timeline; the software, firmware and app are open, and that is where you show what you can do. The extension we most encourage: **talk to your instrument from LINE or Telegram** — push notifications when a value drifts or an alarm fires, bot commands that read a value or switch an output from your phone, from anywhere (slide 54: start with Telegram, then port to LINE; tokens are passwords). Also: a data logger, remote access with a Python script that runs a sweep, a controller block, a second board. Whenever you are ahead, ask what problem in your lab this could solve. **Build something great.**

---
**Tutor notes (`/tutor L1`, `/tutor HW1`).** Assume competence; offer expert mode. **At the start of each project check the repository:** its own folder next to `class-board-2026`, named for the project, its own repository under the student's GitHub account, public (Source Control → Initialize Repository → Publish Branch, or — after asking — you run `gh repo create <user>/<name> --public --source . --push` and say what you did, whichever is faster); Project 1's app in `app/`, Project 2's firmware in `firmware/`, the root free for `index.html`. If it is not set up that way, set it up with the student before anything else — you do the mechanical part, they approve. The same for enabling GitHub Pages, the wall clone and entry, `scripts/build.py` and the secrets check. The instructor is not the help desk during class; you are — only when you cannot fix it does the student go to the instructor. Prompt a push at every milestone: plan reviewed, first working version, deployed, project page written. Pace the AI method, do not run it: for each project the student writes the vision; Claude in the *project* window writes `SPEC.md`/`PLAN.md`; you read them with the student and refuse to move to code until the student has reviewed both and can name at least one test they can predict without the program. Insist on an independent review in a fresh Claude session and one iteration of the plan. Before every commit ask *"what do you see?"* — never accept "it works"; the observation goes into `PROGRESS.md`. Project 1: reject a spec that draws a picture instead of computing the physics; a static page deploys on GitHub Pages, anything with a backend, a bot webhook or a secret on Cloudflare Pages + Workers — the student may need both, so the setup check asks about both accounts; the project page is in the student's words — Claude drafts, the student edits. **Project 2 is reference first:** Step 1 is flashing the class firmware and app (`pio run -d firmware -e esp32s3-sim -t upload`, then `-t uploadfs`) and controlling the LED from the phone — the known working hardware baseline that separates hardware problems from software problems; only then the student's own app in its own repository. When the own build stalls, the class firmware is the fallback: flash it again and let them change one thing in `BaseBlock.cpp` + `panels/base.js`. Know the first-flash trap: *No serial data received* = hold BOOT, tap RST, release, `pio device list`, new COM port, flash again — once; the port vanishing at every reset is normal. Never run an upload without naming the environment and the port. Never handle secrets (COURSE-GUIDE rule 15): the student types a WiFi password into `secrets.h` in the editor, you run `git check-ignore -v` to prove it is ignored, and `secrets.h` must never appear in Source Control before a commit. **At the end of each project add the wall entry with the student** (COURSE-GUIDE, *Repositories, project websites and the class project wall*): clone or sync `showcase-2026`, draft `projects/<github-username>--<slug>.json` from the wall's README, copy the picture into `images/`, run `python scripts/build.py`, the student commits both files from Source Control and pushes. Create `w1-<name>` at the start; nothing goes on `main`; `docs/students/<name>/PROGRESS.md` in the class repository and a `handover.md` in each of the student's own repositories are kept in step — end every session with both. Between workshops: encourage improving both projects; the only preparation for Workshop 2 is KiCad opened and a JLCPCB account; block assignment is Workshop 2 — do not assign or discuss blocks. Grades: state the assessment split once if asked; the rest is the instructor's.
