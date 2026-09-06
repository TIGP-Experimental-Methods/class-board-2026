# SETUP.md — toolchain setup, run by Claude Code

**What this is.** A step-by-step setup script for the Claude Code agent to follow on a student's laptop before day 1 of *Basic Skills for Experimentalists* (TIGP 2026). The student has already installed VS Code and the Claude Code extension, created a local course folder (e.g. `tigp-2026`), opened it in VS Code and pasted this prompt:

> Read https://raw.githubusercontent.com/TIGP-Experimental-Methods/class-board-2026/main/SETUP.md and follow it step by step. Ask me before installing anything, and tell me what each step is for in one sentence.

The agent does the installs and checks; the student reads along, answers questions and does the browser-only steps (GitHub account, organization invitation, Cloudflare account). Chapter 0 of the workbook (`workbook/ch0-before-day-1.md`) is the student-facing version of the same list.

## Rules for the agent

1. **Detect the OS first** (Windows / macOS / Linux, and on Linux whether `apt` or `dnf` is present). Use the matching commands below and skip the others. Windows commands are PowerShell; macOS and Linux commands are `bash`/`zsh`.
2. **One sentence per step** saying what the step is for, then the command(s), then the ✔ check.
3. **Ask before every install.** Install nothing that is not listed here. If a tool is already present and passes its ✔ check, say so and move on.
4. **Interactive commands** (`gh auth login`, anything that opens a browser or asks for a password) are run by the student in the VS Code terminal; tell them what to type and what to click, then wait.
5. **Never store secrets** anywhere in the repo: no tokens, passwords or WiFi credentials in files, commits or `CLAUDE.md`. `gh` keeps its own credentials; leave them there.
6. **Stop on the first failure.** Print the exact command and the exact error text, apply only the fallbacks named in that step, and if it still fails end with the final report marked as failed. Do not improvise other installers or manual downloads.
7. **PATH.** After an installer, new binaries may not be visible in the current terminal. Windows: refresh with `$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")`. macOS/Linux: open a new terminal or `source ~/.zshrc` / `source ~/.bashrc`. Try that before declaring a tool missing.
8. **Working folder.** Everything is created inside the folder VS Code has open. If that path contains spaces or lives under OneDrive / Google Drive / Dropbox / iCloud, warn the student (sync folders corrupt git repos and PlatformIO caches) and ask whether to continue or to create e.g. `C:\Users\<user>\tigp-2026` / `~/tigp-2026` instead.
9. **Finish with the report** in the format at the end of this file.

## Step 1 — git

Purpose: version control; every file in the course goes through git.

