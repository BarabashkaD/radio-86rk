"""Fixture checks for the harness. No framework, no dependencies.

Each check is a zero-argument callable that returns True or raises AssertionError
with a message naming what differed. `kicad-verify selftest` runs all of them.
"""
import os
import sys

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
    assert report_mod.drift_suffix("unknown", "10.0.4") == "", "unparsable baseline version must not warn"
    assert report_mod.drift_suffix("10.0.4", "") == "", "unparsable running version must not warn"
    suffix = report_mod.drift_suffix("10.0.4", "11.0.1")
    assert "VERSION-DRIFT" in suffix, repr(suffix)
    assert "baseline=10.0.4" in suffix and "running=11.0.1" in suffix, repr(suffix)
    assert "changelog" in suffix, "the warning must tell the reader what to do"
    return True


@check("json mode replaces verdict lines with one document")
def _json_mode():
    import io
    import json as json_mod

    # Test JSON mode: no verdict lines, proper document output
    buf = io.StringIO()
    held, sys.stdout = sys.stdout, buf
    try:
        rep = report_mod.Report(json_mode=True)
        rep.gate("gerber", True, "22 files identical", files=22)
        rep.info("rules", "ERC 413 (0 errors)")
        rep.warn("baseline captured with a different major version")
        rep.finish()
    finally:
        sys.stdout = held
    raw = buf.getvalue()
    assert "PASS  gerber" not in raw, "json mode must not emit verdict lines: %r" % raw
    doc = json_mod.loads(raw)
    statuses = [g["status"] for g in doc["gates"]]
    assert statuses == ["PASS", "INFO"], "INFO must be a distinct third status: %r" % statuses
    assert doc["gates"][0]["files"] == 22, "extra fields must reach the document: %r" % doc
    assert len(doc["warnings"]) == 1, "warnings must reach the document: %r" % doc

    # Test non-JSON mode: verdict lines SHOULD be present
    buf = io.StringIO()
    held, sys.stdout = sys.stdout, buf
    try:
        rep = report_mod.Report(json_mode=False)
        rep.gate("gerber", True, "22 files identical")
        rep.finish()
    finally:
        sys.stdout = held
    raw = buf.getvalue()
    assert "PASS  gerber" in raw, "non-json mode must emit verdict lines: %r" % raw
    assert raw.startswith("PASS  gerber"), "verdict line must be first output: %r" % raw

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
