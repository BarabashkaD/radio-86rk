# kicad-verify: a verification harness for KiCad projects

## What it does

This tool proves that a KiCad project's copper, connectivity and rule counts
have not changed since a known-good point. It compares the current board and
schematic against a captured baseline, and tells you exactly which of those
three things moved, if any.

It does not tell you whether your design is *good*. It tells you whether it
is *the same as before*, in the specific ways that are easy to break by
accident: a net silently reassigned, copper that shifted, a footprint that
lost a pad.

## How to run it

There is no install step. Clone the repository and run:

```
macOS / Linux:   python3 tools/kicad-verify.py all
Windows:         py tools\kicad-verify.py all
```

That runs every check (`gerber`, `netlist`, `rules`) and prints one verdict
line per gate, followed by a combined verdict for the run.

## Requirements

- KiCad 10 or newer (specifically `kicad-cli`, KiCad's command-line tool,
  which ships inside every KiCad 10 install).
- Any Python 3.8 or newer. The standard library only — nothing to `pip
  install`, no virtual environment, no configuration file.

The harness looks for `kicad-cli` in the usual per-OS install locations and
on `PATH`. If it cannot find one, or you want to point it at a specific
install, set the `KICAD_CLI` environment variable to the full path of the
`kicad-cli` executable:

```
export KICAD_CLI=/path/to/kicad-cli          # macOS / Linux
set KICAD_CLI=C:\path\to\kicad-cli.exe        # Windows
```

`KICAD_CLI` is authoritative once set: if it points at something that does
not run, the harness fails with an error naming that path rather than
silently falling back to some other `kicad-cli` it finds elsewhere on the
machine. That is deliberate — a tool that quietly ran a different KiCad than
the one you chose would be worse than one that stops and says so.

## The commands

Run as `python3 tools/kicad-verify.py <command>` (macOS / Linux) or
`py tools\kicad-verify.py <command>` (Windows).

