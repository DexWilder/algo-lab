# Forced-Flow Mechanism Packets — 2026-06-22

> Discipline: NO "one-variable-z-score → long ZN tomorrow" screens. Each packet names the forced PARTICIPANT, why it implies a SPECIFIC direction+timing, instruments, no-lookahead, cheap-screen spec, kill criteria. Direction comes from the mechanism, not fishing. Simple directional expressions already KILLED (SOFR-EFFR→rates; vanilla auction windows) — these are richer/conditional. Report-only; build-before-test.

## P-RRP — RRP drawdown / liquidity-drain state
- **Forced participant:** money funds shifting OUT of overnight RRP into bills/repo/Treasuries as the cash glut drains.
- **Implied effect+direction:** falling RRP volume = liquidity leaving the parking facility → front-end/bill demand, possible curve & risk-on/off state. NOT a clean directional bond entry → better as a **regime/risk state**, not a long-ZN signal.
- **Feed:** funding.csv (RRPONTSYD, 2003+). **Cheap screen:** RRP-volume *trend-state* as a FILTER on existing books (does an edge concentrate in draining vs glut regimes?), not standalone direction. **Kill:** no regime separation / overfit.

## P-WALCL — balance-sheet QT/QE contraction
- **Forced participant:** Fed balance-sheet runoff (QT) removes a price-insensitive buyer → net duration supply rises.
- **Implied effect:** QT = structural headwind for bonds (regime), QE = tailwind. **Regime filter, NOT standalone entry** (weekly, slow).
- **Feed:** funding.csv (WALCL weekly). **Cheap screen:** QT-vs-QE regime (WALCL 13w change sign, lagged) as a FILTER on rates books / the FOMC-week sleeve. **Kill:** no regime conditioning value.

## P-SOMA — Fed operation-day tenor pressure
- **Forced participant:** Fed buying/selling/reinvesting SPECIFIC tenors on operation days (price-insensitive flow).
- **Implied direction:** Fed *buying* a tenor on op-day → that tenor's future bid (long ZN/ZF/ZB matched to operated tenor, op-day window). Direction implied by buy/sell side.
- **Feed:** NY-Fed Markets API (treasury ops; check op-level history depth + buy/sell + tenor). **Cheap screen:** matched-tenor future on operation-day window, by side. **Kill:** sparse / no edge / can't get clean op-level history.

## P-AUC-RESULT — auction-result-conditioned reaction (data in hand)
- **Forced participant:** dealers absorbing a WEAK (low bid-to-cover / tailing) auction must distribute inventory → post-auction concession persists/extends; a STRONG auction → relief rally.
- **Implied direction:** weak result → SHORT matched-tenor T0→T+1/2; strong result → LONG. **Post-results only (no pre-result lookahead).** This is the untested branch after vanilla-window KILL.
- **Feed:** treasury_auctions.csv (+ re-pull bid_to_cover_ratio / high_yield). **Cheap screen:** split post-auction reaction by demand strength (bid-to-cover tercile / yield-tail proxy), by tenor, contamination-clean. **Kill:** no separation between weak/strong auctions, or both KILL.

## P-SLEEVE — bench-construction report (not a new strategy)
- **Purpose:** WH2 unfound → quantify whether banked event/tail/overlay finds improve the TOTAL bench (correlation, overlap, drawdown sequencing) without pretending they're daily workhorses.
- **Inputs (in hand):** FOMC-week rates, FOMC-MNQ-1h, pre-holiday equity, MGC-prior_day_break, MGC-ORB low-vol overlay vs incumbents (MNQ-ORB/stop_run, MGC-ORB). **Report:** pairwise daily-PnL corr, bad-day overlap, combined DD sequencing, does adding each reduce combined DD / improve combined PF. **No promotion/wiring.**

## Priority to run (cheap + participant-implied direction + data-in-hand)
1. **P-AUC-RESULT** — data in hand (re-pull bid_to_cover), direction mechanism-implied, natural follow-on to the vanilla KILL.
2. **P-SLEEVE** — pure report-only, in-hand, concrete value while WH2 unfound.
3. P-WALCL / P-RRP — regime-FILTER framing only (not standalone direction).
4. P-SOMA — needs NY-Fed op-level history check first.

## RESULTS
- **P-AUC-RESULT → KILL (`forge_cycle_2026-06-22i`).** Demand (bid-to-cover vs tenor trailing norm) → matched future T0(post-results)→T+2. Mechanism-implied direction (strong→long/weak→short) is WRONG: PF 0.51-0.72 net-negative ALL tenors; BOTH sides lose (strong-long 0.31-0.83, weak-short 0.66-0.81). **Did NOT flip to chase inverse** (no forced-participant story for strong→short = would be fishing). → auctions now dead across **vanilla windows AND result-conditioned daily reactions**. Only intraday-auction-time + curve/yield-tail variants remain (more speculative, need more fields). The auction WH2 vein is largely exhausted for daily-directional.
- P-SLEEVE → NEXT (report-only bench-construction, in-hand, no fishing risk).
- P-RRP / P-WALCL / P-SOMA → pending (regime-filter framing; SOMA needs op-level history check).

## Boundaries
Build-before-test; report-only; no wiring/promotion/mutation; no z-score-direction fishing; no post-hoc direction-flipping.
