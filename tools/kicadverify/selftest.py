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
from . import canon as canon_mod


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


def _fixture(name):
    return canon_mod.canon(os.path.join(FIXTURES, name))


@check("reordering and aperture renumbering canonicalise identically")
def _reorder_is_identical():
    a, b = _fixture("plain.gbr"), _fixture("reordered.gbr")
    assert a == b, "same geometry compared different:\n  %r\n  %r" % (a, b)
    return True


@check("a one-unit displacement canonicalises differently")
def _displacement_is_caught():
    a, b = _fixture("plain.gbr"), _fixture("moved.gbr")
    assert a != b, "a moved pad compared identical: %r" % (a,)
    return True


@check("region fills survive verbatim and in order")
def _region_verbatim():
    units = _fixture("region.gbr")
    assert len(units) == 1, "expected one region unit, got %r" % (units,)
    assert units[0] == ("REGION|C,0.100000|"
                        "X0Y0D02*|X1000000Y0D01*|X1000000Y1000000D01*|"
                        "X0Y1000000D01*|X0Y0D01*"), repr(units[0])
    return True


@check("region vertex order is significant")
def _region_order_matters():
    a, b = _fixture("region.gbr"), _fixture("region-reversed.gbr")
    assert a != b, "a reversed polygon compared identical -- a line sort would do this"
    return True


from . import discover as discover_mod


@check("kicad-cli discovery order: KICAD_CLI, then PATH, then known locations")
def _cli_order():
    order = discover_mod.cli_candidates("darwin", {"KICAD_CLI": "/custom/kicad-cli"})
    assert order[0] == "/custom/kicad-cli", repr(order)
    assert "kicad-cli" in order, "PATH lookup must be tried"
    assert any("KiCad.app" in c for c in order), "macOS known location missing: %r" % (order,)

    linux = discover_mod.cli_candidates("linux", {})
    assert linux[0] == "kicad-cli", repr(linux)
    assert any("flatpak" in c for c in linux), "flatpak wrapper missing: %r" % (linux,)
    return True


@check("Windows candidates are sorted by version, not lexically, and use backslashes")
def _windows_candidates():
    win = discover_mod.cli_candidates(
        "win32", {}, listdir=lambda base: ["8.0", "9.0", "10.0"])
    windows_only = [c for c in win if c != "kicad-cli"]
    assert windows_only, "no Windows known-location candidates produced: %r" % (win,)

    # Checked first and independently of separator style, so a broken join alone
    # cannot mask this assertion behind a lookup failure.
    assert all("/" not in c for c in windows_only), (
        "Windows candidates must use the declared platform's separator, not the "
        "host's: %r" % (win,))

    index_10 = win.index(next(c for c in windows_only if "10.0" in c))
    index_9 = win.index(next(c for c in windows_only if "9.0" in c))
    assert index_10 < index_9, (
        "a string sort puts '9.0' before '10.0' -- version directories must be "
        "sorted numerically, not lexically: %r" % (win,))
    return True


@check("two boards in a repo is an error that names both")
def _ambiguous_project():
    try:
        discover_mod.pick_project(["/r/a.kicad_pcb", "/r/b.kicad_pcb"])
    except discover_mod.EnvError as exc:
        assert "a.kicad_pcb" in str(exc) and "b.kicad_pcb" in str(exc), str(exc)
        return True
    raise AssertionError("two candidate boards must not be resolved silently")


@check("no board is an error that says how to fix it")
def _no_project():
    try:
        discover_mod.pick_project([])
    except discover_mod.EnvError as exc:
        assert "--project" in str(exc), "the error must name the flag that fixes it: %s" % exc
        return True
    raise AssertionError("an empty repository must not resolve to a project")


@check("KiCad older than 10 is fatal, not a warning")
def _version_floor():
    assert discover_mod.check_floor("10.0.4") is None
    assert discover_mod.check_floor("11.0.0") is None
    message = discover_mod.check_floor("9.0.1")
    assert message and "9.0.1" in message and "10" in message, repr(message)
    return True


@check("strict mode appends X2 attributes in byte order, geometry mode drops them")
def _strict_keeps_attributes():
    from . import gerber as gerber_mod
    raw = ("%FSLAX46Y46*%\n"
           "%TO.N,GND*%\n"
           "%TO.C,R1*%\n"
           "%ADD10C,1.000000*%\n"
           "D10*\n"
           "X0Y0D03*\n"
           "M02*\n").splitlines(True)
    strict = gerber_mod.normalise_lines(raw, "strict")
    geometry = gerber_mod.normalise_lines(raw, "geometry")
    assert "%TO.C,R1*%" in strict and "%TO.N,GND*%" in strict, strict
    assert strict.index("%TO.C,R1*%") < strict.index("%TO.N,GND*%"), \
        "attributes must sort in byte order, not locale order: %r" % (strict,)
    assert not any(line.startswith("%TO.") for line in geometry), geometry
    assert any(line.startswith("FLASH|") for line in geometry), \
        "geometry mode must keep the geometry: %r" % (geometry,)
    return True


@check("netlist extraction keeps connectivity and drops refreshable metadata")
def _netlist_extract():
    from . import netlist as netlist_mod
    raw = ("(export (version \"E\")\n"
           "\t(components\n"
           "\t\t(comp (ref \"R1\") (datasheet \"http://example.com/changed\")))\n"
           "\t(nets\n"
           "\t\t(net (code \"1\") (name \"GND\")\n"
           "\t\t\t(node (ref \"R1\") (pin \"1\")\n"
           "\t\t\t\t(pintype \"passive\")))))\n"
           ).splitlines(True)
    got = netlist_mod.extract(raw)
    text = "".join(got)
    assert "(nets" in text, "the nets section must be kept: %r" % text
    assert "datasheet" not in text, "everything before (nets must be dropped: %r" % text
    assert "pintype" not in text, "pintype is metadata, not connectivity: %r" % text
    assert "R1" in text and "GND" in text, "the actual connectivity must survive: %r" % text
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
