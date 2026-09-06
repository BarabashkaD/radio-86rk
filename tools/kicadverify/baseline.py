"""Baseline capture and metadata.

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
    with open(path) as handle:
        try:
            return json.load(handle)
        except ValueError as exc:
            raise EnvError(
                "could not read %s: %s. Re-capture the baseline or restore it "
                "from git." % (path, exc))


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
    with open(os.path.join(env.baseline_dir, "meta.json"), "w") as handle:
        json.dump(meta, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return meta


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

    if not os.path.isdir(env.baseline_dir):
        os.makedirs(env.baseline_dir)

    raw = os.path.join(env.build_dir, "gerber-raw")
    strict_dir = os.path.join(env.baseline_dir, "strict")
    gerber.export(env, report, raw)
    # gerber.normalise removes and recreates strict_dir itself; no need to do it here too.
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