| Command    | What it does |
|------------|--------------|
| `doctor`   | Checks the environment: is `kicad-cli` found, is it new enough, is there a project, and is there a baseline the gates can actually use (`strict/` and `netlist.nets` present). Exits `0` if everything needed is present, `2` if not. Run this first when anything else fails unexpectedly. |
| `baseline` | Captures a new reference snapshot of the board's gerbers, drill files and netlist connectivity into `verify/baseline/`. Fails if a baseline already exists there; pass `--force` to overwrite it. Pass `--geometry` to instead capture (or refresh) the geometry-only baseline alongside it — see [Using `--geometry`](#using---geometry) below. |
| `gerber`   | Exports gerbers and drill files from the current board, canonicalises them, and compares them against the committed baseline. Reports whether the copper is unchanged. |
| `netlist`  | Exports the netlist from the current schematic and compares its connectivity (which pin is on which net) against the baseline. Reports whether the wiring is unchanged. |
| `rules`    | Runs ERC and DRC and reports the violation counts, by type. This is informational, not pass/fail — see [Why `rules` reports instead of judging](#why-rules-reports-instead-of-judging) below. |
| `models`   | Reports which 3D model references resolve on this machine: how many footprints have a model KiCad can find, which do not, and which KiCad path variable is responsible when one cannot be resolved at all. Informational, like `rules`. Needs no `pcbnew` and no `kicad-cli` — it reads the board as text, so it still answers on a machine where KiCad is not set up, which is where the question usually arises. |
| `all`      | Runs `gerber`, `netlist` and `rules` in order, and prints a combined verdict. This is the one command most people want. |
| `run`      | `run <script> [args]` executes a script under the interpreter that can import `pcbnew` — the four model tools in `tools/` need it and no plain interpreter provides it. A passthrough: the script's stdout, stderr and exit code are its own, and no verdict line is written. Set `KICAD_PY` to override discovery. |
| `selftest` | Runs the harness's own internal checks (currently 24) against fixtures. Tests the tool itself, not your project — it needs no KiCad install and no board. |

Useful flags, valid on every command above: `--json` (emit one JSON document
instead of verdict lines), `--verbose` (show tool output that is normally
filtered as noise), `--project PCB` (point at a specific `.kicad_pcb` if more
than one exists), `--baseline-dir DIR` (use a baseline somewhere other than
`verify/baseline`). Two more flags apply to specific commands: `--force`
(`baseline`: overwrite an existing baseline of the same mode) and `--geometry`
(`baseline` and `gerber`: use the geometry-only baseline instead of the
committed strict one — see below).

## Verdict statuses

Each gate's line on stdout begins with one of three statuses, and `--json`
records the same value in that gate's `"status"` field. The one exception is
`run`, which writes no verdict line at all: it is a passthrough, so its stdout
belongs to the script it launched and its exit code is that script's.

| Status | Meaning |
|--------|---------|
| `PASS` | The gate ran and found no difference from the baseline. |
| `FAIL` | The gate ran and found a difference from the baseline. |
| `INFO` | The gate ran and is reporting a count, not a verdict. `rules` (see below) and `models`. An `INFO` gate never causes exit code `1`, and `all`'s combined "N of N gates passed" line does not count it either way. |

## Why `rules` reports instead of judging

`rules` runs ERC and DRC and prints the violation counts, by type. It always
returns `INFO`, never `PASS` or `FAIL`, and it never affects `all`'s exit
code.

There is no baseline for rule counts to compare against, on purpose: unlike
copper and connectivity, the number of ERC/DRC violations legitimately
changes as a project is worked on, and a change in that count is not
automatically a regression. It also means this repository's own current
counts can include violations that are already understood and accepted
rather than accidentally introduced: as of this writing, DRC reports 5
`starved_thermal` errors, a known property of this board's thermal relief
pattern, not something `rules` is equipped to distinguish from a genuine new
problem. Reading the counts and the by-type breakdown, and deciding whether a
change in them is expected, is on the person or agent running the tool.

## Using `--geometry`

`gerber`'s default ("strict") comparison includes the X2 net and component
name attributes KiCad embeds in each gerber, so a net rename shows up even
when no copper moved. `--geometry` drops those attributes and compares copper
shape only — for a change that legitimately renames nets without moving
anything.

The geometry baseline is deliberately not committed (only `strict/` and
`netlist.nets` are). To use it, capture it yourself into the same baseline
directory:

```
python3 tools/kicad-verify.py baseline --geometry
python3 tools/kicad-verify.py gerber --geometry
```

Capturing geometry never touches the committed `strict/` baseline, and
capturing strict never touches `geometry/` — each `--force` applies only to
the mode you are capturing. If you want to keep a geometry baseline out of
the repository entirely (recommended, since it is deliberately uncommitted),
point both commands at a directory outside the repo with `--baseline-dir`.

## The three exit codes, and why there are three and not two

| Exit code | Meaning |
|-----------|---------|
| `0` | Every gate passed. Nothing changed. |
| `1` | A gate failed. The board genuinely changed. |
| `2` | A check could not run at all — no `kicad-cli` found, no baseline captured, no board in the repository, an unexpected error. |

This distinction is the single most important thing to understand about this
tool, and it is easy to get wrong if you only skim the output. `1` means
"the board changed." `2` means "I don't know, because the check never ran."
Those are different facts, and collapsing them is a real hazard: a script,
CI job, or agent that treats any non-zero exit as "a regression" will report
a copper change that never happened, just because `kicad-cli` was not on
`PATH` that day. Always branch on the exit code, not just on "zero or
non-zero."

## What the version warning means

If the harness runs under a different major version of KiCad than the one
that captured the current baseline, it prints a `VERSION-DRIFT` warning to
stderr and (in `--json` mode) sets `"version_drift": true` on the affected
gates.

This is **not** a failure, and it never changes the exit code by itself.
KiCad's own exporters occasionally change their output between major
versions in ways that are cosmetic — reordered attributes, a different
comment string — with no actual change to the board. The warning means: go
read the KiCad changelog for the version jump, and confirm that whatever
difference the gate reports (if any) is one of those emitter changes and not
a real one. It exists because those two situations look identical in a diff
but mean very different things.

## Using it on another project

This harness is not specific to this repository. To use it on a different
KiCad project, copy two things into it:

- `tools/kicad-verify.py`
- `tools/kicadverify/` (the whole directory)

Then, from inside that project's repository, run:

```
python3 tools/kicad-verify.py baseline
```

once, to capture the reference snapshot, and commit the resulting
`verify/baseline/` directory. After that, `python3 tools/kicad-verify.py all`
works the same way it does here. No project name, board name, or file path is
hard-coded anywhere in the tool — it discovers the `.kicad_pcb` in the
repository itself.

## What is deliberately not here

These were left out on purpose, not forgotten:

- **CI / GitHub Actions.** A workflow running `selftest` and `all` on every
  push would need a runner with KiCad 10 installed, which pins a specific
  KiCad version as its own piece of work. The harness's three exit codes,
  `--json` output, and lack of any interactive input are all there to make
  that straightforward to add later.
- **Packaging** the harness as a standalone, independently versioned
  component with its own repository.
- **A test framework** beyond `selftest`, should the harness ever grow past
  what its fixture-based checks can cover.

See also [`docs/harness-equivalence.md`](../docs/harness-equivalence.md) for
the evidence that this harness checks the same things the shell scripts it
replaced checked.
