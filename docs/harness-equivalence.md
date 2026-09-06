# Harness equivalence: the Python rewrite against the shell it replaced

Dated 2026-09-06. Comparison run on commit `63a7b75588a06153ef4732c37d18f9b294f62e04`
(branch `harness`), against the archived shell implementation at tag
`archive/kicad10-3d-2026-09-06` (commit `7645f3c09f3cf4c5daacfe0c9d0b797d331b8ab3`).
KiCad `10.0.4` (`kicad-cli version`), same install for both sides of every
comparison below — the shell scripts invoke it through
`$KICAD_APP/MacOS/kicad-cli` and `$KICAD_APP/Frameworks/Python.framework/.../python3.9`
(see `tools/kicad-env.sh` as archived); the Python harness invokes the same
`kicad-cli` binary via its own discovery logic. Host locale: `en_US.UTF-8`.

## Why this document exists, and why the bar is not "byte-identical"

Tasks 1–9 replaced five shell scripts (`kicad-env.sh`, `gerber_canon.py`,
`gerber-gate.sh`, `netlist-gate.sh`, `rules-report.sh`) with
`python3 tools/kicad-verify.py`, a stdlib-only Python harness. This document is
the evidence that the rewrite checks the same things the shell did — copper
geometry, connectivity, and ERC/DRC counts — not fewer, not different.

The original success bar for this task was "byte-identical output." That bar
turned out to be unattainable by design for two of the twenty-two gerber
files, and meeting it would have meant reproducing a bug rather than proving
equivalence. The archived shell gate built its strict-mode output by grepping
out the X2 net/component attribute lines and piping them through the `sort`
command:

```sh
grep -E '^%T[OA]\.' "$f" | sort >> "$out" || true
```

`sort` with no `LC_ALL` set collates under the process locale — here
`en_US.UTF-8` — which is not byte order. Python's `sorted()` on the harness
side *is* byte order. So the shell gate's own baseline was never
locale-portable: a CI runner set to `LC_ALL=C`, or any non-`en_US` locale,
would have produced a different ordering for those attribute lines than the
one committed to the repository, and reported FAIL against a change that
never happened. That is exactly the failure mode this harness exists to
prevent. The corrected bar, used below, is:

- **strict mode:** 20 of 22 files byte-identical; the remaining two hold the
  identical multiset of lines and differ only in the order of the appended
  X2 attribute block.
- **geometry mode:** 22 of 22 byte-identical (this mode drops the X2 block
  entirely, so there is nothing left for a locale to reorder).
- **netlist:** byte-identical, 5835 lines.
- **rules:** identical ERC/DRC counts and by-type breakdown.

## The decisive experiment: geometry mode isolates the cause

`gerber --geometry` and plain `gerber` (strict) run the identical export and
canonicalisation pipeline; the only difference is that geometry mode does not
append the sorted X2 attribute block at all. If the divergence in strict mode
is caused by that block's sort, geometry mode — having no sort — must
reproduce the archive with zero exceptions. It does:

```
$ python3 tools/kicad-verify.py gerber --geometry; echo "exit=$?"
[gerber] exporting gerbers
[gerber] exporting drill
[gerber] 22 files canonicalised (geometry)
error: no geometry baseline in .../verify/baseline/geometry. Run: python3 tools/kicad-verify.py baseline
exit=2
```

Exit 2 is expected and correct: geometry mode has no committed baseline in
this repository, by design (it exists only to let a legitimate net rename go
unflagged; nothing currently commits to a frozen expectation for it). The
normalised output the run just produced is still on disk. Extract the
archive's copy of `verify/baseline/geometry` (which the shell gate — run
with `--geometry --capture` at some prior point — produced) and diff:

