#!/usr/bin/env bash
# Single source of truth for KiCad tool locations. Source, don't execute.
#
# REPO_ROOT comes from git rather than ${BASH_SOURCE[0]}: this file is sourced from
# interactive shells, and on macOS that shell is zsh, where BASH_SOURCE is empty.
KICAD_APP="/Applications/KiCad/KiCad.app/Contents"
export KICAD_CLI="$KICAD_APP/MacOS/kicad-cli"
export KICAD_PY="$KICAD_APP/Frameworks/Python.framework/Versions/3.9/bin/python3"
export KICAD_3DMODEL_DIR="$KICAD_APP/SharedSupport/3dmodels"
export KICAD_3RD_PARTY="$HOME/Documents/KiCad/10.0/3rdparty"
export REPO_ROOT="$(git rev-parse --show-toplevel)"
export PCB="$REPO_ROOT/KiCad/Radio-86RK.kicad_pcb"
export SCH="$REPO_ROOT/KiCad/Radio-86RK.kicad_sch"
export BUILD="$REPO_ROOT/.build"

for v in KICAD_CLI KICAD_PY KICAD_3DMODEL_DIR KICAD_3RD_PARTY PCB SCH; do
  eval "p=\$$v"
  [ -e "$p" ] || { echo "kicad-env: missing $v = $p" >&2; return 1 2>/dev/null || exit 1; }
done
