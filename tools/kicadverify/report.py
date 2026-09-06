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
