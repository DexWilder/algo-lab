# Gamma / Options (GEX) Feasibility Memo (2026-07-01) — FEASIBILITY ONLY, not a strategy claim

> Operator approved "pull gamma". Per instruction, FIRST output = schema/OI/GEX feasibility, NOT a strategy. Proof on
> a cheap ES.OPT sample (GLBX.MDP3, key in .env). No GEX strategy is claimed here.

## The 10 questions — answered from real pulled data
1. **OI present?** YES — statistics schema `stat_type=9` = open interest (`quantity` field). POC 2026-05-05: 2,784 lines w/ OI.
2. **Strikes/expirations clean?** YES — definition schema `strike_price` + `expiration` (per instrument_id).
3. **Underlying mapping?** YES — definition `underlying` + `instrument_class` (C/P/T/M).
4. **Bid/ask or trades/OHLC?** statistics (OI+settlement) + ohlcv-1d (prices). Bid/ask needs mbp/tbbo (available, not needed for GEX).
5. **Approx GEX computable?** YES — dealer GEX = Σ_strike OI_k × BS_gamma_k × dealer-sign. POC: call-OI 878k, put-OI 1.57M; max-call-OI strike 7200, max-put-OI 6800 (gamma-wall/max-pain candidates).
6. **Greeks present?** NO — must approximate via Black-Scholes (IV inverted from settlement price + underlying + strike + expiry). Standard.
7. **Historical depth?** GLBX ES.OPT definition+statistics available; 2023-2026 pullable. Sufficient.
8. **Point-in-time timing?** Daily OI/settlement are EOD → prior-day GEX for next-day trading is point-in-time. (OI updates daily; intraday GEX uses prior EOD OI + live underlying.)
9. **Exact ES/MES expression (candidate, not claim):** daily dealer-GEX profile → gamma-flip level + GEX-regime (positive→pinning/mean-revert, negative→trend-amplify) → trade MES/ES intraday around it (intraday-flat prop profile).
10. **First safe packet:** predeclared test — does GEX-regime (sign/magnitude, lagged) predict next-day ES realized vol / mean-reversion vs trend? Through data+expression validators. FEASIBILITY→regime test, NOT a strategy yet.

## Cost / data-engineering
- POC spend: ~$0.10 (1-day + earlier samples). Full GEX-essentials (statistics+definition 2023-26) = **$11.54** → **> $5 threshold → OPERATOR_COST_APPROVAL** (gamma approved; will pull for the strategy phase).
- **Data-engineering finding:** ES.OPT statistics over multi-month windows 504-TIMES-OUT (huge). Full pull MUST be CHUNKED (daily/weekly loop) or use Databento batch API. Loader for this = a prerequisite before the regime test.

## Status
gamma/options = **DATABENTO_REPULL_POSSIBLE (chunked), GEX FEASIBLE, OPERATOR_COST_APPROVED**. Next: chunked OI loader →
approx-GEX builder → predeclared GEX-regime test (validators first). No GEX strategy claimed until that runs.
