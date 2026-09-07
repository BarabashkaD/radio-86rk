"""Report which 3D model references resolve on this machine.

A report, not a gate, for the same reason `rules` is one: there is no baseline to be
right or wrong about, and a missing 3D model says nothing about whether the board
manufactures correctly. The gates are blind to 3D entirely; this says only whether the
files a viewer would need are present.

No pcbnew. The predecessor, tools/model_coverage.py on the archive branch, used it for
exactly two things -- enumerating footprints and reading each one's model filenames --
and both are plain text in the .kicad_pcb. Its real work was variable substitution and
os.path.exists, which is stdlib. Dropping the dependency matters because the machine
where you most want to know which models are missing is the one where KiCad's Python is
not set up.
"""
import os
import re
import sys

# Components that legitimately never carry a model. Carried over from
# model_coverage.py, where the same two prefixes produced the settled 183/183.
EXEMPT_PREFIXES = ("HOLE", "LOGO")

_FOOTPRINT = re.compile(r'^\t\(footprint "')
_REFERENCE = re.compile(r'^\t\t\(property "Reference" "([^"]*)"')
_MODEL = re.compile(r'^\t\t\(model "([^"]*)"')
_VAR = re.compile(r"\$\{([A-Za-z0-9_]+)\}|\$\(([A-Za-z0-9_]+)\)")


def parse(text):
    """[(reference, [model path, ...]), ...] in board order.

    Depth-based rather than a full s-expression parse: a footprint opens at one tab and
    its properties and models sit at two, which is how KiCad writes the file. A nested
    (model inside something else would be missed, and none exists -- every model line in
    this board is a direct child of a footprint.
    """
    footprints = []
    reference, models = None, None
    for line in text.splitlines():
        if _FOOTPRINT.match(line):
            if reference is not None:
                footprints.append((reference, models))
            reference, models = "", []
            continue
        if reference is None:
            continue
        found = _REFERENCE.match(line)
        if found and not reference:
            reference = found.group(1)
            continue
        found = _MODEL.match(line)
        if found:
            models.append(found.group(1))
    if reference is not None:
        footprints.append((reference, models))
    return footprints


def path_vars(platform=None, environ=None, project_dir=None, cli=None):
    """The KiCad path variables this board's model references use, and where each came
    from. Returns {name: (value, source)}; a value of None means unresolved.

    Only macOS is verified. `${KICAD10_3RD_PARTY}` is a user-editable KiCad setting whose
    authoritative source is kicad_common.json in the user's config directory, which this
    does not read: doing that portably is its own problem, and a wrong guess is worse
    than an honest gap. So an unresolved variable is reported as unresolved rather than
    silently producing "the models are missing" -- those are different facts.
    """
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    resolved = {}

    if project_dir:
        resolved["KIPRJMOD"] = (project_dir, "the project directory")

    if platform == "darwin":
        share = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels"
        third = os.path.join(os.path.expanduser("~"), "Documents", "KiCad", "10.0",
                             "3rdparty")
        default_source = "the macOS default location"
    else:
        share = third = None
        default_source = None

    for name, default in (("KICAD10_3DMODEL_DIR", share),
                          ("KICAD8_3DMODEL_DIR", share),
                          ("KICAD10_3RD_PARTY", third),
                          # KICAD6_3RD_PARTY appears in the archive's variable map and
                          # is easy to forget; it points at the same tree.
                          ("KICAD6_3RD_PARTY", third)):
        if environ.get(name):
            resolved[name] = (environ[name], "the %s environment variable" % name)
        elif default:
            resolved[name] = (default, default_source)
        else:
            resolved[name] = (None, None)
    return resolved


def resolve(path, variables):
    """Substitute ${VAR} and $(VAR). Returns None if any variable is unresolved, so the
    caller can distinguish 'cannot look' from 'looked and it was absent'."""
    missing = []

    def swap(match):
        name = match.group(1) or match.group(2)
        value = variables.get(name, (None, None))[0]
        if value is None:
            missing.append(name)
            return match.group(0)
        return value

    substituted = _VAR.sub(swap, path)
    return (None, missing[0]) if missing else (substituted, None)


def coverage(footprints, variables, exists=os.path.exists):
    """(covered, missing, exempt, unresolved).

    A footprint counts as covered if ANY of its models resolves, matching
    model_coverage.py. That is why the headline is footprints and not references: 26
    footprints here carry two models each (socket plus IC, switch plus stabilizer), so
    the reference count is 209 against 183 non-exempt footprints, and only the footprint
    count is comparable with the project's recorded figure.
    """
    covered, missing, exempt, unresolved = [], [], [], []
    for reference, models in footprints:
        found = False
        for model in models:
            path, absent_var = resolve(model, variables)
            if path is None:
                unresolved.append((reference, model, absent_var))
                continue
            if exists(path):
                found = True
        if found:
            covered.append(reference)
        elif not models or reference.startswith(EXEMPT_PREFIXES):
            exempt.append(reference)
        else:
            missing.append((reference, models[0]))
    return covered, missing, exempt, unresolved


def report_models(pcb, report, environ=None, platform=None):
    """INFO only. Never fails a run: this is not a gate."""
    with open(pcb) as handle:
        footprints = parse(handle.read())
    variables = path_vars(platform=platform, environ=environ,
                          project_dir=os.path.dirname(os.path.abspath(pcb)))
    covered, missing, exempt, unresolved = coverage(footprints, variables)

    target = len(covered) + len(missing)
    report.detail("3D coverage %d / %d footprints   (exempt %d)"
                  % (len(covered), target, len(exempt)))
    if unresolved:
        names = sorted(set(name for _, _, name in unresolved))
        report.detail("could not resolve: %s" % " ".join("${%s}" % n for n in names))
        report.detail("  set it in the environment, or check KiCad's path settings")
    if missing:
        report.detail("without a resolving model: %s"
                      % " ".join(sorted(reference for reference, _ in missing)))
    return len(covered), target, len(exempt), len(unresolved)