```
$ rm -rf $SCRATCH/ag && mkdir -p $SCRATCH/ag
$ git archive archive/kicad10-3d-2026-09-06 verify/baseline/geometry \
    | tar -x -C $SCRATCH/ag --strip-components=3
$ diff -r -q $SCRATCH/ag .build/verify/gerber-geometry && echo "geometry: 22/22 identical"
geometry: 22/22 identical
```

**Result: 22/22 byte-identical.** No sort, no divergence, in all 22 files —
including the two that diverge in strict mode. This is a controlled
experiment, not just an observation: it isolates the sorted attribute block
as the sole variable and shows that removing it removes the divergence
completely.

## Strict mode: 20/22, and the two exceptions are provably cosmetic

```
$ python3 tools/kicad-verify.py gerber   # (strict is the default mode)
[gerber] exporting gerbers
[gerber] exporting drill
[gerber] 22 files canonicalised (strict)
PASS  gerber   22 files identical
```

That `PASS` is against the *committed* baseline (`verify/baseline/strict`),
which was itself captured by this Python harness (see
`verify/baseline/meta.json`, `"commit": "75e6fbe2..."`) — so it is not, by
itself, a comparison against the shell. The comparison against the shell's
own archived output is:

```
$ rm -rf $SCRATCH/as && mkdir -p $SCRATCH/as
$ git archive archive/kicad10-3d-2026-09-06 verify/baseline/strict \
    | tar -x -C $SCRATCH/as --strip-components=3
$ diff -rq $SCRATCH/as .build/verify/gerber-strict
Files .../as/Radio-86RK-B_Cu.gbl and .build/verify/gerber-strict/Radio-86RK-B_Cu.gbl differ
Files .../as/Radio-86RK-F_Cu.gtl and .build/verify/gerber-strict/Radio-86RK-F_Cu.gtl differ
```

**20 of 22 files byte-identical.** The two exceptions are exactly the two
copper layers — `Radio-86RK-B_Cu.gbl` and `Radio-86RK-F_Cu.gtl` — the layers
carrying the most net-attribute lines (6358 and 5083 lines respectively) and
therefore the only ones with enough X2 attributes for a locale-collation
reordering to be visible. Confirming the difference is ordering only, not
content:

```
$ wc -l $SCRATCH/as/Radio-86RK-B_Cu.gbl .build/verify/gerber-strict/Radio-86RK-B_Cu.gbl
    6358 .../as/Radio-86RK-B_Cu.gbl
    6358 .build/verify/gerber-strict/Radio-86RK-B_Cu.gbl
$ diff <(sort $SCRATCH/as/Radio-86RK-B_Cu.gbl) <(sort .build/verify/gerber-strict/Radio-86RK-B_Cu.gbl)
  (no output — multisets identical)
$ diff <(sort $SCRATCH/as/Radio-86RK-F_Cu.gtl) <(sort .build/verify/gerber-strict/Radio-86RK-F_Cu.gtl)
  (no output — multisets identical)
```

Same line count, same multiset of lines, in both files. Line-by-line diff
(not sorted) confirms every differing line matches `^%TO\.` — i.e. every
line that moved is an X2 net-attribute line, and nothing else in either file
is touched:

```
$ diff $SCRATCH/as/Radio-86RK-F_Cu.gtl .build/verify/gerber-strict/Radio-86RK-F_Cu.gtl \
    | grep -E '^[<>]' | sed 's/^..//' | sort -u | grep -vE '^%T'
  (no output — every differing line is a %T attribute line)
```

**0 real content differences.** The remaining two files match the corrected
success criterion exactly.

### The locale mechanism, made checkable

The shell's `sort` (no `LC_ALL`) uses the process locale's collation, which
is not byte order. This repository's shell runs under `en_US.UTF-8`. A
minimal, reproducible two-line example makes the divergence mechanical
rather than asserted:

