# Pre-Flight: Item #3.5 — Silent-Default Hardening Pass

**Filed:** 2026-05-19
**Authority:** T1 (pre-flight); T2 (build approval, granted same day for execution after Item #3)
**Lane:** 2 (governance fix; replaces silent defaults with fail-closed or explicit-fallback behavior)
**Status:** APPROVED 2026-05-19 — execute immediately after Item #3 ships. **No build today.**
**Related doctrine:** `feedback_evidence_integrity_failsafe.md` (broadened 2026-05-19 — universal fail-closed rule) and `feedback_proactive_plumbing_inspection.md` (the meta-rule that surfaced these).

---

## Why Item #3.5 exists

The proactive plumbing inspection that followed the cost-defaults find surfaced 5 additional silent-default sites — same shape as the cost bug, lower per-site blast radius, same class of failure. Operator decision 2026-05-19: harden them as a focused pass after Item #3, not as part of it (scope discipline).

**Operator-locked universal rule:** *Any missing assumption that can change a trading decision must fail closed.*

No more:
- missing costs → zero cost
- missing drawdown → zero drawdown
- missing regime rule → trade all regimes
- missing metadata → permissive default
- missing carry rate → continue calculation

For a trading lab, permissive defaults are dangerous — they make broken evidence look clean.

---

## Scope (5 sites, ~0.5 session bundled)

### Site 1 — `engine/io.py:126-130`

Backtest result loader silently defaults missing metrics to 0:

```python
"roi": metrics.get("roi", 0),
"max_drawdown": metrics.get("max_drawdown", 0),
"sharpe": metrics.get("sharpe", 0),
"expected_value": metrics.get("expected_value", 0),
"trades": metrics.get("trades", 0),
```

**Fix:** Replace `0` defaults with `None` and add an explicit `valid: bool` field. Downstream consumers must check `valid` before reading metrics. A failed backtest with missing fields now reads as `valid=False` instead of "neutral strategy with zero drawdown."

### Site 2 — `engine/regime_engine.py:203`

```python
avoid = set(profile.get("avoid_regimes", []))
```

A strategy profile missing `avoid_regimes` silently means "avoid no regimes" — strategy trades in regimes its author intended to skip.

**Fix:** If `avoid_regimes` key is missing entirely (vs. explicitly empty list), raise `InvalidRegimeProfile(strategy)`. Explicit empty list is fine ("intentionally trades all regimes"); missing key is fail-closed.

### Site 3 — `engine/strategy_universe.py:181-183` + `engine/strategy_controller.py:169,183`

```python
"exit_variant": exec_cfg.get("exit_variant", None),
"avoid_regimes": exec_cfg.get("avoid_regimes", []),
"preferred_regimes": exec_cfg.get("preferred_regimes", []),
```

Same pattern. Missing strategy metadata silently becomes permissive.

**Fix:** For each decision-affecting field, distinguish "key absent" (fail-closed) from "key present and empty" (intentional). Decision-affecting fields here: `exit_variant`, `avoid_regimes`, `preferred_regimes`. Missing key → raise `InvalidStrategyConfig(strategy_id, field)`.

### Site 4 — `engine/carry_lookup.py:65-66`

```python
dom_rate = policy.get(pair["domestic"], {}).get("rate")
for_rate = policy.get(pair["foreign"], {}).get("rate")
```

Missing currency or missing rate → None silently propagates into carry calculation. **Active impact: Treasury-Rolldown-Carry-Spread is the only out-of-band probation strategy and uses this path.** If any of ZN/ZF/ZB rates are absent from `carry_rates.json`, the spread calc proceeds with None.

**Fix:** If currency missing → `InvalidCarryConfig(currency)`. If currency present but rate missing → `InvalidCarryRate(currency)`. Either is fail-closed. Same pattern at `engine/carry_lookup.py:104` (`treasury_params`).

### Site 5 — Runner asset coverage verification

Could not find a `SUPPORTED_ASSETS` constant in `research/fql_forge*.py`. Risk: the runner is hardcoded rather than driven by `engine/asset_config.py::ASSETS`, allowing drift between the 17 declared assets and N actually processed.

**Fix:** Audit how `fql_forge_batch_runner.py` and `fql_forge_daily_loop.py` enumerate assets. If hardcoded, replace with import from `asset_config.ASSETS`. If config-driven already, add an assert that runner-enumerated-assets == asset_config-declared-assets at startup; fail-closed if they diverge.

---

## What this does NOT include

- ❌ Engine refactor beyond the 5 sites named above
- ❌ A broad "find every `.get(x, default)` site" sweep (defer; would balloon scope)
- ❌ Strategy logic changes — pure plumbing
- ❌ Registry mutation
- ❌ Doc changes (the doctrine memory captures the universal rule; per-doc updates are out of scope)
- ❌ Test framework additions beyond exercising the new exception paths

---

## Build rule

- Target **~0.5 session bundled.**
- Order: Sites 1 → 2 → 3 → 4 → 5. Each is independent — atomic commits per site, revert path per site.
- Each fix must include a test that exercises the new `Invalid*` exception path (or asserts the runner equality for Site 5).
- If any single site takes >0.2 session, escalate — likely the silent-default is doing more load-bearing work than expected, and the fix needs a separate pre-flight.

---

## Counter-argument

> *Item #3.5 is making the engine stricter for marginal benefit. Item #3 already fixes the load-bearing failure (cost). Sites 1-5 may never have produced a wrong decision in practice. Tightening them all is paranoia bleed.*

**Why we proceed anyway:**
- The cost-defaults bug also "may never" have produced a wrong decision — until it did, silently, for months on MCL/MYM. The whole point of fail-closed is that we don't get to know in advance which silent default eventually bites.
- The 5 sites named are not speculative; each was confirmed by direct file inspection 2026-05-19.
- The total cost is ~0.5 session, lower than the cost of one paper-trading decision made on broken plumbing.
- The doctrine (`feedback_evidence_integrity_failsafe.md`) is decoration without enforcement. Item #3.5 is the enforcement.

## What would prove this decision wrong

- The new `Invalid*` exceptions fire in practice on legitimate strategies that *should* run → the missing-key distinction is wrong; need to revise per-site whether "missing" is really fail-closed or is a documented fallback.
- Item #3.5 takes >1 session → one or more sites needs a dedicated pre-flight, not a bundled pass.
- Site 5 reveals the runner is silently skipping assets → that finding upgrades to its own pre-flight, not part of #3.5.

---

## Sequencing

1. Item #3 (cost integrity reset, including Piece H) — next session
2. **Item #3.5 (this) — session after Item #3**
3. Cost-aware pool expansion batch (3-pick from `_DRAFT_2026-05-19_pool_expansion_packet.md`) — after #3.5
4. Validation funnel v0 (Item #7) — after expansion batch
5. Paper-readiness packets (Item #9) — deliverable by 2026-06-17

Item #3.5 inserts cleanly between cost reset and pool expansion; does not delay the sprint exit gate.

---

## Operator decision

**APPROVED 2026-05-19** — execute after Item #3 ships. Scope is the 5 sites named. No registry mutation. No paper/probation/promotion decisions until Item #3 impact report lands (and, downstream, until #3.5 hardens the remaining sites).

---

*Filed 2026-05-19, approved same day. Lane 2 governance/enforcement. The cost-defaults bug was one instance of a class. Item #3.5 closes the class.*
