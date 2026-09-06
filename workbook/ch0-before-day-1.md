# Chapter 0 — Before day 1

The first class is hands-on from the start: everyone types `/tutor L1`, builds a simulator with Claude, deploys it to the public web before the break, and flashes their own firmware to an ESP32 after it. All of that only works if the tools below already work on your laptop. Every step has a ✔ check. If a step fails, do not fight it: note the error, ask in the LINE group, and come early on day 1.

*Tip:* once steps 2–3 are done you can ask Claude to help with the rest ("Help me install uv and Python on Windows and check that it works"). That is not cheating; it is the course.

## 0.1 A laptop you can install software on
Windows 10/11, macOS or Linux; admin rights; ~10 GB free; a USB-A port or a USB-C adapter for the dev board. Bring a **USB-C data cable** on day 1 (charging-only cables are the number one flashing failure).

## 0.2 Visual Studio Code
Install from https://code.visualstudio.com/download with default options (Windows: tick *Add to PATH* and *Open with Code*).
✔ *Help → About* shows a version.

## 0.3 Claude Code extension, signed in to the course organization
In VS Code press `Ctrl+Shift+X` (macOS `Cmd+Shift+X`), search **Claude Code** (publisher Anthropic), Install. Accept the e-mail invitation to the course's Claude organization and sign in with that account. Docs: https://code.claude.com/docs/en/vs-code
✔ The Claude icon is in the side bar; "hello" gets an answer.

## 0.4 git (and tell it who you are)
Windows: Git for Windows (defaults). macOS: `git --version` in Terminal and accept the developer-tools prompt. Linux: `sudo apt install git`.
```sh
git config --global user.name "Your Name"
git config --global user.email "you@example.com"     # same e-mail as your GitHub account
```
✔ `git --version` prints a version.

## 0.5 Python via uv
```sh
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Close and reopen the terminal, then `uv python install 3.13`. Also install the *Python* extension in VS Code.
✔ `uv run python -c "print(2**10)"` prints `1024`.

## 0.6 A personal GitHub account + the GitHub CLI
Sign up at https://github.com/signup with a professional username (it will be in the URL of your work for years); turn on two-factor authentication. Install the GitHub CLI (https://cli.github.com/) and run:
```sh
gh auth login          # GitHub.com → HTTPS → login with a web browser
```
✔ `gh auth status` says you are logged in.

## 0.7 Join the class GitHub organization
Send your GitHub username to the instructor; accept the invitation to **TIGP-Experimental-Methods** (e-mail or https://github.com/settings/organizations).
✔ The organization appears in your list.

## 0.8 PlatformIO extension — and let it download its toolchain
In VS Code install **PlatformIO IDE**. On first start it downloads its own Python and the ESP32 toolchain (~1 GB). **Let it finish now**; on day 1 there is no time for this. Windows needs no driver for the dev board's native USB.
✔ The alien-head icon is in the side bar; in the *PlatformIO Core CLI* terminal `pio --version` prints a version. This is the first thing the tutor checks on day 1.

## 0.9 Clone the class repository
All project work lives in one repo. In VS Code: *File → New Window → Clone Git Repository…* → `https://github.com/TIGP-Experimental-Methods/class-board-2026` → a folder such as `Documents/tigp`. (If it is not visible, accept the invitation from 0.7 first.)
Then, in the repo's terminal, pre-download the firmware dependencies so day 1's flash is fast:
```sh
cd firmware
pio run -e esp32s3-sim          # compiles only; downloads the ESP32 platform + libraries once
```
✔ `git status` says `On branch main`; `pio run` ends with `SUCCESS`.

## 0.10 A free Cloudflare account, connected to GitHub
On day 1 you deploy your first program to the public web with Cloudflare Pages, straight from a GitHub repo, no build step. Sign up at https://dash.cloudflare.com/sign-up (free plan; verify the e-mail). Then, once: *Workers & Pages → Create → Pages → Connect to Git* → authorise Cloudflare for your GitHub account — and stop there; the project itself is created in class.
✔ Signed in to the dashboard; the *Connect to Git* screen lists your GitHub account. (If sign-up fails, GitHub Pages is the fallback in class; nothing else to install.)

## 0.11 Watch V1 and V2; V0 optional
V1 *Setup* walks through 0.2–0.9. V2 *Flash the skeleton and open the app on your phone* is exactly what you do after the break on day 1. V0 *Build, ship, log: teach one idea on the web* previews the first exercise on one topic; in class you pick your own. Links on the course site's Preparation page.

## 0.12 Check in on the LINE group
Post a screenshot of the cloned repo open in VS Code. The LINE group is where you ask for help during the course.
✔ Your screenshot is in the group.

## 0.13 Know what you are going to build
Everyone builds the same instrument: one class board with five blocks — **B1 inputs · B2 power · B3 outputs · B4 switching · B5 digital/TRIG** — one block per student, one shared repo, one phone app. On day 1 you also build something of your own first: a physics simulator on the public web. Read the course site's *Project* page.

---
**Tutor notes (`/tutor CH0`).** Run the ✔ checks in order and stop at the first failure; suggest the fix; when the student is stuck, write the error into `docs/students/<name>/PROGRESS.md` under *gotchas* and send the student to the LINE group. Do not install anything the student did not ask for.
