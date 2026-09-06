# Verification Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace five shell scripts with one stdlib-only Python harness that proves a KiCad project's copper, connectivity and rule counts are unchanged, on macOS, Linux and Windows, for a human or an agent.

**Architecture:** A launcher script (`tools/kicad-verify.py`) in front of a package (`tools/kicadverify/`). The launcher exists so the invocation is one instruction on every platform with no install step. The package splits into discovery, reporting, three gates, the canonicaliser, and a fixture-driven selftest. Nothing imports `pcbnew`; the only external dependency is `kicad-cli`.

**Tech Stack:** Python 3 standard library only (`argparse`, `json`, `re`, `subprocess`, `shutil`, `pathlib`, `os`, `sys`, `collections`, `datetime`). `kicad-cli` 10 or newer. No package manager, no test framework, no configuration file.

**Spec:** `docs/superpowers/specs/2026-09-06-workstream-split-and-verification-harness-design.md`, Part 2. Read it from the archive tag while executing: `git show archive/kicad10-3d-2026-09-06:docs/superpowers/specs/2026-09-06-workstream-split-and-verification-harness-design.md`

---

## Global Constraints

Every task's requirements implicitly include this section.

- **Branch:** all work happens on `harness`, branched from `master`. Master has no `tools/` and no `verify/` — everything here is new. Nothing is deleted.
- **Source material** is the archive tag, not the working tree: `git show archive/kicad10-3d-2026-09-06:tools/<file>`. The five files being ported are `kicad-env.sh`, `gerber_canon.py`, `gerber-gate.sh`, `netlist-gate.sh`, `rules-report.sh`.
- **Standard library only.** No third-party import in shipped code, ever. No `pcbnew`.
- **Python floor is 3.8.** No `match` statements, no PEP 604 (`int | None`) annotations evaluated at runtime, no `tomllib`, no `str.removeprefix`. macOS system Python is 3.9 and KiCad bundles 3.9; the floor must clear them.
- **Repository-agnostic.** No project name, no board filename, and no absolute path to this repository appears anywhere in `tools/`. Grep for `Radio-86RK` and `radio-86rk` before every commit; both must return nothing under `tools/`.
- **Exit codes:** `0` pass · `1` a gate failed · `2` environment or usage problem. `2` takes precedence over `1`.
- **Streams:** progress and detail to **stderr**; one verdict line per gate to **stdout**; `--json` replaces the verdict lines on stdout with one JSON document.
- **Version policy:** major version only. `major < 10` is a fatal environment error (exit 2). A major that differs from the baseline's major is a **warning** carried on the verdict line and in the JSON — never its own exit code. Same major, any patch, is silent.
- **Baseline location:** `verify/baseline/` by default, overridable with `--baseline-dir`. The `strict` gerber baseline, `netlist.nets` and `meta.json` are committed. The `geometry` baseline is **not** committed.
- **Scratch files** go in `$SCRATCH`, never in the repository and never in `/tmp`. Set it once per session:

  ```bash
  SCRATCH=/private/tmp/claude-501/-Users-dveremeev-projects-radio-86rk/6d6b37d9-b675-42b4-a2cd-2d530fc093d5/scratchpad
  mkdir -p "$SCRATCH"
  ```

  The harness's own working files go in `.build/verify/`, which is derived and must be in `.gitignore` before the first commit that creates it.

### Running Python in this sandbox

A hook in this environment blocks `python3` and `pip` invocations, and blocks any Bash command whose text contains those strings. Resolve an interpreter once per session and call it by path:

```bash
VENV_SCRIPT="/Users/dveremeev/.claude/plugins/cache/dv-claude-dev-market/python-venv-manager/1.2.0/skills/python-venv-manager/scripts/ensure_venv.sh"
PY=$(bash "$VENV_SCRIPT" radio-86rk-harness)
"$PY" tools/kicad-verify.py selftest
```

The venv already exists at `/Users/dveremeev/.claude/venvs/radio-86rk-harness/bin/python` (3.14.6) and holds no packages — it is an interpreter, not a dependency set. **This is a sandbox constraint only.** Every user-facing instruction, README line and error message must say `python3 tools/kicad-verify.py`, because that is what a stranger will type.

Because the sandbox interpreter is 3.14 and the floor is 3.8, syntax that only 3.9+ accepts will not be caught by running the tests. Read for it.

### kicad-cli in this sandbox

```
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli      version 10.0.4
```

`kicad-cli version` prints exactly `10.0.4` and exits 0.

### Verdict line format

Exactly this, `%-6s%-9s%s` on the first three fields:

```
PASS  gerber   22 files identical
FAIL  gerber   3 files differ: F_Cu.gtl, B_Cu.gbl, Edge_Cuts.gm1
INFO  rules    ERC 413 (0 errors)  DRC 212 (5 errors)
```

Drift appends to the summary, in one bracket:

```
FAIL  gerber   3 files differ  [VERSION-DRIFT baseline=10.0.4 running=11.0.1 differences may be emitter changes — check the KiCad changelog]
```

---

## File Structure

| Path | Responsibility |
|---|---|
| `tools/kicad-verify.py` | Launcher. Puts `tools/` on `sys.path`, calls `kicadverify.__main__.main()`, exits with its code. Nothing else. |
| `tools/kicadverify/__init__.py` | Empty except `__version__`. |
| `tools/kicadverify/__main__.py` | argparse, subcommand dispatch, the only place exit codes are decided. |
| `tools/kicadverify/report.py` | Verdict lines, progress, `--json`, noise filtering. No knowledge of gates. |
| `tools/kicadverify/canon.py` | The gerber canonicaliser. Pure: text in, canonical units out. No I/O beyond opening a file. |
| `tools/kicadverify/discover.py` | Locate `kicad-cli`, the repo root and the project; read the KiCad version. Raises `EnvError`. |
| `tools/kicadverify/gerber.py` | Export, normalise, compare gerbers and drill. |
| `tools/kicadverify/netlist.py` | Export the netlist, extract connectivity, compare. |
| `tools/kicadverify/rules.py` | ERC and DRC counts by type. |
| `tools/kicadverify/baseline.py` | Capture, `meta.json`, drift detection. **Not in the spec's file list** — added because capture and drift are shared by three commands and belong to neither the gerber gate nor the netlist gate. |
| `tools/kicadverify/selftest.py` | Fixture checks. The shipped test suite and this plan's TDD loop. |
| `tools/fixtures/*.gbr` | Five tiny gerbers, hand-written, a few lines each. |
| `tools/README.md` | Written for a stranger. |

`canon.py` is separate from `gerber.py` because it defines what "same copper" means; it should be readable on its own without a CLI wrapped round it.

### A note on `selftest` as the TDD loop

The spec gives `selftest` three canonicaliser properties and forbids a test framework. This plan extends `selftest` to also cover version parsing, verdict formatting and exit-code precedence — pure functions, fixture-driven, no framework, still about a second to run. The reason is that it makes the shipped self-check verify the whole tool rather than one module, and it gives every task below a real red-green cycle without adding a dependency the spec rules out. `selftest` remains a single subcommand with no arguments.

---

## Task 1: Launcher, CLI skeleton and exit codes

**Files:**
- Create: `tools/kicad-verify.py`
- Create: `tools/kicadverify/__init__.py`
- Create: `tools/kicadverify/__main__.py`
- Create: `tools/kicadverify/selftest.py`
- Create: `.gitignore`

Master has no `.gitignore` at all. The harness writes derived files to `.build/verify/`, so one has to exist before the first run, or the first `git status` after Task 5 will offer to commit twenty megabytes of exported gerbers. Its whole content:

```gitignore
# Derived output from tools/kicad-verify.py
.build/
```

**Interfaces:**
- Consumes: nothing.
- Produces: `kicadverify.selftest.run(report) -> bool`, `kicadverify.selftest.CHECKS` (a list of `(name, callable)` where the callable returns `True` or raises `AssertionError`); `kicadverify.__main__.main(argv=None) -> int`.

- [ ] **Step 1: Write the failing test**

Create `tools/kicadverify/selftest.py` with the registry and one check that is deliberately trivial, so the harness itself is proven before anything real depends on it:

```python
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
```

- [ ] **Step 2: Run it to verify it fails**

```bash
"$PY" tools/kicad-verify.py selftest
```

Expected: FAIL — `tools/kicad-verify.py` does not exist yet.

- [ ] **Step 3: Write the launcher and the CLI**

`tools/kicad-verify.py` — this file is deliberately minimal and must stay so:

```python
"""Launcher for the KiCad verification harness.

Run as:  python3 tools/kicad-verify.py <command>
On Windows:  py tools\\kicad-verify.py <command>

There is no install step. This file exists so the invocation is the same
instruction on every platform: no shebang, no PATH entry, no PYTHONPATH.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kicadverify.__main__ import main  # noqa: E402  (path must be set first)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

`tools/kicadverify/__init__.py`:

```python
"""A stdlib-only harness that proves a KiCad project's copper, connectivity and
rule counts are unchanged. See tools/README.md."""

