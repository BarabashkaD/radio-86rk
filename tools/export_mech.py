"""Export the mechanical hand-off for case design in FreeCAD.

Produces four STEP files plus a switch position table, all sharing one datum. The board's
drill/place origin is its top-left corner, so every file lands in the same coordinate
system and a case built against one of them fits the others.

  assembly.step     board + all 183 components. The full picture; 21 MB.
  connectors.step   board + the parts that need panel cutouts (J*, SW68, SP1); 5 MB.
  switches.step     the 68 switches with no board under them; the key-plate envelope.
  board.step        outline, thickness and the 7 mounting holes; for standoffs and bosses.
  placement.csv     every footprint's Ref, Value, Package, X, Y, Rotation.

The split matters because the whole assembly is slow to work against. Cut panel openings
against connectors.step and key openings against switches.step; load the full assembly
only to check clearances.

Keycaps are deliberately NOT in any of these. A cap is a case parameter, not a board one:
its envelope drives the top-plate openings and the bezel height, and trying DSA against
XDA should cost one filename, not a re-export. placement.csv is what makes that work --
its Package column is the cap size (CHERRY_PCB_100H = 1u, _125H = 1.25u, _150H, _225H,
_625H), so a FreeCAD macro can place all 68 caps from the table with no manual mapping.
The Value column carries the key legend, for the day legends get cut as geometry.

Note the switches are PCB-mount (CHERRY_PCB_*), not plate-mount: nothing holds the keys at
a plate height, so the case top has to clear the switch housing at 11.6 mm rather than
sandwich a plate there. The keyswitch library's switch model spans z -3.16 .. +15.44 mm.

Usage: tools/export_mech.py [outdir]        (default: .build/mech)

Needs kicad-cli, not pcbnew, so any Python 3.8+ runs it directly.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kicadverify import discover                                      # noqa: E402
from kicadverify.report import Report                                 # noqa: E402

# --subst-models prefers a STEP/IGES sibling over a VRML one, so the output is solid
# geometry rather than mesh -- FreeCAD can cut against solids, not against triangles.
# --drill-origin pins the datum to the board corner (matching the aux origin stored in
# the board file); without it every export floats by 6.275 mm.
STEP_OPTS = ["--force", "--subst-models", "--drill-origin"]

# name -> the extra arguments that select what goes in it.
STEPS = [
    ("assembly", []),
    ("connectors", ["--component-filter", "J*,SW68,SP1"]),
    ("switches", ["--component-filter", "SW*", "--no-board-body"]),
    ("board", ["--board-only"]),
]


def _size(path):
    return "%.1f MB" % (os.path.getsize(path) / 1048576.0)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tools/export_mech.py",
                                     description=__doc__.split("\n")[0])
    parser.add_argument("outdir", nargs="?", default=None,
                        help="output directory (default: .build/mech)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    report = Report(json_mode=False, verbose=args.verbose)
    try:
        env = discover.build(args)
    except discover.EnvError as exc:
        report.error(str(exc))
        report.finish()
        return 2

    out = args.outdir or os.path.join(env.repo_root, ".build", "mech")
    if not os.path.isdir(out):
        os.makedirs(out)
    report.detail("mechanical export -> %s" % out)

    try:
        for name, extra in STEPS:
            path = os.path.join(out, name + ".step")
            # Arguments go in an argv list, never through a shell. The shell script
            # quoted "J*,SW68,SP1" and "SW*" to stop the shell touching them; here the
            # quotes must NOT be part of the value, and shell=True must not be used --
            # * is KiCad's wildcard and would otherwise glob against the working
            # directory. run_cli raises on a non-zero exit, which is the fail-fast the
            # script had from `set -euo pipefail`: without it the size report below
            # would run on a file that was never created.
            discover.run_cli(env, report,
                             ["pcb", "export", "step"] + STEP_OPTS + extra
                             + ["--output", path, env.pcb],
                             "pcb export step (%s)" % name)
            report.detail("  %-16s %9s" % (name + ".step", _size(path)))

        placement = os.path.join(out, "placement.csv")
        discover.run_cli(env, report,
                         ["pcb", "export", "pos", "--format", "csv", "--units", "mm",
                          "--side", "front", "--use-drill-file-origin",
                          "--output", placement, env.pcb],
                         "pcb export pos")
        with open(placement) as handle:
            switches = sum(1 for line in handle if line.startswith('"SW'))
        report.detail("  %-16s %9s   (%d switches)"
                      % ("placement.csv", _size(placement), switches))
    except discover.EnvError as exc:
        report.error(str(exc))
        report.finish()
        return 2

    report.detail("")
    report.detail("datum: board top-left corner; board is 266.85 x 203.35 mm, "
                  "X right, Y down in the CSV.")
    report.finish()
    return 0


if __name__ == "__main__":
    sys.exit(main())
