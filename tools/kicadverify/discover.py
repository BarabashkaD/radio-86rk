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
    because 'kicad-cli not found' with no list is a dead end for whoever reads it.

    An explicit KICAD_CLI is authoritative, not merely first in line: if the reader
    set it, a silent fall-through to some other kicad-cli found on the machine would
    hide the very problem they need to see, and would mean this tool ran a build they
    did not choose.
    """
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    explicit = environ.get("KICAD_CLI")
    if explicit:
        version = _runs(explicit)
        if version:
            return explicit, version
        raise EnvError(
            "kicad-cli not found. Set KICAD_CLI=/path/to/kicad-cli or install KiCad %d.\n"
            "Tried:\n  %s" % (MIN_MAJOR, explicit))
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
