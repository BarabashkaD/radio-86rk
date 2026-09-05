"""Report 3D model coverage, counting only models whose file actually resolves.

This distinction matters: the board started with 109 footprints carrying KiCad-4-era model
references (dil/, discret/, pin_array/) that resolve to nothing. Counting "has a model
entry" would score those as covered. Counting "the file exists" is the honest measure.

Path variables are expanded the way KiCad expands them.

Usage: model_coverage.py <board.kicad_pcb> [--list-missing]
"""
import os
import sys

import pcbnew

BOARD = sys.argv[1]
VERBOSE = "--list-missing" in sys.argv

KICAD_APP = "/Applications/KiCad/KiCad.app/Contents"
VARS = {
    "KICAD10_3DMODEL_DIR": KICAD_APP + "/SharedSupport/3dmodels",
    "KICAD10_3RD_PARTY": os.path.expanduser("~/Documents/KiCad/10.0/3rdparty"),
    "KICAD6_3RD_PARTY": os.path.expanduser("~/Documents/KiCad/10.0/3rdparty"),
    "KIPRJMOD": os.path.dirname(os.path.abspath(BOARD)),
}


def resolve(path):
    for k, v in VARS.items():
        path = path.replace("${%s}" % k, v).replace("$(%s)" % k, v)
    return path


board = pcbnew.LoadBoard(BOARD)
# Components that legitimately never get a model.
EXEMPT_PREFIXES = ("HOLE", "LOGO")

covered, missing, exempt = [], [], []
for fp in board.GetFootprints():
    ref = fp.GetReference()
    paths = [m.m_Filename for m in fp.Models()]
    ok = [p for p in paths if os.path.exists(resolve(p))]
    if ok:
        covered.append(ref)
    elif ref.startswith(EXEMPT_PREFIXES):
        exempt.append(ref)
    else:
        missing.append((ref, paths[0] if paths else "<none>"))

target = len(covered) + len(missing)
print("3D coverage: %d / %d   (exempt: %d — %s)"
      % (len(covered), target, len(exempt), " ".join(sorted(exempt)) or "none"))
if missing:
    print("without a resolving model: %d" % len(missing))
    if VERBOSE:
        for ref, p in sorted(missing):
            print("  %-8s %s" % (ref, p))
    else:
        print("  " + " ".join(sorted(r for r, _ in missing)))
