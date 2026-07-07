# Permanent Mechanism-Harvest Pipeline (2026-07-07)

> Standing weekly process — the library must never run out of raw material. Mission: **grow the mechanism library every week.**
> Every source item → a candidate MECHANISM (Tier A/B/C), added to `mechanism_library.json`. Correctness is NOT required to add
> — a mechanism is a *hypothesis about why prices move*. Skepticism happens at validation, not at harvest.

## Weekly harvest quota (raw material in)
| Source | Target/wk | Extract | Anti-retail filter |
|---|---|---|---|
| Academic / SSRN | 20 papers | the MECHANISM + horizon + market (not the backtest) | require a forced-participant/structural story |
| Hedge-fund / CTA white papers (AQR/Man/TwoSigma public) | 10 | premia + flow mechanisms | reject if it's an indicator with a tuned lookback |
| Exchange notices (CME/ICE/CBOE) | all new | rule/roll/settlement/rebalance changes → forced-flow | directly testable |
| GitHub / QuantConnect | 10 repos | data sources + mechanisms | treat strategies as hypotheses to DISPROVE, never copy |
| Reddit/forums (experienced quants) | scan | mechanism ideas | heavy skepticism; most are overfit |
| Conference / dissertation | as available | novel microstructure/flow | mechanism-first |

## Originality tiers (the metric that matters)
- **Tier A** — completely new distinct behavioral mechanism (highest value; track A-added/week).
- **Tier B** — existing mechanism in a NEW market.
- **Tier C** — new EXPRESSION of an existing mechanism (lowest value; the batch generates these).
**We care far more about +1 Tier-A than +100 Tier-C.** Target: **≥3 Tier-A mechanisms added per week.**

## Pipeline: harvest → library (Discovery) → cheap-screen/pre-register (Research) → full-stack (Validation) → portfolio
Each harvested mechanism: status=untested, tier, data_have/data_needed. If data-gapped → feeds `DATA_ACQUISITION_ROADMAP` (ranked by discovery ROI). If data-ready → cheap-screen or pre-register. Only DSR-survivors reach expensive validation.

## The library is a KNOWLEDGE BASE, not a tracker
It permanently records: mechanisms falsified (dead/weak — so we never re-mine them), partially validated (watch/ingredient/screen_pass), waiting-on-data (untested/data_blocked), and harvested-not-yet-tested. Over years this compounds into institutional knowledge no retail trader has.

## Cadence
- **Weekly:** harvest quota → add to library → report Tier-A added, library size, discovery-surface (untested Tier-A).
- **Standing metric:** "Are we learning about markets faster than last week?" = Δ(library size) + Tier-A added + mechanisms-moved-to-tested.
