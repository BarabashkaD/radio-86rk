# Retained ERC violations

32 violations remain, all warnings, zero errors. They are recorded here as deliberate
decisions rather than fixed.

## 32 × `same_local_global_label`

Address, data and control-bus signals that carry both a **local** and a **global** label of
the same name on the same sheet: `A0`–`A14`, `D0`–`D7`, the strobes `~{RD}` `~{WR}`
`~{IOR}` `~{MEMW}`, plus `OSC`, `RESET`, `TTL_CLK` on the root sheet, and `SPKR_ENA`,
`PIT2_ENA` on the Keyboard sheet.

KiCad flags the mixed scope as ambiguous to a reader. It is not a defect: each signal
resolves to exactly one net. `A0`, for example, is a single net carrying 10 nodes — the
CPU, both EPROMs, the RAM, the PPI, the DMA controller and the expansion header.

### Why they are not fixed

**The cost is 91 edits, not 32.** ERC reports a violation per *signal name*, not per label.
A signal keeps its warning while **any** local label of that name coexists with the global
one, and each signal carries 2–4 local labels:

| Signal group | Local labels each |
|---|---:|
| `A0`, `A1`, `A2`, `A3`, `A4`, `A5`, `TTL_CLK`, `~{IOR}`, `~{MEMW}` | 2 |
| `A6`–`A11` | 3 |
| `A12`–`A14`, `D0`–`D7`, `RESET`, `~{WR}` | 4 |
| `~{RD}`, `PIT2_ENA`, `SPKR_ENA` | 1 |

**Total: 91 local labels** would have to be deleted or converted to clear all 32 warnings.

This was tested, not assumed. Six local labels were deleted from the root sheet
(`A0`–`A5`); the netlist gate confirmed connectivity was untouched, and the ERC count did
not move — 32 before, 32 after. The change was reverted.

Ninety-one manual edits to a working, frozen schematic, for warnings that carry no errors
and change no copper, is a poor trade. The board's whole premise is that it is preserved
exactly.

### Why not convert them to global labels instead

Converting `label` → `global_label` is mechanically simpler and cannot split a net. It is
rejected anyway: the design spec records that converting local labels to global is what
masked the U3/U22 RS-232 defect on the `migrate2kicad10` branch, by giving those pins a
driver and silencing the connectivity check. Doing it to 91 labels is that same manoeuvre
at scale, and it would change how the schematic reads for no functional gain.

**Reason recorded:** `bus signals carry both label scopes by original design; one net each,
verified in the netlist; fixing costs 91 edits for 0 errors`

## GitHub issue #2 — U3 / U22 RS-232 wiring

Not currently reported. The 8251A (U3) and SN75154 (U22) have receiver input and output
pins wired backwards — a defect in the original v1.4 design, filed as
[issue #2](https://github.com/BarabashkaD/radio-86rk/issues/2).

If resolving further symbol or label links ever makes `pin_not_driven` /
`pin_not_connected` / `unconnected_wire_endpoint` violations appear on U3 or U22, that is
this defect becoming visible — the correct outcome, not a regression. It is **not fixed
here**: correcting it requires moving wire endpoints, a topology change, and this project's
top constraint is that the board is preserved exactly. It must **not** be silenced by
relabelling.

## Marking them as exclusions in KiCad

The list above is the durable record. Marking each violation excluded additionally cleans
the ERC panel, and is a GUI action: **Inspect → Electrical Rules Checker**, run, then
right-click each → **Exclude with comment**.

As with the DRC exclusions, this could not be scripted — see `docs/drc-exclusions.md` for
why.
