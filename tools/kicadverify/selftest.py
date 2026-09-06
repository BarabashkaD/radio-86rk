"""Fixture checks for the harness. No framework, no dependencies.

Each check is a zero-argument callable that returns True or raises AssertionError
with a message naming what differed. `kicad-verify selftest` runs all of them.
"""
import os

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures")

CHECKS = []


def check(name):
    """Register a check under a human-readable name."""
    def register(fn):
        CHECKS.append((name, fn))
        return fn
    return register


@check("selftest harness runs")
def _harness_runs():
    assert os.path.isdir(FIXTURES), "fixtures directory missing: %s" % FIXTURES
    return True


def run(report):
    """Run every check. Returns True if all passed."""
    failed = []
    for name, fn in CHECKS:
        try:
            fn()
            report.progress("selftest", "ok   %s" % name)
        except AssertionError as exc:
            failed.append((name, str(exc)))
            report.progress("selftest", "FAIL %s" % name)
            report.detail(str(exc))
    report.gate("selftest", not failed,
                "%d checks passed" % len(CHECKS) if not failed
                else "%d of %d checks failed" % (len(failed), len(CHECKS)))
    return not failed
