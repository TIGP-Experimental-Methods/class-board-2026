# Chapter 0 — Before day 1

The first class is hands-on from the start: everyone types `/tutor L1`, builds a simulator with Claude, deploys it (publishes it so it is live on the web) before the break, and after it flashes their own firmware (writes the program that runs on the microcontroller onto the board over USB) to an ESP32 (the microcontroller we use — a small computer on a chip, with WiFi). All of that only works if the tools already work on your laptop. Tooling terms are explained the first time they appear and collected in the glossary, [chapter C](chC-cheat-sheets.md#c0-words-we-use). You install VS Code and Claude Code by hand (0.2–0.4); Claude installs the rest (0.5). Every step has a ✔ check. If you are stuck in 0.1–0.4, email the instructor (s.p.bennetts@g.iams.sinica.edu.tw) with a screenshot. From 0.5 onwards work with the tutor (`/tutor CH0`, see 0.5); when you want the fix, ask it for the fix; if that does not solve it, note the error and email it to the instructor.

## 0.1 A laptop you can install software on
Windows 10/11, macOS or Linux; admin rights; ~10 GB free. The connector on the dev board (the development board: the ESP32 on a small board with a USB connector and pins) is **USB-C**. Bring a **USB-C data cable** that fits your laptop — USB-C to USB-C, or USB-A to USB-C; charging-only cables do not carry data and are the number one flashing failure. Most of you receive the board on day 1.

## 0.2 Visual Studio Code
Install from https://code.visualstudio.com/download with default options (Windows: tick *Add to PATH* and *Open with Code*).
✔ *Help → About* shows a version.

## 0.3 Claude Code extension, signed in to the course organization
In VS Code press `Ctrl+Shift+X` (macOS `Cmd+Shift+X`), search **Claude Code** (publisher Anthropic), Install. Accept the e-mail invitation to the course's Claude organization and sign in with that account. Docs: https://code.claude.com/docs/en/vs-code
✔ The Claude icon is in the side bar; "hello" gets an answer.

## 0.4 Create a local folder for the course work and open it in VS Code
Make an empty folder for everything you do in this course, e.g. `C:\Users\<you>\tigp-2026` or `~/tigp-2026`. **Not** inside OneDrive, Google Drive, Dropbox or iCloud (sync corrupts git repositories — the project folders whose history the tool git keeps — and build caches), and **no spaces** in the path. In VS Code: *File → Open Folder…* → that folder.
✔ The folder name is in the VS Code title bar; the Claude Code panel opens with that folder as its working directory.

## 0.5 Let Claude do the rest
Open the Claude Code panel and paste exactly this:

> Read https://raw.githubusercontent.com/TIGP-Experimental-Methods/class-board-2026/main/SETUP.md and follow it step by step. Ask me before installing anything, and tell me what each step is for in one sentence.

Claude detects your OS and sets up, asking before each install:
- **git** — the tool that records the history of a folder of files. It asks for your name and e-mail: use the **same e-mail as your GitHub account** (GitHub is the website where repositories are stored and shared), or your commits (saved snapshots of your work) will not be attributed to you.
- **Python via uv**.
- **GitHub CLI** (`gh`, GitHub's command-line tool) and `gh auth login`.
- A check that you are a member of the class organization `TIGP-Experimental-Methods` (you can clone without it; you need it to push and open pull requests).
- A clone (a downloaded full copy) of the class repository `class-board-2026` into your folder.
- **PlatformIO** — the tool that builds and flashes the firmware (VS Code extension + `pio` command) — and one build of the simulator environment, which **downloads the ESP32 toolchain (~1 GB) — let it finish now, not on day 1** (the toolchain is the compiler and helper programs that turn source code into firmware).
- **KiCad 10** — the free program the class board is drawn and laid out in; optional now, needed for homework 1.

It will stop and ask you to do three things in the browser: create a **GitHub account** if you have none (professional username, two-factor on), and send the username to the instructor · accept the **invitation to the GitHub organization** `TIGP-Experimental-Methods` (e-mail, or https://github.com/orgs/TIGP-Experimental-Methods/invitation) · a **Cloudflare account** (0.7). `gh auth login` is interactive: Claude tells you what to type and click; you run it.

At the end Claude prints a report ending in **toolchain OK**, or the first failure with the exact error. If it fails and the fix is not obvious: *File → Open Folder…* → `class-board-2026` (the folder Claude just cloned), open Claude Code there and run `/tutor CH0` — the tutor lives in that folder and is not found from the folder above it. If the clone itself failed, email the report to the instructor.
✔ The report says **toolchain OK**.

## 0.6 The ✔ checks
The same list Claude prints — so you can verify by hand in the VS Code terminal (the text window where you type commands). One command per line; on Windows the default terminal does not accept `&&` between commands.

```sh
git --version
git config --global --list                         # name, e-mail, init.defaultBranch=main
uv --version
uv run --python 3.12 python -c "print(2**10)"      # 1024
gh auth status                                     # logged in as <username>
gh api user/memberships/orgs/TIGP-Experimental-Methods --jq .state   # active
ls class-board-2026/firmware/platformio.ini        # exists
pio --version
cd class-board-2026/firmware
pio run -e esp32s3-sim                             # ends with [SUCCESS]
pio device list                                    # a port, only if you already have the board
```

KiCad, if installed: it starts and *Help → About KiCad* shows 10.x. The PlatformIO alien-head icon is in the VS Code side bar. If you have the board: it goes on the port marked *USB* (native USB, not *UART*); Windows and macOS need no driver; Linux needs the `dialout` group (the user group allowed to open serial ports) and PlatformIO's udev rules (the file that lets ordinary users talk to the board; `SETUP.md` step 7 has both). No port → another cable, or hold **BOOT**, tap **RST**, release BOOT, retry. A brand-new board shows up as USB device `303A:4001` (its factory firmware) and needs that BOOT+RST once at its first flash, after which it comes back as `303A:1001` on a different port. You flash your own board in class on day 1, so you will meet this once — it is expected, not a fault.

## 0.7 A free Cloudflare account, connected to GitHub (manual)
On day 1 you deploy your first program to the public web with Cloudflare Pages (a free service that turns a repository into a public web page), straight from a GitHub repository, no build step. Sign up at https://dash.cloudflare.com/sign-up (free plan; verify the e-mail). Then, once: *Workers & Pages → Create → Pages → Connect to Git* → authorise Cloudflare for your GitHub account — and stop there; the project itself is created in class.
✔ Signed in to the dashboard; the *Connect to Git* screen lists your GitHub account. (If sign-up fails, GitHub Pages is the fallback in class; nothing else to install.)

## 0.8 Know what you are going to build
Everyone builds the same instrument: one class board with five blocks — **B1 inputs · B2 power · B3 outputs · B4 switching · B5 digital/TRIG** — one block per student, one shared repository, one phone app. On day 1 you also build something of your own first: a physics simulator on the public web. Read the course site's *Project* page.

---
**Tutor notes (`/tutor CH0`).** Run `SETUP.md` (repository root) step by step under its rules: detect the OS, one sentence per step, ask before every install, run each ✔ check. Stop at the first failure; suggest the fix; write the error and the fix into `docs/students/<name>/PROGRESS.md` (the handover-notes file: done, verified, next, gotchas) under *gotchas*. If it cannot be fixed, the student emails the report to the instructor and you continue with the steps that do not depend on it. Do not install anything the student did not ask for.
