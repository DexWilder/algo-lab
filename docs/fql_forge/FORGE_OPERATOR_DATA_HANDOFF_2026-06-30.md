# Forge Operator Data Handoff (2026-06-30) — LANE 1 (you), so LANE 2 (Forge) never blocks

> Drop each file at its exact path → its harness AUTO-RUNS (report-only, no synthetic data, no mutation). These are the
> structural feeds the now-exhausted primitive sweep cannot replace. `.gov`/vendor are sandbox-blocked → operator-downloaded.

## #1 Treasury roll-yield (true carry) — HIGHEST · drop → `data/feeds/rates_multicontract.csv`
- Cols: `instrument,contract_month,date,settle` (front + 2nd-deferred per ZN/ZF/ZB).
- Source: Databento `GLBX.MDP3` per-expiry ZN/ZF/ZB settles (you already have Databento) OR CME settles.
- Auto-runs: month-end-rates RE-GRADE protocol + true front-vs-deferred carry P1 (re-grades the WATCH-marginal rates edge on PROPERLY-ROLLED series — confirms or kills the roll-adjacency-inflated edge).
## #2 EIA crude stocks — drop → `data/feeds/eia_crude_stocks.csv`
- Cols: `release_date,period_end,stocks_kbbl` (+`consensus_kbbl` if available; else 5yr-seasonal baseline).
- Source: EIA Weekly Petroleum Status (crude ex-SPR). Free API: `api.eia.gov/v2/petroleum/stoc/wstk/data/` (free key) or manual CSV.
- Auto-runs: energy-event surprise screen (draw/build vs consensus → MCL/CL response). NOTE: MCL returns are roll-dirty; use clean CL or winsorize.
## #3 CPI consensus — drop → `data/feeds/cpi_releases.csv`
- Cols: `release_date,ref_month,cpi_mom_pct,consensus_mom_pct`.
- Source: BLS release dates (have realized on FRED) + consensus (the missing piece).
- Auto-runs: inflation-SURPRISE event screen.
## Paid-data decision (separate, your call) — `PAID_DATA_DECISION_MEMO_2026-06-26.md`
- Rank: gamma/GEX (#1 structural prior) → true VIX curve (#2, cheap) → options-OI/L2 (#3).

**On any drop, Forge's runner detects the file and fires the harness — no further ask needed.**
