"""Command-line entry point. This module owns the exit codes and nothing else
returns them: gates return booleans, discovery raises EnvError, and every path
out of main() maps to exactly one of EXIT_OK / EXIT_FAIL / EXIT_ENV."""
import argparse

from . import selftest
from .report import Report

EXIT_OK = 0     # every gate passed
EXIT_FAIL = 1   # a gate failed: the board changed
EXIT_ENV = 2    # could not run the check, or the command line was wrong

COMMANDS = ("doctor", "baseline", "gerber", "netlist", "rules", "all", "selftest")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python3 tools/kicad-verify.py",
        description="Prove a KiCad project's copper, connectivity and rule counts "
                    "are unchanged.")
    parser.add_argument("command", choices=COMMANDS, help="what to run")
    parser.add_argument("--json", action="store_true",
                        help="emit one JSON document on stdout instead of verdict lines")
    parser.add_argument("--verbose", action="store_true",
                        help="show tool output that is normally filtered as noise")
    parser.add_argument("--project", metavar="PCB",
                        help="path to the .kicad_pcb (default: the one in the repo root)")
    parser.add_argument("--baseline-dir", metavar="DIR", default=None,
                        help="baseline location (default: verify/baseline)")
    parser.add_argument("--geometry", action="store_true",
                        help="gerber: compare geometry only, ignoring X2 net attributes")
    parser.add_argument("--force", action="store_true",
                        help="baseline: overwrite an existing baseline")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    report = Report(json_mode=args.json, verbose=args.verbose)

    if args.command == "selftest":
        ok = selftest.run(report)
        report.finish()
        return EXIT_OK if ok else EXIT_FAIL

    if args.command == "doctor":
        return _doctor(args, report)

    if args.command == "gerber":
        from . import gerber
        mode = "geometry" if args.geometry else "strict"
        return _gate(args, report, lambda env: gerber.run(env, report, mode))

    report.error("%s is not implemented yet" % args.command)
    report.finish()
    return EXIT_ENV


def _gate(args, report, fn):
    """Build the environment, run one gate, map every outcome to an exit code.
    fn takes the Environment and returns True or False; anything that stops it
    running raises EnvError and becomes exit 2."""
    from . import discover
    try:
        env = discover.build(args)
        ok = fn(env)
    except discover.EnvError as exc:
        report.error(str(exc))
        report.finish()
        return EXIT_ENV
    report.finish()
    return EXIT_OK if ok else EXIT_FAIL


def _doctor(args, report):
    """Answer the environment question directly. Most real failures are environmental --
    KiCad missing, wrong version, no project, no baseline -- and both humans and agents
    should be able to ask once rather than infer it from a gate that failed for the
    wrong reason. Exit 0 when everything needed is present, 2 when anything is not, so
    it works as a precondition check and not only as prose."""
    from . import discover
    try:
        env = discover.build(args)
    except discover.EnvError as exc:
        report.error(str(exc))
        report.gate("doctor", False, "environment incomplete")
        report.finish()
        return EXIT_ENV

    report.progress("doctor", "kicad-cli   %s" % env.cli)
    report.progress("doctor", "version     %s" % env.version)
    report.progress("doctor", "repository  %s" % env.repo_root)
    report.progress("doctor", "board       %s" % env.pcb)
    report.progress("doctor", "schematic   %s" % env.sch)
    report.progress("doctor", "baseline    %s" % env.baseline_dir)

    from . import baseline as baseline_mod
    meta = baseline_mod.read_meta(env.baseline_dir)
    if meta is None:
        report.error("no baseline in %s. Run: python3 tools/kicad-verify.py baseline"
                     % env.baseline_dir)
        report.gate("doctor", False, "no baseline captured")
        report.finish()
        return EXIT_ENV

    from .report import drift_suffix
    suffix = drift_suffix(meta.get("kicad_version", ""), env.version)
    if suffix:
        report.warn("baseline captured with KiCad %s, running %s"
                    % (meta.get("kicad_version"), env.version))
    report.gate("doctor", True,
                "kicad-cli %s, baseline from %s%s"
                % (env.version, meta.get("kicad_version", "?"), suffix),
                kicad_version=env.version,
                baseline_kicad=meta.get("kicad_version"),
                version_drift=bool(suffix))
    report.finish()
    return EXIT_OK
