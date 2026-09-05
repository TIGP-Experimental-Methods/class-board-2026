#!/usr/bin/env bash
# Paced fetch of the BOM parts still missing from e2k/class_board (EasyEDA API 403s after ~15 quick calls).
# Usage: nohup bash fetch_missing.sh > fetch_missing.log 2>&1 &
cd "$(dirname "$0")"
OUT="$(pwd -W 2>/dev/null || pwd)/e2k/class_board"
PAUSE=25
for c in $(tr -d '\r' < lcsc_codes.txt); do
  if grep -q "^$c ok" e2k_done.txt 2>/dev/null; then continue; fi
  for attempt in 1 2 3 4; do
    if easyeda2kicad --full --lcsc_id="$c" --output "$OUT" >> e2k.log 2>&1; then
      echo "$c ok" >> e2k_done.txt; echo "$(date +%T) $c ok (attempt $attempt)"; break
    else
      echo "$(date +%T) $c fail attempt $attempt"; sleep $((attempt * 120))
    fi
  done
  sleep $PAUSE
done
echo "DONE $(grep -c ' ok' e2k_done.txt) ok"