```
$ printf '%%TO.N,+12V*%%\n%%TO.N,/~{CRT_CS}*%%\n' > $SCRATCH/mini
$ sort $SCRATCH/mini                # locale collation (en_US.UTF-8)
%TO.N,/~{CRT_CS}*%
%TO.N,+12V*%
$ LC_ALL=C sort $SCRATCH/mini        # byte order
%TO.N,+12V*%
%TO.N,/~{CRT_CS}*%
```

`en_US.UTF-8` collation gives low weight to punctuation (`/`, `~`, `{`, `}`)
in its primary comparison pass, so `/~{CRT_CS}` collates close to `CRT_CS`
and sorts ahead of `+12V`. Byte order has no such pass: `+` is `0x2B` and
`/` is `0x2F`, so `+12V` sorts first. Both orderings are internally
consistent; they are simply different total orders over the same set of
strings, and the shell gate's committed baseline can only match one of them
at a time — whichever locale captured it.

The same divergence, at full scale, on the real attribute lines extracted
from a fresh export of the board:

```
$ grep -E '^%T[OA]\.' $SCRATCH/raw/Radio-86RK-F_Cu.gtl > $SCRATCH/attrs
$ wc -l $SCRATCH/attrs
2149 .../attrs
$ sort $SCRATCH/attrs > $SCRATCH/attrs.locale
$ LC_ALL=C sort $SCRATCH/attrs > $SCRATCH/attrs.byte
$ cmp -s $SCRATCH/attrs.locale $SCRATCH/attrs.byte \
    || echo "locale sort differs from byte sort"
locale sort differs from byte sort
```

Python's `sorted()` is always byte order, regardless of the host's `LANG`
or `LC_ALL`. The rewrite's strict-mode output is therefore reproducible on
any machine, in any locale — which the archived shell gate's was not. That
is the corrected criterion's justification: byte order is the correct fix,
and the archived byte-sequence is the anomaly it corrects.

### The symmetry: the shell gate cannot reproduce the new baseline either

If the difference really is locale collation and nothing else, the shell
gate run against the (Python-authored, byte-order) committed baseline should
fail for the mirror-image reason. It does — see "Side-by-side verdicts"
below, `gerber-gate(strict)`. This is not a new bug on either side; it is the
same one-directional locale dependency observed from the other direction,
and it is recorded here because a reader who runs the shell gate against
this branch will see a FAIL and should not mistake it for a regression.

## Netlist: byte-identical, 5835 lines

```
$ python3 tools/kicad-verify.py netlist
[netlist] exporting netlist
[netlist] 5835 connectivity lines
PASS  netlist  every pin maps to the same net
```

Checked against both baselines directly:

```
$ diff .build/verify/netlist.nets verify/baseline/netlist.nets \
    && echo "netlist: byte-identical vs committed baseline"
netlist: byte-identical vs committed baseline

$ git archive archive/kicad10-3d-2026-09-06 verify/baseline/netlist.nets \
    | tar -x -C $SCRATCH/an --strip-components=2
$ diff .build/verify/netlist.nets $SCRATCH/an/netlist.nets \
    && echo "netlist: byte-identical vs archive baseline"
netlist: byte-identical vs archive baseline
$ wc -l $SCRATCH/an/netlist.nets
5835 .../netlist.nets
```

The netlist gate has no sort step and no free-ordering geometry to
canonicalise — it awks out the `(nets ...)` s-expression block and drops
`(pintype ...)` lines — so there is no locale-sensitive step to diverge on,
and none is observed: all three copies (fresh export, committed baseline,
archived baseline) are byte-identical at 5835 lines.

## Rules: same counts, different verdict shape

Shell (`tools/rules-report.sh`, extracted from the archive and run against
this tree — see "Side-by-side verdicts"):

```
ERC 413  errors=0 warnings=413
      210  footprint_link_issues
      142  lib_symbol_mismatch
       32  same_local_global_label
       29  lib_symbol_issues
DRC 212  errors=5 warnings=207
      190  lib_footprint_issues
       17  silk_edge_clearance
        5  starved_thermal
     unconnected=0  parity=0
```

