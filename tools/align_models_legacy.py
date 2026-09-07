"""Recover the manufacturer 3D models from the abandoned `migrate2kicad10` branch.

That branch attacked the same problem from the other end: instead of keeping the board's
own footprints and hanging public models off them, it replaced each footprint with a
manufacturer-sourced one that carried its own model. The footprint swaps moved copper, so
they are unusable here — but the seven STEP files they brought in are exactly the parts
this board actually uses, and a model does not care which footprint introduced it.

This tool proves the two footprints are the same physical part before reusing the model,
rather than assuming it. For each pair it brute-forces the four 90-degree rotations, lands
our pad 1 on theirs, and reports the worst distance from any of our pads to the nearest
same-named pad of theirs. A residual of a few microns means "same part, different frame";
a residual of millimetres would mean the model does not belong here.

Then it composes two transforms. KiCad renders a model as

    translate(offset) . Rz(-rot_z) . Ry(-rot_y) . Rx(-rot_x) . scale

so pre-multiplying an extra Z rotation theta (the frame difference between their footprint
and ours) gives

    translate(Rz(theta).offset + delta) . Rz(-(rot_z + theta)) . Ry . Rx . scale

i.e. the stored Z rotations simply add, rot_x and rot_y and scale pass through untouched,
and the old offset is rotated by theta before delta is added. Offsets live in the 3D frame,
whose Y is inverted relative to the board's (see tools/align_models.py).

Usage: align_models_legacy.py [--branch migrate2kicad10]
       -> prints models.tsv rows on stdout, the congruence evidence on stderr
"""
import math
import os
import re
import subprocess
import sys
import tempfile

import pcbnew

OURS = "KiCad/Radio86RK.pretty"
SHAPES = "${KIPRJMOD}/Radio86RK.3dshapes"
BRANCH = "migrate2kicad10"
if "--branch" in sys.argv:
    BRANCH = sys.argv[sys.argv.index("--branch") + 1]

# our footprint -> (their .pretty, their footprint, the STEP basename we vendored)
PAIRS = [
    ("DC-DC_SIP8",                    "DCDC_Custom",              "IZ0512S",       "IZ0512S.step"),
    ("Conn_DIN_8pin",                 "Conn_DIN_Custom",          "SDF-80J",       "SDF-80J.step"),
    ("Conn_RCA_Right",                "Conn_RCA_Custom",          "RCJ-014",       "RCJ-014.step"),
    ("Conn_Power_Jack_Circular_Pads", "Conn_DCJack_Custom",       "KLDX-0202-A",   "KLDX-0202-A.step"),
    ("Conn_Friction_Lock_8P_2.54mm",  "Conn_FrictionLock_Custom", "640456-8",      "640456-8.step"),
    ("Speaker_12mm",                  "Speaker_Custom",           "AT-1224-TWT-R", "AT-1224-TWT-R.step"),
    ("Switch_Tactile_6mm_Right",      "Switch_Tactile_Custom",    "B3F-3152",      "B3F-3152.step"),
]

# Corrections to what the old branch stored, keyed by their footprint name.
#
# U26 is the one model here that is not the real part: no STEP exists for the XP Power
# IZ0512S, so the branch took the sibling IA0512S and scaled it. The two ratios it computed
# are right but they are on the wrong axes. Its note orders both parts "L x H x W"
# (IA 19.3 x 10.1 x 6.0, IZ 21.85 x 11.10 x 9.20 -- and the IZ figures do match the
# mechanical drawing on page 1 of Documentation/XP Power - DC-DC Converter - IZ Series.pdf,
# where 0.44" = 11.10 is the height and 0.36" = 9.20 the width on the bottom view). But the
# STEP itself is authored Z-up, so its axes run L x W x H: measuring the file gives
# X 19.30, Y 6.09, Z -5.00..10.16. Stored as (1.1321, 1.0990, 1.5333), the height ratio
# lands on width and the width ratio on height, rendering U26 about 15.6 mm tall and 6.7 mm
# thick instead of 11.10 x 9.20 -- a brick of roughly the right footprint and visibly the
# wrong proportions.
SCALE_FIX = {
    "IZ0512S": (21.85 / 19.30, 9.20 / 6.09, 11.10 / 10.16),
}

