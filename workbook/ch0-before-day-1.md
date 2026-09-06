# Chapter 0 — Before day 1

The first class is hands-on from the start: everyone types `/tutor L1`, builds a simulator with Claude, deploys it to the public web before the break, and flashes their own firmware to an ESP32 after it. All of that only works if the tools already work on your laptop. You install VS Code and Claude Code by hand (0.2–0.4); Claude installs the rest (0.5). Every step has a ✔ check. If you are stuck, ask the tutor for the fix; if that does not solve it, note the error and email it to the instructor (s.p.bennetts@g.iams.sinica.edu.tw).

## 0.1 A laptop you can install software on
Windows 10/11, macOS or Linux; admin rights; ~10 GB free. The dev board's connector is **USB-C**. Bring a **USB-C data cable** that fits your laptop — USB-C to USB-C, or USB-A to USB-C; charging-only cables do not carry data and are the number one flashing failure. Most of you receive the board on day 1.

## 0.2 Visual Studio Code
Install from https://code.visualstudio.com/download with default options (Windows: tick *Add to PATH* and *Open with Code*).
✔ *Help → About* shows a version.

## 0.3 Claude Code extension, signed in to the course organization
In VS Code press `Ctrl+Shift+X` (macOS `Cmd+Shift+X`), search **Claude Code** (publisher Anthropic), Install. Accept the e-mail invitation to the course's Claude organization and sign in with that account. Docs: https://code.claude.com/docs/en/vs-code
✔ The Claude icon is in the side bar; "hello" gets an answer.

## 0.4 Create a local folder for the course work and open it in VS Code
Make an empty folder for everything you do in this course, e.g. `C:\Users\<you>\tigp-2026` or `~/tigp-2026`. **Not** inside OneDrive, Google Drive, Dropbox or iCloud (sync corrupts git repos and build caches), and **no spaces** in the path. In VS Code: *File → Open Folder…* → that folder.
✔ The folder name is in the VS Code title bar; the Claude Code panel opens with that folder as its working directory.

## 0.5 Let Claude do the rest
Open the Claude Code panel and paste exactly this:

> Read https://raw.githubusercontent.com/TIGP-Experimental-Methods/class-board-2026/main/SETUP.md and follow it step by step. Ask me before installing anything, and tell me what each step is for in one sentence.

Claude detects your OS and sets up, asking before each install: **git** (and your name + e-mail — use the **same e-mail as your GitHub account**, or your commits will not be attributed to you) · **Python via uv** · **GitHub CLI** and `gh auth login` · a check that you are in the class organization · a clone of the class repo `class-board-2026` into your folder · **PlatformIO** (VS Code extension + `pio` command) and one build of the simulator environment, which **downloads the ESP32 toolchain (~1 GB) — let it finish now, not on day 1** · **KiCad 10** (optional now; needed for homework 1).

It will stop and ask you to do three things in the browser: create a **GitHub account** if you have none (professional username, two-factor on), and send the username to the instructor · accept the **invitation to the GitHub organization** `TIGP-Experimental-Methods` (e-mail, or https://github.com/orgs/TIGP-Experimental-Methods/invitation) · a **Cloudflare account** (0.7). `gh auth login` is interactive: Claude tells you what to type and click; you run it.

At the end Claude prints a report ending in **toolchain OK**, or the first failure with the exact error. If it fails and the fix is not obvious, run `/tutor CH0`; if that does not solve it, email the report to the instructor.
✔ The report says **toolchain OK**.

## 0.6 The ✔ checks
The same list Claude prints — so you can verify by hand in the VS Code terminal:

```sh
git --version && git config --global --list        # name, e-mail, init.defaultBranch=main
uv --version && uv run --python 3.12 python -c "print(2**10)"   # 1024
gh auth status                                     # logged in as <username>
gh api user/memberships/orgs/TIGP-Experimental-Methods --jq .state   # active
ls class-board-2026/firmware/platformio.ini        # exists
pio --version
cd class-board-2026/firmware && pio run -e esp32s3-sim   # ends with [SUCCESS]
pio device list                                    # a port, only if you already have the board
kicad-cli version                                  # 10.x, if installed
```

The PlatformIO alien-head icon is in the VS Code side bar. If you have the board: it goes on the port marked *USB* (native USB, not *UART*); Windows and macOS need no driver; Linux needs the `dialout` group and PlatformIO's udev rules. No port → another cable, or hold **BOOT**, tap **RST**, release BOOT, retry.

## 0.7 A free Cloudflare account, connected to GitHub (manual)
On day 1 you deploy your first program to the public web with Cloudflare Pages, straight from a GitHub repo, no build step. Sign up at https://dash.cloudflare.com/sign-up (free plan; verify the e-mail). Then, once: *Workers & Pages → Create → Pages → Connect to Git* → authorise Cloudflare for your GitHub account — and stop there; the project itself is created in class.
✔ Signed in to the dashboard; the *Connect to Git* screen lists your GitHub account. (If sign-up fails, GitHub Pages is the fallback in class; nothing else to install.)

## 0.8 Watch V1 and V2; V0 optional
V1 *Setup* walks through 0.2–0.7 from your side of the screen. V2 *Flash the skeleton and open the app on your phone* is exactly what you do after the break on day 1. V0 *Build, ship, log: teach one idea on the web* previews the first exercise on one topic; in class you pick your own. Links on the course site's Preparation page: https://tigp-experimental-methods.github.io/preparation.html

## 0.9 Know what you are going to build
Everyone builds the same instrument: one class board with five blocks — **B1 inputs · B2 power · B3 outputs · B4 switching · B5 digital/TRIG** — one block per student, one shared repo, one phone app. On day 1 you also build something of your own first: a physics simulator on the public web. Read the course site's *Project* page.

---
**Tutor notes (`/tutor CH0`).** Run `SETUP.md` (repo root) step by step under its rules: detect the OS, one sentence per step, ask before every install, run each ✔ check. Stop at the first failure; suggest the fix; write the error and the fix into `docs/students/<name>/PROGRESS.md` under *gotchas*. If it cannot be fixed, the student emails the report to the instructor and you continue with the steps that do not depend on it. Do not install anything the student did not ask for.
