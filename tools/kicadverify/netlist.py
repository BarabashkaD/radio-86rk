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


def run(env, report, drift="", baseline_kicad=None, running_kicad=None):
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
    if not nets:
        # extract() itself must stay pure and reusable, so the emptiness check lives
        # here, at its one caller. An absent (nets marker is not an exception -- it is
        # silently empty output -- and an empty result is never a legitimate outcome
        # for a real board: comparing it against the baseline would report "everything
        # changed" for a connectivity section that was simply never exported.
        raise EnvError(
            "netlist export produced no connectivity section (no (nets marker found "
            "in %s); the export is suspect" % raw)
    with open(cur, "w") as handle:
        handle.writelines(nets)
    report.progress("netlist", "%d connectivity lines" % len(nets))

    if not os.path.exists(base):
        raise EnvError("no netlist baseline at %s. Run: "
                       "python3 tools/kicad-verify.py baseline" % base)

    # The version fields ride along whenever a baseline was found to compare
    # against, not only when the majors disagree -- an agent should not have to
    # infer "no drift" from an absent key.
    extra = {}
    if baseline_kicad is not None:
        extra["baseline_kicad"] = baseline_kicad
        extra["running_kicad"] = running_kicad
        extra["version_drift"] = bool(drift)

    with open(base, errors="replace") as handle:
        expected = handle.readlines()
    if expected == nets:
        report.gate("netlist", True, "every pin maps to the same net%s" % drift,
                    lines=len(nets), **extra)
        return True

    import difflib
    changed = [line for line in difflib.unified_diff(expected, nets, "baseline", "current")
               if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))]
    report.gate("netlist", False,
                "%d connectivity lines differ%s" % (len(changed), drift),
                lines=len(nets), changed=len(changed), **extra)
    for line in changed[:40]:
        report.detail(line.rstrip())
    if len(changed) > 40:
        report.detail("... %d more; compare %s with %s" % (len(changed) - 40, base, cur))
    return False
