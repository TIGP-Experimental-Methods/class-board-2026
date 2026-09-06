# Chapter C — Cheat-sheets

## C.1 git and GitHub — the ten commands you use
```sh
git status                          # what changed
git switch -c e2-<name>             # new branch (e2-<name>, b<N>-<name>, b<N>-fw-<name>)
git add -A                          # stage everything (or: git add path/)
git commit -m "E2: press button + presses counter"
git push -u origin <branch>         # first push of a branch
gh pr create --fill                 # open the PR (then add the screenshot on GitHub)
git switch main && git pull         # back to main, get everyone's merges
git log --oneline -10               # what happened
git diff                            # what you changed, unstaged
git restore <file>                  # undo an unstaged change to one file
```
Rules: `main` is protected; one PR per deliverable; the PR description carries the screenshot; the instructor merges (*Squash and merge*). Review: *Files changed → + on a line → comment*; finish with *Approve* or *Request changes*. Stuck in a merge conflict? Do not fight it — ask on LINE.

## C.2 PlatformIO
```sh
cd firmware
pio run -e esp32s3-sim                 # compile only (SIM = bare dev board)
pio run -e esp32s3-sim -t upload       # flash the code
pio run -e esp32s3-sim -t uploadfs     # flash the web app (host/pwa → LittleFS)
pio device monitor                     # serial console, 115200
pio device list                        # which port is the board on
pio run -e esp32s3 -t upload           # the REAL board (no SIM) — wrap-up only
```
No port found: hold **BOOT**, tap **RST**, release BOOT, retry; use the **USB** connector (not UART); use a **data** cable. Upload works but the app is old: you forgot `uploadfs`. LED colours: blue = access point, green = on the lab WiFi.

## C.3 KiCad 10 — the six operations and their keys
| Operation | Where | Key |
|---|---|---|
| Place a symbol | schematic | `A` (project library `class_board`) |
| Wire | schematic | `W`; `K` ends a wire |
| Value / edit fields | schematic | `V` / `E` (check the **Footprint** field) |
| Annotate | schematic | *Tools → Annotate* |
| ERC | schematic | *Inspect → Electrical Rules Checker* |
| Update PCB from schematic | schematic → PCB | `F8` |
| Move / rotate a footprint | PCB | `M` / `R` |
| Route a track | PCB | `X`; `V` drops a via and switches layer |
| Fill zones | PCB | `B` |
| DRC | PCB | *Inspect → Design Rules Checker* |
| 3D view | PCB | `Alt+3` |
| Layers | PCB | F.Cu top signals · **In1.Cu = GND, do not route** · In2.Cu power (instructor) · B.Cu bottom signals |

Your rule area is `ZONE_B<N>`; nothing outside it; do not touch net classes or the instructor's tracks. Library: `hardware/lib/class_board.*`; new part: `easyeda2kicad --full --lcsc_id C… --output "<abs path>/hardware/lib/class_board"`.

## C.4 The review checklist (E10; the instructor's merge list)
- [ ] ERC 0 errors · DRC 0 errors, 0 unrouted
- [ ] `LCSC` field on every part
- [ ] values match the PDF
- [ ] decoupling capacitors next to the pins they serve
- [ ] nothing on In1.Cu
- [ ] nothing outside the rule area
- [ ] pin 1 marked on the silkscreen for every IC and connector
- [ ] ground pour joined (no islands)
- [ ] B4: isolation band ≥ 2.5 mm, no copper under it
- [ ] a silkscreen label on every connector
- [ ] CI green

## C.5 The protocol in one screen
Command: `{"id":1,"block":"b4","cmd":"relay","args":{"n":1,"on":true}}` → reply `{"id":1,"ok":true,"result":{…}}`.
Status (20 Hz): `{"type":"status","t":ms,"blocks":{"base":{…},"b1":{…}}}` — numeric top-level keys are chartable and alarmable.
Alarm rule: `{block, key, op: gt|lt|ge|le|eq|ne, threshold, action: notify | relay:<n>:on|off}`.
Scope: `stream {ch, rate_hz, chunk}` (rolling; `rate_hz: 0` stops) · `capture {ch, rate_hz, n, trig:{level, edge, pre}}` (one binary frame). Full list: `firmware/PROTOCOL.md`.

## C.6 The four log lines (`PROGRESS.md`, every session)
```markdown
## 2026-09-18 — L2 (class)
- Done: placed the 4 missing parts on b3_gapped; ERC 0; half of ZONE_B3 routed
- Verified: DRC shows only unrouted items; 3D view looks like the PDF
- Next: finish AO2 routing; E8 OPA2192 from LCSC; PR by Wed
- Gotchas: F8 put the new footprints outside my zone — drag them in first
```

## C.7 Who to ask
Tutor on your screen (`/tutor <chapter>`) → stuck: ask the tutor for the fix → still stuck: the course **LINE group** with a screenshot → your ring reviewer for anything about your block's design.