__version__ = "1.0.0"
```

`tools/kicadverify/__main__.py` — only `selftest` is wired up in this task; the rest are placeholders that exit 2 so an early caller gets an honest "not implemented" rather than a traceback:

```python
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
```

- [ ] **Step 4: Write the minimum of `report.py` this task needs**

Task 2 builds `report.py` properly. This task needs four methods to exist so `selftest` can run:

```python
"""Progress, verdicts and machine-readable output. Knows nothing about gates."""
import sys


class Report(object):
    def __init__(self, json_mode=False, verbose=False):
        self.json_mode = json_mode
        self.verbose = verbose
        self.gates = []

    def progress(self, gate, message):
        sys.stderr.write("[%s] %s\n" % (gate, message))

    def detail(self, text):
        sys.stderr.write("        %s\n" % text)

    def error(self, message):
        sys.stderr.write("error: %s\n" % message)

    def gate(self, name, ok, summary, **extra):
        self.gates.append({"gate": name, "pass": bool(ok), "summary": summary})
        sys.stdout.write("%-6s%-9s%s\n" % ("PASS" if ok else "FAIL", name, summary))

    def finish(self):
        pass
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
"$PY" tools/kicad-verify.py selftest
```

Expected on stdout: `FAIL  selftest 1 of 1 checks failed` — the fixtures directory does not exist. Then:

```bash
mkdir -p tools/fixtures && touch tools/fixtures/.gitkeep
"$PY" tools/kicad-verify.py selftest
```

Expected on stdout: `PASS  selftest 1 checks passed`, exit 0.

- [ ] **Step 6: Verify the exit codes and the usage error**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"        # exit=0
"$PY" tools/kicad-verify.py gerber;   echo "exit=$?"        # exit=2, "not implemented yet"
"$PY" tools/kicad-verify.py nonsense; echo "exit=$?"        # exit=2, argparse usage message
"$PY" tools/kicad-verify.py --help;   echo "exit=$?"        # exit=0
```

argparse exits 2 on a bad argument by default, which is already the code this plan wants. Confirm it rather than overriding it.

- [ ] **Step 7: Commit**

```bash
git add .gitignore tools/kicad-verify.py tools/kicadverify/ tools/fixtures/.gitkeep
git commit -m "Add the harness launcher, CLI skeleton and selftest registry"
```

---

## Task 2: The reporting contract

**Files:**
- Modify: `tools/kicadverify/report.py`
- Modify: `tools/kicadverify/selftest.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Report(json_mode=False, verbose=False)`
  - `Report.progress(gate, message)` → stderr
  - `Report.detail(text)` → stderr, indented
  - `Report.warn(message)` → stderr, collected into JSON
  - `Report.error(message)` → stderr
  - `Report.gate(name, ok, summary, **extra)` → one stdout verdict line; `**extra` becomes JSON fields
  - `Report.info(name, summary, **extra)` → an `INFO` verdict, neither pass nor fail
  - `Report.finish()` → in `--json` mode writes the document to stdout
  - `Report.failed` → property, `True` if any `gate()` call had `ok=False`
  - `report.scrub(text, verbose=False) -> str` — module-level function, drops known noise lines
  - `report.drift_suffix(baseline_version, running_version) -> str` — `""` when the majors match

- [ ] **Step 1: Write the failing tests**

Append to `tools/kicadverify/selftest.py`:

```python
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"
```

Expected: `FAIL  selftest 3 of 4 checks failed`, exit 1, with `AttributeError`-shaped messages naming `verdict_line`, `scrub`, `drift_suffix`.

Note: a missing attribute raises `AttributeError`, not `AssertionError`, so `run()` would not catch it. Widen the except clause in `selftest.run` to `except (AssertionError, Exception)` — no: catch `Exception` and record `type(exc).__name__ + ": " + str(exc)`. A check that explodes is a failed check, not a crashed run.

- [ ] **Step 3: Write the implementation**

Replace `tools/kicadverify/report.py`:

```python
"""Progress, verdicts and machine-readable output.

Three audiences, three streams. A human reads stderr while it runs and the verdict
line at the end. An agent reads the exit code, or --json when it needs detail. The
split matters because an agent that cannot tell "the board changed" from "I could
not run the check" will report a false regression.

Knows nothing about gates: it formats what it is given.
"""
import json
import re
import sys

# Two known noise sources, both harmless, both matched exactly so a real error on
# stderr still reaches the reader:
#   * Homebrew's fontconfig warns roughly forty times per kicad-cli call
#   * on macOS kicad-cli stats its output file before creating it, which logs an
#     NSCocoaErrorDomain 260 "no such file" for every export
NOISE = (
    re.compile(r"^Fontconfig warning"),
    re.compile(r"Error retrieving source file attributes"),
)

DRIFT_TEMPLATE = ("  [VERSION-DRIFT baseline=%s running=%s "
                  "differences may be emitter changes \u2014 check the KiCad changelog]")


def verdict_line(status, gate, summary):
    """The one stable line per gate on stdout. Columns are fixed so a human can
    scan them and a script can cut them."""
    return "%-6s%-9s%s" % (status, gate, summary)


def scrub(text, verbose=False):
    """Drop known-noise lines from captured tool output. --verbose keeps everything,
    so the filter is never the reason something was missed."""
    if verbose:
        return text
    kept = [line for line in text.splitlines(True)
            if not any(p.search(line) for p in NOISE)]
    return "".join(kept)


def major(version):
    """Leading integer of a version string. '10.0.4' -> 10. Returns None if unparsable."""
    match = re.match(r"\s*(\d+)", version or "")
    return int(match.group(1)) if match else None


def drift_suffix(baseline_version, running_version):
    """The yellow flag. Fires on major version only: warning on 10.0.4 against 10.0.5
    would be noise, and a flag that fires on every patch release is one people learn
    to ignore. Emitter changes arrive with major releases."""
    a, b = major(baseline_version), major(running_version)
    if a is None or b is None or a == b:
        return ""
    return DRIFT_TEMPLATE % (baseline_version, running_version)


class Report(object):
    def __init__(self, json_mode=False, verbose=False):
        self.json_mode = json_mode
        self.verbose = verbose
        self.gates = []
        self.warnings = []
        self.errors = []

    # -- stderr: for the human watching it run -------------------------------
    def progress(self, gate, message):
        sys.stderr.write("[%s] %s\n" % (gate, message))

    def detail(self, text):
        for line in str(text).splitlines():
            sys.stderr.write("        %s\n" % line)

    def warn(self, message):
        self.warnings.append(message)
        sys.stderr.write("warning: %s\n" % message)

    def error(self, message):
        self.errors.append(message)
        sys.stderr.write("error: %s\n" % message)

    # -- stdout: one stable line per gate ------------------------------------
    def _record(self, status, name, summary, extra):
        entry = {"gate": name, "status": status, "summary": summary}
        entry.update(extra)
        self.gates.append(entry)
        if not self.json_mode:
            sys.stdout.write(verdict_line(status, name, summary) + "\n")

    def gate(self, name, ok, summary, **extra):
        self._record("PASS" if ok else "FAIL", name, summary, extra)

    def info(self, name, summary, **extra):
        """A gate that reports rather than judges. `rules` has no baseline to compare
        against, so it states the counts and leaves the verdict to the reader."""
        self._record("INFO", name, summary, extra)

    @property
    def failed(self):
        return any(g["status"] == "FAIL" for g in self.gates)

    def finish(self):
        if self.json_mode:
            json.dump({"gates": self.gates,
                       "warnings": self.warnings,
                       "errors": self.errors},
                      sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
```

- [ ] **Step 4: Widen the exception handling in `selftest.run`**

```python
        except Exception as exc:
            failed.append((name, "%s: %s" % (type(exc).__name__, exc)))
```

