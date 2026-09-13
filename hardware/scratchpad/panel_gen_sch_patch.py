"""Patch scripts/gen_sch.py for the v0.7 link pinout (2026-09-13).

The front-panel generator (scripts/gen_panel.py) already uses the new pinout; this script brings the MAIN-BOARD
generator's LINK table and the front_panel_link sheet text in line so the two stop disagreeing.  gen_panel.py
prints a NOTE at every run until this patch is applied.

    pins 37-40   old:  +5V_RAW  GND  n/c  n/c
                 new:  RX       AGND TX   AGND

Run:  python scratchpad/panel_gen_sch_patch.py        (from the repository root; add --dry-run to preview)

It is idempotent: running it twice changes nothing.  It only edits the link table and its documentation text -
it does NOT decide where RX/TX come from on the main board.  See the WARNING printed at the end.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "scripts", "gen_sch.py")

EDITS = [
    # 1. the LINK pin table
    ('        37: "+5V_RAW", 38: "GND", 39: None, 40: None}',
     '        37: "RX", 38: "AGND", 39: "TX", 40: "AGND"}'),
    # 2. the sheet note
    ('"LED_PWR is +3V3 (always on, resistor on the panel). LED_WIFI/LED_ACT come from GPIO43/GPIO44 through JP1/JP2 (base sheet). +5V_RAW pin 37 is spare power for future panel use.",',
     '"LED_PWR is +3V3 (always on, resistor on the panel). LED_WIFI/LED_ACT come from GPIO43/GPIO44 through JP1/JP2 (base sheet). Pins 37/39 = RX/TX (3.3 V UART) to the panel SMAs with AGND on 38/40 (v0.7); +5V_RAW no longer reaches the panel.",'),
    # 3. the pinout table printed on the sheet
    ('["37-40", "+5V_RAW GND n/c n/c"]',
     '["37-40", "RX AGND TX AGND"]'),
]

WARNING = """
WARNING - the main board still has to DRIVE these two pins:
  * link pin 37 (RX) and pin 39 (TX) are now global labels RX / TX on the front_panel_link sheet.  Unless a
    matching RX / TX label exists on the base sheet, they are single-pin nets: the panel SMAs would go nowhere.
  * the obvious source is UART0 on the dev board: GPIO43 = U0TXD -> TX, GPIO44 = U0RXD -> RX.  Those two pins
    are currently used for LED_WIFI / LED_ACT through JP1 / JP2 (base sheet) and appear on the 2x10 expansion
    header, so that reassignment is an engineering decision - make it explicitly, then wire the labels.
  * +5V_RAW no longer leaves the main board through the link.  Nothing on the panel used it (verified: on the
    rev A panel the only +5V_RAW node was the link pad itself), so no panel change is needed.
After patching, re-run:  python scripts/gen_sch.py  and  python scripts/gen_panel.py
"""


def main():
    dry = "--dry-run" in sys.argv
    src = open(TARGET, encoding="utf-8").read()
    done, todo = [], []
    for old, new in EDITS:
        if new in src and old not in src:
            done.append(new[:60])
            continue
        if src.count(old) != 1:
            raise SystemExit("ERROR: expected exactly one occurrence of:\n  %s\nfound %d - gen_sch.py has moved on, patch by hand." % (old[:100], src.count(old)))
        src = src.replace(old, new)
        todo.append(new[:60])
    if done:
        print("already patched: %d edit(s)" % len(done))
    if not todo:
        print("nothing to do - gen_sch.py already carries the v0.7 link pinout")
        return
    for t in todo:
        print("patched: %s..." % t)
    if dry:
        print("(dry run - nothing written)")
        return
    with open(TARGET, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(src)
    print("wrote", TARGET)
    print(WARNING)


if __name__ == "__main__":
    main()
