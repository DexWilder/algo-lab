# Daily-Timeframe Primitive Methodology — 2026-06-12

> **Authority:** Operator #198 C (2026-06-12). Methodology first; bounded first batch after.
> **Status:** Lane B research design note. No new code yet.
> **Strategic question:** Can a daily-timeframe primitive produce a genuinely different exposure profile from the current MNQ intraday workhorses — lower frequency, different rhythm, lower correlation by construction?

## Why this is the right Lane B direction

After Lane A produced 3 GREEN MNQ intraday workhorses + 1 event-tail, two cross-asset hypotheses tested NEGATIVE (mes_alignment, ZN port). The simple intraday-MNQ family is saturated for new elite candidates by intraday-mechanism variation. The strongest remaining diversification lever is **holding period / timeframe**, not asset.

Daily-timeframe mechanisms by construction have:
- Different correlation to intraday (different trade timing)
- Different exposure profile (overnight risk vs intraday flat)
- Lower trade frequency (different sample-size statistics)
- Potential to use intermarket / multi-day context that intraday primitives can't see

## Daily primitive families (operator-suggested + ranked)

| # | Family | Existing? | Cost | Theory |
|---|---|---|---|---|
| 1a | `prior_day_break` (BREAKOUT) | **Already in engine** | TRIVIAL | Long > prior-day high; short < prior-day low — classic Donchian-style daily breakout |
| 1b | `prior_day_fade` (REVERSION) | **Already in engine** | TRIVIAL | Fade prior-day high/low — mean-reversion variant |
| 2 | Failed daily breakout / close-back-inside | NEW primitive needed | moderate | Break prior-day H/L fails to hold → reverse |
| 3 | Weekly range compression breakout | NEW (needs weekly aggregation) | moderate | 5-day range tight → directional break |
| 4 | 3-day momentum continuation | NEW | moderate | 3-day directional drift → continuation |
| 5 | Inside-day expansion | NEW | moderate | Yesterday's range inside day-before → today's range expansion |

**Critical:** primitives 1a and 1b already exist. They should be tested FIRST as the cheapest probe of whether daily mechanisms work AT ALL on MNQ/MES. If they fail, the more sophisticated daily primitives (2-5) face an uphill battle and the "new mechanism class outside saturated lane" assumption needs revisiting.

## Pre-declared success criteria

Daily primitives trade less frequently — n statistics will differ from intraday.

### Workhorse archetype gates (n ≥ 500 cumulative trades)

Applied if primitive fires at least 500 times over 8 years:
- PF ≥ 1.20
- positive median
- PASS_STRESS (2× cost + 2 ticks slip)
- max-yr ≤ 50%
- yrs+ ≥ 50%
- Era 3 PF ≥ 1.0
- Era 3 median ≥ 0

### Tail-engine archetype gates (n < 500)

Applied if primitive is genuinely sparse:
- n ≥ 20
- PF ≥ 1.30 STRONG
- stress PF ≥ 1.30
- max single instance ≤ 35%
- positive instance frac ≥ 60%
- instance CV ≤ 3.0
- Era 3 PF ≥ 1.0

### Daily-specific instrumentation

For each candidate, report:
- Average hold time (bars per trade — daily mechanisms may hold for days)
- Overnight exposure fraction (% of trade time when position is held overnight)
- Calendar correlation (does the strategy concentrate on certain DOW or month patterns?)

## Pre-declared anti-curve-fit guardrails

1. **One primitive family at a time.** Don't sweep multiple at once before reading baseline.
2. **Default parameters first.** No threshold tuning until baseline is honest.
3. **Same filter / exit family as intraday workhorses** (ema_slope + profit_ladder) for fair comparison initially.
4. **Honest correlation check.** Must report correlation vs all 4 Lane A candidates AND XB-ORB-MNQ probation.
5. **No discretion to preserve.** If a primitive fails criteria, archive immediately.
6. **Daily primitives are NOT additive to intraday primitives** unless family review confirms low correlation. A daily primitive that overlaps 80% with intraday on event days isn't a portfolio diversifier.

## First-batch plan (smallest blast radius)

**Test 1 (cheapest — uses existing primitives):**
- prior_day_break × MNQ × ema_slope × profit_ladder
- prior_day_break × MES × ema_slope × profit_ladder
- prior_day_fade × MNQ × ema_slope × profit_ladder
- prior_day_fade × MES × ema_slope × profit_ladder

4 candidates, ~5 minutes of compute. Honest probe of whether daily mechanisms work at all in current MNQ/MES microstructure.

**Branch decisions:**
- If ≥ 1 PAPER_PACKET_CANDIDATE surfaces with family corr < 0.30 to Lane A: ratify daily-mechanism lane is viable, proceed to Test 2 (more sophisticated daily primitives)
- If all 4 KILL but with positive medians: daily mechanism is borderline; investigate stronger filters
- If all 4 KILL with negative medians: daily mechanism doesn't work on MNQ/MES with these primitives; archive direct-port daily thesis

**Test 2 (only if Test 1 shows life):**
Build NEW primitives in priority order:
- failed daily breakout / close-back-inside (most theoretically distinct from existing prior_day_break)
- inside-day expansion
- weekly range compression breakout (requires weekly aggregation in feature dict)
- 3-day momentum continuation

## What this methodology does NOT do

- ❌ Does NOT change Lane A candidates
- ❌ Does NOT pre-commit to building any NEW daily primitive until Test 1 informs
- ❌ Does NOT mutate existing primitive code (only ADDS new primitives if Test 2 fires)
- ❌ Does NOT test cross-asset filters again (per #199 mes_alignment archived)

## Why prior_day_break/fade first (cheap inspection)

The existing primitives use `prev_day_high` / `prev_day_low` features already in the engine. Running them as workhorse candidates with the current Lane A filter+exit stack is a zero-new-code test.

**Operator-relevant context:** prior_day_break was used in earlier sprint work but has not been V1-audited under the current archetype-correct gates. This test will produce a clean V1 verdict.

## Operator decision

After this methodology, operator may:
- (A) Proceed with Test 1 (4 candidates) immediately
- (B) Modify methodology (e.g., start with weekly range instead)
- (C) Approve methodology + authorize Forge to choose first test
- (D) Defer for in-person review

Standing for operator response before running Test 1.

## Cross-reference

- [[packet_standard_v1]] — archetype-correct gates
- [[packet_standard_v1_1_amendments]] — V1.1 doctrine
- `docs/fql_forge/cross_asset_confirmation_methodology_2026-06-12.md` — sibling methodology (now archived hypothesis per #199)
- [[feedback_asset_family_saturation_rule]] — narrow saturation framework
- `docs/fql_forge/paper_packet_drafts/LANE_A_BATCH_2026-06-12.md` — Lane A candidates being protected
