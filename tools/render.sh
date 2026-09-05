#!/usr/bin/env bash
# Render the board to PNG for the visual record. Usage: tools/render.sh <tag>
set -euo pipefail
source "$(git rev-parse --show-toplevel)/tools/kicad-env.sh"

TAG="${1:?usage: render.sh <tag>}"
OUT="$REPO_ROOT/verify/renders"
mkdir -p "$OUT"

"$KICAD_CLI" pcb render --output "$OUT/$TAG-top.png" \
    --width 2400 --height 1600 --quality high \
    --rotate '-30,0,25' --perspective --floor "$PCB"

echo "rendered $OUT/$TAG-top.png"
