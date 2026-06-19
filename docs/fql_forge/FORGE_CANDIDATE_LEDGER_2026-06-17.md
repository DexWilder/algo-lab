# Forge Candidate Ledger — 2026-06-17

> Report-only candidate queue. Gates here are **promotion gates, not research gates** — banking a gated candidate does NOT pause discovery. No activation/registry/scheduler/portfolio/paper/live/prop mutation.

## ALIVE / gated candidates
| Candidate | Lane | Status | Evidence | Promotion gate |
|---|---|---|---|---|
| **MGC-prior_day_break** | 2 (gold sleeve) | **`GOLD_CAP_GATED_ADDITION_CANDIDATE`** | distinct return-add: overlap 34.5%, corr 0.244, adds +$5.8k net, combined PF 1.464, worst-day −$1,363 (prop-OK). NOT a risk-reducer (deepens DD; no bad-day offset). NOT WH2. | **Gold concentration / MGC soft-cap** (would be 5th gold book) — operator decision before any promotion. **Research continues meanwhile.** |
| Rates-FOMC-week sleeve (ZN+ZF) | 1 (event) | banked, DATA_AUDIT_GREEN, regime-gated; executor fidelity-green | needs activation reopen + external DSCL + V1 packet (out-of-band wiring) |
| FOMC-MNQ-1h | 1 (event) | banked, executor-compatible, all-weather + entry/hold robust | activation reopen + Phase 1C clear + DSCL + V1 packet |
| **Month-End Rates settlement flow** (ZF primary, long bonds last ~3d into month-end) | 1 (structural event/tail) | **`WATCH_tail`-marginal (cycle 18a audit — DOWNGRADED from PASS_tail; the PASS was a contaminated metric)** | Edge is REAL but WEAK once decontaminated. Headline PF 1.92 was inflated by roll-adjacent months (Feb/May/Aug/Nov PF **3.39**) + FOMC-overlap (PF 1.75, partly the FOMC sleeve). **Truly clean (non-roll AND non-FOMC, n=32): PF 1.48, max-year 84%** (year-dominated → fails concentration). ZF primary; ZN secondary (PF 1.49 clean); **ZB KILL** (clean max-yr 109%). | **NOT packet-grade.** Decontaminated edge fails max-year gate (84%, one-year-dominated) and overlaps FOMC sleeve (24/84). Needs far more years to resolve concentration + must be run FOMC-clean to avoid double-count. 2021 neg. Cadence 12/yr event/tail, NOT daily WH2. De-prioritized vs the cleaner FOMC-week sleeve. |

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

## Rates event/tail MAP (narrowed thesis, banked 2026-06-18 — do not re-grind the cliffs)
The reachable rates calendar/event vein is now mapped. **Thesis: FOMC-specific rates behavior is real; generic macro-date rates flow is NOT broadly alive.**
| Surface | Status |
|---|---|
| **FOMC-week rates (ZN/ZF)** | **cleanest banked rates event sleeve** (the one real ridge) |
| Month-end rates | WATCH-marginal — contaminated (roll-adjacent + 29% FOMC overlap); clean edge thin/year-dominated; needs properly-rolled data |
| Quarter-end rates | subset of month-end, not separate enough |
| NFP-day rates | KILL (clean non-roll/non-FOMC negative) |
| FRED yield-curve carry (rotation/spread/duration-balanced) | KILL — branch closed |
| Reactive overlays (VIX→ZN, copper/gold→ZN, dollar→MCL, real-rate/breakeven→gold) | KILL |
**Implication:** the rates edge is narrow (FOMC), not broad. Don't re-test generic macro-date rates flow. The unproven-but-plausible one (month-end) is FEED-gated (properly-rolled/F2 data).

## Reachable structural-flow queue — WORKED THROUGH (2026-06-18; archive, do not re-poke)
The operator's priority queue of reachable-now structural mechanisms is now mapped:
| # | Item | Status |
|--:|---|---|
| 1 | Treasury auctions / WP-B1 | **FEED-GATED (highest-EV, NOT only-path)** — harness ready-but-unrun |
| 2 | COT positioning | CLOSED — standalone KILL + as-filter NO_IMPROVEMENT (reachable surface banked; Δ-positioning low-pri) |
| 3 | Quad-witch expiry-day | KILL (post-witch seasonal inverted OOS; equity-event/tail) |
| 4 | Settlement-window | KILL (self-caught lookahead inflated PF 2.67→0.98; ZN data-quality-limited; MES=equity) |
| 5 | Index reconstitution | SAMPLE_BLOCKED (Russell annual n=7; S&P-qtrly ≈ quad-witch already KILL) |
| 6 | FX-fixing (London 4pm) | HISTORY-LIMITED (6E/6J/6B 2024+ only, ~2.4yr, can't year-spread; DST timestamp trap) |

**Conclusion: the reachable structural-flow surface is mapped — no robustly-validatable candidate emerged.** This is NOT "out of ideas." The productive path now: (a) **structural FEEDS** (auctions highest-EV; then F2 rates, EIA, etc.), (b) **apply the Claw config** → fresh harvest supply, (c) any **new reachable source** (FRED/Yahoo/COT were found this way — keep probing). Reachable mechanisms got worked; the next ore is feeds/supply, not more reachable screens.

## Note
PDB is **gated for promotion, not for research.** Forge continues — but the reachable rates vein is mapped; the next serious progress is feed-gated (stage the feed to unlock the highest-EV test; this is NOT "Forge done"). Highest-EV unlock: **Treasury auctions CSV** (exact dates, not generic-calendar-inferred, not roll-stitch-dependent, economically forced, distinct from FOMC, rates-native — avoids exactly what hurt month-end).
