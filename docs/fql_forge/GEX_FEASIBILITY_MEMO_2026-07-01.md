# GEX / Dealer-Gamma Feasibility Memo (2026-07-01) — PROVEN on real ES.OPT sample

> Operator-approved pull ($0.07, well under $25 cap). Sample: ES.OPT definition+statistics, 2025-06-02..07. Report-only.
> **No strategy claim** — this memo only proves OI/GEX is computable.

| Question | Answer (from sample) |
|---|---|
| Cost | $0.07 sample; full history via chunked loader (5-mo pull previously 504-timed-out) |
| Schema | definition (22,526 rows) + statistics (967,705 rows) |
| Strikes / expirations | 292 unique strikes; `strike_price`, `expiration` present |
| Calls/Puts | `instrument_class`: C=6,954, P=6,954, T=7,760, M=858 |
| **Open Interest present?** | **YES** — `stat_type=9`, 16,489 rows |
| Settlement price | present (stat_type set incl. 3/6) → IV inversion feasible |
| Greeks present? | **NO** — Databento GLBX has no greeks; gamma = Black-Scholes from IV inverted off settlement |
| Approx GEX feasible? | **YES** — Σ(OI_strike × BS-gamma(IV_strike) × dealer-sign) |
| PIT timing risk | statistics `ts_ref` vs `ts_event`; OI is prior-day settle → use with 1-day lag (causal) |
| First safe packet | GEX-regime: sign of net dealer gamma (above/below flip) → next-day realized-vol / pin behavior |
| Loader status | sample loader works; **chunked-OI loader still required for full history (P1)** |
| Data validator | sample columns validated present; full pull needs validate_data_file pass |

**Verdict:** GEX vein is DATA-UNLOCKED at T6 (feasibility proven). Next: chunked-OI loader → full-history OI+settlement → invert IV → approx-GEX → predeclared GEX-regime test (adversarial + DSR). No claim until that runs.
