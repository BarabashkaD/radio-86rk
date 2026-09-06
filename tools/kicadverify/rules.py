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
