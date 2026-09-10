# SETUP.md — toolchain setup, run by Claude Code

**What this is.** A step-by-step setup script for the Claude Code agent (Claude Code working on your files: it reads them, writes code, runs commands, and reports back) to follow on a student's laptop before Workshop 1 of *Basic Skills for Experimentalists* (TIGP 2026). The student has already installed VS Code and the Claude Code extension, created a local course folder (e.g. `tigp-2026`), opened it in VS Code and pasted this prompt:

> Read https://raw.githubusercontent.com/TIGP-Experimental-Methods/class-board-2026/main/SETUP.md and follow it step by step. Ask me before installing anything, and tell me what each step is for in one sentence.

The agent does the installs and checks; the student reads along, answers questions and does the browser-only steps (GitHub account — GitHub is the website where repositories, project folders with their full history, are stored and shared — organization invitation, Cloudflare account). Chapter 0 of the workbook (`workbook/ch0-before-day-1.md`) is the student-facing version of the same list.

## Rules for the agent

1. **Detect the OS first** (Windows / macOS / Linux, and on Linux whether `apt` or `dnf` is present). Use the matching commands below and skip the others. Windows commands are PowerShell; macOS and Linux commands are `bash`/`zsh`.
2. **One sentence per step** saying what the step is for, then the command(s), then the ✔ check.
3. **Ask before every install.** Install nothing that is not listed here. If a tool is already present and passes its ✔ check, say so and move on.
4. **Interactive commands** (`gh auth login`, anything that opens a browser or asks for a password) are run by the student in the VS Code terminal (the text window where you type commands); tell them what to type and what to click, then wait.
5. **Never store secrets** anywhere in the repository: no tokens, passwords or WiFi credentials in files, commits (saved snapshots of the work) or `CLAUDE.md` (the plain-text file that tells the agent how the project is set up). Never ask the student to type a password or token into the chat either — the student types those into the terminal or the editor themselves. `gh` keeps its own credentials; leave them there.
6. **Stop on the first failure.** Print the exact command and the exact error text, apply only the fallbacks named in that step, and if it still fails end with the final report marked as failed. Do not improvise other installers or manual downloads.
7. **PATH.** After an installer, new binaries may not be visible in the current terminal. Windows: refresh with `$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")`. macOS/Linux: open a new terminal or `source ~/.zshrc` / `source ~/.bashrc`. Try that before declaring a tool missing.
8. **Working folder.** Everything is created inside the folder VS Code has open. If that path contains spaces or lives under OneDrive / Google Drive / Dropbox / iCloud, warn the student (sync folders corrupt git repositories and PlatformIO caches) and ask whether to continue or to create e.g. `C:\Users\<user>\tigp-2026` / `~/tigp-2026` instead.
9. **Finish with the report** in the format at the end of this file.

## Step 1 — git

Purpose: git is the tool that records the history of a folder of files (version control); every file in the course goes through it.

| OS | Install |
|---|---|
| Windows | `winget install --id Git.Git -e --source winget` |
| macOS | `git --version` — if a developer-tools dialog appears, accept it; otherwise `brew install git` (install Homebrew first if `brew` is missing — the student runs this one, it asks for the login password: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`) |
| Linux | `sudo apt install git` or `sudo dnf install git` |

Then ask the student for their name and the **e-mail address of their GitHub account** (the two must match, or GitHub will not attribute their commits):

```sh
git config --global user.name "<name>"
git config --global user.email "<github e-mail>"
git config --global init.defaultBranch main
```

✔ `git --version` prints a version; `git config --global --list` shows the three lines.

## Step 2 — Python via uv

Purpose: `uv` installs and manages Python and Python tools without touching any system Python.

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
```sh
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then (new terminal or PATH refresh first):

```sh
uv --version
uv python install 3.12
```

✔ `uv --version` prints a version; `uv run --python 3.12 python -c "print(2**10)"` prints `1024`.

## Step 3 — GitHub account and the GitHub CLI

Purpose: the class repository, the student's own repositories and the code review all live on GitHub; `gh` (the GitHub CLI, GitHub's command-line tool) logs the laptop in once so git and the agent can push (upload commits to GitHub) and open pull requests (a pull request asks to merge your changes into the shared project; someone reviews it first).

