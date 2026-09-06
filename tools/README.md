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
| `doctor`   | Checks the environment: is `kicad-cli` found, is it new enough, is there a project and a captured baseline. Exits `0` if everything needed is present, `2` if not. Run this first when anything else fails unexpectedly. |
| `baseline` | Captures a new reference snapshot of the board's gerbers, drill files and netlist connectivity into `verify/baseline/`. Fails if a baseline already exists there; pass `--force` to overwrite it. |
| `gerber`   | Exports gerbers and drill files from the current board, canonicalises them, and compares them against the committed baseline. Reports whether the copper is unchanged. |
| `netlist`  | Exports the netlist from the current schematic and compares its connectivity (which pin is on which net) against the baseline. Reports whether the wiring is unchanged. |
| `rules`    | Runs ERC and DRC and reports the violation counts, by type. This is informational, not pass/fail — see below. |
| `all`      | Runs `gerber`, `netlist` and `rules` in order, and prints a combined verdict. This is the one command most people want. |
| `selftest` | Runs the harness's own internal checks (currently 21) against fixtures. Tests the tool itself, not your project — it needs no KiCad install and no board. |

Useful flags, valid on every command above: `--json` (emit one JSON document
instead of verdict lines), `--verbose` (show tool output that is normally
filtered as noise), `--project PCB` (point at a specific `.kicad_pcb` if more
than one exists), `--baseline-dir DIR` (use a baseline somewhere other than
`verify/baseline`).

## The three exit codes, and why there are three and not two

| Exit code | Meaning |
|-----------|---------|
| `0` | Every gate passed. Nothing changed. |
| `1` | A gate failed. The board (or its rules count, where applicable) genuinely changed. |
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
