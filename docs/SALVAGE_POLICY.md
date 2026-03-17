# FQL Salvage Lane Policy

*Rules for when and how to retry a failed strategy before permanent closure.*
*Last updated: 2026-03-16*

---

## Salvage vs Monitor vs Reject

| Status | What it means | What happens next |
|--------|--------------|-------------------|
| **SALVAGE** | Partial edge detected. One specific fix might work. | Exactly ONE controlled retry with a defined change. |
| **MONITOR** | Signal exists but insufficient data to judge. | Wait. Revisit when more data accumulates. No active work. |
| **REJECT** | No viable edge. Structural failure. | Archived permanently. Never retested without material change. |

**Key distinction:** SALVAGE requires an identifiable, testable fix. If you can't name the specific change that might work, it's MONITOR or REJECT — not SALVAGE.

---

## What Qualifies as SALVAGE

A strategy earns SALVAGE classification (from batch_first_pass) when:

1. **Overall PF > 1.0 with >= 20 trades** AND one of:
   - One directional mode (long or short) shows PF > 1.2
   - One walk-forward half shows PF > 1.3
   - One specific session or regime shows strong edge

2. The fix is **identifiable and singular:**
   - Session restriction (e.g., "remove Asia hours")
   - Direction restriction (e.g., "long only")
   - Regime filter (e.g., "avoid RANGING")
   - Parameter adjustment (e.g., "wider ATR stops for this asset")
   - Entry timing shift (e.g., "London open instead of NY open")

3. The fix is **different from what was already tested.** Retrying the same parameters or logic is not salvage — it's denial.

---

## Salvage Rules

### Rule 1: Maximum ONE salvage attempt per strategy

After the initial batch_first_pass SALVAGE classification:
- One controlled follow-up test
- Test exactly one change (single-variable)
- Run through batch_first_pass again

If the salvage attempt produces ADVANCE → proceed to validation battery.
If the salvage attempt produces anything else → REJECT permanently.

**No second chances.** Two failed attempts on the same strategy is enough evidence.

### Rule 2: The salvage change must be pre-declared

Before running the salvage test, document in the registry:
```
salvage_attempt: {
    "original_classification": "SALVAGE",
    "proposed_fix": "restrict to US session only",
    "rationale": "Asia/Europe sessions showed negative PnL",
    "date": "2026-XX-XX"
}
```

This prevents post-hoc rationalization ("I tried 5 things and one worked").

### Rule 3: Salvage attempts count toward the family limit

If 3+ strategies in the same family (e.g., mean_reversion x equity_index) have been tested and all failed or salvage-failed, the family is **permanently closed** for that asset class.

Current closed families:
- mean_reversion x equity_index (M2K): 5 tested, all failed
- ict x any: 2 tested, both failed
- breakout x morning (equity): 13 strategies, saturated

### Rule 4: Salvage window expires

A SALVAGE classification expires after 30 days if not acted on. After expiration, the strategy moves to REJECT unless explicitly converted to MONITOR with a reason.

---

## When a Family is Permanently Closed

A strategy family is closed for a specific asset class when:

| Condition | Result |
|-----------|--------|
| 3+ strategies tested, all REJECT | Family CLOSED for that asset class |
| 2+ strategies tested, all STRUCTURAL_LOSS | Family CLOSED |
| 1 strategy REJECT + 1 salvage attempt REJECT | Family CLOSED for that specific combination |
| Genome map flags as AVOID | Family CLOSED (overcrowded or proven non-viable) |

**Closed families are logged in the genome map avoid list** and the harvest engine targeting config.

Reopening a closed family requires:
- Material change in market structure (documented)
- OR fundamentally different approach (not parameter tweaks)
- AND explicit approval before testing

---

## How Salvage is Logged

### In the registry:

```json
{
    "strategy_id": "XYZ-Salvage",
    "status": "testing",
    "source": "salvage_attempt",
    "salvage_attempt": {
        "original_id": "XYZ-Original",
        "original_classification": "SALVAGE",
        "proposed_fix": "US session restriction",
        "rationale": "Asia/Europe negative, US session profitable",
        "attempt_date": "2026-XX-XX",
        "result": "ADVANCE | REJECT",
        "result_pf": X.XX,
        "result_trades": N
    }
}
```

### In batch_first_pass output:

The salvage test runs through the normal factory pipeline. No special treatment — same thresholds, same classification rules.

### In the genome map:

If salvage fails, the rejection_reason is updated to include the salvage failure, and the family closure count increments.

---

## Examples from FQL History

### Successful salvage: MomPB-6J-Long-US

- **Original:** momentum_pullback_trend on 6J, all sessions, PF 1.09
- **SALVAGE classification:** directional split showed long PF 1.09 with consistent walk-forward
- **Proposed fix:** restrict to US session only
- **Result:** PF 1.58, Sharpe 2.92, CONDITIONAL_PASS → PROBATION
- **Outcome:** Successful. Now in probation portfolio.

### Failed salvage: 6B Donchian breakout

- **Original:** donchian_trend_breakout on 6B, PF 0.95
- **SALVAGE consideration:** nearly breakeven, long-only showed marginal edge
- **Decision:** Not worth salvaging — PF 0.95 is too close to breakeven, long-only had 145 trades all losing mode
- **Outcome:** Correctly rejected. No salvage attempt.

### Family closure: M2K mean reversion

- **Tested:** RSI2-Bounce (PF 0.76), GapFill (PF 0.68), IBS-MR (idea stage), plus 2 others
- **Result:** 5 strategies tested or ideated, all negative
- **Outcome:** Family permanently closed. Logged in genome map AVOID list.

---

## Quick Reference

```
batch_first_pass → SALVAGE classification
  → identify ONE specific fix
  → document fix in registry BEFORE testing
  → run ONE salvage test through batch_first_pass
  → ADVANCE? → validation battery
  → anything else? → REJECT permanently
```

**Maximum:** 1 salvage attempt per strategy. 3 failures closes the family.
**Expires:** 30 days from SALVAGE classification if not acted on.