MODEL_RE = re.compile(
    r"\(model\s+\"[^\"]*\"\s*"
    r"\(offset\s*\(xyz\s+([-+.\deE]+)\s+([-+.\deE]+)\s+([-+.\deE]+)\s*\)\s*\)\s*"
    r"\(scale\s*\(xyz\s+([-+.\deE]+)\s+([-+.\deE]+)\s+([-+.\deE]+)\s*\)\s*\)\s*"
    r"\(rotate\s*\(xyz\s+([-+.\deE]+)\s+([-+.\deE]+)\s+([-+.\deE]+)\s*\)\s*\)",
    re.S)


def git_show(path):
    return subprocess.check_output(["git", "show", "%s:%s" % (BRANCH, path)])


def pads(lib, name):
    fp = pcbnew.FootprintLoad(lib, name)
    if fp is None:
        return None
    out = {}
    for p in fp.Pads():
        out.setdefault(p.GetName(), []).append(
            (pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)))
    return out


def rot_pt(x, y, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return x * c - y * s, x * s + y * c


def worst_residual(a, b, rot, ox, oy):
    """Largest distance from one of our pads to the nearest same-named pad of theirs."""
    worst, which = 0.0, None
    for name, ours in a.items():
        if name not in b:
            continue
        for (px, py) in ours:
            d = min(math.hypot(rot_pt(qx, qy, rot)[0] + ox - px,
                               rot_pt(qx, qy, rot)[1] + oy - py)
                    for (qx, qy) in b[name])
            if d > worst:
                worst, which = d, name
    return worst, which


def best_fit(a, b):
    """(worst_residual, pad, theta, delta_x, delta_y) in board coordinates."""
    cands = []
    for theta in (0.0, 90.0, 180.0, 270.0):
        for (bx, by) in b.get("1", []):
            for (ax, ay) in a.get("1", []):
                rx, ry = rot_pt(bx, by, theta)
                ox, oy = ax - rx, ay - ry
                w, which = worst_residual(a, b, theta, ox, oy)
                cands.append((w, which, theta, ox, oy))
    cands.sort(key=lambda c: c[0])
    return cands[0]


def main():
    tmp = tempfile.mkdtemp(prefix="legacy-fp-")
    print("# Recovered from the %s branch by tools/align_models_legacy.py." % BRANCH)
    print("# footprint\tmodel\toff_x\toff_y\toff_z\trot_z\trot_x\trot_y\tsx\tsy\tsz")
    for ours, theirlib, theirname, step in PAIRS:
        src = "KiCad/%s.pretty/%s.kicad_mod" % (theirlib, theirname)
        d = os.path.join(tmp, theirlib + ".pretty")
        os.path.isdir(d) or os.makedirs(d)
        text = git_show(src)
        open(os.path.join(d, theirname + ".kicad_mod"), "wb").write(text)

        m = MODEL_RE.search(text.decode("utf-8"))
        if not m:
            sys.exit("no (model ...) block in %s" % src)
        g = [float(x) for x in m.groups()]
        off_old, scale, rot_old = g[0:3], g[3:6], g[6:9]
        if theirname in SCALE_FIX:
            was, scale = scale, list(SCALE_FIX[theirname])
            print("  %-32s scale corrected (%.4f, %.4f, %.4f) -> (%.4f, %.4f, %.4f)"
                  % (theirname, was[0], was[1], was[2], scale[0], scale[1], scale[2]),
                  file=sys.stderr)

        a, b = pads(OURS, ours), pads(d, theirname)
        if a is None or b is None:
            sys.exit("could not load %s / %s" % (ours, theirname))
        resid, pad, theta, dx, dy = best_fit(a, b)

        # compose: rotate their in-footprint offset by theta (3D frame, so -theta),
        # then translate by our frame delta (3D frame, so Y negated)
        ox, oy = rot_pt(off_old[0], off_old[1], -theta)
        ox, oy = ox + dx, oy + (-dy)
        rz = (rot_old[2] + theta) % 360.0
        if rz > 180.0:
            rz -= 360.0

        print("%s\t%s/%s\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f"
              % (ours, SHAPES, step, ox, oy, off_old[2], rz,
                 rot_old[0], rot_old[1], scale[0], scale[1], scale[2]))
        print("  %-32s <- %-14s  fit rot %5.1f, worst pad residual %.4f mm (pad %s)"
              % (ours, theirname, theta, resid, pad), file=sys.stderr)


if __name__ == "__main__":
    main()
