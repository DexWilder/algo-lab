# Daily Test 2 — Harness Methodology Spec (2026-06-12)

> **Authority:** Operator #202 C (harness-first mandate, then A).
> **Status:** Spec doc — code follows in stages. Harness module + risk-accounting BEFORE any failed_daily_breakout primitive build.
> **Key principle:** "Harness first. Strategy second. No intraday-exit fake daily systems."
> **Lesson driving this:** Test 1 (cycle 12j) showed that prior_day_break/fade with profit_ladder exits hold only 14-28 bars (1-2.4 hours). They reference daily LEVELS but execute intraday. They are not timeframe-diversifying.

## §1 — Daily-Bar Construction

### Source bars

5-minute bars from `data/processed/{ASSET}_5m.csv` aggregated to **session bars**:
- Open = first session bar's open (09:30 ET)
- High = max(high) over RTH session (09:30-16:00 ET)
- Low = min(low) over RTH session
- Close = last RTH bar's close (15:55 or 16:00 ET, whichever exists)
- Volume = sum of RTH bar volumes
- Bar timestamp = session date

**Decision:** Use RTH-only session bars (09:30-16:00 ET). Globex/overnight bars NOT aggregated into the daily bar. This matches how prop-firm execution typically thinks about session.

### Session close convention

- RTH close = 16:00 ET. If bar at 16:00 missing, use last bar before 16:00 within the session.
- Signal evaluation occurs at session close — entry executes NEXT session's open.

### Contract roll handling

Current `data/processed/{ASSET}_5m.csv` is the **continuous contract** (already roll-adjusted per FQL convention). No new roll logic needed at the daily-bar level. Document that roll-adjustment is inherited from the data feed.

### No-lookahead on failed-break confirmation

For failed_daily_breakout entry:
- "Break" defined at session close on day T
- "Failure" defined at session close on day T+1 (i.e., daily close back inside prior-day range)
- Entry triggers at OPEN of day T+2

**Strict rule:** confirmation must use ONLY closed-session data. Never look at intraday data of the confirmation day.

## §2 — Entry Timing

### Entry execution rule

Entries fire at the **OPEN** of the trading session FOLLOWING confirmation:
- Confirmation completes at 16:00 ET on day T (session close)
- Entry executes at 09:30 ET on day T+1 session open
- Entry PRICE = open of the 09:30 5-min bar on day T+1

### Overnight gap handling

The entry price is the next-session open (after gap risk has already realized). The strategy DOES NOT take overnight risk between confirmation close and entry open — the position doesn't exist yet during that period.

### Bar continuity check

Per [[feedback_hold_continuity_canonical_filter]] doctrine for hold-window strategies:
- Confirmation day T close must exist
- Entry day T+1 open must exist
- Each day within the hold window must have at least one RTH bar (otherwise the trade is excluded as "data-incomplete")

## §3 — Exit Engine (NEW MULTI-DAY EXIT MODULE)

This is the new harness component. Per operator: "No profit_ladder exit for Test 2. This must be true daily/multi-day holding logic."

### Module: `multi_day_exit` (new file: `engine/multi_day_exit.py`)

Pre-declared exit variants (operator-approved up front, no post-hoc additions):

#### Variant A: `fixed_3_day_hold`

- Exit at OPEN of session N+3 (where N is entry session)
- 3 daily bars of holding (~3 trading days)
- Exit price = open of day N+3

#### Variant B: `fixed_5_day_hold`

- Exit at OPEN of session N+5
- 5 daily bars of holding
- Exit price = open of day N+5

#### Variant C: `daily_invalidation_exit`

- Exit at OPEN of session N+1 if daily close on session N is on the wrong side of an "invalidation level"
- Invalidation level defined per-strategy (e.g., for failed_daily_breakout long: invalidation = prior-day high; if close < prior-day high, position is invalidated)
- Combine with a MAX-hold of 5 days as upper bound

#### Variant D (optional, only if pre-declared): `daily_trailing_stop`

- Trailing stop ratcheted on daily bars (not 5-min)
- Initial stop = entry-day low (for long) or high (for short)
- After each daily close beyond ratchet threshold, advance stop by N% of prior day range
- Use only if explicitly listed in the test plan before running

### No combination of exit variants in a single test

One variant per test. No "let me try with daily_trailing_stop instead" loops.

## §4 — Risk Accounting (EXPANDED PER OPERATOR)

Every Test 2 candidate report MUST include these fields. Non-negotiable.

### Per-trade risk metrics

| Metric | Definition |
|---|---|
| `worst_overnight_gap_per_trade` | Absolute price difference between session N close and session N+1 open, normalized to PnL terms, worst case across all trades held overnight |
| `largest_single_day_loss` | Maximum loss within a single session N (open-to-close or peak-to-trough on the day) across all trade-days |
| `worst_close_to_open_loss` | Max loss attributable to overnight gap (close session N → open session N+1) across all trade-overnight events |
| `worst_open_to_open_loss` | Max loss across a full 24-hour open-to-open period within a held trade |
| `max_adverse_excursion_during_hold` | Worst unrealized loss at any point during a trade's hold period |
| `max_cumulative_unrealized_loss` | Worst point-in-time cumulative drawdown of the strategy equity curve |

### Event-day exposure

| Metric | Definition |
|---|---|
| `event_day_exposure_count` | Number of trades held overnight on NFP / CPI / FOMC announcement days |
| `event_day_exposure_pct` | Same as % of all trade-overnight events |
| `pct_trades_with_fomc_exposure` | % of trades with at least one FOMC announcement during hold |

### Hold duration

