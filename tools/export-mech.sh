#!/usr/bin/env bash
# Export the mechanical hand-off for case design in FreeCAD.
#
# Produces four STEP files plus a switch position table, all sharing one datum. The board's
# drill/place origin is its top-left corner, so every file lands in the same coordinate
# system and a case built against one of them fits the others.
#
#   assembly.step     board + all 183 components. The full picture; 21 MB.
#   connectors.step   board + the parts that need panel cutouts (J*, SW68, SP1); 5 MB.
#   switches.step     the 68 switches with no board under them; the key-plate envelope.
#   board.step        outline, thickness and the 7 mounting holes; for standoffs and bosses.
#   placement.csv     every footprint's Ref, Value, Package, X, Y, Rotation.
#
# The split matters because the whole assembly is slow to work against. Cut panel openings
# against connectors.step and key openings against switches.step; load the full assembly
# only to check clearances.
#
# Keycaps are deliberately NOT in any of these. A cap is a case parameter, not a board one:
# its envelope drives the top-plate openings and the bezel height, and trying DSA against
# XDA should cost one filename, not a re-export. placement.csv is what makes that work --
# its Package column is the cap size (CHERRY_PCB_100H = 1u, _125H = 1.25u, _150H, _225H,
# _625H), so a FreeCAD macro can place all 68 caps from the table with no manual mapping.
# The Value column carries the key legend, for the day legends get cut as geometry.
#
# Note the switches are PCB-mount (CHERRY_PCB_*), not plate-mount: nothing holds the keys at
# a plate height, so the case top has to clear the switch housing at 11.6 mm rather than
# sandwich a plate there. Perigoso's switch model spans z -3.16 .. +15.44 mm.
#
# Usage: tools/export-mech.sh [outdir]        (default: .build/mech)
set -euo pipefail
source "$(git rev-parse --show-toplevel)/tools/kicad-env.sh"

# Two sources of noise, both harmless, both dropped by exact match so a real error on
# stderr still shows: Homebrew fontconfig warns ~40 times per kicad-cli call, and on macOS
# kicad-cli stats its output file before creating it, which logs an NSCocoaErrorDomain 260
# "couldn't be opened because there is no such file" for every export.
nofc() {
    "$@" 2> >(grep -vE "^Fontconfig warning|Error retrieving source file attributes" >&2)
}

OUT="${1:-$BUILD/mech}"
mkdir -p "$OUT"

# --subst-models prefers a STEP/IGES sibling over a VRML one, so the output is solid
# geometry rather than mesh -- FreeCAD can cut against solids, not against triangles.
# --drill-origin pins the datum to the board corner (see tools/kicad-env.sh consumers and
# the aux origin stored in the board file); without it every export floats by 6.275 mm.
STEP_OPTS=(--force --subst-models --drill-origin)

step() {  # step <name> <extra args...>
    local name="$1"; shift
    nofc "$KICAD_CLI" pcb export step "${STEP_OPTS[@]}" "$@" \
        --output "$OUT/$name.step" "$PCB" >/dev/null
    printf '  %-16s %7s\n' "$name.step" "$(du -h "$OUT/$name.step" | cut -f1)"
}

echo "mechanical export -> $OUT"
step assembly
step connectors --component-filter "J*,SW68,SP1"
step switches   --component-filter "SW*" --no-board-body
step board      --board-only

nofc "$KICAD_CLI" pcb export pos --format csv --units mm --side front \
    --use-drill-file-origin --output "$OUT/placement.csv" "$PCB" >/dev/null
printf '  %-16s %7s   (%d switches)\n' "placement.csv" \
    "$(du -h "$OUT/placement.csv" | cut -f1)" \
    "$(grep -c '^"SW' "$OUT/placement.csv")"

echo
echo "datum: board top-left corner; board is 266.85 x 203.35 mm, X right, Y down in the CSV."
