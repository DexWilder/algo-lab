# Sprint B — Commodity term-structure carry (CL/GC) — VERDICT 2026-07-01

**Data:** real per-contract Databento ohlcv-1d (CL, GC), roll-handled (no cross-contract jump). Report-only.
**Expressions tested (3 of 6 predeclared):** CL carry, GC carry, cross-sectional CL/GC carry.

| Expression | Sh | net | H1/H2 | max-year | side | validator | verdict |
|---|---|---|---|---|---|---|---|
| CL carry (long backwardated) | 0.11 | +$30.7k | 0.10/0.12 | **135%** (one year) | 66% long | YEAR_CONCENTRATION flag | weak/artifact |
| GC carry (long backwardated) | −0.48 | −$217k | −0.6/−0.5 | — | **93% short** | **EXPR_INVALID DEGENERATE_SIDE** | rejected pre-verdict |
| xsec CL/GC (long higher-carry) | 0.32 | — | — | — | ok | — | weak |

**Best = CL, Sh 0.11, DSR global = 0.0 (N=1776) → FAMILY VERDICT: CLEAN_KILL for naive roll-yield carry-sign.**
Adversarial review: PASS (kill label, no overclaim).

## Why GC failed the *expression* check, not just the backtest
Gold carries a structural cost-of-carry → the curve is in contango almost always → `sign(F1−F2)` ≈ constant short.
That is directional gold beta, not a carry signal. The pre-test expression validator caught this BEFORE the −$217k
result could be mistaken for evidence. This is the validator doing exactly its job (locked control).

## SCOPE (do NOT over-claim exhaustion — per scope-negative-results rule)
KILLED: **naive raw-sign roll-yield carry on CL/GC daily per-contract.** NOT killed: the commodity term-structure
FAMILY. 3 of 6 predeclared expressions remain, now refined by what we learned:
1. **GC de-trended carry** — carry z-score vs own rolling contango baseline (raw sign is degenerate; z-score is the correct expression).
2. **CL/GC front–deferred spread momentum** (trade the curve, not the level).
3. **CL/GC front–deferred spread mean-reversion.**
4. **Roll-window pressure** (long-ETF roll bleed in steep contango — the NOVELTY_PACKETS #13 mechanism).

Micro mapping if any survives: CL→MCL, GC→MGC (signal identical, contract 1/10 size).
Family map status: **commodity carry = ACTIVE_EXPANSION** (naive sub-expression killed; 4 refined queued).
