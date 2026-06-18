# Forge Candidate Ledger — 2026-06-17

> Report-only candidate queue. Gates here are **promotion gates, not research gates** — banking a gated candidate does NOT pause discovery. No activation/registry/scheduler/portfolio/paper/live/prop mutation.

## ALIVE / gated candidates
| Candidate | Lane | Status | Evidence | Promotion gate |
|---|---|---|---|---|
| **MGC-prior_day_break** | 2 (gold sleeve) | **`GOLD_CAP_GATED_ADDITION_CANDIDATE`** | distinct return-add: overlap 34.5%, corr 0.244, adds +$5.8k net, combined PF 1.464, worst-day −$1,363 (prop-OK). NOT a risk-reducer (deepens DD; no bad-day offset). NOT WH2. | **Gold concentration / MGC soft-cap** (would be 5th gold book) — operator decision before any promotion. **Research continues meanwhile.** |
| Rates-FOMC-week sleeve (ZN+ZF) | 1 (event) | banked, DATA_AUDIT_GREEN, regime-gated; executor fidelity-green | needs activation reopen + external DSCL + V1 packet (out-of-band wiring) |
| FOMC-MNQ-1h | 1 (event) | banked, executor-compatible, all-weather + entry/hold robust | activation reopen + Phase 1C clear + DSCL + V1 packet |
| **Quarter-End Rates settlement flow** (ZF primary + ZN confirmation, long bonds last ~3d into quarter-end) | 1 (structural event/tail) | **`STRUCTURE_FOUND_tail` (NEW 2026-06-17, cycle 17o)** | reachable-data forced-flow: ZF-K3 PF 1.80 (pos 68%, both halves +), ZN-K3 PF 1.98 (both halves +), top3 41-45%; cross-instrument confirmed. Edge is last 3 days (K=5 weaker; ZN-K5 negative). | **Tail-engine audit** (n=28 small → instance CV, max-single<35%, max-year<50%, prop-fit, cost verify) + clean-events; sparse event NOT daily WH2; ZN/ZF=one correlated sleeve |

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