| Metric | Definition |
|---|---|
| `avg_hold_trading_days` | Mean hold in trading sessions |
| `max_hold_trading_days` | Max hold in trading sessions |
| `avg_hold_calendar_days` | Mean hold in calendar days |
| `max_hold_calendar_days` | Max hold in calendar days (weekends included) |
| `overnight_exposure_pct` | % of trade-time when position is held overnight |

### Concentration

| Metric | Definition |
|---|---|
| `top_1_trade_pct_of_net` | % of total net contributed by largest single winning trade |
| `top_3_trades_pct_of_net` | Sum of top 3 winners as % of net |
| `top_10_trades_pct_of_net` | Sum of top 10 winners as % of net |
| `max_year_share_pct` | Single-year contribution to net (existing V1 metric) |
| `instance_cv` | Std/mean of per-year nets (existing V1 metric) |

### Prop-firm compatibility note

Each candidate report must include a 1-paragraph note:
- Is the worst single-day loss compatible with a typical $2,000-$3,000 daily loss limit (e.g., Tradeify daily DD)?
- Is the worst open-to-open loss compatible with a typical $5,000-$10,000 trailing drawdown?
- What's the max consecutive losing trade days streak?

This is operator-facing risk evidence, not gate criteria — but flags candidates that would fail prop-firm rules even if V1 gates pass.

## §5 — Success Criteria

### Archetype routing by sample size

- Workhorse if n ≥ 500 → V1 workhorse gates
- Tail-engine if n < 500 → V1 tail-engine gates

### Mandatory pass requirements (in addition to archetype gates)

1. Positive median trade
2. Top-1 trade ≤ 15% of net (no lucky-event carry)
3. Top-10 trades ≤ 50% of net
4. Max-year share ≤ 50% (workhorse) / 35% (tail-engine)
5. Family review vs all 4 Lane A candidates AND XB-ORB-MNQ probation; max corr < 0.50 (lower bar than intraday to acknowledge that any daily strategy will share some macro-day movement)
6. Worst-overnight-gap NOT exceeding 3× average winning trade size (catastrophic-gap protection)
7. Outlier sensitivity: remove largest WIN AND largest LOSS, PF still meets archetype threshold

### Soft flags (report, don't fail)

- Era 3 median (per V1.1-B doctrine for tail engines)
- DOW/month concentration patterns
- Event-day exposure %

## §6 — Anti-Curve-Fit Rules

1. **No threshold tuning before baseline.** Pre-declared parameters fixed; no sweep until baseline meets criteria.
2. **No trying multiple exits to save one entry** unless exits were pre-declared from the start (variants A-D listed in §3).
3. **No preserving a candidate by changing confirmation timing** after seeing results.
4. **If baseline fails with negative median AND PF below threshold, archive the thesis.** No "let me try with a stop adjustment."
5. **If positive median but PF thin (1.15-1.20 range), classify WATCH/OBSERVATIONAL only.** Don't add filters to push it over.
6. **One asset at a time.** MNQ first. MES only if MNQ shows life. No "let me run both in parallel to save time."

## §7 — Build sequence (per operator C→A)

| Stage | Deliverable | Dependencies |
|---|---|---|
| **Stage 1 (today, post-spec approval)** | `engine/multi_day_exit.py` module with variants A-D | None |
| Stage 1.5 | Risk-accounting reporter (helper functions) | Module |
| Stage 2 | `entry_failed_daily_breakout` primitive | Daily-bar features in compute_features |
| Stage 3 | `forge_cycle_2026-06-13a_daily_test2_failed_breakout_MNQ.py` — first MNQ test | Stages 1+2 |
| Stage 4 (conditional) | MES port of failed_daily_breakout | Stage 3 shows life |
| Stage 5 (conditional) | inside_day_expansion, weekly_range_compression, 3_day_momentum primitives | Stage 3 shows life |
| Stage 6 (conditional) | Pivot to event-conditioning or vol-regime work | If Stage 3 fails hard |

## §8 — Build estimate

Realistic Lane B effort:
- Stage 1 (multi_day_exit module): ~30-60 min coding + tests
- Stage 1.5 (risk reporter): ~30-60 min
- Stage 2 (failed_daily_breakout entry): ~30 min coding
- Stage 3 (first test): ~10-20 min runtime + report
- Total to first MNQ verdict: ~2-3 hours of active work

This is meaningful Lane B investment vs the 5-minute Test 1 we just ran. Justified by:
- Test 1 produced a CONTAMINATED result (intraday exits on daily levels)
- A proper daily-timeframe verdict (positive or negative) requires honest exits
- A failed_daily_breakout candidate that passes V1 + risk accounting would be the FIRST true timeframe-diversifier for the Lane A portfolio

## §9 — What this spec does NOT do

- ❌ Does NOT mutate any Lane A candidate
- ❌ Does NOT pre-commit to a candidate result
- ❌ Does NOT define the failed_daily_breakout entry primitive in detail (Stage 2 spec, separate)
- ❌ Does NOT authorize Stages 4-6 — those are conditional on Stage 3 outcomes

## §10 — Operator decision

After this spec:
- (A) Proceed with Stage 1 (multi_day_exit module) immediately, then Stages 1.5-3 sequentially
- (B) Modify spec (e.g., adjust risk-accounting metrics, change exit variants)
- (C) Approve + Forge picks first variant to test (A, B, or C)
- (D) Defer for in-person review

Standing for operator response before any code.

## Cross-reference

- `docs/fql_forge/daily_timeframe_primitive_methodology_2026-06-12.md` — sibling Test 1 methodology
- [[feedback_hold_continuity_canonical_filter]] — applies to multi-day strategies too
- [[feedback_evidence_integrity_failsafe]] — fail-closed plumbing rule
- [[packet_standard_v1]] — base gates spec
- [[packet_standard_v1_1_amendments]] — V1.1 doctrine
