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

## NEW (2026-06-20, fresh discovery loop after queue archived) — Pre-Holiday Equity Drift
**`STRUCTURE_FOUND_tail` (equity event/tail — NOT the non-MNQ/non-gold WH2).** `forge_cycle_2026-06-20a`. Calendar-mechanical forced-flow (pre-closure short-cover/thin liquidity), proper NYSE holiday calendar (n=69, consistent across instruments). LONG prior-close → pre-holiday close:
- **M2K (Russell small-cap): clean PF 2.65, pos 69%, max-single 13.5%, max-yr 28.9%, both halves + (3.13/2.33), 6/8 yrs+** — standout; distinct index from MNQ/MES.
- MES (S&P): clean PF 1.98, pos 61%, max-yr 24.8%, both halves + (2.40/1.75), 7/8 yrs+.
- MCL/ZN/ZF: KILL (mechanism is equity-specific).
**Status: banked equity event-tail candidate (≈10/yr sparse), alongside FOMC-MNQ-1h. NOT daily WH2.** Audit-pending before packet: cost/slippage robustness, prop worst-day, clean-events deeper, half-day-session handling. Method note: first run used empirical holiday-from-gaps (unreliable — inconsistent n; produced a ZF false-WATCH artifact); fixed with proper calendar → ZF correctly KILL, equity structure confirmed. (Self-caught broken method, no false bank.)

## Reachable DIRECTIONAL-structure class — comprehensively MAPPED (2026-06-22)
Across this session the reachable single-series + calendar + intraday DIRECTIONAL space for a daily non-MNQ/non-gold WH2 is now thoroughly mapped and empty:
- single-series technical (112 cands), cross-asset overlays, rates curve/carry → dead
- calendar directional: month-end (contaminated/marginal), NFP/quarter-end (KILL), day-of-week (rates/crude dead; only equity-beta) → dead for target
- intraday directional: unconditional time-of-day hour-drift → comprehensive KILL (cost eats all)
- event/tail that DID survive: FOMC-week rates, FOMC-MNQ-1h, pre-holiday equity — all event/tail, not daily; gold sleeve (capped)
**Honest convergence: the daily non-MNQ/non-gold workhorse is NOT in the reachable DIRECTIONAL-drift class.** Continuing to fire more directional reachable screens = vanity (two consecutive clean-empty maps confirm it). Genuinely-different LIVE avenues (not yet vanity): (1) **feed-gated forced-flow** — auctions highest-EV (structural flow ≠ price/calendar pattern); (2) **conditional/multi-state intraday microstructure** (not unconditional drift — harder, partially covered by crossbreeding); (3) **Lane-2 sleeve-improvement** (MCL/M2K, not WH2); (4) **new reachable data source** (FRED/Yahoo/COT found by probing). Next loops should pick from these, NOT another directional map.

## Lane-2 overlay candidates (2026-06-22, report-only, NOT WH2)
- **MGC-ORB low-vol-exclusion overlay** (`forge_cycle_2026-06-22d/e`): exclude lowest vol-regime days (entry-day ATR-pctile < ~0.2, lagged). **ROBUST** — predeclared thresholds 0.10-0.30 all improve max-DD (5/5), −$1,022 → −$692..−794 (~22% DD cut), PF held/better, net held, retention 78-93%, both halves +. Modest magnitude, gold (capped sleeve), Lane-2 risk overlay NOT a new strategy/WH2. Status: **confirmed overlay candidate** (would refine the gold sleeve's DD if ever applied; report-only, no wiring).
- **Day-after-loss throttle** (`22e`): NO clean improvement on any book (MNQ-stop overfit-risk @55% retention; MNQ-ORB/MGC-ORB no-improvement). Contrast hint: post-WIN-day weakness (daily-PnL mean-reversion) on MNQ-ORB/MGC-ORB — WATCH observation only, NOT confirmed (heavy net cut, retention/OOS untested), not pursued.
- **MNQ books already vol-robust** (vol overlay no improvement) — reassuring about the wired/strong books.
- **MNQ-ORB session-quality (prior-day trend-efficiency, `forge_cycle_2026-06-22f`):** REAL STRUCTURAL SIGNAL but PARTIAL overlay. Excluding strong-trend-prior days (eff>0.7): in-cycle SESSIONQ_IMPROVES (PF 1.628→1.779, DD −2331→−1879, 77% retain, OOS+). Band test (eff 0.60-0.80): **PF above baseline 5/5 (1.68-1.88, monotone) = robust structural signal (post-big-trend-day ORB exhaustion); BUT DD-benefit only at eff≤0.70 (3/5) + net haircut grows as you tighten** → tradeoff, NOT a clean free-DD-cut. Status: **WATCH / real-signal-partial-overlay** — interesting (on the live workhorse, robust PF lift) but not a confirmed clean improvement, not promotable, report-only. Band-test caught the single-threshold overclaim.

## Note
PDB is **gated for promotion, not for research.** Forge continues — but the reachable rates vein is mapped; the next serious progress is feed-gated (stage the feed to unlock the highest-EV test; this is NOT "Forge done"). Highest-EV unlock: **Treasury auctions CSV** (exact dates, not generic-calendar-inferred, not roll-stitch-dependent, economically forced, distinct from FOMC, rates-native — avoids exactly what hurt month-end).
