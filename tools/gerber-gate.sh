#!/usr/bin/env bash
# Export gerbers+drill and diff against verify/baseline.
#   --strict    (default) geometry plus X2 net/component attributes
#   --geometry  geometry only; drops %TO.*/%TA.*, for tasks that legitimately rename nets
#   --capture   write the baseline instead of comparing
#
# Gerbers go through tools/gerber_canon.py rather than a byte diff: KiCad re-emits the same
# geometry in a different order and renumbers aperture D-codes whenever it rewrites a board.
set -euo pipefail
source "$(git rev-parse --show-toplevel)/tools/kicad-env.sh"

# Homebrew fontconfig emits ~40 warning lines per kicad-cli call. Drop only those;
# anything else on stderr is a real error and must stay visible.
nofc() { "$@" 2> >(grep -v "^Fontconfig warning" >&2); }

MODE="strict"; CAPTURE=0
for a in "$@"; do
  case "$a" in
    --strict)   MODE="strict" ;;
    --geometry) MODE="geometry" ;;
    --capture)  CAPTURE=1 ;;
    *) echo "unknown arg: $a" >&2; exit 2 ;;
  esac
done

RAW="$BUILD/gerber-raw"; NORM="$BUILD/gerber-$MODE"
BASE="$REPO_ROOT/verify/baseline/$MODE"
rm -rf "$RAW" "$NORM"; mkdir -p "$RAW" "$NORM"

nofc "$KICAD_CLI" pcb export gerbers --output "$RAW" "$PCB" >/dev/null
nofc "$KICAD_CLI" pcb export drill   --output "$RAW" "$PCB" >/dev/null

# Timestamp-bearing lines, all four forms observed in KiCad 10.0.4 output.
STAMP='CreationDate|Created by KiCad|DRILL file KiCad'
for f in "$RAW"/*; do
  b="$(basename "$f")"
  out="$NORM/$b"
  case "$b" in
    *.drl|*.gbrjob)
      # Drill and job files are already stable and order-independent.
      grep -vE "$STAMP" "$f" > "$out" ;;
    *)
      "$KICAD_PY" "$REPO_ROOT/tools/gerber_canon.py" "$f" > "$out"
      if [ "$MODE" = "strict" ]; then
        # Keep X2 net/component attributes so a net rename is visible.
        grep -E '^%T[OA]\.' "$f" | sort >> "$out" || true
      fi ;;
  esac
done

if [ "$CAPTURE" = 1 ]; then
  rm -rf "$BASE"; mkdir -p "$(dirname "$BASE")"; cp -R "$NORM" "$BASE"
  echo "gerber-gate: captured $MODE baseline ($(ls "$BASE" | wc -l | tr -d ' ') files)"
  exit 0
fi

[ -d "$BASE" ] || { echo "gerber-gate: no $MODE baseline; run --capture" >&2; exit 2; }
if diff -r -q "$BASE" "$NORM" >/dev/null; then
  echo "gerber-gate($MODE): PASS - board geometry unchanged"
else
  echo "gerber-gate($MODE): FAIL"; diff -r -u "$BASE" "$NORM" | head -80; exit 1
fi