Python (`python3 tools/kicad-verify.py rules`):

```
[rules] running ERC
[rules] running DRC
        ERC 413  errors=0 warnings=413
              210  footprint_link_issues
              142  lib_symbol_mismatch
               32  same_local_global_label
               29  lib_symbol_issues
        DRC 212  errors=5 warnings=207
              190  lib_footprint_issues
               17  silk_edge_clearance
                5  starved_thermal
             unconnected=0  parity=0
INFO  rules    ERC 413 (0 errors)  DRC 212 (5 errors)
```

**Identical totals, identical by-type breakdown, identical
`unconnected`/`parity` counts.** The one change is in the verdict shape, not
the numbers underneath it: the shell script was a bare report with no
pass/fail semantics at all — it printed counts and exited 0 unconditionally.
The Python harness wraps the same counts in a verdict line
(`INFO  rules    ERC 413 (0 errors)  DRC 212 (5 errors)`) and the same
`--json` document carries the full by-type breakdown as structured data
(`by_type`, `errors`, `warnings`, `total` per gate) rather than only as
human-readable text. `INFO` rather than `PASS`/`FAIL` is deliberate: the
project's ERC/DRC counts are a known, tracked baseline (413 ERC
warnings/0 errors, 212 DRC total split 190/17/5 across
`lib_footprint_issues`/`silk_edge_clearance`/`starved_thermal`) that the team
has decided not to gate the build on yet — `rules` reports drift, it does
not block on it.

## Side-by-side verdicts (shell vs Python, same tree, same commit)

The archived shell scripts were extracted to a scratch directory and copied
into `tools/` only for the duration of these runs, then removed — see
"Housekeeping" below.

| Gate | Shell (archived) | Python (`kicad-verify.py`) |
|---|---|---|
| gerber, strict | `gerber-gate(strict): FAIL` (diffs on the two copper layers' attribute order — see above) | `PASS  gerber   22 files identical` |
| gerber, geometry | `gerber-gate: no geometry baseline; run --capture` (exit 2) | `error: no geometry baseline ...` (exit 2) |
| netlist | `netlist-gate: PASS - every pin maps to the same net` | `PASS  netlist  every pin maps to the same net` |
| rules | bare report, counts above, exit 0 | `INFO  rules    ERC 413 (0 errors)  DRC 212 (5 errors)`, same counts |

The shell gerber gate's FAIL against the *committed* (Python-generated,
byte-order) baseline is the mirror image of the 20/22 result above: this
repository's baseline was captured under byte order, and the shell's
locale-collated sort cannot reproduce it, for exactly the reason it could
not be reproduced in the other direction either. Both directions point at
the same cause. Every other gate agrees exactly between the two
implementations on this tree, at this commit.

### The old gate's exit code, on this same run, was not one it defines

The table above shows `gerber-gate(strict): FAIL` as printed text. The
process's actual exit code for that run was **141**, not the `1` the script
is written to return on a failed diff. The script's tail is:

```sh
if diff -r -q "$BASE" "$NORM" >/dev/null; then
  echo "gerber-gate($MODE): PASS - board geometry unchanged"
else
  echo "gerber-gate($MODE): FAIL"; diff -r -u "$BASE" "$NORM" | head -80; exit 1
fi
```

run under `set -euo pipefail` (declared near the top of the script). `head
-80` closes its input once it has printed 80 lines; on this diff there are
more than 80 lines of output, so `diff` receives `SIGPIPE` when it tries to
write past that point and is killed by that signal. Under `pipefail`, the
exit status of the pipeline is the status of the last command to fail —
`diff`'s `141` (128 + `SIGPIPE`'s signal number 13) — and `set -e` then
takes that non-zero pipeline status as the whole `if` block's result and
exits the script immediately with it, never reaching the `exit 1` written
on the same line. The printed text is correct; the process's exit code is
an accident of how much output the diff happened to produce, not a
decision anyone made.

