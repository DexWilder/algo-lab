# Pool-Expansion Packet — `convert_next` / `cleared_to_convert` Candidates

**Filed:** 2026-05-19
**Authority:** T1 (intelligence packet; no truth mutation)
**Lane:** 1 (reversible Lane B research; no registry / runner / engine changes today)
**Status:** DRAFT — ranks the 10 convert-next candidates, recommends the next Forge runner batch, surfaces the real bottleneck.
**Related:** `_DRAFT_2026-05-19_sentinel_v0_preflight.md`, `_BACKLOG_post_patch_a_and_phase_1_exit.md` (Paper-Readiness Sprint)

---

## Why this packet exists

GPT pushed back on staying stuck at ~60 cheap-screened strategies. The supply-chain audit found 88 `idea` rows in the registry but only 19 in the Forge runner pool — a 78-deep tail of registered-but-untested ideas. The visible subset that the registry has explicitly tagged as ready to convert is **10 candidates**. This packet ranks them, recommends the next batch, and — most importantly — surfaces what's actually blocking conversion.

**Headline finding (deeper than "operator caution"):** 7 of the 10 candidates require entry/exit mechanisms that **do not exist** in the crossbreeding engine. The "convert_next" tag was applied at intake time and reflects *thesis* readiness, not *harness* readiness. So the bottleneck at ~60 strategies is partly an engine inventory limit, not just runner-pool throttling.

---

## 1. The 10 candidates

| # | strategy_id | family | asset | session | dir | source | engine fit |
|---|---|---|---|---|---|---|---|
| 1 | VWAPPullback-MES-Long | pullback | MES | morning | long | practitioner_composite | ✅ approximate via `pb_pullback` + `vwap_slope` filter |
| 2 | BBW-Percentile | vol_expansion | M2K | all_day | both | tradingview_community | 🟡 small extension to existing `bandwidth_squeeze` |
| 3 | FX-Daily-Donchian-Breakout | breakout | 6J | daily_close | both | openclaw_tactical_harvest | 🟡 uses existing `donchian_breakout` but daily horizon untested in harness |
| 4 | NR7-Breakout | vol_expansion | M2K | all_day | both | toby_crabel_book | ❌ new entry (narrowest-bar-of-N detector) |
| 5 | TV-EOD-Sentiment-Flip | structural | MES | close | both | tradingview_scan | ❌ new entry (intraday-trend-exhaustion classifier) |
| 6 | IB-Breakout-Gold | breakout | MGC | morning | both | tail_engine_research | ❌ new entry (Initial Balance window, distinct from ORB); **overlap risk** with ORB-MGC |
| 7 | FX-Asian-Session-Breakout | breakout | 6J | london_open | both | openclaw_tactical_harvest | ❌ new entry (Asian-range capture + London-open trigger); **overlap risk** with FX-Daily-Donchian |
| 8 | DualThrust | breakout | multi | all_day | both | cta_research | ❌ new entry (K1/K2 range bands on daily Open); registry notes itself tag Tier 3 |
| 9 | VCP-Intraday | vol_expansion | MGC | all_day | long | minervini_book | ❌ new entry (multi-contraction pattern detector); registry notes itself tag Tier 3 |
| 10 | THEME-VolGated-Structural-Intraday | structural | MES | morning | both | internal_research | ❌ **not a strategy** — research direction; notes say "Do not convert until current queue clears" |

Source field for "engine fit": comparing each candidate's `rule_summary` against the catalog in `research/forge_source_feedback.py:63-83` (5 entries / 6 filters / 5 exits).

---

## 2. Ranking criteria

Each candidate scored against four sprint-relevant dimensions:

- **Sprint usefulness** — does shipping this advance a paper-readiness packet by 2026-06-17?
- **Diversification angle** — does it reduce the momentum/ORB concentration in the current pool? (XB-ORB family is 3 of 3 probation seats.)
- **Harness availability** — can the engine run it today with ≤0.5 session of code?
- **Cost-aware compatibility** — does the strategy's edge depend on assumptions Item #3 will sharpen (intraday slippage, commission, fill quality)?

Weighting: harness availability is the gating constraint. A "Tier 1 thesis" with no harness is a 1-session engine build before it's a candidate at all; a "Tier 2 thesis" with existing harness can be cheap-screened this week.

---

## 3. Recommended top 3 for next Forge runner batch

The honest cut is **3, not 5**. Padding to 5 would require kicking off 1+ session of engine work per add — exactly the infrastructure drift the 5/18 doctrine forbids.

### Pick 1 — `VWAPPullback-MES-Long` *(strongly recommended)*

