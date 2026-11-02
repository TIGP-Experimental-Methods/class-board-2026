# Lab PC setup: build and flash the class-board firmware from a fresh Windows PC

**What this is.** A script for Claude Code to follow on a fresh Windows PC in the electronics lab, so that the class
firmware can be built and written onto an ESP32-S3 dev board or an assembled class board. It installs only what
flashing needs: git, Python via uv, the PlatformIO command line, the ESP32 toolchain, and a clone of the class
repository. No GitHub login, no organization membership, no KiCad.

**How to start it.** Install VS Code (https://code.visualstudio.com) and its Claude Code extension, sign in, create
the folder `C:\Claude`, open it in VS Code, start Claude Code and paste:

> Read https://raw.githubusercontent.com/TIGP-Experimental-Methods/class-board-2026/main/docs/lab-pc-setup.md and follow it step by step. Ask me before installing anything, and tell me what each step is for in one sentence.

## Rules for the agent

1. Windows is assumed; commands are PowerShell. If the PC is macOS or Linux, say so and stop: use `SETUP.md` in the repository root instead, steps 1, 2, 5, 6 and 7.
2. One sentence per step saying what it is for, then the commands, then the ✔ check. Ask before every install.
3. Everything is created under `C:\Claude`. Never under Google Drive, OneDrive or Dropbox folders: sync folders corrupt git repositories.
4. Stop on the first failure: print the exact command and the exact error text, apply only the fallback named in that step, and if it still fails end with the report marked as failed. Do not improvise other tools or other ways.
5. Never store secrets anywhere in the repository and never ask for one in the chat: no WiFi password, no OTA password, no token. If the person wants the board on the lab network, they type the credentials themselves into a git-ignored file (step 7); the agent only checks that the file is ignored.
6. Interactive commands and anything that opens a browser are run by the person in the VS Code terminal; tell them what to type.
7. After an install, open a new terminal before using the new command, so the updated PATH is read.

## Step 1 — git

Purpose: git fetches the repository and records changes; PlatformIO also needs it.

```powershell
winget install --id Git.Git -e --source winget
```

Fallback: if `winget` is missing, download the installer from https://git-scm.com/download/win and let the person run it with the defaults.

✔ In a new terminal, `git --version` prints a version.

## Step 2 — Python via uv

Purpose: `uv` installs a private Python and Python tools without touching any system Python.

```powershell
winget install --id astral-sh.uv -e
```

Fallback: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` (the person runs it).

✔ In a new terminal, `uv --version` prints a version.

## Step 3 — PlatformIO command line

Purpose: PlatformIO builds the firmware and writes it onto the board over USB. The command line is enough here; the VS Code extension is optional.

```powershell
uv tool install --python 3.12 platformio
```

Optional, for the serial monitor and build buttons inside VS Code: `code --install-extension platformio.platformio-ide`, then *Developer: Reload Window* from the Command Palette.

✔ In a new terminal, `pio --version` prints a version.

## Step 4 — Clone the class repository

Purpose: the firmware, the web app and the assembly guide are in the public repository `TIGP-Experimental-Methods/class-board-2026`; cloning needs no login.

```powershell
git clone https://github.com/TIGP-Experimental-Methods/class-board-2026 C:\Claude\class-board-2026
```

If the folder already exists, run `git -C C:\Claude\class-board-2026 pull` instead.

✔ `C:\Claude\class-board-2026\firmware\platformio.ini` exists and `git -C C:\Claude\class-board-2026 log -1 --format=%h` prints a commit.

## Step 5 — Build once, which downloads the ESP32 toolchain

Purpose: the first build pulls the Espressif platform, compiler and framework (about 1 GB) into `C:\Users\<user>\.platformio`, once. Do not interrupt it.

```powershell
cd C:\Claude\class-board-2026\firmware
pio run -e esp32s3
```

`esp32s3` is the build for the real class board. `esp32s3-sim` is the simulator build for a bare dev board, with every piece of hardware faked; build it the same way when a bare board is to be tested.

✔ The output ends with `[SUCCESS]`.

## Step 6 — USB

Purpose: find the board's COM port. Windows 10 and 11 carry the driver for the ESP32-S3's native USB; nothing is installed.

Tell the person: plug the dev board in with a **USB-C data cable** (a charge-only cable shows nothing). On an assembled class board use the **main board's USB-C socket** at the rear edge; on a bare dev board use the port marked **USB**. **Never the port marked UART**: it drives a panel LED line and is not used for flashing.

```powershell
pio device list
```

✔ A `COMn` port is listed with hardware ID `303A:1001` (a board that already runs our firmware or any Arduino build) or `303A:4001` (a factory-fresh board; see step 8). If nothing is listed, try another cable before anything else.

## Step 7 — Optional: WiFi credentials, typed by the person

Purpose: with no credentials the board opens its own WiFi network `instrument-XXXX` (password `instrument`) and serves the app at 192.168.4.1, which is enough for every test. For the lab network the person copies the template and types the credentials themselves.

Tell the person: in VS Code open `firmware\include\secrets.h.example`, save it as `firmware\include\secrets.h` in the same folder, and type the SSID and password into it. The agent does not ask for them and does not read the file.

```powershell
git -C C:\Claude\class-board-2026 check-ignore -v firmware/include/secrets.h
```

✔ The command prints the `.gitignore` rule that ignores the file. If it prints nothing, stop: the file would be committed; report it.

## Step 8 — Flash

Purpose: write the firmware, then the web app, onto the board. Two commands, one at a time, from `firmware`.

```powershell
cd C:\Claude\class-board-2026\firmware
pio run -e esp32s3 -t upload
pio run -e esp32s3 -t uploadfs
```

If PlatformIO picks the wrong port, add `--upload-port COMn` to both commands.

**Factory-fresh board (hardware ID 303A:4001):** the first upload fails with "No serial data received". Tell the person: hold **BOOT**, tap **RST**, release **BOOT** (the two small buttons on the dev board). The board comes back on a **new** COM port; run `pio device list` again and repeat the two uploads to that port. Later uploads reset the board by themselves. This is needed once per board.

✔ Both commands end with `[SUCCESS]`.

## Step 9 — Watch it boot

Purpose: confirm the firmware runs.

```powershell
pio device monitor
```

(Ctrl+C ends it.) Expected lines: `[boot]`, one `[registry] <name> ready` per block, then `[wifi] AP instrument-XXXX` or `[wifi] STA <ip>`, and `[http] server started`. The dev board's RGB LED: yellow while joining a network, green on the lab network, blue on its own network. Tell the person to join `instrument-XXXX` from a phone or the PC and open 192.168.4.1 (or `http://instrument-XXXX.local` on the lab network).

If the monitor shows nothing: unplug, wait two seconds, plug in again, and run the monitor before pressing anything on the board. Do not press RST while the monitor is open and then wonder about the port: every reset drops and re-creates the COM port.

✔ The app opens in the browser.

## Final report

Print a table of the steps with ✔ or ✘, the versions of git, uv and pio, the COM port and hardware ID seen, and the firmware environment flashed. Then say where the assembly guide is: `C:\Claude\class-board-2026\hardware\docs\assembly.html` (open it in the browser) and https://tigp-experimental-methods.github.io/assembly/.
