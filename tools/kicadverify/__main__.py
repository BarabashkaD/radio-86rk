"""Command-line entry point. This module owns the exit codes and nothing else
returns them: gates return booleans, discovery raises EnvError, and every path
out of main() maps to exactly one of EXIT_OK / EXIT_FAIL / EXIT_ENV."""
import argparse
import os

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
                        help="gerber/baseline: use the geometry-only baseline "
                             "(ignores X2 net attributes) instead of strict")
    parser.add_argument("--force", action="store_true",
                        help="baseline: overwrite an existing baseline of the same mode")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    report = Report(json_mode=args.json, verbose=args.verbose)

    if args.command == "selftest":
        ok = selftest.run(report)
        report.finish()
        return EXIT_OK if ok else EXIT_FAIL

    # Every other command needs discover.build() and, one way or another, the
    # baseline's meta.json -- and either can raise. This single pair is now the
    # only place that maps "something a command needed raised" to EXIT_ENV, so
    # every command inherits the guarantee instead of each command's function
    # needing to remember to add it. (meta.json is committed, so a merge
    # conflict or truncated checkout leaving it unparsable is a realistic way
    # to hit this, not just a theoretical one.) report.finish() runs here too,
    # so --json still yields a document even when a command never gets far
    # enough to call it itself.
    from . import discover
    try:
        return _dispatch(args, report)
    except discover.EnvError as exc:
        report.error(str(exc))
        report.finish()
        return EXIT_ENV
    except Exception as exc:
        _report_unexpected(report, exc)
        report.finish()
        return EXIT_ENV


def _dispatch(args, report):
    """The six non-selftest commands. Each one is free to raise EnvError (or
    anything else): main()'s guard around this call is what turns that into
    EXIT_ENV, not anything here."""
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
        mode = "geometry" if args.geometry else "strict"
        return _gate(args, report,
                     lambda env: baseline_mod.capture(env, report, args.force, mode))

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
    """Build the environment and run one gate. fn takes the Environment and
    returns True or False.

    Anything that stops it running -- EnvError from discover, an OSError from a
    full disk, a malformed report, any exception this harness did not
    anticipate -- is deliberately left to propagate: main()'s guard around the
    whole dispatch is what maps it to exit 2, not exit 1. CPython exits 1 on an
    uncaught exception by default, and 1 means "the board changed" in this
    tool's vocabulary; letting that default stand would make it report a
    copper change that never happened. KeyboardInterrupt and SystemExit are
    BaseException, not Exception, so a deliberate interrupt still propagates
    instead of being reported as an environment problem."""
    from . import discover
    env = discover.build(args)
    ok = fn(env)
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
    rules never decides the run: it has no baseline and reports rather than judges.

    discover.build() and _drift() (via baseline.read_meta) are both left to raise
    rather than caught here: main()'s guard around the whole dispatch is what maps
    that to EXIT_ENV. Only the three per-gate calls below get their own recovery,
    via _run_one_gate, because a gate that cannot run must not stop the other gates
    from reporting."""
    from . import discover, gerber, netlist, rules
    env = discover.build(args)

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
        # rules has no baseline and never decides the run (see above), so it is
        # excluded from this count: claiming it "passed" would count a gate that
        # explicitly neither passes nor fails.
        decisive = [outcome for name, outcome in
                   zip(("gerber", "netlist", "rules"), outcomes) if name != "rules"]
        report.gate("all", code == EXIT_OK,
                    "%d of %d gates passed"
                    % (decisive.count("pass"), len(decisive)))
    report.finish()
    return code


def _doctor(args, report):
    """Answer the environment question directly. Most real failures are environmental --
    KiCad missing, wrong version, no project, no baseline -- and both humans and agents
    should be able to ask once rather than infer it from a gate that failed for the
    wrong reason. Exit 0 when everything needed is present, 2 when anything is not, so
    it works as a precondition check and not only as prose.

    "Present" means everything a gate can actually consume -- kicad-cli, the
    project, and the two paths every gate compares against -- not merely a
    meta.json that no gate ever looks at. Deciding on meta.json alone let doctor
    and a gate disagree about whether a baseline exists, in both directions: a
    meta-only directory used to pass doctor and fail every gate, and a
    data-only one used to fail doctor while every gate ran fine.

    discover.build() and baseline.read_meta() are both left to raise rather than
    caught here: main()'s guard around the whole dispatch is what maps that to
    EXIT_ENV, the same as every other command."""
    from . import discover
    env = discover.build(args)

    report.progress("doctor", "kicad-cli   %s" % discover.cli_display(env.cli))
    report.progress("doctor", "version     %s" % env.version)
    report.progress("doctor", "repository  %s" % env.repo_root)
    report.progress("doctor", "board       %s" % env.pcb)
    report.progress("doctor", "schematic   %s" % env.sch)
    report.progress("doctor", "baseline    %s" % env.baseline_dir)

    strict_dir = os.path.join(env.baseline_dir, "strict")
    nets_path = os.path.join(env.baseline_dir, "netlist.nets")
    missing = [name for name, path in
              (("strict", strict_dir), ("netlist.nets", nets_path))
              if not os.path.exists(path)]
    if missing:
        report.error(
            "baseline incomplete in %s: missing %s. Run: "
            "python3 tools/kicad-verify.py baseline"
            % (env.baseline_dir, ", ".join(missing)))
        report.gate("doctor", False, "baseline incomplete: missing %s" % ", ".join(missing))
        report.finish()
        return EXIT_ENV

    from . import baseline as baseline_mod
    meta = baseline_mod.read_meta(env.baseline_dir)
    if meta is None:
        # The gates do not need meta.json -- only the artefacts checked above --
        # so its absence is a warning, not the "no baseline captured" error this
        # used to raise. That old wording claimed there was no baseline at all
        # when the gates could plainly use the one that is there; it just carries
        # no version metadata for the drift check below.
        report.warn("baseline in %s has strict/ and netlist.nets but no meta.json; "
                    "version drift cannot be checked" % env.baseline_dir)
        report.gate("doctor", True,
                    "kicad-cli %s, baseline present (no metadata)" % env.version)
        report.finish()
        return EXIT_OK

    from .report import drift_suffix
    suffix = drift_suffix(meta.get("kicad_version", ""), env.version)
    if suffix:
        report.warn("baseline captured with KiCad %s, running %s"
                    % (meta.get("kicad_version"), env.version))
    report.gate("doctor", True,
                "kicad-cli %s, baseline from %s%s"
                % (env.version, meta.get("kicad_version", "?"), suffix),
                running_kicad=env.version,
                baseline_kicad=meta.get("kicad_version"),
                version_drift=bool(suffix))
    report.finish()
    return EXIT_OK
