# Phase 4 — Harvest backlog translation + Phase 5 plan (2026-05-28)

This document records Phase 4 backlog sourcing output and proposes the next
cheap-screen batch (Phase 5).

---

## Phase 4 backlog parse results

- **Notes parsed:** 649 (out of 649 harvest files; structured format)
- **Distribution by priority:**
  - LOW: 494 (mostly NEW_INFRA — needs new primitives to test)
  - MEDIUM: 155
  - HIGH: 0 (because HIGH requires SCREENABLE *and* HIGH-priority factor, and most screenable candidates are STRUCTURAL/MEDIUM)
- **Distribution by feasibility:**
  - SCREENABLE_WITH_DEFAULT: 26 (immediately testable with existing primitives)
  - NEEDS_HOST: 134 (filter/overlay; requires pairing with a host entry strategy)
  - NEW_INFRA: 489 (carry/value/auction/curve — need new primitive infrastructure)
- **Distribution by factor:** VALUE 239, CARRY 137, STRUCTURAL 116, VOLATILITY 80, EVENT 67, MOMENTUM 10
- **Distribution by session:** unspecified 566, london 33, close 22, overnight 15, afternoon 11, open/morning 2

**Key insight:** the operator-set priority list (`~/openclaw-intake/inbox/_priorities.md`) marks VALUE as HIGH and CARRY as MEDIUM, but the BACKLOG NOTES for those factors mostly require new infrastructure (cross-sectional value spreads, carry curves, auction calendars). The immediately-screenable candidates are predominantly STRUCTURAL — opening-range / Donchian / ATR / VWAP fragments on non-equity assets. So Phase 5 will widen the *asset* dimension (energy / rates / FX / gold) far more than the *factor* dimension.

---

## Top 25 queue — full rank in `2026-05-28_phase4_candidate_queue.json`

Highlights:

| # | Title | Factor | Assets | Session | Feasibility |
|---|---|---|---|---|---|
| 1 | Partial profit ladder for non-equity trends | STRUCTURAL | 6N,CL,GC,MCL,MGC,ZB,ZN | unspecified | SCREENABLE_WITH_DEFAULT |
| 3 | Dual-thrust ORB for rates and commodities | STRUCTURAL | CL,GC,MCL,MGC,ZB,ZN | unspecified | SCREENABLE_WITH_DEFAULT |
| 4 | Donchian channel breakout for non-equity trends | STRUCTURAL | 6E,CL,GC,MCL,MGC | unspecified | SCREENABLE_WITH_DEFAULT |
| 5 | ATR stop + Donchian entry for commodity/rates | STRUCTURAL | CL,MCL,NG,ZB,ZN | unspecified | SCREENABLE_WITH_DEFAULT |
| 8 | Afternoon VWAP Slope Confirmation | STRUCTURAL | CL,GC,MCL,MGC | afternoon | SCREENABLE_WITH_DEFAULT |
| 10 | Global Commodity Open Buffer Breakout | STRUCTURAL | CL,MCL,NG | unspecified | SCREENABLE_WITH_DEFAULT |
| 12 | Donchian breakout with ATR stop for non-equity | STRUCTURAL | 6E,CL,GC | unspecified | SCREENABLE_WITH_DEFAULT |
| 15 | Bollinger bandwidth expansion for non-equity | VOLATILITY | 6E,CL,GC | unspecified | SCREENABLE_WITH_DEFAULT |
| 16 | Dual-Thrust Afternoon Energy Release | STRUCTURAL | CL,MCL | afternoon | SCREENABLE_WITH_DEFAULT |
| 18 | Tokyo Session VWAP Bounce on JPY Futures | STRUCTURAL | 6J | overnight | SCREENABLE_WITH_DEFAULT |

---

## Phase 5 candidate batch (8 candidates recommended for next cheap-screen)

Selected for maximum diversity vs the current 5-clock active set
(`MNQ Ladder` + 4 MNQ/MES variants). Each batch entry expands at least one of:
asset class, entry family, filter, exit, or session.