**Manual (student, browser).** If the student has no GitHub account: https://github.com/signup — a professional username (it appears in the web address, the URL, of their work), two-factor authentication on. Ask for the username; it is needed in Step 4.

| OS | Install |
|---|---|
| Windows | `winget install --id GitHub.cli -e --source winget` |
| macOS | `brew install gh` |
| Linux | `sudo apt install gh` or `sudo dnf install gh` (if `apt` has no `gh` package, follow https://github.com/cli/cli/blob/trunk/docs/install_linux.md) |

**Interactive (student, VS Code terminal):**

```sh
gh auth login
```

Tell the student to choose: *GitHub.com* → *HTTPS* → *Yes* (authenticate Git with GitHub credentials) → *Login with a web browser* → copy the one-time code, press Enter, paste the code in the browser, *Authorize github*. Then return to the terminal.

✔ `gh auth status` reports *Logged in to github.com account <username>*; `gh api user --jq .login` prints the username.

## Step 4 — Join the class GitHub organization

Purpose: the class repository is owned by the organization **TIGP-Experimental-Methods**. It is public — anyone can clone it (download a full copy) — but only members can push and open pull requests.

**Manual (student).** The instructor invites the username from Step 3. The student accepts the invitation from the e-mail GitHub sends, or at https://github.com/orgs/TIGP-Experimental-Methods/invitation. If no invitation has arrived, the student e-mails their GitHub username to the instructor (s.p.bennetts@g.iams.sinica.edu.tw) and continues with Steps 5–9; Step 4 is re-checked later by re-running this file.

✔ `gh api user/memberships/orgs/TIGP-Experimental-Methods --jq .state` prints `active`. (`404` = no invitation or not yet accepted; `pending` = accept it in the browser.)

## Step 5 — Clone the class repository

Purpose: all project work for the course happens inside this one repository. Its `main` branch is the version everyone builds on (a branch is a separate line of work inside a repository).

In the course folder (the folder VS Code has open):

```sh
gh repo clone TIGP-Experimental-Methods/class-board-2026
```

✔ `class-board-2026/firmware/platformio.ini` exists; `git -C class-board-2026 status` says `On branch main`.

## Step 6 — PlatformIO and the ESP32 toolchain

Purpose: PlatformIO builds the board's firmware (the program that runs on the ESP32-S3, the microcontroller we use) and flashes it (writes it onto the board over USB); the VS Code extension gives the buttons, the Core CLI gives `pio` in the terminal, and the first build downloads the ESP32-S3 toolchain (the compiler and helper programs that turn source code into firmware) so Workshop 1 does not.

Extension:

```sh
code --install-extension platformio.platformio-ide
```

(If `code` is not found: macOS — VS Code Command Palette → *Shell Command: Install 'code' command in PATH*; Windows — re-run the VS Code installer with *Add to PATH* ticked, or install the extension from the Extensions view by searching *PlatformIO IDE*. Linux: the extension needs `python3-venv` — `sudo apt install python3-venv` or `sudo dnf install python3` — before it can set itself up.)

Core CLI:

```sh
uv tool install --python 3.12 platformio
pio --version
```

(If `pio` is not found afterwards: `uv tool update-shell`, then a new terminal.)

Toolchain — build the simulator environment (SIM mode: the firmware fakes its hardware, so everything runs on the bare dev board) once, without a board:

```sh
cd class-board-2026/firmware
pio run -e esp32s3-sim
```

This downloads the Espressif platform, compiler and framework (~1 GB) into `~/.platformio`, which the VS Code extension shares, so it happens once. Do not interrupt it. **It must finish before Workshop 1.**

✔ The PlatformIO alien-head icon is in the VS Code side bar (after *Developer: Reload Window* from the Command Palette); `pio --version` prints a version; the build output ends with `[SUCCESS]`.

## Step 7 — USB (only if the student already has the dev board)

Purpose: confirm the laptop sees the board on a serial port; most students receive the board in Workshop 1, so skip this step if there is no board yet and say so in the report.

The board is a Jinhua #40729 ESP32-S3 N16R8 dev board (the development board: the microcontroller on a small board with a USB connector and pins; DevKitC-1 pinout). Its connector is **USB-C**; use a **data** cable that fits the laptop (USB-C to USB-C, or USB-A to USB-C — charging-only cables carry no data), plugged into the port marked *USB* (native USB, not *UART*). No serial driver is needed on Windows or macOS. Linux: add the user to the `dialout` group (the user group allowed to open serial ports: `sudo usermod -aG dialout $USER`, then log out and in) and install PlatformIO's udev rules (the file that tells Linux to let ordinary users talk to the board: https://docs.platformio.org/en/latest/core/installation/udev-rules.html).

```sh
pio device list
```

✔ A port is listed: Windows `COMn`, macOS `/dev/cu.usbmodem…`, Linux `/dev/ttyACM0`, with a hardware ID of either `USB VID:PID=303A:1001` — the board already carries our firmware (the chip's built-in USB-Serial/JTAG; flashing later needs no buttons) — or `USB VID:PID=303A:4001` — a factory-fresh board with the firmware it shipped with; both pass. On a `4001` board the first `upload` will end with *"No serial data received"*: hold **BOOT**, tap **RST**, release BOOT, run `pio device list` again — the board comes back as `303A:1001` on a different port — and flash to that port; this is needed once only. The boards handed out in class are already flashed. If no port at all: try another cable, the other USB port on the board, or the same BOOT+RST and retry.

Flashing itself happens in Workshop 1 (Project 2), from `class-board-2026/firmware`, one command at a time: `pio run -e esp32s3-sim -t upload`, then `pio run -e esp32s3-sim -t uploadfs`, then `pio device monitor`. Do not run these now unless the student asks.

## Step 8 — Cloudflare account (manual)

Purpose: in Workshop 1 (Project 1) the student deploys (publishes, so it is live on the web) a web page to the public internet with Cloudflare Pages (a free service that turns a repository into a public web page), straight from a GitHub repository; the account and the GitHub authorisation are done in advance.

**Manual (student, browser).**
1. Sign up (free plan) at https://dash.cloudflare.com/sign-up and verify the e-mail.
2. Once: *Workers & Pages → Create → Pages → Connect to Git* → authorise Cloudflare for the GitHub account. Stop there — the Pages project is created in class.

✔ Ask the student to confirm that the *Connect to Git* screen lists their GitHub account. If sign-up fails, note it in the report; GitHub Pages is the fallback used in class and needs nothing extra.

## Step 9 — KiCad 10 (optional now; needed for homework 1)

Purpose: the class board is designed in KiCad (the free program we draw the schematic and lay out the printed circuit board in); each student edits their own zone (the region of the board that is theirs) of the schematic (the circuit drawing) and layout (the physical board design) from homework 1 onwards. Offer this step; the student may defer it.

| OS | Install |
|---|---|
| Windows | `winget install --id KiCad.KiCad -e --source winget` |
| macOS | `brew install --cask kicad` |
| Linux | `sudo apt install kicad` (Ubuntu: add `ppa:kicad/kicad-10-releases` first for version 10) or `sudo dnf install kicad` |

Start KiCad once and accept the default library tables when asked.

✔ KiCad starts and *Help → About KiCad* shows version 10.x (on Linux `kicad-cli version` also works; on Windows and macOS `kicad-cli` is not on the PATH, so do not use it as the check). If deferred, write *deferred* in the report.

## Final report

Print this block at the end, filled in. On a failure, stop at that step, fill in the lines completed so far, and put the exact command and error under *First failure*. The student e-mails the whole block to the instructor (s.p.bennetts@g.iams.sinica.edu.tw) if a failure could not be fixed.

```markdown
## Toolchain report — <date>, <OS and version>

- ✔/✘ git <version>; user.name / user.email set; init.defaultBranch main
- ✔/✘ uv <version>; Python 3.12 installed
- ✔/✘ gh <version>; logged in as <username>
- ✔/✘ TIGP-Experimental-Methods membership: <active | pending | none>
- ✔/✘ class-board-2026 cloned; firmware/platformio.ini present
- ✔/✘ PlatformIO IDE extension installed; pio <version>; `pio run -e esp32s3-sim` SUCCESS
- ✔/✘/skipped USB: <port> (or: no board yet)
- ✔/✘ Cloudflare: Connect to Git lists GitHub account <username>
- ✔/✘/deferred KiCad <version>

**toolchain OK** — or — **First failure:** Step <n>: `<command>` → `<exact error>`
```
