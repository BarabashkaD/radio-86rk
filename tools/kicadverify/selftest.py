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


@check("violations are read from both the ERC and DRC document shapes")
def _rules_shapes():
    from . import rules as rules_mod
    erc = {"sheets": [{"violations": [{"type": "pin_not_connected", "severity": "warning"}]},
                      {"violations": [{"type": "pin_not_connected", "severity": "warning"},
                                      {"type": "label_dangling", "severity": "error"}]}]}
    drc = {"violations": [{"type": "starved_thermal", "severity": "error"}],
           "unconnected_items": [{}, {}],
           "schematic_parity": []}

    erc_summary = rules_mod.summarise(erc)
    assert erc_summary["total"] == 3, erc_summary
    assert erc_summary["errors"] == 1 and erc_summary["warnings"] == 2, erc_summary
    assert erc_summary["by_type"][0] == ("pin_not_connected", 2), erc_summary["by_type"]

    drc_summary = rules_mod.summarise(drc)
    assert drc_summary["total"] == 1 and drc_summary["errors"] == 1, drc_summary
    assert drc_summary["unconnected"] == 2 and drc_summary["parity"] == 0, drc_summary
    return True


@check("meta.json records what a later capture needs to reproduce this one")
def _meta_fields():
    from . import baseline as baseline_mod
    meta = baseline_mod.build_meta("10.0.4", "abc1234", "KiCad/Board.kicad_pcb", ["strict"])
    for field in ("tool", "format", "kicad_version", "captured", "commit", "project", "modes"):
        assert field in meta, "meta.json is missing %s: %r" % (field, meta)
    assert meta["kicad_version"] == "10.0.4", meta
    assert meta["commit"] == "abc1234", meta
    assert meta["modes"] == ["strict"], meta
    assert meta["captured"].endswith("Z"), "capture time must be UTC: %r" % meta["captured"]
    return True


@check("exit code precedence: environment beats failure beats pass")
def _exit_precedence():
    from . import __main__ as main_mod
    assert main_mod.combine(["pass", "pass", "pass"]) == 0
    assert main_mod.combine(["pass", "fail", "pass"]) == 1
    assert main_mod.combine(["fail", "env", "pass"]) == 2, \
        "not having run is a more important fact than having failed"
    assert main_mod.combine(["env"]) == 2
    assert main_mod.combine([]) == 0
    return True


@check("an unexpected exception maps to exit 2, not exit 1")
def _unexpected_exception_guard():
    """An OSError from a full disk, a malformed report, anything not raised as
    EnvError must never surface as exit 1 -- CPython's default for an uncaught
    exception -- because 1 means 'the board changed' and nothing was actually
    checked. Constructed directly against _gate rather than by breaking a real
    module, so this stays fast and deterministic."""
    import io

    from . import __main__ as main_mod
    from . import discover as discover_mod
    from .report import Report

    class DummyEnv(object):
        pass

    class FakeArgs(object):
        project = None
        baseline_dir = None

    def boom(env):
        raise ValueError("disk full")

    original_build = discover_mod.build
    discover_mod.build = lambda args: DummyEnv()
    report = Report()
    buf = io.StringIO()
    held, sys.stderr = sys.stderr, buf
    try:
        code = main_mod._gate(FakeArgs(), report, boom)
    finally:
        sys.stderr = held
        discover_mod.build = original_build

    assert code == main_mod.EXIT_ENV, \
        "an unexpected exception must map to exit 2, not %r" % code
    assert not report.failed, "an environment problem is not a gate failure"
    joined = " ".join(report.errors)
    assert "ValueError" in joined and "disk full" in joined, report.errors
    assert "could not be completed" in joined, report.errors
    return True


@check("a gate that could not run inside `all` is recorded as INFO, not FAIL")
def _incomplete_gate_is_info():
    """`all`'s combined line already says INFO/incomplete when a gate could not run,
    and the exit code already says 2 -- but the per-gate entry in report.gates is a
    separate fact, and an agent that reads gates[].status directly (a plausible
    pattern, since the combined line is the only place that names incompleteness)
    must not see FAIL there: FAIL claims something was checked and found wrong, when
    nothing was checked at all. Exercises _run_one_gate directly -- the seam _all was
    split at for exactly this purpose -- rather than the exit code alone, because the
    exit code was already correct while this status string was wrong."""
    import io

    from . import __main__ as main_mod
    from .discover import EnvError
    from .report import Report

    def boom():
        raise EnvError("no netlist baseline")

    report = Report()
    out_buf, err_buf = io.StringIO(), io.StringIO()
    held_out, held_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out_buf, err_buf
    try:
        outcome = main_mod._run_one_gate(report, "netlist", boom)
    finally:
        sys.stdout, sys.stderr = held_out, held_err
    assert outcome == "env", outcome

    entry = report.gates[-1]
    assert entry["gate"] == "netlist", entry
    assert entry["status"] == "INFO", \
        "a gate that could not run must be recorded as INFO, not FAIL: %r" % entry
    assert not report.failed, \
        "a could-not-run gate must not mark the report failed: %r" % report.gates
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
