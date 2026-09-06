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
        return _gate(args, report,
                     lambda env: gerber.run(env, report, mode, *_drift(env, report)))

    if args.command == "netlist":
        from . import netlist
        return _gate(args, report,
                     lambda env: netlist.run(env, report, *_drift(env, report)))

    if args.command == "rules":
        from . import rules
        return _gate(args, report, lambda env: rules.run(env, report))

    if args.command == "baseline":
        from . import baseline as baseline_mod
        return _gate(args, report,
                     lambda env: baseline_mod.capture(env, report, args.force))

    if args.command == "all":
        return _all(args, report)

    report.error("%s is not implemented yet" % args.command)
    report.finish()
    return EXIT_ENV


def _drift(env, report):
    """The version-drift suffix, the two version strings behind it, and the warning
    that goes with it. All three reach an agent through the verdict line and the
    JSON; the warning reaches a human on stderr. It is never an exit code -- it
    obliges the reader to check the changelog, it does not decide for them.

    The versions are returned whenever a baseline exists, not only when the majors
    disagree: absent-versus-false is exactly the ambiguity structured output exists
    to remove. When there is no baseline at all both come back None -- the caller's
    gate raises before it would report anything, so there is nothing to decide.
    """
    from . import baseline as baseline_mod
    meta = baseline_mod.read_meta(env.baseline_dir)
    if not meta:
        return "", None, None
    baseline_kicad = meta.get("kicad_version")
    suffix = baseline_mod.drift_for(env)
    if suffix:
        report.warn("baseline was captured with a different major KiCad version; "
                    "differences may be emitter changes, not board changes")
    return suffix, baseline_kicad, env.version


def _gate(args, report, fn):
    """Build the environment, run one gate, map every outcome to an exit code.
    fn takes the Environment and returns True or False; anything that stops it
    running raises EnvError and becomes exit 2.

    Anything else -- an OSError from a full disk, a malformed report, any exception
    this harness did not anticipate -- also becomes exit 2, not exit 1. CPython exits
    1 on an uncaught exception by default, and 1 means "the board changed" in this
    tool's vocabulary; letting that default stand would make it report a copper change
    that never happened. KeyboardInterrupt and SystemExit are BaseException, not
    Exception, so a deliberate interrupt still propagates instead of being reported
    as an environment problem."""
    from . import discover
    try:
        env = discover.build(args)
        ok = fn(env)
    except discover.EnvError as exc:
        report.error(str(exc))
        report.finish()
        return EXIT_ENV
    except Exception as exc:
        _report_unexpected(report, exc)
        report.finish()
        return EXIT_ENV
    report.finish()
    return EXIT_OK if ok else EXIT_FAIL


def _report_unexpected(report, exc, prefix=""):
    """An exception the harness did not anticipate reaching this far. Reported
    legibly -- the exception type and message, and a line saying the check could not
    be completed so the board's state is unknown -- because it must map to EXIT_ENV,
    never be mistaken for a gate that ran and found a difference. The traceback is
    kept for --verbose only: a genuine harness bug still needs debugging, but printing
    it by default would bury the one-line message that matters under noise."""
    report.error("%sunexpected %s: %s" % (prefix, type(exc).__name__, exc))
    report.error("%scheck could not be completed; the board's state is unknown"
                 % prefix)
    if report.verbose:
        import traceback
        report.detail(traceback.format_exc())


def combine(outcomes):
    """Final exit code for a run of several gates.

    Environment problems outrank failures: 'I could not run the check' is a more
    important fact than 'the check failed', and an agent that collapses the two will
    report a regression that did not happen.
    """
    if "env" in outcomes:
        return EXIT_ENV
    if "fail" in outcomes:
        return EXIT_FAIL
    return EXIT_OK


def _run_one_gate(report, name, call):
    """Run one gate within `all` and record its outcome. Returns "pass", "fail" or
    "env". Extracted from `_all` as its own seam so this recording logic can be
    exercised directly by a check, without a full environment or the real project.

    A gate that could not run is recorded with report.info, not report.gate: FAIL
    would claim something was checked and found wrong, when nothing was checked at
    all. An agent that reads gates[].status per gate -- a plausible pattern, since
    the combined 'all' line is deliberately the only place that names incompleteness
    -- must not see netlist=FAIL and report a regression that never happened."""
    from . import discover
    try:
        return "pass" if call() else "fail"
    except discover.EnvError as exc:
        report.error("%s: %s" % (name, exc))
        report.info(name, "could not run")
        return "env"
    except Exception as exc:
        _report_unexpected(report, exc, prefix="%s: " % name)
        report.info(name, "could not run")
        return "env"


def _all(args, report):
    """Every gate, in order, with nothing skipped. A run reports everything that is
    wrong, not just the first thing -- someone fixing three problems should learn about
    all three in one run. selftest is not included: it tests the tool, not the project.
    rules never decides the run: it has no baseline and reports rather than judges."""
    from . import discover, gerber, netlist, rules
    try:
        env = discover.build(args)
    except discover.EnvError as exc:
        report.error(str(exc))
        report.finish()
        return EXIT_ENV
    except Exception as exc:
        _report_unexpected(report, exc)
        report.finish()
        return EXIT_ENV

    drift = _drift(env, report)

    mode = "geometry" if args.geometry else "strict"
    outcomes = [_run_one_gate(report, name, call) for name, call in
               (("gerber", lambda: gerber.run(env, report, mode, *drift)),
                ("netlist", lambda: netlist.run(env, report, *drift)),
                ("rules", lambda: rules.run(env, report)))]

    code = combine(outcomes)
    if code == EXIT_ENV:
        # Not a verdict on the board: a gate did not run, so there is nothing to
        # pass or fail. Saying FAIL here would assert something that was not checked.
        report.info("all", "incomplete: %s" % ", ".join(
            "%s=%s" % pair for pair in zip(("gerber", "netlist", "rules"), outcomes)))
    else:
        report.gate("all", code == EXIT_OK,
                    "%d of %d gates passed"
                    % (outcomes.count("pass"), len(outcomes)))
    report.finish()
    return code


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