- [ ] **Step 5: Run to verify they pass**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"
```

Expected: `PASS  selftest 4 checks passed`, exit 0.

- [ ] **Step 6: Verify `--json`**

```bash
"$PY" tools/kicad-verify.py selftest --json
```

Expected: a JSON document on stdout with a `gates` array of one entry whose `status` is `PASS`, and no verdict line.

- [ ] **Step 7: Commit**

```bash
git add tools/kicadverify/report.py tools/kicadverify/selftest.py
git commit -m "Add the reporting contract: verdict lines, JSON, noise filter, drift warning"
```

---

## Task 3: The canonicaliser and its fixtures

This is the heart of the harness. Everything else is plumbing; this module defines what "the copper did not move" means.

**Files:**
- Create: `tools/kicadverify/canon.py`
- Create: `tools/fixtures/plain.gbr`
- Create: `tools/fixtures/reordered.gbr`
- Create: `tools/fixtures/moved.gbr`
- Create: `tools/fixtures/region.gbr`
- Create: `tools/fixtures/region-reversed.gbr`
- Modify: `tools/kicadverify/selftest.py`

**Interfaces:**
- Consumes: `selftest.check`, `selftest.FIXTURES`.
- Produces: `canon.canon_lines(lines) -> list[str]` (sorted canonical units) and `canon.canon(path) -> list[str]` (opens the file, delegates). `canon_lines` takes any iterable of strings so fixtures can be fed as text in tests.

- [ ] **Step 1: Write the fixtures**

Five files, hand-written, a few lines each. They are gerber, so they must stay syntactically plausible, but they need no header beyond format and units.

`tools/fixtures/plain.gbr` — one trace and one flashed pad:

```
%FSLAX46Y46*%
%MOMM*%
%ADD10C,1.000000*%
%ADD11R,2.000000X2.000000*%
G01*
D10*
X10000000Y10000000D02*
X20000000Y10000000D01*
D11*
X30000000Y30000000D03*
M02*
```

`tools/fixtures/reordered.gbr` — the same geometry, commands in a different order, aperture D-codes renumbered. This is what KiCad emits after it rewrites a board:

```
%FSLAX46Y46*%
%MOMM*%
%ADD20R,2.000000X2.000000*%
%ADD21C,1.000000*%
G01*
D20*
X30000000Y30000000D03*
D21*
X10000000Y10000000D02*
X20000000Y10000000D01*
M02*
```

`tools/fixtures/moved.gbr` — `plain.gbr` with the trace endpoint moved by one unit of the 4.6 format, which is 1 nm at X46; the point is that the smallest representable move is caught:

```
%FSLAX46Y46*%
%MOMM*%
%ADD10C,1.000000*%
%ADD11R,2.000000X2.000000*%
G01*
D10*
X10000000Y10000000D02*
X20000001Y10000000D01*
D11*
X30000000Y30000000D03*
M02*
```

`tools/fixtures/region.gbr` — a G36/G37 filled square:

```
%FSLAX46Y46*%
%MOMM*%
%ADD10C,0.100000*%
D10*
G36*
X0Y0D02*
X1000000Y0D01*
X1000000Y1000000D01*
X0Y1000000D01*
X0Y0D01*
G37*
M02*
```

`tools/fixtures/region-reversed.gbr` — the same vertices, traversed the other way. A naive line sort would call this identical to `region.gbr`; it is a different polygon:

```
%FSLAX46Y46*%
%MOMM*%
%ADD10C,0.100000*%
D10*
G36*
X0Y0D02*
X0Y1000000D01*
X1000000Y1000000D01*
X1000000Y0D01*
X0Y0D01*
G37*
M02*
```

- [ ] **Step 2: Write the failing tests**

Append to `tools/kicadverify/selftest.py`:

```python
from . import canon as canon_mod


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
```

- [ ] **Step 3: Run to verify they fail**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"
```

Expected: `FAIL  selftest 4 of 8 checks failed`, exit 1, each naming `canon`.

- [ ] **Step 4: Write the implementation**

Port `gerber_canon.py` from the archive. Recover the original first so the port is a port and not a rewrite from memory:

```bash
git show archive/kicad10-3d-2026-09-06:tools/gerber_canon.py > $SCRATCH/gerber_canon.orig.py
```

The algorithm is unchanged. Two things differ: the input becomes an iterable of lines so fixtures can be fed as text, and the module-level `__main__` block goes away because the CLI now lives in `__main__.py`.

```python
"""Canonicalise a gerber file so reordering and aperture renumbering compare equal,
while any change to real geometry compares different.

Why this is needed: KiCad re-emits identical geometry in a different order and
renumbers aperture D-codes whenever it rewrites a board. Measured on the board this
harness was built for, a format upgrade changed 12 of 22 gerber files byte-wise while
moving nothing: the drill file stayed byte-identical, the aperture sets matched, and
every copper file held the same multiset of drawing commands. A byte diff fails on
every such rewrite, so a byte diff is useless as a gate.

A naive line sort is not safe either, because copper and silkscreen layers use G36/G37
region fills whose vertex order defines the polygon. Sorting the lines inside a fill
turns a square into a bowtie and reports it as unchanged.

Canonical form: the file is split into atomic drawing units --
  * a G36...G37 region block, kept verbatim and in order
  * a D02 move plus the D01/D03 operations that follow it
  * a bare D03 flash
each prefixed by the resolved aperture definition (not its D-code) and the current
interpolation mode. Units are then sorted, so order between units is irrelevant while
order within a unit is preserved.

Validated both ways: reports a KiCad format upgrade as unchanged, and detects a 1um
pad displacement in 5 of 22 files. tools/fixtures/ holds the minimal cases.
"""
import re

APERTURE_DEF = re.compile(r"^%ADD(\d+)([^*]*)\*%")
APERTURE_SEL = re.compile(r"^D(\d+)\*$")
GMODE = re.compile(r"^(G0[123])\*?$")
OPLINE = re.compile(r"D0([123])\*$")


def canon_lines(lines):
    """Canonical units for an iterable of gerber lines, sorted."""
    apertures, units = {}, []
    cur_ap, cur_g, unit = "none", "G01", None
    in_region, region = False, []

    for raw in lines:
        line = raw.rstrip("\n").rstrip("\r")
        if not line:
            continue

        m = APERTURE_DEF.match(line)
        if m:                                   # remember the shape, discard the D-code
            apertures[m.group(1)] = m.group(2)
            continue

        if line.startswith("G36"):
            if unit:
                units.append(unit)
                unit = None
            in_region, region = True, []
            continue
        if line.startswith("G37"):
            units.append("REGION|%s|%s" % (cur_ap, "|".join(region)))
            in_region = False
            continue
        if in_region:
            region.append(line)
            continue

        m = APERTURE_SEL.match(line)
        if m:                                   # aperture select: resolve to its shape
            if unit:
                units.append(unit)
                unit = None
            cur_ap = apertures.get(m.group(1), "D" + m.group(1))
            continue

        m = GMODE.match(line)
        if m:
            cur_g = m.group(1)
            continue

        m = OPLINE.search(line)
        if m:
            op = m.group(1)
            if op == "2":                       # move: starts a new unit
                if unit:
                    units.append(unit)
                unit = "DRAW|%s|%s|%s" % (cur_ap, cur_g, line)
            elif op == "1":                     # draw: extends the current unit
                if unit is None:
                    unit = "DRAW|%s|%s|" % (cur_ap, cur_g)
                unit += "||" + line
            else:                               # flash: atomic
                if unit:
                    units.append(unit)
                    unit = None
                units.append("FLASH|%s|%s" % (cur_ap, line))
            continue
        # everything else (format specs, attributes, M02) is metadata, not geometry

    if unit:
        units.append(unit)
    return sorted(units)


def canon(path):
    """Canonical units for a gerber file on disk."""
    with open(path, errors="replace") as handle:
        return canon_lines(handle)
```

- [ ] **Step 5: Run to verify they pass**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"
```

Expected: `PASS  selftest 8 checks passed`, exit 0.

- [ ] **Step 6: Verify the port is faithful, not merely plausible**

The port must produce exactly what the shell-era script produced. Run both against a real gerber from the archive:

```bash
git show archive/kicad10-3d-2026-09-06:verify/baseline/strict/Radio-86RK-F_Cu.gtl > $SCRATCH/expected-F_Cu.txt
mkdir -p $SCRATCH/gerbertest
git show archive/kicad10-3d-2026-09-06:gerber/Radio-86RK-F_Cu.gtl > $SCRATCH/gerbertest/F_Cu.gtl 2>/dev/null || \
  echo "no committed raw gerber; skip and rely on Task 10"
```

If the raw gerber is available, compare the canonical output against the head of the committed baseline (which is canonical output plus appended `%TO./%TA.` lines):

```bash
"$PY" -c "import sys; sys.path.insert(0,'tools'); from kicadverify.canon import canon; print('\n'.join(canon('$SCRATCH/gerbertest/F_Cu.gtl')))" > $SCRATCH/got-F_Cu.txt
head -n "$(wc -l < $SCRATCH/got-F_Cu.txt)" $SCRATCH/expected-F_Cu.txt | diff -u - $SCRATCH/got-F_Cu.txt && echo "canonicaliser is byte-faithful"
```

If the raw gerber is not in the archive, note it and let Task 10 carry the whole proof — it does so end-to-end and is the authoritative check either way.

- [ ] **Step 7: Commit**

```bash
git add tools/kicadverify/canon.py tools/fixtures/ tools/kicadverify/selftest.py
git rm --cached tools/fixtures/.gitkeep 2>/dev/null || true
git commit -m "Port the gerber canonicaliser with fixtures for its four properties"
```

---

## Task 4: Discovery and the `doctor` command

**Files:**
- Create: `tools/kicadverify/discover.py`
- Modify: `tools/kicadverify/__main__.py`
- Modify: `tools/kicadverify/selftest.py`

**Interfaces:**
- Consumes: `Report`, `report.major`.
- Produces:
  - `discover.EnvError(Exception)` — every environment failure; `__main__` turns it into exit 2
  - `discover.cli_candidates(platform, environ, listdir=os.listdir) -> list[str]` — pure, ordered, testable without a KiCad install
  - `discover.find_cli(...) -> str` — first candidate that runs
  - `discover.cli_version(cli) -> str` — runs `cli version`
  - `discover.find_repo_root(start) -> str`
  - `discover.find_project(root, explicit=None) -> (pcb_path, sch_path)`
  - `discover.Environment` — attributes `cli`, `version`, `repo_root`, `pcb`, `sch`, `baseline_dir`, `build_dir`
  - `discover.build(args) -> Environment`

- [ ] **Step 1: Write the failing tests**

The interesting logic is candidate ordering and project selection — both pure, both testable with no KiCad and no board. Append to `selftest.py`:

```python
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"
```

Expected: `FAIL  selftest 4 of 12 checks failed`, exit 1.

- [ ] **Step 3: Write the implementation**

```python
"""Locate kicad-cli, the repository and the project, on any of the three platforms.

The harness needs no pcbnew, which is what makes this tractable: KiCad's Python is
bundled inside the application on macOS and Windows but is a distribution package on
Linux, and there is no portable way to find it. kicad-cli is an executable, and an
executable can be found by looking.
"""
import glob
import os
import subprocess
import sys

