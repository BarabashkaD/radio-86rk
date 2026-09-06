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


from . import report as report_mod


@check("verdict line format is exactly six and nine columns")
def _verdict_format():
    line = report_mod.verdict_line("PASS", "gerber", "22 files identical")
    assert line == "PASS  gerber   22 files identical", repr(line)
    line = report_mod.verdict_line("FAIL", "netlist", "3 nets differ")
    assert line == "FAIL  netlist  3 nets differ", repr(line)
    return True


@check("noise filter drops the two known sources and nothing else")
def _noise_filter():
    noisy = ("Fontconfig warning: line 5: unknown element\n"
             "Error retrieving source file attributes: NSCocoaErrorDomain Code=260\n"
             "error: real problem here\n")
    kept = report_mod.scrub(noisy)
    assert kept == "error: real problem here\n", repr(kept)
    assert report_mod.scrub(noisy, verbose=True) == noisy, "verbose must keep everything"
    return True


@check("version drift fires on major only")
def _drift():
    assert report_mod.drift_suffix("10.0.4", "10.0.5") == "", "patch drift must be silent"
    assert report_mod.drift_suffix("10.0.4", "10.9.9") == "", "minor drift must be silent"
    suffix = report_mod.drift_suffix("10.0.4", "11.0.1")
    assert "VERSION-DRIFT" in suffix, repr(suffix)
    assert "baseline=10.0.4" in suffix and "running=11.0.1" in suffix, repr(suffix)
    assert "changelog" in suffix, "the warning must tell the reader what to do"
    return True


def run(report):
    """Run every check. Returns True if all passed."""
    failed = []
    for name, fn in CHECKS:
        try:
            fn()
            report.progress("selftest", "ok   %s" % name)
        except Exception as exc:
            failed.append((name, "%s: %s" % (type(exc).__name__, exc)))
            report.progress("selftest", "FAIL %s" % name)
            report.detail("%s: %s" % (type(exc).__name__, exc))
    report.gate("selftest", not failed,
                "%d checks passed" % len(CHECKS) if not failed
                else "%d of %d checks failed" % (len(failed), len(CHECKS)))
    return not failed
