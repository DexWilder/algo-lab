# Forge Report — FX London-open breakout — 2026-06-16

> **Mode:** Lane B / REPORT-ONLY. **Verdict: KILL** — no FX contract independently viable (per-instrument gate, no pooled pass). No promotion/wiring/mutation.
> Artifacts: `research/forge_cycle_2026-06-16_fx_london_open_breakout.py` + `.json`.

## Result (per-instrument gate per operator 2026-06-16)
Range-breakout after London open, 6E/6J/6B, two ET window mappings (02:00–03:00, 03:00–04:00 — robust to GMT→ET DST ambiguity), session-slippage 2x stress.

| window | 6E | 6J | 6B |
|---|---|---|---|
| 02:00–03:00 ET | PF 0.65 | PF 0.57 | PF 0.51 |
| 03:00–04:00 ET | PF 0.66 | PF 0.69 | PF 0.76 |

All PF<1, negative medians, WR ~45–50% (both windows, both halves weak, 2x-slip worse). **No contract independently viable** (PF≥1.3 + positive median + 2x-slip≥1.2 + conc≤50% + prop-DD all required). → **KILL, no pooled pass.**

WR ~50% confirms genuine no-edge (not a logic/DST artifact). London-open range breakouts on these FX contracts don't continue profitably after costs (if anything they mean-revert). The vol-cap refinement from the source note is a possible follow-up but low prior given the sub-1.0 base.

## Boundaries
Report-only; no promotion/wiring/mutation; canonical feeds + active books untouched. Phase 1C frozen pending PHASE1C_24H_VERIFY.