MIN_MAJOR = 10


class EnvError(Exception):
    """Something the harness needs is missing or ambiguous. Always exit 2:
    'I could not run the check' is a different fact from 'the board changed'."""


def cli_candidates(platform, environ, listdir=os.listdir):
    """Ordered kicad-cli candidates. Pure, so it can be tested without a KiCad install.
    First an explicit override, then PATH, then per-OS known locations."""
    candidates = []
    if environ.get("KICAD_CLI"):
        candidates.append(environ["KICAD_CLI"])
    candidates.append("kicad-cli")

    if platform == "darwin":
        candidates.append("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
    elif platform.startswith("win"):
        for base in (r"C:\Program Files\KiCad", r"C:\Program Files (x86)\KiCad"):
            try:
                versions = sorted(listdir(base), reverse=True)   # highest version first
            except OSError:
                versions = []
            for version in versions:
                candidates.append(os.path.join(base, version, "bin", "kicad-cli.exe"))
    else:
        candidates.extend([
            "/usr/bin/kicad-cli",
            "/usr/local/bin/kicad-cli",
            "/var/lib/flatpak/exports/bin/org.kicad.KiCad",
            os.path.expanduser("~/.local/share/flatpak/exports/bin/org.kicad.KiCad"),
            "/snap/bin/kicad.kicad-cli",
        ])
    return candidates


def _runs(path):
    try:
        proc = subprocess.Popen([path, "version"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, _ = proc.communicate()
        return proc.returncode == 0 and out.decode("utf-8", "replace").strip() or None
    except OSError:
        return None


def find_cli(platform=None, environ=None):
    """First candidate that actually runs. On failure the error names every path tried,
    because 'kicad-cli not found' with no list is a dead end for whoever reads it."""
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    tried = cli_candidates(platform, environ)
    for candidate in tried:
        version = _runs(candidate)
        if version:
            return candidate, version
    raise EnvError(
        "kicad-cli not found. Set KICAD_CLI=/path/to/kicad-cli or install KiCad %d.\n"
        "Tried:\n  %s" % (MIN_MAJOR, "\n  ".join(tried)))


def run_cli(env, report, args, what, allow_failure=False):
    """kicad-cli with its noise filtered and its real errors kept. Lives here rather
    than in a gate because all three gates need it.

    allow_failure is for the checkers: kicad-cli exits non-zero when ERC or DRC finds
    violations, which is a result, not a failure to run.
    """
    from .report import scrub
    proc = subprocess.Popen([env.cli] + args,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _, err = proc.communicate()
    text = scrub(err.decode("utf-8", "replace"), report.verbose)
    if text.strip():
        report.detail(text.rstrip())
    if proc.returncode != 0 and not allow_failure:
        raise EnvError("kicad-cli %s failed with exit %d" % (what, proc.returncode))


def check_floor(version):
    """None if the version is new enough, otherwise the message to fail with."""
    from .report import major
    found = major(version)
    if found is None:
        return "could not read a version number from %r" % version
    if found < MIN_MAJOR:
        return ("this harness requires KiCad %d or newer, found %s"
                % (MIN_MAJOR, version))
    return None


def find_repo_root(start=None):
    """git if it is there, the working directory if it is not. git is convenient,
    not required: the harness must run from a plain download of the repository."""
    start = start or os.getcwd()
    try:
        proc = subprocess.Popen(["git", "-C", start, "rev-parse", "--show-toplevel"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, _ = proc.communicate()
        if proc.returncode == 0:
            return out.decode("utf-8", "replace").strip()
    except OSError:
        pass
    return os.path.abspath(start)


def pick_project(matches, explicit=None):
    """Exactly one board, or an error that says what to do about it."""
    if explicit:
        if not os.path.exists(explicit):
            raise EnvError("no such board file: %s" % explicit)
        return explicit
    if not matches:
        raise EnvError("no .kicad_pcb found. Run from inside the repository, "
                       "or pass --project /path/to/board.kicad_pcb")
    if len(matches) > 1:
        raise EnvError("several boards found; pass --project to choose one:\n  %s"
                       % "\n  ".join(sorted(matches)))
    return matches[0]


def find_project(root, explicit=None):
    """The board, and the schematic that shares its stem."""
    matches = glob.glob(os.path.join(root, "*.kicad_pcb"))
    matches += glob.glob(os.path.join(root, "*", "*.kicad_pcb"))
    pcb = pick_project(sorted(set(matches)), explicit)
    sch = pcb[: -len(".kicad_pcb")] + ".kicad_sch"
    if not os.path.exists(sch):
        raise EnvError("board found but no matching schematic: expected %s" % sch)
    return pcb, sch


class Environment(object):
    def __init__(self, cli, version, repo_root, pcb, sch, baseline_dir, build_dir):
        self.cli = cli
        self.version = version
        self.repo_root = repo_root
        self.pcb = pcb
        self.sch = sch
        self.baseline_dir = baseline_dir
        self.build_dir = build_dir


def build(args):
    """Everything the gates need, or EnvError explaining what is missing."""
    cli, version = find_cli()
    problem = check_floor(version)
    if problem:
        raise EnvError(problem)
    root = find_repo_root()
    pcb, sch = find_project(root, getattr(args, "project", None))
    baseline = getattr(args, "baseline_dir", None) or os.path.join(root, "verify", "baseline")
    return Environment(cli, version, root, pcb, sch, baseline,
                       os.path.join(root, ".build", "verify"))
```

- [ ] **Step 4: Run to verify they pass**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"
```

Expected: `PASS  selftest 12 checks passed`, exit 0.

- [ ] **Step 5: Wire up `doctor`**

In `__main__.py`, replace the placeholder branch:

```python
    if args.command == "doctor":
        return _doctor(args, report)
```

and add:

```python
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
```

`baseline.read_meta` does not exist yet — Task 8 writes it. Until then, add a two-line stub in a new `tools/kicadverify/baseline.py` so `doctor` runs:

```python
"""Baseline capture and metadata. Task 8 fills this in."""
import json
import os


def read_meta(baseline_dir):
    """The captured baseline's metadata, or None if there is no baseline."""
    path = os.path.join(baseline_dir, "meta.json")
    if not os.path.exists(path):
        return None
    with open(path) as handle:
        return json.load(handle)
```

- [ ] **Step 6: Run `doctor` against the real environment**

```bash
"$PY" tools/kicad-verify.py doctor; echo "exit=$?"
```

Expected on the `harness` branch before any baseline exists: the six progress lines on stderr with the real macOS paths and version `10.0.4`, then `error: no baseline in .../verify/baseline`, `FAIL  doctor   no baseline captured`, exit 2.

Then prove the override and the failure message:

```bash
KICAD_CLI=/nonexistent "$PY" tools/kicad-verify.py doctor; echo "exit=$?"
```

Expected: an error listing every path tried, starting with `/nonexistent`, and telling the reader to set `KICAD_CLI`. Exit 2.

- [ ] **Step 7: Commit**

```bash
git add tools/kicadverify/discover.py tools/kicadverify/baseline.py \
        tools/kicadverify/__main__.py tools/kicadverify/selftest.py
git commit -m "Add cross-platform discovery and the doctor command"
```

---

## Task 5: The gerber gate

**Files:**
- Create: `tools/kicadverify/gerber.py`
- Modify: `tools/kicadverify/__main__.py`

**Interfaces:**
- Consumes: `Environment`, `Report`, `canon.canon`, `report.scrub`.
- Produces:
  - `gerber.export(env, report, raw_dir)` — runs `pcb export gerbers` and `pcb export drill` into `raw_dir`
  - `gerber.normalise(raw_dir, out_dir, mode) -> int` — canonicalises, returns the file count
  - `gerber.compare(base_dir, cur_dir) -> list[str]` — names of differing or missing files, sorted
  - `gerber.run(env, report, mode="strict", drift="") -> bool`
  - `gerber.STAMP` — the compiled timestamp-line pattern

Recover the shell original first: `git show archive/kicad10-3d-2026-09-06:tools/gerber-gate.sh`.

- [ ] **Step 1: Write the failing test**

Normalisation is where a port silently diverges, and the trap is specific: the shell version appends `grep -E '^%T[OA]\.' "$f" | sort`, and `sort` is **locale-sensitive** while Python's `sorted()` is not. Encode the intent so the difference is caught here rather than in Task 10:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"
```

Expected: `FAIL  selftest 1 of 13 checks failed`, naming `gerber`.

- [ ] **Step 3: Write the implementation**

```python
"""The copper gate: export gerbers and drill, canonicalise, compare against the baseline.

Two modes. `strict` compares geometry plus the X2 net and component attributes, so a net
rename is visible. `geometry` drops those attributes, for a change that legitimately
renames nets while moving no copper. Strict is the default and the one that is committed.

Drill and job files are compared with timestamps stripped and nothing else: they are
already order-independent, and the drill file has been observed byte-stable across a
board format upgrade that rewrote 12 of 22 gerbers.
"""
import os
import re
import shutil

from .canon import canon_lines
from .discover import EnvError, run_cli

# Timestamp-bearing lines, all three forms observed in KiCad 10 output.
STAMP = re.compile(r"CreationDate|Created by KiCad|DRILL file .* KiCad")

ATTRIBUTE = re.compile(r"^%T[OA]\.")


def export(env, report, raw_dir):
    if os.path.isdir(raw_dir):
        shutil.rmtree(raw_dir)
    os.makedirs(raw_dir)
    report.progress("gerber", "exporting gerbers")
    run_cli(env, report, ["pcb", "export", "gerbers", "--output", raw_dir, env.pcb],
         "pcb export gerbers")
    report.progress("gerber", "exporting drill")
    run_cli(env, report, ["pcb", "export", "drill", "--output", raw_dir, env.pcb],
         "pcb export drill")


def normalise_lines(lines, mode):
    """Canonical form of one gerber, as a list of lines without terminators.

    sorted() rather than the shell's `sort`: byte order, not locale order. The two
    disagree on files containing mixed case, and the committed baseline was written
    by a `sort` running under the C locale.
    """
    lines = list(lines)
    units = canon_lines(lines)
    if mode == "strict":
        units = units + sorted(line.rstrip("\r\n") for line in lines
                               if ATTRIBUTE.match(line))
    return units


def normalise(raw_dir, out_dir, mode):
    """Canonicalise every exported file into out_dir. Returns the file count."""
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    count = 0
    for name in sorted(os.listdir(raw_dir)):
        source = os.path.join(raw_dir, name)
        target = os.path.join(out_dir, name)
        with open(source, errors="replace") as handle:
            lines = handle.readlines()
        if name.endswith(".drl") or name.endswith(".gbrjob"):
            body = [line.rstrip("\r\n") for line in lines if not STAMP.search(line)]
        else:
            body = normalise_lines(lines, mode)
        with open(target, "w") as handle:
            for line in body:
                handle.write(line + "\n")
        count += 1
    return count


def compare(base_dir, cur_dir):
    """Names of files that differ, are missing, or are unexpected. Sorted."""
    base = set(os.listdir(base_dir))
    cur = set(os.listdir(cur_dir))
    differing = sorted((base - cur) | (cur - base))
    for name in sorted(base & cur):
        with open(os.path.join(base_dir, name), "rb") as a, \
                open(os.path.join(cur_dir, name), "rb") as b:
            if a.read() != b.read():
                differing.append(name)
    return sorted(differing)


def run(env, report, mode="strict", drift=""):
    raw = os.path.join(env.build_dir, "gerber-raw")
    cur = os.path.join(env.build_dir, "gerber-" + mode)
    base = os.path.join(env.baseline_dir, mode)

    export(env, report, raw)
    count = normalise(raw, cur, mode)
    report.progress("gerber", "%d files canonicalised (%s)" % (count, mode))

    if not os.path.isdir(base):
        raise EnvError("no %s baseline in %s. Run: "
                       "python3 tools/kicad-verify.py baseline" % (mode, base))

    differing = compare(base, cur)
    if not differing:
        report.gate("gerber", True, "%d files identical%s" % (count, drift),
                    mode=mode, files=count, version_drift=bool(drift))
        return True

    report.gate("gerber", False,
                "%d files differ: %s%s" % (len(differing), ", ".join(differing[:3]),
                                           drift),
                mode=mode, files=count, differing=differing,
                version_drift=bool(drift))
    for name in differing:
        report.detail("--- %s" % name)
        _show_diff(os.path.join(base, name), os.path.join(cur, name), report)
    return False


def _show_diff(base_path, cur_path, report, limit=20):
    """First few differing units. The full file is on disk; this is orientation."""
    import difflib
    try:
        with open(base_path, errors="replace") as a:
            old = a.readlines()
        with open(cur_path, errors="replace") as b:
            new = b.readlines()
    except IOError as exc:
        report.detail(str(exc))
        return
    for i, line in enumerate(difflib.unified_diff(old, new, "baseline", "current")):
        if i >= limit:
            report.detail("... truncated; compare %s with %s" % (base_path, cur_path))
            break
        report.detail(line.rstrip())
```

- [ ] **Step 4: Wire up the command**

Every gate command has the same shape — build the environment, run one gate, map the outcome to an exit code — so write that shape once in `__main__.py` and let the three gates share it:

```python
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
```

and dispatch to it:

```python
    if args.command == "gerber":
        from . import gerber
        mode = "geometry" if args.geometry else "strict"
        return _gate(args, report, lambda env: gerber.run(env, report, mode))
```

Drift defaults to `""` here; Task 8 supplies the real value.

- [ ] **Step 5: Run to verify the selftest passes**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"
```

Expected: `PASS  selftest 13 checks passed`, exit 0.

- [ ] **Step 6: Run the gate against the real board**

There is no baseline on the `harness` branch yet, so the honest expectation is a clean environment error:

```bash
"$PY" tools/kicad-verify.py gerber; echo "exit=$?"
```

Expected: export progress on stderr, then `error: no strict baseline in .../verify/baseline/strict. Run: python3 tools/kicad-verify.py baseline`, exit 2 — **not** exit 1. This is the distinction the whole design rests on; confirm the number.

Then prove the comparison path works by borrowing the archive's baseline:

```bash
mkdir -p verify/baseline
git archive archive/kicad10-3d-2026-09-06 verify/baseline/strict | tar -x
"$PY" tools/kicad-verify.py gerber; echo "exit=$?"
```

Expected: `PASS  gerber   22 files identical`, exit 0. Master's board is the KiCad 6 original the archive's baseline was captured from, so this must pass. **If it fails, stop** — either the port diverged or the locale trap above is real; read the diff before going further.

```bash
rm -rf verify/baseline           # leave the branch clean; Task 8 captures it properly
```

- [ ] **Step 7: Commit**

```bash
git add tools/kicadverify/gerber.py tools/kicadverify/__main__.py tools/kicadverify/selftest.py
git commit -m "Add the gerber gate: export, canonicalise, compare"
```

---

## Task 6: The netlist gate

**Files:**
- Create: `tools/kicadverify/netlist.py`
- Modify: `tools/kicadverify/__main__.py`
- Modify: `tools/kicadverify/selftest.py`

**Interfaces:**
- Consumes: `Environment`, `Report`, `gerber._run` (moved to a shared helper — see Step 3).
- Produces:
  - `netlist.extract(lines) -> list[str]` — the connectivity section, pure
  - `netlist.run(env, report, drift="") -> bool`

- [ ] **Step 1: Write the failing test**

The extraction rule from the shell version is `awk '/^\t(nets/{f=1} f'` then `grep -v '^\s*(pintype '`. Both halves are line-leading matches, which is why the fixture below puts `(pintype …)` on its own line — that is how kicad-cli emits it, and a rule that matched anywhere in the line would also eat the `(node …)` that carries the connectivity. Encode both halves and the reason:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"
```

Expected: `FAIL  selftest 1 of 14 checks failed`.

- [ ] **Step 3: Write the gate**

`discover.run_cli` already exists from Task 4 and is what this gate uses to call kicad-cli; do not add a second runner here.

```python
"""The connectivity gate: does every pin still map to the same net?

The gerber gate cannot see schematic-side damage, because the board is not edited when
a symbol is. The netlist is the ground truth linking schematic to copper: if it is
unchanged, no symbol edit can have moved a net to a different pad.

Only the (nets ...) section is compared. The rest of the netlist legitimately gains and
loses metadata when symbols are refreshed from their libraries -- datasheet URLs,
ki_keywords, ki_fp_filters, ngspice Sim.* fields -- none of which is connectivity, and
all of which would otherwise make this gate cry wolf on every library update.
"""
import os

from .discover import EnvError, run_cli

NETS_MARKER = "\t(nets"
PINTYPE = "(pintype "


def extract(lines):
    """The connectivity section: everything from the (nets marker on, minus pintype."""
    out, started = [], False
    for line in lines:
        if not started:
            if line.startswith(NETS_MARKER):
                started = True
            else:
                continue
        if line.lstrip().startswith(PINTYPE):
            continue
        out.append(line)
    return out


def run(env, report, drift=""):
    raw = os.path.join(env.build_dir, "netlist.raw")
    cur = os.path.join(env.build_dir, "netlist.nets")
    base = os.path.join(env.baseline_dir, "netlist.nets")
    if not os.path.isdir(env.build_dir):
        os.makedirs(env.build_dir)

    report.progress("netlist", "exporting netlist")
    run_cli(env, report,
            ["sch", "export", "netlist", "--format", "kicadsexpr",
             "--output", raw, env.sch],
            "sch export netlist")

    with open(raw, errors="replace") as handle:
        nets = extract(handle.readlines())
    with open(cur, "w") as handle:
        handle.writelines(nets)
    report.progress("netlist", "%d connectivity lines" % len(nets))

    if not os.path.exists(base):
        raise EnvError("no netlist baseline at %s. Run: "
                       "python3 tools/kicad-verify.py baseline" % base)

    with open(base, errors="replace") as handle:
        expected = handle.readlines()
    if expected == nets:
        report.gate("netlist", True, "every pin maps to the same net%s" % drift,
                    lines=len(nets), version_drift=bool(drift))
        return True

    import difflib
    changed = [line for line in difflib.unified_diff(expected, nets, "baseline", "current")
               if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))]
    report.gate("netlist", False,
                "%d connectivity lines differ%s" % (len(changed), drift),
                lines=len(nets), changed=len(changed), version_drift=bool(drift))
    for line in changed[:40]:
        report.detail(line.rstrip())
    if len(changed) > 40:
        report.detail("... %d more; compare %s with %s" % (len(changed) - 40, base, cur))
    return False
```

- [ ] **Step 4: Wire up the command**

In `__main__.py`, add a `netlist` branch through the `_gate` helper written in Task 5:

```python
    if args.command == "netlist":
        from . import netlist
        return _gate(args, report, lambda env: netlist.run(env, report))
```

- [ ] **Step 5: Run to verify it passes**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"
```

Expected: `PASS  selftest 14 checks passed`, exit 0.

- [ ] **Step 6: Run the gate against the real schematic**

```bash
mkdir -p verify/baseline
git show archive/kicad10-3d-2026-09-06:verify/baseline/netlist.nets > verify/baseline/netlist.nets
"$PY" tools/kicad-verify.py netlist; echo "exit=$?"
```

Expected: `PASS  netlist  every pin maps to the same net`, exit 0. Then:

```bash
rm -rf verify/baseline
"$PY" tools/kicad-verify.py netlist; echo "exit=$?"
```

Expected: exit 2 with the "no netlist baseline" message.

- [ ] **Step 7: Commit**

```bash
git add tools/kicadverify/netlist.py tools/kicadverify/gerber.py \
        tools/kicadverify/discover.py tools/kicadverify/__main__.py \
        tools/kicadverify/selftest.py
git commit -m "Add the netlist gate and share the kicad-cli runner"
```

---

## Task 7: The rules report

**Files:**
- Create: `tools/kicadverify/rules.py`
- Modify: `tools/kicadverify/__main__.py`
- Modify: `tools/kicadverify/selftest.py`

**Interfaces:**
- Consumes: `Environment`, `Report`, `discover.run_cli`.
- Produces:
  - `rules.violations(doc) -> list[dict]` — flattens the two shapes ERC and DRC use
  - `rules.summarise(doc) -> dict` with keys `total`, `errors`, `warnings`, `by_type` (an ordered list of `(type, count)`), and for DRC also `unconnected` and `parity`
  - `rules.run(env, report) -> bool` — always `True` unless it could not run

**A decision this plan makes that the spec left open.** `rules` is a **report, not a gate**. It emits an `INFO` verdict and never fails. There are two reasons. It has no baseline to compare against, so there is nothing for it to be right or wrong about. And master's pre-conversion board legitimately carries 5 `starved_thermal` errors — a "zero errors" gate would report master as broken forever, which contradicts the preservation rule that the gates run green on master after every merge. `all` therefore takes its verdict from `gerber` and `netlist` only. If a future workstream wants rule counts frozen, that is a baseline of its own and a separate design.

- [ ] **Step 1: Write the failing test**

The one non-obvious thing is that ERC nests violations under sheets while DRC lists them at the top level:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"
```

Expected: `FAIL  selftest 1 of 15 checks failed`.

- [ ] **Step 3: Write the implementation**

```python
"""ERC and DRC counts, total and by type.

This reports rather than judges. There is no baseline for rule counts, and the counts
legitimately move as a project is worked on: the reader decides whether a number is
acceptable. It emits an INFO verdict for that reason, and `all` does not take its
verdict from here.

kicad-cli returns a non-zero exit code when it finds violations, which is not an error
condition for this command -- a board with warnings still produced a valid report.
"""
import collections
import json
import os

from .discover import EnvError, run_cli


def violations(doc):
    """ERC nests violations under sheets; DRC lists them at the top level."""
    if "sheets" in doc:
        return [v for sheet in doc["sheets"] for v in sheet.get("violations", [])]
    return doc.get("violations", [])


def summarise(doc):
    items = violations(doc)
    severity = collections.Counter(v.get("severity", "?") for v in items)
    summary = {
        "total": len(items),
        "errors": severity.get("error", 0),
        "warnings": severity.get("warning", 0),
        "by_type": collections.Counter(
            v.get("type", "?") for v in items).most_common(),
    }
    if "unconnected_items" in doc or "schematic_parity" in doc:
        summary["unconnected"] = len(doc.get("unconnected_items", []))
        summary["parity"] = len(doc.get("schematic_parity", []))
    return summary


def _collect(env, report, kind):
    """Run one checker and read its JSON. Violations are not a failure here."""
    path = os.path.join(env.build_dir, "%s.json" % kind.lower())
    args = (["sch", "erc", "--format", "json", "--severity-all",
             "--output", path, env.sch] if kind == "ERC" else
            ["pcb", "drc", "--format", "json", "--severity-all",
             "--output", path, env.pcb])
    report.progress("rules", "running %s" % kind)
    run_cli(env, report, args, "%s" % kind.lower(), allow_failure=True)
    if not os.path.exists(path):
        raise EnvError("%s produced no report at %s" % (kind, path))
    with open(path, errors="replace") as handle:
        return summarise(json.load(handle))


def run(env, report):
    if not os.path.isdir(env.build_dir):
        os.makedirs(env.build_dir)
    erc = _collect(env, report, "ERC")
    drc = _collect(env, report, "DRC")

    for label, summary in (("ERC", erc), ("DRC", drc)):
        report.detail("%s %d  errors=%d warnings=%d"
                      % (label, summary["total"], summary["errors"],
                         summary["warnings"]))
        for kind, count in summary["by_type"]:
            report.detail("     %4d  %s" % (count, kind))
    report.detail("     unconnected=%d  parity=%d"
                  % (drc.get("unconnected", 0), drc.get("parity", 0)))

    report.info("rules",
                "ERC %d (%d errors)  DRC %d (%d errors)"
                % (erc["total"], erc["errors"], drc["total"], drc["errors"]),
                erc=erc, drc=drc)
    return True
```

`run_cli`'s `allow_failure` parameter exists from Task 4 for exactly this: kicad-cli exits non-zero when ERC or DRC finds violations, and a board with warnings still produced a valid report.

- [ ] **Step 4: Wire up the command**

```python
    if args.command == "rules":
        from . import rules
        return _gate(args, report, lambda env: rules.run(env, report))
```

- [ ] **Step 5: Run to verify the selftest passes**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"
```

Expected: `PASS  selftest 15 checks passed`, exit 0.

- [ ] **Step 6: Run against the real project and check the numbers**

```bash
"$PY" tools/kicad-verify.py rules; echo "exit=$?"
```

On the `harness` branch — which carries master's KiCad 6 board — the recorded v1.4 reference is **DRC 212 total: 190 `lib_footprint_issues`, 17 `silk_edge_clearance`, 5 `starved_thermal`**. Expect exactly that, `INFO  rules    ...`, exit 0. A different total means the port changed what is counted; do not proceed past it.

Also verify the JSON carries the breakdown an agent needs:

```bash
"$PY" tools/kicad-verify.py rules --json | head -40
```

- [ ] **Step 7: Commit**

```bash
git add tools/kicadverify/rules.py tools/kicadverify/discover.py \
        tools/kicadverify/__main__.py tools/kicadverify/selftest.py
git commit -m "Add the ERC and DRC rules report"
```

---

## Task 8: Baseline capture, meta.json and version drift

**Files:**
- Modify: `tools/kicadverify/baseline.py`
- Modify: `tools/kicadverify/__main__.py`
- Modify: `tools/kicadverify/selftest.py`

**Interfaces:**
- Consumes: `gerber.export`, `gerber.normalise`, `netlist.extract`, `discover.Environment`, `report.drift_suffix`.
- Produces:
  - `baseline.read_meta(baseline_dir) -> dict or None` (already exists)
  - `baseline.write_meta(baseline_dir, env, modes)` 
  - `baseline.source_commit(repo_root) -> str` — the git commit, or `"unknown"` outside a repository
  - `baseline.capture(env, report, force=False) -> bool`
  - `baseline.drift_for(env) -> str` — the suffix to hang on a verdict line, `""` when the majors agree

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run to verify it fails**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"
```

Expected: `FAIL  selftest 1 of 16 checks failed`.

- [ ] **Step 3: Write the implementation**

Append to `tools/kicadverify/baseline.py`:

```python
"""Capture the frozen reference and record what it was captured from.

meta.json exists for two reasons. Version drift is only detectable if the baseline
remembers which KiCad wrote it. And a later capture -- of the geometry variant, say,
which is deliberately not committed -- has to be made from the same commit rather than
from a master that has moved on, so the commit is recorded too.

Only the strict gerber baseline and netlist.nets are committed. The geometry variant is
half the bulk and has never been needed: every task so far kept nets identical. It can
be recreated from the commit named here on the day something needs it.

The strict baseline stays committed rather than being regenerated on demand, because a
baseline that is regenerated on demand can be regenerated *after* a mistake, silently
erasing the evidence it exists to preserve. A committed one cannot be quietly
re-derived: changing it shows up as a diff.
"""
import datetime
import json
import os
import shutil
import subprocess

from . import gerber, netlist
from .discover import EnvError, run_cli
from .report import drift_suffix

FORMAT = 1


def build_meta(kicad_version, commit, project, modes):
    return {
        "tool": "kicad-verify",
        "format": FORMAT,
        "kicad_version": kicad_version,
        "captured": datetime.datetime.now(
            datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": commit,
        "project": project,
        "modes": list(modes),
    }


def source_commit(repo_root):
    try:
        proc = subprocess.Popen(["git", "-C", repo_root, "rev-parse", "HEAD"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, _ = proc.communicate()
        if proc.returncode == 0:
            return out.decode("utf-8", "replace").strip()
    except OSError:
        pass
    return "unknown"


def drift_for(env):
    """The version-drift suffix for a verdict line. Empty when the majors agree."""
    meta = read_meta(env.baseline_dir)
    if not meta:
        return ""
    return drift_suffix(meta.get("kicad_version", ""), env.version)


def capture(env, report, force=False):
    existing = read_meta(env.baseline_dir)
    if existing and not force:
        raise EnvError(
            "a baseline already exists in %s, captured %s with KiCad %s from commit %s.\n"
            "Pass --force to replace it."
            % (env.baseline_dir, existing.get("captured"),
               existing.get("kicad_version"), (existing.get("commit") or "")[:12]))
    if existing:
        report.warn("replacing the baseline captured %s with KiCad %s from commit %s"
                    % (existing.get("captured"), existing.get("kicad_version"),
                       (existing.get("commit") or "")[:12]))

    raw = os.path.join(env.build_dir, "gerber-raw")
    strict_dir = os.path.join(env.baseline_dir, "strict")
    gerber.export(env, report, raw)
    if os.path.isdir(strict_dir):
        shutil.rmtree(strict_dir)
    count = gerber.normalise(raw, strict_dir, "strict")
    report.progress("baseline", "%d gerber and drill files captured" % count)

    nets_path = os.path.join(env.baseline_dir, "netlist.nets")
    raw_netlist = os.path.join(env.build_dir, "netlist.raw")
    run_cli(env, report,
            ["sch", "export", "netlist", "--format", "kicadsexpr",
             "--output", raw_netlist, env.sch], "sch export netlist")
    with open(raw_netlist, errors="replace") as handle:
        nets = netlist.extract(handle.readlines())
    with open(nets_path, "w") as handle:
        handle.writelines(nets)
    report.progress("baseline", "%d connectivity lines captured" % len(nets))

    write_meta(env, ["strict"])
    report.gate("baseline", True,
                "captured %d files and %d nets with KiCad %s"
                % (count, len(nets), env.version),
                files=count, lines=len(nets), kicad_version=env.version)
    return True


def write_meta(env, modes):
    meta = build_meta(env.version, source_commit(env.repo_root),
                      os.path.relpath(env.pcb, env.repo_root), modes)
    with open(os.path.join(env.baseline_dir, "meta.json"), "w") as handle:
        json.dump(meta, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return meta
```

`capture` exports the netlist itself rather than calling `netlist.run`, because `run` compares against a baseline and there is not one yet — that is the whole point of this command. It shares `netlist.extract` with the gate, so the two can never disagree about what counts as connectivity.

- [ ] **Step 4: Wire drift into the two comparing gates**

Both comparing gates now carry the drift suffix. Add one helper to `__main__.py` and thread it through the two lambdas:

```python
def _drift(env, report):
    """The version-drift suffix, and the warning that goes with it. The suffix reaches
    an agent through the verdict line and the JSON; the warning reaches a human on
    stderr. It is never an exit code -- it obliges the reader to check the changelog,
    it does not decide for them."""
    from . import baseline as baseline_mod
    suffix = baseline_mod.drift_for(env)
    if suffix:
        report.warn("baseline was captured with a different major KiCad version; "
                    "differences may be emitter changes, not board changes")
    return suffix
```

```python
    if args.command == "gerber":
        from . import gerber
        mode = "geometry" if args.geometry else "strict"
        return _gate(args, report,
                     lambda env: gerber.run(env, report, mode, _drift(env, report)))

    if args.command == "netlist":
        from . import netlist
        return _gate(args, report,
                     lambda env: netlist.run(env, report, _drift(env, report)))
```

And add the `baseline` branch:

```python
    if args.command == "baseline":
        from . import baseline as baseline_mod
        return _gate(args, report,
                     lambda env: baseline_mod.capture(env, report, args.force))
```

- [ ] **Step 5: Run to verify the selftest passes**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"
```

Expected: `PASS  selftest 16 checks passed`, exit 0.

- [ ] **Step 6: Capture the real baseline and verify it against the archive**

This is the moment the baseline enters the `harness` branch:

```bash
"$PY" tools/kicad-verify.py baseline; echo "exit=$?"
```

Expected: `PASS  baseline captured 22 files and N nets with KiCad 10.0.4`, exit 0.

Now the check that matters — it must equal what the shell scripts produced:

```bash
git show archive/kicad10-3d-2026-09-06:verify/baseline/netlist.nets > $SCRATCH/archive-netlist.nets
diff -q $SCRATCH/archive-netlist.nets verify/baseline/netlist.nets && echo "netlist baseline: identical"

rm -rf $SCRATCH/archive-strict && mkdir -p $SCRATCH/archive-strict
git archive archive/kicad10-3d-2026-09-06 verify/baseline/strict \
  | tar -x -C $SCRATCH/archive-strict --strip-components=2
diff -r -q $SCRATCH/archive-strict verify/baseline/strict && echo "gerber baseline: identical"
```

Both must report identical. If they do not, the port diverged — read the diff and fix the port, not the baseline.

Then prove `--force`:

```bash
"$PY" tools/kicad-verify.py baseline; echo "exit=$?"          # exit 2, names what exists
"$PY" tools/kicad-verify.py baseline --force; echo "exit=$?"  # exit 0, warns what it replaced
```

- [ ] **Step 7: Commit**

```bash
git add tools/kicadverify/baseline.py tools/kicadverify/__main__.py \
        tools/kicadverify/selftest.py verify/baseline/
git commit -m "Add baseline capture with meta.json and wire up version drift"
```

The committed baseline is `verify/baseline/strict/` (22 files), `verify/baseline/netlist.nets` and `verify/baseline/meta.json`. Confirm `verify/baseline/geometry` is **not** among the staged files.

---

## Task 9: The `all` command

**Files:**
- Modify: `tools/kicadverify/__main__.py`
- Modify: `tools/kicadverify/selftest.py`

**Interfaces:**
- Consumes: `gerber.run`, `netlist.run`, `rules.run`.
- Produces: `__main__.combine(outcomes) -> int` — pure, maps a list of per-gate outcomes to the final exit code.

- [ ] **Step 1: Write the failing test**

Exit-code precedence is the property most worth encoding, because getting it wrong is exactly the failure that makes an agent report a false regression:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"
```

Expected: `FAIL  selftest 1 of 17 checks failed`.

- [ ] **Step 3: Write the implementation**

```python
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


def _all(args, report):
    """Every gate, in order, with nothing skipped. A run reports everything that is
    wrong, not just the first thing -- someone fixing three problems should learn about
    all three in one run. selftest is not included: it tests the tool, not the project."""
    from . import discover, gerber, netlist, rules
    try:
        env = discover.build(args)
    except discover.EnvError as exc:
        report.error(str(exc))
        report.finish()
        return EXIT_ENV

    drift = _drift(env, report)

    mode = "geometry" if args.geometry else "strict"
    outcomes = []
    for name, call in (("gerber", lambda: gerber.run(env, report, mode, drift)),
                       ("netlist", lambda: netlist.run(env, report, drift)),
                       ("rules", lambda: rules.run(env, report))):
        try:
            outcomes.append("pass" if call() else "fail")
        except discover.EnvError as exc:
            report.error("%s: %s" % (name, exc))
            report.gate(name, False, "could not run")
            outcomes.append("env")

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
```

The `all` line is `INFO` rather than `FAIL` when the code is 2, because a gate that did not run is not a verdict on the board. `FAIL  all` would assert that something was checked and found wrong, which is exactly the confusion the three exit codes exist to prevent — and it would be the tool committing the error it is built to stop an agent making.

- [ ] **Step 4: Wire up the command**

```python
    if args.command == "all":
        return _all(args, report)
```

- [ ] **Step 5: Run to verify it passes**

```bash
"$PY" tools/kicad-verify.py selftest; echo "exit=$?"
```

Expected: `PASS  selftest 17 checks passed`, exit 0.

- [ ] **Step 6: Run everything against the real project**

```bash
"$PY" tools/kicad-verify.py all; echo "exit=$?"
```

Expected, on the `harness` branch with the baseline captured in Task 8:

```
PASS  gerber   22 files identical
PASS  netlist  every pin maps to the same net
INFO  rules    ERC 413 (0 errors)  DRC 212 (5 errors)
PASS  all      3 of 3 gates passed
```

exit 0. Then prove no gate is skipped after a failure:

```bash
mv verify/baseline/netlist.nets $SCRATCH/nets.bak
"$PY" tools/kicad-verify.py all; echo "exit=$?"
mv $SCRATCH/nets.bak verify/baseline/netlist.nets
```

Expected: gerber still passes, netlist reports `could not run`, rules still runs and reports its counts, the final line is `INFO  all      incomplete: gerber=pass, netlist=env, rules=pass`, and the exit code is **2**. Three facts matter: nothing was skipped, the summary does not claim a verdict, and the code is 2 rather than 1.

- [ ] **Step 7: Commit**

```bash
git add tools/kicadverify/__main__.py tools/kicadverify/selftest.py
git commit -m "Add the all command with exit-code precedence"
```

---

## Task 10: Prove the rewrite against the shell implementation

The port is not finished until the Python produces byte-identical output to the scripts it replaces. Task 8 already compared the captured baseline against the archive's; this task closes the remaining gaps — the `geometry` mode, which is never committed and so was never compared, and the verdicts themselves.

**Files:**
- Create: `docs/harness-equivalence.md` (the evidence, committed with the branch)

**Interfaces:**
- Consumes: everything.
- Produces: nothing the code depends on.

- [ ] **Step 1: Capture the geometry baseline both ways**

The Python side:

```bash
"$PY" tools/kicad-verify.py gerber --geometry; echo "exit=$?"
```

This will exit 2 — there is no committed geometry baseline, by design. The normalised output is still on disk at `.build/verify/gerber-geometry/`. Compare it against the archive's:

```bash
rm -rf $SCRATCH/archive-geometry && mkdir -p $SCRATCH/archive-geometry
git archive archive/kicad10-3d-2026-09-06 verify/baseline/geometry \
  | tar -x -C $SCRATCH/archive-geometry --strip-components=2
diff -r -q $SCRATCH/archive-geometry .build/verify/gerber-geometry && echo "geometry: identical"
```

Expected: identical. This is the mode with no committed baseline, so it is the one where a divergence could have hidden indefinitely.

- [ ] **Step 2: Compare the verdicts**

Run the archived shell scripts and the new harness side by side on the same tree. The shell scripts need `tools/kicad-env.sh`, which hardcodes this repository's board path, so extract them to a scratch directory rather than onto the branch:

```bash
mkdir -p $SCRATCH/shellgates/tools
for f in kicad-env.sh gerber_canon.py gerber-gate.sh netlist-gate.sh rules-report.sh; do
  git show "archive/kicad10-3d-2026-09-06:tools/$f" > "$SCRATCH/shellgates/tools/$f"
done
chmod +x $SCRATCH/shellgates/tools/*.sh
```

The scripts resolve `REPO_ROOT` from git, so running them from inside this working tree points them at this board. Copy them in temporarily, run, remove:

```bash
cp $SCRATCH/shellgates/tools/*.sh $SCRATCH/shellgates/tools/gerber_canon.py tools/
bash tools/gerber-gate.sh   ; echo "shell gerber  exit=$?"
bash tools/netlist-gate.sh  ; echo "shell netlist exit=$?"
bash tools/rules-report.sh  ; echo "shell rules   exit=$?"
rm -f tools/kicad-env.sh tools/gerber-gate.sh tools/netlist-gate.sh \
      tools/rules-report.sh tools/gerber_canon.py
git status --porcelain tools/     # must be empty of these five
```

The shell scripts use `$KICAD_PY`, KiCad's bundled interpreter, so they are not blocked by the sandbox hook.

Record: shell `gerber-gate(strict): PASS` against Python `PASS  gerber   22 files identical`; shell `netlist-gate: PASS` against Python `PASS  netlist  ...`; shell `DRC 212` with its three-line breakdown against Python's `INFO  rules` and JSON.

- [ ] **Step 3: Write the evidence down**

`docs/harness-equivalence.md` — short, factual, and dated. It records what was compared, on which commit, with which KiCad, and the result. This document is the answer to "how do you know the rewrite did not change what is being checked", and it is worth more than any assertion in the code.

Include: the commit the comparison ran on, KiCad version, the three diffs (strict, geometry, netlist) and their results, the DRC total and breakdown from both implementations, and the note that `rules` changed from a bare report to an `INFO` verdict with the same numbers underneath.

- [ ] **Step 4: Run the whole thing once more from a clean tree**

```bash
git stash list                     # expect empty
rm -rf .build
"$PY" tools/kicad-verify.py selftest && "$PY" tools/kicad-verify.py all; echo "exit=$?"
```

Expected: 17 selftest checks pass, then the four-line `all` output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add docs/harness-equivalence.md
git commit -m "Record the evidence that the Python harness matches the shell scripts"
```

---

## Task 11: Documentation and finishing the branch

**Files:**
- Create: `tools/README.md`
- Modify: `README.md` (repository root — add a short section pointing at the harness)

**Interfaces:**
- Consumes: everything.
- Produces: nothing the code depends on.

- [ ] **Step 1: Write `tools/README.md`**

Written for a stranger who has just cloned a published repository, not for the person who built it. It must cover, in this order:

1. **What it does**, in two sentences: proves the copper, the connectivity and the rule counts did not change.
2. **How to run it**, on each platform, as literal commands:

```
macOS / Linux:   python3 tools/kicad-verify.py all
Windows:         py tools\kicad-verify.py all
```

3. **Requirements:** KiCad 10 or newer, and any Python 3.8 or newer. Nothing else — no `pip install`, no virtual environment, no configuration file. If `kicad-cli` is not on `PATH`, set `KICAD_CLI`.
4. **The commands**, as a table: `doctor`, `baseline`, `gerber`, `netlist`, `rules`, `all`, `selftest`.
5. **The three exit codes**, with the sentence that explains why there are three rather than two: `1` means the board changed, `2` means the check could not run, and conflating them makes an agent report a regression that did not happen.
6. **What the version warning means:** it fires when the running KiCad's major version differs from the one that captured the baseline. It is not a failure. It means: read the KiCad changelog and confirm any difference is an emitter change and not a real one.
7. **Using it on another project:** copy `tools/kicad-verify.py` and `tools/kicadverify/` into any KiCad repository and run `baseline` once. No project name is hard-coded anywhere.
8. **What is deliberately not here:** CI, packaging, and a test framework. Name them as future steps so a reader does not think they were forgotten.

- [ ] **Step 2: Verify the README's claims are true, one at a time**

Every command in the README gets run before the README is committed. Documentation that was never executed is the most common way a published repository wastes a stranger's afternoon.

```bash
"$PY" tools/kicad-verify.py doctor
"$PY" tools/kicad-verify.py selftest
"$PY" tools/kicad-verify.py gerber
"$PY" tools/kicad-verify.py netlist
"$PY" tools/kicad-verify.py rules
"$PY" tools/kicad-verify.py all
"$PY" tools/kicad-verify.py all --json | head -20
```

And the repository-agnostic claim, which is the easiest one to have broken:

```bash
grep -ril "radio-86rk" tools/ ; echo "matches above must be none"
```

- [ ] **Step 3: Add the root README section**

Four or five lines under a `## Verification` heading: what the harness guarantees, the one command to run it, and a pointer to `tools/README.md`. Do not duplicate the tool's documentation in the root README; it will drift.

- [ ] **Step 4: Confirm the branch contains only Workstream A**

```bash
git diff --stat master..harness
```

Expected paths only: `.gitignore`, `tools/kicad-verify.py`, `tools/kicadverify/*`, `tools/fixtures/*`, `tools/README.md`, `verify/baseline/*`, `docs/harness-equivalence.md`, `README.md`. Anything under `KiCad/` on this branch is a mistake — A does not touch the board.

- [ ] **Step 5: Final gate run**

```bash
rm -rf .build
"$PY" tools/kicad-verify.py selftest && "$PY" tools/kicad-verify.py all; echo "exit=$?"
```

Expected: exit 0.

- [ ] **Step 6: Commit**

```bash
git add tools/README.md README.md
git commit -m "Document the verification harness for a first-time reader"
```

- [ ] **Step 7: Request review, then merge**

Use `superpowers:requesting-code-review`, then `superpowers:finishing-a-development-branch`. Per the preservation rules: merge to master, do **not** delete the `harness` branch, and run the gates on master after the merge:

```bash
git checkout master && git merge --no-ff harness
"$PY" tools/kicad-verify.py all; echo "exit=$?"
```

Expected: exit 0 on master. That is preservation rule 5 satisfied, and it is what makes master's copper claim verified rather than asserted.

---

## Future steps, recorded not built

- **CI / GitHub Actions.** A workflow running `selftest` and `all` on push. It needs a runner with KiCad 10 installed, which pins a version and is its own piece of work. The harness is shaped for it: three exit codes, `--json` output, and no interactive input.
- **Packaging** the harness as a standalone reusable component with its own repository.
- **A test framework** beyond `selftest`, if the harness ever grows past what fixture checks can cover.
- **A rules baseline**, if a future workstream wants ERC and DRC counts frozen rather than reported.
