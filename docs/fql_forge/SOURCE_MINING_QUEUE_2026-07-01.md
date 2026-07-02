# Source-Mining Queue (2026-07-01) — external insight → packet factory

> Elite novelty can't rely only on internal generation. No source summary counts unless it produces a packet or archive.
> Each item → mechanism packet (scored by `score_novelty_packet.py`) → queue. Status: QUEUED / PACKETED / ARCHIVED.

| # | Source category | Expected mechanism | Priority | Data req (tier) | Output packet target | Status |
|---|---|---|---|---|---|---|
| 1 | CME roll methodology docs | forced index/fund roll timing | P1 | per-contract T4 | roll-window pressure (CL/GC/ZN) | QUEUED |
| 2 | Options dealer-hedging papers (SqueezeMetrics/Nomura-style) | gamma pin / flip reflexivity | P1 | ES.OPT OI T6 | GEX-regime pin | QUEUED (data-blocked on loader) |
| 3 | CTA/trend/carry papers (AQR/MAN) | crowding + carry premia | P2 | T4/T5 | carry-neighborhood of spreadMR_GC | QUEUED |
| 4 | Microstructure (Kyle, VPIN, Easley) | informed-flow / liquidity-hole | P1 | 1m+volume T3 | liquidity-hole reversal | QUEUED |
| 5 | Treasury auction concession studies | dealer inventory pre/post auction | P2 | auctions T5 | tenor-divergence concession | QUEUED |
| 6 | Month/quarter-end rebalance studies | index-fund forced rebalance | P2 | calendar T5 + 1m T3 | settlement-1m revert | QUEUED |
| 7 | VRP literature | vol risk premium curve | P2 | VIX/DVOL T5/T6 | true-curve VRP | QUEUED |
| 8 | Commodity term-structure research | roll-yield / storage / lease | P1 | per-contract T4 | contango-bleed (CL/GC) | QUEUED |
| 9 | Crypto funding/perp research | funding-carry / basis | P3 | Deribit/OKX T5 | (funding killed; basis untested) | QUEUED |
| 10 | Execution/TWAP-VWAP notes | benchmark-fix flow | P1 | 1m T3 | WMR 16:00 fix (FX) | QUEUED |

**P1: convert ≥3 of these to scored packets next cycle to prove the source lane is a real factory (currently 0 source-derived packets).**