| OS | Install |
|---|---|
| Windows | `winget install --id Git.Git -e --source winget` |
| macOS | `git --version` — if a developer-tools dialog appears, accept it; otherwise `brew install git` (install Homebrew first if `brew` is missing: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`) |
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

Purpose: the class repo, the student's own repos and the code review all live on GitHub; `gh` logs the laptop in once so git and the agent can push and open pull requests.

**Manual (student, browser).** If the student has no GitHub account: https://github.com/signup — a professional username (it appears in the URL of their work), two-factor authentication on. Ask for the username; it is needed in Step 4.

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

Purpose: the class repo is owned by the organization **TIGP-Experimental-Methods**; only members can clone it and open pull requests.

**Manual (student).** The instructor invites the username from Step 3. The student accepts the invitation from the e-mail GitHub sends, or at https://github.com/orgs/TIGP-Experimental-Methods/invitation. If no invitation has arrived, the student e-mails their GitHub username to the instructor (s.p.bennetts@g.iams.sinica.edu.tw) and continues with Steps 6, 8, 9 and 10 meanwhile; Steps 4–5 are then finished later by re-running this file.

✔ `gh api user/memberships/orgs/TIGP-Experimental-Methods --jq .state` prints `active`. (`404` = no invitation or not yet accepted; `pending` = accept it in the browser.)

## Step 5 — Clone the class repo

Purpose: all project work for the course happens inside this one repository.

In the course folder (the folder VS Code has open):

```sh
gh repo clone TIGP-Experimental-Methods/class-board-2026
```

✔ `class-board-2026/firmware/platformio.ini` exists; `git -C class-board-2026 status` says `On branch main`.

## Step 6 — PlatformIO and the ESP32 toolchain

Purpose: PlatformIO builds and flashes the board's firmware; the VS Code extension gives the buttons, the Core CLI gives `pio` in the terminal, and the first build downloads the ESP32-S3 toolchain so day 1 does not.

Extension:

```sh
code --install-extension platformio.platformio-ide
```

(If `code` is not found: macOS — VS Code Command Palette → *Shell Command: Install 'code' command in PATH*; Windows — re-run the VS Code installer with *Add to PATH* ticked, or install the extension from the Extensions view by searching *PlatformIO IDE*.)

Core CLI:

```sh
uv tool install platformio
pio --version
```

(If `pio` is not found afterwards: `uv tool update-shell`, then a new terminal.)

Toolchain — build the simulator environment once, without a board:

```sh
cd class-board-2026/firmware
pio run -e esp32s3-sim
```

This downloads the Espressif platform, compiler and framework (~1 GB) into `~/.platformio`, which the VS Code extension shares, so it happens once. Do not interrupt it. **It must finish before day 1.**

✔ The PlatformIO alien-head icon is in the VS Code side bar; `pio --version` prints a version; the build output ends with `[SUCCESS]`.

## Step 7 — USB (only if the student already has the dev board)

Purpose: confirm the laptop sees the board on a serial port; most students receive the board on day 1, so skip this step if there is no board yet and say so in the report.

The board is a Jinhua #40729 ESP32-S3 N16R8 dev board (DevKitC-1 pinout). Its connector is **USB-C**; use a **data** cable that fits the laptop (USB-C to USB-C, or USB-A to USB-C — charging-only cables carry no data), plugged into the port marked *USB* (native USB, not *UART*). No serial driver is needed on Windows or macOS. Linux: add the user to the `dialout` group (`sudo usermod -aG dialout $USER`, then log out and in) and install PlatformIO's udev rules (https://docs.platformio.org/en/latest/core/installation/udev-rules.html).

```sh
pio device list
```

✔ A port is listed: Windows `COMn`, macOS `/dev/cu.usbmodem…`, Linux `/dev/ttyACM0`. If none: try another cable, the other USB port on the board, or hold **BOOT**, tap **RST**, release BOOT and retry.

Flashing itself happens on day 1 (from `class-board-2026/firmware`): `pio run -e esp32s3-sim -t upload`, then `pio run -e esp32s3-sim -t uploadfs`, then `pio device monitor`. Do not run these now unless the student asks.

## Step 8 — Cloudflare account (manual)

Purpose: on day 1 the student deploys a web page to the public internet with Cloudflare Pages, straight from a GitHub repo; the account and the GitHub authorisation are done in advance.

**Manual (student, browser).**
1. Sign up (free plan) at https://dash.cloudflare.com/sign-up and verify the e-mail.
2. Once: *Workers & Pages → Create → Pages → Connect to Git* → authorise Cloudflare for the GitHub account. Stop there — the Pages project is created in class.

✔ Ask the student to confirm that the *Connect to Git* screen lists their GitHub account. If sign-up fails, note it in the report; GitHub Pages is the fallback used in class and needs nothing extra.

## Step 9 — KiCad 10 (optional now; needed for homework 1)

Purpose: the class board is designed in KiCad; each student edits their own zone of the schematic and layout from homework 1 onwards. Offer this step; the student may defer it.

| OS | Install |
|---|---|
| Windows | `winget install --id KiCad.KiCad -e --source winget` |
| macOS | `brew install --cask kicad` |
| Linux | `sudo apt install kicad` (Ubuntu: add `ppa:kicad/kicad-10-releases` first for version 10) or `sudo dnf install kicad` |

Start KiCad once and accept the default library tables when asked.

✔ `kicad-cli version` prints `10.x`. If deferred, write *deferred* in the report.

## Step 10 — Videos

Purpose: V1 shows this setup from the student's side; V2 shows exactly what happens after the break on day 1 (flash the skeleton, open the app on the phone).

Ask the student to watch **V1** and **V2** on the course site's Preparation page, https://tigp-experimental-methods.github.io/preparation.html. **V0** (build, ship, log: teach one idea on the web) is optional. Record the answer.

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
- V1, V2 watched: <yes | not yet>

**toolchain OK** — or — **First failure:** Step <n>: `<command>` → `<exact error>`
```
