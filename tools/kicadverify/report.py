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
                  "differences may be emitter changes — check the KiCad changelog]")


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