- **Family / asset / session:** pullback / MES / morning long
- **Why it diversifies:** Current probation pool is ORB-EMA-Ladder on MNQ/MCL/MYM. Adding a *non-ORB entry on MES* differentiates by both entry mechanism (pullback vs breakout) and asset (MES vs MNQ as the equity-index workhorse). Genome map gap: MES-long.
- **Harness availability:** ✅ Approximate today with `entry=pb_pullback`, `filter=vwap_slope`, `exit=profit_ladder`. Not a 1:1 implementation of the practitioner spec (VWAP touch from above + bullish close), but a close enough first cut to cheap-screen. **Risk:** the cheap-screen result represents the approximation, not the spec — if it passes, a higher-fidelity reimplementation should follow before paper.
- **Blocker:** none with current engine.
- **Wait for Item #3?** No. Cheap-screen first; Item #3 sharpens the cost-adjusted PF when the result lands.

### Pick 2 — `BBW-Percentile` *(recommended; small extension)*

- **Family / asset / session:** vol_expansion / M2K / all-day both
- **Why it diversifies:** Vol_expansion archetype is currently absent from the probation pool. Pairs naturally with the existing `bandwidth_squeeze` filter family and is asymmetric in payoff shape (rare fires, large per-trade).
- **Harness availability:** 🟡 Existing `bandwidth_squeeze` filter is close but not identical — the BBWP variant requires percentile-of-BBW (rolling rank) plus a "cross above 13-bar SMA of BBWP" trigger. Estimate **0.5 session** of filter extension.
- **Blocker:** filter extension; no new entry needed.
- **Wait for Item #3?** **Yes — preferred.** Rare-fire / asymmetric-payoff strategies are the most sensitive to cost assumptions. Cost-aware evidence from day one prevents a misleading first-pass PF.

### Pick 3 — `FX-Daily-Donchian-Breakout` *(conditionally recommended)*

- **Family / asset / session:** breakout / 6J / daily close both
- **Why it diversifies:** Adds a **daily horizon** to a pool that is otherwise entirely intraday. Adds FX exposure (6J) where current FX coverage is limited. Genome map gap: daily-bar FX.
- **Harness availability:** 🟡 `donchian_breakout` entry exists but has only been exercised on intraday bars (the MCL XB sweep used 5m). Need to verify the existing entry works correctly on daily bars, and a daily-close exit needs to be wired (current exits are intraday: profit_ladder, atr_trail, chandelier, time_stop, midline_target). Estimate **0.5 session** of harness wiring.
- **Blocker:** daily-bar harness path. Also flagged: FX donchian has a known bug noted RETEST since 2026-05-05 — needs that resolved first.
- **Wait for Item #3?** **Yes.** Cost-per-trade on FX daily bars is dominated by spread/slippage; cheap-screening without Item #3 risks a false-positive PF.

---

## 4. Explicit defer list (with reasons)

| Candidate | Defer reason |
|---|---|
| NR7-Breakout | New entry detector (narrowest-bar-of-N). 1 session engine build. Worthwhile but not before VWAPPullback ships its first cheap-screen result; defer to Phase 3 engine extension queue. |
| TV-EOD-Sentiment-Flip | New entry (trend-exhaustion classifier); definition is fuzzy in source notes. High specification risk — would consume more time defining the signal than running it. Defer until source can be sharpened. |
| IB-Breakout-Gold | Registry note explicitly flags overlap risk with ORB-MGC. Build only after running an overlap check against the existing XB-ORB MGC sweep results. Otherwise risk is double-counting a known exposure. |
| FX-Asian-Session-Breakout | Same overlap risk vs. FX-Daily-Donchian-Breakout (both 6J, both breakouts). Run FX-Daily first; if its cheap-screen result is informative, Asian-Session becomes either a complement or a redundancy — the answer determines whether to build. |
| DualThrust | Registry tags itself Tier 3 ("fires too frequently for intraday"). Multi-asset, daily-overlay. Park until daily-bar harness is generalized. |
| VCP-Intraday | Registry tags itself Tier 3 ("complex pattern detection", "rare on 5m"). Detector cost is high; expected fire rate is low. Worst harness-cost / signal-yield ratio of the set. Park. |
| THEME-VolGated-Structural-Intraday | Not a strategy — a research direction. Registry note: "Do not convert until current queue clears." Honors that note. |

---

## 5. Recommended timing

**Sequence:**

1. **Finish Item #3 (cost/slippage model) first.** The recommendation explicitly delays adds until Item #3 ships so new tests produce cost-aware evidence from the start. This matches the 5/18 doctrine that says infrastructure builds must move a candidate toward paper, and avoids the more pernicious failure mode where new candidates get cheap-screen PFs that overstate edge net of cost.
2. **After Item #3:** Add the top 3 to the runner pool **as a single batch** so they share the same baseline cost-assumption set. Order of operations:
   - Pick 1 (VWAPPullback-MES-Long) — zero engine work, runs immediately.
   - Pick 2 (BBW-Percentile) — 0.5 session of filter extension, then runs.
   - Pick 3 (FX-Daily-Donchian-Breakout) — 0.5 session of daily-bar harness + resolve known donchian RETEST flag, then runs.
