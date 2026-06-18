# Forge Candidate Ledger — 2026-06-17

> Report-only candidate queue. Gates here are **promotion gates, not research gates** — banking a gated candidate does NOT pause discovery. No activation/registry/scheduler/portfolio/paper/live/prop mutation.

## ALIVE / gated candidates
| Candidate | Lane | Status | Evidence | Promotion gate |
|---|---|---|---|---|
| **MGC-prior_day_break** | 2 (gold sleeve) | **`GOLD_CAP_GATED_ADDITION_CANDIDATE`** | distinct return-add: overlap 34.5%, corr 0.244, adds +$5.8k net, combined PF 1.464, worst-day −$1,363 (prop-OK). NOT a risk-reducer (deepens DD; no bad-day offset). NOT WH2. | **Gold concentration / MGC soft-cap** (would be 5th gold book) — operator decision before any promotion. **Research continues meanwhile.** |
| Rates-FOMC-week sleeve (ZN+ZF) | 1 (event) | banked, DATA_AUDIT_GREEN, regime-gated; executor fidelity-green | needs activation reopen + external DSCL + V1 packet (out-of-band wiring) |
| FOMC-MNQ-1h | 1 (event) | banked, executor-compatible, all-weather + entry/hold robust | activation reopen + Phase 1C clear + DSCL + V1 packet |
| **Quarter-End Rates settlement flow** (ZF primary, long bonds last ~3d into quarter-end) | 1 (structural event/tail) | **`WATCH_tail` (audited 2026-06-17, cycle 17p — downgraded from STRUCTURE_FOUND)** | ZF-K3 PF 1.80, pos 68%, **NOT event-dominated** (max-single 16.4%, top3 40.7%), cost-robust (1.57 @3x), prop-OK (worst-day −$1,125), distinct from FOMC (2/28 overlap), window-robust (K2/3/4 1.90/1.80/1.99). | **NOT packet-grade:** max-year 54.5% (>50%), Q2/June negative (edge is Q3/Q4), n=28 small, ZN leg shaky (window-fragile K2 PF 0.90, year-conc 77%). Path to PASS = more years to resolve year-concentration. NOT daily WH2. |

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
