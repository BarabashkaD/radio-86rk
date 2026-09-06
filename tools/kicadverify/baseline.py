"""Baseline capture and metadata.

meta.json exists for two reasons. Version drift is only detectable if the baseline
remembers which KiCad wrote it. And a later capture -- of the geometry variant, say,
which is deliberately not committed -- has to be made from the same commit rather than
from a master that has moved on, so the commit is recorded too.

Only the strict gerber baseline and netlist.nets are committed. The geometry variant is
half the bulk and has never been needed in this repository -- every task so far kept
nets identical -- so `baseline --geometry` captures it on demand, into the same
--baseline-dir, without ever being committed itself.

The strict baseline stays committed rather than being regenerated on demand, because a
baseline that is regenerated on demand can be regenerated *after* a mistake, silently
erasing the evidence it exists to preserve. A committed one cannot be quietly
re-derived: changing it shows up as a diff.
"""
import datetime
import json
import os
import subprocess

from . import gerber, netlist
from .discover import EnvError, run_cli
from .report import drift_suffix

FORMAT = 1


def read_meta(baseline_dir):
    """The captured baseline's metadata, or None if there is no baseline.

    A meta.json that exists but will not parse is a different fact from "no
    baseline": it is an environment problem -- the tool cannot read its own
    metadata -- not a missing-baseline one, so it is raised as EnvError rather
    than left to escape as a bare JSONDecodeError and be mistaken for a gate
    reporting that the board changed.
    """
    path = os.path.join(baseline_dir, "meta.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        try:
            return json.load(handle)
        except ValueError as exc:
            # from None: the ValueError is fully explained in this message: a
            # "During handling of the above exception" chain would just wrap a
            # clean error in a second, noisier one.
            raise EnvError(
                "could not read %s: %s. Re-capture the baseline or restore it "
                "from git." % (path, exc)) from None


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
    """The version-drift suffix for a verdict line. Empty when the majors agree,
    and also when there is no baseline at all -- that is a missing-baseline error
    for the gate to raise, not a drift warning for this to fabricate."""
    meta = read_meta(env.baseline_dir)
    if not meta:
        return ""
    return drift_suffix(meta.get("kicad_version", ""), env.version)


def write_meta(env, modes):
    meta = build_meta(env.version, source_commit(env.repo_root),
                      os.path.relpath(env.pcb, env.repo_root), modes)
    with open(os.path.join(env.baseline_dir, "meta.json"), "w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return meta


def capture(env, report, force=False, mode="strict"):
    """Capture one gerber mode ("strict" or "geometry") plus, the first time
    around, the netlist.

    mode is threaded all the way through rather than hardcoded, and --force and
    the already-exists check are scoped to *this* mode's directory, not to the
    baseline as a whole: capturing geometry must be possible without --force
    just because strict already exists, and must never touch strict's
    directory -- that is the one file this branch exists to establish, and a
    capture that quietly re-derives it could erase evidence of a real
    regression. netlist.nets is not mode-specific, so it is (re)captured only
    on a strict capture or when it does not exist yet -- a geometry capture on
    top of an existing baseline leaves the committed netlist.nets alone.
    """
    existing = read_meta(env.baseline_dir)
    mode_dir = os.path.join(env.baseline_dir, mode)
    nets_path = os.path.join(env.baseline_dir, "netlist.nets")
    already = os.path.isdir(mode_dir)
    if already and not force:
        raise EnvError(
            "a %s baseline already exists in %s.\nPass --force to replace it."
            % (mode, mode_dir))
    if already:
        report.warn("replacing the %s baseline in %s" % (mode, mode_dir))

    if not os.path.isdir(env.baseline_dir):
        os.makedirs(env.baseline_dir)

    raw = os.path.join(env.build_dir, "gerber-raw")
    gerber.export(env, report, raw)
    # gerber.normalise removes and recreates mode_dir itself; no need to do it here too.
    count = gerber.normalise(raw, mode_dir, mode)
    report.progress("baseline", "%d gerber and drill files captured (%s)" % (count, mode))

    if mode == "strict" or not os.path.exists(nets_path):
        raw_netlist = os.path.join(env.build_dir, "netlist.raw")
        run_cli(env, report,
                ["sch", "export", "netlist", "--format", "kicadsexpr",
                 "--output", raw_netlist, env.sch], "sch export netlist")
        with open(raw_netlist, encoding="utf-8", errors="replace") as handle:
            nets = netlist.extract(handle.readlines())
        with open(nets_path, "w", encoding="utf-8") as handle:
            handle.writelines(nets)
        lines = len(nets)
        report.progress("baseline", "%d connectivity lines captured" % lines)
    else:
        report.progress("baseline", "netlist.nets already captured; left untouched")
        with open(nets_path, encoding="utf-8", errors="replace") as handle:
            lines = sum(1 for _ in handle)

    modes = (set(existing.get("modes", [])) if existing else set()) | {mode}
    write_meta(env, sorted(modes))
    report.gate("baseline", True,
                "captured %d files (%s) and %d nets with KiCad %s"
                % (count, mode, lines, env.version),
                files=count, lines=lines, kicad_version=env.version, mode=mode)
    return True
