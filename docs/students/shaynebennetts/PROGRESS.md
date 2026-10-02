# PROGRESS — shaynebennetts

- Language: English
- Pacing: one step at a time (expert mode available on request)
- Background: software — uses Claude Code daily for month-long builds; electronics — KiCad; CAD — extensive SolidWorks.
- Project 1: "Load the train" — freight-train loading game (locomotive + 20 cars, grain chute, physics-based)
- Block: not assigned yet (assigned at the start of Workshop 2)
- Project 1 repository: https://github.com/shaynebennetts/load-the-train (public)
- Project 1 website: —
- Project 2 repository: —
- Project 2 website: —

## 2026-09-11 — L1 (class)
- Done: toolchain check; branch `w1-shaynebennetts` created; this file created.
- Verified: git 2.49.0; gh signed in as shaynebennetts; PlatformIO Core 6.2.0; `pio run -e esp32s3-sim` SUCCESS; no board on a port yet; KiCad 10.0.3 installed.
- Next: Project 1 — SPEC.md + PLAN.md in the project window, then independent review in a fresh session.

- Gotchas: `/tutor` does not register when VS Code has the parent folder open instead of `class-board-2026`; the skill lives in the repository.

### Project 1 tests named by the student (2026-09-11)
1. Mass ledger: chute flow rate x open time = grain in cars + grain lost. Closes to 0.1%.
2. Energy ledger, with zero resistance and zero drag assumed:
       W_traction - W_brakes = dKE_total + 0.5*integral(v^2 * dM/dt dt)
   closing to 0.1%. dKE_total uses the full instantaneous mass, grain included.
   Tutor note: the student's first version was "energy in = final KE"; sharpened to a
   ledger, then simplified again once resistance and drag were set to zero. The surviving
   sink is the inelastic grain transfer, and only HALF of the work absorbed at rate
   v^2*(dM/dt) is dissipated. Getting that factor of two wrong is the failure this test
   exists to catch.
3. Hand-checkable limiting case: resistance off, brakes off, chute shut, constant power from
   rest gives v = sqrt(2Pt/M) and s = (2/3)*sqrt(2P/M)*t^(3/2).
4. Coasting accretion test (exact, no integration): chute open, zero traction, zero brake.
   Mv = const, so v_f = v_0*M_0/M_f and KE_f/KE_0 = M_0/M_f.

Also required in the spec: adhesion limit on traction, since F = P/v diverges at v = 0.

### Physics settled with the student (2026-09-11)
Zero rolling resistance and zero aerodynamic drag are assumed. Flag this as an idealisation
in the intro popup: the train never slows on its own, so every stop must be braked.

Mass accretion, NOT the rocket equation. The student first called it the rocket equation;
corrected. General law: F_ext = d(Mv)/dt - u*(dM/dt). The rocket has u = exhaust velocity
(propels); grain arrives with u = 0 (retards). Opposite sign. Textbook analogue is sand
falling onto a moving conveyor / hopper car. Equation of motion:

    F_traction - F_brake = d(Mv)/dt = M*(dv/dt) + v*(dM/dt)

The v*(dM/dt) term is a real retarding force and must come out of the integrator, never
be added as a tuned penalty.

Momentum: conserved for train+grain ONLY while coasting (F_ext = 0). Under throttle or
brake the rails supply external force, so d(Mv)/dt = F_ext.

Energy, the factor of two: grain arriving at rest onto a car at speed v absorbs work at
rate v^2*(dM/dt); half becomes grain KE, half is dissipated in the inelastic transfer.
Loaded grain moves with the train, so its KE is already inside KE_total. With zero
resistance the ledger is therefore:

    W_traction - W_brakes = dKE_total + 0.5*integral(v^2 * dM/dt dt)

Spilled grain is never accelerated, so it enters neither term. Free cross-check against
the mass ledger.


### Project 2 Step 1 — hardware baseline (2026-09-11)
Board: Jinhua ESP32-S3 N16R8, MAC 7c:4f:ad:1c:63:9c, so hostname/AP = instrument-639C.
Port COM10, hardware ID 303A:1001 (already carried our firmware, so the first-flash
BOOT+RST trap did not apply and every upload auto-reset).

- `pio run -d firmware -e esp32s3-sim -t upload`   SUCCESS (20.3 s, 912416 bytes)
- `pio run -d firmware -e esp32s3-sim -t uploadfs` SUCCESS (17.5 s)
- Boot log read with pyserial (dtr=False, rts=False set before open, never toggled;
  `pio device monitor` will not run without an interactive terminal):
      [boot] class-board firmware 0.1.0 (SIM)
      [registry] base ready ... alarms ready
      [wifi] AP "instrument-639C" password "instrument"  http://192.168.4.1/
      [http] server started
  The `/littlefs/alarms.json does not exist` line is harmless on first boot.

- Verified from the phone: (pending - student to report what they see)

## 2026-10-02 — L3 (class)
- Done: Project 3 housing designed in OpenSCAD with Claude, from scratch, in `housing/CompleteHousing.scad`: base with board bosses, corner columns, rear connector openings, dev-board USB notches and engraved labels; 2 mm top cover, separate SMA plate and OLED housing with white two-colour label inlays; laser-cut 3 mm bottom lid. All parts exported in print orientation to `housing/export/`; `housing/HANDOVER.md` written.
- Verified: renders in OpenSCAD looked at after every change; clash test of all three board models against every part (clean); labels checked against silkscreen and copper nets; SMA plate fit checked with the plate shifted 0.5 mm in 8 directions.
- Next: test coupon and a print of the coupon; slice in Bambu Studio; measure the DC jack axis and the OLED glass; bump the main board's dev-board socket rows from 25.0 to 25.4 mm before ordering; Project 3 website.
- Gotchas: a Python edit with Windows' default encoding emptied the .scad file (rebuilt, verified identical against earlier STLs) — write with UTF-8 or the Edit tool; relative import paths need the file saved in its folder.