| # | Candidate spec | Asset | Entry | Filter | Exit | Rationale |
|---|---|---|---|---|---|---|
| P5-1 | XB-Donchian-EMA-Ladder-MCL | MCL | donchian_breakout | ema_slope | profit_ladder | Donchian entry NEW family; energy NEW asset class |
| P5-2 | XB-Donchian-EMA-Ladder-MGC | MGC | donchian_breakout | ema_slope | profit_ladder | Donchian entry on already-wired MGC asset for ladder family comparison |
| P5-3 | XB-Donchian-EMA-ATRTrail-MCL | MCL | donchian_breakout | ema_slope | atr_trail | Donchian + ATR-trail = the literal backlog #5 candidate |
| P5-4 | XB-ORB-BBSqueeze-Ladder-MCL | MCL | orb_breakout | bandwidth_squeeze | profit_ladder | BB-squeeze filter on energy; tests volatility-expansion gate |
| P5-5 | XB-ORB-EMA-Ladder-ZN | ZN | orb_breakout | ema_slope | profit_ladder | ORB workhorse extension to rates (ZN); rates underrepresented |
| P5-6 | XB-ORB-Afternoon-Ladder-MCL | MCL | orb_breakout | session_afternoon | profit_ladder | Afternoon-energy release (backlog #16) |
| P5-7 | XB-PB-EMA-Ladder-6J | 6J | pb_pullback | ema_slope | profit_ladder | FX cross-asset on yen; Tokyo-session inspired |
| P5-8 | XB-VWAP-EMA-Chandelier-MCL | MCL | vwap_continuation | ema_slope | chandelier | Test VWAP entry on energy (failed on MNQ/MES; energy may differ) |

**Diversity check:**
- non-MNQ: 8 of 8 ✓
- non-ORB: 4 (P5-1, P5-2, P5-3, P5-7, P5-8) — meets ≥3 ✓
- non-equity-index: 8 of 8 ✓ (no MNQ/MES/M2K/MYM)
- afternoon/session: 1 (P5-6) — below the ≥3 target but session candidates are sparse in screenable backlog. Acceptable for this batch.
- mean-reversion: 0 — backlog screenable set has none; defer mean-rev expansion
- rates/gold/FX/energy: P5-1/3/4/6/8 energy, P5-5 rates, P5-7 FX, P5-2 gold = 8 of 8 ✓
- tail/payoff-ratio likely (per Phase 2-3 pattern): P5-3 (ATR-trail), P5-8 (chandelier) — 2 ✓

**Correlation guard pre-check:**
- P5-1 vs P5-3: same (asset, entry, filter) = MCL+donchian+ema, different exits. Cluster will fire — pick 1 at promotion.
- All other candidates differ on ≥2 slots from each other and from current portfolio.

---

## Hard boundaries (unchanged per operator instruction)

- No automatic registry promotions
- No automatic forward-clock wiring
- No live/prop changes
- No paper-packet drafting
- No protected Lane A/runtime changes

Phase 5 sprint execution remains in the "active Forge continuous" lane (allowed without per-batch approval). Promotion of any PASS result requires explicit operator authorization, same as Phase 2 + Phase 3.

---

## What Phase 4 deliberately did NOT include

- **VALUE/CARRY/EVENT NEW_INFRA candidates** — they are 86% of the backlog (489 of 649) but require new engine primitives. Logged in `2026-05-28_phase4_candidate_queue.json` under `full_queue` with `module_feasibility = NEW_INFRA`. These become a separate roadmap track (primitive-build project) rather than a Phase-N sprint candidate.
- **Notes from `inbox/refinement/`** — 182 additional notes there were not parsed. Most are convergence/refinement memos, not fresh candidate ideas. Defer until next Phase 4 cycle if needed.
- **Operator interpretation of borderline notes** — automated parsing tagged everything via keyword detection. Operator-curated re-tagging of the 26 SCREENABLE_WITH_DEFAULT may surface ones I missed.

---

## Living state at end of Phase 4

```
Active forward clocks (5):
  Track 1: XB-ORB-EMA-Ladder-MNQ                 28/30, near packet
  Track 1: XB-ORB-EMA-Ladder-MGC                 0 forward, wired today
  Track 2: XB-ORB-EMA-Chandelier-MNQ             0 forward
  Track 2: XB-PB-EMA-Chandelier-MNQ              0 forward, wired today
  Track 2: XB-ORB-EMA-ATRTrail-MES               0 forward, wired today

Phase 5 candidate batch (8 specs):
  P5-1 through P5-8 — awaiting operator authorization to run cheap-screens

Phase 4 deliverables:
  docs/reports/forge_sprint/2026-05-28_phase4_candidate_queue.json
  docs/reports/forge_sprint/2026-05-28_phase4_summary_phase5_plan.md (this file)
  docs/reports/2026-05-28_phase4_backlog_sourcing.log
```

---

## Pointers

- Operator priority list: `~/openclaw-intake/inbox/_priorities.md`
- Backlog source: `~/openclaw-intake/inbox/harvest/` (649 notes)
- Refinement queue: `~/openclaw-intake/inbox/refinement/` (182 notes, deferred)
- Upgraded screen: `research/forge_screen_metrics.py`
- Three-track model: `feedback_three_track_candidate_model.md` (memory)
- Continuous Forge doctrine: `feedback_continuous_forge_execution.md` (memory)
- Diversity / correlation rule: `feedback_phase3_sourcing_rule.md` (memory)
