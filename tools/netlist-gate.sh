#!/usr/bin/env bash
# Export the netlist and diff its connectivity against verify/baseline/netlist.nets.
#   --capture   write the baseline instead of comparing
#
# The gerber gate cannot see schematic-side damage, because the board is not edited. The
# netlist is the ground truth linking schematic to copper: if it is unchanged, no symbol
# edit can have moved a net to a different pad.
#
# Only the (nets ...) section is compared. The rest of the netlist legitimately gains and
# loses metadata when symbols are refreshed from their libraries -- datasheet URLs,
# ki_keywords, ki_fp_filters, ngspice Sim.* fields -- none of which is connectivity.
set -euo pipefail
source "$(git rev-parse --show-toplevel)/tools/kicad-env.sh"

# Homebrew fontconfig emits ~40 warning lines per kicad-cli call. Drop only those;
# anything else on stderr is a real error and must stay visible.
nofc() { "$@" 2> >(grep -v "^Fontconfig warning" >&2); }
mkdir -p "$BUILD" "$REPO_ROOT/verify/baseline"

BASE="$REPO_ROOT/verify/baseline/netlist.nets"
CUR="$BUILD/netlist.nets"

nofc "$KICAD_CLI" sch export netlist --format kicadsexpr \
    --output "$BUILD/netlist.raw" "$SCH" >/dev/null
awk '/^\t\(nets/{f=1} f' "$BUILD/netlist.raw" > "$CUR"

if [ "${1:-}" = "--capture" ]; then
  cp "$CUR" "$BASE"
  echo "netlist-gate: captured baseline ($(wc -l < "$BASE" | tr -d ' ') lines)"
  exit 0
fi

[ -f "$BASE" ] || { echo "netlist-gate: no baseline; run --capture" >&2; exit 2; }
if diff -q "$BASE" "$CUR" >/dev/null; then
  echo "netlist-gate: PASS - every pin maps to the same net"
else
  echo "netlist-gate: FAIL"; diff -u "$BASE" "$CUR" | head -40; exit 1
fi
