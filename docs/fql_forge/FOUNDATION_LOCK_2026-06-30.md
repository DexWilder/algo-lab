# FOUNDATION LOCK (2026-06-30/07-01) — pre-sprint, proof-based. PASS → sprint immediately.

## 1. Data-quality lock — per-contract RATES (PASS)
`data/databento/{ZT,ZF,ZN,ZB}_percontract_1d.csv`. Loader `research/term_structure.py` (filters `UD:` spreads to outrights).
| root | outrights | dupes | range | F1+F2 days | F3 days |
|---|---|---|---|---|---|
| ZT(2y) | 32 | 0 | 2019-01→2026-05 | 1624 | 101 |
| ZF(5y) | 32 | 0 | same | 1586 | 42 |
| ZN(10y) | 32 | 0 | same | 2148 | 593 |
| ZB(30y) | 32 | 0 | same | 2079 | 513 |
Fields: ts_event, instrument_id, symbol, OHLCV. TZ→naive-date. Expiry parsed from month-code+year (F..Z, digit; 9=2019).
**Front rule:** nearest un-expired outright by expiry. **Deferred:** next. Quarterly (H/M/U/Z). Roll: implicit via
per-date live-contract selection (NO stitch → no roll artifact). **Supports: roll-yield/carry ✓, 2s5s10s (ZT+ZF+ZN) ✓,
5s10s30s (ZF+ZN+ZB) ✓, front/deferred spread ✓.**

## 2. Data-quality lock — COMMODITY term-structure (PASS after re-pull)
CL: 120 outrights, GC: 112; F1/F2/F3 on 2305 days (deep curves). (First save dropped ts_event=index → re-pulled with
reset_index; now clean.) **Micro mapping:** signal on CL/GC per-contract; tradeable via MCL/MGC (micros = same underlying,
1/10 size) — valid as EXECUTION proxy, verify point-value. Crude roll artifacts SOLVED (per-contract, not continuous .c.0).

## 3. Databento regeneration lock (PASS)
Key in `.env` ✓; pkg 0.72.0 ✓; reusable `data/databento_percontract_pull.py` (cost-check-before-pull) ✓; per-contract
command documented ✓. **Spend threshold rule: pulls ≤ $5 auto-run; > $5 = OPERATOR_COST_APPROVAL.** Spent on foundation:
~$6.40 (rates $0.30 + CL/GC $3.05 ×2 re-pull). **ES options gamma = $9.58 → OPERATOR_COST_APPROVAL_REQUIRED** (command ready).

## 4. Certificate/guardrail lock (PASS)
`forge_system_guardrails.py` check-9: DATA_BLOCKED/PAID_DATA_REQUIRED without a certificate → P1 fail; cert doc present →
[ok]. Also live: unused-feeds, unrun-harnesses, close-only-bias, git-backlog, WH-language, trial-ledger. Verdict: P1_WARN.

## 5. Master-queue lock — newly-unblocked families ADDED (RUN_NOW)
rates roll-yield/carry, true 2s5s10s RV, 5s10s30s (distinct), commodity CL/GC carry → RUN_NOW. gamma → OPERATOR_COST_APPROVAL.
VIX/DVOL corrected-local → queue. See forge_run_queue.json.

## 6. Status-label lock (corrected)
proper rates carry/RV, commodity carry = **LOCAL_DATA_FOUND_USE_IT_NOW** (was DATA_BLOCKED). gamma = **OPERATOR_COST_APPROVAL_REQUIRED**
($9.58, not "paid tier"). DVOL_ETH = LOCAL_DATA_FOUND (was "malformed"). FAMILY_EXHAUSTED reserved for coverage-proven; CLEAN_KILL reserved for correct-data+harness+DSR.

## 7. Trial-ledger lock
Global N ~1769 (primitive_sweep=1679 dominates). Lanes: carry, curve_rv, commodity_carry (new) counted SEPARATELY from
primitive_sweep so structural families aren't buried. Rates/commodity tests → carry/curve_rv lanes; report global+family+lane+packet N + threshold 0.95.

## 8. Existing-harness lock (checked BEFORE building)
EXISTING: `forge_cycle_2026-06-24c_s1_rollyield_carry.py`, `run_treasury_rolldown_spread.py`, `forge_cycle_2026-06-17d_p1p2_rates_carry.py`
— all ran on CONTINUOUS/PROXY data (per-contract didn't exist before today). Sprint uses `term_structure.py` real front/deferred
(NEW capability) and reconciles those old verdicts. No pure duplication.

## 9. Commit/push lock — backlog 0 (verified below).
