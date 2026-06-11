# Post-V1 Nonstop Search Queue — 2026-06-11

> **Date:** 2026-06-11 (Day 16 / 30 of sprint)
> **Authority:** Operator directive (compressed Factory Stabilization).
> **Starting size:** 10 ranked mechanisms. Extend to 15-25 only if first 10 cluster too tightly.

## Restart rules

After V1 + Phase 2 are committed:
1. Start the highest-ranked RUNNABLE_NOW branch immediately
2. Build/test/classify/document/commit
3. Failure → preserve insight, move to next branch
4. PAPER_PACKET_CANDIDATE or REVIEW → operator packet
5. NEEDS_DATA / NEEDS_CALENDAR → park, continue to next safe branch
6. NEEDS_PRIMITIVE → check infrastructure budget (10%); only build if ≥2 candidates blocked
7. Continue chain without idle gaps; surface operator packets only on triggers

## Ranked queue (10 mechanisms)

### 1. FOMC-MES-Long-1h (RUNNABLE_NOW)

| Field | Value |
|---|---|
| Archetype | TAIL_ENGINE |
| Asset | MES |
| Thesis | FOMC dovish reaction → equity rally within the announcement-to-press-conference window |
| Data required | MES_5m.csv (have) |
| Implementation cost | reuse event_window_engine |
| Expected sample size | ~50 events (58 scheduled × 93.1% clean) |
| Duplicate/family overlap risk | low — different asset from Packet #1, different event from XB-ORB probation |
| Saturation risk | NEW — never tested |
| Why different from failed paths | Different asset (MES not MGC), different event (FOMC not NFP/CPI), 1h hold (strict filter sufficient — no hold-continuity issue) |
| First bounded test | FOMC-MES-Long-1h with 12-bar hold, OFFICIAL Fed.gov calendar, V1 tail-engine gates |
| Stop condition | If PF < 1.30 or concentration > 35%, ARCHIVE |

### 2. FOMC-MNQ-Long-1h (RUNNABLE_NOW)

| Field | Value |
|---|---|
| Archetype | TAIL_ENGINE |
| Asset | MNQ |
| Thesis | Same as #1 — FOMC dovish → tech-heavy rally |
| Data required | MNQ_5m.csv (have) |
| Implementation cost | parallel to #1 |
| Expected sample size | ~50 events (93.1% clean) |
| Why different from failed paths | Different asset, different event from saturated NFP-cross |
| First bounded test | FOMC-MNQ-Long-1h with 12-bar hold |
| Stop condition | Same as #1 |

### 3. FOMC-MES/MNQ-Short-1h (RUNNABLE_NOW)

| Field | Value |
|---|---|
| Archetype | TAIL_ENGINE |
| Asset | MES, MNQ |
| Thesis | FOMC hawkish surprise → equity sell within 1h window |
| Data required | have |
| Implementation cost | parallel batch with #1 + #2 |
| Expected sample size | ~50 each |
| Why different from failed paths | Tests inverse FOMC thesis; could be the direction that works for equity micros |
| First bounded test | bundled with #1+#2 (4 candidates total) |
| Stop condition | Standard V1 tail-engine gates |

### 4. NFP-MGC-Long with profit_ladder exit (RUNNABLE_NOW)

| Field | Value |
|---|---|
| Archetype | TAIL_ENGINE |
| Asset | MGC |
| Thesis | Same NFP-MGC thesis as Packet #1 but with profit_ladder exit instead of 2h time exit |
| Data required | MGC_5m.csv (have); known data gaps |
| Implementation cost | use crossbreeding_engine with event_window entry + profit_ladder exit |
| Expected sample size | ~63 (strict-only NFP clean events on MGC) |
| Why different from failed paths | DIFFERENT EXIT ARCHITECTURE — profit_ladder may sidestep the multi-day data-gap problem (exit triggers earlier on profit, never holds through gaps) |
| First bounded test | Build via crossbreeding hybrid: NFP entry signal × ema_slope filter × profit_ladder exit |
| Stop condition | If clean-events count drops below 20 or fails tail-engine gates |
| Note | REOPENABLE_WITH_NEW_EXIT_ARCHITECTURE per Packet #1 archive |

### 5. NFP-MGC-Short with regime filter (RUNNABLE_NOW)

| Field | Value |
|---|---|
| Archetype | TAIL_ENGINE |
| Asset | MGC |
| Thesis | Pre-event drift filter conditions direction: if pre-event MGC has been UP-trending, take SHORT after NFP (mean-reversion of stretched gold); if DOWN-trending, take LONG (continuation) |
| Data required | have |
| Implementation cost | requires regime-state primitive (may already exist via ema_slope check) |
| Expected sample size | ~63 events split by regime |
| Why different from failed paths | NEW THESIS — Packet #1 was direction-blind. This adds an explicit pre-event regime filter |
| First bounded test | Use existing ema_slope filter as proxy for regime |
| Stop condition | Standard V1 tail-engine gates |

