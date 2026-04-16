# Ghost Inventory

**Created:** 2026-04-16 (FQL Forge v1 day 2)
**Source:** ghost-candidate scan across `strategies/*/strategy.py` +
`research/data/first_pass/*.json` vs `research/data/strategy_registry.json`
**Root cause:** batch_first_pass sweep (2026-04-06 → 2026-04-09) created
strategy dirs + first-pass results but did not auto-register in the
strategy registry. Every strategy from that batch is a ghost.

**Total ghosts found:** 33 (+ 1 resolved day-1: SPX-Lunch-Compression)

---

## Disposition categories

| Category | Count | Action |
|---|---|---|
| `batch_register_reject` | 26 | Queue for bulk memory-closure on fallback days. Does not need individual triage — clear REJECT or TAIL_ENGINE_REJECT verdicts. |
| `individual_triage` | 5 | SALVAGE classification. Individual read of first-pass detail + gap-relevance assessment in today's or next packet. |
| `monitor_pending` | 2 | MONITOR classification (too few trades). Park until data grows. |

---

## individual_triage (5) — ordered by triage priority

| # | Strategy | Classification | PF | Trades | Gap relevance | Triage status |
|---|---|---|---|---|---|---|
| 1 | `vol_compression_breakout` | SALVAGE | 1.184 | 310 | VOLATILITY family — VolManaged exists but different shape | pending |
| 2 | `vol_compression_breakout_v2` | SALVAGE | 1.184 | 310 | Likely variant of #1 — resolve duplicate first | pending |
| 3 | `ema_trend_rider` | SALVAGE | 1.079 | 1985 | MOMENTUM — crowded family but highest trade count of any ghost | pending |
| 4 | `gold_bw_squeeze` | SALVAGE | 1.377 | 23 | MGC — gold already well-covered (3 active strategies) | pending |
| 5 | `6j_tokyo_london` | SALVAGE | 1.021 | 162 | FX + STRUCTURAL (open gaps!) but PF barely above 1.0 | pending |

---

## monitor_pending (2) — parked

| Strategy | Classification | PF | Trades | Notes |
|---|---|---|---|---|
| `fx_value_mean_reversion` | MONITOR | 3.579 | 7 | FX gap-relevant but 7 trades = noise. Re-evaluate if data depth increases. |
| `vwap_rev` | MONITOR | 8.039 | 5 | Absurd PF on 5 trades. Meaningless until significantly more observations accumulate. |

---

## batch_register_reject (26) — queued for bulk memory-closure

These are clear REJECT or TAIL_ENGINE_REJECT verdicts from the
batch_first_pass classifier. They will be batch-registered in the
strategy registry on future memory-closure fallback days. Each gets a
minimal registry entry: `status=rejected`, `rejection_reason` from the
first-pass classification, minimal memory payload. They do NOT need
individual deep-triage.

| Strategy | Classification | Best PF | Trades |
|---|---|---|---|
| `atr_expansion_breakout` | REJECT | — | — |
| `bb_compression_gold` | REJECT | — | — |
| `bb_range_mr` | REJECT | — | — |
| `donchian_trend_breakout` | REJECT | — | — |
| `eia_reaction` | REJECT | — | — |
| `eod_sentiment_flip` | REJECT | — | — |
| `gap_fill` | REJECT | — | — |
| `keltner_channel` | REJECT | — | — |
| `larry_oops` | REJECT | — | — |
| `london_preopen_fx_breakout` | TAIL_ENGINE_REJECT | — | — |
| `lucid-100k` | REJECT | — | — |
| `macro_event_box` | TAIL_ENGINE_REJECT | — | — |
| `nfp_event_box` | TAIL_ENGINE_REJECT | — | — |
| `opex_week` | REJECT | — | — |
| `orb_fade` | REJECT | — | — |
| `overnight_drift` | REJECT | — | — |
| `rate_daily_momentum` | TAIL_ENGINE_REJECT | — | — |
| `rate_intraday_mr` | REJECT | — | — |
| `sma-crossover` | REJECT | — | — |
| `tokyo_vwap_bounce_6j` | REJECT | — | — |
| `treasury_tsm` | TAIL_ENGINE_REJECT | — | — |
| `trend_continuation` | REJECT | — | — |
| `vol_compression_breakout` | — | — | — |
| `vol_compression_breakout_v2` | — | — | — |
| `vwap_006` | REJECT | — | — |
| `vwap_dev_mr` | TAIL_ENGINE_REJECT | — | — |
| `vwap_mr_gold` | TAIL_ENGINE_REJECT | — | — |
| `xb_pb_squeeze_chand` | REJECT | — | — |

*(Updated 2026-04-16: vol_compression_breakout moved from
individual_triage to batch_register_reject — misclassified by
ghost-scan glob bug. vol_compression_breakout_v2 triaged and rejected
on 2026-04-16. Current batch_register_reject count: 26 including both
vol_compression variants.)*

---

## Already resolved (1)

| Strategy | Resolution date | Outcome |
|---|---|---|
| `spx_lunch_compression` | 2026-04-15 | REJECT with full memory payload. Registry entry created. See commit `bdff4e3`. |

---

## Triage progress tracking

Updated as individual_triage items are processed:

| Strategy | Triage date | Verdict | Salvage class | Notes |
|---|---|---|---|---|
| `spx_lunch_compression` | 2026-04-15 | REJECT (concentration catastrophe) | extract-components-only | Full 6-field memory payload + component extraction. Commit `bdff4e3`. |
| `vol_compression_breakout` | 2026-04-16 | batch_register_reject | — | Misclassified by ghost-scan glob bug. Actual first-pass: TAIL_ENGINE_REJECT, PF 0.488, 107 trades on M2K. Moved from individual_triage to batch_register_reject. |
| `vol_compression_breakout_v2` | 2026-04-16 | REJECT | extract-components-only | MNQ PF 1.184 / 310 trades / WF 1.13→1.23. Below 1.2 PF, cross-asset fails (MES 0.82, M2K 0.92), max_year 56.4%, MNQ already has stronger XB-ORB workhorse. Vol-compression regime detection logic reusable. |
| `ema_trend_rider` | 2026-04-16 | REJECT | archive | MNQ PF 1.079 / 1985 trades. Structurally too thin (1985 trades at PF 1.08 = near-zero edge despite huge sample). Cross-asset fails comprehensively (5/5 other assets REJECT). Generic EMA concept, nothing to extract. |
| `gold_bw_squeeze` | 2026-04-16 | REJECT | archive | MGC PF 1.377 / 23 trades / WF H1=0.003, H2=1.94. Period artifact: virtually all PnL in H2. MGC already has 3 active strategies. Squeeze concept exists in BB-EQ-MGC-Long. |
| `6j_tokyo_london` | 2026-04-16 | REJECT | archive | 6J PF 1.021 / 162 trades / WF 1.32→0.92 (degrading). No edge (PF≈1.0). Top-3 concentration extreme (~790%). Targets open FX+STRUCTURAL gaps but gap relevance doesn't rescue zero-edge. Session-transition on 6J tested from multiple angles (also FXBreak-6J); both fail. |

---

## Batch-register progress

| Batch | Date | Items registered | Running total |
|---|---|---|---|
| (none yet) | — | — | 0 / 24 |

---

*This file is the standing reference for ghost-candidate work. Updated
as triage and batch-registration proceed. See `cadence.md` weekly
integrity checklist for the ghost-scan policy that created this
inventory.*
