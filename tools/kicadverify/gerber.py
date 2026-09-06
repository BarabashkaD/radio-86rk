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

# Timestamp-bearing lines, all three forms observed in KiCad 10 output. The drill
# file's line is literally "; DRILL file KiCad 10.0.4 date ...": there is no
# separator between "file" and "KiCad", so the pattern must match that literally
# rather than with a ".*" that would never find one.
STAMP = re.compile(r"CreationDate|Created by KiCad|DRILL file KiCad")

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