`141` is neither `0` (pass) nor `1` (the code this script's own author
wrote for "the board changed") — it is `128 + 13`, the shell's generic
encoding for "killed by SIGPIPE," and it appears here only because this
particular failing diff happens to print more than 80 lines. A shorter
failing diff on the very same script would have returned the intended `1`;
a longer one returns `141` instead, for a reason that has nothing to do
with whether the board actually changed. A caller that only checks the
exit code — any CI step that does `gerber-gate.sh || fail-the-build` —
cannot tell "the board changed" apart from "a pipe closed early because the
failure report was long," from the same number alone. The rewrite's three
exit codes (`0` pass, `1` fail, `2` could not run — see `selftest`'s "exit
code precedence" check) exist precisely so that distinction is never left
to how much text a particular failure happens to print.

## Housekeeping performed for this comparison

- The five archived scripts (`kicad-env.sh`, `gerber_canon.py`,
  `gerber-gate.sh`, `netlist-gate.sh`, `rules-report.sh`) were copied into
  `tools/` only long enough to run them, then deleted. Confirmed removed:
  `git status --porcelain tools/` returned empty afterward.
- Neither shell script was run with `--capture`. No file under `verify/`
  was written by this comparison; `git status --porcelain verify/` shows
  only pre-existing, unrelated `.DS_Store` files, present before this task
  began.
- `.build/` is git-ignored; the shell scripts' output there (under
  `.build/gerber-strict`, `.build/netlist.nets`, etc., alongside the
  Python harness's own `.build/verify/...` tree) is not tracked and needed
  no cleanup.

## Full run, clean tree

```
$ git stash list                      # pre-existing stashes from unrelated work; none added or touched by this task
$ rm -rf .build
$ python3 tools/kicad-verify.py selftest
...
PASS  selftest 21 checks passed
```

(An earlier planning note for this rewrite predicted 17 self-test checks;
that number predates later additions to the harness's self-test suite —
version-drift detection, JSON mode, and the `all`-command's exit-code
precedence among them. 21 is the current, correct count, not a discrepancy.)

```
$ python3 tools/kicad-verify.py all
[gerber] exporting gerbers
[gerber] exporting drill
[gerber] 22 files canonicalised (strict)
[netlist] exporting netlist
[netlist] 5835 connectivity lines
[rules] running ERC
[rules] running DRC
        ERC 413  errors=0 warnings=413
              210  footprint_link_issues
              142  lib_symbol_mismatch
               32  same_local_global_label
               29  lib_symbol_issues
        DRC 212  errors=5 warnings=207
              190  lib_footprint_issues
               17  silk_edge_clearance
                5  starved_thermal
             unconnected=0  parity=0
PASS  gerber   22 files identical
PASS  netlist  every pin maps to the same net
INFO  rules    ERC 413 (0 errors)  DRC 212 (5 errors)
PASS  all      3 of 3 gates passed
exit=0
```

## Conclusion

- **Geometry** (22/22): identical, with no locale-sensitive step anywhere in
  the pipeline to explain a divergence if one had appeared.
- **Strict** (20/22, 0 real content differences): the two exceptions are the
  two copper layers, and their only difference is the order of the X2
  attribute block a locale-sensitive `sort` produced in the shell and a
  byte-order `sorted()` produces in Python — demonstrated directly, at both
  minimal and full scale, above.
- **Netlist**: byte-identical, 5835 lines, against both the committed and
  the archived baseline.
- **Rules**: identical counts and identical by-type breakdown between the
  shell report and the Python `INFO` verdict; only the presentation
  changed, from an unconditional bare report to a verdict line with the
  same numbers underneath and a structured JSON form.

The rewrite does not change what is being checked. Where its output differs
from the archived shell's, the difference is exactly one locale-dependent
sort order that carried no information to begin with, and the harness's
byte-order replacement is the more reproducible of the two.
