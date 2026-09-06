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

    report.error("%s is not implemented yet" % args.command)
    report.finish()
    return EXIT_ENV
