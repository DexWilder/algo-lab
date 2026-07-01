# Data Blocker Certificates (2026-06-30/07-01) — DATA_BLOCKED is now PROVEN or it's void

> Trigger: I asserted DATA_BLOCKED without lineage proof — the exact failure class from Databento/wp_b1. Investigation
> found **the Databento API key is in `.env`, package installed (v0.72.0), and per-contract data costs CENTS to pull.**
> Almost nothing I called blocked actually was. New rule: no DATA_BLOCKED label without a certificate below.

## PROVEN status of every prior "DATA_BLOCKED"/"PAID" claim
| Item | I WRONGLY said | PROVEN status | Evidence | Exact unblock |
|---|---|---|---|---|
| 2s5s10s / 5s10s30s tradeable rates RV | DATA_BLOCKED | **LOCAL_DATA_FOUND_USE_IT_NOW** | ZT/ZF/ZN/ZB per-contract PULLED ($0.30); 2177/2308 days have front+deferred outrights | build fly on real front contracts |
| proper futures carry / roll-yield (rates) | DATA_BLOCKED | **LOCAL_DATA_FOUND_USE_IT_NOW** | same pull | build roll-yield carry |
| commodity term-structure carry | DATA_BLOCKED | **LOCAL_DATA_FOUND_USE_IT_NOW** | CL (2998 contracts) + GC (999) PULLED ($3.05) | build commodity carry |
| options gamma / GEX / OI | PAID_DATA_REQUIRED | **DATABENTO_REPULL_POSSIBLE** | ES.OPT ohlcv-1d 2022-26 = **$9.58** (cost-checked) | pull ES.OPT (OI via `statistics` schema) |
| VIX futures curve / vol-carry | PAID | **DATABENTO_REPULL_CHECK** | not yet cost-checked (GLBX has VX? verify dataset) | cost-check VX.FUT |
| DVOL ETH "malformed" | DATA_LIMITED | **LOCAL_DATA_FOUND_USE_IT_NOW** | date,value blank-header (same as DVOL_BTC), 1918 rows | read with header=0, col '0'=DVOL |
| FX / policy-rate carry (n=0) | (implied blocked) | **LOCAL_DATA_PARSE_BUG** | policy_rates has fed_funds+boj; my join dropped all | fix ffill/align |
| EIA crude inventory surprise | DATA_BLOCKED | **FREE_API (EIA) — not Databento** | EIA v2 API free key | write EIA pull to data/feeds/eia_crude_stocks.csv |
| CPI consensus/surprise | DATA_BLOCKED | **partial: release dates FREE, consensus = vendor** | BLS free; consensus is the only paid piece | operator/vendor for consensus only |

## The corrected meta-conclusion
The "we're stuck / need operator data decisions / paid-data tier" framing was an EXECUTION MISS. The high-EV structural
data (per-contract futures term-structure for rates+commodities, and even ES options for gamma) is Databento-pullable for
**<$15 total with the key already present.** Genuinely external: EIA/BLS macro (free APIs) + consensus (small vendor).
Nothing warrants a "paid-data decision" gate. **Total spent proving this: ~$3.30 (rates+CL+GC pulled).**

## Standing rule (guardrail-enforced)
No item may be labeled DATA_BLOCKED / PAID_DATA_REQUIRED without a certificate here proving: local search, loader/Databento
regeneration check (with cost), existing-harness check, and exact unblock command. Else label = DATA_STATUS_UNPROVEN.