### 6. ZN session-open momentum (RUNNABLE_NOW)

| Field | Value |
|---|---|
| Archetype | WORKHORSE |
| Asset | ZN |
| Thesis | Rates have specific session-boundary behavior at NY 08:00 ET cash open (vs futures 18:00 ET prior day). Test whether overnight-to-open direction continues during early NY session. |
| Data required | ZN_5m.csv (have, CLEAN_EVENT_READY) |
| Implementation cost | new entry primitive (session-open momentum, threshold on first-30-min return) |
| Expected sample size | ~2000 sessions × 8 yrs |
| Why different from failed paths | Different asset class (rates), different mechanism (session boundary), workhorse archetype — escapes tail-engine concentration trap |
| First bounded test | Define momentum as sign(open - prev_close); long/short continuation; 1h hold |
| Stop condition | Standard V1 workhorse gates |

### 7. VIX-spike event-window on MES (NEEDS_PRIMITIVE)

| Field | Value |
|---|---|
| Archetype | TAIL_ENGINE |
| Asset | MES |
| Thesis | VIX spikes (>30) signal capitulation; MES mean-reverts within 2-4 day window |
| Data required | VIX historical data (does not currently exist in data/processed) |
| Implementation cost | requires VIX threshold primitive + cross-data join |
| Expected sample size | ~40 events 2019-2026 |
| Status | NEEDS_PRIMITIVE (VIX threshold detector); NEEDS_DATA (VIX 5min historical) |
| Stop condition | If VIX data unavailable, defer |

### 8. Retail Sales release on MGC/MES (NEEDS_RESEARCH)

| Field | Value |
|---|---|
| Archetype | TAIL_ENGINE |
| Asset | MGC, MES |
| Thesis | Census Bureau Retail Sales release (mid-month, 8:30am ET) is a smaller-magnitude macro shock — directional impact on gold/equities |
| Data required | retail sales calendar (operator-verifiable from census.gov) |
| Implementation cost | new calendar source needed |
| Status | NEEDS_RESEARCH (calendar source verification) |
| Stop condition | If calendar grade < MACHINE_FETCHED_OFFICIAL after operator review, defer |

### 9. EIA Crude inventory on MCL (NEEDS_DATA)

| Field | Value |
|---|---|
| Archetype | TAIL_ENGINE |
| Asset | MCL |
| Thesis | EIA Wednesday 10:30am ET crude inventory release; MCL directional response within 2h window |
| Data required | MCL pre-2021 data (currently DATA_REQUIRED status) |
| Implementation cost | EIA calendar already exists (`research/forge_eia_crude_calendar.py`) |
| Status | NEEDS_DATA (MCL data file extension) |
| Stop condition | Defer until MCL data available |

### 10. Cross-asset spike propagation: MGC → MES on macro days (NEEDS_RESEARCH)

| Field | Value |
|---|---|
| Archetype | TAIL_ENGINE (event-conditioned cross-asset) |
| Asset | MES (signal) ← MGC (catalyst) |
| Thesis | When MGC moves > N std devs during NFP/CPI/FOMC window, MES follows X minutes later (USD-driven correlation lag) |
| Data required | both files (have) |
| Implementation cost | new cross-asset propagation primitive |
| Status | NEEDS_RESEARCH (define propagation methodology, lag window, threshold) |
| Stop condition | Standard V1 gates after first bounded test |

## Diversity check

| Mechanism class | Count |
|---|---:|
| Event-window (FOMC) | 3 (#1, #2, #3) |
| Event-window (NFP variants) | 2 (#4, #5) |
| Session/momentum workhorse | 1 (#6) |
| Volatility-event | 1 (#7) |
| Other-event window | 2 (#8, #9) |
| Cross-asset propagation | 1 (#10) |

**Concern:** 5 of 10 are event-window candidates, which is the family that just saturated. **Mitigation:** they are on different assets (MES, MNQ) OR different events (FOMC vs NFP) OR different mechanisms (PL exit, regime filter). Per saturation doctrine, these are narrow-saturation REOPEN paths, not duplicates.

Per operator policy: if first 10 cluster too tightly on event-window theme, will extend to 15-25 with more workhorse / non-event mechanisms.

## Execution priority

**Immediate first batch (combined to reduce idle):** #1 + #2 + #3 (FOMC-MES + FOMC-MNQ long + short, single cycle script).

After classification: #4 (NFP-MGC profit_ladder), then #5 (NFP-MGC regime filter), then #6 (ZN session-open momentum).

NEEDS_X items stay queued for operator authorization or data unblock.
