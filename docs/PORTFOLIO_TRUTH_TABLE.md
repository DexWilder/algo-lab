# Portfolio Truth Table

**Current as of: 2026-04-14**

> **This is an operator summary, not a source of truth.** All state below
> is derived from existing authoritative sources. If this document
> disagrees with the listed authorities, **the authorities win.** Update
> this table by re-reading the authorities; do not edit the authorities
> to match this table.
>
> **Authorities (do not duplicate):**
> - **Live execution / lifecycle:** `research/data/strategy_registry.json` + belt-and-suspenders guard in `engine/strategy_universe.py`
> - **Probation gates (non-XB-ORB):** `docs/PROBATION_REVIEW_CRITERIA.md`
> - **Probation gates (XB-ORB family):** `docs/XB_ORB_PROBATION_FRAMEWORK.md`
> - **Drift monitoring:** `research/live_drift_monitor.py` BASELINE
> - **Recovery state:** `research/logs/.watchdog_state.json` (shell watchdog)
> - **SAFE_MODE verdict:** `research/data/watchdog_state.json` (system_watchdog.py, scheduled daily)

---

## Active Core (3)

| Strategy | Asset | Family | Direction | BT PF | Drift tier |
|---|---|---|---|---|---|
| ORB-MGC-Long | MGC | Breakout | Long | 1.99 | reference-only |
| PB-MGC-Short | MGC | Pullback | Short | 2.36 | observational |
| XB-PB-EMA-MES-Short | MES | Pullback | Short | 1.31 | reference-only |

## Active Probation — Intraday Single-Asset (7)

| Strategy | Asset | Family | BT PF | BT Trades | Promoted | Drift tier |
|---|---|---|---|---|---|---|
| XB-ORB-EMA-Ladder-MNQ | MNQ | Crossbreed breakout | 1.62 | 1183 | 2026-04-06 | full |
| XB-ORB-EMA-Ladder-MCL | MCL | Crossbreed breakout | 1.33 | 898 | 2026-04-08 | full |
| XB-ORB-EMA-Ladder-MYM | MYM | Crossbreed breakout | 1.67 | 340 | 2026-04-13 | full |
| ZN-Afternoon-Reversion | ZN | Afternoon rates reversion | 1.32 | 300 | 2026-03-20 | full |
| DailyTrend-MGC-Long | MGC | Trend (daily bars) | 3.65 | sparse | 2026-03-16 | observational |
| TV-NFP-High-Low-Levels | MNQ | Event-driven | 1.66 | sparse | 2026-03-18 | observational |
| VolManaged-EquityIndex-Futures | MES | Volatility sizing | — | daily rebalance | 2026-03-20 | **excluded** |

## Active Probation — Out-of-Band (1)

| Strategy | Asset(s) | Shape | Execution path | Evidence log | Drift handling |
|---|---|---|---|---|---|
| Treasury-Rolldown-Carry-Spread | ZN/ZF/ZB (3-tenor spread) | Monthly carry-rank spread | `research/run_treasury_rolldown_spread.py` via `com.fql.treasury-rolldown-monthly` launchd (weekdays 17:10, first-business-day guard) | `logs/spread_rebalance_log.csv` | **excluded from per-trade severity** |

**First live rebalance:** expected 2026-05-01 (Friday). Seeded historical entries: TRS-2026-03, TRS-2026-04.

## Excluded / Archived / Rejected (not active, not in drift baseline)

Representative, not exhaustive. Full list in registry.

