"""Locate kicad-cli, the repository and the project, on any of the three platforms.

The harness needs no pcbnew, which is what makes this tractable: KiCad's Python is
bundled inside the application on macOS and Windows but is a distribution package on
Linux, and there is no portable way to find it. kicad-cli is an executable, and an
executable can be found by looking.
"""
import glob
import ntpath
import os
import subprocess
import sys

MIN_MAJOR = 10


class EnvError(Exception):
    """Something the harness needs is missing or ambiguous. Always exit 2:
    'I could not run the check' is a different fact from 'the board changed'."""


def _version_key(name):
    """Sort key for a KiCad install directory. '10.0' must outrank '9.0',
    which a string sort gets backwards. Non-numeric parts sort low rather
    than raising, so a stray directory cannot break discovery."""
    return [int(part) if part.isdigit() else -1 for part in name.split(".")]


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
                versions = sorted(listdir(base), key=_version_key, reverse=True)   # highest version first
            except OSError:
                versions = []
            for version in versions:
                candidates.append(ntpath.join(base, version, "bin", "kicad-cli.exe"))
    else:
        candidates.extend([
            "/usr/bin/kicad-cli",
            "/usr/local/bin/kicad-cli",
            # The flatpak *export* wrapper (org.kicad.KiCad, bare) launches the
            # KiCad GUI, not kicad-cli -- there is no kicad-cli export at all.
            # "flatpak run --command=kicad-cli org.kicad.KiCad" is the form that
            # actually runs the CLI, and it resolves system or user installs the
            # same way, so one candidate covers both scopes. This is an argv list,
            # not a path, because it is a command with a fixed argument, not an
            # executable found by looking.
            ["flatpak", "run", "--command=kicad-cli", "org.kicad.KiCad"],
            "/snap/bin/kicad.kicad-cli",
        ])
    return candidates


def _argv(cli):
    """Normalise a resolved (or candidate) cli to an argv list: a bare path
    becomes a one-element list, the flatpak form is already a list."""
    return list(cli) if isinstance(cli, (list, tuple)) else [cli]


def cli_display(cli):
    """Human-readable form of a resolved kicad-cli, for progress output."""
    return " ".join(_argv(cli))


def _runs(candidate, timeout=10):
    """The version string if `<candidate> version` runs and exits 0 within
    `timeout` seconds, else None.

    The timeout matters because the flatpak export wrapper some candidates
    resolve to launches the KiCad GUI rather than kicad-cli on a host with no
    kicad-cli on PATH: without it, discovery would block on a GUI process
    forever instead of failing with the documented actionable message.
    Expiry is treated the same as any other candidate that does not work --
    not as an error -- so the search moves on to the next one.
    """
    try:
        proc = subprocess.Popen(_argv(candidate) + ["version"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        return None
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return None
    return proc.returncode == 0 and out.decode("utf-8", "replace").strip() or None


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
        # KICAD_CLI is what the reader already set, and it is what just failed --
        # telling them to "Set KICAD_CLI=..." again describes the problem as its
        # own fix. Name the setting and say it did not run, not how to set it.
        raise EnvError(
            "KICAD_CLI is set to %s but it did not run as kicad-cli %d or newer.\n"
            "Check that path, or unset KICAD_CLI to search the usual locations."
            % (explicit, MIN_MAJOR))
    tried = cli_candidates(platform, environ)
    for candidate in tried:
        version = _runs(candidate)
        if version:
            return candidate, version
    raise EnvError(
        "kicad-cli not found. Set KICAD_CLI=/path/to/kicad-cli or install KiCad %d.\n"
        "Tried:\n  %s" % (MIN_MAJOR, "\n  ".join(cli_display(c) for c in tried)))


def run_cli(env, report, args, what, allow_failure=False):
    """kicad-cli with its noise filtered and its real errors kept. Lives here rather
    than in a gate because all three gates need it.

    allow_failure is for the checkers: kicad-cli exits non-zero when ERC or DRC finds
    violations, which is a result, not a failure to run.
    """
    from .report import scrub
    proc = subprocess.Popen(_argv(env.cli) + args,
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
