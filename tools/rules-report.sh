#!/usr/bin/env bash
# Print ERC and DRC violation counts, total and by type.
set -euo pipefail
source "$(git rev-parse --show-toplevel)/tools/kicad-env.sh"

mkdir -p "$BUILD"

"$KICAD_CLI" sch erc --format json --output "$BUILD/erc.json" \
    --severity-all "$SCH" >/dev/null 2>&1 || true
"$KICAD_CLI" pcb drc --format json --output "$BUILD/drc.json" \
    --severity-all "$PCB" >/dev/null 2>&1 || true

"$KICAD_PY" - "$BUILD/erc.json" "$BUILD/drc.json" <<'PY'
import collections
import json
import sys


def violations(doc):
    """ERC reports nest violations under sheets; DRC lists them at the top level."""
    if "sheets" in doc:
        return [v for s in doc["sheets"] for v in s.get("violations", [])]
    return doc.get("violations", [])


for label, path in (("ERC", sys.argv[1]), ("DRC", sys.argv[2])):
    try:
        doc = json.load(open(path))
    except Exception as exc:
        print("%s  <unreadable: %s>" % (label, exc))
        continue
    items = violations(doc)
    sev = collections.Counter(v.get("severity", "?") for v in items)
    print("%s %d  errors=%d warnings=%d"
          % (label, len(items), sev.get("error", 0), sev.get("warning", 0)))
    for t, n in collections.Counter(v["type"] for v in items).most_common():
        print("     %4d  %s" % (n, t))
    if label == "DRC":
        print("     unconnected=%d  parity=%d"
              % (len(doc.get("unconnected_items", [])),
                 len(doc.get("schematic_parity", []))))
PY
