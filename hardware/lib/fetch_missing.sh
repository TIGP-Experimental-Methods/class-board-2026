#!/usr/bin/env bash
# Paced fetch of the BOM parts still missing from e2k/class_board.
# Lessons (2026-09-06): EasyEDA returns HTTP 403 after ~15 quick calls -> pace at 25 s.
# easyeda2kicad exits 1 on "Symbol/Footprint already exists" (shared 0603/0805 footprints, or a symbol
# created on an earlier attempt) -> its exit code is NOT a success signal. We pass --overwrite and
# declare success when the LCSC id appears in class_board.kicad_sym.
# Usage: nohup bash fetch_missing.sh > fetch_missing.log 2>&1 &
cd "$(dirname "$0")"
OUT="$(pwd -W 2>/dev/null || pwd)/e2k/class_board"
SYM="e2k/class_board.kicad_sym"
PAUSE=25
for c in $(tr -d '\r' < lcsc_codes.txt); do
  if grep -q "^$c ok" e2k_done.txt 2>/dev/null; then continue; fi
  for attempt in 1 2 3 4; do
    easyeda2kicad --full --overwrite --lcsc_id="$c" --output "$OUT" >> e2k.log 2>&1
    if grep -q "$c" "$SYM" 2>/dev/null; then
      echo "$c ok" >> e2k_done.txt; echo "$(date +%T) $c ok (attempt $attempt)"; break
    else
      echo "$(date +%T) $c fail attempt $attempt"; sleep $((attempt * 60))
    fi
  done
  sleep $PAUSE
done
echo "DONE $(grep -c ' ok' e2k_done.txt) ok of $(tr -d '\r' < lcsc_codes.txt | wc -l)"
