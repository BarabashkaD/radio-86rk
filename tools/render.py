"""Render the board to an image, for the visual record and for the README.

The gates are blind to 3D entirely, so a picture is the only detector this project has
for a whole class of defect: a rotated IC, a part off by half a pitch, a model at the
wrong scale. Every 3D defect found here was invisible to automation and obvious in a
render. See the `verifying-3d-models` skill for what that costs when an agent is the one
looking.

Usage:
    kicad-verify.py run is NOT needed -- this needs kicad-cli, not pcbnew, so any
    Python 3.8+ runs it.

    tools/render.py <tag>                    one iso view into verify/renders/ (gitignored)
    tools/render.py --view bottom <tag>       a named view
    tools/render.py --shipped                 the four images/ renders, at full quality

Views are named rather than expressed as raw angles because the angles are not obvious
and one of them is a correction: at kicad-cli's default zoom the isometric view *clips
this board* -- the spacebar row runs off the frame. The shell script this replaces used
that default, so its documented view was cropped. 0.75 fits the board with margin.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kicadverify import discover                                      # noqa: E402
from kicadverify.report import Report                                 # noqa: E402

# name -> the kicad-cli arguments that produce it.
VIEWS = {
    "iso-left":  ["--rotate", "-30,0,25", "--perspective", "--zoom", "0.75"],
    "iso-right": ["--rotate", "-30,0,-25", "--perspective", "--zoom", "0.75"],
    "top":       ["--side", "top"],
    "bottom":    ["--side", "bottom"],
    # A true orthographic elevation from the rear edge. Dimensionally honest, which is
    # what a panel-cutout drawing needs, but it renders as a thin strip in an empty
    # frame: kicad-cli fits the camera to the board's diagonal, so a wider aspect ratio
    # does not fill it. Use `rear` for a picture and this for a measurement.
    "back":      ["--side", "back"],
    # The connector panel, seen from behind and just above the board plane. Almost an
    # elevation -- every rear connector is identifiable and in one row -- but with
    # enough perspective to show each body's depth, which the flat `back` view cannot.
    # 180 on Z swings the camera round to the connector edge; -72 on X is the shallow
    # angle that keeps the row unstacked while the keyboard rises behind it.
    "rear":      ["--rotate", "-72,0,180", "--perspective", "--zoom", "1.25"],
}

# The five that ship in images/, beside the photographs. Version 1.4 is not a guess:
# this board's manufacturing output is byte-identical to the v1.4 reference.
# A view may override the default frame; `rear` is a wide, short band because the
# subject is a single row of parts along one edge.
SHIPPED = [
    ("top",       "images/Radio-86RK-1.4-3D-Top.jpg", None, None),
    ("iso-left",  "images/Radio-86RK-1.4-3D-Iso-Left.jpg", None, None),
    ("iso-right", "images/Radio-86RK-1.4-3D-Iso-Right.jpg", None, None),
    ("rear",      "images/Radio-86RK-1.4-3D-Rear.jpg", 2400, 790),
    ("bottom",    "images/Radio-86RK-1.4-3D-Bottom.jpg", None, None),
]


def render(env, report, view, output, width, height, quality):
    """One view. The extension decides the format -- kicad-cli writes PNG or JPEG."""
    directory = os.path.dirname(output)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    args = (["pcb", "render", "--output", output,
             "--width", str(width), "--height", str(height),
             "--quality", quality, "--floor"]
            + VIEWS[view] + [env.pcb])
    # run_cli raises EnvError on a non-zero exit, which is the fail-fast the shell
    # script got from `set -e`. Without it the size report below runs on a file that
    # was never written.
    discover.run_cli(env, report, args, "pcb render")
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="tools/render.py", description=__doc__.split("\n")[0])
    parser.add_argument("tag", nargs="?", help="name for the output file")
    parser.add_argument("--view", default="iso-left", choices=sorted(VIEWS),
                        help="which view to render (default: iso-left)")
    parser.add_argument("--shipped", action="store_true",
                        help="render the four images/ files at full quality")
    parser.add_argument("--width", type=int, default=2400)
    parser.add_argument("--height", type=int, default=1600)
    parser.add_argument("--quality", default="high",
                        choices=["basic", "high", "user", "job_settings"])
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    report = Report(json_mode=False, verbose=args.verbose)
    try:
        env = discover.build(args)
    except discover.EnvError as exc:
        report.error(str(exc))
        report.finish()
        return 2

    try:
        if args.shipped:
            for view, relative, width, height in SHIPPED:
                path = os.path.join(env.repo_root, relative)
                render(env, report, view, path,
                       width or args.width, height or args.height, args.quality)
                report.detail("%-44s %6.0f KB" % (relative, os.path.getsize(path) / 1024.0))
        else:
            if not args.tag:
                report.error("name a tag, or pass --shipped")
                report.finish()
                return 2
            # verify/renders/ is gitignored: renders are build output, never committed.
            path = os.path.join(env.repo_root, "verify", "renders",
                                "%s-%s.png" % (args.tag, args.view))
            render(env, report, args.view, path, args.width, args.height, args.quality)
            report.detail("rendered %s" % path)
    except discover.EnvError as exc:
        report.error(str(exc))
        report.finish()
        return 2

    report.finish()
    return 0


if __name__ == "__main__":
    sys.exit(main())