3. **Total engine effort for the batch:** ~1 session, split across two adds. Pick 1 produces a cheap-screen result with zero engine work — that result is the gate. If Pick 1 fails cheap-screen, the engine work for Picks 2 and 3 is justified by diversification value alone; if Pick 1 passes, the engine work compounds usefully.

**What "after Item #3" means concretely:** the cost/slippage model is the next primary sprint build, estimated ~1 session. So this packet's recommended batch is feasible during Phase 2 (Paper-Readiness Sprint) without delaying any of Items #4-#9.

**What this packet does NOT recommend:**

- ❌ Building 5 new entry mechanisms in parallel to fill all 5 batch slots. That is the exact infrastructure-drift failure mode caught 5/18.
- ❌ Cheap-screening any of the 7 engine-blocked candidates before Item #3. Their evidence would be either non-existent (no harness) or cost-blind (no cost model).
- ❌ Mutating the registry today. All 10 entries stay `status: idea` until cheap-screen results land.

---

## 6. The deeper finding

The "stuck at ~60 strategies" symptom has **two causes**, not one:

1. **Operator caution** — selective deployment, elite-standard pruning. This is healthy and intentional per the CLAUDE.md operating mode.
2. **Engine inventory limit** — the crossbreeding engine has 5 entries / 6 filters / 5 exits. Most newly-harvested ideas need a new entry mechanism. Until the engine catalog grows, harvest throughput cannot translate into runner throughput.

**Implication:** the highest-leverage Phase 3 or post-sprint engineering item is probably **a generalized entry-mechanism registration framework** — one that lets new entries land in the engine as small focused additions rather than full code branches. This is a Phase 3 candidate, NOT a Phase 2 deliverable. Surfacing it here so it doesn't get re-discovered later.

**Validation of this finding:** if Item #3 ships, the recommended 3-pick batch runs, and we *still* end Phase 2 with <3 paper-ready candidates because the runner pool has nothing new to cheap-screen, then the engine-catalog hypothesis is confirmed and the post-sprint queue should prioritize the registration framework.

---

## Counter-argument

**Strongest case against this packet's recommendation:**

> *Recommending only 3 of 10 candidates and gating them on Item #3 is too conservative. "Stuck at ~60" is the operator's concern, and shipping 3 candidates over 2-3 weeks doesn't meaningfully change the number. The recommendation is mostly "wait" with a thin veneer of action.*

**Why we proceed anyway:**

- 3 well-evidenced additions beat 5 underspecified ones — paper-readiness requires *passing* candidates, not just *more* candidates.
- 7 of 10 candidates require engine builds that are themselves multi-session infrastructure work. Approving them today would *be* the infrastructure drift the 5/18 doctrine names.
- The "deeper finding" section above gives the operator a concrete second-order item (entry-registration framework) that addresses the underlying constraint, rather than papering over it.
- If operator wants more aggressive expansion, the explicit dial is: **approve one engine-build candidate from the defer list per Lane 2 slot** — but that's an explicit operator decision, not a default.

## What would prove this packet wrong

- VWAPPullback-MES-Long cheap-screens with PF < 1.1 *and* the approximation-vs-spec gap is the cause → reimplementation, not abandon.
- The 0.5-session estimates for BBWP and FX-Donchian wiring blow up to 1+ session each → re-prioritize: maybe NR7 (cleaner spec) is cheaper to build new than to extend existing.
- Item #3 reveals that intraday cost assumptions invalidate one or more of the existing XB-ORB workhorses → the entire batch-add plan defers; cost diagnosis takes precedence.

---

## Operator decision

| Option | Decision |
|---|---|
| ☐ Approve top 3, sequence after Item #3 | Default recommendation. No engine work today; batch lands post-Item-#3. |
| ☐ Approve top 1 only (VWAPPullback-MES-Long), skip others | Use if you want a single cheap-screen signal first before committing to BBWP/FX-Donchian extension work. |
| ☐ Approve top 3 + add one defer-list candidate to engine queue | Specify which. Triggers an engine pre-flight before the build. |
| ☐ Defer entire batch to post-sprint | Use if Item #3 + Items #4-#9 fill the sprint window without slack. |
| ☐ Reject — keep runner pool frozen at current 19 | Use if operator wants to focus 100% of Phase 2 on cost/slippage and validation funnel without any new candidate intake. |

---

*Filed 2026-05-19. Lane 1 intelligence packet. NO registry mutation, NO runner mutation, NO engine changes today. Top-3 batch recommended only after Item #3 cost/slippage model ships. Engine-catalog finding surfaced as a Phase 3 candidate.*
