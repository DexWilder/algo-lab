# Next Search Basis Selection Note — 2026-06-10

> **Status:** Per operator decision #126. Compare 7 candidate mechanism families against 6 criteria; recommend one bounded next-build while prop-cost data pending.
> **Authority:** Lane B research-only. Recommendation only; build proceeds only after operator approval.

## Selection criteria (operator-specified)

1. **Mechanism novelty** — distance from already-tested mechanism families
2. **Data availability** — uses existing features vs requires new ingestion
3. **Expected sample size** — adequate for statistical resolution
4. **Prop-cost margin potential** — per-trade $ size relative to typical cost ladder
5. **Likelihood of non-duplicate exposure** — independence from existing probation
6. **Ability to test with current infrastructure** — minimal vs significant new build

## 7-candidate comparison matrix

| # | Candidate | Novelty | Data | Sample | Cost margin | Non-dup | Infra | Score |
|---:|---|---|---|---|---|---|---|---:|
| 1 | opening_drive_continuation | LOW-MED | existing | HIGH | LOW (ORB-family overlap) | LOW (ORB family) | minimal | ★★ |
| 2 | **continuation/fade after abnormal range day** | **HIGH** | **existing (prior_day_high/low)** | **MOD (~150-200/yr/asset)** | **HIGH (sparse = larger per-trade)** | **HIGH** | **minimal** | **★★★★★** |
| 3 | overnight range breakout/fade (Asian/Europe range) | HIGH | needs new feature | MOD | MED | HIGH | small build | ★★★★ |
| 4 | liquidation/reclaim reversal (stop_run redesign) | MED (#118 chain redo) | existing | TBD (depends on multi-bar logic) | TBD | HIGH | moderate build | ★★★ |
| 5 | session_close / settlement behavior | HIGH | existing (session_close filter) | HIGH (~500+/yr) | LOW-MED (high-freq → small per-trade) | HIGH | minimal | ★★★★ |
| 6 | macro/metals-specific event variants (CPI-MGC, FOMC-MGC, PPI-MGC) | MED (Packet #1 family extension) | existing event_window | LOW (event-conditioned) | **VERY HIGH (event = large per-trade)** | MED (NFP-MGC family) | minimal | ★★★★ |
| 7 | rates-native curve/carry (2s10s, ZN/ZF/ZB cross) | HIGH | needs cross-asset/pair engine work | MOD | LOW (rates = small per-trade $) | HIGH | significant build | ★★★ |

## Detailed candidate analysis

### Candidate 1: opening_drive_continuation (SMP-3 Tier 2 last)

- **Thesis:** sustained morning move + pullback + continuation entry
- **Mechanism similarity to ORB:** high — same morning session window, same direction-of-strength bet
- **Duplicate risk vs XB-ORB-EMA-Ladder family:** HIGH — would family-review against MNQ/MES/MYM probation
- **Expected outcome:** PORTFOLIO_COMPLEMENT or DIRECTIONAL_INSIGHT at best; low Packet #2 probability
- **Verdict: NOT recommended** — too similar to existing probation family

### Candidate 2: continuation/fade after abnormal range day (RECOMMENDED)

- **Thesis:** prior-day total range (high - low) was abnormally large (top quintile of recent 60-day distribution); next-day either continues the regime shift OR reverts toward the prior multi-day mean
- **Mechanism:** different from all 5 tested families (compression, vol-regime, squeeze, gap-fade, sweep-reversal). Operates on DAILY range stats, triggers on FOLLOWING day.
- **Implementation:** add `prev_day_range` and `prev_day_range_pctrank_60` as features (cheap). Entry primitive: at session open of day N+1, if prev_day_range_pctrank ≥ 80, enter direction-of-yesterday's-close (continuation) OR opposite (fade). First batch tests both modes.
- **Expected sample size:** abnormal-range days ≈ 20% of trading days = ~50/yr per asset. With 8 years data ≈ 400 candidates per asset (across MES/MNQ/MYM/MGC/MCL).
- **Cost-margin potential:** sparse signals historically produce larger per-trade $ (similar to event-window candidates). NFP-MGC pattern: ~$25 median trade vs ORB family $5-$10.
- **Non-duplicate exposure:** entirely different from existing probation. ORB triggers on RTH range; PB triggers on pullback; this triggers on PRIOR DAY's range pctrank.
- **Infrastructure:** ~2-3h build (feature + entry primitive + smoke tests). Reuses existing PL exit + ema_slope filter.
- **Filter pre-flight (#120):** Thesis is continuation OR fade. Test both modes in first batch with `filter=none` (avoid pre-judging direction-trend alignment).
- **Verdict: RECOMMENDED PRIMARY** — best combined score across all criteria. HIGH novelty + MOD sample + HIGH cost-margin potential + HIGH non-duplicate + minimal infrastructure.

### Candidate 3: overnight range breakout/fade

- **Thesis:** overnight session (Asian + European hours) produces a range; RTH open breaks above/below → continuation; OR fade back to overnight range center
- **Data:** would need new feature `overnight_range_high/low` (calculated from non-RTH bars). Not currently in features.
- **Sample size:** every day has an overnight range = ~250/yr per asset
- **Cost margin:** similar to opening drive — high frequency, small per-trade
- **Duplicate risk:** LOW — no current overnight strategy
- **Infrastructure:** small build (~3-4h for feature engineering)
- **Verdict: STRONG SECONDARY** — slightly worse than #2 on cost-margin (higher frequency), slightly more infra work.

### Candidate 4: liquidation/reclaim reversal (stop_run_reversal redesign)

- **Thesis:** multi-bar version of stop_run_reversal — sweep + 3-5 bar reversal confirmation, plus session-high/low liquidity context instead of 20-bar Donchian
- **Implementation:** requires redesigned state machine (track sweep events, count post-sweep reversal bars, confirm reversal magnitude)
- **Infrastructure:** moderate build (~4-6h)
- **Expected outcome:** uncertain — might rescue the mechanism, might confirm same failure pattern
- **Verdict: BACKUP** — only worth doing if #2 + #3 both fail. Per operator: "Do not run a quick retry unless the mechanism is redesigned."

### Candidate 5: session_close / settlement behavior

- **Thesis:** last-30-min directional bias around settlement
- **Sample size:** every day = ~500/yr per asset
- **Cost margin:** small per-trade (high frequency)
- **Verdict: SECONDARY** — strong novelty but cost-margin profile likely similar to ORB family (thin per-trade $ that fails prop-stress).

### Candidate 6: macro/metals-specific event variants (CPI-MGC, FOMC-MGC, PPI-MGC)

- **Thesis:** extend Packet #1 NFP-MGC template to other macro events on MGC
- **Operator constraint:** explicitly said "do not restart broad FOMC/CPI equity-index event sweeps" but DID NOT exclude metals-specific event extensions
- **Cost margin:** HIGH — event candidates produce large per-trade $ (NFP-MGC packet has $25 median)
- **Sample size:** LOW — ~10-12 events/year per type
- **Duplicate risk vs NFP-MGC:** MED — different event timing means different overlap probability; family-review required
- **Infrastructure:** existing event_window_engine + verified calendars for FOMC/CPI/PPI
- **Verdict: SECONDARY-STRONG** — high cost-margin potential could be the unlock alongside BBKC-MNQ. But operator's restriction language is ambiguous (equity-index excluded; metals-specific possibly allowed). Should defer to operator clarification.

### Candidate 7: rates-native curve/carry

- **Thesis:** 2s10s curve trades (ZN vs ZF spread) or 5s30s (ZF vs ZB)
- **Infrastructure:** significant — need cross-asset pair engine + cointegration validation + carry signal construction
- **Cost margin:** LOW — rates are smaller-dollar instruments
- **Verdict: NOT recommended** — significant infrastructure cost; uncertain payoff.

## Recommendation: Candidate #2 (continuation/fade after abnormal range day)

**Reasons:**
1. **Highest novelty** vs all 5 tested mechanism families (compression, vol-regime, squeeze, gap-fade, sweep-reversal)
2. **HIGH non-duplicate** — no current strategy operates on daily-range pctrank
3. **HIGH cost-margin potential** — sparse signals typically produce $20-30 median per trade (vs ORB family $5-10)
4. **Minimal infrastructure** — 2 new features + 1 entry primitive (~2-3h build incl. smoke tests)
5. **Filter pre-flight compatible** — thesis is bidirectional (continuation OR fade); first batch tests both modes with `filter=none`
6. **Adequate sample size** — ~50 abnormal-range days/year/asset × 5 assets × 8 years = ~2000 total candidates

### Proposed first-batch spec (if operator approves)

| Asset | Mode | Filter | Exit | Notes |
|---|---|---|---|---|
| MES | continuation | none | profit_ladder | LONG if prev day closed > prev day midpoint; mirror for short |
| MES | fade | none | profit_ladder | Opposite direction of prev day's closing direction |
| MNQ | continuation | none | profit_ladder | |
| MNQ | fade | none | profit_ladder | |
| MGC | continuation | none | profit_ladder | Metals — different cost regime |
| MGC | fade | none | profit_ladder | |
| MCL | continuation | none | profit_ladder | |
| MCL | fade | none | profit_ladder | |

8 candidates. Operator-decision matrix as before: PASS_STRESS + clean concentration → family review → 8-dim audit. Strict gates apply.

## Constraints

- No registry mutation. No scheduler change. No portfolio allocation change.
- No paper/live promotion. No OpenClaw upgrade.
- No cost-assumption changes without operator-verified data.
- BBKC-MNQ remains CONDITIONAL PRE-PACKET / OBSERVATIONAL pending operator prop-cost verification — NOT promoted.
- Build proceeds only after operator approval of recommended candidate.

## Source artifacts

- `research/data/fql_forge/source_mining_packet_3_2026-06-09.md` (predecessor catalog)
- `research/data/fql_forge/kill_taxonomy.json` (campaign trail of 5 archived/research-only primitives)
- `research/data/fql_forge/reports/forge_cycle_2026-06-09e_break_even_analysis.json` (cost-fragility evidence)
- `docs/fql_forge/paper_packet_drafts/BBKC-MNQ-Both-PL_PRE_PACKET_SCAFFOLD.md` (conditional pre-packet)
