# Forge Candidate Ledger — 2026-06-17

> Report-only candidate queue. Gates here are **promotion gates, not research gates** — banking a gated candidate does NOT pause discovery. No activation/registry/scheduler/portfolio/paper/live/prop mutation.

## ALIVE / gated candidates
| Candidate | Lane | Status | Evidence | Promotion gate |
|---|---|---|---|---|
| **MGC-prior_day_break** | 2 (gold sleeve) | **`GOLD_CAP_GATED_ADDITION_CANDIDATE`** | distinct return-add: overlap 34.5%, corr 0.244, adds +$5.8k net, combined PF 1.464, worst-day −$1,363 (prop-OK). NOT a risk-reducer (deepens DD; no bad-day offset). NOT WH2. | **Gold concentration / MGC soft-cap** (would be 5th gold book) — operator decision before any promotion. **Research continues meanwhile.** |
| Rates-FOMC-week sleeve (ZN+ZF) | 1 (event) | banked, DATA_AUDIT_GREEN, regime-gated; executor fidelity-green | needs activation reopen + external DSCL + V1 packet (out-of-band wiring) |
| FOMC-MNQ-1h | 1 (event) | banked, executor-compatible, all-weather + entry/hold robust | activation reopen + Phase 1C clear + DSCL + V1 packet |
| **Month-End Rates settlement flow** (ZF primary, long bonds last ~3d into EVERY month-end) — supersedes the quarter-end-only version | 1 (structural event/tail) | **`PASS_tail`-grade (cycle 17r, 2026-06-17 — UPGRADED from quarter-end WATCH_tail)** | **Generalizing to all month-ends resolved the limiters:** ZF-K3 n=**84**, PF **1.92** (cost-robust 1.61@3x), max-single **6.8%**, top3 **16.8%**, max-year **36.4%** (passes <50%), 7/8 yrs+, both halves +, worst-day −$1,125 (prop-OK). Non-QE months PF 2.01 (stronger) → genuine monthly settlement flow, not QE-specific. First candidate this session to clear tail-engine gates. | **`PASS_tail` ≠ paper-ready.** Still: clean-events/data-integrity audit (ZF roll artifacts), forward validation, 2021 zero-rate year negative (regime caveat), ZN confirm weaker (pos 0.56 — ZF primary), confirm low FOMC-sleeve overlap. **Cadence 12/yr = event/tail, NOT daily WH2.** |

## Incumbent live/wired books (benchmarks, not candidates)
MNQ: XB-ORB-EMA-Ladder-MNQ (PF 1.628), WH-MNQ-stop_run_reversal (PF 1.477, Phase 1C). Gold: XB-ORB-EMA-Ladder-MGC (wired probation, PF 1.495). Plus core MGC books, treasury-rolldown (out-of-band).

## DEAD / archived this session (no-repeat)
- **P8 real-rate gold gate** — NaN-rolling artifact; corrected → hurts sleeve. Not WH2/diversifier/overlay.
- **MNQ first_impulse_pullback** — REDUNDANT-with-orb + DD "benefit" was a 2025 drift artifact (3/8 years, piles on bad days).
- **P12 WTI-Brent reversion → MCL** — no edge on stale (FRED) AND fresh (Yahoo) data → mechanism dead.
- **FRED yield-curve carry** (rotation / naïve spread / duration-balanced) — branch closed/mapped-dead.
- **P9 breakeven rotation, copper/gold→ZN, dollar→MCL** — decorrelated-but-no-edge KILLs.
- **donchian_breakout (MNQ)** REDUNDANT; range_compression_break NEUTRAL; pb_pullback/vwap_continuation KILL.

## Open frontiers (research continues — NOT paused)
- **Lane 1 (WH2/diversifier, highest-EV):** structural feeds — Treasury auctions (stage CSV → WP-B1) > rates F2 roll > EIA surprise; PLUS reachable forced-flow tests (calendar/settlement/roll).
- **Lane 2 (sleeve-improvement):** MNQ open for genuinely-distinct/replacement mechanisms; gold further additions gated by the same soft-cap concern as pdb.

## Note
PDB is **gated for promotion, not for research.** Forge continues.