| Strategy | Status | Reason |
|---|---|---|
| FXBreak-6J-Short-London | rejected | Concentration catastrophe (top-3 98.7%, max-year 112.6%). Both workhorse and tail-engine paths reject. Not re-probatable. |
| MomPB-6J-Long-US | archived | 2026-03-18 review. |
| PreFOMC-Drift-Equity | rejected | 2026-03-17 review. |
| CloseVWAP-M2K-Short, MomIgn-M2K-Short, MomPB-6E-Long-US, TTMSqueeze-M2K-Short | rejected (2026-03-18 batch) | Status guard now prevents runner inclusion. 4 trades of residual live history each. |
| NoiseBoundary-MNQ-Long | archived | `controller_action=ARCHIVE_REVIEW` already ineligible. 9 historical trades in log. |
| VWAP-MNQ-Long, Donchian-MNQ-Long-GRINDING, BB-EQ-MGC-Long | Phase 17 legacy | Dropped from drift baseline 2026-04-14. |

## Open Factor Gaps

| Gap | Severity | Coverage status | Resolution path |
|---|---|---|---|
| **FX** | HIGH | 0 active strategies | FXBreak family verified unsalvageable. Fresh design required; lane NOT open. |
| **STRUCTURAL (primary)** | MEDIUM | Thin — ZN-Afternoon (microstructure) + TV-NFP (event levels). No pure session-transition primary. | FXBreak-6J was the intended fill; verified not viable. Fresh design required; lane NOT open. |
| VALUE | LOW | 0 | Not prioritized at current scale. |
| CARRY | CLOSED | Treasury-Rolldown-Carry-Spread (out-of-band monthly, re-probated 2026-04-14) | N/A |
| Rates breadth | CLOSED | ZN-Afternoon (intraday) + Treasury-Rolldown (monthly spread) | N/A |

## Open Asset Gaps

| Asset class | Coverage | Notes |
|---|---|---|
| FX (6E, 6J, 6B, DX) | 0 active | All FXBreak variants archived/rejected. |
| Energy breadth | 1 (XB-ORB-MCL only) | Single-strategy concentration on MCL. Low priority. |
| Rates beyond ZN | 0 (ZF, ZB via Treasury-Rolldown spread only) | Treasury-Rolldown spans ZN/ZF/ZB but as spread legs, not primary directional exposure. |

## Next Checkpoint

**2026-05-01 — Treasury-Rolldown first live monthly rebalance.** Verification procedure: `docs/MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md`.

No other lanes open. Hold in effect until the checkpoint outcome is evaluated.

## Registry vs Runner Divergences Currently Contained by Status Guard

`build_portfolio_config` skips any strategy with `status in {"rejected", "archived"}` regardless of `controller_action`. The following registry entries have divergent fields that the guard is currently masking; they are NOT operational risks while the guard remains in place, but are candidates for a future registry-hygiene pass:

BB-EQ-MGC-Long, ORBEnh-M2K-Short, VWAPMR-MCL-Short, GapMom, RangeExpansion, FXBreak-6J-Short-London, PreFOMC-Drift-Equity, Commodity-TermStructure-Carry-EnergyMetals
(each: `status=rejected/archived` but `controller_action` still in PROBATION/REDUCED_ON)

## Health Stack At A Glance

| Layer | File | Scheduled? | Current |
|---|---|---|---|
| Recovery (gateway, claw loop, missed jobs) | `scripts/fql_watchdog.sh` | every 5 min | Active |
| SAFE_MODE gate for forward trading | `research/system_watchdog.py` → `research/data/watchdog_state.json` | daily, priority 0 | Active since 2026-04-14 |
| 60-point hygiene report | `research/fql_health_check.py` → `research/reports/health_check_*.json` | daily, priority 1 | Active |
| Forward drift monitoring | `research/live_drift_monitor.py` → `research/data/live_drift_log.json` | daily | Active (live sources since 2026-04-14) |
| Out-of-band monthly execution (Treasury-Rolldown) | `research/run_treasury_rolldown_spread.py` | weekdays 17:10, first-BD guard | Pending first fire 2026-05-01 |

---

*This document is machine-readable by eye, not by schema. It is regenerated manually from the authorities listed at the top. If the state below is older than ~7 days, re-derive from the authorities rather than trusting these cells.*
